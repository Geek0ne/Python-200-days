# Day 005 — 布尔值与条件判断

> 从"是不是"到"做不做"：理解 Python 的真假判断逻辑与控制流程

---

## 📋 今日学习目标

- [ ] 理解布尔类型 `True` / `False` 的本质（`bool` 是 `int` 的子类）
- [ ] 掌握 Truthy / Falsy 值的判断规则
- [ ] 理解逻辑运算符的短路求值机制
- [ ] 熟练使用 `if` / `elif` / `else` 条件分支
- [ ] 掌握三元表达式及其适用场景
- [ ] 完成实战：猜数字游戏

---

## 一、布尔类型（bool）

### 1.1 概念解释

`bool`（布尔类型）是 Python 中最简单的数据类型，只有两个取值：

| 值 | 含义 | 备注 |
|----|------|------|
| `True` | 真 | 本质上就是整数 `1` |
| `False` | 假 | 本质上就是整数 `0` |

```python
is_python_fun = True
is_raining = False
```

### 1.2 原理解析：bool 是 int 的子类

这是一个让很多初学者意外的设计决策——Python 中的 `bool` 类型是 `int` 类型的子类。

```python
print(issubclass(bool, int))   # True
print(isinstance(True, int))   # True

print(True + True)             # 2（因为 True == 1）
print(True * 10)               # 10
print(False * 100)             # 0
print(True > False)            # True（因为 1 > 0）
```

**为什么这样设计？**

历史原因：Python 在 2.2 版本之前没有独立的 `bool` 类型，只用整数 `0` 和 `1` 表示真假。引入 `bool` 时，为了向后兼容，让 `bool` 继承自 `int`。这样所有曾用整数表示真假的老代码仍然正常工作。

**实际影响：**
- 可以拿布尔值做数学运算（但不推荐——代码可读性差）
- `True` 和 `False` 在需要整数的场合自动转为 `1` 和 `0`
- 带来了一个"坑"：`is` 判断时要注意

```python
# 行为差异
a = 1
b = True
print(a == b)   # True — 值相等
print(a is b)   # False — 对象不同
```

### 1.3 布尔值的转换

任何值都可以转为布尔值：

```python
print(bool(1))          # True
print(bool(0))          # False
print(bool("hello"))    # True
print(bool(""))         # False
print(bool([1, 2]))     # True
print(bool([]))         # False
print(bool(None))       # False
```

---

## 二、Truthy 与 Falsy 值

### 2.1 概念解释

在需要布尔值的上下文中（如 `if` 条件），Python 会将任何值解释为真或假，而不需要显式转换为 `bool`。这些值被称为 **Truthy**（真值）和 **Falsy**（假值）。

### 2.2 Falsy 值完整列表

Python 中只有以下值被视为 `False`：

| 类别 | Falsy 值 | 示例 |
|------|----------|------|
| 布尔值 | `False` | `bool(False)` → False |
| 数值零 | `0`, `0.0`, `0j` | `bool(0.0)` → False |
| 空序列 | `""`, `[]`, `()` | `bool("")` → False |
| 空映射 | `{}` | `bool({})` → False |
| 空集合 | `set()`, `frozenset()` | `bool(set())` → False |
| 特殊值 | `None` | `bool(None)` → False |
| 自定义 | 定义了 `__bool__` 返回 False 或 `__len__` 返回 0 | — |

**凡是未在上面列出的值，都是 Truthy。**

```python
# Falsy 值一览
falsy_values = [False, None, 0, 0.0, 0j, "", [], (), {}, set()]

for val in falsy_values:
    print(f"bool({val!r:10s}) = {bool(val)}")

# 全部输出 False
```

### 2.3 原理解析：Python 如何判断真假

当 Python 遇到一个需要布尔判断的值时（比如 `if x:`），内部调用 `bool(x)`，其判断逻辑是：

```
bool(x) 的底层流程：

1. 检查 x 是否有 __bool__() 方法？
   ├─ 有 → 调用 x.__bool__()，返回 True/False
   └─ 没有 → 进入第 2 步

2. 检查 x 是否有 __len__() 方法？
   ├─ 有 → 调用 x.__len__()，len != 0 为 True，否则 False
   └─ 没有 → 返回 True（默认 True）

规则：显式 __bool__ > 回退 __len__ > 默认 True
```

