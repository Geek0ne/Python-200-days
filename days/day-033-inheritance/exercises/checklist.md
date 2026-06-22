# Day 033 — 继承：完成清单与练习题

## ✅ 完成清单

### 概念理解
- [ ] 理解继承的 is-a 关系
- [ ] 理解方法重写（Override）的概念
- [ ] 理解 super() 的工作原理（MRO 链）
- [ ] 理解 MRO（方法解析顺序）
- [ ] 理解 C3 线性化算法
- [ ] 理解菱形继承（钻石问题）的解决方式
- [ ] 理解 Mixin 模式及其适用场景
- [ ] 理解 isinstance vs type 的区别

### Python 实现
- [ ] 能够定义继承关系（class Child(Parent)）
- [ ] 能够重写父类方法
- [ ] 能够使用 super() 调用父类方法
- [ ] 能够查看和理解 __mro__
- [ ] 能够进行多重继承
- [ ] 能够实现 Mixin 类
- [ ] 能够使用 __init_subclass__

### 代码实践
- [ ] 运行 `01-basic-usage.py` 理解单继承和多态
- [ ] 运行 `02-advanced-usage.py` 掌握 MRO 和 Mixin
- [ ] 运行 `03-practical.py` 完成形状层次结构
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 练习 1：实现员工继承体系

```python
"""
实现员工继承体系：
- Employee: 基类 (name, salary, work())
- Manager: 继承 Employee (team_size, work() → "管理团队")
- Developer: 继承 Employee (language, work() → "写代码")
- Intern: 继承 Employee (mentor, work() → "学习")
- SalesPerson: 继承 Employee (quota, work() → "销售")

要求使用 super() 调用父类方法
"""
class Employee:
    def __init__(self, name, salary):
        self.name = name
        self.salary = salary

    def work(self):
        return f"{self.name} 在工作"

    def __str__(self):
        return f"{self.__class__.__name__}: {self.name} (${self.salary})"

class Manager(Employee):
    def __init__(self, name, salary, team_size):
        super().__init__(name, salary)
        self.team_size = team_size

    def work(self):
        return f"{super().work()} → 管理 {self.team_size} 人团队"

# 完成其他子类...
# 测试：
# mgr = Manager("Alice", 80000, 10)
# dev = Developer("Bob", 70000, "Python")
# print(mgr.work())  # → Alice 在工作 → 管理 10 人团队
# print(dev.work())  # → Bob 在工作 → 用 Python 写代码
```

### 练习 2：学校继承体系

```python
"""
实现学校人员继承体系：
- Person: 基类 (name, age)
- Student: 继承 Person (student_id, grades)
- Teacher: 继承 Person (subject, salary)
- TeachingAssistant: 继承 Student, Teacher (多继承, courses)

要求：
1. Student 和 Teacher 都继承 Person
2. TeachingAssistant 多重继承 Student 和 Teacher
3. 使用 super() 正确处理 MRO
4. TeachingAssistant 应该包含 student_id, grades, subject
"""
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def introduce(self):
        return f"我叫{self.name}，{self.age}岁"

class Student(Person):
    def __init__(self, name, age, student_id):
        super().__init__(name, age)
        self.student_id = student_id
        self.grades = []

    def introduce(self):
        return f"{super().introduce()}，学号{self.student_id}"

class Teacher(Person):
    # 你的代码
    pass

class TeachingAssistant(Student, Teacher):
    # 你的代码
    pass

# 测试
# ta = TeachingAssistant("张三", 22, "S2024001", "数据结构", ["CS101", "CS102"])
# print(ta.introduce())  # 正确显示身份
# print(TeachingAssistant.__mro__)  # 理解 MRO
```

### 练习 3：实现 DrawableMixin

