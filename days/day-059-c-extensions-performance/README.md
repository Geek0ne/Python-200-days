# Day 059 — C 扩展与性能优化

> Python 的优雅与 C 的速度，鱼与熊掌可以兼得

## 📋 今日学习目标

1. 理解 Python 与 C 交互的底层原理
2. 掌握 Cython、ctypes、CFFI、Numba 四种性能优化方案
3. 能根据场景选择合适的优化工具
4. 实战：用多种方式加速数值计算

---

## 一、为什么需要 C 扩展？

Python 是解释型语言，执行速度受限于：
- **全局解释器锁（GIL）**：同一时刻只有一个线程执行 Python 字节码
- **动态类型开销**：每次操作都需要类型检查
- **解释执行**：字节码逐条解释，无法像编译语言那样优化

### 性能对比示意

```
纯 Python 循环：  ████████████████████████████  100x（基准）
NumPy 向量化：    ████                          4x
C 扩展 / Cython： ██                            1-2x
纯 C：            █                             1x
```

### 优化路线图

```
┌─────────────────────────────────────────────────┐
│            Python 性能优化选择                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  能用 NumPy/Pandas 解决？                        │
│    ├─ 是 → 优先用向量化操作（最省事）              │
│    └─ 否 ↓                                      │
│                                                 │
│  需要 JIT 编译？                                 │
│    ├─ 是 → Numba（最简单，装饰器一行搞定）         │
│    └─ 否 ↓                                      │
│                                                 │
│  已有 C 代码需要调用？                            │
│    ├─ 是 → ctypes（标准库，零依赖）               │
│    │       CFFI（更 Pythonic）                   │
│    └─ 否 ↓                                      │
│                                                 │
│  需要从零写 C 扩展？                              │
│    └─ Cython（Python 语法 + C 编译）              │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 二、Cython — Python 语法，C 级速度

### 2.1 什么是 Cython？

Cython 是 Python 的超集，可以将 Python 代码编译成 C 扩展模块。它允许你：
- 添加 C 类型声明，消除动态类型开销
- 直接调用 C 函数和库
- 保持 Python 语法的可读性

### 2.2 工作原理

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  .pyx 文件   │ ──→ │   Cython     │ ──→ │   .c 文件    │
│ (Python+Type)│     │   编译器     │     │   (纯 C)     │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │  gcc/clang   │
                                         │   编译为      │
                                         │   .so/.pyd   │
                                         └──────────────┘
```

### 2.3 基础用法

**步骤 1：创建 `.pyx` 文件**

```python
# sum_cy.pyx
def cy_sum(n):
    """用 Cython 计算 0 到 n-1 的和"""
    total = 0
    for i in range(n):
        total += i
    return total
```

**步骤 2：创建 `setup.py`**

```python
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("sum_cy.pyx")
)
```

**步骤 3：编译安装**

```bash
python3 setup.py build_ext --inplace
```

### 2.4 类型声明加速

不加类型声明，Cython 和纯 Python 差不多。关键在于类型声明：

```cython
# sum_typed.pyx

# C 级变量声明 — 消除 Python 对象开销
def cy_sum_typed(int n):
    cdef long total = 0    # C long 类型
    cdef int i             # C int 类型
    for i in range(n):
        total += i
    return total
```

### 2.5 Cython 类型速查表

| 类型 | Python 对应 | 说明 |
|------|------------|------|
| `int` | int | C int（通常 32 位） |
| `long` | int | C long（通常 64 位） |
| `float` | float | C double |
| `bint` | bool | C 布尔 |
| `str` | str | Python 字符串（不可用 C 类型） |
| `char*` | bytes | C 字符串 |

### 2.6 速度对比

```python
import time

# 纯 Python
def py_sum(n):
    total = 0
    for i in range(n):
        total += i
    return total

# 测试
n = 10_000_000

start = time.perf_counter()
py_sum(n)
py_time = time.perf_counter() - start

start = time.perf_counter()
cy_sum_typed(n)  # Cython 版本
cy_time = time.perf_counter() - start

print(f"Python:  {py_time:.3f}s")
print(f"Cython:  {cy_time:.3f}s")
print(f"加速比:  {py_time/cy_time:.1f}x")
```

