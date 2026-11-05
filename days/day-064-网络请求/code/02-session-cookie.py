#!/usr/bin/env python3
"""
Day 064 - 网络请求
示例 2: Session/Cookie 管理与 HTTP 高级特性

本示例演示：
1. requests.Session 自动 Cookie 管理
2. 手动 Cookie 操作
3. 连接池与重试机制
4. 认证方式（Basic / Bearer / Digest）
5. 请求钩子（Hooks）
6. 上下文管理器（with Session）

安装依赖: pip install requests
运行方式: python3 02-session-cookie.py
"""

import time
import json

print("=" * 60)
print("🔐 Session / Cookie 管理与高级特性")
print("=" * 60)

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from http.cookiejar import CookieJar
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  requests 未安装。安装: pip install requests")

if not HAS_REQUESTS:
    print("    跳过所有演示。")
    sys.exit(0)

# ════════════════════════════════════════════
# 1. Session 基础 — Cookie 自动管理
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("1️⃣  Session Cookie 自动管理")
print("=" * 40)

# 创建 Session（相当于打开一个浏览器标签页）
session = requests.Session()
print("Session 已创建")

# 访问登录页面（获取 Cookie）
print("\n--- 模拟登录过程 ---")
login_response = session.post(
    "https://httpbin.org/cookies/set",
    params={"session_id": "abc123", "username": "alice"},
    timeout=10
)
print(f"登录响应状态码: {login_response.status_code}")

# Cookie 已经被 Session 自动保存
print(f"\nSession Cookie 列表:")
for cookie in session.cookies:
    print(f"  {cookie.name} = {cookie.value}")

# 后续请求自动携带 Cookie
print("\n--- 验证 Cookie 已携带 ---")
verify_response = session.get(
    "https://httpbin.org/cookies",
    timeout=10
)
print(f"服务器收到的 Cookie: {verify_response.json()}")

print("\n🎉 自动 Cookie 管理成功！")

# ─── 无 Session 的对比 ───
print("\n--- 无 Session 的对比（每次请求独立） ---")
no_session_response = requests.get(
    "https://httpbin.org/cookies",
    timeout=10
)
print(f"无 Session: {no_session_response.json()}")
print("  → 没有 Cookie 被发送！Cookie 丢失了 😢")

# ════════════════════════════════════════════
# 2. Session 级别配置
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("2️⃣  Session 级别配置")
print("=" * 40)

configured_session = requests.Session()

# 设置全局默认值
configured_session.headers.update({
    "User-Agent": "MyApp/1.0 (Session Config Demo)",
    "Accept": "application/json",
})
configured_session.timeout = 10  # 所有请求默认超时 10 秒

# 验证 header 是否生效
print("--- 全局请求头 ---")
response = configured_session.get(
    "https://httpbin.org/headers",
    timeout=10
)
headers = response.json().get("headers", {})
print(f"  User-Agent: {headers.get('User-Agent')}")
print(f"  Accept: {headers.get('Accept')}")

# 单次请求覆盖全局配置
print("\n--- 单次请求覆盖全局配置 ---")
response = configured_session.get(
    "https://httpbin.org/headers",
    headers={
        "User-Agent": "OverrideAgent/1.0",  # 这次覆盖
        "X-Trace-Id": "abc-123-def",
    },
    timeout=10
)
headers = response.json().get("headers", {})
print(f"  User-Agent (覆盖后): {headers.get('User-Agent')}")
print(f"  X-Trace-Id: {headers.get('X-Trace-Id')}")
print(f"  Accept (保留全局): {headers.get('Accept')}")
# 注意：单次 headers 不会覆盖全局的 headers，而是合并
# 如果单次指定的键与全局冲突，单次的优先

# ════════════════════════════════════════════
# 3. 连接池与重试机制
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("3️⃣  连接池与重试机制")
print("=" * 40)


def demo_retry():
    """演示重试机制"""
    retry_session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=3,                    # 最多重试 3 次
        backoff_factor=0.5,         # 等待时间: 0.5, 1, 2, 4 秒
        status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码触发重试
        allowed_methods=["GET", "POST"],  # 允许重试的方法
        raise_on_status=True,       # 最终失败时抛出异常
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,        # 连接池大小
        pool_maxsize=20,            # 最大连接数
    )

    # 挂载到 http 和 https
    retry_session.mount("http://", adapter)
    retry_session.mount("https://", adapter)

    print("重试策略已配置:")
    print(f"  总重试次数: {retry_strategy.total}")
    print(f"  退避因子: {retry_strategy.backoff_factor}")
    print(f"  触发重试的状态码: {retry_strategy.status_forcelist}")
    print(f"  连接池大小: {adapter.pool_connections}")

    # 测试重试（访问会返回 429 的端点）
    print("\n--- 测试重试 (429 Too Many Requests) ---")
    start_time = time.time()
    try:
        response = retry_session.get(
            "https://httpbin.org/status/429",
            timeout=10
        )
        print(f"最终状态码: {response.status_code}")
    except requests.exceptions.RetryError as e:
        elapsed = time.time() - start_time
        print(f"重试耗尽后失败 (耗时: {elapsed:.2f}秒)")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"其他错误: {type(e).__name__}: {e} (耗时: {elapsed:.2f}秒)")

    return retry_session


