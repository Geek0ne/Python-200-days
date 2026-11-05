"""
Day 100 - 知识体系梳理：设计模式综合示例 2
展示 OOP 三大特性 + 设计模式在实际场景中的应用
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


# ============================================================
# 概念 1: 抽象基类 + 多态 + 继承（Day 33, 34, 49）
# ============================================================

class PaymentMethod(ABC):
    """支付方式基类 - 抽象基类定义接口"""
    
    @abstractmethod
    def pay(self, amount: float) -> bool:
        """支付抽象方法"""
        pass
    
    @abstractmethod
    def refund(self, amount: float) -> bool:
        """退款抽象方法"""
        pass
    
    def process(self, amount: float, action: str = "pay") -> bool:
        """模板方法 - 固定流程"""
        print(f"  📋 处理{action}: ¥{amount:.2f}")
        
        if action == "pay":
            success = self.pay(amount)
        elif action == "refund":
            success = self.refund(amount)
        else:
            print(f"  ❌ 未知操作: {action}")
            return False
        
        if success:
            print(f"  ✅ {action}成功")
        else:
            print(f"  ❌ {action}失败")
        
        return success


# 多态：不同支付方式的实现
class CreditCard(PaymentMethod):
    """信用卡支付"""
    
    def __init__(self, card_number: str):
        self.card_number = card_number
        self.balance = 10000.0
    
    def pay(self, amount: float) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            print(f"  💳 信用卡 {self.card_number[-4:]} 扣款 ¥{amount:.2f}")
            return True
        return False
    
    def refund(self, amount: float) -> bool:
        self.balance += amount
        print(f"  💳 信用卡 {self.card_number[-4:]} 退款 ¥{amount:.2f}")
        return True


class Alipay(PaymentMethod):
    """支付宝支付"""
    
    def __init__(self, account: str):
        self.account = account
        self.balance = 5000.0
    
    def pay(self, amount: float) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            print(f"  📱 支付宝 {self.account} 扣款 ¥{amount:.2f}")
            return True
        return False
    
    def refund(self, amount: float) -> bool:
        self.balance += amount
        print(f"  📱 支付宝 {self.account} 退款 ¥{amount:.2f}")
        return True


# ============================================================
# 概念 2: 工厂模式 + 单例模式（Day 38）
# ============================================================

class PaymentFactory:
    """支付工厂 - 根据类型创建支付对象"""
    
    _registry: Dict[str, type] = {
        "credit": CreditCard,
        "alipay": Alipay,
    }
    
    @classmethod
    def create(cls, method_type: str, **kwargs) -> PaymentMethod:
        """工厂方法"""
        if method_type not in cls._registry:
            raise ValueError(f"未知支付方式: {method_type}")
        
        payment_class = cls._registry[method_type]
        return payment_class(**kwargs)
    
    @classmethod
    def register(cls, name: str, payment_class: type):
        """注册新的支付方式"""
        cls._registry[name] = payment_class


class OrderManager:
    """订单管理器 - 单例模式"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.orders = []
        return cls._instance
    
    def create_order(self, payment: PaymentMethod, amount: float, description: str) -> bool:
        """创建订单并支付"""
        print(f"\n🛒 创建订单: {description} (¥{amount:.2f})")
        
        success = payment.process(amount, "pay")
        if success:
            self.orders.append({
                "description": description,
                "amount": amount,
                "time": time.time(),
            })
        return success


# ============================================================
# 概念 3: 观察者模式 + 装饰器（Day 39, 23）
# ============================================================

class EventSystem:
    """事件系统 - 观察者模式"""
    
    def __init__(self):
        self._listeners: Dict[str, List[callable]] = {}
    
    def on(self, event: str, callback: callable):
        """注册事件监听器"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
        print(f"  📡 注册监听器: {event} → {callback.__name__}")
    
    def emit(self, event: str, *args, **kwargs):
        """触发事件"""
        if event in self._listeners:
            print(f"\n  🎯 触发事件: {event}")
            for listener in self._listeners[event]:
                listener(*args, **kwargs)


# 用装饰器记录事件日志
def log_event(func):
    """事件日志装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"  📝 记录事件: {func.__name__}")
        return func(*args, **kwargs)
    return wrapper


# ============================================================
# 综合实战：电商订单系统
# ============================================================

import functools

def timer(func):
    """计时装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  ⏱ {func.__name__} 耗时: {elapsed:.4f}s")
        return result
    return wrapper


@timer
def run_ecommerce_demo():
    """
    综合演示：电商订单系统
    融合了：
    - 抽象基类 + 多态 (Day 33, 34, 49)
    - 工厂模式 (Day 38)
    - 观察者模式 (Day 39)
    - 装饰器 (Day 23)
    - 单例模式 (Day 38)
    - 枚举 (Day 44)
    - dataclass (Day 43)
    """
    
    print("=" * 60)
    print("🎓 Day 100 - 电商订单系统综合示例")
    print("=" * 60)
    
    # 1. 创建事件系统
    event_system = EventSystem()
    
    def on_order_created(order_info):
        print(f"    📧 发送订单确认邮件: {order_info['description']}")
    
    def on_order_created_log(order_info):
        print(f"    📝 记录订单日志: {order_info['description']}")
    
    event_system.on("order_created", on_order_created)
    event_system.on("order_created", on_order_created_log)
    
    # 2. 创建订单管理器（单例）
    manager = OrderManager()
    
    # 3. 使用工厂创建支付方式
    credit_card = PaymentFactory.create("credit", card_number="4111111111111234")
    alipay = PaymentFactory.create("alipay", account="user@example.com")
    
    # 4. 模拟订单流程
    orders = [
        ("Python 书籍", 99.0),
        ("机械键盘", 599.0),
        ("显示器支架", 199.0),
    ]
    
    for i, (desc, amount) in enumerate(orders):
        payment = credit_card if i % 2 == 0 else alipay
        success = manager.create_order(payment, amount, desc)
        
        if success:
            event_system.emit("order_created", {"description": desc, "amount": amount})
    
    # 5. 查看所有订单
    print("\n" + "=" * 60)
    print("📊 订单汇总")
    print("=" * 60)
    print(f"  总订单数: {len(manager.orders)}")
    total = sum(o['amount'] for o in manager.orders)
    print(f"  总金额: ¥{total:.2f}")
    
    # 6. 展示多态的威力
    print("\n📌 多态演示：相同接口，不同实现")
    methods = [credit_card, alipay]
    for method in methods:
        print(f"\n  {type(method).__name__}:")
        method.process(50, "pay")
        method.process(50, "refund")


if __name__ == "__main__":
    run_ecommerce_demo()
