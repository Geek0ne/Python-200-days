# Day 019 — Lambda 与函数式编程

## 📖 学习目标

- 理解 Lambda 表达式的语法、原理与作用域
- 掌握 `map()` / `filter()` / `reduce()` 的用法与内部机制
- 理解函数式编程与命令式编程的风格差异
- 掌握高阶函数的概念与实践
- 通过 Mermaid 图解理解函数式数据流

---

## 一、Lambda 表达式

### 1.1 什么是 Lambda

Lambda 表达式是一种 **匿名函数** —— 没有函数名的、单行的、立即使用的函数。

```python
# 普通函数
def add(x, y):
    return x + y

# Lambda 表达式
add = lambda x, y: x + y
```

### 1.2 语法与作用域

**语法：**

```
lambda 参数列表: 表达式
```

- 左侧：逗号分隔的参数（可为 0 个或多个）
- 右侧：单个表达式（不能含语句、赋值、return）

**作用域规则：**

```python
x = 10
f = lambda y: x + y   # x 来自外部作用域（闭包捕捉）
print(f(5))            # 15
```

> ⚠️ **Late Binding 陷阱**：Lambda 中的变量在 **调用时** 才查找，而非定义时。

```python
# ❌ 陷阱：所有函数打印 3
funcs = [lambda: i for i in range(3)]
for f in funcs:
    print(f())  # 3, 3, 3

# ✅ 修复：使用默认参数绑定当前值
funcs = [lambda i=i: i for i in range(3)]
for f in funcs:
    print(f())  # 0, 1, 2
```

### 1.3 Lambda vs 普通函数

| 特性 | 普通函数 | Lambda |
|------|---------|--------|
| 名称 | 有函数名 | 匿名 |
| 行数 | 多行 | 单行 |
| 语句支持 | 支持 | 不支持（仅表达式） |
| `return` | 显式 | 隐式 |
| 文档字符串 | 支持 | 不支持 |
| 调试友好度 | 高 | 低 |
| 适用场景 | 通用 | 简单的一次性逻辑 |

---

## 二、函数式编程核心工具

### 2.1 `map()` — 映射

**原理：** 将一个函数应用于可迭代对象的每个元素，返回迭代器。

```python
map(func, iterable, *iterables)
```

- `func`：接收元素并返回新值的函数
- 返回 `map` 对象（迭代器，惰性求值）

```python
numbers = [1, 2, 3, 4]
squared = list(map(lambda x: x ** 2, numbers))
# [1, 4, 9, 16]
```

**多迭代器：**

```python
list(map(lambda a, b: a + b, [1, 2, 3], [10, 20, 30]))
# [11, 22, 33]
```

**内部机制（简化）：**

```python
def my_map(func, iterable):
    for item in iterable:
        yield func(item)
```

### 2.2 `filter()` — 过滤

**原理：** 用函数测试每个元素，保留测试结果为 `True` 的元素。

```python
filter(func, iterable)
```

- `func`：接收元素返回布尔值
- `func=None` 时过滤掉所有假值

```python
numbers = [1, 2, 3, 4, 5, 6]
evens = list(filter(lambda x: x % 2 == 0, numbers))
# [2, 4, 6]

# 过滤假值
data = [0, 1, '', 'hello', None, [], [1]]
cleaned = list(filter(None, data))
# [1, 'hello', [1]]
```

### 2.3 `reduce()` — 归约

**原理：** 从左到右累积应用函数，将序列归约为单个值。

```python
from functools import reduce

reduce(func, iterable, initial=None)
```

- `func(a, b)` → 接收当前累积值和下一个元素
- 可选 `initial`：初始值

```python
from functools import reduce

# 求和
reduce(lambda a, b: a + b, [1, 2, 3, 4, 5])
# ((((1+2)+3)+4)+5) = 15

# 带初始值
reduce(lambda a, b: a + b, [1, 2, 3], 10)
# (((10+1)+2)+3) = 16

# 阶乘
reduce(lambda a, b: a * b, range(1, 6))
# 120
```

**内部机制：**

```python
def my_reduce(func, iterable, initial=None):
    it = iter(iterable)
    if initial is None:
        value = next(it)
    else:
        value = initial
    for item in it:
        value = func(value, item)
    return value

### 2.4 API 速查表

| 函数 | 说明 | 输入 → 输出 |
|------|------|-----------|
| `map(func, iter)` | 映射变换 | `[a,b,c] → [f(a),f(b),f(c)]` |
| `filter(func, iter)` | 条件过滤 | `[a,b,c] → [b]` (仅包含真) |
| `reduce(func, iter)` | 归约聚合 | `[a,b,c] → f(f(a,b),c)` |
| `sorted(iter, key=)` | 自定义排序 | `[a,b,c] → [c,a,b]` (按 key 排序) |
| `all(iter)` / `any(iter)` | 全真/任一真 | `[T,T,F] → False / True` |
| `zip(*iters)` | 打包为元组 | `[a,b],[x,y] → [(a,x),(b,y)]` |
| `enumerate(iter)` | 带索引枚举 | `[a,b] → [(0,a),(1,b)]` |
```

---

## 三、思考题

1. **lambda 的边界**：为什么 `lambda x: return x + 1` 是语法错误？哪些场景适合用 lambda，哪些场景应该老老实实写 `def`？

**参考答案**

