#!/usr/bin/env python3
"""Day 145 - 阶段复盘报告生成器.

扫描 days/ 下 Phase 9(Day 126-145) 的目录, 自动统计:
- 覆盖的天数/主题
- 每天的文件数与 Python 代码行数
- 输出一份 Markdown 复盘报告(4L 结构骨架)

用法: python3 01-phase-retrospective.py [--out report.md]
"""
import argparse
import re
from pathlib import Path

DAYS_ROOT = Path(__file__).resolve().parents[2]  # .../Learn-Python/days
PHASE9_RANGE = range(126, 146)  # Day 126-145


def parse_day_dir(path: Path) -> tuple[int, str] | None:
    """从目录名解析 (day_number, topic), 如 day-137-browser-fingerprint."""
    m = re.match(r"day-(\d+)-(.+)", path.name)
    return (int(m.group(1)), m.group(2)) if m else None


def count_stats(day_dir: Path) -> dict:
    """统计目录内文件数与 .py 行数."""
    stats = {"files": 0, "py_lines": 0, "py_files": 0}
    for f in day_dir.rglob("*"):
        if f.is_file():
            stats["files"] += 1
            if f.suffix == ".py":
                stats["py_files"] += 1
                stats["py_lines"] += sum(
                    1 for line in f.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.strip().startswith("#")
                )
    return stats


def build_report(rows: list[dict], total: dict) -> str:
    lines = [
        "# Phase 9 阶段复盘报告(自动生成)",
        "",
        f"- 覆盖天数: **{len(rows)} 天**(Day 126-145)",
        f"- 总文件数: **{total['files']}** | Python 文件: **{total['py_files']}**",
        f"- 有效 Python 代码行(去空行/纯注释): **{total['py_lines']}**",
        "",
        "| Day | 主题 | 文件数 | .py | 有效代码行 |",
        "|----:|:-----|-------:|----:|-----------:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['day']} | {r['topic']} | {r['files']} | "
            f"{r['py_files']} | {r['py_lines']} |"
        )
    lines += [
        "",
        "## 4L 复盘骨架(人工填写)",
        "- **Liked**: 哪部分学得最顺?",
        "- **Learned**: 三条最重要的收获?",
        "- **Lacked**: 哪些地方是'能跑但不理解'?",
        "- **Longed for**: 下阶段(Phase 10)想补什么?",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 9 复盘报告生成器")
    ap.add_argument("--out", default=None, help="输出文件路径(缺省只打印)")
    args = ap.parse_args()

    rows, total = [], {"files": 0, "py_files": 0, "py_lines": 0}
    for path in sorted(DAYS_ROOT.iterdir()):
        if not path.is_dir():
            continue
        parsed = parse_day_dir(path)
        if not parsed or parsed[0] not in PHASE9_RANGE:
            continue
        stats = count_stats(path)
        rows.append({"day": parsed[0], "topic": parsed[1], **stats})
        for k in total:
            total[k] += stats[k]

    report = build_report(rows, total)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"报告已写入 {args.out}")
    print(report)


if __name__ == "__main__":
    main()
