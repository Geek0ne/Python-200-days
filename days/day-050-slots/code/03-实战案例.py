"""
Day 050 - 槽(__slots__) - 实战案例
构建一个高性能的事件系统 + 数据记录器
"""
import time
import weakref
from typing import Any, Callable, Dict, List, Optional


# ============================================
# Part 1: 高性能事件系统
# ============================================

class Event:
    """事件对象 — 使用 __slots__ 优化"""

    __slots__ = ('_name', '_data', '_timestamp', '_propagating')

    def __init__(self, name: str, data: Any = None):
        self._name = name
        self._data = data
        self._timestamp = time.time()
        self._propagating = True

    @property
    def name(self) -> str:
        return self._name

    @property
    def data(self) -> Any:
        return self._data

    @property
    def timestamp(self) -> float:
        return self._timestamp

    def stop_propagation(self):
        self._propagating = False

    @property
    def propagating(self) -> bool:
        return self._propagating

    def __repr__(self):
        return f"Event(name='{self._name}', data={self._data})"


class EventHandler:
    """事件处理器 — 使用 __slots__ 优化"""

    __slots__ = ('_callback', '_priority', '_once')

    def __init__(self, callback: Callable, priority: int = 0, once: bool = False):
        self._callback = callback
        self._priority = priority
        self._once = once

    def __call__(self, event: Event):
        return self._callback(event)

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def once(self) -> bool:
        return self._once


class EventEmitter:
    """事件发射器 — 管理事件监听和触发"""

    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}

    def on(self, event_name: str, callback: Callable, priority: int = 0) -> 'EventEmitter':
        """注册事件监听器"""
        if event_name not in self._handlers:
            self._handlers[event_name] = []

        handler = EventHandler(callback, priority)
        self._handlers[event_name].append(handler)
        self._handlers[event_name].sort(key=lambda h: h.priority, reverse=True)

        return self  # 支持链式调用

    def once(self, event_name: str, callback: Callable, priority: int = 0) -> 'EventEmitter':
        """注册一次性事件监听器"""
        if event_name not in self._handlers:
            self._handlers[event_name] = []

        handler = EventHandler(callback, priority, once=True)
        self._handlers[event_name].append(handler)
        self._handlers[event_name].sort(key=lambda h: h.priority, reverse=True)

        return self

    def off(self, event_name: str, callback: Optional[Callable] = None) -> 'EventEmitter':
        """移除事件监听器"""
        if event_name not in self._handlers:
            return self

        if callback is None:
            del self._handlers[event_name]
        else:
            self._handlers[event_name] = [
                h for h in self._handlers[event_name]
                if h._callback != callback
            ]

        return self

    def emit(self, event_name: str, data: Any = None) -> Event:
        """触发事件"""
        event = Event(event_name, data)

        if event_name not in self._handlers:
            return event

        # 收集需要移除的一次性处理器
        to_remove = []

        for handler in self._handlers[event_name]:
            if not event.propagating:
                break

            handler(event)

            if handler.once:
                to_remove.append(handler)

        # 移除一次性处理器
        for handler in to_remove:
            self._handlers[event_name].remove(handler)

        return event

    def listener_count(self, event_name: str) -> int:
        """获取事件监听器数量"""
        return len(self._handlers.get(event_name, []))


# ============================================
# Part 2: 高性能数据记录器
# ============================================

class DataRecord:
    """数据记录 — 使用 __slots__ 优化"""

    __slots__ = ('_id', '_timestamp', '_level', '_category', '_message', '_metadata')

    def __init__(self, record_id: int, level: str, category: str,
                 message: str, metadata: dict = None):
        self._id = record_id
        self._timestamp = time.time()
        self._level = level
        self._category = category
        self._message = message
        self._metadata = metadata or {}

    @property
    def id(self) -> int:
        return self._id

    @property
    def timestamp(self) -> float:
        return self._timestamp

    @property
    def level(self) -> str:
        return self._level

    @property
    def category(self) -> str:
        return self._category

    @property
    def message(self) -> str:
        return self._message

    @property
    def metadata(self) -> dict:
        return self._metadata

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "timestamp": self._timestamp,
            "level": self._level,
            "category": self._category,
            "message": self._message,
            "metadata": self._metadata,
        }

    def __repr__(self):
        return (f"DataRecord(id={self._id}, level='{self._level}', "
                f"category='{self._category}', message='{self._message[:30]}...')")


