# Day 076 — Web 爬虫系统：Scrapy 框架入门

## 概述

Phase 6 实战项目的第一天，我们开始构建**电商价格监控系统**。今天先打好基础——学习 Python 最强大的爬虫框架 **Scrapy**。

**今天你将学到：**
1. Scrapy 框架的核心架构与组件
2. 创建并运行第一个 Scrapy 爬虫
3. 数据管道（Pipeline）的使用
4. 请求调度与去重机制
5. 常见反爬策略的应对方法

> 💡 **为什么用 Scrapy 而不是 requests + BeautifulSoup？**
> - Scrapy 内置异步并发，性能远超手动 requests
> - 框架级的去重、重试、限速，不用自己造轮子
> - Pipeline 机制让数据清洗、存储流水线化
> - 生态成熟，社区活跃，遇到问题容易找到解决方案

---

## 1. Scrapy 架构总览

### 1.1 核心组件

```
┌─────────────────────────────────────────────────────┐
│                    Scrapy Engine                      │
│              （调度所有组件之间的数据流）                 │
└──────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Scheduler │ │Downloader│ │  Spider  │ │ Item     │
│ 调度器    │ │ 下载器    │ │ 爬虫     │ │ Pipeline │
│ 请求队列  │ │ HTTP请求  │ │ 解析逻辑  │ │ 数据处理  │
│ 去重      │ │ 响应下载  │ │ 提取数据  │ │ 存储      │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

### 1.2 数据流详解

```
1. Spider 生成初始请求 (Request)
        │
        ▼
2. Engine 将请求传递给 Scheduler（调度器）
        │
        ▼
3. Scheduler 将请求入队（自动去重）
        │
        ▼
4. Engine 从 Scheduler 取出下一个请求
        │
        ▼
5. Engine 将请求传递给 Downloader（下载器）
        │
        ▼
6. Downloader 发送 HTTP 请求，接收响应 (Response)
        │
        ▼
7. Downloader 将响应返回给 Engine
        │
        ▼
8. Engine 将响应传递给 Spider 进行解析
        │
        ▼
9. Spider 解析响应，产出：
   - Item（数据）→ 交给 Pipeline 处理
   - 新的 Request → 回到步骤 2
        │
        ▼
10. Pipeline 处理 Item（清洗、验证、存储）
```

### 1.3 各组件职责

| 组件 | 职责 | 关键类 |
|------|------|--------|
| **Engine** | 控制数据流，触发信号 | `scrapy.engine.Engine` |
| **Scheduler** | 请求调度、去重 | `scrapy.scheduler.Scheduler` |
| **Downloader** | 执行 HTTP 请求 | `scrapy.downloader.Downloader` |
| **Spider** | 定义爬取逻辑和解析规则 | 自定义继承 `scrapy.Spider` |
| **Item Pipeline** | 清洗和存储数据 | 自定义实现 `open_spider/process_item/close_spider` |
| **Spider Middleware** | Spider 输入输出的钩子 | `SpiderMiddlewareManager` |
| **Downloader Middleware** | 请求/响应的预处理 | `DownloaderMiddlewareManager` |

---

## 2. 安装与项目创建

### 2.1 安装 Scrapy

```bash
pip install scrapy
# 验证安装
scrapy version
```

### 2.2 创建项目

```bash
scrapy startproject myspider
cd myspider
```

生成的目录结构：

```
myspider/
├── scrapy.cfg           # 项目配置文件
└── myspider/            # 项目模块
    ├── __init__.py
    ├── items.py         # 数据模型定义
    ├── middlewares.py   # 中间件
    ├── pipelines.py     # 数据管道
    ├── settings.py      # 项目设置
    └── spiders/         # 爬虫目录
        └── __init__.py
```

### 2.3 创建爬虫

```bash
# 方式一：命令行创建
scrapy genspider example example.com

# 方式二：手动在 spiders/ 下创建 Python 文件
```

---

## 3. 编写第一个 Spider

### 3.1 基础结构

```python
import scrapy

