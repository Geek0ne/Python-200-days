"""
Day 028 — 数据结构综合：基础用法
======================================================================
栈、队列、优先队列、heapq、bisect 的基础用法演示
======================================================================
"""

print("=" * 60)
print("1️⃣  栈（Stack）— LIFO 后进先出")
print("=" * 60)

# ----- 列表实现栈 -----
stack = []
stack.append(10)
stack.append(20)
stack.append(30)
print(f"压入 10, 20, 30 后的栈: {stack}")
print(f"弹出: {stack.pop()}, 栈顶 peek: {stack[-1]}")
print(f"栈是否为空: {len(stack) == 0}")
print(f"栈大小: {len(stack)}")

# ----- 自定义 Stack 类 -----
class Stack:
    """基于链表的栈实现"""
    class _Node:
        __slots__ = ('value', 'next')
        def __init__(self, value, next_node=None):
            self.value = value
            self.next = next_node

    def __init__(self):
        self._top = None
        self._size = 0

    def push(self, value):
        self._top = self._Node(value, self._top)
        self._size += 1

    def pop(self):
        if self.is_empty():
            raise IndexError("pop from empty stack")
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self):
        if self.is_empty():
            raise IndexError("peek from empty stack")
        return self._top.value

    def is_empty(self):
        return self._top is None

    def __len__(self):
        return self._size

    def __repr__(self):
        values = []
        cur = self._top
        while cur:
            values.append(str(cur.value))
            cur = cur.next
        return f"Stack(top→bottom): [{', '.join(values)}]"

s = Stack()
s.push(1)
s.push(2)
s.push(3)
print(f"\n链表栈: {s}")
print(f"弹出: {s.pop()}, peek: {s.peek()}, size: {len(s)}")

# ----- 栈的应用：括号匹配 -----
def is_balanced(s: str) -> bool:
    """检查括号是否匹配"""
    pairs = {')': '(', ']': '[', '}': '{'}
    stack = []
    for ch in s:
        if ch in '([{':
            stack.append(ch)
        elif ch in ')]}':
            if not stack or stack[-1] != pairs[ch]:
                return False
            stack.pop()
    return len(stack) == 0

print(f"\n括号匹配 '({[]})': {is_balanced('({[]})')}")
print(f"括号匹配 '([)]':   {is_balanced('([)]')}")
print(f"括号匹配 '((()':    {is_balanced('((()')}")


print("\n" + "=" * 60)
print("2️⃣  队列（Queue）— FIFO 先进先出")
print("=" * 60)

from collections import deque

# ----- deque 实现队列 -----
queue = deque()
queue.append(1)
queue.append(2)
queue.append(3)
print(f"入队 1, 2, 3: {list(queue)}")
print(f"出队: {queue.popleft()}")
print(f"出队: {queue.popleft()}")
print(f"队列剩余: {list(queue)}")

# 性能对比：list.pop(0) vs deque.popleft()
import time

def benchmark_queue(impl, count=100000):
    start = time.perf_counter()
    for i in range(count):
        impl.append(i)
    for i in range(count):
        if isinstance(impl, list):
            impl.pop(0)
        else:
            impl.popleft()
    return time.perf_counter() - start

# Note: 只用较小数量做对比，避免 list.pop(0) 太慢
small_count = 10000
list_time = benchmark_queue([], small_count)
deque_time = benchmark_queue(deque(), small_count)
print(f"\n性能对比（{small_count} 次入出队）:")
print(f"  list.pop(0):  {list_time:.4f}s")
print(f"  deque.popleft(): {deque_time:.4f}s")
print(f"  deque 快 {list_time/deque_time:.1f} 倍")


print("\n" + "=" * 60)
print("3️⃣  堆（heapq）")
print("=" * 60)

import heapq

