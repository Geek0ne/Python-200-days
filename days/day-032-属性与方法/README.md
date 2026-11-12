# Day 032 — 属性与方法

> 实例属性 vs 类属性、实例/类/静态方法、property 装饰器、getter/setter、银行账户类

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 实例属性 vs 类属性 | ⭐⭐ | 属性定义、查找链、修改规则 |
| 实例方法 | ⭐⭐ | self、操作实例数据 |
| 类方法 @classmethod | ⭐⭐⭐ | cls、工厂方法、类级操作 |
| 静态方法 @staticmethod | ⭐⭐⭐ | 无隐式参数、工具函数 |
| @property 装饰器 | ⭐⭐⭐ | getter/setter/deleter |
| 银行账户类 | ⭐⭐⭐ | 综合实战 |

---

## 一、实例属性 vs 类属性

### 1.1 定义位置

```python
class Student:
    # 类属性（在类体中直接定义）
    school = "Python Academy"
    student_count = 0
    
    def __init__(self, name, grade):
        # 实例属性（通过 self 定义）
        self.name = name
        self.grade = grade
        Student.student_count += 1
```

### 1.2 内存与访问

```
类属性:
  ┌──────────────┐
  │ Student类    │ ← 一份，所有实例共享
  │ school =     │
  │ "Python"     │
  └──────────────┘
        ↑ 共享
  ┌─────┴─────┐
  │ alice      │  bob       │
  │ name=Alice │  name=Bob  │  ← 实例属性（各自独立）
  │ grade=90   │  grade=85  │
  │ school → ↑ │  school → ↑│  ← 类属性（引用类）
  └────────────┘  └──────────┘
```

### 1.3 修改规则

```python
# 1. 通过类修改 — 影响所有实例
Student.school = "New School"
print(alice.school)  # → New School
print(bob.school)    # → New School

# 2. 通过实例修改 — 创建实例变量，不影响类和其它实例
alice.school = "Alice's School"  # 创建实例属性
print(alice.school)  # → Alice's School (实例属性)
print(bob.school)    # → New School (类属性)
print(Student.school)  # → New School (类属性)

# 3. 删除实例属性后恢复类属性
del alice.school
print(alice.school)  # → New School (重新使用类属性)
```

---

## 二、实例方法、类方法、静态方法

### 2.1 三种方法对比

| 方法类型 | 第一个参数 | 修饰器 | 访问类 | 访问实例 | 调用方式 |
|---------|-----------|-------|-------|---------|---------|
| 实例方法 | `self` | 无 | ✅ | ✅ | `obj.method()` |
| 类方法 | `cls` | `@classmethod` | ✅ | ✅ | `cls.method()` 或 `obj.method()` |
| 静态方法 | 无 | `@staticmethod` | ❌（需显式） | ❌ | `ClassName.method()` 或 `obj.method()` |

### 2.2 完整示例

```python
class Pizza:
    """披萨类 — 演示三种方法"""
    
    # 类属性
    menu = {
        'margherita': ('番茄酱', '马苏里拉', '罗勒'),
        'pepperoni': ('番茄酱', '马苏里拉', '意式辣肠'),
        'hawaiian': ('番茄酱', '马苏里拉', '火腿', '菠萝'),
    }
    
    def __init__(self, name, size='M', toppings=None):
        # 实例属性
        self.name = name
        self.size = size
        self.toppings = toppings or []
        self._baked = False
    
    # 1️⃣ 实例方法
    def add_topping(self, topping):
        """添加配料"""
        self.toppings.append(topping)
        return self  # 链式调用
    
    def bake(self):
        """烘烤披萨"""
        if not self._baked:
            print(f"🔥 {self.name} ({self.size}) 正在烤制...")
            self._baked = True
        else:
            print(f"♻️ {self.name} 已经烤好了!")
        return self
    
    def __str__(self):
        toppings = ', '.join(self.toppings)
        status = "🔥 已烤好" if self._baked else "🧊 未烤"
        return f"🍕 {self.name} [{self.size}] {toppings} {status}"
    
    # 2️⃣ 类方法 — 工厂方法
    @classmethod
    def from_menu(cls, name, size='M', extra_toppings=None):
        """根据菜单创建披萨"""
        if name.lower() not in cls.menu:
            raise ValueError(f"菜单中没有 '{name}'，可选: {list(cls.menu.keys())}")
        
        base_toppings = list(cls.menu[name.lower()])
        if extra_toppings:
            base_toppings.extend(extra_toppings)
        
        return cls(name.capitalize(), size, base_toppings)
    
    @classmethod
    def show_menu(cls):
        """显示菜单"""
        print("📋 披萨菜单:")
        for name, toppings in cls.menu.items():
            print(f"  • {name.title()}: {', '.join(toppings)}")
    
    # 3️⃣ 静态方法 — 工具函数
    @staticmethod
    def format_price(price):
        """格式化价格"""
        return f"${price:.2f}"
    
    @staticmethod
    def calculate_discount(price, percent):
        """计算折扣"""
        return price * (1 - percent / 100)

# 使用
# 实例方法
pizza = Pizza("Custom")
pizza.add_topping("芝士").add_topping("蘑菇").bake()
print(pizza)

# 类方法
margherita = Pizza.from_menu("margherita", "L", ["额外芝士"])
margherita.bake()
print(margherita)

# 静态方法
print(Pizza.format_price(12.5))        # → $12.50
print(Pizza.calculate_discount(100, 20))  # → 80.0
```

