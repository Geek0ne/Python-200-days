# Day 047 — 描述符（Descriptor）

## 📚 今日目标

深入理解 Python 描述符协议，掌握 `__get__`、`__set__`、`__delete__` 三大方法，理解 `property` 的底层实现，并实战构建类型校验描述符。

---

## 1. 描述符是什么？

### 1.1 概念定义

**描述符（Descriptor）** 是实现了特定协议方法的对象，当它作为另一个类的**属性**时，Python 会自动拦截对该属性的访问、赋值和删除操作。

简单说：**描述符就是"属性的代理人"**——你访问 `obj.attr`，但实际执行的是描述符对象的 `__get__` 方法。

```python
# 普通属性：直接返回值
class Regular:
    def __init__(self):
        self.name = "hello"  # 普通属性

# 描述符：拦截属性访问
class Descriptor:
    def __get__(self, obj, objtype=None):
        return "通过描述符访问"

class WithDescriptor:
    name = Descriptor()  # 类属性是一个描述符对象

obj = WithDescriptor()
print(obj.name)  # 输出: 通过描述符访问（而非 AttributeError）
```

### 1.2 为什么需要描述符？

| 问题 | 传统方案 | 描述符方案 |
|------|----------|------------|
| 类型检查 | 每个属性都写 `@property` | 写一个类型描述符复用 |
| 值验证 | 在 `__init__` 里逐个校验 | 描述符自动校验 |
| 懒加载 | 每个属性写 getter | 一个描述符搞定 |
| 访问控制 | 每个属性写 `@prop.setter` | 描述符统一管理 |

**核心价值：DRY 原则（Don't Repeat Yourself）—— 把属性的通用行为抽成可复用的组件。**

---

## 2. 描述符协议详解

### 2.1 三大核心方法

描述符协议由三个可选方法组成：

```python
class MyDescriptor:
    """描述符协议示例"""

    def __get__(self, obj, objtype=None):
        """
        参数:
            obj     - 实例对象（通过实例访问时），静态访问时为 None
            objtype - 所属类
        返回: 属性值
        """
        print(f"__get__ 被调用: obj={obj}, objtype={objtype}")
        return self._value

    def __set__(self, obj, value):
        """
        参数:
            obj   - 实例对象
            value - 要设置的新值
        """
        print(f"__set__ 被调用: obj={obj}, value={value}")
        self._value = value

    def __delete__(self, obj):
        """
        参数:
            obj - 实例对象
        """
        print(f"__delete__ 被调用: obj={obj}")
        del self._value
```

### 2.2 描述符的访问机制

当 Python 执行 `obj.attr` 时，查找顺序如下：

```
                    obj.attr 查找流程
                    ─────────────────
                         │
                         ▼
              ┌─────────────────────┐
              │ obj.__class__.__mro │  ← 沿 MRO 查找
              └─────────┬───────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │ 找到 attr 所在类    │
              └─────────┬───────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │ attr 是否描述符?    │──── 否 ──→ 返回类属性值
              └─────────┬───────────┘
                        │ 是
                        ▼
              ┌─────────────────────┐
              │ obj 是否实例?       │──── 否 ──→ 返回描述符本身
              └─────────┬───────────┘
                        │ 是
                        ▼
              ┌─────────────────────┐
              │ 调用 __get__(obj)   │
              └─────────────────────┘
```

> **关键规则：描述符只在类属性上有效，实例属性上的同名对象不会触发描述符协议！**

```python
class Desc:
    def __get__(self, obj, objtype=None):
        return "desc value"

class MyClass:
    x = Desc()  # 类属性 → 描述符生效

obj = MyClass()
print(obj.x)          # "desc value" ✅ 描述符拦截

obj.x = "instance"    # 赋值到实例属性
print(obj.x)          # "instance" ❌ 描述符被绕过！
```

### 2.3 数据描述符 vs 非数据描述符

这是理解描述符最重要的分类：

