# Day 028 — 数据结构综合

> 深入理解栈、队列、堆与二分查找，实战表达式求值

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 栈 (Stack) | ⭐⭐ | LIFO 原理、Python 实现、应用场景 |
| 队列 (Queue) | ⭐⭐ | FIFO 原理、deque 实现、优先队列 |
| 堆 (heapq) | ⭐⭐⭐ | 堆数据结构、heapq 模块 API、堆排序 |
| bisect 模块 | ⭐⭐ | 二分查找算法、bisect API、有序列表维护 |
| 表达式求值 | ⭐⭐⭐⭐ | 中缀转后缀、逆波兰表达式、计算器实战 |

---

## 一、栈（Stack）

### 1.1 栈的原理

栈是一种 **后进先出（LIFO, Last In First Out）** 的线性数据结构。就像一摞盘子——最后放上去的盘子最先被拿走。

```
      ┌─────┐
      │  5  │ ← 栈顶 (top)
      ├─────┤
      │  4  │
      ├─────┤
      │  3  │
      ├─────┤
      │  2  │
      ├─────┤
      │  1  │ ← 栈底 (bottom)
      └─────┘
   push(6) → 从栈顶添加
   pop()   → 从栈顶移除
```

### 1.2 栈的核心操作

| 操作 | 描述 | 时间复杂度 |
|------|------|-----------|
| `push(x)` | 将元素 x 压入栈顶 | O(1) |
| `pop()` | 移除并返回栈顶元素 | O(1) |
| `peek()` | 返回栈顶元素不移除 | O(1) |
| `is_empty()` | 判断栈是否为空 | O(1) |
| `size()` | 返回栈中元素个数 | O(1) |

### 1.3 Python 实现栈

**方式一：使用列表（推荐日常使用）**

```python
stack = []
stack.append(1)       # push
stack.append(2)
top = stack.pop()      # pop → 2
top = stack[-1]        # peek → 1
```

**方式二：链表实现（理解原理）**

```python
class Node:
    def __init__(self, value):
        self.value = value
        self.next = None

class Stack:
    def __init__(self):
        self.top = None
        self._size = 0
    
    def push(self, value):
        node = Node(value)
        node.next = self.top
        self.top = node
        self._size += 1
    
    def pop(self):
        if self.is_empty():
            raise IndexError("pop from empty stack")
        value = self.top.value
        self.top = self.top.next
        self._size -= 1
        return value
    
    def peek(self):
        if self.is_empty():
            raise IndexError("peek from empty stack")
        return self.top.value
    
    def is_empty(self):
        return self.top is None
    
    def __len__(self):
        return self._size
```

### 1.4 栈的应用场景

- **函数调用栈**：Python 解释器使用调用栈跟踪函数调用
- **括号匹配**：检查代码中括号是否成对
- **撤销操作**：编辑器的 Ctrl+Z
- **浏览器后退**：页面历史记录
- **表达式求值**：中缀转后缀

---

## 二、队列（Queue）

### 2.1 队列的原理

队列是一种 **先进先出（FIFO, First In First Out）** 的线性数据结构。就像排队买东西——先到的人先服务。

```
  出队 ← ┌──┬──┬──┬──┬──┐ ← 入队
         │1 │2 │3 │4 │5 │
         └──┴──┴──┴──┴──┘
         队头         队尾
```

### 2.2 队列的核心操作

| 操作 | 描述 | 时间复杂度 |
|------|------|-----------|
| `enqueue(x)` | 将元素 x 加入队尾 | O(1) |
| `dequeue()` | 移除并返回队头元素 | O(1) |
| `front()` | 返回队头元素不移除 | O(1) |
| `is_empty()` | 判断队列是否为空 | O(1) |
| `size()` | 返回队列中元素个数 | O(1) |

### 2.3 Python 实现队列

**推荐方式：collections.deque**

```python
from collections import deque

queue = deque()
queue.append(1)      # 入队（队尾）
queue.append(2)
front = queue.popleft()  # 出队（队头）→ 1
```

**为什么用 deque 而不是 list？**

```
list.pop(0)      → O(n) — 所有元素要前移
deque.popleft()  → O(1) — 双向链表
```

### 2.4 优先队列

优先队列中，每个元素都有一个优先级，优先级最高的元素最先出队。

