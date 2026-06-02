# Day 011 — 函数基础

> "函数是程序员的超能力——把复杂问题拆成小问题，每个小问题单独解决。"

---

## 目录

1. [为什么需要函数？](#1-为什么需要函数)
2. [函数定义与调用](#2-函数定义与调用)
3. [参数传递机制（值传递 vs 引用传递）](#3-参数传递机制值传递-vs-引用传递)
4. [返回值与 None](#4-返回值与-none)
5. [文档字符串（docstring）](#5-文档字符串docstring)
6. [实战：计算器函数库](#6-实战计算器函数库)
7. [思考题](#7-思考题)

---

## 1. 为什么需要函数？

### 1.1 没有函数的世界

假设你要计算三个圆的面积：

```python
# 圆 1: 半径 5
area1 = 3.14159 * 5 * 5
print(f"圆1面积: {area1}")

# 圆 2: 半径 7
area2 = 3.14159 * 7 * 7
print(f"圆2面积: {area2}")

# 圆 3: 半径 10
area3 = 3.14159 * 10 * 10
print(f"圆3面积: {area3}")
```

**问题出在哪？**

| 问题 | 说明 |
|------|------|
| **重复代码** | 同样的公式写了 3 遍 |
| **难以修改** | 如果要改 PI 精度，要改 3 个地方 |
| **容易出错** | 复制粘贴时容易漏改某个变量 |
| **可读性差** | 没有有意义的命名，不知道在算什么 |

### 1.2 有了函数之后

```python
def circle_area(radius):
    """计算圆的面积"""
    pi = 3.14159
    return pi * radius * radius

# 使用
print(f"圆1面积: {circle_area(5)}")   # 78.53975
print(f"圆2面积: {circle_area(7)}")   # 153.93791
print(f"圆3面积: {circle_area(10)}")  # 314.159
```

**函数解决的核心问题：**

```
┌─────────────────────────────────────────────────────┐
│                    函数的本质                         │
│                                                      │
│   输入（参数） ──→  [ 函数体：处理逻辑 ]  ──→  输出（返回值）│
│                                                      │
│   函数的三大作用：                                     │
│   ① 抽象 —— 把细节封装起来，只用关心"做什么"而不是"怎么做"  │
│   ② 复用 —— 写一次，用无数次                            │
│   ③ 组合 —— 小函数拼成大函数，大函数拼成程序               │
└─────────────────────────────────────────────────────┘
```

### 1.3 函数 vs 过程

严格来说：

| 概念 | 定义 | Python 中 |
|------|------|-----------|
| **函数（Function）** | 有返回值 | `def f(): return value` |
| **过程（Procedure）** | 没有返回值 | `def f(): print("hi")` |

但在 Python 中，**过程本质上也是函数**——没有显式返回值的函数会隐式返回 `None`。

---

## 2. 函数定义与调用

### 2.1 基本语法

```python
def 函数名(参数1, 参数2, ...):
    """文档字符串（可选）"""
    函数体
    return 返回值  # 可选
```

**语法要点：**

```
def  →  关键字，声明这是在定义一个函数
 │
 │      greet  →  函数名，遵循标识符命名规则
 │       │
 │       │      name  →  参数列表，可以是 0 个或多个
 │       │       │
 ▼       ▼       ▼
┌──┐  ┌──────┐ ┌──────┐
│def│  │ greet│(│name │):    ← 冒号不能省略
└──┘  └──────┘ └──────┘
         │
         │  """
         │  Say hello
         │  """            ← 文档字符串（可选，但强烈推荐）
         │
         │  print(f"你好, {name}!")  ← 函数体（缩进一致）
         │                        ← 函数体结束（取消缩进）
```

### 2.2 最简单的函数（无参数、无返回值）

```python
# 定义
def say_hello():
    print("你好！")

# 调用
say_hello()  # 输出: 你好！
```

### 2.3 带参数的函数

```python
# 一个参数
def greet(name):
    print(f"你好, {name}!")

greet("张三")  # 输出: 你好, 张三!


# 多个参数
def introduce(name, age, city):
    print(f"我叫{name}, 今年{age}岁, 来自{city}")

introduce("张三", 25, "北京")  # 输出: 我叫张三, 今年25岁, 来自北京
```

### 2.4 带返回值的函数

```python
def add(a, b):
    return a + b

result = add(3, 5)
print(result)  # 输出: 8

# return 还可以用于提前退出
def check_age(age):
    if age < 0:
        return "年龄不能为负数"  # 提前返回
    if age < 18:
        return f"{age}岁是未成年人"
    return f"{age}岁是成年人"
```

### 2.5 函数命名规范

| 规则 | 说明 | 示例 |
|------|------|------|
| **小写 + 下划线** | Python 官方推荐 | `calculate_area`, `get_user_name` |
| **动词开头** | 表明功能 | `get_xxx`, `set_xxx`, `is_xxx`, `has_xxx` |
| **见名知意** | 从名称就能猜到功能 | 好: `calculate_average` 差: `calc`, `func1` |
| **避免缩写** | 除非是公认缩写 | 好: `max` 好: `convert_to_uppercase` 差: `conv_to_uc` |

### 2.6 函数的调用过程（栈帧）

**函数调用时，Python 内部发生了什么？**

```
                调用栈（Call Stack）
     ┌────────────────────────────────────┐
     │                                    │
     │  ┌──────────────────────────────┐  │
     │  │ greet_scope (调用 greet 时创建)│  │  ← 新栈帧（Stack Frame）
     │  │ name = "张三"                │  │
     │  │                             │  │
     │  └──────────────────────────────┘  │
     │  ┌──────────────────────────────┐  │
     │  │ global_scope (全局作用域)      │  │
     │  │ say_hello = <function>       │  │
     │  │ greet = <function>           │  │
     │  │ result = 8                   │  │
     │  └──────────────────────────────┘  │
     │                                    │
     └────────────────────────────────────┘
```

**执行过程：**

```
1. 遇到 greet("张三")
2. Python 在全局作用域查找 greet 这个名字
3. 找到 greet 函数对象
4. 为这次调用创建新的栈帧（frame）
5. 将参数 "张三" 绑定到参数名 name
6. 执行函数体
7. 函数结束，销毁栈帧
8. 回到调用点继续执行
```

### 2.7 函数是一等公民（First-class Citizen）

Python 中函数是**对象**——你可以像操作其他对象一样操作函数：

```python
# 函数可以赋值给变量
def square(x):
    return x * x

f = square       # f 现在指向 square 函数
print(f(5))      # 输出: 25

# 函数可以作为参数传递
def apply(func, value):
    return func(value)

print(apply(square, 4))  # 输出: 16

# 函数可以作为返回值
def make_multiplier(n):
    def multiplier(x):
        return x * n
    return multiplier

double = make_multiplier(2)
triple = make_multiplier(3)
print(double(5))  # 输出: 10
print(triple(5))  # 输出: 15
```

**为什么说函数是"一等公民"？**

```
数据类型的"地位"对比:

┌──────────────────────────────────┐
│          "一等公民"               │
│  可以:                            │
│    ✓ 赋值给变量                    │
│    ✓ 作为参数传递                  │
│    ✓ 作为返回值                    │
│    ✓ 存储在数据结构中               │
│                                  │
│  int  str  list  dict  FUNC      │
│   ✓    ✓    ✓     ✓    ✓ ← 函数也是│
└──────────────────────────────────┘
```

---

## 3. 参数传递机制（值传递 vs 引用传递）

### 3.1 核心概念

这是 Python 中最容易混淆的概念之一。先看 Java 的对比：

| 语言 | 基本类型 | 对象类型 | 总结 |
|------|---------|---------|------|
| **Java** | 值传递（复制值） | 引用传递（复制引用） | 两种机制 |
| **Python** | 全部是引用传递 | 全部是引用传递 | **统一机制** |

**Python 的准确说法：** Python 的参数传递是 **"传对象引用"（pass-by-object-reference）**。

### 3.2 不可变对象的"值传递"错觉

```python
def change_number(x):
    x = 10  # 这会改变外部吗？
    print(f"函数内部: x = {x}")

n = 5
change_number(n)
print(f"函数外部: n = {n}")

# 输出:
# 函数内部: x = 10
# 函数外部: n = 5  ← 没变！
```

**为什么没变？**

```
调用前:               调用中:               调用后:
                    ┌──────────┐
n ──→ 5 (int)       │ x = 5    │          n ──→ 5 (int)
                    │          │
                    │ x = 10   │  ← x 重新绑定到新对象
                    │  (新 int) │
                    └──────────┘
```

**关键理解：** `x = 10` 不是"修改 x 的值"，而是"让 x 指向一个新对象"。原来的 `n` 仍然指向 5。

### 3.3 可变对象的"引用传递"行为

```python
def append_to_list(lst):
    lst.append(4)  # 这会改变外部吗？
    print(f"函数内部: lst = {lst}")

my_list = [1, 2, 3]
append_to_list(my_list)
print(f"函数外部: my_list = {my_list}")

# 输出:
# 函数内部: lst = [1, 2, 3, 4]
# 函数外部: my_list = [1, 2, 3, 4]  ← 变了！
```

**为什么变了？**

```
调用前:                调用中:                 调用后:
                    ┌──────────┐
my_list ──→ [1,2,3] │ lst ──→ [1,2,3]─→ [1,2,3,4]  my_list ──→ [1,2,3,4]
                    │          │                     (同一个对象被修改)
                    │ lst.append(4)  ← 修改对象内容
                    └──────────┘
```

### 3.4 重新绑定 vs 修改对象

这是最重要的一步——区分这两个操作：

```python
def rebind(lst):
    """重新绑定——不会影响外部"""
    lst = [4, 5, 6]  # lst 指向一个新列表
    print(f"内部重新绑定后: {lst}")

def mutate(lst):
    """修改对象——会影响外部"""
    lst.append(4)     # 在原列表上操作
    lst[0] = 99       # 修改原列表的元素

original = [1, 2, 3]
rebind(original)
print(f"rebind 后: {original}")  # [1, 2, 3] ← 没变

mutate(original)
print(f"mutate 后: {original}")  # [99, 2, 3, 4] ← 变了
```

```
图解关键区别:

重新绑定 (rebind):                修改对象 (mutate):

函数外部                           函数外部
│                                  │
▼                                  ▼
[1, 2, 3]  ←─ lst (参数)          [1, 2, 3]  ←─ lst (参数)
  ↑                                  │
  │                                  ├──→ lst.append(4) → [1, 2, 3, 4]
原始变量                            │
                                    ├──→ lst[0] = 99 → [99, 2, 3, 4]
lst = [4, 5, 6]  ──→ [4, 5, 6]    │
  ↑                    ↑          原始变量 ──→ [99, 2, 3, 4]
  └── 新对象，与外部无关            (指向同一个已修改的对象)
```

### 3.5 完整对比表

| 操作 | 参数类型 | 影响外部？ | 说明 |
|------|---------|-----------|------|
| `x = new_value` | 不可变（int, str, tuple） | ❌ | 重新绑定参数名 |
| `x = new_value` | 可变（list, dict, set） | ❌ | 重新绑定参数名 |
| `x.method()` 修改对象 | 可变 | ✅ | 修改对象内容 |
| `x[key] = value` | 可变 | ✅ | 修改对象内容 |
| `x += other` | 不可变 | ❌ | 创建新对象 |
| `x += other` | 可变（如 list） | ✅ | 原地修改（__iadd__） |

### 3.6 如何避免意外修改？

```python
# ❌ 函数内部意外修改了外部列表
def process_data(data):
    data.append("extra")  # 影响了外部！
    return data

# ✅ 拷贝一份再操作
def process_data_safe(data):
    data = data.copy()    # 创建副本
    data.append("extra")
    return data

# ✅ 或者使用切片创建副本
def process_data_safe2(data):
    data = data[:]        # 创建副本的另一种方式
    data.append("extra")
    return data
```

---

## 4. 返回值与 None

### 4.1 return 语句

```python
def get_max(a, b):
    if a > b:
        return a
    else:
        return b

result = get_max(7, 3)
print(result)  # 输出: 7
```

**return 的两个作用：**

```
return 的作用
┌──────────────┐
│  ① 返回值     │  → 把结果传给调用者
│  ② 结束函数   │  → 立即退出，后面的代码不执行
└──────────────┘
```

```python
def check_score(score):
    if score < 0:
        return "无效分数"  # 提前返回
    if score >= 90:
        return "优秀"
    if score >= 60:
        return "及格"
    return "不及格"

# 根据不同的条件，函数可能在多个位置返回
```

### 4.2 返回多个值

Python 函数可以"返回多个值"——实际上返回的是元组：

```python
def get_stats(numbers):
    """返回最小值、最大值、平均值"""
    return min(numbers), max(numbers), sum(numbers) / len(numbers)

result = get_stats([1, 2, 3, 4, 5])
print(result)        # 输出: (1, 5, 3.0)  ← 元组
print(type(result))  # <class 'tuple'>

# 解包（unpacking）
min_val, max_val, avg = get_stats([1, 2, 3, 4, 5])
print(f"最小值: {min_val}, 最大值: {max_val}, 平均值: {avg}")
```

**原理：**

```
return min, max, avg
         │    │    │
         ▼    ▼    ▼
       (min, max, avg)  ← Python 自动打包成元组
               │
               ▼
调用者通过解包获取:  a, b, c = func()
```

### 4.3 没有 return 会怎样？——隐式的 None

```python
def print_message(msg):
    print(msg)  # 没有 return

result = print_message("你好")
print(result)   # 输出: None
print(result is None)  # True
```

**None 的本质：**

```
Python 中每个函数都必须返回一个值。

如果函数体中没有 return 语句，
或者执行了 return 但没有指定值，
Python 会自动 return None。

def f1():       def f2():
    pass           return

这两种写法等价——都返回 None。
```

### 4.4 None 的检查

```python
# ✅ 正确方式
if result is None:
    print("没有结果")

# ✅ 或
if result is not None:
    print(f"结果是: {result}")

# ❌ 错误方式（不推荐）
if result == None:
    print("不推荐这样比较")
```

**为什么用 `is` 而不是 `==`？**

```python
# is 比较的是身份（内存地址）
# == 比较的是值（内容）

# None 是单例（Singleton）——整个程序只有一个 None 对象
# 所以用 is 比较更快、更符合语义

a = None
b = None
print(a is b)      # True（同一个人）
print(a == None)   # True（但语义不够精确）
```

### 4.5 return 的类型可以不一致

Python 是动态类型语言，同一个函数在不同条件下可以返回不同类型：

```python
def process(value):
    if isinstance(value, int):
        return value * 2      # 返回 int
    elif isinstance(value, str):
        return value.upper()  # 返回 str
    else:
        return None           # 返回 None

print(process(5))      # 10 (int)
print(process("hi"))   # HI (str)
print(process([1,2]))  # None
```

**虽然灵活，但生产代码中建议保持返回类型一致**（后续会学到 type hints 约束）。

---

## 5. 文档字符串（docstring）

### 5.1 什么是文档字符串？

文档字符串是函数定义后的第一个语句，用 `""" """` 包围，用于描述函数的功能、参数和返回值。

```python
def calculate_bmi(weight, height):
    """
    计算 BMI 指数

    根据体重（kg）和身高（m）计算身体质量指数。

    参数:
        weight (float): 体重，单位公斤
        height (float): 身高，单位米

    返回:
        float: BMI 值 = weight / (height ** 2)
    """
    return weight / (height ** 2)
```

### 5.2 为什么需要文档字符串？

```
没有文档字符串:                           有文档字符串:
                                        │
def f(a, b):                            def add(a, b):
    return a + b                         """
                                        │ 返回两数之和
                                        │
谁会知道 f 是做什么的？                    │ 参数:
使用前必须读代码                           │     a: 第一个数字
                                        │     b: 第二个数字
                                        │
                                        │ 返回:
                                        │     a + b
                                        │ """
                                        │ return a + b
```

### 5.3 如何访问文档字符串？

```python
# 方式 1: help() 函数
help(calculate_bmi)  # 打印格式化的文档

# 方式 2: __doc__ 属性
print(calculate_bmi.__doc__)  # 直接访问文档字符串
```

**帮助系统的工作原理：**

```
help(calculate_bmi)
       │
       ▼
Python 获取 calculate_bmi.__doc__
       │
       ▼
通过 pydoc 模块格式化输出
       │
       ▼
显示在终端
```

### 5.4 Docstring 格式规范

| 风格 | 说明 | 适用 |
|------|------|------|
| **Google 风格** | 简洁清晰，最常见 | 个人项目、小团队 |
| **NumPy/SciPy 风格** | 详细，适合科学计算 | 科学计算、数据分析 |
| **Sphinx/reST 风格** | 自动生成 HTML 文档 | 大型开源项目 |

**Google 风格（推荐初学者使用）：**

```python
def function_name(param1, param2):
    """简短的一句话描述。

    详细描述（可选），可以写多行。
    解释函数的功能、使用注意事项等。

    Args:
        param1 (int): 参数1的描述
        param2 (str): 参数2的描述

    Returns:
        bool: 返回值的描述

    Raises:
        ValueError: 什么情况下抛出这个异常
    """
    pass
```

### 5.5 单行 vs 多行文档字符串

```python
# 单行——简单函数
def square(x):
    """返回 x 的平方。"""
    return x * x

# 多行——复杂函数
def complex_function(a, b, c=None):
    """
    执行复杂的计算逻辑。

    这个函数处理三个参数，执行一系列操作。
    如果 c 为 None 时会有特殊行为。

    Args:
        a (int): 第一个参数
        b (int): 第二个参数
        c (int, optional): 第三个参数，默认为 None

    Returns:
        dict: 包含计算结果的字典

    Raises:
        TypeError: 如果 a 或 b 不是整数
    """
```

---

## 6. 实战：计算器函数库

### 6.1 需求分析

我们要构建一个完整的计算器函数库，包含：

| 功能 | 函数名 | 说明 |
|------|--------|------|
| 基本运算 | `add`, `subtract`, `multiply`, `divide` | 加减乘除 |
| 高级运算 | `power`, `sqrt`, `mod` | 幂、平方根、取模 |
| 统计运算 | `average`, `median`, `factorial` | 均值、中位数、阶乘 |
| 交互模式 | `calculator()` | 命令行交互计算器 |

### 6.2 设计原则

```
┌──────────────────────────────────────────┐
│              计算器函数库                   │
│                                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ 基本运算  │  │ 高级运算  │  │ 统计运算  │  │
│  │ add()   │  │ power() │  │ avg()   │  │
│  │ sub()   │  │ sqrt()  │  │ median()│  │
│  │ mul()   │  │ mod()   │  │ fact()  │  │
│  │ div()   │  │         │  │         │  │
│  └─────────┘  └─────────┘  └─────────┘  │
│                                           │
│  ┌──────────────────────────────────┐     │
│  │  交互模式: calculator()          │     │
│  │  用户输入 → 解析 → 调用对应函数   │     │
│  └──────────────────────────────────┘     │
└──────────────────────────────────────────┘
```

### 6.3 完整代码

详见 `code/01-calculator-library.py`，这里展示核心部分：

**基本运算函数：**

```python
def add(a, b):
    """返回 a + b 的和。"""
    return a + b

def subtract(a, b):
    """返回 a - b 的差。"""
    return a - b

def multiply(a, b):
    """返回 a × b 的积。"""
    return a * b

def divide(a, b):
    """
    返回 a ÷ b 的商。

    注意: 除数为 0 时会返回错误信息而不是抛出异常（防御性编程）。
    这是故意的设计——让调用者可以选择如何处理错误。
    """
    if b == 0:
        return "错误：除数不能为 0"
    return a / b
```

**高级运算：**

```python
def power(base, exp):
    """返回 base 的 exp 次幂。"""
    return base ** exp

def sqrt(n):
    """
    返回 n 的平方根。

    使用牛顿迭代法实现，而不是 math.sqrt。
    目的是演示循环和近似计算的算法思维。

    牛顿迭代公式: x = (x + n/x) / 2
    """
    if n < 0:
        return "错误：不能对负数开平方"
    if n == 0:
        return 0

    x = n  # 初始猜测
    # 迭代直到收敛
    for _ in range(1000):
        next_x = (x + n / x) / 2
        if abs(next_x - x) < 1e-15:  # 精度够了
            break
        x = next_x
    return x
```

**交互模式的核心逻辑：**

```python
def calculator():
    """
    交互式计算器主函数。

    用户输入格式: 数字 运算符 数字
    支持的运算符: + - * / ^ % sqrt

    按 'q' 或 'quit' 退出。
    """
    print("=" * 40)
    print("        🔢 Python 计算器")
    print("=" * 40)
    print("支持的运算:")
    print("  a + b   加法")
    print("  a - b   减法")
    print("  a * b   乘法")
    print("  a / b   除法")
    print("  a ^ b   幂运算")
    print("  a % b   取模")
    print("  sqrt a  平方根")
    print("  quit    退出")
    print("=" * 40)

    while True:
        user_input = input("\n请输入表达式: ").strip().lower()

        if user_input in ('q', 'quit', 'exit'):
            print("感谢使用，再见！")
            break

        if not user_input:
            continue

        parts = user_input.split()
        result = None

        try:
            if parts[0] == 'sqrt' and len(parts) == 2:
                a = float(parts[1])
                result = sqrt(a)
            elif len(parts) == 3:
                a = float(parts[0])
                op = parts[1]
                b = float(parts[2])

                if op == '+':    result = add(a, b)
                elif op == '-':  result = subtract(a, b)
                elif op == '*':  result = multiply(a, b)
                elif op == '/':  result = divide(a, b)
                elif op == '^':  result = power(a, b)
                elif op == '%':  result = mod(a, b)
                else:
                    result = f"不支持的运算符: {op}"
            else:
                result = "格式错误，请按 '数字 运算符 数字' 格式输入"

            print(f"结果: {result}")

        except ValueError:
            print("错误: 请输入有效的数字")
```

### 6.4 函数库的模块化设计

```
calculator_library/
│
├── basic_ops.py      ← 基本运算函数
├── advanced_ops.py   ← 高级运算函数
├── stats_ops.py      ← 统计运算函数
└── calculator.py     ← 交互模式

（关于模块化的内容，Day 014 会详细讲解）
```

---

## 7. 思考题

1. **传参机制的理解**：如果函数接收一个列表参数，内部执行 `lst = lst + [4]` 和 `lst += [4]` 对外部列表的影响一样吗？为什么？试着从运算符重载的角度分析。

2. **函数作为对象**：既然函数是"一等公民"，你能想出实际开发中利用这个特性的例子吗？比如回调函数、装饰器等场景？不用实现，先从概念层面思考。

3. **None 的陷阱**：为什么下面的代码可能会出错？

```python
def find_user(user_id):
    if user_id == 1:
        return {"name": "张三", "age": 25}
    # 没有 else，没有其他 return

user = find_user(2)
if user["name"] == "张三":  # 这里会怎样？
    print("找到了")
```

4. **return vs print**：如果一个函数既用 `return` 返回值，又在内部 `print` 输出信息，这样设计有什么优缺点？什么时候该用哪种方式？

5. **函数设计原则**：一个函数应该做几件事？"单一职责原则"在函数设计中意味着什么？下面的函数设计有什么问题？

```python
def process_data(data):
    # 1. 清洗数据
    # 2. 分析数据
    # 3. 生成图表
    # 4. 发送邮件
    # 5. 保存到数据库
    pass
```
