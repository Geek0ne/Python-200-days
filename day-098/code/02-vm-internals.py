#!/usr/bin/env python3
"""
Day 098 - Python 内部机制
示例 02: CPython 虚拟机内部机制 - 栈帧、引用计数、内存管理
"""

import sys
import gc
import ctypes
import dis
import types


# ============================================================
# 1. 栈帧（Frame）操作
# ============================================================
print("=" * 60)
print("1. 栈帧（Frame）操作")
print("=" * 60)


def outer():
    """外部函数"""
    x = 10

    def inner():
        """内部函数"""
        y = 20
        # 获取当前帧
        frame = sys._getframe(0)
        print(f"\n  inner 的帧:")
        print(f"    f_code: {frame.f_code.co_name}")
        print(f"    f_lineno: {frame.f_lineno}")
        print(f"    f_locals: {frame.f_locals}")
        print(f"    f_back: {frame.f_back.f_code.co_name if frame.f_back else None}")

        # 访问外部函数的变量（通过闭包）
        print(f"    闭包变量: {frame.f_back.f_locals.get('x', 'N/A')}")

        return y

    return inner()


print("\n调用 outer() 的栈帧信息:")
result = outer()
print(f"\n返回值: {result}")


# ============================================================
# 2. 调用栈追踪
# ============================================================
print("\n" + "=" * 60)
print("2. 调用栈追踪")
print("=" * 60)


def level_3():
    """第三层函数"""
    frame = sys._getframe(0)
    print(f"\n  level_3 帧:")
    print(f"    函数: {frame.f_code.co_name}")
    _print_call_stack(frame)


def level_2():
    """第二层函数"""
    level_3()


def level_1():
    """第一层函数"""
    level_2()


def _print_call_stack(frame):
    """打印调用栈"""
    depth = 0
    while frame:
        print(f"    [{'  ' * depth}]{frame.f_code.co_name} "
              f"({frame.f_code.co_filename}:{frame.f_lineno})")
        frame = frame.f_back
        depth += 1


print("\n调用栈追踪:")
level_1()


# ============================================================
# 3. 使用 sys.settrace 追踪执行
# ============================================================
print("\n" + "=" * 60)
print("3. 使用 sys.settrace 追踪执行")
print("=" * 60)


def trace_calls(frame, event, arg):
    """追踪函数调用"""
    if event == "call":
        print(f"  [CALL] {frame.f_code.co_name}")
    elif event == "return":
        print(f"  [RETURN] {frame.f_code.co_name} -> {arg}")
    return trace_calls


def traced_function_a():
    x = 1
    return x


def traced_function_b():
    y = traced_function_a()
    return y + 1


# 启用追踪
print("\n启用函数调用追踪:")
sys.settrace(trace_calls)
result = traced_function_b()
sys.settrace(None)  # 禁用追踪
print(f"\n结果: {result}")


# ============================================================
# 4. 引用计数详解
# ============================================================
print("\n" + "=" * 60)
print("4. 引用计数详解")
print("=" * 60)


def demonstrate_refcount():
    """演示引用计数"""
    print("\n引用计数演示:")

    # 创建对象
    a = [1, 2, 3]
    print(f"  a = [1, 2, 3]")
    print(f"  sys.getrefcount(a) = {sys.getrefcount(a)}")  # +1 因为参数本身

    # 增加引用
    b = a
    print(f"\n  b = a")
    print(f"  sys.getrefcount(a) = {sys.getrefcount(a)}")

    # 加入容器
    c = [a]
    print(f"\n  c = [a]")
    print(f"  sys.getrefcount(a) = {sys.getrefcount(a)}")

    # 减少引用
    del b
    print(f"\n  del b")
    print(f"  sys.getrefcount(a) = {sys.getrefcount(a)}")

    # 从容器移除
    c.clear()
    print(f"\n  c.clear()")
    print(f"  sys.getrefcount(a) = {sys.getrefcount(a)}")


demonstrate_refcount()


# ============================================================
# 5. 循环引用与垃圾回收
# ============================================================
print("\n" + "=" * 60)
print("5. 循环引用与垃圾回收")
print("=" * 60)


class Node:
    """节点类，用于演示循环引用"""

    def __init__(self, name):
        self.name = name
        self.ref = None
        print(f"  创建节点: {name}")

    def __del__(self):
        print(f"  销毁节点: {self.name}")


print("\n循环引用演示:")
# 禁用自动 GC 以便观察
gc.disable()

a = Node("A")
b = Node("B")
a.ref = b  # A -> B
b.ref = a  # B -> A (循环引用)

print(f"\n  a 和 b 互相引用")
del a
del b
print("  del a, del b 完成")
print("  注意: __del__ 没有被调用！因为引用计数不为 0")

# 手动触发 GC
print("\n  手动触发垃圾回收...")
gc.collect()
print("  GC 完成，循环引用被清理")

# 重新启用自动 GC
gc.enable()


