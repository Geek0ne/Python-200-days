#!/usr/bin/env python3
"""
01-default-param-trap.py — 默认参数陷阱演示与正确做法

本文件演示 Python 中默认参数使用可变对象时的"陷阱"，
并给出正确的解决方案。

运行: python3 01-default-param-trap.py
"""

import sys


# ============================================================
# 1. 陷阱演示：可变对象作为默认参数
# ============================================================
print("=" * 60)
print("1️⃣  默认参数陷阱演示")
print("=" * 60)


def add_item(item, items=[]):
    """❌ 陷阱版本：默认参数是可变列表"""
    items.append(item)
    return items


print("\n--- 陷阱版本 ---")
print(f"第1次调用: {add_item('a')}")   # 预期 ['a']
print(f"第2次调用: {add_item('b')}")   # 预期 ['b']，实际 ['a', 'b'] ← 陷阱！
print(f"第3次调用: {add_item('c')}")   # 预期 ['c']，实际 ['a', 'b', 'c'] ← 越来越大！


# ============================================================
# 2. 底层机制证明：id() 和 __defaults__
# ============================================================
print("\n" + "=" * 60)
print("2️⃣  底层机制证明（代码验证）")
print("=" * 60)


def prove_trap(lst=[]):
    """用 id() 证明每次调用用的是同一个列表对象"""
    print(f"  列表的 id: {id(lst):#x}, 内容: {lst}")


print("\n--- id() 证明：每次调用是同一个对象 ---")
prove_trap()  # id: 0x1234
prove_trap()  # id: 0x1234 ← 完全相同！
prove_trap()  # id: 0x1234 ← 还是相同！

print("\n--- __defaults__ 证明：默认参数存在函数对象上 ---")


def inspect_defaults(lst=[]):
    """查看默认参数在 __defaults__ 中的变化"""
    lst.append("x")
    return lst


# 查看 __defaults__ 内容变化
print(f"调用前 __defaults__: {inspect_defaults.__defaults__}")
inspect_defaults()
print(f"第一次调用后 __defaults__: {inspect_defaults.__defaults__}")
inspect_defaults()
print(f"第二次调用后 __defaults__: {inspect_defaults.__defaults__}")

# 证明：__defaults__ 里存的就是 lst 指向的那个列表
print(f"\n默认参数列表与 __defaults__[0] 是同一个对象: "
      f"{inspect_defaults.__defaults__[0] is inspect_defaults.__defaults__[0]}")


# ============================================================
# 3. 陷阱扩展：字典和集合同样中招
# ============================================================
print("\n" + "=" * 60)
print("3️⃣  其他可变类型的陷阱")
print("=" * 60)


def add_to_dict(key, value, cache={}):
    """❌ 陷阱：字典默认参数"""
    cache[key] = value
    return cache


def add_to_set(element, unique=set()):
    """❌ 陷阱：集合默认参数"""
    unique.add(element)
    return unique


print("\n--- 字典陷阱 ---")
print(f"第1次: {add_to_dict('a', 1)}")
print(f"第2次: {add_to_dict('b', 2)}")  # 保留了第一次的结果

print("\n--- 集合陷阱 ---")
print(f"第1次: {add_to_set(1)}")
print(f"第2次: {add_to_set(2)}")  # 保留了第一次的结果

print("\n--- 安全的类型（不可变）不会触发陷阱 ---")


def safe_with_int(x=0):
    """int 是不可变类型，不会触发陷阱"""
    x += 1  # 实际上是重新绑定，不是修改原对象
    return x


def safe_with_str(s=""):
    """str 是不可变类型，不会触发陷阱"""
    s += "!"  # 实际上是创建新字符串
    return s


print(f"  int: {safe_with_int()}, {safe_with_int()}")      # 都是 1
print(f"  str: {safe_with_str('a')}, {safe_with_str('a')}")  # 都是 a!


# ============================================================
# 4. 正确做法：None + 函数体内创建
# ============================================================
print("\n" + "=" * 60)
print("4️⃣  正确做法：None 模式")
print("=" * 60)


def add_item_correct(item, items=None):
    """✅ 正确：使用 None 作为默认值，函数体内创建新列表"""
    if items is None:
        items = []
    items.append(item)
    return items


print("\n--- 列表：None 模式 ---")
print(f"第1次: {add_item_correct('a')}")   # ['a'] ✅
print(f"第2次: {add_item_correct('b')}")   # ['b'] ✅
print(f"第3次: {add_item_correct('c')}")   # ['c'] ✅


