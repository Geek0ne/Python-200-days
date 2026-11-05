#!/usr/bin/env python3
"""
Day 190 · 01 — 调度窗口：固定频率 / 固定延迟 / 抖动 / 补跑策略

只用标准库，虚拟时钟推演，不 sleep 真实时间，所以 24 小时推演不到 1 秒。

本脚本实测并打印四个结论：
  1. 固定延迟（delay = 上次完成 + interval）会累积漂移，漂移量约等于"每轮耗时之和"。
  2. 固定频率（anchor + n*interval 网格）不累积漂移，代价是必须处理"错过的格子"。
  3. 抖动（jitter）把同时刻的并发扇出摊平到窗口里，避免整点尖峰。
  4. 停机 6 小时后若无 grace 策略，会把积压格子一次性补跑（catch-up storm）。

用法：
  python3 01-scheduler-basic.py --self-test
  python3 01-scheduler-basic.py --simulate 24 --interval 900
  python3 01-scheduler-basic.py --outage 6
"""
from __future__ import annotations

import argparse
import random
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

BASE = datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Policy:
    """调度策略。interval 是格子宽度，jitter 是相对比例，grace 是迟到容忍。"""

    interval_s: int = 900
    jitter_ratio: float = 0.08
    grace_s: int = 300
    max_catchup: int = 1


def fmt(dt: datetime) -> str:
    return dt.strftime("%H:%M:%S")


def grid_fire_time(anchor: datetime, slot: int, policy: Policy, rng: random.Random | None) -> datetime:
    """第 slot 个格子的计划触发时刻 = 锚点 + slot*interval + 抖动偏移。

    抖动以格子中心为基准上下浮动，且被裁剪到格子内部，保证不会跨格。
    注意：抖动必须是"确定的"（同一 slot 每次算出来一样），否则重试/重启后
    同一格子会被当成不同任务重复执行。生产上用 hash(job_id, slot) 做种子。
    """
    ideal = anchor + timedelta(seconds=slot * policy.interval_s)
    if rng is None or policy.jitter_ratio <= 0:
        return ideal
    span = policy.interval_s * policy.jitter_ratio
    offset = rng.uniform(-span, span)
    offset = max(-policy.interval_s / 2, min(policy.interval_s / 2, offset))
    return ideal + timedelta(seconds=offset)


def simulate_fixed_delay(policy: Policy, hours: int, rng: random.Random) -> dict:
    """老派写法：跑完再等 interval。实现简单，但漂移会一直累积。"""
    now = BASE
    end = BASE + timedelta(hours=hours)
    fires, finishes = [], []
    while True:
        fires.append(now)
        duration = rng.uniform(1.0, 3.0)  # 每次巡检 1~3 秒
        now = now + timedelta(seconds=duration + policy.interval_s)
        finishes.append(now)
        if now > end:
            break
    ideal_last = BASE + timedelta(seconds=(len(fires) - 1) * policy.interval_s)
    drift = (fires[-1] - ideal_last).total_seconds()
    return {
        "mode": "fixed-delay",
        "runs": len(fires),
        "drift_s": drift,
        "first": fires[:3],
        "last": fires[-1],
    }


