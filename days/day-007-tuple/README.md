# Day 007 — 元组（Tuple）

> "不可变"不是限制，是契约：元组的不可变性带来的不仅是安全性，更是性能钥匙

---

## 📋 今日学习目标

- [ ] 理解元组的不可变性原理与内存布局
- [ ] 掌握元组的创建、索引与操作
- [ ] 熟练掌握元组拆包的各种用法
- [ ] 理解 namedtuple 的概念与使用场景
- [ ] 理解列表 vs 元组的性能差异及选择依据
- [ ] 完成实战：坐标系统

---

## 一、元组的不可变性原理

### 1.1 概念解释

**元组（tuple）** 是 Python 中的一种序列类型，和列表非常相似，但有一个根本区别：**元组不可变（immutable）**。

```python
# 创建元组的多种方式
empty = ()                    # 空元组
single = (42,)                # 单元素元组 — 逗号是必须的！
simple = (1, 2, 3)            # 括号包裹
without_parens = 1, 2, 3      # 没有括号也可以——这叫"元组字面量"
nested = (1, (2, 3), 4)       # 嵌套元组
from_list = tuple([1, 2, 3])  # 从列表转换
from_str = tuple("hello")     # 从字符串转换 → ('h','e','l','l','o')
```

**为什么叫"元组"？**

元组（tuple）这个术语来自数学（如 n-tuple，n 元组），表示一组有序的元素序列。Python 用它来指代这种不可变的序列类型。

### 1.2 不可变性的底层原理

#### Python 对象的内存模型

要理解元组的不可变性，必须先理解 Python 对象在内存中的布局。

**列表的内存布局**：
```
列表对象 (list)
┌─────────────────┐
│ ob_refcnt (引用计数)│
│ ob_type (类型指针)  │
│ ob_size (长度)     │ → 3
│ allocated (容量)   │ → 4
│ ob_item ──────────┼──→ [ptr_to_obj1, ptr_to_obj2, ptr_to_obj3, ...]
└─────────────────┘        ↓          ↓          ↓
                          "a"         "b"         "c"
```
列表底层是一个**动态数组**（dynamic array），`ob_item` 指向一个连续的内存块，里面存放的是**指向 Python 对象的指针**。当 append 或 insert 时，这个内存块可能被 realloc 扩大或缩小。

**元组的内存布局**：
```
元组对象 (tuple)
┌─────────────────┐
│ ob_refcnt        │
│ ob_type          │
│ ob_size          │ → 3
│ ob_item[0]       │ → ptr_to_obj1
│ ob_item[1]       │ → ptr_to_obj2
│ ob_item[2]       │ → ptr_to_obj3
└─────────────────┘
```
元组的指针数组是**直接嵌入在对象结构体内部**的（通过变长结构体实现），而不是通过独立分配的指针数组。这意味：

1. **元组对象在创建时就确定了大小** — 指针数组紧随对象头，在堆上一次性分配
2. **不能增删元素** — 因为结构体大小固定，没有额外空间
3. **不能替换元素引用的对象** — 内存布局不允许写操作

> ⚠️ **重要澄清**：元组的"不可变"是指**元组对象本身的结构**（指针数组）不可变。但元组包含的**可变对象**（如列表）内部状态仍然可以改变。

```python
t = ([1, 2], 3)
t[0].append(3)   # ✅ 可以！元组的第一个元素（列表）没有被替换，列表内部变了
print(t)         # ([1, 2, 3], 3)
# t[0] = [4, 5]  # ❌ TypeError: 'tuple' object does not support item assignment
```

### 1.3 元组的基本操作

```python
t = (10, 20, 30, 40, 50)

# 索引访问（和列表一样）
print(t[0])      # 10
print(t[-1])     # 50
print(t[1:3])    # (20, 30) — 切片返回新元组

# 拼接与重复
print(t + (60, 70))     # (10, 20, 30, 40, 50, 60, 70)
print(t * 2)            # (10, 20, 30, 40, 50, 10, 20, 30, 40, 50)

# 成员检查
print(20 in t)          # True
print(99 not in t)      # True

# 长度与计数
print(len(t))           # 5
print(t.count(10))      # 1
print(t.index(30))      # 2  — 返回第一个匹配的索引

# 遍历
for value in t:
    print(value)
```

