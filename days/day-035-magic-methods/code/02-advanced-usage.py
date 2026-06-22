"""
Day 035 — 特殊方法：进阶用法
===============================

涵盖：
1. 运算符重载（完整实现）
2. 反向运算与原地运算
3. 属性访问控制（__getattr__ / __setattr__）
4. 上下文管理器协议
5. 迭代器协议与 __reversed__
"""


# ====================================
# 1. 运算符重载（完整实现）
# ====================================
print("=" * 60)
print("1️⃣ 运算符重载（完整实现）")
print("=" * 60)


class ComplexNumber:
    """复数类 —— 展示完整的运算符重载"""

    def __init__(self, real: float, imag: float = 0.0):
        self.real = real
        self.imag = imag

    def __repr__(self):
        if self.imag >= 0:
            return f"Complex({self.real} + {self.imag}j)"
        return f"Complex({self.real} - {abs(self.imag)}j)"

    def __str__(self):
        if self.imag >= 0:
            return f"({self.real} + {self.imag}i)"
        return f"({self.real} - {abs(self.imag)}i)"

    # ── 算术运算 ──

    def __add__(self, other):
        if isinstance(other, ComplexNumber):
            return ComplexNumber(self.real + other.real, self.imag + other.imag)
        if isinstance(other, (int, float)):
            return ComplexNumber(self.real + other, self.imag)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, ComplexNumber):
            return ComplexNumber(self.real - other.real, self.imag - other.imag)
        if isinstance(other, (int, float)):
            return ComplexNumber(self.real - other, self.imag)
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, ComplexNumber):
            # (a+bi)(c+di) = (ac-bd) + (ad+bc)i
            return ComplexNumber(
                self.real * other.real - self.imag * other.imag,
                self.real * other.imag + self.imag * other.real
            )
        if isinstance(other, (int, float)):
            return ComplexNumber(self.real * other, self.imag * other)
        return NotImplemented

    def __truediv__(self, other):
        if isinstance(other, ComplexNumber):
            denom = other.real ** 2 + other.imag ** 2
            if denom == 0:
                raise ZeroDivisionError("复数除法：除数为零")
            # (a+bi)/(c+di) = (ac+bd)/(c²+d²) + (bc-ad)/(c²+d²)i
            return ComplexNumber(
                (self.real * other.real + self.imag * other.imag) / denom,
                (self.imag * other.real - self.real * other.imag) / denom
            )
        if isinstance(other, (int, float)):
            if other == 0:
                raise ZeroDivisionError("除数为零")
            return ComplexNumber(self.real / other, self.imag / other)
        return NotImplemented

    def __neg__(self):
        return ComplexNumber(-self.real, -self.imag)

    def __abs__(self):
        return (self.real ** 2 + self.imag ** 2) ** 0.5

    # ── 比较运算 ──

    def __eq__(self, other):
        if not isinstance(other, ComplexNumber):
            return NotImplemented
        return self.real == other.real and self.imag == other.imag

    def __lt__(self, other):
        """按模长比较"""
        if not isinstance(other, ComplexNumber):
            return NotImplemented
        return abs(self) < abs(other)

    # ── 类型转换 ──

    def __complex__(self):
        return complex(self.real, self.imag)

    def __bool__(self):
        return self.real != 0 or self.imag != 0


# 演示
c1 = ComplexNumber(3, 4)
c2 = ComplexNumber(1, 2)

print(f"  c1 = {c1}")
print(f"  c2 = {c2}")
print(f"  c1 + c2 = {c1 + c2}")
print(f"  c1 - c2 = {c1 - c2}")
print(f"  c1 * c2 = {c1 * c2}")
print(f"  c1 / c2 = {c1 / c2}")
print(f"  -c1 = {-c1}")
print(f"  |c1| = {abs(c1):.3f}")
print(f"  c1 == ComplexNumber(3, 4): {c1 == ComplexNumber(3, 4)}")
print(f"  c1 < c2: {c1 < c2}")  # 按模长: |c1|=5, |c2|=√5

