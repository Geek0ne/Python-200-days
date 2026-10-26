#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day 197 — 并发与内存八股实测：把「听说」变成「量过」

三个高频面试结论，本文件各配一个可复现实验：
    1. CPU 密集型任务，多线程拿不到多核加速（GIL）；多进程可以。
    2. IO 密集型任务，多线程有效，因为等待时会释放 GIL。
    3. sys.getsizeof(list) 只算容器本身，不算元素——单独用它估内存会错得离谱。

运行：
    python3 04-concurrency-and-memory.py --self-test   # 只跑正确性断言，约 1 秒
    python3 04-concurrency-and-memory.py --bench       # 真跑基准，约 5–8 秒
    python3 04-concurrency-and-memory.py --bench --json

实测环境：Linux 7.0.0-34-generic / Python 3.12.3 / 4 vCPU
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import tracemalloc
from array import array
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# 工作负载：必须纯粹、可重复、不受磁盘/网络影响
# ---------------------------------------------------------------------------


def count_primes(limit: int) -> int:
    """埃氏筛，返回 <= limit 的质数个数。CPU 密集、内存局部性好。"""
    if limit < 2:
        return 0
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, int(limit**0.5) + 1):
        if sieve[p]:
            start = p * p
            sieve[start : limit + 1 : p] = b"\x00" * (((limit - start) // p) + 1)
    return sum(sieve)


def io_task(seconds: float = 0.2) -> float:
    """模拟一次阻塞 IO（数据库、HTTP、磁盘）。sleep 会释放 GIL。"""
    time.sleep(seconds)
    return seconds


# ---------------------------------------------------------------------------
# 基准 1：CPU 密集型 —— 顺序 / 线程 / 进程
# ---------------------------------------------------------------------------


def cpu_sequential(tasks: List[int]) -> int:
    return sum(count_primes(n) for n in tasks)


def cpu_threads(tasks: List[int], workers: int) -> int:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return sum(pool.map(count_primes, tasks))


def cpu_processes(tasks: List[int], workers: int) -> int:
    # Linux 用 fork，省掉重新导入模块的启动成本（面试里也常被追问）
    import multiprocessing as mp

    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as pool:
        return sum(pool.map(count_primes, tasks))


def timeit_call(fn, *args) -> Tuple[float, object]:
    start = time.perf_counter()
    value = fn(*args)
    return time.perf_counter() - start, value


# ---------------------------------------------------------------------------
# 基准 2：IO 密集型 —— 顺序 / 线程
# ---------------------------------------------------------------------------


def io_sequential(n: int, seconds: float) -> float:
    return sum(io_task(seconds) for _ in range(n))


def io_threads(n: int, seconds: float, workers: int) -> float:
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return sum(pool.map(io_task, [seconds] * n))


# ---------------------------------------------------------------------------
# 基准 3：忘记 join 的线程计时（真实翻车点）
# ---------------------------------------------------------------------------


def threads_without_join(n: int, seconds: float) -> Tuple[float, int]:
    """错误示范：只 start 不 join，测到的是「启动线程」的时间，不是任务时间。"""
    done: List[int] = []

    def work(i: int) -> None:
        time.sleep(seconds)
        done.append(i)

    start = time.perf_counter()
    threads = [threading.Thread(target=work, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    return time.perf_counter() - start, len(done)


def threads_with_join(n: int, seconds: float) -> Tuple[float, int]:
    done: List[int] = []

    def work(i: int) -> None:
        time.sleep(seconds)
        done.append(i)

    start = time.perf_counter()
    threads = [threading.Thread(target=work, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.perf_counter() - start, len(done)


# ---------------------------------------------------------------------------
# 基准 4：内存测量 —— getsizeof 的陷阱
# ---------------------------------------------------------------------------


def memory_report(n: int = 100_000) -> Dict[str, float]:
    """三种口径测同一个 list[int]，差距能到 4 倍以上。"""
    data = list(range(n))

    container = sys.getsizeof(data)                 # 只算指针数组
    elements = sum(sys.getsizeof(x) for x in data)  # 逐个 int 对象（小整数有缓存）
    naive_total = container + elements

    tracemalloc.start()
    data2 = list(range(n))
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del data2

    arr = array("i", range(n))
    arr_bytes = sys.getsizeof(arr)

    return {
        "n": n,
        "getsizeof_list": container,
        "sum_getsizeof_ints": elements,
        "naive_total": naive_total,
        "tracemalloc_peak": peak,
        "array_bytes": arr_bytes,
        "ratio_container_vs_real": round(peak / container, 2),
        "array_vs_list": round(peak / arr_bytes, 2),
    }


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------


def run_bench(cpu_limit: int = 20_000_000, workers: int = 4, io_n: int = 4, io_s: float = 0.2) -> dict:
    tasks = [cpu_limit] * workers

    t_seq, v_seq = timeit_call(cpu_sequential, tasks)
    t_thr, v_thr = timeit_call(cpu_threads, tasks, workers)
    t_pro, v_pro = timeit_call(cpu_processes, tasks, workers)
    assert v_seq == v_thr == v_pro, "三种方式结果必须一致，否则基准无效"

    t_io_seq, _ = timeit_call(io_sequential, io_n, io_s)
    t_io_thr, _ = timeit_call(io_threads, io_n, io_s, workers)

    t_bad, done_bad = threads_without_join(io_n, io_s)
    t_good, done_good = threads_with_join(io_n, io_s)

    # 让未 join 的线程先跑完，避免污染后续计时
    time.sleep(io_s + 0.05)

    mem = memory_report()

    return {
        "env": {
            "python": sys.version.split()[0],
            "cpu_count": os.cpu_count(),
            "platform": sys.platform,
        },
        "cpu": {
            "limit": cpu_limit,
            "tasks": workers,
            "sequential_s": round(t_seq, 3),
            "threads_s": round(t_thr, 3),
            "processes_s": round(t_pro, 3),
            "thread_speedup": round(t_seq / t_thr, 2),
            "process_speedup": round(t_seq / t_pro, 2),
            "answer": v_seq,
        },
        "io": {
            "tasks": io_n,
            "sleep_each_s": io_s,
            "sequential_s": round(t_io_seq, 3),
            "threads_s": round(t_io_thr, 3),
            "speedup": round(t_io_seq / t_io_thr, 2),
        },
        "join": {
            "without_join_s": round(t_bad, 4),
            "without_join_done": done_bad,
            "with_join_s": round(t_good, 3),
            "with_join_done": done_good,
            "expected_done": io_n,
        },
        "memory": mem,
    }


def run_self_test() -> int:
    checks = 0

    def check(cond: bool, label: str) -> None:
        nonlocal checks
        assert cond, label
        checks += 1

    # 正确性：筛法的已知值，防止「快但算错」
    check(count_primes(100) == 25, "π(100) 应为 25")
    check(count_primes(1_000_000) == 78_498, "π(1e6) 应为 78498")
    check(count_primes(2_000_000) == 148_933, "π(2e6) 应为 148933")

    # 线程池与顺序计算结果一致（不比较时间，避免机器负载导致假失败）
    tasks = [50_000, 80_000, 120_000, 200_000]
    check(cpu_sequential(tasks) == cpu_threads(tasks, 4) == cpu_processes(tasks, 4),
          "顺序/线程/进程结果一致")

    # IO：线程应显著快于顺序（4×0.05s；给足容差）
    t_seq, _ = timeit_call(io_sequential, 4, 0.05)
    t_thr, _ = timeit_call(io_threads, 4, 0.05, 4)
    check(t_thr < t_seq * 0.6, f"IO 线程应更快：seq={t_seq:.3f} thr={t_thr:.3f}")

    # 忘记 join：计时明显偏小、完成数为 0
    t_bad, done_bad = threads_without_join(4, 0.1)
    check(t_bad < 0.05, f"未 join 的计时应远小于 0.1s，实际 {t_bad:.4f}")
    check(done_bad == 0, f"未 join 时完成数应为 0，实际 {done_bad}")

    # join 后：完成数齐全、耗时 >= sleep
    t_good, done_good = threads_with_join(4, 0.1)
    check(done_good == 4, "join 后 4 个任务都应完成")
    check(t_good >= 0.1, "join 后耗时不应小于单次 sleep")

    # 内存：getsizeof 容器 << tracemalloc 真实峰值；array 更紧凑
    mem = memory_report(100_000)
    check(mem["getsizeof_list"] < mem["tracemalloc_peak"], "getsizeof 低估真实内存")
    check(mem["array_bytes"] < mem["tracemalloc_peak"], "array 应比 list[int] 紧凑")
    # 逐元素相加看起来更准，但仍不等于真实峰值：它忽略了分配器开销，
    # 也没算测量期间同时在世的另一个 list。三个口径给出三个数，才是事实。
    check(mem["naive_total"] < mem["tracemalloc_peak"], "逐元素相加仍低估真实峰值")

    print(f"✅ 04-concurrency-and-memory: {checks} 项断言全部通过")
    return checks


def print_bench(data: dict) -> None:
    env = data["env"]
    print(f"环境：Python {env['python']} / {env['cpu_count']} vCPU / {env['platform']}\n")

    cpu = data["cpu"]
    print(f"① CPU 密集：{cpu['tasks']} 个任务，每个筛到 {cpu['limit']}（答案 {cpu['answer']}）")
    print(f"   顺序 {cpu['sequential_s']:.3f}s | 线程 {cpu['threads_s']:.3f}s "
          f"({cpu['thread_speedup']}x) | 进程 {cpu['processes_s']:.3f}s ({cpu['process_speedup']}x)")

    io = data["io"]
    print(f"\n② IO 密集：{io['tasks']} 个 sleep({io['sleep_each_s']}s)")
    print(f"   顺序 {io['sequential_s']:.3f}s | 线程 {io['threads_s']:.3f}s ({io['speedup']}x)")

    j = data["join"]
    print("\n③ 忘记 join 会测到什么")
    print(f"   不 join：{j['without_join_s']:.4f}s，完成 {j['without_join_done']}/{j['expected_done']}")
    print(f"   有 join：{j['with_join_s']:.3f}s，完成 {j['with_join_done']}/{j['expected_done']}")

    m = data["memory"]
    print(f"\n④ 内存口径：list(range({m['n']}))")
    print(f"   sys.getsizeof(list)      {m['getsizeof_list']:>12,} B  ← 只有指针数组")
    print(f"   逐元素 getsizeof 之和    {m['sum_getsizeof_ints']:>12,} B  ← 高估，小整数被复用")
    print(f"   tracemalloc 峰值        {m['tracemalloc_peak']:>12,} B  ← 真实分配")
    print(f"   array('i')               {m['array_bytes']:>12,} B")
    print(f"   容器口径低估 {m['ratio_container_vs_real']}x；array 比 list[int] 省 {m['array_vs_list']}x")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Day 197 并发与内存实测")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--bench", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=20_000_000, help="CPU 基准的筛法上限")
    args = parser.parse_args(argv)

    if args.self_test:
        return 0 if run_self_test() else 1

    if args.bench:
        data = run_bench(cpu_limit=args.limit)
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print_bench(data)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
