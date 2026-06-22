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
2. 为什么说冒泡排序的 swap 操作可以通过「标记是否交换」来优化？这个优化在什么场景下收益最大？
3. 归并排序的空间复杂度为什么是 O(n)？能否改进到 O(1)？
4. 二分搜索要求数组有序，那如果数组频繁插入/删除，二分搜索还实用吗？有什么更好的选择？
5. 用大 O 表示法描述以下代码的时间复杂度：
```python
def mystery(n):
    for i in range(n):
        for j in range(i, n):
            print(i, j)
```

---

## 📚 参考资源

- [Big O Cheat Sheet](https://www.bigocheatsheet.com/)
- [Visualgo — 排序算法可视化](https://visualgo.net/en/sorting)
- [Python Sorting HOW TO](https://docs.python.org/3/howto/sorting.html)
- [Timsort — Python 内置排序算法](https://en.wikipedia.org/wiki/Timsort)
