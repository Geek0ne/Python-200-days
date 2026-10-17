# Day 187 · 概念与原理：端口扫描与服务指纹

> 目标：把 Day 186 得到的"名字/IP"变成"这台机器开了什么服务"。
> 本文件讲原理与 API，README.md 记录真机实验（含两个由自测/实测抓出的 bug）。

---

## 1. 端口扫描到底在测什么

TCP 端口不是一个可以"读取"的对象。扫描器能做的是**尝试建立连接**，然后根据内核返回的错误推断状态。

```text
客户端                          目标主机
  │ ──── SYN ─────────────────▶ │
  │ ◀─── SYN+ACK ────────────── │   端口有进程监听 → open
  │ ──── ACK ─────────────────▶ │
  │                              │
  │ ──── SYN ─────────────────▶ │
  │ ◀─── RST ────────────────── │   没有监听 → closed
  │                              │
  │ ──── SYN ─────────────────▶ │
  │        （无响应，一直等）      │   防火墙 DROP → filtered
```

**三种扫描方式对比：**

| 方式 | 原理 | 权限 | 是否完成握手 | 日志可见 | 速度 |
|---|---|---|---|---|---|
| TCP connect | 完整三次握手 | 普通用户 | 是 | 目标应用日志可见 | 较慢 |
| TCP SYN（半开） | 只发 SYN，收到 SYN+ACK 后 RST | root/raw socket | 否 | 网络层可见 | 快 |
| UDP | 发 UDP 包看 ICMP 端口不可达 | 普通用户 | 否 | 视服务 | 很慢、不可靠 |

本课程用 connect 扫描：零依赖、无需 root、行为最容易解释。生产环境的大规模扫描才需要 SYN。

---

## 2. 状态判定：errno 才是真相

`socket.connect_ex()` 返回 0 表示成功，否则返回 errno。常见值：

| errno | 常量 | 含义 | 应判为 |
|---:|---|---|---|
| 0 | — | 握手成功 | open |
| 111 | ECONNREFUSED | 目标回了 RST | closed |
| 11 | EAGAIN / EWOULDBLOCK | 非阻塞 connect 未完成（等超时） | filtered |
| 115 | EINPROGRESS | 连接进行中（等超时） | filtered |
| 110 | ETIMEDOUT | 内核判定超时 | filtered |
| 101 | ENETUNREACH | 网络不可达 | unreachable |
| 113 | EHOSTUNREACH | 主机不可达 | unreachable |

**本日真实踩坑**：对黑洞地址 `198.51.100.1:81` 做 connect，Linux 返回的是 **errno 11（EAGAIN）**，
耗时正好 200ms/1000ms（等于超时）。第一版代码只把 `110` 当 filtered，于是把"被过滤"误标成 `error(11)`。
修复后才得到正确的 `filtered`。

**教训**：不要凭经验枚举 errno，要在真实环境打印出来再归类；并且用"耗时 ≈ timeout"作为辅助判据。

---

## 3. 超时：扫描速度的真正决定因素

假设扫 1000 个端口：
- 全是 closed：本机/局域网约 0.02~1ms，1 秒内完成；
- 混有 filtered：每个 filtered 都要等满 timeout。timeout=1s、100 个 filtered → 至少 100 秒（串行）。

**并发能把等待重叠**：500 个端口、timeout=0.5s、100 并发，最坏约 `ceil(500/100) × 0.5 = 2.5s`。
但并发不能突破"单个 filtered 端口至少要等 timeout"这个下限。

**调参原则**：
- 局域网：timeout 0.2~0.5s；
- 公网：timeout 1~2s，并接受更多 filtered；
- 大规模：先快速扫常见端口，再对少量目标做深扫。

---

## 4. 指纹识别：三层证据

### 4.1 Banner（原始响应）

SSH/FTP/SMTP 等服务在连接建立后**主动**发送版本字符串：

```text
SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13
220 mail.example.com ESMTP Postfix
```

HTTP 不会主动说话，必须客户端先发请求。

### 4.2 HTTP 头

