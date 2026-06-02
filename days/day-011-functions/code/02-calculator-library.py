#!/usr/bin/env python3
"""
02-calculator-library.py
计算器函数库 —— 完整实战项目

本文件构建了一个完整的计算器函数库，包含基本运算、高级运算和交互式界面。
演示如何用函数组织代码、构建模块化的功能集合。

运行:
    # 直接运行交互模式:
    python3 02-calculator-library.py

    # 作为模块导入使用:
    # from 02_calculator_library import add, multiply, power
"""

# ============================================================
# 🧮 第一部分: 基本运算函数
# ============================================================

def add(a, b):
    """
    加法运算。

    返回 a + b 的和。
    浮点数和整数都可以。

    Args:
        a (float/int): 第一个数
        b (float/int): 第二个数

    Returns:
        float/int: a + b 的结果
    """
    return a + b


def subtract(a, b):
    """
    减法运算。

    返回 a - b 的差。

    Args:
        a (float/int): 被减数
        b (float/int): 减数

    Returns:
        float/int: a - b 的结果
    """
    return a - b


def multiply(a, b):
    """
    乘法运算。

    返回 a × b 的积。

    Args:
        a (float/int): 第一个因数
        b (float/int): 第二个因数

    Returns:
        float/int: a × b 的结果
    """
    return a * b


def divide(a, b):
    """
    除法运算（防御性编程）。

    返回 a ÷ b 的商。
    当除数为 0 时返回错误信息字符串而非抛出异常。

    为什么这样设计？
    - 让调用者可以自行决定如何处理除零错误
    - 交互模式下，显示错误比崩溃更友好
    - 批量处理时，一个错误不会中断整个流程

    Args:
        a (float/int): 被除数
        b (float/int): 除数

    Returns:
        float/str: a ÷ b 的结果，或错误信息
    """
    if b == 0:
        return "错误：除数不能为 0"
    return a / b


def mod(a, b):
    """
    取模运算（求余数）。

    返回 a 除以 b 的余数。
    负数取模需要注意：结果的符号和除数一致。

    Args:
        a (float/int): 被除数
        b (float/int): 除数

    Returns:
        float/int/str: 余数，或错误信息
    """
    if b == 0:
        return "错误：除数不能为 0"
    return a % b


# ============================================================
# 🧮 第二部分: 高级运算函数
# ============================================================

def power(base, exp):
    """
    幂运算。

    返回 base 的 exp 次幂。
    支持整数和浮点指数（如平方根 power(9, 0.5) = 3.0）。

    实现原理:
        base ** exp = base^exp
        当 exp 为整数时，Python 内部使用快速幂算法（O(log n)）
        当 exp 为浮点时，通过对数实现: exp(exp * log(base))

    Args:
        base (float/int): 底数
        exp (float/int): 指数

    Returns:
        float: base^exp 的结果
    """
    return base ** exp


def sqrt_newton(n, precision=1e-15):
    """
    牛顿迭代法求平方根（不依赖 math.sqrt）。

    牛顿迭代公式:
        x_{n+1} = (x_n + n / x_n) / 2

    算法原理:
        我们要解方程 f(x) = x² - n = 0
        牛顿迭代: x_{n+1} = x_n - f(x_n)/f'(x_n)
                    = x_n - (x_n² - n)/(2*x_n)
                    = (x_n + n/x_n) / 2

    几何意义:
        在 (x_n, f(x_n)) 处做切线，切线与 x 轴的交点就是 x_{n+1}

    Args:
        n (float): 要开平方的数
        precision (float): 精度要求，默认 1e-15

    Returns:
        float/str: 平方根，或错误信息
    """
    if n < 0:
        return "错误：不能对负数开平方"
    if n == 0:
        return 0.0

    x = n  # 初始猜测

    # 迭代收敛
    for iteration in range(1000):
        next_x = (x + n / x) / 2
        if abs(next_x - x) < precision:
            print(f"    (牛顿迭代收敛: {iteration + 1} 次迭代)")
            return next_x
        x = next_x

    return x  # 达到最大迭代次数


