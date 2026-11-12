# Day 044 — 枚举与常量

> 枚举（Enum）是 Python 3.4（PEP 435）引入的一种**符号常量**机制。它让你定义一组有名字的常量，使代码更可读、更安全、更易维护。如果说 `@dataclass` 是"装数据的类"，那么 `Enum` 就是"命名常量的类"。

---

## 概述

```python
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3
```

**这行代码做了什么？** 它定义了一组枚举成员（`Color.RED`、`Color.GREEN`、`Color.BLUE`），每个成员都是 `Color` 类的**唯一单例实例**。从此你可以写 `Color.RED` 而不是魔法数字 `1`。

---

## 1. 为什么需要枚举？

### 1.1 不用枚举的问题

```python
# ❌ 方式一：魔法数字
status = 1  # 1 是什么意思？已支付？已发货？已取消？

# ❌ 方式二：模块级常量
PENDING = 0
PAID = 1
SHIPPED = 2
status = PAID  # 好一点，但仍然不安全
status = 999   # ❌ 没有类型检查，传什么都行

# ❌ 方式三：字符串常量
STATUS_PENDING = "pending"
STATUS_PAID = "paid"
print(STATUS_PAID == "paid")   # True，但不是单例，可被任意字符串替换
```

**三个核心痛点：**
1. **可读性差** — 数字/字符串的含义需要在脑子里映射
2. **不安全** — 可以传入任何无效值，无编译/运行时检查
3. **不可迭代** — 不能方便地列出所有有效值

### 1.2 枚举的解决方案

```python
from enum import Enum

class OrderStatus(Enum):
    PENDING = 0
    PAID = 1
    SHIPPED = 2
    DELIVERED = 3

# ✅ 可读：self-explanatory
status = OrderStatus.PAID

# ✅ 安全：类型检查
# status = 999  # ❌ 类型错误，IntEnum 除外

# ✅ 单例：每个成员全局唯一
assert OrderStatus.PAID is OrderStatus.PAID  # True

# ✅ 可迭代：列出所有合法状态
for s in OrderStatus:
    print(s.name, s.value)

# ✅ 可比较：推荐用 is 而非 ==
if status is OrderStatus.PAID:
    print("已支付")
```

---

## 2. Enum 核心概念与设计原理

### 2.1 枚举成员是单例

每个枚举成员在类定义时被实例化一次，之后全局只存在这一个实例：

```python
from enum import Enum

class Status(Enum):
    OK = 200
    NOT_FOUND = 404

a = Status.OK
b = Status.OK
print(a is b)          # True — 同一个实例
print(a is Status.OK)  # True — 也是同一个实例
```

**为什么是单例？** 枚举的核心目的是**定义一组固定的命名值**。如果每次访问都创建新实例，那就失去了"同一性"的语义。`Status.OK` 必须始终指向同一个对象，才能用 `is` 做恒等比较。

### 2.2 枚举成员是不可变的

一旦定义，枚举成员的值不能修改：

```python
Status.OK = 201  # ❌ AttributeError: Cannot reassign members.
```

### 2.3 枚举成员名和值

每个枚举成员有两个关键属性：
- `.name` — 成员的名字（字符串），如 `"OK"`
- `.value` — 成员的值，如 `200`

```python
print(Status.OK.name)   # 'OK'
print(Status.OK.value)  # 200
```

### 2.4 枚举的成员是类，不是实例的"属性"

```python
# 成员是类属性
print(Status.OK)     # Status.OK
print(type(Status.OK))  # <enum 'Status'>

# 但不是常规类属性——枚举通过 metaclass 控制
```

枚举的底层依靠 `EnumMeta`（元类）实现。当定义枚举类时，元类会收集所有类属性，将枚举成员转换为枚举类型的实例，并阻止这些属性被覆盖。

---

## 3. Enum 定义方式与常用基类

### 3.1 基本 Enum

