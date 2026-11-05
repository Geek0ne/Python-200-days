"""
Day 060 - 阶段项目：高性能图像处理管道
Numba 加速 + 多进程并行

运行方式：python3 02-image-pipeline.py
依赖：numpy，可选 numba (pip install numba)
"""

import time
import multiprocessing as mp
from dataclasses import dataclass
from typing import List
import numpy as np

# ─── Numba 可选导入 ───

try:
    from numba import jit, prange
    HAS_NUMBA = True
    print("✅ Numba 已加载，将使用 JIT 加速")
except ImportError:
    HAS_NUMBA = False
    print("⚠️  Numba 未安装，使用纯 NumPy 版本")


# ─── 灰度转换 ───

def to_grayscale(pixels: np.ndarray) -> np.ndarray:
    """RGB → 灰度"""
    if HAS_NUMBA:
        return _grayscale_numba(pixels)
    return _grayscale_numpy(pixels)


def _grayscale_numpy(pixels):
    return (0.299 * pixels[:, :, 0] +
            0.587 * pixels[:, :, 1] +
            0.114 * pixels[:, :, 2])


if HAS_NUMBA:
    @jit(nopython=True, parallel=True, cache=True)
    def _grayscale_numba(pixels):
        h, w = pixels.shape[:2]
        gray = np.empty((h, w), dtype=np.float64)
        for y in prange(h):
            for x in range(w):
                gray[y, x] = (0.299 * pixels[y, x, 0] +
                              0.587 * pixels[y, x, 1] +
                              0.114 * pixels[y, x, 2])
        return gray


# ─── 高斯模糊 ───

def gaussian_blur(image: np.ndarray, kernel_size: int = 5) -> np.ndarray:
    """高斯模糊"""
    if HAS_NUMBA:
        return _blur_numba(image, kernel_size)
    return _blur_numpy(image, kernel_size)


def _blur_numpy(image, kernel_size):
    ax = np.arange(kernel_size, dtype=np.float64) - kernel_size // 2
    xx, yy = np.meshgrid(ax, ax)
    sigma = kernel_size / 3.0
    kernel = np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
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
    @jit(nopython=True, parallel=True, cache=True)
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


# ─── 边缘检测 (Sobel) ───

def edge_detect(image: np.ndarray) -> np.ndarray:
    """Sobel 边缘检测"""
    if HAS_NUMBA:
        return _edge_numba(image)
    return _edge_numpy(image)


def _edge_numpy(image):
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
    @jit(nopython=True, parallel=True, cache=True)
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
                        val = image[y + ky - 1, x + kx - 1]
                        s_x += val * sobel_x[ky, kx]
                        s_y += val * sobel_y[ky, kx]
                gx[y, x] = s_x
                gy[y, x] = s_y

        return np.sqrt(gx**2 + gy**2)


# ─── 处理管道 ───

@dataclass
class ImageTask:
    task_id: int
    pixels: np.ndarray
    width: int = 0
    height: int = 0

    def __post_init__(self):
        self.height = self.pixels.shape[0]
        self.width = self.pixels.shape[1]


@dataclass
class ImageResult:
    task_id: int
    original_shape: tuple
    processed_shape: tuple
    process_time_ms: float
    steps: dict


def process_single_image(task: ImageTask) -> ImageResult:
    """处理单张图像的完整管道"""
    start = time.perf_counter()
    steps = {}

    # Step 1: 灰度
    t = time.perf_counter()
    gray = to_grayscale(task.pixels)
    steps["grayscale_ms"] = (time.perf_counter() - t) * 1000

    # Step 2: 模糊
    t = time.perf_counter()
    blurred = gaussian_blur(gray, kernel_size=5)
    steps["blur_ms"] = (time.perf_counter() - t) * 1000

    # Step 3: 边缘检测
    t = time.perf_counter()
    edges = edge_detect(blurred)
    steps["edge_ms"] = (time.perf_counter() - t) * 1000

    total = (time.perf_counter() - start) * 1000
    steps["total_ms"] = total

    return ImageResult(
        task_id=task.task_id,
        original_shape=task.pixels.shape,
        processed_shape=edges.shape,
        process_time_ms=total,
        steps=steps,
    )


# ─── 多进程批处理 ───

class ImageProcessor:
    """高性能图像批处理器"""

    def __init__(self, num_workers: int = None):
        self.num_workers = num_workers or mp.cpu_count()
        print(f"🖼️  图像处理器: {self.num_workers} 个 Worker")

    def process_batch(self, images: List[np.ndarray]) -> List[ImageResult]:
        """批量处理"""
        tasks = [ImageTask(task_id=i, pixels=img) for i, img in enumerate(images)]

        print(f"  处理 {len(tasks)} 张图像 ({tasks[0].height}×{tasks[0].width})...")

        # 预热（Numba 首次编译）
        if HAS_NUMBA:
            _ = process_single_image(tasks[0])
            print("  ✅ Numba 预热完成")

        start = time.perf_counter()

        with mp.Pool(processes=self.num_workers) as pool:
            results = pool.map(process_single_image, tasks)

        total_time = time.perf_counter() - start
        total_proc = sum(r.process_time_ms for r in results)

        print(f"\n  总耗时:     {total_time:.2f}s")
        print(f"  处理时间:   {total_proc:.0f}ms (所有图像)")
        print(f"  并行加速:   {total_proc / (total_time * 1000):.1f}x")

        # 打印每步耗时
        if results:
            avg = {k: sum(r.steps[k] for r in results) / len(results)
                   for k in results[0].steps if k != "total_ms"}
            print(f"\n  平均每步:")
            for step, ms in sorted(avg.items(), key=lambda x: -x[1]):
                print(f"    {step}: {ms:.1f}ms")

        return results


# ─── 基准测试 ───

def benchmark():
    print("=" * 60)
    print("高性能图像处理管道 — 性能测试")
    print("=" * 60)

    sizes = [(256, 256), (512, 512)]
    num_images = 4

    for h, w in sizes:
        print(f"\n--- {h}×{w}, {num_images} 张 ---")
        images = [np.random.randint(0, 256, (h, w, 3), dtype=np.float64)
                  for _ in range(num_images)]

        processor = ImageProcessor(num_workers=2)
        results = processor.process_batch(images)

        for r in results:
            print(f"  Image {r.task_id}: {r.process_time_ms:.0f}ms "
                  f"(gray={r.steps['grayscale_ms']:.0f}, "
                  f"blur={r.steps['blur_ms']:.0f}, "
                  f"edge={r.steps['edge_ms']:.0f})")


if __name__ == "__main__":
    benchmark()
    print("\n✅ 图像处理管道测试完成！")
