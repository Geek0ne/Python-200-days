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

**参考答案**

**两个栈 → 队列**：一个"输入栈"只管入队，一个"输出栈"只管出队。出队时若输出栈为空，就把输入栈的元素**逐个弹出再压入**输出栈——顺序恰好被反转，栈底最早的元素到了输出栈顶，实现先进先出。每个元素最多被搬一次，所以均摊 O(1)。

**两个队列 → 栈**：入队时永远放进非空的那个队列；出栈时把该队列的前 n-1 个元素搬到另一个队列，**留下的最后一个就是最新入队的**，弹出它即实现后进先出。代价是每次 pop 要搬 O(n) 个元素。

```python
from collections import deque


class StackQueue:
    """用两个栈实现队列（FIFO）"""
    def __init__(self):
        self.in_stack = []   # 只负责入队
        self.out_stack = []  # 只负责出队

    def enqueue(self, x):
        self.in_stack.append(x)

    def dequeue(self):
        if not self.out_stack:
            # 把输入栈整体倒入输出栈，顺序被反转，变成先进先出
            while self.in_stack:
                self.out_stack.append(self.in_stack.pop())
        if not self.out_stack:
            raise IndexError("dequeue from empty queue")
        return self.out_stack.pop()


class QueueStack:
    """用两个队列实现栈（LIFO）"""
    def __init__(self):
        self.q1 = deque()
        self.q2 = deque()

    def push(self, x):
        # 永远放进非空的那个队列（都空则放 q1）
        (self.q1 if self.q1 or not self.q2 else self.q2).append(x)

    def pop(self):
        if not self.q1 and not self.q2:
            raise IndexError("pop from empty stack")
        src, dst = (self.q1, self.q2) if self.q1 else (self.q2, self.q1)
        # 把前 n-1 个元素搬到另一个队列，只留下最后入队的那个
        while len(src) > 1:
            dst.append(src.popleft())
        return src.popleft()


q = StackQueue()
for x in (1, 2, 3):
    q.enqueue(x)
print(q.dequeue(), q.dequeue())  # 1 2
q.enqueue(4)
print(q.dequeue(), q.dequeue())  # 3 4

s = QueueStack()
for x in (1, 2, 3):
    s.push(x)
print(s.pop(), s.pop())  # 3 2
s.push(4)
print(s.pop(), s.pop())  # 4 1
```

预期输出：

```text
1 2
3 4
3 2
4 1
```

💡 提示：也可以让"两个队列实现栈"的 push 变 O(n)、pop 变 O(1)（新元素进空队列，再把旧元素全部搬过来），思路对称，按读写频率选择即可。

2. **表达式求值**：如何扩展表达式求值支持幂运算（`**`）和取模（`%`）？

**参考答案**

在"中缀转后缀 + 后缀求值"的框架上改三处即可：

1. **优先级表**：`%` 与 `*`、`/` 同级（记 2）；`**` 最高（记 3）。
2. **结合性**：`**` 是**右结合**——`2**3**2` 应算成 `2**(3**2)=512` 而非 `(2**3)**2=64`。体现在调度场算法里：遇到右结合运算符时，只弹出栈顶优先级**严格更高**的运算符（相等不弹）。
3. **分词**：`**` 是两个字符，扫描时要把相邻的两个 `*` 识别成一个 token，不能拆成两个乘号。

