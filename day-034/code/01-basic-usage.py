"""
Day 034 — 多态与鸭子类型：基础用法
====================================

涵盖：
1. 传统继承多态
2. 鸭子类型多态
3. EAFP 与 LBYL 对比
4. isinstance + ABC 检查
"""

# ====================================
# 1. 传统继承多态
# ====================================
print("=" * 50)
print("1️⃣ 传统继承多态")
print("=" * 50)


class Animal:
    """动物基类"""

    def speak(self) -> str:
        raise NotImplementedError("子类必须实现 speak 方法")

    def move(self) -> str:
        return "移动中..."


class Dog(Animal):
    def speak(self) -> str:
        return "汪汪! 🐕"

    def move(self) -> str:
        return "四条腿奔跑"


class Cat(Animal):
    def speak(self) -> str:
        return "喵喵~ 🐈"

    def move(self) -> str:
        return "悄无声息地行走"


class Bird(Animal):
    def speak(self) -> str:
        return "叽叽喳喳! 🐦"

    def move(self) -> str:
        return "展翅飞翔"


def animal_show(animal: Animal) -> None:
    """多态调用 —— 不关心具体类型"""
    print(f"  {animal.__class__.__name__}: {animal.speak()}, {animal.move()}")


animals = [Dog(), Cat(), Bird()]
for a in animals:
    animal_show(a)


# ====================================
# 2. 鸭子类型多态
# ====================================
print("\n" + "=" * 50)
print("2️⃣ 鸭子类型多态")
print("=" * 50)


class Duck:
    """鸭子 —— 会叫、会走、会游泳"""

    def quack(self) -> str:
        return "嘎嘎! 🦆"

    def walk(self) -> str:
        return "摇摇摆摆地走"

    def swim(self) -> str:
        return "在水面游"


class Person:
    """人 —— 也会叫、会走、会游泳（但和鸭子没关系）"""

    def quack(self) -> str:
        return "我在学鸭子叫: 嘎嘎!"

    def walk(self) -> str:
        return "两条腿走路"

    def swim(self) -> str:
        return "自由泳"


class RobotDuck:
    """机器鸭 —— 会叫、会走，但不会游泳"""

    def quack(self) -> str:
        return "哔——嘎嘎! 🤖"

    def walk(self) -> str:
        return "机械步态"

    def swim(self) -> str:
        raise RuntimeError("机器鸭不能游泳！会短路！")


def duck_test(creature) -> None:
    """鸭子测试 —— 不关心类型，只关心有没有这些方法"""
    print(f"  [{type(creature).__name__}]")
    print(f"    叫声: {creature.quack()}")
    print(f"    走路: {creature.walk()}")
    try:
        print(f"    游泳: {creature.swim()}")
    except RuntimeError as e:
        print(f"    游泳: ❌ {e}")


print("\n🐤 鸭子测试:")
duck_test(Duck())
duck_test(Person())
duck_test(RobotDuck())


# ====================================
# 3. EAFP vs LBYL
# ====================================
print("\n" + "=" * 50)
print("3️⃣ EAFP vs LBYL 风格对比")
print("=" * 50)


def divide_lbyl(a, b):
    """LBYL 风格：先检查再操作"""
    if not isinstance(a, (int, float)):
        return None, "a 不是数字"
    if not isinstance(b, (int, float)):
        return None, "b 不是数字"
    if b == 0:
        return None, "除数不能为零"
    return a / b, None


def divide_eafp(a, b):
    """EAFP 风格：直接操作，出错再处理"""
    try:
        return a / b
    except TypeError:
        return None
    except ZeroDivisionError:
        return None


test_cases = [
    (10, 3),
    (10, 0),
    ("abc", 5),
    (10, "xyz"),
]

print("\n📊 LBYL 风格:")
for a, b in test_cases:
    result, error = divide_lbyl(a, b)
    print(f"  {a} / {b} = {result}" + (f" ({error})" if error else ""))

print("\n📊 EAFP 风格:")
for a, b in test_cases:
    result = divide_eafp(a, b)
    print(f"  {a} / {b} = {result}" + (" (None)" if result is None else ""))


# EAFP 在字典访问中的优势
print("\n📊 EAFP 字典访问:")
data = {"name": "Alice", "age": 30}

keys_to_access = ["name", "email", "age", "address"]

print("  LBYL 风格:")
for key in keys_to_access:
    if key in data:
        print(f"    {key} = {data[key]}")
    else:
        print(f"    {key} = ❌ 不存在")

print("  EAFP 风格（推荐）:")
for key in keys_to_access:
    try:
        print(f"    {key} = {data[key]}")
    except KeyError:
        print(f"    {key} = ❌ 不存在")

# 更 Pythonic 的方式
print("  Pythonic (dict.get):")
for key in keys_to_access:
    value = data.get(key, "不存在")
    print(f"    {key} = {value}")


# ====================================
# 4. isinstance + collections.abc
# ====================================
print("\n" + "=" * 50)
print("4️⃣ isinstance 与 ABC 类型检查")
print("=" * 50)

from collections.abc import (
    Iterable,
    Iterator,
    Sequence,
    MutableSequence,
    Mapping,
    Set as AbstractSet,
    Callable,
)

test_objects = [
    ([1, 2, 3], "list"),
    ("hello", "str"),
    ({1, 2, 3}, "set"),
    ({"a": 1}, "dict"),
    (range(5), "range"),
    ((1, 2), "tuple"),
]

print("\n📊 行为类型检查:")
for obj, name in test_objects:
    checks = []
    if isinstance(obj, Sequence):
        checks.append("Sequence")
    if isinstance(obj, MutableSequence):
        checks.append("MutableSequence")
    if isinstance(obj, Mapping):
        checks.append("Mapping")
    if isinstance(obj, AbstractSet):
        checks.append("Set")
    if isinstance(obj, Iterable):
        checks.append("Iterable")
    print(f"  {name:8s} -> {', '.join(checks)}")

# Callable 检查
print("\n📊 Callable 检查:")


def my_func():
    pass


class MyCallable:
    def __call__(self):
        pass


for obj, name in [(my_func, "function"), (MyCallable(), "callable_obj"),
                   (42, "integer"), ("hello", "string")]:
    print(f"  {name:14s} -> {'可调用' if callable(obj) else '不可调用'}")
