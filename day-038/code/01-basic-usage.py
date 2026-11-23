"""
Day 038 — 创建型设计模式：基础用法
====================================

涵盖：
1. 单例模式（__new__ 方式）
2. 单例模式（装饰器方式）
3. 单例模式（元类方式）
4. 简单工厂模式
5. 工厂方法模式
"""


# ====================================
# 1. 单例模式（__new__ 方式）
# ====================================
print("=" * 60)
print("1️⃣ 单例模式（__new__ 方式）")
print("=" * 60)


class DatabaseConnection:
    """数据库连接池 —— 经典单例实现"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            print("  🆕 创建新的数据库连接实例")
            cls._instance = super().__new__(cls)
            # 在这里进行一次性初始化
            cls._instance._initialized = False
        else:
            print("  🔄 复用已有的数据库连接实例")
        return cls._instance

    def __init__(self, host: str = "localhost", port: int = 5432):
        # __init__ 每次都会调用，所以需要检查是否已初始化
        if not self._initialized:
            print(f"  📦 初始化数据库连接: {host}:{port}")
            self.host = host
            self.port = port
            self._connected = False
            self._initialized = True

    def connect(self):
        self._connected = True
        return f"  ✅ 已连接到 {self.host}:{self.port}"

    def disconnect(self):
        self._connected = False
        return "  ❌ 已断开连接"


db1 = DatabaseConnection("prod-server", 5432)
db2 = DatabaseConnection("dev-server", 3306)  # 参数被忽略！

print(f"  db1 is db2: {db1 is db2}")        # True
print(f"  db1.host: {db1.host}")             # prod-server
print(f"  db2.host: {db2.host}")             # prod-server (不是 dev-server!)
print(db1.connect())
print(db2.connect())  # 同一个连接


# ====================================
# 2. 单例模式（装饰器方式）
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 单例模式（装饰器方式）")
print("=" * 60)


def singleton(cls):
    """单例装饰器"""
    _instances = {}

    def get_instance(*args, **kwargs):
        if cls not in _instances:
            print(f"  🆕 创建 {cls.__name__} 实例")
            _instances[cls] = cls(*args, **kwargs)
        else:
            print(f"  🔄 复用 {cls.__name__} 实例")
        return _instances[cls]
    return get_instance


@singleton
class Logger:
    """日志器（装饰器单例）"""

    def __init__(self):
        self.logs = []
        print("  📝 Logger 初始化（只执行一次）")

    def info(self, msg):
        self.logs.append(f"[INFO] {msg}")
        print(f"  📝 {msg}")


logger1 = Logger()
logger2 = Logger()

print(f"  logger1 is logger2: {logger1 is logger2}")
logger1.info("系统启动")
logger2.info("用户登录")
print(f"  日志条数: {len(logger1.logs)}")


# ====================================
# 3. 单例模式（元类方式）
# ====================================
print("\n" + "=" * 60)
print("3️⃣ 单例模式（元类方式）")
print("=" * 60)


class SingletonMeta(type):
    """单例元类"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            print(f"  🆕 元类创建 {cls.__name__} 实例")
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class AppConfig(metaclass=SingletonMeta):
    """应用配置（元类单例）"""

    def __init__(self):
        self.debug = False
        self.secret_key = "default-secret"
        print("  ⚙️  AppConfig 初始化（只执行一次）")


config1 = AppConfig()
config2 = AppConfig()

print(f"  config1 is config2: {config1 is config2}")
config1.debug = True
print(f"  config2.debug: {config2.debug}")  # True


# ====================================
# 4. 简单工厂模式
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 简单工厂模式")
print("=" * 60)


class Notification:
    """通知基类"""

    def send(self, message: str, recipient: str) -> str:
        raise NotImplementedError


class EmailNotification(Notification):
    def send(self, message: str, recipient: str) -> str:
        return f"📧 发送邮件到 {recipient}: {message}"


class SMSNotification(Notification):
    def send(self, message: str, recipient: str) -> str:
        return f"📱 发送短信到 {recipient}: {message}"


class PushNotification(Notification):
    def send(self, message: str, recipient: str) -> str:
        return f"🔔 发送推送到 {recipient}: {message}"


class WeChatNotification(Notification):
    def send(self, message: str, recipient: str) -> str:
        return f"💬 发送微信消息到 {recipient}: {message}"


