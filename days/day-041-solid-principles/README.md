# Day 41 — SOLID 原则

> SOLID 是面向对象设计的五个基本原则，由 Robert C. Martin（Uncle Bob）在 2000 年代提出。掌握这些原则是写出可维护、可扩展代码的关键。

---

## 目录

1. [SOLID 概览](#1-solid-概览)
2. [SRP — 单一职责原则](#2-srp--单一职责原则)
3. [OCP — 开闭原则](#3-ocp--开闭原则)
4. [LSP — 里氏替换原则](#4-lsp--里氏替换原则)
5. [ISP — 接口隔离原则](#5-isp--接口隔离原则)
6. [DIP — 依赖反转原则](#6-dip--依赖反转原则)
7. [设计原则 vs 设计模式](#7-设计原则-vs-设计模式)
8. [实战：重构糟糕代码](#8-实战重构糟糕代码)
9. [思考题](#9-思考题)

---

## 1. SOLID 概览

### 1.1 什么是 SOLID？

SOLID 是五个设计原则的首字母缩写：

| 缩写 | 全称 | 核心思想 |
|------|------|----------|
| **S** | 单一职责原则（SRP） | 一个类只做一件事 |
| **O** | 开闭原则（OCP） | 对扩展开放，对修改关闭 |
| **L** | 里氏替换原则（LSP） | 子类必须可替换父类 |
| **I** | 接口隔离原则（ISP） | 接口要小而专 |
| **D** | 依赖反转原则（DIP） | 依赖抽象，不依赖具体 |

### 1.2 为什么学习 SOLID？

```
┌─────────────────────────────────────────────────────────────────────┐
│                    没有 SOLID 原则 → 意大利面条代码                    │
│                                                                     │
│  一个类做所有事 → 改一处崩一片 → 不敢重构 → 技术债爆炸                  │
│                                                                     │
│                    应用 SOLID 原则 → 整洁架构                        │
│                                                                     │
│  高内聚低耦合 → 模块可独立测试 → 容易扩展 → 长期维护成本低               │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 SOLID 之间的关系

```
                ┌──────────────────────┐
                │        DIP           │ ─── 顶层：架构级别的指导
                │    依赖反转原则       │     决定模块间的依赖方向
                └────────┬─────────────┘
                         │ 依赖抽象而非具体
            ┌────────────┴────────────┐
            │                         │
   ┌────────▼────────┐     ┌─────────▼─────────┐
   │      OCP        │     │       ISP          │
   │  开闭原则        │     │   接口隔离原则      │
   │  扩展开放        │     │   小而专的接口      │
   └────────┬────────┘     └─────────┬─────────┘
            │                         │
            └────────────┬────────────┘
                         │
                 ┌──────▼──────┐
                 │     SRP     │ ─── 基础：每个类/模块只关注一件事
                 │  单一职责    │
                 └──────┬──────┘
                        │
                 ┌──────▼──────┐
                 │     LSP     │ ─── 保障：多态能正确工作
                 │  里氏替换    │
                 └─────────────┘

  关系解读：
  - SRP 是地基：职责清晰才谈得上扩展和替换
  - OCP 和 ISP 是手段：通过抽象和隔离达到弹性
  - LSP 是保障：保证多态替换不出问题
  - DIP 是顶层设计：控制整体依赖流向
```

---

## 2. SRP — 单一职责原则

> **Single Responsibility Principle**
> *"A class should have one, and only one, reason to change."*
> — Robert C. Martin

一个类应该只有一个引起它变化的原因。换句话说，**一个类只做一件事**。

### 2.1 违反 SRP 的例子

```python
class Report:
    """这个类做了太多事——违反了 SRP"""

    def __init__(self, data):
        self.data = data

    def generate_report(self):
        """生成报表数据"""
        # ... 业务逻辑 ...

    def save_to_file(self, filename):
        """保存到文件（持久化职责）"""
        with open(filename, 'w') as f:
            f.write(self.data)

    def send_email(self, recipient):
        """发送邮件（通知职责）"""
        # ... 发送邮件 ...

    def format_html(self):
        """格式化为 HTML（展示职责）"""
        return f"<html>{self.data}</html>"
```

这个 `Report` 类同时承担了：业务生成、持久化、通知、展示 四种职责。任何一项发生变化，都要修改这个类。

### 2.2 遵循 SRP 的重构

```python
class ReportGenerator:
    """只负责报表数据生成"""
    def generate(self): ...

class ReportSaver:
    """只负责保存"""
    def save(self, filename): ...

class EmailSender:
    """只负责发送邮件"""
    def send(self, recipient): ...

class HTMLFormatter:
    """只负责格式化"""
    def format(self): ...
```

每个类只有一个变化原因，测试更容易，修改更安全。

### 2.3 SRP 判断标准

| 症状 | 说明 |
|------|------|
| 类名含多个概念 | 如 `ReportEmailSaver` — 拆！ |
| 方法太多（>10） | 很可能在做多件事 |
| 变更总是不同领域 | 改数据库 + 改报表逻辑 |
| 测试需要 mock 太多 | 一个类依赖过多外部组件 |

### 2.4 注意：不要过度拆分

```
  过粗                   适中                   过细
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ 一个类做所有事 │   │  3-5 个职责域  │   │ 每个方法一个类 │
│ 上帝反模式    │   │  合理平衡     │   │ 接口爆炸     │
└──────────────┘   └──────────────┘   └──────────────┘
```

SRP 是指导原则，不是教条。拆分到**高内聚、低耦合**即可。

---

## 3. OCP — 开闭原则

> **Open/Closed Principle**
> *"Software entities should be open for extension, but closed for modification."*
> — Bertrand Meyer

一个模块应该**对扩展开放，对修改关闭**。意思是：添加新功能时，尽量通过扩展（新增类、方法）来实现，而不是修改已有的代码。

### 3.1 违反 OCP 的例子

```python
class ShapeDrawer:
    """每当有新形状，就要修改这个类——违反 OCP"""

    def draw(self, shape):
        if shape["type"] == "circle":
            self._draw_circle(shape)
        elif shape["type"] == "rectangle":
            self._draw_rectangle(shape)
        # 每次加新形状都要加 elif —— 不！好！
```

### 3.2 遵循 OCP 的重构

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    """抽象基类——对扩展开放"""
    @abstractmethod
    def draw(self): ...

class Circle(Shape):
    def draw(self):
        print("绘制圆形")

class Rectangle(Shape):
    def draw(self):
        print("绘制矩形")

# 新形状来了——新增类就行，不修改已有代码
class Triangle(Shape):
    def draw(self):
        print("绘制三角形")

def draw_all(shapes: list[Shape]):
    for s in shapes:
        s.draw()  # 多态——无需 if-elif
```

### 3.3 OCP 的实现方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| **继承** | 子类扩展父类方法 | 框架扩展、模板方法 |
| **抽象基类** | 定义接口，具体类实现 | 策略模式、工厂模式 |
| **依赖注入** | 运行时传入不同实现 | 配置切换、A/B 测试 |
| **装饰器** | 动态添加行为 | 日志、缓存、鉴权 |

---

## 4. LSP — 里氏替换原则

> **Liskov Substitution Principle**
> *"Objects in a program should be replaceable with instances of their subtypes without altering the correctness of that program."*
> — Barbara Liskov

如果 S 是 T 的子类型，那么任何使用 T 的地方都可以用 S 替换，而程序行为不会出错。

### 4.1 经典反例：正方形 vs 长方形

```python
class Rectangle:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    def set_width(self, w):
        self._width = w

    def set_height(self, h):
        self._height = h

    def area(self):
        return self._width * self._height

class Square(Rectangle):
    """正方形——看似"是一个"长方形，但行为不同"""

    def set_width(self, w):
        self._width = w
        self._height = w  # 强制宽高相等！

    def set_height(self, h):
        self._height = h
        self._width = h  # 强制宽高相等！

def test_rectangle(r: Rectangle):
    """这个测试对 Rectangle 成立，但对 Square 失败"""
    r.set_width(5)
    r.set_height(10)
    assert r.area() == 50  # Square 给的是 100！❌
```

`Square` 替换 `Rectangle` 后程序行为变了——违反了 LSP。

**正确的做法**：让 `Rectangle` 和 `Square` 都继承自一个抽象 `Shape`，而不是相互继承。

### 4.2 LSP 的三大约束

```
┌──────────────────────────────────────────────────┐
│                  LSP 约束                          │
├──────────────────────────────────────────────────┤
│ 1. 前置条件不能增强                     │
│   父类接受 int，子类不能要求 "int > 0"             │
│                                                  │
│ 2. 后置条件不能减弱                     │
│   父类保证返回非空，子类不能返回 None              │
│                                                  │
│ 3. 不变条件必须保持                     │
│   父类的所有不变式，子类也必须遵守                 │
└──────────────────────────────────────────────────┘
```

### 4.3 Python 中的 LSP

```python
from abc import ABC, abstractmethod

class Bird(ABC):
    @abstractmethod
    def move(self): ...

class Sparrow(Bird):
    def move(self):
        print("麻雀在飞")

class Penguin(Bird):
    def move(self):
        print("企鹅在走路和游泳")
        # 企鹅不会飞——但 move() 语义仍然是"移动"，没问题

# 关键：不要定义一个 Bird.fly() 然后企鹅 raise NotImplementedError
# 正确的抽象是 move() 而不是 fly()
```

**LSP 的指导意义**：设计继承层次时，**行为契约**比"现实世界分类"更重要。

---

## 5. ISP — 接口隔离原则

> **Interface Segregation Principle**
> *"Clients should not be forced to depend upon interfaces that they do not use."*
> — Robert C. Martin

客户端不应该依赖它不需要的接口。**接口要小而专**，而不是大而全。

### 5.1 违反 ISP 的例子

```python
from abc import ABC, abstractmethod

class Worker(ABC):
    """胖接口——什么都有"""
    @abstractmethod
    def work(self): ...

    @abstractmethod
    def eat(self): ...

    @abstractmethod
    def sleep(self): ...

class Human(Worker):
    def work(self): print("人类工作")
    def eat(self): print("人类吃饭")
    def sleep(self): print("人类睡觉")

class Robot(Worker):
    def work(self): print("机器人工作")
    def eat(self): raise NotImplementedError("机器人不需要吃饭")
    def sleep(self): raise NotImplementedError("机器人不需要睡觉")
```

`Robot` 被迫实现了两个不需要的方法——这是 ISP 反例。

### 5.2 遵循 ISP 的重构

```python
class Workable(ABC):
    @abstractmethod
    def work(self): ...

class Eatable(ABC):
    @abstractmethod
    def eat(self): ...

class Sleepable(ABC):
    @abstractmethod
    def sleep(self): ...

class Human(Workable, Eatable, Sleepable):
    def work(self): print("人类工作")
    def eat(self): print("人类吃饭")
    def sleep(self): print("人类睡觉")

class Robot(Workable):
    def work(self): print("机器人工作")
    # 不需要 eat 和 sleep 了
```

接口被拆分成更小的角色，每个类只实现自己需要的。

### 5.3 ISP 与 Python

Python 没有接口关键字，但可以通过 ABC 或 Protocol 来实现：

```python
from typing import Protocol

class Drawable(Protocol):
    """Protocol —— Python 式的接口"""
    def draw(self) -> None: ...

class Printable(Protocol):
    def print_content(self) -> None: ...

def render(thing: Drawable):
    thing.draw()
```

**Python 的鸭子类型天然支持 ISP**——你不需要"实现"一个接口，只需要实现需要的方法即可。

### 5.4 ISP 判断信号

- 你的类中有 `raise NotImplementedError`
- 接口方法分组后可以被自然分开
- 某个客户端只用到了接口的 20% 方法

---

## 6. DIP — 依赖反转原则

> **Dependency Inversion Principle**
> *"High-level modules should not depend on low-level modules. Both should depend on abstractions."*
> — Robert C. Martin

高层模块不应该依赖低层模块，**两者都应该依赖抽象**。
抽象不应该依赖细节，**细节应该依赖抽象**。

### 6.1 DIP ≠ 依赖注入

| 概念 | 说明 |
|------|------|
| **依赖反转（DIP）** | 设计原则：依赖抽象而非具体类 |
| **控制反转（IoC）** | 将控制权交给框架/容器 |
| **依赖注入（DI）** | 一种实现方式：从外部传入依赖 |

DIP 是"WHAT"，DI 是"HOW"。

### 6.2 违反 DIP 的例子

```python
class MySQLDatabase:
    def save(self, data):
        print(f"保存到 MySQL: {data}")

class UserService:
    """高层模块直接依赖低层模块——违反 DIP"""

    def __init__(self):
        self.db = MySQLDatabase()  # ❌ 硬编码依赖

    def create_user(self, name):
        self.db.save({"name": name})
```

如果将来要切换成 PostgreSQL，必须修改 `UserService`。

### 6.3 遵循 DIP 的重构

```python
from abc import ABC, abstractmethod

class Database(ABC):
    """抽象——高层和低层都依赖它"""
    @abstractmethod
    def save(self, data): ...

class MySQLDatabase(Database):
    def save(self, data):
        print(f"保存到 MySQL: {data}")

class PostgreSQLDatabase(Database):
    def save(self, data):
        print(f"保存到 PostgreSQL: {data}")

class UserService:
    """高层依赖抽象，低层也依赖抽象"""

    def __init__(self, db: Database):  # 依赖注入！✅
        self._db = db

    def create_user(self, name):
        self._db.save({"name": name})

# 使用
mysql = MySQLDatabase()
service = UserService(mysql)
service.create_user("Alice")
```

```
依赖流向变化：

   违反 DIP：                       遵循 DIP：
  UserService ──▶ MySQLDatabase     UserService ──▶ Database ◀── MySQLDatabase
                                                        ▲
                                                        │
                                                  PostgreSQLDatabase
    
  高层 → 低层（具体）                高层/低层 → 抽象
```

### 6.4 依赖注入的三种方式

```python
# 方式一：构造器注入（最常用）
class Service:
    def __init__(self, db: Database):
        self._db = db

# 方式二：Setter 注入
class Service:
    def set_db(self, db: Database):
        self._db = db

# 方式三：方法注入
class Service:
    def create_user(self, name, db: Database):
        db.save({"name": name})
```

---

## 7. 设计原则 vs 设计模式

### 7.1 核心区别

```
┌─────────────────────────────────────────────────────────────────┐
│                 设计原则                 │       设计模式         │
├─────────────────────────────────────────────────────────────────┤
│  哲学层面的指导（WHY）                   │  可复用的解决方案（HOW）│
│  抽象、普适、跨语言                      │  具体、有模板、语言相关 │
│  SOLID、DRY、KISS、YAGNI               │  23 种 GoF 模式         │
│  告诉你要"做什么"                       │  告诉你要"怎么做"       │
│  永不"过时"                            │  随技术演进演化         │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 原则指导模式

```
           SOLID 原则（指导思想）
                  │
       ┌──────────┼──────────┐
       │          │          │
       ▼          ▼          ▼
   创建型模式    结构型模式    行为型模式
  (工厂、单例)  (适配器、代理) (策略、观察者)

  举例：
  - OCP → 策略模式（新增策略无需修改上下文）
  - DIP → 工厂模式（通过抽象创建对象）
  - ISP → 适配器模式（小接口更容易适配）
```

### 7.3 学习路径建议

1. **先掌握原则**（理解 WHY）
2. **再学习模式**（掌握 HOW）
3. **在实战中应用**（什么时候用什么）
4. **最终内化**（设计模式变成直觉）

> 掌握原则比记住模式更重要。原则是永恒的，模式是工具。

---

## 8. 实战：重构糟糕代码

> 本节的完整可运行代码在 `code/03-code-refactoring.py`

### 8.1 重构前：意大利面条代码

```python
class OrderProcessor:
    """这个类违反了全部五个 SOLID 原则"""

    def __init__(self):
        self.db = {}          # 临时数据库
        self.log = []         # 日志
        self.total = 0        # 总额

    def process(self, order, user, email):
        # SRP 违反：这个函数做了太多事
        # 1. 验证
        if not order.get("items"):
            raise ValueError("订单为空")
        if not user.get("email"):
            raise ValueError("用户无邮箱")

        # 2. 计算价格
        total = sum(item["price"] * item["qty"] for item in order["items"])
        if user.get("vip"):
            total *= 0.9
        self.total = total

        # 3. 保存
        self.db[order["id"]] = {"order": order, "total": total}
        self.log.append(f"订单 {order['id']} 已保存，金额 {total}")

        # 4. 发送邮件
        print(f"发送邮件到 {email}: 订单 {order['id']} 处理成功，总价 {total}")

        # OCP 违反：新增功能必须改这个函数
        # LSP 违反：没有抽象，无法替换实现
        # DIP 违反：直接依赖 print/数据库实现细节
```

**问题清单：**
- 一个函数做验证、计算、存储、日志、邮件 —— **违反 SRP**
- 新增支付方式、通知方式必须改代码 —— **违反 OCP**
- 没有抽象层，无法用 Mock 替换 —— **违反 LSP**
- 一个巨大的接口，客户端被迫依赖全部 —— **违反 ISP**
- 高层依赖具体的 print/字典 —— **违反 DIP**

### 8.2 重构后：遵循 SOLID

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# ── 数据对象（SRP：只保存数据） ──
@dataclass
class Order:
    id: str
    items: list
    user_id: str

@dataclass
class User:
    id: str
    name: str
    email: str
    is_vip: bool = False

# ── 验证器（SRP：只负责验证） ──
class OrderValidator:
    def validate(self, order: Order, user: User):
        if not order.items:
            raise ValueError("订单为空")
        if not user.email:
            raise ValueError("用户无邮箱")

# ── 价格计算器（SRP：只负责计算） ──
class PriceCalculator(ABC):
    @abstractmethod
    def calculate(self, order: Order, user: User) -> float: ...

class DefaultPriceCalculator(PriceCalculator):
    def calculate(self, order: Order, user: User) -> float:
        total = sum(item["price"] * item["qty"] for item in order.items)
        return total * 0.9 if user.is_vip else total

# ── 存储（SRP + DIP：依赖抽象） ──
class OrderRepository(ABC):
    @abstractmethod
    def save(self, order_id: str, data: dict): ...

class InMemoryOrderRepository(OrderRepository):
    def __init__(self):
        self._store = {}

    def save(self, order_id: str, data: dict):
        self._store[order_id] = data

# ── 通知（SRP + OCP：可扩展） ──
class Notifier(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str): ...

class EmailNotifier(Notifier):
    def send(self, recipient: str, message: str):
        print(f"发送邮件到 {recipient}: {message}")

class SMSNotifier(Notifier):
    def send(self, recipient: str, message: str):
        print(f"发送短信到 {recipient}: {message}")

# ── 日志（SRP） ──
class Logger:
    def __init__(self):
        self._logs = []

    def log(self, message: str):
        self._logs.append(message)
        print(f"[LOG] {message}")

    def get_logs(self):
        return self._logs

# ── 核心处理（OCP + DIP：依赖注入） ──
class OrderProcessor:
    def __init__(self,
                 validator: OrderValidator,
                 calculator: PriceCalculator,
                 repository: OrderRepository,
                 notifier: Notifier,
                 logger: Logger):
        self._validator = validator
        self._calculator = calculator
        self._repository = repository
        self._notifier = notifier
        self._logger = logger

    def process(self, order: Order, user: User) -> float:
        # 验证
        self._validator.validate(order, user)
        # 计算
        total = self._calculator.calculate(order, user)
        # 存储
        self._repository.save(order.id, {"order": order, "total": total})
        # 日志
        self._logger.log(f"订单 {order.id} 已保存，金额 {total}")
        # 通知
        self._notifier.send(user.email, f"订单 {order.id} 处理完成，总价 {total}")
        return total
```

**重构后的优点：**
- ✅ **SRP**：每个类只做一件事
- ✅ **OCP**：新增通知方式不用改核心代码
- ✅ **LSP**：所有实现类都可替换
- ✅ **ISP**：接口小而专
- ✅ **DIP**：高层依赖抽象而非具体

---

## 9. 思考题

1. **SRP 边界问题**：一个类有 5 个公共方法，它们都需要访问同一个私有属性。这算"做了一件事"还是"做了多件事"？边界在哪里？

2. **OCP 与现实**：在产品迭代中，完全"不修改已有代码"几乎不可能。你怎样在实际工作中平衡 OCP 原则与快速迭代的需求？

3. **LSP 的 Python 特色**：Python 的鸭子类型在哪些方面自然地实现了 LSP？在哪些方面反而容易导致 LSP 违反？

4. **ISP vs 接口数量**：拆分接口到多细合适？请列举"过度拆分"带来的问题。

5. **DIP 实战思考**：在你的项目中，有没有哪个模块因为直接依赖了具体实现而难以测试？用 DIP + DI 重构后，测试会有什么变化？

---

> **下一章预告：Day 42 — 类型注解（Type Hints）**

