# Day 035 — 特殊方法（Magic Methods）

> 掌握 Python 的魔术方法协议，实现自定义类型与内置类型无缝协作

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| `__str__` / `__repr__` | ⭐⭐ | 字符串表示、调试 vs 展示 |
| `__len__` / `__getitem__` | ⭐⭐⭐ | 容器协议、索引与切片 |
| 运算符重载 | ⭐⭐⭐ | `__add__`、`__eq__` 等算术/比较运算符 |
| `__call__` 与可调用对象 | ⭐⭐ | 使实例像函数一样调用 |
| 实战：自定义向量类 | ⭐⭐⭐⭐ | 完整的多维向量实现 |

---

## 一、字符串表示：`__str__` 与 `__repr__`

### 1.1 两者的区别

| 方法 | 目标用户 | 何时调用 | 目的 |
|------|---------|---------|------|
| `__repr__` | 开发者 | `repr(obj)`、交互式解释器 | 无歧义的调试信息 |
| `__str__` | 最终用户 | `str(obj)`、`print(obj)` | 友好的可读输出 |

```
           ┌─────────────────────────────────┐
           │           datetime(2026,6,22)    │
           └────────────────┬────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
    ┌──────────────────┐      ┌──────────────────────┐
    │  __repr__()      │      │   __str__()           │
    │  repr(dt)        │      │   str(dt)             │
    │  → "datetime.    │      │   → "2026-06-22       │
    │    datetime(2026,│      │     09:03:00"         │
    │    6,22,9,3)"    │      │                       │
    └──────────────────┘      └──────────────────────┘
    开发者调试                    最终用户展示
```

### 1.2 实现规范

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        # 返回可重建对象的信息
        return f"Point({self.x}, {self.y})"

    def __str__(self):
        # 返回用户友好的信息
        return f"({self.x}, {self.y})"


p = Point(3, 4)
print(str(p))    # (3, 4)      ← 用户友好
print(repr(p))   # Point(3, 4) ← 开发者友好
```

**黄金法则：** `__repr__` 应该返回足以重建对象的信息，`__str__` 返回美观的展示。

### 1.3 `__repr__` 的 `eval()` 约定

理想情况下，`repr(obj)` 返回的字符串可以直接传给 `eval()` 重建对象：

```python
p = Point(3, 4)
r = repr(p)               # "Point(3, 4)"
p2 = eval(r)              # Point(3, 4) ← 重建
print(p2 == p)            # 需要实现 __eq__
```

---

## 二、容器协议：`__len__` 与 `__getitem__`

### 2.1 `__len__` —— 长度协议

```python
class Playlist:
    def __init__(self):
        self._songs = []

    def add(self, song):
        self._songs.append(song)

    def __len__(self):
        """使对象支持 len() 函数"""
        return len(self._songs)

    def __bool__(self):
        """使对象支持 bool() 判断"""
        return len(self._songs) > 0


playlist = Playlist()
print(len(playlist))    # 0
print(bool(playlist))   # False

playlist.add("Bohemian Rhapsody")
print(len(playlist))    # 1
print(bool(playlist))   # True
```

### 2.2 `__getitem__` —— 索引协议

```python
class Playlist:
    def __init__(self):
        self._songs = []

    def add(self, song):
        self._songs.append(song)

    def __getitem__(self, index):
        """使对象支持索引和切片"""
        if isinstance(index, slice):
            # 处理切片
            return [self._songs[i] for i in range(*index.indices(len(self)))]
        return self._songs[index]

    def __len__(self):
        return len(self._songs)


playlist = Playlist()
playlist.add("Song A")
playlist.add("Song B")
playlist.add("Song C")

