#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01-skill-audit.py — 能力模型与「证据锚定」自评

为什么要有这个脚本：
    毕业那天最危险的一句话是「我感觉我学得还行」。
    感觉不可比较、不可追踪、也无法被反驳——它既不能告诉你该补哪里，
    也不能在三个月后告诉你有没有进步。
    所以自评必须挂在一个可数的东西上：仓库里留下的痕迹。

它做什么：
    1. 扫描 days/ 下每一课，按「证据阶梯」定级（L1 读过 → L4 交付过）
    2. 把课归入 8 个跨阶段的能力维度，算出每个维度的证据分（0–100）
    3. 读入你的自评分，算校准差 = 自评 − 证据分，标出高估 / 低估
    4. 输出人读表格 / Markdown / JSON，JSON 供 04-growth-roadmap.py 消费

用法：
    python 01-skill-audit.py                          # 只算证据分
    python 01-skill-audit.py --ratings self-rating.example.json
    python 01-skill-audit.py --markdown audit.md
    python 01-skill-audit.py --json audit.json
    python 01-skill-audit.py --self-test              # 离线自证，不依赖本仓库

诚实边界（重要）：
    证据分衡量的是「仓库里的痕迹」，不是「你脑子里的能力」。
    它只能证伪「我没学过」，不能证明「我会」。
    一个把笔记抄得很全的人可以拿高分，一个只跑代码不写笔记的人会拿低分。
    所以校准差要双向读：高估要补证据，低估要补外部验证（面试 / 开源 / 读者）。

设计要点：
    - 只依赖标准库；Python 3.10+
    - 维度区间是人工策展的，写在 DIMENSIONS 里，读者可以改
    - 一课可以支撑多个维度（刻意重叠），分母各自独立
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
from dataclasses import dataclass, asdict, field
from pathlib import Path

# Windows 默认控制台是 GBK，打印 ✅ 会抛 UnicodeEncodeError
# stderr 也要切，否则 traceback 里的中文路径仍然是乱码
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

DAY_DIR_RE = re.compile(r"^day-(\d{3})-")
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
PROJECT_RE = re.compile(r"项目|阶段|实战")

# 证据阶梯：等级 -> (名字, 权重)。权重是序数，不是能力倍数。
LEVELS: dict[int, tuple[str, int]] = {
    1: ("读过", 1),
    2: ("跑过", 2),
    3: ("自证过", 3),
    4: ("交付过", 4),
}
MAX_WEIGHT = max(w for _, w in LEVELS.values())

# 交付物信号：出现任意一个，就把这一课顶到 L4
DELIVERABLES = (
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "smoke_test.py",
)
DELIVERABLE_DIRS = ("deploy", "ci", "workflows")

# 8 个能力维度。区间跨阶段，刻意重叠：一天可以同时支撑多个维度。
DIMENSIONS: list[tuple[str, tuple[tuple[int, int], ...]]] = [
    ("语言与数据模型", ((1, 30), (46, 58), (95, 98))),
    ("工程化与质量", ((31, 45), (72, 75), (180, 181))),
    ("并发与性能", ((54, 60), (91, 94), (99, 100))),
    ("数据与 AI", ((79, 81), (101, 125))),
    ("网络与爬虫", ((64, 71), (76, 78), (126, 145))),
    ("安全与合规", ((146, 165), (186, 190))),
    ("运维与交付", ((82, 84), (166, 179), (182, 185), (191, 195))),
    # 窄口径：只计总复习 5 天。「会做」和「会讲」是两件事，不混算。
    ("表达与协作", ((196, 200),)),
]

CALIBRATION_BAND = 15  # 校准差在 ±15 内算「基本一致」，产品判断而非统计结论


