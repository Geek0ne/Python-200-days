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

**参考答案**

区别在于**实现了哪些协议方法**：`property` 定义了 `__get__` + `__set__`（+ `__delete__`），所以是数据描述符；函数只定义了 `__get__`（用来把 `self` 绑定成绑定方法），没有 `__set__`，所以是非数据描述符。

这种设计的好处来自二者的**优先级差异**（数据描述符 > 实例 `__dict__` > 非数据描述符）：

- **property 必须「压过」实例字典**：它的职责是拦截读写做校验/计算。假如它是非数据描述符，用户一旦 `obj.name = x` 把值写进实例 `__dict__`，之后读取就会绕过 property，校验失效。做成数据描述符，保证无论实例字典里有没有同名值，**永远走 property 的 `__get__`/`__set__`**，控制不被架空。
- **方法应当「允许被实例覆盖」**：方法只需在读取时绑定 self，不需要拦截赋值。做成非数据描述符，意味着可以给单个实例临时替换某个方法（`obj.method = 别的函数`，常用于测试打桩/ monkey patch），实例属性优先于方法生效，灵活而不冲突。

一句话：**property 要「强制管控」所以用数据描述符；方法要「可被灵活覆盖」所以用非数据描述符。** 优先级规则恰好同时满足了这两种需求。

2. **如果要实现一个 `@cached_property` 装饰器**（值计算后缓存到实例 `__dict__`，后续直接读取），它的描述符需要实现 `__set__` 吗？为什么？

**参考答案**

**不需要，而且恰恰不能实现 `__set__`。** `cached_property` 必须是**非数据描述符**（只有 `__get__`），缓存机制才能成立。

原理正是优先级规则：非数据描述符 **低于** 实例 `__dict__`。第一次访问时实例字典里还没有这个键，于是走 `__get__` 计算值，并把结果写进 `obj.__dict__[同名]`；之后再访问，Python 发现实例字典里已有同名值，且描述符是非数据的，就**直接返回字典里的缓存值，不再触发 `__get__`**——这就是「算一次、后面直接读」。

如果实现了 `__set__`，它就变成数据描述符，优先级高于实例字典，那么每次读取都会强制走 `__get__`，缓存永远读不到，每次都重新计算，`cached_property` 就退化成普通 `property` 了。

```python
class cached_property:
    def __init__(self, func):
        self.func = func
        self.attrname = None

    def __set_name__(self, owner, name):
        self.attrname = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        value = self.func(obj)
        obj.__dict__[self.attrname] = value   # 缓存到实例字典
        return value
        # 注意：故意不写 __set__，保持非数据描述符

class Circle:
    def __init__(self, r):
        self.r = r

    @cached_property
    def area(self):
        print("计算中...")
        return 3.14159 * self.r ** 2

c = Circle(2)
print(c.area)    # 第一次：打印"计算中..."再输出结果
print(c.area)    # 第二次：直接读缓存，不再打印"计算中..."
```

预期输出：

```
计算中...
12.56636
12.56636
```

「计算中...」只出现一次，证明第二次读取命中了实例字典里的缓存。标准库 `functools.cached_property` 正是这样实现的。

⚠️ 注意：使用 `cached_property` 的类必须有 `__dict__`（不能是纯 `__slots__` 且没留 `__dict__` 的类），否则没地方存缓存。

3. **`__set_name__` 是什么时候被调用的？** 如果你的描述符不写 `__set_name__`，有什么替代方案？

**参考答案**

`__set_name__(self, owner, name)` 在**所属类被创建时**自动调用（Python 3.6+）。具体时机：类体执行完、`type.__new__` 造出类对象的过程中，会遍历类属性，对每个实现了 `__set_name__` 的描述符调用一次，把「宿主类 owner」和「属性名 name」告诉它。每个描述符只调用一次，发生在任何实例创建之前。它的作用是让描述符知道自己在类里叫什么，从而能用 `_{name}` 之类的私有名去实例字典里存值。

不写 `__set_name__` 的替代方案：

- **构造时显式传名字**：`name = TypeChecked('name', str)`，把属性名作为参数传给描述符。缺点是名字要写两遍，改名时容易漏改、不同步。
- **用元类统一设置**：在元类 `__new__` 里遍历属性，手动给每个描述符 `desc.name = key`，相当于自己实现 `__set_name__` 的逻辑。
- **访问时动态推断**：在 `__get__`/`__set__` 里遍历 `obj.__dict__` 或类的属性反查名字，但低效又别扭，不推荐。

