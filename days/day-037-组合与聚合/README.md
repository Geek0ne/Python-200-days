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

**参考答案**

```python
# ── 方式一：继承（is-a）──
class Bird:
    def eat(self):
        return "吃东西"

    def fly(self):
        return "飞翔"

class Eagle(Bird):
    pass  # 老鹰会飞，直接继承即可

class Penguin(Bird):
    def fly(self):
        # 企鹅不会飞，被迫覆盖父类方法，调用方若按 Bird 使用会出错
        raise NotImplementedError("企鹅不会飞")

class Duck(Bird):
    def swim(self):
        return "游泳"

# ── 方式二：组合（has-a），把「行为」拆成独立对象 ──
class FlyBehavior:
    def fly(self):
        return "展翅高飞"

class NoFly:
    def fly(self):
        return "不会飞"

class SwimBehavior:
    def swim(self):
        return "游泳"

class ComposedBird:
    def __init__(self, fly_behavior, swim_behavior=None):
        self.fly_behavior = fly_behavior      # 注入飞行能力
        self.swim_behavior = swim_behavior    # 注入游泳能力（可选）

    def fly(self):
        return self.fly_behavior.fly()        # 委托给行为对象

    def swim(self):
        if self.swim_behavior is None:
            return "不会游泳"
        return self.swim_behavior.swim()

# 同一套零件，组装出不同的鸟
eagle = ComposedBird(FlyBehavior())
penguin = ComposedBird(NoFly(), SwimBehavior())
duck = ComposedBird(FlyBehavior(), SwimBehavior())
print(eagle.fly())
print(penguin.fly())
print(duck.swim())
```

预期输出：

```
展翅高飞
不会飞
游泳
```

对比：继承写法简单直观，但 `Penguin` 被迫覆盖 `fly()`，任何把企鹅当普通 `Bird` 调用的代码都会踩坑（违反「里氏替换」——子类应能无缝替换父类）；而且「会不会飞」「会不会游泳」两个维度交叉时，子类数量会爆炸。组合写法把能力做成可插拔的对象，企鹅、鸭子只是「装配方案」不同，还能在运行时换行为（比如给受伤的鹰临时换成 `NoFly`），代价是类更多、要多写一层委托代码。

2. **组合 vs 聚合**：举出三个组合的例子和三个聚合的例子，说明为什么选择那种关系。

**参考答案**

判断标准只有一条：**「部分」能不能脱离「整体」独立存在？整体创建时是否负责创建部分、整体销毁时部分是否随之消亡？** 是 → 组合；否 → 聚合。

组合的例子（强拥有，生命周期绑定）：

- **房子 → 房间**：房间在盖房子时才产生，房子拆了房间也不复存在，房间不能「搬」到别的房子里。代码上表现为 `House.__init__` 内部自己 `Room(...)`。
- **订单 → 订单明细行**：明细行依附于订单，订单取消后明细行没有独立意义，通常随订单一起创建和删除。
- **文章 → 段落**：段落是文章的组成部分，文章删掉后段落对象也失去归属（这里指建模上的从属关系，而非文本复制）。

聚合的例子（弱拥有，部分可独立存在）：

- **部门 → 老师/员工**：员工先于部门存在，部门撤销后员工可以转岗，人不是部门「造」出来的。代码上表现为对象从外部传入 `add_teacher(teacher)`。
- **歌单 → 歌曲**：歌曲属于曲库，删除歌单不会删除歌曲，同一首歌还能进别的歌单。
- **停车场 → 汽车**：车开进来只是暂时停放，停车场关闭后车照样存在。

💡 提示：Python 里两者代码形态很像（都是持有引用），区别主要体现在「谁负责创建/销毁」的设计意图上；拿不准时先按组合建模，需要共享或替换时再放宽为聚合。

3. **依赖注入的优缺点**：依赖注入虽然降低了耦合，但也增加了代码复杂度。在什么场景下值得使用依赖注入？什么场景下简单硬编码反而更好？

**参考答案**

依赖注入（DI）就是把对象需要的「帮手」（依赖）从外部传进来，而不是在内部自己 `new` 一个。它的收益是**可替换、可测试**，代价是**多一层参数传递和装配代码**。值不值得，取决于这个依赖将来会不会变、要不要被单独测试。

值得用 DI 的场景：

- **依赖有多种实现或将来会换**：数据库（MySQL/PostgreSQL）、支付渠道、短信/邮件服务商。注入接口后，换实现只改装配处，不动业务代码。
- **需要单元测试**：把真实数据库、网络请求换成假的（Mock）对象注入，测试就能离线、快速、可控地跑。
- **依赖是「重」资源或有副作用**：连接、文件、时钟、随机数。注入后可以在测试里固定时间/随机种子，让结果可复现。

硬编码反而更好的场景：

