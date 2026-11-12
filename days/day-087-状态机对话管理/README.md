# Day 087 — 状态机对话管理

> 🤖 项目四（聊天机器人）第 3 天：用状态机管理对话流程

## 📋 今日目标

| 目标 | 说明 |
|------|------|
| 理解状态机 | 什么是有限状态机（FSM），为什么聊天机器人需要它 |
| 实现 FSM | 从零实现一个轻量状态机 |
| 对话管理 | 用状态机管理多轮对话的状态流转 |
| 上下文维护 | 对话上下文、槽位填充、意图识别的整合 |
| 实战项目 | 构建一个完整的客服聊天机器人 |

---

## 一、为什么聊天机器人需要状态机？

### 1.1 无状态 vs 有状态

**无状态机器人**（如 Day 086 的简单 NLP）：
```
用户：我想订机票
机器人：请问出发城市？
用户：北京
机器人：请问目的地？
用户：上海
机器人：请问日期？
用户：明天
机器人：好的，已为您查询！
```

看似正常，但问题是——**机器人并不"记住"之前的对话**。如果用户突然说：

```
用户：改成后天
```

无状态机器人会完全困惑，因为它不知道"后天"指的是哪个字段。

**有状态机器人**：
```
用户：我想订机票
机器人：请问出发城市？ [状态：等待出发城市]
用户：北京
机器人：请问目的地？ [状态：等待目的地，已记录出发=北京]
用户：上海
机器人：请问日期？ [状态：等待日期，已记录出发=北京，目的=上海]
用户：明天
机器人：好的，北京→上海，明天的机票已查询到！ [状态：完成]
用户：改成后天
机器人：好的，已改为北京→上海，后天的机票。 [状态：已完成修改]
```

### 1.2 状态机的核心思想

**有限状态机（Finite State Machine, FSM）** 是一种数学模型，由以下部分组成：

```
┌─────────────────────────────────────────────────────┐
│                    FSM 五元组                         │
│                                                     │
│  S  = 有限状态集合        (States)                   │
│  Σ  = 输入符号集合        (Inputs/Events)            │
│  δ  = 状态转移函数        (Transition Function)       │
│  s₀ = 初始状态            (Initial State)            │
│  F  = 终止状态集合        (Final/Accepting States)    │
│                                                     │
│  简化版：                                            │
│  δ: S × Σ → S   当前状态 + 输入事件 → 下一个状态      │
└─────────────────────────────────────────────────────┘
```

用一个经典的例子——红绿灯：

```mermaid
stateDiagram-v2
    [*] --> 红灯
    红灯 --> 绿灯 : timer
    绿灯 --> 黄灯 : timer
    黄灯 --> 红灯 : timer
```

---

## 二、从零实现状态机

### 2.1 最简状态机

```python
class SimpleFSM:
    """最简有限状态机"""

    def __init__(self, initial_state):
        self.state = initial_state
        self.transitions = {}  # {(当前状态, 事件): 下一状态}

    def add_transition(self, from_state, event, to_state):
        """添加状态转移规则"""
        self.transitions[(from_state, event)] = to_state

    def trigger(self, event):
        """触发事件，返回新状态"""
        key = (self.state, event)
        if key in self.transitions:
            old_state = self.state
            self.state = self.transitions[key]
            return old_state, self.state
        raise ValueError(f"非法转移: 状态={self.state}, 事件={event}")

    def is_in(self, state):
        return self.state == state
```

**使用示例——红绿灯：**

```python
light = SimpleFSM("红灯")
light.add_transition("红灯", "timer", "绿灯")
light.add_transition("绿灯", "timer", "黄灯")
light.add_transition("黄灯", "timer", "红灯")

print(light.state)  # 红灯
light.trigger("timer")
print(light.state)  # 绿灯
```

### 2.2 带动作的状态机

实际应用中，状态转移时通常需要执行一些动作（回调函数）：

