# Day 093 — 网络编程深入

> **socket 编程 | 异步网络框架 | HTTP/2 与 HTTP/3 | 自定义协议服务器**

---

## 📋 今日目标

1. 深入理解 socket 编程底层机制
2. 掌握异步网络框架（asyncio + aiohttp）
3. 了解 HTTP/2 与 HTTP/3 协议演进
4. 实战：构建自定义协议服务器

---

## 1. Socket 编程深入

### 1.1 Socket 是什么？

Socket（套接字）是操作系统提供的网络通信端点。它是应用层与 TCP/IP 协议族通信的中间软件抽象层。

```
┌─────────────────────────────────────────┐
│              应用层 (HTTP, FTP...)        │
├─────────────────────────────────────────┤
│           Socket API (中间层)             │
├──────────┬──────────────────────────────┤
│   TCP    │           UDP                │
├──────────┴──────────────────────────────┤
│            IP 协议层                      │
├─────────────────────────────────────────┤
│          网络接口层 (网卡)                 │
└─────────────────────────────────────────┘
```

### 1.2 TCP vs UDP 对比

| 特性 | TCP | UDP |
|------|-----|-----|
| 连接方式 | 面向连接（三次握手） | 无连接 |
| 可靠性 | 可靠传输，有确认机制 | 不可靠，可能丢包 |
| 顺序性 | 保证顺序 | 不保证顺序 |
| 速度 | 较慢 | 较快 |
| 适用场景 | HTTP、文件传输、邮件 | 视频流、游戏、DNS |

### 1.3 TCP 三次握手与四次挥手

```
三次握手 (建立连接):
  客户端                    服务端
    │── SYN (seq=x) ──────>│
    │<── SYN+ACK (seq=y,  │
    │     ack=x+1) ────────│
    │── ACK (ack=y+1) ────>│
    │     连接已建立          │

四次挥手 (断开连接):
  客户端                    服务端
    │── FIN ───────────────>│
    │<── ACK ───────────────│
    │<── FIN ───────────────│
    │── ACK ───────────────>│
    │     连接已关闭          │
```

### 1.4 Socket 核心 API

```python
import socket

# 创建 socket 对象
# family: AF_INET(IPv4) 或 AF_INET6(IPv6)
# type: SOCK_STREAM(TCP) 或 SOCK_DGRAM(UDP)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# 设置端口复用（避免 TIME_WAIT 问题）
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 绑定地址和端口
s.bind(('0.0.0.0', 8080))

# 监听（backlog 为等待队列长度）
s.listen(5)

# 接受连接，返回 (conn, address)
conn, addr = s.accept()

# 发送数据（返回发送字节数）
conn.sendall(b'Hello, Client!')

# 接收数据（bufsize 为最大接收字节数）
data = conn.recv(1024)

# 关闭连接
conn.close()
s.close()
```

---

## 2. 异步网络框架

### 2.1 为什么需要异步？

同步 I/O 模型在高并发场景下的瓶颈：

```
同步模型 (一个线程处理一个连接):

时间线: ──────────────────────────────────>
线程1: [连接1]---等待I/O---[处理]---[等待I/O]---[处理]
线程2: [连接2]---等待I/O---[处理]---[等待I/O]---[处理]
线程3: 空闲...

异步模型 (一个事件循环处理多个连接):

时间线: ──────────────────────────────────>
事件循环: [连接1就绪]→[处理1]→[连接2就绪]→[处理2]→[连接1就绪]→...
         ↑ 利用等待时间处理其他连接
```

### 2.2 asyncio 事件循环

```python
import asyncio

async def handle_client(reader, writer):
    """异步处理客户端连接"""
    data = await reader.read(1024)
    message = data.decode()
    print(f"收到: {message}")
    
    writer.write(b'ACK')
    await writer.drain()
    
    writer.close()
    await writer.wait_closed()

async def main():
    # 启动 TCP 服务器
    server = await asyncio.start_server(
        handle_client, '127.0.0.1', 8888
    )
    print("服务器启动: 127.0.0.1:8888")
    
    async with server:
        await server.serve_forever()

asyncio.run(main())
```

### 2.3 aiohttp 客户端

```python
import aiohttp
import asyncio

async def fetch(url):
    """异步 HTTP 请求"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            print(f"状态码: {response.status}")
            return await response.text()

async def main():
    urls = [
        'http://httpbin.org/get',
        'http://httpbin.org/delay/1',
        'http://httpbin.org/delay/2',
    ]
    # 并发请求所有 URL
    results = await asyncio.gather(*[fetch(url) for url in urls])
    print(f"完成 {len(results)} 个请求")

asyncio.run(main())
```

