"""
Day 051 - 实战：基于弱引用的 LRU 缓存与内存管理
主题：弱引用在实际项目中的应用
"""

import weakref
import time
from collections import OrderedDict
import gc


# ============================================================
# 1. 线程安全的弱引用缓存
# ============================================================
print("=" * 60)
print("1. 线程安全的弱引用缓存")
print("=" * 60)

import threading

class ThreadSafeWeakCache:
    """线程安全的弱引用缓存"""
    def __init__(self, maxsize=100):
        self._cache = weakref.WeakValueDictionary()
        self._lock = threading.Lock()
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0

    def get(self, key):
        with self._lock:
            result = self._cache.get(key)
            if result is not None:
                self._hits += 1
            else:
                self._misses += 1
            return result

    def put(self, key, value):
        with self._lock:
            if len(self._cache) >= self._maxsize:
                # WeakValueDictionary 会自动清理被回收的对象
                pass
            self._cache[key] = value

    def stats(self):
        return {
            'size': len(self._cache),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
        }


class DataObject:
    def __init__(self, data):
        self.data = data

# 测试
cache = ThreadSafeWeakCache(maxsize=10)

# 添加数据
for i in range(5):
    obj = DataObject(f"data_{i}")
    cache.put(f"key_{i}", obj)

# 获取数据
result = cache.get("key_0")
print(f"获取 key_0: {result.data if result else '未找到'}")

# 统计
print(f"缓存统计: {cache.stats()}")


# ============================================================
# 2. LRU 缓存与弱引用
# ============================================================
print("\n" + "=" * 60)
print("2. LRU 缓存与弱引用")
print("=" * 60)

class LRUCache:
    """基于弱引用的 LRU 缓存"""

    class Entry:
        __slots__ = ('key', 'value', 'expire_time', '__weakref__')

        def __init__(self, key, value, ttl):
            self.key = key
            self.value = value
            self.expire_time = time.time() + ttl

    def __init__(self, maxsize=128, ttl=300):
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache = weakref.WeakValueDictionary()
        self._order = OrderedDict()

    def get(self, key):
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry.expire_time:
                self._order.move_to_end(key)
                return entry.value
            else:
                del self._cache[key]
                del self._order[key]
        return None

    def put(self, key, value):
        if key in self._cache:
            self._order.move_to_end(key)
        self._order[key] = True
        entry = self.Entry(key, value, self._ttl)
        self._cache[key] = entry
        while len(self._order) > self._maxsize:
            oldest_key, _ = self._order.popitem(last=False)
            if oldest_key in self._cache:
                del self._cache[oldest_key]

    def __len__(self):
        return len(self._cache)

    def __repr__(self):
        return f"LRUCache(size={len(self)}, maxsize={self._maxsize})"


class UserProfile:
    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name
    def __repr__(self):
        return f"UserProfile({self.user_id}, {self.name!r})"

# 测试 LRU 缓存
cache = LRUCache(maxsize=3, ttl=60)

# 添加用户
for i, name in enumerate(["Alice", "Bob", "Charlie", "David"], 1):
    user = UserProfile(i, name)
    cache.put(f"user:{i}", user)
    print(f"  添加: {user}")

print(f"\n缓存: {cache}")

# 获取用户
print(f"\n获取 user:1: {cache.get('user:1')}")

# 添加第四个用户，触发 LRU 淘汰
cache.put("user:4", UserProfile(4, "Eve"))
print(f"添加 user:4 后:")
print(f"  user:2 是否还在: {cache.get('user:2') is not None}")
print(f"  缓存: {cache}")


# ============================================================
# 3. 事件监听器（自动清理）
# ============================================================
print("\n" + "=" * 60)
print("3. 事件监听器（自动清理）")
print("=" * 60)

