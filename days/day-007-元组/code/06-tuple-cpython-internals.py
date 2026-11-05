#!/usr/bin/env python3
"""
06-tuple-cpython-internals.py — Day 007 补充
元组 CPython 底层实现探秘与高级技巧

可直接运行：python3 06-tuple-cpython-internals.py
"""

import sys
import ctypes
import dis
import time
from collections import namedtuple


# ============================================================
# 1. sys.getsizeof — 看底层大小
# ============================================================

def demo_sizeof():
    """分析 list 和 tuple 的内存差异"""
    print("=" * 60)
    print("  1️⃣ 底层内存：list vs tuple 逐字节对比")
    print("=" * 60)

    for n in [0, 1, 2, 3, 5, 10, 20]:
        lst = list(range(n))
        tpl = tuple(range(n))

        lst_size = sys.getsizeof(lst)
        tup_size = sys.getsizeof(tpl)

        # Python int 对象本身 28 字节（64位系统）
        int_overhead = n * 28

        print(f"\n  n={n:2d}:")
        print(f"    list:  {lst_size:4d} bytes (obj={56}+ptr={n*8}+预分配)", end="")
        if n > 0:
            over = lst_size - 56 - n * 8
            if over > 0:
                print(f"+预分配{over}", end="")
        print()
        print(f"    tuple: {tup_size:4d} bytes (obj={40}+ptr={n*8})")
        print(f"    节省:  {lst_size - tup_size:3d} bytes")

    print(f"\n  💡 关键洞察:")
    print(f"     - list 对象头 56 bytes, tuple 对象头 40 bytes")
    print(f"     - list 多 16 bytes 是因为需要存 allocated 字段")
    print(f"     - list 总会有预分配（over-allocating）")
    print(f"     - tuple 精确匹配元素数量，没有浪费")


# ============================================================
# 2. 使用 ctypes 窥探元组底层结构
# ============================================================

def demo_ctypes_inspect():
    """使用 ctypes 直接读取内存，验证 tuple 的结构"""
    print("\n" + "=" * 60)
    print("  2️⃣ ctypes 窥探元组底层结构")
    print("=" * 60)

    # CPython PyObject 结构（C 层）
    class PyObject(ctypes.Structure):
        _fields_ = [
            ("ob_refcnt", ctypes.c_ssize_t),
            ("ob_type", ctypes.c_void_p),
        ]

    # CPython PyVarObject 结构（变长对象）
    class PyVarObject(PyObject):
        _fields_ = [
            ("ob_size", ctypes.c_ssize_t),
        ]

    # CPython PyTupleObject 结构
    class PyTupleObject(PyVarObject):
        _fields_ = [
            # ob_item 是变长数组，但 Python 层面无法直接声明
            # 这里用 ob_item_array 占位
            ("ob_item", ctypes.c_void_p * 1),  # 至少1个
        ]

    t = (10, 20, 30, 40)
    addr = id(t)

    # 强制转换内存地址为 PyTupleObject 指针
    p_tuple = ctypes.cast(addr, ctypes.POINTER(PyTupleObject))

    print(f"\n  元组: {t}")
    print(f"  内存地址: 0x{addr:x}")
    print(f"  ob_refcnt: {p_tuple.contents.ob_refcnt} (引用计数)")
    print(f"  ob_size:   {p_tuple.contents.ob_size} (元素数量)")

    # 读取每个元素
    print(f"\n  遍历元素（通过 ob_item 指针数组）:")
    for i in range(p_tuple.contents.ob_size):
        # 每个 ob_item 是 PyObject* (8 bytes each on 64-bit)
        ptr = ctypes.c_void_p.from_address(
            addr + ctypes.sizeof(PyVarObject) + i * ctypes.sizeof(ctypes.c_void_p)
        )
        obj_addr = ptr.value
        # 通过对象地址获取 Python 对象（危险操作！仅供演示）
        obj = ctypes.cast(obj_addr, ctypes.py_object)
        print(f"    [{i}] = {obj.value}, ptr=0x{obj_addr:x}")

    print(f"\n  ⚠️ 此演示仅用于教学目的，ctypes 直接操作内存有风险！")


# ============================================================
# 3. 字节码反汇编
# ============================================================

