"""
Day 037 — 组合与聚合：基础用法
===============================

涵盖：
1. 组合（Composition）基本模式
2. 聚合（Aggregation）基本模式
3. 组合 vs 聚合 生命周期对比
4. 继承 vs 组合 对比
5. 依赖注入基础
"""


# ====================================
# 1. 组合（Composition）基本模式
# ====================================
print("=" * 60)
print("1️⃣ 组合（Composition）基本模式")
print("=" * 60)


class Author:
    """作者信息"""

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def __repr__(self):
        return f"Author({self.name}, {self.email})"


class Chapter:
    """章节"""

    def __init__(self, title: str, content: str):
        self.title = title
        self.content = content
        self.pages = len(content) // 1000 + 1

    def __repr__(self):
        return f"Chapter({self.title}, {self.pages}p)"


class Book:
    """书籍 —— 组合：Author 和 Chapter 的生命周期由 Book 管理"""

    def __init__(self, title: str, author_name: str, author_email: str):
        self.title = title
        # ⭐ 组合：在构造器中创建依赖对象
        self.author = Author(author_name, author_email)
        self.chapters: list[Chapter] = []
        self._is_published = False

    def add_chapter(self, title: str, content: str):
        """添加章节（组合对象由 Book 创建）"""
        chapter = Chapter(title, content)
        self.chapters.append(chapter)
        return chapter

    def publish(self):
        self._is_published = True

    @property
    def total_pages(self) -> int:
        return sum(c.pages for c in self.chapters)

    @property
    def is_published(self) -> bool:
        return self._is_published

    def __repr__(self):
        return (f"Book({self.title} by {self.author.name}, "
                f"{len(self.chapters)} chapters)")


book = Book("Python 编程实战", "张三", "zhang@example.com")
book.add_chapter("入门", "Python 是一门...")
book.add_chapter("进阶", "Python 的高级特性...")
book.add_chapter("项目实战", "让我们做一个...")

print(f"  书籍信息: {book}")
print(f"  作者: {book.author}")
print(f"  总页数: {book.total_pages}")

# 组合关系：删除 Book 后，Author 和 Chapter 也不复存在
del book
# print(book)  # ❌ NameError


# ====================================
# 2. 聚合（Aggregation）基本模式
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 聚合（Aggregation）基本模式")
print("=" * 60)


class Student:
    """学生 —— 可以独立于班级存在"""

    def __init__(self, name: str, student_id: str):
        self.name = name
        self.student_id = student_id
        self.courses: list[str] = []

    def enroll(self, course: str):
        self.courses.append(course)

    def __repr__(self):
        return f"Student({self.name}, {self.student_id})"


class Course:
    """课程 —— 可以独立于班级存在"""

    def __init__(self, name: str, code: str, credits: int = 3):
        self.name = name
        self.code = code
        self.credits = credits

    def __repr__(self):
        return f"Course({self.name}, {self.code})"


class SchoolClass:
    """班级 —— 聚合：学生和课程可以从外部传入"""

    def __init__(self, name: str):
        self.name = name
        self.students: list[Student] = []   # 聚合：从外部添加
        self.courses: list[Course] = []     # 聚合：从外部添加

    def add_student(self, student: Student):
        """添加学生（聚合 — 学生对象已经存在于外部）"""
        self.students.append(student)

    def add_course(self, course: Course):
        """添加课程（聚合 — 课程对象已经存在于外部）"""
        self.courses.append(course)

    def remove_student(self, student: Student):
        """移除学生（但学生对象继续存在）"""
        if student in self.students:
            self.students.remove(student)

    def list_students(self):
        return [s.name for s in self.students]

    def list_courses(self):
        return [c.name for c in self.courses]

    def total_credits(self):
        return sum(c.credits for c in self.courses)


# 创建独立的学生对象
alice = Student("Alice", "S001")
bob = Student("Bob", "S002")
charlie = Student("Charlie", "S003")

# 创建独立的课程对象
python = Course("Python 编程", "CS101", 4)
math = Course("高等数学", "MATH101", 5)
english = Course("大学英语", "ENG101", 3)

# 创建班级，聚合学生和课程
class_a = SchoolClass("软件工程 2026-1")
class_a.add_student(alice)
class_a.add_student(bob)
class_a.add_student(charlie)
class_a.add_course(python)
class_a.add_course(math)
class_a.add_course(english)

print(f"  班级: {class_a.name}")
print(f"  学生: {class_a.list_students()}")
print(f"  课程: {class_a.list_courses()}")
print(f"  总学分: {class_a.total_credits()}")

# ⭐ 聚合：删除班级后，学生和课程仍然存在
del class_a
print(f"  删除班级后，学生仍存在:")
print(f"    {alice}")
print(f"    {bob}")
print(f"  课程仍存在: {python}")


# ====================================
# 3. 组合 vs 聚合 生命周期对比
# ====================================
print("\n" + "=" * 60)
print("3️⃣ 组合 vs 聚合 生命周期对比")
print("=" * 60)


class Component:
    """组合中的部件 —— 随整体创建和销毁"""

    def __init__(self, name: str, owner: str):
        self.name = name
        self.owner = owner
        print(f"    🏗️  [{owner}] 创建部件: {name}")

    def __del__(self):
        print(f"    💥 [{self.owner}] 销毁部件: {self.name}")