---

## 二、元组拆包与多返回值

### 2.1 概念解释

**元组拆包（tuple unpacking）** 是将元组（或任何可迭代对象）的元素直接赋值给多个变量的操作。这是 Python 中非常优雅、Pythonic 的特性。

### 2.2 基础拆包

```python
# 最基础的拆包
point = (3, 7)
x, y = point
print(x, y)  # 3 7

# 交换变量（经典应用）
a, b = 1, 2
a, b = b, a
print(a, b)  # 2 1
# 这行代码等价于：(a, b) = (b, a)，右边的 (b, a) 会先构造一个临时元组 (2, 1)
```

### 2.3 高级拆包技巧

```python
# 星号拆包（Python 3 引入的 * 操作符）
first, *middle, last = (1, 2, 3, 4, 5)
print(first)    # 1
print(middle)   # [2, 3, 4] — 注意：中间部分变成列表！
print(last)     # 5

# 只取前 N 个，忽略剩余
a, b, *_ = (10, 20, 30, 40, 50)
print(a, b)     # 10 20

# 嵌套拆包
data = ("Alice", (1990, 5, 15))
name, (year, month, day) = data
print(f"{name} born on {year}-{month:02d}-{day:02d}")

# 列表也可以拆包（任何可迭代对象都行）
head, *tail = [1, 2, 3, 4]
print(head)  # 1
print(tail)  # [2, 3, 4]
```

### 2.4 函数多返回值的本质

Python 函数所谓的"返回多个值"，本质就是**返回一个元组**：

```python
def divide_and_remainder(a, b):
    """返回 (商, 余数)"""
    quotient = a // b
    remainder = a % b
    return quotient, remainder  # 实际返回的是元组 (quotient, remainder)

q, r = divide_and_remainder(17, 5)
print(f"17 ÷ 5 = {q} 余 {r}")  # 17 ÷ 5 = 3 余 2

# 也可以先接收整个元组
result = divide_and_remainder(17, 5)
print(type(result))   # <class 'tuple'>
print(result)         # (3, 2)
```

**为什么 Python 用元组实现多返回值？**

- **不可变性**：函数返回后，返回值不可被意外修改，保证数据安全
- **轻量高效**：元组的创建开销比列表小（后面会详解）
- **拆包语法天然配合**：`a, b = func()` 优雅且直观

### 2.5 实际应用场景

```python
# 场景 1：遍历字典的 items()
scores = {"Alice": 95, "Bob": 87, "Charlie": 92}
for name, score in scores.items():
    print(f"{name}: {score}")

# 场景 2：enumerate() 返回 (索引, 值) 元组
for idx, val in enumerate(["a", "b", "c"]):
    print(f"索引 {idx} → {val}")

# 场景 3：zip() 打包多个可迭代对象
names = ["Alice", "Bob", "Charlie"]
ages = [25, 30, 35]
for name, age in zip(names, ages):
    print(f"{name} is {age} years old")

# 场景 4：函数同时返回结果和状态
def get_user(user_id):
    """返回 (用户数据, 是否成功)"""
    if user_id <= 0:
        return None, False
    # 模拟数据库查询
    return {"id": user_id, "name": f"User{user_id}"}, True

user, ok = get_user(42)
if ok:
    print(f"找到用户: {user['name']}")
```

---

## 三、命名元组（namedtuple）

### 3.1 概念解释

**命名元组（namedtuple）** 是 `collections` 模块提供的一个工厂函数，用于创建**带字段名称的元组子类**。

它结合了：
- **元组的优点**：不可变、轻量、可拆包
- **字典的优点**：字段名称具有自描述性，可以通过 `obj.field` 访问

```python
from collections import namedtuple

# 定义命名元组类型
# 语法：namedtuple('类型名', '字段名1 字段名2 ...')
Point = namedtuple('Point', ['x', 'y'])

# 创建实例
p = Point(3, 5)
print(p.x)       # 3  — 通过属性名访问
print(p.y)       # 5
print(p[0])      # 3  — 仍支持索引访问（因为它归根结底还是元组）
print(p)         # Point(x=3, y=5)

# 拆包
x, y = p
print(x, y)      # 3 5
```

