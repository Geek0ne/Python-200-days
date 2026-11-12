# Day 091 — 性能剖析

> 📊 Phase 7 进阶与性能优化 | 性能剖析第一天

## 📚 学习目标

今天我们将掌握 Python 代码性能剖析的核心工具和方法，学会定位性能瓶颈，为后续的优化工作打下基础。

---

## 一、为什么需要性能剖析？

### 1.1 性能优化的误区

```
❌ 常见错误: 凭直觉优化
  → "我觉得这个循环很慢" → 优化了错误的地方

✅ 正确做法: 先测量，再优化
  → 用工具找到真正的瓶颈 → 精准优化
```

### 1.2 性能剖析的核心价值

1. **定位瓶颈**：找到代码中真正耗时的部分
2. **量化改进**：用数据证明优化效果
3. **避免过早优化**：不浪费时间在不重要的地方
4. **监控回归**：确保优化没有引入新问题

---

## 二、cProfile — 函数级性能剖析

### 2.1 基本使用

```python
import cProfile

def my_function():
    # 你的代码
    pass

# 方法1: 直接运行剖析
cProfile.run('my_function()')

# 方法2: 按函数统计
profiler = cProfile.Profile()
profiler.enable()
my_function()
profiler.disable()
profiler.print_stats(sort='cumtime')
```

### 2.2 输出解读

```
         4 function calls in 0.002 seconds

   Ordered by: standard name

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.001    0.001    0.002    0.002 main.py:5(my_function)
        2    0.001    0.001    0.001    0.001 main.py:10(helper)
        1    0.000    0.000    0.000    0.000 {method 'append' of 'list' objects}
```

**关键列说明：**
- `ncalls`：调用次数
- `tottime`：函数自身耗时（不含子函数）
- `cumtime`：累计耗时（含子函数）
- `percall`：每次调用平均耗时

### 2.3 常用参数

```python
# 按累计时间排序
profiler.print_stats(sort='cumtime')

# 按调用次数排序
profiler.print_stats(sort='ncalls')

# 按自身时间排序
profiler.print_stats(sort='tottime')

# 限制输出行数
profiler.print_stats(20)  # 只显示前20行
```

---

## 三、line_profiler — 行级性能剖析

### 3.1 安装与基本使用

```bash
pip install line_profiler
```

```python
# 使用装饰器
@profile  # 注意: 这个装饰器由 line_profiler 提供
def my_function():
    a = [1, 2, 3]
    b = [x * 2 for x in a]
    return sum(b)

# 运行: kernprof -l -v my_script.py
```

### 3.2 输出解读

```
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
     3                                           def my_function():
     4         1          0.1      0.1      1.2      a = [1, 2, 3]
     5         1        200.3    200.3     78.5      b = [x * 2 for x in a]
     6         1         55.0     55.0     21.5      return sum(b)
```

**关键列说明：**
- `Hits`：该行执行次数
- `Time`：该行总耗时（微秒）
- `Per Hit`：每次执行平均耗时
- `% Time`：占总时间百分比

### 3.3 在代码中动态使用

```python
from line_profiler import LineProfiler

def my_function():
    a = [1, 2, 3]
    b = [x * 2 for x in a]
    return sum(b)

lp = LineProfiler()
lp.add_function(my_function)
lp_wrapper = lp(my_function)
lp_wrapper()
lp.print_stats()
```

---

## 四、memory_profiler — 内存剖析

### 4.1 安装与使用

```bash
pip install memory_profiler
```

```python
from memory_profiler import profile

@profile
def my_function():
    a = [i for i in range(10000)]  # ~400KB
    b = [i ** 2 for i in range(10000)]  # ~400KB
    return a, b
```

### 4.2 输出解读

```
Line #    Mem usage    Increment   Line Contents
================================================
     3     38.5 MiB     38.5 MiB   @profile
     4                             def my_function():
     5     38.5 MiB      0.0 MiB       a = [i for i in range(10000)]
     6     38.5 MiB      0.0 MiB       b = [i ** 2 for i in range(10000)]
     7     38.5 MiB      0.0 MiB       return a, b
```