```python
from enum import Enum

class Direction(Enum):
    NORTH = 1
    SOUTH = 2
    EAST = 3
    WEST = 4
```

### 3.2 `IntEnum` — 可当作整数使用的枚举

```python
from enum import IntEnum

class StatusCode(IntEnum):
    OK = 200
    NOT_FOUND = 404
    ERROR = 500

print(StatusCode.OK == 200)    # True — 可以直接和整数比较
print(StatusCode.OK + 100)     # 300 — 可以进行整数运算
print(isinstance(StatusCode.OK, int))  # True
```

**何时用 IntEnum？** 当你需要与整数兼容时（如 HTTP 状态码、协议字段、位掩码）。但注意：它放弃了类型安全性！

### 3.3 `StrEnum`（Python 3.11+）— 可当作字符串的枚举

```python
from enum import StrEnum

class Color(StrEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"

print(Color.RED == "red")      # True
print(Color.RED.upper())       # "RED"
```

### 3.4 IntFlag — 位标志枚举

```python
from enum import IntFlag

class Permission(IntFlag):
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 4

perm = Permission.READ | Permission.WRITE  # 组合
print(Permission.READ in perm)  # True
```

---

## 4. `@unique` 装饰器与唯一性保证

### 4.1 默认：值可以重复（别名）

Python 枚举**允许不同的成员拥有相同的值**，但后定义的会变成别名：

```python
from enum import Enum

class Color(Enum):
    RED = 1
    CRIMSON = 1  # 这是 RED 的别名！
    GREEN = 2
    BLUE = 3

print(Color(1))      # Color.RED — 第一个定义的获胜
print(Color.CRIMSON) # Color.RED — 实际上是同一个成员
print(Color.CRIMSON is Color.RED)  # True
```

**别名有什么用？** 同一状态的不同命名：
```python
class Status(Enum):
    OK = 200
    SUCCESS = 200  # 别名：OK 的另一种叫法
    NOT_FOUND = 404
```

### 4.2 `@unique` 强制唯一值

如果你希望**每个值唯一**（绝大多数场景），用 `@unique`：

```python
from enum import Enum, unique

@unique
class Color(Enum):
    RED = 1
    CRIMSON = 1  # ❌ ValueError: duplicate value found!
    GREEN = 2
    BLUE = 3
```

**最佳实践**：除非有明确的原因需要别名，否则始终使用 `@unique`。它能让你尽早发现值冲突的 bug。

---

## 5. `auto()` 与自定义值

### 5.1 `auto()` 自动赋值

`auto()` 自动为枚举成员分配值，默认从 1 开始递增：

```python
from enum import Enum, auto

class Color(Enum):
    RED = auto()    # 1
    GREEN = auto()  # 2
    BLUE = auto()   # 3

print(list(Color))
# [<Color.RED: 1>, <Color.GREEN: 2>, <Color.BLUE: 3>]
```

**为什么从 1 开始而不是 0？** 因为 0 在布尔上下文中是 falsy，容易导致微妙 bug。枚举的第一个有效值应该 truthy。

### 5.2 自定义 auto() 行为

你可以覆盖 `_generate_next_value_` 方法改变自动赋值逻辑：

```python
class AutoName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name.upper()  # 用成员名作为值

class Color(AutoName):
    RED = auto()    # "RED"
    GREEN = auto()  # "GREEN"
    BLUE = auto()   # "BLUE"
```

或者自定义递增策略：

```python
class Sequential(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return count + 1  # 从 1 开始计数

class Day(Sequential):
    MON = auto()  # 1
    TUE = auto()  # 2
    WED = auto()  # 3
```

### 5.3 混合赋值

你可以混合使用 `auto()` 和显式值：

```python
class HttpStatus(Enum):
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    # ... 其他
    REDIRECT = auto()  # 203？不，auto() 不会接着 202，它从 1 开始
```

> ⚠️ 注意：`auto()` 不会"接着上一个值"——它的计数器是全局的。混合赋值时小心值意外冲突。

---

