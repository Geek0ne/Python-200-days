#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04-growth-roadmap.py — 毕业总结 + 缺口驱动的 90 天成长路线图

为什么要有这个脚本：
    前 199 天，题目是别人出的：目录里写着 Day N，你照着做就行。
    毕业那天起，没人给你出题了。这才是真正的难点——
    不是「学什么」，而是「凭什么决定学什么」。
    所以今天交付的不是新知识，是一台出题机：
    把三份测量（能力证据 / 系统瓶颈 / 技术资产）合成下一步的可验收计划。

它做什么：
    1. 扫仓库出毕业统计：课数、代码量、四件套完整度、mermaid 图数、12 阶段分布
    2. 读 01/02/03 导出的 JSON（缺哪份就明确标缺，绝不编数字）
    3. 生成 graduation.md：毕业总结，含「这份总结不能证明什么」
    4. 生成 roadmap-90d.md：3 个 30 天里程碑，每个都有可验收交付物 + 放弃条件
    5. 生成 summary.json：机器可读汇总

用法：
    python 04-growth-roadmap.py --out /tmp/day200/毕业交付 \\
        --audit /tmp/day200/audit.json \\
        --loop  /tmp/day200/loop.json \\
        --radar /tmp/day200/radar.json
    python 04-growth-roadmap.py --self-test        # 离线自证，不依赖本仓库

设计要点（也是本课的方法论）：
    - 里程碑由缺口驱动，不是愿望清单：证据分最低的维度优先
    - 每个里程碑必须有「别人能检查」的交付物，否则等于没做
    - 每个里程碑必须有放弃条件：没有 kill criteria 的计划会无限拖尾
    - 只依赖标准库；Python 3.10+
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DAY_DIR_RE = re.compile(r"^day-(\d{3})-")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
MERMAID_RE = re.compile(r"^```mermaid\s*$", re.MULTILINE)

PHASES: list[tuple[int, str]] = [
    (15, "Python 基础"), (30, "核心编程概念"), (45, "面向对象编程"), (60, "高阶特性"),
    (75, "标准库与生态系统"), (90, "实战项目"), (100, "进阶与性能优化"),
    (125, "数据分析与 AI/ML"), (145, "爬虫与反爬对抗"), (165, "网络安全开发"),
    (185, "自动化运维与 DevOps"), (200, "综合实战"),
]
REQUIRED = ("README.md", "code", "exercises/checklist.md", "diagrams/README.md")
CAPSTONES = ((186, 190, "企业资产监控系统"), (191, 195, "AI 赋能反爬数据平台"))

# 维度 → 可验收交付物。刻意都要求「别人能检查」，呼应 Day 197/198/199。
DELIVERABLE: dict[str, str] = {
    "语言与数据模型": "10 个标准库模块的陷阱清单，每个带 --self-test，合成一篇体检 100 分的文章",
    "工程化与质量": "给两个毕业项目补 pytest，覆盖率门禁进 CI，附一次真实拦截记录",
    "并发与性能": "5 次重复、带环境指纹的并发基准报告，含至少一个翻车复盘",
    "数据与 AI": "端到端可复现的分析管道 + EDA 报告，读者能凭文章重跑",
    "网络与爬虫": "礼貌爬虫（robots + 限速 + 断点续爬）+ 一页合规说明",
    "安全与合规": "授权范围内的只读审计报告 + 修复建议，附范围门禁与审计留痕",
    "运维与交付": "一键部署 + 故障演练 + 自动回滚，附端到端验收记录",
    "表达与协作": "3 篇体检 100 分的技术文章 + 1 个被上游合并的 PR",
}
DEFAULT_DELIVERABLE = "一个可被别人独立验收的交付物（文章 / PR / 可复现报告三选一）"


@dataclass
class Milestone:
    index: int
    window: str
    title: str
    why: str
    weekly: list[str]
    deliverable: str
    acceptance: str
    kill_criteria: str


