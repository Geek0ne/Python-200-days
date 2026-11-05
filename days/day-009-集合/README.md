# Day 009 — 集合（Set）

> "集合是数学家在 Python 中留下的礼物——用 Venn 图的直觉，写出 O(1) 的代码"

---

## 📋 今日学习目标

- [ ] 理解集合的数学基础与哈希集合的底层原理
- [ ] 掌握集合的创建、方法与基本操作
- [ ] 熟练掌握集合运算：并集、交集、差集、对称差
- [ ] 理解集合 vs 列表的性能差异及选择依据
- [ ] 掌握 frozenset 及其使用场景
- [ ] 完成实战：去重与数据清洗

---

## 一、集合的数学原理

### 1.1 概念解释

**集合（set）** 是 Python 中的一种内置数据结构，它存储的是**无序的、不重复的元素**。集合的概念直接来源于数学中的**集合论**。

```python
# 创建集合的多种方式
empty = set()                   # 空集合（不能用 {}，那是空字典）
literal = {1, 2, 3, 4, 5}      # 集合字面量
from_list = set([1, 2, 2, 3])  # 从可迭代对象创建（自动去重）→ {1, 2, 3}
from_str = set("hello")        # 从字符串创建 → {'h', 'e', 'l', 'o'}
from_range = set(range(5))     # 从 range 创建 → {0, 1, 2, 3, 4}
```

**为什么叫"集合"？**

集合（set）直接借用数学中的集合概念，Python 用这个术语来表示一个**无序且无重复元素的容器**。和数学集合一样，Python 集合关注的是"元素是否在集合中"，而不是"元素在什么位置"。

### 1.2 集合论基础

集合论是现代数学的基础，几个核心概念直接体现在 Python 集合中：

| 数学概念 | 数学符号 | Python 实现 | 说明 |
|---------|---------|-------------|------|
| 并集 | $A \cup B$ | `a \| b` 或 `a.union(b)` | 合并两个集合 |
| 交集 | $A \cap B$ | `a & b` 或 `a.intersection(b)` | 两集合共有元素 |
| 差集 | $A - B$ | `a - b` 或 `a.difference(b)` | 在 A 中但不在 B 中 |
| 对称差 | $A \triangle B$ | `a ^ b` 或 `a.symmetric_difference(b)` | 只在其中一个集合中的元素 |
| 子集 | $A \subseteq B$ | `a <= b` 或 `a.issubset(b)` | A 的所有元素都在 B 中 |
| 真子集 | $A \subset B$ | `a < b` | A 是 B 的子集且不相等 |
| 超集 | $A \supseteq B$ | `a >= b` 或 `a.issuperset(b)` | B 的所有元素都在 A 中 |
| 真超集 | $A \supset B$ | `a > b` | A 是 B 的超集且不相等 |
| 属于 | $x \in A$ | `x in a` | 元素是否在集合中 |
| 不属于 | $x \notin A$ | `x not in a` | 元素是否不在集合中 |
| 空集 | $\varnothing$ | `set()` | 不含任何元素的集合 |
| 全集 | — | 无直接对应 | 由业务逻辑自行确定 |

### 1.3 Python 集合的两个关键特性

**特性一：无序性**

集合不维护元素的顺序。这意味着你不能通过索引访问集合元素：

```python
s = {3, 1, 2}
print(s)            # {1, 2, 3} — 但实际输出顺序不可预测！
# s[0]              # TypeError: 'set' object is not subscriptable
```

**为什么无序？** 因为集合底层是哈希表（和字典的键一样），元素的位置由哈希值决定，而不是插入顺序。

**特性二：唯一性**

集合中的元素不能重复。向集合添加已存在的元素不会有任何效果：

```python
s = {1, 2, 3}
s.add(3)            # 没有任何效果
s.add(3)            # 还是没有效果
print(s)            # {1, 2, 3}
```

**为什么唯一？** 同样因为哈希表——哈希表中的每个键只能出现一次。

---

## 二、集合的底层原理：哈希集合

### 2.1 Python 集合 = 只有键的字典

Python 集合的底层实现和字典非常相似——实际上，CPython 的 `set` 和 `dict` 共享了大量的底层代码。**可以把集合理解为一个只有键（key）没有值（value）的字典**。

