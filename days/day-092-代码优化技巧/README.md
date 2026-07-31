# Day 092 — 代码优化技巧

> ⚡ Phase 7 进阶与性能优化 | 代码优化技巧

## 📚 学习目标

今天我们将深入学习 Python 代码优化的核心技巧，包括数据结构选择、循环优化、缓存策略等，将慢代码提速 10 倍以上。

---

## 一、优化思维框架

### 1.1 优化原则

```
优化金字塔:

        ┌───────┐
        │ 算法  │  ← 最重要: O(n²) → O(n log n)
        ├───────┤
        │数据结构│  ← 关键: list → set/dict
        ├───────┤
        │ 循环  │  ← 减少迭代次数
        ├───────┤
        │ 缓存  │  ← 避免重复计算
        ├───────┤
        │ 细节  │  ← 微优化(最后考虑)
        └───────┘
```

### 1.2 优化检查清单

1. **算法复杂度**：是否可以用更好的算法？
2. **数据结构**：是否选择了最合适的数据结构？
3. **遍历次数**：能否减少循环次数？
4. **重复计算**：能否缓存结果？
5. **内存使用**：是否有不必要的内存分配？
6. **I/O 操作**：能否减少文件/网络操作？

---

## 二、数据结构选择优化

### 2.1 查找操作

```python
# ❌ 列表查找: O(n)
my_list = [1, 2, 3, ..., 10000]
if 9999 in my_list:  # 遍历整个列表!
    pass

# ✅ 集合查找: O(1)
my_set = set(my_list)
if 9999 in my_set:  # 哈希查找!
    pass

# 性能对比:
# 列表查找 10000 个元素: ~1ms
# 集合查找 10000 个元素: ~0.001ms
```

### 2.2 频繁插入/删除

```python
# ❌ 列表头部插入: O(n)
my_list.insert(0, item)  # 所有元素都要移动!

# ✅ 双端队列: O(1)
from collections import deque
my_deque = deque(my_list)
my_deque.appendleft(item)  # 头部插入 O(1)

# ✅ 链表模拟 (如果需要频繁中间插入)
from collections import OrderedDict
# 或使用第三方库如 linkedlist
```

### 2.3 计数与分组

```python
# ❌ 手动计数
counts = {}
for item in data:
    if item in counts:
        counts[item] += 1
    else:
        counts[item] = 1

# ✅ Counter
from collections import Counter
counts = Counter(data)

# ✅ defaultdict
from collections import defaultdict
counts = defaultdict(int)
for item in data:
    counts[item] += 1
```

---

## 三、循环优化

### 3.1 减少循环次数

```python
# ❌ 多次遍历
max_val = max(data)
min_val = min(data)
avg_val = sum(data) / len(data)

# ✅ 单次遍历
max_val = float("-inf")
min_val = float("inf")
total = 0
for item in data:
    if item > max_val:
        max_val = item
    if item < min_val:
        min_val = item
    total += item
avg_val = total / len(data)
```

### 3.2 循环展开

```python
# ❌ 普通循环
result = []
for i in range(0, len(data), 2):
    result.append(data[i] + data[i+1])

# ✅ 循环展开 (减少循环开销)
result = []
for i in range(0, len(data), 4):
    result.append(data[i] + data[i+1])
    if i + 2 < len(data):
        result.append(data[i+2] + data[i+3])
```

### 3.3 使用内置函数

```python
# ❌ 手动实现
result = []
for item in data:
    result.append(item * 2)

# ✅ map 函数
result = list(map(lambda x: x * 2, data))

# ✅ 列表推导 (通常最快)
result = [x * 2 for x in data]

# ✅ numpy 向量化 (数值计算)
import numpy as np
arr = np.array(data)
result = arr * 2
```

---

## 四、缓存策略

### 4.1 函数缓存

```python
from functools import lru_cache

# ❌ 每次都重新计算
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# ✅ 使用 lru_cache
@lru_cache(maxsize=128)
def fibonacci_cached(n):
    if n < 2:
        return n
    return fibonacci_cached(n-1) + fibonacci_cached(n-2)

# 性能对比:
# fibonacci(30): ~300ms
# fibonacci_cached(30): ~0.001ms
```

### 4.2 结果缓存

```python
# ❌ 重复计算
def process_data(data):
    # 每次都重新排序!
    sorted_data = sorted(data)
    return sorted_data[:10]

# ✅ 缓存结果
class DataProcessor:
    def __init__(self):
        self._cache = {}
    
    def get_top10(self, data_key, data):
        if data_key not in self._cache:
            self._cache[data_key] = sorted(data)[:10]
        return self._cache[data_key]
```

