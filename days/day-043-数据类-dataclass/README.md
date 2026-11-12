# Day 043 — 数据类（dataclass）

> 数据类是 Python 3.7（PEP 557）引入的一种"语法糖"，让你用最少的代码定义数据容器类。它自动生成 `__init__`、`__repr__`、`__eq__` 等特殊方法，是日常开发中**最常用的 OOP 工具之一**。

---

## 概述

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: float
    y: float
```

**这一行装饰器做了什么？**  
它自动为 `Point` 类生成了以下方法：
- `__init__(self, x: float, y: float)` — 不用写构造函数了
- `__repr__(self)` — 返回 `Point(x=1.0, y=2.0)` 这样的可读字符串
- `__eq__(self, other)` — 两个实例如果属性相同就相等
- `__hash__` — 可选，默认是 `None`（不可哈希）

对比普通类，省掉了大约 **15 行**模板代码。

---

## 1. `@dataclass` 装饰器原理

### 1.1 它到底做了什么？

`@dataclass` 本质上是一个**类装饰器**，它在类定义完成后遍历所有带有类型注解的类变量（字段），然后动态生成特殊方法：

```python
# 你写的代码：
@dataclass
class Person:
    name: str
    age: int

# Python 实际生成的 __init__（简化版）：
class Person:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"Person(name={self.name!r}, age={self.age!r})"

    def __eq__(self, other):
        if not isinstance(other, Person):
            return NotImplemented
        return (self.name, self.age) == (other.name, other.age)
```

> **重要理解**：`@dataclass` 不是运行时类型检查工具！它不校验类型，即使传了 `age="hello"` 也能运行。

### 1.2 装饰器参数

```python
@dataclass(init=True, repr=True, eq=True, order=False, frozen=False, slots=False)
```

| 参数 | 默认值 | 作用 |
|------|--------|------|
| `init` | `True` | 是否生成 `__init__` |
| `repr` | `True` | 是否生成 `__repr__` |
| `eq` | `True` | 是否生成 `__eq__` |
| `order` | `False` | 是否生成比较方法（`__lt__`/`__le__`/`__gt__`/`__ge__`） |
| `frozen` | `False` | 是否不可变（类似 namedtuple） |
| `slots` | `False` | 是否使用 `__slots__`（Python 3.10+） |

```python
@dataclass(order=True, frozen=True)
class Version:
    major: int
    minor: int
    patch: int

v1 = Version(1, 0, 0)
v2 = Version(2, 0, 0)
print(v1 < v2)  # True — order=True 生成比较方法
# v1.major = 2  # ❌ FrozenInstanceError — frozen=True 禁止修改
```

---

## 2. `field()` 函数与高级配置

### 2.1 field() 能做什么？

`field()` 让你对**单个字段**进行精细化配置：

```python
from dataclasses import field

@dataclass
class Config:
    name: str
    port: int = field(default=8080, metadata={"unit": "端口号"})
    hosts: list[str] = field(default_factory=list)
    debug: bool = field(default=False, repr=False)    # repr 不显示
    _secret: str = field(default="", repr=False)      # 隐藏敏感字段
```

### 2.2 核心参数速查

| 参数 | 作用 | 经典场景 |
|------|------|----------|
| `default` | 字段默认值 | 简单类型默认值 |
| `default_factory` | 返回默认值的工厂函数 | 可变类型默认值（list, dict, set） |
| `init` | 该字段是否出现在 `__init__` 中 | 计算字段 |
| `repr` | 该字段是否出现在 `__repr__` 中 | 隐藏敏感数据 |
| `compare` | 该字段是否参与 `__eq__`/比较方法 | 排除无意义的比较字段 |
| `hash` | 该字段是否参与 `__hash__` | 精细控制哈希行为 |
| `metadata` | 用户自定义元数据 | 验证规则、序列化配置 |

### 2.3 ⚠️ 可变默认值的陷阱

这是新手最常踩的坑：

```python
# ❌ 错误！所有实例共享同一个列表
@dataclass
class Bad:
    items: list = []  # 这会报错：ValueError: mutable default <class 'list'> for field items is not allowed

