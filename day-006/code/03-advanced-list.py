#!/usr/bin/env python3
"""
03-advanced-list.py — Day 006 补充
列表高级操作：切片深究、深浅拷贝、栈与队列、排序算法、多维列表

可直接运行：python3 03-advanced-list.py
"""

import copy
import time
from collections import deque


# ============================================================
# 1. 切片操作深度解析
# ============================================================

def demo_slicing():
    print("=" * 60)
    print("  1️⃣ 列表切片深入：不只是 [start:stop:step]")
    print("=" * 60)

    lst = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    print(f"\n  原始列表: {lst}")

    # 基础切片
    print(f"\n  基础切片:")
    print(f"    lst[2:5]     = {lst[2:5]}   # 索引 2~4")
    print(f"    lst[:4]      = {lst[:4]}    # 前 4 个")
    print(f"    lst[6:]      = {lst[6:]}    # 从索引 6 到末尾")
    print(f"    lst[-3:]     = {lst[-3:]}   # 最后 3 个")
    print(f"    lst[:-2]     = {lst[:-2]}   # 去掉最后 2 个")

    # 步长切片
    print(f"\n  步长切片:")
    print(f"    lst[::2]     = {lst[::2]}   # 每 2 个取 1 个")
    print(f"    lst[1::2]    = {lst[1::2]}  # 从索引 1 开始每 2 个取 1 个")
    print(f"    lst[::-1]    = {lst[::-1]}  # 反转")
    print(f"    lst[::-2]    = {lst[::-2]}  # 反向每 2 个取 1 个")

    # 切片赋值（重点！不同于列表赋值）
    print(f"\n  切片赋值（重点！）:")
    a = [1, 2, 3, 4, 5]
    print(f"    原始: {a}")
    a[1:3] = [99, 100]
    print(f"    a[1:3] = [99, 100]  → {a}")

    b = [1, 2, 3, 4, 5]
    b[1:3] = [10]  # 替换范围小于切片范围
    print(f"    b[1:3] = [10]       → {b}")

    c = [1, 2, 3, 4, 5]
    c[1:3] = [10, 20, 30, 40]  # 替换范围大于切片范围
    print(f"    c[1:3] = [10,20,30,40] → {c}")

    d = [1, 2, 3, 4, 5]
    d[1:4:2] = [99, 100]  # 步长切片赋值，数量必须匹配
    print(f"    d[1:4:2] = [99, 100]   → {d}")

    # 切片删除
    e = [1, 2, 3, 4, 5]
    e[1:3] = []
    print(f"    e[1:3] = []        → {e} （等价于删除切片范围内的元素）")

    # 切片是浅拷贝
    print(f"\n  切片创建的是浅拷贝:")
    nested = [[1, 2], [3, 4], [5, 6]]
    sliced = nested[:2]
    print(f"    nested = {nested}")
    print(f"    sliced = nested[:2] = {sliced}")
    sliced[0][0] = 999
    print(f"    修改 sliced[0][0]=999")
    print(f"    nested = {nested}  ← 受影响！（浅拷贝的证据）")


# ============================================================
# 2. 深浅拷贝详解
# ============================================================

