"""
Day 43 - 03-dataclass-vs-namedtuple.py
dataclass 与 namedtuple / 普通类的对比

本文件通过实际对比展示三种定义数据容器的方式的差异，
帮助你在不同场景下做出合适的选择。
"""

from dataclasses import dataclass, field, fields
from typing import NamedTuple, List, Optional
from collections import namedtuple
import time
import sys


# ============================================================
# 1. 相同功能，三种实现
# ============================================================

# --- 普通类 ---
# 需要手写所有模板方法
class NormalPerson:
    """普通类实现——需要写大量模板代码"""

    def __init__(self, name: str, age: int, email: str = ""):
        self.name = name
        self.age = age
        self.email = email

    def __repr__(self) -> str:
        return f"NormalPerson(name={self.name!r}, age={self.age!r}, email={self.email!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NormalPerson):
            return NotImplemented
        return (self.name, self.age, self.email) == (other.name, other.age, other.email)


# --- namedtuple ---
# 最简洁，但功能有限
# 经典方式
PersonTuple = namedtuple("PersonTuple", ["name", "age", "email"])
# 默认值——经典版的 default 参数 (Python 3.7+)
PersonTupleDefault = namedtuple("PersonTupleDefault", ["name", "age", "email"], defaults=[""])

# 现代方式：用 typing.NamedTuple（支持类型注解和方法）
class PersonNamedTuple(NamedTuple):
    name: str
    age: int
    email: str = ""

    def greet(self) -> str:
        return f"你好，我是 {self.name}"


# --- dataclass ---
# 简洁且功能丰富
@dataclass
class PersonDataClass:
    """数据类实现——几行代码搞定"""
    name: str
    age: int
    email: str = ""

    def greet(self) -> str:
        return f"你好，我是 {self.name}"


def demo_creation_comparison() -> None:
    """对比三种方式的代码量和易用性"""
    print("=" * 60)
    print("1. 代码量对比")
    print("=" * 60)

    # 普通类
    np = NormalPerson("Alice", 30, "alice@example.com")
    print(f"普通类: {np}  |  {np.greet() if hasattr(np, 'greet') else '无方法'}")

    # namedtuple
    nt = PersonNamedTuple("Bob", 25, "bob@example.com")
    print(f"namedtuple: {nt}  |  {nt.greet()}")

    # dataclass
    dc = PersonDataClass("Charlie", 35, "charlie@example.com")
    print(f"dataclass: {dc}  |  {dc.greet()}")

    print()


# ============================================================
# 2. 可变性对比
# ============================================================

def demo_mutability() -> None:
    """对比三种方式的不可变性"""
    print("=" * 60)
    print("2. 可变性对比")
    print("=" * 60)

    # ★ dataclass 默认可变
    dc = PersonDataClass("Alice", 30, "alice@example.com")
    dc.age = 31  # ✅ 可以修改
    print(f"dataclass 可变: {dc}")

    # ★ dataclass frozen=True 不可变
    @dataclass(frozen=True)
    class FrozenPerson:
        name: str
        age: int

    fp = FrozenPerson("Bob", 25)
    print(f"dataclass frozen: {fp}")
    try:
        fp.age = 26
    except Exception as e:
        print(f"  尝试修改 ➜ {type(e).__name__}: {e}")

    # ★ namedtuple 不可变
    nt = PersonNamedTuple("Charlie", 35, "charlie@example.com")
    print(f"namedtuple: {nt}")
    try:
        nt.age = 36
    except Exception as e:
        print(f"  尝试修改 ➜ {type(e).__name__}: {e}")

    # ★ 普通类 可变
    nc = NormalPerson("Diana", 28)
    nc.age = 29  # ✅
    print(f"普通类可变: {nc}")

    print()


# ============================================================
# 3. 访问方式对比
# ============================================================

