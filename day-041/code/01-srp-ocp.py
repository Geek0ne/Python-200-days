"""
Day 41 - 单一职责原则（SRP）和开闭原则（OCP）示例

本文件包含两个原则的独立演示，每个示例都可直接运行。

运行方式：
    python3 days/day-041-solid-principles/code/01-srp-ocp.py
"""

# ============================================================
# 第一部分：SRP（单一职责原则）
# ============================================================

print("=" * 60)
print("第一部分：SRP — 单一职责原则")
print("=" * 60)

# --- 违反 SRP 的反例 ---

class BadReport:
    """
    糟糕的设计 —— 一个类承担了三个职责：
    1. 数据生成（业务逻辑）
    2. 文件保存（持久化）
    3. HTML 格式化（展示）
    """

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content
        self._processed_data = None

    def process_data(self) -> str:
        """职责 1：数据处理"""
        self._processed_data = f"{self.title}: {self.content}"
        return self._processed_data

    def save_to_file(self, filename: str) -> None:
        """职责 2：文件保存"""
        data = self._processed_data or self.process_data()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"  已保存到文件: {filename}")

    def to_html(self) -> str:
        """职责 3：HTML 格式化"""
        data = self._processed_data or self.process_data()
        html = f"<h1>{self.title}</h1><p>{self.content}</p>"
        print(f"  生成 HTML: {html}")
        return html

    # 问题：如果邮件格式变了，要改这个类（展示职责变动）
    # 如果存储方式变了（比如存数据库），也要改这个类（持久化变动）
    # 如果数据处理逻辑变了，还是要改这个类（业务变动）
    # —— 三个变化原因集中在同一个类里！


# --- 遵循 SRP 的正确设计 ---

class ReportData:
    """职责 1：只保存报表数据（数据对象）"""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content


class ReportProcessor:
    """职责 2：只负责数据处理"""

    def process(self, report: ReportData) -> str:
        return f"{report.title}: {report.content}"


class ReportSaver:
    """职责 3：只负责持久化"""

    def save_to_file(self, data: str, filename: str) -> None:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"  已保存到文件: {filename}")

    def save_to_database(self, data: str) -> None:
        """未来可以扩展其他存储方式，不影响其他类"""
        print(f"  已保存到数据库: {data[:50]}...")


class ReportFormatter:
    """职责 4：只负责格式化输出"""

    def to_html(self, title: str, content: str) -> str:
        return f"<h1>{title}</h1><p>{content}</p>"

    def to_markdown(self, title: str, content: str) -> str:
        return f"# {title}\n\n{content}"


# 测试 SRP 设计
print("\n>> SRP 正确设计演示:")
report_data = ReportData("销售报告", "Q3 营收增长 20%")
processor = ReportProcessor()
saver = ReportSaver()
formatter = ReportFormatter()

processed = processor.process(report_data)
print(f"  处理后的数据: {processed}")

html = formatter.to_html(report_data.title, report_data.content)
print(f"  生成的 HTML: {html}")

saver.save_to_file(processed, "/tmp/srp_demo.txt")
# 测试后清理
import os
os.remove("/tmp/srp_demo.txt")
print("  已清理临时文件")

print("\n  ✅ SRP 优势: 每个类只有一个变化原因, 修改互不影响")


# ============================================================
# 第二部分：OCP（开闭原则）
# ============================================================

print("\n" + "=" * 60)
print("第二部分：OCP — 开闭原则")
print("=" * 60)


# --- 违反 OCP 的反例 ---

class BadDiscountCalculator:
    """
    糟糕的设计 —— 每次新增折扣类型都要修改这个类
    
    问题：对修改是"开"放的 —— 违反 OCP
    """

    def calculate(self, price: float, customer_type: str) -> float:
        if customer_type == "normal":
            return price
        elif customer_type == "vip":
            return price * 0.9
        elif customer_type == "super_vip":
            return price * 0.8
        elif customer_type == "seasonal":
            return price * 0.85
        # 每当有新的客户类型，就要加 elif —— 这是修改已有代码
        # 额外风险：改一个 elif 可能影响其他分支
        else:
            return price


# --- 遵循 OCP 的正确设计 ---

from abc import ABC, abstractmethod


class DiscountStrategy(ABC):
    """抽象基类 —— 对扩展开放"""

    @abstractmethod
    def apply(self, price: float) -> float:
        """应用折扣，返回折扣后价格"""
        pass


