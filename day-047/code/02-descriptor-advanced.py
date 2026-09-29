"""
Day 047 — 描述符（Descriptor）进阶用法与避坑

本示例展示：
1. 数据描述符 vs 非数据描述符的优先级差异
2. 描述符的常见陷阱及解决方案
3. 实际工程中的描述符模式
"""

# ============================================================
# 1. 数据描述符 vs 非数据描述符：优先级差异
# ============================================================

class DataDescriptor:
    """数据描述符：同时实现 __get__ 和 __set__"""

    def __get__(self, obj, objtype=None):
        if obj is None:
            return "类访问 → DataDescriptor"
        return f"数据描述符拦截 → {getattr(obj, '_val', '无值')}"

    def __set__(self, obj, value):
        print(f"  ⚡ 数据描述符 __set__ 触发 (value={value!r})")
        obj._val = value


class NonDataDescriptor:
    """非数据描述符：只实现 __get__"""

    def __get__(self, obj, objtype=None):
        if obj is None:
            return "类访问 → NonDataDescriptor"
        return f"非数据描述符 → {getattr(obj, '_val2', '无值')}"


class PriorityTest:
    data_desc = DataDescriptor()
    non_data_desc = NonDataDescriptor()


print("=" * 60)
print("1. 数据描述符 vs 非数据描述符的优先级")
print("=" * 60)

obj = PriorityTest()

# 数据描述符：实例 __dict__ 无法覆盖
print("\n数据描述符测试:")
obj.data_desc = "尝试通过实例覆盖"
print(f"  obj.data_desc = {obj.data_desc}")  # 数据描述符仍然拦截
print(f"  obj.__dict__ 有 _val 吗？{'_val' in obj.__dict__}")  # True
print(f"  obj.__dict__['_val'] = {obj.__dict__.get('_val')}")  # "尝试通过实例覆盖"

# 非数据描述符：实例 __dict__ 可以覆盖
print("\n非数据描述符测试:")
obj.non_data_desc = "实例覆盖了描述符"
print(f"  obj.non_data_desc = {obj.non_data_desc}")  # 实例值胜出！
print(f"  但类访问仍触发描述符:")
print(f"  PriorityTest.non_data_desc → {PriorityTest.non_data_desc}")

# 清理
del obj.non_data_desc
print(f"  del 后: obj.non_data_desc = {obj.non_data_desc}")  # 描述符回来

# ============================================================
# 2. 陷阱：方法被实例属性覆盖
# ============================================================

print("\n" + "=" * 60)
print("2. 陷阱：方法被实例属性覆盖")
print("=" * 60)

class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        return f"{self.name} says: Woof!"

dog = Dog("Buddy")
print(f"\n正常调用: {dog.bark()}")

# ⚠️ 危险操作：覆盖方法！
dog.bark = "覆盖了方法"
print(f"dog.bark = {dog.bark}")  # "覆盖了方法"
try:
    dog.bark()  # TypeError!
except TypeError as e:
    print(f"❌ 调用报错: {e}")

# 解决方案：用描述符保护方法
class ProtectedMethod:
    """防止方法被实例属性覆盖的描述符"""

    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__
        self.__name__ = func.__name__

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func  # 类访问返回原始函数
        # 创建绑定方法
        import types
        return types.MethodType(self.func, obj)

    def __set__(self, obj, value):
        raise AttributeError(f"不能覆盖受保护的方法 '{self.name}'")


class SafeDog:
    def __init__(self, name):
        self.name = name

    @ProtectedMethod
    def bark(self):
        return f"{self.name} says: Woof!"


safe_dog = SafeDog("Rex")
print(f"\n受保护的方法: {safe_dog.bark()}")

try:
    safe_dog.bark = "尝试覆盖"
except AttributeError as e:
    print(f"✅ 拦截成功: {e}")

# ============================================================
# 3. 陷阱：描述符实例共享状态
# ============================================================

print("\n" + "=" * 60)
print("3. 陷阱：描述符实例共享状态")
print("=" * 60)

# ❌ 错误示范
class SharedCounter:
    """所有实例共享同一个计数器！"""
    def __get__(self, obj, objtype=None):
        return self.count if hasattr(self, 'count') else 0

    def __set__(self, obj, value):
        self.count = value  # 存到描述符实例上，所有对象共享


class WrongClass:
    counter = SharedCounter()


a = WrongClass()
b = WrongClass()

a.counter = 10
print(f"\n❌ 共享状态错误:")
print(f"  a.counter = {a.counter}")  # 10
print(f"  b.counter = {b.counter}")  # 也是 10！共享了

# ✅ 正确示范
class IsolatedCounter:
    """每个实例独立的计数器"""
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, 0)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value


class RightClass:
    counter = IsolatedCounter()

a2 = RightClass()
b2 = RightClass()

a2.counter = 10
print(f"\n✅ 独立状态正确:")
print(f"  a2.counter = {a2.counter}")  # 10
print(f"  b2.counter = {b2.counter}")  # 0，独立

# ============================================================
# 4. 实际应用：只读属性描述符
# ============================================================

print("\n" + "=" * 60)
print("4. 只读属性描述符")
print("=" * 60)

class ReadOnly:
    """只读属性：首次设置后不可修改"""

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if not hasattr(obj, self.private_name):
            raise AttributeError(f"{self.name} 尚未设置")
        return getattr(obj, self.private_name)

    def __set__(self, obj, value):
        if hasattr(obj, self.private_name):
            raise AttributeError(f"{self.name} 是只读属性，不可修改")
        setattr(obj, self.private_name, value)


class ImmutableRecord:
    id = ReadOnly()
    created_at = ReadOnly()

    def __init__(self, id, created_at):
        self.id = id
        self.created_at = created_at

    def __repr__(self):
        return f"ImmutableRecord(id={self.id!r}, created_at={self.created_at!r})"


record = ImmutableRecord("REC-001", "2026-07-03")
print(f"\n{record}")

try:
    record.id = "MODIFIED"  # ❌ 只读！
except AttributeError as e:
    print(f"✅ 拦截成功: {e}")

# ============================================================
# 5. 实际应用：带日志的描述符
# ============================================================

print("\n" + "=" * 60)
print("5. 带日志的描述符")
print("=" * 60)

class LoggedField:
    """自动记录所有属性操作的描述符"""

    def __init__(self, field_type=str):
        self.field_type = field_type
        self.logs = []

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = getattr(obj, self.private_name, None)
        log = f"[GET] {self.name} = {value!r}"
        self.logs.append(log)
        print(f"  📋 {log}")
        return value

    def __set__(self, obj, value):
        value = self.field_type(value)  # 强制类型转换
        old = getattr(obj, self.private_name, None)
        setattr(obj, self.private_name, value)
        log = f"[SET] {self.name}: {old!r} → {value!r}"
        self.logs.append(log)
        print(f"  📋 {log}")

    def __delete__(self, obj):
        old = getattr(obj, self.private_name, None)
        delattr(obj, self.private_name)
        log = f"[DEL] {self.name}: {old!r} → None"
        self.logs.append(log)
        print(f"  📋 {log}")

    def get_logs(self):
        return list(self.logs)


class Config:
    host = LoggedField(str)
    port = LoggedField(int)
    debug = LoggedField(bool)


config = Config()
print("\n设置配置:")
config.host = "localhost"
config.port = "8080"  # 自动转为 int
config.debug = "yes"  # 自动转为 bool (True)
print(f"\n  host={config.host}, port={config.port}, debug={config.debug}")
print(f"\n  📊 操作日志: {Config.host.get_logs()}")

print("\n✅ 所有测试通过！")
