#!/usr/bin/env python3
"""
Day 170 — 定时任务 · 02 十大陷阱复现
========================================================================

定时任务的 bug 有一个共同特点：**平时不出现，出事时已经晚了**。
所以这一份全部是「可复现」的最小案例，每个都能当场跑给你看。

坑位清单：
    ①  get_next_fire_time(previous=None) 原地打转
    ②  naive vs aware datetime → TypeError
    ③  IntervalTrigger 不给 start_date → 从"此刻"起算，不可预测
    ④  max_instances 默认 1 → 慢任务的后续触发被"丢弃"而非排队
    ⑤  misfire_grace_time → 错过窗口直接跳过（不补跑）
    ⑥  job_state 是 pickle → 局部函数/lambda 重启后反序列化炸掉
    ⑦  add_job 不给 id + replace_existing → 重启 N 次注册 N 个任务
    ⑧  schedule.run_pending() 单线程串行 → 一个卡住全堵
    ⑨  多实例部署 → 同一任务被跑 N 次（本文给三种解法）
    ⑩  任务抛异常默认被静默吞掉，只写日志

运行：
    python3 02-pitfalls.py --self-test
    python3 02-pitfalls.py                 # 逐个复现全部 10 个
    python3 02-pitfalls.py --only 4,6      # 只看第 4、6 个
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pickle
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

try:
    import schedule as schedule_mod
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 schedule，请先 `pip install schedule`\n")
    sys.exit(3)

try:
    from apscheduler.jobstores.memory import MemoryJobStore
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("❌ 缺少依赖 apscheduler，请先 `pip install apscheduler`\n")
    sys.exit(3)

LOCAL_TZ = dt.datetime.now().astimezone().tzinfo or dt.timezone.utc


# ---------------------------------------------------------------------------
# 必须放在模块顶层！陷阱 ⑥ 要靠它演示 pickle 反序列化
# ---------------------------------------------------------------------------
def top_level_job() -> str:
    """顶层函数：pickle 记的是它的**导入路径**，重启后能重新找到。"""
    return "top-level ok"


def slow_job(seconds: float) -> str:
    """故意慢的任务，用来撞 max_instances。"""
    time.sleep(seconds)
    return f"slept {seconds}s"


def always_fails() -> None:
    """故意抛异常，演示"异常被静默吞掉"。"""
    raise RuntimeError("这个异常调度器不会替你打印")


# ---------------------------------------------------------------------------
# ① get_next_fire_time 原地打转
# ---------------------------------------------------------------------------
def pitfall_01() -> str:
    base = dt.datetime(2026, 1, 5, 2, 30, tzinfo=LOCAL_TZ)  # 周一
    trig = CronTrigger(hour=3, minute=0)

    wrong: list[dt.datetime] = []
    cursor = base
    for _ in range(3):
        cursor = trig.get_next_fire_time(None, cursor)  # ← 错：previous 永远 None
        wrong.append(cursor)

    right: list[dt.datetime] = []
    prev = None
    now = base
    for _ in range(3):
        nxt = trig.get_next_fire_time(prev, now)
        right.append(nxt)
        prev, now = nxt, nxt

    lines = [
        "  ❌ previous 传 None，三次推算原地打转：",
        f"     {[f'{t:%m-%d %H:%M}' for t in wrong]}",
        "  ✅ 把上一次结果当 previous 传回去，才真正推进：",
        f"     {[f'{t:%m-%d %H:%M}' for t in right]}",
    ]
    verdict = "ok" if wrong[0] == wrong[1] == wrong[2] and right[0] != right[1] else "unexpected"
    lines.append(f"  → 判定：{verdict}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ② naive vs aware
# ---------------------------------------------------------------------------
def pitfall_02() -> str:
    naive = dt.datetime(2026, 1, 5, 2, 30)  # 没有 tzinfo
    iv = IntervalTrigger(minutes=30)
    err = ""
    try:
        iv.get_next_fire_time(None, naive)
    except TypeError as e:
        err = f"{type(e).__name__}: {e}"
    ok = "can't compare offset-naive" in err
    return "\n".join([
        "  ❌ 把 naive datetime 喂给 IntervalTrigger：",
        f"     {err or '（没报错？本版本已宽容）'}",
        "  ✅ 调度器返回的时间带 tzinfo，基准点也必须带：",
        f"     start_date 默认值 = {iv.start_date}",
        f"  → 判定：{'ok' if ok else 'unexpected'}",
    ])


# ---------------------------------------------------------------------------
# ③ IntervalTrigger 隐式 start_date
# ---------------------------------------------------------------------------
def pitfall_03() -> str:
    base = dt.datetime(2026, 1, 5, 2, 30, tzinfo=LOCAL_TZ)
    implicit = IntervalTrigger(minutes=30)
    explicit = IntervalTrigger(minutes=30, start_date=base)
    return "\n".join([
        "  ❌ 不给 start_date，默认是「此刻 + interval」，跟你的基准点无关：",
        f"     隐式 start_date = {implicit.start_date}   ← 是 2026-09 的真实现在",
        "  ✅ 显式指定，推算才可预测：",
        f"     显式 start_date = {explicit.start_date}",
        "  → 后果：单元测试里「下次运行是 30 分钟后」这种断言永远写不稳",
    ])


# ---------------------------------------------------------------------------
# ④ max_instances：丢弃而不是排队
# ---------------------------------------------------------------------------
def pitfall_04() -> str:
    import logging

    records: list[str] = []
    logging.getLogger("apscheduler.executors.default").setLevel(logging.DEBUG)
    logging.getLogger("apscheduler.executors.default").addHandler(
        type("H", (logging.Handler,), {"emit": lambda s, r: records.append(r.getMessage())})()
    )

    sched = BackgroundScheduler()
    sched.start()
    try:
        # 任务睡 1.2 秒，但每 0.2 秒就该触发一次 → 6 倍超载
        sched.add_job(slow_job, "interval", seconds=1, args=[1.2],
                      id="slow", max_instances=1, misfire_grace_time=None)
        time.sleep(2.5)
    finally:
        sched.shutdown(wait=False)

    warnings = [r for r in records if "maximum number" in r or "skipped" in r.lower()]
    return "\n".join([
        "  任务耗时 1.2s，间隔 1s（超载 1.2 倍），max_instances=1：",
        "  ❌ 你以为的第 2、3 次触发被**直接丢弃**（记 warning），不会排队",
        f"     调度器日志：{warnings[0] if warnings else '（本版本未打印 warning）'}",
        "  ✅ 想让它们排队：把 max_instances 调大，或干脆让任务本身幂等 + 接受丢弃",
        f"  → 本次捕获 {len(warnings)} 条丢弃告警",
    ])


# ---------------------------------------------------------------------------
# ⑤ misfire：错过即跳过（不补跑）
# ---------------------------------------------------------------------------
def pitfall_05() -> str:
    import logging

    msgs: list[str] = []
    logging.getLogger("apscheduler.scheduler").addHandler(
        type("H", (logging.Handler,), {"emit": lambda s, r: msgs.append(r.getMessage())})()
    )

    runs: list[str] = []
    sched = BackgroundScheduler(job_defaults={"misfire_grace_time": 1})
    sched.start()
    try:
        # 直接把 next_run 设成 5 秒前 → 调度器发现"已经错过窗口"
        sched.add_job(lambda: runs.append("fired"), "interval", seconds=10,
                      id="late", next_run_time=dt.datetime.now(LOCAL_TZ) - dt.timedelta(seconds=5))
        time.sleep(1.2)
    finally:
        sched.shutdown(wait=False)

    missed = [m for m in msgs if "missed" in m.lower() or "misfire" in m.lower()]
    return "\n".join([
        "  把 next_run_time 设成 5 秒前，misfire_grace_time=1（只容忍 1 秒）：",
        f"  ❌ 实际执行次数 = {len(runs)}（超过 1 秒的迟到一律不补跑）",
        f"     调度器提示：{missed[0] if missed else '（本版本未打印）'}",
        "  机器关机 3:00–3:05，3:00 的任务就永远丢了——这不是 bug，是设计",
        "  ✅ 要补跑：coalesce=True（积压多次只合并成一次）+ 放宽 misfire_grace_time",
        "  ✅ 更稳的语义：任务函数自己幂等 + 记录 last_success 时间戳，",
        "     启动时判断「上次成功在何时」决定要不要补",
    ])


# ---------------------------------------------------------------------------
# ⑥ pickle：函数必须顶层可导入
# ---------------------------------------------------------------------------
def pitfall_06() -> str:
    lines = []

    # 情况 A：顶层函数 —— pickle 只存导入路径
    good = pickle.dumps(top_level_job)
    lines.append(f"  ✅ 顶层函数 pickle 后 {len(good)} 字节，内容是导入路径：")
    lines.append(f"     {pickle.loads(good).__module__}.{pickle.loads(good).__name__}")

    # 情况 B：lambda / 局部函数 —— pickle 直接失败
    try:
        pickle.dumps(lambda: 1)
        err = "（没报错？）"
    except (AttributeError, pickle.PicklingError) as e:
        err = f"{type(e).__name__}: {e}"
    lines.append("  ❌ lambda：")
    lines.append(f"     {err}")

    def local_fn() -> None:  # 局部函数
        pass

    try:
        pickle.dumps(local_fn)
        err2 = "（没报错？）"
    except (AttributeError, pickle.PicklingError) as e:
        err2 = f"{type(e).__name__}: {e}"
    lines.append("  ❌ 局部函数（写在 main 里）：")
    lines.append(f"     {err2}")

    # 情况 C：真正写进 JobStore 后重启进程反序列化
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "jobs.sqlite")
        code = f"""
