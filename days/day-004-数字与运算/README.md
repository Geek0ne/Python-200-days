# Day 004 — 数字与运算

> 从"算对"到"算懂"：深入理解 Python 数字类型与运算的底层机制

---

## 📋 今日学习目标

- [ ] 理解整数、浮点数、复数三种数字类型的内存表示
- [ ] 掌握运算符优先级和结合性的实际影响
- [ ] 理解位运算的底层原理与应用场景
- [ ] 分清隐式类型转换与显式类型转换
- [ ] 完成实战：编写科学计算器

---

## 一、整数（int）

### 1.1 概念解释

Python 的 `int` 是**任意精度整数**（arbitrary-precision integer），理论上只受内存限制。这与 C/Java 等语言的固定位数整数完全不同。

```python
# Python 整数可以无限大（仅受内存限制）
small = 42
huge = 10 ** 100  # 1 后面 100 个零，也能精确表示
print(huge)
```

### 1.2 原理解析：CPython 中的 int 对象

CPython 中的 `int` 并非 CPU 寄存器中的原生整数，而是一个堆分配的对象：

```
  PyObject_HEAD (16 bytes)
  ┌────────────────────┐
  │ ob_refcnt = 1       │ ← 引用计数
  │ ob_type = &PyLong_Type │ ← 类型指针
  ├────────────────────┤
  │ ob_digit[]           │ ← 实际数值，以 2^30 为基的"数字数组"
  │ [d0, d1, d2, ...]    │
  └────────────────────┘
```

**小整数缓存**：CPython 会预创建 [-5, 256] 范围内的整数对象并复用。

```python
a = 256
b = 256
print(a is b)   # True — 小整数缓存

c = 257
d = 257
print(c is d)   # False — 超出缓存范围，每次新建对象
```

**为什么设计为任意精度？**
1. **避免溢出错误**：C 语言中 `INT_MAX + 1` 产生未定义行为，Python 不会
2. **简化心智模型**：不需要关心 int/long/short 的区别
3. **代价**：大整数运算比原生整数慢，因为需要软件实现

### 1.3 整数进制表示

| 进制 | 前缀 | 示例 | 值 |
|------|------|------|-----|
| 二进制 | `0b` / `0B` | `0b1010` | 10 |
| 八进制 | `0o` / `0O` | `0o12` | 10 |
| 十进制 | 无 | `10` | 10 |
| 十六进制 | `0x` / `0X` | `0xA` | 10 |

```python
# 不同进制表示同一数值
print(0b1010)   # 10
print(0o12)     # 10
print(0xA)      # 10

# 转换函数
print(bin(10))  # '0b1010'
print(oct(10))  # '0o12'
print(hex(10))  # '0xa'
```

### 1.4 整数常用方法

| 方法 | 说明 | 示例 |
|------|------|------|
| `int.bit_length()` | 表示该数所需的最少二进制位数 | `(42).bit_length()` → 6 |
| `int.to_bytes(n, byteorder)` | 转为字节序列 | `(1024).to_bytes(2, 'big')` |
| `int.from_bytes(bytes, byteorder)` | 从字节序列恢复整数 | `int.from_bytes(b'\x04\x00', 'big')` |
| `int.as_integer_ratio()` | 返回 (分子, 分母) | `(5).as_integer_ratio()` → (5, 1) |

```python
# bit_length 的应用：判断需要多少位存储
for n in [1, 16, 255, 256, 1024]:
    bits = n.bit_length()
    bytes_needed = (bits + 7) // 8  # 向上取整
    print(f"{n:5d} → {bits:2d} bits, {bytes_needed} byte(s)")

# to_bytes / from_bytes：网络协议编程中常用
data = (2024).to_bytes(4, byteorder='big')  # 大端序
print(data)                     # b'\x00\x00\x07\xe8'
original = int.from_bytes(data, byteorder='big')
print(original)                 # 2024
```

---

## 二、浮点数（float）

### 2.1 概念解释

`float` 实现为 C 语言的 **double**（双精度浮点数），遵循 **IEEE 754 标准**。它用 64 位表示一个数：1 位符号、11 位指数、52 位尾数。

### 2.2 原理解析：浮点数的二进制表示

