# Day 046 — 元类（Metaclass）

> **Phase 4 — 高阶特性** | Day 046/200 | 实战日

## 📌 今日目标

理解 Python 中"一切皆对象"的终极体现——元类。掌握 `type()` 的本质、动态创建类的方法，以及如何用自定义元类实现 ORM 字段验证。

---

## 一、类也是对象

### 1.1 核心概念

在 Python 中，**一切皆对象**。整数是对象，字符串是对象，函数是对象——**类本身也是对象**。

```python
class Dog:
    pass

# Dog 是一个类，但它同时也是一个对象
print(type(Dog))  # <class 'type'>
print(isinstance(Dog, type))  # True
```

这意味着：
- 类可以赋值给变量
- 类可以作为参数传递
- 类可以动态创建
- 类有类型——它的类型就是 `type`

### 1.2 为什么类是对象？

Python 的设计哲学是**一致性**。如果函数可以作为对象传递（回调机制），那么类也应该是对象。这使得：

1. **元编程**成为可能——你可以编写"生成类的代码"
2. **框架设计**更加灵活——Django ORM、SQLAlchemy 都依赖此机制
3. **装饰器**可以应用于类——`@dataclass`、`@singleton` 等

### 1.3 对象的层级关系

```
普通对象（实例）  →  类（Class）  →  元类（Metaclass）
    Dog()          class Dog:       type
    实例              类定义        创建类的"类"
```

每个对象都有一个 `type`：
- `type(dog_instance)` → `<class 'Dog'>`
- `type(Dog)` → `<class 'type'>`
- `type(type)` → `<class 'type'>`（`type` 是它自己的实例！）

---

## 二、type() 动态创建类

### 2.1 type() 的两种用法

**用法一：查询对象类型**

```python
x = 42
print(type(x))  # <class 'int'>
```

**用法二：动态创建类**

```python
# type(类名, 基类元组, 属性字典)
MyClass = type('MyClass', (object,), {'greet': lambda self: 'Hello!'})
obj = MyClass()
print(obj.greet())  # Hello!
```

`type()` 三参数版本等价于：

```python
class MyClass:
    def greet(self):
        return 'Hello!'
```

### 2.2 type() 的完整参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `name` | 类名（字符串） | `'Dog'` |
| `bases` | 基类元组，没有就写 `(object,)` | `(Animal,)` |
| `attrs` | 类属性字典 | `{'legs': 4}` |

### 2.3 动态创建类的实际意义

```python
# 根据配置文件动态生成类
config = {
    'name': 'User',
    'fields': ['name', 'email', 'age']
}

# 动态创建一个包含验证方法的类
def make_validator(fields):
    attrs = {f: None for f in fields}
    attrs['validate'] = lambda self: all(getattr(self, f) is not None for f in fields)
    return type('Model', (), attrs)

Model = make_validator(config['fields'])
user = Model()
user.name = 'Alice'
user.email = 'alice@example.com'
user.age = 30
print(user.validate())  # True
```

---

## 三、自定义元类

### 3.1 元类是什么？

元类就是**创建类的类**。当你写 `class Dog:` 时，Python 会：

1. 执行 `type()` 来创建 `Dog` 类对象
2. 但如果有自定义元类，Python 会用**自定义元类**来创建

### 3.2 编写第一个自定义元类

```python
class UpperAttrMetaclass(type):
    """自动将类的所有属性名转为大写"""
    
    def __new__(mcs, name, bases, attrs):
        uppercase_attrs = {}
        for key, value in attrs.items():
            if not key.startswith('__'):
                uppercase_attrs[key.upper()] = value
            else:
                uppercase_attrs[key] = value
        return super().__new__(mcs, name, bases, uppercase_attrs)

class MyClass(metaclass=UpperAttrMetaclass):
    name = 'test'

print(dir(MyClass))  # 包含 NAME 而不是 name
```

### 3.3 元类的关键方法

| 方法 | 何时调用 | 用途 |
|------|---------|------|
| `__new__(mcs, name, bases, attrs)` | 创建类时 | 控制类的创建过程 |
| `__init__(cls, name, bases, attrs)` | 创建类后 | 初始化类 |
| `__call__(cls, *args, **kwargs)` | 创建实例时 | 控制实例化过程 |

### 3.4 元类 vs 装饰器

| 特性 | 元类 | 装饰器 |
|------|------|--------|
| 作用范围 | 影响所有子类 | 仅影响被装饰的类 |
| 复杂度 | 高 | 低 |
| 可读性 | 差 | 好 |
| 适用场景 | 框架、库设计 | 简单的类修改 |

