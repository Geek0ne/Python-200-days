# Day 023 — 装饰器入门练习题与检查表

## ✅ 完成检查表

### 概念理解
- [ ] 理解函数是一等公民的含义
- [ ] 能解释闭包的三要素
- [ ] 理解装饰器是语法糖，等价于 `func = decorator(func)`
- [ ] 理解 `functools.wraps` 的作用
- [ ] 能解释装饰器在定义时执行而非调用时执行
- [ ] 理解洋葱模型的装饰顺序和调用顺序
- [ ] 知道装饰器常见陷阱

### 代码实践
- [ ] 能徒手写出通用装饰器模板
- [ ] 会使用 `@functools.wraps`
- [ ] 能实现日志装饰器
- [ ] 能实现计时装饰器
- [ ] 能实现函数调用计数装饰器
- [ ] 会使用 `*args, **kwargs` 让装饰器通用
- [ ] 能处理装饰器的返回值
- [ ] 能实现函数注册/收集装饰器

### 练习完成
- [ ] 基础练习（1-4 题）
- [ ] 进阶练习（5-7 题）
- [ ] 挑战练习（8-10 题）

---

## 📝 基础练习

### 练习 1：实现一个简单的装饰器

实现装饰器 `print_call`，在函数调用前后打印横线 `---`。

```python
@print_call
def greet(name):
    print(f"Hello, {name}!")

greet("Alice")
# 输出：
# ---
# Hello, Alice!
# ---
```

<details>
<summary>提示</summary>
装饰器内定义一个 wrapper，在调用 func 前后分别 print。
</details>

### 练习 2：添加 functools.wraps

给练习 1 的装饰器添加 `functools.wraps`，然后验证 `__name__` 和 `__doc__` 被正确保留。

```python
@print_call
def greet(name):
    """向某人问好"""
    pass

print(greet.__name__)  # 应该是 'greet' 而不是 'wrapper'
print(greet.__doc__)   # 应该是 '向某人问好' 而不是 None
```

### 练习 3：通用参数处理

将练习 1 的装饰器改造为能处理任意参数的通用装饰器。

```python
@print_call
def add(a, b):
    return a + b

@print_call
def greet(greeting, name, punctuation="!"):
    return f"{greeting}, {name}{punctuation}"

print(add(3, 4))           # 应该能工作
print(greet("Hello", "Alice", punctuation="?"))  # 应该能工作
```

### 练习 4：带参数的装饰器基础

实现装饰器 `repeat(n)`，让被装饰的函数重复执行 n 次。

```python
@repeat(3)
def say_hi():
    print("Hi!")

say_hi()
# 输出：
# Hi!
# Hi!
# Hi!
```

<details>
<summary>提示</summary>
repeat(n) 返回实际的装饰器，装饰器再返回 wrapper。
repeat(n) → decorator(func) → wrapper → result
</details>

---

## 🔥 进阶练习

### 练习 5：函数调用计数器

实现装饰器 `count_calls`，统计函数被调用的次数，并将计数存储在 `func.call_count` 中。添加 `func.reset_count()` 方法重置计数。

```python
@count_calls
def foo():
    pass

foo()
foo()
print(foo.call_count)  # 2
foo.reset_count()
print(foo.call_count)  # 0
```

### 练习 6：延迟执行装饰器

实现装饰器 `delay(seconds)`，在被装饰函数执行前先等待指定的秒数。

```python
@delay(0.5)
def say(msg):
    print(msg)

say("延迟后才显示")  # 等了 0.5 秒后才打印
```

### 练习 7：返回值类型检查装饰器

实现装饰器 `type_check(return_type)`，检查被装饰函数的返回值是否为指定类型，如果不是则抛出 `TypeError`。

```python
@type_check(int)
def add(a, b):
    return a + b

@type_check(str)
def greet(name):
    return f"Hello, {name}"

print(add(1, 2))  # 3 (int 类型，通过)
print(greet("Alice"))  # "Hello, Alice!" (str 类型，通过)

@type_check(int)
def bad():
    return "not a number"

bad()  # TypeError: 返回值类型错误，期望 int，实际得到 str
```

