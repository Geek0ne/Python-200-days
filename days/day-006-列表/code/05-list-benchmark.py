#!/usr/bin/env python3
"""
05-list-benchmark.py — Day 006 补充
列表性能基准测试

对比：Python list 不同操作在不同数据量下的性能
测试项目：追加/插入/删除/查找/排序/推导式/内存

可直接运行：python3 05-list-benchmark.py
"""

import time
import random
import sys
from collections import deque


# ============================================================
# 测试 1：尾部追加性能
# ============================================================

def test_append_performance():
    """list.append() 尾部追加（均摊 O(1)）"""
    print("=" * 60)
    print("  📊 Test 1: list.append() 尾部追加性能")
    print("=" * 60)

    sizes = [100_000, 1_000_000, 10_000_000]
    rows = []

    for n in sizes:
        start = time.perf_counter()
        lst = []
        for i in range(n):
            lst.append(i)
        elapsed = time.perf_counter() - start
        rows.append((n, elapsed, elapsed / n * 1e6))

    print(f"\n  {'数据量':<12} {'总耗时':<12} {'每次(µs)':<12}")
    print(f"  {'-' * 36}")
    for n, t, avg in rows:
        print(f"  {n:<12,} {t:<12.4f} {avg:<12.2f}")
    print(f"\n  💡 append 均摊 O(1)，数据量线性增长，耗时也线性增长。")


# ============================================================
# 测试 2：头部插入 vs 尾部插入
# ============================================================

