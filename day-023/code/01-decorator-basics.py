#!/usr/bin/env python3
"""
Day 023 — 装饰器入门：基础装饰器、语法糖、wraps

涵盖：
1. 函数是一等公民
2. 闭包与基础装饰器
3. 语法糖 @ 的使用
4. functools.wraps 的应用
5. 装饰器执行时机
6. 常见陷阱与避坑
"""

import functools
import time

print("=" * 60)
print("1. 函数是一等公民 — 装饰器的基础")
print("=" * 60)


def greet(name):
    """向某人问好"""
    return f"Hello, {name}!"


# 函数赋值给变量
say_hello = greet
print(f"greet('Alice')  = {greet('Alice')}")
print(f"say_hello('Alice') = {say_hello('Alice')}")

# 函数作为参数
def call_twice(func, arg):
    return func(arg), func(arg)

print(f"call_twice(greet, 'Bob') = {call_twice(greet, 'Bob')}")

# 函数作为返回值
def make_greeter(lang):
    def greeter(name):
        if lang == "zh":
            return f"你好, {name}!"
        return f"Hello, {name}!"
    return greeter

zh_greet = make_greeter("zh")
en_greet = make_greeter("en")
print(f"zh_greet('小明') = {zh_greet('小明')}")
print(f"en_greet('Alice') = {en_greet('Alice')}")

print()
print("=" * 60)
print("2. 闭包与基础装饰器")
print("=" * 60)


# 最简装饰器
def simple_decorator(func):
    """一个最简单的装饰器——在调用前后添加横线"""
    def wrapper():
        print("—" * 30)
        func()
        print("—" * 30)
    return wrapper


# 手动应用装饰器
def say_hello():
    print("Hello, World!")

say_hello = simple_decorator(say_hello)
print("手动装饰后的调用:")
say_hello()

print()
print("=" * 60)
print("3. 语法糖 @ — 等价于手动装饰")
print("=" * 60)


@simple_decorator
def say_hi():
    print("Hi there!")

print("语法糖 @ 装饰后的调用:")
say_hi()


# 验证装饰器返回的是 wrapper
print(f"\nsay_hi 函数的身份: {say_hi}")
print(f"say_hi.__name__: {say_hi.__name__}")  # wrapper — 不是 say_hi！

print()
print("=" * 60)
print("4. functools.wraps — 保留函数元信息")
print("=" * 60)


def bad_decorator(func):
    """不带 wraps 的装饰器"""
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def good_decorator(func):
    """带 wraps 的装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


@bad_decorator
def add_bad(a, b):
    """将两个数相加"""
    return a + b


@good_decorator
def add_good(a, b):
    """将两个数相加"""
    return a + b


print("不带 wraps:")
print(f"  __name__: {add_bad.__name__}")     # 'wrapper'
print(f"  __doc__:  {add_bad.__doc__}")      # None

print("带 wraps:")
print(f"  __name__: {add_good.__name__}")    # 'add_good'
print(f"  __doc__:  {add_good.__doc__}")     # '将两个数相加'

# wraps 还会在 wrapper 上设置 __wrapped__ 属性
print(f"\nwraps 设置了 __wrapped__: {add_good.__wrapped__}")
print(f"__wrapped__ 就是原始函数: {add_good.__wrapped__ is add_good.__wrapped__}")

print()
print("=" * 60)
print("5. 通用装饰器模板 — 处理任意参数")
print("=" * 60)


def universal_decorator(func):
    """可以装饰任意函数的通用装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """wrapper 文档"""
        print(f"[装饰器] 调用 {func.__name__}({args}, {kwargs})")
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[装饰器] {func.__name__} 返回 {result!r} (耗时 {elapsed:.4f}s)")
        return result
    return wrapper


@universal_decorator
def multiply(x, y):
    """计算两数之积"""
    return x * y


@universal_decorator
def hello(name, greeting="Hello"):
    """向某人打招呼"""
    return f"{greeting}, {name}!"


print("调用 multiply(3, 4):")
result = multiply(3, 4)
print(f"结果: {result}")

print("\n调用 hello('Alice', greeting='Hi'):")
result = hello("Alice", greeting="Hi")
print(f"结果: {result}")

print()
print("=" * 60)
print("6. 装饰器执行时机 — 定义时，而非调用时")
print("=" * 60)


# 定义一个注册表
FUNCTION_REGISTRY = []


def register(func):
    """将函数注册到全局注册表中"""
    print(f"[注册] 注册函数: {func.__name__}")
    FUNCTION_REGISTRY.append(func)
    return func


print("开始定义函数...")

@register
def func_a():
    return "A"

@register
def func_b():
    return "B"

@register
def func_c():
    return "C"

print(f"\n定义完成！注册表中有 {len(FUNCTION_REGISTRY)} 个函数:")
for f in FUNCTION_REGISTRY:
    print(f"  - {f.__name__}")

print("\n现在调用它们...")
for f in FUNCTION_REGISTRY:
    print(f"  {f.__name__}() → {f()}")

print()
print("=" * 60)
print("7. 装饰器顺序 — 装饰与调用的区别")
print("=" * 60)


def decorator_a(func):
    print("  装饰 A 执行")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  A 前置")
        result = func(*args, **kwargs)
        print("  A 后置")
        return result
    return wrapper

def decorator_b(func):
    print("  装饰 B 执行")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  B 前置")
        result = func(*args, **kwargs)
        print("  B 后置")
        return result
    return wrapper


print("定义函数（装饰阶段）:")
@decorator_a
@decorator_b
def target():
    print("  ★ 原始函数执行 ★")

print("\n调用函数（执行阶段）:")
target()

print()
print("=" * 60)
print("8. 常见陷阱与避坑")
print("=" * 60)


# 陷阱：忘记 wraps
print("陷阱 1 — 不加 wraps:")
@bad_decorator
def important_func():
    """这个文档很重要！"""
    pass

print(f"  __name__ = {important_func.__name__}")  # wrapper
print(f"  __doc__ = {important_func.__doc__}")     # None

# 陷阱：返回类型假设
print("\n陷阱 2 — 返回值类型假设:")

def uppercase_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result.upper()  # 假设返回值是字符串
    return wrapper

@uppercase_decorator
def get_greeting():
    return "hello"

print(f"  字符串返回: {get_greeting()}")  # HELLO

# 但如果函数返回非字符串：
@uppercase_decorator
def get_number():
    return 42

try:
    get_number()
except AttributeError as e:
    print(f"  非字符串返回出错: {e}")


print("\n✅ 所有示例执行完成！")
