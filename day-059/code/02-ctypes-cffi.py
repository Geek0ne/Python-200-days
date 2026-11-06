"""
Day 059 - ctypes 与 CFFI 调用 C 库
进阶用法：自定义 C 函数 + Python 调用

运行方式：先编译 C 库，再运行 Python
    gcc -shared -o fast_math.so -fPIC fast_math.c -lm
    python3 02-ctypes-cffi.py

依赖：标准库 ctypes，CFFI 需要 pip install cffi
"""

import os
import tempfile
import ctypes
import time

# ─── 0. 先生成并编译 C 库 ───

C_SOURCE = """
#include <math.h>
#include <stdlib.h>

// 简单的加法
double add(double a, double b) {
    return a + b;
}

// 向量点积
double dot_product(double *a, double *b, int n) {
    double result = 0.0;
    for (int i = 0; i < n; i++) {
        result += a[i] * b[i];
    }
    return result;
}

// 快速阶乘（整数溢出仅用于演示）
long long fast_factorial(int n) {
    long long result = 1;
    for (int i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}

// 快速幂
double fast_pow(double base, int exp) {
    double result = 1.0;
    while (exp > 0) {
        if (exp % 2 == 1)
            result *= base;
        base *= base;
        exp /= 2;
    }
    return result;
}

// 字符串长度（演示字符串处理）
int str_length(const char *s) {
    int len = 0;
    while (s[len] != '\\0') len++;
    return len;
}

// 冒泡排序
void bubble_sort(double *arr, int n) {
    for (int i = 0; i < n - 1; i++) {
        for (int j = 0; j < n - i - 1; j++) {
            if (arr[j] > arr[j + 1]) {
                double tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
        }
    }
}
"""


def compile_c_library():
    """编译 C 源码为共享库"""
    # 创建临时目录存放 C 文件
    tmp_dir = tempfile.mkdtemp(prefix="day059_")
    c_file = os.path.join(tmp_dir, "fast_math.c")
    so_file = os.path.join(tmp_dir, "fast_math.so")

    with open(c_file, "w") as f:
        f.write(C_SOURCE)

    # 编译
    ret = os.system(f"gcc -shared -o {so_file} -fPIC {c_file} -lm -O2")
    if ret != 0:
        raise RuntimeError("C 编译失败！请确保安装了 gcc")

    return so_file, tmp_dir


# ─── 1. ctypes 方式 ───

def demo_ctypes(so_path):
    """用 ctypes 调用 C 函数"""
    print("=" * 60)
    print("ctypes 演示")
    print("=" * 60)

    lib = ctypes.CDLL(so_path)

    # --- 基础调用 ---
    lib.add.argtypes = [ctypes.c_double, ctypes.c_double]
    lib.add.restype = ctypes.c_double
    result = lib.add(3.14, 2.72)
    print(f"  add(3.14, 2.72) = {result}")

    # --- 阶乘 ---
    lib.fast_factorial.argtypes = [ctypes.c_int]
    lib.fast_factorial.restype = ctypes.c_longlong
    result = lib.fast_factorial(20)
    print(f"  fast_factorial(20) = {result}")

    # --- 快速幂 ---
    lib.fast_pow.argtypes = [ctypes.c_double, ctypes.c_int]
    lib.fast_pow.restype = ctypes.c_double
    result = lib.fast_pow(2.0, 100)
    print(f"  fast_pow(2, 100) = {result:.0f}")

    # --- 字符串处理 ---
    lib.str_length.argtypes = [ctypes.c_char_p]
    lib.str_length.restype = ctypes.c_int
    result = lib.str_length(b"Hello, ctypes!")
    print(f"  str_length('Hello, ctypes!') = {result}")

    # --- 数组操作 ---
    lib.dot_product.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
    ]
    lib.dot_product.restype = ctypes.c_double

    a = (ctypes.c_double * 5)(1.0, 2.0, 3.0, 4.0, 5.0)
    b = (ctypes.c_double * 5)(2.0, 3.0, 4.0, 5.0, 6.0)
    result = lib.dot_product(a, b, 5)
    print(f"  dot_product([1..5], [2..6]) = {result}")

    # --- 排序 ---
    lib.bubble_sort.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
    ]
    lib.bubble_sort.restype = None

    arr = (ctypes.c_double * 6)(5.0, 3.0, 1.0, 4.0, 2.0, 6.0)
    print(f"  排序前: {list(arr)}")
    lib.bubble_sort(arr, 6)
    print(f"  排序后: {list(arr)}")

    # --- 性能测试 ---
    print(f"\n  --- 性能测试 ---")
    n = 1_000_000
    a_large = (ctypes.c_double * n)(*([1.0] * n))
    b_large = (ctypes.c_double * n)(*([2.0] * n))

    start = time.perf_counter()
    _ = lib.dot_product(a_large, b_large, n)
    elapsed = time.perf_counter() - start
    print(f"  100万元素点积: {elapsed:.4f}s")


