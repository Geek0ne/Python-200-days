# Day 069 — ORM 深入：SQLAlchemy 对象关系映射

## 概述

Day 068 我们学习了直接用 SQL 操作数据库。但每次写 SQL 字符串很繁琐，而且容易出错。今天学习 **ORM（Object-Relational Mapping）**——让 Python 对象和数据库表自动映射，用面向对象的方式操作数据库。

**SQLAlchemy** 是 Python 最强大的 ORM 框架，Day 066 在 Flask 中简单用过，今天深入学习它的完整功能。

**今天你将学到：**
1. ORM 原理与架构——理解 SQLAlchemy 的分层设计
2. 模型定义与关系映射——一对多、多对多
3. 查询 API 与高级用法——过滤、排序、分组、子查询
4. **实战：电商数据模型**——商品、订单、用户的完整关系

> 💡 **为什么学 ORM？** ORM 让你用 Python 类操作数据库，自动处理 SQL 生成、类型转换、关系管理。但理解底层 SQL 同样重要——ORM 生成的 SQL 不一定最优。

---

## 1. ORM 原理与架构

### 1.1 什么是 ORM？

```
Python 对象  ←→  ORM 映射  ←→  数据库表

class User:
    name: str          ←→    users.name TEXT
    age: int           ←→    users.age INTEGER
    
user = User(name="张三", age=25)
# 自动生成: INSERT INTO users (name, age) VALUES ('张三', 25)
```

### 1.2 SQLAlchemy 2.0 架构

```
┌─────────────────────────────────────┐
│           应用层（ORM）              │
│   Session / Query / Model           │
├─────────────────────────────────────┤
│           核心层（Core）             │
│   Engine / Connection / SQL表达式    │
├─────────────────────────────────────┤
│           适配层（Dialect）          │
│   SQLite / PostgreSQL / MySQL       │
└─────────────────────────────────────┘
```

### 1.3 安装与配置

```bash
# 安装 SQLAlchemy
pip install sqlalchemy

# 如果需要特定数据库驱动
pip install psycopg2-binary  # PostgreSQL
pip install pymysql          # MySQL
# SQLite 不需要额外安装（Python 内置）
```

```python
# code/01-sqlalchemy-setup.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# 创建引擎——连接数据库
# SQLite: sqlite:///filename.db
# PostgreSQL: postgresql://user:pass@host/db
# MySQL: mysql+pymysql://user:pass@host/db
engine = create_engine("sqlite:///shop.db", echo=True)
# echo=True 会打印生成的 SQL（调试用）

# 创建会话工厂
SessionLocal = sessionmaker(bind=engine)

# 声明基类——所有模型继承它
class Base(DeclarativeBase):
    pass

# 使用示例
def get_db():
    """获取数据库会话（依赖注入用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

> ⚠️ **避坑指南**：SQLAlchemy 2.0 使用 `DeclarativeBase` 代替旧版的 `declarative_base()`。如果你看到旧教程用 `Base = declarative_base()`，那是 1.x 写法。

---

## 2. 模型定义

### 2.1 基础模型

```python
# code/02-model-definition.py
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """声明基类"""
    pass


class User(Base):
    """用户模型"""
    __tablename__ = "users"  # 表名

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    age = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    def __repr__(self):
        """友好打印"""
        return f"<User(id={self.id}, username='{self.username}')>"


