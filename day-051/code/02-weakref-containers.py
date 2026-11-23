"""
Day 051 - 弱引用容器：WeakValueDictionary / WeakKeyDictionary / WeakSet
主题：弱引用容器的使用与实战
"""

import weakref
import gc


# ============================================================
# 1. WeakValueDictionary 基础用法
# ============================================================
print("=" * 60)
print("1. WeakValueDictionary 基础用法")
print("=" * 60)

class ExpensiveObject:
    """模拟一个占用大量内存的对象"""
    def __init__(self, name, data=None):
        self.name = name
        self.data = data or []
    def __repr__(self):
        return f"ExpensiveObject({self.name!r})"
    def __del__(self):
        print(f"  💀 {self.name} 被回收")

# 创建 WeakValueDictionary
cache = weakref.WeakValueDictionary()

# 存储对象
obj1 = ExpensiveObject("data1", [1, 2, 3])
obj2 = ExpensiveObject("data2", [4, 5, 6])
cache["key1"] = obj1
cache["key2"] = obj2

print(f"缓存中有: {list(cache.keys())}")
print(f"key1 的值: {cache['key1']}")

# 删除对象后，缓存条目自动消失
del obj1
print(f"\n删除 obj1 后，缓存中有: {list(cache.keys())}")
print("→ 对象被回收后，WeakValueDictionary 自动清理条目")


# ============================================================
# 2. WeakValueDictionary 与循环引用
# ============================================================
print("\n" + "=" * 60)
print("2. WeakValueDictionary 打破循环引用")
print("=" * 60)

class Node:
    def __init__(self, name):
        self.name = name
        self.children = []  # 强引用子节点
    def __repr__(self):
        return f"Node({self.name!r})"
    def __del__(self):
        print(f"  💀 Node({self.name}) 被回收")

class Tree:
    def __init__(self):
        self._nodes = weakref.WeakValueDictionary()  # 弱引用存储节点

    def add_node(self, node):
        self._nodes[node.name] = node

    def get_node(self, name):
        return self._nodes.get(name)

    def create_child(self, parent_name, child_name):
        parent = self.get_node(parent_name)
        if parent:
            child = Node(child_name)
            parent.children.append(child)
            self.add_node(child)
            return child
        return None

# 创建树
tree = Tree()
root = Node("root")
tree.add_node(root)

child1 = tree.create_child("root", "child1")
child2 = tree.create_child("root", "child2")

print(f"树的节点: {list(tree._nodes.keys())}")

# 删除根节点
del root
print(f"\n删除 root 后，缓存中有: {list(tree._nodes.keys())}")
print("→ WeakValueDictionary 自动清理，避免循环引用问题")


# ============================================================
# 3. WeakKeyDictionary
# ============================================================
print("\n" + "=" * 60)
print("3. WeakKeyDictionary —— 键为弱引用")
print("=" * 60)

class Config:
    def __init__(self, env):
        self.env = env
    def __repr__(self):
        return f"Config({self.env!r})"
    def __del__(self):
        print(f"  💀 Config({self.env}) 被回收")

# 创建 WeakKeyDictionary
config_data = weakref.WeakKeyDictionary()

config = Config("production")
config_data[config] = {"db_host": "localhost", "db_port": 5432}

print(f"配置数据: {config_data[config]}")
print(f"字典长度: {len(config_data)}")

# 删除键后，条目自动消失
del config
print(f"\n删除 Config 对象后，字典长度: {len(config_data)}")
print("→ WeakKeyDictionary 自动清理条目")


# ============================================================
# 4. WeakSet
# ============================================================
print("\n" + "=" * 60)
print("4. WeakSet —— 元素为弱引用")
print("=" * 60)

class Observer:
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return f"Observer({self.name!r})"
    def __del__(self):
        print(f"  💀 Observer({self.name}) 被回收")

# 创建 WeakSet
observers = weakref.WeakSet()

obs1 = Observer("observer1")
obs2 = Observer("observer2")
obs3 = Observer("observer3")

observers.add(obs1)
observers.add(obs2)
observers.add(obs3)

print(f"观察者数量: {len(observers)}")
print(f"观察者列表: {list(observers)}")

# 删除观察者
del obs1
del obs2
print(f"\n删除两个观察者后，数量: {len(observers)}")
print(f"剩余: {list(observers)}")


# ============================================================
# 5. 观察者模式实战
# ============================================================
print("\n" + "=" * 60)
print("5. 观察者模式实战")
print("=" * 60)

class EventEmitter:
    """事件发射器，使用 WeakSet 管理观察者"""
    def __init__(self):
        self._listeners = {}  # event -> WeakSet of callbacks

    def on(self, event, callback):
        """注册事件监听"""
        if event not in self._listeners:
            self._listeners[event] = weakref.WeakSet()
        self._listeners[event].add(callback)

    def emit(self, event, *args, **kwargs):
        """触发事件"""
        if event in self._listeners:
            dead_refs = []
            for callback in self._listeners[event]:
                try:
                    callback(*args, **kwargs)
                except ReferenceError:
                    dead_refs.append(callback)
            # 清理无效引用
            for ref in dead_refs:
                self._listeners[event].discard(ref)

    def listener_count(self, event):
        return len(self._listeners.get(event, weakref.WeakSet()))


class Button:
    """按钮类，作为事件源"""
    def __init__(self, name):
        self.name = name
        self.events = EventEmitter()

    def click(self):
        print(f"  按钮 [{self.name}] 被点击")
        self.events.emit("click", self.name)


class Logger:
    """日志记录器，作为观察者"""
    def __init__(self, name):
        self.name = name
    def log(self, message):
        print(f"  [{self.name}] 记录: {message}")


# 使用
button = Button("submit")
logger1 = Logger("console")
logger2 = Logger("file")

button.events.on("click", logger1.log)
button.events.on("click", logger2.log)

print("点击按钮 (两个观察者都活跃):")
button.click()

print(f"\n日志观察者数量: {button.events.listener_count('click')}")

# 删除一个观察者
del logger1
print(f"\n删除 console logger 后:")
print(f"日志观察者数量: {button.events.listener_count('click')}")
button.click()


# ============================================================
# 6. 自动清理缓存
# ============================================================
print("\n" + "=" * 60)
print("6. 自动清理缓存实战")
print("=" * 60)

class ConnectionPool:
    """连接池，使用 WeakValueDictionary 自动管理连接"""
    _pool = weakref.WeakValueDictionary()

    @classmethod
    def get_connection(cls, host, port):
        key = f"{host}:{port}"
        conn = cls._pool.get(key)
        if conn is None:
            conn = Connection(host, port)
            cls._pool[key] = conn
            print(f"  创建新连接: {key}")
        else:
            print(f"  复用连接: {key}")
        return conn

    @classmethod
    def pool_size(cls):
        return len(cls._pool)


class Connection:
    def __init__(self, host, port):
        self.host = host
        self.port = port
    def __repr__(self):
        return f"Connection({self.host}:{self.port})"
    def __del__(self):
        print(f"  💀 连接 {self.host}:{self.port} 被回收")


# 测试
conn1 = ConnectionPool.get_connection("localhost", 5432)
conn2 = ConnectionPool.get_connection("localhost", 5432)
print(f"池大小: {ConnectionPool.pool_size()}")

del conn1
print(f"\n释放一个连接后，池大小: {ConnectionPool.pool_size()}")

conn3 = ConnectionPool.get_connection("localhost", 5432)
print(f"获取新连接后，池大小: {ConnectionPool.pool_size()}")
print(f"是否是同一个连接: {conn2 is conn3}")
