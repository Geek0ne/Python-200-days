#!/usr/bin/env python3
"""
06-list-comprehension-deep-dive.py — Day 006 补充
列表推导式深度解析：嵌套、性能、陷阱、高阶模式

可直接运行：python3 06-list-comprehension-deep-dive.py
"""

import time
import math


# ============================================================
# 1. 推导式基础回顾 + 执行顺序
# ============================================================

def demo_comprehension_order():
    """推导式的执行顺序——理解它才能用好它"""
    print("=" * 60)
    print("  1️⃣ 推导式执行顺序")
    print("=" * 60)

    # 语法：[expression for item in iterable if condition]
    # 执行顺序等同于嵌套 for 循环：
    # for item in iterable:
    #     if condition:
    #         expression

    matrix = [[1, 2], [3, 4], [5, 6]]
    result = [x for row in matrix for x in row]
    print(f"\n  矩阵展平:")
    print(f"    矩阵: {matrix}")
    print(f"    展平: {result}")

    # 等价于：
    flattened = []
    for row in matrix:
        for x in row:
            flattened.append(x)
    print(f"    for 循环等价: {flattened}")

    # 条件过滤
    result2 = [x for row in matrix for x in row if x % 2 == 0]
    print(f"\n  展平+过滤偶数:")
    print(f"    结果: {result2}")

    # 等价于：
    evens = []
    for row in matrix:
        for x in row:
            if x % 2 == 0:
                evens.append(x)
    print(f"    for 循环等价: {evens}")

    # 执行顺序记忆法：去掉方括号，从外到内读
    # [x for row in matrix for x in row]
    #  ↓
    #  for row in matrix:
    #      for x in row:
    #          x


# ============================================================
# 2. 嵌套推导式实战
# ============================================================

def demo_nested_comprehension():
    """嵌套列表推导式高级用法"""
    print("\n" + "=" * 60)
    print("  2️⃣ 嵌套推导式实战")
    print("=" * 60)

    # 2.1 矩阵转置
    matrix = [[1, 2, 3], [4, 5, 6]]
    transposed = [[row[i] for row in matrix] for i in range(3)]
    print(f"\n  矩阵转置:")
    print(f"    原始: {matrix}")
    print(f"    转置: {transposed}")

    # 2.2 矩阵乘法
    A = [[1, 2], [3, 4]]
    B = [[5, 6], [7, 8]]

    # A×B: result[i][j] = ΣA[i][k] * B[k][j]
    result = [
        [sum(A[i][k] * B[k][j] for k in range(len(B)))
         for j in range(len(B[0]))]
        for i in range(len(A))
    ]
    print(f"\n  矩阵乘法 (2×2):")
    print(f"    A = {A}")
    print(f"    B = {B}")
    print(f"    A×B = {result}")

    # 2.3 笛卡尔积
    colors = ["红", "蓝", "绿"]
    sizes = ["S", "M", "L"]
    cartesian = [(c, s) for c in colors for s in sizes]
    print(f"\n  笛卡尔积:")
    print(f"    颜色: {colors}, 尺寸: {sizes}")
    print(f"    全部组合: {cartesian}")

    # 2.4 三维列表展平
    three_d = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
    flat_3d = [z for layer2 in three_d for layer1 in layer2 for z in layer1]
    print(f"\n  三维展平:")
    print(f"    3D: {three_d}")
    print(f"    1D: {flat_3d}")


# ============================================================
# 3. 推导式性能陷阱
# ============================================================

def demo_comprehension_traps():
    """列表推导式常见陷阱"""
    print("\n" + "=" * 60)
    print("  3️⃣ 推导式陷阱与注意事项")
    print("=" * 60)

    # 陷阱 1：变量泄露（Python 2 的问题，Python 3 已修复）
    x = "原始值"
    result = [x for x in range(5)]
    print(f"\n  陷阱 1 — 变量泄露:")
    print(f"    推导式中 x = {x}（Python 3 中推导式有自己的作用域）")
    print(f"    结果: {result}")

    # 但嵌套推导式中的变量会泄露！
    # 实际上 Python 3 中只有列表推导式有独立作用域
    # 在 Python 2 中 x 会变成 4

    # 陷阱 2：方括号 vs 圆括号（生成器 vs 列表）
    print(f"\n  陷阱 2 — 列表 vs 生成器:")
    list_comp = [x ** 2 for x in range(5)]
    gen_expr = (x ** 2 for x in range(5))
    print(f"    列表推导式: {list_comp} (类型: {type(list_comp).__name__})")
    print(f"    生成器表达式: {gen_expr} (类型: {type(gen_expr).__name__})")
    print(f"    生成器惰性求值: {list(gen_expr)}")

    # 陷阱 3：过于复杂的推导式（可读性灾难）
    print(f"\n  陷阱 3 — 复杂推导式:")
    # 不推荐：过于复杂
    hard_to_read = [
        [x * y for x in range(5) if x % 2 == 0]
        for y in range(5) if y % 2 != 0
    ]
    print(f"    复杂推导式: {hard_to_read}")
    # 推荐：拆开写
    better = []
    for y in range(5):
        if y % 2 != 0:
            row = []
            for x in range(5):
                if x % 2 == 0:
                    row.append(x * y)
            better.append(row)
    print(f"    等价 for 循环: {better}")

    # 陷阱 4：海象运算符在推导式中的使用 (Python 3.8+)
    print(f"\n  陷阱 4 — 海象运算符 :=")
    values = [1, 2, 3, 4, 5]
    # 错误的使用方式
    processed = [y for x in values if (y := x * 2) > 5]
    print(f"    带海象运算符: {processed}")

    # 陷阱 5：副作用（推导式中不要做副作用操作）
    print(f"\n  陷阱 5 — 副作用:")
    side_effects = []
    # 不推荐：推导式用于副作用
    _ = [side_effects.append(x * 2) for x in range(5)]
    print(f"    错误用法（推导式作副作用）: {side_effects}")
    # 正确做法
    correct = [x * 2 for x in range(5)]
    print(f"    正确用法: {correct}")


