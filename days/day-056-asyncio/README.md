# Day 056 — 异步编程（asyncio）

> 🎯 **今日目标**：掌握 Python 异步编程核心概念，理解事件循环原理，学会用 `async/await` 编写高效并发程序。

---

## 一、为什么需要异步编程？

### 1.1 同步编程的瓶颈

在传统同步模型中，程序是**顺序执行**的：

```python
import time

def fetch_data():
    print("开始请求数据...")
    time.sleep(2)  # 模拟网络请求，阻塞 2 秒
    print("数据获取完成")

def process_data():
    print("开始处理数据...")
    time.sleep(1)  # 模拟处理，阻塞 1 秒
    print("数据处理完成")

# 同步执行：总耗时 = 2 + 1 = 3 秒
fetch_data()
process_data()
```

**问题**：当 `fetch_data()` 等待网络响应时，CPU 空闲但无法做其他事。如果有 100 个请求，同步方式需要等待 `100 × 2 = 200` 秒。

### 1.2 异步编程的核心思想

异步编程的核心是：**在等待 I/O 的时候切换去做别的事**。

```
同步模型（阻塞）：
时间 ──────────────────────────────────►
[请求1 等待中......][请求1完成][请求2 等待中......][请求2完成]
                     ↑ CPU空闲

异步模型（非阻塞）：
时间 ──────────────────────────────────►
[请求1 发起][请求2 发起][请求3 发起]...[请求1完成][请求2完成][请求3完成]
             ↑ CPU不闲着，继续发请求
```

### 1.3 asyncio 的定位

| 场景 | 推荐方案 |
|------|----------|
| CPU 密集型（数学计算、图像处理） | 多进程 `multiprocessing` |
| I/O 密集型（网络请求、文件读写） | 异步 `asyncio` |
| 混合场景 | asyncio + ProcessPoolExecutor |

> **asyncio 的优势**：比线程更轻量（无上下文切换开销），单线程即可实现高并发。

---

## 二、事件循环（Event Loop）—— asyncio 的心脏

### 2.1 什么是事件循环？

事件循环是 asyncio 的核心调度器。它的工作原理就像一个**无限循环的调度中心**：

```
┌──────────────────────────────────────────────────┐
│                  事件循环 (Event Loop)              │
│                                                    │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│   │ Task 1  │  │ Task 2  │  │ Task 3  │  ...      │
│   └────┬────┘  └────┬────┘  └────┬────┘          │
│        │            │            │                 │
│        ▼            ▼            ▼                 │
│   ┌─────────────────────────────────────┐         │
│   │        就绪队列 (Ready Queue)        │         │
│   └─────────────────────────────────────┘         │
│        │                                          │
│        ▼                                          │
│   ┌─────────────────────────────────────┐         │
│   │     I/O 监听器 (Selector/Poller)     │         │
│   │   - 网络 socket 就绪？               │         │
│   │   - 文件描述符就绪？                  │         │
│   │   - 子进程完成？                      │         │
│   └─────────────────────────────────────┘         │
│        │                                          │
│        ▼                                          │
│   ┌─────────────────────────────────────┐         │
│   │      定时器 (Timer/Callback)         │         │
│   │   - sleep 到期？                     │         │
│   │   - 超时检测？                       │         │
│   └─────────────────────────────────────┘         │
└──────────────────────────────────────────────────┘
```

### 2.2 事件循环的工作流程

```python
import asyncio

async def main():
    print("Hello")
    await asyncio.sleep(1)  # 挂起，让出控制权
    print("World")

# asyncio.run() 做了以下事情：
# 1. 创建事件循环
# 2. 运行 main() 协程
# 3. 关闭事件循环
asyncio.run(main())
```

**事件循环的每一步**：
1. 从就绪队列取出一个协程
2. 执行协程直到遇到 `await`（挂起点）
3. 如果 `await` 的是 I/O 操作，注册到 I/O 监听器
4. 继续处理下一个就绪的协程
5. 当 I/O 完成时，将对应的协程放回就绪队列
6. 重复步骤 1-5 直到所有协程完成