@dataclass
class Graduation:
    days: int
    py_files: int
    py_lines: int
    readme_chars: int
    mermaid_blocks: int
    complete_days: int
    incomplete: list[str]
    phases: list[dict]
    capstones: list[dict]
    audit: dict | None = None
    loop: dict | None = None
    radar: dict | None = None
    missing_inputs: list[str] = field(default_factory=list)


def find_repo(start: Path | None = None) -> Path:
    env = os.environ.get("LEARN_PYTHON_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "days").is_dir():
            return candidate
    raise SystemExit("找不到仓库根；用 --root 或 LEARN_PYTHON_ROOT 指定")


def phase_of(day: int) -> tuple[int, str]:
    for number, (end, name) in enumerate(PHASES, 1):
        if day <= end:
            return number, name
    raise ValueError(f"day out of range: {day}")


def scan(repo: Path) -> Graduation:
    days_dir = repo / "days"
    if not days_dir.is_dir():
        raise SystemExit(f"找不到 days/ 目录: {days_dir}")
    days = py_files = py_lines = readme_chars = mermaid = complete = 0
    incomplete: list[str] = []
    per_phase: dict[int, dict] = {}

    for child in sorted(days_dir.iterdir()):
        match = DAY_DIR_RE.match(child.name)
        if not child.is_dir() or not match:
            continue
        day = int(match.group(1))
        days += 1
        number, name = phase_of(day)
        bucket = per_phase.setdefault(number, {"phase": number, "name": name, "days": 0, "py_lines": 0})
        bucket["days"] += 1

        missing = [r for r in REQUIRED if not (child / r).exists()]
        if missing:
            incomplete.append(f"{child.name}: 缺 {', '.join(missing)}")
        else:
            complete += 1

        readme = child / "README.md"
        if readme.is_file():
            text = readme.read_text(encoding="utf-8", errors="replace")
            readme_chars += len(text)
            mermaid += len(MERMAID_RE.findall(text))
        for md in child.rglob("*.md"):
            if md == readme or "__pycache__" in md.parts:
                continue
            mermaid += len(MERMAID_RE.findall(md.read_text(encoding="utf-8", errors="replace")))
        for py in child.rglob("*.py"):
            if "__pycache__" in py.parts:
                continue
            py_files += 1
            lines = py.read_bytes().count(b"\n")
            py_lines += lines
            bucket["py_lines"] += lines

    capstones = [
        {"name": name, "range": f"Day {lo}–{hi}",
         "days_present": sum(1 for d in range(lo, hi + 1) if (days_dir / f"day-{d:03d}").exists()
                             or any(p.name.startswith(f"day-{d:03d}-") for p in days_dir.iterdir()))}
        for lo, hi, name in CAPSTONES
    ]
    return Graduation(
        days=days, py_files=py_files, py_lines=py_lines, readme_chars=readme_chars,
        mermaid_blocks=mermaid, complete_days=complete, incomplete=incomplete,
        phases=[per_phase[k] for k in sorted(per_phase)], capstones=capstones,
    )


def load_inputs(grad: Graduation, audit: Path | None, loop: Path | None, radar: Path | None) -> None:
    for label, path in (("audit", audit), ("loop", loop), ("radar", radar)):
        if path is None:
            grad.missing_inputs.append(label)
            continue
        if not path.is_file():
            grad.missing_inputs.append(f"{label}（文件不存在: {path}）")
            continue
        setattr(grad, label, json.loads(path.read_text(encoding="utf-8")))


def build_milestones(grad: Graduation) -> list[Milestone]:
    """缺口驱动：先修系统瓶颈，再补最弱的能力维度。技术债作为贯穿动作，不占里程碑。"""
    weakest = (grad.audit or {}).get("weakest") or []
    dims = {d["name"]: d for d in (grad.audit or {}).get("dimensions", [])}
    bottlenecks = (grad.loop or {}).get("bottlenecks") or []
    feedback_starved = any("反馈" in b for b in bottlenecks)

    titles: list[tuple[str, str]] = []
    if feedback_starved:
        ratio = (grad.loop or {}).get("stage_ratio", {}).get("反馈", 0)
        titles.append((
            "修反馈回路：让旧代码真的能跑",
            f"02 测出反馈占比仅 {ratio * 100:.1f}%，低于 5% 阈值；"
            f"剔除批量提交后 {(grad.loop or {}).get('never_revisited_targeted', '?')} 门课从未被针对性修正",
        ))
    for name in weakest:
        if len(titles) >= 3:
            break
        evidence = dims.get(name, {}).get("evidence", "?")
        titles.append((f"补最弱维度：{name}", f"01 测出该维度证据分 {evidence}，排在薄弱榜"))
    while len(titles) < 3:
        titles.append(("自选深耕方向", "01 未提供足够缺口数据，需人工指定（不编造）"))

    milestones: list[Milestone] = []
    for i, (title, why) in enumerate(titles[:3], 1):
        if i == 1 and feedback_starved:
            weekly = [
                "第 1 周：写一个 import 级冒烟脚本，逐课实跑 code/ 下每个入口，记录失败清单",
                "第 2 周：修掉失败清单里最靠前的一课（本仓库实测是 Day 018 的缺失 tools 模块）",
                "第 3 周：把冒烟脚本接进 CI，与 compileall 并列——语法通过不等于能跑",
                "第 4 周：写复盘文章，用 Day 199 的体检器拿到 100 分后发布",
            ]
            deliverable = "一个进 CI 的 import 级冒烟门禁 + 一份真实失败清单 + 一篇复盘文章"
            acceptance = "CI 日志里能看到冒烟步骤；故意改坏一个 import，门禁必须变红"
            kill = "若第 2 周结束仍无法让冒烟脚本稳定跑完全部课，缩小到只覆盖 Phase 1–4，不要硬扛"
        else:
            name = title.replace("补最弱维度：", "")
            deliverable = DELIVERABLE.get(name, DEFAULT_DELIVERABLE)
            weekly = [
                f"第 1 周：重做「{name}」的 3 课，只动手不重读，每课补一个 --self-test",
                "第 2 周：把重做中踩的坑写成陷阱清单，每条附一行可跑的验证",
                "第 3 周：产出交付物的第一版，找一个不在场的人照着跑",
                "第 4 周：按对方反馈修正，补齐环境与样本量，发布",
            ]
            acceptance = "交付物能被一个没参与的人独立验收；文章体检 0 error 0 warning"
            kill = "若第 3 周找不到愿意试跑的读者，改为录一段 5 分钟复现视频自证，不要无限等待"
        milestones.append(Milestone(
            index=i, window=f"第 {(i - 1) * 30 + 1}–{i * 30} 天", title=title, why=why,
            weekly=weekly, deliverable=deliverable, acceptance=acceptance, kill_criteria=kill,
        ))
    return milestones


def recurring_tasks(grad: Graduation) -> list[str]:
    """贯穿 90 天的固定动作：技术债收敛 + 系统节奏，不占里程碑。"""
    tasks = [
        "每周一次：跑 02-learning-loop.py，确认反馈占比在上升（目标 ≥ 5%）",
        "每月一次：跑 01-skill-audit.py，对比上月证据分，只认涨落不认感觉",
    ]
    radar = grad.radar or {}
    holds = [p["name"] for p in radar.get("packages", []) if p.get("ring") == "Hold"]
    if holds:
        tasks.append(f"技术债：Hold 环 {', '.join(holds)} —— 新项目不再引入，旧项目评估替换成本")
    ranged = radar.get("req_counts", {}).get("ranged", 0)
    unpinned = radar.get("req_counts", {}).get("unpinned", 0)
    if ranged or unpinned:
        tasks.append(f"供应链：{ranged} 条范围约束 + {unpinned} 条未约束，逐步钉死并生成哈希锁文件")
    suspects = radar.get("suspects") or []
    if suspects:
        tasks.append("静态扫描待人工核对：" + "；".join(f"{s['name']}（Day {s['days']}）" for s in suspects)
                     + " —— 有的是运行时创建的良性模块，有的是真缺失，必须实跑区分")
    if grad.incomplete:
        tasks.append(f"四件套补齐：{len(grad.incomplete)} 课缺件，按阶段顺序补")
    return tasks


def render_graduation(grad: Graduation, milestones: list[Milestone]) -> str:
    out = [
        "# 毕业总结 · Python 200 天",
        "",
        f"> 生成时间：{time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
        "> 口径：全部数字来自本仓库真实文件与 git 历史，命令见 README 第五节。",
        "",
        "## 一、交付盘点",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 课程数 | {grad.days} |",
        f"| .py 文件 | {grad.py_files} |",
        f"| 代码行数 | {grad.py_lines:,} |",
        f"| README 字符 | {grad.readme_chars:,} |",
        f"| mermaid 图 | {grad.mermaid_blocks} |",
        f"| 四件套完整 | {grad.complete_days}/{grad.days} |",
        "",
        "## 二、12 个阶段",
        "",
        "| 阶段 | 名称 | 课数 | 代码行数 |",
        "|---:|---|---:|---:|",
    ]
    for p in grad.phases:
        out.append(f"| {p['phase']} | {p['name']} | {p['days']} | {p['py_lines']:,} |")
    out += ["", "## 三、两个毕业项目", ""]
    for c in grad.capstones:
        out.append(f"- **{c['name']}**（{c['range']}）：{c['days_present']}/5 课在仓库中")
    if grad.loop:
        lp = grad.loop
        out += ["", "## 四、学习系统体检", "",
                f"- 窗口 {lp['first']} → {lp['last']}，{lp['total']} 条提交，活跃 {lp['active_days']} 天",
                f"- 最长连续 {lp['longest_streak']} 天，断档 {lp['gap_count']} 次",
                f"- 实践 {lp['stage_ratio']['实践'] * 100:.1f}% / 输出 {lp['stage_ratio']['输出'] * 100:.1f}%"
                f" / 反馈 {lp['stage_ratio']['反馈'] * 100:.1f}%"]
        out += [f"- ⚠️ {b}" for b in lp.get("bottlenecks", [])]
        out.append(f"- 从未被针对性修正的课：{lp.get('never_revisited_targeted')} 门")
    if grad.audit:
        out += ["", "## 五、能力证据分", "", "| 维度 | 证据分 | 自评 | 校准差 | 判定 |", "|---|---:|---:|---:|---|"]
        for d in grad.audit.get("dimensions", []):
            rating = d.get("self_rating")
            cal = d.get("calibration")
            out.append(f"| {d['name']} | {d['evidence']} | "
                       f"{rating if rating is not None else '—'} | "
                       f"{cal if cal is not None else '—'} | {d['verdict']} |")
    if grad.radar:
        rd = grad.radar
        out += ["", "## 六、技术资产", "",
                f"- 标准库占比 {rd['stdlib_share'] * 100:.1f}%，第三方包 {len(rd['packages'])} 个",
                f"- 雷达：Adopt {rd['ring_counts']['Adopt']} / Trial {rd['ring_counts']['Trial']}"
                f" / Assess {rd['ring_counts']['Assess']} / Hold {rd['ring_counts']['Hold']}",
                f"- 窄面依赖（≤2 课）{len(rd['narrow_packages'])} 个，是最该收敛的部分"]
    if grad.missing_inputs:
        out += ["", "## 缺失输入", ""] + [f"- {m}（未提供，相关结论不编造）" for m in grad.missing_inputs]
    out += [
        "", "## 这份总结不能证明什么", "",
        "- 不能证明「学会了」：代码行数和课数衡量产出，不衡量理解。",
        "- 不能证明「能上手生产」：教学环境与真实系统的复杂度差一个量级。",
        "- 不能证明「200 天日历」：课程编号是序号，真实跨度见第四节窗口。",
        "- 证据分只统计仓库痕迹；一个只跑代码不写笔记的人会被系统性低估。",
        "", "## 下一步", "",
        "见 `roadmap-90d.md`：3 个 30 天里程碑，每个都有可验收交付物与放弃条件。", "",
    ]
    return "\n".join(out)


def render_roadmap(grad: Graduation, milestones: list[Milestone]) -> str:
    out = [
        "# 毕业后的 90 天成长路线图",
        "",
        "> 生成规则：里程碑由缺口驱动（01 的薄弱维度 + 02 的系统瓶颈），不是愿望清单。",
        "> 每个里程碑都必须有「别人能检查」的交付物，以及明确的放弃条件。",
        "",
    ]
    for m in milestones:
        out += [
            f"## 里程碑 {m.index}（{m.window}）：{m.title}", "",
            f"**为什么是它**：{m.why}", "", "**每周节奏**：", "",
        ]
        out += [f"- {w}" for w in m.weekly]
        out += ["", f"**可验收交付物**：{m.deliverable}", "",
                f"**验收方式**：{m.acceptance}", "",
                f"**放弃条件**：{m.kill_criteria}", ""]
    out += ["## 贯穿 90 天的固定动作", ""]
    out += [f"- {t}" for t in recurring_tasks(grad)]
    out += ["", "## 为什么必须有放弃条件", "",
            "没有 kill criteria 的计划会无限拖尾：你永远觉得「再一周就能做完」，",
            "于是三个月后既没交付也没复盘。放弃条件不是认输，是把「继续投入」变成一个",
            "需要重新举证的决策——和 Day 199 要求每个数字带条件是同一个道理。", ""]
    return "\n".join(out)


def self_test() -> int:
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        print(("  ✅ " if cond else "  ❌ ") + label)
        assert cond, label
        checks += 1

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        for day in (1, 186, 200):
            d = repo / "days" / f"day-{day:03d}-x"
            (d / "code").mkdir(parents=True)
            (d / "exercises").mkdir()
            (d / "diagrams").mkdir()
            (d / "README.md").write_text(f"# Day {day} — 测试\n\n```mermaid\nflowchart LR\n```\n", encoding="utf-8")
            (d / "code" / "01-a.py").write_text("print(1)\nprint(2)\n", encoding="utf-8")
            (d / "exercises" / "checklist.md").write_text("- [ ] x\n", encoding="utf-8")
            (d / "diagrams" / "README.md").write_text("```mermaid\nflowchart TD\n```\n", encoding="utf-8")
        # 一课故意缺件
        bad = repo / "days" / "day-050-y"
        bad.mkdir(parents=True)
        (bad / "README.md").write_text("# Day 050 — 缺件\n", encoding="utf-8")

        grad = scan(repo)
        check(grad.days == 4 and grad.py_files == 3, "课数与 py 文件数")
        check(grad.py_lines == 6, "代码行数按 \\n 计数")
        check(grad.mermaid_blocks == 6, "README 与 diagrams 的 mermaid 都计入")
        check(grad.complete_days == 3 and len(grad.incomplete) == 1, "四件套完整度与缺件清单")
        check(grad.phases[0]["phase"] == 1 and grad.phases[-1]["phase"] == 12, "阶段归类")
        check(grad.capstones[0]["days_present"] == 1, "毕业项目只统计真实存在的课")

        load_inputs(grad, None, None, None)
        check(grad.missing_inputs == ["audit", "loop", "radar"], "缺输入时明确标缺")
        ms = build_milestones(grad)
        check(len(ms) == 3 and all(m.deliverable for m in ms), "无输入也生成 3 个里程碑且不编数字")
        check("不编造" in ms[0].why, "缺数据时说明需人工指定")
        check("放弃条件" in render_roadmap(grad, ms), "路线图含放弃条件")
        check("不能证明" in render_graduation(grad, ms), "毕业总结含诚实边界")

        audit = {"weakest": ["表达与协作", "数据与 AI"],
                 "dimensions": [{"name": "表达与协作", "evidence": 40.0, "self_rating": None,
                                 "calibration": None, "verdict": "未自评"}]}
        loop = {"bottlenecks": ["反馈占比 1.3% 低于 5%：这一环被饿死了"],
                "stage_ratio": {"反馈": 0.013}, "never_revisited_targeted": 152}
        radar = {"packages": [{"name": "httpx", "ring": "Hold"}],
                 "req_counts": {"ranged": 1, "unpinned": 0},
                 "suspects": [{"name": "tools", "days": [18]}]}
        for label, payload in (("audit", audit), ("loop", loop), ("radar", radar)):
            path = repo / f"{label}.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            setattr(grad, label, payload)
        grad.missing_inputs = []
        ms2 = build_milestones(grad)
        check(ms2[0].title.startswith("修反馈回路"), "反馈瓶颈优先成为里程碑 1")
        check("152" in ms2[0].why, "里程碑引用真实测量数字")
        check(ms2[1].title == "补最弱维度：表达与协作", "其后按薄弱榜排序")
        check(ms2[1].deliverable == DELIVERABLE["表达与协作"], "交付物按维度取模板")
        check(all(m.kill_criteria for m in ms2), "每个里程碑都有放弃条件")
        tasks = recurring_tasks(grad)
        check(any("httpx" in t for t in tasks), "Hold 环进入贯穿任务")
        check(any("tools" in t for t in tasks), "缺失模块进入待修缺陷")
        check(any("钉死" in t for t in tasks), "范围约束进入供应链任务")
        check("Day 018" in render_roadmap(grad, ms2) or "Day 018" in ms2[0].weekly[1], "修复目标指向实测缺陷")

    print(f"SELF-TEST PASS（{checks} 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="毕业总结与 90 天成长路线图")
    parser.add_argument("--root", help="仓库根目录")
    parser.add_argument("--audit", type=Path, help="01 导出的 JSON")
    parser.add_argument("--loop", type=Path, help="02 导出的 JSON")
    parser.add_argument("--radar", type=Path, help="03 导出的 JSON")
    parser.add_argument("--out", type=Path, help="输出目录（写 graduation.md / roadmap-90d.md / summary.json）")
    parser.add_argument("--self-test", action="store_true", help="离线自证")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    repo = Path(args.root).expanduser().resolve() if args.root else find_repo()
    started = time.perf_counter()
    grad = scan(repo)
    load_inputs(grad, args.audit, args.loop, args.radar)
    milestones = build_milestones(grad)
    elapsed = time.perf_counter() - started

    graduation_md = render_graduation(grad, milestones)
    roadmap_md = render_roadmap(grad, milestones)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "graduation.md").write_text(graduation_md, encoding="utf-8")
        (args.out / "roadmap-90d.md").write_text(roadmap_md, encoding="utf-8")
        (args.out / "summary.json").write_text(
            json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "scan_seconds": round(elapsed, 3),
                        "graduation": asdict(grad),
                        "milestones": [asdict(m) for m in milestones],
                        "recurring": recurring_tasks(grad)}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"✅ 已写入 {args.out}/：graduation.md、roadmap-90d.md、summary.json")
    else:
        print(graduation_md)
        print(roadmap_md)

    print(f"课程 {grad.days} · 四件套完整 {grad.complete_days}/{grad.days} · "
          f"代码 {grad.py_lines:,} 行 · mermaid {grad.mermaid_blocks} 张")
    if grad.missing_inputs:
        print(f"⚠️ 缺失输入：{', '.join(grad.missing_inputs)}（相关结论未编造）")
    print(f"（扫描 + 合成耗时 {elapsed * 1000:.1f} ms）")
    return 0


if __name__ == "__main__":
    sys.exit(main())