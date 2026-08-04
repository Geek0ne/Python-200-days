#!/usr/bin/env python3
"""
Day 098 - Python 内部机制
示例 01: 字节码基础 - dis 模块的使用
"""

import dis
import sys
import types


def simple_function():
    """一个简单的函数，用于演示字节码分析"""
    x = 10
    y = 20
    z = x + y
    return z


def if_else_demo(n):
    """if-else 语句的字节码分析"""
    if n > 0:
        return "正数"
    elif n == 0:
        return "零"
    else:
        return "负数"


def for_loop_demo(lst):
    """for 循环的字节码分析"""
    total = 0
    for item in lst:
        total += item
    return total


def list_comprehension_demo(n):
    """列表推导式的字节码分析"""
    return [x ** 2 for x in range(n) if x % 2 == 0]


def try_except_demo():
    """try-except 的字节码分析"""
    try:
        result = 1 / 0
    except ZeroDivisionError:
        result = None
    return result


# ============================================================
# 1. 反汇编函数
# ============================================================
print("=" * 60)
print("1. 反汇编简单函数")
print("=" * 60)
print(f"\n函数源码: simple_function()")
print(f"字节码如下:\n")
dis.dis(simple_function)

print("\n" + "=" * 60)
print("2. 反汇编 if-else 语句")
print("=" * 60)
print(f"\n函数源码: if_else_demo(n)")
print(f"字节码如下:\n")
dis.dis(if_else_demo)

print("\n" + "=" * 60)
print("3. 反汇编 for 循环")
print("=" * 60)
print(f"\n函数源码: for_loop_demo(lst)")
print(f"字节码如下:\n")
dis.dis(for_loop_demo)

print("\n" + "=" * 60)
print("4. 反汇编列表推导式")
print("=" * 60)
print(f"\n函数源码: list_comprehension_demo(n)")
print(f"字节码如下:\n")
dis.dis(list_comprehension_demo)

print("\n" + "=" * 60)
print("5. 反汇编 try-except")
print("=" * 60)
print(f"\n函数源码: try_except_demo()")
print(f"字节码如下:\n")
dis.dis(try_except_demo)


# ============================================================
# 6. Code Object 属性详解
# ============================================================
print("\n" + "=" * 60)
print("6. Code Object 属性详解")
print("=" * 60)

code = simple_function.__code__

print(f"\n函数名: {simple_function.__name__}")
print(f"代码对象类型: {type(code)}")
print(f"源文件: {code.co_filename}")
print(f"第一行行号: {code.co_firstlineno}")
print(f"参数个数: {code.co_argcount}")
print(f"局部变量数: {code.co_nlocals}")
print(f"栈大小: {code.co_stacksize}")
print(f"标志位: {code.co_flags} (二进制: {bin(code.co_flags)})")
print(f"\n常量池 (co_consts): {code.co_consts}")
print(f"变量名 (co_varnames): {code.co_varnames}")
print(f"全局名 (co_names): {code.co_names}")

# 解码标志位
flags = code.co_flags
flag_names = {
    0x01: "CO_OPTIMIZED",
    0x02: "CO_NEWLOCALS",
    0x04: "CO_VARARGS",
    0x08: "CO_VARKEYWORDS",
    0x10: "CO_NESTED",
    0x20: "CO_GENERATOR",
    0x40: "CO_NOFREE",
    0x80: "CO_COROUTINE",
    0x100: "CO_ITERABLE_COROUTINE",
    0x200: "CO_ASYNC_GENERATOR",
}

print(f"\n标志位解析:")
for bit, name in flag_names.items():
    if flags & bit:
        print(f"  ✓ {name} ({hex(bit)})")


# ============================================================
# 7. 字节码指令分析
# ============================================================
print("\n" + "=" * 60)
print("7. 字节码指令分析")
print("=" * 60)

