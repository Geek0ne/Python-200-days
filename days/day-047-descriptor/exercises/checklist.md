# Day 047 — 描述符（Descriptor）练习清单

## ✅ 今日完成清单

- [ ] 理解描述符协议的三个方法（`__get__`、`__set__`、`__delete__`）
- [ ] 掌握数据描述符 vs 非数据描述符的区别
- [ ] 理解 `property` 的底层实现
- [ ] 学会用 `__set_name__` 获取字段名
- [ ] 完成至少 2 个代码示例的运行和理解
- [ ] 完成基础练习题（1-3 题）
- [ ] 完成进阶挑战题（4-5 题）

---

## 📝 基础练习题

### 练习 1：实现一个 `UpperField` 描述符

**要求**：创建一个描述符，将所有赋值自动转为大写字符串。

```python
class UpperField:
    """赋值时自动转为大写"""
    # TODO: 实现 __set_name__, __get__, __set__

class Article:
    title = UpperField()
    # ...

a = Article()
a.title = "hello world"
assert a.title == "HELLO WORLD"
```

**目标**：理解描述符自动转换数据的基本模式。

---

### 练习 2：实现一个 `CachedProperty` 描述符

**要求**：创建一个描述符，第一次访问时计算值，之后从实例 `__dict__` 读取缓存。

```python
class CachedProperty:
    def __init__(self, func):
        self.func = func
        self.attrname = None

    def __set_name__(self, owner, name):
        # TODO: 记住属性名
        pass

    def __get__(self, obj, objtype=None):
        # TODO: 首次计算并缓存到 obj.__dict__[self.attrname]
        # 提示：缓存后描述符就不会再被触发
        pass

class DataProcessor:
    def __init__(self, data):
        self.data = data

    @CachedProperty
    def sorted_data(self):
        print("正在排序...")
        return sorted(self.data)
```

**目标**：理解非数据描述符如何利用实例 `__dict__` 做缓存。

---

### 练习 3：修复共享状态 Bug

以下代码有 Bug —— 所有实例共享同一个计数器。请修复它。

```python
class Counter:
    """❌ 所有实例共享同一个 count！"""
    def __get__(self, obj, objtype=None):
        return self.count if hasattr(self, 'count') else 0

    def __set__(self, obj, value):
        self.count = value  # BUG: 存到了描述符上

class Instance:
    count = Counter()

a = Instance()
b = Instance()
a.count = 5
print(b.count)  # 期望: 0, 实际: 5
```

**要求**：将状态存到实例 `__dict__` 而不是描述符上。

---

## 🚀 进阶挑战题

### 练习 4：实现一个 `TypeChecked` 描述符家族

创建一个可复用的类型检查框架：

```python
class Typed:
    """基础类型检查描述符"""
    # TODO: 在 __init__ 中接收 expected_type
    # TODO: 在 __set__ 中校验类型

class Integer(Typed):
    def __init__(self):
        super().__init__(int)

class String(Typed):
    def __init__(self, max_length=255):
        super().__init__(str)
        self.max_length = max_length
    # TODO: 额外校验长度

class Float(Typed):
    def __init__(self):
        super().__init__((int, float))  # int 和 float 都接受

class Model:
    age = Integer()
    name = String(max_length=50)
    score = Float()
```

**目标**：构建一个可扩展的验证框架。

---

### 练习 5：实现一个 `Validated` 描述符 + 校验器

**要求**：实现一个支持多个校验函数的描述符：

```python
def not_empty(value):
    """校验非空"""
    return "不能为空" if not value else None

def min_value(n):
    """校验最小值"""
    def check(value):
        return f"必须 >= {n}" if value < n else None
    return check

class Validated:
    def __init__(self, *validators):
        self.validators = validators
    # TODO: 实现描述符方法，在 __set__ 中执行所有校验

class Product:
    name = Validated(not_empty)
    price = Validated(min_value(0.01))
```

**目标**：掌握描述符 + 函数式编程的组合模式（校验器是闭包）。

---

## 💡 思考题（口头回答即可）

1. 为什么说 Python 的方法（method）也是描述符？它实现了哪个方法？
2. `@property` 是数据描述符还是非数据描述符？为什么？
3. 如果你在描述符的 `__get__` 中 `return self`，会发生什么？
4. Django 的 `Model.field` 在赋值时做了什么？用描述符解释。
5. `__set_name__` 是什么时候被调用的？有什么用？

---

## 📚 参考答案位置

完成练习后，可以参考 `code/` 目录下的三个示例文件：
- `01-descriptor-basics.py` — 描述符基础用法
- `02-descriptor-advanced.py` — 进阶用法与避坑
- `03-descriptor-orm.py` — ORM 字段系统实战
