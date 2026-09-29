"""基础用法：日志格式标准化（Day 160 — 日志安全分析）。

本文件演示"标准化"到底是什么：
1. 三种异构日志（sshd syslog / nginx combined / 应用 JSON）→ 统一 LogEvent
2. 时间一律解析成**带时区**的 datetime；解析不了就是 None，绝不填 now()
3. 完全相同的重复行去重（日志重采/轮转边界很常见）
4. 统计覆盖：无法识别的行、缺时间戳的行、乱序行，全部如实计数

运行：
    python3 01-log-parser.py              # 打印标准化结果与覆盖统计
    python3 01-log-parser.py --self-test  # 输出 SELF-TEST OK

本文件里所有 IP（203.0.113.x / 198.51.100.x / 192.0.2.x）与账号均为
文档专用示例值（RFC 5737 / RFC 2606），不是真实环境数据。
"""

import argparse

from log_core import (
    DEFAULT_TZ,
    detect_source,
    mask_ip,
    parse_lines,
    parse_timestamp,
    subject_sha,
)

# ── 合成日志样例 ────────────────────────────────────────────────────────
# 刻意混入 4 类"脏"数据：未知格式、缺时间戳、重复行、乱序行。
SYNTHETIC_LINES = [
    # sshd（syslog 格式，无年份、无时区）
    "Sep 19 06:12:01 web01 sshd[1234]: Failed password for invalid user admin from 203.0.113.7 port 51234 ssh2",
    "Sep 19 06:12:04 web01 sshd[1235]: Failed password for invalid user admin from 203.0.113.7 port 51240 ssh2",
    "Sep 19 06:15:00 web01 sshd[1240]: Accepted password for deploy from 10.0.0.5 port 51280 ssh2",
    # 乱序：这行时间早于上一行（多主机/多文件合并后很常见）
    "Sep 19 05:59:00 web01 sshd[1200]: Accepted publickey for deploy from 10.0.0.5 port 51100 ssh2",
    # nginx combined
    '203.0.113.9 - - [19/Sep/2026:06:13:20 +0800] "POST /login HTTP/1.1" 401 512 "-" "curl/8.0"',
    # 应用 JSON
    '{"time": "2026-09-19T06:14:00+08:00", "event": "login_failed", "host": "api01", "user": "ops", "src_ip": "198.51.100.23"}',
    # 缺时间戳的 JSON（时间不可用 → 不猜，计入 no_timestamp）
    '{"event": "login_failed", "host": "api02", "user": "svc", "src_ip": "198.51.100.9"}',
    # 重复行（与第一行完全一致）
    "Sep 19 06:12:01 web01 sshd[1234]: Failed password for invalid user admin from 203.0.113.7 port 51234 ssh2",
    # 完全无法识别的行
    "this line matches nothing and must be counted as unparsed",
    "",
]


def normalize(lines=None):
    """标准化入口：返回 (events, coverage)。"""
    lines = SYNTHETIC_LINES if lines is None else lines
    return parse_lines(lines, fallback_host="unknown-host", assume_tz=DEFAULT_TZ,
                       year=2026, source_name="synthetic.log")


def render_events(events) -> str:
    header = f"{'TIME(UTC+8)':<20} {'HOST':<7} {'SOURCE':<7} {'ACTION':<14} {'USER':<8} {'SRC_IP':<16} STATUS REF"
    rows = [header, "-" * len(header)]
    for event in events:
        time_text = event.ts.strftime("%Y-%m-%d %H:%M:%S") if event.ts else "??"
        rows.append(
            f"{time_text:<20} {event.host:<7} {event.source:<7} {event.action:<14} "
            f"{(event.user or '-'):<8} {mask_ip(event.src_ip):<16} "
            f"{(event.status if event.status is not None else '-'):<6} {event.ref}"
        )
    return "\n".join(rows)


def render_coverage(coverage) -> str:
    lines = [
        "覆盖统计：",
        f"  lines_total={coverage.lines_total} parsed={coverage.parsed} "
        f"unparsed={coverage.unparsed} no_timestamp={coverage.no_timestamp} "
        f"deduped={coverage.deduped} out_of_order={coverage.out_of_order}",
        f"  hosts={coverage.hosts}",
        f"  time_range={coverage.time_start} → {coverage.time_end}",
        f"  complete={coverage.complete}  gaps={coverage.gaps}",
    ]
    return "\n".join(lines)


def self_test() -> None:
    # 1) 时间解析：三种格式 + 不可解析
    assert parse_timestamp("19/Sep/2026:06:12:01 +0800").utcoffset().total_seconds() == 8 * 3600
    assert parse_timestamp("2026-09-19T06:12:01Z").tzinfo is not None
    syslog_ts = parse_timestamp("Sep 19 06:12:01", year=2026)
    assert (syslog_ts.year, syslog_ts.month, syslog_ts.day, syslog_ts.hour) == (2026, 9, 19, 6)
    assert parse_timestamp("not-a-time") is None
    assert parse_timestamp("") is None

    # 2) 来源识别
    assert detect_source(SYNTHETIC_LINES[0]) == "sshd"
    assert detect_source(SYNTHETIC_LINES[4]) == "nginx"
    assert detect_source(SYNTHETIC_LINES[5]) == "app"
    assert detect_source("garbage") == "unknown"

    # 3) 标准化结果
    events, coverage = normalize()
    actions = [e.action for e in events]
    assert "login_failed" in actions and "login_success" in actions and "request" in actions
    assert coverage.unparsed == 1, coverage.unparsed
    assert coverage.no_timestamp == 1, coverage.no_timestamp
    assert coverage.deduped == 1, coverage.deduped
    assert coverage.out_of_order == 1, coverage.out_of_order
    assert coverage.complete is False and len(coverage.gaps) == 2

    # 4) 事件按时间升序：05:59 必须排到 06:12 之前（乱序被修正）
    timed = [e for e in events if e.ts]
    assert timed == sorted(timed, key=lambda e: e.ts), "事件必须按时间排序"
    assert timed[0].ts.hour == 5 and timed[0].ts.minute == 59

    # 5) 缺时间戳的事件仍然保留（只是标记为不可用于窗口判定）
    assert any(e.ts is None for e in events)
    assert coverage.parsed == len(events) == 7, len(events)

    # 6) 报告脱敏工具
    assert mask_ip("203.0.113.7") == "203.0.113.x"
    assert mask_ip("2001:db8::1") == "2001:db8::x"
    assert mask_ip(None) == "-"
    assert subject_sha("a|b") == subject_sha("a|b") != subject_sha("a|c")

    # 7) host 覆盖：sshd 行的 host 来自日志本身，nginx/JSON 用 fallback/字段
    assert set(coverage.hosts) == {"web01", "api01", "api02", "unknown-host"}, coverage.hosts

    # 8) 渲染不泄露原始行（raw 不在结果对象里，渲染自然也不会带出来）
    text = render_events(events) + render_coverage(coverage)
    assert "Failed password for invalid user" not in text, "报告不应复制原始日志行"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("SELF-TEST OK")
    else:
        events, coverage = normalize()
        print(render_events(events))
        print()
        print(render_coverage(coverage))
        print()
        print("提示：缺时间戳 / 无法识别的行不会参与窗口判定，但必须在报告里声明。")