# ----- 基本操作 -----
heap = []
heapq.heappush(heap, 5)
heapq.heappush(heap, 3)
heapq.heappush(heap, 7)
heapq.heappush(heap, 1)
print(f"堆内容: {heap}")
print(f"弹出最小值: {heapq.heappop(heap)}")
print(f"弹出最小值: {heapq.heappop(heap)}")
print(f"剩余堆: {heap}")

# ----- heapify -----
arr = [9, 5, 3, 8, 1, 6, 2]
print(f"\n原始列表: {arr}")
heapq.heapify(arr)
print(f"堆化后:    {arr}")

# ----- 堆排序 -----
def heap_sort(arr):
    """堆排序"""
    heapq.heapify(arr)
    return [heapq.heappop(arr) for _ in range(len(arr))]

data = [9, 5, 3, 8, 1, 6, 2]
print(f"\n堆排序 {data} → {heap_sort(data[:])}")

# ----- nlargest / nsmallest -----
scores = [85, 92, 78, 95, 88, 76, 99, 81, 90, 87]
print(f"\n成绩: {scores}")
print(f"Top 3:  {heapq.nlargest(3, scores)}")
print(f"Bottom 3: {heapq.nsmallest(3, scores)}")


print("\n" + "=" * 60)
print("4️⃣  bisect — 二分查找与有序插入")
print("=" * 60)

import bisect

# ----- 二分查找插入点 -----
sorted_arr = [1, 3, 5, 7, 7, 7, 9, 11]
print(f"有序数组: {sorted_arr}")

# 查找插入点
pos_left = bisect.bisect_left(sorted_arr, 7)
pos_right = bisect.bisect_right(sorted_arr, 7)
print(f"bisect_left(7)  = {pos_left}  (插入到第一个 7 左边)")
print(f"bisect_right(7) = {pos_right} (插入到最后一个 7 右边)")

# ----- 有序插入 -----
data = [1, 3, 5, 7, 9, 11]
bisect.insort(data, 6)
bisect.insort(data, 8)
bisect.insort(data, 2)
print(f"\n有序插入后: {data}")

# ----- 成绩等级划分 -----
def grade(score, breakpoints=[60, 70, 80, 90], grades='FDCBA'):
    """根据分数返回等级"""
    i = bisect.bisect(breakpoints, score)
    return grades[i]

scores_list = [55, 62, 75, 88, 95, 100]
print(f"\n成绩等级划分:")
for s in scores_list:
    print(f"  {s:3d} → {grade(s)}")

# ----- 查找元素是否存在 -----
def exists(sorted_arr, target):
    """在有序数组中查找元素是否存在"""
    i = bisect.bisect_left(sorted_arr, target)
    return i < len(sorted_arr) and sorted_arr[i] == target

print(f"\n查找元素:")
for t in [4, 7, 9, 12]:
    print(f"  {t} 在数组中: {exists(sorted_arr, t)}")


print("\n" + "=" * 60)
print("5️⃣  优先队列（PriorityQueue）")
print("=" * 60)

class PriorityQueue:
    """基于 heapq 的优先队列"""
    def __init__(self):
        self._heap = []
        self._index = 0

    def push(self, item, priority):
        heapq.heappush(self._heap, (priority, self._index, item))
        self._index += 1

    def pop(self):
        if self.is_empty():
            raise IndexError("pop from empty priority queue")
        return heapq.heappop(self._heap)[-1]

    def peek(self):
        if self.is_empty():
            raise IndexError("peek from empty priority queue")
        return self._heap[0][-1]

    def is_empty(self):
        return len(self._heap) == 0

    def __len__(self):
        return len(self._heap)

# 演示：任务调度
pq = PriorityQueue()
pq.push("写日报", 3)
pq.push("紧急修复Bug", 1)   # 优先级最高
pq.push("代码审查", 2)
pq.push("整理文档", 5)
pq.push("开会", 1)           # 相同优先级，按入队顺序

print("任务调度（优先级从高到低）:")
while not pq.is_empty():
    print(f"  执行: {pq.pop()}")

print("\n✅ 基础用法演示完毕！")
