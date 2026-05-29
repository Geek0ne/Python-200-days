#!/usr/bin/env python3
"""
Day 006 — 列表基础操作演示
===========================
涵盖：创建、索引、切片、方法、列表推导式
可直接运行： python3 01-list-basics.py
"""

# ============================================================
# 1. 列表的多种创建方式
# ============================================================
print("=" * 60)
print("📦 1. 列表的多种创建方式")
print("=" * 60)

# 方式 1：字面量
fruits = ["苹果", "香蕉", "橘子", "葡萄", "西瓜"]
print(f"字面量创建: {fruits}")

# 方式 2：list() 构造器
chars = list("Python")
print(f"从字符串创建: {chars}")

# 方式 3：列表推导式
squares = [x**2 for x in range(1, 11)]
print(f"列表推导式: {squares}")

# 方式 4：range + list
numbers = list(range(0, 20, 3))
print(f"从 range 创建: {numbers}")

# ============================================================
# 2. 索引与切片
# ============================================================
print("\n" + "=" * 60)
print("🔍 2. 索引与切片")
print("=" * 60)

alphabet = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

# 正向索引
print(f"列表: {alphabet}")
print(f"alphabet[0]  = {alphabet[0]}")    # a
print(f"alphabet[4]  = {alphabet[4]}")    # e
print(f"alphabet[-1] = {alphabet[-1]}")   # j
print(f"alphabet[-3] = {alphabet[-3]}")   # h

# 切片操作
print(f"\nalphabet[2:5]     = {alphabet[2:5]}")        # [c, d, e]
print(f"alphabet[:4]      = {alphabet[:4]}")           # [a, b, c, d]
print(f"alphabet[6:]      = {alphabet[6:]}")           # [g, h, i, j]
print(f"alphabet[::2]     = {alphabet[::2]}")          # [a, c, e, g, i]
print(f"alphabet[::-1]    = {alphabet[::-1]}")         # 反转
print(f"alphabet[-5:-2]   = {alphabet[-5:-2]}")        # [f, g, h]
print(f"alphabet[1:8:3]   = {alphabet[1:8:3]}")        # [b, e, h]

# 切片赋值（高级用法）
values = [1, 2, 3, 4, 5, 6, 7, 8]
print(f"\n切片赋值前: {values}")

# 替换（数量不等）
values[2:5] = [30, 40]
print(f"values[2:5] = [30, 40]: {values}")  # [1, 2, 30, 40, 6, 7, 8]

# 插入
values[2:2] = [99, 100]
print(f"values[2:2] = [99, 100]: {values}")  # [1, 2, 99, 100, 30, 40, 6, 7, 8]

# 删除
values[2:4] = []
print(f"values[2:4] = []: {values}")  # [1, 2, 30, 40, 6, 7, 8]

# ============================================================
# 3. 列表方法演示
# ============================================================
print("\n" + "=" * 60)
print("🛠️  3. 列表方法演示")
print("=" * 60)

tasks = []

# append — 追加
tasks.append("写规划")
tasks.append("编码")
tasks.append("测试")
print(f"append 后: {tasks}")

# insert — 插入
tasks.insert(1, "需求分析")
print(f"insert 后: {tasks}")

# extend — 扩展
more_tasks = ["部署", "监控"]
tasks.extend(more_tasks)
print(f"extend 后: {tasks}")

# pop — 弹出
last = tasks.pop()
print(f"pop(): 弹出 '{last}' → {tasks}")

# pop 指定位置
first = tasks.pop(0)
print(f"pop(0): 弹出 '{first}' → {tasks}")

# remove — 删除指定值
tasks.remove("编码")
print(f"remove('编码'): {tasks}")

# index — 查找索引
try:
    pos = tasks.index("测试")
    print(f"index('测试') = {pos}")
except ValueError:
    print("'测试' 不在列表中")