```python
PREC = {'+': 1, '-': 1, '*': 2, '/': 2, '%': 2, '**': 3}
RIGHT_ASSOC = {'**'}  # 幂运算是右结合：2**3**2 == 2**(3**2)


def tokenize(expr):
    """把表达式切成 token，支持多位数与双字符运算符 **"""
    tokens = []
    i = 0
    while i < len(expr):
        c = expr[i]
        if c.isspace():
            i += 1
        elif c.isdigit() or c == '.':
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
                j += 1
            tokens.append(expr[i:j])
            i = j
        elif c == '*' and i + 1 < len(expr) and expr[i + 1] == '*':
            tokens.append('**')  # 两个字符一起识别
            i += 2
        elif c in '+-*/%()':
            tokens.append(c)
            i += 1
        else:
            raise ValueError(f"非法字符: {c}")
    return tokens


def to_rpn(tokens):
    """调度场算法：中缀 -> 后缀"""
    output, ops = [], []
    for tok in tokens:
        if tok not in PREC and tok not in '()':
            output.append(tok)  # 数字直接输出
        elif tok == '(':
            ops.append(tok)
        elif tok == ')':
            while ops and ops[-1] != '(':
                output.append(ops.pop())
            if not ops:
                raise ValueError("括号不匹配")
            ops.pop()  # 丢掉左括号
        else:
            # 右结合运算符只弹出优先级"严格更高"的栈顶
            while (ops and ops[-1] != '(' and
                   (PREC[ops[-1]] > PREC[tok] or
                    (PREC[ops[-1]] == PREC[tok] and tok not in RIGHT_ASSOC))):
                output.append(ops.pop())
            ops.append(tok)
    while ops:
        op = ops.pop()
        if op == '(':
            raise ValueError("括号不匹配")
        output.append(op)
    return output


def eval_rpn(rpn):
    """后缀表达式求值"""
    stack = []
    for tok in rpn:
        if tok in PREC:
            b, a = stack.pop(), stack.pop()  # 注意先弹的是右操作数
            if tok == '+':
                stack.append(a + b)
            elif tok == '-':
                stack.append(a - b)
            elif tok == '*':
                stack.append(a * b)
            elif tok == '/':
                stack.append(a / b)
            elif tok == '%':
                stack.append(a % b)
            else:
                stack.append(a ** b)
        else:
            stack.append(float(tok) if '.' in tok else int(tok))
    return stack[0]


def calculate(expr):
    return eval_rpn(to_rpn(tokenize(expr)))


print(calculate('2 + 3 * 4'))        # 14
print(calculate('2 ** 3 ** 2'))      # 512，右结合
print(calculate('10 % 3 + 2 ** 3'))  # 9
print(calculate('(2 + 3) * 4 ** 2')) # 80
```

预期输出：

```text
14
512
9
80
```

💡 提示：`-3+2` 这类开头的一元负号、以及 `2*-3` 中的一元负号需要额外处理（本例聚焦二元运算符）；取模对负数的行为遵循 Python 的"结果符号跟除数"规则。

3. **堆**：如何用堆实现一个 O(log n) 时间复杂度的「动态中位数查找」？

**参考答案**

用**两个堆把数据流劈成两半**：

- `lo`：最大堆（`heapq` 只有最小堆，存负值模拟），装**较小的一半**，堆顶是这一半的最大值；
- `hi`：最小堆，装**较大的一半**，堆顶是这一半的最小值。

维护两条不变量：① `lo` 里所有数 ≤ `hi` 里所有数；② 两堆大小相等，或 `lo` 恰好多一个。这样中位数要么是 `lo` 堆顶（奇数个），要么是两堆顶的平均（偶数个），读取 O(1)。

插入的套路是"先进 `lo`，再把 `lo` 的最大值送给 `hi`，若 `hi` 变多了再还一个回来"——三次堆操作，每次 O(log n)。

```python
import heapq


class MedianFinder:
    def __init__(self):
        self.lo = []  # 最大堆（存负值）：较小的一半
        self.hi = []  # 最小堆：较大的一半

    def add(self, num):
        # 先入较小半，再把其中最大值移入较大半，保证 lo 中所有数 <= hi 中所有数
        heapq.heappush(self.lo, -num)
        heapq.heappush(self.hi, -heapq.heappop(self.lo))
        # 保持数量平衡：lo 最多比 hi 多一个
        if len(self.hi) > len(self.lo):
            heapq.heappush(self.lo, -heapq.heappop(self.hi))

    def median(self):
        if len(self.lo) > len(self.hi):
            return -self.lo[0]           # 奇数个：较小半的堆顶
        return (-self.lo[0] + self.hi[0]) / 2  # 偶数个：两堆顶平均


mf = MedianFinder()
for x in [5, 2, 8, 1, 9]:
    mf.add(x)
    print(x, '->', mf.median())
```

预期输出：

```text
5 -> 5
2 -> 3.5
8 -> 5
1 -> 3.5
9 -> 5
```