```
符号位  指数位 (偏移 1023)    尾数位
  ↓        ↓                    ↓
 ┌─┬──────────┬────────────────────────────────────────────────────┐
 │0│01111111111│1001001000011111101101010100010001000010110100011000│
 └─┴──────────┴────────────────────────────────────────────────────┘
  ±        × 2^(e-1023)          × (1 + f/2^52)
```

**精度问题**：某些十进制小数无法用二进制精确表示，这是**所有使用 IEEE 754 的语言**都有的问题。

```python
print(0.1 + 0.2)          # 0.30000000000000004
print(0.1 + 0.2 == 0.3)  # False

# 为什么？因为 0.1 在二进制中是无限循环小数
# 0.1(十进制) = 0.00011001100110011...(二进制循环)
```

**如何看待精度问题？**
1. **不是 bug，是特性**：二进制与十进制之间的先天矛盾
2. **容忍误差**：用 abs(a - b) < 1e-9 代替 a == b
3. **需要精确计算时**：使用 `decimal.Decimal`

```python
# 正确的浮点数比较方式
def float_equal(a, b, epsilon=1e-9):
    return abs(a - b) < epsilon

print(float_equal(0.1 + 0.2, 0.3))  # True
```

### 2.3 特殊浮点值

```python
import math

# 正无穷大
inf_pos = float('inf')
print(inf_pos > 10**1000)       # True

# 负无穷大
inf_neg = float('-inf')

# 非数字（Not a Number）
nan = float('nan')
print(nan == nan)               # False — NaN 不等于自身！
print(math.isnan(nan))          # True — 用 is* 函数判断

# 无穷大运算规则
print(inf_pos + 1)              # inf
print(inf_pos * 0)              # nan（无穷 × 0 无定义）
print(inf_pos / inf_pos)        # nan
```

### 2.4 浮点数方法

| 方法 | 说明 |
|------|------|
| `float.as_integer_ratio()` | 返回精确分数 (分子, 分母) |
| `float.is_integer()` | 判断是否为整数值 |
| `float.hex()` | 返回十六进制浮点表示 |
| `float.fromhex(s)` | 从十六进制字符串恢复 |

```python
# 每个浮点数理论上都是有理数
ratio = 0.75.as_integer_ratio()
print(ratio)          # (3, 4)

print(3.0.is_integer())   # True
print(3.14.is_integer())  # False
```

---

## 三、复数（complex）

### 3.1 概念解释

复数由实部和虚部构成，形式为 `a + bj`（其中 `j` 代表虚数单位，注意 Python 用 `j` 而非数学中的 `i`）。

```python
z = 3 + 4j
print(type(z))                  # <class 'complex'>
print(z.real)                   # 3.0 — 实部
print(z.imag)                   # 4.0 — 虚部
print(z.conjugate())            # (3-4j) — 共轭复数
```

### 3.2 原理解析：为何需要复数？

复数在以下领域不可或缺：
- **信号处理**：傅里叶变换的输出是复数
- **量子力学**：波函数本质上是复数的
- **电路分析**：阻抗用复数表示
- **计算机图形学**：复数平面变换

```python
import cmath  # complex math

# 欧拉公式：e^(iπ) + 1 = 0
result = cmath.exp(complex(0, math.pi))
print(result)               # (-1+1.2246467991473532e-16j) ≈ -1
print(abs(result + 1) < 1e-15)  # True — 验证欧拉恒等式

# 相位和模长
z = 3 + 4j
print(abs(z))               # 5.0 — 模长 |z| = √(3²+4²)
print(cmath.phase(z))       # 0.927... — 辐角 arctan(4/3)
```

### 3.3 复数运算

```python
a = 1 + 2j
b = 3 - 1j

print(a + b)    # (4+1j)
print(a * b)    # (5+5j) — 交叉相乘
print(a / b)    # (0.1+0.7j)
print(a**2)     # (-3+4j)

# 注意：复数不支持 < > 比较
# 3 + 4j > 1 + 2j  # TypeError
```

---

## 四、运算符优先级与结合性

### 4.1 优先级全表（从高到低）

