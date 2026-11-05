#!/usr/bin/env python3
"""
01-dict-basics.py
Day 008 — 字典基础：创建、操作、推导式与进阶工具

本文件包含：
1. 字典的各种创建方式
2. 字典核心操作与方法
3. 字典视图与集合运算
4. 字典推导式高级用法
5. defaultdict / Counter 实例
6. 自定义可哈希对象

可直接运行：python3 01-dict-basics.py
"""

import sys
import time
from collections import defaultdict, Counter


# ============================================================
# 第一部分：字典创建方式大全
# ============================================================

print("=" * 60)
print("📦 第一部分：字典创建方式大全")
print("=" * 60)


def demonstrate_creation():
    """7 种创建字典的方法"""
    print("\n1️⃣  空字典")
    d1 = {}
    d2 = dict()
    print(f"   d1 = {d1}, type = {type(d1).__name__}")
    print(f"   d2 = {d2}, type = {type(d2).__name__}")

    print("\n2️⃣  字面量创建")
    d = {"name": "Alice", "age": 25, "city": "Beijing"}
    print(f"   {d}")

    print("\n3️⃣  dict() 构造函数（关键字参数）")
    d = dict(name="Alice", age=25, city="Beijing")
    print(f"   {d}")

    print("\n4️⃣  从可迭代对象创建（键值对列表/元组）")
    pairs = [("a", 1), ("b", 2), ("c", 3)]
    d = dict(pairs)
    print(f"   dict([('a',1), ('b',2), ('c',3)]) = {d}")

    print("\n5️⃣  zip() 组合两个序列")
    keys = ["name", "age", "city"]
    values = ["Alice", 25, "Beijing"]
    d = dict(zip(keys, values))
    print(f"   dict(zip({keys}, {values})) = {d}")

    print("\n6️⃣  fromkeys() 统一赋初值")
    d = dict.fromkeys(["a", "b", "c"], 0)
    print(f"   dict.fromkeys(['a','b','c'], 0) = {d}")

    print("\n7️⃣  字典推导式创建")
    squares = {x: x ** 2 for x in range(6)}
    print(f"   {{x: x**2 for x in range(6)}} = {squares}")


demonstrate_creation()


# ============================================================
# 第二部分：字典核心操作
# ============================================================

print("\n" + "=" * 60)
print("🔧 第二部分：字典核心操作")
print("=" * 60)


def demonstrate_operations():
    print("\n=== 基础 CRUD ===")
    d = {"name": "Alice", "age": 25, "city": "Beijing"}

    # 读取
    print(f"   d['name'] = {d['name']}")
    print(f"   d.get('age') = {d.get('age')}")
    print(f"   d.get('country', '未知') = {d.get('country', '未知')}")

    # 写入/更新
    d["age"] = 26
    d["country"] = "China"  # 新增键
    print(f"   更新后: {d}")

    # 删除
    removed = d.pop("country")
    print(f"   pop('country') = {removed}, 剩余: {d}")

    removed_item = d.popitem()
    print(f"   popitem() = {removed_item}, 剩余: {d}")

    # 恢复
    d["city"] = "Beijing"

    print("\n=== setdefault 的妙用 ===")
    inventory = {}

    # setdefault: 键不存在时设置默认值并返回，存在时返回已有值
    result1 = inventory.setdefault("apple", 0)
    print(f"   首次 setdefault('apple', 0) = {result1}")

    inventory["apple"] += 1
    inventory["apple"] += 1

    result2 = inventory.setdefault("apple", 0)
    print(f"   再次 setdefault('apple', 0) = {result2} (已有值, 不改动)")
    print(f"   apple 计数: {inventory['apple']}")

    # 用 setdefault 初始化列表
    inventory.setdefault("fruits", []).append("apple")
    inventory.setdefault("fruits", []).append("banana")
    print(f"   setdefault 初始化列表: {inventory}")

    print("\n=== 字典合并 (Python 3.9+) ===")
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 3, "c": 4}

    # update 方法（原地修改）
    d1_copy = d1.copy()
    d1_copy.update(d2)
    print(f"   update: d1 = {d1}, d2 = {d2}")
    print(f"   d1.copy().update(d2) → {d1_copy}")

    # | 操作符（返回新字典）
    merged = d1 | d2
    print(f"   | 操作符: d1 | d2 = {merged}")

    # |= 操作符（原地合并）
    d1_copy2 = d1.copy()
    d1_copy2 |= d2
    print(f"   |= 操作符: d1.copy() |= d2 → {d1_copy2}")

    print("\n=== 字典的 in / not in ===")
    d = {"a": 1, "b": 2}
    print(f"   'a' in d: {'a' in d}")
    print(f"   'z' in d: {'z' in d}")
    print(f"   1 in d:   {1 in d}   ← 注意：in 检查的是键，不是值！")


