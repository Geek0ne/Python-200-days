#!/usr/bin/env python3
"""
Day 024 — 缓存/重试/权限装饰器实战

涵盖：
1. 简单缓存装饰器（memoize）
2. LRU 缓存装饰器
3. TTL（过期时间）缓存
4. 基础重试装饰器
5. 高级重试装饰器（指数退避、异常白名单）
6. 权限检查装饰器
7. 综合应用
"""

import functools
import time
import random
from collections import OrderedDict


print("=" * 60)
print("1. 简单缓存装饰器 (Memoize)")
print("=" * 60)


def memoize(func):
    """缓存函数返回结果（基于参数）"""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # 创建缓存键（参数必须可哈希）
        key = (args, tuple(sorted(kwargs.items())))

        if key not in cache:
            cache[key] = func(*args, **kwargs)
            print(f"  [缓存] 未命中，计算 {func.__name__}{args}")
        else:
            print(f"  [缓存] 命中！返回缓存结果")

        return cache[key]

    # 暴露缓存操作
    wrapper.cache = cache
    wrapper.cache_info = lambda: f"缓存大小: {len(cache)}"
    wrapper.cache_clear = cache.clear
    return wrapper


@memoize
def fibonacci(n):
    """计算斐波那契数列（递归）"""
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


print("计算 fibonacci(10):")
result = fibonacci(10)
print(f"  fibonacci(10) = {result}")
print(f"  缓存信息: {fibonacci.cache_info()}")

print("\n再次计算 fibonacci(10) — 应该命中缓存:")
fibonacci(10)

print("\n计算 fibonacci(11):")
fibonacci(11)

print(f"\n最终缓存: {fibonacci.cache_info()}")


print()
print("=" * 60)
print("2. LRU 缓存装饰器")
print("=" * 60)


def lru_cache(maxsize=5):
    """LRU (Least Recently Used) 缓存

    使用 OrderedDict 实现——最近访问的移到末尾，
    超出容量时删除最早访问的（最前面的）。
    """
    def decorator(func):
        cache = OrderedDict()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))

            if key in cache:
                # 命中：移到末尾（最近使用）
                cache.move_to_end(key)
                print(f"  [LRU] 命中第 {list(cache.keys()).index(key)} 个缓存")
                return cache[key]

            # 未命中：计算结果
            result = func(*args, **kwargs)

            # 超出容量：删除最久未使用的
            if len(cache) >= maxsize:
                oldest = next(iter(cache))
                cache.pop(oldest)
                print(f"  [LRU] 容量满，淘汰最旧缓存 {oldest}")

            cache[key] = result
            print(f"  [LRU] 添加新缓存，当前大小 {len(cache)}/{maxsize}")
            return result

        wrapper.cache = cache
        wrapper.cache_info = lambda: f"LRU 缓存: {len(cache)}/{maxsize}"
        return wrapper
    return decorator


@lru_cache(maxsize=3)
def slow_square(n):
    """慢速计算平方"""
    time.sleep(0.5)
    return n * n


print("第一次调用（缓存未命中）:")
slow_square(1)
slow_square(2)
slow_square(3)
print("\n再次调用（缓存命中）:")
slow_square(1)
slow_square(2)

print("\n添加新元素（超出容量 3）:")
slow_square(4)  # 淘汰 1
slow_square(5)  # 淘汰 2

print("\n之前被淘汰的 1 再次计算（重新缓存）:")
slow_square(1)  # 淘汰 3


print()
print("=" * 60)
print("3. TTL 缓存装饰器（带过期时间）")
print("=" * 60)


def ttl_cache(ttl_seconds=10):
    """带过期时间的缓存装饰器"""
    def decorator(func):
        cache = {}  # key → (value, expire_time)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()

            if key in cache:
                value, expire_time = cache[key]
                if now < expire_time:
                    remaining = expire_time - now
                    print(f"  [TTL] 缓存有效，剩余 {remaining:.1f}s")
                    return value
                else:
                    print(f"  [TTL] 缓存已过期，重新计算")
                    del cache[key]

            value = func(*args, **kwargs)
            cache[key] = (value, now + ttl_seconds)
            print(f"  [TTL] 缓存新结果 (有效期 {ttl_seconds}s)")
            return value

        wrapper.cache = cache
        return wrapper
    return decorator


