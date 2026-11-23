"""
Day 031 — 类与对象：基础用法
======================================================================
类的定义、实例化、构造方法、实例方法、特殊方法
======================================================================
"""

# ====================================================================
# 1. 最简单的类
# ====================================================================
print("=" * 60)
print("1️⃣  最简单的类定义与实例化")
print("=" * 60)


class Dog:
    """狗类"""
    species = "Canis familiaris"  # 类变量

    def __init__(self, name, age):
        """构造方法：初始化实例"""
        self.name = name  # 实例变量
        self.age = age

    def bark(self):
        """实例方法"""
        return f"{self.name} says Woof!"

    def get_info(self):
        return f"{self.name} ({self.age}岁) - {self.species}"


# 创建实例
buddy = Dog("Buddy", 3)
max_dog = Dog("Max", 5)

print(f"  buddy: {buddy.get_info()}")
print(f"  max:   {max_dog.get_info()}")
print(f"  buddy.bark(): {buddy.bark()}")

# 类变量 vs 实例变量
print(f"\n  类变量访问:")
print(f"    Dog.species = {Dog.species}")
print(f"    buddy.species = {buddy.species}")
print(f"    max_dog.species = {max_dog.species}")

# 修改类变量
Dog.species = "Canis lupus familiaris"
print(f"  修改后: buddy.species = {buddy.species}")

# 修改实例的类变量（实际上创建了实例变量）
buddy.species = "不同的物种"
print(f"  buddy.species = {buddy.species} (实例变量)")
print(f"  max_dog.species = {max_dog.species} (类变量)")


# ====================================================================
# 2. 构造方法 __init__ 详解
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  __init__ 构造方法详解")
print("=" * 60)


class Point:
    """二维坐标点"""

    def __init__(self, x=0, y=0):
        """
        初始化点坐标
        Args:
            x: x 坐标（默认 0）
            y: y 坐标（默认 0）
        """
        self.x = x
        self.y = y
        print(f"  创建点 ({self.x}, {self.y})")

    def distance_from_origin(self):
        """计算到原点的距离"""
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def distance_to(self, other):
        """计算到另一个点的距离"""
        dx = self.x - other.x
        dy = self.y - other.y
        return (dx ** 2 + dy ** 2) ** 0.5


print("  创建点对象:")
p1 = Point(3, 4)
p2 = Point()  # 使用默认值
p3 = Point(y=5, x=10)  # 关键字参数

print(f"  p1 = ({p1.x}, {p1.y}), 到原点距离: {p1.distance_from_origin():.2f}")
print(f"  p2 = ({p2.x}, {p2.y})")
print(f"  p1 到 p3 距离: {p1.distance_to(p3):.2f}")


# ====================================================================
# 3. __new__ vs __init__
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  __new__ 与 __init__ 的区别")
print("=" * 60)


