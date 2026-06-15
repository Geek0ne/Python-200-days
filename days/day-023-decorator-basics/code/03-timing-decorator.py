#!/usr/bin/env python3
"""
Day 023 — 计时装饰器实战

涵盖：
1. 基础计时装饰器
2. 可配置计时器（单位、精度）
3. 平均耗时统计
4. 函数调用计数器
5. 性能采样与报告
"""

import functools
import time
import math
import random
from collections import defaultdict


# ============================================================
# 1. 基础计时装饰器
# ============================================================

def timer(func):
    """基础计时装饰器——测量函数执行时间"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"[⏱] {func.__name__} 耗时: {elapsed:.6f} 秒")
        return result
    return wrapper


@timer
def slow_function():
    """一个慢函数"""
    time.sleep(0.5)
    return "完成"


print("=" * 60)
print("1. 基础计时装饰器")
print("=" * 60)
result = slow_function()
print(f"结果: {result}")


# ============================================================
# 2. 可配置计时装饰器
# ============================================================

def timer_with_unit(unit="s", precision=4):
    """可配置的计时装饰器

    参数:
        unit: 时间单位 ('s' 秒, 'ms' 毫秒, 'us' 微秒)
        precision: 小数位数
    """
    unit_map = {
        "s": 1,
        "ms": 1000,
        "us": 1_000_000,
    }
    unit_names = {"s": "秒", "ms": "毫秒", "us": "微秒"}

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_native = time.perf_counter() - start
            converted = elapsed_native * unit_map[unit]
            print(f"[⏱] {func.__name__} 耗时: {converted:.{precision}f} {unit_names[unit]}")
            return result
        return wrapper
    return decorator


@timer_with_unit(unit="ms", precision=2)
def quick_task(n):
    """一个快速任务"""
    time.sleep(n / 1000)


print("\n" + "=" * 60)
print("2. 可配置计时装饰器")
print("=" * 60)
quick_task(100)   # 约 100ms
quick_task(250)   # 约 250ms


# ============================================================
# 3. 统计计时装饰器（多次调用取均值）
# ============================================================

def stats_timer(max_samples=100):
    """统计计时装饰器——记录多次调用的耗时统计

    收集每次调用的耗时，提供平均值、最小值、最大值等信息
    """
    stats = {"min": float("inf"), "max": 0, "total": 0, "count": 0}

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            # 更新统计
            stats["count"] += 1
            stats["total"] += elapsed
            stats["min"] = min(stats["min"], elapsed)
            stats["max"] = max(stats["max"], elapsed)
            stats["last"] = elapsed

            return result

        # 在 wrapper 上挂载统计方法
        def print_stats():
            if stats["count"] == 0:
                print(f"  [📊] {func.__name__}: 暂无调用记录")
                return
            avg = stats["total"] / stats["count"]
            print(f"  [📊] {func.__name__} 调用统计:")
            print(f"        调用次数: {stats['count']}")
            print(f"        总耗时:   {stats['total']:.4f}s")
            print(f"        平均耗时: {avg:.4f}s")
            print(f"        最短耗时: {stats['min']:.4f}s")
            print(f"        最长耗时: {stats['max']:.4f}s")
            print(f"        最近耗时: {stats.get('last', 0):.4f}s")

        wrapper.print_stats = print_stats
        return wrapper
    return decorator


@stats_timer()
def compute_square(n):
    """计算平方并模拟随机延迟"""
    time.sleep(random.uniform(0.001, 0.05))
    return n * n


print("\n" + "=" * 60)
print("3. 统计计时装饰器")
print("=" * 60)

for i in range(10):
    compute_square(i)

compute_square.print_stats()


# ============================================================
# 4. 函数调用计数器装饰器
# ============================================================

def count_calls(func):
    """统计函数被调用的次数"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.call_count += 1
        return func(*args, **kwargs)

    wrapper.call_count = 0

    def reset():
        wrapper.call_count = 0

    wrapper.reset = reset
    return wrapper