## 6. 枚举的高级用法

### 6.1 枚举方法与自定义方法

枚举类可以有方法：

```python
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3

    @property
    def hex_value(self):
        return {1: "#FF0000", 2: "#00FF00", 3: "#0000FF"}[self.value]

    def is_warm(self):
        return self in (Color.RED,)

print(Color.RED.hex_value)  # "#FF0000"
print(Color.BLUE.is_warm())  # False
```

### 6.2 枚举的查找

Python 枚举支持三种查找方式：

```python
# 1. 按名字查找
Color["RED"]  # Color.RED

# 2. 按值查找
Color(1)      # Color.RED

# 3. 按成员
Color(Color.RED)  # Color.RED（返回自身）
```

### 6.3 枚举成员装饰器

Python 3.11+ 支持在枚举成员上使用装饰器：

```python
from enum import Enum, property as enum_property

class Status(Enum):
    OK = 200
    ERROR = 500

    @enum_property
    def is_error(self):
        return self.value >= 500
```

### 6.4 枚举的序列化

```python
import json
from enum import Enum

class Color(Enum):
    RED = 1
    GREEN = 2

class ColorEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Color):
            return {"name": obj.name, "value": obj.value}
        return super().default(obj)

# 或者使用自定义 JSON 序列化方案（如 .value）
json.dumps(Color.RED.value)  # "1"
```

---

## 7. 实战：订单状态机

这个实战案例展示枚举如何实现一个**完整的状态机**，确保订单在正确的状态之间流转，拒绝非法转换。

### 7.1 状态转移规则

```
PENDING → PROCESSING → SHIPPED → DELIVERED
    ↑         ↓
    └── CANCELLED ←───┘
```

规则：
- `PENDING` 可转 `PROCESSING` 或 `CANCELLED`
- `PROCESSING` 可转 `SHIPPED` 或 `CANCELLED`
- `SHIPPED` 可转 `DELIVERED`
- `DELIVERED` 和 `CANCELLED` 是终态
- 非法转换抛出异常

### 7.2 完整实现见 `code/03-state-machine.py`

---

## 8. Enum vs 其他方案对比

| 特性 | 模块级常量 | 普通类常量 | Enum | 第三方库（aenum） |
|------|-----------|-----------|------|------------------|
| 类型安全 | ❌ | ❌ | ✅ | ✅ |
| 可迭代 | ❌ | ❌ | ✅ | ✅ |
| 可序列化 | ✅ | ✅ | ⚠️ 需自定义 | ✅ |
| 单例保证 | ❌ | ❌ | ✅ | ✅ |
| 反向查找 | ❌ | ❌ | ✅ | ✅ |
| 位运算 | ❌ | ❌ | IntFlag 支持 | ✅ |
| 继承 | N/A | ✅ | ✅ | ✅ |
| Python 内置 | ✅ | ✅ | ✅ | ❌ |

**结论**：
- **简单常量值**（2-3 个散落常量）→ 模块级常量足够
- **相关常量组**（5+ 个同语义常量）→ **用 Enum** 🌟
- **需要整数兼容**（HTTP 状态码等）→ `IntEnum`
- **需要位标志**（权限、选项）→ `IntFlag`

---

## 9. 思维导图

```mermaid
mindmap
  root((枚举与常量))
    为什么需要枚举
      魔法数字问题
      类型不安全
      缺乏迭代能力
    核心特性
      成员是单例
      成员不可变
      name 和 value
      支持 is 比较
    基类选择
      Enum
      IntEnum
      StrEnum
      IntFlag
    @unique
      防止值重复
      别名检查
    auto()
      自动赋值
      自定义生成策略
    高级用法
      自定义方法
      枚举查找
      序列化
      状态机
    实战
      订单状态机
      游戏状态管理
      协议字段定义
```

---

## 10. 思考题

1. **为什么 Enum 成员默认从 1 开始而不是 0？** 答案在 `auto()` 设计理据中。

**参考答案**

