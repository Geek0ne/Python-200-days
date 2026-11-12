# Day 057 — asyncio 进阶

> **阶段**：Phase 4 — 高阶特性  
> **主题**：异步上下文管理器、异步迭代器与生成器、aiohttp 实战、异步 API 调用  
> **预计学习时间**：3~4 小时

---

## 📋 今日学习目标

| 序号 | 目标 | 掌握程度 |
|------|------|----------|
| 1 | 理解异步上下文管理器的原理与实现 | ⭐⭐⭐⭐ |
| 2 | 掌握异步迭代器与异步生成器 | ⭐⭐⭐⭐ |
| 3 | 使用 aiohttp 进行异步 HTTP 请求 | ⭐⭐⭐⭐⭐ |
| 4 | 构建完整的异步 API 调用系统 | ⭐⭐⭐⭐⭐ |

---

## 一、异步上下文管理器

### 1.1 什么是异步上下文管理器

异步上下文管理器是 `__aenter__` 和 `__aexit__` 方法的组合，用于在 `async with` 语句中管理异步资源的生命周期。

**与同步上下文管理器的区别**：

| 特性 | 同步上下文管理器 | 异步上下文管理器 |
|------|-----------------|-----------------|
| 语法 | `with` | `async with` |
| 方法 | `__enter__` / `__exit__` | `__aenter__` / `__aexit__` |
| 方法类型 | 普通方法 | 协程方法（async） |
| 返回值 | `__enter__` 返回值 | `__aenter__` 返回 awaitable |
| 适用场景 | 文件、锁、数据库连接 | 网络连接、异步数据库、WebSocket |

### 1.2 为什么需要异步上下文管理器

**场景**：异步数据库连接池、网络 Socket、WebSocket 连接等资源需要：
1. 异步建立连接（避免阻塞事件循环）
2. 保证异常时正确释放资源
3. 在 `async with` 块结束后自动清理

**设计原理**：
- `__aenter__` 在进入 `async with` 块时被调用，返回值绑定到 `as` 变量
- `__aexit__` 在退出块时被调用（无论是否发生异常），负责清理资源
- 异步版本允许在资源管理过程中执行 `await`，不阻塞事件循环

### 1.3 实现异步上下文管理器

#### 方式一：基于类的实现

```python
import asyncio


class AsyncDatabaseConnection:
    """异步数据库连接（模拟）"""

    def __init__(self, db_name: str):
        self.db_name = db_name
        self.connection = None

    async def __aenter__(self):
        """异步进入上下文 — 建立连接"""
        print(f"🔌 正在连接数据库 {self.db_name}...")
        await asyncio.sleep(0.5)  # 模拟异步连接
        self.connection = {"db": self.db_name, "status": "connected"}
        print(f"✅ 数据库 {self.db_name} 已连接")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步退出上下文 — 释放连接"""
        print(f"🔌 正在断开数据库 {self.db_name}...")
        await asyncio.sleep(0.2)  # 模拟异步关闭
        self.connection = None
        print(f"✅ 数据库 {self.db_name} 已断开")
        # 返回 False 表示不抑制异常
        return False

    async def query(self, sql: str) -> dict:
        """模拟异步查询"""
        if not self.connection:
            raise RuntimeError("数据库未连接")
        await asyncio.sleep(0.1)  # 模拟异步查询
        return {"sql": sql, "result": f"查询结果 for {sql}"}


async def main():
    async with AsyncDatabaseConnection("mydb") as db:
        result = await db.query("SELECT * FROM users")
        print(f"查询结果: {result}")
    print("连接已自动释放")


asyncio.run(main())
```

**输出**：
```
🔌 正在连接数据库 mydb...
✅ 数据库 mydb 已连接
查询结果: {'sql': 'SELECT * FROM users', 'result': '查询结果 for SELECT * FROM users'}
🔌 正在断开数据库 mydb...
✅ 数据库 mydb 已断开
连接已自动释放
```

#### 方式二：基于 `asynccontextmanager` 装饰器

```python
import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def async_file_handler(filename: str):
    """异步文件处理器（模拟异步文件操作）"""
    print(f"📂 打开文件 {filename}")
    await asyncio.sleep(0.1)  # 模拟异步打开
    file_obj = {"name": filename, "content": "", "is_open": True}

    try:
        yield file_obj  # 将资源交给使用方
    except Exception as e:
        print(f"⚠️ 发生异常: {e}")
        raise
    finally:
        print(f"📂 关闭文件 {filename}")
        await asyncio.sleep(0.1)  # 模拟异步关闭
        file_obj["is_open"] = False


async def main():
    async with async_file_handler("data.txt") as f:
        f["content"] = "Hello, async world!"
        print(f"文件内容: {f['content']}")

    print(f"文件状态: {f['is_open']}")


asyncio.run(main())
```

**输出**：
```
📂 打开文件 data.txt
文件内容: Hello, async world!
📂 关闭文件 data.txt
文件状态: False
```

### 1.4 异步上下文管理器的异常处理

