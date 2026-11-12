# Day 033 — 继承

> 单继承与 MRO、C3 线性化算法、super() 原理、形状层次结构

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 单继承 | ⭐⭐ | 子类定义、属性/方法继承、重写 |
| super() | ⭐⭐⭐ | 调用父类方法、MRO、菱形继承 |
| MRO (方法解析顺序) | ⭐⭐⭐ | C3 线性化算法、__mro__ 属性 |
| 多继承 | ⭐⭐⭐ | 钻石问题、super() 的正确使用 |
| Mixin 模式 | ⭐⭐⭐ | 通过多继承组合功能 |
| 形状层次结构 | ⭐⭐⭐ | 综合实战 |

---

## 一、继承基础

### 1.1 什么是继承？

继承允许一个类（子类）自动获取另一个类（父类）的属性和方法。

```python
class Animal:               # 父类 / 基类
    def __init__(self, name):
        self.name = name
    def speak(self):
        return "..."
    def move(self):
        return f"{self.name} moves"

class Dog(Animal):          # 子类 / 派生类
    def speak(self):        # 重写父类方法
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

# 使用
dog = Dog("Buddy")
cat = Cat("Kitty")
print(dog.speak())   # → Woof!    （来自子类）
print(dog.move())    # → Buddy moves  （来自父类）
print(cat.speak())   # → Meow!
```

### 1.2 继承关系图

```
Animal (父类)
├── name
├── speak() → "..."
└── move()  → "name moves"
     │
     ├── Dog (子类)
     │   ├── name (继承)
     │   ├── speak() → "Woof!"  (重写)
     │   └── move()  (继承)
     │
     └── Cat (子类)
         ├── name (继承)
         ├── speak() → "Meow!"  (重写)
         └── move()  (继承)

Dog 和 Cat 是 Animal 的"is-a"关系:
  Dog is an Animal ✓
  Cat is an Animal ✓
```

### 1.3 继承的语法

```python
# 定义父类
class Parent:
    def __init__(self, name):
        self.name = name
    def greet(self):
        return f"Hello, I'm {self.name}"

# 定义子类
class Child(Parent):
    def __init__(self, name, age):
        # 调用父类的 __init__
        super().__init__(name)
        self.age = age
    
    # 重写父类方法
    def greet(self):
        parent_greet = super().greet()
        return f"{parent_greet}. I'm {self.age} years old."
    
    # 新增方法
    def play(self):
        return f"{self.name} is playing"
```

---

## 二、方法重写 (Override)

```python
class Shape:
    def area(self):
        return 0
    
    def describe(self):
        return f"Shape with area {self.area()}"

class Circle(Shape):
    def __init__(self, radius):
        self.radius = radius
    
    def area(self):          # 重写
        return 3.14 * self.radius ** 2
    
    def describe(self):      # 重写 + 调用父类
        base = super().describe()
        return f"Circle(r={self.radius}), {base}"

class Square(Shape):
    def __init__(self, side):
        self.side = side
    
    def area(self):          # 重写
        return self.side ** 2

# 多态 — 同一方法在不同类中不同行为
shapes = [Circle(5), Square(4)]
for shape in shapes:
    print(shape.describe())
    # Circle(r=5), Shape with area 78.5
    # Shape with area 16
```

---

## 三、super() 详解

### 3.1 super() 的作用

`super()` 返回一个代理对象，用于调用父类的方法。

```python
class A:
    def __init__(self):
        print("A.__init__")
        self.a = 1

class B(A):
    def __init__(self):
        super().__init__()    # 调用 A.__init__
        print("B.__init__")
        self.b = 2

b = B()
# 输出:
#   A.__init__
#   B.__init__
```

### 3.2 super() 不只调用"父类"

`super()` 实际上根据 MRO 链来解析调用的类，而不只是字面意义上的"父类"。

