# Day 032 — 属性与方法：完成清单与练习题

## ✅ 完成清单

### 概念理解
- [ ] 理解实例属性和类属性的区别与修改规则
- [ ] 理解实例方法（self）、类方法（cls）、静态方法的区别
- [ ] 理解 @classmethod 的工厂方法用途
- [ ] 理解 @staticmethod 的工具函数用途
- [ ] 理解 @property 的 getter/setter/deleter
- [ ] 理解描述符协议（Descriptor Protocol）
- [ ] 理解 __getattr__ 和 __setattr__ 的拦截机制

### Python 实现
- [ ] 能够定义和访问实例属性与类属性
- [ ] 能够使用 @classmethod 定义工厂方法
- [ ] 能够使用 @staticmethod 定义工具方法
- [ ] 能够使用 @property 实现 getter/setter
- [ ] 能够实现计算属性（只读 property）
- [ ] 能够使用 @cached_property 做惰性计算
- [ ] 能够实现描述符类

### 代码实践
- [ ] 运行 `01-basic-usage.py` 理解三种方法和 property
- [ ] 运行 `02-advanced-usage.py` 掌握进阶用法
- [ ] 运行 `03-practical.py` 完成银行账户系统
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 练习 1：实现 Temperature 类

```python
"""
实现 Temperature 类，支持摄氏度和华氏度互相转换。
要求使用 property 实现自动转换。

属性:
  celsius: 摄氏度 (getter/setter)
  fahrenheit: 华氏度 (只读, 自动计算)

方法:
  @classmethod from_kelvin(k): 从开尔文创建
  @staticmethod to_absolute_zero(): 返回绝对零度值
"""
class Temperature:
    # 你的代码
    pass

# 测试
t = Temperature(25)
print(t.celsius)      # → 25
print(t.fahrenheit)   # → 77.0
t.celsius = 0
print(t.fahrenheit)   # → 32.0

t2 = Temperature.from_kelvin(300)
print(t2.celsius)     # → 26.85
```

### 练习 2：实现 ShoppingCart 类

```python
"""
实现购物车类 ShoppingCart，包含：

类属性:
  tax_rate: 税率 (0.08)
  free_shipping_threshold: 免运费门槛 ($50)

实例属性:
  items: list of (name, price, quantity)

实例方法:
  add_item(name, price, quantity=1)
  remove_item(name)
  update_quantity(name, quantity)

计算属性 (@property):
  subtotal: 小计
  tax: 税费
  total: 总价 (含税)
  item_count: 商品总数
  qualifies_free_shipping: 是否免运费

类方法:
  @classmethod from_cart(other): 复制购物车
  @classmethod update_tax_rate(new_rate): 更新税率

静态方法:
  @staticmethod format_price(price): 格式化价格
"""
class ShoppingCart:
    tax_rate = 0.08
    free_shipping_threshold = 50.0

    # 你的代码
    pass

# 测试
cart = ShoppingCart()
cart.add_item("Python编程", 39.99, 2)
cart.add_item("鼠标", 25.00, 1)
print(f"小计: ${cart.subtotal:.2f}")
print(f"总价: ${cart.total:.2f}")
print(f"免运费: {cart.qualifies_free_shipping}")
```

### 练习 3：实现 User 类（带验证）

```python
"""
实现 User 类，使用 property 进行数据验证。

属性:
  username: 3-20个字符，只能包含字母数字和下划线
  email: 必须包含 @ 和 .
  password: 至少8个字符，必须包含大小写字母和数字
  is_admin: 只读，默认为 False
  login_attempts: 只读，默认为 0

方法:
  login(password): 验证密码
  is_valid_email(email): 静态方法，验证邮箱格式
  generate_temp_password(): 类方法，生成临时密码
"""
import re

class User:
    # 你的代码
    pass

# 测试
user = User("alice_wonder", "alice@example.com", "SecurePass1")
print(user.username)   # → alice_wonder
print(user.email)      # → alice@example.com

try:
    User("ab", "test@test.com", "Pass1234")  # username 太短
except ValueError as e:
    print(f"验证通过: {e}")
```