典型结果：Cython 比纯 Python 快 **30-100 倍**（循环密集型代码）。

---

## 三、ctypes — 标准库中的 C 互操作

### 3.1 什么是 ctypes？

ctypes 是 Python **标准库**自带的模块，用于调用共享库（.so / .dll）中的 C 函数。无需任何额外安装。

### 3.2 工作原理

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Python 代码 │ ──→ │   ctypes     │ ──→ │  C 共享库    │
│              │     │  (FFI 桥接)  │     │  (.so/.dll)  │
└──────────────┘     └──────────────┘     └──────────────┘
       │                    │                    │
   Python 对象         类型转换            C 函数执行
   (int, str...)     (自动/手动)          (原生速度)
```

### 3.3 调用 C 标准库函数

```python
import ctypes

# 加载 C 标准库
libc = ctypes.CDLL("libc.so.6")  # Linux
# libc = ctypes.CDLL("msvcrt")   # Windows

# 调用 abs()
result = libc.abs(-42)
print(result)  # 42

# 调用 strlen()
libc.strlen.argtypes = [ctypes.c_char_p]  # 声明参数类型
libc.strlen.restype = ctypes.c_size_t     # 声明返回类型
result = libc.strlen(b"Hello, World!")
print(result)  # 13
```

### 3.4 调用自定义 C 函数

**步骤 1：写一个 C 文件**

```c
// fast_math.c
#include <math.h>

double fast_sin(double x) {
    return sin(x);
}

long long fast_factorial(int n) {
    long long result = 1;
    for (int i = 2; i <= n; i++) {
        result *= i;
    }
    return result;
}
```

**步骤 2：编译为共享库**

```bash
gcc -shared -o fast_math.so -fPIC fast_math.c -lm
```

**步骤 3：Python 调用**

```python
import ctypes

# 加载共享库
lib = ctypes.CDLL("./fast_math.so")

# 声明函数签名
lib.fast_sin.argtypes = [ctypes.c_double]
lib.fast_sin.restype = ctypes.c_double

lib.fast_factorial.argtypes = [ctypes.c_int]
lib.fast_factorial.restype = ctypes.c_longlong

# 调用
print(lib.fast_sin(3.14159))      # ≈ 0
print(lib.fast_factorial(20))     # 2432902008176640000
```

### 3.5 ctypes 类型对照表

| ctypes 类型 | C 类型 | Python 对应 |
|------------|--------|------------|
| `c_bool` | `_Bool` | bool |
| `c_char` | `char` | bytes（单字符） |
| `c_int` | `int` | int |
| `c_long` | `long` | int |
| `c_float` | `float` | float |
| `c_double` | `double` | float |
| `c_char_p` | `char*` | bytes |
| `c_void_p` | `void*` | int |

### 3.6 传入数组

```python
import ctypes

# 创建 C 数组
arr = (ctypes.c_double * 5)(1.0, 2.0, 3.0, 4.0, 5.0)

# 传给 C 函数
lib.sum_array.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int]
lib.sum_array.restype = ctypes.c_double

result = lib.sum_array(arr, 5)
print(result)  # 15.0
```

---

## 四、CFFI — 更 Pythonic 的 C 互操作

### 4.1 什么是 CFFI？

CFFI（C Foreign Function Interface）提供了比 ctypes 更现代的接口，支持：
- 直接从 C 头文件解析函数签名
- ABI 模式（类似 ctypes，运行时加载）和 API 模式（编译时绑定）
- 更方便的结构体操作

### 4.2 ABI 模式（最快上手）

```python
from cffi import FFI

ffi = FFI()

# 声明 C 函数签名（直接写 C 语法）
ffi.cdef("""
    double sin(double x);
    long long factorial(int n);
""")

# 加载共享库
C = ffi.dlopen("libc.so.6")

# 调用
print(C.sin(3.14159))  # ≈ 0
```

### 4.3 调用自定义 C 库

```python
from cffi import FFI

ffi = FFI()
ffi.cdef("""
    double fast_sin(double x);
    long long fast_factorial(int n);
""")

lib = ffi.dlopen("./fast_math.so")
print(lib.fast_sin(1.5708))  # ≈ 1.0 (sin(π/2))
print(lib.fast_factorial(10))  # 3628800
```

### 4.4 API 模式（编译时绑定）

```python
# build_ffi.py — 运行一次生成绑定
from cffi import FFI

