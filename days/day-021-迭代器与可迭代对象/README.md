# Day 021 — 迭代器与可迭代对象 (Iterator & Iterable)

<!-- Updated 2026-06-15: Added for loop implementation details and __getitem__ fallback mechanism -->

## 概述

**迭代器（Iterator）** 和 **可迭代对象（Iterable）** 是 Python 中遍历数据的核心抽象。理解它们的关系和差异，是掌握 Python 数据流处理的关键一步。

> **一句话理解**：可迭代对象是"可以产生迭代器的东西"，迭代器是"可以逐个取值的东西"。

## 📚 可迭代对象 vs 迭代器 vs 生成器

### 三者的层次关系

```
┌──────────────────────────────────────┐
│          可迭代对象 (Iterable)         │
│  ┌──────────────────────────────────┐│
│  │        迭代器 (Iterator)          ││
│  │  ┌────────────────────────────┐  ││
│  │  │    生成器 (Generator)      │  ││
│  │  └────────────────────────────┘  ││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```

### 对比速查表

| 特性 | 可迭代对象 (Iterable) | 迭代器 (Iterator) | 生成器 (Generator) |
|------|----------------------|-------------------|-------------------|
| **可 for 循环** | ✅ | ✅ | ✅ |
| **有 `__iter__()`** | ✅ | ✅ | ✅ |
| **有 `__next__()`** | ❌ | ✅ | ✅ |
| **可多次遍历** | ✅ | ❌（只能一次） | ❌（只能一次） |
| **惰性求值** | ❌ | ✅ | ✅ |
| **使用 `yield`** | ❌ | ❌ | ✅ |
| **举例** | list, str, dict, tuple, set | iter([]), 文件句柄 | 生成器函数返回值 |

### 判断方法

```python
from collections.abc import Iterable, Iterator, Generator

# 检查
print(isinstance([1, 2, 3], Iterable))   # True
print(isinstance([1, 2, 3], Iterator))   # False
print(isinstance(iter([1, 2, 3]), Iterable))  # True
print(isinstance(iter([1, 2, 3]), Iterator))  # True
```

## 🏗️ 迭代器协议 (Iterator Protocol)

### 协议定义

迭代器协议由两个魔法方法组成：

| 方法 | 作用 | 返回值 |
|------|------|--------|
| `__iter__(self)` | 返回迭代器自身 | `self` |
| `__next__(self)` | 返回下一个元素 | 元素值，或抛出 `StopIteration` |

### 协议流程

```
可迭代对象          iter()          迭代器           next()          值
  list       ──────────────→   list_iterator  ──────────────→  元素
  str                          str_iterator                     ...
  dict                         dict_keyiterator                 StopIteration
```

### 完整契约

```python
class IteratorProtocol:
    """迭代器协议的完整契约"""

    def __iter__(self):
        """返回迭代器对象本身"""
        return self

    def __next__(self):
        """返回下一个元素，没有元素时抛出 StopIteration"""
        if self._exhausted:
            raise StopIteration
        # ... 返回下一个值
```

## 🔄 for 循环底层实现原理

### 等价代码

Python 的 `for x in iterable:` 语句底层实际上执行的是：

```python
# for x in iterable:
#     print(x)

# 等价于：
_iterator = iter(iterable)     # 1. 获取迭代器
while True:
    try:
        x = next(_iterator)     # 2. 逐个取值
    except StopIteration:       # 3. 捕捉结束信号
        break
    print(x)                    # 4. 执行循环体
del _iterator                   # 5. 清理迭代器
```

### 步骤详解

**步骤 1: `iter(iterable)`**
- 调用 `iterable.__iter__()` 或 `iterable.__getitem__(0)`（回退方案）
- 返回一个迭代器对象

**步骤 2-3: `next(iterator)` 和 `StopIteration`**
- 反复调用 `next(iterator)`（等价于 `iterator.__next__()`）
- 当迭代器耗尽时抛出 `StopIteration`，循环正常结束

**步骤 4-5: 循环体和清理**
- 每次迭代执行循环体代码
- 循环结束后删除迭代器引用（触发 GC）

### `__getitem__` 回退机制

