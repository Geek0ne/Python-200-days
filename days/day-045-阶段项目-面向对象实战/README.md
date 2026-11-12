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

**参考答案**

元类是「创建类的类」，它能在**类被定义的那一刻**拦截并加工类。ORM 需要它，是因为要支持那种声明式写法：

```python
class User(Model):
    id = IntegerField(primary_key=True)
    name = CharField(max_length=50)
```

用户只是把字段「摆」在类体里，框架却要在背后自动完成：扫描所有 `Field` 实例、收集成 `_fields` 字典、推导表名 `_table_name`。这些「在类创建时统一处理类属性」的活儿，正是元类 `ModelMeta.__new__` 的强项——它对用户完全透明，用户不必手动注册字段。

不用元类的替代方案：

- **`__init_subclass__` 钩子**：在 `Model` 里定义 `__init_subclass__(cls, **kw)`，子类定义时自动调用，同样能收集字段。比元类更轻量，是现代 Python 的首选替代。
- **类装饰器**：`@register_fields` 装饰在模型类上，显式触发字段收集。
- **手动注册/惰性扫描**：让用户显式写 `_fields = [...]`，或在第一次实例化时再扫描类属性。代价是失去「全自动」的便利。

💡 提示：元类功能强但难懂、易与多重继承冲突；若只是「子类创建时做点登记」，`__init_subclass__` 通常就够了，不必动元类。

2. **API 封装**：在 REST API 客户端中，为什么要使用 `requests.Session()` 而不是直接调用 `requests.get()`？

**参考答案**

`requests.Session()` 是一个「会记住状态、复用连接」的请求会话，相比每次裸调 `requests.get()` 有三大好处：

- **连接复用（性能）**：Session 内部维护连接池，对同一主机的多次请求复用底层 TCP 连接（HTTP keep-alive），省去反复握手/建连的开销。频繁调用 API 时速度提升明显。而 `requests.get()` 每次都临时建一个会话、用完即弃，连接无法复用。
- **跨请求保持状态**：Session 会自动保存并携带 Cookie，还能统一设置 headers。比如登录后的会话 Cookie、`Authorization: Bearer xxx` 认证头，设一次就对后续所有请求生效——这正是代码里 `self.session.headers['Authorization'] = ...` 的用意。
- **统一配置**：超时、代理、重试适配器等都能在 Session 上集中配置，所有请求一致，便于维护。

一句话：**裸 `requests.get` 适合「打一枪换一个地方」的零星请求；封装 API 客户端这种「对同一服务持续、带认证地发请求」的场景，Session 在性能和便利性上都更优。**

💡 提示：`requests` 是第三方库（需 `pip install requests`）。Session 不是线程安全的，多线程共享同一个 Session 时要留意；用完可用 `with requests.Session() as s:` 确保连接释放。

3. **继承选择**：在设计 `Model` 基类时，为什么不使用组合模式来实现字段管理？

**参考答案**

这里用继承是合理的，因为它属于「框架契约 + 真正的 is-a」那一类例外（参见 day-037 第 4 题），而非单纯为了复用代码：

- **框架要按类型识别模型**：ORM 需要把 `User`、`Article` 都当成「Model」统一调度（建表、查询、序列化）。继承让所有模型共享 `Model` 的身份，框架能用 `isinstance(obj, Model)` 识别、用统一接口处理。组合做不到这种「名义上的统一类型」。
- **元类依赖继承触发**：`ModelMeta` 是绑在 `Model` 上的元类，只有「继承 Model」的类才会经过它的加工，自动收集字段。若改成组合（每个类内部持有一个 field manager），就失去了「定义即注册」的声明式语法。
- **共享行为天然下沉**：`save / get / filter` 是所有模型共有的操作，放在基类里由子类继承最自然；用组合则每个模型都要持有一个管理器并逐个委托，样板代码更多。
- **用户体验**：`class User(Model): ...` 直观表达了「User 是一种模型」，符合直觉；组合写法会把这个关系藏起来，反而晦涩。

💡 提示：这不违背「组合优于继承」——该原则反对的是「为复用而滥用继承」。此处继承承载的是稳定的框架契约与多态识别，正是继承的适用场景。字段内部的「验证逻辑」倒可以委托给独立的 Field 对象（那部分其实就是组合）。

### 进阶题

4. **性能优化**：在 ORM 框架中，如何优化数据库查询性能？请列出至少 3 种优化策略。

