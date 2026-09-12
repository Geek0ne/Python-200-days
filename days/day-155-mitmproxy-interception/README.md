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
## 三、定义与使用方法（API 速查表）

### 3.1 安装与首次运行

```bash
# 方式 1：pip（推荐，与本系列 Python 环境一致）
pip install mitmproxy
mitmdump --version

# 方式 2：pipx（隔离环境，不污染项目）
pipx install mitmproxy

# 方式 3：系统包（Ubuntu）
# sudo apt install mitmproxy

# 启动（默认监听 127.0.0.1:8080）
mitmproxy                 # TUI
mitmdump                  # 无界面
mitmweb                   # Web UI，默认 http://127.0.0.1:8081
```

**首次运行会生成 CA：**

```
~/.mitmproxy/
├── mitmproxy-ca-cert.pem      ← 给 Firefox/curl 用（PEM）
├── mitmproxy-ca-cert.cer      ← 给 Windows/Android 用
├── mitmproxy-ca-cert.p12      ← 给 iOS/macOS 用（双击导入）
└── mitmproxy-ca.pem           ← CA 私钥（⚠️ 绝不要外泄！）
```

> ⚠️ **`mitmproxy-ca.pem` 是私钥**。谁拿到它，就能伪造任何 HTTPS 站点。
> 不要提交到 git，不要发到聊天里，用完及时 `mitmproxy --set confdir=...` 隔离。

### 3.2 客户端配置

```bash
# curl
curl -x http://127.0.0.1:8080 https://example.com
curl -x http://127.0.0.1:8080 --cacert ~/.mitmproxy/mitmproxy-ca-cert.pem https://example.com

# 环境变量（大多数 CLI 工具认这两个）
export HTTP_PROXY=http://127.0.0.1:8080
export HTTPS_PROXY=http://127.0.0.1:8080
# ⚠️ 别忘 NO_PROXY，否则本机请求也会被代理
export NO_PROXY=127.0.0.1,localhost

# Python requests
proxies = {"http": "http://127.0.0.1:8080", "https": "http://127.0.0.1:8080"}
requests.get(url, proxies=proxies, verify="~/.mitmproxy/mitmproxy-ca-cert.pem")

# 浏览器：设置 → 网络 → 代理 → 手动 http/https = 127.0.0.1:8080
# 然后访问 http://mitm.it 下载对应平台的 CA 并安装信任
```

### 3.3 `mitmdump` 常用参数速查

```bash
# ── 监听 ──
mitmdump -p 8080                       # 端口
mitmdump --listen-host 0.0.0.0         # 对外监听（⚠️ 危险，仅内网授权场景）

# ── 模式 ──
mitmdump --mode regular                # 正向（默认）
mitmdump --mode transparent            # 透明（需 iptables）
mitmdump --mode reverse:http://127.0.0.1:3000   # 反向代理到本地上游
mitmdump --mode upstream:http://127.0.0.1:8081  # 走上游代理

# ── 流量控制（关键：只抓你想抓的）──
mitmdump -f "~u example\.com"          # 只看这个域
mitmdump -f "~m POST"                  # 只看 POST
mitmdump -f "~s"                       # 只看响应
mitmdump -f "~u api" | mitmdump --ignore-hosts ".*\.png"

# ── 输出 ──
mitmdump -w flows.mitm                 # 保存为 mitm 格式（可回放/重分析）
mitmdump -r flows.mitm                 # 读取并重新处理
mitmdump --set save_stream_file=all.mitm
mitmdump -n                            # 不加载任何 addon（纯净模式，排查问题用）

# ── 加载脚本（核心用法）──
mitmdump -s my_addon.py
mitmdump -s my_addon.py --set my_option=1

# ── 常用 set 项 ──
--set confdir=./mitmconf               # 隔离配置目录（含 CA）
--set block_global=false               # 允许非本机客户端连进来
--set connection_strategy=lazy         # 延迟连接上游（配合 map_local 有用）
--set upstream_cert=false              # 不校验上游证书（⚠️ 仅测试环境）
--set ssl_insecure=true                # 同上，跳过 TLS 校验
--set stream_large_bodies=10m          # 大 body 流式处理阈值
--set termlog_verbosity=info
```

### 3.4 `mitmproxy` TUI 快捷键速查

```
┌─ 三个主页面 ───────────────────────────────────────┐
│  q        返回上一级 / 退出                          │
│  ?        帮助（所有快捷键）                          │
│  Enter    进入选中的 flow                            │
│  Tab      在 Request / Response / Detail 间切换      │
│  /        搜索（正则）                                │
│  f        过滤（输入 filter 表达式，如 ~u api）        │
│  z        清空当前视图                                │
└────────────────────────────────────────────────────┘

┌─ 编辑与重放 ───────────────────────────────────────┐
│  e        编辑（按类型选：headers / body / method）   │
│  r        重放（replay）该请求                        │
│  R        重放并编辑后重放                            │
│  d        删除                                       │
│  i        设置 interception 断点（拦截并暂停）         │
│  a        恢复被拦截的 flow                           │
│  A        恢复全部                                    │
│  m        标记 / 取消标记                             │
│  w        保存 body 到文件                            │
│  |        用外部命令处理 body（如 |jq）                │
└────────────────────────────────────────────────────┘
```