class QuotesSpider(scrapy.Spider):
    """名言爬虫 - 爬取 quotes.toscrape.com"""
    
    # 爬虫名称（运行时使用）
    name = "quotes"
    
    # 允许的域名（限制爬取范围）
    allowed_domains = ["quotes.toscrape.com"]
    
    # 起始 URL 列表
    start_urls = ["https://quotes.toscrape.com/"]
    
    def parse(self, response):
        """解析首页，提取名言和作者"""
        for quote in response.css("div.quote"):
            yield {
                "text": quote.css("span.text::text").get(),
                "author": quote.css("small.author::text").get(),
                "tags": quote.css("div.tags a.tag::text").getall(),
            }
        
        # 提取下一页链接，递归爬取
        next_page = response.css("li.next a::attr(href)").get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)
```

### 3.2 运行爬虫

```bash
# 基本运行
scrapy crawl quotes

# 输出为 JSON 文件
scrapy crawl quotes -o quotes.json

# 输出为 CSV 文件
scrapy crawl quotes -o quotes.csv

# 限制爬取数量
scrapy crawl quotes -s CLOSESPIDER_ITEMCOUNT=100
```

### 3.3 Selector 详解

Scrapy 的 Selector 支持 CSS 和 XPath 两种选择器：

```python
# CSS 选择器
response.css("h1.title::text").get()        # 提取文本
response.css("a::attr(href)").getall()       # 提取所有链接
response.css("div.post").getall()            # 提取所有匹配元素

# XPath 选择器
response.xpath("//h1[@class='title']/text()").get()
response.xpath("//a/@href").getall()

# 链式调用
response.css("div.quote") \
    .css("span.text::text") \
    .get()
```

**CSS 选择器速查：**

| 选择器 | 说明 | 示例 |
|--------|------|------|
| `tag` | 元素名 | `div`, `a`, `span` |
| `.class` | 类名 | `.title`, `.post` |
| `#id` | ID | `#main` |
| `[attr=val]` | 属性 | `a[href]`, `div[class="main"]` |
| `::text` | 文本内容 | `span::text` |
| `::attr(name)` | 属性值 | `a::attr(href)` |
| `>` | 直接子元素 | `div > a` |
| 空格 | 后代元素 | `div a` |

---

## 4. Item 与 Item Pipeline

### 4.1 定义 Item

Item 是 Scrapy 中的数据模型，类似于 Django 的 Model：

```python
# items.py
import scrapy

class QuoteItem(scrapy.Item):
    """名言数据模型"""
    text = scrapy.Field()       # 名言内容
    author = scrapy.Field()     # 作者
    tags = scrapy.Field()       # 标签列表
```

使用 Item 的好处：
- 有明确的数据结构定义
- 支持字段验证
- 方便 Pipeline 处理
- 序列化更规范

### 4.2 Item Pipeline

Pipeline 在 Spider 产出 Item 后进行处理：

```python
# pipelines.py
import json
import logging

class ValidationPipeline:
    """验证管道 - 检查数据完整性"""
    
    def process_item(self, item, spider):
        """处理每条数据"""
        # 检查必填字段
        if not item.get("text"):
            raise scrapy.exceptions.DropItem("缺少名言内容")
        if not item.get("author"):
            raise scrapy.exceptions.DropItem("缺少作者信息")
        
        # 清洗数据
        item["text"] = item["text"].strip()
        item["author"] = item["author"].strip()
        
        return item


class DuplicateFilterPipeline:
    """去重管道 - 过滤重复数据"""
    
    def __init__(self):
        self.seen_authors = set()
    
    def process_item(self, item, spider):
        author = item["author"]
        if author in self.seen_authors:
            raise scrapy.exceptions.DropItem(f"重复作者: {author}")
        self.seen_authors.add(author)
        return item


class JsonWriterPipeline:
    """JSON 写入管道"""
    
    def open_spider(self, spider):
        """爬虫启动时执行"""
        self.file = open("quotes.jl", "w", encoding="utf-8")
    
    def close_spider(self, spider):
        """爬虫关闭时执行"""
        self.file.close()
    
    def process_item(self, item, spider):
        """处理每条数据 - 写入 JSON Lines"""
        line = json.dumps(dict(item), ensure_ascii=False) + "\n"
        self.file.write(line)
        return item
```