class Post(Base):
    """文章模型"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    author_id = Column(Integer, ForeignKey("users.id"))
    # ForeignKey 建立与 users 表的关联

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}')>"


# 创建表
engine = create_engine("sqlite:///models_demo.db", echo=False)
Base.metadata.create_all(engine)
print("✅ 表创建成功")
```

### 2.2 常用字段类型速查

| SQLAlchemy 类型 | Python 类型 | 数据库类型 | 说明 |
|----------------|-------------|-----------|------|
| Integer | int | INTEGER | 整数 |
| String(n) | str | VARCHAR(n) | 变长字符串 |
| Text | str | TEXT | 长文本 |
| Float | float | FLOAT | 浮点数 |
| Boolean | bool | BOOLEAN | 布尔值 |
| DateTime | datetime | DATETIME | 日期时间 |
| Date | date | DATE | 日期 |
| Numeric | Decimal | DECIMAL | 精确数字 |
| JSON | dict | JSON | JSON 数据 |

### 2.3 字段约束

```python
Column(Integer, primary_key=True)     # 主键
Column(String(50), unique=True)       # 唯一
Column(String(50), nullable=False)    # 非空
Column(Integer, default=0)            # 默认值
Column(Integer, index=True)           # 创建索引
Column(Integer, autoincrement=True)   # 自增
Column(String(50), comment="用户名称")  # 注释
```

---

## 3. 关系映射

### 3.1 一对多关系（One-to-Many）

```python
# code/03-relationships.py
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    ForeignKey, Table
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session

class Base(DeclarativeBase):
    pass


# 多对多的关联表
student_course = Table(
    "student_course",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id")),
    Column("course_id", Integer, ForeignKey("courses.id")),
)


class Department(Base):
    """部门——一对多的"一"端"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # relationship 定义关系
    # back_populates="department" 在 Employee 中建立反向引用
    employees = relationship("Employee", back_populates="department")

    def __repr__(self):
        return f"<Department(name='{self.name}')>"


class Employee(Base):
    """员工——一对多的"多"端"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    salary = Column(Float, default=0)
    department_id = Column(Integer, ForeignKey("departments.id"))

    # 反向关系
    department = relationship("Department", back_populates="employees")

    def __repr__(self):
        return f"<Employee(name='{self.name}')>"


class Student(Base):
    """学生——多对多关系"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # 多对多关系
    courses = relationship("Course", secondary=student_course, back_populates="students")

    def __repr__(self):
        return f"<Student(name='{self.name}')>"