如果对象没有 `__iter__()` 但有 `__getitem__()`，Python 会创建一个旧的序列迭代器：

```python
class OldStyleIterable:
    """旧式可迭代对象——只有 __getitem__"""
    def __init__(self, data):
        self.data = data

    def __getitem__(self, index):
        if index >= len(self.data):
            raise IndexError     # Python 捕获 IndexError 并转为 StopIteration
        return self.data[index]

# 仍然可以 for 循环！
for x in OldStyleIterable([1, 2, 3]):
    print(x)  # 1, 2, 3
```

> ⚠️ **注意**：`__getitem__` 是 Python 2 的遗留协议。Python 3 优先使用 `__iter__()`。推荐始终实现 `__iter__()`。

## 🔧 迭代器的惰性求值（Lazy Evaluation）

### 什么是惰性求值？

迭代器的核心优势是**惰性求值**——只在需要时才计算下一个值。这意味着：

1. **节省内存**：可以处理无限序列或超大文件
2. **节省CPU**：不需要一次性计算所有值
3. **支持无限数据流**：理论上可以永不停止

```python
# ❌ 列表：一次性加载所有数据到内存
all_lines = file.readlines()  # 大文件时内存爆炸

# ✅ 迭代器：逐行读取，每次只占一行内存
for line in file:             # file 本身是迭代器
    process(line)

# ❌ 列表推导式：立即生成全部结果
squares = [x**2 for x in range(10**7)]  # 内存爆炸！

# ✅ 迭代器：按需生成
squares = (x**2 for x in range(10**7))  # 几乎不占内存
```

### 无限迭代器

```python
class Counter:
    """无限递增的迭代器——演示惰性求值"""
    def __init__(self, start=0):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        result = self.current
        self.current += 1
        return result

# 永远不会构造完 10 亿个元素的列表
# 只会在 for 循环中逐个生成
counter = Counter()
for i, val in enumerate(counter):
    if i >= 10:
        break
    print(val)  # 0, 1, 2, ..., 9
```

## 🔗 itertools 标准库

### 核心函数速查

| 函数 | 作用 | 等价于 | 示例 |
|------|------|--------|------|
| `count(start, step)` | 无限等差数列 | `start, start+step, ...` | `count(10, 2)` → 10, 12, 14... |
| `cycle(iterable)` | 无限循环 | `A, B, C, A, B, C, ...` | `cycle('ABC')` → A, B, C, A... |
| `repeat(elem, n)` | 重复元素 n 次 | `elem, elem, ...` | `repeat(5, 3)` → 5, 5, 5 |
| `chain(*iters)` | 串联多个迭代器 | `a1, a2, b1, b2` | `chain('AB', 'CD')` → A, B, C, D |
| `zip_longest(*iters)` | 类似 zip 但以最长为准 | 填充 `fillvalue` | 见下方示例 |
| `islice(iter, start, stop)` | 迭代器切片 | 惰性切片 | `islice(count(), 5)` → 0-4 |
| `takewhile(pred, iter)` | 条件为真时取值 | | 从开头取直到条件不满足 |
| `dropwhile(pred, iter)` | 跳过条件为真的部分 | | 从条件不满足开始取 |
| `product(*iters)` | 笛卡尔积 | 嵌套 for | `product('AB', '12')` |
| `permutations(iter, r)` | 排列 | | |
| `combinations(iter, r)` | 组合 | | |
| `groupby(iter, key)` | 相邻元素分组 | | 类似 SQL GROUP BY |

### 实战示例

```python
import itertools

# 1. count + islice = 惰性切片
evens = itertools.count(start=0, step=2)
first_10 = list(itertools.islice(evens, 10))  # [0, 2, 4, ... 18]

# 2. cycle 实现轮询
servers = ['S1', 'S2', 'S3']
pool = itertools.cycle(servers)
assignments = [next(pool) for _ in range(7)]  # ['S1','S2','S3','S1','S2','S3','S1']

# 3. chain 合并多个迭代器
result = list(itertools.chain([1, 2], [3, 4], 'AB'))  # [1, 2, 3, 4, 'A', 'B']

# 4. zip_longest 处理不等长
a = [1, 2, 3]
b = ['a', 'b']
padded = list(itertools.zip_longest(a, b, fillvalue='N/A'))
# [(1, 'a'), (2, 'b'), (3, 'N/A')]

# 5. groupby 分组（必须已排序）
data = [('A', 1), ('A', 2), ('B', 3), ('B', 4)]
for key, group in itertools.groupby(data, key=lambda x: x[0]):
    print(key, list(group))  # A [(A,1),(A,2)]  B [(B,3),(B,4)]
```