| 类型 | 必须实现的方法 | 优先级 | 典型例子 |
|------|--------------|--------|---------|
| **数据描述符** | `__get__` + `__set__`（或 `__delete__`） | **高于**实例 `__dict__` | `property`, `classmethod` |
| **非数据描述符** | 仅 `__get__` | **低于**实例 `__dict__` | 方法、`@staticmethod` |

```python
# 数据描述符：有 __get__ + __set__
class DataDesc:
    def __get__(self, obj, objtype=None):
        return "data descriptor"
    def __set__(self, obj, value):
        print(f"数据描述符拦截了赋值: {value}")

# 非数据描述符：只有 __get__
class NonDataDesc:
    def __get__(self, obj, objtype=None):
        return "non-data descriptor"

class Test:
    a = DataDesc()
    b = NonDataDesc()

t = Test()
t.a = "try"          # 输出: 数据描述符拦截了赋值: try
print(t.a)           # "data descriptor" ✅

t.b = "try"          # 不触发 __set__（因为没有）
print(t.b)           # "try" ← 实例属性覆盖了描述符！
```

**为什么方法也是描述符？** 函数实现了 `__get__`，所以当你在实例上调用方法时：

```python
class MyClass:
    def greet(self):
        return "hello"

obj = MyClass()
# obj.greet 是一个非数据描述符
# Python 调用 Function.__get__(obj, MyClass)
# 返回一个绑定方法（bound method），自动绑定 self
print(obj.greet())  # "hello" — 描述符帮你做了 self 绑定！
```

---

## 3. property 的底层实现

`property` 本质上就是一个**数据描述符**：

```python
# 等价关系
class MyClass:
    @property
    def name(self):
        return self._name

# 底层等价于
class name_property:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self          # 类访问返回描述符本身
        return obj._name

    def __set__(self, obj, value):
        obj._name = value

    def __delete__(self, obj):
        del obj._name

    def getter(self, func):
        self._getter = func
        return self

    def setter(self, func):
        self._setter = func
        return self

class MyClass:
    name = name_property()
    name = name.name.getter(lambda self: self._name)
    name = name.name.setter(lambda self, v: setattr(self, '_name', v))
```

### 3.1 用描述符重写 property

```python
class Property:
    """自己实现一个简化版 property"""

    def __init__(self, fget=None, fset=None, fdel=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        return self.fget(obj)

    def __set__(self, obj, value):
        if self.fset is None:
            raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        self.fdel(obj)

    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel)
```

---

## 4. 实战：类型校验描述符

### 4.1 基础版：类型检查描述符

```python
class TypeChecked:
    """类型检查描述符 —— 自动校验属性类型"""

    def __init__(self, expected_type, default=None):
        self.expected_type = expected_type
        self.default = default
        self.name = None  # 会在 __set_name__ 中设置

    def __set_name__(self, owner, name):
        """Python 3.6+ 自动调用，告诉描述符它在哪个类、叫什么名字"""
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(
                f"{self.name} 必须是 {self.expected_type.__name__} 类型，"
                f"但收到 {type(value).__name__}: {value!r}"
            )
        setattr(obj, self.private_name, value)

    def __repr__(self):
        return f"TypeChecked({self.expected_type.__name__}, default={self.default!r})"


class User:
    name = TypeChecked(str)
    age = TypeChecked(int, default=0)
    email = TypeChecked(str)

    def __init__(self, name, age, email):
        self.name = name
        self.age = age
        self.email = email

    def __repr__(self):
        return f"User(name={self.name!r}, age={self.age}, email={self.email!r})"


# 使用
u = User("Alice", 30, "alice@example.com")
print(u)  # User(name='Alice', age=30, email='alice@example.com')

try:
    u.age = "thirty"  # TypeError!
except TypeError as e:
    print(f"✅ 拦截成功: {e}")
```

### 4.2 进阶版：带范围检查和自定义校验

