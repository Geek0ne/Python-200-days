"""
Day 029 — 算法入门：基础用法
======================================================================
排序算法（冒泡/选择/插入/快排/归并）与搜索算法的基础实现
======================================================================
"""

import random
import time

# ====================================================================
# 辅助函数
# ====================================================================
def print_separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def measure_time(func, arr):
    """测量排序时间"""
    arr_copy = arr.copy()
    start = time.perf_counter()
    result = func(arr_copy)
    elapsed = time.perf_counter() - start
    return result, elapsed


# ====================================================================
# 1. 冒泡排序 (Bubble Sort)
# ====================================================================
print_separator("1. 冒泡排序 — 相邻交换，大数上浮")

def bubble_sort(arr):
    """冒泡排序：优化版（带 early stop）"""
    n = len(arr)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


arr1 = [64, 34, 25, 12, 22, 11, 90]
print(f"  原始: {arr1}")
print(f"  排序: {bubble_sort(arr1.copy())}")

# 近乎有序数组 — 展示 early stop 优势
arr_nearly = [1, 2, 3, 4, 6, 5, 7, 8, 9]
result, t = measure_time(bubble_sort, arr_nearly)
print(f"  近乎有序: {result} (耗时: {t:.6f}s)")


# ====================================================================
# 2. 选择排序 (Selection Sort)
# ====================================================================
print_separator("2. 选择排序 — 每次选最小，交换到前端")

def selection_sort(arr):
    """选择排序：每趟找最小值"""
    n = len(arr)
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr


arr2 = [29, 10, 14, 37, 13, 33]
print(f"  原始: {arr2}")
print(f"  排序: {selection_sort(arr2.copy())}")


# ====================================================================
# 3. 插入排序 (Insertion Sort)
# ====================================================================
print_separator("3. 插入排序 — 像打牌一样插入")

def insertion_sort(arr):
    """插入排序：局部有序，逐步扩张"""
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr


arr3 = [12, 11, 13, 5, 6]
print(f"  原始: {arr3}")
print(f"  排序: {insertion_sort(arr3.copy())}")

# 最佳情况（已排序）
arr_best = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
result, t = measure_time(insertion_sort, arr_best)
print(f"  已有序: {result} (耗时: {t:.6f}s)")

# 最坏情况（逆序）
arr_worst = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
result, t = measure_time(insertion_sort, arr_worst)
print(f"  逆序:   {result} (耗时: {t:.6f}s)")


# ====================================================================
# 4. 快速排序 (Quick Sort)
# ====================================================================
print_separator("4. 快速排序 — 分治思想，枢纽划分")

def quick_sort(arr):
    """快速排序：列表推导式版本（简洁但额外空间）"""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)


def quick_sort_inplace(arr, low=0, high=None):
    """快速排序：原地版本（面试高频）"""
    if high is None:
        high = len(arr) - 1
    if low < high:
        pi = _partition(arr, low, high)
        quick_sort_inplace(arr, low, pi - 1)
        quick_sort_inplace(arr, pi + 1, high)
    return arr


def _partition(arr, low, high):
    """Lomuto 分割方案"""
    pivot = arr[high]
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


arr4 = [3, 7, 8, 5, 2, 1, 9, 5, 4]
print(f"  原始:            {arr4}")
print(f"  快排(简洁版):    {quick_sort(arr4.copy())}")
print(f"  快排(原地版):    {quick_sort_inplace(arr4.copy())}")


# ====================================================================
# 5. 归并排序 (Merge Sort)
# ====================================================================
print_separator("5. 归并排序 — 先分后合，稳定有序")

def merge_sort(arr):
    """归并排序：递归版本"""
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left, right):
    """合并两个有序数组"""
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    # 添加剩余元素
    result.extend(left[i:])
    result.extend(right[j:])
    return result


arr5 = [38, 27, 43, 3, 9, 82, 10]
print(f"  原始: {arr5}")
print(f"  排序: {merge_sort(arr5.copy())}")


# ====================================================================
# 6. 算法性能对比
# ====================================================================
print_separator("6. 算法性能对比 (n=500 随机数据)")

random.seed(42)
test_arr = [random.randint(1, 10000) for _ in range(500)]

algorithms = [
    ("冒泡排序", bubble_sort),
    ("选择排序", selection_sort),
    ("插入排序", insertion_sort),
    ("快速排序", quick_sort),
    ("归并排序", merge_sort),
    # Python 内置排序 — Timsort
    ("Timsort", lambda arr: sorted(arr)),
]

for name, func in algorithms:
    try:
        _, elapsed = measure_time(func, test_arr)
        print(f"  {name:<12} → {elapsed:.6f}s")
    except RecursionError:
        print(f"  {name:<12} → 递归错误")


# ====================================================================
# 7. 搜索算法
# ====================================================================
print_separator("7. 搜索算法")

def linear_search(arr, target):
    """线性搜索"""
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1


def binary_search(arr, target):
    """二分搜索（迭代版）"""
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1


def binary_search_recursive(arr, target, low, high):
    """二分搜索（递归版）"""
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search_recursive(arr, target, mid + 1, high)
    else:
        return binary_search_recursive(arr, target, low, mid - 1)


# 测试线性搜索
arr_unsorted = [4, 2, 7, 1, 9, 3, 5]
print(f"  无序数组: {arr_unsorted}")
print(f"  线性搜索 7: 索引 {linear_search(arr_unsorted, 7)}")
print(f"  线性搜索 8: 索引 {linear_search(arr_unsorted, 8)}")

# 测试二分搜索
arr_sorted = sorted(arr_unsorted)
print(f"  有序数组: {arr_sorted}")
print(f"  二分搜索 7: 索引 {binary_search(arr_sorted, 7)}")
print(f"  二分搜索 8: 索引 {binary_search(arr_sorted, 8)}")
print(f"  递归二分 7: 索引 {binary_search_recursive(arr_sorted, 7, 0, len(arr_sorted) - 1)}")

# 性能对比
print(f"\n  搜索性能 (n=10000):")
big_data = sorted([random.randint(1, 1000000) for _ in range(10000)])
target = big_data[random.randint(0, 9999)]  # 保证存在

start = time.perf_counter()
idx1 = linear_search(big_data, target)
t1 = time.perf_counter() - start

start = time.perf_counter()
idx2 = binary_search(big_data, target)
t2 = time.perf_counter() - start

print(f"  线性搜索: {t1:.8f}s (索引 {idx1})")
print(f"  二分搜索: {t2:.8f}s (索引 {idx2})")
print(f"  二分速度是线性的 {t1/t2:.0f} 倍!")
