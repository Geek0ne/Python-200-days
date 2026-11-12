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

**参考答案**

看你需要什么特性：

- **列表（list）**：有序、可重复、可按索引访问、可变。适合「需要顺序/位置、允许重复元素、要 `lst[i]` 或切片、频繁尾部增删」的场景。
- **集合（set）**：无序、不重复、基于哈希。适合「去重、成员判断 `in`、集合运算（交并差）」，成员判断平均 `O(1)`。

性能差异是关键：list 的 `in` 是 `O(n)`（要遍历），set 的 `in` 平均 `O(1)`（哈希直达）。**大量「判断是否存在」的操作，用 set 快得多**。

- 小例子：判断 9999 是否在一万个元素里，list 可能要遍历到底，set 一步到位；去重直接 `list(set(data))`。

注意：set 的元素必须**可哈希**（不能放 list/dict）；set 无序、不能索引。

💡 提示：既要**去重又要保序**，用 `list(dict.fromkeys(data))`——字典保持插入顺序，比 `list(set(...))` 更可控。

2. **缓存策略**：`lru_cache` 的 `maxsize` 参数如何选择？太大或太小有什么问题？

**参考答案**

`maxsize` 决定缓存多少个「不同参数」的结果，本质是「内存」与「命中率」的权衡：

- **太大**：每个结果都长期留着，占内存多；若缓存了大量「只用一次」的值，纯属浪费，极端情况甚至 OOM。`maxsize=None` 表示不淘汰、全缓存，要警惕内存无限增长。
- **太小**：频繁触发 LRU 淘汰，刚算出的结果很快被挤掉，下次又得重算，**命中率低**，缓存几乎白做。`maxsize=0` 则完全不缓存。

如何选：看「参数空间大小 + 重复访问模式 + 内存预算」。参数有限且高频复用 → 设足够大（或 `None`）；参数空间巨大、只偶尔重复 → 设适中上限。最实用的办法是用 `cache_info()` 观察 `hits/misses` 命中率，据此调大或调小。

下面演示 `maxsize=2` 太小导致淘汰重算（仅用标准库，已验证）：

```python
from functools import lru_cache


@lru_cache(maxsize=2)          # 只缓存最近 2 个不同参数
def square(n):
    print(f"  计算 square({n})")   # 只有未命中时才真正计算
    return n * n


for n in [1, 2, 1, 3, 1, 2]:
    square(n)
print(square.cache_info())
```

预期输出：

```
  计算 square(1)
  计算 square(2)
  计算 square(3)
  计算 square(2)
CacheInfo(hits=2, misses=4, maxsize=2, currsize=2)
```

调用序列 `1,2,1,3,1,2`：因为只能存 2 个，算 `3` 时挤掉了 `2`，导致最后的 `2` 又要重算（`misses=4`）。若把 `maxsize` 调到 3，`2` 不会被挤掉，命中会更多——这就是「太小」的代价。

⚠️ 注意：① 参数必须**可哈希**（list/dict 不能直接当参数）；② 被缓存函数应是**纯函数**（同参数同结果、无副作用），否则缓存会返回过期或错误的结果。

3. **生成器 vs 列表**：在什么情况下必须用列表，不能用生成器？

**参考答案**

生成器是「一次性、惰性、不可索引」的流，凡是需要下面这些能力的场景，就**必须用列表**（或其他可重复访问的序列）：

- **随机访问/索引/切片**：要 `lst[i]`、`lst[a:b]`——生成器不支持下标。
- **多次遍历同一份数据**：生成器耗尽后就空了，第二次遍历拿不到东西；列表可反复遍历。
- **需要 `len()`、原地修改、排序**：`len(gen)` 报错，`sorted()` 返回的也是列表。
- **传给「要求序列/会反复读取」的 API**：某些库需要可索引、可多次迭代的数据。

生成器的优势则在「省内存、惰性、适合一次性流式处理超大/无限序列」。两者是互补，不是谁取代谁。

下面对比演示（仅用标准库，已验证）：

