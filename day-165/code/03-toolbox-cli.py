#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03-toolbox-cli.py — 报告生成 CLI + 退出码门禁（Day 165 · 实战）

这是四天阶段项目的**收口入口**：把前三天产出的发现（findings）
统一转成可交付报告，并用退出码告诉 CI"这次审计算不算过"。

用法示例：
    # 用示例数据渲染全部四种格式
    python3 03-toolbox-cli.py --input findings.example.json --format all

    # 只渲染 markdown，且高危及以上就返回非 0（给 CI 当门禁）
    python3 03-toolbox-cli.py --input findings.example.json --format md --fail-on high

    # 固定时间戳，产出可 diff 的归档
    python3 03-toolbox-cli.py --input findings.example.json --format md \
        --generated-at 2026-09-24T06:00:00+08:00

退出码语义（**这是本工具被 CI 消费的契约**）：
    0  无阻断问题（可能在阈值以下，也可能完全没有发现）
    1  存在达到/超过阈值的发现（门禁拦截）
    2  入参/输入数据错误（用法错、JSON 坏、severity 非法）
    3  渲染或写盘失败（磁盘、权限）
    4  存在**覆盖缺口**（发现本身可能不阻断，但结论不完整）

为什么 4 要单独一档？因为"没测"和"测了没问题"是两种截然不同的状态。
如果都返回 0，那么一个"因为代理超时什么都没测到"的运行
会和"真的全部通过"长得一模一样——这是审计工具最危险的失败模式。

安全边界：本脚本只读本地 JSON、写本地文件，不发起任何网络请求。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from report_core import Finding, Report, SEVERITY_ORDER, summarize
except ImportError:  # pragma: no cover - 明确给出可操作的提示，而不是 ImportError 堆栈
    print("错误：找不到 report_core.py。请在同一目录下运行本脚本。", file=sys.stderr)
    raise SystemExit(2)

DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "out"

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT = 2
EXIT_RENDER = 3
EXIT_COVERAGE = 4

FORMAT_SUFFIX = {"md": ".md", "json": ".json", "html": ".html", "sarif": ".sarif"}


