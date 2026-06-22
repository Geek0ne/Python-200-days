# Day 031 — 类与对象：完成清单与练习题

## ✅ 完成清单

### 概念理解
- [ ] 理解面向对象编程的三大特征（封装、继承、多态）
- [ ] 理解类与对象的区别与关系
- [ ] 理解 `__init__` 构造方法的作用
- [ ] 理解 `__new__` 与 `__init__` 的区别
- [ ] 理解 `self` 参数的含义
- [ ] 理解类变量与实例变量的区别
- [ ] 理解特殊方法（Magic Methods）的用途

### Python 实现
- [ ] 能够使用 `class` 关键字定义类
- [ ] 能够实现 `__init__` 构造方法
- [ ] 能够定义和调用实例方法
- [ ] 能够使用类变量和实例变量
- [ ] 能够实现 `__str__` 和 `__repr__`
- [ ] 能够实现 `__eq__` 和 `__lt__` 等比较方法
- [ ] 能够实现链式调用（返回 self）

### 代码实践
- [ ] 运行 `01-basic-usage.py` 理解类的基础用法
- [ ] 运行 `02-advanced-usage.py` 掌握进阶特性
- [ ] 运行 `03-practical.py` 完成图书管理系统
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 练习 1：实现一个 Counter 类

```python
"""
实现一个计数器类 Counter，支持：
- count(): 返回当前计数
- increment(n=1): 增加计数
- decrement(n=1): 减少计数
- reset(): 重置为 0
- __str__: 显示当前计数值
- 支持链式调用
"""
class Counter:
    # 你的代码
    pass

# 测试
c = Counter()
c.increment(5).decrement(2).increment(3)
print(c)  # → 计数: 6
print(c.count())  # → 6
c.reset()
print(c)  # → 计数: 0
```

### 练习 2：实现一个 Rectangle 类

```python
"""
实现矩形类 Rectangle，支持：
- __init__(self, width, height)
- area(): 返回面积
- perimeter(): 返回周长
- __str__ 和 __repr__
- __eq__: 面积相等即相等
- __lt__: 按面积比较
- __add__: 两个矩形的面积相加
"""
class Rectangle:
    # 你的代码
    pass

# 测试
r1 = Rectangle(3, 4)
r2 = Rectangle(2, 6)
r3 = Rectangle(3, 4)

print(f"r1 面积: {r1.area()}")  # → 12
print(f"r1 == r3: {r1 == r3}")  # → True
print(f"r1 < r2: {r1 < r2}")    # → False (12 < 12?)
print(f"r1 + r2: {r1 + r2}")    # → 24
```

### 练习 3：实现一个 Student 成绩管理系统

```python
"""
实现学生类 Student 和成绩管理类 GradeManager。

Student:
  - name, scores (dict, 科目→分数)
  - add_score(subject, score)
  - average(): 平均分
  - __str__: 显示学生信息和平均分

GradeManager:
  - students: list
  - add_student(student)
  - top_student(n=1): 前 n 名
  - subject_average(subject): 某科平均分
  - class_average(): 全班平均
"""
class Student:
    # 你的代码
    pass

class GradeManager:
    # 你的代码
    pass

# 测试
s1 = Student("Alice")
s1.add_score("语文", 90)
s1.add_score("数学", 85)
s1.add_score("英语", 92)

s2 = Student("Bob")
s2.add_score("语文", 88)
s2.add_score("数学", 95)
s2.add_score("英语", 78)

gm = GradeManager()
gm.add_student(s1)
gm.add_student(s2)
print(gm.class_average())  # → (90+85+92+88+95+78)/6 ≈ 88.0
```

### 练习 4：实现一个 Stack 类

```python
"""
用面向对象的方式实现栈（Stack）。
除了基本的 push/pop/peek，还要支持：
- __len__: len(stack)
- __bool__: 非空为 True
- __iter__: 支持 for 循环（从栈顶到栈底）
- __repr__: 快速查看内容
"""
class Stack:
    # 你的代码
    pass

# 测试
s = Stack()
s.push(1)
s.push(2)
s.push(3)
print(len(s))  # → 3
print(bool(s))  # → True
for item in s:
    print(item)  # → 3, 2, 1（每行一个）
print(s)  # → Stack([3, 2, 1])
```

### 练习 5：实现一个有限缓存（LRU 风格）

```python
"""
实现一个简单的缓存类 Cache。
- __init__(self, max_size): 最大容量
- put(self, key, value): 添加缓存
- get(self, key): 获取缓存，不存在返回 None
- 达到 max_size 时，移除最早添加的项
- __len__: 缓存项数
"""
class Cache:
    # 你的代码
    pass

# 测试
cache = Cache(3)
cache.put("a", 1)
cache.put("b", 2)
cache.put("c", 3)
print(cache.get("a"))  # → 1
cache.put("d", 4)  # 移除 b（最早添加且未访问）
print(cache.get("b"))  # → None
print(len(cache))  # → 3
```

---

## 📊 自评表

| 技能 | 初学者 | 理解 | 掌握 | 熟练 |
|------|--------|------|------|------|
| 类定义与实例化 | ☐ | ☐ | ☐ | ☐ |
| __init__ 构造方法 | ☐ | ☐ | ☐ | ☐ |
| self 参数理解 | ☐ | ☐ | ☐ | ☐ |
| 实例方法 | ☐ | ☐ | ☐ | ☐ |
| 类变量 vs 实例变量 | ☐ | ☐ | ☐ | ☐ |
| __str__ / __repr__ | ☐ | ☐ | ☐ | ☐ |
| __eq__ / __lt__ | ☐ | ☐ | ☐ | ☐ |
| 链式调用 | ☐ | ☐ | ☐ | ☐ |
| 面向对象设计原则 | ☐ | ☐ | ☐ | ☐ |

---

## 🔗 参考资源

- [Python 官方教程 — 类](https://docs.python.org/3/tutorial/classes.html)
- [Python 数据模型](https://docs.python.org/3/reference/datamodel.html)
- [Real Python — OOP in Python](https://realpython.com/python3-object-oriented-programming/)
- [Python __slots__ 文档](https://docs.python.org/3/reference/datamodel.html#slots)
- [Python 抽象基类](https://docs.python.org/3/library/abc.html)