def demo_bytecode():
    """反汇编看 list 和 tuple 创建的区别"""
    print("\n" + "=" * 60)
    print("  3️⃣ 字节码反汇编：list vs tuple 创建区别")
    print("=" * 60)

    def create_list():
        return [1, 2, 3, 4, 5]

    def create_tuple():
        return (1, 2, 3, 4, 5)

    print("\n  list 创建字节码:")
    dis.dis(create_list)

    print("\n  tuple 创建字节码:")
    dis.dis(create_tuple)

    print("\n  💡 区别分析:")
    print("     - list: BUILD_LIST + 多个 LOAD_CONST + LIST_APPEND")
    print("     - tuple: 直接 LOAD_CONST 加载整个元组常量")
    print("     - 元组作为常量被存储在 code object 的 co_consts 中")
    print("     - 每次调用创建元组函数，直接返回常量引用（无需构造）")


# ============================================================
# 4. 元组缓存机制（小元组复用）
# ============================================================

def demo_tuple_cache():
    """Python 对小元组的缓存机制"""
    print("\n" + "=" * 60)
    print("  4️⃣ CPython 小元组缓存机制")
    print("=" * 60)

    # CPython 会缓存大小 <= 20 的空元组
    # 这就是"元组池"（tuple freelist）

    # 空元组永远是同一个对象
    empty1 = ()
    empty2 = ()
    print(f"\n  空元组:")
    print(f"    () is () = {empty1 is empty2}  (id: 0x{id(empty1):x} == 0x{id(empty2):x})")

    # 但非空元组不保证复用（尽管有常量折叠）
    t1 = (1, 2)
    t2 = (1, 2)
    print(f"\n  相同内容的元组:")
    print(f"    (1,2) is (1,2) = {t1 is t2}")  # 可能会 is，取决于字节码是否常量折叠
    print(f"    (1,2) == (1,2) = {t1 == t2}")  # 永远 True（值比较）

    # 字符串驻留机制
    s1 = "hello"
    s2 = "hello"
    print(f"\n  字符串驻留:")
    print(f"    'hello' is 'hello' = {s1 is s2}  (Python 会驻留短字符串)")

    # 函数内常量折叠 — 元组作为常量
    def get_tuple():
        return (1, 2, 3)

    def get_tuple2():
        return (1, 2, 3)

    print(f"\n  函数返回相同元组常量:")
    print(f"    get_tuple() is get_tuple2() = {get_tuple() is get_tuple2()}")
    print(f"    (因为同一个 code object 的 co_consts 中同一个元组对象)")


# ============================================================
# 5. 元组的 __hash__ 原理
# ============================================================

def demo_hash_internals():
    """元组哈希的实现机制"""
    print("\n" + "=" * 60)
    print("  5️⃣ 元组哈希实现原理")
    print("=" * 60)

    # 元组的哈希值由所有元素组合计算
    # 公式：hash(tuple) = 常数 + Σ(hash(elem_i) * 某种加权)

    t1 = (1, 2, 3)
    t2 = (1, 2, 3)
    t3 = (3, 2, 1)
    t4 = (1, 2, "three")

    print(f"\n  哈希值:")
    print(f"    hash((1, 2, 3))       = {hash(t1):>20}")
    print(f"    hash((1, 2, 3))       = {hash(t2):>20}")
    print(f"    hash((3, 2, 1))       = {hash(t3):>20}")
    print(f"    hash((1, 2, 'three')) = {hash(t4):>20}")
    print(f"    hash(1)               = {hash(1):>20}")
    print(f"    hash(2)               = {hash(2):>20}")
    print(f"    hash(3)               = {hash(3):>20}")
    print(f"    hash('three')         = {hash('three'):>20}")

    # 重要约束：相同元素顺序必须相同才相等
    print(f"\n  相等性:")
    print(f"    (1,2,3) == (1,2,3) = {t1 == t2}")
    print(f"    (1,2,3) == (3,2,1) = {t1 == t3}  (顺序影响相等性)")

    # 可变 vs 不可变哈希
    print(f"\n  哈希稳定性:")
    t = (1, [2, 3], 4)
    print(f"    含可变元素的元组: {t}")
    print(f"    hash({t}) = ", end="")
    try:
        print(hash(t))
    except TypeError as e:
        print(f"❌ {e}")
    print(f"    💡 包含不可哈希元素的元组，自身也不可哈希")

    # 字典键的哈希一致性
    print(f"\n  元组作为字典键:")
    d = {
        (1, "Alice"): "工程师",
        (2, "Bob"): "设计师",
    }
    print(f"    字典: {d}")
    print(f"    d[(1, 'Alice')] = {d[(1, 'Alice')]}")


# ============================================================
# 主程序
# ============================================================

def main():
    demo_sizeof()
    demo_ctypes_inspect()
    demo_bytecode()
    demo_tuple_cache()
    demo_hash_internals()

    print("\n" + "=" * 60)
    print("  ✅ 元组底层探索完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