**参考答案**

ORM 方便但容易掩盖低效查询，常见优化策略（任选其三即可，这里多列几种）：

- **只取需要的列，避免 `SELECT *`**：代码里 `get/filter` 都用 `SELECT *`，会把用不到的大字段（如长文本）也拉回来。提供 `.only('id', 'name')` 之类的投影，减少数据传输和内存。
- **建立合适的索引**：在经常出现在 `WHERE`、`JOIN`、`ORDER BY` 的列（如 `author_id`、`name`）上建索引，把全表扫描变成索引查找，这是收益最大的一招。
- **解决 N+1 查询**：取一批文章后再逐条查作者，会发出 N+1 条 SQL。用「预加载/急加载」（类似 Django 的 `select_related`/`prefetch_related`，一次 JOIN 或批量 IN 查询）把关联数据一并取回。
- **批量操作**：插入/更新大量记录时用 `bulk_insert`/`executemany`，一条语句搞定，而不是循环里逐条 `save()`。
- **分页与缓存**：大结果集分页（LIMIT/OFFSET 或游标）；对热点只读查询加结果缓存（带 TTL，见 day-039）。
- **连接池**：复用数据库连接，避免每次查询都建连。

💡 提示：优化前先「测量」——打开 SQL 日志或用 `EXPLAIN` 看执行计划，找到真正的慢查询再下手，避免凭感觉优化。

5. **设计模式**：REST API 客户端封装中使用了哪些设计模式？请举例说明。

**参考答案**

这个封装里至少能看到以下几种模式：

- **外观模式（Facade）**：`APIClient` 把「拼 URL、发请求、检查状态码、解析 JSON」这一整套繁琐流程，收敛成 `get/post/put/delete` 几个简单方法。调用方不用关心 HTTP 细节，正是「为复杂子系统提供简单入口」。
- **模板方法模式（Template Method）**：基类 `APIClient` 定好了请求的骨架（`_build_url` → 发请求 → `raise_for_status` → 返回 json），`UserAPI`/`ArticleAPI` 通过继承复用骨架，只填充各自的业务端点（`get_users`、`create_article`）。流程固定、细节可变。
- **装饰器模式（Decorator）**：`@retry(...)` 在不改动 `get` 本身代码的前提下，动态给它叠加了「失败重试」的能力，是典型的装饰器（这里用 Python 函数装饰器实现）。
- **继承实现的多态/里氏替换**：`UserAPI`、`ArticleAPI` 都是 `APIClient` 的子类，可以互相替换传给任何接受 `APIClient` 的代码。

一句话：**外观简化接口、模板方法固定流程、装饰器叠加横切能力（重试/日志/鉴权）**，三者配合让客户端既好用又易扩展。

6. **错误处理**：如何设计一个完善的 API 错误处理机制，包括重试、降级和告警？

**参考答案**

一个完善的机制要分三层，并且**先区分错误类型**：瞬时错误（网络抖动、超时、5xx、429 限流）值得重试；永久错误（4xx 参数错、401 未授权）重试无意义，应直接失败。

- **重试（Retry）**：只对瞬时错误重试，采用**指数退避 + 随机抖动**（每次等待时间翻倍并加一点随机，避免大量客户端同时重试造成「惊群」），并设最大次数与总超时。注意写操作要保证幂等（重复执行结果一致）才能安全重试。
- **降级（Fallback）**：重试仍失败时不要直接崩，给出兜底——返回缓存的旧数据、默认值，或切换到备用服务/简化功能，保证核心流程可用。配合「熔断器」：连续失败就暂时停止调用，过一会儿再试探恢复。
- **告警（Alert）**：记录结构化日志（请求、状态码、耗时），统计失败率/延迟指标，超过阈值就通知（邮件/IM/监控平台），让人能及时发现故障。

下面是一个「指数退避重试」的最小实现：

```python
import time

def retry(max_retries=3, delay=0.1, backoff=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except ConnectionError as e:      # 只对可重试的瞬时错误重试
                    if attempt == max_retries:
                        raise
                    print(f"第 {attempt} 次失败: {e}，{wait:.1f}s 后重试")
                    time.sleep(wait)
                    wait *= backoff               # 指数退避
        return wrapper
    return decorator

calls = {"n": 0}

@retry(max_retries=3, delay=0.1)
def fetch():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError("网络抖动")
    return "数据"

print(fetch())
print("总调用次数:", calls["n"])
```