# ✅ 正确：使用 default_factory
@dataclass
class Good:
    items: list = field(default_factory=list)
```

**原因**：Python 的默认参数在**定义时求值**一次。如果直接用 `[]`，所有实例共享同一个列表对象，修改一个会影响全部。`default_factory` 在每个实例创建时调用一次工厂函数，保证独立副本。

### 2.4 `__post_init__` 钩子方法

你可以定义 `__post_init__` 方法来执行初始化后的额外逻辑（验证、转换、计算）：

```python
@dataclass
class Person:
    name: str
    age: int
    adult: bool = field(init=False)  # 不在 __init__ 中

    def __post_init__(self):
        # 验证
        if self.age < 0:
            raise ValueError("年龄不能为负数")
        # 计算字段
        self.adult = self.age >= 18

p = Person("Alice", 25)
print(p.adult)  # True
```

---

## 3. 与 namedtuple / 普通类的对比

### 3.1 对比总览

| 特性 | 普通类 | namedtuple | 数据类 (dataclass) |
|------|--------|------------|-------------------|
| 代码量 | 多（需要手写模板方法） | 极少（一行） | 少（几行注解） |
| 可变性 | 可变 | **不可变** | 可变（可设置 frozen=True） |
| 类型注解 | 手动 | 无（字段是字符串） | 完整的类型注解支持 |
| 默认值 | 手动 | 通过 `defaults` 参数 | 通过 `field()` 或直接赋值 |
| 继承 | 完整支持 | 有限 | 完整支持 |
| 方法定义 | 任意方法 | 有限（可以添加方法但麻烦） | 任意方法 |
| 可读性 | 好（构造函数明确） | 差（位置参数） | 极好 |
| 性能 | 一般 | **最快**（底层 C 实现） | 稍慢于 namedtuple |
| 序列化 | 手动 | 支持 _asdict() | 原生支持（dataclasses.asdict） |

### 3.2 何时用哪个？

```
普通类（class）
├── 需要复杂业务逻辑、方法封装
├── 需要多重继承
└── 需要细致的访问控制（property、描述符）

namedtuple（推荐用 typing.NamedTuple）
├── 简单的不可变数据结构
├── 性能敏感的场合（大量创建 10 万+ 对象）
├── 需要元组拆包兼容性
└── 作为字典键（必须可哈希）

数据类（dataclass）⭐⭐ 日常首选
├── 大多数"数据携带"场景
├── 需要类型注解提高可读性
├── 需要可变对象
├── 需要继承和自定义方法
├── 需要默认值/验证/后处理
└── 需要序列化支持
```

---

## 4. 实战：配置管理系统

Day 43 的实战是一个完整的配置管理系统，支持：
- 多种配置来源（默认值、环境变量、JSON 文件、命令行参数）
- 配置验证和类型转换
- 配置只读保护
- 配置序列化与合并

详见 `code/04-config-manager.py`。

---

## 5. 高级话题

### 5.1 继承中的字段顺序

```python
@dataclass
class Base:
    x: int = 0

@dataclass
class Derived(Base):
    y: int

# ⚠️ 这会导致 TypeError: non-default argument 'y' follows default argument
# 因为字段顺序是 [x, y]，而 x 有默认值、y 没有
```

**规则**：所有没有默认值的字段必须在有默认值的字段之前声明。dataclass 的字段顺序是父类字段在前，子类字段在后。

### 5.2 与类型检查工具配合

```python
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

