# Day 060 — 阶段项目：高性能计算

> 综合运用 Phase 4 知识，用并发 + C 扩展解决真实计算问题

## 📋 今日学习目标

1. 综合运用多线程、多进程、异步编程解决实际问题
2. 实现并发数据采集 + 高性能图像处理管道
3. 掌握生产级高性能计算的最佳实践
4. 理解如何评估和优化计算密集型任务

---

## 一、项目概述

### 项目 1：并发数据爬虫

用多进程 + asyncio 实现高效数据采集：

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  URL 队列    │───→│  Worker 进程 │───→│  结果聚合    │
│  (共享)      │    │  (多个)     │    │  (去重存储)  │
└─────────────┘    └─────────────┘    └─────────────┘
      │                   │
      │            ┌──────▼──────┐
      └───────────→│  asyncio    │
                   │  (每个进程  │
                   │  内部并发)  │
                   └─────────────┘
```

### 项目 2：高性能图像处理

用 Numba + 多进程实现图像批处理管道：

```
原图 → [灰度转换] → [高斯模糊] → [边缘检测] → [保存结果]
         Numba        Numba       Numba      多进程并行
```

---

## 二、项目 1：并发数据采集器

### 架构设计

```python
"""
并发数据采集器架构：

主进程 (Coordinator)
├── 管理 URL 队列
├── 分发任务给 Worker
└── 聚合结果

Worker 进程 (multiprocessing.Pool)
├── 每个进程内部用 asyncio 并发
├── aiohttp 做 HTTP 请求
└── 返回结构化结果
"""
```

### 完整实现

```python
"""
文件: 01-concurrent-crawler.py
并发数据采集器 — 多进程 + asyncio 混合架构
"""

import asyncio
import multiprocessing as mp
from multiprocessing import Queue, Manager
import time
import json
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import urlparse

# ─── 数据模型 ───

