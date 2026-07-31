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

2. **性能测试的陷阱**：为什么 `timeit` 要默认执行多次？只执行一次有什么问题？

3. **内存 vs 时间**：有时候优化内存使用会增加时间开销，反之亦然。如何权衡？

4. **基准测试**：为什么基准测试要在"安静"的环境下进行？其他程序会影响结果吗？

5. **性能回归**：如何在项目中建立性能监控，防止新代码导致性能下降？

---

## 📖 延伸阅读

- [Python 官方文档 - cProfile](https://docs.python.org/3/library/profile.html)
- [line_profiler GitHub](https://github.com/pyutils/line_profiler)
- [memory_profiler GitHub](https://pythonhosted.org/MemoryProfiler/)
