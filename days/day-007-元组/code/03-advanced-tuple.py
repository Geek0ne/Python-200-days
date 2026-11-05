#!/usr/bin/env python3
"""
03-advanced-tuple.py — Day 007 补充
元组高级用法：命名元组模式、序列化、数据记录、性能对比

可直接运行：python3 03-advanced-tuple.py
"""

import time
import sys
from collections import namedtuple
from typing import NamedTuple, List, Optional
from datetime import datetime


# ============================================================
# 1. 命名元组设计模式
# ============================================================

def demo_namedtuple_patterns():
    print("=" * 60)
    print("  1️⃣ 命名元组设计模式")
    print("=" * 60)

    # 模式 A：简单的数据容器
    Point = namedtuple("Point", ["x", "y", "z"])

    # 模式 B：带默认值
    # namedtuple 不支持直接默认值，通过 __new__.__defaults__ 实现
    Employee = namedtuple("Employee", ["name", "age", "department", "salary"])
    Employee.__new__.__defaults__ = (None, None, "通用", 0)

    alice = Employee("Alice", 25, "技术部", 15000)
    bob = Employee("Bob", 30)  # 使用默认值
    print(f"\n  Employee 示例:")
    print(f"    Alice: {alice}")
    print(f"    Bob:   {bob}")

    # 模式 C：类语法（typing.NamedTuple）— 支持方法
    class Stock(NamedTuple):
        symbol: str
        price: float
        change: float = 0.0

        def pct_change(self) -> str:
            if self.price - self.change == 0:
                return "0.00%"
            pct = (self.change / (self.price - self.change)) * 100
            return f"{pct:+.2f}%"

        def is_up(self) -> bool:
            return self.change > 0

        def __str__(self):
            arrow = "📈" if self.is_up() else "📉"
            return f"{arrow} {self.symbol}: ${self.price:.2f} ({self.pct_change()})"

    stocks = [
        Stock("AAPL", 175.30, 2.50),
        Stock("GOOGL", 142.80, -1.20),
        Stock("TSLA", 245.60, 5.80),
    ]
    print(f"\n  Stock (NamedTuple + 方法):")
    for s in stocks:
        print(f"    {s}")

    # 模式 D：组合模式
    class Address(NamedTuple):
        city: str
        street: str
        zip_code: str

    class Person(NamedTuple):
        name: str
        address: Address
        phone: Optional[str] = None

        def full_address(self) -> str:
            addr = self.address
            return f"{addr.city}{addr.street} {addr.zip_code}"

    p = Person("Alice", Address("北京", "朝阳区建国路88号", "100022"), "13800138000")
    print(f"\n  组合 Pattern:")
    print(f"    Person: {p}")
    print(f"    地址: {p.full_address()}")


# ============================================================
# 2. 元组作为不可变记录
# ============================================================

def demo_tuple_as_record():
    """元组作为数据记录的实际应用"""
    print("\n" + "=" * 60)
    print("  2️⃣ 元组作为不可变数据记录")
    print("=" * 60)

    # 日志记录（元组不可变：日志发出后不允许修改）
    LogEntry = namedtuple("LogEntry", ["timestamp", "level", "module", "message"])

    logs = [
        LogEntry(datetime.now(), "INFO", "app", "服务启动"),
        LogEntry(datetime.now(), "WARNING", "db", "连接池使用率 80%"),
        LogEntry(datetime.now(), "ERROR", "api", "请求超时: /users"),
    ]

    print(f"\n  日志记录（不可变 → 审计安全）:")
    for log in logs:
        print(f"    [{log.level:<7}] {log.timestamp:%H:%M:%S} [{log.module}] {log.message}")

    # 数据库查询结果（SQL 查询返回元组行）
    print(f"\n  数据库行记录:")
    db_rows = [
        (1, "Alice", 25, "Beijing"),
        (2, "Bob", 30, "Shanghai"),
        (3, "Charlie", 28, "Guangzhou"),
    ]

    # 拆包遍历
    for uid, name, age, city in db_rows:
        print(f"    ID={uid}, {name}, {age}岁, {city}")

    # 多返回值作为不可变结果
    def parse_config_line(line: str) -> tuple:
        """解析配置行，返回不可变结果"""
        parts = line.strip().split("=", 1)
        if len(parts) != 2:
            return ("parse_error", line, False)
        key, value = parts
        return (key.strip(), value.strip(), True)

    config_lines = [
        "name=Alice",
        "debug=true",
        "invalid_line",
        "port=8080",
    ]
    print(f"\n  配置解析（返回元组保证不被修改）:")
    for line in config_lines:
        result = parse_config_line(line)
        key, value, ok = result
        status = "✅" if ok else "❌"
        print(f"    {status} {line:<20} → {key}: {value}")


