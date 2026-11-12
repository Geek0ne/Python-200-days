#!/usr/bin/env python3
"""
Day 017 — 断言与防御式编程示例

演示 assert 的正确用法和防御式编程的多种策略。

运行方式：
  python3 07-assert-defensive.py
  python3 -O 07-assert-defensive.py   # 看断言被禁用的效果
"""

import sys
import math

SEP = "=" * 60


# ═══════════════════════════════════════════════════════════════
# Part 1：assert 的正确用法
# ═══════════════════════════════════════════════════════════════

def demo_assert_preconditions():
    """断言用于检查前置条件（开发期）"""
    print(SEP)
    print("1️⃣  assert 前置条件检查")
    print(SEP)

    def sqrt_safe(x):
        """安全开方 — 前置条件断言"""
        assert x >= 0, f"sqrt_safe: x={x} 必须 >= 0"
        return math.sqrt(x)

    # 正常
    result = sqrt_safe(9.0)
    print(f"  ✅ sqrt_safe(9.0) = {result}")

    # 断言失败
    try:
        sqrt_safe(-1.0)
    except AssertionError as e:
        print(f"  ❌ 断言触发: {e}")

    print("\n  ⚠️  Python -O 模式下 assert 被禁用，检查失效！")


def demo_assert_invariants():
    """断言用于检查内部不变量"""
    print(SEP)
    print("2️⃣  assert 内部不变量检查")
    print(SEP)

    class BankAccount:
        def __init__(self, balance: float):
            assert balance >= 0, "初始余额不能为负"
            self.balance = balance

        def deposit(self, amount: float):
            assert amount > 0, "存款金额必须为正"
            old = self.balance
            self.balance += amount
            # 后置条件：余额应该增加
            assert self.balance > old, f"存款后余额应增加: {old} → {self.balance}"

        def withdraw(self, amount: float):
            assert amount > 0, "取款金额必须为正"
            assert self.balance >= amount, "余额不足"
            self.balance -= amount
            assert self.balance >= 0, f"取款后余额不能为负: {self.balance}"

    account = BankAccount(100.0)
    account.deposit(50.0)
    print(f"  ✅ 存款后余额: {account.balance}")
    account.withdraw(30.0)
    print(f"  ✅ 取款后余额: {account.balance}")


def demo_assert_postconditions():
    """断言用于检查后置条件"""
    print(SEP)
    print("3️⃣  assert 后置条件检查")
    print(SEP)

    def sort_and_validate(items: list) -> list:
        """排序并验证结果"""
        result = sorted(items)
        # 后置条件：结果已排序
        assert all(result[i] <= result[i + 1] for i in range(len(result) - 1)), \
            "排序结果不满足升序要求"
        # 后置条件：元素数量不变
        assert len(result) == len(items), "元素数量变化"
        return result

    data = [3, 1, 4, 1, 5, 9, 2, 6]
    sorted_data = sort_and_validate(data)
    print(f"  ✅ 排序验证通过: {sorted_data}")


# ═══════════════════════════════════════════════════════════════
# Part 2：防御式编程
# ═══════════════════════════════════════════════════════════════

def demo_type_guarding():
    """类型守卫"""
    print(SEP)
    print("4️⃣  防御式编程 — 类型守卫")
    print(SEP)

    def safe_divide(a, b):
        """带类型守卫的除法"""
        # 类型守卫
        if not isinstance(a, (int, float)):
            raise TypeError(f"a 必须是数字，收到 {type(a).__name__}")
        if not isinstance(b, (int, float)):
            raise TypeError(f"b 必须是数字，收到 {type(b).__name__}")
        # 值守卫
        if b == 0:
            raise ValueError("除数不能为零")
        return a / b

    # ✅ 正常
    print(f"  ✅ safe_divide(10, 3) = {safe_divide(10, 3):.4f}")

    # ❌ 类型错误
    try:
        safe_divide("10", 3)
    except TypeError as e:
        print(f"  ❌ {e}")

    # ❌ 值错误
    try:
        safe_divide(10, 0)
    except ValueError as e:
        print(f"  ❌ {e}")