## 🚨 常见陷阱与注意事项

### 陷阱 1: 迭代器只能遍历一次

```python
nums = iter([1, 2, 3])

# 第一次遍历：正常
for x in nums:
    print(x)  # 1, 2, 3

# 第二次遍历：什么都没有！
for x in nums:
    print(x)  # (无输出) — 迭代器已经耗尽

# ✅ 解决：需要重新创建迭代器
nums = iter([1, 2, 3])
```

### 陷阱 2: 在迭代时修改集合

```python
# ❌ RuntimeError: Set changed size during iteration
items = {1, 2, 3, 4, 5}
for item in items:
    if item % 2 == 0:
        items.remove(item)

# ✅ 正确做法：先复制再遍历
for item in list(items):  # list() 创建副本
    if item % 2 == 0:
        items.remove(item)
```

### 陷阱 3: 生成器被意外耗尽

```python
# 小心：传给多个函数可能导致意外耗尽
def check_positive(nums):
    return all(x > 0 for x in nums)

def sum_squares(nums):
    return sum(x**2 for x in nums)

data = (x for x in [1, 2, -3, 4])  # 生成器
print(check_positive(data))  # False（遍历到 -3 时停止）
print(sum_squares(data))     # 只得到 4²=16，因为生成器已部分耗尽！

# ✅ 改用列表
data = [1, 2, -3, 4]
```

### 陷阱 4: 递归迭代器的深层嵌套

```python
# chain 嵌套 chain：没问题，惰性的
deep = itertools.chain.from_iterable(
    itertools.chain.from_iterable(...)
)

# 但打印调试时会立即求值
list(deep)  # 小心内存！
```

## 🎨 Mermaid 图解

### 迭代器协议流程

```mermaid
sequenceDiagram
    participant Code as Python代码
    participant Iterable as 可迭代对象 (list)
    participant Iterator as 迭代器
    participant Elements as 元素列表

    Code->>Iterable: iter([1,2,3])
    Iterable-->>Iterator: __iter__() → list_iterator
    Code->>Iterator: next(it)
    Iterator->>Elements: __next__()
    Elements-->>Iterator: 1
    Iterator-->>Code: 1
    Code->>Iterator: next(it)
    Elements-->>Iterator: 2
    Iterator-->>Code: 2
    Code->>Iterator: next(it)
    Elements-->>Iterator: 3
    Iterator-->>Code: 3
    Code->>Iterator: next(it)
    Elements-->>Iterator: StopIteration
    Iterator-->>Code: StopIteration 异常
    Note over Code: 循环结束
```

### 可迭代对象 → 迭代器 → 元素

```mermaid
flowchart LR
    subgraph 可迭代对象
        L1["list [1,2,3]"]
    end
    subgraph iter函数
        I1["iter()"]
    end
    subgraph 迭代器
        IT1["list_iterator<br/>__iter__ → self<br/>__next__ → value"]
    end
    subgraph 逐个取值
        N1["next()"]
        N2["next()"]
        N3["StopIteration"]
    end

    L1 --> I1 --> IT1
    IT1 --> N1 --> 1
    IT1 --> N2 --> 2
    IT1 --> N3
```

### for 循环底层等价代码流程图

```mermaid
flowchart TD
    A["for x in iterable:"] --> B["it = iter(iterable)"]
    B --> C{"try:<br/>x = next(it)"}
    C -->|成功| D["执行循环体<br/>print(x)"]
    D --> C
    C -->|StopIteration| E["except StopIteration:<br/>break"]
    E --> F["del it"]
    F --> G["循环结束"]
```

### 常见迭代器关系

