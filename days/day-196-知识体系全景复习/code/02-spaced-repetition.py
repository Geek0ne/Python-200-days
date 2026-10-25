#!/usr/bin/env python3
"""
02-spaced-repetition.py — SM-2 间隔重复排期器（附真实 sqlite 存储）

为什么需要它：
    「今天复习 Day 1–196」等于没复习。人一天能真正回忆的条目有限，
    平均分配时间的结果是每一条都只被浅看一遍。
    间隔重复解决的是「什么时候复习」：在即将忘记的临界点复习，成本最低、留存最高。

原理（SM-2，SuperMemo 2）：
    每张卡片有难度因子 EF（easiness factor，初始 2.5）与当前间隔 I。
    回忆质量 q ∈ [0,5]：
        q < 3  → 视为遗忘：重复次数归零，间隔回到 1 天，EF 不降到底（下限 1.3）
        q >= 3 → 通过：I1=1, I2=6, In=round(I(n-1) * EF)
    EF 更新：EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))，下限 1.3

    为什么是乘法而不是加法：
        间隔必须随「已经记住的强度」增长。加法会让 100 天后的卡片和 10 天前的
        卡片以同样节奏出现，复习量线性膨胀；乘法让间隔指数增长，长期日均复习量收敛。

用法：
    python3 02-spaced-repetition.py --self-test   # 离线自证 SM-2 数值
    python3 02-spaced-repetition.py --demo        # 60 天模拟 + sqlite 基准

注意：
    --demo 里的「回忆」是模拟出来的（指数遗忘曲线 + 固定随机种子），
    用于比较两种排期策略的工作量，不代表任何真实学习者的留存率。
"""

from __future__ import annotations

import argparse
import math
import random
import sqlite3
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import date, timedelta

MIN_EASE = 1.3
START_EASE = 2.5


@dataclass
class Card:
    topic: str
    ease: float = START_EASE
    interval: int = 0
    reps: int = 0
    lapses: int = 0
    due: date | None = None
    last_review: date | None = None

    def review(self, quality: int, today: date) -> None:
        """按 SM-2 更新卡片状态。quality 必须落在 0..5，静默夹取会掩盖调用错误。"""
        if not 0 <= quality <= 5:
            raise ValueError(f"quality must be 0..5, got {quality}")

        if quality < 3:
            self.reps = 0
            self.lapses += 1
            self.interval = 1
        else:
            self.reps += 1
            if self.reps == 1:
                self.interval = 1
            elif self.reps == 2:
                self.interval = 6
            else:
                self.interval = max(1, round(self.interval * self.ease))

        delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        self.ease = max(MIN_EASE, self.ease + delta)
        self.last_review = today
        self.due = today + timedelta(days=self.interval)


class CardStore:
    """sqlite 持久化。日期统一存 ISO 字符串（YYYY-MM-DD），便于比较与人工排查。"""

    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY,
                topic TEXT NOT NULL UNIQUE,
                ease REAL NOT NULL,
                interval_days INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                lapses INTEGER NOT NULL,
                due TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def upsert(self, card: Card) -> None:
        assert card.due is not None
        self.conn.execute(
            """
            INSERT INTO cards (topic, ease, interval_days, reps, lapses, due)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic) DO UPDATE SET
                ease=excluded.ease,
                interval_days=excluded.interval_days,
                reps=excluded.reps,
                lapses=excluded.lapses,
                due=excluded.due
            """,
            (card.topic, card.ease, card.interval, card.reps, card.lapses, card.due.isoformat()),
        )

    def due_on(self, day: date) -> list[tuple[str, float, int]]:
        rows = self.conn.execute(
            "SELECT topic, ease, interval_days FROM cards WHERE due <= ? ORDER BY due, topic",
            (day.isoformat(),),
        ).fetchall()
        return rows

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]

    def close(self) -> None:
        self.conn.close()


def recall_probability(card: Card, day: date) -> float:
    """模拟学习者的回忆概率：R = exp(-t/S)，S = 3 × 当前间隔。

    S 取 3 倍间隔意味着「到期那天」R≈0.72，而不是 1.0——
    这是刻意设置：真实复习到期时本来就该有一点想不起来，全对反而说明间隔太短。
    这是模拟器，不是任何真实学习者的记忆测量。
    """
    if card.last_review is None:
        return 0.0
    elapsed = max(0, (day - card.last_review).days)
    stability = max(1.0, card.interval * 3.0)
    return math.exp(-elapsed / stability)


def simulate(days: int, cards: list[Card], rng: random.Random, scheduler: str) -> dict:
    """跑 N 天。scheduler='sm2' 用 SM-2；'fixed' 每 7 天固定复习。

    两种策略共用同一个学习者模型与同一个随机种子，差异只来自排期。
    """
    today = date(2026, 1, 1)
    reviews = failures = 0
    per_day: list[int] = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        if scheduler == "sm2":
            due = [c for c in cards if c.due is not None and c.due <= day]
        else:
            due = [c for c in cards if c.due == day]
        per_day.append(len(due))
        for card in due:
            q = 5 if rng.random() < recall_probability(card, day) else 2
            if q < 3:
                failures += 1
            reviews += 1
            if scheduler == "sm2":
                card.review(q, day)
            else:
                card.interval = 7
                card.last_review = day
                card.due = day + timedelta(days=7)
    final_day = today + timedelta(days=days - 1)
    return {
        "reviews": reviews,
        "failures": failures,
        "per_day": per_day,
        "avg_per_day": reviews / days,
        "max_per_day": max(per_day),
        "retention": statistics.mean(recall_probability(c, final_day) for c in cards),
    }


