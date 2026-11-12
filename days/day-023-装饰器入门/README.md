# Day 023 — 装饰器入门

## 📖 学习目标

- 理解装饰器模式原理与函数是一等公民的概念
- 掌握简单装饰器的实现与语法糖 `@`
- 理解 `functools.wraps` 的原理与重要性
- 掌握装饰器的执行时机与执行顺序
- 通过实战掌握日志装饰器与计时装饰器

---

## 一、装饰器模式原理

### 1.1 什么是装饰器

**装饰器（Decorator）** 是一种设计模式，它允许在不修改原始代码的情况下，**动态地给函数或类添加新功能**。

在 Python 中，装饰器是一个**可调用对象**（通常是函数），它接收一个函数作为参数，返回一个增强后的函数。

```python
# 最简单的装饰器
def decorator(func):
    def wrapper():
        print("—— 调用前 ——")
        func()
        print("—— 调用后 ——")
    return wrapper

def hello():
    print("Hello, World!")

# 手动装饰
hello = decorator(hello)
hello()
# 输出：
# —— 调用前 ——
# Hello, World!
# —— 调用后 ——
```

### 1.2 函数是一等公民

Python 中**函数是一等公民（First-Class Citizen）**，这是装饰器能够工作的基础：

| 特性 | 说明 | 示例 |
|------|------|------|
| **赋值给变量** | 函数可以像普通值一样赋值 | `f = print; f("hi")` |
| **作为参数传递** | 函数可以作为参数传入其他函数 | `map(str, [1,2,3])` |
| **作为返回值** | 函数可以嵌套定义并返回 | `def outer(): def inner(): ...; return inner` |
| **存储在容器中** | 函数可以存储在列表/字典中 | `ops = {"add": add, "sub": sub}` |

```python
# 函数是一等公民的演示
def greet(name):
    return f"Hello, {name}!"

# 1. 赋值给变量
say_hello = greet
print(say_hello("Alice"))          # Hello, Alice!

# 2. 作为参数传递
def call_twice(func, arg):
    return func(arg), func(arg)

print(call_twice(greet, "Bob"))    # ('Hello, Bob!', 'Hello, Bob!')

# 3. 作为返回值
def get_greeter(lang):
    if lang == "zh":
        def greeter(name):
            return f"你好, {name}!"
        return greeter
    else:
        def greeter(name):
            return f"Hello, {name}!"
        return greeter

zh_greet = get_greeter("zh")
print(zh_greet("小明"))            # 你好, 小明!
```

### 1.3 闭包（Closure）—— 装饰器的核心机制

装饰器的本质是**闭包**——内层函数捕获外层函数的变量（被装饰的函数）：

```python
def decorator(func):     # ← func 被 wrapper 捕获
    def wrapper(*args, **kwargs):
        print("前置操作")
        result = func(*args, **kwargs)  # ← func 来自闭包
        print("后置操作")
        return result
    return wrapper        # ← 返回内层函数（闭包）
```

闭包的三要素：
1. **嵌套函数** — `wrapper` 定义在 `decorator` 内部
2. **引用自由变量** — `wrapper` 引用了 `func`
3. **返回内层函数** — `decorator` 返回 `wrapper`

---

## 二、简单装饰器实现

### 2.1 语法糖 `@`

Python 提供了 `@` 语法糖，让装饰器使用更简洁：

```python
# 等价写法
# 1. 手动装饰
def say_hi():
    print("Hi!")
say_hi = decorator(say_hi)

# 2. 语法糖 @ —— 完全等价
@decorator
def say_hi():
    print("Hi!")
```

`@decorator` 的本质就是 `say_hi = decorator(say_hi)`。

### 2.2 通用装饰器模板

一个通用的装饰器应该能处理任意函数（任意数量的位置参数和关键字参数）：

```python
import functools

def my_decorator(func):
    @functools.wraps(func)          # 保留原函数的元信息
    def wrapper(*args, **kwargs):   # 接收任意参数
        # 前置操作（调用前）
        result = func(*args, **kwargs)  # 调用原函数
        # 后置操作（调用后）
        return result               # 返回原函数的结果
    return wrapper
```

---

## 三、functools.wraps 原理

### 3.1 为什么要用 wraps？

装饰器返回的 `wrapper` 函数会**替换**原始函数，导致原始函数的元信息丢失：

```python
def bad_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@bad_decorator
def greet(name):
    """向某人问好"""
    return f"Hello, {name}!"

print(greet.__name__)    # 'wrapper' ← 原始名称丢失！
print(greet.__doc__)     # None ← 文档字符串丢失！
print(greet.__module__)  # '__main__'
```