<details>
<summary>提示</summary>
使用 `isinstance(result, return_type)` 检查类型。
</details>

---

## 🏆 挑战练习

### 练习 8：装饰器执行顺序分析

预测以下代码的输出，然后运行验证：

```python
def dec_a(func):
    print("装饰 A")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("A 开始")
        result = func(*args, **kwargs)
        print("A 结束")
        return result
    return wrapper

def dec_b(func):
    print("装饰 B")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("B 开始")
        result = func(*args, **kwargs)
        print("B 结束")
        return result
    return wrapper

def dec_c(func):
    print("装饰 C")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("C 开始")
        result = func(*args, **kwargs)
        print("C 结束")
        return result
    return wrapper

@dec_a
@dec_b
@dec_c
def target():
    print("★ 目标函数执行")

target()
```

**问题**：
1. 装饰阶段的输出顺序是什么？为什么？
2. 调用阶段的输出顺序是什么？为什么？
3. 如果要改变执行顺序，应该怎么改？

### 练习 9：装饰器注册表

实现一个装饰器 `register`，它能自动将函数注册到一个全局列表中。同时实现一个装饰器 `unregister`，手动从注册表中移除函数。

```python
FUNCTIONS = []

@register
def func_a():
    return "A"

@register
def func_b():
    return "B"

print(FUNCTIONS)  # [<function func_a>, <function func_b>]

@unregister
def func_a():
    return "A"

print(FUNCTIONS)  # [<function func_b>]
```

### 练习 10：函数调用记录器

实现装饰器 `record_calls`，记录每次函数调用的参数和返回值，并存储为 `func.history` 列表。

```python
@record_calls
def add(a, b):
    return a + b

add(1, 2)
add(3, 4)
add(5, 6)

for call in add.history:
    print(f"add{call.args} = {call.return_value}")

# 输出：
# add(1, 2) = 3
# add(3, 4) = 7
# add(5, 6) = 11
```

<details>
<summary>提示</summary>
使用一个简单的类或 namedtuple 来存储每次调用的信息。在 wrapper 中记录 args, kwargs, return_value。
</details>

---

## 💡 思考题

1. Python 的装饰器和其他语言（如 Java 的注解、C# 的特性）有什么本质区别？
2. 为什么 Python 选择在定义时（而非调用时）应用装饰器？这样设计的优缺点是什么？
3. 装饰器可以用于类上吗？`@decorator` 放在 `class` 定义前是什么效果？
4. 函数装饰器返回的是一个函数，类装饰器返回的是什么？
5. 使用装饰器和直接修改函数体各有什么优缺点？什么时候选择装饰器？

## 📊 自我评估

| 技能 | 😰 不熟练 | 🤔 基本掌握 | 💪 熟练 |
|------|----------|------------|--------|
| 理解函数是一等公民 | | | |
| 理解闭包与装饰器关系 | | | |
| 使用 @ 语法糖 | | | |
| 使用 functools.wraps | | | |
| 实现通用装饰器模板 | | | |
| 理解装饰执行顺序 | | | |
| 实现日志装饰器 | | | |
| 实现计时装饰器 | | | |
| 理解洋葱模型 | | | |
| 避免常见陷阱 | | | |

---

## 🧪 练习题解答思路

### 练习 1：简单装饰器

```python
def print_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("---")
        result = func(*args, **kwargs)
        print("---")
        return result
    return wrapper
```

### 练习 4：repeat 装饰器

```python
def repeat(n):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator
```

### 练习 5：调用计数器

```python
def count_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.call_count += 1
        return func(*args, **kwargs)

    wrapper.call_count = 0

    def reset():
        wrapper.call_count = 0

    wrapper.reset_count = reset
    return wrapper
```

### 练习 10：调用记录器

```python
from collections import namedtuple

CallRecord = namedtuple("CallRecord", ["args", "kwargs", "return_value"])

def record_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        wrapper.history.append(CallRecord(args, kwargs, result))
        return result

    wrapper.history = []
    return wrapper
```