ffi = FFI()
ffi.cdef("""
    double fast_sin(double x);
    long long fast_factorial(int n);
""")

ffi.set_source("_fast_math_cffi", """
    #include "fast_math.c"  // 直接包含 C 源码
""", sources=["fast_math.c"])

ffi.compile()
```

```python
# 使用编译后的绑定
from _fast_math_cffi import ffi, lib

print(lib.fast_sin(1.0))
print(lib.fast_factorial(5))
```

### 4.5 ctypes vs CFFI 对比

| 特性 | ctypes | CFFI |
|------|--------|------|
| 依赖 | 标准库，零依赖 | 需要 pip install |
| 声明方式 | Python API 链式调用 | 直接写 C 语法 |
| 结构体支持 | 较繁琐 | 更方便 |
| 性能 | 略慢（每次调用有开销） | API 模式接近原生 |
| ABI 模式 | ✅ | ✅ |
| API 模式 | ❌ | ✅ |

---

## 五、Numba — 一行装饰器搞定加速

### 5.1 什么是 Numba？

Numba 是一个 JIT（Just-In-Time）编译器，通过装饰器将 Python 函数编译为机器码。它的最大优势是：**几乎不改代码，加个装饰器就行**。

### 5.2 工作原理

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Python 函数 │ ──→ │   @jit 装饰  │ ──→ │  LLVM 编译   │
│              │     │   首次调用时  │     │  生成机器码   │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                        │
   Python 字节码                          原生机器码
   (慢)                                  (快 10-100x)
```

### 5.3 基础用法

```python
from numba import jit
import time

@jit(nopython=True)  # nopython=True 强制编译为纯机器码
def monte_carlo_pi(n_samples):
    """用蒙特卡洛方法估算 π"""
    import random
    count = 0
    for i in range(n_samples):
        x = random.random()
        y = random.random()
        if x**2 + y**2 <= 1.0:
            count += 1
    return 4.0 * count / n_samples

# 首次调用会编译（较慢）
start = time.perf_counter()
pi = monte_carlo_pi(10_000_000)
first_call = time.perf_counter() - start

# 后续调用直接用机器码（很快）
start = time.perf_counter()
pi = monte_carlo_pi(10_000_000)
fast_call = time.perf_counter() - start

print(f"首次调用（含编译）: {first_call:.3f}s")
print(f"后续调用: {fast_call:.3f}s")
print(f"π ≈ {pi}")
```

### 5.4 Numba 装饰器参数速查

| 参数 | 说明 |
|------|------|
| `nopython=True` | 强制纯机器码模式（推荐） |
| `cache=True` | 缓存编译结果，避免重复编译 |
| `parallel=True` | 自动并行化循环 |
| `fastmath=True` | 启用快速数学运算（牺牲精度换速度） |
| `locals={'x': 'float64'}` | 局部变量类型声明 |

### 5.5 自动并行化

```python
from numba import jit, prange
import numpy as np

@jit(nopython=True, parallel=True)
def parallel_sum(arr):
    """并行求和"""
    total = 0.0
    for i in prange(len(arr)):  # prange 替代 range
        total += arr[i]
    return total

data = np.random.rand(100_000_000)
result = parallel_sum(data)
print(f"Sum: {result}")
```

### 5.6 Numba 支持的 Python 特性

```
✅ 支持：                    ❌ 不支持：
• NumPy 数组操作             • Python 类（class）
• 数学运算                   • 字典/集合的复杂操作
• 循环和条件                 • 字符串操作（有限）
• 元组/列表（固定大小）       • 生成器
• 内置数学函数               • 递归（有限支持）
```

---

## 六、方案选型决策树

```
需要加速 Python 代码？
│
├─ 循环密集型计算？
│   ├─ 能用 NumPy 向量化？ → NumPy（首选）
│   ├─ 不行 → Numba（最快上手）
│   └─ 需要复杂 C 交互？ → Cython
│
├─ 需要调用已有 C 库？
│   ├─ 快速原型 → ctypes（零依赖）
│   └─ 生产环境 → CFFI（更安全）
│
├─ 从零写 C 扩展？
│   └─ Cython（最推荐）
│
└─ 一般数值计算？
    └─ Numba（一行搞定）
```

