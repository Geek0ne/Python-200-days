"""
Day 004 — 实战：科学计算器
======================================================================
综合应用整型、浮点、位运算和类型转换知识。
可直接运行: python3 02-scientific-calculator.py
"""

import math
import sys


# =====================================================================
# 工具函数
# =====================================================================

def get_number(prompt="请输入一个数: ", num_type=float):
    """安全获取数字输入，带异常处理"""
    while True:
        try:
            return num_type(input(prompt))
        except (ValueError, TypeError):
            print("❌ 输入无效，请输入有效的数字。")


def clear_screen():
    """清屏"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')


def header(text):
    """打印格式化标题"""
    width = 60
    print("\n" + "=" * width)
    print(f"  {text}".center(width))
    print("=" * width)


# =====================================================================
# 模块 1：基础运算
# =====================================================================

def basic_calculator():
    """基础四则运算模块"""
    header("基础运算")
    print("支持的运算: +, -, *, /, //, %, **")
    
    try:
        expr = input("\n输入表达式 (例如: 3 + 4 * 2): ").strip()
        # 使用 eval 演示（仅学习环境使用，生产环境慎用）
        result = eval(expr, {"__builtins__": {}}, math.__dict__)
        print(f"\n  {expr} = {result}")
        
        # 类型分析
        print(f"\n  结果类型: {type(result).__name__}")
        
        if isinstance(result, float):
            ratio = result.as_integer_ratio()
            print(f"  精确分数: {ratio[0]}/{ratio[1]}")
            print(f"  是否为整数: {result.is_integer()}")
        elif isinstance(result, int):
            print(f"  二进制: {bin(result)}")
            print(f"  位长度: {result.bit_length()} bits")
        elif isinstance(result, complex):
            print(f"  模长: {abs(result):.4f}")
            print(f"  辐角: {cmath.phase(result):.4f} rad")
            
    except Exception as e:
        print(f"❌ 表达式错误: {e}")


# =====================================================================
# 模块 2：单位换算
# =====================================================================

def unit_converter():
    """单位换算模块"""
    import cmath  # 复数支持
    
    header("单位换算器")
    
    print("1) 温度: °C ↔ °F")
    print("2) 长度: 米 ↔ 英尺")
    print("3) 重量: 千克 ↔ 磅")
    print("4) 角度: 度 ↔ 弧度")
    
    choice = input("\n请选择 (1-4): ").strip()
    
    if choice == "1":
        value = get_number("输入摄氏度: ")
        f = value * 9/5 + 32
        k = value + 273.15
        print(f"\n  {value}°C = {f:.2f}°F")
        print(f"  {value}°C = {k:.2f}K")
        
    elif choice == "2":
        value = get_number("输入米: ")
        feet = value * 3.28084
        inches = value * 39.3701
        print(f"\n  {value} m = {feet:.2f} ft")
        print(f"  {value} m = {inches:.2f} in")
        
    elif choice == "3":
        value = get_number("输入千克: ")
        pounds = value * 2.20462
        print(f"\n  {value} kg = {pounds:.2f} lb")
        
    elif choice == "4":
        value = get_number("输入角度(度): ")
        rad = math.radians(value)
        print(f"\n  {value}° = {rad:.6f} rad")
        print(f"  sin({value}°) = {math.sin(rad):.6f}")
        print(f"  cos({value}°) = {math.cos(rad):.6f}")
        
    else:
        print("❌ 无效选项。")


# =====================================================================
# 模块 3：浮点数分析器
# =====================================================================

def float_analyzer():
    """浮点数分析器 — 探索 IEEE 754 表示"""
    header("浮点数分析器")
    
    value = get_number("输入一个浮点数: ")
    f = float(value)
    
    print(f"\n📊 {f} 的完整分析:")
    print(f"  {'─' * 40}")
    
    # 基本性质
    print(f"  类型: {type(f).__name__}")
    print(f"  精确分数: {f.as_integer_ratio()}")
    print(f"  是否为整数: {f.is_integer()}")
    
    # IEEE 754 十六进制表示
    print(f"  IEEE 754 hex: {f.hex()}")
    
    # 精度分析
    print(f"  {'─' * 40}")
    print(f"  🔍 精度分析:")
    
    # 找最小可表示增量
    eps = math.ulp(f)
    print(f"  ULP (最小精度单位): {eps}")
    print(f"  下一个可表示的数: {f + eps}")
    print(f"  上一个可表示的数: {f - eps}")
    
    # 比较说明
    print(f"  {'─' * 40}")
    print(f"  ⚠️ 浮点数比较建议:")
    print(f"  不要使用: f == some_value")
    print(f"  应该使用: abs(f - some_value) < 1e-9")


# =====================================================================
# 模块 4：进制转换器
# =====================================================================

def base_converter():
    """进制转换器"""
    header("进制转换器")
    
    print("输入一个数（支持 10 进制或加前缀的其他进制）")
    print("前缀: 0b=二进制, 0o=八进制, 0x=十六进制")
    
    raw = input("\n输入: ").strip()
    
    try:
        if raw.startswith(("0b", "0B")):
            base_info = "二进制"
            value = int(raw, 2)
        elif raw.startswith(("0o", "0O")):
            base_info = "八进制"
            value = int(raw, 8)
        elif raw.startswith(("0x", "0X")):
            base_info = "十六进制"
            value = int(raw, 16)
        else:
            base_info = "十进制"
            value = int(raw)
        
        print(f"\n📊 {raw} ({base_info}) 的转换结果:")
        print(f"  {'─' * 40}")
        print(f"  十进制:    {value}")
        print(f"  二进制:    {bin(value)}")
        print(f"  八进制:    {oct(value)}")
        print(f"  十六进制:  {hex(value)}")
        print(f"  {'─' * 40}")
        print(f"  位长度:    {value.bit_length()} bits")
        
        bytes_needed = max(1, (value.bit_length() + 7) // 8)
        print(f"  所需字节:  {bytes_needed} bytes")
        
        if bytes_needed <= 8:
            big_endian = value.to_bytes(bytes_needed, 'big')
            little_endian = value.to_bytes(bytes_needed, 'little')
            print(f"  大端表示:  {big_endian.hex()}")
            print(f"  小端表示:  {little_endian.hex()}")
            
    except ValueError:
        print(f"❌ 无法解析: {raw}")
    except OverflowError:
        print(f"❌ 数值过大无法转换")


# =====================================================================
# 模块 5：素数检测器
# =====================================================================

def is_prime(n: int) -> bool:
    """检查整数 n 是否为素数"""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    
    limit = int(math.sqrt(n)) + 1
    for i in range(3, limit, 2):
        if n % i == 0:
            return False
    return True


def prime_checker():
    """素数检测器"""
    header("素数检测器")
    
    n = get_number("输入一个正整数: ", int)
    
    if n <= 0:
        print("❌ 请输入正整数。")
        return
    
    print(f"\n  检查 {n}:")
    print(f"  {'─' * 40}")
    
    if is_prime(n):
        print(f"  ✅ {n} 是素数！")
        print(f"  ℹ️ 素数只有 1 和自身两个因数。")
    else:
        print(f"  ❌ {n} 不是素数。")
        print(f"  ℹ️ 因数分解:")
        
        temp = n
        factors = []
        d = 2
        while d * d <= temp:
            while temp % d == 0:
                factors.append(d)
                temp //= d
            d += 1 if d == 2 else 2  # 2之后只检查奇数
        if temp > 1:
            factors.append(temp)
        
        print(f"  {n} = {' × '.join(map(str, factors))}")
    
    # 相邻素数
    print(f"\n  📍 相邻素数:")
    lower = n - 1
    while lower > 1 and not is_prime(lower):
        lower -= 1
    upper = n + 1
    while not is_prime(upper):
        upper += 1
    if lower > 1:
        print(f"  比 {n} 小的最大素数: {lower}")
    print(f"  比 {n} 大的最小素数: {upper}")


# =====================================================================
# 模块 6：位运算游乐场
# =====================================================================

def bitwise_playground():
    """位运算交互游乐场"""
    header("位运算游乐场")
    
    a = get_number("输入第一个整数: ", int)
    b = get_number("输入第二个整数: ", int)
    
    print(f"\n  a = {a:8d}  = {bin(a):>16s}")
    print(f"  b = {b:8d}  = {bin(b):>16s}")
    print(f"  {'─' * 48}")
    print(f"  a & b  = {a & b:8d}  = {bin(a & b):>16s}  (AND)")
    print(f"  a | b  = {a | b:8d}  = {bin(a | b):>16s}  (OR)")
    print(f"  a ^ b  = {a ^ b:8d}  = {bin(a ^ b):>16s}  (XOR)")
    print(f"  ~a     = {~a:8d}  = {bin(~a & 0xFF):>16s}  (NOT, 8位截断)")
    print(f"  ~b     = {~b:8d}  = {bin(~b & 0xFF):>16s}")
    print(f"  a << 1 = {a << 1:8d}  = {bin(a << 1):>16s}  (左移, ×2)")
    print(f"  a >> 1 = {a >> 1:8d}  = {bin(a >> 1):>16s}  (右移, ÷2)")
    
    # 实战检查
    print(f"\n  🔍 实战检查:")
    print(f"  {a} 是奇数: {bool(a & 1)}")
    print(f"  {a} 是 2 的幂: {a > 0 and (a & (a - 1)) == 0}")
    print(f"  {b} 是奇数: {bool(b & 1)}")
    print(f"  {b} 是 2 的幂: {b > 0 and (b & (b - 1)) == 0}")


# =====================================================================
# 模块 7：统计计算器
# =====================================================================

def statistics_calculator():
    """统计计算器"""
    header("统计计算器")
    
    print("输入一组数字（用空格分隔）:")
    try:
        raw = input("> ").strip()
        numbers = [float(x) for x in raw.split()]
        
        if not numbers:
            print("❌ 请输入至少一个数")
            return
        
        n = len(numbers)
        total = sum(numbers)
        mean = total / n
        
        # 方差（总体方差）
        variance = sum((x - mean) ** 2 for x in numbers) / n
        std_dev = math.sqrt(variance)
        
        # 中位数
        sorted_nums = sorted(numbers)
        if n % 2 == 1:
            median = sorted_nums[n // 2]
        else:
            mid = n // 2
            median = (sorted_nums[mid - 1] + sorted_nums[mid]) / 2
        
        # 最小/最大
        minimum = min(numbers)
        maximum = max(numbers)
        
        print(f"\n📊 统计结果 (共 {n} 个数):")
        print(f"  {'─' * 40}")
        print(f"  总和:     {total:.4f}")
        print(f"  平均数:   {mean:.4f}")
        print(f"  中位数:   {median:.4f}")
        print(f"  最小值:   {minimum}")
        print(f"  最大值:   {maximum}")
        print(f"  极差:     {maximum - minimum:.4f}")
        print(f"  方差:     {variance:.4f}")
        print(f"  标准差:   {std_dev:.4f}")
        
        # 类型信息
        print(f"\n  💡 数值分析:")
        print(f"  所有整数: {all(isinstance(x, float) and x.is_integer() for x in numbers)}")
        print(f"  浮点数精度示例: 0.1 + 0.2 = {0.1 + 0.2}")
        
    except ValueError:
        print("❌ 输入无效，请用空格分隔数字。")


# =====================================================================
# 主菜单
# =====================================================================

def show_menu():
    """显示主菜单"""
    print("\n" + "★" * 60)
    print("                 🧮 Python 科学计算器")
    print("                 Day 004 — 数字与运算实战")
    print("★" * 60)
    print()
    print("  [1] 基础运算计算器    [2] 单位换算器")
    print("  [3] 浮点数分析器      [4] 进制转换器")
    print("  [5] 素数检测器        [6] 位运算游乐场")
    print("  [7] 统计计算器")
    print()
    print("  [0] 退出")
    print()
    print("-" * 60)


def main():
    """主程序入口"""
    import cmath  # 全局复数支持
    
    while True:
        show_menu()
        choice = input("  请选择功能 (0-7): ").strip()
        
        if choice == "0":
            print("\n👋 感谢使用，再见！")
            print(f"  Python {sys.version.split()[0]}  |  OpenClaw Learn-Python")
            break
        elif choice == "1":
            basic_calculator()
        elif choice == "2":
            unit_converter()
        elif choice == "3":
            float_analyzer()
        elif choice == "4":
            base_converter()
        elif choice == "5":
            prime_checker()
        elif choice == "6":
            bitwise_playground()
        elif choice == "7":
            statistics_calculator()
        else:
            print("❌ 无效选项，请重新选择。")
        
        input("\n按 Enter 继续...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程序被用户中断。")
        sys.exit(0)
