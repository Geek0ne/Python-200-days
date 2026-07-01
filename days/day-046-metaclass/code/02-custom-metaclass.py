"""
Day 046 — 元类 进阶用法：自定义元类

本文件演示：
1. 自定义元类的基本结构
2. __new__、__init__、__call__ 的区别
3. 元类的实战应用
4. 元类的常见陷阱与避坑
"""


# ============================================================
# 1. 基础自定义元类
# ============================================================

print("=== 1. 基础自定义元类 ===")

class DebugMeta(type):
    """调试元类：在类创建和实例化时打印信息"""
    
    def __new__(mcs, name, bases, attrs):
        print(f"  📦 创建类: {name}")
        print(f"     基类: {bases}")
        print(f"     属性: {list(attrs.keys())}")
        return super().__new__(mcs, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        print(f"  🔧 初始化类: {name}")
        super().__init__(name, bases, attrs)
    
    def __call__(cls, *args, **kwargs):
        print(f"  🏭 实例化: {cls.__name__}")
        instance = super().__call__(*args, **kwargs)
        print(f"  ✅ 实例创建完成: {instance}")
        return instance


class Base(metaclass=DebugMeta):
    pass

print("---")
class Child(Base):
    pass

print("---")
obj = Child()
print(f"obj 的类型: {type(obj)}")


# ============================================================
# 2. 自动属性转大写
# ============================================================

print("\n=== 2. 自动属性转大写 ===")

class UpperAttrMeta(type):
    """将类的所有非 dunder 属性名转为大写"""
    
    def __new__(mcs, name, bases, attrs):
        uppercase_attrs = {}
        for key, value in attrs.items():
            if not key.startswith('__'):
                uppercase_attrs[key.upper()] = value
            else:
                uppercase_attrs[key] = value
        return super().__new__(mcs, name, bases, uppercase_attrs)

class Config(metaclass=UpperAttrMeta):
    database = "postgresql"
    host = "localhost"
    port = 5432
    debug = True

print(f"Database: {Config.DATABASE}")   # postgresql
print(f"Host: {Config.HOST}")           # localhost
print(f"Port: {Config.PORT}")           # 5432
print(f"Debug: {Config.DEBUG}")         # True


# ============================================================
# 3. 元类实现单例模式
# ============================================================

print("\n=== 3. 元类实现单例模式 ===")

class SingletonMeta(type):
    """使用元类实现单例"""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Logger(metaclass=SingletonMeta):
    def __init__(self):
        self.logs = []
    
    def log(self, message):
        self.logs.append(message)
        print(f"  📝 {message}")

log1 = Logger()
log1.log("第一次日志")

log2 = Logger()
log2.log("第二次日志")

print(f"log1 is log2: {log1 is log2}")  # True
print(f"日志数量: {len(log1.logs)}")     # 2（共享同一个实例）


# ============================================================
# 4. 元类实现自动注册
# ============================================================

print("\n=== 4. 元类实现自动注册 ===")

class PluginRegistry(type):
    """自动注册所有插件类"""
    _registry = {}
    
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        if bases:  # 只注册子类，不注册基类
            mcs._registry[name] = cls
            print(f"  📋 已注册插件: {name}")
        return cls
    
    @classmethod
    def get_all_plugins(mcs):
        return dict(mcs._registry)

class Plugin(metaclass=PluginRegistry):
    def execute(self):
        raise NotImplementedError

class AuthPlugin(Plugin):
    def execute(self):
        return "身份验证完成"

class CachePlugin(Plugin):
    def execute(self):
        return "缓存已初始化"

class LogPlugin(Plugin):
    def execute(self):
        return "日志系统就绪"

# 使用注册表
print("\n所有已注册的插件:")
for name, cls in PluginRegistry.get_all_plugins().items():
    instance = cls()
    result = instance.execute()
    print(f"  {name}: {result}")


# ============================================================
# 5. 元类实现自动添加 __repr__
# ============================================================

print("\n=== 5. 元类实现自动添加 __repr__ ===")

class AutoReprMeta(type):
    """根据类的非 dunder 属性自动生成 __repr__"""
    
    def __new__(mcs, name, bases, attrs):
        # 收集非 dunder、非方法的属性名
        fields = []
        for key, value in attrs.items():
            if not key.startswith('_') and not callable(value):
                fields.append(key)
        
        def __repr__(self):
            values = ', '.join(
                f'{f}={getattr(self, f)!r}' for f in fields
            )
            return f'{name}({values})'
        
        attrs['__repr__'] = __repr__
        return super().__new__(mcs, name, bases, attrs)

class Point(metaclass=AutoReprMeta):
    x = 0
    y = 0

class Person(metaclass=AutoReprMeta):
    name = ""
    age = 0
    city = ""

p1 = Point()
p1.x = 3
p1.y = 4
print(p1)  # Point(x=3, y=4)

p2 = Point()
p2.x = 10
p2.y = 20
print(p2)  # Point(x=10, y=20)

person = Person()
person.name = "Alice"
person.age = 30
person.city = "北京"
print(person)  # Person(name='Alice', age=30, city='北京')


# ============================================================
# 6. ⚠️ 常见陷阱与避坑
# ============================================================

print("\n=== 6. 常见陷阱与避坑 ===")

# 陷阱 1：忘记 super().__new__
# class BadMeta(type):
#     def __new__(mcs, name, bases, attrs):
#         # 忘记调用 super().__new__，会导致问题
#         return type.__new__(mcs, name, bases, attrs)  # ❌ 不好
#         # 应该用: return super().__new__(mcs, name, bases, attrs)  ✅

# 陷阱 2：元类冲突
# 如果两个不同的元类都要作为基类的元类，会报错：
# class MetaA(type): pass
# class MetaB(type): pass
# class A(metaclass=MetaA): pass
# class B(metaclass=MetaB): pass
# class C(A, B): pass  # ❌ TypeError: metaclass conflict

# 陷阱 3：过度使用元类
# 能用装饰器解决的就不要用元类
# 能用 __init_subclass__ 解决的就不要用元类

# 陷阱 4：type() 创建类时的属性是类属性
# 动态创建的类属性是共享的，修改会影响所有实例
DynamicClass = type('DynamicClass', (), {'shared_list': []})
d1 = DynamicClass()
d2 = DynamicClass()
d1.shared_list.append(1)
print(f"  d1.shared_list: {d1.shared_list}")  # [1]
print(f"  d2.shared_list: {d2.shared_list}")  # [1] — 注意：共享了！
# 正确做法：在 __init__ 中初始化实例属性

print("\n✅ 所有测试通过！")
print("\n💡 关键要点：")
print("  1. __new__ 创建类，__init__ 初始化类，__call__ 创建实例")
print("  2. 元类适合框架设计，简单需求用装饰器或 __init_subclass__")
print("  3. 不要过度使用元类，保持代码简洁")
