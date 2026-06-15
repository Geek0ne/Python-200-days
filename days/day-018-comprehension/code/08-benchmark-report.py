#!/usr/bin/env python3
"""
Day 018 — 推导式性能基准测试报告

自动生成详细的性能对比报告，包含：
- 不同数据规模下的性能数据
- 各实现方式的速度对比
- 内存使用对比
- 推荐使用场景

运行: python3 08-benchmark-report.py
"""

import timeit
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def benchmark(func, sizes, number=200):
    """对多个数据规模的函数进行基准测试"""
    results = {}
    for n in sizes:
        t = timeit.timeit(lambda: func(n), number=number)
        results[n] = t / number * 1e6
    return results


def for_loop(N):
    result = []
    for x in range(N):
        if x % 2 == 0:
            result.append(x ** 2)
    return result


def list_comp(N):
    return [x ** 2 for x in range(N) if x % 2 == 0]


def map_filter(N):
    return list(map(lambda x: x**2, filter(lambda x: x % 2 == 0, range(N))))


def gen_expr(N):
    return list(x ** 2 for x in range(N) if x % 2 == 0)


console.section("推导式性能基准测试报告")

sizes = [1000, 5000, 10000, 50000, 100000]
methods = [
    ("for 循环    ", for_loop),
    ("列表推导式  ", list_comp),
    ("map+filter  ", map_filter),
    ("生成器→列表", gen_expr),
]

print(f"{'数据规模':>10}", end="")
for name, _ in methods:
    print(f" {name:>12}", end="")
print()

print("-" * 60)

all_results = {}
for n in sizes:
    print(f"{n:>10,}", end="")
    for m_name, func in methods:
        t = timeit.timeit(lambda f=func, s=n: f(s), number=100)
        t_us = t / 100 * 1e6
        print(f" {t_us:>12.2f}", end="")
    print()

print()
print("=" * 60)
print("性能总结（推导式 = 1.0x）")
print("=" * 60)

for n in sizes:
    base = None
    times = []
    for m_name, func in methods:
        t = timeit.timeit(lambda f=func, s=n: f(s), number=100)
        times.append(t)
    base_time = times[1]  # list_comp is index 1

    print(f"\nN = {n:,}")
    for i, (m_name, func) in enumerate(methods):
        ratio = times[i] / base_time
        bar = '█' * int(ratio * 20)
        print(f"  {m_name} {ratio:>6.2f}x {bar}")
