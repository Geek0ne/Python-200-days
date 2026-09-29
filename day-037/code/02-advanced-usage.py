"""
Day 037 — 组合与聚合：进阶用法
===============================

涵盖：
1. 装饰器模式（组合的经典用法）
2. 策略模式（通过组合替换算法）
3. 桥接模式（通过组合分离抽象和实现）
4. 工厂模式中的组合
5. Mixin 与组合
"""


# ====================================
# 1. 装饰器模式（组合的经典用法）
# ====================================
print("=" * 60)
print("1️⃣ 装饰器模式 — 组合的经典用法")
print("=" * 60)


class Coffee:
    """基础咖啡"""

    def cost(self) -> float:
        return 10.0

    def description(self) -> str:
        return "美式咖啡"


class CoffeeDecorator:
    """咖啡装饰器基类 —— 通过组合包装 Coffee"""

    def __init__(self, coffee: Coffee):
        self._coffee = coffee  # 组合：包装另一个 Coffee 对象

    def cost(self) -> float:
        return self._coffee.cost()

    def description(self) -> str:
        return self._coffee.description()


class MilkDecorator(CoffeeDecorator):
    """加牛奶"""

    def cost(self) -> float:
        return super().cost() + 3.0

    def description(self) -> str:
        return super().description() + " + 牛奶"


class SugarDecorator(CoffeeDecorator):
    """加糖"""

    def cost(self) -> float:
        return super().cost() + 1.5

    def description(self) -> str:
        return super().description() + " + 糖"


class WhipDecorator(CoffeeDecorator):
    """加奶油"""

    def cost(self) -> float:
        return super().cost() + 4.0

    def description(self) -> str:
        return super().description() + " + 奶油"


# 组合装饰
basic = Coffee()
print(f"  基础: {basic.description()} = ¥{basic.cost():.1f}")

milk = MilkDecorator(basic)
print(f"  加奶: {milk.description()} = ¥{milk.cost():.1f}")

milk_sugar = SugarDecorator(MilkDecorator(Coffee()))
print(f"  全加: {milk_sugar.description()} = ¥{milk_sugar.cost():.1f}")

full = WhipDecorator(SugarDecorator(MilkDecorator(Coffee())))
print(f"  豪华: {full.description()} = ¥{full.cost():.1f}")


# ====================================
# 2. 策略模式（通过组合替换算法）
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 策略模式 — 通过组合替换算法")
print("=" * 60)


class SortingStrategy:
    """排序策略接口"""

    def sort(self, data: list) -> list:
        raise NotImplementedError


class BubbleSort(SortingStrategy):
    """冒泡排序"""

    def sort(self, data: list) -> list:
        arr = data[:]
        n = len(arr)
        for i in range(n):
            for j in range(0, n - i - 1):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
        return arr


class QuickSort(SortingStrategy):
    """快速排序"""

    def sort(self, data: list) -> list:
        if len(data) <= 1:
            return data[:]
        pivot = data[0]
        less = [x for x in data[1:] if x <= pivot]
        greater = [x for x in data[1:] if x > pivot]
        return self.sort(less) + [pivot] + self.sort(greater)


class Sorter:
    """排序器 —— 通过组合使用不同的排序策略"""

    def __init__(self, strategy: SortingStrategy):
        self._strategy = strategy  # 组合：策略对象

    def set_strategy(self, strategy: SortingStrategy):
        """运行时切换策略"""
        self._strategy = strategy

    def sort(self, data: list) -> list:
        return self._strategy.sort(data)


data = [64, 34, 25, 12, 22, 11, 90]

sorter = Sorter(BubbleSort())
print(f"  冒泡排序: {sorter.sort(data)}")

sorter.set_strategy(QuickSort())
print(f"  快速排序: {sorter.sort(data)}")


# ====================================
# 3. 桥接模式
# ====================================
print("\n" + "=" * 60)
print("3️⃣ 桥接模式 — 分离抽象和实现")
print("=" * 60)


class Device:
    """设备接口"""

    def is_enabled(self): pass
    def enable(self): pass
    def disable(self): pass
    def get_volume(self): pass
    def set_volume(self, pct): pass


