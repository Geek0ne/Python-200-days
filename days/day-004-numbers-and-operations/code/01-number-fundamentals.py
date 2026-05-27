"""
Day 004 — 数字基础：整数、浮点数、位运算与类型转换
======================================================================
本文件演示 Python 数字类型的核心特性。
"""

import math


# =====================================================================
# 第一部分：整数深入
# =====================================================================

def demonstrate_integers():
    """演示整数的核心特性"""
    print("=" * 60)
    print("🔢 整数 (int) 深入")
    print("=" * 60)
    
    # 1. 任意精度
    huge = 10 ** 100
    print(f"\n1. 任意精度整数:")
    print(f"   10^100 = {huge}")
    print(f"   位数: {len(str(huge))} 位")
    
    # 2. 不同进制
    print(f"\n2. 不同进制表示同一数值 42:")
    print(f"   十进制: {42}")
    print(f"   二进制: {bin(42)}")
    print(f"   八进制: {oct(42)}")
    print(f"   十六进制: {hex(42)}")
    
    # 3. 小整数缓存
    print(f"\n3. 小整数缓存 (-5 到 256):")
    a, b = 256, 256
    print(f"   a = 256, b = 256, a is b = {a is b}")      # True
    c, d = 257, 257
    print(f"   c = 257, d = 257, c is d = {c is d}")      # False
    
    # 4. 位长度
    print(f"\n4. bit_length() — 所需二进制位数:")
    for n in [0, 1, 8, 42, 255, 256, 1024, 65535]:
        bits = n.bit_length()
        print(f"   {n:6d} → {bits:2d} bits  ({bin(n)})")
    
    # 5. to_bytes / from_bytes
    print(f"\n5. 字节序列转换:")
    value = 2024
    data = value.to_bytes(4, byteorder='big')
    recovered = int.from_bytes(data, byteorder='big')
    print(f"   {value} → {data} → {recovered}")
    
    # 大端 vs 小端
    big = (0x1234).to_bytes(2, 'big')
    little = (0x1234).to_bytes(2, 'little')
    print(f"   大端: {big.hex()}  小端: {little.hex()}")


# =====================================================================
# 第二部分：浮点数原理
# =====================================================================

def demonstrate_floats():
    """演示浮点数的核心特性"""
    print("\n" + "=" * 60)
    print("🎯 浮点数 (float) 深入")
    print("=" * 60)
    
    # 1. 精度问题
    print(f"\n1. IEEE 754 精度问题:")
    print(f"   0.1 + 0.2 = {0.1 + 0.2}")
    print(f"   0.1 + 0.2 == 0.3: {0.1 + 0.2 == 0.3}")
    
    # 哪些浮点数精确？
    print(f"   0.5 (1/2) 在二进制中精确: {0.5}")
    print(f"   0.25 (1/4) 在二进制中精确: {0.25}")
    print(f"   0.125 (1/8) 在二进制中精确: {0.125}")
    print(f"   0.1 (1/10) 在二进制中循环: {0.1}")
    
    # 2. 正确比较
    print(f"\n2. 正确的浮点数比较:")
    def float_equal(a, b, eps=1e-9):
        return abs(a - b) < eps
    
    print(f"   0.1 + 0.2 == 0.3: {float_equal(0.1 + 0.2, 0.3)}")
    print(f"   1/3 == 0.333333: {float_equal(1/3, 0.333333)}")
    
    # 3. as_integer_ratio
    print(f"\n3. 每个浮点数都是有理数:")
    for v in [0.5, 0.75, 0.1, 0.3333333333333333]:
        n, d = v.as_integer_ratio()
        print(f"   {v} = {n}/{d}")
    
    # 4. 特殊浮点值
    print(f"\n4. 特殊浮点值:")
    inf = float('inf')
    nan = float('nan')
    
    print(f"   float('inf') = {inf}")
    print(f"   float('-inf') = {float('-inf')}")
    print(f"   float('nan') = {nan}")
    print(f"   inf + 1 = {inf + 1}")
    print(f"   inf * 0 = {inf * 0}  (nan)")
    print(f"   nan == nan: {nan == nan}  (⚠️ nan 不等于自身!)")
    print(f"   math.isnan(nan): {math.isnan(nan)}")
    
    # 5. 浮点数的十六进制表示
    print(f"\n5. 浮点数的精确十六进制表示:")
    print(f"   1.0 = {1.0.hex()}")
    print(f"   0.1 = {0.1.hex()}  (可看到循环模式)")
    print(f"   π  = {math.pi.hex()}")

    # 6. 无穷大运算规则
    print(f"\n6. 无穷大运算规则:")
    print(f"   inf + inf = {inf + inf}")
    print(f"   inf - inf = {inf - inf}  (nan)")
    print(f"   inf / inf = {inf / inf}  (nan)")
    print(f"   inf > 10**1000: {inf > 10**1000}")


