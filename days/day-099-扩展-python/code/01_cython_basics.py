"""
Day 099 - Cython 基础示例
演示如何用 Cython 加速 Python 计算

运行方式（需要安装 cython）:
    pip install cython
    cythonize -i 01_cython_basics.pyx

注意：这里提供 .py 版本用于演示，实际需要 .pyx 文件
本文件模拟 Cython 的效果，展示纯 Python vs 优化后的对比
"""

import time
import math


# ============================================
# 1. 纯 Python 实现
# ============================================

def fibonacci_python(n: int) -> int:
    """纯 Python 斐波那契数列"""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def sum_of_squares_python(n: int) -> int:
    """纯 Python 计算 1² + 2² + ... + n²"""
    total = 0
    for i in range(1, n + 1):
        total += i * i
    return total


def primes_python(limit: int) -> list:
    """纯 Python 素数筛选"""
    primes = []
    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, int(math.sqrt(num)) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            primes.append(num)
    return primes


# ============================================
# 2. 优化版本（模拟 Cython 效果）
# ============================================

def fibonacci_optimized(n: int) -> int:
    """
    优化后的斐波那契：减少变量分配
    Cython 版本会声明 cdef long long a, b = 0, 1
    """
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def sum_of_squares_optimized(n: int) -> int:
    """
    优化后的求和：使用数学公式 n*(n+1)*(2n+1)/6
    O(n) -> O(1)，这是算法优化而非编译优化
    """
    return n * (n + 1) * (2 * n + 1) // 6


def primes_optimized(limit: int) -> list:
    """
    优化后的素数筛选：埃拉托斯特尼筛法
    从 O(n√n) 降到 O(n log log n)
    """
    if limit < 2:
        return []
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(math.sqrt(limit)) + 1):
        if sieve[i]:
            for j in range(i * i, limit + 1, i):
                sieve[j] = False
    return [i for i, is_p in enumerate(sieve) if is_p]


# ============================================
# 3. 性能测试
# ============================================

def benchmark(func, *args, runs=3):
    """运行函数并返回平均耗时"""
    times = []
    result = None
    for _ in range(runs):
        start = time.perf_counter()
        result = func(*args)
        times.append(time.perf_counter() - start)
    avg = sum(times) / len(times)
    return result, avg


if __name__ == "__main__":
    print("=" * 60)
    print("Day 099 - Cython 基础示例")
    print("=" * 60)

    # --- Fibonacci ---
    n = 500_000
    print(f"\n📊 斐波那契数列 (n={n})")

    r1, t1 = benchmark(fibonacci_python, n)
    r2, t2 = benchmark(fibonacci_optimized, n)

    print(f"  纯 Python:     {t1:.4f}s")
    print(f"  优化版本:      {t2:.4f}s")
    print(f"  加速比:        {t1/t2:.1f}x")
    print(f"  结果一致:      {r1 == r2}")

    # --- Sum of Squares ---
    n = 1_000_000
    print(f"\n📊 平方和 (n={n})")

    r1, t1 = benchmark(sum_of_squares_python, n)
    r2, t2 = benchmark(sum_of_squares_optimized, n)

    print(f"  纯 Python O(n):   {t1:.4f}s")
    print(f"  数学公式 O(1):    {t2:.6f}s")
    print(f"  加速比:           {t1/t2:.0f}x")
    print(f"  结果一致:         {r1 == r2}")

    # --- Primes ---
    n = 100_000
    print(f"\n📊 素数筛选 (n={n})")

    r1, t1 = benchmark(primes_python, n)
    r2, t2 = benchmark(primes_optimized, n)

    print(f"  纯 Python O(n√n):  {t1:.4f}s")
    print(f"  筛法 O(n loglogn): {t2:.4f}s")
    print(f"  加速比:            {t1/t2:.1f}x")
    print(f"  素数数量:          {len(r1)}")
    print(f"  结果一致:          {r1 == r2}")

    # --- 说明 ---
    print("\n" + "=" * 60)
    print("💡 说明")
    print("=" * 60)
    print("""
    上面演示的是「算法优化」的效果。Cython 真正的威力在于：
    
    1. 类型声明消除 Python 对象开销
       cdef int i  →  C int，无需装箱
       
    2. 直接调用 C 库函数
       from libc.math cimport sqrt
       
    3. 禁用边界检查
       @cython.boundscheck(False)
       @cython.wraparound(False)
    
    用 Cython 编译后，斐波那契函数可以再快 50-100 倍！
    """)

    # --- Cython .pyx 示例代码（不能直接运行） ---
    print("=" * 60)
    print("📝 对应的 Cython (.pyx) 代码示例")
    print("=" * 60)
    print("""
    # fibonacci.pyx
    
    cpdef long long fibonacci_cy(int n):
        cdef long long a = 0, b = 1
        cdef int i
        for i in range(n):
            a, b = b, a + b
        return a
    
    # setup.py
    from setuptools import setup
    from Cython.Build import cythonize
    
    setup(
        ext_modules=cythonize("fibonacci.pyx"),
    )
    
    # 编译: python setup.py build_ext --inplace
    # 使用: from fibonacci import fibonacci_cy
    #        result = fibonacci_cy(500000)
    """)