```python
import asyncio
from contextlib import asynccontextmanager


@asynccontextmanager
async def risky_resource(name: str):
    """一个可能出错的异步资源"""
    print(f"🔒 获取资源 {name}")
    await asyncio.sleep(0.1)
    resource = {"name": name, "active": True}

    try:
        yield resource
    except ValueError as e:
        # 捕获特定异常，记录日志，然后重新抛出
        print(f"❌ 资源 {name} 出错: {e}")
        resource["active"] = False
        raise  # 重新抛出异常
    finally:
        # 无论如何都会执行 — 清理资源
        resource["active"] = False
        print(f"🔓 释放资源 {name}")


async def main():
    # 情况1：正常退出
    async with risky_resource("res1") as r:
        print(f"使用 {r['name']}，状态: {r['active']}")

    print("---")

    # 情况2：异常退出
    try:
        async with risky_resource("res2") as r:
            print(f"使用 {r['name']}，状态: {r['active']}")
            raise ValueError("处理出错！")
    except ValueError as e:
        print(f"捕获到异常: {e}")


asyncio.run(main())
```

**输出**：
```
🔒 获取资源 res1
使用 res1，状态: True
🔓 释放资源 res1
---
🔒 获取资源 res2
使用 res2，状态: True
❌ 资源 res2 出错: 处理出错！
🔓 释放资源 res2
捕获到异常: 处理出错！
```

### 1.5 异步上下文管理器 API 速查

| 方法 | 签名 | 说明 |
|------|------|------|
| `__aenter__` | `async def __aenter__(self)` | 进入上下文，返回资源 |
| `__aexit__` | `async def __aexit__(self, exc_type, exc_val, exc_tb)` | 退出上下文，处理清理 |
| `asynccontextmanager` | `@asynccontextmanager` | 装饰器，简化异步上下文管理器创建 |
| `async_exit_stack` | `AsyncExitStack()` | 管理多个异步上下文管理器 |

---

## 二、异步迭代器与异步生成器

### 2.1 异步迭代器

异步迭代器实现了 `__aiter__` 和 `__anext__` 方法，允许在 `async for` 循环中逐个获取元素。

**为什么需要异步迭代器？**

普通迭代器在 `__next__` 中无法执行 I/O 操作（会阻塞事件循环）。异步迭代器的 `__anext__` 是协程，可以 `await` I/O 操作。

**对比**：

| 特性 | 同步迭代器 | 异步迭代器 |
|------|-----------|-----------|
| 协议 | `__iter__` / `__next__` | `__aiter__` / `__anext__` |
| 循环 | `for` | `async for` |
| next 返回 | 值或 raise StopIteration | await 值或 raise StopAsyncIteration |
| 适用场景 | 内存数据遍历 | 异步数据流、网络数据、数据库游标 |

### 2.2 实现异步迭代器

```python
import asyncio


class AsyncRange:
    """异步 Range — 模拟异步数据源"""

    def __init__(self, start: int, end: int, delay: float = 0.1):
        self.start = start
        self.end = end
        self.current = start
        self.delay = delay

    def __aiter__(self):
        """返回异步迭代器自身"""
        return self

    async def __anext__(self):
        """返回下一个值（模拟异步获取）"""
        if self.current >= self.end:
            raise StopAsyncIteration

        await asyncio.sleep(self.delay)  # 模拟异步 I/O
        value = self.current
        self.current += 1
        return value


async def main():
    print("异步迭代 0~4:")
    async for num in AsyncRange(0, 5, delay=0.05):
        print(f"  获取到: {num}")

asyncio.run(main())
```

**输出**：
```
异步迭代 0~4:
  获取到: 0
  获取到: 1
  获取到: 2
  获取到: 3
  获取到: 4
```

### 2.3 异步生成器

异步生成器结合了 `async def` 和 `yield`，既可使用 `await`，也可使用 `yield`。它是最常用的异步数据流处理方式。

**语法**：

```python
async def async_generator():
    yield value  # 生成值
    await something  # 执行异步操作
    yield another_value
```

**为什么不用 `asyncio.Queue`？**

| 方式 | 优点 | 缺点 |
|------|------|------|
| 异步生成器 | 语法简洁，按需生成 | 单消费者，无法多消费者共享 |
| `asyncio.Queue` | 支持多消费者，可设置最大容量 | 代码略复杂 |

### 2.4 实战：异步生成器数据流

```python
import asyncio
from typing import AsyncGenerator


async def fetch_page(page: int) -> dict:
    """模拟异步 API 请求"""
    await asyncio.sleep(0.2)  # 模拟网络延迟
    return {
        "page": page,
        "data": [f"item-{page}-{i}" for i in range(5)]
    }


async def paginated_fetch(total_pages: int = 5) -> AsyncGenerator[dict, None]:
    """分页异步生成器 — 逐页获取数据"""
    for page in range(1, total_pages + 1):
        result = await fetch_page(page)
        yield result
        print(f"  ✅ 第 {page} 页获取完成")


async def main():
    print("📦 分页数据获取:")
    async for page_data in paginated_fetch(3):
        items = page_data["data"]
        print(f"  📄 第 {page_data['page']} 页: {items[:2]}...")

asyncio.run(main())
```

### 2.5 异步生成器表达式

```python
import asyncio


async def async_square(n: int) -> int:
    await asyncio.sleep(0.05)
    return n * n


async def main():
    # 异步生成器表达式
    squares = [await async_square(i) for i in range(5)]
    print(f"列表推导式结果: {squares}")

    # 等价的异步生成器函数
    async def gen():
        for i in range(5):
            yield await async_square(i)

    print("异步生成器遍历:")
    async for val in gen():
        print(f"  {val}", end=" ")
    print()

asyncio.run(main())
```

