#!/usr/bin/env python3
"""
03-higher-order-functions.py — 高阶函数应用实战

涵盖：
  - 闭包（Closure）
  - 装饰器（Decorator）
  - 函数工厂
  - 偏函数（Partial Application）
  - 柯里化（Currying）
  - 组合（Composition）
"""

from functools import wraps, partial, lru_cache
import time

# ============================================================
# 1. 闭包（Closure）
# ============================================================
print("=" * 60)
print("1. 闭包（Closure）")
print("=" * 60)


def make_counter():
    """创建计数器闭包"""
    count = [0]

    def counter():
        count[0] += 1
        return count[0]

    return counter


counter1 = make_counter()
print("计数器闭包:")
print(f"  第1次调用: {counter1()}")
print(f"  第2次调用: {counter1()}")
print(f"  第3次调用: {counter1()}")

counter2 = make_counter()
print(f"  新计数器: {counter2()}")

print()


def make_adder(x):
    """返回将参数加 x 的函数"""
    def adder(y):
        return x + y
    return adder


add5 = make_adder(5)
add10 = make_adder(10)
print(f"make_adder(5)(3) = {add5(3)}")
print(f"make_adder(10)(3) = {add10(3)}")

print(f"\n闭包变量: {add5.__closure__}")
print(f"闭包单元格: {[c.cell_contents for c in add5.__closure__]}")

print()

# ============================================================
# 2. 装饰器（Decorator）
# ============================================================
print("=" * 60)
print("2. 装饰器（Decorator）")
print("=" * 60)


def timer(func):
    """统计函数执行时间的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  ⏱ {func.__name__} 耗时: {elapsed * 1000:.2f}ms")
        return result
    return wrapper


@timer
def slow_fib(n):
    """计算斐波那契数（慢递归）"""
    if n <= 1:
        return n
    return slow_fib(n - 1) + slow_fib(n - 2)


print("timer 装饰器测试:")
r = slow_fib(10)
print(f"  fib(10) = {r}")
print(f"  函数名保留: {slow_fib.__name__}")
print(f"  文档保留: {slow_fib.__doc__}")

print()


# 带参数装饰器
def retry(max_attempts=3, delay=0.1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"  🔄 {func.__name__} 第{attempt}次失败: {e}, 重试中...")
                    time.sleep(delay)
        return wrapper
    return decorator


attempts = 0


@retry(max_attempts=3, delay=0.05)
def unstable_api():
    """模拟不稳定 API"""
    global attempts
    attempts += 1
    if attempts < 3:
        raise ConnectionError("网络超时")
    return "成功响应"


print("retry 装饰器测试:")
result = unstable_api()
print(f"  最终结果: {result}")

print()


# 缓存装饰器
@lru_cache(maxsize=None)
@timer
def cached_fib(n):
    """带缓存和计时的斐波那契"""
    if n <= 1:
        return n
    return cached_fib(n - 1) + cached_fib(n - 2)


print("缓存装饰器测试:")
print(f"  第一次 (无缓存):")
r1 = cached_fib(30)
print(f"  fib(30) = {r1}")
print(f"  第二次 (有缓存):")
r2 = cached_fib(30)
print(f"  fib(30) = {r2}")
print(f"  缓存信息: {cached_fib.cache_info()}")

print()


# 日志装饰器
def log_calls(logger=print):
    """记录函数调用的装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            args_repr = ", ".join(repr(a) for a in args)
            kwargs_repr = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
            signature = args_repr
            if kwargs_repr:
                signature += ", " + kwargs_repr
            logger(f"  📝 {func.__name__}({signature})")
            result = func(*args, **kwargs)
            logger(f"     → {result!r}")
            return result
        return wrapper
    return decorator


@log_calls()
def divide(a, b):
    return a / b if b != 0 else float("inf")


print("日志装饰器测试:")
r1 = divide(10, 3)
r2 = divide(10, 0)

print()

# ============================================================
# 3. 函数工厂
# ============================================================
print("=" * 60)
print("3. 函数工厂")
print("=" * 60)


def create_validator(condition, error_msg):
    """创建验证器工厂"""
    def validator(value):
        if not condition(value):
            raise ValueError(error_msg)
        return value
    return validator


is_positive = create_validator(lambda x: x > 0, "值必须为正数")
is_even = create_validator(lambda x: x % 2 == 0, "值必须为偶数")
is_in_range = create_validator(lambda x: 0 <= x <= 100, "值必须在 0-100 范围内")

print("验证器工厂测试:")
print(f"  is_positive(5)  = {is_positive(5)}")
print(f"  is_even(10)     = {is_even(10)}")
print(f"  is_in_range(50) = {is_in_range(50)}")

