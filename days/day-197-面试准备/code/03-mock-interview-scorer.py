#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day 197 — 本地模拟面试评分器（题库 + 四维评分 + 校准）

为什么自己写一个评分器：
    面试的反馈通常只有「回去等通知」。等通知没有信息量，练十次也不知道改哪里。
    把评分拆成可观测的四维（概念覆盖 / 技术深度 / 表达结构 / 简洁度），
    每次练习都能拿到一张「哪里丢分」的账单。

重要局限（先写在最前面，避免误用）：
    这是**关键词 + 结构启发式**评分器，不懂语义。
    同义改写、正确的非常规答案会被低估；堆关键词的答案会被结构分压住，
    但不能保证 100% 拦住。它适合做「自查清单」，不能替代真人面试。

用法：
    python3 03-mock-interview-scorer.py --list
    python3 03-mock-interview-scorer.py --demo
    python3 03-mock-interview-scorer.py --question py-gil --answer-file answer.txt
    python3 03-mock-interview-scorer.py --calibrate
    python3 03-mock-interview-scorer.py --self-test
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

BANK_PATH = Path(__file__).with_name("interview_bank.json")
DEFAULT_PASS = 60.0

# 四维权重：覆盖是硬门槛，深度区分「背过」与「想过」，结构决定听感
# 覆盖只是入场券：只堆概念不讲结构，总分会被压到及格线下
WEIGHTS = {"coverage": 0.35, "depth": 0.25, "structure": 0.30, "concision": 0.10}

DEPTH_SIGNALS = (
    "复杂度", "因为", "所以", "导致", "因此", "意味着", "取决于", "本质",
    "不变量", "权衡", "实测", "对比", "边界", "缺陷", "限制",
    "原理", "内存", "线程", "进程", "源码", "基准", "o(", "p95", "根因",
)
TECH_STRUCTURE = ("首先", "其次", "然后", "最后", "第一", "第二", "比如", "例如", "总结", "一句话")
STAR_GROUPS = (
    ("背景", "情境", "项目"),
    ("目标", "任务", "负责"),
    ("行动", "做法", "方案", "实现", "措施"),
    ("结果", "指标", "提升", "降低", "节省", "达到"),
)

_SPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """去掉空白并统一小写；中文不分词，直接子串匹配。"""
    return _SPACE.sub("", text).lower()


def keyword_hit(spec: str, text: str) -> bool:
    """支持同义词：must_have 里的 "a|b|c" 命中任意一个即算覆盖。

    为什么需要同义词：同一个概念，候选人不会逐字复述标准答案。
    只认单一写法会把「准确率从 18% 降到 2%」判成没讲指标。
    """
    return any(alt and alt in text for alt in normalize(spec).split("|"))


def load_bank(path: Path = BANK_PATH) -> Dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {q["id"]: q for q in data["questions"]}


@dataclass
class Dimension:
    name: str
    score: float          # 0..1
    weight: float
    detail: str

    @property
    def points(self) -> float:
        return round(self.score * self.weight * 100, 1)


@dataclass
class Result:
    question_id: str
    total: float
    passed: bool
    dimensions: List[Dimension]
    missing: List[str] = field(default_factory=list)
    hits: List[str] = field(default_factory=list)
    advice: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "question_id": self.question_id,
            "total": self.total,
            "passed": self.passed,
            "missing": self.missing,
            "hits": self.hits,
            "dimensions": [
                {"name": d.name, "score": round(d.score, 3), "points": d.points, "detail": d.detail}
                for d in self.dimensions
            ],
            "advice": self.advice,
        }


def _concision(text: str) -> Tuple[float, str]:
    """长度分：80–1200 字满分；过短像敷衍，过长抓不住重点。"""
    n = len(text)
    if 80 <= n <= 1200:
        return 1.0, f"{n} 字，在建议区间 80–1200"
    if n < 80:
        return max(0.0, n / 80 * 0.8), f"{n} 字，偏短（建议 ≥80）"
    # 超过 1200 后线性衰减，4000 字归零
    return max(0.0, 1 - (n - 1200) / 2800), f"{n} 字，偏长（建议 ≤1200）"


