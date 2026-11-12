# Day 036 — 封装与数据隐藏

> 掌握 Python 中的封装机制：名称改写、私有属性约定、属性访问控制，实战安全的 API 封装

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 封装的概念 | ⭐⭐ | 面向对象三大特征之一，信息隐藏 |
| 名称改写 (Name Mangling) | ⭐⭐⭐ | `__attr` → `_Class__attr` 机制 |
| 私有属性约定 | ⭐⭐ | `_single` vs `__double` 下划线 |
| Property 属性 | ⭐⭐⭐ | `@property` 实现可控属性访问 |
| 实战：安全的 API 封装 | ⭐⭐⭐⭐ | 完整的 API 客户端封装 |

---

## 一、封装的概念

### 1.1 什么是封装

**封装** 是面向对象编程的三大特征之一，指将 **数据（属性）和操作数据的方法（行为）** 打包在一起，并对外隐藏内部实现细节。

```
┌─────────────────────────────────┐
│         电视机 (TV)              │
│                                 │
│  ┌───────────────────────────┐  │
│  │    内部实现 (隐藏)         │  │
│  │  ┌─────────────────────┐  │  │
│  │  │ voltage: 220V       │  │  │
│  │  │ frequency: 50Hz     │  │  │
│  │  │ picture_tube_temp   │  │  │
│  │  │ circuit_board_state │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │    公开接口 (暴露)         │  │
│  │  power_on()               │  │
│  │  power_off()              │  │
│  │  change_channel(n)        │  │
│  │  adjust_volume(n)         │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
      ↑ 用户只通过接口操作，不关心内部电路
```

### 1.2 封装的优点

| 优点 | 说明 |
|------|------|
| **信息隐藏** | 隐藏复杂实现，暴露简洁接口 |
| **降低复杂度** | 使用者不需要了解内部细节 |
| **提高安全性** | 防止外部代码意外修改内部状态 |
| **便于修改** | 修改内部实现不影响外部代码 |
| **提高复用性** | 封装良好的模块可以独立使用 |

### 1.3 Python 中的封装哲学

Python 的封装哲学与其他语言不同：

```
其他语言 (Java/C++):          Python:
═══════════════════════       ═══════════════════════
private/protected/public      _约定 / __名称改写
编译器强制                    开发者自觉遵守
「我们信任开发者」              「我们也是成年人了」
```

> **「We are all consenting adults here.」** — Python 社区名言

---

## 二、名称改写（Name Mangling）

### 2.1 基本机制

Python 中，以 **双下划线开头** 的属性名会触发 **名称改写（name mangling）**：

```python
class MyClass:
    def __init__(self):
        self.public = "公开的"
        self._protected = "受保护的"
        self.__private = "私有的"  # → _MyClass__private

    def get_private(self):
        return self.__private


obj = MyClass()
print(obj.public)                 # 公开的    ✅ 直接访问
print(obj._protected)             # 受保护的   ✅ 约定访问
# print(obj.__private)            # ❌ AttributeError

print(obj._MyClass__private)      # 私有的    ✅ 仍然可以访问
print(obj.get_private())          # 私有的    ✅ 通过方法访问
```

### 2.2 改名的规则

```
__attribute_name
      ↓
_ClassName__attribute_name
```

```python
class A:
    def __init__(self):
        self.__x = 10      # → self._A__x

class B(A):
    def __init__(self):
        super().__init__()
        self.__x = 20      # → self._B__x (和自己的 __x 不同！)


obj = B()
print(obj._A__x)   # 10  ← 父类的 __x
print(obj._B__x)   # 20  ← 子类的 __x
```

### 2.3 名称改写的作用

1. **避免子类意外覆盖父类的私有属性**
2. **作为「更强」的私有声明（虽然仍然可访问）**
3. **防止命名冲突（特别是在继承体系中）**

