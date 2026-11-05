# Day 038 — 设计模式（创建型）

> 掌握三种核心创建型设计模式：单例、工厂、建造者，实战配置管理器

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 设计模式总览 | ⭐⭐ | GoF 23 种设计模式分类 |
| 单例模式 | ⭐⭐⭐ | 确保类只有一个实例 |
| 工厂模式 | ⭐⭐⭐ | 封装对象创建逻辑 |
| 建造者模式 | ⭐⭐⭐⭐ | 分步构建复杂对象 |
| 实战：配置管理器 | ⭐⭐⭐⭐ | 综合运用多种模式 |

---

## 一、设计模式总览

### 1.1 GoF 23 种设计模式

**创建型模式（5 种）** — 对象创建机制
┌─────────────────────────────────────────────┐
│ 单例 (Singleton)   工厂方法 (Factory Method)   │
│ 抽象工厂 (Abstract Factory)  建造者 (Builder)  │
│ 原型 (Prototype)                              │
└─────────────────────────────────────────────┘

**结构型模式（7 种）** — 对象组合关系
┌─────────────────────────────────────────────┐
│ 适配器 (Adapter)    桥接 (Bridge)             │
│ 组合 (Composite)    装饰器 (Decorator)         │
│ 外观 (Facade)       享元 (Flyweight)           │
│ 代理 (Proxy)                                  │
└─────────────────────────────────────────────┘

**行为型模式（11 种）** — 对象交互与职责分配
┌─────────────────────────────────────────────┐
│ 策略 (Strategy)     观察者 (Observer)          │
│ 命令 (Command)      迭代器 (Iterator)          │
│ 模板方法 (Template)  责任链 (Chain of Resp)    │
│ 状态 (State)        访问者 (Visitor)           │
│ 中介者 (Mediator)   备忘录 (Memento)           │
│ 解释器 (Interpreter)                         │
└─────────────────────────────────────────────┘

### 1.2 创建型模式的作用

> 创建型模式将对象 **「创建」** 的逻辑从 **「使用」** 的逻辑中分离出来。

```
不使用模式：                        使用创建型模式：
class Client:                       class Client:
    def __init__(self):                 def __init__(self):
        self.obj = SomeClass()              self.factory = factory
            ↑ 硬编码                         ↑ 注入
    要改类型必须改 Client 代码           运行时决定创建什么对象
```

---

## 二、单例模式（Singleton）

### 2.1 概念

**单例模式** 确保一个类 **只有一个实例**，并提供一个全局访问点。

```
                    ┌──────────────────────┐
                    │      Singleton       │
                    │                      │
                    │ -_instance: Singleton │
                    │                      │
                    │ +get_instance():     │
                    │   Singleton          │
                    └──────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
              ┌──────────┐       ┌──────────┐
              │ 调用方 A  │       │ 调用方 B  │
              └──────────┘       └──────────┘
                    同一实例       同一实例
```

### 2.2 Python 实现方式

**方式一：使用 `__new__` 方法（最常用）**

```python
class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.value = 42

# 测试
s1 = Singleton()
s2 = Singleton()
print(s1 is s2)  # True
```

**方式二：使用装饰器**

```python
def singleton(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance

@singleton
class Config:
    def __init__(self):
        self.data = {}

c1 = Config()
c2 = Config()
print(c1 is c2)  # True
```

**方式三：使用元类**

```python
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Config(metaclass=SingletonMeta):
    def __init__(self):
        self.data = {}
```

### 2.3 单例的优缺点

| 优点 | 缺点 |
|------|------|
| 确保唯一实例 | 全局状态，可能引起隐藏的依赖 |
| 节省内存 | 难以测试（全局状态） |
| 提供全局访问点 | 违反单一职责原则 |
| 懒初始化（按需创建） | 多线程需要额外注意 |

### 2.4 Python 模块本身就是单例

```python
# config_module.py
# Python 模块是天然的单例——import 多次只加载一次

DEFAULT_TIMEOUT = 30
API_KEY = ""

def configure(key, timeout=DEFAULT_TIMEOUT):
    global API_KEY, DEFAULT_TIMEOUT
    API_KEY = key
    DEFAULT_TIMEOUT = timeout
```

---

## 三、工厂模式（Factory Pattern）

### 3.1 简单工厂（Simple Factory）

```
                          ┌──────────────────────┐
                          │   简单工厂            │
                          │ create_payment(type)  │
                          └──────────┬───────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                ▼                    ▼                    ▼
        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
        │ 支付宝支付     │    │  微信支付     │    │  银联支付     │
        │ pay()         │    │  pay()       │    │  pay()       │
        └──────────────┘    └──────────────┘    └──────────────┘
```

