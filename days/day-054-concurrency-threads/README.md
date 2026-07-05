# Day 054 — 并发入门：线程

> 📅 学习日期：2026-07-06  
> 🎯 学习目标：理解 Python 线程机制，掌握 GIL 原理，学会线程安全与锁的使用

---

## 目录

1. [为什么需要并发？](#1-为什么需要并发)
2. [GIL 原理与影响](#2-gil-原理与影响)
3. [threading 模块](#3-threading-模块)
4. [线程安全与锁](#4-线程安全与锁)
5. [实战：并发下载器](#5-实战并发下载器)
6. [思考题](#6-思考题)

---

## 1. 为什么需要并发？

### 1.1 同步 vs 并发

在同步编程中，代码按顺序逐行执行——上一行没执行完，下一行就不会开始。但很多场景下，我们需要同时做多件事：

- **I/O 密集型任务**：读写文件、网络请求、数据库查询（CPU 在等待 I/O，大部分时间在空闲）
- **多用户服务**：Web 服务器需要同时处理多个用户请求
- **定时任务**：后台监控、心跳检测等需要与主逻辑并行

### 1.2 并发的两种形态

| 概念 | 定义 | Python 实现 |
|------|------|-------------|
| **并发 (Concurrency)** | 任务交替执行，逻辑上同时进行 | threading, asyncio |
| **并行 (Parallelism)** | 任务物理上同时执行（多核 CPU） | multiprocessing |

> 💡 关键区别：并发是"看起来同时"，并行是"真的同时"。单核 CPU 只能并发，不能并行。

### 1.3 Python 的并发工具箱

```
┌─────────────────────────────────────────────────┐
│              Python 并发方案                      │
├──────────┬──────────┬──────────┬────────────────┤
│ threading│  multiprocessing│ asyncio  │ concurrent.futures│
│ 线程并发  │  多进程并行     │ 异步协程 │ 线程/进程池    │
│ I/O 密集 │  CPU 密集     │ I/O 密集 │ 统一接口     │
└──────────┴──────────┴──────────┴────────────────┘
```

今天先攻克 **threading 模块**，这是 Python 并发编程的第一课。

---

## 2. GIL 原理与影响

### 2.1 什么是 GIL？

**GIL（Global Interpreter Lock）** 是 CPython 解释器中的一把全局互斥锁。它保证同一时刻只有一个线程执行 Python 字节码。

```
  线程 A 执行中          线程 B 等待          线程 A I/O 阻塞
  ┌──────────┐         ┌──────────┐         ┌──────────┐
  │ 执行字节码 │ ──────▶│ 等待 GIL  │         │ 执行字节码 │
  │ ...      │         │ ...      │         │ ...      │
  └──────────┘         └──────────┘         └──────────┘
        │                                        │
        │          释放 GIL（遇到 I/O）            │
        └────────────────────────────────────────┘
                    线程 B 获得 GIL 执行
```

### 2.2 为什么要有 GIL？

1. **简化内存管理**：CPython 使用引用计数，GIL 保证引用计数操作的线程安全
2. **简化 C 扩展开发**：大多数 C 扩展假设单线程环境，GIL 让它们不用考虑并发
3. **历史原因**：Python 诞生于 1991 年，当时多核 CPU 还不常见

### 2.3 GIL 的影响

| 场景 | GIL 影响 | 推荐方案 |
|------|---------|---------|
| CPU 密集型 | ❌ 有害 — 多线程反而更慢 | multiprocessing |
| I/O 密集型 | ✅ 有益 — I/O 时释放 GIL | threading / asyncio |
| 混合型 | ⚠️ 部分有益 | 视情况而定 |

```python
import threading, time

def cpu_bound():
    """CPU 密集型任务 — GIL 导致多线程无法加速"""
    total = 0
    for i in range(10_000_000):
        total += i
    return total

# 单线程
start = time.time()
cpu_bound()
cpu_bound()
print(f"单线程: {time.time() - start:.2f}s")  # ~2.1s

# 多线程 — 注意：并不会更快！
start = time.time()
t1 = threading.Thread(target=cpu_bound)
t2 = threading.Thread(target=cpu_bound)
t1.start(); t2.start()
t1.join(); t2.join()
print(f"多线程: {time.time() - start:.2f}s")  # ~2.3s（可能更慢）
```

> ⚠️ GIL 的存在意味着：**对于 CPU 密集型任务，多线程无法利用多核 CPU 加速**。

### 2.4 释放 GIL 的场景

Python 中这些操作会释放 GIL：

- **文件 I/O**：`open()`, `read()`, `write()`
- **网络 I/O**：`socket.recv()`, `urllib.request.urlopen()`
- **`time.sleep()`**
- **`os.system()`**
- **C 扩展**：NumPy、PIL 等在计算时会释放 GIL
- **`ctypes` 调用**

### 2.5 GIL 替代方案

| 方案 | 说明 |
|------|------|
| **PEP 703 (Python 3.13+)** | 可选 GIL — `python3.13t` 构建 |
| **PyPy** | 使用 JIT 的替代解释器，GIL 实现不同 |
| **Cython** | 可在 C 代码中释放 GIL |
| **multiprocessing** | 绕过 GIL，使用独立进程 |

---

## 3. threading 模块

### 3.1 创建线程

Python 的 `threading` 模块提供了两种创建线程的方式：

```python
import threading

# 方式 1：传入 callable（推荐用于简单任务）
def worker(name):
    print(f"Worker {name} is running")

t = threading.Thread(target=worker, args=("Alice",))
t.start()
t.join()

# 方式 2：继承 Thread 类（推荐用于复杂任务）
class MyThread(threading.Thread):
    def __init__(self, name):
        super().__init__()
        self.name = name
    
    def run(self):
        print(f"MyThread {self.name} is running")

t = MyThread("Bob")
t.start()
t.join()
```

### 3.2 threading.Thread API 速查

| 参数 | 类型 | 说明 |
|------|------|------|
| `target` | callable | 线程要执行的函数 |
| `args` | tuple | target 的位置参数 |
| `kwargs` | dict | target 的关键字参数 |
| `name` | str | 线程名称（默认 Thread-N） |
| `daemon` | bool | 是否为守护线程 |

| 方法 | 说明 |
|------|------|
| `start()` | 启动线程 |
| `join(timeout)` | 等待线程结束 |
| `is_alive()` | 检查线程是否仍在运行 |
| `name` | 线程名称（读写） |
| `ident` | 线程 ID（整数） |
| `daemon` | 是否守护线程（读写） |

### 3.3 守护线程 vs 非守护线程

```python
import threading, time

# 守护线程：主线程退出时自动终止
def daemon_worker():
    while True:
        print("守护线程运行中...")
        time.sleep(0.5)

# 非守护线程：主线程退出后仍会运行直到完成
def normal_worker():
    for i in range(3):
        print(f"普通线程 {i}")
        time.sleep(1)

d = threading.Thread(target=daemon_worker, daemon=True)
n = threading.Thread(target=normal_worker)

d.start()
n.start()

# 主线程不 join，守护线程会被强制终止
time.sleep(0.3)
print("主线程退出")
```

> 💡 守护线程适合：后台监控、定时心跳。普通线程适合：需要确保完成的任务。

### 3.4 daemon 的设计原理

```
主线程退出时：
  ┌──────────┐     ┌──────────────┐     ┌──────────────┐
  │ 主线程    │     │ 守护线程      │     │ 普通线程      │
  │ exit()   │────▶│ 被强制终止 ✗  │     │ 继续运行 ✓   │
  └──────────┘     └──────────────┘     └──────────────┘
```

守护线程就像"仆从"——主人走了，仆从也跟着走。

---

## 4. 线程安全与锁

### 4.1 为什么需要线程安全？

当多个线程同时访问共享资源时，可能产生**竞态条件（Race Condition）**：

```python
import threading

counter = 0

def increment():
    global counter
    for _ in range(1_000_000):
        counter += 1  # 这不是原子操作！

# 两个线程同时 increment
t1 = threading.Thread(target=increment)
t2 = threading.Thread(target=increment)
t1.start(); t2.start()
t1.join(); t2.join()

print(f"期望: 2000000, 实际: {counter}")
# 输出: 期望: 2000000, 实际: 1234567（每次不同）
```

### 4.2 `counter += 1` 的隐患

`counter += 1` 看似简单，实际上是三步操作：

```
  线程 A                    线程 B
  ──────                    ──────
  1. 读取 counter (5)       1. 读取 counter (5)
  2. 计算 counter+1 (6)     2. 计算 counter+1 (6)
  3. 写入 counter (6)       3. 写入 counter (6)
  
  结果: counter = 6（期望 7！）
```

这就是经典的"读-改-写"竞态条件。

### 4.3 Lock — 基本锁

```python
import threading

counter = 0
lock = threading.Lock()

def safe_increment():
    global counter
    for _ in range(1_000_000):
        with lock:  # 获取锁，退出时自动释放
            counter += 1

t1 = threading.Thread(target=safe_increment)
t2 = threading.Thread(target=safe_increment)
t1.start(); t2.start()
t1.join(); t2.join()

print(f"结果: {counter}")  # 期望: 2000000
```

### 4.4 Lock API 速查

```python
lock = threading.Lock()   # 创建锁

lock.acquire()            # 获取锁（阻塞）
lock.acquire(timeout=5)   # 超时获取（返回 True/False）
lock.release()            # 释放锁

# 推荐使用 context manager
with lock:
    # 受保护的代码
    pass

# 尝试非阻塞获取
if lock.locked():
    print("锁已被占用")
```

### 4.5 RLock — 可重入锁

普通 Lock 在同一线程中不能重复获取，否则会死锁。RLock 允许同一线程多次获取：

```python
import threading

rlock = threading.RLock()

def recursive_task(n):
    with rlock:
        if n > 0:
            print(f"递归层级: {n}")
            recursive_task(n - 1)  # 同一线程再次获取锁

recursive_task(3)
# 如果用 Lock，这里会死锁！
```

### 4.6 条件变量 (Condition)

线程间的"通知-等待"机制：

```python
import threading, time

items = []
condition = threading.Condition()

def producer():
    with condition:
        items.append("item")
        print("生产了 item")
        condition.notify()  # 通知消费者

def consumer():
    with condition:
        while not items:
            print("等待产品...")
            condition.wait()  # 释放锁并等待通知
        item = items.pop()
        print(f"消费了 {item}")

t1 = threading.Thread(target=consumer)
t2 = threading.Thread(target=producer)
t1.start()
time.sleep(0.1)  # 确保 consumer 先运行
t2.start()
t1.join(); t2.join()
```

### 4.7 信号量 (Semaphore)

控制同时访问资源的线程数量：

```python
import threading

semaphore = threading.Semaphore(3)  # 最多 3 个线程同时访问

def access_resource(name):
    with semaphore:
        print(f"{name} 进入资源区")
        # 模拟处理
        import time; time.sleep(1)
        print(f"{name} 离开资源区")

threads = [threading.Thread(target=access_resource, args=(f"T{i}",)) 
           for i in range(6)]
for t in threads: t.start()
for t in threads: t.join()
```

### 4.8 事件 (Event)

简单的线程间同步信号：

```python
import threading, time

event = threading.Event()

def waiter():
    print("等待事件...")
    event.wait()  # 阻塞直到 event.set()
    print("事件已发生！")

def setter():
    time.sleep(2)
    print("触发事件！")
    event.set()

t1 = threading.Thread(target=waiter)
t2 = threading.Thread(target=setter)
t1.start(); t2.start()
t1.join(); t2.join()
```

### 4.9 同步原语对比

```
┌────────────┬────────────────────────────────────┐
│   原语      │  用途                              │
├────────────┼────────────────────────────────────┤
│   Lock      │  互斥访问共享资源                   │
│   RLock     │  可重入的互斥锁（递归场景）          │
│   Condition │  生产者-消费者模型的等待/通知        │
│   Semaphore │  限制并发数量（如数据库连接池）       │
│   Event     │  简单的一次性信号通知                │
│   Barrier   │  多线程同步到达某个点再继续           │
└────────────┴────────────────────────────────────┘
```

---

## 5. 实战：并发下载器

### 5.1 同步下载 vs 多线程下载

```python
"""同步下载 — 串行等待，效率低"""
import urllib.request
import time

urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

start = time.time()
for url in urls:
    urllib.request.urlopen(url)
print(f"同步下载: {time.time() - start:.2f}s")  # ~3s
```

### 5.2 多线程版本

```python
"""多线程下载 — 并发执行，效率高"""
import urllib.request
import threading
import time

urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

results = {}
lock = threading.Lock()

def download(url):
    try:
        data = urllib.request.urlopen(url)
        with lock:
            results[url] = len(data.read())
    except Exception as e:
        with lock:
            results[url] = str(e)

start = time.time()
threads = [threading.Thread(target=download, args=(url,)) for url in urls]
for t in threads: t.start()
for t in threads: t.join()
print(f"多线程下载: {time.time() - start:.2f}s")  # ~1s
```

### 5.3 线程池版本（最佳实践）

```python
"""使用 concurrent.futures.ThreadPoolExecutor — 推荐方式"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import time

urls = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

def download(url):
    data = urllib.request.urlopen(url)
    return url, len(data.read())

start = time.time()
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(download, url): url for url in urls}
    for future in as_completed(futures):
        url, size = future.result()
        print(f"下载完成: {url} ({size} bytes)")
print(f"总耗时: {time.time() - start:.2f}s")
```

### 5.4 带进度条的并发下载器

```python
"""带进度显示的并发下载器"""
import urllib.request
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class ProgressDownloader:
    def __init__(self, max_workers=3):
        self.max_workers = max_workers
        self.completed = 0
        self.lock = threading.Lock()
        self.total = 0
    
    def download_one(self, url):
        """下载单个文件"""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            data = response.read()
            
            with self.lock:
                self.completed += 1
                progress = f"[{self.completed}/{self.total}]"
                print(f"{progress} ✓ {url} ({len(data)} bytes)")
            
            return {"url": url, "size": len(data), "status": "ok"}
        except Exception as e:
            with self.lock:
                self.completed += 1
                print(f"[{self.completed}/{self.total}] ✗ {url} ({e})")
            return {"url": url, "size": 0, "status": "error", "error": str(e)}
    
    def download_all(self, urls):
        """并发下载所有文件"""
        self.total = len(urls)
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {
                executor.submit(self.download_one, url): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
        
        # 统计
        ok = sum(1 for r in results if r["status"] == "ok")
        total_size = sum(r["size"] for r in results)
        print(f"\n📊 完成: {ok}/{self.total} 成功, 总大小: {total_size:,} bytes")
        return results

# 使用示例
if __name__ == "__main__":
    urls = [
        "https://httpbin.org/delay/0.5",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1.5",
        "https://httpbin.org/status/200",
        "https://httpbin.org/bytes/1024",
    ]
    
    downloader = ProgressDownloader(max_workers=3)
    start = time.time()
    results = downloader.download_all(urls)
    print(f"⏱️ 总耗时: {time.time() - start:.2f}s")
```

---

## 6. 思考题

1. **GIL 与多线程**：如果 GIL 阻止了多线程并行执行 Python 代码，为什么 Python 还要提供 threading 模块？它主要解决什么问题？

2. **死锁场景**：以下代码有什么问题？如何修复？
   ```python
   lock_a = threading.Lock()
   lock_b = threading.Lock()
   
   def task1():
       with lock_a:
           with lock_b:
               print("task1")
   
   def task2():
       with lock_b:
           with lock_a:
               print("task2")
   ```

3. **线程 vs 进程**：一个 Web 爬虫程序需要同时下载 100 个网页，应该用 threading 还是 multiprocessing？为什么？

4. **锁的选择**：什么场景下应该用 `threading.Lock()`？什么场景下应该用 `threading.RLock()`？

5. **守护线程陷阱**：如果一个守护线程正在写文件，主线程退出时守护线程被强制终止，可能导致什么问题？如何避免？

---

## 今日总结

| 概念 | 核心要点 |
|------|---------|
| **GIL** | 全局解释器锁，保证同一时刻只有一个线程执行字节码 |
| **threading** | Python 标准库线程模块，适合 I/O 密集型任务 |
| **Lock/RLock** | 互斥锁，保护共享资源；RLock 可重入 |
| **Condition** | 条件变量，用于生产者-消费者模型 |
| **Semaphore** | 信号量，控制并发数量 |
| **ThreadPoolExecutor** | 线程池，推荐的并发下载方式 |

> 📌 明天预告：Day 055 — 并发进阶：进程（multiprocessing 模块）