```python
import heapq

class PriorityQueue:
    def __init__(self):
        self._heap = []
        self._index = 0
    
    def push(self, item, priority):
        heapq.heappush(self._heap, (priority, self._index, item))
        self._index += 1
    
    def pop(self):
        return heapq.heappop(self._heap)[-1]
    
    def is_empty(self):
        return len(self._heap) == 0
```

### 2.5 队列的应用场景

- **任务调度**：打印机队列、线程池
- **广度优先搜索（BFS）**：图论算法
- **消息队列**：生产者-消费者模式
- **缓存淘汰（LRU）**：最近最少使用缓存
- **数据缓冲**：网络数据包排队

---

## 三、堆（heapq）

### 3.1 堆的原理

堆是一种 **完全二叉树** 结构，Python 中的 `heapq` 实现的是 **最小堆（min-heap）**：

- 父节点的值 ≤ 子节点的值
- 堆顶（root）永远是最小值
- 用列表存储：`heap[i]` 的子节点为 `heap[2*i+1]` 和 `heap[2*i+2]`

```
        1
       / \
      3   5
     / \ / \
    7  6 8  9
    
    列表表示: [1, 3, 5, 7, 6, 8, 9]
```

### 3.2 heapq 模块 API

| 函数 | 描述 | 时间复杂度 |
|------|------|-----------|
| `heappush(heap, item)` | 将元素插入堆 | O(log n) |
| `heappop(heap)` | 弹出并返回最小值 | O(log n) |
| `heapify(x)` | 将列表转换为堆 | O(n) |
| `heapreplace(heap, item)` | 弹出最小值，压入新值 | O(log n) |
| `heappushpop(heap, item)` | 先压再弹，效率更高 | O(log n) |
| `nlargest(n, iterable)` | 返回最大的 n 个元素 | O(n log k) |
| `nsmallest(n, iterable)` | 返回最小的 n 个元素 | O(n log k) |
| `merge(*iterables)` | 合并多个有序迭代器 | O(n log k) |

### 3.3 堆排序

```python
import heapq

def heap_sort(arr):
    heapq.heapify(arr)
    return [heapq.heappop(arr) for _ in range(len(arr))]
```

### 3.4 堆的应用场景

- **优先队列**：任务调度、Dijkstra 最短路径
- **Top K 问题**：求最大/最小的 K 个元素
- **中位数查找**：两个堆维护数据流的中位数
- **合并有序文件**：多路归并
- **定时器**：最近触发时间优先

### 3.5 最大堆的实现

Python 的 heapq 只支持最小堆。要实现最大堆，可以存储负值：

```python
import heapq

# 最大堆：存储负值
max_heap = []
heapq.heappush(max_heap, -3)
heapq.heappush(max_heap, -1)
heapq.heappush(max_heap, -2)
largest = -heapq.heappop(max_heap)  # 3
```

---

## 四、bisect 模块

### 4.1 二分查找原理

二分查找（Binary Search）是一种在 **有序列表** 中查找元素的算法，每次将搜索范围缩小一半。

```
查找目标值 7：
             ┌────────────────────────────┐
             │1  3  5  7  9  11  13  15  17│
         L=0 ↑                    ↑ R=8
               mid = (0+8)//2 = 4
               arr[4] = 9 > 7 → R = 3
             ┌────────────────┐
             │1  3  5  7  9  │
             L=0    ↑    R=3
               mid = (0+3)//2 = 1
               arr[1] = 3 < 7 → L = 2
                    ┌─────────┐
                    │5  7  9  │
                  L=2 ↑  ↑ R=3
               mid = (2+3)//2 = 2
               arr[2] = 5 < 7 → L = 3
                       ┌──────┐
                       │7  9  │
                    L=3 ↑  ↑ R=3
               arr[3] = 7 == 7 ✓ 找到！
```

### 4.2 bisect API

| 函数 | 描述 | 时间复杂度 |
|------|------|-----------|
| `bisect_left(a, x)` | 查找插入点，相等时插左边 | O(log n) |
| `bisect_right(a, x)` | 查找插入点，相等时插右边 | O(log n) |
| `bisect(a, x)` | 等价于 `bisect_right` | O(log n) |
| `insort_left(a, x)` | 插入到 `bisect_left` 位置 | O(n) |
| `insort_right(a, x)` | 插入到 `bisect_right` 位置 | O(n) |
| `insort(a, x)` | 等价于 `insort_right` | O(n) |