# ============================================================
# 4. 条件推导式深度解析
# ============================================================

def demo_conditional_comprehension():
    """条件推导式高级用法"""
    print("\n" + "=" * 60)
    print("  4️⃣ 条件推导式深度解析")
    print("=" * 60)

    nums = range(-5, 6)

    # 三元条件表达式
    classified = ["正" if x > 0 else "零" if x == 0 else "负" for x in nums]
    print(f"\n  三元条件分类:")
    print(f"    数据: {list(nums)}")
    print(f"    分类: {classified}")

    # 多条件过滤（多个 if）
    filtered = [x for x in range(50) if x % 2 == 0 if x % 3 == 0 if x % 5 == 0]
    print(f"\n  多条件过滤（2∩3∩5 的倍数）:")
    print(f"    结果: {filtered}")

    # 等价于
    equiv = [x for x in range(50) if x % 2 == 0 and x % 3 == 0 and x % 5 == 0]
    print(f"    and 等价: {equiv}")

    # if-else 的三元模式
    parity = ["even" if x % 2 == 0 else "odd" for x in range(10)]
    print(f"\n  if-else 三元:")
    print(f"    结果: {parity}")

    # 复杂业务逻辑
    def categorize_score(score):
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        return "F"

    scores = [95, 82, 67, 73, 45, 88]
    grades = [categorize_score(s) for s in scores]
    print(f"\n  自定义函数分类:")
    print(f"    成绩: {scores}")
    print(f"    等级: {grades}")


# ============================================================
# 5. 推导式与内置函数的黄金组合
# ============================================================

def demo_comprehension_with_builtins():
    """推导式 + 内置函数的最佳实践"""
    print("\n" + "=" * 60)
    print("  5️⃣ 推导式 + 内置函数组合")
    print("=" * 60)

    # zip + 推导式
    names = ["Alice", "Bob", "Charlie", "Diana"]
    scores = [85, 92, 78, 95]
    gradebook = {name: score for name, score in zip(names, scores)}
    print(f"\n  zip + 推导式:")
    print(f"    成绩簿: {gradebook}")

    # enumerate + 推导式
    indexed = {i: name.upper() for i, name in enumerate(names)}
    print(f"\n  enumerate + 推导式:")
    print(f"    索引映射: {indexed}")

    # filter + 推导式
    filtered = [s for s in scores if s >= 85]
    print(f"\n  filter 替代:")
    print(f"    高分(≥85): {filtered}")

    # map + 推导式（推导式更 Pythonic）
    lengths = [len(name) for name in names]
    print(f"\n  map 替代:")
    print(f"    名字长度: {lengths}")

    # sorted + 推导式
    sorted_by_score = sorted(gradebook.items(), key=lambda x: -x[1])
    print(f"\n  sorted + 推导式:")
    print(f"    按分排序: {sorted_by_score}")

    # all / any + 推导式
    all_pass = all(s >= 60 for s in scores)
    any_perfect = any(s == 100 for s in scores)
    print(f"\n  all/any 语法:")
    print(f"    全部及格: {all_pass}")
    print(f"    有满分: {any_perfect}")

    # sum / max / min + 推导式
    total = sum(s for s in scores)
    average = total / len(scores)
    print(f"\n  sum + 推导式:")
    print(f"    总分: {total}, 平均: {average:.1f}")


# ============================================================
# 主程序
# ============================================================

def main():
    demo_comprehension_order()
    demo_nested_comprehension()
    demo_comprehension_traps()
    demo_conditional_comprehension()
    demo_comprehension_with_builtins()

    print("\n" + "=" * 60)
    print("  ✅ 列表推导式深度解析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
