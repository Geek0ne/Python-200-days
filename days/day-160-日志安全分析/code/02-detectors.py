"""进阶用法与常见陷阱：七个检测器与它们的边界（Day 160）。

检测器不难写，难的是知道它们**什么时候会骗你**。本文件用合成日志构造
七种场景，并逐条演示对应的踩坑方式：

  1. 阈值幻觉：同样的数据，threshold=20 时"零告警"——零告警不等于安全
  2. 跨主机混淆：同一个 IP 打在两台主机上，必须是两条独立告警
  3. 分布式爆破：每个来源都低于单源阈值，per-IP 规则完全看不见
  4. 失败后成功：只有 host+user+ip 全部相同才算同一链路，否则全是误报
  5. 非工作时段：值班、发布窗口会产生大量正常夜间登录 → 低置信度
  6. 缺时间戳：窗口类检测直接不可用，必须声明而不是静默跳过
  7. 乱序输入：文件顺序不可信，排序后才允许做窗口统计

运行：
    python3 02-detectors.py
    python3 02-detectors.py --self-test
"""

import argparse

from log_core import analyze, mask_ip, parse_lines, priority

# ── 合成日志生成器 ──────────────────────────────────────────────────────
def sshd(clock: str, msg: str, host: str = "web01", pid: int = 1000) -> str:
    """生成一行 sshd syslog（Sep 19 固定日期，年份由 parse_lines 补齐）。"""
    return f"Sep 19 {clock} {host} sshd[{pid}]: {msg}"


def nginx(clock: str, path: str, status: int, ip: str = "203.0.113.50") -> str:
    """生成一行 nginx combined 日志。"""
    return f'{ip} - - [19/Sep/2026:{clock} +0800] "GET {path} HTTP/1.1" {status} 512 "-" "curl/8.0"'


def build_scenarios() -> dict:
    """构造七个场景的日志行（各场景之间互不干扰）。"""
    logs = {}

    # 场景 1/2：单源爆破（同主机 10 次失败），并有同一 IP 打另一台主机的情况
    logs["brute"] = [
        sshd(f"07:00:{i:02d}", f"Failed password for invalid user admin from 203.0.113.7 port 51{i:03d} ssh2")
        for i in range(10)
    ]
    logs["brute"] += [
        sshd(f"07:01:{i:02d}", f"Failed password for invalid user admin from 203.0.113.7 port 52{i:03d} ssh2",
             host="web02")
        for i in range(10)
    ]

    # 场景 3：分布式爆破 —— 5 个来源，每个 3 次失败（单源阈值 8 抓不到）
    # 注意：三次失败必须时间各不相同，否则会被去重成 1 条（第 1 课的去重机制）
    logs["distributed"] = [
        sshd(f"08:{i:02d}:{j * 10:02d}",
             f"Failed password for invalid user svc from 198.51.100.{i} port 4000{i} ssh2")
        for i in range(1, 6)
        for j in range(3)
    ]

    # 场景 4：失败后成功（同主机 + 同账号 + 同来源 IP）
    logs["fts"] = [
        sshd(f"09:00:0{i}", f"Failed password for deploy from 192.0.2.9 port 6000{i} ssh2")
        for i in range(4)
    ] + [sshd("09:00:09", "Accepted password for deploy from 192.0.2.9 port 60009 ssh2")]

    # 场景 5：非工作时段成功登录（03:20）
    logs["offhours"] = [sshd("03:20:00", "Accepted publickey for deploy from 192.0.2.20 port 2200 ssh2")]

    # 场景 6：Web 撞库 + 目录穿越探测
    logs["web"] = [nginx(f"10:00:{i:02d}", "/login", 401) for i in range(25)]
    logs["web"] += [nginx("10:05:00", "/static/../../etc/passwd", 404)]

    # 场景 7：缺时间戳的事件（JSON 没有 time 字段）
    logs["no_timestamp"] = ['{"event": "login_failed", "host": "api01", "user": "ops", "src_ip": "198.51.100.77"}']

    return logs


def analyze_scenario(name: str, lines: list, **params):
    events, coverage = parse_lines(lines, fallback_host="unknown-host", year=2026,
                                   source_name=f"{name}.log")
    return analyze(events, coverage, parameters=params)


def print_alerts(report, title: str) -> None:
    print(f"── {title}")
    if not report.alerts:
        print("   （无告警）")
    for alert in report.alerts:
        print(f"   [P{alert.band[1]}] {alert.detector:<30} {alert.severity:<8} {alert.subject} "
              f"count={alert.count} {alert.evidence}")
    print(f"   覆盖：complete={report.coverage.complete} gaps={report.coverage.gaps}")


