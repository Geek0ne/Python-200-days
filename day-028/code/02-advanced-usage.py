"""
Day 028 — 数据结构综合：进阶用法
======================================================================
利用栈、队列、heapq、bisect 解决经典算法问题
======================================================================
"""

import heapq
import bisect
from collections import deque
import random


print("=" * 60)
print("1️⃣  用两个栈实现队列")
print("=" * 60)

class QueueWithTwoStacks:
    """用两个栈实现 FIFO 队列"""
    def __init__(self):
        self._in_stack = []   # 入队栈
        self._out_stack = []  # 出队栈

    def enqueue(self, value):
        self._in_stack.append(value)

    def dequeue(self):
        if not self._out_stack:
            while self._in_stack:
                self._out_stack.append(self._in_stack.pop())
        if not self._out_stack:
            raise IndexError("dequeue from empty queue")
        return self._out_stack.pop()

    def peek(self):
        if not self._out_stack:
            while self._in_stack:
                self._out_stack.append(self._in_stack.pop())
        return self._out_stack[-1]

    def is_empty(self):
        return not self._in_stack and not self._out_stack

    def __len__(self):
        return len(self._in_stack) + len(self._out_stack)

# 测试
q = QueueWithTwoStacks()
for i in range(5):
    q.enqueue(i)
    print(f"入队: {i}")
print(f"出队: {q.dequeue()}  (期望 0)")
print(f"出队: {q.dequeue()}  (期望 1)")
q.enqueue(99)
print(f"入队: 99")
for _ in range(4):
    print(f"出队: {q.dequeue()}")


print("\n" + "=" * 60)
print("2️⃣  最小栈（MinStack）— O(1) 获取最小值")
print("=" * 60)

class MinStack:
    """
    支持 push, pop, top, getMin 全部 O(1) 操作
    思路：辅助栈同步记录当前最小值
    """
    def __init__(self):
        self._stack = []
        self._min_stack = []

    def push(self, value):
        self._stack.append(value)
        if not self._min_stack or value <= self._min_stack[-1]:
            self._min_stack.append(value)
        else:
            self._min_stack.append(self._min_stack[-1])

    def pop(self):
        if not self._stack:
            raise IndexError("pop from empty stack")
        self._min_stack.pop()
        return self._stack.pop()

    def top(self):
        return self._stack[-1]

    def get_min(self):
        return self._min_stack[-1]

# 测试
ms = MinStack()
ms.push(3)
ms.push(5)
print(f"push 3, 5 → min: {ms.get_min()} (期望 3)")
ms.push(2)
ms.push(1)
print(f"push 2, 1 → min: {ms.get_min()} (期望 1)")
ms.pop()
print(f"pop → top: {ms.top()}, min: {ms.get_min()} (期望 2)")
ms.pop()
print(f"pop → top: {ms.top()}, min: {ms.get_min()} (期望 3)")


print("\n" + "=" * 60)
print("3️⃣  Top K 问题 — 求最大/最小的 K 个元素")
print("=" * 60)

def top_k_smallest(arr, k):
    """求最小的 K 个元素（使用最大堆）"""
    if k <= 0:
        return []
    heap = [-x for x in arr[:k]]
    heapq.heapify(heap)
    for x in arr[k:]:
        if -x > heap[0]:  # x 比堆中的最大值小
            heapq.heapreplace(heap, -x)
    return sorted([-x for x in heap])

def top_k_largest(arr, k):
    """求最大的 K 个元素（使用最小堆）"""
    if k <= 0:
        return []
    heap = arr[:k]
    heapq.heapify(heap)
    for x in arr[k:]:
        if x > heap[0]:
            heapq.heapreplace(heap, x)
    return sorted(heap, reverse=True)

data = [random.randint(1, 1000) for _ in range(100)]
k = 5
print(f"在 {len(data)} 个数中找 Top {k}:")
print(f"最小 {k} 个: {top_k_smallest(data, k)}")
print(f"最大 {k} 个: {top_k_largest(data, k)}")

# 验证
sorted_data = sorted(data)
assert top_k_smallest(data, k) == sorted_data[:k]
assert top_k_largest(data, k) == sorted_data[-k:][::-1]
print("✅ 结果验证通过")


print("\n" + "=" * 60)
print("4️⃣  数据流中位数查找（双堆法）")
print("=" * 60)