# count — 统计
nums = [1, 2, 3, 2, 4, 2, 5]
print(f"\n列表: {nums}")
print(f"count(2) = {nums.count(2)}")
print(f"count(9) = {nums.count(9)}")

# in 运算符
print(f"3 in nums = {3 in nums}")
print(f"9 in nums = {9 in nums}")

# ============================================================
# 4. 排序与反转
# ============================================================
print("\n" + "=" * 60)
print("📊 4. 排序与反转")
print("=" * 60)

scores = [85, 92, 67, 78, 95, 88, 73]

# sort — 原地排序
scores.sort()
print(f"升序排序: {scores}")

scores.sort(reverse=True)
print(f"降序排序: {scores}")

# sorted — 返回新列表
original = [3, 1, 4, 1, 5, 9, 2, 6]
sorted_list = sorted(original)
print(f"\nsorted() 返回新列表: {sorted_list}")
print(f"原列表不受影响: {original}")

# key 排序
words = ["python", "java", "c", "javascript", "go", "rust"]
words.sort(key=len)
print(f"\n按长度排序: {words}")

words.sort(key=lambda w: w[-1])  # 按最后一个字母排序
print(f"按最后一个字母排序: {words}")

# reverse
words.reverse()
print(f"反转: {words}")

# ============================================================
# 5. 列表推导式
# ============================================================
print("\n" + "=" * 60)
print("🎯 5. 列表推导式")
print("=" * 60)

# 基础
squares = [x**2 for x in range(1, 11)]
print(f"1~10 的平方: {squares}")

# 带条件
even_squares = [x**2 for x in range(1, 11) if x % 2 == 0]
print(f"偶数的平方: {even_squares}")

# 嵌套循环
pairs = [(x, y) for x in range(1, 4) for y in range(1, 4)]
print(f"笛卡尔积: {pairs}")

# 条件表达式
labels = ["大" if x > 5 else "小" if x > 3 else "很小" for x in range(1, 9)]
print(f"条件标签: {labels}")

# 展平嵌套列表
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flattened = [num for row in matrix for num in row]
print(f"展平矩阵: {flattened}")

# ============================================================
# 6. 枚举与拉链
# ============================================================
print("\n" + "=" * 60)
print("🔗 6. enumerate 和 zip")
print("=" * 60)

# enumerate
names = ["Alice", "Bob", "Charlie"]
print("enumerate 示例:")
for i, name in enumerate(names):
    print(f"  索引 {i}: {name}")

# 指定起始索引
for i, name in enumerate(names, start=1):
    print(f"  第{i}名: {name}")

# zip
print("\nzip 示例:")
students = ["张三", "李四", "王五"]
chinese = [88, 95, 73]
math = [92, 88, 85]

for name, c, m in zip(students, chinese, math):
    print(f"  {name}: 语文 {c}, 数学 {m}")

# zip 解包
pairs = [(1, 'a'), (2, 'b'), (3, 'c')]
numbers, letters = zip(*pairs)
print(f"\nzip 解包后: numbers={list(numbers)}, letters={list(letters)}")

# ============================================================
# 7. 列表复制与深浅拷贝
# ============================================================
print("\n" + "=" * 60)
print("📋 7. 深浅拷贝演示")
print("=" * 60)

# 赋值 = 复制引用
a = [1, 2, 3]
b = a
b.append(4)
print(f"赋值引用: a = {a}, b = {b}")  # 都变成 [1,2,3,4]

# 浅拷贝
import copy

nested = [[1, 2], [3, 4]]
shallow = nested.copy()
shallow[0][0] = 99
print(f"\n浅拷贝: nested = {nested}")  # [[99, 2], [3, 4]] — 内层共享!

# 深拷贝
deep = copy.deepcopy(nested)
deep[0][0] = 999
print(f"深拷贝: nested = {nested}")    # [[99, 2], [3, 4]] — 不变
print(f"深拷贝: deep = {deep}")        # [[999, 2], [3, 4]]

print("\n✅ 所有列表操作演示完成！")