### 3.2 为什么需要 namedtuple？

看一个对比，同样表示一个 2D 点：

```python
# 方式 1：普通元组 — 不明确
point1 = (3, 5)
# 直接用的话，阅读代码的人不知道 3 是 x 还是 y

# 方式 2：字典 — 可变且啰嗦
point2 = {'x': 3, 'y': 5}
print(point2['x'])  # 需要加引号

# 方式 3：自定义类 — 代码量多
class Point3:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 方式 4：namedtuple ✨ — 最佳平衡
Point4 = namedtuple('Point4', 'x y')
p = Point4(3, 5)
print(p.x)          # 简洁
x, y = p            # 支持拆包
print(p == Point4(3, 5))  # 自动实现 __eq__
```

### 3.3 namedtuple 的完整用法

```python
from collections import namedtuple

# ---------- 定义方式 ----------
# 方式 A：字段列表
Person = namedtuple('Person', ['name', 'age', 'city'])

# 方式 B：空格分隔的字符串（推荐简洁写法）
Person = namedtuple('Person', 'name age city')

# 方式 C：逗号分隔
Person = namedtuple('Person', 'name, age, city')

# ---------- 创建实例 ----------
p1 = Person('Alice', 30, 'Beijing')
p2 = Person(name='Bob', age=25, city='Shanghai')  # 关键字参数

# ---------- 访问 ----------
print(p1.name)    # Alice
print(p1[1])      # 30 — 索引仍然支持

# ---------- 不可变 ----------
# p1.age = 31     # ❌ AttributeError: can't set attribute

# ---------- 转换方法 ----------
# ._asdict() → 转为有序字典
print(p1._asdict())  # {'name': 'Alice', 'age': 30, 'city': 'Beijing'}

# ._replace() → 返回新实例（替换某些字段）
p1_new = p1._replace(age=31)
print(p1_new)    # Person(name='Alice', age=31, city='Beijing')
print(p1)        # Person(name='Alice', age=30, city='Beijing') — 原对象不变

# ._make() → 从可迭代对象创建
data = ['Charlie', 28, 'Shenzhen']
p3 = Person._make(data)
print(p3)        # Person(name='Charlie', age=28, city='Shenzhen')

# ---------- 获取字段信息 ----------
print(Person._fields)   # ('name', 'age', 'city') — 所有字段名
print(p1._field_defaults)  # {} — 默认值（如无则为空）

# ---------- 设置默认值 ----------
# 通过设置 __field_defaults__ 或使用 defaults 参数
PersonWithDefault = namedtuple('PersonWithDefault', 'name age city', defaults=['Unknown'])
p = PersonWithDefault('Alice', 30)
print(p)  # PersonWithDefault(name='Alice', age=30, city='Unknown')
# defaults 从右向左匹配：city → Unknown, age → 无默认, name → 无默认
```

### 3.4 namedtuple 的底层原理

`namedtuple` 实际上是一个**元类的动态类创建**：

```python
# namedtuple('Point', 'x y') 大致等价于：

class Point(tuple):
    """Point(x, y)"""
    
    _fields = ('x', 'y')
    
    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))
    
    @property
    def x(self):
        return self[0]
    
    @property
    def y(self):
        return self[1]
    
    def _replace(self, **kwargs):
        return self._make(kwargs.get(k, self[i]) for i, k in enumerate(self._fields))
    
    def _asdict(self):
        return {k: self[i] for i, k in enumerate(self._fields)}
    
    @classmethod
    def _make(cls, iterable):
        return cls(*iterable)
```

它继承自 `tuple`，所以：
- **内存布局和元组一致** — 不可变、轻量
- **通过 property 实现属性访问** — `p.x` 实际访问 `p[0]`
- **`__repr__` 自动生成** — 显示 `Point(x=3, y=5)` 而不是 `(3, 5)`

### 3.5 类型注解（Python 3.6+）

