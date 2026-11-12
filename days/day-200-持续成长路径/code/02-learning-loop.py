#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02-learning-loop.py — 用 git 历史测量「输入 → 实践 → 输出 → 反馈」学习系统

为什么要有这个脚本：
    「我很努力」不是系统指标。努力可以持续一年而毫无积累，
    只要四个环节里有一个是断的。最常见的断法是：只写不改——
    代码越堆越多，但从来没有被修正过，于是错误被固化成习惯。
    git 历史恰好是一份不会撒谎的行为日志：每次提交都带时间和类型。

它做什么：
    1. 读 git log，按 Conventional Commits 类型把提交映射到三个阶段
       实践 = feat/test    输出 = docs    反馈 = fix/refactor/perf
    2. 算节奏：活跃天、最长连续、断档次数与最长断档
    3. 算配比：哪个环节被饿死了（瓶颈判定）
    4. 算反馈延迟：一课从「首次写出」到「被修正」隔了多少天
    5. 算打磨度：哪些课被反复提交（真实难点，而不是自我感觉的难点）

用法：
    python 02-learning-loop.py                     # 人读报告
    python 02-learning-loop.py --json loop.json    # 供 04 消费
    python 02-learning-loop.py --markdown loop.md
    python 02-learning-loop.py --top 10            # 打磨度榜单长度
    python 02-learning-loop.py --self-test         # 离线自证，不依赖 git

诚实边界（重要）：
    「输入」阶段在 git 里不可观测——你读了什么书、看了什么文档，不会留下提交。
    所以本报告只覆盖实践/输出/反馈三环，输入是明确的盲区，不是 0。
    另外：提交类型来自作者自己写的 message，写错类型就会算错阶段。
    本仓库有 43 条「更新readme文件」这类不符合规范的 message，它们被归入「其他」。

设计要点：
    - 只依赖标准库 + 系统 git；Python 3.10+
    - analyze() 是纯函数，read_git() 才碰 IO，所以自测不需要真实仓库
    - 忽略 merge 提交：它不携带学习信号
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, asdict, field
from datetime import date, timedelta
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DAY_RE = re.compile(r"days/day-(\d{3})-")
TYPE_RE = re.compile(r"^([a-zA-Z]+)(?:\([^)]*\))?!?:")

# 阶段映射：type -> 环节。perf 归反馈，因为它应当由测量驱动而不是凭感觉。
STAGE_OF: dict[str, str] = {
    "feat": "实践", "test": "实践",
    "docs": "输出",
    "fix": "反馈", "refactor": "反馈", "perf": "反馈",
}
STAGES = ("实践", "输出", "反馈")
OTHER = "其他"

# 瓶颈阈值：占比低于此值就判「饿死」。产品判断，不是统计显著性。
STARVED = {"实践": 0.20, "输出": 0.15, "反馈": 0.05}

# 一次提交触及 >= 这么多课，就算「批量提交」。
# 为什么需要它：本仓库 2026-11-06 有一条 refactor 一次改了 199 课，
# 它会把「从未被回访的课」直接刷成 0，让反馈回路看起来健康。见 README 原理 2.3。
BULK_THRESHOLD = 20


@dataclass
class Commit:
    sha: str
    day: date
    subject: str
    kind: str
    stage: str
    touched: tuple[int, ...] = ()


@dataclass
class LoopReport:
    total: int
    first: str
    last: str
    span_days: int
    active_days: int
    per_active_day: float
    longest_streak: int
    gap_count: int
    longest_gap: int
    stage_counts: dict[str, int]
    stage_ratio: dict[str, float]
    bottlenecks: list[str]
    latency_samples: int
    latency_median: float | None
    latency_max: int | None
    never_revisited: int
    bulk_feedback: int
    targeted_samples: int
    targeted_median: float | None
    never_revisited_targeted: int
    top_days: list[tuple[int, int]]
    weekday: dict[str, int]
    kind_counts: dict[str, int] = field(default_factory=dict)