```python
class Base:
    def __init__(self):
        self.__id = 0     # _Base__id

    def get_id(self):
        return self.__id  # 始终访问 _Base__id


class Derived(Base):
    def __init__(self):
        super().__init__()
        self.__id = 1     # _Derived__id — 不影响父类的 __id


d = Derived()
print(d.get_id())          # 0    ← 父类方法访问的是 _Base__id
print(d._Base__id)         # 0
print(d._Derived__id)      # 1
```

### 2.4 何时使用名称改写

```
✅ 使用 __ 的情况:                ❌ 不需要使用 __ 的情况:
──────────────────────           ─────────────────────────
• 父类定义不希望被子类覆盖          • 简单的内部属性
• 框架/库的内部实现                • 已经被 @property 管理的属性
• 需要「强烈暗示」私有              • __xxx__ 魔术方法
                                  • 测试代码中的内部变量
```

---

## 三、私有属性约定

### 3.1 Python 的属性命名约定

| 命名 | 约定 | 示例 |
|------|------|------|
| `name` | 公开属性 | `self.name` |
| `_name` | 受保护的内部属性 | `self._data` |
| `__name` | 名称改写私有属性 | `self.__secret` |
| `__name__` | 魔术方法 | `__init__`, `__str__` |
| `name_` | 避免与关键字冲突 | `class_`, `type_` |

### 3.2 单下划线前缀 `_`

```python
class Database:
    def __init__(self):
        self._connection = None     # 内部使用，不是公共 API
        self._cache = {}             # 实现细节

    def connect(self):
        """公开方法"""
        self._init_connection()     # 调用内部方法

    def _init_connection(self):
        """内部初始化方法（以下划线开头 => 非公开 API）"""
        # 这个方法不是公共接口的一部分
        self._connection = "connected"

    # `_` 前缀是约定，不是强制
    # from module import * 不会导入 _ 开头的名字
```

### 3.3 Python 的信息隐藏哲学

```
其他语言:                        Python:
"你不能访问这个"                   "你可以访问，但建议别这么做"
private int x;                    _x = 42

编译器报错                        只是命名惯例
完全无法访问                      仍然可以访问（self._x）
```

**Python 认为：**
- 保护是通过 **文档和约定** 实现的，而不是编译器强制
- 使用者应该 **信任** API 提供者
- 如果需要访问私有属性（调试、测试），**可以** 访问

---

## 四、Property 属性

### 4.1 为什么需要 Property

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    # ❌ 直接暴露属性 — 无法添加逻辑
    # self.celsius = celsius

    # ✅ 使用方法暴露
    def get_celsius(self):
        return self._celsius

    def set_celsius(self, value):
        if value < -273.15:
            raise ValueError("温度不能低于绝对零度")
        self._celsius = value

    def del_celsius(self):
        print("删除温度设置")
        self._celsius = 0


t = Temperature(25)
print(t.get_celsius())   # 需要调用方法，不够 Pythonic
t.set_celsius(30)        # 不像属性访问
```

### 4.2 @property 装饰器

Property 允许你 **像访问属性一样使用方法**：

```python
class Temperature:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        """获取摄氏温度（像访问属性一样）"""
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        """设置摄氏温度（带验证）"""
        if value < -273.15:
            raise ValueError("温度不能低于绝对零度")
        self._celsius = value

    @celsius.deleter
    def celsius(self):
        """删除温度"""
        print("删除温度")
        self._celsius = 0

    @property
    def fahrenheit(self):
        """计算属性（只读）"""
        return self._celsius * 9/5 + 32


t = Temperature(25)
print(t.celsius)         # 25       ← 像属性一样访问
t.celsius = 30           # ✅ 像属性一样赋值
print(t.fahrenheit)      # 86.0     ← 计算属性

# t.celsius = -300       # ❌ ValueError!
# del t.celsius          # 触发 deleter
```

### 4.3 Property 的优势

```
⌨️ 不用 Property:                          ✅ 使用 Property:
─────────────────────                     ─────────────────────
class Person:                             class Person:
    def __init__(self, name):                 def __init__(self, name):
        self.name = name                          self._name = name

