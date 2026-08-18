# Day 119 练习 — 大模型 API 调用

## ✅ 今日完成清单

- [ ] 理解 OpenAI/DeepSeek API 的调用方式
- [ ] 掌握 System/User/Assistant 消息角色的使用
- [ ] 理解 Temperature、Max Tokens 等参数的含义
- [ ] 掌握 6 大 Prompt Engineering 技巧
- [ ] 理解 Function Calling 的工作流程
- [ ] 完成基础练习题
- [ ] 完成进阶挑战题

---

## 📝 基础练习

### 练习 1：单轮对话封装
编写一个函数 `ask_ai(prompt, system_prompt=None)`，封装 OpenAI API 调用，支持可选的 system prompt。函数应处理 API 错误并返回字符串结果。

```python
# 测试用例
print(ask_ai("Python 的列表推导式是什么？"))
print(ask_ai("用 Python 实现", system_prompt="你是 Python 专家"))
```

### 练习 2：Prompt 模板渲染器
实现一个 `PromptRenderer` 类，支持：
- 使用 `{变量名}` 语法定义变量
- `render(**kwargs)` 方法替换变量
- 缺少必需变量时抛出异常

```python
template = PromptRenderer("你是{role}，请回答：{question}")
print(template.render(role="翻译专家", question="Hello 是什么意思？"))
```

### 练习 3：对话历史管理器
编写一个 `ChatHistory` 类，管理多轮对话：
- 维护 messages 列表（包含 system prompt）
- 自动添加 user/assistant 消息
- 当消息超过限制时，自动截断旧消息（保留 system prompt）

---

## 🚀 进阶挑战

### 挑战 1：Streaming 打字机效果
修改 `SmartAssistant` 类，实现逐字打印的流式效果（参考 `code/03-smart-assistant.py`），并在回复完成后显示 token 用量。

### 挑战 2：多工具链式调用
扩展助手功能，让模型能连续调用多个工具。例如：
- "搜索 Python 3.12 新特性，把结果保存到文件"
  → 先调用 search_web，再调用 write_file

### 挑战 3：自定义工具注册
实现一个 `@register_tool` 装饰器，自动将函数注册为可用工具：
```python
@register_tool(description="查询天气")
def get_weather(city: str) -> dict:
    return {"city": city, "temp": 25}
```

### 挑战 4：Token 预算管理
实现一个 TokenBudget 类，在发送请求前估算 token 用量，如果超出预算则自动截断历史消息：
```python
budget = TokenBudget(max_tokens=4000)
budget.estimate(messages)  # 预估
budget.trim(messages)      # 截断
```