class EventBus:
    """事件总线，使用弱引用管理监听器"""
    def __init__(self):
        self._listeners = weakref.WeakKeyDictionary()

    def subscribe(self, listener, event_name):
        if listener not in self._listeners:
            self._listeners[listener] = set()
        self._listeners[listener].add(event_name)

    def unsubscribe(self, listener, event_name):
        if listener in self._listeners:
            self._listeners[listener].discard(event_name)

    def publish(self, event_name, data):
        dead_listeners = []
        for listener, events in self._listeners.items():
            if event_name in events:
                try:
                    listener.on_event(event_name, data)
                except (ReferenceError, AttributeError):
                    dead_listeners.append(listener)
        for listener in dead_listeners:
            del self._listeners[listener]

    def listener_count(self):
        return len(self._listeners)


class EventHandler:
    """事件处理器"""
    def __init__(self, name):
        self.name = name

    def on_event(self, event_name, data):
        print(f"  [{self.name}] 收到事件 {event_name}: {data}")


# 测试事件总线
bus = EventBus()

handler1 = EventHandler("Handler1")
handler2 = EventHandler("Handler2")

bus.subscribe(handler1, "user_created")
bus.subscribe(handler2, "user_created")

print(f"监听器数量: {bus.listener_count()}")

print("\n发布事件:")
bus.publish("user_created", {"user_id": 1, "name": "Alice"})

# 删除一个处理器
del handler1
print(f"\n删除 Handler1 后，监听器数量: {bus.listener_count()}")

print("\n再次发布事件:")
bus.publish("user_created", {"user_id": 2, "name": "Bob"})


# ============================================================
# 4. 单例模式与弱引用
# ============================================================
print("\n" + "=" * 60)
print("4. 单例模式与弱引用")
print("=" * 60)

class Singleton:
    """基于弱引用的单例模式"""
    _instances = weakref.WeakValueDictionary()

    def __new__(cls, *args, **kwargs):
        key = cls.__name__
        instance = cls._instances.get(key)
        if instance is None:
            instance = super().__new__(cls)
            cls._instances[key] = instance
            print(f"  创建新实例: {cls.__name__}")
        else:
            print(f"  复用实例: {cls.__name__}")
        return instance

    def __init__(self, value=None):
        self.value = value


# 测试
s1 = Singleton(1)
print(f"s1.value = {s1.value}")

s2 = Singleton(2)
print(f"s2.value = {s2.value}")
print(f"s1 is s2: {s1 is s2}")

del s1  # 删除强引用
s3 = Singleton(3)
print(f"\n删除 s1 后创建 s3:")
print(f"s3.value = {s3.value}")
print(f"s2 is s3: {s2 is s3}")  # False，因为 s2 仍然持有旧实例
print(f"Singleton 实例数: {len(Singleton._instances)}")


# ============================================================
# 5. 内存分析辅助工具
# ============================================================
print("\n" + "=" * 60)
print("5. 内存分析辅助工具")
print("=" * 60)

class MemoryTracker:
    """使用弱引用追踪对象创建和销毁"""
    _instances = weakref.WeakSet()
    _created_count = 0

    def __init__(self, name):
        self.name = name
        MemoryTracker._created_count += 1
        MemoryTracker._instances.add(self)
        print(f"  创建: {name} (活跃对象: {len(MemoryTracker._instances)}, 总创建: {MemoryTracker._created_count})")

    @classmethod
    def active_count(cls):
        return len(cls._instances)

    @classmethod
    def total_created(cls):
        return cls._created_count

    @classmethod
    def active_objects(cls):
        return [obj.name for obj in cls._instances]


# 测试
print("创建对象:")
obj1 = MemoryTracker("A")
obj2 = MemoryTracker("B")
obj3 = MemoryTracker("C")

print(f"\n活跃对象: {MemoryTracker.active_objects()}")
print(f"活跃数量: {MemoryTracker.active_count()}")
print(f"总创建数: {MemoryTracker.total_created()}")

del obj1
del obj2

print(f"\n删除两个对象后:")
print(f"活跃对象: {MemoryTracker.active_objects()}")
print(f"活跃数量: {MemoryTracker.active_count()}")
print(f"总创建数: {MemoryTracker.total_created()}")