def demo_copy():
    print("\n" + "=" * 60)
    print("  2️⃣ 深浅拷贝详解")
    print("=" * 60)

    original = [
        {"name": "Alice", "scores": [85, 92]},
        {"name": "Bob", "scores": [78, 88]},
    ]

    # 引用赋值
    ref = original
    # 浅拷贝
    shallow = copy.copy(original)
    # 深拷贝
    deep = copy.deepcopy(original)

    # 修改内部可变对象
    shallow[0]["scores"].append(100)

    print(f"\n    修改 shallow[0]['scores'].append(100) 后:")
    print(f"    original: {original}")
    print(f"    shallow:  {shallow}")
    print(f"    deep:     {deep}")
    print(f"\n    → 浅拷贝共享内部可变对象，深拷贝完全独立")

    # 修改顶层元素
    shallow[1] = {"name": "Charlie", "scores": [95]}

    print(f"\n    修改 shallow[1] = 新对象 后:")
    print(f"    original: {original}")
    print(f"    shallow:  {shallow}")
    print(f"    → 浅拷贝的顶层替换不影响原始列表")

    # 内存地址对比
    print(f"\n  内存地址对比:")
    print(f"    id(original[0]['scores']) = {id(original[0]['scores'])}")
    print(f"    id(shallow[0]['scores'])  = {id(shallow[0]['scores'])}  ← 同一对象")
    print(f"    id(deep[0]['scores'])     = {id(deep[0]['scores'])}  ← 不同对象")

    # 实用建议
    print(f"\n  💡 选择指南:")
    print(f"     - 纯值列表（int/str等不可变）: 切片/浅拷贝都行")
    print(f"     - 嵌套结构: 用 deepcopy")
    print(f"     - 只想防止顶层被改: 浅拷贝足够")


# ============================================================
# 3. 列表作为栈与队列
# ============================================================

def demo_stack_queue():
    print("\n" + "=" * 60)
    print("  3️⃣ 列表作为栈与队列")
    print("=" * 60)

    # --- 栈（Stack）：LIFO ---
    print(f"\n  📚 栈（LIFO — 后进先出）:")
    stack = []
    print(f"    初始: {stack}")

    # 入栈
    for item in ["书1", "书2", "书3"]:
        stack.append(item)
        print(f"    push({item}) → {stack}")

    # 出栈
    while stack:
        item = stack.pop()
        print(f"    pop() → {item}, 剩余: {stack}")

    # --- 队列（Queue）：FIFO ---
    print(f"\n  🚶 队列（FIFO — 先进先出）:")
    # 注意：用 list 做队列性能差（pop(0) 是 O(n)）
    # 正确做法：用 collections.deque

    # 错误示范：list 做队列
    print(f"  ⚠️  不推荐用 list 做队列:")
    q_list = list(range(10000))
    start = time.perf_counter()
    for _ in range(1000):
        q_list.pop(0)
    list_time = time.perf_counter() - start
    print(f"    list.pop(0) × 1000:  {list_time:.4f}s")

    # 正确做法：deque
    print(f"\n  ✅ 推荐用 deque:")
    q_deque = deque(range(10000))
    start = time.perf_counter()
    for _ in range(1000):
        q_deque.popleft()
    deque_time = time.perf_counter() - start
    print(f"    deque.popleft() × 1000: {deque_time:.6f}s")
    print(f"    deque 快 {list_time / deque_time:.0f}x！")

    # deque 的完整用法
    print(f"\n  deque 完整用法:")
    dq = deque(maxlen=5)  # 固定最大长度
    for i in range(8):
        dq.append(i)
        print(f"    append({i}) → {list(dq)}")
    print(f"    固定长度自动淘汰最早元素")


# ============================================================
# 4. 排序算法实现
# ============================================================