```python
class AlwaysFalse:
    """自定义类，始终为 False"""
    def __bool__(self):
        return False

class Container:
    """容器类，通过长度判断真假"""
    def __init__(self, items):
        self.items = items
    def __len__(self):
        return len(self.items)

obj = Container([1, 2, 3])
if obj:  # __len__() 返回 3，所以为 True
    print("✅ 容器非空，视为 True")

empty = Container([])
if not empty:  # __len__() 返回 0，所以为 False
    print("❌ 容器为空，视为 False")
```

### 2.4 编程实践：利用 Truthy/Falsy 简化代码

```python
# ❌ 新手写法
name = input("请输入名字: ")
if name != "":
    print(f"你好, {name}!")
else:
    print("名字不能为空")

# ✅ Pythonic 写法 — 利用空字符串是 Falsy
name = input("请输入名字: ")
if name:
    print(f"你好, {name}!")
else:
    print("名字不能为空")
```

```python
# ❌ 新手写法
items = get_items()  # 可能返回 None 或列表
if items is not None and len(items) > 0:
    process(items)

# ✅ Pythonic 写法
items = get_items()
if items:  # None 是 Falsy，空列表也是 Falsy
    process(items)
```

**重要提醒**：利用 Truthy/Falsy 简化代码是 Python 的特色，但在某些场景下过于"聪明"反而降低可读性。例如检查 `x is not None` 和 `if x:` 语义不同（`x=0` 时前者为 True，后者为 False），要根据实际语义选择。

---

## 三、比较运算符

### 3.1 定义与速查

| 运算符 | 含义 | 示例 | 结果 |
|--------|------|------|------|
| `==` | 等于（值相等） | `5 == 5` | `True` |
| `!=` | 不等于 | `5 != 3` | `True` |
| `>` | 大于 | `5 > 3` | `True` |
| `<` | 小于 | `5 < 3` | `False` |
| `>=` | 大于等于 | `5 >= 5` | `True` |
| `<=` | 小于等于 | `5 <= 3` | `False` |
| `is` | 同一对象（内存地址相同） | `a is b` | — |
| `is not` | 不同一对象 | `a is not b` | — |
| `in` | 成员关系 | `"a" in "abc"` | `True` |
| `not in` | 非成员关系 | `"x" not in "abc"` | `True` |

### 3.2 链式比较

Python 支持独特的链式比较语法，这在大多数语言中是不支持的：

```python
# 传统写法（大多数语言）
x = 5
if x > 3 and x < 10:
    print("x 在 3 和 10 之间")

# Python 链式比较
if 3 < x < 10:
    print("x 在 3 和 10 之间")

# 更多例子
age = 25
if 18 <= age <= 65:
    print("适龄工作人群")

# 甚至可以跨越多个运算符
print(1 < 2 < 3 < 4 < 5)   # True（等价于 1<2 and 2<3 and 3<4 and 4<5）
```

**原理**：链式比较 `a < b < c` 在内部等价于 `a < b and b < c`，表达式 `b` 只计算一次。

### 3.3 `== 与 is` 的区别

这是 Python 入门必踩的"坑"之一：

```python
# == 比较的是值（内容）是否相等
# is 比较的是对象（内存地址）是否相同

a = [1, 2, 3]
b = [1, 2, 3]

print(a == b)   # True  — 内容相同
print(a is b)   # False — 不同对象

# 特殊情况：小整数缓存
x = 256
y = 256
print(x is y)   # True  — 小整数被缓存复用

z = 257
w = 257
print(z is w)   # False — 超出缓存范围

# None 的检查习惯
value = None
print(value is None)     # ✅ 推荐：检查 None 用 is
print(value == None)     # ❌ 不推荐：但也能工作
```

**黄金规则**：
- 比较"值"用 `==`
- 比较"身份"（是不是同一个对象）用 `is`
- 检查 `None` 统一用 `is None` / `is not None`

---

## 四、逻辑运算符

### 4.1 定义与速查

Python 有三个逻辑运算符：

| 运算符 | 名称 | 描述 | 示例 |
|--------|------|------|------|
| `and` | 逻辑与 | 两边都为 True 才返回 True | `True and False` → `False` |
| `or` | 逻辑或 | 至少一边为 True 就返回 True | `True or False` → `True` |
| `not` | 逻辑非 | 取反 | `not True` → `False` |

```python
print(True and True)    # True
print(True and False)   # False
print(False and False)  # False

print(True or True)     # True
print(True or False)    # True
print(False or False)   # False

print(not True)         # False
print(not False)        # True
```