def self_test() -> None:
    logs = build_scenarios()

    # ── 1) 单源爆破：两台主机各一条告警，绝不合并 ──
    report = analyze_scenario("brute", logs["brute"])
    brute = [a for a in report.alerts if a.detector == "brute_force_single_source"]
    assert len(brute) == 2, f"跨主机必须分成 2 条告警，实际 {len(brute)}"
    assert {a.subject.split("@")[1] for a in brute} == {"web01", "web02"}
    assert all(a.count == 10 for a in brute)

    # ── 2) 阈值幻觉：同一份数据，阈值 20 时零告警 ──
    quiet = analyze_scenario("brute", logs["brute"], brute_threshold=20)
    assert not [a for a in quiet.alerts if a.detector == "brute_force_single_source"]
    assert quiet.parameters["brute_threshold"] == 20, "报告必须回显实际使用的阈值"

    # ── 3) 分布式爆破：per-IP 抓不到，按账号聚合才可见 ──
    dist = analyze_scenario("distributed", logs["distributed"])
    assert not [a for a in dist.alerts if a.detector == "brute_force_single_source"], \
        "单源规则不应命中（每个来源都低于阈值）"
    distributed = [a for a in dist.alerts if a.detector == "brute_force_distributed"]
    assert len(distributed) == 1 and distributed[0].count == 15, distributed

    # ── 4) 失败后成功：必须同 host+user+ip ──
    fts = analyze_scenario("fts", logs["fts"])
    hits = [a for a in fts.alerts if a.detector == "failed_then_success"]
    assert len(hits) == 1 and hits[0].count == 4, hits
    assert hits[0].confidence == "medium", "本人连续输错也会命中，不能给高置信度"
    # 反例：失败来自 A，成功来自 B（不同来源）→ 不算同一条链路
    mixed = [
        sshd(f"09:00:0{i}", f"Failed password for deploy from 192.0.2.9 port 6000{i} ssh2") for i in range(4)
    ] + [sshd("09:00:09", "Accepted password for deploy from 192.0.2.99 port 60099 ssh2")]
    assert not [a for a in analyze_scenario("mixed", mixed).alerts
                if a.detector == "failed_then_success"], "不同来源 IP 不应关联"

    # ── 5) 非工作时段：低置信度 + 低严重度 ──
    off = analyze_scenario("offhours", logs["offhours"])
    off_hits = [a for a in off.alerts if a.detector == "off_hours_success"]
    assert len(off_hits) == 1 and (off_hits[0].severity, off_hits[0].confidence) == ("low", "low")

    # ── 6) Web 撞库 + 穿越探测 ──
    web = analyze_scenario("web", logs["web"])
    web_hits = [a for a in web.alerts if a.detector == "web_auth_abuse"]
    assert len(web_hits) == 1 and web_hits[0].count == 25, web_hits
    assert [a for a in web.alerts if a.detector == "path_traversal_probe"]

    # ── 7) 缺时间戳：窗口类检测不可用，且必须在覆盖里声明 ──
    no_ts = analyze_scenario("no_timestamp", logs["no_timestamp"])
    assert no_ts.coverage.no_timestamp == 1
    assert no_ts.coverage.complete is False
    assert no_ts.coverage.gaps and "no_timestamp" in no_ts.coverage.gaps[0]
    assert not [a for a in no_ts.alerts if "brute" in a.detector], "无时间戳不能参与窗口判定"

    # ── 8) 乱序输入：排序后仍然检测出同样结果 ──
    shuffled = list(reversed(logs["brute"]))
    shuffled_report = analyze_scenario("shuffled", shuffled)
    assert len([a for a in shuffled_report.alerts
                if a.detector == "brute_force_single_source"]) == 2

    # ── 9) 排序与优先级：第一条必须是最高优先级 ──
    combined = analyze_scenario("combined", sum(logs.values(), []))
    ordered = [priority(a.severity, a.confidence) for a in combined.alerts]
    assert ordered == sorted(ordered, reverse=True)

    # ── 10) 报告脱敏：不得出现完整 IP ──
    for alert in combined.alerts:
        assert "203.0.113.7" not in alert.subject, alert.subject
        assert alert.evidence is not None and mask_ip("198.51.100.1") == "198.51.100.x"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("SELF-TEST OK")
    else:
        logs = build_scenarios()
        combined = analyze_scenario("combined", sum(logs.values(), []))
        print(f"检测器：{', '.join(combined.detectors_run)}\n")
        print_alerts(analyze_scenario("brute", logs["brute"]), "场景1/2 单源爆破 + 跨主机隔离")
        print_alerts(analyze_scenario("distributed", logs["distributed"]), "场景3 分布式爆破")
        print_alerts(analyze_scenario("fts", logs["fts"]), "场景4 失败后成功")
        print_alerts(analyze_scenario("offhours", logs["offhours"]), "场景5 非工作时段登录")
        print_alerts(analyze_scenario("web", logs["web"]), "场景6 Web 撞库 + 穿越探测")
        print_alerts(analyze_scenario("no_timestamp", logs["no_timestamp"]), "场景7 缺时间戳")
        print()
        print("提示：阈值是参数不是真理。报告必须回显参数，"
              "否则'没告警'与'阈值太宽'无法区分。")
