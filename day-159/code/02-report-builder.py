"""进阶用法与常见陷阱：把命中变成**可复核的报告**（Day 159）。

扫描只是前半程。真正决定审计工具好不好用的，是报告：
复核人员只看到报告，看不到你的扫描过程。本文件演示报告生成的六个陷阱，
以及每个陷阱对应的正确写法。

陷阱 1：报告里出现绝对路径 / 主机名 / 用户名
    → 报告会被转发到外部（供应商、客户）。绝对路径会泄露内部目录结构。
    → 正确做法：报告里只保留**相对路径**，根目录单独一行说明。

陷阱 2：把命中的原始行拼进报告
    → 那就等于把明文口令抄进报告。始终只输出 `masked` + `evidence_sha256`。

陷阱 3：覆盖不全时写"未发现问题"
    → 跳过的文件里可能就是问题所在。`Coverage.complete == False` 时，
      报告必须把 gaps 打在**最显眼**的位置（摘要之后、明细之前）。

陷阱 4：Markdown 表格不转义
    → 文件名/证据里的 `|` 会把表格切碎。渲染前统一 escape。

陷阱 5：空结果什么都不输出
    → CI 里"没有输出"和"任务没跑"无法区分。空结果也要有摘要行。

陷阱 6：baseline 直接过滤掉命中
    → 抑制项被无声丢弃后，没人知道"我们接受过多少风险"。
      必须单独计数并列出（哪怕只列 id 和位置）。

运行：
    python3 02-report-builder.py              # 在临时目录搭建样例项目并生成报告
    python3 02-report-builder.py --self-test
"""

import argparse
import json
import tempfile
from pathlib import Path

from audit_core import Coverage, priority, scan_path, summarize


def escape_md(text: str) -> str:
    """转义 Markdown 表格/正文里的特殊字符，避免报告被文件名切碎。"""
    return str(text).replace("|", "\\|").replace("`", "\\`").replace("\n", " ")


def sort_findings(findings) -> list:
    """排序规则：优先级降序 → 位置。为什么不用字母序？因为复核是按优先级做的。"""
    return sorted(
        findings,
        key=lambda f: (-priority(f.severity, f.confidence), f.path, f.line),
    )


def load_baseline(path: str | None) -> list:
    """读取 baseline 文件：每行 `rule_id:path` 或 `rule_id:sha256`，`#` 开头为注释。

    为什么 baseline 要写进版本控制？因为它是一张"我们已知并接受的风险清单"，
    需要评审、需要定期复查（否则它会变成永久消音器）。
    """
    if not path:
        return []
    items = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def coverage_warning(report) -> str:
    """覆盖声明。完整时也输出一行，证明"这份报告确实检查了覆盖情况"。"""
    if report.coverage.complete:
        return "- 覆盖：完整（无跳过、无读取错误、未达到文件上限）"
    gaps = "、".join(escape_md(g) for g in report.coverage.gaps) or "未知"
    return (
        "- 覆盖：**不全** ⚠️\n"
        f"  - 缺口：{gaps}\n"
        "  - 含义：上述范围内的文件**没有被检查**，本次报告不能用于得出"
        "「未发现问题」的结论。"
    )


def render_markdown(report, title: str = "安全审计报告") -> str:
    """人类可读报告。注意所有动态内容都过 escape_md。"""
    sev = report.by_severity()
    band = report.by_band()
    lines = [
        f"# {title}",
        "",
        f"- 目标根目录：`{escape_md(Path(report.root).name or '.')}`（报告只保留末级目录名）",
        f"- 评估规则数：{len(report.rules_evaluated)}",
        f"- 命中：{len(report.findings)} 条（其中被 baseline 抑制 {len(report.suppressed)} 条）",
        f"- 严重度分布："
        + "、".join(f"{k}={v}" for k, v in sev.items() if v),
        f"- 优先级分布：P0={band['P0']} P1={band['P1']} P2={band['P2']} P3={band['P3']}",
        coverage_warning(report),
        "",
    ]

    if not report.findings:
        lines += [
            "## 命中明细",
            "",
            "无命中。**注意**：这只说明在内置规则集下没有匹配到模式，"
            "不等于目标没有安全问题。",
            "",
        ]
    else:
        lines += ["## 命中明细（按优先级排序）", ""]
        for f in sort_findings(report.findings):
            lines += [
                f"### [{f.band}] {f.rule_id} — {escape_md(f.title)}",
                "",
                f"- 位置：`{escape_md(f.path)}:{f.line}`",
                f"- 证据：`{escape_md(f.masked)}`（sha256:{f.evidence_sha256}）",
                f"- 严重度 / 置信度：{f.severity} / {f.confidence}（{escape_md(f.cwe)}）",
                f"- 为什么是问题：{escape_md(f.why)}",
                f"- 修复建议：{escape_md(f.remediation)}",
                "",
            ]

    if report.suppressed:
        lines += [
            "## 已抑制（baseline）",
            "",
            "| 规则 | 位置 | 严重度 |",
            "| --- | --- | --- |",
        ]
        lines += [
            f"| {escape_md(f.rule_id)} | {escape_md(f.path)}:{f.line} | {f.severity} |"
            for f in sort_findings(report.suppressed)
        ]
        lines += [
            "",
            "> 抑制不等于修复。请在评审记录中说明每条抑制的原因与复查日期。",
            "",
        ]

    lines += [
        "---",
        "",
        "本报告由离线只读审计工具生成：不修改被审计文件、不发起网络请求、"
        "命中值已脱敏。命中项为复核线索，需人工确认后再处置。",
        "",
    ]
    return "\n".join(lines)


