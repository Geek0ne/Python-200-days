"""
Day 051 - 弱引用基础用法
主题：weakref 模块核心 API
"""

import weakref
import sys


# ============================================================
# 1. 强引用 vs 弱引用
# ============================================================
print("=" * 60)
print("1. 强引用 vs 弱引用")
print("=" * 60)

class MyClass:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"MyClass({self.name!r})"

# 创建对象
obj = MyClass("hello")

# 强引用计数
ref_count = sys.getrefcount(obj)
print(f"强引用计数: {ref_count}  (实际为 {ref_count - 1})")
print(f"注意: getrefcount 自身也算一个引用，所以减 1")

# 创建弱引用
weak_ref = weakref.ref(obj)
print(f"\n弱引用对象: {weak_ref}")
print(f"弱引用类型: {type(weak_ref)}")
print(f"通过弱引用访问: {weak_ref()}")
print(f"弱引用指向同一对象: {weak_ref() is obj}")

# 弱引用不影响引用计数
print(f"\n创建弱引用后，引用计数: {sys.getrefcount(obj)}")
print("→ 弱引用不增加引用计数！")


# ============================================================
# 2. 弱引用的生命周期
# ============================================================
print("\n" + "=" * 60)
print("2. 弱引用的生命周期")
print("=" * 60)

obj2 = MyClass("world")
weak_ref2 = weakref.ref(obj2)

print(f"对象存在时: {weak_ref2()}")
print(f"对象地址: {id(obj2)}")

del obj2  # 删除强引用

print(f"对象被 del 后: {weak_ref2()}")
print("→ 弱引用返回 None，对象已被回收")


# ============================================================
# 3. 弱引用回调函数
# ============================================================
print("\n" + "=" * 60)
print("3. 弱引用回调函数")
print("=" * 60)

def on_object_deleted(ref):
    """当弱引用指向的对象被回收时，此函数被调用"""
    print(f"  [回调] 对象被回收了！弱引用状态: {ref}")

obj3 = MyClass("callback_test")
ref3 = weakref.ref(obj3, on_object_deleted)

print(f"对象存在: {ref3()}")
print("删除对象...")
del obj3  # 触发回调


# ============================================================
# 4. weakref.proxy() —— 代理对象
# ============================================================
print("\n" + "=" * 60)
print("4. weakref.proxy() 代理对象")
print("=" * 60)

class Calculator:
    def add(self, a, b):
        return a + b
    def multiply(self, a, b):
        return a * b

calc = Calculator()

# 创建代理
proxy = weakref.proxy(calc)

# 代理可以像原对象一样使用
print(f"通过代理调用: {proxy.add(1, 2)}")
print(f"通过代理调用: {proxy.multiply(3, 4)}")
print(f"类型: {type(proxy)}")
print(f"isinstance 检查: {isinstance(proxy, Calculator)}")

# 删除原对象后使用代理会报错
del calc
try:
    proxy.add(1, 2)
except ReferenceError as e:
    print(f"\n代理对象报错: {e}")


# ============================================================
# 5. ref vs proxy 对比
# ============================================================
print("\n" + "=" * 60)
print("5. ref vs proxy 对比")
print("=" * 60)

class TestClass:
    def __init__(self):
        self.value = 42

obj = TestClass()

# ref 方式
ref = weakref.ref(obj)
print(f"ref 需要调用: ref() = {ref()}")
print(f"ref() is obj: {ref() is obj}")

# proxy 方式
proxy = weakref.proxy(obj)
print(f"\nproxy 直接使用: proxy.value = {proxy.value}")
print(f"无法通过 proxy 判断类型: isinstance(proxy, TestClass) = {isinstance(proxy, TestClass)}")

print("\n总结:")
print("  - ref: 更安全，可以通过返回值是否为 None 判断对象是否存活")
print("  - proxy: 更方便，使用体验接近原对象，但无法区分代理和原对象")


# ============================================================
# 6. 哪些对象支持弱引用
# ============================================================
print("\n" + "=" * 60)
print("6. 哪些对象支持弱引用")
print("=" * 60)

class Supported:
    """自定义类，默认支持弱引用"""
    pass

class Slotted:
    """有 __slots__ 的类，默认不支持弱引用"""
    __slots__ = ('name',)
    def __init__(self, name):
        self.name = name

class SlottedWithWeak:
    """有 __slots__ 但显式添加 __weakref__ 的类"""
    __slots__ = ('name', '__weakref__')
    def __init__(self, name):
        self.name = name

# 测试
test_cases = [
    ("自定义类", Supported()),
    ("有 __slots__ 的类", Slotted("test")),
    ("带 __weakref__ 的 slots 类", SlottedWithWeak("test")),
]

for name, obj in test_cases:
    try:
        ref = weakref.ref(obj)
        print(f"✅ {name}: 支持弱引用")
    except TypeError as e:
        print(f"❌ {name}: {e}")

print("\n注意: 内置类型 (list, dict, int, str, tuple) 不支持弱引用！")
