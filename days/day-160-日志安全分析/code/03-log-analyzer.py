"""实战：安全日志分析器 CLI（Day 160 — 日志安全分析）。

把"解析 → 标准化 → 检测 → 报告 → 门禁"整合成一个可用的命令行工具。

整合纪律（为什么这么切）：
1. **parse 与 analyze 分开**：解析问题（格式变了、编码错了）与检测问题
   （阈值不合适）是两类完全不同的故障，混在一起排查会浪费大量时间。
2. **JSON 是机器接口，Markdown 是人的接口**：CI 与工单系统只该消费 JSON。
3. **退出码优先级 2 > 4 > 3 > 0**：覆盖不全（4）不能当门禁依据，
   所以它优先于"有告警"（3）。
4. **参数必须回显**：报告里带上实际使用的 window/threshold。
   "没告警"与"阈值太宽"必须能被区分开。
5. **只读 + 不构造请求**：本工具只读日志文件；发现"目录穿越探测"时
   只记录日志事实，**不**去发请求验证（那是渗透测试，需要单独授权）。

运行：
    python3 03-log-analyzer.py parse sshd.log access.log      # 只看标准化
    python3 03-log-analyzer.py analyze /var/log              # 分析目录下 *.log
    python3 03-log-analyzer.py analyze a.log --format json --fail-on high
    python3 03-log-analyzer.py analyze a.log --baseline baseline.json
    python3 03-log-analyzer.py lab                            # 合成日志演示（exit 3）
    python3 03-log-analyzer.py lab --dirty                    # 含脏数据（exit 4）
    python3 03-log-analyzer.py --self-test
"""

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

from log_core import (AlertReport, LogCoverage, analyze, mask_ip, parse_lines,
                      priority, summarize)

EXIT_OK, EXIT_USAGE, EXIT_GATE, EXIT_COVERAGE = 0, 2, 3, 4
MAX_LINES_PER_FILE = 200_000   # 资源自限：单个文件最多读这么多行


# ─────────────────────────────── IO ───────────────────────────────
def expand_targets(paths) -> list:
    """把文件/目录展开成日志文件列表（目录只收 *.log / *.txt）。"""
    files: list = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*")
                                if p.is_file() and p.suffix.lower() in (".log", ".txt")))
        elif path.is_file():
            files.append(path)
    return files


def read_lines(files, *, max_lines: int = MAX_LINES_PER_FILE) -> tuple:
    """读取日志行，返回 (lines, read_errors)。二进制/无法解码的行按原文跳过。"""
    lines, errors = [], []
    for path in files:
        try:
            with path.open("r", encoding="utf-8", errors="strict") as handle:
                for count, line in enumerate(handle, start=1):
                    if count > max_lines:
                        errors.append(f"{path.name}: 超过 {max_lines} 行，已截断")
                        break
                    lines.append(line.rstrip("\n"))
        except OSError as exc:
            errors.append(f"{path.name}: {exc.__class__.__name__}")
        except UnicodeDecodeError:
            errors.append(f"{path.name}: 非 UTF-8 编码，已跳过")
    return lines, errors


def load_baseline(path: str | None) -> dict:
    """基线文件格式：{"host|user": ["1.2.3.4", ...]}，用于"新来源登录"检测。"""
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("baseline 必须是 JSON 对象：{\"host|user\": [\"ip\", ...]}")
    return {str(k): {str(ip) for ip in v} for k, v in data.items()}


def analyze_files(paths, *, params: dict | None = None, baseline: dict | None = None,
                  year: int = 2026, fallback_host: str | None = None) -> tuple:
    files = expand_targets(paths)
    if not files:
        return None, ["未找到可读的日志文件"]
    lines, read_errors = read_lines(files)
    # fallback host：日志本身不带主机名时（nginx combined / JSON 无 host 字段）用它。
    # 它会被记进 coverage.hosts，所以报告里能看到"主机名其实是猜的"。
    host = fallback_host or files[0].stem or "unknown-host"
    events, coverage = parse_lines(lines, fallback_host=host, year=year,
                                   source_name=",".join(p.name for p in files[:3]))
    report = analyze(events, coverage, baseline=baseline, parameters=params or {})
    return report, read_errors


