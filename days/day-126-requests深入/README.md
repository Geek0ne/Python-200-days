# Day 126 — Requests 深入

> 🎯 **今日目标**：深入掌握 `requests` 库的高级用法，包括 Session 会话保持、Cookie 管理、请求头伪装、超时控制、连接池、重试机制等。

---

## 📋 概念总览

`requests` 是 Python 最流行的 HTTP 客户端库，但大多数人只用到了最基础的功能。本日深入讲解其高级特性。

### 为什么需要深入学习 requests？

| 基础用法 | 高级用法 |
|---------|---------|
| `requests.get(url)` | Session 会话保持 |
| 简单的参数传递 | 复杂的认证机制 |
| 同步阻塞请求 | 连接池复用 |
| 无重试机制 | 自动重试与降级 |
| 默认 User-Agent | 精细的请求头伪装 |

---

## 🔄 Session 会话保持

### 什么是 Session？

```python
import requests

# ❌ 基础用法：每次请求都是独立的
response = requests.get("https://httpbin.org/cookies/set/token/abc123")
print(response.cookies)  # {'token': 'abc123'}
# 但下一次请求不会携带这个 cookie！

# ✅ 高级用法：使用 Session 保持会话
session = requests.Session()
response = session.get("https://httpbin.org/cookies/set/token/abc123")
print(session.cookies.get("token"))  # abc123
# Session 会自动管理 cookies
```

### Session 的原理

```
┌──────────────────────────────────────────────────────────┐
│                    requests Session 架构                   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────┐                                     │
│  │ requests.Session │                                     │
│  │                 │                                     │
│  │  ┌───────────┐  │    ┌──────────────┐                │
│  │  │ cookies   │──┼───▶│ Cookie Jar   │                │
│  │  │ (会话状态) │  │    │ (自动管理)    │                │
│  │  └───────────┘  │    └──────────────┘                │
│  │                 │                                     │
│  │  ┌───────────┐  │    ┌──────────────┐                │
│  │  │ headers   │──┼───▶│ 默认请求头    │                │
│  │  │ (公共头)   │  │    │ (所有请求共享)│                │
│  │  └───────────┘  │    └──────────────┘                │
│  │                 │                                     │
│  │  ┌───────────┐  │    ┌──────────────┐                │
│  │  │ auth      │──┼───▶│ 认证信息      │                │
│  │  │ (认证)    │  │    │ (自动附加)    │                │
│  │  └───────────┘  │    └──────────────┘                │
│  │                 │                                     │
│  │  ┌───────────┐  │    ┌──────────────┐                │
│  │  │ adapters  │──┼───▶│ 连接适配器    │                │
│  │  │ (连接池)   │  │    │ (HTTPAdapter)│                │
│  │  └───────────┘  │    └──────────────┘                │
│  │                 │                                     │
│  └─────────────────┘                                     │
│                                                          │
│  请求流程:                                                │
│  session.get(url)                                        │
│       │                                                  │
│       ▼                                                  │
│  1. 合并公共 headers                                      │
│  2. 附加 cookies                                         │
│  3. 附加 auth                                            │
│  4. 通过 adapter 发送请求                                 │
│  5. 更新 cookies（从响应中）                              │
│  6. 返回 Response                                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🍪 Cookie 管理

### 手动管理 Cookie

```python
import requests
from http.cookiejar import MozillaCookieJar

# 创建 Session 并加载/保存 cookies
session = requests.Session()

# 使用 MozillaCookieJar 自动保存 cookies 到文件
session.cookies = MozillaCookieJar("cookies.txt")

# 发送请求，cookies 会自动保存
response = session.get("https://httpbin.org/cookies/set/token/abc123")

# 手动添加 cookie
session.cookies.set("session_id", "xyz789", domain=".example.com")

# 从文件加载 cookies（下次启动时恢复会话）
session.cookies.load(ignore_discard=True, ignore_expires=True)

# 保存 cookies 到文件
session.cookies.save(ignore_discard=True, ignore_expires=True)
```

### Cookie 参数详解

```python
# cookies 参数的多种用法
# 1. 字典
requests.get(url, cookies={"token": "abc"})