class Course(Base):
    """课程——多对多关系"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    credit = Column(Integer, default=1)

    # 多对多反向关系
    students = relationship("Student", secondary=student_course, back_populates="courses")

    def __repr__(self):
        return f"<Course(name='{self.name}')>"


# ========== 使用示例 ==========
def demo():
    engine = create_engine("sqlite:///relationship_demo.db", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 创建部门
        tech = Department(name="技术部")
        hr = Department(name="人事部")
        session.add_all([tech, hr])
        session.flush()  # 获取 ID

        # 创建员工并关联部门
        alice = Employee(name="Alice", salary=15000, department=tech)
        bob = Employee(name="Bob", salary=12000, department=tech)
        charlie = Employee(name="Charlie", salary=11000, department=hr)
        session.add_all([alice, bob, charlie])

        # 创建学生和课程（多对多）
        math = Course(name="数学", credit=4)
        python = Course(name="Python", credit=3)
        s1 = Student(name="张三", courses=[math, python])
        s2 = Student(name="李四", courses=[math])
        session.add_all([math, python, s1, s2])

        session.commit()

        # ========== 查询关系 ==========
        print("=== 技术部员工 ===")
        tech_dept = session.query(Department).filter_by(name="技术部").first()
        for emp in tech_dept.employees:
            print(f"  {emp.name} - ¥{emp.salary}")

        print("\n=== 张三的课程 ===")
        zhang = session.query(Student).filter_by(name="张三").first()
        for course in zhang.courses:
            print(f"  {course.name} ({course.credit}学分)")

        print("\n=== Python 课的学生 ===")
        py = session.query(Course).filter_by(name="Python").first()
        for student in py.students:
            print(f"  {student.name}")

        print("\n=== Alice 的部门 ===")
        alice_emp = session.query(Employee).filter_by(name="Alice").first()
        print(f"  {alice_emp.name} → {alice_emp.department.name}")


if __name__ == "__main__":
    demo()
```

### 3.2 关系类型速查

| 关系类型 | SQLAlchemy 写法 | 场景 |
|---------|----------------|------|
| 一对多 | `relationship()` + `ForeignKey` | 部门→员工 |
| 多对一 | `relationship()` + `ForeignKey` | 员工→部门（反向） |
| 多对多 | `relationship(secondary=关联表)` | 学生↔课程 |
| 一对一 | `relationship(uselist=False)` | 用户→个人资料 |

> ⚠️ **避坑指南**：`back_populates` 和 `backref` 都能建立反向关系，但推荐用 `back_populates`——更明确，类型检查更好。

---

## 4. 查询 API

### 4.1 基础查询

```python
# code/04-query-api.py
from sqlalchemy import create_engine, Column, Integer, String, Float, func
from sqlalchemy.orm import DeclarativeBase, Session

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    category = Column(String(50))
    price = Column(Float)
    stock = Column(Integer)

def demo():
    engine = create_engine("sqlite:///query_demo.db", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # 插入测试数据
        products = [
            Product(name="Python书", category="图书", price=59.9, stock=100),
            Product(name="Java书", category="图书", price=69.9, stock=50),
            Product(name="机械键盘", category="外设", price=299, stock=30),
            Product(name="鼠标", category="外设", price=99, stock=200),
            Product(name="显示器", category="外设", price=1999, stock=10),
            Product(name="Python进阶", category="图书", price=79.9, stock=80),
        ]
        session.add_all(products)
        session.commit()

        # ========== 基础查询 ==========
        print("=== 所有产品 ===")
        all_products = session.query(Product).all()
        for p in all_products:
            print(f"  {p.name} - ¥{p.price} (库存:{p.stock})")

        # ========== 条件过滤 ==========
        print("\n=== 图书类产品 ===")
        books = session.query(Product).filter(Product.category == "图书").all()
        for p in books:
            print(f"  {p.name} - ¥{p.price}")

        # 多条件过滤
        print("\n=== 价格在 100-500 之间 ===")
        filtered = session.query(Product).filter(
            Product.price >= 100,
            Product.price <= 500
        ).all()
        for p in filtered:
            print(f"  {p.name} - ¥{p.price}")

        # filter_by（按字段名过滤，更简洁）
        print("\n=== filter_by 用法 ===")
        results = session.query(Product).filter_by(category="图书").all()
        print(f"  图书数量: {len(results)}")

        # ========== 排序 ==========
        print("\n=== 按价格从高到低 ===")
        sorted_products = session.query(Product).order_by(Product.price.desc()).all()
        for p in sorted_products:
            print(f"  ¥{p.price:.0f} - {p.name}")

        # ========== 限制结果 ==========
        print("\n=== 最便宜的 3 个 ===")
        cheapest = session.query(Product).order_by(Product.price).limit(3).all()
        for p in cheapest:
            print(f"  ¥{p.price} - {p.name}")

        # ========== 获取单个对象 ==========
        print("\n=== first() vs one() vs one_or_none() ===")
        first = session.query(Product).filter_by(name="Python书").first()
        print(f"  first(): {first}")

        # one() 期望恰好一条结果
        # one_or_none() 期望 0 或 1 条

        # ========== 聚合查询 ==========
        print("\n=== 聚合统计 ===")
        # 总数
        total = session.query(func.count(Product.id)).scalar()
        print(f"  总产品数: {total}")

        # 平均价
        avg_price = session.query(func.avg(Product.price)).scalar()
        print(f"  平均价格: ¥{avg_price:.2f}")

        # 按分类统计
        print("\n=== 按分类统计 ===")
        category_stats = session.query(
            Product.category,
            func.count(Product.id),
            func.sum(Product.price)
        ).group_by(Product.category).all()
        for cat, count, total_price in category_stats:
            print(f"  {cat}: {count} 个, 总价 ¥{total_price:.0f}")

        # ========== exists 和 any ==========
        has_expensive = session.query(
            session.query(Product).filter(Product.price > 1000).exists()
        ).scalar()
        print(f"\n有超过 1000 元的产品: {has_expensive}")


if __name__ == "__main__":
    demo()
```

### 4.2 高级查询

```python
# ========== 子查询 ==========
# 查找价格高于平均价的产品
subquery = session.query(func.avg(Product.price)).scalar_subquery()
expensive = session.query(Product).filter(Product.price > subquery).all()

# ========== join 查询 ==========
# session.query(Employee).join(Department).filter(Department.name == "技术部")

# ========== 懒加载 vs 预加载 ==========
# 懒加载：访问关系属性时才查询（可能 N+1 问题）
employees = session.query(Employee).all()
for emp in employees:
    print(emp.department.name)  # 每次访问都查数据库！

# 预加载：一次性加载关联数据
from sqlalchemy.orm import joinedload
employees = session.query(Employee).options(joinedload(Employee.department)).all()
for emp in employees:
    print(emp.department.name)  # 不再查询数据库

# ========== 批量操作 ==========
# 批量插入
session.bulk_save_objects([Product(name="a"), Product(name="b")])

# 批量更新
session.query(Product).filter(Product.category == "图书").update(
    {"price": Product.price * 0.9}  # 打九折
)
session.commit()
```

---

## 5. Session 管理

### 5.1 Session 的生命周期

```
创建 Session → 添加/修改对象 → flush（写入数据库）→ commit（提交事务）→ 关闭 Session
```

```python
# code/05-session-management.py
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))

# ========== 方式 1：手动管理 ==========
engine = create_engine("sqlite:///session_demo.db")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

session = SessionLocal()
try:
    user = User(name="Alice")
    session.add(user)
    session.commit()
    print("✅ 添加成功")
except Exception:
    session.rollback()
    print("❌ 操作失败，已回滚")
finally:
    session.close()

# ========== 方式 2：with 语句（推荐） ==========
with Session(engine) as session:
    user = User(name="Bob")
    session.add(user)
    session.commit()  # 自动提交
# 离开 with 块自动关闭

# ========== 方式 3：FastAPI 依赖注入 ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 5.2 常见陷阱

```python
# ❌ 陷阱 1：在 Session 关闭后访问对象
session.close()
print(user.name)  # 可能报错（detached instance）

# ✅ 在关闭前完成所有操作

# ❌ 陷阱 2：忘记 commit
session.add(user)
session.close()  # 数据没有保存！

# ✅ 显式 commit
session.add(user)
session.commit()

# ❌ 陷阱 3：在循环中频繁 commit
for name in names:
    session.add(User(name=name))
    session.commit()  # 每次都 commit，性能差

# ✅ 批量添加后一次 commit
for name in names:
    session.add(User(name=name))
session.commit()  # 一次 commit
```

---

## 实战项目：电商数据模型

### 项目说明

构建一个完整的电商数据模型，包含：
- 用户（User）
- 商品（Product）
- 订单（Order）
- 订单项（OrderItem）
- 一对多、多对多关系
- 完整的查询功能

### 完整代码

```python
# code/06-ecommerce-model.py
"""
🛒 电商数据模型 —— 完整实战项目
功能：用户、商品、订单管理，关系映射，复杂查询
"""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Text, Boolean, DateTime, ForeignKey, func
)
from sqlalchemy.orm import (
    DeclarativeBase, relationship, Session, sessionmaker
)


# ========== 声明基类 ==========
class Base(DeclarativeBase):
    pass


# ========== 关联表 ==========
# 商品标签（多对多）
product_tags = __import__("sqlalchemy").Table(
    "product_tags",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


# ========== 模型定义 ==========

class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20))
    is_vip = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

    # 一个用户有多个订单
    orders = relationship("Order", back_populates="user")

    def __repr__(self):
        return f"<User(username='{self.username}')>"


class Category(Base):
    """商品分类"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    # 一个分类有多个商品
    products = relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category(name='{self.name}')>"


