"""
Day 059 - Numba JIT 编译加速
基础用法：用 @jit 装饰器加速 Python 函数

运行方式：python3 01-numba-jit.py
依赖：pip install numba numpy
"""

import time
import random
import numpy as np
from numba import jit, prange, cuda

# ─── 1. 基础 @jit 装饰器 ───

@jit(nopython=True)
def sum_range_pure(n):
    """纯循环求和 — Numba 最擅长的场景"""
    total = 0
    for i in range(n):
        total += i
    return total


@jit(nopython=True)
def monte_carlo_pi(n_samples):
    """
    蒙特卡洛估算 π
    - 随机撒点在 [0,1]×[0,1] 正方形内
    - 统计落在单位圆内的比例 × 4 = π
    """
    count = 0
    for _ in range(n_samples):
        x = random.random()
        y = random.random()
        if x * x + y * y <= 1.0:
            count += 1
    return 4.0 * count / n_samples


@jit(nopython=True, cache=True)
def fibonacci_fast(n):
    """
    递推计算第 n 个斐波那契数
    cache=True 避免重复编译
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# ─── 2. 数组操作 ───

@jit(nopython=True)
def array_multiply(arr, factor):
    """逐元素乘法 — 用 Numba 替代 Python 循环"""
    result = np.empty_like(arr)
    for i in range(len(arr)):
        result[i] = arr[i] * factor
    return result


@jit(nopython=True, parallel=True)
def parallel_dot(a, b):
    """
    并行点积运算
    parallel=True 自动利用多核
    """
    total = 0.0
    for i in prange(len(a)):
        total += a[i] * b[i]
    return total


# ─── 3. 性能对比 ───

def benchmark():
    n = 10_000_000

    print("=" * 60)
    print("Numba JIT 性能测试")
    print("=" * 60)

    # --- sum_range ---
    print("\n--- 循环求和 (n={:,}) ---".format(n))

    # 纯 Python
    start = time.perf_counter()
    py_result = sum(range(n))
    py_time = time.perf_counter() - start
    print(f"  Python sum(): {py_time:.4f}s")

    # Numba 首次调用（含编译）
    start = time.perf_counter()
    _ = sum_range_pure(n)
    first_time = time.perf_counter() - start
    print(f"  Numba (首次，含编译): {first_time:.4f}s")

    # Numba 后续调用
    start = time.perf_counter()
    _ = sum_range_pure(n)
    fast_time = time.perf_counter() - start
    print(f"  Numba (后续调用): {fast_time:.6f}s")
    print(f"  加速比: {py_time / fast_time:.1f}x")

    # --- Monte Carlo π ---
    n_mc = 5_000_000
    print(f"\n--- 蒙特卡洛 π 估算 (n={n_mc:,}) ---")

    # 纯 Python
    start = time.perf_counter()
    count = 0
    for _ in range(n_mc):
        x, y = random.random(), random.random()
        if x * x + y * y <= 1:
            count += 1
    py_pi = 4.0 * count / n_mc
    py_time = time.perf_counter() - start
    print(f"  Python: π ≈ {py_pi:.6f}, 耗时 {py_time:.3f}s")

    # Numba
    start = time.perf_counter()
    _ = monte_carlo_pi(100)  # 预热
    start = time.perf_counter()
    nba_pi = monte_carlo_pi(n_mc)
    nba_time = time.perf_counter() - start
    print(f"  Numba:  π ≈ {nba_pi:.6f}, 耗时 {nba_time:.3f}s")
    print(f"  加速比: {py_time / nba_time:.1f}x")

    # --- 并行点积 ---
    size = 10_000_000
    a = np.random.rand(size)
    b = np.random.rand(size)

    print(f"\n--- 并行点积 (n={size:,}) ---")

    start = time.perf_counter()
    np_result = np.dot(a, b)
    np_time = time.perf_counter() - start
    print(f"  NumPy np.dot(): {np_time:.6f}s")

    _ = parallel_dot(a[:100], b[:100])  # 预热
    start = time.perf_counter()
    nba_result = parallel_dot(a, b)
    nba_time = time.perf_counter() - start
    print(f"  Numba parallel: {nba_time:.6f}s")
    print(f"  差异: {abs(np_result - nba_result):.2e}")

    # --- Fibonacci ---
    print(f"\n--- 斐波那契数列 ---")
    start = time.perf_counter()
    for i in range(50):
        fibonacci_fast(i)
    fib_time = time.perf_counter() - start
    print(f"  计算 fib(0..49) 共 {fib_time:.4f}s")
    print(f"  fib(49) = {fibonacci_fast(49)}")


if __name__ == "__main__":
    benchmark()
    print("\n✅ Numba 测试完成！")