def disp_width(text: str) -> int:
    """中文/全角字符占两列。str.ljust 按码点数补齐，中文表格一定会歪。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def pad(text: str, size: int, right: bool = False) -> str:
    gap = " " * max(size - disp_width(text), 0)
    return gap + text if right else text + gap


def expand(ranges: tuple[tuple[int, int], ...]) -> set[int]:
    return {d for lo, hi in ranges for d in range(lo, hi + 1)}


def find_repo(start: Path | None = None) -> Path:
    """从脚本位置向上找含 days/ 的目录，避免硬编码 ~/code 这种跨机器失效的路径。"""
    env = os.environ.get("LEARN_PYTHON_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "days").is_dir():
            return candidate
    raise SystemExit("找不到仓库根（含 days/ 的目录）；用 --root 或 LEARN_PYTHON_ROOT 指定")


@dataclass
class DayEvidence:
    day: int
    slug: str
    title: str
    level: int
    signals: list[str] = field(default_factory=list)

    @property
    def level_name(self) -> str:
        return LEVELS[self.level][0]

    @property
    def weight(self) -> int:
        return LEVELS[self.level][1]


@dataclass
class DimensionScore:
    name: str
    expected: int
    covered: int
    missing: list[int]
    evidence: float
    level_hist: dict[str, int]
    self_rating: float | None = None
    calibration: float | None = None
    verdict: str = "未自评"


def read_title(readme: Path) -> str:
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = H1_RE.search(text)
    return match.group(1).strip() if match else ""


def grade_day(path: Path, day: int) -> DayEvidence:
    """给一课定级。取能命中的最高等级，并把命中信号记下来供人工核对。"""
    signals: list[str] = []
    readme = path / "README.md"
    title = read_title(readme)
    level = 0

    if readme.is_file() and len(readme.read_text(encoding="utf-8", errors="replace")) > 200:
        level = 1
        signals.append("README > 200 字符")

    code_dir = path / "code"
    py_files = [p for p in code_dir.rglob("*.py") if "__pycache__" not in p.parts] if code_dir.is_dir() else []
    if py_files:
        level = 2
        signals.append(f"{len(py_files)} 个 .py")

    selftested = 0
    for py in py_files:
        try:
            if "--self-test" in py.read_text(encoding="utf-8", errors="replace"):
                selftested += 1
        except OSError:
            continue
    if selftested:
        level = 3
        signals.append(f"{selftested} 个脚本带 --self-test")

    hits = [name for name in DELIVERABLES if (code_dir / name).exists()]
    hits += [f"{d}/" for d in DELIVERABLE_DIRS if (path / d).is_dir() or (code_dir / d).is_dir()]
    if (path / "article" / "post.md").is_file():
        hits.append("article/post.md")
    if title and PROJECT_RE.search(title):
        hits.append("标题含项目/阶段/实战")
    if hits:
        level = 4
        signals.append("交付物: " + ", ".join(hits[:3]))

    return DayEvidence(day=day, slug=path.name, title=title or f"(无 README) {path.name}",
                       level=max(level, 1), signals=signals)


def scan(repo: Path) -> tuple[list[DayEvidence], float]:
    days_dir = repo / "days"
    if not days_dir.is_dir():
        raise SystemExit(f"找不到 days/ 目录: {days_dir}")
    started = time.perf_counter()
    out: list[DayEvidence] = []
    for child in sorted(days_dir.iterdir()):
        match = DAY_DIR_RE.match(child.name)
        if not child.is_dir() or not match:
            continue
        out.append(grade_day(child, int(match.group(1))))
    out.sort(key=lambda e: e.day)
    return out, time.perf_counter() - started


def load_ratings(path: Path, scale: int) -> dict[str, float]:
    """读自评分。scale=5 时按星级换算成百分制；维度名必须对得上，否则直接报错。"""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit("自评文件必须是 {维度名: 分数} 的 JSON 对象")
    known = {name for name, _ in DIMENSIONS}
    unknown = set(raw) - known
    if unknown:
        raise SystemExit(f"未知维度: {sorted(unknown)}；可用维度: {sorted(known)}")
    ratings: dict[str, float] = {}
    for name, value in raw.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SystemExit(f"{name} 的分数必须是数字，收到 {value!r}")
        num = float(value)
        if scale == 5:
            if not 1 <= num <= 5:
                raise SystemExit(f"{name}: 星级必须在 1–5，收到 {num}")
            num *= 20
        elif not 0 <= num <= 100:
            raise SystemExit(f"{name}: 百分制必须在 0–100，收到 {num}")
        ratings[name] = num
    return ratings


def score(evidences: list[DayEvidence], ratings: dict[str, float] | None = None) -> list[DimensionScore]:
    by_day = {e.day: e for e in evidences}
    ratings = ratings or {}
    scores: list[DimensionScore] = []
    for name, ranges in DIMENSIONS:
        wanted = expand(ranges)
        present = sorted(wanted & by_day.keys())
        hist: dict[str, int] = {}
        total = 0
        for day in present:
            ev = by_day[day]
            hist[ev.level_name] = hist.get(ev.level_name, 0) + 1
            total += ev.weight
        # 分母用「实际存在的课」，缺失的课单独报，不混进分数里稀释结论
        evidence = round(total / (len(present) * MAX_WEIGHT) * 100, 1) if present else 0.0
        item = DimensionScore(
            name=name, expected=len(wanted), covered=len(present),
            missing=sorted(wanted - by_day.keys()), evidence=evidence, level_hist=hist,
        )
        if name in ratings:
            item.self_rating = ratings[name]
            item.calibration = round(item.self_rating - evidence, 1)
            if item.calibration > CALIBRATION_BAND:
                item.verdict = "高估：补证据"
            elif item.calibration < -CALIBRATION_BAND:
                item.verdict = "低估：去外部验证"
            else:
                item.verdict = "基本一致"
        scores.append(item)
    return scores


def weakest(scores: list[DimensionScore], top: int = 3) -> list[DimensionScore]:
    return sorted(scores, key=lambda s: (s.evidence, s.name))[:top]


def render_table(scores: list[DimensionScore], evidences: list[DayEvidence], elapsed: float) -> str:
    out = [
        f"扫描 {len(evidences)} 课，耗时 {elapsed * 1000:.1f} ms",
        f"证据阶梯：L1 读过(1) → L2 跑过(2) → L3 自证过(3) → L4 交付过(4)",
        "",
        pad("能力维度", 16) + pad("课数", 5, True) + pad("证据分", 8, True)
        + pad("自评", 7, True) + pad("校准差", 8, True) + "  判定",
        "-" * 68,
    ]
    for s in scores:
        rating = f"{s.self_rating:.0f}" if s.self_rating is not None else "—"
        cal = f"{s.calibration:+.1f}" if s.calibration is not None else "—"
        out.append(
            pad(s.name, 16) + pad(str(s.covered), 5, True) + pad(f"{s.evidence:.1f}", 8, True)
            + pad(rating, 7, True) + pad(cal, 8, True) + "  " + s.verdict
        )
    out.append("")
    out.append("等级分布（全仓库）：")
    hist: dict[str, int] = {}
    for ev in evidences:
        hist[ev.level_name] = hist.get(ev.level_name, 0) + 1
    for level in sorted(LEVELS, reverse=True):
        name = LEVELS[level][0]
        count = hist.get(name, 0)
        bar = "█" * round(count / max(len(evidences), 1) * 40)
        out.append(f"  L{level} {pad(name, 8)}{pad(str(count), 4, True)} 课 {bar}")
    gaps = [s for s in scores if s.missing]
    if gaps:
        out.append("")
        for s in gaps:
            out.append(f"⚠️ {s.name} 缺失课：{s.missing}")
    out.append("")
    out.append("最薄弱的三个维度（04 会拿它们生成里程碑）：")
    for i, s in enumerate(weakest(scores), 1):
        out.append(f"  {i}. {s.name}  证据分 {s.evidence:.1f}  覆盖 {s.covered}/{s.expected} 课")
    out.append("")
    out.append("注意：证据分只统计仓库痕迹，不等于真实能力；校准差要双向读。")
    return "\n".join(out)


def render_markdown(scores: list[DimensionScore], evidences: list[DayEvidence]) -> str:
    out = [
        "# 能力自评（证据锚定）",
        "",
        f"- 扫描课数：{len(evidences)}",
        f"- 生成时间：{time.strftime('%Y-%m-%dT%H:%M:%S%z')}",
        "- 口径：L1 读过 / L2 跑过 / L3 自证过 / L4 交付过，权重 1/2/3/4",
        "",
        "| 能力维度 | 覆盖课数 | 证据分 | 自评 | 校准差 | 判定 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for s in scores:
        rating = f"{s.self_rating:.0f}" if s.self_rating is not None else "—"
        cal = f"{s.calibration:+.1f}" if s.calibration is not None else "—"
        out.append(f"| {s.name} | {s.covered}/{s.expected} | {s.evidence:.1f} | {rating} | {cal} | {s.verdict} |")
    out += ["", "## 薄弱维度", ""]
    for s in weakest(scores):
        out.append(f"- **{s.name}**：证据分 {s.evidence:.1f}，等级分布 {s.level_hist}")
    out += ["", "> 证据分只能证伪「没学过」，不能证明「会」。高估补证据，低估补外部验证。", ""]
    return "\n".join(out)


def self_test() -> int:
    """造一个临时仓库验证定级与打分，不依赖真实仓库，可离线跑。"""
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        print(("  ✅ " if cond else "  ❌ ") + label)
        assert cond, label
        checks += 1

    check(disp_width("能力") == 4, "中文按两列宽计算")
    check(pad("能力", 8) == "能力    ", "中文左对齐补齐到 8 列")
    check(pad("ab", 5, True) == "   ab", "ASCII 右对齐补齐")

    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        days = repo / "days"

        # day-001：只有 README → L1
        d1 = days / "day-001-只读"
        d1.mkdir(parents=True)
        (d1 / "README.md").write_text("# Day 001 — 只读\n\n" + "正文" * 200, encoding="utf-8")
        # day-016：README + 普通脚本 → L2
        d16 = days / "day-016-跑过"
        (d16 / "code").mkdir(parents=True)
        (d16 / "README.md").write_text("# Day 016 — 跑过\n\n" + "正文" * 200, encoding="utf-8")
        (d16 / "code" / "01-x.py").write_text("print('x')\n", encoding="utf-8")
        # day-196：带 --self-test → L3
        d196 = days / "day-196-自证"
        (d196 / "code").mkdir(parents=True)
        (d196 / "README.md").write_text("# Day 196 — 自证\n\n" + "正文" * 200, encoding="utf-8")
        (d196 / "code" / "01-x.py").write_text("# --self-test\n", encoding="utf-8")
        # day-183：有 requirements.txt → L4
        d183 = days / "day-183-交付"
        (d183 / "code").mkdir(parents=True)
        (d183 / "README.md").write_text("# Day 183 — 交付\n\n" + "正文" * 200, encoding="utf-8")
        (d183 / "code" / "01-x.py").write_text("# --self-test\n", encoding="utf-8")
        (d183 / "code" / "requirements.txt").write_text("flask==3.0.0\n", encoding="utf-8")
        # 干扰项：不符合命名的目录 + __pycache__
        (days / "not-a-day").mkdir()
        cache = d196 / "code" / "__pycache__"
        cache.mkdir()
        (cache / "junk.py").write_text("# --self-test\n", encoding="utf-8")

        ev, _ = scan(repo)
        check([e.day for e in ev] == [1, 16, 183, 196], "只认 day-NNN- 目录且按序")
        levels = {e.day: e.level for e in ev}
        check(levels == {1: 1, 16: 2, 183: 4, 196: 3}, f"证据阶梯定级正确 {levels}")
        check(ev[2].weight == 4, "L4 权重为 4")

        scores = score(ev)
        check(len(scores) == len(DIMENSIONS), "8 个维度都出分")
        by_name = {s.name: s for s in scores}
        check(by_name["表达与协作"].covered == 1, "表达维度只命中 day-196")
        check(by_name["表达与协作"].missing == [197, 198, 199, 200], "缺失课被单独报出")
        check(by_name["运维与交付"].evidence == 100.0, "唯一一课是 L4 → 证据分 100")
        check(by_name["语言与数据模型"].evidence == round((1 + 2) / (2 * 4) * 100, 1),
              "混合等级按权重求均值")

        # 夹具里表达维度只有 day-196（L3），证据分 = 3/4 = 75，不是低分
        check(by_name["表达与协作"].evidence == 75.0, "表达维度证据分 75（L3 单课）")
        rated = score(ev, {"表达与协作": 95.0, "运维与交付": 20.0})
        rn = {s.name: s for s in rated}
        check(rn["表达与协作"].verdict == "高估：补证据", "自评高于证据 20 分 → 高估")
        check(rn["运维与交付"].verdict == "低估：去外部验证", "自评远低于证据 → 低估")
        check(rn["语言与数据模型"].verdict == "未自评", "没给自评分的维度不硬判")
        edge = score(ev, {"表达与协作": 75.0 + CALIBRATION_BAND})
        check({s.name: s for s in edge}["表达与协作"].verdict == "基本一致",
              "校准差正好 +15 落在带内（边界算一致）")

        check(weakest(scores)[0].evidence <= weakest(scores)[-1].evidence, "薄弱排序升序")
        check("证据分" in render_markdown(scores, ev), "Markdown 视图可生成")

        rating_file = repo / "r.json"
        rating_file.write_text(json.dumps({"表达与协作": 4}), encoding="utf-8")
        check(load_ratings(rating_file, 5)["表达与协作"] == 80.0, "星级 4 → 80 分")
        rating_file.write_text(json.dumps({"不存在的维度": 4}), encoding="utf-8")
        try:
            load_ratings(rating_file, 100)
            check(False, "未知维度应当报错")
        except SystemExit:
            check(True, "未知维度直接报错，不静默忽略")

    print(f"SELF-TEST PASS（{checks} 条）")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="能力模型与证据锚定自评")
    parser.add_argument("--root", help="仓库根目录（默认从脚本位置向上找，或用 LEARN_PYTHON_ROOT）")
    parser.add_argument("--ratings", metavar="JSON", help="自评分文件 {维度名: 分数}")
    parser.add_argument("--scale", type=int, choices=(5, 100), default=100, help="自评分制，默认百分制")
    parser.add_argument("--json", metavar="PATH", help="导出结构化结果（供 04 消费）")
    parser.add_argument("--markdown", metavar="PATH", help="导出 Markdown 报告")
    parser.add_argument("--self-test", action="store_true", help="离线自证")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    repo = Path(args.root).expanduser().resolve() if args.root else find_repo()
    evidences, elapsed = scan(repo)
    ratings = load_ratings(Path(args.ratings), args.scale) if args.ratings else {}
    scores = score(evidences, ratings)

    if args.json:
        payload = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "repo": str(repo),
            "total_days": len(evidences),
            "calibration_band": CALIBRATION_BAND,
            "dimensions": [asdict(s) for s in scores],
            "weakest": [s.name for s in weakest(scores)],
            "days": [asdict(e) for e in evidences],
        }
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {args.json}")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(scores, evidences), encoding="utf-8")
        print(f"已写入 {args.markdown}")
    print(render_table(scores, evidences, elapsed))
    return 0


if __name__ == "__main__":
    sys.exit(main())