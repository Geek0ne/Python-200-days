# Day 079 — NumPy 基础

> **数据分析仪表盘项目 Day 1/3：NumPy — 科学计算的基石**

---

## 📋 今日学习目标

- 理解 NumPy 的设计理念与核心价值
- 掌握 ndarray 的创建、属性与基本操作
- 学会数组索引、切片与布尔索引
- 理解 NumPy 的广播机制
- 掌握常用数学函数与线性代数操作

---

## 1. 为什么需要 NumPy？

### 1.1 Python 原生列表的痛点

```python
import time

# Python 原生列表求平方
start = time.time()
result = [x ** 2 for x in range(1_000_000)]
print(f"列表推导式: {time.time() - start:.4f}s")

# NumPy 向量化求平方
import numpy as np
arr = np.arange(1_000_000)
start = time.time()
result = arr ** 2
print(f"NumPy 向量化: {time.time() - start:.4f}s")
```

典型结果：
- 列表推导式：~0.05s
- NumPy 向量化：~0.001s

**性能差距约 50 倍！**

### 1.2 NumPy 的核心优势

| 特性 | Python 列表 | NumPy 数组 |
|------|------------|-----------|
| 数据类型 | 可混合 | 统一类型 |
| 内存占用 | 高（每个元素是完整对象） | 低（连续内存块） |
| 运算速度 | 慢（逐元素 Python 解释） | 快（C 语言底层实现） |
| 向量化运算 | ❌ 不支持 | ✅ 原生支持 |
| 广播机制 | ❌ 不支持 | ✅ 支持 |
| 多维索引 | 繁琐 | 简洁 |

---

## 2. ndarray — NumPy 的核心数据结构

### 2.1 什么是 ndarray？

`ndarray`（N-dimensional array）是 NumPy 的核心数据结构。与 Python 列表不同，ndarray 有以下关键特性：

- **同质数据**：所有元素必须是同一类型（dtype）
- **连续内存**：数据存储在连续的内存块中，便于 CPU 缓存优化
- **固定大小**：创建后大小不可变（需要改变时创建新数组）
- **视图机制**：切片操作返回视图而非副本

### 2.2 创建数组

```python
import numpy as np

# 从 Python 列表创建
arr1 = np.array([1, 2, 3, 4, 5])
print(arr1)  # [1 2 3 4 5]
print(type(arr1))  # <class 'numpy.ndarray'>

# 二维数组（嵌套列表）
arr2 = np.array([[1, 2, 3], [4, 5, 6]])
print(arr2)
# [[1 2 3]
#  [4 5 6]]

# 指定数据类型
arr3 = np.array([1, 2, 3], dtype=np.float64)
print(arr3.dtype)  # float64

# 从特殊函数创建
zeros = np.zeros((3, 4))       # 3x4 全零矩阵
ones = np.ones((2, 3))         # 2x3 全一矩阵
empty = np.empty((2, 2))       # 2x2 未初始化数组
eye = np.eye(3)                # 3x3 单位矩阵
full = np.full((2, 3), 7)      # 2x3 全填充数组

# 等差序列
arr_range = np.arange(0, 10, 2)    # [0, 2, 4, 6, 8]
arr_linspace = np.linspace(0, 1, 5)  # [0, 0.25, 0.5, 0.75, 1.0]

# 随机数
rand1 = np.random.rand(3, 3)       # 均匀分布 [0, 1)
rand2 = np.random.randn(3, 3)      # 标准正态分布
rand_int = np.random.randint(0, 10, (3, 3))  # 随机整数

print("zeros:\n", zeros)
print("linspace:", arr_linspace)
print("random rand:\n", rand1)
```

### 2.3 数组属性

```python
arr = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])

print("shape:", arr.shape)       # (3, 4) — 形状（行，列）
print("ndim:", arr.ndim)         # 2 — 维度数
print("size:", arr.size)         # 12 — 元素总数
print("dtype:", arr.dtype)       # int64 — 数据类型
print("itemsize:", arr.itemsize) # 8 — 每个元素占多少字节
print("nbytes:", arr.nbytes)     # 96 — 总字节数
print("T:\n", arr.T)            # 转置
```

