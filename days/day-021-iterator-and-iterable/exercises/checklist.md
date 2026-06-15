# Day 021 — 迭代器与可迭代对象 练习题与检查表

## ✅ 完成检查表

### 概念理解
- [ ] 理解迭代器协议的构成（`__iter__` + `__next__`）
- [ ] 能区分可迭代对象（Iterable）和迭代器（Iterator）
- [ ] 能描述 `for` 循环的底层执行流程
- [ ] 理解惰性求值的概念和优势
- [ ] 知道 `__getitem__` 回退机制
- [ ] 理解迭代器只能遍历一次的原因

### 代码实践
- [ ] 能徒手实现 `__iter__` 和 `__next__`
- [ ] 能创建既支持 `for` 循环又支持 `next()` 的自定义类
- [ ] 能区分"可重复遍历"和"单次遍历"的设计模式
- [ ] 会使用 `itertools.count`, `cycle`, `chain`
- [ ] 会使用 `itertools.islice`, `zip_longest`
- [ ] 会使用 `itertools.groupby`, `product`
- [ ] 能判断一个对象是否是 Iterable / Iterator

### 练习完成
- [ ] 基础练习（1-4 题）
- [ ] 进阶练习（5-8 题）
- [ ] 挑战练习（9-10 题）

---

## 📝 基础练习

### 练习 1：平方数迭代器

实现一个 `SquareIterator`，生成从 1 开始的平方数序列（1, 4, 9, 16, ...），可指定上限。

```python
class SquareIterator:
    """平方数迭代器"""
    def __init__(self, max_value=None):
        self.max_value = max_value
        self.n = 1

    def __iter__(self):
        return self

    def __next__(self):
        # TODO: 如果超过 max_value，抛出 StopIteration
        #       否则返回 self.n ** 2 并递增 n
        pass

# 测试
squares = SquareIterator(max_value=50)
print(list(squares))  # 应该输出 [1, 4, 9, 16, 25, 36, 49]
```

<details>
<summary>提示</summary>
检查 n^2 是否超过 max_value。
</details>

### 练习 2：倒序遍历迭代器

实现一个 `ReverseIterator`，接收一个列表，从后往前遍历。

```python
class ReverseIterator:
    """从后往前遍历的迭代器"""
    def __init__(self, data):
        self.data = data
        self.index = len(data) - 1

    def __iter__(self):
        return self

    def __next__(self):
        # TODO: 从后往前遍历
        pass

# 测试
it = ReverseIterator([1, 2, 3, 4, 5])
print(list(it))  # 应该输出 [5, 4, 3, 2, 1]
```

### 练习 3：步进迭代器

实现一个 `StepIterator`，支持跳步（step）遍历。

```python
class StepIterator:
    """步进迭代器"""
    def __init__(self, data, step=1):
        self.data = data
        self.step = step
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        # TODO: 每次返回 data[index]，然后 index += step
        pass

# 测试
it = StepIterator([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], step=3)
print(list(it))  # 应该输出 [1, 4, 7, 10]
```

### 练习 4：用 iter() 实现 for 循环

不用 `for` 关键字，只用 `iter()` 和 `next()` 遍历一个列表。

```python
def custom_for_loop(iterable, func):
    """用 iter 和 next 模拟 for 循环

    参数:
        iterable: 可迭代对象
        func: 对每个元素执行的函数
    """
    # TODO: 获取迭代器，调用 next() 直到 StopIteration
    pass

# 测试
custom_for_loop([1, 2, 3], print)  # 应该输出 1, 2, 3（每行一个）
```

---

## 🔥 进阶练习

### 练习 5：可重复遍历的迭代器

修改 `Counter` 类，使其支持重复遍历。

```python
class ReusableCounter:
    """可重复遍历的计数器"""
    def __init__(self, start=0, end=10):
        self.start = start
        self.end = end

    def __iter__(self):
        # TODO: 每次都返回一个新的迭代器
        pass

# 测试
c = ReusableCounter(0, 5)
print(list(c))  # [0, 1, 2, 3, 4]
print(list(c))  # [0, 1, 2, 3, 4] (可重复)
```

### 练习 6：合并多个迭代器

编写一个函数 `merge_iterators(*iters)`，将多个迭代器交错合并。

```python
def merge_iterators(*iters):
    """交错合并多个迭代器

    输入: iters = [iter([1,2,3]), iter(['a','b'])]
    输出: 1, 'a', 2, 'b', 3
    """
    # TODO: 交错取值，当全部耗尽时停止
    pass

# 测试
i1 = iter([1, 2, 3])
i2 = iter(['a', 'b'])
i3 = iter(['x', 'y', 'z'])
print(list(merge_iterators(i1, i2, i3)))
# 应该输出: [1, 'a', 'x', 2, 'b', 'y', 3, 'z']
```

### 练习 7：缓存迭代器

实现一个 `CachedIterator`，将迭代器的结果缓存起来，可以多次遍历。

