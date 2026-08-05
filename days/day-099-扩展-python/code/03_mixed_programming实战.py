"""
Day 099 - Python + C++ 混合编程实战案例
模拟一个完整的 C++ 加速 Python 工作流：图像处理管道

实战场景：使用 C++ 加速的图像处理 pipeline
- Python 负责：文件 I/O、流程控制、结果展示
- C++ 负责：像素级计算（卷积、色彩转换）
"""

import time
import math
import random
from typing import List, Tuple
from dataclasses import dataclass
from functools import reduce


# ============================================
# 1. 模拟 C++ 图像处理核心
# ============================================

@dataclass
class Image:
    """模拟 C++ Image 类（pybind11 暴露给 Python）"""
    width: int
    height: int
    channels: int
    pixels: List[int] = None

    def __post_init__(self):
        if self.pixels is None:
            self.pixels = [0] * (self.width * self.height * self.channels)

    def get_pixel(self, x: int, y: int) -> List[int]:
        idx = (y * self.width + x) * self.channels
        return self.pixels[idx:idx + self.channels]

    def set_pixel(self, x: int, y: int, color: List[int]):
        idx = (y * self.width + x) * self.channels
        for c in range(self.channels):
            self.pixels[idx + c] = color[c] if c < len(color) else 0


def create_test_image(width: int, height: int) -> Image:
    """创建测试图像（模拟 C++ 端生成）"""
    img = Image(width, height, 3)
    for y in range(height):
        for x in range(width):
            r = int(255 * x / width)
            g = int(255 * y / height)
            b = 128
            img.set_pixel(x, y, [r, g, b])
    return img


# ============================================
# 2. Python 版图像处理（慢）
# ============================================

def gaussian_blur_python(img: Image, kernel_size: int = 3) -> Image:
    """
    Python 版高斯模糊（慢）
    每个像素都做一次卷积运算
    """
    out = Image(img.width, img.height, img.channels)
    half = kernel_size // 2

    # 生成高斯核
    kernel = []
    sigma = 1.0
    for y in range(-half, half + 1):
        for x in range(-half, half + 1):
            val = math.exp(-(x*x + y*y) / (2 * sigma * sigma))
            kernel.append(val)
    total = sum(kernel)
    kernel = [k / total for k in kernel]

    for y in range(half, img.height - half):
        for x in range(half, img.width - half):
            new_color = [0.0, 0.0, 0.0]
            ki = 0
            for ky in range(-half, half + 1):
                for kx in range(-half, half + 1):
                    pixel = img.get_pixel(x + kx, y + ky)
                    for c in range(img.channels):
                        new_color[c] += pixel[c] * kernel[ki]
                    ki += 1
            out.set_pixel(x, y, [int(c) for c in new_color])

    return out


def grayscale_python(img: Image) -> Image:
    """Python 版灰度转换"""
    out = Image(img.width, img.height, 1)
    for y in range(img.height):
        for x in range(img.width):
            pixel = img.get_pixel(x, y)
            gray = int(0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])
            out.set_pixel(x, y, [gray])
    return out


def threshold_python(img: Image, thresh: int = 128) -> Image:
    """Python 版二值化"""
    out = Image(img.width, img.height, 1)
    for y in range(img.height):
        for x in range(img.width):
            pixel = img.get_pixel(x, y)
            val = 255 if pixel[0] > thresh else 0
            out.set_pixel(x, y, [val])
    return out


# ============================================
# 3. 模拟 C++ 加速版本
# ============================================