code_bytes = simple_function.__code__.co_code
print(f"\n原始字节码 (hex): {code_bytes.hex()}")
print(f"字节码长度: {len(code_bytes)} 字节")
print(f"指令数: {len(code_bytes) // 2}")

# 手动解析字节码
print(f"\n手动解析字节码:")
for i in range(0, len(code_bytes), 2):
    opcode = code_bytes[i]
    arg = code_bytes[i + 1]
    # 查找操作码名称
    opname = dis.opname[opcode] if opcode < len(dis.opname) else f"UNKNOWN({opcode})"
    print(f"  偏移 {i:2d}: opcode={opcode:3d} ({opname:20s}), arg={arg}")


# ============================================================
# 8. 字节码与性能
# ============================================================
print("\n" + "=" * 60)
print("8. 字节码指令计数")
print("=" * 60)

# 统计各函数的字节码指令
functions = [
    ("simple_function", simple_function),
    ("if_else_demo", if_else_demo),
    ("for_loop_demo", for_loop_demo),
    ("list_comprehension_demo", list_comprehension_demo),
]

for name, func in functions:
    code = func.__code__
    instructions = list(dis.get_instructions(code))
    print(f"\n{name}:")
    print(f"  字节码大小: {len(code.co_code)} 字节")
    print(f"  指令数: {len(instructions)}")
    print(f"  常量数: {len(code.co_consts)}")

    # 统计指令频率
    from collections import Counter
    opcode_counts = Counter(instr.opname for instr in instructions)
    print(f"  指令频率 (Top 5):")
    for opname, count in opcode_counts.most_common(5):
        print(f"    {opname}: {count}")


# ============================================================
# 9. 字节码比较
# ============================================================
print("\n" + "=" * 60)
print("9. 不同写法的字节码比较")
print("=" * 60)

# 方式 1: 普通加法
def add_normal(a, b):
    return a + b

# 方式 2: 使用 operator 模块
import operator

def add_operator(a, b):
    return operator.add(a, b)

print("\n普通加法 (a + b):")
dis.dis(add_normal)

print("\noperator.add(a, b):")
dis.dis(add_operator)

print("\n结论: operator.add 比直接 + 多了模块导入和函数调用开销")


# ============================================================
# 10. 实用技巧
# ============================================================
print("\n" + "=" * 60)
print("10. 实用技巧: 获取函数的字节码统计信息")
print("=" * 60)


def analyze_bytecode(func):
    """分析函数的字节码并返回统计信息"""
    code = func.__code__
    instructions = list(dis.get_instructions(code))

    stats = {
        "name": func.__name__,
        "code_size": len(code.co_code),
        "instruction_count": len(instructions),
        "argcount": code.co_argcount,
        "nlocals": code.co_nlocals,
        "stacksize": code.co_stacksize,
        "consts": code.co_consts,
        "varnames": code.co_varnames,
    }

    # 指令频率
    from collections import Counter
    opcode_counts = Counter(instr.opname for instr in instructions)
    stats["opcode_frequency"] = dict(opcode_counts.most_common(10))

    return stats


# 分析所有示例函数
for name, func in [
    ("simple_function", simple_function),
    ("if_else_demo", if_else_demo),
    ("for_loop_demo", for_loop_demo),
]:
    stats = analyze_bytecode(func)
    print(f"\n{'='*40}")
    print(f"函数: {stats['name']}")
    print(f"  字节码大小: {stats['code_size']} 字节")
    print(f"  指令数: {stats['instruction_count']}")
    print(f"  参数数: {stats['argcount']}")
    print(f"  局部变量数: {stats['nlocals']}")
    print(f"  栈大小: {stats['stacksize']}")
    print(f"  常量: {stats['consts']}")
    print(f"  变量: {stats['varnames']}")
    print(f"  指令频率 (Top 5):")
    for op, count in list(stats["opcode_frequency"].items())[:5]:
        print(f"    {op}: {count}")

print("\n✅ 示例 01 完成！")
