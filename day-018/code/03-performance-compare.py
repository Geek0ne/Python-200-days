#!/usr/bin/env python3
"""
Day 018 — 性能对比：推导式 vs 循环 vs map/filter

对四种实现方式进行详细的性能基准测试：
1. 手写 for 循环
2. 列表推导式
3. map + filter + lambda
4. 生成器表达式 → 列表

结论通过实际数据验证，包含数据可视化的文本报告。
"""

import sys
import os
import timeit
import math
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title: str):
    console.section(title)


# ══════════════════════════════════════════════════════════
# 1. 基础性能对比
# ══════════════════════════════════════════════════════════
section("1. 基础性能基准测试")

# 测试场景：对 [1..N] 中的偶数求平方
# 四种实现方式

def for_loop(N):
    """手写 for 循环"""
    result = []
    for x in range(N):
        if x % 2 == 0:
            result.append(x ** 2)
    return result


def list_comp(N):
    """列表推导式"""
    return [x ** 2 for x in range(N) if x % 2 == 0]


def map_filter(N):
    """map + filter + lambda"""
    return list(map(lambda x: x**2, filter(lambda x: x % 2 == 0, range(N))))


def gen_expr(N):
    """生成器表达式 → 列表"""
    return list(x ** 2 for x in range(N) if x % 2 == 0)


# 验证四种方式结果相同
N = 100
r1 = for_loop(N)
r2 = list_comp(N)
r3 = map_filter(N)
r4 = gen_expr(N)
assert r1 == r2 == r3 == r4, "四种实现结果不一致！"
print(f"✅ 四种实现结果一致（前10个: {r1[:10]}）")

# 不同数据规模
sizes = [1000, 10_000, 100_000, 500_000]
num_runs = 100  # 小次数热身

print(f"\n{'大小':>10} {'for循环':>12} {'推导式':>12} {'map/filter':>12} {'生成器':>12}")
print("-" * 60)

for size in sizes:
    # 对每种实现运行多次求平均
    t_for = timeit.timeit(lambda: for_loop(size), number=num_runs)
    t_comp = timeit.timeit(lambda: list_comp(size), number=num_runs)
    t_map = timeit.timeit(lambda: map_filter(size), number=num_runs)
    t_gen = timeit.timeit(lambda: gen_expr(size), number=num_runs)

    # 归一化（以最快的推导式为基准 1.0）
    min_t = min(t_for, t_comp, t_map, t_gen)

    print(f"{size:>10,} "
          f"{t_for/t_comp:>11.2f}x "
          f"{t_comp/t_comp:>11.2f}x "
          f"{t_map/t_comp:>11.2f}x "
          f"{t_gen/t_comp:>11.2f}x"
          f"  (推导式 = {t_comp*1000/num_runs:.3f}ms/run)")

print()
print("相对性能 (推导式 = 1.0x, 越小越快):")
print("  for 循环      — 最慢")
print("  列表推导式    — 通常最快")
print("  map + filter  — 接近推导式")
print("  生成器表达式  — 介于两者之间（迭代开销）")


# ══════════════════════════════════════════════════════════
# 2. 复杂操作性能对比
# ══════════════════════════════════════════════════════════
section("2. 复杂操作性能对比")

# 更复杂的数据处理：字符串操作
def for_loop_strings(words):
    result = []
    for w in words:
        if len(w) > 3:
            result.append(w.upper())
    return result


def comp_strings(words):
    return [w.upper() for w in words if len(w) > 3]


def map_filter_strings(words):
    return list(map(str.upper, filter(lambda w: len(w) > 3, words)))


# 生成测试数据
random.seed(42)
sample_words = []
for _ in range(10000):
    length = random.randint(2, 15)
    word = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(length))
    sample_words.append(word)

print(f"测试数据: {len(sample_words):,} 个随机单词")

t_for = timeit.timeit(lambda: for_loop_strings(sample_words), number=1000)
t_comp = timeit.timeit(lambda: comp_strings(sample_words), number=1000)
t_map = timeit.timeit(lambda: map_filter_strings(sample_words), number=1000)

print(f"\n{'方法':<20} {'总时间(秒)':<15} {'相对速度':<15}")
print("-" * 50)
print(f"{'for 循环':<20} {t_for:<15.3f} {t_for/t_comp:<15.2f}x")
print(f"{'列表推导式':<20} {t_comp:<15.3f} {t_comp/t_comp:<15.2f}x (基准)")
print(f"{'map + filter':<20} {t_map:<15.3f} {t_map/t_comp:<15.2f}x")


# ══════════════════════════════════════════════════════════
# 3. 内存使用对比
# ══════════════════════════════════════════════════════════
section("3. 内存使用对比")


def mem_usage(obj):
    """估算对象内存占用（bytes）"""
    # 粗略估算：列表对象本身 + 每个元素
    if isinstance(obj, list):
        # 64-bit Python: 每个 int ~28 bytes, 列表指针 ~8 bytes/elem
        elem_size = 28 if obj and isinstance(obj[0], int) else 50
        return sys.getsizeof(obj) + len(obj) * elem_size
    if hasattr(obj, '__next__'):
        return sys.getsizeof(obj)
    return sys.getsizeof(obj)


# 比较列表推导式和生成器表达式的内存
N = 100_000

