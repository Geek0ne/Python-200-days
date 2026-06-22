"""
Day 033 — 继承：实战案例
======================================================================
形状层次结构系统
  1. 抽象基类 Shape
  2. 2D 形状 (Circle, Rectangle, Triangle)
  3. 3D 形状 (Sphere, Box, Cylinder)
  4. 形状管理器
======================================================================
"""

import math
from abc import ABC, abstractmethod
from functools import total_ordering


# ====================================================================
# 1. 抽象基类 Shape
# ====================================================================
@total_ordering
class Shape(ABC):
    """形状抽象基类 — 所有形状的基类"""

    # 类属性
    shape_count = 0

    def __init__(self, name="Shape"):
        self.name = name
        self._id = Shape.shape_count
        Shape.shape_count += 1

    @property
    def id(self):
        return self._id

    # ── 抽象方法（子类必须实现） ──
    @abstractmethod
    def area(self):
        """计算面积"""
        pass

    @abstractmethod
    def perimeter(self):
        """计算周长"""
        pass

    # ── 具体方法 ──
    def describe(self):
        """形状描述"""
        return (f"{self.name:>10} (ID:{self._id}) "
                f"面积={self.area():>8.2f} "
                f"周长={self.perimeter():>8.2f}")

    def scale(self, factor):
        """缩放 — 默认实现（子类可重写）"""
        raise NotImplementedError(f"{self.__class__.__name__} 不支持 scale")

    # ── 特殊方法 ──
    def __str__(self):
        return self.describe()

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __eq__(self, other):
        if not isinstance(other, Shape):
            return NotImplemented
        return (abs(self.area() - other.area()) < 1e-10 and
                abs(self.perimeter() - other.perimeter()) < 1e-10)

    def __lt__(self, other):
        if not isinstance(other, Shape):
            return NotImplemented
        return self.area() < other.area()

    def __hash__(self):
        return hash((self.__class__.__name__, round(self.area(), 5)))


# ====================================================================
# 2. 2D 形状
# ====================================================================
class Circle(Shape):
    """圆形"""

    def __init__(self, radius, name="Circle"):
        super().__init__(name)
        self._radius = radius

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        if value <= 0:
            raise ValueError("半径必须为正数")
        self._radius = value

    @property
    def diameter(self):
        return self._radius * 2

    def area(self):
        return math.pi * self._radius ** 2

    def perimeter(self):
        return 2 * math.pi * self._radius

    def scale(self, factor):
        self.radius *= factor
        return self


class Rectangle(Shape):
    """矩形"""

    def __init__(self, width, height, name="Rectangle"):
        super().__init__(name)
        self._width = width
        self._height = height

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        if value <= 0:
            raise ValueError("宽度必须为正数")
        self._width = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        if value <= 0:
            raise ValueError("高度必须为正数")
        self._height = value

    @property
    def is_square(self):
        return self._width == self._height

    def area(self):
        return self._width * self._height

    def perimeter(self):
        return 2 * (self._width + self._height)

    def scale(self, factor):
        self._width *= factor
        self._height *= factor
        return self


class Triangle(Shape):
    """三角形（使用海伦公式）"""

    def __init__(self, a, b, c, name="Triangle"):
        super().__init__(name)
        # 验证三角形
        if not (a + b > c and a + c > b and b + c > a):
            raise ValueError(f"边长 ({a}, {b}, {c}) 不能构成三角形")
        self._a = a
        self._b = b
        self._c = c

    @property
    def sides(self):
        return (self._a, self._b, self._c)

    @property
    def is_equilateral(self):
        """等边三角形"""
        return self._a == self._b == self._c

    @property
    def is_isosceles(self):
        """等腰三角形"""
        return len({self._a, self._b, self._c}) == 2

    @property
    def is_right(self):
        """直角三角形"""
        sides = sorted([self._a, self._b, self._c])
        return abs(sides[0]**2 + sides[1]**2 - sides[2]**2) < 1e-10

    def area(self):
        """海伦公式"""
        s = self.perimeter() / 2
        return math.sqrt(s * (s - self._a) * (s - self._b) * (s - self._c))

    def perimeter(self):
        return self._a + self._b + self._c

    def scale(self, factor):
        self._a *= factor
        self._b *= factor
        self._c *= factor
        return self


class Square(Rectangle):
    """正方形 — 继承自 Rectangle"""

    def __init__(self, side, name="Square"):
        super().__init__(side, side, name)

    @property
    def side(self):
        return self._width

    @side.setter
    def side(self, value):
        if value <= 0:
            raise ValueError("边长必须为正数")
        self._width = value
        self._height = value

    @property
    def diagonal(self):
        return self._width * math.sqrt(2)

    def describe(self):
        base = super().describe()
        return f"{base} (正方形, 边长={self._width})"


# ====================================================================
# 3. 3D 形状（额外层级）
# ====================================================================
class SolidShape(Shape):
    """立体形状 — 扩展 Shape"""

    @abstractmethod
    def volume(self):
        """体积"""
        pass

    @abstractmethod
    def surface_area(self):
        """表面积"""
        pass

    def describe(self):
        base = super().describe()
        return (f"{base} | 体积={self.volume():>10.2f} "
                f"表面积={self.surface_area():>10.2f}")


class Sphere(SolidShape):
    """球体"""

    def __init__(self, radius, name="Sphere"):
        super().__init__(name)
        self.radius = radius

    def area(self):
        """横截面积"""
        return math.pi * self.radius ** 2

    def perimeter(self):
        """大圆周"""
        return 2 * math.pi * self.radius

    def volume(self):
        return 4 / 3 * math.pi * self.radius ** 3

    def surface_area(self):
        return 4 * math.pi * self.radius ** 2

    def scale(self, factor):
        self.radius *= factor
        return self