**经验法则**：能用装饰器解决的，就不用元类。

---

## 四、实战：ORM 字段验证

### 4.1 需求分析

仿照 Django ORM，实现一个简单的字段验证系统：
- 定义字段类型（StringField、IntegerField 等）
- 自动收集字段定义
- 创建实例时自动验证

### 4.2 实现方案

使用元类实现：

```python
class Field:
    def __init__(self, required=True, max_length=None):
        self.required = required
        self.max_length = max_length
        self.name = None

class StringField(Field):
    pass

class IntegerField(Field):
    pass

class ModelMeta(type):
    def __new__(mcs, name, bases, attrs):
        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                value.name = key
                fields[key] = value
        attrs['_fields'] = fields
        return super().__new__(mcs, name, bases, attrs)

class Model(metaclass=ModelMeta):
    def __init__(self, **kwargs):
        for name, field in self._fields.items():
            if field.required and name not in kwargs:
                raise ValueError(f"缺少必填字段: {name}")
            setattr(self, name, kwargs.get(name))
    
    def validate(self):
        for name, field in self._fields.items():
            value = getattr(self, name, None)
            if value is not None and field.max_length:
                if len(str(value)) > field.max_length:
                    raise ValueError(f"{name} 超出最大长度 {field.max_length}")

# 使用
class User(Model):
    name = StringField(required=True, max_length=50)
    age = IntegerField(required=True)

user = User(name='Alice', age=30)
user.validate()  # 通过
```

---

## 五、API 速查表

### type() 函数

```python
# 查询类型
type(obj)                    # 返回 obj 的类型
type(obj) is SomeClass       # 判断类型

# 动态创建类
MyClass = type('MyClass', (BaseClass,), {'attr': value})
```

### 自定义元类

```python
class Meta(type):
    def __new__(mcs, name, bases, attrs):
        # mcs: 元类自身
        # name: 类名
        # bases: 基类元组
        # attrs: 类属性字典
        return super().__new__(mcs, name, bases, attrs)
    
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
    
    def __call__(cls, *args, **kwargs):
        return super().__call__(*args, **kwargs)

# 使用
class MyClass(metaclass=Meta):
    pass
```

### hasattr / getattr 动态操作

```python
# 元类常与动态属性操作配合
hasattr(cls, 'some_attr')       # 检查属性是否存在
getattr(cls, 'some_attr', None) # 安全获取属性
setattr(cls, 'new_attr', value) # 动态设置属性
```

---

## 六、原理解析图

### 元类调用链

```
用户代码: class Dog(Animal):
              legs = 4
              def bark(self): ...

                    ↓ Python 解释器

type('Dog', (Animal,), {'legs': 4, 'bark': <function>})
                    ↓
              type.__call__()
                    ↓
              type.__new__()  ← 创建 Dog 类对象
                    ↓
              type.__init__() ← 初始化 Dog 类
                    ↓
              Dog 类对象诞生 🎉
```

### 自定义元类调用链

```
用户代码: class Dog(Animal, metaclass=Meta):
              legs = 4
              def bark(self): ...

                    ↓ Python 解释器

Meta.__new__(Meta, 'Dog', (Animal,), {'legs': 4, 'bark': ...})
                    ↓
              Meta 创建 Dog 类（可以修改 attrs）
                    ↓
              Meta.__init__(Dog, ...)
                    ↓
              Dog 类对象诞生 🎉
```

---

## 七、实战代码案例

### 案例 1：自动注册类到注册表

```python
registry = {}

class PluginMeta(type):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)
        if bases:  # 不注册基类本身
            registry[name] = cls
        return cls

class Plugin(metaclass=PluginMeta):
    pass

class MathPlugin(Plugin):
    def run(self):
        return 'Math running'

class DataPlugin(Plugin):
    def run(self):
        return 'Data running'

print(registry)
# {'MathPlugin': <class 'MathPlugin'>, 'DataPlugin': <class 'DataPlugin'>}
```

### 案例 2：单例模式

```python
class SingletonMeta(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Database(metaclass=SingletonMeta):
    def __init__(self):
        self.connection = 'Connected'

db1 = Database()
db2 = Database()
print(db1 is db2)  # True
```

### 案例 3：自动添加 __repr__

```python
class AutoReprMeta(type):
    def __new__(mcs, name, bases, attrs):
        fields = [k for k, v in attrs.items() 
                  if not k.startswith('_') and not callable(v)]
        
        def __repr__(self):
            values = ', '.join(f'{f}={getattr(self, f)!r}' for f in fields)
            return f'{name}({values})'
        
        attrs['__repr__'] = __repr__
        return super().__new__(mcs, name, bases, attrs)

class Point(metaclass=AutoReprMeta):
    x = 0
    y = 0

p = Point()
p.x = 3
p.y = 4
print(p)  # Point(x=3, y=4)
```