### 4.2 原理解析：短路求值（Short-Circuit Evaluation）

这是逻辑运算符最核心、最容易被忽视的特性。

**and 的短路行为：**
```
表达式 A and B 的执行流程：
1. 计算 A
2. 如果 A 是 Falsy → 直接返回 A，不计算 B（B 被跳过了！）
3. 如果 A 是 Truthy → 继续计算 B，返回 B
```

**or 的短路行为：**
```
表达式 A or B 的执行流程：
1. 计算 A
2. 如果 A 是 Truthy → 直接返回 A，不计算 B（B 被跳过了！）
3. 如果 A 是 Falsy → 继续计算 B，返回 B
```

```python
# 短路求值演示
def risky_operation():
    """模拟一个会报错的危险操作"""
    print("⚠️  执行了危险操作！")
    return 1 / 0  # 会引发 ZeroDivisionError

def safe_check():
    """安全检查：返回 False"""
    print("🔍 安全检查通过")
    return False

# 因为短路机制，risky_operation() 永远不会被执行！
result = safe_check() and risky_operation()
print(f"结果: {result}")  # False，risky_operation 没被调用

# 同理：
result2 = safe_check() or risky_operation()
print(f"结果: {result2}")  # 先执行 safe_check，返回 False
                          # 由于 or 的短路：第一个是 False，继续执行第二个
```

**为什么要有短路求值？**
1. **性能优化**：如果 A 已经能决定结果，就不需要计算 B
2. **安全编程**：可以在确认安全后再执行危险操作
3. **条件前置检查**：最常见的用途

```python
# 常见用途：先检查再访问
user = {"name": "Alice", "age": 30}

# 安全地访问可能不存在的键
if "email" in user and user["email"].endswith(".com"):
    print("邮箱是 .com 域名")

# 等价于（但更安全）：
if user.get("email", "").endswith(".com"):
    print("邮箱是 .com 域名")

# 短路求值的另一个经典用法：默认值
name = input("请输入名字: ") or "匿名用户"
# 如果 input 返回空字符串（Falsy），则使用 "匿名用户"
print(f"你好, {name}")
```

**重要陷阱：and/or 返回的不一定是布尔值**

```python
# and 和 or 返回的是最后一个被计算的值，不一定是 True/False
print(0 and 42)    # 0 （因为 0 是 Falsy，短路，返回 0）
print(3 and 42)    # 42（因为 3 是 Truthy，继续计算，返回 42）
print(0 or 42)     # 42（因为 0 是 Falsy，继续计算，返回 42）
print(3 or 42)     # 3 （因为 3 是 Truthy，短路，返回 3）
```

### 4.3 德摩根定律与逻辑简化

```python
# 德摩根定律
# not (A and B) == not A or not B
# not (A or B)  == not A and not B

# 实际应用：简化条件
age = 20
has_permit = False

# 复杂版本
if not (age >= 18 and has_permit):
    print("不能进入")

# 简化版本（德摩根）
if age < 18 or not has_permit:
    print("不能进入")

# 规则：把括号展开，not 分配给每个条件，and↔or 互换
```

### 4.4 运算符优先级（含逻辑运算符）

```
从高到低：
  not      ← 逻辑非（一元运算符，优先级很高）
  and      ← 逻辑与
  or       ← 逻辑或（优先级最低）
```

```python
# 优先级实战
print(True or False and False)
# 等价于 True or (False and False)  因为 and 优先于 or
# = True or False
# = True

print(not True and False)
# 等价于 (not True) and False  因为 not 优先于 and
# = False and False
# = False

# 最佳实践：永远用括号明确优先级
result = (True or False) and False   # False（清晰！）
result = True or (False and False)   # True（清晰！）
```

---

## 五、if / elif / else 条件分支

### 5.1 基本语法

```python
if 条件:
    代码块  # 条件为 True 时执行
elif 其他条件:
    代码块  # 上面条件不满足且当前条件为 True 时执行
else:
    代码块  # 以上条件都不满足时执行
```

```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
elif score >= 70:
    grade = "C"
elif score >= 60:
    grade = "D"
else:
    grade = "F"

print(f"分数: {score}, 等级: {grade}")  # B
```

### 5.2 原理解析：条件判断的执行流程