### 3.2 wraps 做了什么

`functools.wraps` 将原始函数的元信息**复制**到 `wrapper` 函数上：

```python
import functools

def good_decorator(func):
    @functools.wraps(func)  # ← 关键！
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@good_decorator
def greet(name):
    """向某人问好"""
    return f"Hello, {name}!"

print(greet.__name__)    # 'greet' ← 正确保留
print(greet.__doc__)     # '向某人问好' ← 正确保留
```

`functools.wraps(func)` 实际上做了：
1. 将 `func` 的 `__name__`、`__qualname__`、`__doc__`、`__module__`、`__annotations__`、`__dict__` 等属性复制到 `wrapper`
2. 更新 `wrapper.__wrapped__` 属性指向原始函数 `func`
3. 返回 `functools.partial(update_wrapper, wrapped=func, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES)`

> ⚠️ **重要**：不仅仅是"好看"！许多框架（Flask、Django、pytest）依赖 `__name__` 和 `__doc__` 进行路由匹配、文档生成等。不用 wraps 会导致难以排查的 bug。

---

## 四、装饰器执行时机与顺序

### 4.1 执行时机：定义时

装饰器在**函数定义时**执行，而非函数调用时：

```python
registry = []

def register(func):
    print(f"注册函数: {func.__name__}")
    registry.append(func)
    return func

@register
def foo():
    print("foo 被调用")

@register
def bar():
    print("bar 被调用")

print("注册表中的函数:", registry)
# 输出（注意执行顺序）：
# 注册函数: foo
# 注册函数: bar
# 注册表中的函数: [<function foo at ...>, <function bar at ...>]
```

### 4.2 装饰顺序：自下而上

多个装饰器堆叠时，应用顺序是**从下往上**（靠近函数体的先执行）：

```python
@decorator_a
@decorator_b
@decorator_c
def func():
    pass

# 等价于：
# func = decorator_a(decorator_b(decorator_c(func)))
```

而**调用顺序**则相反：最外层装饰器最先执行前置操作：

```python
def decorator_a(func):
    print("装饰 A 执行")
    def wrapper(*args, **kwargs):
        print("A 前置")
        result = func(*args, **kwargs)
        print("A 后置")
        return result
    return wrapper

def decorator_b(func):
    print("装饰 B 执行")
    def wrapper(*args, **kwargs):
        print("B 前置")
        result = func(*args, **kwargs)
        print("B 后置")
        return result
    return wrapper

@decorator_a
@decorator_b
def hello():
    print("Hello!")

print("—— 调用阶段 ——")
hello()

# 输出：
# 装饰 B 执行     ← 先装饰 B
# 装饰 A 执行     ← 后装饰 A（外层）
# —— 调用阶段 ——
# A 前置         ← A 先进入
# B 前置         ← B 再进入
# Hello!         ← 原始函数执行
# B 后置         ← B 先退出
# A 后置         ← A 再退出
```

**记忆口诀**：装饰像洋葱——从里到外贴，从外到里剥。

---

## 五、常见装饰器陷阱与避坑

### 5.1 陷阱 1：忘记加括号

```python
# ❌ 错误：返回了装饰器本身而不是被装饰的函数
@decorator      # 正确
@decorator()    # 不同类型——调用了 decorator() 的结果作为装饰器

# 对于带参数的装饰器
@log()          # 可以——如果 log() 返回装饰器
@log            # 错误——如果 log 本身不是装饰器
```

### 5.2 陷阱 2：装饰器参数不匹配

```python
def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):  # ← 通用参数！永远正确
        return func(*args, **kwargs)
    return wrapper
```

### 5.3 陷阱 3：忽略 wraps

```python
# 不加 wraps 会导致调试困难、文档丢失、测试框架出问题
# 每条 decorator 都应该加 @functools.wraps(func)
```

### 5.4 陷阱 4：修改返回值的陷阱

```python
def uppercase_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return result.upper()  # 假设返回值总是字符串
    return wrapper

# 如果 func 返回非字符串类型会崩溃！
```

### 5.5 陷阱 5：类方法上的装饰器

```python
def method_decorator(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # 注意：类方法装饰器第一个参数是 self
        return func(self, *args, **kwargs)
    return wrapper
```

---

## 六、装饰器 API 速查表