def _structure(question: dict, text: str) -> Tuple[float, str]:
    groups = question.get("structure_groups")
    if groups:
        hit_groups = sum(1 for group in groups if any(k in text for k in group))
        # 有数字（指标）额外加权，但不突破 1.0
        has_number = bool(re.search(r"\d", text))
        score = min(1.0, hit_groups / len(groups) + (0.15 if has_number else 0))
        name = "STAR" if question["id"] == "proj-star" else "要点"
        return score, f"{name} 命中 {hit_groups}/{len(groups)} 组" + ("，含量化数字" if has_number else "，缺少数字")
    # 技术题的结构不靠背连接词，而看三件事：
    # ① 有没有先给定义/结论；② 有没有分点（句号/分号分层）；③ 有没有讲边界。
    connectors = sum(1 for k in TECH_STRUCTURE if k in text)
    head = text[:60]
    has_definition = any(k in head for k in ("是", "指", "本质", "意思", "核心"))
    segments = len([s for s in re.split(r"[；。;!?！？]", text) if s])
    has_boundary = any(k in text for k in ("边界", "注意", "但是", "但", "缺陷", "限制", "除非", "否则"))
    score = (
        (0.35 if has_definition else 0.0)
        + (0.35 if segments >= 3 else (0.15 if segments == 2 else 0.0))
        + (0.30 if has_boundary else 0.0)
    )
    return score, (
        f"首句定义={'有' if has_definition else '无'}，分句 {segments} 段，"
        f"边界={'有' if has_boundary else '无'}，连接词 {connectors} 个"
    )


def score_answer(question: dict, answer: str, pass_line: float = DEFAULT_PASS) -> Result:
    text = normalize(answer)
    if not text:
        return Result(question["id"], 0.0, False, [], list(question["must_have"]), [], ["回答为空"])

    must = question["must_have"]
    hits = [k for k in must if keyword_hit(k, text)]
    missing = [k for k in must if not keyword_hit(k, text)]
    coverage = len(hits) / len(must)

    depth_hits = [s for s in DEPTH_SIGNALS if s in text]
    depth = min(1.0, len(depth_hits) / 4)

    structure, structure_detail = _structure(question, text)
    concision, concision_detail = _concision(answer.strip())

    dims = [
        Dimension("概念覆盖", coverage, WEIGHTS["coverage"], f"命中 {len(hits)}/{len(must)}：{', '.join(hits) or '无'}"),
        Dimension("技术深度", depth, WEIGHTS["depth"], f"深度信号 {len(depth_hits)} 个"),
        Dimension("表达结构", structure, WEIGHTS["structure"], structure_detail),
        Dimension("简洁度", concision, WEIGHTS["concision"], concision_detail),
    ]
    total = round(sum(d.points for d in dims), 1)

    advice: List[str] = []
    if missing:
        advice.append("补上这些必要概念：" + "、".join(missing))
    if depth < 0.5:
        advice.append("加一句「为什么」或复杂度/边界分析，别只给结论")
    if structure < 0.5:
        if question["category"] == "project":
            advice.append("用 STAR 组织：背景 → 目标 → 行动 → 结果，并给出数字")
        else:
            advice.append("先给结论，再分 2–3 点展开，最后收一句边界")
    if concision < 0.5:
        advice.append("控制长度：80–1200 字，先讲主线再补细节")
    if not advice:
        advice.append("结构完整；下一步对照追问清单自测")

    return Result(question["id"], total, total >= pass_line, dims, missing, hits, advice)


# ---------------------------------------------------------------------------
# 校准集：8 条人工标注答案（4 通过 / 4 不通过）
# 标注依据：是否覆盖核心概念 + 是否讲清因果 + 是否有结构，而不是文采。
# ---------------------------------------------------------------------------

CALIBRATION: List[Tuple[str, str, str, bool]] = [
    (
        "py-gil-strong",
        "py-gil",
        "GIL 是 CPython 的全局解释器锁，保证同一时刻只有一个线程执行字节码。"
        "所以 CPU 密集型多线程拿不到多核加速，切换反而更慢；IO 密集时等待会释放 GIL，多线程仍然有效。"
        "要真并行就用多进程。",
        True,
    ),
    (
        "py-gil-weak",
        "py-gil",
        "GIL 就是个锁，多线程没什么用，直接用多进程就行了。",
        False,
    ),
    (
        "algo-binary-mid",
        "algo-binary",
        "二分要先确定区间，我习惯左闭右开，循环 lo < hi，更新 hi = mid，这样不会死循环，"
        "退出时 lo 就是插入点，复杂度 O(log n)。",
        True,
    ),
    (
        "algo-binary-weak",
        "algo-binary",
        "就是每次取中间，然后比较大小，大了往左，小了往右，注意 mid 加一减一。",
        False,
    ),
    (
        "proj-star-strong",
        "proj-star",
        "背景是 2000 台服务器的资产靠 Excel 维护，盘点要两周。目标是压到一天内、准确率 95%。"
        "我负责采集和差分：并发 DNS 加端口指纹，SQLite 快照差分，grace 去抖避免抖动误报。"
        "结果是 4 小时完成，漏报从 18% 降到 2%，每周省 30 人时。",
        True,
    ),
    (
        "proj-star-weak",
        "proj-star",
        "做过一个资产管理的项目，挺有挑战的，用了 Python 和数据库，最后上线了，学到很多。",
        False,
    ),
    (
        "py-default-strong",
        "py-default-arg",
        "默认值在 def 执行时只求值一次，挂在函数对象上，所以可变默认值会被所有调用共享，"
        "导致跨调用累积。正确写法是默认 None，函数里判断 if bucket is None 再新建列表。",
        True,
    ),
    (
        "py-default-weak",
        "py-default-arg",
        "默认参数最好别用 list，会有坑，用 None 比较好。",
        False,
    ),
]