# 后来想加验证，必须改成方法：              # 后来加验证，不改接口：
p = Person("Alice")                         p = Person("Alice")
p.set_name("Bob")      # ❌ 接口变了!       p.name = "Bob"  # ✅ 接口不变!
```

**Property 的核心价值：** 从 **直接属性访问** 切换到 **受控访问** 时，使用者代码完全不需要修改。

### 4.4 描述符协议（进阶）

Property 的底层是 **描述符协议**（Descriptor Protocol）：

```python
class ValidatedAttribute:
    """自定义描述符 — 带验证的属性"""

    def __init__(self, validator):
        self.validator = validator
        self.data = {}

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.data.get(id(obj), None)

    def __set__(self, obj, value):
        self.validator(value)  # 验证
        self.data[id(obj)] = value

    def __delete__(self, obj):
        del self.data[id(obj)]


def validate_positive(value):
    if value <= 0:
        raise ValueError("必须是正数")


class Order:
    quantity = ValidatedAttribute(validate_positive)
    price = ValidatedAttribute(validate_positive)

    def __init__(self, quantity, price):
        self.quantity = quantity
        self.price = price

    @property
    def total(self):
        return self.quantity * self.price


# order = Order(-1, 100)   # ❌ ValueError!
order = Order(3, 100)
print(order.total)          # 300
```

---

## 五、实战：安全的 API 封装

### 5.1 系统设计

```
┌─────────────────────────────────────────────────┐
│                  APIClient                       │
│  ┌───────────────────────────────────────────┐  │
│  │  🔐 私有属性                              │  │
│  │  __api_key: str                           │  │
│  │  __base_url: str                          │  │
│  │  __session: requests.Session              │  │
│  │  __rate_limiter: deque                    │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │  📋 公开接口                              │  │
│  │  base_url (property) — 只读              │  │
│  │  rate_limit (property) — 读写 + 验证     │  │
│  │  get() — HTTP GET                       │  │
│  │  post() — HTTP POST                     │  │
│  │  close() — 清理资源                      │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │  ⚙️ 内部实现（_ 前缀）                    │  │
│  │  _request() — 统一请求处理                │  │
│  │  _check_rate_limit() — 频率控制           │  │
│  │  _refresh_token() — token 刷新            │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 5.2 核心实现