### 4.3 启用 Pipeline

```python
# settings.py
ITEM_PIPELINES = {
    "myspider.pipelines.ValidationPipeline": 100,      # 先验证
    "myspider.pipelines.DuplicateFilterPipeline": 200,  # 再去重
    "myspider.pipelines.JsonWriterPipeline": 300,       # 最后存储
}
```

Pipeline 的执行顺序由数字决定，数字越小越先执行。

---

## 5. Scrapy Shell 调试

Scrapy Shell 是调试选择器的利器：

```bash
# 启动 Shell
scrapy shell "https://quotes.toscrape.com/"

# 在 Shell 中测试选择器
>>> response.css("div.quote").getall()
>>> response.xpath("//span[@class='text']/text()").get()
>>> response.css("span.text::text").get()
```

---

## 6. 常用设置

```python
# settings.py

# === 基本设置 ===
BOT_NAME = "myspider"
ROBOTSTXT_OBEY = True           # 遵守 robots.txt
CONCURRENT_REQUESTS = 16        # 并发请求数
DOWNLOAD_DELAY = 1              # 下载延迟（秒）

# === 下载设置 ===
DOWNLOAD_TIMEOUT = 30           # 超时时间
RETRY_TIMES = 3                 # 重试次数
USER_AGENT = "Mozilla/5.0 ..."  # User-Agent

# === 日志设置 ===
LOG_LEVEL = "INFO"              # 日志级别
LOG_FILE = "spider.log"         # 日志文件

# === 数据处理 ===
FEED_EXPORT_ENCODING = "utf-8"  # 输出编码
```

---

## 7. 反爬策略应对

### 7.1 常见反爬手段

| 反爬手段 | 说明 | 应对方法 |
|----------|------|----------|
| User-Agent 检测 | 检查请求头 | 随机 User-Agent |
| IP 限速/封禁 | 同一 IP 大量请求 | 代理池 + 下载延迟 |
| Cookie/Session | 登录态验证 | 携带 Cookie 或模拟登录 |
| 验证码 | 图形/行为验证码 | 打码平台或跳过 |
| JavaScript 渲染 | 数据在 JS 中动态加载 | Splash 或 Playwright |
| 请求频率检测 | 短时间大量请求 | 限速 + 随机延迟 |

### 7.2 User-Agent 轮换

```python
# settings.py - 下载中间件
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "myspider.middlewares.RandomUserAgentMiddleware": 400,
}

# middlewares.py
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
]

class RandomUserAgentMiddleware:
    def process_request(self, request, spider):
        request.headers["User-Agent"] = random.choice(USER_AGENTS)
```

### 7.3 代理设置

```python
# settings.py
HTTP_PROXY = "http://proxy:8080"

# 或在 Request 中指定
yield scrapy.Request(url, meta={"proxy": "http://proxy:8080"})
```

### 7.4 下载延迟与自动限速

```python
# settings.py
DOWNLOAD_DELAY = 2                    # 固定延迟 2 秒
RANDOMIZE_DOWNLOAD_DELAY = True       # 随机延迟 (0.5 * DELAY ~ 1.5 * DELAY)
AUTOTHROTTLE_ENABLED = True           # 自动限速
AUTOTHROTTLE_START_DELAY = 1          # 起始延迟
AUTOTHROTTLE_MAX_DELAY = 10           # 最大延迟
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0  # 目标并发数
```

---

## 8. 性能对比

### Scrapy vs requests + BeautifulSoup

| 特性 | Scrapy | requests + BS4 |
|------|--------|----------------|
| 并发 | 异步 Twisted，高并发 | 同步，需手动多线程 |
| 去重 | 内置指纹去重 | 需手动实现 |
| 重试 | 内置重试机制 | 需手动实现 |
| 限速 | 内置自动限速 | 需手动实现 |
| Pipeline | 完整的数据管道 | 无，需自行组织 |
| 中间件 | 请求/响应可拦截 | 无 |
| 学习曲线 | 较陡（框架级） | 平缓 |
| 适用场景 | 大规模爬虫 | 简单页面、小规模任务 |

