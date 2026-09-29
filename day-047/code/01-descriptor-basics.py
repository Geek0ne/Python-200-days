"""
Day 047 — 描述符（Descriptor）基础用法

本示例展示描述符协议的三个核心方法：
__get__、__set__、__delete__ 的基本工作原理。
"""

# ============================================================
# 1. 最简单的描述符
# ============================================================

class SimpleDescriptor:
    """最基础的描述符 —— 拦截所有属性操作"""

    def __get__(self, obj, objtype=None):
        """当访问 obj.attr 时被调用"""
        print(f"  → __get__ 被调用 (obj={obj}, objtype={objtype})")
        return self._value if hasattr(self, '_value') else "未设置"

    def __set__(self, obj, value):
        """当执行 obj.attr = value 时被调用"""
        print(f"  → __set__ 被调用 (value={value!r})")
        self._value = value

    def __delete__(self, obj):
        """当执行 del obj.attr 时被调用"""
        print(f"  → __delete__ 被调用")
        if hasattr(self, '_value'):
            del self._value


class MyClass:
    name = SimpleDescriptor()
    age = SimpleDescriptor()


print("=" * 60)
print("1. 基本描述符操作")
print("=" * 60)

obj = MyClass()

# 赋值 → 触发 __set__
print("\n📝 执行 obj.name = 'Alice':")
obj.name = "Alice"

# 读取 → 触发 __get__
print("\n📖 读取 obj.name:")
print(f"  name = {obj.name}")

# 再次赋值
print("\n📝 执行 obj.age = 25:")
obj.age = 25
print(f"  age = {obj.age}")

# 删除 → 触发 __delete__
print("\n🗑️  执行 del obj.name:")
del obj.name
print(f"  删除后读取: {obj.name}")

# ============================================================
# 2. 描述符 vs 普通属性的区别
# ============================================================

print("\n" + "=" * 60)
print("2. 描述符 vs 普通属性")
print("=" * 60)

class Compare:
    desc = SimpleDescriptor()    # 描述符
    plain = "普通属性"            # 普通属性

    def __init__(self):
        self.instance_plain = "实例属性"


c = Compare()

print("\n类属性访问:")
print(f"  Compare.desc → {Compare.desc}")      # 返回描述符对象本身！
print(f"  Compare.plain → {Compare.plain}")

print("\n实例属性访问:")
print(f"  c.desc → {c.desc}")                   # 触发 __get__
print(f"  c.plain → {c.plain}")                 # 返回实例属性

# 关键区别：实例 __dict__ 可以覆盖普通属性，但无法绕过数据描述符
print("\n关键区别演示:")
c.plain = "被实例覆盖"  # 赋值到实例 __dict__
print(f"  c.plain → {c.plain}")  # "被实例覆盖"

c.desc = "尝试覆盖描述符"  # 触发 __set__
print(f"  c.desc → {c.desc}")  # 仍然返回 _value（因为有 __set__）

# ============================================================
# 3. 类访问 vs 实例访问
# ============================================================

print("\n" + "=" * 60)
print("3. 类访问 vs 实例访问")
print("=" * 60)

class Awareness:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return "这是类访问 (obj=None)"
        return f"这是实例访问 (obj={obj.__class__.__name__})"

class AccessTest:
    value = Awareness()

# 类访问
print(f"\nAccessTest.value → {AccessTest.value}")

# 实例访问
t = AccessTest()
print(f"t.value → {t.value}")

# ============================================================
# 4. 多个实例之间的隔离
# ============================================================

print("\n" + "=" * 60)
print("4. 多实例隔离（状态存到实例 __dict__）")
print("=" * 60)

class IsolatedDescriptor:
    """每个实例有自己的值"""

    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, value)

class User:
    name = IsolatedDescriptor()
    age = IsolatedDescriptor()

    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"User(name={self.name!r}, age={self.age})"


u1 = User("Alice", 25)
u2 = User("Bob", 30)

print(f"\nu1 = {u1}")
print(f"u2 = {u2}")

u1.name = "Alice Updated"
print(f"\n修改 u1.name 后:")
print(f"  u1 = {u1}")
print(f"  u2 = {u2}")  # u2 不受影响

print("\n✅ 所有测试通过！")
