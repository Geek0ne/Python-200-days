"""
Day 069 — 关系映射详解（一对多、多对多）
运行方式：python 03-relationships.py
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, ForeignKey, Table
)
from sqlalchemy.orm import DeclarativeBase, relationship, Session


class Base(DeclarativeBase):
    pass


# ========== 多对多关联表 ==========
student_course = Table(
    "student_course",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
)


# ========== 一对多关系 ==========

class Department(Base):
    """部门（一端）"""
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # 一个部门有多个员工
    employees = relationship("Employee", back_populates="department")

    def __repr__(self):
        return f"<Department(name='{self.name}')>"


class Employee(Base):
    """员工（多端）"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    salary = Column(Float, default=0)
    department_id = Column(Integer, ForeignKey("departments.id"))

    # 关联到部门
    department = relationship("Department", back_populates="employees")

    def __repr__(self):
        return f"<Employee(name='{self.name}')>"


# ========== 多对多关系 ==========

class Student(Base):
    """学生"""
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

    # 多对多：一个学生可以选多门课
    courses = relationship("Course", secondary=student_course, back_populates="students")

    def __repr__(self):
        return f"<Student(name='{self.name}')>"


class Course(Base):
    """课程"""
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    credit = Column(Integer, default=1)

    # 多对多反向
    students = relationship("Student", secondary=student_course, back_populates="courses")

    def __repr__(self):
        return f"<Course(name='{self.name}')>"


# ========== 一对一关系 ==========

class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))

    # 一对一
    profile = relationship("Profile", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(name='{self.name}')>"


class Profile(Base):
    """个人资料（一对一）"""
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    bio = Column(Text, default="")
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    user = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"<Profile(bio='{self.bio[:20]}...')>"


from sqlalchemy import Text


def demo():
    engine = create_engine("sqlite:///rel_demo.db", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # ========== 一对多 ==========
        print("=" * 50)
        print("🏢 一对多：部门 → 员工")

        tech = Department(name="技术部")
        hr = Department(name="人事部")
        session.add_all([tech, hr])
        session.flush()

        alice = Employee(name="Alice", salary=15000, department=tech)
        bob = Employee(name="Bob", salary=12000, department=tech)
        charlie = Employee(name="Charlie", salary=11000, department=hr)
        session.add_all([alice, bob, charlie])
        session.flush()

        # 从"一"端查"多"端
        print(f"\n技术部员工:")
        for emp in tech.employees:
            print(f"  {emp.name} - ¥{emp.salary}")

        # 从"多"端查"一"端
        print(f"\nAlice 的部门: {alice.department.name}")

        # ========== 多对多 ==========
        print("\n" + "=" * 50)
        print("📚 多对多：学生 ↔ 课程")

        math = Course(name="数学", credit=4)
        python = Course(name="Python", credit=3)
        english = Course(name="英语", credit=2)
        session.add_all([math, python, english])
        session.flush()

        s1 = Student(name="张三", courses=[math, python])
        s2 = Student(name="李四", courses=[math, english])
        s3 = Student(name="王五", courses=[python, english])
        session.add_all([s1, s2, s3])
        session.flush()

        print(f"\n张三的课程:")
        for course in s1.courses:
            print(f"  {course.name} ({course.credit}学分)")

        print(f"\nPython 课的学生:")
        for student in python.students:
            print(f"  {student.name}")

        # ========== 一对一 ==========
        print("\n" + "=" * 50)
        print("👤 一对一：用户 → 个人资料")

        u1 = User(name="alice")
        p1 = Profile(bio="Python 开发者，喜欢编程", user=u1)
        session.add_all([u1, p1])
        session.flush()

        print(f"\n用户: {u1.name}")
        print(f"资料: {u1.profile.bio}")

        session.commit()
        print("\n✅ 所有数据保存成功")


if __name__ == "__main__":
    demo()