---

## 八、思考题

1. **为什么 `type(type) is type`？** 这意味着什么？

**参考答案**

因为 **`type` 是它自己的实例**——这是 Python 对象体系刻意设计的「终点」。

 normally 对象层级是「实例 → 类 → 元类」：`type(狗实例)` 是 `Dog`，`type(Dog)` 是 `type`。如果继续追问「type 的类型是谁」，再往上造一个「元元类」就会无穷无尽。Python 让这条链在 `type` 处**自我闭环**：`type(type) is type`，于是任何对象的类型追溯最终都停在 `type`，不会无限上升。

这意味着：

- **`type` 是「实例化链」的根**：所有类（包括 `type` 自己）都是由 `type` 或其子类创建的。
- **要区分两条链**：「实例化链」（谁创建了谁，根是 `type`）和「继承链」（谁是谁的父类，根是 `object`）。`type` 本身也继承自 `object`（`type.__bases__ == (object,)`），而 `object` 的类型又是 `type`（`type(object) is type`），两者互相依存、各自闭环。

```python
print(type(type))            # <class 'type'>
print(type(object))          # <class 'type'>
print(type.__bases__)        # (<class 'object'>,)
print(object.__bases__)      # ()  —— object 没有父类，是继承链的根
```

💡 提示：可以这样记——`object` 是「所有类的祖先」（继承层面），`type` 是「所有类的制造者」（实例化层面），而 `type` 自己制造了自己。

2. **元类的 `__new__` 和 `__init__` 有什么区别？** 在元类中，`__new__` 不能直接调用 `super().__init__()`，为什么？

**参考答案**

两者是「创建对象」的两个阶段，分工不同（对元类而言，被创建的对象就是「类」）：

- **`__new__(mcs, name, bases, attrs)`**：负责**创建并返回**类对象，是「分配/构造」阶段。它拿到的是类名、基类、属性字典这些「原材料」，调用 `super().__new__(...)` 真正造出类，然后 `return` 它。想修改类结构（增删属性、收集字段）就在这里做。
- **`__init__(cls, name, bases, attrs)`**：负责**初始化已经创建好的**类对象，是「装修」阶段。它的第一个参数 `cls` 就是 `__new__` 返回的那个类，此时类已存在，可以做后续设置，但不返回任何东西。

为什么 `__new__` 里不能直接调 `super().__init__()`？因为**调用时机和职责不对**：`__new__` 执行时类对象还没被造出来，没有可供初始化的实例；初始化是 `__init__` 的活儿，Python 会在 `__new__` 返回对象后**自动**接着调用 `__init__`。若在 `__new__` 里手动调 `__init__`，等于对着「尚不存在/还没返回」的对象提前初始化，逻辑错乱，还会导致重复初始化。正确写法是：`__new__` 里只调 `super().__new__()` 造对象，初始化交给随后自动触发的 `__init__`。

一句话：**`__new__` 造出来（return 对象），`__init__` 装上去（无返回值）；先有 `__new__` 后有 `__init__`，各司其职，不能越位。**

3. **如果一个类同时使用了元类和装饰器，执行顺序是什么？** 先元类还是先装饰器？

**参考答案**

**先元类，后装饰器。** 顺序是：执行类体 → 元类创建出类对象（`__new__`/`__init__`）→ 类装饰器作用在这个已创建好的类上。原因很直观：装饰器 `@deco` 本质是 `Demo = deco(Demo)`，它得先有一个「类」才能装饰，而这个类正是元类造出来的。

```python
def deco(cls):
    print("2. 装饰器执行")
    cls.decorated = True
    return cls

class Meta(type):
    def __new__(mcs, name, bases, attrs):
        print("1. 元类 __new__ 执行")
        return super().__new__(mcs, name, bases, attrs)

@deco
class Demo(metaclass=Meta):
    pass

print("3. 使用类:", Demo.decorated)
```

预期输出：

```
1. 元类 __new__ 执行
2. 装饰器执行
3. 使用类: True
```

可见元类 `__new__` 先打印（造类），装饰器随后打印（加工类）。如果有多个装饰器，按「就近原则」从下往上依次作用，但都发生在元类创建之后。

💡 提示：元类影响「这个类及其所有子类」的创建过程；装饰器只加工「被装饰的这一个类」。两者可叠加，但装饰器若返回一个全新的类，要注意它可能不再带原来的元类。

