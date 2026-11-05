#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实战：完整的事件系统（Event System）

综合运用观察者模式、策略模式和命令模式构建一个可生产化的事件系统。

模式运用：
  1. 观察者模式 ─ 事件的发布与订阅（EventBus + EventHandler）
  2. 策略模式   ─ 不同的事件处理策略（同步、异步、优先级）
  3. 命令模式   ─ 事件被封装为命令对象（支持撤销、日志记录）

运行：python3 03-event-system.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum, auto
import time
import uuid
import json
from collections import defaultdict


# ============================================================
# 第1部分：核心类型定义
# ============================================================

class EventPriority(Enum):
    """事件优先级（策略模式：处理策略的一种维度）"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """
    事件对象。

    命令模式的关键——将"发生了什么"封装为对象。
    """
    event_type: str                          # 事件类型
    data: Dict[str, Any] = field(default_factory=dict)  # 事件数据
    source: str = "system"                   # 事件来源
    priority: EventPriority = EventPriority.NORMAL  # 优先级
    timestamp: float = field(default_factory=time.time)  # 发生时间
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])  # 唯一ID
    _cancelled: bool = False                 # 是否取消（支持撤销）

    def cancel(self) -> None:
        """取消事件（命令模式：undo 支持）"""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def to_dict(self) -> dict:
        """序列化为字典（支持事件日志持久化）"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "data": self.data,
            "source": self.source,
            "priority": self.priority.name,
            "timestamp": self.timestamp,
        }


# ============================================================
# 第2部分：事件处理接口（观察者模式 + 策略模式）
# ============================================================