### 2.6 异步迭代器 API 速查

| 方法/语法 | 说明 | 示例 |
|-----------|------|------|
| `async for` | 异步迭代循环 | `async for item in async_iter:` |
| `__aiter__` | 返回异步迭代器 | `def __aiter__(self):` |
| `__anext__` | 返回下一个值 | `async def __anext__(self):` |
| `StopAsyncIteration` | 停止迭代异常 | `raise StopAsyncIteration` |
| `async def ... yield` | 异步生成器 | `async def gen(): yield await ...` |
| `[expr async for ...]` | 异步推导式 | `[await f(x) async for x in gen()]` |
| `{expr async for ...}` | 异步集合推导式 | `{await f(x) async for x in gen()}` |

---

## 三、aiohttp 实战

### 3.1 什么是 aiohttp

aiohttp 是基于 asyncio 的异步 HTTP 客户端/服务器框架，提供：
- **客户端**：异步 HTTP 请求（GET/POST/PUT/DELETE）
- **服务器**：异步 Web 服务器
- 连接池管理
- WebSocket 支持

**为什么用 aiohttp 而不是 requests？**

| 特性 | requests | aiohttp |
|------|----------|---------|
| 执行模式 | 同步阻塞 | 异步非阻塞 |
| 并发能力 | 单个请求 | 同时发起大量请求 |
| 性能（高并发） | 串行，慢 | 并行，快 |
| 学习曲线 | 简单 | 中等 |
| 适用场景 | 单次请求、脚本 | 批量请求、爬虫、API 客户端 |

### 3.2 安装与基础用法

```bash
pip install aiohttp
```

```python
import asyncio
import aiohttp


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    """使用 aiohttp 发送 GET 请求"""
    async with session.get(url) as response:
        print(f"  URL: {url}")
        print(f"  状态码: {response.status}")
        print(f"  Content-Type: {response.headers.get('Content-Type')}")
        text = await response.text()
        return text


async def main():
    async with aiohttp.ClientSession() as session:
        # 单个请求
        html = await fetch(session, "https://httpbin.org/get")
        print(f"  响应长度: {len(html)} 字符\n")

        # 并发请求
        urls = [
            "https://httpbin.org/get",
            "https://httpbin.org/ip",
            "https://httpbin.org/user-agent",
        ]
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        print(f"  并发请求完成，共 {len(results)} 个响应")


asyncio.run(main())
```

### 3.3 aiohttp 核心 API

| 类/方法 | 说明 |
|---------|------|
| `aiohttp.ClientSession()` | 会话管理器，管理连接池 |
| `session.get(url)` | GET 请求 |
| `session.post(url, data=...)` | POST 请求 |
| `session.put(url, json=...)` | PUT 请求 |
| `session.delete(url)` | DELETE 请求 |
| `session.request(method, url)` | 通用请求 |
| `response.status` | HTTP 状态码 |
| `response.headers` | 响应头 |
| `response.text()` | 获取文本响应 |
| `response.json()` | 获取 JSON 响应 |
| `response.read()` | 获取原始字节响应 |

### 3.4 aiohttp 会话管理最佳实践

```python
import asyncio
import aiohttp


class APIClient:
    """异步 API 客户端 — 推荐的会话管理模式"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            base_url=self.base_url,
            headers={"User-Agent": "MyApp/1.0"},
            timeout=aiohttp.ClientTimeout(total=30),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get(self, path: str, **kwargs) -> dict:
        async with self.session.get(path, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def post(self, path: str, **kwargs) -> dict:
        async with self.session.post(path, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()


async def main():
    async with APIClient("https://httpbin.org") as client:
        # GET 请求
        data = await client.get("/get?name=test")
        print(f"GET 响应: {data.get('args')}")

        # POST 请求
        result = await client.post("/post", json={"key": "value"})
        print(f"POST 响应: {result.get('json')}")

asyncio.run(main())
```

### 3.5 并发请求与速率控制

```python
import asyncio
import aiohttp
import time


async def fetch_with_semaphore(
    sem: asyncio.Semaphore,
    session: aiohttp.ClientSession,
    url: str
) -> dict:
    """带并发控制的请求"""
    async with sem:  # 限制并发数
        async with session.get(url) as resp:
            data = await resp.json()
            return {"url": url, "status": resp.status, "data": data}


async def main():
    urls = [f"https://httpbin.org/get?page={i}" for i in range(10)]

    # 限制最大并发为 3
    semaphore = asyncio.Semaphore(3)

    start = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_semaphore(semaphore, session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    elapsed = time.perf_counter() - start
    print(f"✅ 10 个请求完成，耗时 {elapsed:.2f}s")
    print(f"   最大并发: 3，实际顺序执行约 3 批")
    for r in results[:3]:
        print(f"   {r['url']} → {r['status']}")

asyncio.run(main())
```

---

## 四、实战：异步 API 调用系统

### 4.1 完整的异步 API 调用框架