demonstrate_operations()


# ============================================================
# 第三部分：字典视图与遍历
# ============================================================

print("\n" + "=" * 60)
print("👁️  第三部分：字典视图与遍历")
print("=" * 60)


def demonstrate_views():
    d = {"name": "Alice", "age": 25, "city": "Beijing", "job": "Engineer"}

    print("\n=== 三种视图 ===")
    keys = d.keys()
    values = d.values()
    items = d.items()

    print(f"   keys()  : {keys}    ← {type(keys).__name__}")
    print(f"   values(): {values}  ← {type(values).__name__}")
    print(f"   items() : {items}   ← {type(items).__name__}")

    print("\n=== 视图的动态性 ===")
    print(f"   添加前 keys: {list(keys)}")
    d["country"] = "China"
    print(f"   添加后 keys: {list(keys)}  ← 自动更新！")

    print("\n=== 四种遍历方式 ===")
    print("\n   方式 1：直接遍历字典（遍历键）")
    for key in d:
        print(f"     {key}: {d[key]}")

    print("\n   方式 2：遍历 items()（推荐）")
    for key, value in d.items():
        print(f"     {key}: {value}")

    print("\n   方式 3：带枚举遍历")
    for idx, (key, value) in enumerate(d.items(), 1):
        print(f"     {idx}. {key} → {value}")

    print("\n   方式 4：遍历值")
    for value in d.values():
        print(f"     value: {value}")

    print("\n=== 视图的集合运算 ===")
    d1 = {"a": 1, "b": 2, "c": 3}
    d2 = {"b": 2, "c": 4, "d": 5}

    print(f"   d1.keys() = {set(d1.keys())}")
    print(f"   d2.keys() = {set(d2.keys())}")
    print(f"   交集 &: {d1.keys() & d2.keys()}")
    print(f"   差集 -: {d1.keys() - d2.keys()}")
    print(f"   并集 |: {d1.keys() | d2.keys()}")
    print(f"   对称差 ^: {d1.keys() ^ d2.keys()}")


demonstrate_views()


# ============================================================
# 第四部分：字典推导式
# ============================================================

print("\n" + "=" * 60)
print("🌀 第四部分：字典推导式")
print("=" * 60)


def demonstrate_dict_comprehension():
    print("\n=== 基础推导 ===")

    # 平方映射
    squares = {x: x ** 2 for x in range(10)}
    print(f"   平方映射: {squares}")

    # 条件过滤
    even_squares = {x: x ** 2 for x in range(10) if x % 2 == 0}
    print(f"   偶数平方: {even_squares}")

    print("\n=== 实用场景 ===")

    # 键值互换
    original = {"a": 1, "b": 2, "c": 3}
    swapped = {v: k for k, v in original.items()}
    print(f"   键值互换: {swapped}")
    # 注意：如果值不唯一，后面的会覆盖前面的！

    # 字符串长度映射
    words = ["hello", "world", "python", "dictionary"]
    len_map = {word: len(word) for word in words}
    print(f"   单词长度: {len_map}")

    # 词性分类（条件嵌套）
    nums = [1, 2, 3, 4, 5, 6, 7, 8]
    classified = {
        x: "even" if x % 2 == 0 else "odd"
        for x in nums
    }
    print(f"   奇偶分类: {classified}")

    print("\n=== 进阶技巧 ===")

    # 从 zip 构建
    names = ["Alice", "Bob", "Charlie"]
    scores = [85, 92, 78]
    gradebook = {
        name: score
        for name, score in zip(names, scores)
    }
    print(f"   成绩簿: {gradebook}")

    # 枚举索引
    fruits = ["apple", "banana", "cherry"]
    indexed = {i: fruit for i, fruit in enumerate(fruits)}
    print(f"   索引映射: {indexed}")

    # 矩阵转置
    matrix = [[1, 2, 3], [4, 5, 6]]
    transposed = {
        col: [matrix[row][col] for row in range(len(matrix))]
        for col in range(len(matrix[0]))
    }
    print(f"   矩阵: {matrix}")
    print(f"   转置: {transposed}")

    # 双重条件
    filtered = {
        x: x ** 3
        for x in range(20)
        if x % 2 == 0
        if x % 4 != 0  # 多个 if = and 关系
    }
    print(f"   双重过滤立方: {filtered}")


demonstrate_dict_comprehension()


