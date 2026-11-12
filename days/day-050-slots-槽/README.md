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

**参考答案**

并不是「绝对互斥」。真正的原因是：一旦类定义了 `__slots__`，Python 就**不再自动为实例创建 `__dict__`**，未声明的属性无处存放，于是看起来二者不能共存。

- 想「既省内存又能动态加属性」，可以把 `'__dict__'` 显式写进 `__slots__`，固定槽和动态字典就同时存在了。
- 但代价是字典又回来了，内存优势基本消失——这是「鱼与熊掌」的权衡。
- 折中：只给少数高频属性用槽，另设一个字典槽（如 `__slots__ = ('x', 'extra')`，把动态属性塞进 `extra`）；或干脆不用 `__slots__`。

小例子（已验证）：

```python
class Hybrid:
    __slots__ = ('x', '__dict__')   # 显式保留 __dict__
    def __init__(self):
        self.x = 1

h = Hybrid()
h.y = 2                              # 动态属性进入 __dict__
print(h.x, h.y, h.__dict__)          # 1 2 {'y': 2}

class Strict:
    __slots__ = ('x',)               # 不含 __dict__
s = Strict()
try:
    s.y = 2
except AttributeError as e:
    print(e)                         # 'Strict' object has no attribute 'y'
```

2. **`__slots__` 对数据类（`@dataclass`）有什么影响？** 如何为 `@dataclass` 添加 `__slots__`？

**参考答案**

`@dataclass` 默认生成的类带 `__dict__`，可以动态加属性。加上 `__slots__` 后同样能省内存、禁止未声明属性，但要注意「字段默认值」与槽的冲突。

- **Python 3.10+**：直接写 `@dataclass(slots=True)`，解释器会自动生成 `__slots__` 并重建类，最省心。
- **旧版本手动写**：在类体里定义 `__slots__`。但若某字段带默认值（如 `x: int = 0`），该默认值会变成**类变量**，与同名槽冲突，抛 `ValueError`。解决办法是去掉类体默认值、改用 `field(default=...)` 仍会冲突，所以最稳妥还是升级到 3.10 用 `slots=True`。

小例子（已验证，Python 3.12）：

```python
from dataclasses import dataclass

@dataclass(slots=True)          # 3.10+ 自动生成 __slots__
class Point:
    x: int
    y: int

p = Point(1, 2)
print(p)                        # Point(x=1, y=2)
print(hasattr(p, '__dict__'))   # False
try:
    p.z = 3
except AttributeError as e:
    print(e)                    # 'Point' object has no attribute 'z'

# 手动写 __slots__ 时，带默认值的字段会与槽冲突
try:
    @dataclass
    class Bad:
        __slots__ = ('x',)
        x: int = 0              # 默认值 → 类变量，与同名槽冲突
except ValueError as e:
    print(e)                    # 'x' in __slots__ conflicts with class variable
```

⚠️ 注意：`slots=True` 是 Python 3.10 才加入的参数；更低版本会报 `TypeError: dataclass() got an unexpected keyword argument 'slots'`。

3. **在什么场景下不应该使用 `__slots__`？** 比如需要动态属性、序列化、或频繁修改的类。

**参考答案**

`__slots__` 是「用灵活性换内存/速度」的优化，下列场景不适合：

- **需要动态属性**：运行时要随意 `obj.new_attr = ...`（如 ORM、配置对象、给实例打补丁）。
- **多继承且多个基类都有非空 `__slots__`**：会触发「实例布局冲突」，无法创建子类。
- **依赖 `__dict__` 的工具/序列化**：一些库直接读写 `obj.__dict__`（如某些序列化、调试、`vars(obj)`）；用槽后需自己实现 `__getstate__`/`__setstate__`。
- **需要弱引用但没声明 `'__weakref__'`**：默认槽类不支持 `weakref`。
- **对象数量很少**：省下的内存微不足道，属于过早优化，反而增加维护成本。