对比：每次插入后重新排序要 O(n log n)，双堆方案把插入压到 O(log n)、查询 O(1)，数据流越大优势越明显。

4. **bisect**：`bisect_left` 和 `bisect_right` 在查找元素是否存在的场景下，性能差在哪里？如何配合使用？

**参考答案**

先纠正一个预设：**两者性能没有实质差别**——都是同一套二分查找，时间复杂度都是 O(log n)，常数差异可忽略。真正的区别是**语义**：遇到重复元素时，`bisect_left` 返回"第一个 ≥ x 的位置"（相等元素的最左端），`bisect_right` 返回"第一个 > x 的位置"（相等元素的最右端之后）。

**判断存在**：用 `bisect_left` 找到插入点 `i`，再检查 `i < len(a) and a[i] == x`。一次二分 + 一次比较即可，无需遍历。

**配合使用**：`left = bisect_left(a, x)`、`right = bisect_right(a, x)`，则区间 `[left, right)` 恰好是所有等于 x 的元素，`right - left` 就是 x 出现的次数——这是统计重复元素个数的标准写法。

```python
import bisect

arr = [1, 3, 5, 7, 7, 7, 9, 11]

# 判断存在：bisect_left + 一次比较
i = bisect.bisect_left(arr, 7)
print(i < len(arr) and arr[i] == 7)   # True
j = bisect.bisect_left(arr, 6)
print(j < len(arr) and arr[j] == 6)   # False

# 配合使用：定位所有 7 的范围与个数
left = bisect.bisect_left(arr, 7)
right = bisect.bisect_right(arr, 7)
print(left, right)          # 3 6
print(right - left)         # 3 个
print(arr[left:right])      # [7, 7, 7]
```

预期输出：

```text
True
False
3 6
3
[7, 7, 7]
```

⚠️ 注意：bisect 的前提是列表**已按升序排好**；对无序列表结果无意义。另外 `insort` 虽然定位是 O(log n)，但列表插入要移动元素，整体仍是 O(n)。

5. **综合**：如果你需要维护一个操作系统级别的任务调度器，你会如何组合使用这些数据结构？

**参考答案**

让每种结构各司其职：

- **堆（heapq）→ 就绪队列**：按 `(优先级, 序号, 任务)` 组织，O(log n) 取出优先级最高的任务；序号做第二关键字，既保证同优先级按提交顺序（FIFO），又避免直接比较任务对象。
- **deque → 等待/轮转队列**：等待 I/O 或资源的任务按 FIFO 排队；同优先级任务做时间片轮转（round-robin）时，用完时间片的任务 `append` 到队尾。
- **有序表 + bisect → 定时器**：把 `(唤醒时刻, 任务)` 按时间有序维护，用 `bisect_right(times, now)` 一步找出所有已到期的任务；任务量大时也可改用按截止时间的堆。
- **字典 → 任务表**：按任务 ID 做 O(1) 查找/取消；堆中已取消的任务用"懒删除"（弹出时检查标记再丢弃）。
- **栈 → 现场保存**：任务切换/中断嵌套时保存与恢复执行现场，天然对应调用栈的 LIFO 语义。

一个极简骨架（堆 + FIFO 序号）：

```python
import heapq
from collections import deque

ready = []          # 堆：(优先级, 序号, 任务ID)，数字越小优先级越高
waiting = deque()   # FIFO 队列：等待资源的任务
seq = 0             # 序号：优先级相同时按提交顺序（FIFO）


def submit(task_id, priority):
    global seq
    heapq.heappush(ready, (priority, seq, task_id))
    seq += 1


def next_task():
    if ready:
        return heapq.heappop(ready)[2]
    return None


submit('compile', 5)
submit('io_flush', 1)
submit('backup', 9)
print(next_task(), next_task(), next_task())
```

预期输出：

```text
io_flush compile backup
```

优先级 1 的 `io_flush` 最先出队；真实调度器还会加上多级反馈队列（多个 deque + 动态优先级）、抢占和时间片统计，但骨架就是"堆选最急、队列保公平、二分管时间、字典管状态"。

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
