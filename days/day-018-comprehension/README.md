# Day 018 — 推导式（Comprehensions）

> "列表推导式不是 Python 的语法糖，它是表达力与简洁性的完美平衡"

---

## 目录

1. [推导式：初识与动机](#1-推导式初识与动机)
2. [列表推导式内部原理](#2-列表推导式内部原理)
3. [字典推导式与集合推导式](#3-字典推导式与集合推导式)
4. [嵌套推导式](#4-嵌套推导式)
5. [推导式 & 条件过滤](#5-推导式--条件过滤)
6. [列表推导式 vs 生成器表达式](#6-列表推导式-vs-生成器表达式)
7. [性能对比分析](#7-性能对比分析)
8. [常见陷阱与避坑指南](#8-常见陷阱与避坑指南)
9. [实战：数据转换流水线](#9-实战数据转换流水线)
10. [思考题](#10-思考题)

---

## 1. 推导式：初识与动机

### 1.1 从循环到推导式

假设你要创建一个包含 1–10 平方数的列表：

**手写循环——命令式风格：**

```python
squares = []
for x in range(1, 11):
    squares.append(x ** 2)
# squares → [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
```

**列表推导式——声明式风格：**

```python
squares = [x ** 2 for x in range(1, 11)]
# squares → [1, 4, 9, 16, 25, 36, 49, 64, 81, 100]
```

**区别：**

| 特性 | 手写循环 | 列表推导式 |
|------|----------|-----------|
| 代码行数 | 3–4 行 | 1 行 |
| 可读性 | 逐步执行，显式 | 声明式，接近数学 |
| 性能 | 较慢（大量字节码） | 更快（C 层优化） |
| 调试友好度 | 可加断点 | 难以断点调试 |
| 适用场景 | 复杂逻辑 | 简单映射/过滤 |

### 1.2 推导式的数学本质

列表推导式与数学中的**集合构造式**（Set-builder notation）一脉相承：

```
数学:  { x² | x ∈ [1, 10] }

Python: [x**2 for x in range(1, 11)]
```

这种**声明式风格**让你只关注"要什么"，而非"怎么要"。

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   数学集合构造式        →        Python 列表推导式        │
│                                                         │
│   { f(x) | x ∈ S }     →     [f(x) for x in S]         │
│                                                         │
│   { f(x) | x ∈ S, P(x) } →  [f(x) for x in S if P(x)]  │
│                                                         │
│    ─── 输出 ──   ── 输入 ──  ── 过滤 ──               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 列表推导式内部原理

### 2.1 语法糖还是底层优化？

列表推导式本质上是 **语法糖**，但 Python 对其做了特殊优化，性能优于手写循环。

**CPython 内部执行流程：**

```python
# 你写的代码
result = [x ** 2 for x in range(1000)]

# 近似等价的字节码语义（非实际代码）
result = []
app = result.append  # 本地化 append 方法（推导式已做此优化）
for x in range(1000):
    app(x ** 2)
```

**关键优化点：**

1. **`LIST_APPEND` 单字节码指令**：CPython 为推导式内循环专门优化，每次迭代只生成一条 `LIST_APPEND` 指令，无需 `LOAD_METHOD` + `CALL_METHOD`
2. **`append` 方法本地缓存**：推导式内部将 `result.append` 提前加载到局部变量，避免每次迭代查找方法
3. **无需显式变量管理**：推导式中的循环变量在推导式完成后仍可访问（Python 3 中推导式有自己的作用域）

### 2.2 字节码对比

```python
# 手写循环的字节码片段（简化）
LOAD_CONST       (<code object <listcomp>>)
MAKE_FUNCTION
...
FOR_ITER         16 (to 28)
STORE_FAST       x
LOAD_FAST        x
LOAD_CONST       2
BINARY_POWER
LIST_APPEND      2
JUMP_ABSOLUTE    10

# 推导式的字节码片段
LOAD_CONST       (<code object <listcomp>>)
MAKE_FUNCTION
LOAD_NAME        range
LOAD_CONST       (1000,)
CALL_FUNCTION    1
GET_ITER
CALL_FUNCTION    1
RETURN_VALUE
```

**关键差异**：推导式的循环体被编译为独立代码对象（`<listcomp>`），执行时以 C 速度迭代。

### 2.3 完整的语句级等价展开

```python
# 推导式
result = [x * 2 for x in range(5) if x % 2 == 0]

# 等价展开
result = []
for x in range(5):
    if x % 2 == 0:
        result.append(x * 2)
```

**for+if 嵌套层次一一对应：**

```python
# 两层 for + 两层 if
result = [a + b for a in [1,2] for b in [3,4] if a < 2 if b > 3]

# 等价展开
result = []
for a in [1, 2]:
    for b in [3, 4]:
        if a < 2:
            if b > 3:
                result.append(a + b)
```

> **核心原则**：推导式中的 `for` 和 `if` 按**出现顺序**从左到右嵌套，与手写循环完全一致。

---

## 3. 字典推导式与集合推导式

### 3.1 字典推导式

```python
# 语法: {key_expr: value_expr for item in iterable}
squares_dict = {x: x ** 2 for x in range(5)}
# {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# 从两个列表构建字典
keys = ['a', 'b', 'c']
values = [1, 2, 3]
d = {k: v for k, v in zip(keys, values)}
# {'a': 1, 'b': 2, 'c': 3}

# 条件过滤
even_squares = {x: x**2 for x in range(10) if x % 2 == 0}
# {0: 0, 2: 4, 4: 16, 6: 36, 8: 64}

# 键值互换
original = {'a': 1, 'b': 2, 'c': 3}
reversed_dict = {v: k for k, v in original.items()}
# {1: 'a', 2: 'b', 3: 'c'}
```

### 3.2 集合推导式

```python
# 语法: {expression for item in iterable}
unique_lengths = {len(word) for word in ['hi', 'hello', 'hey', 'howdy']}
# {2, 3, 4, 5}

# 去重
nums = [1, 2, 2, 3, 3, 3, 4]
unique_squares = {x ** 2 for x in nums}
# {1, 4, 9, 16}

# 条件过滤
evens_set = {x for x in range(20) if x > 5 and x % 2 == 0}
# {6, 8, 10, 12, 14, 16, 18}
```

### 3.3 三种推导式语法对比

```python
# 列表推导式 — 方括号 []
list_comp = [x ** 2 for x in range(5)]    # [0, 1, 4, 9, 16]

# 集合推导式 — 花括号 {}
set_comp  = {x ** 2 for x in range(5)}    # {0, 1, 16, 4, 9} (无序)

# 字典推导式 — 花括号 + 冒号 :
dict_comp = {x: x ** 2 for x in range(5)}  # {0: 0, 1: 1, 2: 4, 3: 9, 4: 16}

# 元组？没这回事！
tuple_comp = (x ** 2 for x in range(5))    # ❌ 这是生成器表达式！
```

---

## 4. 嵌套推导式

### 4.1 二维列表扁平化

```python
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

# 扁平化
flat = [num for row in matrix for num in row]
# [1, 2, 3, 4, 5, 6, 7, 8, 9]

# 等价于
flat = []
for row in matrix:
    for num in row:
        flat.append(num)
```

### 4.2 矩阵转置

```python
matrix = [[1, 2, 3], [4, 5, 6]]

# 使用嵌套推导式转置
transposed = [[row[i] for row in matrix] for i in range(3)]
# [[1, 4], [2, 5], [3, 6]]

# 等价于
transposed = []
for i in range(3):
    col = []
    for row in matrix:
        col.append(row[i])
    transposed.append(col)
```

> **可读性提示**：两层嵌套推导式尚可，三层及以上请改用普通循环或拆成独立步骤。

### 4.3 嵌套推导式执行顺序

```python
# 外层 → 内层的遍历顺序
result = [a + b for a in ['x', 'y'] for b in [1, 2]]
# 执行顺序: a='x', b=1 → a='x', b=2 → a='y', b=1 → a='y', b=2
# 结果: ['x1', 'x2', 'y1', 'y2']
```

```
嵌套推导式执行流（以扁平化为例）：

    matrix = [[1, 2], [3, 4], [5, 6]]

    外层 for row in matrix:         内层 for num in row:        append(num)
    ──────────────────────         ────────────────────       ───────────
    row = [1, 2]      ─────→       num = 1  ──────────────→      [1]
                                    num = 2  ──────────────→      [1, 2]
    row = [3, 4]      ─────→       num = 3  ──────────────→      [1, 2, 3]
                                    num = 4  ──────────────→      [1, 2, 3, 4]
    row = [5, 6]      ─────→       num = 5  ──────────────→      [1, 2, 3, 4, 5]
                                    num = 6  ──────────────→      [1, 2, 3, 4, 5, 6]
```

---

## 5. 推导式 & 条件过滤

### 5.1 基本过滤

```python
# if 过滤
evens = [x for x in range(20) if x % 2 == 0]

# 多个条件（and 关系）
filtered = [x for x in range(100) if x > 10 if x < 50 if x % 3 == 0]
# 等价于: x > 10 and x < 50 and x % 3 == 0
```

### 5.2 三元表达式 + 推导式

```python
# 在表达式部分使用三元运算符
result = ['even' if x % 2 == 0 else 'odd' for x in range(5)]
# ['even', 'odd', 'even', 'odd', 'even']

# 注意：if 在表达式（左半部分）vs if 在过滤（右半部分）
# [表达式 if 条件 else 其他  for x in ...]  ← 三元表达式（始终添加元素）
# [表达式              for x in ... if 条件]  ← 条件过滤（可选添加）
```

### 5.3 实际应用场景

```python
# 提取文件扩展名中的图片文件
files = ['cat.jpg', 'doc.pdf', 'dog.png', 'sheet.xlsx', 'bird.gif']
images = [f for f in files if f.endswith(('.jpg', '.png', '.gif'))]
# ['cat.jpg', 'dog.png', 'bird.gif']

# 从字典中过滤
scores = {'Alice': 85, 'Bob': 42, 'Charlie': 73, 'Diana': 91}
passed = {name: score for name, score in scores.items() if score >= 60}
# {'Alice': 85, 'Charlie': 73, 'Diana': 91}

# 字符串清洗
words = [' Hello ', 'WORLD', '  Python  ', ' CODE ']
cleaned = [w.strip().lower() for w in words if w.strip()]
# ['hello', 'world', 'python', 'code']
```

---

## 6. 列表推导式 vs 生成器表达式

### 6.1 核心区别

| 特性 | 列表推导式 `[...]` | 生成器表达式 `(...)` |
|------|-------------------|---------------------|
| 返回类型 | `list` | `generator` |
| 求值方式 | **急切**（立即计算全部） | **惰性**（按需逐个计算） |
| 内存占用 | O(n) — 整个列表都在内存 | O(1) — 只保存当前元素 |
| 可迭代次数 | 任意多次 | 只能迭代一次 |
| 支持索引/切片 | ✅ | ❌ |
| 有 `len()` | ✅ | ❌ |
| 适用数据量 | 小到中等 | 大到无限 |

### 6.2 何时用哪个？

```python
# ✅ 小数据量 / 需要多次访问 → 列表推导式
squares = [x ** 2 for x in range(100)]

# ✅ 大数据量 / 只需遍历一次 → 生成器表达式
total = sum(x ** 2 for x in range(10_000_000))  # 内存友好

# ✅ 作为函数参数 → 生成器表达式（省略外层括号）
total = sum(x ** 2 for x in range(1000))

# ❌ 需要索引访问 → 必须用列表
squares = [x ** 2 for x in range(100)]
print(squares[5])  # ✅ 25

# ❌ 生成器最多只可用一次
gen = (x for x in range(5))
print(list(gen))  # [0, 1, 2, 3, 4]
print(list(gen))  # []  ← 已经空了！
```

### 6.3 内存对比示意图

```
列表推导式 [x**2 for x in range(1000)]
─────────────────────────────────────
 全部元素立即创建，存入内存

 [0, 1, 4, 9, 16, 25, ... , 998001]
  ↑                            ↑
 所有 1000 个整数同时存在       ← 内存: O(n)

生成器表达式 (x**2 for x in range(1000))
─────────────────────────────────────
 不创建元素，只保存算法

 (generator object)              ← 内存: O(1)
       │
       ▼ 每次 __next__() 调用
       计算一个值 → yield → 丢弃
       │
       ▼
 下一个值... 如此重复
```

---

## 7. 性能对比分析

### 7.1 不同实现方式对比

对 `[1..N]` 中的所有偶数求平方，分别用 4 种方式实现：

```python
# 方法 1: 手写 for 循环
result = []
for x in range(N):
    if x % 2 == 0:
        result.append(x ** 2)

# 方法 2: 列表推导式
result = [x ** 2 for x in range(N) if x % 2 == 0]

# 方法 3: map + filter
result = list(map(lambda x: x**2, filter(lambda x: x % 2 == 0, range(N))))

# 方法 4: 生成器表达式 → 列表
result = list(x ** 2 for x in range(N) if x % 2 == 0)
```

**性能趋势（N = 1,000,000 典型结果）：**

| 方式 | 相对速度 | 内存 | 可读性 |
|------|---------|------|--------|
| 列表推导式 | ⚡ 最快 | O(n) | ⭐⭐⭐⭐⭐ |
| map + filter | ⚡ 接近 | O(n) | ⭐⭐ |
| 手写 for 循环 | 🐢 较慢 | O(n) | ⭐⭐⭐⭐ |
| 生成器表达式 | ⚡ 快（迭代时不一次性） | O(1) | ⭐⭐⭐⭐ |

### 7.2 为什么列表推导式更快？

1. **C 层面优化**：列表推导式在 CPython 的 `__Pyx_LookupSpecial` 机制中跳过 Python 属性查找
2. **`LIST_APPEND` 指令**：专门优化的字节码，避免了 `list.append` 方法查找和调用开销
3. **临时代码对象**：推导式体编译为独立代码对象，解释器可以更高效地执行
4. **循环变量作用域**：Python 3 中推导式有独立作用域，减少了名字查找冲突

### 7.3 什么时候推导式不合适？

```python
# ❌ 复杂逻辑 — 代码难懂
result = [process(deep_transform(item))
          for item in HUGE_DATA
          if check(validate(item))
          if another_filter(item)]

# ✅ 改用循环，拆成步骤
valid_items = [item for item in HUGE_DATA if validate(item)]
filtered = [item for item in valid_items if another_filter(item)]
result = [process(deep_transform(item)) for item in filtered]

# ❌ 有副作用（如文件写入）
[print(x) for x in data]  # 别这么做！

# ✅ 用 for 循环表达副作用
for x in data:
    print(x)
```

---

## 8. 常见陷阱与避坑指南

### 8.1 陷阱 1：推导式中的变量泄露

```python
# Python 2 问题（Python 3 已修复）
x = 'old'
squares = [x ** 2 for x in range(5)]
print(x)  # Python 2: 4  ← 泄露！ Python 3: 'old'  ← 安全
```

**Python 3 规则**：推导式中的循环变量是**局部于推导式作用域**的，不影响外部同名变量。

### 8.2 陷阱 2：列表推导式与闭包

```python
# 问题：闭包捕获的是变量引用，不是值
funcs = [lambda: x for x in range(5)]
print([f() for f in funcs])  # [4, 4, 4, 4, 4]

# 解法：使用默认参数绑定当前值
funcs = [lambda x=x: x for x in range(5)]
print([f() for f in funcs])  # [0, 1, 2, 3, 4]
```

### 8.3 陷阱 3：对生成器使用列表推导式

```python
# 生成器被消耗后不可重用
gen = (x for x in range(5))
result = [x * 2 for x in gen]  # ✅ 正常：[0, 2, 4, 6, 8]
result2 = [x * 3 for x in gen] # ❌ 空列表！gen 已耗尽
```

### 8.4 陷阱 4：列表推导式中的赋值表达式（海象运算符）

```python
# Python 3.8+: 可以在推导式中使用 :=
# ✅ 合法用法：避免重复计算
[clean_name for item in data if (clean_name := item.strip()) != '']

# ⚠️ 注意：推导式中的 := 作用域规则可能令人困惑
# 请确保你真的需要它再使用，否则还是用普通循环
```

### 8.5 陷阱 5：把推导式当"聪明"的捷径

```python
# ❌ 过度复杂
matrix = [[1, 2, 3], [4, 5, 6]]
result = [
    [matrix[j][i] for j in range(len(matrix))]
    for i in range(len(matrix[0]))
]

# ✅ 拆开更清晰
rows, cols = len(matrix), len(matrix[0])
result = []
for i in range(cols):
    new_row = []
    for j in range(rows):
        new_row.append(matrix[j][i])
    result.append(new_row)
```

---

## 9. 实战：数据转换流水线

### 9.1 数据清洗流水线

```python
raw_data = [
    '  Alice, 85, A ',
    'Bob, 92, B+',
    '  Charlie, 73, C ',
    '  Diana, , A',  # 缺失分数
    'Eve, 88, B+',
    '',  # 空行
    'Frank, 105, A+',  # 分数越界
]

# 第一步：去除空白和空行
cleaned = [line.strip() for line in raw_data if line.strip()]

# 第二步：解析 CSV
parsed = [line.split(',') for line in cleaned]

# 第三步：类型清洗
processed = []
for name, score, grade in parsed:
    name = name.strip()
    grade = grade.strip()
    if not score.strip():  # 缺失分数
        continue
    score = int(score.strip())
    if 0 <= score <= 100:  # 过滤不合理分数
        processed.append({'name': name, 'score': score, 'grade': grade})
```

### 9.2 嵌套推导式实战：矩阵运算

```python
# 矩阵加法
A = [[1, 2], [3, 4]]
B = [[5, 6], [7, 8]]
C = [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]
# [[6, 8], [10, 12]]

# 矩阵乘法（3层嵌套 — 已达可读性极限）
def matmul(A, B):
    """矩阵乘法 A(m×n) × B(n×p) = C(m×p)"""
    m, n = len(A), len(A[0])
    p = len(B[0])
    return [
        [sum(A[i][k] * B[k][j] for k in range(n)) for j in range(p)]
        for i in range(m)
    ]
```

### 9.3 实用工具函数

```python
def flatten(nested):
    """将任意嵌套列表扁平化（算一个深度）"""
    return [item for sublist in nested for item in sublist]

def unique_by_key(items, key_func):
    """按键去重"""
    seen = set()
    result = []
    for item in items:
        key = key_func(item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result

def chunked(lst, n):
    """将列表分割为 n 个一组"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]
```

---

## 10. 思考题

1. **推导式展开**：将以下推导式展开为等价的 for 循环：
   ```python
   [(x, y) for x in range(3) for y in range(3) if x != y]
   ```

2. **性能分析**：使用 `timeit` 比较 `[x for x in range(1_000_000)]` 和 `list(range(1_000_000))`，为什么后者更快？

3. **笛卡尔积**：用推导式生成集合 `{1, 2, 3}` 与字符串 `"AB"` 的笛卡尔积（所有有序对）。

4. **字典反转**：给定一个字典 `{'a': 1, 'b': 2, 'c': 3}`，用字典推导式反转键值。如果值重复怎么办？

5. **调试难点**：为什么费曼说"我能用 one-liner 写出来就别拆成三行"是错误的？推导式适合什么、不适合什么？

6. **组合变换**：给定 `words = ['hello', 'world', 'python', 'comprehension']`，用一条推导式生成所有长度为偶数的单词的大写形式。

7. **矩阵旋转**：用推导式实现矩阵顺时针旋转 90°。

---

> **下集预告：Day 019 — 高阶函数与 Lambda**