```python
class CachedIterator:
    """将迭代器的结果缓存，支持重复遍历"""
    def __init__(self, iterator):
        self.iterator = iterator
        self.cache = []
        self.exhausted = False

    def __iter__(self):
        return CachedIteratorHelper(self)

class CachedIteratorHelper:
    def __init__(self, cached_iter):
        self.cached_iter = cached_iter
        self.index = 0

    def __next__(self):
        # TODO: 如果 index < len(cache)，从 cache 返回
        #       否则从原始迭代器获取，加入 cache 再返回
        pass

# 测试
original = iter([1, 2, 3, 4, 5])
cached = CachedIterator(original)
print(list(cached))  # [1, 2, 3, 4, 5]
print(list(cached))  # [1, 2, 3, 4, 5] (来自缓存)
```

### 练习 8：peekable 迭代器

实现一个 `PeekableIterator`，可以"偷看"下一个值而不消耗它。

```python
class PeekableIterator:
    """支持 peek() 的迭代器"""
    def __init__(self, iterator):
        self.iterator = iterator
        self._next_item = None
        self._has_next = False
        self._advance()

    def _advance(self):
        """预取下一个值"""
        try:
            self._next_item = next(self.iterator)
            self._has_next = True
        except StopIteration:
            self._has_next = False

    def __iter__(self):
        return self

    def __next__(self):
        """返回当前值，并预取下一个"""
        if not self._has_next:
            raise StopIteration
        current = self._next_item
        self._advance()
        return current

    def peek(self):
        """偷看下一个值，不消耗"""
        return self._next_item

    def has_next(self):
        """是否还有下一个元素"""
        return self._has_next

# 测试
p = PeekableIterator(iter([1, 2, 3]))
print(p.peek())    # 1
print(next(p))     # 1
print(p.peek())    # 2
print(p.has_next())  # True
print(next(p))     # 2
print(next(p))     # 3
print(p.has_next())  # False
```

---

## 🏆 挑战练习

### 练习 9：无限迭代器 + islice 应用

用 `itertools` 解决以下问题：

1. 生成 1 到 100 之间，所有能被 7 整除的数字
2. 生成第一个大于 1000 的斐波那契数
3. 将 3 个列表 `[1,2,3]`, `[4,5,6]`, `[7,8]` 展平为一个迭代器

```python
import itertools

def divisible_by_7():
    """返回 1-100 之间能被 7 整除的数（用迭代器方式）"""
    pass

def first_fib_above_1000():
    """返回第一个大于 1000 的斐波那契数"""
    pass

def flatten_lists(*lists):
    """将多个列表展平为一个迭代器"""
    pass
```

### 练习 10：迭代器实现分页器

实现一个 `Paginator` 类，接受数据列表和每页大小，返回页码和数据。

```python
class Paginator:
    """分页迭代器

    data: 总数据列表
    per_page: 每页元素数
    """

    def __init__(self, data, per_page=10):
        self.data = data
        self.per_page = per_page
        self._page = 0

    def __iter__(self):
        return self

    def __next__(self):
        """返回 (page_num, page_data) 元组

        每页数据是 data 的一个切片。
        """
        # TODO: 实现分页逻辑
        pass

# 测试
data = list(range(1, 21))  # 1..20
paginator = Paginator(data, per_page=6)
for page_num, page_data in paginator:
    print(f"第 {page_num} 页: {page_data}")

# 预期输出:
# 第 1 页: [1, 2, 3, 4, 5, 6]
# 第 2 页: [7, 8, 9, 10, 11, 12]
# 第 3 页: [13, 14, 15, 16, 17, 18]
# 第 4 页: [19, 20]
```

---

## 💡 思考题

1. 可迭代对象和迭代器是同一个对象吗？什么时候应该这样做？
2. 为什么 `list` 是可迭代的但不是迭代器？为什么 `file` 既是可迭代的又是迭代器？
3. 迭代器的惰性求值在什么场景下会带来性能问题？
4. Python 3 的 `range()` 返回的是什么？它和迭代器有什么区别？
5. 如果你在设计一个 API 返回大量数据，你会用列表还是迭代器？为什么？
6. 用迭代器实现"读取文件最后 N 行"应该怎么做？
7. `itertools.tee` 的原理是什么？它的内存消耗如何？
8. 为什么 `map()` 和 `filter()` 返回的不是列表？

## 📊 自我评估

| 技能 | 😰 不熟练 | 🤔 基本掌握 | 💪 熟练 |
|------|----------|------------|--------|
| 理解迭代器协议 | | | |
| 实现自定义迭代器 | | | |
| for 循环底层原理 | | | |
| 惰性求值理解 | | | |
| Iterable/Iterator 区分 | | | |
| itertools 基础使用 | | | |
| itertools 高级应用 | | | |
| 迭代器陷阱识别 | | | |
| 迭代器内存优势 | | | |

---

## 🧪 挑战题解答思路

### 练习 5：可重复遍历的实现思路

```python
class ReusableCounter:
    def __init__(self, start=0, end=10):
        self.start = start
        self.end = end

    def __iter__(self):
        # 关键是每次返回一个新的迭代器对象
        return ReusableCounterIterator(self.start, self.end)

class ReusableCounterIterator:
    def __init__(self, start, end):
        self.current = start
        self.end = end

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.end:
            raise StopIteration
        val = self.current
        self.current += 1
        return val
```

### 练习 6：交错合并迭代器

```python
def merge_iterators(*iters):
    iters = list(iters)
    while iters:
        alive = []
        for it in iters:
            try:
                yield next(it)
                alive.append(it)
            except StopIteration:
                pass
        iters = alive
```
