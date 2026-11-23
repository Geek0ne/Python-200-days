"""
Day 036 — 封装与数据隐藏：基础用法
====================================

涵盖：
1. 名称改写（Name Mangling）机制
2. 单下划线 _ 与双下划线 __ 的区别
3. 继承中的名称改写
4. @property 装饰器基础
5. 属性访问控制模式
"""


# ====================================
# 1. 名称改写机制
# ====================================
print("=" * 60)
print("1️⃣ 名称改写（Name Mangling）机制")
print("=" * 60)


class BankAccount:
    """银行账户 —— 展示名称改写"""

    def __init__(self, owner: str, balance: float):
        self.owner = owner          # 公开属性
        self._branch = "总部"       # 受保护的（约定）
        self.__balance = balance    # 私有的（名称改写 → _BankAccount__balance）

    def deposit(self, amount: float):
        if amount <= 0:
            raise ValueError("存款金额必须为正数")
        self.__balance += amount
        print(f"  存入 ¥{amount:.2f}，当前余额: ¥{self.__balance:.2f}")

    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValueError("取款金额必须为正数")
        if amount > self.__balance:
            raise ValueError("余额不足")
        self.__balance -= amount
        print(f"  取出 ¥{amount:.2f}，当前余额: ¥{self.__balance:.2f}")

    def get_balance(self):
        """公开的余额查询接口"""
        return self.__balance


account = BankAccount("Alice", 1000)

# 公开属性 — 可直接访问
print(f"  账户持有人: {account.owner}")

# 受保护的属性 — 可访问（但按约定不应直接修改）
print(f"  分行: {account._branch}")

# 私有属性 — 名称改写
try:
    print(account.__balance)
except AttributeError as e:
    print(f"  ❌ 直接访问 __balance 失败: {e}")

# 通过改写后的名字访问
print(f"  通过名称改写访问: {account._BankAccount__balance}")

# 通过公开方法访问
print(f"  通过 get_balance(): {account.get_balance()}")

# 存取款
account.deposit(500)
account.withdraw(200)
print(f"  最终余额: {account.get_balance()}")


# ====================================
# 2. 单下划线 vs 双下划线
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 单下划线 _ 与双下划线 __ 的区别")
print("=" * 60)


class Employee:
    """员工类 —— 展示不同前缀的语义区别"""

    def __init__(self, name: str, salary: float):
        self.name = name            # 公开：公共 API 的一部分
        self._department = "通用"   # 受保护：内部使用，子类可以访问
        self.__salary = salary      # 私有：不希望被子类覆盖

    def __repr__(self):
        return (f"Employee({self.name}, "
                f"dept={self._department}, "
                f"salary={self.__salary})")


# 查看类的 __dict__
print("  Employee 类的属性:")
for key in sorted(Employee.__dict__.keys()):
    if not key.startswith('__') or key.endswith('__'):
        print(f"    {key}")

print("\n  实例属性:")
e = Employee("Bob", 50000)
for key, value in sorted(e.__dict__.items()):
    print(f"    {key} = {value}")


# ====================================
# 3. 继承中的名称改写
# ====================================
print("\n" + "=" * 60)
print("3️⃣ 继承中的名称改写")
print("=" * 60)


class Base:
    """基类 — 定义私有和公开方法"""

    def __init__(self):
        self.__secret = "Base的秘密"     # _Base__secret
        self.public_data = "Base公开"

    def public_method(self):
        return f"Base: {self.__get_secret()}"

    def __get_secret(self):
        """私有方法 — 名称改写"""
        return f"[基类秘密] {self.__secret}"


class Derived(Base):
    """派生类 — 尝试覆盖基类的私有成员"""

    def __init__(self):
        super().__init__()
        self.__secret = "Derived的秘密"  # _Derived__secret (不同！)

    # 这不叫「覆盖」，而是定义了一个不同的方法
    def __get_secret(self):
        return f"[派生类秘密] {self.__secret}"

    def demonstrate(self):
        print(f"  Derived.__secret = {self.__secret}")
        print(f"  Derived.__get_secret() = {self.__get_secret()}")
        print(f"  Base 的 public_method = {self.public_method()}")


d = Derived()
d.demonstrate()

print(f"\n  完全限定名:")
print(f"    _Base__secret = {d._Base__secret}")
print(f"    _Derived__secret = {d._Derived__secret}")


# 对比：保护级别的属性可以覆盖
print("\n  对比: _protected 可以被覆盖")


class Base2:
    def __init__(self):
        self._value = "基类的值"

    def show(self):
        return f"  基类: {self._value}"