print(playlist[1])       # Song B           ← 索引
print(playlist[1:])      # ['Song B', 'Song C']  ← 切片
print(playlist[::-1])    # ['Song C', 'Song B', 'Song A']
```

### 2.3 完整的序列协议

| 方法 | 用途 | 自动获得的行为 |
|------|------|--------------|
| `__getitem__` | 索引访问 `obj[i]` | 迭代、`in` 运算符（如果会引发 `IndexError`） |
| `__setitem__` | 索引赋值 `obj[i] = v` | 可变序列支持 |
| `__delitem__` | 索引删除 `del obj[i]` | — |
| `__len__` | 长度 `len(obj)` | — |
| `__contains__` | 成员检查 `x in obj` | 如果没有实现，会退化为 `__getitem__` 迭代 |

---

## 三、运算符重载

### 3.1 算术运算符

| 运算符 | 方法 | 示例 |
|--------|------|------|
| `+` | `__add__` | `a + b` |
| `-` | `__sub__` | `a - b` |
| `*` | `__mul__` | `a * b` |
| `/` | `__truediv__` | `a / b` |
| `//` | `__floordiv__` | `a // b` |
| `%` | `__mod__` | `a % b` |
| `**` | `__pow__` | `a ** b` |
| `@` | `__matmul__` | `a @ b` (矩阵乘法) |

**原地运算符**（`+=`, `-=` 等）：

| 运算符 | 方法 |
|--------|------|
| `+=` | `__iadd__` |
| `-=` | `__isub__` |
| `*=` | `__imul__` |

### 3.2 比较运算符

| 运算符 | 方法 |
|--------|------|
| `==` | `__eq__` |
| `!=` | `__ne__` |
| `<` | `__lt__` |
| `<=` | `__le__` |
| `>` | `__gt__` |
| `>=` | `__ge__` |

> **注意：** Python 3 中实现 `__eq__` 后，`!=` 会自动取反（除非显式实现 `__ne__`）。

### 3.3 实现示例

```python
class Vector2D:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    # ── 字符串表示 ──
    def __repr__(self):
        return f"Vector2D({self.x}, {self.y})"

    # ── 算术运算 ──
    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        """标量乘法"""
        if isinstance(scalar, (int, float)):
            return Vector2D(self.x * scalar, self.y * scalar)
        return NotImplemented

    # 反向运算（scalar * vector）
    def __rmul__(self, scalar):
        return self.__mul__(scalar)

    def __neg__(self):
        """一元负号"""
        return Vector2D(-self.x, -self.y)

    # ── 比较运算 ──
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __abs__(self):
        """模长"""
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __bool__(self):
        return self.x != 0 or self.y != 0


v1 = Vector2D(3, 4)
v2 = Vector2D(1, 2)

print(v1 + v2)        # Vector2D(4, 6)
print(v1 * 2)         # Vector2D(6, 8)
print(2 * v1)         # Vector2D(6, 8)  ← 反向运算
print(-v1)            # Vector2D(-3, -4)
print(abs(v1))        # 5.0
print(v1 == Vector2D(3, 4))  # True
print(bool(Vector2D(0, 0)))  # False
```

---

## 四、`__call__` 与可调用对象

### 4.1 基本原理

任何对象，如果定义了 `__call__` 方法，就可以像函数一样被调用：

```python
class Greeter:
    def __init__(self, greeting="Hello"):
        self.greeting = greeting

    def __call__(self, name):
        return f"{self.greeting}, {name}!"


hello = Greeter("Hello")
hi = Greeter("Hi")

print(hello("Alice"))   # Hello, Alice!  ← 像函数一样调用
print(hi("Bob"))        # Hi, Bob!
```

### 4.2 `__call__` 的应用场景

```
可调用对象 vs 普通函数 + 闭包

普通函数 + 闭包:                可调用对象:
┌─────────────────┐           ┌─────────────────────┐
│ def make_counter(): │       │ class Counter:       │
│     count = 0     │       │     def __init__(self):│
│     def counter():│       │         self.count = 0│
│         nonlocal   │       │     def __call__(self):│
│           count   │       │         self.count += 1│
│         count += 1│       │         return count  │
│         return    │       │                      │
│           count   │       │ c = Counter()        │
│     return counter│       │ c()  ← 有状态的函数   │
│                   │       │ c.count  ← 可访问状态  │
│ c = make_counter()│       └─────────────────────┘
│ c()               │
│ # 状态不可访问     │
└─────────────────┘
```

### 4.3 常见应用：装饰器、策略、回调

