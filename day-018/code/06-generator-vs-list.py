#!/usr/bin/env python3
"""
Day 018 — 生成器表达式详解与对比

深入对比生成器表达式与列表推导式的各方面差异：
1. 惰性求值 vs 急切求值
2. 内存占用对比
3. 迭代器特性
4. 链式处理
5. 实际应用场景
"""

import sys
import os
import tracemalloc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title):
    console.section(title)


# ══════════════════════════════════════════════════════════
# 1. 核心差异演示
# ══════════════════════════════════════════════════════════
section("1. 核心差异演示")

print("--- 1.1 类型不同 ---")
list_comp = [x ** 2 for x in range(5)]
gen_expr = (x ** 2 for x in range(5))

print(f"列表推导式: type = {type(list_comp).__name__}, 值 = {list_comp}")
print(f"生成器表达式: type = {type(gen_expr).__name__}, 值 = {gen_expr}")

print("\n--- 1.2 惰性求值 ---")
print("生成器表达式直到被迭代时才计算:")

def track(name):
    """带日志的生成器"""
    for i in range(3):
        print(f"  {name}: 生成 {i}")
        yield i

print("定义生成器表达式...")
gen = (x * 2 for x in track("GEN"))
print("生成器对象已创建（未执行任何计算）")
print("开始迭代...")
result = list(gen)
print(f"完成: {result}")

print("\n--- 1.3 列表推导式立即计算 ---")
print("列表推导式会在定义时立刻计算全部元素:")
result = [x * 2 for x in track("LIST")]
print(f"完成: {result}")


# ══════════════════════════════════════════════════════════
# 2. 内存占用对比
# ══════════════════════════════════════════════════════════
section("2. 内存占用对比")

print("--- 2.1 小数据量对比 ---")
N = 10_000

# 列表推导式
list_result = [x ** 2 for x in range(N)]
list_size = sys.getsizeof(list_result)
# 粗略估算每个 int 对象的大小
list_total = list_size + len(list_result) * 28

# 生成器表达式
gen_result = (x ** 2 for x in range(N))
gen_size = sys.getsizeof(gen_result)

print(f"N = {N:,}")
print(f"列表推导式:  列表对象 = {list_size:,} bytes")
print(f"          + int 对象 ≈ {len(list_result) * 28:,} bytes")
print(f"          总计 ≈ {list_total:,} bytes ({list_total/1024:.1f} KB)")
print(f"生成器表达式: 对象 = {gen_size:,} bytes ({gen_size/1024:.3f} KB)")
print(f"内存比例: {list_total / gen_size:.0f}x")

print("\n--- 2.2 验证生成器不创建完整列表 ---")
print("创建 10,000,000 个元素的平方...")

# 大 N
BIG_N = 10_000_000

# 列表推导式
import tracemalloc
tracemalloc.start()
big_list = [x ** 2 for x in range(BIG_N)]
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"列表推导式: 峰值内存 ≈ {peak / 1024 / 1024:.1f} MB")

tracemalloc.start()
big_gen = (x ** 2 for x in range(BIG_N))
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f"生成器表达式: 峰值内存 ≈ {peak / 1024 / 1024:.1f} MB (几乎为零！)")

# 释放
del big_list, big_gen


# ══════════════════════════════════════════════════════════
# 3. 迭代器特性
# ══════════════════════════════════════════════════════════
section("3. 迭代器特性")

print("--- 3.1 生成器只能迭代一次 ---")
gen = (x for x in range(5))
print(f"第一次 list(): {list(gen)}")
print(f"第二次 list(): {list(gen)}")  # []
print("→ 生成器耗尽后不可重用")

print("\n--- 3.2 手动迭代 ---")
gen = (x for x in range(3))
print(f"next(): {next(gen)}")
print(f"next(): {next(gen)}")
print(f"next(): {next(gen)}")
try:
    next(gen)
except StopIteration:
    print("StopIteration: 生成器已耗尽")

print("\n--- 3.3 for 循环迭代 ---")
gen = (x * 10 for x in range(3))
for val in gen:
    print(f"  for: {val}")
# 再次 for 循环，无输出
print("再次 for 循环:")
for val in gen:
    print(f"  for: {val}")
print("  (无输出，生成器已空)")

