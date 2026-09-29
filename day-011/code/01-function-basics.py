#!/usr/bin/env python3
"""
01-function-basics.py
Python 函数基础 —— 完整示例集合

本文件演示函数的定义、调用、参数传递、返回值等核心概念，
所有代码均可直接运行。

运行: python3 01-function-basics.py
"""

import sys

# ============================================================
# 1. 函数定义与调用的多种形式
# ============================================================

print("=" * 70)
print("📌 1. 函数定义与调用")
print("=" * 70)


# --- 1.1 无参数、无返回值的函数 ---
def say_hello():
    """最简单的函数：打印问候语。"""
    print("你好！欢迎学习 Python 函数！")


print("\n--- 1.1 无参数函数 ---")
say_hello()


# --- 1.2 带参数的函数 ---
def greet(name):
    """带一个参数的函数。"""
    print(f"你好，{name}！")


def introduce(name, age, city):
    """带多个参数的函数。"""
    print(f"我叫{name}，今年{age}岁，来自{city}")


print("\n--- 1.2 带参数的函数 ---")
greet("张三")
introduce("李四", 30, "上海")


# --- 1.3 带返回值的函数 ---
def add(a, b):
    """返回两个数的和。"""
    return a + b


def is_even(n):
    """判断一个数是否为偶数。"""
    return n % 2 == 0


print("\n--- 1.3 带返回值的函数 ---")
result = add(10, 20)
print(f"10 + 20 = {result}")
print(f"7 是偶数吗？ {is_even(7)}")
print(f"8 是偶数吗？ {is_even(8)}")


# --- 1.4 返回多个值的函数（实际返回元组） ---
def min_max_avg(numbers):
    """
    返回列表中的最小值、最大值和平均值。

    返回值本质上是一个元组 (min, max, avg)，
    Python 会自动打包。
    """
    return min(numbers), max(numbers), sum(numbers) / len(numbers)


print("\n--- 1.4 返回多个值 ---")
scores = [85, 92, 78, 95, 88, 76, 91]
low, high, avg = min_max_avg(scores)
print(f"成绩列表: {scores}")
print(f"最低分: {low}")
print(f"最高分: {high}")
print(f"平均分: {avg:.1f}")

# 也可以直接接收元组
result_tuple = min_max_avg(scores)
print(f"返回类型: {type(result_tuple)}  ← 元组")
print(f"完整结果: {result_tuple}")


# --- 1.5 提前 return 退出函数 ---
def classify_age(age):
    """
    根据年龄分类。

    return 可以用于提前退出函数。
    """
    if age < 0:
        return "无效年龄"  # 提前返回
    if age < 18:
        return "未成年人"
    if age < 60:
        return "成年人"
    return "老年人"


print("\n--- 1.5 提前 return ---")
for age in [-5, 15, 25, 65]:
    print(f"{age}岁: {classify_age(age)}")


# --- 1.6 没有 return 的函数返回 None ---
def just_print(msg):
    """这个函数只有 print，没有 return。"""
    print(f"消息: {msg}")
    # 没有 return 语句
    # 等价于: return None


print("\n--- 1.6 隐式 None ---")
r = just_print("你好")
print(f"just_print 的返回值: {r}")
print(f"返回值是 None 吗？ {r is None}")


# ============================================================
# 2. 参数传递机制（值传递 vs 引用传递）
# ============================================================

print("\n" + "=" * 70)
print("📌 2. 参数传递机制")
print("=" * 70)


# --- 2.1 不可变类型（int, str, tuple）—— "值传递" 错觉 ---
def try_change_int(x):
    """尝试修改整数参数——不会影响外部。"""
    print(f"  接收到的 x = {x}, id = {id(x)}")
    x = 100  # 重新绑定到新对象
    print(f"  修改后 x = {x}, id = {id(x)}")
    # 注意: x 指向了新的对象，原来的对象没变


print("\n--- 2.1 不可变类型参数 ---")
n = 5
print(f"调用前: n = {n}, id = {id(n)}")
try_change_int(n)
print(f"调用后: n = {n}, id = {id(n)}  ← 没变！")


# --- 2.2 可变类型（list, dict, set）—— 修改内容会影响外部 ---
def add_element(lst):
    """往列表中添加元素——会影响外部。"""
    print(f"  接收到的 lst = {lst}, id = {id(lst)}")
    lst.append(999)  # 修改对象内容
    print(f"  修改后 lst = {lst}")


print("\n--- 2.2 可变类型参数（修改内容） ---")
my_list = [1, 2, 3]
print(f"调用前: my_list = {my_list}, id = {id(my_list)}")
add_element(my_list)
print(f"调用后: my_list = {my_list}, id = {id(my_list)}  ← 变了！")


