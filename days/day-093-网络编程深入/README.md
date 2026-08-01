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
2. **asyncio 的事件循环和操作系统的 epoll/kqueue 有什么关系？**
3. **HTTP/3 为什么选择 UDP 而不是在 TCP 上改进？**
4. **在自定义协议中，如何处理消息丢失和重传？** 提示：参考 TCP 的 ACK 机制
5. **如何用 asyncio 实现一个支持广播的聊天室？** 提示：用一个集合管理所有 writer

---

## 📚 扩展阅读

- [Python socket 编程官方文档](https://docs.python.org/3/library/socket.html)
- [asyncio 高级用法](https://docs.python.org/3/library/asyncio-stream.html)
- [HTTP/2 规范 (RFC 7540)](https://tools.ietf.org/html/rfc7540)
- [QUIC 协议概述](https://www.chromium.org/developers/design-documents/network-quic/)
