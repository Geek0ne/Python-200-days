"""
Day 029 — 算法入门：实战案例
======================================================================
案例1：排序可视化 — 用柱状图展示排序过程
案例2：搜索算法对比分析器
案例3：随机数生成 + 算法性能测试框架
======================================================================
"""

import random
import time
import sys
import copy

random.seed(42)


# ====================================================================
# 案例1: 排序可视化（字符柱状图）
# ====================================================================
def visual_sort(arr, algorithm, delay=0.05):
    """
    用字符柱状图展示排序过程（Terminal 版本）
    返回排序后的数组
    """
    def display(data, highlight=None):
        """打印柱状图: 每个数字用 █ 块表示"""
        max_val = max(data)
        if max_val == 0:
            return
        # 清空（模拟动画效果）
        print("\033[H", end="")  # 回到光标顶部
        for i, val in enumerate(data):
            bar_len = int(val / max_val * 30)
            bar = "█" * bar_len
            marker = " ◀" if highlight and i in highlight else ""
            print(f"  {val:3d} |{bar:<30}{marker}")

    print("\033[2J")  # 清屏
    print(f"  🔄 排序算法: {algorithm.__name__}")
    print("─" * 45)

    if algorithm in [selection_sort_vis]:
        # 选择排序
        arr_copy = arr.copy()
        n = len(arr_copy)
        for i in range(n - 1):
            min_idx = i
            for j in range(i + 1, n):
                if arr_copy[j] < arr_copy[min_idx]:
                    min_idx = j
            arr_copy[i], arr_copy[min_idx] = arr_copy[min_idx], arr_copy[i]
            display(arr_copy, highlight=[i, min_idx])
            print(f"\n  🎯 第{i+1}趟: 将 {arr_copy[i]} 放到位置 {i}")
            time.sleep(delay)

    elif algorithm in [bubble_sort_vis]:
        # 冒泡排序
        arr_copy = arr.copy()
        n = len(arr_copy)
        for i in range(n - 1):
            for j in range(n - 1 - i):
                if arr_copy[j] > arr_copy[j + 1]:
                    arr_copy[j], arr_copy[j + 1] = arr_copy[j + 1], arr_copy[j]
                display(arr_copy, highlight=[j, j+1])
                time.sleep(delay / 2)
            display(arr_copy, highlight=[n-1-i])
            print(f"\n  💨 第{i+1}趟: {arr_copy[n-1-i]} 已冒泡到位")
            time.sleep(delay * 0.5)

    elif algorithm in [insertion_sort_vis]:
        arr_copy = arr.copy()
        for i in range(1, len(arr_copy)):
            key = arr_copy[i]
            j = i - 1
            while j >= 0 and arr_copy[j] > key:
                arr_copy[j + 1] = arr_copy[j]
                j -= 1
            arr_copy[j + 1] = key
            display(arr_copy, highlight=[j+1, i])
            print(f"\n  🃏 第{i}步: 插入 {key} 到位置 {j+1}")
            time.sleep(delay)

    return arr_copy


def selection_sort_vis(arr):
    return arr  # 占位，实际在 visual_sort 中实现


def bubble_sort_vis(arr):
    return arr


def insertion_sort_vis(arr):
    return arr


print("=" * 60)
print("案例1: 排序可视化")
print("=" * 60)

# 使用小数组以便视觉上清晰
demo_arr = [5, 3, 8, 1, 7, 2, 6, 4]
print("\n  ⚠️  可视化排序需要终端支持 ANSI 控制码")
print("  建议手动运行此脚本查看效果")
print("  展示排序算法: 冒泡、选择、插入")
print(f"  示例数组: {demo_arr}")
print()


# ====================================================================
# 案例2: 搜索算法对比分析器
# ====================================================================
class SearchBenchmark:
    """搜索算法性能对比工具"""

    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.results = {"linear": [], "binary": []}

    def run_benchmark(self):
        """测试不同数据规模下的搜索性能"""
        sizes = [100, 500, 1000, 5000, 10000, 50000]
        print(f"\n{'数据规模':<10} {'线性搜索':<15} {'二分搜索':<15} {'提速比':<10}")
        print("-" * 50)

        for size in sizes:
            if size > self.max_size:
                break

            # 生成测试数据
            data = sorted(random.sample(range(size * 10), size))
            target = random.choice(data)

            # 线性搜索
            start = time.perf_counter_ns()
            for _ in range(100):
                for i, v in enumerate(data):
                    if v == target:
                        break
            linear_time = (time.perf_counter_ns() - start) / 100

            # 二分搜索
            start = time.perf_counter_ns()
            for _ in range(1000):  # 二分快得多，多测几次
                low, high = 0, len(data) - 1
                found = False
                while low <= high and not found:
                    mid = (low + high) // 2
                    if data[mid] == target:
                        found = True
                    elif data[mid] < target:
                        low = mid + 1
                    else:
                        high = mid - 1
            binary_time = (time.perf_counter_ns() - start) / 1000

            ratio = linear_time / max(binary_time, 1)
            print(f"{size:<10} {linear_time/1e3:<15.2f} {binary_time/1e3:<15.2f} {ratio:<10.1f}×")

            self.results["linear"].append((size, linear_time))
            self.results["binary"].append((size, binary_time))

        return self.results

    def summary_report(self):
        """生成总结报告"""
        print("\n" + "=" * 50)
        print("📊 搜索算法总结报告")
        print("=" * 50)
        print("\n  线性搜索 (Linear Search)")
        print("  ├── 时间复杂度: O(n)")
        print("  ├── 适用场景: 无序数据、小规模数据")
        print("  └── 优点: 实现简单，无需预处理")

        print("\n  二分搜索 (Binary Search)")
        print("  ├── 时间复杂度: O(log n)")
        print("  ├── 适用场景: 有序数据、大规模数据")
        print("  ├── 优点: 极快，数据越大优势越明显")
        print("  └── 缺点: 要求数据已排序")

        # 理论值验证
        if self.results["linear"] and self.results["binary"]:
            size = self.results["linear"][-1][0]
            linear_t = self.results["linear"][-1][1]
            binary_t = self.results["binary"][-1][1]
            theoretical_ratio = size / (size ** 0.5)  # 约 n / log₂n

            print(f"\n  📐 理论验证 (n={size}):")
            print(f"  ├── 实际搜索次数: 线性≈{size}, 二分≈{int(size**0.5)}")
            print(f"  ├── 实际耗时比: {linear_t/max(binary_t,1):.1f}×")
            print(f"  └── 理论比值: O(n)/O(log n) ≈ {size / (size**0.5):.0f}×")


