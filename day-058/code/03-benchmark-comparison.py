"""
03-benchmark-comparison.py — 三种并发模型性能基准测试
对比线程、进程、协程在 CPU 密集型和 I/O 密集型任务中的表现
"""

import time
import asyncio
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor


# ── 任务定义 ──

def cpu_bound_task(n):
    """CPU 密集型任务：计算质数个数"""
    count = 0
    for i in range(2, n):
        if all(i % j != 0 for j in range(2, int(i**0.5) + 1)):
            count += 1
    return count


def io_bound_task(delay):
    """I/O 密集型任务：模拟网络请求"""
    time.sleep(delay)
    return f"done-{delay}"


async def io_bound_async(delay):
    """异步 I/O 任务"""
    await asyncio.sleep(delay)
    return f"done-{delay}"


# ── CPU 密集型基准测试 ──

def benchmark_cpu_serial(n, rounds):
    """串行执行"""
    start = time.time()
    for _ in range(rounds):
        cpu_bound_task(n)
    return time.time() - start


def benchmark_cpu_threaded(n, rounds):
    """多线程执行"""
    start = time.time()
    threads = []
    for _ in range(rounds):
        t = threading.Thread(target=cpu_bound_task, args=(n,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    return time.time() - start


def benchmark_cpu_multiprocess(n, rounds):
    """多进程执行"""
    start = time.time()
    processes = []
    for _ in range(rounds):
        p = multiprocessing.Process(target=cpu_bound_task, args=(n,))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    return time.time() - start


def benchmark_cpu_coroutine(n, rounds):
    """协程执行（单线程，无加速）"""
    start = time.time()
    for _ in range(rounds):
        cpu_bound_task(n)
    return time.time() - start


def benchmark_cpu_pool(n, rounds):
    """进程池执行"""
    start = time.time()
    with ProcessPoolExecutor(max_workers=rounds) as executor:
        list(executor.map(cpu_bound_task, [n] * rounds))
    return time.time() - start


# ── I/O 密集型基准测试 ──

def benchmark_io_serial(delay, count):
    """串行 I/O"""
    start = time.time()
    for _ in range(count):
        io_bound_task(delay)
    return time.time() - start


def benchmark_io_threaded(delay, count, workers=10):
    """多线程 I/O"""
    start = time.time()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(io_bound_task, [delay] * count))
    return time.time() - start


def benchmark_io_coroutine(delay, count):
    """异步 I/O"""
    async def run():
        start = time.time()
        tasks = [io_bound_async(delay) for _ in range(count)]
        await asyncio.gather(*tasks)
        return time.time() - start

    return asyncio.run(run())


# ── 主测试 ──

def run_benchmarks():
    print("=" * 60)
    print("🔬 并发模型性能基准测试")
    print("=" * 60)

    # CPU 密集型测试
    print("\n📊 测试 1: CPU 密集型 (计算质数)")
    print("-" * 50)

    n = 3000
    rounds = 4

    serial = benchmark_cpu_serial(n, rounds)
    threaded = benchmark_cpu_threaded(n, rounds)
    multiprocess = benchmark_cpu_multiprocess(n, rounds)
    pool = benchmark_cpu_pool(n, rounds)

    print(f"  串行执行:   {serial:.2f}s  (基准 1.00x)")
    print(f"  多线程:     {threaded:.2f}s  ({serial/threaded:.2f}x)")
    print(f"  多进程:     {multiprocess:.2f}s  ({serial/multiprocess:.2f}x)")
    print(f"  进程池:     {pool:.2f}s  ({serial/pool:.2f}x)")

    if threaded > serial:
        print(f"  ⚠️  多线程比串行慢 (GIL 争抢)")
    if multiprocess < serial:
        print(f"  ✅ 多进程有效加速 (绕过 GIL)")

    # I/O 密集型测试
    print("\n📊 测试 2: I/O 密集型 (模拟网络请求)")
    print("-" * 50)

    delay = 0.1
    count = 20

    serial_io = benchmark_io_serial(delay, count)
    threaded_io = benchmark_io_threaded(delay, count, workers=10)
    async_io = benchmark_io_coroutine(delay, count)

    print(f"  串行执行:   {serial_io:.2f}s  (基准 1.00x)")
    print(f"  多线程(10): {threaded_io:.2f}s  ({serial_io/threaded_io:.2f}x)")
    print(f"  协程:       {async_io:.2f}s  ({serial_io/async_io:.2f}x)")

    if threaded_io < serial_io:
        print(f"  ✅ 多线程有效加速 I/O 任务")
    if async_io < threaded_io:
        print(f"  ✅ 协程比多线程更高效")

    # 资源消耗对比
    print("\n📊 测试 3: 资源消耗估算")
    print("-" * 50)
    print("  指标          线程        进程        协程")
    print("  ─────────────────────────────────────────")
    print("  内存占用      ~8MB/个     ~50MB/个    ~1KB/个")
    print("  创建开销      ~10ms       ~100ms      ~0.01ms")
    print("  上下文切换    ~1ms        ~5ms        ~0.01ms")
    print("  最大并发      ~数百       ~数十       ~数万")

    # 总结
    print("\n" + "=" * 60)
    print("📋 测试总结")
    print("=" * 60)
    print("  • CPU 密集型 → 多进程 (绕过 GIL, 多核并行)")
    print("  • I/O 密集型 → 协程 (轻量级, 高并发)")
    print("  • 混合型     → 线程池 + 进程池 (各取所长)")
    print("  • 多线程 CPU → 比串行更慢 (GIL 争抢!)")
    print("  • 协程 CPU   → 无加速效果 (单线程执行)")
    print()


if __name__ == "__main__":
    run_benchmarks()
    print("✅ 基准测试完成")