| 概念 | 关键词 | 说明 |
|------|--------|------|
| **装饰器定义** | `def decorator(func): def wrapper(): ...` | 最基本的装饰器模式 |
| **语法糖** | `@decorator` | 等价于 `func = decorator(func)` |
| **保留元信息** | `@functools.wraps(func)` | 复制 `__name__`, `__doc__` 等 |
| **闭包** | 内层函数引用外层变量 | 装饰器的核心机制 |
| **通用参数** | `*args, **kwargs` | 使 wrapper 适配任意函数 |
| **执行时机** | 定义时执行 | 在 `def` 语句执行时立即应用 |
| **装饰顺序** | 自下而上 | `@A @B def f()` → `A(B(f))` |
| **调用顺序** | 自上而下（洋葱模型） | A 前置 → B 前置 → f → B 后置 → A 后置 |
| **无副作用** | 返回原函数的结果 | 装饰器一般应保留原函数的行为和返回值 |

---

## 💡 思考题

1. 装饰器返回的 `wrapper` 函数和原函数是什么关系？怎么证明 `@decorator` 等价于 `f = decorator(f)`？

**参考答案**

`wrapper` 是一个**新函数**（闭包），不是原函数本身。它内部把原函数 `func` 作为自由变量捕获，调用时先执行增强逻辑、再委托给 `func`。装饰后名字 `f` 实际指向 `wrapper`；原函数依然存在，被闭包引用着，并（若用了 `@functools.wraps`）可通过 `wrapper.__wrapped__` 访问。两者是"包装 / 被包装"的关系：调用签名一致，行为被增强。

`@decorator` 的本质就是 `f = decorator(f)`——Python 在 `def` 语句执行完后自动做这次赋值。下面验证两种写法行为完全一致：

```python
import functools

def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("调用前")
        return func(*args, **kwargs)
    return wrapper

def f():
    return "结果"

f_manual = decorator(f)     # 方式一：手动装饰

@decorator                  # 方式二：语法糖
def f_sugar():
    return "结果"

print(f_manual())
print(f_sugar())
print(f_manual.__wrapped__ is f)   # True：wrapper 内部持有原函数 f
```

预期输出：

```text
调用前
结果
调用前
结果
True
```

两种写法都输出"调用前 → 结果"，且 `f_manual.__wrapped__ is f` 为 `True`，说明 wrapper 内部包着原函数——这就是 `@decorator` 与 `f = decorator(f)` 等价的证据。

2. 如果同一个函数被多个装饰器装饰，它们的执行顺序是怎样的？为什么是洋葱模型？

**参考答案**

要区分两种顺序：

- **装饰（应用）顺序：自下而上**。`@A @B def f` 等价于 `f = A(B(f))`：靠近函数体的 B 先包装，A 再包装 B 的结果。这一步发生在**定义时**。
- **调用顺序：由外到内、再由内到外**。调用 f 时先执行 A 的前置，再 B 的前置，再到原函数；返回时先 B 的后置，再 A 的后置。

```python
def decorator_a(func):
    def wrapper(*args, **kwargs):
        print("A 前置")
        result = func(*args, **kwargs)
        print("A 后置")
        return result
    return wrapper

def decorator_b(func):
    def wrapper(*args, **kwargs):
        print("B 前置")
        result = func(*args, **kwargs)
        print("B 后置")
        return result
    return wrapper

@decorator_a
@decorator_b
def hello():
    print("Hello!")

hello()
```

预期输出：

```text
A 前置
B 前置
Hello!
B 后置
A 后置
```

**为什么是洋葱模型**：每个装饰器都把"上一层的结果"再包进一层闭包，形成层层嵌套，就像洋葱。调用时从最外层往里剥（A 前置 → B 前置 → 核心函数），到达核心后再逐层往外返回（B 后置 → A 后置）。前置"由外向内"、后置"由内向外"，完全对称。

3. 没有 `functools.wraps` 会有什么实际影响？试想 Flask 的路由装饰器如果不用 wraps 会怎样？

**参考答案**

不加 `functools.wraps`，装饰器返回的 `wrapper` 的 `__name__`、`__doc__`、`__qualname__`、`__module__`、`__annotations__` 等元信息都变成 wrapper 自己的（名字成了 `"wrapper"`、文档成了 `None`）。实际影响：traceback 和调试看到的是 `wrapper` 而非真实函数名；`help()`、自动文档出错；**依赖 `__name__` 的框架会直接出 bug**。

以 Flask 为例：`@app.route` 默认用视图函数的 `__name__` 作为**端点名（endpoint）**。若不用 wraps，所有视图函数都叫 `wrapper`，注册第二个路由时端点名冲突，抛出 `AssertionError: View function mapping is overwriting an existing endpoint function: wrapper`。下面用纯 Python 模拟这个注册逻辑：

