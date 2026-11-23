#!/usr/bin/env python3
"""
01-multiplication-table.py
九九乘法表 — 全面实战

本文件包含九九乘法表的多种实现版本，演示 for 循环嵌套、格式化输出、
以及不同算法策略。

运行: python3 01-multiplication-table.py
"""

print("=" * 60)
print("📐 版本 1: 标准下三角九九乘法表")
print("=" * 60)

for i in range(1, 10):
    for j in range(1, i + 1):
        # :2d 表示占 2 个字符宽度右对齐，让输出对齐
        print(f"{j}×{i}={i * j:2d}", end="  ")
    print()  # 换行


print("\n" + "=" * 60)
print("📐 版本 2: 完整上三角（含对称部分）")
print("=" * 60)

for i in range(1, 10):
    for j in range(1, 10):
        print(f"{j}×{i}={i * j:2d}", end="  ")
    print()


print("\n" + "=" * 60)
print("📐 版本 3: 反序下三角（从 9×9 开始）")
print("=" * 60)

for i in range(9, 0, -1):          # 外层从 9 递减到 1
    for j in range(1, i + 1):      # 内层从 1 到 i
        print(f"{j}×{i}={i * j:2d}", end="  ")
    print()


print("\n" + "=" * 60)
print("📐 版本 4: 生成字符串（不直接打印）")
print("  — 演示如何把结果存入变量供后续使用")
print("=" * 60)

lines = []
for i in range(1, 10):
    parts = []
    for j in range(1, i + 1):
        parts.append(f"{j}×{i}={i * j:2d}")
    lines.append("  ".join(parts))

# 现在 lines 是结果列表，可以任意处理
table_str = "\n".join(lines)
print(table_str)

# 还可以写入文件
with open("multiplication_table.txt", "w", encoding="utf-8") as f:
    f.write("九九乘法表\n")
    f.write("=" * 50 + "\n")
    f.write(table_str)
    f.write("\n" + "=" * 50)
print("\n📁 已保存到 multiplication_table.txt")


print("\n" + "=" * 60)
print("📐 版本 5: 使用列表推导式（一行搞定）")
print("  — 高级用法，演示 Python 的简洁性")
print("=" * 60)

table = "\n".join(
    "  ".join(f"{j}×{i}={i * j:2d}" for j in range(1, i + 1))
    for i in range(1, 10)
)
print(table)


print("\n" + "=" * 60)
print("📐 版本 6: 使用 while 循环实现（对比）")
print("=" * 60)

i = 1
while i <= 9:
    j = 1
    while j <= i:
        print(f"{j}×{i}={i * j:2d}", end="  ")
        j += 1
    print()
    i += 1


print("\n" + "=" * 60)
print("💡 关键理解")
print("=" * 60)
print("""
1. 为什么内层 range(1, i+1)?
   → 保证只打印下三角（j ≤ i），避免重复（1×2 和 2×1 是同一个算式）

2. 执行次数计算:
   i=1: 1次   i=2: 2次   i=3: 3次   ...   i=9: 9次
   总计 = 1+2+3+...+9 = 45 次

3. :2d 格式化的作用?
   → 冒号后的 2d 表示整数占 2 位右对齐，让所有"=结果"纵向对齐

4. for vs while 的选择:
   → for 更简洁（已知范围和步长）
   → while 更灵活（条件可任意复杂）
""")