| 头 | 价值 | 注意 |
|---|---|---|
| `Server` | 产品/版本 | 可被改写、可被 CDN 覆盖 |
| `X-Powered-By` | 后端框架 | 常被安全配置移除 |
| `Via` / `X-Cache` | CDN/代理 | 说明你连到的不是源站 |
| `Set-Cookie` | 框架特征（JSESSIONID/PHPSESSID） | 需结合路径 |

### 4.3 页面内容

`<title>`、默认错误页、目录列表样式、favicon 哈希，都能作为指纹。
但内容最容易变，置信度最低。

### 4.4 置信度模型

本日代码用简单规则：

| 置信度 | 条件 |
|---|---|
| high | 有明确 Server 头且匹配到已知产品 |
| medium | 有状态行或 banner，但产品未知/证据弱 |
| low | 只有连接成功，没有任何可识别内容 |

**为什么要输出置信度**：资产台账里"unknown (low)"和"nginx (high)"的处置优先级完全不同。
把猜测当事实，会让后续漏洞匹配产生大量误报。

---

## 5. 指纹不可靠的四个原因

1. **可伪造**：`Server: nginx` 可以随便写。
2. **CDN 遮挡**：你看到的是边缘节点的 Server，不是源站。
3. **默认配置**：大量 Python http.server 的 Server 头完全一样，无法区分业务。
4. **版本滞后**：header 里的版本可能被反向代理改写。

所以指纹只用于**缩小范围**，不能单独作为漏洞结论。Day 188 的漏洞检测必须做主动验证。

---

## 6. 与 nmap 对账：为什么要自己写一遍

nmap 是成熟工具，生产环境直接用即可。自己实现的价值：

- 理解 `-sT` / `-sS` / `-Pn` 到底改变了什么；
- 能解释"为什么 nmap 说 filtered，我的脚本说 closed"；
- 在只能跑 Python 的环境（容器、受限主机）里仍能完成基础探测。

本日对账结果：nmap `-sT -Pn` 与自研扫描器对 `18080/18022` 的判定一致（open/closed），
nmap 用时 0.07s，自研脚本含指纹约 0.2s —— 差距主要在进程启动与指纹请求，不在扫描本身。

---

## 7. API 速查

| 需求 | 写法 | 注意 |
|---|---|---|
| 创建 socket | `socket.socket(AF_INET, SOCK_STREAM)` | 记得 `close()` 或用 `with` |
| 设置超时 | `sock.settimeout(0.5)` | 只影响该 socket |
| 连接并取 errno | `sock.connect_ex((host, port))` | 不抛异常，返回错误码 |
| 连接（抛异常） | `sock.connect(...)` | 需捕获 `OSError` |
| 判断超时 | `except socket.timeout` | Python 3.10+ 是 `TimeoutError` 别名 |
| 解析端口段 | 自己写 `parse_ports` | 注意边界 1~65535 |
| 并发 | `ThreadPoolExecutor` | I/O 密集，线程足够 |
| HTTP 请求 | 手写 `GET ... HTTP/1.0` | 简单场景无需 `requests` |
| 读响应 | 按 `Content-Length` 读 body | 只读到 `\r\n\r\n` 会丢 body（本日 bug） |

---

## 8. 合规与安全边界

- 只扫描**自有资产或书面授权**的目标；公网随机扫描在多数司法辖区违法。
- connect 扫描会在目标应用日志留下完整连接，隐蔽性差，但这也意味着**可审计**。
- 生产扫描要限速，避免把老旧设备打挂（工控/打印机对并发连接极敏感）。
- 本课程实验只扫 `127.0.0.1` 和自己启动的临时服务。

---

## 9. 思考题

1. 为什么 `connect_ex` 对黑洞地址返回 11 而不是 110？这对状态归类意味着什么？
2. timeout=0.2s 时，一个真正慢但存活的公网服务会被误判成什么？如何降低误判？
3. 如果目标把 `Server` 改成随机字符串，还有哪些指纹证据可用？
4. 500 个端口、100 并发、timeout=0.5s，最坏情况要多久？如果要求 3 秒内完成，参数怎么调？
5. 为什么"端口 open"不等于"服务可用"？举两个例子。
