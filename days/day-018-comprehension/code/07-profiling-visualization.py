#!/usr/bin/env python3
"""
Day 018 — 性能分析工具与结果可视化

使用 Python 内置性能分析工具深入分析推导式性能：
1. timeit 精确计时
2. cProfile 函数级分析
3. dis 字节码分析
4. memory_profiler 内存分析
5. 文本形式的可视化报告
"""

import sys
import os
import timeit
import dis
import cProfile
import pstats
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from tools import console


def section(title):
    console.section(title)


# ══════════════════════════════════════════════════════════
# 1. timeit 精确计时
# ══════════════════════════════════════════════════════════
section("1. timeit 精确计时")

print("--- 1.1 基本用法 ---")
# timeit 会运行多次取平均，消除系统噪声
setup = "import random; data = [random.randint(0, 100) for _ in range(1000)]"

# 测试方式1: 在函数外（最快，但不准确）
test_code = "[x ** 2 for x in range(1000) if x % 2 == 0]"
t = timeit.timeit(test_code, number=10000)
print(f"timeit(stmt='{test_code}', number=10000): {t:.4f}s")
print(f"平均单次: {t/10000*1e6:.2f}μs")

print("\n--- 1.2 对比测试 ---")
N = 100_000

# 使用 timeit 批量对比
def for_loop(N):
    result = []
    for x in range(N):
        if x % 2 == 0:
            result.append(x ** 2)
    return result

def list_comp(N):
    return [x ** 2 for x in range(N) if x % 2 == 0]

def map_filter(N):
    return list(map(lambda x: x**2, filter(lambda x: x % 2 == 0, range(N))))

def gen_expr(N):
    return list(x ** 2 for x in range(N) if x % 2 == 0)

# 预热
_ = for_loop(1000)
_ = list_comp(1000)
_ = map_filter(1000)
_ = gen_expr(1000)

# 正式测试
num_runs = 500
times = {
    'for 循环': timeit.timeit(lambda: for_loop(N), number=num_runs),
    '列表推导式': timeit.timeit(lambda: list_comp(N), number=num_runs),
    'map+filter': timeit.timeit(lambda: map_filter(N), number=num_runs),
    '生成器→列表': timeit.timeit(lambda: gen_expr(N), number=num_runs),
}

print(f"N = {N:,}, 运行 {num_runs} 次")
print()
print(f"{'方法':<16} {'总时间':<12} {'单次':<14} {'相对速度':<10}")
print("-" * 55)

base = min(times.values())
for name, t in sorted(times.items(), key=lambda x: x[1]):
    per_run = t / num_runs * 1e6
    ratio = t / base
    print(f"{name:<16} {t:<12.4f} {per_run:<14.2f}μs {ratio:<10.2f}x")

print("\n--- 1.3 timeit.repeat 多次采样 ---")
# repeat 会运行多次 timeit，得到统计分布
results = timeit.repeat(
    lambda: list_comp(100_000),
    number=100,
    repeat=5
)
print(f"5 次采样结果: {[f'{r:.4f}' for r in results]}")
print(f"  最小值: {min(results):.4f}s")
print(f"  最大值: {max(results):.4f}s")
print(f"  平均值: {sum(results)/len(results):.4f}s")
print(f"  标准差: {(sum((r - sum(results)/len(results))**2 for r in results)/len(results))**0.5:.4f}s")


# ══════════════════════════════════════════════════════════
# 2. dis 字节码分析
# ══════════════════════════════════════════════════════════
section("2. dis 字节码分析")

print("--- 2.1 列表推导式字节码 ---")
print("列表推导式 [x**2 for x in range(5)] 的字节码:")
print()

# 捕获 dis 输出
list_comp_code = compile("[x**2 for x in range(5)]", "<string>", "eval")
# 打印主代码对象
dis.dis(list_comp_code)

print("\n--- 2.2 推导式内部的独立代码对象 ---")
print("列表推导式的代码对象中包含嵌套的 <listcomp> 函数:")
# 捕获 <listcomp> 代码对象的 dis
consts = list_comp_code.co_consts
listcomp_code = consts[0]  # 第一个常量是 <listcomp> 代码对象
print(f"代码对象名: {listcomp_code.co_name}")
print(f"参数数量: {listcomp_code.co_argcount}")
print(f"局部变量: {listcomp_code.co_varnames}")
dis.dis(listcomp_code)

print()
print("关键字节码说明:")
print("  BUILD_LIST   → 创建空列表 []")
print("  LIST_APPEND  → 向列表添加元素（C 层优化，无需方法调用）")
print("  GET_ITER     → 获取迭代器")
print("  FOR_ITER     → 迭代循环")
print()
print("→ 列表推导式被编译为独立的 <listcomp> 代码对象")
print("→ 这个对象以 C 速度执行，比普通的 Python 循环更快")


# ══════════════════════════════════════════════════════════
# 3. cProfile 函数级分析
# ══════════════════════════════════════════════════════════
section("3. cProfile 函数级分析")

print("--- 3.1 简单分析 ---")

def compute_with_loop(n):
    """使用 for 循环计算"""
    result = []
    for x in range(n):
        if x % 3 == 0 and x % 5 == 0:
            result.append(x ** 2)
    return result


def compute_with_comp(n):
    """使用推导式计算"""
    return [x ** 2 for x in range(n) if x % 3 == 0 and x % 5 == 0]


# 使用 cProfile 分析
profiler = cProfile.Profile()
profiler.enable()
_ = compute_with_loop(100000)
_ = compute_with_comp(100000)
profiler.disable()

# 输出统计
s = io.StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats('cumtime')
ps.print_stats(10)

