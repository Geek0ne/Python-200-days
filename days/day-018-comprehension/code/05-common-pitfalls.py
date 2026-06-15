#!/usr/bin/env python3
"""
Day 018 — 推导式常见陷阱与避坑

展示推导式中容易出现的各类陷阱以及正确的处理方式：
1. 变量泄露作用域
2. 闭包中的变量捕获
3. 生成器耗尽
4. 副作用问题
5. 过度复杂
6. 海象运算符陷阱
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title):
    console.section(title)


# ══════════════════════════════════════════════════════════
# 陷阱 1：作用域与变量泄露
# ══════════════════════════════════════════════════════════
section("陷阱 1：作用域与变量泄露")

print("--- 1.1 Python 3 中推导式有自己的作用域 ---")
x = '我是外部变量'
squares = [x ** 2 for x in range(5)]
print(f"推导式中的 x 最后值: {x}")  # '我是外部变量'，不是 4
print("→ Python 3 中推导式变量不泄露到外部作用域 ✅")

print("\n--- 1.2 但局部作用域中依然可见 ---")
# 推导式创建了一个隐式的函数作用域（通过 <listcomp> 代码对象）
# 循环变量在推导式外部不可见
try:
    print(loop_var)
except NameError:
    print("→ 推导式中的循环变量在外部不可见 ✅")

print("\n--- 1.3 Python 2 中的泄露问题（已修复） ---")
print("→ Python 2 中列表推导式会泄露循环变量")
print("→ Python 3 中列表/字典/集合推导式均有独立作用域")
print("→ 生成器表达式在 Python 2 中也有独立作用域")


# ══════════════════════════════════════════════════════════
# 陷阱 2：闭包中的变量捕获
# ══════════════════════════════════════════════════════════
section("陷阱 2：闭包中的变量捕获")

print("--- 2.1 经典闭包陷阱 ---")
funcs = [lambda: x for x in range(5)]
results = [f() for f in funcs]
print(f"闭包结果: {results}")  # [4, 4, 4, 4, 4] 而不是 [0, 1, 2, 3, 4]
print("→ 所有 lambda 捕获的是同一个变量 x 的最终值")

print("\n--- 2.2 解决方案：默认参数绑定当前值 ---")
funcs_fixed = [lambda x=x: x for x in range(5)]
results_fixed = [f() for f in funcs_fixed]
print(f"修复后: {results_fixed}")  # [0, 1, 2, 3, 4]
print("→ 使用默认参数 x=x 将当前值绑定到闭包")

print("\n--- 2.3 列表推导式中使用 lambda 作为表达式 ---")
# ❌ 错误用法 - 所有 lambda 共享同一个 i
wrong = [(lambda: i)() for i in range(5)]
print(f"错误: {wrong}")  # [4, 4, 4, 4, 4]

# ✅ 正确用法
right = [(lambda x=i: x)() for i in range(5)]
print(f"正确: {right}")  # [0, 1, 2, 3, 4]


# ══════════════════════════════════════════════════════════
# 陷阱 3：生成器耗尽
# ══════════════════════════════════════════════════════════
section("陷阱 3：生成器耗尽")

print("--- 3.1 生成器一次性使用 ---")
gen = (x for x in range(5))
print(f"首次迭代: {list(gen)}")  # [0, 1, 2, 3, 4]
print(f"再次迭代: {list(gen)}")  # [] - 已经空了
print("→ 生成器只能迭代一次！")

print("\n--- 3.2 推导式消耗生成器 ---")
gen = (x for x in range(5))
first = [x * 2 for x in gen]
second = [x * 3 for x in gen]
print(f"第一次: {first}")   # [0, 2, 4, 6, 8]
print(f"第二次: {second}")  # [] - gen 已耗尽
print("→ 小心！推导式消耗完生成器后不会再产生数据")

print("\n--- 3.3 解决方案：提前转为列表 ---")
gen = (x for x in range(5))
data = list(gen)  # 需要多次迭代时，先转为列表
first = [x * 2 for x in data]
second = [x * 3 for x in data]
print(f"第一次: {first}")
print(f"第二次: {second}")
print("→ 需要多次遍历时，用 list() 将生成器转为列表")


# ══════════════════════════════════════════════════════════
# 陷阱 4：副作用问题
# ══════════════════════════════════════════════════════════
section("陷阱 4：副作用问题")

print("--- 4.1 用推导式做副作用操作 ---")
data = [1, 2, 3]

# ❌ 错误：使用推导式仅为了副作用
side_effects = [print(f"数字: {x}") for x in data]
print(f"推导式结果: {side_effects}")  # [None, None, None]
print("→ 推导式应返回有意义的结果，而不是 None 列表")

print("\n--- 4.2 正确做法：用 for 循环表达副作用 ---")
print("✅ 正确的副作用做法:")
for x in data:
    print(f"  数字: {x}")

print("\n--- 4.3 修改外部变量 ---")
count = 0
# ❌ 极端糟糕：推导式 + 副作用
[count := count + x for x in range(5)]
print(f"通过推导式修改外部变量: count = {count}")
print("→ 虽然可以工作，但这是非常糟糕的风格！")


# ══════════════════════════════════════════════════════════
# 陷阱 5：过度复杂
# ══════════════════════════════════════════════════════════
section("陷阱 5：过度复杂")

print("--- 5.1 一行代码试图做太多事 ---")
data = [{'name': 'Alice', 'scores': [85, 90, 78]},
        {'name': 'Bob', 'scores': [92, 88, 95]},
        {'name': 'Charlie', 'scores': [70, 75, 72]}]

# ❌ 过度复杂：一条推倒式试图做太多
try:
    result = {
        p['name']: [
            s * 1.1 for s in p['scores']
            if s >= 80
        ]
        for p in data
        if sum(p['scores']) / len(p['scores']) > 75
    }
    print(f"过度复杂的结果: {result}")
    print("→ 可以工作，但可读性差")

except Exception as e:
    print(f"错误: {e}")

# ✅ 更好：拆成多步
print("\n✅ 推荐做法：分步处理")
avg_scores = {p['name']: sum(p['scores']) / len(p['scores']) for p in data}
print(f"平均分: {avg_scores}")
qualified = {name for name, avg in avg_scores.items() if avg > 75}
print(f"合格: {qualified}")
adjusted = {
    p['name']: [s * 1.1 for s in p['scores'] if s >= 80]
    for p in data
    if p['name'] in qualified
}
print(f"调整后: {adjusted}")

print("\n--- 5.2 嵌套推导式可读性下降 ---")
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

# 可读（两层）
flat = [num for row in matrix for num in row]
print(f"两层嵌套: {flat} ✅")

# OK（两层互相嵌套）
transposed = [[row[i] for row in matrix] for i in range(3)]
print(f"转置: {transposed} ✅")

# 勉强（若熟练）
flatten_negative = [-num if num % 2 == 0 else num
                    for row in matrix
                    for num in row
                    if num >= 0]
print(f"复杂表达式: {flatten_negative} ⚠️")


# ══════════════════════════════════════════════════════════
# 陷阱 6：海象运算符的误用
# ══════════════════════════════════════════════════════════
section("陷阱 6：海象运算符")

print("--- 6.1 推导式中使用 := ---")
# ✅ 合法用法：避免重复计算
data = ['  hello ', 'world', '  ', 'python  ', '']
cleaned = [clean_name for item in data
           if (clean_name := item.strip()) != '']
print(f"海象运算符清洗: {cleaned}")

print("\n--- 6.2 作用域问题 ---")
# 在推导式中使用 := 赋值的变量会在推导式外部可见
_ = [val for x in [1, 2, 3] if (val := x * 2) > 0]
print(f"海象变量在推导式外部: val = {val}")  # 6（Python 3.9+）

print("\n--- 6.3 与列表推导式结合时的常见错误 ---")
# ❌ 错误：试图在表达式部分赋值
try:
    [x := x * 2 for x in range(5)]
except Exception as e:
    print(f"错误: {type(e).__name__}: {e}")
    print("→ 表达式部分不允许使用 := ")


# ══════════════════════════════════════════════════════════
# 最佳实践总结
# ══════════════════════════════════════════════════════════
section("最佳实践总结")

print("✅ 应该使用推导式的情况:")
print("   1. 简单映射：对数据做统一变换")
print("   2. 简单过滤：根据条件筛选数据")
print("   3. 两层以内的嵌套")
print("   4. 结果需要列表/字典/集合")
print()
print("❌ 不应该使用推导式的情况:")
print("   1. 复杂逻辑（超过两层或复杂条件）")
print("   2. 有副作用（print、文件写入等）")
print("   3. 代码行可能超过 80 字符")
print("   4. 调试时需要逐行检查")
print("   5. 处理无限数据流（应使用生成器）")
print()
print("💡 黄金法则：")
print("   如果一行推导式让你停下来思考 5 秒以上，")
print("   请拆成普通循环。")


if __name__ == '__main__':
    print("\n✅ Day 018 — 推导式常见陷阱与避坑完成")
    print("📌 记住：推导式强大但不万能")
    print("   可读性 > 简洁性 > 性能")