### 2.3 @classmethod 的典型用途

```python
class Date:
    """日期类 — 演示多种构造方式"""
    
    def __init__(self, year, month, day):
        self.year = year
        self.month = month
        self.day = day
    
    @classmethod
    def from_string(cls, date_str, sep='-'):
        """从字符串创建（反序列化）"""
        parts = date_str.split(sep)
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))
    
    @classmethod
    def today(cls):
        """创建今天日期的实例"""
        from datetime import date
        d = date.today()
        return cls(d.year, d.month, d.day)
    
    def __str__(self):
        return f"{self.year}-{self.month:02d}-{self.day:02d}"

# 多种创建方式
d1 = Date(2024, 6, 22)          # 直接实例化
d2 = Date.from_string("2024-06-22")  # 从字符串
d3 = Date.today()                     # 当前日期
```

### 2.4 @staticmethod 的典型用途

```python
class MathUtils:
    """数学工具类"""
    
    @staticmethod
    def is_prime(n):
        """判断素数"""
        if n < 2:
            return False
        for i in range(2, int(n ** 0.5) + 1):
            if n % i == 0:
                return False
        return True
    
    @staticmethod
    def gcd(a, b):
        """最大公约数（欧几里得算法）"""
        while b:
            a, b = b, a % b
        return a
    
    @staticmethod
    def lcm(a, b):
        """最小公倍数"""
        return a * b // MathUtils.gcd(a, b)

# 静态方法不需要类实例
print(MathUtils.gcd(12, 18))  # → 6
print(MathUtils.lcm(4, 6))    # → 12
```

---

## 三、@property 装饰器

### 3.1 为什么需要 property？

```python
# ❌ 直接暴露属性的问题
class BankAccount:
    def __init__(self, balance):
        self.balance = balance  # 可以直接修改

acc = BankAccount(-100)  # ❌ 允许负余额！
acc.balance = -500       # ❌ 没有任何验证！
```

### 3.2 property 基本用法

```python
class BankAccount:
    def __init__(self, balance=0):
        self._balance = balance  # 约定私有
    
    @property
    def balance(self):
        """getter — 获取余额"""
        return self._balance
    
    @balance.setter
    def balance(self, value):
        """setter — 设置余额（带验证）"""
        if value < 0:
            raise ValueError("余额不能为负数")
        self._balance = value
    
    @balance.deleter
    def balance(self):
        """deleter — 删除余额（通常不允许）"""
        raise AttributeError("余额不能被删除")

acc = BankAccount(1000)
print(acc.balance)  # → 1000（调用 getter）

acc.balance = 2000  # → 调用 setter
# acc.balance = -500  # ❌ ValueError
```

### 3.3 property 的多种实现方式

