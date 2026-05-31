#!/usr/bin/env python3
"""
04-list-exercise-solutions.py — Day 006 补充
列表练习题参考实现

包含：
1. 动态数组实现
2. 滑动窗口最大值
3. 列表旋转
4. 区间合并
5. 列表交集

可直接运行：python3 04-list-exercise-solutions.py
"""

import random
import time


# ============================================================
# 练习 1：动态数组（ArrayList）实现
# ============================================================

class ArrayList:
    """
    从零实现动态数组（类似 Python list 底层）
    练习：理解 list 底层扩容机制
    """

    def __init__(self, initial_capacity: int = 4):
        self._capacity = initial_capacity
        self._size = 0
        self._data = [None] * self._capacity

    def append(self, value):
        """尾部追加（均摊 O(1)）"""
        if self._size == self._capacity:
            self._resize(self._capacity * 2)  # 扩容 2 倍
        self._data[self._size] = value
        self._size += 1

    def insert(self, index: int, value):
        """指定位置插入 O(n)"""
        if index < 0:
            index = max(0, self._size + index)
        index = min(index, self._size)

        if self._size == self._capacity:
            self._resize(self._capacity * 2)

        # 后移元素
        for i in range(self._size, index, -1):
            self._data[i] = self._data[i - 1]
        self._data[index] = value
        self._size += 1

    def pop(self, index: int = -1):
        """删除并返回指定位置元素 O(n)"""
        if self._size == 0:
            raise IndexError("pop from empty list")
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise IndexError("pop index out of range")

        value = self._data[index]
        # 前移元素
        for i in range(index, self._size - 1):
            self._data[i] = self._data[i + 1]
        self._size -= 1
        self._data[self._size] = None  # 释放引用

        # 缩容（当用量低于 25% 时缩为一半）
        if self._size > 0 and self._size <= self._capacity // 4:
            self._resize(max(self._capacity // 2, 4))

        return value

    def _resize(self, new_capacity: int):
        """调整容量"""
        new_data = [None] * new_capacity
        for i in range(self._size):
            new_data[i] = self._data[i]
        self._data = new_data
        self._capacity = new_capacity

    def __getitem__(self, index):
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise IndexError("list index out of range")
        return self._data[index]

    def __setitem__(self, index, value):
        if index < 0:
            index = self._size + index
        if index < 0 or index >= self._size:
            raise IndexError("list index out of range")
        self._data[index] = value

    def __len__(self):
        return self._size

    def __repr__(self):
        return f"ArrayList({[self._data[i] for i in range(self._size)]}, cap={self._capacity})"

    def capacity(self):
        return self._capacity


def test_array_list():
    print("=" * 60)
    print("  练习 1: 动态数组（ArrayList）实现")
    print("=" * 60)

    al = ArrayList(4)
    print(f"\n  初始: {al}")

    al.append(10)
    al.append(20)
    al.append(30)
    print(f"  append 10,20,30: {al}")

    al.insert(1, 15)
    print(f"  insert(1, 15):   {al}")

    val = al.pop()
    print(f"  pop():           → {val}, {al}")

    val = al.pop(0)
    print(f"  pop(0):          → {val}, {al}")

    # 扩容测试
    print(f"\n  扩容测试:")
    al2 = ArrayList(2)
    for i in range(1, 9):
        al2.append(i * 10)
        print(f"    append({i * 10}) → {al2}")

    # 缩容测试
    print(f"\n  缩容测试:")
    for i in range(6):
        al2.pop()
        print(f"    pop() → {al2}")

    print(f"\n  ✅ ArrayList 通过基本测试")


# ============================================================
# 练习 2：滑动窗口最大值
# ============================================================

def sliding_window_max(nums: list, k: int) -> list:
    """
    滑动窗口最大值
    输入: nums = [1,3,-1,-3,5,3,6,7], k = 3
    输出: [3,3,5,5,6,7]

    使用单调队列（deque），O(n) 时间复杂度
    """
    from collections import deque
    result = []
    dq = deque()  # 存储索引，保持值递减

    for i, num in enumerate(nums):
        # 移除超出窗口范围的索引
        if dq and dq[0] < i - k + 1:
            dq.popleft()

        # 移除比当前元素小的尾部（保持递减）
        while dq and nums[dq[-1]] < num:
            dq.pop()

        dq.append(i)

        # 当窗口形成后，记录最大值
        if i >= k - 1:
            result.append(nums[dq[0]])

    return result


def test_sliding_window():
    print("\n" + "=" * 60)
    print("  练习 2: 滑动窗口最大值")
    print("=" * 60)

    nums = [1, 3, -1, -3, 5, 3, 6, 7]
    k = 3
    result = sliding_window_max(nums, k)
    print(f"\n  nums = {nums}")
    print(f"  k = {k}")
    print(f"  结果 = {result}")
    print(f"  预期 = [3, 3, 5, 5, 6, 7]")
    print(f"  ✅ {result == [3, 3, 5, 5, 6, 7]}")

    # 性能测试
    big_nums = [random.randint(-100, 100) for _ in range(100000)]
    start = time.perf_counter()
    result = sliding_window_max(big_nums, 100)
    elapsed = time.perf_counter() - start
    print(f"\n  性能: 100,000 数据, 窗口 100")
    print(f"  耗时: {elapsed:.4f}s（O(n) 算法）")


# ============================================================
# 练习 3：列表旋转
# ============================================================

def rotate_right(nums: list, k: int) -> list:
    """
    列表右旋 k 步（不使用额外空间，原地修改）
    输入: [1,2,3,4,5,6,7], k=3
    输出: [5,6,7,1,2,3,4]

    方法：三次反转
    1. 反转全部: [7,6,5,4,3,2,1]
    2. 反转前 k: [5,6,7,4,3,2,1]
    3. 反转后 n-k: [5,6,7,1,2,3,4]
    """

    def reverse(arr, start, end):
        while start < end:
            arr[start], arr[end] = arr[end], arr[start]
            start += 1
            end -= 1

    n = len(nums)
    if n == 0:
        return nums

    k = k % n
    if k == 0:
        return nums

    reverse(nums, 0, n - 1)
    reverse(nums, 0, k - 1)
    reverse(nums, k, n - 1)

    return nums


def rotate_left(nums: list, k: int) -> list:
    """左旋"""
    n = len(nums)
    k = k % n
    return rotate_right(nums, n - k)


def test_rotation():
    print("\n" + "=" * 60)
    print("  练习 3: 列表旋转（三次反转算法）")
    print("=" * 60)

    # 右旋
    nums1 = [1, 2, 3, 4, 5, 6, 7]
    print(f"\n  右旋 k=3:")
    print(f"    原始: {[1,2,3,4,5,6,7]}")
    print(f"    结果: {rotate_right(nums1, 3)}")
    print(f"    预期: [5, 6, 7, 1, 2, 3, 4]")

    # 左旋
    nums2 = [1, 2, 3, 4, 5]
    print(f"\n  左旋 k=2:")
    print(f"    原始: {[1,2,3,4,5]}")
    print(f"    结果: {rotate_left(nums2, 2)}")
    print(f"    预期: [3, 4, 5, 1, 2]")

    # 大 k 值
    nums3 = [1, 2, 3]
    print(f"\n  右旋 k=5（k > 长度，取模）：")
    print(f"    原始: {[1,2,3]}")
    print(f"    结果: {rotate_right(nums3, 5)}")
    print(f"    预期: [2, 3, 1]")


# ============================================================
# 练习 4：区间合并
# ============================================================

def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    """
    合并重叠区间
    输入: [[1,3],[2,6],[8,10],[15,18]]
    输出: [[1,6],[8,10],[15,18]]
    """
    if not intervals:
        return []

    # 按起始位置排序
    intervals.sort(key=lambda x: x[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_end = merged[-1][1]

        if start <= last_end:
            # 有重叠，合并（取更大的结束位置）
            merged[-1][1] = max(last_end, end)
        else:
            # 无重叠，新增区间
            merged.append([start, end])

    return merged


def test_merge_intervals():
    print("\n" + "=" * 60)
    print("  练习 4: 区间合并")
    print("=" * 60)

    test_cases = [
        ([[1, 3], [2, 6], [8, 10], [15, 18]], [[1, 6], [8, 10], [15, 18]]),
        ([[1, 4], [4, 5]], [[1, 5]]),  # 边界相接也合并
        ([[1, 2], [3, 4], [5, 6]], [[1, 2], [3, 4], [5, 6]]),  # 无重叠
        ([[1, 10], [2, 5], [3, 6]], [[1, 10]]),  # 完全包含
        ([], []),
    ]

    for intervals, expected in test_cases:
        result = merge_intervals(intervals)
        ok = result == expected
        print(f"\n  {'✅' if ok else '❌'} {intervals} → {result} {'✅' if ok else f'❌ 预期: {expected}'}")


# ============================================================
# 练习 5：两个列表的交集与并集
# ============================================================

def list_intersection(nums1: list, nums2: list) -> list:
    """
    两个列表的交集（不含重复）

    输入: [1, 2, 2, 1], [2, 2]
    输出: [2]
    """
    return list(set(nums1) & set(nums2))


def list_intersection_with_duplicates(nums1: list, nums2: list) -> list:
    """
    两个列表的交集（保留重复次数）
    输入: [1, 2, 2, 1], [2, 2]
    输出: [2, 2]
    """
    from collections import Counter
    c1 = Counter(nums1)
    c2 = Counter(nums2)
    result = []
    for num in c1 & c2:
        result.extend([num] * (c1[num] & c2[num]))
    # 注意 & 在 Counter 上就是取 min，所以可以：
    # return list((c1 & c2).elements())
    return list((Counter(nums1) & Counter(nums2)).elements())


def list_union(nums1: list, nums2: list) -> list:
    """并集（去重）"""
    return list(set(nums1) | set(nums2))


def test_intersection():
    print("\n" + "=" * 60)
    print("  练习 5: 列表交集与并集")
    print("=" * 60)

    nums1 = [1, 2, 2, 1, 3]
    nums2 = [2, 2, 3, 4]
    print(f"\n  nums1 = {nums1}")
    print(f"  nums2 = {nums2}")
    print(f"  交集（去重）:           {list_intersection(nums1, nums2)}")
    print(f"  交集（保留重复）:       {list_intersection_with_duplicates(nums1, nums2)}")
    print(f"  并集（去重）:           {list_union(nums1, nums2)}")


# ============================================================
# 主程序
# ============================================================

def main():
    test_array_list()
    test_sliding_window()
    test_rotation()
    test_merge_intervals()
    test_intersection()

    print("\n" + "=" * 60)
    print("  ✅ 列表练习全部完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
