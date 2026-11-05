"""实战场景：把规则引擎 + 报告生成整合成一个 CLI 审计工具箱（Day 159）。

整合要点（为什么 CLI 不是"随手包一层 argparse"）：

1. **子命令边界清晰**：`scan` 只扫描；`report` 只把已有 JSON 重新渲染；
   `rules` 只打印规则库；`lab` 在临时目录生成演示项目。
   扫描与报告分离，意味着"复核人员可以用同一个 JSON 换不同格式输出"，
   也意味着 CI 里扫描与出报告的权限可以不同。

2. **退出码是机器接口**：CI 不读你的 Markdown，只读退出码。
   0=通过 / 3=命中达到阈值 / 4=覆盖不全 / 2=用法错误。
   覆盖不全排在"命中"之前，因为不可信的结果不配当门禁依据。

3. **门禁阈值可配**：`--fail-on high`，避免一条低危噪音卡死整条流水线
   （门禁太严的后果是所有人都在加 `|| true`，等于没有门禁）。

4. **baseline 是一等公民**：`--baseline ignore.txt`，抑制项单独计数并列出。

5. **零网络、零写操作**：`lab` 的所有文件都写在临时目录，退出即清理。

运行：
    python3 03-audit-toolkit.py lab
    python3 03-audit-toolkit.py lab --format markdown
    python3 03-audit-toolkit.py rules
    python3 03-audit-toolkit.py scan ./your-project --fail-on high
    python3 03-audit-toolkit.py report report.json --format markdown
    python3 03-audit-toolkit.py --self-test
"""

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

from audit_core import AuditReport, Coverage, Finding, local_rules, scan_path, summarize


# 复用 02 的报告函数。文件名带连字符不能直接 import，
# 用 importlib 从同目录加载（仓库里每个文件都要能独立运行）。
def _load_report_module():
    path = Path(__file__).with_name("02-report-builder.py")
    spec = importlib.util.spec_from_file_location("report_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


report_builder = _load_report_module()
render_markdown = report_builder.render_markdown
gate_exit_code = report_builder.gate_exit_code
load_baseline = report_builder.load_baseline

EXIT_OK, EXIT_USAGE, EXIT_GATE, EXIT_COVERAGE = 0, 2, 3, 4

LAB_FILES = {
    "app/settings.py": (
        "# 演示配置（占位值）\n"
        "DEBUG = True\n"
        'DB_PASSWORD = "ChangeMe-Demo-123"\n'
        "requests.get(url, verify=False)\n"
        "subprocess.run(cmd, shell=True)\n"
    ),
    "app/legacy_client.py": (
        'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n'   # AWS 官方文档示例值
        'TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkZW1vIn0.abcdefghijklmnop"\n'
    ),
    "requirements.txt": "flask==3.0.0\nrequests\n",
    "deploy/pip.conf": "[global]\nindex-url = http://pypi.demo.local/simple\n",
    "deploy/fix_perms.sh": "#!/bin/sh\nchmod 777 /srv/app/uploads\n",
    "ids/private.pem": "-----BEGIN RSA PRIVATE KEY-----\nPLACEHOLDER-NOT-A-REAL-KEY\n",
    "docs/notes.md": "内部说明：password = \"example-value\" 仅为示例，切勿照抄。\n",
}

# 演示 baseline：把文档误报和已接受的权限问题登记为已抑制项
LAB_BASELINE = (
    "# 已知并接受的风险（需评审 + 复查日期）\n"
    "secret_hardcoded_credential:docs/notes.md\n"
    "world_writable_chmod:deploy/fix_perms.sh\n"
)


def build_lab(root: Path) -> None:
    """在临时目录搭建演示项目（含一份 baseline）。"""
    for rel, content in LAB_FILES.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (root / "ignore.txt").write_text(
        "# 已知并接受的风险（需评审 + 复查日期）\n"
        "secret_hardcoded_credential:docs/notes.md\n"
        "world_writable_chmod:deploy/fix_perms.sh\n",
        encoding="utf-8",
    )


def cmd_scan(args) -> int:
    baseline = load_baseline(args.baseline)
    try:
        report = scan_path(
            args.target,
            max_files=args.max_files,
            max_bytes=args.max_bytes,
            baseline=baseline,
        )
    except FileNotFoundError as exc:
        print(f"目标不存在: {exc}", file=sys.stderr)
        return EXIT_USAGE

    payload = report.to_dict()
    if args.format == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = render_markdown(report, f"安全审计报告 — {Path(report.root).name}")

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"报告已写入 {args.output}")
    else:
        print(text)

    print(f"# {summarize(report)}", file=sys.stderr)
    return gate_exit_code(report, args.fail_on)


def cmd_report(args) -> int:
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return EXIT_OK

    # 从 JSON 还原最小报告对象：证明"JSON 是唯一可信中间产物"
    coverage = Coverage(**{k: v for k, v in payload["coverage"].items()
                           if k in {"files_scanned", "bytes_read", "skipped",
                                    "errors", "truncated"}})
    findings = []
    for item in payload["findings"]:
        item = {k: v for k, v in item.items() if k not in {"priority", "triage_band"}}
        findings.append(Finding(**item))
    suppressed = [Finding(**{k: v for k, v in item.items()
                             if k not in {"priority", "triage_band"}})
                  for item in payload.get("suppressed", [])]
    report = AuditReport(
        root=payload["root"],
        findings=findings,
        suppressed=suppressed,
        coverage=coverage,
        rules_evaluated=payload.get("rules_evaluated", []),
    )
    print(render_markdown(report, "安全审计报告（由 JSON 重新渲染）"))
    return EXIT_OK