# 与整数运算
print(f"\n  c1 + 5 = {c1 + 5}")
print(f"  c1 * 2 = {c1 * 2}")


# ====================================
# 2. 反向运算与原地运算
# ====================================
print("\n" + "=" * 60)
print("2️⃣ 反向运算与原地运算")
print("=" * 60)


class Vector2D:
    """二维向量 —— 展示反向运算和原地运算"""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Vector2D({self.x}, {self.y})"

    # ── 正向运算 ──

    def __add__(self, other):
        if isinstance(other, Vector2D):
            return Vector2D(self.x + other.x, self.y + other.y)
        return NotImplemented

    def __mul__(self, scalar):
        """向量 * 标量"""
        if isinstance(scalar, (int, float)):
            return Vector2D(self.x * scalar, self.y * scalar)
        return NotImplemented

    # ⭐ 反向运算：标量 * 向量
    def __rmul__(self, scalar):
        """标量 * 向量 — 委托给 __mul__"""
        return self.__mul__(scalar)

    # ⭐ 原地运算：+=
    def __iadd__(self, other):
        """v1 += v2 — 直接修改自身，返回 self"""
        if isinstance(other, Vector2D):
            self.x += other.x
            self.y += other.y
            return self
        return NotImplemented

    # ⭐ 原地运算：*=
    def __imul__(self, scalar):
        """v *= 2"""
        if isinstance(scalar, (int, float)):
            self.x *= scalar
            self.y *= scalar
            return self
        return NotImplemented


v1 = Vector2D(3, 4)
v2 = Vector2D(1, 2)

print(f"  v1 = {v1}")
print(f"  v2 = {v2}")

# 反向运算
result = 2 * v1  # 调用 v1.__rmul__(2)
print(f"  2 * v1 = {result}")

# 原地运算
v1 += v2
print(f"  v1 += v2 → {v1}")

v1 *= 3
print(f"  v1 *= 3 → {v1}")


# ====================================
# 3. 属性访问控制（__getattr__ / __setattr__）
# ====================================
print("\n" + "=" * 60)
print("3️⃣ 属性访问控制")
print("=" * 60)


class LazyAttribute:
    """惰性属性 — 使用 __getattr__ 实现按需加载"""

    def __init__(self):
        self._loaded = set()

    def __getattr__(self, name):
        """属性不存在时调用 —— 实现动态属性和惰性加载"""
        if name.startswith('_'):
            raise AttributeError(name)

        print(f"  🔄 惰性加载: {name}")
        value = f"data:{name}"
        # 缓存到实例字典中
        object.__setattr__(self, name, value)
        self._loaded.add(name)
        return value

    def __setattr__(self, name, value):
        """所有属性赋值都会经过这里"""
        print(f"  📝 设置属性: {name} = {value!r}")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        """删除属性"""
        print(f"  🗑️ 删除属性: {name}")
        object.__delattr__(self, name)


obj = LazyAttribute()
print(f"  name: {obj.name}")        # 第一次访问，触发惰性加载
print(f"  name: {obj.name}")        # 第二次访问，已缓存
print(f"  email: {obj.email}")      # 另一个属性
print(f"  已加载的属性: {obj._loaded}")

# 属性赋值
obj.age = 25
print(f"  age: {obj.age}")

# 属性删除
del obj.age


class ReadOnlyProxy:
    """只读代理 —— 使用 __setattr__ 实现保护"""

    def __init__(self, data: dict):
        # 使用 object.__setattr__ 绕开保护进行初始化
        object.__setattr__(self, '_data', dict(data))
        object.__setattr__(self, '_locked', True)

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'{type(self).__name__}' 没有属性 '{name}'")

    def __setattr__(self, name, value):
        if hasattr(self, '_locked') and self._locked:
            raise AttributeError(f"只读对象，不能修改 '{name}'")
        object.__setattr__(self, name, value)


proxy = ReadOnlyProxy({"name": "Alice", "age": 30})
print(f"\n  proxy.name = {proxy.name}")
print(f"  proxy.age = {proxy.age}")