### 2.4 aiohttp 服务端

```python
from aiohttp import web
import aiohttp

# 路由处理
async def hello(request):
    name = request.match_info.get('name', 'World')
    return web.Response(text=f"Hello, {name}!")

async def json_handler(request):
    data = await request.json()
    return web.json_response({"received": data})

# 创建应用
app = web.Application()
app.router.add_get('/', hello)
app.router.add_get('/hello/{name}', hello)
app.router.add_post('/api/data', json_handler)

if __name__ == '__main__':
    web.run_app(app, host='127.0.0.1', port=8080)
```

---

## 3. HTTP/2 与 HTTP/3

### 3.1 HTTP 协议演进

```
HTTP/1.0 (1996)     HTTP/1.1 (1997)     HTTP/2 (2015)      HTTP/3 (2022)
    │                    │                    │                   │
    ▼                    ▼                    ▼                   ▼
 每次请求          持久连接              多路复用             基于 QUIC
 新建 TCP          管线化(有队头阻塞)    头部压缩             UDP 传输
 关闭连接          Host 头              服务器推送           0-RTT 连接
                                      二进制分帧            连接迁移
```

### 3.2 HTTP/2 核心特性

| 特性 | 说明 | 解决的问题 |
|------|------|-----------|
| 多路复用 | 一个连接上并发多个流 | 队头阻塞 |
| 头部压缩 | HPACK 算法压缩请求头 | 减少带宽占用 |
| 服务器推送 | 主动推送资源 | 减少请求次数 |
| 二进制分帧 | 二进制传输代替文本 | 解析效率更高 |

### 3.3 HTTP/3 (QUIC)

HTTP/3 基于 QUIC 协议，解决了 TCP 层面的队头阻塞问题：

```
TCP + TLS 1.2:           QUIC (HTTP/3):
  TCP 握手 (1 RTT)         QUIC 握手 (0-1 RTT)
  + TLS 握手 (1-2 RTT)     (合并在一起)
  = 2-3 RTT 建立连接       = 0-1 RTT 建立连接

  一个流丢包 →            一个流丢包 →
  所有流都阻塞            只有该流受影响
```

### 3.4 Python 中使用 HTTP/2

```python
# 需要安装: pip install httpx[http2]
import httpx

async def fetch_http2():
    async with httpx.AsyncClient(http2=True) as client:
        response = await client.get('https://www.google.com')
        print(f"HTTP 版本: {response.http_version}")  # HTTP/2
        print(f"状态码: {response.status_code}")

# 同步方式
client = httpx.Client(http2=True)
response = client.get('https://www.google.com')
print(f"HTTP 版本: {response.http_version}")
```

---

## 4. 自定义协议服务器

### 4.1 协议设计原则

一个好的应用层协议需要：

1. **消息定界**：接收方如何知道一条消息的边界
2. **字节序**：大端/小端的选择
3. **消息类型**：请求/响应/通知等
4. **版本兼容**：协议升级机制

### 4.2 消息定界方案对比

```
方案1: 固定长度
┌──────┬──────┬──────┬──────┐
│Msg 1 │Msg 2 │Msg 3 │Msg 4 │
│ 64B  │ 64B  │ 64B  │ 64B  │
└──────┴──────┴──────┴──────┘
优点: 简单    缺点: 浪费空间

方案2: 分隔符 (如 \n)
┌────────┬────────┬────────┐
│Msg 1\n │Msg 2\n │Msg 3\n │
└────────┴────────┴────────┘
优点: 可读    缺点: 需要转义

方案3: 长度前缀 (推荐)
┌──────┬─────────────┬──────┬──────────────┐
│ 5 B  │  Hello...   │ 3 B  │  Hi...       │
└──────┴─────────────┴──────┴──────────────┘
优点: 高效、无限制    缺点: 需要解析
```

---

## 5. 思考题

1. **为什么 TCP 需要三次握手而不是两次？** 提示：考虑网络延迟和历史报文

**参考答案**

两次握手只确认了「客户端能发、服务端能收」这一个方向，服务端无法确认自己发的包对方真的收到了，也无法确认双方的初始序列号（ISN，给字节编号、判断报文新旧的起点）都被对方接受。

核心原因是**网络里滞留的历史报文**。设想客户端发的第一个 SYN 在某个节点排队迟到了，客户端超时后重发 SYN、正常通信并关闭了连接；那个迟到的旧 SYN 这时才到达服务端。若只有两次握手，服务端回一个 SYN+ACK 就认为连接建立，白开一条「幽灵连接」占着内存和端口。三次握手下，客户端收到这个 SYN+ACK 会发现序号对不上，回 RST 拒绝，服务端就不会建立连接。

