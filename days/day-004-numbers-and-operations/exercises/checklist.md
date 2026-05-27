# Day 004 — 数字与运算：检查清单与练习题

## ✅ 今日完成清单

### 概念理解
- [ ] 理解 Python 整数是任意精度的，对比 C/Java 的固定位数整数
- [ ] 了解小整数缓存的机制（-5 到 256）
- [ ] 掌握整数的四种进制表示
- [ ] 理解 IEEE 754 双精度浮点数的表示方法
- [ ] 理解 0.1 + 0.2 精度问题的根本原因
- [ ] 掌握浮点数正确比较的方法（误差容忍）
- [ ] 了解 NaN 和 Infinity 特殊值的行为
- [ ] 理解复数的实部、虚部、模长和辐角
- [ ] 掌握运算符优先级全表（从高到低 15 级）
- [ ] 理解幂运算 `**` 的右结合性
- [ ] 掌握六种位运算符的运算规则
- [ ] 理解补码表示法及 `~x = -x-1` 的原因
- [ ] 区分隐式类型转换链和显式类型转换函数
- [ ] 了解 bool 是 int 的子类这一事实
- [ ] 理解 int() 截断 vs round() 四舍五入的区别

### 代码练习
- [ ] 运行 `01-number-fundamentals.py` 并观察所有输出
- [ ] 运行 `02-scientific-calculator.py` 并尝试所有功能
- [ ] 使用进制转换器体验不同进制
- [ ] 使用浮点数分析器观察 ULP
- [ ] 在位运算游乐场中验证位运算规则

---

## 📝 练习题

### 练习 1：回文数检测器

判断一个整数是否为回文数（正读反读都一样）。

```python
def is_palindrome(n: int) -> bool:
    """判断整数 n 是否为回文数（不使用字符串）"""
    # 提示：用 // 10 和 % 10 逐位提取数字
    # 然后把反转后的数字与原数比较
    pass

# 测试用例
# print(is_palindrome(121))    # True
# print(is_palindrome(-121))   # False（负号不参与回文）
# print(is_palindrome(10))     # False
# print(is_palindrome(12321))  # True
```

**要求**：
- 不能将整数转为字符串
- 使用 `/` 和 `%` 运算符提取各位数字
- 考虑负数的情况

---

### 练习 2：浮点数误差检测器

编写一个函数，找出 0.01 到 1.00 之间所有在二进制中**不精确**的浮点数。

```python
def find_imprecise_floats():
    """
    找出 0.01 到 1.00 之间（步长 0.01）哪些数在二进制中不精确。
    提示：将浮点数转为分数（as_integer_ratio），
    看分母是否含 2 以外的质因数。
    """
    pass
```

**提示**：
- 使用 `as_integer_ratio()` 获取分数的分母
- 不精确的浮点数，其分母的质因数包含 2 以外的数

---

### 练习 3：位运算 — 汉明重量

统计一个整数的二进制表示中有多少个 1（这叫做"汉明重量"或"popcount"）。

```python
def hamming_weight(n: int) -> int:
    """
    计算整数 n 的二进制表示中 1 的个数。
    要求：仅使用位运算。
    """
    pass

# 测试用例
# print(hamming_weight(0b101010))  # 3
# print(hamming_weight(0))         # 0
# print(hamming_weight(255))       # 8
# print(hamming_weight(2**100))    # 1
```

**进阶挑战**：你能实现布莱恩·克尼根算法吗？
`n = n & (n - 1)` 每次清除最低位的 1。

---

### 练习 4：素数筛法

实现埃拉托色尼筛法，找出 2 到 n 之间的所有素数。

```python
def sieve_of_eratosthenes(n: int) -> list[int]:
    """
    使用筛法找出 <= n 的所有素数。
    原理：从 2 开始，标记所有 2 的倍数为合数，
    然后找到下一个未标记的数，标记它的倍数，
    重复直到 sqrt(n)。
    """
    pass

# 测试用例
# print(sieve_of_eratosthenes(30))
# # 预期: [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
```

---

### 练习 5：复数平面可视化

不使用外部库，用文本绘制 Mandelbrot 集合的一个截面。

```python
def mandelbrot_text(width: int, height: int) -> str:
    """
    绘制一个字符版的 Mandelbrot 集合。
    原理：对每个像素点 c，迭代 z = z² + c。
    如果 |z| <= 2，该点属于集合。
    
    参数：
      width: 字符宽度（x 轴）
      height: 字符高度（y 轴）
    
    返回：字符串，空格=集合内, * = 发散
    """
    # x 范围: -2 到 1
    # y 范围: -1.5 到 1.5
    pass

# print(mandelbrot_text(80, 24))
```

---

## 📊 自评

| 项目 | 掌握度 (1-5) |
|------|:------------:|
| 整数类型理解 | ⭐⭐⭐⭐⭐ |
| 浮点数精度问题 | ⭐⭐⭐⭐⭐ |
| 复数基础 | ⭐⭐⭐⭐⭐ |
| 运算符优先级 | ⭐⭐⭐⭐⭐ |
| 位运算实战 | ⭐⭐⭐⭐⭐ |
| 类型转换 | ⭐⭐⭐⭐⭐ |

---

## 📚 参考资料

- [Python 文档: 数字类型](https://docs.python.org/zh-cn/3/library/stdtypes.html#numeric-types-int-float-complex)
- [Python 文档: math 模块](https://docs.python.org/3/library/math.html)
- [Python 文档: cmath 模块](https://docs.python.org/3/library/cmath.html)
- [IEEE 754 Wikipedia](https://en.wikipedia.org/wiki/IEEE_754)
- [浮点运算指南（英文经典）](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html)
