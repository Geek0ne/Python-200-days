# Day 058 — 并发模型对比 练习清单

## ✅ 今日完成清单

- [ ] 理解 GIL 的工作原理和影响
- [ ] 掌握 threading 模块的基本用法
- [ ] 掌握 multiprocessing 模块的基本用法
- [ ] 掌握 asyncio 协程的基本用法
- [ ] 理解三种模型的内存模型差异
- [ ] 能根据场景选择合适的并发模型
- [ ] 完成基准测试代码并分析结果

---

## 📝 基础练习

### 练习 1: 线程安全计数器
编写一个线程安全的计数器类，支持 `increment()` 和 `get_value()` 方法，使用 `threading.Lock` 保护。

```python
class ThreadSafeCounter:
    def __init__(self):
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self):
        # TODO: 实现线程安全的递增
        pass
    
    def get_value(self):
        # TODO: 返回当前值
        pass
```

**验证**：启动 10 个线程各递增 10000 次，最终值应为 100000。

---

### 练习 2: 进程池并行计算
使用 `ProcessPoolExecutor` 并行计算 100 个数的阶乘，对比串行和并行的耗时。

```python
import math
from concurrent.futures import ProcessPoolExecutor

def factorial(n):
    return math.factorial(n)

# TODO: 使用 ProcessPoolExecutor 并行计算
# TODO: 对比串行和并行耗时
```

---

### 练习 3: 协程并发请求
使用 `asyncio.gather` 同时发起 10 个异步任务（模拟 I/O），总耗时应接近单个任务的耗时。

```python
import asyncio

async def simulated_request(task_id, delay):
    print(f"Task {task_id} 开始")
    await asyncio.sleep(delay)
    print(f"Task {task_id} 完成")
    return f"result-{task_id}"

# TODO: 使用 asyncio.gather 并发执行 10 个任务
```

---

## 🚀 进阶挑战

### 挑战 1: 生产者-消费者模型
实现一个多进程的生产者-消费者系统：
- 1 个生产者进程，持续生成随机数
- 3 个消费者进程，从队列取数并计算平方
- 使用 `multiprocessing.Queue` 通信
- 优雅退出（生产者发送结束信号）

---

### 挑战 2: 混合并发架构
设计一个程序，同时使用进程池和线程池：
- 进程池处理 CPU 密集型子任务
- 线程池处理 I/O 密集型子任务
- 主协程协调两者

---

### 挑战 3: 性能对比实验
编写完整的基准测试脚本，测量：
- 不同线程数对 CPU 密集型任务的影响
- 不同进程数对 CPU 密集型任务的影响
- 不同协程数对 I/O 密集型任务的影响
- 输出对比表格

---

## 💡 思考题

1. **为什么 Python 选择保留 GIL？移除 GIL 有什么代价？**

2. **在什么场景下，多线程比多进程更好？（除了 I/O 密集型）**

3. **协程的 `await` 和线程的 `sleep` 有什么本质区别？**

4. **如何判断一个任务是 CPU 密集型还是 I/O 密集型？**