@count_calls
def say(msg):
    """说点什么"""
    return f"我说: {msg}"


print("\n" + "=" * 60)
print("4. 函数调用计数器")
print("=" * 60)

say("你好")
say("世界")
say("Hello")

print(f"say() 被调用了 {say.call_count} 次")

say.reset()
print(f"重置后: {say.call_count} 次")


# ============================================================
# 5. 综合计时 + 计数器
# ============================================================

def timed_counter(func):
    """计时 + 计数的复合装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.count += 1
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        wrapper.total_time += elapsed
        print(f"  [{wrapper.count}] {func.__name__} 耗时 {elapsed:.4f}s")
        return result

    wrapper.count = 0
    wrapper.total_time = 0.0

    def report():
        avg = wrapper.total_time / wrapper.count if wrapper.count > 0 else 0
        print(f"\n📋 {func.__name__} 执行报告:")
        print(f"  调用次数: {wrapper.count}")
        print(f"  总耗时:   {wrapper.total_time:.4f}s")
        print(f"  平均耗时: {avg:.4f}s")

    wrapper.report = report
    return wrapper


@timed_counter
def heavy_compute(n):
    """模拟重计算"""
    time.sleep(0.05)
    return sum(math.sqrt(i) for i in range(n))


print("\n" + "=" * 60)
print("5. 综合计时 + 计数")
print("=" * 60)

for n in [100, 200, 500, 1000]:
    heavy_compute(n)

heavy_compute.report()


# ============================================================
# 6. 性能采样装饰器
# ============================================================

def sample_timer(sample_interval=0.1):
    """性能采样计时器——在函数执行期间定期采样

    适用于分析长时间运行的函数的性能特征。
    每隔 sample_interval 秒采样一次函数名。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            result_type = type(result).__name__
            result_len = len(result) if hasattr(result, '__len__') else None

            wrapper.samples.append({
                "args": args,
                "kwargs": kwargs,
                "duration": elapsed,
                "return_type": result_type,
                "return_len": result_len,
            })
            return result

        wrapper.samples = []
        return wrapper
    return decorator


@sample_timer()
def batch_process(items):
    """批量处理数据"""
    time.sleep(len(items) * 0.01)
    return [item * 2 for item in items]


print("\n" + "=" * 60)
print("6. 性能采样装饰器")
print("=" * 60)

batch_process([1, 2, 3])
batch_process(list(range(50)))
batch_process(list(range(100)))

print(f"采样记录: {len(batch_process.samples)} 条")
for i, sample in enumerate(batch_process.samples):
    ret_len = sample.get('return_len')
    ret_len_str = f"长度{ret_len}" if ret_len is not None else sample['return_type']
    print(f"  采样 {i+1}: 参数长度={len(sample['args'][0])}, "
          f"耗时={sample['duration']:.4f}s, "
          f"返回={sample['return_type']}({ret_len_str})")


# ============================================================
# 7. 实战：函数超时监控
# ============================================================

class TimeoutError(Exception):
    """函数执行超时异常"""
    pass


def timeout(limit_seconds):
    """超时监控装饰器——当函数执行超过指定时间时打印警告"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start

            if elapsed > limit_seconds:
                print(f"⚠️ [{func.__name__}] 执行时间 {elapsed:.2f}s "
                      f"超过限制 {limit_seconds}s")
            return result
        return wrapper
    return decorator


@timeout(limit_seconds=0.3)
def fast_task():
    time.sleep(0.1)
    return "快速完成"

@timeout(limit_seconds=0.3)
def slow_task():
    time.sleep(0.5)
    return "慢速完成"


print("\n" + "=" * 60)
print("7. 函数超时监控")
print("=" * 60)

fast_task()
slow_task()  # 触发超时警告


print("\n✅ 所有计时装饰器示例完成！")