多继承冲突小例子（已验证）：

```python
class A:
    __slots__ = ('x',)
class B:
    __slots__ = ('y',)

try:
    class C(A, B):    # 两个非空 slots 基类 → 实例布局冲突
        pass
except TypeError as e:
    print(e)          # multiple bases have instance lay-out conflict
```

💡 提示：只有「大量、结构固定、需要省内存」的对象（游戏实体、数据记录、百万级节点）才值得用 `__slots__`。

4. **`__slots__` 和 `NamedTuple` 的区别是什么？** 什么情况下用哪个更合适？

**参考答案**

两者都能省内存，但本质不同：

- **`NamedTuple` 是 `tuple` 的子类**：不可变、有序、可索引/解包/迭代，元素可哈希时整体可哈希，自带 `_fields`、`_asdict()`、`_replace()`。它适合「只读的值对象/记录」。
- **`__slots__` 类是普通类**：默认可变，按属性名访问，不能直接索引或解包（除非自己加方法），但能自由定义方法、属性、继承。它适合「有行为、需要修改的实体」。

选择：要「不可变 + 可解包 + 当字典键」用 `NamedTuple`；要「可变 + 丰富方法 + 大量实例省内存」用 `__slots__` 类。小例子（已验证）：

```python
from typing import NamedTuple

class PointNT(NamedTuple):      # tuple 子类：不可变、可索引/解包
    x: int
    y: int

class PointSlots:               # 普通类 + slots：可变、按名访问
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x, self.y = x, y

nt = PointNT(1, 2)
print(nt[0], nt.x, tuple(nt))   # 1 1 (1, 2)
try:
    nt.x = 9                    # 不可变
except AttributeError as e:
    print(e)                    # can't set attribute

ps = PointSlots(1, 2)
ps.x = 9                        # 可变
print(ps.x)                     # 9
```

5. **如何测量 `__slots__` 的实际内存节省？** 除了 `sys.getsizeof`，还有什么方法可以更准确地测量？

**参考答案**

`sys.getsizeof` 是**浅层**大小：它只算对象本身，**不含实例指向的 `__dict__`**。所以直接比较会误导——普通对象本身可能比槽对象还小，但加上字典后普通对象就大得多。更准确的做法：

- **手动补上字典**：`sys.getsizeof(obj) + sys.getsizeof(obj.__dict__)`（注意 3.11+ 同类实例共享键表，简单相加会略微高估）。
- **`tracemalloc`（标准库，推荐）**：统计「创建一整批对象」期间真实分配的内存，最贴近实际节省。
- 第三方 `pympler.asizeof` 可递归计算深层大小（需 `pip install pympler`）。

小例子（已验证，CPython 3.12 / 64 位）：

```python
import sys, tracemalloc

class Normal:
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

class Slots:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x, y, z):
        self.x, self.y, self.z = x, y, z

# 1) 浅层 getsizeof：普通对象不含 __dict__，需单独相加
a, b = Normal(1, 2, 3), Slots(1, 2, 3)
print(sys.getsizeof(a))           # 48（普通对象本身）
print(sys.getsizeof(a.__dict__))  # 296（还要加上字典）
print(sys.getsizeof(b))           # 56（槽对象本身）

# 2) tracemalloc：测量整批对象的真实分配
n = 100_000
def measure(cls):
    tracemalloc.start()
    objs = [cls(i, i, i) for i in range(n)]
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return current

print(measure(Normal))   # 约 12795440 字节
print(measure(Slots))    # 约 9592704 字节（更省）
```

预期输出：浅层大小为 `48 / 296 / 56`，可见普通对象「本身 48 + 字典 296」远大于槽对象的 56；`tracemalloc` 下 10 万个对象普通类约 12.8 MB、槽类约 9.6 MB，槽类明显更省。具体字节数随 Python 版本与平台变化，但「槽类总内存更小」的结论稳定。

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