# mypy 会发现类型错误
u = User("Alice", "25")  # ❌ mypy: Argument 2 to "User" has incompatible type "str"; expected "int"
```

### 5.3 dataclass 的哈希行为

默认情况下：
- `frozen=True` → 自动生成 `__hash__`，实例可哈希
- `frozen=False` + `eq=True` → `__hash__` 设为 `None`，实例不可哈希
- 手动设置 `unsafe_hash=True` → 强制生成 `__hash__`（即使可变，不推荐）

---

## 6. 思考题

1. **`@dataclass` 到底做了什么**：给 `Point` 加上 `@dataclass` 后，省掉了哪些手写代码？`Point(1, "2")` 会报错吗？为什么默认的可变 dataclass 实例不能当字典键？

**参考答案**

装饰器会扫描所有带类型注解的类变量（字段），自动生成 `__init__`（按字段顺序接收参数并赋值）、`__repr__`（`Point(x=1, y=2)` 这种可读形式）、`__eq__`（逐字段比较，值相同就相等）。再按需生成比较方法（`order=True`）、不可变保护（`frozen=True`）、`__slots__`（`slots=True`，3.10+）。

**不会报错**。类型注解只是「声明」，`@dataclass` 不做运行时类型检查，`Point(1, "2")` 照样创建成功，`y` 就是字符串 `"2"`。想要校验得自己在 `__post_init__` 里判断，或者交给 mypy 这类静态检查工具在运行前发现问题。

默认不能当字典键，是因为 `eq=True` + `frozen=False` 时 dataclass 把 `__hash__` 设成了 `None`。道理和「列表不能当字典键」一样：对象可变，放进字典后再改字段，哈希值就变了，原来的条目再也找不回来。设 `frozen=True` 后实例不可变，dataclass 才会自动生成 `__hash__`。

💡 提示：需要「按值相等」的数据容器选 dataclass；需要当键或集合元素，就用 `frozen=True`（或 `NamedTuple`）。

2. **可变默认值与初始化后处理（代码）**：为什么 `items: list = []` 会直接报错？请用 `field(default_factory=list)`、`__post_init__`、`field(repr=False)` 写一个购物车数据类，并说明 `count` 这类计算字段有什么局限。

**参考答案**

```python
from dataclasses import dataclass, field, asdict

# ❌ 可变默认值：定义类的时候就会报错
try:
    @dataclass
    class Bad:
        items: list = []
except ValueError as e:
    print("报错:", e)

# ✅ 正确写法：default_factory + __post_init__ + field 精细控制
@dataclass
class Cart:
    owner: str
    items: list = field(default_factory=list)    # 每个实例独立一份列表
    coupon: str = field(default="", repr=False)  # 敏感字段不出现在 repr
    count: int = field(init=False, default=0)    # 计算字段，不由外部传入

    def __post_init__(self):
        if not self.owner:                       # 校验要自己做
            raise ValueError("owner 不能为空")
        self.count = len(self.items)             # 初始化后计算一次

a = Cart("Alice", ["apple"])
b = Cart("Bob")
a.items.append("banana")           # 只影响 a，不会串到 b
print(a.items, b.items)            # ['apple', 'banana'] []
print(a)                           # coupon 被隐藏；count 仍是创建时的 1
print(asdict(a))                   # 转普通字典，方便 json.dumps
```

预期输出：

```
报错: mutable default <class 'list'> for field items is not allowed: use default_factory
['apple', 'banana'] []
Cart(owner='Alice', items=['apple', 'banana'], count=1)
{'owner': 'Alice', 'items': ['apple', 'banana'], 'coupon': '', 'count': 1}
```

`[]` 这种默认值在**类定义时只求值一次**，若允许写下去，所有实例会共享同一个列表，改一个等于改全部。dataclass 干脆在装饰阶段就抛 `ValueError` 提醒你。`default_factory=list` 则是「每次创建实例时调用一次 `list()`」，各实例拿到独立副本。

`__post_init__` 是自动生成的 `__init__` 末尾调用的钩子，适合做校验（年龄为负就抛错）、类型转换和派生字段计算；配合 `field(init=False)` 可以让计算字段不出现在构造参数里。`field(repr=False)` 把敏感或无关字段从打印结果中隐藏（但 `asdict()` 仍会包含它，真要脱敏得自己处理）。

⚠️ 注意：`count` 停在 1，因为 `__post_init__` **只在创建时执行一次**，之后 `append` 不会重算。想要「随时正确」的派生值，应该用 `@property` 定义只读属性，而不是把它存成字段。

3. **继承字段顺序与不可变版本（代码）**：父类 `Base` 的 `x` 有默认值，子类新增无默认值的 `y`，为什么会报错、怎么修？`order=True` 和 `frozen=True` 分别带来什么能力？

**参考答案**

```python
from dataclasses import dataclass