```python
from typing import Callable
import time


class Timer:
    """计时器装饰器（作为可调用对象）"""

    def __init__(self, func: Callable):
        self.func = func
        self.total_time = 0.0
        self.calls = 0

    def __call__(self, *args, **kwargs):
        start = time.perf_counter()
        result = self.func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        self.total_time += elapsed
        self.calls += 1
        print(f"{self.func.__name__} 调用 #{self.calls}: {elapsed:.4f}s")
        return result


@Timer
def slow_function(n):
    return sum(range(n))


slow_function(100000)   # 调用 #1: 0.0023s
slow_function(1000000)  # 调用 #2: 0.0150s
```

---

## 五、更多特殊方法

### 5.1 类型转换

| 方法 | 用途 |
|------|------|
| `__int__` | `int(obj)` |
| `__float__` | `float(obj)` |
| `__bool__` | `bool(obj)` |
| `__complex__` | `complex(obj)` |
| `__index__` | 用于 `bin()`, `hex()`, 切片索引 |

### 5.2 属性访问

| 方法 | 用途 |
|------|------|
| `__getattr__` | 属性不存在时调用 |
| `__setattr__` | 属性赋值时调用 |
| `__delattr__` | 删除属性时调用 |
| `__getattribute__` | 所有属性访问调用（慎用） |

### 5.3 上下文管理

| 方法 | 用途 |
|------|------|
| `__enter__` | `with` 语句进入 |
| `__exit__` | `with` 语句退出 |

### 5.4 迭代器

| 方法 | 用途 |
|------|------|
| `__iter__` | 返回迭代器对象 |
| `__next__` | 返回下一个元素 |
| `__reversed__` | 反向迭代（`reversed(obj)`）|

---

## 六、实战：自定义向量类

```python
import math
from typing import Union, List, Tuple

Number = Union[int, float]


class Vector:
    """多维向量 —— 展示完整的魔术方法实现"""

    def __init__(self, *components: Number):
        self._data = list(components)

    # ── 属性 ──

    @property
    def dim(self) -> int:
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        self._data[index] = value

    # ── 字符串 ──

    def __repr__(self):
        return f"Vector({', '.join(f'{c:.2f}' for c in self._data)})"

    def __str__(self):
        parts = ', '.join(f'{c:.2f}' for c in self._data)
        return f"[{parts}]"

    # ── 长度与布尔 ──

    def __len__(self):
        return self.dim

    def __bool__(self):
        return any(c != 0 for c in self._data)

    # ── 比较 ──

    def __eq__(self, other):
        if not isinstance(other, Vector):
            return NotImplemented
        if self.dim != other.dim:
            return False
        return all(a == b for a, b in zip(self._data, other._data))

    def __lt__(self, other):
        """按模长比较"""
        return abs(self) < abs(other)

    # ── 算术 ──

    def __add__(self, other):
        if isinstance(other, Vector):
            if self.dim != other.dim:
                raise ValueError(f"维度不匹配: {self.dim} vs {other.dim}")
            return Vector(*[a + b for a, b in zip(self._data, other._data)])
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Vector):
            if self.dim != other.dim:
                raise ValueError(f"维度不匹配: {self.dim} vs {other.dim}")
            return Vector(*[a - b for a, b in zip(self._data, other._data)])
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Vector(*[c * other for c in self._data])
        if isinstance(other, Vector):
            # 点积
            if self.dim != other.dim:
                raise ValueError(f"维度不匹配: {self.dim} vs {other.dim}")
            return sum(a * b for a, b in zip(self._data, other._data))
        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __neg__(self):
        return Vector(*[-c for c in self._data])

    def __pos__(self):
        return Vector(*self._data)

    def __abs__(self):
        return math.sqrt(sum(c ** 2 for c in self._data))

    # ── 可调用 ──

    def __call__(self, index: int) -> Number:
        """像函数一样访问分量"""
        return self._data[index]

    # ── 哈希（不可变向量的支持） ──

    def __hash__(self):
        return hash(tuple(self._data))

    # ── 工具方法 ──

    def normalize(self) -> 'Vector':
        """归一化"""
        magnitude = abs(self)
        if magnitude == 0:
            raise ValueError("零向量无法归一化")
        return Vector(*[c / magnitude for c in self._data])

    def dot(self, other: 'Vector') -> float:
        """点积"""
        return self * other

    def cross(self, other: 'Vector') -> 'Vector':
        """叉积（仅 3D）"""
        if self.dim != 3 or other.dim != 3:
            raise ValueError("叉积仅支持 3 维向量")
        x1, y1, z1 = self._data
        x2, y2, z2 = other._data
        return Vector(
            y1 * z2 - z1 * y2,
            z1 * x2 - x1 * z2,
            x1 * y2 - y1 * x2
        )


# 使用示例
v1 = Vector(3, 4)
v2 = Vector(1, 2)

print(f"v1 = {v1}")                    # [3.00, 4.00]
print(f"|v1| = {abs(v1):.2f}")         # 5.00
print(f"v1 + v2 = {v1 + v2}")          # [4.00, 6.00]
print(f"v1 * 2 = {v1 * 2}")            # [6.00, 8.00]
print(f"v1 · v2 = {v1.dot(v2)}")       # 11
print(f"v1.normalize() = {v1.normalize()}")  # [0.60, 0.80]

v3 = Vector(1, 0, 0)
v4 = Vector(0, 1, 0)
print(f"v3 × v4 = {v3.cross(v4)}")     # [0.00, 0.00, 1.00]
```

