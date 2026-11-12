# Day 029 — 算法入门

> 排序算法、搜索算法、时间复杂度与大 O 表示法

---

## 📖 本章概览

| 主题 | 难度 | 内容 |
|------|------|------|
| 大 O 表示法 | ⭐⭐ | 时间复杂度、空间复杂度、常见复杂度 |
| 冒泡排序 | ⭐⭐ | 交换排序、O(n²)、优化版本 |
| 选择排序 | ⭐⭐ | 不稳定排序、O(n²) |
| 插入排序 | ⭐⭐ | 局部有序、近乎有序时高效 |
| 快速排序 | ⭐⭐⭐ | 分治思想、枢纽选择、O(n log n) |
| 归并排序 | ⭐⭐⭐ | 分治思想、稳定排序、额外空间 |
| 线性搜索 | ⭐ | 无序数据、O(n) |
| 二分搜索 | ⭐⭐ | 有序数据、O(log n) |

---

## 一、时间复杂度与大 O 表示法

### 1.1 什么是时间复杂度

时间复杂度描述 **算法执行时间随输入规模增长的变化趋势**。

> 「大 O」表示法的数学定义：存在常数 c 和 n₀，使得当 n ≥ n₀ 时，T(n) ≤ c·f(n)，则称 T(n) = O(f(n))。

简单理解：**忽略常数和低阶项，只保留增长最快的部分**。

```
T(n) = 3n² + 2n + 1  →  大 O: O(n²)
T(n) = 5n + 10       →  大 O: O(n)
T(n) = 2ⁿ + n³       →  大 O: O(2ⁿ)
```

### 1.2 常见时间复杂度

| 复杂度 | 名称 | 示例 | n=100 时的操作数 |
|--------|------|------|-----------------|
| O(1) | 常数时间 | 数组索引、哈希查找 | 1 |
| O(log n) | 对数时间 | 二分查找 | ≈ 7 |
| O(n) | 线性时间 | 线性搜索、遍历 | 100 |
| O(n log n) | 线性对数时间 | 快排、归并 | ≈ 664 |
| O(n²) | 平方时间 | 冒泡、选择 | 10,000 |
| O(2ⁿ) | 指数时间 | 斐波那契递归 | 2¹⁰⁰ ≈ 天文数字 |
| O(n!) | 阶乘时间 | 旅行商问题 | 9.3 × 10¹⁵⁷ |

### 1.3 增长趋势对比

```
操作数
  ↑
  |                          2ⁿ
  |                      ____/
  |                  __/
  |             ___/  n²
  |         ___/
  |     ___/  n log n
  |    / 
  |   /   n
  |   _
  | /   log n
  |____________________________→ 输入规模 n
```

### 1.4 空间复杂度

记录算法执行过程中 **额外占用的内存空间**。

```python
# O(1) — 只用了几个变量
def sum_list(arr):
    total = 0
    for x in arr:
        total += x
    return total

# O(n) — 创建了新的列表
def double_list(arr):
    return [x * 2 for x in arr]

# O(n²) — 创建了二维矩阵
def create_matrix(n):
    return [[i * j for j in range(n)] for i in range(n)]
```

### 1.5 如何分析时间复杂度

**规则 1：顺序结构取最大值**
```python
for x in arr:    # O(n)
    pass
for y in arr:    # O(n)
    pass
# 总复杂度: O(n) + O(n) = O(n)
```

**规则 2：循环嵌套用乘法**
```python
for x in arr:        # O(n)
    for y in arr:    # O(n)
        pass
# 总复杂度: O(n) × O(n) = O(n²)
```

**规则 3：递归看递推关系**
```python
# T(n) = T(n-1) + O(1) → O(n)
def factorial(n):
    if n <= 1: return 1
    return n * factorial(n-1)

# T(n) = 2T(n/2) + O(n) → O(n log n)
def merge_sort(arr):
    ...
```

**规则 4：对数复杂度的判定**
```python
# 每次规模减半 → O(log n)
def binary_search(arr, target):
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target: return mid
        elif arr[mid] < target: low = mid + 1
        else: high = mid - 1
    return -1
```

---

## 二、冒泡排序 (Bubble Sort)

### 2.1 原理

相邻元素两两比较，大的往后"冒泡"。每一趟确定一个最大值在末尾。

