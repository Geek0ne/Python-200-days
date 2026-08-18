# Day 119 — 大模型 API 调用

> 🎯 **今日目标**：掌握大模型 API 的调用方式，学会 Prompt Engineering 技巧，理解 Function Calling 机制，并实战构建一个智能助手。

---

## 一、概述：为什么需要大模型 API？

传统编程需要人来定义每一条规则，而大模型（LLM）通过海量数据训练获得了强大的语言理解和生成能力。通过 API 调用，我们可以：

- **零训练成本**：直接使用预训练模型的能力
- **弹性扩展**：按需调用，无需自建 GPU 集群
- **快速迭代**：几行代码就能集成 AI 能力

```
┌─────────────────────────────────────────────┐
│              传统开发 vs API 调用              │
├──────────────────┬──────────────────────────┤
│   传统方式        │   API 调用方式            │
├──────────────────┼──────────────────────────┤
│ 收集数据 → 训练   │ 直接调用 API              │
│ 部署模型 → 维护   │ 无需部署                  │
│ 耗时数周/月       │ 几分钟集成                │
│ 需要 GPU/算力     │ 只需 HTTP 请求            │
└──────────────────┴──────────────────────────┘
```

---

## 二、OpenAI / DeepSeek API 调用

### 2.1 核心概念

| 概念 | 说明 |
|------|------|
| **API Key** | 认证密钥，每个请求必须携带 |
| **Model** | 模型名称，如 `gpt-4o`、`deepseek-chat` |
| **Messages** | 对话消息列表，包含 role 和 content |
| **Temperature** | 生成随机性（0=确定，1=创造性） |
| **Max Tokens** | 最大生成 token 数 |
| **Stream** | 是否流式返回（逐 token 输出） |

### 2.2 API 请求结构

```
┌──────────────────────────────────────────────────┐
│                   HTTP POST 请求                   │
├──────────────────────────────────────────────────┤
│ URL: https://api.openai.com/v1/chat/completions  │
│ Headers:                                         │
│   Authorization: Bearer sk-xxx                   │
│   Content-Type: application/json                 │
├──────────────────────────────────────────────────┤
│ Body:                                            │
│   {                                              │
│     "model": "gpt-4o",                           │
│     "messages": [                                │
│       {"role": "system", "content": "..."},       │
│       {"role": "user", "content": "..."}          │
│     ],                                           │
│     "temperature": 0.7                           │
│   }                                              │
└──────────────────────────────────────────────────┘
```

### 2.3 消息角色（Role）

| Role | 作用 | 类比 |
|------|------|------|
| `system` | 设定 AI 的行为规则 | 人设/性格设定 |
| `user` | 用户的输入 | 用户提问 |
| `assistant` | AI 的回复 | AI 回答 |
| `function` | 工具调用的结果 | 工具返回值 |

```python
# 消息流转示意
system  →  "你是一个翻译助手"        # 设定角色
user    →  "把'你好'翻译成英文"       # 用户提问
assistant → "Hello"                   # AI 回答
user    →  "再翻译成日文"             # 后续追问
assistant → "こんにちは"              # AI 继续回答
```

---

## 三、Prompt Engineering 技巧

### 3.1 什么是 Prompt Engineering？

Prompt Engineering 是设计和优化输入提示（Prompt）以获得更好 AI 输出的技术。核心原则：

```
输入质量 → 输出质量

差的 Prompt: "写个故事"
好的 Prompt: "写一个200字的科幻短篇，主角是一个在火星上种土豆的程序员，
              风格幽默，包含反转结局"
```

### 3.2 六大核心技巧

#### 1️⃣ 角色设定（Role Prompting）

```
你是一位资深的 Python 高级工程师，拥有 15 年开发经验。
请用专业但易懂的方式解释以下概念...
```

**为什么有效**：角色设定让模型锁定知识领域，输出更专业。

#### 2️⃣ Few-Shot 示例（提供范例）

```
请按以下格式翻译：

英文: Good morning → 中文: 早上好
英文: Thank you → 中文: 谢谢
英文: How are you → 中文:
```

**为什么有效**：示例比描述更精确，模型能从范例中学习模式。

#### 3️⃣ 链式思考（Chain of Thought）

```
请一步步思考：
1. 首先分析问题...
2. 然后考虑...
3. 最后得出结论...
```

