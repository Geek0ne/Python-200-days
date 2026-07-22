# NumPy API 速查表

## 数组创建

| 函数 | 说明 | 示例 |
|------|------|------|
| `np.array(obj)` | 从列表创建 | `np.array([1,2,3])` |
| `np.zeros(shape)` | 全零数组 | `np.zeros((3,4))` |
| `np.ones(shape)` | 全一数组 | `np.ones((2,3))` |
| `np.empty(shape)` | 未初始化 | `np.empty((2,2))` |
| `np.eye(n)` | 单位矩阵 | `np.eye(3)` |
| `np.full(shape, val)` | 全填充 | `np.full((2,3), 7)` |
| `np.arange(start, stop, step)` | 等差序列 | `np.arange(0,10,2)` |
| `np.linspace(start, stop, num)` | 等间距 | `np.linspace(0,1,5)` |

## 随机数

| 函数 | 说明 |
|------|------|
| `np.random.rand(d0,d1,...)` | 均匀分布 [0,1) |
| `np.random.randn(d0,d1,...)` | 标准正态分布 |
| `np.random.randint(low, high, size)` | 随机整数 |
| `np.random.random(size)` | 均匀分布 |
| `np.random.normal(loc, scale, size)` | 正态分布 |
| `np.random.seed(n)` | 固定随机种子 |

## 形状操作

| 函数 | 说明 |
|------|------|
| `arr.reshape(shape)` | 改变形状 |
| `arr.flatten()` | 展平（副本） |
| `arr.ravel()` | 展平（视图） |
| `arr.T` | 转置 |
| `np.vstack(arrs)` | 垂直堆叠 |
| `np.hstack(arrs)` | 水平堆叠 |
| `np.concatenate(arrs, axis)` | 指定轴拼接 |
| `np.split(arr, indices, axis)` | 拆分 |

## 数学函数

| 函数 | 说明 |
|------|------|
| `np.sum(arr, axis)` | 求和 |
| `np.mean(arr, axis)` | 均值 |
| `np.std(arr, axis)` | 标准差 |
| `np.var(arr, axis)` | 方差 |
| `np.min(arr, axis)` | 最小值 |
| `np.max(arr, axis)` | 最大值 |
| `np.argmin(arr, axis)` | 最小值索引 |
| `np.argmax(arr, axis)` | 最大值索引 |
| `np.cumsum(arr, axis)` | 累积和 |
| `np.cumprod(arr, axis)` | 累积积 |

## 线性代数

| 函数 | 说明 |
|------|------|
| `np.dot(a, b)` / `a @ b` | 矩阵乘法 |
| `np.linalg.inv(a)` | 逆矩阵 |
| `np.linalg.det(a)` | 行列式 |
| `np.linalg.eig(a)` | 特征值/特征向量 |
| `np.linalg.solve(A, b)` | 解线性方程组 |
| `np.linalg.norm(a)` | 范数 |

## 逻辑与条件

| 函数 | 说明 |
|------|------|
| `np.where(cond, x, y)` | 条件选择 |
| `np.unique(arr)` | 去重 |
| `np.in1d(a, b)` | 元素是否在 b 中 |
| `np.intersect1d(a, b)` | 交集 |
| `np.union1d(a, b)` | 并集 |
| `np.setdiff1d(a, b)` | 差集 |