def find_repo(start: Path | None = None) -> Path:
    env = os.environ.get("LEARN_PYTHON_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "days").is_dir():
            return candidate
    raise SystemExit("找不到仓库根；用 --root 或 LEARN_PYTHON_ROOT 指定")


def classify(subject: str) -> tuple[str, str]:
    """返回 (type, 阶段)。不符合 Conventional Commits 的一律归「其他」，不猜。"""
    match = TYPE_RE.match(subject.strip())
    kind = match.group(1).lower() if match else "other"
    return kind, STAGE_OF.get(kind, OTHER)


def read_git(repo: Path) -> list[Commit]:
    """一次 git log 拿到时间+标题+改动文件。用 \\x01/\\x02 做分隔，避免中文路径被转义。"""
    cmd = [
        "git", "-C", str(repo), "-c", "core.quotepath=false", "log", "--no-merges",
        "--date=short", "--format=%x01%H%x02%ad%x02%s", "--name-only",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(f"git log 失败: {proc.stderr.decode('utf-8', 'replace').strip()}")
    text = proc.stdout.decode("utf-8", "replace")
    commits: list[Commit] = []
    for chunk in text.split("\x01"):
        if not chunk.strip():
            continue
        head, _, rest = chunk.partition("\n")
        parts = head.split("\x02")
        if len(parts) != 3:
            continue
        sha, day_str, subject = parts
        touched = sorted({int(m.group(1)) for m in DAY_RE.finditer(rest)})
        kind, stage = classify(subject)
        commits.append(Commit(sha=sha[:7], day=date.fromisoformat(day_str),
                              subject=subject, kind=kind, stage=stage, touched=tuple(touched)))
    commits.sort(key=lambda c: (c.day, c.sha))
    return commits


def streaks_and_gaps(days: list[date]) -> tuple[int, int, int]:
    """返回 (最长连续天数, 断档次数, 最长断档天数)。断档 = 相邻活跃日之间空了几天。"""
    if not days:
        return 0, 0, 0
    longest = run = 1
    gaps: list[int] = []
    for prev, cur in zip(days, days[1:]):
        delta = (cur - prev).days
        if delta == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1
            gaps.append(delta - 1)
    return longest, len(gaps), max(gaps, default=0)


def feedback_latency(commits: list[Commit], exclude_bulk: bool = False) -> tuple[list[int], int]:
    """对每个「反馈」提交，找它之前最近一次改动同一课的「实践」提交，算天数差。

    返回 (延迟样本, 从未被回访的课数)。从未回访 = 只有实践、没有后续反馈的课。
    exclude_bulk=True 时跳过批量提交，只统计针对性的修正。
    """
    last_practice: dict[int, date] = {}
    revisited: set[int] = set()
    practiced: set[int] = set()
    samples: list[int] = []
    for c in commits:
        is_bulk = len(c.touched) >= BULK_THRESHOLD
        for day in c.touched:
            if c.stage == "实践":
                # 实践侧不过滤：否则批量写出的课会凭空消失，分母被偷偷改小
                last_practice[day] = c.day
                practiced.add(day)
            elif c.stage == "反馈" and day in last_practice:
                if exclude_bulk and is_bulk:
                    continue
                samples.append((c.day - last_practice[day]).days)
                revisited.add(day)
    return samples, len(practiced - revisited)


def analyze(commits: list[Commit], top: int = 5) -> LoopReport:
    if not commits:
        raise SystemExit("没有提交可分析（浅克隆？先 git fetch --unshallow）")
    active = sorted({c.day for c in commits})
    longest, gap_count, longest_gap = streaks_and_gaps(active)
    counts = Counter(c.stage for c in commits)
    total = len(commits)
    ratio = {s: round(counts.get(s, 0) / total, 4) for s in (*STAGES, OTHER)}
    bottlenecks = [
        f"{s}占比 {ratio[s] * 100:.1f}% 低于 {STARVED[s] * 100:.0f}%：这一环被饿死了"
        for s in STAGES if ratio[s] < STARVED[s]
    ]
    samples, never = feedback_latency(commits)
    targeted, never_targeted = feedback_latency(commits, exclude_bulk=True)
    bulk_feedback = sum(1 for c in commits if c.stage == "反馈" and len(c.touched) >= BULK_THRESHOLD)
    per_day = Counter(d for c in commits for d in c.touched)
    weekday_names = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")
    weekday = Counter(weekday_names[c.day.weekday()] for c in commits)
    span = (active[-1] - active[0]).days + 1
    return LoopReport(
        total=total, first=active[0].isoformat(), last=active[-1].isoformat(),
        span_days=span, active_days=len(active),
        per_active_day=round(total / len(active), 2),
        longest_streak=longest, gap_count=gap_count, longest_gap=longest_gap,
        stage_counts={s: counts.get(s, 0) for s in (*STAGES, OTHER)},
        stage_ratio=ratio, bottlenecks=bottlenecks,
        latency_samples=len(samples),
        latency_median=round(statistics.median(samples), 1) if samples else None,
        latency_max=max(samples, default=None),
        never_revisited=never,
        bulk_feedback=bulk_feedback,
        targeted_samples=len(targeted),
        targeted_median=round(statistics.median(targeted), 1) if targeted else None,
        never_revisited_targeted=never_targeted,
        top_days=per_day.most_common(top),
        weekday={name: weekday.get(name, 0) for name in weekday_names},
        kind_counts=dict(Counter(c.kind for c in commits).most_common()),
    )


def render(rep: LoopReport, top: int) -> str:
    out = [
        f"提交 {rep.total} 条（已忽略 merge）· {rep.first} → {rep.last}",
        f"日历跨度 {rep.span_days} 天 · 活跃 {rep.active_days} 天 · 活跃日均 {rep.per_active_day} 条",
        f"最长连续 {rep.longest_streak} 天 · 断档 {rep.gap_count} 次 · 最长断档 {rep.longest_gap} 天",
        "",
        "四阶段配比（输入不可观测，见 README 原理 2.2）：",
        "  输入        —  不可观测：git 里没有「我读了什么」",
    ]
    for stage in (*STAGES, OTHER):
        count = rep.stage_counts[stage]
        ratio = rep.stage_ratio[stage]
        bar = "█" * round(ratio * 40)
        out.append(f"  {stage:<6}{count:>7}{ratio * 100:>9.1f}%  {bar}")
    out.append("")
    if rep.bottlenecks:
        out.append("瓶颈判定：")
        out += [f"  ⚠️ {b}" for b in rep.bottlenecks]
    else:
        out.append("瓶颈判定：✅ 三环占比都在阈值之上")
    out.append("")
    out.append("反馈延迟（同一课：最近一次实践 → 后续修正）：")
    if rep.latency_samples:
        out.append(f"  全部反馈    样本 {rep.latency_samples} 条 · 中位 {rep.latency_median} 天 · 最长 {rep.latency_max} 天")
    else:
        out.append("  全部反馈    样本 0 条：没有任何一课在写出之后被修正过")
    out.append(f"  其中批量提交 {rep.bulk_feedback} 条（一次触及 >= {BULK_THRESHOLD} 课）")
    if rep.targeted_samples:
        out.append(f"  剔除批量后  样本 {rep.targeted_samples} 条 · 中位 {rep.targeted_median} 天")
    else:
        out.append("  剔除批量后  样本 0 条：没有任何一课被针对性修正过")
    out.append(f"  从未被回访的课：全部口径 {rep.never_revisited} 门 / 剔除批量 {rep.never_revisited_targeted} 门")
    if rep.never_revisited == 0 and rep.never_revisited_targeted > 0:
        out.append("  ⚠️ 差距来自批量提交：一次改 199 课，不等于 199 课都被复盘过")
    out.append("")
    out.append(f"打磨度 Top {top}（被提交次数最多的课 = 真实难点）：")
    for day, count in rep.top_days:
        out.append(f"  Day {day:03d}  {count:>3} 次  {'▇' * min(count, 40)}")
    out.append("")
    out.append("星期分布：")
    for name, count in rep.weekday.items():
        out.append(f"  {name} {count:>5}  {'█' * round(count / max(rep.weekday.values()) * 30)}")
    out.append("")
    out.append("提交类型明细：" + ", ".join(f"{k}={v}" for k, v in rep.kind_counts.items()))
    return "\n".join(out)


def render_markdown(rep: LoopReport) -> str:
    out = [
        "# 学习系统体检（git 历史口径）",
        "",
        f"- 窗口：{rep.first} → {rep.last}（{rep.span_days} 天）",
        f"- 提交：{rep.total} 条，活跃 {rep.active_days} 天，活跃日均 {rep.per_active_day} 条",
        f"- 最长连续：{rep.longest_streak} 天；断档 {rep.gap_count} 次，最长 {rep.longest_gap} 天",
        "",
        "| 环节 | 提交数 | 占比 | 阈值 |",
        "|---|---:|---:|---:|",
        "| 输入 | — | 不可观测 | — |",
    ]
    for stage in (*STAGES, OTHER):
        threshold = f"{STARVED[stage] * 100:.0f}%" if stage in STARVED else "—"
        out.append(f"| {stage} | {rep.stage_counts[stage]} | {rep.stage_ratio[stage] * 100:.1f}% | {threshold} |")
    out += ["", "## 瓶颈", ""]
    out += [f"- ⚠️ {b}" for b in rep.bottlenecks] or ["- ✅ 三环占比均在阈值之上"]
    out += ["", "## 反馈延迟", "",
            f"- 全部反馈：样本 {rep.latency_samples} 条，中位 {rep.latency_median} 天，最长 {rep.latency_max} 天",
            f"- 批量提交（一次触及 ≥ {BULK_THRESHOLD} 课）：{rep.bulk_feedback} 条",
            f"- 剔除批量后：样本 {rep.targeted_samples} 条，中位 {rep.targeted_median} 天",
            f"- 从未被回访的课：全部口径 {rep.never_revisited} 门 / 剔除批量 {rep.never_revisited_targeted} 门", "",
            "> 输入阶段不可观测；提交类型由作者自填，写错即算错；批量提交会美化回访率。", ""]
    return "\n".join(out)


def self_test() -> int:
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        print(("  ✅ " if cond else "  ❌ ") + label)
        assert cond, label
        checks += 1

    check(classify("feat(example): 添加示例") == ("feat", "实践"), "feat → 实践")
    check(classify("docs(concept): 笔记") == ("docs", "输出"), "docs → 输出")
    check(classify("fix: 修正") == ("fix", "反馈"), "fix → 反馈")
    check(classify("perf!: 优化") == ("perf", "反馈"), "带 ! 的破坏性变更也能识别")
    check(classify("更新readme文件") == ("other", "其他"), "不规范 message 归其他，不猜")

    d = date(2026, 1, 1)
    check(streaks_and_gaps([d, d + timedelta(1), d + timedelta(2)]) == (3, 0, 0), "三天连续")
    check(streaks_and_gaps([d, d + timedelta(4)]) == (1, 1, 3), "中间空 3 天算一次断档")
    check(streaks_and_gaps([]) == (0, 0, 0), "空输入不崩")

    def mk(offset: int, subject: str, days: tuple[int, ...]) -> Commit:
        kind, stage = classify(subject)
        return Commit(sha=f"{offset:07d}", day=d + timedelta(offset), subject=subject,
                      kind=kind, stage=stage, touched=days)

    commits = [
        mk(0, "feat: 写 Day001", (1,)),
        mk(1, "docs: 补笔记", (1,)),
        mk(3, "fix: 修正 Day001", (1,)),
        mk(4, "feat: 写 Day002", (2,)),
        mk(9, "chore: 杂项", ()),
    ]
    rep = analyze(commits, top=3)
    check(rep.total == 5 and rep.active_days == 5, "提交数与活跃天数（5 个不同日期）")
    check(rep.span_days == 10, "跨度含首尾两天")
    check(rep.longest_streak == 2, "最长连续 2 天（0,1）")
    check(rep.gap_count == 2 and rep.longest_gap == 4, "断档 2 次，最长 4 天")
    check(rep.stage_counts == {"实践": 2, "输出": 1, "反馈": 1, "其他": 1}, f"阶段计数 {rep.stage_counts}")
    check(rep.latency_samples == 1 and rep.latency_median == 3.0, "Day001 反馈延迟 3 天")
    check(rep.never_revisited == 1, "Day002 从未被回访")
    check(rep.top_days[0] == (1, 3), "Day001 被提交 3 次，居首")
    check(not any("反馈" in b for b in rep.bottlenecks), "反馈 1/5=20% 高于 5% 阈值，不报瓶颈")
    check(not any("输出" in b for b in rep.bottlenecks), "输出 1/5=20% 高于 15% 阈值，不报瓶颈")
    check(rep.stage_ratio["实践"] == 0.4, "实践占比 40%")

    starved = analyze([mk(0, "feat: a", (1,)), mk(1, "feat: b", (2,)), mk(2, "docs: c", (3,))])
    check(any("反馈" in b for b in starved.bottlenecks), "零反馈 → 判定饿死")
    check(starved.latency_samples == 0 and starved.latency_median is None, "无样本时中位数为 None")
    check("不可观测" in render(rep, 3), "报告显式声明输入盲区")
    check("| 输入 | — |" in render_markdown(rep), "Markdown 也保留盲区行")

    # 批量提交会把回访率刷好看：一次改 20 课 ≠ 20 课都被复盘
    bulk = [mk(0, "feat: a", (1,)), mk(1, "feat: b", (2,)),
            mk(2, "refactor: 批量重排", tuple(range(1, BULK_THRESHOLD + 1)))]
    brev = analyze(bulk)
    check(brev.bulk_feedback == 1, "识别出 1 条批量反馈提交")
    check(brev.never_revisited == 0, "全部口径：两门课都算被回访")
    check(brev.never_revisited_targeted == 2, "剔除批量：两门课从未被针对性修正")
    check(brev.targeted_samples == 0 and brev.targeted_median is None, "剔除批量后无延迟样本")
    check("一次改 199 课" in render(brev, 3), "报告主动揭示两个口径的差距")

    try:
        analyze([])
        check(False, "空提交应当报错")
    except SystemExit:
        check(True, "空提交直接报错并提示浅克隆")

    print(f"SELF-TEST PASS（{checks} 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="用 git 历史体检学习系统")
    parser.add_argument("--root", help="仓库根目录")
    parser.add_argument("--top", type=int, default=5, help="打磨度榜单长度")
    parser.add_argument("--json", metavar="PATH", help="导出结构化结果（供 04 消费）")
    parser.add_argument("--markdown", metavar="PATH", help="导出 Markdown 报告")
    parser.add_argument("--self-test", action="store_true", help="离线自证")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    repo = Path(args.root).expanduser().resolve() if args.root else find_repo()
    started = time.perf_counter()
    commits = read_git(repo)
    rep = analyze(commits, top=args.top)
    elapsed = time.perf_counter() - started

    if args.json:
        Path(args.json).write_text(
            json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "read_seconds": round(elapsed, 3), **asdict(rep)},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {args.json}")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(rep), encoding="utf-8")
        print(f"已写入 {args.markdown}")
    print(render(rep, args.top))
    print(f"\n（读 git + 分析耗时 {elapsed * 1000:.1f} ms）")
    return 0


if __name__ == "__main__":
    sys.exit(main())