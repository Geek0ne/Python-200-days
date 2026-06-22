# Day 034 — 多态与鸭子类型

> 深入理解 Python 多态机制、鸭子类型哲学与抽象基类，实战插件系统

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 多态概念 | ⭐⭐ | 多态的定义、优势、Python 中的实现方式 |
| 鸭子类型 | ⭐⭐⭐ | 「如果它走起来像鸭子…」动态类型的核心哲学 |
| EAFP 风格 | ⭐⭐ | 「请求原谅比请求许可更容易」编程范式 |
| 抽象基类 (ABC) | ⭐⭐⭐ | 虚拟子类、注册机制、`@abstractmethod` |
| 实战：插件系统 | ⭐⭐⭐⭐ | 动态加载、插件注册、热插拔架构 |

---

## 一、多态（Polymorphism）

### 1.1 多态的概念

**多态** 是面向对象编程的三大特征之一（封装、继承、多态），指 **同一操作作用于不同的对象上，可以产生不同的行为**。

> 一句话概括：**同一个接口，不同的实现**

```
      ┌─────────────────┐
      │    Animal       │  ← 基类（抽象接口）
      │  speak()        │
      └────────┬────────┘
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
  ┌────────┐┌──────┐┌──────┐
  │  Dog   ││ Cat  ││ Duck │  ← 子类（不同实现）
  │ bark() ││ meow()││quack │
  └────────┘└──────┘└──────┘

  统一调用: animal.speak()
  Dog   → "汪汪!"
  Cat   → "喵喵~"
  Duck  → "嘎嘎!"
```

### 1.2 静态多态 vs 动态多态

| 特性 | 静态多态（编译时） | 动态多态（运行时） |
|------|------------------|------------------|
| 实现方式 | 函数重载、模板 | 方法重写、虚函数 |
| 绑定时机 | 编译期 | 运行期 |
| Python 支持 | ❌（没有重载） | ✅（动态绑定） |
| 代表语言 | C++/Java | Python/Ruby |

Python 中的多态都是 **动态多态**——方法调用在运行时才确定具体调用哪个类的版本。

### 1.3 Python 中的多态

**方式一：继承 + 方法重写（传统多态）**

```python
class Animal:
    def speak(self):
        raise NotImplementedError

class Dog(Animal):
    def speak(self):
        return "汪汪!"

class Cat(Animal):
    def speak(self):
        return "喵喵~"

# 多态调用
animals = [Dog(), Cat()]
for animal in animals:
    print(animal.speak())  # 同一接口，不同行为
```

**方式二：鸭子类型（Python 式多态）**

```python
class Dog:
    def speak(self): return "汪汪!"

class Cat:
    def speak(self): return "喵喵~"

class Car:
    def speak(self): return "滴滴!"  # 没有继承关系也一样工作

def make_it_speak(thing):
    print(thing.speak())  # 不关心类型，只关心有没有 speak 方法

make_it_speak(Dog())  # 汪汪!
make_it_speak(Car())  # 滴滴!  —— 没有继承也能用
```

---

## 二、鸭子类型（Duck Typing）

### 2.1 原理：「鸭子测试」

> 「当看到一只鸟，它走起来像鸭子、游泳像鸭子、叫起来像鸭子，那么这只鸟就可以被称为鸭子。」

```python
def process(iterable):
    """这个函数只要求 iterable 支持迭代，不关心它的具体类型"""
    for item in iterable:
        print(item)

process([1, 2, 3])          # list
process("hello")            # str
process({1, 2, 3})          # set
process(range(5))           # range
# 只要是可迭代的，都能工作 —— 这就是鸭子类型
```

### 2.2 鸭子类型的优缺点

| 优点 | 缺点 |
|------|------|
| 代码更灵活、复用性更高 | 错误发现较晚（运行时才暴露） |
| 不需要复杂的继承体系 | 文档/类型提示更重要 |
| 更符合 Python 的动态哲学 | 调试时可能难以追踪 |
| 减少样板代码 | IDE 自动补全支持较差 |

### 2.3 鸭子类型 vs 静态类型