def demo() -> int:
    rng = random.Random(20261026)
    day0 = date(2026, 1, 1)
    topics = [
        "语法与数据类型", "函数与作用域", "OOP 与魔法方法", "装饰器与生成器",
        "标准库", "项目工程化", "性能优化", "NumPy/Pandas", "爬虫与反爬",
        "Web 安全", "DevOps", "综合实战",
    ]

    # ── 真机基准：1 万张卡批量写入 + 到期查询
    store = CardStore()
    t0 = time.perf_counter()
    with store.conn:
        for i in range(10_000):
            store.upsert(Card(topic=f"bench-{i}", due=day0 + timedelta(days=i % 30)))
    insert_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    due_rows = store.due_on(day0 + timedelta(days=10))
    query_ms = (time.perf_counter() - t0) * 1000
    total = store.count()
    store.close()

    print("== sqlite 基准（本机实测）==")
    print(f"写入 10,000 张卡：{insert_ms:.1f} ms（{insert_ms / 10_000 * 1000:.1f} µs/张）")
    print(f"到期查询：{len(due_rows)} 条，{query_ms:.2f} ms；表内共 {total} 张")

    # ── 两种排期策略对比（模拟，同一学习者模型，同一种子）
    def make_cards() -> list[Card]:
        # 第一天全部到期：所有卡都算「刚学完」，上一次复习就是 day0
        return [Card(topic=t, due=day0, last_review=day0, interval=1) for t in topics]

    sm2_cards = make_cards()
    fixed_cards = make_cards()
    sm2 = simulate(180, sm2_cards, random.Random(20261026), "sm2")
    fixed = simulate(180, fixed_cards, random.Random(20261026), "fixed")

    print("\n== 180 天工作量对比（12 张卡，模拟回忆，种子 20261026）==")
    print(f"{'策略':<10}{'总复习':>8}{'日均':>8}{'峰值':>6}{'遗忘次数':>8}{'平均间隔':>9}{'期末留存':>9}")
    for name, result, cards in (("SM-2", sm2, sm2_cards), ("固定 7 天", fixed, fixed_cards)):
        avg_interval = statistics.mean(c.interval for c in cards)
        print(f"{name:<10}{result['reviews']:>8}{result['avg_per_day']:>8.2f}"
              f"{result['max_per_day']:>6}{result['failures']:>8}"
              f"{avg_interval:>9.1f}{result['retention']:>9.2f}")

    print("\n== 30 天后的日复习量（前 15 天）==")
    print("SM-2  :", sm2["per_day"][:15])
    print("固定   :", fixed["per_day"][:15])

    # 排期是否真的变长？打印一张卡的完整轨迹
    sample = sm2_cards[0]
    print(f"\n样本卡「{sample.topic}」：reps={sample.reps} ease={sample.ease:.2f} "
          f"interval={sample.interval} 天 lapses={sample.lapses}")
    return 0


def self_test() -> int:
    # 连续 q=5：1 → 6 → 16 → 45（EF 2.5→2.6→2.7→2.8→2.9）
    card = Card(topic="t")
    seq = []
    today = date(2026, 1, 1)
    for _ in range(4):
        card.review(5, today)
        seq.append(card.interval)
        today = card.due  # type: ignore[assignment]
    assert seq == [1, 6, 16, 45], seq
    assert abs(card.ease - 2.9) < 1e-9, card.ease

    # q=2：归零 + 1 天 + EF 下降 0.32
    c2 = Card(topic="u", ease=2.5, interval=20, reps=5)
    c2.review(2, date(2026, 1, 1))
    assert c2.interval == 1 and c2.reps == 0 and c2.lapses == 1
    assert abs(c2.ease - (2.5 - 0.32)) < 1e-9, c2.ease

    # EF 下限
    c3 = Card(topic="v", ease=1.3)
    c3.review(0, date(2026, 1, 1))
    assert c3.ease == 1.3

    # 越界 quality 必须报错
    try:
        Card(topic="w").review(6, date(2026, 1, 1))
    except ValueError:
        pass
    else:
        raise AssertionError("quality=6 应抛 ValueError")

    # sqlite 往返 + 到期筛选
    store = CardStore()
    store.upsert(Card(topic="a", interval=1, due=date(2026, 1, 2)))
    store.upsert(Card(topic="b", interval=6, due=date(2026, 1, 7)))
    assert [r[0] for r in store.due_on(date(2026, 1, 3))] == ["a"]
    assert store.count() == 2
    store.close()
    print("✅ self-test passed: SM-2 序列/遗忘重置/EF 下限/sqlite 往返 均符合预期")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SM-2 间隔重复排期")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.demo:
        return demo()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
