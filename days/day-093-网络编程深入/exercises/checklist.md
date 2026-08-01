# Day 093 — 网络编程深入 · 练习清单

## ✅ 今日完成清单

- [ ] 理解 socket 编程的基本 API 和流程
- [ ] 掌握 TCP 三次握手和四次挥手
- [ ] 编写一个简单的 TCP Echo 服务器
- [ ] 使用 asyncio 编写异步网络服务器
- [ ] 了解 HTTP/2 和 HTTP/3 的核心特性
- [ ] 设计并实现一个自定义二进制协议

---

## 📝 练习题

### 基础题

**1. TCP Echo 服务器增强**

在 01-socket-basics.py 的基础上，添加以下功能：
- 支持客户端设置昵称（发送 `/name 昵称` 命令）
- 聊天消息带上昵称前缀
- 显示在线用户列表（`/list` 命令）

**2. UDP 对比实验**

编写一个 UDP 版本的 Echo 服务器和客户端，对比 TCP 版本：
- 使用 `socket.SOCK_DGRAM` 替代 `SOCK_STREAM`
- 不需要 listen/accept/connect
- 观察 UDP 丢包的情况（可以用大消息测试）

**3. 协议解析器**

编写一个 HTTP 请求解析器，能解析：
- 请求方法 (GET/POST/...)
- 请求路径
- 请求头
- 请求体（Content-Length）

```python
# 测试数据
request = b"GET /api/users HTTP/1.1\r\nHost: example.com\r\nContent-Length: 0\r\n\r\n"
# 解析结果应为: {'method': 'GET', 'path': '/api/users', 'headers': {...}}
```

### 进阶题

**4. 心跳机制实现**

在 02-async-server.py 的基础上：
- 客户端每 10 秒发送一次心跳
- 服务器检测 30 秒无心跳则断开连接
- 实现心跳超时的优雅断开（通知其他用户）

**5. 文件传输协议**

设计一个支持文件传输的协议：
- 客户端发送文件名和文件内容
- 服务器保存到指定目录
- 支持断点续传（记录已传输字节数）
- 添加传输进度显示

**6. 聊天室加密通信**

为聊天服务器添加加密：
- 使用 `ssl` 模块为 TCP 连接添加 TLS 加密
- 生成自签名证书用于测试
- 对比加密前后的性能差异

---

## 🔍 检查点

完成后，确认你能回答以下问题：

1. `send()` 和 `sendall()` 的区别是什么？
2. 为什么 TCP 服务器需要设置 `SO_REUSEADDR`？
3. asyncio 的 `start_server` 和普通 socket `listen/accept` 有什么区别？
4. HTTP/2 的多路复用是如何解决队头阻塞的？
5. 在自定义协议中，为什么推荐使用"长度前缀"而不是"分隔符"来定界消息？
