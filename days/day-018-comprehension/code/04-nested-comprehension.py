#!/usr/bin/env python3
"""
Day 018 — 嵌套推导式与条件过滤进阶

深入探索嵌套推导式的各种用法：
1. 多维数据扁平化
2. 矩阵转置与旋转
3. 笛卡尔积与组合生成
4. 条件过滤的高级技巧
5. 嵌套推导式的可读性边界
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title):
    console.section(title)


# ══════════════════════════════════════════════════════════
# 1. 嵌套推导式：扁平化
# ══════════════════════════════════════════════════════════
section("1. 嵌套推导式：扁平化")

print("--- 1.1 基本扁平化 ---")
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flat = [num for row in matrix for num in row]
print(f"原始矩阵: {matrix}")
print(f"扁平化:   {flat}")

print("\n--- 1.2 深层嵌套扁平化（仅一层） ---")
deep = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
# 这是扁平化一层，不是完全扁平化
flat_one = [inner for outer in deep for inner in outer]
print(f"深层嵌套: {deep}")
print(f"扁平一层: {flat_one}")

print("\n--- 1.3 字符串列表扁平化 ---")
sentences = [['hello', 'world'], ['python', 'is', 'great'], ['comprehensions']]
all_words = [word for sentence in sentences for word in sentence]
print(f"原始: {sentences}")
print(f"合并: {all_words}")


# ══════════════════════════════════════════════════════════
# 2. 矩阵操作
# ══════════════════════════════════════════════════════════
section("2. 矩阵操作")

print("--- 2.1 矩阵转置 ---")
matrix = [[1, 2, 3],
          [4, 5, 6]]

transposed = [[row[i] for row in matrix] for i in range(3)]
print(f"原始:\n{matrix[0]}\n{matrix[1]}")
print(f"转置:\n{transposed[0]}\n{transposed[1]}\n{transposed[2]}")

print("\n--- 2.2 矩阵旋转 90° 顺时针 ---")
def rotate_cw(mat):
    """顺时针旋转矩阵 90°"""
    if not mat:
        return []
    return [[mat[len(mat) - 1 - j][i] for j in range(len(mat))]
            for i in range(len(mat[0]))]


def rotate_ccw(mat):
    """逆时针旋转矩阵 90°"""
    if not mat:
        return []
    return [[mat[j][len(mat[0]) - 1 - i] for j in range(len(mat))]
            for i in range(len(mat[0]))]


m = [[1, 2],
     [3, 4],
     [5, 6]]

print(f"原始 (3×2):")
for row in m:
    print(f"  {row}")

rotated = rotate_cw(m)
print(f"顺时针 90° (2×3):")
for row in rotated:
    print(f"  {row}")

rotated_ccw = rotate_ccw(m)
print(f"逆时针 90° (2×3):")
for row in rotated_ccw:
    print(f"  {row}")

print("\n--- 2.3 矩阵边界提取 ---")
m2 = [[1,  2,  3,  4],
      [5,  6,  7,  8],
      [9, 10, 11, 12]]

r, c = len(m2), len(m2[0])
top_row = m2[0]
bottom_row = m2[-1]
left_col = [m2[i][0] for i in range(1, r-1)]
right_col = [m2[i][c-1] for i in range(1, r-1)]
border = top_row + bottom_row + left_col + right_col
print(f"矩阵边界: {border}")

# 对角线元素
main_diag = [m2[i][i] for i in range(min(r, c))]
anti_diag = [m2[i][c-1-i] for i in range(min(r, c))]
print(f"主对角线: {main_diag}")
print(f"反对角线: {anti_diag}")


# ══════════════════════════════════════════════════════════
# 3. 笛卡尔积与组合
# ══════════════════════════════════════════════════════════
section("3. 笛卡尔积与组合")

print("--- 3.1 基本笛卡尔积 ---")
colors = ['red', 'green', 'blue']
sizes = ['S', 'M', 'L', 'XL']
products = [(c, s) for c in colors for s in sizes]
print(f"颜色×尺寸: {len(products)} 种组合")
for p in products[:6]:
    print(f"  {p}")

print("\n--- 3.2 条件笛卡尔积 ---")
# 只有和是奇数才保留
pairs = [(a, b) for a in [1, 2, 3] for b in [4, 5, 6] if (a + b) % 2 == 1]
print(f"和是奇数的有序对: {pairs}")

print("\n--- 3.3 对角线排除 ---")
# 生成所有 (i, j) 对，排除 i == j
pairs_no_diag = [(i, j) for i in range(4) for j in range(4) if i != j]
print(f"4×4 除去对角线: {len(pairs_no_diag)} 个")
print(f"前10个: {pairs_no_diag[:10]}")

print("\n--- 3.4 组合生成（不重复有序对） ---")
# 类似 itertools.combinations_with_replacement
items = ['A', 'B', 'C', 'D']
combos = [(items[i], items[j]) for i in range(len(items))
          for j in range(i+1, len(items))]
print(f"唯一有序对（组合）: {combos}")


# ══════════════════════════════════════════════════════════
# 4. 高级条件过滤
# ══════════════════════════════════════════════════════════
section("4. 高级条件过滤")

print("--- 4.1 多层条件过滤 ---")
data = range(100)
filtered = [x for x in data if x > 10 if x < 50 if x % 3 == 0 if x % 2 == 1]
print(f"10 < x < 50, 被3整除, 奇数: {filtered}")

print("\n--- 4.2 使用 any/all 进行条件 ---")
words = ['cat', 'elephant', 'dog', 'giraffe', 'ant', 'bee']
# 包含 'e' 或 'a' 的单词
has_e_or_a = [w for w in words if any(c in w for c in 'ea')]
print(f"含e或a: {has_e_or_a}")

# 所有字母都短于 5 的单词（从另一个角度）
short_words = [w for w in words if all(len(w) < 5 for _ in [1])]
# 简化版：
short_words = [w for w in words if len(w) < 5]
print(f"短单词: {short_words}")

print("\n--- 4.3 条件颠倒（去除非） ---")
nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
# 不是 3 的倍数
not_mult3 = [x for x in nums if x % 3 != 0]
print(f"非3倍数: {not_mult3}")

# 不包含 'a' 的单词
no_a = [w for w in ['apple', 'banana', 'cherry', 'date'] if 'a' not in w]
print(f"不含a: {no_a}")

print("\n--- 4.4 过滤 None 和空值 ---")
mixed = [0, 1, None, '', 'hello', [], [1, 2], False, True]
non_falsy = [x for x in mixed if x]
non_none = [x for x in mixed if x is not None]
print(f"原始:                {mixed}")
print(f"去假值:              {non_falsy}")
print(f"去 None:             {non_none}")


# ══════════════════════════════════════════════════════════
# 5. 嵌套推导式的可读性边界
# ══════════════════════════════════════════════════════════
section("5. 嵌套推导式的可读性边界")

print("--- 5.1 两层嵌套（推荐） ---")
matrix = [[1, 2], [3, 4], [5, 6]]
result_2 = [x for row in matrix for x in row]
print(f"两层嵌套: OK ✅")

print("\n--- 5.2 三层嵌套（可读性存疑） ---")
# 三维数据
data_3d = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
result_3 = [z for dim1 in data_3d for dim2 in dim1 for z in dim2]
print(f"三层嵌套: {result_3} (可读吗？🤔)")

print("\n--- 5.3 四层嵌套（应该避免！） ---")
# ❌ 以下仅为演示，不推荐在实际代码中使用
data_4d = [[[[1]]]]
result_4 = [w for d1 in data_4d for d2 in d1 for d3 in d2 for w in d3]
print(f"四层嵌套: {result_4} (无法理解！❌)")

print()
print("可读性指南:")
print("  两层嵌套: ✅ 推荐使用")
print("  三层嵌套: ⚠️ 看情况，建议拆开")
print("  四层或更多: ❌ 请使用普通循环或拆成多步")


if __name__ == '__main__':
    print("\n✅ Day 018 — 嵌套推导式与条件过滤进阶完成")
    print("📌 关键技巧：")
    print("   1. 嵌套推导式的执行顺序 = 从左到右、从外到内")
    print("   2. 条件过滤可以叠加多个 if")
    print("   3. any()/all() 可以在推导式内部做复杂条件判断")
    print("   4. 超过两层嵌套应拆分为多步")