```python
# 方式一：装饰器风格（推荐）
class Circle:
    def __init__(self, radius):
        self._radius = radius
    
    @property
    def radius(self):
        return self._radius
    
    @radius.setter
    def radius(self, value):
        if value <= 0:
            raise ValueError("半径必须为正数")
        self._radius = value
    
    @property
    def area(self):
        """只读属性 — 没有 setter"""
        return 3.14159 * self._radius ** 2
    
    @property
    def diameter(self):
        return self._radius * 2

# 方式二：property() 函数
class Person:
    def __init__(self, name):
        self._name = name
    
    def _get_name(self):
        return self._name
    
    def _set_name(self, value):
        if not isinstance(value, str):
            raise TypeError("名字必须是字符串")
        self._name = value
    
    def _del_name(self):
        raise AttributeError("名字不能删除")
    
    name = property(_get_name, _set_name, _del_name, "人的名字")
```

### 3.4 计算属性

```python
class Rectangle:
    def __init__(self, width, height):
        self.width = width
        self.height = height
    
    @property
    def area(self):
        """面积 — 计算属性"""
        return self.width * self.height
    
    @property
    def perimeter(self):
        """周长 — 计算属性"""
        return 2 * (self.width + self.height)
    
    @property
    def is_square(self):
        """是否是正方形"""
        return self.width == self.height
    
    @width.setter
    def width(self, value):
        if value <= 0:
            raise ValueError("宽度必须为正数")
        self._width = value
    
    @height.setter
    def height(self, value):
        if value <= 0:
            raise ValueError("高度必须为正数")
        self._height = value

rect = Rectangle(4, 5)
print(rect.area)        # → 20
print(rect.perimeter)   # → 18
print(rect.is_square)   # → False
```

---

## 四、@cached_property

Python 3.8+ 的 `functools.cached_property` 将计算结果缓存：

```python
from functools import cached_property

class DataAnalysis:
    def __init__(self, data):
        self.data = data
    
    @cached_property
    def stats(self):
        """复杂的统计分析 — 只计算一次"""
        print("  📊 计算统计数据中...")
        return {
            'mean': sum(self.data) / len(self.data),
            'max': max(self.data),
            'min': min(self.data),
            'length': len(self.data),
        }

da = DataAnalysis([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
print(da.stats)  # 首次调用：计算
print(da.stats)  # 再次调用：直接返回缓存值
```

---

## 五、实战：银行账户类

### 5.1 设计

```
BankAccount
├── 类属性: bank_name, interest_rate
├── 类方法: from_balance(), get_total_accounts()
├── 实例方法: deposit(), withdraw(), transfer()
├── property: balance, frozen
└── 静态方法: validate_amount(), interest_over_years()
```

### 5.2 核心代码

```python
class BankAccount:
    bank_name = "Python Savings Bank"
    _total_accounts = 0
    interest_rate = 0.02
    
    def __init__(self, owner, initial_balance=0):
        self.owner = owner
        self._balance = 0
        self._frozen = False
        self._transaction_history = []
        
        if initial_balance > 0:
            self.deposit(initial_balance)
        
        BankAccount._total_accounts += 1
        self._account_number = BankAccount._total_accounts
    
    @property
    def balance(self):
        return self._balance
    
    @property
    def frozen(self):
        return self._frozen
    
    @frozen.setter
    def frozen(self, value):
        if not isinstance(value, bool):
            raise TypeError("frozen 必须是布尔值")
        self._frozen = value
    
    def deposit(self, amount):
        self._validate_amount(amount)
        if self._frozen:
            raise RuntimeError("账户已冻结")
        self._balance += amount
        self._add_transaction('deposit', amount)
        return self._balance
    
    def withdraw(self, amount):
        self._validate_amount(amount)
        if self._frozen:
            raise RuntimeError("账户已冻结")
        if amount > self._balance:
            raise ValueError("余额不足")
        self._balance -= amount
        self._add_transaction('withdraw', amount)
        return self._balance
    
    def transfer(self, target_account, amount):
        self._validate_amount(amount)
        if self._frozen or target_account.frozen:
            raise RuntimeError("账户已冻结")
        self.withdraw(amount)
        target_account.deposit(amount)
    
    @staticmethod
    def _validate_amount(amount):
        if not isinstance(amount, (int, float)):
            raise TypeError("金额必须是数字")
        if amount <= 0:
            raise ValueError("金额必须大于0")
    
    @classmethod
    def from_balance(cls, owner, balance):
        return cls(owner, balance)
    
    @classmethod
    def get_total_accounts(cls):
        return cls._total_accounts
    
    def get_interest(self, years):
        return self._balance * (1 + self.interest_rate) ** years
```