因为 **0 在布尔上下文里是「假」（falsy）**，而从 1 开始能保证第一个成员是「真」（truthy），避免一类隐蔽 bug。

设想 `auto()` 从 0 开始：`Color.RED = 0`。那么 `if Color.RED:` 会被判为 False——明明是一个合法的颜色成员，却在条件判断里「消失」了。类似地，`while member:`、`member or default` 这类写法都会因为 0 是 falsy 而出错。让自动值从 1 起跳，就保证了「任何枚举成员都是 truthy」，条件判断更符合直觉。

```python
print(bool(0))   # False —— 0 是 falsy
print(bool(1))   # True  —— 1 是 truthy
```

💡 提示：这只是 `auto()` 的默认策略。如果你显式写 `RED = 0`，枚举照样允许，只是要自己留意布尔判断的坑；也可以重写 `_generate_next_value_` 改成从 0 或其他值开始。

2. **如果不用 `@unique`，两个成员值相同会发生什么？** 后定义的成员会成为前者的别名还是独立成员？写代码验证。

**参考答案**

会成为**别名（alias）**，而不是独立成员。值相同时，第一个定义的名字是「规范成员」，后面的名字都指向同一个对象。

```python
from enum import Enum

class Color(Enum):
    RED = 1
    CRIMSON = 1   # 值与 RED 相同
    GREEN = 2

print(Color.CRIMSON is Color.RED)      # True：CRIMSON 是 RED 的别名
print(Color(1))                        # Color.RED：按值查找返回首个定义
print(list(Color))                     # 迭代只含规范成员，不含别名
print(list(Color.__members__))         # __members__ 含别名
```

预期输出：

```
True
Color.RED
[<Color.RED: 1>, <Color.GREEN: 2>]
['RED', 'CRIMSON', 'GREEN']
```

可以看到：`CRIMSON is RED` 为 True（同一对象）；按值 `Color(1)` 返回 RED；直接迭代 `list(Color)` 只有 RED、GREEN 两个规范成员，别名 CRIMSON 被跳过；但 `__members__` 里仍保留 CRIMSON 这个名字。若加上 `@unique`，定义时就会直接抛 `ValueError`，把值冲突挡在早期。

3. **为什么推荐用 `is` 而不是 `==` 比较枚举成员？** 在什么极端情况下 `==` 会返回意想不到的结果？

**参考答案**

因为枚举成员是**单例**——每个成员全局只有一个实例。`is` 比较的是「是不是同一个对象」（身份），对单例来说既快又绝对准确；而 `==` 比较的是「值相等」，可能被自定义的 `__eq__` 或混入类型干扰。

`==` 出意外的典型情况是 **`IntEnum` / `StrEnum`**：它们同时是 int/str 的子类，会和裸整数/字符串判为相等：

```python
from enum import Enum, IntEnum

class Color(Enum):
    RED = 1

class Code(IntEnum):
    OK = 200

print(Color.RED == 1)     # False：普通 Enum 不等于裸整数
print(Code.OK == 200)     # True：IntEnum 会和整数相等，可能掩盖类型错误
```

预期输出：

```
False
True
```

`Code.OK == 200` 为 True，意味着你无法靠 `==` 区分「枚举成员」和「一个普通整数」，传入错误的裸值也可能悄悄通过。而 `is` 只认那个唯一的枚举对象，`Code.OK is Code.OK` 恒为 True，拿一个整数来比绝不会误判。此外，若有人给枚举写了自定义 `__eq__`，`==` 的行为更不可控，`is` 则始终稳定。

💡 提示：`is` 用于「判断是不是某个已知成员」；若你确实想按值匹配（如从外部数据还原），用 `Code(200)` 做查找更合适。另外不要写 `x is 200` 这种「is 配字面量」，解释器会告警。

4. **设计题**：一个交通灯状态机——从绿灯到黄灯到红灯再回到绿灯。如果在红灯时强行变绿灯，应该报错。用枚举实现这个状态机。

