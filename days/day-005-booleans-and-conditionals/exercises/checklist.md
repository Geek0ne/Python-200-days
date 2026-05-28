# Day 005 — 布尔值与条件判断：检查清单与练习题

## ✅ 今日完成清单

### 概念理解
- [ ] 理解 `bool` 是 `int` 的子类（历史原因与设计哲学）
- [ ] 掌握 Truthy / Falsy 值的完整判断规则
- [ ] 了解 `__bool__()` 与 `__len__()` 在布尔判断中的优先级
- [ ] 掌握比较运算符（`==`, `!=`, `>`, `<`, `>=`, `<=`, `is`, `in`）
- [ ] 理解链式比较的原理（`a < b < c` 等价于 `a < b and b < c`）
- [ ] 分清 `==`（值相等）与 `is`（身份相等）
- [ ] 理解 `and/or` 的短路求值机制
- [ ] 掌握逻辑运算符优先级（`not > and > or`）
- [ ] 理解德摩根定律及其化简方法
- [ ] 熟练使用 `if` / `elif` / `else` 条件分支
- [ ] 掌握守卫子句（guard clause）避免嵌套过深
- [ ] 掌握三元表达式的使用场景和注意事项
- [ ] 了解 `and/or` 返回最后一个计算值（不一定是布尔值）

### 代码练习
- [ ] 运行 `01-booleans-and-operators.py` 并观察所有输出
- [ ] 理解短路求值演示中的行为
- [ ] 运行 `02-guess-number-game.py` 并至少玩一轮
- [ ] 尝试 AI 猜数字演示，观察二分查找效率
- [ ] 调整猜数字游戏的参数（范围、次数）观察变化

---

## 📝 练习题

### 练习 1：闰年判断器

编写一个函数判断给定年份是否为闰年。

**闰年规则**：
- 能被 4 整除但不能被 100 整除，是闰年
- 能被 400 整除，也是闰年
- 其他都不是闰年

```python
def is_leap_year(year: int) -> bool:
    """
    判断 year 是否是闰年。
    要求：使用链式比较或 and/or/not 简化条件。
    """
    pass

# 测试用例
# print(is_leap_year(2000))  # True (能被 400 整除)
# print(is_leap_year(1900))  # False (能被 100 整除但不能被 400 整除)
# print(is_leap_year(2024))  # True (能被 4 整除但不能被 100 整除)
# print(is_leap_year(2023))  # False
```

**进阶要求**：使用三元表达式写成一行的版本。

---

### 练习 2：数字分类器

编写函数，输入一个整数，判断它属于以下哪类：

- 正偶数 / 正奇数
- 零
- 负偶数 / 负奇数

```python
def classify_number(n: int) -> str:
    """
    返回数字的分类描述。
    要求：使用 if/elif/else，尽可能使用链式比较和逻辑运算符。
    """
    pass

# 测试用例
# print(classify_number(10))   # "正偶数"
# print(classify_number(7))    # "正奇数"
# print(classify_number(0))    # "零"
# print(classify_number(-4))   # "负偶数"
# print(classify_number(-3))   # "负奇数"
```

---

### 练习 3：密码强度检测器

编写函数，根据以下规则评估密码强度：

- **弱**：长度 < 6
- **中**：长度 >= 6 且至少包含一个小写字母和一个数字
- **强**：长度 >= 8 且包含大写字母、小写字母、数字
- **很强**：长度 >= 12 且包含大写字母、小写字母、数字、特殊字符（非字母数字）

```python
def password_strength(password: str) -> str:
    """
    返回密码强度等级：'弱' / '中' / '强' / '很强'
    提示：用 any() 函数和字符串方法检查字符类型。
    str.isupper(), str.islower(), str.isdigit() 等可用来判断字符。
    """
    pass

# 测试用例
# print(password_strength("abc"))          # "弱"
# print(password_strength("abc123"))       # "中"
# print(password_strength("Abc12345"))     # "强"
# print(password_strength("Abc@12345xyz")) # "很强"
# print(password_strength("ABCDEFG"))      # "弱" (只有大写字母)
```

