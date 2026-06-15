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