### 2.3 手动管理事件循环（了解即可）

```python
import asyncio

async def hello():
    print("Hello")
    await asyncio.sleep(1)
    print("World")

# Python 3.10+ 之前常用的方式
loop = asyncio.get_event_loop()
loop.run_until_complete(hello())
loop.close()

# Python 3.10+ 推荐使用 asyncio.run()
asyncio.run(hello())
```

---

## 三、async/await 关键字

### 3.1 协程函数 vs 协程对象

```python
import asyncio

# 协程函数：用 async def 定义的函数
async def my_coroutine():
    print("我是协程")
    await asyncio.sleep(1)
    return 42

# 注意：调用协程函数不会执行函数体！
# 只是返回一个协程对象（coroutine object）
coro = my_coroutine()
print(type(coro))  # <class 'coroutine'>

# 必须通过事件循环来执行协程
result = asyncio.run(coro)  # 打印"我是协程"，返回 42
print(result)  # 42
```

### 3.2 await 的本质

`await` 是一个**挂起点**（yield point）。当执行到 `await` 时：

1. 协程暂停执行
2. 事件循环可以去执行其他协程
3. 当 `await` 的操作完成后，协程恢复执行

```python
async def fetch_url(url):
    print(f"开始请求 {url}")
    # 这里是挂起点：事件循环可以去处理其他任务
    await asyncio.sleep(2)  # 模拟网络延迟
    print(f"{url} 请求完成")
    return f"{url} 的数据"

async def main():
    # 顺序执行（总耗时 4 秒）
    result1 = await fetch_url("http://a.com")
    result2 = await fetch_url("http://b.com")
    print(result1, result2)

asyncio.run(main())
```

### 3.3 await 的使用限制

```python
import asyncio

# ✅ 正确：在 async def 中 await 协程
async def good():
    await asyncio.sleep(1)

# ❌ 错误：在普通函数中 await 会报 SyntaxError
def bad():
    await asyncio.sleep(1)  # SyntaxError

# ✅ 正确：用 asyncio.run() 启动
asyncio.run(good())
```

---

## 四、并发执行：gather 与 Task

### 4.1 问题：await 会阻塞

上面的例子中，`await fetch_url("http://a.com")` 必须等它完成才能执行下一个。这并不是真正的并发！

### 4.2 asyncio.gather() —— 并发执行多个协程

```python
import asyncio
import time

async def fetch_url(url):
    print(f"开始请求 {url}")
    await asyncio.sleep(2)
    print(f"{url} 完成")
    return f"{url} 数据"

async def main():
    start = time.time()
    
    # gather 会并发执行所有协程
    results = await asyncio.gather(
        fetch_url("http://a.com"),
        fetch_url("http://b.com"),
        fetch_url("http://c.com"),
    )
    
    elapsed = time.time() - start
    print(f"总耗时: {elapsed:.1f}s")  # 约 2 秒，不是 6 秒
    print(f"结果: {results}")

asyncio.run(main())
```

**gather 的工作原理**：

```
时间 ──────────────────────────────────►
[fetch_url(a) 发起][fetch_url(b) 发起][fetch_url(c) 发起]
                    ── 等待中 ──
[a完成] [b完成] [c完成]
        gather 返回 [结果a, 结果b, 结果c]
```

### 4.3 asyncio.create_task() —— 手动创建任务

```python
import asyncio

async def worker(name, delay):
    print(f"[{name}] 开始工作")
    await asyncio.sleep(delay)
    print(f"[{name}] 完成工作")
    return f"{name} 的结果"

async def main():
    # 创建 Task 对象（立即调度执行）
    task1 = asyncio.create_task(worker("A", 2))
    task2 = asyncio.create_task(worker("B", 1))
    task3 = asyncio.create_task(worker("C", 3))
    
    # 等待所有任务完成
    result1 = await task1
    result2 = await task2
    result3 = await task3
    
    print(f"结果: {result1}, {result2}, {result3}")

asyncio.run(main())
```

### 4.4 Task vs gather 对比

