# Day 064 — 网络请求

## 概述

网络请求是 Python 与外部世界通信的基础。无论是调用 API、爬取网页、还是与云服务交互，都离不开 HTTP 请求。Python 提供了标准库 `urllib` 和更强大的第三方库 `requests`，本日将全面掌握这两者。

---

## 1. HTTP 协议基础

### 1.1 什么是 HTTP？

HTTP（HyperText Transfer Protocol，超文本传输协议）是客户端和服务器之间通信的协议。它的核心设计理念是 **请求-响应模型**：

```
客户端 (Client)                    服务器 (Server)
    │                                  │
    │─────── HTTP 请求 ──────────────→ │
    │  GET /api/users HTTP/1.1         │
    │  Host: example.com              │
    │  Authorization: Bearer xxx      │
    │                                  │
    │←────── HTTP 响应 ──────────────│
    │  HTTP/1.1 200 OK                │
    │  Content-Type: application/json │
    │  {"users": [...]}               │
    │                                  │
```

### 1.2 HTTP 请求方法

| 方法 | 用途 | 幂等 | 安全 | 请求体 |
|------|------|------|------|--------|
| `GET` | 获取资源 | ✅ | ✅ | ❌ |
| `POST` | 创建资源 | ❌ | ❌ | ✅ |
| `PUT` | 完整更新资源 | ✅ | ❌ | ✅ |
| `PATCH` | 部分更新资源 | ❌ | ❌ | ✅ |
| `DELETE` | 删除资源 | ✅ | ❌ | 可选 |
| `HEAD` | 获取响应头（无响应体） | ✅ | ✅ | ❌ |
| `OPTIONS` | 获取服务器支持的选项 | ✅ | ✅ | ❌ |

> **幂等**：多次执行结果相同。**安全**：不会改变服务器状态。

### 1.3 HTTP 状态码

```mermaid
graph TD
    subgraph "1xx 信息"
        A1["100 Continue"]
        A2["101 Switching Protocols"]
    end
    subgraph "2xx 成功"
        B1["200 OK"]
        B2["201 Created"]
        B3["204 No Content"]
    end
    subgraph "3xx 重定向"
        C1["301 Moved Permanently"]
        C2["302 Found"]
        C3["304 Not Modified"]
    end
    subgraph "4xx 客户端错误"
        D1["400 Bad Request"]
        D2["401 Unauthorized"]
        D3["403 Forbidden"]
        D4["404 Not Found"]
        D5["429 Too Many Requests"]
    end
    subgraph "5xx 服务器错误"
        E1["500 Internal Server Error"]
        E2["502 Bad Gateway"]
        E3["503 Service Unavailable"]
    end
```

**常见状态码速记：**

| 状态码 | 含义 | 场景 |
|--------|------|------|
| `200` | ✅ OK | 请求成功 |
| `201` | ✅ Created | POST 创建成功 |
| `204` | ✅ No Content | 删除成功 |
| `301` | 🔀 永久重定向 | 网站更换域名 |
| `302` | 🔀 临时重定向 | 登录后跳转 |
| `400` | ❌ Bad Request | 参数错误 |
| `401` | ❌ Unauthorized | 未登录 |
| `403` | ❌ Forbidden | 无权限 |
| `404` | ❌ Not Found | 资源不存在 |
| `429` | ❌ Too Many Requests | 请求频率限制 |
| `500` | 💥 服务器错误 | 后端异常 |
| `502` | 💥 Bad Gateway | 网关/代理错误 |
| `503` | 💥 服务不可用 | 服务器过载/维护 |

### 1.4 HTTP 请求头（Headers）

```http
# ─── 通用请求头 ───
Host: api.example.com           # 目标主机（HTTP/1.1 必需）
User-Agent: Mozilla/5.0 ...     # 客户端标识
Accept: application/json        # 期望的响应格式
Accept-Language: zh-CN,en       # 接受的语言
Connection: keep-alive          # 连接复用

# ─── 认证相关 ───
Authorization: Bearer eyJ...    # Bearer Token
Authorization: Basic base64...  # Basic Auth
Cookie: session_id=abc123       # Cookie

# ─── 内容相关 ───
Content-Type: application/json  # 请求体格式
Content-Length: 123             # 请求体长度

# ─── 缓存与控制 ───
Cache-Control: no-cache         # 缓存策略
If-Modified-Since: Mon, ...     # 条件请求
```

---

## 2. urllib — Python 标准库

### 2.1 概念

`urllib` 是 Python 内置的 HTTP 请求库，无需安装。但它 API 设计较为底层，用法不如 `requests` 直观。

> ⚠️ urllib.request 的 `urlopen()` 返回的是类文件对象（http.client.HTTPResponse），需要手动处理编码、异常等。

### 2.2 核心 API