```
初始:  [5, 3, 8, 6, 4]
第一趟:
  [3, 5, 8, 6, 4]  → 5 vs 3 → 交换
  [3, 5, 8, 6, 4]  → 5 vs 8 → 不动
  [3, 5, 6, 8, 4]  → 8 vs 6 → 交换
  [3, 5, 6, 4, 8]  → 8 vs 4 → 交换  ✓ 8 已就位

第二趟:
  [3, 5, 6, 4, 8]  → 3 vs 5 → 不动
  [3, 5, 6, 4, 8]  → 5 vs 6 → 不动
  [3, 5, 4, 6, 8]  → 6 vs 4 → 交换  ✓ 6 已就位

第三趟:
  [3, 5, 4, 6, 8]  → 3 vs 5 → 不动
  [3, 4, 5, 6, 8]  → 5 vs 4 → 交换  ✓ 5 已就位

第四趟:
  [3, 4, 5, 6, 8]  → 3 vs 4 → 不动  ✓ 全部有序
```

### 2.2 代码

```python
def bubble_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break  # 优化：提前终止
    return arr
```

### 2.3 复杂度分析

| | 最坏 | 平均 | 最好 | 空间 | 稳定性 |
|---|---|---|---|---|---|
| 冒泡排序 | O(n²) | O(n²) | O(n) | O(1) | ✅ 稳定 |

---

## 三、选择排序 (Selection Sort)

### 3.1 原理

每一趟找到未排序部分的最小值，放到已排序部分的末尾。

```
初始:  [5, 3, 8, 6, 4]

第1趟: 找到最小值 3，与 5 交换 → [3, 5, 8, 6, 4]
第2趟: 找到最小值 4 (从索引1起)，与 5 交换 → [3, 4, 8, 6, 5]
第3趟: 找到最小值 5，与 8 交换 → [3, 4, 5, 6, 8]
第4趟: 无需交换 → [3, 4, 5, 6, 8]
```

### 3.2 代码

```python
def selection_sort(arr):
    n = len(arr)
    for i in range(n - 1):
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        if min_idx != i:
            arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr
```

### 3.3 复杂度

| | 最坏 | 平均 | 最好 | 空间 | 稳定性 |
|---|---|---|---|---|---|
| 选择排序 | O(n²) | O(n²) | O(n²) | O(1) | ❌ 不稳定 |

---

## 四、插入排序 (Insertion Sort)

### 4.1 原理

将待排序元素插入到已排序部分的正确位置——像打牌时整理手牌。

```
初始:  [5, 3, 8, 6, 4]
                              │ 竖线左侧为已排序区
第1步: [5 | 3, 8, 6, 4]      → 3<5 → 插入
       [3, 5 | 8, 6, 4]
第2步: [3, 5 | 8, 6, 4]      → 8>5 → 不动
       [3, 5, 8 | 6, 4]
第3步: [3, 5, 8 | 6, 4]      → 6<8 → 插入
       [3, 5, 6, 8 | 4]
第4步: [3, 5, 6, 8 | 4]      → 4<8,4<6,4<5,4>3 → 插入
       [3, 4, 5, 6, 8]
```

### 4.2 代码

```python
def insertion_sort(arr):
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr
```

### 4.3 复杂度

| | 最坏 | 平均 | 最好 | 空间 | 稳定性 |
|---|---|---|---|---|---|
| 插入排序 | O(n²) | O(n²) | O(n) | O(1) | ✅ 稳定 |

---

## 五、快速排序 (Quick Sort)

### 5.1 原理

分治思想的核心步骤：

1. 选一个元素作为 **枢纽 (pivot)**
2. **分割 (partition)**：把数组分成两部分 — 左边都 ≤ pivot，右边都 > pivot
3. 递归对左右两部分进行快速排序

```
初始:  [8, 3, 5, 1, 9, 4, 7, 6]
             选择 pivot = 6

分割过程:
  左指针→                     ←右指针
  [8, 3, 5, 1, 9, 4, 7, 6]
   ↑                       ↑
   L                       R

  8 > 6, 6 < 7 → 不交换:
  [4, 3, 5, 1, 9, 8, 7, 6]
         ↑         ↑
         L         R
  
  交叉 → 退出:
  [4, 3, 5, 1, 6, 8, 7, 9]
                ↑
              pivot就位

递归:
  左: [4, 3, 5, 1]  右: [8, 7, 9]
```

### 5.2 代码

```python
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)
```

**原地版本（面试高频）：**

