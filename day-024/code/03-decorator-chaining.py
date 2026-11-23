#!/usr/bin/env python3
"""
Day 024 — 装饰器链式组合实战

涵盖：
1. 装饰器链基础组合（洋葱模型验证）
2. 文本格式化链（bold / italic / underline）
3. 数据转换链（验证 → 清洗 → 格式化）
4. 认证与授权链
5. 缓存 + 重试组合
6. 装饰器工厂：动态组合
"""

import functools
import time
import random


print("=" * 60)
print("1. 装饰器链基础 — 洋葱模型验证")
print("=" * 60)


def dec_a(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  [A 前置]")
        result = func(*args, **kwargs)
        print("  [A 后置]")
        return f"<A>{result}</A>"
    return wrapper


def dec_b(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  [B 前置]")
        result = func(*args, **kwargs)
        print("  [B 后置]")
        return f"<B>{result}</B>"
    return wrapper


def dec_c(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("  [C 前置]")
        result = func(*args, **kwargs)
        print("  [C 后置]")
        return f"<C>{result}</C>"
    return wrapper


print("定义和装饰阶段:")
print("  @dec_a\n  @dec_b\n  @dec_c\n  def target(): ...")

@dec_a
@dec_b
@dec_c
def target():
    print("  ★ 原始函数执行 ★")
    return "Hello"


print("\n调用阶段:")
result = target()
print(f"\n最终输出: {result}")
print(f"预期: <A><B><C>Hello</C></B></A> — 确认洋葱模型!")


print()
print("=" * 60)
print("2. 文本格式化链 — HTML 标签组合")
print("=" * 60)


def bold(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return f"<b>{func(*args, **kwargs)}</b>"
    return wrapper


def italic(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return f"<i>{func(*args, **kwargs)}</i>"
    return wrapper


def underline(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return f"<u>{func(*args, **kwargs)}</u>"
    return wrapper


@bold
@italic
@underline
def get_text(name):
    return f"Hello, {name}!"


print("顺序 bold > italic > underline:")
print(f"  结果: {get_text('Alice')}")
print(f"  预期: <b><i><u>Hello, Alice!</u></i></b>")


# 不同顺序的结果不同
@underline
@italic
@bold
def get_text2(name):
    return f"Hello, {name}!"


print("\n顺序 underline > italic > bold:")
print(f"  结果: {get_text2('Bob')}")
print(f"  预期: <u><i><b>Hello, Bob!</b></i></u>")


print()
print("=" * 60)
print("3. 数据转换链 — 验证 → 清洗 → 格式化")
print("=" * 60)


def validate_positive(func):
    """验证输入为正数"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for arg in args:
            if isinstance(arg, (int, float)) and arg < 0:
                raise ValueError(f"参数 {arg} 不能为负数")
        for k, v in kwargs.items():
            if isinstance(v, (int, float)) and v < 0:
                raise ValueError(f"参数 {k}={v} 不能为负数")
        return func(*args, **kwargs)
    return wrapper


def sanitize_result(func):
    """清洗输出结果：保留两位小数"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, float):
            return round(result, 2)
        return result
    return wrapper


def format_result(func):
    """格式化输出：添加单位"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return f"结果: {result}"
    return wrapper


# 验证 → 清洗 → 格式化（从下往上：先验证，再清洗，最后格式化）
@format_result
@sanitize_result
@validate_positive
def calculate_price(unit_price, quantity, tax_rate=0.0):
    """计算总价"""
    subtotal = unit_price * quantity
    tax = subtotal * tax_rate
    return subtotal + tax


print("计算价格 (10.5, 3, tax_rate=0.08):")
print(f"  {calculate_price(10.5, 3, tax_rate=0.08)}")

print("\n计算价格 (0.99, 100):")
print(f"  {calculate_price(0.99, 100)}")

print("\n负值验证:")
try:
    calculate_price(-10, 5)
except ValueError as e:
    print(f"  ❌ {e}")


print()
print("=" * 60)
print("4. 认证与授权链")
print("=" * 60)


class AuthError(Exception):
    pass


def authenticated(func):
    """认证装饰器：检查用户是否已登录"""
    @functools.wraps(func)
    def wrapper(user, *args, **kwargs):
        if not user or not user.get("authenticated", False):
            raise AuthError("用户未登录")
        print("  [认证] ✅ 已登录")
        return func(user, *args, **kwargs)
    return wrapper


def require_role(role):
    """授权装饰器：检查角色"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if user.get("role") != role:
                raise AuthError(f"需要 [{role}] 角色")
            print(f"  [授权] ✅ 角色: {role}")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator


def audit_log(func):
    """审计日志装饰器：记录操作"""
    @functools.wraps(func)
    def wrapper(user, *args, **kwargs):
        print(f"  [审计] {user['name']} 执行 {func.__name__}")
        result = func(user, *args, **kwargs)
        print(f"  [审计] 操作完成")
        return result
    return wrapper


# 组合：先审计，再认证，最后授权（从下往上：授权 → 认证 → 审计）
@audit_log
@authenticated
@require_role("admin")
def delete_user(user, target_user_id):
    """删除用户"""
    print(f"  [操作] 删除用户 {target_user_id}")
    return {"status": "deleted", "user_id": target_user_id}


# 模拟用户
admin = {"name": "Admin", "authenticated": True, "role": "admin"}
viewer = {"name": "Viewer", "authenticated": True, "role": "viewer"}
anon = {"name": "Guest", "authenticated": False, "role": "guest"}

print("管理员操作:")
try:
    result = delete_user(admin, "user_123")
    print(f"  结果: {result}")
except AuthError as e:
    print(f"  ❌ {e}")

print("\n查看者操作（权限不足）:")
try:
    delete_user(viewer, "user_456")
except AuthError as e:
    print(f"  ❌ {e}")

print("\n未登录用户:")
try:
    delete_user(anon, "user_789")
except AuthError as e:
    print(f"  ❌ {e}")


print()
print("=" * 60)
print("5. 缓存 + 重试 组合实战")
print("=" * 60)


def cache_result(func):
    """简单缓存装饰器"""
    cache = {}

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            print(f"  [缓存] 命中!")
            return cache[key]
        result = func(*args, **kwargs)
        cache[key] = result
        print(f"  [缓存] 存储新结果")
        return result

    wrapper._cache = cache
    wrapper.cache_clear = cache.clear
    return wrapper


def retry_on_failure(max_attempts=2, delay=0.05):
    """重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"  [重试] 第 {attempt} 次失败: {e}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


# 组合方式 1：先缓存，后重试
# 缓存是外层，重试是内层
# 调用顺序：缓存先查 → 重试 → 原始函数
@cache_result
@retry_on_failure(max_attempts=3, delay=0.05)
def fetch_user_data(user_id):
    """获取用户数据（可能失败）"""
    if random.random() < 0.6:
        raise ConnectionError("获取数据失败")
    return {"id": user_id, "name": f"User_{user_id}", "balance": random.randint(0, 1000)}


print("第一次获取（缓存未命中，可能重试）:")
random.seed(42)
result = fetch_user_data(123)
print(f"  结果: {result}")

print("\n第二次获取（缓存命中，跳过所有）:")
result = fetch_user_data(123)
print(f"  结果: {result}")


# 组合方式 2：先重试，后缓存
# 重试是外层，缓存是内层
@retry_on_failure(max_attempts=3, delay=0.05)
@cache_result
def fetch_orders(user_id):
    """获取订单数据"""
    if random.random() < 0.4:
        raise ConnectionError("获取订单失败")
    return {"user_id": user_id, "orders": [f"ORD-{i}" for i in range(3)]}


print("\n\n组合方式对比（缓存在内层 vs 外层）:")
print("方式 1: @cache_result @retry_on_failure — 缓存失败结果!")
print("方式 2: @retry_on_failure @cache_result — 每次失败都重试,成功才缓存")


print()
print("=" * 60)
print("6. 装饰器工厂：动态组合")
print("=" * 60)


def compose_decorators(*decorators):
    """装饰器工厂：将多个装饰器组合成一个"""
    def combined_decorator(func):
        # 从下到上应用装饰器
        for dec in reversed(decorators):
            func = dec(func)
        return func
    return combined_decorator


# 预定义装饰器
def add_prefix(prefix):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return f"{prefix}{func(*args, **kwargs)}"
        return wrapper
    return decorator


def add_suffix(suffix):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return f"{func(*args, **kwargs)}{suffix}"
        return wrapper
    return decorator


# 使用工厂组合
full_format = compose_decorators(
    add_prefix(">>> "),
    bold,
    italic,
    add_suffix(" <<<"),
)


@full_format
def get_message():
    return "装饰器工厂!"


print("装饰器工厂组合的输出:")
print(f"  {get_message()}")


# 动态创建不同组合
error_format = compose_decorators(
    bold,
    add_prefix("❌ "),
    add_suffix(" ❌"),
)

success_format = compose_decorators(
    bold,
    add_prefix("✅ "),
    add_suffix(" ✅"),
)


@error_format
def error_msg():
    return "操作失败"


@success_format
def success_msg():
    return "操作成功"


print(f"\n错误消息: {error_msg()}")
print(f"成功消息: {success_msg()}")


print()
print("=" * 60)
print("7. 陷阱：装饰器顺序导致的问题")
print("=" * 60)


def validate_non_empty(func):
    """验证输入不为空"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for arg in args:
            if isinstance(arg, str) and not arg.strip():
                raise ValueError("参数不能为空字符串")
        return func(*args, **kwargs)
    return wrapper


def uppercase_result(func):
    """将结果转为大写"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str):
            return result.upper()
        return result
    return wrapper


# ❌ 错误顺序：先转换大小写，后验证
@validate_non_empty
@uppercase_result
def get_greeting_wrong(name):
    """获取问候语"""
    return f"hello, {name}"


# ✅ 正确顺序：先验证，后转换
@uppercase_result
@validate_non_empty
def get_greeting_correct(name):
    """获取问候语"""
    return f"hello, {name}"


print("错误顺序（验证在转换之后）:")
print(f"  调用 get_greeting_wrong('Alice'): {get_greeting_wrong('Alice')}")

print("\n正确顺序（验证在转换之前）:")
print(f"  调用 get_greeting_correct('Alice'): {get_greeting_correct('Alice')}")


print()
print("=" * 60)
print("8. 实战：完整的数据处理管道")
print("=" * 60)


def validate_email(func):
    """验证邮箱格式"""
    @functools.wraps(func)
    def wrapper(user_email, *args, **kwargs):
        if "@" not in user_email or "." not in user_email.split("@")[1]:
            raise ValueError(f"无效邮箱: {user_email}")
        print(f"  [验证] 邮箱格式正确")
        return func(user_email, *args, **kwargs)
    return wrapper


def rate_limit(max_calls=5, window=10):
    """限流装饰器"""
    calls = []

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # 清理过期记录
            while calls and now - calls[0] > window:
                calls.pop(0)
            if len(calls) >= max_calls:
                raise RuntimeError(
                    f"请求过于频繁，{window}s 内限制 {max_calls} 次"
                )
            calls.append(now)
            print(f"  [限流] 当前窗口: {len(calls)}/{max_calls}")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_result(func):
    """记录结果"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"  [日志] 操作结果: {result}")
        return result
    return wrapper


# 完整管道：日志 → 限流 → 验证 → 函数
@log_result
@rate_limit(max_calls=3, window=5)
@validate_email
def send_notification(user_email, message):
    """发送通知"""
    print(f"  [发送] 通知已发送到 {user_email}: '{message}'")
    return {"status": "sent", "email": user_email}


print("调用发送通知管道:")
try:
    send_notification("alice@example.com", "欢迎加入!")
    send_notification("bob@test.org", "您的订单已确认")
    send_notification("carol@mail.co", "系统更新通知")
except ValueError as e:
    print(f"  ❌ {e}")
except RuntimeError as e:
    print(f"  ❌ {e}")

print("\n测试无效邮箱:")
try:
    send_notification("invalid-email", "测试消息")
except ValueError as e:
    print(f"  ❌ {e}")
except RuntimeError as e:
    print(f"  ❌ 限流: {e} (等待 5 秒后重试...)")
    time.sleep(5)
    try:
        send_notification("invalid-email", "测试消息")
    except ValueError as e:
        print(f"  ❌ {e}")


print("\n✅ 所有装饰器链式组合示例完成！")
