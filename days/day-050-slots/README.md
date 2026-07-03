# Day 050 — 槽（__slots__）

## 📚 概念解释

### 什么是 `__slots__`？

**`__slots__`** 是 Python 中一种内存优化机制。当一个类定义了 `__slots__`，Python 会为该类的每个实例使用**固定大小的存储空间**，而不是动态的 `__dict__` 字典。

```
┌──────────────────────────────────────────────────────┐
│              普通类 vs __slots__ 类                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  普通类（使用 __dict__）：                              │
│  ┌──────────────────────────────────────┐            │
│  │ instance.__dict__                     │            │
│  │ {                                      │            │
│  │   'name': '张三',                     │            │
│  │   'age': 28,                          │            │
│  │   'email': 'zhangsan@example.com'     │            │
│  │ }  ← 每个属性都是字典的一个键值对       │            │
│  └──────────────────────────────────────┘            │
│                                                      │
│  __slots__ 类（使用固定槽位）：                         │
│  ┌──────────────────────────────────────┐            │
│  │ name → '张三'                         │            │
│  │ age  → 28                             │            │
│  │ email→ 'zhangsan@example.com'         │            │
│  │  ← 直接存储在对象的固定偏移量位置       │            │
│  └──────────────────────────────────────┘            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 为什么需要 `__slots__`？

```python
# ❌ 普通类：每个实例都有一个 __dict__ 字典
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

u1 = User("张三", 28)
u2 = User("李四", 32)
# u1.__dict__ = {'name': '张三', 'age': 28}  ← 每个实例都有一个字典
# u2.__dict__ = {'name': '李四', 'age': 32}
# 两个字典，每个大约 232 字节（CPython）
```

```python
# ✅ 使用 __slots__：没有 __dict__，节省内存
class User:
    __slots__ = ('name', 'age')

    def __init__(self, name, age):
        self.name = name
        self.age = age

u1 = User("张三", 28)
u2 = User("李四", 32)
# 没有 __dict__，每个实例大约节省 40%~50% 内存
```

---

## 🔬 原理深入

### 内存布局对比

```
普通类实例（CPython 3.10+）：
┌──────────────────────────┐
│ PyObject_HEAD             │  16 bytes (引用计数 + 类型指针)
│ __dict__ pointer ────────│──→ 字典对象 (~232 bytes)
│ __weakref__ pointer      │
└──────────────────────────┘
总大小: ~64 bytes + 字典大小

__slots__ 类实例：
┌──────────────────────────┐
│ PyObject_HEAD             │  16 bytes
│ slot[0] (name)           │  8 bytes (指针)
│ slot[1] (age)            │  8 bytes (指针)
└──────────────────────────┘
总大小: ~32 bytes（没有字典开销）
```

### `__slots__` 的底层实现

```python
# CPython 中，__slots__ 通过 PyMemberDef 实现
# 每个 slot 是一个固定偏移量的成员变量
# 访问速度比 __dict__ 查找更快

class WithSlots:
    __slots__ = ('x', 'y')

class WithoutSlots:
    def __init__(self):
        self.x = 0
        self.y = 0

# 性能对比：
# 属性访问: WithSlots 比 WithoutSlots 快约 5-10%
# 内存占用: WithSlots 比 WithoutSlots 小约 40-50%
```

### `__slots__` 与继承

```python
class Base:
    __slots__ = ('x',)

class Child(Base):
    __slots__ = ('y',)  # 添加新槽位

c = Child()
c.x = 1  # ✅ 继承的槽位
c.y = 2  # ✅ 自己的槽位
# c.z = 3  # ❌ AttributeError: 'Child' object has no attribute 'z'
```

---

## 📖 API 速查表

### 基本用法

```python
class MyClass:
    __slots__ = ('attr1', 'attr2', 'attr3')

    def __init__(self, attr1, attr2, attr3):
        self.attr1 = attr1
        self.attr2 = attr2
        self.attr3 = attr3