第三次握手还顺带完成两件事：让服务端确认「客户端收到了我的 ISN」，双向序号都同步好；客户端也能在第三个 ACK 里就捎带数据（TCP Fast Open 把这个优化进一步提前）。

小例子：`SYN(seq=x)` → `SYN+ACK(seq=y, ack=x+1)` → `ACK(ack=y+1)`。第二步客户端确认了 x，第三步服务端才确认了 y——少一步就少一个方向的确认。

💡 提示：四次挥手比三次握手多一次，是因为服务端收到 FIN 后可能还有数据没发完，ACK 和 FIN 无法合并成一个包。

2. **asyncio 的事件循环和操作系统的 epoll/kqueue 有什么关系？**

**参考答案**

一句话：**事件循环是「调度器」，epoll/kqueue/IOCP 是它底层用来问操作系统「哪些 socket 就绪了」的工具**。事件循环自己不做 I/O，它把这件事委托给内核。

流程是这样的：协程执行到 `await reader.read()` 时数据还没到，协程挂起，并把「我关心这个 fd 的可读事件」注册给事件循环；事件循环把这些 fd 交给标准库 `selectors`（Linux 用 epoll、macOS/BSD 用 kqueue、Windows 用 IOCP 或 select），然后调用一次 `epoll_wait()` 之类的系统调用统一等待。内核返回就绪 fd 列表后，事件循环把对应协程重新排进可运行队列，`await` 那一行就继续往下走了。

所以「单线程扛上万连接」不是 Python 的魔法，而是**阻塞点从「每个连接一个线程」变成了「整个进程一次系统调用」**。epoll 比老的 select/poll 强在：就绪列表由内核维护，不必每次把全部 fd 拷进内核再线性扫描，开销从 O(连接总数) 降到接近 O(就绪数)。

小例子：`loop = asyncio.get_running_loop()`，`await loop.sock_recv(sock, 1024)` 内部就是「注册 fd → 挂起协程 → epoll 报告可读 → 恢复协程」。

⚠️ 注意：事件循环是单线程的，协程里一旦写了 `time.sleep(1)` 或 CPU 密集循环，整个 epoll 等待都被卡住，所有连接一起变慢。这类活儿要用 `await asyncio.to_thread(...)` 或 `run_in_executor()` 丢进线程/进程池。

3. **HTTP/3 为什么选择 UDP 而不是在 TCP 上改进？**

**参考答案**

不是 UDP 本身更好，而是**TCP 已经改不动了**：TCP 实现在操作系统内核里，升级要等用户换系统；沿途的路由器、防火墙、NAT 设备（统称「中间盒」）还会按老规矩检查 TCP 头，任何新字段都可能被丢弃或篡改。这种现象叫**协议僵化（ossification）**。

TCP 有两个绕不过去的结构性问题：一是**队头阻塞**——TCP 保证字节流严格有序，一个包丢了，后面已到达的数据也得在内核缓冲区里等重传；HTTP/2 虽然在应用层分了多个 stream，但它们共用一条 TCP 连接，一个 stream 丢包会拖住全部。二是**握手延迟**——TCP 三次握手 1 个 RTT（往返时延），再叠加 TLS 握手又要 1~2 个 RTT。

QUIC 的解法是**把可靠传输搬到用户态、跑在 UDP 之上**：UDP 只负责尽力送出数据报，重传、拥塞控制、有序交付全部由 QUIC 库（如 aioquic、quiche）在应用进程里实现。好处是：每个 stream 独立重传互不阻塞；传输握手与 TLS 1.3 握手合并，做到 1-RTT 甚至 0-RTT；连接用 Connection ID 而非「IP+端口」四元组标识，手机从 Wi-Fi 切到 4G 也不用重连；升级只需更新软件，不用等内核。

小例子：加载网页时一张图片的包丢了，HTTP/2 over TCP 会让同连接上的 CSS/JS 一起等；HTTP/3 里只有那张图片的 stream 等，其它照常渲染。

💡 提示：UDP 常被中间盒限速或封禁，所以客户端一般先试 QUIC，失败再回落到 HTTP/2 over TCP（通过 Alt-Svc 响应头协商）。

4. **在自定义协议中，如何处理消息丢失和重传？** 提示：参考 TCP 的 ACK 机制

**参考答案**

先分清跑在哪一层：**如果自定义协议建在 TCP 上，字节不会丢也不会乱序**（TCP 已经做了确认、重传、排序），你要处理的只是「连接断了要重连」和「粘包/拆包」（用长度前缀或 `\n` 定界）。只有跑在 UDP 上，才需要自己实现 TCP 那套可靠机制。

