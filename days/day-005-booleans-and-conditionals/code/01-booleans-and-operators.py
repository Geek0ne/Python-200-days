"""
Day 005 — 布尔值与条件判断：基础示例
======================================================================
本文件演示 Python 布尔值、比较运算、逻辑运算和条件判断的核心概念。
可直接运行: python3 01-booleans-and-operators.py
"""

import dis
import sys


# =====================================================================
# 第一部分：布尔类型基础
# =====================================================================

def part1_boolean_basics():
    """布尔类型本质：bool 是 int 的子类"""
    print("=" * 70)
    print("🔷 第一部分：布尔类型 (bool) 基础")
    print("=" * 70)

    # 1. bool 是 int 的子类
    print("\n1. bool 是 int 的子类:")
    print(f"   issubclass(bool, int) = {issubclass(bool, int)}")
    print(f"   isinstance(True, int)  = {isinstance(True, int)}")

    # 2. 布尔值的整数行为
    print("\n2. 布尔值参与数学运算:")
    print(f"   True + True     = {True + True}")        # 2
    print(f"   True * 10      = {True * 10}")            # 10
    print(f"   False * 100    = {False * 100}")          # 0
    print(f"   (True + False) * 5 = {(True + False) * 5}")  # 5
    print(f"   True > False   = {True > False}")         # True

    # 3. True/False 作为列表索引（利用 1/0）
    print("\n3. 利用布尔值做索引:")
    items = ["假", "真"]
    print(f"   items[False] = {items[False]}")   # "假"
    print(f"   items[True]  = {items[True]}")    # "真"

    # 4. == 与 is 的区别
    print("\n4. == 与 is 的区别:")
    a, b = 256, 256
    print(f"   a = 256, b = 256")
    print(f"   a == b: {a == b}")    # True — 值相等
    print(f"   a is b: {a is b}")    # True — 小整数缓存

    c, d = 257, 257
    print(f"\n   c = 257, d = 257")
    print(f"   c == d: {c == d}")    # True — 值相等
    print(f"   c is d: {c is d}")    # False — 超出缓存范围


# =====================================================================
# 第二部分：Truthy 与 Falsy 值
# =====================================================================

def part2_truthy_falsy():
    """演示 Truthy / Falsy 值的判断规则"""
    print("\n" + "=" * 70)
    print("🔷 第二部分：Truthy 与 Falsy 值")
    print("=" * 70)

    # 1. Falsy 值一览
    print("\n1. 所有 Falsy 值:")
    falsy_values = [False, None, 0, 0.0, 0j, "", [], (), {}, set(), range(0)]

    for val in falsy_values:
        print(f"   bool({val!r:15s}) = {bool(val)}")

    # 2. 常见 Truthy 值
    print("\n2. 一些 Truthy 值:")
    truthy_values = [True, 1, -1, 3.14, " ", [0], (None,), {"key": False}, "False"]
    for val in truthy_values:
        print(f"   bool({val!r:15s}) = {bool(val)}")

    # 3. 实战：利用 Truthy/Falsy 简化代码
    print("\n3. Truthy/Falsy 的实用场景:")

    # 场景 1：检查空列表
    items = []
    # 传统写法（其他语言风格）
    if len(items) > 0:
        print("   [传统] 列表非空")
    else:
        print("   [传统] 列表为空")

    # Pythonic 写法
    if items:
        print("   [Pythonic] 列表非空")
    else:
        print("   [Pythonic] 列表为空")  # 这行会执行

    # 场景 2：检查 None
    user_input = None
    # 注意：if not user_input 会把 0/False 也排除
    # 所以检查 None 推荐用 is None
    if user_input is None:
        print("   ✅ 用户输入为 None（明确检查）")

    # 场景 3：空字符串回退
    name = "" or "匿名用户"
    print(f"   空字符串回退: {name}")  # 匿名用户

    # 场景 4：自定义对象
    class CustomContainer:
        def __init__(self, items):
            self.items = items
        def __len__(self):
            print(f"     调用了 __len__(): {len(self.items)}")
            return len(self.items)
        def __bool__(self):
            print(f"     调用了 __bool__(): {bool(self.items)}")
            return bool(self.items)

    print("\n4. 自定义对象的真假判断（__bool__ vs __len__）:")
    container1 = CustomContainer([1, 2, 3])
    if container1:  # 优先调用 __bool__
        print("   container1 被视为 True")

    container2 = CustomContainer([])
    if not container2:
        print("   container2 被视为 False（因为列表为空）")