# ─────────────────────────────── 报告 ───────────────────────────────
def escape_md(text) -> str:
    return str(text).replace("|", "\\|").replace("`", "\\`").replace("\n", " ")


def coverage_ok(report) -> bool:
    return report.coverage.complete and report.coverage.lines_total > 0


def render_markdown(report, sources: list = (), read_errors: list = ()) -> str:
    cov = report.coverage
    if cov.lines_total == 0:
        gaps = ["empty_input=没有任何可解析的日志行，报告不可用于任何结论"]
    else:
        gaps = list(cov.gaps)
    gaps.extend(f"read_error={e}" for e in read_errors)

    lines = [
        "# 安全日志分析报告",
        "",
        f"- 输入文件：{len(sources)} 个" + (f"（{escape_md(', '.join(Path(s).name for s in sources[:5]))}…）"
                                          if sources else ""),
        f"- 行数：{cov.lines_total}（解析 {cov.parsed}，无法识别 {cov.unparsed}，"
        f"缺时间戳 {cov.no_timestamp}，去重 {cov.deduped}，乱序 {cov.out_of_order}）",
        f"- 主机：{escape_md(', '.join(cov.hosts)) or '-'}",
        f"- 时间范围：{cov.time_start} → {cov.time_end}（统一为 UTC+8 展示）",
        f"- 告警：{len(report.alerts)} 条"
        + ("（" + "、".join(f"{k}={v}" for k, v in report.by_severity().items() if v) + "）"
           if report.alerts else ""),
        "",
    ]

    if gaps:
        lines += [
            "## ⚠️ 覆盖声明（先读这一段）",
            "",
        ]
        lines += [f"- {escape_md(g)}" for g in gaps]
        lines += [
            "",
            "上述范围内的日志**没有参与判定**。本次报告不能用于得出"
            "「未发现异常」的结论。",
            "",
        ]
    else:
        lines += ["- 覆盖：完整（全部行均成功解析且带时间戳）", ""]

    if not report.alerts:
        lines += [
            "## 告警明细",
            "",
            "无告警。**注意**：这只说明在当前阈值下没有命中模式，"
            "请核对下方「检测参数」——阈值过宽同样会产生零告警。",
            "",
        ]
    else:
        lines += ["## 告警明细（按优先级排序）", ""]
        for alert in report.alerts:
            lines += [
                f"### [{alert.band}] {escape_md(alert.detector)} — {escape_md(alert.title)}",
                "",
                f"- 主体：`{escape_md(alert.subject)}`（sha: {alert.subject_sha}）",
                f"- 次数 / 窗口：{alert.count} 次 / {alert.window_seconds}s",
                f"- 时间：{alert.first_ts} → {alert.last_ts}",
                f"- 严重度 / 置信度：{alert.severity} / {alert.confidence}",
                f"- 证据：{escape_md(alert.evidence)}",
                f"- 为什么可疑：{escape_md(alert.why)}",
                f"- 处置建议：{escape_md(alert.remediation)}",
                "",
            ]

    lines += [
        "## 检测参数（阈值回显）",
        "",
        "| 参数 | 值 | 含义 |",
        "| --- | --- | --- |",
    ]
    defaults = {"brute_window": 300, "brute_threshold": 8, "dist_window": 600,
                "dist_threshold": 10, "dist_min_sources": 3, "fts_window": 900,
                "fts_min_failures": 3, "work_start": 8, "work_end": 20,
                "web_window": 600, "web_threshold": 20}
    for key, default in defaults.items():
        value = report.parameters.get(key, default)
        marker = "（本次自定义）" if key in report.parameters else "（默认）"
        lines.append(f"| `{key}` | {value} {marker} | |")
    lines += [
        "",
        f"## 检测器清单（{len(report.detectors_run)} 个）",
        "",
        "- " + "、".join(f"`{name}`" for name in report.detectors_run),
        "",
        "---",
        "",
        "本报告由离线只读日志分析器生成：不改动日志文件、不发起任何网络请求、"
        "对外展示的 IP 已做末段掩码。告警为复核线索，需人工确认后处置。",
        "",
    ]
    return "\n".join(lines)


