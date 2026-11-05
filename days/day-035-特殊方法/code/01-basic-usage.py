"""
Day 035 — 特殊方法：基础用法
===============================

涵盖：
1. __str__ / __repr__ 字符串表示
2. __len__ / __getitem__ 容器协议
3. __eq__ / __hash__ 相等与哈希
4. __bool__ / __int__ / __float__ 类型转换
5. __call__ 可调用对象
"""


# ====================================
# 1. __str__ / __repr__ 字符串表示
# ====================================
print("=" * 60)
print("1️⃣ __str__ / __repr__ 字符串表示")
print("=" * 60)


class Book:
    """图书类 —— 展示 __repr__ 和 __str__ 的区别"""

    def __init__(self, title: str, author: str, year: int, isbn: str):
        self.title = title
        self.author = author
        self.year = year
        self.isbn = isbn

    def __repr__(self):
        """开发者友好的表示 —— 包含重建所需的所有信息"""
        return (f"Book(title={self.title!r}, author={self.author!r}, "
                f"year={self.year}, isbn={self.isbn!r})")

    def __str__(self):
        """用户友好的表示"""
        return f"《{self.title}》by {self.author} ({self.year})"


book = Book("Python 核心编程", "张三", 2024, "978-7-XXX-XXXXX-X")
print(f"  str(book)  = {str(book)}")
print(f"  repr(book) = {repr(book)}")
# 交互式环境默认使用 repr
print(f"  print(book) = ", end="")
print(book)  # 调用 __str__


# 如果没有 __str__，退化为 __repr__
class SimpleBook:
    def __init__(self, title: str):
        self.title = title

    def __repr__(self):
        return f"SimpleBook({self.title!r})"


sb = SimpleBook("Python 入门")
print(f"\n  print(SimpleBook): {sb}")  # 调用 __repr__


# 格式控制
class Temperature:
    def __init__(self, celsius: float):
        self.celsius = celsius

    def __repr__(self):
        return f"Temperature({self.celsius})"

    def __str__(self):
        return f"{self.celsius}°C"

    def __format__(self, spec: str) -> str:
        """支持 format() 和 f-string 格式控制"""
        if spec == "f":
            return f"{self.celsius:.1f}°F ({(self.celsius * 9/5 + 32):.1f}°C)"
        if spec == "k":
            return f"{self.celsius + 273.15:.2f}K"
        return str(self)


t = Temperature(25)
print(f"\n  format 默认: {t}")
print(f"  format 华氏: {t:f}")
print(f"  format 开氏: {t:k}")


# ====================================
# 2. __len__ / __getitem__ 容器协议
# ====================================
print("\n" + "=" * 60)
print("2️⃣ __len__ / __getitem__ 容器协议")
print("=" * 60)


class Deck:
    """一副扑克牌 —— 展示容器协议"""

    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['A', '2', '3', '4', '5', '6', '7',
             '8', '9', '10', 'J', 'Q', 'K']

    def __init__(self):
        self._cards = [
            f"{rank}{suit}"
            for suit in self.SUITS
            for rank in self.RANKS
        ]

    def __len__(self):
        """len(deck) 返回 52"""
        return len(self._cards)

    def __getitem__(self, position):
        """deck[i] 返回第 i 张牌；支持切片"""
        return self._cards[position]

    def __contains__(self, card):
        """'A♠' in deck → True"""
        return card in self._cards

    def __iter__(self):
        """返回迭代器（自动实现 for card in deck）"""
        return iter(self._cards)

    def __reversed__(self):
        """reversed(deck) 返回反向迭代器"""
        return reversed(self._cards)


deck = Deck()
print(f"  扑克牌总数: {len(deck)}")
print(f"  第一张牌: {deck[0]}")
print(f"  最后一张牌: {deck[-1]}")
print(f"  前 5 张: {deck[:5]}")
print(f"  'A♠' in deck: {'A♠' in deck}")
print(f"  'JOKER' in deck: {'JOKER' in deck}")

# 自动获得迭代能力
print(f"\n  遍历前 5 张: ", end="")
for i, card in enumerate(deck):
    if i >= 5:
        break
    print(card, end=" ")
print()

# 反向遍历
print(f"  反向前 5 张: ", end="")
for i, card in enumerate(reversed(deck)):
    if i >= 5:
        break
    print(card, end=" ")
print()


# 可变容器：__setitem__
class MutableDeck(Deck):
    """可变扑克牌 —— 支持修改和删除"""

    def __setitem__(self, position, card):
        """deck[i] = card"""
        self._cards[position] = card

    def __delitem__(self, position):
        """del deck[i]"""
        del self._cards[position]

    def pop(self):
        """弹出最后一张牌"""
        return self._cards.pop()


mdeck = MutableDeck()
print(f"\n  原始第一张: {mdeck[0]}")
mdeck[0] = "JOKER"
print(f"  修改后: {mdeck[0]}")
del mdeck[-1]
print(f"  删除最后一张后还剩: {len(mdeck)} 张")


# ====================================
# 3. __eq__ / __hash__ 相等与哈希
# ====================================
print("\n" + "=" * 60)
print("3️⃣ __eq__ / __hash__ 相等与哈希")
print("=" * 60)