# =====================================================================
# 第三部分：比较运算符
# =====================================================================

def part3_comparison_operators():
    """演示各种比较运算符"""
    print("\n" + "=" * 70)
    print("🔷 第三部分：比较运算符")
    print("=" * 70)

    a, b = 10, 20

    print("\n1. 基本比较:")
    print(f"   {a} == {b} : {a == b}")
    print(f"   {a} != {b} : {a != b}")
    print(f"   {a} <  {b} : {a < b}")
    print(f"   {a} >  {b} : {a > b}")
    print(f"   {a} <= {b} : {a <= b}")
    print(f"   {a} >= {b} : {a >= b}")

    # 2. 链式比较
    print("\n2. 链式比较（Python 特色）:")
    x = 5
    print(f"   x = {x}")
    print(f"   3 < x < 10     : {3 < x < 10}")    # True
    print(f"   1 < x < 4      : {1 < x < 4}")     # False
    print(f"   0 < 1 < 2 < 3  : {0 < 1 < 2 < 3}")  # True

    # 链式比较 vs and 写法
    print("\n   链式比较的本质:")
    print(f"   3 < x < 10 等价于 (3 < x) and (x < 10)")
    print(f"   结果: {(3 < x) and (x < 10)}")  # True

    # 3. 字符串比较
    print("\n3. 字符串比较（按字典序）:")
    print(f"   'apple' < 'banana' : {'apple' < 'banana'}")    # True
    print(f"   'apple' < 'Apple'  : {'apple' < 'Apple'}")     # False（大写字母排在小写之前）
    print(f"   '10' < '2'         : {'10' < '2'}")            # True（字符串比较，按字符逐位比）
    print(f"   '10' < 2           : 报错！不同类型不能比较")

    # 4. 列表比较
    print("\n4. 列表比较:")
    print(f"   [1, 2, 3] < [1, 3, 0] : {[1, 2, 3] < [1, 3, 0]}")     # True（2 < 3）
    print(f"   [1, 2] < [1, 2, 3]    : {[1, 2] < [1, 2, 3]}")       # True（短的更小）

    # 5. is 和 is not
    print("\n5. is 和 is not（身份比较）:")
    list_a = [1, 2, 3]
    list_b = [1, 2, 3]
    list_c = list_a

    print(f"   list_a == list_b : {list_a == list_b}")  # True — 值相等
    print(f"   list_a is list_b : {list_a is list_b}")  # False — 不同对象
    print(f"   list_a is list_c : {list_a is list_c}")  # True — 同一对象

    # None 检查的标准做法
    value = None
    print(f"\n   value is None    : {value is None}")    # ✅ 正确
    print(f"   value == None    : {value == None}")     # ❌ 可行但不推荐


# =====================================================================
# 第四部分：逻辑运算符与短路求值
# =====================================================================