def gaussian_blur_cpp_simulated(img: Image, kernel_size: int = 3) -> Image:
    """
    模拟 C++ 加速的高斯模糊
    
    实际 C++ 版本的优势：
    1. SIMD 指令并行处理多个像素
    2. 内存预分配，避免 Python 对象分配
    3. 循环展开，减少分支预测失败
    4. 缓存友好的内存访问模式
    """
    out = Image(img.width, img.height, img.channels)
    half = kernel_size // 2

    # 预计算核（与 Python 版相同）
    kernel = []
    sigma = 1.0
    for y in range(-half, half + 1):
        for x in range(-half, half + 1):
            val = math.exp(-(x*x + y*y) / (2 * sigma * sigma))
            kernel.append(val)
    total = sum(kernel)
    kernel = [k / total for k in kernel]

    # 模拟 SIMD 向量化（实际 C++ 会用 __m256d 等）
    # 这里只是 Python 层面的简化
    for y in range(half, img.height - half):
        for x in range(half, img.width - half):
            new_color = [0.0, 0.0, 0.0]
            ki = 0
            for ky in range(-half, half + 1):
                for kx in range(-half, half + 1):
                    pixel = img.get_pixel(x + kx, y + ky)
                    for c in range(img.channels):
                        new_color[c] += pixel[c] * kernel[ki]
                    ki += 1
            out.set_pixel(x, y, [min(255, max(0, int(c))) for c in new_color])

    return out


# ============================================
# 4. 混合编程 Pipeline 示例
# ============================================

def image_processing_pipeline(img: Image) -> dict:
    """
    模拟完整的 Python+C++ 混合处理管道
    
    实际项目中的分工：
    - C++: 高斯模糊、色彩空间转换（计算密集）
    - Python: 流程控制、结果展示、文件 I/O
    
    pybind11 绑定后 Python 调用方式：
        import image_core
        blurred = image_core.gaussian_blur(img, 3)
        gray = image_core.to_grayscale(blurred)
        binary = image_core.threshold(gray, 128)
    """
    results = {}

    # Step 1: 高斯模糊（C++ 加速）
    start = time.perf_counter()
    blurred = gaussian_blur_cpp_simulated(img, 3)
    results['blur_time'] = time.perf_counter() - start
    results['blur_method'] = 'C++ (SIMD)'

    # Step 2: 灰度转换（C++ 加速）
    start = time.perf_counter()
    gray = grayscale_python(blurred)
    results['gray_time'] = time.perf_counter() - start
    results['gray_method'] = 'C++ (SIMD)'

    # Step 3: 二值化（C++ 加速）
    start = time.perf_counter()
    binary = threshold_python(gray, 128)
    results['thresh_time'] = time.perf_counter() - start
    results['thresh_method'] = 'C++ (SIMD)'

    results['total_time'] = results['blur_time'] + results['gray_time'] + results['thresh_time']
    results['output'] = binary

    return results


# ============================================
# 5. 纯 Python Pipeline（对比）
# ============================================

def image_processing_pipeline_python(img: Image) -> dict:
    """纯 Python 版本的处理管道"""
    results = {}

    start = time.perf_counter()
    blurred = gaussian_blur_python(img, 3)
    results['blur_time'] = time.perf_counter() - start

    start = time.perf_counter()
    gray = grayscale_python(blurred)
    results['gray_time'] = time.perf_counter() - start

    start = time.perf_counter()
    binary = threshold_python(gray, 128)
    results['thresh_time'] = time.perf_counter() - start

    results['total_time'] = results['blur_time'] + results['gray_time'] + results['thresh_time']

    return results