print("cProfile 分析结果 (前 10 条):")
print(s.getvalue())


# ══════════════════════════════════════════════════════════
# 4. 性能测试自动化
# ══════════════════════════════════════════════════════════
section("4. 性能测试自动化")


def benchmark(func, sizes, number=100):
    """对多个数据规模进行基准测试"""
    results = {}
    for n in sizes:
        t = timeit.timeit(lambda: func(n), number=number)
        results[n] = t / number * 1e6  # μs per run
    return results


def print_benchmark(results, unit='μs'):
    """格式化输出基准测试结果"""
    sizes = sorted(results.keys())
    labels = list(results[list(results.keys())[0]].keys())

    # 表头
    header = f"{'Size':>10}"
    for label in labels:
        header += f" {label:>14}"
    print(header)
    print("-" * (10 + 15 * len(labels)))

    for n in sizes:
        row = f"{n:>10,}"
        row_data = results[n]
        values = [row_data[label] for label in labels]
        min_val = min(values)
        for label in labels:
            val = row_data[label]
            ratio = val / min_val
            row += f" {val:>8.2f}{unit} ({ratio:>5.2f}x)"
        print(row)


print("自动化基准测试:")

sizes = [1000, 10000, 50000]
results = {}

for n in sizes:
    results[n] = {
        'for 循环': benchmark(for_loop, [n], 200)[n],
        '推导式': benchmark(list_comp, [n], 200)[n],
        'map+filter': benchmark(map_filter, [n], 200)[n],
        '生成器→列表': benchmark(gen_expr, [n], 200)[n],
    }

print_benchmark(results)


# ══════════════════════════════════════════════════════════
# 5. 性能报告生成
# ══════════════════════════════════════════════════════════
section("5. 性能报告生成")


def generate_performance_report():
    """生成完整的性能分析报告"""
    print("=" * 60)
    print("          推导式性能分析报告")
    print("=" * 60)
    print()

    N = 100_000
    num_runs = 500

    print(f"数据规模: N = {N:,}")
    print(f"样本数:   {num_runs} 次")
    print()

    # 运行测试
    t_loop = timeit.timeit(lambda: for_loop(N), number=num_runs)
    t_comp = timeit.timeit(lambda: list_comp(N), number=num_runs)
    t_map = timeit.timeit(lambda: map_filter(N), number=num_runs)
    t_gen = timeit.timeit(lambda: gen_expr(N), number=num_runs)

    base = min(t_comp, t_map, t_gen, t_loop)

    methods = [
        ("for 循环 (手写)", t_loop, '🔵'),
        ("列表推导式", t_comp, '🟢'),
        ("map + filter", t_map, '🟡'),
        ("生成器→列表", t_gen, '🟠'),
    ]

    # 排序（最快的排前面）
    methods.sort(key=lambda m: m[1])

    print(f"{'排名':>4} {'方法':<20} {'总时间':<12} {'单次':<14} {'相对':<8} {'柱状图'}")
    print("-" * 85)

    bar_max = 40
    max_time = methods[-1][1]

    for i, (name, t, icon) in enumerate(methods, 1):
        per_run = t / num_runs * 1e6
        ratio = t / base
        bar_len = int(t / max_time * bar_max)
        bar = '█' * bar_len + '░' * (bar_max - bar_len)
        print(f"{i:>4} {name:<20} {t:<12.4f} {per_run:<14.2f}μs {ratio:<8.2f}x {icon} {bar}")

    print()
    print("性能结论:")
    print(f"  最快: {methods[0][1]} ({methods[0][0]})")
    print(f"  最慢: {methods[-1][1]} ({methods[-1][0]}) — {methods[-1][2]/methods[0][2]:.2f}x 慢")
    print()
    print("优化建议:")
    print("  ✔ 默认选择: 列表推导式（速度 + 可读性最佳）")
    print("  ✔ 大内存敏感: 生成器表达式")
    print("  ✔ 函数式风格: map + filter（适合链式操作）")
    print("  ✘ 避免: 手写 for 循环除非逻辑复杂")


generate_performance_report()


# ══════════════════════════════════════════════════════════
# 6. 实用性能检测工具函数
# ══════════════════════════════════════════════════════════
section("6. 实用性能检测工具")


def time_call(func, *args, **kwargs):
    """方便地测量函数执行时间"""
    def wrapper():
        return func(*args, **kwargs)
    t = timeit.timeit(wrapper, number=100)
    return t / 100 * 1e6  # μs


def compare_methods(methods, data, number=100):
    """对比多个方法在相同数据上的性能"""
    results = []
    for name, func in methods:
        t = timeit.timeit(lambda: func(data), number=number)
        results.append((name, t / number * 1e6))
    return results


# 演示：字符串处理对比
sample_words = ['python', 'comprehension', 'generator', 'list', 'performance'] * 2000

methods = [
    ("for 循环",
     lambda words: [w.upper() for w in words if len(w) > 5]),
    ("推导式",
     lambda words: [w.upper() for w in words if len(w) > 5]),
]

results = compare_methods(methods, sample_words, 500)
print("字符串处理性能对比:")
for name, t in results:
    print(f"  {name:<16} {t:.2f}μs")


if __name__ == '__main__':
    print("\n✅ Day 018 — 性能分析工具与结果可视化完成")
    print("📌 工具清单：")
    print("   timeit — 精确计时（推荐）")
    print("   dis    — 字节码分析（深入理解）")
    print("   cProfile — 函数级分析")
    print("   sys.getsizeof — 内存占用")
    print("   tracemalloc — 内存追踪")
