#!/usr/bin/env python3
"""
Day 092 - 代码优化技巧: 数据结构与算法优化
演示常见数据结构选择和算法优化
"""

import time
import random
from collections import defaultdict, Counter, deque
from functools import lru_cache


# ═══════════════════════════════════════════════
# 1. 查找操作优化
# ═══════════════════════════════════════════════

def demo_lookup_optimization():
    """演示查找操作优化"""
    print("=" * 60)
    print("  Day 092 — 数据结构与算法优化演示")
    print("=" * 60)
    
    print("\n【1. 查找操作优化】")
    print("-" * 40)
    
    random.seed(42)
    data = list(range(10000))
    targets = random.sample(data, 100)
    
    # 列表查找
    start = time.perf_counter()
    for t in targets:
        _ = t in data
    list_time = time.perf_counter() - start
    
    # 集合查找
    data_set = set(data)
    start = time.perf_counter()
    for t in targets:
        _ = t in data_set
    set_time = time.perf_counter() - start
    
    print(f"  数据大小: {len(data)}")
    print(f"  查找次数: {len(targets)}")
    print(f"  列表查找: {list_time*1000:.3f}ms")
    print(f"  集合查找: {set_time*1000:.3f}ms")
    print(f"  提速: {list_time/set_time:.1f}x")


# ═══════════════════════════════════════════════
# 2. 频繁插入优化
# ═══════════════════════════════════════════════

def demo_insert_optimization():
    """演示频繁插入优化"""
    print("\n【2. 频繁插入优化】")
    print("-" * 40)
    
    n = 10000
    
    # 列表头部插入
    start = time.perf_counter()
    lst = []
    for i in range(n):
        lst.insert(0, i)
    list_insert_time = time.perf_counter() - start
    
    # 双端队列头部插入
    start = time.perf_counter()
    dq = deque()
    for i in range(n):
        dq.appendleft(i)
    deque_insert_time = time.perf_counter() - start
    
    print(f"  插入次数: {n}")
    print(f"  列表头部插入: {list_insert_time*1000:.3f}ms")
    print(f"  双端队列头部插入: {deque_insert_time*1000:.3f}ms")
    print(f"  提速: {list_insert_time/deque_insert_time:.1f}x")


# ═══════════════════════════════════════════════
# 3. 计数与分组优化
# ═══════════════════════════════════════════════

def demo_count_optimization():
    """演示计数与分组优化"""
    print("\n【3. 计数与分组优化】")
    print("-" * 40)
    
    random.seed(42)
    data = [random.choice("ABCDE") for _ in range(10000)]
    
    # 手动计数
    start = time.perf_counter()
    counts_manual = {}
    for item in data:
        if item in counts_manual:
            counts_manual[item] += 1
        else:
            counts_manual[item] = 1
    manual_time = time.perf_counter() - start
    
    # Counter
    start = time.perf_counter()
    counts_counter = Counter(data)
    counter_time = time.perf_counter() - start
    
    # defaultdict
    start = time.perf_counter()
    counts_default = defaultdict(int)
    for item in data:
        counts_default[item] += 1
    default_time = time.perf_counter() - start
    
    print(f"  数据大小: {len(data)}")
    print(f"  手动计数: {manual_time*1000:.3f}ms")
    print(f"  Counter: {counter_time*1000:.3f}ms")
    print(f"  defaultdict: {default_time*1000:.3f}ms")
    print(f"  Counter vs 手动: {manual_time/counter_time:.1f}x")


# ═══════════════════════════════════════════════
# 4. 循环优化
# ═══════════════════════════════════════════════

def demo_loop_optimization():
    """演示循环优化"""
    print("\n【4. 循环优化】")
    print("-" * 40)
    
    data = list(range(100000))
    
    # 多次遍历
    start = time.perf_counter()
    max_val = max(data)
    min_val = min(data)
    avg_val = sum(data) / len(data)
    multi_pass_time = time.perf_counter() - start
    
    # 单次遍历
    start = time.perf_counter()
    max_val2 = float("-inf")
    min_val2 = float("inf")
    total = 0
    for item in data:
        if item > max_val2:
            max_val2 = item
        if item < min_val2:
            min_val2 = item
        total += item
    avg_val2 = total / len(data)
    single_pass_time = time.perf_counter() - start
    
    print(f"  数据大小: {len(data)}")
    print(f"  多次遍历: {multi_pass_time*1000:.3f}ms")
    print(f"  单次遍历: {single_pass_time*1000:.3f}ms")
    print(f"  提速: {multi_pass_time/single_pass_time:.1f}x")
    
    # 内置函数 vs 手动循环
    print(f"\n  内置函数 vs 手动循环:")
    
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


# ═══════════════════════════════════════════════
# 5. 缓存策略
# ═══════════════════════════════════════════════