```python
from typing import NamedTuple

# 使用 typing.NamedTuple 的类语法（更可读）
class Point(NamedTuple):
    """2D 坐标点"""
    x: float
    y: float
    
    # 可以定义方法！
    def distance_from_origin(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

p = Point(3.0, 4.0)
print(p.distance_from_origin())  # 5.0

# typing.NamedTuple 和 collections.namedtuple 的关系：
# typing.NamedTuple 是 collections.namedtuple 的语法糖封装
# 本质还是创建了一个 namedtuple，额外加了类型注解
```

### 3.6 namedtuple 适用场景

| 场景 | 推荐使用 | 原因 |
|------|---------|------|
| 简单的数据容器（只有属性，没有行为） | namedtuple | 轻量、不可变、可读性高 |
| 复杂的业务对象（有方法） | 自定义类 | 需要更多行为支持 |
| 数据类（无行为，但属性多） | @dataclass | 更灵活（Day 048 详解） |
| 临时返回多个值 | 普通元组 | 最简单，不需要定义类型 |

---

## 四、列表 vs 元组性能对比

### 4.1 性能差异的根本原因

```python
import sys
import time

# ----- 内存占用 -----
list_mem = sys.getsizeof([1, 2, 3, 4, 5])
tuple_mem = sys.getsizeof((1, 2, 3, 4, 5))

print(f"列表内存: {list_mem} bytes")    # 列表内存: 104 bytes（因扩容策略，实际可能更大）
print(f"元组内存: {tuple_mem} bytes")   # 元组内存: 72 bytes

# 原因：列表需要额外的 allocated 字段和指针数组的空间预留，
#       元组的结构体一次性分配，不需要额外的指针数组

# ----- 创建速度 -----
N = 10_000_000

start = time.perf_counter()
for _ in range(N):
    [1, 2, 3]  # 列表字面量
list_time = time.perf_counter() - start

start = time.perf_counter()
for _ in range(N):
    (1, 2, 3)  # 元组字面量
tuple_time = time.perf_counter() - start

print(f"\n列表创建（{N}次）: {list_time:.3f}s")
print(f"元组创建（{N}次）: {tuple_time:.3f}s")
print(f"元组快了 {list_time/tuple_time:.1f}x")

# ----- 索引访问（两者无差异，都是 O(1)）-----
t = tuple(range(1000))
l = list(range(1000))

start = time.perf_counter()
for _ in range(N):
    _ = l[500]
list_index = time.perf_counter() - start

start = time.perf_counter()
for _ in range(N):
    _ = t[500]
tuple_index = time.perf_counter() - start

print(f"\n列表索引: {list_index:.3f}s")
print(f"元组索引: {tuple_index:.3f}s")
```

### 4.2 性能差异的底层分析

| 操作 | 列表 | 元组 | 原因 |
|------|------|------|------|
| **创建** | 慢 | 快 | 列表需要分配指针数组 + 预留扩容空间；元组一次分配 |
| **索引访问** | O(1) | O(1) | 都是连续内存的指针数组 |
| **追加/插入** | O(1)摊销/O(n) | ❌ 不支持 | 列表有动态扩容；元组不可变 |
| **删除/弹出** | O(n) | ❌ 不支持 | 列表需要移动元素 |
| **迭代** | 稍慢 | 稍快 | 元组没有修改检查开销 |
| **哈希** | ❌ 不支持 | ✅ 可哈希 | 列表可变 → 不可哈希；元组不可变 → 可哈希 |
| **内存** | 大 | 小 | 列表预留空间；元组精确大小 |

### 4.3 何时用列表，何时用元组？

```
同一段数据 → 数量可变？ → 是 → 列表
                       → 否 → 是同质数据？ → 是 → 列表（同质数据通常要增删）
                                              → 否 → 元组（异质固定结构）
```

**经验法则**：

```python
# ✅ 用元组（不可变、固定结构）
# - 函数的返回值（多个值一起返回）
# - 字典的键
# - 配置常量（如颜色 RGB 值：RED = (255, 0, 0)）
# - 数据库查询的一行记录

# ✅ 用列表（可变、可增长）
# - 需要频繁增删的数据集合
# - 存储同类型数据的序列
# - 栈、队列等数据结构
# - 需要排序或修改的数据
```