```python
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote, urlparse
from urllib.error import HTTPError, URLError

# ─── GET 请求 ───
response = urlopen('https://api.example.com/users')
data = response.read().decode('utf-8')   # bytes → str
status = response.status                  # 状态码
headers = response.headers                # 响应头

# ─── POST 请求 ───
data = urlencode({'key': 'value'}).encode()
req = Request('https://api.example.com/post', data=data,
              headers={'Content-Type': 'application/x-www-form-urlencoded'})
response = urlopen(req)

# ─── 自定义请求头 ───
req = Request('https://api.example.com/users',
              headers={
                  'User-Agent': 'Mozilla/5.0',
                  'Authorization': 'Bearer token123'
              })
response = urlopen(req)

# ─── URL 编码 ───
# 中文/特殊字符在 URL 中需要编码
encoded = quote('你好世界')  # %E4%BD%A0%E5%A5%BD...
params = urlencode({'q': 'Python教程', 'page': 1})
# 'q=Python%E6%95%99%E7%A8%8B&page=1'

# ─── URL 解析 ───
parsed = urlparse('https://user:pass@api.com:8080/path?a=1#frag')
# parsed.scheme → 'https'
# parsed.netloc → 'user:pass@api.com:8080'
# parsed.path → '/path'
# parsed.query → 'a=1'

# ─── 异常处理 ───
try:
    response = urlopen('https://api.example.com/nonexistent')
except HTTPError as e:
    print(f"HTTP 错误: {e.code} - {e.reason}")
except URLError as e:
    print(f"URL 错误: {e.reason}")
```

### 2.3 urllib 的缺点

| 问题 | 说明 |
|------|------|
| **API 过于底层** | 需要手动 encode/decode，处理响应体 |
| **缺少 Session** | 每次请求独立，Cookie 需手动管理 |
| **异常处理繁琐** | HTTPError / URLError 需要逐级捕获 |
| **JSON 支持差** | 需要 json.loads(response.read().decode()) |
| **上传文件复杂** | 需要自己构造 multipart/form-data |
| **超时设置** | 默认无超时，需手动设置 timeout 参数 |

```python
# urllib 实现一个"简单"的 POST JSON 请求
import json
from urllib.request import Request, urlopen

data = json.dumps({"name": "Alice"}).encode()
req = Request('https://api.example.com/users',
              data=data,
              headers={'Content-Type': 'application/json'})
resp = urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
```

---

## 3. requests — 现代 HTTP 库

### 3.1 概念

`requests` 是 Python 生态中最流行的 HTTP 库，以 `HTTP for Humans` 为设计理念，API 简洁优雅。

**安装：** `pip install requests`

### 3.2 核心 API

```python
import requests

# ─── GET 请求 ───
response = requests.get('https://api.example.com/users')
print(response.status_code)     # 200
print(response.json())           # 自动解析 JSON
print(response.text)             # 文本响应体
print(response.content)          # 二进制响应体
print(response.headers)          # 响应头

# 带参数
response = requests.get('https://api.example.com/search',
                        params={'q': 'python', 'page': 1})

# ─── POST 请求 ───
# JSON 数据
response = requests.post('https://api.example.com/users',
                         json={'name': 'Alice', 'age': 30})

# 表单数据
response = requests.post('https://api.example.com/login',
                         data={'username': 'admin', 'password': '123456'})

# 文件上传
files = {'file': open('report.pdf', 'rb')}
response = requests.post('https://api.example.com/upload', files=files)

# 多个文件
files = [
    ('file1', ('report1.pdf', open('report1.pdf', 'rb'), 'application/pdf')),
    ('file2', ('report2.pdf', open('report2.pdf', 'rb'), 'application/pdf')),
]
response = requests.post('https://api.example.com/upload', files=files)

# ─── 请求头 ───
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0)',
    'Authorization': 'Bearer token123',
    'Accept-Language': 'zh-CN',
}
response = requests.get('https://api.example.com/data', headers=headers)

# ─── 超时设置 ───
response = requests.get('https://api.example.com', timeout=5)  # 5秒超时
response = requests.get('https://api.example.com', timeout=(3, 10))  # (连接超时, 读取超时)

# ─── 代理 ───
proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'https://proxy.example.com:8080',
}
response = requests.get('https://api.example.com', proxies=proxies)

# ─── SSL 验证 ───
response = requests.get('https://api.example.com', verify=True)     # 默认验证
response = requests.get('https://api.example.com', verify=False)    # ⚠️ 跳过验证

# ─── 重定向 ───
response = requests.get('https://api.example.com', allow_redirects=True)   # 默认自动跟随

# ─── 流式响应 ───
response = requests.get('https://api.example.com/large-file', stream=True)
for chunk in response.iter_content(chunk_size=8192):
    process(chunk)
```

### 3.3 urllib vs requests 对比