```python
# 生成器省内存，但「一次性、不可索引、不可重复遍历」；这些场景必须用列表
gen = (x * x for x in range(5))
lst = [x * x for x in range(5)]

print("列表可索引:", lst[2])                 # 随机访问
print("列表可重复遍历:", sum(lst), sum(lst))  # 多次遍历都在
print("列表有长度:", len(lst))

print("生成器求和:", sum(gen))                # 第一次遍历：正常
print("生成器再求和:", sum(gen))              # 已耗尽：0（不能再遍历）
try:
    gen[2]                                   # 生成器不支持索引
except TypeError as e:
    print("生成器索引报错:", e)
```

预期输出：

```
列表可索引: 4
列表可重复遍历: 30 30
列表有长度: 5
生成器求和: 30
生成器再求和: 0
生成器索引报错: 'generator' object is not subscriptable
```

列表能索引、能重复求和（都是 30）、有长度；生成器第二次求和变成 0（已耗尽），且索引直接报 `TypeError`。

💡 提示：若既想省内存又要多次遍历，可以「每次重新创建生成器」，或在内存允许时物化成列表——按内存预算权衡。

4. **numpy 适用场景**：什么时候应该用 numpy，什么时候用原生 Python 更好？

**参考答案**

numpy 的杀手锏是「**同质数值数组 + 向量化**」：它把逐元素循环下沉到 C 层、利用连续内存和 SIMD，避免 Python 解释器的逐元素开销，大数组运算能快几十倍。

**适合用 numpy**：

- 大规模数值/数组运算、向量化计算（`arr * 2`、`arr ** 2`）。
- 线性代数、统计、傅里叶变换等科学计算。
- 与 scipy/pandas/scikit-learn 等生态协作。

**适合用原生 Python**：

- 数据量小（numpy 的数组创建/转换开销反而可能比纯 Python 还慢）。
- 逻辑复杂、分支多、非数值处理（字符串、对象、字典、混合类型）。
- 需要灵活的数据结构，或不想引入额外依赖的一次性脚本。

- 小例子：对一百万个数求平方，`arr ** 2` 向量化极快；但只有 10 个数、或处理一个字符串列表，原生列表推导式更简单，甚至更快。

⚠️ 注意：numpy 需 `pip install numpy`；并且**不要在 numpy 数组上写 Python 级的逐元素 for 循环**，那样会丧失向量化优势，反而更慢——要用数组整体运算或 `np.vectorize`/ufunc。

5. **优化陷阱**：过度优化会带来什么问题？如何平衡性能和可读性？

**参考答案**

过度优化的代价：① **可读性/可维护性下降**（晦涩技巧、位运算、缓存套缓存，后人看不懂）；② **引入 bug**（缓存一致性、边界条件）；③ **浪费开发时间**在无关紧要处（过早优化）；④ **收益微乎其微**——按 Amdahl 定律，优化非热点几乎不影响整体；⑤ 徒增内存与复杂度。

平衡的做法：

- **先测量再优化**：用 cProfile 定位真正的热点，只优化瓶颈，别凭直觉到处改。
- **优先算法/数据结构级优化**：`O(n²)→O(n log n)`、list→set 这类收益大，而且通常让代码**更清晰**，是「双赢」。
- **微优化放最后**：且必须有数据证明收益，否则不做。
- **保持清晰**：确需晦涩写法时加注释说明「为什么」；设定「够用就行」的性能目标，达标即止。

- 小例子：为省几微秒把清晰的列表推导改成晦涩位运算，结果难维护、还没测出明显收益——得不偿失。

💡 提示：记住 Knuth 的名言「过早优化是万恶之源」。先保证**正确、清晰**，再按数据优化；可读性与性能冲突时优先可读，除非该处确实是被证实的瓶颈。

---

## 📖 延伸阅读

- [Python 官方文档 - functools.lru_cache](https://docs.python.org/3/library/functools.html#functools.lru_cache)
- [Python Speed Tips](https://wiki.python.org/moin/PythonSpeed/PerformanceTips)
- [High Performance Python](https://www.oreilly.com/library/view/high-performance-python/9781492055013/)
