# Day 077 — 请求调度与数据管道

## 概述

Day 076 我们学会了 Scrapy 的基本架构和第一个爬虫的编写。今天深入**核心机制**——请求调度（Scheduler）、去重（Duplicate Filter）和数据管道（Pipeline）。这些是 Scrapy 从"能跑"到"能用"的关键。

**今天你将学到：**
1. Scrapy 调度器的工作原理与调度策略
2. 去重机制：基于什么去重？如何自定义？
3. 数据管道（Pipeline）的完整生命周期
4. 多管道协作：清洗 → 验证 → 存储
5. 电商价格监控系统的数据管道实战

---

## 1. 请求调度器（Scheduler）

### 1.1 什么是调度器？

调度器是 Scrapy 引擎中的"交通指挥官"。它决定：
- **哪个请求先发出去**（优先级）
- **哪些请求该跳过**（去重）
- **请求失败后怎么办**（重试策略）

```
┌──────────────────────────────────────────────────────────┐
│                    Scrapy 引擎                            │
│                                                          │
│   Spider 发出请求 ──→ 调度器（入队） ──→ 下载器（执行）    │
│         ↑                                    │            │
│         └──── 响应回来 ←── 中间件 ←──────────┘            │
│                                                          │
│   调度器内部：                                            │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐    │
│   │  请求队列   │ ←→ │  去重过滤器 │ ←→ │  优先级堆   │    │
│   │ (pending)  │    │ (dupefilter)│   │  (heap)    │    │
│   └────────────┘    └────────────┘    └────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### 1.2 调度器的两种实现

Scrapy 默认使用两种调度器后端：

| 后端 | 存储位置 | 特点 | 适用场景 |
|------|---------|------|---------|
| `MemoryQueue` | 内存 | 速度快，重启丢失 | 小规模爬虫 |
| `DiskQueue` | 磁盘文件 | 持久化，可恢复 | 大规模/长时间爬虫 |

在 `settings.py` 中配置：

```python
# 默认使用内存队列
SCHEDULER = 'scrapy.core.scheduler.Scheduler'

# 如需磁盘持久化（断点续爬）
# SCHEDULER = 'scrapy.core.scheduler.Scheduler'
# QUEUE_CLASS = 'scrapy.utils.job.FilePath'  # 或自定义
```

### 1.3 调度优先级

每个 Request 都可以设置 `priority`（整数，越大越优先）：

```python
# 高优先级：首页
yield scrapy.Request(url, callback=self.parse, priority=10)

# 低优先级：详情页
yield scrapy.Request(url, callback=self.parse_detail, priority=0)
```

**原理**：调度器内部使用**优先级堆（heapq）**管理请求队列，priority 越大的请求越先被取出发送。

---

## 2. 去重机制（Duplicate Filter）

### 2.1 为什么需要去重？

爬虫最常见的问题之一就是**重复爬取同一个 URL**。原因包括：
- 多个页面都链接到同一个 URL
- 响应中解析出重复的链接
- 重试机制导致重复请求

去重能避免浪费带宽和时间，同时降低被目标网站封禁的风险。

### 2.2 默认去重原理

Scrapy 默认使用 `RFPDupeFilter`（Request Fingerprint Filter）：

```python
# 默认去重基于请求指纹（Fingerprint）
# 指纹 = hash(request.url + request.method + request.body)
```

**指纹生成流程**：

```
Request 对象
    │
    ├─ url: "https://example.com/page/1"
    ├─ method: "GET"
    ├─ body: b""  (GET 请求通常为空)
    │
    ▼
fingerprint = hashlib.sha1(
    url + method + body
).hexdigest()
    │
    ▼
检查 fingerprint 是否在已见集合中
    ├─ 不在 → 允许通过，记录指纹
    └─ 在 → 过滤掉，跳过请求
```

### 2.3 自定义去重

有时默认的 URL 去重不够用。比如：
- 同一个 URL，不同的 Cookie/Referer 应该算不同请求
- 需要基于参数值去重（忽略参数顺序）

自定义去重过滤器：

```python
# myproject/dupefilters.py
import hashlib
from scrapy.dupefilters import RFPDupeFilter