class MedianFinder:
    """
    动态维护数据流的中位数
    思路：
        - 最大堆 lo 存储较小的半部分
        - 最小堆 hi 存储较大的半部分
        - 始终保持 len(lo) >= len(hi)
    """
    def __init__(self):
        self._lo = []   # 最大堆（用负数模拟）
        self._hi = []   # 最小堆

    def add_num(self, num):
        # 先放入 lo，再调整
        heapq.heappush(self._lo, -num)
        # 保证 lo 的最大值 <= hi 的最小值
        if self._lo and self._hi and (-self._lo[0]) > self._hi[0]:
            val = -heapq.heappop(self._lo)
            heapq.heappush(self._hi, val)
        # 平衡两堆大小
        if len(self._lo) > len(self._hi) + 1:
            val = -heapq.heappop(self._lo)
            heapq.heappush(self._hi, val)
        elif len(self._hi) > len(self._lo):
            val = heapq.heappop(self._hi)
            heapq.heappush(self._lo, -val)

    def find_median(self):
        if not self._lo:
            raise ValueError("no data")
        if len(self._lo) > len(self._hi):
            return -self._lo[0]  # 奇数个，中位数在 lo
        return (-self._lo[0] + self._hi[0]) / 2.0

mf = MedianFinder()
stream = [5, 3, 8, 1, 7, 9, 2, 6, 4]
for i, x in enumerate(stream):
    mf.add_num(x)
    sorted_so_far = sorted(stream[:i+1])
    n = len(sorted_so_far)
    expected = (sorted_so_far[n//2] if n % 2 == 1
                else (sorted_so_far[n//2-1] + sorted_so_far[n//2]) / 2)
    print(f"添加 {x:2d} → 中位数: {mf.find_median():5.1f}  (期望: {expected:5.1f})")


print("\n" + "=" * 60)
print("5️⃣  日程冲突检测（bisect 应用）")
print("=" * 60)

class Calendar:
    """日程冲突检测器"""
    def __init__(self):
        self._events = []  # [(start, end), ...]

    def book(self, start: int, end: int) -> bool:
        """
        尝试预订 [start, end)
        无冲突返回 True，否则 False
        """
        # 找到第一个 start >= 当前事件的结束时间
        i = bisect.bisect_left(self._events, (start, end))
        # 检查与前一个事件是否冲突
        if i > 0 and self._events[i-1][1] > start:
            return False
        # 检查与后一个事件是否冲突
        if i < len(self._events) and self._events[i][0] < end:
            return False
        self._events.insert(i, (start, end))
        return True

    def list_events(self):
        return list(self._events)

cal = Calendar()
tests = [
    (10, 12, True, "10:00-12:00"),
    (9, 10, True,  "09:00-10:00"),
    (11, 13, False, "11:00-13:00 (冲突)"),
    (14, 15, True,  "14:00-15:00"),
    (12, 13, True,  "12:00-13:00"),
    (9, 11, False,  "09:00-11:00 (冲突)"),
]
for start, end, expected, desc in tests:
    result = cal.book(start, end)
    status = "✅" if result == expected else "❌"
    print(f"  {status} 预订 {desc}: {'成功' if result else '拒绝'}")
print(f"\n最终日程: {cal.list_events()}")


print("\n" + "=" * 60)
print("6️⃣  LRU 缓存（最近最少使用）")
print("=" * 60)

class LRUCache:
    """最近最少使用缓存，O(1) 操作"""
    class _Node:
        __slots__ = ('key', 'value', 'prev', 'next')
        def __init__(self, key=0, value=0):
            self.key = key
            self.value = value
            self.prev = None
            self.next = None

    def __init__(self, capacity: int):
        self._capacity = capacity
        self._cache = {}
        self._head = self._Node()  # dummy head
        self._tail = self._Node()  # dummy tail
        self._head.next = self._tail
        self._tail.prev = self._head

    def _remove(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_head(self, node):
        node.next = self._head.next
        node.prev = self._head
        self._head.next.prev = node
        self._head.next = node

    def get(self, key: int) -> int:
        if key not in self._cache:
            return -1
        node = self._cache[key]
        self._remove(node)
        self._add_to_head(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        if key in self._cache:
            node = self._cache[key]
            node.value = value
            self._remove(node)
            self._add_to_head(node)
        else:
            if len(self._cache) >= self._capacity:
                lru = self._tail.prev
                self._remove(lru)
                del self._cache[lru.key]
            node = self._Node(key, value)
            self._cache[key] = node
            self._add_to_head(node)

# 测试
cache = LRUCache(3)
cache.put(1, 10)
cache.put(2, 20)
cache.put(3, 30)
print(f"初始: get(1)={cache.get(1)} (访问了 key=1)")
cache.put(4, 40)  # 应该淘汰 key=2
print(f"put(4): get(2)={cache.get(2)} (期望 -1, 被淘汰)")
print(f"get(3)={cache.get(3)}")
print(f"get(4)={cache.get(4)}")

print("\n✅ 进阶用法演示完毕！")