| 特性 | `asyncio.create_task()` | `asyncio.gather()` |
|------|------------------------|---------------------|
| 返回值 | 单个 `Task` 对象 | 结果列表 |
| 错误处理 | 需单独处理 | 自动传播 |
| 取消 | 可单独取消 | 需要 `return_exceptions` |
| 适用场景 | 需要精细控制单个任务 | 批量并发执行 |
| 调度时机 | 创建时立即调度 | `await` 时开始执行 |

---

## 五、Future 与 Task

### 5.1 Future 是什么？

`Future` 是一个**代表异步操作最终结果**的对象。它是一个"承诺"——现在没有结果，将来会有。

```
┌─────────────────────────────────┐
│           Future                 │
│                                  │
│  状态: pending → done            │
│  结果: None → result            │
│  回调: callbacks[]              │
│                                  │
│  ┌─────────────────────────┐    │
│  │ 当 Future 完成时：        │    │
│  │ 1. 设置 result           │    │
│  │ 2. 调用所有 callbacks    │    │
│  │ 3. 唤醒等待的协程        │    │
│  └─────────────────────────┘    │
└─────────────────────────────────┘
```

### 5.2 Task 是 Future 的子类

`Task` 继承自 `Future`，额外包装了一个协程：

```python
import asyncio

async def compute():
    await asyncio.sleep(1)
    return 42

async def main():
    task = asyncio.create_task(compute())
    
    print(task.done())  # False — 还在执行
    result = await task
    print(task.done())  # True — 已完成
    print(task.result())  # 42

asyncio.run(main())
```

### 5.3 Task 的生命周期

```
创建 Task → Pending → Running → Done (result/exception/cancelled)
              │         │         │
              │         │         └─ task.result() / task.exception()
              │         └─ 协程正在执行
              └─ 已加入事件循环，等待调度
```

### 5.4 常用 Task 方法

```python
import asyncio

async def work():
    await asyncio.sleep(2)
    return "done"

async def main():
    task = asyncio.create_task(work())
    
    # 状态查询
    print(task.done())       # False
    print(task.cancelled())  # False
    
    # 取消任务
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("任务被取消了")
    
    # 带超时的等待
    task2 = asyncio.create_task(work())
    try:
        result = await asyncio.wait_for(task2, timeout=1.0)
    except asyncio.TimeoutError:
        print("任务超时了")

asyncio.run(main())
```

---

## 六、错误处理

### 6.1 单个协程的异常

```python
import asyncio

async def risky_operation():
    await asyncio.sleep(1)
    raise ValueError("出错了！")

async def main():
    try:
        result = await risky_operation()
    except ValueError as e:
        print(f"捕获到错误: {e}")

asyncio.run(main())
```

### 6.2 Task 的异常

```python
import asyncio

async def failing_task():
    await asyncio.sleep(0.5)
    raise RuntimeError("Task 失败")

async def main():
    task = asyncio.create_task(failing_task())
    
    # 异常会被"存储"在 Task 中
    # 如果不 await 或不处理，Python 会发出警告
    try:
        result = await task
    except RuntimeError as e:
        print(f"Task 错误: {e}")

asyncio.run(main())
```

### 6.3 gather 的错误处理

```python
import asyncio

async def ok_task():
    await asyncio.sleep(1)
    return "成功"

async def fail_task():
    await asyncio.sleep(0.5)
    raise ValueError("失败")

async def main():
    # 默认：第一个异常会抛出，其他任务被取消
    try:
        results = await asyncio.gather(ok_task(), fail_task())
    except ValueError as e:
        print(f"错误: {e}")

    # 使用 return_exceptions=True 收集所有结果（含异常）
    results = await asyncio.gather(
        ok_task(), fail_task(),
        return_exceptions=True  # 异常作为结果返回，不抛出
    )
    for r in results:
        if isinstance(r, Exception):
            print(f"异常: {r}")
        else:
            print(f"成功: {r}")

asyncio.run(main())
```

---

## 七、asyncio 的内部机制

### 7.1 基于生成器的协程（历史）

早期的 asyncio（Python 3.4）使用 `@asyncio.coroutine` 装饰器和 `yield from`：

