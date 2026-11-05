#!/usr/bin/env python3
"""
Day 141 示例 01 — 指数退避重试器（基础用法 + 原理演示）

纯标准库实现指数退避 + 抖动，并演示 requests/urllib3 内置重试的用法。
可直接运行: python3 01-retry-backoff.py
"""
import random
import time
from urllib.request import urlopen
from urllib.error import URLError


# ========== 1. 手写指数退避重试装饰器（理解原理） ==========
def retry_with_backoff(max_attempts=4, base=1.0, max_delay=30.0,
                       retry_on=(ConnectionError, TimeoutError, URLError)):
    """指数退避重试装饰器。

    delay = base * (2 ** attempt) + random jitter
    - base=1: 1s, 2s, 4s, 8s... 指数增长
    - jitter: 随机抖动，避免多个客户端同步重试（惊群效应）
    - 只对"暂时性错误"重试；4xx 类逻辑错误重试无意义
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        break  # 最后一次失败，放弃
                    delay = min(base * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    print(f"  [重试] 第 {attempt + 1} 次失败: {e!r}，"
                          f"{delay:.1f}s 后重试")
                    time.sleep(delay)
            raise last_exc  # 抛出最后的异常，由上层决定是否进死信队列
        return wrapper
    return decorator


# ========== 2. 模拟一个不稳定的服务 ==========
class FlakyService:
    """前 3 次调用都失败，第 4 次成功 —— 模拟服务过载后恢复。"""
    def __init__(self, fail_times=3):
        self.calls = 0
        self.fail_times = fail_times

    @retry_with_backoff(max_attempts=5)
    def fetch(self, url: str) -> str:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError(f"connection refused (attempt {self.calls})")
        return f"OK: data from {url}"


# ========== 3. requests 内置重试（生产推荐） ==========
def demo_requests_retry():
    """生产环境用 urllib3 Retry + HTTPAdapter，无需手写。

    关键点：
    - status_forcelist: 只对 5xx 重试（4xx 是逻辑错误，重试无意义）
    - allowed_methods: 只对幂等方法重试，POST 重试可能造成重复下单
    - backoff_factor: 退避基数
    """
    try:
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
    except ImportError:
        print("\n[跳过] 未安装 requests，先 pip install requests")
        return

    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 请求一个必然 404 的地址：404 不在 forcelist 中，不会重试
    try:
        resp = session.get("https://httpbin.org/status/404", timeout=10)
        print(f"\n[requests重试] 状态码 {resp.status_code}（404 不触发重试，直接返回）")
    except Exception as e:
        print(f"\n[requests重试] 请求异常: {e!r}")


if __name__ == "__main__":
    print("=" * 50)
    print("演示 1: 手写指数退避（模拟不稳定服务）")
    print("=" * 50)
    svc = FlakyService(fail_times=3)
    result = svc.fetch("https://example.com/api/data")
    print(f"最终结果: {result}")

    print("\n" + "=" * 50)
    print("演示 2: requests 内置重试")
    print("=" * 50)
    # 缩短 sleep 演示，避免运行太久
    demo_requests_retry()
    print("\n✅ 重试演示完成。核心: 指数退避 + 抖动 + 只重试暂时性错误")