def demo_sorting():
    print("\n" + "=" * 60)
    print("  4️⃣ 排序算法实现与对比")
    print("=" * 60)

    def bubble_sort(arr):
        """冒泡排序 O(n²)"""
        arr = arr.copy()
        n = len(arr)
        for i in range(n):
            swapped = False
            for j in range(n - 1 - i):
                if arr[j] > arr[j + 1]:
                    arr[j], arr[j + 1] = arr[j + 1], arr[j]
                    swapped = True
            if not swapped:
                break
        return arr

    def selection_sort(arr):
        """选择排序 O(n²)"""
        arr = arr.copy()
        n = len(arr)
        for i in range(n):
            min_idx = i
            for j in range(i + 1, n):
                if arr[j] < arr[min_idx]:
                    min_idx = j
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
        return arr

    def insertion_sort(arr):
        """插入排序 O(n²)"""
        arr = arr.copy()
        for i in range(1, len(arr)):
            key = arr[i]
            j = i - 1
            while j >= 0 and arr[j] > key:
                arr[j + 1] = arr[j]
                j -= 1
            arr[j + 1] = key
        return arr

    def merge_sort(arr):
        """归并排序 O(n log n)"""
        if len(arr) <= 1:
            return arr
        mid = len(arr) // 2
        left = merge_sort(arr[:mid])
        right = merge_sort(arr[mid:])
        return merge(left, right)

    def merge(left, right):
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

    # 性能对比
    sizes = [100, 1000, 5000]

    for n in sizes:
        data = list(range(n))
        import random
        random.shuffle(data)

        print(f"\n   数据量: {n:,}")
        print(f"   {'算法':<15} {'时间':<12} {'正确性'}")

        # Python 内置排序（Timsort）
        start = time.perf_counter()
        result = sorted(data)
        builtin_time = time.perf_counter() - start
        print(f"   {'Timsort (内置)':<15} {builtin_time:<12.4f} {'✅'}")

        if n <= 1000:  # O(n²) 算法只在小数据量测试
            for name, func in [("冒泡排序", bubble_sort), ("选择排序", selection_sort),
                               ("插入排序", insertion_sort)]:
                start = time.perf_counter()
                result = func(data)
                elapsed = time.perf_counter() - start
                ok = result == sorted(data)
                print(f"   {name:<15} {elapsed:<12.4f} {'✅' if ok else '❌'}")

        # 归并排序（大数据量也能跑）
        if n <= 5000:
            start = time.perf_counter()
            result = merge_sort(data)
            elapsed = time.perf_counter() - start
            ok = result == sorted(data)
            print(f"   {'归并排序':<15} {elapsed:<12.4f} {'✅' if ok else '❌'}")

    print(f"\n  💡 Python 内置 sorted() 使用 Timsort 算法，")
    print(f"     结合了归并和插入排序的优点，实际项目永远用内置排序！")


# ============================================================
# 5. 多维列表与矩阵
# ============================================================

def demo_multidimensional():
    print("\n" + "=" * 60)
    print("  5️⃣ 多维列表与矩阵操作")
    print("=" * 60)

    # 创建矩阵
    rows, cols = 3, 4

    # 正确方式
    matrix = [[0] * cols for _ in range(rows)]
    print(f"  正确创建 3×4 矩阵:")
    for row in matrix:
        print(f"    {row}")

    # 错误方式（共享引用！）
    wrong = [[0] * cols] * rows
    wrong[0][0] = 999
    print(f"\n  错误创建（共享引用）:")
    for row in wrong:
        print(f"    {row}")

    # 矩阵乘法（2×3 × 3×2）
    A = [[1, 2, 3], [4, 5, 6]]
    B = [[7, 8], [9, 10], [11, 12]]

    def matrix_multiply(X, Y):
        """矩阵乘法"""
        m = len(X)
        n = len(Y[0])
        k = len(Y)
        result = [[0] * n for _ in range(m)]

        for i in range(m):
            for j in range(n):
                for p in range(k):
                    result[i][j] += X[i][p] * Y[p][j]
        return result

    C = matrix_multiply(A, B)
    print(f"\n  矩阵乘法:")
    print(f"    A = {A}")
    print(f"    B = {B}")
    print(f"    A×B = {C}")

    # 矩阵转置
    def transpose(matrix):
        return [[matrix[j][i] for j in range(len(matrix))]
                for i in range(len(matrix[0]))]

    print(f"\n  矩阵转置:")
    print(f"    A = {A}")
    print(f"    Aᵀ = {transpose(A)}")


# ============================================================
# 主程序
# ============================================================

def main():
    demo_slicing()
    demo_copy()
    demo_stack_queue()
    demo_sorting()
    demo_multidimensional()

    print("\n" + "=" * 60)
    print("  ✅ 列表高级操作演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