def part4_logical_operators():
    """演示逻辑运算符的短路求值机制"""
    print("\n" + "=" * 70)
    print("🔷 第四部分：逻辑运算符与短路求值")
    print("=" * 70)

    # 1. 基本真值表
    print("\n1. 逻辑运算真值表:")
    print(f"   True  and True  = {True and True}")
    print(f"   True  and False = {True and False}")
    print(f"   False and True  = {False and True}")
    print(f"   False and False = {False and False}")

    print(f"\n   True  or True   = {True or True}")
    print(f"   True  or False  = {True or False}")
    print(f"   False or True   = {False or True}")
    print(f"   False or False  = {False or False}")

    print(f"\n   not True        = {not True}")
    print(f"   not False       = {not False}")

    # 2. 短路求值演示
    print("\n2. 短路求值（Short-Circuit）:")

    def check_a():
        """第一个检查：返回 False 并打印日志"""
        print("   → 执行 check_a()")
        return False

    def check_b():
        """第二个检查：返回 True 并打印日志"""
        print("   → 执行 check_b()")
        return True

    print("   check_a() and check_b():")
    result = check_a() and check_b()
    print(f"   结果: {result}  (check_b 没有被调用！因为 check_a 已经返回 False)")

    print("\n   check_a() or check_b():")
    result = check_a() or check_b()
    print(f"   结果: {result}  (因为 check_a 返回 False，继续执行 check_b)")

    # 3. and/or 返回最后一个计算的值
    print("\n3. and/or 返回最后一个被计算的值（不一定是 True/False）:")
    print(f"   0 and 42  = {0 and 42}")     # 0（因为 0 是 Falsy，短路返回 0）
    print(f"   3 and 42  = {3 and 42}")     # 42（因为 3 是 Truthy，继续计算返回 42）
    print(f"   0 or 42   = {0 or 42}")      # 42（因为 0 是 Falsy，继续计算返回 42）
    print(f"   3 or 42   = {3 or 42}")      # 3（因为 3 是 Truthy，短路返回 3）

    # 4. 短路求值的实际应用
    print("\n4. 短路求值的实际应用:")

    # 应用 1：先检查再访问
    user = {"name": "Alice"}
    if "email" in user and user["email"].endswith(".com"):
        print("   [应用1] 邮箱是 .com 域名")  # 不会执行，因为"email"不在字典中
    else:
        print("   [应用1] 没有 email 或非 .com 域名")

    # 应用 2：默认值
    username = "" or "默认用户"
    print(f"   [应用2] 空字符串默认值: {username}")

    # 应用 3：多重条件
    def is_valid_password(pw):
        """检查密码是否有效"""
        return len(pw) >= 8 and any(c.isdigit() for c in pw) and any(c.isupper() for c in pw)

    test_passwords = ["abc", "abcdefgh", "Abcdef1g"]
    for pw in test_passwords:
        print(f"   [应用3] 密码 '{pw}' 有效: {is_valid_password(pw)}")

    # 5. 运算符优先级
    print("\n5. 逻辑运算符优先级（not > and > or）:")
    print(f"   True or False and False:")
    print(f"     结果: {True or False and False}")
    print(f"     等价于: True or (False and False) = True or False = True")

    print(f"\n   not True and False:")
    print(f"     结果: {not True and False}")
    print(f"     等价于: (not True) and False = False and False = False")

    # 6. 使用德摩根定律简化
    print("\n6. 德摩根定律化简:")
    age, has_id = 16, False

    # 原始：不能进入 = 不满 18 或没有身份证
    cond1 = not (age >= 18 and has_id)     # not (A and B)
    cond2 = age < 18 or not has_id         # not A or not B
    print(f"   not (age>=18 and has_id): {cond1}")
    print(f"   age<18 or not has_id:      {cond2}")
    print(f"   二者等价: {cond1 == cond2}")


# =====================================================================
# 第五部分：if/elif/else 条件分支
# =====================================================================

def part5_conditionals():
    """演示 if/elif/else 的完整用法"""
    print("\n" + "=" * 70)
    print("🔷 第五部分：条件分支 if/elif/else")
    print("=" * 70)

    # 1. 基本结构
    print("\n1. 基本 if/elif/else:")
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
    print(f"   得分: {score}, 等级: {grade}")

    # 2. 嵌套 if（不推荐超过 3 层）
    print("\n2. 嵌套 if 与守卫子句对比:")

    def login_nested(username, password, is_admin):
        """嵌套版本"""
        if username:
            if password:
                if len(password) >= 6:
                    if is_admin:
                        return "管理员登录成功"
                    else:
                        return "用户登录成功"
                else:
                    return "密码太短"
            else:
                return "密码不能为空"
        else:
            return "用户名不能为空"

    def login_guarded(username, password, is_admin):
        """守卫子句版本（推荐）"""
        if not username:
            return "用户名不能为空"
        if not password:
            return "密码不能为空"
        if len(password) < 6:
            return "密码太短"

        return "管理员登录成功" if is_admin else "用户登录成功"

    result1 = login_nested("alice", "secret123", False)
    result2 = login_guarded("alice", "secret123", False)
    print(f"   嵌套版本结果: {result1}")
    print(f"   守卫版本结果: {result2}")
    print(f"   推荐使用守卫子句版本——更扁平、更易读")

    # 3. 使用 in 检查多个值
    print("\n3. 使用 in 简化多重条件:")
    char = "a"
    # ❌ 冗长写法
    if char == "a" or char == "e" or char == "i" or char == "o" or char == "u":
        print(f"   '{char}' 是元音字母（传统写法）")

    # ✅ Pythonic 写法
    vowels = "aeiouAEIOU"
    if char in vowels:
        print(f"   '{char}' 是元音字母（in 写法）")

    # 4. 条件判断中的常见错误
    print("\n4. 常见边界错误:")
    age = 18

    # 错误：用 > 而不是 >=
    if age > 18:
        print("   ❌ 用 > 18: 这行不会执行（age=18 时不满足）")
    if age >= 18:
        print("   ✅ 用 >= 18: 这行会执行")

    # 5. 比色法（switch-case 的替代）
    print("\n5. Python 中没有 switch-case，用 if/elif 或字典实现:")

    def get_day_name(day_num):
        """字典代替 switch-case"""
        days = {
            1: "周一",
            2: "周二",
            3: "周三",
            4: "周四",
            5: "周五",
            6: "周六",
            7: "周日",
        }
        return days.get(day_num, "无效日期")

    for d in range(1, 9):
        print(f"   {d} → {get_day_name(d)}")