lambda 的语法是 `lambda 参数列表: 表达式`，右侧只允许一个**表达式**（能算出值的东西），不允许**语句**（`return`、赋值、`for`、`raise` 等）。`return` 是语句，所以直接语法报错；lambda 会隐式把表达式的值作为返回值，不需要也不能写 `return`。需要分支时用条件表达式即可：`lambda x: "偶" if x % 2 == 0 else "奇"`。

适合 lambda 的场景：**一次性、够短、就地使用**的逻辑，比如 `sorted(students, key=lambda s: s.score)`、`map(lambda x: x * 2, nums)`、`defaultdict(lambda: 0)`。

应该用 `def` 的场景：逻辑超过一行、需要复用、需要文档字符串或类型注解、需要调试。lambda 的 `__name__` 永远是 `<lambda>`，报错栈里看不出是哪段逻辑；具名函数可读性和可测试性都更好。

💡 提示：lambda 也是完整的函数对象，能赋值、能当参数、能被返回——这正是**高阶函数**（接收函数或返回函数的函数）的基础。但按 PEP 8 的建议，别用 `f = lambda x: ...` 长期代替 `def f(x): ...`。

2. **Late Binding 陷阱（代码）**：`funcs = [lambda: i for i in range(3)]`，依次调用这三个函数会输出什么？为什么？请给出两种修复方式。

**参考答案**

```python
# ❌ 陷阱：lambda 里的 i 是「调用时」才去外层查找
funcs = [lambda: i for i in range(3)]
print([f() for f in funcs])          # [2, 2, 2]

# ✅ 修复一：用默认参数在「定义时」把当前值固定下来
funcs = [lambda i=i: i for i in range(3)]
print([f() for f in funcs])          # [0, 1, 2]

# ✅ 修复二：工厂函数，每次调用产生一个独立闭包
def make(n):
    return lambda: n

funcs = [make(i) for i in range(3)]
print([f() for f in funcs])          # [0, 1, 2]
```

预期输出：

```
[2, 2, 2]
[0, 1, 2]
[0, 1, 2]
```

lambda 里的自由变量 `i` 不是「定义时的快照」，而是**对外层作用域中那个变量的引用**（闭包）。三个 lambda 引用的是同一个 `i`，循环结束后 `i` 停在最后一个值，于是三次调用都返回它——这就是 late binding（延迟绑定）。

修复一利用「**默认参数在定义时求值**」这条规则：`lambda i=i: i` 把当时的 `i` 存进函数自己的默认值里，与外层变量脱钩。修复二用工厂函数 `make(n)`，每次调用都新建一个作用域，`n` 各自独立，天然没有共享问题。

⚠️ 注意：`range(3)` 的最后一个值是 **2**，所以陷阱版输出 `[2, 2, 2]`（本日 1.2 小节写成 3 是笔误，现象一致：所有函数都返回循环结束后的同一个值）。另外列表推导式在 Python 3 中拥有独立作用域，循环变量不会泄漏到外层。

3. **map / filter / reduce 管道（代码）**：把 `[1, 2, 3, 4, 5, 6]` 中的偶数取平方后求和，用这三个函数串成一条管道。同时说明 `map`/`filter` 的返回值类型、「惰性求值」的含义，以及 `reduce` 的初始值为什么重要。

**参考答案**

```python
from functools import reduce

nums = [1, 2, 3, 4, 5, 6]

# map/filter 返回迭代器：惰性求值，不消费就还没算
squared = map(lambda x: x ** 2, nums)
print(type(squared).__name__)        # map
print(list(squared))                 # [1, 4, 9, 16, 25, 36]
print(list(squared))                 # [] —— 迭代器只能消费一次

# 组合管道：过滤偶数 → 平方 → 求和
total = reduce(lambda a, b: a + b,
               map(lambda x: x ** 2,
                   filter(lambda x: x % 2 == 0, nums)),
               0)                    # 给初始值 0，空序列也安全
print(total)                         # 4 + 16 + 36 = 56

# 等价的推导式写法（更易读，日常首选）
print(sum(x ** 2 for x in nums if x % 2 == 0))   # 56

# reduce 不给初始值又遇到空序列 → TypeError
try:
    reduce(lambda a, b: a + b, [])
except TypeError as e:
    print("报错:", e)
```

预期输出：

```
map
[1, 4, 9, 16, 25, 36]
[]
56
56
报错: reduce() of empty iterable with no initial value
```

`map` 和 `filter` 返回的是**迭代器**而不是列表：它们只记录「要做什么」，直到你去遍历（`list()`、`for`、`sum()`）才逐个计算，这叫惰性求值，好处是处理大数据时不必一次性生成全部结果。代价是**只能消费一次**，第二次 `list(squared)` 得到空列表——需要反复用就先转成 `list`。

`reduce(func, iterable, initial)` 从左到右把累积值和下一个元素喂给 `func`。给了 `initial`，它就是累积起点；不给，就用序列第一个元素当起点，因此**空序列会抛 TypeError**。求和、求积这类操作永远建议显式给初始值（`0` 或 `1`）。

💡 提示：Python 3 把 `reduce` 移到了 `functools`，需要 `from functools import reduce`。日常代码里「过滤 + 变换 + 聚合」用推导式配 `sum()` 通常比三层嵌套的 `reduce/map/filter` 更好读，函数式工具更适合配合已有函数（如 `map(str.upper, words)`）使用。
