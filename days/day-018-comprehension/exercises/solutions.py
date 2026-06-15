#!/usr/bin/env python3
"""
Day 018 — 列表推导式练习题解答

这是 Day 018 练习题的参考答案。
尝试自己先做，再对照答案学习。
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title):
    console.section(title)


section("练习题解答")

print("--- 1. 平方数列表 ---")
squares_1_20 = [x ** 2 for x in range(1, 21)]
print(f"1-20的平方: {squares_1_20}")

print("\n--- 2. 偶数过滤并乘3 ---")
numbers = [1, 5, 8, 12, 15, 20, 23, 30]
result = [x * 3 for x in numbers if x % 2 == 0]
print(f"原始: {numbers}")
print(f"偶数×3: {result}")

print("\n--- 3. 字典推导式：单词→长度 ---")
words = ['apple', 'banana', 'cherry', 'date']
word_len = {w: len(w) for w in words}
print(f"单词→长度: {word_len}")

print("\n--- 4. 集合推导式：去重字母 ---")
text = "hello world python programming"
unique_letters = {c.lower() for c in text if c.isalpha()}
print(f"唯一字母 ({len(unique_letters)} 个): {sorted(unique_letters)}")

print("\n--- 5. 嵌套扁平化 ---")
nested = [[1, 2], [3, 4, 5], [6], [7, 8, 9, 10]]
flat = [item for sublist in nested for item in sublist]
print(f"原始: {nested}")
print(f"扁平: {flat}")

print("\n--- 6. 字典过滤：及格学生 ---")
scores = {'Alice': 85, 'Bob': 42, 'Charlie': 73, 'Diana': 91, 'Eve': 58}
passed = [name for name, score in scores.items() if score >= 60]
print(f"及格学生: {passed}")

print("\n--- 7. 笛卡尔积 + 条件 ---")
pairs = [(a, b) for a in {1, 2, 3} for b in {4, 5} if (a + b) % 2 == 1]
print(f"和是奇数的有序对: {pairs}")

print("\n--- 8. 矩阵旋转 90° ---")
matrix = [[1, 2, 3], [4, 5, 6]]
rotated = [[matrix[len(matrix) - 1 - j][i] for j in range(len(matrix))]
           for i in range(len(matrix[0]))]
print(f"原始:\n{matrix[0]}\n{matrix[1]}")
print(f"顺时针90°:\n{rotated[0]}\n{rotated[1]}\n{rotated[2]}")

print("\n--- 9. 生成器表达式求和 ---")
total = sum(x ** 3 for x in range(1, 1_000_001) if x % 2 == 1)
print(f"1-1,000,000奇数立方和: {total}")

print("\n--- 10. 素数判断（2-100） ---")
primes = [x for x in range(2, 101) if all(x % i != 0 for i in range(2, int(x**0.5) + 1))]
print(f"2-100的素数 ({len(primes)} 个): {primes}")

print("\n--- 11. 单词统计 ---")
text = "Hello world! Hello Python. Python is great, Python is fun."
import re
words = re.findall(r'\w+', text.lower())
word_count = {w: words.count(w) for w in set(words)}
print(f"单词统计: {word_count}")

print("\n--- 12. 性能优化 ---")
import timeit
import random
random.seed(42)
data = [random.randint(0, 1000) for _ in range(10000)]

t_comp = timeit.timeit(lambda: [x ** 2 for x in data], number=1000)
t_map = timeit.timeit(lambda: list(map(lambda x: x**2, data)), number=1000)
print(f"推导式: {t_comp:.4f}s")
print(f"map:     {t_map:.4f}s")
print(f"比例:   {t_comp/t_map:.2f}x ({'推导式快' if t_comp < t_map else 'map快'})")

print("\n✅ 所有练习题解答完成")
