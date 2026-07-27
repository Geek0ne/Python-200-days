# Day 085 — WebSocket 通信

> 📅 2026-07-27 | 🎯 Phase 6: 实战项目 — 项目四：聊天机器人（1/3）

---

## 📋 今日学习目标

1. 理解 WebSocket 协议的工作原理与设计思想
2. 掌握 Python `websockets` 库的服务端与客户端开发
3. 学会处理并发连接、心跳检测、异常断开等实际问题
4. 能够构建一个基础的实时聊天室

---

## 1. WebSocket 是什么？

### 1.1 为什么需要 WebSocket？

传统的 HTTP 通信是**请求-响应**模式：

```
HTTP 轮询方式：

客户端                    服务器
  │                        │
  │── GET /data ──────────▶│
  │◀── Response ───────────│
  │                        │ ...等几秒...
  │── GET /data ──────────▶│
  │◀── Response ───────────│
  │                        │ ...再等几秒...
  │── GET /data ──────────▶│
  │◀── Response ───────────│
  │                        │
```

问题：
- **延迟高**：服务器有新数据时客户端不知道，必须等轮询周期
- **浪费带宽**：大量空请求消耗资源
- **服务器压力大**：频繁的连接建立与销毁开销大

WebSocket 解决了这些问题：

```
WebSocket 通信方式：

客户端                    服务器
  │                        │
  │── HTTP Upgrade ───────▶│  ← 握手阶段（仍然是HTTP）
  │◀── 101 Switching ──────│
  │                        │
  │═════ WebSocket 连接建立 ═════│  ← 持久化连接
  │                        │
  │◀═══ 数据推送 ═══════════│  ← 服务器可主动推送
  │◀═══ 数据推送 ═══════════│
  │═════ 双向通信 ══════════▶│  ← 客户端也可发送
  │◀═══ 数据推送 ═══════════│
  │                        │
```

### 1.2 WebSocket 与 HTTP 对比

| 特性 | HTTP | WebSocket |
|------|------|-----------|
| 通信模式 | 请求-响应 | 全双工 |
| 连接状态 | 无状态 | 有状态 |
| 服务器推送 | 不支持（需轮询） | 原生支持 |
| 数据格式 | 文本 | 文本 + 二进制 |
| 协议标识 | `http://` / `https://` | `ws://` / `wss://` |
| 连接开销 | 每次建立新连接 | 一次握手，持久连接 |
| 适用场景 | REST API、页面加载 | 聊天、实时推送、游戏 |

### 1.3 WebSocket 协议流程

```
┌────────────────────────────────────────────────────────────┐
│                   WebSocket 握手过程                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  客户端                                    服务器            │
│    │                                        │              │
│    │── HTTP GET /chat ─────────────────────▶│              │
│    │   Headers:                             │              │
│    │   Upgrade: websocket                   │              │
│    │   Connection: Upgrade                  │              │
│    │   Sec-WebSocket-Key: dGhl...           │              │
│    │                                        │              │
│    │◀── HTTP 101 Switching Protocols ───────│              │
│    │   Headers:                             │              │
│    │   Upgrade: websocket                   │              │
│    │   Connection: Upgrade                  │              │
│    │   Sec-WebSocket-Accept: s3pP...        │              │
│    │                                        │              │
│    │◄═════ WebSocket 帧传输开始 ════════════►│              │
│    │                                        │              │
└────────────────────────────────────────────────────────────┘
```

---

## 2. Python WebSocket 开发

### 2.1 安装 websockets 库

```bash
pip install websockets
```

### 2.2 服务端开发

#### 最简单的 WebSocket 服务

```python
import asyncio
import websockets

async def handler(websocket):
    """处理每个客户端连接"""
    async for message in websocket:
        print(f"收到消息: {message}")
        await websocket.send(f"回显: {message}")

async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # 永久运行

asyncio.run(main())
```

#### 核心 API 速查

