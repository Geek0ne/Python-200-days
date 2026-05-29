# Day 006 — 列表（List）完成清单与练习题

## ✅ 今日完成清单

- [ ] 理解了列表的创建方式（字面量、构造器、推导式）
- [ ] 掌握了正/负索引机制和边界情况
- [ ] 理解了列表作为动态数组的内存模型
- [ ] 理解了深浅拷贝的区别和引用陷阱
- [ ] 掌握了切片的完整语法（`[start:stop:step]`）
- [ ] 学会了用切片进行赋值、插入、删除
- [ ] 掌握了所有常用列表方法
  - [ ] `append()` / `extend()` / `insert()`
  - [ ] `pop()` / `remove()` / `clear()`
  - [ ] `index()` / `count()` / `in`
  - [ ] `sort()` / `sorted()` / `reverse()`
  - [ ] `len()` / `min()` / `max()` / `sum()`
- [ ] 掌握了列表推导式的语法和用法
- [ ] 学会了 `enumerate` 和 `zip` 的使用
- [ ] 完成了待办事项管理器实战
- [ ] 阅读了内存原理和底层实现图解

---

## 📝 练习题

### 练习 1：列表反转

不使用 `reverse()` 方法也不使用 `[::-1]`，手动实现一个函数来反转列表。

```python
def reverse_list(lst):
    """
    手动反转列表（不修改原列表）
    返回一个新的反转后的列表
    """
    # 在这里写你的代码
    pass

# 测试
print(reverse_list([1, 2, 3, 4, 5]))  # 应输出 [5, 4, 3, 2, 1]
print(reverse_list(["a", "b", "c"]))  # 应输出 ["c", "b", "a"]
print(reverse_list([]))               # 应输出 []
```

### 练习 2：矩阵转置

将一个 3×3 矩阵（嵌套列表）进行转置（行变列）。

```python
def transpose(matrix):
    """
    矩阵转置
    例如: [[1,2,3], [4,5,6], [7,8,9]] → [[1,4,7], [2,5,8], [3,6,9]]
    """
    # 在这里写你的代码（尝试用列表推导式一行搞定）
    pass

matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
]
result = transpose(matrix)
print(result)  # 应输出 [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
```

### 练习 3：找出列表中的重复元素

```python
def find_duplicates(lst):
    """
    找出列表中所有出现次数大于 1 的元素
    返回一个去重后的列表（每个重复元素只出现一次）
    """
    # 在这里写你的代码
    pass

print(find_duplicates([1, 2, 3, 2, 4, 3, 5, 1]))  # 应输出 [1, 2, 3]（顺序不限）
print(find_duplicates(["a", "b", "c"]))            # 应输出 []
print(find_duplicates([1, 1, 1, 1]))               # 应输出 [1]
```

### 练习 4：分块列表

```python
def chunk_list(lst, chunk_size):
    """
    将列表分块，每块包含 chunk_size 个元素
    例如: chunk_list([1,2,3,4,5,6,7], 3) → [[1,2,3], [4,5,6], [7]]
    """
    # 在这里写你的代码
    pass

print(chunk_list([1, 2, 3, 4, 5, 6, 7], 3))
# 应输出 [[1, 2, 3], [4, 5, 6], [7]]

print(chunk_list([1, 2, 3, 4, 5], 2))
# 应输出 [[1, 2], [3, 4], [5]]

print(chunk_list([1, 2, 3], 5))
# 应输出 [[1, 2, 3]]
```

### 练习 5：两个列表的交替合并

```python
def merge_alternating(list1, list2):
    """
    将两个列表交替合并
    例如: merge_alternating([1,2,3], ['a','b','c']) → [1,'a',2,'b',3,'c']
    
    如果长度不同，多余的元素放在末尾
    例如: merge_alternating([1,2], ['a','b','c','d']) → [1,'a',2,'b','c','d']
    """
    # 在这里写你的代码
    pass

print(merge_alternating([1, 2, 3], ['a', 'b', 'c']))
# 应输出 [1, 'a', 2, 'b', 3, 'c']

print(merge_alternating([1, 2], ['a', 'b', 'c', 'd']))
# 应输出 [1, 'a', 2, 'b', 'c', 'd']

print(merge_alternating([], [1, 2, 3]))
# 应输出 [1, 2, 3]
```

---

## 💡 参考答案提示

有问题时先独立思考，实在做不出来再参考：

<details>
<summary>练习 1 提示</summary>

可以用 `pop()` 从原列表尾部取元素，用 `append()` 添加到新列表。或者用循环从后往前遍历索引。

</details>

<details>
<summary>练习 2 提示</summary>

使用列表推导式嵌套：`[[row[i] for row in matrix] for i in range(len(matrix[0]))]`

或者用 `zip(*matrix)` 加 list 转换。

</details>

<details>
<summary>练习 3 提示</summary>

使用 `count()` 方法 + 列表推导式 + `set()` 去重。

</details>

<details>
<summary>练习 4 提示</summary>

用 range 的步长参数：`range(0, len(lst), chunk_size)`，然后每个切片 `lst[i:i+chunk_size]`。

</details>

<details>
<summary>练习 5 提示</summary>

先找最短长度，循环交替添加。然后 `extend()` 将多余部分追加到末尾。

</details>
