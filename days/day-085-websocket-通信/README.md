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

**参考答案**

两者都能「服务器主动发数据」，但语义完全不同。HTTP/2 Server Push（服务器推送）本质仍是 HTTP「请求-响应」的扩展：它推送的是**与某个请求相关联的资源**（比如客户端请求了 HTML，服务器顺带把它即将用到的 CSS/JS 提前推过去），目的是减少往返、加速页面加载，并不是一个「任意时刻互发消息」的通道。而 WebSocket 是独立的**全双工**协议：一次握手后连接长期保持，双方都能在任意时刻主动发消息，无需对方先请求。

聊天室的核心需求是「事件驱动的任意推送」：A 发了一句话，服务器要**立刻**把这句话推给此刻在线的 B、C，而 B、C 并没有发起任何请求。这正是 WebSocket 的强项；HTTP/2 Push 做不到「没有对应请求就凭空推一条聊天消息」。

- 小例子：聊天室里服务器执行 `await ws_B.send("A 说：你好")` 即可主动推送；用 HTTP/2 Push 则无法在 B 没请求时把这条消息塞给它。
- 此外 WebSocket 帧开销小、延迟低，适合高频小消息；HTTP 每次请求都带较大头部。

⚠️ 注意：HTTP/2 Server Push 已被主流浏览器弃用（Chrome 106+ 移除支持），不要把它当实时推送方案。浏览器端实时推送应选 WebSocket 或 SSE（Server-Sent Events，单向服务器推送）。

2. **心跳间隔设多少合适？** 太频繁浪费带宽，太稀疏检测不及时，如何权衡？

**参考答案**

心跳（ping/pong）有两个作用：一是**探测死连接**（对方掉线但 TCP 没正常关闭），二是**保活**（防止 NAT、防火墙、负载均衡因连接「空闲太久」而静默切断）。间隔的选择就是在这两个作用与「带宽/CPU/电量开销」之间找平衡。

- **太频繁**：ping/pong 本身很小，但连接数一多（上万），累积的报文、CPU 唤醒、移动端耗电都很可观。
- **太稀疏**：死连接迟迟发现不了，白白占用内存和 fd；还可能超过中间设备的空闲超时被切断。

权衡的关键依据是**中间设备的最短空闲超时**：心跳间隔必须小于它，才能保活。常见 NAT/防火墙超时在 30 秒到几分钟不等。经验做法是 `ping_interval` 设 20~30 秒、`ping_timeout` 设 10~20 秒，既能在半分钟内发现掉线，又不会太吵。

- 小例子：若某 NAT 的空闲超时是 60 秒，心跳间隔设 30 秒就能稳稳保活；设 120 秒则连接可能在两次心跳之间被悄悄切断。
- 还可**自适应**：活跃连接少发心跳、空闲连接按时发；移动端适当拉长间隔省电。

💡 提示：`websockets` 库默认已开启心跳（`ping_interval=20`、`ping_timeout=20`），多数场景无需自己实现，只要按部署环境微调即可。

3. **如何实现聊天室的"正在输入..."提示？** 需要考虑哪些边界情况？

**参考答案**

基本思路：把「正在输入」当成一种**控制消息**，而不是聊天内容。客户端在用户开始打字时发一条 `{"type": "typing", "user": "Alice"}`，服务器广播给房间里其他人，对方 UI 就显示「Alice 正在输入…」；用户停止打字或发出消息后，再发 `{"type": "stop_typing"}` 清除提示。

关键是要**节流**：不要每敲一个键就发一条，否则消息量爆炸。常见做法是「开始输入时发一次，之后每隔 1~2 秒最多续发一次」，并配合超时自动消失。

需要重点处理的边界情况：

- **对方断线/直接关闭页面**：不会再发 stop_typing，所以接收端必须设「超时自动隐藏」（如 3~5 秒没收到更新就清除），否则会永远显示「正在输入」。
- **用户清空输入框或取消**：应主动发 stop_typing。
- **用户真的把消息发出去了**：收到正式聊天消息时立即清除该用户的 typing 状态。
- **同一用户多设备/多标签页**：需要聚合状态，避免一个标签停了另一个还在显示。
- **大房间广播放大**：几百人同时打字会产生海量控制消息，需节流、采样，甚至只对「正在看同一会话」的人推送。
- **隐私开关**：允许用户关闭「显示我正在输入」。

