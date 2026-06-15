# Day 019 — Lambda 与函数式编程 🧪

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