class Derived2(Base2):
    def __init__(self):
        super().__init__()
        self._value = "派生类的值"  # 覆盖了基类的 _value


d2 = Derived2()
print(f"  Derived2._value = {d2._value}")
print(f"  Derived2.show() = {d2.show()}")


# ====================================
# 4. @property 装饰器基础
# ====================================
print("\n" + "=" * 60)
print("4️⃣ @property 装饰器基础")
print("=" * 60)


class Circle:
    """圆形类 — 展示 @property 的读写控制"""

    def __init__(self, radius: float):
        self._radius = radius

    @property
    def radius(self) -> float:
        """半径（可读可写）"""
        return self._radius

    @radius.setter
    def radius(self, value: float):
        if value <= 0:
            raise ValueError("半径必须为正数")
        self._radius = value

    @radius.deleter
    def radius(self):
        print("  删除半径（重置为 1）")
        self._radius = 1.0

    @property
    def diameter(self) -> float:
        """直径（只读计算属性）"""
        return self._radius * 2

    @property
    def area(self) -> float:
        """面积（只读计算属性）"""
        import math
        return math.pi * self._radius ** 2

    @property
    def circumference(self) -> float:
        """周长（只读计算属性）"""
        import math
        return 2 * math.pi * self._radius


c = Circle(5)
print(f"  radius = {c.radius}")
print(f"  diameter = {c.diameter}")
print(f"  area = {c.area:.2f}")
print(f"  circumference = {c.circumference:.2f}")

# 修改半径
c.radius = 10
print(f"\n  修改 radius = 10 后:")
print(f"  area = {c.area:.2f}")

# 删除半径
del c.radius
print(f"  删除后 radius = {c.radius}")


# ====================================
# 5. 属性访问控制模式
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 属性访问控制模式")
print("=" * 60)


class Product:
    """商品类 — 展示完整的属性控制"""

    def __init__(self, name: str, price: float, stock: int):
        # 使用 object.__setattr__ 直接设置内部值
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_price', price)
        object.__setattr__(self, '_stock', stock)
        object.__setattr__(self, '_discount', 0.0)

    # ── 只读属性 ──
    @property
    def name(self) -> str:
        """商品名（只读）"""
        return self._name

    # ── 读写 + 验证 ──
    @property
    def price(self) -> float:
        """价格（读写 + 验证）"""
        return self._price * (1 - self._discount)

    @price.setter
    def price(self, value: float):
        if value <= 0:
            raise ValueError("价格必须为正数")
        self._price = value

    @property
    def stock(self) -> int:
        """库存（读写 + 验证）"""
        return self._stock

    @stock.setter
    def stock(self, value: int):
        if value < 0:
            raise ValueError("库存不能为负")
        self._stock = value

    @property
    def discount(self) -> float:
        """折扣率（0~1）"""
        return self._discount

    @discount.setter
    def discount(self, value: float):
        if not 0 <= value <= 1:
            raise ValueError("折扣率必须在 0~1 之间")
        self._discount = value

    # ── 计算属性（只读） ──
    @property
    def discounted_price(self) -> float:
        """折后价"""
        return self._price * (1 - self._discount)

    @property
    def is_in_stock(self) -> bool:
        """是否有库存"""
        return self._stock > 0

    # ── 方法 ──
    def purchase(self, quantity: int) -> float:
        """购买商品"""
        if quantity <= 0:
            raise ValueError("购买数量必须为正数")
        if quantity > self._stock:
            raise ValueError(f"库存不足（当前: {self._stock}, 需要: {quantity})")
        self._stock -= quantity
        return quantity * self.discounted_price

    def restock(self, quantity: int):
        """补货"""
        if quantity <= 0:
            raise ValueError("补货数量必须为正数")
        self._stock += quantity

    def __repr__(self):
        return (f"Product({self._name}, "
                f"¥{self.discounted_price:.2f}, "
                f"库存={self._stock})")


phone = Product("iPhone", 6999, 10)

print(f"  商品: {phone}")
print(f"  名称: {phone.name}")
print(f"  价格: ¥{phone.price:.2f}")
print(f"  有库存: {phone.is_in_stock}")

# 打八折
phone.discount = 0.2
print(f"\n  八折后:")
print(f"  折后价: ¥{phone.discounted_price:.2f}")
print(f"  商品: {phone}")

# 购买
cost = phone.purchase(2)
print(f"\n  购买 2 台: 花费 ¥{cost:.2f}")
print(f"  剩余库存: {phone.stock}")
print(f"  商品: {phone}")

# 补货
phone.restock(5)
print(f"\n  补货 5 台: 库存 = {phone.stock}")
