#!/usr/bin/env python3
"""
01-knowledge-map.py — 从仓库真实数据生成「200 天知识地图」

为什么要有这个脚本：
    复习最大的敌人不是「忘了」，而是「不知道自己忘了什么」。
    凭感觉翻目录，会反复看已经会的；真正薄弱的部分反而被跳过。
    所以第一步不是复习，而是把「学过什么」变成可统计的数据。

它做什么：
    1. 扫描 days/ 下所有 day-XXX-* 目录（真实文件，不做任何硬编码清单）
    2. 解析每课 README.md 的 H1 标题、代码文件数、代码行数、字符数
    3. 按 Day 区间归入 12 个阶段
    4. 输出人读表格 / Mermaid mindmap / JSON 三种视图

用法：
    python3 01-knowledge-map.py                 # 人读汇总
    python3 01-knowledge-map.py --mermaid       # 输出 Mermaid mindmap
    python3 01-knowledge-map.py --json out.json # 导出结构化数据
    python3 01-knowledge-map.py --self-test     # 离线自证（不依赖本仓库）

设计要点：
    - 只依赖标准库，零第三方包
    - 代码行数统计跳过 __pycache__ 与 .venv，否则会虚高
    - day 目录名里的中文 slug 不参与统计，标题一律从 README H1 取
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path

# ── 12 个阶段的边界（与 tools/generate_daily.py 的 phase_for_day 保持一致）
PHASES: list[tuple[int, str]] = [
    (15, "Python 基础"),
    (30, "核心编程概念"),
    (45, "面向对象编程"),
    (60, "高阶特性"),
    (75, "标准库与生态系统"),
    (90, "实战项目（一）"),
    (100, "进阶与性能优化"),
    (125, "数据分析与 AI/ML"),
    (145, "爬虫与反爬对抗"),
    (165, "网络安全开发"),
    (185, "自动化运维与 DevOps"),
    (200, "综合实战"),
]

DAY_DIR_RE = re.compile(r"^day-(\d{3})-")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def phase_of(day: int) -> tuple[int, str]:
    """返回 (阶段编号, 阶段名)。越界直接抛错，避免静默算错阶段。"""
    if not 1 <= day <= 200:
        raise ValueError(f"day out of range: {day}")
    for number, (end, name) in enumerate(PHASES, 1):
        if day <= end:
            return number, name
    raise AssertionError("unreachable")


@dataclass
class DayStat:
    day: int
    slug: str
    title: str
    py_files: int
    py_lines: int
    readme_chars: int
    phase: int
    phase_name: str


def count_py(root: Path) -> tuple[int, int]:
    """统计 .py 文件数与总行数。按二进制读再数 \n 比 readlines() 快。"""
    files = lines = 0
    for path in root.rglob("*.py"):
        parts = set(path.parts)
        if "__pycache__" in parts or ".venv" in parts or "venv" in parts:
            continue
        files += 1
        try:
            lines += path.read_bytes().count(b"\n")
        except OSError:
            continue
    return files, lines


def read_title(readme: Path) -> str:
    """取第一个 H1 作为标题；读不到就返回空串，让调用方决定怎么兜底。"""
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = H1_RE.search(text)
    return match.group(1).strip() if match else ""


def scan(repo: Path) -> tuple[list[DayStat], float]:
    days_dir = repo / "days"
    if not days_dir.is_dir():
        raise SystemExit(f"找不到 days/ 目录: {days_dir}")

    started = time.perf_counter()
    stats: list[DayStat] = []
    for child in sorted(days_dir.iterdir()):
        if not child.is_dir():
            continue
        match = DAY_DIR_RE.match(child.name)
        if not match:
            continue
        day = int(match.group(1))
        readme = child / "README.md"
        py_files, py_lines = count_py(child)
        phase, phase_name = phase_of(day)
        stats.append(
            DayStat(
                day=day,
                slug=child.name,
                title=read_title(readme) or f"(无 README) {child.name}",
                py_files=py_files,
                py_lines=py_lines,
                readme_chars=len(readme.read_text(encoding="utf-8", errors="replace"))
                if readme.exists()
                else 0,
                phase=phase,
                phase_name=phase_name,
            )
        )
    elapsed = time.perf_counter() - started
    stats.sort(key=lambda s: s.day)
    return stats, elapsed


def summarize(stats: list[DayStat], elapsed: float) -> str:
    total_files = sum(s.py_files for s in stats)
    total_lines = sum(s.py_lines for s in stats)
    total_chars = sum(s.readme_chars for s in stats)
    covered = {s.day for s in stats}
    gaps = [d for d in range(1, max(covered, default=0) + 1) if d not in covered]

    out = []
    out.append(f"扫描目录：{len(stats)} 课，耗时 {elapsed * 1000:.1f} ms")
    out.append(f"代码文件：{total_files} 个 | 代码行数：{total_lines:,} 行 | README 字符：{total_chars:,}")
    out.append("")
    out.append(f"{'阶段':<4}{'区间':<14}{'课数':>4}{'py文件':>7}{'py行数':>9}{'README字符':>12}  阶段名")
    out.append("-" * 78)
    for phase in range(1, len(PHASES) + 1):
        rows = [s for s in stats if s.phase == phase]
        if not rows:
            continue
        end = PHASES[phase - 1][0]
        start = 1 if phase == 1 else PHASES[phase - 2][0] + 1
        out.append(
            f"{phase:<6}{f'Day {start:03d}-{end:03d}':<16}{len(rows):>4}"
            f"{sum(r.py_files for r in rows):>8}{sum(r.py_lines for r in rows):>10}"
            f"{sum(r.readme_chars for r in rows):>12}  {PHASES[phase - 1][1]}"
        )
    if gaps:
        out.append("")
        out.append(f"⚠️ 缺失的 Day：{gaps}")
    return "\n".join(out)


def to_mermaid(stats: list[DayStat]) -> str:
    lines = ["mindmap", "  root((Python 200 Days))"]
    for phase in range(1, len(PHASES) + 1):
        rows = [s for s in stats if s.phase == phase]
        if not rows:
            continue
        safe_name = PHASES[phase - 1][1].replace("(", "（").replace(")", "）")
        lines.append(f"    P{phase} {safe_name}")
        for row in rows:
            title = re.sub(r'[\x60"\n]', "", row.title)
            lines.append(f"      D{row.day:03d} {title}")
    return "\n".join(lines)


def self_test() -> int:
    """造一个临时仓库，验证扫描逻辑；不依赖真实仓库，可离线跑。"""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        for day, py, lines in ((1, 1, 10), (16, 2, 30), (196, 3, 60)):
            d = repo / "days" / f"day-{day:03d}-x"
            d.mkdir(parents=True)
            (d / "README.md").write_text(f"# Day {day} — 测试主题\n\n正文\n", encoding="utf-8")
            for i in range(py):
                (d / f"{i}.py").write_text("# x\n" * lines, encoding="utf-8")
        # 干扰项：不符合命名的目录、__pycache__ 里的 py 文件
        (repo / "days" / "not-a-day").mkdir()
        cache = repo / "days" / "day-001-x" / "__pycache__"
        cache.mkdir()
        (cache / "junk.py").write_text("# 不该被统计\n" * 999, encoding="utf-8")

        stats, _ = scan(repo)
        assert [s.day for s in stats] == [1, 16, 196], [s.day for s in stats]
        assert stats[0].py_files == 1, stats[0]
        assert stats[0].py_lines == 10, stats[0].py_lines
        assert stats[1].phase == 2, stats[1].phase
        assert stats[2].phase == 12, stats[2].phase
        assert stats[2].title == "Day 196 — 测试主题", stats[2].title
        assert "P12" in to_mermaid(stats)
        assert phase_of(200)[0] == 12
        print("✅ self-test passed: 扫描/阶段/行数/Mermaid 均符合预期")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="从 days/ 生成知识地图")
    parser.add_argument("--root", default=os.environ.get("LEARN_PYTHON_ROOT", str(Path.home() / "code" / "Learn-Python")))
    parser.add_argument("--mermaid", action="store_true", help="输出 Mermaid mindmap")
    parser.add_argument("--json", metavar="PATH", help="导出 JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    stats, elapsed = scan(Path(args.root))
    if args.json:
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "total_days": len(stats),
            "total_py_files": sum(s.py_files for s in stats),
            "total_py_lines": sum(s.py_lines for s in stats),
            "days": [asdict(s) for s in stats],
        }
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {args.json}")
    print(to_mermaid(stats) if args.mermaid else summarize(stats, elapsed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
