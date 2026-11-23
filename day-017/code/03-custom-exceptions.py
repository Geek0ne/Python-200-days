#!/usr/bin/env python3
"""
Day 017 — 自定义异常实战

展示如何在实际项目中设计和应用自定义异常层次结构。

运行方式：
  python3 03-custom-exceptions.py
"""

import sys
import json
import time
from typing import Any, Optional

SEP = "=" * 60


# ═══════════════════════════════════════════════════════════════
# 1. 项目级异常层次结构
# ═══════════════════════════════════════════════════════════════

class AppError(Exception):
    """应用异常的基类 — 所有业务异常的父类"""
    def __init__(self, message: str, code: str = "UNKNOWN", context: dict = None):
        self.code = code
        self.context = context or {}
        super().__init__(f"[{code}] {message}")


class DataError(AppError):
    """数据层异常"""
    pass


class DatabaseError(DataError):
    """数据库操作异常"""
    def __init__(self, message: str, query: str = "", db_name: str = "", **kwargs):
        self.query = query
        self.db_name = db_name
        context = kwargs.pop("context", {})
        context.update({"query": query, "db": db_name})
        super().__init__(message, code="DB_ERR", context=context)


class ConnectionError(DatabaseError):
    """数据库连接异常"""
    def __init__(self, host: str = "", port: int = 0, **kwargs):
        self.host = host
        self.port = port
        context = kwargs.pop("context", {})
        context.update({"host": host, "port": port})
        super().__init__(
            f"无法连接到数据库 {host}:{port}",
            code="DB_CONN",
            context=context,
            **kwargs
        )


class QueryError(DatabaseError):
    """查询异常"""
    pass


class ValidationError(AppError):
    """验证异常"""
    pass


class FieldError(ValidationError):
    """字段验证异常"""
    def __init__(self, field: str, expected: str, actual: Any, **kwargs):
        self.field = field
        self.expected = expected
        self.actual = actual
        context = kwargs.pop("context", {})
        context.update({"field": field, "expected": expected, "actual": repr(actual)})
        super().__init__(
            f"字段 '{field}' 验证失败: 期望 {expected}, 收到 {actual!r}",
            code="FIELD_ERR",
            context=context,
            **kwargs
        )


class NetworkError(AppError):
    """网络异常"""
    pass


class TimeoutError(NetworkError):
    """超时异常"""
    def __init__(self, operation: str, timeout_sec: float, **kwargs):
        self.operation = operation
        self.timeout_sec = timeout_sec
        context = kwargs.pop("context", {})
        context.update({"operation": operation, "timeout": timeout_sec})
        super().__init__(
            f"操作 '{operation}' 超时 ({timeout_sec}s)",
            code="TIMEOUT",
            context=context,
            **kwargs
        )


class RetryError(AppError):
    """重试耗尽异常"""
    def __init__(self, operation: str, attempts: int, last_error: Exception = None, **kwargs):
        self.operation = operation
        self.attempts = attempts
        self.last_error = last_error
        context = kwargs.pop("context", {})
        context.update({"operation": operation, "attempts": attempts})
        msg = f"操作 '{operation}' 重试 {attempts} 次后仍然失败"
        if last_error:
            msg += f": {last_error}"
        super().__init__(msg, code="RETRY_EXHAUSTED", context=context, **kwargs)


class AuthError(AppError):
    """认证/授权异常"""
    pass


# 异常层次树
def print_exception_tree():
    """打印异常层次结构"""
    print(SEP)
    print("📂 自定义异常层次结构")
    print(SEP)

    tree = """AppError (应用异常基类)
 ├── DataError (数据层)
 │    └── DatabaseError (数据库操作)
 │         ├── ConnectionError (连接错误)
 │         └── QueryError (查询错误)
 ├── ValidationError (验证)
 │    └── FieldError (字段验证)
 ├── NetworkError (网络)
 │    └── TimeoutError (超时)
 ├── RetryError (重试耗尽)
 └── AuthError (认证授权)"""
    print(tree)


# ═══════════════════════════════════════════════════════════════
# 2. 使用自定义异常 — 模拟数据库层
# ═══════════════════════════════════════════════════════════════