```

### 带默认值的 slot

```python
class MyClass:
    __slots__ = ('x', 'y')

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

# slot 没有默认值机制，需要在 __init__ 中设置
```

### 只读 slot

```python
class MyClass:
    __slots__ = ('_x',)

    @property
    def x(self):
        return self._x

    def __init__(self, x):
        self._x = x

obj = MyClass(10)
print(obj.x)  # 10
# obj.x = 20  # ❌ AttributeError (没有 setter)
```

### 动态添加属性（绕过 slots）

```python
class MyClass:
    __slots__ = ('x',)

obj = MyClass()
obj.x = 10

# 通过实例 __dict__ 绕过（如果允许）
obj.__dict__['y'] = 20  # 需要先允许扩展
# 或者使用 types.SimpleNamespace
```

---

## 📊 图解

### 内存布局对比

```mermaid
graph TB
    subgraph "普通类实例"
        A1[PyObject_HEAD] --> B1[__dict__ pointer]
        B1 --> C1[dict object]
        C1 --> D1["'name': '张三'"]
        C1 --> E1["'age': 28"]
        C1 --> F1["'email': '...'"]
    end

    subgraph "__slots__ 类实例"
        A2[PyObject_HEAD] --> B2["slot[0]: name"]
        A2 --> C2["slot[1]: age"]
        A2 --> D2["slot[2]: email"]
    end
```

### 性能对比

```
┌───────────────────────────────────────────┐
│         100,000 个对象内存对比             │
├───────────────────┬───────────────────────┤
│  普通类            │  __slots__ 类         │
├───────────────────┼───────────────────────┤
│  ~50 MB           │  ~25 MB              │
│  (每个 ~500 bytes)│  (每个 ~250 bytes)   │
├───────────────────┼───────────────────────┤
│  属性访问: 100ns   │  属性访问: 90ns       │
│  属性设置: 120ns   │  属性设置: 95ns       │
└───────────────────┴───────────────────────┘
```

---

## 💻 实战代码案例

### 案例1：百万级数据对象优化

```python
import sys
import time
from typing import List


class PointNormal:
    """普通类 — 使用 __dict__"""

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


class PointSlots:
    """使用 __slots__ 的类"""

    __slots__ = ('x', 'y', 'z')

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


def benchmark():
    n = 100_000

    # 内存对比
    print("=== 内存对比 ===")

    normal_points = [PointNormal(i, i*2, i*3) for i in range(n)]
    slots_points = [PointSlots(i, i*2, i*3) for i in range(n)]

    normal_size = sys.getsizeof(normal_points[0])
    slots_size = sys.getsizeof(slots_points[0])

    print(f"普通类单个对象大小: {normal_size} bytes")
    print(f"__slots__ 类单个对象大小: {slots_size} bytes")
    print(f"节省: {(1 - slots_size/normal_size)*100:.1f}%")

    # 注意：sys.getsizeof 不包含 __dict__ 的大小
    # 需要额外计算
    normal_dict_size = sys.getsizeof(normal_points[0].__dict__)
    print(f"\n普通类 __dict__ 大小: {normal_dict_size} bytes")
    print(f"实际总大小（含 dict）: {normal_size + normal_dict_size} bytes")
    print(f"实际节省: {(1 - slots_size/(normal_size + normal_dict_size))*100:.1f}%")

    # 速度对比
    print("\n=== 速度对比 ===")

    # 属性访问
    start = time.perf_counter()
    for _ in range(1000000):
        _ = normal_points[0].x
    normal_access = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(1000000):
        _ = slots_points[0].x
    slots_access = time.perf_counter() - start

    print(f"普通类属性访问: {normal_access:.3f}s")
    print(f"__slots__ 属性访问: {slots_access:.3f}s")
    print(f"加速: {normal_access/slots_access:.2f}x")

    # 属性设置
    start = time.perf_counter()
    for i in range(1000000):
        normal_points[0].x = i
    normal_set = time.perf_counter() - start

    start = time.perf_counter()
    for i in range(1000000):
        slots_points[0].x = i
    slots_set = time.perf_counter() - start

    print(f"\n普通类属性设置: {normal_set:.3f}s")
    print(f"__slots__ 属性设置: {slots_set:.3f}s")
    print(f"加速: {normal_set/slots_set:.2f}x")