### 4.3 内存泄漏检测

```python
from memory_profiler import profile

@profile
def leaky_function():
    # 每次调用都会泄漏内存
    global my_list
    my_list = []
    my_list.extend(range(10000))
    return len(my_list)

# 多次调用观察内存增长
for i in range(10):
    leaky_function()
```

---

## 五、时间测量工具

### 5.1 timeit — 精确计时

```python
import timeit

# 基本用法
time = timeit.timeit('sum(range(1000))', number=10000)
print(f"耗时: {time:.4f}秒")

# 测量函数
def my_func():
    return sum(range(1000))

time = timeit.timeit(my_func, number=10000)
print(f"耗时: {time:.4f}秒")

# 对比两种方法
time1 = timeit.timeit('[x**2 for x in range(1000)]', number=10000)
time2 = timeit.timeit('list(map(lambda x: x**2, range(1000)))', number=10000)
print(f"列表推导: {time1:.4f}秒")
print(f"map函数: {time2:.4f}秒")
```

### 5.2 上下文管理器计时

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name="操作"):
    start = time.perf_counter()
    yield
    end = time.perf_counter()
    print(f"⏱️ {name}: {end - start:.6f}秒")

# 使用
with timer("排序"):
    data = sorted(range(100000), reverse=True)

with timer("列表推导"):
    data = [x ** 2 for x in range(10000)]
```

---

## 六、性能剖析最佳实践

### 6.1 剖析流程

```
┌─────────────────────────────────────┐
│         性能剖析流程                 │
├─────────────────────────────────────┤
│                                     │
│  1. 确定目标                        │
│     └→ 优化什么？为什么？           │
│                                     │
│  2. 基准测试                        │
│     └→ 当前性能如何？               │
│                                     │
│  3. 剖析代码                        │
│     └→ cProfile → 找到热点函数     │
│     └→ line_profiler → 找到热点行  │
│                                     │
│  4. 分析结果                        │
│     └→ 哪些函数/行耗时最多？       │
│     └→ 为什么慢？                   │
│                                     │
│  5. 制定优化方案                    │
│     └→ 算法优化？数据结构？缓存？  │
│                                     │
│  6. 实施优化                        │
│     └→ 一次只改一个地方            │
│                                     │
│  7. 验证效果                        │
│     └→ 对比优化前后性能            │
│                                     │
└─────────────────────────────────────┘
```

### 6.2 常见性能陷阱

```python
# ❌ 陷阱1: 在循环中重复创建对象
for i in range(10000):
    regex = re.compile(r'\d+')  # 每次都编译!
    regex.search(str(i))

# ✅ 正确: 预编译正则
regex = re.compile(r'\d+')
for i in range(10000):
    regex.search(str(i))


# ❌ 陷阱2: 字符串拼接
result = ""
for i in range(10000):
    result += str(i)  # 每次都创建新字符串!

# ✅ 正确: 使用 join
parts = [str(i) for i in range(10000)]
result = "".join(parts)


# ❌ 陷阱3: 在循环中查找
my_list = [1, 2, 3, ..., 10000]
for i in range(10000):
    if i in my_list:  # O(n) 查找!
        pass

# ✅ 正确: 使用集合
my_set = set(my_list)
for i in range(10000):
    if i in my_set:  # O(1) 查找!
        pass
```

### 6.3 性能对比模板

```python
import timeit
from functools import wraps

