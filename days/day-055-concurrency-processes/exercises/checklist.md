# Day 055 — 进程并发：完成清单与练习

## ✅ 今日完成清单

- [ ] 理解 GIL 对 CPU 密集型任务的限制，明白为什么需要多进程
- [ ] 掌握 `multiprocessing.Process` 的创建、启动和等待
- [ ] 理解 daemon 守护进程的用途和行为
- [ ] 掌握 Queue 实现生产者-消费者模式
- [ ] 掌握 Pipe 实现点对点通信
- [ ] 了解 Value/Array 共享内存和 Manager 共享对象
- [ ] 掌握 Pool 的 map/apply_async 等方法
- [ ] 理解 fork vs spawn 启动方式的区别
- [ ] 完成至少 3 道练习题

---

## 📝 练习题

### 基础题

#### 练习 1：双进程累加器
创建两个子进程，分别计算 1~500000 和 500001~1000000 的和，主进程汇总结果。

**要求：**
- 使用 `multiprocessing.Process`
- 通过 `Queue` 传递结果
- 验证最终结果 = 500000500000

**参考：**
```python
import multiprocessing as mp

def calculate_sum(start, end, queue):
    total = sum(range(start, end + 1))
    queue.put(total)

if __name__ == '__main__':
    queue = mp.Queue()
    p1 = mp.Process(target=calculate_sum, args=(1, 500000, queue))
    p2 = mp.Process(target=calculate_sum, args=(500001, 1000000, queue))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    result = queue.get() + queue.get()
    print(f"总和: {result}")
```

---

#### 练习 2：多进程文件统计器
编写一个多进程程序，统计指定目录下所有 `.py` 文件的总行数。

**要求：**
- 使用 `Pool.map` 并行处理文件
- 每个文件由一个进程负责统计
- 输出每个文件的行数和总行数

**提示：**
```python
import multiprocessing as mp
import glob

def count_lines(filepath):
    with open(filepath, 'r') as f:
        return len(f.readlines())

if __name__ == '__main__':
    files = glob.glob("**/*.py", recursive=True)
    with mp.Pool() as pool:
        results = pool.map(count_lines, files)
    for f, lines in zip(files, results):
        print(f"  {f}: {lines} 行")
    print(f"总计: {sum(results)} 行")
```

---

#### 练习 3：进程间传递自定义类
实现两个进程间传递自定义类的实例（需要实现 `__getstate__` 和 `__setstate__` 方法）。

**要求：**
- 定义一个 `Point` 类，包含 x, y 坐标
- 实现 pickle 序列化支持
- 通过 Queue 在进程间传递 Point 对象

---

### 进阶题

#### 练习 4：多进程 MapReduce
实现一个简单的 MapReduce 框架，统计一段文本中每个单词出现的次数。

**要求：**
- map 阶段：多个进程并行处理文本分片
- reduce 阶段：汇总各进程的结果
- 使用 Pool 和 Queue/Pipe

**参考思路：**
```python
import multiprocessing as mp
from collections import Counter

def map_words(text_chunk):
    words = text_chunk.lower().split()
    return Counter(words)

def reduce_counters(counter_list):
    total = Counter()
    for c in counter_list:
        total.update(c)
    return total

if __name__ == '__main__':
    text = "the quick brown fox jumps over the lazy dog the fox"
    chunks = text.split(' ', 3)  # 简单分片
    
    with mp.Pool(2) as pool:
        mapped = pool.map(map_words, chunks)
    
    result = reduce_counters(mapped)
    print(dict(result))
```

---

#### 练习 5：进程池监控器
实现一个监控进程池状态的装饰器，记录每个任务的执行时间、进程 ID 和成功/失败状态。

**要求：**
- 包装 `Pool.apply_async`
- 记录每个任务的元数据
- 任务完成后输出汇总报告

**参考：**
```python
import multiprocessing as mp
import time
from functools import wraps

def monitored_task(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        pid = mp.current_process().pid
        try:
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            return {"result": result, "pid": pid, "time": elapsed, "status": "ok"}
        except Exception as e:
            elapsed = time.perf_counter() - start
            return {"error": str(e), "pid": pid, "time": elapsed, "status": "fail"}
    return wrapper

@monitored_task
def process_item(item):
    time.sleep(0.1)
    return item ** 2

if __name__ == '__main__':
    with mp.Pool(4) as pool:
        results = pool.map(process_item, range(10))
    for r in results:
        print(r)
```

---

#### 练习 6：生产者-消费者 + 背压控制
实现一个带背压（backpressure）控制的生产者-消费者系统，当消费者处理不过来时，生产者自动减速。

**要求：**
- 使用 `Queue(maxsize=N)` 控制缓冲区大小
- 生产者在队列满时阻塞（自动背压）
- 消费者处理完一个才通知生产者继续

---

## 🎯 挑战题

#### 挑战 1：多进程爬虫模拟器
模拟一个多进程网页爬虫，使用进程池并发下载 N 个 URL（模拟），支持：
- 超时控制
- 重试机制
- 结果汇总与去重

#### 挑战 2：进程间共享缓存
实现一个基于 Manager 的分布式缓存系统，支持：
- `get(key)` / `set(key, value)` / `delete(key)`
- TTL（过期时间）
- LRU 淘汰策略

#### 挑战 3：进程池动态扩缩容
实现一个可以根据负载自动调整进程数的进程池包装器：
- 队列积压时增加工作进程
- 空闲时减少工作进程
- 设置最小/最大进程数限制

---

## 📊 自评

完成后打分（1-5）：
- 概念理解：___/5
- 代码实现：___/5
- 避坑意识：___/5
- 实战应用：___/5