| 方法/属性 | 说明 |
|-----------|------|
| `websockets.serve(handler, host, port)` | 启动 WebSocket 服务 |
| `websocket.send(data)` | 发送数据（文本或字节） |
| `async for msg in websocket` | 接收消息（异步迭代） |
| `websocket.close()` | 关闭连接 |
| `websocket.remote_addr` | 客户端地址 |
| `websocket.path` | 请求路径 |
| `websockets.connect(uri)` | 连接到服务器 |

### 2.3 客户端开发

```python
import asyncio
import websockets

async def client():
    async with websockets.connect("ws://localhost:8765") as ws:
        await ws.send("Hello!")
        response = await ws.recv()
        print(f"服务器回复: {response}")

asyncio.run(client())
```

---

## 3. 并发连接管理

### 3.1 多客户端同时在线

在聊天室场景中，需要同时维护多个客户端连接：

```python
# 存储所有已连接的客户端
connected_clients = set()

async def handler(websocket):
    # 注册新客户端
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # 广播给所有客户端
            for client in connected_clients.copy():
                if client != websocket:
                    await client.send(f"用户说: {message}")
    finally:
        # 客户端断开时移除
        connected_clients.discard(websocket)
```

### 3.2 并发模型

```
┌──────────────────────────────────────────────┐
│           asyncio 并发模型                    │
├──────────────────────────────────────────────┤
│                                              │
│  Event Loop (事件循环)                        │
│  ┌──────────────────────────────────────┐    │
│  │  Task 1: 客户端 A 的消息处理          │    │
│  │  Task 2: 客户端 B 的消息处理          │    │
│  │  Task 3: 客户端 C 的消息处理          │    │
│  │  ...                                 │    │
│  │  Task N: 客户端 N 的消息处理          │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  特点：                                      │
│  - 单线程，避免锁竞争                         │
│  - 协程切换开销极小                           │
│  - 每个连接一个协程，互不阻塞                   │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 4. 心跳检测与断线重连

### 4.1 为什么需要心跳？

网络环境复杂，连接可能静默断开（防火墙超时、NAT 过期等）。心跳机制用于：

- 检测连接是否仍然存活
- 保持连接不被中间设备关闭
- 及时发现并清理死连接

### 4.2 服务端心跳实现

```python
import asyncio
import websockets

async def handler(websocket):
    try:
        async for message in websocket:
            await websocket.send(f"echo: {message}")
    except websockets.exceptions.ConnectionClosed as e:
        print(f"连接关闭: code={e.code}, reason={e.reason}")

async def main():
    async with websockets.serve(
        handler,
        "localhost",
        8765,
        ping_interval=30,   # 每30秒发送ping
        ping_timeout=10,    # 10秒内没收到pong则断开
    ):
        await asyncio.Future()

asyncio.run(main())
```

### 4.3 客户端断线重连

```python
import asyncio
import websockets

async def connect_with_retry():
    while True:
        try:
            async with websockets.connect("ws://localhost:8765") as ws:
                print("连接成功!")
                async for message in ws:
                    print(f"收到: {message}")
        except websockets.exceptions.ConnectionClosed:
            print("连接断开，2秒后重连...")
            await asyncio.sleep(2)
        except ConnectionRefusedError:
            print("服务器未启动，5秒后重试...")
            await asyncio.sleep(5)

asyncio.run(connect_with_retry())
```

---

## 5. 数据序列化

### 5.1 JSON 消息格式

实际项目中，通常用 JSON 传递结构化数据：

```python
import json

# 发送
message = {
    "type": "chat",
    "username": "Alice",
    "content": "你好大家！",
    "timestamp": "2026-07-27T12:00:00"
}
await websocket.send(json.dumps(message, ensure_ascii=False))

# 接收
data = json.loads(await websocket.recv())
print(data["content"])
```

### 5.2 消息类型约定

```python
# 常见消息类型设计
MESSAGE_TYPES = {
    "join": "用户加入聊天室",
    "leave": "用户离开聊天室",
    "chat": "聊天消息",
    "system": "系统通知",
    "ping": "心跳探测",
    "pong": "心跳响应",
}
```

---

## 6. 常见陷阱与最佳实践

### 6.1 必须使用 asyncio

`websockets` 库基于 `asyncio`，不能在普通函数中直接使用：

```python
# 错误 ❌
def main():
    async with websockets.serve(handler, "localhost", 8765):
        pass

