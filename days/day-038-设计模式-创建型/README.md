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

**参考答案**

**不安全。** 问题出在「先检查、再创建」这两步不是原子操作（原子操作指不可被打断、要么全做要么全不做的一步）。`if cls._instance is None` 判断通过后、`super().__new__(cls)` 还没执行完时，另一个线程可能也判断到 `None`，于是两个线程各建一个实例，单例就被破坏了。虽然 CPython 有 GIL（全局解释器锁，同一时刻只让一个线程执行字节码），但 GIL 会在字节码之间切换，挡不住这种「检查—创建」的竞态。

解决办法是**加锁 + 双重检查**：只在第一次创建时加锁，之后直接返回，兼顾安全与性能。

```python
import threading
from concurrent.futures import ThreadPoolExecutor

class Singleton:
    _instance = None
    _lock = threading.Lock()   # 类级锁，所有线程共享

    def __new__(cls, *args, **kwargs):
        # 双重检查：先不加锁判断，减少锁竞争
        if cls._instance is None:
            with cls._lock:               # 加锁，同一时刻只让一个线程进入
                if cls._instance is None: # 再检查一次，防止重复创建
                    cls._instance = super().__new__(cls)
        return cls._instance

# 用 20 个线程同时创建，验证拿到的是同一个实例
with ThreadPoolExecutor(max_workers=20) as pool:
    instances = list(pool.map(lambda _: Singleton(), range(20)))
print(all(obj is instances[0] for obj in instances))
```

预期输出：

```
True
```

`all(...)` 为 `True` 说明 20 个线程拿到的都是同一个对象。第一次判断避免每次调用都抢锁；锁内的第二次判断防止多个线程在锁外都看到 `None` 后重复创建。

💡 提示：更省心的「Python 方式」是直接用模块级变量当单例（模块只会被导入一次），或用元类把锁逻辑集中封装，避免每个单例类都手写一遍。

2. **工厂的演化**：从简单工厂 -> 工厂方法 -> 抽象工厂，每一步解决了什么问题？什么场景下需要最复杂的抽象工厂？

**参考答案**

这三者是「逐步解耦、逐步增强扩展性」的关系，复杂度递增，按需选用即可。

- **简单工厂**：把「创建哪个对象」的判断集中到一个工厂函数里，调用方不再 `new` 具体类。它解决了**创建逻辑散落各处**的问题。缺点是新增类型要改工厂里的 `if/elif`，违反「开闭原则」（对扩展开放、对修改关闭）。
- **工厂方法**：把创建逻辑下放到子类，父类只定义「要创建一个产品」的抽象方法。新增产品只需新增一个子类，**不用改原有代码**，解决了简单工厂「一改就要动中心」的扩展性问题。
- **抽象工厂**：一次创建**一整族相互配套**的对象（如按钮 + 复选框 + 滚动条）。它解决的是**产品之间的一致性**问题——保证你拿到的整套组件风格统一，不会 Windows 按钮配了 macOS 复选框。

什么时候才需要抽象工厂？当系统存在**多个「产品族」、且族内对象必须配套使用**时，例如：

- 跨平台 GUI：Windows / macOS / Linux 各有一套控件，切换平台时整套控件一起换。
- 数据库驱动族：连接 + 命令 + 适配器要来自同一个数据库厂商，不能混搭。
- 主题皮肤：一套「深色主题」的按钮、输入框、图标必须成套出现。

💡 提示：如果只是「根据参数造一个对象」，简单工厂（甚至一个字典映射）就够了；别一上来就上抽象工厂，那是过度设计。

3. **Builder vs 构造器**：建造者模式和 `__init__` 中使用大量参数有什么区别？Python 中是否可以用 `**kwargs` 替代 Builder？

**参考答案**

`__init__` 塞一堆参数（尤其位置参数）的痛点是：**参数顺序难记、可选参数难表达、构造一步到位无法分步**。`Computer('Intel', 32, 512, 'RTX4090', ...)` 里第 3 个 512 到底是内存还是硬盘，读代码的人得回去翻定义。建造者把每个参数变成一个**有名字的方法**（`.cpu(...)`、`.ram(...)`），链式调用、按需设置，最后 `.build()` 一次性产出对象，可读性和灵活性都更好。

`**kwargs`（接收任意关键字参数的字典）能不能替代 Builder？**部分能，但有明显短板：

- **能**：对于「参数多但都是简单赋值」的场景，`Computer(cpu='i9', ram=32, disk=1024)` 这种关键字参数已经比位置参数清晰得多，配合 `dataclass` 的默认值就更省事，未必需要专门的 Builder 类。
- **不能**：`**kwargs` 是「黑盒」——没有类型提示、IDE 无法补全、拼错键名不会报错（悄悄被忽略）；它也做不了**分步构建中的校验**（比如 build 时检查「选了独显就必须配大电源」）、**构建过程复用**（同一套步骤造不同表示）和**不可变产品的最终封装**。这些正是 Builder 的强项。

