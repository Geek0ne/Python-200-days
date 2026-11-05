"""
Day 029 — 算法入门：进阶用法
======================================================================
排序稳定性演示、自定义排序（多key/对象）、
各种优化变种（随机快排、三路快排）、bisect 模块应用
======================================================================
"""

import random
import bisect
from operator import attrgetter

random.seed(42)

# ====================================================================
# 1. 排序稳定性演示
# ====================================================================
print("=" * 60)
print("1️⃣  ⭐ 排序稳定性 — 相同键值的元素维持原始顺序")
print("=" * 60)

# 按"颜色"排序，稳定排序会保留原有的"值"顺序
items = [
    ("red", 3), ("blue", 1), ("red", 1),
    ("blue", 2), ("green", 2), ("red", 2),
]

# Python sort 是稳定的 (Timsort)
sorted_by_color = sorted(items, key=lambda x: x[0])
print(f"  原始:   {items}")
print(f"  稳排:   {sorted_by_color}")
print(f"  → red 的顺序是 (red,3)→(red,1)→(red,2)，保持原序")

# 为什么稳定重要：先按数字排序，再按颜色排序
by_number = sorted(items, key=lambda x: x[1])
by_color = sorted(by_number, key=lambda x: x[0])
print(f"  \n  先按数字排序: {by_number}")
print(f"  再按颜色排序: {by_color}")
print(f"  → 每个颜色的区间内仍然保持数字有序!")


# ====================================================================
# 2. 自定义对象排序
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  ⭐ 自定义对象排序")
print("=" * 60)

class Student:
    def __init__(self, name, grade, age):
        self.name = name
        self.grade = grade
        self.age = age

    def __repr__(self):
        return f"Student({self.name}, G{self.grade}, {self.age})"

students = [
    Student("Alice", 90, 20),
    Student("Bob", 85, 22),
    Student("Charlie", 95, 19),
    Student("David", 85, 21),
    Student("Eve", 90, 18),
]

print(f"  学生列表: {students}")

# 方法1：lambda 单 key
by_name = sorted(students, key=lambda s: s.name)
print(f"  \n  按姓名排序: {by_name}")

# 方法2：attrgetter
by_grade_desc = sorted(students, key=attrgetter('grade'), reverse=True)
print(f"  按分数降序: {by_grade_desc}")

# 方法3：多 key 排序（先分数降序，再年龄升序）
multi_key = sorted(students,
                   key=lambda s: (-s.grade, s.age))
print(f"  按分数↓年龄↑: {multi_key}")

# 方法4：实现 __lt__
class StudentWithCompare:
    def __init__(self, name, grade):
        self.name = name
        self.grade = grade

    def __lt__(self, other):
        return self.grade < other.grade

    def __repr__(self):
        return f"SWC({self.name}, {self.grade})"

swc_students = [
    StudentWithCompare("Alice", 90),
    StudentWithCompare("Bob", 85),
    StudentWithCompare("Charlie", 95),
]
print(f"  带 __lt__ 排序: {sorted(swc_students)}")

# 方法5: sort / sorted 的 key 参数 — 最常用的方式
# 高级技巧：用复杂函数做 key
def sort_key(s):
    """先按成绩降序，再按姓名升序"""
    return (-s.grade, s.name)

smart = sorted(students, key=sort_key)
print(f"  自定义 key 函数: {smart}")


# ====================================================================
# 3. 快速排序优化：随机枢纽
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  ⭐ 快排优化 — 随机枢纽 vs 固定枢纽")
print("=" * 60)

def quick_sort_fixed(arr):
    """固定选最后一个元素为枢纽（有序数据会退化）"""
    if len(arr) <= 1:
        return arr
    pivot = arr[-1]
    left = [x for x in arr[:-1] if x <= pivot]
    right = [x for x in arr[:-1] if x > pivot]
    return quick_sort_fixed(left) + [pivot] + quick_sort_fixed(right)


def quick_sort_random(arr):
    """随机选择枢纽，避免退化"""
    if len(arr) <= 1:
        return arr
    pivot_idx = random.randint(0, len(arr) - 1)
    pivot = arr[pivot_idx]
    # 把 pivot 移到最后方便处理
    rest = [x for i, x in enumerate(arr) if i != pivot_idx]
    left = [x for x in rest if x <= pivot]
    right = [x for x in rest if x > pivot]
    return quick_sort_random(left) + [pivot] + quick_sort_random(right)


# 测试：已排序数组（固定枢纽的致命弱点）
ordered = list(range(1000, 0, -1))  # 大 -> 小

import time
start = time.perf_counter()
quick_sort_random(ordered[:])
t_random = time.perf_counter() - start
print(f"  逆序 n=1000, 随机快排: {t_random:.4f}s")

# 千万注意: 固定枢纽在逆序/有序数组上会退化到 O(n²)
# 会导致 RecursionError 所以这里只测试小规模
small = list(range(50, 0, -1))
start = time.perf_counter()
quick_sort_fixed(small[:])
t_fixed = time.perf_counter() - start
print(f"  逆序 n=50,  固定快排: {t_fixed:.4f}s")