# =====================================================================
# 第三部分：复数
# =====================================================================

def demonstrate_complex():
    """演示复数的核心特性"""
    print("\n" + "=" * 60)
    print("🌀 复数 (complex)")
    print("=" * 60)
    
    import cmath
    
    z1 = 3 + 4j
    z2 = 1 - 2j
    
    print(f"\n1. 复数定义:")
    print(f"   z1 = {z1}")
    print(f"   实部: {z1.real}, 虚部: {z1.imag}")
    print(f"   共轭: {z1.conjugate()}")
    print(f"   模长: {abs(z1)}  (√(3²+4²) = 5)")
    print(f"   辐角: {cmath.phase(z1):.4f} rad")
    
    print(f"\n2. 复数运算:")
    print(f"   z1 + z2 = {z1 + z2}")
    print(f"   z1 - z2 = {z1 - z2}")
    print(f"   z1 * z2 = {z1 * z2}")
    print(f"   z1 / z2 = {z1 / z2}")
    print(f"   z1**2   = {z1 ** 2}")
    
    # 欧拉公式验证
    print(f"\n3. 欧拉公式 e^(iπ) + 1 = 0:")
    euler = cmath.exp(complex(0, math.pi))
    print(f"   e^(iπ) = {euler}")
    print(f"   |e^(iπ) + 1| < 1e-15: {abs(euler + 1) < 1e-15}")

    # 极坐标与直角坐标转换
    print(f"\n4. 坐标转换:")
    r, theta = cmath.polar(z1)
    print(f"   z1 的极坐标: r={r:.4f}, θ={theta:.4f}")
    rectangular = cmath.rect(r, theta)
    print(f"   恢复直角坐标: {rectangular}")


# =====================================================================
# 第四部分：运算符优先级
# =====================================================================

def demonstrate_precedence():
    """演示运算符优先级"""
    print("\n" + "=" * 60)
    print("📐 运算符优先级与结合性")
    print("=" * 60)
    
    print(f"\n1. 幂运算是右结合:")
    print(f"   2 ** 3 ** 2 = {2 ** 3 ** 2}")
    print(f"   2 ** (3 ** 2) = {2 ** (3 ** 2)}")
    print(f"   (2 ** 3) ** 2 = {(2 ** 3) ** 2}")
    
    print(f"\n2. 链式比较:")
    print(f"   1 < 2 < 3: {1 < 2 < 3}")    # True
    print(f"   3 > 2 > 1: {3 > 2 > 1}")    # True
    print(f"   1 < 3 > 2: {1 < 3 > 2}")    # True — 1<3 and 3>2
    
    print(f"\n3. 常见陷阱:")
    print(f"   False or True and False: {False or True and False}")
    # 等价于 False or (True and False)
    print(f"   True or True and False: {True or True and False}")
    # 等价于 True or (True and False) — 短路求值，不计算右边

    print(f"\n4. 一元运算符与二元:")
    print(f"   -5 ** 2 = {-5 ** 2}")  # -(5**2) = -25
    print(f"   (-5) ** 2 = {(-5) ** 2}")  # 25
    print(f"   ~5 + 1 = {~5 + 1}")  # -5


# =====================================================================
# 第五部分：位运算实战
# =====================================================================