benchmark()
```

### 案例2：游戏实体系统

```python
"""
游戏实体系统 — 使用 __slots__ 优化大量游戏对象
"""
import time
from typing import List


class GameObject:
    """游戏对象基类"""

    __slots__ = ('_id', '_active', '_x', '_y')

    def __init__(self, obj_id: int, x: float, y: float):
        self._id = obj_id
        self._active = True
        self._x = x
        self._y = y

    @property
    def position(self):
        return (self._x, self._y)

    @position.setter
    def position(self, pos):
        self._x, self._y = pos

    def deactivate(self):
        self._active = False


class Player(GameObject):
    """玩家类"""

    __slots__ = ('_health', '_name', '_score')

    def __init__(self, obj_id: int, name: str, x: float = 0, y: float = 0):
        super().__init__(obj_id, x, y)
        self._name = name
        self._health = 100
        self._score = 0

    @property
    def health(self):
        return self._health

    def take_damage(self, amount: int):
        self._health = max(0, self._health - amount)
        if self._health <= 0:
            self.deactivate()

    @property
    def score(self):
        return self._score

    def add_score(self, points: int):
        self._score += points


class Enemy(GameObject):
    """敌人类"""

    __slots__ = ('_health', '_damage', '_speed')

    def __init__(self, obj_id: int, x: float, y: float,
                 health: int = 50, damage: int = 10, speed: float = 1.0):
        super().__init__(obj_id, x, y)
        self._health = health
        self._damage = damage
        self._speed = speed

    def attack(self, target: Player):
        if self._active and target._active:
            target.take_damage(self._damage)
            return True
        return False


class GameWorld:
    """游戏世界 — 管理所有游戏对象"""

    def __init__(self):
        self._objects: List[GameObject] = []
        self._next_id = 0

    def spawn_player(self, name: str, x: float = 0, y: float = 0) -> Player:
        player = Player(self._next_id, name, x, y)
        self._objects.append(player)
        self._next_id += 1
        return player

    def spawn_enemy(self, x: float, y: float, **kwargs) -> Enemy:
        enemy = Enemy(self._next_id, x, y, **kwargs)
        self._objects.append(enemy)
        self._next_id += 1
        return enemy

    def active_objects(self) -> List[GameObject]:
        return [obj for obj in self._objects if obj._active]

    def stats(self) -> dict:
        active = self.active_objects()
        players = [o for o in active if isinstance(o, Player)]
        enemies = [o for o in active if isinstance(o, Enemy)]
        return {
            "total": len(self._objects),
            "active": len(active),
            "players": len(players),
            "enemies": len(enemies),
        }


# 使用演示
if __name__ == "__main__":
    print("=" * 60)
    print("Day 050 - __slots__ 实战：游戏实体系统")
    print("=" * 60)

    import sys

    world = GameWorld()

    # 创建玩家和敌人
    player = world.spawn_player("勇者", 0, 0)
    enemy1 = world.spawn_enemy(10, 5)
    enemy2 = world.spawn_enemy(8, 3)

    # 战斗
    print("\n--- 战斗开始 ---")
    print(f"玩家生命: {player.health}")

    enemy1.attack(player)
    print(f"敌人1攻击后，玩家生命: {player.health}")

    enemy2.attack(player)
    print(f"敌人2攻击后，玩家生命: {player.health}")

    enemy1.attack(player)
    print(f"敌人1再次攻击后，玩家生命: {player.health}")

    # 统计
    print(f"\n--- 世界统计 ---")
    print(world.stats())

    # 内存分析
    print(f"\n--- 内存分析 ---")
    print(f"Player 对象大小: {sys.getsizeof(player)} bytes")
    print(f"Enemy 对象大小: {sys.getsizeof(enemy1)} bytes")
    print(f"Player 有 __dict__? {hasattr(player, '__dict__')}")
    print(f"Enemy 有 __dict__? {hasattr(enemy1, '__dict__')}")
