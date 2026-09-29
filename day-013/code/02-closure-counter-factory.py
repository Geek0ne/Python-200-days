"""
Day 013 - 02: 闭包与计数器工厂
===============================
深入演示闭包的原理、陷阱和完整的计数器工厂实战。
可直接运行：python3 02-closure-counter-factory.py
"""

import sys


# ============================================================
# 1. 闭包基础：函数工厂
# ============================================================
print("=" * 60)
print("1. 闭包基础——函数工厂")
print("=" * 60)


def make_power(exp):
    """创建一个求幂函数"""
    def power(base):
        return base ** exp
    return power


square = make_power(2)
cube = make_power(3)

print(f"3 的平方: {square(3)}")   # → 9
print(f"3 的立方: {cube(3)}")     # → 27
print(f"5 的平方: {square(5)}")   # → 25

# 检查闭包的内部结构
print(f"\n闭包内部结构:")
print(f"  自由变量: {square.__code__.co_free_vars}")
print(f"  闭包 cell: {square.__closure__}")
print(f"  自由变量值: {square.__closure__[0].cell_contents}")


# ============================================================
# 2. 闭包实现数据封装
# ============================================================
print("\n" + "=" * 60)
print("2. 闭包实现数据封装")
print("=" * 60)


def create_bank_account(owner, initial_balance=0):
    """
    创建一个"银行账户"闭包。
    余额对外部完全隐藏，只能通过返回的函数操作。
    """
    balance = initial_balance

    def deposit(amount):
        """存款"""
        nonlocal balance
        if amount <= 0:
            raise ValueError("存款金额必须为正数")
        balance += amount
        return f"存款 {amount} 元，余额: {balance}"

    def withdraw(amount):
        """取款"""
        nonlocal balance
        if amount <= 0:
            raise ValueError("取款金额必须为正数")
        if amount > balance:
            raise ValueError(f"余额不足！当前余额: {balance}")
        balance -= amount
        return f"取款 {amount} 元，余额: {balance}"

    def check_balance():
        """查询余额"""
        return f"账户 [{owner}] 余额: {balance} 元"

    # 返回操作接口字典
    return {
        "deposit": deposit,
        "withdraw": withdraw,
        "check": check_balance,
    }


# 使用
alice_account = create_bank_account("Alice", 1000)
bob_account = create_bank_account("Bob", 500)

print(alice_account["deposit"](500))     # → 存款 500 元，余额: 1500
print(alice_account["withdraw"](200))    # → 取款 200 元，余额: 1300
print(alice_account["check"]())          # → 账户 [Alice] 余额: 1300 元

# 两个账户独立
print(bob_account["check"]())            # → 账户 [Bob] 余额: 500 元

# 余额完全隐藏，外部无法直接访问
try:
    print(alice_account["balance"])  # KeyError — 不存在！
except KeyError as e:
    print(f"无法直接访问余额: {e}")


# ============================================================
# 3. 延迟绑定陷阱
# ============================================================
print("\n" + "=" * 60)
print("3. 闭包延迟绑定陷阱")
print("=" * 60)


# 有问题的版本
def create_lazy_multipliers():
    """⚠️ 错误的延迟绑定"""
    result = []
    for i in range(5):
        def multiply(x):
            return x * i  # i 在运行时才查找
        result.append(multiply)
    return result


# 修正版本 1：默认参数
def create_fixed_multipliers_v1():
    """✅ 使用默认参数立即绑定"""
    result = []
    for i in range(5):
        def multiply(x, i=i):  # 默认参数在定义时求值
            return x * i
        result.append(multiply)
    return result


# 修正版本 2：额外闭包层
def create_fixed_multipliers_v2():
    """✅ 使用额外闭包创建独立作用域"""
    def make_multiplier(i):
        def multiply(x):
            return x * i
        return multiply

    return [make_multiplier(i) for i in range(5)]


# 演示结果
bad = create_lazy_multipliers()
good1 = create_fixed_multipliers_v1()
good2 = create_fixed_multipliers_v2()

print("有问题的版本（所有函数返回 x * 4）:")
for m in bad:
    print(f"  m(2) = {m(2)}", end="")
print()  # → 8 8 8 8 8

print("修正版1（默认参数）:")
for m in good1:
    print(f"  m(2) = {m(2)}", end="")
print()  # → 0 2 4 6 8

print("修正版2（额外闭包层）:")
for m in good2:
    print(f"  m(2) = {m(2)}", end="")
print()  # → 0 2 4 6 8


# ============================================================
# 4. 完整的计数器工厂
# ============================================================
print("\n" + "=" * 60)
print("4. 🏭 实战：完整计数器工厂")
print("=" * 60)


class StopIterationError(Exception):
    """自定义停止迭代异常"""
    pass


