# Day 008 — 字典（Dict）

> "Python 字典就是一台哈希表引擎——O(1) 的读写速度，让数据检索变成真正的瞬间"

---

## 📋 今日学习目标

- [ ] 理解哈希表原理与字典的底层实现
- [ ] 掌握字典的创建、访问与常用方法
- [ ] 熟练运用字典推导式
- [ ] 掌握 defaultdict/Counter 等进阶工具
- [ ] 理解字典的哈希约束（什么能做键）
- [ ] 完成实战：词频统计器

---

## 一、哈希表原理与字典实现

### 1.1 概念解释

**字典（dict）** 是 Python 中最重要、最高效的数据结构之一。它存储的是 **键-值对（key-value pair）**，通过键来快速查找对应的值。

```python
# 创建字典的多种方式
empty = {}                              # 空字典
literal = {"name": "Alice", "age": 25}  # 字面量
dict_fn = dict(name="Alice", age=25)    # dict() 构造函数
zipped = dict(zip(["a","b"], [1,2]))    # 从 zip 转换
pairs = dict([("a",1), ("b",2)])        # 从键值对列表
from_keys = dict.fromkeys(["a","b","c"], 0)  # 统一赋初值
```

**为什么字典这么快？**

字典的底层实现是 **哈希表（hash table）**。哈希表的核心思想是：通过一个**哈希函数**将键（key）直接映射到内存槽位的索引，从而在 O(1) 时间内完成查找。

```python
# 字典的基本操作 — O(1)
d = {"name": "Alice", "age": 25}
print(d["name"])       # "Alice"  — O(1) 查找
d["city"] = "Beijing"  # O(1) 插入
"age" in d             # True    — O(1) 成员检查
del d["age"]           # O(1) 删除
```

### 1.2 哈希表的底层原理

#### 哈希函数

Python 对每个对象调用 `hash()` 函数，将其转换为一个整数：

```python
print(hash("hello"))     # 一个很大的整数
print(hash(42))          # 42（小整数哈希就是自身）
print(hash((1, 2, 3)))   # 元组可哈希
# print(hash([1,2,3]))   # TypeError: 列表不可哈希！
```

**哈希表的存储结构（简化版）：**

```
哈希表数组（PyDictEntry 数组）
┌──────┬────────────────────────────────────────────┐
│ 索引  │  内容                                       │
├──────┼────────────────────────────────────────────┤
│  0   │  [空]                                       │
│  1   │  [hash: 12345] [key: "name"] [val: "Alice"]│
│  2   │  [空]                                       │
│  3   │  [hash: 67890] [key: "age" ] [val: 25]     │
│  4   │  [空]                                       │
│  5   │  [hash: 11121] [key:"city"] [val:"Beijing"]│
│  6   │  [空]                                       │
│  7   │  [空]                                       │
└──────┴────────────────────────────────────────────┘
```

**插入过程（简化）：**
1. 计算 `hash("name")` → 12345
2. 取模计算初始索引：`12345 % 8` → 1
3. 检查槽位 1 是否为空 → 是，直接填入
4. 如果槽位被占用 → **开放寻址法**：线性探测下一个槽位

**查找过程：**
1. 计算 `hash("name")` → 12345
2. 初始索引：`12345 % 8` → 1
3. 检查槽位 1 的 key 是否是 "name" → 是，返回值
4. 如果 key 不匹配 → 继续探测

> ⚠️ **为什么列表不能做字典键？**
> 因为列表是**可变（mutable）**的。如果列表能做键，修改列表内容后它的哈希值会变，导致哈希表无法找到原来的条目。Python 要求字典键必须是**可哈希（hashable）**的——即实现了 `__hash__()` 和 `__eq__()` 方法，且哈希值不变。

**可哈希类型**：int, float, str, tuple（仅当所有元素可哈希）, frozenset, None
**不可哈希类型**：list, set, dict（可变类型）

### 1.3 Python 3.7+ 的关键特性：插入有序

从 Python 3.7 开始，字典**保持插入顺序**：

```python
d = {}
d["c"] = 3
d["a"] = 1
d["b"] = 2
print(list(d.keys()))    # ['c', 'a', 'b'] — 插入顺序！
print(list(d.items()))   # [('c',3), ('a',1), ('b',2)]
```

