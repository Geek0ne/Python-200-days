#!/usr/bin/env python3
"""
Day 092 - 代码优化技巧: 实战 - 将慢代码提速 10 倍
完整优化流程演示
"""

import time
import random
from functools import lru_cache
from collections import defaultdict, Counter


# ═══════════════════════════════════════════════
# 1. 原始慢代码
# ═══════════════════════════════════════════════

def slow_version(data):
    """
    原始慢代码 - 有多处性能问题
    """
    result = []
    
    # 问题1: 每次都遍历检查重复
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100:
                if transformed not in result:  # O(n) 查找!
                    result.append(transformed)
    
    # 问题2: 多次遍历
    max_val = max(result)
    min_val = min(result)
    avg_val = sum(result) / len(result) if result else 0
    
    # 问题3: 排序后返回
    return sorted(result)


# ═══════════════════════════════════════════════
# 2. 优化后的代码
# ═══════════════════════════════════════════════

def fast_version(data):
    """
    优化后: 10x+ 提速
    """
    # 优化1: 使用集合去重
    seen = set()
    result = []
    
    # 优化2: 单次遍历
    max_val = float("-inf")
    min_val = float("inf")
    total = 0
    
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100 and transformed not in seen:
                result.append(transformed)
                seen.add(transformed)
                
                # 在遍历中同时计算统计值
                if transformed > max_val:
                    max_val = transformed
                if transformed < min_val:
                    min_val = transformed
                total += transformed
    
    avg_val = total / len(result) if result else 0
    
    # 优化3: 使用内置排序
    return sorted(result)


# ═══════════════════════════════════════════════
# 3. 进一步优化 (使用 defaultdict)
# ═══════════════════════════════════════════════

def fastest_version(data):
    """
    极致优化版本
    """
    # 使用 Counter 计数
    counter = Counter()
    
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100:
                counter[transformed] += 1
    
    # 只取出现过的值
    result = sorted(counter.keys())
    
    # 使用内置函数计算统计
    if result:
        max_val = max(result)
        min_val = min(result)
        avg_val = sum(result) / len(result)
    else:
        max_val = min_val = avg_val = 0
    
    return result


# ═══════════════════════════════════════════════
# 4. 缓存版本
# ═══════════════════════════════════════════════

@lru_cache(maxsize=128)
def cached_transform(item):
    """缓存变换结果"""
    return item ** 2 + item * 3


def cached_version(data):
    """
    使用缓存的版本
    """
    seen = set()
    result = []
    
    for item in data:
        if item % 2 == 0:
            transformed = cached_transform(item)  # 缓存计算结果
            if transformed > 100 and transformed not in seen:
                result.append(transformed)
                seen.add(transformed)
    
    return sorted(result)


# ═══════════════════════════════════════════════
# 5. 测试与对比
# ═══════════════════════════════════════════════

def benchmark(func, data, name, runs=10):
    """性能测试"""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        result = func(data)
        end = time.perf_counter()
        times.append(end - start)
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"  {name:>20}: 平均 {avg_time*1000:>8.3f}ms, "
          f"最快 {min_time*1000:>8.3f}ms, "
          f"最慢 {max_time*1000:>8.3f}ms")
    
    return result, avg_time


def main():
    print("=" * 60)
    print("  Day 092 — 实战: 将慢代码提速 10 倍")
    print("=" * 60)
    
    # 生成测试数据
    random.seed(42)
    test_data = [random.randint(0, 1000) for _ in range(100000)]
    
    print(f"\n  测试数据: {len(test_data)} 个随机整数")
    print(f"  测试轮次: 10 次取平均")
    
    # 性能对比
    print(f"\n【性能对比】")
    print("-" * 60)
    
    _, time_slow = benchmark(slow_version, test_data, "原始慢代码")
    _, time_fast = benchmark(fast_version, test_data, "优化版本")
    _, time_fastest = benchmark(fastest_version, test_data, "极致优化")
    _, time_cached = benchmark(cached_version, test_data, "缓存版本")
    
    # 计算提速比
    print(f"\n【提速效果】")
    print("-" * 60)
    print(f"  优化版本 vs 原始: {time_slow/time_fast:.1f}x 提速")
    print(f"  极致优化 vs 原始: {time_slow/time_fastest:.1f}x 提速")
    print(f"  缓存版本 vs 原始: {time_slow/time_cached:.1f}x 提速")
    
    # 验证结果一致性
    print(f"\n【结果验证】")
    print("-" * 60)
    
    result_slow = slow_version(test_data)
    result_fast = fast_version(test_data)
    result_fastest = fastest_version(test_data)
    result_cached = cached_version(test_data)
    
    print(f"  原始版本结果数: {len(result_slow)}")
    print(f"  优化版本结果数: {len(result_fast)}")
    print(f"  极致优化结果数: {len(result_fastest)}")
    print(f"  缓存版本结果数: {len(result_cached)}")
    
    print(f"\n  结果一致性: {'✅' if result_slow == result_fast == result_fastest == result_cached else '❌'}")
    
    # 优化分析
    print(f"\n【优化分析】")
    print("-" * 60)
    print("""
  原始代码的问题:
  1. 每次都遍历检查重复 → O(n²)
  2. 多次遍历同一数据 → 3n 操作
  3. 使用列表而非集合 → O(n) 查找
  
  优化策略:
  1. 使用集合去重 → O(1) 查找
  2. 单次遍历收集所有信息 → n 操作
  3. 使用 Counter/默认字典 → O(1) 插入
  
  关键教训:
  • 数据结构选择是最重要的优化
  • 减少遍历次数可以显著提速
  • 使用内置函数通常比手动实现更快
""")
    
    # 不同数据规模对比
    print(f"\n【不同数据规模对比】")
    print("-" * 60)
    
    sizes = [10000, 50000, 100000, 500000]
    
    for size in sizes:
        data = [random.randint(0, 1000) for _ in range(size)]
        
        start = time.perf_counter()
        slow_version(data)
        time_s = time.perf_counter() - start
        
        start = time.perf_counter()
        fast_version(data)
        time_f = time.perf_counter() - start
        
        speedup = time_s / time_f
        print(f"  规模 {size:>7}: 慢 {time_s*1000:>8.2f}ms, "
              f"快 {time_f*1000:>8.2f}ms, "
              f"提速 {speedup:.1f}x")


if __name__ == "__main__":
    main()
