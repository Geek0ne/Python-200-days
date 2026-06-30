#!/usr/bin/env python3
"""
Day 44 — 03-state-machine.py
状态机实战：订单状态流转

本案例展示如何使用 Enum 实现一个完整的订单状态机，
确保状态只能在规定的合法路径上转换。

状态转换图：
    PENDING ──→ PROCESSING ──→ SHIPPED ──→ DELIVERED
       │              │             │
       └──→ CANCELLED←┘             │
                       └──→ CANCELLED

规则：
- PENDING → PROCESSING ✓
- PENDING → CANCELLED  ✓
- PROCESSING → SHIPPED ✓
- PROCESSING → CANCELLED ✓
- SHIPPED → DELIVERED  ✓
- SHIPPED → CANCELLED  ✗（已发货不能取消！）
- DELIVERED → ✗ 已签收不能变化
- CANCELLED  → ✗ 已取消不能变化
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Optional, Dict, Set


# ============================================================
# 1. 订单状态枚举
# ============================================================

class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = auto()       # 待处理
    PROCESSING = auto()    # 处理中
    SHIPPED = auto()       # 已发货
    DELIVERED = auto()     # 已签收
    CANCELLED = auto()     # 已取消

    def __str__(self):
        """友好的字符串表示"""
        labels = {
            OrderStatus.PENDING:    "⏳ 待处理",
            OrderStatus.PROCESSING: "🔄 处理中",
            OrderStatus.SHIPPED:    "📦 已发货",
            OrderStatus.DELIVERED:  "✅ 已签收",
            OrderStatus.CANCELLED:  "❌ 已取消",
        }
        return f"{self.name} {labels[self]}"


# ============================================================
# 2. 状态转移规则表
# ============================================================

# 定义合法转移：当前状态 → 允许的目标状态集合
TRANSITIONS: Dict[OrderStatus, Set[OrderStatus]] = {
    OrderStatus.PENDING:    {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED:    {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED:  set(),   # 终态：不可再转移
    OrderStatus.CANCELLED:  set(),   # 终态：不可再转移
}


# ============================================================
# 3. 订单类
# ============================================================

class Order:
    """具有状态机行为的订单"""

    def __init__(self, order_id: str, customer: str, items: list[str]):
        self.order_id = order_id
        self.customer = customer
        self.items = items
        self._status: OrderStatus = OrderStatus.PENDING
        self.history: list[tuple[OrderStatus, str]] = [
            (OrderStatus.PENDING, "订单创建")
        ]

    @property
    def status(self) -> OrderStatus:
        """获取当前状态（只读属性，外部不能随意修改）"""
        return self._status

    def transition(self, target: OrderStatus, reason: str = ""):
        """
        尝试从当前状态转移到目标状态。
        如果转移非法，抛出 ValueError。
        """
        current = self._status
        allowed = TRANSITIONS[current]

        if target not in allowed:
            raise ValueError(
                f"❌ 非法状态转换: {current.name} → {target.name}\n"
                f"   从 {current.name} 允许的转换: "
                f"{[s.name for s in allowed] or ['无（终态）']}"
            )

        # 执行转换
        self._status = target
        self.history.append((target, reason or f"状态变更为 {target.name}"))
        print(f"  ✅ {current} → {target}")
        if reason:
            print(f"     原因: {reason}")

    def get_transitions(self) -> list[str]:
        """获取当前状态下允许的转换"""
        return [s.name for s in TRANSITIONS[self._status]]

    def is_final(self) -> bool:
        """判断是否为终态"""
        return not bool(TRANSITIONS[self._status])

    def show_history(self):
        """显示完整的状态变更历史"""
        print(f"\n📋 订单 {self.order_id} 状态历史:")
        print("-" * 50)
        for i, (status, note) in enumerate(self.history):
            arrow = " ──→ " if i < len(self.history) - 1 else ""
            print(f"  {i+1}. {status}  {arrow}")
            if note:
                print(f"     📝 {note}")


# ============================================================
# 4. 测试：完整订单生命周期
# ============================================================

def test_normal_flow():
    """测试正常订单流程"""
    print("\n" + "=" * 60)
    print("📦 场景 1：正常订单流程（PENDING → DELIVERED）")
    print("=" * 60)

    order = Order("ORD-001", "张三", ["Python 书", "机械键盘"])

    print(f"\n订单信息:")
    print(f"  订单号: {order.order_id}")
    print(f"  客户:   {order.customer}")
    print(f"  商品:   {', '.join(order.items)}")
    print(f"  状态:   {order.status}")

    # 正常流转
    order.transition(OrderStatus.PROCESSING, "已确认库存，开始处理")
    order.transition(OrderStatus.SHIPPED, "已通过顺丰发出，单号 SF123456")
    order.transition(OrderStatus.DELIVERED, "客户已签收")

    order.show_history()
    print(f"\n终态: {order.is_final()}")


def test_cancellation():
    """测试订单取消"""
    print("\n" + "=" * 60)
    print("📦 场景 2：订单取消（PENDING → CANCELLED）")
    print("=" * 60)

    order = Order("ORD-002", "李四", ["显示器"])

    print(f"\n订单信息: {order.order_id}")
    order.transition(OrderStatus.CANCELLED, "客户主动取消")

    # 取消后不能再操作
    try:
        order.transition(OrderStatus.PROCESSING, "客服误操作")
    except ValueError as e:
        print(f"\n{e}")


def test_illegal_transition():
    """测试非法状态转换（已发货后想取消）"""
    print("\n" + "=" * 60)
    print("📦 场景 3：非法转换（已发货→取消）")
    print("=" * 60)

    order = Order("ORD-003", "王五", ["耳机"])

    order.transition(OrderStatus.PROCESSING, "开始配货")
    order.transition(OrderStatus.SHIPPED, "已发货")

    print(f"\n当前状态: {order.status}")
    print(f"允许的转换: {order.get_transitions()}")

    # 尝试取消已发货的订单 → 应该报错
    try:
        order.transition(OrderStatus.CANCELLED, "想取消但是不行")
    except ValueError as e:
        print(f"\n{e}")


def test_terminal_state():
    """测试终态行为"""
    print("\n" + "=" * 60)
    print("📦 场景 4：终态行为")
    print("=" * 60)

    # 已签收
    order1 = Order("ORD-004", "赵六", ["键盘"])
    order1.transition(OrderStatus.PROCESSING)
    order1.transition(OrderStatus.SHIPPED)
    order1.transition(OrderStatus.DELIVERED)
    print(f"\n订单 {order1.order_id} 终态: {order1.status}")
    print(f"  是终态吗? {order1.is_final()}")
    try:
        order1.transition(OrderStatus.CANCELLED)
    except ValueError as e:
        print(f"  {e}")

    # 已取消
    order2 = Order("ORD-005", "钱七", ["鼠标"])
    order2.transition(OrderStatus.CANCELLED, "不想要了")
    print(f"\n订单 {order2.order_id} 终态: {order2.status}")
    print(f"  是终态吗? {order2.is_final()}")
    try:
        order2.transition(OrderStatus.PROCESSING)
    except ValueError as e:
        print(f"  {e}")


# ============================================================
# 5. 扩展：游戏角色状态机
# ============================================================

class PlayerState(Enum):
    """游戏角色状态"""
    IDLE = auto()       # 待机
    WALKING = auto()    # 行走
    RUNNING = auto()    # 奔跑
    ATTACKING = auto()  # 攻击
    HURT = auto()       # 受伤
    DEAD = auto()       # 死亡

    def __str__(self):
        labels = {
            PlayerState.IDLE:      "🧍 待机",
            PlayerState.WALKING:   "🚶 行走",
            PlayerState.RUNNING:   "🏃 奔跑",
            PlayerState.ATTACKING: "⚔️ 攻击",
            PlayerState.HURT:      "💥 受伤",
            PlayerState.DEAD:      "💀 死亡",
        }
        return labels[self]


PLAYER_TRANSITIONS = {
    PlayerState.IDLE:      {PlayerState.WALKING, PlayerState.ATTACKING, PlayerState.DEAD},
    PlayerState.WALKING:   {PlayerState.IDLE, PlayerState.RUNNING, PlayerState.ATTACKING, PlayerState.HURT, PlayerState.DEAD},
    PlayerState.RUNNING:   {PlayerState.IDLE, PlayerState.WALKING, PlayerState.ATTACKING, PlayerState.HURT, PlayerState.DEAD},
    PlayerState.ATTACKING: {PlayerState.IDLE, PlayerState.HURT, PlayerState.DEAD},
    PlayerState.HURT:      {PlayerState.IDLE, PlayerState.WALKING, PlayerState.DEAD},
    PlayerState.DEAD:      set(),
}


class GameCharacter:
    """具有状态机的游戏角色"""

    def __init__(self, name: str, hp: int):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.state = PlayerState.IDLE
        self.history: list[PlayerState] = [PlayerState.IDLE]

    def change_state(self, target: PlayerState):
        """尝试切换状态"""
        allowed = PLAYER_TRANSITIONS[self.state]
        if target not in allowed:
            print(f"  ❌ {self.state} → {target} (非法转换!)")
            return False

        self.history.append(target)
        print(f"  ✅ {self.state} → {target}")
        self.state = target
        return True

    def take_damage(self, damage: int):
        """受到伤害"""
        self.hp = max(0, self.hp - damage)
        print(f"  💔 {self.name} 受到 {damage} 点伤害，剩余 HP: {self.hp}/{self.max_hp}")
        if self.hp <= 0:
            self.change_state(PlayerState.DEAD)
        elif self.state in (PlayerState.IDLE, PlayerState.WALKING, PlayerState.RUNNING):
            self.change_state(PlayerState.HURT)


def test_game_state_machine():
    """测试游戏角色状态机"""
    print("\n" + "=" * 60)
    print("🎮 场景 5：游戏角色状态机")
    print("=" * 60)

    hero = GameCharacter("勇者", 100)
    print(f"角色: {hero.name} (HP: {hero.hp})")

    print("\n基础移动:")
    hero.change_state(PlayerState.WALKING)
    hero.change_state(PlayerState.RUNNING)
    hero.change_state(PlayerState.IDLE)

    print("\n战斗循环:")
    hero.change_state(PlayerState.ATTACKING)
    hero.take_damage(30)

    print("\n继续游走:")
    hero.change_state(PlayerState.WALKING)
    hero.take_damage(50)

    print("\n致命一击:")
    hero.take_damage(50)  # HP 降到 0，触发死亡
    hero.change_state(PlayerState.WALKING)  # 死亡后不能行走

    print(f"\n最终状态: {hero.state}")
    print(f"最终 HP: {hero.hp}")


# ============================================================
# 6. 主程序
# ============================================================

if __name__ == "__main__":
    print("🏁 状态机实战：枚举驱动流程")
    print("=" * 60)

    test_normal_flow()
    test_cancellation()
    test_illegal_transition()
    test_terminal_state()
    test_game_state_machine()

    print("\n" + "=" * 60)
    print("🏁 所有状态机场景测试完成！")
    print("=" * 60)