list_result = [x ** 2 for x in range(N)]  # 列表：所有元素在内存
gen_result = (x ** 2 for x in range(N))   # 生成器：只保存状态

list_size = mem_usage(list_result)
gen_size = mem_usage(gen_result)

print(f"N = {N:,}")
print(f"{'列表推导式':<20} {list_size:>12,} bytes ({list_size/1024:.1f} KB)")
print(f"{'生成器表达式':<20} {gen_size:>12,} bytes ({gen_size/1024:.3f} KB)")
print(f"{'内存比例':<20} {list_size/gen_size:>12.1f}x")
print()
print("→ 生成器在迭代数据时几乎不占内存！")
print("→ 但只能遍历一次，且不能索引访问")


# ══════════════════════════════════════════════════════════
# 4. 嵌套推导式性能
# ══════════════════════════════════════════════════════════
section("4. 嵌套推导式性能")

matrix = [[random.randint(0, 100) for _ in range(500)] for _ in range(500)]

print(f"矩阵大小: {len(matrix)}×{len(matrix[0])}")

# 扁平化性能比较
def for_flat(mat):
    result = []
    for row in mat:
        for x in row:
            result.append(x)
    return result


def comp_flat(mat):
    return [x for row in mat for x in row]


def sum_flat(mat):
    """扁平化后求所有元素平方和"""
    # 方式1: 列表推导式 → sum
    t1 = timeit.timeit(lambda: sum([x ** 2 for row in mat for x in row]), number=10)

    # 方式2: 生成器表达式 → sum（更优）
    t2 = timeit.timeit(lambda: sum(x ** 2 for row in mat for x in row), number=10)

    return t1, t2


t_sum_list, t_sum_gen = sum_flat(matrix)
print(f"\n矩阵元素平方和性能:")
print(f"{'列表推导式 + sum':<25} {t_sum_list:.4f}s")
print(f"{'生成器表达式 + sum':<25} {t_sum_gen:.4f}s")
print(f"{'加速比':<25} {t_sum_list/t_sum_gen:.2f}x (生成器更快)")
print()
print("→ 传递数据到 sum() 时，生成器表达式避免创建中间列表")
print("→ 这是推荐模式：sum(x**2 for x in data) 优于 sum([x**2 for x in data])")


# ══════════════════════════════════════════════════════════
# 5. 性能可视化 (文本图表)
# ══════════════════════════════════════════════════════════
section("5. 性能可视化")

print("性能对比柱状图 (N=100,000):")
print()

bars = []

# 运行一次大测试
N = 100_000
t_for = timeit.timeit(lambda: for_loop(N), number=100)
t_comp = timeit.timeit(lambda: list_comp(N), number=100)
t_map = timeit.timeit(lambda: map_filter(N), number=100)
t_gen = timeit.timeit(lambda: gen_expr(N), number=100)

max_t = max(t_for, t_comp, t_map, t_gen)
scale = 50  # 最大柱长

data = [
    ("for循环    ", t_for, '🔵'),
    ("推导式     ", t_comp, '🟢'),
    ("map+filter ", t_map, '🟡'),
    ("生成器→列表", t_gen, '🟠'),
]

for label, t, icon in data:
    bar_len = int(t / max_t * scale)
    bar = '█' * bar_len
    pct = t / t_comp * 100
    print(f"  {label} {icon} {bar:<{scale}} {t*1000/100:.3f}ms ({pct:.0f}%)")

print()
print("结论:")
print("  🥇 列表推导式 — 综合最快（C 层优化 + 无函数调用开销）")
print("  🥈 map+filter — 稍慢于推导式（lambda 函数调用开销）")
print("  🥉 生成器表达式 — 内存最优，迭代略慢")
print("  🏅 for 循环 — 最慢（字节码多，方法查找开销）")
print()
print("但是！如果 for 循环的代码更容易理解，选 for 循环。")
print("性能差异在可读性面前常常不值一提。")


# ══════════════════════════════════════════════════════════
# 6. 何时推导式不合适
# ══════════════════════════════════════════════════════════
section("6. 何时推导式不合适")

print("场景 1 — 复杂逻辑（超过两层嵌套）:")
print("  ❌ [transform(process(item)) for lst in data for item in lst if check(item) if validate(item)]")
print("  ✅ 拆分成多步或使用普通循环")

print("\n场景 2 — 有副作用的操作:")
print("  ❌ [print(x) for x in data]")
print("  ✅ for x in data: print(x)")

print("\n场景 3 — 需要跳过大量中间迭代:")
print("  ❌ [expensive(x) for x in generator if condition(x)]  # 每次都要计算条件")
print("  ✅ filter(lambda x: condition(x), generator)  # 惰性求值")

print("\n场景 4 — 大型数据不需要列表:")
print("  ❌ total = sum([x**2 for x in range(10_000_000)])  # 创建大型中间列表")
print("  ✅ total = sum(x**2 for x in range(10_000_000))    # 使用生成器")


if __name__ == '__main__':
    print("\n✅ Day 018 — 性能对比分析完成")
    print("📌 性能总结：")
    print("   1. 列表推导式通常是最快的选择")
    print("   2. 大数据用生成器表达式节省内存")
    print("   3. 可读性 > 性能优化，除非瓶颈已确认")
    print("   4. 不同实现方式的结果可以完全等价")