```
集合的哈希表结构（简化）
┌──────┬──────────────────────────────┐
│ 索引  │  内容                         │
├──────┼──────────────────────────────┤
│  0   │  [空]                         │
│  1   │  [hash: 12345] [entry: "Alice"] │
│  2   │  [空]                         │
│  3   │  [hash: 67890] [entry: "Bob"]   │
│  4   │  [空]                         │
│  5   │  [hash: 11121] [entry:"Charlie"]│
│  6   │  [空]                         │
│  7   │  [空]                         │
└──────┴──────────────────────────────┘
```

和字典一样的特性：
- **O(1) 平均查找/插入/删除**时间复杂度
- 元素必须是**可哈希（hashable）**的（不可变类型）
- 同样使用**开放寻址法**处理哈希碰撞
- 同样会在负载因子超过 2/3 时**自动扩容**
- 同样受 **PYTHONHASHSEED** 随机化保护

### 2.2 可哈希约束

和字典键一样，集合元素必须是可哈希的（不可变）：

```python
# ✅ 可哈希类型（可以做集合元素）
s1 = {1, 2, 3}                     # int
s2 = {1.5, 2.5}                    # float
s3 = {"hello", "world"}            # str
s4 = {(1, 2), (3, 4)}             # tuple（仅当元素可哈希）
s5 = {frozenset({1, 2})}           # frozenset
s6 = {None}                        # NoneType

# ❌ 不可哈希类型（不能做集合元素）
# s7 = {[1, 2], [3, 4]}           # TypeError: unhashable type: 'list'
# s8 = {{1, 2}, {3, 4}}           # TypeError: unhashable type: 'set'
# s9 = {{"a": 1}, {"b": 2}}       # TypeError: unhashable type: 'dict'
```

### 2.3 集合 vs 列表：性能对比

这是集合最重要的实战价值——**O(1) 的成员检查**。

```python
import time

# 准备数据
n = 1_000_000
my_list = list(range(n))
my_set = set(range(n))

# 成员检查 — 最坏情况（检查不在集合中的元素）
target = -1  # 不在集合中

start = time.perf_counter()
result = target in my_list  # O(n) — 从头扫描到尾
list_time = time.perf_counter() - start

start = time.perf_counter()
result = target in my_set   # O(1) — 一次哈希计算
set_time = time.perf_counter() - start

print(f"列表查找: {list_time:.6f}s")   # ~0.01s（百万级）
print(f"集合查找: {set_time:.6f}s")    # ~0.000001s（纳秒级）
print(f"集合快约 {list_time/set_time:.0f} 倍")
```

**实际输出示例（数据量 100 万）：**
```
列表查找: 0.012345s     ← 线性扫描，随数据量增大而增大
集合查找: 0.000001s     ← 常数时间，和数据量无关
集合快约 12345 倍
```

**为什么集合更快？**
- 列表：需要从头到尾逐个比较，最坏情况需要遍历整个列表
- 集合：计算哈希值 → 直接定位到桶位置 → 检查即可

### 2.4 何时用集合，何时用列表？

| 场景 | 推荐结构 | 原因 |
|------|---------|------|
| 频繁成员检查（`x in data`） | `set` | O(1) vs O(n) |
| 去重 | `set` | 天然支持 |
| 集合运算（并交差） | `set` | 内置运算符 |
| 保持插入顺序 | `list` | 集合无序 |
| 允许重复元素 | `list` | 集合去重 |
| 索引访问 | `list` | 集合不支持 |
| 元素数量很小（< 100） | 两者皆可 | 性能差异可忽略 |
| 需要切片操作 | `list` | 集合不支持 |

---

## 三、集合方法与操作详解

### 3.1 集合的创建

```python
# 字面量
s = {1, 2, 3}

# 从可迭代对象
s = set([1, 2, 3])       # 从列表
s = set("hello")         # 从字符串 → {'h', 'e', 'l', 'o'}
s = set(range(10))       # 从 range
s = set((1, 2, 3))       # 从元组

# 集合推导式（set comprehension）
s = {x**2 for x in range(10)}           # {0, 1, 4, 9, 16, 25, 36, 49, 64, 81}
s = {x for x in range(20) if x % 3 == 0}  # {0, 3, 6, 9, 12, 15, 18}
```

### 3.2 核心操作（修改集合）

