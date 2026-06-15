# Day 017 — 异常处理：完成清单与练习题

## ✅ 完成清单

### 理论学习

- [ ] 理解 `try/except/else/finally` 四段结构的执行流
- [ ] 区分 EAFP 和 LBYL 两种编码风格
- [ ] 理解异常传播链的向上查找机制
- [ ] 掌握 `raise`, `raise ... from`, `raise ... from None` 的区别
- [ ] 理解 `finally` 在 `return/break/continue` 之前的执行保证
- [ ] 了解 Python 内置异常层次结构
- [ ] 知道 `assert` 的用途和局限性

### 代码实践

- [ ] 运行并理解 `01-exception-basics.py`
- [ ] 运行并理解 `02-input-validator.py`
- [ ] 运行并理解 `03-custom-exceptions.py`

### 动手实现

- [ ] 实现一个带有至少 3 层异常层次结构的自定义异常系统
- [ ] 实现一个 `retry()` 装饰器
- [ ] 实现一个 `ErrorHandler` 类将异常转换为 HTTP 响应
- [ ] 实现一个 `Validator` 链（可组合的验证器模式）

---

## 💪 练习题

### 练习 1：温度转换器

实现一个温度转换程序，要求：

1. 提示用户输入温度和单位（C/F）
2. 使用异常处理确保输入合法
3. 支持华氏 ↔ 摄氏互转
4. 处理：`ValueError`、`KeyError`、自定义 `TemperatureError`

```python
# 期望行为
> 输入温度: abc
❌ 请输入数字

> 输入温度和单位: 100 C
→ 212.0 °F

> 输入温度和单位: -500 K
❌ 不支持的单位，请使用 C 或 F

> 输入温度和单位: -300 C
❌ 温度低于绝对零度 (-273.15°C)
```

### 练习 2：文件读取器

实现一个安全的文件读取器：

1. 接收文件名列表
2. 尝试逐个读取，成功的返回内容，失败的记录错误到 `errors.log`
3. 支持 `FileNotFoundError`、`PermissionError`、`IsADirectoryError`
4. 返回 `(results: dict, errors: list)` 元组

```python
# 期望
safe_read(["a.txt", "b.txt", "c.txt"])
# → {"a.txt": "内容...", "b.txt": "内容..."}, 
#   [{"file": "c.txt", "error": "FileNotFoundError"}]
```

### 练习 3：嵌套异常处理

下面的代码输出什么？（先推理，再运行验证）

```python
def outer():
    try:
        inner()
    except ValueError:
        print("外部: 捕获 ValueError")
    except RuntimeError:
        print("外部: 捕获 RuntimeError")

def inner():
    try:
        raise ValueError("内部错误")
    except ValueError:
        print("内部: 重新引发")
        raise RuntimeError("包装为 RuntimeError")

outer()
```

### 练习 4：实现 retry 装饰器

```python
@retry(max_attempts=3, delay=0.1, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url: str) -> dict:
    """从 API 获取数据"""
    ...
```

要求：
1. 在指定异常类型时自动重试
2. 重试间隔可配置
3. 最终失败抛出 `RetryExhaustedError`（自定义异常）
4. 包含重试次数和最后一次错误信息

### 练习 5：输入验证框架

参照 `02-input-validator.py`，实现一个更完整的验证框架：

```python
# 期望 API
class UserSchema(Schema):
    username = StringField(required=True, min_len=3, max_len=20, pattern=r"^\w+$")
    age = IntField(min=0, max=150)
    email = EmailField()
    tags = ListField(StringField())

schema = UserSchema()
result = schema.validate({"username": "alice", "age": 25, "email": "a@b.com"})
# → {"username": "alice", "age": 25, "email": "a@b.com"}

result = schema.validate({"username": ""})
# → ValidationError(field="username", message="必填字段")
```

### 练习 6：finally 与 return

运行以下代码并解释输出：

```python
def test1():
    try:
        return "try"
    finally:
        return "finally"

def test2():
    try:
        raise ValueError("错误")
    finally:
        return "被覆盖"

def test3():
    for i in range(3):
        try:
            if i == 1:
                continue
            print(i)
        finally:
            print(f"finally i={i}")

print("test1:", test1())
print("test2:", test2())
test3()
```

### 练习 7：记录异常上下文

实现一个 `ExceptionLogger` 上下文管理器：

```python
class ExceptionLogger:
    """自动记录异常到 logger 对象"""

    def __init__(self, logger, operation: str):
        ...

# 使用
with ExceptionLogger(logger, "数据导入"):
    import_data(file)  # 如有异常自动记录
```

### 练习 8：断言 v.s. 异常

以下场景中，应该用 `assert` 还是 `raise`？为什么？

1. 检查用户输入的用户名是否为空
2. 检查函数内部计算结果是否始终大于 0
3. 检查数据库连接是否可用
4. 检查排序算法输出的数组是否已排序（排序函数本身没有副作用）
5. 检查 API 返回的状态码是否为 200

---

## 🔍 思考题答案参考

### 练习 3 答案

```
内部: 重新引发
外部: 捕获 RuntimeError
```

因为 `inner()` 中先捕获 `ValueError`，然后 `raise RuntimeError`（新的异常），所以外层 `outer()` 的 `except ValueError` 不匹配，被 `except RuntimeError` 捕获。

### finally+return 规则

`finally` 中的 `return` 会覆盖 `try` 或 `except` 中的 `return` 以及任何异常。

- `test1` → `"finally"`（覆盖 try 的 return）
- `test2` → `"被覆盖"`（覆盖 ValueError，异常消失！）
- `test3` → 循环体中 `finally` 在 `continue` 之前执行，所以输出是：
  ```
  0
  finally i=0
  finally i=1  # 没有打印 1（continue），但 finally 仍执行
  2
  finally i=2
  ```