def gate_exit_code(report, read_errors=(), fail_on: str = "high") -> int:
    """0 通过 / 3 有告警达到阈值 / 4 覆盖不全或无可分析输入。"""
    if not coverage_ok(report) or read_errors:
        return EXIT_COVERAGE
    if report.at_or_above(fail_on):
        return EXIT_GATE
    return EXIT_OK


# ─────────────────────────────── 演示数据 ───────────────────────────────
def build_lab(directory: Path, *, dirty: bool = False) -> Path:
    """生成一份多主机合成日志（内容与 02-detectors.py 的场景一致）。"""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "lab-auth.log"

    def sshd(clock, msg, host="web01", pid=2000):
        return f"Sep 19 {clock} {host} sshd[{pid}]: {msg}"

    lines = []
    # 单源爆破（web01 / web02 各 10 次，同一 IP）
    for i in range(10):
        lines.append(sshd(f"07:00:{i:02d}", f"Failed password for invalid user admin from 203.0.113.7 port 51{i:03d} ssh2"))
    for i in range(10):
        lines.append(sshd(f"07:01:{i:02d}", f"Failed password for invalid user admin from 203.0.113.7 port 52{i:03d} ssh2", host="web02"))
    # 失败后成功
    for i in range(4):
        lines.append(sshd(f"09:00:0{i}", f"Failed password for deploy from 192.0.2.9 port 6000{i} ssh2"))
    lines.append(sshd("09:00:09", "Accepted password for deploy from 192.0.2.9 port 60009 ssh2"))
    # 非工作时段成功
    lines.append(sshd("03:20:00", "Accepted publickey for deploy from 192.0.2.20 port 2200 ssh2"))
    # Web 撞库 + 目录穿越
    for i in range(22):
        lines.append(f'203.0.113.50 - - [19/Sep/2026:10:00:{i:02d} +0800] "GET /login HTTP/1.1" 401 512 "-" "curl/8.0"')
    lines.append('203.0.113.50 - - [19/Sep/2026:10:05:00 +0800] "GET /static/../../etc/passwd HTTP/1.1" 404 512 "-" "curl/8.0"')
    # 正常业务（不应产生告警）：白天的成功登录
    lines.append(sshd("11:30:00", "Accepted publickey for ci from 10.0.0.8 port 33000 ssh2"))

    if dirty:
        lines.append("!!! log rotation marker: no parseable format here")
        lines.append('{"event": "login_failed", "host": "api01", "user": "ops", "src_ip": "198.51.100.77"}')

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ─────────────────────────────── 子命令 ───────────────────────────────
def cmd_parse(args) -> int:
    files = expand_targets(args.targets)
    if not files:
        print("未找到可读的日志文件", file=sys.stderr)
        return EXIT_USAGE
    lines, read_errors = read_lines(files)
    events, coverage = parse_lines(lines, fallback_host=args.host or files[0].stem,
                                   year=args.year,
                                   source_name=",".join(p.name for p in files[:3]))
    print(f"{'TIME':<20} {'HOST':<8} {'SOURCE':<7} {'ACTION':<14} {'USER':<8} SRC_IP")
    print("-" * 78)
    for event in events:
        time_text = event.ts.strftime("%Y-%m-%d %H:%M:%S") if event.ts else "??"
        print(f"{time_text:<20} {event.host:<8} {event.source:<7} {event.action:<14} "
              f"{(event.user or '-'):<8} {mask_ip(event.src_ip)}")
    print()
    print(f"行数 {coverage.lines_total} / 解析 {coverage.parsed} / 无法识别 {coverage.unparsed} / "
          f"缺时间戳 {coverage.no_timestamp} / 去重 {coverage.deduped} / 乱序 {coverage.out_of_order}")
    for error in read_errors:
        print(f"[read_error] {error}")
    return EXIT_OK


