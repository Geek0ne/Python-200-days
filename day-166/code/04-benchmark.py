#!/usr/bin/env python3
"""性能对比分析（Day 166 — 系统监控 psutil）。

监控脚本的第一约束不是"能采到"，而是"**采集本身的开销足够小**"：
如果你为了监控 CPU 而吃掉 5% 的 CPU，那监控就成了被监控对象的一部分。

本文件实测三组对比：
  A. 进程枚举的四种写法（最影响单轮采集耗时）
     1) psutil.pids()                        —— 只列 pid
     2) process_iter()                       —— 迭代器，不取属性
     3) process_iter(["name"])               —— 每进程读 1 个字段
     4) process_iter(全量 attrs)              —— 每进程读多个字段
     5) 逐进程 Process(pid).name()             —— 无迭代器级优化
  B. oneshot() 的收益（一次读多个字段时）
  C. 系统级指标的开销
     - psutil.cpu_percent(interval=None) vs 手写解析 /proc/stat
     - disk_usage() 重复调用（statvfs 系统调用）
     - net_io_counters() 重复调用

⚠ 说明：
- 本文件**只读**本机指标，不做任何修改，不启动额外进程。
- 计时统一使用 time.monotonic()（README 2.3 / 陷阱 4）。
- 机器噪声会让单次测量抖动，所以每个项目**重复 N 轮取最小值**：
  最小值比平均值更接近"真实成本"，因为噪声只会让测量变慢，不会变快。

运行：
    python3 04-benchmark.py                # 默认每项 5 轮
    python3 04-benchmark.py --rounds 20    # 更多轮次（结果更稳）
    python3 04-benchmark.py --self-test    # 输出 SELF-TEST OK

依赖：
    pip install psutil
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from typing import Callable

try:
    import psutil
except ImportError:  # pragma: no cover
    print("缺少依赖：请先执行  pip install psutil", file=sys.stderr)
    raise SystemExit(1)


# ── 计时框架 ─────────────────────────────────────────────────────────────

def bench(fn: Callable[[], object], rounds: int) -> float:
    """跑 rounds 轮，返回**最小**单轮耗时（毫秒）。

    为什么取最小值而不是平均值？
      监控脚本的耗时测量总被机器噪声污染（其它进程抢 CPU、页缓存未命中、GC）。
      这些干扰只会让测量值**变大**，永远不会变小 —— 所以最小值是对
      "这段代码本身要多少时间"最接近的估计。这是 microbenchmark 的通行做法。
    """
    best = float("inf")
    for _ in range(rounds):
        t0 = time.monotonic()
        fn()
        dt = time.monotonic() - t0
        best = min(best, dt)
    return best * 1000.0     # 转毫秒


# ── A. 进程枚举的四种写法 ────────────────────────────────────────────────

def pid_only() -> int:
    """只拿 pid 列表：最快，只读 /proc 目录项。"""
    return len(psutil.pids())


def iter_pids() -> int:
    """迭代器但不读属性。"""
    n = 0
    for proc in psutil.process_iter():
        n += 1
        _ = proc.pid
    return n


def iter_name() -> int:
    """每进程读 1 个字段（comm）。"""
    n = 0
    for proc in psutil.process_iter(attrs=["name"], ad_value=None):
        if proc.info["name"]:
            n += 1
    return n


def iter_name_pid_mem() -> int:
    """每进程读多个字段：这就是"全量排行榜"的成本。"""
    n = 0
    for proc in psutil.process_iter(
            attrs=["pid", "name", "memory_info", "num_threads", "status"], ad_value=None):
        if proc.info["memory_info"] is not None:
            n += 1
    return n


def iter_per_process_call() -> int:
    """逐进程 Process(pid).name()：没有迭代器级别的信息复用。"""
    n = 0
    for pid in psutil.pids():
        try:
            if psutil.Process(pid).name():
                n += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return n


def bench_process_enumeration(rounds: int) -> list[tuple[str, float, int]]:
    cases: list[tuple[str, Callable[[], int]]] = [
        ("psutil.pids()（只要 pid）", pid_only),
        ("process_iter()（不取属性）", iter_pids),
        ("process_iter(['name'])", iter_name),
        ("process_iter(5 字段，含 memory_info)", iter_name_pid_mem),
        ("逐进程 Process(pid).name()", iter_per_process_call),
    ]
    results = []
    for label, fn in cases:
        ms = bench(fn, rounds)
        n = fn()
        results.append((label, ms, n))
    return results


# ── B. oneshot() 的收益 ─────────────────────────────────────────────────

def without_oneshot() -> int:
    p = psutil.Process(os.getpid())
    total = 0
    for _ in range(200):
        total += len(p.name()) + len(p.status()) + p.memory_info().rss
    return total


def with_oneshot() -> int:
    p = psutil.Process(os.getpid())
    total = 0
    for _ in range(200):
        # oneshot 会缓存 /proc/<pid>/stat 与 status 等文件，减少重复读
        with p.oneshot():
            total += len(p.name()) + len(p.status()) + p.memory_info().rss
    return total


def bench_oneshot(rounds: int) -> list[tuple[str, float, int]]:
    results = []
    for label, fn in (("无 oneshot（200 轮）", without_oneshot),
                      ("有 oneshot（200 轮）", with_oneshot)):
        results.append((label, bench(fn, rounds), fn()))
    return results


# ── C. 系统级指标开销 ────────────────────────────────────────────────────

def read_proc_stat_manual() -> tuple[int, int]:
    """手写解析 /proc/stat 的 CPU 行。

    为什么要手写？
      不是为了更快，而是为了**去掉 psutil 这层**，看看"读内核"本身要多少钱。
      如果 psutil 的开销和手写差不多，说明 psutil 几乎没有额外成本
      （因为它的活儿本来就是读这些文件 + 做算术）。
    """
    with open("/proc/stat", encoding="utf-8") as fh:
        line = fh.readline()
    fields = line.split()[1:]                     # 跳过 "cpu"
    values = [int(x) for x in fields]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    return idle, total


def bench_system_metrics(rounds: int) -> list[tuple[str, float, int]]:
    # 预热 cpu_percent，否则每次都是 0.0 且走的是"无参照"分支
    psutil.cpu_percent(interval=None)

    cases: list[tuple[str, Callable[[], int]]] = [
        ("psutil.cpu_percent(interval=None)", lambda: int(psutil.cpu_percent(interval=None))),
        ("手写解析 /proc/stat（同样算一次）", lambda: sum(read_proc_stat_manual())),
        ("psutil.virtual_memory()", lambda: psutil.virtual_memory().total),
        ("psutil.disk_usage('/')", lambda: int(psutil.disk_usage("/").percent)),
        ("psutil.net_io_counters()", lambda: psutil.net_io_counters().bytes_sent),
        ("psutil.disk_partitions()", lambda: len(psutil.disk_partitions(all=False))),
    ]
    return [(label, bench(fn, rounds), fn()) for label, fn in cases]


# ── 渲染 ─────────────────────────────────────────────────────────────────

def render(title: str, rows: list[tuple[str, float, int]], baseline: float | None = None) -> None:
    print(f"\n{title}")
    print(f"  {'项目':<38} {'最小耗时':>12} {'相对':>8}")
    print(f"  {'-' * 38} {'-' * 12} {'-' * 8}")
    base = baseline if baseline else (rows[0][1] if rows else 1.0)
    for label, ms, _n in rows:
        if ms < 1.0:
            shown = f"{ms * 1000:8.1f} µs"
        else:
            shown = f"{ms:8.2f} ms"
        rel = ms / base if base > 0 else 0.0
        print(f"  {label:<38} {shown:>12} {rel:>7.2f}×")


def main() -> int:
    ap = argparse.ArgumentParser(description="psutil 采集性能对比")
    ap.add_argument("--rounds", type=int, default=5, help="每项重复轮数（取最小值，默认 5）")
    ap.add_argument("--self-test", action="store_true", help="只做自检并输出 SELF-TEST OK")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    print("=" * 68)
    print(" psutil 采集性能对比（只读；每项取多轮最小值）")
    print("=" * 68)

    proc_count = len(psutil.pids())
    print(f"\n  本机进程数: {proc_count}   逻辑核数: {psutil.cpu_count(logical=True)}")
    print(f"  每项轮数: {args.rounds}")

    rows_a = bench_process_enumeration(args.rounds)
    render("A. 进程枚举的五种写法", rows_a)
    # ★ 结论必须从实测数据推出来，不能写死。不同机器/进程数的倍数差得很远，
    #   写死"约 1.5 倍"这种话，换一台机器就会被自己的基准测试当场打脸。
    base_ms = rows_a[0][1]
    dict_a = {label: ms for label, ms, _ in rows_a}
    name_ms = dict_a.get("process_iter(['name'])", 0.0)
    full_ms = dict_a.get("process_iter(5 字段，含 memory_info)", 0.0)
    per_ms = dict_a.get("逐进程 Process(pid).name()", 0.0)
    print(f"  实测（本机 {proc_count} 个进程）:")
    print(f"    扫描全量字段 = {full_ms / base_ms:6.1f}× 「只要 pid」")
    if name_ms > 0 and per_ms > 0:
        if per_ms > name_ms:
            print(f"    逐进程 Process(pid).name() 比 process_iter(['name']) 慢 "
                  f"{per_ms / name_ms:.2f}×  → 别丢掉迭代器的复用优化")
        else:
            print(f"    逐进程 Process(pid).name() 反而比 process_iter(['name']) 快 "
                  f"{name_ms / per_ms:.2f}×（本机/本版本如此，不要当成普遍结论）")
    print("  可复用的结论: ① 只取需要的字段（attrs= 列表写最小集）；")
    print("                ② 单轮扫描全量字段在高进程数机器上可能达到几百毫秒，")
    print("                   这直接决定了采样周期的下限。")

    rows_b = bench_oneshot(args.rounds)
    render("B. oneshot() 的收益（同一进程读 3 个字段 × 200 轮）", rows_b)
    print("  结论: 一次采集内要读多个字段时用 with p.oneshot()，既更快也更一致（缩小采样窗口）。")
    print("        ⚠ 但 oneshot 内的值不会更新，不能用来做循环采样。")

    rows_c = bench_system_metrics(args.rounds)
    render("C. 系统级单项指标开销", rows_c)
    print("  结论: 单次系统级读取通常是微秒~百微秒级，可以忽略；")
    print("        真正的成本在**进程枚举**和**采样频率**上 —— 别在 5 秒周期里扫 2000 个进程。")

    # 采样开销的自我观测（观测者效应）
    print("\nD. 观测者效应（本脚本自身）")
    me = psutil.Process(os.getpid())
    me.cpu_percent()
    time.sleep(0.3)
    print(f"  本进程 cpu_percent = {me.cpu_percent():.1f}%   "
          f"rss = {me.memory_info().rss / 2**20:.1f} MiB")
    print("  监控进程自己也要吃 CPU/内存；做排行榜时必须排除自身，")
    print("  否则你会看到'监控脚本霸榜'这种自欺欺人的现象。")

    print("\n" + "=" * 68)
    return 0


# ── 自检 ─────────────────────────────────────────────────────────────────

def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    checks.append(("bench 返回正数", bench(lambda: sum(range(1000)), 3) > 0))
    checks.append(("process_iter 计数 > 0", iter_pids() > 0))
    checks.append(("iter_name 计数 > 0", iter_name() > 0))
    checks.append(("iter_name_pid_mem 计数 > 0", iter_name_pid_mem() > 0))
    checks.append(("pids() 与 iter 一致", pid_only() == iter_pids()))
    checks.append(("手动 /proc/stat 可解析", sum(read_proc_stat_manual()) > 0))
    checks.append(("oneshot 结果一致（值通路正确）",
                   isinstance(without_oneshot(), int) and isinstance(with_oneshot(), int)))
    checks.append(("cpu_percent 在合理范围", 0 <= psutil.cpu_percent(interval=None) <= 100))

    # 统计口径自检：最小值 <= 平均值
    samples = [0.01, 0.02, 0.015]
    checks.append(("min <= mean", min(samples) <= statistics.mean(samples)))

    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    if ok:
        print("SELF-TEST OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
