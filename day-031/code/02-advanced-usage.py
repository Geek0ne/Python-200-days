"""
Day 031 — 类与对象：进阶用法
======================================================================
类变量与实例变量深层机制、__slots__、抽象基类、设计模式入门
======================================================================
"""

import weakref

# ====================================================================
# 1. 类变量与实例变量深层机制
# ====================================================================
print("=" * 60)
print("1️⃣  类变量与实例变量 — 属性查找机制")
print("=" * 60)


class Employee:
    """员工类"""
    # 类变量
    company = "TechCorp"
    raise_rate = 1.05
    employee_count = 0

    def __init__(self, name, salary):
        # 实例变量
        self.name = name
        self.salary = salary
        Employee.employee_count += 1

    def apply_raise(self):
        """应用涨薪"""
        self.salary = int(self.salary * Employee.raise_rate)

    def __repr__(self):
        return f"Employee({self.name}, ${self.salary})"


print("  属性查找顺序: 实例变量 → 类变量 → 父类")

alice = Employee("Alice", 50000)
bob = Employee("Bob", 60000)

print(f"\n  创建员工:")
print(f"    {alice}")
print(f"    {bob}")
print(f"    总员工数: {Employee.employee_count}")

# 类变量被所有实例共享
print(f"\n  类变量共享:")
print(f"    Employee.company = {Employee.company}")
print(f"    alice.company = {alice.company}")
print(f"    bob.company = {bob.company}")

# 通过实例修改类变量 — 实际上创建了实例变量
alice.company = "NewCompany"  # 创建实例变量，不影响类
print(f"\n  通过实例修改类变量:")
print(f"    alice.company = {alice.company}  (实例变量)")
print(f"    bob.company = {bob.company}      (类变量)")
print(f"    Employee.company = {Employee.company}  (类变量没变)")

# 删除实例变量后恢复类变量
del alice.company
print(f"\n  删除实例变量后:")
print(f"    alice.company = {alice.company}  (重新使用类变量)")

# 类变量通过类修改 — 影响所有实例
print(f"\n  通过类修改类变量:")
Employee.raise_rate = 1.10
print(f"    raise_rate = {Employee.raise_rate}")
alice.apply_raise()
print(f"    alice 涨薪后: {alice.salary}")

print(f"\n  📘 变量查找 MRO:")
print(f"    1. 先找实例的 __dict__")
print(f"    2. 没找到 → 找类的 __dict__")
print(f"    3. 没找到 → 找父类的 __dict__")


# ====================================================================
# 2. __slots__ — 内存优化
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  ⭐ __slots__ — 内存优化与属性限制")
print("=" * 60)


class PointWithoutSlots:
    """普通类（使用 __dict__）"""
    def __init__(self, x, y):
        self.x = x
        self.y = y


class PointWithSlots:
    """使用 __slots__ 优化内存"""
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y


# 内存对比
import sys

p1 = PointWithoutSlots(1, 2)
p2 = PointWithSlots(1, 2)

print(f"  PointWithoutSlots __dict__ 大小: {sys.getsizeof(p1.__dict__)} bytes")
print(f"  PointWithSlots 无 __dict__ (使用 slots)")
print(f"  整个对象大小对比:")
print(f"    普通: {sys.getsizeof(p1)} bytes")
print(f"    slots: {sys.getsizeof(p2)} bytes")

# 性能对比 — 创建大量对象
import time

N = 1_000_000

start = time.perf_counter()
pts1 = [PointWithoutSlots(i, i) for i in range(N)]
t1 = time.perf_counter() - start

start = time.perf_counter()
pts2 = [PointWithSlots(i, i) for i in range(N)]
t2 = time.perf_counter() - start

print(f"\n  创建 {N:,} 个对象:")
print(f"    普通: {t1:.2f}s")
print(f"    slots: {t2:.2f}s")
print(f"    提速: {t1/t2:.1f}x")

# __slots__ 限制属性
print(f"\n  __slots__ 限制:")
print(f"    p2.x = {p2.x} ✅")
try:
    p2.z = 3  # ❌ __slots__ 没有 'z'
except AttributeError as e:
    print(f"    p2.z = 3 → AttributeError: {e}")


# ====================================================================
# 3. 抽象基类（ABC）
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  抽象基类（ABC）— 定义接口规范")
print("=" * 60)

from abc import ABC, abstractmethod


class Shape(ABC):
    """形状抽象基类"""

    @abstractmethod
    def area(self):
        """计算面积"""
        pass

    @abstractmethod
    def perimeter(self):
        """计算周长"""
        pass

    def describe(self):
        """通用描述（非抽象方法）"""
        return f"面积: {self.area():.2f}, 周长: {self.perimeter():.2f}"


class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def area(self):
        return 3.14159 * self.radius ** 2

    def perimeter(self):
        return 2 * 3.14159 * self.radius


class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height

    def perimeter(self):
        return 2 * (self.width + self.height)


# 尝试实例化抽象类
try:
    s = Shape()  # ❌ 不能实例化抽象类
except TypeError as e:
    print(f"  Shape() 失败: {e}")

# 子类实现
circle = Circle(5)
rect = Rectangle(4, 6)

print(f"\n  Circle(半径=5):")
print(f"    面积: {circle.area():.2f}")
print(f"    周长: {circle.perimeter():.2f}")
print(f"    描述: {circle.describe()}")

print(f"\n  Rectangle(4×6):")
print(f"    面积: {rect.area():.2f}")
print(f"    周长: {rect.perimeter():.2f}")
print(f"    描述: {rect.describe()}")

