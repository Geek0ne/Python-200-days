#!/usr/bin/env python3
"""
Day 091 - 性能剖析: line_profiler 与 memory_profiler
行级剖析与内存剖析
"""

import time
import random
import sys


# ═══════════════════════════════════════════════
# 1. line_profiler 使用方法
# ═══════════════════════════════════════════════

def data_processing_pipeline(data):
    """
    数据处理管线 - 需要行级剖析的函数
    
    使用方法:
    1. 安装: pip install line_profiler
    2. 添加 @profile 装饰器 (不需要导入)
    3. 运行: kernprof -l -v script.py
    """
    # 步骤1: 数据清洗
    cleaned = [x for x in data if x is not None and x > 0]
    
    # 步骤2: 数据转换
    transformed = []
    for item in cleaned:
        value = item ** 2 + item * 3
        transformed.append(value)
    
    # 步骤3: 数据过滤
    filtered = [x for x in transformed if x > 100]
    
    # 步骤4: 数据聚合
    total = sum(filtered)
    count = len(filtered)
    average = total / count if count > 0 else 0
    
    return {
        "total": total,
        "count": count,
        "average": average,
        "max": max(filtered) if filtered else 0,
        "min": min(filtered) if filtered else 0,
    }


def simulate_line_profiler():
    """模拟 line_profiler 输出"""
    print("=" * 60)
    print("  Day 091 — line_profiler 使用方法演示")
    print("=" * 60)
    
    print("\n【1. line_profiler 使用步骤】")
    print("-" * 40)
    print("""
  1. 安装: pip install line_profiler
  
  2. 在函数上添加装饰器 (不需要导入):
     @profile
     def my_function():
         pass
  
  3. 运行剖析:
     kernprof -l -v my_script.py
  
  4. 查看输出:
     Line #      Hits         Time  Per Hit   % Time  Line Contents
     ===============================================================
           3         1        0.1      0.1      1.2      a = [1, 2, 3]
           4         1      200.3    200.3     78.5      b = [x * 2 for x in a]
           5         1       55.0     55.0     21.5      return sum(b)
""")
    
    print("【2. 行级剖析输出解读】")
    print("-" * 40)
    
    # 模拟剖析输出
    print("  Line #      Hits         Time  Per Hit   % Time  Line Contents")
    print("  " + "=" * 60)
    
    # 模拟数据
    lines = [
        ("  3", "1", "0.1", "0.1", "0.1", "def data_processing_pipeline(data):"),
        ("  5", "1", "15.2", "15.2", "2.1", "cleaned = [x for x in data if x is not None]"),
        ("  8", "1000", "450.3", "0.5", "62.5", "for item in cleaned:"),
        ("  9", "1000", "180.1", "0.2", "24.7", "value = item ** 2 + item * 3"),
        (" 10", "1000", "25.5", "0.0", "3.5", "transformed.append(value)"),
        (" 13", "1", "12.8", "12.8", "1.8", "filtered = [x for x in transformed if x > 100]"),
        (" 16", "1", "8.2", "8.2", "1.1", "total = sum(filtered)"),
        (" 17", "1", "5.5", "5.5", "0.8", "count = len(filtered)"),
        (" 18", "1", "3.1", "3.1", "0.4", "average = total / count if count > 0 else 0"),
    ]
    
    for line in lines:
        print("  ".join(line))
    
    print()
    print("  分析:")
    print("  • 第8行: 循环占 62.5% 时间 → 主要瓶颈")
    print("  • 第9行: 计算占 24.7% 时间 → 可优化")
    print("  • 第5行: 列表推导占 2.1% → 合理")


# ═══════════════════════════════════════════════
# 2. memory_profiler 使用方法
# ═══════════════════════════════════════════════

def simulate_memory_profiler():
    """模拟 memory_profiler 输出"""
    print("\n【3. memory_profiler 使用方法】")
    print("-" * 40)
    print("""
  1. 安装: pip install memory_profiler
  
  2. 在函数上添加装饰器:
     from memory_profiler import profile
     
     @profile
     def my_function():
         pass
  
  3. 运行剖析:
     python -m memory_profiler my_script.py
  
  4. 查看输出:
     Line #    Mem usage    Increment   Line Contents
     =================================================
           3     38.5 MiB     38.5 MiB   @profile
           4                             def my_function():
           5     38.5 MiB      0.0 MiB       a = [i for i in range(10000)]
           6     38.5 MiB      0.0 MiB       b = [i ** 2 for i in range(10000)]
           7     38.5 MiB      0.0 MiB       return a, b
""")
    
    print("【4. 内存剖析输出解读】")
    print("-" * 40)
    
    # 模拟内存剖析输出
    print("  Line #    Mem usage    Increment   Line Contents")
    print("  " + "=" * 55)
    
    memory_lines = [
        ("  3", "38.5 MiB", "38.5 MiB", "@profile"),
        ("  4", "38.5 MiB", "0.0 MiB", "def analyze_memory():"),
        ("  6", "38.5 MiB", "0.0 MiB", "small_list = [1, 2, 3]"),
        ("  7", "38.5 MiB", "0.0 MiB", "small_dict = {'a': 1, 'b': 2}"),
        ("  9", "42.3 MiB", "3.8 MiB", "large_list = [i for i in range(100000)]"),
        (" 10", "46.1 MiB", "3.8 MiB", "large_dict = {i: i**2 for i in range(100000)}"),
        (" 12", "46.1 MiB", "0.0 MiB", "result = sum(large_list)"),
        (" 13", "46.1 MiB", "0.0 MiB", "del large_list"),
        (" 14", "42.3 MiB", "-3.8 MiB", "del large_dict"),
    ]
    
    for line in memory_lines:
        print("  ".join(line))
    
    print()
    print("  分析:")
    print("  • 第9行: 创建大列表增加 3.8 MiB")
    print("  • 第10行: 创建大字典增加 3.8 MiB")
    print("  • 第13-14行: 删除后内存释放")