def create_counter(start=0, step=1, min_val=None, max_val=None):
    """
    创建一个灵活的计数器。

    参数:
        start: 起始值（默认 0）
        step: 步长（默认 1，负数表示递减）
        min_val: 最小值限制（None 表示不限制）
        max_val: 最大值限制（None 表示不限制）

    返回:
        dict: 包含 next / prev / reset / peek / info 方法的字典
    """
    current = start

    def _check_bounds(new_val):
        """检查新值是否超出边界"""
        if max_val is not None and new_val > max_val:
            raise StopIterationError(
                f"已达到上限 {max_val}（当前: {current}，步长: {step}）"
            )
        if min_val is not None and new_val < min_val:
            raise StopIterationError(
                f"已达到下限 {min_val}（当前: {current}，步长: {step}）"
            )

    def next():
        """下一步"""
        nonlocal current
        new_val = current + step
        _check_bounds(new_val)
        current = new_val
        return current

    def prev():
        """上一步（反向步长）"""
        nonlocal current
        new_val = current - step
        _check_bounds(new_val)
        current = new_val
        return current

    def reset():
        """重置到起始值"""
        nonlocal current
        current = start

    def peek():
        """查看当前值（不修改）"""
        return current

    def info():
        """查看计数器配置"""
        return {
            "start": start,
            "step": step,
            "min": min_val,
            "max": max_val,
            "current": current,
        }

    return {
        "next": next,
        "prev": prev,
        "reset": reset,
        "peek": peek,
        "info": info,
    }


# ---------- 测试计数器 ----------
print("\n--- 基础计数器 ---")
c1 = create_counter()
for _ in range(5):
    print(f"  c1.next() = {c1['next']()}", end="")
print()  # → 1 2 3 4 5

c1["reset"]()
print(f"  重置后: {c1['peek']()}")  # → 0

print("\n--- 递减计数器 ---")
c2 = create_counter(start=10, step=-1, min_val=5)
for _ in range(6):
    print(f"  c2.next() = {c2['next']()}", end=" ")
print()  # → 9 8 7 6 5

try:
    c2["next"]()  # 超出下限
except StopIterationError as e:
    print(f"  ⛔ 超出范围: {e}")

print("\n--- 反向移动 ---")
c3 = create_counter(start=0, step=2, max_val=10)
print(f"  c3[peek]() = {c3['peek']()}")  # → 0
c3["next"]()
c3["next"]()
c3["next"]()
print(f"  c3.next() *3 = {c3['peek']()}")  # → 6
c3["prev"]()
print(f"  c3.prev() = {c3['peek']()}")  # → 4

print("\n--- 计数器配置 ---")
c4 = create_counter(start=100, step=10, min_val=0, max_val=200)
import pprint
pprint.pprint(c4["info"]())


# ============================================================
# 5. 对比：闭包 vs 类
# ============================================================
print("\n" + "=" * 60)
print("5. 闭包 vs 类对比")
print("=" * 60)


# 闭包版本
def make_greeter_closure(greeting):
    """闭包版问候生成器"""
    def greet(name):
        return f"{greeting}, {name}!"
    return greet


# 类版本
class GreeterClass:
    """类版问候生成器"""

    def __init__(self, greeting):
        self.greeting = greeting

    def greet(self, name):
        return f"{self.greeting}, {name}!"


# 使用对比
closure_greeter = make_greeter_closure("你好")
class_greeter = GreeterClass("你好")

print(f"闭包版: {closure_greeter('Alice')}")
print(f"类版:  {class_greeter.greet('Alice')}")

# 性能简单对比
import timeit

# 闭包版
closure_time = timeit.timeit(
    'closure_greeter("World")',
    globals={"closure_greeter": closure_greeter},
    number=1000000
)

# 类版
class_time = timeit.timeit(
    'class_greeter.greet("World")',
    globals={"class_greeter": class_greeter},
    number=1000000
)

print(f"\n性能对比（100万次调用）:")
print(f"  闭包版: {closure_time:.4f} 秒")
print(f"  类版本: {class_time:.4f} 秒")
print(f"  差异: {abs(closure_time - class_time) / min(closure_time, class_time) * 100:.1f}%")


# ============================================================
# 6. 内存与引用检查
# ============================================================
print("\n" + "=" * 60)
print("6. 闭包内存与引用检查")
print("=" * 60)


def create_big_closure():
    """创建一个持有大数据的闭包"""
    big_data = list(range(10000))  # 10K 大小的列表

    def process():
        return len(big_data)

    return process


# 创建闭包
processor = create_big_closure()
# create_big_closure 已经返回了，但 big_data 仍然被闭包引用
print(f"处理函数: {processor()}")
print(f"闭包自由变量: {processor.__code__.co_free_vars}")

# 强制垃圾回收并查看引用
import gc
gc.collect()
print(f"闭包 cell 对象存活: {processor.__closure__ is not None}")

print("\n✅ 所有示例运行完毕！")
