# Day 046 — 元类（Metaclass）练习清单

## ✅ 今日完成清单

- [ ] 理解"类也是对象"的概念
- [ ] 掌握 `type()` 的两种用法
- [ ] 理解 `type(name, bases, attrs)` 三参数形式
- [ ] 掌握自定义元类的 `__new__`、`__init__`、`__call__`
- [ ] 能用元类实现 ORM 字段验证
- [ ] 运行所有示例代码并观察输出
- [ ] 完成基础练习题
- [ ] 完成进阶挑战题

---

## 基础练习题

### 练习 1：type() 查询

用 `type()` 查询以下对象的类型，然后用 `isinstance()` 验证：
- `42`、`"hello"`、`[1,2,3]`、`{'a': 1}`、`None`、`True`
- 你自定义的类的实例

```python
# 你的代码
objects = [42, "hello", [1,2,3], {'a': 1}, None, True]
for obj in objects:
    print(f"type({obj!r}) = {type(obj)}")
```

### 练习 2：动态创建类

用 `type()` 动态创建一个 `Calculator` 类，包含：
- 属性 `name = "MyCalculator"`
- 方法 `add(a, b)` 返回 `a + b`
- 方法 `multiply(a, b)` 返回 `a * b`

然后实例化并测试。

```python
# 提示：用 lambda 或普通函数作为方法
def add(self, a, b):
    return a + b

def multiply(self, a, b):
    return a * b

Calculator = type('Calculator', (object,), {
    'name': 'MyCalculator',
    'add': add,
    'multiply': multiply,
})

calc = Calculator()
print(calc.add(3, 5))         # 8
print(calc.multiply(3, 5))    # 15
```

### 练习 3：简单元类

编写一个元类，自动给类添加一个 `created_at` 属性，记录类创建的时间。

```python
import datetime

class TimestampMeta(type):
    def __new__(mcs, name, bases, attrs):
        attrs['created_at'] = datetime.datetime.now().isoformat()
        return super().__new__(mcs, name, bases, attrs)

class MyClass(metaclass=TimestampMeta):
    pass

print(MyClass.created_at)  # 2026-07-02T...
```

---

## 进阶挑战题

### 挑战 1：字段验证器

扩展 ORM 字段系统，添加 `FloatField` 和 `DateField`：

```python
class FloatField(Field):
    def validate(self, value):
        if value is not None and not isinstance(value, (int, float)):
            raise TypeError(f"字段 '{self.name}' 必须是数字")
        return True

from datetime import date
class DateField(Field):
    def validate(self, value):
        if value is not None and not isinstance(value, date):
            raise TypeError(f"字段 '{self.name}' 必须是 date 类型")
        return True
```

### 挑战 2：自动序列化

修改 `Model` 类，添加 `serialize()` 和 `deserialize()` 方法，支持 JSON 序列化：

```python
import json

class Model(metaclass=ModelMeta):
    # ... 已有代码 ...
    
    def serialize(self):
        """序列化为 JSON 字符串"""
        data = {}
        for name, field in self._fields.items():
            value = getattr(self, name)
            if isinstance(value, date):
                data[name] = value.isoformat()
            else:
                data[name] = value
        return json.dumps(data, ensure_ascii=False)
    
    @classmethod
    def deserialize(cls, json_str):
        """从 JSON 字符串反序列化"""
        data = json.loads(json_str)
        # 处理日期字段
        for name, field in cls._fields.items():
            if isinstance(field, DateField) and data.get(name):
                data[name] = date.fromisoformat(data[name])
        return cls(**data)
```

### 挑战 3：元类实现缓存

编写一个元类，自动为类的方法添加简单的缓存（memoization）：

```python
class CacheMeta(type):
    def __new__(mcs, name, bases, attrs):
        for key, value in attrs.items():
            if callable(value) and not key.startswith('_'):
                attrs[key] = mcs._make_cached(value)
        return super().__new__(mcs, name, bases, attrs)
    
    @staticmethod
    def _make_cached(func):
        cache = {}
        def wrapper(*args):
            if args in cache:
                return cache[args]
            result = func(*args)
            cache[args] = result
            return result
        wrapper.__name__ = func.__name__
        return wrapper

class Fibonacci(metaclass=CacheMeta):
    def fib(self, n):
        if n < 2:
            return n
        return self.fib(n - 1) + self.fib(n - 2)

f = Fibonacci()
print(f.fib(50))  # 瞬间计算完成（无缓存会非常慢）
```

---

## 📝 反思

完成练习后，回答以下问题：

1. 在什么场景下你会考虑使用元类？什么场景下应该避免？
2. 元类和装饰器的主要区别是什么？
3. 你觉得 Django 的 Model 系统设计得好在哪里？