# ═══════════════════════════════════════════════
# 3. 内存泄漏检测示例
# ═══════════════════════════════════════════════

class MemoryLeakSimulator:
    """模拟内存泄漏场景"""
    
    def __init__(self):
        self.cache = {}
        self.leaked_data = []
    
    def leaky_function(self, key, value):
        """有内存泄漏的函数"""
        # 问题: 缓存无限增长
        self.cache[key] = value  # 永远不清理!
        
        # 问题: 列表无限增长
        self.leaked_data.append(value)
        
        return self.cache.get(key)
    
    def fixed_function(self, key, value):
        """修复后的函数"""
        # 使用 LRU 缓存，限制大小
        if len(self.cache) > 1000:
            # 删除最旧的条目
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = value
        
        # 定期清理
        if len(self.leaked_data) > 10000:
            self.leaked_data = self.leaked_data[-1000:]  # 只保留最近的
        
        return self.cache.get(key)


def simulate_leak_detection():
    """演示内存泄漏检测"""
    print("\n【5. 内存泄漏检测示例】")
    print("-" * 40)
    
    simulator = MemoryLeakSimulator()
    
    print("  模拟内存泄漏场景:")
    print("  • 缓存无限增长")
    print("  • 列表无限增长")
    print()
    
    # 模拟泄漏
    print("  泄漏函数调用 1000 次:")
    for i in range(1000):
        simulator.leaky_function(f"key_{i}", i)
    
    print(f"  缓存大小: {len(simulator.cache)} 条")
    print(f"  列表大小: {len(simulator.leaked_data)} 条")
    
    # 估算内存占用
    cache_size = sys.getsizeof(simulator.cache) + sum(
        sys.getsizeof(k) + sys.getsizeof(v)
        for k, v in simulator.cache.items()
    )
    list_size = sys.getsizeof(simulator.leaked_data)
    
    print(f"  缓存内存: ~{cache_size / 1024:.1f} KB")
    print(f"  列表内存: ~{list_size / 1024:.1f} KB")


# ═══════════════════════════════════════════════
# 4. timeit 使用方法
# ═══════════════════════════════════════════════

def demo_timeit():
    """演示 timeit 使用方法"""
    print("\n【6. timeit 精确计时】")
    print("-" * 40)
    
    import timeit
    
    # 基本用法
    time1 = timeit.timeit('sum(range(1000))', number=10000)
    print(f"  sum(range(1000)) × 10000: {time1*1000:.2f}ms")
    
    # 对比不同方法
    methods = {
        "列表推导": "[x**2 for x in range(1000)]",
        "map函数": "list(map(lambda x: x**2, range(1000)))",
        "生成器": "list(x**2 for x in range(1000))",
    }
    
    print(f"\n  计算 1000 个数的平方:")
    for name, code in methods.items():
        time = timeit.timeit(code, number=10000)
        print(f"  {name:>8}: {time*1000:.2f}ms (10000次)")
    
    # 使用 stmt 和 setup 参数
    print(f"\n  使用 stmt/setup 参数:")
    time = timeit.timeit(
        stmt="process_list(data)",
        setup="data = list(range(1000)); def process_list(d): return [x**2 for x in d]",
        number=10000
    )
    print(f"  process_list: {time*1000:.2f}ms")


# ═══════════════════════════════════════════════
# 5. 上下文管理器计时
# ═══════════════════════════════════════════════

from contextlib import contextmanager

@contextmanager
def timer(name="操作"):
    """精确计时上下文管理器"""
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    print(f"  ⏱️ {name}: {(end - start)*1000:.3f}ms")


def demo_timer_context():
    """演示上下文管理器计时"""
    print("\n【7. 上下文管理器计时】")
    print("-" * 40)
    
    with timer("列表推导"):
        result1 = [x ** 2 for x in range(100000)]
    
    with timer("map函数"):
        result2 = list(map(lambda x: x ** 2, range(100000)))
    
    with timer("内置排序"):
        data = list(range(100000))
        random.shuffle(data)
        sorted_data = sorted(data)


# ═══════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    simulate_line_profiler()
    simulate_memory_profiler()
    simulate_leak_detection()
    demo_timeit()
    demo_timer_context()
    
    print("\n✅ line_profiler 与 memory_profiler 演示完成!")
