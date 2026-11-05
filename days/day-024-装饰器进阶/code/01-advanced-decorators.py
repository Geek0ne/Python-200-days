#!/usr/bin/env python3
"""
Day 024 — 装饰器进阶：参数装饰器与类装饰器

涵盖：
1. 带参数装饰器（三层嵌套）
2. 可选的参数装饰器（@log 和 @log(level=...)）
3. 类装饰器（__call__ 方法）
4. 带参数的类装饰器
5. 类装饰器 vs 函数装饰器对比
"""

import functools
import time


print("=" * 60)
print("1. 带参数装饰器 — 三层嵌套结构")
print("=" * 60)


def repeat(n):
    """重复执行被装饰函数 n 次

    三层结构：
    repeat(n)         → 第 1 层：接收参数
      → decorator(func)  → 第 2 层：接收函数
        → wrapper()       → 第 3 层：接收调用参数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(n):
                print(f"  [{i+1}/{n}] ", end="")
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


@repeat(3)
def greet(name):
    print(f"Hello, {name}!")


print("调用 greet('Alice'):")
greet("Alice")

print()
print("手动等价形式:")
say_hi = repeat(2)(lambda: print("Hi!"))
say_hi()


print()
print("=" * 60)
print("2. 可选参数装饰器 — @log 和 @log(level=...) 都支持")
print("=" * 60)


def log(func=None, *, level="INFO"):
    """智能装饰器，支持两种调用方式：
    @log           — 无参数
    @log(level="DEBUG")  — 带参数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[{level}] 调用 {func.__name__}(...{args}, {kwargs})")
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            print(f"[{level}] {func.__name__} → {result!r} ({elapsed:.3f}s)")
            return result
        return wrapper

    # 核心技巧：如果 func 被直接传入（无参数调用），直接装饰
    if func is not None:
        return decorator(func)
    return decorator


@log
def foo():
    """无参数日志装饰器"""
    return "foo 的结果"


@log(level="DEBUG")
def bar():
    """带参数日志装饰器"""
    return "bar 的结果"


@log(level="WARNING")
def add(a, b):
    return a + b


print("调用 foo() — 使用 @log:")
foo()

print("\n调用 bar() — 使用 @log(level='DEBUG'):")
bar()

print("\n调用 add(10, 20) — 使用 @log(level='WARNING'):")
add(10, 20)


print()
print("=" * 60)
print("3. 类装饰器 — 使用 __call__ 方法")
print("=" * 60)


class CallCounter:
    """类装饰器：统计函数调用次数"""

    def __init__(self, func):
        """初始化：接收被装饰的函数"""
        self.func = func
        self.count = 0
        # 手动复制函数元信息
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        """调用时执行"""
        self.count += 1
        print(f"[调用 #{self.count}] {self.func.__name__}")
        return self.func(*args, **kwargs)


@CallCounter
def say_hello(name):
    """类装饰器测试函数"""
    return f"Hello, {name}!"


print("调用 say_hello('Alice'):")
result = say_hello("Alice")
print(f"  → {result}")

print("\n再次调用:")
result = say_hello("Bob")
print(f"  → {result}")

print("\n第三次调用:")
result = say_hello("Charlie")
print(f"  → {result}")

print(f"\n总调用次数: {say_hello.count}")
print(f"函数名称: {say_hello.__name__}")
print(f"函数文档: {say_hello.__doc__}")
print(f"类型: {type(say_hello)}")


print()
print("=" * 60)
print("4. 带参数的类装饰器")
print("=" * 60)


class Timed:
    """带参数的类装饰器：计时

    用法：
    @Timed           — 默认毫秒
    @Timed(unit="s") — 指定单位
    """

    def __init__(self, unit="ms", precision=3):
        self.unit = unit
        self.precision = precision
        self.unit_names = {"s": "秒", "ms": "毫秒", "us": "微秒"}
        self.unit_factors = {"s": 1, "ms": 1000, "us": 1_000_000}

    def __call__(self, func):
        """接收被装饰的函数"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            converted = elapsed * self.unit_factors[self.unit]
            print(f"[⏱] {func.__name__} 耗时: {converted:.{self.precision}f} "
                  f"{self.unit_names[self.unit]}")
            return result
        return wrapper


@Timed(unit="ms", precision=2)
def quick_compute(n):
    """快速计算"""
    time.sleep(n / 1000)
    return n * 2


@Timed(unit="s", precision=4)
def slow_compute(n):
    """慢速计算"""
    time.sleep(n)
    return n ** 2


print("调用 quick_compute(50):")
quick_compute(50)

print("\n调用 slow_compute(0.3):")
slow_compute(0.3)


print()
print("=" * 60)
print("5. 类装饰器 vs 函数装饰器对比")
print("=" * 60)


# 函数装饰器实现计数器
def func_counter(func):
    """函数装饰器：计数器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.count += 1
        return func(*args, **kwargs)
    wrapper.count = 0
    return wrapper


# 类装饰器实现计数器
class ClassCounter:
    """类装饰器：计数器"""

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self.func(*args, **kwargs)


@func_counter
def func_approach():
    return "函数装饰器"


@ClassCounter
def class_approach():
    return "类装饰器"


print("函数装饰器调用 3 次:")
for _ in range(3):
    func_approach()
print(f"  计数: {func_approach.count}")

print("\n类装饰器调用 3 次:")
for _ in range(3):
    class_approach()
print(f"  计数: {class_approach.count}")


print("\n对比:")
print(f"  函数装饰器类型: {type(func_approach)}")  # function
print(f"  类装饰器类型:   {type(class_approach)}")  # ClassCounter
print(f"  函数装饰器__name__: {func_approach.__name__}")
print(f"  类装饰器__name__:   {class_approach.__name__}")


print()
print("=" * 60)
print("6. 带状态的类装饰器 — 更复杂的场景")
print("=" * 60)


class Profiler:
    """性能分析器：记录每次调用的时间，提供统计报告"""

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.times = []

    def __call__(self, *args, **kwargs):
        start = time.perf_counter()
        result = self.func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        self.times.append(elapsed)
        return result

    def stats(self):
        """输出统计信息"""
        if not self.times:
            print(f"  [Profiler] {self.func.__name__}: 暂无数据")
            return
        avg = sum(self.times) / len(self.times)
        print(f"  [Profiler] {self.func.__name__} 统计:")
        print(f"    调用次数: {len(self.times)}")
        print(f"    总耗时:   {sum(self.times):.4f}s")
        print(f"    平均耗时: {avg:.4f}s")
        print(f"    最短耗时: {min(self.times):.4f}s")
        print(f"    最长耗时: {max(self.times):.4f}s")

    def reset(self):
        """重置统计数据"""
        self.times.clear()


@Profiler
def worker(n):
    """模拟工作"""
    time.sleep(n * 0.01)
    return sum(range(n))


import random

for _ in range(5):
    worker(random.randint(10, 100))

worker.stats()

print("\n重置后:")
worker.reset()
worker(10)
worker.stats()


print("\n✅ 所有装饰器进阶示例完成！")
