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

# 方式 4：Cython 版本见 code/03-cython-performance.py
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

**参考答案**

先厘清一个关键前提：**如果每个步骤都已经是 NumPy 数组操作，重活其实已经在 C 里跑了**——NumPy 的 ufunc/向量化操作本身就是编译好的 C 代码，还会释放 GIL。这种情况下，无论套 Cython 还是 Numba，都不会让「NumPy 调用本身」明显变快。所以第一步永远是先 profile，找到真正的瓶颈。

在「必须二选一」的前提下，对这个以 NumPy 为中心的管道，**更推荐 Numba**：

- **几乎零改动**：给自定义的逐元素/逐像素循环加一个 `@njit` 装饰器即可，Numba 原生理解 NumPy 数组，能把多步操作融合成一个编译内核，省掉中间临时数组。
- **上手成本低**：不用写 `.pyx`、不用配 `setup.py`、不用手动管理 C 类型。
- **适合数值内核**：滤波、边缘检测里若有你自己写的 Python 循环，Numba 能直接编译成机器码（10~100x）。

**什么时候反而选 Cython**：需要和 C/C++ 图像库（OpenCV、libjpeg、自研 C 算法）深度集成、要用 typed memoryview 做精细内存控制、或要把整个模块编译成稳定发布的 C 扩展时，Cython 更合适，但工程量更大。

具体例子：管道里「读取/保存」是磁盘 I/O（工具帮不上），「滤波/边缘检测」若用 `cv2.filter2D`、`cv2.Canny` 或 `scipy.ndimage`（都是 C 实现）已经很快；真正值得加速的是你手写的 Python 逐像素循环——下面量化这种循环的成本：

```python
import time


def python_kernel(n):
    """模拟手写的逐像素 Python 循环（这正是 Numba/Cython 要编译掉的部分）"""
    total = 0.0
    for i in range(n):
        x = i * 0.5
        total += x * x          # 每个元素都在 Python 层做运算
    return total


t0 = time.perf_counter()
python_kernel(2_000_000)
print(f"纯 Python 逐元素循环 200 万次: {time.perf_counter() - t0:.3f}s")
```

运行输出（耗时随机器而异）：

```
纯 Python 逐元素循环 200 万次: 0.067s
```

这种 Python 级循环用 Numba `@njit` 编译后通常能快一个数量级以上；而已经是 NumPy/OpenCV 的向量化 C 操作则不必再套壳。

💡 提示：实际用 Numba 加速时 `pip install numba numpy`，给函数加 `@njit(nopython=True)` 即可；首次调用含编译时间，计时前要先预热（参见本章「常见陷阱」）。

2. **性能题**：为什么 ctypes 每次调用 C 函数都有固定开销，而 Cython 没有？从底层机制解释。

**参考答案**

因为两者调用 C 函数的「路径」完全不同：

- **ctypes 是运行时 FFI 桥接**：每次调用都要在 Python 层做一整套 marshalling（编组）——把 Python 对象转换成 C 类型（int→c_int 等）、查找函数地址、用 libffi 动态构造调用栈帧、调用、再把 C 返回值转换回 Python 对象。这套胶水逻辑每次调用都重复执行，于是有一个固定的微秒级开销。
- **Cython 是编译期绑定**：`.pyx` 被编译成 C 扩展模块，当你用 `cdef` 声明了类型后，对 C 函数的调用会被直接编译成一条原生 C 调用指令，参数已是 C 类型、无需运行时转换，也没有 libffi 动态构造栈帧的开销。所以 Cython 调 C 函数几乎没有「每次调用」的额外成本。

一句话：ctypes 每次调用都「现场翻译 + 搭桥」，Cython 在编译时就把桥修好了、直接走过去。

具体例子：对比「ctypes 包一层的 C abs」和「解释器直接调用的内置 abs」（后者也是 C 实现，但无编组开销）：

```python
import ctypes
import ctypes.util
import sys
import time

# 加载 C 标准库（Windows 用 msvcrt，Linux 用 libc）
if sys.platform == "win32":
    libc = ctypes.CDLL("msvcrt")
else:
    libc = ctypes.CDLL(ctypes.util.find_library("c"))
libc.abs.argtypes = [ctypes.c_int]     # 声明参数/返回类型
libc.abs.restype = ctypes.c_int

N = 1_000_000
t0 = time.perf_counter()
for i in range(N):
    libc.abs(-i)                        # 每次都要编组
ct = time.perf_counter() - t0

t0 = time.perf_counter()
for i in range(N):
    abs(-i)                             # 内置 abs：解释器直接调 C，无编组
pt = time.perf_counter() - t0

print(f"ctypes 调用 abs {N} 次: {ct:.3f}s, 每次 {ct / N * 1e6:.3f}us")
print(f"内置 abs {N} 次: {pt:.3f}s, 每次 {pt / N * 1e6:.3f}us")
print(f"ctypes/内置 耗时比: {ct / pt:.1f}x")
```