---

## 七、特殊方法速查表

```
字符串 / 表示
 ┌────────────────────────────────────────────────┐
 │ __str__       str(obj) 或 print(obj)            │
 │ __repr__      repr(obj)，交互式环境              │
 │ __format__    format(obj, spec) 或 f"{obj:spec}"  │
 │ __bytes__     bytes(obj)                         │
 └────────────────────────────────────────────────┘

容器协议
 ┌────────────────────────────────────────────────┐
 │ __len__       len(obj)                          │
 │ __getitem__   obj[key], obj[i:j]                │
 │ __setitem__   obj[key] = value                  │
 │ __delitem__   del obj[key]                      │
 │ __contains__  x in obj                          │
 │ __reversed__  reversed(obj)                     │
 └────────────────────────────────────────────────┘

算术运算
 ┌────────────────────────────────────────────────┐
 │ __add__ / __radd__     +   │ __iadd__   +=     │
 │ __sub__ / __rsub__     -   │ __isub__   -=     │
 │ __mul__ / __rmul__     *   │ __imul__   *=     │
 │ __truediv__ / __rtruediv__ /                     │
 │ __floordiv__ / __rfloordiv__ //                  │
 │ __mod__ / __rmod__     %                        │
 │ __pow__ / __rpow__     **                       │
 └────────────────────────────────────────────────┘

比较运算
 ┌────────────────────────────────────────────────┐
 │ __eq__   ==   │ __ne__   !=   │ __lt__   <    │
 │ __le__   <=   │ __gt__   >   │ __ge__   >=   │
 └────────────────────────────────────────────────┘

类型转换
 ┌────────────────────────────────────────────────┐
 │ __int__       int(obj)     │ __float__ float() │
 │ __bool__      bool(obj)   │ __complex__ complex│
 │ __index__     bin(), hex(), slice              │
 │ __hash__      hash(obj)                        │
 └────────────────────────────────────────────────┘

其他
 ┌────────────────────────────────────────────────┐
 │ __call__      obj(args)    → 可调用对象          │
 │ __iter__      iter(obj)    → 迭代器              │
 │ __next__      next(iter)   → 下一个元素          │
 │ __enter__ / __exit__        → 上下文管理器        │
 │ __new__ / __init__          → 对象创建流程        │
 │ __del__                      → 析构函数 (少用)    │
 │ __slots__                    → 限制属性 + 节省内存 │
 └────────────────────────────────────────────────┘
```

---

## 八、思考题

1. **`__repr__` 与 `__str__`**：如果一个类只实现了 `__repr__` 没实现 `__str__`，`print(obj)` 会调用哪个？为什么？

**参考答案**

会调用 **`__repr__`**。原因是继承链上的回退机制：所有类最终继承自 `object`，而 `object.__str__` 的默认实现就是"调用 `self.__repr__()`"。当你没有覆盖 `__str__` 时，`print(obj)` / `str(obj)` 找到的正是这个默认的 `__str__`，它转而调用你实现的 `__repr__`。

反过来不成立：只实现 `__str__` 而没实现 `__repr__` 时，`repr(obj)` 仍会走 `object.__repr__`（输出 `<__main__.X object at 0x...>` 这种带地址的默认形式），**不会**回退到 `__str__`。所以实践建议：**至少实现 `__repr__`**，这样调试和展示都有合理输出；需要更友好的展示时再额外实现 `__str__`。