def benchmark(func):
    """性能测试装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        times = timeit.repeat(
            lambda: func(*args, **kwargs),
            repeat=5,
            number=1000
        )
        avg_time = sum(times) / len(times)
        print(f"📊 {func.__name__}: {avg_time*1000:.3f}ms (平均)")
        return func(*args, **kwargs)
    return wrapper

@benchmark
def slow_function():
    return sorted(range(10000), reverse=True)

@benchmark
def fast_function():
    return list(range(9999, -1, -1))
```

---

## 七、实战：性能剖析完整示例

### 7.1 剖析一个实际函数

```python
import cProfile
import pstats
from io import StringIO

def process_data(data):
    """需要优化的函数"""
    result = []
    for item in data:
        # 过滤
        if item % 2 == 0:
            # 转换
            transformed = item ** 2 + item * 3
            # 验证
            if transformed > 100:
                result.append(transformed)
    return result

# 生成测试数据
test_data = list(range(100000))

# 剖析
profiler = cProfile.Profile()
profiler.enable()
result = process_data(test_data)
profiler.disable()

# 分析结果
s = StringIO()
ps = pstats.Stats(profiler, stream=s)
ps.sort_stats('cumulative')
ps.print_stats(20)
print(s.getvalue())
```

---

## 八、思考题

1. **cProfile vs line_profiler**：什么时候用 cProfile，什么时候用 line_profiler？

**参考答案**

两者是「由粗到细」的关系，粒度不同：

- **cProfile（函数级）**：标准库自带、开销小，统计每个函数的调用次数、自身耗时 `tottime`、累计耗时 `cumtime`。适合**第一步定位「哪个函数是热点」**，做整体概览，甚至在生产环境粗筛。
- **line_profiler（行级）**：第三方库（`pip install line_profiler`），逐行统计耗时占比，开销较大。适合**已经知道某个函数慢，进一步钻取「函数里哪一行慢」**。

典型流程：先用 cProfile 找到热点函数，再用 line_profiler 解剖那个函数的热点行。

- 小例子：cProfile 告诉你 `process_data` 占了 80% 的时间；line_profiler 进一步指出其中那行列表推导占了 78%——于是优化目标精确到一行。

💡 提示：line_profiler 的 `@profile` 装饰器要靠 `kernprof -l -v script.py` 注入，或在代码里手动用 `LineProfiler`；直接 `python script.py` 运行会因找不到 `profile` 而报 `NameError`。

2. **性能测试的陷阱**：为什么 `timeit` 要默认执行多次？只执行一次有什么问题？

**参考答案**

只测一次，结果会被各种**偶然因素**污染：操作系统调度、CPU 睿频/降频、缓存冷热、后台进程抢占、垃圾回收、计时器精度等。这一次可能恰好偏大或偏小，**不可靠也不可复现**，你无法判断测到的是「代码的真实性能」还是「当时的运气」。

`timeit` 默认执行多次（`number`）就是为了解决这个问题：① 把计时开销和启动噪声**摊薄**到大量执行上；② 让结果更稳定。再配合 `repeat` 跑多轮、**取最小值**——最小值受「额外干扰」最少，最接近代码的真实性能（平均值容易被偶发卡顿拉高）。

下面是对比演示（仅用标准库，已验证；**耗时数值因机器/版本而异**，这里给示例值）：

```python
import timeit

stmt = "sum(range(1000))"

# 只测一次：结果受偶然因素（调度、缓存、后台进程）影响大
one = timeit.timeit(stmt, number=1)

# 测多轮：每轮跑 1000 次摊薄开销，再取最小值最接近真实性能
rounds = timeit.repeat(stmt, number=1000, repeat=5)

print(f"单次测量        : {one*1e6:.1f} 微秒")
print(f"5 轮(每轮1000次): {[round(t*1e3, 2) for t in rounds]} 毫秒")
print(f"取最小值        : {min(rounds)*1e3:.2f} 毫秒  <- 最稳定、最接近真实性能")
```

示例输出（数值会变化）：

```
单次测量        : 7.3 微秒
5 轮(每轮1000次): [5.65, 5.71, 5.63, 5.64, 5.69] 毫秒
取最小值        : 5.63 毫秒  <- 最稳定、最接近真实性能
```

可以看到：单次测量（7.3 微秒）波动大、参考性差；多轮结果集中在 5.6 毫秒附近，取最小值最稳。

⚠️ 注意：`timeit` 默认会临时关闭 GC 以减少干扰；如果你要测「包含 GC 的真实场景」，需要留意这一默认行为。

3. **内存 vs 时间**：有时候优化内存使用会增加时间开销，反之亦然。如何权衡？

**参考答案**

这是经典的**空间-时间权衡（space-time tradeoff）**：缓存、预计算、查表是「用内存换时间」；生成器、流式处理、压缩是「用时间换内存」。没有绝对优劣，关键看**哪种资源更稀缺、瓶颈在哪**。

权衡的步骤：

1. **明确约束**：是内存受限（嵌入式、海量数据、容器限额），还是延迟敏感（高频交易、实时交互）？
2. **量化测量**：把两种方案的耗时和内存都测出来，用数据说话，而不是凭感觉。
3. **看规模与场景**：数据量小时省内存意义不大；数据量大或内存紧张时优先省内存；高频低延迟场景优先省时间。
4. **找平衡点**：很多工具自带「旋钮」，比如 `lru_cache(maxsize=...)` 用上限控制内存、分块处理兼顾两者。

- 小例子：对百万级数据求平方和，用生成器几乎不占内存但略慢、且不能复用；用列表快但要占几十 MB——内存紧张就选生成器，追求速度且内存够就选列表。

原则：不要走极端，**优先优化最稀缺的资源**，并始终用测量验证收益，避免「省了内存却慢得不可接受」或反之。

4. **基准测试**：为什么基准测试要在"安静"的环境下进行？其他程序会影响结果吗？

**参考答案**

会，而且影响很大。其他程序会抢占 **CPU、内存带宽、磁盘、网络**，还会引起 CPU 睿频/降频波动、污染缓存、增加调度延迟。这些都会让你的测量结果**偏大、不稳定、不可复现**——你测到的不再是「代码本身的性能」，而是「代码 + 当时系统噪声」的混合。

之所以要在「安静」环境下做基准，是因为基准测试的核心价值是**可复现、可对比**：只有环境稳定，优化前后的差异才有意义。噪声会掩盖真实差异，甚至让你把「偶然卡顿」误当成「性能回归」，或把「运气好」误当成「优化生效」。

营造安静环境的常见做法：

- 关闭无关程序和后台服务（编译、杀毒扫描、下载、浏览器等）。
- 固定 CPU 频率（关闭睿频/省电模式）、插电运行、避免过热降频。
- 固定输入数据与随机种子，多次测量取最小值/中位数。

- 小例子：后台正在跑编译或杀毒扫描时测排序，耗时可能翻倍，你会误以为代码变慢了。

💡 提示：用 `timeit.repeat` 多轮取最小值、固定数据规模与种子，能显著降低噪声影响；条件允许时用专门的基准机或容器隔离资源。

5. **性能回归**：如何在项目中建立性能监控，防止新代码导致性能下降？

**参考答案**

核心是把「性能」变成像单元测试一样**可自动检查、可对比、可报警**的东西，建立「基线 → 持续测量 → 超阈值报警」的闭环：

- **建立基线（baseline）**：对关键路径写基准测试，记录基线耗时/内存，作为对比参照。
- **纳入 CI 自动化**：用 `pytest-benchmark`、`asv`（airspeed velocity）等在每次提交/合并时跑基准，与基线对比，**超过阈值（如慢 10%）就让 CI 失败或报警**，把回归挡在合并前。
- **趋势监控**：保存历史性能曲线，长期跟踪；生产环境用 APM/Prometheus 埋点监控延迟、吞吐、错误率，发现线上回归及时定位。
- **流程保障**：性能测试纳入代码评审，优化前后都要测，固定测试环境与数据规模，避免「假回归」。

- 小例子：`pytest-benchmark` 先 `--benchmark-save=baseline` 存基线，CI 中用 `--benchmark-compare` 对比，回退超阈值则 fail。

💡 提示：基准必须在稳定环境、多轮取统计量下运行，否则系统噪声会造成「假回归」，频繁误报反而让人忽略真问题。

---

## 📖 延伸阅读

- [Python 官方文档 - cProfile](https://docs.python.org/3/library/profile.html)
- [line_profiler GitHub](https://github.com/pyutils/line_profiler)
- [memory_profiler GitHub](https://pythonhosted.org/MemoryProfiler/)