### 4.4 字典键的使用

因为元组可哈希（hashable），而列表不可，所以元组可以做字典的键：

```python
# ✅ 元组做键
locations = {
    (40.7128, -74.0060): "New York",    # 经纬度坐标对
    (31.2304, 121.4737): "Shanghai",
    (35.6762, 139.6503): "Tokyo",
}

# ❌ 列表不能做键
# d = {[1, 2]: "error"}  # TypeError: unhandled TypeError: unhashable type: 'list'

# 为什么元组可哈希？
# 元组的 __hash__() 基于其包含元素的哈希值计算得到
# 因为元组不可变，所以哈希值在创建后不会改变
# 列表可变 → 哈希值会变 → 不能做字典键

print(hash((1, 2, 3)))   # 输出一个整数
# print(hash([1, 2, 3]))  # TypeError: unhashable type: 'list'
```

---

## 五、图解：元组与列表的内存对比

### 5.1 内存布局对比图

```ascii
列表 [1, 2, 3]          元组 (1, 2, 3)
                       
┌──────────────┐       ┌──────────────┐
│  PyObject 头  │       │  PyObject 头  │
│  ob_size = 3  │       │  ob_size = 3  │
│  allocated = 4│       │               │
│               │       │  ob_item[0]───┼──→ PyLong(1)
│  ob_item[0]───┼──→ 1  │  ob_item[1]───┼──→ PyLong(2)
│  ob_item[1]───┼──→ 2  │  ob_item[2]───┼──→ PyLong(3)
│  ob_item[2]───┼──→ 3  └──────────────┘
│  [未使用]     │       [精确分配，无浪费]
│  ob_item[3]───┼──→ ?  
└──────────────┘
 [有额外预留空间]
```

### 5.2 操作复杂度对比图

```mermaid
graph TB
    subgraph "列表 List"
        A[创建] --> B[O(n) 分配+初始化]
        C[索引] --> D[O(1)]
        E[追加] --> F[O(1) 摊销]
        G[插入] --> H[O(n) 移动元素]
        I[删除] --> J[O(n) 移动元素]
    end
    
    subgraph "元组 Tuple"
        K[创建] --> L[O(n) 一次分配]
        M[索引] --> N[O(1)]
        O[修改] --> P[❌ 不支持]
        Q[哈希] --> R[✅ O(n)]
        S[字典键] --> T[✅ 可用]
    end
```

### 5.3 拆包原理图

```ascii
元组拆包过程：
    point = (3, 7)
    
    x, y = point
    
    1. 右侧 point 求值 → 得到元组对象 (3, 7)
    2. Python 获取元组的迭代器
    3. 依次取出元素：
       x = next(iterator)  →  x = 3
       y = next(iterator)  →  y = 7

星号拆包过程：
    first, *middle, last = (1, 2, 3, 4, 5)
    
    1. *middle 捕获中间所有元素
    2. first = 1 (左边的第一个)
    3. middle = [2, 3, 4] (星号变量 → 总是列表)
    4. last = 5 (右边的第一个)
```

---

## 六、实战：坐标系统

### 6.1 问题描述

构建一个完整的 2D/3D 坐标系统，包含：
- 点的创建、距离计算
- 批量坐标变换
- 数据记录与查找

### 6.2 完整代码

