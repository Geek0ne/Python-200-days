"""
Day 050 - 槽(__slots__) - 进阶用法与避坑
演示：__slots__ 与继承、@dataclass、常见陷阱
"""
import sys
from dataclasses import dataclass


# ============================================
# 1. __slots__ 与继承
# ============================================

class Base:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y


class Child(Base):
    __slots__ = ('z',)  # 只声明自己的新槽位

    def __init__(self, x, y, z):
        super().__init__(x, y)
        self.z = z


class GrandChild(Child):
    __slots__ = ('w',)  # 继续声明新槽位

    def __init__(self, x, y, z, w):
        super().__init__(x, y, z)
        self.w = w


print("=== __slots__ 与继承 ===")
obj = GrandChild(1, 2, 3, 4)
print(f"x={obj.x}, y={obj.y}, z={obj.z}, w={obj.w}")
print(f"有 __dict__? {hasattr(obj, '__dict__')}")
print(f"对象大小: {sys.getsizeof(obj)} bytes")


# ============================================
# 2. 不声明 __slots__ 的子类
# ============================================

class Parent:
    __slots__ = ('x',)

    def __init__(self, x):
        self.x = x


class ChildWithoutSlots(Parent):
    """子类没有声明 __slots__ — 会恢复 __dict__！"""

    def __init__(self, x, extra):
        super().__init__(x)
        self.extra = extra  # 这个属性会存入 __dict__


class ChildWithSlots(Parent):
    """子类声明了 __slots__ — 保持优化"""

    __slots__ = ('extra',)

    def __init__(self, x, extra):
        super().__init__(x)
        self.extra = extra


print("\n--- 不声明 __slots__ 的子类 ---")
c1 = ChildWithoutSlots(1, "hello")
c2 = ChildWithSlots(1, "hello")

print(f"ChildWithoutSlots 有 __dict__: {hasattr(c1, '__dict__')}")
print(f"ChildWithSlots 有 __dict__: {hasattr(c2, '__dict__')}")
print(f"ChildWithoutSlots 大小: {sys.getsizeof(c1)} bytes")
print(f"ChildWithSlots 大小: {sys.getsizeof(c2)} bytes")

# ChildWithoutSlots 可以添加动态属性
c1.new_attr = "动态添加"
print(f"ChildWithoutSlots 动态属性: {c1.new_attr}")

try:
    c2.new_attr = "不允许"
except AttributeError as e:
    print(f"ChildWithSlots 动态属性失败: {e}")


# ============================================
# 3. @dataclass 与 __slots__
# ============================================

# Python 3.10+ 支持 dataclass(slots=True)
try:
    @dataclass(slots=True)
    class PointDataclass:
        x: float
        y: float
        z: float

    print("\n--- @dataclass(slots=True) ---")
    p = PointDataclass(1.0, 2.0, 3.0)
    print(f"点: {p}")
    print(f"有 __dict__: {hasattr(p, '__dict__')}")
    print(f"大小: {sys.getsizeof(p)} bytes")
except TypeError:
    print("\n--- @dataclass(slots=True) ---")
    print("Python 版本 < 3.10，不支持 slots=True")
    print("替代方案：手动定义 __slots__")


# 手动为 dataclass 添加 __slots__（兼容旧版本）
@dataclass
class PointManualSlots:
    __slots__ = ('x', 'y', 'z')
    x: float
    y: float
    z: float


print("\n--- 手动 @dataclass + __slots__ ---")
p = PointManualSlots(1.0, 2.0, 3.0)
print(f"点: {p}")
print(f"有 __dict__: {hasattr(p, '__dict__')}")
print(f"大小: {sys.getsizeof(p)} bytes")


# ============================================
# 4. __slots__ 的常见陷阱
# ============================================

print("\n--- 常见陷阱 ---")

# 陷阱1：忘记声明新槽位
class TrapBase:
    __slots__ = ('x',)

class TrapChild(TrapBase):
    # 忘记声明 __slots__
    def __init__(self, x, y):
        super().__init__(x)
        self.y = y

trap = TrapChild(1, 2)
print(f"陷阱1 - 忘记声明 __slots__:")
print(f"  有 __dict__: {hasattr(trap, '__dict__')}")
print(f"  可以动态添加: {hasattr(trap, '__dict__')}")


# 陷阱2：默认值问题
class TrapDefaults:
    __slots__ = ('x', 'y')

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

# ⚠️ slot 没有默认值机制，需要手动处理
t = TrapDefaults()  # OK
print(f"\n陷阱2 - 默认值: x={t.x}, y={t.y}")


# 陷阱3：弱引用
import weakref

class TrapWeakRef:
    __slots__ = ('x',)

t = TrapWeakRef()
t.x = 10
try:
    ref = weakref.ref(t)  # ❌ 需要声明 '__weakref__' slot
    print(f"\n陷阱3 - 弱引用: {ref()}")
except TypeError as e:
    print(f"\n陷阱3 - 弱引用失败: {e}")
    print("  解决: __slots__ = ('x', '__weakref__')")


# 正确的弱引用支持
class CorrectWeakRef:
    __slots__ = ('x', '__weakref__')

obj = CorrectWeakRef()
obj.x = 10
ref = weakref.ref(obj)
print(f"  正确支持弱引用: {ref() is obj}")


# 陷阱4：pickle 序列化
import pickle

class TrapPickle:
    __slots__ = ('x',)

try:
    obj = TrapPickle()
    obj.x = 10
    data = pickle.dumps(obj)
    obj2 = pickle.loads(data)
    print(f"\n陷阱4 - pickle: x={obj2.x}")
except Exception as e:
    print(f"\n陷阱4 - pickle 失败: {e}")
    print("  解决: 定义 __getstate__ 和 __setstate__")


# ============================================
# 5. 最佳实践
# ============================================

print("\n" + "=" * 50)
print("__slots__ 最佳实践：")
print("=" * 50)
print("""
✅ DO:
  - 大量相同结构的对象使用 __slots__
  - 子类也要声明 __slots__
  - 需要弱引用时添加 '__weakref__'
  - 需要 pickle 时实现 __getstate__/__setstate__

❌ DON'T:
  - 不要忘记子类声明 __slots__
  - 不要指望 __slots__ 防止所有动态属性
  - 不要对频繁修改结构的类使用 __slots__
  - 不要对需要 __dict__ 的框架（如某些 ORM）使用
""")