### 练习 4：实现 TodoList 类

```python
"""
实现待办事项列表 TodoList，使用 property 管理统计信息。

类属性:
  priority_levels: {1: "高", 2: "中", 3: "低"}

TodoItem: (title, completed=False, priority=2)

实例方法:
  add(title, priority=2)
  complete(index)
  uncomplete(index)
  remove(index)
  sort_by_priority()
  filter(completed=None, priority=None)

计算属性:
  total: 总数
  completed_count: 已完成数
  pending_count: 待完成数
  completion_rate: 完成率 (百分比)
  top_priority: 最高优先级的未完成任务列表
"""
class TodoList:
    priority_levels = {1: "高", 2: "中", 3: "低"}

    # 你的代码
    pass

# 测试
todo = TodoList()
todo.add("学习Python", 1)
todo.add("买菜", 3)
todo.add("写报告", 1)
print(f"总任务: {todo.total}")           # → 3
print(f"完成率: {todo.completion_rate}%")  # → 0.0%
todo.complete(0)
print(f"完成率: {todo.completion_rate}%")  # → 33.3%
```

### 练习 5：实现 Time 类（描述符）

```python
"""
实现时间描述符 TimeDescriptor，自动将超过60的值进位。

例如: 设置 seconds=120 → 自动变为 2 minutes
     设置 minutes=90  → 自动变为 1 hour 30 minutes

用于 Time 类的 hours, minutes, seconds 属性。
"""
class TimeDescriptor:
    """时间描述符 — 自动进位"""

    def __init__(self, field, max_value, carry_to=None):
        """
        field: 字段名 (用于存储)
        max_value: 最大值 (超过则进位)
        carry_to: 进位到的字段名
        """
        # 你的代码
        pass

    def __get__(self, obj, objtype=None):
        pass

    def __set__(self, obj, value):
        pass


class Time:
    """时间类 — 使用描述符自动进位"""
    seconds = TimeDescriptor('_seconds', 60, 'minutes')
    minutes = TimeDescriptor('_minutes', 60, 'hours')
    hours = TimeDescriptor('_hours', 24, None)

    def __init__(self, hours=0, minutes=0, seconds=0):
        self.hours = hours
        self.minutes = minutes
        self.seconds = seconds

    def __str__(self):
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"


# 测试
t = Time(0, 0, 150)  # 150秒 → 2分30秒
print(t)  # → 00:02:30

t.minutes = 90  # 90分 → 1时30分
print(t)  # → 01:30:30
```

---

## 📊 自评表

| 技能 | 初学者 | 理解 | 掌握 | 熟练 |
|------|--------|------|------|------|
| 实例属性 vs 类属性 | ☐ | ☐ | ☐ | ☐ |
| @classmethod | ☐ | ☐ | ☐ | ☐ |
| @staticmethod | ☐ | ☐ | ☐ | ☐ |
| @property getter/setter | ☐ | ☐ | ☐ | ☐ |
| 计算属性 | ☐ | ☐ | ☐ | ☐ |
| @cached_property | ☐ | ☐ | ☐ | ☐ |
| 描述符协议 | ☐ | ☐ | ☐ | ☐ |
| __getattr__ / __setattr__ | ☐ | ☐ | ☐ | ☐ |

---

## 🔗 参考资源

- [Python property() 函数](https://docs.python.org/3/library/functions.html#property)
- [Python classmethod 文档](https://docs.python.org/3/library/functions.html#classmethod)
- [Python staticmethod 文档](https://docs.python.org/3/library/functions.html#staticmethod)
- [Python 描述符指南](https://docs.python.org/3/howto/descriptor.html)
- [Real Python — Python Descriptors](https://realpython.com/python-descriptors/)