# ============================================================
# 6. 内存管理详解
# ============================================================
print("\n" + "=" * 60)
print("6. 内存管理详解")
print("=" * 60)

# 6.1 对象内存大小
print("\n不同对象的内存大小:")
objects = [
    ("int (小)", 42),
    ("int (大)", 12345678901234567890),
    ("float", 3.14),
    ("bool", True),
    ("None", None),
    ("空字符串", ""),
    ("短字符串", "hello"),
    ("长字符串", "a" * 100),
    ("空元组", ()),
    ("小元组", (1, 2, 3)),
    ("空列表", []),
    ("小列表", [1, 2, 3]),
    ("空字典", {}),
    ("小字典", {"a": 1}),
]

for name, obj in objects:
    print(f"  {name:15s}: {sys.getsizeof(obj):4d} bytes")

# 6.2 对象池
print("\n\n小整数缓存池演示:")
a = 256
b = 256
print(f"  a = 256, b = 256")
print(f"  a is b: {a is b}")  # True - 同一个对象

a = 257
b = 257
print(f"\n  a = 257, b = 257")
print(f"  a is b: {a is b}")  # 在交互式环境中为 False

# 6.3 intern 机制
print("\n\n字符串 intern 机制:")
s1 = "hello"
s2 = "hello"
print(f"  s1 = 'hello', s2 = 'hello'")
print(f"  s1 is s2: {s1 is s2}")  # True - intern 机制

# 使用 sys.intern 可以显式 intern 字符串
s3 = sys.intern("hello world")
s4 = sys.intern("hello world")
print(f"\n  s3 = sys.intern('hello world')")
print(f"  s4 = sys.intern('hello world')")
print(f"  s3 is s4: {s3 is s4}")  # True


# ============================================================
# 7. gc 模块详解
# ============================================================
print("\n" + "=" * 60)
print("7. gc 模块详解")
print("=" * 60)

# 获取 GC 统计
print("\nGC 统计信息:")
stats = gc.get_stats()
for i, gen in enumerate(stats):
    print(f"  Generation {i}:")
    print(f"    collections: {gen['collections']}")
    print(f"    collected: {gen['collected']}")
    print(f"    uncollectable: {gen['uncollectable']}")

# 获取 GC 阈值
print(f"\nGC 阈值: {gc.get_threshold()}")

# 获取当前 GC 中的对象
print(f"\nGC 中的对象数: {len(gc.get_objects())}")

# 查找不可回收的对象
print(f"不可回收对象: {gc.garbage}")


# ============================================================
# 8. ctypes 直接操作内存
# ============================================================
print("\n" + "=" * 60)
print("8. ctypes 直接操作内存")
print("=" * 60)

# 获取对象的内存地址
x = 42
print(f"\n对象 x = {x}")
print(f"  id(x): {id(x)}")
print(f"  十六进制地址: {hex(id(x))}")

# 使用 ctypes 读取引用计数
# 注意: 这是一个高级技巧，仅用于学习目的
print(f"\n引用计数 (通过 sys.getrefcount): {sys.getrefcount(x)}")

# 查看 PyObject 结构（概念性）
print(f"\nPyObject 内存布局（概念性）:")
print(f"  ┌─────────────────────┐")
print(f"  │ ob_refcnt (8 bytes) │  ← 引用计数")
print(f"  │ ob_type (8 bytes)   │  ← 类型指针 -> int")
print(f"  ├─────────────────────┤")
print(f"  │ ob_digit (4 bytes)  │  ← 整数值: {x}")
print(f"  └─────────────────────┘")


# ============================================================
# 9. 字节码修改技巧（高级）
# ============================================================
print("\n" + "=" * 60)
print("9. 字节码修改技巧（高级 - 仅学习用）")
print("=" * 60)


def original_func():
    """原始函数"""
    return 42


def modified_func():
    """修改后的函数"""
    return 100


print("\n原始函数字节码:")
dis.dis(original_func)

print("\n修改后函数字节码:")
dis.dis(modified_func)

# 注意: 直接修改字节码是危险的，这里仅演示概念
# 实际上可以通过修改 co_code 属性来改变函数行为
print("\n注意: 直接修改字节码是危险的操作，仅用于学习目的！")


# ============================================================
# 10. 性能分析工具
# ============================================================
print("\n" + "=" * 60)
print("10. 性能分析: 字节码级别的函数调用开销")
print("=" * 60)

import timeit


def simple_add(a, b):
    return a + b


def function_call_add(a, b):
    def inner(x, y):
        return x + y
    return inner(a, b)


# 测量性能差异
n = 1000000

t1 = timeit.timeit("simple_add(1, 2)", globals=globals(), number=n)
t2 = timeit.timeit("function_call_add(1, 2)", globals=globals(), number=n)

print(f"\n简单加法: {t1:.4f} 秒 ({n} 次)")
print(f"函数调用加法: {t2:.4f} 秒 ({n} 次)")
print(f"函数调用开销: {(t2 - t1) / t1 * 100:.1f}%")

print("\n✅ 示例 02 完成！")