```python
import asyncio
import aiohttp
import time
import json
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


@dataclass
class APIRequest:
    """API 请求定义"""
    method: HttpMethod
    path: str
    params: Optional[dict] = None
    data: Optional[dict] = None
    json_body: Optional[dict] = None
    headers: Optional[dict] = None


@dataclass
class APIResponse:
    """API 响应结果"""
    status: int
    data: Any
    elapsed: float
    url: str
    error: Optional[str] = None


@dataclass
class APIClientConfig:
    """API 客户端配置"""
    base_url: str
    max_concurrent: int = 10
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    headers: dict = field(default_factory=lambda: {"User-Agent": "AsyncAPIClient/1.0"})


class AsyncAPIClient:
    """异步 API 调用客户端"""

    def __init__(self, config: APIClientConfig):
        self.config = config
        self.session = None
        self.semaphore = None
        self.stats = {"total": 0, "success": 0, "failed": 0}

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            base_url=self.config.base_url,
            headers=self.config.headers,
            timeout=timeout,
        )
        self.semaphore = asyncio.Semaphore(self.config.max_concurrent)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _request_with_retry(self, req: APIRequest) -> APIResponse:
        """带重试的请求"""
        url = req.path
        last_error = None

        for attempt in range(self.config.retry_count):
            try:
                async with self.semaphore:
                    start = time.perf_counter()
                    async with self.session.request(
                        method=req.method.value,
                        url=url,
                        params=req.params,
                        data=req.data,
                        json=req.json_body,
                        headers=req.headers,
                    ) as resp:
                        elapsed = time.perf_counter() - start
                        if resp.status >= 400:
                            error_text = await resp.text()
                            return APIResponse(
                                status=resp.status,
                                data=None,
                                elapsed=elapsed,
                                url=url,
                                error=error_text,
                            )
                        data = await resp.json()
                        return APIResponse(
                            status=resp.status,
                            data=data,
                            elapsed=elapsed,
                            url=url,
                        )
            except aiohttp.ClientError as e:
                last_error = str(e)
                if attempt < self.config.retry_count - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))

        return APIResponse(
            status=0,
            data=None,
            elapsed=0,
            url=url,
            error=f"重试 {self.config.retry_count} 次后失败: {last_error}",
        )

    async def execute(self, request: APIRequest) -> APIResponse:
        """执行单个请求"""
        self.stats["total"] += 1
        response = await self._request_with_retry(request)
        if response.error:
            self.stats["failed"] += 1
        else:
            self.stats["success"] += 1
        return response

    async def batch_execute(self, requests: list[APIRequest]) -> list[APIResponse]:
        """批量并发执行请求"""
        tasks = [self.execute(req) for req in requests]
        return await asyncio.gather(*tasks)

    def get_stats(self) -> dict:
        return self.stats.copy()


async def main():
    """实战：异步 API 调用"""
    config = APIClientConfig(
        base_url="https://httpbin.org",
        max_concurrent=5,
        timeout=10,
        retry_count=2,
    )

    async with AsyncAPIClient(config) as client:
        # 1. 单个请求
        print("=== 单个请求 ===")
        req = APIRequest(method=HttpMethod.GET, path="/get", params={"q": "python"})
        resp = await client.execute(req)
        print(f"  状态: {resp.status}, 耗时: {resp.elapsed:.3f}s")

        # 2. 批量并发请求
        print("\n=== 批量并发请求 ===")
        batch = [
            APIRequest(method=HttpMethod.GET, path="/get", params={"id": i})
            for i in range(8)
        ]
        start = time.perf_counter()
        results = await client.batch_execute(batch)
        elapsed = time.perf_counter() - start

        print(f"  完成 {len(results)} 个请求，总耗时: {elapsed:.2f}s")
        print(f"  成功率: {sum(1 for r in results if not r.error)}/{len(results)}")

        # 3. POST 请求
        print("\n=== POST 请求 ===")
        post_req = APIRequest(
            method=HttpMethod.POST,
            path="/post",
            json_body={"user": "聂董", "action": "learn_python"},
        )
        post_resp = await client.execute(post_req)
        print(f"  状态: {post_resp.status}")
        print(f"  回显: {post_resp.data.get('json', {})}")

        # 4. 统计
        stats = client.get_stats()
        print(f"\n=== 统计 ===")
        print(f"  总请求: {stats['total']}")
        print(f"  成功: {stats['success']}")
        print(f"  失败: {stats['failed']}")


asyncio.run(main())
```

### 4.2 流式处理异步数据

```python
import asyncio
import aiohttp
from typing import AsyncGenerator


async def stream_response(
    session: aiohttp.ClientSession,
    url: str,
) -> AsyncGenerator[str, None]:
    """流式读取响应"""
    async with session.get(url) as resp:
        async for line in resp.content:
            yield line.decode("utf-8")


async def process_stream():
    """处理流式数据"""
    async with aiohttp.ClientSession() as session:
        url = "https://httpbin.org/stream/5"
        print("📡 流式数据接收:")
        count = 0
        async for chunk in stream_response(session, url):
            count += 1
            data = chunk.strip()
            if data:
                print(f"  📦 片段 {count}: {data[:80]}...")

asyncio.run(process_stream())
```

---

## 五、异步编程避坑指南

### 5.1 常见陷阱