```python
import functools

def bad(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def good(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@bad
def view_a():
    """文档 A"""

@bad
def view_b():
    """文档 B"""

print(view_a.__name__, view_a.__doc__)   # wrapper None
print(view_b.__name__, view_b.__doc__)   # wrapper None

# 模拟 Flask 按 __name__ 注册端点：两个视图都叫 wrapper → 冲突
endpoints = {}
for view in (view_a, view_b):
    name = view.__name__
    if name in endpoints:
        print(f"端点冲突: {name}")
    endpoints[name] = view
```

预期输出：

```text
wrapper None
wrapper None
端点冲突: wrapper
```

可见两个用 `bad` 装饰的视图都叫 `wrapper`，导致端点冲突；换成带 `@functools.wraps` 的 `good` 就能保留各自名字，冲突消失。所以 wraps 不只是"好看"，而是框架正确工作的刚需。

4. 装饰器在函数定义时执行——这个特性有什么实际用途？（提示：注册机制、信号系统）

**参考答案**

装饰器在**函数定义时（通常是模块导入时）**就执行，而非调用时。这意味着：只要"定义"了函数，就能自动完成注册 / 绑定，无需任何显式调用。典型用途：

- **注册机制**：插件系统、路由表（Flask `@app.route`）、命令注册表（CLI 框架）——函数定义时自动加入某个注册表。
- **信号 / 事件系统**：`@register("click")` 把处理函数绑定到事件名，事件触发时按名查表调用。
- **测试发现、缓存预热、权限标记**等需要"定义即收集元数据"的场景。

```python
handlers = {}

def register(event):
    def decorator(func):
        handlers[event] = func     # 定义时就完成注册，无需显式调用
        return func
    return decorator

@register("click")
def on_click():
    return "处理点击"

@register("hover")
def on_hover():
    return "处理悬停"

print(sorted(handlers))      # ['click', 'hover']
print(handlers["click"]())   # 处理点击
```

预期输出：

```text
['click', 'hover']
处理点击
```

注意：`on_click` / `on_hover` 这两个函数**从未被显式调用**，但 `handlers` 表已经填好了——这正是"定义时即完成注册"的证明。之后只要按事件名查表分发，就实现了解耦。

5. 如何实现一个装饰器，让它既能带参数又能不带参数？（`@decorator` 和 `@decorator(args)` 都能工作）

**参考答案**

核心难点：`@decorator` 会把**函数本身**作为参数传进来，而 `@decorator(args)` 先传入**配置参数**、期望返回一个装饰器。解决办法是**判断第一个位置参数是不是可调用对象（函数）**：是，就按"不带参数"处理；否则按"带参数"处理，返回真正的装饰器。

```python
import functools

def smart_decorator(*args, **kwargs):
    """兼容 @smart_decorator 与 @smart_decorator(prefix=...) / @smart_decorator("...")"""
    def decorator(func, prefix="LOG"):
        @functools.wraps(func)
        def wrapper(*a, **kw):
            print(f"[{prefix}] 调用 {func.__name__}")
            return func(*a, **kw)
        return wrapper

    # @smart_decorator：唯一位置参数就是函数本身
    if len(args) == 1 and callable(args[0]) and not kwargs:
        return decorator(args[0])
    # @smart_decorator(...)：解析配置后返回装饰器
    prefix = kwargs.get("prefix", args[0] if args else "LOG")
    return lambda func: decorator(func, prefix)

@smart_decorator
def add(a, b):
    return a + b

@smart_decorator(prefix="DEBUG")
def mul(a, b):
    return a * b

@smart_decorator("TRACE")
def sub(a, b):
    return a - b

print(add(2, 3))
print(mul(2, 3))
print(sub(5, 2))
```

预期输出：

```text
[LOG] 调用 add
5
[DEBUG] 调用 mul
6
[TRACE] 调用 sub
3
```

三种用法都成立：裸 `@smart_decorator`（默认 LOG）、关键字 `@smart_decorator(prefix="DEBUG")`、位置参数 `@smart_decorator("TRACE")`。

💡 提示：若只需支持"裸用 + 关键字参数"两种形式，还有更简洁的写法——`def deco(_func=None, *, prefix="LOG")`：`_func` 非 None 即裸用，直接装饰；否则返回内层装饰器。上面的 `callable` 判断额外兼容了"单个位置配置参数"，更通用。

## 📚 扩展阅读

- [PEP 318 — Decorators for Functions and Methods](https://peps.python.org/pep-0318/)
- Python 官方文档：[装饰器](https://docs.python.org/3/glossary.html#term-decorator)
- `functools.wraps` 源码分析
- [Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/)