```python
class A:
    def method(self):
        print("A.method")

class B(A):
    def method(self):
        print("B.method")
        super().method()

class C(A):
    def method(self):
        print("C.method")
        super().method()

class D(B, C):
    def method(self):
        print("D.method")
        super().method()

print(D.__mro__)
# D -> B -> C -> A -> object

d = D()
d.method()
# D.method
# B.method
# C.method  ← super() 在 B 中调用的是 C，不是 A!
# A.method
```

### 3.3 super() 的菱形继承

```
         A
        / \
       B   C
        \ /
         D

MRO: D → B → C → A → object

super() 在菱形继承中的效果:
  在 B.method 中调用 super().method()
    → 实际调用 C.method (不是 A.method!)
```

---

## 四、MRO (方法解析顺序)

### 4.1 什么是 MRO？

MRO (Method Resolution Order) 定义了 Python 查找方法的顺序。

```python
class A:
    pass

class B(A):
    pass

class C(A):
    pass

class D(B, C):
    pass

print(D.__mro__)
# (<class 'D'>, <class 'B'>, <class 'C'>, <class 'A'>, <class 'object'>)
```

### 4.2 C3 线性化算法

Python 使用 **C3 线性化** 算法计算 MRO，核心原则：

1. **子类优先于父类**
2. **声明顺序优先**（`class D(B, C)` 中 B 优先于 C）
3. **单调性**：一个类的 MRO 中的顺序不会影响其子类的 MRO

```
C3 算法伪代码:
  L[D(B, C)] = D + merge(L[B], L[C], [B, C])

merge 规则:
  取第一个列表的头（head）
  如果这个头不在其它列表的尾部（tail）中
    → 取出这个头，继续 merge
  否则 → 取下一个列表的头

示例: L[D(B, C)] where B and C extend A:
  L[B] = B, A, object
  L[C] = C, A, object
  
  L[D] = D + merge([B, A, O], [C, A, O], [B, C])
       = D + B + merge([A, O], [C, A, O], [C])
       = D + B + C + merge([A, O], [A, O])
       = D, B, C, A, O
```

### 4.3 查看 MRO

```python
# 三种方式查看 MRO
D.__mro__         # 元组形式
D.mro()           # 列表形式
help(D)           # 详细帮助

issubclass(D, A)  # → True
issubclass(D, B)  # → True
issubclass(D, C)  # → True
```

---

## 五、多继承与 Mixin

### 5.1 多继承

Python 允许一个类继承多个父类：

```python
class FlyingMixin:
    def fly(self):
        return f"{self.name} is flying"

class SwimmingMixin:
    def swim(self):
        return f"{self.name} is swimming"

class Duck(Animal, FlyingMixin, SwimmingMixin):
    def speak(self):
        return "Quack!"
```

### 5.2 Mixin 模式

Mixin 是一种特殊的多继承用法：
- 作为"插件"提供额外功能
- 不包含 `__init__`（避免初始化冲突）
- 方法名前缀确保不冲突

```python
class JSONMixin:
    """提供 JSON 序列化功能"""
    def to_json(self):
        import json
        return json.dumps(self.__dict__, default=str)

class LogMixin:
    """提供日志功能"""
    def log(self, message):
        print(f"[{self.__class__.__name__}] {message}")

class TimestampMixin:
    """提供时间戳功能"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_at = __import__('datetime').datetime.now()

class User(JSONMixin, LogMixin, TimestampMixin):
    def __init__(self, name, email):
        super().__init__()
        self.name = name
        self.email = email

user = User("Alice", "alice@example.com")
print(user.to_json())  # JSON serialization
user.log("logged in")  # [User] logged in
```

### 5.3 Mixin 的使用原则

```
✅ 正确用法:
  class MyClass(BaseClass, Mixin1, Mixin2):
      pass

  Mixin1 和 Mixin2 是"插件"功能
  BaseClass 是主要继承

❌ 错误用法:
  class MyClass(Mixin1, Mixin2, BaseClass):
      pass
  
  Mixin 应放在 BaseClass 之后

✅ Mixin 的最佳实践:
  • Mixin 不要有 __init__
  • Mixin 的方法名要避免冲突
  • Mixin 只添加功能，不修改现有行为
  • Mixin 倾向于与 super() 兼容
```