| 优先级 | 运算符 | 说明 | 结合性 |
|--------|--------|------|--------|
| 1 | `(...)` | 括号 | — |
| 2 | `**` | 幂运算 | **右结合** |
| 3 | `+x`, `-x`, `~x` | 一元运算符 | 右结合 |
| 4 | `*`, `/`, `//`, `%` | 乘、除、整除、取余 | 左结合 |
| 5 | `+`, `-` | 加、减 | 左结合 |
| 6 | `<<`, `>>` | 位左移、位右移 | 左结合 |
| 7 | `&` | 位与 | 左结合 |
| 8 | `^` | 位异或 | 左结合 |
| 9 | `\|` | 位或 | 左结合 |
| 10 | `==`, `!=`, `<`, `>`, `<=`, `>=`, `is`, `in` | 比较 | 左结合 |
| 11 | `not` | 逻辑非 | 右结合 |
| 12 | `and` | 逻辑与 | 左结合 |
| 13 | `or` | 逻辑或 | 左结合 |
| 14 | `if-else` | 三元表达式 | 右结合 |
| 15 | `:=` | 海象运算符 | 右结合 |

### 4.2 原理解析：为什么**是右结合？

数学中，幂运算是右结合的：

```
2 ** 3 ** 2  → 2 ** (3 ** 2) → 2 ** 9 → 512
          非 (2 ** 3) ** 2 → 8 ** 2 → 64
```

这种设计符合数学约定：$a^{b^c} = a^{(b^c)}$

```python
print(2 ** 3 ** 2)     # 512 — 右结合
print(2 ** (3 ** 2))   # 512 — 显式括号一致
print((2 ** 3) ** 2)   # 64 — 显式括号改变含义

# 小心链式赋值也是右结合
a = b = c = 42
# 等价于: a = (b = (c = 42))
```

### 4.3 常见陷阱

```python
# 陷阱 1：算术和比较运算符
# 有人以为这样写是 (x + y) > z
x, y, z = 1, 2, 5
print(x + y > z)        # False — 实际上正确，因为 + 优先级高于 >

# 陷阱 2：链式比较
print(1 < 2 < 3)        # True — 等价于 1 < 2 and 2 < 3
print(1 < 3 > 2)        # True — 也合法：1 < 3 and 3 > 2

# 陷阱 3：and/or 优先级
# False or True and False → False or (True and False) → False or False → False
print(False or True and False)  # False
# 如果误解为 (False or True) and False → True and False → False（结果凑巧相同）
# 但下面就有区别了：
print(True or True and False)   # True — 等价于 True or (True and False)

# 陷阱 4：赋值与比较
# if x = 5:  ← Python 中禁止，不会把赋值当条件
# but:
if n := len("hello"):   # 海象运算符可以在表达式中赋值
    print(f"长度是 {n}")  # 长度是 5
```

---

## 五、位运算原理

### 5.1 概念解释

位运算直接操作整数的二进制位，是**最底层的运算形式**。Python 的 `int` 虽然是任意精度，但位运算符对每一位进行独立操作。

### 5.2 运算符总览

| 运算符 | 名称 | 示例 | 说明 |
|--------|------|------|------|
| `&` | 位与 (AND) | `5 & 3` → 1 | 两个位都为 1 时结果为 1 |
| `\|` | 位或 (OR) | `5 \| 3` → 7 | 至少一个位为 1 时结果为 1 |
| `^` | 位异或 (XOR) | `5 ^ 3` → 6 | 两个位不同时结果为 1 |
| `~` | 位非 (NOT) | `~5` → -6 | 按位取反（含符号位） |
| `<<` | 左移 | `5 << 1` → 10 | 左移 n 位等价于 × 2ⁿ |
| `>>` | 右移 | `5 >> 1` → 2 | 右移 n 位等价于 ÷ 2ⁿ（向下取整） |

### 5.3 原理解析：补码表示

Python 中的整数使用**补码**（two's complement）表示，理论上无限位：

```
二进制                                 十进制
  ...00000101                          5
  ...00000011                          3
& ...00000001                          1
────────────────────────────────────
  ...00000101                          5
| ...00000011                          3
  ...00000111                          7
────────────────────────────────────
  ...00000101                          5
^ ...00000011                          3
  ...00000110                          6
────────────────────────────────────
  ~...00000101
  ...11111010                          -6  ← 取反后加 -1 等于 -6
```