```python
s = {1, 2, 3}

# 添加元素
s.add(4)            # s → {1, 2, 3, 4}
s.add(1)            # 没有效果（已存在）

# 删除元素
s.remove(3)         # 删除元素，不存在则抛出 KeyError
s.discard(10)       # 删除元素，不存在则静默忽略（推荐！）
x = s.pop()         # 删除并返回任意一个元素（集合为空则 KeyError）
s.clear()           # 清空集合 → set()

# 批量操作
s.update([5, 6, 7])  # 批量添加元素（等同于并集赋值）
s |= {8, 9}          # Python 3.9+ 语法
```

### 3.3 成员检查

```python
s = {1, 2, 3, 4, 5}

print(3 in s)       # True  — O(1)
print(10 in s)      # False — O(1)
print(3 not in s)   # False
```

### 3.4 集合运算

```python
a = {1, 2, 3, 4}
b = {3, 4, 5, 6}

# 并集
print(a | b)                    # {1, 2, 3, 4, 5, 6}
print(a.union(b))               # 同上

# 交集
print(a & b)                    # {3, 4}
print(a.intersection(b))        # 同上

# 差集
print(a - b)                    # {1, 2}（在 a 不在 b）
print(a.difference(b))          # 同上
print(b - a)                    # {5, 6}（在 b 不在 a）

# 对称差
print(a ^ b)                    # {1, 2, 5, 6}（两集合中非共有元素）
print(a.symmetric_difference(b))  # 同上
```

**Venn 图示意：**

```
       并集（Union）           交集（Intersection）
    ┌─────────────┐          ┌─────────────┐
    │  A     B    │          │  A     B    │
    │  ┌───┐      │          │  ┌───┐      │
    │  │1 2│3 4│5 6│          │  │   │3 4│   │
    │  └───┘      │          │  └───┘      │
    └─────────────┘          └─────────────┘
   (全部元素合集)          (两个集合重叠部分)

       差集（Difference）        对称差（Symmetric Diff）
    ┌─────────────┐          ┌─────────────┐
    │  A     B    │          │  A     B    │
    │  ┌───┐      │          │  ┌───┐      │
    │  │1 2│   │   │          │  │1 2│   │5 6│
    │  └───┘      │          │  └───┘      │
    └─────────────┘          └─────────────┘
   (A - B: 只在A中的)      (A ^ B: 去掉重叠部分)
```

### 3.5 关系判断

```python
a = {1, 2, 3}
b = {1, 2, 3, 4, 5}
c = {1, 2, 3}

# 子集判断
print(a <= b)      # True — a 是 b 的子集
print(a.issubset(b))

# 真子集
print(a < b)       # True — a 是 b 的真子集
print(a < c)       # False — 相等不是真子集

# 超集判断
print(b >= a)      # True — b 是 a 的超集
print(b.issuperset(a))

# 真超集
print(b > a)       # True
print(a > c)       # False

# 不相交判断
d = {10, 20}
print(a.isdisjoint(d))  # True — 没有共同元素
print(a.isdisjoint(b))  # False — 有共同元素
```

### 3.6 不可变方法与原地方法

大部分集合运算提供两个版本：

| 不可变版本 | 原地修改版本 | 说明 |
|-----------|-------------|------|
| `a.union(b)` | `a.update(b)` 或 `a \|= b` | 并集 |
| `a.intersection(b)` | `a.intersection_update(b)` 或 `a &= b` | 交集 |
| `a.difference(b)` | `a.difference_update(b)` 或 `a -= b` | 差集 |
| `a.symmetric_difference(b)` | `a.symmetric_difference_update(b)` 或 `a ^= b` | 对称差 |

```python
a = {1, 2, 3}
b = {3, 4, 5}

result = a.union(b)   # → {1, 2, 3, 4, 5}，a 不变
print(a)              # {1, 2, 3}

a.update(b)           # → a 直接被修改
print(a)              # {1, 2, 3, 4, 5}
```

### 3.7 集合的遍历

```python
s = {"apple", "banana", "cherry"}

# 遍历元素（顺序不固定）
for item in s:
    print(item)

# 带索引？不行！集合无序
# 但可以用 enumerate 加一个临时顺序
for idx, item in enumerate(s):
    print(f"{idx}: {item}")

# 排序后遍历
for item in sorted(s):
    print(item)
```

