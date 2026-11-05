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
2. Python 的 MRO 使用 C3 线性化算法。为什么 Java/C++ 的单一虚继承不需要这种机制？多继承带来了哪些复杂性？
3. Mixin 模式和普通多继承有什么区别？为什么 Django 的 View 类大量使用了 Mixin？
4. `isinstance(obj, cls)` 和 `type(obj) is cls` 有什么区别？在什么场景应该使用哪一个？
5. `__init_subclass__` 可以用于实现什么设计模式？它和 metaclass 相比有什么优劣？

---

## 📚 参考资源

- [Python 官方教程 — 继承](https://docs.python.org/3/tutorial/classes.html#inheritance)
- [Python MRO 文档](https://www.python.org/download/releases/2.3/mro/)
- [super() 详解 — Raymond Hettinger](https://rhettinger.wordpress.com/2011/05/26/super-considered-super/)
- [Python abc 模块](https://docs.python.org/3/library/abc.html)
- [Real Python — Python Inheritance](https://realpython.com/inheritance-python/)