**为什么 ~5 = -6？**
因为 Python 的整数位数无限，`~5` 翻转所有位：
- 5 的无限补码：`...00000101`
- 取反后：`...11111010`
- 这个值是 -6（-6 的补码正是 `...11111010`）

### 5.4 位运算实战技巧

```python
# 1. 检查奇偶性（比 % 2 更快）
def is_odd(n):
    return n & 1 == 1

print(is_odd(5))   # True
print(is_odd(6))   # False

# 2. 交换变量（不使用第三个变量）
a, b = 5, 3
a ^= b  # a = a ^ b
b ^= a  # b = b ^ a = (a ^ b) ^ b = a
a ^= b  # a = a ^ b = (a ^ b) ^ a = b
print(a, b)         # 3, 5

# 3. 判断是否为 2 的幂
def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0

for n in [1, 2, 4, 8, 16, 3, 6, 10]:
    print(f"{n}: {is_power_of_two(n)}")

# 4. 取最低位的 1
n = 0b101100
lowest_one = n & -n
print(bin(lowest_one))  # 0b100

# 5. 清除最低位的 1
n = 0b101100
cleared = n & (n - 1)
print(bin(cleared))     # 0b101000

# 6. 位掩码 — 用位来存储多个布尔标志
READ = 0b001
WRITE = 0b010
EXECUTE = 0b100

permissions = READ | WRITE  # 0b011 — 可读可写
can_read = permissions & READ != 0      # True
can_execute = permissions & EXECUTE != 0  # False

# 添加执行权限
permissions |= EXECUTE      # 0b111
# 移除写权限
permissions &= ~WRITE       # 0b101
```

### 5.5 位运算图解

```
8 的二进制表示：      00001000
8 >> 1 (右移一位)：   00000100  = 4  (等价于 ÷2)
8 << 1 (左移一位)：   00010000  = 16 (等价于 ×2)
7 >> 1 (奇数右移)：  00000011  = 3  (向下取整 ÷2)

掩码操作图解（清除 bit 2）：
  原值：     10110101
  掩码：    &11011111  (= ~00100000)
  结果：     10010101
```

---

## 六、类型转换（Type Conversion）

### 6.1 隐式类型转换（Implicit）

Python 在运算中自动将"精度较低"的类型转为"精度较高"的类型。

**转换链**：`int → float → complex`

```python
# int + float → float
result = 3 + 2.5
print(type(result), result)   # <class 'float'> 5.5

# int + complex → complex
result = 3 + (1+2j)
print(type(result), result)   # <class 'complex'> (4+2j)

# bool 是 int 的子类
print(True + 1)               # 2 — True 被视为 1
print(False * 5)              # 0 — False 被视为 0
print(True + False)           # 1
```

### 6.2 显式类型转换（Explicit）

```python
# int() — 转为整数
print(int(3.14))        # 3 — 截断取整（不四舍五入）
print(int("42"))        # 42
print(int("0xFF", 16))  # 255 — 指定进制
print(int(True))        # 1

# float() — 转为浮点数
print(float(3))         # 3.0
print(float("3.14"))    # 3.14
print(float("nan"))     # nan
print(float("inf"))     # inf

# complex() — 转为复数
print(complex(3))       # (3+0j)
print(complex(3, 4))    # (3+4j)
print(complex("3+4j"))  # (3+4j)

# bool() — 转为布尔值
print(bool(0))          # False
print(bool(0.0))        # False
print(bool(42))         # True
print(bool(""))         # False
print(bool("hello"))    # True
```

### 6.3 常见转换陷阱

```python
# 陷阱 1：int() 对浮点数截断而非四舍五入
print(int(3.9))             # 3 — 直接砍掉小数部分
print(int(-3.9))            # -3 — 向零取整
print(round(3.5))           # 4 — round() 银行家舍入
print(round(4.5))           # 4 — 银行家舍入：偶数时舍去

# 陷阱 2：字符串转数字可能失败
try:
    value = int("3.14")     # ValueError ！
except ValueError:
    value = float("3.14")   # 先转 float 再转 int
    value = int(value)
print(value)                # 3

# 陷阱 3：布尔值参与算术
count = True + True + True
print(count)                # 3 — 可能不是你想要的结果
print(type(True))           # <class 'bool'>
print(isinstance(True, int))  # True — bool 是 int 的子类！
```

