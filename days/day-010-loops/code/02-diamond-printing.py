#!/usr/bin/env python3
"""
02-diamond-printing.py
菱形打印 — 循环嵌套与图形输出实战

核心知识点:
1. for 循环嵌套（外层行，内层列）
2. range() 控制空格和星号数量
3. 上下对称分析：上半部分 vs 下半部分
4. end="" 参数控制不换行

运行: python3 02-diamond-printing.py
"""


def print_diamond(n):
    """
    打印菱形（上半部分 n 行）

    参数:
        n: 上半部分行数（总行数 = 2*n - 1）

    图解（n=4):
       *
      ***
     *****
    *******
     *****
      ***
       *

    每行的空格、星号计算公式:
    上半部分第 i 行 (1-based): 空格 = n - i, 星号 = 2*i - 1
    下半部分第 i 行 (1-based): 空格 = i,     星号 = 2*(n - i) - 1
    """
    print(f"\n📐 菱形 (n={n}, 总行数={2*n - 1}):")

    # ========== 上半部分（含中间行）==========
    for i in range(1, n + 1):
        # 打印左边的空格
        for j in range(n - i):
            print(" ", end="")
        # 打印星号
        for j in range(2 * i - 1):
            print("*", end="")
        print()  # 当前行结束，换行

    # ========== 下半部分（不含中间行）==========
    for i in range(1, n):
        # 打印左边的空格
        for j in range(i):
            print(" ", end="")
        # 打印星号
        for j in range(2 * (n - i) - 1):
            print("*", end="")
        print()


def print_diamond_compact(n):
    """
    更紧凑的菱形打印版本
    使用字符串乘法（'*' * times）减少内部嵌套层数
    """
    print(f"\n📐 紧凑版菱形 (n={n}):")
    # 上半部分
    for i in range(1, n + 1):
        spaces = " " * (n - i)
        stars = "*" * (2 * i - 1)
        print(spaces + stars)
    # 下半部分
    for i in range(1, n):
        spaces = " " * i
        stars = "*" * (2 * (n - i) - 1)
        print(spaces + stars)


def print_hollow_diamond(n):
    """
    空心菱形
    只打印边界星号，内部为空格
    """
    print(f"\n📐 空心菱形 (n={n}):")
    # 上半部分
    for i in range(1, n + 1):
        for j in range(n - i):
            print(" ", end="")
        for j in range(2 * i - 1):
            # 只在第一个、最后一个位置打印星号
            if j == 0 or j == 2 * i - 2:
                print("*", end="")
            else:
                print(" ", end="")
        print()
    # 下半部分
    for i in range(1, n):
        for j in range(i):
            print(" ", end="")
        for j in range(2 * (n - i) - 1):
            if j == 0 or j == 2 * (n - i) - 2:
                print("*", end="")
            else:
                print(" ", end="")
        print()


def print_letter_diamond():
    """
    字母菱形：用字母递增来填充菱形
      A
     BBB
    CCCCC
     DDD
      E
    这个版本展示了如何将循环变量映射到不同内容
    """
    print("\n📐 字母菱形:")
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    n = 5  # 上半部分行数

    # 上半部分
    for i in range(1, n + 1):
        spaces = " " * (n - i)
        count = 2 * i - 1
        char = letters[i - 1]
        print(spaces + char * count)

    # 下半部分
    for i in range(1, n):
        spaces = " " * i
        count = 2 * (n - i) - 1
        char = letters[n + i - 1]  # 使用的字母继续递增
        print(spaces + char * count)


def print_table_of_shapes():
    """
    打印多种形状一览，对比不同循环策略
    """
    print("\n" + "=" * 60)
    print("📊 形状生成器一览")
    print("=" * 60)

    n = 5

    shapes = []

    # 形状 1: 直角三角形（左对齐）
    shape1 = ["直角三角形 (左):"]
    for i in range(1, n + 1):
        shape1.append("*" * i)
    shapes.append(shape1)

    # 形状 2: 直角三角形（右对齐）
    shape2 = ["直角三角形 (右):"]
    for i in range(1, n + 1):
        shape2.append(" " * (n - i) + "*" * i)
    shapes.append(shape2)

    # 形状 3: 倒三角形
    shape3 = ["倒三角形:"]
    for i in range(n, 0, -1):
        shape3.append("*" * i)
    shapes.append(shape3)

    # 形状 4: 等腰三角形
    shape4 = ["等腰三角形:"]
    for i in range(1, n + 1):
        shape4.append(" " * (n - i) + "*" * (2 * i - 1))
    shapes.append(shape4)

    # 形状 5: 沙漏
    shape5 = ["沙漏:"]
    for i in range(n, 0, -1):
        shape5.append(" " * (n - i) + "*" * (2 * i - 1))
    for i in range(2, n + 1):
        shape5.append(" " * (n - i) + "*" * (2 * i - 1))
    shapes.append(shape5)

    # 打印所有形状
    for shape in shapes:
        print(f"\n--- {shape[0]} ---")
        for line in shape[1:]:
            print(line)

    print("\n📝 规律总结:")
    print("""
    形状                   空格公式        星号公式
    ─────────────────────────────────────────────
    左三角                 0               i
    右三角                 n - i           i
    等腰三角               n - i           2i - 1
    倒三角                 n - i           2i - 1 (i 递减)
    菱形 (上+下)           见上方           见上方
    """)


def analyze_loop_execution(n):
    """
    分析嵌套循环的执行次数
    """
    print(f"\n🔍 嵌套循环执行次数分析 (n={n}):")

    total = 0
    for i in range(1, n + 1):
        row_iterations = 0
        for j in range(2 * i - 1):
            row_iterations += 1
            total += 1
        print(f"  第{i}行: 内层执行 {row_iterations} 次", end="")
        print(f"  (空格: {n - i}, 星号: {2 * i - 1})")
    print(f"  总计内层执行: {total} 次")

    # 上半部分总数 = 1 + 3 + 5 + ... + (2n-1) = n²
    print(f"  理论值: n² = {n}² = {n * n}")


# ========== 主程序 ==========
if __name__ == "__main__":
    print("=" * 60)
    print("💎 菱形打印与图形输出 — 嵌套循环实战")
    print("=" * 60)

    # 基本菱形
    print_diamond(4)

    # 更大一点的菱形
    print_diamond(6)

    # 紧凑版
    print_diamond_compact(4)

    # 空心菱形
    print_hollow_diamond(4)

    # 字母菱形
    print_letter_diamond()

    # 形状一览
    print_table_of_shapes()

    # 分析执行次数
    analyze_loop_execution(4)

    print("\n" + "=" * 60)
    print("💡 图形输出核心思想")
    print("=" * 60)
    print("""
    所有图形输出 = 空格 + 星号 + 换行

    关键公式:
      第 i 行: 空格数 = f₁(i), 星号数 = f₂(i)

    菱形核心公式（上半部分 n 行）:
      空格数 = n - i
      星号数 = 2i - 1

    要点:
    - 外层循环控制"行"
    - 内层循环控制"列"
    - end="" 阻止 print 自动换行
    - 每个图形都是数学规律的可视化
    """)
