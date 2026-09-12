# Day 155 — mitmproxy 中间人：流量拦截、修改与 Addon 编程

> 阶段：Phase 7 — 进阶与性能优化 · 主题：mitmproxy 中间人
>
> 前置知识：Day 116 TCP/UDP、Day 146 HTTPS/TLS 分析、Day 151 SQL 注入（了解 HTTP 参数）、
> Day 149 JWT 安全、Day 154 目录扫描与指纹识别。
> 昨天我们用"发请求 + 看响应"的方式观察 Web；今天换个位置——
> **把自己插到客户端和服务器中间**，实时看到、改动、重放每一个包。

---

## ⚠️ 使用前必读：法律与伦理边界

中间人（MITM）拦截在技术上就是**解密别人的加密流量**。它对 TLS 的信任模型
是一次"合法但危险"的破坏，因此法律与伦理要求极高：

| 场景 | 是否合法 |
|---|---|
| 抓**自己手机/自己浏览器**的流量，且目的是调试自己的程序 | ✅ 合法 |
| 在自己的测试环境代理自己的 App ↔ 自己的服务器 | ✅ 合法 |
| 公司安全团队在**书面授权 + 员工知情**前提下做内部审计 | ⚠️ 需严格合规流程 |
| 抓同事、家人、陌生人的流量 | ❌ 违法 |
| 在公共 WiFi 上劫持他人流量 | ❌ 刑事犯罪 |

| 法域 | 相关法条 |
|---|---|
| 中国大陆 | 《刑法》第 285 条（非法获取计算机信息系统数据）、第 253 条之一（侵犯公民个人信息）；《网络安全法》第 27 条 |
| 美国 | CFAA 18 U.S.C. § 1030；Wiretap Act 18 U.S.C. § 2511 |
| 英国 | Computer Misuse Act 1990；Investigatory Powers Act 2016 |
| 欧盟 | GDPR（个人数据传输）；《网络犯罪公约》 |

**本日所有示例的目标域都限制为 `127.0.0.1` / `localhost` / `example.com`
等无害地址**；示例 03 内置域名白名单校验。

> 本系列定位是**安全防御与教学**：学 MITM 的目的是
> ①调试自己的程序、②理解"为什么证书校验这么重要"、③给自己做 App 抓包分析。
> 不是去截别人的密码。

---

## 一、概念解释

### 1.1 mitmproxy 是什么

一组**开源交互式 HTTPS 中间人代理**工具，用 Python 编写：

| 命令 | 形态 | 适用 |
|---|---|---|
| `mitmproxy` | 交互式 TUI（终端界面） | 人工探索：翻请求、改包、重放 |
| `mitmdump` | 无界面，纯命令行 | 脚本化 / 自动化 / 写进 CI |
| `mitmweb` | Web UI（浏览器界面） | 图形化查看，适合演示与团队协作 |

**它与 Fiddler / Charles / Burp 是同类**，区别在于：

1. **完全开源、跨平台**（Fiddler 偏 Windows，Charles 收费）；
2. **Addon 用 Python 写**——本系列已学完 154 天 Python，正好用得上；
3. **可嵌入**（`mitmproxy` 可以当 Python 库用，直接在代码里 in-process 起代理）。

**为什么需要中间人代理？** 因为 HTTPS 之后，流量是加密的：

```
没有代理:
  你的程序  ──TLS 加密隧道──►  服务器          ←  你只能看到"长度和字节数"

有中间人代理:
  你的程序  ──TLS①──►  mitmproxy  ──TLS②──►  服务器
                       ↑ 明文在这里
                       （对两段 TLS 各自解密/再加密，成为"可信的中间人"）
```

这里的关键点是：**mitmproxy 对客户端伪装成服务器，对服务器伪装成客户端**。
它能成功的前提是——**客户端信任 mitmproxy 自己签发的 CA 证书**。

### 1.2 为什么必须装 CA 证书

TLS 的核心安全保证是**证书链校验**：客户端拿到服务器证书后，会验证
"它是否由我信任的 CA 签发"。mitmproxy 要解密流量，就必须用自己的 CA
**现场签发一张"服务器名一模一样"的假证书**给客户端：

```
客户端  ──握手──►  mitmproxy
                     │ "我是 github.com"
                     │ (出示 mitmproxy 自签发的 github.com 证书)
客户端  ←───────────┘
   ↓ 校验：这张证书是谁签的？
   ├─ 若客户端信任 mitmproxy CA  →  校验通过 → 建立 TLS①  →  明文到手 ✅
   └─ 若客户端不信任            →  证书错误 → 连接失败 ❌
```

