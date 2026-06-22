"""
Day 033 — 继承：进阶用法
======================================================================
C3 线性化算法、Mixin 模式、__init_subclass__、抽象基类、钻石问题
======================================================================
"""

from abc import ABC, abstractmethod
import json
from datetime import datetime

# ====================================================================
# 1. C3 线性化算法详解
# ====================================================================
print("=" * 60)
print("1️⃣  C3 线性化算法详解")
print("=" * 60)


class O: pass

class A(O): pass
class B(O): pass
class C(O): pass

class D(A, B): pass
class E(B, C): pass
class F(D, E): pass


def show_mro(cls, name=""):
    mro = cls.__mro__
    print(f"\n  {name or cls.__name__}.__mro__:")
    for i, c in enumerate(mro):
        indent = "  " * (i + 1)
        print(f"{indent}{'→ ' if i > 0 else ''}{c.__name__}")


print("  菱形继承链:")
show_mro(F, "F(D, E)")

print(f"\n  C3 线性化验证:")
print(f"    F = D + E + merge(L[D], L[E], [D, E])")
print(f"    L[D] = D, A, B, O")
print(f"    L[E] = E, B, C, O")
print(f"    L[F] = F, D, A, E, B, C, O")
print(f"    ✓ 验证: {[c.__name__ for c in F.__mro__]}")
print(f"    ✓ D 先于 E (声明顺序)")
print(f"    ✓ A 先于 B, E (单调性)")


# ====================================================================
# 2. 钻石问题 (Diamond Problem)
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  钻石问题 — Python 的解决方案")
print("=" * 60)


class Base:
    """基数"""
    value = "Base"

    def whoami(self):
        return "Base"

    def process(self):
        return f"Base.process"


class Left(Base):
    value = "Left"

    def whoami(self):
        return "Left"

    def process(self):
        return f"Left.process → {super().process()}"


class Right(Base):
    value = "Right"

    def whoami(self):
        return "Right"

    def process(self):
        return f"Right.process → {super().process()}"


class Diamond(Left, Right):
    """钻石继承"""

    def whoami(self):
        return "Diamond"

    def process(self):
        return f"Diamond.process → {super().process()}"


print("  钻石继承示例:")
print(f"    MRO: {[c.__name__ for c in Diamond.__mro__]}")

d = Diamond()
print(f"    d.value = {d.value}")            # → Left (第一个父类)
print(f"    d.whoami() = {d.whoami()}")       # → Diamond
print(f"    d.process() = {d.process()}")
print(f"    → Diamond → Left → Right → Base")
print(f"    → 注意: super() 在 Left 中调用了 Right (不是 Base!)")


# ====================================================================
# 3. Mixin 模式
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  Mixin 模式 — 功能组合")
print("=" * 60)


class SerializableMixin:
    """序列化 Mixin — 提供 JSON/YAML 序列化"""

    def to_dict(self):
        """转换为字典"""
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif hasattr(value, 'to_dict'):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result

    def to_json(self, **kwargs):
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), **kwargs, ensure_ascii=False)


class ValidateMixin:
    """验证 Mixin — 提供属性验证"""

    _validations = {}

    @classmethod
    def add_validation(cls, attr_name, validator):
        """添加属性验证规则"""
        if attr_name not in cls._validations:
            cls._validations[attr_name] = []
        cls._validations[attr_name].append(validator)
        return cls

    def validate(self):
        """验证所有属性"""
        errors = []
        for attr_name, validators in self._validations.items():
            if not hasattr(self, attr_name):
                continue
            value = getattr(self, attr_name)
            for validator in validators:
                try:
                    validator(value)
                except (ValueError, TypeError) as e:
                    errors.append(f"{attr_name}: {e}")
        return errors


class LogMixin:
    """日志 Mixin"""

    def log(self, action, details=""):
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"  📝 [{timestamp}] [{self.__class__.__name__}] {action}: {details}")