```python
class ActionFSM:
    """带动作回调的状态机"""

    def __init__(self, initial_state):
        self.state = initial_state
        self.transitions = {}  # {(state, event): (new_state, callback)}
        self.callbacks = {}    # {state: on_enter_callback}

    def add_transition(self, from_state, event, to_state, action=None):
        self.transitions[(from_state, event)] = (to_state, action)

    def on_enter(self, state, callback):
        """注册进入状态时的回调"""
        self.callbacks[state] = callback

    def trigger(self, event):
        key = (self.state, event)
        if key not in self.transitions:
            raise ValueError(f"非法转移: {self.state} + {event}")

        new_state, action = self.transitions[key]
        old_state = self.state

        # 执行转移时的动作
        if action:
            action(old_state, new_state, event)

        # 执行进入新状态的回调
        self.state = new_state
        if new_state in self.callbacks:
            self.callbacks[new_state](new_state)

        return new_state
```

### 2.3 状态转移表（可视化）

| 当前状态 | 事件 | 下一状态 | 动作 |
|---------|------|---------|------|
| 等待出发 | 输入城市 | 等待目的 | 保存出发城市 |
| 等待目的 | 输入城市 | 等待日期 | 保存目的城市 |
| 等待日期 | 输入日期 | 确认订单 | 保存日期 |
| 确认订单 | 确认 | 完成 | 提交订单 |
| 确认订单 | 取消 | 初始 | 清空数据 |
| 任何状态 | 退出 | 结束 | 清理资源 |

---

## 三、对话状态机设计

### 3.1 对话状态定义

一个典型的客服机器人需要以下状态：

```
                         ┌─────────────┐
                         │   初始状态   │
                         │   GREET     │
                         └──────┬──────┘
                                │ 用户发消息
                                ▼
                         ┌─────────────┐
                    ┌───▶│  理解意图    │
                    │    │  UNDERSTAND │
                    │    └──────┬──────┘
                    │           │ 识别到意图
                    │           ▼
                    │    ┌─────────────┐
                    │    │  收集信息    │◀─────┐
                    │    │  COLLECT     │      │ 信息不完整
                    │    └──────┬──────┘      │
                    │           │ 信息完整      │
                    │           ▼              │
                    │    ┌─────────────┐      │
                    │    │  执行操作    │      │
                    │    │  EXECUTE     │      │
                    │    └──────┬──────┘      │
                    │           │ 执行失败      │
                    │           └──────────────┘
                    │
                    │ 用户重新提问
                    └──────────────────────────┘
```

### 3.2 槽位（Slot）概念

槽位是对话中需要填充的信息字段，类似函数的参数：

```python
# 订机票场景的槽位定义
SLOTS = {
    "book_flight": {
        "departure": {"required": True,  "question": "请问出发城市？"},
        "destination": {"required": True, "question": "请问目的地？"},
        "date": {"required": True,       "question": "请问出发日期？"},
        "passengers": {"required": False, "question": "请问几位乘客？", "default": 1},
    },
    "check_order": {
        "order_id": {"required": True, "question": "请提供订单号？"},
    },
    "cancel_order": {
        "order_id": {"required": True, "question": "请提供要取消的订单号？"},
        "reason": {"required": False, "question": "取消原因是什么？"},
    }
}
```

### 3.3 意图识别 + 槽位填充流程

```mermaid
flowchart TD
    A[用户输入] --> B[NLP 意图识别]
    B --> C{识别到意图?}
    C -->|是| D[加载对应槽位定义]
    C -->|否| E[闲聊/兜底回复]
    D --> F[从输入提取槽位值]
    F --> G{所有必填槽位已填充?}
    G -->|是| H[执行操作]
    G -->|否| I[追问缺失槽位]
    I --> J[用户回复]
    J --> F
    H --> K{操作成功?}
    K -->|是| L[回复结果]
    K -->|否| M[回复错误]
```

---

## 四、完整实战：客服聊天机器人

### 4.1 架构设计

```
┌─────────────────────────────────────────────────┐
│                  ChatBot                         │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ NLP 引擎  │→│ 状态管理器 │→│ 动作执行器    │   │
│  │ (意图+NER)│  │ (FSM)    │  │ (业务逻辑)   │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│       ↑              │              ↓            │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ 用户输入  │  │ 对话历史  │  │ 回复生成     │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
└─────────────────────────────────────────────────┘
```

