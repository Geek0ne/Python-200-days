#!/usr/bin/env python3
"""
Day 018 — 基础用法：列表/字典/集合推导式

重点：
1. 列表推导式基础语法与多种变体
2. 字典推导式 — 键值变换、合并、过滤
3. 集合推导式 — 去重、映射转换
4. 条件过滤与三元表达式结合
"""

import sys
import os

# 确保能找到项目工具
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title: str):
    """打印章节分隔"""
    console.section(title)


# ══════════════════════════════════════════════════════════
# 1. 列表推导式基础
# ══════════════════════════════════════════════════════════
section("1. 列表推导式基础")

print("--- 1.1 基本语法 ---")
# [expression for item in iterable]
squares = [x ** 2 for x in range(10)]
print(f"平方列表: {squares}")

# 与手写循环等价
hand_coded = []
for x in range(10):
    hand_coded.append(x ** 2)
print(f"手写循环: {hand_coded}")
print(f"结果相同: {squares == hand_coded}")

print("\n--- 1.2 字符串操作 ---")
words = ['hello', 'world', 'python', 'comprehension']
uppercased = [w.upper() for w in words]
print(f"大写: {uppercased}")

lengths = [len(w) for w in words]
print(f"长度: {lengths}")

first_chars = [w[0] for w in words]
print(f"首字母: {first_chars}")

print("\n--- 1.3 类型转换 ---")
str_nums = ['1', '2', '3', '4', '5']
int_nums = [int(s) for s in str_nums]
print(f"字符串→整数: {int_nums}, 类型: {type(int_nums[0])}")

float_nums = [float(s) for s in str_nums]
print(f"字符串→浮点: {float_nums}")

print("\n--- 1.4 数学运算 ---")
nums = [1, 2, 3, 4, 5]
doubled = [n * 2 for n in nums]
print(f"翻倍: {doubled}")

cubes = [n ** 3 for n in nums]
print(f"立方: {cubes}")

negatives = [-n for n in nums]
print(f"取反: {negatives}")


# ══════════════════════════════════════════════════════════
# 2. 条件过滤
# ══════════════════════════════════════════════════════════
section("2. 条件过滤")

print("--- 2.1 基本 if 过滤 ---")
evens = [x for x in range(20) if x % 2 == 0]
print(f"偶数: {evens}")

odds = [x for x in range(20) if x % 2 != 0]
print(f"奇数: {odds}")

print("\n--- 2.2 多个条件 ---")
# 多个 if 相当于 and
filtered = [x for x in range(50) if x > 10 if x < 40 if x % 5 == 0]
print(f"10 < x < 40 且被5整除: {filtered}")
# 等价于: [x for x in range(50) if x > 10 and x < 40 and x % 5 == 0]

print("\n--- 2.3 三元表达式 + 推导式 ---")
nums = range(10)
labels = ['even' if x % 2 == 0 else 'odd' for x in nums]
print(f"奇偶标签: {labels}")

# 三元表达式在表达式位置 vs if 在过滤位置
# [A if condition else B for x in ...]  ← 三元表达式：始终有元素
# [A              for x in ... if cond]  ← 过滤：可选添加
signed = [x if x % 2 == 0 else -x for x in range(10)]
print(f"偶数保留/奇数取反: {signed}")

print("\n--- 2.4 实际场景 ---")
# 文件后缀过滤
files = ['cat.jpg', 'doc.pdf', 'dog.png', 'sheet.xlsx', 'bird.gif']
images = [f for f in files if f.endswith(('.jpg', '.png', '.gif'))]
print(f"图片文件: {images}")

# 字符串清洗
words = [' Hello ', 'WORLD', '  Python  ', ' CODE ', '   ']
cleaned = [w.strip().lower() for w in words if w.strip()]
print(f"清洗后: {cleaned}")


# ══════════════════════════════════════════════════════════
# 3. 字典推导式
# ══════════════════════════════════════════════════════════
section("3. 字典推导式")

print("--- 3.1 基本键值变换 ---")
squares_dict = {x: x ** 2 for x in range(5)}
print(f"平方字典: {squares_dict}")