class CustomDupeFilter(RFPDupeFilter):
    """自定义去重：忽略某些查询参数"""

    IGNORE_PARAMS = {'timestamp', 'nonce', 'session_id'}

    def request_fingerprint(self, request):
        """重写指纹生成逻辑"""
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        parsed = urlparse(request.url)
        params = parse_qs(parsed.query, keep_blank_values=True)

        # 移除忽略的参数
        for key in self.IGNORE_PARAMS:
            params.pop(key, None)

        # 重新排序参数
        sorted_query = urlencode(sorted(params.items()), doseq=True)

        # 重建 URL
        new_url = urlunparse(parsed._replace(query=sorted_query))

        # 生成指纹
        fp = hashlib.sha1()
        fp.update(request.method.encode())
        fp.update(new_url.encode())
        fp.update(request.body or b'')

        return fp.hexdigest()
```

在 `settings.py` 中启用：

```python
DUPEFILTER_CLASS = 'myproject.dupefilters.CustomDupeFilter'
```

### 2.4 关闭去重

某些场景（如监控数据变化）需要重复爬取：

```python
# 方式 1：单个请求关闭去重
yield scrapy.Request(url, callback=self.parse, dont_filter=True)

# 方式 2：全局关闭（不推荐）
# DUPEFILTER_CLASS = 'scrapy.dupefilters.BaseDupeFilter'
```

---

## 3. 数据管道（Pipeline）

### 3.1 管道是什么？

Pipeline 是 Scrapy 中处理爬取数据的**流水线**。每个 Item 会依次经过所有启用的 Pipeline，就像工厂的流水线：

```
Spider 产出 Item
    │
    ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  清洗管道     │ → │  验证管道    │ → │  存储管道    │
│ (Clean)     │   │ (Validate)  │   │ (Store)     │
└─────────────┘   └─────────────┘   └─────────────┘
    │                  │                  │
    ▼                  ▼                  ▼
  去除空字段         检查必填字段       写入数据库
  格式化数据         类型校验           保存到文件
```

### 3.2 管道类的基本结构

```python
class MyPipeline:
    """每个 Pipeline 都是实现了特定方法的类"""

    def open_spider(self, spider):
        """爬虫启动时调用一次。适合做初始化：打开文件、连接数据库等"""
        self.file = open('output.json', 'w')

    def close_spider(self, spider):
        """爬虫关闭时调用一次。适合做清理：关闭文件、断开连接等"""
        self.file.close()

    def process_item(self, item, spider):
        """
        每个 Item 都会经过这里。
        必须返回 Item（或 DropItem 丢弃它）。
        """
        # 处理 item...
        return item
```

### 3.3 启用与排序 Pipeline

在 `settings.py` 中：

```python
ITEM_PIPELINES = {
    'myproject.pipelines.CleanPipeline': 100,      # 先清洗
    'myproject.pipelines.ValidatePipeline': 200,    # 再验证
    'myproject.pipelines.StorePipeline': 300,       # 最后存储
}
```

**数字越小，越先执行。** 这就是流水线的执行顺序。

### 3.4 DropItem：丢弃不合格数据

```python
from scrapy.exceptions import DropItem

class ValidatePipeline:
    def process_item(self, item, spider):
        if not item.get('price'):
            raise DropItem(f"缺少价格字段，丢弃: {item}")
        if not isinstance(item['price'], (int, float)):
            raise DropItem(f"价格类型错误: {item['price']}")
        return item
```

### 3.5 管道间的通信

有时后续管道需要前序管道的信息：

```python
class EnrichPipeline:
    def process_item(self, item, spider):
        # 添加处理时间戳
        from datetime import datetime
        item['crawled_at'] = datetime.now().isoformat()
        # 添加处理阶段标记
        item['_pipeline_stage'] = 'enriched'
        return item