### 4.2 核心组件

```python
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import re


class Intent(Enum):
    """用户意图"""
    GREET = auto()          # 打招呼
    BOOK_FLIGHT = auto()    # 订机票
    CHECK_ORDER = auto()    # 查询订单
    CANCEL_ORDER = auto()   # 取消订单
    BYE = auto()            # 再见
    UNKNOWN = auto()        # 未知意图


@dataclass
class Slot:
    """槽位定义"""
    name: str
    required: bool = True
    question: str = ""
    default: Any = None
    value: Any = None

    @property
    def is_filled(self):
        return self.value is not None


@dataclass
class DialogueState:
    """对话状态"""
    current_intent: Optional[Intent] = None
    slots: Dict[str, Slot] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def get_next_slot(self) -> Optional[Slot]:
        """获取下一个需要填充的槽位"""
        for slot in self.slots.values():
            if slot.required and not slot.is_filled:
                return slot
        return None

    def all_slots_filled(self) -> bool:
        return all(s.is_filled for s in self.slots.values() if s.required)


class NLPProcessor:
    """简化版 NLP 处理器"""

    # 意图关键词映射
    INTENT_KEYWORDS = {
        Intent.BOOK_FLIGHT: ["订机票", "买机票", "航班", "飞"],
        Intent.CHECK_ORDER: ["查询订单", "查订单", "订单状态", "我的订单"],
        Intent.CANCEL_ORDER: ["取消订单", "退票", "不要了"],
        Intent.GREET: ["你好", "嗨", "您好", "hi", "hello"],
        Intent.BYE: ["再见", "拜拜", "bye", "quit", "退出"],
    }

    # 城市识别（简化）
    CITIES = ["北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "重庆", "西安", "南京"]

    def identify_intent(self, text: str) -> Intent:
        """识别用户意图"""
        text_lower = text.lower().strip()
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return intent
        return Intent.UNKNOWN

    def extract_entities(self, text: str, slot_name: str) -> Optional[str]:
        """提取实体（简化版 NER）"""
        if slot_name == "departure" or slot_name == "destination":
            for city in self.CITIES:
                if city in text:
                    return city
        elif slot_name == "date":
            # 简单日期提取
            date_patterns = [
                r"(\d{1,2})月(\d{1,2})[日号]",
                r"(明天|后天|大后天|今天)",
                r"(下[一二三四五六日天])",
                r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            ]
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    return match.group(0)
        elif slot_name == "order_id":
            match = re.search(r"[A-Za-z0-9]{8,}", text)
            if match:
                return match.group(0)
        elif slot_name == "passengers":
            match = re.search(r"(\d+)\s*[位个名人]", text)
            if match:
                return int(match.group(1))
        return None


class ChatBot:
    """客服聊天机器人"""

    # 意图对应的槽位模板
    SLOT_TEMPLATES = {
        Intent.BOOK_FLIGHT: [
            Slot("departure", question="请问从哪个城市出发？"),
            Slot("destination", question="请问目的地是哪里？"),
            Slot("date", question="请问出发日期？"),
            Slot("passengers", required=False, question="请问几位乘客？", default=1),
        ],
        Intent.CHECK_ORDER: [
            Slot("order_id", question="请提供订单号？"),
        ],
        Intent.CANCEL_ORDER: [
            Slot("order_id", question="请提供要取消的订单号？"),
            Slot("reason", required=False, question="取消原因是什么？"),
        ],
    }

    def __init__(self):
        self.nlp = NLPProcessor()
        self.state = DialogueState()
        self._init_state()

    def _init_state(self):
        """初始化/重置对话状态"""
        self.state = DialogueState()

    def process_message(self, user_input: str) -> str:
        """处理用户消息，返回回复"""
        self.state.add_message("user", user_input)

        # 1. 识别意图
        intent = self.nlp.identify_intent(user_input)

        # 2. 处理特殊意图
        if intent == Intent.GREET:
            reply = "您好！我是智能客服，可以帮您订机票、查询订单、取消订单。请问有什么可以帮您？"
            self.state.add_message("bot", reply)
            return reply

        if intent == Intent.BYE:
            reply = "感谢您的咨询，再见！👋"
            self._init_state()
            self.state.add_message("bot", reply)
            return reply

        # 3. 如果当前正在收集信息（有未完成的槽位），继续填充
        if self.state.current_intent and not self.state.all_slots_filled():
            self._fill_slots(user_input)
            return self._continue_collection()

        # 4. 新意图
        if intent == Intent.UNKNOWN:
            reply = "抱歉，我没理解您的意思。我可以帮您：\n1. 订机票\n2. 查询订单\n3. 取消订单\n请问您需要什么服务？"
            self.state.add_message("bot", reply)
            return reply

        # 5. 开始新的意图处理
        self.state.current_intent = intent
        self.state.slots = {}
        for slot_template in self.SLOT_TEMPLATES.get(intent, []):
            self.state.slots[slot_template.name] = Slot(
                name=slot_template.name,
                required=slot_template.required,
                question=slot_template.question,
                default=slot_template.default,
            )

        # 尝试从当前输入提取槽位
        self._fill_slots(user_input)

        return self._continue_collection()

    def _fill_slots(self, text: str):
        """从文本中提取槽位值"""
        for slot in self.state.slots.values():
            if not slot.is_filled:
                value = self.nlp.extract_entities(text, slot.name)
                if value is not None:
                    slot.value = value

    def _continue_collection(self) -> str:
        """继续收集信息或执行操作"""
        next_slot = self.state.get_next_slot()
        if next_slot:
            reply = next_slot.question
        elif self.state.all_slots_filled():
            reply = self._execute_action()
        else:
            reply = "抱歉，处理中遇到问题。"

        self.state.add_message("bot", reply)
        return reply

    def _execute_action(self) -> str:
        """执行业务操作"""
        intent = self.state.current_intent
        slots = {k: v.value for k, v in self.state.slots.items()}

        if intent == Intent.BOOK_FLIGHT:
            return (
                f"✅ 订票成功！\n"
                f"  出发：{slots.get('departure')}\n"
                f"  目的地：{slots.get('destination')}\n"
                f"  日期：{slots.get('date')}\n"
                f"  乘客：{slots.get('passengers', 1)} 位\n"
                f"  订单号：FL{hash(str(slots)) % 100000:06d}"
            )
        elif intent == Intent.CHECK_ORDER:
            order_id = slots.get('order_id', '未知')
            return f"📋 订单 {order_id} 状态：已支付，等待出票"
        elif intent == Intent.CANCEL_ORDER:
            order_id = slots.get('order_id', '未知')
            reason = slots.get('reason', '未说明')
            return f"❌ 订单 {order_id} 已取消（原因：{reason}）"
        else:
            return "操作已完成。"

        # 重置状态，准备下一轮对话
        self._init_state()
```