---

## 3. 数组索引与切片

### 3.1 一维数组索引

```python
arr = np.array([10, 20, 30, 40, 50])

print(arr[0])       # 10
print(arr[-1])      # 50
print(arr[1:4])     # [20 30 40]
print(arr[::2])     # [10 30 50]
print(arr[::-1])    # [50 40 30 20 10]  反转
```

### 3.2 二维数组索引

```python
arr = np.array([[1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]])

# 行索引
print(arr[0])       # [1 2 3]  — 第0行
print(arr[1])       # [4 5 6]  — 第1行

# 元素索引
print(arr[0, 1])    # 2  — 第0行第1列
print(arr[1, -1])   # 6  — 第1行最后一列

# 切片
print(arr[0:2, 1:3])
# [[2 3]
#  [5 6]]

print(arr[::2, ::2])
# [[1 3]
#  [7 9]]
```

### 3.3 布尔索引（核心！）

布尔索引是 NumPy 最强大的功能之一，用于条件筛选。

```python
arr = np.array([15, 22, 8, 35, 12, 40, 5])

# 创建布尔掩码
mask = arr > 20
print(mask)        # [False  True False  True False  True False]

# 用掩码筛选
result = arr[mask]
print(result)      # [22 35 40]

# 更复杂的条件
mask2 = (arr > 10) & (arr < 30)  # 注意：用 & 而不是 and
result2 = arr[mask2]
print(result2)     # [15 22 12]

# 用 ~ 取反
mask3 = ~(arr > 20)
print(arr[mask3])  # [15  8 12  5]

# 多维布尔索引
data = np.array([[10, 20, 30],
                 [40, 50, 60],
                 [70, 80, 90]])

# 筛选大于 40 的所有元素
result = data[data > 40]
print(result)      # [50 60 70 80 90]
```

### 3.4 花式索引（Fancy Indexing）

```python
arr = np.array([10, 20, 30, 40, 50])

# 用整数数组索引
indices = np.array([0, 2, 4])
print(arr[indices])  # [10 30 50]

# 二维花式索引
arr2d = np.array([[1, 2], [3, 4], [5, 6], [7, 8]])
row_indices = np.array([0, 2, 3])
col_indices = np.array([1, 0, 1])

print(arr2d[row_indices, col_indices])  # [2, 5, 8]
```

---

## 4. 广播机制（Broadcasting）

广播是 NumPy 的核心机制，允许不同形状的数组进行运算。

### 4.1 广播规则

当两个数组进行运算时，NumPy 从后往前逐维度比较：
1. **维度相等**：直接运算
2. **一个维度为 1**：自动扩展
3. **都不满足**：报错

```
Shape:      (4, 3)  +  (3,)    →  不匹配！
Shape:      (4, 3)  +  (1, 3)  →  可广播：(4, 3)
Shape:      (4, 3)  +  (4, 1)  →  可广播：(4, 3)
Shape:      (4, 3)  +  ()      →  可广播：(4, 3)  标量
```

### 4.2 广播实战

```python
# 标量广播
arr = np.array([[1, 2, 3],
                [4, 5, 6]])
result = arr + 10
print(result)
# [[11 12 13]
#  [14 15 16]]

# 列向量广播
col = np.array([[10], [20]])  # shape: (2, 1)
result = arr + col
print(result)
# [[11 12 13]
#  [24 25 26]]

# 每行减去均值（数据标准化常用）
data = np.array([[1, 2, 3],
                 [4, 5, 6],
                 [7, 8, 9]])

row_means = data.mean(axis=1, keepdims=True)  # shape: (3, 1)
print(row_means)
# [[2.]
#  [5.]
#  [8.]]

standardized = data - row_means
print(standardized)
# [[-1.  0.  1.]
#  [-1.  0.  1.]
#  [-1.  0.  1.]]
```

---

## 5. 数组操作

### 5.1 形状操作