# ============================================================
# 第五部分：defaultdict 实战
# ============================================================

print("\n" + "=" * 60)
print("🛡️  第五部分：defaultdict 的四种模式")
print("=" * 60)


def demonstrate_defaultdict():
    print("\n=== 模式 1：defaultdict(int) — 计数器 ===")
    words = ["apple", "banana", "apple", "orange", "banana", "apple"]

    # 普通 dict 实现
    counter_plain = {}
    for w in words:
        if w not in counter_plain:
            counter_plain[w] = 0
        counter_plain[w] += 1

    # defaultdict 实现 — 更简洁！
    counter_dd = defaultdict(int)
    for w in words:
        counter_dd[w] += 1

    print(f"   普通 dict: {counter_plain}")
    print(f"   defaultdict: {dict(counter_dd)}")
    print(f"   代码行数: 普通 dict 需 4 行, defaultdict 只需 2 行 ✓")

    print("\n=== 模式 2：defaultdict(list) — 分组 ===")
    data = [
        ("水果", "苹果"), ("水果", "香蕉"),
        ("蔬菜", "白菜"), ("水果", "橘子"),
        ("蔬菜", "萝卜"),
    ]

    grouped = defaultdict(list)
    for category, item in data:
        grouped[category].append(item)

    print(f"   分组结果: {dict(grouped)}")

    print("\n=== 模式 3：defaultdict(set) — 去重分组 ===")
    data_dup = [
        ("tag", "python"), ("tag", "java"),
        ("tag", "python"), ("tag", "go"),
    ]
    unique_tags = defaultdict(set)
    for cat, tag in data_dup:
        unique_tags[cat].add(tag)

    print(f"   去重分组: {dict(unique_tags)}")

    print("\n=== 模式 4：嵌套 defaultdict ===")
    # 深层嵌套：defaultdict(lambda: defaultdict(int))
    # 适用场景：二级计数，例如 年份→月份→销售额
    nested = defaultdict(lambda: defaultdict(int))

    sales_data = [
        (2023, 1, 100), (2023, 2, 150),
        (2024, 1, 200), (2023, 1, 50),
    ]
    for year, month, amount in sales_data:
        nested[year][month] += amount

    for year, months in sorted(nested.items()):
        for month, total in sorted(months.items()):
            print(f"   {year}年{month}月: {total}")

    print("\n=== defaultdict 与普通 dict 性能对比 ===")
    from timeit import timeit

    setup_plain = """
data = list(range(10000))
result = {}
"""
    code_plain = """
for x in data:
    if x % 2 not in result:
        result[x % 2] = []
    result[x % 2].append(x)
"""

    setup_dd = """
from collections import defaultdict
data = list(range(10000))
result = defaultdict(list)
"""
    code_dd = """
for x in data:
    result[x % 2].append(x)
"""

    t1 = timeit(code_plain, setup_plain, number=1000)
    t2 = timeit(code_dd, setup_dd, number=1000)
    print(f"\n   普通 dict 分组: {t1:.4f}s")
    print(f"   defaultdict 分组: {t2:.4f}s")
    print(f"   提速: {t1 / t2:.2f}x")


demonstrate_defaultdict()


# ============================================================
# 第六部分：Counter 详解
# ============================================================

print("\n" + "=" * 60)
print("🔢 第六部分：Counter 计数利器")
print("=" * 60)


def demonstrate_counter():
    from collections import Counter

    print("\n=== 创建 Counter ===")
    # 从字符串
    c1 = Counter("abracadabra")
    print(f"   字符串计数: {c1}")

    # 从列表
    c2 = Counter(["red", "blue", "red", "green", "blue", "red"])
    print(f"   列表计数: {c2}")

    # 从字典
    c3 = Counter({"a": 3, "b": 1, "c": 2})
    print(f"   字典转换: {c3}")

    print("\n=== 核心方法 ===")
    c = Counter("abracadabra")
    print(f"   完整统计: {c}")

    # most_common
    print(f"   most_common(3): {c.most_common(3)}")
    print(f"   most_common() 全部: {c.most_common()}")

    # 不存在的键返回 0
    print(f"   c['z'] = {c['z']}")  # 0, not KeyError!

    # elements()
    print(f"   elements() → {sorted(c.elements())}")

    # total() — Python 3.10+
    if hasattr(c, "total"):
        print(f"   总数 total(): {c.total()}")

    print("\n=== Counter 算术运算 ===")
    c1 = Counter(a=3, b=1, c=0)
    c2 = Counter(a=1, b=2, d=1)

    print(f"   c1: {c1}")
    print(f"   c2: {c2}")
    print(f"   加法 +: {c1 + c2}")  # 合并计数
    print(f"   减法 -: {c1 - c2}")  # 只保留正数
    print(f"   交集 &: {c1 & c2}")  # 取最小
    print(f"   并集 |: {c1 | c2}")  # 取最大

    print("\n=== 实际应用：文本分析 ===")
    text = """
    Python is powerful and fast
    Python is easy to learn
    Python is open and free
    Fast and easy Python
    """

    words = text.lower().split()
    word_count = Counter(words)
    top3 = word_count.most_common(3)
    print(f"   文本: {text.strip()}")
    print(f"   词频 Top 3: {top3}")


