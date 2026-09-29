#!/usr/bin/env python3
"""
Day 170 — 定时任务 · 03 进阶用法
========================================================================

前两份把"能跑"和"别踩坑"讲完了。这一份讲**真正决定生产质量**的三件事：

    ① 三种 Trigger 混用 + 复合表达式（AndTrigger / OrTrigger）
    ② job_defaults：coalesce / max_instances / misfire_grace_time 三参数
    ③ 事件监听：把「任务失败」变成你能看见的信号（这是 02 陷阱⑩ 的解法）

另外顺手演示一个很多人踩的组合：**持久化 JobStore + 进程重启后任务不丢，
但也不会重复补跑**——因为 next_run_time 是被持久化下来的共享状态。

运行：
    python3 03-advanced-scheduler.py --self-test
    python3 03-advanced-scheduler.py                 # 跑全部演示
    python3 03-advanced-scheduler.py --demo coalesce
    python3 03-advanced-scheduler.py --demo listener
    python3 03-advanced-scheduler.py --demo persist
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field

try:
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobEvent
    from apscheduler.executors.pool import ProcessPoolExecutor, ThreadPoolExecutor
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.combining import OrTrigger

    # ⚠️ 本课只演示 OrTrigger。AndTrigger 与 cron 组合会死循环（见 README 陷阱 ⑪），
    #    所以这里**故意不导入** AndTrigger——避免有人照抄后整个调度器卡死。
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 apscheduler，请先 `pip install apscheduler`\n")
    sys.exit(3)

try:
    import sqlalchemy  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 sqlalchemy，请先 `pip install sqlalchemy`\n")
    sys.exit(3)

LOCAL_TZ = dt.datetime.now().astimezone().tzinfo or dt.timezone.utc


# ---------------------------------------------------------------------------
# 顶层函数：持久化 JobStore 要求可重新导入（见 02 陷阱⑥）
# ---------------------------------------------------------------------------
def record_hit(tag: str, sink: str) -> dict:
    """写一行 JSON 到 sink 文件，返回这条记录。用于观察任务真实执行情况。"""
    rec = {"tag": tag, "at": dt.datetime.now().isoformat(timespec="seconds")}
    with open(sink, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def boom_job(sink: str) -> None:
    """故意失败，用来触发 EVENT_JOB_ERROR。"""
    with open(sink, "a", encoding="utf-8") as fh:
        fh.write('{"tag":"about-to-fail"}\n')
    raise ValueError("业务异常：连不上数据库")


@dataclass
class CoalesceDemo:
    """记录 coalesce / max_instances 的实际行为。"""

    sink: str
    hits: list[dict] = field(default_factory=list)

    def tick(self) -> None:
        self.hits.append(record_hit("coalesce-tick", self.sink))


# ---------------------------------------------------------------------------
# ① 三种 Trigger + 复合表达式
# ---------------------------------------------------------------------------
def explain_triggers() -> str:
    base = dt.datetime(2026, 1, 5, 9, 0, tzinfo=LOCAL_TZ)  # 周一 09:00

    def nxt(trig, n: int = 3) -> str:
        out, prev, now = [], None, base
        for _ in range(n):
            t = trig.get_next_fire_time(prev, now)
            if t is None:
                return "(无更多触发)"
            out.append(f"{t:%m-%d(%a) %H:%M}")
            prev = now = t
        return " → ".join(out)

    lines = ["【cron — 按日历对齐】"]
    lines.append(f"  每天 03:00        {nxt(CronTrigger(hour=3, minute=0))}")
    lines.append(f"  工作日 09-18 每 2h  {nxt(CronTrigger(day_of_week='mon-fri', hour='9-18', minute=0))}")
    lines.append(f"  每周一 08:30      {nxt(CronTrigger(day_of_week='mon', hour=8, minute=30), 2)}")

    lines.append("\n【interval — 按固定秒数，且不漂移】")
    lines.append(f"  每 30 分钟        {nxt(IntervalTrigger(minutes=30, start_date=base), 3)}")
    lines.append(f"  每 90 秒          {nxt(IntervalTrigger(seconds=90, start_date=base), 3)}")

    lines.append("\n【复合 — Or 可以，And 会挂死】")
    # ⚠️ 正确写法：把条件合并进**同一个** CronTrigger
    lines.append(f"  仅工作日 9 点     {nxt(CronTrigger(day_of_week='mon-fri', hour=9), 3)}   ← 一个表达式搞定")
    or_t = OrTrigger([CronTrigger(day_of_week="sat"), CronTrigger(day_of_week="sun")])
    lines.append(f"  周末              {nxt(or_t, 4)}   ← Or 取最早，安全")
    lines.append("  ❌ AndTrigger([CronTrigger(day_of_week='mon-fri'), CronTrigger(hour=9)])")
    lines.append("     → 死循环。官方实现是 while True 直到各子触发器产出**完全相同**的时间戳，")
    lines.append("       而 cron 永远不会对齐（一个给 00:00、一个给 09:00）→ 调度器直接卡死。")
    lines.append("     官方 docstring 也警告了：AndTrigger 混 IntervalTrigger 会让调度器挂起。")
    lines.append("     结论：条件过滤一律写进单个 cron 表达式，别用 AndTrigger 拼 cron。")

    lines.append("\n【为什么 cron 不会漂移、interval 也不会】")
    lines.append("  两者都是先算出**绝对的下一次时刻**再等待，而不是「睡 N 秒」。")
    lines.append("  区别：cron 每次都从日历推（跳过大段空闲），interval 从注册时刻累加。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ② job_defaults 三参数
# ---------------------------------------------------------------------------
def explain_job_defaults() -> str:
    return "\n".join([
        "  coalesce=True",
        "    积压了 5 次触发（进程卡了 5 个周期）→ 只补跑**最后那一次**。",
        "    False 则 5 次全补 → 半夜醒来发现备份跑了 5 遍。",
        "",
        "  max_instances=1",
        "    上一次还没跑完又到点了 → **直接丢弃**并记 warning，不排队。",
        "    调大到 N 才会排队；排队适合'每次都必须做'的任务（如累加），",
        "    丢弃适合'只要最新状态'的任务（如采集快照）。",
        "",
        "  misfire_grace_time=60",
        "    允许迟到 60 秒内仍然执行。0=不宽容（严格准点，超时丢弃），",
        "    None=无限宽容（但会把积压的触发全补一遍）。",
        "    生产经验：日常任务 30~300；一次性任务设 None；",
        "    绝不要设 0 又指望机器偶尔卡顿时仍能跑。",
    ])


def demo_coalesce(td: str) -> None:
    """真实复现：任务很慢 + 间隔很短 → 观察丢弃行为。"""
    sink = os.path.join(td, "coalesce.jsonl")
    demo = CoalesceDemo(sink)
    sched = BackgroundScheduler(
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": None},
    )
    sched.start()
    try:
        sched.add_job(lambda: (time.sleep(1.5), record_hit("slow", sink)),
                      "interval", seconds=1, id="slow", max_instances=1)
        print("  任务耗时 1.5s，间隔 1s，连跑 4s —— 观察实际执行几次：")
        time.sleep(4)
    finally:
        sched.shutdown(wait=False)
    n = sum(1 for _ in open(sink, encoding="utf-8")) if os.path.exists(sink) else 0
    print(f"  4 秒内理论到期 4 次，实际执行 {n} 次 → 其余被 max_instances 丢弃")
    print("  日志里会有：'Execution of job ... skipped: maximum number of running instances reached'")
    _ = demo


# ---------------------------------------------------------------------------
# ③ 事件监听：让失败可见
# ---------------------------------------------------------------------------
def demo_listener(td: str) -> None:
    sink = os.path.join(td, "listener.jsonl")
    ok_events: list[str] = []
    err_events: list[tuple[str, str]] = []

    sched = BackgroundScheduler()
    sched.add_listener(
        lambda e: ok_events.append(e.job_id), EVENT_JOB_EXECUTED
    )

    def on_error(event: JobEvent) -> None:
        err_events.append((event.job_id, repr(event.exception)))

    sched.add_listener(on_error, EVENT_JOB_ERROR)
    sched.start()
    try:
        sched.add_job(boom_job, "interval", seconds=1, id="risky", args=(sink,),
                      max_instances=1, misfire_grace_time=None)
        sched.add_job(record_hit, "interval", seconds=1, id="healthy",
                      args=("healthy", sink), misfire_grace_time=None)
        print("  同时挂一个必失败任务和一个必成功任务，各跑 2.5 秒：")
        time.sleep(2.5)
    finally:
        sched.shutdown(wait=False)

    print(f"  ✅ 成功事件 {len(ok_events)} 次：{ok_events}")
    print(f"  ❌ 失败事件 {len(err_events)} 次：{err_events[:2]}")
    print("  → 这就是解法：EVENT_JOB_ERROR 接到飞书/钉钉/Webhook，失败立刻有人知道")


# ---------------------------------------------------------------------------
# ④ 持久化：重启不丢、也不重复补跑
# ---------------------------------------------------------------------------
def demo_persist(td: str) -> None:
    db = os.path.join(td, "jobs.sqlite")
    url = f"sqlite:///{db}"
    sink = os.path.join(td, "persist.jsonl")

    print("  第 1 次进程：注册任务后立刻退出（模拟重启）")
    s1 = BackgroundScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=url)},
        job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": None},
    )
    s1.add_job(record_hit, "cron", hour=3, minute=0, id="daily-backup",
               args=("backup", sink), replace_existing=True)
    s1.start()
    time.sleep(0.3)
    jobs_before = len(s1.get_jobs())
    nrt = s1.get_job("daily-backup").next_run_time
    s1.shutdown(wait=False)
    print(f"    内存/库里任务数 = {jobs_before}，next_run_time = {nrt:%Y-%m-%d %H:%M}")

    print("  第 2 次进程：全新进程对象，重新连同一个库")
    s2 = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=url)})
    s2.start()
    time.sleep(0.3)
    jobs_after = len(s2.get_jobs())
    restored = s2.get_job("daily-backup")
    nrt2 = restored.next_run_time if restored else None
    s2.shutdown(wait=False)
    print(f"    重启后任务数 = {jobs_after}，next_run_time = {nrt2:%Y-%m-%d %H:%M}"
          if nrt2 else f"    重启后任务数 = {jobs_after}，任务丢失！")
    print(f"    任务是否原样恢复 = {jobs_after == jobs_before}")
    print("  → 关键点：next_run_time 是**被持久化的状态**，所以：")
    print("     ① 重启不丢任务；② 也不会因为停机 3 小时就补跑 3 次；")
    print("     ③ 想补跑要显式 pause_job/resume_job 或改 next_run_time")


# ---------------------------------------------------------------------------
# ⑤ Executor 该选哪个
# ---------------------------------------------------------------------------
def explain_executors() -> str:
    return "\n".join([
        "  ThreadPoolExecutor(10)   ← 默认，IO 密集（请求 HTTP、读文件、查库）",
        "  ProcessPoolExecutor(4)  ← CPU 密集（压缩、加密、图像处理）",
        "    ⚠️ 任务函数与参数必须**可 pickle**；局部闭包会直接报错",
        "    ⚠️ 进程池不能传数据库连接、文件句柄这类对象",
        "  AsyncIOScheduler         ← 任务本身是 async 函数时用它",
        "",
        "  判断口诀：等 IO 就用线程，算 CPU 就用进程，本来就 async 就别绕线程。",
    ])


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def self_test() -> int:
    checks = fails = 0

    def ok(cond: bool, label: str) -> None:
        nonlocal checks, fails
        checks += 1
        print(f"  {'✓' if cond else '✗'} {label}")
        if not cond:
            fails += 1

    base = dt.datetime(2026, 1, 5, 9, 0, tzinfo=LOCAL_TZ)  # 周一

    def nxt(trig, n=5):
        out, prev, now = [], None, base
        for _ in range(n):
            t = trig.get_next_fire_time(prev, now)
            if t is None:
                break
            out.append(t)
            prev = now = t
        return out

    print("== cron：工作日 9-18 点整点 ==")
    runs = nxt(CronTrigger(day_of_week="mon-fri", hour="9-18", minute=0), 12)
    ok(all(r.hour in range(9, 19) and r.minute == 0 for r in runs), "全部落在 9-18 点整")
    ok(all(r.weekday() < 5 for r in runs), "全部是工作日")
    ok((runs[0] - base).total_seconds() == 0, "首次即当前 09:00")

    print("== 单个 Cron 表达多条件：工作日且 9 点 ==")
    # 不要用 AndTrigger([cron(day_of_week), cron(hour=9)])——会死循环
    a = nxt(CronTrigger(day_of_week="mon-fri", hour=9), 3)
    ok(len(a) == 3, "得到 3 次")
    ok(all(r.weekday() < 5 and r.hour == 9 for r in a), "同时满足两个条件")
    ok((a[1].date() - a[0].date()).days == 1, "工作日逐日推进")
    ok((a[1] - a[0]).total_seconds() == 86400, "间隔 24 小时（周五→下周一跨 3 天除外）")
    print("  ⚠️ AndTrigger 拼两个 cron 会死循环，已改用单表达式（原因见 README 陷阱 ⑪）")

    print("== OrTrigger：周末 ==")
    o = nxt(OrTrigger([CronTrigger(day_of_week="sat"), CronTrigger(day_of_week="sun")]), 4)
    ok(all(r.weekday() >= 5 for r in o), "只落在周末")
    ok({r.weekday() for r in o} == {5, 6}, "周六周日都覆盖")

    print("== interval 不漂移 ==")
    iv = nxt(IntervalTrigger(minutes=30, start_date=base), 4)
    ok(all((iv[i + 1] - iv[i]).total_seconds() == 1800 for i in range(3)), "严格 1800s")

    print("== job_defaults 生效 ==")
    with tempfile.TemporaryDirectory() as td:
        sink = os.path.join(td, "st.jsonl")
        s = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1,
                                              "misfire_grace_time": 45})
        s.start()
        try:
            s.add_job(record_hit, "interval", seconds=60, id="j", args=("x", sink))
            j = s.get_job("j")
            ok(j.coalesce is True, f"coalesce={j.coalesce}")
            ok(j.max_instances == 1, f"max_instances={j.max_instances}")
            ok(j.misfire_grace_time == 45, f"misfire_grace_time={j.misfire_grace_time}")
            ok(j.id == "j", "id 生效")
        finally:
            s.shutdown(wait=False)

    print("== max_instances 丢失误杀 ==")
    with tempfile.TemporaryDirectory() as td:
        sink = os.path.join(td, "slow.jsonl")
        s = BackgroundScheduler()
        s.start()
        try:
            def slow():
                time.sleep(1.2)
                record_hit("slow", sink)

            s.add_job(slow, "interval", seconds=1, id="slow", max_instances=1)
            time.sleep(3.2)
        finally:
            s.shutdown(wait=False)
        n = sum(1 for _ in open(sink, encoding="utf-8")) if os.path.exists(sink) else 0
        ok(n < 3, f"3.2 秒内理论到期 3 次，实际只跑了 {n} 次（其余丢弃）")

    print("== 事件监听 ==")
    with tempfile.TemporaryDirectory() as td:
        sink = os.path.join(td, "ev.jsonl")
        errs: list[tuple[str, str]] = []
        oks: list[str] = []
        s = BackgroundScheduler()
        s.add_listener(lambda e: errs.append((e.job_id, repr(e.exception))), EVENT_JOB_ERROR)
        s.add_listener(lambda e: oks.append(e.job_id), EVENT_JOB_EXECUTED)
        s.start()
        try:
            s.add_job(boom_job, "interval", seconds=1, id="bad", args=(sink,),
                      misfire_grace_time=None)
            s.add_job(record_hit, "interval", seconds=1, id="good",
                      args=("good", sink), misfire_grace_time=None)
            time.sleep(2.4)
        finally:
            s.shutdown(wait=False)
        ok(len(errs) >= 1, f"捕获到 {len(errs)} 个失败事件")
        ok(all(j == "bad" for j, _ in errs), "失败事件来自 bad")
        ok("good" in oks, f"成功事件包含 good（{oks}）")

    print("== 持久化 JobStore：重启不丢 ==")
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "p.sqlite")
        sink = os.path.join(td, "p.jsonl")
        url = f"sqlite:///{db}"
        s1 = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=url)})
        s1.add_job(record_hit, "cron", hour=3, minute=0, id="bk", args=("bk", sink),
                   replace_existing=True)
        s1.start()
        time.sleep(0.3)
        before = len(s1.get_jobs())
        nrt1 = s1.get_job("bk").next_run_time
        s1.shutdown(wait=False)

        s2 = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=url)})
        s2.start()
        time.sleep(0.3)
        after = len(s2.get_jobs())
        j2 = s2.get_job("bk")
        s2.shutdown(wait=False)
        ok(after == before == 1, f"重启前后任务数都是 1（{before}→{after}）")
        ok(j2 is not None, "重启后任务原样恢复")
        ok(j2 is not None and j2.next_run_time == nrt1, "next_run_time 被持久化（不会补跑）")

        print("== 幂等注册配合持久化 ==")
        s3 = BackgroundScheduler(jobstores={"default": SQLAlchemyJobStore(url=url)})
        s3.start()
        try:
            for _ in range(5):
                s3.add_job(record_hit, "cron", hour=3, minute=0, id="bk",
                           args=("bk", sink), replace_existing=True)
            n = len(s3.get_jobs())
        finally:
            s3.shutdown(wait=False)
        ok(n == 1, f"持久化库里重复注册 5 次仍为 {n} 个（幂等）")

    print("== Executor 可选 ==")
    ok(hasattr(ThreadPoolExecutor, "__init__"), "ThreadPoolExecutor 可用")
    ok(hasattr(ProcessPoolExecutor, "__init__"), "ProcessPoolExecutor 可用")

    print(f"\n结果：{checks - fails}/{checks} 通过")
    print("SELF-TEST OK" if not fails else "SELF-TEST FAILED")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 170 · 定时任务 03 进阶用法")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", choices=["triggers", "defaults", "executor",
                                       "coalesce", "listener", "persist"])
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.demo in (None, "triggers"):
        print("== ① 三种 Trigger 与复合表达式 ==")
        print(explain_triggers())
    if args.demo in (None, "defaults"):
        print("\n== ② job_defaults 三参数 ==")
        print(explain_job_defaults())
    if args.demo in (None, "executor"):
        print("\n== ⑤ Executor 选型 ==")
        print(explain_executors())
    if args.demo in (None, "coalesce"):
        print("\n== ④ coalesce / max_instances 实测 ==")
        with tempfile.TemporaryDirectory() as td:
            demo_coalesce(td)
    if args.demo in (None, "listener"):
        print("\n== ③ 事件监听 ==")
        with tempfile.TemporaryDirectory() as td:
            demo_listener(td)
    if args.demo in (None, "persist"):
        print("\n== ⑥ 持久化实测 ==")
        with tempfile.TemporaryDirectory() as td:
            demo_persist(td)
    return 0


if __name__ == "__main__":
    sys.exit(main())