---

## 七、性能对比实战

| 方案 | 安装难度 | 学习曲线 | 典型加速比 | 适用场景 |
|------|---------|---------|-----------|---------|
| 纯 Python | 无 | 无 | 1x（基准） | 原型开发 |
| NumPy | pip install | 低 | 10-100x | 数值数组操作 |
| Cython | pip + 编译 | 中 | 30-100x | 循环密集计算 |
| ctypes | 标准库 | 低 | 10-50x | 调用已有 C 库 |
| CFFI | pip install | 低 | 10-50x | 调用 C 库（更现代） |
| Numba | pip install | 极低 | 10-200x | JIT 加速数值计算 |

---

## 八、实战：蒙特卡洛 π 估算

用四种方式实现同一个算法，对比性能：

```python
# 方式 1：纯 Python
def pure_python_pi(n):
    import random
    count = 0
    for _ in range(n):
        x, y = random.random(), random.random()
        if x*x + y*y <= 1:
            count += 1
    return 4 * count / n

# 方式 2：NumPy 向量化
import numpy as np
def numpy_pi(n):
    x = np.random.rand(n)
    y = np.random.rand(n)
    return 4 * np.sum(x*x + y*y <= 1) / n

# 方式 3：Numba JIT
from numba import jit
@jit(nopython=True)
def numba_pi(n):
    count = 0
    for _ in range(n):
        x = np.random.random()
        y = np.random.random()
        if x*x + y*y <= 1:
            count += 1
    return 4 * count / n

# 方式 4：Cython 版本见 code/03-cython-monte-carlo.pyx
```

---

## 九、常见陷阱与避坑

### 1. Numba 首次调用慢
```python
# ❌ 错误：在计时代码中包含首次调用
start = time.time()
result = jit_func(data)  # 首次调用包含编译时间！
elapsed = time.time() - start

# ✅ 正确：先预热再计时
jit_func(data)  # 预热（编译）
start = time.time()
result = jit_func(data)  # 真正的执行时间
elapsed = time.time() - start
```

### 2. ctypes 忘记声明类型
```python
# ❌ 不声明类型（每次都转换，很慢）
lib.func(arg)

# ✅ 声明类型（自动转换，更快）
lib.func.argtypes = [ctypes.c_double]
lib.func.restype = ctypes.c_double
lib.func(arg)
```

### 3. Cython 编译错误
```python
# ❌ .pyx 文件不能直接 import
import sum_cy  # ModuleNotFoundError

# ✅ 必须先编译
# python3 setup.py build_ext --inplace
import sum_cy  # 现在可以了
```

### 4. Numba 不支持的特性
```python
# ❌ Numba 不支持普通 Python class
@jit(nopython=True)
class MyClass:  # 会报错
    pass

# ✅ 用 namedtuple 代替
from collections import namedtuple
Point = namedtuple('Point', ['x', 'y'])

@jit(nopython=True)
def use_point():
    p = Point(1.0, 2.0)  # namedtuple 可以用
    return p.x + p.y
```

---

## 十、思考题

1. **选型题**：你要加速一个图像处理管道（读取图片→滤波→边缘检测→保存），每个步骤都用 NumPy 数组操作。应该选择 Cython 还是 Numba？为什么？

2. **性能题**：为什么 ctypes 每次调用 C 函数都有固定开销，而 Cython 没有？从底层机制解释。

3. **设计题**：如果你有一个 10GB 的大文件需要逐行处理，ctypes 和 Cython 哪个更适合？为什么？

4. **对比题**：Numba 的 `parallel=True` 和 `concurrent.futures.ThreadPoolExecutor` 有什么区别？在什么场景下各自更优？

5. **进阶题**：编写一个 Cython 函数，接受两个 NumPy 数组，计算它们的余弦相似度，要求性能接近纯 C 实现。

---

## 📚 扩展阅读

- [Cython 官方文档](https://cython.readthedocs.io/)
- [Numba 用户手册](https://numba.pydata.org/)
- [CFFI 文档](https://cffi.readthedocs.io/)
- [Python C 扩展最佳实践](https://docs.python.org/3/extending/)