```
if/elif/else 的执行流程（以 CPU 指令级别理解）：

程序计数器 PC 开始执行

① 计算 if 条件表达式
   ↓
② 条件为 True? ──Yes──→ 执行 if 代码块 → 跳到 end
   │
   No
   ↓
③ 计算 elif 条件表达式（如果有）
   ↓
④ 条件为 True? ──Yes──→ 执行 elif 代码块 → 跳到 end
   │
   No (或没有 elif)
   ↓
⑤ 有 else? ──Yes──→ 执行 else 代码块
   │
   No → 什么都不做
   ↓
end: 继续执行后续代码
```

```python
# 可以用 dis 模块看字节码
import dis

code = """
if x > 0:
    print("正数")
elif x == 0:
    print("零")
else:
    print("负数")
"""

dis.dis(code)
```

### 5.3 条件判断中的常见错误

```python
# ❌ 错误 1：忘记冒号
# if x > 5
#     SyntaxError: expected ':'

# ❌ 错误 2：用 = 代替 ==
# if x = 5:  # 赋值表达式，不是比较
#     SyntaxError: invalid syntax  (Python 3 中)
# 但在 Python 3.8+ 可用海象运算符 :=
# if (n := len(items)) > 5:  # 合法但语义不同

# ❌ 错误 3：缩进不一致
# if True:
#   print("hello")
#        print("world")  # 多了一个空格！IndentationError

# ❌ 错误 4：没考虑边界情况
age = 18
if age > 18:
    print("成年人")    # age=18 时不输出，可能不符合预期
if age >= 18:
    print("成年人")    # 正确

# ❌ 错误 5：条件悬空（dangling else）—— Python 不存在这个问题
# 因为 Python 通过缩进确定归属，不存在 else 属于哪个 if 的歧义
```

### 5.4 嵌套 if

```python
# 嵌套使用场景：有多层前置条件
def validate_login(username, password, is_admin):
    """模拟登录验证"""
    if username:                    # 第一层：用户名非空
        if password:                # 第二层：密码非空
            if len(password) >= 8:  # 第三层：密码长度
                if is_admin:        # 第四层：管理员权限
                    print("✅ 管理员登录成功")
                else:
                    print("✅ 普通用户登录成功")
            else:
                print("❌ 密码长度不足 8 位")
        else:
            print("❌ 密码不能为空")
    else:
        print("❌ 用户名不能为空")

# 嵌套太深怎么办？—— 提前返回（guard clause）
def validate_login_v2(username, password, is_admin):
    """用守卫子句避免嵌套过深"""
    if not username:
        print("❌ 用户名不能为空")
        return
    
    if not password:
        print("❌ 密码不能为空")
        return
    
    if len(password) < 8:
        print("❌ 密码长度不足 8 位")
        return
    
    if is_admin:
        print("✅ 管理员登录成功")
    else:
        print("✅ 普通用户登录成功")

# 原则：嵌套不超过 3 层。超过就考虑用守卫子句或拆分函数
```

**扁平优于嵌套——Python 之禅（The Zen of Python）的体现之一。**

---

## 六、三元表达式（条件表达式）

### 6.1 概念解释

Python 的三元表达式（也称条件表达式）是一种在一行内完成条件判断的语法：

```python
# 语法
值_when_true if 条件 else 值_when_false
```

```python
# 传统 if/else
age = 20
if age >= 18:
    status = "成年"
else:
    status = "未成年"

# 三元表达式
status = "成年" if age >= 18 else "未成年"
```

### 6.2 适用场景

```python
# ✅ 适合：简单赋值
x = 10
label = "正数" if x > 0 else ("零" if x == 0 else "负数")

# ✅ 适合：列表推导式中
numbers = [1, 2, 3, 4, 5]
parity = ["偶" if n % 2 == 0 else "奇" for n in numbers]
print(parity)  # ['奇', '偶', '奇', '偶', '奇']

# ✅ 适合：函数返回值
def max_of_two(a, b):
    return a if a > b else b

# ❌ 不适合：复杂逻辑
# action = "删除" if user.is_admin else ("查看" if user.has_permission else "拒绝")
# 改成 if/elif/else 更清晰

# ❌ 不适合：分支中有副作用
# 下面这种写法虽然可行但可读性差
# print("成功") if save_data() else print("失败")
# 应该用：
# if save_data():
#     print("成功")
# else:
#     print("失败")
```

### 6.3 嵌套三元表达式

