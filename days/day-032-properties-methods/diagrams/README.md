# Day 032 — 属性与方法：图解

> 属性查找链、三种方法对比、property 执行流程、描述符协议

---

## 1️⃣ 属性查找链

```
obj.attr

1. type(obj).__mro__ 中的 __getattribute__
   │
   ├── 2a. 数据描述符? (有 __set__ 或 __delete__)
   │    └── 调用描述符的 __get__
   │
   ├── 2b. 实例 __dict__?
   │    └── 返回 obj.__dict__['attr']
   │
   ├── 2c. 类 __dict__ 中的非数据描述符?
   │    └── 调用描述符的 __get__
   │
   ├── 2d. 类 __dict__ 中?
   │    └── 返回 Class.__dict__['attr']
   │
   └── 2e. 父类链?
        └── 遍历 MRO 查找
             │
             未找到 → AttributeError
             (如果定义了 __getattr__ 则调用它)

解释:
  数据描述符优先于实例属性
  实例属性优先于非数据描述符
  非数据描述符优先于类属性
```

## 2️⃣ 实例方法 / 类方法 / 静态方法

```
                       ┌──────────────────────────┐
                       │      Method Types         │
                       └──────────────────────────┘

实例方法 (Instance Method):
┌─────────────────────────────────────────────┐
│ def method(self, args):                      │
│     # 可以访问 self (实例数据)               │
│     # 可以访问 cls (通过 type(self))         │
│                                              │
│ 调用: obj.method(args)                       │
│ 等价: Class.method(obj, args)                │
└─────────────────────────────────────────────┘

类方法 (Class Method):
┌─────────────────────────────────────────────┐
│ @classmethod                                 │
│ def method(cls, args):                       │
│     # 第一个参数是类本身                     │
│     # 不能直接访问实例数据                   │
│     # 常做工厂方法、替代构造器              │
│                                              │
│ 调用: Class.method(args)                     │
│ 等价: obj.method(args)  (cls = type(obj))    │
└─────────────────────────────────────────────┘

静态方法 (Static Method):
┌─────────────────────────────────────────────┐
│ @staticmethod                                │
│ def method(args):                            │
│     # 没有隐式参数!                          │
│     # 只是放在类命名空间中的独立函数         │
│     # 常做工具函数/验证函数                  │
│                                              │
│ 调用: Class.method(args)                     │
│ 等价: obj.method(args)  (忽略实例)           │
└─────────────────────────────────────────────┘

示例 — Pizza 类:
  Pizza                     ← 类
  ├── menu = {...}          ← 类属性
  ├── show_menu()           ← 类方法
  ├── from_menu()           ← 类方法 (工厂)
  ├── format_price()        ← 静态方法 (工具)
  └── calculate_discount()  ← 静态方法 (工具)

  pizza = Pizza("Custom")   ← 实例
  ├── name = "Custom"       ← 实例属性
  ├── toppings = [...]      ← 实例属性
  ├── add_topping()         ← 实例方法
  └── bake()                ← 实例方法
```

## 3️⃣ @property 执行流程

```
class Circle:
    @property
    def area(self):
        return 3.14 * self._radius ** 2

调用 c.area:
    c.area
      │
      ▼
    type(c).__getattribute__('area')
      │
      ├── 检查 Circle.__dict__['area']
      │    ← 发现是 property 描述符对象
      │
      ├── property 是数据描述符
      │    (有 __get__ / __set__ / __delete__)
      │
      ├── 调用 property.__get__(c, Circle)
      │    │
      │    ├── 调用 fget (getter 函数)
      │    │    c.area → 3.14 * c._radius ** 2
      │    │
      │    └── 返回计算结果
      │
      └── 返回 area 值

完整 property 对象结构:
    property(fget=None, fset=None, fdel=None, doc=None)
    
    @property          = property(fget)
    @x.setter          = property().setter(fset)
    @x.deleter         = property().deleter(fdel)
```

## 4️⃣ 银行账户系统架构

```
BankAccount (基类)
│
├── 类属性
│   ├── bank_name
│   ├── _total_accounts
│   └── daily_withdraw_limit
│
├── @property
│   ├── owner (getter + setter, 验证)
│   ├── balance (只读 getter)
│   ├── frozen (getter + setter)
│   ├── transaction_count (计算属性)
│   └── today_summary (计算属性)
│
├── 实例方法
│   ├── deposit()
│   ├── withdraw() ← 含日限额检查
│   ├── transfer()
│   ├── get_statement()
│   └── display_statement()
│
├── @classmethod
│   ├── from_balance()
│   ├── get_total_accounts()
│   └── create_random_account()
│
├── @staticmethod
│   ├── _validate_amount()
│   ├── format_amount()
│   └── calculate_interest()
│
└── 私有方法
    ├── _check_frozen()
    ├── _check_sufficient()
    ├── _check_daily_limit()
    └── _add_transaction()

子类:
SavingsAccount ── 继承 BankAccount
  ├── 添加: annual_interest_rate
  ├── 添加: apply_interest()
  └── 重写: withdraw() ← 添加手续费

CheckingAccount ── 继承 BankAccount
  ├── 添加: monthly_fee
  ├── 添加: apply_monthly_fee()
  └── 重写: withdraw() ← 跟踪免费交易数
```

## 5️⃣ 描述符协议

```
描述符 = 实现了特殊方法的类

数据描述符 (Data Descriptor):
  __get__ + __set__ 或 __delete__
  优先级高于实例 __dict__
  示例: @property

非数据描述符 (Non-Data Descriptor):
  只实现 __get__
  优先级低于实例 __dict__
  示例: 实例方法

示例 — PositiveNumber 描述符:
class PositiveNumber:
    def __get__(self, obj, objtype):
        if obj is None: return self
        return self._values.get(obj, 0)
    
    def __set__(self, obj, value):
        if value <= 0:
            raise ValueError("必须为正数")
        self._values[obj] = value

使用:
class Product:
    price = PositiveNumber("price")
    stock = PositiveNumber("stock")
    
    def __init__(self, name, price, stock):
        self.name = name
        self.price = price   ← 调用 PositiveNumber.__set__()
        self.stock = stock   ← 调用 PositiveNumber.__set__()

赋值流程:
  product.price = 99.99
    │
    ├── 数据描述符优先!
    │   Product.__dict__['price'] = PositiveNumber
    │   PositiveNumber 有 __set__
    │
    ├── 调用 PositiveNumber.__set__(product, 99.99)
    │
    └── 执行验证逻辑
```

## 6️⃣ 类属性与 instance __dict__ 修改对比

```
alice = Employee("Alice", 50000)
bob   = Employee("Bob", 60000)

初始状态:
  Employee.__dict__['company']   = "TechCorp"  ← 类属性
  alice.__dict__['name']         = "Alice"     ← 实例属性
  alice.__dict__['salary']       = 50000       ← 实例属性
  bob.__dict__['name']           = "Bob"       ← 实例属性
  bob.__dict__['salary']         = 60000       ← 实例属性

操作1: Employee.company = "NewCorp"
  修改 Employee.__dict__['company']
  alice.company → NewCorp (找不到实例属性 → 读取类)
  bob.company   → NewCorp

操作2: alice.company = "AliceCorp"
  创建 alice.__dict__['company']
  alice.company → "AliceCorp" (实例属性优先)
  bob.company   → "NewCorp" (仍然读取类)

操作3: del alice.company
  删除 alice.__dict__['company']
  alice.company → "NewCorp" (恢复类属性)
```