```python
import asyncio
import aiohttp


async def main():
    # ❌ 陷阱1：忘记 await
    # session.get(url)  # 返回协程，不是响应！
    # ✅ 正确：
    # async with session.get(url) as resp: ...

    # ❌ 陷阱2：在异步上下文管理器外使用 session
    # session = aiohttp.ClientSession()
    # await session.get(url)  # session 可能已关闭
    # ✅ 正确：始终用 async with

    # ❌ 陷阱3：在同步函数中使用异步代码
    # def sync_func():
    #     await some_async_func()  # SyntaxError!
    # ✅ 正确：在 async 函数中使用，或用 asyncio.run()

    # ❌ 陷阱4：阻塞事件循环
    # async with session.get(url) as resp:
    #     time.sleep(5)  # 阻塞！
    # ✅ 正确：await asyncio.sleep(5)

    # ❌ 陷阱5：不处理异常
    # async with session.get(url) as resp:
    #     data = await resp.json()  # 可能抛异常
    # ✅ 正确：用 try/except 或 resp.raise_for_status()

    print("✅ 已了解常见陷阱")

asyncio.run(main())
```

### 5.2 错误处理最佳实践

```python
import asyncio
import aiohttp
from aiohttp import ClientTimeout


async def safe_request(
    session: aiohttp.ClientSession,
    url: str,
    retries: int = 3,
) -> dict:
    """安全的异步请求，带重试和超时"""
    last_error = None

    for attempt in range(retries):
        try:
            timeout = ClientTimeout(total=10)
            async with session.get(url, timeout=timeout) as resp:
                resp.raise_for_status()
                return {"status": resp.status, "data": await resp.json()}
        except aiohttp.ClientTimeout:
            last_error = "请求超时"
        except aiohttp.ClientResponseError as e:
            last_error = f"HTTP 错误: {e.status}"
        except aiohttp.ClientError as e:
            last_error = f"连接错误: {e}"
        except Exception as e:
            last_error = f"未知错误: {e}"

        if attempt < retries - 1:
            delay = 2 ** attempt  # 指数退避
            print(f"  ⚠️ 重试 {attempt + 1}/{retries}，等待 {delay}s...")
            await asyncio.sleep(delay)

    return {"status": 0, "error": last_error}


async def main():
    async with aiohttp.ClientSession() as session:
        result = await safe_request(session, "https://httpbin.org/get")
        print(f"结果: {result.get('status')}")

asyncio.run(main())
```

---

## 六、图解

### 6.1 异步上下文管理器执行流程

```
┌─────────────────────────────────────────────────────────┐
│              async with Resource() as res:               │
│                     │                                    │
│                     ▼                                    │
│         ┌─────────────────────┐                          │
│         │  await __aenter__() │  ← 进入上下文             │
│         └─────────┬───────────┘                          │
│                   │                                      │
│                   ▼                                      │
│         ┌─────────────────────┐                          │
│         │   执行 async with   │  ← 使用资源               │
│         │       块内的代码     │                          │
│         └─────────┬───────────┘                          │
│                   │                                      │
│          ┌────────┴────────┐                              │
│          │  正常/异常退出   │                              │
│          └────────┬────────┘                              │
│                   │                                      │
│                   ▼                                      │
│         ┌─────────────────────┐                          │
│         │  await __aexit__()  │  ← 清理资源               │
│         └─────────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

### 6.2 aiohttp 并发请求模型

```
           事件循环 (Event Loop)
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐ ┌────────┐ ┌────────┐
│ Task 1 │ │ Task 2 │ │ Task 3 │   ← 协程任务
└───┬────┘ └───┬────┘ └───┬────┘
    │          │          │
    ▼          ▼          ▼
┌────────────────────────────────┐
│     aiohttp 连接池             │
│  ┌─────┐ ┌─────┐ ┌─────┐     │
│  │Conn1│ │Conn2│ │Conn3│     │   ← 复用 TCP 连接
│  └──┬──┘ └──┬──┘ └──┬──┘     │
└─────┼───────┼───────┼─────────┘
      │       │       │
      ▼       ▼       ▼
   Server1 Server2 Server3     ← 目标服务器
```

### 6.3 异步数据流处理

```
异步生成器                    消费者
    │                          │
    │  yield data              │
    ├─────────────────────►   async for
    │                          │
    │  await fetch_next()      │  处理 data
    │                          │
    │  yield data              │
    ├─────────────────────►   async for
    │                          │
    │  StopAsyncIteration      │  循环结束
    └─────────────────────►   退出
```

---

## 七、思考题

1. **异步上下文管理器 vs `try/finally`**：异步上下文管理器的 `__aexit__` 在异常时也会执行。如果只用 `try/finally` 能实现同样效果吗？异步上下文管理器有什么独特优势？

**参考答案**

能。`async with` 本质上就是「调用 `__aenter__` → 执行块 → 无论正常还是异常都调用 `__aexit__`」的语法糖，用 `try/finally` 手动调用清理逻辑，可以达到同样的「异常时也释放资源」效果。但异步上下文管理器有几点独特优势：

- **封装与复用**：把「获取资源」和「释放资源」打包进一个类（或 `@asynccontextmanager` 函数），写一次就能到处用；`try/finally` 则要在每个使用点重复写获取/释放，容易漏写或写错顺序。
- **可抑制异常**：`__aexit__` 返回 `True` 时能把块内异常「吞掉」让程序继续，这是 `try/finally` 做不到的（`finally` 只负责清理，不能阻止异常传播）。
- **可组合**：用 `contextlib.AsyncExitStack` 能动态管理多个异步资源，退出时统一逆序释放。
- **可读性**：`async with conn:` 一眼就能看出「这里管理着一个需要释放的资源」。

```python
import asyncio


