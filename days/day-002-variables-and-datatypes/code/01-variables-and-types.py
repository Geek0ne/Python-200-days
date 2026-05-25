#!/usr/bin/env python3
"""
Day 002 — 变量与数据类型基础示例
==============================

覆盖：变量定义、命名规则、基本数据类型、type()、id()
直接运行：python3 01-variables-and-types.py
"""

import sys

print("=" * 60)
print("📦 01 — 变量基础与数据类型")
print("=" * 60)


# ============================================================
# 1. 变量定义与赋值
# ============================================================
print("\n" + "=" * 60)
print("1️⃣  变量定义与赋值")
print("=" * 60)

# 基本赋值
name = "Alice"       # 字符串
age = 25             # 整数
height = 1.68        # 浮点数
is_student = True    # 布尔值
middle_name = None   # 空值

print(f"name        = {name}")
print(f"age         = {age}")
print(f"height      = {height}")
print(f"is_student  = {is_student}")
print(f"middle_name = {middle_name}")

# Python 的"标签"机制演示
print("\n🎯 标签机制演示：")
x = 10
print(f"x = {x}, id(x) = {id(x)}")

y = x  # y 现在指向同一个对象
print(f"y = x → y = {y}, id(y) = {id(y)}")

x = 20  # x 指向新对象，y 仍指向旧对象
print(f"x = 20 → x = {x}, id(x) = {id(x)}")
print(f"y 仍然 = {y}, id(y) = {id(y)}")
print("✅ 结论：y 并没有变成 20，因为变量是标签不是盒子")


# ============================================================
# 2. 命名规则演示
# ============================================================
print("\n" + "=" * 60)
print("2️⃣  命名规则演示")
print("=" * 60)

# ✅ 合法命名
user_name = "Alice"
_user_id = 42
user2 = "Bob"
camelCaseName = "Charlie"  # 合法但不推荐
MY_CONSTANT = 3.14159

print(f"user_name      = {user_name}")
print(f"_user_id       = {_user_id}")
print(f"user2          = {user2}")
print(f"MY_CONSTANT    = {MY_CONSTANT}")

# 变量重绑定（动态类型）
print("\n🎭 动态类型演示：")
value = 42
print(f"value = {value}, type = {type(value).__name__}")
value = "Hello, Python!"
print(f"value = {value}, type = {type(value).__name__}")
value = 3.14
print(f"value = {value}, type = {type(value).__name__}")
value = True
print(f"value = {value}, type = {type(value).__name__}")
value = None
print(f"value = {value}, type = {type(value).__name__}")


# ============================================================
# 3. 基本数据类型详解
# ============================================================
print("\n" + "=" * 60)
print("3️⃣  基本数据类型详解")
print("=" * 60)

# 3a. int — 整数
print("\n--- int 整数 ---")
a = 42
b = 0b101010  # 二进制
c = 0o52      # 八进制
d = 0x2A      # 十六进制
e = 1_000_000  # 带下划线的可读形式

print(f"十进制:    a = {a}")
print(f"二进制: 0b101010 = {b}")
print(f"八进制:   0o52 = {c}")
print(f"十六进制: 0x2A = {d}")
print(f"下划线:  1_000_000 = {e}")

# 任意精度整数
big = 2 ** 200
print(f"\n2^200 = {big}")
print(f"位数: {len(str(big))} 位数字")

# 3b. float — 浮点数
print("\n--- float 浮点数 ---")
pi = 3.141592653589793
scientific = 1.5e-4  # = 0.00015
inf = float('inf')
neg_inf = float('-inf')
nan = float('nan')

print(f"pi = {pi}")
print(f"1.5e-4 = {scientific}")
print(f"正无穷 = {inf}")
print(f"负无穷 = {neg_inf}")
print(f"非数字 = {nan}")

# 浮点数精度问题
print("\n⚠️  浮点数精度问题：")
print(f"0.1 + 0.2 = {0.1 + 0.2}")
print(f"期望值 = 0.3")
print(f"相等吗？{0.1 + 0.2 == 0.3}")
print(f"差异 = {(0.1 + 0.2) - 0.3}")

# 3c. str — 字符串
print("\n--- str 字符串 ---")
s1 = "Hello"
s2 = 'World'
s3 = """多行
字符串
示例"""

print(f"s1 = '{s1}'")
print(f"s2 = '{s2}'")
print(f"s3 = '''{s3}'''")
print(f"s1 + ' ' + s2 = '{s1 + ' ' + s2}'")
print(f"'Ha' * 3 = '{"Ha" * 3}'")
print(f"len('{s1}') = {len(s1)}")
print(f"'{s1}'[0] = '{s1[0]}'")
print(f"'{s1}'[-1] = '{s1[-1]}'")