class EventHandler(ABC):
    """
    事件处理器抽象基类。

    双重身份：
    - 观察者模式中的 Observer
    - 策略模式中的 Strategy（不同的处理策略）
    """

    @abstractmethod
    def handle(self, event: Event) -> None:
        """处理事件"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """处理器名称"""
        pass


# ============================================================
# 第3部分：具体事件处理器（Concrete Observers / Strategies）
# ============================================================

class LoggingHandler(EventHandler):
    """日志记录处理器 —— 记录所有事件到日志"""

    def __init__(self, log_file: Optional[str] = None):
        self._log_file = log_file
        self._logs: List[str] = []

    @property
    def name(self) -> str:
        return "日志记录器"

    def handle(self, event: Event) -> None:
        if event.is_cancelled:
            return

        log_entry = (
            f"[{time.strftime('%H:%M:%S', time.localtime(event.timestamp))}] "
            f"{event.event_type} | 来源={event.source} | "
            f"优先级={event.priority.name} | ID={event.event_id}"
        )
        self._logs.append(log_entry)
        print(f"  📝 [{self.name}] {log_entry}")

        if self._log_file:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


class EmailNotifier(EventHandler):
    """邮件通知处理器 —— 对特定事件发送邮件"""

    def __init__(self, admin_email: str = "admin@example.com"):
        self._admin_email = admin_email

    @property
    def name(self) -> str:
        return f"邮件通知器({self._admin_email})"

    def handle(self, event: Event) -> None:
        if event.is_cancelled:
            return

        # 只处理关键事件
        if event.priority in (EventPriority.HIGH, EventPriority.CRITICAL):
            print(f"  📧 [{self.name}]")
            print(f"     收件人：{self._admin_email}")
            print(f"     标题：{event.event_type} - {event.data.get('title', '无标题')}")
            print(f"     内容：{event.data.get('message', '无消息')}")
        else:
            # 低优先级事件忽略，不浪费邮件发送
            pass


class DataProcessor(EventHandler):
    """数据处理器 —— 处理数据变更事件（支持撤销）"""

    def __init__(self):
        self._processed: Dict[str, Any] = {}
        self._history: List[Dict] = []  # 命令模式：操作历史

    @property
    def name(self) -> str:
        return "数据处理器"

    def handle(self, event: Event) -> None:
        if event.is_cancelled:
            return

        if event.event_type == "data.create":
            key = event.data.get("key")
            value = event.data.get("value")
            if key:
                old_value = self._processed.get(key)
                self._processed[key] = value
                # 记录历史以便撤销（命令模式）
                self._history.append({
                    "event_id": event.event_id,
                    "type": "create",
                    "key": key,
                    "old_value": old_value,
                    "new_value": value,
                })
                print(f"  💾 [{self.name}] 创建/更新: {key} = {value}")
                print(f"     当前数据：{self._processed}")

        elif event.event_type == "data.delete":
            key = event.data.get("key")
            if key and key in self._processed:
                old_value = self._processed.pop(key)
                self._history.append({
                    "event_id": event.event_id,
                    "type": "delete",
                    "key": key,
                    "old_value": old_value,
                })
                print(f"  🗑️  [{self.name}] 删除: {key} (原值={old_value})")

    def undo(self, event_id: str) -> bool:
        """撤销指定事件（命令模式：undo 支持）"""
        for entry in reversed(self._history):
            if entry["event_id"] == event_id:
                if entry["type"] == "create":
                    if entry["old_value"] is None:
                        del self._processed[entry["key"]]
                    else:
                        self._processed[entry["key"]] = entry["old_value"]
                elif entry["type"] == "delete":
                    self._processed[entry["key"]] = entry["old_value"]
                print(f"  ↩️  [{self.name}] 撤销事件 {event_id}")
                print(f"     当前数据：{self._processed}")
                return True
        return False


class AlertHandler(EventHandler):
    """警报处理器 —— 对关键事件发出警报"""

    @property
    def name(self) -> str:
        return "警报系统"

    def handle(self, event: Event) -> None:
        if event.is_cancelled:
            return

        if event.priority == EventPriority.CRITICAL:
            print(f"  🚨 [{self.name}] ⚠️⚠️⚠️ 严重警报 ⚠️⚠️⚠️")
            print(f"     事件：{event.event_type}")
            print(f"     详情：{event.data.get('message', '无')}")
        elif event.priority == EventPriority.HIGH:
            print(f"  ⚠️  [{self.name}] 高优先级事件：{event.event_type}")
            print(f"     请尽快处理：{event.data.get('message', '无')}")


# ============================================================
# 第4部分：事件总线（EventBus）—— 观察者模式核心
# ============================================================

class EventBus:
    """
    事件总线 —— 观察者模式的核心实现。

    职责：
    1. 维护事件类型 → 处理器的映射关系
    2. 事件发布时，通知所有订阅该事件的处理器
    3. 支持同步/异步处理策略
    """

    def __init__(self, name: str = "default"):
        self._name = name
        # 核心数据结构：event_type → Set[EventHandler]
        self._handlers: Dict[str, Set[EventHandler]] = defaultdict(set)
        # 事件历史（命令模式：支持撤销和重放）
        self._event_history: List[Event] = []
        # 已取消事件（命令模式：undo 集合）
        self._cancelled_events: Set[str] = set()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """订阅事件（观察者模式：注册观察者）"""
        self._handlers[event_type].add(handler)
        print(f"  🔗 [{self._name}] {handler.name} 订阅了 '{event_type}'")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """取消订阅（观察者模式：移除观察者）"""
        if handler in self._handlers.get(event_type, set()):
            self._handlers[event_type].remove(handler)
            print(f"  🔓 [{self._name}] {handler.name} 取消订阅 '{event_type}'")

    def publish(self, event: Event) -> None:
        """
        发布事件（观察者模式：通知所有观察者）。

        这也是命令模式的核心 —— 事件被封装为 Event 对象，
        可以排队、记录、撤销。
        """
        if event.is_cancelled:
            print(f"  ⛔ 事件 {event.event_id} 已被取消，跳过处理")
            return

        # 记录事件到历史（命令模式：支持撤销和重放）
        self._event_history.append(event)
        print(f"\n  📢 [{self._name}] 发布事件: {event.event_type}")
        print(f"     ID={event.event_id} | 优先级={event.priority.name}")

        # 获取该事件类型的处理器
        handlers = self._handlers.get(event.event_type, set())
        # 也获取通配符处理器（订阅 "*" 的处理所有事件）
        wildcard_handlers = self._handlers.get("*", set())
        all_handlers = handlers | wildcard_handlers

        if not all_handlers:
            print(f"  ⚠️  没有处理器订阅 '{event.event_type}'")
            return

        # 通知所有处理器（观察者模式核心：遍历通知）
        for handler in all_handlers:
            handler.handle(event)

    def publish_many(self, events: List[Event]) -> None:
        """批量发布事件"""
        for event in events:
            self.publish(event)

    def cancel_event(self, event_id: str) -> bool:
        """取消事件（命令模式：undo 支持）"""
        for event in self._event_history:
            if event.event_id == event_id:
                event.cancel()
                self._cancelled_events.add(event_id)
                print(f"  ↩️  已取消事件 {event_id}")
                return True
        return False

    def replay_events(self) -> None:
        """重放所有事件（命令模式：redo / 恢复支持）"""
        print(f"\n  🔄 重放 {len(self._event_history)} 个事件...")
        for event in self._event_history:
            # 取消的事件跳过
            if event.event_id in self._cancelled_events:
                continue
            # 重新发布（注意：这可能产生重复操作，实际系统需要幂等设计）
            self.publish(event)

    def get_event_history(self) -> List[dict]:
        """获取事件历史（可序列化用于持久化）"""
        return [e.to_dict() for e in self._event_history]


# ============================================================
# 第5部分：辅助策略 —— 事件处理策略
# ============================================================

class ProcessingStrategy(ABC):
    """事件处理策略抽象（策略模式）"""

    @abstractmethod
    def process(self, bus: EventBus, event: Event) -> None:
        """处理事件"""
        pass


class SyncProcessing(ProcessingStrategy):
    """同步处理策略 —— 立即同步处理"""

    def process(self, bus: EventBus, event: Event) -> None:
        print(f"  ⏱️  处理策略：同步处理（立即执行）")
        bus.publish(event)


class PriorityProcessing(ProcessingStrategy):
    """优先级处理策略 —— 按优先级排序后处理"""

    def process(self, bus: EventBus, event: Event) -> None:
        priority_map = {
            EventPriority.CRITICAL: "立即",
            EventPriority.HIGH: "尽快",
            EventPriority.NORMAL: "正常",
            EventPriority.LOW: "稍后",
        }
        print(f"  ⏱️  处理策略：优先级队列（{priority_map[event.priority]}）")
        bus.publish(event)


# ============================================================
# 第6部分：应用程序（实战场景）
# ============================================================

class Application:
    """
    应用程序 —— 综合运用三种行为型模式。

    场景：电商网站的用户行为追踪与通知系统。
    """

    def __init__(self):
        self.event_bus = EventBus("电商系统")
        self.processing_strategy: ProcessingStrategy = SyncProcessing()

        # 创建事件处理器
        self.logger = LoggingHandler()
        self.email_notifier = EmailNotifier("ops@shop.com")
        self.data_processor = DataProcessor()
        self.alert_handler = AlertHandler()

        # 订阅事件（观察者模式）
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        """配置事件订阅"""
        # 日志记录所有事件
        self.event_bus.subscribe("*", self.logger)

        # 数据处理器关注数据变更
        self.event_bus.subscribe("data.create", self.data_processor)
        self.event_bus.subscribe("data.delete", self.data_processor)

        # 邮件通知关注用户关键行为
        self.event_bus.subscribe("user.login", self.email_notifier)
        self.event_bus.subscribe("order.paid", self.email_notifier)
        self.event_bus.subscribe("user.error", self.email_notifier)

        # 警报系统关注错误和安全事件
        self.event_bus.subscribe("system.error", self.alert_handler)
        self.event_bus.subscribe("security.alert", self.alert_handler)

    def set_processing_strategy(self, strategy: ProcessingStrategy) -> None:
        """设置处理策略（策略模式）"""
        self.processing_strategy = strategy
        print(f"\n  🔧 处理策略已切换为：{strategy.__class__.__name__}")

    def run(self) -> None:
        """运行模拟场景"""
        print("=" * 55)
        print("  🏪 电商事件系统模拟")
        print("=" * 55)

        # ── 场景1：用户登录 ──
        print(f"\n{'─'*50}")
        print("  📋 场景1：用户登录事件")
        print(f"{'─'*50}")
        self.processing_strategy.process(
            self.event_bus,
            Event(
                event_type="user.login",
                data={
                    "user_id": "u1001",
                    "username": "张三",
                    "ip": "192.168.1.100",
                    "title": "用户登录",
                    "message": "用户 张三 从 192.168.1.100 登录系统",
                },
                source="auth-service",
                priority=EventPriority.NORMAL,
            ),
        )

        # ── 场景2：创建数据 ──
        print(f"\n{'─'*50}")
        print("  📋 场景2：数据创建事件")
        print(f"{'─'*50}")
        create_event = Event(
            event_type="data.create",
            data={"key": "user_profile:u1001", "value": {"name": "张三", "level": "VIP"}},
            source="user-service",
            priority=EventPriority.NORMAL,
        )
        self.processing_strategy.process(self.event_bus, create_event)

        # ── 场景3：订单支付 ──
        print(f"\n{'─'*50}")
        print("  📋 场景3：订单支付事件（高优先级）")
        print(f"{'─'*50}")
        self.processing_strategy.process(
            self.event_bus,
            Event(
                event_type="order.paid",
                data={
                    "order_id": "ORD-2026-9999",
                    "amount": 5999.00,
                    "user_id": "u1001",
                    "title": "新订单支付成功",
                    "message": f"订单 ORD-2026-9999 已支付 ¥5999.00",
                },
                source="payment-service",
                priority=EventPriority.HIGH,
            ),
        )

        # ── 场景4：系统错误（关键事件）──
        print(f"\n{'─'*50}")
        print("  📋 场景4：严重系统错误事件（CRITICAL）")
        print(f"{'─'*50}")
        error_event = Event(
            event_type="system.error",
            data={
                "error_code": "DB_TIMEOUT",
                "message": "数据库连接超时，重试 3 次失败",
                "service": "order-service",
            },
            source="monitor",
            priority=EventPriority.CRITICAL,
        )
        self.processing_strategy.process(self.event_bus, error_event)

        # ── 场景5：切换策略 + 撤销演示 ──
        print(f"\n{'─'*50}")
        print("  📋 场景5：撤销事件 + 命令模式演示")
        print(f"{'─'*50}")

        # 保存事件 ID 用于撤销
        event_id_to_undo = create_event.event_id

        # 撤销事件（命令模式：undo）
        print(f"\n  撤销事件 {event_id_to_undo}...")
        self.event_bus.cancel_event(event_id_to_undo)

        # 数据处理器手动 undo
        self.data_processor.undo(event_id_to_undo)

        # ── 场景6：安全警报 ──
        print(f"\n{'─'*50}")
        print("  📋 场景6：安全警报")
        print(f"{'─'*50}")
        self.processing_strategy.process(
            self.event_bus,
            Event(
                event_type="security.alert",
                data={
                    "alert_type": "BRUTE_FORCE",
                    "source_ip": "203.0.113.50",
                    "attempts": 15,
                    "title": "暴力破解检测",
                    "message": "IP 203.0.113.50 在 5 分钟内进行了 15 次登录尝试",
                },
                source="security",
                priority=EventPriority.CRITICAL,
            ),
        )

        # ── 场景7：优先级策略 ──
        print(f"\n{'─'*50}")
        print("  📋 场景7：切换为优先级处理策略")
        print(f"{'─'*50}")
        self.set_processing_strategy(PriorityProcessing())
        self.processing_strategy.process(
            self.event_bus,
            Event(
                event_type="data.delete",
                data={"key": "session:u1001_old"},
                source="cleanup",
                priority=EventPriority.LOW,
            ),
        )

        # ── 最终状态 ──
        print(f"\n{'='*55}")
        print("  📊 事件系统运行统计")
        print(f"{'='*55}")
        print(f"  总共产生事件：{len(self.event_bus.get_event_history())}")
        print(f"  已取消事件：{len(self.event_bus._cancelled_events)}")
        print(f"  当前处理器：{sum(len(h) for h in self.event_bus._handlers.values())} 个")
        print(f"  事件类型：{len(self.event_bus._handlers)} 种")
        print(f"\n  事件历史记录：")
        for e in self.event_bus.get_event_history():
            cancel_mark = " [已取消]" if e["event_id"] in self.event_bus._cancelled_events else ""
            print(f"    - [{time.strftime('%H:%M:%S', time.localtime(e['timestamp']))}] "
                  f"{e['event_type']} [{e['priority']}]{cancel_mark}")

        print(f"\n{'='*55}")
        print("  ✅ 事件系统演示结束")
        print(f"  💡 综合运用：观察者模式 + 策略模式 + 命令模式")
        print(f"{'='*55}")


def main():
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
