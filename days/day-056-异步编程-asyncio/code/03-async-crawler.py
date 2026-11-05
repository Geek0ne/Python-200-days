"""
Day 056 - 异步爬虫实战
演示异步 HTTP 请求、Semaphore 限流、错误重试、超时控制
注意：需要安装 aiohttp: pip install aiohttp
"""
import asyncio
import time
from urllib.parse import urljoin

# 尝试导入 aiohttp，如果没有安装则用内置模拟
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("⚠️  未安装 aiohttp，使用模拟模式演示")
    print("   安装命令: pip install aiohttp\n")


# ============================================
# 模拟 HTTP 客户端（不依赖 aiohttp）
# ============================================
class MockResponse:
    """模拟 HTTP 响应"""
    def __init__(self, url, status=200, delay=1):
        self.url = url
        self.status = status
        self._delay = delay
    
    async def json(self):
        await asyncio.sleep(self._delay)
        return {"url": self.url, "status": self.status, "data": "mock"}
    
    async def text(self):
        await asyncio.sleep(self._delay)
        return f"Response from {self.url}"
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


class MockSession:
    """模拟 aiohttp ClientSession"""
    def get(self, url):
        delay = 0.5  # 模拟 0.5 秒延迟
        return MockResponse(url, delay=delay)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


# ============================================
# 1. 基础异步爬虫
# ============================================
async def fetch_url(session, url):
    """获取单个 URL"""
    try:
        async with session.get(url) as response:
            data = await response.json()
            return {"url": url, "status": "ok", "data": data}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


async def basic_crawler():
    """基础爬虫：并发请求多个 URL"""
    print("=== 基础异步爬虫 ===\n")
    
    urls = [
        "https://httpbin.org/get?id=1",
        "https://httpbin.org/get?id=2",
        "https://httpbin.org/get?id=3",
        "https://httpbin.org/get?id=4",
        "https://httpbin.org/get?id=5",
    ]
    
    SessionClass = aiohttp.ClientSession if HAS_AIOHTTP else MockSession
    
    start = time.time()
    async with SessionClass() as session:
        tasks = [fetch_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"请求了 {len(urls)} 个 URL")
    print(f"总耗时: {elapsed:.2f}s")
    for r in results:
        print(f"  {r['url']}: {r['status']}")
    print()


# ============================================
# 2. 带限流的爬虫（Semaphore）
# ============================================
async def fetch_with_semaphore(session, url, semaphore, stats):
    """使用信号量限制并发"""
    async with semaphore:
        stats['active'] += 1
        print(f"  [请求] {url} (当前并发: {stats['active']})")
        
        try:
            async with session.get(url) as response:
                data = await response.json()
                stats['success'] += 1
                return {"url": url, "status": "ok"}
        except Exception as e:
            stats['failed'] += 1
            return {"url": url, "status": "error", "error": str(e)}
        finally:
            stats['active'] -= 1


async def limited_crawler():
    """限流爬虫：最多 3 个并发"""
    print("=== 限流爬虫 (Semaphore) ===\n")
    
    urls = [f"https://httpbin.org/get?id={i}" for i in range(10)]
    
    # 限制同时最多 3 个请求
    semaphore = asyncio.Semaphore(3)
    stats = {"active": 0, "success": 0, "failed": 0}
    
    SessionClass = aiohttp.ClientSession if HAS_AIOHTTP else MockSession
    
    start = time.time()
    async with SessionClass() as session:
        tasks = [fetch_with_semaphore(session, url, semaphore, stats) for url in urls]
        results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"\n完成! 成功: {stats['success']}, 失败: {stats['failed']}")
    print(f"总耗时: {elapsed:.2f}s\n")


# ============================================
# 3. 带重试的爬虫
# ============================================
async def fetch_with_retry(session, url, max_retries=3):
    """带重试的请求"""
    for attempt in range(max_retries):
        try:
            async with session.get(url) as response:
                data = await response.json()
                return {"url": url, "status": "ok", "attempts": attempt + 1}
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"  重试 {url} (等待 {wait_time}s)...")
                await asyncio.sleep(wait_time)
            else:
                return {"url": url, "status": "error", "error": str(e), "attempts": attempt + 1}


async def retry_crawler():
    """带重试的爬虫"""
    print("=== 带重试的爬虫 ===\n")
    
    urls = [
        "https://httpbin.org/get?id=1",
        "https://httpbin.org/get?id=2",
        "https://httpbin.org/get?id=3",
    ]
    
    SessionClass = aiohttp.ClientSession if HAS_AIOHTTP else MockSession
    
    async with SessionClass() as session:
        tasks = [fetch_with_retry(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
    
    for r in results:
        print(f"  {r['url']}: {r['status']} (尝试 {r['attempts']} 次)")
    print()


# ============================================
# 4. 超时控制的爬虫
# ============================================
async def fetch_with_timeout(session, url, timeout=2.0):
    """带超时的请求"""
    try:
        async with asyncio.timeout(timeout):
            async with session.get(url) as response:
                data = await response.json()
                return {"url": url, "status": "ok"}
    except TimeoutError:
        return {"url": url, "status": "timeout"}
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


async def timeout_crawler():
    """超时控制爬虫"""
    print("=== 超时控制爬虫 ===\n")
    
    urls = [
        "https://httpbin.org/get?id=1",
        "https://httpbin.org/get?id=2",
        "https://httpbin.org/get?id=3",
    ]
    
    SessionClass = aiohttp.ClientSession if HAS_AIOHTTP else MockSession
    
    async with SessionClass() as session:
        tasks = [fetch_with_timeout(session, url, timeout=1.0) for url in urls]
        results = await asyncio.gather(*tasks)
    
    for r in results:
        print(f"  {r['url']}: {r['status']}")
    print()


# ============================================
# 主函数
# ============================================
async def main():
    await basic_crawler()
    await limited_crawler()
    await retry_crawler()
    await timeout_crawler()
    print("✅ 所有爬虫演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
