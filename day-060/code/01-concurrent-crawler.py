"""
Day 060 - 阶段项目：并发数据采集器
多进程 + asyncio 混合架构实现

运行方式：python3 01-concurrent-crawler.py
依赖：标准库，可选 aiohttp (pip install aiohttp)
"""

import asyncio
import multiprocessing as mp
import time
import json
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urlparse
import urllib.request
import urllib.error
import ssl

# ─── 数据模型 ───

@dataclass
class CrawlResult:
    """单次抓取结果"""
    url: str
    status: int
    content_length: int
    title: str = ""
    fetch_time_ms: float = 0.0
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.error is None and 200 <= self.status < 400

    @property
    def domain(self) -> str:
        return urlparse(self.url).netloc


# ─── Worker 进程 ───

def crawl_worker(urls: list, worker_id: int, timeout: float = 10.0):
    """
    单个 Worker 进程
    用 asyncio 并发抓取多个 URL
    """
    async def fetch_one(url):
        """抓取单个 URL"""
        start = time.perf_counter()
        try:
            # 创建不验证 SSL 的上下文（仅用于演示）
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={
                "User-Agent": "LearnPython-HPC/1.0",
                "Accept": "text/html,application/json,*/*",
            })

            # 使用 asyncio 在线程池中执行阻塞 I/O
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(req, timeout=timeout, context=ctx)
            )
            content = response.read()
            elapsed = (time.perf_counter() - start) * 1000

            return CrawlResult(
                url=url,
                status=response.status,
                content_length=len(content),
                fetch_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            return CrawlResult(
                url=url,
                status=0,
                content_length=0,
                fetch_time_ms=elapsed,
                error=str(e)[:200],
            )

    async def crawl_all():
        """并发抓取所有 URL"""
        # 每批最多同时 10 个请求
        semaphore = asyncio.Semaphore(10)

        async def limited_fetch(url):
            async with semaphore:
                return await fetch_one(url)

        tasks = [limited_fetch(url) for url in urls]
        return await asyncio.gather(*tasks)

    # 执行
    print(f"  [Worker-{worker_id}] 开始抓取 {len(urls)} 个 URL")
    results = asyncio.run(crawl_all())
    success = sum(1 for r in results if r.is_success)
    print(f"  [Worker-{worker_id}] 完成: {success}/{len(urls)} 成功")
    return results


# ─── 主协调器 ───

class ConcurrentCrawler:
    """多进程并发爬虫"""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.results = []
        self.domain_stats = {}

    def crawl(self, urls: List[str]) -> List[CrawlResult]:
        """主入口"""
        print(f"🕷️  并发抓取: {len(urls)} 个 URL, {self.max_workers} 个 Worker\n")

        # 按域名分组，均匀分配
        batches = self._distribute(urls)

        start = time.perf_counter()

        with mp.Pool(processes=self.max_workers) as pool:
            tasks = [
                pool.apply_async(crawl_worker, (batch, i))
                for i, batch in enumerate(batches)
            ]
            for task in tasks:
                worker_results = task.get(timeout=60)
                self.results.extend(worker_results)

        elapsed = time.perf_counter() - start
        self._compute_stats()
        self._print_report(elapsed)

        return self.results

    def _distribute(self, urls):
        """均匀分配 URL 到 Worker"""
        batches = [[] for _ in range(self.max_workers)]
        for i, url in enumerate(urls):
            batches[i % self.max_workers].append(url)
        return batches

    def _compute_stats(self):
        """计算域名统计"""
        for r in self.results:
            d = r.domain
            if d not in self.domain_stats:
                self.domain_stats[d] = {"total": 0, "success": 0, "bytes": 0, "time_ms": 0}
            s = self.domain_stats[d]
            s["total"] += 1
            if r.is_success:
                s["success"] += 1
            s["bytes"] += r.content_length
            s["time_ms"] += r.fetch_time_ms

    def _print_report(self, elapsed):
        """打印报告"""
        total = len(self.results)
        success = sum(1 for r in self.results if r.is_success)
        total_bytes = sum(r.content_length for r in self.results)
        avg_time = sum(r.fetch_time_ms for r in self.results) / max(total, 1)

        print(f"\n{'='*50}")
        print(f"📊 抓取报告")
        print(f"{'='*50}")
        print(f"  总耗时:       {elapsed:.2f}s")
        print(f"  总请求数:     {total}")
        print(f"  成功:         {success} ({success/max(total,1)*100:.1f}%)")
        print(f"  总数据量:     {total_bytes/1024:.1f} KB")
        print(f"  平均延迟:     {avg_time:.0f} ms/请求")
        print(f"  吞吐量:       {total/elapsed:.1f} req/s")

        print(f"\n  按域名:")
        for domain, st in sorted(self.domain_stats.items()):
            avg = st["time_ms"] / max(st["total"], 1)
            print(f"    {domain}: {st['success']}/{st['total']} "
                  f"({st['bytes']/1024:.1f}KB, avg {avg:.0f}ms)")


# ─── 演示 ───

def demo():
    # 生成测试 URL
    test_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/200",
        "https://httpbin.org/bytes/512",
        "https://httpbin.org/user-agent",
    ] * 2  # 10 个请求

    crawler = ConcurrentCrawler(max_workers=3)
    results = crawler.crawl(test_urls)

    # 保存 JSON
    output = [asdict(r) for r in results]
    with open("/tmp/crawl_results.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n💾 结果已保存到 /tmp/crawl_results.json")


if __name__ == "__main__":
    demo()