```python
# ─── urllib ───
from urllib.request import Request, urlopen
import json

data = json.dumps({"key": "value"}).encode()
req = Request("http://api.example.com/data",
              data=data,
              headers={"Content-Type": "application/json"})
resp = urlopen(req, timeout=10)
result = json.loads(resp.read().decode())

# ─── requests ───
import requests

result = requests.post("http://api.example.com/data",
                        json={"key": "value"},
                        timeout=10).json()
```

| 特性 | urllib | requests |
|------|--------|----------|
| **安装** | 内置 | 需安装 |
| **API 简洁度** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **JSON 支持** | 需手动转换 | 自动 `.json()` |
| **Session** | 无 | ✅ `requests.Session()` |
| **Cookie** | 手动 | 自动管理 |
| **连接池** | 无 | ✅ urllib3 支持 |
| **重试机制** | 无 | 配合 `requests.adapters` |
| **文件上传** | 复杂 | 一行代码 |
| **流式响应** | 支持 | 支持 |
| **SSL 验证** | 需额外配置 | 默认配置好 |

---

## 4. Session / Cookie 管理

### 4.1 概念

HTTP 是无状态的，每次请求都是独立的。Session 和 Cookie 用于维护客户端和服务器之间的状态。

- **Cookie**：存储在客户端的小数据片段，由服务器通过 `Set-Cookie` 响应头设置
- **Session**：存储在服务器端的会话数据，通过 Session ID（通常存在 Cookie 中）关联

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    
    C->>S: POST /login (username, password)
    S->>S: 验证身份
    S->>S: 创建 Session（session_id=abc123）
    S->>C: Set-Cookie: session_id=abc123
    
    C->>S: GET /profile
    Note over C: Cookie: session_id=abc123
    S->>S: 查找 session_id=abc123
    S->>C: 200 OK (用户信息)
    
    C->>S: GET /logout
    S->>S: 销毁 session_id=abc123
    S->>C: Set-Cookie: session_id=; Max-Age=0
```

### 4.2 requests.Session 使用

```python
import requests

# 创建 Session 对象
session = requests.Session()

# Session 会自动保存 Cookie
session.get('https://httpbin.org/cookies/set?name=alice')

# 后续请求自动携带 Cookie
response = session.get('https://httpbin.org/cookies')
print(response.json())  # {'cookies': {'name': 'alice'}}

# Session 级别的配置（所有请求共享）
session.headers.update({'User-Agent': 'MyApp/1.0'})
session.verify = False  # 所有请求跳过 SSL 验证
session.timeout = 10    # 所有请求默认超时

# 挂载适配器（配置重试）
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,                      # 总重试次数
    backoff_factor=1,             # 退避因子（等待 1, 2, 4 秒）
    status_forcelist=[429, 500, 502, 503, 504],  # 重试的状态码
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 使用底层连接池（性能提升）
# requests.Session 底层使用 urllib3 的连接池
# 默认连接池大小 10，可通过适配器调整
```

### 4.3 Cookie 手动管理

```python
import requests

# 查看响应中的 Cookie
response = requests.get('https://httpbin.org/cookies/set?name=alice')
for cookie in response.cookies:
    print(f"{cookie.name}: {cookie.value} (domain={cookie.domain})")

# 手动设置 Cookie
cookies = {'session_id': 'abc123', 'user_pref': 'theme=dark'}
response = requests.get('https://api.example.com/user',
                        cookies=cookies)

# CookieJar 对象
from http.cookiejar import CookieJar

jar = CookieJar()
session = requests.Session()
session.cookies = jar
```

---

## 5. 实战：天气预报 CLI

详见 `code/03-weather-cli.py`

实现一个命令行天气查询工具，支持：
- 通过城市名称查询实时天气
- 天气缓存
- 友好的 CLI 输出
- 错误处理和重试

---

## 6. 思考题

1. **为什么 POST 请求不是幂等的？** 同样的 POST 请求重复提交一次和两次会有什么不同的后果？
2. **301 和 302 重定向的区别是什么？** 为什么浏览器对 301 和 302 的缓存行为不同？
3. **HTTP/2 和 HTTP/3 主要解决了 HTTP/1.1 的哪些问题？** 头压缩、多路复用、队头阻塞分别是什么？
4. **为什么 requests 库能成为最流行的 Python 库之一？** 它的 API 设计具体做了哪些让开发者"爽"的事情？
5. **Session 和 Token（JWT）两种认证方式的优缺点是什么？** 为什么现在越来越多的项目选择 JWT？

---

## 7. 最佳实践总结

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 简单 GET 请求 | requests | 一行代码搞定 |
| 复杂 API 调用 | requests.Session | Cookie 自动管理 + 连接池 |
| 需要重试 | HTTPAdapter + Retry | 优雅处理网络波动 |
| 文件下载 | stream=True + iter_content | 避免内存溢出 |
| 批量请求 | requests.Session + 连接池 | 性能提升 10x+ |
| 爬虫 | requests + Session + Headers | 模拟浏览器 |
| 系统内置/无依赖 | urllib | 无需 pip install |