```python
# 嵌套三元表达式（不推荐写太长）
score = 75
result = "优秀" if score >= 90 else "良好" if score >= 80 else "及格" if score >= 60 else "不及格"

# 格式化换行后更清晰
result = (
    "优秀" if score >= 90 else
    "良好" if score >= 80 else
    "及格" if score >= 60 else
    "不及格"
)
print(result)  # 及格
```

**黄金法则**：三元表达式适用于简单条件赋值。如果条件逻辑超过一行，或者条件多于两个分支，请改用传统的 `if/elif/else`。

---

## 七、实战：猜数字游戏

完整的猜数字游戏代码见 `code/02-guess-number-game.py`。这里仅展示核心逻辑：

```python
import random

def guess_number():
    """猜数字游戏核心逻辑"""
    # 生成随机数
    target = random.randint(1, 100)
    attempts = 0
    max_attempts = 7
    
    print("🎯 猜数字游戏（1-100）")
    print(f"你有 {max_attempts} 次机会")
    
    while attempts < max_attempts:
        try:
            guess = int(input(f"\n第 {attempts + 1} 次猜测: "))
        except ValueError:
            print("❌ 请输入有效数字")
            continue
        
        attempts += 1
        
        # 条件判断核心
        if guess == target:
            print(f"🎉 恭喜！你猜中了！用了 {attempts} 次")
            return True
        elif guess < target:
            print("📈 太小了，再大点")
        else:
            print("📉 太大了，再小点")
        
        # 提示剩余次数
        remaining = max_attempts - attempts
        if remaining > 0:
            print(f"还剩 {remaining} 次机会")
    
    print(f"😅 游戏结束，答案是 {target}")
    return False
```

**设计要点**：
1. `if/elif/else` 结构处理三种情况：相等、偏小、偏大
2. 使用 `try/except` 处理用户输入异常
3. 通过循环控制游戏轮次
4. 利用布尔返回值表示输赢

---

## 八、常见陷阱与避坑指南

### 陷阱 1：`==` 和 `is` 混用

```python
# 当心！
a = 1000
b = 1000
print(a is b)    # 可能是 False（CPython 实现细节）

# 安全做法：永远用 == 比较值
```

### 陷阱 2：and/or 返回值类型

```python
# 以为会返回 True/False，结果返回了其他类型
result = 0 or "default"
print(result)              # "default"
print(result is True)      # False! 类型是 str，不是 bool

# 如果需要布尔值，用 bool() 包装
safe_result = bool(0 or "default")
```

### 陷阱 3：链式比较的意外行为

```python
# 猜猜结果？
print(False == False in [False])  # True
# 等价于 (False == False) and (False in [False])
# 并不是 False == (False in [False])
```

### 陷阱 4：`elif` 中忘记前面的条件

```python
x = 50

if x > 10:
    print("大于 10")    # 会被执行
elif x > 30:
    print("大于 30")    # 不会被执行！因为前面的 x > 10 已经匹配
# elif 只在前面的条件不成立时才检查
```

### 陷阱 5：浮点数比较

```python
# 浮点数不要用 == 比较
a = 0.1 + 0.2
if a == 0.3:  # False!
    print("相等")

# 正确做法：用误差范围
if abs(a - 0.3) < 1e-9:
    print("近似相等")
```

---

## 💡 思考题

1. **短路求值应用题**：为什么下面的代码不会报错？`result = [] and 1/0` 的结果是什么？

2. **布尔值运算题**：`True + True + True * False` 的值是多少？先不要运行，在脑中推算。

3. **链式比较题**：`1 == 1 == 1` 的结果是什么？`1 == 1 == 2` 呢？为什么？

4. **Truthy/Falsy 题**：`bool("False")` 的结果是什么？解释原因。

5. **代码审查题**：以下代码有什么问题？如何改进？
   ```python
   if user:
       if user.is_active:
           if user.has_permission:
               do_something()
   ```

---

## 📚 参考资料

- [Python 文档: 布尔值](https://docs.python.org/zh-cn/3/library/stdtypes.html#truth-value-testing)
- [Python 文档: 比较运算符](https://docs.python.org/zh-cn/3/reference/expressions.html#comparisons)
- [Python 文档: 布尔运算](https://docs.python.org/zh-cn/3/reference/expressions.html#boolean-operations)
- [Python 文档: 条件语句](https://docs.python.org/zh-cn/3/tutorial/controlflow.html#if-statements)
- [PEP 308 — 三元表达式](https://peps.python.org/pep-0308/)