在 UDP 上要做四件事：

1. **编号**：每条消息带递增的 `seq`，接收方据此去重和排序。
2. **确认（ACK）**：接收方回 `ack=seq`，或用累积确认表示「seq 及之前都收到了」。发送方为每条未确认消息启动定时器。
3. **超时重传**：定时器到期还没收到 ACK 就重发。超时时间按往返时延 RTT 动态估算（类似 TCP 的 `RTO = SRTT + 4×RTTVAR`），重传间隔用指数退避，避免网络拥塞时越重传越堵。
4. **幂等/去重**：ACK 本身也可能丢，导致发送方重发、接收方收到重复消息。所以业务操作要设计成幂等的（带唯一请求 ID，处理过就直接返回上次结果），或接收方按 `seq` 丢弃重复包。

小例子：发 `{"seq": 7, "op": "转账", "req_id": "a1"}`，200 ms 内没收到 `{"ack": 7}` 就重发；服务端发现 `req_id=a1` 已处理过，只回 ACK 不再扣款。

💡 提示：生产环境别自己造轮子——要可靠就用 TCP，要低延迟就用现成的 QUIC/KCP 库。自研重传最常踩的坑是超时估得太短造成重传风暴，以及忘了幂等导致重复扣款。

5. **如何用 asyncio 实现一个支持广播的聊天室？** 提示：用一个集合管理所有 writer

**参考答案**

思路：用 `asyncio.start_server` 起一个 TCP 服务，每个连接进来就把它的 `writer` 加进一个全局集合；读到一行消息后，遍历集合把数据写给「除发送者外」的所有 writer；连接断开时在 `finally` 里把 writer 从集合移除并关闭。下面这份代码只用标准库，自带三个客户端做自测，可直接运行。

```python
import asyncio

# 用一个集合管理所有客户端 writer，实现广播
clients = set()

async def handle_client(reader, writer):
    clients.add(writer)                 # 新连接登记
    try:
        while True:
            data = await reader.readline()   # 按行定界，读到一条完整消息
            if not data:                     # 客户端断开
                break
            # 广播给「除发送者外」的所有客户端
            for w in list(clients):          # 复制集合，避免遍历时被修改
                if w is not writer:
                    w.write(data)
                    await w.drain()
    finally:
        clients.discard(writer)         # 断开时务必清理
        writer.close()

async def main():
    # 端口 0 = 让系统自动分配空闲端口
    server = await asyncio.start_server(handle_client, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    # 启动三个客户端：Alice / Bob / Carol
    r1, w1 = await asyncio.open_connection("127.0.0.1", port)
    r2, w2 = await asyncio.open_connection("127.0.0.1", port)
    r3, w3 = await asyncio.open_connection("127.0.0.1", port)
    await asyncio.sleep(0.1)            # 等三个连接都登记进 clients

    w1.write("Alice: 大家好\n".encode())
    await w1.drain()
    print("Bob 收到:", (await r2.readline()).decode().strip())
    print("Carol 收到:", (await r3.readline()).decode().strip())

    # 清理：关闭客户端，再关闭服务器
    for w in (w1, w2, w3):
        w.close()
        await w.wait_closed()
    server.close()
    await server.wait_closed()

asyncio.run(main())
```

运行输出（已验证）：

```
Bob 收到: Alice: 大家好
Carol 收到: Alice: 大家好
```

关键点解释：`readline()` 用 `\n` 做消息定界，天然解决了 TCP 粘包问题；`w.write()` 只是把数据放进发送缓冲区，`await w.drain()` 才会在缓冲区积压时让出控制权，起到背压（backpressure）作用，防止慢客户端把内存撑爆；`list(clients)` 复制一份再遍历，避免广播过程中有连接断开导致「集合在迭代时被修改」的 RuntimeError。

⚠️ 注意：这个版本是「谁发谁不收」的简单广播。生产环境还要加：昵称/鉴权、消息长度上限（防恶意大包）、异常 writer 的剔除，以及用 `asyncio.Queue` + 单个广播协程来保证所有人看到的消息顺序一致。

---

## 📚 扩展阅读

- [Python socket 编程官方文档](https://docs.python.org/3/library/socket.html)
- [asyncio 高级用法](https://docs.python.org/3/library/asyncio-stream.html)
- [HTTP/2 规范 (RFC 7540)](https://tools.ietf.org/html/rfc7540)
- [QUIC 协议概述](https://www.chromium.org/developers/design-documents/network-quic/)