### 4.3 延迟加载

```python
# ❌ 提前加载所有数据
class DataLoader:
    def __init__(self):
        self.data = self._load_all()  # 启动时加载所有!
    
    def _load_all(self):
        return [self._load_item(i) for i in range(10000)]

# ✅ 延迟加载
class DataLoader:
    def __init__(self):
        self._data = None
    
    @property
    def data(self):
        if self._data is None:
            self._data = self._load_all()
        return self._data
```

---

## 五、字符串优化

### 5.1 字符串拼接

```python
# ❌ 字符串拼接 (每次创建新字符串)
result = ""
for i in range(10000):
    result += str(i)  # O(n²) 复杂度!

# ✅ 使用 join
parts = [str(i) for i in range(10000)]
result = "".join(parts)  # O(n) 复杂度

# ✅ 使用 io.StringIO
from io import StringIO
buffer = StringIO()
for i in range(10000):
    buffer.write(str(i))
result = buffer.getvalue()
```

### 5.2 正则表达式预编译

```python
import re

# ❌ 每次都编译
for text in texts:
    match = re.search(r'\d+', text)  # 每次都编译!

# ✅ 预编译
pattern = re.compile(r'\d+')
for text in texts:
    match = pattern.search(text)  # 只编译一次
```

---

## 六、I/O 优化

### 6.1 文件读取

```python
# ❌ 逐行读取
with open('file.txt') as f:
    for line in f:  # 每次都进行 I/O
        process(line)

# ✅ 批量读取
with open('file.txt') as f:
    lines = f.readlines()  # 一次读取全部
    for line in lines:
        process(line)

# ✅ 使用 mmap (大文件)
import mmap
with open('file.txt', 'r+') as f:
    mm = mmap.mmap(f.fileno(), 0)
    # 直接操作内存
```

### 6.2 数据库查询

```python
# ❌ 逐条查询
for user_id in user_ids:
    user = db.query(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ 批量查询
users = db.query(
    "SELECT * FROM users WHERE id IN (%s)",
    user_ids
)

# ✅ 使用 ORM 批量操作
users = User.query.filter(User.id.in_(user_ids)).all()
```

---

## 七、内存优化

### 7.1 使用生成器

```python
# ❌ 列表占用大量内存
data = [i ** 2 for i in range(1000000)]  # ~8MB

# ✅ 生成器节省内存
data = (i ** 2 for i in range(1000000))  # ~100B

# ✅ 使用 yield
def process_large_file(filename):
    with open(filename) as f:
        for line in f:
            yield process(line)
```

### 7.2 使用 slots

```python
# ❌ 普通类 (每个实例有 __dict__)
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

# ✅ 使用 __slots__
class Point:
    __slots__ = ['x', 'y']
    
    def __init__(self, x, y):
        self.x = x
        self.y = y

# 节省 ~40% 内存
```

### 7.3 使用数组

```python
# ❌ 列表存储数字
data = [1, 2, 3, ..., 1000000]  # 每个元素是 PyObject

# ✅ 使用 array 模块
from array import array
data = array('i', range(1000000))  # 紧凑存储

# ✅ 使用 numpy
import numpy as np
data = np.arange(1000000)  # 最紧凑
```

---

## 八、实战：将慢代码提速 10 倍

### 8.1 原始慢代码

```python
def slow_function(data):
    """原始慢代码"""
    result = []
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100:
                # 每次都遍历检查重复!
                if transformed not in result:
                    result.append(transformed)
    return sorted(result)
```

### 8.2 优化后的代码

```python
def fast_function(data):
    """优化后: 10x 提速"""
    # 1. 使用集合去重
    seen = set()
    result = []
    
    # 2. 单次遍历
    for item in data:
        if item % 2 == 0:
            transformed = item ** 2 + item * 3
            if transformed > 100 and transformed not in seen:
                result.append(transformed)
                seen.add(transformed)
    
    # 3. 使用内置排序
    return sorted(result)
```

---

## 九、思考题

1. **列表 vs 集合**：什么时候应该用列表，什么时候应该用集合？

2. **缓存策略**：`lru_cache` 的 `maxsize` 参数如何选择？太大或太小有什么问题？

3. **生成器 vs 列表**：在什么情况下必须用列表，不能用生成器？

4. **numpy 适用场景**：什么时候应该用 numpy，什么时候用原生 Python 更好？

5. **优化陷阱**：过度优化会带来什么问题？如何平衡性能和可读性？

---

## 📖 延伸阅读

- [Python 官方文档 - functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [Python Speed Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [High Performance Python](https://www.oreilly.com/library/view/high-performance-python/9781492055013/)