try:
    is_positive(-1)
except ValueError as e:
    print(f"  is_positive(-1) 抛出: {e}")

try:
    is_even(3)
except ValueError as e:
    print(f"  is_even(3)      抛出: {e}")

print()


def create_math_operation(op_name):
    """数学运算工厂"""
    operations = {
        "add": lambda a, b: a + b,
        "subtract": lambda a, b: a - b,
        "multiply": lambda a, b: a * b,
        "divide": lambda a, b: a / b if b != 0 else float("inf"),
        "power": lambda a, b: a ** b,
    }
    return operations.get(op_name, lambda a, b: None)


add_op = create_math_operation("add")
pow_op = create_math_operation("power")
print(f"  add_op(3, 5)     = {add_op(3, 5)}")
print(f"  pow_op(2, 10)    = {pow_op(2, 10)}")

print()

# ============================================================
# 4. 偏函数（Partial Application）
# ============================================================
print("=" * 60)
print("4. 偏函数（Partial Application）")
print("=" * 60)


def power(base, exponent):
    return base ** exponent


square = partial(power, exponent=2)
cube = partial(power, exponent=3)

print(f"  square(5)  = {square(5)}")
print(f"  cube(3)    = {cube(3)}")


def format_number(number, decimal_places, prefix="", suffix=""):
    return f"{prefix}{number:.{decimal_places}f}{suffix}"


currency = partial(format_number, decimal_places=2, prefix="¥")
percentage = partial(format_number, decimal_places=1, suffix="%")

print(f"  currency(1999.5)   = {currency(1999.5)}")
print(f"  percentage(0.856)  = {percentage(0.856)}")

print()

# ============================================================
# 5. 柯里化（Currying）
# ============================================================
print("=" * 60)
print("5. 柯里化（Currying）")
print("=" * 60)


def curry(func):
    """手动实现柯里化"""
    def curried(*args):
        if len(args) >= func.__code__.co_argcount:
            return func(*args)
        return lambda *more_args: curried(*args, *more_args)
    return curried


@curry
def add_three(a, b, c):
    return a + b + c


print("柯里化测试:")
add_five = add_three(5)
add_five_and_three = add_five(3)
result = add_five_and_three(2)
print(f"  add_three(5)(3)(2) = {result}")
print(f"  add_three(1, 2, 3) = {add_three(1, 2, 3)}")
print(f"  add_three(1)(2, 3) = {add_three(1)(2, 3)}")

print()

# ============================================================
# 6. 函数组合（Composition）
# ============================================================
print("=" * 60)
print("6. 函数组合（Composition）")
print("=" * 60)


def compose(*funcs):
    """函数组合：从右到左执行"""
    def composed(arg):
        result = arg
        for func in reversed(funcs):
            result = func(result)
        return result
    return composed


def double(x):
    return x * 2


def increment(x):
    return x + 1


def square_func(x):
    return x ** 2


pipeline = compose(square_func, increment, double)
print(f"  compose(square, inc, double)(3) = {pipeline(3)}")


def pipe(*funcs):
    """管道组合：从左到右执行"""
    def piped(arg):
        result = arg
        for func in funcs:
            result = func(result)
        return result
    return piped


data_pipeline = pipe(double, increment, square_func)
print(f"  pipe(double, inc, square)(3)    = {data_pipeline(3)}")

print()

# ============================================================
# 7. 综合案例：数据处理框架
# ============================================================
print("=" * 60)
print("7. 综合案例：数据处理框架")
print("=" * 60)


def create_pipeline(name):
    """创建数据处理管道框架"""
    steps = []

    def add_step(step_func, step_name=None):
        steps.append((step_func, step_name or step_func.__name__))

    def process(data):
        print(f"\n📊 管道: {name}")
        print("-" * 40)
        current = data
        for step_func, step_name in steps:
            print(f"  Step: {step_name}")
            current = step_func(current)
        return current

    return {"add_step": add_step, "process": process}


pipeline_ctx = create_pipeline("数据分析")

pipeline_ctx["add_step"](
    lambda data: map(lambda x: x ** 2, data), "平方"
)
pipeline_ctx["add_step"](
    lambda data: filter(lambda x: x % 10 == 0, data), "被10整除"
)
pipeline_ctx["add_step"](
    lambda data: reduce(lambda a, b: a + b, data, 0), "求和"
)
pipeline_ctx["add_step"](
    lambda data: (f"结果: {data}", data)[0], "格式化"
)

data = range(1, 21)
print(f"输入数据: {list(data)}")
result = pipeline_ctx["process"](data)
print(f"\n最终结果: {result}")

print("\n✅ 高阶函数应用实战完成")
