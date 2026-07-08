"""
Day 057 - aiohttp 实战：异步 API 调用系统

学习要点：
1. aiohttp 会话管理
2. 并发请求与速率控制
3. 完整的 API 客户端框架
4. 错误处理与重试机制
"""

import asyncio
import aiohttp
import time
import json
from dataclasses import dataclass, field
from typing import Optional, Any


# ============================================
# 示例 1：基础 aiohttp 用法
# ============================================

async def basic_request():
    """基础 GET 请求"""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://httpbin.org/get") as resp:
            print(f"  状态码: {resp.status}")
            print(f"  Content-Type: {resp.headers.get('Content-Type')}")
            data = await resp.json()
            print(f"  URL: {data.get('url')}")


# ============================================
# 示例 2：并发请求
# ============================================

async def fetch_url(session: aiohttp.ClientSession, url: str) -> dict:
    """单个请求"""
    async with session.get(url) as resp:
        return {"url": url, "status": resp.status, "size": len(await resp.text())}


async def concurrent_requests():
    """并发请求多个 URL"""
    urls = [
        "https://httpbin.org/get?page=1",
        "https://httpbin.org/get?page=2",
        "https://httpbin.org/get?page=3",
        "https://httpbin.org/get?page=4",
        "https://httpbin.org/get?page=5",
    ]

    async with aiohttp.ClientSession() as session:
        start = time.perf_counter()
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        print(f"  并发请求 {len(urls)} 个 URL，耗时: {elapsed:.2f}s")
        for r in results:
            print(f"    {r['url']} → {r['status']} ({r['size']} bytes)")


# ============================================
# 示例 3：Semaphore 限流
# ============================================

async def rate_limited_fetch(
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    url: str,
) -> dict:
    """带限流的请求"""
    async with sem:
        start = time.perf_counter()
        async with session.get(url) as resp:
            elapsed = time.perf_counter() - start
            return {
                "url": url,
                "status": resp.status,
                "elapsed": f"{elapsed:.3f}s",
            }


async def rate_limiting_demo():
    """限流并发演示"""
    urls = [f"https://httpbin.org/get?id={i}" for i in range(10)]
    semaphore = asyncio.Semaphore(3)  # 最多 3 个并发

    async with aiohttp.ClientSession() as session:
        start = time.perf_counter()
        tasks = [rate_limited_fetch(semaphore, session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        print(f"  限流并发（最大 3），{len(urls)} 个请求，总耗时: {elapsed:.2f}s")
        # 前 3 个几乎同时完成，后面的需要等待


# ============================================
# 示例 4：POST 请求与 JSON 数据
# ============================================

async def post_example():
    """POST 请求发送 JSON 数据"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "user": "聂董",
            "action": "learn_python",
            "day": 57,
        }
        async with session.post(
            "https://httpbin.org/post",
            json=payload,
        ) as resp:
            data = await resp.json()
            print(f"  状态码: {resp.status}")
            print(f"  回显数据: {data.get('json')}")


# ============================================
# 示例 5：完整的 API 客户端
# ============================================

class SimpleAPIClient:
    """简洁的异步 API 客户端"""

    def __init__(self, base_url: str, max_concurrent: int = 5):
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        self._stats = {"total": 0, "success": 0, "failed": 0}

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            timeout=aiohttp.ClientTimeout(total=15),
        )
        return self

    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()

    async def get(self, path: str, **kwargs) -> dict:
        """带限流的 GET 请求"""
        async with self.semaphore:
            self._stats["total"] += 1
            try:
                async with self.session.get(path, **kwargs) as resp:
                    resp.raise_for_status()
                    self._stats["success"] += 1
                    return {"status": resp.status, "data": await resp.json()}
            except Exception as e:
                self._stats["failed"] += 1
                return {"status": 0, "error": str(e)}

    async def batch_get(self, paths: list[str]) -> list[dict]:
        """批量并发 GET"""
        tasks = [self.get(p) for p in paths]
        return await asyncio.gather(*tasks)

    @property
    def stats(self):
        return self._stats.copy()


# ============================================
# 示例 6：带重试的请求
# ============================================

async def fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    retries: int = 3,
) -> dict:
    """带重试和指数退避的请求"""
    for attempt in range(retries):
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return {"status": resp.status, "data": await resp.json()}
        except aiohttp.ClientError as e:
            if attempt == retries - 1:
                return {"status": 0, "error": str(e)}
            delay = 2 ** attempt
            print(f"    ⚠️ 重试 {attempt + 1}/{retries}，等待 {delay}s...")
            await asyncio.sleep(delay)


async def retry_demo():
    """重试机制演示"""
    # httpbin 的 /status/500 会返回 500 错误
    async with aiohttp.ClientSession() as session:
        result = await fetch_with_retry(
            session,
            "https://httpbin.org/get",
            retries=2,
        )
        print(f"  结果: 状态 {result.get('status')}")


# ============================================
# 主函数
# ============================================

async def main():
    print("=" * 50)
    print("示例 1：基础请求")
    print("=" * 50)
    await basic_request()

    print("\n" + "=" * 50)
    print("示例 2：并发请求")
    print("=" * 50)
    await concurrent_requests()

    print("\n" + "=" * 50)
    print("示例 3：限流并发")
    print("=" * 50)
    await rate_limiting_demo()

    print("\n" + "=" * 50)
    print("示例 4：POST 请求")
    print("=" * 50)
    await post_example()

    print("\n" + "=" * 50)
    print("示例 5：API 客户端")
    print("=" * 50)
    async with SimpleAPIClient("https://httpbin.org") as client:
        # 单个请求
        result = await client.get("/get?test=1")
        print(f"  单个请求: {result['status']}")

        # 批量请求
        paths = [f"/get?batch={i}" for i in range(5)]
        results = await client.batch_get(paths)
        print(f"  批量请求: {len(results)} 个，成功 {sum(1 for r in results if r['status'] == 200)} 个")

        # 统计
        print(f"  统计: {client.stats}")

    print("\n" + "=" * 50)
    print("示例 6：重试机制")
    print("=" * 50)
    await retry_demo()

    print("\n✅ 所有示例运行完毕")


if __name__ == "__main__":
    asyncio.run(main())
