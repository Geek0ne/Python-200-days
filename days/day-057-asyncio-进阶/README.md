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

2. **异步生成器的内存优势**：假设有 100 万条数据库记录需要处理。对比列表推导式和异步生成器，分析内存使用差异和适用场景。

3. **Semaphore vs 连接池**：在 aiohttp 中，`asyncio.Semaphore` 和 `aiohttp.TCPConnector(limit=...)` 都能限制并发，它们有什么区别？什么场景下应该同时使用两者？

4. **错误处理策略**：在批量 API 调用中，如果 10 个请求中有 2 个失败，应该使用 `asyncio.gather(return_exceptions=True)` 还是让整个 batch 失败？各有什么优缺点？

5. **异步 vs 多线程**：在 I/O 密集型任务（如批量 HTTP 请求）中，asyncio 和多线程哪个性能更好？为什么？请从 GIL、上下文切换、资源消耗等角度分析。

---

## 📚 扩展阅读

- [Python 官方文档 — asyncio](https://docs.python.org/3/library/asyncio.html)
- [aiohttp 官方文档](https://docs.aiohttp.org/)
- [PEP 525 — 异步生成器](https://peps.python.org/pep-0525/)
- [PEP 526 — 异步上下文管理器](https://peps.python.org/pep-0526/)

---

> **明日预告**：Day 058 — 并发模型对比，线程 vs 进程 vs 协程的深度对比与基准测试。