class AggregateItem:
    """聚合中的物品 —— 可独立存在"""

    def __init__(self, name: str):
        self.name = name
        print(f"    📦 创建物品: {name}")

    def __del__(self):
        print(f"    🗑️ 销毁物品: {self.name}")


class Container:
    """容器 —— 展示组合和聚合的生命周期区别"""

    def __init__(self, name: str, item: AggregateItem):
        self.name = name
        # 组合：部件在构造器中创建
        self.part = Component(f"部件-1", name)
        # 聚合：物品从外部传入
        self.item = item
        print(f"    📀 [{name}] 容器创建完成")

    def __del__(self):
        print(f"    💿 [{self.name}] 容器销毁")


print("\n  创建容器...")
agg_item = AggregateItem("外部物品")
container = Container("主容器", agg_item)

print("\n  删除容器引用...")
del container
print("  容器已删除")

print("\n  外部物品仍然存在:")
print(f"    {agg_item.name}")
del agg_item
print("  外部物品也删除了")


# ====================================
# 4. 继承 vs 组合 对比
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 继承 vs 组合 对比")
print("=" * 60)


# ❌ 使用继承
class Animal:
    """动物基类"""

    def eat(self):
        return "吃东西"

    def sleep(self):
        return "睡觉"

    def fly(self):
        return "飞行"  # ❌ 不是所有动物都会飞


class Dog(Animal):
    def fly(self):
        raise NotImplementedError("狗不会飞！")  # ❌ 违反 LSP


class Fish(Animal):
    def fly(self):
        raise NotImplementedError("鱼不会飞！")  # ❌


print("  ❌ 继承方式的问题:")
print(f"  狗需要继承 fly() → 但狗不会飞")


# ✅ 使用组合
class Eatable:
    """吃东西的行为"""
    def eat(self): return "品尝食物"


class Sleepable:
    """睡觉的行为"""
    def sleep(self): return "进入梦乡"


class Flyable:
    """飞行的行为"""
    def fly(self): return "展翅高飞"


class Swimmable:
    """游泳的行为"""
    def swim(self): return "自由游动"


class GoodDog:
    """狗 —— 组合需要的功能"""
    def __init__(self):
        self.eat_behavior = Eatable()
        self.sleep_behavior = Sleepable()

    def eat(self): return self.eat_behavior.eat()
    def sleep(self): return self.sleep_behavior.sleep()


class Bird:
    """鸟 —— 组合不同的功能"""
    def __init__(self):
        self.eat_behavior = Eatable()
        self.sleep_behavior = Sleepable()
        self.fly_behavior = Flyable()

    def eat(self): return self.eat_behavior.eat()
    def sleep(self): return self.sleep_behavior.sleep()
    def fly(self): return self.fly_behavior.fly()


class Fish:
    """鱼 —— 组合不同的功能"""
    def __init__(self):
        self.eat_behavior = Eatable()
        self.sleep_behavior = Sleepable()
        self.swim_behavior = Swimmable()

    def eat(self): return self.eat_behavior.eat()
    def sleep(self): return self.sleep_behavior.sleep()
    def swim(self): return self.swim_behavior.swim()


dog = GoodDog()
bird = Bird()
fish = Fish()

print("\n  ✅ 组合方式:")
print(f"  狗: {dog.eat()}, {dog.sleep()}")
print(f"  鸟: {bird.eat()}, {bird.sleep()}, {bird.fly()}")
print(f"  鱼: {fish.eat()}, {fish.sleep()}, {fish.swim()}")
print(f"  ✅ 没有不会飞的方法，每个类只组合自己需要的功能")


# ====================================
# 5. 依赖注入基础
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 依赖注入基础")
print("=" * 60)


# ❌ 紧耦合 —— 类自己创建依赖
class FileLogger:
    """文件日志器"""

    def log(self, message: str):
        print(f"  [FileLogger] {message}")


class TightlyCoupledService:
    """紧耦合服务 —— 直接创建依赖"""

    def __init__(self):
        self.logger = FileLogger()  # ❌ 硬编码

    def do_work(self):
        self.logger.log("开始工作")


# ✅ 松耦合 —— 依赖从外部注入
class ConsoleLogger:
    """控制台日志器"""

    def log(self, message: str):
        print(f"  [ConsoleLogger] {message}")


class DatabaseLogger:
    """数据库日志器"""

    def log(self, message: str):
        print(f"  [DatabaseLogger] 写入数据库: {message}")


class LooselyCoupledService:
    """松耦合服务 —— 依赖注入"""

    def __init__(self, logger):
        """构造器注入"""
        self.logger = logger

    def do_work(self):
        self.logger.log("开始工作")


# 测试时注入不同的依赖
print("\n  依赖注入演示:")

# 生产环境：使用文件日志
service = LooselyCoupledService(FileLogger())
service.do_work()

# 测试环境：使用控制台日志
test_service = LooselyCoupledService(ConsoleLogger())
test_service.do_work()

# 开发环境：使用数据库日志
dev_service = LooselyCoupledService(DatabaseLogger())
dev_service.do_work()