### 4.3 运行效果

```
🤖 智能客服已启动！输入 quit 退出。

你: 你好
机器人: 您好！我是智能客服，可以帮您订机票、查询订单、取消订单。请问有什么可以帮您？

你: 我要订机票
机器人: 请问从哪个城市出发？

你: 北京
机器人: 请问目的地是哪里？

你: 上海
机器人: 请问出发日期？

你: 明天
机器人: ✅ 订票成功！
  出发：北京
  目的地：上海
  日期：明天
  乘客：1 位
  订单号：FL482917

你: 我要查订单
机器人: 请提供订单号？

你: FL482917
机器人: 📋 订单 FL482917 状态：已支付，等待出票

你: 再见
机器人: 感谢您的咨询，再见！👋
```

---

## 五、进阶：状态机的高级用法

### 5.1 状态嵌套（层级状态机）

复杂对话可能有嵌套状态：

```python
class HierarchicalState:
    """层级状态机 - 支持子状态"""

    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.children = {}
        self.current_child = None

    def add_child(self, child_state):
        self.children[child_state.name] = child_state

    def enter(self):
        """进入状态时调用"""
        print(f"  → 进入状态: {self.name}")

    def exit(self):
        """退出状态时调用"""
        print(f"  ← 退出状态: {self.name}")
        if self.current_child:
            self.children[self.current_child].exit()
            self.current_child = None


class HierarchicalFSM:
    """层级状态机"""

    def __init__(self):
        self.root = HierarchicalState("root")
        self.current = self.root

    def add_state(self, name, parent_name=None):
        state = HierarchicalState(name)
        if parent_name:
            parent = self._find_state(self.root, parent_name)
            if parent:
                parent.add_child(state)
                state.parent = parent
        else:
            self.root.add_child(state)
        return state

    def _find_state(self, node, name):
        if node.name == name:
            return node
        for child in node.children.values():
            result = self._find_state(child, name)
            if result:
                return result
        return None

    def transition_to(self, state_name):
        # 退出当前状态链
        self.current.exit()
        # 进入新状态链
        new_state = self._find_state(self.root, state_name)
        if new_state:
            self.current = new_state
            self.current.enter()
```