```

---

## 4. 实战：电商价格监控系统的数据管道

### 4.1 项目结构

```
ecommerce_monitor/
├── scrapy.cfg
├── ecommerce_monitor/
│   ├── __init__.py
│   ├── items.py          # 定义数据结构
│   ├── pipelines.py      # 数据管道
│   ├── dupefilters.py    # 自定义去重
│   ├── middlewares.py
│   ├── settings.py
│   └── spiders/
│       └── price_spider.py
└── data/                 # 数据输出目录
```

### 4.2 Item 定义

```python
# items.py
import scrapy

class ProductItem(scrapy.Item):
    """电商商品数据结构"""
    name = scrapy.Field()           # 商品名称
    price = scrapy.Field()          # 当前价格
    original_price = scrapy.Field() # 原价
    url = scrapy.Field()            # 商品链接
    shop = scrapy.Field()           # 店铺名称
    category = scrapy.Field()       # 商品分类
    rating = scrapy.Field()         # 评分
    reviews = scrapy.Field()        # 评价数
    crawled_at = scrapy.Field()     # 爬取时间
```

### 4.3 完整 Pipeline 实现

```python
# pipelines.py
import json
import logging
from datetime import datetime
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)


class CleanPipeline:
    """
    第一步：数据清洗
    - 去除空白字符
    - 标准化价格格式
    - 过滤无效数据
    """

    def process_item(self, item, spider):
        # 清洗商品名称
        if item.get('name'):
            item['name'] = item['name'].strip()
            # 移除多余空格
            item['name'] = ' '.join(item['name'].split())

        # 标准化价格
        if item.get('price'):
            try:
                # 去除货币符号和逗号
                price_str = str(item['price'])
                price_str = price_str.replace('¥', '').replace('$', '')
                price_str = price_str.replace(',', '').replace(' ', '')
                item['price'] = float(price_str)
            except (ValueError, TypeError):
                raise DropItem(f"价格格式无效: {item.get('price')}")

        # 添加爬取时间
        item['crawled_at'] = datetime.now().isoformat()

        return item


class ValidatePipeline:
    """
    第二步：数据验证
    - 检查必填字段
    - 类型校验
    - 业务规则校验
    """

    def process_item(self, item, spider):
        # 必填字段检查
        required_fields = ['name', 'price', 'url']
        for field in required_fields:
            if not item.get(field):
                raise DropItem(f"缺少必填字段 '{field}': {item}")

        # 价格合理性检查
        if item['price'] <= 0:
            raise DropItem(f"价格必须大于 0: {item['price']}")
        if item['price'] > 1000000:
            raise DropItem(f"价格异常偏高，可能解析错误: {item['price']}")

        # URL 格式检查
        if not item['url'].startswith('http'):
            raise DropItem(f"URL 格式无效: {item['url']}")

        return item


class AlertPipeline:
    """
    第三步：价格预警
    - 与历史价格对比
    - 触发降价提醒
    """

    def __init__(self):
        self.price_history = {}  # {url: [price1, price2, ...]}

    def process_item(self, item, spider):
        url = item['url']
        current_price = item['price']

        if url in self.price_history:
            last_price = self.price_history[url][-1]
            if current_price < last_price:
                discount = (last_price - current_price) / last_price * 100
                item['alert'] = f"降价 {discount:.1f}%！"
                logger.info(f"🔔 降价提醒: {item['name']} "
                           f"¥{last_price} → ¥{current_price}")
            elif current_price > last_price:
                item['alert'] = f"涨价！"
                logger.info(f"📈 涨价: {item['name']} "
                           f"¥{last_price} → ¥{current_price}")
            else:
                item['alert'] = "价格不变"
        else:
            item['alert'] = "首次记录"

        # 更新历史
        if url not in self.price_history:
            self.price_history[url] = []
        self.price_history[url].append(current_price)

        return item


class JsonExportPipeline:
    """
    第四步：导出为 JSON 文件
    每个商品一行（JSON Lines 格式），方便追加写入
    """

    def open_spider(self, spider):
        today = datetime.now().strftime('%Y%m%d')
        self.filename = f'data/prices_{today}.jsonl'
        self.file = open(self.filename, 'a', encoding='utf-8')
        self.count = 0

    def close_spider(self, spider):
        self.file.close()
        logger.info(f"共导出 {self.count} 条商品数据到 {self.filename}")

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + '\n')
        self.file.flush()
        self.count += 1
        return item
