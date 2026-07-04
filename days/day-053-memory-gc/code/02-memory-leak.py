"""
Day 053 - 内存泄漏排查
主题：常见内存泄漏模式与检测
"""

import gc
import sys
from collections import defaultdict


# ============================================================
# 1. 循环引用（可回收）
# ============================================================
print("=" * 60)
print("1. 循环引用（可回收）")
print("=" * 60)

class SimpleNode:
    def __init__(self, name):
        self.name = name
        self.ref = None
    def __repr__(self):
        return f"SimpleNode({self.name!r})"

# 创建循环引用（没有 __del__）
a = SimpleNode("A")
b = SimpleNode("B")
a.ref = b
b.ref = a

del a
del b

# 垃圾回收可以处理
gc.collect()
print("✅ 无 __del__ 的循环引用可以被 GC 回收")


# ============================================================
# 2. 循环引用 + __del__（不可回收）
# ============================================================
print("\n" + "=" * 60)
print("2. 循环引用 + __del__（不可回收）")
print("=" * 60)

class NodeWithDel:
    def __init__(self, name):
        self.name = name
        self.ref = None
    def __del__(self):
        # 有 __del__ 的循环引用对象无法被回收
        pass

a = NodeWithDel("A")
b = NodeWithDel("B")
a.ref = b
b.ref = a

del a
del b

# 尝试回收
gc.collect()

# 检查 gc.garbage
if gc.garbage:
    print(f"⚠️ 无法回收的对象: {len(gc.garbage)}")
    for obj in gc.garbage:
        print(f"  {type(obj).__name__}: {obj}")
else:
    print("✅ 没有无法回收的对象")


# ============================================================
# 3. 全局变量持有引用
# ============================================================
print("\n" + "=" * 60)
print("3. 全局变量持有引用")
print("=" * 60)

# 不良实践：全局缓存
_global_cache = {}

def process_data_bad(data):
    """错误：全局变量持有数据引用"""
    _global_cache[id(data)] = data

# 良好实践：使用弱引用
import weakref
_global_cache_good = weakref.WeakValueDictionary()

def process_data_good(data):
    """正确：使用弱引用"""
    _global_cache_good[id(data)] = data

# 测试
data = list(range(1000))
process_data_bad(data)
print(f"全局缓存大小: {len(_global_cache)}")

del data
gc.collect()
print(f"删除数据后缓存大小: {len(_global_cache)}")  # 仍然持有引用


# ============================================================
# 4. 闭包持有外部变量
# ============================================================
print("\n" + "=" * 60)
print("4. 闭包持有外部变量")
print("=" * 60)

def make_processor():
    """闭包持有 large_data 的引用"""
    large_data = [i for i in range(100000)]
    def processor(x):
        return x in large_data
    return processor

# 测试
processor = make_processor()
print(f"processor 函数: {processor}")
print(f"闭包变量: {processor.__closure__}")
print(f"闭包内容: {[c.cell_contents for c in processor.__closure__]}")

# 即使函数执行完毕，large_data 仍然被持有
del processor
gc.collect()


# ============================================================
# 5. 使用 gc 检测内存增长
# ============================================================
print("\n" + "=" * 60)
print("5. 使用 gc 检测内存增长")
print("=" * 60)

def detect_growth():
    """检测内存增长"""
    gc.collect()
    before = len(gc.get_objects())

    # 模拟一些操作
    data = [dict(zip(range(10), range(10))) for _ in range(1000)]

    gc.collect()
    after = len(gc.get_objects())

    growth = after - before
    print(f"对象数变化: {before} -> {after} (增长 {growth})")

    # 清理
    del data
    gc.collect()

    after_cleanup = len(gc.get_objects())
    print(f"清理后对象数: {after_cleanup}")

    return growth

detect_growth()


# ============================================================
# 6. 使用 gc.get_referrers 追踪引用
# ============================================================
print("\n" + "=" * 60)
print("6. 使用 gc.get_referrers 追踪引用")
print("=" * 60)

class DataHolder:
    def __init__(self, data):
        self.data = data

obj = DataHolder([1, 2, 3])
ref_list = [obj]
ref_dict = {"key": obj}

# 查找所有引用者
referrers = gc.get_referrers(obj)
print(f"DataHolder 实例的引用者: {len(referrers)}")

for ref in referrers:
    ref_type = type(ref).__name__
    if ref_type == 'list':
        print(f"  列表引用: {ref[:3]}...")
    elif ref_type == 'dict':
        print(f"  字典引用: {list(ref.keys())[:3]}...")
    elif ref_type == 'DataHolder':
        print(f"  DataHolder 引用")


# ============================================================
# 7. 内存快照对比
# ============================================================
print("\n" + "=" * 60)
print("7. 内存快照对比")
print("=" * 60)

def memory_snapshot():
    """获取内存快照"""
    gc.collect()
    objects = gc.get_objects()
    type_counts = defaultdict(int)
    for obj in objects:
        type_counts[type(obj).__name__] += 1
    return dict(type_counts)

# 快照 1
snap1 = memory_snapshot()

# 创建一些对象
data = [[i] for i in range(1000)]

# 快照 2
snap2 = memory_snapshot()

# 对比
print("内存快照对比:")
for type_name in set(list(snap1.keys()) + list(snap2.keys())):
    count1 = snap1.get(type_name, 0)
    count2 = snap2.get(type_name, 0)
    diff = count2 - count1
    if abs(diff) > 10:
        print(f"  {type_name}: {count1} -> {count2} ({'+' if diff > 0 else ''}{diff})")


# ============================================================
# 8. 弱引用打破循环
# ============================================================
print("\n" + "=" * 60)
print("8. 弱引用打破循环")
print("=" * 60)

import weakref

class NodeWeak:
    def __init__(self, name):
        self.name = name
        self._parent = None  # 将存储弱引用
        self.children = []

    def add_child(self, child):
        self.children.append(child)
        child._parent = weakref.ref(self)  # 弱引用指向父节点

    @property
    def parent(self):
        if self._parent is not None:
            return self._parent()
        return None

# 创建树结构
root = NodeWeak("root")
child1 = NodeWeak("child1")
child2 = NodeWeak("child2")

root.add_child(child1)
root.add_child(child2)
child1.add_child(NodeWeak("grandchild"))

print(f"root: {root.name}")
print(f"child1.parent: {child1.parent.name}")
print(f"child1.children: {[c.name for c in child1.children]}")

# 删除 root，由于弱引用，不会造成循环引用问题
del root
del child1
del child2
gc.collect()

print("✅ 使用弱引用，树结构可以被正确回收")
