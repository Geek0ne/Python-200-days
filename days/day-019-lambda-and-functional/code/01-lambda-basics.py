#!/usr/bin/env python3
"""
01-lambda-basics.py — Lambda 基础用法

涵盖：
  - Lambda 语法基础
  - sorted() 自定义排序
  - map() 映射
  - filter() 过滤
  - reduce() 归约
  - 常见陷阱与避坑
"""

from functools import reduce

# ============================================================
# 1. Lambda 语法基础
# ============================================================
print("=" * 60)
print("1. Lambda 语法基础")
print("=" * 60)

# 基本写法
add = lambda a, b: a + b
print(f"lambda a, b: a + b  → add(3, 5) = {add(3, 5)}")

# 无参数
always_true = lambda: True
print(f"lambda: True         → always_true() = {always_true()}")

# 默认参数
power = lambda base, exp=2: base ** exp
print(f"power(3)             = {power(3)}")
print(f"power(2, 10)         = {power(2, 10)}")

# 可变参数
sum_all = lambda *args: sum(args)
print(f"sum_all(1,2,3,4,5)   = {sum_all(1, 2, 3, 4, 5)}")

# 关键字参数
format_person = lambda name, age, **kw: f"{name}({age}): {kw}"
print(f"format_person('Alice', 25, city='NY') = {format_person('Alice', 25, city='NY')}")

print()

# ============================================================
# 2. sorted() 自定义排序
# ============================================================
print("=" * 60)
print("2. sorted() 自定义排序")
print("=" * 60)

students = [
    {"name": "Alice", "score": 88, "age": 20},
    {"name": "Bob", "score": 95, "age": 19},
    {"name": "Charlie", "score": 72, "age": 22},
    {"name": "Diana", "score": 95, "age": 18},
]

by_score = sorted(students, key=lambda s: s["score"])
print("按分数升序：")
for s in by_score:
    print(f"  {s['name']:8} {s['score']}分")

by_score_desc = sorted(students, key=lambda s: s["score"], reverse=True)
print("\n按分数降序：")
for s in by_score_desc:
    print(f"  {s['name']:8} {s['score']}分")

multi_key = sorted(students, key=lambda s: (-s["score"], s["age"]))
print("\n按分数降序，年龄升序：")
for s in multi_key:
    print(f"  {s['name']:8} {s['score']}分  {s['age']}岁")

words = ["apple", "kiwi", "banana", "cherry", "date"]
by_len = sorted(words, key=lambda w: len(w))
print(f"\n按长度排序: {by_len}")

by_last = sorted(words, key=lambda w: w[-1])
print(f"按尾字母排序: {by_last}")

print()

# ============================================================
# 3. map() — 映射变换
# ============================================================
print("=" * 60)
print("3. map() — 映射变换")
print("=" * 60)

nums = [1, 2, 3, 4, 5, 6]

squared = list(map(lambda x: x ** 2, nums))
print(f"平方:       {squared}")

str_nums = list(map(lambda x: f"数字-{x}", nums))
print(f"转字符串:   {str_nums}")

list1 = [1, 2, 3]
list2 = [10, 20, 30]
list3 = [100, 200, 300]
combined = list(map(lambda a, b, c: a + b + c, list1, list2, list3))
print(f"三列表和:   {combined}")

m = map(lambda x: x * 10, nums)
print(f"map对象类型: {type(m).__name__}")
print(f"转为列表:   {list(m)}")

products = [
    ("iPhone", 7999),
    ("iPad", 3499),
    ("MacBook", 9999),
]
formatted = list(map(lambda p: f"{p[0]:10} ¥{p[1]:,}", products))
for line in formatted:
    print(f"  产品: {line}")

print()

# ============================================================
# 4. filter() — 条件过滤
# ============================================================
print("=" * 60)
print("4. filter() — 条件过滤")
print("=" * 60)

nums = list(range(-5, 11))

positives = list(filter(lambda x: x > 0, nums))
print(f"正数:     {positives}")

evens = list(filter(lambda x: x % 2 == 0, nums))
print(f"偶数:     {evens}")

data = [0, 1, "", "hello", None, [], [1, 2], False, True]
truthy = list(filter(None, data))
print(f"真值过滤: {truthy}")

special = list(filter(lambda x: x > 0 and x % 3 == 0, nums))
print(f"正且被3整除: {special}")

f = filter(lambda x: x > 0, nums)
print(f"filter对象: {type(f).__name__}")

print()

# ============================================================
# 5. reduce() — 归约聚合
# ============================================================
print("=" * 60)
print("5. reduce() — 归约聚合")
print("=" * 60)

numbers = [1, 2, 3, 4, 5]
total = reduce(lambda a, b: a + b, numbers)
print(f"求和:        {total}")

fact = reduce(lambda a, b: a * b, range(1, 6))
print(f"5! =         {fact}")

max_val = reduce(lambda a, b: a if a > b else b, numbers)
print(f"最大值:      {max_val}")

words = ["Python", "是", "一门", "优雅", "的", "语言"]
sentence = reduce(lambda a, b: a + b, words)
print(f"拼接:        {sentence}")

from_zero = reduce(lambda a, b: a + b, numbers, 10)
print(f"求和(初始10): {from_zero}")

nested = [[1, 2], [3, 4, 5], [6], [7, 8]]
flattened = reduce(lambda a, b: a + b, nested)
print(f"列表扁平化:  {flattened}")

print()

# ============================================================
# 6. 常见陷阱与避坑
# ============================================================
print("=" * 60)
print("6. 常见陷阱与避坑")
print("=" * 60)

# 陷阱 1：Late Binding（延迟绑定）
print("\n--- 陷阱 1: Late Binding ---")
bad_funcs = [lambda: i for i in range(3)]
print("延迟绑定导致：", [f() for f in bad_funcs])  # [2, 2, 2]

good_funcs = [lambda i=i: i for i in range(3)]
print("修复后：      ", [f() for f in good_funcs])  # [0, 1, 2]

# 陷阱 2：Lambda 中不能使用赋值语句
print("\n--- 陷阱 2: 不能使用赋值 ---")
inc = lambda x: x + 1
print(f"inc(5) = {inc(5)}")

# 陷阱 3：Lambda 可读性陷阱
print("\n--- 陷阱 3: 过度使用 Lambda ---")
hard = lambda x: (lambda y: (lambda z: x + y + z)(3))(2)(1)
def easy(x, y, z):
    return x + y + z
print(f"可读版本: easy(1, 2, 3) = {easy(1, 2, 3)}")

# 陷阱 4：map/filter 惰性求值
print("\n--- 陷阱 4: 惰性求值 ---")
m = map(lambda x: x ** 2, [1, 2, 3])
print(f"第一次消费: {list(m)}")
print(f"第二次消费: {list(m)}")

# 陷阱 5：reduce 空序列
print("\n--- 陷阱 5: reduce 空序列 ---")
try:
    reduce(lambda a, b: a + b, [])
except TypeError as e:
    print(f"空序列出错: {e}")
print(f"带初始值:   {reduce(lambda a, b: a + b, [], 0)}")