def factorial(n):
    """
    阶乘运算。

    n! = n × (n-1) × (n-2) × ... × 2 × 1
    例如: 5! = 5 × 4 × 3 × 2 × 1 = 120

    特殊值: 0! = 1（数学定义）

    实现原理:
        用循环累乘，比递归更节省内存（不会创建调用栈）。

    Args:
        n (int): 非负整数

    Returns:
        int/str: n! 的结果，或错误信息
    """
    if not isinstance(n, int) or n < 0:
        return "错误：阶乘仅定义于非负整数"

    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def gcd(a, b):
    """
    最大公约数（欧几里得算法/辗转相除法）。

    算法原理:
        gcd(a, b) = gcd(b, a % b)
        当 b = 0 时，gcd(a, 0) = a

    证明:
        如果 d|a 且 d|b，则 d|(a - qb)，即 d|(a % b)
        所以 gcd(a, b) = gcd(b, a mod b)

    Args:
        a (int): 第一个整数
        b (int): 第二个整数

    Returns:
        int: a 和 b 的最大公约数
    """
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """
    最小公倍数。

    公式: lcm(a, b) = |a × b| / gcd(a, b)

    原理:
        a 和 b 的乘积 = 最大公约数 × 最小公倍数

    Args:
        a (int): 第一个整数
        b (int): 第二个整数

    Returns:
        int: a 和 b 的最小公倍数
    """
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


# ============================================================
# 🧮 第三部分: 统计运算函数
# ============================================================

def average(numbers):
    """
    计算算术平均数（均值）。

    公式: avg = sum(numbers) / len(numbers)

    Args:
        numbers (list): 数字列表

    Returns:
        float/str: 平均值，或错误信息
    """
    if not numbers:
        return "错误：列表不能为空"
    return sum(numbers) / len(numbers)


def median(numbers):
    """
    计算中位数。

    中位数是排序后位于正中间的值：
    - 如果元素个数为奇数：最中间的那个
    - 如果元素个数为偶数：中间两个的平均值

    和平均值的对比：
    - 平均值对异常值敏感（例：[1,2,3,100] 的 avg=26.5）
    - 中位数对异常值鲁棒（例：[1,2,3,100] 的 median=2.5）

    Args:
        numbers (list): 数字列表

    Returns:
        float/str: 中位数，或错误信息
    """
    if not numbers:
        return "错误：列表不能为空"

    sorted_nums = sorted(numbers)
    n = len(sorted_nums)
    mid = n // 2

    if n % 2 == 1:
        # 奇数个元素
        return float(sorted_nums[mid])
    else:
        # 偶数个元素
        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2


def variance(numbers, ddof=0):
    """
    计算方差。

    方差衡量数据围绕均值的离散程度。

    总体方差 (ddof=0): σ² = Σ(xi - μ)² / N
    样本方差 (ddof=1): s² = Σ(xi - x̄)² / (N-1)

    为什么样本方差用 N-1 而不是 N？（贝塞尔校正）
    - 样本均值 x̄ 已经消耗了一个自由度
    - 用 N-1 得到的是总体方差的无偏估计

    Args:
        numbers (list): 数字列表
        ddof (int): Delta degrees of freedom (0=总体, 1=样本)

    Returns:
        float/str: 方差，或错误信息
    """
    if not numbers:
        return "错误：列表不能为空"
    if len(numbers) <= ddof:
        return f"错误：数据量不足以计算（需要 > {ddof} 个元素）"

    avg = sum(numbers) / len(numbers)
    squared_diffs = sum((x - avg) ** 2 for x in numbers)
    return squared_diffs / (len(numbers) - ddof)


def std_dev(numbers, ddof=0):
    """
    计算标准差。

    标准差 = 方差的平方根。
    和方差相比，标准差和原始数据单位一致，更直观。

    Args:
        numbers (list): 数字列表
        ddof (int): Delta degrees of freedom

    Returns:
        float/str: 标准差，或错误信息
    """
    var = variance(numbers, ddof)
    if isinstance(var, str):
        return var
    return var ** 0.5


# ============================================================
# 🧮 第四部分: 格式化与辅助函数
# ============================================================