```python
arr = np.arange(12)

# reshape（总元素数必须一致）
arr2d = arr.reshape(3, 4)
print(arr2d)

# -1 自动计算
arr3d = arr.reshape(2, 2, -1)  # shape: (2, 2, 3)
print(arr3d.shape)  # (2, 2, 3)

# flatten（返回副本）vs ravel（返回视图）
flat = arr2d.flatten()
flat[0] = 999
print(arr2d[0, 0])  # 0（未改变）— flatten 是副本

ravel = arr2d.ravel()
ravel[0] = 999
print(arr2d[0, 0])  # 999（已改变）— ravel 是视图

# 转置
print(arr2d.T)
```

### 5.2 数组拼接

```python
a = np.array([[1, 2], [3, 4]])
b = np.array([[5, 6], [7, 8]])

# 垂直堆叠
v = np.vstack((a, b))  # 等同于 np.concatenate((a, b), axis=0)
print(v)
# [[1 2]
#  [3 4]
#  [5 6]
#  [7 8]]

# 水平堆叠
h = np.hstack((a, b))  # 等同于 np.concatenate((a, b), axis=1)
print(h)
# [[1 2 5 6]
#  [3 4 7 8]]

# 深度堆叠（三维）
d = np.dstack((a, b))
print(d.shape)  # (2, 2, 2)
```

### 5.3 数组拆分

```python
arr = np.arange(16).reshape(4, 4)

# 垂直拆分
top, bottom = np.vsplit(arr, 2)
print("Top:\n", top)
print("Bottom:\n", bottom)

# 水平拆分
left, right = np.hsplit(arr, 2)
print("Left:\n", left)
print("Right:\n", right)
```

---

## 6. 常用数学函数

### 6.1 统计函数

```python
arr = np.array([[1, 2, 3],
                [4, 5, 6],
                [7, 8, 9]], dtype=float)

print("mean:", arr.mean())         # 5.0  全局均值
print("std:", arr.std())           # 2.58 全局标准差
print("var:", arr.var())           # 6.67 全局方差
print("min:", arr.min())           # 1.0
print("max:", arr.max())           # 9.0
print("sum:", arr.sum())           # 45.0

# 沿 axis 操作
print("行均值:", arr.mean(axis=1))  # [2. 5. 8.]  每行的均值
print("列均值:", arr.mean(axis=0))  # [4. 5. 6.]  每列的均值
print("行求和:", arr.sum(axis=1))   # [ 6. 15. 24.]

# argmin/argmax — 返回最大/最小值的索引
print("最大值位置:", arr.argmax())   # 8
print("每行最大值位置:", arr.argmax(axis=1))  # [2 2 2]

# cumsum — 累积和
print("累积和:", arr.sum(axis=0))    # [12. 15. 18.]
print("逐行累积和:\n", np.cumsum(arr, axis=1))
```

### 6.2 三角函数

```python
angles = np.array([0, 30, 45, 60, 90])
radians = np.radians(angles)  # 角度转弧度

print("sin:", np.sin(radians))
print("cos:", np.cos(radians))
print("tan:", np.tan(radians))
```

### 6.3 线性代数

```python
# 矩阵乘法
a = np.array([[1, 2], [3, 4]])
b = np.array([[5, 6], [7, 8]])

# 方法1: @ 运算符（推荐）
c = a @ b
print("矩阵乘法:\n", c)
# [[19 22]
#  [43 50]]

# 方法2: np.dot
c2 = np.dot(a, b)

# 方法3: np.matmul
c3 = np.matmul(a, b)

# 转置
print("转置:\n", a.T)

# 逆矩阵
print("逆矩阵:\n", np.linalg.inv(a))

# 行列式
print("行列式:", np.linalg.det(a))  # -2.0

# 特征值和特征向量
eigenvalues, eigenvectors = np.linalg.eig(a)
print("特征值:", eigenvalues)
print("特征向量:\n", eigenvectors)

# 解线性方程组 Ax = b
A = np.array([[3, 1], [1, 2]])
b = np.array([9, 8])
x = np.linalg.solve(A, b)
print("解:", x)  # [2. 3.]
```

---