```python
def quick_sort_inplace(arr, low=0, high=None):
    if high is None:
        high = len(arr) - 1
    if low < high:
        pi = partition(arr, low, high)
        quick_sort_inplace(arr, low, pi - 1)
        quick_sort_inplace(arr, pi + 1, high)

def partition(arr, low, high):
    pivot = arr[high]  # 选最后一个为 pivot
    i = low - 1
    for j in range(low, high):
        if arr[j] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1
```

### 5.3 复杂度

| | 最坏 | 平均 | 最好 | 空间 | 稳定性 |
|---|---|---|---|---|---|
| 快速排序 | O(n²) | O(n log n) | O(n log n) | O(log n) | ❌ 不稳定 |

> ⚠️ 最坏情况发生在每次选择的 pivot 都是极值（有序数组）。优化策略：随机选 pivot / 三数取中。

---

## 六、归并排序 (Merge Sort)

### 6.1 原理

分治思想的另一经典应用：

1. **分割 (Divide)**：将数组递归分成两半，直到每个子数组只有一个元素
2. **合并 (Conquer)**：将两个有序子数组合并成一个有序数组

```
分割阶段:
[8, 3, 5, 1, 9, 4, 7, 6]
         ↓  分割
[8, 3, 5, 1]    [9, 4, 7, 6]
   ↓  分割          ↓  分割
[8, 3]  [5, 1]  [9, 4]  [7, 6]
 ↓ 分割  ↓ 分割   ↓ 分割  ↓ 分割
[8] [3] [5] [1] [9] [4] [7] [6]

合并阶段:
[3, 8]  [1, 5]  [4, 9]  [6, 7]
   ↓       ↓       ↓       ↓
[1, 3, 5, 8]        [4, 6, 7, 9]
         ↓               ↓
      [1, 3, 4, 5, 6, 7, 8, 9]
```

**合并两个有序数组的过程：**

```
合并 [3, 8] 和 [1, 5]:

3 vs 1 → 取 1    → [1]
3 vs 5 → 取 3    → [1, 3]
8 vs 5 → 取 5    → [1, 3, 5]
剩余 8          → [1, 3, 5, 8]
```

### 6.2 代码

```python
def merge_sort(arr):
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
```

### 6.3 复杂度

| | 最坏 | 平均 | 最好 | 空间 | 稳定性 |
|---|---|---|---|---|---|
| 归并排序 | O(n log n) | O(n log n) | O(n log n) | O(n) | ✅ 稳定 |

---

## 七、搜索算法

### 7.1 线性搜索 (Linear Search)

逐个检查每个元素，直到找到目标。

```python
def linear_search(arr, target):
    for i, val in enumerate(arr):
        if val == target:
            return i
    return -1
```

- 时间复杂度：O(n)
- 空间复杂度：O(1)
- 适用于：**无序数据**

### 7.2 二分搜索 (Binary Search)

在有序数组中，每次将搜索范围缩小一半。

```
在有序数组 [1, 3, 4, 6, 7, 8, 9, 12] 中搜索 7:

  [1, 3, 4, 6, 7, 8, 9, 12]
   ↑           ↑           ↑
   L         mid=4         R          arr[4] = 7 == 7 ✓ 找到!
```

```
搜索 5（不存在）:

  [1, 3, 4, 6, 7, 8, 9, 12]
   ↑           ↑           ↑
   L         mid=4         R          arr[4] = 7 > 5 → R = 3

  [1, 3, 4, 6]
   ↑     ↑    ↑
   L  mid=1   R            arr[1] = 3 < 5 → L = 2

  [4, 6]
   ↑  ↑
   L,R                   L = 2, R = 2, arr[2] = 4 < 5 → L = 3

  L > R → 未找到，返回 -1
```

**递归实现：**
```python
def binary_search_recursive(arr, target, low, high):
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search_recursive(arr, target, mid + 1, high)
    else:
        return binary_search_recursive(arr, target, low, mid - 1)
```

---

## 八、算法全景对比

| 算法 | 平均时间 | 最坏时间 | 空间 | 稳定 | 排序方式 | 适用场景 |
|------|---------|---------|------|------|---------|---------|
| 冒泡排序 | O(n²) | O(n²) | O(1) | ✅ | 内排 | 教学/小数据集 |
| 选择排序 | O(n²) | O(n²) | O(1) | ❌ | 内排 | 交换成本高的场景 |
| 插入排序 | O(n²) | O(n²) | O(1) | ✅ | 内排 | 近乎有序的数据 |
| 快速排序 | O(n log n) | O(n²) | O(log n) | ❌ | 内排 | ⭐ 通用首选 |
| 归并排序 | O(n log n) | O(n log n) | O(n) | ✅ | 外排 | 大数据/需要稳定 |
| 二分搜索 | O(log n) | O(log n) | O(1) | — | — | 有序数据查找 |