### 6.4 安全转换最佳实践

```python
def safe_int(value, default=0):
    """安全地将输入转为整数，转换失败返回默认值"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value, default=0.0):
    """安全地将输入转为浮点数"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

# 使用示例
print(safe_int("42"))           # 42
print(safe_int("not a number")) # 0
print(safe_int(None))           # 0
print(safe_float("3.14"))       # 3.14
```

---

## 七、实战：科学计算器

> 综合运用所有知识，构建一个支持多种数学运算的科学计算器。

```python
"""
科学计算器 — 实战案例
综合应用：数字类型、位运算、类型转换、运算符优先级
"""

import math
import sys


def show_menu():
    """显示主菜单"""
    print("\n" + "=" * 50)
    print("            🧮  Python 科学计算器")
    print("=" * 50)
    print("基础运算:  1)加法  2)减法  3)乘法  4)除法")
    print("          5)整除  6)取余  7)幂运算")
    print("科学运算:  8)平方根  9)三角函数  10)对数")
    print("位运算:   11)位与  12)位或  13)位异或  14)左移  15)右移")
    print("工具:     16)进制转换  17)浮点分析  18)检查素数")
    print("          0)退出")
    print("=" * 50)


def get_number(prompt="请输入一个数: ", num_type=float):
    """安全获取数字输入"""
    while True:
        try:
            return num_type(input(prompt))
        except (ValueError, TypeError):
            print("❌ 输入无效，请重新输入。")


def get_two_numbers():
    """获取两个操作数"""
    a = get_number("第一个数: ")
    b = get_number("第二个数: ")
    return a, b


def basic_operations():
    """基础四则运算"""
    a, b = get_two_numbers()
    print(f"\n结果:")
    print(f"  {a} + {b} = {a + b}")
    print(f"  {a} - {b} = {a - b}")
    print(f"  {a} * {b} = {a * b}")
    if b != 0:
        print(f"  {a} / {b} = {a / b}")
        print(f"  {a} // {b} = {a // b}")
        print(f"  {a} % {b} = {a % b}")
    else:
        print(f"  {a} / {b} = 错误：除数不能为零")
        print(f"  {a} // {b} = 错误：除数不能为零")
        print(f"  {a} % {b} = 错误：除数不能为零")
    print(f"  {a} ** {b} = {a ** b}")


def scientific_operations():
    """科学运算"""
    choice = input("请选择 (8=平方根, 9=三角函数, 10=对数): ").strip()
    
    if choice == "8":
        n = get_number("输入数值: ")
        if n < 0:
            print(f"  √{n} = {cmath.sqrt(n)} (复数结果)")
        else:
            print(f"  √{n} = {math.sqrt(n)}")
    elif choice == "9":
        x = get_number("输入角度(度): ")
        rad = math.radians(x)
        print(f"  sin({x}°) = {math.sin(rad):.6f}")
        print(f"  cos({x}°) = {math.cos(rad):.6f}")
        print(f"  tan({x}°) = {math.tan(rad):.6f}")
    elif choice == "10":
        n = get_number("输入数值: ")
        if n <= 0:
            print("❌ 对数要求正数。")
        else:
            base = get_number("底数(默认 e，输入 0 则用 e): ")
            if base == 0:
                print(f"  ln({n}) = {math.log(n):.6f}")
            else:
                print(f"  log_{base}({n}) = {math.log(n, base):.6f}")
    else:
        print("❌ 无效选项。")


def bitwise_operations():
    """位运算"""
    a = get_number("第一个整数: ", int)
    b = get_number("第二个整数: ", int)
    
    print(f"\n  {a} 的二进制: {bin(a)}")
    print(f"  {b} 的二进制: {bin(b)}")
    print(f"\n  {a} & {b} = {a & b}  ({bin(a & b)})")
    print(f"  {a} | {b} = {a | b}  ({bin(a | b)})")
    print(f"  {a} ^ {b} = {a ^ b}  ({bin(a ^ b)})")
    print(f"  {a} << 1 = {a << 1}  (×2)")
    print(f"  {a} >> 1 = {a >> 1}  (÷2)")


def conversion_tools():
    """进制转换工具"""
    n = get_number("输入一个整数: ", int)
    print(f"\n  十进制: {n}")
    print(f"  二进制: {bin(n)}")
    print(f"  八进制: {oct(n)}")
    print(f"  十六进制: {hex(n)}")
    print(f"  二进制位数: {n.bit_length()} bits")
    print(f"  字节表示(big): {n.to_bytes((n.bit_length() + 7) // 8, 'big')}")


def float_analysis():
    """浮点数分析工具"""
    n = get_number("输入一个数: ")
    if isinstance(n, float) or isinstance(n, int):
        f = float(n)
        ratio = f.as_integer_ratio()
        print(f"\n  {f} 的精确分数: {ratio[0]}/{ratio[1]}")
        print(f"  是否为整数: {f.is_integer()}")
        print(f"  十六进制表示: {f.hex()}")
        
        # 演示精度问题
        if abs(f - 0.1) < 1e-10 or abs(f - 0.2) < 1e-10:
            print(f"\n  ⚠️ 提示: {f} 在二进制中无法精确表示")
            print(f"  例如: 0.1 + 0.2 = {0.1 + 0.2}")
    else:
        print("输入不是数值类型。")


def is_prime(n: int) -> bool:
    """检查素数"""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    # 只需要检查到 √n
    limit = int(math.sqrt(n)) + 1
    for i in range(3, limit, 2):
        if n % i == 0:
            return False
    return True


def prime_check():
    """素数检查工具"""
    n = get_number("输入一个正整数: ", int)
    if n <= 0:
        print("❌ 请输入正整数。")
        return
    
    result = is_prime(n)
    if result:
        print(f"\n  ✅ {n} 是素数!")
    else:
        print(f"\n  ❌ {n} 不是素数")
        # 找到最小因子
        for i in range(2, int(math.sqrt(n)) + 1):
            if n % i == 0:
                print(f"  {n} = {i} × {n // i}")
                break


def main():
    """主程序"""
    import cmath  # 复数支持
    
    print("\n欢迎使用 Python 科学计算器！")
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"当前阶段: 学习数字与运算的实战应用")
    
    while True:
        show_menu()
        choice = input("\n请选择功能 (0-18): ").strip()
        
        if choice == "0":
            print("\n感谢使用，再见！👋")
            break
        elif choice == "1":
            basic_operations()
        elif choice == "8":
            scientific_operations()
        elif choice in ("11", "12", "13", "14", "15"):
            bitwise_operations()
        elif choice == "16":
            conversion_tools()
        elif choice == "17":
            float_analysis()
        elif choice == "18":
            prime_check()
        else:
            basic_operations()


if __name__ == "__main__":
    main()
```

