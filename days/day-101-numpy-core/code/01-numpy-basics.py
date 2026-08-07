#!/usr/bin/env python3
"""
Day 101 — NumPy 核心：基础用法
演示 ndarray 的创建、属性查看和基本运算
"""

import numpy as np

print("=" * 60)
print("NumPy 基础：ndarray 创建与属性")
print("=" * 60)

# ── 1. 从 Python 列表创建 ──
arr_1d = np.array([1, 2, 3, 4, 5])
arr_2d = np.array([[1, 2, 3],
                   [4, 5, 6]])
arr_3d = np.array([[[1, 2], [3, 4]],
                    [[5, 6], [7, 8]]])

print("\n--- 1D 数组 ---")
print(f"数组: {arr_1d}")
print(f"shape: {arr_1d.shape}")       # (5,)
print(f"dtype: {arr_1d.dtype}")       # int64
print(f"ndim: {arr_1d.ndim}")         # 1
print(f"size: {arr_1d.size}")         # 5
print(f"itemsize: {arr_1d.itemsize}") # 8 字节

print("\n--- 2D 数组 ---")
print(f"数组:\n{arr_2d}")
print(f"shape: {arr_2d.shape}")       # (2, 3)
print(f"ndim: {arr_2d.ndim}")         # 2
print(f"转置:\n{arr_2d.T}")

print("\n--- 3D 数组 ---")
print(f"shape: {arr_3d.shape}")       # (2, 2, 2)
print(f"ndim: {arr_3d.ndim}")         # 3

# ── 2. 常用创建函数 ──
print("\n" + "=" * 60)
print("常用创建函数")
print("=" * 60)

print(f"\nzeros(3,4):\n{np.zeros((3, 4))}")
print(f"\nones(2,3):\n{np.ones((2, 3))}")
print(f"\nfull(2,2, 7.5):\n{np.full((2, 2), 7.5)}")
print(f"\neye(4) 单位矩阵:\n{np.eye(4)}")

# ── 3. 序列生成 ──
print("\n" + "=" * 60)
print("序列生成")
print("=" * 60)

print(f"\narange(0, 10, 2): {np.arange(0, 10, 2)}")
print(f"linspace(0, 1, 5): {np.linspace(0, 1, 5)}")
print(f"logspace(0, 3, 4): {np.logspace(0, 3, 4)}")

# ── 4. 随机数生成 ──
print("\n" + "=" * 60)
print("随机数生成")
print("=" * 60)

np.random.seed(42)  # 固定种子，保证可复现
print(f"\nrand(2,3) 均匀分布:\n{np.random.rand(2, 3)}")
print(f"\nrandn(2,3) 正态分布:\n{np.random.randn(2, 3)}")
print(f"\nrandint(0, 100, (2,3)) 随机整数:\n{np.random.randint(0, 100, (2, 3))}")

# ── 5. 基本运算 ──
print("\n" + "=" * 60)
print("基本运算（向量化）")
print("=" * 60)

a = np.array([1, 2, 3, 4, 5])
b = np.array([10, 20, 30, 40, 50])

print(f"\na + b = {a + b}")        # [11, 22, 33, 44, 55]
print(f"a * b = {a * b}")        # [10, 40, 90, 160, 250]
print(f"a ** 2 = {a ** 2}")      # [1, 4, 9, 16, 25]
print(f"np.sqrt(a) = {np.sqrt(a)}")
print(f"np.sum(a) = {np.sum(a)}")  # 15
print(f"np.mean(a) = {np.mean(a)}")  # 3.0
print(f"np.max(a) = {np.max(a)}")  # 5

# ── 6. dtype 指定 ──
print("\n" + "=" * 60)
print("dtype 与内存")
print("=" * 60)

arr_f32 = np.array([1.0, 2.0, 3.0], dtype=np.float32)
arr_f64 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
arr_i8 = np.array([100, 200], dtype=np.int8)

print(f"float32 数组: dtype={arr_f32.dtype}, itemsize={arr_f32.itemsize}字节, 总大小={arr_f32.nbytes}字节")
print(f"float64 数组: dtype={arr_f64.dtype}, itemsize={arr_f64.itemsize}字节, 总大小={arr_f64.nbytes}字节")
print(f"int8 数组:    dtype={arr_i8.dtype}, itemsize={arr_i8.itemsize}字节, 总大小={arr_i8.nbytes}字节")

# 内存占用对比
big_f32 = np.random.rand(1_000_000).astype(np.float32)
big_f64 = np.random.rand(1_000_000).astype(np.float64)
print(f"\n100万元素 float32 占用: {big_f32.nbytes / 1024 / 1024:.1f} MB")
print(f"100万元素 float64 占用: {big_f64.nbytes / 1024 / 1024:.1f} MB")
print(f"float64 比 float32 多用 {big_f64.nbytes / big_f32.nbytes:.0f}x 内存")

print("\n✅ 基础用法演示完成！")