def test_insert_performance():
    """头部 vs 中间 vs 尾部插入"""
    print("\n" + "=" * 60)
    print("  📊 Test 2: 插入性能对比（头部/中间/尾部）")
    print("=" * 60)

    n = 50_000  # 避免 O(n) 操作太久
    print(f"\n  向 {n:,} 长度的列表执行 1,000 次插入:")

    # 尾部插入
    lst = list(range(n))
    start = time.perf_counter()
    for i in range(1000):
        lst.append(i)
    tail_time = time.perf_counter() - start

    # 中间插入
    lst = list(range(n))
    start = time.perf_counter()
    for i in range(1000):
        lst.insert(n // 2, i)
    mid_time = time.perf_counter() - start

    # 头部插入
    lst = list(range(n))
    start = time.perf_counter()
    for i in range(1000):
        lst.insert(0, i)
    head_time = time.perf_counter() - start

    print(f"\n  {'位置':<10} {'总耗时':<12} {'每次(µs)':<12}")
    print(f"  {'-' * 34}")
    print(f"  {'尾部':<10} {tail_time:<12.4f} {tail_time / 1000 * 1e6:<12.2f}")
    print(f"  {'中间':<10} {mid_time:<12.4f} {mid_time / 1000 * 1e6:<12.2f}")
    print(f"  {'头部':<10} {head_time:<12.4f} {head_time / 1000 * 1e6:<12.2f}")
    print(f"\n  💡 尾部 O(1) vs 头部 O(n) — 差 {head_time / tail_time:.0f}x！")


# ============================================================
# 测试 3：尾部删除 vs 头部删除
# ============================================================

def test_deletion_performance():
    """pop() vs pop(0) 删除性能"""
    print("\n" + "=" * 60)
    print("  📊 Test 3: 删除性能对比（尾部/头部）")
    print("=" * 60)

    n = 100_000
    print(f"\n  从 {n:,} 长度的列表删除 5,000 个元素:")
    print(f"  {'操作':<15} {'总耗时':<12}")
    print(f"  {'-' * 27}")

    # pop() 尾部删除 O(1)
    lst = list(range(n))
    start = time.perf_counter()
    for _ in range(5000):
        lst.pop()
    pop_time = time.perf_counter() - start
    print(f"  {'pop()':<15} {pop_time:<12.4f}")

    # pop(0) 头部删除 O(n)
    lst = list(range(n))
    start = time.perf_counter()
    for _ in range(5000):
        lst.pop(0)
    pop0_time = time.perf_counter() - start
    print(f"  {'pop(0)':<15} {pop0_time:<12.4f}")

    # deque.popleft() O(1)
    dq = deque(range(n))
    start = time.perf_counter()
    for _ in range(5000):
        dq.popleft()
    popleft_time = time.perf_counter() - start
    print(f"  {'deque.popleft()':<15} {popleft_time:<12.6f}")

    print(f"\n  💡 pop() vs pop(0): 差 {pop0_time / pop_time:.0f}x")
    print(f"  💡 deque.popleft(): 比 pop(0) 快 {pop0_time / popleft_time:.0f}x")


# ============================================================
# 测试 4：成员查找性能
# ============================================================

def test_contains_performance():
    """list vs set 成员查找"""
    print("\n" + "=" * 60)
    print("  📊 Test 4: in 操作性能（list vs set）")
    print("=" * 60)

    sizes = [1_000, 10_000, 100_000]
    lookups = 10_000

    print(f"\n  查找 {lookups:,} 次:")
    print(f"  {'数据量':<10} {'list (秒)':<12} {'set (秒)':<12} {'加速比'}")
    print(f"  {'-' * 46}")

    for n in sizes:
        lst = list(range(n))
        st = set(range(n))
        search = random.choices(range(-n // 2, n + n // 2), k=lookups)

        start = time.perf_counter()
        for x in search:
            _ = x in lst
        list_time = time.perf_counter() - start

        start = time.perf_counter()
        for x in search:
            _ = x in st
        set_time = time.perf_counter() - start

        ratio = f"{list_time / set_time:.0f}x"
        print(f"  {n:<10,} {list_time:<12.4f} {set_time:<12.6f} {ratio}")

    print(f"\n  💡 数据量越大，set 优势越明显！list 是 O(n)，set 是 O(1)")


# ============================================================
# 测试 5：列表推导式 vs for 循环
# ============================================================

def test_comprehension_performance():
    """推导式 vs for 循环"""
    print("\n" + "=" * 60)
    print("  📊 Test 5: 列表推导式 vs for 循环")
    print("=" * 60)

    n = 5_000_000
    print(f"\n  生成 {n:,} 个数的平方:")

    # for 循环
    start = time.perf_counter()
    result1 = []
    for i in range(n):
        result1.append(i ** 2)
    for_time = time.perf_counter() - start

    # 列表推导式
    start = time.perf_counter()
    result2 = [i ** 2 for i in range(n)]
    comp_time = time.perf_counter() - start

    # map
    start = time.perf_counter()
    result3 = list(map(lambda x: x ** 2, range(n)))
    map_time = time.perf_counter() - start

    print(f"\n  {'方法':<15} {'耗时':<12}")
    print(f"  {'-' * 27}")
    print(f"  {'for 循环':<15} {for_time:<12.4f}")
    print(f"  {'列表推导式':<15} {comp_time:<12.4f}")
    print(f"  {'map + list':<15} {map_time:<12.4f}")

    fastest = min(for_time, comp_time, map_time)
    print(f"\n  💡 列表推导式比 for 循环快 {for_time / comp_time:.1f}x")
    print(f"  💡 map 比 for 循环快 {for_time / map_time:.1f}x")


# ============================================================
# 测试 6：排序性能
# ============================================================

def test_sort_performance():
    """sorted() 和 .sort() 排序性能"""
    print("\n" + "=" * 60)
    print("  📊 Test 6: 排序性能")
    print("=" * 60)

    sizes = [10_000, 100_000, 1_000_000]

    print(f"\n  {'数据量':<10} {'sorted()':<12} {'.sort()':<12}")
    print(f"  {'-' * 34}")

    for n in sizes:
        data = list(range(n))
        random.shuffle(data)

        start = time.perf_counter()
        r1 = sorted(data)
        sorted_time = time.perf_counter() - start

        d2 = data.copy()
        start = time.perf_counter()
        d2.sort()
        sort_time = time.perf_counter() - start

        print(f"  {n:<10,} {sorted_time:<12.4f} {sort_time:<12.4f}")

    print(f"\n  💡 sorted() 和 .sort() 使用相同的 Timsort 算法，性能接近。")


# ============================================================
# 测试 7：复制方式对比
# ============================================================

def test_copy_performance():
    """不同复制方式的性能"""
    print("\n" + "=" * 60)
    print("  📊 Test 7: 列表复制方式对比")
    print("=" * 60)

    n = 1_000_000
    lst = list(range(n))

    print(f"\n  复制 {n:,} 个元素:")
    print(f"  {'方法':<20} {'耗时':<12}")
    print(f"  {'-' * 32}")

    # 切片复制
    start = time.perf_counter()
    c1 = lst[:]
    slice_time = time.perf_counter() - start
    print(f"  {'切片 lst[:]':<20} {slice_time:<12.4f}")

    # list() 构造函数
    start = time.perf_counter()
    c2 = list(lst)
    list_time = time.perf_counter() - start
    print(f"  {'list() 构造':<20} {list_time:<12.4f}")

    # copy()
    start = time.perf_counter()
    c3 = lst.copy()
    copy_time = time.perf_counter() - start
    print(f"  {'.copy()':<20} {copy_time:<12.4f}")

    # * 复制
    start = time.perf_counter()
    c4 = lst * 1
    mul_time = time.perf_counter() - start
    print(f"  {'lst * 1':<20} {mul_time:<12.4f}")


# ============================================================
# 测试 8：内存占用
# ============================================================

def test_memory_usage():
    """列表不同大小的内存占用"""
    print("\n" + "=" * 60)
    print("  📊 Test 8: 列表内存占用")
    print("=" * 60)

    import sys

    sizes = [0, 1, 10, 100, 1000, 10000]

    print(f"\n  {'元素数':<10} {'sys.getsizeof':<16} {'估算总内存':<16}")
    print(f"  {'-' * 42}")

    for n in sizes:
        lst = list(range(n))
        base = sys.getsizeof(lst)
        # 每个 int 对象约 28 字节
        estimated = base + n * 28
        print(f"  {n:<10,} {base:<16,} {estimated:<16,}")

    print(f"\n  💡 列表对象头部约 56 字节，每个元素指针 8 字节")
    print(f"  💡 实际内存还需要加上元素对象本身的大小")


# ============================================================
# 主程序
# ============================================================

def main():
    print("🐍 Python " + sys.version.split()[0])
    print("=" * 60)
    print("  📊 List 全方位性能基准测试")
    print("=" * 60)

    test_append_performance()
    test_insert_performance()
    test_deletion_performance()
    test_contains_performance()
    test_comprehension_performance()
    test_sort_performance()
    test_copy_performance()
    test_memory_usage()

    print("\n" + "=" * 60)
    print("  ✅ 基准测试完成！")
    print("\n  📌 核心结论:")
    print("  1. append 尾部追加 — O(1) 均摊，最快")
    print("  2. insert(0) 头部插入 — O(n)，慢！用 deque 替代")
    print("  3. pop(0) 头部删除 — O(n)，慢！用 deque.popleft()")
    print("  4. 成员查找 in — O(n)，大数据量改用 set")
    print("  5. 列表推导式 — 比 for 循环快 10-20%")
    print("  6. 内置排序 Timsort — O(n log n)，比手写排序快 1000x")
    print("=" * 60)


if __name__ == "__main__":
    main()