### 3.8 集合的复制

```python
s = {1, 2, 3}

shallow = s.copy()          # 浅拷贝
import copy
deep = copy.deepcopy(s)     # 深拷贝（对于集合本身，浅/深一样）
```

---

## 四、集合推导式

### 4.1 基础语法

```python
# 语法：{expression for item in iterable if condition}

# 平方值（去重）
numbers = [1, 2, 2, 3, 3, 3, 4]
squares = {x**2 for x in numbers}
print(squares)  # {16, 1, 9, 4}

# 条件过滤
even_squares = {x**2 for x in range(20) if x % 2 == 0}
# {0, 4, 16, 36, 64, 100, 144, 196, 256, 324}

# 字符串处理
words = ["Hello", "World", "Python", "Set"]
first_letters = {w[0].lower() for w in words}
print(first_letters)  # {'h', 'w', 'p', 's'}
```

### 4.2 高级用法

```python
# 从嵌套结构中提取不重复值
matrix = [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
unique = {x for row in matrix for x in row}
print(unique)  # {1, 2, 3, 4, 5}

# 过滤与转换
text = "the quick brown fox jumps over the lazy dog"
vowels = {c for c in text if c in "aeiou"}
print(vowels)  # {'e', 'i', 'o', 'u', 'a'}（去重后）

# 找出两个列表中的重复元素
list1 = [1, 2, 3, 4, 5]
list2 = [4, 5, 6, 7, 8]
duplicates = {x for x in list1 if x in list2}
print(duplicates)  # {4, 5}

# 更高效的方式（见性能对比）
duplicates = set(list1) & set(list2)
print(duplicates)  # {4, 5}
```

---

## 五、frozenset — 不可变集合

### 5.1 概念解释

**frozenset** 是集合的不可变版本。和普通 `set` 的关系，就像 `tuple` 和 `list` 的关系。

```python
# 创建 frozenset
fs = frozenset([1, 2, 3, 3, 4])
print(fs)               # frozenset({1, 2, 3, 4})
print(type(fs))         # <class 'frozenset'>

# frozenset 不可变
# fs.add(5)             # AttributeError: 'frozenset' object has no attribute 'add'
# fs.remove(1)          # AttributeError: 'frozenset' object has no attribute 'remove'

# 只读操作全部支持
print(3 in fs)          # True
print(fs | {5, 6})     # frozenset({1, 2, 3, 4, 5, 6}) — 返回新 frozenset
print(fs & {2, 3})     # frozenset({2, 3})
```

### 5.2 frozenset 的核心价值：可哈希

因为 `frozenset` 是不可变的，所以它是**可哈希的**，可以做：

1. **字典的键**
2. **集合的元素**

```python
# 作为字典的键
registry = {
    frozenset({"admin", "user"}): "内部系统",
    frozenset({"guest"}): "公共访问",
}
print(registry[frozenset({"user", "admin"})])  # "内部系统"

# 作为集合的元素（集合的集合）
permission_groups = {
    frozenset({"read"}),
    frozenset({"read", "write"}),
    frozenset({"read", "write", "execute"}),
}

# 更实际的应用：词袋模型
doc1 = frozenset("the quick brown fox".split())
doc2 = frozenset("the lazy dog".split())
doc3 = frozenset("quick fox".split())

docs = {doc1, doc2, doc3}
print(frozenset("fox quick".split()) in docs)  # True
# 注意：顺序不重要！frozenset 自动处理
```

### 5.3 frozenset vs set 选择指南

```python
# 什么时候用 frozenset？
# 1. 需要作为字典键
# 2. 需要作为集合元素
# 3. 需要保证集合不被意外修改
# 4. 在多线程环境中共享数据（天然线程安全）

# 什么时候用 set？
# 1. 需要增删改元素
# 2. 绝大多数日常场景
# 3. 性能要求不是极度苛刻时
```

---

## 六、集合实战应用模式

### 6.1 快速去重