def gate_exit_code(report, fail_on: str = "high") -> int:
    """CI 门禁退出码。

    0 = 无达到阈值的命中，且覆盖完整
    3 = 存在达到阈值的命中
    4 = 覆盖不全（优先级高于 3：结果不可信时先修工具/权限，再谈修代码）
    """
    if not report.coverage.complete:
        return 4
    if report.at_or_above(fail_on):
        return 3
    return 0


def build_lab(root: Path) -> None:
    """搭建一个"什么都有"的样例项目，覆盖跳过/错误/抑制三类情况。"""
    (root / "app").mkdir(parents=True, exist_ok=True)
    (root / "app" / "settings.py").write_text(
        'DEBUG = True\nDB_PASSWORD = "ChangeMe-Demo-123"\nrequests.get(u, verify=False)\n',
        encoding="utf-8",
    )
    (root / "app" / "requirements.txt").write_text("flask\nrequests\n", encoding="utf-8")
    (root / "big.txt").write_text("x" * 4096, encoding="utf-8")
    (root / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    (root / "bad_encoding.txt").write_bytes(b"\xff\xfe\x00bad")
    (root / "link.py").symlink_to(root / "app" / "settings.py")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_lab(root)

        report = scan_path(root, max_bytes=1024)

        # 1) 覆盖统计必须抓到四类跳过
        assert report.coverage.skipped.get("too_large") == 1, report.coverage.skipped
        assert report.coverage.skipped.get("binary") == 1, report.coverage.skipped
        assert report.coverage.skipped.get("not_utf8") == 1, report.coverage.skipped
        assert report.coverage.skipped.get("symlink") == 1, report.coverage.skipped
        assert report.coverage.complete is False

        # 2) 命中与脱敏
        rule_ids = {f.rule_id for f in report.findings}
        assert {"config_debug_enabled", "tls_verify_disabled"} <= rule_ids, rule_ids
        md = render_markdown(report)
        assert "ChangeMe-Demo-123" not in md, "报告泄露明文"
        assert "**不全**" in md and "没有被检查" in md, "覆盖不全必须显式声明"

        # 3) 门禁退出码语义
        assert gate_exit_code(report, "critical") == 4, "覆盖不全时退出码应为 4"
        probe = scan_path(root, max_bytes=1024)
        probe.coverage = Coverage(files_scanned=2)  # 只改副本，模拟"覆盖完整"
        assert gate_exit_code(probe, "high") == 3, "存在 high 命中应为 3"
        assert gate_exit_code(probe, "critical") == 0, "无 critical 命中且覆盖完整应为 0"

        # 4) 空结果也有摘要（不能静默）
        empty_md = render_markdown(scan_path(tmp, max_bytes=1 << 20))
        assert "严重度分布" in empty_md

        # 5) 抑制可见：baseline 命中的条目不消失，只被移到 suppressed
        baseline = ["config_debug_enabled:app/settings.py"]
        report2 = scan_path(root, max_bytes=1024, baseline=baseline)
        assert len(report2.suppressed) >= 1
        assert all(f.rule_id != "config_debug_enabled" for f in report2.findings)
        md2 = render_markdown(report2)
        assert "已抑制（baseline）" in md2 and "config_debug_enabled" in md2

        # 6) 转义：文件名里的竖线不能切碎表格
        assert escape_md("a|b`c") == "a\\|b\\`c"

        # 7) 排序：第一条必须是最高优先级
        ordered = sort_findings(report.findings)
        if len(ordered) > 1:
            assert priority(*((ordered[0].severity, ordered[0].confidence))) >= priority(
                ordered[-1].severity, ordered[-1].confidence
            )

        # 8) JSON 可序列化且字段稳定
        payload = json.loads(json.dumps(report.to_dict(), ensure_ascii=False))
        assert payload["summary"]["findings"] == len(report.findings)
        assert payload["coverage"]["complete"] is False
        assert isinstance(payload["coverage"]["gaps"], list)

        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="运行自测")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("SELF-TEST OK")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "demo-project"
            root.mkdir()
            build_lab(root)
            report = scan_path(root, max_bytes=1024)
            print(summarize(report))
            print(f"覆盖缺口: {report.coverage.gaps}")
            print()
            print(render_markdown(report, "安全审计报告（样例项目）"))
