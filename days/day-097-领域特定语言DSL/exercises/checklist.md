# Day 097 — 领域特定语言（DSL）练习清单

## ✅ 今日完成清单

- [ ] 理解 DSL 的定义、分类（外部/内部/中间）
- [ ] 掌握 Python 构建 DSL 的 5 大核心技巧
- [ ] 阅读并理解装饰器 DSL 示例
- [ ] 阅读并理解上下文管理器 DSL 示例
- [ ] 阅读并理解链式调用 DSL 示例
- [ ] 完成规则引擎 DSL 代码
- [ ] 完成配置 DSL 代码
- [ ] 完成练习题

---

## 📝 基础练习

### 练习 1：简单的表单验证 DSL

用装饰器 + 链式调用实现一个表单验证 DSL：

```python
# 期望的 DSL 语法：
validator = (Validator()
    .field("name").required().min_length(2).max_length(50)
    .field("email").required().email()
    .field("age").required().between(0, 150)
    .field("password").required().min_length(8))

result = validator.validate({
    "name": "Alice",
    "email": "alice@example.com",
    "age": 25,
    "password": "secret123"
})
```

**要求**：
1. 实现 `Validator` 类
2. 实现 `field()`、`required()`、`min_length()`、`max_length()`、`email()`、`between()` 方法
3. `validate()` 方法返回验证结果（成功/失败 + 错误信息）

### 练习 2：状态机 DSL

用链式调用实现一个简单的状态机 DSL：

```python
# DSL 语法：
fsm = (StateMachine("idle")
    .on("start").goto("running")
    .on("stop").goto("idle")
    .on("error").goto("error_state")
    .on("retry").from_state("error_state").goto("running"))

fsm.trigger("start")  # idle → running
fsm.trigger("stop")   # running → idle
```

**要求**：
1. 实现 `StateMachine` 类
2. 支持 `on().goto()` 和 `on().from_state().goto()` 语法
3. 处理非法状态转换

---

## 🔥 进阶挑战

### 挑战 1：模板 DSL

设计一个简单的模板语言 DSL，支持变量替换和条件：

```python
# DSL 语法：
template = (Template("Hello {{name}}!")
    .if_("age > 18").then("You are an adult.")
    .else_("You are a minor.")
    .render({"name": "Alice", "age": 25}))
# 输出: "Hello Alice! You are an adult."
```

### 挑战 2：测试 DSL

设计一个测试断言 DSL，让测试代码读起来像自然语言：

```python
# DSL 语法：
(expect(42)
    .to_equal(42)
    .to_be_greater_than(10)
    .to_be_less_than(100))

(expect("hello")
    .to_contain("ell")
    .to_start_with("he")
    .to_have_length(5))
```

### 挑战 3：API 客户端 DSL

为 HTTP API 设计一个流畅的客户端 DSL：

```python
# DSL 语法：
response = (API("https://api.example.com")
    .header("Authorization", "Bearer xxx")
    .get("/users")
    .query_params(page=1, limit=10)
    .timeout(30)
    .retry(3)
    .execute())
```

---

## 💡 思考题

1. **设计原则**：DSL 的「最小惊讶原则」是什么？在设计 DSL 时如何遵循？

2. **可测试性**：内部 DSL 的代码如何测试？与外部 DSL 的测试策略有何不同？

3. **性能考量**：Python 内部 DSL 的性能瓶颈在哪里？如何优化？

4. **团队协作**：如何让团队成员接受并使用你设计的 DSL？需要什么文档？

5. **DSL 与框架**：Flask、Django、SQLAlchemy 都是 DSL 吗？它们的 DSL 设计各有什么特点？

---

> 🎯 **完成标准**：至少完成 2 个基础练习 + 1 个思考题