def demonstrate_bitwise():
    """演示位运算的实战应用"""
    print("\n" + "=" * 60)
    print("🔧 位运算实战")
    print("=" * 60)
    
    # 位运算可视化
    a, b = 0b1101, 0b1011
    print(f"\n   a = {a:4d} = {bin(a):>8s}")
    print(f"   b = {b:4d} = {bin(b):>8s}")
    print(f"   {'─' * 20}")
    print(f"   a & b = {a & b:4d} = {bin(a & b):>8s}  (AND)")
    print(f"   a | b = {a | b:4d} = {bin(a | b):>8s}  (OR)")
    print(f"   a ^ b = {a ^ b:4d} = {bin(a ^ b):>8s}  (XOR)")
    
    # 实战技巧 1: 判断奇偶
    print(f"\n1. 判断奇偶性 (n & 1):")
    for n in range(5):
        print(f"   {n} → {'奇数' if n & 1 else '偶数'}")
    
    # 实战技巧 2: 2的幂判断
    print(f"\n2. 判断 2 的幂 (n & (n-1)):")
    for n in [1, 2, 3, 4, 8, 16, 31, 64]:
        is_pow2 = n > 0 and (n & (n - 1)) == 0
        print(f"   {n:3d} → {'是✓' if is_pow2 else '否'}")
    
    # 实战技巧 3: 位掩码
    print(f"\n3. 使用位掩码管理权限:")
    READ = 0b001
    WRITE = 0b010
    EXECUTE = 0b100
    
    perm = READ | WRITE
    print(f"   初始权限(读+写): {bin(perm)}")
    print(f"   可读: {bool(perm & READ)}")
    print(f"   可执行: {bool(perm & EXECUTE)}")
    
    perm |= EXECUTE
    print(f"   添加执行: {bin(perm)}")
    print(f"   可执行: {bool(perm & EXECUTE)}")
    
    perm &= ~WRITE
    print(f"   移除写: {bin(perm)}")
    print(f"   可写: {bool(perm & WRITE)}")
    
    # 实战技巧 4: XOR 交换
    print(f"\n4. XOR 交换 (无需临时变量):")
    x, y = 5, 9
    print(f"   交换前: x={x}, y={y}")
    x ^= y
    y ^= x
    x ^= y
    print(f"   交换后: x={x}, y={y}")
    
    # 实战技巧 5: 取最低位1
    print(f"\n5. 取最低位 1 (n & -n):")
    n = 0b101100
    print(f"   n = {bin(n)}")
    print(f"   n & -n = {bin(n & -n)} (最低位 1)")
    
    # 清除最低位1
    print(f"   n & (n-1) = {bin(n & (n-1))} (清除最低位 1)")


# =====================================================================
# 第六部分：类型转换
# =====================================================================

def demonstrate_conversion():
    """演示类型转换"""
    print("\n" + "=" * 60)
    print("🔄 类型转换")
    print("=" * 60)
    
    print(f"\n1. 隐式转换 (int → float → complex):")
    print(f"   3 + 2.5: {3 + 2.5} → {type(3 + 2.5)}")
    print(f"   3 + (1+2j): {3 + (1+2j)} → {type(3 + (1+2j))}")
    print(f"   True + 1: {True + 1} (bool是int的子类!)")
    
    print(f"\n2. 显式转换:")
    print(f"   int(3.14) = {int(3.14)} (截断)")
    print(f"   int(-3.14) = {int(-3.14)} (向零取整)")
    print(f"   int('FF', 16) = {int('FF', 16)}")
    print(f"   float('3.14') = {float('3.14')}")
    print(f"   complex(3, 4) = {complex(3, 4)}")
    
    print(f"\n3. 截断 vs 四舍五入:")
    for v in [3.4, 3.5, 3.6, 4.5, -3.5]:
        print(f"   {v:6.1f} → int={int(v):3d}  round={round(v):3d}")

    print(f"\n4. 安全转换函数:")
    def safe_int(val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default
    
    for test in ["42", "3.14", "abc", None, True]:
        print(f"   safe_int({test!r:8s}) = {safe_int(test)}")


# =====================================================================
# 主程序
# =====================================================================

if __name__ == "__main__":
    print("\n" + "★" * 30)
    print("  Day 004 — 数字基础综合演示")
    print("★" * 30)
    
    demonstrate_integers()
    demonstrate_floats()
    demonstrate_complex()
    demonstrate_precedence()
    demonstrate_bitwise()
    demonstrate_conversion()
    
    print("\n" + "=" * 60)
    print("✅ 全部演示完成!")
    print("=" * 60)
