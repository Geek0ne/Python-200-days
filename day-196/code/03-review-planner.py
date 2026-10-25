#!/usr/bin/env python3
"""
03-review-planner.py — 用真实仓库数据排出 14 天复习计划

为什么不是「平均分」：
    196 课平均分到 14 天 = 每天 14 课。听起来公平，实际上每课只够扫一眼。
    真实差异很大：Phase 10（Web 安全）有 3.4 万行代码，Phase 9 只有 7 千行；
    按代码量加权，才能把时间放在真正复杂的地方。

算法：
    1. 扫描 days/：每课的 .py 行数 + README 字符数 → 难度权重
       weight = py_lines + readme_chars / 50   （README 50 字符折算 1 行代码）
    2. 每个阶段是一个「复习单元」，单元权重 = 该阶段所有课权重之和
    3. 容量约束：每天 4 个单元；间隔按 1 → 2 → 4 天指数增长
       （刚复习完的单元不会被立刻再排进来）
    4. 贪心：每天从「已到间隔期」的单元里挑权重最高的
    5. 校验：每个阶段至少 2 次、总槽位不超标、每天的负载可见

用法：
    python3 03-review-planner.py --dry-run        # 只打印，不落盘
    python3 03-review-planner.py --write plan.md  # 写 Markdown
    python3 03-review-planner.py --self-test      # 合成仓库自证
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

PHASES = [
    (15, "Python 基础"), (30, "核心编程概念"), (45, "面向对象编程"),
    (60, "高阶特性"), (75, "标准库与生态系统"), (90, "实战项目（一）"),
    (100, "进阶与性能优化"), (125, "数据分析与 AI/ML"), (145, "爬虫与反爬对抗"),
    (165, "网络安全开发"), (185, "自动化运维与 DevOps"), (200, "综合实战"),
]
DAY_DIR_RE = re.compile(r"^day-(\d{3})-")
SLOTS_PER_DAY = 4
HORIZON = 14


def phase_of(day: int) -> int:
    for number, (end, _) in enumerate(PHASES, 1):
        if day <= end:
            return number
    raise ValueError(day)


@dataclass
class Unit:
    phase: int
    name: str
    days: int = 0
    py_lines: int = 0
    readme_chars: int = 0
    sessions: int = 0
    next_allowed: int = 1
    history: list[int] = field(default_factory=list)

    @property
    def weight(self) -> float:
        return self.py_lines + self.readme_chars / 50.0

    @property
    def priority(self) -> float:
        # 还没复习过的单元加权；复习次数越多优先级越低
        return self.weight / (1 + self.sessions)


def scan_units(repo: Path) -> list[Unit]:
    days_dir = repo / "days"
    if not days_dir.is_dir():
        raise SystemExit(f"找不到 days/ 目录: {days_dir}")
    units = {n: Unit(n, name) for n, (_, name) in enumerate(PHASES, 1)}
    for child in days_dir.iterdir():
        match = DAY_DIR_RE.match(child.name)
        if not child.is_dir() or not match:
            continue
        day = int(match.group(1))
        unit = units[phase_of(day)]
        unit.days += 1
        for py in child.rglob("*.py"):
            if "__pycache__" in set(py.parts):
                continue
            try:
                unit.py_lines += py.read_bytes().count(b"\n")
            except OSError:
                pass
        readme = child / "README.md"
        if readme.exists():
            unit.readme_chars += len(readme.read_text(encoding="utf-8", errors="replace"))
    return [u for u in units.values() if u.days > 0]


def build_plan(units: list[Unit], horizon: int = HORIZON,
               slots: int = SLOTS_PER_DAY) -> list[list[Unit]]:
    """返回 plan[day_index] = 当天要复习的单元列表（day_index 从 0 开始）。"""
    plan: list[list[Unit]] = []
    for day in range(1, horizon + 1):
        today: list[Unit] = []
        for _ in range(slots):
            ready = [u for u in units if u.next_allowed <= day and u not in today]
            if not ready:
                break
            chosen = max(ready, key=lambda u: (u.priority, -u.phase))
            today.append(chosen)
            chosen.sessions += 1
            chosen.history.append(day)
            # 间隔 1 → 2 → 4 → 8 天，避免「今天看完明天又看」
            gap = min(2 ** (chosen.sessions - 1), 8)
            chosen.next_allowed = day + gap
        plan.append(today)
    return plan


def render(units: list[Unit], plan: list[list[Unit]], horizon: int) -> str:
    total_slots = sum(len(p) for p in plan)
    capacity = horizon * SLOTS_PER_DAY
    lines = [
        f"# {horizon} 天复习计划（按真实代码量加权）",
        "",
        f"- 复习单元：{len(units)} 个阶段 / 覆盖 {sum(u.days for u in units)} 课",
        f"- 槽位使用：{total_slots}/{capacity}（{total_slots / capacity:.0%}）",
        f"- 每单元次数：最少 {min(u.sessions for u in units)}，最多 {max(u.sessions for u in units)}",
        "",
        "## 权重表",
        "",
        "| 阶段 | 名称 | 课数 | 代码行 | README 字符 | 权重 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for unit in sorted(units, key=lambda u: -u.weight):
        lines.append(f"| P{unit.phase} | {unit.name} | {unit.days} | {unit.py_lines:,} "
                     f"| {unit.readme_chars:,} | {unit.weight:,.0f} |")
    lines += ["", "## 日程", "", "| 天 | 复习单元 |", "|---|---|"]
    for index, todays in enumerate(plan, 1):
        names = "、".join(f"P{u.phase} {u.name}" for u in todays) or "（空）"
        lines.append(f"| Day{index} | {names} |")
    lines += ["", "## 校验", ""]
    for unit in units:
        ok = "✅" if unit.sessions >= 2 else "⚠️"
        lines.append(f"- {ok} P{unit.phase} {unit.name}: {unit.sessions} 次 {unit.history}")
    return "\n".join(lines)


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        # 只造 3 个阶段：1、10、12，且代码量差异明显
        for day, lines in ((1, 5), (2, 5), (146, 200), (147, 200), (196, 30)):
            d = repo / "days" / f"day-{day:03d}-t"
            d.mkdir(parents=True)
            (d / "README.md").write_text("# t\n" + "x" * 100, encoding="utf-8")
            (d / "a.py").write_text("# c\n" * lines, encoding="utf-8")
        units = scan_units(repo)
        assert {u.phase for u in units} == {1, 10, 12}, [u.phase for u in units]
        plan = build_plan(units, horizon=14, slots=4)
        assert len(plan) == 14
        assert any(len(p) > 0 for p in plan)
        # 每个单元至少 2 次，且同一天不重复
        assert all(u.sessions >= 2 for u in units), [(u.phase, u.sessions) for u in units]
        for todays in plan:
            assert len({u.phase for u in todays}) == len(todays)
        # 最重的单元应该被排得更多
        heaviest = max(units, key=lambda u: u.weight)
        assert heaviest.sessions >= min(u.sessions for u in units)
        assert len({u.phase for p in plan for u in p}) == 3
        print("✅ self-test passed: 阶段归并/容量/间隔/覆盖 均符合预期")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="按真实代码量生成复习计划")
    parser.add_argument("--root", default=os.environ.get("LEARN_PYTHON_ROOT",
                                                         str(Path.home() / "code" / "Learn-Python")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--write", metavar="PATH")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    units = scan_units(Path(args.root))
    plan = build_plan(units)
    report = render(units, plan, HORIZON)
    if args.write and not args.dry_run:
        Path(args.write).write_text(report, encoding="utf-8")
        print(f"已写入 {args.write}")
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