```

---

## 5. 调度器与去重的高级技巧

### 5.1 断点续爬

利用 `JOBDIR` 参数，Scrapy 可以持久化调度器状态：

```bash
# 首次运行，保存状态
scrapy crawl price_monitor -o prices.json --jobdir=crawl_jobs/001

# 中断后恢复
scrapy crawl price_monitor -o prices.json --jobdir=crawl_jobs/001
```

**原理**：JOBDIR 会保存调度器的请求队列和去重集合到磁盘，下次运行时自动恢复。

### 5.2 深度限制

防止爬虫陷入无限深度：

```python
# settings.py
DEPTH_LIMIT = 10          # 最大爬取深度
CLOSESPIDER_PAGECOUNT = 1000  # 最大页面数
CLOSESPIDER_TIMEOUT = 3600    # 最大运行时间（秒）
```

### 5.3 域名限制

```python
# settings.py
# 限制只爬取特定域名
CLOSESPIDER_ITEMCOUNT = 500  # 最大 Item 数

# 或在 Spider 中控制
class MySpider(scrapy.Spider):
    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=False,  # 启用去重（默认）
                errback=self.errback,  # 错误处理
                meta={'depth': 0},  # 初始深度
            )
```

---

## 6. 常见问题与避坑

### 6.1 Pipeline 执行顺序问题

**错误现象**：存储管道先执行了，数据还是脏的。

**原因**：`ITEM_PIPELINES` 中数字设反了。

**解决**：确保清洗（100） < 验证（200） < 存储（300）。

### 6.2 忘记 return item

**错误现象**：后续管道收不到数据，整个链路断裂。

**解决**：`process_item` 必须 `return item`（或 `raise DropItem`）。

### 6.3 去重过于激进

**错误现象**：明明是不同的数据，但因为 URL 相同被过滤了。

**场景**：分页参数在 fragment（# 后面）中，Scrapy 默认不处理 fragment。

**解决**：自定义去重过滤器，或者用 `dont_filter=True`。

### 6.4 内存泄漏

**错误现象**：爬虫运行时间越长，内存占用越高。

**原因**：在 Pipeline 或 Spider 中用列表/字典缓存数据，没有清理。

**解决**：
- Pipeline 中避免无限增长的缓存
- 用 `open_spider/close_spider` 做资源生命周期管理
- 大数据量考虑用数据库而非内存

---

## 7. 思考题

1. **调度器优先级**：如果你在爬取一个电商网站，首页、分类页、商品详情页应该分别设置什么优先级？为什么？

2. **去重策略**：假设你要爬取一个新闻网站，同一个新闻可能出现在首页、分类页、搜索结果中。默认的 URL 去重能正确处理吗？如果不能，你会怎么设计去重逻辑？

3. **管道顺序**：如果你有三个管道——存储到数据库、发送告警邮件、数据统计，它们的执行顺序应该怎么安排？为什么？

4. **断点续爬**：JOBDIR 机制是如何实现断点续爬的？它保存了哪些状态？有什么局限性？

5. **性能优化**：当爬虫需要处理 10 万条数据时，Pipeline 中的数据库写入会成为瓶颈吗？你会怎么优化？

---

## 总结

今天深入学习了 Scrapy 的核心机制：

| 概念 | 核心要点 |
|------|---------|
| **调度器** | 管理请求队列，支持内存/磁盘两种后端，基于优先级堆调度 |
| **去重** | 基于请求指纹（URL+Method+Body）去重，支持自定义指纹逻辑 |
| **Pipeline** | 数据处理流水线，按数字顺序依次执行，必须 return item |
| **DropItem** | 丢弃不合格数据的机制 |
| **断点续爬** | JOBDIR 持久化调度器状态，支持中断恢复 |

> 🎯 **明天预告**：Day 078 将学习反爬策略的应对——UA 轮换、IP 代理池、验证码处理、Cookie 管理，让我们的爬虫更健壮。
