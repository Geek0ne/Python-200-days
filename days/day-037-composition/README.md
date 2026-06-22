# Day 037 — 组合与聚合

> 掌握组合 vs 继承的权衡、依赖注入模式，实战汽车-引擎-轮胎模型

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 组合 vs 继承 | ⭐⭐⭐ | 两种代码复用方式的对比与选择 |
| 聚合 | ⭐⭐ | 「拥有」关系与生命周期管理 |
| 依赖注入 | ⭐⭐⭐ | 松耦合的设计模式 |
| 优先组合原则 | ⭐⭐ | 「组合优于继承」的设计哲学 |
| 实战：汽车模型 | ⭐⭐⭐⭐ | 完整的汽车-引擎-轮胎系统 |

---

## 一、组合（Composition）

### 1.1 什么是组合

**组合** 是一种 **「has-a」**（有一个）关系，通过将一个对象作为另一个对象的成员来实现功能复用。

```
┌───────────────────────┐
│        Computer       │
│                       │
│  ┌─────────────────┐  │
│  │     CPU          │  │  ← Computer has-a CPU
│  │  model: str      │  │     （组合）
│  │  speed: GHz     │  │
│  └─────────────────┘  │
│                       │
│  ┌─────────────────┐  │
│  │     RAM          │  │  ← Computer has-a RAM
│  │  size: GB       │  │     （组合）
│  │  type: str      │  │
│  └─────────────────┘  │
│                       │
│  ┌─────────────────┐  │
│  │     Disk         │  │  ← Computer has-a Disk
│  │  capacity: TB   │  │     （组合）
│  │  type: SSD/HDD │  │
│  └─────────────────┘  │
└───────────────────────┘
```

### 1.2 组合的实现

```python
class CPU:
    def __init__(self, model: str, speed: float):
        self.model = model
        self.speed = speed

    def process(self) -> str:
        return f"{self.model} @ {self.speed}GHz 正在处理..."

class RAM:
    def __init__(self, size: int, type_: str):
        self.size = size
        self.type = type_

class Disk:
    def __init__(self, capacity: int, type_: str):
        self.capacity = capacity
        self.type = type_

class Computer:
    """计算机 —— 通过组合 CPU、RAM、Disk 实现功能"""
    def __init__(self, cpu: CPU, ram: RAM, disk: Disk):
        self.cpu = cpu      # 组合：Computer has-a CPU
        self.ram = ram      # 组合：Computer has-a RAM
        self.disk = disk    # 组合：Computer has-a Disk

    def boot(self) -> str:
        return self.cpu.process()

# 使用组合
cpu = CPU("Intel i7", 3.5)
ram = RAM(16, "DDR5")
disk = Disk(512, "SSD")
pc = Computer(cpu, ram, disk)
print(pc.boot())
```

---

## 二、继承（Inheritance）

### 2.1 继承的问题

继承建立的是 **「is-a」**（是一个）关系，但滥用继承会导致：

```
继承的陷阱：                       组合的替代：
══════════════                     ══════════════

❌ Duck extends Bird               ✅ Duck has-a Wing
   → Duck 必须继承 Bird 的所有行为      → 选择需要的行为
   → 如果 Bird 有 fly()，              → 不会继承不需要的 fly()
     不能飞的 Duck 就尴尬了

❌ Stack extends List               ✅ Stack has-a List
   → Stack 不会想继承 insert()          → 只暴露 push/pop
   → 不安全！可以中间插入元素

❌ ElectricCar extends Car           ✅ ElectricCar has-a Engine
   → Car 有 gas_tank                    → 换成 Battery
   → ElectricCar 不需要
```

### 2.2 继承 vs 组合对比

```
特性             继承 (is-a)              组合 (has-a)
═══════════════ ═════════════════════      ═════════════════════

关系              类层次结构                   对象引用

复用粒度          整个类                       对象方法

耦合度            高（子类依赖父类）             低（通过接口依赖）

灵活性            低（继承是静态的）             高（运行时替换）

代码重用          ⚠️ 容易破坏封装              ✅ 安全

「脆弱的基类问题」    ⚠️ 父类变化影响全部子类    ✅ 不受影响

测试             困难（需要基类上下文）        容易（Mock 依赖）

何时使用          真正的「is-a」关系             大多数情况
```