def demo_access() -> None:
    """对比三种方式的字段访问方式"""
    print("=" * 60)
    print("3. 字段访问方式")
    print("=" * 60)

    # 属性访问：三种都支持
    dc = PersonDataClass("Alice", 30)
    nt = PersonNamedTuple("Bob", 25)
    nc = NormalPerson("Charlie", 35)

    # 属性访问（点语法）— 都支持
    print(f"属性访问 — dataclass:  {dc.name}")
    print(f"属性访问 — namedtuple: {nt.name}")
    print(f"属性访问 — 普通类:    {nc.name}")

    # 索引访问 — 只有 namedtuple 支持
    print(f"\n索引访问 — namedtuple[0]: {nt[0]}")   # Bob
    print(f"索引访问 — namedtuple[1]: {nt[1]}")   # 25

    # 拆包 — 只有 namedtuple 支持
    name, age, email = nt
    print(f"\n拆包 — namedtuple: name={name}, age={age}")

    try:
        print(dc[0])  # ❌
    except TypeError as e:
        print(f"dataclass 不支持索引: {e}")

    # 转字典
    import dataclasses
    print(f"\ndataclasses.asdict:   {dataclasses.asdict(dc)}")
    print(f"namedtuple._asdict:   {nt._asdict()}")
    print(f"vars(普通类):           {vars(nc)}")

    print()


# ============================================================
# 4. 性能对比
# ============================================================

def demo_performance() -> None:
    """三种方式的创建性能对比"""
    print("=" * 60)
    print("4. 创建性能对比（创建 100 万个对象）")
    print("=" * 60)

    # 预热
    N = 1_000_000

    # dataclass 创建
    start = time.perf_counter()
    dcs = [PersonDataClass(f"User-{i}", i % 100) for i in range(N)]
    dc_time = time.perf_counter() - start

    # namedtuple 创建
    start = time.perf_counter()
    nts = [PersonNamedTuple(f"User-{i}", i % 100) for i in range(N)]
    nt_time = time.perf_counter() - start

    # 普通类创建
    start = time.perf_counter()
    ncs = [NormalPerson(f"User-{i}", i % 100) for i in range(N)]
    nc_time = time.perf_counter() - start

    print(f"  dataclass:  {dc_time:.3f} 秒  ({dc_time/nc_time:.2f}x 普通类)")
    print(f"  namedtuple: {nt_time:.3f} 秒  ({nt_time/nc_time:.2f}x 普通类)")
    print(f"  普通类:     {nc_time:.3f} 秒  (基准)")

    # 读取性能
    start = time.perf_counter()
    for p in dcs:
        _ = p.name, p.age
    dc_read = time.perf_counter() - start

    start = time.perf_counter()
    for p in nts:
        _ = p.name, p.age
    nt_read = time.perf_counter() - start

    print(f"\n属性读取性能（100 万次）:")
    print(f"  dataclass:  {dc_read:.3f} 秒")
    print(f"  namedtuple: {nt_read:.3f} 秒")

    # 内存对比
    print(f"\n内存占用（取 1 个实例的粗略大小）:")
    print(f"  dataclass:  {sys.getsizeof(dcs[0])} 字节")
    print(f"  namedtuple: {sys.getsizeof(nts[0])} 字节")
    print(f"  普通类:     {sys.getsizeof(ncs[0])} 字节")

    print()


# ============================================================
# 5. 功能丰富度对比
# ============================================================

@dataclass
class FeatureRich:
    """dataclass 高级功能演示"""
    name: str
    items: List[str] = field(default_factory=list)
    #              ^^^^^^^^^^^^^^^^^^^^^^^ 可变类型默认值
    _secret: str = field(default="", repr=False)
    #            ^^^^^^^^^^^^^^^^^^^^^^ 隐藏字段
    id: str = field(compare=False, default="")
    #                 ^^^^^^^^^^^^^ 排除比较字段

    def __post_init__(self) -> None:
        """初始化后处理"""
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("名称不能为空")

    def add_item(self, item: str) -> None:
        self.items.append(item)