try:
    proxy.name = "Bob"
except AttributeError as e:
    print(f"  ❌ 修改失败: {e}")


# ====================================
# 4. 上下文管理器协议
# ====================================
print("\n" + "=" * 60)
print("4️⃣ 上下文管理器协议")
print("=" * 60)

import time


class Timer:
    """计时器上下文管理器"""

    def __init__(self, name: str = "代码块"):
        self.name = name

    def __enter__(self):
        """进入 with 块时调用"""
        self.start = time.perf_counter()
        print(f"  ▶️  开始计时: {self.name}")
        return self  # 绑定到 as 变量

    def __exit__(self, exc_type, exc_val, exc_tb):
        """离开 with 块时调用（无论是否异常）"""
        self.elapsed = time.perf_counter() - self.start
        print(f"  ⏱️  {self.name} 耗时: {self.elapsed * 1000:.2f}ms")
        # 返回 False 表示不抑制异常，True 表示抑制
        return False


with Timer("求和运算") as t:
    total = sum(range(10_000_000))
    print(f"  结果: {total}")

print(f"  从上下文管理器获取耗时: {t.elapsed:.4f}s")


class Transaction:
    """模拟数据库事务 —— 提交/回滚"""

    def __init__(self, name: str):
        self.name = name
        self.operations = []

    def add_operation(self, op: str):
        self.operations.append(op)

    def __enter__(self):
        print(f"  🔄 开始事务: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # 无异常，提交
            print(f"  ✅ 提交事务: {self.name}")
            for op in self.operations:
                print(f"     -> {op}")
        else:
            # 有异常，回滚
            print(f"  ❌ 回滚事务: {self.name} ({exc_type.__name__}: {exc_val})")
        # 不抑制异常
        return False


print("\n📊 事务演示（成功）:")
with Transaction("创建用户") as tx:
    tx.add_operation("INSERT INTO users (name) VALUES ('Alice')")
    tx.add_operation("INSERT INTO logs (action) VALUES ('create_user')")

print("\n📊 事务演示（失败）:")
try:
    with Transaction("创建用户") as tx:
        tx.add_operation("INSERT INTO users (name) VALUES ('Bob')")
        raise ValueError("违反唯一约束!")
except ValueError:
    print("  异常已传播到外部")


# ====================================
# 5. 迭代器协议与 __reversed__
# ====================================
print("\n" + "=" * 60)
print("5️⃣ 迭代器协议与 __reversed__")
print("=" * 60)


class Fibonacci:
    """斐波那契数列 —— 自定义迭代器"""

    def __init__(self, max_count: int = 10):
        self.max_count = max_count
        self.count = 0
        self.a, self.b = 0, 1

    def __iter__(self):
        """返回迭代器对象"""
        self.count = 0
        self.a, self.b = 0, 1
        return self

    def __next__(self):
        """返回下一个值"""
        if self.count >= self.max_count:
            raise StopIteration
        self.count += 1
        result = self.a
        self.a, self.b = self.b, self.a + self.b
        return result

    def __reversed__(self):
        """反向迭代 —— 生成反向的斐波那契数列"""
        # 先收集所有值
        values = list(self)
        return iter(reversed(values))


fib = Fibonacci(10)
print("  正向迭代: ", end="")
for n in fib:
    print(n, end=" ")
print()

# __getitem__ 实现迭代
class CountDown:
    """倒计时 —— 使用 __getitem__ 隐式实现迭代"""

    def __init__(self, start: int):
        self.start = start

    def __getitem__(self, index):
        if isinstance(index, int):
            val = self.start - index
            if val < 0:
                raise IndexError("超出范围")
            return val
        raise TypeError("索引必须为整数")


cd = CountDown(5)
print("  倒计时迭代: ", end="")
for n in cd:
    print(n, end=" ")
print()

print(f"  cd[0] = {cd[0]}")
print(f"  cd[2] = {cd[2]}")
print(f"  5 in cd: {5 in cd}")  # 自动使用 __getitem__
