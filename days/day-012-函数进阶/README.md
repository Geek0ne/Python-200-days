# Day 012 — 函数进阶

> "函数不只是写几行代码——参数传递的底层机制、默认参数的陷阱、可变参数的灵活性、类型注解的规范，这些才是真正拉开 Python 程序员水平的分水岭。"

---

## 目录

1. [默认参数陷阱（可变对象问题）](#1-默认参数陷阱可变对象问题)
2. [关键字参数与可变参数（*args, **kwargs）](#2-关键字参数与可变参数args-kwargs)
3. [函数注解（Type Hints）](#3-函数注解type-hints)
4. [实战：通用数据处理器](#4-实战通用数据处理器)
5. [思考题](#5-思考题)

---

## 1. 默认参数陷阱（可变对象问题）

### 1.1 什么是默认参数陷阱？

看下面这段代码，猜猜输出是什么：

```python
def add_item(item, items=[]):
    items.append(item)
    return items

print(add_item("a"))   # 预期: ['a']
print(add_item("b"))   # 预期: ['b'] ？
print(add_item("c"))   # 预期: ['c'] ？
```

**实际输出：**

```python
['a']
['a', 'b']      # 咦？多了个 'a'
['a', 'b', 'c'] # 越来越多！
```

**这就是默认参数陷阱** — 当你使用可变对象（如 `list`、`dict`、`set`）作为默认值时，所有调用共享**同一个**对象。

### 1.2 陷阱的原因：def 语句的执行机制

这个陷阱的核心在于理解 **Python 在什么时候创建默认参数**。

```
关键原理:

def 语句是一个可执行语句，它在 Python 中与其他语句（如赋值、if）一样，
在特定时刻执行。但有一个关键区别:

┌─────────────────────────────────────────────────────────┐
│           def 语句的执行（模块加载阶段）                    │
│                                                          │
│  当 Python 执行到 def add_item(item, items=[]): 时:      │
│                                                          │
│  ① 创建一个函数对象                                      │
│  ② 计算默认参数表达式（这里是 []）                         │
│  ③ 将计算出的默认值存入函数对象的 __defaults__ 属性中      │
│  ④ 将函数对象绑定到名字 add_item                          │
│                                                          │
│  重点: 第②步在 def 语句执行时发生，而不是在每次调用时！      │
└─────────────────────────────────────────────────────────┘
```

**用代码证明：**

```python
def add_item(item, items=[]):
    items.append(item)
    return items

# 默认参数存在函数对象的 __defaults__ 属性中
print(add_item.__defaults__)  # 输出: ([],)

# 调用一次
add_item("a")
print(add_item.__defaults__)  # 输出: (['a'],)  ← 同一个对象被修改了！
```

**id() 证明：**

```python
def demo(lst=[]):
    print(f"默认参数的 id: {id(lst)}")
    lst.append("x")

demo()  # id: 140234567890 (举例)
demo()  # id: 140234567890 (完全相同！是同一个对象)
demo()  # id: 140234567890 (还是同一个！)
```

### 1.3 内存图解

```
函数定义时 (def 语句执行):

  add_item 函数对象
  ┌─────────────────────────────────────┐
  │  __defaults__: ([])                 │
  │       │                             │
  │       ▼                             │
  │       ┌─────┐                       │
  │       │ []  │  ← 唯一的列表对象     │
  │       └─────┘                       │
  └─────────────────────────────────────┘

第一次调用 add_item("a"):

  传入 "a"
  ┌─────────────────────────────────────┐
  │ items 指向默认参数                   │
  │       │                             │
  │       ▼                             │
  │       ┌─────┐                       │
  │       │[ ]  │── items.append("a")   │
  │       │     │     ↓                 │
  │       └─────┘  ┌─────┐             │
  │                │[a] │              │
  │                └─────┘             │
  │  __defaults__ 中的列表被修改了！     │
  └─────────────────────────────────────┘

第二次调用 add_item("b"):

  传入 "b"
  ┌─────────────────────────────────────┐
  │ items 仍然指向同一个默认参数         │
  │       │                             │
  │       ▼                             │
  │       ┌─────┐                       │
  │       │[a]  │── items.append("b")   │
  │       │     │     ↓                 │
  │       └─────┘  ┌─────┐             │
  │                │[a,b]│            │
  │                └─────┘             │
  │  上个调用的 'a' 还在！              │
  └─────────────────────────────────────┘
```

### 1.4 哪些类型会触发陷阱？

| 默认参数类型 | 可变？ | 是否触发陷阱 | 说明 |
|-------------|--------|-------------|------|
| `[]` (list) | ✅ 可变 | ✅ **会** | 所有调用共享同一个列表 |
| `{}` (dict) | ✅ 可变 | ✅ **会** | 所有调用共享同一个字典 |
| `set()` | ✅ 可变 | ✅ **会** | 所有调用共享同一个集合 |
| `""` (str) | ❌ 不可变 | ❌ **不会** | 每次使用是同一对象，但不可修改 |
| `0` (int) | ❌ 不可变 | ❌ **不会** | 每次使用是同一对象，但不可修改 |
| `None` | ❌ 不可变 | ❌ **不会** | 最安全的默认值选择 |
| `True`/`False` | ❌ 不可变 | ❌ **不会** | 布尔值不可变 |

### 1.5 正确的做法

**黄金法则：使用不可变默认值 + 函数体内赋值**

```python
# ✅ 正确做法：用 None 代替可变默认值
def add_item(item, items=None):
    if items is None:
        items = []       # 每次调用时创建新列表
    items.append(item)
    return items

print(add_item("a"))  # ['a']
print(add_item("b"))  # ['b']  ← 正确！
print(add_item("c"))  # ['c']  ← 正确！
```

**为什么这样就行了？**

```
def add_item(item, items=None):
    │                          │
    │  def 执行时创建 None 对象  │
    │  None 不可变，无法修改     │
    │                           │
    │  items is None → True     │
    │  items = [] → 每次调用都   │
    │  创建一个新的空列表         │
    │                           │
    │  每个调用有自己独立的 []   │
    └───────────────────────────┘
```

**更多示例：**

```python
# ❌ 陷阱
def add_student(name, grades=[]):
    grades.append(name)
    return grades

# ✅ 正确
def add_student(name, grades=None):
    if grades is None:
        grades = []
    grades.append(name)
    return grades


# ❌ 陷阱
def cache_result(key, cache={}):
    cache[key] = key.upper()
    return cache

# ✅ 正确
def cache_result(key, cache=None):
    if cache is None:
        cache = {}
    cache[key] = key.upper()
    return cache
```

### 1.6 什么时候可以用可变默认值？

Python 官方文档其实说过：**了解原理后，如果你故意要这个行为**，那可以用。

**合法使用场景——缓存/记忆化：**

```python
def fibonacci(n, cache={}):
    """带缓存的斐波那契数列（利用默认参数陷阱进行记忆化）"""
    if n in cache:
        return cache[n]
    if n < 2:
        return n
    cache[n] = fibonacci(n - 1, cache) + fibonacci(n - 2, cache)
    return cache[n]

# 每次调用都共享同一个 cache 字典——这正是我们想要的！
print(fibonacci(10))   # 55
```

但这仍然是**反直觉**的写法，生产代码中应使用明确的类或闭包。

---

## 2. 关键字参数与可变参数（*args, **kwargs）

### 2.1 位置参数 vs 关键字参数

先搞清楚这两个概念：

```python
def greet(name, greeting, punctuation):
    return f"{greeting}, {name}{punctuation}"

# 位置参数（Positional Arguments）— 按顺序传递
print(greet("张三", "你好", "!"))     # 你好, 张三!

# 关键字参数（Keyword Arguments）— 指定参数名传递
print(greet(name="张三", greeting="你好", punctuation="!"))

# 混合使用 — 位置参数必须在关键字参数之前
print(greet("张三", greeting="你好", punctuation="!"))  # ✅
# print(greet(name="张三", "你好", "!"))                # ❌ SyntaxError
```

**位置参数 vs 关键字参数对比：**

| 对比维度 | 位置参数 | 关键字参数 |
|---------|---------|-----------|
| 传递方式 | 按位置匹配 | 按名称匹配 |
| 顺序要求 | 必须遵守参数顺序 | 可以不按顺序 |
| 可读性 | 差（需要知道参数位置） | 好（一目了然） |
| 必须性 | 调用时必不可少 | 可选（搭配默认值） |
| 性能 | 稍快（少一步名称匹配） | 稍慢 |

### 2.2 *args — 可变位置参数

**需求场景：**

假如你要写一个求和函数，但调用者可能传入 2 个、3 个、甚至 10 个数字：

```python
# ❌ 笨办法：为每个数量写一个函数
def sum2(a, b): return a + b
def sum3(a, b, c): return a + b + c
def sum4(a, b, c, d): return a + b + c + d
# ... 没完没了

# ✅ 优雅的解法：*args
def sum_all(*args):
    """接收任意多个位置参数"""
    total = 0
    for num in args:
        total += num
    return total

print(sum_all(1, 2))              # 3
print(sum_all(1, 2, 3, 4, 5))    # 15
print(sum_all())                  # 0
```

***args 的本质：**

```
def sum_all(*args):
             │
             ▼
    *args 将所有传入的位置参数
    打包（packing）成一个元组

    sum_all(1, 2, 3, 4, 5)
                 │
                 ▼
    args = (1, 2, 3, 4, 5)    ← 元组（tuple）
                 │
                 ▼
    在函数体内可以像普通元组一样操作:
    len(args)   → 5
    args[0]     → 1
    for x in args: ...
```

**语法规则：**

```
def 函数名(普通参数, *args, 关键字参数):
              │          │
              │          └── 收集所有"多余"的位置参数
              │
              └── 普通参数正常接收值

*args 必须在普通位置参数之后，关键字参数之前。
```

```python
def multi_param(a, b, *others):
    """a 和 b 是固定参数，others 收集剩余的位置参数"""
    print(f"a = {a}, b = {b}, others = {others}")

multi_param(1, 2)              # a = 1, b = 2, others = ()
multi_param(1, 2, 3)           # a = 1, b = 2, others = (3,)
multi_param(1, 2, 3, 4, 5)    # a = 1, b = 2, others = (3, 4, 5)
```

### 2.3 **kwargs — 可变关键字参数

**需求场景：**

你想写一个函数，调用者可以传入任意命名的配置参数：

```python
def create_profile(name, **kwargs):
    """创建用户档案，支持任意额外信息"""
    profile = {"name": name}
    profile.update(kwargs)  # 将 kwargs 中的键值对加入
    return profile

print(create_profile("张三", age=25, city="北京", job="工程师"))
# {'name': '张三', 'age': 25, 'city': '北京', 'job': '工程师'}
```

****kwargs 的本质：**

```
def create_profile(name, **kwargs):
                           │
                           ▼
    **kwargs 将所有传入的关键字参数
    打包（packing）成一个字典

    create_profile("张三", age=25, city="北京")
                              │
                              ▼
    kwargs = {"age": 25, "city": "北京"}    ← 字典（dict）
                              │
                              ▼
    在函数体内可以像普通字典一样操作：
    kwargs["age"]       → 25
    kwargs.get("city")  → "北京"
    for k, v in kwargs.items(): ...
```

### 2.4 *args 和 **kwargs 解包（Unpacking）

`*` 和 `**` 不仅能用在函数定义中（打包），也能用在函数调用中**解包**：

```python
# 定义
def introduce(name, age, city):
    print(f"我叫{name}, {age}岁, 来自{city}")

# 解包列表/元组 — 使用 *
person_info = ["张三", 25, "北京"]
introduce(*person_info)  # 相当于 introduce("张三", 25, "北京")

# 解包字典 — 使用 **
person_dict = {"name": "李四", "age": 30, "city": "上海"}
introduce(**person_dict)  # 相当于 introduce(name="李四", age=30, city="上海")
```

**解包的数据流图：**

```
调用时解包（Unpacking）：

  列表解包:
  numbers = [1, 2, 3, 4, 5]
  func(*numbers)
       │
       ▼
  func(1, 2, 3, 4, 5)
       │
       ▼
  如果函数有 *args: 再次打包成元组

  字典解包:
  config = {"key1": "val1", "key2": "val2"}
  func(**config)
       │
       ▼
  func(key1="val1", key2="val2")
       │
       ▼
  如果函数有 **kwargs: 再次打包成字典
```

### 2.5 完整参数顺序（最复杂的情况）

```python
def complex_func(a, b, *args, c=10, d=20, **kwargs):
    """
    参数顺序（从左到右）：
    1. a, b           — 普通位置参数
    2. *args          — 可变位置参数
    3. c=10, d=20     — 默认关键字参数
    4. **kwargs       — 可变关键字参数
    """
    print(f"a={a}, b={b}")
    print(f"args={args}")
    print(f"c={c}, d={d}")
    print(f"kwargs={kwargs}")

complex_func(1, 2, 3, 4, 5, c=100, x="foo", y="bar")
# a=1, b=2
# args=(3, 4, 5)
# c=100, d=20
# kwargs={'x': 'foo', 'y': 'bar'}
```

**参数传递总览图：**

```
调用: complex_func(1, 2, 3, 4, 5, c=100, x="foo", y="bar")

位置参数匹配 ───────────┐        关键字参数匹配 ────────┐
                      ▼                               ▼
传入参数:   1    2    3    4    5   c=100  x="foo"  y="bar"
           │    │    │    │    │     │       │        │
           ▼    ▼    ▼    ▼    ▼     ▼       ▼        ▼
函数参数:  a    b   *args ─────►   c=10   **kwargs ────────►
                     打包成元组  (默认20)     打包成字典
                     (3,4,5)    被100覆盖   {'x':'foo','y':'bar'}
```

### 2.6 常见使用模式

**模式 1：转发参数（装饰器模式的基础）**

```python
def logger(func):
    """一个简单的装饰器：调用函数前打印参数"""
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}，参数: args={args}, kwargs={kwargs}")
        return func(*args, **kwargs)  # 原封不动转发
    return wrapper

@logger
def say_hello(name, greeting="你好"):
    print(f"{greeting}, {name}!")

say_hello("张三")
say_hello("李四", greeting="Hello")
```

**模式 2：鸭子类型编程**

```python
def configure(**kwargs):
    """通用的配置函数"""
    settings = {
        "host": "localhost",
        "port": 8080,
        "debug": False,
    }
    settings.update(kwargs)  # 用户配置覆盖默认
    return settings

print(configure(host="example.com", debug=True))
# {'host': 'example.com', 'port': 8080, 'debug': True}
```

**模式 3：适配不同数据源的统一接口**

```python
def fetch_data(source_type, **params):
    """同一接口适配不同数据源"""
    if source_type == "api":
        return f"从 API 获取: {params}"
    elif source_type == "database":
        return f"从数据库获取: {params}"
    elif source_type == "file":
        return f"从文件获取: {params}"
    else:
        raise ValueError(f"未知数据源: {source_type}")

# 调用者传入不同的关键字参数
print(fetch_data("api", url="https://api.example.com", timeout=30))
print(fetch_data("database", table="users", where="age > 18"))
print(fetch_data("file", path="/data/input.csv", encoding="utf-8"))
```

### 2.7 仅限关键字参数（Python 3 特性）

```python
def create_user(name, age, *, city, phone):
    """
    * 之后的参数是"仅限关键字参数"（Keyword-only arguments）：
    调用时必须使用关键字形式传递，不能使用位置参数。
    """
    return f"{name}({age}岁) - {city}, {phone}"

# ✅ 正确
print(create_user("张三", 25, city="北京", phone="13800138000"))

# ❌ 错误 — city 和 phone 必须用关键字形式
# print(create_user("张三", 25, "北京", "13800138000"))
# TypeError: create_user() takes 2 positional arguments but 4 were given
```

**为什么要有仅限关键字参数？**

```
┌─────────────────────────────────────────────────────────┐
│  防止位置参数混淆                                        │
│                                                          │
│  def register(name, age, *, email, phone):               │
│                                                          │
│  调用时:                                                  │
│  register("张三", 25, email="a@b.com", phone="123")      │
│  ────────  清晰明了，不会搞混                             │
│                                                          │
│  如果没有 *:                                               │
│  register("张三", 25, "a@b.com", "123")                  │
│  ────────  谁是谁全靠位置猜，容易出错                       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. 函数注解（Type Hints）

### 3.1 什么是函数注解？

函数注解（Function Annotations）是 Python 3 引入的语法，让你可以为函数的参数和返回值添加"类型提示"（Type Hints）：

```python
def greet(name: str) -> str:
    return f"你好, {name}!"

#   ↑      ↑        ↑
#  参数名   类型     返回类型
#          注解     注解
```

**关键理解：注解只是"提示"，不是"强制"**

```python
# ✅ 尽管注解说 name 应该是 str，但传入 int 也能运行
print(greet(42))  # 输出: 你好, 42!

# Python 不检查、不强制、不报错——注解只存储在 __annotations__ 中
```

### 3.2 注解的存储机制

```python
def add(x: int, y: int) -> int:
    return x + y

# 所有注解存在函数的 __annotations__ 属性中
print(add.__annotations__)
# 输出: {'x': <class 'int'>, 'y': <class 'int'>, 'return': <class 'int'>}
```

**__annotations__ 是一个字典：**

```
┌──────────────────────────────────────────────────────┐
│                  __annotations__                       │
│                                                        │
│  def add(x: int, y: int) -> int:                       │
│           ↑       ↑        ↑                           │
│           │       │        │                           │
│           ▼       ▼        ▼                           │
│   {'x': int, 'y': int, 'return': int}                  │
│                                                        │
│  键: 参数名 / 'return'  (字符串)                       │
│  值: 类型对象 / 任何表达式                              │
└──────────────────────────────────────────────────────┘
```

**注解的值可以是任何表达式：**

```python
# 字符串注解
def f(name: "用户名", age: "年龄（岁）") -> "欢迎信息":
    return f"欢迎, {name}!"

print(f.__annotations__)
# {'name': '用户名', 'age': '年龄（岁）', 'return': '欢迎信息'}


# 复杂类型（Python 3.9+ 直接用）
def process(items: list[int], mapping: dict[str, int]) -> tuple[int, str]:
    result = sum(items)
    key = list(mapping.keys())[0]
    return result, key
```

### 3.3 Python 为什么不是"强类型"？

```
动态类型 vs 静态类型:

┌─────────────────────────────────────────────────────────┐
│                    Python（动态类型）                      │
│                                                          │
│  def double(x):              # x 可以是任何类型           │
│      return x * 2            # 只要支持 * 操作             │
│                                                          │
│  double(5)         → 10      # 整数                      │
│  double("Hi")      → "HiHi"  # 字符串                    │
│  double([1,2])     → [1,2,1,2]  # 列表                   │
│  double(3.14)      → 6.28    # 浮点数                     │
│                                                          │
│  这就是"鸭子类型"（Duck Typing）：                          │
│  如果它走起来像鸭子、叫起来像鸭子，那它就是鸭子。             │
│                                                          │
│  优点: 灵活、通用                                         │
│  缺点: 大项目中容易隐藏类型错误                             │
└─────────────────────────────────────────────────────────┘
```

**Type Hints 的作用：**

```
无注解时:
    def process(data):
        # data 是什么类型？
        # 返回什么类型？
        # 全靠文档和人脑记忆

有注解时:
    def process(data: list[dict]) -> list[str]:
        # 明确知道 data 是 "列表套字典"
        # 明确知道返回 "字符串列表"
        # IDE 可以自动补全、静态检查
```

### 3.4 常用类型注解速查表

| 类型 | 语法 | 说明 |
|------|------|------|
| 基础类型 | `int`, `str`, `float`, `bool` | Python 内置类型 |
| 列表 | `list[int]` | 元素为 int 的列表 |
| 字典 | `dict[str, int]` | 键 str → 值 int 的字典 |
| 元组 | `tuple[int, str]` | 固定结构 (int, str) |
| 集合 | `set[str]` | 元素为 str 的集合 |
| 可选值 | `Optional[int]` 或 `int \| None` | 可能是 int 或 None |
| 任意类型 | `Any` | 可以是任何类型 |
| 联合类型 | `Union[int, str]` 或 `int \| str` | int 或 str |
| 可调用对象 | `Callable[[int, int], int]` | 接收两个 int 返回 int 的函数 |
| 无返回值 | `None` | 函数没有返回值 |

```python
from typing import Optional, Any, Union, Callable

# 可选值（可能是 None）
def find_user(id: int) -> Optional[dict]:
    # 返回 dict 或 None
    ...

# 联合类型（Python 3.10+ 可以用 | 语法）
def process(value: int | str) -> str:
    return str(value)

# 可调用对象
def apply_func(func: Callable[[int], str], x: int) -> str:
    return func(x)

# Any - 你能传入任何东西
def debug_log(msg: Any) -> None:
    print(str(msg))
```

### 3.5 静态类型检查工具：mypy

**注解本身不检查类型，但工具可以：**

```bash
pip install mypy
mypy your_code.py
```

**示例：**

```python
# greet.py
def greet(name: str) -> str:
    return f"你好, {name}!"

result = greet(42)  # 类型错误！42 不是 str
```

```bash
$ mypy greet.py
greet.py:4: error: Argument 1 to "greet" has incompatible type "int"; expected "str"
```

**mypy 的工作流：**

```
                    ┌─────────────┐
                    │  写代码      │
                    │  + 类型注解  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  运行 mypy   │
                    └──────┬──────┘
                           │
               ┌───────────┴───────────┐
               │                       │
               ▼                       ▼
        ┌──────────────┐      ┌──────────────┐
        │  没有错误      │      │  发现类型错误   │
        │  提交代码 ✅   │      │  修复后再提交 ❌│
        └──────────────┘      └──────────────┘
```

### 3.6 实战：带类型注解的数据处理

```python
from typing import List, Dict, Optional

def clean_data(raw_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    清洗原始数据，去除空值记录。

    Args:
        raw_data: 原始数据列表，每条记录是字典

    Returns:
        清洗后的数据列表
    """
    cleaned = []
    for record in raw_data:
        # 去除空值记录
        if any(record.values()):
            cleaned.append(record)
    return cleaned


def analyze_scores(scores: List[Union[int, float]]) -> Dict[str, float]:
    """
    分析分数数据。

    Args:
        scores: 分数列表

    Returns:
        包含统计结果的字典
    """
    if not scores:
        return {"mean": 0.0, "max": 0.0, "min": 0.0}

    return {
        "mean": sum(scores) / len(scores),
        "max": max(scores),
        "min": min(scores),
    }
```

### 3.7 何时该用 Type Hints？

| 场景 | 建议 | 理由 |
|------|------|------|
| 学习/练习代码 | 可选 | 帮助理解类型，但非必须 |
| 个人脚本（< 200 行） | 可不用 | 自己看懂就行 |
| 小型项目 | 核心函数加注解 | 提高可读性 |
| 中大型项目 | 全员加注解 | 用 mypy 做 CI 检查 |
| 库/API 开发 | 必须加注解 | 使用者需要明确的接口 |
| 教学代码 | 强烈推荐 | 帮助学习者理解类型 |

---

## 4. 实战：通用数据处理器

### 4.1 需求分析

构建一个**通用数据处理器**，它利用今天学到的所有进阶函数特性：

| 功能 | 涉及的技术 |
|------|-----------|
| 支持任意类型的数据传入 | `*args`, `**kwargs` |
| 可配置预处理函数 | 函数作为参数（Callback） |
| 带缓存的耗时计算 | 默认参数陷阱（缓存字典） |
| 安全的默认配置 | None 默认值模式 |
| 类型注解 | Type Hints |
| 多种聚合方式 | `**kwargs` 配置聚合参数 |
| 自动生成报告 | 关键字参数控制输出 |

### 4.2 架构设计

```
┌──────────────────────────────────────────────────┐
│             通用数据处理器                          │
│                                                    │
│  User Code                                         │
│  ┌──────────────────────────────────────────┐     │
│  │ data = [1, 2, 3, 4, 5]                  │     │
│  │ processor = DataProcessor()              │     │
│  │ result = processor.process(*data,        │     │
│  │     preprocess=square,                   │     │
│  │     agg_method="sum",                    │     │
│  │     report=True)                         │     │
│  └──────────────────┬───────────────────────┘     │
│                     │                              │
│                     ▼                              │
│  ┌──────────────────────────────────────────┐     │
│  │  DataProcessor                            │     │
│  │                                           │     │
│  │  ① 预处理（preprocess callback）           │     │
│  │  ② 聚合计算（方法名称通过 **kwargs 传入）   │     │
│  │  ③ 缓存结果（cache 字典）                   │     │
│  │  ④ 报告生成（通过关键字参数开关）             │     │
│  └──────────────────────────────────────────┘     │
│                                                    │
└──────────────────────────────────────────────────┘
```

### 4.3 完整代码

详见 `code/04-universal-data-processor.py`，以下是核心逻辑概览：

```python
from typing import List, Union, Optional, Callable, Dict, Any
import time

class DataProcessor:
    """
    通用数据处理器

    利用函数进阶特性实现灵活的数据处理管道：
    - 变参接收任意数量数据
    - 回调函数作为预处理
    - 缓存 + None 默认值安全模式
    - 完整类型注解
    """

    def __init__(self, name: str = "default"):
        self.name = name
        # 缓存字典 — 利用函数进阶知识：用 None 避免陷阱
        self._cache: Dict[str, Any] = {}

    def process(
        self,
        *data: Union[int, float],
        preprocess: Optional[Callable] = None,
        agg_method: str = "sum",
        use_cache: bool = True,
        **options: Any,
    ) -> Dict[str, Any]:
        """
        核心处理方法

        Args:
            *data: 要处理的数据（可变位置参数）
            preprocess: 可选的预处理函数
            agg_method: 聚合方法（sum/mean/max/min）
            use_cache: 是否使用缓存
            **options: 其他选项（verbose, report 等）

        Returns:
            处理结果字典
        """
        # 应用预处理
        if preprocess is not None:
            processed = [preprocess(x) for x in data]
        else:
            processed = list(data)

        # 缓存检查
        if use_cache:
            cache_key = self._make_cache_key(processed, agg_method)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # 聚合计算
        if agg_method == "sum":
            result_value = sum(processed)
        elif agg_method == "mean":
            result_value = sum(processed) / len(processed) if processed else 0.0
        elif agg_method == "max":
            result_value = max(processed) if processed else 0.0
        elif agg_method == "min":
            result_value = min(processed) if processed else 0.0
        else:
            raise ValueError(f"不支持的聚合方法: {agg_method}")

        result = {
            "processor": self.name,
            "method": agg_method,
            "data_count": len(processed),
            "result": result_value,
            "timestamp": time.time(),
        }

        # 缓存结果
        if use_cache:
            cache_key = self._make_cache_key(processed, agg_method)
            self._cache[cache_key] = result

        # 详细输出
        if options.get("verbose"):
            print(f"[{self.name}] 处理完成: 共 {len(processed)} 条数据")

        return result

    def _make_cache_key(self, data: list, method: str) -> str:
        return f"{method}_{hash(tuple(data))}"
```

---

## 5. 思考题

1. **默认参数陷阱的深度理解**：试试下面的代码，解释为什么第一次和第二次的输出不同：

```python
def surprise(x, lst=[]):
    lst.append(len(lst))
    return lst

print(surprise(1))    # 输出: [0]
print(surprise(2))    # 输出: [0, 1] — 为什么是 0, 1 而不是 0, 0？
```

思考顺序：第一次调用时 `lst` 是 `[]`，`len(lst)` 是 0，所以 `lst` 变成 `[0]`。第二次调用时 `lst` 还是那个列表，`len(lst)` 是 1，所以追加 1。这就证明了**调用之间共享同一个列表对象**。

2. ***args 和 **kwargs 的对比**：`*args` 和 `**kwargs` 各自什么时候使用？如果函数需要同时使用两者，为什么 `*args` 必须在 `**kwargs` 之前？尝试从 Python 参数解析机制的底层逻辑思考。

3. **类型注解的"谎言"**：Type Hints 只是"注解"，不强制检查类型。那么以下代码会怎样？

```python
def divide(a: int, b: int) -> float:
    return a / b

result = divide("10", "5")
print(result)
```

测试后思考：这说明了类型注解的什么特性？在实际项目中如何弥补这个"不强制"的不足？

4. **仅限关键字参数的设计**：写一个函数 `send_message(recipient, subject, *, urgency, attachments=None)`，解释为什么 `urgency` 和 `attachments` 要设计成仅限关键字参数？如果允许用位置参数调用 `send_message("a", "b", "high", ["file.pdf"])` 会有什么问题？

5. **混合所有概念**：设计一个函数签名，它至少包含：2 个位置参数、`*args`、1 个仅限关键字参数、`**kwargs`，并且包含完整的类型注解。描述这个函数应该做什么，并解释为什么需要这么复杂的参数结构。
