#!/usr/bin/env python3
"""
Day 023 — 日志装饰器实战

一个功能完整的日志装饰器，用于记录函数调用信息。
包括：
1. 基础日志装饰器
2. 可配置的日志装饰器（自定义格式、输出目标）
3. 函数调用追踪
4. 性能日志
"""

import functools
import logging
import time
from datetime import datetime


# ============================================================
# 1. 基础日志装饰器
# ============================================================

def log_calls(func):
    """记录每次函数调用的基本信息"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] 调用: {func.__name__}")
        print(f"[LOG] 参数: args={args}, kwargs={kwargs}")
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[LOG] 返回: {result!r}")
        print(f"[LOG] 耗时: {elapsed:.4f} 秒")
        return result
    return wrapper


@log_calls
def divide(a, b):
    """除法运算"""
    if b == 0:
        return "错误：除数不能为零"
    return a / b


print("=" * 60)
print("1. 基础日志装饰器")
print("=" * 60)

divide(10, 3)
print()
divide(10, 0)


# ============================================================
# 2. 带自定义格式的日志装饰器
# ============================================================

def detailed_log(func):
    """记录详细调用信息的日志装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        arg_str = ", ".join(
            [repr(a) for a in args] +
            [f"{k}={v!r}" for k, v in kwargs.items()]
        )
        print(f"[{timestamp}] 🔄 {func.__name__}({arg_str})")

        try:
            result = func(*args, **kwargs)
            print(f"[{timestamp}] ✅ {func.__name__} → {result!r}")
            return result
        except Exception as e:
            print(f"[{timestamp}] ❌ {func.__name__} → 异常: {type(e).__name__}: {e}")
            raise
    return wrapper


@detailed_log
def process_order(order_id, items, discount=0):
    """处理订单"""
    total = sum(items) * (1 - discount)
    if total < 0:
        raise ValueError("订单总额不能为负数")
    return {"order_id": order_id, "total": total, "items_count": len(items)}


print("\n" + "=" * 60)
print("2. 详细日志装饰器")
print("=" * 60)

order = process_order("ORD-001", [100, 200, 150], discount=0.1)
print(f"订单结果: {order}")

print()

try:
    process_order("ORD-002", [-100], discount=2)
except ValueError as e:
    print(f"捕获预期异常: {e}")


# ============================================================
# 3. 使用 logging 模块的日志装饰器
# ============================================================

# 配置 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("decorator")


def logged(level=logging.INFO):
    """使用标准 logging 模块的日志装饰器（可配置级别）"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.log(level, f"调用 {func.__name__}()")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func.__name__}() → {result!r}")
                return result
            except Exception as e:
                logger.exception(f"{func.__name__}() 抛出异常: {e}")
                raise
        return wrapper
    return decorator


@logged(level=logging.DEBUG)
def calculate(a, b, op="add"):
    """基本运算"""
    if op == "add":
        return a + b
    elif op == "sub":
        return a - b
    elif op == "mul":
        return a * b
    elif op == "div":
        return a / b
    else:
        raise ValueError(f"未知操作: {op}")


print("\n" + "=" * 60)
print("3. logging 模块日志装饰器")
print("=" * 60)

calculate(10, 5, op="add")
calculate(10, 5, op="mul")

try:
    calculate(10, 0, op="div")
except ZeroDivisionError:
    pass


# ============================================================
# 4. 调用追踪装饰器（嵌套调用缩进）
# ============================================================

class CallTracker:
    """追踪函数调用深度并缩进显示"""
    _depth = 0

    @classmethod
    def increment(cls):
        cls._depth += 1
        return cls._depth

    @classmethod
    def decrement(cls):
        cls._depth -= 1
        return cls._depth


def trace_calls(func):
    """追踪函数调用，按嵌套深度缩进显示"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        CallTracker.increment()
        indent = "  " * (CallTracker._depth - 1)
        print(f"{indent}→ {func.__name__}{args}")

        try:
            result = func(*args, **kwargs)
            print(f"{indent}← {func.__name__} → {result!r}")
            return result
        finally:
            CallTracker.decrement()
    return wrapper


@trace_calls
def factorial(n):
    """递归阶乘（带调用追踪）"""
    if n <= 1:
        return 1
    return n * factorial(n - 1)


print("\n" + "=" * 60)
print("4. 调用追踪装饰器（递归函数）")
print("=" * 60)

factorial(5)


# ============================================================
# 5. 实战：API 请求日志
# ============================================================

class APILogger:
    """模拟 API 请求日志记录器"""

    def __init__(self):
        self.requests = []

    def log_request(self, method, endpoint, status, duration):
        self.requests.append({
            "method": method,
            "endpoint": endpoint,
            "status": status,
            "duration": duration,
            "time": datetime.now().isoformat()
        })

    def summary(self):
        successful = sum(1 for r in self.requests if r["status"] < 400)
        failed = len(self.requests) - successful
        avg_duration = sum(r["duration"] for r in self.requests) / len(self.requests) if self.requests else 0
        print(f"\n📊 API 请求统计:")
        print(f"   总请求: {len(self.requests)}")
        print(f"   成功: {successful}")
        print(f"   失败: {failed}")
        print(f"   平均耗时: {avg_duration:.3f}s")


api_logger = APILogger()


def api_log(func):
    """API 请求日志装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        method = kwargs.get("method", "GET")
        endpoint = kwargs.get("endpoint", "/")
        start = time.time()

        try:
            result = func(*args, **kwargs)
            status = result.get("status", 200)
            duration = time.time() - start
            api_logger.log_request(method, endpoint, status, duration)
            print(f"[API] {method} {endpoint} → {status} ({duration:.3f}s)")
            return result
        except Exception as e:
            duration = time.time() - start
            api_logger.log_request(method, endpoint, 500, duration)
            print(f"[API] {method} {endpoint} → 500 ({duration:.3f}s) - {e}")
            raise
    return wrapper


import random


@api_log
def fetch_data(method="GET", endpoint="/", simulate_error=False):
    """模拟 API 请求"""
    time.sleep(random.uniform(0.05, 0.2))
    if simulate_error:
        raise ConnectionError("网络连接失败")
    return {"status": 200, "data": f"数据来自 {endpoint}"}


print("\n" + "=" * 60)
print("5. 实战：API 请求日志")
print("=" * 60)

fetch_data(method="GET", endpoint="/users")
fetch_data(method="POST", endpoint="/users/create")
fetch_data(method="GET", endpoint="/orders/123")

try:
    fetch_data(method="GET", endpoint="/error-test", simulate_error=True)
except ConnectionError:
    pass

api_logger.summary()

print("\n✅ 所有日志装饰器示例完成！")
