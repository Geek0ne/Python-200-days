"""
Day 036 — 封装与数据隐藏：进阶用法
====================================

涵盖：
1. 描述符协议详解
2. 惰性属性（Lazy Property）
3. __getattr__ / __setattr__ 控制
4. 只读属性与代理模式
5. 属性验证框架
"""


# ====================================
# 1. 描述符协议详解
# ====================================
print("=" * 60)
print("1️⃣ 描述符协议详解")
print("=" * 60)


class NonNegative:
    """描述符：非负数值验证"""

    def __set_name__(self, owner, name):
        """Python 3.6+：自动获取属性名"""
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, 0)

    def __set__(self, obj, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{self.name} 必须是数字")
        if value < 0:
            raise ValueError(f"{self.name} 不能为负")
        obj.__dict__[self.name] = value


class Order:
    """订单类 — 使用描述符验证属性"""

    quantity = NonNegative()
    price = NonNegative()

    def __init__(self, quantity, price):
        self.quantity = quantity
        self.price = price

    @property
    def total(self):
        return self.quantity * self.price

    def __repr__(self):
        return f"Order(qty={self.quantity}, price={self.price}, total={self.total})"


print("  Order 字段验证:")
o = Order(3, 100)
print(f"  {o}")

try:
    o.quantity = -1
except ValueError as e:
    print(f"  ❌ quantity = -1: {e}")

try:
    o.price = "免费"
except TypeError as e:
    print(f"  ❌ price = '免费': {e}")

# 描述符在不同实例间独立
o2 = Order(10, 50)
print(f"  o2 = {o2}")
print(f"  o  = {o}")


# 类型检查描述符
class Typed:
    """类型检查描述符"""

    def __init__(self, name, expected_type):
        self.name = name
        self.expected_type = expected_type

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(
                f"{self.name} 应为 {self.expected_type.__name__}, "
                f"收到 {type(value).__name__}"
            )
        obj.__dict__[self.name] = value


class Person:
    name = Typed("name", str)
    age = Typed("age", int)

    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self):
        return f"Person({self.name}, {self.age})"


print("\n  Typed 描述符:")
p = Person("Alice", 30)
print(f"  {p}")

try:
    Person("Bob", "三十")
except TypeError as e:
    print(f"  ❌ {e}")


# ====================================
# 2. 惰性属性（Lazy Property）
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 惰性属性（Lazy Property）")
print("=" * 60)


class LazyProperty:
    """惰性属性描述符 — 首次访问时计算并缓存"""

    def __init__(self, func):
        self.func = func
        self.name = func.__name__

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # 计算值并缓存到实例字典
        value = self.func(obj)
        obj.__dict__[self.name] = value
        print(f"  🔄 缓存 {self.name} = {value}")
        return value


class DataProcessor:
    """数据处理类 — 使用惰性属性优化性能"""

    def __init__(self, data):
        self.data = data

    @LazyProperty
    def processed(self):
        """大量计算 — 惰性执行"""
        print("  ⏳ 正在处理大量数据...")
        import time
        time.sleep(0.1)  # 模拟耗时
        return [x * 2 for x in self.data]

    @LazyProperty
    def stats(self):
        """统计数据 — 惰性计算"""
        print("  ⏳ 正在计算统计数据...")
        processed = self.processed  # 会触发 processed 的计算
        return {
            'min': min(processed),
            'max': max(processed),
            'sum': sum(processed),
            'avg': sum(processed) / len(processed),
        }


dp = DataProcessor([1, 2, 3, 4, 5])

# 第一次访问 — 触发计算
print("\n  首次访问 processed:")
result = dp.processed
print(f"  result = {result}")

# 第二次访问 — 直接返回缓存
print("\n  再次访问 processed:")
result = dp.processed
print(f"  result = {result}")

# 访问 stats — 同时触发 processed
print("\n  访问 stats:")
stats = dp.stats
print(f"  stats = {stats}")


# 方法二：使用 functools.cached_property (Python 3.8+)
from functools import cached_property


class WeatherData:
    def __init__(self, city):
        self.city = city
        self._fetch_count = 0

    @cached_property
    def forecast(self):
        """天气预报 — 只获取一次"""
        self._fetch_count += 1
        print(f"  🌤️ 获取 {self.city} 天气预报...")
        return {"temp": 25, "humidity": 60, "wind": "5km/h"}

    @cached_property
    def air_quality(self):
        """空气质量 — 只获取一次"""
        print(f"  🌫️ 获取 {self.city} 空气质量...")
        return {"aqi": 42, "pm25": 15}


wd = WeatherData("北京")
print(f"\n  forecast: {wd.forecast}")
print(f"  fetch_count: {wd._fetch_count}")
print(f"  forecast (cached): {wd.forecast}")
print(f"  fetch_count: {wd._fetch_count}")


# ====================================
# 3. __getattr__ / __setattr__ 控制
# ====================================
print("\n" + "=" * 60)
print("3️⃣ __getattr__ / __setattr__ 控制")
print("=" * 60)