### 实际选择建议

```
数据量很小 (< 50)?
    ├── 近乎有序 → 插入排序
    └── 任意 → 随便选
数据量中等 (50 ~ 1000)?
    └── 快速排序
数据量很大 (> 1000)?
    ├── 需要稳定 → 归并排序
    └── 无所谓稳定 → 快速排序
需要有序查找频繁?
    └── 排序 + 二分搜索
```

---

## 💡 思考题

1. 快速排序在最坏情况下的时间复杂度是 O(n²)，什么场景会导致这个情况？如何避免？

**参考答案**

**触发场景**：每次选的枢纽（pivot）恰好是当前区间的最大值或最小值，分区变成"0 个 + n-1 个"的极端不平衡。最典型的是**对已排序（或逆序）数组固定取首/尾元素做枢纽**；大量重复元素配合糟糕的分区写法也会退化。此时递推式是 T(n) = T(n-1) + O(n)，展开就是 n+(n-1)+…+1 = O(n²)，递归深度也达到 n，可能栈溢出。

**避免手段**：

- **随机选枢纽**：让"最坏输入"无法被针对性构造，期望复杂度稳定 O(n log n)；
- **三数取中**：取首、中、尾三个数的中位数做枢纽，对抗有序输入；
- **三路分区**（荷兰国旗）：把等于枢纽的元素单独放一路，重复元素多时不再退化；
- **introsort**：递归过深时切换堆排序兜底（C++ `std::sort` 的思路）。

```python
import random


def quick_sort_count(arr, random_pivot=False):
    """原地快排（Lomuto 分区），统计比较次数"""
    comparisons = 0

    def sort(low, high):
        nonlocal comparisons
        if low >= high:
            return
        if random_pivot:
            r = random.randint(low, high)
            arr[r], arr[high] = arr[high], arr[r]
        pivot = arr[high]
        i = low - 1
        for j in range(low, high):
            comparisons += 1
            if arr[j] <= pivot:
                i += 1
                arr[i], arr[j] = arr[j], arr[i]
        arr[i + 1], arr[high] = arr[high], arr[i + 1]
        sort(low, i)
        sort(i + 2, high)

    sort(0, len(arr) - 1)
    return comparisons


data = list(range(200))  # 已排序数组
print("固定取末尾为枢纽:", quick_sort_count(data[:]))
random.seed(42)
print("随机枢纽:", quick_sort_count(data[:], random_pivot=True))
```

预期输出（随机枢纽的具体数值随种子变化）：

```text
固定取末尾为枢纽: 19900
随机枢纽: 1638
```

n=200 时固定枢纽比较了 19900 次 ≈ n²/2，随机枢纽只有约 1600 次 ≈ n log n，差距一目了然。

2. 为什么说冒泡排序的 swap 操作可以通过「标记是否交换」来优化？这个优化在什么场景下收益最大？

**参考答案**

冒泡排序每一趟把相邻元素两两比较、逆序就交换。**如果某一趟从头到尾一次交换都没发生，说明所有相邻对都已有序，整个数组必然已经排好**，后面的趟全是无用功，可以立即结束。这就是 `swapped` 标记的意义。

收益最大的场景是**输入已经有序或接近有序**：最好情况从 O(n²) 降到 O(n)（只扫一趟就退出）。如正文 2.3 节表格所示，"最好 O(n)"正是靠这个优化才成立的；最坏和平均仍是 O(n²)，优化不改变它们。

```python
def bubble(arr, optimized):
    n = len(arr)
    comparisons = 0
    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            comparisons += 1
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if optimized and not swapped:
            break  # 一整趟没有交换 → 已经有序
    return comparisons


data = list(range(100))  # 已排序输入
print("无优化:", bubble(data[:], False))
print("有优化:", bubble(data[:], True))
```

预期输出：

```text
无优化: 4950
有优化: 99
```

同样 100 个已排序元素：无优化要比较 4950 次（n(n-1)/2），有优化只比较 99 次（一趟）就提前退出。