import sys
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
s = BackgroundScheduler(jobstores={{"default": SQLAlchemyJobStore(url="sqlite:///{db}")}})
try:
    print("RESTORE_OK", len(s.get_jobs()))
except Exception as e:
    print("RESTORE_FAIL", type(e).__name__, e)
"""
        # 写入端必须能导入到脚本顶层函数，所以把当前文件当作模块传入
        env = {**os.environ, "PYTHONPATH": os.path.dirname(os.path.abspath(__file__))}
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=60, env=env
        )
        tail = (out.stdout + out.stderr).strip().splitlines()[-1:] or ["(no output)"]
        lines.append("  🔬 新进程重新打开同一个 JobStore：")
        lines.append(f"     {tail[0]}")
        lines.append("     （只存了 __main__ 里的函数时，重启后必然 RESTORE_FAIL 或 0 个任务）")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ⑦ 重复注册
# ---------------------------------------------------------------------------
def pitfall_07() -> str:
    store = MemoryJobStore()
    sched = BackgroundScheduler(jobstores={"default": store})
    sched.start()
    try:
        for _ in range(5):
            sched.add_job(top_level_job, "cron", hour=3, minute=0)  # ← 无 id、无 replace
        bad = len(sched.get_jobs())
        for _ in range(5):
            sched.add_job(top_level_job, "cron", hour=3, minute=0,
                          id="daily-backup", replace_existing=True)
        good = len(sched.get_jobs())
    finally:
        sched.shutdown(wait=False)
    return "\n".join([
        f"  ❌ 无 id 注册 5 次 → {bad} 个任务（每天凌晨备份 5 遍，还互相踩文件）",
        f"  ✅ 稳定 id + replace_existing=True 注册 5 次 → {good} 个任务（幂等）",
        "  根因：内存 JobStore 里，重启后本该清空；但配了持久化 JobStore 时，",
        "  重启 10 次就是 10 个任务——所以 id 是**幂等注册**的前提，不是可选优化",
    ])


# ---------------------------------------------------------------------------
# ⑧ schedule 串行阻塞
# ---------------------------------------------------------------------------
def pitfall_08() -> str:
    sched = schedule_mod.Scheduler()
    order: list[str] = []

    def slow():
        time.sleep(0.6)
        order.append("slow")

    def fast():
        order.append("fast")

    sched.every(0.1).seconds.do(slow)
    sched.every(0.1).seconds.do(fast)
    t0 = time.time()
    while time.time() - t0 < 0.7:
        sched.run_pending()
        time.sleep(0.05)
    return "\n".join([
        f"  一个 0.6s 的慢任务 + 一个 0.1s 的快任务，同一 scheduler：",
        f"  ❌ 实际执行顺序 = {order}  ← 快的被慢的堵在后面（单线程串行）",
        "  ✅ APScheduler 用线程池并发跑；schedule 永远只有一个循环",
        "     补救：把慢任务丢进 ThreadPoolExecutor，或干脆换 APScheduler",
    ])


# ---------------------------------------------------------------------------
# ⑨ 多实例重复执行
# ---------------------------------------------------------------------------
def pitfall_09() -> str:
    return "\n".join([
        "  两台机器各跑一个 scheduler，共用同一个任务定义：",
        "  ❌ 03:00 到达时两边都认为自己该跑 → 备份两份 / 邮件发两封",
        "",
        "  三种解法（按推荐度排序）：",
        "    ① 单实例：调度器只部署 1 份，web 多副本里不含它  ← 最简单、最可靠",
        "    ② 分布式锁：任务开头 SET NX 抢锁，抢不到直接退出（见 04 的实现）",
        "    ③ 外部编排：交给 cron / K8s CronJob / Airflow，只让它触发",
        "",
        "  判断标准：任务**必须只跑一次** → ①；任务**幂等且允许重复** → 随便；",
        "  介于两者之间 → ②，但你要自己处理锁超时与续约",
    ])


# ---------------------------------------------------------------------------
# ⑩ 异常被静默吞掉
# ---------------------------------------------------------------------------
def pitfall_10() -> str:
    import logging

    errs: list[str] = []
    logging.getLogger("apscheduler.executors.default").addHandler(
        type("H", (logging.Handler,), {
            "emit": lambda s, r: errs.append(r.getMessage()) if r.levelno >= logging.ERROR else None
        })()
    )
    sched = BackgroundScheduler()
    sched.start()
    try:
        job = sched.add_job(always_fails, "interval", seconds=1, id="boom")
        time.sleep(1.6)
        job = sched.get_job("boom")
    finally:
        sched.shutdown(wait=False)

    survived = job is not None  # 任务还在，next_run_time 继续推进
    return "\n".join([
        "  任务每次都抛 RuntimeError：",
        f"  ❌ 调度器不抛出、不打印到 stderr，只写内部日志：{errs[-1] if errs else '(未捕获)'}",
        f"  ✅ 任务依然在表里（{survived}）——**失败的任务会静默地一直失败下去**",
        "  必须自己做：① 任务内部 try/except 记日志 + 告警；",
        "  ② 加一个监听器把 EVENT_JOB_ERROR 接到你的通知渠道；",
        "  ③ 别依赖 last_run 成功，任务里自己记录 last_success",
    ])


PITFALLS = {
    1: ("get_next_fire_time 原地打转", pitfall_01),
    2: ("naive vs aware datetime", pitfall_02),
    3: ("IntervalTrigger 隐式 start_date", pitfall_03),
    4: ("max_instances 丢弃而非排队", pitfall_04),
    5: ("misfire 错过不补跑", pitfall_05),
    6: ("pickle 要求顶层函数", pitfall_06),
    7: ("重复注册", pitfall_07),
    8: ("schedule 串行阻塞", pitfall_08),
    9: ("多实例重复执行", pitfall_09),
    10: ("异常被静默吞掉", pitfall_10),
}


def run_pitfalls(only: list[int] | None = None) -> int:
    for idx, (title, fn) in PITFALLS.items():
        if only and idx not in only:
            continue
        print(f"\n{'=' * 72}\n陷阱 {idx:02d}：{title}\n{'=' * 72}")
        try:
            print(fn())
        except Exception as e:  # 复现脚本自己出错要显式暴露
            print(f"  ⚠️ 复现脚本自身异常：{type(e).__name__}: {e}")
    return 0


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

    print("== ① 打转 ==")
    base = dt.datetime(2026, 1, 5, 2, 30, tzinfo=LOCAL_TZ)
    t = CronTrigger(hour=3, minute=0)
    c = base
    seq = []
    for _ in range(3):
        c = t.get_next_fire_time(None, c)
        seq.append(c)
    ok(seq[0] == seq[1] == seq[2], "previous=None 时三次返回同一时刻（复现成功）")
    prev, now = None, base
    seq2 = []
    for _ in range(3):
        n = t.get_next_fire_time(prev, now)
        seq2.append(n)
        prev, now = n, n
    ok(seq2[0] != seq2[1] and seq2[1] != seq2[2], "传入 previous 后每次推进一天")

    print("== ② 时区 ==")
    try:
        IntervalTrigger(minutes=30).get_next_fire_time(None, dt.datetime(2026, 1, 5, 2, 30))
        got = False
    except TypeError:
        got = True
    ok(got, "naive datetime 触发 TypeError")
    ok(IntervalTrigger(minutes=30).start_date.tzinfo is not None, "触发器默认 start_date 带时区")

    print("== ③ 隐式 start_date ==")
    ok(IntervalTrigger(minutes=30).start_date.year >= 2026, "隐式 start_date 是真实当前时间")
    ok(IntervalTrigger(minutes=30, start_date=base).start_date == base, "显式 start_date 生效")

    print("== ⑤ misfire ==")
    fired: list[int] = []
    s = BackgroundScheduler(job_defaults={"misfire_grace_time": 1})
    s.start()
    try:
        s.add_job(lambda: fired.append(1), "interval", seconds=10, id="late",
                  next_run_time=dt.datetime.now(LOCAL_TZ) - dt.timedelta(seconds=5))
        time.sleep(1.2)
    finally:
        s.shutdown(wait=False)
    ok(len(fired) == 0, f"迟到 5s 超过 grace=1 → 未执行（实际 {len(fired)} 次）")

    print("== ⑥ pickle ==")
    ok(pickle.loads(pickle.dumps(top_level_job))() == "top-level ok", "顶层函数可往返 pickle")
    try:
        pickle.dumps(lambda: 1)
        lam = False
    except Exception:
        lam = True
    ok(lam, "lambda 无法 pickle")

    print("== ⑦ 幂等注册 ==")
    # 两种注册方式必须放在**各自独立**的调度器里比，否则前一组的 5 个匿名任务会算进后一组
    s1 = BackgroundScheduler()
    s1.start()
    try:
        for _ in range(5):
            s1.add_job(top_level_job, "cron", hour=3, minute=0)
        bad = len(s1.get_jobs())
    finally:
        s1.shutdown(wait=False)

    s2 = BackgroundScheduler()
    s2.start()
    try:
        for _ in range(5):
            s2.add_job(top_level_job, "cron", hour=3, minute=0, id="x", replace_existing=True)
        good = len(s2.get_jobs())
    finally:
        s2.shutdown(wait=False)
    ok(bad == 5, f"无 id 注册 5 次 → {bad} 个任务")
    ok(good == 1, f"带 id + replace → {good} 个任务")

    print("== ⑧ 串行 ==")
    order: list[str] = []
    sc = schedule_mod.Scheduler()

    def _slow():
        time.sleep(0.4)
        order.append("slow")

    sc.every(0.1).seconds.do(_slow)
    sc.every(0.1).seconds.do(lambda: order.append("fast"))
    t0 = time.time()
    while time.time() - t0 < 0.5:
        sc.run_pending()
        time.sleep(0.05)
    ok(order[:1] == ["slow"], f"慢任务先跑并阻塞（{order[:3]}）")

    print("== ⑩ 异常 ==")
    s = BackgroundScheduler()
    s.start()
    try:
        j = s.add_job(always_fails, "interval", seconds=1, id="boom")
        time.sleep(1.6)
        alive = s.get_job("boom") is not None
    finally:
        s.shutdown(wait=False)
    ok(alive, "抛异常的任务仍留在表里继续跑（失败会静默持续）")

    print(f"\n结果：{checks - fails}/{checks} 通过")
    print("SELF-TEST OK" if not fails else "SELF-TEST FAILED")
    return 0 if not fails else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Day 170 · 定时任务 02 十大陷阱")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--only", help="只跑指定坑位，如 4,6")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    only = [int(x) for x in args.only.split(",")] if args.only else None
    return run_pitfalls(only)


if __name__ == "__main__":
    sys.exit(main())