```python
class Payment:
    def pay(self, amount):
        pass

class Alipay(Payment):
    def pay(self, amount):
        return f"支付宝支付 ¥{amount}"

class WechatPay(Payment):
    def pay(self, amount):
        return f"微信支付 ¥{amount}"

class PaymentFactory:
    @staticmethod
    def create(payment_type: str) -> Payment:
        if payment_type == "alipay":
            return Alipay()
        elif payment_type == "wechat":
            return WechatPay()
        raise ValueError(f"不支持的支付方式: {payment_type}")

payment = PaymentFactory.create("alipay")
payment.pay(100)
```

### 3.2 工厂方法模式（Factory Method）

工厂方法将 **创建逻辑** 推迟到子类中实现：

```python
from abc import ABC, abstractmethod

class Document(ABC):
    @abstractmethod
    def open(self): pass

class PDFDocument(Document):
    def open(self): return "打开 PDF 文档"

class WordDocument(Document):
    def open(self): return "打开 Word 文档"

class Application(ABC):
    @abstractmethod
    def create_document(self) -> Document:
        """工厂方法 —— 子类决定创建哪种文档"""
        pass

    def new_document(self):
        doc = self.create_document()
        return doc.open()

class PDFApp(Application):
    def create_document(self) -> Document:
        return PDFDocument()

class WordApp(Application):
    def create_document(self) -> Document:
        return WordDocument()

app = PDFApp()
print(app.new_document())  # 打开 PDF 文档
```

### 3.3 抽象工厂模式（Abstract Factory）

创建 **一系列相关** 的对象：

```python
class GUIFactory(ABC):
    @abstractmethod
    def create_button(self): pass

    @abstractmethod
    def create_checkbox(self): pass

class WinFactory(GUIFactory):
    def create_button(self): return "Windows 按钮"
    def create_checkbox(self): return "Windows 复选框"

class MacFactory(GUIFactory):
    def create_button(self): return "macOS 按钮"
    def create_checkbox(self): return "macOS 复选框"

def create_ui(factory: GUIFactory):
    button = factory.create_button()
    checkbox = factory.create_checkbox()
    return f"{button} + {checkbox}"

print(create_ui(WinFactory()))   # Windows 按钮 + Windows 复选框
print(create_ui(MacFactory()))   # macOS 按钮 + macOS 复选框
```

---

## 四、建造者模式（Builder）

### 4.1 概念

建造者模式将 **复杂对象的构建过程** 与它的 **表示** 分离，使得同样的构建过程可以创建不同的表示。

```
                 Director
                    │
             构建步骤指导
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│  Builder  │  │  Builder │  │  Builder │
│ (接口)    │  │ (A)      │  │ (B)      │
│ build_a() │  │          │  │          │
│ build_b() │  │ 产品 A   │  │ 产品 B   │
│ get()     │  └──────────┘  └──────────┘
└──────────┘
```

### 4.2 适用场景

```
❌ 不使用 Builder:              ✅ 使用 Builder:
                                
Computer('Intel', 32, 512,      Computer.builder()
         'NVIDIA 3080',           .cpu('Intel')
         '机械键盘',               .ram(32)
         '24寸 4K')               .disk(512)
                                 .gpu('NVIDIA 3080')
  ← 参数太多，容易混淆            .build()
                                  ← 链式调用，清晰
  # 哪个参数是 SSD 容量?           ← 可选参数，灵活
  # 第 3 个参数怎么是 512 不是 256?
```

### 4.3 实现

```python
class Computer:
    def __init__(self):
        self.cpu = None
        self.ram = None
        self.disk = None
        self.gpu = None
        self.keyboard = None
        self.monitor = None

    def __repr__(self):
        return (f"Computer(cpu={self.cpu}, ram={self.ram}, "
                f"disk={self.disk}, gpu={self.gpu})")

    @staticmethod
    def builder():
        return ComputerBuilder()


class ComputerBuilder:
    def __init__(self):
        self._computer = Computer()

    def cpu(self, model: str):
        self._computer.cpu = model
        return self  # 返回 self 以支持链式调用

    def ram(self, size: int):
        self._computer.ram = size
        return self

    def disk(self, capacity: int):
        self._computer.disk = capacity
        return self

    def gpu(self, model: str):
        self._computer.gpu = model
        return self

    def build(self):
        return self._computer


# 使用
gaming_pc = Computer.builder() \
    .cpu("Intel i9") \
    .ram(32) \
    .disk(1024) \
    .gpu("RTX 4090") \
    .build()

office_pc = Computer.builder() \
    .cpu("Intel i5") \
    .ram(16) \
    .disk(512) \
    .build()

print(gaming_pc)  # Computer(cpu=Intel i9, ...)
print(office_pc)  # Computer(cpu=Intel i5, ...)
```

