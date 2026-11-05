#!/usr/bin/env python3
"""实战：安全审计工具箱 CLI（Day 162 — 资产面）。

把三个模块串成一条流水线，输出统一报告：

    端口扫描  →  目录爆破  →  指纹识别  →  统一 Finding  →  JSON / Markdown

子命令：

    python3 03-audit-toolkit.py lab
        启动本机实验服务（HTTP，仅回环）+ 可选 429 演示，跑完整流水线

    python3 03-audit-toolkit.py ports --hosts 127.0.0.1 --ports 8080-8082
        只做端口扫描（三态 + 服务推断来源）

    python3 03-audit-toolkit.py dirs --base http://127.0.0.1:8080
        只做目录爆破（软 404 基线 + 状态码分类 + 429 退避）

    python3 03-audit-toolkit.py fingerprint --base http://127.0.0.1:8080
        只做指纹识别（信号 → 打分 → 置信度）

    python3 03-audit-toolkit.py scan --hosts 127.0.0.1 --ports 8080 --base http://127.0.0.1:8080
        完整流水线（推荐入口）

    python3 03-audit-toolkit.py --self-test

退出码：2=范围/参数错误   4=覆盖不完整(429/filtered/error)   3=有 P0/P1   0=干净完成

⚠️ 边界：只发只读 GET；不登录、不带 Cookie、不爆破、不上传、不修改任何数据；
   词表内置 30 条公开路径；默认 5 请求/秒；只允许授权范围内的目标。
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from audit_core import (
    DEFAULT_WORDS,
    AuthorizationError,
    Baseline,
    Finding,
    LabHTTP,
    Scope,
    ScopeError,
    build_baseline,
    build_report,
    collect_signals,
    dir_brute,
    fetch,
    findings_from_dirs,
    findings_from_ports,
    findings_from_tech,
    render_markdown,
    sanitize,
    scan_ports,
    score_signals,
)

DAY_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT = DAY_DIR / "out"


def lab_scope(port: int, base: str | None = None) -> Scope:
    return Scope(networks=["127.0.0.1/32"], ports=[(8000, 8099)],
                 http_bases=[f"http://127.0.0.1:{port}"] if port else ([base] if base else []),
                 ticket="LAB-SELF-002", note="self-owned loopback lab only")


def run_pipeline(scope: Scope, hosts: list[str], ports_spec: str, base: str | None,
                 rate: float, out_dir: Path, tag: str, verbose: bool = True) -> int:
    from audit_core import parse_port_spec
    out_dir.mkdir(parents=True, exist_ok=True)
    ports_list = parse_port_spec(ports_spec)

    # ── 阶段 1：端口扫描 ──
    port_results = scan_ports(hosts, ports_list, scope, timeout=0.5, rate=200.0)
    if verbose:
        open_ports = [r.key for r in port_results if r.state == "open"]
        print(f"[ports]  目标 {len(port_results)} 个 → open {len(open_ports)} "
              f"({', '.join(open_ports) or '无'})")

    # ── 阶段 2：目录爆破 ──
    entries: list = []
    baseline = Baseline()
    coverage: dict = {"total": 0, "completed": 0, "throttled": 0, "errors": 0,
                      "backoff_events": 0, "max_backoff_s": 0.0, "incomplete": False}
    if base:
        if verbose:
            print(f"[dirs]   基线 status=? len=? 词表 {len(DEFAULT_WORDS)} 条 @ {rate} 请求/秒")
        t0 = time.perf_counter()
        entries, baseline, coverage = dir_brute(base, DEFAULT_WORDS, scope, rate=rate)
        if verbose:
            print(f"[dirs]   完成 {coverage['completed']}/{coverage['total']}"
                  f"｜限速 {coverage['throttled']}｜退避事件 {coverage['backoff_events']}"
                  f"｜耗时 {time.perf_counter() - t0:.2f}s")
            print(f"[dirs]   基线：status={baseline.status} len={baseline.length}"
                  f"（随机路径实测，用于识别软 404）")
    else:
        print("[dirs]   已跳过（未提供 --base）")

    # ── 阶段 3：指纹识别 ──
    guesses = []
    main_res = None
    if base:
        main_res = fetch(base)
        probes = {p: fetch(f"{base.rstrip('/')}/{p}")
                  for p in ("server-status", "backup.zip")}
        signals = collect_signals(main_res, probes)
        guesses = score_signals(signals)
        if verbose:
            print(f"[fp]     信号 {len(signals)} 条 → 推断 {len(guesses)} 项："
                  + ", ".join(f"{g.tech}({g.score}/{g.confidence})" for g in guesses))

    # ── 阶段 4：汇总与报告 ──
    findings: list[Finding] = findings_from_ports(port_results)
    if entries:
        findings += findings_from_dirs(entries, coverage)
    if guesses and main_res is not None:
        findings += findings_from_tech(guesses, main_res)

    params = {"ports_spec": ports_spec, "dir_rate": rate, "words": len(DEFAULT_WORDS),
              "timeout_s": 0.5, "anon_only": True}
    report = build_report(scope, port_results, entries, baseline, coverage,
                          guesses, findings, params)
    report["mode"] = tag
    (out_dir / f"{tag}-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"{tag}-report.md").write_text(render_markdown(report), encoding="utf-8")

    if verbose:
        prio_count: dict[str, int] = {}
        for f in findings:
            prio_count[f.priority] = prio_count.get(f.priority, 0) + 1
        print(f"[find]   发现 {len(findings)} 条：{prio_count}")
        for f in sorted(findings, key=lambda x: x.priority)[:6]:
            print(f"         {f.priority} {f.key:<18} {f.title}")
        print(f"[report] {out_dir / (tag + '-report.json')}")
        print(f"[exit]   {report['exit_code']}"
              f"{'（覆盖不完整 → 本轮无结论）' if report['coverage']['incomplete'] else ''}")
    return report["exit_code"]


def cmd_lab(args) -> int:
    port = args.http_port
    with LabHTTP(port=port, throttle_after=args.throttle_after):
        print(f"[lab]    实验 HTTP 服务已启动：http://127.0.0.1:{port}"
              f"{'（429 限速演示：第 ' + str(args.throttle_after) + ' 个请求后开始限速）' if args.throttle_after else ''}")
        scope = lab_scope(port)
        return run_pipeline(scope, ["127.0.0.1"], args.ports, f"http://127.0.0.1:{port}",
                            args.rate, Path(args.out), "day162-lab")


def cmd_ports(args) -> int:
    scope = load_scope(args, hosts=args.hosts)
    from audit_core import parse_port_spec
    results = scan_ports(args.hosts, parse_port_spec(args.ports), scope, timeout=0.5)
    print(f"{'目标':<20}{'状态':<11}{'服务':<12}{'来源':<11}{'耗时(ms)':>9}")
    for r in results:
        print(f"{r.key:<20}{r.state:<11}{r.service:<12}{r.service_source or '-':<11}{r.elapsed_ms:>9}")
    stats = {s: sum(1 for r in results if r.state == s)
             for s in ("open", "closed", "filtered", "error")}
    print(f"统计：{stats}")
    findings = findings_from_ports(results)
    return exit_with(findings, results, None)


def cmd_dirs(args) -> int:
    scope = load_scope(args, base=args.base)
    entries, baseline, coverage = dir_brute(args.base, DEFAULT_WORDS, scope, rate=args.rate)
    print(f"基线：status={baseline.status} len={baseline.length}（随机路径实测）")
    print(f"{'路径':<22}{'状态':<6}{'分类':<14}{'长度':>6}")
    for e in entries:
        print(f"/{e.word:<21}{e.status:<6}{e.category:<14}{e.length:>6}")
    print(f"完成 {coverage['completed']}/{coverage['total']}"
          f"｜被限速 {coverage['throttled']}｜错误 {coverage['errors']}")
    findings = findings_from_dirs(entries, coverage)
    return exit_with(findings, [], coverage)


def cmd_fingerprint(args) -> int:
    scope = load_scope(args, base=args.base)
    scope.check_url(args.base)
    main_res = fetch(args.base)
    probes = {p: fetch(f"{args.base.rstrip('/')}/{p}")
              for p in ("server-status", "backup.zip")}
    signals = collect_signals(main_res, probes)
    guesses = score_signals(signals)
    print(f"响应：status={main_res.status} len={main_res.length} "
          f"Server={main_res.headers.get('Server')!r}")
    print(f"\n{'推断':<16}{'分值':>6}  {'置信度':<9}证据")
    for g in guesses:
        print(f"{g.tech:<16}{g.score:>6}  {g.confidence:<9}{'; '.join(g.evidence[:2])}")
    print("\n★ 所有信号都由目标控制，可被任意伪造；单信号置信度上限为『低』。")
    print("★ 提升置信度只能靠多信号交叉，报告里必须写明『需要人工确认』。")
    findings = findings_from_tech(guesses, main_res)
    return exit_with(findings, [], None)


def exit_with(findings, ports, coverage) -> int:
    from audit_core import exit_code
    code = exit_code(findings, ports, coverage)
    if any(p.state in ("filtered", "error") for p in ports):
        print("⚠️ 存在 filtered/error 目标 → 覆盖不完整，退出码 4。")
    if coverage and coverage.get("incomplete"):
        print("⚠️ 目录爆破未完成（429/错误）→ 本轮无结论，退出码 4。")
    print(f"退出码：{code}")
    return code


def load_scope(args, hosts=None, base=None) -> Scope:
    if getattr(args, "scope", None):
        return Scope.load(args.scope)
    if hosts:
        hosts = list(hosts)
    # 默认实验范围（仅回环）
    return Scope(networks=["127.0.0.1/32"], ports=[(8000, 8099)],
                 http_bases=[base] if base else [],
                 ticket="LAB-SELF-002")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Day 162 安全审计工具箱（仅限授权目标）",
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    sub = ap.add_subparsers(dest="cmd")

    p_lab = sub.add_parser("lab", help="启动实验服务并跑完整流水线")
    p_lab.add_argument("--http-port", type=int, default=8080)
    p_lab.add_argument("--ports", default="8080-8082")
    p_lab.add_argument("--rate", type=float, default=20.0)
    p_lab.add_argument("--throttle-after", type=int, default=None,
                       help="第 N 个请求后返回 429（演示退避）")

    p_ports = sub.add_parser("ports", help="端口扫描")
    p_ports.add_argument("--hosts", nargs="+", required=True)
    p_ports.add_argument("--ports", required=True)
    p_ports.add_argument("--scope", default=None)

    p_dirs = sub.add_parser("dirs", help="目录爆破")
    p_dirs.add_argument("--base", required=True)
    p_dirs.add_argument("--rate", type=float, default=5.0)
    p_dirs.add_argument("--scope", default=None)

    p_fp = sub.add_parser("fingerprint", help="指纹识别")
    p_fp.add_argument("--base", required=True)
    p_fp.add_argument("--scope", default=None)

    p_scan = sub.add_parser("scan", help="完整流水线")
    p_scan.add_argument("--hosts", nargs="+", required=True)
    p_scan.add_argument("--ports", default="8080")
    p_scan.add_argument("--base", default=None)
    p_scan.add_argument("--rate", type=float, default=5.0)
    p_scan.add_argument("--scope", default=None)
    p_scan.add_argument("--tag", default="day162-scan")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.self_test:
        return _self_test()
    try:
        if args.cmd == "lab":
            return cmd_lab(args)
        if args.cmd == "ports":
            return cmd_ports(args)
        if args.cmd == "dirs":
            return cmd_dirs(args)
        if args.cmd == "fingerprint":
            return cmd_fingerprint(args)
        if args.cmd == "scan":
            scope = load_scope(args, hosts=args.hosts, base=args.base)
            return run_pipeline(scope, args.hosts, args.ports, args.base,
                                args.rate, Path(args.out), args.tag)
    except AuthorizationError as exc:
        print(f"⛔ AuthorizationError: {exc}")
        print("   （越界是策略拒绝：不重试、不跳过、整轮终止）")
        return 2
    except ScopeError as exc:
        print(f"⛔ ScopeError: {exc}")
        return 2
    ap.print_help()
    return 0


def _self_test() -> int:
    import contextlib
    import io

    with LabHTTP(port=0) as lab:
        base = f"http://127.0.0.1:{lab.port}"
        scope = Scope(networks=["127.0.0.1/32"], ports=[(lab.port, lab.port)],
                      http_bases=[base], ticket="SELF-TEST")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_pipeline(scope, ["127.0.0.1"], str(lab.port), base, 500.0,
                                DEFAULT_OUT, "day162-selftest")
        out = buf.getvalue()
        assert code == 3, (code, out)      # 有 P0/P1（backup_artifact / cleartext）

        report = json.loads((DEFAULT_OUT / "day162-selftest-report.json")
                            .read_text(encoding="utf-8"))
        assert report["coverage"]["ports"]["open"] == 1, report["coverage"]
        assert report["baseline"]["status"] == 200, report["baseline"]
        keys = {f["key"] for f in report["findings"]}
        assert {"protected_path", "backup_artifact", "tech_fingerprint"} <= keys, keys
        techs = {g["tech"]: g for g in report["fingerprint"]}
        assert techs["lab-cms"]["confidence"] == "medium", techs
        assert "覆盖与结论可信度" in render_markdown(report)

        # 越界基址 → 退出码 2
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            bad = main(["dirs", "--base", "http://192.0.2.1:8080", "--rate", "500"])
        assert bad == 2, (bad, buf2.getvalue())
        assert "AuthorizationError" in buf2.getvalue()

        # 429 → 覆盖不完整，退出码 4
    with LabHTTP(port=0, throttle_after=2) as lab2:
        base2 = f"http://127.0.0.1:{lab2.port}"
        scope2 = Scope(networks=["127.0.0.1/32"], ports=[(lab2.port, lab2.port)],
                       http_bases=[base2], ticket="SELF-TEST-429")
        buf3 = io.StringIO()
        with contextlib.redirect_stdout(buf3):
            code3 = run_pipeline(scope2, ["127.0.0.1"], str(lab2.port), base2, 500.0,
                                 DEFAULT_OUT, "day162-selftest429")
        assert code3 == 4, (code3, buf3.getvalue())
        rep3 = json.loads((DEFAULT_OUT / "day162-selftest429-report.json")
                          .read_text(encoding="utf-8"))
        assert rep3["coverage"]["incomplete"] is True

    # 不可判定端口 → 退出码 4
    buf4 = io.StringIO()
    with contextlib.redirect_stdout(buf4):
        code4 = run_pipeline(Scope(networks=["192.0.2.0/24"], ports=[(8080, 8082)],
                                   http_bases=[], ticket="SELF-TEST-FAR"),
                             ["192.0.2.1"], "8080-8082", None, 500.0,
                             DEFAULT_OUT, "day162-selftest-far")
    assert code4 == 4, (code4, buf4.getvalue())

    # 输出脱敏：报告里不应出现原始响应体的控制字符
    assert "\x1b" not in sanitize("a\x1b[31mb")
    print("SELF-TEST OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