# --- 2.3 重新绑定 vs 修改对象 ---
def rebind(lst):
    """重新绑定——不会影响外部。"""
    lst = [100, 200, 300]  # ← 指向新对象
    print(f"  重新绑定后: lst = {lst}")


def mutate(lst):
    """修改对象内容——会影响外部。"""
    lst.append(999)
    lst[0] = 999


print("\n--- 2.3 重新绑定 vs 修改对象 ---")
original = [1, 2, 3]
print(f"原始列表: {original}")

rebind(original)
print(f"rebind 后: {original}  ← 没变")

mutate(original)
print(f"mutate 后: {original}  ← 变了")


# --- 2.4 如何避免意外修改 ---
def process_data_bad(data):
    """错误方式：意外修改外部数据。"""
    data.append(99)  # 添加元素（和数据类型一致）
    data.sort()
    return data


def process_data_good(data):
    """
    正确方式：先拷贝再操作。

    使用 data[:] 或 data.copy() 创建副本。
    """
    data = data[:]  # 创建副本
    data.append(99)
    data.sort()
    return data


print("\n--- 2.4 避免意外修改 ---")
original_data = [3, 1, 4, 1, 5]
print(f"原始数据: {original_data}")

result_bad = process_data_bad(original_data)
print(f"错误方式处理后的数据: {result_bad}")
print(f"原始数据被修改了: {original_data}  ← 影响外部")

# 重新准备
original_data = [3, 1, 4, 1, 5]
result_good = process_data_good(original_data)
print(f"正确方式处理后的数据: {result_good}")
print(f"原始数据没变: {original_data}  ← 安全")


# ============================================================
# 3. 返回值详解
# ============================================================

print("\n" + "=" * 70)
print("📌 3. 返回值详解")
print("=" * 70)


# --- 3.1 返回 None 的几种情况 ---
def return_none_explicit():
    """显式返回 None。"""
    return None


def return_none_implicit():
    """没有 return 语句。"""
    pass


def return_none_empty():
    """return 后不跟值。"""
    return


print("\n--- 3.1 None 的多种返回方式 ---")
print(f"显式 None:  {return_none_explicit()}")
print(f"隐式 None:  {return_none_implicit()}")
print(f"空 return:  {return_none_empty()}")


# --- 3.2 返回复杂数据结构 ---
def get_student_record(student_id):
    """
    返回一个包含学生信息的字典。

    演示函数可以返回任意 Python 对象。
    """
    # 模拟数据库
    records = {
        1: {"name": "张三", "age": 20, "scores": {"math": 95, "english": 88}},
        2: {"name": "李四", "age": 21, "scores": {"math": 78, "english": 92}},
    }
    return records.get(student_id, None)


print("\n--- 3.2 返回复杂数据结构 ---")
student = get_student_record(1)
if student is not None:  # ✅ 正确检查 None 的方式
    print(f"学生: {student['name']}")
    print(f"数学成绩: {student['scores']['math']}")
else:
    print("未找到该学生")

not_found = get_student_record(999)
print(f"查找不存在的学生: {not_found}")


# --- 3.3 条件返回不同的类型（Python 动态类型特性） ---
def flex_return(value):
    """
    根据输入返回不同类型。

    虽然灵活，但生产代码中不建议这样用——
    保持返回类型一致更可读。
    """
    if isinstance(value, int):
        return value * 2
    elif isinstance(value, str):
        return value.upper()
    elif isinstance(value, list):
        return len(value)
    else:
        return None


print("\n--- 3.3 动态返回类型 ---")
print(f"flex_return(5)      = {flex_return(5)}      (int)")
print(f"flex_return('hi')   = {flex_return('hi')}   (str)")
print(f"flex_return([1,2,3])= {flex_return([1,2,3])} (int — 长度)")


# ============================================================
# 4. 文档字符串（docstring）实战
# ============================================================

print("\n" + "=" * 70)
print("📌 4. 文档字符串实战")
print("=" * 70)


def calculate_bmi(weight_kg, height_m):
    """
    计算身体质量指数（BMI）。

    根据世界卫生组织（WHO）的标准公式计算 BMI 值。

    Args:
        weight_kg (float): 体重，单位公斤（kg）
        height_m (float):  身高，单位米（m）

    Returns:
        float: BMI 值，计算公式为 weight_kg / (height_m ** 2)

    Example:
        >>> calculate_bmi(70, 1.75)
        22.857142857142858
    """
    if height_m <= 0:
        return float('inf')
    return weight_kg / (height_m ** 2)