class NormalDiscount(DiscountStrategy):
    """普通用户 —— 无折扣"""

    def apply(self, price: float) -> float:
        return price


class VIPDiscount(DiscountStrategy):
    """VIP 用户 —— 9 折"""

    def apply(self, price: float) -> float:
        return round(price * 0.9, 2)


class SuperVIPDiscount(DiscountStrategy):
    """超级 VIP —— 8 折"""

    def apply(self, price: float) -> float:
        return round(price * 0.8, 2)


class SeasonalDiscount(DiscountStrategy):
    """季节性折扣 —— 85 折"""

    def apply(self, price: float) -> float:
        return round(price * 0.85, 2)


class DiscountCalculator:
    """
    遵循 OCP 的折扣计算器
    
    - 新增折扣类型 → 创建新的策略类（扩展）
    - 已有代码 ✅ 不需要修改（关闭）
    """

    def __init__(self, strategy: DiscountStrategy):
        self._strategy = strategy

    def calculate(self, price: float) -> float:
        return self._strategy.apply(price)


# 测试 OCP 设计
print("\n>> OCP 正确设计演示:")

products = [
    ("笔记本电脑", 5999.00),
    ("机械键盘", 899.00),
    ("显示器", 2499.00),
]

# 定义策略映射
strategies = {
    "normal": NormalDiscount(),
    "vip": VIPDiscount(),
    "super_vip": SuperVIPDiscount(),
    "seasonal": SeasonalDiscount(),
}

for product_name, price in products:
    print(f"\n  商品: {product_name} (原价 ¥{price})")
    for customer_type, strategy in strategies.items():
        calc = DiscountCalculator(strategy)
        final_price = calc.calculate(price)
        print(f"    {customer_type:>10}: ¥{final_price:>8.2f}")


# 演示扩展：新增"员工内部价"
class EmployeeDiscount(DiscountStrategy):
    """员工内部价 —— 7 折"""
    def apply(self, price: float) -> float:
        return round(price * 0.7, 2)


print("\n>> OCP 扩展演示 — 新增员工折扣:")
employee_calc = DiscountCalculator(EmployeeDiscount())
for product_name, price in products:
    final_price = employee_calc.calculate(price)
    print(f"  {product_name}: ¥{final_price:>8.2f} (员工价)")

print("\n  ✅ OCP 优势: 新增折扣类型只需新建类, 无需修改 DiscountCalculator")
print("  ✅ 原有系统稳定, 新功能安全扩展")


# ============================================================
# 第三部分：OCP + 策略模式（进一步演示）
# ============================================================

print("\n" + "=" * 60)
print("第三部分：OCP 实战 — 支付处理系统")
print("=" * 60)


class PaymentMethod(ABC):
    """支付方式抽象"""

    @abstractmethod
    def pay(self, amount: float) -> str:
        pass


class Alipay(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"支付宝支付 ¥{amount:.2f} 成功"


class WeChatPay(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"微信支付 ¥{amount:.2f} 成功"


class CreditCard(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"信用卡支付 ¥{amount:.2f} 成功"


class PaymentProcessor:
    def __init__(self, method: PaymentMethod):
        self._method = method

    def execute(self, amount: float) -> str:
        return self._method.pay(amount)


# 测试支付系统
methods = [Alipay(), WeChatPay(), CreditCard()]
for method in methods:
    processor = PaymentProcessor(method)
    result = processor.execute(99.99)
    print(f"  {result}")

# 新增支付方式 —— 扩展，不修改
class CryptoPayment(PaymentMethod):
    def pay(self, amount: float) -> str:
        return f"加密货币支付 ¥{amount:.2f} 成功 (0.005 BTC)"

crypto_processor = PaymentProcessor(CryptoPayment())
print(f"  {crypto_processor.execute(99.99)} (新增支付方式!)")

print("\n  ✅ OCP 保证了支付系统的弹性扩展能力")


# ============================================================
# 总结
# ============================================================

print("\n" + "=" * 60)
print("总结")
print("=" * 60)
print("""
  SRP（单一职责原则）：
    - 一个类只做一件事
    - 判断标准：是否有多个"变化原因"
    - 好处：易维护、易测试、低耦合

  OCP（开闭原则）：
    - 对扩展开放，对修改关闭
    - 实现方式：抽象基类 + 多态 + 依赖注入
    - 好处：新增功能安全，不改原有逻辑
""")
