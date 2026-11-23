#!/usr/bin/env python3
"""
Day 092 - 代码优化技巧: 高级优化技巧
演示向量化、并行处理、惰性求值等
"""

import time
import random
from functools import lru_cache, wraps
from itertools import islice, chain
from typing import List, Tuple


# ═══════════════════════════════════════════════
# 1. 装饰器优化
# ═══════════════════════════════════════════════

def timer_decorator(func):
    """计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"  ⏱️ {func.__name__}: {(end-start)*1000:.3f}ms")
        return result
    return wrapper


def memoize(func):
    """手动实现缓存装饰器"""
    cache = {}
    
    @wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    
    wrapper.cache = cache
    return wrapper


# ═══════════════════════════════════════════════
# 2. 生成器与惰性求值
# ═══════════════════════════════════════════════

def demo_generator_optimization():
    """演示生成器与惰性求值"""
    print("=" * 60)
    print("  Day 092 — 高级优化技巧演示")
    print("=" * 60)
    
    print("\n【1. 生成器与惰性求值】")
    print("-" * 40)
    
    # 列表 vs 生成器
    print("  内存对比:")
    
    # 列表推导
    start = time.perf_counter()
    lst = [i ** 2 for i in range(1000000)]
    list_time = time.perf_counter() - start
    
    # 生成器表达式
    start = time.perf_counter()
    gen = (i ** 2 for i in range(1000000))
    gen_time = time.perf_counter() - start
    
    import sys
    print(f"  列表: {list_time*1000:.3f}ms, ~{sys.getsizeof(lst)/1024/1024:.1f}MB")
    print(f"  生成器: {gen_time*1000:.3f}ms, ~{sys.getsizeof(gen)/1024:.1f}KB")
    
    # 惰性求值的优势
    print(f"\n  惰性求值: 只处理需要的数据")
    
    def process_large_dataset():
        """模拟处理大数据集"""
        for i in range(1000000):
            yield i ** 2 + i * 3
    
    # 只取前10个
    start = time.perf_counter()
    result = list(islice(process_large_dataset(), 10))
    lazy_time = time.perf_counter() - start
    print(f"  惰性求值 (取前10个): {lazy_time*1000:.3f}ms")
    print(f"  结果: {result}")


# ═══════════════════════════════════════════════
# 3. 内置函数优化
# ═══════════════════════════════════════════════

@timer_decorator
def demo_builtin_optimization():
    """演示内置函数优化"""
    print("\n【2. 内置函数优化】")
    print("-" * 40)
    
    data = list(range(100000))
    
    # sum vs 手动累加
    print(f"  累加操作:")
    
    # 手动累加
    start = time.perf_counter()
    total_manual = 0
    for x in data:
        total_manual += x
    manual_time = time.perf_counter() - start
    
    # 内置 sum
    start = time.perf_counter()
    total_builtin = sum(data)
    builtin_time = time.perf_counter() - start
    
    print(f"  手动累加: {manual_time*1000:.3f}ms")
    print(f"  内置 sum: {builtin_time*1000:.3f}ms")
    print(f"  提速: {manual_time/builtin_time:.1f}x")
    
    # any/all vs 手动检查
    print(f"\n  条件检查:")
    targets = random.sample(range(100000), 100)
    
    # 手动检查
    start = time.perf_counter()
    found_manual = False
    for t in targets:
        if t in data:
            found_manual = True
            break
    manual_time = time.perf_counter() - start
    
    # 内置 any
    start = time.perf_counter()
    found_builtin = any(t in data for t in targets)
    builtin_time = time.perf_counter() - start
    
    print(f"  手动检查: {manual_time*1000:.3f}ms")
    print(f"  内置 any: {builtin_time*1000:.3f}ms")
    print(f"  提速: {manual_time/builtin_time:.1f}x")


# ═══════════════════════════════════════════════
# 4. 缓存策略进阶
# ═══════════════════════════════════════════════

@timer_decorator
def demo_advanced_caching():
    """演示高级缓存策略"""
    print("\n【3. 高级缓存策略】")
    print("-" * 40)
    
    # LRU 缓存
    @lru_cache(maxsize=256)
    def fibonacci(n):
        if n < 2:
            return n
        return fibonacci(n-1) + fibonacci(n-2)
    
    # 清除缓存
    fibonacci.cache_clear()
    
    start = time.perf_counter()
    result = fibonacci(100)
    lru_time = time.perf_counter() - start
    
    print(f"  LRU 缓存 (fib(100)):")
    print(f"  结果: {result}")
    print(f"  缓存信息: {fibonacci.cache_info()}")
    
    # 手动实现缓存
    @memoize
    def fibonacci_manual(n):
        if n < 2:
            return n
        return fibonacci_manual(n-1) + fibonacci_manual(n-2)
    
    start = time.perf_counter()
    result = fibonacci_manual(100)
    manual_time = time.perf_counter() - start
    
    print(f"\n  手动缓存 (fib(100)):")
    print(f"  结果: {result}")
    print(f"  缓存大小: {len(fibonacci_manual.cache)}")


# ═══════════════════════════════════════════════
# 5. 数据处理优化
# ═══════════════════════════════════════════════

@timer_decorator
def demo_data_processing_optimization():
    """演示数据处理优化"""
    print("\n【4. 数据处理优化】")
    print("-" * 40)
    
    # 链式操作优化
    data = list(range(100000))
    
    # 多次遍历
    start = time.perf_counter()
    filtered = [x for x in data if x % 2 == 0]
    transformed = [x ** 2 for x in filtered]
    result_multi = sum(transformed)
    multi_time = time.perf_counter() - start
    
    # 单次遍历
    start = time.perf_counter()
    result_single = 0
    for x in data:
        if x % 2 == 0:
            result_single += x ** 2
    single_time = time.perf_counter() - start
    
    print(f"  多次遍历: {multi_time*1000:.3f}ms")
    print(f"  单次遍历: {single_time*1000:.3f}ms")
    print(f"  提速: {multi_time/single_time:.1f}x")
    
    # 使用 map + filter
    start = time.perf_counter()
    result_map = sum(map(lambda x: x ** 2, filter(lambda x: x % 2 == 0, data)))
    map_time = time.perf_counter() - start
    
    print(f"\n  map + filter: {map_time*1000:.3f}ms")
    
    # 使用 zip 并行处理
    print(f"\n  zip 并行处理:")
    data1 = list(range(10000))
    data2 = list(range(10000, 20000))
    
    # 顺序处理
    start = time.perf_counter()
    result_seq = [data1[i] + data2[i] for i in range(len(data1))]
    seq_time = time.perf_counter() - start
    
    # zip 并行
    start = time.perf_counter()
    result_zip = [a + b for a, b in zip(data1, data2)]
    zip_time = time.perf_counter() - start
    
    print(f"  顺序处理: {seq_time*1000:.3f}ms")
    print(f"  zip 并行: {zip_time*1000:.3f}ms")
    print(f"  提速: {seq_time/zip_time:.1f}x")


# ═══════════════════════════════════════════════
# 6. 字符串处理优化
# ═══════════════════════════════════════════════

@timer_decorator
def demo_string_optimization():
    """演示字符串处理优化"""
    print("\n【5. 字符串处理优化】")
    print("-" * 40)
    
    n = 10000
    
    # 字符串拼接
    start = time.perf_counter()
    result = ""
    for i in range(n):
        result += str(i)
    concat_time = time.perf_counter() - start
    
    # join
    start = time.perf_counter()
    parts = [str(i) for i in range(n)]
    result = "".join(parts)
    join_time = time.perf_counter() - start
    
    # 使用 f-string
    start = time.perf_counter()
    result = "".join(f"{i}" for i in range(n))
    fstring_time = time.perf_counter() - start
    
    print(f"  字符串拼接: {concat_time*1000:.3f}ms")
    print(f"  join: {join_time*1000:.3f}ms")
    print(f"  f-string: {fstring_time*1000:.3f}ms")
    print(f"  join vs 拼接: {concat_time/join_time:.1f}x")
    
    # 正则表达式优化
    import re
    
    text = " ".join(["word" + str(i) for i in range(1000)])
    
    # 每次编译
    start = time.perf_counter()
    for _ in range(100):
        re.search(r'word\d+', text)
    recompile_time = time.perf_counter() - start
    
    # 预编译
    pattern = re.compile(r'word\d+')
    start = time.perf_counter()
    for _ in range(100):
        pattern.search(text)
    precompile_time = time.perf_counter() - start
    
    print(f"\n  正则表达式优化:")
    print(f"  每次编译: {recompile_time*1000:.3f}ms")
    print(f"  预编译: {precompile_time*1000:.3f}ms")
    print(f"  提速: {recompile_time/precompile_time:.1f}x")


# ═══════════════════════════════════════════════
# 7. 性能对比总结
# ═══════════════════════════════════════════════

@timer_decorator
def demo_performance_summary():
    """性能对比总结"""
    print("\n【6. 性能对比总结】")
    print("-" * 40)
    
    print("""
  优化策略效果对比:
  ┌─────────────────┬────────────┬────────────┬────────┐
  │ 优化策略         │ 优化前     │ 优化后     │ 提速   │
  ├─────────────────┼────────────┼────────────┼────────┤
  │ 列表→集合查找   │ O(n)       │ O(1)       │ 100x+  │
  │ 列表→双端队列   │ O(n) insert│ O(1) insert│ 10x+   │
  │ 多次→单次遍历   │ 3n 操作    │ n 操作     │ 3x     │
  │ 字符串拼接→join │ O(n²)      │ O(n)       │ 10x+   │
  │ 无缓存→LRU缓存  │ 指数时间   │ 线性时间   │ 1000x+ │
  │ 列表→生成器     │ O(n) 内存  │ O(1) 内存  │ 内存   │
  └─────────────────┴────────────┴────────────┴────────┘
""")


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    demo_generator_optimization()
    demo_builtin_optimization()
    demo_advanced_caching()
    demo_data_processing_optimization()
    demo_string_optimization()
    demo_performance_summary()
    
    print("\n✅ 高级优化技巧演示完成!")