class DataLogger:
    """高性能数据记录器"""

    def __init__(self, max_records: int = 10000):
        self._records: List[DataRecord] = []
        self._max_records = max_records
        self._next_id = 0

    def log(self, level: str, category: str, message: str,
            metadata: dict = None) -> DataRecord:
        """记录一条数据"""
        record = DataRecord(self._next_id, level, category, message, metadata)
        self._records.append(record)
        self._next_id += 1

        # 如果超过最大记录数，移除最旧的
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        return record

    def query(self, level: str = None, category: str = None,
              limit: int = 100) -> List[DataRecord]:
        """查询记录"""
        results = []
        for record in reversed(self._records):
            if level and record.level != level:
                continue
            if category and record.category != category:
                continue
            results.append(record)
            if len(results) >= limit:
                break
        return results

    def stats(self) -> dict:
        """统计信息"""
        levels = {}
        categories = {}
        for record in self._records:
            levels[record.level] = levels.get(record.level, 0) + 1
            categories[record.category] = categories.get(record.category, 0) + 1
        return {
            "total": len(self._records),
            "levels": levels,
            "categories": categories,
        }


# ============================================
# Part 3: 使用演示
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 050 - __slots__ 实战：事件系统 + 数据记录器")
    print("=" * 60)

    # 事件系统
    print("\n--- 事件系统 ---")
    emitter = EventEmitter()

    # 注册监听器
    def on_user_login(event):
        print(f"  用户登录: {event.data}")

    def on_user_logout(event):
        print(f"  用户登出: {event.data}")

    def on_high_priority(event):
        print(f"  高优先级处理: {event.data}")

    emitter.on("user.login", on_user_login)
    emitter.on("user.logout", on_user_logout)
    emitter.on("user.login", on_high_priority, priority=10)

    # 触发事件
    emitter.emit("user.login", {"user": "张三"})
    emitter.emit("user.logout", {"user": "张三"})

    print(f"\nuser.login 监听器数量: {emitter.listener_count('user.login')}")

    # 一次性监听器
    print("\n--- 一次性监听器 ---")
    def on_first_connect(event):
        print(f"  首次连接: {event.data}")

    emitter.once("connection", on_first_connect)
    emitter.emit("connection", {"host": "localhost"})
    emitter.emit("connection", {"host": "localhost"})  # 不会触发
    print(f"connection 监听器数量: {emitter.listener_count('connection')}")

    # 数据记录器
    print("\n--- 数据记录器 ---")
    logger = DataLogger(max_records=1000)

    # 记录数据
    logger.log("INFO", "auth", "用户登录成功", {"user_id": 1})
    logger.log("ERROR", "db", "数据库连接失败", {"host": "localhost"})
    logger.log("WARN", "cache", "缓存命中率低", {"hit_rate": 0.3})
    logger.log("INFO", "auth", "用户登出", {"user_id": 1})
    logger.log("ERROR", "api", "API 请求超时", {"timeout": 30})

    # 查询
    print("\n查询 ERROR 级别:")
    errors = logger.query(level="ERROR")
    for record in errors:
        print(f"  {record}")

    print("\n查询 auth 分类:")
    auth_records = logger.query(category="auth")
    for record in auth_records:
        print(f"  {record}")

    # 统计
    print("\n统计信息:")
    import json
    print(json.dumps(logger.stats(), ensure_ascii=False, indent=2))

    # 内存分析
    print("\n--- 内存分析 ---")
    import sys
    print(f"Event 对象大小: {sys.getsizeof(Event('test', {}))} bytes")
    print(f"DataRecord 对象大小: {sys.getsizeof(DataRecord(0, 'INFO', 'test', 'msg'))} bytes")
    print(f"Event 有 __dict__: {hasattr(Event('test'), '__dict__')}")
    print(f"DataRecord 有 __dict__: {hasattr(DataRecord(0, 'INFO', 'test', 'msg'), '__dict__')}")
