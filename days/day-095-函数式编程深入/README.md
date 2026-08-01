# Day 095 — 函数式编程深入

> **functools 模块详解 | 惰性求值与柯里化 | 不可变数据结构 | 函数式数据处理管道**

---

## 📋 今日目标

1. 深入掌握 functools 模块的高级用法
2. 理解惰性求值与柯里化概念
3. 学习不可变数据结构
4. 实战：构建函数式数据处理管道

---

## 1. functools 模块详解

### 1.1 reduce — 归约操作

```python
from functools import reduce

# reduce 将二元函数应用于序列，累积结果
# reduce(function, iterable[, initializer])

# 求和
numbers = [1, 2, 3, 4, 5]
result = reduce(lambda acc, x: acc + x, numbers)
print(result)  # 15

# 等价于
result = reduce(lambda acc, x: acc + x, numbers, 0)

# 找最大值
max_val = reduce(lambda a, b: a if a > b else b, numbers)

# 扁平化嵌套列表
nested = [[1, 2], [3, 4], [5, 6]]
flat = reduce(lambda acc, x: acc + x, nested, [])
print(flat)  # [1, 2, 3, 4, 5, 6]

# 字符合并
words = ["Hello", " ", "World", "!"]
sentence = reduce(lambda acc, w: acc + w, words)
print(sentence)  # "Hello World!"
```

### 1.2 partial — 偏函数

```python
from functools import partial

# partial 固定函数的部分参数，生成新函数

def power(base, exponent):
    return base ** exponent

# 创建常用幂函数
square = partial(power, exponent=2)
cube = partial(power, exponent=3)

print(square(5))  # 25
print(cube(5))    # 125

# 实际应用：简化 API 调用
def api_request(url, method="GET", timeout=30, headers=None):
    print(f"{method} {url} (timeout={timeout})")
    return {"url": url, "method": method}

# 创建常用配置的请求函数
get_request = partial(api_request, method="GET", timeout=10)
post_request = partial(api_request, method="POST", timeout=30)

get_request("https://api.example.com/users")
post_request("https://api.example.com/users")

# 排序偏函数
from operator import itemgetter

users = [
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25},
    {"name": "Charlie", "age": 35},
]

sort_by_age = sorted(users, key=itemgetter("age"))
sort_by_name = sorted(users, key=itemgetter("name"))
```

### 1.3 lru_cache — 函数缓存

```python
from functools import lru_cache
import time

# lru_cache 缓存函数调用结果，避免重复计算

@lru_cache(maxsize=128)
def fibonacci(n):
    """计算斐波那契数列（带缓存）"""
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# 无缓存版本（非常慢）
def fib_no_cache(n):
    if n < 2:
        return n
    return fib_no_cache(n-1) + fib_no_cache(n-2)

# 性能对比
start = time.time()
result = fibonacci(100)
cached_time = time.time() - start
print(f"fib(100) = {result}")
print(f"有缓存: {cached_time:.6f}s")

# 查看缓存统计
print(f"缓存命中: {fibonacci.cache_info()}")

# 清除缓存
fibonacci.cache_clear()

# 注意：参数必须是可哈希的
@lru_cache(maxsize=None)
def process_data(key, value):
    return f"{key}: {value}"

# ✅ 可以缓存
process_data("name", "Alice")

# ❌ 不能缓存（列表不可哈希）
# process_data("data", [1, 2, 3])
```

### 1.4 singledispatch — 单分派泛型函数

```python
from functools import singledispatch

# singledispatch 根据第一个参数的类型选择不同的实现

@singledispatch
def process(value):
    raise NotImplementedError(f"不支持的类型: {type(value)}")

@process.register(int)
def _(value):
    return f"处理整数: {value * 2}"

@process.register(str)
def _(value):
    return f"处理字符串: {value.upper()}"

@process.register(list)
def _(value):
    return f"处理列表: {len(value)} 个元素"

@process.register(dict)
def _(value):
    return f"处理字典: {list(value.keys())}"

# 使用
print(process(42))           # 处理整数: 84
print(process("hello"))      # 处理字符串: HELLO
print(process([1, 2, 3]))    # 处理列表: 3 个元素
print(process({"a": 1}))     # 处理字典: ['a']
```

