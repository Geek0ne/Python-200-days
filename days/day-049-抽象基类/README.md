# Day 049 — 抽象基类（ABC）

## 📚 概念解释

### 什么是抽象基类？

**抽象基类（Abstract Base Class，ABC）** 是一种不能被直接实例化的类，它定义了一组接口规范，强制子类实现特定的方法。ABC 通过 `abc` 模块提供，是 Python 实现**接口契约**的官方机制。

```
┌─────────────────────────────────────────────────┐
│              抽象基类 Shape                      │
├─────────────────────────────────────────────────┤
│  + area()      ← 必须实现                       │
│  + perimeter() ← 必须实现                       │
├─────────────────────────────────────────────────┤
│  ❌ 不能直接实例化 Shape()                       │
├─────────────────────────────────────────────────┤
│        ↓ 子类必须实现                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Circle   │  │ Rectangle│  │ Triangle │      │
│  │ area() ✓  │  │ area() ✓ │  │ area() ✓ │      │
│  │ perim() ✓ │  │ perim()✓ │  │ perim()✓ │      │
│  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────┘
```

### 为什么需要 ABC？

```python
# ❌ 没有 ABC：运行时才发现错误
class Dog:
    def speak(self):
        return "Woof"

class Cat:
    # 忘记实现 speak()
    pass

def make_sound(animal):
    return animal.speak()  # Cat 没有 speak()，运行时报错！

make_sound(Dog())  # OK
make_sound(Cat())  # ❌ AttributeError
```

```python
# ✅ 有 ABC：定义时就强制检查
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self):
        pass

# Animal()  # ❌ TypeError: Can't instantiate abstract class

class Cat(Animal):
    # 忘记实现 speak()，也会报错
    pass

# Cat()  # ❌ TypeError: Can't instantiate abstract class with abstract method 'speak'
```

---

## 🔬 原理深入

### ABCMeta 元类

`ABC` 的底层是 `ABCMeta` 元类，它在类创建时检查是否有未实现的抽象方法：

```python
from abc import ABCMeta, abstractmethod

class MyABC(metaclass=ABCMeta):
    @abstractmethod
    def required(self):
        pass

# 过程：
# 1. MyABC 类被创建时，ABCMeta.__new__ 被调用
# 2. 检查所有标记为 @abstractmethod 的方法
# 3. 如果子类没有实现所有抽象方法，禁止实例化
```

### register() — 虚拟子类

```python
from abc import ABC, abstractmethod

class Drawable(ABC):
    @abstractmethod
    def draw(self):
        pass

# 即使没有继承 ABC，也能注册为子类
class LegacyWidget:
    def draw(self):
        print("Drawing widget")

Drawable.register(LegacyWidget)  # 虚拟注册

# LegacyWidget 现在被认为是 Drawable 的子类
print(issubclass(LegacyWidget, Drawable))  # True
print(isinstance(LegacyWidget(), Drawable))  # True
```

### abstractproperty 已废弃

```python
# ❌ 旧写法（已废弃）
from abc import abstractproperty

class Old(ABC):
    @abstractproperty
    def value(self):
        pass

# ✅ 新写法
class New(ABC):
    @property
    @abstractmethod
    def value(self):
        pass
```

---

## 📖 API 速查表

### abc 模块核心 API

```python
from abc import ABC, ABCMeta, abstractmethod, abstractproperty, abstractstaticmethod, abstractclassmethod, register

# ABC — 常用基类（等价于 metaclass=ABCMeta）
class MyBase(ABC):
    pass

# ABCMeta — 元类（更灵活）
class MyBase(metaclass=ABCMeta):
    pass

# @abstractmethod — 标记抽象方法
class Shape(ABC):
    @abstractmethod
    def area(self):
        """子类必须实现此方法"""
        pass

# register() — 虚拟子类注册
Shape.register(MyClass)

# issubclass() / isinstance() — 检查
print(issubclass(Circle, Shape))  # True
print(isinstance(circle, Shape))  # True
```

