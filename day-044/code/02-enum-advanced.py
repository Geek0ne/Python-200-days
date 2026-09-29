#!/usr/bin/env python3
"""
Day 44 — 02-enum-advanced.py
枚举高级特性：IntEnum, auto(), @unique, 自定义方法

学习目标：
1. 理解 IntEnum 与普通 Enum 的区别
2. 掌握 auto() 自动赋值机制
3. 学会使用 @unique 保证值唯一
4. 掌握自定义枚举方法和属性
5. 了解 IntFlag 位标志
"""

from enum import Enum, IntEnum, auto, unique
from enum import IntFlag

print("=" * 60)
print("1. IntEnum — 可当作整数的枚举")
print("=" * 60)


class StatusCode(IntEnum):
    """HTTP 状态码枚举，IntEnum 允许与整数直接比较"""
    OK = 200
    CREATED = 201
    NOT_FOUND = 404
    SERVER_ERROR = 500


# IntEnum 成员可以直接与整数比较
code = StatusCode.OK
print(f"code = StatusCode.OK = {code}")
print(f"code == 200:            {code == 200}")  # True!
print(f"code == StatusCode.OK:  {code == StatusCode.OK}")  # True

# IntEnum 成员是 int 的子类
print(f"\nisinstance(code, int): {isinstance(code, int)}")  # True

# 可以进行整数运算——好用但也危险
print(f"code + 100:             {code + 100}")   # 300
print(f"code < 300:             {code < 300}")    # True

# 可以用于需要整数的场景
status_map = {200: "Success", 404: "Not Found", 500: "Error"}
print(f"\nstatus_map[StatusCode.OK]: {status_map[StatusCode.OK]}")

# ⚠️ 注意：IntEnum 放弃了类型安全
# 本应只接受特定值，但传任何整数都不会报错
def handle_status(code: StatusCode):
    print(f"处理状态码: {code}")

handle_status(StatusCode.OK)
handle_status(999)  # ✅ 不会报错！这就是 IntEnum 的"缺点"
print("⚠️ IntEnum 可以接受任何整数参数")

print("\n" + "=" * 60)
print("2. auto() — 自动赋值")
print("=" * 60)


class AutoColor(Enum):
    """使用 auto() 自动赋值"""
    RED = auto()
    GREEN = auto()
    BLUE = auto()


print("auto() 自动赋的值:")
for member in AutoColor:
    print(f"  {member.name} = {member.value}")

# 多个枚举类的 auto() 计数器是独立的
print("\nauto() 计数器是独立的:")


class Animal(Enum):
    DOG = auto()
    CAT = auto()
    FISH = auto()


class Plant(Enum):
    TREE = auto()
    FLOWER = auto()
    GRASS = auto()


print("Animal:", [(m.name, m.value) for m in Animal])
print("Plant:",  [(m.name, m.value) for m in Plant])

print("\n" + "=" * 60)
print("3. 自定义 auto() 行为")
print("=" * 60)


class CustomAuto(Enum):
    """覆盖 _generate_next_value_ 定义 auto() 赋值策略"""
    def _generate_next_value_(name, start, count, last_values):
        # 用成员名字的大写作为值
        return name.upper()


class Category(CustomAuto):
    FRUIT = auto()     # value = "FRUIT"
    VEGETABLE = auto() # value = "VEGETABLE"
    MEAT = auto()      # value = "MEAT"


print("自定义 auto() 策略（用名字作为值）:")
for member in Category:
    print(f"  {member.name:10} = {member.value!r}")


class PowerOfTwo(Enum):
    """自定义 auto() 产生 2 的幂"""
    def _generate_next_value_(name, start, count, last_values):
        return 2 ** count  # count 从 0 开始


class Permission(PowerOfTwo):
    NONE = auto()      # 2^0 = 1
    READ = auto()      # 2^1 = 2
    WRITE = auto()     # 2^2 = 4
    EXECUTE = auto()   # 2^3 = 8


print("\n自定义 auto() 策略（2 的幂）:")
for member in Permission:
    print(f"  {member.name:7} = {member.value}")

print("\n" + "=" * 60)
print("4. @unique — 强制值唯一")
print("=" * 60)


class ColorWithAlias(Enum):
    """不加 @unique，允许值重复（别名）"""
    RED = 1
    CRIMSON = 1  # 别名！底层与 RED 是同一个成员
    GREEN = 2
    BLUE = 3


# CRIMSON 是 RED 的别名
print("ColorWithAlias:")
print(f"  ColorWithAlias(1)      = {ColorWithAlias(1)}")  # RED（第一个定义的）
print(f"  ColorWithAlias.CRIMSON  = {ColorWithAlias.CRIMSON}")
print(f"  ColorWithAlias.CRIMSON is ColorWithAlias.RED: {ColorWithAlias.CRIMSON is ColorWithAlias.RED}")

