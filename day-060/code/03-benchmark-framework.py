"""
Day 060 - 阶段项目：性能基准测试框架
通用性能测试 + Amdahl 定律验证

运行方式：python3 03-benchmark-framework.py
"""

import time
import math
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable, List, Dict
import numpy as np

# ─── 基准测试工具 ───

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    mean_ms: float
    median_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    p99_ms: float
    n_runs: int
    throughput: float  # ops/sec


def benchmark(func: Callable, *args, n_runs: int = 20, warmup: int = 3,
              name: str = "unknown") -> BenchmarkResult:
    """
    通用基准测试
    - warmup: 预热次数（JIT 编译需要）
    - n_runs: 正式测试次数
    """
    # 预热
    for _ in range(warmup):
        func(*args)

    # 正式测试
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        result = func(*args)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    times.sort()
    n = len(times)
    mean = sum(times) / n

    return BenchmarkResult(
        name=name,
        mean_ms=mean,
        median_ms=times[n // 2],
        min_ms=times[0],
        max_ms=times[-1],
        p95_ms=times[int(n * 0.95)],
        p99_ms=times[int(n * 0.99)],
        n_runs=n,
        throughput=1000.0 / mean if mean > 0 else 0,
    )


def print_benchmark(results: List[BenchmarkResult]):
    """格式化打印基准测试结果"""
    print(f"\n{'名称':<25} {'平均':>8} {'中位':>8} {'最小':>8} {'P95':>8} {'吞吐':>10}")
    print("-" * 70)
    for r in results:
        print(f"{r.name:<25} {r.mean_ms:>7.2f}ms {r.median_ms:>7.2f}ms "
              f"{r.min_ms:>7.2f}ms {r.p95_ms:>7.2f}ms {r.throughput:>8.1f}/s")


# ─── 测试用例 ───

def cpu_bound_loop(n):
    """纯 CPU 循环"""
    total = 0
    for i in range(n):
        total += math.sqrt(i)
    return total


def cpu_bound_numpy(n):
    """NumPy 向量化"""
    arr = np.arange(n, dtype=np.float64)
    return np.sum(np.sqrt(arr))


def matrix_multiply_numpy(size):
    """NumPy 矩阵乘法"""
    a = np.random.rand(size, size)
    b = np.random.rand(size, size)
    return np.dot(a, b)


def fibonacci_recursive(n):
    """递归斐波那契"""
    if n <= 1:
        return n
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


def fibonacci_iterative(n):
    """迭代斐波那契"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# ─── 并行基准测试 ───

def parallel_benchmark(func, data_chunks, max_workers=None):
    """并行执行基准测试"""
    max_workers = max_workers or mp.cpu_count()

    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, chunk): i
                   for i, chunk in enumerate(data_chunks)}
        results = {}
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    total = time.perf_counter() - start

    return total, results


# ─── Amdahl 定律验证 ───

def amdahl_law(P, N):
    """
    Amdahl 定律
    P: 可并行比例
    N: 处理器数
    返回: 理论加速比
    """
    return 1.0 / ((1 - P) + P / N)


def verify_amdahl():
    """验证 Amdahl 定律"""
    print("\n" + "=" * 60)
    print("Amdahl 定律验证")
    print("=" * 60)

    # 任务：计算 100 万个数的平方根
    n = 1_000_000
    chunk_size = n // 4  # 4 个 chunk

    # 串行时间
    data = list(range(n))
    serial_result = cpu_bound_loop(n)
    serial_time = benchmark(cpu_bound_loop, n, n_runs=5, name="串行").mean_ms

    # 并行测试
    print(f"\n{'Workers':>8} {'实际加速比':>12} {'理论加速比':>12} {'误差':>8}")
    print("-" * 45)

    for workers in [1, 2, 4]:
        chunks = [list(range(i * chunk_size, (i + 1) * chunk_size))
                  for i in range(workers)]

        total_time, _ = parallel_benchmark(cpu_bound_loop, chunks, workers)

        # 理论加速比（假设 90% 可并行）
        P = 0.9
        theoretical = amdahl_law(P, workers)
        actual = serial_time / (total_time * 1000) if total_time > 0 else 0
        error = abs(actual - theoretical) / theoretical * 100

        print(f"{workers:>8} {actual:>11.2f}x {theoretical:>11.2f}x {error:>7.1f}%")

    print(f"\n💡 注意：实际加速比通常低于理论值，因为：")
    print(f"   1. 进程间通信有开销")
    print(f"   2. 数据分片和结果合并有开销")
    print(f"   3. 不是所有代码都能完美并行")


# ─── 主测试 ───

def main():
    print("=" * 60)
    print("高性能计算 — 性能基准测试")
    print("=" * 60)

    # 1. CPU 密集型测试
    print("\n--- CPU 密集型 ---")
    results = []
    results.append(benchmark(cpu_bound_loop, 500_000, name="纯循环"))
    results.append(benchmark(cpu_bound_numpy, 500_000, name="NumPy 向量化"))
    results.append(benchmark(fibonacci_iterative, 100, name="迭代斐波那契"))
    print_benchmark(results)

    # 2. 矩阵运算
    print("\n--- 矩阵运算 ---")
    results = []
    results.append(benchmark(matrix_multiply_numpy, 100, name="矩阵乘法 100x100"))
    results.append(benchmark(matrix_multiply_numpy, 200, name="矩阵乘法 200x200"))
    results.append(benchmark(matrix_multiply_numpy, 500, name="矩阵乘法 500x500"))
    print_benchmark(results)

    # 3. 并行加速
    print("\n--- 并行加速测试 ---")
    n = 200_000
    serial = benchmark(cpu_bound_loop, n, name="串行 200K")
    print(f"\n串行: {serial.mean_ms:.2f}ms")

    for workers in [2, 4]:
        chunk_size = n // workers
        chunks = [list(range(i * chunk_size, (i + 1) * chunk_size))
                  for i in range(workers)]
        total_time, _ = parallel_benchmark(cpu_bound_loop, chunks, workers)
        parallel_ms = total_time * 1000
        speedup = serial.mean_ms / parallel_ms
        print(f"并行({workers}w): {parallel_ms:.2f}ms (加速 {speedup:.2f}x)")

    # 4. Amdahl 定律
    verify_amdahl()

    print("\n✅ 基准测试完成！")


if __name__ == "__main__":
    main()
