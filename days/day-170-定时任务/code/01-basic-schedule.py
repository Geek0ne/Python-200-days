#!/usr/bin/env python3
"""
Day 170 — 定时任务 · 01 基础用法
========================================================================

把"每隔 N 秒跑一次"从 `while True: time.sleep()` 升级成真正的调度器调用。
本脚本把两个库的**最小可用形态**并排摆出来，让你亲眼看到它们差在哪：

  ① schedule  —— 三行搞定，但只有一个"主循环"、一个线程、零持久化
  ② APScheduler —— 骨架同样是五行，但 Trigger/JobStore/Executor 各可替换

同时讲清三件容易被跳过的事：
  · next_run_time 是怎么算出来的（不是 now + interval）
  · 任务跑得比间隔还久会怎样（max_instances 才是那道闸）
  · 为什么注册任务必须给稳定 id + replace_existing

运行：
    python3 01-basic-schedule.py --self-test
    python3 01-basic-schedule.py --demo schedule
    python3 01-basic-schedule.py --demo apscheduler
    python3 01-basic-schedule.py --demo compare      # 两者行为差异对照
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo

try:
    import schedule
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 schedule，请先 `pip install schedule`\n")
    sys.exit(3)

# 调度器返回的时间都带本地时区；推算用的基准点必须同样带时区，否则 interval 触发器
# 内部做 start_date > now 比较时会 TypeError（naive vs aware）
LOCAL_TZ: tzinfo = datetime.now().astimezone().tzinfo or tzinfo.utc

try:
    from apscheduler.executors.pool import ThreadPoolExecutor
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 apscheduler，请先 `pip install apscheduler`\n")
    sys.exit(3)


# ---------------------------------------------------------------------------
# 1. 纯函数区：不依赖调度器，可离线单测
# ---------------------------------------------------------------------------
@dataclass
class RunLog:
    """记录一次任务被调用的时刻与耗时——用来证明'有没有漂移'。"""

    label: str
    fired_at: datetime
    cost: float = 0.0
    tags: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        extra = f" tags={self.tags}" if self.tags else ""
        return f"[{self.fired_at:%H:%M:%S.%f}] {self.label} cost={self.cost:.3f}s{extra}"


def naive_loop_plan(n: int, work_cost: float, sleep: float) -> list[float]:
    """模拟 `while True: work(); sleep()` 的实际触发间隔。

    返回每次 work 开始的时刻（相对第一次的偏移秒数）。
    这就是 README 第 2.1 节说的**漂移**：实际间隔 = sleep + work_cost，
    而不是 sleep。
    """
    stamps: list[float] = []
    clock = 0.0
    for _ in range(n):
        stamps.append(clock)
        clock += work_cost + sleep  # 工作耗时 + 睡眠
    return stamps


def interval_stamps(n: int, seconds: float) -> list[float]:
    """调度器的理想触发时刻：从 0 开始，每 `seconds` 一次，不漂移。"""
    return [i * seconds for i in range(n)]


def drift_report(n: int, work_cost: float, sleep: float) -> dict:
    """对比朴素循环与调度器的累计偏差。"""
    naive = naive_loop_plan(n, work_cost, sleep)
    ideal = interval_stamps(n, sleep)
    return {
        "naive": naive,
        "ideal": ideal,
        "naive_span": naive[-1] - naive[0],
        "ideal_span": ideal[-1] - ideal[0],
        "drift_at_end": (naive[-1] - naive[0]) - (ideal[-1] - ideal[0]),
        "drift_ratio": (naive[-1] - naive[0]) / (ideal[-1] - ideal[0]) if n > 1 and ideal[-1] > ideal[0] else float("inf"),
    }


def describe_cron(*, hour: int | None = None, minute: int | None = None,
                  day_of_week: str | None = None) -> str:
    """把 CronTrigger 的表达翻译成人话——排错时非常好用。"""
    parts = []
    if hour is not None:
        parts.append(f"每天 {hour:02d} 点")
    if minute is not None:
        parts.append(f"{minute:02d} 分")
    if day_of_week:
        names = {"mon": "周一", "tue": "周二", "wed": "周三", "thu": "周四",
                 "fri": "周五", "sat": "周六", "sun": "周日"}
        parts.append(names.get(day_of_week, day_of_week))
    return " / ".join(parts) if parts else "（未设置字段）"


def cron_next_runs(trigger, count: int, since: datetime) -> list[datetime]:
    """连续推算 count 个 next_run_time，验证触发器表达式是否符合预期。

    两个容易踩的细节（都写进了 README 的陷阱节）：

    1. `get_next_fire_time(previous_fire_time, now)` 里 **previous_fire_time 不能一直传 None**。
       传 None 时 cron 触发器认为「没有历史」，当 now 本身命中 cron 就返回 now 本身——
       循环推算会原地打转，永远返回同一个时间戳。
    2. 返回值带 tzinfo（本地时区），而 interval 触发器内部拿 start_date 与 now 比较，
       **naive datetime 会直接 TypeError**。所以 since 必须带时区。
    """
    out: list[datetime] = []
    prev = None
    now = since
    for _ in range(count):
        nxt = trigger.get_next_fire_time(prev, now)
        if nxt is None:
            break
        out.append(nxt)
        prev = nxt
        now = nxt
    return out


# ---------------------------------------------------------------------------
# 2. schedule 演示
# ---------------------------------------------------------------------------
def demo_schedule(seconds: float, rounds: int) -> list[RunLog]:
    """用 schedule 跑 rounds 轮，每 seconds 秒一次。"""
    sched = schedule.Scheduler()
    logs: list[RunLog] = []

    def tick() -> None:
        logs.append(RunLog("schedule-tick", datetime.now(), tags=[f"run#{len(logs) + 1}"]))

    sched.every(seconds).seconds.do(tick)
    print(f"  已注册任务：{[ (j.interval, 's') for j in sched.jobs ]}")
    print(f"  next_run    ：{sched.jobs[0].next_run:%H:%M:%S}")

    # 只等够 rounds-1 个间隔即可拿到 rounds 次触发（多留 1.5s 余量吸收调度抖动）
    deadline = time.time() + seconds * (rounds - 1) + 1.5
    while len(logs) < rounds and time.time() < deadline:
        sched.run_pending()
        time.sleep(0.05)

    print(f"  实际触发 {len(logs)} 次：")
    for line in logs:
        print(f"    {line}")
    return logs


# ---------------------------------------------------------------------------
# 3. APScheduler 演示
# ---------------------------------------------------------------------------
def demo_apscheduler(seconds: float, rounds: int) -> list[RunLog]:
    """用 APScheduler 跑同样件事，并打印 Trigger 推算的 next_run_time。"""
    sched = BackgroundScheduler(
        executors={"default": ThreadPoolExecutor(2)},
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 30},
    )
    logs: list[RunLog] = []

    def tick2() -> None:
        logs.append(RunLog("aps-tick", datetime.now(), tags=[f"run#{len(logs) + 1}"]))

    sched.add_job(
        tick2,
        trigger=IntervalTrigger(seconds=int(seconds)),
        id="demo-tick",
        replace_existing=True,   # ← 幂等注册：重启 10 次也只有 1 个任务
        next_run_time=datetime.now() + timedelta(seconds=seconds),
    )
    sched.start()
    try:
        job = sched.get_job("demo-tick")
        print(f"  已注册任务 id=demo-tick，trigger={job.trigger}")
        print(f"  next_run    ：{job.next_run_time:%H:%M:%S}")
        print(f"  misfire_grace_time={job.misfire_grace_time} "
              f"coalesce={job.coalesce} max_instances={job.max_instances}")

        deadline = time.time() + seconds * (rounds - 1) + 1.5
        while len(logs) < rounds and time.time() < deadline:
            time.sleep(0.05)
    finally:
        sched.shutdown(wait=False)

    print(f"  实际触发 {len(logs)} 次：")
    for line in logs:
        print(f"    {line}")
    return logs


# ---------------------------------------------------------------------------
# 4. 对照演示
# ---------------------------------------------------------------------------
def demo_compare() -> None:
    print("\n【A】朴素 sleep 循环 —— 漂移")
    rep = drift_report(5, work_cost=5.0, sleep=60.0)
    print(f"  理想间隔（睡 60s）    ：{[f'{x:.0f}' for x in rep['ideal']]} 秒")
    print(f"  朴素循环（干活 5s）   ：{[f'{x:.0f}' for x in rep['naive']]} 秒")
    print(f"  4 小时后累计偏 {rep['drift_at_end']:.0f}s（{rep['drift_ratio']:.2f}×）")

    print("\n【B】调度器 —— 对齐到网格，不漂移")
    print(f"  IntervalTrigger 从注册时刻起每 60s 一次，不受任务耗时影响")

    print("\n【C】三种 Trigger 各自表达什么")
    base = datetime(2026, 1, 5, 2, 30, 0, tzinfo=LOCAL_TZ)  # 周一凌晨
    cases = [
        ("cron 每天 03:00", CronTrigger(hour=3, minute=0)),
        ("cron 周一 08:30", CronTrigger(day_of_week="mon", hour=8, minute=30)),
        ("interval 每 30 分钟", IntervalTrigger(minutes=30)),
        ("date 一次性", DateTrigger(run_date=base + timedelta(hours=1))),
    ]
    for label, trig in cases:
        runs = cron_next_runs(trig, 2, base) if not isinstance(trig, DateTrigger) else [trig.run_date]
        pretty = " → ".join(f"{r:%m-%d %H:%M}" for r in runs)
        print(f"  {label:22s} {pretty}")

    print("\n【D】max_instances：任务比间隔还久时会怎样")
    print("  scheduler 里对同一 job 默认 max_instances=1；")
    print("  第 1 次还没跑完就到点了，第 2 次会被直接丢弃并记 warning，")
    print("  而不是排队堆着——这叫'合并/丢弃'，不是'串行排队'。")


# ---------------------------------------------------------------------------
# 5. self-test
# ---------------------------------------------------------------------------
def self_test() -> int:
    checks = 0
    fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal checks, fails
        checks += 1
        if cond:
            print(f"  ✓ {label}")
        else:
            fails += 1
            print(f"  ✗ {label}")

    print("== 漂移计算 ==")
    r = drift_report(5, work_cost=5.0, sleep=60.0)
    ok(r["naive"] == [0.0, 65.0, 130.0, 195.0, 260.0], f"朴素循环间隔含耗时 {[f'{x:.0f}' for x in r['naive']]}")
    ok(r["ideal"] == [0.0, 60.0, 120.0, 180.0, 240.0], "理想间隔不含耗时")
    ok(abs(r["drift_at_end"] - 20.0) < 1e-9, "4 轮累计漂移 20s")
    ok(abs(r["drift_ratio"] - 260.0 / 240.0) < 1e-9, "漂移倍率 ≈1.083")

    print("== cron 人话翻译 ==")
    ok(describe_cron(hour=3, minute=0) == "每天 03 点 / 00 分", describe_cron(hour=3, minute=0))
    ok("周一" in describe_cron(day_of_week="mon"), "周几翻译正确")

    print("== cron / interval 触发时间推算 ==")
    base = datetime(2026, 1, 5, 2, 30, 0, tzinfo=LOCAL_TZ)  # 周一
    runs = cron_next_runs(CronTrigger(hour=3, minute=0), 3, base)
    ok(len(runs) == 3, "得到 3 个触发时刻")
    ok(all(r.hour == 3 and r.minute == 0 for r in runs), "全部落在 03:00")
    ok(runs[0].date() == base.date() and runs[1].date() == base.date() + timedelta(days=1),
       "前两次在同一天与次日")

    mon = cron_next_runs(CronTrigger(day_of_week="mon", hour=8, minute=30), 2, base)
    ok(all(r.weekday() == 0 for r in mon), "周一只在周一触发")
    ok((mon[1] - mon[0]).days == 7, "相邻两次相隔 7 天")

    # 注意：IntervalTrigger 不给 start_date 时，默认从「此刻 + interval」开始，
    # 跟传入的 since 无关。要让推算结果可预测，必须显式指定 start_date。
    iv = cron_next_runs(IntervalTrigger(minutes=30, start_date=base), 3, base)
    ok(len(iv) == 3, "interval 得到 3 个触发时刻")
    # start_date 本身即第一次触发，之后严格每 30 分钟
    ok((iv[0] - base).total_seconds() == 0, "首次触发即 start_date 本身")
    ok(all((iv[i + 1] - iv[i]).total_seconds() == 1800 for i in range(len(iv) - 1)),
       "相邻间隔严格 1800s")
    ok(all(r.minute in (0, 30) for r in iv), "只落在整点/半点（对齐到网格）")

    print("== date 一次性触发 ==")
    dt = DateTrigger(run_date=base + timedelta(hours=1))
    # 在 run_date 之前查询 → 返回那一次；在 run_date 之后查询 → None（再也不会跑）
    ok(dt.get_next_fire_time(None, base) == base + timedelta(hours=1), "run_date 之前查询返回该时刻")
    ok(dt.get_next_fire_time(base + timedelta(hours=1), base + timedelta(hours=2)) is None,
       "run_date 之后查询返回 None（一次性，不会重复）")
    ok(dt.run_date == base + timedelta(hours=1), "run_date 与传入一致")

    print("== 调度器真实行为 ==")
    logs = demo_schedule(seconds=1, rounds=3)
    ok(len(logs) == 3, f"schedule 触发 {len(logs)} 次")
    if len(logs) == 3:
        gaps = [(logs[i + 1].fired_at - logs[i].fired_at).total_seconds() for i in range(2)]
        ok(all(0.8 < g < 1.5 for g in gaps), f"间隔接近 1s：{[f'{g:.2f}' for g in gaps]}")

    logs2 = demo_apscheduler(seconds=1, rounds=3)
    ok(len(logs2) == 3, f"APScheduler 触发 {len(logs2)} 次")

    print("== 幂等注册 ==")
    s = BackgroundScheduler()
    s.start()
    try:
        for i in range(5):
            s.add_job(lambda: None, "interval", seconds=60,
                      id="same", replace_existing=True)
        jobs = s.get_jobs()
        ok(len(jobs) == 1, f"重复 add_job 5 次后仍只有 1 个任务（实际 {len(jobs)}）")
    finally:
        s.shutdown(wait=False)

    print(f"\n结果：{checks - fails}/{checks} 通过")
    if fails:
        print("SELF-TEST FAILED")
        return 1
    print("SELF-TEST OK")
    return 0


# ---------------------------------------------------------------------------
# 6. CLI
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Day 170 · 定时任务 01 基础用法")
    ap.add_argument("--self-test", action="store_true", help="离线自测（不联网、不 sleep 太久）")
    ap.add_argument("--demo", choices=["schedule", "apscheduler", "compare"], help="演示某种用法")
    ap.add_argument("--seconds", type=float, default=1.0, help="演示用的间隔秒数")
    ap.add_argument("--rounds", type=int, default=3, help="演示触发轮数")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.demo == "compare":
        demo_compare()
        return 0
    if args.demo == "schedule":
        print("【schedule】")
        demo_schedule(args.seconds, args.rounds)
        return 0
    if args.demo == "apscheduler":
        print("【APScheduler】")
        demo_apscheduler(args.seconds, args.rounds)
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
