#!/usr/bin/env python3
"""
Day 087 - 代码示例 3：完整客服聊天机器人项目
整合状态机、NLP、槽位填充，构建一个可交互的客服系统
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
import re
import json
from datetime import datetime


# ═══════════════════════════════════════════
# 一、意图识别（简化版 NLP）
# ═══════════════════════════════════════════

class Intent(Enum):
    """用户意图枚举"""
    GREET = "greet"           # 打招呼
    BOOK = "book"             # 预订
    QUERY = "query"           # 查询
    COMPLAINT = "complaint"   # 投诉
    CANCEL = "cancel"         # 取消
    BYE = "bye"               # 告别
    UNKNOWN = "unknown"       # 未知


# 关键词 → 意图映射表（生产环境应使用 ML 模型）
INTENT_KEYWORDS: Dict[Intent, List[str]] = {
    Intent.GREET: ["你好", "您好", "嗨", "hello", "hi", "在吗"],
    Intent.BOOK: ["预订", "订", "预约", "我要", "帮我订", "买票"],
    Intent.QUERY: ["查询", "查", "我的订单", "进度", "状态", "什么时候"],
    Intent.COMPLAINT: ["投诉", "差评", "不满意", "太差", "垃圾", "退款"],
    Intent.CANCEL: ["取消", "退订", "不要了", "算了"],
    Intent.BYE: ["再见", "拜拜", "bye", "没有了", "谢谢"],
}


def detect_intent(text: str) -> Intent:
    """基于关键词的意图识别（简化版）"""
    text_lower = text.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return intent
    return Intent.UNKNOWN


# ═══════════════════════════════════════════
# 二、槽位定义
# ═══════════════════════════════════════════

@dataclass
class SlotDef:
    """槽位定义"""
    name: str               # 槽位名
    question: str           # 提示语
    required: bool = True   # 是否必填
    validator: Optional[Callable] = None  # 验证函数


# 预订机票的槽位定义
BOOKING_SLOTS = [
    SlotDef("departure", "请问出发城市是哪里？"),
    SlotDef("destination", "请问目的地城市是？"),
    SlotDef("date", "请问出发日期？（如：明天、7月30日）"),
    SlotDef("name", "请问您的姓名？"),
    SlotDef("phone", "请输入手机号码", validator=lambda x: re.match(r'^1[3-9]\d{9}$', x)),
]

# 投诉的槽位定义
COMPLAINT_SLOTS = [
    SlotDef("order_id", "请问涉及的订单号是？"),
    SlotDef("issue", "请描述您遇到的问题"),
]


# ═══════════════════════════════════════════
# 三、对话上下文
# ═══════════════════════════════════════════

@dataclass
class DialogueContext:
    """对话上下文 - 存储会话状态和槽位数据"""
    user_id: str
    intent: Optional[Intent] = None
    slots: Dict[str, str] = field(default_factory=dict)
    slot_defs: List[SlotDef] = field(default_factory=list)
    history: List[Dict[str, str]] = field(default_factory=list)
    turn_count: int = 0

    def fill_slot(self, name: str, value: str) -> bool:
        """填充槽位，返回是否成功"""
        for sd in self.slot_defs:
            if sd.name == name:
                if sd.validator and not sd.validator(value):
                    return False
                self.slots[name] = value
                return True
        return False

    def get_next_slot(self) -> Optional[SlotDef]:
        """获取下一个需要填充的槽位"""
        for sd in self.slot_defs:
            if sd.required and sd.name not in self.slots:
                return sd
        return None

    def all_slots_filled(self) -> bool:
        """检查所有必填槽位是否已填充"""
        return all(
            sd.name in self.slots
            for sd in self.slot_defs
            if sd.required
        )

    def add_message(self, role: str, text: str):
        """添加对话历史"""
        self.history.append({
            "role": role,
            "text": text,
            "time": datetime.now().isoformat()
        })

    def reset(self):
        """重置上下文（保留用户ID）"""
        self.intent = None
        self.slots.clear()
        self.slot_defs.clear()


# ═══════════════════════════════════════════
# 四、状态定义
# ═══════════════════════════════════════════

class State:
    """状态基类"""
    def handle(self, ctx: DialogueContext, user_input: str) -> 'State':
        raise NotImplementedError

    def get_response(self, ctx: DialogueContext) -> str:
        raise NotImplementedError


class WelcomeState(State):
    """欢迎状态 - 初始状态"""

    def handle(self, ctx: DialogueContext, user_input: str) -> State:
        intent = detect_intent(user_input)
        ctx.add_message("user", user_input)
        ctx.turn_count += 1

        if intent == Intent.GREET:
            return WelcomeState()  # 继续欢迎

        if intent == Intent.BYE:
            return ByeState()

        # 根据意图切换到对应状态
        if intent == Intent.BOOK:
            ctx.intent = Intent.BOOK
            ctx.slot_defs = BOOKING_SLOTS
            return CollectingState()

        if intent == Intent.COMPLAINT:
            ctx.intent = Intent.COMPLAINT
            ctx.slot_defs = COMPLAINT_SLOTS
            return CollectingState()

        if intent == Intent.QUERY:
            return QueryState()

        if intent == Intent.CANCEL:
            return CancelState()

        # 未知意图，留在欢迎状态
        return WelcomeState()

    def get_response(self, ctx: DialogueContext) -> str:
        return "您好！我是智能客服小助手 🤖\n我可以帮您：\n1️⃣ 预订机票\n2️⃣ 查询订单\n3️⃣ 投诉反馈\n4️⃣ 取消订单\n\n请问有什么可以帮您？"


class CollectingState(State):
    """信息收集状态 - 填充槽位"""

    def handle(self, ctx: DialogueContext, user_input: str) -> State:
        ctx.add_message("user", user_input)
        ctx.turn_count += 1

        # 检查是否要放弃
        if detect_intent(user_input) == Intent.BYE:
            return ByeState()

        # 检查是否要取消
        if detect_intent(user_input) == Intent.CANCEL:
            ctx.reset()
            return WelcomeState()

        # 尝试填充当前槽位
        next_slot = ctx.get_next_slot()
        if next_slot:
            if ctx.fill_slot(next_slot.name, user_input):
                # 填充成功
                if ctx.all_slots_filled():
                    return ProcessingState()
                return CollectingState()
            else:
                # 验证失败，留在当前状态（会重新提问）
                return CollectingState()

        return CollectingState()

    def get_response(self, ctx: DialogueContext) -> str:
        next_slot = ctx.get_next_slot()
        if next_slot:
            filled = len(ctx.slots)
            total = sum(1 for s in ctx.slot_defs if s.required)
            progress = "⬜" * (total - filled) + "✅" * filled
            return f"[{progress}] {next_slot.question}"
        return "信息收集中..."



class ProcessingState(State):
    """处理状态 - 执行业务逻辑"""

    def handle(self, ctx: DialogueContext, user_input: str) -> State:
        ctx.add_message("user", user_input)
        ctx.turn_count += 1
        # 处理完成后回到欢迎状态
        return WelcomeState()

    def get_response(self, ctx: DialogueContext) -> str:
        if ctx.intent == Intent.BOOK:
            return self._process_booking(ctx)
        elif ctx.intent == Intent.COMPLAINT:
            return self._process_complaint(ctx)
        return "处理完成！"

    def _process_booking(self, ctx: DialogueContext) -> str:
        """处理预订"""
        departure = ctx.slots.get("departure", "未知")
        destination = ctx.slots.get("destination", "未知")
        date = ctx.slots.get("date", "未知")
        name = ctx.slots.get("name", "未知")

        # 模拟订单号生成
        order_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"

        result = (
            f"✅ 预订成功！\n\n"
            f"📋 订单信息：\n"
            f"  订单号：{order_id}\n"
            f"  乘客：{name}\n"
            f"  航线：{departure} → {destination}\n"
            f"  日期：{date}\n\n"
            f"💡 如需修改或取消，请随时告诉我。"
        )
        ctx.reset()
        return result

    def _process_complaint(self, ctx: DialogueContext) -> str:
        """处理投诉"""
        order_id = ctx.slots.get("order_id", "未知")
        issue = ctx.slots.get("issue", "未知")

        ticket_id = f"CP{datetime.now().strftime('%Y%m%d%H%M%S')}"

        result = (
            f"📋 投诉已记录\n\n"
            f"  工单号：{ticket_id}\n"
            f"  关联订单：{order_id}\n"
            f"  问题描述：{issue}\n\n"
            f"⏰ 我们会在 24 小时内处理您的投诉，请耐心等待。\n"
            f"如有紧急情况，请拨打客服热线：400-XXX-XXXX"
        )
        ctx.reset()
        return result



class QueryState(State):
    """查询状态"""

    def handle(self, ctx: DialogueContext, user_input: str) -> State:
        ctx.add_message("user", user_input)
        ctx.turn_count += 1
        return WelcomeState()

    def get_response(self, ctx: DialogueContext) -> str:
        return (
            "📋 订单查询结果：\n\n"
            "  暂无进行中的订单。\n"
            "  历史订单请登录官网查看。\n\n"
            "还有什么可以帮您？"
        )


class CancelState(State):
    """取消状态"""

    def handle(self, ctx: DialogueContext, user_input: str) -> State:
        ctx.add_message("user", user_input)
        ctx.turn_count += 1
        return WelcomeState()

    def get_response(self, ctx: DialogueContext) -> str:
        return (
            "❌ 取消操作已受理。\n\n"
            "  如需重新预订，随时告诉我。\n\n"
            "还有什么可以帮您？"
        )


class ByeState(State):
    """告别状态"""

    def handle(self, ctx: DialogueContext, user_input: str) -> State:
        ctx.add_message("user", user_input)
        return self  # 保持告别状态

    def get_response(self, ctx: DialogueContext) -> str:
        return "感谢您的咨询，祝您生活愉快！再见 👋"


# ═══════════════════════════════════════════
# 五、对话引擎
# ═══════════════════════════════════════════

class ChatbotEngine:
    """对话引擎 - 管理状态流转"""

    def __init__(self):
        self.sessions: Dict[str, DialogueContext] = {}

    def get_context(self, user_id: str) -> DialogueContext:
        """获取或创建用户上下文"""
        if user_id not in self.sessions:
            self.sessions[user_id] = DialogueContext(user_id=user_id)
        return self.sessions[user_id]

    def chat(self, user_id: str, message: str) -> str:
        """处理用户消息，返回机器人回复"""
        ctx = self.get_context(user_id)

        # 获取当前状态（首次对话为 WelcomeState）
        if not hasattr(ctx, '_state') or ctx._state is None:
            ctx._state = WelcomeState()

        # 状态处理
        current_state = ctx._state
        new_state = current_state.handle(ctx, message)

        # 状态转换
        old_state_name = type(current_state).__name__
        ctx._state = new_state
        new_state_name = type(new_state).__name__

        # 记录机器人回复
        response = new_state.get_response(ctx)
        ctx.add_message("bot", response)

        # 调试日志
        if old_state_name != new_state_name:
            print(f"  [状态转换] {old_state_name} → {new_state_name}")

        return response

    def get_history(self, user_id: str) -> List[Dict]:
        """获取对话历史"""
        ctx = self.get_context(user_id)
        return ctx.history


# ═══════════════════════════════════════════
# 六、主程序 - 交互式客服
# ═══════════════════════════════════════════

def main():
    """交互式客服聊天机器人"""
    print("=" * 60)
    print("🤖 智能客服系统 v1.0")
    print("=" * 60)
    print("输入消息开始对话，输入 'quit' 退出")
    print("-" * 60)

    engine = ChatbotEngine()
    user_id = "demo_user"

    # 打印欢迎语
    ctx = engine.get_context(user_id)
    print(f"\n🤖 {WelcomeState().get_response(ctx)}\n")

    while True:
        try:
            user_input = input("👤 您：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\n👋 再见！")
            break

        response = engine.chat(user_id, user_input)
        print(f"\n🤖 客服：{response}\n")

        # 检查是否进入告别状态
        ctx = engine.get_context(user_id)
        if isinstance(ctx._state, ByeState):
            break

    # 打印对话历史
    print("\n" + "=" * 60)
    print("📝 对话历史")
    print("=" * 60)
    for msg in engine.get_history(user_id):
        role = "👤" if msg["role"] == "user" else "🤖"
        print(f"{role} {msg['text'][:80]}...")


if __name__ == "__main__":
    main()