⚠️ 注意：一定要实现「超时自动消失 + 断线清理」，这是最容易漏掉、也最影响体验的坑。

4. **WebSocket 连接数有上限吗？** 一台服务器最多能同时服务多少个 WebSocket 连接？瓶颈在哪里？

**参考答案**

有上限，但不是协议本身规定的。每条 WebSocket 连接底层就是一条 TCP 连接，会占用一个**文件描述符（fd）**和一份内存。单机经过调优可以支撑数万甚至数十万连接（业界常说的 C10K/C100K 问题），具体数字**因机器、系统配置、版本而异**，必须靠压测确定。

真正的瓶颈通常在这几处：

- **文件描述符上限**：Linux 默认每进程 1024，需调高 `ulimit -n` 和系统级 `fs.file-max`，否则连接数卡在几千。
- **内存**：每条连接的读写缓冲区、协程栈、应用层状态（用户名、房间等）都吃内存，连接越多越明显。
- **CPU 与广播放大**：群发是 O(n) 的——1 条消息要发给 n 个客户端就是 n 次 `send`；再加上心跳、JSON 序列化、`wss` 的加解密，CPU 随连接数线性增长。
- **网络带宽**：同样被广播放大，房间越大越费带宽。
- **asyncio 单线程**：事件循环里若有耗时操作（重计算、同步 I/O），会阻塞所有连接。

提升手段：调高 fd 上限、用多进程/多机 + 负载均衡分摊连接、用 Redis pub/sub 或消息队列做跨进程广播、精简每连接状态、把重活丢到线程/进程池。

- 小例子：1 万连接的聊天室，每人发一句话都要广播给其余 9999 人，瞬间就是近 1 万次发送，带宽和 CPU 压力远大于「连接本身」。

💡 提示：客户端**出站**连接还受本地临时端口范围限制；服务器**入站**连接靠「源 IP+源端口+目的 IP+目的端口」四元组区分，不受单一端口数量限制。

5. **如何保证消息的顺序性？** 在并发环境下，如何确保消息按发送顺序被接收？

**参考答案**

先分清两个层面。**单条连接内**：TCP 保证字节流有序，WebSocket 帧也按序传输，所以「同一个客户端发给服务器」的消息天然有序，`async for message in websocket` 本身就是串行接收，不用额外处理。

真正的乱序风险在**服务器的并发处理与广播**：如果用多个协程/worker 并行处理消息，「处理完成的顺序」可能和「到达顺序」不一致；广播给不同客户端时也可能交错。要保证顺序，常用三招：

- **单一广播队列**：所有待广播消息进入一个 FIFO 队列（`asyncio.Queue`），由**一个**专门的协程按入队顺序依次广播。这样无论多少连接并发产生消息，出口只有一个、顺序确定。
- **序列号（seq）**：服务器给每条消息打一个单调递增编号，客户端按 seq 排序、去重、补齐，即使网络层乱序也能还原。
- **同一会话串行处理**：保证同一条连接的消息不被并行处理（用 `async for` 串行消费即可）。

- 小例子：`queue = asyncio.Queue()`；各连接协程 `await queue.put(msg)`；一个 broadcaster 协程 `while True: msg = await queue.get(); 广播(msg)`——出口单一，顺序就有保障。

⚠️ 注意：跨多连接、多服务器实例时，「全局绝对顺序」代价很高（要全局协调）。工程上通常只保证「同一会话/同一房间内有序」，或用 seq 让客户端自行重排，而非追求全局严格有序。

---

## 📚 参考资料

- [websockets 官方文档](https://websockets.readthedocs.io/)
- [RFC 6455 - The WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [MDN - WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [Python asyncio 官方文档](https://docs.python.org/3/library/asyncio.html)