def demo_cache_optimization():
    """演示缓存策略"""
    print("\n【5. 缓存策略】")
    print("-" * 40)
    
    # 斐波那契数列
    def fib_slow(n):
        """无缓存"""
        if n < 2:
            return n
        return fib_slow(n-1) + fib_slow(n-2)
    
    @lru_cache(maxsize=128)
    def fib_fast(n):
        """有缓存"""
        if n < 2:
            return n
        return fib_fast(n-1) + fib_fast(n-2)
    
    n = 30
    
    start = time.perf_counter()
    result_slow = fib_slow(n)
    slow_time = time.perf_counter() - start
    
    start = time.perf_counter()
    result_fast = fib_fast(n)
    fast_time = time.perf_counter() - start
    
    print(f"  fib({n}):")
    print(f"  无缓存: {slow_time*1000:.3f}ms")
    print(f"  有缓存: {fast_time*1000:.3f}ms")
    print(f"  提速: {slow_time/fast_time:.0f}x")
    print(f"  结果: {result_slow}")


# ═══════════════════════════════════════════════
# 6. 字符串优化
# ═══════════════════════════════════════════════

def demo_string_optimization():
    """演示字符串优化"""
    print("\n【6. 字符串优化】")
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
    
    # StringIO
    from io import StringIO
    start = time.perf_counter()
    buffer = StringIO()
    for i in range(n):
        buffer.write(str(i))
    result = buffer.getvalue()
    io_time = time.perf_counter() - start
    
    print(f"  字符串拼接: {concat_time*1000:.3f}ms")
    print(f"  join: {join_time*1000:.3f}ms")
    print(f"  StringIO: {io_time*1000:.3f}ms")
    print(f"  join vs 拼接: {concat_time/join_time:.1f}x")


# ═══════════════════════════════════════════════
# 7. 内存优化
# ═══════════════════════════════════════════════

def demo_memory_optimization():
    """演示内存优化"""
    print("\n【7. 内存优化】")
    print("-" * 40)
    
    import sys
    
    # 列表 vs 生成器
    print(f"  列表 vs 生成器:")
    
    # 列表
    start = time.perf_counter()
    lst = [i ** 2 for i in range(100000)]
    list_time = time.perf_counter() - start
    list_mem = sys.getsizeof(lst)
    
    # 生成器
    start = time.perf_counter()
    gen = (i ** 2 for i in range(100000))
    gen_time = time.perf_counter() - start
    gen_mem = sys.getsizeof(gen)
    
    print(f"  列表: {list_time*1000:.3f}ms, {list_mem/1024:.1f}KB")
    print(f"  生成器: {gen_time*1000:.3f}ms, {gen_mem/1024:.1f}KB")
    print(f"  内存节省: {list_mem/gen_mem:.0f}x")
    
    # 普通类 vs __slots__
    print(f"\n  普通类 vs __slots__:")
    
    class PointNormal:
        def __init__(self, x, y):
            self.x = x
            self.y = y
    
    class PointSlots:
        __slots__ = ['x', 'y']
        def __init__(self, x, y):
            self.x = x
            self.y = y
    
    # 创建大量实例
    start = time.perf_counter()
    points_normal = [PointNormal(i, i) for i in range(10000)]
    normal_time = time.perf_counter() - start
    normal_mem = sys.getsizeof(points_normal) + sum(
        sys.getsizeof(p.__dict__) for p in points_normal
    )
    
    start = time.perf_counter()
    points_slots = [PointSlots(i, i) for i in range(10000)]
    slots_time = time.perf_counter() - start
    slots_mem = sys.getsizeof(points_slots) + sum(
        sys.getsizeof(getattr(p, '__dict__', {})) for p in points_slots
    )
    
    print(f"  普通类: {normal_time*1000:.3f}ms, ~{normal_mem/1024:.1f}KB")
    print(f"  __slots__: {slots_time*1000:.3f}ms, ~{slots_mem/1024:.1f}KB")


# ═══════════════════════════════════════════════
# 8. 内置函数优化
# ═══════════════════════════════════════════════

def demo_builtin_optimization():
    """演示内置函数优化"""
    print("\n【8. 内置函数优化】")
    print("-" * 40)
    
    data = list(range(100000))
    random.shuffle(data)
    
    # 手动排序 vs 内置排序
    print(f"  排序优化:")
    
    # 内置 sorted
    start = time.perf_counter()
    result = sorted(data)
    builtin_sort_time = time.perf_counter() - start
    
    print(f"  内置 sorted: {builtin_sort_time*1000:.3f}ms")
    
    # map vs 列表推导
    print(f"\n  map vs 列表推导:")
    
    # 列表推导
    start = time.perf_counter()
    result1 = [x ** 2 for x in data[:1000]]
    listcomp_time = time.perf_counter() - start
    
    # map
    start = time.perf_counter()
    result2 = list(map(lambda x: x ** 2, data[:1000]))
    map_time = time.perf_counter() - start
    
    print(f"  列表推导: {listcomp_time*1000:.3f}ms")
    print(f"  map函数: {map_time*1000:.3f}ms")
    
    if listcomp_time < map_time:
        print(f"  列表推导更快: {map_time/listcomp_time:.1f}x")
    else:
        print(f"  map更快: {listcomp_time/map_time:.1f}x")


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    demo_lookup_optimization()
    demo_insert_optimization()
    demo_count_optimization()
    demo_loop_optimization()
    demo_cache_optimization()
    demo_string_optimization()
    demo_memory_optimization()
    demo_builtin_optimization()
    
    print("\n✅ 数据结构与算法优化演示完成!")
