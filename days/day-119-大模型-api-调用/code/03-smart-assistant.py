"""
Day 119 - 实战：智能助手
========================
一个完整的智能助手，支持：
- 多轮对话
- Function Calling
- 流式输出
- 上下文管理
- 多工具集成
"""

import os
import json
import time
from datetime import datetime
from typing import Callable

import openai


# ─── 工具函数定义 ───

def get_current_time(timezone: str = "Asia/Shanghai") -> dict:
    """获取当前时间"""
    now = datetime.now()
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "timezone": timezone
    }


def calculate(expression: str) -> dict:
    """安全的数学计算"""
    try:
        # 仅允许安全的数学运算
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return {"error": "不允许的字符", "expression": expression}
        
        result = eval(expression)  # ⚠️ 生产环境应使用 ast.literal_eval 或 sympy
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e), "expression": expression}


def search_web_stub(query: str) -> dict:
    """模拟网络搜索（实际应接入搜索 API）"""
    # 实际项目中接入 Google/Bing API
    return {
        "query": query,
        "results": [
            {"title": f"搜索结果: {query}", "snippet": "这是模拟的搜索结果..."},
        ],
        "note": "这是模拟搜索，实际请接入搜索 API"
    }


def write_file(filepath: str, content: str) -> dict:
    """写入文件"""
    try:
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "filepath": filepath, "size": len(content)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 工具注册表 ───

TOOLS_REGISTRY: dict[str, dict] = {
    "get_current_time": {
        "function": get_current_time,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前日期和时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "时区，默认 Asia/Shanghai"
                        }
                    },
                    "required": []
                }
            }
        }
    },
    "calculate": {
        "function": calculate,
        "schema": {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "执行数学计算，支持加减乘除和括号",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "数学表达式，如 '(3 + 5) * 2'"
                        }
                    },
                    "required": ["expression"]
                }
            }
        }
    },
    "search_web": {
        "function": search_web_stub,
        "schema": {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "搜索互联网获取信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    },
    "write_file": {
        "function": write_file,
        "schema": {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "将内容写入指定文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filepath": {
                            "type": "string",
                            "description": "文件路径"
                        },
                        "content": {
                            "type": "string",
                            "description": "要写入的内容"
                        }
                    },
                    "required": ["filepath", "content"]
                }
            }
        }
    }
}


# ─── 智能助手核心类 ───

