"""
Day 054 — 实战：并发下载器
使用 concurrent.futures 实现高效的并发下载
"""

import urllib.request
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadResult:
    url: str
    size: int = 0
    status: DownloadStatus = DownloadStatus.PENDING
    error: Optional[str] = None
    elapsed: float = 0.0


class ConcurrentDownloader:
    """线程安全的并发下载器"""
    
    def __init__(self, max_workers=3, timeout=10):
        self.max_workers = max_workers
        self.timeout = timeout
        self.results: List[DownloadResult] = []
        self._lock = threading.Lock()
        self._completed_count = 0
        self._total = 0
    
    def _download_one(self, url: str) -> DownloadResult:
        """下载单个 URL"""
        result = DownloadResult(url=url)
        result.status = DownloadStatus.DOWNLOADING
        start = time.time()
        
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'PythonDownloader/1.0'}
            )
            response = urllib.request.urlopen(req, timeout=self.timeout)
            data = response.read()
            
            result.size = len(data)
            result.status = DownloadStatus.COMPLETED
            result.elapsed = time.time() - start
            
        except Exception as e:
            result.status = DownloadStatus.FAILED
            result.error = str(e)
            result.elapsed = time.time() - start
        
        with self._lock:
            self._completed_count += 1
            self._print_progress(url, result)
        
        return result
    
    def _print_progress(self, url: str, result: DownloadResult):
        """打印下载进度"""
        icon = "✓" if result.status == DownloadStatus.COMPLETED else "✗"
        status = "ok" if result.status == DownloadStatus.COMPLETED else result.error
        print(
            f"  [{self._completed_count}/{self._total}] {icon} "
            f"{url} — {result.size:,} bytes ({result.elapsed:.2f}s) [{status}]"
        )
    
    def download(self, urls: List[str]) -> List[DownloadResult]:
        """并发下载所有 URL"""
        self.results = []
        self._completed_count = 0
        self._total = len(urls)
        
        print(f"🚀 开始并发下载 {len(urls)} 个 URL (最大并发: {self.max_workers})\n")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self._download_one, url): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                result = future.result()
                self.results.append(result)
        
        return self.results
    
    def get_summary(self) -> dict:
        """获取下载统计"""
        ok = [r for r in self.results if r.status == DownloadStatus.COMPLETED]
        fail = [r for r in self.results if r.status == DownloadStatus.FAILED]
        
        total_size = sum(r.size for r in ok)
        total_time = sum(r.elapsed for r in self.results)
        avg_time = total_time / len(self.results) if self.results else 0
        
        return {
            "total": len(self.results),
            "success": len(ok),
            "failed": len(fail),
            "total_size": total_size,
            "total_time": total_time,
            "avg_time": avg_time,
            "throughput": total_size / total_time if total_time > 0 else 0,
        }


# ============================================================
# 实际运行
# ============================================================

if __name__ == "__main__":
    # 测试 URL（使用 httpbin 模拟延迟）
    urls = [
        "https://httpbin.org/delay/0.5",
        "https://httpbin.org/delay/0.8",
        "https://httpbin.org/delay/1.0",
        "https://httpbin.org/delay/0.3",
        "https://httpbin.org/delay/0.6",
        "https://httpbin.org/bytes/1024",
        "https://httpbin.org/bytes/2048",
        "https://httpbin.org/status/200",
    ]
    
    # 下载
    downloader = ConcurrentDownloader(max_workers=4)
    start = time.time()
    results = downloader.download(urls)
    total_elapsed = time.time() - start
    
    # 统计
    summary = downloader.get_summary()
    
    print(f"\n{'='*50}")
    print(f"📊 下载统计:")
    print(f"  总任务数: {summary['total']}")
    print(f"  成功: {summary['success']}, 失败: {summary['failed']}")
    print(f"  总大小: {summary['total_size']:,} bytes")
    print(f"  实际耗时: {total_elapsed:.2f}s")
    print(f"  平均单任务耗时: {summary['avg_time']:.2f}s")
    print(f"  吞吐量: {summary['throughput']:,.0f} bytes/s")
    print(f"{'='*50}")
    
    # 如果同步下载会花多久？
    serial_time = sum(r.elapsed for r in results)
    print(f"\n  如果同步下载需要: ~{serial_time:.1f}s")
    print(f"  并发加速比: {serial_time / total_elapsed:.1f}x")