```python
import time
import hashlib
import hmac
from collections import deque
from typing import Optional, Dict, Any


class APIClient:
    """安全的 API 客户端封装"""

    def __init__(self, api_key: str, base_url: str,
                 max_requests_per_sec: int = 10):
        self.__api_key = api_key               # 名称改写 → _APIClient__api_key
        self.__base_url = base_url.rstrip('/')  # 名称改写
        self.__session = None                   # 懒初始化
        self.__call_count = 0

        # 速率限制器
        self.__request_times = deque()
        self._rate_limit = max_requests_per_sec  # 受保护的属性

    # ── Property 控制 ──

    @property
    def base_url(self) -> str:
        """基础 URL（只读）"""
        return self.__base_url

    @property
    def rate_limit(self) -> int:
        """每秒最大请求数"""
        return self._rate_limit

    @rate_limit.setter
    def rate_limit(self, value: int):
        """设置速率限制（带验证）"""
        if not isinstance(value, int) or value < 1:
            raise ValueError("速率限制必须是正整数")
        self._rate_limit = value

    @property
    def call_count(self) -> int:
        """API 调用次数（只读）"""
        return self.__call_count

    # ── 内部方法（_ 前缀） ──

    def _get_session(self):
        """获取 session（懒初始化）"""
        if self.__session is None:
            import requests
            self.__session = requests.Session()
            # 设置默认请求头
            self.__session.headers.update({
                'Authorization': f'Bearer {self.__api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'APIClient/1.0',
            })
        return self.__session

    def _check_rate_limit(self):
        """检查是否超过速率限制"""
        now = time.time()
        # 移除超过 1 秒的旧记录
        while self.__request_times and \
                self.__request_times[0] < now - 1:
            self.__request_times.popleft()

        if len(self.__request_times) >= self._rate_limit:
            # 需要等待
            wait_time = self.__request_times[0] + 1 - now
            if wait_time > 0:
                print(f"  ⏳ 速率限制，等待 {wait_time:.2f}s")
                time.sleep(wait_time)

    def _make_signature(self, method: str, path: str,
                        timestamp: str) -> str:
        """生成请求签名（内部实现细节）"""
        message = f"{method}{path}{timestamp}"
        return hmac.new(
            self.__api_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    # ── 公开方法 ──

    def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        """发送 GET 请求"""
        return self._request('GET', path, params=params)

    def post(self, path: str, data: Optional[Dict] = None) -> Dict:
        """发送 POST 请求"""
        return self._request('POST', path, json=data)

    def put(self, path: str, data: Optional[Dict] = None) -> Dict:
        """发送 PUT 请求"""
        return self._request('PUT', path, json=data)

    def delete(self, path: str) -> Dict:
        """发送 DELETE 请求"""
        return self._request('DELETE', path)

    def _request(self, method: str, path: str,
                 **kwargs) -> Dict:
        """统一请求处理（内部方法）"""
        self._check_rate_limit()
        self.__call_count += 1

        session = self._get_session()
        url = f"{self.__base_url}/{path.lstrip('/')}"

        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"  ❌ 请求失败: {e}")
            return {"error": str(e)}

    def close(self):
        """关闭会话"""
        if self.__session:
            self.__session.close()
            self.__session = None

    # ── 上下文管理器支持 ──

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ── 隐藏 __api_key 的字符串表示 ──

    def __repr__(self):
        return f"APIClient(base_url={self.__base_url!r})"

    def __str__(self):
        return f"APIClient({self.__base_url})"


# 使用示例
client = APIClient("sk-secret-key-12345", "https://api.example.com/v1")

print(client.base_url)           # 只读
print(client.call_count)         # 只读
# print(client.__api_key)        # ❌ AttributeError (名称改写)

# 使用上下文管理器
with APIClient("key", "https://api.test.com") as c:
    result = c.get("/users", params={"page": 1})
    print(f"  请求结果: {result}")
```

---

## 六、思考题

1. **名称改写的限制**：名称改写真的能阻止外部访问吗？在什么场景下需要绕过它？（Python 的动态特性允许 `obj._ClassName__attr`）

**参考答案**

**不能真正阻止**。名称改写只是把 `self.__attr` 在编译期改名为 `self._ClassName__attr`，目的是**避免子类意外覆盖父类同名属性**，而不是安全屏障。任何人只要知道类名，就能用 `obj._ClassName__attr` 直接读写，甚至 `vars(obj)` / `obj.__dict__` 里就能看到改写后的真实名字。它"防君子不防小人"。

**需要绕过它的场景**：

- **调试 / 白盒测试**：检查对象内部状态、验证不变量；
- **序列化 / 反序列化**：保存或恢复对象时需要触及内部字段；
- **框架 / 反射工具**：ORM、依赖注入等需要动态访问成员；
- **临时修补 / 兼容**：在不改源码的前提下访问库的内部实现。

但要记住：绕过改写意味着**依赖了实现细节**，对方一旦改名/重构就会失效，生产代码应优先走公开接口。

```python
# 思考题1：名称改写不能真正阻止访问
class Account:
    def __init__(self):
        self.__balance = 100


a = Account()
# print(a.__balance)        # AttributeError
print(a._Account__balance)  # 100，绕过改写
print(vars(a))              # 实例字典里的真实名字
```

预期输出：

```text
100
{'_Account__balance': 100}
```

