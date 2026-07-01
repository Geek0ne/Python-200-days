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

2. **元类的 `__new__` 和 `__init__` 有什么区别？** 在元类中，`__new__` 不能直接调用 `super().__init__()`，为什么？

3. **如果一个类同时使用了元类和装饰器，执行顺序是什么？** 先元类还是先装饰器？

4. **Django 的 `Model` 基类是如何利用元类实现字段自动收集的？** 试着查看 Django 源码中的 `ModelMetaclass`。

5. **能否用元类实现 `@dataclass` 的功能？** 如果能，怎么做？如果不能，为什么？

---

## 📚 延伸阅读

- [Python 官方文档 — 3.3.1.1. 动态创建类型](https://docs.python.org/zh-cn/3/reference/datamodel.html#metaclasses)
- [Python 元类编程 — 中文详解](https://zhuanlan.zhihu.com/p/138884836)
- [Django Model 源码分析](https://github.com/django/django/blob/main/django/db/models/base.py)

---

**上一课**：Day 045 — OOP 综合实战
**下一课**：Day 047 — 描述符（Descriptor）
