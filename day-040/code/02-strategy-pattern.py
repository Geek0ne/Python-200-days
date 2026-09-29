#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略模式（Strategy Pattern）进阶用法

定义一系列算法，将每个算法封装起来，使它们可以相互替换。
策略模式让算法的变化独立于使用算法的客户。

本示例展示：
1. 支付策略系统（多种支付方式）
2. 排序策略（不同排序算法）
3. 高阶函数替代策略类（Pythonic 方式）
4. 策略 + 工厂模式结合

运行：python3 02-strategy-pattern.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Protocol
import random
import string


# ============================================================
# 第1部分：经典 OOP 实现 —— 支付策略
# ============================================================

class PaymentStrategy(ABC):
    """支付策略抽象基类"""

    @abstractmethod
    def pay(self, amount: float) -> bool:
        """支付指定金额，返回是否成功"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass


class CreditCardPayment(PaymentStrategy):
    """信用卡支付策略"""

    def __init__(self, card_number: str, cvv: str):
        self._card_number = card_number
        self._cvv = cvv
        # 模拟余额
        self._balance = 10000.0

    @property
    def name(self) -> str:
        return f"信用卡(尾号{self._card_number[-4:]})"

    def pay(self, amount: float) -> bool:
        if amount <= 0:
            print(f"  ❌ {self.name}：无效金额 {amount}")
            return False
        if amount > self._balance:
            print(f"  ❌ {self.name}：余额不足（余额：{self._balance}，需支付：{amount}）")
            return False

        self._balance -= amount
        print(f"  ✅ {self.name}：支付 ¥{amount:.2f} 成功，剩余额度 ¥{self._balance:.2f}")
        return True


class WeChatPayment(PaymentStrategy):
    """微信支付策略"""

    def __init__(self, phone: str):
        self._phone = phone
        self._balance = 5000.0

    @property
    def name(self) -> str:
        return f"微信支付({self._phone[:3]}****{self._phone[-4:]})"

    def pay(self, amount: float) -> bool:
        if amount <= 0:
            print(f"  ❌ {self.name}：无效金额")
            return False
        if amount > self._balance:
            print(f"  ❌ {self.name}：零钱余额不足")
            return False

        self._balance -= amount
        print(f"  ✅ {self.name}：支付 ¥{amount:.2f} 成功（零钱余额 ¥{self._balance:.2f}）")
        return True


class AliPayPayment(PaymentStrategy):
    """支付宝支付策略"""

    def __init__(self, account: str):
        self._account = account
        self._credit_limit = 20000.0  # 花呗额度

    @property
    def name(self) -> str:
        return f"支付宝({self._account[:3]}****{self._account[-4:]})"

    def pay(self, amount: float) -> bool:
        if amount <= 0:
            print(f"  ❌ {self.name}：无效金额")
            return False
        if amount > self._credit_limit:
            print(f"  ❌ {self.name}：花呗额度不足（额度：{self._credit_limit}）")
            return False

        self._credit_limit -= amount
        print(f"  ✅ {self.name}：支付 ¥{amount:.2f} 成功（花呗剩余额度 ¥{self._credit_limit:.2f}）")
        return True


class BitcoinPayment(PaymentStrategy):
    """比特币支付策略（策略模式新增策略无需修改 Context）"""

    # 模拟比特币对人民币汇率（简化）
    BTC_CNY_RATE = 450000.0

    def __init__(self, wallet_address: str):
        self._address = wallet_address
        self._btc_balance = 0.5  # 比特币余额

    @property
    def name(self) -> str:
        return f"比特币({self._address[:8]}...)"

    def pay(self, amount: float) -> bool:
        btc_amount = amount / self.BTC_CNY_RATE
        if btc_amount > self._btc_balance:
            print(f"  ❌ {self.name}：BTC 不足（需要 {btc_amount:.8f} BTC，"
                  f"余额 {self._btc_balance} BTC）")
            return False

        self._btc_balance -= btc_amount
        print(f"  ✅ {self.name}：支付 {btc_amount:.8f} BTC "
              f"(¥{amount:.2f}) 成功")
        return True


# ============================================================
# 第2部分：上下文 —— 订单系统
# ============================================================

@dataclass
class OrderItem:
    """订单项"""
    name: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


class Order:
    """订单（上下文 Context）"""

    def __init__(self, order_id: str, customer: str):
        self.order_id = order_id
        self.customer = customer
        self.items: List[OrderItem] = []
        self.payment_strategy: Optional[PaymentStrategy] = None
        self._paid = False

    def add_item(self, name: str, quantity: int, unit_price: float) -> None:
        """添加商品"""
        self.items.append(OrderItem(name, quantity, unit_price))

    @property
    def total_amount(self) -> float:
        """计算订单总金额"""
        return sum(item.subtotal for item in self.items)

    def set_payment_strategy(self, strategy: PaymentStrategy) -> None:
        """设置支付策略（运行时替换算法）"""
        self.payment_strategy = strategy
        print(f"  选择支付方式：{strategy.name}")

    def checkout(self) -> bool:
        """
        执行结账（委托给支付策略）。

        这是策略模式的核心——Context 将算法执行委托给 Strategy 对象。
        """
        if not self.payment_strategy:
            print("  ❌ 未设置支付方式，无法结账")
            return False

        if self._paid:
            print("  ⚠️  订单已支付，请勿重复操作")
            return False

        print(f"\n  📋 订单 {self.order_id} 明细：")
        for item in self.items:
            print(f"     {item.name} x {item.quantity} = ¥{item.subtotal:.2f}")
        print(f"  ─────────────────────────")
        print(f"  总计：¥{self.total_amount:.2f}")
        print(f"  支付方式：{self.payment_strategy.name}")

        # 委托给策略执行支付
        success = self.payment_strategy.pay(self.total_amount)

        if success:
            self._paid = True
            print(f"  🎉 订单 {self.order_id} 支付完成！")
        else:
            print(f"  💔 订单 {self.order_id} 支付失败")

        return success


# ============================================================
# 第3部分：Pythonic 方案 —— 函数式策略
# ============================================================

# Python 中函数是一等公民，可以直接用函数替代策略类
# 这种方式更轻量，适合简单策略


def quick_sort_strategy(data: List[int]) -> List[int]:
    """策略：快速排序（O(n log n)，适合乱序数据）"""
    print("  策略：快速排序 - 适合大数据量随机分布")
    if len(data) <= 1:
        return data
    pivot = data[len(data) // 2]
    left = [x for x in data if x < pivot]
    middle = [x for x in data if x == pivot]
    right = [x for x in data if x > pivot]
    return quick_sort_strategy(left) + middle + quick_sort_strategy(right)


def bubble_sort_strategy(data: List[int]) -> List[int]:
    """策略：冒泡排序（O(n²)，适合几乎有序的小数据）"""
    print("  策略：冒泡排序 - 适合小规模或基本有序数据")
    arr = data.copy()
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def python_sort_strategy(data: List[int]) -> List[int]:
    """策略：Python 内置排序（Timsort，O(n log n)）"""
    print("  策略：Python 内置排序 (Timsort) - 混合排序，通用最优")
    return sorted(data)


class Sorter:
    """
    排序器上下文

    支持通过 Callable（Function as Strategy）动态切换排序算法。
    """

    def __init__(self, strategy: Callable[[List[int]], List[int]] = python_sort_strategy):
        self._strategy = strategy

    def set_strategy(self, strategy: Callable[[List[int]], List[int]]) -> None:
        """运行时切换排序策略"""
        self._strategy = strategy

    def sort(self, data: List[int]) -> List[int]:
        """执行排序"""
        print(f"\n  输入数据：{data}")
        result = self._strategy(data)
        print(f"  排序结果：{result}")
        return result


# ============================================================
# 第4部分：策略 + 简单工厂 结合
# ============================================================

class PaymentStrategyFactory:
    """
    支付策略工厂

    结合简单工厂与策略模式：由工厂负责创建策略对象，
    客户端只需传递策略类型标识符。
    """

    @staticmethod
    def create(strategy_type: str, **kwargs) -> Optional[PaymentStrategy]:
        """根据类型创建支付策略"""
        factories = {
            "credit": lambda: CreditCardPayment(
                kwargs.get("card_number", "6222-0000-0000-0000"),
                kwargs.get("cvv", "123"),
            ),
            "wechat": lambda: WeChatPayment(
                kwargs.get("phone", "13800138000"),
            ),
            "alipay": lambda: AliPayPayment(
                kwargs.get("account", "user@alipay.com"),
            ),
            "bitcoin": lambda: BitcoinPayment(
                kwargs.get("wallet", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"),
            ),
        }

        creator = factories.get(strategy_type)
        if creator is None:
            print(f"  未知支付策略类型：{strategy_type}")
            return None

        return creator()


# ============================================================
# 第5部分：主程序
# ============================================================

def demo_payment_strategy():
    """演示支付策略系统"""
    print("\n" + "=" * 55)
    print("  🏪 策略模式演示 1：订单支付系统")
    print("=" * 55)

    # 创建订单
    order = Order("ORD-2026-0001", "张三")

    # 添加商品
    order.add_item("Python 编程入门", 2, 59.0)
    order.add_item("算法导论", 1, 128.0)
    order.add_item("机械键盘", 1, 399.0)

    print(f"\n📋 订单信息：")
    print(f"  订单号：{order.order_id}")
    print(f"  客户：{order.customer}")

    # ── 场景1：使用信用卡支付 ──
    print(f"\n{'─'*50}")
    print("  🔄 场景1：使用信用卡支付")
    print(f"{'─'*50}")
    card = CreditCardPayment("6222-1234-5678-9012", "123")
    order.set_payment_strategy(card)
    order.checkout()

    # ── 场景2：新订单，切换微信支付 ──
    print(f"\n{'─'*50}")
    print("  🔄 场景2：新订单，切换为微信支付")
    print(f"{'─'*50}")
    order2 = Order("ORD-2026-0002", "李四")
    order2.add_item("显示器 4K", 1, 2499.0)
    wechat = WeChatPayment("13912345678")
    order2.set_payment_strategy(wechat)
    order2.checkout()

    # ── 场景3：使用比特币支付 ──
    print(f"\n{'─'*50}")
    print("  🔄 场景3：使用比特币支付（新增策略，无需修改 Order）")
    print(f"{'─'*50}")
    order3 = Order("ORD-2026-0003", "王五")
    order3.add_item("限量版手办", 1, 12999.0)
    btc = BitcoinPayment("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq")
    order3.set_payment_strategy(btc)
    order3.checkout()

    # ── 场景4：策略 + 工厂 ──
    print(f"\n{'─'*50}")
    print("  🔄 场景4：使用策略工厂创建支付方式")
    print(f"{'─'*50}")
    order4 = Order("ORD-2026-0004", "赵六")
    order4.add_item("耳机", 1, 699.0)

    strategy = PaymentStrategyFactory.create("alipay", account="zhaoliu@alipay.com")
    if strategy:
        order4.set_payment_strategy(strategy)
        order4.checkout()


def demo_sort_strategy():
    """演示函数式策略"""
    print("\n" + "=" * 55)
    print("  🔢 策略模式演示 2：排序策略（函数式）")
    print("=" * 55)

    sorter = Sorter()

    # 准备数据
    data = [64, 34, 25, 12, 22, 11, 90]

    # 使用不同的排序策略
    print(f"\n📋 使用 Python 内置排序")
    sorter.sort(data)

    print(f"\n📋 切换为冒泡排序")
    sorter.set_strategy(bubble_sort_strategy)
    sorter.sort(data)

    print(f"\n📋 切换为快速排序")
    sorter.set_strategy(quick_sort_strategy)
    sorter.sort(data)


def main():
    print("=" * 55)
    print("  策略模式完整演示")
    print("=" * 55)

    demo_payment_strategy()
    demo_sort_strategy()

    print(f"\n{'='*55}")
    print("  ✅ 策略模式演示结束")
    print(f"  💡 关键点：算法封装、运行时替换、开闭原则")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