# 字符串不可变性
print("\n🔒 字符串不可变性：")
original = "Python"
# original[0] = "J"  # ❌ 这会引发 TypeError
modified = "J" + original[1:]
print(f"original = '{original}'")
print(f"modified = '{modified}' (创建了新字符串)")

# 3d. bool — 布尔值
print("\n--- bool 布尔值 ---")
print(f"True = {True}")
print(f"False = {False}")
print(f"type(True) = {type(True)}")
print(f"True + True = {True + True}")
print(f"True * 10 = {True * 10}")
print(f"isinstance(True, int) = {isinstance(True, int)}")

# 3e. None — 空值
print("\n--- None 空值 ---")
result = None
print(f"result = {result}")
print(f"type(None) = {type(None)}")
print(f"None is None = {None is None}")
print(f"None == False = {None == False}")
print(f"None == 0 = {None == 0}")
print(f"None == '' = {None == ''}")


# ============================================================
# 4. type() 与 id() 函数详解
# ============================================================
print("\n" + "=" * 60)
print("4️⃣  type() 与 id() 函数")
print("=" * 60)

# type() 演示
print("\n--- type() 函数 ---")
values = [42, 3.14, "Hello", True, None, [1, 2, 3]]
for v in values:
    print(f"type({v!r:12}) = {type(v)}")

# id() 演示
print("\n--- id() 函数 ---")
a = 42
b = 42
c = 1000
d = 1000

print(f"a = {a}, id(a) = {id(a)}")
print(f"b = {b}, id(b) = {id(b)}")
print(f"a is b? {a is b}  (小整数驻留)")
print(f"c = {c}, id(c) = {id(c)}")
print(f"d = {d}, id(d) = {id(d)}")
print(f"c is d? {c is d}  (大整数不驻留)")

# 重新绑定后 id 变化
print("\n--- 赋值后 id 变化 ---")
x = [1, 2, 3]
print(f"x = {x}, id(x) = {id(x)}")
x.append(4)
print(f"x.append(4) → {x}, id(x) = {id(x)} (⚠️ 可变对象 id 不变！)")


# ============================================================
# 5. 类型转换
# ============================================================
print("\n" + "=" * 60)
print("5️⃣  类型转换")
print("=" * 60)

# 显式转换
print("\n--- 显式转换 ---")
print(f"int('42')     = {int('42')}")
print(f"float('3.14') = {float('3.14')}")
print(f"str(100)      = '{str(100)}'")
print(f"bool(1)       = {bool(1)}")
print(f"bool(0)       = {bool(0)}")
print(f"bool('')      = {bool('')}")
print(f"bool('Hello') = {bool('Hello')}")
print(f"bool(None)    = {bool(None)}")

# 隐式转换
print("\n--- 隐式转换 ---")
result = 10 + 3.14
print(f"10 + 3.14 = {result} (type: {type(result).__name__})")
result = True + 5
print(f"True + 5   = {result} (type: {type(result).__name__})")


# ============================================================
# 6. 基本运算符
# ============================================================
print("\n" + "=" * 60)
print("6️⃣  基本运算符")
print("=" * 60)

a, b = 10, 3
print(f"a = {a}, b = {b}")
print(f"a + b  = {a + b}   (加法)")
print(f"a - b  = {a - b}   (减法)")
print(f"a * b  = {a * b}   (乘法)")
print(f"a / b  = {a / b}   (除法，结果是 float)")
print(f"a // b = {a // b}  (整除，向下取整)")
print(f"a % b  = {a % b}   (取余)")
print(f"a ** b = {a ** b}  (幂运算)")

# 增强赋值
x = 5
print(f"\n增强赋值演示：初始 x = {x}")
x += 3
print(f"x += 3  → x = {x}")
x -= 2
print(f"x -= 2  → x = {x}")
x *= 4
print(f"x *= 4  → x = {x}")
x /= 3
print(f"x /= 3  → x = {x}")


# ============================================================
# 7. 综合小实验：探索 Python 对象
# ============================================================
print("\n" + "=" * 60)
print("7️⃣  综合实验：探索 Python 对象内存模型")
print("=" * 60)

def explore_object(obj, label="对象"):
    """显示一个 Python 对象的详细信息"""
    print(f"\n📌 {label}:")
    print(f"   值      = {obj!r}")
    print(f"   类型    = {type(obj)}")
    print(f"   身份 id = {id(obj)}")
    print(f"   是 bool? {isinstance(obj, bool)}")
    print(f"   是 int?  {isinstance(obj, int)}")
    print(f"   是 str?  {isinstance(obj, str)}")
    print(f"   是 float? {isinstance(obj, float)}")

explore_object(42, "整数 42")
explore_object(3.14, "浮点数 3.14")
explore_object("Python", "字符串 'Python'")
explore_object(True, "布尔值 True")
explore_object(None, "空值 None")

print("\n✅ 所有示例执行完毕！")
print("=" * 60)
