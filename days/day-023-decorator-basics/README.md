# Day 023 — 装饰器入门 🎨

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
2. 如果同一个函数被多个装饰器装饰，它们的执行顺序是怎样的？为什么是洋葱模型？
3. 没有 `functools.wraps` 会有什么实际影响？试想 Flask 的路由装饰器如果不用 wraps 会怎样？
4. 装饰器在函数定义时执行——这个特性有什么实际用途？（提示：注册机制、信号系统）
5. 如何实现一个装饰器，让它既能带参数又能不带参数？（`@decorator` 和 `@decorator(args)` 都能工作）

## 📚 扩展阅读

- [PEP 318 — Decorators for Functions and Methods](https://peps.python.org/pep-0318/)
- Python 官方文档：[装饰器](https://docs.python.org/3/glossary.html#term-decorator)
- `functools.wraps` 源码分析
- [Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/)