```python
class Validated:
    """支持多种校验规则的描述符"""

    def __init__(self, *validators, error_msg=None):
        self.validators = validators
        self.error_msg = error_msg or "验证失败"
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        for validator in self.validators:
            error = validator(value)
            if error:
                raise ValueError(f"{self.name}: {error}")
        setattr(obj, self.private_name, value)

    def __repr__(self):
        return f"Validated({self.name})"


# 校验器函数
def not_empty(value):
    return "不能为空" if not value else None

def min_length(n):
    def check(value):
        return f"长度不能少于 {n}" if len(value) < n else None
    return check

def positive(value):
    return "必须为正数" if value <= 0 else None

def in_range(low, high):
    def check(value):
        return f"必须在 {low}-{high} 之间" if not (low <= value <= high) else None
    return check


class Product:
    name = Validated(not_empty, min_length(2))
    price = Validated(positive)
    quantity = Validated(positive, in_range(1, 10000))

    def __init__(self, name, price, quantity):
        self.name = name
        self.price = price
        self.quantity = quantity

    def __repr__(self):
        return f"Product({self.name!r}, ¥{self.price}, x{self.quantity})"


# 正常使用
p = Product("Python教程", 59.9, 100)
print(p)

# 校验失败
try:
    Product("", 59.9, 100)     # 空名字
except ValueError as e:
    print(f"✅ {e}")

try:
    Product("Py", 59.9, 100)   # 名字太短
except ValueError as e:
    print(f"✅ {e}")

try:
    Product("Python", -10, 100) # 负价格
except ValueError as e:
    print(f"✅ {e}")
```

### 4.3 实战：懒加载 + 缓存描述符

```python
import time

class LazyProperty:
    """惰性求值描述符 —— 第一次访问时计算，之后缓存"""

    def __init__(self, func):
        self.func = func
        self.attrname = None

    def __set_name__(self, owner, name):
        self.attrname = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        # 计算值并存到实例 __dict__（绕过描述符）
        value = self.func(obj)
        obj.__dict__[self.attrname] = value
        return value


class DataAnalyzer:
    """数据分析器 —— 用懒加载延迟昂贵计算"""

    def __init__(self, data):
        self.data = data

    @LazyProperty
    def mean(self):
        """平均值 —— 只在第一次访问时计算"""
        print("⏳ 计算平均值中...")
        time.sleep(0.1)  # 模拟耗时操作
        return sum(self.data) / len(self.data)

    @LazyProperty
    def variance(self):
        """方差 —— 依赖 mean"""
        print("⏳ 计算方差中...")
        time.sleep(0.1)
        m = self.mean  # 会触发缓存
        return sum((x - m) ** 2 for x in self.data) / len(self.data)

    @LazyProperty
    def std_dev(self):
        """标准差"""
        return self.variance ** 0.5


analyzer = DataAnalyzer(list(range(100)))

print("首次访问 mean:")
t = time.time()
print(f"  mean = {analyzer.mean}")
print(f"  ⏱️ 耗时: {time.time() - t:.3f}s")

print("\n再次访问 mean（使用缓存）:")
t = time.time()
print(f"  mean = {analyzer.mean}")
print(f"  ⏱️ 耗时: {time.time() - t:.6f}s")

print("\n访问 std_dev（触发 variance + mean）:")
t = time.time()
print(f"  std_dev = {analyzer.std_dev:.4f}")
print(f"  ⏱️ 耗时: {time.time() - t:.3f}s")
```

---

## 5. 高级技巧

### 5.1 `__set_name__` 的作用

Python 3.6+ 新增，描述符被定义为类属性时自动调用：

```python
class Descriptor:
    def __set_name__(self, owner, name):
        self.public_name = name
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, value)
```

### 5.2 描述符与 `__slots__` 的交互

