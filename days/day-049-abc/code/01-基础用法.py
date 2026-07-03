"""
Day 049 - 抽象基类(ABC) - 基础用法
演示：ABC 的基本概念、抽象方法、强制接口实现
"""
from abc import ABC, abstractmethod
from typing import List


# ============================================
# 1. 基本 ABC：形状类
# ============================================

class Shape(ABC):
    """
    形状抽象基类 — 定义形状的通用接口。

    设计要点：
    - 标记为 ABC，不能直接实例化
    - area() 和 perimeter() 标记为 @abstractmethod
    - 子类必须实现所有抽象方法才能实例化
    """

    @abstractmethod
    def area(self) -> float:
        """计算面积"""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """计算周长"""
        pass

    def describe(self) -> str:
        """非抽象方法 — 子类可以直接使用"""
        return f"{self.__class__.__name__}: 面积={self.area():.2f}, 周长={self.perimeter():.2f}"


class Circle(Shape):
    """圆形 — 实现 Shape 的所有抽象方法"""

    def __init__(self, radius: float):
        if radius <= 0:
            raise ValueError("半径必须大于0")
        self.radius = radius

    def area(self) -> float:
        import math
        return math.pi * self.radius ** 2

    def perimeter(self) -> float:
        import math
        return 2 * math.pi * self.radius


class Rectangle(Shape):
    """矩形 — 实现 Shape 的所有抽象方法"""

    def __init__(self, width: float, height: float):
        if width <= 0 or height <= 0:
            raise ValueError("宽和高必须大于0")
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)


# ============================================
# 2. 未实现所有抽象方法的子类
# ============================================

class IncompleteShape(Shape):
    """只实现了部分抽象方法 — 不能实例化"""

    def area(self) -> float:
        return 0  # 实现了 area

    # 缺少 perimeter() — 不完整


# ============================================
# 3. 多重抽象方法
# ============================================

class Animal(ABC):
    """动物抽象基类"""

    @abstractmethod
    def speak(self) -> str:
        pass

    @abstractmethod
    def move(self) -> str:
        pass

    @property
    @abstractmethod
    def species(self) -> str:
        pass


class Dog(Animal):
    """狗 — 实现所有抽象方法"""

    @property
    def species(self) -> str:
        return "犬科"

    def speak(self) -> str:
        return "汪汪！"

    def move(self) -> str:
        return "四条腿跑"


class Bird(Animal):
    """鸟 — 实现所有抽象方法"""

    @property
    def species(self) -> str:
        return "鸟科"

    def speak(self) -> str:
        return "叽叽喳喳！"

    def move(self) -> str:
        return "用翅膀飞"


# ============================================
# 4. 运行演示
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Day 049 - 抽象基类(ABC) 基础用法")
    print("=" * 50)

    # 测试形状
    print("\n--- 形状类 ---")
    circle = Circle(5)
    rect = Rectangle(4, 6)

    shapes: List[Shape] = [circle, rect]
    for shape in shapes:
        print(shape.describe())

    # 测试抽象类不能实例化
    print("\n--- 抽象类限制 ---")
    try:
        shape = Shape()  # ❌ TypeError
    except TypeError as e:
        print(f"Shape() 失败: {e}")

    try:
        incomplete = IncompleteShape()  # ❌ TypeError
    except TypeError as e:
        print(f"IncompleteShape() 失败: {e}")

    # 测试动物
    print("\n--- 动物类 ---")
    animals: List[Animal] = [Dog(), Bird()]
    for animal in animals:
        print(f"{animal.species}: {animal.speak()} {animal.move()}")

    # 检查类型
    print("\n--- 类型检查 ---")
    print(f"Circle 是 Shape 吗？ {issubclass(Circle, Shape)}")
    print(f"circle 是 Shape 吗？ {isinstance(circle, Shape)}")
    print(f"circle 是 Animal 吗？ {isinstance(circle, Animal)}")
