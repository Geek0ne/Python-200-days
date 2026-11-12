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

**参考答案**

两者本质都是「参数 → 结果」的查表，但 `lru_cache` 把四件麻烦事替你做好了：

- **LRU 淘汰与内存上限**：`maxsize=128` 保证最多存 128 条，超出时淘汰「最久未使用」（Least Recently Used）的那条；手写 dict 默认无限增长，长跑服务会慢慢吃光内存。`maxsize=None` 才是无上限。
- **线程安全**：`lru_cache` 的 C 实现内部带锁，多线程同时调用不会把缓存结构写坏；手写 dict 在 CPython 里靠 GIL 侥幸不出错，但「先查→再算→再写」不是原子的，仍会重复计算，在自由线程构建（3.13+ 的 no-GIL）下更危险。
- **参数规范化**：它按「位置参数 + 关键字参数」生成键，`f(1, b=2)` 和 `f(1, 2)` 命中同一条；手写 dict 得自己拼键，很容易漏掉这种情况。参数必须可哈希，传 list/dict 会 `TypeError`。
- **可观测与可清理**：自带 `cache_info()`（hits/misses/maxsize/currsize）和 `cache_clear()`，方便调优和测试隔离；这些手写版本都得自己加。

此外 `lru_cache` 用 `update_wrapper` 保留了原函数的 `__name__`/`__doc__`，并暴露 `__wrapped__` 方便拿到未装饰的版本；3.9+ 还可以直接写 `@cache`（等价于 `maxsize=None`）。

小例子：给递归斐波那契加 `@lru_cache(maxsize=None)`，复杂度从指数级降到线性级；手写 dict 也能做到，但淘汰、并发、统计都要自己实现。

⚠️ 注意：`lru_cache` 会**强引用**参数和返回值，装饰实例方法时连 `self` 一起留住，导致对象无法回收——这类场景改用 `weakref` 或把缓存挂在实例上。另外它只适合**纯函数**，有副作用或结果随时间变化的函数不能缓存。

2. **柯里化和偏函数（partial）有什么区别？什么时候用哪个？**

**参考答案**

**偏函数 `partial`** 是「预填参数」：一次性固定若干参数（位置前缀或任意关键字），得到参数更少的新函数；调用时若还缺参数，直接 `TypeError`。

**柯里化 `curry`** 是「改造成单参数函数链」：`f(a, b, c)` 变成 `f(a)(b)(c)`，每传一个参数就返回一个「还在等剩下参数」的新函数，凑齐才真正执行。

选型要点：

- 想固定配置、简化调用（`partial(api_request, method="GET", timeout=10)`）→ 用 `partial`：标准库自带、开销小、可读性好，是 Python 里的首选。
- 想做「逐步特化」的函数工厂，或把函数喂给只接受单参数的高阶函数（`map(double, xs)`）→ 柯里化更自然。
- `partial` 能用关键字固定**任意位置**的参数，柯里化通常只能按顺序固定前缀；反过来柯里化可以无限细分，`partial` 一次就定型。
- Python 没有内置 curry，要自己写装饰器（用 `inspect.signature` 数参数个数），对 `*args`、默认值、关键字参数的处理很容易出 bug——这也是实践中大家更爱 `partial` 的原因。

下面这份代码把两者的行为差异跑出来对比：

```python
from functools import partial
import inspect


def log(level, module, message):
    """普通三参数函数"""
    return f"[{level}] [{module}] {message}"


def curry(func):
    """把多参数函数变成可以「一次传一个」的柯里化版本"""
    n = len(inspect.signature(func).parameters)   # 一共需要几个参数

    def curried(*args):
        if len(args) >= n:                        # 参数够了，真正执行
            return func(*args)
        return lambda *more: curried(*(args + more))  # 不够就继续收集

    return curried


c_log = curry(log)

# 柯里化：每一步返回「还差参数」的新函数，可以任意细分
error = c_log("ERROR")            # 还差 2 个
db_error = error("Database")      # 还差 1 个
print("柯里化逐步调用 :", db_error("连接超时"))
print("柯里化一次给全 :", c_log("INFO")("API")("ok"))
print("柯里化混合传参 :", c_log("WARN", "Cache")("命中率低"))

# partial：一次性固定前缀参数（或关键字参数），剩下的按普通方式传
p_log = partial(log, "ERROR", "Database")
print("partial 固定前缀:", p_log("连接超时"))
print("partial 关键字  :", partial(log, message="连接超时")("ERROR", "Database"))

# 关键差异：partial 只是「预填参数」，不会自动继续等待
p = partial(log, "ERROR")
try:
    p("Database")                 # 只有 2 个参数，还差 message
except TypeError as e:
    print("partial 缺参报错:", e)

# 柯里化版本同样只给 2 个参数时，返回的是函数而不是报错
print("柯里化缺参返回 :", callable(c_log("ERROR")("Database")))
```

