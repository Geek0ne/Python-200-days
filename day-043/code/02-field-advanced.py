"""
Day 43 - 02-field-advanced.py
field() 函数与高级配置

本文件深入展示 dataclasses.field() 的完整功能，
包括：default_factory、init/repr/compare 控制、metadata、__post_init__ 等。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import uuid


# ============================================================
# 1. default_factory：可变类型的默认值
# ============================================================
# ⚠️ 核心知识点：Python 不允许可变对象作为默认参数
#    list = []  → ValueError
#    必须用 list = field(default_factory=list)

@dataclass
class ShoppingCart:
    """购物车——用 default_factory 处理可变类型"""
    user_id: int
    items: List[str] = field(default_factory=list)
    #                ^^^^^^^^^^^^^^^^^^^^^^^^
    #                每次创建实例时调用 list()，得到独立副本
    quantities: Dict[str, int] = field(default_factory=dict)
    tags: set = field(default_factory=set)

    # ⚠️ 错误写法（取消注释试试）：
    # items: List[str] = []  # ❌ ValueError: mutable default ...


def demo_default_factory() -> None:
    """演示 default_factory 的必要性"""
    print("=" * 60)
    print("1. default_factory：可变类型默认值")
    print("=" * 60)

    cart1 = ShoppingCart(user_id=1)
    cart2 = ShoppingCart(user_id=2)

    # 各自拥有独立列表
    cart1.items.append("苹果")
    cart1.items.append("香蕉")
    cart2.items.append("牛奶")

    print(f"cart1.items = {cart1.items}")  # ['苹果', '香蕉']
    print(f"cart2.items = {cart2.items}")  # ['牛奶']

    # ✅ 关键验证：两个列表是不同对象
    print(f"cart1.items is cart2.items: {cart1.items is cart2.items}")  # False
    print()


# ============================================================
# 2. init=False：计算字段（不在构造函数中出现）
# ============================================================

@dataclass
class Order:
    """订单——包含自动计算字段"""
    order_id: str = field(init=False)       # 自动生成，不传参
    product: str
    quantity: int
    unit_price: float
    total_price: float = field(init=False)  # 自动计算

    def __post_init__(self) -> None:
        """初始化后自动调用，用来做验证或计算"""
        # 自动生成订单号（UUID 的前8位）
        self.order_id = uuid.uuid4().hex[:8].upper()

        # 自动计算总价
        self.total_price = round(self.quantity * self.unit_price, 2)

        # 验证逻辑
        if self.quantity <= 0:
            raise ValueError("数量必须大于 0")
        if self.unit_price <= 0:
            raise ValueError("单价必须大于 0")


def demo_init_false() -> None:
    """演示 init=False 和 __post_init__"""
    print("=" * 60)
    print("2. init=False：计算字段")
    print("=" * 60)

    # 创建订单 — 只需要传 product, quantity, unit_price
    order = Order("笔记本电脑", 2, 4999.00)

    print(f"订单号: {order.order_id}")    # 自动生成，如 "A3F8C2B1"
    print(f"商品: {order.product}")
    print(f"数量: {order.quantity}")
    print(f"单价: ¥{order.unit_price}")
    print(f"总价: ¥{order.total_price}")  # 自动计算 9998.00

    # order_id 和 total_price 不在 __init__ 参数中
    # 如果尝试 Order(order_id="xxx", ...) → TypeError

    print()


# ============================================================
# 3. repr=False：隐藏敏感字段
# ============================================================

@dataclass
class DatabaseConfig:
    """数据库配置——隐藏密码等敏感字段"""
    host: str
    username: str
    port: int = 3306
    password: str = field(default="", repr=False)  # repr 中不显示密码
    database: str = "default"
    #        ^^^^^^^^^^^^^^^^
    #        直接给默认值（这是字符串，不可变，不需要 default_factory）


@dataclass
class ApiResponse:
    """API 响应——大字段不在 repr 中显示"""
    status: int
    message: str
    data: Dict = field(repr=False)          # 大数据体，repr 不显示
    _internal: str = field(repr=False, default="")  # 内部字段，repr 不显示


def demo_repr_false() -> None:
    """演示 repr=False 的效果"""
    print("=" * 60)
    print("3. repr=False：隐藏敏感/大数据字段")
    print("=" * 60)

    config = DatabaseConfig(
        host="db.example.com",
        port=5432,
        username="admin",
        password="super_secret_123!",
        database="production"
    )
    print(f"数据库配置: {config}")
    # ✅ 密码被隐藏：DatabaseConfig(host='db.example.com', port=5432, ...)
    # 不会输出 password='super_secret_123!'

    print()

    response = ApiResponse(
        status=200,
        message="成功",
        data={"users": [{"id": 1}, {"id": 2}] * 100}  # 大数组
    )
    print(f"API 响应: {response}")
    # 不会在 repr 中打印巨大的 data 字段
    print()


# ============================================================
# 4. compare=False：排除无关比较字段
# ============================================================

@dataclass(order=True)
class Task:
    """任务——比较时排除缓存和 id"""
    priority: int                              # 参与排序
    title: str                                 # 参与排序
    task_id: str = field(compare=False)        # 不参与比较
    #          ^^^^^^^^^^^^^^^^^^^^^^^^^^
    #          即使 order=True，task_id 不同也不影响 == 和排序
    created_at: float = field(compare=False)   # 不参与比较
    _cache: Dict = field(compare=False, repr=False, default_factory=dict)


def demo_compare_false() -> None:
    """演示 compare=False 的效果"""
    print("=" * 60)
    print("4. compare=False：排除无关比较字段")
    print("=" * 60)

    t1 = Task(priority=1, title="修复 Bug", task_id="T-001", created_at=100.0)
    t2 = Task(priority=1, title="修复 Bug", task_id="T-002", created_at=200.0)
    t3 = Task(priority=2, title="优化性能", task_id="T-003", created_at=150.0)

    # t1 和 t2 的任务 ID 和时间不同，但核心数据相同
    print(f"t1 == t2: {t1 == t2}")  # True（compare=False 排除了 task_id 和 created_at）

    # 排序只基于 priority 和 title
    tasks = [t3, t1, t2]
    sorted_tasks = sorted(tasks)
    print("按 priority, title 排序：")
    for t in sorted_tasks:
        print(f"  {t.priority} - {t.title} [{t.task_id}]")
    print()


# ============================================================
# 5. metadata：自定义元数据
# ============================================================
# metadata 是一个字典，可以存储任意用户数据。
# dataclass 自己不使用 metadata，但可以被外部工具读取。

@dataclass
class FieldDef:
    """字段定义——演示 metadata 的用法"""
    name: str
    type_name: str
    required: bool = field(
        default=True,
        metadata={"help": "该字段是否必填", "order": 1}
    )
    default_value: Optional[str] = field(
        default=None,
        metadata={"help": "默认值（可选）", "order": 2}
    )
    validation: Optional[str] = field(
        default=None,
        metadata={"help": "验证规则（正则表达式）", "order": 3}
    )


@dataclass
class UserProfile:
    """用户资料——带字段元数据和验证规则"""
    username: str = field(metadata={"min_length": 3, "max_length": 20, "pattern": r"^[a-zA-Z0-9_]+$"})
    email: str = field(metadata={"pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"})
    age: int = field(default=18, metadata={"min": 0, "max": 150})
    phone: Optional[str] = field(default=None, metadata={"pattern": r"^\d{11}$"})


def demo_metadata() -> None:
    """演示 metadata 的用法"""
    print("=" * 60)
    print("5. metadata：自定义元数据")
    print("=" * 60)

    # 遍历字段中的 metadata
    print("UserProfile 字段验证规则：")
    for f in dataclasses.fields(UserProfile):
        meta = f.metadata
        if meta:
            print(f"  {f.name}: {meta}")

    print()

    # 读取特定字段的 metadata
    email_field = [f for f in dataclasses.fields(UserProfile) if f.name == "email"][0]
    print(f"email 字段的 metadata: {email_field.metadata}")
    # {'pattern': '^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'}
    print()


# ============================================================
# 6. hash=False：精细控制哈希
# ============================================================

@dataclass(frozen=True)
class CacheKey:
    """缓存键——排除非关键字段对哈希的影响"""
    base_url: str
    endpoint: str
    # query 不同时不需要不同的缓存键——不参与 hash
    query: str = field(default="", hash=False, compare=False)

    # timestamp 不参与哈希（但可以参与比较）
    timestamp: float = field(default=0.0, hash=False, compare=False)


def demo_hash_false() -> None:
    """演示 hash=False 的用途"""
    print("=" * 60)
    print("6. hash=False：精细控制哈希")
    print("=" * 60)

    # 尽管 url、query 不同，但只要 base_url 和 endpoint 相同，就视为相同缓存键
    key1 = CacheKey("https://api.example.com", "/users", "page=1", 100.0)
    key2 = CacheKey("https://api.example.com", "/users", "page=2", 200.0)

    print(f"key1 == key2: {key1 == key2}")     # True（hash=False 排除了 query）
    print(f"hash(key1) == hash(key2): {hash(key1) == hash(key2)}")  # True

    # 可以用作字典键——去重效果
    cache = {key1: "用户列表"}
    print(f"缓存命中: {cache[key2]}")  # 两个键相等，所以能命中
    print()


# ============================================================
# 7. __post_init__ 完整示例：验证 + 转换 + 计算
# ============================================================

@dataclass
class Temperature:
    """温度——演示 __post_init__ 验证 + 自动转换"""
    celsius: float

    # 华氏度：自动计算，不在 __init__ 中
    fahrenheit: float = field(init=False)
    # 开尔文：自动计算，不在 __init__ 中
    kelvin: float = field(init=False)
    # 格式化字符串：自动生成
    display: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """初始化后的验证、转换、计算"""
        # 验证：绝对零度以下
        if self.celsius < -273.15:
            raise ValueError(f"温度不能低于绝对零度: {self.celsius}°C")

        # 转换：计算华氏度（四舍五入到2位小数）
        self.fahrenheit = round(self.celsius * 9 / 5 + 32, 2)

        # 转换：计算开尔文
        self.kelvin = round(self.celsius + 273.15, 2)

        # 计算：生成显示字符串
        self.display = f"{self.celsius}°C / {self.fahrenheit}°F / {self.kelvin}K"


def demo_post_init() -> None:
    """演示完整的 __post_init__ 用法"""
    print("=" * 60)
    print("7. __post_init__：验证 + 转换 + 计算")
    print("=" * 60)

    # 正常温度
    temp = Temperature(25.0)
    print(f"摄氏度: {temp.celsius}°C")
    print(f"华氏度: {temp.fahrenheit}°F")
    print(f"开尔文: {temp.kelvin}K")
    print(f"显示: {temp.display}")

    # 零下
    temp2 = Temperature(-10.5)
    print(f"\n零下温度: {temp2}")

    # ❌ 低于绝对零度
    try:
        Temperature(-300.0)
    except ValueError as e:
        print(f"\n验证失败: {e}")

    print()


# ============================================================
# 8. slots=True：内存优化 (Python 3.10+)
# ============================================================

# slots=True 让 dataclass 使用 __slots__，
# 每个实例减少约 8 字节的 __dict__ 开销。
# 大量对象（10万+）时效果明显。

try:
    # Python 3.10+ 才支持
    @dataclass(slots=True)
    class SmallPoint:
        x: float = 0.0
        y: float = 0.0
        z: float = 0.0

    HAS_SLOTS = True
except TypeError:
    HAS_SLOTS = False


def demo_slots() -> None:
    """演示 slots=True 的效果（Python 3.10+）"""
    print("=" * 60)
    print("8. slots=True：内存优化")
    print("=" * 60)

    if not HAS_SLOTS:
        print("⚠️ 需要 Python 3.10+ 才支持 slots=True")
        print()

        # 手动创建 __slots__ 版本的兼容写法
        @dataclass
        class SmallPoint2:
            __slots__ = ("x", "y", "z")
            x: float = 0.0
            y: float = 0.0
            z: float = 0.0

        p = SmallPoint2(1.0, 2.0, 3.0)
        print(f"手动 __slots__ 版: {p}")
        print(f"没有 __dict__ 属性: {not hasattr(p, '__dict__')}")
        print()

        return

    p = SmallPoint(1.0, 2.0, 3.0)
    print(f"slots dataclass: {p}")
    print(f"没有 __dict__: {not hasattr(p, '__dict__')}")

    # 性能对比（简单演示）
    import sys

    @dataclass()
    class NormalPoint:
        x: float = 0.0
        y: float = 0.0
        z: float = 0.0

    normal = [NormalPoint() for _ in range(10000)]
    slot = [SmallPoint() for _ in range(10000)]

    # 粗略内存对比
    normal_size = sys.getsizeof(normal[0])
    slot_size = sys.getsizeof(slot[0])
    print(f"普通实例大小: {normal_size} 字节")
    print(f"slots 实例大小: {slot_size} 字节")
    print(f"节省: {normal_size - slot_size} 字节/实例")

    print()


import dataclasses  # 给 demo_metadata 用


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    demo_default_factory()
    demo_init_false()
    demo_repr_false()
    demo_compare_false()
    demo_metadata()
    demo_hash_false()
    demo_post_init()
    demo_slots()

    print("=" * 60)
    print("🎉 field() 高级配置演示完成！")
    print("=" * 60)
