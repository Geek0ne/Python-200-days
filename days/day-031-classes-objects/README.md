# Day 031 — 类与对象

> 面向对象编程基础：类定义、实例化、构造方法、图书管理系统

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 面向对象概念 | ⭐⭐ | 类/对象、封装/继承/多态 |
| 类定义与实例化 | ⭐⭐ | `class` 关键字、`__init__` |
| 实例变量与方法 | ⭐⭐ | self、实例方法 |
| 类变量 | ⭐⭐ | 类属性、所有实例共享 |
| 特殊方法 | ⭐⭐⭐ | `__str__`、`__repr__`、`__eq__` |
| 图书管理系统 | ⭐⭐⭐ | 综合实战 |

---

## 一、面向对象编程概述

### 1.1 什么是面向对象编程？

**面向对象编程（OOP）** 是一种将程序组织为「对象」的编程范式。每个对象包含数据（属性）和操作这些数据的方法。

```
                    ┌─────────────────────┐
                    │     类 (Class)      │
                    │     ───────────     │
                    │  class Dog:         │
                    │    name = "Buddy"   │ ← 属性
                    │    def bark():      │
                    │      print("Woof!") │ ← 方法
                    └─────────┬───────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ 对象1    │   │ 对象2    │   │ 对象3    │
        │ Buddy    │   │ Max      │   │ Bella    │
        └──────────┘   └──────────┘   └──────────┘
```

### 1.2 面向对象的三大特征

| 特征 | 说明 | 类比 |
|------|------|------|
| **封装** | 将数据和方法绑定在一起，隐藏内部实现 | 电视遥控器 — 你按按钮就好，不用知道内部电路 |
| **继承** | 子类自动拥有父类的属性和方法 | 儿子拥有父亲的特征（肤色、眼睛颜色） |
| **多态** | 同一个方法在不同类中有不同实现 | 猫叫"喵"，狗叫"汪"，但都是动物叫 |

### 1.3 类 vs 对象

```
类 (Class)                         对象 (Object)
─────────                         ──────────
• 蓝图/模板                        • 具体实例
• 定义属性与方法                    • 有具体的数据
• 就像一个"蛋糕模具"               • 就像用模具做出来的"蛋糕"

class Car:                          my_car = Car("红色", "特斯拉")
    def __init__(self, color):      # my_car.color = "红色"
        self.color = color          # my_car.brand = "特斯拉"
    def drive(self):                # my_car.drive()
        print("行驶中...")
```

---

## 二、类定义与实例化

### 2.1 定义类

```python
class Student:
    """学生类 — 类文档字符串"""
    
    # 类变量（所有实例共享）
    school = "Python Academy"
    
    # 构造方法（实例化时自动调用）
    def __init__(self, name, age, grade):
        # 实例变量（每个实例独有）
        self.name = name
        self.age = age
        self.grade = grade
    
    # 实例方法
    def introduce(self):
        return f"我叫{self.name}，{self.age}岁，就读于{self.school}"
    
    def study(self, hours):
        self.grade += hours * 0.5
        return f"学习了{hours}小时，成绩提高到{self.grade:.1f}分"
```

### 2.2 实例化

```python
# 创建对象（实例化）
alice = Student("Alice", 18, 85.0)
bob = Student("Bob", 19, 92.0)

# 访问属性
print(alice.name)      # → Alice
print(alice.school)    # → Python Academy（类变量）
print(bob.school)      # → Python Academy

# 调用方法
print(alice.introduce())  # → 我叫Alice，18岁，就读于Python Academy
print(alice.study(2))     # → 学习了2小时，成绩提高到86.0分

# 修改属性
alice.age = 19
print(alice.age)  # → 19
```

### 2.3 构造方法 `__init__`

`__init__` 是 Python 中特殊的构造方法，在类实例化时自动调用。

```python
class Point:
    def __init__(self, x=0, y=0):
        """初始化点的坐标"""
        self.x = x
        self.y = y
        print(f"创建点 ({self.x}, {self.y})")

# 创建对象时自动调用 __init__
p1 = Point(3, 4)     # → 创建点 (3, 4)
p2 = Point()          # → 创建点 (0, 0) — 使用默认值
```