# 正确 ✅
async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()

asyncio.run(main())
```

### 6.2 异常处理不可少

网络连接随时可能断开，必须捕获异常：

```python
async def handler(websocket):
    try:
        async for message in websocket:
            await process_message(websocket, message)
    except websockets.exceptions.ConnectionClosedOK:
        print("正常断开")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"异常断开: {e}")
    except Exception as e:
        print(f"未知错误: {e}")
    finally:
        cleanup(websocket)
```

### 6.3 连接资源清理

务必在 `finally` 块中清理资源，防止内存泄漏：

```python
async def handler(websocket):
    connected.add(websocket)
    try:
        async for message in websocket:
            await broadcast(message)
    finally:
        connected.discard(websocket)  # 必须清理！
```

### 6.4 广播时复制集合

遍历过程中集合可能变化，需要复制：

```python
# 错误 ❌ — 遍历时修改集合会报 RuntimeError
for client in connected:
    await client.send(message)

# 正确 ✅ — 复制后再遍历
for client in connected.copy():
    await client.send(message)
```

---

## 7. 实战：简易聊天室架构

```
┌─────────────────────────────────────────────────────────┐
│                   聊天室系统架构                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐   WebSocket    ┌─────────────────────┐    │
│  │ 客户端A │◄═════════════▶│                     │    │
│  └─────────┘                │                     │    │
│  ┌─────────┐   WebSocket    │   聊天室服务器        │    │
│  │ 客户端B │◄═════════════▶│   (Python + asyncio) │    │
│  └─────────┘                │                     │    │
│  ┌─────────┐   WebSocket    │   - 连接管理         │    │
│  │ 客户端C │◄═════════════▶│   - 消息广播         │    │
│  └─────────┘                │   - 用户管理         │    │
│                             │   - 心跳检测         │    │
│                             └─────────────────────┘    │
│                                    │                    │
│                                    ▼                    │
│                           ┌──────────────┐             │
│                           │  消息日志存储  │             │
│                           └──────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 8. API 速查表

### websockets 核心 API

```python
# 服务端
import websockets.serve(host, port, handler, **kwargs)
# kwargs: ping_interval, ping_timeout, max_size, extra_headers

# 客户端
import websockets.connect(uri, **kwargs)
# kwargs: extra_headers, open_timeout, close_timeout

# websocket 对象
ws.send(data)           # 发送消息
ws.recv()               # 接收消息
ws.close(code, reason)  # 关闭连接
ws.ping()               # 发送 ping
ws.remote_addr          # (host, port)
ws.path                 # 请求路径
ws.request.headers      # 请求头
ws.subprotocol           # 协议协商结果
```

### 常见异常

```python
websockets.exceptions.ConnectionClosed  # 连接已关闭（基类）
websockets.exceptions.ConnectionClosedOK    # 正常关闭 (code=1000)
websockets.exceptions.ConnectionClosedError # 异常关闭
websockets.exceptions.InvalidURI            # URI 无效
websockets.exceptions.InvalidHandshake      # 握手失败
websockets.exceptions.PayloadTooBig         # 消息过大
```

---

## 9. 思考题

1. **WebSocket 和 HTTP/2 Server Push 有什么区别？** 为什么聊天室场景更适合 WebSocket？

2. **心跳间隔设多少合适？** 太频繁浪费带宽，太稀疏检测不及时，如何权衡？

3. **如何实现聊天室的"正在输入..."提示？** 需要考虑哪些边界情况？

4. **WebSocket 连接数有上限吗？** 一台服务器最多能同时服务多少个 WebSocket 连接？瓶颈在哪里？

5. **如何保证消息的顺序性？** 在并发环境下，如何确保消息按发送顺序被接收？

---

## 📚 参考资料

- [websockets 官方文档](https://websockets.readthedocs.io/)
- [RFC 6455 - The WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [MDN - WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Python asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)