# 从键格式转换
names = ['Alice', 'Bob', 'Charlie']
name_len = {name: len(name) for name in names}
print(f"名字→长度: {name_len}")

print("\n--- 3.2 从两个列表构建 ---")
keys = ['a', 'b', 'c']
values = [1, 2, 3]
d = {k: v for k, v in zip(keys, values)}
print(f"zip构建: {d}")

print("\n--- 3.3 字典过滤 ---")
scores = {'Alice': 85, 'Bob': 42, 'Charlie': 73, 'Diana': 91}
passed = {name: score for name, score in scores.items() if score >= 60}
print(f"及格: {passed}")

high_scores = {name: score for name, score in scores.items() if score >= 80}
print(f"高分: {high_scores}")

print("\n--- 3.4 键值互换 ---")
original = {'a': 1, 'b': 2, 'c': 3}
reversed_dict = {v: k for k, v in original.items()}
print(f"反转: {reversed_dict}")

# 注意：值重复时会覆盖前面的
dup = {'a': 1, 'b': 2, 'c': 1, 'd': 3}
dup_reversed = {v: k for k, v in dup.items()}
print(f"有重复值反转(后覆盖前): {dup_reversed}")

print("\n--- 3.5 枚举索引 ---")
items = ['apple', 'banana', 'cherry']
indexed = {i: item for i, item in enumerate(items)}
print(f"索引字典: {indexed}")

# 条件索引
even_indexed = {i: item for i, item in enumerate(items) if i % 2 == 0}
print(f"偶数索引: {even_indexed}")


# ══════════════════════════════════════════════════════════
# 4. 集合推导式
# ══════════════════════════════════════════════════════════
section("4. 集合推导式")

print("--- 4.1 基本去重 ---")
nums = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4]
unique_squares = {x ** 2 for x in nums}
print(f"平方去重: {unique_squares}")
print(f"类型: {type(unique_squares)}")

print("\n--- 4.2 从字符串获取唯一字母 ---")
word = "hello world"
unique_chars = {c for c in word if c != ' '}
print(f"唯一字母: {sorted(unique_chars)}")

print("\n--- 4.3 条件集合 ---")
evens_set = {x for x in range(20) if x > 5 and x % 2 == 0}
print(f"大于5的偶数: {evens_set}")

print("\n--- 4.4 单词长度去重 ---")
words = ['hi', 'hello', 'hey', 'howdy', 'hola', 'he']
unique_lengths = {len(w) for w in words}
print(f"唯一长度: {unique_lengths}")

# 与列表推导式对比
list_lengths = [len(w) for w in words]
print(f"列表长度: {list_lengths}")  # 有重复


# ══════════════════════════════════════════════════════════
# 5. 嵌套推导式
# ══════════════════════════════════════════════════════════
section("5. 嵌套推导式基础")

print("--- 5.1 二维扁平化 ---")
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flat = [num for row in matrix for num in row]
print(f"扁平化: {flat}")

# 等价手写
flat_manual = []
for row in matrix:
    for num in row:
        flat_manual.append(num)
print(f"手写等价: {flat_manual}")
print(f"结果相同: {flat == flat_manual}")

print("\n--- 5.2 多个可迭代对象的笛卡尔积 ---")
colors = ['red', 'blue']
sizes = ['S', 'M', 'L']
products = [(c, s) for c in colors for s in sizes]
print(f"笛卡尔积: {products}")

print("\n--- 5.3 嵌套推导式执行顺序验证 ---")
result = [f"{a}+{b}" for a in ['x', 'y'] for b in [1, 2]]
print(f"顺序验证: {result}")
# 预期: x+1 → x+2 → y+1 → y+2


if __name__ == '__main__':
    print("\n✅ Day 018 — 推导式基础用法示例完成")
    print("📌 关键总结：")
    print("   列表推导式 [expr for x in iterable if cond]")
    print("   字典推导式 {key: val for x in iterable if cond}")
    print("   集合推导式 {expr for x in iterable if cond}")
    print("   嵌套推导式按照从左到右、从外到内的顺序执行")
