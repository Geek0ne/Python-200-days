#!/usr/bin/env python3
"""
01-tuple-basics.py
Day 007 — 元组基础：创建、操作、拆包与 namedtuple

本文件包含：
1. 元组的各种创建方式
2. 元组的基本操作（索引、切片、拼接）
3. 元组拆包的各种用法
4. namedtuple 使用详解
5. 列表 vs 元组性能对比

可直接运行：python3 01-tuple-basics.py
"""

import sys
import time
from collections import namedtuple


# ============================================================
# 第一部分：元组的创建方式
# ============================================================

print("=" * 60)
print("📦 第一部分：元组的创建方式")
print("=" * 60)

# 方式 1：空元组
empty_tuple = ()
print(f"空元组: {empty_tuple}, 类型: {type(empty_tuple).__name__}")

# 方式 2：单元素元组（⚠️ 逗号必须有！）
single_tuple = (42,)
not_a_tuple = (42)  # 这只是一个整数，不是元组！
print(f"单元素元组: {single_tuple}, 类型: {type(single_tuple).__name__}")
print(f"不加逗号: {not_a_tuple}, 类型: {type(not_a_tuple).__name__} （⚠️ 不是元组！）")

# 方式 3：多元素元组
simple = (1, 2, 3)
print(f"多元素元组: {simple}")

# 方式 4：省略括号（元组字面量）
no_parens = 10, 20, 30
print(f"省略括号: {no_parens}, 类型: {type(no_parens).__name__}")

# 方式 5：从其他序列转换
from_list = tuple([1, 2, 3])
from_str = tuple("Python")
from_range = tuple(range(5))
print(f"从列表转换: {from_list}")
print(f"从字符串转换: {from_str}")
print(f"从 range 转换: {from_range}")

# 方式 6：嵌套元组
nested = (1, (2, 3), (4, (5, 6)))
print(f"嵌套元组: {nested}")

# 方式 7：生成器表达式转元组
from_gen = tuple(x ** 2 for x in range(5))
print(f"从生成器转换: {from_gen}")


# ============================================================
# 第二部分：元组的基本操作
# ============================================================

print("\n" + "=" * 60)
print("🔧 第二部分：元组的基本操作")
print("=" * 60)

t = (10, 20, 30, 40, 50, 20, 60)

# 索引访问
print(f"元组: {t}")
print(f"t[0] = {t[0]}")          # 10
print(f"t[-1] = {t[-1]}")        # 60
print(f"t[1:4] = {t[1:4]}")      # (20, 30, 40)

# 拼接与重复
print(f"t + (70, 80) = {t + (70, 80)}")
print(f"t * 2 = {t * 2}")

# 成员检查
print(f"20 in t = {20 in t}")
print(f"99 not in t = {99 not in t}")

# 常用方法
print(f"len(t) = {len(t)}")
print(f"t.count(20) = {t.count(20)}")  # 元素出现次数
print(f"t.index(30) = {t.index(30)}")  # 元素首次出现的索引

# 尝试修改元组（会报错！）
try:
    t[0] = 999
except TypeError as e:
    print(f"\n⚠️  尝试修改元组元素: {e}")

# 尝试追加元素
try:
    t.append(70)
except AttributeError as e:
    print(f"⚠️  尝试追加元素: {e}")

# 但元组包含的可变对象可以修改
nested_list_tuple = ([1, 2], "hello")
print(f"\n包含列表的元组: {nested_list_tuple}")
nested_list_tuple[0].append(3)  # 修改列表本身
print(f"修改列表后: {nested_list_tuple}")
# ⚠️ 这不是修改元组结构，而是修改元组中引用的可变对象


# ============================================================
# 第三部分：元组拆包
# ============================================================

print("\n" + "=" * 60)
print("🎯 第三部分：元组拆包")
print("=" * 60)

# 基础拆包
print("\n--- 基础拆包 ---")
coords = (3, 7)
x, y = coords
print(f"coords = {coords}")
print(f"拆包: x = {x}, y = {y}")

# 一行交换变量（Python 经典写法）
print("\n--- 变量交换 ---")
a, b = 10, 20
print(f"交换前: a = {a}, b = {b}")
a, b = b, a  # 先构造元组 (20, 10)，再拆包赋值
print(f"交换后: a = {a}, b = {b}")
print(f"  原理: 右侧 (b, a) 先创建临时元组，再拆包赋值给左侧")

# 星号拆包（Python 3+）
print("\n--- 星号拆包 ---")
first, *middle, last = (1, 2, 3, 4, 5)
print(f"元组: (1, 2, 3, 4, 5)")
print(f"first = {first}, middle = {middle}, last = {last}")
print(f"注意: middle 是列表，不是元组！")

# 只取前面部分
a, b, *_ = (10, 20, 30, 40, 50)
print(f"\n只取前两个: a = {a}, b = {b}")
print(f"(忽略剩余元素，使用 _ 表示不关心)")

# 嵌套拆包
data = ("Alice", (1990, 5, 15))
name, (year, month, day) = data
print(f"\n嵌套拆包: name = {name}, year = {year}, month = {month}, day = {day}")

# 函数多返回值本质
print("\n--- 函数多返回值 ---")