# 类型检查
print(f"\n  类型检查:")
print(f"    isinstance(circle, Shape): {isinstance(circle, Shape)}")
print(f"    isinstance(rect, Shape): {isinstance(rect, Shape)}")
print(f"    issubclass(Circle, Shape): {issubclass(Circle, Shape)}")


# ====================================================================
# 4. 工厂模式
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  工厂模式 — 根据输入创建不同对象")
print("=" * 60)


class Logger(ABC):
    """日志抽象基类"""

    @abstractmethod
    def log(self, message):
        pass


class ConsoleLogger(Logger):
    def log(self, message):
        print(f"  [CONSOLE] {message}")


class FileLogger(Logger):
    def __init__(self, filename="app.log"):
        self.filename = filename

    def log(self, message):
        with open(self.filename, 'a') as f:
            f.write(f"[FILE] {message}\n")
        print(f"  [FILE] 已写入: {message}")


class ErrorLogger(Logger):
    def log(self, message):
        print(f"  🔴 [ERROR] {message}")


class LoggerFactory:
    """日志工厂类"""
    @staticmethod
    def create(log_type):
        loggers = {
            'console': ConsoleLogger,
            'file': FileLogger,
            'error': ErrorLogger,
        }
        logger_class = loggers.get(log_type)
        if not logger_class:
            raise ValueError(f"未知日志类型: {log_type}")
        return logger_class()


# 使用工厂
print("  通过工厂创建不同的日志器:")
for log_type in ['console', 'error', 'file']:
    logger = LoggerFactory.create(log_type)
    logger.log(f"这是 {log_type} 日志")
    print()


# ====================================================================
# 5. 弱引用与垃圾回收
# ====================================================================
print("=" * 60)
print("5️⃣  ⭐ 弱引用与对象生命周期")
print("=" * 60)


class Resource:
    """模拟占用资源的对象"""
    def __init__(self, name):
        self.name = name
        print(f"  【创建】{self.name}")

    def __del__(self):
        print(f"  【销毁】{self.name}")

    def use(self):
        print(f"  使用中: {self.name}")


print("  强引用（阻止垃圾回收）:")
res = Resource("强引用对象")
ref = weakref.ref(res)
print(f"  弱引用有效: {ref() is not None}")
print(f"  通过弱引用访问: {ref().name}")

del res  # 删除强引用
print(f"  弱引用失效 (None): {ref() is None}")

print("\n  WeakValueDictionary — 自动管理的缓存:")
import gc
gc.collect()  # 清理


class CacheItem:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        print(f"  + 缓存: {key}={value}")

    def __del__(self):
        print(f"  - 缓存失效: {self.key}={self.value}")


cache = weakref.WeakValueDictionary()

# 创建并缓存
item1 = CacheItem("a", 1)
item2 = CacheItem("b", 2)

cache["a"] = item1
cache["b"] = item2

print(f"\n  缓存内容: dict(cache) = {dict(cache)}")

# 删除强引用 → 自动从缓存清除
print("\n  删除 item1...")
del item1
gc.collect()
print(f"  缓存内容: dict(cache) = {dict(cache)}")


# ====================================================================
# 6. 不可变对象与 __hash__
# ====================================================================
print("\n" + "=" * 60)
print("6️⃣  __hash__ 与不可变对象")
print("=" * 60)


class MutablePoint:
    """可变点（不可哈希）"""
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"MP({self.x},{self.y})"


class ImmutablePoint:
    """不可变点（可哈希）"""
    __slots__ = ('_x', '_y')

    def __init__(self, x, y):
        # 使用 object.__setattr__ 绕过 __slots__ 限制
        object.__setattr__(self, '_x', x)
        object.__setattr__(self, '_y', y)

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    def __eq__(self, other):
        if not isinstance(other, ImmutablePoint):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __repr__(self):
        return f"IP({self.x},{self.y})"


mp = MutablePoint(1, 2)
ip = ImmutablePoint(1, 2)

# 可变对象不可哈希
try:
    hash(mp)
except TypeError as e:
    print(f"  MutablePoint 不可哈希: {e}")

# 不可变对象可哈希
print(f"  ImmutablePoint 哈希值: {hash(ip)}")

# 可以用作字典键
d = {ip: "point1"}
print(f"  字典键: {d}")
print(f"  d[ImmutablePoint(1,2)] = {d[ImmutablePoint(1, 2)]}")


# ====================================================================
# 7. 属性访问控制
# ====================================================================
print("\n" + "=" * 60)
print("7️⃣  属性访问控制 — 命名约定")
print("=" * 60)


class BankAccount:
    """银行账户（演示属性访问控制）"""

    def __init__(self, owner, balance):
        self.owner = owner          # 公开
        self._branch = "Main"       # 约定为受保护
        self.__balance = balance    # 名称改写 (name mangling)

    def deposit(self, amount):
        if amount > 0:
            self.__balance += amount
            return True
        return False

    def withdraw(self, amount):
        if 0 < amount <= self.__balance:
            self.__balance -= amount
            return True
        return False

    def get_balance(self):
        return self.__balance


account = BankAccount("Alice", 1000)

print(f"  公开属性: account.owner = {account.owner}")
print(f"  受保护: account._branch = {account._branch}")

# 名称改写 — 不能直接访问 __balance
try:
    print(f"  account.__balance = {account.__balance}")
except AttributeError as e:
    print(f"  无法直接访问: {e}")
    print(f"  通过 name mangling: {account._BankAccount__balance}")

# 通过方法访问
account.deposit(500)
account.withdraw(200)
print(f"  余额: ${account.get_balance()}")


print("\n" + "=" * 60)
print("✅  Day 31 进阶用法演示完成!")
print("=" * 60)