---

## 9. 实战：豆瓣电影 Top250 爬虫

```python
"""
完整实战案例：爬取豆瓣电影 Top250
演示 Scrapy 的完整工作流
"""
import scrapy

class DoubanTop250Spider(scrapy.Spider):
    name = "douban_top250"
    allowed_domains = ["movie.douban.com"]
    start_urls = ["https://movie.douban.com/top250"]
    
    def parse(self, response):
        """解析电影列表页"""
        for movie in response.css("div.item"):
            yield {
                "rank": movie.css("em::text").get(),
                "title": movie.css("span.title::text").get(),
                "rating": movie.css("span.rating_num::text").get(),
                "quote": movie.css("span.inq::text").get(),
                "detail_url": movie.css("div.hd a::attr(href)").get(),
            }
        
        # 翻页：下一页
        next_page = response.css("span.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)
```

运行：`scrapy crawl douban_top250 -o douban_top250.json`

---

## 10. 常用命令速查

```bash
# 项目管理
scrapy startproject <name>           # 创建项目
scrapy genspider <name> <domain>     # 创建爬虫
scrapy list                         # 列出所有爬虫
scrapy settings --get <setting>      # 查看设置

# 运行爬虫
scrapy crawl <spider_name>           # 运行爬虫
scrapy crawl <spider_name> -o out.json  # 输出到文件
scrapy crawl <spider_name> -a tag=life  # 传递参数

# 调试
scrapy shell <url>                   # 交互式调试
scrapy parse --spider <name> <url>   # 测试解析函数
scrapy view <url>                    # 在浏览器中查看页面

# 其他
scrapy check                        # 运行契约检查
scrapy bench                        # 性能基准测试
```

---

## 11. 思考题

1. **为什么 Scrapy 选择 Twisted 而不是 asyncio？** 两者在爬虫场景各有什么优劣？

**参考答案**

主要是**历史原因**：Scrapy 诞生于 2008 年，当时 Python 还没有官方异步方案，Twisted 是生态里最成熟的异步网络框架（事件循环 + Deferred 回调模型，Deferred 可以理解为"将来才会有结果的凭证"），Scrapy 的引擎、下载器、中间件全部建立在它之上。而 asyncio 直到 2014 年（Python 3.4）才进入标准库。等 asyncio 成熟时，Scrapy 已有海量代码和插件依赖 Twisted，整体重写代价太大。

两者在爬虫场景的优劣：

- **Twisted**：久经生产考验、协议支持丰富、性能稳定；缺点是 Deferred 回调写法晦涩、调试困难，且与 asyncio 生态（aiohttp、asyncpg 等）不互通。
- **asyncio**：标准库自带、`async/await` 语法直观、生态庞大；缺点是出现较晚，早期第三方协议库不如 Twisted 齐全。

现状是两者正在融合：Scrapy 2.0 起可选 asyncio reactor（反应器，即底层事件循环），2.7 起新建项目默认使用，**2.13 起所有项目默认 asyncio reactor**——也就是说今天的 Scrapy 已经跑在 asyncio 事件循环上，只是保留了 Twisted 的 API 兼容层。

💡 提示：版本差异较大——老教程里 `TWISTED_REACTOR = None` 对应 2.12 及以前的默认行为；2.13+ 默认值已改为 `"twisted.internet.asyncioreactor.AsyncioSelectorReactor"`。

2. **如果一个网站同时使用了 User-Agent 检测、IP 限速、验证码三种反爬手段，你会如何设计爬虫架构来应对？**

**参考答案**

核心思路是**分层应对、先避后解**：把三种反爬分别交给不同组件处理，并尽量不触发验证码。