def bmi_category(bmi):
    """
    根据 BMI 值返回体重分类。

    BMI 分类标准（WHO 亚太地区参考）：
        - < 18.5:   偏瘦
        - 18.5-24.9: 正常
        - 25.0-29.9: 偏胖
        - >= 30:     肥胖

    Args:
        bmi (float): BMI 值

    Returns:
        str: 体重分类名称
    """
    if bmi < 18.5:
        return "偏瘦"
    elif bmi < 25:
        return "正常"
    elif bmi < 30:
        return "偏胖"
    else:
        return "肥胖"


print("\n--- 4.1 使用 help() 查看文档 ---")
# 取消下面一行的注释来查看 help() 输出:
# help(calculate_bmi)

print("__doc__ 属性内容:")
print(calculate_bmi.__doc__)


print("\n--- 4.2 实际使用 ---")
# 计算几个人的 BMI
people = [
    ("张三", 70, 1.75),
    ("李四", 85, 1.72),
    ("王五", 55, 1.68),
    ("赵六", 95, 1.80),
]

print("姓名   体重(kg)  身高(m)  BMI     分类")
print("-" * 50)
for name, weight, height in people:
    bmi = calculate_bmi(weight, height)
    category = bmi_category(bmi)
    print(f"{name}  {weight:^8}  {height:.2f}    {bmi:.1f}   {category}")


# ============================================================
# 5. 函数是一等公民 —— 高级概念展示
# ============================================================

print("\n" + "=" * 70)
print("📌 5. 函数是一等公民（First-class Citizen）")
print("=" * 70)


# --- 5.1 函数可以赋值给变量 ---
def square(x):
    """计算 x 的平方。"""
    return x * x


print("\n--- 5.1 函数赋值给变量 ---")
f = square  # f 现在指向 square 函数
print(f"square(5) = {square(5)}")
print(f"f(5) = {f(5)}")  # 和上面一样
print(f"f 的类型: {type(f)}")
print(f"f 就是 square? {f is square}")


# --- 5.2 函数作为参数传递 ---
def apply_twice(func, value):
    """
    对 value 应用两次 func。
    演示函数作为参数传递。
    """
    return func(func(value))


print("\n--- 5.2 函数作为参数 ---")
result = apply_twice(square, 2)
print(f"apply_twice(square, 2) = {result}  ← 先 2²=4, 再 4²=16")


# --- 5.3 函数列表 ---
def double(x):
    return x * 2

def triple(x):
    return x * 3

def halve(x):
    return x / 2


operations = [double, triple, halve, square]
print("\n--- 5.3 函数列表 ---")
x = 10
for op in operations:
    print(f"{op.__name__}({x}) = {op(x)}")


# --- 5.4 内省 —— 检查函数属性 ---
print("\n--- 5.4 函数内省（Introspection） ---")


def sample_func(a, b, c=3):
    """这是一个示例函数。"""
    return a + b + c


print(f"函数名:         {sample_func.__name__}")
print(f"文档字符串:     {repr(sample_func.__doc__)}")
print(f"模块:           {sample_func.__module__}")
print(f"默认参数:       {sample_func.__defaults__}")
print(f"代码对象:       {type(sample_func.__code__)}")
print(f"参数数量:       {sample_func.__code__.co_argcount}")
print(f"局部变量名:     {sample_func.__code__.co_varnames}")


# ============================================================
# 6. 常见错误与最佳实践
# ============================================================

print("\n" + "=" * 70)
print("📌 6. 常见错误与最佳实践")
print("=" * 70)


# --- 错误 1: 忘记 return ---
def bad_average(numbers):
    """❌ 忘记 return 了！"""
    total = sum(numbers)
    avg = total / len(numbers)
    # 忘记写 return avg


def good_average(numbers):
    """✅ 正确返回。"""
    return sum(numbers) / len(numbers)


print("\n--- 错误 1: 忘记 return ---")
result_bad = bad_average([1, 2, 3, 4, 5])
result_good = good_average([1, 2, 3, 4, 5])
print(f"忘记 return: {result_bad}  ← 得到 None!")
print(f"正确 return: {result_good}")


# --- 错误 2: 在函数内部意外修改全局变量（后面 Day 13 会详细讲） ---
total = 0  # 全局变量


def add_to_total_bad(x):
    """❌ 错误方式：试图直接修改全局变量。"""
    # total += x  # 这行会报 UnboundLocalError！
    pass


def add_to_total_good(x):
    """✅ 正确方式：使用参数和返回值。"""
    return total + x  # 读取全局变量不修改，这是可以的


# --- 错误 3: 可变默认参数（Day 12 会详细讲） ---
def add_student_bad(name, class_list=[]):
    """❌ 不要用可变对象作为默认参数！"""
    class_list.append(name)
    return class_list


