#!/usr/bin/env python3
"""
Day 079 - NumPy 基础用法
演示 ndarray 的创建、属性、索引与切片
"""

import numpy as np

print("=" * 60)
print("NumPy 基础用法演示")
print("=" * 60)

# ─── 1. 创建数组 ───────────────────────────────────────
print("\n【1】创建数组")

# 从列表创建
arr1 = np.array([1, 2, 3, 4, 5])
print(f"一维数组: {arr1}")
print(f"类型: {type(arr1)}")

# 二维数组
arr2 = np.array([[1, 2, 3], [4, 5, 6]])
print(f"二维数组:\n{arr2}")

# 特殊数组
print(f"\n全零数组 (2x3):\n{np.zeros((2, 3))}")
print(f"\n全一数组 (2x3):\n{np.ones((2, 3))}")
print(f"\n单位矩阵 (3x3):\n{np.eye(3)}")
print(f"\n等差序列 arange(0, 10, 2): {np.arange(0, 10, 2)}")
print(f"\n等间距序列 linspace(0, 1, 5): {np.linspace(0, 1, 5)}")

# ─── 2. 数组属性 ───────────────────────────────────────
print("\n【2】数组属性")
arr = np.array([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
print(f"数组:\n{arr}")
print(f"shape (形状): {arr.shape}")
print(f"ndim (维度数): {arr.ndim}")
print(f"size (元素总数): {arr.size}")
print(f"dtype (数据类型): {arr.dtype}")
print(f"itemsize (每元素字节数): {arr.itemsize}")
print(f"nbytes (总字节数): {arr.nbytes}")

# ─── 3. 索引与切片 ─────────────────────────────────────
print("\n【3】索引与切片")
arr = np.array([10, 20, 30, 40, 50])
print(f"数组: {arr}")
print(f"arr[0] = {arr[0]}")
print(f"arr[-1] = {arr[-1]}")
print(f"arr[1:4] = {arr[1:4]}")
print(f"arr[::2] = {arr[::2]}")
print(f"arr[::-1] = {arr[::-1]}")

# 二维索引
arr2d = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
print(f"\n二维数组:\n{arr2d}")
print(f"arr2d[0, 1] = {arr2d[0, 1]}")
print(f"arr2d[0:2, 1:3] =\n{arr2d[0:2, 1:3]}")

# 布尔索引
print("\n【布尔索引】")
data = np.array([15, 22, 8, 35, 12, 40, 5])
print(f"原始数据: {data}")
mask = data > 20
print(f"布尔掩码: {mask}")
print(f"大于20的元素: {data[mask]}")
print(f"在10到30之间的元素: {data[(data > 10) & (data < 30)]}")

# ─── 4. 广播机制 ───────────────────────────────────────
print("\n【4】广播机制演示")
a = np.array([[1, 2, 3],
              [4, 5, 6]])
print(f"原始数组:\n{a}")

# 标量广播
print(f"\n加上标量10:\n{a + 10}")

# 列向量广播
col = np.array([[10], [20]])
print(f"\n加上列向量 [[10],[20]]:\n{a + col}")

# 每行减均值
row_means = a.mean(axis=1, keepdims=True)
print(f"\n每行均值: {row_means.flatten()}")
print(f"标准化后:\n{a - row_means}")

# ─── 5. 常用数学函数 ───────────────────────────────────
print("\n【5】常用数学函数")
arr = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float)
print(f"数组:\n{arr}")
print(f"均值: {arr.mean():.2f}")
print(f"标准差: {arr.std():.2f}")
print(f"最小值: {arr.min()}")
print(f"最大值: {arr.max()}")
print(f"求和: {arr.sum()}")

print(f"\n行均值 (axis=1): {arr.mean(axis=1)}")
print(f"列均值 (axis=0): {arr.mean(axis=0)}")
print(f"每行最大值索引: {arr.argmax(axis=1)}")

# ─── 6. 矩阵运算 ───────────────────────────────────────
print("\n【6】矩阵运算")
a = np.array([[1, 2], [3, 4]])
b = np.array([[5, 6], [7, 8]])
print(f"A:\n{a}")
print(f"B:\n{b}")
print(f"A @ B:\n{a @ b}")
print(f"逆矩阵:\n{np.linalg.inv(a)}")
print(f"行列式: {np.linalg.det(a):.2f}")

# 解线性方程组
A = np.array([[3, 1], [1, 2]])
b = np.array([9, 8])
x = np.linalg.solve(A, b)
print(f"\n解方程组 3x + y = 9, x + 2y = 8:")
print(f"x = {x[0]:.2f}, y = {x[1]:.2f}")

print("\n" + "=" * 60)
print("✅ 基础用法演示完成！")
print("=" * 60)