这是 CPython 3.6（实现细节）和 3.7+（语言保证）引入的优化。底层使用**紧凑哈希表（compact dict）**，将条目按插入顺序存储在一个数组中，哈希索引另存为一个稀疏数组。

---

## 二、字典方法与操作详解

### 2.1 核心操作

```python
d = {"a": 1, "b": 2, "c": 3}

# 访问
d["a"]            # 1 — 键不存在会抛 KeyError
d.get("a")        # 1 — 安全的访问方式
d.get("x", 0)     # 0 — 键不存在返回默认值
d.setdefault("x", 100)  # 如果键不存在，设置默认值 100 并返回
                        # 如果键存在，返回已有值（不改动）

# 修改
d["a"] = 10       # 更新已有键
d["z"] = 26       # 添加新键值对

# 删除
del d["z"]        # 删除键值对（KeyError 如果键不存在）
d.pop("x")        # 删除并返回值（KeyError 如果键不存在）
d.pop("x", None)  # 安全删除，不存在返回默认值
d.popitem()       # 删除并返回 (key, value) — 从 Python 3.7 起为 LIFO
d.clear()         # 清空字典

# 合并
d1 = {"a": 1, "b": 2}
d2 = {"b": 3, "c": 4}
d1.update(d2)     # d1 变为 {"a": 1, "b": 3, "c": 4}
merged = d1 | d2  # Python 3.9+ 合并操作符，返回新字典
d1 |= d2          # Python 3.9+ 原地更新（等同于 update）

# 复制
shallow = d.copy()           # 浅拷贝
import copy
deep = copy.deepcopy(d)      # 深拷贝
```

### 2.2 遍历字典

```python
d = {"name": "Alice", "age": 25, "city": "Beijing"}

# 遍历键
for key in d:
    print(key)

for key in d.keys():
    print(key)

# 遍历值
for value in d.values():
    print(value)

# 同时遍历键和值（推荐！）
for key, value in d.items():
    print(f"{key}: {value}")

# 带索引的遍历
for idx, (key, value) in enumerate(d.items()):
    print(f"{idx}: {key} → {value}")
```

### 2.3 视图对象（Views）

`keys()`, `values()`, `items()` 返回的是**视图对象（view objects）**，不是列表：

```python
d = {"a": 1, "b": 2}
keys_view = d.keys()
print(type(keys_view))  # <class 'dict_keys'>

# 视图的特点是动态反映字典变化
d["c"] = 3
print(list(keys_view))  # ['a', 'b', 'c'] — 自动更新！

# 视图支持集合运算（keys() 和 items()）
d1 = {"a": 1, "b": 2, "c": 3}
d2 = {"b": 2, "c": 4, "d": 5}

print(d1.keys() & d2.keys())     # {'b', 'c'} — 交集
print(d1.keys() - d2.keys())     # {'a'}      — 差集
print(d1.keys() | d2.keys())     # {'a','b','c','d'} — 并集
```

---

## 三、字典推导式

### 3.1 基础语法

字典推导式（dict comprehension）是从可迭代对象构建字典的简洁方式：

```python
# 语法：{key_expr: value_expr for item in iterable if condition}

# 例 1：平方映射
squares = {x: x**2 for x in range(10)}
# {0: 0, 1: 1, 2: 4, 3: 9, 4: 16, 5: 25, 6: 36, 7: 49, 8: 64, 9: 81}

# 例 2：条件过滤
even_squares = {x: x**2 for x in range(10) if x % 2 == 0}
# {0: 0, 2: 4, 4: 16, 6: 36, 8: 64}

# 例 3：键值互换
original = {"a": 1, "b": 2, "c": 3}
swapped = {v: k for k, v in original.items()}
# {1: 'a', 2: 'b', 3: 'c'}

# 例 4：字符串长度映射
words = ["hello", "world", "python", "dict"]
len_map = {word: len(word) for word in words}
# {'hello': 5, 'world': 5, 'python': 6, 'dict': 4}
```

### 3.2 高级技巧