def add_to_dict_correct(key, value, cache=None):
    """✅ 正确：字典的 None 模式"""
    if cache is None:
        cache = {}
    cache[key] = value
    return cache


print("\n--- 字典：None 模式 ---")
print(f"第1次: {add_to_dict_correct('a', 1)}")   # {'a': 1} ✅
print(f"第2次: {add_to_dict_correct('b', 2)}")   # {'b': 2} ✅


def add_to_set_correct(element, unique=None):
    """✅ 正确：集合的 None 模式"""
    if unique is None:
        unique = set()
    unique.add(element)
    return unique


print("\n--- 集合：None 模式 ---")
print(f"第1次: {add_to_set_correct(1)}")   # {1} ✅
print(f"第2次: {add_to_set_correct(2)}")   # {2} ✅


# ============================================================
# 5. None 模式的原理
# ============================================================
print("\n" + "=" * 60)
print("5️⃣  None 模式的原理演示")
print("=" * 60)

"""
为什么 None 模式能解决问题？

def add_item_correct(item, items=None):    
                                    │
    def 执行时: items 被赋值为 None   │ 
    None 是一个不可变对象（单例）      │
                                     │
    每次调用:                         │
    if items is None:                │
        items = []  ← 每次调用都      │
                     创建新的列表      │
                                    │
    结果: 每个调用都有自己独立的列表    │
"""


def demonstrate_none_pattern():
    """
    用 id() 证明 None 模式下每次创建新列表
    """
    def inner(lst=None):
        if lst is None:
            lst = []
        print(f"列表 id: {id(lst):#x}")
        return lst

    print("\n--- None 模式下每次创建新对象 ---")
    a = inner()
    b = inner()
    c = inner()
    print(f"a is b: {a is b}")  # False ← 不同的对象!
    print(f"a is c: {a is c}")  # False ← 每个调用独立!


demonstrate_none_pattern()


# ============================================================
# 6. 合法使用场景：利用默认参数陷阱做缓存
# ============================================================
print("\n" + "=" * 60)
print("6️⃣  合法使用：缓存/记忆化")
print("=" * 60)


def fibonacci(n, cache={}):
    """
    带缓存的斐波那契数列 — 利用默认参数陷阱做记忆化

    虽然是"陷阱"行为，但有时正是我们想要的：
    调用之间共享同一个 cache 字典！
    """
    if n in cache:
        return cache[n]
    if n < 2:
        result = n
    else:
        result = fibonacci(n - 1, cache) + fibonacci(n - 2, cache)
    cache[n] = result
    return result


print("\n--- 斐波那契数列（带缓存）---")
for i in range(10):
    print(f"  fibonacci({i}) = {fibonacci(i)}")

print(f"\n缓存内容: {fibonacci.__defaults__[0]}")
print(f"缓存命中次数(键数量): {len(fibonacci.__defaults__[0])}")

# 注意：生产代码中推荐用类或闭包实现缓存，更清晰


# ============================================================
# 7. 总结对比表
# ============================================================
print("\n" + "=" * 60)
print("📋 总结对比")
print("=" * 60)

summary = """
┌──────────────────────┬──────────────────────┬──────────────────────┐
│                      │  陷阱版本 ❌          │  正确版本 ✅          │
├──────────────────────┼──────────────────────┼──────────────────────┤
│  list 默认参数        │  def f(lst=[]):      │  def f(lst=None):    │
│                      │                      │      if lst is None: │
│                      │                      │          lst = []    │
├──────────────────────┼──────────────────────┼──────────────────────┤
│  dict 默认参数        │  def f(d={}):        │  def f(d=None):      │
│                      │                      │      if d is None:   │
│                      │                      │          d = {}      │
├──────────────────────┼──────────────────────┼──────────────────────┤
│  set 默认参数         │  def f(s=set()):     │  def f(s=None):      │
│                      │                      │      if s is None:   │
│                      │                      │          s = set()   │
├──────────────────────┼──────────────────────┼──────────────────────┤
│  原理                 │  def 执行时创建一次    │  每次调用创建新对象      │
│                      │  所有调用共享同一个     │                        │
└──────────────────────┴──────────────────────┴──────────────────────┘
"""
print(summary)

print("\n✅ 结论：默认参数只用不可变类型（None、int、str、tuple、bool）")
print("  需要可变默认值时，在函数体内用 None 守卫创建。")