- **请求层（下载中间件）**：① UA 轮换中间件，每个请求随机换一个浏览器 User-Agent，应对 UA 检测；② 代理池中间件，轮换出口 IP，失败代理自动标记剔除，应对 IP 限速；③ 开启 `AUTOTHROTTLE_ENABLED` 自动限速 + `DOWNLOAD_DELAY`，把请求频率压到对方容忍线以下——这是**减少验证码出现**的关键。
- **响应层（中间件/errback）**：识别验证码页面、403/429 状态码 → 换一个代理 IP 重试、进一步调低频率；连续失败就暂停该域名一段时间（退避）。
- **验证码本身**：优先"绕开"（降频、走官方 API 等公开接口）；确实绕不开时接入第三方打码平台或人工处理，不要暴力破解。
- **监控层**：统计成功率、被封次数等指标，失败率升高时自动降速或切换代理池，形成闭环。

对应的 settings 骨架（示意）：

```python
# settings.py
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2
AUTOTHROTTLE_ENABLED = True
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "myspider.middlewares.RandomUserAgentMiddleware": 400,
    "myspider.middlewares.ProxyPoolMiddleware": 410,
}
```

⚠️ 注意：应对反爬要守住合规底线——遵守 robots.txt 与网站条款，控制频率不影响对方服务，不绕过登录/付费墙抓取非公开数据。

3. **Pipeline 的执行顺序（数字大小）有什么实际意义？** 能否举一个需要精确控制顺序的场景？

**参考答案**

`ITEM_PIPELINES` 里的数字决定执行先后（越小越先执行），每个管道的输出是下一个管道的输入。它的实际意义有三点：

1. **正确性**：后续步骤依赖前面步骤的加工结果，顺序错了逻辑就错。
2. **性能**：把"丢弃坏数据"的步骤放前面，后面的清洗、存储就不用做无用功。
3. **副作用管理**：写库、发邮件这类不可逆操作放最后，确保只对合格数据执行。

典型场景：电商价格清洗。爬下来的价格是字符串 `"￥1,299.00"`，必须先经清洗管道转成浮点数，验证管道才能判断"价格 > 0"；若验证排在清洗前面，拿到字符串直接报错。另外数字习惯留间隔（100/200/300），方便日后插入新管道而不用改已有编号。

小例子（已验证，用普通函数模拟三个管道）：

```python
def clean(item):
    # 清洗：把价格字符串转成浮点数（兼容半角/全角货币符号）
    price = str(item["price"]).replace("¥", "").replace("￥", "").replace(",", "")
    item["price"] = float(price)
    return item

def validate(item):
    # 验证：价格必须是数字且大于 0
    if not isinstance(item["price"], (int, float)) or item["price"] <= 0:
        raise ValueError(f"价格无效: {item['price']}")
    return item

def store(item, db):
    # 存储：写入"数据库"（这里用列表模拟）
    db.append(item)
    return item

item = {"name": "键盘", "price": "￥1,299.00"}
db = []

# 正确顺序：清洗(100) -> 验证(200) -> 存储(300)
item = clean(item)
item = validate(item)
store(item, db)
print("正确顺序，入库:", db)

# 错误顺序：验证先执行，拿到的还是字符串，直接报错
try:
    validate({"name": "键盘", "price": "￥1,299.00"})
except ValueError as e:
    print("错误顺序，报错:", e)
```

预期输出：

```
正确顺序，入库: [{'name': '键盘', 'price': 1299.0}]
错误顺序，报错: 价格无效: ￥1,299.00
```

顺序颠倒后，验证管道拿到未清洗的字符串直接失败——这就是必须精确控制顺序的原因。

4. **Scrapy 的去重机制是如何实现的？** 如果需要按用户维度去重（而非 URL 维度），该怎么改？

**参考答案**

Scrapy 默认用 `RFPDupeFilter`（请求指纹过滤器）去重：对每个请求计算**指纹**——把请求方法、规范化后的 URL（排序查询参数、去掉 fragment 等）、请求体拼接后做 SHA1 哈希，存进一个内存集合 `seen`。新请求的指纹已在集合里就丢弃（日志记为 filtered），否则放行并记录。单个请求可用 `dont_filter=True` 跳过去重。

按用户维度去重（同一 URL、不同登录用户应视为不同请求），有两种改法：