```python
# Python 3.4 风格（已废弃）
@asyncio.coroutine
def old_style():
    yield from asyncio.sleep(1)
    return 42

# Python 3.5+ 风格（推荐）
async def new_style():
    await asyncio.sleep(1)
    return 42
```

### 7.2 协程的挂起与恢复

```
async def example():
    x = 1              ← 执行
    await something()  ← 挂起点（保存当前状态）
    y = 2              ← 恢复执行（从挂起点继续）
```

底层实现：
- 协程对象内部维护一个 **字节码指令指针** 和 **局部变量表**
- 遇到 `await` 时，保存这些状态，将控制权交还事件循环
- 事件循环在合适时机恢复协程，从中断点继续执行

### 7.3 选择器（Selector）—— I/O 多路复用

事件循环底层使用操作系统的 I/O 多路复用机制：

| 操作系统 | 底层机制 |
|---------|---------|
| Linux | `epoll` |
| macOS | `kqueue` |
| Windows | `IOCP` (Proactor) |
| 通用 | `selectors` 模块（自动选择最优方案） |

```
事件循环
    │
    ├── select/kqueue/epoll 监听 socket 可读/可写
    ├── 回调注册到 selector
    ├── selector.select(timeout) 等待事件
    └── 触发回调，恢复对应协程
```

---

## 八、实战：异步 Web 爬虫

### 8.1 场景：并发请求多个 URL

```python
import asyncio
import aiohttp
import time

URLS = [
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/1",
]

async def fetch(session, url):
    """异步获取单个 URL"""
    async with session.get(url) as response:
        return await response.json()

async def main():
    start = time.time()
    
    async with aiohttp.ClientSession() as session:
        # 并发请求所有 URL
        tasks = [fetch(session, url) for url in URLS]
        results = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start
    print(f"请求了 {len(URLS)} 个 URL")
    print(f"总耗时: {elapsed:.1f}s")  # 约 1 秒，不是 5 秒
    for i, r in enumerate(results):
        print(f"  URL {i+1}: delay={r.get('args', {}).get('delay', '?')}")

asyncio.run(main())
```

### 8.2 带限流的爬虫

```python
import asyncio
import aiohttp

async def fetch_with_limit(session, url, semaphore):
    """使用信号量限制并发数"""
    async with semaphore:  # 同时最多 5 个请求
        async with session.get(url) as response:
            print(f"  请求 {url}: 状态 {response.status}")
            return await response.text()

async def main():
    # 限制同时最多 5 个并发请求
    semaphore = asyncio.Semaphore(5)
    
    urls = [f"https://httpbin.org/delay/1?id={i}" for i in range(20)]
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_limit(session, url, semaphore) for url in urls]
        results = await asyncio.gather(*tasks)
    
    print(f"完成 {len(results)} 个请求")

asyncio.run(main())
```

### 8.3 超时控制

```python
import asyncio
import aiohttp

async def fetch_with_timeout(url, timeout_seconds=5):
    """带超时控制的请求"""
    try:
        async with asyncio.timeout(timeout_seconds):  # Python 3.11+
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
    except TimeoutError:
        print(f"  {url} 请求超时")
        return None

async def main():
    urls = [
        "https://httpbin.org/delay/1",  # 1秒延迟
        "https://httpbin.org/delay/10",  # 10秒延迟，会超时
    ]
    
    tasks = [fetch_with_timeout(url, timeout_seconds=3) for url in urls]
    results = await asyncio.gather(*tasks)
    
    for i, r in enumerate(results):
        status = "成功" if r else "超时"
        print(f"URL {i+1}: {status}")

asyncio.run(main())
```

---

## 九、常见陷阱与最佳实践

### 9.1 ❌ 在异步函数中使用同步阻塞

```python
import asyncio
import time

async def bad_example():
    # 这会阻塞整个事件循环！其他协程也无法执行
    time.sleep(5)  # ❌ 不要用 time.sleep
    return "done"

async def good_example():
    await asyncio.sleep(5)  # ✅ 使用 asyncio.sleep
    return "done"
```