```python
# 思考题1：只实现 __repr__ 时 print 走 __repr__
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __repr__(self):
        return f'Point({self.x}, {self.y})'


p = Point(3, 4)
print(p)        # 没有 __str__，回退到 __repr__
print(str(p))   # 同样回退
```

预期输出：

```text
Point(3, 4)
Point(3, 4)
```

💡 提示：回退方向是单向的——`__str__` 缺省时退到 `__repr__`，但 `__repr__` 缺省时不会退到 `__str__`。

2. **运算符重载的返回值**：`__add__` 应该返回新对象还是修改自身？两种方式分别在什么场景下更合适？

**参考答案**

**`__add__`（对应 `a + b`）应当返回新对象，不修改自身**。这符合"值语义"：`+` 是表达式，调用者期望 `a`、`b` 都不被改动，结果是一个新值。数字、字符串、元组都是这样。若 `__add__` 偷偷改了 `self`，会破坏链式表达式、引发隐蔽副作用，也不利于多线程安全。

**原地修改交给 `__iadd__`（对应 `a += b`）**。对**可变容器**（如 `list`），`+=` 就地扩展并返回 `self`，省去创建新对象的开销；对**不可变类型**（如 `int`、`tuple`），没有 `__iadd__`，`a += b` 会退化为 `a = a + b`，即重新绑定到新对象。

**选择标准**：

- 表达"产生一个新值"、对象是不可变值类型 → `__add__` 返回新对象；
- 表达"就地累积/更新"、对象是可变容器且追求性能 → 实现 `__iadd__` 修改并返回 `self`。

```python
# 思考题2：__add__ 返回新对象，__iadd__ 原地修改
class Vec:
    def __init__(self, x):
        self.x = x

    def __add__(self, other):
        return Vec(self.x + other.x)   # 新对象，不改自身

    def __iadd__(self, other):
        self.x += other.x              # 原地修改
        return self

    def __repr__(self):
        return f'Vec({self.x})'


a = Vec(1)
b = a + Vec(2)
print(a, b)        # a 不变
a += Vec(5)
print(a)           # 原地累加
```

预期输出：

```text
Vec(1) Vec(3)
Vec(6)
```

⚠️ 注意：`__iadd__` 必须 `return self`（或某个对象），因为 `a += b` 实际是 `a = a.__iadd__(b)`，忘记返回会让 `a` 变成 `None`。

3. **`NotImplemented` vs `NotImplementedError`**：在 `__add__` 中返回 `NotImplemented` 和在重载方法中 `raise NotImplementedError` 有什么区别？

**参考答案**

两者名字像，但本质完全不同：

- **`NotImplemented` 是一个"哨兵值"（单例对象）**，用于二元特殊方法（`__add__`、`__eq__` 等）**返回**。它告诉解释器："我不支持这个操作数类型，请试试另一方的反向方法。" 于是 `a + b` 中 `a.__add__` 返回 `NotImplemented` 后，Python 会转去调用 `b.__radd__(a)`；若双方都返回 `NotImplemented`，才最终抛出 `TypeError`。它是**协作式回退机制**的一部分。
- **`NotImplementedError` 是一个"异常类"**，用于**抛出**，通常出现在抽象基类/父类里"子类必须覆盖"的方法中。一旦 `raise`，调用立即中断，**不会**触发任何反向运算回退。

一句话：在运算符重载里要表达"我处理不了，交给对方"，必须 **`return NotImplemented`**；写成 `raise NotImplementedError` 会直接报错、丧失回退能力，是常见误用。

```python
# 思考题3：返回 NotImplemented 触发反向运算
class A:
    def __add__(self, other):
        return NotImplemented   # 我不处理，交给对方


class B:
    def __radd__(self, other):
        return 'B 处理了加法'


print(A() + B())   # 解释器转而调用 B.__radd__
```

预期输出：

```text
B 处理了加法
```

⚠️ 注意：`NotImplemented` 只能用于二元运算方法的返回值；在普通方法里 `return NotImplemented` 没有特殊含义，而 `bool(NotImplemented)` 为 `True`，误用还可能触发 `DeprecationWarning`。

