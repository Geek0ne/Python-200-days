# Day 048 — 混入（Mixin）练习清单

## ✅ 今日完成清单

- [ ] 理解 Mixin 的定义和设计目的
- [ ] 掌握 MRO（方法解析顺序）的查找机制
- [ ] 理解协作式多重继承中 `super()` 的作用
- [ ] 知道 Mixin 的命名约定和最佳实践
- [ ] 能够避免 Mixin 中的常见陷阱

---

## 📝 基础练习题

### 练习1：实现 `PrintableMixin`

实现一个 `PrintableMixin`，为任何类添加漂亮的打印能力：

```python
class PrintableMixin:
    def pretty_print(self):
        """打印对象的属性，格式如：
        ClassName {
            attr1 = value1
            attr2 = value2
        }
        """
        pass

class Person(PrintableMixin):
    def __init__(self, name, age):
        self.name = name
        self.age = age

p = Person("张三", 25)
p.pretty_print()
# 输出:
# Person {
#     name = 张三
#     age = 25
# }
```

### 练习2：实现 `ComparableMixin`

实现一个 `ComparableMixin`，让对象支持 `>`、`>=`、`<=` 运算符（提示：使用 `functools.total_ordering`）。

### 练习3：实现 `ReprMixin`

实现一个 `ReprMixin`，自动生成 `__repr__` 方法，显示类名和所有非私有属性。

---

## 🔥 进阶挑战题

### 挑战1：Mixin 链式调用

实现以下 Mixin 并确保它们可以链式调用：

```python
class ChainableMixin:
    def chain(self):
        """返回 self，支持链式调用"""
        pass

class Builder(ChainableMixin):
    def set_name(self, name): ...
    def set_age(self, age): ...
    def build(self): ...

builder = Builder()
user = builder.set_name("张三").set_age(25).build()
```

### 挑战2：Mixin 自动注册

实现一个 `RegistryMixin`，使用类变量自动注册所有子类：

```python
class RegistryMixin:
    _registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._registry[cls.__name__] = cls

class ModelA(RegistryMixin): pass
class ModelB(RegistryMixin): pass

print(RegistryMixin._registry)  # {'ModelA': <class 'ModelA'>, ...}
```

### 挑战3：Mixin 条件执行

实现一个 `ConditionalMixin`，只有在满足特定条件时才执行 Mixin 的方法：

```python
class ConditionalMixin:
    def conditional_method(self, condition_func):
        """根据条件决定是否执行方法"""
        pass

class Feature(ConditionalMixin):
    def expensive_operation(self):
        print("执行耗时操作")
        return 42

obj = Feature()
# 只有条件为 True 时才执行
result = obj.conditional_method(lambda: True)(obj.expensive_operation)
```

---

## 📚 参考资源

- Python 官方文档：https://docs.python.org/3/tutorial/classes.html#multiple-instances
- 《Python Cookbook》第8章：类与对象
- MRO 详解：https://www.python.org/download/releases/2.3/mro/
