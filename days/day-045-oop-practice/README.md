# Day 045 — 阶段项目：面向对象实战

> 🎯 **学习目标**：综合运用 Phase 3 面向对象编程知识，通过两个实战项目巩固 OOP 核心概念

## 📚 目录

1. [项目概述](#项目概述)
2. [项目一：简易 ORM 框架](#项目一简易-orm-框架)
3. [项目二：REST API 客户端封装](#项目二rest-api-客户端封装)
4. [OOP 知识点回顾](#oop-知识点回顾)
5. [实战演练](#实战演练)
6. [思考题](#思考题)

---

## 项目概述

今天是 Phase 3 面向对象编程的收官之日。我们将通过两个完整的实战项目，把前 44 天学到的所有 OOP 知识点融会贯通。

### 项目价值

| 项目 | 技术点 | 实际应用 |
|------|--------|----------|
| 简易 ORM 框架 | 类、继承、元类、描述符、属性装饰器 | 数据库操作抽象化 |
| REST API 客户端封装 | 类、实例方法、类方法、静态方法、组合 | HTTP 请求管理 |

---

## 项目一：简易 ORM 框架

### 什么是 ORM？

ORM（Object-Relational Mapping，对象关系映射）是一种将数据库表映射为 Python 类的技术。通过 ORM，我们可以用操作对象的方式来操作数据库。

### 核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                      ORM 核心概念                            │
├─────────────────────────────────────────────────────────────┤
│  1. Model（模型类）→ 数据库表                                 │
│  2. Field（字段类）→ 数据库列                                 │
│  3. Field Value → 单元格数据                                  │
│  4. Method → 数据库操作                                      │
└─────────────────────────────────────────────────────────────┘
```

### 类结构设计

```python
# 用户定义的模型
class User(Model):
    id = IntegerField(primary_key=True)
    name = CharField(max_length=50)
    age = IntegerField()

# 底层自动完成：
# 1. 创建表结构
# 2. 数据验证
# 3. SQL 生成
# 4. 结果映射
```

### Field 字段类设计

```python
class Field:
    """字段基类"""
    def __init__(self, primary_key=False):
        self.primary_key = primary_key
        self.value = None

class CharField(Field):
    """字符串字段"""
    def __init__(self, max_length=100, **kwargs):
        super().__init__(**kwargs)
        self.max_length = max_length

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError(f"Expected str, got {type(value)}")
        if len(value) > self.max_length:
            raise ValueError(f"Length {len(value)} exceeds max {self.max_length}")
        return value

class IntegerField(Field):
    """整数字段"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def validate(self, value):
        if not isinstance(value, int):
            raise TypeError(f"Expected int, got {type(value)}")
        return value
```

### Model 基类设计

```python
class ModelMeta(type):
    """元类：自动处理字段映射"""
    def __new__(cls, name, bases, attrs):
        # 收集所有 Field 实例
        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                fields[key] = value

        # 存储到类属性
        attrs['_fields'] = fields
        attrs['_table_name'] = name.lower() + 's'

        return super().__new__(cls, name, bases, attrs)


class Model(metaclass=ModelMeta):
    """模型基类"""
    def __init__(self, **kwargs):
        # 设置字段值
        for field_name, field in self._fields.items():
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])
            else:
                setattr(self, field_name, None)

    def save(self):
        """保存到数据库"""
        # 验证所有字段
        for field_name, field in self._fields.items():
            value = getattr(self, field_name)
            if value is not None:
                field.validate(value)

        # 生成 SQL（示例）
        sql = self._generate_insert_sql()
        print(f"[SAVE] {sql}")
        return True

    def _generate_insert_sql(self):
        """生成 INSERT SQL"""
        fields = []
        values = []
        for field_name, field in self._fields.items():
            value = getattr(self, field_name)
            if value is not None:
                fields.append(field_name)
                if isinstance(value, str):
                    values.append(f"'{value}'")
                else:
                    values.append(str(value))

        return f"INSERT INTO {self._table_name} ({', '.join(fields)}) VALUES ({', '.join(values)})"

    @classmethod
    def get(cls, id):
        """获取单条记录"""
        sql = f"SELECT * FROM {cls._table_name} WHERE id = {id}"
        print(f"[GET] {sql}")
        return cls(id=id)

    @classmethod
    def filter(cls, **kwargs):
        """过滤查询"""
        conditions = [f"{k} = '{v}'" if isinstance(v, str) else f"{k} = {v}"
                     for k, v in kwargs.items()]
        sql = f"SELECT * FROM {cls._table_name} WHERE {' AND '.join(conditions)}"
        print(f"[FILTER] {sql}")
        return []
```

### 使用示例

```python
# 定义模型
class User(Model):
    id = IntegerField(primary_key=True)
    name = CharField(max_length=50)
    age = IntegerField()

class Article(Model):
    id = IntegerField(primary_key=True)
    title = CharField(max_length=200)
    content = CharField(max_length=2000)
    author_id = IntegerField()

# 创建实例
user = User(name="张三", age=25)
print(user.name)  # 张三

# 保存
user.save()
# [SAVE] INSERT INTO users (name, age) VALUES ('张三', 25)

# 查询
user = User.get(1)
# [GET] SELECT * FROM users WHERE id = 1

# 过滤
users = User.filter(name="张三")
# [FILTER] SELECT * FROM users WHERE name = '张三'
```

### ORM 进阶：关系映射

```python
class ForeignKey(Field):
    """外键字段"""
    def __init__(self, related_model, **kwargs):
        super().__init__(**kwargs)
        self.related_model = related_model

# 使用
class Article(Model):
    id = IntegerField(primary_key=True)
    title = CharField(max_length=200)
    author = ForeignKey(User)  # 外键关联

    @property
    def author_obj(self):
        """获取关联的作者对象"""
        return self.related_model.get(self.author_id)
```

---

## 项目二：REST API 客户端封装

### 什么是 REST API？

REST（Representational State Transfer）是一种 Web 服务架构风格。REST API 使用 HTTP 方法（GET、POST、PUT、DELETE）来操作资源。

### 类结构设计

```python
import requests
from typing import Any, Dict, Optional


class APIClient:
    """REST API 客户端基类"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        if api_key:
            self.session.headers['Authorization'] = f'Bearer {api_key}'

    def _build_url(self, endpoint: str) -> str:
        """构建完整 URL"""
        return f"{self.base_url}/{endpoint.lstrip('/')}"

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """GET 请求"""
        url = self._build_url(endpoint)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        """POST 请求"""
        url = self._build_url(endpoint)
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def put(self, endpoint: str, data: Optional[Dict] = None) -> Any:
        """PUT 请求"""
        url = self._build_url(endpoint)
        response = self.session.put(url, json=data)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str) -> bool:
        """DELETE 请求"""
        url = self._build_url(endpoint)
        response = self.session.delete(url)
        response.raise_for_status()
        return True
```

### 业务 API 封装

```python
class UserAPI(APIClient):
    """用户 API 封装"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def get_users(self, page: int = 1, limit: int = 10) -> list:
        """获取用户列表"""
        return self.get('/users', params={'page': page, 'limit': limit})

    def get_user(self, user_id: int) -> dict:
        """获取单个用户"""
        return self.get(f'/users/{user_id}')

    def create_user(self, name: str, email: str) -> dict:
        """创建用户"""
        return self.post('/users', data={'name': name, 'email': email})

    def update_user(self, user_id: int, **kwargs) -> dict:
        """更新用户"""
        return self.put(f'/users/{user_id}', data=kwargs)

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        return self.delete(f'/users/{user_id}')


class ArticleAPI(APIClient):
    """文章 API 封装"""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def get_articles(self, author_id: Optional[int] = None) -> list:
        """获取文章列表"""
        params = {}
        if author_id:
            params['author_id'] = author_id
        return self.get('/articles', params=params)

    def create_article(self, title: str, content: str, author_id: int) -> dict:
        """创建文章"""
        return self.post('/articles', data={
            'title': title,
            'content': content,
            'author_id': author_id
        })
```

### 错误处理与重试

```python
import time
from functools import wraps


def retry(max_retries=3, delay=1):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    print(f"Attempt {attempt + 1} failed: {e}")
                    time.sleep(delay)
        return wrapper
    return decorator


class APIClient:
    """增强的 API 客户端"""

    @retry(max_retries=3, delay=1)
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        """带重试的 GET 请求"""
        url = self._build_url(endpoint)
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
```

### 使用示例

```python
# 初始化客户端
user_api = UserAPI('https://api.example.com', api_key='your-api-key')

# 获取用户列表
users = user_api.get_users(page=1, limit=10)
print(f"获取到 {len(users)} 个用户")

# 创建用户
new_user = user_api.create_user('李四', 'lisi@example.com')
print(f"创建用户: {new_user}")

# 更新用户
updated = user_api.update_user(1, name='张三（已更新）')
print(f"更新成功: {updated}")

# 删除用户
deleted = user_api.delete_user(1)
print(f"删除结果: {deleted}")
```

---

## OOP 知识点回顾

### 1. 类与对象

```python
# 类定义
class Dog:
    species = "Canis familiaris"  # 类属性

    def __init__(self, name, age):
        self.name = name  # 实例属性
        self.age = age

    def bark(self):  # 实例方法
        return f"{self.name} says Woof!"

# 对象创建
dog = Dog("Buddy", 3)
print(dog.bark())  # Buddy says Woof!
```

### 2. 继承与多态

```python
class Animal:
    def speak(self):
        raise NotImplementedError

class Dog(Animal):
    def speak(self):
        return "Woof!"

class Cat(Animal):
    def speak(self):
        return "Meow!"

# 多态
animals = [Dog(), Cat()]
for animal in animals:
    print(animal.speak())  # Woof! Meow!
```

### 3. 封装

```python
class BankAccount:
    def __init__(self, balance=0):
        self.__balance = balance  # 私有属性

    @property
    def balance(self):
        """只读属性"""
        return self.__balance

    def deposit(self, amount):
        if amount > 0:
            self.__balance += amount
            return True
        return False

    def withdraw(self, amount):
        if 0 < amount <= self.__balance:
            self.__balance -= amount
            return True
        return False
```

### 4. 属性装饰器

```python
class Circle:
    def __init__(self, radius):
        self._radius = radius

    @property
    def radius(self):
        return self._radius

    @radius.setter
    def radius(self, value):
        if value < 0:
            raise ValueError("Radius cannot be negative")
        self._radius = value

    @property
    def area(self):
        return 3.14159 * self._radius ** 2

circle = Circle(5)
print(circle.area)  # 78.53975
circle.radius = 10
print(circle.area)  # 314.159
```

### 5. 静态方法与类方法

```python
class Date:
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day

    @classmethod
    def from_string(cls, date_string):
        """类方法：从字符串创建日期"""
        year, month, day = map(int, date_string.split('-'))
        return cls(year, month, day)

    @staticmethod
    def is_valid_date(year, month, day):
        """静态方法：验证日期有效性"""
        return 1 <= month <= 12 and 1 <= day <= 31

# 使用
date = Date.from_string("2024-01-15")
print(date.year)  # 2024

valid = Date.is_valid_date(2024, 13, 1)
print(valid)  # False
```

### 6. 魔术方法

```python
class Vector:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Vector({self.x}, {self.y})"

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __len__(self):
        return int((self.x**2 + self.y**2)**0.5)

v1 = Vector(1, 2)
v2 = Vector(3, 4)
print(v1 + v2)  # (4, 6)
print(repr(v1))  # Vector(1, 2)
```

### 7. 抽象基类

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        pass

    @abstractmethod
    def perimeter(self):
        pass

class Rectangle(Shape):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height

    def perimeter(self):
        return 2 * (self.width + self.height)

# shape = Shape()  # TypeError: Can't instantiate abstract class
rect = Rectangle(5, 3)
print(rect.area())  # 15
```

---

## 实战演练

### 综合案例：学生管理系统

```python
from abc import ABC, abstractmethod
from typing import List, Optional


class Person(ABC):
    """抽象基类：人员"""

    def __init__(self, name: str, age: int):
        self._name = name
        self._age = age

    @property
    def name(self) -> str:
        return self._name

    @property
    def age(self) -> int:
        return self._age

    @abstractmethod
    def get_role(self) -> str:
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}({self._name}, {self._age})"


class Student(Person):
    """学生类"""

    def __init__(self, name: str, age: int, student_id: str):
        super().__init__(name, age)
        self.student_id = student_id
        self.grades: dict = {}

    def get_role(self) -> str:
        return "Student"

    def add_grade(self, subject: str, score: float):
        """添加成绩"""
        if not 0 <= score <= 100:
            raise ValueError("Score must be between 0 and 100")
        self.grades[subject] = score

    def get_average(self) -> float:
        """计算平均分"""
        if not self.grades:
            return 0.0
        return sum(self.grades.values()) / len(self.grades)

    def is_passing(self) -> bool:
        """是否及格"""
        return self.get_average() >= 60


class Teacher(Person):
    """教师类"""

    def __init__(self, name: str, age: int, subject: str):
        super().__init__(name, age)
        self.subject = subject
        self.students: List[Student] = []

    def get_role(self) -> str:
        return "Teacher"

    def add_student(self, student: Student):
        """添加学生"""
        if student not in self.students:
            self.students.append(student)

    def remove_student(self, student: Student):
        """移除学生"""
        if student in self.students:
            self.students.remove(student)

    def get_student_count(self) -> int:
        """获取学生数量"""
        return len(self.students)


class Classroom:
    """班级类：组合模式"""

    def __init__(self, name: str):
        self.name = name
        self.teacher: Optional[Teacher] = None
        self.students: List[Student] = []

    def set_teacher(self, teacher: Teacher):
        """设置班主任"""
        self.teacher = teacher
        teacher.students = self.students

    def add_student(self, student: Student):
        """添加学生"""
        if student not in self.students:
            self.students.append(student)
            if self.teacher:
                self.teacher.add_student(student)

    def remove_student(self, student: Student):
        """移除学生"""
        if student in self.students:
            self.students.remove(student)
            if self.teacher:
                self.teacher.remove_student(student)

    def get_class_average(self) -> float:
        """计算班级平均分"""
        if not self.students:
            return 0.0
        total = sum(student.get_average() for student in self.students)
        return total / len(self.students)

    def get_passing_rate(self) -> float:
        """计算及格率"""
        if not self.students:
            return 0.0
        passing = sum(1 for student in self.students if student.is_passing())
        return passing / len(self.students) * 100

    def __repr__(self):
        return f"Classroom({self.name}, students={len(self.students)})"


# 使用示例
if __name__ == "__main__":
    # 创建学生
    student1 = Student("Alice", 20, "S001")
    student2 = Student("Bob", 21, "S002")
    student3 = Student("Charlie", 19, "S003")

    # 添加成绩
    student1.add_grade("Python", 95)
    student1.add_grade("Math", 88)
    student2.add_grade("Python", 78)
    student2.add_grade("Math", 82)
    student3.add_grade("Python", 60)
    student3.add_grade("Math", 55)

    # 创建教师
    teacher = Teacher("Mr. Smith", 35, "Python")

    # 创建班级
    classroom = Classroom("Python班")
    classroom.set_teacher(teacher)
    classroom.add_student(student1)
    classroom.add_student(student2)
    classroom.add_student(student3)

    # 输出信息
    print(classroom)
    print(f"班级平均分: {classroom.get_class_average():.2f}")
    print(f"及格率: {classroom.get_passing_rate():.1f}%")
    print(f"学生数量: {teacher.get_student_count()}")
```

### 输出结果

```
Classroom(Python班, students=3)
班级平均分: 76.33
及格率: 66.7%
学生数量: 3
```

---

## 思考题

### 基础题

1. **ORM 设计**：为什么 ORM 框架需要使用元类（metaclass）？如果不使用元类，有什么替代方案？

2. **API 封装**：在 REST API 客户端中，为什么要使用 `requests.Session()` 而不是直接调用 `requests.get()`？

3. **继承选择**：在设计 `Model` 基类时，为什么不使用组合模式来实现字段管理？

### 进阶题

4. **性能优化**：在 ORM 框架中，如何优化数据库查询性能？请列出至少 3 种优化策略。

5. **设计模式**：REST API 客户端封装中使用了哪些设计模式？请举例说明。

6. **错误处理**：如何设计一个完善的 API 错误处理机制，包括重试、降级和告警？

### 开放题

7. **扩展思考**：如果要将这个简易 ORM 框架扩展为支持多种数据库（MySQL、PostgreSQL、SQLite），应该如何设计架构？

8. **实际应用**：在实际项目中，你会如何选择使用 ORM 还是直接写 SQL？请说明理由。

---

## 📝 学习总结

### 今日收获

- ✅ 掌握了 ORM 框架的核心设计思想
- ✅ 理解了元类在 ORM 中的应用
- ✅ 学会了 REST API 客户端的封装方法
- ✅ 综合运用了类、继承、封装、多态等 OOP 概念
- ✅ 实践了抽象基类、属性装饰器、魔术方法等高级特性

### 核心要点

1. **ORM 框架**：通过元类自动处理字段映射，通过描述符实现数据验证
2. **API 客户端**：使用类封装 HTTP 请求，通过继承实现业务 API
3. **OOP 综合应用**：将理论知识转化为实际代码能力

### 下一步

Phase 3 面向对象编程到此结束。明天进入 Phase 4 高阶特性，我们将学习元类（Metaclass）的深入应用。

---

*📅 学习日期：2026-07-01*
*📖 课程进度：Day 045/100*
*🎯 阶段：Phase 3 — 面向对象编程（完成）*