class AsyncConn:
    """把“建立连接/释放连接”封装成可复用的异步上下文管理器"""

    def __init__(self, name):
        self.name = name
        self.is_open = False

    async def __aenter__(self):
        await asyncio.sleep(0.01)      # 模拟异步建立连接
        self.is_open = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.sleep(0.01)      # 模拟异步释放连接
        self.is_open = False
        print(f"{self.name} 已释放（块内是否有异常: {exc_type is not None}）")
        return False                   # False=不抑制异常，异常照常向外抛


async def main():
    conn = AsyncConn("数据库连接")
    try:
        async with conn:               # 块内抛异常，__aexit__ 依然执行
            raise ValueError("处理出错")
    except ValueError:
        pass
    print("is_open =", conn.is_open)   # False，资源已释放

    # 独特优势：__aexit__ 返回 True 可“抑制”异常，try/finally 做不到
    class Ignorer:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return True                # True=吞掉异常，程序继续往下走

    async with Ignorer():
        raise RuntimeError("这个异常会被抑制")
    print("抑制异常后，程序继续执行")


asyncio.run(main())
```

运行输出：

```
数据库连接 已释放（块内是否有异常: True）
is_open = False
抑制异常后，程序继续执行
```

可见异常发生时连接仍被释放；而 `Ignorer` 的 `__aexit__` 返回 `True` 后，`RuntimeError` 被抑制、程序继续执行——这是纯 `try/finally` 无法实现的。

💡 提示：`@contextlib.asynccontextmanager` 能用「生成器 + yield」的写法快速创建异步上下文管理器，`yield` 之前相当于 `__aenter__`、之后（放在 `finally` 里）相当于 `__aexit__`。

2. **异步生成器的内存优势**：假设有 100 万条数据库记录需要处理。对比列表推导式和异步生成器，分析内存使用差异和适用场景。

**参考答案**

两者处理的数据量相同，但内存占用天差地别：

- **列表推导式** `[await fetch(i) for i in range(1_000_000)]` 会一次性把 100 万条记录全部读进内存，峰值内存随数据量线性增长（O(n)）。实测约 60 MB，真实数据库记录字段更多会更大，数据量再大就可能撑爆内存。
- **异步生成器** `async for r in record_stream()` 是「惰性」的：取一条、处理一条、再取下一条，同一时刻内存里基本只有一条记录，峰值内存近似常数（O(1)），实测不到 1 KB。

适用场景：

- 用**列表**：数据量小、需要随机访问 / 多次遍历 / `len()` / 切片，或要一次性拿到全部结果。
- 用**异步生成器**：海量数据流、分页拉取、ETL、日志处理等「边取边处理」的管道场景，尤其是内存受限、又需要在取数据时 `await` 异步 I/O 的情况。

```python
import asyncio
import tracemalloc

N = 1_000_000


async def fetch_record(i: int) -> str:
    """模拟从数据库异步取一条记录"""
    return f"record-{i}"


async def record_stream():
    """异步生成器：取一条 yield 一条，内存里只留当前记录"""
    for i in range(N):
        yield await fetch_record(i)


async def main():
    # 方式一：列表推导式，一次性全部载入内存
    tracemalloc.start()
    records = [await fetch_record(i) for i in range(N)]
    total1 = sum(len(r) for r in records)
    _, peak1 = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    del records
    print(f"列表推导式: 峰值内存 {peak1 / 1024 / 1024:.1f} MB")

    # 方式二：异步生成器，流式处理
    tracemalloc.start()
    total2 = 0
    async for r in record_stream():
        total2 += len(r)
    _, peak2 = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"异步生成器: 峰值内存 {peak2 / 1024:.1f} KB")
    print(f"处理结果一致: {total1 == total2}")


asyncio.run(main())
```

运行输出（内存数值随环境略有浮动，运行需数秒）：

```
列表推导式: 峰值内存 59.5 MB
异步生成器: 峰值内存 0.8 KB
处理结果一致: True
```

两者结果完全一致，但峰值内存相差约 7 万倍。

⚠️ 注意：内存优势来自「惰性求值」，同步生成器同样具备；异步生成器的额外价值是能在惰性求值的同时 `await` 异步 I/O。另外异步生成器是单消费者的，若要多个消费者共享数据流，应改用 `asyncio.Queue`。

3. **Semaphore vs 连接池**：在 aiohttp 中，`asyncio.Semaphore` 和 `aiohttp.TCPConnector(limit=...)` 都能限制并发，它们有什么区别？什么场景下应该同时使用两者？

**参考答案**

两者都能「限并发」，但作用的层次和范围不同：

- **`asyncio.Semaphore(n)`** 是通用的异步同步原语，限制「同时进入某段代码」的协程数量。它是应用层逻辑，和网络无关，可以跨多个会话共享，也能限制非网络操作（如同时写文件的数量）。
- **`aiohttp.TCPConnector(limit=n)`** 限制的是这个连接池里「同时活跃的 TCP 连接数」，属于传输层。超出的请求会排队等待空闲连接，连接支持 keep-alive 复用；还有 `limit_per_host` 可单独限制每个主机的连接数。关键：`limit` 是**每个 connector（会话）独立**的。

下面在本地起一个每请求耗时 0.2s 的服务，发 10 个请求实测区别：

```python
import asyncio
import time