```python
from collections import namedtuple
from typing import List, Tuple, Optional
import math
import json

# ======================================================
# 定义坐标类型
# ======================================================

# 2D 坐标点（使用 namedtuple）
Point2D = namedtuple('Point2D', ['x', 'y'])

# 3D 坐标点（使用 typing.NamedTuple 类语法）
class Point3D(NamedTuple):
    """3D 空间坐标点"""
    x: float
    y: float
    z: float
    
    def __str__(self) -> str:
        return f"({self.x:.2f}, {self.y:.2f}, {self.z:.2f})"


# ======================================================
# 坐标计算工具
# ======================================================

class CoordinateUtils:
    """坐标系统工具类"""
    
    @staticmethod
    def distance_2d(p1: Point2D, p2: Point2D) -> float:
        """计算两点间 2D 欧几里得距离"""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)
    
    @staticmethod
    def distance_3d(p1: Point3D, p2: Point3D) -> float:
        """计算两点间 3D 欧几里得距离"""
        return math.sqrt(
            (p1.x - p2.x) ** 2 + 
            (p1.y - p2.y) ** 2 + 
            (p1.z - p2.z) ** 2
        )
    
    @staticmethod
    def midpoint_2d(p1: Point2D, p2: Point2D) -> Point2D:
        """计算两点间 2D 中点"""
        return Point2D(
            (p1.x + p2.x) / 2,
            (p1.y + p2.y) / 2,
        )
    
    @staticmethod
    def midpoint_3d(p1: Point3D, p2: Point3D) -> Point3D:
        """计算两点间 3D 中点"""
        return Point3D(
            (p1.x + p2.x) / 2,
            (p1.y + p2.y) / 2,
            (p1.z + p2.z) / 2,
        )
    
    @staticmethod
    def translate_2d(point: Point2D, dx: float, dy: float) -> Point2D:
        """平移 2D 点"""
        return Point2D(point.x + dx, point.y + dy)
    
    @staticmethod
    def translate_3d(point: Point3D, dx: float, dy: float, dz: float) -> Point3D:
        """平移 3D 点"""
        return Point3D(point.x + dx, point.y + dy, point.z + dz)
    
    @staticmethod
    def polygon_perimeter(points: List[Point2D]) -> float:
        """计算多边形周长（点按顺序连接）"""
        if len(points) < 2:
            return 0.0
        
        perimeter = 0.0
        n = len(points)
        for i in range(n):
            p1 = points[i]
            p2 = points[(i + 1) % n]  # 回到第一个点闭合多边形
            perimeter += CoordinateUtils.distance_2d(p1, p2)
        return perimeter


# ======================================================
# 坐标数据管理器
# ======================================================

class CoordinateDatabase:
    """坐标数据库 — 使用元组做键（因为可哈希）"""
    
    def __init__(self):
        # 使用 (x, y) 元组作为键，城市名作为值
        self._cities: dict[Tuple[float, float], str] = {}
        # 使用 namedtuple 作为键存储地标数据
        self._landmarks: dict[Point2D, dict] = {}
    
    def add_city(self, name: str, lat: float, lng: float):
        """添加城市坐标（未命名元组做键）"""
        self._cities[(lat, lng)] = name
    
    def find_city(self, lat: float, lng: float) -> Optional[str]:
        """根据坐标查找城市"""
        return self._cities.get((lat, lng))
    
    def add_landmark(self, name: str, description: str, x: float, y: float):
        """添加地标（namedtuple 做键）"""
        point = Point2D(x, y)
        self._landmarks[point] = {
            'name': name,
            'description': description,
        }
    
    def find_landmark(self, x: float, y: float) -> Optional[dict]:
        """根据坐标查找地标"""
        return self._landmarks.get(Point2D(x, y))
    
    def get_all_points(self) -> List[Point2D]:
        """获取所有地标记坐标"""
        return list(self._landmarks.keys())
    
    def list_cities_near(self, center_lat: float, center_lng: float, radius_km: float) -> list:
        """查找指定半径内的城市（简化版本，不考虑地球曲率）"""
        center = Point2D(center_lat, center_lng)
        results = []
        for (lat, lng), name in self._cities.items():
            p = Point2D(lat, lng)
            # 1度 ≈ 111km（简化）
            dist = CoordinateUtils.distance_2d(center, p) * 111
            if dist <= radius_km:
                results.append((name, dist))
        return sorted(results, key=lambda x: x[1])


# ======================================================
# 主程序演示
# ======================================================

def main():
    print("=" * 60)
    print("📍 坐标系统实战演示")
    print("=" * 60)
    
    # ---- 基础操作 ----
    print("\n1️⃣  基础坐标操作")
    p1 = Point2D(1.0, 2.0)
    p2 = Point2D(4.0, 6.0)
    print(f"  点1: {p1}")
    print(f"  点2: {p2}")
    print(f"  距离: {CoordinateUtils.distance_2d(p1, p2):.2f}")
    print(f"  中点: {CoordinateUtils.midpoint_2d(p1, p2)}")
    
    # ---- 3D 坐标 ----
    print("\n2️⃣  3D 空间操作")
    pp1 = Point3D(0, 0, 0)
    pp2 = Point3D(1, 1, 1)
    print(f"  3D 点1: {pp1}")
    print(f"  3D 点2: {pp2}")
    print(f"  3D 距离: {CoordinateUtils.distance_3d(pp1, pp2):.2f}")
    
    # ---- 坐标变换 ----
    print("\n3️⃣  坐标变换")
    p = Point2D(5, 5)
    p_moved = CoordinateUtils.translate_2d(p, 3, -2)
    print(f"  原坐标: {p}")
    print(f"  平移后: {p_moved}")
    
    # ---- 多边形周长 ----
    print("\n4️⃣  多边形周长")
    triangle = [
        Point2D(0, 0),
        Point2D(3, 0),
        Point2D(0, 4),
    ]
    perimeter = CoordinateUtils.polygon_perimeter(triangle)
    print(f"  三角形顶点: {triangle}")
    print(f"  周长: {perimeter:.2f}")
    
    # ---- 坐标数据库 ----
    print("\n5️⃣  坐标数据库（元组作为字典键）")
    db = CoordinateDatabase()
    
    # 添加城市
    db.add_city("北京", 39.9042, 116.4074)
    db.add_city("上海", 31.2304, 121.4737)
    db.add_city("广州", 23.1291, 113.2644)
    db.add_city("深圳", 22.5431, 114.0579)
    db.add_city("成都", 30.5728, 104.0668)
    
    # 查找城市
    city = db.find_city(31.2304, 121.4737)
    print(f"  (31.2304, 121.4737) → {city}")
    
    # 附近城市搜索
    print("\n  🏙️  上海附近 500km 内的城市:")
    nearby = db.list_cities_near(31.2304, 121.4737, 500)
    for name, dist in nearby:
        print(f"    {name}: {dist:.0f}km")
    
    # 使用 namedtuple 作为键存储地标
    print("\n  🏛️  地标数据库:")
    db.add_landmark("天安门广场", "世界最大城市广场", 39.9042, 116.3972)
    db.add_landmark("东方明珠塔", "上海标志性建筑", 31.2397, 121.4997)
    db.add_landmark("广州塔", "广州地标", 23.1065, 113.3246)
    
    landmark = db.find_landmark(39.9042, 116.3972)
    if landmark:
        print(f"    (39.9042, 116.3972) → {landmark['name']}: {landmark['description']}")

if __name__ == "__main__":
    main()
```