```mermaid
graph TD
    subgraph 内置类型
        L(List) --> I(可迭代对象)
        S(Str) --> I
        D(Dict) --> I
        T(Tuple) --> I
    end

    subgraph 迭代器
        LI("list_iterator") --> Ir(迭代器)
        FI("file_iterator") --> Ir
        GI("generator") --> Ir
    end

    I -->|"iter()"| Ir
    Ir -->|"next()"| EI(元素)
    Ir -->|"list()"| ALL(全部元素)
```

## 📝 思考题

1. 为什么迭代器遍历过一次后就不能再次遍历？设计上的考虑是什么？

**参考答案**

迭代器本质上是一个**有状态的"游标"**：内部记录着"读到哪儿了"，每调用一次 `__next__()` 就把游标往前挪一格，走到尽头抛出 `StopIteration`，且游标停在末尾**不会自动回退**。所以再遍历一次就什么都取不到。

```python
it = iter([1, 2, 3])
print(list(it))   # [1, 2, 3]
print(list(it))   # [] —— 已经耗尽，不会自动重置
```

预期输出：

```text
[1, 2, 3]
[]
```

设计上的考虑：

- **支持惰性 / 一次性数据流**：迭代器可能代表文件句柄、网络套接字、无限序列，数据根本没全部存在内存里，物理上无法"倒带"。一次性设计才能统一处理这些场景。
- **节省内存**：不必为了"能重复遍历"而缓存所有元素。
- **职责分离**："可重复遍历"是**可迭代对象**（容器）的事——每次 `iter(容器)` 都产生一个**全新**迭代器。所以列表能被反复 `for`，而迭代器对象本身是一次性的。

💡 提示：想再遍历一次，要么重新 `iter(容器)` 拿新迭代器，要么先 `list(it)` 把结果固化成列表。

2. 用自己的话说说 `__iter__()` 和 `__next__()` 方法的各自职责。

**参考答案**

用大白话说，两个方法分别负责"开始"和"前进"：

- **`__iter__(self)`**：负责"交出迭代器"。`for` 循环和 `iter()` 内置函数会先调用它。对**迭代器**而言，约定返回它自己（`return self`）；对**可迭代对象**（如列表）而言，它返回一个新建的迭代器。它就像按下"从头播放"，拿到一个遥控器。
- **`__next__(self)`**：负责"给我下一个元素"。每调用一次就返回当前值并把内部状态推进一步；没有元素时抛出 `StopIteration` 表示"结束"。它就像按遥控器的"下一首"。

关键区别：一个对象**同时**拥有 `__iter__`（返回自身）和 `__next__` 才是**迭代器**；而**可迭代对象**只需要 `__iter__`。所以列表能被 `for`（有 `__iter__`），却不能直接 `next()`（没有 `__next__`），必须先 `iter(列表)` 拿到迭代器。

3. 实现一个迭代器来生成斐波那契数列——和递归版本、迭代版本比有什么优劣势？

**参考答案**

```python
class FibIterator:
    """逐个产出斐波那契数列的迭代器（可以是无限序列）"""
    def __init__(self, limit=None):
        self.a, self.b = 0, 1     # 最近两项
        self.limit = limit        # 可选：最多产出多少项
        self.count = 0

    def __iter__(self):
        return self               # 迭代器返回自身

    def __next__(self):
        if self.limit is not None and self.count >= self.limit:
            raise StopIteration   # 达到数量上限，结束
        value = self.a
        self.a, self.b = self.b, self.a + self.b   # 推进状态
        self.count += 1
        return value

print(list(FibIterator(10)))           # 前 10 项
fib = FibIterator()                    # 无限序列，按需取用
print([next(fib) for _ in range(5)])
```

预期输出：

```text
[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
[0, 1, 1, 2, 3]
```

与另外两种版本对比：

- **对比朴素递归**：迭代器逐项推进，O(n) 时间、O(1) 额外空间，无重复计算，也不受递归深度限制；朴素递归是 O(2ⁿ)，n 一大就栈溢出。
- **对比迭代（返回 list 的函数）**：两者都是 O(n) 时间，但迭代器是**惰性**的——能表示无限序列，取多少算多少，内存 O(1)；而一次性建好列表的版本占 O(n) 内存，且必须先算完才能返回。
- **代价**：迭代器一次性、不支持索引和 `len()`，代码也比普通循环稍多。