def format_number(n):
    """
    格式化数字显示。

    如果是整数就显示为整数，否则保留两位小数。
    提高交互界面的可读性。

    Args:
        n (float/int): 要格式化的数字

    Returns:
        str: 格式化后的字符串
    """
    if isinstance(n, float) and n == int(n):
        return str(int(n))
    elif isinstance(n, float):
        return f"{n:.2f}"
    return str(n)


def show_menu():
    """显示计算器菜单。"""
    print("\n" + "=" * 50)
    print("          🔢 Python 计算器函数库")
    print("=" * 50)
    print("  【基本运算】")
    print("    a + b    加法")
    print("    a - b    减法")
    print("    a * b    乘法")
    print("    a / b    除法")
    print("    a % b    取模")
    print()
    print("  【高级运算】")
    print("    a ^ b    幂运算")
    print("    sqrt n   平方根（牛顿迭代法）")
    print("    n !      阶乘")
    print("    gcd a b  最大公约数")
    print("    lcm a b  最小公倍数")
    print()
    print("  【统计运算】")
    print("    avg n1 n2 n3 ...   平均值")
    print("    med n1 n2 n3 ...   中位数")
    print("    var n1 n2 n3 ...   方差")
    print("    std n1 n2 n3 ...   标准差")
    print()
    print("  【其他】")
    print("    help     显示此菜单")
    print("    quit     退出")
    print("=" * 50)


def parse_numbers(parts, start_index=1):
    """
    把字符串列表转换为浮点数。

    从 start_index 开始解析，忽略命令词本身。

    Args:
        parts (list): 拆分后的用户输入
        start_index (int): 从哪个索引开始解析数字

    Returns:
        list: 浮点数列表

    Raises:
        ValueError: 如果无法解析为数字
    """
    numbers = []
    for p in parts[start_index:]:
        numbers.append(float(p))
    return numbers


# ============================================================
# 🧮 第五部分: 交互式计算器
# ============================================================

def calculator():
    """
    交互式计算器主函数。

    这是整个函数库的入口点，提供命令行交互界面。
    演示如何用函数组织复杂逻辑：
    - 输入解析 → 路由分发 → 结果展示

    按 'q', 'quit', 'exit' 退出。
    """
    show_menu()

    while True:
        try:
            user_input = input("\n请输入表达式 > ").strip()

            # 退出条件
            if user_input.lower() in ('q', 'quit', 'exit'):
                print("感谢使用！再见 👋")
                break

            if not user_input:
                continue

            if user_input.lower() == 'help':
                show_menu()
                continue

            parts = user_input.split()
            cmd = parts[0].lower()
            result = None

            # ── 二元运算: a op b ──
            if cmd.lstrip('-').replace('.', '').isdigit() or \
               (len(cmd) == 1 and cmd not in ('sqrt', 'avg', 'med', 'var', 'std', 'gcd', 'lcm', 'factorial', '!') and len(parts) >= 3):

                if len(parts) >= 3:
                    a = float(parts[0])
                    op = parts[1]
                    b = float(parts[2])

                    if op == '+':
                        result = add(a, b)
                    elif op == '-':
                        result = subtract(a, b)
                    elif op == '*':
                        result = multiply(a, b)
                    elif op == '/':
                        result = divide(a, b)
                    elif op == '%':
                        result = mod(a, b)
                    elif op == '^':
                        result = power(a, b)
                    else:
                        print(f"不支持的运算符: {op}")
                        continue
                else:
                    print("格式错误: 请按 'a op b' 格式输入")
                    continue

            # ── 高级运算命令 ──
            elif cmd == 'sqrt' and len(parts) >= 2:
                n = float(parts[1])
                print(f"计算 {n} 的平方根...")
                result = sqrt_newton(n)
                # 同时用内置运算符验证
                if isinstance(result, (int, float)):
                    verify = n ** 0.5
                    print(f"    验证 (n**0.5): {verify:.15f}")

            elif cmd in ('factorial', '!') and len(parts) >= 2:
                if cmd == 'factorial':
                    n = int(float(parts[1]))
                else:
                    n = int(float(parts[0]))
                result = factorial(n)

            elif cmd == 'gcd' and len(parts) >= 3:
                a, b = int(float(parts[1])), int(float(parts[2]))
                result = gcd(a, b)

            elif cmd == 'lcm' and len(parts) >= 3:
                a, b = int(float(parts[1])), int(float(parts[2]))
                result = lcm(a, b)

            # ── 统计运算命令 ──
            elif cmd == 'avg' and len(parts) >= 3:
                nums = parse_numbers(parts, 1)
                result = average(nums)

            elif cmd == 'med' and len(parts) >= 3:
                nums = parse_numbers(parts, 1)
                result = median(nums)

            elif cmd == 'var' and len(parts) >= 3:
                nums = parse_numbers(parts, 1)
                result = variance(nums, ddof=1)  # 样本方差

            elif cmd == 'std' and len(parts) >= 3:
                nums = parse_numbers(parts, 1)
                result = std_dev(nums, ddof=1)

            else:
                print("无法识别的命令，输入 'help' 查看帮助")
                continue

            # ── 显示结果 ──
            if isinstance(result, str):
                print(f"❌ {result}")
            else:
                print(f"✅ 结果: {format_number(result)}")

        except ValueError as e:
            print(f"❌ 输入错误: 请确保输入了有效的数字 ({e})")
        except KeyboardInterrupt:
            print("\n\n程序已中断，再见 👋")
            break
        except Exception as e:
            print(f"❌ 发生未知错误: {e}")