## 7. 实战：数据分析场景

### 7.1 数据清洗示例

```python
import numpy as np

# 模拟销售数据（含缺失值用 NaN 表示）
sales = np.array([100, 200, np.nan, 350, 400, np.nan, 500, 150, 300, 450])

# 统计缺失值
nan_count = np.isnan(sales).sum()
print(f"缺失值数量: {nan_count}")

# 用均值填充
mean_val = np.nanmean(sales)
sales_clean = np.where(np.isnan(sales), mean_val, sales)
print(f"清洗后数据: {sales_clean}")

# 计算统计指标
print(f"平均销售额: {np.mean(sales_clean):.2f}")
print(f"标准差: {np.std(sales_clean):.2f}")
print(f"中位数: {np.median(sales_clean):.2f}")
```

### 7.2 股票数据分析

```python
import numpy as np

# 模拟 30 天股票价格
np.random.seed(42)
prices = np.cumsum(np.random.randn(30) * 2) + 100

# 计算收益率
returns = np.diff(prices) / prices[:-1] * 100

# 计算移动平均（5日均线）
window = 5
ma5 = np.convolve(prices, np.ones(window)/window, mode='valid')

# 计算波动率
volatility = np.std(returns)

# 查找最高价和最低价
max_price = np.max(prices)
min_price = np.min(prices)
max_day = np.argmax(prices)
min_day = np.argmin(prices)

print(f"最高价: {max_price:.2f} (第{max_day}天)")
print(f"最低价: {min_price:.2f} (第{min_day}天)")
print(f"日均波动: {volatility:.2f}%")
print(f"总收益率: {(prices[-1]/prices[0]-1)*100:.2f}%")
```

---

## 8. 常用方法速查表

| 方法 | 功能 | 示例 |
|------|------|------|
| `np.array()` | 创建数组 | `np.array([1,2,3])` |
| `np.zeros()` | 全零数组 | `np.zeros((3,4))` |
| `np.ones()` | 全一数组 | `np.ones((2,3))` |
| `np.arange()` | 等差序列 | `np.arange(0, 10, 2)` |
| `np.linspace()` | 等间距序列 | `np.linspace(0, 1, 5)` |
| `np.random.randn()` | 正态随机数 | `np.random.randn(3,3)` |
| `arr.reshape()` | 改变形状 | `arr.reshape(3,4)` |
| `arr.flatten()` | 展平为一维 | `arr.flatten()` |
| `arr.mean()` | 均值 | `arr.mean(axis=0)` |
| `arr.sum()` | 求和 | `arr.sum(axis=1)` |
| `arr.std()` | 标准差 | `arr.std()` |
| `np.where()` | 条件选择 | `np.where(arr>0, 1, 0)` |
| `np.dot()` | 矩阵乘法 | `np.dot(a, b)` |
| `np.linalg.inv()` | 逆矩阵 | `np.linalg.inv(a)` |

---

## 🧠 思考题

1. **为什么 NumPy 数组比 Python 列表快？** 从内存布局、数据类型、CPU 缓存、C 底层实现等角度思考。

2. **视图 vs 副本**：`arr.ravel()` 和 `arr.flatten()` 的区别是什么？在什么场景下应该用哪个？

3. **广播的限制**：为什么 `np.array([[1,2,3],[4,5,6]]) + np.array([1,2])` 会报错？如何修复？

4. **性能陷阱**：以下哪种方式计算数组元素之和更快？为什么？
   ```python
   a = np.arange(1_000_000)
   # 方式A: np.sum(a)
   # 方式B: sum(a)
   ```

5. **轴的理解**：`np.mean(arr, axis=0)` 和 `np.mean(arr, axis=1)` 的结果分别代表什么含义？画图说明。

---

## 📚 参考资源

- [NumPy 官方文档](https://numpy.org/doc/stable/)
- [NumPy 100 Exercises](https://github.com/rougier/numpy-100)
- 《利用 Python 进行数据分析》第 4 章

---

> **明天预告**：Day 080 — Pandas 数据分析，学习 DataFrame 操作与数据清洗