@dataclass
class Base:
    x: int = 0

# ❌ 字段顺序是「父类在前」：x 有默认值、y 没有 → 报错
try:
    @dataclass
    class Derived(Base):
        y: int
except TypeError as e:
    print("报错:", e)

# ✅ 给 y 也补上默认值（或把父类字段改成无默认值）
@dataclass
class Derived(Base):
    y: int = 0

print(Derived(1, 2))               # Derived(x=1, y=2)

# order=True 生成比较方法，可以直接排序
@dataclass(order=True)
class Version:
    major: int
    minor: int

vs = [Version(1, 9), Version(1, 2), Version(2, 0)]
print(sorted(vs))                  # 按字段声明顺序逐个比较

# frozen=True：不可变 + 自动可哈希，能当字典键
@dataclass(frozen=True)
class Point:
    x: int
    y: int

p = Point(1, 2)
print({p: "起点"})
try:
    p.x = 9                        # 禁止修改
except Exception as e:
    print(type(e).__name__)        # FrozenInstanceError

# 默认（可变 + eq=True）的 dataclass 不可哈希
try:
    hash(Derived(1, 2))
except TypeError as e:
    print("报错:", e)
```

预期输出：

```
报错: non-default argument 'y' follows default argument
Derived(x=1, y=2)
[Version(major=1, minor=2), Version(major=1, minor=9), Version(major=2, minor=0)]
{Point(x=1, y=2): '起点'}
FrozenInstanceError
报错: unhashable type: 'Derived'
```

dataclass 生成的 `__init__` 参数顺序是**父类字段在前、子类字段在后**，即 `(x=0, y)`。Python 函数不允许「无默认值参数跟在有默认值参数后面」，所以装饰阶段就抛 `TypeError`。修法有三种：给 `y` 也加默认值；把父类 `x` 改成无默认值；或用 `field(kw_only=True)`（3.10+）把字段变成仅关键字参数，绕开位置顺序限制。

`order=True` 额外生成 `__lt__`/`__le__`/`__gt__`/`__ge__`，比较规则是把字段按声明顺序组成元组逐个比，所以 `Version` 能直接 `sorted()`，先比 `major` 再比 `minor`。

`frozen=True` 让实例不可变：赋值抛 `FrozenInstanceError`，同时自动生成 `__hash__`，于是能当字典键、放进集合。这也解释了最后一行——可变的 `Derived` 依然不可哈希。

💡 提示：`frozen=True` 只是「浅冻结」，字段里若装着列表，列表内容仍可修改；需要彻底不可变就把字段也换成元组等不可变类型。

---

## 总结

```
@dataclass  =  "给我一个类，专门装数据"
  ├── 自动生成 __init__ / __repr__ / __eq__
  ├── field() 提供精细的字段控制
  ├── __post_init__ 做初始化后处理
  ├── frozen=True 做不可变版本
  └── 完整支持继承和类型注解
```

> **一句话记住**：需要装数据的类，默认选 `@dataclass`。需要装数据的元组，选 `NamedTuple`。需要复杂行为的类，用手写 class。

---

## 参考资料

- [PEP 557 – Data Classes](https://peps.python.org/pep-0557/)
- [Python dataclasses 官方文档](https://docs.python.org/3/library/dataclasses.html)
- [Raymond Hettinger 的 dataclass 演讲](https://www.youtube.com/watch?v=T-TwcmT6Rcw)