def divide_with_remainder(a, b):
    """除法，返回 (商, 余数) — 实际上返回的是元组"""
    quotient = a // b
    remainder = a % b
    return quotient, remainder  # 这是元组字面量


result = divide_with_remainder(17, 5)
print(f"divide_with_remainder(17, 5) 的返回值: {result}")
print(f"返回值类型: {type(result).__name__}")  # tuple

q, r = divide_with_remainder(17, 5)
print(f"拆包: q = {q}, r = {r}")


# ============================================================
# 第四部分：namedtuple 进阶
# ============================================================

print("\n" + "=" * 60)
print("📛 第四部分：namedtuple 进阶")
print("=" * 60)

# 定义多种 namedtuple
# 方式 A：字段列表
Student = namedtuple('Student', ['name', 'age', 'grade'])

# 方式 B：空格分隔（推荐）
Color = namedtuple('Color', 'red green blue alpha')

# 使用默认值
City = namedtuple('City', 'name population country', defaults=['Unknown'])

# 创建实例
s1 = Student('Alice', 16, 'A')
s2 = Student(name='Bob', age=17, grade='B')

white = Color(255, 255, 255, 255)
semi_transparent = Color(0, 0, 0, 128)

# namedtuple 的三种访问方式
print(f"\n学生: {s1}")
print(f"  s1.name = {s1.name}")      # 方式 1：属性
print(f"  s1[0] = {s1[0]}")          # 方式 2：索引
name, age, grade = s1                 # 方式 3：拆包
print(f"  拆包: name={name}, age={age}, grade={grade}")

# namedtuple 的不可变性
try:
    s1.age = 30
except AttributeError as e:
    print(f"\n⚠️  namedtuple 也是不可变的: {e}")

# ._replace() — 创建修改后的副本
s1_updated = s1._replace(grade='A+')
print(f"\n_replace 创建副本:")
print(f"  原对象: {s1}")
print(f"  新对象: {s1_updated}")
print(f"  (原对象不受影响)")

# ._asdict() — 转为有序字典
print(f"\n_asdict 转为字典: {s1._asdict()}")

# ._make() — 从可迭代对象创建
data = ['Charlie', 15, 'B+']
s3 = Student._make(data)
print(f"\n_make 从列表创建: {s3}")

# ._fields — 查看字段名
print(f"\nStudent 的字段: {Student._fields}")
print(f"Color 的字段: {Color._fields}")

# 默认值演示
c1 = City('Beijing', 21540000, 'China')
c2 = City('SmallTown', 5000)  # 省略 country，使用默认值
print(f"\n带默认值的 City:")
print(f"  {c1}")
print(f"  {c2}")

# namedtuple 作为字典键（因为可哈希）
print(f"\nnamedtuple 的哈希值: {hash(s1)}")
locations = {
    Color(255, 0, 0, 255): "Red Zone",
    Color(0, 255, 0, 255): "Green Zone",
    Color(0, 0, 255, 255): "Blue Zone",
}
print(f"Color namedtuple 作为字典键: {locations}")


# ============================================================
# 第五部分：列表 vs 元组性能测试
# ============================================================

print("\n" + "=" * 60)
print("⚡ 第五部分：列表 vs 元组性能对比")
print("=" * 60)

N = 5_000_000

# 1. 创建速度
print(f"\n1) 创建速度（{N:,} 次）...")

start = time.perf_counter()
for _ in range(N):
    _ = (1, 2, 3)  # 元组字面量
tuple_create_time = time.perf_counter() - start

start = time.perf_counter()
for _ in range(N):
    _ = [1, 2, 3]  # 列表字面量
list_create_time = time.perf_counter() - start

print(f"   元组创建: {tuple_create_time:.3f}s")
print(f"   列表创建: {list_create_time:.3f}s")
print(f"   元组快了 {list_create_time / tuple_create_time:.1f}x")

# 2. 内存占用
small_list = list(range(10))
small_tuple = tuple(range(10))
print(f"\n2) 10 个元素的内存占用:")
print(f"   列表: {sys.getsizeof(small_list)} bytes")
print(f"   元组: {sys.getsizeof(small_tuple)} bytes")

# 3. 索引访问
print(f"\n3) 索引访问速度...")
t_index = tuple(range(1000))
l_index = list(range(1000))

start = time.perf_counter()
for _ in range(N):
    _ = t_index[500]
tuple_index_time = time.perf_counter() - start

start = time.perf_counter()
for _ in range(N):
    _ = l_index[500]
list_index_time = time.perf_counter() - start

print(f"   元组索引: {tuple_index_time:.3f}s")
print(f"   列表索引: {list_index_time:.3f}s")
print(f"   (索引效率几乎一致)")

# 4. 迭代速度
print(f"\n4) 迭代速度...")
start = time.perf_counter()
for _ in t_index:
    pass
tuple_iter = time.perf_counter() - start

start = time.perf_counter()
for _ in l_index:
    pass
list_iter = time.perf_counter() - start

print(f"   元组迭代: {tuple_iter:.6f}s")
print(f"   列表迭代: {list_iter:.6f}s")

print(f"\n{'='*60}")
print(f"📊 总结：元组更小、更快创建、可哈希做字典键")
print(f"     列表更灵活、可增删、适用动态数据")
print(f"{'='*60}")