```python
# 枚举索引
items = ["apple", "banana", "cherry"]
indexed = {i: item for i, item in enumerate(items)}
# {0: 'apple', 1: 'banana', 2: 'cherry'}

# 嵌套推导：使用 zip 合并多个列表
names = ["Alice", "Bob", "Charlie"]
scores = [85, 92, 78]
gradebook = {name: score for name, score in zip(names, scores)}
# {'Alice': 85, 'Bob': 92, 'Charlie': 78}

# 条件嵌套：根据值分类
nums = [1, 2, 3, 4, 5, 6]
categorized = {x: ("even" if x % 2 == 0 else "odd") for x in nums}
# {1: 'odd', 2: 'even', 3: 'odd', 4: 'even', 5: 'odd', 6: 'even'}

# 矩阵转置
matrix = [[1, 2, 3], [4, 5, 6]]
transposed = {i: [row[i] for row in matrix] for i in range(3)}
# {0: [1, 4], 1: [2, 5], 2: [3, 6]}

# 分组（最常见应用之一）
students = [
    ("Alice", "A班"), ("Bob", "B班"),
    ("Charlie", "A班"), ("Diana", "B班"),
]
from collections import defaultdict
grouped = defaultdict(list)
for name, cls in students:
    grouped[cls].append(name)
# {'A班': ['Alice', 'Charlie'], 'B班': ['Bob', 'Diana']}

# 用普通字典实现分组（需要多一步判断）
grouped2 = {}
for name, cls in students:
    if cls not in grouped2:
        grouped2[cls] = []
    grouped2[cls].append(name)
```

### 3.3 与列表推导式的性能对比

```python
import timeit

# 列表推导式
numbers = list(range(1000000))

# 创建字典
start = time.time()
d = {x: x**2 for x in numbers}
print(f"字典推导式: {time.time() - start:.3f}s")

# 普通 for 循环
start = time.time()
d2 = {}
for x in numbers:
    d2[x] = x**2
print(f"普通循环: {time.time() - start:.3f}s")
# 字典推导式通常比普通循环快 10-20%
```

---

## 四、defaultdict 与 Counter

### 4.1 defaultdict — 自带默认值的字典

```python
from collections import defaultdict

# 基本用法：当键不存在时，自动调用工厂函数创建默认值

# 例 1：默认值为 0（用于计数）
counter = defaultdict(int)
words = ["a", "b", "a", "c", "b", "a"]
for word in words:
    counter[word] += 1  # 不需要先检查键是否存在！
print(dict(counter))  # {'a': 3, 'b': 2, 'c': 1}

# 例 2：默认值为空列表（用于分组）
grouped = defaultdict(list)
data = [("水果", "苹果"), ("水果", "香蕉"), ("蔬菜", "白菜")]
for category, item in data:
    grouped[category].append(item)
print(dict(grouped))
# {'水果': ['苹果', '香蕉'], '蔬菜': ['白菜']}

# 例 3：默认值为空集合（用于去重）
unique = defaultdict(set)
pairs = [("语言", "Python"), ("语言", "Java"), ("语言", "Python")]
for cat, val in pairs:
    unique[cat].add(val)
print(dict(unique))
# {'语言': {'Python', 'Java'}}

# 例 4：自定义默认值
from collections import defaultdict
def default_value():
    return {"count": 0, "total": 0.0}

stats = defaultdict(default_value)
stats["Alice"]["count"] += 1
stats["Alice"]["total"] += 85.5
print(dict(stats))
# {'Alice': {'count': 1, 'total': 85.5}}
```

### 4.2 Counter — 计数利器

```python
from collections import Counter

# 创建 Counter
c1 = Counter("abracadabra")  # 从字符串
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})

c2 = Counter(["a", "b", "a", "c"])  # 从列表
# Counter({'a': 2, 'b': 1, 'c': 1})

c3 = Counter(a=3, b=1, c=2)  # 从关键字参数
# Counter({'a': 3, 'c': 2, 'b': 1})

# 核心操作
c = Counter("abracadabra")
print(c.most_common(3))   # [('a', 5), ('b', 2), ('r', 2)]
print(c["z"])              # 0 — 不存在的键返回 0，不会 KeyError
print(list(c.elements()))  # ['a','a','a','a','a','b','b','r','r','c','d']

# 算术运算
c1 = Counter(a=3, b=1)
c2 = Counter(a=1, b=2, c=1)
print(c1 + c2)  # Counter({'a': 4, 'b': 3, 'c': 1})
print(c1 - c2)  # Counter({'a': 2}) — 只保留正数
print(c1 & c2)  # Counter({'a': 1, 'b': 1}) — 交集（取最小）
print(c1 | c2)  # Counter({'a': 3, 'b': 2, 'c': 1}) — 并集（取最大）
```

### 4.3 dict vs defaultdict vs Counter 选择指南