def demo_guard_clause():
    """Guard Clause 模式"""
    print(SEP)
    print("5️⃣  防御式编程 — Guard Clause")
    print(SEP)

    def get_user_score(data: dict) -> float:
        """带多层守卫的分数获取函数"""
        # Guard 1: data 为 None
        if data is None:
            raise ValueError("数据不能为空")

        # Guard 2: 键不存在
        if "score" not in data:
            raise KeyError("缺少 score 字段")

        # Guard 3: 类型不正确
        score = data["score"]
        if not isinstance(score, (int, float)):
            raise TypeError(f"score 必须是数字，收到 {type(score).__name__}")

        # Guard 4: 值范围不正确
        if score < 0 or score > 100:
            raise ValueError(f"score 必须在 [0, 100] 范围内，收到 {score}")

        return float(score)

    # 测试
    test_cases = [
        (None, "None"),
        ({}, "空字典"),
        ({"score": "abc"}, "字符串分数"),
        ({"score": 150}, "超范围"),
        ({"score": 85}, "✅ 正常"),
    ]

    for data, desc in test_cases:
        try:
            result = get_user_score(data)
            print(f"  ✅ {desc}: {result}")
        except (ValueError, KeyError, TypeError) as e:
            print(f"  ❌ {desc}: {e}")


def demo_result_object():
    """Result Object 模式 — 返回成功/失败"""
    print(SEP)
    print("6️⃣  防御式编程 — Result Object 模式")
    print(SEP)

    from typing import NamedTuple, Optional

    class Result(NamedTuple):
        """表示操作结果"""
        success: bool
        value: Optional[object] = None
        error: Optional[str] = None

    def parse_age(text: str) -> Result:
        """安全解析年龄，返回 Result 而不是抛异常"""
        try:
            age = int(text.strip())
            if age < 0 or age > 150:
                return Result(False, error=f"年龄 {age} 超出 [0, 150]")
            return Result(True, value=age)
        except (ValueError, AttributeError) as e:
            return Result(False, error=f"解析失败: {e}")

    tests = ["25", "abc", "-5", "200", ""]
    for t in tests:
        r = parse_age(t)
        if r.success:
            print(f"  ✅ '{t}' → {r.value}")
        else:
            print(f"  ❌ '{t}' → {r.error}")


# ═══════════════════════════════════════════════════════════════
# Part 3：断言 vs 异常 对比
# ═══════════════════════════════════════════════════════════════

def demo_assert_vs_exception():
    """断言 vs 异常 场景对比"""
    print(SEP)
    print("7️⃣  断言 vs 异常 — 场景对比")
    print(SEP)

    scenarios = [
        ("用户输入验证", "❌ assert", "✅ 异常"),
        ("内部不变量", "✅ assert", "❌ 异常"),
        ("函数前置条件（开发期）", "✅ assert", "✅ 可选"),
        ("外部数据验证", "❌ assert", "✅ 异常"),
        ("后置条件验证", "✅ assert", "❌ 异常"),
        ("可恢复错误", "❌ assert", "✅ 异常"),
        ("单元测试", "✅ assert", "❌ 异常"),
    ]

    print(f"  {'场景':<30s} {'用 assert':<15s} {'用异常':<15s}")
    print(f"  {'-'*30} {'-'*15} {'-'*15}")
    for scene, a, e in scenarios:
        print(f"  {scene:<30s} {a:<15s} {e:<15s}")

    print()
    print("  📌 黄金法则:")
    print("     assert: 开发期调试、内部不变量")
    print("     异常:  用户输入、外部数据、可恢复错误")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 断言与防御式编程")
    print()

    demo_assert_preconditions()
    demo_assert_invariants()
    demo_assert_postconditions()
    demo_type_guarding()
    demo_guard_clause()
    demo_result_object()
    demo_assert_vs_exception()

    print(SEP)
    print("✅ 演示完毕！")
    print("📌 总结:")
    print("   assert → 开发期调试、内部不变量")
    print("   raise  → 用户输入、外部数据验证")
    print("   Guard Clause → 多层防御")
    print("   Result Object → 优雅处理预期内错误")


if __name__ == "__main__":
    main()
