"""
Day 046 — 元类 基础用法：type() 动态创建类

本文件演示：
1. type() 查询对象类型
2. type() 三参数形式动态创建类
3. 动态添加方法和属性
4. type() 的本质原理
"""


# ============================================================
# 1. type() 查询对象类型
# ============================================================

x = 42
s = "hello"
lst = [1, 2, 3]

print("=== 1. type() 查询类型 ===")
print(f"type(42)        = {type(x)}")           # <class 'int'>
print(f"type('hello')   = {type(s)}")           # <class 'str'>
print(f"type([1,2,3])   = {type(lst)}")         # <class 'list'>
print(f"type(None)      = {type(None)}")         # <class 'NoneType'>
print(f"type(True)      = {type(True)}")         # <class 'bool'>


# ============================================================
# 2. type() 动态创建类
# ============================================================

print("\n=== 2. type() 动态创建类 ===")

# type(类名, 基类元组, 属性字典)
# 等价于: class MyClass: ...

def hello_method(self):
    return f"Hello from {self.name}!"

# 动态创建 Person 类
Person = type('Person', (object,), {
    'greet': hello_method,
    'species': 'human'
})

# 使用
p = Person()
p.name = "Alice"
print(p.greet())          # Hello from Alice!
print(p.species)          # human
print(f"Person 的类型: {type(Person)}")  # <class 'type'>


# ============================================================
# 3. 动态创建带继承的类
# ============================================================

print("\n=== 3. 动态创建带继承的类 ===")

class Animal:
    def __init__(self, name):
        self.name = name
    
    def speak(self):
        raise NotImplementedError

# 用 type() 创建继承 Animal 的 Dog 类
Dog = type('Dog', (Animal,), {
    'speak': lambda self: f"{self.name} says: Woof!",
    'legs': 4
})

# 用 type() 创建继承 Animal 的 Cat 类
Cat = type('Cat', (Animal,), {
    'speak': lambda self: f"{self.name} says: Meow!",
    'color': 'black'
})

dog = Dog("Rex")
cat = Cat("Kitty")

print(dog.speak())          # Rex says: Woof!
print(cat.speak())          # Kitty says: Meow!
print(f"Dog 有 {dog.legs} 条腿")  # Dog 有 4 条腿
print(f"Cat 的颜色: {cat.color}")  # Cat 的颜色: black


# ============================================================
# 4. 动态添加方法
# ============================================================

print("\n=== 4. 动态添加方法 ===")

def run_method(self, distance):
    return f"{self.name} 跑了 {distance} 米"

def eat_method(self, food):
    return f"{self.name} 在吃 {food}"

# 给 Dog 类动态添加方法
Dog.run = run_method
Dog.eat = eat_method

print(dog.run(100))    # Rex 跑了 100 米
print(dog.eat("骨头"))  # Rex 在吃 骨头


# ============================================================
# 5. 验证 type() 的本质
# ============================================================

print("\n=== 5. type() 的本质 ===")
print(f"type(type)          = {type(type)}")           # <class 'type'>
print(f"type(type) is type  = {type(type) is type}")   # True
print(f"type(Dog)           = {type(Dog)}")             # <class 'type'>
print(f"type(dog)           = {type(dog)}")             # <class 'Dog'>
print()

# type 是它自己的实例！
# 这是 Python 对象模型的一个巧妙设计
# type 既是类（可以创建其他类），也是自身的实例


# ============================================================
# 6. 动态创建类的实战：根据配置生成类
# ============================================================

print("\n=== 6. 实战：根据配置动态生成类 ===")

config = {
    'classes': {
        'Student': {
            'fields': ['name', 'age', 'grade'],
            'methods': {
                'introduce': "lambda self: f'我是 {self.name}，{self.age} 岁，{self.grade} 年级'"
            }
        },
        'Teacher': {
            'fields': ['name', 'subject'],
            'methods': {
                'teach': "lambda self: f'{self.name} 老师正在教 {self.subject}'"
            }
        }
    }
}

generated_classes = {}

for cls_name, cls_config in config['classes'].items():
    attrs = {}
    
    # 添加字段（默认为 None）
    for field in cls_config['fields']:
        attrs[field] = None
    
    # 添加方法
    for method_name, method_code in cls_config['methods'].items():
        attrs[method_name] = eval(method_code)
    
    # 动态创建类
    generated_classes[cls_name] = type(cls_name, (object,), attrs)

# 使用生成的类
Student = generated_classes['Student']
Teacher = generated_classes['Teacher']

s = Student()
s.name = "小明"
s.age = 15
s.grade = "初三"
print(s.introduce())  # 我是 小明，15 岁，初三 年级

t = Teacher()
t.name = "王"
t.subject = "数学"
print(t.teach())  # 王 老师正在教 数学

print("\n✅ 所有测试通过！")
