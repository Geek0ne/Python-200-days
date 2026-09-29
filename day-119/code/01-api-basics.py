"""
Day 119 - 大模型 API 调用：基础用法
=====================================
演示 OpenAI / DeepSeek API 的基本调用方式
"""

import os
import json

# ─── 1. 客户端初始化 ───
# 方式一：使用环境变量（推荐）
# export OPENAI_API_KEY="sk-xxx"
# client = openai.OpenAI()

# 方式二：直接指定（不推荐在生产环境使用）
import openai

# 演示用 - DeepSeek（更便宜，适合学习）
client = openai.OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", "your-key-here"),
    base_url="https://api.deepseek.com/v1"
)

# ─── 2. 最简单的调用 ───
def simple_chat(prompt: str) -> str:
    """最基础的单轮对话"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content


# ─── 3. 带 System Prompt 的调用 ───
def role_play_chat(user_input: str) -> str:
    """使用 System Prompt 设定角色"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": "你是一位友好的 Python 编程导师，用简洁的中文回答问题，适当使用 emoji。"
            },
            {"role": "user", "content": user_input}
        ],
        temperature=0.7,
        max_tokens=500
    )
    return response.choices[0].message.content


# ─── 4. 多轮对话 ───
def multi_turn_chat():
    """演示多轮对话的消息管理"""
    messages = [
        {"role": "system", "content": "你是一个简洁的翻译助手，只输出翻译结果，不加解释。"}
    ]
    
    # 模拟多轮对话
    conversations = [
        "把'人生苦短，我用Python'翻译成英文",
        "再翻译成日文",
        "用更口语化的方式翻译第一句"
    ]
    
    for user_input in conversations:
        print(f"\n👤 用户: {user_input}")
        
        messages.append({"role": "user", "content": user_input})
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        
        assistant_reply = response.choices[0].message.content
        print(f"🤖 AI: {assistant_reply}")
        
        # 把 AI 回复也加入历史（保持上下文）
        messages.append({"role": "assistant", "content": assistant_reply})
    
    print(f"\n📋 完整对话历史 ({len(messages)} 条消息):")
    for msg in messages:
        print(f"  [{msg['role']}] {msg['content'][:50]}...")


# ─── 5. 流式输出 ───
def stream_chat(prompt: str):
    """流式输出 - 逐 token 打印（类似 ChatGPT 的打字效果）"""
    print(f"\n👤 用户: {prompt}")
    print("🤖 AI: ", end="", flush=True)
    
    stream = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        stream=True  # 开启流式
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            print(text, end="", flush=True)
            full_response += text
    
    print()  # 换行
    return full_response


# ─── 6. 查看 Token 使用情况 ───
def check_tokens(prompt: str):
    """查看请求的 token 用量"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    
    usage = response.usage
    print(f"\n📊 Token 用量:")
    print(f"  Prompt tokens:     {usage.prompt_tokens}")
    print(f"  Completion tokens: {usage.completion_tokens}")
    print(f"  Total tokens:      {usage.total_tokens}")
    print(f"  回复内容: {response.choices[0].message.content[:80]}...")


# ─── 主程序 ───
if __name__ == "__main__":
    print("=" * 50)
    print("Day 119 - 大模型 API 基础调用")
    print("=" * 50)
    
    # 注意：实际运行需要有效的 API Key
    print("\n💡 以下为示例代码，实际运行需要设置 DEEPSEEK_API_KEY 环境变量")
    print("   export DEEPSEEK_API_KEY='your-api-key'")
    print("   python3 01-api-basics.py")
    
    # 取消下面的注释来实际运行
    # print("\n--- 1. 简单调用 ---")
    # result = simple_chat("用一句话解释 Python 是什么")
    # print(f"回答: {result}")
    
    # print("\n--- 2. 角色扮演 ---")
    # result = role_play_chat("列表推导式是什么？")
    # print(f"回答: {result}")
    
    # print("\n--- 3. 多轮对话 ---")
    # multi_turn_chat()
    
    # print("\n--- 4. 流式输出 ---")
    # stream_chat("写一个 Python 快速排序")
    
    # print("\n--- 5. Token 统计 ---")
    # check_tokens("Python 的 GIL 是什么？")