class Database:
    """模拟数据库"""
    def __init__(self, host: str, port: int, db_name: str):
        self.host = host
        self.port = port
        self.db_name = db_name
        self._connected = False
        self._tables: dict[str, list[dict]] = {
            "users": [
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ]
        }

    def connect(self):
        """模拟连接数据库"""
        print(f"  🔌 尝试连接 {self.host}:{self.port}/{self.db_name}...")
        # 模拟连接失败
        if self.port == 0:
            raise ConnectionError(
                host=self.host, port=self.port,
                db_name=self.db_name, query="CONNECT"
            )
        self._connected = True
        print(f"  ✅ 已连接到 {self.db_name}")

    def query(self, sql: str) -> list[dict]:
        """执行查询"""
        if not self._connected:
            raise DatabaseError("数据库未连接", query=sql, db_name=self.db_name)

        if sql.upper().startswith("SELECT"):
            table = "users"  # 简化
            return self._tables.get(table, [])
        else:
            raise QueryError(f"不支持的查询类型", query=sql, db_name=self.db_name)

    def close(self):
        """关闭连接"""
        self._connected = False
        print(f"  🔌 已断开 {self.db_name}")


# ═══════════════════════════════════════════════════════════════
# 3. 重试装饰器
# ═══════════════════════════════════════════════════════════════

class RetryableError(AppError):
    """可重试操作的基类"""
    pass