- **依赖稳定且唯一**：比如一个函数内部用 `math.sqrt`、`json.dumps`，这些标准工具没有替换需求，注入只会徒增参数。
- **一次性脚本、小工具、原型**：代码量小、生命周期短，DI 带来的装配复杂度超过收益，直接写死更清晰。
- **依赖是纯粹的内部实现细节**：外部根本不关心、也不会替换它，暴露成注入参数反而泄露了内部结构。

一句话：**「会变的、要测的、有副作用的」依赖值得注入；「稳定的、纯内部的、用完即弃的」依赖直接硬编码。** 不要为了模式而模式。

4. **「优先组合」的例外**：标准库中有哪些经典的使用继承的场景（如 Django 的 Model、Flask 的 View）？这些场景为什么使用继承而不是组合？

**参考答案**

先澄清一点：Django 的 `Model`、Flask 的 `View` 其实是**第三方框架**，不是标准库。不过它们和标准库里的一些例子属于同一类——**框架预留「挂钩点」让你继承**。标准库里的经典继承场景有：

- **自定义异常**：`class MyError(Exception)`。异常体系是稳定的 is-a 层次，`except` 按类型捕获，必须靠继承才能被正确识别。
- **`threading.Thread`**：继承后重写 `run()` 定义线程要干的活。
- **`unittest.TestCase`**：继承后写 `test_xxx` 方法，框架自动发现并运行。
- **`http.server.BaseHTTPRequestHandler`**：重写 `do_GET()` 等方法处理请求。
- **`collections.UserDict / UserList / UserString`**：官方推荐用它们做基类来定制容器，比直接继承 `dict/list` 更安全。
- **`enum.Enum`、`abc.ABC`、`logging.Handler`**：都是「继承以接入框架机制」的典型。

为什么这些场景用继承而非组合？

- **真正的 is-a + 多态需求**：框架要把你的对象当成「某一类东西」统一调度（异常要被 `except` 捕获、测试要被 runner 发现、线程要被调度器启动）。这种「按类型识别」的能力组合给不了。
- **模板方法模式**：基类把整体流程骨架固定好，只留几个「钩子方法」让你重写。你填的是稳定的空，而不是替换整个行为，所以不存在「企鹅被迫飞」那种问题。
- **框架掌控创建与生命周期**：对象往往由框架实例化和调用，你没有机会从外部「注入」一个组合好的对象，继承是最自然的接入方式。

💡 提示：这些例外的共同点是「层次稳定 + 框架要求按类型识别 + 只重写少量钩子」。一旦你要复用代码、或子类得覆盖大半方法，就该回到组合。

5. **无限递归问题**：如果两个对象互相组合（A has-a B，B has-a A），会有什么问题？如何避免？

**参考答案**

两个对象互相持有引用，就形成了**循环引用**（A 里有 B，B 里又有 A）。它本身在 Python 里是合法的，普通属性访问完全正常，但会在几个地方埋雷：

- **打印 / 序列化无限递归**：`__repr__`、`json.dumps`、`copy.deepcopy` 等会顺着引用一路走下去，A→B→A→B…… 直到栈溢出抛 `RecursionError`。
- **构造顺序「先有鸡还是先有蛋」**：A 创建时需要 B，B 创建时又需要 A，没法在构造器里一次性互相传好，只能先建一个再补设反向引用。
- **内存回收变慢**：循环引用让「引用计数」无法归零，得靠循环垃圾回收器额外处理；若还定义了 `__del__`，情况更复杂。
- **耦合过紧**：两个对象死死绑在一起，难以单独测试或替换。

下面这段演示「访问正常、打印却递归」：

```python
class A:
    def __init__(self):
        self.b = None
    def __repr__(self):
        return f"A(b={self.b})"   # 打印自己时又去打印 b

class B:
    def __init__(self):
        self.a = None
    def __repr__(self):
        return f"B(a={self.a})"   # 打印自己时又去打印 a

a, b = A(), B()
a.b = b        # A has-a B
b.a = a        # B has-a A，形成循环引用

# 普通属性访问没问题：绕一圈还能回到自己
print(a.b.a is a)

# 但打印 / 序列化会无限递归
try:
    print(a)
except RecursionError:
    print("捕获到 RecursionError：__repr__ 无限递归")
```

预期输出：

```
True
捕获到 RecursionError：__repr__ 无限递归
```

如何避免：

- **改成单向引用 + 用 ID 反查**：只让 A 持有 B，B 不持有 A，需要时通过一个「注册表/字典」按 ID 找到对方。
- **反向引用用弱引用 `weakref`**：`B.a = weakref.ref(a)`，弱引用不增加引用计数，既打破循环又不影响回收。
- **引入中间人（中介者/事件总线）**：A、B 都只跟中间人通信，彼此不直接持有，彻底解耦。
- **`__repr__` 只打印标识而非整个对象**：比如打印 `id` 或名字，避免顺着引用递归。

⚠️ 注意：循环引用不等于「内存泄漏」——Python 的循环 GC 通常能回收它们，真正要防的是递归打印/序列化和过度耦合。

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