# 别名也出现在 __members__ 中
print(f"  __members__: {[k for k in ColorWithAlias.__members__]}")

print("\n使用 @unique 禁止别名:")


@unique
class UniqueColor(Enum):
    """@unique 装饰器确保每个值都是唯一的"""
    RED = 1
    # CRIMSON = 1  # ❌ 这行会 ValueError
    GREEN = 2
    BLUE = 3


print("  ✅ UniqueColor 定义成功（没有值冲突）")

# 如果尝试定义重复值会怎样？
try:
    @unique
    class BadColor(Enum):
        RED = 1
        CRIMSON = 1  # 重复值！
        GREEN = 2
    print("  这行不会执行")
except ValueError as e:
    print(f"  ❌ @unique 检测到重复值: {e}")

print("\n" + "=" * 60)
print("5. 枚举的自定义方法")
print("=" * 60)


class Planet(Enum):
    """太阳系行星（好吧，没有冥王星）"""
    MERCURY = (0.39, 0.055, "水星")
    VENUS = (0.72, 0.815, "金星")
    EARTH = (1.0, 1.0, "地球")
    MARS = (1.52, 0.107, "火星")
    JUPITER = (5.2, 317.8, "木星")
    SATURN = (9.54, 95.2, "土星")
    URANUS = (19.19, 14.6, "天王星")
    NEPTUNE = (30.07, 17.2, "海王星")

    def __init__(self, distance_au: float, mass_earth: float, name_cn: str):
        self.distance_au = distance_au      # 距离太阳（天文单位）
        self.mass_earth = mass_earth        # 质量（地球=1）
        self.name_cn = name_cn              # 中文名

    @property
    def is_terrestrial(self) -> bool:
        """是否是类地行星"""
        return self.distance_au < 3.0 and self.mass_earth < 1.0

    def surface_gravity_ratio(self) -> float:
        """相对地球表面重力比（简化计算：质量/距离²）"""
        return self.mass_earth / (self.distance_au ** 2)


print("太阳系行星数据:")
print(f"{'名称':8} {'中文名':6} {'距离(AU)':10} {'质量(地球=1)':13} {'类地':4}")
print("-" * 50)
for planet in Planet:
    terr = "✅" if planet.is_terrestrial else "  "
    print(f"{planet.name:8} {planet.name_cn:6} {planet.distance_au:8.2f}  {planet.mass_earth:10.2f}  {terr}")

print(f"\n地球的表面积重力比: {Planet.EARTH.surface_gravity_ratio():.2f}")
print(f"火星的表面积重力比: {Planet.MARS.surface_gravity_ratio():.2f}")
print(f"木星的'表面'重力比: {Planet.JUPITER.surface_gravity_ratio():.2f}")

print("\n" + "=" * 60)
print("6. IntFlag — 位标志")
print("=" * 60)


class FilePermission(IntFlag):
    """文件权限位标志"""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 4
    ALL = READ | WRITE | EXECUTE


print(f"FilePermission.READ = {FilePermission.READ}")
print(f"FilePermission.WRITE = {FilePermission.WRITE}")

# 组合权限
perm = FilePermission.READ | FilePermission.WRITE
print(f"\nREAD | WRITE = {perm}")

# 检查权限
print(f"READ in perm:            {FilePermission.READ in perm}")
print(f"EXECUTE in perm:         {FilePermission.EXECUTE in perm}")

# 添加和移除权限
perm |= FilePermission.EXECUTE
print(f"添加 EXECUTE 后: {perm}")

perm & ~FilePermission.WRITE
print(f"移除 WRITE 后:  {perm & ~FilePermission.WRITE}")

# 位运算示例
print(f"\nALL = {FilePermission.ALL}")
print(f"ALL & ~WRITE = {FilePermission.ALL & ~FilePermission.WRITE}")

print("\n" + "=" * 60)
print("7. 枚举的 __members__ 与别名")
print("=" * 60)


class Day(Enum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7
    # 别名
    MON = 1
    TUE = 2
    WED = 3
    THU = 4
    FRI = 5
    SAT = 6
    SUN = 7


print("迭代 Day (只显示唯一成员):")
for m in Day:
    print(f"  {m}")

print("\n__members__ 包含别名:")
for name, member in Day.__members__.items():
    print(f"  {name} -> {member}")

print(f"\nDay.__members__['MON'] is Day.MONDAY: {Day.__members__['MON'] is Day.MONDAY}")
print(f"Day.MON is Day.MONDAY: {Day.MON is Day.MONDAY}")

print("\n✅ 枚举高级特性学完了！")