def cmd_rules(_args) -> int:
    print(f"{'RULE':<30} {'SEV':<9} {'CONF':<7} {'CAT':<8} CWE")
    print("-" * 78)
    for rule in local_rules():
        print(f"{rule.id:<30} {rule.severity:<9} {rule.confidence:<7} "
              f"{rule.category:<8} {rule.cwe}")
    print(f"\n共 {len(local_rules())} 条规则（教学基线，按业务调整）。")
    return EXIT_OK


def cmd_lab(args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "demo-project"
        root.mkdir()
        build_lab(root)
        args.target = str(root)
        args.baseline = str(root / "ignore.txt")
        args.output = None
        args.max_files, args.max_bytes = 1000, 1 << 20
        code = cmd_scan(args)
        print(f"\n# 演示项目退出码 = {code}（0=通过 3=命中达到阈值 4=覆盖不全）",
              file=sys.stderr)
        return code


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "demo-project"
        root.mkdir()
        build_lab(root)

        baseline = load_baseline(str(root / "ignore.txt"))
        assert len(baseline) == 2, baseline

        report = scan_path(root, baseline=baseline)
        rule_ids = {f.rule_id for f in report.findings}

        # 1) 关键类别都要命中（凭据 / 配置 / 代码 / 供应链）
        for rule_id in ("secret_private_key", "secret_cloud_access_key",
                        "config_debug_enabled", "tls_verify_disabled",
                        "shell_exec_enabled", "insecure_package_index"):
            assert rule_id in rule_ids, f"未命中: {rule_id}；实际: {sorted(rule_ids)}"

        # 2) baseline 命中进入 suppressed，且不在 findings 里
        assert {f.rule_id for f in report.suppressed} == {
            "secret_hardcoded_credential", "world_writable_chmod"
        }, {f.rule_id for f in report.suppressed}

        # 3) 报告脱敏：明文一个都不能出现
        md = render_markdown(report)
        payload = json.dumps(report.to_dict(), ensure_ascii=False)
        for raw in ("ChangeMe-Demo-123", "AKIAIOSFODNN7EXAMPLE", "PLACEHOLDER-NOT-A-REAL-KEY"):
            assert raw not in md, f"Markdown 泄露: {raw}"
            assert raw not in payload, f"JSON 泄露: {raw}"

        # 4) 门禁退出码
        assert gate_exit_code(report, "critical") == 3, "存在 critical 命中应为 3"
        assert gate_exit_code(report, "high") == 3
        assert gate_exit_code(report, "critical") != 0

        # 5) 覆盖完整（这个样例目录没有跳过/错误）
        assert report.coverage.complete is True, report.coverage.gaps

        # 6) 规则库自检：id 唯一、字段合法
        rules = local_rules()
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids)) >= 13
        assert all(r.why and r.remediation for r in rules), "规则必须带 why/remediation"

        # 7) JSON → 再渲染的通路可用（report 子命令的核心逻辑）
        with tempfile.TemporaryDirectory() as tmp2:
            out = Path(tmp2) / "report.json"
            out.write_text(json.dumps(report.to_dict(), ensure_ascii=False), encoding="utf-8")
            payload2 = json.loads(out.read_text(encoding="utf-8"))
            assert payload2["summary"]["findings"] == len(report.findings)

        return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="audit-toolkit",
        description="离线只读安全审计工具箱（Day 159）。命中为复核线索，非漏洞结论。",
    )
    parser.add_argument("--self-test", action="store_true", help="运行自测并退出")
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="扫描本地目录/文件")
    p_scan.add_argument("target")
    p_scan.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_scan.add_argument("--fail-on", choices=["low", "medium", "high", "critical"],
                        default="high", help="门禁阈值（默认 high）")
    p_scan.add_argument("--baseline", default=None, help="baseline 文件路径")
    p_scan.add_argument("--max-files", type=int, default=1000)
    p_scan.add_argument("--max-bytes", type=int, default=1 << 20)
    p_scan.add_argument("--output", default=None, help="报告输出文件（默认打印到 stdout）")

    p_report = sub.add_parser("report", help="把已有 JSON 报告重新渲染")
    p_report.add_argument("input")
    p_report.add_argument("--format", choices=["markdown", "json"], default="markdown")

    sub.add_parser("rules", help="打印规则库")

    p_lab = sub.add_parser("lab", help="在临时目录生成演示项目并扫描")
    p_lab.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_lab.add_argument("--fail-on", choices=["low", "medium", "high", "critical"],
                       default="high")

    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        print("SELF-TEST OK")
        return EXIT_OK

    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "rules":
        return cmd_rules(args)
    if args.command == "lab":
        return cmd_lab(args)

    parser.print_help()
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