def demo_connection_pool():
    """演示连接池性能提升"""
    print("\n--- 连接池性能对比 ---")

    urls = ["https://httpbin.org/get"] * 50

    # 不使用 Session（每次新建连接）
    start = time.time()
    for url in urls[:10]:  # 只测 10 次
        requests.get(url, timeout=10)
    no_session_time = time.time() - start
    print(f"不使用 Session (10 次): {no_session_time:.3f} 秒")

    # 使用 Session（连接复用）
    pool_session = requests.Session()
    adapter = HTTPAdapter(pool_connections=5, pool_maxsize=10)
    pool_session.mount("https://", adapter)

    # 预热连接池
    for url in urls[:10]:
        pool_session.get(url, timeout=10)

    start = time.time()
    for url in urls[:10]:
        pool_session.get(url, timeout=10)
    session_time = time.time() - start
    print(f"使用 Session (10 次): {session_time:.3f} 秒")

    if no_session_time > 0:
        speedup = (no_session_time - session_time) / no_session_time * 100
        print(f"性能提升: {speedup:.1f}% 🚀")


# ════════════════════════════════════════════
# 4. 认证方式
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("4️⃣  认证方式")
print("=" * 40)

# Basic Auth (用户名:密码 → base64)
print("--- Basic Auth ---")
response = requests.get(
    "https://httpbin.org/basic-auth/user/pass",
    auth=("user", "pass"),
    timeout=10
)
print(f"Basic Auth 结果: {response.json()}")

# Bearer Token (API Key)
print("\n--- Bearer Token ---")
headers = {
    "Authorization": "Bearer fake_jwt_token_12345",
    "Content-Type": "application/json",
}
response = requests.get(
    "https://httpbin.org/bearer",
    headers=headers,
    timeout=10
)
print(f"Bearer Token 结果: {response.json()}")

# Digest Auth
print("\n--- Digest Auth ---")
response = requests.get(
    "https://httpbin.org/digest-auth/auth/user/pass",
    auth=("user", "pass"),
    timeout=10
)
print(f"Digest Auth 结果: {response.json()}")

# ════════════════════════════════════════════
# 5. 请求钩子（Hooks）
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("5️⃣  请求钩子 (Hooks)")
print("=" * 40)


def log_request(response, *args, **kwargs):
    """Hook: 记录请求信息"""
    elapsed = response.elapsed.total_seconds()
    print(f"  [Hook] {response.request.method} "
          f"{response.url} → {response.status_code} "
          f"({elapsed:.3f}s)")
    return response


def check_status(response, *args, **kwargs):
    """Hook: 检查状态码"""
    if response.status_code >= 400:
        print(f"  ⚠️  [Hook] 请求失败! Status: {response.status_code}")
    return response


# 使用 hooks
print("使用 hooks:")
response = requests.get(
    "https://httpbin.org/get",
    hooks={"response": [log_request, check_status]},
    timeout=10
)

# 测试失败请求的 hook
print("\n失败请求 hook:")
try:
    response = requests.get(
        "https://httpbin.org/status/404",
        hooks={"response": [log_request, check_status]},
        timeout=10
    )
except Exception as e:
    print(f"  异常: {e}")

# ════════════════════════════════════════════
# 6. Session 上下文管理器
# ════════════════════════════════════════════

print("\n" + "=" * 40)
print("6️⃣  Session 上下文管理器")
print("=" * 40)


class TimedSession:
    """计时 Session 包装器"""

    def __init__(self):
        self.session = requests.Session()
        self.total_time = 0.0

    def get(self, url, **kwargs):
        start = time.time()
        response = self.session.get(url, timeout=10, **kwargs)
        elapsed = time.time() - start
        self.total_time += elapsed
        print(f"  {url} → {response.status_code} ({elapsed:.3f}s)")
        return response

    def close(self):
        self.session.close()
        print(f"  Session 关闭。总耗时: {self.total_time:.3f}s")


print("使用上下文管理器 (with 语句):")
with TimedSession() as t_session:
    for i in range(5):
        t_session.get(f"https://httpbin.org/delay/0.1")

print("\n✅ Session/Cookie 高级特性演示完成！")