@ttl_cache(ttl_seconds=2)
def get_timestamp():
    """返回当前时间戳"""
    return time.time()


print("第一次调用:")
t1 = get_timestamp()
print(f"  时间戳: {t1:.4f}")

print("\n立即再次调用（缓存命中）:")
t2 = get_timestamp()
print(f"  时间戳: {t2:.4f}")
print(f"  相同? {t1 == t2}")

print("\n等待 2 秒后...")
time.sleep(2.1)

print("缓存过期后调用:")
t3 = get_timestamp()
print(f"  时间戳: {t3:.4f}")
print(f"  不同? {t3 != t2}")


print()
print("=" * 60)
print("4. 基础重试装饰器")
print("=" * 60)


def retry(max_attempts=3):
    """函数执行失败时自动重试"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 1:
                        print(f"  [重试] 第 {attempt} 次成功")
                    return result
                except Exception as e:
                    last_exception = e
                    print(f"  [重试] 第 {attempt}/{max_attempts} 次失败: {e}")
                    if attempt == max_attempts:
                        print(f"  [重试] 已达最大重试次数，抛出异常")
                        raise
            # 不应该到达这里，但为了类型安全
            raise last_exception or RuntimeError("重试失败")
        return wrapper
    return decorator


attempt_counter = 0


@retry(max_attempts=3)
def unstable_service():
    """模拟不稳定服务：前两次失败，第三次成功"""
    global attempt_counter
    attempt_counter += 1
    if attempt_counter < 2:
        raise ConnectionError("服务暂时不可用")
    return "服务响应成功"


print("调用不稳定服务（预期前1次失败，第2次成功）:")
attempt_counter = 0
result = unstable_service()
print(f"  最终结果: {result}")


# 模拟始终失败的服务
@retry(max_attempts=2)
def always_fail():
    raise ValueError("始终失败")


print("\n调用始终失败的服务:")
try:
    always_fail()
except ValueError as e:
    print(f"  最终抛出: {type(e).__name__}: {e}")


print()
print("=" * 60)
print("5. 高级重试装饰器（指数退避+异常白名单）")
print("=" * 60)


def advanced_retry(
    max_attempts=3,
    delay=0.1,
    backoff=2.0,
    max_delay=5.0,
    exceptions=(Exception,),
):
    """高级重试装饰器

    参数:
        max_attempts: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子（每次延迟 × backoff）
        max_delay: 最大延迟上限
        exceptions: 需要重试的异常类型元组
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        print(f"  [高级重试] 第 {attempt} 次失败，不再重试: {e}")
                        raise
                    print(f"  [高级重试] 第 {attempt} 次失败 ({e}), "
                          f"等待 {current_delay:.2f}s 后重试...")
                    time.sleep(current_delay)
                    current_delay = min(current_delay * backoff, max_delay)
                except Exception as e:
                    # 不在重试白名单中的异常直接抛出
                    print(f"  [高级重试] 不可重试的异常: {type(e).__name__}")
                    raise
            return None  # 不应该到这里
        return wrapper
    return decorator


@advanced_retry(
    max_attempts=4,
    delay=0.05,
    backoff=2.0,
    max_delay=1.0,
    exceptions=(ConnectionError, TimeoutError),
)
def fetch_data(url):
    """模拟获取数据"""
    if random.random() < 0.7:  # 70% 概率失败
        raise ConnectionError(f"无法连接 {url}")
    return f"从 {url} 获取的数据"


print("调用带指数退避的请求 (70% 失败率):")
try:
    result = fetch_data("https://api.example.com/data")
    print(f"  最终结果: {result}")
except ConnectionError as e:
    print(f"  全部重试失败: {e}")


