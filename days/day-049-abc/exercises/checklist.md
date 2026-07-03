# Day 049 — 抽象基类（ABC）练习清单

## ✅ 今日完成清单

- [ ] 理解 ABC 的定义和设计目的
- [ ] 掌握 `@abstractmethod` 的使用方法
- [ ] 理解 `ABCMeta` 元类的工作原理
- [ ] 掌握 `register()` 注册虚拟子类
- [ ] 知道 ABC 与 Protocol 的区别

---

## 📝 基础练习题

### 练习1：实现 `Container` 抽象基类

```python
from abc import ABC, abstractmethod

class Container(ABC):
    """容器抽象基类"""

    @abstractmethod
    def add(self, item) -> None:
        pass

    @abstractmethod
    def remove(self, item) -> bool:
        pass

    @abstractmethod
    def contains(self, item) -> bool:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

# 实现一个 Bag（允许重复的集合）
class Bag(Container):
    pass
```

### 练习2：实现工厂方法

```python
from abc import ABC, abstractmethod

class AnimalFactory(ABC):
    @abstractmethod
    def create(self, name: str) -> 'Animal':
        pass

class DogFactory(AnimalFactory):
    def create(self, name):
        return Dog(name)

class CatFactory(AnimalFactory):
    def create(self, name):
        return Cat(name)
```

### 练习3：使用 `register()` 注册遗留类

将一个现有的 `list` 子类注册为自定义 `Sequence` 的虚拟子类。

---

## 🔥 进阶挑战题

### 挑战1：插件加载器

实现一个基于 ABC 的插件系统，支持：
- 插件注册
- 插件初始化
- 插件执行
- 插件卸载

### 挑战2：ORM 模型基类

```python
class Model(ABC):
    """ORM 模型基类"""
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = cls

    @abstractmethod
    def save(self) -> None: ...

    @abstractmethod
    def delete(self) -> None: ...

    @classmethod
    def get(cls, id):
        pass
```

### 挑战3：抽象 Mixin

实现一个 `SerializableABC`，既是 ABC 又是 Mixin，子类必须实现序列化方法但可以选择性继承其他能力。

---

## 📚 参考资源

- Python 官方文档：https://docs.python.org/3/library/abc.html
- PEP 3119：Abstract Base Classes
- typing.Protocol 文档：https://docs.python.org/3/library/typing.html#typing.Protocol