print("\n--- 3.4 列表可以多次迭代 ---")
lst = [x * 10 for x in range(3)]
print("第一次 for:")
for val in lst:
    print(f"  {val}")
print("第二次 for:")
for val in lst:
    print(f"  {val}")


# ══════════════════════════════════════════════════════════
# 4. 链式处理
# ══════════════════════════════════════════════════════════
section("4. 链式处理")

print("--- 4.1 生成器链（不创建中间列表） ---")
def get_numbers(n):
    """模拟产生大量数据"""
    for i in range(n):
        yield i

nums = get_numbers(100_000)

# 链式处理：过滤 → 映射 → 聚合，全部惰性
result = sum(
    x ** 2
    for x in nums
    if x % 2 == 0
    if x > 10
)
print(f"链式处理结果: {result}")
print("→ 整个过程没有创建任何中间列表！")

print("\n--- 4.2 列表推导式链会创建中间列表 ---")
# ❌ 每次推导式都会创建新的列表
N = 100_000
step1 = [x for x in range(N) if x % 2 == 0]   # 创建列表 1
step2 = [x ** 2 for x in step1]                # 创建列表 2
result = sum(step2)
print(f"列表链结果: {result}")
print("→ 创建了两个大型中间列表！")

# ✅ 用生成器表达式避免中间列表
step1_gen = (x for x in range(N) if x % 2 == 0)
step2_gen = (x ** 2 for x in step1_gen)
result = sum(step2_gen)
print(f"生成器链结果: {result}")
print("→ 没有创建任何中间列表！")

print("\n--- 4.3 用括号省略生成器表达式 ---")
# 函数调用时，生成器表达式的外层括号可以省略
result = sum(x ** 2 for x in range(1000) if x % 2 == 0)
print(f"sum(gen): {result}")

# 但如果有多个参数，需要括号
function_result = max(
    (x ** 2 for x in range(100) if x % 2 == 0),
    default=0
)
print(f"max(gen): {function_result}")


# ══════════════════════════════════════════════════════════
# 5. 何时使用生成器表达式
# ══════════════════════════════════════════════════════════
section("5. 何时使用生成器表达式")

print("--- 5.1 应用场景 ---")
print("✅ 大数据量（超过 10 万元素）：使用生成器节省内存")
print("✅ 仅需迭代一次：如传给 sum(), max(), min(), any(), all()")
print("✅ 流式处理：数据源源源不断产生")
print("✅ 无限序列：如斐波那契数列")
print()
print("❌ 只需要较小的列表")
print("❌ 需要多次迭代")
print("❌ 需要下标访问或切片")
print("❌ 需要在迭代过程中修改内容")

print("\n--- 5.2 实用例子：读取大文件 ---")
# 模拟大文件处理
big_file_lines = [f"line {i}" for i in range(100)]  # 模拟

# 使用生成器表达式处理
total_chars = sum(len(line) for line in big_file_lines)
print(f"总字符数: {total_chars}")

# 找到最长的行
max_len = max(len(line) for line in big_file_lines)
print(f"最长行长度: {max_len}")

# 检查是否所有行都包含 'line'
all_contain = all('line' in line for line in big_file_lines)
print(f"所有行都包含 'line': {all_contain}")

# 是否有空行
any_empty = any(not line.strip() for line in big_file_lines)
print(f"存在空行: {any_empty}")

print("\n--- 5.3 保存为列表 vs 生成器的选择 ---")
NEED_REUSE = False  # 是否多次使用
NEED_INDEX = False  # 是否需要下标访问
NEED_MUTATE = False # 是否需要修改
DATA_IS_LARGE = True  # 数据是否很大

if DATA_IS_LARGE and not NEED_REUSE:
    print(f"→ 使用生成器表达式")
elif NEED_REUSE or NEED_INDEX or NEED_MUTATE:
    print(f"→ 使用列表推导式")
else:
    print(f"→ 可以使用任何一种，根据喜好选择")


if __name__ == '__main__':
    print("\n✅ Day 018 — 生成器表达式详解与对比完成")
    print("📌 核心区别：")
    print("   列表推导式 = 内存换便利（可索引、可复用）")
    print("   生成器表达式 = 时间换内存（惰性、一次性）")
    print("   选择依据：数据大小 + 使用方式")