⚠️ 注意：真要保护敏感数据（如密钥），名称改写毫无作用——它只是命名变换，不是加密。安全要靠接口设计、最小暴露和真正的访问控制手段。

2. **`_` vs `__`**：在什么情况下应该使用单下划线，什么时候应该使用双下划线？社区的共识是什么？

**参考答案**

- **单下划线 `_name`**：表达"内部使用、非公开 API"的**约定**，解释器不做任何限制（仅 `from module import *` 默认不导入）。这是**日常默认选择**，绝大多数"私有"属性/方法都该用它。
- **双下划线 `__name`**：触发**名称改写**，唯一实际价值是**避免子类意外覆盖父类的同名属性**。只在"这个类会被继承、且某个内部名字可能与子类撞车"时才需要，典型是框架/库的基类。

**社区共识（PEP 8 与主流风格）**：**优先用单下划线**，谨慎使用双下划线。因为名称改写会让访问变麻烦（调试、测试都得写 `_Class__name`），而它解决的"子类撞名"问题在实际中很少见；滥用双下划线反而增加复杂度。简单内部属性、已被 `@property` 管理的属性，都不需要双下划线。

```python
# 思考题2：双下划线避免子类撞名
class Base:
    def __init__(self):
        self.__id = 'base'    # _Base__id

    def show(self):
        return self.__id


class Child(Base):
    def __init__(self):
        super().__init__()
        self.__id = 'child'   # _Child__id，不覆盖父类


c = Child()
print(c.show())          # base
print(c._Base__id)       # base
print(c._Child__id)      # child
```

预期输出：

```text
base
base
child
```

💡 提示：父类的 `show()` 始终读到 `_Base__id`（`base`），子类的 `__id` 存成 `_Child__id`（`child`），互不干扰——这正是双下划线存在的意义。若没有继承撞名风险，用 `_id` 就够了。

3. **Property vs Getter/Setter**：Python 的 `@property` 和 Java 的 getter/setter 风格有什么根本区别？为什么 Python 社区偏好 property？

**参考答案**

根本区别在于**"统一访问原则"（Uniform Access Principle）**：

- **Java**：字段访问（`obj.x`）和方法调用（`obj.getX()`）是两种不同语法，且字段无法被拦截。为了将来能加校验/计算，Java 习惯**一开始就写 getter/setter**，哪怕暂时只是简单返回字段——于是产生大量样板代码。
- **Python**：可以**先用普通公开属性起步**（`self.x = x`），等真正需要校验/计算时再把它升级成 `@property`，而**所有调用代码 `obj.x` 一行都不用改**。属性读写在语法上始终是 `obj.x`，背后是字段还是方法对调用者透明。

**社区偏好 property 的原因**：

- 语法简洁自然（`obj.x` 而非 `obj.get_x()`），无样板；
- 支持**渐进式演进**，不必为"将来可能需要"提前付出代价（YAGNI）；
- 不写 setter 即只读，计算属性用起来像字段，语义清晰；
- 与 `getattr`/`hasattr` 等内置机制无缝协作。

```python
# 思考题3：property 让受控访问保持属性语法
class Account:
    def __init__(self, balance=0):
        self._balance = balance

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, value):
        if value < 0:
            raise ValueError('余额不能为负')
        self._balance = value


a = Account(100)
print(a.balance)     # 像属性一样读
a.balance = 200      # 像属性一样写，走校验
print(a.balance)
```

预期输出：

```text
100
200
```

💡 提示：property 适合"轻量、快速"的读写；若获取属性要发起网络请求或耗时计算，用显式方法更能提醒调用者成本，避免"看起来是字段、实则很贵"的 surprises。

4. **描述符 vs Property**：什么时候应该使用描述符协议而不是 `@property`？描述符的复用价值在哪里？

**参考答案**

`@property` 本质上是描述符的一个**特例**，但它**绑定在某个具体属性上**——每个需要校验的字段都得重复写一遍 getter/setter，逻辑无法直接复用。