class TV(Device):
    """电视机"""

    def __init__(self):
        self._on = False
        self._volume = 50

    def is_enabled(self): return self._on
    def enable(self):
        self._on = True
        print("    电视已开启")
    def disable(self):
        self._on = False
        print("    电视已关闭")
    def get_volume(self): return self._volume
    def set_volume(self, pct):
        self._volume = max(0, min(100, pct))
        print(f"    电视音量: {self._volume}")


class Radio(Device):
    """收音机"""

    def __init__(self):
        self._on = False
        self._volume = 30

    def is_enabled(self): return self._on
    def enable(self):
        self._on = True
        print("    收音机已开启")
    def disable(self):
        self._on = False
        print("    收音机已关闭")
    def get_volume(self): return self._volume
    def set_volume(self, pct):
        self._volume = max(0, min(100, pct))
        print(f"    收音机音量: {self._volume}")


class RemoteControl:
    """遥控器 —— 通过组合控制任意 Device"""

    def __init__(self, device: Device):
        self._device = device  # 组合：任意设备

    def toggle_power(self):
        if self._device.is_enabled():
            self._device.disable()
        else:
            self._device.enable()

    def volume_up(self):
        v = self._device.get_volume()
        self._device.set_volume(v + 10)

    def volume_down(self):
        v = self._device.get_volume()
        self._device.set_volume(v - 10)


# 同一个遥控器控制不同设备
tv = TV()
radio = Radio()

print("  遥控器控制电视:")
remote = RemoteControl(tv)
remote.toggle_power()
remote.volume_up()

print("\n  遥控器控制收音机:")
remote2 = RemoteControl(radio)
remote2.toggle_power()
remote2.volume_up()


# ====================================
# 4. 工厂模式中的组合
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 工厂模式 — 组合对象创建逻辑")
    print("=" * 60)


class NotificationSender:
    """通知发送器基类"""

    def send(self, message: str, recipient: str):
        pass


class EmailSender(NotificationSender):
    def send(self, message: str, recipient: str):
        print(f"  📧 发送邮件到 {recipient}: {message}")


class SMSSender(NotificationSender):
    def send(self, message: str, recipient: str):
        print(f"  📱 发送短信到 {recipient}: {message}")


class PushSender(NotificationSender):
    def send(self, message: str, recipient: str):
        print(f"  🔔 发送推送到 {recipient}: {message}")


class NotificationFactory:
    """通知工厂 —— 组合了创建逻辑和发送逻辑"""

    def __init__(self):
        self._senders = {
            "email": EmailSender(),
            "sms": SMSSender(),
            "push": PushSender(),
        }

    def send_notification(self, channel: str, message: str, recipient: str):
        sender = self._senders.get(channel)
        if not sender:
            raise ValueError(f"不支持的通知渠道: {channel}")
        sender.send(message, recipient)


factory = NotificationFactory()
factory.send_notification("email", "欢迎注册!", "user@example.com")
factory.send_notification("sms", "验证码: 123456", "13800138000")
factory.send_notification("push", "你有新消息", "device-token-xxx")


# ====================================
# 5. Mixin 与组合
# ====================================
print("\n" + "=" * 60)
print("5️⃣ Mixin — 通过多重继承实现组合式复用")
print("=" * 60)


class JSONMixin:
    """JSON 序列化 Mixin"""

    def to_json(self) -> str:
        import json
        return json.dumps(self.__dict__, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str):
        import json
        data = json.loads(json_str)
        return cls(**data)


class LoggableMixin:
    """日志记录 Mixin"""

    def log(self, message: str):
        print(f"  📝 [{self.__class__.__name__}] {message}")


class SerializableMixin:
    """序列化 Mixin"""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()
                if not k.startswith('_')}


class User(JSONMixin, LoggableMixin, SerializableMixin):
    """用户类 —— 通过 Mixin 组合不同能力"""

    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age


class Product(JSONMixin, LoggableMixin):
    """商品类 —— 组合不同的 Mixin 集合"""

    def __init__(self, name: str, price: float):
        self.name = name
        self.price = price


user = User("Alice", 30)
print(f"  用户 JSON: {user.to_json()}")
user.log("用户已创建")
print(f"  用户 dict: {user.to_dict()}")

product = Product("iPhone", 6999)
print(f"\n  商品 JSON: {product.to_json()}")
product.log("商品已上架")

# 从 JSON 恢复
restored = User.from_json('{"name": "Bob", "age": 25}')
print(f"  恢复的用户: {restored.name}, {restored.age}")