4. **哈希与相等性**：如果你实现了 `__eq__`，为什么 Python 通常会将 `__hash__` 设为 `None`？实现 `__hash__` 时需要注意什么？

**参考答案**

哈希有一条**铁律**：**相等的对象必须有相等的哈希值**（`a == b` ⇒ `hash(a) == hash(b)`），否则字典/集合会出错。`object` 默认的 `__hash__` 基于对象的**身份（内存地址）**，而默认的 `__eq__` 也是身份比较，二者本来一致。

一旦你覆盖了 `__eq__` 改成**按值相等**，默认的身份哈希就不再满足铁律了——两个"值相等"的对象会有不同哈希。为避免这种隐患，Python 在你定义 `__eq__` 时**自动把 `__hash__` 置为 `None`**，让实例**不可哈希**（放进 `set`/`dict` 键会 `TypeError`），逼使你显式决定哈希策略。

**实现 `__hash__` 的要点**：

- 哈希必须基于**与 `__eq__` 相同的字段**，保证相等对象哈希相同；
- 这些字段最好是**不可变**的：对象作为字典键/集合元素期间若哈希会变，就再也找不回来了；
- 常用写法 `return hash((self.x, self.y))`，把参与比较的字段打包成元组求哈希；
- 若对象本质可变、不该做键，就保持 `__hash__ = None`。

```python
# 思考题4：__eq__ 与 __hash__ 的一致性
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other):
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)

    def __hash__(self):
        return hash((self.x, self.y))   # 与 __eq__ 用同样的字段


p1, p2 = Point(1, 2), Point(1, 2)
print(p1 == p2)             # True
print(hash(p1) == hash(p2)) # True
print(len({p1, p2}))        # 1，集合去重


class OnlyEq:
    def __eq__(self, other):
        return True


print(OnlyEq.__hash__)      # None：只定义 __eq__ 会变为不可哈希
```

预期输出：

```text
True
True
1
None
```

💡 提示：`dataclass` 默认 `eq=True` 也会把 `__hash__` 设为 `None`；想要可哈希需显式 `@dataclass(frozen=True)`（冻结后自动生成基于字段的 `__hash__`）。

5. **`__call__` 与闭包**：使用 `__call__` 的可调用对象和闭包函数相比，各自有什么优劣？在什么场景下可调用对象更好？

**参考答案**

两者都能实现"带状态、可像函数一样调用"的对象，区别在于状态的可见性与扩展性：

- **闭包函数**：写法简洁、轻量，状态藏在自由变量里（配合 `nonlocal` 修改），天然封装、外部看不到。适合**状态简单、只需一个调用入口**的场景（如简单计数器、装饰器）。缺点是状态不可直接访问/重置，难以附加其它方法，调试和序列化较麻烦。
- **可调用对象（`__call__`）**：状态是**显式的实例属性**，可读、可改、可重置；还能定义多个方法、支持继承、便于 `pickle` 序列化和单元测试。代价是代码量略多。

**可调用对象更好的场景**：状态需要被外部检查或配置（如累计耗时、调用次数）、需要"重置/暂停"等额外操作、需要多个相关方法、需要继承复用或序列化保存状态时。

```python
# 思考题5：可调用对象的状态可访问、可重置
class Counter:
    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1
        return self.count

    def reset(self):
        self.count = 0


c = Counter()
print(c(), c(), c())   # 1 2 3
print(c.count)         # 3，状态可直接访问
c.reset()
print(c())             # 1
```

预期输出：

```text
1 2 3
3
1
```

💡 提示：闭包要达到同样的"查看/重置状态"效果，得额外返回 getter/setter 或把状态挂到函数属性上，反而更别扭；这时可调用对象是更自然的选择。

---

## 📝 本章小结

```
✅ __str__ / __repr__ —— 字符串表示双协议
✅ __len__ / __getitem__ —— 容器协议
✅ 运算符重载 —— 让自定义类型支持运算
✅ 反向运算 —— __radd__、__rmul__ 等
✅ __call__ —— 函数式对象，状态保持
✅ __hash__ + __eq__ —— 可哈希对象的正确实现
✅ 实战：向量类 —— 完整魔术方法集合
```
