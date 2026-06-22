"""
Day 032 — 属性与方法：进阶用法
======================================================================
@property 高级用法、cached_property、描述符协议、属性访问拦截
======================================================================
"""

from functools import cached_property, lru_cache
import time
import math

# ====================================================================
# 1. @property 高级用法 — 验证 + 计算
# ====================================================================
print("=" * 60)
print("1️⃣  @property 高级用法 — 带验证的计算属性")
print("=" * 60)


class Student:
    """学生 — 带完整验证的成绩管理"""

    def __init__(self, name, scores=None):
        self._name = None
        self._scores = {}
        self.name = name
        if scores:
            for subject, score in scores.items():
                self.set_score(subject, score)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str) or len(value.strip()) < 1:
            raise ValueError("姓名必须是非空字符串")
        self._name = value.strip().title()

    def set_score(self, subject, score):
        """设置单科成绩"""
        if not 0 <= score <= 100:
            raise ValueError(f"{subject} 成绩必须在 0-100 之间")
        self._scores[subject] = score

    @property
    def average(self):
        """平均分（只读计算属性）"""
        if not self._scores:
            return 0.0
        return sum(self._scores.values()) / len(self._scores)

    @property
    def total(self):
        """总分"""
        return sum(self._scores.values())

    @property
    def max_score(self):
        """最高分科目"""
        if not self._scores:
            return None
        max_subj = max(self._scores, key=self._scores.get)
        return max_subj, self._scores[max_subj]

    @property
    def passed(self):
        """是否全部及格"""
        if not self._scores:
            return False
        return all(s >= 60 for s in self._scores.values())

    @property
    def grade(self):
        """总体等级"""
        avg = self.average
        if avg >= 90:
            return 'A'
        elif avg >= 80:
            return 'B'
        elif avg >= 70:
            return 'C'
        elif avg >= 60:
            return 'D'
        return 'F'

    def __str__(self):
        subjects = ', '.join(f"{s}:{sc}" for s, sc in self._scores.items())
        return (f"{self.name:>8} | {subjects} | "
                f"平均:{self.average:.1f} 等级:{self.grade}")


students = [
    Student("alice", {"数学": 92, "英语": 88, "语文": 95}),
    Student("bob", {"数学": 75, "英语": 82, "语文": 68}),
    Student("charlie", {"数学": 45, "英语": 55, "语文": 48}),
]

print("  学生成绩:")
print(f"  {'姓名':>8} | {'科目成绩':<30} | {'平均':<6} | {'等级'}")
print(f"  {'-'*60}")
for s in students:
    print(f"  {s}")
    if not s.passed:
        print(f"  {'⚠️ 有不及格科目':>50}")


# ====================================================================
# 2. @cached_property — 惰性缓存计算
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  @cached_property — 惰性缓存计算")
print("=" * 60)