# ====================================================================
# 4. 三路快速排序（处理大量重复元素）
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  ⭐ 三路快速排序 — 处理大量重复元素")
print("=" * 60)

def quick_sort_3way(arr):
    """
    三路快排：将数组分成 < pivot / == pivot / > pivot 三部分
    应对大量重复元素的场景
    """
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    lt = [x for x in arr if x < pivot]
    eq = [x for x in arr if x == pivot]
    gt = [x for x in arr if x > pivot]
    return quick_sort_3way(lt) + eq + quick_sort_3way(gt)


# 大量重复元素的数组
many_dups = [random.choice([1, 2, 3, 4, 5]) for _ in range(1000)]

start = time.perf_counter()
result1 = quick_sort(many_dups)
t1 = time.perf_counter() - start

start = time.perf_counter()
result2 = quick_sort_3way(many_dups)
t2 = time.perf_counter() - start

print(f"  大量重复元素 (n=1000):")
print(f"  标准快排: {t1:.6f}s")
print(f"  三路快排: {t2:.6f}s")
print(f"  ✅ 结果一致: {result1 == result2}")


# ====================================================================
# 5. bisect 模块 — 二分查找与有序插入
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  ⭐ bisect 模块应用")
print("=" * 60)

scores = [60, 70, 80, 85, 90, 95]

# bisect_left / bisect_right — 查找插入位置
print(f"  成绩列表: {scores}")
print(f"  插入 75 的左侧位置: {bisect.bisect_left(scores, 75)}")
print(f"  插入 75 的右侧位置: {bisect.bisect_right(scores, 75)}")
print(f"  80 的左侧位置: {bisect.bisect_left(scores, 80)}")
print(f"  80 的右侧位置: {bisect.bisect_right(scores, 80)}")

# insort — 插入并保持有序
bisect.insort(scores, 75)
print(f"  插入 75: {scores}")

bisect.insort(scores, 88)
print(f"  插入 88: {scores}")

# 实用场景：成绩等级判定
def grade(score, breakpoints=[60, 70, 80, 90], grades='FDCBA'):
    """根据分数返回等级"""
    i = bisect.bisect(breakpoints, score)
    return grades[i]

test_scores = [33, 55, 65, 75, 85, 95, 100]
print(f"\n  成绩等级:")
for s in test_scores:
    print(f"    {s:3d} → {grade(s)}")


# ====================================================================
# 6. 有限插入排序 — 维护 Top-K
# ====================================================================
print("\n" + "=" * 60)
print("6️⃣  ⭐ 维护 Top-K（插入排序思想）")
print("=" * 60)

def maintain_top_k(arr, k):
    """返回前 k 大的元素"""
    top = []
    for x in arr:
        # 插入到有序列表中
        bisect.insort(top, x)
        # 只保留 k 个最大的
        if len(top) > k:
            top.pop(0)  # 移除最小的
    return top

scores_stream = [random.randint(1, 100) for _ in range(50)]
print(f"  数据流 (n=50): {scores_stream}")
print(f"  Top 5: {maintain_top_k(scores_stream, 5)}")
print(f"  Top 3: {maintain_top_k(scores_stream, 3)}")


# ====================================================================
# 7. 归并排序的原地合并（不使用额外空间）
# ====================================================================
print("\n" + "=" * 60)
print("7️⃣  ⭐ 旋转合并 — 原地归并（理论演示）")
print("=" * 60)

def merge_inplace(arr, start, mid, end):
    """
    原地合并两个有序子数组 [start:mid] 和 [mid:end]
    （简化版演示）
    """
    # 为了清晰，这里使用简单方法（实际可以使用旋转技巧）
    i, j = start, mid
    while i < j < end:
        if arr[i] <= arr[j]:
            i += 1
        else:
            # 将 arr[j] 插入到位置 i，后面的元素右移
            val = arr[j]
            for k in range(j, i, -1):
                arr[k] = arr[k - 1]
            arr[i] = val
            i += 1
            j += 1

arr2 = [1, 3, 5, 2, 4, 6]
print(f"  合并前: {arr2}")
merge_inplace(arr2, 0, 3, 6)
print(f"  合并后: {arr2}")


# ====================================================================
# 8. 算法可视化辅助 — 打印排序过程
# ====================================================================
print("\n" + "=" * 60)
print("8️⃣  ⭐ 排序过程可视化")
print("=" * 60)

def bubble_sort_verbose(arr):
    """可视化冒泡排序"""
    n = len(arr)
    print(f"  初始: {arr}")
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        print(f"  第{i+1}趟: {arr}" + ("" if swapped else " (无交换)"))
        if not swapped:
            break
    return arr

bubble_sort_verbose([5, 3, 8, 6, 4])

print("\n" + "=" * 60)
print("✅  算法进阶用法演示完成!")
print("=" * 60)
