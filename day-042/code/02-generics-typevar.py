"""
Day 42 - 02-generics-typevar.py
泛型与 TypeVar 进阶

演示 TypeVar、Generic 泛型类、Protocol 协议等高级类型提示用法。
所有代码均可直接运行。
"""

from typing import TypeVar, Generic, List, Protocol, Iterator
from typing import overload


# ============================================================
# 1. 基础 TypeVar
# ============================================================

T = TypeVar("T")  # 类型变量，可代表任何类型


def first(items: List[T]) -> T:
    """返回列表第一个元素，保持类型信息"""
    return items[0]


def demo_basic_typevar() -> None:
    """演示基础 TypeVar 使用"""
    print("=" * 60)
    print("1. 基础 TypeVar - 类型变量")
    print("=" * 60)

    nums: List[int] = [1, 2, 3]
    result_int = first(nums)  # mypy 推断 T = int
    print(f"first([1, 2, 3]) = {result_int} (类型: {type(result_int).__name__})")

    strs: List[str] = ["a", "b", "c"]
    result_str = first(strs)  # mypy 推断 T = str
    print(f"first(['a', 'b', 'c']) = {result_str!r} (类型: {type(result_str).__name__})")

    print()


# ============================================================
# 2. 约束 TypeVar
# ============================================================

# 只允许 int 或 float
Number = TypeVar("Number", int, float)


def add_numbers(a: Number, b: Number) -> Number:
    """两个同类型数字相加"""
    return a + b


def demo_constrained_typevar() -> None:
    """演示受约束的 TypeVar"""
    print("=" * 60)
    print("2. 约束 TypeVar")
    print("=" * 60)

    # int + int
    result_i = add_numbers(10, 20)
    print(f"add_numbers(10, 20) = {result_i} (类型: {type(result_i).__name__})")

    # float + float
    result_f = add_numbers(3.14, 2.71)
    print(f"add_numbers(3.14, 2.71) = {result_f} (类型: {type(result_f).__name__})")

    # add_numbers(10, "abc")  # ← mypy 会报错: 类型不匹配

    print()


# ============================================================
# 3. 带边界的 TypeVar
# ============================================================

class Animal:
    """动物基类"""
    def speak(self) -> str:
        return "..."  # 抽象声音

    def __str__(self) -> str:
        return self.__class__.__name__


class Dog(Animal):
    """狗"""
    def speak(self) -> str:
        return "汪汪！"

    def fetch(self) -> str:
        return "狗叼回了球 🎾"


class Cat(Animal):
    """猫"""
    def speak(self) -> str:
        return "喵～"

    def scratch(self) -> str:
        return "猫抓了沙发 😾"


# TAnimal 必须是 Animal 或其子类
TAnimal = TypeVar("TAnimal", bound=Animal)


def make_speak(animal: TAnimal) -> TAnimal:
    """
    让动物发出声音，并返回原对象（保持原始类型）。
    
    使用 bound=Animal 保证传入的是 Animal 子类，
    同时保持返回类型为原始传入类型（而非 Animal）。
    """
    print(f"  {animal} 说: {animal.speak()}")
    return animal


def demo_bounded_typevar() -> None:
    """演示带边界的 TypeVar"""
    print("=" * 60)
    print("3. 带边界的 TypeVar (bound)")
    print("=" * 60)

    dog = make_speak(Dog())  # 返回类型是 Dog，不是 Animal
    cat = make_speak(Cat())  # 返回类型是 Cat，不是 Animal

    # 由于返回类型保持为 Dog，可以调用 Dog 特有方法
    print(f"  {dog} 还能: {dog.fetch()}")

    # 由于返回类型保持为 Cat，可以调用 Cat 特有方法
    print(f"  {cat} 还能: {cat.scratch()}")

    # make_speak("hello")  # ← mypy 会报错: str 不是 Animal 的子类

    print()


# ============================================================
# 4. 泛型类 (Generic[T])
# ============================================================

