# Day 40：行为型设计模式 ✓ 完成清单

## ✅ 今日完成情况

- [x] 理解观察者模式的概念与原理
- [x] 理解策略模式的概念与原理
- [x] 理解命令模式的概念与原理
- [x] 掌握观察者模式的推模型与拉模型
- [x] 掌握策略与状态模式的区别
- [x] 掌握命令模式撤销/重做支持
- [x] 阅读并运行 `code/01-observer-pattern.py`
- [x] 阅读并运行 `code/02-strategy-pattern.py`
- [x] 阅读并运行 `code/03-event-system.py`
- [x] 理解三种模式在事件系统中的协同

---

## 📝 练习题

### 基础题

#### 1. 分析下面的代码属于哪种模式（5 分）

```python
class Calculator:
    def __init__(self, operation):
        self.operation = operation

    def calculate(self, a, b):
        return self.operation(a, b)

add = lambda a, b: a + b
multiply = lambda a, b: a * b

calc = Calculator(add)
print(calc.calculate(3, 4))  # 7
calc.operation = multiply
print(calc.calculate(3, 4))  # 12
```

**问题**：这段代码实现了什么模式？如果不用 lambda，请用标准 OOP 方式改写。

---

#### 2. 补全观察者模式代码（5 分）

```python
from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod
    def update(self, message: str) -> None:
        pass

class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        # 请补全：注册观察者

    def notify(self, message: str):
        # 请补全：通知所有观察者

class User(Observer):
    def __init__(self, name: str):
        self.name = name

    def update(self, message: str):
        print(f"[{self.name}] 收到通知: {message}")

# 测试代码
subject = Subject()
user1 = User("Alice")
user2 = User("Bob")
subject.attach(user1)
subject.attach(user2)
subject.notify("欢迎来到 Python 世界！")
```

**问题**：请补全 `attach` 和 `notify` 方法，使程序输出：
```
[Alice] 收到通知: 欢迎来到 Python 世界！
[Bob] 收到通知: 欢迎来到 Python 世界！
```

---

#### 3. 命令模式：设计一个简单的遥控器（5 分）

使用**命令模式**设计一个智能家居遥控器系统，支持以下操作：
- 打开/关闭灯光（`Light.on()` / `Light.off()`）
- 打开/关闭风扇（`Fan.on()` / `Fan.off()`）
- 遥控器支持**撤销上一个操作**

请完成以下代码结构：

```python
# TODO: 实现 Command 接口
# TODO: 实现 LightOnCommand, LightOffCommand
# TODO: 实现 FanOnCommand, FanOffCommand
# TODO: 实现 RemoteControl（支持 execute + undo）
```

**要求**：
1. 定义 `Command` 抽象类，包含 `execute()` 和 `undo()` 方法
2. 遥控器记录操作历史，按下 undo 时撤销上一个命令
3. 编写简单的 main 函数演示

---

### 进阶题

#### 4. 实现一个日志系统：策略模式 + 观察者模式（10 分）

设计一个灵活的日志记录系统：

**需求**：
1. 日志来源（被观察者）：`Application` 会产生不同类型的日志（INFO, WARN, ERROR）
2. 日志记录器（观察者）：
   - `ConsoleLogger`：输出到控制台
   - `FileLogger`：追加到文件
   - `DatabaseLogger`：存入数据库（用 print 模拟）
3. 日志格式化策略（策略模式）：
   - `SimpleFormatter`：`[INFO] 消息`
   - `DetailedFormatter`：`[2026-06-28 22:35:00] [ERROR] [main.py:42] 消息`
   - `JSONFormatter`：`{"level": "INFO", "message": "...", "timestamp": "..."}`

**要求**：
- 每种日志类型都可以独立配置使用哪些日志记录器
- 日志记录器可以运行时添加或移除（观察者模式）
- 日志格式化方式可以运行时切换（策略模式）
- 补充代码并写出 main 函数测试

```python
# 请在这里编写你的代码
```

---

#### 5. 思考题：Pythonic 的行为型模式（10 分）

Python 中的函数是一等公民，不需要严格的类层次也能实现这些模式：

**题目**：用**纯函数和高阶函数**（不使用 ABC 和类继承）实现以下功能：

1. 一个简单的事件发射器 `EventEmitter`，支持：
   - `on(event_type, callback)` — 注册监听器
   - `off(event_type, callback)` — 移除监听器
   - `emit(event_type, data)` — 触发事件

2. 不使用 `class` 实现，使用闭包返回字典：

```python
def create_emitter():
    # 返回一个字典，包含 on, off, emit 方法
    pass
```

**要求**：
- 使用闭包 `create_emitter()` 替代类
- 注册的监听器可以是一个普通函数
- 同一个事件类型可以注册多个监听器
- 支持 `off()` 移除指定监听器
- 提供测试代码

---

## 📖 扩展阅读

| 资源 | 链接 |
|------|------|
| GoF 设计模式原著 | Design Patterns: Elements of Reusable Object-Oriented Software |
| Python 官方 ABC 文档 | https://docs.python.org/3/library/abc.html |
| `typing.Protocol` | https://docs.python.org/3/library/typing.html#typing.Protocol |
| 观察者 vs 发布订阅 | https://refactoring.guru/design-patterns/observer |
| 策略模式 | https://refactoring.guru/design-patterns/strategy |
| 命令模式 | https://refactoring.guru/design-patterns/command |

## 🔑 参考答案提示

练习 1：策略模式。标准 OOP 方式可定义一个 `Operation` ABC，然后 `AddOperation` 和 `MultiplyOperation` 分别继承。

练习 2：
```python
def attach(self, observer):
    self._observers.append(observer)

def notify(self, message: str):
    for obs in self._observers:
        obs.update(message)
```

练习 5（核心思路）：
```python
def create_emitter():
    listeners = {}
    def on(evt_type, cb):
        listeners.setdefault(evt_type, []).append(cb)
    def off(evt_type, cb):
        if evt_type in listeners:
            listeners[evt_type] = [l for l in listeners[evt_type] if l != cb]
    def emit(evt_type, data):
        for cb in listeners.get(evt_type, []):
            cb(data)
    return {"on": on, "off": off, "emit": emit}
```