def calibrate(bank: Dict[str, dict], pass_line: float = DEFAULT_PASS) -> dict:
    rows = []
    for label, qid, text, expected in CALIBRATION:
        res = score_answer(bank[qid], text, pass_line)
        rows.append((label, expected, res))

    def accuracy_at(line: float) -> float:
        correct = sum(1 for _, expected, res in rows if (res.total >= line) == expected)
        return correct / len(rows)

    # 在 0–100 上按 0.5 步长找最佳阈值；取准确率最高且最接近默认值的那个
    candidates = [i / 2 for i in range(0, 201)]
    best_acc = max(accuracy_at(x) for x in candidates)
    best_lines = [x for x in candidates if accuracy_at(x) == best_acc]
    best_line = min(best_lines, key=lambda x: abs(x - pass_line))

    strong = [r.total for _, exp, r in rows if exp]
    weak = [r.total for _, exp, r in rows if not exp]
    margin = min(strong) - max(weak)

    return {
        "n": len(rows),
        "pass_line": best_line,
        "accuracy": round(best_acc, 3),
        "min_pass_score": min(strong),
        "max_fail_score": max(weak),
        "margin": round(margin, 1),
        # 用「校准出的最佳阈值」判定，而不是调用时的默认阈值
        "rows": [
            {"case": label, "expected_pass": exp, "score": r.total,
             "predicted": r.total >= best_line}
            for label, exp, r in rows
        ],
    }


def aggregate(results: Sequence[Result], bank: Dict[str, dict]) -> dict:
    if not results:
        return {"count": 0, "average": 0.0, "weakest": [], "by_category": {}}
    by_cat: Dict[str, List[float]] = {}
    for r in results:
        cat = bank[r.question_id]["category"]
        by_cat.setdefault(cat, []).append(r.total)
    dim_avg = {}
    for name in ("概念覆盖", "技术深度", "表达结构", "简洁度"):
        vals = [next(d.score for d in r.dimensions if d.name == name) for r in results if r.dimensions]
        dim_avg[name] = round(sum(vals) / len(vals), 3) if vals else 0.0
    weakest = sorted(
        ({"id": r.question_id, "score": r.total} for r in results), key=lambda x: x["score"]
    )[:3]
    return {
        "count": len(results),
        "average": round(sum(r.total for r in results) / len(results), 1),
        "passed": sum(1 for r in results if r.passed),
        "by_category": {k: round(sum(v) / len(v), 1) for k, v in by_cat.items()},
        "dimension_avg": dim_avg,
        "weakest": weakest,
    }


DEMO_ANSWERS = {
    "py-gil": "GIL 是 CPython 的全局解释器锁，保证同一时刻只有一个线程执行字节码。"
              "所以 CPU 密集型多线程拿不到多核加速，IO 密集时等待会释放 GIL，多线程有效；真并行用多进程。",
    "algo-binary": "二分先固定区间为左闭右开，循环 lo < hi，更新 hi = mid，避免死循环，"
                   "退出时 lo 就是插入点，复杂度 O(log n)。",
    "proj-star": "背景是资产盘点靠 Excel，两周才能完成。目标是压到一天内。"
                 "我负责采集与差分，用并发 DNS 和快照差分，加 grace 去抖。"
                 "结果 4 小时完成，漏报从 18% 降到 2%。",
    "py-iterator": "可迭代对象实现 __iter__，迭代器还要 __next__，结束抛 StopIteration。"
                    "生成器用 yield，惰性求值。",
}