💡 提示：这也是"插入排序适合近乎有序数据"的同类思想——利用输入已有的有序性省掉无用功；Python 内置的 Timsort 更是把这一思想发挥到极致。

3. 归并排序的空间复杂度为什么是 O(n)？能否改进到 O(1)？

**参考答案**

**为什么是 O(n)**：归并的"合并"步骤需要一块临时缓冲区存放合并结果——两个有序子数组合并时，结果最长就是 n 个元素（顶层合并时恰好为 n），再加上 O(log n) 的递归栈，峰值额外空间记为 O(n)。

```python
def merge(left, right):
    result = []  # 合并缓冲区，最终长度 = len(left) + len(right)
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


print(merge([1, 3, 5], [2, 4, 6]))
```

预期输出：`[1, 2, 3, 4, 5, 6]`。这个 `result` 就是额外空间的来源。

**能否 O(1)**：分情况——

- **数组上的原地归并**理论上可行，但实现复杂，朴素做法会让时间退化到 O(n²)，精巧做法常数大、还可能牺牲稳定性，工程上很少用；
- **链表归并排序**合并只需改指针、不需要缓冲区，辅助空间可做到 O(1)（自底向上写法连递归栈都省了）；
- 如果硬性要求数组 + O(1) 空间，通常改选**堆排序**（代价是不稳定）。

所以"O(n) 空间"是数组归并为"稳定 + 最坏 O(n log n)"付出的合理代价，Python 内置 Timsort 同样需要 O(n) 临时空间。

4. 二分搜索要求数组有序，那如果数组频繁插入/删除，二分搜索还实用吗？有什么更好的选择？

**参考答案**

**不太实用了**。二分查找本身 O(log n)，但用列表维护有序需要付出代价：`list.insert` 要移动插入点之后的所有元素，单次 O(n)。"每次插入 O(n) + 查找 O(log n)"总体被插入拖成 O(n)，二分的优势被抵消。

```python
import bisect

a = [1, 3, 5, 7]
bisect.insort(a, 4)  # 定位 O(log n)，但插入要移动元素，整体 O(n)
print(a)
```

预期输出：`[1, 3, 4, 5, 7]`。`insort` 找位置快，挪元素慢。

**仍然值得用的情况**：写少读多（如启动时加载一次的配置表），或可以"批量插入后统一排序一次"的场景。

**更好的选择**（按需求挑）：

- **平衡二叉搜索树**（AVL、红黑树）：插入/删除/查找都是 O(log n)，是"频繁增删 + 有序查找"的标准答案；Python 标准库没有内置，可用第三方 `sortedcontainers.SortedList`（需 `pip install sortedcontainers`）；
- 只关心**最大/最小值** → 堆（`heapq`）；
- 只判断**是否存在**、不需要顺序 → 字典/集合，O(1)；
- 数据量大且要持久化 → 数据库的 B 树索引。

5. 用大 O 表示法描述以下代码的时间复杂度：
```python
def mystery(n):
    for i in range(n):
        for j in range(i, n):
            print(i, j)
```

**参考答案**

**O(n²)**。外层 `i` 取 0 到 n-1；对每个 `i`，内层 `j` 从 `i` 到 n-1，执行 `n - i` 次。总执行次数为：

n + (n-1) + (n-2) + … + 1 = n(n+1)/2

忽略常数系数 1/2 和低阶项，得 O(n²)。虽然它只有完整 n×n 双重循环的"一半"，但增长量级不变。

```python
def mystery_count(n):
    count = 0
    for i in range(n):
        for j in range(i, n):
            count += 1  # 对应原题的 print(i, j)
    return count


for n in (1, 2, 3, 10, 100):
    print(n, mystery_count(n), n * (n + 1) // 2)
```

预期输出（第二列是实际执行次数，第三列是公式 n(n+1)/2，两者完全一致）：

```text
1 1 1
2 3 3
3 6 6
10 55 55
100 5050 5050
```

💡 提示：判断嵌套循环复杂度时，先写出"总次数关于 n 的求和式"，再取最高阶项——比凭感觉猜可靠得多。

---

## 📚 参考资源

- [Big O Cheat Sheet](https://www.bigocheatsheet.com/)
- [Visualgo — 排序算法可视化](https://visualgo.net/en/sorting)
- [Python Sorting HOW TO](https://docs.python.org/3/howto/sorting.html)
- [Timsort — Python 内置排序算法](https://en.wikipedia.org/wiki/Timsort)