---

## 七、思考题

1. 🤔 **元组的"不可变"到底是什么意思？** 如果元组中包含一个列表，列表的内容可以修改吗？为什么？这算不算破坏了"不可变性"？

2. 🧮 **拆包的底层机制**：`a, b = b, a` 这行代码在 Python 中是如何工作的？请从字节码层面解释。

3. ⚡ **性能选择**：为什么 CPython 的 Parser 在解析函数参数时，用 `*args` 接收多余参数时始终返回一个元组而不是列表？背后的设计考虑是什么？

4. 🔑 **可哈希性**：一个包含列表的元组 `t = (1, [2, 3])` 可以被哈希吗？为什么？这与元组的不可变性有何关系？

5. 🏗️ **设计权衡**：Python 已经有一等公民的 `list`，为什么还要引入 `tuple`？如果没有元组，用只读列表替代（比如在 JavaScript 中），会丢失什么？

---

## 📚 今日回顾

| 主题 | 掌握程度 |
|------|---------|
| 元组不可变性原理 | □ 理解 □ 熟练 □ 精通 |
| 元组拆包与多返回值 | □ 理解 □ 熟练 □ 精通 |
| namedtuple 使用 | □ 理解 □ 熟练 □ 精通 |
| 列表 vs 元组性能对比 | □ 理解 □ 熟练 □ 精通 |
| 实战：坐标系统 | □ 理解 □ 熟练 □ 精通 |