# ============================================================
# 📊 第六部分: 演示模式（直接运行代码时执行）
# ============================================================

def demo_mode():
    """
    演示模式——展示函数库的各种功能。

    不进入交互界面，而是自动运行一系列计算示例。
    适合快速了解函数库的能力。
    """
    print("=" * 60)
    print("           📊 计算器函数库 —— 演示模式")
    print("=" * 60)

    print("\n── 基本运算 ──")
    print(f"  add(10, 20)      = {add(10, 20)}")
    print(f"  subtract(100, 45) = {subtract(100, 45)}")
    print(f"  multiply(6, 7)    = {multiply(6, 7)}")
    print(f"  divide(22, 7)     = {divide(22, 7):.6f}")

    print(f"\n  divide(5, 0)      = {divide(5, 0)}  ← 防御性编程")
    print(f"  mod(17, 5)        = {mod(17, 5)}")
    print(f"  mod(-17, 5)       = {mod(-17, 5)}")

    print("\n── 高级运算 ──")
    print(f"  power(2, 10)      = {power(2, 10)}")
    print(f"  power(9, 0.5)     = {power(9, 0.5)}")
    print(f"  sqrt_newton(144)  = {sqrt_newton(144)}")
    print(f"  sqrt_newton(2)    = {sqrt_newton(2):.15f}")
    print(f"  factorial(10)     = {factorial(10):,}")
    print(f"  gcd(48, 18)       = {gcd(48, 18)}")
    print(f"  lcm(12, 18)       = {lcm(12, 18)}")

    print("\n── 统计运算 ──")
    data = [67, 72, 85, 73, 91, 68, 79, 84, 76, 88]
    print(f"  数据: {data}")
    print(f"  average           = {average(data):.2f}")
    print(f"  median            = {median(data)}")
    print(f"  variance(ddof=1)  = {variance(data, ddof=1):.2f}")
    print(f"  std_dev(ddof=1)   = {std_dev(data, ddof=1):.2f}")

    print("\n── 函数即对象 ──")
    ops = {'+': add, '-': subtract, '*': multiply, '/': divide, '^': power}
    a, b = 15, 4
    print(f"  对 {a} 和 {b} 应用各运算:")
    for op_name, func in ops.items():
        print(f"    {a} {op_name} {b} = {func(a, b)}")

    print("\n" + "=" * 60)
    print("✅ 演示结束！运行 python3 02-calculator-library.py")
    print("   不带参数进入交互模式: python3 02-calculator-library.py")
    print("=" * 60)


# ============================================================
# 🎯 程序入口
# ============================================================

if __name__ == "__main__":
    import sys

    # 如果命令行有参数，检查是否为 --demo
    if len(sys.argv) > 1 and sys.argv[1] == '--demo':
        demo_mode()
    else:
        # 默认进入交互模式
        print("🎯 欢迎使用 Python 计算器函数库！")
        print("   输入 'help' 查看命令，'quit' 退出")
        try:
            calculator()
        except KeyboardInterrupt:
            print("\n\n再见 👋")