💡 提示：用生成器（`yield`）写这种迭代器会更简洁，状态由解释器自动保存——这正是下一课 Day 022 的主题。

4. `range()` 返回的是什么？是迭代器吗？用代码验证。

**参考答案**

```python
from collections.abc import Iterable, Iterator

r = range(5)
print(type(r))                   # <class 'range'>
print(isinstance(r, Iterable))   # True：可迭代对象
print(isinstance(r, Iterator))   # False：但不是迭代器
print(hasattr(r, '__next__'))    # False：没有 __next__

it = iter(r)                     # iter() 之后才得到真正的迭代器
print(type(it))                  # <class 'range_iterator'>
print(next(it))                  # 0

print(list(r), list(r))          # range 可反复遍历
```

预期输出：

```text
<class 'range'>
True
False
False
<class 'range_iterator'>
0
[0, 1, 2, 3, 4] [0, 1, 2, 3, 4]
```

结论：`range()` 返回的是一个 **`range` 对象——惰性的不可变序列（可迭代对象），不是迭代器**。它只保存 start/stop/step 三个参数，按需计算元素，所以 `range(10**9)` 几乎不占内存；但它支持反复遍历、索引、`len()`、`in` 判断，这些是迭代器做不到的。只有 `iter(range(...))` 才得到真正的迭代器 `range_iterator`。

5. 如何实现一个"可暂停、可恢复"的迭代器？需要存储哪些状态？

**参考答案**

迭代器**天然就是"可暂停、可恢复"的**：每次 `__next__()` 算出一个值并返回，就是"暂停"；下一次调用 `next()` 就是"恢复"。关键在于——**要把"算下一个值所需的状态"保存在对象上**，让它在两次调用之间存活，而不是放在函数返回即销毁的临时局部变量里。

需要存储的状态：当前位置 / 索引、最近几项的值（如斐波那契的两项）、计数器、底层数据源的引用、是否已结束的标志等，一句话——"继续算下一个值所必需的一切"。

```python
class PausableCounter:
    """可暂停 / 可恢复的迭代器：状态保存在对象上，跨 next() 调用保留"""
    def __init__(self, start, stop):
        self.current = start     # 状态①：当前位置
        self.stop = stop         # 状态②：结束边界

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.stop:
            raise StopIteration
        value = self.current
        self.current += 1        # 更新状态后返回，相当于"暂停"
        return value

c = PausableCounter(0, 5)
print(next(c))     # 0：取一个就暂停
print(next(c))     # 1：从上次位置恢复
print(c.current)   # 2：能看到保存的状态
print(list(c))     # [2, 3, 4]：继续取完剩余
```

预期输出：

```text
0
1
2
[2, 3, 4]
```

这里 `self.current` 跨调用持久存在，就是"恢复"的全部秘密。生成器（`yield`）做的是同一件事，只不过由解释器自动帮你保存局部变量和执行位置，无需手写状态管理。

6. `itertools.chain` 和 `+` 运算符拼接列表有什么区别？

**参考答案**

```python
import itertools

a = [1, 2]
b = [3, 4]

plus = a + b                     # + ：立即生成新列表，复制全部元素
print(plus, type(plus))

ch = itertools.chain(a, b)       # chain ：返回惰性迭代器，不复制
print(type(ch))
print(list(ch))

# chain 可拼接任意可迭代对象（类型可不同）
print(list(itertools.chain([1, 2], 'AB', (3,))))
```

预期输出：

```text
[1, 2, 3, 4] <class 'list'>
<class 'itertools.chain'>
[1, 2, 3, 4]
[1, 2, 'A', 'B', 3]
```

主要区别：

- **急切 vs 惰性**：`+` 立刻新建一个列表并复制所有元素，O(n+m) 时间和内存；`chain` 返回迭代器，不复制元素，遍历时才逐个产出，额外内存 O(1)。
- **类型限制**：`+` 要求两边同类型（list + list）；`chain` 接受任意可迭代对象，可混合列表、字符串、元组等。
- **可复用性**：`+` 的结果是列表，可反复遍历、可索引；`chain` 的结果是一次性迭代器。

