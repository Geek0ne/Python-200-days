# Day 038 — 创建型设计模式：图解

> Mermaid 与 ASCII 示意图，帮助理解单例、工厂、建造者模式

---

## 1️⃣ 单例模式（Singleton）

```mermaid
flowchart TB
    subgraph 多次获取
        A1["s1 = Singleton()"]
        A2["s2 = Singleton()"]
    end

    A1 -->|__new__| C{_instance 存在?}
    A2 -->|__new__| C

    C -->|否| N["创建新实例<br/>_instance = new"]
    C -->|是| R["返回 _instance"]

    N --> R
    R --> S["s1 is s2 = True<br/>✅ 同一个实例"]
```

### 三种实现方式对比

```
方式一：__new__ 方法
═══════════════════════
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

✅ 最 Pythonic
✅ 不多余实例化
✅ __init__ 仍会执行（需 _initialized 控制）


方式二：装饰器
═══════════════════════
@singleton
class Config:
    pass

✅ 不入侵类定义
✅ 灵活性高
❌ type(instance) 不会返回 Config


方式三：元类
═══════════════════════
class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        ...

class Config(metaclass=SingletonMeta):
    pass

✅ type(instance) 正确
✅ 可继承
❌ 复杂度较高
```

---

## 2️⃣ 简单工厂模式

```mermaid
flowchart LR
    subgraph 客户端
        C["notification =<br/>Factory.create('email')"]
    end

    subgraph 工厂
        F["NotificationFactory"]
        F --> D{"type = ?"}
    end

    subgraph 产品
        D -->|email| E["EmailNotification()"]
        D -->|sms| S["SMSNotification()"]
        D -->|push| P["PushNotification()"]
    end

    C --> F
    E --> R["notification.send('Hi!')"]
    S --> R
    P --> R
```

### 工厂解耦

```
❌ 不使用工厂:                     ✅ 使用工厂:

def send_notification(channel, msg, to):
    if channel == "email":            def send_notification(channel, msg, to):
        notifier = EmailNotifier()        notifier = NotificationFactory.create(channel)
    elif channel == "sms":               notifier.send(msg, to)
        notifier = SMSNotifier()
    ...

    ← 创建逻辑混杂在业务逻辑中      ← 创建逻辑集中管理
    ← 新增渠道要改多处代码          ← 新增渠道只改工厂
```

---

## 3️⃣ 工厂方法模式

```mermaid
classDiagram
    class Application {
        <<abstract>>
        +new_document() str
        +create_document() Document*
    }

    class PDFApplication {
        +create_document() PDFDocument
    }

    class WordApplication {
        +create_document() WordDocument
    }

    class Document {
        <<interface>>
        +open() str
        +save() str
    }

    class PDFDocument {
        +open() str
        +save() str
    }

    class WordDocument {
        +open() str
        +save() str
    }

    Application <|-- PDFApplication : 继承
    Application <|-- WordApplication : 继承
    Document <|.. PDFDocument : 实现
    Document <|.. WordDocument : 实现
    PDFApplication --> PDFDocument : 创建
    WordApplication --> WordDocument : 创建
```

### 演化过程

```
简单工厂：                    工厂方法：                    抽象工厂：
                                ┌─────────┐               ┌─────────────┐
┌──────────┐    Factory    ┌────┤App A    │   Document   │  WinFactory  │
│ Client   │───→ create()──→│    │create()─→ Doc A       │  ├─ WinButton │
└──────────┘               │    └─────────┘               │  └─ WinCheck  │
        │                  │                              │              │
        ▼                  │    ┌─────────┐               │  MacFactory  │
    ┌──────────┐           └────┤App B    │               │  ├─ MacButton│
    │ Product  │                │create()─→ Doc B         │  └─ MacCheck │
    └──────────┘                └─────────┘               └─────────────┘

    集中管理创建              创建逻辑分散到子类        创建一族相关产品
    扩展性差                  扩展性好                  产品族一致
```

---

## 4️⃣ 建造者模式（Builder）