### 9.2 ❌ 忘记 await

```python
import asyncio

async def compute():
    return 42

async def main():
    result = compute()  # ❌ 忘记 await，result 是协程对象不是数字！
    print(result)  # <coroutine object compute at 0x...>
    
    result = await compute()  # ✅ 正确
    print(result)  # 42
```

### 9.3 ❌ 创建 Task 后不等待

```python
import asyncio

async def background_work():
    await asyncio.sleep(10)
    print("后台工作完成")

async def main():
    # ❌ 创建了 Task 但不 await，可能程序退出时任务还没执行完
    task = asyncio.create_task(background_work())
    # 程序可能在这里退出

async def main_correct():
    # ✅ 创建 Task 后要等待
    task = asyncio.create_task(background_work())
    await task  # 或者使用 asyncio.gather
```

### 9.4 ✅ 最佳实践清单

1. **始终使用 `asyncio.run()` 启动**（Python 3.7+）
2. **I/O 操作用 `await`，不要用同步版本**
3. **用 `asyncio.gather()` 或 `create_task()` 实现并发**
4. **用 `Semaphore` 控制并发数**，避免过多连接
5. **用 `asyncio.timeout()` 设置超时**
6. **不要在异步代码中混用同步阻塞操作**
7. **Task 创建后一定要 `await` 或 `gather`**

---

## 十、API 速查表

### 核心函数

| 函数 | 说明 |
|------|------|
| `asyncio.run(coro)` | 运行协程，关闭事件循环 |
| `asyncio.gather(*coros)` | 并发运行多个协程，返回结果列表 |
| `asyncio.create_task(coro)` | 创建 Task 并调度执行 |
| `asyncio.wait(tasks)` | 等待多个 Task，返回 (done, pending) |
| `asyncio.wait_for(coro, timeout)` | 带超时等待协程 |
| `asyncio.sleep(seconds)` | 异步休眠 |
| `asyncio.current_task()` | 获取当前运行的 Task |
| `asyncio.all_tasks()` | 获取所有未完成的 Task |

### Semaphore

| 方法 | 说明 |
|------|------|
| `asyncio.Semaphore(n)` | 创建信号量，限制并发数为 n |
| `semaphore.acquire()` | 获取信号量（异步） |
| `semaphore.release()` | 释放信号量 |

### Task 方法

| 方法 | 说明 |
|------|------|
| `task.done()` | 是否已完成 |
| `task.result()` | 获取结果（未完成会阻塞） |
| `task.exception()` | 获取异常 |
| `task.cancel()` | 请求取消 |
| `task.cancelled()` | 是否已取消 |
| `task.add_done_callback(fn)` | 添加完成回调 |

---

## 十一、思考题

1. **为什么 asyncio 是单线程的，却能实现高并发？** 它和多线程的本质区别是什么？

2. **如果一个协程中调用了 `time.sleep(5)` 而不是 `await asyncio.sleep(5)`，会发生什么？** 如何检测这类问题？

3. **`asyncio.gather()` 和 `asyncio.create_task()` + `await task` 有什么区别？** 在什么场景下选择哪个？

4. **如何实现一个异步的生产者-消费者模型？** 提示：使用 `asyncio.Queue`。

5. **事件循环在不同操作系统上使用不同的 I/O 多路复用机制（epoll/kqueue/IOCP），这些机制的本质区别是什么？**

---

## 十二、总结

| 概念 | 关键点 |
|------|--------|
| **事件循环** | asyncio 的心脏，调度所有协程和 I/O 事件 |
| **async/await** | 定义和使用协程的关键字，`await` 是挂起点 |
| **Task** | Future 的子类，包装协程，可并发执行 |
| **gather** | 并发运行多个协程，收集结果 |
| **Semaphore** | 控制并发数量，避免资源耗尽 |
| **核心原则** | I/O 操作用 `await`，避免同步阻塞，Task 创建后要等待 |

> 💡 **下一步**：Day 057 将深入学习 asyncio 的进阶特性——异步上下文管理器、异步迭代器和 aiohttp 实战。