# namedtuple 也能添加方法，但很有限
class AdvancedNamedTuple(NamedTuple):
    """namedtuple 扩展——通过继承添加方法"""
    name: str
    items: tuple = ()  # namedtuple 不可变，只能用元组

    def add_item(self, item: str) -> "AdvancedNamedTuple":
        # 不可变对象只能返回新实例
        return self._replace(items=self.items + (item,))

    def item_count(self) -> int:
        return len(self.items)


def demo_feature_comparison() -> None:
    """对比功能丰富度"""
    print("=" * 60)
    print("5. 功能丰富度对比")
    print("=" * 60)

    # dataclass：可变，支持 field()，__post_init__
    dc = FeatureRich("数据包", _secret="hidden")
    dc.add_item("日志条目1")
    dc.add_item("日志条目2")
    print(f"dataclass: {dc}")  # repr 隐藏了 _secret
    print(f"  items: {dc.items}")

    # namedtuple：不可变，修改需要创建新对象
    nt = AdvancedNamedTuple("数据包")
    nt2 = nt.add_item("日志条目1")
    nt3 = nt2.add_item("日志条目2")
    print(f"\nnamedtuple:           {nt}")    # 原对象不变
    print(f"  add_item 后:         {nt3}")
    print(f"  item_count: {nt3.item_count()}")

    # dataclass 支持默认工厂、metadata 等：
    print(f"\ndataclass fields 数量: {len(fields(FeatureRich))}")

    # namedtuple 的不变性使它可哈希
    print(f"\nnamedtuple 可哈希: {hasattr(nt, '__hash__') and nt.__hash__ is not None}")
    print(f"dataclass 可哈希: {hasattr(dc, '__hash__') and dc.__hash__ is not None}")  # False（默认）

    print()


# ============================================================
# 6. 继承对比
# ============================================================

@dataclass
class Shape:
    """基类"""
    name: str

    def area(self) -> float:
        return 0.0


@dataclass
class Circle(Shape):
    """dataclass 继承——简洁"""
    radius: float

    def area(self) -> float:
        return 3.14159 * self.radius ** 2


@dataclass
class ColoredCircle(Circle):
    """多层继承"""
    color: str = "red"



class CircleNT(NamedTuple):
    """圆——NamedTuple 可以直接定义方法"""
    name: str
    radius: float

    def area(self) -> float:
        return 3.14159 * self.radius ** 2


def demo_inheritance() -> None:
    """对比继承能力"""
    print("=" * 60)
    print("6. 继承对比")
    print("=" * 60)

    # dataclass 继承
    c = ColoredCircle("小红圆", 5.0, "red")
    print(f"dataclass 继承: {c}")
    print(f"  area: {c.area():.2f}")
    print(f"  多层继承: ColoredCircle → Circle → Shape")

    # NamedTuple 也可以定义方法和计算属性
    cn = CircleNT("大蓝圆", 10.0)
    print(f"\nnamedtuple 方法: {cn}")
    print(f"  area: {cn.area():.2f}")
    # ⚠️ NamedTuple 子类添加字段需要 Python 3.6+ 的 typing.NamedTuple
    # 但不支持多层继承添加字段，这是 dataclass 的优势

    print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    demo_creation_comparison()
    demo_mutability()
    demo_access()
    demo_performance()
    demo_feature_comparison()
    demo_inheritance()

    print("=" * 60)
    print("🎉 三种方式对比演示完成！")
    print("=" * 60)
    print()
    print("📌 总结建议：")
    print("   ✅ 日常首选 dataclass — 功能/简洁的最佳平衡")
    print("   ✅ 不可变 + 性能敏感 → NamedTuple")
    print("   ✅ 简单元组兼容 + 拆包 → namedtuple")
    print("   ✅ 复杂业务逻辑 → 手写 class")