一句话：**参数多但逻辑简单 → 关键字参数 / dataclass 就够；需要分步装配、构建期校验、或一套流程产出多种表示 → 才值得上 Builder。**

⚠️ 注意：用 `**kwargs` 时最好显式列出已知参数并校验未知键，否则拼写错误会被静默吞掉，埋下难查的 bug。

4. **原型模式替代方案**：Python 的 `copy.deepcopy()` 和原型模式的关系是什么？什么场景下原型模式比工厂更高效？

**参考答案**

**原型模式**的核心思想是：不通过「从零构造」来创建对象，而是**复制一个已有的样板对象（原型）**，再按需修改。在 Java/C++ 里通常要手写 `clone()` 方法；而 Python 标准库的 `copy.deepcopy()` 天然就是「克隆」工具，所以**原型模式在 Python 里基本就等于「深拷贝一个原型实例」**，无需额外造轮子。

`deepcopy`（深拷贝）会递归复制对象及其内部所有可变子对象，保证克隆体和原型互不影响；浅拷贝 `copy.copy` 只复制最外层，内部列表等仍共享，容易踩坑。

```python
import copy

class Enemy:
    def __init__(self, hp, skills):
        self.hp = hp
        self.skills = skills   # 列表是可变对象

# 先造一个「原型」：初始化可能很贵（读配置、算数值、加载资源）
prototype = Enemy(hp=100, skills=["撕咬", "冲撞"])

# 之后批量「克隆」原型，再微调，而不是每次从头构造
clone = copy.deepcopy(prototype)
clone.hp = 80
clone.skills.append("中毒")

print(prototype.hp, prototype.skills)   # 原型不受影响
print(clone.hp, clone.skills)           # 克隆体独立
print(clone is prototype)               # False，确实是新对象
```

预期输出：

```
100 ['撕咬', '冲撞']
80 ['撕咬', '冲撞', '中毒']
False
```

原型比工厂更高效的场景：**构造成本高、但对象之间高度相似**时。比如游戏里成百上千个只有血量/位置略有差异的小怪、已加载好纹理/配置的模板对象、初始化要读文件或做复杂计算的对象——先精心造一个原型，之后不断克隆微调，省去了重复的昂贵初始化。

⚠️ 注意：`deepcopy` 本身也要遍历整个对象图，对象极大或极深时并不便宜；若只需共享只读部分，可考虑浅拷贝或享元模式。

5. **设计模式的 Python 之道**：很多 GoF 设计模式在 Python 中有更简单的实现（如用模块代替单例），什么时候该用「Python 方式」而不是「GoF 方式」？

**参考答案**

GoF（《设计模式》四位作者）的很多模式，是在 Java/C++ 这种「没有一等函数、没有模块、类型系统严格」的语言里，为了绕开语言限制而发明的结构。Python 语言本身更灵活，许多模式可以**大幅简化甚至消失**：

- **单例 → 模块**：模块只会被导入一次，模块级变量天然全局唯一，不必写 `__new__`/元类。
- **策略 → 函数**：策略模式本质是「把算法当参数传」，Python 函数是一等对象，直接传函数即可，不必为每个策略建一个类。
- **工厂 → 字典/函数**：`{'alipay': Alipay, 'wechat': WechatPay}[type]()` 一行就够，未必需要工厂类。
- **迭代器 → 生成器**：`yield` 自动实现迭代协议，不用手写 `__iter__`/`__next__`。
- **装饰器模式 → 语法糖 `@`**：语言内置支持。

什么时候优先用「Python 方式」？**当语言特性已经能直接、清晰地表达意图时**——代码更短、依赖更少、可读性更高，就没必要套一层 GoF 的类结构。小项目、脚本、内部工具尤其如此。

什么时候仍值得用「GoF 方式」（完整的类结构）？

- **需要带状态的多态对象**：策略不只是一个函数，还要持有配置、缓存、生命周期，用类更合适。
- **框架契约/团队协作**：大型项目里，显式的接口和类层次能让契约清晰、便于多人协作和静态检查。
- **需要被框架按类型识别**：如异常、`TestCase`、线程，必须靠继承接入（见 day-037 第 4 题）。

一句话：**模式是手段不是目的。能用语言特性简单解决就用 Python 方式；当问题确实需要那种结构（状态、多态、契约）时，再请出 GoF。** 切忌为了「用上模式」而过度设计。

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