```
鸭子类型:
  function quack(duck):
      duck.quack()      # 🦆 只要会叫，就是鸭子

静态类型 (Java):
  void quack(Duck duck):
      duck.quack()      # 🦆 必须是 Duck 类型

Go 接口:
  type Quacker interface {
      Quack()
  }
  func quack(q Quacker) {
      q.Quack()         # 🦆 只要实现了 Quacker 接口
  }
```

---

## 三、EAFP 风格

### 3.1 什么是 EAFP

**EAFP**（Easier to Ask for Forgiveness than Permission）是 Python 社区的惯用风格：

> **请求原谅比请求许可更容易**

```python
# ❌ LBYL (Look Before You Leap) — 先检查再操作
def safe_divide_lbyl(a, b):
    if not isinstance(a, (int, float)):
        return None
    if not isinstance(b, (int, float)):
        return None
    if b == 0:
        return None
    return a / b

# ✅ EAFP — 尝试做，出错再处理
def safe_divide_eafp(a, b):
    try:
        return a / b
    except (TypeError, ZeroDivisionError):
        return None
```

### 3.2 LBYL vs EAFP

```
LBYL (Look Before You Leap)
═════════════════════════════
      ┌─────────┐
      │  检查    │ ← 先判断「能不能做」
      └────┬────┘
           ▼
      ┌─────────┐
      │  操作    │ ← 安全了再操作
      └─────────┘
    问题：条件判断可能过时
    （检查完到执行之间，状态可能改变）

EAFP (Easier to Ask for Forgiveness)
════════════════════════════════════
      ┌─────────┐
      │  操作    │ ← 直接做
      └────┬────┘
           ▼
       成功？     ← 成功了就结束
      ┌──┴──┐
      │  是  │ 否
      │     ▼
      │  ┌─────────┐
      │  │  处理异常 │ ← 出错了再处理
      │  └─────────┘
      ▼
     结束
```

### 3.3 Python 中的 EAFP 场景

```python
# 🔑 字典访问
# LBYL
if 'key' in d:
    value = d['key']

# EAFP
try:
    value = d['key']
except KeyError:
    value = None

# 更 Pythonic: d.get('key', None)


# 📁 文件操作
# LBYL
import os
if os.path.exists('data.txt'):
    with open('data.txt') as f:
        data = f.read()

# EAFP
try:
    with open('data.txt') as f:
        data = f.read()
except FileNotFoundError:
    data = ''


# 🏷️ 属性访问
# LBYL
if hasattr(obj, 'name'):
    name = obj.name

# EAFP
try:
    name = obj.name
except AttributeError:
    name = None

# 更 Pythonic: getattr(obj, 'name', None)
```

---

## 四、抽象基类（ABC）

### 4.1 为什么需要 ABC

鸭子类型虽然灵活，但有时我们需要 **确保某个类一定实现了特定的方法**。抽象基类（Abstract Base Class）提供了这种保障。

```
           ┌─────────────────────────┐
           │    abc.ABC (元类)        │ ← Python 的抽象基类机制
           │  @abstractmethod         │
           └────────────┬─────────────┘
                        │ 继承
           ┌────────────┴─────────────┐
           │    Shape (抽象基类)        │ ← 定义接口契约
           │    @abstractmethod        │
           │    area()                  │
           │    perimeter()             │
           └────────────┬─────────────┘
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
        ┌─────────┐ ┌───────┐ ┌───────┐
        │  Circle  │ │Square │ │Triangle│ ← 具体实现
        │ area()   │ │area() │ │area()  │
        │peri()    │ │peri() │ │peri()  │
        └─────────┘ └───────┘ └───────┘
```

### 4.2 ABC 基本用法

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    """形状抽象基类"""

    @abstractmethod
    def area(self) -> float:
        """计算面积（子类必须实现）"""
        pass

    @abstractmethod
    def perimeter(self) -> float:
        """计算周长（子类必须实现）"""
        pass

# ❌ 不能直接实例化抽象类
# s = Shape()  # TypeError: Can't instantiate abstract class Shape