print("\n--- 错误 3: 可变默认参数 ---")
print(f"第一次: {add_student_bad('张三')}")  # ['张三']
print(f"第二次: {add_student_bad('李四')}")  # ['张三', '李四'] ← 不是预期的 ['李四']！
print(f"默认参数是同一个对象: {add_student_bad.__defaults__[0]}")


def add_student_good(name, class_list=None):
    """✅ 正确方式：用 None 作为默认值。"""
    if class_list is None:
        class_list = []
    class_list.append(name)
    return class_list


print(f"正确方式: {add_student_good('张三')}")
print(f"正确方式: {add_student_good('李四')}")


# ============================================================
# 7. 函数调用过程可视化（模拟栈帧）
# ============================================================

print("\n" + "=" * 70)
print("📌 7. 函数调用栈模拟")
print("=" * 70)


def a(x):
    """函数 a，调用 b。"""
    print(f"  → a({x}) 开始执行, 栈深度: 1")
    result = b(x + 1)
    print(f"  ← a({x}) 结束, 返回: {result}")
    return result


def b(y):
    """函数 b，调用 c。"""
    print(f"    → b({y}) 开始执行, 栈深度: 2")
    result = c(y + 1)
    print(f"    ← b({y}) 结束, 返回: {result}")
    return result


def c(z):
    """函数 c，计算结果。"""
    print(f"      → c({z}) 开始执行, 栈深度: 3")
    result = z * 2
    print(f"      ← c({z}) 结束, 返回: {result}")
    return result


print("\n调用链: main → a(1) → b(2) → c(3)\n")
print("执行过程（从外到内，再从内到外）:")
print("─" * 50)
final = a(1)
print("─" * 50)
print(f"\n最终结果: {final}")

print("\n💡 调用栈执行顺序（LIFO — 后进先出）:")
print("""
    调用栈（时间从上到下）:
    ┌───────────────┐
    │    c(3)       │  ← 最后压入，最先弹出
    ├───────────────┤
    │    b(2)       │
    ├───────────────┤
    │    a(1)       │
    ├───────────────┤
    │  全局作用域    │  ← 最先压入，最后弹出
    └───────────────┘
""")


# ============================================================
# 8. 综合示例：温度转换工具
# ============================================================

print("=" * 70)
print("📌 8. 综合示例：温度转换工具")
print("=" * 70)


def celsius_to_fahrenheit(c):
    """
    摄氏度 → 华氏度转换。
    公式: ℉ = ℃ × 9/5 + 32
    """
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f):
    """
    华氏度 → 摄氏度转换。
    公式: ℃ = (℉ - 32) × 5/9
    """
    return (f - 32) * 5 / 9


def celsius_to_kelvin(c):
    """
    摄氏度 → 开尔文转换。
    公式: K = ℃ + 273.15
    """
    return c + 273.15


def kelvin_to_celsius(k):
    """
    开尔文 → 摄氏度转换。
    公式: ℃ = K - 273.15
    """
    return k - 273.15


def convert_temperature(value, from_unit, to_unit):
    """
    通用温度转换函数。

    Args:
        value (float): 待转换的温度值
        from_unit (str): 来源单位（'C', 'F', 'K'）
        to_unit (str): 目标单位（'C', 'F', 'K'）

    Returns:
        float: 转换后的温度值
    """
    # 先统一转换为摄氏度
    if from_unit.upper() == 'F':
        celsius = fahrenheit_to_celsius(value)
    elif from_unit.upper() == 'K':
        celsius = kelvin_to_celsius(value)
    elif from_unit.upper() == 'C':
        celsius = value
    else:
        raise ValueError(f"不支持的温度单位: {from_unit}")

    # 再从摄氏度转换到目标单位
    if to_unit.upper() == 'C':
        return celsius
    elif to_unit.upper() == 'F':
        return celsius_to_fahrenheit(celsius)
    elif to_unit.upper() == 'K':
        return celsius_to_kelvin(celsius)
    else:
        raise ValueError(f"不支持的温度单位: {to_unit}")


print("\n常见温度值转换:")
print("-" * 60)
conversions = [
    (0, 'C', 'F'),      # 冰点
    (100, 'C', 'F'),    # 沸点
    (32, 'F', 'C'),     # 水的冰点（华氏）
    (212, 'F', 'C'),    # 水的沸点（华氏）
    (0, 'C', 'K'),      # 绝对零度的另一种表示
    (300, 'K', 'C'),    # 室温约 27℃
    (37, 'C', 'F'),     # 人体体温
    (-40, 'C', 'F'),    # 有趣：-40℃ = -40℉
]

for value, from_u, to_u in conversions:
    result = convert_temperature(value, from_u, to_u)
    print(f"  {value:>6.1f}°{from_u}  =  {result:>7.1f}°{to_u}")


print("\n" + "=" * 70)
print("✅ 所有示例运行完毕！")
print("=" * 70)
