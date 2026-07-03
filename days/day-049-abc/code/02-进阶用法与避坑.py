"""
Day 049 - 抽象基类(ABC) - 进阶用法与避坑
演示：register()、虚拟子类、抽象属性、常见陷阱
"""
from abc import ABC, ABCMeta, abstractmethod
from typing import Any


# ============================================
# 1. register() — 虚拟子类
# ============================================

class Drawable(ABC):
    """可绘制接口"""

    @abstractmethod
    def draw(self) -> str:
        pass


class LegacyWidget:
    """遗留组件 — 没有继承 Drawable，但有 draw() 方法"""

    def draw(self) -> str:
        return "Drawing legacy widget"

    def legacy_method(self):
        return "This is a legacy method"


# 手动注册为虚拟子类
Drawable.register(LegacyWidget)

print("=== register() 虚拟子类 ===")
print(f"issubclass(LegacyWidget, Drawable): {issubclass(LegacyWidget, Drawable)}")
print(f"isinstance(widget, Drawable): {isinstance(LegacyWidget(), Drawable)}")
print(f"draw(): {LegacyWidget().draw()}")

# ⚠️ 注意：虚拟子类只是类型检查通过，不会强制实现接口！
class BrokenWidget:
    def draw(self) -> str:
        return "OK"
    # 但可以不实现任何方法，Python 不会检查

Drawable.register(BrokenWidget)
# BrokenWidget() 是 Drawable 的实例，但可能缺少方法


# ============================================
# 2. 自定义 ABCMeta
# ============================================

class ValidatedMeta(ABCMeta):
    """自定义元类 — 自动验证子类是否实现了所有接口"""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        # 跳过抽象基类本身
        if getattr(cls, '__abstractmethods__', None):
            return cls

        # 检查是否有未实现的抽象方法
        missing = []
        for attr in cls.__abstractmethods__:
            if attr not in namespace:
                missing.append(attr)

        if missing:
            raise TypeError(
                f"类 {name} 缺少抽象方法: {', '.join(missing)}"
            )

        return cls


class Repository(metaclass=ValidatedMeta):
    """仓储抽象基类"""

    @abstractmethod
    def get(self, id: Any) -> Any:
        pass

    @abstractmethod
    def save(self, entity: Any) -> None:
        pass

    @abstractmethod
    def delete(self, id: Any) -> bool:
        pass


# ✅ 正确实现
class UserRepository(Repository):
    def __init__(self):
        self._data = {}

    def get(self, id):
        return self._data.get(id)

    def save(self, entity):
        self._data[id(entity)] = entity

    def delete(self, id):
        if id in self._data:
            del self._data[id]
            return True
        return False


# ❌ 不完整实现（会被 ValidatedMeta 拦截）
try:
    class BadRepository(Repository):
        def get(self, id):
            return None
        # 缺少 save() 和 delete()
except TypeError as e:
    print(f"\n--- ValidatedMeta 拦截 ---")
    print(f"错误: {e}")


# ============================================
# 3. 抽象属性和类方法
# ============================================

class Product(ABC):
    """产品抽象基类 — 使用多种抽象方法"""

    @property
    @abstractmethod
    def name(self) -> str:
        """抽象属性 — 子类必须提供"""
        pass

    @property
    @abstractmethod
    def price(self) -> float:
        """抽象属性 — 子类必须提供"""
        pass

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict):
        """抽象类方法 — 子类必须实现工厂方法"""
        pass

    @staticmethod
    @abstractmethod
    def validate(data: dict) -> bool:
        """抽象静态方法 — 子类必须实现验证逻辑"""
        pass

    def display(self) -> str:
        """非抽象方法 — 提供通用实现"""
        return f"{self.name}: ¥{self.price:.2f}"


class Book(Product):
    """图书产品"""

    def __init__(self, name: str, price: float, author: str):
        self._name = name
        self._price = price
        self.author = author

    @property
    def name(self) -> str:
        return self._name

    @property
    def price(self) -> float:
        return self._price

    @classmethod
    def from_config(cls, config: dict):
        return cls(
            name=config['name'],
            price=config['price'],
            author=config.get('author', '未知')
        )

    @staticmethod
    def validate(data: dict) -> bool:
        return 'name' in data and 'price' in data and data['price'] > 0


class Electronics(Product):
    """电子产品"""

    def __init__(self, name: str, price: float, brand: str):
        self._name = name
        self._price = price
        self.brand = brand

    @property
    def name(self) -> str:
        return self._name

    @property
    def price(self) -> float:
        return self._price

    @classmethod
    def from_config(cls, config: dict):
        return cls(
            name=config['name'],
            price=config['price'],
            brand=config.get('brand', '未知品牌')
        )

    @staticmethod
    def validate(data: dict) -> bool:
        return 'name' in data and 'price' in data and data['price'] > 0


print("\n--- 抽象属性和类方法 ---")
book = Book.from_config({"name": "Python入门", "price": 59.9, "author": "张三"})
print(f"图书: {book.display()}")

# 抽象属性
print(f"书名: {book.name}")
print(f"价格: {book.price}")

# 验证
print(f"验证: {Book.validate({'name': 'test', 'price': 10})}")
print(f"验证: {Book.validate({'name': 'test'})}")


# ============================================
# 4. 常见陷阱
# ============================================

print("\n--- 常见陷阱 ---")

# 陷阱1：抽象方法可以有实现
class WithDefault(ABC):
    @abstractmethod
    def method(self) -> str:
        """虽然有默认实现，但子类仍然必须 override"""
        return "default"

class Child1(WithDefault):
    pass  # ❌ 即使有默认实现，不 override 也不能实例化

try:
    Child1()
except TypeError as e:
    print(f"陷阱1: {e}")

class Child2(WithDefault):
    def method(self) -> str:
        return "custom"  # ✅ 必须显式 override

print(f"Child2().method(): {Child2().method()}")


# 陷阱2：__init__ 中调用抽象方法
class Base(ABC):
    def __init__(self):
        self.value = self.compute()  # ⚠️ 调用抽象方法

    @abstractmethod
    def compute(self) -> int:
        pass

class Derived(Base):
    def __init__(self):
        self.extra = 10
        super().__init__()  # ✅ 先设置 extra，再调用 compute

    def compute(self) -> int:
        return self.extra * 2

d = Derived()
print(f"\n陷阱2: Derived().value = {d.value}")  # 20
