"""
Day 053 - 垃圾回收基础
主题：gc 模块核心 API
"""

import gc
import sys


# ============================================================
# 1. 引用计数机制
# ============================================================
print("=" * 60)
print("1. 引用计数机制")
print("=" * 60)

class MyClass:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"MyClass({self.name!r})"

obj = MyClass("test")
print(f"创建对象后引用计数: {sys.getrefcount(obj)}")  # 2

# 增加引用
b = obj
c = obj
print(f"增加引用后: {sys.getrefcount(obj)}")  # 4

# 减少引用
del b
del c
print(f"减少引用后: {sys.getrefcount(obj)}")  # 2


# ============================================================
# 2. gc 模块基础
# ============================================================
print("\n" + "=" * 60)
print("2. gc 模块基础")
print("=" * 60)

# 检查 GC 状态
print(f"GC 启用: {gc.isenabled()}")
print(f"自动回收: {gc.isenabled()}")

# 获取回收阈值
print(f"回收阈值: {gc.get_threshold()}")

# 获取各代对象数
print(f"各代对象数: {gc.get_count()}")


# ============================================================
# 3. 手动触发垃圾回收
# ============================================================
print("\n" + "=" * 60)
print("3. 手动触发垃圾回收")
print("=" * 60)

class Node:
    def __init__(self, name):
        self.name = name
        self.ref = None
    def __del__(self):
        print(f"  回收: {self.name}")

# 创建循环引用
a = Node("A")
b = Node("B")
a.ref = b
b.ref = a

print("删除对象前:")
print(f"  a is None: {a is None}")
print(f"  b is None: {b is None}")

del a
del b

print("\n删除对象后（del 之后立即检查）:")
print("  循环引用仍然存在，需要 GC 处理")

print("\n触发垃圾回收:")
collected = gc.collect()
print(f"  回收对象数: {collected}")


# ============================================================
# 4. 分代回收
# ============================================================
print("\n" + "=" * 60)
print("4. 分代回收")
print("=" * 60)

# 查看各代统计信息
stats = gc.get_stats()
print("各代回收统计:")
for i, stat in enumerate(stats):
    print(f"  第 {i} 代:")
    print(f"    收集次数: {stat['collections']}")
    print(f"    收集对象数: {stat['collected']}")
    print(f"    不可收集对象: {stat['uncollectable']}")

# 创建大量对象触发回收
print("\n创建大量对象...")
before_count = gc.get_count()
data = [dict(zip(range(100), range(100))) for _ in range(1000)]
after_count = gc.get_count()

print(f"创建前各代对象数: {before_count}")
print(f"创建后各代对象数: {after_count}")


# ============================================================
# 5. gc.get_objects() 查看所有对象
# ============================================================
print("\n" + "=" * 60)
print("5. gc.get_objects() 查看所有对象")
print("=" * 60)

# 获取所有对象
all_objects = gc.get_objects()
print(f"当前对象总数: {len(all_objects)}")

# 按类型统计
from collections import Counter
type_counts = Counter(type(obj).__name__ for obj in all_objects)

print("\n占用最多的类型 (Top 10):")
for type_name, count in type_counts.most_common(10):
    print(f"  {type_name}: {count}")


# ============================================================
# 6. gc.get_referrers() 查看引用者
# ============================================================
print("\n" + "=" * 60)
print("6. gc.get_referrers() 查看引用者")
print("=" * 60)

class TrackedClass:
    pass

obj = TrackedClass()
ref1 = obj
ref2 = [obj]

# 查看谁引用了这个对象
referrers = gc.get_referrers(obj)
print(f"引用 TrackedClass 实例的对象数量: {len(referrers)}")

for ref in referrers:
    ref_type = type(ref).__name__
    if ref_type == 'list':
        print(f"  列表: {ref}")
    elif ref_type == 'dict':
        print(f"  字典: ...")
    elif ref_type == 'TrackedClass':
        print(f"  TrackedClass 实例")


# ============================================================
# 7. gc.get_referents() 查看引用的对象
# ============================================================
print("\n" + "=" * 60)
print("7. gc.get_referents() 查看引用的对象")
print("=" * 60)

class Container:
    def __init__(self):
        self.data = [1, 2, 3]
        self.name = "container"

obj = Container()
referents = gc.get_referents(obj)

print(f"Container 实例引用的对象数量: {len(referents)}")
for ref in referents:
    print(f"  {type(ref).__name__}: {ref!r:.50}")


# ============================================================
# 8. 调试选项
# ============================================================
print("\n" + "=" * 60)
print("8. 调试选项")
print("=" * 60)

# 启用调试
gc.set_debug(gc.DEBUG_STATS)
print("已启用 DEBUG_STATS")

# 执行回收（会打印统计信息）
gc.collect()

# 禁用调试
gc.set_debug(0)
print("已禁用调试")


# ============================================================
# 9. 禁用/启用垃圾回收
# ============================================================
print("\n" + "=" * 60)
print("9. 禁用/启用垃圾回收")
print("=" * 60)

# 禁用 GC
gc.disable()
print(f"GC 禁用后: {gc.isenabled()}")

# 手动回收仍然有效
gc.collect()

# 重新启用
gc.enable()
print(f"GC 启用后: {gc.isenabled()}")