运行输出（已验证）：

```
柯里化逐步调用 : [ERROR] [Database] 连接超时
柯里化一次给全 : [INFO] [API] ok
柯里化混合传参 : [WARN] [Cache] 命中率低
partial 固定前缀: [ERROR] [Database] 连接超时
partial 关键字  : [ERROR] [Database] 连接超时
partial 缺参报错: log() missing 1 required positional argument: 'message'
柯里化缺参返回 : True
```

最后两行是核心区别：同样只给两个参数，`partial` 立刻报错，柯里化则返回一个可继续调用的函数。另外注意 `partial(log, message=...)` 能用关键字固定**最后一个**参数，这是纯位置式柯里化做不到的。

💡 提示：`partial` 返回的是 `functools.partial` 对象而非函数，它没有 `__name__`，也不是描述符（放到类属性上不会自动绑定 `self`）。需要「像普通函数一样」时，用闭包或 `functools.wraps` 包一层。

3. **不可变数据结构在并发编程中有什么优势？** 提示：考虑锁、竞态条件

**参考答案**

核心优势是**没有共享可变状态，就没有竞态条件**。竞态条件（race condition）指结果依赖线程执行的先后顺序：两个线程同时 `count += 1`，各自读到旧值再写回，就少加了一次。不可变对象根本无法被「写回」，这类 bug 从源头消失。

具体好处：

- **免锁**：读不可变数据不用加锁，省掉锁竞争、死锁风险和加解锁开销，只读场景可以直接多线程/多进程共享。
- **安全发布**：把 tuple / frozenset / NamedTuple 交给别的线程，不用担心对方偷偷改内容，也不必做防御性拷贝。
- **可哈希**：不可变才能当 dict 键、set 元素、`lru_cache` 的参数，缓存和去重才成立。
- **易推理、可重放**：管道里每一步都返回新对象，出错时能定位到具体哪一步，也便于实现撤销/回滚。

小例子：配置对象用 `NamedTuple` 或 `@dataclass(frozen=True)`，10 个线程同时读它完全安全；若用 dict，某个线程写一句 `cfg["timeout"] = 5` 就会影响所有人。

⚠️ 注意两点：一是**不可变要「深」**——tuple 里装 list，列表照样能被改，`([1, 2],)` 并非真正不可变；二是**不可变不等于原子**，`self.config = new_config` 这种「读-改-写」整体仍可能丢更新，需要锁或队列来串行化。另外每次修改都新建对象，高频更新会有 GC 压力，这时可考虑 `pyrsistent` 这类持久化数据结构（结构共享，只复制改动路径）。

4. **如何将函数式管道与异步编程结合？** 提示：考虑 async 函数的组合

**参考答案**

同步管道 `pipe(f, g, h)` 的本质是 `h(g(f(x)))`；异步版只需把「调用」换成「await 调用」，组合子本身几乎不用改：

```python
import asyncio


def async_pipe(*funcs):
    """把若干 async 函数组合成管道：前一个的返回值是后一个的入参"""
    async def pipeline(data):
        for f in funcs:
            data = await f(data)      # 逐个 await，保证顺序
        return data
    return pipeline


# ---- 三个异步处理步骤（用 sleep 模拟 I/O）----
async def fetch(user_id):
    await asyncio.sleep(0.01)         # 模拟查数据库
    return {"id": user_id, "name": f"  User{user_id}  ", "score": str(60 + user_id * 10)}


async def clean(user):
    await asyncio.sleep(0.01)         # 模拟调远程校验服务
    # 返回新字典而不是原地修改，保持「不可变」风格，并发复用才安全
    return {**user, "name": user["name"].strip().lower()}


async def enrich(user):
    await asyncio.sleep(0.01)         # 模拟调风控接口
    score = int(user["score"])
    return {**user, "score": score, "passed": score >= 60}


process = async_pipe(fetch, clean, enrich)


async def main():
    # 单个数据走管道
    print("单个结果:", await process(1))

    # 多个数据「并发」走同一条管道：管道只是函数组合，可安全复用
    results = await asyncio.gather(*(process(i) for i in (1, 2, 3)))
    print("并发结果:", [r["name"] for r in results])


asyncio.run(main())
```

