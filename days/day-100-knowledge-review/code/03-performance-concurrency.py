"""
Day 100 - 知识体系梳理：性能与并发综合示例 3
展示并发编程 + 性能优化在实际场景中的应用
"""

import time
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
from typing import List, Dict
import sys


# ============================================================
# 概念 1: GIL 的理解与绕过（Day 54, 55, 58）
# ============================================================

def cpu_bound_task(n: int) -> int:
    """CPU 密集型任务 - 计算大量数字"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def io_bound_task(seconds: float) -> str:
    """IO 密集型任务 - 模拟网络请求"""
    time.sleep(seconds)
    return f"完成 {seconds}s 任务"


# ============================================================
# 概念 2: 并发模型对比（Day 58）
# ============================================================

@dataclass
class BenchmarkResult:
    """性能基准测试结果"""
    model: str
    task_count: int
    total_time: float
    throughput: float  # tasks/second
    
    def __str__(self):
        return f"{self.model}: {self.total_time:.2f}s ({self.throughput:.1f} tasks/s)"


def benchmark_sequential(tasks: list, task_func) -> float:
    """顺序执行基准"""
    start = time.perf_counter()
    results = [task_func(t) for t in tasks]
    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_threading(tasks: list, task_func, max_workers: int = 4) -> float:
    """多线程执行基准"""
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(task_func, tasks))
    elapsed = time.perf_counter() - start
    return elapsed


def benchmark_multiprocessing(tasks: list, task_func, max_workers: int = 4) -> float:
    """多进程执行基准"""
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(task_func, tasks))
    elapsed = time.perf_counter() - start
    return elapsed


async def benchmark_async(tasks: list, task_func) -> float:
    """asyncio 执行基准"""
    start = time.perf_counter()
    
    async def async_wrapper(t):
        return task_func(t)
    
    results = await asyncio.gather(*[async_wrapper(t) for t in tasks])
    elapsed = time.perf_counter() - start
    return elapsed


# ============================================================
# 概念 3: 性能剖析实战（Day 91）
# ============================================================

def profile_with_timing(func, *args, **kwargs):
    """简单性能剖析"""
    import cProfile
    import pstats
    import io
    
    pr = cProfile.Profile()
    pr.enable()
    result = func(*args, **kwargs)
    pr.disable()
    
    # 格式化输出
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(10)
    
    print(s.getvalue())
    return result


# ============================================================
# 概念 4: 内存优化（Day 51-53, 92）
# ============================================================

class MemoryEfficientDataProcessor:
    """内存高效的数据处理器 - 使用生成器避免内存爆炸"""
    
    @staticmethod
    def inefficient_approach(data_size: int = 1_000_000) -> int:
        """低效方式：创建完整列表"""
        # 这会占用大量内存
        data = [i ** 2 for i in range(data_size)]
        return sum(data)
    
    @staticmethod
    def efficient_approach(data_size: int = 1_000_000) -> int:
        """高效方式：使用生成器"""
        # 生成器不会创建完整列表，内存占用极低
        data = (i ** 2 for i in range(data_size))
        return sum(data)
    
    @staticmethod
    def compare_memory():
        """对比内存使用"""
        import tracemalloc
        
        # 测试列表方式
        tracemalloc.start()
        MemoryEfficientDataProcessor.inefficient_approach(1_000_000)
        current, peak_list = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # 测试生成器方式
        tracemalloc.start()
        MemoryEfficientDataProcessor.efficient_approach(1_000_000)
        current, peak_gen = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return peak_list, peak_gen


# ============================================================
# 综合实战：并发数据处理管道
# ============================================================

def run_concurrent_demo():
    """并发处理综合演示"""
    
    print("=" * 60)
    print("🎓 Day 100 - 并发与性能综合示例")
    print("=" * 60)
    
    # 1. 并发模型对比（IO 密集型）
    print("\n📊 并发模型对比 (IO 密集型任务)")
    print("-" * 40)
    
    io_tasks = [0.1] * 8  # 8 个 100ms 的 IO 任务
    
    # 顺序执行
    t1 = benchmark_sequential(io_tasks, io_bound_task)
    print(f"  顺序执行:   {t1:.2f}s")
    
    # 多线程
    t2 = benchmark_threading(io_tasks, io_bound_task, max_workers=4)
    print(f"  多线程:     {t2:.2f}s (加速比: {t1/t2:.1f}x)")
    
    # asyncio
    t3 = asyncio.get_event_loop().run_until_complete(
        benchmark_async(io_tasks, io_bound_task)
    )
    print(f"  asyncio:    {t3:.2f}s (加速比: {t1/t3:.1f}x)")
    
    # 2. GIL 影响演示（CPU 密集型）
    print("\n📊 GIL 影响演示 (CPU 密集型任务)")
    print("-" * 40)
    
    cpu_tasks = [100_000] * 4  # 4 个 CPU 密集型任务
    
    t1 = benchmark_sequential(cpu_tasks, cpu_bound_task)
    print(f"  顺序执行:   {t1:.2f}s")
    
    t2 = benchmark_threading(cpu_tasks, cpu_bound_task, max_workers=4)
    print(f"  多线程:     {t2:.2f}s (加速比: {t1/t2:.1f}x) ← GIL 限制！")
    
    t3 = benchmark_multiprocessing(cpu_tasks, cpu_bound_task, max_workers=4)
    print(f"  多进程:     {t3:.2f}s (加速比: {t1/t3:.1f}x) ← 真正并行！")
    
    # 3. 内存优化对比
    print("\n📊 内存优化对比")
    print("-" * 40)
    
    peak_list, peak_gen = MemoryEfficientDataProcessor.compare_memory()
    print(f"  列表方式峰值内存: {peak_list / 1024 / 1024:.2f} MB")
    print(f"  生成器峰值内存:   {peak_gen / 1024 / 1024:.4f} MB")
    print(f"  内存节省: {peak_list / max(peak_gen, 1):.0f}x")
    
    # 4. 性能剖析示例
    print("\n📊 性能剖析示例")
    print("-" * 40)
    
    def sample_work():
        """示例工作函数"""
        total = 0
        for i in range(100_000):
            total += i ** 2
        return total
    
    print("  执行性能剖析...")
    result = profile_with_timing(sample_work)
    print(f"  结果: {result}")
    
    # 5. 选择指南
    print("\n📋 并发模型选择指南")
    print("-" * 40)
    print("  IO 密集型 (网络/文件):")
    print("    → asyncio (单线程高并发)")
    print("    → 多线程 (简单场景)")
    print()
    print("  CPU 密集型 (计算/加密):")
    print("    → 多进程 (绕过 GIL)")
    print("    → C 扩展 (最高性能)")
    print()
    print("  混合型:")
    print("    → asyncio + ProcessPoolExecutor")


if __name__ == "__main__":
    run_concurrent_demo()