1. **请求层**：自定义 `DUPEFILTER_CLASS`，重写指纹逻辑，把用户标识（如 Cookie、`meta['user_id']`）拼进哈希输入。这样"同 URL 不同用户"指纹不同，都会被放行。
2. **数据层**：请求全部 `dont_filter=True`，在 Pipeline 里按 `(user_id, url)` 组合去重，重复的 `raise DropItem`。适合"请求可以重发、但数据不能重复入库"的场景。

小例子（已验证，用 hashlib 模拟"把用户拼进指纹"）：

```python
import hashlib

def fingerprint(method, url, body=b"", user=""):
    """模拟请求指纹：方法 + URL + 请求体 + 用户标识 一起做 SHA1"""
    data = method.encode() + url.encode() + body + user.encode()
    return hashlib.sha1(data).hexdigest()

url = "https://example.com/user/profile"
# 同一 URL、不同用户（Cookie 不同）-> 指纹不同，两个请求都保留
fp_a = fingerprint("GET", url, user="cookie:user_A")
fp_b = fingerprint("GET", url, user="cookie:user_B")
print("用户A指纹:", fp_a[:16])
print("用户B指纹:", fp_b[:16])
print("同URL不同用户，指纹不同:", fp_a != fp_b)

# 同一用户重复请求同一 URL -> 指纹相同，第二次被过滤
seen = set()
for i in range(2):
    fp = fingerprint("GET", url, user="cookie:user_A")
    if fp in seen:
        print(f"第{i+1}次请求: 重复，过滤掉")
    else:
        seen.add(fp)
        print(f"第{i+1}次请求: 首次，放行")
```

预期输出（指纹前 16 位）：

```
用户A指纹: 4364093a7b4cb896
用户B指纹: a64e721bbf4b99d2
同URL不同用户，指纹不同: True
第1次请求: 首次，放行
第2次请求: 重复，过滤掉
```

💡 提示：Scrapy 2.7+ 推荐用 `scrapy.utils.request.fingerprint` 生成指纹；自定义过滤器时要把"影响响应内容的因素"（用户、语言、请求体）都纳入，否则会把不同数据误判为重复。

5. **在什么情况下你会选择 requests + BeautifulSoup 而不是 Scrapy？** 请给出具体场景。

**参考答案**

Scrapy 的优势（并发、去重、重试、管道）只有在**规模化、长期运行**的爬虫里才值回票价。以下场景用 requests + BeautifulSoup 更合适：

- **一次性小任务**：只抓几个页面，比如把某公告页的标题和日期存下来。十几行脚本搞定，不值得 `startproject` 建项目、写 Spider/Pipeline。
- **快速验证想法**：先确认"这个页面能不能解析出想要的数据"，用 requests 发一个请求、BS4 试几个选择器，几分钟出结果；验证可行后再考虑要不要上 Scrapy。
- **嵌入现有同步项目**：Web 后端里偶尔抓一个页面，直接同步调用即可；引入 Scrapy 的事件循环反而增加复杂度。
- **环境受限**：目标机器装不上 Scrapy 的依赖（Twisted、lxml 需要编译），requests + BS4 依赖轻得多。
- **需要逐请求精细控制**：复杂登录流程、每步都要人工检查的调试场景，同步代码更直观。

一句话判断：**请求量少、逻辑简单、生命周期短 → requests + BS4；请求量大、需要调度/去重/管道、长期运行 → Scrapy。**

---

## 今日小结

| 概念 | 一句话 |
|------|--------|
| Scrapy 架构 | Engine 调度，Spider 解析，Pipeline 存储 |
| Spider | 定义爬取逻辑的爬虫类 |
| Selector | CSS/XPath 提取数据的工具 |
| Item | 数据模型，规范化数据结构 |
| Pipeline | 数据处理流水线（验证→清洗→存储） |
| 反爬应对 | UA轮换 + 代理池 + 限速 + 中间件 |

> 🎯 **Phase 6 开启！** 接下来几天我们将逐步完善电商价格监控系统，明天学习 Scrapy 的深度功能——Item Loader、中间件、增量爬取。