import aiohttp
from aiohttp import web


async def handler(request):
    await asyncio.sleep(0.2)           # 每个请求耗时 0.2s
    return web.json_response({"ok": True})


async def fetch(session, i, sem=None):
    if sem is not None:
        async with sem:                # 信号量：限制同时进入这段代码的协程数
            async with session.get("/") as resp:
                return await resp.json()
    async with session.get("/") as resp:
        return await resp.json()


async def timed(factory, n):
    t0 = time.perf_counter()
    await asyncio.gather(*[factory(i) for i in range(n)])
    return time.perf_counter() - t0


async def main():
    # 本地起一个 aiohttp 服务器，无需外网即可实测
    app = web.Application()
    app.router.add_get("/", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 18766)
    await site.start()
    url = "http://127.0.0.1:18766"

    # A：单会话 + 连接池 limit=2 → 10 个请求分 5 批，约 1.0s
    async with aiohttp.ClientSession(
        base_url=url, connector=aiohttp.TCPConnector(limit=2)
    ) as s:
        t = await timed(lambda i: fetch(s, i), 10)
        print(f"A 单会话连接池 limit=2: {t:.2f}s")

    # B：两个会话各 limit=2 → 连接池各自独立，总并发 4，约 0.6s
    async with aiohttp.ClientSession(
        base_url=url, connector=aiohttp.TCPConnector(limit=2)
    ) as s1, aiohttp.ClientSession(
        base_url=url, connector=aiohttp.TCPConnector(limit=2)
    ) as s2:
        t = await timed(lambda i: fetch(s1 if i % 2 == 0 else s2, i), 10)
        print(f"B 两个会话各 limit=2: {t:.2f}s")

    # C：两个会话 + 共享 Semaphore(2) → 跨会话全局并发 2，约 1.0s
    sem = asyncio.Semaphore(2)
    async with aiohttp.ClientSession(base_url=url) as s1, \
            aiohttp.ClientSession(base_url=url) as s2:
        t = await timed(lambda i: fetch(s1 if i % 2 == 0 else s2, i, sem), 10)
        print(f"C 两个会话+共享 Semaphore(2): {t:.2f}s")

    await runner.cleanup()


asyncio.run(main())
```

运行输出（耗时随环境略有浮动）：

```
A 单会话连接池 limit=2: 1.02s
B 两个会话各 limit=2: 0.65s
C 两个会话+共享 Semaphore(2): 1.03s
```

B 比 A 快，说明两个会话的连接池 `limit` 各算各的（总并发变成 4）；C 用共享信号量把跨会话的总并发又压回 2。

**何时同时用两者**：比如爬虫要同时访问很多站点——用共享 `Semaphore` 控制「全局总并发」保护本机资源，再用每个会话的 `TCPConnector(limit_per_host=...)` 控制「对单个站点的连接数」避免把对方打挂。一个管全局任务数、一个管单主机连接数，正好互补。

💡 提示：本题代码用到当天主题库 aiohttp，需先 `pip install aiohttp`。

4. **错误处理策略**：在批量 API 调用中，如果 10 个请求中有 2 个失败，应该使用 `asyncio.gather(return_exceptions=True)` 还是让整个 batch 失败？各有什么优缺点？

**参考答案**

两种策略对应两种语义，批量 API 调用通常推荐 `return_exceptions=True`：

- **默认 `gather`（`return_exceptions=False`）**：第一个异常会立刻抛给调用方，整个 batch「失败」。优点是快速失败、代码简单，适合「必须全部成功」的场景（如事务性操作）。缺点：① 一个失败就丢掉所有已成功的结果；② 其它已启动的任务**不会自动取消**，仍在后台跑，可能浪费资源或产生「异常未被取回」的警告。
- **`gather(return_exceptions=True)`**：异常被当作返回值（不抛出），所有任务都跑完，得到「8 个成功结果 + 2 个异常对象」。优点是保留部分成功、可对失败项单独重试/记录，适合批量爬虫、批量调用这类「尽力而为」的场景。缺点：要自己用 `isinstance(r, Exception)` 检查每个结果，容易漏判。

```python
import asyncio


async def call_api(i: int) -> str:
    await asyncio.sleep(0.05 * (i % 3))   # 模拟不同耗时
    if i in (3, 7):                        # 假设第 3、7 个请求失败
        raise ConnectionError(f"请求 {i} 失败")
    return f"结果-{i}"


async def main():
    # 策略一：默认 gather —— 第一个异常直接抛出
    try:
        await asyncio.gather(*[call_api(i) for i in range(10)])
    except ConnectionError as e:
        print(f"默认 gather: 捕获 {e}")
    await asyncio.sleep(0.3)               # 等后台剩余任务结束，避免警告

    # 策略二：return_exceptions=True —— 异常作为结果返回
    results = await asyncio.gather(
        *[call_api(i) for i in range(10)], return_exceptions=True
    )
    ok = [r for r in results if not isinstance(r, BaseException)]
    bad = [r for r in results if isinstance(r, BaseException)]
    print(f"return_exceptions=True: 成功 {len(ok)} 个, 失败 {len(bad)} 个")
    for e in bad:
        print(f"  失败原因: {e}")

    # 策略三（Python 3.11+）：TaskGroup —— 失败时自动取消兄弟任务
    try:
        async with asyncio.TaskGroup() as tg:
            for i in range(10):
                tg.create_task(call_api(i))
    except* ConnectionError as eg:
        print(f"TaskGroup: 捕获 {len(eg.exceptions)} 个 ConnectionError，其余任务已取消")