# ──────────────────────────────────────────────────────────────────────
# 输入解析：把外部 JSON 变成 Finding 对象
# ──────────────────────────────────────────────────────────────────────
def load_findings(path: Path) -> tuple[list[Finding], list[str], list[str]]:
    """读入 findings 文件。

    支持两种结构：
      1) 裸数组：           [ {finding}, {finding}, ... ]
      2) 带元信息的对象：   { "scope": "...", "coverage_gaps": [...], "findings": [...] }

    为什么强制做合法性校验（而不是"宽容地忽略错误字段"）？
    因为一个拼错的 severity（比如 "hight"）如果被静默吞掉，
    它就会从报告里消失——报告看起来更干净，事实却更糟。
    审计工具宁可**拒绝运行**，也不能悄悄丢东西。
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"输入文件不存在：{path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"输入不是合法 JSON（第 {exc.lineno} 行第 {exc.colno} 列）：{exc.msg}")

    if isinstance(raw, list):
        items, scope, gaps = raw, "未声明", []
    elif isinstance(raw, dict):
        items = raw.get("findings", [])
        scope = raw.get("scope", "未声明")
        gaps = list(raw.get("coverage_gaps", []))
    else:
        raise ValueError("输入顶层必须是数组或对象")

    findings: list[Finding] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"findings[{idx}] 不是对象")
        missing = [k for k in ("rule_id", "title", "severity", "target", "reason")
                   if not item.get(k)]
        if missing:
            raise ValueError(f"findings[{idx}] 缺少必填字段：{', '.join(missing)}")
        if item["severity"] not in SEVERITY_ORDER:
            raise ValueError(
                f"findings[{idx}].severity={item['severity']!r} 非法，"
                f"允许：{', '.join(SEVERITY_ORDER)}"
            )
        findings.append(Finding(
            rule_id=str(item["rule_id"]),
            title=str(item["title"]),
            severity=str(item["severity"]),
            target=str(item["target"]),
            reason=str(item["reason"]),
            remediation=str(item.get("remediation", "")),
            confidence=str(item.get("confidence", "high")),
            evidence=tuple(str(e) for e in item.get("evidence", ())),
            tags=tuple(str(t) for t in item.get("tags", ())),
            phase=str(item.get("phase", "")),
        ))
    return findings, scope, gaps


def resolve_generated_at(argv_value: str | None) -> str:
    """决定报告时间戳，优先级：--generated-at > SOURCE_DATE_EPOCH > 当前时间。

    SOURCE_DATE_EPOCH 是**可复现构建**领域的既有约定
    （见 reproducible-builds.org）。借用它的好处：
    CI 里设一个固定值，同一份输入的产物哈希就完全稳定，
    可以直接拿哈希做"报告是否变化"的判据。
    """
    if argv_value:
        return argv_value
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        import datetime as _dt
        ts = _dt.datetime.fromtimestamp(int(epoch), tz=_dt.timezone.utc)
        return ts.astimezone(_dt.timezone(_dt.timedelta(hours=8))).isoformat()
    import datetime as _dt
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


# ──────────────────────────────────────────────────────────────────────
# 门禁判定
# ──────────────────────────────────────────────────────────────────────
def blocked_by(findings: list[Finding], threshold: str | None) -> list[Finding]:
    """返回达到或超过阈值的发现。

    注意"达到"的含义：`--fail-on high` 会同时命中 critical 与 high。
    这条语义必须写进文档，否则用户会以为 high 只管 high。
    """
    if threshold is None:
        return []
    limit = SEVERITY_ORDER[threshold]
    return [f for f in findings if SEVERITY_ORDER[f.severity] <= limit]


# ──────────────────────────────────────────────────────────────────────
# 渲染与写盘
# ──────────────────────────────────────────────────────────────────────
def render_all(report: Report, formats: list[str]) -> dict[str, str]:
    renderers = {
        "md": (report.render_markdown, ".md"),
        "json": (report.render_json, ".json"),
        "html": (report.render_html, ".html"),
        "sarif": (report.render_sarif, ".sarif.json"),
    }
    return {fmt: renderers[fmt][0]() for fmt in formats}


def write_outputs(contents: dict[str, str], out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fmt, text in contents.items():
        suffix = FORMAT_SUFFIX[fmt]
        path = out_dir / f"{stem}{suffix}"
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audit-report",
        description="安全审计报告生成器（Day 165 实战）：统一渲染 + 退出码门禁",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "退出码：0=通过  1=有阻断发现  2=输入错误  3=渲染失败  4=存在覆盖缺口\n"
            "示例：python3 03-toolbox-cli.py --input findings.example.json "
            "--format all --fail-on high"
        ),
    )
    parser.add_argument("--input", "-i", required=True, help="findings JSON 路径")
    parser.add_argument("--format", "-f", default="md",
                        choices=["md", "json", "html", "sarif", "all"],
                        help="输出格式，all = 四种全部（默认 md）")
    parser.add_argument("--out-dir", "-o", default=str(DEFAULT_OUT_DIR), help="输出目录")
    parser.add_argument("--stem", default="day165-report", help="输出文件名主干")
    parser.add_argument("--title", default="安全审计报告", help="报告标题")
    parser.add_argument("--fail-on", default=None,
                        choices=list(SEVERITY_ORDER) + [""],
                        help="达到或超过该严重度即返回退出码 1（空字符串=不门禁）")
    parser.add_argument("--allow-coverage-gaps", action="store_true",
                        help="即使存在覆盖缺口也返回 0（**不推荐**，请显式说明理由）")
    parser.add_argument("--generated-at", default=None,
                        help="固定报告时间戳（ISO-8601），用于可复现产物")
    parser.add_argument("--summary-only", action="store_true", help="只打印摘要，不写文件")
    args = parser.parse_args(argv)

    threshold = args.fail_on or None
    formats = ["md", "json", "html", "sarif"] if args.format == "all" else [args.format]

    # ── 输入阶段：任何问题都是退出码 2 ──
    try:
        findings, scope, gaps = load_findings(Path(args.input))
    except ValueError as exc:
        print(f"❌ 输入错误：{exc}", file=sys.stderr)
        return EXIT_INPUT

    report = Report(
        title=args.title,
        scope=scope,
        generated_at=resolve_generated_at(args.generated_at),
        findings=findings,
        coverage_gaps=gaps,
    )

    blocking = blocked_by(report.ordered_findings(), threshold)

    print(f"📄 报告：{args.title}")
    print(f"   范围　：{scope}")
    print(f"   摘要　：{summarize(report)}")
    print(f"   时间戳：{report.generated_at}")
    if threshold:
        print(f"   门禁　：--fail-on {threshold} → 命中 {len(blocking)} 条")
        for f in blocking:
            print(f"      · [{f.severity}] {f.rule_id} @ {f.target}")

    if args.summary_only:
        print("   （--summary-only，未写文件）")
    else:
        try:
            contents = render_all(report, formats)
            written = write_outputs(contents, Path(args.out_dir), args.stem)
        except OSError as exc:
            print(f"❌ 写盘失败：{exc}", file=sys.stderr)
            return EXIT_RENDER
        for path in written:
            size = path.stat().st_size
            print(f"   ✅ 已写入 {path}（{size} 字节）")

    # ── 退出码决策（顺序有意义：输入错误已被上面提前返回） ──
    if blocking:
        print("⛔ 门禁拦截：存在达到阈值的发现")
        return EXIT_FINDINGS
    if gaps and not args.allow_coverage_gaps:
        print("⚠️  存在覆盖缺口：结论不完整，返回 4（不是失败，但也不能算通过）")
        return EXIT_COVERAGE
    print("✅ 通过")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
