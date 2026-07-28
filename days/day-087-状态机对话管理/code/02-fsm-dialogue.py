#!/usr/bin/env python3
"""
Day 087 - 代码示例 2：基于状态机的对话管理系统
演示如何用 FSM 管理多轮对话、槽位填充、意图识别
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import re


# ═══════════════════════════════════════════
# 意图与槽位定义
# ═══════════════════════════════════════════

class Intent(Enum):
    """用户意图"""
    GREET = auto()
    BOOK_FLIGHT = auto()
    CHECK_ORDER = auto()
    CANCEL_ORDER = auto()
    BYE = auto()
    UNKNOWN = auto()


@dataclass
class Slot:
    """槽位（需要填充的信息字段）"""
    name: str
    required: bool = True
    question: str = ""
    default: Any = None
    value: Any = None

    @property
    def is_filled(self):
        return self.value is not None

    def __repr__(self):
        status = "✅" if self.is_filled else "❌"
        return f"{status} {self.name}={self.value}"


# ═══════════════════════════════════════════
# NLP 处理器（简化版）
# ═══════════════════════════════════════════

class NLPProcessor:
    """简化版 NLP 处理器 - 意图识别 + 实体提取"""

    INTENT_KEYWORDS = {
        Intent.BOOK_FLIGHT: ["订机票", "买机票", "航班", "机票", "飞"],
        Intent.CHECK_ORDER: ["查询订单", "查订单", "订单状态", "我的订单", "查一下"],
        Intent.CANCEL_ORDER: ["取消订单", "退票", "不要了", "退款"],
        Intent.GREET: ["你好", "嗨", "您好", "hi", "hello", "在吗"],
        Intent.BYE: ["再见", "拜拜", "bye", "quit", "退出", "没了"],
    }

    CITIES = ["北京", "上海", "广州", "深圳", "成都", "杭州",
              "武汉", "重庆", "西安", "南京", "天津", "苏州"]

    def identify_intent(self, text: str) -> Intent:
        """识别用户意图"""
        text_lower = text.lower().strip()
        for intent, keywords in self.INTENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return intent
        return Intent.UNKNOWN

    def extract_entities(self, text: str, slot_name: str) -> Optional[Any]:
        """从文本中提取实体（简化版 NER）"""
        if slot_name in ("departure", "destination"):
            for city in self.CITIES:
                if city in text:
                    return city

        elif slot_name == "date":
            patterns = [
                (r"(\d{1,2})月(\d{1,2})[日号]", lambda m: m.group(0)),
                (r"(明天|后天|大后天|今天)", lambda m: m.group(1)),
                (r"(下[一二三四五六日天])", lambda m: m.group(1)),
                (r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", lambda m: m.group(1)),
            ]
            for pattern, extractor in patterns:
                match = re.search(pattern, text)
                if match:
                    return extractor(match)

        elif slot_name == "order_id":
            match = re.search(r"[A-Za-z]{2}\d{5,}", text)
            if match:
                return match.group(0)

        elif slot_name == "passengers":
            match = re.search(r"(\d+)\s*[位个名人]", text)
            if match:
                return int(match.group(1))

        elif slot_name == "reason":
            # 取消原因：取整句话
            return text.strip()

        return None


# ═══════════════════════════════════════════
# 对话状态管理器
# ═══════════════════════════════════════════

@dataclass
class ConversationState:
    """单轮对话状态"""
    intent: Optional[Intent] = None
    slots: Dict[str, Slot] = field(default_factory=dict)
    history: List[Dict[str, str]] = field(default_factory=list)
    round_count: int = 0

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

    def reset(self):
        """重置状态"""
        self.intent = None
        self.slots.clear()
        self.round_count = 0


# ═══════════════════════════════════════════
# 核心：基于状态机的对话管理器
# ═══════════════════════════════════════════

class DialogueManager:
    """
    基于状态机的对话管理器

    状态流转：
    IDLE → UNDERSTANDING → COLLECTING → EXECUTING → IDLE
    """

    # 状态定义
    IDLE = "IDLE"                    # 空闲，等待用户输入
    UNDERSTANDING = "UNDERSTANDING"  # 理解意图中
    COLLECTING = "COLLECTING"        # 收集槽位信息
    EXECUTING = "EXECUTING"          # 执行操作
    CLARIFYING = "CLARIFYING"        # 需要澄清

    # 意图对应的槽位模板
    SLOT_TEMPLATES: Dict[Intent, List[Slot]] = {
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
        self.state = self.IDLE
        self.conversation = ConversationState()

    def process(self, user_input: str) -> str:
        """处理用户输入，返回机器人回复"""
        self.conversation.add_message("user", user_input)
        self.conversation.round_count += 1

        print(f"\n{'─' * 40}")
        print(f"状态: {self.state} | 轮次: {self.conversation.round_count}")

        # 根据当前状态分发处理
        handler = {
            self.IDLE: self._handle_idle,
            self.UNDERSTANDING: self._handle_understanding,
            self.COLLECTING: self._handle_collecting,
            self.CLARIFYING: self._handle_clarifying,
        }.get(self.state, self._handle_idle)

        reply = handler(user_input)
        self.conversation.add_message("bot", reply)

        # 打印当前槽位状态
        if self.conversation.slots:
            print("槽位状态:")
            for slot in self.conversation.slots.values():
                print(f"  {slot}")

        return reply

    def _handle_idle(self, user_input: str) -> str:
        """IDLE 状态处理"""
        intent = self.nlp.identify_intent(user_input)

        if intent == Intent.GREET:
            return "您好！我是智能客服 🤖\n可以帮您：订机票、查询订单、取消订单\n请问有什么可以帮您？"

        if intent == Intent.BYE:
            self.conversation.reset()
            self.state = self.IDLE
            return "感谢您的咨询，再见！👋"

        if intent == Intent.UNKNOWN:
            return ("抱歉，我没理解您的意思。您可以试试：\n"
                    "• 订机票\n• 查询订单\n• 取消订单")

        # 识别到有效意图，开始收集信息
        self.conversation.intent = intent
        self.conversation.slots = {}
        for tmpl in self.SLOT_TEMPLATES.get(intent, []):
            self.conversation.slots[tmpl.name] = Slot(
                name=tmpl.name, required=tmpl.required,
                question=tmpl.question, default=tmpl.default,
            )

        # 尝试从当前输入提取
        self._fill_slots(user_input)
        self.state = self.COLLECTING

        # 检查是否已填满
        if self.conversation.all_slots_filled():
            return self._execute()

        next_slot = self.conversation.get_next_slot()
        return next_slot.question if next_slot else "处理中..."

    def _handle_understanding(self, user_input: str) -> str:
        """UNDERSTANDING 状态 - 重新理解意图"""
        # 通常不会直接进入此状态，作为扩展点
        self.state = self.IDLE
        return self._handle_idle(user_input)

    def _handle_collecting(self, user_input: str) -> str:
        """COLLECTING 状态 - 继续填充槽位"""
        # 检查是否要切换意图
        new_intent = self.nlp.identify_intent(user_input)
        if new_intent in (Intent.BOOK_FLIGHT, Intent.CHECK_ORDER, Intent.CANCEL_ORDER):
            if new_intent != self.conversation.intent:
                # 意图变更，重新开始
                self.conversation.intent = new_intent
                self.conversation.slots = {}
                for tmpl in self.SLOT_TEMPLATES.get(new_intent, []):
                    self.conversation.slots[tmpl.name] = Slot(
                        name=tmpl.name, required=tmpl.required,
                        question=tmpl.question, default=tmpl.default,
                    )

        # 检查是否要退出
        if new_intent == Intent.BYE:
            self.conversation.reset()
            self.state = self.IDLE
            return "好的，已取消当前操作。再见！👋"

        # 继续填充槽位
        self._fill_slots(user_input)

        if self.conversation.all_slots_filled():
            return self._execute()

        next_slot = self.conversation.get_next_slot()
        return next_slot.question if next_slot else "处理中..."

    def _handle_clarifying(self, user_input: str) -> str:
        """CLARIFYING 状态 - 澄清用户意图"""
        self.state = self.COLLECTING
        return self._handle_collecting(user_input)

    def _fill_slots(self, text: str):
        """从文本中提取槽位值"""
        for slot in self.conversation.slots.values():
            if not slot.is_filled:
                value = self.nlp.extract_entities(text, slot.name)
                if value is not None:
                    slot.value = value
                    print(f"  📥 提取到槽位: {slot.name} = {value}")

    def _execute(self) -> str:
        """执行操作"""
        self.state = self.EXECUTING
        intent = self.conversation.intent
        slots = {k: v.value for k, v in self.conversation.slots.items()}

        if intent == Intent.BOOK_FLIGHT:
            order_id = f"FL{hash(str(slots)) % 100000:06d}"
            result = (
                f"✅ 订票成功！\n"
                f"  🛫 出发：{slots.get('departure')}\n"
                f"  🛬 目的地：{slots.get('destination')}\n"
                f"  📅 日期：{slots.get('date')}\n"
                f"  👥 乘客：{slots.get('passengers', 1)} 位\n"
                f"  📋 订单号：{order_id}"
            )
        elif intent == Intent.CHECK_ORDER:
            oid = slots.get('order_id', '未知')
            result = f"📋 订单 {oid} 状态：已支付，等待出票"
        elif intent == Intent.CANCEL_ORDER:
            oid = slots.get('order_id', '未知')
            reason = slots.get('reason', '未说明')
            result = f"❌ 订单 {oid} 已取消（原因：{reason}）"
        else:
            result = "操作已完成。"

        # 重置，准备下一轮
        self.conversation.reset()
        self.state = self.IDLE
        return result


# ═══════════════════════════════════════════
# 交互式测试
# ═══════════════════════════════════════════

def interactive_test():
    """交互式测试对话管理器"""
    print("=" * 55)
    print("🤖 基于状态机的对话管理器 - 交互式测试")
    print("=" * 55)
    print("输入 'quit' 退出\n")

    dm = DialogueManager()

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 再见！")
            break

        reply = dm.process(user_input)
        print(f"机器人: {reply}")


def automated_test():
    """自动化测试"""
    print("=" * 55)
    print("🤖 自动化测试")
    print("=" * 55)

    dm = DialogueManager()

    test_cases = [
        # 测试用例：订机票完整流程
        [
            ("你好", "打招呼"),
            ("我要订机票", "订机票意图"),
            ("北京", "出发城市"),
            ("上海", "目的城市"),
            ("明天", "日期"),
            ("1位", "乘客数"),
        ],
        # 测试用例：查询订单
        [
            ("查订单", "查询意图"),
            ("FL123456", "订单号"),
        ],
        # 测试用例：取消订单
        [
            ("取消订单", "取消意图"),
            ("FL789012", "订单号"),
            ("不想要了", "原因"),
        ],
        # 测试用例：意图切换
        [
            ("订机票", "开始订票"),
            ("北京", "出发城市"),
            ("算了，查订单吧", "切换意图"),
            ("FL999999", "订单号"),
        ],
        # 测试用例：退出
        [
            ("再见", "退出"),
        ],
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'━' * 55}")
        print(f"📋 测试用例 {i}")
        print(f"{'━' * 55}")

        for user_input, desc in case:
            print(f"\n  [{desc}]")
            reply = dm.process(user_input)
            print(f"  你: {user_input}")
            print(f"  机器人: {reply}")

    print(f"\n{'━' * 55}")
    print("✅ 所有测试用例执行完毕")
    print(f"{'━' * 55}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        automated_test()
    else:
        interactive_test()