def retry(max_attempts: int = 3, delay: float = 0.5,
          retryable_exceptions: tuple = (RetryableError,)):
    """重试装饰器

    Args:
        max_attempts: 最大重试次数
        delay: 重试间隔（秒）
        retryable_exceptions: 可重试的异常类型元组

    Raises:
        RetryError: 所有重试都失败时
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    if attempt < max_attempts:
                        print(f"  🔄 第 {attempt} 次尝试失败: {e}")
                        print(f"  ⏳ 等待 {delay}s 后重试...")
                        time.sleep(delay)
                    else:
                        raise RetryError(
                            func.__name__,
                            max_attempts,
                            last_error=last_error
                        ) from e
            return None  # unreachable
        return wrapper
    return decorator


# 模拟可重试操作
class TemporaryError(RetryableError):
    """临时故障（可重试）"""
    pass


attempt_counter = 0


@retry(max_attempts=4, delay=0.1)
def unstable_api_call(user_id: int) -> dict:
    """模拟不稳定的 API 调用"""
    global attempt_counter
    attempt_counter += 1

    if attempt_counter < 3:
        raise TemporaryError(f"服务暂时不可用 (attempt {attempt_counter})")

    return {"id": user_id, "name": "Alice", "status": "ok"}


# ═══════════════════════════════════════════════════════════════
# 4. 异常处理器 / 错误中间件模式
# ═══════════════════════════════════════════════════════════════

class ErrorHandler:
    """异常处理器 — 将异常转换为用户友好的响应"""

    @staticmethod
    def to_response(error: Exception) -> dict:
        """将异常转换为响应字典"""
        if isinstance(error, FieldError):
            return {
                "status": 422,
                "error": "VALIDATION_ERROR",
                "message": str(error),
                "field": error.field,
            }
        elif isinstance(error, ConnectionError):
            return {
                "status": 503,
                "error": "SERVICE_UNAVAILABLE",
                "message": "后端服务暂时不可用，请稍后重试",
                "detail": str(error) if "--verbose" in sys.argv else None,
            }
        elif isinstance(error, TimeoutError):
            return {
                "status": 504,
                "error": "GATEWAY_TIMEOUT",
                "message": f"请求超时 ({error.timeout_sec}s)",
            }
        elif isinstance(error, AuthError):
            return {
                "status": 401,
                "error": "UNAUTHORIZED",
                "message": str(error),
            }
        elif isinstance(error, AppError):
            return {
                "status": 500,
                "error": error.code,
                "message": str(error),
            }
        else:
            # 未知异常
            return {
                "status": 500,
                "error": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "detail": str(error) if "--verbose" in sys.argv else None,
            }


# ═══════════════════════════════════════════════════════════════
# 5. 综合演示
# ═══════════════════════════════════════════════════════════════

def demo_database_layer():
    """演示自定义异常在数据库层的使用"""
    print(SEP)
    print("🗄️  数据库层异常演示")
    print(SEP)

    print("\n▶ 场景 1: 连接成功 → 查询正常")
    db = Database("localhost", 5432, "testdb")
    try:
        db.connect()
        users = db.query("SELECT * FROM users")
        print(f"  查询结果: {users}")
    except AppError as e:
        print(f"  ❌ 异常: {e}")
    finally:
        db.close()

    print("\n▶ 场景 2: 连接失败")
    bad_db = Database("localhost", 0, "testdb")
    try:
        bad_db.connect()
    except ConnectionError as e:
        print(f"  ❌ 捕获到 ConnectionError:")
        print(f"     消息: {e}")
        print(f"     代码: {e.code}")
        print(f"     主机: {e.host}:{e.port}")
        print(f"     上下文: {e.context}")

    print("\n▶ 场景 3: 未连接就查询")
    fresh_db = Database("localhost", 5432, "testdb")
    try:
        fresh_db.query("SELECT * FROM users")
    except DatabaseError as e:
        print(f"  ❌ 捕获到 DatabaseError: {e}")
        print(f"     查询: {e.query}")


def demo_retry():
    """演示重试装饰器"""
    global attempt_counter
    attempt_counter = 0

    print(SEP)
    print("🔄 重试机制演示")
    print(SEP)

    print("\n▶ 重试后成功:")
    try:
        result = unstable_api_call(42)
        print(f"  ✅ 最终结果: {result}")
    except RetryError as e:
        print(f"  ❌ {e}")

    # 模拟永远失败
    print("\n▶ 重试后仍然失败:")
    # 重置计数器到一个永不成功的状态
    attempt_counter = 0

    @retry(max_attempts=2, delay=0.05)
    def always_fails():
        raise TemporaryError("总是失败")

    try:
        always_fails()
    except RetryError as e:
        print(f"  ❌ 捕获到 RetryError:")
        print(f"     操作: {e.operation}")
        print(f"     尝试次数: {e.attempts}")
        if e.last_error:
            print(f"     最后一次错误: {e.last_error}")


def demo_field_validation():
    """演示字段验证异常"""
    print(SEP)
    print("📝 字段验证演示")
    print(SEP)

    def validate_user(data: dict) -> bool:
        """验证用户数据"""
        errors = []

        try:
            if not data.get("name") or len(str(data["name"]).strip()) < 2:
                raise FieldError("name", "至少 2 个字符", data.get("name", ""))
        except FieldError as e:
            errors.append(e)

        try:
            age = int(data.get("age", -1))
            if age < 0 or age > 150:
                raise FieldError("age", "0-150 之间的整数", data.get("age"))
        except FieldError as e:
            errors.append(e)
        except (ValueError, TypeError) as e:
            errors.append(FieldError("age", "有效的整数值", data.get("age")))

        if errors:
            # 使用 ErrorHandler 转换
            print("\n  验证失败:")
            for e in errors:
                response = ErrorHandler.to_response(e)
                print(f"    {response}")
            return False
        return True

    print("\n▶ 场景 1: 有效数据")
    validate_user({"name": "Alice", "age": "28"})
    print("  ✅ 验证通过")

    print("\n▶ 场景 2: 无效数据")
    validate_user({"name": "A", "age": "abc"})


def demo_error_handler():
    """演示异常处理器"""
    print(SEP)
    print("🔧 异常处理器演示")
    print(SEP)

    test_cases = [
        FieldError("email", "有效的邮箱地址", "not-an-email"),
        ConnectionError(host="db-prod", port=3306),
        TimeoutError("API 请求", 30.0),
        AuthError("登录令牌已过期", code="TOKEN_EXPIRED"),
        RetryError("fetch_data", 3, last_error=TimeoutError("连接超时", 5)),
        ValueError("未预期错误"),
    ]

    for error in test_cases:
        print(f"\n▶ {type(error).__name__}: {error}")
        response = ErrorHandler.to_response(error)
        for k, v in response.items():
            print(f"    {k}: {v}")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 自定义异常实战")
    print()

    print_exception_tree()
    demo_database_layer()
    demo_retry()
    demo_field_validation()
    demo_error_handler()

    print(SEP)
    print("✅ 所有演示完成！")
    print("📚 关键要点:")
    print("   1. 从 Exception 继承建立层次结构")
    print("   2. 在构造函数中收集有用上下文")
    print("   3. 用 AppError 基类统一捕获业务异常")
    print("   4. 使用 ErrorHandler 模式统一转换异常")
    print("   5. 使用 Retry + RetryableError 处理临时故障")
    print("   6. 自定义异常的 __init__ 应调用 super().__init__()")


if __name__ == "__main__":
    main()
