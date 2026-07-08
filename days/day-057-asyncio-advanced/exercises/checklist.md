# Day 057 — asyncio 进阶：完成清单与练习

## ✅ 今日完成清单

- [ ] 理解异步上下文管理器的 `__aenter__` / `__aexit__` 机制
- [ ] 掌握 `@asynccontextmanager` 装饰器的使用
- [ ] 理解异步迭代器的 `__aiter__` / `__anext__` 协议
- [ ] 掌握异步生成器的语法和使用场景
- [ ] 学会使用 aiohttp 发送异步 HTTP 请求
- [ ] 理解 aiohttp 会话管理和连接池
- [ ] 掌握 `asyncio.Semaphore` 控制并发
- [ ] 完成所有代码示例并运行验证
- [ ] 完成以下练习题

---

## 📝 基础练习

### 练习 1：异步文件管理器

实现一个异步上下文管理器 `AsyncFileManager`，模拟异步文件操作：

```python
async with AsyncFileManager("data.json") as f:
    await f.write('{"name": "test"}')
    content = await f.read()
    print(content)
# 自动关闭文件
```

要求：
- `__aenter__` 返回文件对象
- `__aexit__` 确保文件关闭
- 支持 `read()` 和 `write()` 异步方法

### 练习 2：异步生成器实现分页

实现一个异步生成器 `fetch_pages(url_template, total_pages)`：

```python
async for page_data in fetch_pages("https://api.example.com?page={}", 5):
    print(page_data)
```

要求：
- 每次 `yield` 返回一页数据
- 模拟网络延迟
- 页码从 1 开始

### 练习 3：异步迭代器实现倒计时

实现一个异步迭代器 `AsyncCountdown`，从 N 倒数到 0：

```python
async for remaining in AsyncCountdown(5):
    print(f"倒计时: {remaining}")
# 5, 4, 3, 2, 1, 0
```

要求：
- 每次倒数间隔 0.5 秒
- 实现 `__aiter__` 和 `__anext__`

---

## 🚀 进阶挑战

### 挑战 1：异步任务池

实现一个 `AsyncTaskPool`，支持：
- 添加异步任务
- 限制最大并发数
- 等待所有任务完成
- 获取每个任务的结果

```python
pool = AsyncTaskPool(max_workers=3)
pool.add_task(task1())
pool.add_task(task2())
pool.add_task(task3())
results = await pool.run_all()
```

### 挑战 2：异步缓存装饰器

实现一个异步缓存装饰器 `@async_cache(maxsize=128)`：

```python
@async_cache(maxsize=10)
async def expensive_api_call(user_id: int):
    await asyncio.sleep(1)  # 模拟慢查询
    return {"id": user_id, "data": "..."}

# 第一次调用：1秒
await expensive_api_call(1)
# 第二次调用：几乎瞬间（缓存命中）
await expensive_api_call(1)
```

要求：
- 支持 TTL（生存时间）
- 支持 LRU 淘汰
- 线程安全（使用 asyncio.Lock）

### 挑战 3：异步 Web 爬虫

使用 aiohttp 实现一个简单的异步爬虫：
- 从起始 URL 开始
- 提取页面中的链接
- 并发爬取（限制最大并发 5）
- 记录已访问的 URL（避免重复）
- 返回所有页面的标题

```python
crawler = AsyncCrawler(max_concurrent=5)
results = await crawler.crawl("https://example.com")
print(f"爬取了 {len(results)} 个页面")
```

---

## 📊 自我评估

完成后，评估自己对以下内容的掌握程度（1-5 分）：

| 知识点 | 自评 |
|--------|------|
| 异步上下文管理器原理 | ⭐⭐⭐⭐⭐ |
| 异步上下文管理器实现 | ⭐⭐⭐⭐⭐ |
| 异步迭代器协议 | ⭐⭐⭐⭐⭐ |
| 异步生成器使用 | ⭐⭐⭐⭐⭐ |
| aiohttp 基础请求 | ⭐⭐⭐⭐⭐ |
| 并发控制 (Semaphore) | ⭐⭐⭐⭐⭐ |
| 错误处理与重试 | ⭐⭐⭐⭐⭐ |

---

## 💡 提示

- 遇到问题可以先回顾 README.md 中的对应章节
- 运行代码示例时注意网络依赖（aiohttp 示例需要联网）
- 异步编程的核心：**不要阻塞事件循环**