def _print_result(bank: Dict[str, dict], res: Result) -> None:
    q = bank[res.question_id]
    mark = "✅ 通过" if res.passed else "❌ 未通过"
    print(f"\n[{res.question_id}] {q['question']}")
    print(f"总分 {res.total}/100  {mark}（及格线 {DEFAULT_PASS:.0f}）")
    for d in res.dimensions:
        print(f"  - {d.name:<6} {d.points:>5.1f} 分  ({d.score:.2f})  {d.detail}")
    if res.missing:
        print("  缺失概念：" + "、".join(res.missing))
    print("  建议：")
    for a in res.advice:
        print(f"    · {a}")
    if q.get("follow_ups"):
        print("  追问准备：")
        for f in q["follow_ups"]:
            print(f"    ? {f}")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day 197 模拟面试评分器")
    parser.add_argument("--list", action="store_true", help="列出题库")
    parser.add_argument("--demo", action="store_true", help="跑四条示例答案")
    parser.add_argument("--question", help="题目 id")
    parser.add_argument("--answer-text", help="直接传回答文本")
    parser.add_argument("--answer-file", help="从文件读回答")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--calibrate", action="store_true", help="跑标注集并给出校准结果")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    bank = load_bank()

    if args.self_test:
        return 0 if run_self_test(bank) else 1

    if args.list:
        for q in bank.values():
            print(f"{q['id']:<18} [{q['category']:<9}] {q['question']}")
        return 0

    if args.calibrate:
        cal = calibrate(bank)
        if args.json:
            print(json.dumps(cal, ensure_ascii=False, indent=2))
        else:
            print(f"校准集 {cal['n']} 条：最佳及格线 {cal['pass_line']}，准确率 {cal['accuracy']:.0%}")
            print(f"通过组最低 {cal['min_pass_score']}，未通过组最高 {cal['max_fail_score']}，间隔 {cal['margin']}")
            for row in cal["rows"]:
                flag = "✓" if row["predicted"] == row["expected_pass"] else "✗"
                print(f"  {flag} {row['case']:<18} 期望={'通过' if row['expected_pass'] else '未通过'} "
                      f"实际={row['score']:>5.1f} ({'通过' if row['predicted'] else '未通过'})")
        return 0

    if args.demo:
        results = [score_answer(bank[qid], text) for qid, text in DEMO_ANSWERS.items()]
        if args.json:
            print(json.dumps({"results": [r.to_dict() for r in results],
                              "summary": aggregate(results, bank)}, ensure_ascii=False, indent=2))
        else:
            for r in results:
                _print_result(bank, r)
            print("\n汇总：" + json.dumps(aggregate(results, bank), ensure_ascii=False))
        return 0

    if args.question:
        if args.question not in bank:
            print(f"未知题目 {args.question!r}，用 --list 查看")
            return 2
        if args.answer_file:
            text = Path(args.answer_file).read_text(encoding="utf-8")
        elif args.answer_text:
            text = args.answer_text
        else:
            print("需要 --answer-text 或 --answer-file")
            return 2
        res = score_answer(bank[args.question], text)
        if args.json:
            print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        else:
            _print_result(bank, res)
        return 0

    parser.print_help()
    return 0


def run_self_test(bank: Dict[str, dict]) -> int:
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        assert cond, label
        checks += 1

    # 1. 所有标准答案都应高分通过
    for qid, q in bank.items():
        res = score_answer(q, q["model_answer"])
        check(res.total >= 70, f"标准答案应 ≥70：{qid} 得 {res.total}")
        check(res.passed, f"标准答案应通过：{qid}")

    # 2. 无效回答接近 0 分
    empty = score_answer(bank["py-gil"], "")
    check(empty.total == 0 and not empty.passed, "空回答应为 0 分")
    check("回答为空" in empty.advice, "空回答应有提示")

    # 3. 无句子的关键词列表不能通过（没有解释结构，长度也不够）
    #    注意：长段落的关键词堆砌仍可能骗过词袋评分，这是本方法的已知局限
    stuffing = "GIL 同一时刻 线程 IO CPU 多进程"
    st = score_answer(bank["py-gil"], stuffing)
    check(st.total < DEFAULT_PASS, f"关键词列表不应通过，实际 {st.total}")

    # 4. 缺概念要进 missing，且给出建议
    short = score_answer(bank["py-gil"], "GIL 是一个锁。")
    check("多进程" in short.missing, "应识别缺失概念")
    check(any("补上" in a for a in short.advice), "应给出补概念建议")

    # 5. 校准集可分，且最佳阈值下准确率 ≥ 0.875
    cal = calibrate(bank)
    check(cal["accuracy"] >= 0.875, f"校准准确率不足：{cal['accuracy']}")
    check(cal["margin"] > 0, f"通过/未通过应有间隔，实际 {cal['margin']}")

    # 6. 汇总
    results = [score_answer(bank[qid], text) for qid, text in DEMO_ANSWERS.items()]
    agg = aggregate(results, bank)
    check(agg["count"] == len(DEMO_ANSWERS), "汇总条数")
    check(0 <= agg["average"] <= 100, "平均分范围")
    check(len(agg["weakest"]) == min(3, len(results)), "最弱题目数量")
    check(set(agg["by_category"]) <= {"python", "algorithm", "project"}, "分类聚合")

    print(f"✅ 03-mock-interview-scorer: {checks} 项断言全部通过（题库 {len(bank)} 题）")
    return checks


if __name__ == "__main__":
    raise SystemExit(main())