💡 提示：`__set_name__` 是官方提供的「自动告知名字」机制，最省心；只有需要兼容 3.6 以前版本时才考虑显式传名。

4. **Django 的 `Model.field` 和 SQLAlchemy 的 `Column` 都用了描述符**，试想它们是如何通过描述符将数据库值映射到 Python 属性的。

**参考答案**

它们把「字段」做成描述符挂在模型类上，利用 `__get__`/`__set__` 在「Python 属性」和「数据库值」之间做双向转换与追踪。关键要分**实例访问**和**类访问**两种情形：

- **实例访问（`user.age`）——取值/转换**：`__get__` 从实例的状态容器（如 SQLAlchemy 的 `obj.__dict__` / `_sa_instance_state`，Django 的 `obj.__dict__`）里取出原始值，必要时做类型转换（数据库的字符串/整数 → Python 的 `datetime`、`Decimal`、枚举等），再返回。若值还没从数据库加载，可触发懒加载。
- **实例赋值（`user.age = 30`）——校验/标脏**：`__set__` 先做类型/约束校验和转换，把值存进实例状态，并**标记该字段为「已修改」（dirty）**。这样 ORM 在 `flush`/`save` 时知道哪些列需要写回数据库，只更新变化的字段。
- **类访问（`User.age`）——返回查询表达式**：当 `obj is None`（通过类而非实例访问）时，`__get__` 返回的不是值，而是一个「可参与运算的表达式对象」（SQLAlchemy 的 `InstrumentedAttribute`）。于是 `User.age > 18` 不是真的比较，而是**构造出一段 SQL 条件**，供 `filter()` 使用。

一句话：**描述符让「读属性＝取/转换数据库值」「写属性＝校验并记录变更」「类上访问属性＝生成 SQL 表达式」三件事统一在一个字段对象里**，这正是 ORM 用起来像普通对象、底层却能操作数据库的核心机制。

💡 提示：Django、SQLAlchemy 均为第三方库，实现细节随版本变化；理解时抓住「实例访问管数据、类访问管查询」这条主线即可。

5. **如果一个类同时有 `__slots__` 和描述符**，描述符的 `__set__` 会被调用吗？为什么？

**参考答案**

**会。** 而且要点是：**`__slots__` 本身就是靠描述符实现的**。声明 `__slots__ = ('x',)` 时，Python 会在类上为 `x` 创建一个「成员描述符」（`member_descriptor`，属于数据描述符）。给 `obj.x` 赋值时，调用的正是这个描述符的 `__set__`——值被存进预留的槽位，而不是实例 `__dict__`（slotted 类根本没有 `__dict__`）。所以「slots + 描述符」不是冲突，而是 slots 离不开描述符。

```python
class Slotted:
    __slots__ = ('x',)

print(type(Slotted.__dict__['x']).__name__)   # slot 本身就是描述符
s = Slotted()
s.x = 10                                       # 调用 slot 描述符的 __set__
print(s.x)
print(hasattr(s, '__dict__'))                  # False：没有实例字典

class Desc:
    def __get__(self, obj, objtype=None):
        return "d"
    def __set__(self, obj, value):
        pass

try:
    class Bad:
        __slots__ = ('x',)
        x = Desc()        # 自定义描述符与同名 slot 冲突
except ValueError as e:
    print("ValueError:", e)
```

预期输出：

```
member_descriptor
10
False
ValueError: 'x' in __slots__ conflicts with class variable
```

需要注意一个限制：**同一个名字不能既是 slot 又是类级自定义描述符**，否则定义类时就抛 `ValueError`（如上）。因此若想在 slotted 类里用自定义描述符，要么让它管理**别的**名字、把值存进某个 slot，要么干脆不用 `__slots__`。另外，自定义描述符里常见的 `obj.__dict__[name] = value` 写法在纯 slotted 类上会失败（没有 `__dict__`），需改用槽位存储。

⚠️ 注意：本章 5.2 的 `ValidatedSlot` 示例用了 `obj.__dict__`，那只适用于「带 `__dict__` 的类」；真正纯 `__slots__` 的类要换成槽位或 `object.__setattr__` 来存值。
