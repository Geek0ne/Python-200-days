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

2. **Cookie 安全**：如果网站使用了 HttpOnly 和 Secure 标志的 Cookie，requests 库会如何处理？

3. **重试策略**：如果目标服务器返回 429 (Too Many Requests)，应该如何设计重试策略？（提示：考虑 Retry-After 头）

4. **连接池大小**：pool_connections 和 pool_maxsize 分别控制什么？如何根据并发需求调整？

5. **反爬虫对抗**：除了 User-Agent 伪装，还有哪些常见的反爬虫机制？如何绕过？