```python
# 最经典用法：列表去重
numbers = [1, 2, 2, 3, 3, 3, 4, 4, 4, 4]
unique_numbers = list(set(numbers))
print(unique_numbers)  # [1, 2, 3, 4]

# 注意：去重后顺序会改变！
# 如果需要保持顺序，用 dict（Python 3.7+ 有序）
ordered_unique = list(dict.fromkeys(numbers))
print(ordered_unique)  # [1, 2, 3, 4]

# 按原顺序去重（手动）
seen = set()
result = []
for x in numbers:
    if x not in seen:
        seen.add(x)
        result.append(x)
print(result)  # [1, 2, 3, 4]
```

### 6.2 数据对比

```python
old_users = {"Alice", "Bob", "Charlie", "David"}
new_users = {"Bob", "David", "Eve", "Frank"}

# 新增用户（在新列表中但不在旧列表中）
added = new_users - old_users
print(f"新增用户: {added}")     # {'Eve', 'Frank'}

# 移除用户（在旧列表中但不在新列表中）
removed = old_users - new_users
print(f"移除用户: {removed}")   # {'Alice', 'Charlie'}

# 持续用户
retained = old_users & new_users
print(f"持续用户: {retained}")  # {'Bob', 'David'}
```

### 6.3 权限检查

```python
# 用户权限集合
user_permissions = {"read", "write"}
required_permissions = {"read", "write", "admin"}

# 是否有某个权限
print("read" in user_permissions)     # True

# 是否有所有需要的权限
has_all = required_permissions <= user_permissions
print(f"有全部权限: {has_all}")       # False

# 缺少哪些权限
missing = required_permissions - user_permissions
print(f"缺少权限: {missing}")         # {'admin'}

# 是否有任意权限
has_any = bool(user_permissions & required_permissions)
print(f"有任一权限: {has_any}")       # True
```

---

## 七、实战：数据清洗管道

完整的实战项目见 `code/02-data-cleaning-pipeline.py`。

数据清洗是数据科学中最基础也最耗时的环节之一。集合凭借其去重、集合运算和 O(1) 成员检查能力，在数据清洗中有着广泛的应用：

- **去重**：移除重复记录
- **数据对比**：找出新旧数据集的差异
- **异常值过滤**：在黑名单/白名单中快速检查
- **交集分析**：找出共同存在的元素
- **数据完整性检查**：验证必填字段是否缺失

---

## 💡 今日重点回顾

```
集合数学原理 → 集合论四大运算：并交差补
      ↓
哈希集合底层 → 只有键的字典，O(1) 成员检查
      ↓
集合方法 → add/remove/discard/pop/update
      ↓
集合运算符 → | & - ^ <= >= 等完整数学运算符
      ↓
集合推导式 → 像列表推导式一样优雅地构建集合
      ↓
frozenset → 不可变集合，可哈希，当字典键/集合元素
      ↓
实战数据清洗 → 去重 + 数据对比 + 异常值过滤
```

## 📖 参考链接

- [Python 官方文档 — set](https://docs.python.org/3/library/stdtypes.html#set)
- [Python 官方文档 — frozenset](https://docs.python.org/3/library/stdtypes.html#frozenset)
- [CPython set 实现源码](https://github.com/python/cpython/blob/main/Objects/setobject.c)
- [PEP 3106 — Revamping dict.keys(), .values(), .items()](https://peps.python.org/pep-3106/)
- [集合论 — Wikipedia](https://zh.wikipedia.org/wiki/%E9%9B%86%E5%90%88%E8%AE%BA)

---

## 💭 思考题

1. **为什么集合的成员检查是 O(1) 而列表是 O(n)？从底层数据结构的角度解释。**
   - 提示：想一想哈希函数的作用，以及"直接定位"vs"逐个比较"的区别

2. **如果你需要保持去重后元素的原始顺序，有哪些方法？各自的优缺点是什么？**
   - 提示：考虑 dict.fromkeys()、手动维护 seen 集合等方案

3. **frozenset 在实际开发中有什么场景是 set 无法替代的？**
   - 提示：想想嵌套结构（集合的集合）和字典键的场景

4. **在数据量很大（如 1000 万元素）的情况下，如果你需要找出两个列表的"对称差"，用集合运算和用列表推导式的性能差异有多大？为什么？**
   - 提示：算一算 O(n) 和 O(n×m) 的差异

5. **Python 的 set 为什么被设计为无序的？如果 Python 推出一个"有序集合"，它的性能会有什么样的变化？**
   - 提示：想一想哈希表的本质，以及维护顺序需要额外付出什么代价