asyncio.run(main())
```

运行输出：

```
默认 gather: 捕获 请求 3 失败
return_exceptions=True: 成功 8 个, 失败 2 个
  失败原因: 请求 3 失败
  失败原因: 请求 7 失败
TaskGroup: 捕获 1 个 ConnectionError，其余任务已取消
```

结论：批量调用一般用 `return_exceptions=True` 保留部分成果，再统一处理失败；若确实要「一损俱损、立即止损」，用 Python 3.11+ 的 `asyncio.TaskGroup` 比默认 `gather` 更安全——它会自动取消兄弟任务，并把异常聚合成 `ExceptionGroup`（用 `except*` 捕获）。

⚠️ 注意：默认 `gather` 抛异常后，剩余任务不会自动取消；要么显式 `cancel()`，要么像示例那样等它们结束，否则可能出现 "Task exception was never retrieved" 警告。

5. **异步 vs 多线程**：在 I/O 密集型任务（如批量 HTTP 请求）中，asyncio 和多线程哪个性能更好？为什么？请从 GIL、上下文切换、资源消耗等角度分析。

**参考答案**

I/O 密集型任务里，**高并发时 asyncio 通常更好**，原因从三个角度看：

- **GIL**：纯 I/O 等待（socket、`sleep`）时线程也会释放 GIL，所以线程同样能并发 I/O；但线程在 CPU 计算部分仍受 GIL 限制，且多线程有锁竞争。asyncio 单线程运行，没有 GIL 争用和线程锁开销。
- **上下文切换**：线程切换是操作系统内核态的抢占式调度，每次切换有内核开销、可能污染缓存；协程切换是用户态协作式（只在 `await` 处让出），只需保存少量栈帧，开销小得多。
- **资源消耗**：每个线程要独立栈（默认 MB 级虚拟内存）+ 内核任务结构，几千个线程就会吃光内存、拖垮调度器；协程只是普通 Python 对象（几百字节~KB 级），单线程就能承载几十万个。

实测（200 个各耗时 0.05s 的 I/O 任务）：

```python
import asyncio
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

N = 200
DELAY = 0.05


def blocking_io(i: int) -> int:
    time.sleep(DELAY)        # 阻塞 I/O，会释放 GIL
    return i


async def async_io(i: int) -> int:
    await asyncio.sleep(DELAY)
    return i


async def main():
    # asyncio：200 个协程并发
    tracemalloc.start()
    t0 = time.perf_counter()
    r1 = await asyncio.gather(*[async_io(i) for i in range(N)])
    e1 = time.perf_counter() - t0
    _, peak1 = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"asyncio 200 协程: {e1:.2f}s, Python对象峰值 {peak1/1024:.0f}KB, 线程数 {threading.active_count()}")

    # 线程池：200 个线程
    tracemalloc.start()
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=N) as ex:
        r2 = list(ex.map(blocking_io, range(N)))
        n_threads = threading.active_count()
    e2 = time.perf_counter() - t0
    _, peak2 = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"线程池 200 线程: {e2:.2f}s, Python对象峰值 {peak2/1024:.0f}KB, 线程数 {n_threads}")

    # 线程池：只开 20 个线程 → 分 10 批串行
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=20) as ex:
        r3 = list(ex.map(blocking_io, range(N)))
    e3 = time.perf_counter() - t0
    print(f"线程池 20 线程: {e3:.2f}s (分 10 批)")
    print(f"三种方式结果一致: {r1 == r2 == r3 == list(range(N))}")


asyncio.run(main())
```

运行输出（耗时/内存随环境略有浮动）：

```
asyncio 200 协程: 0.06s, Python对象峰值 312KB, 线程数 1
线程池 200 线程: 0.08s, Python对象峰值 1001KB, 线程数 201
线程池 20 线程: 0.51s (分 10 批)
三种方式结果一致: True
```

分析：200 并发时两者耗时接近（0.06s vs 0.08s），但协程只用 1 个线程、Python 对象峰值更小（线程栈还没被 `tracemalloc` 统计，实际差距更大）；一旦把线程数压到 20，就得分 10 批、慢一个数量级，而协程轻松全并发。并发上万时线程方案会因内存和调度开销崩溃，asyncio 仍能胜任。

💡 提示：低并发（几十个）或代码库已全是阻塞库（如 `requests`、同步数据库驱动）时，线程池（或 `asyncio.to_thread`）往往比改写成异步更省事，性能差距也不大；CPU 密集型任务两者都不行，应改用多进程。

---

## 📚 扩展阅读

- [Python 官方文档 — asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiohttp 官方文档](https://docs.aiohttp.org/)
- [PEP 525 — 异步生成器](https://peps.python.org/pep-0525/)
- [PEP 526 — 异步上下文管理器](https://peps.python.org/pep-0526/)

---

> **明日预告**：Day 058 — 并发模型对比，线程 vs 进程 vs 协程的深度对比与基准测试。
