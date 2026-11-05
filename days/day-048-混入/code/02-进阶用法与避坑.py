"""
Day 048 - 混入(Mixin) - 进阶用法与避坑
演示：Mixin 的命名冲突、协作式继承、常见陷阱
"""


# ============================================
# 1. 命名冲突问题
# ============================================

class LoggerMixin:
    """日志 Mixin — 提供 log() 方法"""

    def log(self, message):
        print(f"[LoggerMixin] {message}")

    def get_config(self):
        return {"log_level": "INFO"}


class CacheMixin:
    """缓存 Mixin — 也定义了 log() 方法！"""

    def log(self, message):
        print(f"[CacheMixin] {message}")

    def get_config(self):
        return {"cache_size": 1000}


class Service(LoggerMixin, CacheMixin):
    """服务类 — 同时继承两个有冲突的 Mixin"""
    pass


# ⚠️ 命名冲突：MRO 决定调用哪个
print("=== 命名冲突演示 ===")
svc = Service()
svc.log("测试消息")  # 输出: [LoggerMixin] 测试消息 （MRO 中 LoggerMixin 在前）
print(f"get_config 结果: {svc.get_config()}")  # 同理

# MRO 验证
print(f"\nMRO 顺序: {[c.__name__ for c in Service.__mro__]}")


# ============================================
# 2. 正确处理命名冲突：super() 协作
# ============================================

class LoggerMixinV2:
    """改进版日志 Mixin — 使用 super() 协作"""

    def log(self, message):
        print(f"[LoggerMixinV2] {message}")
        # 调用下一个 MRO 中的 log()
        super().log(message) if hasattr(super(), 'log') else None

    def get_config(self):
        base = {}
        if hasattr(super(), 'get_config'):
            base.update(super().get_config())
        base['log_level'] = "INFO"
        return base


class CacheMixinV2:
    """改进版缓存 Mixin — 使用 super() 协作"""

    def log(self, message):
        print(f"[CacheMixinV2] {message}")
        super().log(message) if hasattr(super(), 'log') else None

    def get_config(self):
        base = {}
        if hasattr(super(), 'get_config'):
            base.update(super().get_config())
        base['cache_size'] = 1000
        return base


class ServiceV2(LoggerMixinV2, CacheMixinV2):
    def log(self, message):
        print(f"[ServiceV2] {message}")
        super().log(message)

    def get_config(self):
        base = {}
        if hasattr(super(), 'get_config'):
            base.update(super().get_config())
        base['service'] = "v2"
        return base


print("\n=== super() 协作演示 ===")
svc2 = ServiceV2()
svc2.log("测试消息")  # 调用链: ServiceV2 → LoggerMixinV2 → CacheMixinV2
print(f"get_config 结果: {svc2.get_config()}")


# ============================================
# 3. Mixin 中的 __init__ 陷阱
# ============================================

class BadInitMixin:
    """
    ❌ 错误的 Mixin：定义了 __init__ 但不调用 super().__init__()

    这会导致 MRO 链断裂，后续类的 __init__ 不会被调用！
    """

    def __init__(self):
        print("BadInitMixin.__init__ called")
        # 忘记调用 super().__init__()


class GoodInitMixin:
    """
    ✅ 正确的 Mixin：定义了 __init__ 但正确传递 **kwargs
    """

    def __init__(self, **kwargs):
        print("GoodInitMixin.__init__ called")
        super().__init__(**kwargs)  # 关键：传递给下一个类


class BaseClass:
    def __init__(self, name="default"):
        print(f"BaseClass.__init__ called: name={name}")
        self.name = name


# ❌ 错误示例
print("\n=== Mixin __init__ 陷阱 ===")

try:
    class BadService(BadInitMixin, BaseClass):
        def __init__(self, name="test"):
            super().__init__()
            print(f"BadService.__init__ called")

    # 只会打印 BadInitMixin，BaseClass 的 __init__ 不会被调用
    obj = BadService()
    print(f"obj.name: {getattr(obj, 'name', '❌ 不存在！')}")
except Exception as e:
    print(f"错误: {e}")


# ✅ 正确示例
print("\n--- 正确的 Mixin __init__ ---")

class GoodService(GoodInitMixin, BaseClass):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print(f"GoodService.__init__ called")

obj2 = GoodService(name="正确的服务")
print(f"obj2.name: {obj2.name}")


# ============================================
# 4. Mixin 不应该存储实例状态
# ============================================

class BadStateMixin:
    """
    ❌ 错误：Mixin 存储了自己的状态

    如果多个类使用同一个 Mixin，它们会共享 _counter
    """

    _counter = 0  # 类变量 — 所有实例共享

    def increment(self):
        BadStateMixin._counter += 1
        return BadStateMixin._counter


class GoodStateMixin:
    """
    ✅ 正确：Mixin 的状态应该在实例级别管理

    使用 __init__ 中初始化实例变量
    """

    def __init__(self, **kwargs):
        self._my_state = {}  # 实例变量，每个实例独立
        super().__init__(**kwargs)

    def store(self, key, value):
        self._my_state[key] = value

    def retrieve(self, key):
        return self._my_state.get(key)


class ServiceA(GoodStateMixin, BaseClass):
    pass

class ServiceB(GoodStateMixin, BaseClass):
    pass


print("\n=== 状态隔离演示 ===")
a = ServiceA(name="ServiceA")
b = ServiceB(name="ServiceB")

a.store("config", {"debug": True})
b.store("config", {"debug": False})

print(f"A 的配置: {a.retrieve('config')}")
print(f"B 的配置: {b.retrieve('config')}")
print(f"A 和 B 的状态隔离: {a.retrieve('config') != b.retrieve('config')}")


# ============================================
# 5. 最佳实践总结
# ============================================

print("\n" + "=" * 50)
print("Mixin 最佳实践总结：")
print("=" * 50)
print("""
✅ DO:
  - Mixin 以 Mixin 结尾命名（如 LoggerMixin）
  - Mixin 不定义 __init__，或用 **kwargs 传递
  - Mixin 调用 super().__init__(**kwargs) 协作
  - Mixin 只提供方法，不存储关键状态
  - 用 isinstance() 检查 Mixin 能力

❌ DON'T:
  - Mixin 不要定义 __init__ 但不调用 super()
  - Mixin 不要用类变量存储状态
  - Mixin 不要依赖特定类的属性
  - Mixin 不要过度使用（2-3个最佳）
  - 不要在 Mixin 中引入新的依赖
""")