---

## 💡 思考题

1. 类方法 `@classmethod` 和静态方法 `@staticmethod` 的本质区别是什么？什么场景下应该用哪一个？

**参考答案**

**本质区别在"隐式第一个参数"**：`@classmethod` 自动收到 `cls`——实际发起调用的那个类（通过子类调用时就是子类），因此能读写类属性、能用 `cls(...)` 创建实例；`@staticmethod` 没有任何隐式参数，就是"恰好放在类命名空间里的普通函数"，不碰类状态也不碰实例状态。

**选择标准**：

- 需要类本身（替代构造器/工厂方法、统计实例数、修改类级配置）→ `@classmethod`。用 `cls` 而非写死类名，子类继承后工厂会自动创建子类实例；
- 逻辑上属于这个类、但不需要类或实例数据的工具函数（如金额校验、格式化）→ `@staticmethod`。

```python
class Base:
    @classmethod
    def create(cls):
        return cls()          # cls 是实际调用的类

    @staticmethod
    def info():
        return '工具函数'


class Child(Base):
    pass


print(type(Base.create()).__name__)   # Base
print(type(Child.create()).__name__)  # Child —— classmethod 跟随子类
print(Child.info())                   # 工具函数
```

预期输出：

```text
Base
Child
工具函数
```

💡 提示：如果一个"静态方法"里频繁写死 `ClassName.xxx`，说明它其实需要类状态，改成 `@classmethod` 用 `cls` 更利于继承。

2. `@property` 的 getter/setter 和直接定义 `get_xxx()` / `set_xxx()` 方法相比，有什么优势？

**参考答案**

核心优势是**接口不变、实现可升级**：

- **属性式语法**：`acc.balance` 比 `acc.get_balance()` 更简洁自然，读写看起来和普通属性一样，调用方无感知；
- **平滑演进**：可以先用普通公开属性起步，等需要校验/计算时再改成 property，**所有调用代码一行都不用改**——这是 Java 式"一开始就写 getter/setter"做不到的；
- **表达能力**：不写 setter 就是只读属性；计算属性（如面积）用起来像字段，语义清晰；
- 与 `getattr`/`hasattr` 等内置机制无缝协作。

```python
class Temperature:
    def __init__(self, celsius=0):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError('不能低于绝对零度')
        self._celsius = value

    @property
    def fahrenheit(self):
        return self._celsius * 9 / 5 + 32


t = Temperature(25)
print(t.celsius, t.fahrenheit)  # 25 77.0
t.celsius = 30                  # 看起来是赋值，实际走 setter 校验
print(t.fahrenheit)             # 86.0
```

预期输出：

```text
25 77.0
86.0
```

💡 提示：property 适合"轻量、快速"的读写逻辑；如果获取一个属性要发起网络请求或耗时计算，用显式方法（或 `@cached_property`）更能提醒调用者成本。

3. 类属性如果是一个可变对象（如列表、字典），多个实例共享修改时会发生什么？如何避免？

**参考答案**

类属性只有一份。如果它是列表/字典这类**可变对象**，任何实例做**原地修改**（`append`、`[k]=v` 等）改的都是这同一个对象，其他实例全部被"连带"——这通常不是想要的行为，而且是隐蔽 bug（没有赋值语句，看起来人畜无害）。

**避免方法**：需要"每实例一份"的数据，放进 `__init__` 里用 `self.xxx = []` 初始化；类属性只放真正要共享的东西（常量、计数器、配置）。若确实想共享但又要隔离修改，就为每个实例 `copy.deepcopy` 一份。

```python
class Bad:
    items = []          # 共享列表

    def add(self, x):
        self.items.append(x)


class Good:
    def __init__(self):
        self.items = []  # 每实例一份

    def add(self, x):
        self.items.append(x)


b1, b2 = Bad(), Bad()
b1.add(1)
print(b2.items)   # [1] 被污染

g1, g2 = Good(), Good()
g1.add(1)
print(g2.items)   # [] 互不影响
```

预期输出：