---

## 三、聚合（Aggregation）

### 3.1 组合 vs 聚合

组合和聚合都是 **「has-a」** 关系，但区别在于 **生命周期管理**：

```
组合 (Composition)                 聚合 (Aggregation)
══════════════════                 ══════════════════

「部分」的生命周期由「整体」管理      「部分」可以独立于「整体」存在
整体销毁 → 部分也销毁               整体销毁 → 部分继续存在
强拥有关系                         弱拥有关系

┌────────────┐                   ┌────────────┐
│    House   │                   │ Department │
│  ┌──────┐  │                   │  ┌──────┐  │
│  │ Room │  │  ← 房间不能       │  │Teacher│  │  ← 老师可以
│  └──────┘  │     离开房子       │  └──────┘  │     换部门
│  ┌──────┐  │                   │  ┌──────┐  │
│  │ Room │  │                   │  │Teacher│  │
│  └──────┘  │                   │  └──────┘  │
└────────────┘                   └────────────┘
```

```python
# 🏠 组合：房间的生命周期属于房子
class Room:
    def __init__(self, name: str):
        self.name = name

class House:
    def __init__(self):
        self.rooms = [Room("客厅"), Room("卧室")]  # 在 House 中创建
    # 当 House 被销毁时，Room 也被销毁

# 🏫 聚合：老师可以独立于部门存在
class Teacher:
    def __init__(self, name: str):
        self.name = name

class Department:
    def __init__(self, name: str):
        self.name = name
        self.teachers: list[Teacher] = []  # 从外部传入

    def add_teacher(self, teacher: Teacher):
        self.teachers.append(teacher)
    # 当 Department 被销毁时，Teacher 继续存在
```

### 3.2 选择指南

```
创建对象的生命周期由谁管理？
│
├─ 整体负责创建和销毁 → 组合 (Composition)
│   例：汽车 → 引擎（引擎随汽车一起创建和销毁）
│
├─ 部分可以独立存在 → 聚合 (Aggregation)
│   例：学校 → 老师（老师离开学校后仍是老师）
│
└─ 不确定 → 先用组合，需要时再改为聚合
```

---

## 四、依赖注入（Dependency Injection）

### 4.1 为什么需要依赖注入

```python
# ❌ 紧耦合：类自己创建依赖
class EmailService:
    def __init__(self):
        self.smtp = SMTPConnection()  # 硬编码，难以替换

# ✅ 松耦合：依赖从外部注入
class EmailService:
    def __init__(self, smtp_connection):
        self.smtp = smtp_connection  # 从外部传入，灵活替换
```

### 4.2 依赖注入的三种方式

```python
# 1️⃣ 构造器注入（最常用）
class NotificationService:
    def __init__(self, sender):
        self.sender = sender  # 通过构造器注入

# 2️⃣ Setter 注入
class NotificationService:
    def set_sender(self, sender):
        self.sender = sender  # 通过 setter 注入

# 3️⃣ 方法注入
class NotificationService:
    def send(self, message, sender):
        sender.send(message)   # 直接在方法参数中注入
```

### 4.3 依赖注入的优势

```
紧耦合：                          松耦合（依赖注入）：
══════════                        ═══════════════════

class ReportGenerator:             class ReportGenerator:
    def __init__(self):                def __init__(self, db, formatter):
        self.db = MySQLDB()                self.db = db
        self.formatter = HTMLFmt()         self.formatter = formatter

    def generate(self):                def generate(self):
        data = self.db.fetch()              data = self.db.fetch()
        return self.formatter.format(data)  return self.formatter.format(data)

问题：                             优势：
• 测试时必须连接真实数据库         • 测试时注入 MockDB
• 要改成 PostgreSQL 要改代码        • 切换数据库只需注入不同的 db
• 要改成 PDF 格式要改代码           • 切换格式只需注入不同的 formatter
• 代码难以复用                      • 高度可复用
```

---

## 五、设计原则：优先组合而非继承

### 5.1 「Favor Composition over Inheritance」

这是《设计模式》一书的核心原则之一：