class Stack(Generic[T]):
    """泛型栈 —— 支持任意元素类型"""
    
    def __init__(self) -> None:
        self._items: List[T] = []
    
    def push(self, item: T) -> None:
        """入栈"""
        self._items.append(item)
    
    def pop(self) -> T:
        """出栈"""
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()
    
    def peek(self) -> T:
        """查看栈顶"""
        if not self._items:
            raise IndexError("peek from empty stack")
        return self._items[-1]
    
    def is_empty(self) -> bool:
        """是否为空"""
        return len(self._items) == 0
    
    def __len__(self) -> int:
        return len(self._items)


def demo_generic_class() -> None:
    """演示泛型类"""
    print("=" * 60)
    print("4. 泛型类 Generic[T]")
    print("=" * 60)

    # 整数栈 —— 类型推断为 Stack[int]
    int_stack = Stack[int]()
    int_stack.push(10)
    int_stack.push(20)
    int_stack.push(30)
    
    top = int_stack.pop()  # top 推断为 int
    print(f"int_stack 出栈: {top} (类型: {type(top).__name__})")
    print(f"int_stack 长度: {len(int_stack)}")
    
    # 字符串栈 —— 类型推断为 Stack[str]
    str_stack = Stack[str]()
    str_stack.push("Hello")
    str_stack.push("World")
    
    greet = str_stack.pop()  # greet 推断为 str
    print(f"str_stack 出栈: {greet!r} (类型: {type(greet).__name__})")
    print(f"str_stack 栈顶: {str_stack.peek()!r}")

    print()


# ============================================================
# 5. Protocol — 结构化子类型
# ============================================================

class Flyable(Protocol):
    """可飞行协议：任何有 fly 方法的类型"""
    def fly(self) -> str: ...


class Bird:
    """鸟类"""
    def fly(self) -> str:
        return "鸟儿在天空飞翔 🐦"


class Airplane:
    """飞机"""
    def fly(self) -> str:
        return "飞机穿过云层 ✈️"


class Fish:
    """鱼类 —— 不会飞"""
    def swim(self) -> str:
        return "鱼儿在水里游 🐟"


def let_fly(flyable: Flyable) -> None:
    """
    接受任何实现了 fly() 方法的对象。
    不需要继承某个基类 —— 只要结构匹配即可（鸭子类型）。
    Protocol 将这种鸭子类型用类型注解表达出来。
    """
    print(f"  {flyable.fly()}")


def demo_protocol() -> None:
    """演示 Protocol 协议"""
    print("=" * 60)
    print("5. Protocol — 结构化子类型")
    print("=" * 60)

    bird = Bird()
    airplane = Airplane()
    fish = Fish()

    print("  let_fly 接受任何有 fly() 方法的对象：")
    let_fly(bird)
    let_fly(airplane)
    # let_fly(fish)  # ← mypy 会报错: Fish 没有 fly() 方法
    print()


# ============================================================
# 6. @overload — 精确描述重载
# ============================================================

@overload
def double(value: int) -> int: ...


@overload
def double(value: str) -> str: ...


@overload
def double(value: List[int]) -> List[int]: ...


def double(value):
    """
    将输入值翻倍（数字×2、字符串重复、列表元素×2）。
    使用 @overload 为不同类型提供精确的类型注解。
    """
    if isinstance(value, int):
        return value * 2
    elif isinstance(value, str):
        return value * 2
    elif isinstance(value, list):
        return [x * 2 for x in value]
    raise TypeError(f"Unsupported type: {type(value)}")


def demo_overload() -> None:
    """演示 @overload 装饰器"""
    print("=" * 60)
    print("6. @overload — 精确描述重载")
    print("=" * 60)

    # 每个调用对应不同的 overload 签名
    n = double(5)          # mypy 知道返回 int
    s = double("ab")       # mypy 知道返回 str
    lst = double([1, 2, 3])  # mypy 知道返回 List[int]

    print(f"double(5)         = {n} (类型: {type(n).__name__})")
    print(f"double('ab')      = {s!r} (类型: {type(s).__name__})")
    print(f"double([1, 2, 3]) = {lst} (类型: {type(lst).__name__})")
    print()


# ============================================================
# 主函数
# ============================================================

if __name__ == "__main__":
    """运行所有演示"""
    demo_basic_typevar()
    demo_constrained_typevar()
    demo_bounded_typevar()
    demo_generic_class()
    demo_protocol()
    demo_overload()