### 1.5 total_ordering — 自动比较方法

```python
from functools import total_ordering

@total_ordering
class Money:
    """只需要定义 __eq__ 和一个比较方法，自动获得其他比较方法"""
    
    def __init__(self, amount, currency="CNY"):
        self.amount = amount
        self.currency = currency
    
    def __eq__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency
    
    def __lt__(self, other):
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount < other.amount
    
    def __repr__(self):
        return f"Money({self.amount}, '{self.currency}')"

# 自动获得 __le__, __gt__, __ge__
m1 = Money(100)
m2 = Money(200)
print(m1 < m2)   # True
print(m1 > m2)   # False
print(m1 <= m2)  # True
print(m1 >= m2)  # False
```

---

## 2. 柯里化与部分应用

### 2.1 什么是柯里化？

柯里化（Currying）是将多参数函数转换为一系列单参数函数的技术。

```
普通函数: f(a, b, c) → result

柯里化后: f(a)(b)(c) → result

实际应用:
  log("ERROR")("数据库连接失败")("timeout=30s")
  → 每次只传一个参数，返回新函数
```

### 2.2 手动实现柯里化

```python
def curry(func):
    """将多参数函数转换为柯里化版本"""
    import inspect
    
    # 获取函数参数数量
    params = inspect.signature(func).parameters
    num_params = len(params)
    
    def curried(*args, **kwargs):
        if len(args) + len(kwargs) >= num_params:
            # 参数足够，直接调用
            return func(*args, **kwargs)
        else:
            # 参数不够，返回新函数继续接收
            def wrapper(*more_args, **more_kwargs):
                all_args = args + more_args
                all_kwargs = {**kwargs, **more_kwargs}
                return curried(*all_args, **all_kwargs)
            return wrapper
    
    return curried

# 使用
@curry
def add(a, b, c):
    return a + b + c

# 可以逐步调用
print(add(1)(2)(3))      # 6
print(add(1, 2)(3))      # 6
print(add(1)(2, 3))      # 6
print(add(1, 2, 3))      # 6

# 实际应用：创建专用函数
@curry
def multiply(a, b):
    return a * b

double = multiply(2)      # 双倍
triple = multiply(3)      # 三倍

print(double(5))  # 10
print(triple(5))  # 15
```

### 2.3 实用的柯里化技巧

```python
from functools import partial

# 方法1: 使用 partial（更简单）
def log(level, module, message):
    print(f"[{level}] [{module}] {message}")

# 创建专用日志函数
error_log = partial(log, "ERROR")
db_error = partial(error_log, "Database")

db_error("连接超时")      # [ERROR] [Database] 连接超时
db_error("查询失败")      # [ERROR] [Database] 查询失败

# 方法2: 使用闭包
def make_logger(level, module):
    def logger(message):
        print(f"[{level}] [{module}] {message}")
    return logger

error_db = make_logger("ERROR", "Database")
error_db("连接超时")

# 方法3: 使用装饰器
def auto_curry(func):
    """自动柯里化装饰器"""
    import inspect
    params = list(inspect.signature(func).parameters.keys())
    
    def curried(*args, **kwargs):
        bound = {}
        for i, arg in enumerate(args):
            bound[params[i]] = arg
        bound.update(kwargs)
        
        missing = [p for p in params if p not in bound]
        if not missing:
            return func(**bound)
        
        def wrapper(*more_args, **more_kwargs):
            new_bound = dict(bound)
            for i, arg in enumerate(more_args):
                new_bound[missing[i]] = arg
            new_bound.update(more_kwargs)
            return curried(**new_bound)
        
        return wrapper
    
    return curried
```