class NotificationFactory:
    """通知工厂 —— 封装对象创建逻辑"""

    _channels = {
        "email": EmailNotification,
        "sms": SMSNotification,
        "push": PushNotification,
        "wechat": WeChatNotification,
    }

    @classmethod
    def create(cls, channel: str) -> Notification:
        """创建通知实例"""
        notification_class = cls._channels.get(channel.lower())
        if not notification_class:
            available = ', '.join(cls._channels.keys())
            raise ValueError(
                f"不支持的通知渠道: {channel}. "
                f"可用渠道: {available}"
            )
        return notification_class()

    @classmethod
    def register(cls, name: str, notification_class: type):
        """注册新的通知渠道（扩展性）"""
        cls._channels[name] = notification_class


print("  通知工厂演示:")
for channel in ["email", "sms", "push"]:
    notification = NotificationFactory.create(channel)
    result = notification.send("您好！", "user@example.com")
    print(f"  {result}")

# 注册新渠道
NotificationFactory.register("dingtalk", WeChatNotification)

# 使用 __init_subclass__ 方式的自动注册
class AutoRegisteredNotification(Notification):
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        name = getattr(cls, 'channel_name', cls.__name__.lower())
        AutoRegisteredNotification._registry[name] = cls

    @classmethod
    def create(cls, channel: str) -> 'Notification':
        notif_class = cls._registry.get(channel.lower())
        if not notif_class:
            raise ValueError(f"未知渠道: {channel}")
        return notif_class()


class DingTalkNotification(AutoRegisteredNotification):
    channel_name = "dingtalk"

    def send(self, message: str, recipient: str) -> str:
        return f"🔔 钉钉通知 {recipient}: {message}"


dingtalk = AutoRegisteredNotification.create("dingtalk")
print(f"  自动注册: {dingtalk.send('会议提醒', '全员')}")


# ====================================
# 5. 工厂方法模式
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 工厂方法模式")
print("=" * 60)

from abc import ABC, abstractmethod


class Document(ABC):
    """文档抽象类"""

    @abstractmethod
    def open(self) -> str: pass

    @abstractmethod
    def save(self) -> str: pass

    @abstractmethod
    def close(self) -> str: pass


class PDFDocument(Document):
    def open(self) -> str:
        return "📄 打开 PDF 文档"

    def save(self) -> str:
        return "📄 保存 PDF 文档"

    def close(self) -> str:
        return "📄 关闭 PDF 文档"


class WordDocument(Document):
    def open(self) -> str:
        return "📝 打开 Word 文档"

    def save(self) -> str:
        return "📝 保存 Word 文档"

    def close(self) -> str:
        return "📝 关闭 Word 文档"


class SpreadsheetDocument(Document):
    def open(self) -> str:
        return "📊 打开电子表格"

    def save(self) -> str:
        return "📊 保存电子表格"

    def close(self) -> str:
        return "📊 关闭电子表格"


class Application(ABC):
    """应用基类 —— 使用工厂方法"""

    def __init__(self, name: str):
        self.name = name
        self.documents = []

    @abstractmethod
    def create_document(self) -> Document:
        """工厂方法 —— 子类实现"""
        pass

    def new_document(self) -> str:
        """使用工厂方法创建文档"""
        doc = self.create_document()
        self.documents.append(doc)
        result = doc.open()
        return f"{self.name}: {result}"

    def save_all(self) -> list:
        return [doc.save() for doc in self.documents]


class PDFApplication(Application):
    def __init__(self):
        super().__init__("PDF 编辑器")

    def create_document(self) -> Document:
        return PDFDocument()


class WordApplication(Application):
    def __init__(self):
        super().__init__("Word 处理器")

    def create_document(self) -> Document:
        return WordDocument()


class SpreadsheetApplication(Application):
    def __init__(self):
        super().__init__("表格编辑器")

    def create_document(self) -> Document:
        return SpreadsheetDocument()


print("  工厂方法模式:")
apps = [PDFApplication(), WordApplication(), SpreadsheetApplication()]

for app in apps:
    print(f"  {app.new_document()}")

print("\n  批量保存:")
for app in apps:
    results = app.save_all()
    for r in results:
        print(f"  {app.name}: {r}")