class Box(SolidShape):
    """长方体"""

    def __init__(self, length, width, height, name="Box"):
        super().__init__(name)
        self.length = length
        self.width = width
        self.height = height

    def area(self):
        """底面积"""
        return self.length * self.width

    def perimeter(self):
        """底面周长"""
        return 2 * (self.length + self.width)

    def volume(self):
        return self.length * self.width * self.height

    def surface_area(self):
        l, w, h = self.length, self.width, self.height
        return 2 * (l * w + l * h + w * h)

    def scale(self, factor):
        self.length *= factor
        self.width *= factor
        self.height *= factor
        return self


class Cylinder(SolidShape):
    """圆柱体"""

    def __init__(self, radius, height, name="Cylinder"):
        super().__init__(name)
        self.radius = radius
        self.height = height

    def area(self):
        """底面积"""
        return math.pi * self.radius ** 2

    def perimeter(self):
        """底面周长"""
        return 2 * math.pi * self.radius

    def volume(self):
        return math.pi * self.radius ** 2 * self.height

    def surface_area(self):
        return (2 * math.pi * self.radius * self.height
                + 2 * math.pi * self.radius ** 2)

    def scale(self, factor):
        self.radius *= factor
        self.height *= factor
        return self


# ====================================================================
# 4. 形状管理器
# ====================================================================
class ShapeManager:
    """形状管理器 — 管理所有形状"""

    def __init__(self):
        self.shapes = []

    def add(self, shape):
        self.shapes.append(shape)
        return self

    def remove(self, shape):
        self.shapes.remove(shape)
        return self

    def total_area(self):
        return sum(s.area() for s in self.shapes)

    def total_perimeter(self):
        return sum(s.perimeter() for s in self.shapes)

    def sort_by_area(self, reverse=False):
        self.shapes.sort(key=lambda s: s.area(), reverse=reverse)
        return self

    def filter_by_type(self, shape_class):
        return [s for s in self.shapes if isinstance(s, shape_class)]

    def find_largest(self):
        return max(self.shapes, key=lambda s: s.area())

    def find_smallest(self):
        return min(self.shapes, key=lambda s: s.area())

    def display_all(self):
        print(f"\n  📋 形状列表 ({len(self.shapes)} 个)")
        print(f"  {'='*55}")
        for i, shape in enumerate(self.shapes, 1):
            print(f"  {i:2d}. {shape.describe()}")
        print(f"  {'='*55}")
        print(f"  总面积: {self.total_area():>10.2f}")
        print(f"  总周长: {self.total_perimeter():>10.2f}")

    def display_largest_smallest(self):
        print(f"\n  🏆 最大: {self.find_largest().describe()}")
        print(f"  👶 最小: {self.find_smallest().describe()}")


# ====================================================================
# 5. 完整演示
# ====================================================================
print("=" * 60)
print("📐  形状层次结构系统 — 完整演示")
print("=" * 60)

manager = ShapeManager()

# 添加 2D 形状
print(f"\n─── 创建 2D 形状 ───")
manager.add(Circle(5, "大圆形"))
manager.add(Rectangle(4, 6, "矩形"))
manager.add(Triangle(3, 4, 5, "直角三角形"))
manager.add(Square(4, "正方形"))
manager.add(Circle(2.5, "小圆形"))

# 添加 3D 形状
print(f"\n─── 创建 3D 形状 ───")
manager.add(Sphere(3, "球体"))
manager.add(Box(3, 4, 5, "长方体"))
manager.add(Cylinder(2, 6, "圆柱"))

# 显示所有形状
manager.display_all()

# 排序
print(f"\n─── 按面积排序 (从小到大) ───")
manager.sort_by_area()
manager.display_all()

# 最大/最小
manager.display_largest_smallest()

# 按类型过滤
print(f"\n─── 圆形类形状 ───")
circles = manager.filter_by_type(Circle)
for c in circles:
    print(f"    {c.describe()}")

print(f"\n─── 立体形状 (体积>0) ───")
for s in manager.filter_by_type(SolidShape):
    print(f"    {s.describe()}")

# 缩放
print(f"\n─── 缩放测试 ───")
circle = manager.shapes[2]  # 某个圆形
print(f"  缩放前: {circle.describe()}")
circle.scale(2)
print(f"  放大2倍: {circle.describe()}")

# 继承树验证
print(f"\n─── 继承关系验证 ───")
print(f"  issubclass(Square, Rectangle): {issubclass(Square, Rectangle)}")
print(f"  issubclass(Square, Shape):     {issubclass(Square, Shape)}")
print(f"  issubclass(Sphere, SolidShape): {issubclass(Sphere, SolidShape)}")
print(f"  isinstance(Square(4), Rectangle): {isinstance(Square(4), Rectangle)}")
print(f"  isinstance(Square(4), Shape):     {isinstance(Square(4), Shape)}")

# 特殊方法
print(f"\n─── 特殊方法测试 ───")
s1 = Square(5)
s2 = Square(5)
s3 = Square(4)
print(f"  Square(5) == Square(5): {s1 == s2}")
print(f"  Square(5) == Square(4): {s1 == s3}")
print(f"  Square(5) < Square(10): {s1 < s3}")
print(f"  s1 in [s1, s2, s3]: {s1 in [s1, s2, s3]}")

# 所有形状
print(f"\n─── 形状数量 ───")
print(f"  本次创建: {manager.shapes}")
print(f"  总形状数 (类属性): {Shape.shape_count}")

print(f"\n" + "=" * 60)
print("🏆  形状层次结构系统运行完毕!")
print(f"    共 {len(manager.shapes)} 个形状")
print(f"    总面积: {manager.total_area():.2f}")
print(f"    总周长: {manager.total_perimeter():.2f}")
print("=" * 60)