所以：**你必须在客户端（浏览器/手机/App）里安装并信任 mitmproxy 的根证书**，
否则只能看到一个加密的连接失败。

这也正是**防御要点**：任何 App 只要做 **certificate pinning（证书固定）**，
就能识别出"签发者不是真服务器"，MITM 立即失效。

### 1.3 三种代理模式

| 模式 | 客户端配置 | 原理 | 典型场景 |
|---|---|---|---|
| **正向代理（regular）** | 手动设置 HTTP 代理为 `127.0.0.1:8080` | 客户端主动把请求发给代理 | 浏览器插件、`curl -x`、`proxychains` |
| **透明代理（transparent）** | 无需配置 | 由 iptables/路由把流量重定向到代理端口 | 抓手机 App、抓 IoT 设备 |
| **反向代理（reverse）** | 目标指向代理端口 | 代理作为服务器对外提供，转发到上游 | 调试自己后端、测试证书问题 |
| **上游代理链（upstream）** | `--mode upstream:http://...` | 代理再走一层代理 | 穿透多层网络、Burp 联动 |

**为什么有这么多模式？** 因为"把流量导到代理"这件事，在不同客户端上
能力完全不同：

- 桌面浏览器：可以手动设代理 → 用正向；
- 手机 App：很多 App 忽略系统代理 → 只能透明代理（需要 root 或路由器支持）；
- 服务端程序：写死了目标地址 → 用反向代理改 DNS/hosts。

### 1.4 拦截与修改：能改什么

一次 HTTP 事务里，**所有**部分都可以改：

| 位置 | 可改写的内容 | 例子 |
|---|---|---|
| 请求行 | method / path / version | `GET /a` → `POST /admin` |
| 请求头 | 任意头 | 加 `X-Forwarded-For`、改 `Cookie`、删 `Referer` |
| 请求体 | JSON / form / 二进制 | 把 `{"role":"user"}` 改成 `{"role":"admin"}` |
| 响应行 | status code / reason | `403` → `200` |
| 响应头 | 任意头 | 删 `Content-Security-Policy` 看页面会不会被注入 |
| 响应体 | 任意内容 | 注入一段 JS 测试前端防御 |

**这就是"越权测试"和"前端安全测试"的核心手法**：
在代理层把自己伪装成管理员（改 `role`）、或伪装成攻击者（注入脚本），
看看**服务端有没有真的做校验**、**前端有没有真的做防御**。

### 1.5 Addon：用 Python 控制代理

mitmproxy 的扩展机制叫 **Addon**：一个普通 Python 对象，实现若干
**按事件名命名的方法**，mitmproxy 在对应时机调用它们。

```python
class MyAddon:
    def request(self, flow):        # 收到客户端请求、尚未转发时
        flow.request.headers["X-Test"] = "1"

    def response(self, flow):       # 收到服务器响应、尚未回给客户端时
        if flow.response.status_code == 404:
            flow.response.status_code = 200
```

**为什么用"事件回调"而不是中间件链？** 因为代理的生命周期事件
（连接建立、TLS 握手、请求、响应、WebSocket 帧、错误、断开）比
Web 框架的中间件丰富得多，事件模型更自然。

**Addon 的事件全景（生命周期）：**

```
     ┌─────────────┐
     │  client     │
     └──────┬──────┘
            ▼
     client_connected
            ▼
     tls_clienthello → tls_established_client
            ▼
     request  ←────────────────── 你能改请求
            ▼
     http_connect / requestheaders / request  (分阶段)
            ▼
     ┌─────────────┐
     │  server     │
     └──────┬──────┘
            ▼
     responseheaders → response ←── 你能改响应
            ▼
     websocket_*   (如果是 WebSocket)
            ▼
     client_disconnected / error
```

### 1.6 常见用途（正反两面）

| 用途 | 说明 | 立场 |
|---|---|---|
| 调试自己 App 的 API 调用 | 看请求参数、响应结构、时序 | ✅ 开发日常 |
| 复现线上问题 | 把生产响应抓下来，在本地重放 | ✅ 开发日常 |
| 弱网/异常注入测试 | 注入延迟、丢包、错误码，测客户端的健壮性 | ✅ 质量保障 |
| Mock 后端 | 用 map_local / 脚本返回假数据，前端不阻塞 | ✅ 前后端协作 |
| 越权/认证测试 | 改 role、改 JWT、改 Cookie 看服务端是否校验 | ✅ 授权渗透测试 |
| 屏蔽/篡改广告 | 改写响应体去广告 | ⚠️ 灰色 |
| 抓取他人流量 | 窃取凭据、cookie | ❌ 违法 |