**该用描述符的场景**：当**同一套访问逻辑要应用到多个属性或多个类**时。描述符是一个实现了 `__get__`/`__set__`/`__delete__` 的**独立类**，可以像插件一样赋值给任意多个属性名，把"校验、类型检查、日志、惰性加载、单位换算"等横切逻辑**写一次、到处复用**。

**复用价值**：

- 一个 `Positive` 描述符可同时管 `quantity`、`price`、`weight`……不必为每个字段重复代码；
- 配合 `__set_name__`（3.6+）自动拿到属性名，报错信息更精准；
- 逻辑集中在一个类里，易维护、易测试、可跨项目复用。

反之，若只是**单个属性**的简单读写控制，用 `@property` 更直观，没必要上描述符。

```python
# 思考题4：描述符复用同一套校验逻辑
class Positive:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError(f'{self.name} 必须为正数')
        obj.__dict__[self.name] = value


class Order:
    quantity = Positive()   # 同一个描述符复用到多个属性
    price = Positive()


o = Order()
o.quantity = 3
o.price = 100
print(o.quantity, o.price)
try:
    o.price = -1
except ValueError as e:
    print('ValueError:', e)
```

预期输出：

```text
3 100
ValueError: price 必须为正数
```

💡 提示：这里把值存进 `obj.__dict__[self.name]`，每个实例各自独立；`__set_name__` 让描述符知道自己被赋给了哪个属性名，从而在报错时指出是 `price` 还是 `quantity`。

5. **封装与测试**：单元测试中经常需要访问私有属性来验证状态（白盒测试），这是否违背了封装原则？如何平衡封装与可测试性？

**参考答案**

**不算真正违背**。封装约束的是**生产代码中"外部消费者"对 API 的依赖**——它承诺"公开接口稳定、内部实现可自由改动"。而测试是**特权角色**，本就需要了解内部以验证正确性。Python"我们都是成年人"的哲学也明确允许为调试/测试访问内部。所以白盒测试访问 `_attr` / `_Class__attr` 是被接受的。

**但要权衡**：直接断言私有状态会让测试**耦合实现细节**，一旦重构内部就大片失败，削弱了"封装便于修改"的好处。平衡之道：

- **优先黑盒**：尽量通过**公开接口**验证行为与可观察结果，这类测试最稳健；
- **必要时白盒**：只有当内部不变量无法从外部观察时，才直接检查私有状态，并把它当作"易碎、需随实现更新"的测试；
- **为可测试性设计**：提供只读 property、合理的查询方法、依赖注入，让状态"可观察但不必可随意篡改"；
- **别过度隐藏**：如果大量测试都要绕过封装，往往是接口设计不足或职责过重的信号，应重构而非硬闯。

```python
# 思考题5：白盒测试访问内部状态
class Stack:
    def __init__(self):
        self._items = []

    def push(self, x):
        self._items.append(x)

    def pop(self):
        return self._items.pop()


s = Stack()
s.push(1)
s.push(2)
assert s._items == [1, 2]   # 直接验证内部不变量
print(s.pop())              # 也通过公开接口验证
print(s._items)
```

预期输出：

```text
2
[1]
```

💡 提示：上例中 `assert s._items == [1, 2]` 是白盒断言；而 `s.pop()` 返回 `2` 是黑盒验证。能用后者覆盖的行为，就尽量别依赖前者，这样内部从列表换成别的结构时测试仍可能通过。

---

## 📝 本章小结

```
✅ 封装 —— 隐藏实现细节，暴露简洁接口
✅ 名称改写 —— __attr → _ClassName__attr
✅ 单下划线约定 —— _internal 表示「内部使用」
✅ @property —— 像属性一样访问受控方法
✅ 描述符协议 —— 属性访问的底层机制
✅ 实战：API 客户端 —— 安全的封装实践
```