4. **Django 的 `Model` 基类是如何利用元类实现字段自动收集的？** 试着查看 Django 源码中的 `ModelMetaclass`。

**参考答案**

Django 的 `Model` 用的元类叫 `ModelBase`（位于 `django/db/models/base.py`），思路与本章的 `ModelMeta` 一致，但更完善。核心流程在它的 `__new__` 里：

- **分离「字段」与「普通属性」**：遍历类体 `attrs`，把凡是 `Field` 实例（带 `contribute_to_class` 方法的对象）挑出来，从普通属性里移走，避免它们被当成常规类属性。
- **让字段「认领」名字并登记**：对每个字段调用 `field.contribute_to_class(cls, name)`，字段由此知道自己叫什么、属于哪个类，并被收进一个专门的字段集合。
- **构建 `_meta`（Options）**：把收集到的字段、表名、排序、约束等元信息封装成 `_meta` 对象挂到类上。之后 `User._meta.get_fields()`、建表、生成 SQL 都靠它。
- **处理继承**：合并父类（含抽象基类）的字段，处理 `Meta` 内部类的继承规则。
- **注册到应用注册表**：通过 `apps.register_model(...)` 把模型登记到所属 app，框架据此发现所有模型、做迁移和外键解析。

所以用户只写 `name = CharField(...)`，元类就在「类诞生那一刻」自动完成了字段收集、命名、元信息构建和注册——这正是声明式 ORM 的魔力。

💡 提示：Django 是第三方框架（需 `pip install django`），其源码会随版本演进，建议直接读你所用版本的 `django/db/models/base.py` 中 `ModelBase.__new__`。理解时抓住「收集字段 → 建 `_meta` → 注册模型」这条主线即可，不必拘泥细节。

5. **能否用元类实现 `@dataclass` 的功能？** 如果能，怎么做？如果不能，为什么？

**参考答案**

**能。** `@dataclass` 的本质是「读取类的字段注解，自动生成 `__init__`、`__repr__`、`__eq__` 等方法」。这件事元类完全做得到——在 `__new__` 里读取 `attrs['__annotations__']`，据此生成方法并塞回 `attrs` 即可。下面是一个最小实现：

```python
class DataMeta(type):
    def __new__(mcs, name, bases, attrs):
        annotations = attrs.get('__annotations__', {})
        fields = list(annotations)          # 从注解拿到字段名

        def __init__(self, *args):
            for fname, value in zip(fields, args):
                setattr(self, fname, value)

        def __repr__(self):
            inner = ", ".join(f"{f}={getattr(self, f)!r}" for f in fields)
            return f"{name}({inner})"

        def __eq__(self, other):
            if not isinstance(other, type(self)):
                return NotImplemented
            return all(getattr(self, f) == getattr(other, f) for f in fields)

        attrs['__init__'] = __init__        # 把生成的方法注入类
        attrs['__repr__'] = __repr__
        attrs['__eq__'] = __eq__
        return super().__new__(mcs, name, bases, attrs)

class Point(metaclass=DataMeta):
    x: int
    y: int

p = Point(1, 2)
print(p)                 # Point(x=1, y=2)
print(p == Point(1, 2))  # True
print(p == Point(3, 4))  # False
```

预期输出：

```
Point(x=1, y=2)
True
False
```

`Point` 没手写任何方法，元类却根据 `x: int`、`y: int` 注解自动生成了构造、打印和相等比较，效果与 `@dataclass` 类似。

不过「能做」不等于「该做」：

- 真正的 `dataclass` 还要处理默认值、`default_factory`、关键字参数、`frozen`、`order`、继承字段顺序等大量细节，用元类全部重写成本高。
- **`dataclass` 官方就是用类装饰器实现的**，因为这种「加工单个类」的需求装饰器更简单直观；元类的优势在「影响所有子类」，这里用不上。

💡 提示：本题是很好的元类练习，但生产环境请直接用标准库 `@dataclass`。记住经验法则——能用装饰器解决的，就别上元类。

---

## 📚 延伸阅读

- [Python 官方文档 — 3.3.1.1. 动态创建类型](https://docs.python.org/zh-cn/3/reference/datamodel.html#metaclasses)
- [Python 元类编程 — 中文详解](https://zhuanlan.zhihu.com/p/138884836)
- [Django Model 源码分析](https://github.com/django/django/blob/main/django/db/models/base.py)

---

**上一课**：Day 045 — OOP 综合实战
**下一课**：Day 047 — 描述符（Descriptor）
