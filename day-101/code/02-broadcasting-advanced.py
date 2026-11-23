#!/usr/bin/env python3
"""
Day 101 — NumPy 核心：广播机制与向量化进阶
演示广播规则、常见陷阱和高效向量化技巧
"""

import numpy as np
import time

print("=" * 60)
print("广播机制 (Broadcasting) 详解")
print("=" * 60)

# ── 1. 广播的基本规则 ──
print("\n--- 规则演示 ---")

# 标量 + 数组
a = np.array([[1, 2, 3],
              [4, 5, 6]])
print(f"2D数组 + 标量:\n{a + 10}")

# 不同形状的广播
x = np.array([[1], [2], [3]])   # (3, 1)
y = np.array([10, 20, 30])      # (3,) → 视为 (1, 3)
result = x + y                   # 广播为 (3, 3)
print(f"\n(3,1) + (1,3) 广播结果:\n{result}")

# ── 2. 广播的维度对齐规则 ──
print("\n--- 维度对齐规则 ---")

# 规则：从最右边维度开始逐一对齐
# (2, 3) + (3,) → (2,3) + (1,3) → (2,3) ✓
a = np.ones((2, 3))
b = np.array([1, 2, 3])
print(f"(2,3) + (3,) = (2,3):\n{a + b}")

# (4, 3) + (3,) → (4,3) + (1,3) → (4,3) ✓
a = np.ones((4, 3))
b = np.array([1, 2, 3])
print(f"\n(4,3) + (3,) = (4,3):\n{a + b}")

# ── 3. 广播失败的场景 ──
print("\n--- 广播失败示例 ---")

try:
    a = np.ones((3, 2))
    b = np.ones((3,))
    c = a + b  # (3,2) vs (3,) → (3,2) vs (1,3) → 维度不匹配！
except ValueError as e:
    print(f"❌ 失败: {e}")

# 解决方法：reshape
b_reshaped = b.reshape(3, 1)  # (3,1) vs (3,2) → 可以广播
print(f"修复: reshape 后\n{a + b_reshaped}")

# ── 4. 广播实战：数据归一化 ──
print("\n--- 实战：数据归一化 ---")

# 模拟 5 个学生、3 门课的成绩
np.random.seed(42)
scores = np.random.randint(50, 100, (5, 3))
subjects = ["数学", "英语", "物理"]
students = ["张三", "李四", "王五", "赵六", "钱七"]

print(f"原始成绩:")
for i, name in enumerate(students):
    print(f"  {name}: {dict(zip(subjects, scores[i]))}")

# Z-Score 标准化：(x - mean) / std
mean = scores.mean(axis=0)    # 每列均值，shape=(3,)
std = scores.std(axis=0)      # 每列标准差，shape=(3,)
normalized = (scores - mean) / std  # 广播: (5,3) - (3,) / (3,)

print(f"\n每门课均值: {mean}")
print(f"每门课标准差: {std}")
print(f"标准化后:")
for i, name in enumerate(students):
    print(f"  {name}: {[f'{v:.2f}' for v in normalized[i]]}")

# ── 5. 广播实战：距离矩阵 ──
print("\n--- 实战：计算距离矩阵 ---")

# 3 个二维点
points = np.array([[0, 0],
                   [3, 0],
                   [0, 4]])

# 计算两两之间的欧氏距离
# ||a - b||² = ||a||² + ||b||² - 2 * a·b
sq_x = np.sum(points ** 2, axis=1)       # (3,)
dist_sq = sq_x[:, None] + sq_x[None, :]  # (3, 3) 广播
dist_sq -= 2 * points @ points.T          # (3, 3)
np.maximum(dist_sq, 0, out=dist_sq)       # 数值稳定性
dist = np.sqrt(dist_sq)

print("距离矩阵:")
print(np.array2string(dist, precision=2, suppress_small=True))
print(f"(0,0) → (3,0) 距离: {dist[0,1]:.2f}")
print(f"(0,0) → (0,4) 距离: {dist[0,2]:.2f}")

# ── 6. 向量化 vs 循环 性能对比 ──
print("\n" + "=" * 60)
print("向量化 vs 循环 性能对比")
print("=" * 60)

data = np.random.rand(100_000)

# 循环方式
start = time.time()
result_loop = np.zeros(len(data))
for i in range(len(data)):
    result_loop[i] = np.sin(data[i]) ** 2 + np.cos(data[i]) ** 2
t_loop = time.time() - start

# 向量化方式
start = time.time()
result_vec = np.sin(data) ** 2 + np.cos(data) ** 2
t_vec = time.time() - start

print(f"\n计算 sin²(x) + cos²(x) (10万元素):")
print(f"  循环方式:   {t_loop:.4f}s")
print(f"  向量化方式: {t_vec:.6f}s")
print(f"  加速比:     {t_loop / t_vec:.0f}x")
print(f"  结果相同:   {np.allclose(result_loop, result_vec)}")

# ── 7. 花式索引与布尔索引避坑 ──
print("\n" + "=" * 60)
print("索引避坑指南")
print("=" * 60)

arr = np.arange(20).reshape(4, 5)
print(f"原始数组:\n{arr}")

# 布尔索引返回的是副本！
mask = arr > 10
subset = arr[mask]
subset[0] = 999  # 修改副本
print(f"\n布尔索引后修改子集: {subset[0]}")
print(f"原始数组不变: {arr[0, 0]}")

# 花式索引也是副本
rows = np.array([0, 2])
subset2 = arr[rows]
subset2[0, 0] = 888
print(f"\n花式索引后修改子集: {subset2[0, 0]}")
print(f"原始数组不变: {arr[0, 0]}")

# 唯一保持视图的操作：基础切片
view = arr[0:2, 0:2]
view[0, 0] = 777
print(f"\n切片后修改视图: {view[0, 0]}")
print(f"原始数组被修改: {arr[0, 0]}")

print("\n✅ 广播与向量化进阶演示完成！")