---

## 💭 思考题

1. **精度与性能**：Python 的任意精度整数在什么情况下会显著慢于 C 语言的固定位数整数？写一个基准测试验证你的猜想。

2. **浮点数之谜**：为什么 `0.1 + 0.2 != 0.3`，但 `0.5 + 0.25 == 0.75` 却没有精度问题？哪些小数在二进制中可以精确表示？

3. **位运算威力**：不用 `*` 和 `/`，仅用位运算实现一个整数乘以 10 的函数。提示：`n * 10 = n * (8 + 2) = n * 8 + n * 2 = (n << 3) + (n << 1)`

4. **隐式转换的风险**：写出一个利用布尔值是整数子类的"bug"代码——即因为 `True` 被当作 `1` 而导致逻辑错误的场景。

5. **复数应用**：创建一个复数类，模拟 Mandelbrot 集合的迭代计算：`z = z² + c`。对于初始值 c，如果迭代 100 次后 `|z| < 2`，则 c 属于集合。

---

## 📚 扩展阅读

- [Python 文档: 数字类型](https://docs.python.org/zh-cn/3/library/stdtypes.html#numeric-types-int-float-complex)
- [IEEE 754 标准详解](https://en.wikipedia.org/wiki/IEEE_754)
- [What Every Computer Scientist Should Know About Floating-Point Arithmetic](https://docs.oracle.com/cd/E19957-01/806-3568/ncg_goldberg.html)
- [Python 位运算技巧](https://wiki.python.org/moin/BitwiseOperators)