---

## 六、继承的高级话题

### 6.1 isinstance vs type

```python
class Animal: pass
class Dog(Animal): pass

dog = Dog()

type(dog)          # → <class '__main__.Dog'>
isinstance(dog, Dog)     # → True
isinstance(dog, Animal)  # → True (Dog is a Animal)
type(dog) is Dog         # → True
type(dog) is Animal      # → False (type 不检查继承)
```

### 6.2 `__init_subclass__`

Python 3.6+ 引入的子类初始化钩子：

```python
class PluginBase:
    """所有插件的基类"""
    _registry = {}
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 自动注册子类
        PluginBase._registry[cls.__name__] = cls
        print(f"📝 注册插件: {cls.__name__}")

class LogPlugin(PluginBase):
    pass

class CachePlugin(PluginBase):
    pass

print(PluginBase._registry)
# {'LogPlugin': <class...>, 'CachePlugin': <class...>}
```

### 6.3 抽象方法与 abc

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self): pass
    
    @abstractmethod
    def perimeter(self): pass

class Circle(Shape):
    def __init__(self, r): self.r = r
    def area(self): return 3.14 * self.r ** 2
    def perimeter(self): return 2 * 3.14 * self.r
```

---

## 💡 思考题

1. 多重继承中，`super().__init__()` 实际调用的不是"父类"而是 MRO 链中的下一个类。这意味着什么？在设计类继承时应该如何应对？

**参考答案**

`super()` 不是"调用父类"，而是"调用 MRO 链里当前类的下一个类"。在菱形继承中，`Left` 里写的 `super()` 可能跳到兄弟类 `Right` 而不是共同基类 `Base`。这正是 Python 的**协作式多重继承（cooperative multiple inheritance）**：只要链条上每个类都调用 `super()`，每个类的 `__init__` 恰好执行一次，且顺序由 MRO 决定，不会重复初始化共同基类。

**设计要点**：

- 链条上**每个类都要调用 `super().__init__()`**，漏掉一个就会截断后续初始化；
- 用 `**kwargs` 接收并向下传递参数，让不同类的构造签名能"接力"，避免某个类收到不认识的参数；
- 链条末端（`object` 之前那个类）要保证不再把多余参数传给 `object.__init__`；
- 别用 `Base.__init__(self)` 这种写死类名的方式，它会破坏 MRO 协作、导致基类被重复调用。

```python
# 思考题1：协作式多重继承，每个 __init__ 只执行一次
class Base:
    def __init__(self, **kwargs):
        print('Base')
        super().__init__(**kwargs)   # 链条末端交给 object


class Left(Base):
    def __init__(self, **kwargs):
        print('Left')
        super().__init__(**kwargs)   # 不是 Base，而是 MRO 里的 Right


class Right(Base):
    def __init__(self, **kwargs):
        print('Right')
        super().__init__(**kwargs)


class Child(Left, Right):
    def __init__(self, **kwargs):
        print('Child')
        super().__init__(**kwargs)