print("\n" + "=" * 60)
print("案例2: 搜索算法对比分析器")
print("=" * 60)

benchmark = SearchBenchmark(max_size=50000)
benchmark.run_benchmark()
benchmark.summary_report()


# ====================================================================
# 案例3: 算法性能测试框架
# ====================================================================
class SortBenchmark:
    """排序算法性能测试框架"""

    def __init__(self):
        self.algorithms = {}
        self.test_cases = {}

    def register(self, name, func):
        """注册排序算法"""
        self.algorithms[name] = func
        return self

    def add_test(self, name, generator, n=1000):
        """添加测试用例"""
        self.test_cases[name] = (generator, n)
        return self

    def run_all(self):
        """运行所有测试"""
        if not self.algorithms or not self.test_cases:
            print("⚠️  请先注册算法和测试用例")
            return

        print(f"\n{'算法':<18}", end="")
        for case_name in self.test_cases:
            print(f"{case_name:<22}", end="")
        print(f"{'平均':<10}")
        print("-" * (18 + 22 * len(self.test_cases) + 10))

        results = {}
        for algo_name, algo_func in self.algorithms.items():
            times = []
            print(f"{algo_name:<18}", end="")
            sys.stdout.flush()

            for case_name, (generator, n) in self.test_cases.items():
                try:
                    data = generator(n)
                    arr = data.copy()
                    start = time.perf_counter()
                    algo_func(arr)
                    elapsed = time.perf_counter() - start
                    times.append(elapsed)
                    print(f"{elapsed:<22.4f}", end="")
                except RecursionError:
                    print(f"{'RecursionError':<22}", end="")
                    times.append(float('inf'))
                except Exception as e:
                    print(f"{str(e)[:20]:<22}", end="")
                    times.append(float('inf'))
                sys.stdout.flush()

            avg = sum(t for t in times if t != float('inf'))
            count = sum(1 for t in times if t != float('inf'))
            print(f"{avg/max(count,1):<10.4f}" if count else "---")

            results[algo_name] = times

        return results


def generate_random(n):
    return [random.randint(1, 10000) for _ in range(n)]


def generate_sorted(n):
    return list(range(n))


def generate_reversed(n):
    return list(range(n, 0, -1))


def generate_duplicates(n):
    return [random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) for _ in range(n)]


# ====================================================================
# 排序函数（供测试框架使用）
# ====================================================================
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)

def _merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr


def quick_sort_wrapper(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    mid = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort_wrapper(left) + mid + quick_sort_wrapper(right)


# 使用测试框架
print("\n" + "=" * 60)
print("案例3: 算法性能测试框架")
print("=" * 60)

# 小规模测试 n=300 避免递归错误
framework = (
    SortBenchmark()
    .register("Timsort", lambda arr: sorted(arr))
    .register("归并排序", merge_sort)
    .register("插入排序", insertion_sort)
    .register("快速排序", quick_sort_wrapper)
    .add_test("随机数据", generate_random, 300)
    .add_test("已排序", generate_sorted, 300)
    .add_test("逆序", generate_reversed, 300)
    .add_test("大量重复", generate_duplicates, 300)
)

results = framework.run_all()


# ====================================================================
# 总结
# ====================================================================
print("\n" + "=" * 60)
print("🏆  实战总结")
print("=" * 60)
print(f"""
  📌 排序算法选择策略:
     • 通用: Python 内置 sorted()/list.sort() — Timsort O(n log n)
     • 稳定性优先: 归并排序
     • 空间敏感: 快速排序（原地版本）
     • 小数据/近乎有序: 插入排序

  📌 搜索算法选择策略:
     • 无序数据: 线性搜索 O(n)
     • 有序数据: 二分搜索 O(log n) — 总是更优

  📌 实际应用建议:
     • 用 sorted() 替代手写排序（Timsort 非常快）
     • 用 bisect 模块维护有序列表
     • 关注数据特征选算法（规模、分布、稳定性需求）
""")
print("=" * 60)
print("✅  实战案例全部完成！")
print("=" * 60)