class Color:
    """颜色类 —— 实现相等性判断和哈希支持"""

    def __init__(self, r: int, g: int, b: int):
        self.r = max(0, min(255, r))
        self.g = max(0, min(255, g))
        self.b = max(0, min(255, b))

    def __repr__(self):
        return f"Color({self.r}, {self.g}, {self.b})"

    def __str__(self):
        return f"rgb({self.r}, {self.g}, {self.b})"

    def __eq__(self, other):
        """支持 == 和 != 比较"""
        if not isinstance(other, Color):
            return NotImplemented
        return (self.r, self.g, self.b) == (other.r, other.g, other.b)

    def __hash__(self):
        """支持用作字典键和集合元素"""
        return hash((self.r, self.g, self.b))


red1 = Color(255, 0, 0)
red2 = Color(255, 0, 0)
blue = Color(0, 0, 255)

print(f"  red1 == red2: {red1 == red2}")  # True
print(f"  red1 == blue: {red1 == blue}")  # False
print(f"  red1 is blue: {red1 is blue}")  # False

# 作为字典键
color_map = {
    red1: "鲜红",
    blue: "蓝色",
}
print(f"  color_map[red1]: {color_map[red1]}")
print(f"  color_map[Color(255,0,0)]: {color_map[Color(255, 0, 0)]}")  # same key

# 作为集合元素
color_set = {red1, blue, Color(255, 0, 0), Color(0, 255, 0)}
print(f"  color_set: {color_set}")  # 会去重


# ====================================
# 4. __bool__ / __int__ / __float__ 类型转换
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 类型转换魔法方法")
print("=" * 60)


class Fraction:
    """分数类 —— 展示类型转换协议"""

    def __init__(self, numerator: int, denominator: int):
        if denominator == 0:
            raise ValueError("分母不能为零")
        self.numerator = numerator
        self.denominator = denominator

    def __repr__(self):
        return f"Fraction({self.numerator}, {self.denominator})"

    def __str__(self):
        return f"{self.numerator}/{self.denominator}"

    def __float__(self):
        """float(fraction)"""
        return self.numerator / self.denominator

    def __int__(self):
        """int(fraction) — 取整"""
        return self.numerator // self.denominator

    def __bool__(self):
        """bool(fraction) — 零分数为 False"""
        return self.numerator != 0

    def __neg__(self):
        return Fraction(-self.numerator, self.denominator)

    def __pos__(self):
        return Fraction(self.numerator, self.denominator)

    def __abs__(self):
        return Fraction(abs(self.numerator), abs(self.denominator))


f1 = Fraction(3, 4)
f2 = Fraction(0, 5)
f3 = Fraction(-5, 3)

print(f"  f1 = {f1}")
print(f"  float(f1) = {float(f1):.3f}")
print(f"  int(f1) = {int(f1)}")
print(f"  bool(f1) = {bool(f1)}")
print(f"  bool(f2) = {bool(f2)}")
print(f"  abs(f3) = {abs(f3)}")

# Fraction 作为条件
fractions = [Fraction(0, 1), Fraction(1, 2), Fraction(0, 3), Fraction(3, 4)]
non_zero = [f for f in fractions if f]
print(f"  非零分数: {non_zero}")


# ====================================
# 5. __call__ 可调用对象
# ====================================
print("\n" + "=" * 60)
print("5️⃣ __call__ 可调用对象")
print("=" * 60)


class Accumulator:
    """累加器 —— 每次调用累加值"""

    def __init__(self, initial=0):
        self.value = initial

    def __call__(self, x=1):
        self.value += x
        return self.value

    def reset(self):
        self.value = 0


acc = Accumulator(10)
print(f"  acc(5) = {acc(5)}")   # 15
print(f"  acc(3) = {acc(3)}")   # 18
print(f"  acc()  = {acc()}")    # 19
print(f"  调用次数跟踪:")

# 装饰器风格
import functools


class CountCalls:
    """函数调用计数装饰器"""

    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"  → {self.func.__name__} 第 {self.count} 次调用")
        return self.func(*args, **kwargs)


@CountCalls
def greet(name):
    return f"Hello, {name}!"


print()
print(greet("Alice"))
print(greet("Bob"))
print(greet("Charlie"))
print(f"总计调用: {greet.count} 次")


class PowerFactory:
    """幂函数工厂 —— 演示参数化的可调用对象"""

    def __init__(self, exponent: float):
        self.exponent = exponent

    def __call__(self, base: float) -> float:
        return base ** self.exponent

    def __repr__(self):
        return f"PowerFactory(exponent={self.exponent})"


square = PowerFactory(2)
cube = PowerFactory(3)
sqrt = PowerFactory(0.5)

print(f"\n  square(5) = {square(5)}")
print(f"  cube(3) = {cube(3)}")
print(f"  sqrt(16) = {sqrt(16)}")

# 可调用对象作为策略
strategies = {
    "square": PowerFactory(2),
    "cube": PowerFactory(3),
    "sqrt": PowerFactory(0.5),
}

for name, strategy in strategies.items():
    print(f"  {name}(10) = {strategy(10)}")