class AccessControl:
    """访问控制 — 拦截所有属性读写"""

    def __init__(self):
        self._data = {}
        self._readonly = set()
        self._logger = []

    def __setattr__(self, name, value):
        """所有属性赋值都经过这里"""
        if name.startswith('_'):
            # 内部属性正常处理
            object.__setattr__(self, name, value)
            return

        if name in getattr(self, '_readonly', set()):
            raise AttributeError(f"属性 '{name}' 是只读的")

        self._logger.append(f"SET {name} = {value!r}")
        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        """访问不存在的属性时调用"""
        # 这里可以返回默认值、动态创建等
        if name.startswith('_'):
            raise AttributeError(name)

        self._logger.append(f"GET {name} (不存在)")
        return f"动态属性: {name}"

    def __delattr__(self, name):
        """删除属性时记录"""
        self._logger.append(f"DEL {name}")
        object.__delattr__(self, name)

    def get_log(self):
        """获取操作日志"""
        return self._logger[:]


ac = AccessControl()
print("  __getattr__ 演示:")
print(f"  ac.unknown = {ac.unknown}")
print(f"  ac.dynamic = {ac.dynamic}")

print("\n  __setattr__ 演示:")
ac.name = "Alice"
ac.score = 95
print(f"  ac.name = {ac.name}")

print("\n  操作日志:")
for entry in ac.get_log():
    print(f"    {entry}")


# ====================================
# 4. 只读属性与代理模式
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 只读属性与代理模式")
print("=" * 60)


class ReadOnlyProxy:
    """只读代理 — 保护内部对象不受外部修改"""

    def __init__(self, wrapped):
        # 使用 __dict__ 直接存储，避免触发 __setattr__
        self.__dict__['_wrapped'] = wrapped
        self.__dict__['_readonly'] = True

    def __getattr__(self, name):
        return getattr(self.__dict__['_wrapped'], name)

    def __setattr__(self, name, value):
        if self.__dict__.get('_readonly', False):
            raise AttributeError(
                "此代理是只读的，不能修改属性"
            )
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise AttributeError("此代理是只读的，不能删除属性")


class UserData:
    """原始数据对象"""

    def __init__(self, name, email, age):
        self.name = name
        self.email = email
        self.age = age

    def __repr__(self):
        return f"UserData({self.name}, {self.email})"


user = UserData("Alice", "alice@example.com", 25)
proxy = ReadOnlyProxy(user)

print(f"  读: proxy.name = {proxy.name}")
print(f"  读: proxy.email = {proxy.email}")

try:
    proxy.name = "Bob"
except AttributeError as e:
    print(f"  ❌ 写: {e}")

try:
    del proxy.email
except AttributeError as e:
    print(f"  ❌ 删: {e}")

# 原始对象仍然可变
user.name = "Bob"
print(f"  原始对象修改后 proxy.name = {proxy.name}")


# ====================================
# 5. 属性验证框架
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 属性验证框架")
print("=" * 60)


class Validator:
    """验证器基类"""

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        self.validate(value)
        obj.__dict__[self.name] = value

    def validate(self, value):
        """验证方法 — 子类覆盖"""
        pass


class Range(Validator):
    """范围验证器"""

    def __init__(self, min_val=None, max_val=None):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{self.name} 必须是数字")
        if self.min_val is not None and value < self.min_val:
            raise ValueError(f"{self.name} 不能小于 {self.min_val}")
        if self.max_val is not None and value > self.max_val:
            raise ValueError(f"{self.name} 不能大于 {self.max_val}")


class Length(Validator):
    """字符串长度验证器"""

    def __init__(self, min_len=None, max_len=None):
        self.min_len = min_len
        self.max_len = max_len

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(f"{self.name} 必须是字符串")
        if self.min_len is not None and len(value) < self.min_len:
            raise ValueError(f"{self.name} 长度不能少于 {self.min_len}")
        if self.max_len is not None and len(value) > self.max_len:
            raise ValueError(f"{self.name} 长度不能超过 {self.max_len}")


class Pattern(Validator):
    """正则验证器"""

    def __init__(self, pattern, message=None):
        import re
        self.pattern = re.compile(pattern)
        self.message = message or f"{self.name} 格式不匹配"

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(f"{self.name} 必须是字符串")
        if not self.pattern.match(value):
            raise ValueError(self.message)


class User:
    """用户类 — 使用自定义验证器"""

    name = Length(min_len=2, max_len=50)
    age = Range(min_val=0, max_val=150)
    email = Pattern(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        "邮箱格式不正确"
    )
    score = Range(min_val=0, max_val=100)

    def __init__(self, name, age, email, score=0):
        self.name = name
        self.age = age
        self.email = email
        self.score = score

    def __repr__(self):
        return f"User({self.name}, {self.age}, {self.email}, {self.score})"


print("  带验证器的 User 类:")
u = User("Alice", 28, "alice@example.com", 85)
print(f"  {u}")

try:
    User("A", 20, "a@b.com")
except ValueError as e:
    print(f"  ❌ name='A': {e}")

try:
    User("Bob", -1, "bob@test.com")
except ValueError as e:
    print(f"  ❌ age=-1: {e}")

try:
    User("Charlie", 30, "not-an-email")
except ValueError as e:
    print(f"  ❌ email='not-an-email': {e}")

try:
    User("David", 25, "david@test.com", score=200)
except ValueError as e:
    print(f"  ❌ score=200: {e}")