### 3.5 Addon 事件速查（最常用的 15 个）

```python
class Addon:
    # ─── 连接层 ───
    def client_connected(self, client): ...
    def client_disconnected(self, client): ...

    # ─── TLS 层 ───
    def tls_clienthello(self, data): ...          # 客户端 ClientHello（看 SNI）
    def tls_established_client(self, tls): ...

    # ─── HTTP 请求 ───
    def http_connect(self, flow): ...             # CONNECT 请求
    def requestheaders(self, flow): ...           # 只有头，body 未读
    def request(self, flow): ...                  # ✅ 最常用：请求完整
    def request_error(self, flow): ...

    # ─── HTTP 响应 ───
    def responseheaders(self, flow): ...          # 只有头
    def response(self, flow): ...                 # ✅ 最常用：响应完整
    def error(self, flow): ...                    # 上游出错

    # ─── WebSocket / TCP / UDP ───
    def websocket_start(self, flow): ...
    def websocket_message(self, flow): ...
    def tcp_message(self, flow): ...
    def udp_message(self, flow): ...

    # ─── 生命周期 ───
    def running(self): ...
    def done(self): ...
    def load(self, loader): ...                   # 注册自定义 --set 选项
```

### 3.6 `flow` 对象属性速查

```python
flow.id                      # 唯一 ID（str）
flow.client_conn             # 客户端连接对象（.peername, .tls_setup ...）
flow.server_conn             # 服务器连接对象（.peername, .address, .sni）
flow.request                 # HTTPFlow.request
flow.response                # HTTPFlow.response（可能为 None）
flow.error                   # 如果出错
flow.type                    # "http" / "websocket" / "tcp" / "udp"

# ── request / response 共有属性 ──
flow.request.method          # "GET"
flow.request.scheme          # "https"
flow.request.host            # "example.com"
flow.request.host_header     # 可以单独改（vhost 测试用）
flow.request.port            # 443
flow.request.path            # "/api/v1/users?page=2"（含 query）
flow.request.url             # 完整 URL
flow.request.headers         # Headers 对象（大小写不敏感）
flow.request.content         # bytes（原始字节）
flow.request.text            # str（自动解码，gzip 自动解）
flow.request.query           # MultiDictView（可直接改 query 参数）
flow.request.urlencoded_form # MultiDictView（表单）
flow.request.cookies         # MultiDictView
flow.request.json()          # 若 body 是 JSON → dict

# ── 常用改写操作 ──
flow.request.headers["Authorization"] = "Bearer xxx"
flow.request.headers.pop("Cookie", None)          # 删除头（注意用 pop）
flow.request.url = "http://127.0.0.1/admin"       # 改 URL（谨慎，会改 host）
flow.request.path = "/admin?x=1"
flow.request.query["page"] = "1"
flow.request.json = {"role": "admin"}             # 自动重算 Content-Length
flow.request.text = '{"role":"admin"}'
flow.request.content = b"raw bytes"

# ── 响应改写 ──
flow.response.status_code = 200
flow.response.reason = "OK"
flow.response.headers["X-Debug"] = "1"
flow.response.text = flow.response.text.replace("old", "new")
flow.response.content = b"<html>fake</html>"

# ── 直接构造响应（不发到上游）──
from mitmproxy import http
flow.response = http.Response.make(
    200,
    b'{"mock": true}',
    {"Content-Type": "application/json"},
)
```

### 3.7 常用 filter 表达式（`-f` / 搜索）

```
~u pattern        URL 包含
~u ^https://      URL 以此开头
~h pattern        请求头包含
~hq pattern       请求头（仅请求）
~hs pattern       响应头
~b pattern        请求体包含
~bs pattern       响应体包含
~m POST           method 匹配
~c 200            状态码匹配
~d example.com    域名匹配
~s                是响应（而非请求）
~q                是请求
~t regex          content-type 匹配
!~u example      取反
~u api & ~m POST 组合（& = and, | = or）
```

### 3.8 常见排错速查

| 现象 | 原因 | 解决 |
|---|---|---|
| 浏览器提示 `NET::ERR_CERT_AUTHORITY_INVALID` | CA 没装/没信任 | 访问 `http://mitm.it` 安装并信任 |
| 所有请求都 `502` | 上游连不上 / DNS 问题 | `--set upstream_cert=false`、检查网络 |
| 只看到 `CONNECT` 看不到内容 | 客户端没信任 CA（或 App pinning） | 装 CA / 处理 pinning |
| 改 body 后页面白屏 | 忘了重算 `Content-Length` | 用 `.text` / `.content` 赋值 |
| 代理越来越慢 | 事件循环被阻塞 | 别用 `time.sleep` / 同步 IO |
| 本机请求也被代理了 | `NO_PROXY` 没设 | `export NO_PROXY=127.0.0.1,localhost` |
| 抓不到手机 App | App 忽略系统代理 | 透明代理 或 反向代理 |

---