运行输出（数值随机器而异）：

```
ctypes 调用 abs 1000000 次: 0.206s, 每次 0.206us
内置 abs 1000000 次: 0.048s, 每次 0.048us
ctypes/内置 耗时比: 4.3x
```

两者最终都执行 C 的 abs，但 ctypes 每次多出约 0.16µs 的编组开销（约 4 倍慢）。Cython 编译后的直接 C 调用就像内置 abs 一样，没有这层每次调用的开销。

⚠️ 注意：ctypes 的开销是「每次调用」固定的，所以调用次数越多、单次 C 工作越轻，开销占比越夸张；若单次 C 计算很重（如大数组运算），这点开销可忽略。务必声明 `argtypes/restype`，否则每次还要做更慢的默认类型推断。

3. **设计题**：如果你有一个 10GB 的大文件需要逐行处理，ctypes 和 Cython 哪个更适合？为什么？

**参考答案**

先抓住本质：10GB 文件逐行处理，**第一约束是内存——必须流式（streaming）处理，绝不能一次性读进内存**；第二才是速度。瓶颈通常在磁盘 I/O 和「每行的处理逻辑」，而不是「调用 C 函数的速度」。

- **ctypes 不适合**：它是「调用已有 C 库」的桥，本身不会加速 Python 的文件读取/逐行迭代。若用它，要么调用 C 库做 I/O（很别扭），要么对每一行调用一次 C 处理函数——而 ctypes 每次调用都有编组开销（见第 2 题），逐行调用几亿行会把这点开销放大成灾难。
- **Cython 更适合**：可以把「读取 + 解析 + 转换」整个热循环写进编译代码，用 C 类型和 C 级 I/O（或 typed memoryview 处理缓冲），消除每行的 Python 对象开销，也没有逐次调用的编组成本。

但更重要的结论：**如果每行处理很轻，这是 I/O 密集任务，纯 Python 流式读取就够了，ctypes/Cython 都帮不上大忙**（磁盘是瓶颈）；只有当「每行的解析/计算是 CPU 密集」时，才值得用 Cython（或 Numba）加速那段热循环。

具体例子：流式逐行处理，内存恒定（与文件多大无关），临时文件写在系统临时目录、用后即删：

```python
import os
import tempfile
import tracemalloc

# 造一个演示文件（真实场景是 10GB，这里用小文件演示「流式」模式）
path = os.path.join(tempfile.gettempdir(), "big_demo.txt")
with open(path, "w", encoding="utf-8") as f:
    for i in range(200000):
        f.write(f"{i},hello world,line {i}\n")

# 关键：for line in f 一次只读一行，内存 O(1)，不随文件增大
tracemalloc.start()
total = 0
n = 0
with open(path, "r", encoding="utf-8") as f:
    for line in f:
        total += int(line.split(",", 1)[0])
        n += 1
_, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"处理 {n} 行，累加和 {total}，峰值内存 {peak / 1024:.1f} KB")
os.remove(path)        # 清理临时文件
```

运行输出：

```
处理 200000 行，累加和 19999900000，峰值内存 33.8 KB
```

无论文件是 20 万行还是 10GB，峰值内存都维持在几十 KB——这就是流式处理。把其中 CPU 密集的处理段用 Cython 编译，才是 Cython 的用武之地。

💡 提示：千万别用 `f.readlines()` 或 `f.read()` 读 10GB 文件（会撑爆内存）；逐行 `for line in f` 或分块 `f.read(8192)` 才是正解。

4. **对比题**：Numba 的 `parallel=True` 和 `concurrent.futures.ThreadPoolExecutor` 有什么区别？在什么场景下各自更优？

**参考答案**

两者都能「多线程」，但层次和适用场景根本不同：

- **Numba `parallel=True`（配合 `prange`）**：在**机器码层面**自动把循环并行化。Numba 编译出的原生代码**不持有 GIL**，内部用自己的线程层（TBB/OpenMP/workqueue）把 `prange` 循环切成多段跑在多核上。适合**数据并行的数值循环**（逐元素运算、归约、stencil），是真正的 CPU 多核并行。
- **`ThreadPoolExecutor`**：在 **Python 层面**开线程跑 Python 函数。线程执行 Python 字节码时**受 GIL 限制**，同一时刻只有一个线程在跑 Python 代码——所以对 **CPU 密集的纯 Python 任务没有加速**；它只在 **I/O 密集**（等待时释放 GIL）或调用「会释放 GIL 的 C 扩展（如 NumPy）」时才有用。

一句话：**Numba parallel 是「编译后的无 GIL 多线程」，能加速 CPU 计算；ThreadPoolExecutor 是「受 GIL 限制的 Python 多线程」，适合 I/O 不适合 CPU。**

具体例子：用线程池跑 CPU 密集任务，验证 GIL 让它「并行不起来」：