# ─── 2. CFFI 方式 ───

def demo_cffi(so_path):
    """用 CFFI 调用同一个 C 函数"""
    try:
        from cffi import FFI
    except ImportError:
        print("\n⚠️  CFFI 未安装，跳过 CFFI 演示 (pip install cffi)")
        return

    print("\n" + "=" * 60)
    print("CFFI 演示")
    print("=" * 60)

    ffi = FFI()

    # CFFI 的优势：直接写 C 语法声明
    ffi.cdef("""
        double add(double a, double b);
        double dot_product(double *a, double *b, int n);
        long long fast_factorial(int n);
        double fast_pow(double base, int exp);
        int str_length(const char *s);
        void bubble_sort(double *arr, int n);
    """)

    C = ffi.dlopen(so_path)

    # 基础调用
    print(f"  add(3.14, 2.72) = {C.add(3.14, 2.72)}")
    print(f"  fast_factorial(20) = {C.fast_factorial(20)}")
    print(f"  fast_pow(2, 100) = {C.fast_pow(2.0, 100):.0f}")
    print(f"  str_length('Hello, CFFI!') = {C.str_length(b'Hello, CFFI!')}")

    # CFFI 数组操作
    a = ffi.new("double[5]", [1.0, 2.0, 3.0, 4.0, 5.0])
    b = ffi.new("double[5]", [2.0, 3.0, 4.0, 5.0, 6.0])
    result = C.dot_product(a, b, 5)
    print(f"  dot_product([1..5], [2..6]) = {result}")

    # 排序
    arr = ffi.new("double[6]", [5.0, 3.0, 1.0, 4.0, 2.0, 6.0])
    print(f"  排序前: {[arr[i] for i in range(6)]}")
    C.bubble_sort(arr, 6)
    print(f"  排序后: {[arr[i] for i in range(6)]}")


# ─── 3. 对比 ───

def compare():
    """ctypes vs CFFI 性能对比"""
    print("\n" + "=" * 60)
    print("性能对比：ctypes vs CFFI")
    print("=" * 60)

    try:
        from cffi import FFI
        has_cffi = True
    except ImportError:
        has_cffi = False

    n = 500_000
    lib = ctypes.CDLL(_SO_PATH)

    lib.dot_product.argtypes = [
        ctypes.POINTER(ctypes.c_double),
        ctypes.POINTER(ctypes.c_double),
        ctypes.c_int,
    ]
    lib.dot_product.restype = ctypes.c_double

    a = (ctypes.c_double * n)(*([1.0] * n))
    b = (ctypes.c_double * n)(*([2.0] * n))

    # ctypes 计时
    times = []
    for _ in range(10):
        start = time.perf_counter()
        lib.dot_product(a, b, n)
        times.append(time.perf_counter() - start)
    ctypes_avg = sum(times) / len(times)
    print(f"  ctypes  平均: {ctypes_avg*1000:.2f}ms")

    if has_cffi:
        ffi = FFI()
        ffi.cdef("double dot_product(double *a, double *b, int n);")
        C = ffi.dlopen(_SO_PATH)
        a_cffi = ffi.new("double[]", [1.0] * n)
        b_cffi = ffi.new("double[]", [2.0] * n)

        times = []
        for _ in range(10):
            start = time.perf_counter()
            C.dot_product(a_cffi, b_cffi, n)
            times.append(time.perf_counter() - start)
        cffi_avg = sum(times) / len(times)
        print(f"  CFFI    平均: {cffi_avg*1000:.2f}ms")

        ratio = ctypes_avg / cffi_avg
        print(f"  ctypes / CFFI = {ratio:.2f}x")


# ─── 主程序 ───

_SO_PATH = None
_TMP_DIR = None


def main():
    global _SO_PATH, _TMP_DIR

    print("🔨 编译 C 库...")
    _SO_PATH, _TMP_DIR = compile_c_library()
    print(f"✅ 编译完成: {_SO_PATH}\n")

    demo_ctypes(_SO_PATH)
    demo_cffi(_SO_PATH)
    compare()

    # 清理
    os.remove(_SO_PATH)
    os.remove(os.path.join(_TMP_DIR, "fast_math.c"))
    os.rmdir(_TMP_DIR)

    print("\n✅ ctypes / CFFI 演示完成！")


if __name__ == "__main__":
    main()