demonstrate_counter()


# ============================================================
# 第七部分：自定义可哈希对象
# ============================================================

print("\n" + "=" * 60)
print("🔑 第七部分：自定义可哈希对象")
print("=" * 60)


def demonstrate_hashable():
    print("\n=== 什么是可哈希？ ===")

    # 可哈希类型
    hashable_items = [42, 3.14, "hello", (1, 2, 3), frozenset([1, 2])]
    for item in hashable_items:
        print(f"   hash({item!r:20}) = {hash(item)}")

    # 不可哈希类型
    unhashable = [[1, 2, 3], {"set", "of", "items"}, {"a": 1}]
    for item in unhashable:
        try:
            hash(item)
            print(f"   {item!r} → 可哈希（意外）")
        except TypeError as e:
            print(f"   {type(item).__name__:6} {str(item)!r:15} → ❌ {e}")

    print("\n=== 自定义可哈希类 ===")

    class Person:
        """自定义可哈希类：实现 __hash__ 和 __eq__"""

        def __init__(self, name: str, age: int):
            self.name = name
            self.age = age

        def __hash__(self):
            # 用元组组合所有标识性字段
            return hash((self.name, self.age))

        def __eq__(self, other):
            if not isinstance(other, Person):
                return False
            return self.name == other.name and self.age == other.age

        def __repr__(self):
            return f"Person({self.name}, {self.age})"

    # 现在 Person 可以做字典键了！
    registry = {
        Person("Alice", 25): "工程师",
        Person("Bob", 30): "设计师",
        Person("Charlie", 28): "产品经理",
    }

    print("   人员注册表:")
    for person, role in registry.items():
        print(f"     {person} → {role}")

    # 查找（使用相同的属性值）
    alice = Person("Alice", 25)
    print(f"\n   registry[Person('Alice', 25)] = {registry[alice]}")

    # 验证哈希一致性
    print(f"   hash(Person('Alice', 25)) = {hash(alice)}")

    print("\n=== __hash__ 设置为 None — 强制不可哈希 ===")

    class UnhashablePerson(Person):
        __hash__ = None  # 继承 __eq__ 但显式禁止哈希！

    up = UnhashablePerson("Test", 20)
    try:
        d = {up: "value"}
    except TypeError as e:
        print(f"   ❌ UnhashablePerson 不能做键: {e}")


demonstrate_hashable()


# ============================================================
# 性能对比：列表 vs 字典查找
# ============================================================

print("\n" + "=" * 60)
print("⚡ 额外：列表 vs 字典查找性能对比")
print("=" * 60)


def performance_compare():
    import random

    SIZE = 100_000
    LOOKUPS = 10_000

    # 准备数据
    keys = list(range(SIZE))
    values = [f"value_{k}" for k in keys]

    # 列表方式：并行列表
    list_data = list(zip(keys, values))  # [(key, value), ...]

    # 字典方式
    dict_data = dict(zip(keys, values))

    # 随机选取要查找的键
    search_keys = random.choices(keys, k=LOOKUPS)

    # 列表查找
    start = time.perf_counter()
    found_list = 0
    for sk in search_keys:
        for k, v in list_data:
            if k == sk:
                found_list += 1
                break
    list_time = time.perf_counter() - start

    # 字典查找
    start = time.perf_counter()
    found_dict = 0
    for sk in search_keys:
        if sk in dict_data:
            found_dict += 1
    dict_time = time.perf_counter() - start

    print(f"\n   数据规模: {SIZE:,} 条")
    print(f"   查找次数: {LOOKUPS:,} 次")
    print(f"   列表查找: {list_time:.4f}s  (O(n))")
    print(f"   字典查找: {dict_time:.4f}s  (O(1))")
    print(f"   字典比列表快: {list_time / dict_time:.0f}x!")


performance_compare()

print("\n" + "=" * 60)
print("✅ Day 008 字典基础演示完成！")
print("=" * 60)