---

## 3. 不可变数据结构

### 3.1 为什么需要不可变性？

```
可变数据的问题:

data = [1, 2, 3]
other = data
data.append(4)  # other 也变了！

不可变数据:

data = (1, 2, 3)  # 元组
other = data
# data.append(4)  # AttributeError

优点:
  - 线程安全（无需加锁）
  - 可作为字典键/集合元素
  - 更容易推理和调试
  - 函数式编程的核心概念
```

### 3.2 Python 内置不可变类型

```python
# 不可变类型
immutable_types = {
    "int": 42,
    "float": 3.14,
    "str": "hello",
    "tuple": (1, 2, 3),
    "frozenset": frozenset([1, 2, 3]),
    "bytes": b"hello",
    "NoneType": None,
    "bool": True,
}

# 可变类型
mutable_types = {
    "list": [1, 2, 3],
    "dict": {"a": 1},
    "set": {1, 2, 3},
    "bytearray": bytearray(b"hello"),
}

# frozenset 示例
fs1 = frozenset([1, 2, 3])
fs2 = frozenset([2, 3, 4])

print(fs1 & fs2)   # frozenset({2, 3}) 交集
print(fs1 | fs2)   # frozenset({1, 2, 3, 4}) 并集
print(fs1 - fs2)   # frozenset({1}) 差集

# 可以作为字典键
cache = {}
cache[frozenset([1, 2])] = "cached value"
```

### 3.3 namedtuple — 命名元组

```python
from collections import namedtuple

# 创建命名元组类型
Point = namedtuple('Point', ['x', 'y'])
Color = namedtuple('Color', ['r', 'g', 'b', 'alpha'], defaults=[255])

# 使用
p = Point(10, 20)
print(p.x, p.y)      # 10 20
print(p[0], p[1])     # 10 20 (支持索引)

red = Color(255, 0, 0)
print(red)            # Color(r=255, g=0, b=0, alpha=255)

# 替换字段（返回新对象）
p2 = p._replace(x=50)
print(p2)             # Point(x=50, y=20)
print(p)              # Point(x=10, y=20) 原对象不变

# 转换为字典
d = p._asdict()
print(d)              # {'x': 10, 'y': 20}

# 实际应用：返回多个值
def get_user_info(user_id):
    """返回用户信息（不可变）"""
    User = namedtuple('User', ['id', 'name', 'email', 'is_active'])
    return User(user_id, "Alice", "alice@example.com", True)

user = get_user_info(1)
print(user.name)      # Alice

# Typed namedtuple (Python 3.6+)
from typing import NamedTuple

class Point(NamedTuple):
    x: float
    y: float
    label: str = "origin"

p = Point(1.0, 2.0)
print(p)  # Point(x=1.0, y=2.0, label='origin')
```

---

## 4. 函数式数据处理管道

### 4.1 管道模式

```python
from functools import reduce

# 管道：将数据流经一系列函数处理

def pipe(*functions):
    """创建数据处理管道"""
    def pipeline(data):
        return reduce(lambda acc, f: f(acc), functions, data)
    return pipeline

# 使用
process = pipe(
    str.strip,                    # 去除空白
    str.lower,                    # 转小写
    lambda s: s.replace(" ", "_"),  # 替换空格
    lambda s: f"[{s}]",           # 添加装饰
)

result = process("  Hello World  ")
print(result)  # [hello_world]

# 实际应用：数据清洗管道
clean_data = pipe(
    lambda x: x.strip(),
    lambda x: x.lower(),
    lambda x: x.replace("-", "_"),
    lambda x: x.replace(" ", "_"),
)

print(clean_data("  User-Name  "))  # user_name
```

### 4.2 函数组合

