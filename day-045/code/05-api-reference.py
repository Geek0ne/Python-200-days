"""
Day 045 - API 速查表
OOP 核心概念与语法速查
"""

# ==================== 类与对象 ====================

# 类定义
class MyClass:
    """类的文档字符串"""
    class_attribute = "类属性"

    def __init__(self, value):
        """初始化方法"""
        self.instance_attribute = value  # 实例属性

    def instance_method(self):
        """实例方法"""
        return f"实例方法: {self.instance_attribute}"

    @classmethod
    def class_method(cls):
        """类方法"""
        return f"类方法: {cls.class_attribute}"

    @staticmethod
    def static_method():
        """静态方法"""
        return "静态方法"


# 使用
obj = MyClass("hello")
print(obj.instance_method())  # 实例方法: hello
print(MyClass.class_method())  # 类方法: 类属性
print(MyClass.static_method())  # 静态方法


# ==================== 继承 ====================

class Animal:
    def __init__(self, name):
        self.name = name

    def speak(self):
        raise NotImplementedError


class Dog(Animal):
    def speak(self):
        return "Woof!"


class Cat(Animal):
    def speak(self):
        return "Meow!"


# 多态
animals = [Dog("Buddy"), Cat("Kitty")]
for animal in animals:
    print(f"{animal.name}: {animal.speak()}")


# ==================== 封装 ====================

class BankAccount:
    def __init__(self, balance=0):
        self.__balance = balance  # 私有属性

    @property
    def balance(self):
        """只读属性"""
        return self.__balance

    @balance.setter
    def balance(self, value):
        """设置属性"""
        if value < 0:
            raise ValueError("余额不能为负数")
        self.__balance = value

    def deposit(self, amount):
        """存款"""
        if amount > 0:
            self.__balance += amount
            return True
        return False


account = BankAccount(100)
print(account.balance)  # 100
account.balance = 200
print(account.balance)  # 200


# ==================== 魔术方法 ====================

class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        """开发者表示"""
        return f"Vector({self.x}, {self.y})"

    def __str__(self):
        """用户表示"""
        return f"({self.x}, {self.y})"

    def __add__(self, other):
        """加法"""
        return Vector(self.x + other.x, self.y + other.y)

    def __eq__(self, other):
        """相等比较"""
        return self.x == other.x and self.y == other.y

    def __len__(self):
        """长度"""
        return int((self.x**2 + self.y**2)**0.5)


v1 = Vector(1, 2)
v2 = Vector(3, 4)
print(v1 + v2)  # (4, 6)
print(v1 == Vector(1, 2))  # True


# ==================== 抽象基类 ====================

from abc import ABC, abstractmethod


class Shape(ABC):
    @abstractmethod
    def area(self):
        pass

    @abstractmethod
    def perimeter(self):
        pass


class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height

    def perimeter(self):
        return 2 * (self.width + self.height)


rect = Rectangle(5, 3)
print(f"面积: {rect.area()}")  # 15
print(f"周长: {rect.perimeter()}")  # 16


# ==================== 属性装饰器 ====================

class Temperature:
    def __init__(self, celsius=0):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("温度不能低于绝对零度")
        self._celsius = value

    @property
    def fahrenheit(self):
        return self._celsius * 9/5 + 32


temp = Temperature(100)
print(f"摄氏: {temp.celsius}")  # 100
print(f"华氏: {temp.fahrenheit}")  # 212.0


# ==================== 元类 ====================

class SingletonMeta(type):
    """单例元类"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(metaclass=SingletonMeta):
    def __init__(self, value=None):
        self.value = value


s1 = Singleton("first")
s2 = Singleton("second")
print(s1.value)  # first
print(s2.value)  # first
print(s1 is s2)  # True


# ==================== 装饰器 ====================

def timer(func):
    """计时装饰器"""
    import time
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} 执行时间: {end - start:.4f} 秒")
        return result
    return wrapper


def retry(max_retries=3):
    """重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"重试 {attempt + 1}/{max_retries}: {e}")
        return wrapper
    return decorator


@timer
def slow_function():
    """慢函数"""
    import time
    time.sleep(0.1)
    return "完成"


slow_function()


# ==================== 上下文管理器 ====================

class FileManager:
    """文件管理器"""
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()
        return False


# 使用
with FileManager("test.txt", "w") as f:
    f.write("Hello, World!")


print("\n" + "=" * 60)
print("API 速查表完成！")
print("=" * 60)