```mermaid
flowchart TB
    subgraph 建造过程
        B["Builder"] --> S1["size(12)"]
        S1 --> S2["crust('薄脆')"]
        S2 --> S3["sauce('番茄')"]
        S3 --> S4["cheese('马苏里拉')"]
        S4 --> S5["add_topping('培根')"]
        S5 --> S6["well_done()"]
        S6 --> S7["build() → Pizza"]
    end

    subgraph Director（可选）
        D["PizzaChef"] --> T1["make_margherita()"]
        D --> T2["make_pepperoni()"]
        T1 -->|使用 Builder| P1["玛格丽特披萨"]
        T2 -->|使用 Builder| P2["辣香肠披萨"]
    end

    S7 --> P["🍕 定制披萨"]
```

### 不使用 Builder vs 使用 Builder

```
❌ 不使用 Builder:                  ✅ 使用 Builder:

# 参数太多，顺序容易错              # 链式调用，名称明确
Pizza(12, "薄脆", "番茄",           Pizza.builder()
      True, "培根", 14)               .size(12)
                                      .crust("薄脆")
# 第 4 个参数 extra_cheese?           .sauce("番茄")
# 第 5 个参数 topping?                .add_topping("培根")
# 不读文档看不懂！                     .well_done()
                                      .build()
                                  ← 一目了然！
                                  ← 可选参数可省略
```

---

## 5️⃣ 原型模式（Prototype）

```mermaid
flowchart LR
    subgraph 原型
        P["基础合同模板"]
        P --> V1["变量: {title, party_a, ...}"]
    end

    subgraph 克隆
        C1["service = base.clone()"]
        C2["nba = base.clone()"]
    end

    subgraph 定制
        C1 --> M1["修改变量: 服务合同"]
        C2 --> M2["修改变量: 球员合同"]
    end

    P --> C1
    P --> C2
```

### 深拷贝 vs 浅拷贝

```
原型模式本质：克隆已有对象

浅拷贝 (copy.copy):               深拷贝 (copy.deepcopy):
═══════════════════               ═══════════════════════

对象 A ──→ 对象 A'                对象 A ──→ 对象 A'
  │            │                     │              │
  ├─ attr1     ├─ attr1              ├─ attr1       ├─ attr1
  └─ attr2 ──→ 共享引用              └─ attr2 ──→  复制新对象

✅ 快速                        ✅ 完全独立
⚠️ 共享引用可能产生副作用          ❌ 较慢
```

---

## 6️⃣ 连接池（对象池模式）

```mermaid
flowchart TB
    subgraph 连接池
        POOL["ConnectionPool"]
        IDLE["空闲连接池: [Conn#1, Conn#2]"]
        IN_USE["使用中: {Conn#3}"]
        MAX["最大连接数: 5"]
    end

    T1["线程 1"] -->|acquire| POOL
    T2["线程 2"] -->|acquire| POOL
    POOL -->|复用空闲| T1
    POOL -->|创建新连接| T2

    T1 -->|release| POOL
    POOL -->|归还到空闲池| IDLE
```

---

## 7️⃣ 配置管理器设计

```mermaid
classDiagram
    class ConfigManager {
        -_config: dict
        -_frozen: bool
        -_readonly_keys: set
        -_listeners: list
        -_history: list
        +get(key, default) any
        +set(key, value) ConfigManager
        +freeze() ConfigManager
        +on_change(cb) ConfigManager
        +to_json() str
        +stats: dict
    }

    class ConfigBuilder {
        -_data: dict
        +set(key, value) ConfigBuilder
        +set_database() ConfigBuilder
        +set_redis() ConfigBuilder
        +set_app() ConfigBuilder
        +build() ConfigManager
        +build_and_freeze() ConfigManager
    }

    class ConfigFactory {
        +from_json_file(path) ConfigManager
        +from_json_str(str) ConfigManager
        +from_dict(dict) ConfigManager
        +from_defaults() ConfigManager
    }

    ConfigManager <.. ConfigBuilder : 建造
    ConfigManager <.. ConfigFactory : 工厂创建
```

### 设计模式在配置管理器中的应用

```
ConfigManager (单例)
  • __new__ 确保全局唯一实例
  • _initialized 确保仅初始化一次
  • 全局访问点：get() / set()

ConfigBuilder (建造者)
  • set_database() / set_app() 等预定义配置
  • 链式调用 self return
  • build() 创建 ConfigManager

ConfigFactory (工厂)
  • from_json_file() 从文件创建
  • from_dict() 从字典创建
  • from_defaults() 创建默认配置
  • 封装不同创建方式
```