需要注意：Python 的 `__init__` 不是真正的构造函数（真正的构造函数是 `__new__`），但它是开发者最常用的初始化方法。

### 2.4 `__new__` vs `__init__`

```python
class Demo:
    def __new__(cls, *args, **kwargs):
        """真正的构造函数：创建实例"""
        print(f"1. __new__ 被调用, cls={cls}")
        instance = super().__new__(cls)
        return instance
    
    def __init__(self, value):
        """初始化函数：设置实例属性"""
        print(f"2. __init__ 被调用, self={self}, value={value}")
        self.value = value
```

```
实例化过程:
  Demo(42)
    │
    ▼
  __new__(Demo, 42) → 创建空实例
    │
    ▼
  __init__(instance, 42) → 初始化属性
    │
    ▼
  返回 instance
```

---

## 三、实例方法详解

### 3.1 self 是什么？

`self` 是实例方法的第一参数，指向当前对象实例。

```python
class Dog:
    def __init__(self, name):
        self.name = name
    
    def bark(self):
        print(f"{self.name} says Woof!")

dog = Dog("Buddy")
dog.bark()       # → Buddy says Woof!

# 实际上调用的是:
Dog.bark(dog)    # → 等同于 dog.bark()
```

> 🔑 记住：`self` 就是"我自己"，Python 自动传递实例本身给方法。

### 3.2 方法的链式调用

返回 `self` 可以实现方法的链式调用：

```python
class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x):
        self.result += x
        return self
    
    def subtract(self, x):
        self.result -= x
        return self
    
    def multiply(self, x):
        self.result *= x
        return self

calc = Calculator()
calc.add(5).subtract(2).multiply(3)
print(calc.result)  # → 9
```

---

## 四、特殊方法（Magic Methods）

特殊方法以双下划线开头和结尾，让自定义类能像内置类型一样使用。

### 4.1 常用特殊方法速查

| 方法 | 作用 | 触发方式 |
|------|------|---------|
| `__init__` | 初始化对象 | `obj = Class()` |
| `__str__` | 用户友好的字符串 | `str(obj)`, `print(obj)` |
| `__repr__` | 开发者友好的字符串 | `repr(obj)`, 调试显示 |
| `__eq__` | 相等判断 | `obj1 == obj2` |
| `__lt__` | 小于判断 | `obj1 < obj2` |
| `__len__` | 长度 | `len(obj)` |
| `__getitem__` | 索引访问 | `obj[key]` |
| `__add__` | 加法 | `obj1 + obj2` |
| `__call__` | 可调用对象 | `obj()` |

### 4.2 完整示例

```python
class Book:
    def __init__(self, title, author, pages):
        self.title = title
        self.author = author
        self.pages = pages
    
    def __str__(self):
        """给用户看：print 时显示"""
        return f"《{self.title}》by {self.author}"
    
    def __repr__(self):
        """给开发者看：调试时显示"""
        return f"Book(title='{self.title}', author='{self.author}', pages={self.pages})"
    
    def __eq__(self, other):
        """相等判断：我们通常按标题和作者判断"""
        if not isinstance(other, Book):
            return NotImplemented
        return (self.title == other.title and 
                self.author == other.author)
    
    def __lt__(self, other):
        """小于：按页数排序"""
        return self.pages < other.pages
    
    def __len__(self):
        return self.pages
    
    def __add__(self, other):
        """两本书的页数相加"""
        return self.pages + other.pages

# 使用
book1 = Book("Python入门", "张三", 300)
book2 = Book("Python进阶", "李四", 450)
book3 = Book("Python入门", "张三", 300)

print(book1)              # → 《Python入门》by 张三
print(repr(book1))        # → Book(title='Python入门', ...)
print(book1 == book3)     # → True
print(book1 < book2)      # → True
print(len(book1))         # → 300
print(book1 + book2)      # → 750
```

### 4.3 `__str__` vs `__repr__`

```
                  __str__                    __repr__
                  ───────                    ───────
面向            用户                       开发者
目标           可读性                      明确性/调试
如果未定义      fallback 到 __repr__        不会自动fallback
期望           简洁易读                    至少包含类型和关键属性

示例:
  str(datetime.now())     → '2024-06-22 09:30:00'
  repr(datetime.now())    → 'datetime.datetime(2024, 6, 22, 9, 30)'
```