### 抽象属性

```python
class MyClass(ABC):
    @property
    @abstractmethod
    def value(self):
        pass

    @value.setter
    @abstractmethod
    def value(self, val):
        pass
```

### 抽象类方法和静态方法

```python
class Factory(ABC):
    @classmethod
    @abstractmethod
    def create(cls, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def validate(data):
        pass
```

---

## 📊 图解

### ABC 强制接口实现

```mermaid
classDiagram
    class Drawable {
        <<abstract>>
        +draw()
        +resize(factor)
    }
    class Circle {
        -radius: float
        +draw()
        +resize(factor)
        +area() float
    }
    class Square {
        -side: float
        +draw()
        +resize(factor)
        +area() float
    }
    class Triangle {
        -base: float
        -height: float
        +draw()
        +resize(factor)
        +area() float
    }

    Circle --|> Drawable
    Square --|> Drawable
    Triangle --|> Drawable
```

### ABC 检查流程

```mermaid
flowchart TD
    A[定义抽象基类] --> B[标记 @abstractmethod]
    B --> C[尝试实例化子类]
    C --> D{所有抽象方法已实现?}
    D -->|是| E[✅ 实例化成功]
    D -->|否| F[❌ TypeError]
    F --> G[报错：缺少 abstract method]
```

---

## 💻 实战代码案例

### 案例1：可迭代集合框架

```python
from abc import ABC, abstractmethod
from typing import Iterator, List, Optional


class Collection(ABC):
    """抽象集合基类 — 定义集合的通用接口"""

    @abstractmethod
    def add(self, item) -> None:
        """添加元素"""
        pass

    @abstractmethod
    def remove(self, item) -> bool:
        """移除元素，返回是否成功"""
        pass

    @abstractmethod
    def contains(self, item) -> bool:
        """检查是否包含元素"""
        pass

    @abstractmethod
    def size(self) -> int:
        """返回元素数量"""
        pass

    @abstractmethod
    def is_empty(self) -> bool:
        """是否为空"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空集合"""
        pass

    def __len__(self) -> int:
        return self.size()

    def __bool__(self) -> bool:
        return not self.is_empty()

    @abstractmethod
    def __iter__(self) -> Iterator:
        """支持迭代"""
        pass


class ListCollection(Collection):
    """基于列表的集合实现"""

    def __init__(self):
        self._items: List = []

    def add(self, item) -> None:
        self._items.append(item)

    def remove(self, item) -> bool:
        try:
            self._items.remove(item)
            return True
        except ValueError:
            return False

    def contains(self, item) -> bool:
        return item in self._items

    def size(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self) -> Iterator:
        return iter(self._items)

    def __repr__(self):
        return f"ListCollection({self._items})"


class UniqueCollection(Collection):
    """唯一集合（类似 Set）"""

    def __init__(self):
        self._items = {}  # 用 dict 保持插入顺序（Python 3.7+）

    def add(self, item) -> None:
        if item not in self._items:
            self._items[item] = True

    def remove(self, item) -> bool:
        if item in self._items:
            del self._items[item]
            return True
        return False

    def contains(self, item) -> bool:
        return item in self._items

    def size(self) -> int:
        return len(self._items)

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def clear(self) -> None:
        self._items.clear()

    def __iter__(self) -> Iterator:
        return iter(self._items.keys())

    def __repr__(self):
        return f"UniqueCollection({list(self._items.keys())})"


# 使用
print("=== 可迭代集合框架 ===")

# ListCollection
lc = ListCollection()
lc.add("apple")
lc.add("banana")
lc.add("cherry")
print(f"列表集合: {lc}")
print(f"大小: {len(lc)}")
print(f"包含 apple: {lc.contains('apple')}")

# UniqueCollection
uc = UniqueCollection()
uc.add("apple")
uc.add("apple")  # 重复添加
uc.add("banana")
print(f"唯一集合: {uc}")
print(f"大小: {len(uc)}")  # 应该是 2

# 迭代
print("\n迭代 ListCollection:")
for item in lc:
    print(f"  - {item}")
```