**提示**：
- 可以用 `any(c.isupper() for c in password)` 检查是否包含大写字母
- 特殊字符判断：`not c.isalnum()` 可以检查非字母数字字符

---

### 练习 4：三角形类型判断

输入三个边长，判断能否构成三角形，如果能，是什么三角形？

```python
def triangle_type(a: float, b: float, c: float) -> str:
    """
    判断三角形类型。
    规则：
    - 任意两边之和大于第三边才能构成三角形
    - 三边相等：等边三角形
    - 两边相等：等腰三角形
    - 勾股定理满足：直角三角形
    - 其他：普通三角形
    
    返回："不能构成三角形" / "等边三角形" / "等腰三角形" / "直角三角形" / "普通三角形"
    """
    pass

# 测试用例
# print(triangle_type(1, 2, 3))     # "不能构成三角形" (1+2=3，不大于)
# print(triangle_type(3, 4, 5))     # "直角三角形" (3²+4²=5²)
# print(triangle_type(5, 5, 5))     # "等边三角形"
# print(triangle_type(5, 5, 3))     # "等腰三角形"
# print(triangle_type(7, 8, 9))     # "普通三角形"
```

**注意**：浮点数比较时要注意精度问题，可以用 `abs(a² + b² - c²) < 1e-9` 代替 `a² + b² == c²`。

---

### 练习 5：简易计算器（条件分支版）

编写一个四则运算计算器，支持 `+`, `-`, `*`, `/` 四种运算。

```python
def simple_calculator(num1: float, operator: str, num2: float) -> str:
    """
    执行四则运算。
    
    参数:
        num1: 第一个数
        operator: 运算符 (+, -, *, /)
        num2: 第二个数
    
    返回:
        格式化结果字符串，例如 "3 + 4 = 7"
        注意：除数为 0 时返回错误信息
    """
    pass

# 测试用例
# print(simple_calculator(10, "+", 5))   # "10.0 + 5.0 = 15.0"
# print(simple_calculator(10, "-", 5))   # "10.0 - 5.0 = 5.0"
# print(simple_calculator(10, "*", 5))   # "10.0 * 5.0 = 50.0"
# print(simple_calculator(10, "/", 5))   # "10.0 / 5.0 = 2.0"
# print(simple_calculator(10, "/", 0))   # "错误：除数不能为 0"
# print(simple_calculator(10, "^", 5))   # "错误：不支持的运算符 ^"
```

**进阶**：添加更多的运算符支持（`//`, `%`, `**`）。

---

## 📊 自评

| 项目 | 掌握度 (1-5) |
|------|:------------:|
| 布尔类型理解（bool 是 int 的子类） | ⭐⭐⭐⭐⭐ |
| Truthy / Falsy 值判断 | ⭐⭐⭐⭐⭐ |
| 比较运算符与链式比较 | ⭐⭐⭐⭐⭐ |
| `==` 与 `is` 的区别 | ⭐⭐⭐⭐⭐ |
| 短路求值原理 | ⭐⭐⭐⭐⭐ |
| 逻辑运算符优先级 | ⭐⭐⭐⭐⭐ |
| if/elif/else 条件分支 | ⭐⭐⭐⭐⭐ |
| 守卫子句优化嵌套 | ⭐⭐⭐⭐⭐ |
| 三元表达式 | ⭐⭐⭐⭐⭐ |

---

## 📚 参考资料

- [Python 文档: 真值检测](https://docs.python.org/zh-cn/3/library/stdtypes.html#truth-value-testing)
- [Python 文档: 比较运算](https://docs.python.org/zh-cn/3/reference/expressions.html#comparisons)
- [Python 文档: 布尔运算](https://docs.python.org/zh-cn/3/reference/expressions.html#boolean-operations)
- [Python 文档: 条件语句](https://docs.python.org/zh-cn/3/tutorial/controlflow.html)
- [PEP 308: 条件表达式](https://peps.python.org/pep-0308/)
- [Python 之禅 (Zen of Python)](https://peps.python.org/pep-0020/)