```python
# ❌ 继承 —— 「is-a」
class Bird:
    def fly(self): ...
    def eat(self): ...

class Penguin(Bird):
    def fly(self):      # ❌ 企鹅不会飞！
        raise NotImplementedError

# ✅ 组合 —— 「has-a」
class FlyBehavior:
    def fly(self): return "飞翔中..."

class WalkBehavior:
    def fly(self): return "我不会飞，但我会走"

class Bird:
    def __init__(self, fly_behavior):
        self.fly_behavior = fly_behavior

    def fly(self):
        return self.fly_behavior.fly()

eagle = Bird(FlyBehavior())
penguin = Bird(WalkBehavior())
```

### 5.2 什么时候应该用继承？

| 应该使用继承 | 不应该使用继承 |
|------------|--------------|
| 真正的是「is-a」关系 | 只是为了复用代码 |
| 子类不会改变父类的核心行为 | 子类需要覆盖大部分方法 |
| 层次结构稳定不变 | 需求可能频繁变化 |
| 框架强制要求（如 Django Model） | 「has-a」关系更符合直觉 |

---

## 六、实战：汽车-引擎-轮胎模型

```
┌──────────────────────────────────────────┐
│                 Car                       │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │            Engine                │   │  ← 组合（随汽车创建/销毁）
│  │  +start() → 发动                 │  │
│  │  +stop() → 熄火                   │  │
│  │  -_running: bool                 │  │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │      Tire (4 个实例)              │   │  ← 聚合（可以单独更换）
│  │  +inflate(psi)                    │  │
│  │  +get_pressure()                  │  │
│  │  +check_tread()                   │  │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │         Transmission             │   │  ← 组合
│  │  +shift(gear)                    │  │
│  │  +get_gear()                     │  │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │         FuelTank                 │   │  ← 组合
│  │  +refill(liters)                  │  │
│  │  +consume(liters)                 │  │
│  │  +get_level()                     │  │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │         GPS (依赖注入)            │   │  ← 聚合（可选组件）
│  │  +navigate(dest)                  │  │
│  └──────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

### 核心实现

```python
from typing import List, Optional


class Engine:
    """引擎 —— 组合关系（随 Car 创建/销毁）"""

    def __init__(self, horsepower: int, fuel_type: str = "汽油"):
        self.horsepower = horsepower
        self.fuel_type = fuel_type
        self._running = False
        self._rpm = 0

    def start(self) -> str:
        self._running = True
        self._rpm = 800
        return f"🚗 引擎启动 ({self.fuel_type}, {self.horsepower}HP)"

    def stop(self) -> str:
        self._running = False
        self._rpm = 0
        return "引擎熄火"

    def accelerate(self, amount: int) -> str:
        if not self._running:
            return "请先启动引擎"
        self._rpm = min(self._rpm + amount, 7000)
        return f"转速: {self._rpm} RPM"

    @property
    def is_running(self) -> bool:
        return self._running


class Tire:
    """轮胎 —— 聚合关系（可以独立于 Car 存在/更换）"""

    def __init__(self, brand: str, size: str = "205/55R16"):
        self.brand = brand
        self.size = size
        self._pressure = 32.0  # PSI
        self._tread_depth = 8.0  # mm

    def inflate(self, psi: float) -> str:
        if psi < 20 or psi > 50:
            return f"❌ 胎压 {psi} PSI 超出安全范围"
        self._pressure = psi
        return f"✅ 胎压调整至 {psi} PSI"

    def get_pressure(self) -> float:
        return self._pressure

    def check_tread(self) -> str:
        if self._tread_depth < 1.6:
            return "⚠️ 胎纹深度不足，需要更换！"
        return f"✅ 胎纹深度: {self._tread_depth}mm"

    def wear(self, amount: float = 0.1):
        """轮胎磨损"""
        self._tread_depth = max(0, self._tread_depth - amount)

    def __repr__(self):
        return f"Tire({self.brand} {self.size})"


class GPS:
    """GPS 导航 —— 依赖注入（可选组件）"""

    def __init__(self, model: str):
        self.model = model

    def navigate(self, destination: str) -> str:
        return f"🗺️ [{self.model}] 导航到 {destination}..."

    def get_location(self) -> str:
        return "当前位置: 未知"