class SmartAssistant:
    """支持 Function Calling 的智能助手"""
    
    SYSTEM_PROMPT = """你是一个功能强大的智能助手，名叫小智。

你的能力：
1. 回答各种问题，提供准确、有用的信息
2. 使用工具获取实时信息（时间、搜索、计算等）
3. 编写和保存代码/文件

使用原则：
- 需要实时信息时，主动使用工具获取
- 回答要简洁明了，重点突出
- 遇到不确定的问题，诚实说明
- 中文回复为主，除非用户要求其他语言
"""
    
    def __init__(self, model: str = "deepseek-chat", max_history: int = 20):
        self.client = openai.OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY", "your-key-here"),
            base_url="https://api.deepseek.com/v1"
        )
        self.model = model
        self.max_history = max_history
        self.messages: list[dict] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        self.tool_schemas = [t["schema"] for t in TOOLS_REGISTRY.values()]
    
    def _trim_history(self):
        """保持上下文窗口在合理范围内"""
        # 保留 system + 最近 N 条消息
        if len(self.messages) > self.max_history + 1:  # +1 for system
            # 保留 system prompt 和最后 max_history 条消息
            self.messages = [self.messages[0]] + self.messages[-(self.max_history):]
    
    def _execute_tool(self, name: str, arguments: str) -> str:
        """执行工具调用"""
        tool_info = TOOLS_REGISTRY.get(name)
        if not tool_info:
            return json.dumps({"error": f"未知工具: {name}"})
        
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError:
            args = {}
        
        result = tool_info["function"](**args)
        return json.dumps(result, ensure_ascii=False)
    
    def chat(self, user_input: str, stream: bool = False) -> str:
        """发送消息并获取回复（支持 Function Calling）"""
        
        self.messages.append({"role": "user", "content": user_input})
        self._trim_history()
        
        # 最多重试 3 次（处理 Function Calling 循环）
        for _ in range(5):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tool_schemas if self.tool_schemas else None,
                    tool_choice="auto",
                    stream=stream
                )
            except openai.RateLimitError:
                print("⏳ 触发速率限制，等待 5 秒...")
                time.sleep(5)
                continue
            except openai.APIError as e:
                return f"⚠️ API 错误: {e}"
            
            if stream:
                return self._handle_stream(response)
            
            message = response.choices[0].message
            
            # 没有工具调用，直接返回
            if not message.tool_calls:
                self.messages.append({"role": "assistant", "content": message.content})
                return message.content
            
            # 有工具调用
            self.messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
            })
            
            # 执行每个工具调用
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                print(f"  🔧 调用工具: {tool_name}({tool_args[:50]}...)")
                
                result = self._execute_tool(tool_name, tool_args)
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
        
        return "⚠️ 工具调用循环次数过多"
    
    def _handle_stream(self, response) -> str:
        """处理流式输出"""
        print("🤖: ", end="", flush=True)
        full_content = ""
        tool_calls_data = {}
        
        for chunk in response:
            delta = chunk.choices[0].delta
            
            # 流式文本输出
            if delta.content:
                print(delta.content, end="", flush=True)
                full_content += delta.content
            
            # 流式工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name if tc.function and tc.function.name else "",
                            "arguments": tc.function.arguments if tc.function else ""
                        }
                    else:
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["name"] += tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc.function.arguments
        
        if full_content:
            print()  # 换行
        
        # 处理流式工具调用
        if tool_calls_data:
            self.messages.append({
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]}
                    } for tc in tool_calls_data.values()
                ]
            })
            
            for tc in tool_calls_data.values():
                print(f"  🔧 调用工具: {tc['name']}")
                result = self._execute_tool(tc["name"], tc["arguments"])
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result
                })
            
            # 再次调用获取最终回复
            return self.chat("", stream=False)
        
        self.messages.append({"role": "assistant", "content": full_content})
        return full_content
    
    def reset(self):
        """重置对话"""
        self.messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]


# ─── 主程序 ───

def main():
    """交互式智能助手"""
    print("=" * 50)
    print("🤖 智能助手 v1.0")
    print("=" * 50)
    print("支持功能：问答、时间查询、数学计算、搜索、文件操作")
    print("命令：quit=退出, reset=重置对话, history=查看历史")
    print("=" * 50)
    
    assistant = SmartAssistant()
    
    while True:
        try:
            user_input = input("\n👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() == "quit":
            print("👋 再见！")
            break
        
        if user_input.lower() == "reset":
            assistant.reset()
            print("🔄 对话已重置")
            continue
        
        if user_input.lower() == "history":
            print(f"\n📋 对话历史 ({len(assistant.messages)} 条):")
            for msg in assistant.messages:
                role = msg["role"]
                content = msg.get("content", "") or ""
                print(f"  [{role}] {content[:80]}...")
            continue
        
        # 正常对话
        response = assistant.chat(user_input, stream=True)
        
        if not response:
            continue
        
        print(f"\n\n💡 (使用了 {len(assistant.messages)} 条消息的上下文)")


# ─── 演示模式 ───

def demo():
    """非交互式演示"""
    print("=" * 50)
    print("🤖 智能助手 - 演示模式")
    print("=" * 50)
    
    assistant = SmartAssistant()
    
    demo_queries = [
        "现在几点了？今天星期几？",
        "帮我算一下 (123 + 456) * 789 等于多少",
        "搜索一下 Python 3.12 有什么新特性",
        "把 'print(\"Hello World\")' 保存到 hello.py 文件",
    ]
    
    for query in demo_queries:
        print(f"\n{'─' * 40}")
        print(f"👤 用户: {query}")
        print(f"{'─' * 40}")
        response = assistant.chat(query)
        print(f"🤖 助手: {response}")


if __name__ == "__main__":
    import sys
    
    if "--demo" in sys.argv:
        demo()
    else:
        main()