**为什么有效**：强制模型展示推理过程，减少跳跃式错误。

#### 4️⃣ 结构化输出

```
请以 JSON 格式输出：
{
  "name": "姓名",
  "age": 数字,
  "skills": ["技能1", "技能2"]
}
```

**为什么有效**：明确输出格式，便于程序解析。

#### 5️⃣ 约束与边界

```
注意：
- 不要编造信息，如果不确定请说"我不确定"
- 回答控制在 100 字以内
- 不要使用专业术语
```

**为什么有效**：约束减少幻觉，控制输出长度和风格。

#### 6️⃣ 分步骤指令

```
任务：分析一段代码
步骤：
1. 先阅读代码，理解功能
2. 找出潜在的 bug
3. 给出修复建议
4. 提供优化后的代码
```

**为什么有效**：分步骤让复杂任务条理清晰，减少遗漏。

---

## 四、Function Calling（函数调用）

### 4.1 核心机制

Function Calling 让大模型能够"调用"外部工具/函数。模型本身不执行函数，而是**生成调用指令**，由你的代码执行后将结果返回给模型。

```
┌──────┐    ① 用户提问     ┌───────┐
│ 用户  │ ──────────────→ │  LLM  │
└──────┘                  └───┬───┘
                              │ ② 返回函数调用指令
                              │    {"name": "get_weather",
                              │     "args": {"city": "北京"}}
                              ▼
                        ┌──────────┐
                        │ 你的代码  │  ③ 执行函数
                        └────┬─────┘
                             │ ④ 获取结果: {"temp": 25, "sunny": true}
                             ▼
                        ┌───────┐  ⑤ 将结果发回 LLM
                        │  LLM  │ ──→ 生成自然语言回复
                        └───┬───┘
                            │ ⑥ "北京今天25°C，天气晴朗"
                            ▼
                        ┌──────┐
                        │ 用户  │
                        └──────┘
```

### 4.2 函数定义格式

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "温度单位"
                }
            },
            "required": ["city"]
        }
    }
}]
```

### 4.3 调用流程

```python
import openai

client = openai.OpenAI()

# 1. 发送消息 + 工具定义
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
    tools=tools,
    tool_choice="auto"  # 让模型决定是否调用工具
)

# 2. 检查是否有函数调用
msg = response.choices[0].message
if msg.tool_calls:
    # 3. 执行函数
    result = get_weather(**msg.tool_calls[0].function.arguments)
    
    # 4. 将结果发回
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": "北京今天天气怎么样？"},
            msg,  # assistant 消息（含 tool_calls）
            {"role": "tool", "tool_call_id": msg.tool_calls[0].id,
             "content": json.dumps(result)}
        ]
    )
```

---

## 五、API 速查表

### 5.1 OpenAI Python SDK

```python
import openai

# 创建客户端（推荐方式）
client = openai.OpenAI(api_key="sk-xxx")

# 基础调用
response = client.chat.completions.create(
    model="gpt-4o",               # 模型名称
    messages=[...],                # 消息列表
    temperature=0.7,               # 随机性 (0-2)
    max_tokens=1000,               # 最大输出长度
    top_p=1.0,                     # 核采样
    frequency_penalty=0.0,         # 频率惩罚
    presence_penalty=0.0,          # 存在惩罚
    stream=False,                  # 是否流式
    tools=tools,                   # 工具列表
    tool_choice="auto",            # 工具选择策略
)

# 获取回复
print(response.choices[0].message.content)
```

### 5.2 DeepSeek API（兼容 OpenAI）

```python
import openai

# DeepSeek 完全兼容 OpenAI SDK
client = openai.OpenAI(
    api_key="your-deepseek-key",
    base_url="https://api.deepseek.com/v1"  # 指向 DeepSeek
)

