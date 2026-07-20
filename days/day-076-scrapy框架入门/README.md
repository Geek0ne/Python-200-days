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
2. **如果一个网站同时使用了 User-Agent 检测、IP 限速、验证码三种反爬手段，你会如何设计爬虫架构来应对？**
3. **Pipeline 的执行顺序（数字大小）有什么实际意义？** 能否举一个需要精确控制顺序的场景？
4. **Scrapy 的去重机制是如何实现的？** 如果需要按用户维度去重（而非 URL 维度），该怎么改？
5. **在什么情况下你会选择 requests + BeautifulSoup 而不是 Scrapy？** 请给出具体场景。

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