**参考答案**

思路：用枚举表示三个状态，再用一张「转移表」规定每个状态**只能**转到哪个下一状态；任何不在表里的转换都抛异常。这样就把「合法流转」集中管理，新增/修改规则只改表即可。

```python
from enum import Enum, auto

class Light(Enum):
    GREEN = auto()
    YELLOW = auto()
    RED = auto()

# 转移表：每个状态只能转到指定的下一个状态
NEXT = {
    Light.GREEN: Light.YELLOW,
    Light.YELLOW: Light.RED,
    Light.RED: Light.GREEN,
}

class TrafficLight:
    def __init__(self):
        self.state = Light.GREEN

    def change_to(self, target: Light):
        if NEXT[self.state] is not target:      # 只允许按顺序流转
            raise ValueError(f"非法转换: {self.state.name} → {target.name}")
        self.state = target

    def next(self):
        self.change_to(NEXT[self.state])

light = TrafficLight()
print(light.state.name)                 # GREEN
light.next(); print(light.state.name)   # YELLOW
light.next(); print(light.state.name)   # RED
light.next(); print(light.state.name)   # GREEN（完成一轮）

# 非法跳步：绿灯直接变红灯 → 报错
try:
    light.change_to(Light.RED)
except ValueError as e:
    print("捕获错误:", e)
```

预期输出：

```
GREEN
YELLOW
RED
GREEN
捕获错误: 非法转换: GREEN → RED
```

`next()` 按 绿→黄→红→绿 正常循环；一旦想跳步（绿直接到红），`change_to` 就抛 `ValueError`。

💡 提示：题面「红灯强行变绿要报错」与「红→绿是正常循环」略有出入。本实现把规则定义为「只能按固定顺序流转、任何跳步都报错」。如果你的规则确实是「红灯禁止直接变绿」，只需把转移表里 `Light.RED` 的目标去掉（让红灯成为终态，或另设一个 `reset()` 方法经黄灯回到绿灯），其余代码不变——这正是转移表的好处。

5. **思考题**：枚举的 `__members__` 属性是什么？它和直接迭代枚举类有什么区别？试着自己输出看看。

**参考答案**

`__members__` 是一个**「名字 → 成员」的有序映射**（类似字典），它收录了定义时写下的**所有名字，包括别名**。而直接迭代枚举类（`for x in Color` / `list(Color)`）只产出**规范成员**，会跳过别名。这就是两者最关键的区别。

```python
from enum import Enum

class Status(Enum):
    OK = 200
    SUCCESS = 200      # OK 的别名
    NOT_FOUND = 404

print(list(Status))                 # 迭代：只有规范成员
print(list(Status.__members__))     # __members__：包含别名
print(Status.__members__["SUCCESS"])  # 可按别名取到成员
print(Status.__members__["SUCCESS"] is Status.OK)  # True
```

预期输出：

```
[<Status.OK: 200>, <Status.NOT_FOUND: 404>]
['OK', 'SUCCESS', 'NOT_FOUND']
Status.OK
True
```

可以看到：迭代结果只有 OK、NOT_FOUND 两项（别名 SUCCESS 被略去）；`__members__` 的键却有 OK、SUCCESS、NOT_FOUND 三个，且 `__members__["SUCCESS"]` 取到的就是 OK 本身。

用途上：想「列出所有不重复的有效值」用迭代；想「按任意名字（含别名）查成员」或「保留定义时的全部命名」用 `__members__`。

⚠️ 注意：`__members__` 是只读映射，不要试图往里增删；它包含别名，所以 `len(Status.__members__)` 可能大于 `len(list(Status))`。

---

## 参考资料

- [PEP 435 — Adding an Enum type to the Python standard library](https://peps.python.org/pep-0435/)
- [Python enum 官方文档](https://docs.python.org/3/library/enum.html)
- [Python 3.11 StrEnum 文档](https://docs.python.org/3/library/enum.html#strenum)