def cmd_analyze(args) -> int:
    params = {
        "brute_window": args.brute_window, "brute_threshold": args.brute_threshold,
        "fts_window": args.fts_window, "fts_min_failures": args.fts_min_failures,
        "work_start": args.work_start, "work_end": args.work_end,
        "web_window": args.web_window, "web_threshold": args.web_threshold,
    }
    report, read_errors = analyze_files(args.targets, params=params,
                                        baseline=load_baseline(args.baseline), year=args.year,
                                        fallback_host=args.host)
    if report is None:
        print("；".join(read_errors), file=sys.stderr)
        return EXIT_USAGE

    if args.format == "json":
        text = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
    else:
        text = render_markdown(report, args.targets, read_errors)

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"报告已写入 {args.output}")
    else:
        print(text)
    print(f"# {summarize(report)}", file=sys.stderr)
    return gate_exit_code(report, read_errors, args.fail_on)


def cmd_lab(args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = build_lab(Path(tmp) / "logs", dirty=args.dirty)
        report, read_errors = analyze_files([str(path)], params={}, baseline=None, year=2026)
        if args.format == "json":
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(render_markdown(report, [str(path)], read_errors))
        code = gate_exit_code(report, read_errors, args.fail_on)
        print(f"# {summarize(report)}", file=sys.stderr)
        print(f"# lab 退出码 = {code}（0=通过 3=有告警 4=覆盖不全）", file=sys.stderr)
        return code


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        clean = build_lab(Path(tmp) / "clean")
        report, read_errors = analyze_files([str(clean)], year=2026)
        assert report is not None and not read_errors

        detectors = {a.detector for a in report.alerts}
        for detector in ("brute_force_single_source", "failed_then_success",
                         "off_hours_success", "web_auth_abuse", "path_traversal_probe"):
            assert detector in detectors, f"缺少告警: {detector}（实际 {sorted(detectors)}）"

        # 正常业务登录不应产生"新来源"之外的噪音（低危启发式允许存在）
        assert all(a.count >= 1 for a in report.alerts)

        # 1) 覆盖完整 → 门禁按阈值判
        assert coverage_ok(report) is True, report.coverage.gaps
        assert gate_exit_code(report, fail_on="high") == EXIT_GATE
        assert gate_exit_code(report, fail_on="critical") == EXIT_OK

        # 2) 脏数据 → 覆盖不全优先于"有告警"
        dirty_path = build_lab(Path(tmp) / "dirty", dirty=True)
        dirty, _ = analyze_files([str(dirty_path)], year=2026)
        assert dirty.coverage.unparsed == 1 and dirty.coverage.no_timestamp == 1
        assert gate_exit_code(dirty, fail_on="high") == EXIT_COVERAGE
        md = render_markdown(dirty, [str(dirty_path)])
        assert "覆盖声明" in md and "没有参与判定" in md

        # 3) 空输入也必须算覆盖缺口
        empty = Path(tmp) / "empty.log"
        empty.write_text("", encoding="utf-8")
        empty_report, _ = analyze_files([str(empty)], year=2026)
        assert gate_exit_code(empty_report, fail_on="high") == EXIT_COVERAGE

        # 4) 阈值回显：自定义阈值必须出现在报告参数段
        custom, _ = analyze_files([str(clean)], params={"brute_threshold": 50}, year=2026)
        assert custom.parameters["brute_threshold"] == 50
        assert "本次自定义" in render_markdown(custom, [str(clean)])

        # 5) baseline 生效：把已知来源写进基线，不再报"基线之外来源"
        baseline = {"web01|deploy": ["192.0.2.9", "192.0.2.20"]}
        with_baseline, _ = analyze_files([str(clean)], baseline=baseline, year=2026)
        assert not [a for a in with_baseline.alerts
                    if a.detector == "login_from_unexpected_source"], "基线内的来源不应告警"
        assert not [a for a in with_baseline.alerts
                    if a.detector == "login_from_single_source" and "deploy" in a.subject], \
            "已建基线的账号不应再走低置信度启发式"
        # 反向验证：基线只放一个 IP 时，另一个来源仍应被标出
        partial, _ = analyze_files([str(clean)], baseline={"web01|deploy": ["192.0.2.20"]}, year=2026)
        assert [a for a in partial.alerts if a.detector == "login_from_unexpected_source"], \
            "基线之外的来源必须告警"

        # 6) 报告脱敏：不得出现完整 IP
        text = render_markdown(report, [str(clean)])
        for ip in ("203.0.113.7", "192.0.2.9", "203.0.113.50"):
            assert ip not in text, f"报告泄露完整 IP: {ip}"

        # 7) 目录展开：目录下 *.log 应被发现
        assert expand_targets([str(Path(tmp) / "clean")]), "目录展开失败"

        # 8) 排序：最高优先级在最前
        scores = [priority(a.severity, a.confidence) for a in report.alerts]
        assert scores == sorted(scores, reverse=True)

        # 9) JSON 可序列化
        payload = json.loads(json.dumps(report.to_dict(), ensure_ascii=False))
        assert payload["summary"]["alerts"] == len(report.alerts)
        assert payload["coverage"]["complete"] is True

        # 10) detect 覆盖统计字段齐全
        assert isinstance(report.coverage, LogCoverage)
        assert Counter(a.detector for a in report.alerts).most_common(1)[0][1] >= 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="log-analyzer",
        description="离线只读安全日志分析器（Day 160）。告警为复核线索，非攻击结论。")
    parser.add_argument("--self-test", action="store_true", help="运行自测并退出")
    sub = parser.add_subparsers(dest="command")

    p_parse = sub.add_parser("parse", help="只看解析与标准化结果")
    p_parse.add_argument("targets", nargs="+")
    p_parse.add_argument("--year", type=int, default=2026)
    p_parse.add_argument("--host", default=None, help="日志无主机名时的回退主机名")

    p_analyze = sub.add_parser("analyze", help="完整检测并输出报告")
    p_analyze.add_argument("targets", nargs="+")
    p_analyze.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_analyze.add_argument("--fail-on", choices=["low", "medium", "high", "critical"], default="high")
    p_analyze.add_argument("--baseline", default=None)
    p_analyze.add_argument("--output", default=None)
    p_analyze.add_argument("--year", type=int, default=2026)
    p_analyze.add_argument("--host", default=None, help="日志无主机名时的回退主机名")
    p_analyze.add_argument("--brute-window", type=int, default=300)
    p_analyze.add_argument("--brute-threshold", type=int, default=8)
    p_analyze.add_argument("--fts-window", type=int, default=900)
    p_analyze.add_argument("--fts-min-failures", type=int, default=3)
    p_analyze.add_argument("--work-start", type=int, default=8)
    p_analyze.add_argument("--work-end", type=int, default=20)
    p_analyze.add_argument("--web-window", type=int, default=600)
    p_analyze.add_argument("--web-threshold", type=int, default=20)

    p_lab = sub.add_parser("lab", help="生成合成日志并分析（临时目录）")
    p_lab.add_argument("--dirty", action="store_true", help="混入乱码行与缺时间戳行")
    p_lab.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_lab.add_argument("--fail-on", choices=["low", "medium", "high", "critical"], default="high")

    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        print("SELF-TEST OK")
        return EXIT_OK
    if args.command == "parse":
        return cmd_parse(args)
    if args.command == "analyze":
        return cmd_analyze(args)
    if args.command == "lab":
        return cmd_lab(args)

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