# ✅ 子类必须实现所有抽象方法
class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius

    def area(self) -> float:
        return 3.14159 * self.radius ** 2

    def perimeter(self) -> float:
        return 2 * 3.14159 * self.radius

# ❌ 缺少实现
# class Incomplete(Shape):   # TypeError: Can't instantiate
#     def area(self): return 0
```

### 4.3 ABC 的注册机制

ABC 支持 **虚拟子类**——一个类不需要显式继承 ABC，可以通过注册「假装」自己是子类：

```python
from abc import ABC, abstractmethod

class Sized(ABC):
    """自定义的尺寸接口"""
    @abstractmethod
    def size(self):
        pass

# 虚拟注册 —— dict 没有继承 Sized，但可以注册为「虚拟子类」
Sized.register(dict)
print(isinstance({}, Sized))    # True
print(issubclass(dict, Sized))  # True

# 自定义类注册
@Sized.register
class MyDict:
    def size(self):
        return len(self.__dict__)

print(isinstance(MyDict(), Sized))  # True
```

### 4.4 Python 内置的 ABC

Python 标准库提供了大量内置 ABC：

| ABC | 所在模块 | 需要实现的方法 | 用途 |
|-----|---------|---------------|------|
| `Iterable` | `collections.abc` | `__iter__()` | 可迭代对象 |
| `Iterator` | `collections.abc` | `__next__()` + `__iter__()` | 迭代器 |
| `Sequence` | `collections.abc` | `__getitem__()` + `__len__()` | 序列类型 |
| `MutableSequence` | `collections.abc` | Sequence + `__setitem__()` + `__delitem__()` | 可变序列 |
| `Mapping` | `collections.abc` | `__getitem__()` + `__len__()` + `__iter__()` | 映射类型 |
| `Set` | `collections.abc` | `__contains__()` + `__iter__()` + `__len__()` | 集合类型 |
| `Callable` | `collections.abc` | `__call__()` | 可调用对象 |

```python
from collections.abc import Sequence, MutableSequence, Mapping

# isinstance 检查不再是类型名比较，而是行为检查
def process(data):
    if isinstance(data, Sequence):
        print(f"序列类型，长度: {len(data)}")
    elif isinstance(data, Mapping):
        print(f"映射类型，键数: {len(data)}")

process([1, 2, 3])   # 序列类型，长度: 3
process("hello")     # 序列类型，长度: 5 (字符串也是序列!)
process({"a": 1})    # 映射类型，键数: 1
```

### 4.5 实现自己的 ABC：Container 示例

```python
from abc import ABC, abstractmethod
from collections.abc import Container

class MyContainer(Container):
    """自定义容器"""
    def __init__(self, items):
        self._items = items

    def __contains__(self, item):
        return item in self._items

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

# 自动获得 isinstance 支持
c = MyContainer([1, 2, 3])
print(isinstance(c, Container))  # True
print(2 in c)                    # True
```

---

## 五、实战：插件系统

### 5.1 系统架构

```
                    ┌──────────────────┐
                    │    PluginBase    │ ← 插件抽象基类
                    │  initialize()    │
                    │  execute()       │
                    │  cleanup()       │
                    └────────┬─────────┘
                             │ 继承
           ┌─────────────────┼──────────────────┐
           ▼                 ▼                  ▼
    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
    │ TextPlugin   │  │ ImagePlugin  │  │ AudioPlugin  │
    │ 文本处理      │  │ 图片处理      │  │ 音频处理      │
    └─────────────┘  └──────────────┘  └──────────────┘
           │                 │                  │
           └─────────────────┼──────────────────┘
                             ▼
                    ┌──────────────────┐
                    │   PluginManager  │ ← 插件管理器
                    │  register()      │
                    │  load_plugin()   │
                    │  execute_all()   │
                    └──────────────────┘
```

### 5.2 核心实现

```python
from abc import ABC, abstractmethod
import importlib
import pkgutil
from typing import Dict, List, Optional


