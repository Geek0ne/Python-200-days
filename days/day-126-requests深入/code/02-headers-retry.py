"""
Day 126 - Requests 深入：请求头伪装与重试机制
02-headers-retry.py

演示 User-Agent 伪装、Referer 伪造、超时控制、自动重试
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import time


# ============================================================
# 1. User-Agent 伪装
# ============================================================

# 常见 User-Agent 列表
USER_AGENTS = [
    # Chrome - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Firefox - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari - Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge - Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Chrome - Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_random_ua():
    """随机获取 User-Agent"""
    return random.choice(USER_AGENTS)


def demo_user_agent():
    """演示 User-Agent 伪装"""
    print("=" * 60)
    print("🔧 1. User-Agent 伪装")
    print("=" * 60)

    # 基础用法
    print("\n--- 随机 User-Agent ---")
    for i in range(3):
        ua = get_random_ua()
        print(f"  [{i+1}] {ua[:60]}...")

    # 在 Session 中使用
    session = requests.Session()
    session.headers.update({"User-Agent": get_random_ua()})

    resp = session.get("https://httpbin.org/user-agent")
    print(f"\n服务器识别的 UA: {resp.json().get('user-agent', 'N/A')}")


# ============================================================
# 2. Referer 伪造
# ============================================================

def demo_referer():
    """演示 Referer 伪造"""
    print("\n" + "=" * 60)
    print("🔧 2. Referer 伪造")
    print("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": get_random_ua(),
        "Referer": "https://www.google.com/",
    })

    resp = session.get("https://httpbin.org/headers")
    headers = resp.json().get("headers", {})
    print(f"\n服务器收到的 Headers:")
    print(f"  User-Agent: {headers.get('User-Agent', 'N/A')[:50]}...")
    print(f"  Referer: {headers.get('Referer', 'N/A')}")


# ============================================================
# 3. 完整的伪装 Session
# ============================================================

def create_stealth_session():
    """创建伪装的 Session"""
    session = requests.Session()

    session.headers.update({
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7,en-GB;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    })

    return session


def demo_stealth_session():
    """演示完整的伪装 Session"""
    print("\n" + "=" * 60)
    print("🔧 3. 完整的伪装 Session")
    print("=" * 60)

    session = create_stealth_session()
    resp = session.get("https://httpbin.org/headers")
    headers = resp.json().get("headers", {})

    print("\n服务器收到的完整 Headers:")
    for key, value in sorted(headers.items()):
        print(f"  {key}: {value}")


# ============================================================
# 4. 超时控制
# ============================================================

def demo_timeout():
    """演示超时控制"""
    print("\n" + "=" * 60)
    print("🔧 4. 超时控制")
    print("=" * 60)

    # 方式一：简单超时
    print("\n--- 简单超时 (5秒) ---")
    try:
        start = time.time()
        resp = requests.get("https://httpbin.org/delay/2", timeout=5)
        elapsed = time.time() - start
        print(f"  状态: {resp.status_code}, 耗时: {elapsed:.2f}s")
    except requests.Timeout:
        print("  ⚠️ 请求超时")

    # 方式二：连接超时 + 读取超时
    print("\n--- 分离超时 (连接3s, 读取10s) ---")
    try:
        start = time.time()
        resp = requests.get("https://httpbin.org/delay/2", timeout=(3, 10))
        elapsed = time.time() - start
        print(f"  状态: {resp.status_code}, 耗时: {elapsed:.2f}s")
    except requests.Timeout:
        print("  ⚠️ 请求超时")


# ============================================================
# 5. 自动重试
# ============================================================

def demo_retry():
    """演示自动重试机制"""
    print("\n" + "=" * 60)
    print("🔧 5. 自动重试机制")
    print("=" * 60)

    # 创建带重试的 Session
    session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=3,                           # 总重试次数
        backoff_factor=0.5,                # 退避因子: 等待时间 = 0.5 * (2^(n-1))
        status_forcelist=[500, 502, 503, 504],  # 触发重试的状态码
        allowed_methods=["GET", "POST"],   # 允许重试的方法
        raise_on_status=False,             # 不因状态码抛出异常
    )

    # 配置连接适配器
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # 测试重试
    print("\n--- 测试重试 (httpbin.org/status/500) ---")
    print("  配置: total=3, backoff_factor=0.5")
    print("  预期: 重试 3 次，等待时间递增")

    start = time.time()
    try:
        resp = session.get("https://httpbin.org/status/500", timeout=10)
        elapsed = time.time() - start
        print(f"  最终状态: {resp.status_code}, 耗时: {elapsed:.2f}s")
        print("  (重试后仍然返回 500，但没有抛出异常)")
    except Exception as e:
        print(f"  ⚠️ 异常: {e}")


# ============================================================
# 6. 连接池
# ============================================================

def demo_connection_pool():
    """演示连接池复用"""
    print("\n" + "=" * 60)
    print("🔧 6. 连接池复用")
    print("=" * 60)

    import concurrent.futures

    # 创建带连接池的 Session
    session = requests.Session()
    adapter = HTTPAdapter(
        pool_connections=5,   # 连接池大小
        pool_maxsize=5,       # 最大连接数
    )
    session.mount("https://", adapter)

    def fetch(url):
        """单次请求"""
        start = time.time()
        resp = session.get(url, timeout=5)
        elapsed = time.time() - start
        return {
            "status": resp.status_code,
            "elapsed": round(elapsed, 3),
        }

    # 串行请求
    print("\n--- 串行请求 (5次) ---")
    start = time.time()
    results = [fetch("https://httpbin.org/get") for _ in range(5)]
    serial_time = time.time() - start
    print(f"  总耗时: {serial_time:.3f}s")
    for i, r in enumerate(results):
        print(f"  [{i+1}] 状态: {r['status']}, 耗时: {r['elapsed']}s")

    # 并发请求（连接池复用）
    print("\n--- 并发请求 (5次) ---")
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch, "https://httpbin.org/get") for _ in range(5)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    concurrent_time = time.time() - start
    print(f"  总耗时: {concurrent_time:.3f}s")
    for i, r in enumerate(results):
        print(f"  [{i+1}] 状态: {r['status']}, 耗时: {r['elapsed']}s")

    print(f"\n  性能提升: {(1 - concurrent_time/serial_time) * 100:.1f}%")


# ============================================================
# 7. 主流程
# ============================================================

def main():
    print("🚀 Day 126 - Requests 深入：请求头伪装与重试机制\n")

    try:
        demo_user_agent()
    except Exception as e:
        print(f"⚠️ 错误: {e}")

    try:
        demo_referer()
    except Exception as e:
        print(f"⚠️ 错误: {e}")

    try:
        demo_stealth_session()
    except Exception as e:
        print(f"⚠️ 错误: {e}")

    try:
        demo_timeout()
    except Exception as e:
        print(f"⚠️ 错误: {e}")

    try:
        demo_retry()
    except Exception as e:
        print(f"⚠️ 错误: {e}")

    try:
        demo_connection_pool()
    except Exception as e:
        print(f"⚠️ 错误: {e}")

    print("\n" + "=" * 60)
    print("✅ 请求头伪装与重试机制演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
