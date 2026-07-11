# Day 064 — 网络请求：练习与检查表

## ✅ 今日完成清单

- [ ] 理解 HTTP 协议基础（请求方法/状态码/请求头）
- [ ] 掌握 urllib.request 的基础用法
- [ ] 掌握 requests 库的 GET/POST 请求
- [ ] 理解 urllib vs requests 的优缺点对比
- [ ] 掌握 requests.Session 的 Cookie 自动管理
- [ ] 理解连接池与重试机制
- [ ] 了解各种认证方式（Basic/Bearer/Digest）
- [ ] 掌握请求钩子（Hooks）的用法
- [ ] 完成实战：天气预报 CLI 工具

---

## 📝 练习题

### 基础题

#### 题 1：GET 请求参数对比

分别用 urllib 和 requests 实现以下功能：
1. 向 `https://httpbin.org/get` 发送 GET 请求
2. 带上参数 `q=python教程&page=1&lang=zh`
3. 打印状态码和返回的参数字段

对比两种方式的代码行数差异。

#### 题 2：POST JSON 数据

向 `https://httpbin.org/post` 发送 POST 请求，发送以下 JSON 数据：

```python
{
    "title": "Python 网络编程",
    "author": "张三",
    "tags": ["Python", "HTTP", "requests"],
    "year": 2026
}
```

要求：用 requests 的 `json` 参数发送，验证服务器返回的 `json` 字段与发送数据一致。

#### 题 3：自定义请求头

某 API 需要以下请求头才能访问：
```http
User-Agent: MyCrawler/2.0
Authorization: Bearer sk-xxxxxxxxxxxx
X-Request-ID: req-001
Accept-Language: zh-CN,en;q=0.9
```

编写代码发送请求到 `https://httpbin.org/headers`，验证服务器确实收到了这些请求头。

---

### 进阶题

#### 题 4：Session 登录模拟

模拟一个网站的登录流程：
1. 用 `requests.Session()` 创建会话
2. 访问 `https://httpbin.org/cookies/set?user=alice&role=admin` 模拟登录
3. 访问 `https://httpbin.org/cookies` 验证 Cookie 已保存
4. 创建一个新的 Session，对比——新 Session 不会携带这些 Cookie
5. 手动将 Cookie 设置到新 Session，验证成功

#### 题 5：带重试的文件下载器

编写一个 `RobustDownloader` 类，支持：
1. 从 URL 下载文件到本地
2. 自动重试（3 次，指数退避）
3. 断点续传（如果服务器支持 Range 头）
4. 下载进度显示
5. 超时设置

```python
downloader = RobustDownloader()
downloader.download(
    "https://example.com/large-file.zip",
    "output.zip",
    timeout=30,
    resume=True
)
```

---

## 💡 挑战题

编写一个 `AsyncWebScraper` 类，使用 `concurrent.futures.ThreadPoolExecutor`（或 `asyncio + aiohttp`）实现并发网络请求：

```python
scraper = AsyncWebScraper(max_workers=10)
results = scraper.fetch_all([
    "https://api.example.com/endpoint1",
    "https://api.example.com/endpoint2",
    "https://api.example.com/endpoint3",
    # ... 50 个 URL
])
```

要求：
1. 支持最大并发数控制
2. 单请求超时
3. 自动重试失败请求
4. 统计成功/失败数量
5. 顺序保证（结果列表顺序与输入 URL 顺序一致）

---

## 📚 参考资料

- [urllib.request 官方文档](https://docs.python.org/3/library/urllib.request.html)
- [requests 官方文档](https://requests.readthedocs.io/)
- [HTTP 状态码 (MDN)](https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status)
- [wttr.in 天气 API](https://github.com/chubin/wttr.in)
- [urllib3 Retry 文档](https://urllib3.readthedocs.io/en/latest/reference/urllib3.util.html#urllib3.util.retry.Retry)