### 1.7 与其他方案的对比

| 方案 | 层次 | 能看 HTTPS？ | 上手难度 | 适合 |
|---|---|---|---|---|
| **tcpdump / Wireshark** | 网络层（原始包） | ❌（只能看到密文） | 中 | 协议分析、找网络问题 |
| **mitmproxy** | 应用层（HTTP 语义） | ✅（装 CA 后） | 低 | API 调试、改包、自动化 |
| **浏览器 DevTools** | 应用层（仅浏览器内） | ✅（浏览器自己的栈） | 极低 | 前端调试，但抓不到 App |
| **charles / fiddler** | 应用层 | ✅ | 低 | 图形化，收费/平台限制 |
| **Burp Suite** | 应用层 + 主动扫描 | ✅ | 中高 | 专业渗透，价格高 |
| **frida + 脱壳** | 进程内 hook | ✅（绕过 pinning） | 高 | 逆向 App（Day 140 相关） |

**选择原则：** 只想看 API → DevTools/mitmproxy；要自动化 → mitmdump；
要跨设备/App → mitmproxy 透明代理；要主动扫描漏洞 → Burp。

---
## 二、原理解释（底层机制与设计动机）

### 2.1 HTTP 代理的两种形态：普通请求 vs CONNECT 隧道

客户端配置了 HTTP 代理后，行为分两种：

**（1）目标是 HTTP（明文）：**

```
GET http://example.com/a HTTP/1.1     ← 注意：请求行里是"绝对 URL"
Host: example.com
Proxy-Connection: keep-alive

代理收到后，把请求行改成相对形式，转发给 example.com。
```

**（2）目标是 HTTPS：**

```
CONNECT example.com:443 HTTP/1.1      ← 先建立隧道
Host: example.com:443

代理回复：
HTTP/1.1 200 Connection established

之后客户端在"这条隧道"里做 TLS 握手。
```

**关键理解点：**

- 明文 HTTP 时，代理**天然就能看到全部内容**，不需要任何证书；
- HTTPS 时，`CONNECT` 只是请求开一条**盲隧道**。mitmproxy 要想看内容，
  必须**不老实**——它回复 `200 Connection established` 之后，
  **自己扮演服务器完成 TLS① 握手**（出示自签证书），再**扮演客户端**
  去和真服务器做 TLS②。这就是 MITM 的全部魔法。

```
  客户端                      mitmproxy                      真服务器
    │                             │                             │
    │  CONNECT example.com:443    │                             │
    │────────────────────────────►│                             │
    │  200 Connection established │                             │
    │◄────────────────────────────│                             │
    │                             │                             │
    │  ClientHello                │                             │
    │────────────────────────────►│                             │
    │                             │  ① 判断 SNI = example.com    │
    │                             │  ② 用 CA 现场签一张          │
    │                             │     example.com 证书         │
    │  ServerHello + 自签证书      │                             │
    │◄────────────────────────────│                             │
    │  (若客户端信任 mitmproxy CA) │                             │
    │  Finished  ────────────────►│                             │
    │      ✅ TLS① 建立，明文可达   │                             │
    │                             │  ── TLS② 握手（用真证书）──►  │
    │                             │◄────────────────────────────│
    │                             │      ✅ TLS② 建立            │
    │  HTTP 明文请求 ─────────────►│  改写/记录后重新加密转发 ────►│
    │  HTTP 明文响应 ◄────────────│  ◄── 解密并改写后回传 ───────│
```

### 2.2 证书"现场签发"意味着什么

mitmproxy 内部维护一张 CA（`~/.mitmproxy/mitmproxy-ca-cert.pem`）。
每次遇到新的 SNI，它会：

1. 生成一对新的 **临时私钥**（或用缓存）；
2. 用 mitmproxy CA 的私钥**签发**一张 CN/SAN = 目标域名的证书；
3. 缓存这张证书（默认在内存 + `~/.mitmproxy/` 下）。

**三个重要推论：**

1. **不同域名得到不同证书**——所以 SAN 校验会通过（域名对得上）；
2. **签发者不同**——所以防 pinning 的 App 会拒；
3. **自签证书不受平台欢迎**——Android 7+ 起，用户安装的 CA 默认**不被
   应用信任**（除非 App 显式开启 `networkSecurityConfig` 或系统 CA）。