class Singleton:
    """单例模式：演示 __new__ 的用途"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print("    __new__: 创建新实例")
            cls._instance = super().__new__(cls)
        else:
            print("    __new__: 返回已有实例")
        return cls._instance

    def __init__(self, value=None):
        if value is not None:
            self.value = value
        print(f"    __init__: self.id={id(self)}, value={getattr(self, 'value', 'N/A')}")


print("  单例模式演示:")
s1 = Singleton("first")
s2 = Singleton("second")
print(f"  s1 is s2: {s1 is s2}")  # True
print(f"  s1.value = {s1.value}")  # first (__init__ 被第二次调用覆盖了)
print(f"  s2.value = {s2.value}")  # second


# ====================================================================
# 4. 特殊方法
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  ⭐ 特殊方法（Magic Methods）")
print("=" * 60)


class Vector:
    """二维向量：演示多种特殊方法"""

    def __init__(self, x, y):
        self.x = x
        self.y = y

    # ---- 字符串表示 ----
    def __str__(self):
        """用户友好的字符串表示"""
        return f"({self.x}, {self.y})"

    def __repr__(self):
        """开发者友好的字符串表示"""
        return f"Vector({self.x!r}, {self.y!r})"

    # ---- 比较 ----
    def __eq__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __lt__(self, other):
        """按模长比较"""
        return self.magnitude() < other.magnitude()

    # ---- 运算 ----
    def __add__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        """标量乘法"""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar):
        """标量除法"""
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector(self.x / scalar, self.y / scalar)

    # ---- 容器行为 ----
    def __len__(self):
        """向量不能有长度，返回 2 代表二维"""
        return 2

    def __getitem__(self, index):
        """允许类似 v[0], v[1] 的访问"""
        if index == 0 or index == 'x':
            return self.x
        elif index == 1 or index == 'y':
            return self.y
        raise IndexError("Vector index out of range")

    def __bool__(self):
        """零向量为 False"""
        return self.x != 0 or self.y != 0

    # ---- 其他 ----
    def magnitude(self):
        """向量模长"""
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __call__(self, scale=1):
        """使实例可调用"""
        return Vector(self.x * scale, self.y * scale)


print("  创建向量:")
v1 = Vector(3, 4)
v2 = Vector(1, 2)

print(f"  v1 = {v1}")
print(f"  repr(v1) = {repr(v1)}")
print(f"  v2 = {v2}")

print(f"\n  运算:")
v3 = v1 + v2
print(f"  v1 + v2 = {v3}")
print(f"  v1 * 3 = {v1 * 3}")
print(f"  v1 / 2 = {v1 / 2}")

print(f"\n  比较:")
print(f"  v1 == Vector(3, 4): {v1 == Vector(3, 4)}")
print(f"  v1 == v2: {v1 == v2}")
print(f"  v1 < v2: {v1 < v2}")

print(f"\n  容器行为:")
print(f"  v1[0] = {v1[0]}, v1['x'] = {v1['x']}")
print(f"  len(v1) = {len(v1)}")

print(f"\n  布尔值:")
print(f"  bool(v1) = {bool(v1)}")
print(f"  bool(Vector(0, 0)) = {bool(Vector(0, 0))}")

print(f"\n  可调用:")
result = v1(2)
print(f"  v1(2) = {result}")


# ====================================================================
# 5. 链式调用
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  方法链式调用")
print("=" * 60)


class StringBuilder:
    """支持链式调用的字符串构建器"""

    def __init__(self, initial=""):
        self._buffer = initial

    def append(self, text):
        self._buffer += text
        return self

    def append_line(self, text=""):
        self._buffer += text + "\n"
        return self

    def upper(self):
        self._buffer = self._buffer.upper()
        return self

    def replace(self, old, new):
        self._buffer = self._buffer.replace(old, new)
        return self

    def build(self):
        return self._buffer

    def __str__(self):
        return self._buffer


sb = StringBuilder()
result = (
    sb.append("Hello")
    .append(", ")
    .append("World")
    .append_line("!")
    .upper()
    .replace("WORLD", "PYTHON")
    .build()
)
print(f"  链式调用结果:")
print(f"  {result}")


# ====================================================================
# 6. 理解 self
# ====================================================================
print("\n" + "=" * 60)
print("6️⃣  深入理解 self")
print("=" * 60)


class SelfDemo:
    def __init__(self, value):
        self.value = value

    def show(self):
        return id(self)

    def show_value(self):
        return self.value


obj = SelfDemo(100)
print(f"  obj id  = {id(obj)}")
print(f"  obj.show() = {obj.show()}")
print(f"  id(obj) == obj.show(): {id(obj) == obj.show()}")

# 等价调用方式
print(f"\n  等价调用:")
print(f"  obj.show_value(): {obj.show_value()}")           # 一般形式
print(f"  SelfDemo.show_value(obj): {SelfDemo.show_value(obj)}")  # 等价形式


print("\n" + "=" * 60)
print("✅  Day 31 基础用法演示完成!")
print("=" * 60)
