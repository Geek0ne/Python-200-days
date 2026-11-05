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

2. **性能题**：图像处理管道中，灰度转换用 Numba 并行，但高斯模糊用串行。分析这种设计的合理性。

3. **扩展题**：如果要处理 10 万张图像（每张 4K 分辨率），如何设计内存管理策略？

4. **对比题**：`multiprocessing.Pool` 和 `concurrent.futures.ProcessPoolExecutor` 在这个场景下有什么区别？选哪个？

5. **优化题**：Amdahl 定律告诉我们并行有上限。在这个项目中，并行化比例大约是多少？瓶颈在哪里？

---

## 📚 扩展阅读

- [Python multiprocessing 官方文档](https://docs.python.org/3/library/multiprocessing.html)
- [Amdahl's Law — Wikipedia](https://en.wikipedia.org/wiki/Amdahl%27s_law)
- [Numba 官方性能技巧](https://numba.pydata.org/numba-doc/latest/user/performance-tips.html)