Child()
print([c.__name__ for c in Child.__mro__])
```

预期输出：

```text
Child
Left
Right
Base
['Child', 'Left', 'Right', 'Base', 'object']
```

💡 提示：`Left` 的 `super()` 跳到了 `Right`，`Base` 只打印一次——这就是 C3 + 协作式 `super()` 的价值。

2. Python 的 MRO 使用 C3 线性化算法。为什么 Java/C++ 的单一虚继承不需要这种机制？多继承带来了哪些复杂性？

**参考答案**

**Java 的类是单继承**：每个类只有一个父类，继承关系天然是一条直线，方法查找顺着这条链往上走即可，不存在"该先走哪条分支"的歧义，所以不需要线性化算法。（Java 的多接口实现没有状态和构造器冲突，默认方法冲突由编译器强制要求显式覆盖解决。）**C++ 虽支持多继承**，但它在**编译期**用虚基类指针/虚表布局解决菱形问题，把"共享一份基类子对象"的决策固化进对象内存结构，运行期不需要动态计算查找顺序。

**Python 是运行期动态语言**，属性查找每次都在运行时进行，多继承又允许任意菱形/网状结构，因此必须有一套规则把继承图**压成唯一的线性顺序**，这就是 C3 线性化。它保证三条性质：子类先于父类、声明顺序（`class D(B, C)` 中 B 先于 C）、单调性（父类的相对顺序在子类中不被打乱）。

**多继承带来的复杂性**：

- **菱形问题**：共同基类可能被重复初始化或重复执行（协作式 `super()` + C3 正是为此而生）；
- **方法/属性名冲突**：多个父类有同名成员时，到底用谁的，取决于 MRO；
- **构造器接力**：`__init__` 签名要兼容，参数传递容易出错；
- **可理解性下降**：继承图一复杂，调用顺序就不直观，需要 `__mro__` 辅助排查。

```python
# 思考题2：C3 线性化把菱形继承拉成唯一顺序
class A:
    pass


class B(A):
    pass


class C(A):
    pass


class D(B, C):
    pass


print([c.__name__ for c in D.__mro__])
```

预期输出：

```text
['D', 'B', 'C', 'A', 'object']
```

💡 提示：共同基类 `A` 在 MRO 里只出现一次，且排在 `B`、`C` 之后——这保证了 `A` 的方法不会被提前覆盖，也不会被重复调用。

3. Mixin 模式和普通多继承有什么区别？为什么 Django 的 View 类大量使用了 Mixin？

**参考答案**

Mixin 是**多继承的一种规范化用法**，区别在于设计意图和约束：

- **普通多继承**表达"is-a"，多个父类都可能是完整的、可独立实例化的类，容易带来状态和构造器冲突；
- **Mixin** 表达"can-do / 具备某能力"，是一个**只提供某项正交功能、不单独实例化**的"插件"类。它通常**不定义 `__init__`**（或只协作式地 `super()`）、不持有自己的核心状态、方法名专一以避免冲突，依赖宿主类提供 `self.name` 之类的属性。

**Django 大量用 Mixin 的原因**：视图的需求是"主继承体系（`View`）+ 若干可自由组合的能力"，比如 `LoginRequiredMixin`（登录校验）、`PermissionRequiredMixin`（权限）、`ListView`/`TemplateResponseMixin`（渲染）。这些能力彼此正交，用 Mixin 就能像搭积木一样按需拼装：`class MyView(LoginRequiredMixin, TemplateView)`。借助 MRO，Mixin 的方法（如 `dispatch`）会先于主基类执行，实现"前置拦截"，而无需改动主继承链，复用性和可读性都很好。

```python
# 思考题3：Mixin 组合正交能力
class ReprMixin:
    def __repr__(self):
        attrs = ', '.join(f'{k}={v!r}' for k, v in vars(self).items())
        return f'{type(self).__name__}({attrs})'


class UpperMixin:
    def shout(self):
        return self.name.upper()


class Person(ReprMixin, UpperMixin):
    def __init__(self, name):
        self.name = name


