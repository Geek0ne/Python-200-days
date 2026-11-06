"""
Day 034 — 多态与鸭子类型：进阶用法
====================================

涵盖：
1. ABC 抽象基类深入
2. 虚拟子类与注册机制
3. __subclasshook__ 魔法
4. 使用内置 ABC 创建自定义序列
5. 鸭子类型与协议（Protocol）
"""

# ====================================
# 1. ABC 抽象基类深入
# ====================================
print("=" * 60)
print("1️⃣ ABC 抽象基类深入")
print("=" * 60)

from abc import ABC, abstractmethod


class DataSource(ABC):
    """数据源抽象基类 —— 定义数据访问的接口契约"""

    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    def read(self) -> str:
        """读取数据"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        pass

    # 非抽象方法 —— 所有子类共享
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class DatabaseSource(DataSource):
    """数据库数据源"""

    def __init__(self, host: str, db: str):
        self.host = host
        self.db = db
        self.connected = False

    def connect(self) -> bool:
        print(f"  连接数据库 {self.host}/{self.db}")
        self.connected = True
        return True

    def read(self) -> str:
        if not self.connected:
            raise RuntimeError("未连接!")
        return f"从数据库 {self.db} 读取的数据"

    def close(self) -> None:
        print(f"  关闭数据库连接 {self.host}")
        self.connected = False


class FileSource(DataSource):
    """文件数据源"""

    def __init__(self, path: str):
        self.path = path
        self.file = None

    def connect(self) -> bool:
        print(f"  打开文件 {self.path}")
        self.file = open(self.path, 'r', encoding='utf-8')
        return True

    def read(self) -> str:
        if self.file is None:
            raise RuntimeError("文件未打开!")
        return self.file.read()

    def close(self) -> None:
        if self.file:
            print(f"  关闭文件 {self.path}")
            self.file.close()
            self.file = None


class APISource(DataSource):
    """API 数据源"""

    def __init__(self, url: str):
        self.url = url
        self.session = None

    def connect(self) -> bool:
        print(f"  创建 API 会话: {self.url}")
        # 模拟 session
        self.session = {"url": self.url, "token": "xxx"}
        return True

    def read(self) -> str:
        if not self.session:
            raise RuntimeError("未连接!")
        return f"从 API {self.url} 获取的数据"

    def close(self) -> None:
        print(f"  关闭 API 会话: {self.url}")
        self.session = None


def process_data(source: DataSource) -> None:
    """多态处理 —— 不关心具体数据源类型"""
    source.connect()
    try:
        data = source.read()
        print(f"  📄 处理数据: {data}")
    finally:
        source.close()


print("\n📊 多态数据源处理:")
process_data(DatabaseSource("localhost", "test_db"))
print()
process_data(APISource("https://api.example.com/data"))

# 使用上下文管理器
print("\n📊 使用 with 语句:")
with FileSource("/dev/null") as source:
    data = source.read()
    print(f"  📄 读取: {data}")


# ====================================
# 2. 虚拟子类与注册机制
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 虚拟子类与注册机制")
print("=" * 60)


class Drawable(ABC):
    """可绘制接口"""

    @abstractmethod
    def draw(self) -> str:
        pass

    def describe(self) -> str:
        return f"我是一个可绘制对象: {self.draw()}"


# 第三方类 —— 我们不能修改它
class Rectangle:
    """矩形类（来自第三方库）"""
    def __init__(self, w, h):
        self.w, self.h = w, h

    def draw(self) -> str:
        return f"□ {self.w}x{self.h} 矩形"
    
    def area(self) -> float:
        return self.w * self.h

# 通过注册，让 Rectangle 成为 Drawable 的虚拟子类
Drawable.register(Rectangle)

# 现在 Rectangle 被视为 Drawable
rect = Rectangle(10, 5)
print(f"  isinstance(rect, Drawable): {isinstance(rect, Drawable)}")
print(f"  issubclass(Rectangle, Drawable): {issubclass(Rectangle, Drawable)}")
print(f"  rect.draw(): {rect.draw()}")
print(f"  rect.describe(): {rect.describe()}")


# 装饰器方式注册
@Drawable.register
class Circle:
    """圆形"""
    def __init__(self, r):
        self.r = r

    def draw(self) -> str:
        return f"○ 半径 {self.r} 的圆"

    def area(self) -> float:
        return 3.14159 * self.r * self.r


circle = Circle(3)
print(f"\n  isinstance(circle, Drawable): {isinstance(circle, Drawable)}")
print(f"  circle.draw(): {circle.draw()}")


# ====================================
# 3. __subclasshook__ 魔法
# ====================================
print("\n" + "=" * 60)
print("3️⃣ __subclasshook__ 魔法方法")
print("=" * 60)


class Quackable(ABC):
    """会叫的接口 —— 使用 __subclasshook__ 实现自动识别"""

    @classmethod
    def __subclasshook__(cls, other):
        """检查一个类是否「看起来像」Quackable"""
        if cls is Quackable:
            # 检查是否有 quack 方法
            if any("quack" in B.__dict__ for B in other.__mro__):
                return True
        return NotImplemented

    @abstractmethod
    def quack(self) -> str:
        pass


# 这个类没有继承 Quackable，但实现了 quack 方法
class Goose:
    def quack(self) -> str:
        return "鹅鹅鹅! 🦆"

class Frog:
    def ribbit(self) -> str:
        return "呱呱呱! 🐸"

print(f"  issubclass(Goose, Quackable): {issubclass(Goose, Quackable)}")
print(f"  issubclass(Frog, Quackable): {issubclass(Frog, Quackable)}")
print(f"  isinstance(Goose(), Quackable): {isinstance(Goose(), Quackable)}")
print(f"  isinstance(Frog(), Quackable): {isinstance(Frog(), Quackable)}")


# ====================================
# 4. 使用 ABC 创建自定义序列
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 使用 ABC 创建自定义序列")
print("=" * 60)

from collections.abc import MutableSequence


class SimpleList(MutableSequence):
    """简化版的可变列表"""

    def __init__(self, initial=None):
        self._items = list(initial) if initial else []

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, value):
        self._items[index] = value

    def __delitem__(self, index):
        del self._items[index]

    def __len__(self):
        return len(self._items)

    def insert(self, index, value):
        self._items.insert(index, value)

    def __repr__(self):
        return f"SimpleList({self._items})"


sl = SimpleList([3, 1, 4, 1, 5, 9])
print(f"  创建: {sl}")
print(f"  长度: {len(sl)}")
print(f"  索引[0]: {sl[0]}")
print(f"  isinstance(sl, MutableSequence): {isinstance(sl, MutableSequence)}")

sl.append(2)      # 继承自 MutableSequence
print(f"  append(2): {sl}")
sl.reverse()      # 继承自 MutableSequence
print(f"  reverse(): {sl}")
sl.sort()          # 继承自 MutableSequence (Python 3.11+)
print(f"  sort(): {sl}")

# 自动获得 count, index, pop, remove, clear, extend 等方法


# ====================================
# 5. 鸭子类型与 Protocol
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 鸭子类型与 Protocol (Python 3.8+)")
print("=" * 60)

from typing import Protocol, runtime_checkable


@runtime_checkable
class Logger(Protocol):
    """日志协议 —— 定义结构化接口"""
    def log(self, message: str, level: str = "INFO") -> None:
        ...


class ConsoleLogger:
    """控制台日志器 —— 实现了 Logger 协议但没有显式继承"""
    def log(self, message: str, level: str = "INFO") -> None:
        print(f"[{level}] {message}")


class FileLogger:
    """文件日志器 —— 实现了 Logger 协议"""
    def __init__(self, filename: str):
        self.filename = filename

    def log(self, message: str, level: str = "INFO") -> None:
        with open(self.filename, 'a') as f:
            f.write(f"[{level}] {message}\n")


class NetworkLogger:
    """网络日志器"""
    def log(self, message: str, level: str = "INFO") -> None:
        # 模拟网络发送
        print(f"  🌐 发送日志 [{level}] {message}")

    def flush(self) -> None:
        print("  🌐 刷新缓冲区")


def process_with_logging(logger: Logger) -> None:
    """使用 Logger 协议 —— 接受任何实现了 Logger 协议的对象"""
    logger.log("开始处理")
    logger.log("处理中...", "DEBUG")
    logger.log("处理完成", "INFO")


print("\n📊 Protocol 多态:")
process_with_logging(ConsoleLogger())

# 运行时类型检查（需要 @runtime_checkable）
print(f"\n  isinstance(ConsoleLogger(), Logger): {isinstance(ConsoleLogger(), Logger)}")
print(f"  isinstance(42, Logger): {isinstance(42, Logger)}")
