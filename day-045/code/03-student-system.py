"""
Day 045 - 学生管理系统综合案例
综合运用 OOP 所有核心概念：类、继承、封装、多态、抽象基类、属性装饰器等
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime


class Person(ABC):
    """抽象基类：人员"""

    def __init__(self, name: str, age: int):
        self._name = name
        self._age = age
        self._created_at = datetime.now()

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        if not value or not value.strip():
            raise ValueError("Name cannot be empty")
        self._name = value.strip()

    @property
    def age(self) -> int:
        return self._age

    @age.setter
    def age(self, value: int):
        if value < 0 or value > 150:
            raise ValueError("Age must be between 0 and 150")
        self._age = value

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @abstractmethod
    def get_role(self) -> str:
        pass

    @abstractmethod
    def get_info(self) -> str:
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self._name}', age={self._age})"

    def __str__(self):
        return f"{self._name} ({self._age}岁)"


class Student(Person):
    """学生类"""

    def __init__(self, name: str, age: int, student_id: str, grade: str = "未分配"):
        super().__init__(name, age)
        self._student_id = student_id
        self._grade = grade
        self._grades: Dict[str, float] = {}
        self._attendance: List[bool] = []

    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def grade(self) -> str:
        return self._grade

    @grade.setter
    def grade(self, value: str):
        self._grade = value

    @property
    def grades(self) -> Dict[str, float]:
        return self._grades.copy()

    @property
    def average_score(self) -> float:
        """计算平均分"""
        if not self._grades:
            return 0.0
        return sum(self._grades.values()) / len(self._grades)

    @property
    def is_passing(self) -> bool:
        """是否及格"""
        return self.average_score >= 60

    @property
    def grade_level(self) -> str:
        """成绩等级"""
        avg = self.average_score
        if avg >= 90:
            return "优秀"
        elif avg >= 80:
            return "良好"
        elif avg >= 70:
            return "中等"
        elif avg >= 60:
            return "及格"
        else:
            return "不及格"

    def add_grade(self, subject: str, score: float):
        """添加成绩"""
        if not 0 <= score <= 100:
            raise ValueError("Score must be between 0 and 100")
        self._grades[subject] = score

    def remove_grade(self, subject: str):
        """删除成绩"""
        if subject in self._grades:
            del self._grades[subject]

    def record_attendance(self, present: bool):
        """记录出勤"""
        self._attendance.append(present)

    @property
    def attendance_rate(self) -> float:
        """出勤率"""
        if not self._attendance:
            return 100.0
        present_count = sum(self._attendance)
        return present_count / len(self._attendance) * 100

    def get_role(self) -> str:
        return "Student"

    def get_info(self) -> str:
        grades_str = ", ".join(f"{k}:{v}" for k, v in self._grades.items())
        return (f"学生: {self._name}, 学号: {self._student_id}, "
                f"班级: {self._grade}, 成绩: [{grades_str}], "
                f"平均分: {self.average_score:.1f}, 等级: {self.grade_level}")


class Teacher(Person):
    """教师类"""

    def __init__(self, name: str, age: int, subject: str, title: str = "讲师"):
        super().__init__(name, age)
        self._subject = subject
        self._title = title
        self._students: List[Student] = []
        self._teaching_classes: List[str] = []

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        valid_titles = ["助教", "讲师", "副教授", "教授"]
        if value not in valid_titles:
            raise ValueError(f"Title must be one of: {valid_titles}")
        self._title = value

    @property
    def student_count(self) -> int:
        return len(self._students)

    def add_student(self, student: Student):
        """添加学生"""
        if student not in self._students:
            self._students.append(student)

    def remove_student(self, student: Student):
        """移除学生"""
        if student in self._students:
            self._students.remove(student)

    def add_class(self, class_name: str):
        """添加教学班级"""
        if class_name not in self._teaching_classes:
            self._teaching_classes.append(class_name)

    def remove_class(self, class_name: str):
        """移除教学班级"""
        if class_name in self._teaching_classes:
            self._teaching_classes.remove(class_name)

    def get_role(self) -> str:
        return "Teacher"

    def get_info(self) -> str:
        return (f"教师: {self._name}, 职称: {self._title}, "
                f"科目: {self._subject}, 学生数: {self.student_count}")


class Classroom:
    """班级类：组合模式"""

    def __init__(self, name: str, max_capacity: int = 50):
        self._name = name
        self._max_capacity = max_capacity
        self._teacher: Optional[Teacher] = None
        self._students: List[Student] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def teacher(self) -> Optional[Teacher]:
        return self._teacher

    @property
    def students(self) -> List[Student]:
        return self._students.copy()

    @property
    def student_count(self) -> int:
        return len(self._students)

    @property
    def is_full(self) -> bool:
        return self.student_count >= self._max_capacity

    def set_teacher(self, teacher: Teacher):
        """设置班主任"""
        self._teacher = teacher
        # 将班级所有学生添加到教师
        for student in self._students:
            teacher.add_student(student)

    def add_student(self, student: Student) -> bool:
        """添加学生"""
        if self.is_full:
            print(f"班级 {self._name} 已满，无法添加学生")
            return False
        if student not in self._students:
            self._students.append(student)
            if self._teacher:
                self._teacher.add_student(student)
            return True
        return False

    def remove_student(self, student: Student) -> bool:
        """移除学生"""
        if student in self._students:
            self._students.remove(student)
            if self._teacher:
                self._teacher.remove_student(student)
            return True
        return False

    def get_class_average(self) -> float:
        """计算班级平均分"""
        if not self._students:
            return 0.0
        total = sum(student.average_score for student in self._students)
        return total / len(self._students)

    def get_passing_rate(self) -> float:
        """计算及格率"""
        if not self._students:
            return 0.0
        passing = sum(1 for student in self._students if student.is_passing)
        return passing / len(self._students) * 100

    def get_top_students(self, n: int = 5) -> List[Student]:
        """获取前 N 名学生"""
        return sorted(self._students, key=lambda s: s.average_score, reverse=True)[:n]

    def __repr__(self):
        return f"Classroom(name='{self._name}', students={self.student_count})"

    def __str__(self):
        teacher_name = self._teacher.name if self._teacher else "未分配"
        return (f"班级: {self._name}, 班主任: {teacher_name}, "
                f"学生数: {self.student_count}/{self._max_capacity}")


class School:
    """学校类：最外层组合"""

    def __init__(self, name: str):
        self._name = name
        self._classrooms: List[Classroom] = []
        self._teachers: List[Teacher] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def classroom_count(self) -> int:
        return len(self._classrooms)

    @property
    def teacher_count(self) -> int:
        return len(self._teachers)

    def add_classroom(self, classroom: Classroom):
        """添加班级"""
        if classroom not in self._classrooms:
            self._classrooms.append(classroom)

    def add_teacher(self, teacher: Teacher):
        """添加教师"""
        if teacher not in self._teachers:
            self._teachers.append(teacher)

    def get_school_average(self) -> float:
        """计算学校平均分"""
        total_students = 0
        total_score = 0.0
        for classroom in self._classrooms:
            total_students += classroom.student_count
            total_score += classroom.get_class_average() * classroom.student_count
        if total_students == 0:
            return 0.0
        return total_score / total_students

    def get_school_passing_rate(self) -> float:
        """计算学校及格率"""
        total_students = 0
        passing_students = 0
        for classroom in self._classrooms:
            total_students += classroom.student_count
            passing_students += sum(1 for s in classroom.students if s.is_passing)
        if total_students == 0:
            return 0.0
        return passing_students / total_students * 100

    def get_statistics(self) -> dict:
        """获取学校统计信息"""
        total_students = sum(c.student_count for c in self._classrooms)
        return {
            "学校名称": self._name,
            "班级数量": self.classroom_count,
            "教师数量": self.teacher_count,
            "学生总数": total_students,
            "学校平均分": f"{self.get_school_average():.2f}",
            "学校及格率": f"{self.get_school_passing_rate():.1f}%"
        }

    def __repr__(self):
        return f"School(name='{self._name}')"

    def __str__(self):
        stats = self.get_statistics()
        return (f"学校: {stats['学校名称']}, "
                f"班级: {stats['班级数量']}, "
                f"教师: {stats['教师数量']}, "
                f"学生: {stats['学生总数']}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 045 - 学生管理系统综合案例")
    print("=" * 60)

    # 创建学校
    school = School("北京大学")

    # 创建教师
    teacher_python = Teacher("张老师", 35, "Python", "副教授")
    teacher_math = Teacher("李老师", 40, "数学", "教授")

    school.add_teacher(teacher_python)
    school.add_teacher(teacher_math)

    print("\n1. 创建教师")
    print("-" * 40)
    print(teacher_python.get_info())
    print(teacher_math.get_info())

    # 创建班级
    classroom1 = Classroom("Python一班", max_capacity=30)
    classroom2 = Classroom("Python二班", max_capacity=30)

    school.add_classroom(classroom1)
    school.add_classroom(classroom2)

    # 设置班主任
    classroom1.set_teacher(teacher_python)
    classroom2.set_teacher(teacher_python)

    print("\n2. 创建班级")
    print("-" * 40)
    print(classroom1)
    print(classroom2)

    # 创建学生
    students = [
        Student("Alice", 20, "S001", "Python一班"),
        Student("Bob", 21, "S002", "Python一班"),
        Student("Charlie", 19, "S003", "Python一班"),
        Student("David", 22, "S004", "Python一班"),
        Student("Eve", 20, "S005", "Python一班"),
        Student("Frank", 21, "S006", "Python二班"),
        Student("Grace", 20, "S007", "Python二班"),
    ]

    print("\n3. 创建学生")
    print("-" * 40)
    for student in students[:5]:
        classroom1.add_student(student)
    for student in students[5:]:
        classroom2.add_student(student)

    # 添加成绩
    print("\n4. 添加成绩")
    print("-" * 40)

    # 一班成绩
    students[0].add_grade("Python", 95)
    students[0].add_grade("数学", 88)
    students[0].add_grade("英语", 92)

    students[1].add_grade("Python", 78)
    students[1].add_grade("数学", 82)
    students[1].add_grade("英语", 75)

    students[2].add_grade("Python", 60)
    students[2].add_grade("数学", 55)
    students[2].add_grade("英语", 65)

    students[3].add_grade("Python", 85)
    students[3].add_grade("数学", 90)
    students[3].add_grade("英语", 88)

    students[4].add_grade("Python", 72)
    students[4].add_grade("数学", 68)
    students[4].add_grade("英语", 70)

    # 二班成绩
    students[5].add_grade("Python", 88)
    students[5].add_grade("数学", 92)
    students[5].add_grade("英语", 85)

    students[6].add_grade("Python", 95)
    students[6].add_grade("数学", 98)
    students[6].add_grade("英语", 96)

    # 显示学生成绩
    for student in students:
        print(student.get_info())

    # 记录出勤
    print("\n5. 记录出勤")
    print("-" * 40)
    students[0].record_attendance(True)
    students[0].record_attendance(True)
    students[0].record_attendance(True)
    students[0].record_attendance(False)
    students[0].record_attendance(True)

    print(f"Alice 出勤率: {students[0].attendance_rate:.1f}%")

    # 班级统计
    print("\n6. 班级统计")
    print("-" * 40)
    print(f"班级1平均分: {classroom1.get_class_average():.2f}")
    print(f"班级1及格率: {classroom1.get_passing_rate():.1f}%")
    print(f"班级1前3名:")
    for i, student in enumerate(classroom1.get_top_students(3), 1):
        print(f"  {i}. {student.name}: {student.average_score:.1f}分")

    print(f"\n班级2平均分: {classroom2.get_class_average():.2f}")
    print(f"班级2及格率: {classroom2.get_passing_rate():.1f}%")

    # 学校统计
    print("\n7. 学校统计")
    print("-" * 40)
    stats = school.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    # 教师信息
    print("\n8. 教师信息")
    print("-" * 40)
    print(teacher_python.get_info())
    print(f"教师学生数: {teacher_python.student_count}")

    print("\n" + "=" * 60)
    print("学生管理系统演示完成！")
    print("=" * 60)
