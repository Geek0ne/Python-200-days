# Day 029 — 算法入门：完成清单与练习题

## ✅ 完成清单

### 概念理解
- [ ] 理解大 O 表示法的含义与常见时间复杂度
- [ ] 理解冒泡排序的相邻交换原理
- [ ] 理解选择排序的最小值选择原理
- [ ] 理解插入排序的局部有序原理
- [ ] 理解快速排序的分治思想与分割过程
- [ ] 理解归并排序的分治思想与合并过程
- [ ] 理解线性搜索与二分搜索的区别
- [ ] 了解排序算法的稳定性含义

### Python 实现
- [ ] 能够实现冒泡排序（含 early stop 优化）
- [ ] 能够实现选择排序
- [ ] 能够实现插入排序
- [ ] 能够实现快速排序（简洁版 + 原地版）
- [ ] 能够实现归并排序
- [ ] 能够实现线性搜索
- [ ] 能够实现二分搜索（迭代版 + 递归版）

### 代码实践
- [ ] 运行 `01-basic-usage.py` 理解各算法基础实现
- [ ] 运行 `02-advanced-usage.py` 掌握排序稳定性与优化
- [ ] 运行 `03-practical.py` 完成实战案例
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 练习 1：冒泡排序的 Early Stop 优化

```python
"""
实现一个冒泡排序，并统计比较次数和交换次数。
使用 swapped 标志进行优化，当一轮没有交换时提前终止。

要求：返回 (排序后数组, 比较次数, 交换次数)
"""
def bubble_sort_count(arr):
    # 你的代码
    pass

# 测试
print(bubble_sort_count([5, 1, 4, 2, 8]))
# → ([1, 2, 4, 5, 8], 10, 3)  （示例值）

# 测试近乎有序数组
print(bubble_sort_count([1, 2, 3, 5, 4]))
# 预期：比较次数很少
```

### 练习 2：实现通用排序器

```python
"""
实现一个函数 select_sorter，根据数据特性选择最优排序算法：
- 数据量 < 50 → 插入排序
- 数据量大且近乎有序 → 插入排序
- 数据量大且随机 → 快速排序
- 需要稳定排序 → 归并排序
"""
def select_sorter(arr, need_stable=False):
    # 你的代码
    pass

# 测试
data1 = [3, 1, 4, 1, 5, 9, 2, 6, 5]
print(select_sorter(data1))  # 自动选择算法

data2 = [1, 2, 3, 4, 6, 5, 7, 8]  # 近乎有序
print(select_sorter(data2, need_stable=True))
```

### 练习 3：数组中找两个数和为 target

```python
"""
给定一个升序排列的整数数组和一个目标值 target，
找出数组中两个数之和等于 target 的索引（1-indexed）。

要求：不使用嵌套循环，利用二分搜索或双指针实现 O(n) 时间复杂度
"""
def two_sum_sorted(numbers, target):
    # 你的代码（双指针）
    pass

# 测试
print(two_sum_sorted([2, 7, 11, 15], 9))     # → [1, 2]
print(two_sum_sorted([2, 3, 4], 6))           # → [1, 3]
print(two_sum_sorted([-1, 0], -1))            # → [1, 2]
```

### 练习 4：K 大元素（最小堆）

```python
"""
使用最小堆（heapq）找到数组中第 K 大的元素。
要求：不直接对整个数组排序
"""
import heapq

def find_kth_largest(nums, k):
    # 你的代码
    pass

# 测试
print(find_kth_largest([3, 2, 1, 5, 6, 4], 2))  # → 5
print(find_kth_largest([3, 2, 3, 1, 2, 4, 5, 5, 6], 4))  # → 4

# 提示：维护一个大小为 k 的最小堆
```

### 练习 5：排序算法可视化

```python
"""
写一个函数 print_sort_process，在终端打印排序过程。
每次交换后打印当前数组状态，并用箭头标记正在操作的相邻元素。

例如冒泡排序过程中的一帧：
  [3, 5, 8, 6, 4]
     ↑  ↑
     L  R
"""
def bubble_sort_print(arr):
    # 你的代码
    pass

# 测试
bubble_sort_print([5, 3, 8, 6, 4])
# 期望输出：每一步显示数组 + 箭头标记当前比较的相邻元素
```

---

## 📊 自评表

| 技能 | 初学者 | 理解 | 掌握 | 熟练 |
|------|--------|------|------|------|
| 大 O 复杂度分析 | ☐ | ☐ | ☐ | ☐ |
| 冒泡排序实现 | ☐ | ☐ | ☐ | ☐ |
| 选择排序实现 | ☐ | ☐ | ☐ | ☐ |
| 插入排序实现 | ☐ | ☐ | ☐ | ☐ |
| 快速排序实现 | ☐ | ☐ | ☐ | ☐ |
| 归并排序实现 | ☐ | ☐ | ☐ | ☐ |
| 线性搜索 | ☐ | ☐ | ☐ | ☐ |
| 二分搜索 | ☐ | ☐ | ☐ | ☐ |
| 排序稳定性理解 | ☐ | ☐ | ☐ | ☐ |

---

## 🔗 参考资源

- [Big O Cheatsheet](https://www.bigocheatsheet.com/)
- [Visualgo 排序动画](https://visualgo.net/en/sorting)
- [Timsort — Wikipedia](https://en.wikipedia.org/wiki/Timsort)
- [排序算法可视化 (Toptal)](https://www.toptal.com/developers/sorting-algorithms)
- [Python bisect 官方文档](https://docs.python.org/3/library/bisect.html)