```python
def compose(*functions):
    """函数组合：从右到左执行"""
    def composed(x):
        result = x
        for f in reversed(functions):
            result = f(result)
        return result
    return composed

def pipe_forward(*functions):
    """管道组合：从左到右执行"""
    def composed(x):
        result = x
        for f in functions:
            result = f(result)
        return result
    return composed

# 示例
import math

# 从右到左组合
process = compose(
    math.sqrt,        # 3. sqrt
    lambda x: x + 1,  # 2. +1
    lambda x: x * 2,  # 1. *2
)

print(process(4))  # sqrt(4*2 + 1) = sqrt(9) = 3

# 从左到右管道
process = pipe_forward(
    lambda x: x * 2,  # 1. *2
    lambda x: x + 1,  # 2. +1
    math.sqrt,         # 3. sqrt
)

print(process(4))  # sqrt(4*2 + 1) = sqrt(9) = 3
```

### 4.3 实战：日志分析管道

```python
from functools import reduce
from collections import Counter
from datetime import datetime

# 模拟日志数据
raw_logs = [
    "2024-01-15 10:30:15 ERROR Database connection failed",
    "2024-01-15 10:30:16 INFO Request processed",
    "2024-01-15 10:30:17 WARNING Slow query detected",
    "2024-01-15 10:30:18 ERROR Timeout exceeded",
    "2024-01-15 10:30:19 INFO Request processed",
    "2024-01-15 10:30:20 ERROR Database connection failed",
    "2024-01-15 10:30:21 INFO Request processed",
    "2024-01-15 10:30:22 WARNING Memory usage high",
]

# 定义处理函数
def parse_log(log):
    """解析日志行"""
    parts = log.split(" ", 3)
    return {
        "date": parts[0],
        "time": parts[1],
        "level": parts[2],
        "message": parts[3],
    }

def filter_by_level(level):
    """按级别过滤"""
    return lambda logs: [l for l in logs if l["level"] == level]

def count_by_level(logs):
    """按级别统计"""
    return Counter(l["level"] for l in logs)

def extract_errors(logs):
    """提取错误信息"""
    return [l["message"] for l in logs if l["level"] == "ERROR"]

# 管道组合
analyze_errors = pipe_forward(
    list,                              # 转为列表
    filter_by_level("ERROR"),          # 过滤 ERROR
    extract_errors,                    # 提取错误信息
    Counter,                           # 统计
    dict,                              # 转为字典
)

result = analyze_errors(raw_logs)
print("错误统计:", result)
# {'Database connection failed': 2, 'Timeout exceeded': 1}

# 完整分析管道
full_analysis = pipe_forward(
    list,
    lambda logs: {
        "total": len(logs),
        "errors": len(filter_by_level("ERROR")(logs)),
        "warnings": len(filter_by_level("WARNING")(logs)),
        "error_messages": extract_errors(filter_by_level("ERROR")(logs)),
    }
)

analysis = full_analysis(raw_logs)
print(f"总日志: {analysis['total']}")
print(f"错误数: {analysis['errors']}")
print(f"警告数: {analysis['warnings']}")
```

---

## 5. 思考题

1. **`lru_cache` 和手动实现的字典缓存有什么区别？** 提示：考虑线程安全、LRU 淘汰、内存管理
2. **柯里化和偏函数（partial）有什么区别？什么时候用哪个？**
3. **不可变数据结构在并发编程中有什么优势？** 提示：考虑锁、竞态条件
4. **如何将函数式管道与异步编程结合？** 提示：考虑 async 函数的组合
5. **Python 的 `map/filter/reduce` 和列表推导式哪个更好？为什么？**

---

## 📚 扩展阅读

- [functools 官方文档](https://docs.python.org/3/library/functools.html)
- [函数式编程 in Python (PyCon Talk)](https://www.youtube.com/watch?v=3XFX4mAU7WQ)
- [Pyrsistent - 不可变数据结构库](https://github.com/tobgu/pyrsistent)
- [Toolz - 函数式编程工具库](https://toolz.readthedocs.io/)