# 调用方式完全一样
response = client.chat.completions.create(
    model="deepseek-chat",  # 或 deepseek-coder
    messages=[{"role": "user", "content": "你好"}]
)
```

### 5.3 关键参数对比

| 参数 | 作用 | 推荐值 | 注意事项 |
|------|------|--------|---------|
| `temperature` | 控制随机性 | 0-0.3（精确）/ 0.7-1（创意） | 越高越随机 |
| `max_tokens` | 输出上限 | 根据需求设 | 注意 token 成本 |
| `top_p` | 核采样 | 1.0 | 通常与 temperature 二选一 |
| `frequency_penalty` | 降低重复 | 0-0.5 | 防止车轱辘话 |
| `presence_penalty` | 提升多样性 | 0-1.5 | 鼓励新话题 |
| `stream` | 流式输出 | True（体验好） | 需要特殊处理 |

---

## 六、实战：智能助手

### 6.1 项目架构

```
┌─────────────────────────────────────────────┐
│                智能助手架构                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────┐   ┌──────────┐   ┌─────────┐ │
│  │ 用户输入 │ → │ Prompt   │ → │ LLM API │ │
│  └─────────┘   │ 模板     │   └────┬────┘ │
│                └──────────┘        │       │
│                                    ▼       │
│                              ┌──────────┐  │
│                              │ 工具调用  │  │
│                              │ (可选)    │  │
│                              └────┬─────┘  │
│                                   ▼        │
│                              ┌──────────┐  │
│                              │ 输出格式化│  │
│                              └────┬─────┘  │
│                                   ▼        │
│                              ┌──────────┐  │
│                              │ 用户展示  │  │
│                              └──────────┘  │
└─────────────────────────────────────────────┘
```

### 6.2 完整代码示例

见 `code/03-smart-assistant.py`，包含：
- 多轮对话管理
- Prompt 模板系统
- 工具函数集成
- 流式输出支持
- 上下文窗口管理

---

## 七、避坑指南

### 常见错误

```python
# ❌ 错误 1：每次创建新客户端
for q in questions:
    client = openai.OpenAI()  # 浪费资源！
    response = client.chat.completions.create(...)

# ✅ 正确：复用客户端
client = openai.OpenAI()  # 创建一次
for q in questions:
    response = client.chat.completions.create(...)

# ❌ 错误 2：没有处理 API 错误
response = client.chat.completions.create(...)  # 可能抛异常！

# ✅ 正确：加 try-except
import time
for attempt in range(3):
    try:
        response = client.chat.completions.create(...)
        break
    except openai.RateLimitError:
        time.sleep(2 ** attempt)  # 指数退避
    except openai.APIError as e:
        print(f"API 错误: {e}")

# ❌ 错误 3：System Prompt 放在 User 消息里
messages = [{"role": "user", "content": "你是翻译助手。把你好翻译成英文"}]

# ✅ 正确：分开角色
messages = [
    {"role": "system", "content": "你是专业的翻译助手"},
    {"role": "user", "content": "把'你好'翻译成英文"}
]
```

### Token 成本控制

```
┌─────────────────────────────────────┐
│          Token 计费示意              │
├─────────────────────────────────────┤
│ 1 个中文字 ≈ 1-2 tokens            │
│ 1 个英文词 ≈ 1 token               │
│ 1 个标点   ≈ 0.5-1 token           │
│                                      │
│ 💡 优化策略：                        │
│ • 精简 System Prompt                │
│ • 控制历史消息轮数                   │
│ • 设置合理的 max_tokens             │
│ • 使用 GPT-4o-mini 处理简单任务     │
└─────────────────────────────────────┘
```

---

## 八、思考题

1. **为什么 System Prompt 要放在消息列表最前面？如果放在最后会怎样？**
   > 提示：思考 LLM 处理消息的顺序和注意力机制。

2. **Temperature 和 Top_p 都能控制随机性，为什么需要两个参数？分别在什么场景下使用？**
   > 提示：Temperature 改变概率分布形状，Top_p 截断分布尾部。

3. **Function Calling 中，如果模型返回了错误的函数参数（比如把"北京"传成了数字），你的代码应该如何处理？**
   > 提示：思考参数验证和错误恢复机制。

4. **多轮对话中，如果上下文超过了模型的 token 限制，你会采用什么策略来管理对话历史？**
   > 提示：考虑滑动窗口、摘要压缩、重要性评分等方案。

5. **OpenAI 和 DeepSeek 的 API 几乎完全兼容，这种设计有什么好处？如果明天出了一个新模型 API 不兼容怎么办？**
   > 提示：思考抽象层和适配器模式的价值。

---

## 参考资源

- [OpenAI API 文档](https://platform.openai.com/docs)
- [DeepSeek API 文档](https://platform.deepseek.com/api-docs)
- [Prompt Engineering Guide](https://www.promptingguide.ai/zh)
- [OpenAI Cookbook](https://cookbook.openai.com/)
