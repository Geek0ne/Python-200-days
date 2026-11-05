"""
Day 43 - 01-basic-usage.py
dataclass 基础用法

本文件展示 @dataclass 装饰器的核心功能：
自动生成 __init__、__repr__、__eq__ 以及装饰器参数的使用。
"""

from dataclasses import dataclass


# ============================================================
# 1. 最简单的 dataclass
# ============================================================
# 只要用 @dataclass 装饰类，写上类型注解的字段即可
# Python 自动生成构造函数、字符串表示、相等比较

@dataclass
class Point:
    """二维坐标点——dataclass 最经典的入门示例"""
    x: float          # 字段声明（没有默认值 → 必填参数）
    y: float          # 字段声明（没有默认值 → 必填参数）


def demo_basic() -> None:
    """演示 dataclass 基础功能：自动生成的方法"""
    print("=" * 60)
    print("1. 基础 dataclass 示例")
    print("=" * 60)

    # 自动生成 __init__ — 不需要手写构造函数
    p1 = Point(1.0, 2.0)
    p2 = Point(3.0, 4.0)

    # 自动生成 __repr__ — 友好可读的字符串表示
    print(f"p1 = {p1}")          # Point(x=1.0, y=2.0)
    print(f"p2 = {p2}")          # Point(x=3.0, y=4.0)

    # 自动生成 __eq__ — 相同属性值的实例相等
    p3 = Point(1.0, 2.0)
    print(f"p1 == p3: {p1 == p3}")  # True

    # 直接打印 dataclass 字段
    print(f"p1.x = {p1.x}, p1.y = {p1.y}")
    print()


# ============================================================
# 2. 带默认值的字段
# ============================================================

@dataclass
class Rectangle:
    """矩形——演示带默认值的字段"""
    width: float          # 必填参数
    height: float         # 必填参数
    color: str = "black"  # 有默认值 → 可选参数
    border: int = 0       # 有默认值 → 可选参数


def demo_defaults() -> None:
    """演示带默认值字段的 dataclass"""
    print("=" * 60)
    print("2. 带默认值的字段")
    print("=" * 60)

    # 只传必填参数，默认值自动生效
    r1 = Rectangle(100, 50)
    print(f"r1 = {r1}")
    # Rectangle(width=100, height=50, color='black', border=0)

    # 覆盖部分默认值
    r2 = Rectangle(200, 100, color="red")
    print(f"r2 = {r2}")
    # Rectangle(width=200, height=100, color='red', border=0)

    # 覆盖全部
    r3 = Rectangle(300, 150, "blue", 2)
    print(f"r3 = {r3}")
    # Rectangle(width=300, height=150, color='blue', border=2)

    # ⚠️ 注意：有默认值的字段必须放在无默认值的字段后面
    # 如果写成 width: float = 0; height: float → 会报语法错误
    print()


# ============================================================
# 3. 装饰器参数：init, repr, eq
# ============================================================

@dataclass(init=True, repr=True, eq=True)
class User:
    """用户——演示装饰器参数控制"""
    username: str
    email: str
    role: str = "viewer"

    # 我们可以像普通类一样添加普通方法
    def greet(self) -> str:
        """自定义方法"""
        return f"你好，{self.username}！"


@dataclass(repr=False)  # 不生成 __repr__
class SecretItem:
    """隐藏 repr 的类——防止敏感信息泄漏"""
    id: int
    value: str

    # 自己手动实现返回部分信息
    def __repr__(self) -> str:
        return f"SecretItem(id={self.id}, value='******')"


def demo_decorator_params() -> None:
    """演示装饰器参数对生成的方法的控制"""
    print("=" * 60)
    print("3. 装饰器参数：init, repr, eq")
    print("=" * 60)

    # init=True（默认）→ 自动生成构造函数
    u1 = User("alice", "alice@example.com", "admin")
    u2 = User("bob", "bob@example.com")

    # repr=True（默认）→ 友好的字符串表示
    print(f"u1 = {u1}")
    # User(username='alice', email='alice@example.com', role='admin')

    # eq=True（默认）→ 根据所有字段值比较
    u3 = User("alice", "alice@example.com", "admin")
    print(f"u1 == u3: {u1 == u3}")  # True

    # 自定义方法
    print(f"u1.greet(): {u1.greet()}")

    # repr=False 的效果
    s = SecretItem(1, "超级机密数据")
    print(f"SecretItem with repr=False: {s}")  # 使用手动实现的 __repr__
    print()


# ============================================================
# 4. order=True：自动生成比较方法
# ============================================================

@dataclass(order=True)  # 生成 __lt__, __le__, __gt__, __ge__
class Version:
    """软件版本号——演示自动排序"""
    major: int
    minor: int
    patch: int


@dataclass(order=True)
class Product:
    """产品——按价格排序"""
    name: str
    price: float


def demo_order() -> None:
    """演示 order=True 的效果"""
    print("=" * 60)
    print("4. order=True：自动排序")
    print("=" * 60)

    # 版本号比较
    v1 = Version(2, 0, 0)
    v2 = Version(1, 9, 9)
    v3 = Version(2, 0, 0)

    print(f"v1 = {v1}, v2 = {v2}")
    print(f"v1 > v2: {v1 > v2}")   # True (2.0.0 > 1.9.9)
    print(f"v1 >= v3: {v1 >= v3}") # True (相等)
    print(f"v1 < v2: {v1 < v2}")   # False

    # 直接使用 sorted() 排序
    products = [
        Product("鼠标", 29.9),
        Product("键盘", 199.0),
        Product("显示器", 1299.0),
        Product("耳机", 89.0),
    ]
    sorted_products = sorted(products)
    print("\n按价格排序后的商品：")
    for p in sorted_products:
        print(f"  {p}")

    # sorted 默认升序，降序加 reverse=True
    print("\n按价格降序：")
    for p in sorted(products, reverse=True):
        print(f"  {p}")
    print()


# ============================================================
# 5. frozen=True：不可变数据类
# ============================================================

@dataclass(frozen=True)
class ImmutablePoint:
    """不可变坐标点——类似 namedtuple 但语法更友好"""
    x: float
    y: float
    label: str = ""


def demo_frozen() -> None:
    """演示 frozen=True 的不可变性"""
    print("=" * 60)
    print("5. frozen=True：不可变数据类")
    print("=" * 60)

    ip = ImmutablePoint(10.0, 20.0, "原点")
    print(f"不变量: {ip}")

    # 可以读取字段
    print(f"x = {ip.x}, y = {ip.y}")

    # ❌ 尝试修改会引发 FrozenInstanceError
    try:
        ip.x = 99.0  # dataclasses.FrozenInstanceError
    except Exception as e:
        print(f"修改失败: {type(e).__name__}: {e}")

    # frozen=True 时，实例自动可哈希（可以用作字典键）
    point_map = {
        ImmutablePoint(0, 0): "坐标原点",
        ImmutablePoint(1, 0): "右",
    }
    print(f"可以用作字典键: {point_map}")

    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    demo_basic()
    demo_defaults()
    demo_decorator_params()
    demo_order()
    demo_frozen()

    print("=" * 60)
    print("🎉 所有基础用法演示完成！")
    print("=" * 60)
