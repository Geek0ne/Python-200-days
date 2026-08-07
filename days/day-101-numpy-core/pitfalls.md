# NumPy 常见陷阱与避坑指南

## 陷阱 1：视图 vs 副本的混淆

```python
# ❌ 切片是视图，修改会影响原数组
a = np.array([1, 2, 3, 4])
b = a[1:3]
b[0] = 99
print(a)  # [1, 99, 3, 4] ← 原数组被修改了！

# ✅ 用 copy() 创建独立副本
b = a[1:3].copy()
b[0] = 99
print(a)  # [1, 2, 3, 4] ← 原数组不受影响
```

## 陷阱 2：整数溢出

```python
# ❌ int8 最大值 127
arr = np.array([100], dtype=np.int8)
arr += 1  # 溢出！
print(arr)  # [-128] ← 不是你想要的

# ✅ 使用足够大的 dtype
arr = np.array([100], dtype=np.int64)
arr += 1
print(arr)  # [101]
```

## 陷阱 3：浮点精度

```python
# ❌ 浮点比较
a = np.array([0.1 + 0.2])
b = np.array([0.3])
print(a == b)  # [False] ← 浮点误差

# ✅ 使用 np.allclose()
print(np.allclose(a, b))  # True
```

## 陷阱 4：布尔索引返回副本

```python
arr = np.array([1, 2, 3, 4, 5])
mask = arr > 2
subset = arr[mask]   # 这是一个副本！
subset[0] = 99
print(arr)  # [1, 2, 3, 4, 5] ← 原数组未变

# 如果想修改原数组中满足条件的元素：
arr[arr > 2] = 0
print(arr)  # [1, 2, 0, 0, 0]
```

## 陷阱 5：reshape 与 flatten 的混淆

```python
# reshape(-1) 返回视图
a = np.array([[1, 2], [3, 4]])
b = a.reshape(-1)
b[0] = 99
print(a[0, 0])  # 99 ← 被修改了！

# flatten() 返回副本
c = a.flatten()
c[0] = 0
print(a[0, 0])  # 99 ← 不受影响
```

## 陷阱 6：axis 方向搞反

```python
arr = np.array([[1, 2, 3],
                [4, 5, 6]])

# axis=0 是沿行方向（跨行），结果是列的聚合
print(arr.mean(axis=0))  # [2.5, 3.5, 4.5] ← 每列的均值

# axis=1 是沿列方向（跨列），结果是行的聚合
print(arr.mean(axis=1))  # [2, 5] ← 每行的均值

# 记忆：axis=N 是"沿着第 N 个维度方向移动"
```

## 陷阱 7：广播形状不匹配

```python
# ❌ 报错
a = np.ones((3, 2))
b = np.ones((3,))
c = a + b  # ValueError!

# 原因：
# a.shape = (3, 2)
# b.shape = (3,) → 视为 (1, 3)
# 最右维度: 2 vs 3 → 不兼容

# ✅ 正确做法
b = b.reshape(3, 1)  # (3, 1) vs (3, 2) → 可以广播
c = a + b
```

## 陷阱 8：原地操作 vs 返回新数组

```python
arr = np.array([1.5, 2.5, 3.5])

# ❌ np.floor 不修改原数组
result = np.floor(arr)
print(arr)  # [1.5, 2.5, 3.5] ← 未变

# ✅ 用 out 参数或重新赋值
arr = np.floor(arr)
print(arr)  # [1, 2, 3]

# 或者用原地操作
np.floor(arr, out=arr)
```

## 陷阱 9：空数组的聚合

```python
empty = np.array([])

# ❌ 可能报错或返回 nan
print(empty.max())  # RuntimeWarning: empty sequence

# ✅ 检查是否为空
if empty.size > 0:
    print(empty.max())
```

## 陷阱 10：大数据的内存问题

```python
# ❌ 不要这样创建大矩阵
a = np.random.rand(10000, 10000)  # ~800 MB!
b = np.random.rand(10000, 10000)
c = a + b  # 再分配 ~800 MB

# ✅ 使用 float32 节省内存
a = np.random.rand(10000, 10000).astype(np.float32)  # ~400 MB

# ✅ 使用预分配数组
result = np.empty_like(a)
np.add(a, b, out=result)
```