| 场景 | 推荐类型 | 原因 |
|------|---------|------|
| 普通键值存储 | `dict` | 最基础、最通用 |
| 计数 | `Counter` | 专为计数设计，API 丰富 |
| 分组（列表） | `defaultdict(list)` | 避免 KeyError |
| 分组（集合） | `defaultdict(set)` | 自动去重 |
| 嵌套字典 | `defaultdict(lambda: defaultdict(int))` | 深层自动创建 |
| 有序字典（旧代码） | `OrderedDict` | Python 3.7+ dict 已有序，很少需要 |

---

## 五、字典的哈希约束深入

### 5.1 什么是可哈希？

一个对象可哈希意味着：
1. 它有 `__hash__()` 方法，返回一个整数
2. 它有 `__eq__()` 方法，用于比较相等
3. 如果两个对象相等（`a == b`），它们的哈希值必须相等
4. **对象的哈希值在生命周期内不能改变**

```python
# 可哈希的自定义对象
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
    
    def __hash__(self):
        return hash((self.name, self.age))  # 用元组组合
    
    def __eq__(self, other):
        if not isinstance(other, Person):
            return False
        return self.name == other.name and self.age == other.age
    
    def __repr__(self):
        return f"Person({self.name}, {self.age})"

# 现在 Person 可以做字典键了！
registry = {
    Person("Alice", 25): "工程师",
    Person("Bob", 30): "设计师",
}
print(registry[Person("Alice", 25)])  # "工程师"
```

### 5.2 哈希碰撞与解决

当两个不同的键计算出的哈希值映射到同一个槽位时，发生**哈希碰撞**。

Python 使用**开放寻址法（open addressing）** 中的**二次探测（quadratic probing）** 来解决碰撞：

```python
# 简化的探测过程
def find_slot(keys, key):
    """在哈希表中查找 key 应处的槽位"""
    hash_val = hash(key)
    initial_index = hash_val % len(keys)
    
    index = initial_index
    perturb = hash_val
    i = 0
    
    while keys[index] is not None and keys[index] != key:
        # 二次探测：尝试下一个位置
        # CPython 实际使用更复杂的 perturb 递减策略
        i += 1
        index = (initial_index + i * i) % len(keys)
    
    return index
```

**负载因子（load factor）**：当存储的条目数超过数组容量的 2/3 时，字典会自动**扩容（resize）**，重新分配更大的数组并重新哈希所有键。

### 5.3 哈希攻击

如果大量键发生哈希碰撞，字典操作会退化为 O(n)（所有键都映射到同一个槽位，变成链表搜索）。这就是**哈希洪水攻击（hash flooding attack）** 的原理。

Python 在 3.3+ 中引入了 **PYTHONHASHSEED** 机制：每次启动解释器时，字符串和字节串的哈希值会随机化（使用随机种子），有效防御了针对固定哈希模式的洪水攻击。

---

## 六、实战：词频统计器

完整的实战项目见 `code/02-word-frequency-analyzer.py`。

词频统计是字典最经典的实战应用，涵盖了：
- 使用 `defaultdict(int)` 和 `Counter` 进行高效计数
- 字典的排序与 top-N 选取
- 文本预处理（去标点、统一大小写）
- 停用词过滤
- 词频可视化（直方图）
- 结果导出

---

## 📖 参考链接

- [Python 官方文档 — dict](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict)
- [Python 官方文档 — collections](https://docs.python.org/3/library/collections.html)
- [CPython dict 实现详解（源码注释）](https://github.com/python/cpython/blob/main/Objects/dictobject.c)
- [PEP 584 — Union Operators in dict](https://peps.python.org/pep-0584/) （Python 3.9）
- [The Mighty Dictionary — Brandon Rhodes 的 PyCon 演讲](https://www.youtube.com/watch?v=C4Kc8xzcA68)

---

## 💡 今日重点回顾

```
哈希表原理 → O(1) 查找，哈希函数 + 开放寻址
    ↓
字典的键约束 → 不可变 + 可哈希
    ↓
字典方法 → get / setdefault / update / pop
    ↓
字典推导式 → 优雅构建字典的 DSL
    ↓
defaultdict → 自动化默认值，告别 KeyError
    ↓
Counter → 专注计数，一行完成词频统计
    ↓
实战词频统计 → 从原始文本到数据分析的完整管道
```
