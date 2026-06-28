"""
Day 41 - 实战：重构糟糕代码（SOLID 综合应用）

本文件演示将一个违反全部 SOLID 原则的"意大利面条"代码，
逐步重构为遵循 SOLID 原则的整洁架构。

运行方式：
    python3 days/day-041-solid-principles/code/03-code-refactoring.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json


# ============================================================
# 第一部分：原始代码 —— 违反全部 SOLID 原则
# ============================================================

print("=" * 60)
print("第一部分：原始代码（违反全部 SOLID）")
print("=" * 60)


class OrderSystem:
    """
    这个类违反了所有五个 SOLID 原则！
    
    ❌ SRP：验证、计算、存储、通知、日志都在一个类
    ❌ OCP：新增任何功能都要修改这个类
    ❌ LSP：没有抽象，无法替换实现
    ❌ ISP：客户端被迫依赖整个巨型接口
    ❌ DIP：直接依赖 print/文件/具体实现
    """

    def __init__(self):
        self._database: Dict[str, dict] = {}
        self._logs: List[str] = []
        self._tax_rate: float = 0.13

    def process_order(self, order_data: dict) -> str:
        # ---- 职责 1：验证 ----
        if not order_data:
            return "错误：订单数据为空"

        items = order_data.get("items", [])
        if not items:
            return "错误：订单中无商品"

        user_id = order_data.get("user_id")
        if not user_id:
            return "错误：缺少用户 ID"

        # ---- 职责 2：价格计算 ----
        subtotal = 0.0
        for item in items:
            price = item.get("price", 0)
            qty = item.get("qty", 0)
            subtotal += price * qty

        # 会员折扣
        user = order_data.get("user_info", {})
        if user.get("is_vip"):
            subtotal *= 0.9

        # 税费
        tax = subtotal * self._tax_rate
        total = round(subtotal + tax, 2)

        # ---- 职责 3：存储 ----
        order_id = f"ORD-{order_data.get('id', 'UNKNOWN')}"
        self._database[order_id] = {
            "order": order_data,
            "subtotal": subtotal,
            "tax": tax,
            "total": total,
        }

        # ---- 职责 4：日志 ----
        log_msg = f"[{order_id}] 已处理，金额 ¥{total}"
        self._logs.append(log_msg)

        # ---- 职责 5：通知 ----
        email = user.get("email", "unknown@example.com")
        print(f"  发送邮件到 {email}：订单 {order_id} 处理成功，总价 ¥{total}")
        print(f"  发送短信到 {user.get('phone', '无手机')}：订单已确认")

        # ---- 职责 6：返回结果 ----
        return f"订单 {order_id} 处理成功，总价 ¥{total}"

    def get_logs(self) -> List[str]:
        return self._logs

    def get_database(self) -> Dict[str, dict]:
        return self._database


# 运行原始代码
print("\n>> 运行原始代码：")
old_system = OrderSystem()
sample_order = {
    "id": "A001",
    "items": [
        {"name": "Python 编程书", "price": 79.00, "qty": 2},
        {"name": "机械键盘", "price": 599.00, "qty": 1},
    ],
    "user_id": "U001",
    "user_info": {
        "name": "张三",
        "email": "zhangsan@example.com",
        "phone": "13800138000",
        "is_vip": True,
    },
}
result = old_system.process_order(sample_order)
print(f"  结果：{result}")

print("\n  ❌ 问题：这个类同时负责验证、计算、存储、通知、日志")
print("  ❌ 修改任意一项都要动这个类")


# ============================================================
# 第二部分：重构 —— 遵循 SOLID 原则
# ============================================================

print("\n" + "=" * 60)
print("第二部分：遵循 SOLID 的重构版本")
print("=" * 60)


# --- 数据对象（SRP：只保存数据） ---

@dataclass
class OrderItem:
    name: str
    price: float
    qty: int


@dataclass
class Order:
    id: str
    items: List[OrderItem]
    user_id: str


@dataclass
class User:
    id: str
    name: str
    email: str
    phone: str = ""
    is_vip: bool = False


@dataclass
class OrderResult:
    order_id: str
    subtotal: float
    tax: float
    total: float
    message: str = ""


# --- 验证器（SRP：只负责验证逻辑） ---

class OrderValidator:
    """单一职责：只做验证"""

    def validate(self, order: Order, user: User) -> None:
        errors = []

        if not order.items:
            errors.append("订单中无商品")

        if not user.id:
            errors.append("缺少用户 ID")

        for item in order.items:
            if item.price < 0:
                errors.append(f"商品 '{item.name}' 价格为负")
            if item.qty <= 0:
                errors.append(f"商品 '{item.name}' 数量无效")

        if errors:
            raise ValueError("；".join(errors))


# --- 价格计算器（SRP + OCP：可扩展的折扣策略） ---

class DiscountPolicy(ABC):
    @abstractmethod
    def apply(self, subtotal: float, user: User) -> float:
        pass


class NoDiscount(DiscountPolicy):
    def apply(self, subtotal: float, user: User) -> float:
        return subtotal


class VIPDiscount(DiscountPolicy):
    """VIP 用户 9 折"""

    def apply(self, subtotal: float, user: User) -> float:
        return round(subtotal * 0.9, 2) if user.is_vip else subtotal


class TaxCalculator(ABC):
    @abstractmethod
    def calculate(self, amount: float) -> float:
        pass


class StandardTax(TaxCalculator):
    def __init__(self, rate: float = 0.13):
        self._rate = rate

    def calculate(self, amount: float) -> float:
        return round(amount * self._rate, 2)


class PriceCalculator:
    """
    SRP：只负责价格计算
    OCP：通过依赖注入支持不同的折扣和税率策略
    """

    def __init__(self,
                 discount: DiscountPolicy = VIPDiscount(),
                 tax: TaxCalculator = StandardTax()):
        self._discount = discount
        self._tax = tax

    def calculate(self, order: Order, user: User) -> OrderResult:
        subtotal = sum(item.price * item.qty for item in order.items)
        after_discount = self._discount.apply(subtotal, user)
        tax = self._tax.calculate(after_discount)
        total = round(after_discount + tax, 2)

        return OrderResult(
            order_id=order.id,
            subtotal=subtotal,
            tax=tax,
            total=total,
        )


# --- 仓库（SRP + DIP：依赖抽象） ---

class OrderRepository(ABC):
    """抽象接口 —— DIP"""

    @abstractmethod
    def save(self, order_id: str, result: OrderResult) -> None:
        pass

    @abstractmethod
    def find(self, order_id: str) -> Optional[OrderResult]:
        pass


class InMemoryOrderRepository(OrderRepository):
    """内存存储 —— 适合测试和演示"""

    def __init__(self):
        self._store: Dict[str, OrderResult] = {}

    def save(self, order_id: str, result: OrderResult) -> None:
        self._store[order_id] = result

    def find(self, order_id: str) -> Optional[OrderResult]:
        return self._store.get(order_id)

    def all_orders(self) -> List[OrderResult]:
        return list(self._store.values())


# --- 通知器（SRP + OCP：可扩展通知方式） ---

class Notifier(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> str:
        pass


class EmailNotifier(Notifier):
    def send(self, recipient: str, message: str) -> str:
        # 实际项目中这里是 SMTP 发送逻辑
        return f"📧 邮件已发送至 {recipient}: {message}"


class SMSNotifier(Notifier):
    def send(self, recipient: str, message: str) -> str:
        return f"📱 短信已发送至 {recipient}: {message}"


class CompositeNotifier(Notifier):
    """组合多个通知器 —— 一个通知动作触发多种通知方式"""

    def __init__(self, notifiers: List[Notifier]):
        self._notifiers = notifiers

    def send(self, recipient: str, message: str) -> str:
        results = []
        for notifier in self._notifiers:
            results.append(notifier.send(recipient, message))
        return " | ".join(results)


# --- 日志（SRP：只管日志） ---

class Logger:
    def __init__(self):
        self._entries: List[str] = []

    def log(self, message: str) -> None:
        self._entries.append(message)

    def get_entries(self) -> List[str]:
        return list(self._entries)


# --- 订单处理器（核心编排器） ---

class OrderProcessor:
    """
    核心业务编排 —— 遵循 SOLID
    
    ✅ SRP：只负责编排流程，不负责具体实现
    ✅ OCP：新增策略只需注入新实现
    ✅ LSP：所有依赖都是接口，可替换
    ✅ ISP：只依赖验证、计算、存储、通知、日志五个小接口
    ✅ DIP：所有依赖都是抽象（构造器注入）
    """

    def __init__(self,
                 validator: OrderValidator,
                 calculator: PriceCalculator,
                 repository: OrderRepository,
                 notifier: Notifier,
                 logger: Logger):
        self._validator = validator
        self._calculator = calculator
        self._repository = repository
        self._notifier = notifier
        self._logger = logger

    def process(self, order: Order, user: User) -> OrderResult:
        # 1. 验证
        self._validator.validate(order, user)

        # 2. 计算价格
        result = self._calculator.calculate(order, user)

        # 3. 存储
        self._repository.save(order.id, result)

        # 4. 日志
        log_msg = f"[{order.id}] 已处理，金额 ¥{result.total}"
        self._logger.log(log_msg)

        # 5. 通知
        notif_msg = f"订单 {order.id} 处理成功，总价 ¥{result.total}"
        self._notifier.send(user.email, notif_msg)

        result.message = f"订单 {order.id} 处理成功，总价 ¥{result.total}"
        return result

    def get_history(self, order_id: str) -> Optional[OrderResult]:
        return self._repository.find(order_id)


# --- 测试重构后的代码 ---

print("\n>> 运行重构后的代码：")

# 准备数据
order_items = [
    OrderItem("Python 编程书", 79.00, 2),
    OrderItem("机械键盘", 599.00, 1),
]
order = Order(id="A001", items=order_items, user_id="U001")
user = User(
    id="U001",
    name="张三",
    email="zhangsan@example.com",
    phone="13800138000",
    is_vip=True,
)

# 组装组件（依赖注入）
validator = OrderValidator()
calculator = PriceCalculator(discount=VIPDiscount(), tax=StandardTax(0.13))
repository = InMemoryOrderRepository()
notifier = CompositeNotifier([EmailNotifier(), SMSNotifier()])
logger = Logger()

# 创建处理器
processor = OrderProcessor(
    validator=validator,
    calculator=calculator,
    repository=repository,
    notifier=notifier,
    logger=logger,
)

# 执行
result = processor.process(order, user)
print(f"  {result.message}")

# 验证
history = processor.get_history("A001")
print(f"  历史查询: 订单 {history.order_id}, 小计 ¥{history.subtotal}, "
      f"税费 ¥{history.tax}, 总计 ¥{history.total}")
print(f"  日志: {logger.get_entries()}")
print(f"  存储记录数: {len(repository.all_orders())}")


# ============================================================
# 第三部分：扩展性演示 —— OCP 在实践中的体现
# ============================================================

print("\n" + "=" * 60)
print("第三部分：扩展演示（OCP/DIP 的威力）")
print("=" * 60)


# 需求 1：新增"新用户首单 8 折"策略
class NewUserDiscount(DiscountPolicy):
    def __init__(self, first_order_ids: set):
        self._first_order_ids = first_order_ids

    def apply(self, subtotal: float, user: User) -> float:
        # 假设新用户有自己的标识
        if user.id.startswith("NEW_"):
            return round(subtotal * 0.8, 2)
        return subtotal


print("\n>> 扩展 1：新用户首单 8 折")
new_user = User(id="NEW_001", name="李四", email="lisi@example.com", is_vip=False)
new_order = Order(id="ORD-NEW-001", items=order_items, user_id="NEW_001")

new_processor = OrderProcessor(
    validator=OrderValidator(),
    calculator=PriceCalculator(discount=NewUserDiscount(set())),
    repository=InMemoryOrderRepository(),
    notifier=CompositeNotifier([EmailNotifier()]),
    logger=Logger(),
)
new_result = new_processor.process(new_order, new_user)
print(f"  {new_result.message}")


# 需求 2：新增"零税率"
class ZeroTax(TaxCalculator):
    def calculate(self, amount: float) -> float:
        return 0.0


print("\n>> 扩展 2：零税率（C2C 交易）")
c2c_processor = OrderProcessor(
    validator=OrderValidator(),
    calculator=PriceCalculator(discount=NoDiscount(), tax=ZeroTax()),
    repository=InMemoryOrderRepository(),
    notifier=CompositeNotifier([SMSNotifier()]),
    logger=Logger(),
)
c2c_order = Order(id="ORD-C2C-001", items=[
    OrderItem("二手相机", 2000.00, 1),
], user_id="C2C_001")
c2c_user = User(id="C2C_001", name="王五", email="", phone="13900139000")
c2c_result = c2c_processor.process(c2c_order, c2c_user)
print(f"  {c2c_result.message}")
print(f"  税费: ¥{c2c_result.tax}（零税率）")


# 需求 3：新增"文件日志" —— 只需扩展 Logger
class FileLogger:
    """将日志写入文件"""

    def __init__(self, filename: str = "/tmp/order_log.txt"):
        self._filename = filename

    def log(self, message: str) -> None:
        with open(self._filename, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
        print(f"  📝 日志已写入文件: {message}")

    def get_entries(self) -> List[str]:
        with open(self._filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f]


print("\n>> 扩展 3：文件日志 + MySQL 存储")


class FileOrderRepository(OrderRepository):
    """文件存储实现 —— 不修改 OrderProcessor"""

    def __init__(self, filename: str = "/tmp/orders.json"):
        self._filename = filename
        self._orders: Dict[str, OrderResult] = {}

    def save(self, order_id: str, result: OrderResult) -> None:
        self._orders[order_id] = result
        with open(self._filename, "w", encoding="utf-8") as f:
            json.dump(
                {k: {"subtotal": v.subtotal, "tax": v.tax, "total": v.total}
                 for k, v in self._orders.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )

    def find(self, order_id: str) -> Optional[OrderResult]:
        return self._orders.get(order_id)


file_processor = OrderProcessor(
    validator=OrderValidator(),
    calculator=PriceCalculator(),
    repository=FileOrderRepository(),
    notifier=EmailNotifier(),
    logger=FileLogger(),
)
ext_order = Order(id="ORD-EXT-001", items=[
    OrderItem("显示器", 2499.00, 1),
], user_id="U002")
ext_user = User(id="U002", name="赵六", email="zhaoliu@example.com", is_vip=False)
ext_result = file_processor.process(ext_order, ext_user)
print(f"  {ext_result.message}")


# ============================================================
# 对比总结
# ============================================================

print("\n" + "=" * 60)
print("重构前后对比")
print("=" * 60)
print("""
┌──────────────────┬─────────────────────────┬─────────────────────────┐
│     原则         │    重构前                  │    重构后              │
├──────────────────┼─────────────────────────┼─────────────────────────┤
│ SRP              │ 1 个类做所有事              │ 每个类 1 个职责          │
│ OCP              │ 新功能必须改原有代码          │ 新增策略类即可           │
│ LSP              │ 无法替换任何实现              │ 所有依赖都是接口         │
│ ISP              │ 客户端须依赖巨无霸类           │ 依赖 5 个小接口          │
│ DIP              │ 直接依赖 print/字典           │ 依赖抽象接口             │
└──────────────────┴─────────────────────────┴─────────────────────────┘

核心变化：
  1. 从"一个巨无霸类"变成"多个小类编排协作"
  2. 从"硬编码具体实现"变成"依赖抽象接口"
  3. 从"修改已有代码来扩展"变成"创建新类来扩展"
  4. 每个组件都可独立测试、独立修改
""")