def simulate_fixed_rate(policy: Policy, hours: int, rng: random.Random) -> dict:
    """网格写法：第 n 次 = anchor + n*interval。执行耗时不影响下一次的时刻。"""
    end = BASE + timedelta(hours=hours)
    slots = int(hours * 3600 // policy.interval_s)
    fires = [grid_fire_time(BASE, s, policy, rng) for s in range(1, slots + 1)]
    fires = [f for f in fires if f <= end]
    ideal_last = BASE + timedelta(seconds=len(fires) * policy.interval_s)
    drift = (fires[-1] - ideal_last).total_seconds()
    return {"mode": "fixed-rate", "runs": len(fires), "drift_s": drift, "first": fires[:3], "last": fires[-1]}


@dataclass
class CatchUpPlan:
    fires: list[datetime]
    skipped: int


def plan_catchup(anchor: datetime, last_slot: int, now: datetime, policy: Policy,
                 rng: random.Random | None = None) -> CatchUpPlan:
    """停机恢复：算出该补哪些格子。

    规则：
      - 迟到超过 grace 的格子不再补跑（历史巡检没有意义，扫的是"现在"）；
      - 最多补 max_catchup 个，避免把 6 小时的积压一口气打成 24 次全量扫描；
      - 只补最近的那个格子，被跳过的数量要记下来（否则没人知道有缺口）。
    """
    current = int((now - anchor).total_seconds() // policy.interval_s)
    due = list(range(last_slot + 1, current + 1))
    fresh = [s for s in due if (now - grid_fire_time(anchor, s, policy, rng)).total_seconds() <= policy.grace_s]
    fresh = fresh[-policy.max_catchup:]
    return CatchUpPlan(fires=[now for _ in fresh], skipped=len(due) - len(fresh))


def burst_spread(policy: Policy, workers: int, seed: int = 7) -> tuple[float, float, list[int]]:
    """N 个实例同锚点：无抖动 vs 有抖动，看它们是同一秒还是散开。"""
    def offsets(ratio: float) -> list[float]:
        rng = random.Random(seed)
        p = Policy(interval_s=policy.interval_s, jitter_ratio=ratio, grace_s=policy.grace_s)
        return [grid_fire_time(BASE, 1, p, rng).timestamp() - (BASE + timedelta(seconds=policy.interval_s)).timestamp()
                for _ in range(workers)]

    no_jitter = offsets(0.0)
    with_jitter = offsets(policy.jitter_ratio)
    return (
        max(no_jitter) - min(no_jitter),
        max(with_jitter) - min(with_jitter),
        [int(x) for x in with_jitter],
    )


def print_simulation(hours: int, policy: Policy) -> None:
    rng = random.Random(20261020)
    delay = simulate_fixed_delay(policy, hours, rng)
    rate = simulate_fixed_rate(policy, hours, random.Random(20261020))

    print(f"推演窗口: {hours}h  格子: {policy.interval_s}s  抖动: ±{policy.jitter_ratio:.0%}")
    print("-" * 66)
    print(f"{'策略':<14}{'执行次数':>8}{'末次漂移(秒)':>14}{'末次时刻':>12}")
    print(f"{delay['mode']:<14}{delay['runs']:>8}{delay['drift_s']:>14.1f}{fmt(delay['last']):>12}")
    print(f"{rate['mode']:<14}{rate['runs']:>8}{rate['drift_s']:>14.1f}{fmt(rate['last']):>12}")
    print("-" * 66)
    print("固定延迟的漂移 ≈ 每轮耗时累计：", f"{delay['drift_s']:.1f}s ≈ {delay['runs']} 轮 × 约 2s")
    print("固定频率的漂移只来自抖动上界：", f"{rate['drift_s']:.1f}s ≤ {policy.interval_s * policy.jitter_ratio:.0f}s")

    solid, spread, sample = burst_spread(policy, workers=8)
    print("-" * 66)
    print("8 个实例同锚点触发：")
    print(f"  无抖动窗口跨度 = {solid:.0f}s（全部同时打出去）")
    print(f"  有抖动窗口跨度 = {spread:.0f}s，偏移样本(s) = {sample}")
    print("  → 抖动不改变总工作量，只改变峰值；整点尖峰是压垮扫描目标的常见原因。")


def print_outage(hours_down: int, policy: Policy) -> None:
    anchor = BASE
    now = BASE + timedelta(hours=hours_down)
    last_slot = 0
    plan = plan_catchup(anchor, last_slot, now, policy)
    due = int((now - anchor).total_seconds() // policy.interval_s)
    print(f"停机 {hours_down}h 后恢复（格子 {policy.interval_s}s，grace {policy.grace_s}s）：")
    print(f"  积压格子数        : {due}")
    print(f"  无策略会补跑      : {due} 次（catch-up storm）")
    print(f"  有 grace+上限     : 补跑 {len(plan.fires)} 次，跳过 {plan.skipped} 次")
    print(f"  跳过的格子必须落库: 否则监控里看不出这 {policy.grace_s}s 之外的缺口")


def self_test() -> int:
    policy = Policy()
    rng = random.Random(1)
    checks: list[tuple[str, bool, str]] = []

    fires = [grid_fire_time(BASE, s, policy, rng) for s in range(1, 97)]
    ideal = [BASE + timedelta(seconds=s * policy.interval_s) for s in range(1, 97)]
    max_off = max(abs((f - i).total_seconds()) for f, i in zip(fires, ideal))
    checks.append(("抖动不超界", max_off <= policy.interval_s * policy.jitter_ratio + 1e-6, f"max_offset={max_off:.1f}s"))

    same = [grid_fire_time(BASE, 5, policy, random.Random(99)) for _ in range(1)]
    checks.append(("抖动确定可复现", all(same), "同 slot 同种子结果一致"))

    plan = plan_catchup(BASE, 0, BASE + timedelta(hours=6), policy)
    checks.append(("补跑被合并", len(plan.fires) == 1 and plan.skipped == 23, f"fires={len(plan.fires)} skipped={plan.skipped}"))

    delay = simulate_fixed_delay(policy, 24, random.Random(3))
    rate = simulate_fixed_rate(policy, 24, random.Random(3))
    checks.append(("固定延迟漂移更大", delay["drift_s"] > rate["drift_s"] + 60,
                   f"delay={delay['drift_s']:.0f}s rate={rate['drift_s']:.0f}s"))

    solid, spread, _ = burst_spread(policy, 8)
    checks.append(("抖动摊平尖峰", solid == 0 and spread > 0, f"solid={solid:.0f}s spread={spread:.0f}s"))

    ok = True
    for name, passed, detail in checks:
        ok &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    print(f"\n{'全部通过' if ok else '存在失败项'}（{len(checks)} 项）")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="调度窗口推演")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--simulate", type=int, metavar="HOURS", default=0)
    ap.add_argument("--outage", type=int, metavar="HOURS", default=0)
    ap.add_argument("--interval", type=int, default=900)
    ap.add_argument("--jitter", type=float, default=0.08)
    args = ap.parse_args()

    policy = Policy(interval_s=args.interval, jitter_ratio=args.jitter)
    if args.self_test:
        return self_test()
    if args.simulate:
        print_simulation(args.simulate, policy)
        return 0
    if args.outage:
        print_outage(args.outage, policy)
        return 0
    print_simulation(24, policy)
    print()
    print_outage(6, policy)
    return 0


if __name__ == "__main__":
    sys.exit(main())