**这就是为什么"抓 Android App 的包"这么麻烦：**
需要 root + 把 CA 装到系统证书区，或者用 frida 绕过 pinning。

### 2.3 为什么修改响应体会破坏 `Content-Length`

HTTP/1.1 里，响应体的长度有三种告知方式：

| 方式 | 示例 | 含义 |
|---|---|---|
| `Content-Length: N` | `Content-Length: 342` | 定长，读 N 字节结束 |
| `Transfer-Encoding: chunked` | `chunked` | 分块，`0\r\n\r\n` 结束 |
| 无长度 + 连接关闭 | 无 | 读到 EOF 结束（HTTP/1.0 风格） |

如果你把响应体从 342 字节改成 400 字节，却**不改 `Content-Length`**：

```
客户端期待 342 字节 → 多出来的 58 字节被当作"下一个响应" → 协议错乱
```

**mitmproxy 的正确做法**：用 `flow.response.text = "新内容"` 或
`flow.response.content = b"..."`，它**自动**重算 `Content-Length`
并处理 `chunked`。**不要**手动去写 `flow.response.headers["Content-Length"]`
（除非你很清楚自己在干什么）。

### 2.4 gzip/br压缩：改包前必须先解压

服务器常返回 `Content-Encoding: gzip`。此时 `flow.response.content`
是**压缩后的字节**。你如果直接对压缩字节做字符串替换：

```python
# ❌ 错误：乱码 / 匹配不到
flow.response.content = flow.response.content.replace(b"old", b"new")

# ✅ 正确：用 text 属性，mitmproxy 自动解码/重编码
if "old" in flow.response.text:
    flow.response.text = flow.response.text.replace("old", "new")
```

**注意 `flow.response.text` 的代价**：它会把整个 body 解码成 `str`
（UTF-8 解码失败会抛异常），大文件（>几十 MB）会吃内存。
**规则：小文本用 `.text`，大文件/二进制用 `.content` 或 `.raw_content`。**

### 2.5 Addon 的执行顺序与"响应改写"的时机

Addon 支持**注册顺序**与 `@hook` 装饰器两种写法。默认按注册顺序执行。
重要事件顺序：

```
requestheaders  →  request  →  [转发]  →  responseheaders  →  response
   ↑ 此时只有头          ↑ 此时 body 已完整        ↑ 只有头        ↑ body 完整
```

**设计动机：** 分阶段是为了**流式**处理——大文件上传时，
你不可能等整个 body 到齐才决定要不要拦截。分阶段让你能在
**头阶段**就做出决策（比如直接拒绝），而不用等 body。

**两个常被误解的事实：**

1. `request` 事件触发时，body **已经完整读入**（除非开了 `stream_*` 系列事件）；
2. 在 `response` 里改 `flow.response` **会**生效，因为此时还没回给客户端。

### 2.6 透明代理为什么要靠 iptables

透明代理的目标是"客户端完全不知道有代理"。实现靠**网络层重定向**：

```bash
# Linux 上把 80/443 的流量重定向到 mitmproxy 的 8080
iptables -t nat -A PREROUTING -p tcp --dport 80  -j REDIRECT --to-ports 8080
iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-ports 8080
# 原目标地址会丢失，所以需要 SO_ORIGINAL_DST 找回
```

**关键问题：目标地址被 NAT 改掉了。** 代理必须通过 `getsockopt(SO_ORIGINAL_DST)`
把"客户端原本想访问谁"找回来，否则不知道要连哪里。
mitmproxy 的 `--mode transparent` 会自动处理这一步。

**为什么这在 macOS/Windows 上麻烦？** 因为那是 Linux 的 netfilter 特性，
其它系统要用 pf（macOS）/ WinDivert（Windows）。

### 2.7 为什么 Addon 里不能做"长时间阻塞操作"

mitmproxy 的事件循环（asyncio）是**单线程**的。你在 `request` 里写：

```python
time.sleep(10)          # ❌ 整个代理卡住 10 秒，所有连接都停
requests.get(...)       # ❌ 同步请求阻塞事件循环
```

正确做法：

- 用 `mitmproxy` 提供的异步 API（如 `flow.request` 的 `await` 变体）；
- 或者把重活丢到 `ThreadPoolExecutor` / `asyncio.to_thread`；
- 需要"挂起请求稍后继续"时，用 `flow.intercept()` + `flow.resume()`。

**这就是"代理为什么突然变慢"的最常见原因。**

---