### 案例2：插件系统

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Type


class Plugin(ABC):
    """插件抽象基类 — 所有插件必须实现此接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """初始化插件"""
        pass

    @abstractmethod
    def execute(self, data: dict) -> dict:
        """执行插件逻辑"""
        pass

    def cleanup(self) -> None:
        """清理资源（可选实现）"""
        pass


class PluginManager:
    """插件管理器 — 注册和管理所有插件"""

    _plugins: Dict[str, Plugin] = {}
    _initialized: Dict[str, bool] = {}

    @classmethod
    def register(cls, plugin: Plugin) -> None:
        cls._plugins[plugin.name] = plugin
        cls._initialized[plugin.name] = False
        print(f"✅ 注册插件: {plugin.name} v{plugin.version}")

    @classmethod
    def initialize_all(cls) -> None:
        for name, plugin in cls._plugins.items():
            if not cls._initialized[name]:
                plugin.initialize()
                cls._initialized[name] = True
                print(f"🚀 初始化插件: {name}")

    @classmethod
    def execute_plugin(cls, name: str, data: dict) -> dict:
        if name not in cls._plugins:
            raise ValueError(f"插件不存在: {name}")
        if not cls._initialized[name]:
            raise RuntimeError(f"插件未初始化: {name}")
        return cls._plugins[name].execute(data)

    @classmethod
    def list_plugins(cls) -> List[str]:
        return list(cls._plugins.keys())


# === 具体插件实现 ===

class JsonFormatterPlugin(Plugin):
    @property
    def name(self) -> str:
        return "json_formatter"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        import json
        self._json = json

    def execute(self, data: dict) -> dict:
        formatted = self._json.dumps(data, ensure_ascii=False, indent=2)
        return {"output": formatted, "format": "json"}


class UppercasePlugin(Plugin):
    @property
    def name(self) -> str:
        return "uppercase"

    @property
    def version(self) -> str:
        return "1.0.0"

    def initialize(self) -> None:
        pass

    def execute(self, data: dict) -> dict:
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = value.upper()
            else:
                result[key] = value
        return result


# 使用
print("\n=== 插件系统 ===")

# 注册插件
PluginManager.register(JsonFormatterPlugin())
PluginManager.register(UppercasePlugin())

# 初始化
PluginManager.initialize_all()

# 执行
result = PluginManager.execute_plugin("uppercase", {"name": "hello", "value": 42})
print(f"\nuppercase 结果: {result}")

result = PluginManager.execute_plugin("json_formatter", {"users": ["张三", "李四"]})
print(f"\njson_formatter 结果:\n{result['output']}")

# 列出所有插件
print(f"\n已注册插件: {PluginManager.list_plugins()}")
```

### 案例3：抽象工厂模式

```python
from abc import ABC, abstractmethod
from typing import Optional


class Button(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

    @abstractmethod
    def on_click(self, handler) -> None:
        pass


class TextBox(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

    @abstractmethod
    def get_value(self) -> str:
        pass


class Checkbox(ABC):
    @abstractmethod
    def render(self) -> str:
        pass

    @abstractmethod
    def is_checked(self) -> bool:
        pass


class UIFactory(ABC):
    """抽象工厂 — 定义创建 UI 组件的接口"""

    @abstractmethod
    def create_button(self, label: str) -> Button:
        pass

    @abstractmethod
    def create_textbox(self, placeholder: str = "") -> TextBox:
        pass

    @abstractmethod
    def create_checkbox(self, label: str, checked: bool = False) -> Checkbox:
        pass


# === Web 实现 ===

class WebButton(Button):
    def __init__(self, label: str):
        self.label = label
        self._handler = None

    def render(self) -> str:
        return f'<button class="web-btn">{self.label}</button>'

    def on_click(self, handler) -> None:
        self._handler = handler


class WebTextBox(TextBox):
    def __init__(self, placeholder: str):
        self.placeholder = placeholder
        self._value = ""

    def render(self) -> str:
        return f'<input type="text" placeholder="{self.placeholder}" />'

    def get_value(self) -> str:
        return self._value


class WebCheckbox(Checkbox):
    def __init__(self, label: str, checked: bool):
        self.label = label
        self._checked = checked

    def render(self) -> str:
        checked = "checked" if self._checked else ""
        return f'<label><input type="checkbox" {checked} /> {self.label}</label>'

    def is_checked(self) -> bool:
        return self._checked


class WebUIFactory(UIFactory):
    def create_button(self, label: str) -> Button:
        return WebButton(label)

    def create_textbox(self, placeholder: str = "") -> TextBox:
        return WebTextBox(placeholder)

    def create_checkbox(self, label: str, checked: bool = False) -> Checkbox:
        return WebCheckbox(label, checked)


# === Desktop 实现（简化版） ===

class DesktopButton(Button):
    def __init__(self, label: str):
        self.label = label

    def render(self) -> str:
        return f"[Desktop Button: {self.label}]"

    def on_click(self, handler) -> None:
        pass


class DesktopTextBox(TextBox):
    def __init__(self, placeholder: str):
        self.placeholder = placeholder

    def render(self) -> str:
        return f"[Desktop TextBox: {self.placeholder}]"

    def get_value(self) -> str:
        return ""


class DesktopCheckbox(Checkbox):
    def __init__(self, label: str, checked: bool):
        self.label = label
        self._checked = checked

    def render(self) -> str:
        state = "X" if self._checked else " "
        return f"[Desktop Checkbox: [{state}] {self.label}]"

    def is_checked(self) -> bool:
        return self._checked


class DesktopUIFactory(UIFactory):
    def create_button(self, label: str) -> Button:
        return DesktopButton(label)

    def create_textbox(self, placeholder: str = "") -> TextBox:
        return DesktopTextBox(placeholder)

    def create_checkbox(self, label: str, checked: bool = False) -> Checkbox:
        return DesktopCheckbox(label, checked)


# 使用
print("\n=== 抽象工厂模式 ===")

# Web UI
factory = WebUIFactory()
button = factory.create_button("提交")
textbox = factory.create_textbox("请输入姓名")
checkbox = factory.create_checkbox("同意协议", True)

print("Web UI:")
print(f"  {button.render()}")
print(f"  {textbox.render()}")
print(f"  {checkbox.render()}")

# Desktop UI
factory = DesktopUIFactory()
button = factory.create_button("提交")
textbox = factory.create_textbox("请输入姓名")
checkbox = factory.create_checkbox("同意协议", True)

print("\nDesktop UI:")
print(f"  {button.render()}")
print(f"  {textbox.render()}")
print(f"  {checkbox.render()}")
```

---

## 🧠 思考题

1. **ABC 和 Protocol 的区别是什么？** Python 3.8 引入了 `typing.Protocol`（结构化子类型），它和 ABC 有什么异同？什么场景下用哪个？

**参考答案**

两者都用来描述「接口」，但判定子类型的思路相反：

- **ABC 是「名义子类型」（nominal subtyping）**：必须显式继承（或用 `register()` 注册）才算子类，并在**实例化时**强制检查抽象方法是否实现。它面向运行时，适合你自己掌控的类体系。
- **Protocol 是「结构子类型」（structural subtyping，即鸭子类型的静态版）**：只要一个类「恰好」拥有协议里声明的方法/属性，就被视为匹配，无需继承。它主要面向静态类型检查器（如 mypy），适合给第三方或互不相关的类做类型标注、解耦依赖。
- 加了 `@runtime_checkable` 的 Protocol 才能用 `isinstance()` 检查，但**只检查方法名是否存在**，不校验签名，也不强制实现。

选择建议：要「强制子类必须实现某些方法」用 ABC；要「给已有鸭子类型代码补类型提示」用 Protocol。小例子（已验证）：

```python
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

class Speaker(ABC):
    @abstractmethod
    def speak(self) -> str: ...

class Dog(Speaker):                 # 显式继承
    def speak(self) -> str: return "Woof"

@runtime_checkable
class SpeakerProto(Protocol):
    def speak(self) -> str: ...

class Robot:                        # 没继承任何基类
    def speak(self) -> str: return "Beep"

print(isinstance(Dog(), Speaker))         # True
print(isinstance(Robot(), Speaker))       # False（未继承）
print(isinstance(Robot(), SpeakerProto))  # True（结构匹配）
```

2. **为什么 `@abstractmethod` 必须在最内层装饰器？** 以下代码为什么不能交换顺序？
```python
@abstractmethod
@property
def value(self): ...

# vs

@property
@abstractmethod
def value(self): ...
```

**参考答案**

装饰器是**自下而上**（从最靠近函数的那层开始）应用的，关键在于 `abstractmethod` 要作用在「原始函数」上。

- **正确写法（`@property` 在外、`@abstractmethod` 在内）**：先执行 `abstractmethod(func)`，给函数打上 `__isabstractmethod__ = True` 标记；再执行 `property(func)`。`property` 会读取 `fget` 的这个标记，自动把自身的 `__isabstractmethod__` 也设为 `True`，于是 `ABCMeta` 能识别 `value` 是抽象成员，子类不实现就无法实例化。
- **交换顺序（`@abstractmethod` 在外、`@property` 在内）**：先得到 `property` 对象，再对它调用 `abstractmethod`。`abstractmethod` 试图写 `property_obj.__isabstractmethod__ = True`，但 `property` 对象不允许写这个属性，于是在**定义类的那一刻**就抛出 `AttributeError`。

验证（Python 3.12）：

```python
from abc import ABC, abstractmethod

class Good(ABC):
    @property
    @abstractmethod
    def value(self): ...

class GoodChild(Good):
    pass

try:
    GoodChild()
except TypeError as e:
    print(e)   # Can't instantiate abstract class GoodChild without an implementation for abstract method 'value'

try:
    class Bad(ABC):
        @abstractmethod
        @property
        def value(self): ...
except AttributeError as e:
    print(e)   # attribute '__isabstractmethod__' of 'property' objects is not writable
```

⚠️ 注意：错误顺序不是「静默失效」，而是定义类时直接报 `AttributeError`；同理 `@classmethod` / `@staticmethod` 的正确顺序也是它们在外、`@abstractmethod` 在内。

3. **register() 注册的虚拟子类有什么限制？** 为什么有时候 `isinstance()` 返回 True 但实际调用会报错？

**参考答案**

`register()` 只是「登记一个名义上的子类关系」，它**不检查、也不帮你实现任何方法**。

- 注册后 `issubclass()` / `isinstance()` 会返回 `True`，因为 `ABCMeta` 把该类记进了虚拟子类表。
- 但抽象方法是否实现完全没被校验。若被注册的类其实缺少某个方法，调用时照样抛 `AttributeError`——ABC 的「强制实现」保护对虚拟子类不生效。
- 此外，虚拟子类不会继承 ABC 里的任何具体方法/属性，也不触发 `__init_subclass__` 等继承钩子。

小例子（已验证）：

```python
from abc import ABC, abstractmethod

class Drawable(ABC):
    @abstractmethod
    def draw(self): ...

class Fake:          # 根本没实现 draw
    pass

Drawable.register(Fake)
print(isinstance(Fake(), Drawable))  # True
Fake().draw()                        # AttributeError: 'Fake' object has no attribute 'draw'
```

💡 提示：`register()` 适合「让已有、无法修改继承关系的类被识别为某接口」，但要自己保证它真的实现了接口；需要强制约束时仍应使用真正的继承。

4. **如何用 ABC 实现 Mixin？** 抽象 Mixin 有什么好处和风险？

**参考答案**

Mixin 是一种「只混入部分能力、不单独实例化」的类。用 ABC 做 Mixin，可以一边提供现成的通用方法，一边用抽象方法规定「宿主类必须补齐的部分」。

做法：让 Mixin 继承 `ABC`，把「依赖宿主提供的能力」声明为 `@abstractmethod`，把「可复用的通用逻辑」写成普通方法；宿主类多继承这个 Mixin 并实现抽象方法即可。

- **好处**：通用逻辑只写一次、可自由组合；抽象方法把「隐含依赖」变成显式契约，宿主忘了实现会在实例化时报错，而不是运行到一半才崩。
- **风险**：多继承让 MRO（方法解析顺序）变复杂，多个 Mixin 若有同名方法/属性容易冲突；Mixin 不应自带 `__init__` 或独立状态，否则协作初始化会很棘手。

小例子（已验证）：

```python
import json
from abc import ABC, abstractmethod

class JSONSerializableMixin(ABC):
    @abstractmethod
    def to_dict(self) -> dict: ...        # 依赖宿主实现

    def to_json(self) -> str:             # 可复用逻辑
        return json.dumps(self.to_dict(), ensure_ascii=False)

class User(JSONSerializableMixin):
    def __init__(self, name):
        self.name = name
    def to_dict(self):
        return {"name": self.name}

print(User("张三").to_json())   # {"name": "张三"}
```

5. **Python 标准库中哪些模块使用了 ABC？** 查看 `collections.abc`、`io`、`os` 等模块，找出使用 ABC 的例子。

**参考答案**

标准库大量使用 ABC，最集中的是 `collections.abc`，它把「容器协议」拆成一组抽象基类：

- **基础协议**：`Iterable`（可迭代）、`Iterator`（迭代器）、`Sized`（有长度）、`Container`（支持 `in`）、`Hashable`（可哈希）、`Callable`（可调用）。
- **容器体系**：`Sequence` / `MutableSequence`（如 `list`）、`Mapping` / `MutableMapping`（如 `dict`）、`Set` / `MutableSet`（如 `set`）。
- **其他模块**：`io.IOBase` / `RawIOBase` / `BufferedIOBase` / `TextIOBase` 是文件流的 ABC；`os.PathLike` 是「路径对象」的 ABC（抽象方法 `__fspath__`）；`numbers` 模块的 `Number` / `Complex` / `Real` / `Rational` / `Integral` 是数值塔 ABC。

小例子（已验证）：

```python
from collections.abc import Iterable, Sized, Mapping, Sequence
import io, os

print(isinstance([1, 2], Iterable))       # True
print(isinstance([1, 2], Sequence))       # True
print(isinstance({}, Mapping))            # True
print(isinstance("abc", Sized))           # True
print(issubclass(io.StringIO, io.IOBase)) # True
print(os.PathLike.__abstractmethods__)    # frozenset({'__fspath__'})
```

💡 提示：`isinstance(x, Iterable)` 只检查有没有 `__iter__`，并不保证迭代一定成功；判断「是不是迭代器」要用 `Iterator`（需同时有 `__iter__` 和 `__next__`）。

---

## 📋 今日小结

| 概念 | 说明 |
|------|------|
| **ABC** | 抽象基类，不能直接实例化，强制子类实现接口 |
| **@abstractmethod** | 标记抽象方法，子类必须实现 |
| **ABCMeta** | ABC 的底层元类，负责检查抽象方法 |
| **register()** | 注册虚拟子类，无需继承也能被识别 |
| **接口契约** | ABC 确保子类实现特定方法，提供类型安全 |