---

## 五、类的设计原则

### 5.1 单一职责原则

```python
# ❌ 不好的设计：一个类做太多事
class UserManager:
    def create_user(self, name): ...
    def send_email(self, user): ...
    def generate_report(self): ...

# ✅ 好的设计：每个类职责明确
class User:
    """用户数据模型"""
    ...

class EmailService:
    """邮件服务"""
    ...

class ReportGenerator:
    """报表生成器"""
    ...
```

### 5.2 高内聚低耦合

```
高内聚: 类的属性和方法紧密围绕一个核心功能
低耦合: 类之间的依赖尽量少

✅ 高内聚示例:
  Customer:
    - name, email, phone    ← 都是客户基本信息
    - check_in(), leave()   ← 都是酒店客户操作

    ❌ 低内聚示例:
  Customer:
    - name, email, phone
    - send_email()          ← 属于邮件服务
    - calculate_tax()       ← 属于财务模块
```

---

## 六、综合实战：图书管理系统

### 6.1 系统设计

```
图书管理系统
┌─────────────────────────────────────────────┐
│  Book              Library                  │
│  ──────────         ──────────              │
│  + title            + books: dict           │
│  + author           + add_book()            │
│  + isbn             + borrow_book()         │
│  + available        + return_book()         │
│  + __str__()        + search()              │
│  + __repr__()       + list_books()          │
│  + __eq__()         + stats()               │
│                     + save() / load()       │
└─────────────────────────────────────────────┘
```

### 6.2 核心代码

```python
class Book:
    """图书类"""
    def __init__(self, title, author, isbn):
        self.title = title
        self.author = author
        self.isbn = isbn
        self.available = True
    
    def __str__(self):
        status = "可借" if self.available else "已借出"
        return f"《{self.title}》{self.author} [{status}]"
    
    def __repr__(self):
        return f"Book({self.title!r}, {self.author!r}, {self.isbn!r})"


class Library:
    """图书馆类"""
    def __init__(self, name):
        self.name = name
        self.books = {}
    
    def add_book(self, book):
        self.books[book.isbn] = book
        return f"添加图书: {book.title}"
    
    def borrow_book(self, isbn):
        book = self.books.get(isbn)
        if not book:
            return f"图书不存在 (ISBN: {isbn})"
        if not book.available:
            return f"《{book.title}》已被借出"
        book.available = False
        return f"借出成功: 《{book.title}》"
    
    def return_book(self, isbn):
        book = self.books.get(isbn)
        if not book:
            return f"图书不存在 (ISBN: {isbn})"
        if book.available:
            return f"《{book.title}》未被借出"
        book.available = True
        return f"归还成功: 《{book.title}》"
    
    def search(self, keyword):
        return [b for b in self.books.values() 
                if keyword.lower() in b.title.lower() 
                or keyword.lower() in b.author.lower()]
    
    def list_books(self, only_available=False):
        books = [b for b in self.books.values() 
                 if not only_available or b.available]
        return sorted(books, key=lambda b: b.title)
```

---

## 💡 思考题

1. Python 中为什么需要 `__new__` 和 `__init__` 两个方法？`__new__` 在什么场景下必须重写？
2. 如果 `__eq__` 没有定义，两个属性相同的对象用 `==` 比较会返回什么？为什么？
3. 类变量和实例变量在内存中是如何分布的？修改类变量会影响所有实例吗？
4. 设计模式中的「工厂模式」和普通类的 `__init__` 方法有什么区别？
5. 如果一个类没有定义 `__str__`，调用 `print(obj)` 会怎么样？底层是怎么 fallback 的？

---

## 📚 参考资源

- [Python 官方教程 — 类](https://docs.python.org/3/tutorial/classes.html)
- [Python 特殊方法文档](https://docs.python.org/3/reference/datamodel.html#special-method-names)
- [Real Python — OOP](https://realpython.com/python3-object-oriented-programming/)
- [Python 数据模型详解](https://docs.python.org/3/reference/datamodel.html)