class PrimeAnalyzer:
    """素数分析 — 计算量大，需要缓存"""

    def __init__(self, limit):
        self.limit = limit
        self._sieve = None

    def _compute_sieve(self):
        """埃拉托色尼筛法 — 计算素数"""
        print("    ⚙️  计算素数筛...")
        self._sieve = [True] * (self.limit + 1)
        self._sieve[0] = self._sieve[1] = False
        for i in range(2, int(self.limit ** 0.5) + 1):
            if self._sieve[i]:
                step = i
                start = i * i
                self._sieve[start:self.limit + 1:step] = [False] * ((self.limit - start) // step + 1)
        return self._sieve

    @cached_property
    def primes(self):
        """所有素数（缓存计算结果）"""
        self._compute_sieve()
        return [i for i, is_prime in enumerate(self._sieve) if is_prime]

    @cached_property
    def prime_count(self):
        """素数个数"""
        return len(self.primes)

    @cached_property
    def twin_primes(self):
        """孪生素数对"""
        p = self.primes
        return [(p[i], p[i+1]) for i in range(len(p)-1) if p[i+1] - p[i] == 2]


print("\n  创建 PrimeAnalyzer(limit=100):")
pa = PrimeAnalyzer(100)

print("  首次访问 primes:")
start = time.perf_counter()
p = pa.primes
t1 = time.perf_counter() - start
print(f"    找到 {len(p)} 个素数 (耗时: {t1:.4f}s)")

print("  再次访问 primes (缓存):")
start = time.perf_counter()
p2 = pa.primes
t2 = time.perf_counter() - start
print(f"    找到 {len(p2)} 个素数 (耗时: {t2:.6f}s)")
print(f"    缓存加速比: {t1/t2:.0f}x")

print(f"\n  孪生素数对 (前10):")
for pair in pa.twin_primes[:10]:
    print(f"    {pair}")


# ====================================================================
# 3. 描述符协议（Descriptor Protocol）
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  描述符协议 — property 的底层实现")
print("=" * 60)


class PositiveNumber:
    """描述符：限制属性为正数"""

    def __init__(self, name):
        self.name = name
        self._values = {}

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._values.get(obj, 0)

    def __set__(self, obj, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f"{self.name} 必须是数字")
        if value <= 0:
            raise ValueError(f"{self.name} 必须为正数")
        self._values[obj] = value

    def __delete__(self, obj):
        if obj in self._values:
            del self._values[obj]


class Product:
    """商品 — 使用描述符自动验证"""
    price = PositiveNumber("price")
    stock = PositiveNumber("stock")

    def __init__(self, name, price, stock):
        self.name = name
        self.price = price
        self.stock = stock

    @property
    def total_value(self):
        return self.price * self.stock

    def __repr__(self):
        return f"Product({self.name}, ${self.price:.2f}, {self.stock} pcs)"


print("  创建商品（自动验证属性值）:")
laptop = Product("Laptop", 999.99, 50)
phone = Product("Phone", 699.99, 100)

print(f"    {laptop}")
print(f"    {phone}")
print(f"    Laptop 库存总价值: ${laptop.total_value:.2f}")

print("\n  修改库存（通过描述符验证）:")
laptop.stock = 75
print(f"    {laptop}")

try:
    laptop.price = -100  # ❌
except ValueError as e:
    print(f"    错误: {e}")

try:
    laptop.stock = 0  # ❌
except ValueError as e:
    print(f"    错误: {e}")


# ====================================================================
# 4. __getattr__ 与 __setattr__ — 属性访问拦截
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  __getattr__ / __setattr__ — 属性访问拦截")
print("=" * 60)


class ProtectedDict:
    """
    受保护的字典 — 属性风格访问
    支持 obj.key 方式访问字典
    """

    def __init__(self, initial=None):
        object.__setattr__(self, '_data', {})
        if initial:
            self._data.update(initial)

    def __getattr__(self, name):
        """当正常属性查找失败时调用"""
        if name.startswith('_'):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        return None  # 安全返回 None 而不是抛出错误

    def __setattr__(self, name, value):
        """设置属性时拦截"""
        if name.startswith('_'):
            # 真正的私有属性用 object.__setattr__
            object.__setattr__(self, name, value)
        else:
            self._data[name] = value

    def __delattr__(self, name):
        """删除属性"""
        if name in self._data:
            del self._data[name]
        else:
            raise AttributeError(f"属性 '{name}' 不存在")

    def __str__(self):
        return str(self._data)


config = ProtectedDict({"host": "localhost", "port": 8080})

print("  ProtectedDict 使用:")
print(f"    config.host = {config.host}")
print(f"    config.port = {config.port}")
print(f"    config.token = {config.token} (不存在属性返回 None)")

print("\n  动态添加属性:")
config.timeout = 30
config.debug = True
print(f"    config.timeout = {config.timeout}")
print(f"    config.debug = {config.debug}")
print(f"    内部数据: {config._data}")


# ====================================================================
# 5. 三种方法的实际应用场景对比
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  三种方法实际应用 — CSV 序列化系统")
print("=" * 60)


class CSVSerializable:
    """可序列化为 CSV 的基类"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_row(self):
        """实例方法：序列化为 CSV 行"""
        headers = self.get_headers()
        return ','.join(str(getattr(self, h, '')) for h in headers)

    @classmethod
    def get_headers(cls):
        """类方法：获取字段名"""
        raise NotImplementedError("子类必须实现 get_headers")

    @classmethod
    def from_row(cls, row):
        """类方法：从 CSV 行创建实例"""
        headers = cls.get_headers()
        values = row.strip().split(',')
        data = {}
        for h, v in zip(headers, values):
            data[h] = cls.parse_value(h, v)
        return cls(**data)

    @classmethod
    def parse_header(cls, header_str):
        """类方法：解析表头"""
        return header_str.strip().split(',')

    @staticmethod
    def parse_value(field_name, value):
        """静态方法：解析字段值（工具函数）"""
        value = value.strip()
        if value == '':
            return None

        # 尝试数字类型
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 布尔值
        if value.lower() in ('true', 'yes'):
            return True
        if value.lower() in ('false', 'no'):
            return False

        return value


class PersonData(CSVSerializable):
    """人员数据"""

    @classmethod
    def get_headers(cls):
        return ['name', 'age', 'city', 'salary']


# 创建实例
p1 = PersonData(name="Alice", age=30, city="Beijing", salary=80000)
p2 = PersonData(name="Bob", age=25, city="Shanghai", salary=65000)

print("  CSV 序列化:")
print(f"    CSV 表头: {PersonData.get_headers()}")
print(f"    p1: {p1.to_row()}")
print(f"    p2: {p2.to_row()}")

# 反序列化
csv_line = "Charlie,35,Guangzhou,True"
p3 = PersonData.from_row(csv_line)
print(f"\n  从 CSV 反序列化:")
print(f"    CSV: {csv_line}")
print(f"    结果: name={p3.name}, age={p3.age}, city={p3.city}, salary={p3.salary}")


print("\n" + "=" * 60)
print("✅  Day 32 进阶用法演示完成!")
print("=" * 60)