### 4.3 bisect_left vs bisect_right

```python
import bisect

arr = [1, 3, 5, 7, 7, 7, 9, 11]

# bisect_left — 插入到第一个 7 的左边
pos = bisect.bisect_left(arr, 7)   # → 3

# bisect_right — 插入到最后一个 7 的右边
pos = bisect.bisect_right(arr, 7)  # → 6
```

### 4.4 bisect 的应用场景

- **成绩等级划分**：根据分数自动判断等级
- **日程冲突检测**：维护有序时间表
- **在线更新排序列表**：保持列表有序
- **区间查询**：查找重叠区间

---

## 五、表达式求值实战

### 5.1 问题描述

实现一个能计算算术表达式的计算器，支持：
- 加减乘除：+, -, *, /
- 括号：(, )
- 运算优先级：先乘除后加减

### 5.2 算法流程

```
"3 + 4 * (2 - 1)" → 7

步骤：
1. 中缀表达式 → 后缀表达式（逆波兰表示法）
2. 后缀表达式求值

中缀:  3 + 4 * ( 2 - 1 )
        ↓ 运算符优先级 + 括号
后缀:  3 4 2 1 - * +

后缀求值:
  [3] → [3, 4] → [3, 4, 2] → [3, 4, 2, 1]
                                   遇到 - : 2-1=1
                                [3, 4, 1]
                                   遇到 * : 4*1=4
                                [3, 4]
                                   遇到 + : 3+4=7
                                结果: 7
```

### 5.3 两个核心算法

**中缀转后缀（调度场算法 — Shunting-yard Algorithm）：**

```
遍历每个 token：
  如果是数字 → 输出到后缀列表
  如果是运算符：
    当栈顶运算符优先级 ≥ 当前运算符时 → 弹出到输出
    当前运算符入栈
  如果是左括号 → 入栈
  如果是右括号 → 弹出到输出直到匹配左括号
结束后 → 弹出栈中剩余运算符
```

**后缀表达式求值（逆波兰求值）：**

```
遍历每个 token：
  如果是数字 → 压入栈
  如果是运算符 → 弹出两个数计算，结果压栈
返回栈顶
```

### 5.4 边界情况与陷阱

| 情况 | 处理方式 |
|------|---------|
| 空格 | 去除所有空格 |
| 多位数 | 解析连续数字 |
| 负数处理 | `-3+2` 开头的负号处理 |
| 除数为零 | 抛出 ZeroDivisionError |
| 小数 | 扩展支持浮点数 |
| 超大数字 | 溢出检查 |

---

## 六、思考题

1. **栈与队列**：如何使用两个栈实现一个队列？两个队列实现一个栈？
2. **表达式求值**：如何扩展表达式求值支持幂运算（`**`）和取模（`%`）？
3. **堆**：如何用堆实现一个 O(log n) 时间复杂度的「动态中位数查找」？
4. **bisect**：`bisect_left` 和 `bisect_right` 在查找元素是否存在的场景下，性能差在哪里？如何配合使用？
5. **综合**：如果你需要维护一个操作系统级别的任务调度器，你会如何组合使用这些数据结构？

---

## 📝 本章小结

| 知识点 | 掌握程度 |
|--------|---------|
| 栈的 Python 实现与应用 | ⭐⭐⭐ |
| 队列（deque）的实现与应用 | ⭐⭐⭐ |
| 优先队列与 heapq 模块 | ⭐⭐⭐⭐ |
| 二分查找与 bisect 模块 | ⭐⭐⭐⭐ |
| 表达式求值（中缀转后缀） | ⭐⭐⭐⭐⭐ |

> **"数据结构是程序的骨架。掌握栈、队列、堆和二分查找，你的工具箱就充实了一大半。"**

---

## 🚀 Phase 2 里程碑提示

Day 028 是 Phase 2（核心编程概念，Day 016–030）的倒数第三天。

**即将完成的核心主题线：**
- ✅ 文件 I/O → 异常处理 → 推导式 → Lambda → 递归
- ✅ 迭代器 → 生成器 → 装饰器 → 上下文管理器
- ✅ 字符串高级 → 时间日期 → **数据结构综合** ← 当前
- 📅 Day 029: 算法入门（排序/搜索/大O）
- 📅 Day 030: 阶段项目：命令行工具