### 5.2 并行状态机

某些场景下，机器人需要同时处理多个状态（如等待用户输入的同时处理超时）：

```python
import threading
import time


class ParallelFSM:
    """并行状态机 - 支持多个并发状态机"""

    def __init__(self):
        self.state_machines = {}
        self.locks = {}

    def add_machine(self, name, initial_state):
        self.state_machines[name] = SimpleFSM(initial_state)
        self.locks[name] = threading.Lock()

    def trigger(self, machine_name, event):
        with self.locks[machine_name]:
            return self.state_machines[machine_name].trigger(event)

    def get_state(self, machine_name):
        with self.locks[machine_name]:
            return self.state_machines[machine_name].state
```

### 5.3 状态机可视化

```python
def visualize_fsm(fsm, title="FSM"):
    """将状态机导出为 Mermaid 图"""
    lines = [f"stateDiagram-v2", f"    title {title}"]
    for (from_state, event), to_state in fsm.transitions.items():
        lines.append(f"    {from_state} --> {to_state} : {event}")
    return "\n".join(lines)
```

---

## 六、状态机设计模式

### 6.1 常见模式对比

| 模式 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| 查表法 | 简单状态机 | 直观、易维护 | 状态多时表格庞大 |
| 状态模式（OOP） | 复杂状态逻辑 | 每个状态独立封装 | 类数量多 |
| 表驱动 | 规则明确的系统 | 数据驱动、易配置 | 灵活性较低 |
| 行为树 | 游戏 AI | 可视化、易调试 | 学习成本高 |

### 6.2 状态模式（State Pattern）

```python
from abc import ABC, abstractmethod


class State(ABC):
    """状态基类"""

    @abstractmethod
    def handle(self, context, user_input):
        pass

    @abstractmethod
    def get_prompt(self, context):
        pass


class IdleState(State):
    """空闲状态"""

    def handle(self, context, user_input):
        intent = context.nlp.identify_intent(user_input)
        if intent in context.SLOT_TEMPLATES:
            context.current_intent = intent
            context.slots = {
                s.name: Slot(name=s.name, required=s.required,
                           question=s.question, default=s.default)
                for s in context.SLOT_TEMPLATES[intent]
            }
            return CollectingState()
        return self

    def get_prompt(self, context):
        return "您好！请问有什么可以帮您？"


class CollectingState(State):
    """收集信息状态"""

    def handle(self, context, user_input):
        context.fill_slots(user_input)
        if context.all_slots_filled():
            return ExecutingState()
        return self

    def get_prompt(self, context):
        next_slot = context.get_next_slot()
        return next_slot.question if next_slot else "处理中..."


class ExecutingState(State):
    """执行操作状态"""

    def handle(self, context, user_input):
        result = context.execute_action()
        context.last_result = result
        return IdleState()

    def get_prompt(self, context):
        return context.last_result or "操作完成"
```

---

## 七、思考题

1. **状态爆炸问题**：如果一个聊天机器人要支持 10 种意图，每种意图平均 4 个槽位，理论上需要多少个状态？如何用层级状态机减少状态数量？

**参考答案**