# =====================================================================
# 第六部分：三元表达式
# =====================================================================

def part6_ternary():
    """演示三元表达式的使用"""
    print("\n" + "=" * 70)
    print("🔷 第六部分：三元表达式（条件表达式）")
    print("=" * 70)

    # 1. 基本语法
    print("\n1. 基本语法: x = A if 条件 else B")
    age = 20
    status = "成年" if age >= 18 else "未成年"
    print(f"   age = {age}, status = {status}")

    # 2. 嵌套三元表达式
    print("\n2. 嵌套三元表达式:")
    score = 75
    grade = "优秀" if score >= 90 else "良好" if score >= 80 else "及格" if score >= 60 else "不及格"
    print(f"   得分: {score}, 等级: {grade}")

    # 3. 三元表达式的多种用途
    print("\n3. 三元表达式应用场景:")

    # 场景 1：函数返回值
    def max_of_two(a, b):
        return a if a > b else b
    print(f"   max_of_two(10, 20) = {max_of_two(10, 20)}")

    # 场景 2：列表推导式中
    numbers = list(range(1, 11))
    labels = ["偶" if n % 2 == 0 else "奇" for n in numbers]
    print(f"   数字奇偶标签: {list(zip(numbers, labels))}")

    # 场景 3：print 中（不推荐）
    x = 15
    print(f"   三元在 f-string 中: {x} 是{'偶数' if x % 2 == 0 else '奇数'}")

    # 4. 三元表达式 vs if/else 的选择
    print("\n4. 何时用三元，何时用 if/else:")

    # ✅ 适合三元：简单赋值
    result = "通过" if score >= 60 else "不通过"

    # ❌ 不适合三元：有副作用的操作
    # 下面的写法虽然可行但可读性差：
    # print("成功") if save_data() else print("失败")
    # 应该用普通的 if/else


# =====================================================================
# 第七部分：高级话题
# =====================================================================

def part7_advanced():
    """高级演示：条件判断的字节码视角"""
    print("\n" + "=" * 70)
    print("🔷 第七部分：字节码视角（进阶）")
    print("=" * 70)

    # 查看 if/else 的字节码
    print("\n1. if/else 条件的字节码:")
    code_if = """
def compare(x):
    if x > 0:
        return "正数"
    elif x == 0:
        return "零"
    else:
        return "负数"
"""
    print(f"字节码（简化显示）:")
    # 只取关键行
    lines = code_if.strip().split('\n')
    for line in lines:
        print(f"  {line}")

    print("\n2. and/or 短路求值的字节码:")
    code_and = """
def short_circuit(x):
    return x and risky_call()
"""
    lines = code_and.strip().split('\n')
    for line in lines:
        print(f"  {line}")

    # 实际展示 dis 模块
    print("\n3. 使用 dis 模块查看字节码（可取消注释查看）:")
    code_sample = """
x = 5
if x > 0:
    y = x * 2
else:
    y = x * -1
"""
    print(f"   示例代码: {code_sample.strip()}")
    print(f"   可运行以下命令查看字节码：")
    print(f"     python3 -c \"import dis; dis.dis('{code_sample.strip().replace(chr(10), ';')}')\"")
    # 注意：上面这行太长，建议改用文件方式


# =====================================================================
# 主程序
# =====================================================================

if __name__ == "__main__":
    print("🐍 Python 布尔值与条件判断 — 基础示例\n")

    part1_boolean_basics()
    part2_truthy_falsy()
    part3_comparison_operators()
    part4_logical_operators()
    part5_conditionals()
    part6_ternary()
    part7_advanced()

    print("\n" + "=" * 70)
    print("✅ 所有示例运行完毕！")
    print("=" * 70)