```text
[1]
[]
```

⚠️ 注意：同样的坑也出现在**函数默认参数**上（`def f(x=[])`），原理一致——默认值只求值一次、被所有调用共享。

4. `@cached_property` 和 `@property` + 手动缓存有什么不同？底层是如何实现的？

**参考答案**

**手动缓存**要自己写样板：定义 `self._cache`、在 getter 里判断"算过没有"、算完存起来，还得自己考虑何时失效。`@cached_property`（Python 3.8+）把这些都自动化了：首次访问时计算，之后直接返回缓存。

**底层机制**：`cached_property` 是一个**非数据描述符**（只实现了 `__get__`，没有 `__set__`）。首次访问触发 `__get__` 计算，然后把结果**写进实例的 `__dict__`**（键就是属性名）。由于"实例字典优先于非数据描述符"的属性查找规则，之后的访问直接在 `__dict__` 命中，根本不再进入 `__get__`。所以 `del obj.attr` 删掉缓存后，下次访问会重新计算——失效机制是免费的。

```python
from functools import cached_property


class Dataset:
    def __init__(self, data):
        self.data = data

    @cached_property
    def total(self):
        print('计算中...')
        return sum(self.data)


d = Dataset([1, 2, 3])
print(d.total)               # 首次：计算
print(d.total)               # 再次：直接取缓存
print('total' in d.__dict__) # True：结果存进了实例字典
del d.total                  # 删除缓存
print(d.total)               # 重新计算
```

预期输出：

```text
计算中...
6
6
True
计算中...
6
```

⚠️ 注意：`cached_property` 依赖实例有 `__dict__`，定义了 `__slots__` 且没留 `__dict__` 的类用不了；另外它**不会自动感知数据变化**——`self.data` 改了缓存也不会更新，需手动 `del`。Python 3.12 起内部不再加锁，多线程下首次计算可能重复执行（结果一致，但别依赖它做"只算一次"的副作用）。

5. Python 为什么没有真正的「私有属性」？`_name` 和 `__name` 的约定意味着什么？

**参考答案**

这是 Python 的设计哲学："我们都是成年人"（we're all consenting adults）——**隐私靠约定而非强制**。任何属性都能通过 `obj.__dict__`、`vars(obj)`、`getattr` 检查出来，语言不提供 Java/C++ 那种编译期的访问壁垒。这样做是为了调试、序列化、测试和框架反射的便利，代价是"防君子不防小人"。

两种下划线约定的含义完全不同：

- **单下划线 `_name`**：纯粹的**命名约定**，告诉别人"这是内部实现，别从外部依赖它，将来可能变"。解释器不做任何限制，可以正常读写；唯一的实际效果是 `from module import *` 默认不会导入这类名字。
- **双下划线 `__name`**：触发**名称改写（name mangling）**。在类体内，`self.__name` 会被编译器改写成 `self._ClassName__name`。目的是**避免子类意外覆盖父类的同名属性**，不是安全机制——知道改写规则后，用 `obj._ClassName__name` 照样能访问。

```python
# 思考题5：_name 约定与 __name 名称改写
class Account:
    def __init__(self):
        self._balance = 0      # 约定：内部使用
        self.__secret = 42     # 名称改写（name mangling）


a = Account()
print(a._balance)            # 0，可直接访问
# print(a.__secret)          # AttributeError
print(a._Account__secret)    # 42，改写后仍可访问
print(list(vars(a)))         # 实例字典里的真实名字
```

预期输出：

```text
0
42
['_balance', '_Account__secret']
```

💡 提示：日常优先用单下划线表达"内部使用"即可；双下划线主要留给"可能被继承、且想避免子类撞名"的场景。不要把它当成加密或权限控制——真要保护数据，靠的是接口设计和文档约定。

---

## 📚 参考资源

- [Python @property 文档](https://docs.python.org/3/library/functions.html#property)
- [Python @classmethod 文档](https://docs.python.org/3/library/functions.html#classmethod)
- [Python @staticmethod 文档](https://docs.python.org/3/library/functions.html#staticmethod)
- [Python cached_property](https://docs.python.org/3/library/functools.html#functools.cached_property)
- [Real Python — Python Properties](https://realpython.com/python-property/)
