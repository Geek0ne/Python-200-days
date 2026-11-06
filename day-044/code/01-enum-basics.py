#!/usr/bin/env python3
"""
Day 44 — 01-enum-basics.py
枚举的基本用法

学习目标：
1. 了解如何定义和访问枚举
2. 理解枚举成员是单例
3. 掌握 .name 和 .value 属性
4. 学会遍历枚举成员
5. 理解成员的比较与查找
"""

from enum import Enum

print("=" * 60)
print("1. 基本枚举定义")
print("=" * 60)


class Color(Enum):
    """定义颜色枚举"""
    RED = 1
    GREEN = 2
    BLUE = 3


# 访问枚举成员
print(f"Color.RED   = {Color.RED}")
print(f"Color.GREEN = {Color.GREEN}")
print(f"Color.BLUE  = {Color.BLUE}")

# 成员类型
print(f"\nColor.RED 的类型: {type(Color.RED)}")
print(f"Color.RED 是否是 Color 的实例: {isinstance(Color.RED, Color)}")

print("\n" + "=" * 60)
print("2. .name 和 .value 属性")
print("=" * 60)

print(f"Color.RED.name  = {Color.RED.name!r}")
print(f"Color.RED.value = {Color.RED.value!r}")
print(f"Color.GREEN.name  = {Color.GREEN.name!r}")
print(f"Color.GREEN.value = {Color.GREEN.value!r}")

print("\n" + "=" * 60)
print("3. 枚举成员是单例")
print("=" * 60)

a = Color.RED
b = Color.RED
print(f"a = Color.RED, b = Color.RED")
print(f"a is b:       {a is b}")
print(f"a is Color.RED: {a is Color.RED}")
print(f"a == Color.RED:  {a == Color.RED}")

# 所有成员都是全局唯一的
print(f"\nColor.GREEN is Color.GREEN: {Color.GREEN is Color.GREEN}")

print("\n" + "=" * 60)
print("4. 遍历枚举成员")
print("=" * 60)

print("所有颜色枚举成员:")
for member in Color:
    print(f"  {member.name} = {member.value}")

# 也可以使用 __members__（OrderedDict）
print("\n通过 __members__ 遍历:")
for name, member in Color.__members__.items():
    print(f"  {name} -> {member}")

print("\n" + "=" * 60)
print("5. 枚举成员的不可变性")
print("=" * 60)

try:
    Color.RED = 999  # 尝试修改
except AttributeError as e:
    print(f"❌ 不能修改枚举成员: {e}")

try:
    Color.RED.new_attr = "hello"  # 尝试添加新属性
except AttributeError as e:
    print(f"❌ 不能添加属性到枚举成员: {e}")

print("\n" + "=" * 60)
print("6. 枚举成员的比较")
print("=" * 60)

print(f"Color.RED == Color.RED:   {Color.RED == Color.RED}")
print(f"Color.RED == Color.GREEN: {Color.RED == Color.GREEN}")
print(f"Color.RED is Color.RED:   {Color.RED is Color.RED}")
print(f"Color.RED != Color.GREEN: {Color.RED != Color.GREEN}")

# 枚举成员和值是不同类型，不能直接比较
print(f"\nColor.RED == 1: {Color.RED == 1}")  # False (普通 Enum)
print(f"Color.RED.value == 1: {Color.RED.value == 1}")  # True

print("\n" + "=" * 60)
print("7. 枚举的查找")
print("=" * 60)

# 按名称查找
print(f"Color['RED']   = {Color['RED']}")

# 按值查找
print(f"Color(1)       = {Color(1)}")
print(f"Color(2)       = {Color(2)}")

# 按成员查找（返回自身）
print(f"Color(Color.RED) = {Color(Color.RED)}")

# 查找不存在的值会报错
try:
    Color(999)
except ValueError as e:
    print(f"\n❌ 按不存在的值查找: {e}")

try:
    Color["PURPLE"]
except KeyError as e:
    print(f"❌ 按不存在的名称查找: {e}")

print("\n" + "=" * 60)
print("8. 枚举的哈希性")
print("=" * 60)

# 枚举成员默认是可哈希的，可以用作字典键
fav_colors = {
    Color.RED: "激情",
    Color.GREEN: "自然",
    Color.BLUE: "宁静",
}
print(f"Color.RED 在字典中的含义: {fav_colors[Color.RED]}")

# 也能用在集合中
color_set = {Color.RED, Color.GREEN, Color.BLUE, Color.RED}  # RED 重复
print(f"颜色集合: {color_set}")  # 自动去重

print("\n" + "=" * 60)
print("9. 实战：用枚举定义一周的天数")
print("=" * 60)


class Weekday(Enum):
    """星期枚举"""
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7

    def is_weekend(self):
        """判断是否是周末"""
        return self in (Weekday.SATURDAY, Weekday.SUNDAY)

    def is_weekday(self):
        """判断是否是工作日"""
        return not self.is_weekend()


print("工作日:", [d.name for d in Weekday if d.is_weekday()])
print("周末:", [d.name for d in Weekday if d.is_weekend()])

today = Weekday.MONDAY
print(f"\n今天: {today.name}")
print(f"是工作日吗? {today.is_weekday()}")
print(f"是周末吗? {today.is_weekend()}")

# 枚举值可以是任意类型，甚至字符串
class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

print(f"\nHTTP 方法:")
for method in HttpMethod:
    print(f"  {method.name:6} -> {method.value}")

print("\n✅ 枚举基础用法学完了！")