先算「朴素扁平状态机」的账。如果只是顺序收集，每个意图约 4 个「等待某槽位」的状态，10 个意图就是 `10 × 4 = 40` 个收集状态，再加问候、确认、完成、错误等公共状态。

但真正的**状态爆炸**来自「组合」：若允许槽位以任意顺序填充，并把「已填槽位的组合」编码成状态，每个意图有 `2^4 = 16` 种填充子集，10 个意图就是 `10 × 16 = 160` 个状态；槽位更多时按 `2^n` 指数增长。再叠加「中断/恢复」「错误重试」等维度，状态数是**乘积式**膨胀，很快就失控。

**层级状态机（HSM）+ 数据驱动**能把它压下来：

- 把公共流程抽成**共享的父状态**（如 `GREET / UNDERSTAND / COLLECT / EXECUTE`），所有意图复用同一套，而不是各复制一份。
- 把「意图之间的差异」放进**数据**（槽位模板 `SLOT_TEMPLATES`），而不是放进状态。`COLLECT` 是一个被所有意图复用的子状态机，靠「当前意图的槽位定义」这个参数驱动。
- 子状态可以嵌套：进入某意图时激活它的 `COLLECT` 子机，退出时统一回到父状态，公共的「退出/超时/错误」转移只在父层定义一次。

这样顶层状态数基本恒定（约 5~6 个），与意图数量解耦。一句话：用「层级 + 数据驱动」把 `状态数 = 意图数 × 槽位组合数` 降为 `状态数 ≈ 常数，差异交给数据`。

- 小例子：从 `10 × 2^4 = 160` 个状态，降到约 5~6 个共享顶层状态 + 一张槽位配置表。

2. **并发处理**：当用户在等待系统响应时发来新消息，你的状态机应该如何处理？设计一个"中断-恢复"机制。

**参考答案**

核心思路：把「被打断的对话」当成一个可保存、可恢复的**上下文快照**，用一个**栈**管理。当用户在收集途中插入新意图时，先把当前 `(意图, 已填槽位)` 压栈暂停，转去处理新意图；新意图完成后弹栈，回到原来被打断的地方继续，而不是从头再来。

设计要点：① 中断时保存进度（已填槽位不能丢）；② 用栈支持「多层嵌套中断」（A 被打断成 B，B 又被打断成 C）；③ 恢复时回到「下一个待填槽位」继续追问；④ 给中断设超时/上限，避免栈无限增长。

下面是一个可运行的最小演示（仅用标准库，已验证）：

```python
# 中断-恢复：用「栈」保存被打断的对话，处理完插入意图后再恢复
class InterruptibleBot:
    def __init__(self):
        self.current = None      # 当前意图
        self.slots = {}          # 当前意图已填槽位
        self.stack = []          # 被中断的 (意图, 槽位) 栈

    def start(self, intent, slots=None):
        # 若正在收集别的意图，先把它压栈保存（中断）
        if self.current is not None:
            self.stack.append((self.current, dict(self.slots)))
            print(f"[中断] 暂停 {self.current}，已填 {self.slots}")
        self.current = intent
        self.slots = dict(slots or {})
        print(f"[开始] 处理 {self.current}")

    def fill(self, **kw):
        self.slots.update(kw)

    def finish(self):
        print(f"[完成] {self.current} 槽位={self.slots}")
        self.current = None
        self.slots = {}
        # 恢复最近被中断的对话
        if self.stack:
            self.current, self.slots = self.stack.pop()
            print(f"[恢复] 回到 {self.current}，已填 {self.slots}")


bot = InterruptibleBot()
bot.start("订机票")
bot.fill(departure="北京")
bot.start("查天气")          # 用户中途插入新意图 → 中断订机票
bot.fill(city="上海")
bot.finish()                 # 查天气完成 → 自动恢复订机票
bot.fill(destination="上海", date="明天")
bot.finish()                 # 订机票完成
```

预期输出：

```
[开始] 处理 订机票
[中断] 暂停 订机票，已填 {'departure': '北京'}
[开始] 处理 查天气
[完成] 查天气 槽位={'city': '上海'}
[恢复] 回到 订机票，已填 {'departure': '北京'}
[完成] 订机票 槽位={'departure': '北京', 'destination': '上海', 'date': '明天'}
```

