"""
Day 099 - Pybind11 进阶示例
演示如何封装复杂的 C++ 类型和模式给 Python

注意：本文件模拟 Pybind11 的行为，展示 C++/Python 混合编程的设计模式
实际使用需要 C++ 编译环境
"""

import time
from typing import List, Tuple
from dataclasses import dataclass, field
from functools import lru_cache


# ============================================
# 1. 模拟 Pybind11 的类型转换
# ============================================

@dataclass
class Vec3:
    """模拟 C++ Vec3 类暴露给 Python 的效果"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: 'Vec3') -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def length(self) -> float:
        return (self.x ** 2 + self.y ** 2 + self.z ** 2) ** 0.5

    def normalize(self) -> 'Vec3':
        l = self.length()
        if l == 0:
            return Vec3()
        return self * (1.0 / l)

    def __repr__(self) -> str:
        return f"Vec3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


# ============================================
# 2. 模拟 Pybind11 的 STL 容器转换
# ============================================

def vectorToList(items: list) -> list:
    """
    模拟 pybind11 自动转换 std::vector <-> list
    pybind11 会自动处理：
    - std::vector<int>    <-> list[int]
    - std::vector<double> <-> list[float]
    - std::vector<std::string> <-> list[str]
    - std::vector<std::vector<int>> <-> list[list[int]]
    """
    return list(items)


def dictToMap(d: dict) -> dict:
    """
    模拟 pybind11 自动转换 std::map <-> dict
    """
    return dict(d)


# ============================================
# 3. 模拟异常传播
# ============================================

class CppRuntimeError(Exception):
    """模拟 C++ runtime_error 转换为 Python 异常"""
    pass


class CppValueError(Exception):
    """模拟 C++ std::invalid_argument"""
    pass


def simulate_cpp_function(x: float) -> float:
    """
    模拟 C++ 函数中的异常传播：
    
    C++ 代码:
        double dangerous(double x) {
            if (x < 0) throw std::invalid_argument("x must be non-negative");
            if (x > 1e308) throw std::runtime_error("overflow");
            return std::sqrt(x);
        }
    """
    if x < 0:
        raise CppValueError("x must be non-negative")
    if x > 1e308:
        raise CppRuntimeError("overflow")
    return x ** 0.5


# ============================================
# 4. 模拟 NumPy 集成
# ============================================

def multiply_array_py(data: list, factor: float) -> list:
    """
    模拟 pybind11 的 NumPy 数组操作
    
    C++ 版本：
        py::array_t<double> multiply(py::array_t<double> input, double factor) {
            auto buf = input.mutable_unchecked<1>();
            auto result = py::array_t<double>(buf.shape(0));
            for (py::ssize_t i = 0; i < buf.shape(0); i++) {
                result.mutable_unchecked<1>()(i) = buf(i) * factor;
            }
            return result;
        }
    """
    return [x * factor for x in data]


def elementwise_add(a: list, b: list) -> list:
    """模拟 NumPy 风格的元素级操作"""
    if len(a) != len(b):
        raise ValueError("Arrays must have same length")
    return [x + y for x, y in zip(a, b)]


# ============================================
# 5. 性能基准测试
# ============================================

def benchmark(func, *args, runs=5):
    times = []
    result = None
    for _ in range(runs):
        start = time.perf_counter()
        result = func(*args)
        times.append(time.perf_counter() - start)
    return result, sum(times) / len(times)


if __name__ == "__main__":
    print("=" * 60)
    print("Day 099 - Pybind11 进阶示例")
    print("=" * 60)

    # --- Vec3 运算 ---
    print("\n📐 Vec3 向量运算")
    v1 = Vec3(1.0, 2.0, 3.0)
    v2 = Vec3(4.0, 5.0, 6.0)

    print(f"  v1 = {v1}")
    print(f"  v2 = {v2}")
    print(f"  v1 + v2 = {v1 + v2}")
    print(f"  v1 * 3.0 = {v1 * 3.0}")
    print(f"  v1 · v2 = {v1.dot(v2)}")
    print(f"  |v1| = {v1.length():.3f}")
    print(f"  v1 归一化 = {v1.normalize()}")

    # --- 类型转换 ---
    print("\n🔄 STL 容器转换模拟")
    vec = [1, 2, 3, 4, 5]
    print(f"  std::vector<int> -> list: {vectorToList(vec)}")

    matrix = [[1, 2], [3, 4], [5, 6]]
    print(f"  std::vector<vector<int>> -> nested list: {vectorToList(matrix)}")

    cpp_map = {"a": 1, "b": 2, "c": 3}
    print(f"  std::map<string, int> -> dict: {dictToMap(cpp_map)}")

    # --- 异常传播 ---
    print("\n⚡ C++ 异常传播到 Python")
    try:
        simulate_cpp_function(-1.0)
    except CppValueError as e:
        print(f"  捕获 C++ invalid_argument: {e}")

    try:
        simulate_cpp_function(2e308)
    except CppRuntimeError as e:
        print(f"  捕获 C++ runtime_error: {e}")

    result = simulate_cpp_function(16.0)
    print(f"  sqrt(16) = {result}")

    # --- NumPy 操作 ---
    print("\n🔢 NumPy 集成模拟")
    data = list(range(1_000_000))

    r1, t1 = benchmark(multiply_array_py, data, 2.0)
    r2, t2 = benchmark(lambda d, f: [x * f for x in d], data, 2.0)

    print(f"  100万元素 × 2.0:")
    print(f"    模拟 C++ 版本: {t1:.4f}s")
    print(f"    Python 列表推导: {t2:.4f}s")

    # --- Pybind11 代码示例 ---
    print("\n" + "=" * 60)
    print("📝 对应的 C++ (pybind11) 代码示例")
    print("=" * 60)
    print("""
    # include <pybind11/pybind11.h>
    # include <pybind11/stl.h>
    # include <pybind11/numpy.h>
    # include <vector>
    # include <stdexcept>
    
    namespace py = pybind11;
    
    // Vec3 类
    class Vec3 {
    public:
        double x, y, z;
        Vec3(double x=0, double y=0, double z=0) : x(x), y(y), z(z) {}
        Vec3 operator+(const Vec3& o) const { return {x+o.x, y+o.y, z+o.z}; }
        Vec3 operator*(double s) const { return {x*s, y*s, z*s}; }
        double dot(const Vec3& o) const { return x*o.x + y*o.y + z*o.z; }
        double length() const { return std::sqrt(x*x + y*y + z*z); }
    };
    
    // 带异常的函数
    double safe_sqrt(double x) {
        if (x < 0) throw std::invalid_argument("x must be non-negative");
        return std::sqrt(x);
    }
    
    // NumPy 数组操作
    py::array_t<double> multiply(py::array_t<double> input, double factor) {
        auto buf = input.unchecked<1>();
        auto result = py::array_t<double>(buf.shape(0));
        auto res = result.mutable_unchecked<1>();
        for (py::ssize_t i = 0; i < buf.shape(0); i++) {
            res(i) = buf(i) * factor;
        }
        return result;
    }
    
    PYBIND11_MODULE(example, m) {
        // Vec3
        py::class_<Vec3>(m, "Vec3")
            .def(py::init<double, double, double>())
            .def("__add__", &Vec3::operator+)
            .def("__mul__", &Vec3::operator*)
            .def("dot", &Vec3::dot)
            .def("length", &Vec3::length);
        
        // 函数
        m.def("safe_sqrt", &safe_sqrt, "Safe square root");
        m.def("multiply", &multiply, "Multiply array by scalar");
        
        // 自动转换 std::vector
        m.def("get_primes", []() {
            std::vector<int> primes = {2, 3, 5, 7, 11, 13};
            return primes;  // 自动转为 Python list
        });
    }
    """)