```

### 案例3：配置类优化

```python
"""
配置类 — 使用 __slots__ 避免意外添加属性
"""
import json
from typing import Any, Dict


class Config:
    """
    配置类 — 使用 __slots__ 实现：
    1. 内存优化
    2. 防止意外添加属性
    3. 更快的属性访问
    """

    __slots__ = ('_host', '_port', '_debug', '_db_url', '_secret_key')

    def __init__(self, host: str = "localhost", port: int = 8000,
                 debug: bool = False, db_url: str = "", secret_key: str = ""):
        self._host = host
        self._port = port
        self._debug = debug
        self._db_url = db_url
        self._secret_key = secret_key

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = value

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value: int):
        if not isinstance(value, int) or value < 0 or value > 65535:
            raise ValueError(f"无效端口: {value}")
        self._port = value

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = value

    @property
    def db_url(self):
        return self._db_url

    @property
    def secret_key(self):
        return self._secret_key

    def to_dict(self) -> dict:
        """导出配置（隐藏敏感信息）"""
        return {
            "host": self._host,
            "port": self._port,
            "debug": self._debug,
            "db_url": self._db_url[:10] + "..." if self._db_url else "",
        }

    def __repr__(self):
        return f"Config(host={self._host}, port={self._port}, debug={self._debug})"


class SafeConfig(Config):
    """安全配置 — 继承 Config 的 slots"""

    __slots__ = ('_api_key', '_api_secret')

    def __init__(self, api_key: str = "", api_secret: str = "", **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._api_secret = api_secret

    @property
    def api_key(self):
        return self._api_key[:4] + "****" if self._api_key else ""

    @property
    def api_secret(self):
        return "****" if self._api_secret else ""


# 使用
if __name__ == "__main__":
    print("\n--- 配置类 ---")

    config = Config(
        host="0.0.0.0",
        port=8080,
        debug=True,
        db_url="postgresql://user:pass@localhost/db",
        secret_key="super-secret-key"
    )

    print(f"配置: {config}")
    print(f"导出: {json.dumps(config.to_dict(), ensure_ascii=False, indent=2)}")

    # 防止意外添加属性
    try:
        config.new_attr = "test"
    except AttributeError as e:
        print(f"\n防止意外添加: {e}")

    # 安全配置
    print("\n--- 安全配置 ---")
    safe = SafeConfig(
        api_key="sk-1234567890abcdef",
        api_secret="secret-value",
        host="api.example.com"
    )
    print(f"API Key: {safe.api_key}")
    print(f"API Secret: {safe.api_secret}")
    print(f"Host: {safe.host}")
```

---

## 🧠 思考题

1. **`__slots__` 为什么不能和 `__dict__` 同时使用？** 如果你既想要内存优化，又想动态添加属性，该怎么办？

2. **`__slots__` 对数据类（`@dataclass`）有什么影响？** 如何为 `@dataclass` 添加 `__slots__`？

3. **在什么场景下不应该使用 `__slots__`？** 比如需要动态属性、序列化、或频繁修改的类。

4. **`__slots__` 和 `NamedTuple` 的区别是什么？** 什么情况下用哪个更合适？

5. **如何测量 `__slots__` 的实际内存节省？** 除了 `sys.getsizeof`，还有什么方法可以更准确地测量？

---

## 📋 今日小结

| 概念 | 说明 |
|------|------|
| **`__slots__`** | 使用固定存储槽替代 `__dict__`，节省内存 |
| **内存节省** | 每个实例节省约 40-50% 内存 |
| **性能提升** | 属性访问和设置速度提升约 5-10% |
| **继承规则** | 子类需要声明自己的 `__slots__` |
| **限制** | 不能动态添加未声明的属性 |
| **适用场景** | 大量相同结构的对象（如游戏实体、数据记录） |