可以看到：订机票填到一半被「查天气」打断，查天气结束后自动恢复，且之前填的 `departure=北京` 没丢，最终顺利补全。真实系统里还需配合「超时自动丢弃中断」「向用户确认是否继续原任务」等策略。

3. **错误恢复**：用户输入了一个无效的城市名（如"火星"），状态机应该如何优雅地处理？设计一个错误恢复流程。

**参考答案**

优雅处理无效输入的关键是：**校验失败时不推进状态、不丢已填数据，只停留在当前槽位重新追问**，并给出「可操作」的反馈，而不是崩溃或静默忽略。一个完整的错误恢复流程包含四步：

1. **校验**：把用户输入对照合法值（城市白名单/正则）检查。
2. **反馈**：无效时明确告诉用户「哪里错了、期望什么」，最好给示例或候选（如「支持：北京/上海/广州…」）。
3. **重试**：状态保持不变，重新追问同一槽位；设置最大重试次数。
4. **兜底**：超过重试上限就降级——转人工、提供菜单选择、或礼貌取消，避免无限循环。

下面是可运行的最小演示（仅用标准库，已验证）：

```python
# 错误恢复：校验槽位 → 无效则保留状态、重新追问 → 超过次数兜底
VALID_CITIES = {"北京", "上海", "广州", "深圳"}


def collect_city(inputs, max_retry=3):
    """模拟「等待出发城市」状态：无效输入不推进状态，只重新追问"""
    for attempt, text in enumerate(inputs, 1):
        city = text.strip()
        if city in VALID_CITIES:           # 校验通过 → 状态推进
            print(f"第{attempt}次: '{city}' 有效 → 进入下一状态")
            return city
        # 校验失败 → 状态不变，给出可操作的反馈
        remain = max_retry - attempt
        if remain > 0:
            print(f"第{attempt}次: '{city}' 不是有效城市，请重新输入（还可试 {remain} 次）")
        else:
            print(f"第{attempt}次: '{city}' 仍无效 → 触发兜底（转人工/取消）")
            return None
    return None


print(collect_city(["火星", "北京"]))
print(collect_city(["火星", "月球", "太阳", "北京"]))
```

预期输出：

```
第1次: '火星' 不是有效城市，请重新输入（还可试 2 次）
第2次: '北京' 有效 → 进入下一状态
北京
第1次: '火星' 不是有效城市，请重新输入（还可试 2 次）
第2次: '月球' 不是有效城市，请重新输入（还可试 1 次）
第3次: '太阳' 仍无效 → 触发兜底（转人工/取消）
None
```

第一组「火星→北京」在重试后成功恢复；第二组连续 3 次无效触发兜底返回 `None`（转人工/取消）。注意整个过程中状态始终停在「等待出发城市」，不会错误地跳到下一步。

💡 提示：模糊匹配（如把「北京市」归一化为「北京」、拼音/错别字纠错）能减少误判，但要在「宽松纠错」和「严格校验」之间权衡，涉及订单等关键操作时宜严格。

4. **持久化**：对话状态需要保存到数据库以便会话恢复，你会如何序列化状态机的状态？哪些信息需要持久化，哪些可以丢弃？

**参考答案**

序列化的核心原则：**只存「能据此重建对话」的最小数据，凡是运行时对象一律丢弃**。状态机里真正需要持久化的是「数据」，不是「行为」。

- **需要持久化**：会话/用户 ID、当前状态名（枚举存它的**名字字符串**，如 `"book_flight"`）、已填槽位的值、可选的对话历史、中断栈、重试计数、过期时间戳。这些都是纯数据，能 JSON 化。
- **应当丢弃**：回调函数、socket/数据库连接、线程锁、NLP 模型对象、事件循环——它们无法序列化，且恢复时由程序重新创建/绑定即可。

做法：把状态收敛进一个 `dataclass`（纯数据），用 `asdict()` + `json.dumps` 存库；恢复时 `json.loads` 再构造回对象，并把「状态名」映射回枚举、重新挂上回调。