💡 提示：需要"拿到一个具体、可复用的列表"时用 `+`；需要"省内存地流式拼接"大量或无限序列时用 `chain`。另外 `chain` 是惰性的，消费前若原容器变化会反映最新内容，而 `+` 已经复制完毕、不受影响。

7. 什么时候应该选择用迭代器而不是列表？什么时候反过来？

**参考答案**

**优先用迭代器 / 生成器**的场景：

- 数据量大或无限：逐行读大文件、日志流、传感器数据，内存装不下全部。
- 只需要**单次遍历**、边读边处理，不需要回头。
- 想构建**惰性管道**（map / filter / chain 串联），节省内存。
- 需要**短路求值**：`any` / `all` / `takewhile` 等一旦确定结果就停止，不必算完全部。

**优先用列表**的场景：

- 需要**随机访问**（索引）、切片、`len()`、排序、成员判断。
- 需要**多次遍历**，或把同一份数据交给多个消费者。
- 数据量小，且需要修改（增删元素）。

权衡一句话：迭代器省内存但一次性、不能索引 / `len()`；列表灵活可复用但一次性占满内存。经验法则——"一次性处理大数据流 → 迭代器；小数据要反复 / 随机访问 → 列表"。

8. 请写出 `for x in obj:` 在 CPython 虚拟机中的完整执行步骤。

**参考答案**

在 CPython 字节码层面，`for x in obj:` 大致经历以下步骤：

1. **`GET_ITER`**：求出 `obj` 并调用 `iter(obj)`，即触发 `obj.__iter__()`（若没有则回退到 `__getitem__` 旧序列协议），把得到的迭代器压入值栈。
2. **`FOR_ITER`**：循环头部，调用 `next(iterator)`（即 `iterator.__next__()`）。若返回一个值，就压栈并进入循环体；若抛出 `StopIteration`，`FOR_ITER` 会**内部捕获**它、弹出迭代器并跳到循环之后——异常不会向外传播。
3. **`STORE_FAST x`**：把取到的值绑定到循环变量 `x`。
4. **执行循环体**：依次运行循环内语句的字节码。
5. **`JUMP_BACKWARD`**（3.12；旧版本是 `JUMP_ABSOLUTE`）：跳回 `FOR_ITER`，重复第 2 步。
6. **收尾**：循环结束后弹出迭代器；若有 `else` 子句，仅在循环**未被 `break`** 打断时执行。

可以用 `dis` 直接观察这些指令：

```python
import dis

def loop():
    for x in [1, 2, 3]:
        print(x)

dis.dis(loop)
```

在本机（Python 3.12）的实际输出：

```text
  3           0 RESUME                   0

  4           2 LOAD_CONST               1 ((1, 2, 3))
              4 GET_ITER
        >>    6 FOR_ITER                13 (to 36)
             10 STORE_FAST               0 (x)

  5          12 LOAD_GLOBAL              1 (NULL + print)
             22 LOAD_FAST                0 (x)
             24 CALL                     1
             32 POP_TOP
             34 JUMP_BACKWARD           15 (to 6)

  4     >>   36 END_FOR
             38 RETURN_CONST             0 (None)
```

可以看到 `GET_ITER → FOR_ITER → STORE_FAST →（循环体）→ JUMP_BACKWARD` 这几条关键指令构成闭环。

⚠️ 注意：具体指令名、偏移量和跳转目标随 Python 版本变化（如 3.12 用 `JUMP_BACKWARD` / `END_FOR`，旧版本用 `JUMP_ABSOLUTE`）。上面输出取自 Python 3.12，重点是理解执行流程，而非死记偏移量。

## 🔗 延伸阅读

- [PEP 234 — Iterators](https://peps.python.org/pep-0234/)
- [Python docs: Iterator Types](https://docs.python.org/3/library/stdtypes.html#iterator-types)
- [Python docs: itertools](https://docs.python.org/3/library/itertools.html)
- [Fluent Python — Chapter 17: Iterators, Generators, and Coroutines](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/)