```python
class Slotted:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x  # 触发描述符 __set__
        self.y = y

# 注意：__slots__ 中的条目可以是描述符！
class ValidatedSlot:
    def __init__(self, check):
        self.check = check
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        if not self.check(value):
            raise ValueError(f"{self.name} 校验失败: {value}")
        obj.__dict__[self.name] = value
```

### 5.3 描述符的适用场景总结

```
┌─────────────────────────────────────────────────────┐
│                  描述符适用场景                       │
├─────────────┬───────────────────────────────────────┤
│ 类型检查     │ TypeChecked, TypedField              │
│ 值校验       │ Validated, RangeChecked              │
│ 懒加载       │ LazyProperty, CachedProperty         │
│ 访问控制     │ ReadOnly, Private, Protected          │
│ 单位转换     │ Celsius, Fahrenheit                  │
│ 数据库字段映射│ SQLAlchemy Column                    │
│ ORM 字段     │ Django Model 字段                    │
│ 计算属性     │ property 的本质就是描述符             │
│ 方法绑定     │ 普通方法也是非数据描述符               │
└─────────────┴───────────────────────────────────────┘
```

---

## 6. 描述符执行顺序图解

```mermaid
graph TD
    A["obj.attr"] --> B{attr 在类的 MRO 中?}
    B -->|否| C[返回 AttributeError]
    B -->|是| D{attr 是描述符?}
    D -->|否| E[返回类属性值]
    D -->|是| F{obj 有 __dict__ 且有 attr?}
    F -->|有| G{描述符是数据描述符?}
    G -->|是| H[调用 __get__]
    G -->|否| I[返回实例 __dict__[attr]]
    F -->|无| H
    H --> J{obj 是否为 None?}
    J -->|是| K[返回描述符本身]
    J -->|否| L["调用 __get__(obj, type(obj))"]
```

---

## 7. 常见陷阱

### 陷阱 1：实例属性覆盖非数据描述符

```python
class MyMethod:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        def wrapper(*args):
            return f"called on {obj}"
        return wrapper

class MyClass:
    method = MyMethod()

obj = MyClass()
print(obj.method())  # "called on <__main__.MyClass object...>"

# 但如果手动赋值实例属性，会覆盖描述符
obj.method = "overwritten"
print(obj.method)     # "overwritten" — 描述符被绕过！
print(obj.method())   # TypeError: 'str' is not callable
```

### 陷阱 2：描述符中的循环引用

```python
class Parent:
    def __get__(self, obj, objtype=None):
        return obj  # 返回实例本身 —— 可能导致无限递归

# 解决：缓存到 __dict__
class SafeDescriptor:
    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if '_cached' not in obj.__dict__:
            obj.__dict__['_cached'] = compute_value(obj)
        return obj.__dict__['_cached']
```

### 陷阱 3：描述符实例共享状态

```python
class SharedState:
    """⚠️ 错误示范：描述符实例在所有类实例间共享状态！"""
    def __get__(self, obj, objtype=None):
        return self.value  # self 是描述符对象，不是实例！

    def __set__(self, obj, value):
        self.value = value  # 所有实例都会看到同一个值

# ✅ 正确做法：把状态存到实例 __dict__
class CorrectDescriptor:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value
```

---

## 8. 思考题

1. **为什么 `property` 是数据描述符，而普通方法（函数）是非数据描述符？** 这种设计有什么好处？

2. **如果要实现一个 `@cached_property` 装饰器**（值计算后缓存到实例 `__dict__`，后续直接读取），它的描述符需要实现 `__set__` 吗？为什么？

3. **`__set_name__` 是什么时候被调用的？** 如果你的描述符不写 `__set_name__`，有什么替代方案？

4. **Django 的 `Model.field` 和 SQLAlchemy 的 `Column` 都用了描述符**，试想它们是如何通过描述符将数据库值映射到 Python 属性的。

5. **如果一个类同时有 `__slots__` 和描述符**，描述符的 `__set__` 会被调用吗？为什么？