@dataclass
class CrawlResult:
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
    单个 Worker 进程：用 asyncio 并发抓取多个 URL
    每个进程有自己的事件循环，避免 GIL 竞争
    """
    async def fetch_one(session, url, timeout):
        """抓取单个 URL"""
        start = time.perf_counter()
        try:
            async with session.get(url, timeout=timeout) as resp:
                content = await resp.read()
                text = await resp.text()
                # 简单提取 title
                title = ""
                if "<title>" in text.lower():
                    start_idx = text.lower().find("<title>") + 7
                    end_idx = text.lower().find("</title>")
                    if end_idx > start_idx:
                        title = text[start_idx:end_idx].strip()[:100]

                elapsed = (time.perf_counter() - start) * 1000
                return CrawlResult(
                    url=url,
                    status=resp.status,
                    content_length=len(content),
                    title=title,
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

    async def crawl_all(urls):
        """并发抓取所有 URL"""
        try:
            import aiohttp
        except ImportError:
            # 降级到 urllib
            return crawl_with_urllib(urls)

        connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        results = []

        async with aiohttp.ClientSession(connector=connector, timeout=timeout_config) as session:
            tasks = [fetch_one(session, url, timeout) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if isinstance(r, CrawlResult)]

    def crawl_with_urllib(urls):
        """降级方案：用标准库 urllib"""
        import urllib.request
        import urllib.error
        results = []
        for url in urls:
            start = time.perf_counter()
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "LearnPython/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    content = resp.read()
                    elapsed = (time.perf_counter() - start) * 1000
                    results.append(CrawlResult(
                        url=url,
                        status=resp.status,
                        content_length=len(content),
                        fetch_time_ms=elapsed,
                    ))
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                results.append(CrawlResult(
                    url=url, status=0, content_length=0,
                    fetch_time_ms=elapsed, error=str(e)[:200],
                ))
        return results

    # 执行抓取
    print(f"  [Worker-{worker_id}] 开始抓取 {len(urls)} 个 URL")
    results = asyncio.run(crawl_all(urls))
    success = sum(1 for r in results if r.is_success)
    print(f"  [Worker-{worker_id}] 完成: {success}/{len(urls)} 成功")
    return results


# ─── 主协调器 ───

class ConcurrentCrawler:
    """多进程并发爬虫协调器"""

    def __init__(self, max_workers: int = 4, urls_per_batch: int = 10):
        self.max_workers = max_workers
        self.urls_per_batch = urls_per_batch
        self.results = []
        self.domain_stats = {}

    def crawl(self, urls: List[str]) -> List[CrawlResult]:
        """主入口：分配 URL 给多个 Worker 进程"""
        print(f"🕷️  开始并发抓取: {len(urls)} 个 URL, {self.max_workers} 个 Worker")

        # 按域名分组，避免对同一域名施加过大压力
        batches = self._distribute_urls(urls)

        start = time.perf_counter()

        # 多进程并行
        with mp.Pool(processes=self.max_workers) as pool:
            tasks = []
            for worker_id, batch in enumerate(batches):
                result = pool.apply_async(crawl_worker, (batch, worker_id))
                tasks.append(result)

            # 收集结果
            for task in tasks:
                worker_results = task.get(timeout=30)
                self.results.extend(worker_results)

        elapsed = time.perf_counter() - start
        self._compute_stats()

        print(f"\n📊 抓取完成: {elapsed:.2f}s")
        self._print_stats()

        return self.results

    def _distribute_urls(self, urls):
        """将 URL 分配到多个批次"""
        # 按域名分组
        domain_groups = {}
        for url in urls:
            domain = urlparse(url).netloc
            domain_groups.setdefault(domain, []).append(url)

        # 轮询分配到 Worker
        batches = [[] for _ in range(self.max_workers)]
        for domain_urls in domain_groups.values():
            for i, url in enumerate(domain_urls):
                batches[i % self.max_workers].append(url)

        # 如果某些 Worker 没有任务，从其他 Worker 借
        all_urls = []
        for b in batches:
            all_urls.extend(b)

        # 重新均匀分配
        batches = [[] for _ in range(self.max_workers)]
        for i, url in enumerate(all_urls):
            batches[i % self.max_workers].append(url)

        return batches

    def _compute_stats(self):
        """计算统计信息"""
        for result in self.results:
            domain = result.domain
            if domain not in self.domain_stats:
                self.domain_stats[domain] = {
                    "total": 0, "success": 0,
                    "total_bytes": 0, "total_time_ms": 0,
                }
            stats = self.domain_stats[domain]
            stats["total"] += 1
            if result.is_success:
                stats["success"] += 1
            stats["total_bytes"] += result.content_length
            stats["total_time_ms"] += result.fetch_time_ms

    def _print_stats(self):
        """打印统计报告"""
        total = len(self.results)
        success = sum(1 for r in self.results if r.is_success)
        total_bytes = sum(r.content_length for r in self.results)
        avg_time = sum(r.fetch_time_ms for r in self.results) / max(total, 1)

        print(f"  总请求数:   {total}")
        print(f"  成功数:     {success} ({success/max(total,1)*100:.1f}%)")
        print(f"  总数据量:   {total_bytes/1024:.1f} KB")
        print(f"  平均耗时:   {avg_time:.0f} ms/请求")

        print("\n  按域名统计:")
        for domain, stats in sorted(self.domain_stats.items()):
            print(f"    {domain}: {stats['success']}/{stats['total']} "
                  f"({stats['total_bytes']/1024:.1f}KB, "
                  f"avg {stats['total_time_ms']/max(stats['total'],1):.0f}ms)")


# ─── 演示 ───

def demo():
    # 模拟 URL 列表（实际使用时替换为真实 URL）
    demo_urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/status/200",
        "https://httpbin.org/status/404",
        "https://httpbin.org/bytes/1024",
    ] * 3  # 重复 3 次模拟 15 个请求

    crawler = ConcurrentCrawler(max_workers=3, urls_per_batch=5)
    results = crawler.crawl(demo_urls)

    # 保存结果
    output = [asdict(r) for r in results]
    print(f"\n前 3 条结果:")
    for r in output[:3]:
        print(f"  {r['url'][:50]}... → {r['status']} ({r['fetch_time_ms']:.0f}ms)")


if __name__ == "__main__":
    demo()
```

---

## 三、项目 2：高性能图像处理管道

### 架构设计

```
┌──────────────────────────────────────────────────────┐
│                   图像处理管道                         │
├──────────────────────────────────────────────────────┤
│                                                      │
│  输入图像                                             │
│     │                                                │
│     ▼                                                │
│  ┌──────────────┐                                    │
│  │ Numba: 灰度  │  @jit(nopython=True, parallel=True)│
│  └──────┬───────┘                                    │
│         ▼                                            │
│  ┌──────────────┐                                    │
│  │ Numba: 模糊  │  高斯核卷积                          │
│  └──────┬───────┘                                    │
│         ▼                                            │
│  ┌──────────────┐                                    │
│  │ Numba: 边缘  │  Sobel 算子                        │
│  └──────┬───────┘                                    │
│         ▼                                            │
│  ┌──────────────┐                                    │
│  │ 多进程: 并行  │  多张图同时处理                      │
│  └──────┬───────┘                                    │
│         ▼                                            │
│  输出结果                                             │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 完整实现

```python
"""
文件: 02-image-pipeline.py
高性能图像处理管道 — Numba 加速 + 多进程并行
"""

import time
import os
import multiprocessing as mp
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

# ─── 尝试导入 Numba（可选）───
try:
    from numba import jit, prange
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False
    print("⚠️  Numba 未安装，使用纯 NumPy 版本")


# ─── 图像处理函数 ───

def to_grayscale(pixels: np.ndarray) -> np.ndarray:
    """RGB → 灰度 (ITU-R BT.601)"""
    if HAS_NUMBA:
        return _grayscale_numba(pixels)
    return _grayscale_numpy(pixels)


def _grayscale_numpy(pixels):
    return (0.299 * pixels[:, :, 0] +
            0.587 * pixels[:, :, 1] +
            0.114 * pixels[:, :, 2])


if HAS_NUMBA:
    @jit(nopython=True, parallel=True)
    def _grayscale_numba(pixels):
        h, w = pixels.shape[:2]
        gray = np.empty((h, w), dtype=np.float64)
        for y in prange(h):
            for x in range(w):
                gray[y, x] = (0.299 * pixels[y, x, 0] +
                              0.587 * pixels[y, x, 1] +
                              0.114 * pixels[y, x, 2])
        return gray


def gaussian_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """高斯模糊"""
    if HAS_NUMBA:
        return _blur_numba(image, kernel_size)
    return _blur_numpy(image, kernel_size)


def _blur_numpy(image, kernel_size):
    """NumPy 卷积模糊"""
    # 生成高斯核
    ax = np.arange(kernel_size) - kernel_size // 2
    xx, yy = np.meshgrid(ax, ax)
    kernel = np.exp(-(xx**2 + yy**2) / (2 * (kernel_size/3)**2))
    kernel /= kernel.sum()

    h, w = image.shape
    pad = kernel_size // 2
    padded = np.pad(image, pad, mode='reflect')

    result = np.zeros_like(image)
    for i in range(h):
        for j in range(w):
            result[i, j] = np.sum(padded[i:i+kernel_size, j:j+kernel_size] * kernel)

    return result


if HAS_NUMBA:
    @jit(nopython=True, parallel=True)
    def _blur_numba(image, kernel_size):
        ax = np.arange(kernel_size, dtype=np.float64) - kernel_size // 2
        kernel = np.zeros((kernel_size, kernel_size), dtype=np.float64)
        sigma = kernel_size / 3.0
        for i in range(kernel_size):
            for j in range(kernel_size):
                kernel[i, j] = np.exp(-(ax[i]**2 + ax[j]**2) / (2 * sigma**2))
        kernel /= kernel.sum()

        h, w = image.shape
        pad = kernel_size // 2
        result = np.zeros_like(image)

        for y in prange(h):
            for x in range(w):
                s = 0.0
                for ky in range(kernel_size):
                    for kx in range(kernel_size):
                        s += image[y + ky, x + kx] * kernel[ky, kx]
                result[y, x] = s
        return result


def edge_detect(image: np.ndarray) -> np.ndarray:
    """Sobel 边缘检测"""
    if HAS_NUMBA:
        return _edge_numba(image)
    return _edge_numpy(image)


def _edge_numpy(image):
    """NumPy Sobel 边缘检测"""
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
    sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)

    h, w = image.shape
    gx = np.zeros_like(image)
    gy = np.zeros_like(image)

    for y in range(1, h - 1):
        for x in range(1, w - 1):
            patch = image[y-1:y+2, x-1:x+2]
            gx[y, x] = np.sum(patch * sobel_x)
            gy[y, x] = np.sum(patch * sobel_y)

    return np.sqrt(gx**2 + gy**2)


if HAS_NUMBA:
    @jit(nopython=True, parallel=True)
    def _edge_numba(image):
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float64)
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float64)

        h, w = image.shape
        gx = np.zeros_like(image)
        gy = np.zeros_like(image)

        for y in prange(1, h - 1):
            for x in range(1, w - 1):
                s_x = 0.0
                s_y = 0.0
                for ky in range(3):
                    for kx in range(3):
                        s_x += image[y + ky - 1, x + kx - 1] * sobel_x[ky, kx]
                        s_y += image[y + ky - 1, x + kx - 1] * sobel_y[ky, kx]
                gx[y, x] = s_x
                gy[y, x] = s_y

        return np.sqrt(gx**2 + gy**2)


# ─── 处理管道 ───

@dataclass
class ImageTask:
    """单张图像的处理任务"""
    task_id: int
    pixels: np.ndarray  # shape (H, W, 3)
    output_dir: str


@dataclass
class ImageResult:
    """处理结果"""
    task_id: int
    original_shape: tuple
    processed_shape: tuple
    process_time_ms: float
    output_files: List[str]


def process_single_image(task: ImageTask) -> ImageResult:
    """
    处理单张图像的完整管道
    grayscale → blur → edge_detect
    """
    start = time.perf_counter()

    # 管道处理
    gray = to_grayscale(task.pixels)
    blurred = gaussian_blur(gray, kernel_size=5)
    edges = edge_detect(blurred)

    elapsed = (time.perf_counter() - start) * 1000

    return ImageResult(
        task_id=task.task_id,
        original_shape=task.pixels.shape,
        processed_shape=edges.shape,
        process_time_ms=elapsed,
        output_files=[],  # 实际项目中会保存文件
    )


# ─── 多进程批处理 ───

class ImageProcessor:
    """高性能图像批处理器"""

    def __init__(self, num_workers: int = None):
        self.num_workers = num_workers or mp.cpu_count()
        print(f"🖼️  图像处理器: {self.num_workers} 个 Worker")

    def process_batch(self, images: List[np.ndarray], output_dir: str = "/tmp") -> List[ImageResult]:
        """批量处理图像"""
        tasks = [
            ImageTask(task_id=i, pixels=img, output_dir=output_dir)
            for i, img in enumerate(images)
        ]

        print(f"  处理 {len(tasks)} 张图像...")

        start = time.perf_counter()

        # 多进程并行
        with mp.Pool(processes=self.num_workers) as pool:
            results = pool.map(process_single_image, tasks)

        total_time = time.perf_counter() - start
        total_proc = sum(r.process_time_ms for r in results)

        print(f"  总耗时: {total_time:.2f}s")
        print(f"  处理时间之和: {total_proc:.0f}ms")
        print(f"  并行加速比: {total_proc / (total_time * 1000):.1f}x")

        return results


# ─── 性能基准测试 ───

def benchmark():
    print("=" * 60)
    print("高性能图像处理管道 — 性能测试")
    print("=" * 60)

    # 生成模拟图像
    sizes = [(256, 256), (512, 512), (1024, 1024)]
    num_images = 4

    for h, w in sizes:
        print(f"\n--- 图像尺寸: {h}×{w}, 数量: {num_images} ---")

        images = [np.random.randint(0, 256, (h, w, 3), dtype=np.float64)
                  for _ in range(num_images)]

        # 预热（Numba 首次编译）
        if HAS_NUMBA:
            _ = process_single_image(ImageTask(0, images[0], "/tmp"))

        processor = ImageProcessor(num_workers=2)
        results = processor.process_batch(images)

        for r in results:
            print(f"  Image {r.task_id}: {r.process_time_ms:.0f}ms")


if __name__ == "__main__":
    benchmark()
    print("\n✅ 图像处理管道测试完成！")
```

---

## 四、生产级最佳实践

### 1. 错误处理

```python
from concurrent.futures import ProcessPoolExecutor, as_completed

def robust_crawl(urls, max_workers=4):
    """健壮的并发爬虫"""
    results = []
    errors = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(crawl_one, url): url for url in urls}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result(timeout=30)
                results.append(result)
            except Exception as e:
                errors.append({"url": url, "error": str(e)})

    print(f"成功: {len(results)}, 失败: {len(errors)}")
    return results, errors
```

### 2. 进程间通信

```python
from multiprocessing import Queue, Process

def producer(queue, items):
    """生产者：生成任务"""
    for item in items:
        queue.put(item)
    queue.put(None)  # 哨兵值

def consumer(queue, results):
    """消费者：处理任务"""
    while True:
        item = queue.get()
        if item is None:
            break
        results.append(process(item))
```

### 3. 内存管理

```python
# ❌ 避免：大量数据在进程间复制
def bad_example():
    big_data = np.random.rand(10_000_000)  # ~80MB
    with ProcessPoolExecutor() as pool:
        # 每个 Worker 都会复制一份 big_data！
        results = pool.map(process, [big_data] * 10)

# ✅ 正确：用共享内存
from multiprocessing import shared_memory

def good_example():
    big_data = np.random.rand(10_000_000)
    shm = shared_memory.SharedMemory(create=True, size=big_data.nbytes)
    shared_array = np.ndarray(big_data.shape, dtype=big_data.dtype, buffer=shm.buf)
    shared_array[:] = big_data[:]
    # 共享内存，不会复制
```

### 4. 监控与日志

```python
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hpc")

def monitored_task(task_id):
    """带监控的任务"""
    logger.info(f"Task {task_id} 开始: {datetime.now()}")
    start = time.perf_counter()
    try:
        result = process(task_id)
        elapsed = time.perf_counter() - start
        logger.info(f"Task {task_id} 完成: {elapsed:.2f}s")
        return result
    except Exception as e:
        logger.error(f"Task {task_id} 失败: {e}")
        raise
```

---

## 五、性能评估框架

### 基准测试方法

```python
def benchmark_function(func, *args, n_runs=10, warmup=2):
    """通用基准测试"""
    # 预热
    for _ in range(warmup):
        func(*args)

    # 正式测试
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        result = func(*args)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    times.sort()
    return {
        "mean": sum(times) / len(times),
        "median": times[len(times) // 2],
        "min": times[0],
        "max": times[-1],
        "p95": times[int(len(times) * 0.95)],
    }
```

### Amdahl 定律

```
加速比 = 1 / ((1 - P) + P/N)

P = 可并行化的比例
N = 处理器数量

例：90% 可并行，4 个 CPU
加速比 = 1 / (0.1 + 0.9/4) = 1 / 0.325 ≈ 3.08x

上限：即使 100 个 CPU，加速比也只有 1/0.1 = 10x
```

---

## 六、思考题

1. **架构题**：在并发爬虫中，为什么选择「多进程 + 进程内 asyncio」而不是「纯 asyncio」或「纯多进程」？

**参考答案**

先解释两个术语：**GIL（全局解释器锁）**是 CPython 的一把锁，同一时刻只允许一个线程执行 Python 字节码，所以多线程对「CPU 密集」任务几乎没有加速；**协程（coroutine）**是一种能在等待时主动让出、由「事件循环」统一调度的轻量函数，切换开销远小于线程/进程。

爬虫的负载是「I/O 密集为主、夹带少量 CPU」：大部分时间在等网络响应（I/O），但解析 HTML、提取 title、TLS 加解密、结果序列化也要吃 CPU。三种方案的取舍：

- **纯 asyncio（单进程）**：一个事件循环就能并发成千上万个连接，I/O 效率极高；但所有 CPU 工作都挤在一个核上，核数再多也用不上，且任何一处阻塞调用会卡住整个循环。URL 多、解析重时，单核成为瓶颈。
- **纯多进程（每进程同步阻塞抓取）**：能真正吃满多核，但进程内若串行抓 URL，「并发连接数 ≈ 进程数」。要维持几千个并发连接就得开几千个进程，创建/切换/内存开销巨大，不现实。
- **多进程 + 进程内 asyncio（本项目）**：用「≈CPU 核数」个进程吃满多核做 CPU 部分，每个进程内再用 asyncio + aiohttp 维持大量并发连接做 I/O 部分。两层并发叠加：进程级「并行」利用多核，协程级「并发」利用 I/O 等待，既绕开 GIL，又避免进程爆炸。

下面用标准库模拟「进程内 asyncio 并发 I/O」的效果（5 个各等待 0.1s 的任务，总耗时接近 0.1s 而非 0.5s）：

```python
import asyncio, time

async def fetch(i):
    await asyncio.sleep(0.1)   # 模拟一次网络等待（I/O）
    return i

async def main():
    start = time.perf_counter()
    results = await asyncio.gather(*(fetch(i) for i in range(5)))
    print("结果:", results)
    print(f"5 个各 0.1s 的任务，总耗时约 {time.perf_counter()-start:.2f}s")

asyncio.run(main())
```

预期输出：`结果: [0, 1, 2, 3, 4]`，总耗时约 `0.1s`（因机器/版本而异）。这说明协程在等待 I/O 时互相让出，单进程内就能把多个网络请求「叠」在一起；而要吃满多核做解析，仍需外层多进程。

⚠️ 注意：进程内 asyncio 只解决 I/O 并发，不解决 CPU 并行；CPU 密集部分必须靠多进程。Windows/macOS 默认用 spawn 启动子进程，worker 函数要可被 pickle 且调用放在 `if __name__ == "__main__":` 保护下。

2. **性能题**：图像处理管道中，灰度转换用 Numba 并行，但高斯模糊用串行。分析这种设计的合理性。

**参考答案**

⚠️ 注意：先澄清一个与代码不符的前提。本 README 给出的 `_grayscale_numba`、`_blur_numba`、`_edge_numba` 三个内核其实都用了 `@jit(nopython=True, parallel=True)` + `prange`，都是并行的。所以「模糊用串行」并不符合现有代码；下面按「如果把模糊改成串行，是否合理」来分析，这也是本题真正想考的点。

把内层模糊设为串行，在「外层已经多进程并行」时往往是对的，原因：

- **避免嵌套并行 / 超额订阅（oversubscription）**：外层已用 `mp.Pool(num_workers)` 按「图像之间」并行。若每张图内部的模糊再用 Numba 开满线程，总线程数 ≈ `num_workers × CPU 核数`，远超物理核数，线程互相争抢、频繁上下文切换、缓存失效，反而更慢。让并行只发生在「图像之间」这一层、内层串行，是常见且合理的做法。
- **模糊是访存密集（memory-bound）**：每个输出像素要读 `kernel_size²` 个输入像素，算术量小、访存量大。多核一起跑时大家抢同一条内存带宽，并行收益有限；灰度转换计算更简单、更易向量化，并行的性价比相对更高。
- **粒度与开销**：卷积输出像素之间其实相互独立（读输入邻域、写各自输出），本质可并行；但小图上 `prange` 的线程启动/调度开销可能超过收益，串行更简单也不易在边界处理上出错。

结论：是否串行取决于「外层是否已并行」和「图像大小」。本项目外层已多进程并行，内层模糊串行可避免超额订阅，是合理选择；若改成单进程处理一张大图，则模糊并行更能吃满多核。

💡 提示：Numba 的 `parallel=True` 只对使用 `prange` 的循环真正生效，把 `prange` 换成 `range` 即退回串行；可用环境变量 `NUMBA_NUM_THREADS` 限制内层线程数，避免与外层进程数相乘导致超额订阅。

3. **扩展题**：如果要处理 10 万张图像（每张 4K 分辨率），如何设计内存管理策略？

**参考答案**

先估算量级：4K ≈ 3840×2160 ≈ 830 万像素，×3 通道 ≈ 2500 万个值。用 `uint8` 存约 25MB/张，用 `float64` 约 200MB/张。10 万张就是 2.5TB（uint8）到 20TB（float64）——绝不可能一次性载入内存（数字因分辨率/编码而异）。核心思路是「让内存占用只和并发数有关，与总张数无关」：

- **流式 / 惰性加载**：用生成器一次只读一张（或一小批），处理完立即释放，绝不写 `images = [load(p) for p in 全部路径]`。
- **分批 + 有界队列（背压）**：用 `Pool.imap(func, 生成器, chunksize=...)` 惰性消费，或限制 `ProcessPoolExecutor` 的在途任务数，避免生产者把 10 万个大数组一次性塞进队列撑爆内存。
- **选对 dtype**：原始像素用 `uint8`（0–255）而非 `float64`，内存差 8 倍；只在必要的中间步骤临时转 float，算完转回或释放。
- **共享内存 / 内存映射**：大数组用 `multiprocessing.shared_memory` 或 `np.memmap`（内存映射文件）让多进程零拷贝共享；进程间传「文件路径 / 共享内存名」而不是数组本身，避免 pickle 复制。
- **及时释放 + 限制并发 + 结果落盘**：worker 数 ≈ CPU 核数；用 `maxtasksperchild`（Pool）/ `max_tasks_per_child`（Executor，3.11+）定期重启 worker 回收内存；边缘图等结果直接写磁盘，内存里只留统计量。

下面用标准库演示「流式处理」的核心（生成器惰性产出，内存里同一时刻只有一张）：

```python
def load_one(i):
    # 模拟加载一张 4K 图（真实用图像库/np.load），这里只返回一个小标记
    return f"image_{i}"

def process(img):
    return len(img)

def image_stream(n):
    for i in range(n):
        yield load_one(i)      # 关键：yield 惰性产出，不建列表

# 流式处理 10 万张：内存里同一时刻只有 1 张
total = 0
for img in image_stream(100_000):
    total += process(img)
    # img 离开本次循环后即可被回收
print("处理张数累计长度:", total)
```

预期输出：`处理张数累计长度: 1088890`。无论处理 10 万还是 100 万张，内存峰值都只取决于「同时驻留的图像数」，而不是总量；真实项目把 `for` 循环换成 `pool.imap(process, image_stream(N), chunksize=8)` 即可在保持低内存的同时并行。

⚠️ 注意：4K 单张 float64 约 200MB，若 `num_workers=8` 且每个 worker 同时持有多张，峰值可达数 GB；务必 uint8 + 流式 + 限制在途任务数。示例数字因机器/分辨率而异。

4. **对比题**：`multiprocessing.Pool` 和 `concurrent.futures.ProcessPoolExecutor` 在这个场景下有什么区别？选哪个？

**参考答案**

两者都能多进程并行，区别在 API 风格与控制粒度：

- **接口风格**：`Pool` 是老牌低级 API，用 `map / imap / imap_unordered / apply_async`；`ProcessPoolExecutor` 是更现代的高级 API，与 `ThreadPoolExecutor` 统一，`submit` 返回 **Future（代表「将来才有结果」的对象）**，配合 `as_completed` 按完成顺序取结果。
- **超时与逐任务异常**：Executor 的 `future.result(timeout=...)` 可单独设超时、单独 try/except，一个 URL 失败不影响其它——本项目「健壮爬虫」正是用它；`Pool.map` 则会把整批异常一起抛出。
- **惰性流式**：`Pool.imap` 能惰性消费生成器、配合 chunksize 控制内存，适合 10 万张图那种流式场景；Executor 的 `map` 也支持 chunksize，但一次性提交大量任务时更占内存。
- **worker 回收**：`Pool` 早就有 `maxtasksperchild`（每个 worker 处理 N 个任务后重启，防内存累积）；Executor 直到 Python 3.11+ 才有 `max_tasks_per_child`。
- **崩溃处理**：worker 崩溃时 Executor 抛 `BrokenProcessPool` 且整池不可用；两者都支持 `with` 上下文管理，Executor 另有 `shutdown(cancel_futures=...)`（3.9+）。

怎么选（本项目两种都用了）：图像批处理用 `Pool.map`（整齐一批、要 `maxtasksperchild` 回收内存）；健壮爬虫用 `ProcessPoolExecutor + as_completed`（要逐 URL 超时/异常、按完成顺序聚合）。经验法则：要细粒度 Future/超时/逐个异常 → Executor；要惰性 imap、旧版本上的 worker 回收、简单 map → Pool。

下面演示 Executor「按完成顺序取结果 + 逐任务超时/异常」：

```python
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

def work(n):
    time.sleep(0.05 * (3 - n))   # 故意让不同任务耗时不同
    return n * n

if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(work, n): n for n in range(3)}
        for fut in as_completed(futures):   # 谁先完成先拿谁
            n = futures[fut]
            try:
                print(f"任务 {n} 结果 = {fut.result(timeout=5)}")
            except Exception as e:
                print(f"任务 {n} 失败: {e}")
```

预期输出（按完成先后，而非提交顺序）：`任务 2 结果 = 4`、`任务 1 结果 = 1`、`任务 0 结果 = 0`。耗时短的先返回，这正是 `as_completed` 相对 `Pool.map`（保持输入顺序）的优势。

⚠️ 注意：Windows/macOS 默认 spawn，worker 函数必须在模块顶层定义（可 pickle），调用放在 `if __name__ == "__main__":` 下，否则子进程重复导入主模块会报错；`max_tasks_per_child` 需 Python 3.11+。

5. **优化题**：Amdahl 定律告诉我们并行有上限。在这个项目中，并行化比例大约是多少？瓶颈在哪里？

**参考答案**

Amdahl 定律：`加速比 = 1 / ((1-P) + P/N)`，P 是「可并行比例」，N 是核数；当 N→∞，上限 = `1/(1-P)`。也就是说，哪怕只有一小块串行，也会把加速比死死卡住。

- **图像管道**：灰度/模糊/边缘都是逐像素、天然可并行，P 很高（约 0.9–0.99，因实现而异）。串行部分 (1-P) 主要是：进程池启动、Numba 首次 JIT 编译、读原图/写结果、进程间 pickle 大数组、主进程聚合统计。举例 P=0.95 时，4 核≈3.48x、8 核≈5.93x，上限 20x（数字因机器/版本而异）。
- **爬虫**：网络等待几乎可完全并发，P 也很高；但真正的上限常常不是 CPU 核数，而是「网络带宽 / 对方服务器限流 / 同域名限速」，再加上单核上的解析、TLS 与结果去重聚合。

瓶颈通常落在这几处（按影响排序，需实测确认）：

1. **内存带宽**：模糊/边缘访存密集，多核抢带宽，实际 P 打折。
2. **进程间拷贝 / pickle**：大数组序列化是串行开销，用共享内存/传路径可缓解。
3. **磁盘 I/O**：读原图、写结果。
4. **一次性串行成本**：Numba 首次编译 + 进程池启动，需预热（warmup）后再计时。
5. **结果聚合**：主进程串行汇总。
6. **超额订阅**：外层进程数 × 内层 Numba 线程数超过物理核数。

实践建议：先用基准测试比较串行/并行耗时反推 P，再优先优化最大的串行项（共享内存减拷贝、uint8 减带宽、预热减编译、流式降 I/O 峰值），而不是盲目加核——收益会递减。

下面用标准库把 Amdahl 定律算出来，直观看到「上限」：

```python
def amdahl(P, N):
    return 1 / ((1 - P) + P / N)

for P in (0.5, 0.9, 0.95, 0.99):
    row = [f"{amdahl(P, N):.2f}x" for N in (1, 2, 4, 8, 64)]
    limit = 1 / (1 - P)
    print(f"P={P:.2f}  N=1/2/4/8/64 -> {row}  上限={limit:.1f}x")
```

预期输出：

```
P=0.50  N=1/2/4/8/64 -> ['1.00x', '1.33x', '1.60x', '1.78x', '1.97x']  上限=2.0x
P=0.90  N=1/2/4/8/64 -> ['1.00x', '1.82x', '3.08x', '4.71x', '8.77x']  上限=10.0x
P=0.95  N=1/2/4/8/64 -> ['1.00x', '1.90x', '3.48x', '5.93x', '15.42x']  上限=20.0x
P=0.99  N=1/2/4/8/64 -> ['1.00x', '1.98x', '3.88x', '7.48x', '39.26x']  上限=100.0x
```

可见 P=0.9 时即便 64 核也只有 8.77x（上限 10x）；把 P 从 0.9 提到 0.99，上限就从 10x 跳到 100x——优化串行部分比堆核更划算。

💡 提示：P 不是固定常数，随图像大小、是否预热、dtype、是否共享内存而变；上面都是示例值，应在目标机器上实测。

---

## 📚 扩展阅读

- [Python multiprocessing 官方文档](https://docs.python.org/3/library/multiprocessing.html)
- [Amdahl's Law — Wikipedia](https://en.wikipedia.org/wiki/Amdahl%27s_law)
- [Numba 官方性能技巧](https://numba.pydata.org/numba-doc/latest/user/performance-tips.html)