# ============================================================
# 3. 元组性能基准测试
# ============================================================

def demo_tuple_benchmark():
    """list vs tuple 全面性能对比"""
    print("\n" + "=" * 60)
    print("  3️⃣ 元组 vs 列表：性能基准测试")
    print("=" * 60)

    n = 5_000_000
    data_list = list(range(n))
    data_tuple = tuple(range(n))

    # 测试 a：创建
    print(f"\n  A. 创建 {n:,} 个元素:")

    start = time.perf_counter()
    lst = list(range(n))
    list_create = time.perf_counter() - start

    start = time.perf_counter()
    tpl = tuple(range(n))
    tuple_create = time.perf_counter() - start

    print(f"     list 创建:   {list_create:.4f}s")
    print(f"     tuple 创建:  {tuple_create:.4f}s")
    print(f"     差异:        {'元组快' if tuple_create < list_create else '列表快'} "
          f"{abs(list_create - tuple_create) * 1000:.1f}ms")

    # 测试 b：遍历
    print(f"\n  B. 遍历 {n:,} 个元素:")

    start = time.perf_counter()
    total = 0
    for x in data_list:
        total += x
    list_iter = time.perf_counter() - start

    start = time.perf_counter()
    total = 0
    for x in data_tuple:
        total += x
    tuple_iter = time.perf_counter() - start

    print(f"     list 遍历:   {list_iter:.4f}s")
    print(f"     tuple 遍历:  {tuple_iter:.4f}s")

    # 测试 c：索引访问
    print(f"\n  C. 索引访问 {n:,} 次:")

    import random
    indices = [random.randint(0, n - 1) for _ in range(100_000)]

    start = time.perf_counter()
    for idx in indices:
        _ = data_list[idx]
    list_index = time.perf_counter() - start

    start = time.perf_counter()
    for idx in indices:
        _ = data_tuple[idx]
    tuple_index = time.perf_counter() - start

    print(f"     list 索引:   {list_index:.4f}s")
    print(f"     tuple 索引:  {tuple_index:.4f}s")

    # 测试 d：内存占用
    print(f"\n  D. 内存占用 ({n:,} 元素):")
    list_mem = sys.getsizeof(data_list)
    tuple_mem = sys.getsizeof(data_tuple)
    print(f"     list:        {list_mem:,} bytes")
    print(f"     tuple:       {tuple_mem:,} bytes")
    print(f"     节省:        {list_mem - tuple_mem:,} bytes ({(list_mem - tuple_mem) / list_mem * 100:.1f}%)")

    # 测试 e：哈希
    print(f"\n  E. 哈希计算:")
    small_tuple = tuple(range(1000))
    small_list = list(range(1000))

    start = time.perf_counter()
    _ = hash(small_tuple)
    tuple_hash = time.perf_counter() - start

    try:
        _ = hash(small_list)
    except TypeError:
        print(f"     tuple 哈希:  {tuple_hash * 1e6:.2f}µs")
        print(f"     list 哈希:   ❌ 不可哈希（不能做字典键）")

    print(f"\n  📊 综合结论:")
    print(f"     创建:  元组 ~{list_create / tuple_create:.1f}x 快")
    print(f"     遍历:  几乎无差别")
    print(f"     索引:  几乎无差别")
    print(f"     内存:  tuple 节省 ~{(list_mem - tuple_mem) / list_mem * 100:.0f}%")
    print(f"     哈希:  tuple 可哈希 ✓ | list ❌")


# ============================================================
# 4. 元组在函数式编程中的应用
# ============================================================