```python
"""
实现图形绘制系统的 Mixin。
要求：
1. ColoredMixin: 添加颜色属性
2. BorderMixin: 添加边框样式
3. AnimatableMixin: 添加动画方法

与形状类组合使用
"""
class ColoredMixin:
    """颜色 Mixin"""
    def set_color(self, color):
        self.color = color
        return self

    def get_color(self):
        return getattr(self, 'color', 'black')

class BorderMixin:
    """边框 Mixin"""
    def set_border(self, style="solid", width=1):
        self.border_style = style
        self.border_width = width
        return self

    def get_border(self):
        style = getattr(self, 'border_style', 'none')
        width = getattr(self, 'border_width', 0)
        return f"{width}px {style}"

class AnimatableMixin:
    """动画 Mixin"""
    def animate(self, animation="fadeIn"):
        return f"🎬 播放 {animation} 动画"

# 组合使用
class DrawableCircle(ColoredMixin, BorderMixin, AnimatableMixin):
    def __init__(self, radius):
        self.radius = radius

    def draw(self):
        color = self.get_color()
        border = self.get_border()
        return f"🎨 绘制 {color} 圆形(r={self.radius}), 边框: {border}"

# 测试
# c = DrawableCircle(5)
# c.set_color("red").set_border("dashed", 2)
# print(c.draw())      # → 🎨 绘制 red 圆形(r=5), 边框: 2px dashed
# print(c.animate())   # → 🎬 播放 fadeIn 动画
```

### 练习 4：自定义异常继承体系

```python
"""
创建自定义异常继承体系：
- AppError: 基础异常
- ValidationError: 继承 AppError (字段名, 错误信息)
- AuthError: 继承 AppError (用户ID, 错误代码)
- NotFoundError: 继承 AppError (资源名, 资源ID)
- PermissionDeniedError: 继承 AuthError (所需权限)

要求：
1. 每个异常有额外的属性存储上下文信息
2. 使用 __str__ 返回详细的错误信息
3. 使用 try/except 按类型捕获
"""
class AppError(Exception):
    """应用基础异常"""
    def __init__(self, message, code="UNKNOWN"):
        super().__init__(message)
        self.code = code

    def __str__(self):
        return f"[{self.code}] {self.args[0]}"

# 完成子类...

# 测试
# try:
#     raise ValidationError("用户名不能为空", field="username")
# except ValidationError as e:
#     print(e)  # → [VALIDATION] 用户名不能为空 (field: username)
# except AppError as e:
#     print(f"应用错误: {e}")
```

### 练习 5：实现 Plugin 系统

```python
"""
使用 __init_subclass__ 实现一个插件系统。
- PluginBase: 基类，自动注册子类
- TextPlugin: 文本处理插件
  - UpperPlugin: 转大写
  - ReversePlugin: 反转
  - CapitalizePlugin: 首字母大写
- NumberPlugin: 数字处理插件
  - DoublePlugin: 乘以2
  - SquarePlugin: 平方

要求：
1. 插件注册到 PluginBase._registry
2. 支持启用/禁用插件
3. 可以按类别获取插件
"""
class PluginBase:
    _registry = {}
    _enabled = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # 自动注册
        name = cls.__name__
        PluginBase._registry[name] = cls
        PluginBase._enabled[name] = True

    def process(self, data):
        raise NotImplementedError

    @classmethod
    def get_enabled_plugins(cls):
        return {n: c for n, c in cls._registry.items()
                if cls._enabled.get(n, False)}

# 完成插件实现...

# 测试
# pipeline = DataPipeline([UpperPlugin(), ReversePlugin()])
# result = pipeline.run("hello")
# print(result)  # OLLEH
```

---

## 📊 自评表

| 技能 | 初学者 | 理解 | 掌握 | 熟练 |
|------|--------|------|------|------|
| 单继承 | ☐ | ☐ | ☐ | ☐ |
| 方法重写 | ☐ | ☐ | ☐ | ☐ |
| super() 调用 | ☐ | ☐ | ☐ | ☐ |
| MRO 理解 | ☐ | ☐ | ☐ | ☐ |
| 多重继承 | ☐ | ☐ | ☐ | ☐ |
| Mixin 模式 | ☐ | ☐ | ☐ | ☐ |
| isinstance vs type | ☐ | ☐ | ☐ | ☐ |
| __init_subclass__ | ☐ | ☐ | ☐ | ☐ |
| 抽象基类 | ☐ | ☐ | ☐ | ☐ |

---

## 🔗 参考资源

- [Python 官方教程 — 继承](https://docs.python.org/3/tutorial/classes.html#inheritance)
- [Python MRO 文档](https://www.python.org/download/releases/2.3/mro/)
- [super() considered super!](https://rhettinger.wordpress.com/2011/05/26/super-considered-super/)
- [Real Python — Supercharge Your Classes](https://realpython.com/python-super/)
- [Python abc — 抽象基类](https://docs.python.org/3/library/abc.html)
