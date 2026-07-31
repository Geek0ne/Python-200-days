#!/usr/bin/env python3
"""
Day 091 - 性能剖析: cProfile 基础用法
演示函数级性能剖析
"""

import cProfile
import pstats
from io import StringIO
import time
import random


# ═══════════════════════════════════════════════
# 1. 待剖析的函数
# ═══════════════════════════════════════════════

def bubble_sort(arr):
    """冒泡排序 - O(n²)"""
    arr = arr.copy()
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr


def quick_sort(arr):
    """快速排序 - O(n log n)"""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)


def find_duplicates(arr):
    """查找重复元素"""
    seen = set()
    duplicates = []
    for item in arr:
        if item in seen:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def process_data(data):
    """数据处理函数"""
    result = []
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100:
                result.append(transformed)
    return result


# ═══════════════════════════════════════════════
# 2. cProfile 基本用法
# ═══════════════════════════════════════════════

def demo_basic_profiling():
    """演示 cProfile 基本用法"""
    print("=" * 60)
    print("  Day 091 — cProfile 基础用法演示")
    print("=" * 60)
    
    # 生成测试数据
    random.seed(42)
    test_data = [random.randint(0, 1000) for _ in range(1000)]
    
    # 方法1: cProfile.run()
    print("\n【1. cProfile.run() 基本用法】")
    print("-" * 40)
    
    code = """
result = process_data(test_data)
duplicates = find_duplicates(test_data)
"""
    print("  分析代码:")
    print("  process_data(test_data)")
    print("  find_duplicates(test_data)")
    print()
    
    cProfile.run(code, sort='cumtime')
    
    # 方法2: 使用 Profile 对象
    print("\n【2. 使用 Profile 对象】")
    print("-" * 40)
    
    profiler = cProfile.Profile()
    profiler.enable()
    
    # 执行操作
    result1 = process_data(test_data)
    result2 = find_duplicates(test_data)
    sorted_data = quick_sort(test_data[:200])  # 只排序一部分
    
    profiler.disable()
    
    # 获取统计信息
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('cumulative')
    ps.print_stats(15)
    print(s.getvalue())
    
    # 按不同方式排序
    print("\n【3. 按自身时间排序 (tottime)】")
    print("-" * 40)
    
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('tottime')
    ps.print_stats(10)
    print(s.getvalue())
    
    print("\n【4. 按调用次数排序 (ncalls)】")
    print("-" * 40)
    
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s)
    ps.sort_stats('ncalls')
    ps.print_stats(10)
    print(s.getvalue())
    
    # 结果分析
    print("\n【5. 性能分析结果】")
    print("-" * 40)
    print(f"  process_data 结果数: {len(result1)}")
    print(f"  find_duplicates 结果数: {len(result2)}")
    print(f"  quick_sort 结果数: {len(sorted_data)}")


# ═══════════════════════════════════════════════
# 3. 对比排序算法性能
# ═══════════════════════════════════════════════

def demo_sorting_comparison():
    """对比不同排序算法的性能"""
    print("\n【6. 排序算法性能对比】")
    print("-" * 40)
    
    import timeit
    
    random.seed(42)
    test_data = [random.randint(0, 10000) for _ in range(500)]
    
    # 测试冒泡排序
    bubble_time = timeit.timeit(
        lambda: bubble_sort(test_data),
        number=10
    )
    
    # 测试快速排序
    quick_time = timeit.timeit(
        lambda: quick_sort(test_data),
        number=10
    )
    
    # 测试内置排序
    builtin_time = timeit.timeit(
        lambda: sorted(test_data),
        number=10
    )
    
    print(f"  冒泡排序: {bubble_time*100:.2f}ms (10次)")
    print(f"  快速排序: {quick_time*100:.2f}ms (10次)")
    print(f"  内置排序: {builtin_time*100:.2f}ms (10次)")
    print()
    print(f"  快速排序 vs 冒泡排序: 快 {bubble_time/quick_time:.1f} 倍")
    print(f"  内置排序 vs 快速排序: 快 {quick_time/builtin_time:.1f} 倍")


# ═══════════════════════════════════════════════
# 4. 剖析装饰器
# ═══════════════════════════════════════════════

def profile_decorator(func):
    """性能剖析装饰器"""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        s = StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.sort_stats('cumulative')
        ps.print_stats(10)
        print(f"\n📊 {func.__name__} 性能报告:")
        print(s.getvalue())
        
        return result
    return wrapper


@profile_decorator
def slow_function(n):
    """故意写慢的函数"""
    result = []
    for i in range(n):
        result.append(i ** 2)
    return result


def demo_profile_decorator():
    """演示装饰器用法"""
    print("\n【7. 性能剖析装饰器】")
    print("-" * 40)
    
    slow_function(10000)


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    demo_basic_profiling()
    demo_sorting_comparison()
    demo_profile_decorator()
    
    print("\n✅ cProfile 基础用法演示完成!")