# 测试不在白名单中的异常
@advanced_retry(exceptions=(ConnectionError,))
def type_error_function():
    raise TypeError("类型错误——不应重试")


print("\n不可重试的类型错误:")
try:
    type_error_function()
except TypeError as e:
    print(f"  直接抛出（未重试）: {e}")


print()
print("=" * 60)
print("6. 权限检查装饰器")
print("=" * 60)


class PermissionError_(Exception):
    """权限异常"""
    pass


def require_role(role):
    """检查用户是否有指定角色"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if not isinstance(user, dict) or user.get("role") != role:
                username = user.get("name", "未知用户") if isinstance(user, dict) else "未知"
                raise PermissionError_(
                    f"{username} 需要 [{role}] 角色权限，当前角色: {user.get('role', '无')}"
                )
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission):
    """检查用户是否有特定权限"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if permission not in user.get("permissions", []):
                raise PermissionError_(
                    f"{user.get('name')} 缺少 [{permission}] 权限"
                )
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


# 模拟用户
admin_user = {"name": "Admin", "role": "admin", "permissions": ["read", "write", "delete"]}
editor_user = {"name": "Editor", "role": "editor", "permissions": ["read", "write"]}
viewer_user = {"name": "Viewer", "role": "viewer", "permissions": ["read"]}


@require_role("admin")
def delete_database(user):
    """删除数据库（仅管理员）"""
    return f"✅ {user['name']} 成功删除数据库"


@require_permission("write")
def edit_document(user, doc_id):
    """编辑文档（需要写入权限）"""
    return f"✅ {user['name']} 编辑了文档 {doc_id}"


@require_permission("read")
def view_document(user, doc_id):
    """查看文档（需要读取权限）"""
    return f"✅ {user['name']} 查看了文档 {doc_id}"


print("权限检查测试:")
print()

# 管理员测试
print("管理员 Admin:")
try:
    result = delete_database(admin_user)
    print(f"  {result}")
except PermissionError_ as e:
    print(f"  ❌ {e}")

# 编辑者测试
print("\n编辑者 Editor:")
try:
    result = edit_document(editor_user, "DOC-001")
    print(f"  {result}")
except PermissionError_ as e:
    print(f"  ❌ {e}")

try:
    result = delete_database(editor_user)
except PermissionError_ as e:
    print(f"  ❌ {e}")

# 查看者测试
print("\n查看者 Viewer:")
try:
    result = view_document(viewer_user, "DOC-002")
    print(f"  {result}")
except PermissionError_ as e:
    print(f"  ❌ {e}")

try:
    result = edit_document(viewer_user, "DOC-002")
except PermissionError_ as e:
    print(f"  ❌ {e}")


print()
print("=" * 60)
print("7. 综合应用：带权限和重试的 API 调用")
print("=" * 60)


def require_role_v2(role):
    """检查角色（返回用户信息供后续使用）"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if user.get("role") != role:
                raise PermissionError_(f"需要 [{role}] 角色")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def api_retry(max_attempts=2):
    """API 重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except ConnectionError as e:
                    if attempt == max_attempts:
                        raise
                    print(f"  API 重试 {attempt}/{max_attempts}: {e}")
                    time.sleep(0.1)
            return None
        return wrapper
    return decorator


@require_role_v2("admin")
@api_retry(max_attempts=3)
def admin_api_call(user, endpoint):
    """管理员专用 API 调用（带重试）"""
    if random.random() < 0.5:
        raise ConnectionError("网络波动")
    return f"{user['name']} 调用了 {endpoint}"


print("综合测试（管理员 + 重试）:")
try:
    result = admin_api_call(admin_user, "/admin/backup")
    print(f"  结果: {result}")
except PermissionError_ as e:
    print(f"  ❌ {e}")
except ConnectionError as e:
    print(f"  ❌ 重试耗尽: {e}")

print("\n综合测试（非管理员）:")
try:
    result = admin_api_call(editor_user, "/admin/backup")
except PermissionError_ as e:
    print(f"  ❌ {e}")


print("\n✅ 所有缓存/重试/权限装饰器示例完成！")