运行输出（已验证）：

```
单个结果: {'id': 1, 'name': 'user1', 'score': 70, 'passed': True}
并发结果: ['user1', 'user2', 'user3']
```

要点解释：

- **组合子是同步的，被组合的函数是异步的**。`async_pipe` 本身是普通函数，返回一个 `async def pipeline`。千万别写成 `reduce(lambda acc, f: f(acc), funcs, data)`——那样得到的是 coroutine 对象而非结果，会触发「coroutine was never awaited」警告。
- **顺序 vs 并发**：同一条数据流经各步骤必须串行 `await`（后一步依赖前一步）；不同数据之间用 `asyncio.gather` 并发，这才是异步管道的收益所在。
- **保持纯函数风格**：每步返回新对象（`{**user, ...}`）而不是原地改，管道就能被多个协程安全复用，正好呼应第 3 题的不可变性。
- **流式处理**：数据量很大时把步骤写成异步生成器（`async def` + `yield`），用 `async for` 串起来，边读边处理，内存占用恒定。

⚠️ 注意：`asyncio.gather` 的结果按**传入顺序**排列（不是完成顺序）；某步抛异常时其它任务默认不会被取消，需要 `return_exceptions=True`，或用 Python 3.11+ 的 `asyncio.TaskGroup` 统一处理。CPU 密集步骤放进管道会阻塞事件循环，要用 `await asyncio.to_thread(...)` 挪出去。

5. **Python 的 `map/filter/reduce` 和列表推导式哪个更好？为什么？**

**参考答案**

结论：**日常业务代码优先用推导式**；`map/filter` 在特定场景更优；`reduce` 大多数时候不如专用内置函数或显式循环。

- **可读性**：`[x * 2 for x in xs if x > 0]` 一眼看清「过滤 + 变换」；`list(map(lambda x: x * 2, filter(lambda x: x > 0, xs)))` 嵌了两层 lambda，阅读顺序还是反的。Python 3 已把 `reduce` 从内置函数移到 `functools`，也体现了官方对这种风格的态度。
- **性能**：当映射函数是**已存在的内置/C 函数**时 `map` 更快，因为省掉了每个元素的 Python 字节码开销，例如 `list(map(str, range(1000)))` 通常快于 `[str(x) for x in range(1000)]`（具体倍数因机器/版本而异）；但只要用了 `lambda`，`map` 反而更慢，因为多了一次函数调用。
- **惰性**：Python 3 的 `map/filter` 返回迭代器，处理大文件或无限序列时不占内存，这点与生成器表达式 `(x * 2 for x in xs)` 等价；而 `[...]` 推导式会一次性建好整个列表。
- **表达力**：推导式支持多重 for、条件、解包、嵌套，`map/filter` 做不到；多参数 `map` 会以最短序列为准，容易埋下静默截断的坑。
- **reduce**：`reduce(operator.add, xs)` 不如 `sum(xs)` 直观。它适合「自定义二元累积」，比如合并区间、串联管道；能用 `sum/any/all/max/min/"".join` 就别写 reduce。

小例子：`sum(map(len, words))` 比 `sum([len(w) for w in words])` 更省内存也更快；但 `[w.upper() for w in words if w]` 比 `list(map(str.upper, filter(None, words)))` 更好读。

💡 提示：这是风格取舍而非对错——团队统一最重要。函数式风格浓的代码库（大量用 `toolz`/`pyrsistent`）里 map/filter 更协调；普通业务代码里推导式几乎总是更清晰。

---

## 📚 扩展阅读

- [functools 官方文档](https://docs.python.org/3/library/functools.html)
- [函数式编程 in Python (PyCon Talk)](https://www.youtube.com/watch?v=3XFX4mAU7WQ)
- [Pyrsistent - 不可变数据结构库](https://github.com/tobgu/pyrsistent)
- [Toolz - 函数式编程工具库](https://toolz.readthedocs.io/)
