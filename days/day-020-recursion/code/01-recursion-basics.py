#!/usr/bin/env python3
"""
Day 020 - Recursion Basics
递归基础：阶乘、斐波那契、汉诺塔、二分查找
"""

import sys
sys.setrecursionlimit(10_000)


# ============================================================
# 1. 阶乘 (Factorial)
# ============================================================

def factorial_recursive(n: int) -> int:
    """递归实现阶乘 n!

    数学定义:
        fact(0) = 1
        fact(n) = n * fact(n-1)

    调用栈示例 (n=4):
        fact(4) = 4 * fact(3)
               = 4 * 3 * fact(2)
               = 4 * 3 * 2 * fact(1)
               = 4 * 3 * 2 * 1 * fact(0)
               = 4 * 3 * 2 * 1 * 1
               = 24
    """
    if n == 0:  # 基线条件
        return 1
    return n * factorial_recursive(n - 1)  # 递归条件


def factorial_iterative(n: int) -> int:
    """迭代实现阶乘"""
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def factorial_tail(n: int, accumulator: int = 1) -> int:
    """尾递归形式的阶乘

    ⚠️ Python 不支持尾递归优化，这只是形式上的尾递归。
    实际运行时仍然会消耗栈空间。
    """
    if n == 0:
        return accumulator
    return factorial_tail(n - 1, n * accumulator)


# ============================================================
# 2. 斐波那契数列 (Fibonacci)
# ============================================================

def fib_naive(n: int) -> int:
    """原始递归斐波那契 — O(2ⁿ) 指数级复杂度

    fib(40) 需要约 3.3 亿次调用 😱
    """
    if n <= 1:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)


# 用 functools.lru_cache 添加记忆化
from functools import lru_cache


@lru_cache(maxsize=None)
def fib_memo(n: int) -> int:
    """带记忆化的递归斐波那契 — O(n)

    lru_cache 自动缓存结果，避免重复计算
    """
    if n <= 1:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)


def fib_iterative(n: int) -> int:
    """迭代斐波那契 — O(n), O(1) 空间"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# 手动实现 memoization（不依赖 functools）
def fib_manual_memo():
    """返回一个带记忆化的斐波那契函数"""
    cache = {0: 0, 1: 1}

    def _fib(n: int) -> int:
        if n not in cache:
            cache[n] = _fib(n - 1) + _fib(n - 2)
        return cache[n]

    return _fib


# ============================================================
# 3. 汉诺塔 (Tower of Hanoi)
# ============================================================

def hanoi(n: int, source: str, target: str, auxiliary: str) -> list:
    """汉诺塔递归解法

    三步走策略：
    1. 将 n-1 个盘子从 source 移到 auxiliary
    2. 将第 n 个盘子从 source 移到 target
    3. 将 n-1 个盘子从 auxiliary 移到 target

    参数:
        n: 盘子数量
        source: 起始柱
        target: 目标柱
        auxiliary: 辅助柱

    返回:
        移动步骤列表 [(from, to), ...]

    时间复杂度: O(2ⁿ) — 最少移动次数为 2ⁿ - 1
    """
    if n == 0:
        return []

    steps = []
    # 1. 移动 n-1 个盘子到辅助柱
    steps.extend(hanoi(n - 1, source, auxiliary, target))
    # 2. 移动最大的盘子到目标柱
    steps.append((source, target))
    # 3. 移动 n-1 个盘子从辅助柱到目标柱
    steps.extend(hanoi(n - 1, auxiliary, target, source))

    return steps


def hanoi_print(n: int, source: str, target: str, auxiliary: str, depth: int = 0):
    """汉诺塔（带打印的版本，展示调用过程）"""
    indent = "  " * depth
    if n == 1:
        print(f"{indent}移动 1 号盘: {source} → {target}")
        return

    hanoi_print(n - 1, source, auxiliary, target, depth + 1)
    print(f"{indent}移动 {n} 号盘: {source} → {target}")
    hanoi_print(n - 1, auxiliary, target, source, depth + 1)


# ============================================================
# 4. 二分查找 (Binary Search)
# ============================================================

def binary_search_recursive(arr: list, target: int,
                            left: int = None, right: int = None) -> int:
    """递归实现二分查找

    参数:
        arr: 已排序的列表
        target: 要查找的目标值

    返回:
        目标值的索引，未找到返回 -1

    时间复杂度: O(log n)
    """
    if left is None:
        left, right = 0, len(arr) - 1

    # 基线条件：搜索区间为空
    if left > right:
        return -1

    mid = (left + right) // 2

    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        # 目标在右半边
        return binary_search_recursive(arr, target, mid + 1, right)
    else:
        # 目标在左半边
        return binary_search_recursive(arr, target, left, mid - 1)


def binary_search_iterative(arr: list, target: int) -> int:
    """迭代实现二分查找"""
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


# ============================================================
# 5. 辅助：可视化递归调用
# ============================================================

def factorial_verbose(n: int, depth: int = 0) -> int:
    """带调试输出的阶乘，展示递归调用过程"""
    prefix = "  " * depth
    print(f"{prefix}factorial({n}) 被调用")

    if n == 0:
        print(f"{prefix}→ 基线条件: 返回 1")
        return 1

    result = n * factorial_verbose(n - 1, depth + 1)
    print(f"{prefix}→ 返回 {n} * fact({n-1}) = {result}")
    return result


# ============================================================
# 6. Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("递归基础示例")
    print("=" * 60)

    # --- 阶乘 ---
    print("\n📐 阶乘:")
    n = 5
    print(f"  factorial_recursive({n})  = {factorial_recursive(n)}")
    print(f"  factorial_iterative({n})  = {factorial_iterative(n)}")
    print(f"  factorial_tail({n})      = {factorial_tail(n)}")

    # --- 可视化阶乘 ---
    print("\n📊 可视化递归调用 factorial(4):")
    factorial_verbose(4)

    # --- 斐波那契 ---
    print("\n📈 斐波那契:")
    for n in [10, 20, 30]:
        memo = fib_memo(n)
        it = fib_iterative(n)
        print(f"  fib({n:>2}) → memo={memo}, iterative={it}")

    fib_with_cache = fib_manual_memo()
    print(f"  fib(100) manual memo = {fib_with_cache(100)}")

    # --- 汉诺塔 ---
    print("\n🏯 汉诺塔 (3个盘子):")
    steps = hanoi(3, "A", "C", "B")
    print(f"  总步骤数: {len(steps)}")
    for i, (f, t) in enumerate(steps, 1):
        print(f"  步骤 {i:>2}: {f} → {t}")

    print("\n  带缩进的可视化展示:")
    hanoi_print(3, "A", "C", "B")

    # --- 汉诺塔步数验证 ---
    for n in range(1, 10):
        steps = hanoi(n, "A", "C", "B")
        expected = 2**n - 1
        print(f"  n={n}: 实际步数={len(steps)}, 理论步数={expected}, "
              f"{'✅' if len(steps) == expected else '❌'}")

    # --- 二分查找 ---
    print("\n🔍 二分查找:")
    arr = list(range(0, 100, 2))  # [0, 2, 4, ..., 98]
    targets = [0, 50, 98, 99]
    for t in targets:
        r = binary_search_recursive(arr, t)
        i = binary_search_iterative(arr, t)
        print(f"  搜索 {t:>2}: 递归={r}, 迭代={i}")


if __name__ == "__main__":
    main()
