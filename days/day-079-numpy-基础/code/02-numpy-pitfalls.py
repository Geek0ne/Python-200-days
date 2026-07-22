#!/usr/bin/env python3
"""
Day 079 - NumPy 进阶用法与常见陷阱
演示视图vs副本、类型陷阱、性能对比
"""

import numpy as np
import time

print("=" * 60)
print("NumPy 进阶用法与常见陷阱")
print("=" * 60)

# ─── 陷阱 1: 视图 vs 副本 ─────────────────────────────
print("\n【陷阱1】视图 vs 副本")
print("NumPy 切片返回视图，修改视图会改变原数组！\n")

arr = np.array([1, 2, 3, 4, 5])
print(f"原始数组: {arr}")

# 切片创建视图
view = arr[1:4]
print(f"视图 view = arr[1:4]: {view}")

view[0] = 999
print(f"修改 view[0] = 999 后:")
print(f"  视图: {view}")
print(f"  原数组: {arr}")  # 原数组也被修改了！

# 要创建副本，使用 copy()
arr2 = np.array([10, 20, 30, 40, 50])
copy = arr2[1:4].copy()
copy[0] = 999
print(f"\n使用 copy():")
print(f"  原数组: {arr2}")  # 原数组不变
print(f"  副本: {copy}")

# ─── 陷阱 2: 数据类型陷阱 ─────────────────────────────
print("\n【陷阱2】整数溢出")
arr_uint8 = np.array([100], dtype=np.uint8)
print(f"uint8 数组: {arr_uint8}")
arr_uint8 += 200  # 溢出！uint8 范围是 0-255
print(f"加200后（溢出）: {arr_uint8}")  # 不是 300，而是 300 % 256 = 44

arr_int8 = np.array([100], dtype=np.int8)
arr_int8 += 100
print(f"int8 数组加100后（溢出）: {arr_int8}")  # 200 超出 int8 范围(-128~127)

print("\n💡 建议：使用默认的 int64 或 float64 避免溢出")

# ─── 陷阱 3: 布尔索引与 and/or ────────────────────────
print("\n【陷阱3】布尔索引必须用 & | ~ 而不是 and/or/not")
arr = np.array([1, 2, 3, 4, 5])

# 正确写法
result = arr[(arr > 2) & (arr < 5)]
print(f"大于2且小于5: {result}")

# 错误写法会报错！
# result = arr[(arr > 2) and (arr < 5)]  # ❌ ValueError

# ─── 陷阱 4: shape 不匹配的广播 ────────────────────────
print("\n【陷阱4】广播规则不匹配")
a = np.array([[1, 2, 3], [4, 5, 6]])  # shape: (2, 3)
b = np.array([1, 2])                    # shape: (2,)

try:
    c = a + b
except ValueError as e:
    print(f"错误: {e}")
    print("原因: (2,3) 与 (2,) 无法广播")
    print("修复: 将 b 改为 (1,2) 或 (2,1)")

# ─── 陷阱 5: copy vs view 性能 ─────────────────────────
print("\n【性能对比】copy vs view")
arr = np.arange(10000)

# view 切片（几乎零开销）
start = time.time()
for _ in range(10000):
    _ = arr[1000:5000]
view_time = time.time() - start

# copy（需要分配内存）
start = time.time()
for _ in range(10000):
    _ = arr[1000:5000].copy()
copy_time = time.time() - start

print(f"View 切片 10000 次: {view_time:.4f}s")
print(f"Copy 切片 10000 次: {copy_time:.4f}s")
print(f"View 比 Copy 快约 {copy_time/view_time:.1f} 倍")

# ─── 陷阱 6: 修改形状失败 ─────────────────────────────
print("\n【陷阱5】reshape 的总元素数必须一致")
arr = np.arange(12)
try:
    arr.reshape(3, 5)  # 12 != 3*5
except ValueError as e:
    print(f"错误: {e}")
    print(f"修复: reshape(3,4) 或 reshape(4,3)")

# ─── 进阶技巧 ──────────────────────────────────────────
print("\n【进阶技巧1】np.where 条件选择")
arr = np.array([10, 20, 30, 40, 50])
result = np.where(arr > 25, '大', '小')
print(f"大于25为'大', 否则为'小': {result}")

# 嵌套 where
result2 = np.where(arr < 20, '低',
                   np.where(arr < 40, '中', '高'))
print(f"分级: {result2}")

print("\n【进阶技巧2】np.argpartition — 快速找第K大/小")
arr = np.array([30, 10, 50, 20, 40])
# 找第3小的元素（索引为2）
idx = np.argpartition(arr, 2)
print(f"原始: {arr}")
print(f"第3小的元素: {arr[idx[2]]}")
print(f"前3小的元素: {arr[idx[:3]]}")

print("\n【进阶技巧3】np.unique — 去重与计数")
arr = np.array([1, 2, 2, 3, 3, 3, 4, 4, 4, 4])
values, counts = np.unique(arr, return_counts=True)
print(f"唯一值: {values}")
print(f"计数: {counts}")

print("\n【进阶技巧4】np.searchsorted — 二分查找")
arr = np.array([10, 20, 30, 40, 50])
print(f"数组: {arr}")
print(f"插入 25 的位置: {np.searchsorted(arr, 25)}")
print(f"插入 0 的位置: {np.searchsorted(arr, 0)}")
print(f"插入 55 的位置: {np.searchsorted(arr, 55)}")

print("\n" + "=" * 60)
print("✅ 进阶用法演示完成！")
print("=" * 60)