```python
import time
from concurrent.futures import ThreadPoolExecutor


def cpu_task(n):
    s = 0
    for i in range(n):
        s += i * i          # 纯 Python CPU 计算，持有 GIL
    return s


K = 4
SIZE = 3_000_000
t0 = time.perf_counter()
serial = [cpu_task(SIZE) for _ in range(K)]
ts = time.perf_counter() - t0

t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=K) as ex:
    threaded = list(ex.map(cpu_task, [SIZE] * K))
tt = time.perf_counter() - t0

print(f"串行 {K} 个 CPU 任务: {ts:.2f}s")
print(f"{K} 线程并行: {tt:.2f}s")
print(f"结果一致: {serial == threaded}")
print(f"线程/串行 耗时比: {tt / ts:.2f} (≈1 或更慢=GIL 限制，无加速)")
```

运行输出（数值随机器而异）：

```
串行 4 个 CPU 任务: 0.37s
4 线程并行: 0.35s
结果一致: True
线程/串行 耗时比: 0.95 (≈1 或更慢=GIL 限制，无加速)
```

4 线程几乎没有加速（比值≈1），因为 GIL 把 CPU 计算串行化了。换成 Numba `@njit(parallel=True)` + `prange`，同样的循环会被编译成无 GIL 的机器码并行，在多核上能接近线性加速。

⚠️ 注意：ThreadPoolExecutor 并非一无是处——做网络/文件 I/O，或调用释放 GIL 的 NumPy 运算时它很有效；只是别拿它加速纯 Python 的 CPU 计算。Numba parallel 则要求函数能进 nopython 模式（不支持任意 Python 对象/类）。

5. **进阶题**：编写一个 Cython 函数，接受两个 NumPy 数组，计算它们的余弦相似度，要求性能接近纯 C 实现。

**参考答案**

用 typed memoryview + 关闭边界检查，把余弦相似度写成接近纯 C 的 Cython 函数。

`cosine.pyx`：

```cython
# cosine.pyx —— 用 typed memoryview 直接操作 NumPy 数组底层缓冲
from libc.math cimport sqrt
cimport cython


@cython.boundscheck(False)      # 关闭边界检查（提速）
@cython.wraparound(False)       # 关闭负索引回绕（提速）
def cosine_similarity(double[:] a, double[:] b):
    """计算两个一维 double 数组的余弦相似度，循环编译为纯 C"""
    cdef Py_ssize_t i, n = a.shape[0]
    cdef double dot = 0.0, na = 0.0, nb = 0.0
    for i in range(n):
        dot += a[i] * b[i]      # 点积
        na += a[i] * a[i]       # ||a||^2
        nb += b[i] * b[i]       # ||b||^2
    return dot / (sqrt(na) * sqrt(nb))
```

`setup.py`（编译用）：

```python
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("cosine.pyx", compiler_directives={"language_level": "3"})
)
```

编译并调用（需 `pip install cython numpy setuptools`，且系统装有 C 编译器 gcc/clang/MSVC）：

```bash
python setup.py build_ext --inplace
```

```python
import numpy as np
from cosine import cosine_similarity

a = np.array([1.0, 2.0, 3.0])
b = np.array([4.0, 5.0, 6.0])
print(cosine_similarity(a, b))   # 0.9746318461970762
```

为什么接近纯 C：`double[:]` 是 typed memoryview，直接拿到 NumPy 数组的连续 double 缓冲；`cdef` 声明让 `dot/na/nb/i` 都是 C 变量；关掉 boundscheck/wraparound 后，`for` 循环被编译成无 Python 对象开销的紧凑 C 循环，`sqrt` 直接调 C 数学库。

**算法正确性验证**：本环境无 C 编译器、无法编译 Cython，故用等价的纯 Python 实现验证同一算法与输出：

```python
import math


def cosine_py(a, b):
    """与上面 Cython 完全相同的算法（纯 Python 参考实现）"""
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    return dot / (math.sqrt(na) * math.sqrt(nb))


a = [1.0, 2.0, 3.0]
b = [4.0, 5.0, 6.0]
print(f"cosine([1,2,3],[4,5,6]) = {cosine_py(a, b)}")
```

运行输出：

```
cosine([1,2,3],[4,5,6]) = 0.9746318461970762
```

与公式 `dot/(||a||·||b||) = 32/(√14·√77)` 一致，证明 Cython 版本的算法正确。

⚠️ 注意：Cython 代码必须先编译成 `.so/.pyd` 才能 import（不能直接 import `.pyx`）；typed memoryview 要求传入连续的一维 double 数组（必要时 `np.ascontiguousarray(a, dtype=np.float64)`）。本环境缺少 C 编译器，Cython 版未能实际编译运行，已用等价纯 Python 验证算法与输出。

---

## 📚 扩展阅读

- [Cython 官方文档](https://cython.readthedocs.io/)
- [Numba 用户手册](https://numba.pydata.org/)
- [CFFI 文档](https://cffi.readthedocs.io/)
- [Python C 扩展最佳实践](https://docs.python.org/3/extending/)