def demo_tuple_functional():
    """元组在函数式场景的应用：拆包、zip、map、reduce"""
    print("\n" + "=" * 60)
    print("  4️⃣ 元组在函数式编程中的应用")
    print("=" * 60)

    # zip 打包元组
    names = ["Alice", "Bob", "Charlie"]
    ages = [25, 30, 28]
    cities = ["Beijing", "Shanghai", "Guangzhou"]

    zipped = list(zip(names, ages, cities))
    print(f"\n  zip 打包: {zipped}")

    # map + 拆包
    def format_person(name, age, city):
        return f"{name} ({age}岁, {city})"

    formatted = list(map(lambda p: format_person(*p), zipped))
    print(f"  map + 拆包: {formatted}")

    # enumerate 返回 (index, value)
    fruits = ["apple", "banana", "cherry"]
    enumerated = list(enumerate(fruits, 1))
    print(f"\n  enumerate: {enumerated}")
    for i, fruit in enumerated:
        print(f"    {i}. {fruit}")

    # sorted with key（元组作为排序键）
    students = [
        ("Charlie", 85, "A班"),
        ("Alice", 92, "B班"),
        ("Bob", 78, "A班"),
    ]

    # 按分数排序
    sorted_by_score = sorted(students, key=lambda x: x[1], reverse=True)
    print(f"\n  按分数排序:")
    for name, score, cls in sorted_by_score:
        print(f"    {name}: {score}分 ({cls})")

    # 多级排序（元组作为 key）
    data = [(1, 3), (2, 2), (1, 1), (2, 1)]
    sorted_multi = sorted(data, key=lambda x: (x[0], x[1]))
    print(f"\n  多级排序: {data} → {sorted_multi}")

    # groupby（itertools.groupby 配合拆包）
    from itertools import groupby

    records = [
        ("A班", "Alice", 92),
        ("A班", "Bob", 78),
        ("B班", "Charlie", 85),
        ("B班", "Diana", 95),
    ]
    records.sort(key=lambda x: x[0])  # groupby 需要预先排序

    print(f"\n  groupby 分组:")
    for cls, group in groupby(records, key=lambda x: x[0]):
        students_list = [f"{name}({score})" for _, name, score in group]
        print(f"    {cls}: {', '.join(students_list)}")


# ============================================================
# 5. 元组与 dataclass 对比
# ============================================================

def demo_dataclass_comparison():
    """namedtuple vs dataclass vs 普通元组：选择指南"""
    print("\n" + "=" * 60)
    print("  5️⃣ 元组 vs namedtuple vs dataclass")
    print("=" * 60)

    from dataclasses import dataclass

    # 方案 A：普通元组
    point_a = (3, 4)

    # 方案 B：namedtuple
    PointNT = namedtuple("PointNT", ["x", "y"])
    point_b = PointNT(3, 4)

    # 方案 C：dataclass
    @dataclass
    class PointDC:
        x: float
        y: float
    point_c = PointDC(3, 4)

    print(f"\n  {'维度':<20} {'元组':<20} {'namedtuple':<20} {'dataclass':<20}")
    print(f"  {'-' * 80}")
    features = [
        ("类型信息", "隐式", "显式", "显式"),
        ("属性访问", "❌ t[0]", "✅ t.x", "✅ p.x"),
        ("索引访问", "✅ t[0]", "✅ p.x", "❌ p[0]"),
        ("可哈希", "✅", "✅", "❌ 默认"),
        ("可变", "❌ 不可变", "❌ 不可变", "✅ 默认可变"),
        ("方法", "❌", "✅ 可加", "✅ 可加"),
        ("内存", "最小", "较小", "较大"),
        ("解包", "✅", "✅", "✅"),
        ("默认值", "❌", "✅ __defaults__", "✅ 天然支持"),
    ]

    for feat, t, nt, dc in features:
        print(f"  {feat:<20} {t:<20} {nt:<20} {dc:<20}")

    # 性能对比
    from dataclasses import dataclass
    n = 5_000_000
    print(f"\n  创建 {n:,} 个对象性能:")

    # 元组
    start = time.perf_counter()
    for i in range(n):
        _ = (i, i * 2)
    tuple_time = time.perf_counter() - start
    print(f"    普通元组:       {tuple_time:.4f}s")

    # namedtuple
    start = time.perf_counter()
    for i in range(n):
        _ = PointNT(i, i * 2)
    nt_time = time.perf_counter() - start
    print(f"    namedtuple:     {nt_time:.4f}s")

    # dataclass
    start = time.perf_counter()
    for i in range(n):
        _ = PointDC(i, i * 2)
    dc_time = time.perf_counter() - start
    print(f"    dataclass:      {dc_time:.4f}s")

    print(f"\n  💡 性能: 元组 > namedtuple > dataclass")
    print(f"  💡 选择: 简单用元组, 需语义用 namedtuple, 复杂逻辑用 dataclass")


# ============================================================
# 主程序
# ============================================================

def main():
    demo_namedtuple_patterns()
    demo_tuple_as_record()
    demo_tuple_benchmark()
    demo_tuple_functional()
    demo_dataclass_comparison()

    print("\n" + "=" * 60)
    print("  ✅ 元组高级用法演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
