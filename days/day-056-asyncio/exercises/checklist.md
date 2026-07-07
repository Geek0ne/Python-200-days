# Day 056 — 异步编程（asyncio）练习清单

## ✅ 今日完成清单

- [ ] 理解同步 vs 异步编程的区别
- [ ] 掌握事件循环的工作原理
- [ ] 理解 async/await 关键字的用法
- [ ] 掌握 asyncio.gather() 和 create_task() 的使用
- [ ] 理解 Future 和 Task 的关系
- [ ] 学会错误处理和取消操作
- [ ] 完成基础练习题
- [ ] 完成进阶挑战题

---

## 📝 基础练习题

### 练习 1：异步计数器

编写一个异步函数 `async_counter(n)`，每隔 0.5 秒打印一个数字，从 1 到 n。

```python
import asyncio

async def async_counter(n):
    # 在这里编写代码
    pass

asyncio.run(async_counter(5))
# 预期输出：
# 1
# 2
# 3
# 4
# 5
```

### 练习 2：并发下载模拟

模拟并发下载 5 个文件，每个文件下载耗时不同（1-3 秒）。使用 `asyncio.gather()` 实现并发，并打印总耗时。

```python
import asyncio
import time
import random

async def download_file(file_id):
    delay = random.randint(1, 3)
    print(f"开始下载文件 {file_id}...")
    await asyncio.sleep(delay)
    print(f"文件 {file_id} 下载完成! (耗时 {delay}s)")
    return f"file_{file_id}"

async def main():
    start = time.time()
    # 在这里使用 gather 并发下载
    # files = await asyncio.gather(...)
    elapsed = time.time() - start
    print(f"总耗时: {elapsed:.1f}s")

asyncio.run(main())
```

### 练习 3：错误处理

编写代码，使用 `asyncio.gather()` 同时运行 3 个协程，其中一个会抛出异常。使用 `return_exceptions=True` 收集所有结果，并区分成功和失败。

```python
import asyncio

async def success_task():
    await asyncio.sleep(1)
    return "成功"

async def fail_task():
    await asyncio.sleep(0.5)
    raise ValueError("失败了")

async def main():
    # 在这里编写 gather 代码
    pass

asyncio.run(main())
```

---

## 🚀 进阶挑战题

### 挑战 1：异步生产者-消费者模型

使用 `asyncio.Queue` 实现一个生产者-消费者模型：
- 生产者：每 0.5 秒产生一个数据项，共产生 10 个
- 消费者：3 个消费者并发消费，每个处理耗时 1 秒
- 打印每个数据项被哪个消费者处理

提示：使用 `asyncio.create_task()` 同时运行生产者和消费者。

### 挑战 2：异步超时重试装饰器

编写一个装饰器 `@async_retry(max_retries=3, timeout=2.0)`，实现：
- 自动重试失败的协程
- 每次重试使用指数退避（1s, 2s, 4s...）
- 超过最大重试次数后抛出异常
- 支持超时控制

### 挑战 3：并发爬虫进度条

编写一个异步爬虫，支持：
- 并发请求多个 URL
- 实时显示进度（已完成/总数）
- 支持暂停和恢复
- 使用 `asyncio.Semaphore` 限制并发数为 5

---

## 💡 参考答案提示

<details>
<summary>练习 1 提示</summary>

```python
async def async_counter(n):
    for i in range(1, n + 1):
        print(i)
        await asyncio.sleep(0.5)
```
</details>

<details>
<summary>练习 2 提示</summary>

```python
async def main():
    start = time.time()
    tasks = [download_file(i) for i in range(5)]
    files = await asyncio.gather(*tasks)
    elapsed = time.time() - start
    print(f"总耗时: {elapsed:.1f}s")  # 应该约 3 秒，不是 10 秒
```
</details>

<details>
<summary>练习 3 提示</summary>

```python
async def main():
    results = await asyncio.gather(
        success_task(), fail_task(), success_task(),
        return_exceptions=True
    )
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f"任务 {i}: 失败 - {r}")
        else:
            print(f"任务 {i}: 成功 - {r}")
```
</details>
