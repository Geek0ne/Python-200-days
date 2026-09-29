"""
Day 032 — 属性与方法：基础用法
======================================================================
实例属性 vs 类属性、实例方法/类方法/静态方法、property 基础
======================================================================
"""

import math

# ====================================================================
# 1. 实例属性 vs 类属性
# ====================================================================
print("=" * 60)
print("1️⃣  实例属性 vs 类属性")
print("=" * 60)


class Employee:
    """员工类"""
    # 类属性
    company = "TechCorp"
    employee_count = 0

    def __init__(self, name, salary):
        # 实例属性
        self.name = name
        self.salary = salary
        Employee.employee_count += 1

    def __repr__(self):
        return f"Employee({self.name}, ${self.salary})"


# 创建实例
alice = Employee("Alice", 60000)
bob = Employee("Bob", 75000)
charlie = Employee("Charlie", 90000)

print(f"  员工列表:")
print(f"    {alice}")
print(f"    {bob}")
print(f"    {charlie}")

print(f"\n  总员工数: {Employee.employee_count}")

# 类属性被所有实例共享
print(f"\n  类属性共享:")
print(f"    Employee.company = {Employee.company}")
print(f"    alice.company = {alice.company}")

# 修改类属性 — 影响所有实例
Employee.company = "NewTech"
print(f"\n  修改 Employee.company 为 'NewTech':")
print(f"    alice.company = {alice.company}")
print(f"    bob.company = {bob.company}")

# 通过实例"修改"类属性 — 实际创建了实例属性
alice.company = "Alice's Company"
print(f"\n  通过 alice.company = 'Alice\\'s Company':")
print(f"    alice.__dict__ = {alice.__dict__}")
print(f"    bob.__dict__ = {bob.__dict__}")
print(f"    alice.company = {alice.company} (实例属性)")
print(f"    bob.company = {bob.company} (类属性)")
print(f"    Employee.company = {Employee.company} (类属性)")

# 恢复
del alice.company
print(f"\n  delete alice.company 后:")
print(f"    alice.company = {alice.company} (恢复类属性)")


# ====================================================================
# 2. 实例方法
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  实例方法详解")
print("=" * 60)


class Calculator:
    """科学计算器实例"""

    def __init__(self, name="Basic"):
        self.name = name
        self._history = []

    def add(self, *args):
        """加法（支持多个参数）"""
        result = sum(args)
        self._add_history(f"add{args} = {result}")
        return result

    def multiply(self, *args):
        """乘法"""
        result = 1
        for x in args:
            result *= x
        self._add_history(f"mul{args} = {result}")
        return result

    def power(self, base, exp):
        """幂运算"""
        result = base ** exp
        self._add_history(f"{base}^{exp} = {result}")
        return result

    def _add_history(self, entry):
        """添加历史（私有方法）"""
        timestamp = __import__('datetime').datetime.now().strftime('%H:%M:%S')
        self._history.append(f"[{timestamp}] {entry}")

    def clear_history(self):
        """清空历史"""
        self._history.clear()

    def get_history(self):
        """获取历史"""
        return self._history.copy()

    # 链式调用支持
    def chain_add(self, x):
        self._result = getattr(self, '_result', 0) + x
        return self

    def chain_mul(self, x):
        self._result = getattr(self, '_result', 0) * x
        return self

    def chain_result(self):
        return getattr(self, '_result', 0)


calc = Calculator("科学计算器")
print(f"\n  计算器名称: {calc.name}")

print(f"\n  计算:")
print(f"    add(1, 2, 3) = {calc.add(1, 2, 3)}")
print(f"    multiply(2, 3, 4) = {calc.multiply(2, 3, 4)}")
print(f"    power(2, 10) = {calc.power(2, 10)}")

print(f"\n  操作历史:")
for h in calc.get_history():
    print(f"    {h}")

# 链式调用
result = calc.chain_add(5).chain_mul(3).chain_add(2).chain_result()
print(f"\n  链式调用: add(5).mul(3).add(2) = {result}")


# ====================================================================
# 3. 类方法（@classmethod）
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  @classmethod — 类方法")
print("=" * 60)


class Circle:
    """圆类 — 演示多种构造方式"""

    def __init__(self, radius):
        self.radius = radius

    @classmethod
    def from_diameter(cls, diameter):
        """通过直径创建"""
        return cls(diameter / 2)

    @classmethod
    def from_area(cls, area):
        """通过面积创建"""
        return cls(math.sqrt(area / math.pi))

    def area(self):
        return math.pi * self.radius ** 2

    def __str__(self):
        return f"Circle(r={self.radius:.2f}, area={self.area():.2f})"


