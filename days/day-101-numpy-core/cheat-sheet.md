# NumPy 核心 API 速查表

## 数组创建

| 函数 | 说明 | 示例 |
|------|------|------|
| `np.array(data)` | 从 Python 数据创建 | `np.array([1,2,3])` |
| `np.zeros(shape)` | 全零数组 | `np.zeros((3,4))` |
| `np.ones(shape)` | 全一数组 | `np.ones((2,3))` |
| `np.full(shape, val)` | 指定值填充 | `np.full((2,2), 5)` |
| `np.eye(n)` | 单位矩阵 | `np.eye(3)` |
| `np.empty(shape)` | 空数组（未初始化） | `np.empty((3,3))` |
| `np.arange(start, stop, step)` | 等差序列 | `np.arange(0, 10, 2)` |
| `np.linspace(start, stop, num)` | 等间隔序列 | `np.linspace(0, 1, 5)` |
| `np.logspace(start, stop, num)` | 等比序列 | `np.logspace(0, 3, 4)` |
| `np.random.rand(*shape)` | 均匀随机 [0,1) | `np.random.rand(3,4)` |
| `np.random.randn(*shape)` | 标准正态随机 | `np.random.randn(3,4)` |
| `np.random.randint(low, high, size)` | 随机整数 | `np.random.randint(0, 100, (3,4))` |

## 形状操作

| 函数 | 说明 | 示例 |
|------|------|------|
| `arr.reshape(*shape)` | 改变形状 | `arr.reshape(3, -1)` |
| `arr.flatten()` | 展平为副本 | `arr.flatten()` |
| `arr.ravel()` | 展平为视图 | `arr.ravel()` |
| `arr.T` | 转置 | `arr.T` |
| `np.concatenate(arrs)` | 拼接 | `np.concatenate([a, b])` |
| `np.stack(arrs)` | 堆叠 | `np.stack([a, b])` |
| `np.vstack(arrs)` | 垂直堆叠 | `np.vstack([a, b])` |
| `np.hstack(arrs)` | 水平堆叠 | `np.hstack([a, b])` |
| `np.split(arr, n)` | 拆分 | `np.split(arr, 3)` |

## 数学运算

| 函数 | 说明 | 函数 | 说明 |
|------|------|------|------|
| `np.sqrt(x)` | 平方根 | `np.abs(x)` | 绝对值 |
| `np.exp(x)` | 指数 | `np.log(x)` | 自然对数 |
| `np.log2(x)` | 以2为底对数 | `np.log10(x)` | 以10为底对数 |
| `np.sin(x)` | 正弦 | `np.cos(x)` | 余弦 |
| `np.round(x, n)` | 四舍五入 | `np.ceil(x)` | 向上取整 |
| `np.floor(x)` | 向下取整 | `np.clip(x, min, max)` | 裁剪范围 |

## 聚合函数

| 函数 | 说明 | `axis` 参数 |
|------|------|------------|
| `np.sum(x)` | 求和 | `axis=0` 沿行, `axis=1` 沿列 |
| `np.mean(x)` | 均值 | 同上 |
| `np.std(x)` | 标准差 | 同上 |
| `np.var(x)` | 方差 | 同上 |
| `np.min(x)` | 最小值 | 同上 |
| `np.max(x)` | 最大值 | 同上 |
| `np.argmin(x)` | 最小值索引 | 同上 |
| `np.argmax(x)` | 最大值索引 | 同上 |
| `np.median(x)` | 中位数 | 同上 |
| `np.percentile(x, q)` | 分位数 | 同上 |
| `np.cumsum(x)` | 累计求和 | 同上 |
| `np.cumprod(x)` | 累计乘积 | 同上 |

## 比较与逻辑

| 函数 | 说明 |
|------|------|
| `np.equal(a, b)` / `a == b` | 相等 |
| `np.greater(a, b)` / `a > b` | 大于 |
| `np.logical_and(a, b)` | 逻辑与 |
| `np.logical_or(a, b)` | 逻辑或 |
| `np.logical_not(a)` | 逻辑非 |
| `np.sum(bool_arr)` | True 的个数 |
| `np.any(bool_arr)` | 是否存在 True |
| `np.all(bool_arr)` | 是否全部 True |

## 线性代数

| 函数 | 说明 |
|------|------|
| `A @ B` / `np.dot(A, B)` | 矩阵乘法 |
| `np.linalg.inv(A)` | 逆矩阵 |
| `np.linalg.det(A)` | 行列式 |
| `np.linalg.eig(A)` | 特征值与特征向量 |
| `np.linalg.svd(A)` | SVD 分解 |
| `np.linalg.solve(A, b)` | 解线性方程组 |
| `np.linalg.norm(v)` | 范数 |
| `np.linalg.pinv(A)` | 伪逆 |

## 文件操作

| 函数 | 说明 |
|------|------|
| `np.save(path, arr)` | 保存为 .npy |
| `np.load(path)` | 加载 .npy |
| `np.savez(path, **arrs)` | 保存多个数组为 .npz |
| `np.savetxt(path, arr)` | 保存为文本 |
| `np.loadtxt(path)` | 加载文本 |