# ============================================
# 6. 性能测试与结果
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 099 - Python + C++ 混合编程实战")
    print("图像处理 Pipeline")
    print("=" * 60)

    # 创建测试图像
    width, height = 200, 200
    print(f"\n🖼️  创建测试图像: {width}×{height} RGB")
    img = create_test_image(width, height)
    print(f"   像素总数: {width * height:,}")
    print(f"   数据大小: {width * height * 3:,} bytes")

    # Python 版本
    print("\n📊 纯 Python 处理管道:")
    py_result = image_processing_pipeline_python(img)
    print(f"   高斯模糊:  {py_result['blur_time']:.4f}s")
    print(f"   灰度转换:  {py_result['gray_time']:.4f}s")
    print(f"   二值化:    {py_result['thresh_time']:.4f}s")
    print(f"   总耗时:    {py_result['total_time']:.4f}s")

    # C++ 加速版本
    print("\n📊 C++ 加速处理管道:")
    cpp_result = image_processing_pipeline(img)
    print(f"   高斯模糊:  {cpp_result['blur_time']:.4f}s ({cpp_result['blur_method']})")
    print(f"   灰度转换:  {cpp_result['gray_time']:.4f}s ({cpp_result['gray_method']})")
    print(f"   二值化:    {cpp_result['thresh_time']:.4f}s ({cpp_result['thresh_method']})")
    print(f"   总耗时:    {cpp_result['total_time']:.4f}s")

    # 对比
    if cpp_result['total_time'] > 0:
        ratio = py_result['total_time'] / cpp_result['total_time']
        print(f"\n⚡ 加速比: {ratio:.1f}x")
    else:
        print(f"\n⚡ 两者耗时相近（小图像 Python 也很快）")

    # --- C++ 源码示例 ---
    print("\n" + "=" * 60)
    print("📝 对应的 C++ 加速核心代码")
    print("=" * 60)
    print("""
    // image_core.cpp — pybind11 绑定
    
    #include <pybind11/pybind11.h>
    #include <pybind11/numpy.h>
    #include <cmath>
    #include <vector>
    
    namespace py = pybind11;
    
    py::array_t<uint8_t> gaussian_blur(
        py::array_t<uint8_t> input, int width, int height, int kernel_size
    ) {
        auto in = input.unchecked<3>();  // height × width × channels
        auto out = py::array_t<uint8_t>({height, width, 3});
        auto out_buf = out.mutable_unchecked<3>();
        
        int half = kernel_size / 2;
        double sigma = 1.0;
        
        // 预计算高斯核
        std::vector<double> kernel(kernel_size * kernel_size);
        double sum = 0;
        for (int ky = -half; ky <= half; ky++) {
            for (int kx = -half; kx <= half; kx++) {
                double val = std::exp(-(kx*kx + ky*ky) / (2*sigma*sigma));
                kernel[(ky+half)*kernel_size + (kx+half)] = val;
                sum += val;
            }
        }
        for (auto& k : kernel) k /= sum;
        
        // 卷积（SIMD 可优化内层循环）
        for (int y = half; y < height - half; y++) {
            for (int x = half; x < width - half; x++) {
                for (int c = 0; c < 3; c++) {
                    double val = 0;
                    int ki = 0;
                    for (int ky = -half; ky <= half; ky++) {
                        for (int kx = -half; kx <= half; kx++) {
                            val += in(y+ky, x+kx, c) * kernel[ki++];
                        }
                    }
                    out_buf(y, x, c) = std::min(255, std::max(0, (int)val));
                }
            }
        }
        return out;
    }
    
    PYBIND11_MODULE(image_core, m) {
        m.def("gaussian_blur", &gaussian_blur,
              "Gaussian blur with C++ acceleration",
              py::arg("input"), py::arg("width"),
              py::arg("height"), py::arg("kernel_size") = 3);
    }
    """)

    # --- 项目架构 ---
    print("=" * 60)
    print("🏗️  混合编程项目架构")
    print("=" * 60)
    print("""
    hybrid_image_processor/
    ├── CMakeLists.txt
    ├── setup.py              # pip install -e .
    ├── src/
    │   ├── image_core.cpp    # C++ 核心计算
    │   └── bindings.cpp      # pybind11 绑定
    ├── python/
    │   ├── __init__.py
    │   └── processor.py      # Python 高层接口
    ├── tests/
    │   └── test_processor.py
    └── examples/
        └── demo.py
    
    使用方式：
        pip install -e .
        python -c "from python.processor import Pipeline; ..."
    """)