print("  通过半径创建:")
c1 = Circle(5)
print(f"    {c1}")

print("\n  通过直径创建 (类方法):")
c2 = Circle.from_diameter(10)
print(f"    {c2}")

print("\n  通过面积创建 (类方法):")
c3 = Circle.from_area(100)
print(f"    {c3}")


class Temperature:
    """温度类 — 多种单位构造"""

    def __init__(self, celsius=0):
        self._celsius = celsius

    @classmethod
    def from_fahrenheit(cls, f):
        """从华氏度创建"""
        celsius = (f - 32) * 5 / 9
        return cls(celsius)

    @classmethod
    def from_kelvin(cls, k):
        """从开尔文创建"""
        celsius = k - 273.15
        return cls(celsius)

    @property
    def celsius(self):
        return self._celsius

    @property
    def fahrenheit(self):
        return self._celsius * 9 / 5 + 32

    def __str__(self):
        return f"{self.celsius:.1f}°C = {self.fahrenheit:.1f}°F"


print("\n  温度创建:")
t1 = Temperature(25)
t2 = Temperature.from_fahrenheit(77)
t3 = Temperature.from_kelvin(298.15)
print(f"    {t1}")
print(f"    {t2}")
print(f"    {t3}")


# ====================================================================
# 4. 静态方法（@staticmethod）
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  @staticmethod — 静态方法")
print("=" * 60)


class StringUtils:
    """字符串工具类"""

    @staticmethod
    def is_palindrome(s):
        """判断回文字符串"""
        cleaned = ''.join(c.lower() for c in s if c.isalnum())
        return cleaned == cleaned[::-1]

    @staticmethod
    def count_words(s):
        """统计单词数"""
        return len(s.split())

    @staticmethod
    def reverse_words(sentence):
        """反转单词顺序"""
        return ' '.join(sentence.split()[::-1])

    @staticmethod
    def to_snake_case(camel_case):
        """驼峰转蛇形"""
        result = [camel_case[0].lower()]
        for c in camel_case[1:]:
            if c.isupper():
                result.append('_')
                result.append(c.lower())
            else:
                result.append(c)
        return ''.join(result)


print("  字符串工具测试:")
print(f"    'A man a plan a canal Panama' 是回文: {StringUtils.is_palindrome('A man a plan a canal Panama')}")
print(f"    'racecar' 是回文: {StringUtils.is_palindrome('racecar')}")
print(f"    'Hello World Python' 单词数: {StringUtils.count_words('Hello World Python')}")
print(f"    反转: {StringUtils.reverse_words('Hello World Python')}")
print(f"    camelCaseToSnake: {StringUtils.to_snake_case('camelCaseToSnake')}")

# 静态方法不用创建实例
print(f"\n  不需要实例化!")
print(f"    StringUtils.is_palindrome('racecar') = {StringUtils.is_palindrome('racecar')}")


# ====================================================================
# 5. @property 基础
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  @property 装饰器基础")
print("=" * 60)


class Person:
    """人 — 使用 property 进行数据验证"""

    def __init__(self, name, age):
        self._name = None
        self._age = None
        self.name = name  # 通过 setter 设置
        self.age = age    # 通过 setter 设置

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError("名字必须是字符串")
        if len(value.strip()) == 0:
            raise ValueError("名字不能为空")
        self._name = value.strip()

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if not isinstance(value, int):
            raise TypeError("年龄必须是整数")
        if not 0 <= value <= 150:
            raise ValueError(f"年龄必须在 0-150 之间，收到: {value}")
        self._age = value

    @property
    def is_adult(self):
        """计算属性：只读"""
        return self.age >= 18

    @property
    def next_year_age(self):
        """计算属性"""
        return self.age + 1

    def __str__(self):
        return f"{self.name}, {self.age}岁"


print("  创建 Person 对象:")
p = Person("张三", 25)
print(f"    {p}")
print(f"    是否成年: {p.is_adult}")
print(f"    明年年龄: {p.next_year_age}")

# 通过 setter 修改
p.name = "李四"
p.age = 30
print(f"\n  修改后: {p}")

# 测试验证
try:
    p.age = -5  # ❌
except ValueError as e:
    print(f"\n  错误捕获: {e}")

try:
    p.name = ""  # ❌
except ValueError as e:
    print(f"  错误捕获: {e}")

# 只读属性
print(f"\n  只读属性:")
print(f"    p.is_adult = {p.is_adult}")

try:
    p.is_adult = False  # ❌
except AttributeError as e:
    print(f"    不能设置只读属性: {e}")


print("\n" + "=" * 60)
print("✅  Day 32 基础用法演示完成!")
print("=" * 60)
