"""
Day 119 - 避坑指南与错误处理
=============================
大模型 API 调用中的常见陷阱和最佳实践
"""

import os
import time
import json
from functools import wraps
from typing import Optional

import openai


# ─── 1. 重试装饰器（指数退避）───

def retry_with_backoff(max_retries=3, base_delay=1.0, exceptions=(openai.RateLimitError,)):
    """带指数退避的自动重试装饰器
    
    原理：遇到 429 等临时错误时，等待时间指数增长
    1s → 2s → 4s → ...，避免雪崩效应
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    print(f"  ⏳ 重试 {attempt + 1}/{max_retries}，等待 {delay}s... ({type(e).__name__})")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator


# ─── 2. 安全的 API 调用封装 ───

class SafeAPIClient:
    """带完整错误处理的 API 客户端"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)
    
    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def chat(self, messages: list, model: str = "deepseek-chat", **kwargs) -> Optional[dict]:
        """安全的聊天请求"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model
            }
        except openai.BadRequestError as e:
            print(f"❌ 请求错误（参数问题）: {e}")
            return None
        except openai.AuthenticationError:
            print("❌ 认证失败：请检查 API Key 是否正确")
            return None
        except openai.PermissionDeniedError:
            print("❌ 权限不足：当前 API Key 无权访问该模型")
            return None
        except openai.NotFoundError:
            print("❌ 模型不存在：请检查模型名称")
            return None
        except openai.APIStatusError as e:
            print(f"❌ API 错误 (HTTP {e.status_code}): {e.message}")
            return None


# ─── 3. 消息长度检查 ───

def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中文约1字=1.5token，英文约1词=1token）"""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.3)


def check_message_budget(messages: list, max_tokens: int = 8000) -> tuple[bool, str]:
    """检查消息列表是否超出 token 预算
    
    返回: (是否安全, 警告信息)
    """
    total = sum(estimate_tokens(m.get("content", "")) for m in messages)
    
    if total > max_tokens * 0.8:
        return False, f"⚠️ 消息预估 {total} tokens，接近上限 {max_tokens}"
    return True, f"✅ 消息预估 {total} tokens，安全"


# ─── 4. 常见错误演示 ───

def demo_common_mistakes():
    """演示常见错误及修复"""
    
    print("=" * 60)
    print("🚫 常见错误 1：每次创建新客户端")
    print("=" * 60)
    
    # ❌ 错误方式
    print("""
❌ 错误代码：
for question in questions:
    client = openai.OpenAI()  # 每次都创建！浪费连接池
    response = client.chat.completions.create(...)

✅ 正确方式：
client = openai.OpenAI()  # 创建一次，复用
for question in questions:
    response = client.chat.completions.create(...)
""")
    
    print("=" * 60)
    print("🚫 常见错误 2：没有处理 rate limit")
    print("=" * 60)
    
    print("""
❌ 错误代码：
response = client.chat.completions.create(...)  # 直接调用，无保护

✅ 正确方式：
import time
for attempt in range(3):
    try:
        response = client.chat.completions.create(...)
        break
    except openai.RateLimitError:
        time.sleep(2 ** attempt)  # 1s → 2s → 4s
    except openai.APIError as e:
        print(f"API error: {e}")
        break
""")
    
    print("=" * 60)
    print("🚫 常见错误 3：System Prompt 位置错误")
    print("=" * 60)
    
    print("""
❌ 错误代码：
messages = [{"role": "user", "content": "你是翻译助手。把'你好'翻译成英文"}]

✅ 正确方式：
messages = [
    {"role": "system", "content": "你是专业的翻译助手"},
    {"role": "user", "content": "把'你好'翻译成英文"}
]
""")
    
    print("=" * 60)
    print("🚫 常见错误 4：上下文无限增长")
    print("=" * 60)
    
    print("""
❌ 错误代码：
messages.append(user_msg)
messages.append(assistant_msg)
# 消息越来越多，最终超出 token 限制！

✅ 正确方式：
MAX_MESSAGES = 20
messages.append(user_msg)
messages.append(assistant_msg)
if len(messages) > MAX_MESSAGES:
    messages = [messages[0]] + messages[-(MAX_MESSAGES-1):]
    # 保留 system prompt + 最近 N 条
""")


# ─── 5. 流式输出安全处理 ───

def safe_stream_call(client, messages, model="deepseek-chat"):
    """安全的流式调用，处理各种异常"""
    try:
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )
        
        full_content = ""
        for chunk in stream:
            try:
                if chunk.choices and chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    print(text, end="", flush=True)
                    full_content += text
            except AttributeError:
                # 某些 chunk 可能没有 delta
                continue
        
        print()
        return full_content
        
    except openai.APIError as e:
        print(f"\n❌ 流式调用出错: {e}")
        return None
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
        return full_content if full_content else None


# ─── 主程序 ───

if __name__ == "__main__":
    print("Day 119 - 避坑指南与错误处理\n")
    
    # 演示常见错误
    demo_common_mistakes()
    
    # 演示 token 预算检查
    print("=" * 60)
    print("📊 Token 预算检查演示")
    print("=" * 60)
    
    test_messages = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "Python 是什么？" * 100},  # 模拟长消息
        {"role": "assistant", "content": "Python 是一种编程语言" * 50},
    ]
    
    safe, msg = check_message_budget(test_messages)
    print(f"  {msg}")
    
    print("\n" + "=" * 60)
    print("💡 要实际运行 API 调用，请设置环境变量：")
    print("   export DEEPSEEK_API_KEY='your-key'")
    print("=" * 60)