p = Person('alice')
print(p)          # 来自 ReprMixin
print(p.shout())  # 来自 UpperMixin
```

预期输出：

```text
Person(name='alice')
ALICE
```

💡 提示：约定把 Mixin 放在主基类**左边**（`class C(Mixin, Base)`），这样 Mixin 的方法在 MRO 中优先，才能起到"覆盖/前置"的作用；Mixin 命名常以 `Mixin` 结尾以示区分。

4. `isinstance(obj, cls)` 和 `type(obj) is cls` 有什么区别？在什么场景应该使用哪一个？

**参考答案**

- **`isinstance(obj, cls)`**：检查"是不是 cls **或其子类**的实例"，**尊重继承**，还支持第二个参数传元组（`isinstance(x, (A, B))`），并且认抽象基类的"虚拟子类"（通过 `register` 或 `__instancecheck__` 认定）。
- **`type(obj) is cls`**：只看对象的**精确类型**，完全忽略继承——子类实例返回 `False`。

**选择场景**：

- 绝大多数情况用 `isinstance`：它符合**里氏替换原则**，让子类对象能被当作父类使用，是多态的基础；
- 只有当你**明确要排除子类**、要求"就是这个类型本身"时才用 `type(...) is ...`，例如某些精确分派、序列化时区分 `bool` 与 `int`（`bool` 是 `int` 的子类，`isinstance(True, int)` 为 `True`，需要精确判断时就得用 `type`）。

```python
# 思考题4：isinstance 考虑继承，type 只看精确类型
class Animal:
    pass


class Dog(Animal):
    pass


d = Dog()
print(isinstance(d, Animal))       # True
print(type(d) is Animal)           # False
print(type(d) is Dog)              # True
print(isinstance(d, (Dog, str)))   # True，支持元组

from collections.abc import Iterable
print(isinstance([], Iterable))    # True，抽象基类也认
print(type([]) is Iterable)        # False
```

预期输出：

```text
True
False
True
True
True
False
```

⚠️ 注意：`type(obj) == cls` 与 `type(obj) is cls` 效果类似，但推荐用 `is` 做类型 identity 比较；另外滥用 `type` 精确判断会破坏多态，让子类无法替换父类，应谨慎。

5. `__init_subclass__` 可以用于实现什么设计模式？它和 metaclass 相比有什么优劣？

**参考答案**

`__init_subclass__`（Python 3.6+）是定义在父类里的钩子，**每当有子类被创建时自动调用**（它隐式是 classmethod，收到子类 `cls`）。适合实现：

- **注册表 / 插件模式**：子类一定义就自动登记到中央字典，无需手动注册；
- **工厂模式的变体**：按名字查找并实例化已注册的子类；
- **约束校验 / 自动配置**：强制子类实现某些属性、或统一给子类注入默认配置。

**与 metaclass 对比**：

- **优势**：写法极简，就是普通方法，不需要理解元类；**天然可组合**——多个父类各自的 `__init_subclass__` 会沿 MRO 协作调用，不会像元类那样产生"metaclass conflict"；对使用者透明，继承即生效。
- **劣势**：能力有限。它在**类已经创建之后**才被调用，无法干预类的创建过程本身（如自定义类命名空间 `__prepare__`、在类对象生成前修改成员、控制 `type.__new__`）。这些"造类"级别的定制仍需 metaclass。

一句话：**能用 `__init_subclass__` 解决的就别上 metaclass**；只有需要控制"类是怎么被造出来的"时才用元类。

```python
# 思考题5：__init_subclass__ 实现自动注册
class Plugin:
    registry = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.registry[cls.__name__] = cls   # 定义子类时自动登记


class A(Plugin):
    pass


class B(Plugin):
    pass


print(sorted(Plugin.registry))
```

预期输出：

```text
['A', 'B']
```

💡 提示：`__init_subclass__` 里记得调用 `super().__init_subclass__(**kwargs)`，以保持多继承下的协作链；它只在"定义子类"时触发，实例化对象时不会再触发。

---

## 📚 参考资源

- [Python 官方教程 — 继承](https://docs.python.org/3/tutorial/classes.html#inheritance)
- [Python MRO 文档](https://www.python.org/download/releases/2.3/mro/)
- [super() 详解 — Raymond Hettinger](https://rhettinger.wordpress.com/2011/05/26/super-considered-super/)
- [Python abc 模块](https://docs.python.org/3/library/abc.html)
- [Real Python — Python Inheritance](https://realpython.com/inheritance-python/)