# 2. CookieJar 对象
from requests.cookies import RequestsCookieJar
jar = RequestsCookieJar()
jar.set("token", "abc", domain=".example.com", path="/")
requests.get(url, cookies=jar)

# 3. 从响应中提取 cookies
resp = requests.get(url)
session_cookie = resp.cookies.get("session_id")
```

---

## 🎭 请求头伪装

### User-Agent 伪装

```python
import random

# 常见的 User-Agent 列表
USER_AGENTS = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

def get_random_ua():
    """随机获取 User-Agent"""
    return random.choice(USER_AGENTS)

# 使用
session = requests.Session()
session.headers.update({
    "User-Agent": get_random_ua(),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
})
```

### Referer 伪造

```python
# 模拟从搜索引擎跳转
session.headers.update({
    "Referer": "https://www.google.com/",
    "User-Agent": get_random_ua(),
})

# 某些网站会检查 Referer 来源
response = session.get("https://target-site.com/page")
```

### 完整的请求头模板

```python
def create_session():
    """创建伪装的 Session"""
    session = requests.Session()

    # 基础请求头
    session.headers.update({
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7,en-GB;q=0.6",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    })

    return session
```

---

## ⏱️ 超时与重试

### 超时控制

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 方式一：简单的超时
try:
    response = requests.get(
        "https://httpbin.org/delay/5",
        timeout=(3, 10)  # (连接超时, 读取超时)
    )
except requests.Timeout:
    print("请求超时")

# 方式二：使用 Session + 重试
session = requests.Session()
retries = Retry(
    total=3,                    # 总重试次数
    backoff_factor=1,           # 退避因子: 0, 1, 2, 4 秒
    status_forcelist=[500, 502, 503, 504],  # 触发重试的状态码
    allowed_methods=["GET", "POST"],         # 允许重试的方法
)

adapter = HTTPAdapter(
    max_retries=retries,
    pool_connections=10,        # 连接池大小
    pool_maxsize=10,            # 最大连接数
)
session.mount("http://", adapter)
session.mount("https://", adapter)

response = session.get("https://httpbin.org/get", timeout=5)
```

### 重试策略图解

```
┌──────────────────────────────────────────────────────────┐
│                    重试策略流程                            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  请求发送                                                 │
│     │                                                    │
│     ▼                                                    │
│  ┌──────────┐     成功     ┌──────────┐                 │
│  │ 发送请求  │────────────▶│ 返回响应  │                 │
│  └────┬─────┘              └──────────┘                 │
│       │                                                  │
│       │ 失败                                             │
│       ▼                                                  │
│  ┌──────────┐     不在列表  ┌──────────┐                 │
│  │ 检查状态码│─────────────▶│ 抛出异常  │                 │
│  └────┬─────┘              └──────────┘                 │
│       │                                                  │
│       │ 在重试列表中                                       │
│       ▼                                                  │
│  ┌──────────┐     已达上限  ┌──────────┐                 │
│  │ 检查重试数│─────────────▶│ 抛出异常  │                 │
│  └────┬─────┘              └──────────┘                 │
│       │                                                  │
│       │ 未达上限                                          │
│       ▼                                                  │
│  ┌──────────┐                                           │
│  │ 等待退避  │  等待 0s → 1s → 2s → 4s                   │
│  └────┬─────┘                                           │
│       │                                                  │
│       └──────▶ 重新发送请求                               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 🔗 连接池

```python
from requests.adapters import HTTPAdapter

# 连接池配置
adapter = HTTPAdapter(
    pool_connections=10,    # 连接到目标服务器的连接池大小
    pool_maxsize=10,        # 连接池最大连接数
    max_retries=3,          # 最大重试次数
)

session = requests.Session()
session.mount("https://", adapter)

# 高并发请求时，连接池会复用 TCP 连接
import concurrent.futures

def fetch(url):
    return session.get(url, timeout=5).status_code

urls = ["https://httpbin.org/get"] * 10
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(fetch, urls))
    print(results)  # [200, 200, 200, ...]
```

---

## 🔐 认证机制

```python
from requests.auth import HTTPBasicAuth, HTTPDigestAuth, AuthBase

# 1. Basic Auth
response = requests.get(url, auth=("user", "pass"))

# 2. Digest Auth
response = requests.get(url, auth=HTTPDigestAuth("user", "pass"))

# 3. Token Auth (Bearer)
headers = {"Authorization": "Bearer your-token-here"}
response = requests.get(url, headers=headers)

# 4. 自定义认证
class TokenAuth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["Authorization"] = f"Token {self.token}"
        return r

response = requests.get(url, auth=TokenAuth("your-token"))
```

---

## 📊 性能对比

| 特性 | 基础用法 | Session 用法 |
|------|---------|-------------|
| Cookie 管理 | 手动 | 自动 |
| 连接复用 | ❌ | ✅ |
| 请求头共享 | ❌ | ✅ |
| 认证管理 | 每次指定 | 一次配置 |
| 重试机制 | 需手动实现 | 内置支持 |
| 连接池 | ❌ | ✅ |

**性能提升**：
- 连接复用可减少 30-50% 的延迟（省去 TCP 握手）
- 连接池可显著提升并发性能

---

## 💡 最佳实践

1. **始终使用 Session**：除非只发一次请求
2. **设置合理的超时**：避免无限等待
3. **使用连接池**：高并发场景必备
4. **随机化 User-Agent**：避免被识别为爬虫
5. **处理异常**：网络请求随时可能失败
6. **记录请求日志**：便于调试和监控

---

## 🤔 思考题

1. **Session vs 独立请求**：在什么场景下使用独立请求反而比 Session 更好？

**参考答案**

独立请求（`requests.get`）更合适的场景：

- **一次性请求**：只发一两次、不需要保持 cookie/连接，用 Session 反而多此一举，还要管理它的生命周期。
- **需要完全隔离的状态**：比如测试不同账号、不同 IP，不希望 cookie 互相"串味"。
- **多线程图省事**：Session 并非完全线程安全，每线程用独立请求可避免共享状态的顾虑。
- **临时脚本/探测**：写个小脚本只查一次某 API 版本号，一行 `requests.get` 就够。

⚠️ 注意：但只要是高频、对同一站点发多个请求，Session 的连接复用和自动 cookie 管理优势就很明显，应优先用 Session。

2. **Cookie 安全**：如果网站使用了 HttpOnly 和 Secure 标志的 Cookie，requests 库会如何处理？

**参考答案**

- **HttpOnly**：这是给浏览器 JavaScript 的限制（`document.cookie` 读不到它），目的是防 XSS 偷 cookie。requests 不是浏览器、不执行 JS，所以 HttpOnly 对它**没有影响**——它照常存储和发送这个 cookie。
- **Secure**：标记该 cookie 只能通过 HTTPS 发送。requests 底层用 `http.cookiejar`，会**遵守 Secure 标志**：访问 `http://` 时不带这个 cookie，访问 `https://` 时才带。

小例子：登录拿到一个 Secure 的 session cookie，后续必须用 `https://` 请求才能保持登录态；若误用 `http://`，cookie 不会被发送，服务器会认为你没登录。

⚠️ 注意：requests 不会自动把 http 升级成 https，协议要自己用对。

3. **重试策略**：如果目标服务器返回 429 (Too Many Requests)，应该如何设计重试策略？（提示：考虑 Retry-After 头）

**参考答案**

429 表示请求过频被限流。正确策略：

- **尊重 Retry-After 头**：服务器会告诉你多久后再来（秒数或 HTTP 日期），按它等待，别硬撞。
- **指数退避 + 抖动**：没有 Retry-After 时用退避（1s→2s→4s）并加随机抖动，避免大量客户端同步重试。
- **限制重试次数**：超限就放弃或降级，别无限重试。
- **从源头降速**：降低并发/请求速率，减少 429 发生。

用 urllib3 的 `Retry(respect_retry_after_header=True, status_forcelist=[429, ...])` 挂到 `HTTPAdapter` 即可自动处理。下面用本地 mock 服务器演示（完全离线，需先 `pip install requests`）：

```python
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- 本地模拟服务器：前两次返回 429，第三次返回 200 ----------
class MockHandler(BaseHTTPRequestHandler):
    hits = 0  # 记录收到的请求次数

    def do_GET(self):
        MockHandler.hits += 1
        if MockHandler.hits <= 2:
            self.send_response(429)
            self.send_header("Retry-After", "1")  # 服务器要求：1 秒后再来
            self.end_headers()
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def log_message(self, *args):  # 关闭默认访问日志，输出更干净
        pass

server = HTTPServer(("127.0.0.1", 0), MockHandler)  # 端口 0 = 自动分配空闲端口
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

# ---------- 配置"尊重 Retry-After"的自动重试 ----------
session = requests.Session()
retries = Retry(
    total=5,                                   # 最多重试 5 次
    status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码触发重试
    respect_retry_after_header=True,           # 关键：按服务器要求的时间等待
    backoff_factor=0.5,                        # 没有 Retry-After 头时的退避基数
)
session.mount("http://", HTTPAdapter(max_retries=retries))

start = time.monotonic()
resp = session.get(f"http://127.0.0.1:{port}/", timeout=5)
elapsed = time.monotonic() - start
print("状态码:", resp.status_code, "内容:", resp.text)
print(f"共请求 {MockHandler.hits} 次，耗时 {elapsed:.1f} 秒（两次各等 1 秒）")
server.shutdown()
```

预期输出：

```
状态码: 200 内容: OK
共请求 3 次，耗时 2.0 秒（两次各等 1 秒）
```

客户端收到两次 429 后，各按 `Retry-After: 1` 等待 1 秒再重试，第三次成功，总耗时约 2 秒。

⚠️ 合规提示：遵守网站限流规则与 robots.txt，退避是为了"礼貌"而非恶意绕过限流。

4. **连接池大小**：pool_connections 和 pool_maxsize 分别控制什么？如何根据并发需求调整？

**参考答案**

- **`pool_connections`**：连接池的"池子数量"，即缓存多少个**不同主机**的连接池（对应 urllib3 的 `num_pools`）。
- **`pool_maxsize`**：每个池子里最多保存多少条**可复用连接**（对应 `maxsize`），针对同一主机。

一句话：前者管"对多少个不同主机保持池"，后者管"对同一主机最多复用几条连接"。

调整建议：

- 高并发抓**同一站点** → 调大 `pool_maxsize`（≥ 并发线程数），避免连接不够用而频繁新建/丢弃。
- 爬**很多不同域名** → 调大 `pool_connections`。

小例子：5 个线程并发抓同一站，`pool_maxsize=10` 就够用。

⚠️ 注意：`pool_maxsize` 不是硬上限，超出时仍会新建连接，但用完即弃（并可能告警"连接池已满"），复用效率下降。

5. **反爬虫对抗**：除了 User-Agent 伪装，还有哪些常见的反爬虫机制？如何绕过？

**参考答案**

常见反爬机制：

- **IP 频率限制/封禁**：同一 IP 请求过快被限流或拉黑。
- **请求头校验**：检查 UA、Referer、Accept 等是否像真实浏览器。
- **Cookie/登录态/Token 校验**：要求携带有效会话。
- **JS 挑战/动态渲染**：内容需执行 JS 才出现。
- **验证码**：滑块、点选等。
- **浏览器/TLS 指纹**（如 JA3）：识别 requests/curl 的流量特征。
- **行为分析**：鼠标轨迹、请求时序异常。

在合法合规前提下的应对：降低速率 + 指数退避、用 Session 保持登录态、完善请求头、动态页面改用 Selenium/Playwright、必要时用代理池分散 IP，以及**优先使用官方 API**。

⚠️ 合规提示：遵守 robots.txt 与网站服务条款，控制频率不影响对方服务；不要破解验证码、绕过付费墙或抓取受保护的个人数据。对抗技术仅用于理解原理，生产环境应优先取得授权或使用官方接口。