class Car:
    """汽车 —— 组合 + 聚合 + 依赖注入的综合应用"""

    def __init__(
        self,
        brand: str,
        model: str,
        engine: Engine,          # 组合：构造器中创建
        tires: List[Tire],       # 聚合：可以外部传入/更换
        gps: Optional[GPS] = None,  # 依赖注入：可选
    ):
        self.brand = brand
        self.model = model
        self.engine = engine
        self.tires = tires
        self.gps = gps
        self._speed = 0
        self._odometer = 0.0

    # ── 控制方法 ──

    def start(self) -> str:
        if len(self.tires) < 4:
            return "❌ 轮胎不足 4 个，无法启动！"
        return self.engine.start()

    def stop(self) -> str:
        result = [self.engine.stop()]
        self._speed = 0
        return "\n".join(result)

    def accelerate(self, amount: int = 10) -> str:
        if not self.engine.is_running:
            return "请先启动引擎"
        self._speed = min(self._speed + amount, 200)
        self._odometer += amount * 0.01
        return f"加速至 {self._speed} km/h"

    def brake(self, amount: int = 20) -> str:
        self._speed = max(0, self._speed - amount)
        return f"减速至 {self._speed} km/h"

    # ── 轮胎管理 ──

    def check_tires(self) -> List[str]:
        return [t.check_tread() for t in self.tires]

    def replace_tire(self, index: int, new_tire: Tire) -> str:
        """更换轮胎（聚合关系的灵活性）"""
        if 0 <= index < len(self.tires):
            old = self.tires[index]
            self.tires[index] = new_tire
            return f"轮胎 {index + 1} 已更换: {old} → {new_tire}"
        return "❌ 轮胎索引无效"

    # ── GPS 功能 ──

    def set_gps(self, gps: GPS) -> None:
        """注入 GPS"""
        self.gps = gps

    def navigate(self, destination: str) -> str:
        if not self.gps:
            return "❌ 未安装 GPS 导航"
        return self.gps.navigate(destination)

    # ── 信息 ──

    def info(self) -> str:
        lines = [
            f"🚗 {self.brand} {self.model}",
            f"引擎: {self.engine.fuel_type} {self.engine.horsepower}HP",
            f"速度: {self._speed} km/h",
            f"里程: {self._odometer:.1f} km",
            f"轮胎: {len(self.tires)} 个 ({self.tires[0].brand if self.tires else '无'})",
            f"GPS: {self.gps.model if self.gps else '未安装'}",
        ]
        return "\n".join(lines)


# 使用示例
engine = Engine(200, "汽油")
tires = [
    Tire("米其林"), Tire("米其林"),
    Tire("米其林"), Tire("米其林"),
]
gps = GPS("高德导航")

my_car = Car("丰田", "凯美瑞", engine, tires, gps)
print(my_car.start())
print(my_car.accelerate(50))
print(my_car.check_tires())
print(my_car.navigate("天安门"))
print(my_car.info())
```

---

## 七、思考题

1. **继承 vs 组合**：设计一个「鸟类」系统，包含会飞的（老鹰）、不会飞的（企鹅）、会游泳的（鸭子）。用继承和组合两种方式实现，对比各自的优缺点。

2. **组合 vs 聚合**：举出三个组合的例子和三个聚合的例子，说明为什么选择那种关系。

3. **依赖注入的优缺点**：依赖注入虽然降低了耦合，但也增加了代码复杂度。在什么场景下值得使用依赖注入？什么场景下简单硬编码反而更好？

4. **「优先组合」的例外**：标准库中有哪些经典的使用继承的场景（如 Django 的 Model、Flask 的 View）？这些场景为什么使用继承而不是组合？

5. **无限递归问题**：如果两个对象互相组合（A has-a B，B has-a A），会有什么问题？如何避免？

---

## 📝 本章小结

```
✅ 组合 —— 「has-a」关系，灵活复用
✅ 聚合 —— 弱拥有关系，部分可独立存在
✅ 继承 —— 「is-a」关系，但容易过度使用
✅ 依赖注入 —— 通过构造器/setter/方法注入依赖
✅ 组合优于继承 —— 设计模式核心原则
✅ 实战：汽车模型 —— 组合 + 聚合 + DI 综合示例
```
