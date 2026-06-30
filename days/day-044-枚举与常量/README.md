# Day 44：枚举与常量

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

2. **如果不用 `@unique`，两个成员值相同会发生什么？** 后定义的成员会成为前者的别名还是独立成员？写代码验证。

3. **为什么推荐用 `is` 而不是 `==` 比较枚举成员？** 在什么极端情况下 `==` 会返回意想不到的结果？

4. **设计题**：一个交通灯状态机——从绿灯到黄灯到红灯再回到绿灯。如果在红灯时强行变绿灯，应该报错。用枚举实现这个状态机。

5. **思考题**：枚举的 `__members__` 属性是什么？它和直接迭代枚举类有什么区别？试着自己输出看看。

---

## 参考资料

- [PEP 435 — Adding an Enum type to the Python standard library](https://peps.python.org/pep-0435/)
- [Python enum 官方文档](https://docs.python.org/3/library/enum.html)
- [Python 3.11 StrEnum 文档](https://docs.python.org/3/library/enum.html#strenum)