class Product(Base):
    """商品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)

    # 关系
    category = relationship("Category", back_populates="products")
    tags = relationship("Tag", secondary=product_tags, back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product(name='{self.name}', price={self.price})>"


class Tag(Base):
    """标签（多对多）"""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)

    products = relationship("Product", secondary=product_tags, back_populates="tags")

    def __repr__(self):
        return f"<Tag(name='{self.name}')>"


class Order(Base):
    """订单"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending")  # pending/paid/shipped/done
    total_amount = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关系
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order(id={self.id}, status='{self.status}')>"


class OrderItem(Base):
    """订单项（关联订单和商品）"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float)  # 下单时的价格（快照）

    # 关系
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(product_id={self.product_id}, qty={self.quantity})>"


# ========== 数据库操作 ==========

class EcommerceDB:
    """电商数据库管理器"""

    def __init__(self, db_path: str = "ecommerce.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def init_data(self):
        """初始化示例数据"""
        with self.get_session() as session:
            # 检查是否已有数据
            if session.query(User).count() > 0:
                print("ℹ️ 数据已存在，跳过初始化")
                return

            # 创建分类
            electronics = Category(name="电子产品")
            books = Category(name="图书")
            clothing = Category(name="服装")
            session.add_all([electronics, books, clothing])
            session.flush()

            # 创建标签
            hot = Tag(name="热销")
            new = Tag(name="新品")
            discount = Tag(name="打折")
            session.add_all([hot, new, discount])
            session.flush()

            # 创建商品
            products = [
                Product(name="iPhone 15", price=7999, stock=50,
                        category=electronics, tags=[hot]),
                Product(name="MacBook Pro", price=14999, stock=20,
                        category=electronics, tags=[hot, new]),
                Product(name="Python编程", price=59.9, stock=100,
                        category=books, tags=[hot, discount]),
                Product(name="三体", price=56, stock=80,
                        category=books, tags=[new]),
                Product(name="T恤", price=99, stock=200,
                        category=clothing, tags=[discount]),
            ]
            session.add_all(products)
            session.flush()

            # 创建用户
            alice = User(username="alice", email="alice@test.com", is_vip=True)
            bob = User(username="bob", email="bob@test.com")
            session.add_all([alice, bob])
            session.flush()

            # 创建订单
            order1 = Order(user=alice, status="paid", total_amount=8058.9)
            order2 = Order(user=bob, status="pending", total_amount=155.9)
            session.add_all([order1, order2])
            session.flush()

            # 创建订单项
            items = [
                OrderItem(order=order1, product=products[0], quantity=1,
                          unit_price=7999),
                OrderItem(order=order1, product=products[2], quantity=1,
                          unit_price=59.9),
                OrderItem(order=order2, product=products[2], quantity=1,
                          unit_price=59.9),
                OrderItem(order=order2, product=products[4], quantity=1,
                          unit_price=99),
            ]
            session.add_all(items)
            session.commit()
            print("✅ 示例数据初始化完成")

    def demo_queries(self):
        """演示各种查询"""
        with self.get_session() as session:
            # 1. 基础查询
            print("=" * 50)
            print("📦 所有商品：")
            for p in session.query(Product).all():
                print(f"  {p.name} - ¥{p.price} (库存:{p.stock})")

            # 2. 条件查询
            print("\n🔍 价格低于 100 的商品：")
            for p in session.query(Product).filter(Product.price < 100).all():
                print(f"  {p.name} - ¥{p.price}")

            # 3. 关联查询
            print("\n👤 Alice 的订单：")
            alice = session.query(User).filter_by(username="alice").first()
            for order in alice.orders:
                print(f"  订单 #{order.id} - ¥{order.total_amount} ({order.status})")
                for item in order.items:
                    print(f"    └─ {item.product.name} x{item.quantity}")

            # 4. 聚合查询
            print("\n📊 分类统计：")
            stats = session.query(
                Category.name,
                func.count(Product.id),
                func.avg(Product.price)
            ).join(Product).group_by(Category.id).all()
            for name, count, avg_price in stats:
                print(f"  {name}: {count} 个商品, 均价 ¥{avg_price:.2f}")

            # 5. 多对多查询
            print("\n🏷️ 带'热销'标签的商品：")
            hot_tag = session.query(Tag).filter_by(name="热销").first()
            for p in hot_tag.products:
                print(f"  {p.name} - ¥{p.price}")

            # 6. 排序 + 分页
            print("\n💰 商品价格排行榜（前 3）：")
            for p in session.query(Product).order_by(
                Product.price.desc()
            ).limit(3).all():
                print(f"  ¥{p.price:.0f} - {p.name}")

            # 7. 复杂过滤
            print("\n🛒 库存充足且价格 < 100 的商品：")
            for p in session.query(Product).filter(
                Product.stock > 50,
                Product.price < 100
            ).all():
                print(f"  {p.name} - ¥{p.price} (库存:{p.stock})")


# ========== 运行 ==========
if __name__ == "__main__":
    db = EcommerceDB()
    db.init_data()
    db.demo_queries()
```

---

## 今日总结

- **ORM 将数据库表映射为 Python 类**，用面向对象方式操作数据
- **SQLAlchemy 2.0** 使用 `DeclarativeBase` 定义模型，`Column` 定义字段
- **关系映射**：`relationship()` 建立表间关系，`ForeignKey` 定义外键
- **三种关系**：一对多（OneToMany）、多对一（ManyToOne）、多对多（ManyToMany）
- **查询 API**：`filter`/`filter_by` 过滤、`order_by` 排序、`limit` 限制
- **聚合查询**：`func.count`/`func.sum`/`func.avg` + `group_by`
- **Session 管理**：用 `with Session(engine)` 确保资源正确释放
- **性能优化**：`joinedload` 预加载解决 N+1 问题

## 练习题

### 练习 1：博客系统模型 ⭐⭐
设计一个博客系统的数据模型：
- User（用户）→ Post（文章）→ Comment（评论）
- Post 可以有多个 Tag（多对多）
- 实现功能：
  - 查询某用户的所有文章及评论数
  - 查询某标签下的所有文章
  - 查询最新 10 篇文章（含作者信息）

### 练习 2：图书馆管理系统 ⭐⭐⭐
设计一个图书馆数据模型：
- Book（图书）、Author（作者）、Category（分类）
- Book 和 Author 是多对多关系
- 实现功能：
  - 查询某作者的所有图书
  - 查询某分类下的图书数量
  - 查询借阅次数最多的 5 本书

### 练习 3：论坛系统 ⭐⭐⭐
设计一个论坛系统：
- User、Board（版块）、Thread（帖子）、Reply（回复）
- 实现功能：
  - 查询某版块的所有帖子（含回复数）
  - 查询某用户的所有帖子
  - 查询今日热门帖子（按回复数排序）

### 练习 4：数据迁移 ⭐⭐⭐⭐
编写一个 ORM 数据迁移脚本：
- 从旧数据库读取数据
- 转换为新模型格式
- 写入新数据库
- 记录迁移日志

### 练习 5：性能优化 ⭐⭐⭐⭐
对比以下查询方式的性能：
- 懒加载 vs 预加载（joinedload）
- 批量插入 vs 逐条插入
- 不同索引策略的查询速度
- 生成性能报告

## 明天预告

Day 070 将学习**测试基础**——unittest 框架、pytest 实战、Mock 与 Patch、测试覆盖率。我们将为 API 编写完整的测试套件！