下面是可运行演示（仅用标准库，已验证）：

```python
# 持久化：只存「可重建对话」的最小状态，回调/连接等运行时对象丢弃
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class DialogueState:
    user_id: str
    current_intent: Optional[str] = None        # 枚举意图存「名字」而非对象
    slots: dict = field(default_factory=dict)   # 已填槽位
    history: list = field(default_factory=list) # 对话历史（可选）
    # 不持久化：回调函数、socket 连接、线程锁、NLP 模型等运行时对象


state = DialogueState("u1001", "book_flight",
                      {"departure": "北京", "destination": "上海"},
                      [{"role": "user", "content": "我要订机票"}])

# 序列化 → 存数据库/Redis
blob = json.dumps(asdict(state), ensure_ascii=False)
print("存储:", blob)

# 会话恢复：反序列化 → 重建状态机
restored = DialogueState(**json.loads(blob))
print("恢复:", restored.current_intent, restored.slots)
```

预期输出：

```
存储: {"user_id": "u1001", "current_intent": "book_flight", "slots": {"departure": "北京", "destination": "上海"}, "history": [{"role": "user", "content": "我要订机票"}]}
恢复: book_flight {'departure': '北京', 'destination': '上海'}
```

恢复后 `current_intent` 和 `slots` 与存储前一致，状态机就能从「等待日期」继续，而不必让用户重填。

⚠️ 注意：① 枚举要存名字（`intent.name`），别直接 `json.dumps` 枚举对象；② 给会话设 TTL，长期不活跃的快照应过期清理；③ 含敏感信息（手机号等）的槽位要加密或脱敏后再存；④ 跨版本时给快照加 `schema_version`，便于兼容旧数据。

5. **多用户并发**：一个服务器上运行的状态机需要同时服务 1000 个用户，如何设计才能保证每个用户的会话互不干扰？

**参考答案**

关键一句话：**绝不能用「一个全局状态机」服务所有人，必须做到「每用户一份独立状态」**。1000 个用户就是 1000 个互不相干的 `DialogueState`，靠 ID 隔离。

- **按 ID 索引会话**：用 `sessions = {}`，每次请求 `state = sessions.setdefault(user_id, DialogueState())`，各用户读写自己的对象，天然隔离。
- **无状态工作进程 + 外部存储**：把会话状态放到 Redis/数据库（而不是进程内存），任意 worker 都能凭 `user_id` 取回同一份状态。这样可水平扩容、进程重启不丢会话，也避免「用户被绑死在某台机器」。
- **并发安全**：asyncio 单线程下，同一时刻只有一个协程在跑，但 `await` 处会切换。要保证「取状态→改状态→存回」这段对同一用户是原子的——可用「每用户一把锁」或把同一用户的消息串行化处理，避免两条消息交叉改坏槽位。不同用户之间则无需加锁。
- **生命周期管理**：给会话设空闲 TTL，定时清理过期会话，防止 1000 个（乃至更多）僵尸会话撑爆内存。

- 小例子：`sessions["A"]` 填到「等待日期」，`sessions["B"]` 还在「等待出发城市」，两者各存各的槽位，A 的输入绝不会写进 B 的状态。

💡 提示：多机部署时，若同一用户的请求可能落到不同 worker，务必用共享存储（Redis）而非本地字典，否则会出现「状态在不同机器上不一致」的诡异问题。

---

## 📚 扩展阅读

- [经典状态模式 - Refactoring.Guru](https://refactoring.guru/design-patterns/state)
- [对话系统架构 - Rasa 文档](https://rasa.com/docs/rasa/)
- [有限状态机 - Wikipedia](https://en.wikipedia.org/wiki/Finite-state_machine)
- [行为树 vs 状态机 - Game AI Pro](http://www.gameaipro.com/)

---

> 💡 **今日关键点**：状态机是管理复杂对话流程的核心工具。它让机器人从"一问一答"进化到"理解上下文的多轮对话"。掌握状态机设计，是构建真正智能对话系统的基础。
