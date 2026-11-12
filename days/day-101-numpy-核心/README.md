# Day 101 — NumPy 核心

> NumPy 是 Python 科学计算的基石，几乎所有数据分析、机器学习、深度学习库都依赖它。

---

## 目录

1. [为什么需要 NumPy](#1-为什么需要-numpy)
2. [ndarray 基础](#2-ndarray-基础)
3. [数组创建方式](#3-数组创建方式)
4. [形状与维度操作](#4-形状与维度操作)
5. [广播机制 (Broadcasting)](#5-广播机制-broadcasting)
6. [通用函数 ufunc](#6-通用函数-ufunc)
7. [向量化计算](#7-向量化计算)
8. [线性代数基础](#8-线性代数基础)
9. [实战：矩阵运算与性能对比](#9-实战矩阵运算与性能对比)
10. [思考题](#10-思考题)

---

## 1. 为什么需要 NumPy

### Python 列表的局限性

```python
# Python 原生列表做数学运算
a = [1, 2, 3, 4, 5]
b = [10, 20, 30, 40, 50]

# 逐元素相加？得用循环
c = [a[i] + b[i] for i in range(len(a))]  # [11, 22, 33, 44, 55]
```

**问题：**
- 每个元素都是独立的 Python 对象（类型检查开销大）
- 数学运算需要逐个元素处理，速度慢
- 内存不连续，缓存不友好

### NumPy 的优势

| 对比维度 | Python 列表 | NumPy ndarray |
|---------|------------|---------------|
| 存储方式 | 指针数组（元素是对象引用） | 连续内存块（同类型数据） |
| 运算速度 | 慢（解释器循环） | 快（C 层向量化） |
| 内存占用 | 大（每个 int ~28 字节） | 小（每个 int64 仅 8 字节） |
| 广播运算 | 不支持 | 支持 |
| 线性代数 | 需要第三方库 | 内置 |

```python
import numpy as np
import time

# 性能对比：计算 1000 万个数的平方和
n = 10_000_000

# Python 列表
start = time.time()
a = list(range(n))
result = sum(x * x for x in a)
print(f"Python 列表: {time.time() - start:.3f}s")  # ~1.2s

# NumPy
start = time.time()
arr = np.arange(n)
result = np.sum(arr * arr)
print(f"NumPy: {time.time() - start:.3f}s")  # ~0.01s
```

**核心原理：NumPy 把运算下沉到 C 层，避免了 Python 解释器的逐元素循环开销。**

---

## 2. ndarray 基础

### 什么是 ndarray

`ndarray`（N-dimensional array）是 NumPy 的核心数据结构——一个多维同类型数组。

```
┌─────────────────────────────────────────────┐
│              NumPy ndarray                  │
├─────────────────────────────────────────────┤
│  data  ──→ [连续内存块: 1,2,3,4,5,6]       │
│  dtype ──→ int64                            │
│  shape ──→ (2, 3)                           │
│  strides ─→ (24, 8)  ← 每个维度的字节步长   │
│  ndim  ──→ 2                                │
└─────────────────────────────────────────────┘
```

### 核心属性

```python
import numpy as np

arr = np.array([[1, 2, 3],
                [4, 5, 6]])

print(arr.shape)    # (2, 3)  — 2行3列
print(arr.dtype)    # int64   — 元素类型
print(arr.ndim)     # 2       — 维度数
print(arr.size)     # 6       — 总元素数
print(arr.itemsize) # 8       — 每个元素占的字节数
print(arr.nbytes)   # 48      — 总字节数 (6 * 8)
print(arr.T)        # 转置    — [[1,4],[2,5],[3,6]]
```

### dtype 速查表

| dtype | 说明 | 字节数 |
|-------|------|--------|
| `np.int8` / `np.uint8` | 8位整数 | 1 |
| `np.int16` / `np.uint16` | 16位整数 | 2 |
| `np.int32` / `np.uint32` | 32位整数 | 4 |
| `np.int64` / `np.uint64` | 64位整数 | 8 |
| `np.float32` | 单精度浮点 | 4 |
| `np.float64` | 双精度浮点（默认） | 8 |
| `np.complex64` / `np.complex128` | 复数 | 8/16 |
| `np.bool_` | 布尔 | 1 |
| `np.str_` | Unicode 字符串 | 可变 |

```python
# 指定 dtype
arr_f32 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
arr_i8 = np.array([100, 200], dtype=np.int8)

# 查看类型
print(arr_f32.dtype)  # float32
print(arr_i8.dtype)   # int8
```

---

## 3. 数组创建方式

### 3.1 从 Python 数据创建

```python
import numpy as np

# 从列表创建
a = np.array([1, 2, 3])               # 一维
b = np.array([[1, 2], [3, 4]])        # 二维
c = np.array([[[1, 2], [3, 4]],       # 三维
              [[5, 6], [7, 8]]])
```

### 3.2 常用创建函数

```python
# 零数组
np.zeros((3, 4))          # 3x4 全零矩阵

# 全 1 数组
np.ones((2, 3))           # 2x3 全一矩阵

# 指定值填充
np.full((2, 3), 7.5)      # 2x3 全 7.5

# 单位矩阵
np.eye(4)                 # 4x4 对角线为 1

# 空数组（不初始化，值随机）
np.empty((3, 3))          # 3x3，值不确定
```

### 3.3 序列生成

```python
# arange — 类似 range，但返回 ndarray
np.arange(0, 10, 2)      # [0, 2, 4, 6, 8]
np.arange(0, 1, 0.1)     # [0.0, 0.1, ..., 0.9]

# linspace — 等间隔序列
np.linspace(0, 1, 5)      # [0, 0.25, 0.5, 0.75, 1.0]  5个点

# logspace — 等比序列
np.logspace(0, 3, 4)      # [1, 10, 100, 1000]  10^0 到 10^3
```

### 3.4 随机数

```python
# 均匀分布 [0, 1)
np.random.rand(3, 4)      # 3x4 随机数

# 标准正态分布 (均值0，标准差1)
np.random.randn(3, 4)

# 指定范围的随机整数
np.random.randint(0, 100, size=(3, 4))  # 0-99 的整数

# 指定 seed 保证可复现
np.random.seed(42)
np.random.rand(3)         # 每次运行结果相同
```

### 3.5 从文件读取

```python
# 文本文件
arr = np.loadtxt('data.txt')           # 读取纯文本
np.savetxt('output.txt', arr)          # 保存纯文本

# NumPy 专用格式（二进制，快速）
np.save('data.npy', arr)               # 保存
arr = np.load('data.npy')              # 加载

# 多个数组
np.savez('data.npz', a=arr_a, b=arr_b)
```

---

## 4. 形状与维度操作

### reshape — 改变形状

```python
import numpy as np

arr = np.arange(12)  # [0, 1, 2, ..., 11]

# reshape
arr_2d = arr.reshape(3, 4)     # 3 行 4 列
arr_3d = arr.reshape(2, 3, 2)  # 2 个 3x2 矩阵

# -1 自动推断
arr.reshape(3, -1)    # 3 行，列数自动 → (3, 4)
arr.reshape(-1, 4)    # 4 列，行数自动 → (3, 4)
arr.reshape(-1)       # 展平为一维 → (12,)
```

### flatten vs ravel

```python
arr = np.array([[1, 2], [3, 4]])

# ravel — 返回视图（修改会反映到原数组）
flat_view = arr.ravel()
flat_view[0] = 99
print(arr[0, 0])  # 99 — 原数组被修改了！

# flatten — 返回副本（独立的）
flat_copy = arr.flatten()
flat_copy[0] = 0
print(arr[0, 0])  # 99 — 原数组不受影响
```

### 轴（Axis）概念

```
           axis=0 (行方向 ↓)
              ↓
    ┌─────────────┐
    │ 0   1   2   │ ← axis=1 (列方向 →)
    │             │
    │ 3   4   5   │
    │             │
    │ 6   7   8   │
    └─────────────┘

axis=0 → 沿行方向操作（跨行聚合，结果是列）
axis=1 → 沿列方向操作（跨列聚合，结果是行）
```

```python
arr = np.array([[1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]])

# axis=0：沿行方向求和（每列的和）
print(arr.sum(axis=0))  # [12, 15, 18]

# axis=1：沿列方向求和（每行的和）
print(arr.sum(axis=1))  # [ 6, 15, 24]

# 不指定 axis：全局求和
print(arr.sum())         # 45
```

### 拼接与拆分

```python
a = np.array([1, 2, 3])
b = np.array([4, 5, 6])

# 拼接
np.concatenate([a, b])       # [1, 2, 3, 4, 5, 6]
np.stack([a, b])             # [[1,2,3],[4,5,6]]  堆叠
np.vstack([a, b])            # 同上（垂直堆叠）
np.hstack([a.reshape(1, -1),
           b.reshape(1, -1)]) # 水平堆叠

# 拆分
arr = np.arange(9).reshape(3, 3)
np.hsplit(arr, 3)            # 沿列拆成 3 份
np.vsplit(arr, 3)            # 沿行拆成 3 份
```

---

## 5. 广播机制 (Broadcasting)

### 什么是广播

广播是 NumPy 在不同形状数组间进行运算时自动扩展较小数组的规则。

```
规则（从最右边维度开始逐一对齐）：

1. 如果两个维度相等，或其中一个为 1，则兼容
2. 如果两个维度都不为 1 且不相等 → 报错
3. 缺少的维度视作 1
```

### 广播示意图

```
  示例 1: 标量 + 数组
  ┌──────────┐     ┌──────────┐     ┌──────────┐
  │    5     │  +  │ 1  2  3  │  =  │ 6  7  8  │
  └──────────┘     └──────────┘     └──────────┘
     scalar        (3,) → (1,3)      (3,)
                     ↑ 广播扩展

  示例 2: (3,1) + (1,4)
  ┌──────────┐     ┌──────────────┐
  │  1       │     │ 1  2  3  4   │
  │  2    +  │     └──────────────┘
  │  3       │     shape: (1, 4)
  └──────────┘     ↑ 广播扩展
   shape: (3,1)
   ↓ 广播扩展
  ┌────────────────────────────┐
  │  2   3   4   5             │
  │  3   4   5   6             │
  │  4   5   6   7             │
  └────────────────────────────┘
  shape: (3, 4)
```

### 广播实战

```python
import numpy as np

# 标量与数组
arr = np.array([[1, 2, 3],
                [4, 5, 6]])
print(arr + 10)          # 每个元素 +10

# 不同形状的数组
a = np.array([1, 2, 3]).reshape(3, 1)  # (3,1)
b = np.array([10, 20]).reshape(1, 2)   # (1,2)
print(a + b)
# [[11, 21],
#  [12, 22],
#  [13, 23]]  → 结果 (3,2)

# 归一化（常用技巧）
data = np.array([[1, 2], [3, 4], [5, 6]], dtype=float)
mean = data.mean(axis=0)     # 每列均值 [3, 4]
std = data.std(axis=0)       # 每列标准差
normalized = (data - mean) / std  # 广播运算
```

### 广播失败的例子

```python
a = np.ones((3, 2))
b = np.ones((3,))

# 这会报错！
# a.shape = (3, 2)
# b.shape = (3,) → 视为 (1, 3)
# 最右维度：2 vs 3 → 不兼容！

# 正确做法：reshape
b_reshaped = b.reshape(1, 3)   # (1,3) vs (3,2) → 需要换方向
# 或者：b[:, np.newaxis]       # (3,1) vs (3,2) → 可以广播
```

---

## 6. 通用函数 ufunc

### 什么是 ufunc

ufunc（Universal Function）是 NumPy 的逐元素函数，是向量化运算的核心。

```
ufunc 工作流程：

  输入数组 A  ──→  ┌──────────┐  ──→  输出数组 C
  输入数组 B  ──→  │  ufunc   │  ──→
                   │ (C层实现)│
                   └──────────┘
                   逐元素运算
```

### 常用数学 ufunc

```python
import numpy as np

arr = np.array([1, 4, 9, 16, 25], dtype=float)

# 基础数学
np.sqrt(arr)       # [1, 2, 3, 4, 5]
np.abs(-arr)       # [1, 4, 9, 16, 25]
np.exp(np.array([0, 1]))  # [1, e]
np.log(arr)        # 自然对数
np.log2(arr)       # 以 2 为底
np.log10(arr)      # 以 10 为底

# 三角函数
np.sin(np.array([0, np.pi/2, np.pi]))
np.cos(np.array([0, np.pi/2]))

# 舍入
np.round(np.array([1.2, 1.5, 1.8]), 0)  # [1, 2, 2]
np.ceil(np.array([1.1, 1.9]))           # [2, 2]
np.floor(np.array([1.1, 1.9]))          # [1, 1]
```

### 比较与逻辑

```python
a = np.array([1, 5, 3, 8, 2])
b = np.array([2, 4, 3, 7, 6])

# 比较运算（返回布尔数组）
a > 3       # [False, True, False, True, False]
a == b      # [False, False, True, False, False]

# 逻辑运算
np.logical_and(a > 2, b > 3)  # [False, True, False, True, False]
np.logical_or(a > 6, b > 5)   # [False, False, False, True, True]
np.logical_not(a > 5)         # [True, True, True, True, True]

# 布尔数组统计
arr = np.array([1, 5, 3, 8, 2])
print(np.sum(arr > 3))   # 2 (True 的个数)
print(np.any(arr > 7))   # True (是否存在)
print(np.all(arr > 0))   # True (是否全部满足)
```

### 聚合函数

```python
arr = np.array([[3, 1, 4],
                [1, 5, 9],
                [2, 6, 5]])

# 全局聚合
arr.mean()     # 平均值
arr.sum()      # 求和
arr.min()      # 最小值
arr.max()      # 最大值
arr.std()      # 标准差
arr.var()      # 方差

# 按轴聚合
arr.mean(axis=0)  # 每列均值 [2, 4, 6]
arr.mean(axis=1)  # 每行均值 [2.67, 5, 4.33]
arr.argmax(axis=1) # 每行最大值的索引 [2, 2, 2]
```

---

## 7. 向量化计算

### 什么是向量化

向量化 = 用数组运算替代显式循环，让 NumPy 在 C 层批量处理。

```python
import numpy as np

# ❌ 循环方式（慢）
def slow_distance(a, b):
    result = 0
    for x, y in zip(a, b):
        result += (x - y) ** 2
    return result ** 0.5

# ✅ 向量化方式（快）
def fast_distance(a, b):
    return np.sqrt(np.sum((a - b) ** 2))
```

### 索引与切片

```python
arr = np.arange(20).reshape(4, 5)
# [[ 0  1  2  3  4]
#  [ 5  6  7  8  9]
#  [10 11 12 13 14]
#  [15 16 17 18 19]]

# 基础索引
arr[0, 2]       # 2
arr[1:3, 2:4]   # [[7,8],[12,13]]

# 布尔索引
mask = arr > 10
arr[mask]        # [11, 12, 13, 14, 15, 16, 17, 18, 19]
arr[arr > 10]    # 同上

# 花式索引
arr[[0, 2, 3], [1, 3, 4]]  # [1, 13, 19]  对应位置的元素

# 花式索引选行
arr[[0, 2]]      # 第 0 行和第 2 行
```

### 花式索引 vs 切片 vs 布尔索引的性能

```python
import numpy as np
import time

arr = np.random.rand(10000, 1000)
n = 1000

# 切片（视图，零拷贝，最快）
start = time.time()
for _ in range(n):
    _ = arr[0:100]
print(f"切片: {time.time() - start:.4f}s")

# 布尔索引（拷贝，较慢）
mask = arr[:, 0] > 0.5
start = time.time()
for _ in range(n):
    _ = arr[mask]
print(f"布尔索引: {time.time() - start:.4f}s")

# 花式索引（拷贝，最慢）
indices = np.random.randint(0, 10000, size=100)
start = time.time()
for _ in range(n):
    _ = arr[indices]
print(f"花式索引: {time.time() - start:.4f}s")
```

---

## 8. 线性代数基础

### 矩阵运算

```python
import numpy as np

A = np.array([[1, 2],
              [3, 4]])
B = np.array([[5, 6],
              [7, 8]])

# 矩阵乘法
C = A @ B             # 或 np.dot(A, B) 或 np.matmul(A, B)
# [[19, 22],
#  [43, 50]]

# 逐元素乘法（注意区分）
C = A * B             # [[5, 12], [21, 32]]

# 转置
A.T                   # [[1,3],[2,4]]

# 逆矩阵
A_inv = np.linalg.inv(A)
print(A @ A_inv)      # 单位矩阵（浮点误差内）

# 行列式
np.linalg.det(A)      # -2.0

# 特征值和特征向量
eigenvalues, eigenvectors = np.linalg.eig(A)

# SVD 分解
U, S, Vt = np.linalg.svd(A)
```

### 常用线性代数函数

```python
# 解线性方程组 Ax = b
A = np.array([[3, 1], [1, 2]])
b = np.array([9, 8])
x = np.linalg.solve(A, b)
print(x)  # [2, 3]  → 3*2+1*3=9, 1*2+2*3=8 ✓

# 范数
v = np.array([3, 4])
np.linalg.norm(v)        # 5.0（L2范数，即欧几里得距离）
np.linalg.norm(v, ord=1) # 7.0（L1范数）

# 矩阵范数
np.linalg.norm(A, ord='fro')  # Frobenius 范数
```

---

## 9. 实战：矩阵运算与性能对比

### 场景：计算 10000 个点两两之间的欧氏距离

```python
import numpy as np
import time

# 生成 10000 个 3 维随机点
np.random.seed(42)
points = np.random.rand(10000, 3)

# ── 方法 1：双重循环（最慢） ──
def euclidean_loop(points):
    n = len(points)
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist[i, j] = np.sqrt(np.sum((points[i] - points[j]) ** 2))
    return dist

# ❌ 太慢了，实际运行需几小时，这里只测试前 500 个
# dist_loop = euclidean_loop(points[:500])

# ── 方法 2：向量化循环 ──
def euclidean_vectorized_loop(points):
    n = len(points)
    dist = np.zeros((n, n))
    for i in range(n):
        diff = points - points[i]        # 广播：(n,3) - (3,) → (n,3)
        dist[i] = np.sqrt(np.sum(diff ** 2, axis=1))
    return dist

start = time.time()
dist_vl = euclidean_vectorized_loop(points[:1000])
t_vl = time.time() - start
print(f"向量化循环 (1000点): {t_vl:.3f}s")

# ── 方法 3：全向量化（最快） ──
def euclidean_broadcast(points):
    # 利用 ||a-b||² = ||a||² + ||b||² - 2a·b
    sq_sum = np.sum(points ** 2, axis=1)         # (n,)
    dist_sq = sq_sum[:, None] + sq_sum[None, :]  # (n,n)
    dist_sq -= 2 * points @ points.T              # (n,n)
    # 数值稳定性：负数置零
    np.maximum(dist_sq, 0, out=dist_sq)
    return np.sqrt(dist_sq)

start = time.time()
dist_full = euclidean_broadcast(points)
t_full = time.time() - start
print(f"全向量化 (10000点): {t_full:.3f}s")
# 全向量化只需要 ~0.2s！
```

### 场景：图片灰度处理

```python
import numpy as np

# 模拟一张 1920x1080 RGB 图片
np.random.seed(42)
img = np.random.randint(0, 256, (1080, 1920, 3), dtype=np.uint8)

# ── 方法 1：循环方式（慢） ──
def gray_loop(img):
    h, w = img.shape[:2]
    gray = np.zeros((h, w), dtype=np.uint8)
    for i in range(h):
        for j in range(w):
            gray[i, j] = 0.299 * img[i, j, 0] + \
                          0.587 * img[i, j, 1] + \
                          0.114 * img[i, j, 2]
    return gray

# ── 方法 2：向量化（快） ──
def gray_vectorized(img):
    weights = np.array([0.299, 0.587, 0.114])
    gray = np.dot(img.astype(np.float32), weights).astype(np.uint8)
    return gray

# 测试（只用小图测试循环方法）
small_img = img[:100, :100]
start = time.time()
gray_loop(small_img)
print(f"循环 (100x100): {time.time() - start:.3f}s")

start = time.time()
gray_vectorized(img)
print(f"向量化 (1080x1920): {time.time() - start:.3f}s")
```

---

## 10. 思考题

1. **为什么 `reshape(-1)` 等价于 `flatten`？它们有什么区别？**（提示：视图 vs 副本）

**参考答案**

两者都能把多维数组「拉平」成一维，元素顺序相同，所以结果看起来等价。但**底层机制不同**：

- `reshape(-1)`：**尽量返回视图（view）**——只要原数组内存连续，它就不复制数据，只是换一种方式解读同一块内存。改它会动到原数组。
- `flatten()`：**总是返回副本（copy）**——新开一块内存把数据抄过去，改它不影响原数组。

```python
import numpy as np

arr = np.arange(6).reshape(2, 3)
print("原数组:\n", arr)

r = arr.reshape(-1)      # 尽量返回视图
r[0] = 99
print("reshape(-1) 改首元素后 arr[0,0] =", arr[0, 0])   # 99 → 视图

f = arr.flatten()        # 总是返回副本
f[0] = 0
print("flatten 改首元素后 arr[0,0] =", arr[0, 0])       # 仍是 99 → 副本
```

预期输出：

```
原数组:
 [[0 1 2]
 [3 4 5]]
reshape(-1) 改首元素后 arr[0,0] = 99
flatten 改首元素后 arr[0,0] = 99
```

所以「等价」仅指形状和数值；要安全地拿一份独立数据用 `flatten()`（或 `ravel()` 后 `.copy()`），要省内存、允许联动就用 `reshape(-1)`。

⚠️ 注意：若原数组不连续（比如经过转置 `.T`），`reshape(-1)` 也会被迫复制，此时它和 flatten 一样返回副本——视图只是「尽力而为」。

2. **广播机制中，`(4, 3) + (3,)` 能否成功？为什么？如果不能，怎么改？**

**参考答案**

**能成功**。广播从**最右维度**开始逐一对齐：`(3,)` 先在左边补 1 变成 `(1, 3)`，再和 `(4, 3)` 比较——最右维 3==3 兼容，次右维 4 vs 1 中有一个是 1 也兼容，于是 `(3,)` 被沿行方向复制 4 份，结果形状 `(4, 3)`。

```python
import numpy as np

a = np.ones((4, 3))
b = np.array([10, 20, 30])       # shape (3,)
print("(4,3) + (3,) 结果:\n", a + b)
print("结果形状:", (a + b).shape)

# 对比：(4,3) + (4,) 会失败
c = np.array([1, 2, 3, 4])       # shape (4,)
try:
    a + c
except ValueError as e:
    print("(4,3) + (4,) 报错:", e)

# 修正：把 (4,) 变成 (4,1)
print("(4,3) + (4,1) 结果形状:", (a + c[:, None]).shape)
```

预期输出：

```
(4,3) + (3,) 结果:
 [[11. 21. 31.]
 [11. 21. 31.]
 [11. 21. 31.]
 [11. 21. 31.]]
结果形状: (4, 3)
(4,3) + (4,) 报错: operands could not be broadcast together with shapes (4,3) (4,)
(4,3) + (4,1) 结果形状: (4, 3)
```

反过来 `(4,3) + (4,)` 会失败：`(4,)` 补成 `(1,4)`，最右维 3 vs 4 都不为 1 且不相等 → 不兼容。修正方法是用 `c[:, None]`（即 `np.newaxis`）把它变成 `(4,1)`，让 4 对齐行、1 广播到列。

💡 提示：记住口诀「右对齐、缺补 1、相等或为 1 才兼容」，判断广播就不会错。

3. **在计算两两欧氏距离时，全向量化方法利用了什么数学恒等式？这个方法在什么情况下会出现数值问题？**

**参考答案**

利用的是**展开平方范数**的恒等式：

```
||a - b||² = ||a||² + ||b||² - 2·(a·b)
```

这样就把「两两做差再平方」变成了三个可向量化的部分：每个点的平方和 `||a||²`（一个向量）、以及矩阵乘法 `points @ points.T`（一次算出所有点积）。避免了 n² 次 Python 循环，速度大幅提升。

**数值问题来自「灾难性抵消」（catastrophic cancellation）**：当两个点非常接近时，`||a||² + ||b||²` 和 `2·(a·b)` 是两个很大且几乎相等的数，相减得到的真实距离平方却很小。浮点误差会让结果出现**负数**（理论上平方和不可能为负），开方就得到 NaN。代码里 `np.maximum(dist_sq, 0, out=dist_sq)` 正是为了把这种负数钳回 0。

此外，当坐标数值本身极大（如 1e8）时，平方后超出 float 精度范围，误差会被进一步放大。所以对精度敏感或点极近的场景，要么用 `scipy.spatial.distance.cdist`（内部更稳健），要么先对数据做中心化/缩放。

4. **NumPy 的 `axis` 参数为什么从最外层开始编号？如果有一个 shape 为 `(2, 3, 4, 5)` 的数组，`axis=2` 指向哪个维度？**

**参考答案**

`axis` 的编号与 `shape` 元组的位置一一对应：**axis=0 是最外层（第一个）维度，axis=1 是第二层，依此类推**。这样设计是因为它和数组的嵌套结构、以及 C 顺序（行优先）的内存布局一致——shape 怎么写，axis 就怎么数，直观且无歧义。

对 shape `(2, 3, 4, 5)`：

| axis | 0 | 1 | 2 | 3 |
|------|---|---|---|---|
| 该维大小 | 2 | 3 | **4** | 5 |

所以 **`axis=2` 指向大小为 4 的那个维度**（第三层）。例如 `arr.sum(axis=2)` 会沿着这个长度为 4 的轴求和，结果形状变成 `(2, 3, 5)`——被求和的那一维「消失」了。

小例子：把数组想象成「2 本书，每本 3 章，每章 4 节，每节 5 段」，axis=2 就是「节」这一层，`sum(axis=2)` 即把每章的 4 节合并统计。

5. **为什么 `np.float32` 在深度学习中比 `np.float64` 更常用？除了内存，还有什么优势？**

**参考答案**

float32（单精度，4 字节）相比 float64（双精度，8 字节）的优势不止省一半内存：

- **计算更快**：GPU 的张量核心（Tensor Core）和 CPU 的 SIMD 指令对 float32 的吞吐量远高于 float64，同样硬件每秒能算更多乘加；显存带宽占用也减半，数据搬运更快。
- **缓存更友好**：同样的缓存能装下两倍数据，命中率更高。
- **精度足够**：神经网络训练本身带噪声（随机梯度、dropout），参数更新量级远大于 float32 的舍入误差，float64 的额外精度对最终效果几乎无益，纯属浪费。
- **混合精度的基础**：现代训练常用 float16/bfloat16 算、float32 存主权重，float32 是这套体系的「锚点」。

一句话：深度学习要的是「够用的精度 + 极致的吞吐」，float32 恰好平衡两者；float64 的高精度更适合科学计算（如轨道力学、金融精算）而非神经网络。

⚠️ 注意：需要极高数值精度的场景（如某些损失累加、求逆）仍可能局部用 float64，不要一刀切。
