#!/usr/bin/env python3
"""
Day 087 - 代码示例 1：基础有限状态机
从零实现一个轻量状态机，理解 FSM 核心概念
"""

from enum import Enum, auto
from typing import Dict, Tuple, Callable, Optional, Any


# ═══════════════════════════════════════════
# 方式一：查表法（最简单）
# ═══════════════════════════════════════════

class SimpleFSM:
    """最简有限状态机 - 查表法实现"""

    def __init__(self, initial_state):
        self.state = initial_state
        self.transitions: Dict[Tuple, str] = {}

    def add_transition(self, from_state: str, event: str, to_state: str):
        """添加状态转移规则：(当前状态, 事件) -> 下一状态"""
        self.transitions[(from_state, event)] = to_state

    def trigger(self, event: str) -> str:
        """触发事件，返回新状态"""
        key = (self.state, event)
        if key not in self.transitions:
            raise ValueError(f"❌ 非法转移: 状态={self.state}, 事件={event}")
        old_state = self.state
        self.state = self.transitions[key]
        print(f"  [{old_state}] + {event} → [{self.state}]")
        return self.state

    def is_in(self, state: str) -> bool:
        return self.state == state


def demo_simple_fsm():
    """演示：红绿灯状态机"""
    print("=" * 50)
    print("🚦 演示：红绿灯状态机（查表法）")
    print("=" * 50)

    light = SimpleFSM("红灯")

    # 定义转移规则
    light.add_transition("红灯", "timer", "绿灯")
    light.add_transition("绿灯", "timer", "黄灯")
    light.add_transition("黄灯", "timer", "红灯")

    # 运行
    print(f"\n初始状态: {light.state}")
    for i in range(6):
        light.trigger("timer")

    print(f"\n最终状态: {light.state}")
    print()


# ═══════════════════════════════════════════
# 方式二：带动作回调
# ═══════════════════════════════════════════

class ActionFSM:
    """带动作回调的状态机"""

    def __init__(self, initial_state):
        self.state = initial_state
        self.transitions: Dict[Tuple, Tuple[str, Optional[Callable]]] = {}
        self.state_callbacks: Dict[str, Callable] = {}

    def add_transition(self, from_state: str, event: str,
                       to_state: str, action: Optional[Callable] = None):
        """添加转移规则，可选附带动作"""
        self.transitions[(from_state, event)] = (to_state, action)

    def on_enter(self, state: str, callback: Callable):
        """注册进入某状态时的回调"""
        self.state_callbacks[state] = callback

    def trigger(self, event: str) -> str:
        key = (self.state, event)
        if key not in self.transitions:
            raise ValueError(f"❌ 非法转移: {self.state} + {event}")

        new_state, action = self.transitions[key]
        old_state = self.state

        # 1. 执行转移时的动作
        if action:
            action(old_state, new_state, event)

        # 2. 切换状态
        self.state = new_state

        # 3. 执行进入新状态的回调
        if new_state in self.state_callbacks:
            self.state_callbacks[new_state](new_state)

        return new_state


def demo_action_fsm():
    """演示：带动作的门禁系统"""
    print("=" * 50)
    print("🚪 演示：门禁系统（带动作回调）")
    print("=" * 50)

    door = ActionFSM("锁定")

    # 定义动作
    def on_lock(old, new, event):
        print(f"  🔒 门已锁定 (from {old})")

    def on_unlock(old, new, event):
        print(f"  🔓 门已解锁")

    def on_open(old, new, event):
        print(f"  🚪 门已打开，欢迎进入！")

    def on_close(old, new, event):
        print(f"  🚪 门已关闭")

    # 定义转移
    door.add_transition("锁定", "刷卡", "解锁", action=on_unlock)
    door.add_transition("解锁", "推门", "打开", action=on_open)
    door.add_transition("打开", "进入", "室内")
    door.add_transition("室内", "关门", "关闭", action=on_close)
    door.add_transition("关闭", "自动锁", "锁定", action=on_lock)

    # 运行
    events = ["刷卡", "推门", "进入", "关门", "自动锁"]
    print(f"\n初始状态: {door.state}\n")

    for event in events:
        door.trigger(event)
        print()

    print(f"最终状态: {door.state}")
    print()


# ═══════════════════════════════════════════
# 方式三：状态转移表可视化
# ═══════════════════════════════════════════

def print_transition_table(fsm: SimpleFSM):
    """打印状态转移表"""
    print("\n📊 状态转移表:")
    print(f"{'当前状态':<10} {'事件':<10} {'下一状态':<10}")
    print("-" * 35)
    for (from_state, event), to_state in sorted(fsm.transitions.items()):
        print(f"{from_state:<10} {event:<10} {to_state:<10}")
    print()


def print_mermaid_fsm(fsm: SimpleFSM, title: str = "FSM"):
    """生成 Mermaid 图"""
    lines = [f"stateDiagram-v2"]
    seen = set()
    for (from_state, event), to_state in fsm.transitions.items():
        edge = f"    {from_state} --> {to_state} : {event}"
        if edge not in seen:
            lines.append(edge)
            seen.add(edge)
    print("\n📈 Mermaid 状态图:")
    print("\n".join(lines))
    print()


# ═══════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════

if __name__ == "__main__":
    demo_simple_fsm()
    demo_action_fsm()

    # 可视化
    light = SimpleFSM("红灯")
    light.add_transition("红灯", "timer", "绿灯")
    light.add_transition("绿灯", "timer", "黄灯")
    light.add_transition("黄灯", "timer", "红灯")

    print_transition_table(light)
    print_mermaid_fsm(light, "红绿灯")