class PluginBase(ABC):
    """插件抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """插件初始化"""
        pass

    @abstractmethod
    def execute(self, data: str) -> str:
        """插件核心功能"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """插件清理"""
        pass


class PluginManager:
    """插件管理器"""

    def __init__(self):
        self._plugins: Dict[str, PluginBase] = {}

    def register(self, plugin: PluginBase) -> None:
        """注册插件"""
        if not isinstance(plugin, PluginBase):
            raise TypeError(f"{plugin.__class__.__name__} 不是有效的插件")
        self._plugins[plugin.name] = plugin
        plugin.initialize()

    def unregister(self, name: str) -> None:
        """卸载插件"""
        if name in self._plugins:
            self._plugins[name].cleanup()
            del self._plugins[name]

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """获取插件"""
        return self._plugins.get(name)

    def execute_all(self, data: str) -> Dict[str, str]:
        """执行所有插件"""
        results = {}
        for name, plugin in self._plugins.items():
            try:
                results[name] = plugin.execute(data)
            except Exception as e:
                results[name] = f"错误: {e}"
        return results

    def list_plugins(self) -> List[str]:
        """列出所有已注册插件"""
        return list(self._plugins.keys())

    def get_plugin_count(self) -> int:
        return len(self._plugins)


# 具体插件实现
class UpperCasePlugin(PluginBase):
    """大写转换插件"""

    @property
    def name(self) -> str:
        return "uppercase"

    def initialize(self) -> None:
        print(f"[{self.name}] 插件已加载")

    def execute(self, data: str) -> str:
        return data.upper()

    def cleanup(self) -> None:
        print(f"[{self.name}] 插件已卸载")


class ReversePlugin(PluginBase):
    """反转字符串插件"""

    @property
    def name(self) -> str:
        return "reverse"

    def initialize(self) -> None:
        print(f"[{self.name}] 插件已加载")

    def execute(self, data: str) -> str:
        return data[::-1]

    def cleanup(self) -> None:
        print(f"[{self.name}] 插件已卸载")


class WordCountPlugin(PluginBase):
    """词频统计插件"""

    @property
    def name(self) -> str:
        return "wordcount"

    def initialize(self) -> None:
        self._count = 0
        print(f"[{self.name}] 插件已加载")

    def execute(self, data: str) -> str:
        words = data.split()
        self._count += len(words)
        return f"总词数: {sum(1 for _ in data.split())}，累计: {self._count}"

    def cleanup(self) -> None:
        print(f"[{self.name}] 插件已卸载，累计处理词数: {self._count}")


# 使用示例
if __name__ == "__main__":
    manager = PluginManager()

    manager.register(UpperCasePlugin())
    manager.register(ReversePlugin())
    manager.register(WordCountPlugin())

    print("已注册插件:", manager.list_plugins())

    text = "Hello Python World"
    results = manager.execute_all(text)
    for name, result in results.items():
        print(f"  [{name}]: {result}")

    manager.unregister("reverse")
    print("\n卸载 reverse 后:", manager.list_plugins())

    manager.execute_all("Another test")
```

---

## 六、思考题

1. **鸭子类型 vs 接口**：Python 的鸭子类型和 Java 的 Interface 有什么区别？各自有何优劣？

2. **EAFP vs LBYL**：在什么场景下 LBYL 比 EAFP 更合适？写出一个 LBYL 更好的例子。

3. **ABC 设计**：假设你要设计一个「缓存系统」，要求所有缓存实现（内存、Redis、文件）都提供 `get(key)`、`set(key, value, ttl)`、`delete(key)` 方法。请用 ABC 设计这个接口。

4. **虚拟子类**：Python 的 `register()` 机制有什么用？在什么场景下会用到虚拟子类？

5. **插件系统设计**：如何设计一个支持「优先级」的插件系统（高优先级插件先执行）？如果插件之间有依赖关系（插件 B 需要插件 A 先执行），该如何处理？

---

## 📝 本章小结

```
✅ 多态 —— 同一接口，多种实现
✅ 鸭子类型 —— 不关心类型，只关心行为
✅ EAFP 风格 —— 先做再说，错了再处理
✅ ABC —— 定义接口契约，约束子类行为
✅ 插件系统 —— 扩展性设计的经典模式
```