预期输出：

```
第 1 次失败: 网络抖动，0.1s 后重试
第 2 次失败: 网络抖动，0.2s 后重试
数据
总调用次数: 3
```

前两次模拟网络抖动失败，等待时间从 0.1s 翻倍到 0.2s，第三次成功返回。真实项目里把 `ConnectionError` 换成具体的瞬时异常集合，并在最外层接上降级与告警即可。

⚠️ 注意：不要对所有异常无脑重试（如参数错误重试一万次也没用），也不要重试非幂等的写操作，否则可能重复下单/扣款。

### 开放题

7. **扩展思考**：如果要将这个简易 ORM 框架扩展为支持多种数据库（MySQL、PostgreSQL、SQLite），应该如何设计架构？

**参考答案**

核心思路是 **DIP（依赖反转）+ 策略/适配器**：把「与具体数据库相关的部分」抽象成一个后端接口，让上层模型只依赖抽象，具体数据库各写一个实现，运行时注入。这样新增数据库不用改模型层。

分层设计：

- **模型层（不变）**：`Model` / `Field` 保持声明式写法，不关心底层是哪种数据库。
- **后端抽象层**：定义 `DatabaseBackend` 抽象基类，约定 `connect()`、`execute(sql, params)`、以及 SQL 方言相关的能力（占位符风格、类型映射、自增主键写法等）。
- **具体后端（可扩展）**：`MySQLBackend`、`PostgreSQLBackend`、`SQLiteBackend` 各自实现接口，封装各自的驱动（如 pymysql、psycopg、sqlite3）和方言差异。
- **SQL 生成器/方言**：把 `_generate_insert_sql` 抽成独立的「方言」组件，因为不同数据库占位符不同（MySQL/SQLite 用 `%s`/`?`，PostgreSQL 用 `%s`，参数化方式有别），由后端提供对应方言。
- **装配/工厂**：用配置或工厂根据连接串选择并注入后端，例如 `Model.set_backend(SQLiteBackend("app.db"))`。

```text
User / Article (Model)
        │ 只依赖抽象
        ▼
  DatabaseBackend (ABC)  ◀── MySQLBackend
        ▲                ◀── PostgreSQLBackend
        │                ◀── SQLiteBackend
   注入具体后端 + 方言
```

💡 提示：务必用**参数化查询**（把值作为参数传给驱动）而不是字符串拼接 SQL，既防 SQL 注入，也让方言差异交给驱动处理。真实项目可直接借鉴 SQLAlchemy 的「Core（方言/引擎）+ ORM」分层。

8. **实际应用**：在实际项目中，你会如何选择使用 ORM 还是直接写 SQL？请说明理由。

**参考答案**

不是非此即彼，而是**按场景分工，多数项目两者混用**。

倾向用 ORM 的场景：

- **常规 CRUD 与业务建模**：增删改查、对象关系映射，ORM 用操作对象的方式表达，开发快、可读性好、与业务代码风格一致。
- **需要数据库可移植**：ORM 屏蔽方言差异，换数据库改动小。
- **安全与一致性**：ORM 默认参数化查询，天然防 SQL 注入；字段验证、事务管理也更省心。
- **团队协作与维护**：模型即文档，新人容易上手，重构有类型/IDE 支持。

倾向直接写 SQL 的场景：

- **复杂查询/报表分析**：多表 JOIN、窗口函数、聚合、CTE 等，ORM 表达起来别扭甚至生成低效 SQL，手写更直接可控。
- **性能敏感路径**：需要精确控制执行计划、批量操作、特定索引提示时，手写 SQL 更容易调优。
- **数据库特有特性**：用到某数据库的专属功能（如 PostgreSQL 的 JSONB、数组、地理扩展），ORM 未必支持。

我的选择：**以 ORM 为主干覆盖 80% 的日常操作，把复杂/高性能查询交给手写 SQL（或 ORM 提供的 raw SQL 接口）**，并用 `EXPLAIN`/慢查询日志验证性能。这样兼顾开发效率与运行效率，而不必在「全 ORM」或「全 SQL」之间二选一。

💡 提示：无论哪种方式，都要坚持参数化查询防注入；用 ORM 时警惕 N+1 和 `SELECT *`，用裸 SQL 时注意把查询集中管理、避免散落各处难以维护。

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