class TimestampMixin:
    """时间戳 Mixin"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'created_at'):
            self.created_at = datetime.now()
        self.updated_at = datetime.now()


# 使用 Mixin 组合功能
class Product(SerializableMixin, ValidateMixin, LogMixin, TimestampMixin):
    """商品 — 组合多个 Mixin"""

    def __init__(self, name, price, stock):
        super().__init__()
        self.name = name
        self.price = price
        self.stock = stock
        self.log("创建", f"{name} (${price}, {stock}pcs)")


# 添加验证规则
Product.add_validation("price", lambda v: v > 0 or (_ for _ in ()).throw(
    ValueError("价格必须为正数")))
Product.add_validation("stock", lambda v: v >= 0 or (_ for _ in ()).throw(
    ValueError("库存不能为负数")))

print("  使用 Mixin 组合: ")
product = Product("Python Book", 39.99, 100)

print(f"\n  验证结果: {product.validate()}")
print(f"  JSON: {product.to_json(indent=2, sort_keys=True)}")

try:
    bad_product = Product("Bad", -10, -5)
except Exception as e:
    print(f"\n  验证失败: {e}")


# ====================================================================
# 4. __init_subclass__ — 子类注册钩子
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  __init_subclass__ — 子类自动注册")
print("=" * 60)


class PluginRegistry:
    """插件注册器"""
    _plugins = {}
    _enabled = {}

    def __init_subclass__(cls, plugin_name=None, **kwargs):
        """当子类被定义时自动调用"""
        super().__init_subclass__(**kwargs)
        name = plugin_name or cls.__name__
        PluginRegistry._plugins[name] = cls
        PluginRegistry._enabled[name] = True
        print(f"  📦 注册插件: {name} → {cls.__name__}")

    @classmethod
    def get_plugin(cls, name):
        return cls._plugins.get(name)

    @classmethod
    def list_plugins(cls):
        return list(cls._plugins.keys())

    @classmethod
    def disable(cls, name):
        if name in cls._enabled:
            cls._enabled[name] = False

    @classmethod
    def is_enabled(cls, name):
        return cls._enabled.get(name, False)

    def process(self, data):
        """子类实现具体处理"""
        raise NotImplementedError


class UppercasePlugin(PluginRegistry, plugin_name="uppercase"):
    def process(self, data):
        return data.upper()


class ReversePlugin(PluginRegistry, plugin_name="reverse"):
    def process(self, data):
        return data[::-1]


class StripPlugin(PluginRegistry, plugin_name="strip"):
    def process(self, data):
        return data.strip()


print(f"\n  已注册插件: {PluginRegistry.list_plugins()}")

# 使用插件
data = "  Hello World  "
for name in PluginRegistry.list_plugins():
    plugin_cls = PluginRegistry.get_plugin(name)
    if plugin_cls and PluginRegistry.is_enabled(name):
        plugin = plugin_cls()
        result = plugin.process(data)
        print(f"  🔧 {name}: '{data}' → '{result}'")


# ====================================================================
# 5. 抽象基类与接口约束
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  抽象基类 — 定义接口规范")
print("=" * 60)


class DataSource(ABC):
    """数据源抽象接口"""

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def fetch(self, query):
        pass

    @abstractmethod
    def close(self):
        pass

    # 模板方法模式
    def query(self, query):
        """模板方法 — 定义执行流程"""
        try:
            self.connect()
            result = self.fetch(query)
            return result
        finally:
            self.close()


class DatabaseSource(DataSource):
    def __init__(self, connection_string):
        self.conn_str = connection_string
        self._connected = False

    def connect(self):
        print(f"  🔗 连接数据库: {self.conn_str}")
        self._connected = True

    def fetch(self, query):
        print(f"  📊 执行查询: {query}")
        return [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    def close(self):
        print(f"  🔒 关闭连接")
        self._connected = False


class APISource(DataSource):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def connect(self):
        print(f"  🌐 连接 API: {self.endpoint}")

    def fetch(self, query):
        print(f"  📡 请求数据: {query}")
        return {"status": "ok", "data": ["item1", "item2"]}

    def close(self):
        print(f"  🔌 关闭连接")


print("  使用抽象接口:")
db = DatabaseSource("postgresql://localhost/mydb")
result = db.query("SELECT * FROM users")
print(f"    结果: {result}")

api = APISource("https://api.example.com")
result = api.query("get_items")
print(f"    结果: {result}")

# 验证类型
print(f"\n  类型检查:")
print(f"    isinstance(db, DataSource): {isinstance(db, DataSource)}")
print(f"    isinstance(api, DataSource): {isinstance(api, DataSource)}")
print(f"    issubclass(DatabaseSource, DataSource): {issubclass(DatabaseSource, DataSource)}")


print("\n" + "=" * 60)
print("✅  Day 33 进阶用法演示完成!")
print("=" * 60)
