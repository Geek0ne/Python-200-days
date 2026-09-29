"""
Day 059 - Cython 性能加速实战
实战案例：图像灰度值计算 + 矩阵运算

运行方式：
    编译：cythonize -i 03-cython-performance.pyx
    运行：python3 03-cython-performance.py

注意：此文件需要先通过 cython 编译为 .so 才能运行。
如果未安装 Cython，可以直接运行下面的纯 Python 版本做对比。
"""

# ============================================================
# 以下是纯 Python 版本（无需 Cython 即可运行）
# Cython 加速版本请看注释中的 .pyx 版本
# ============================================================

import time
import numpy as np


# ─── 1. 图像灰度计算 ───

def grayscale_python(pixels):
    """
    将 RGB 像素数组转换为灰度
    pixels: shape (height, width, 3) 的 numpy 数组
    灰度公式: 0.299R + 0.587G + 0.114B (ITU-R BT.601)
    """
    height, width, _ = pixels.shape
    gray = np.empty((height, width), dtype=np.float64)
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            gray[y, x] = 0.299 * r + 0.587 * g + 0.114 * b
    return gray


def grayscale_numpy(pixels):
    """NumPy 向量化版本（作为对照）"""
    return 0.299 * pixels[:, :, 0] + 0.587 * pixels[:, :, 1] + 0.114 * pixels[:, :, 2]


# ─── 2. 矩阵乘法（朴素实现）───

def matmul_python(a, b):
    """朴素矩阵乘法 O(n³)"""
    n = len(a)
    c = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += a[i][k] * b[k][j]
            c[i][j] = s
    return c


def matmul_numpy(a, b):
    """NumPy 矩阵乘法（BLAS 优化）"""
    return np.dot(np.array(a), np.array(b))


# ─── 3. 快速傅里叶变换（简化版）───

def fft_simple(signal):
    """简化版 DFT（非 FFT），用于演示 O(n²) → O(n log n) 的加速需求"""
    n = len(signal)
    result = [0j] * n
    for k in range(n):
        s = 0j
        for t in range(n):
            angle = -2j * np.pi * k * t / n
            s += signal[t] * np.exp(angle)
        result[k] = s
    return result


# ─── 4. 质数计数 ───

def count_primes_python(limit):
    """统计 2 到 limit 之间的质数个数"""
    count = 0
    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, int(num**0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return count


# ─── 5. 性能对比 ───

def benchmark():
    print("=" * 60)
    print("Cython 性能加速实战 — 纯 Python vs NumPy")
    print("=" * 60)

    # --- 图像灰度 ---
    print("\n--- 图像灰度计算 (500×500) ---")
    pixels = np.random.randint(0, 256, (500, 500, 3), dtype=np.float64)

    start = time.perf_counter()
    _ = grayscale_python(pixels)
    py_time = time.perf_counter() - start

    start = time.perf_counter()
    _ = grayscale_numpy(pixels)
    np_time = time.perf_counter() - start

    print(f"  纯 Python 循环: {py_time:.3f}s")
    print(f"  NumPy 向量化:   {np_time:.4f}s")
    print(f"  NumPy 加速比:   {py_time/np_time:.0f}x")
    print(f"  → Cython 可加速纯 Python 版本 ~50x，接近 NumPy")

    # --- 矩阵乘法 ---
    print("\n--- 矩阵乘法 (200×200) ---")
    n = 200
    a = np.random.rand(n, n).tolist()
    b = np.random.rand(n, n).tolist()

    start = time.perf_counter()
    _ = matmul_python(a, b)
    py_time = time.perf_counter() - start

    start = time.perf_counter()
    _ = matmul_numpy(a, b)
    np_time = time.perf_counter() - start

    print(f"  朴素 Python: {py_time:.3f}s")
    print(f"  NumPy (BLAS): {np_time:.4f}s")
    print(f"  NumPy 加速比: {py_time/np_time:.0f}x")
    print(f"  → Cython + typed memoryview 可达 BLAS 70-80% 性能")

    # --- 质数计数 ---
    print("\n--- 质数计数 (100,000) ---")
    limit = 100_000

    start = time.perf_counter()
    py_count = count_primes_python(limit)
    py_time = time.perf_counter() - start

    print(f"  Python 结果: {py_count} 个质数")
    print(f"  Python 耗时: {py_time:.3f}s")
    print(f"  → Cython 可加速 ~30-50x")

    # --- 小型 DFT ---
    print("\n--- DFT (1024 点) ---")
    signal = [complex(x, 0) for x in np.random.rand(1024)]

    start = time.perf_counter()
    _ = fft_simple(signal)
    dft_time = time.perf_counter() - start

    print(f"  DFT O(n²): {dft_time:.3f}s")
    print(f"  → Cython 可加速 ~20-40x，但真正的 FFT 算法更快")


# ─── Cython 版本参考（需要编译） ───

CYTHON_REFERENCE = """
# === 文件: matmul_cy.pyx ===
# 编译: cythonize -i matmul_cy.pyx

import numpy as np
cimport numpy as cnp
from libc.math cimport sqrt

def count_primes_cy(int limit):
    cdef int count = 0
    cdef int num, i
    cdef bint is_prime

    for num in range(2, limit + 1):
        is_prime = True
        for i in range(2, <int>sqrt(num) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return count


def matmul_cy(double[:, ::1] a, double[:, ::1] b):
    \"\"\"Typed memoryview 矩阵乘法\"\"\"
    cdef int n = a.shape[0]
    cdef int m = a.shape[1]
    cdef int p = b.shape[1]
    cdef cnp.ndarray[double, ndim=2] c = np.zeros((n, p))
    cdef int i, j, k
    cdef double s

    for i in range(n):
        for j in range(p):
            s = 0.0
            for k in range(m):
                s += a[i, k] * b[k, j]
            c[i, j] = s
    return c
"""


def main():
    benchmark()

    print("\n" + "=" * 60)
    print("Cython 加速版本参考代码")
    print("=" * 60)
    print(CYTHON_REFERENCE)

    print("✅ 性能对比完成！")
    print("提示：安装 Cython 后运行 'cythonize -i matmul_cy.pyx' 编译加速版本")


if __name__ == "__main__":
    main()