---

## 五、实战：配置管理器

### 5.1 系统设计

```
┌───────────────────────────────────────────┐
│           ConfigManager (单例)             │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │         配置存储 (字典)               │  │
│  │  database.host → localhost           │  │
│  │  database.port → 5432                │  │
│  │  redis.host → localhost              │  │
│  │  redis.port → 6379                   │  │
│  │  app.debug → True                    │  │
│  │  app.name → MyApp                    │  │
│  └─────────────────────────────────────┘  │
│                                           │
│  方法:                                     │
│  • get(key, default)  ← 读取              │
│  • set(key, value)    ← 写入              │
│  • load_from_file()   ← 加载配置          │
│  • as_dict()          ← 导出              │
└───────────────────────────────────────────┘
         ↑                  ↑
         │                  │
    ConfigFactory        ConfigBuilder
    (创建不同格式配置)     (构建复杂配置)
```

### 5.2 关键实现

```python
import json
from typing import Any, Dict, Optional


class ConfigManager:
    """配置管理器 —— 单例模式"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._config: Dict[str, Any] = {}
            self._listeners = []
            self._initialized = True

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的键 """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """设置配置值，支持点号分隔的键"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._notify(key, value)

    def load_dict(self, data: Dict[str, Any], prefix: str = ""):
        """加载字典配置"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self.load_dict(value, full_key)
            else:
                self.set(full_key, value)

    def load_json(self, json_str: str):
        """从 JSON 字符串加载"""
        self.load_dict(json.loads(json_str))

    def as_dict(self) -> Dict[str, Any]:
        """导出为嵌套字典"""
        return self._config.copy()

    def on_change(self, callback):
        """注册变更监听器"""
        self._listeners.append(callback)

    def _notify(self, key: str, value: Any):
        """通知监听器"""
        for listener in self._listeners:
            listener(key, value)


class ConfigFactory:
    """配置工厂 —— 从不同格式创建配置"""

    @staticmethod
    def from_json_file(filepath: str) -> ConfigManager:
        config = ConfigManager()
        with open(filepath, 'r', encoding='utf-8') as f:
            config.load_json(f.read())
        return config

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ConfigManager:
        config = ConfigManager()
        config.load_dict(data)
        return config


class ConfigBuilder:
    """配置建造者 —— 链式构建配置"""

    def __init__(self):
        self._data: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        keys = key.split('.')
        current = self._data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
        return self

    def set_database(self, host="localhost", port=5432,
                     name="app", user="admin"):
        return self \
            .set("database.host", host) \
            .set("database.port", port) \
            .set("database.name", name) \
            .set("database.user", user)

    def set_redis(self, host="localhost", port=6379, db=0):
        return self \
            .set("redis.host", host) \
            .set("redis.port", port) \
            .set("redis.db", db)

    def set_app(self, name="App", debug=False, version="1.0"):
        return self \
            .set("app.name", name) \
            .set("app.debug", debug) \
            .set("app.version", version)

    def build(self) -> ConfigManager:
        config = ConfigManager()
        config.load_dict(self._data)
        return config


# 使用示例
config = ConfigBuilder() \
    .set_database(host="db.example.com") \
    .set_redis() \
    .set_app(name="MyApp", debug=True) \
    .build()

print(config.get("database.host"))      # db.example.com
print(config.get("app.debug"))          # True
print(config.get("database.port"))      # 5432
```

---

## 六、思考题

1. **单例的线程安全**：Python 中 `__new__` 方式的单例在多线程环境下安全吗？如何保证线程安全？

2. **工厂的演化**：从简单工厂 -> 工厂方法 -> 抽象工厂，每一步解决了什么问题？什么场景下需要最复杂的抽象工厂？

3. **Builder vs 构造器**：建造者模式和 `__init__` 中使用大量参数有什么区别？Python 中是否可以用 `**kwargs` 替代 Builder？

4. **原型模式替代方案**：Python 的 `copy.deepcopy()` 和原型模式的关系是什么？什么场景下原型模式比工厂更高效？

5. **设计模式的 Python 之道**：很多 GoF 设计模式在 Python 中有更简单的实现（如用模块代替单例），什么时候该用「Python 方式」而不是「GoF 方式」？

---

## 📝 本章小结

```
✅ 设计模式总览 —— GoF 23 种模式的分类
✅ 单例模式 —— 确保类只有一个实例
✅ 简单工厂 —— 封装对象创建，集中管理
✅ 工厂方法 —— 将创建逻辑推迟到子类
✅ 抽象工厂 —— 创建一系列相关对象
✅ 建造者模式 —— 分步构建复杂对象，链式调用
✅ 实战：配置管理器 —— 单例 + 工厂 + 建造者
```
