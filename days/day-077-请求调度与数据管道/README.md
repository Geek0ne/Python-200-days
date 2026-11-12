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

**参考答案**

一种常见且合理的设置是：**首页最高（如 priority=100）、分类页居中（50）、详情页最低（0）**。

理由：首页和分类页是"发现型"请求——它们本身不产出商品数据，但能解析出更多分类和商品链接。先爬它们，可以尽快铺开整站的 URL 版图（广度优先），避免一开始就陷进某个分类的详情页里。详情页是"数据型"请求，数量最大，放在后面慢慢消化。

但这不是唯一正确答案，要看目标：

- 如果做的是**价格监控**，只关心少数几个商品，希望尽快拿到数据，那就反过来给详情页高优先级（深度优先），让 Item 尽早产出、尽早触发告警。
- Scrapy 中 priority 越大越先出队；所有请求默认 priority=0，且默认内存队列是 LIFO（后进先出），所以不加干预时爬虫天然偏向深度优先。

小例子（已验证，用标准库 heapq 模拟优先级堆——Scrapy 内部也是"优先级越大越先出队"）：

```python
import heapq

# heapq 是最小堆：入队时存 -priority，堆顶就是"优先级最大"的请求
queue = []
requests = [
    ("首页", 100),
    ("分类页-手机", 50),
    ("详情页-商品A", 0),
    ("分类页-电脑", 50),
    ("详情页-商品B", 0),
]
for name, priority in requests:
    heapq.heappush(queue, (-priority, name))

print("出队顺序（优先级从大到小）:")
while queue:
    neg_priority, name = heapq.heappop(queue)
    print(f"  priority={-neg_priority:>3}  {name}")
```

预期输出：

```
出队顺序（优先级从大到小）:
  priority=100  首页
  priority= 50  分类页-手机
  priority= 50  分类页-电脑
  priority=  0  详情页-商品A
  priority=  0  详情页-商品B
```

💡 提示：真实 Scrapy 在同优先级内按 LIFO 出队（本例用名字做了简化排序）；优先级只是"插队"手段，别给所有请求都设高优先级，那等于没设。

2. **去重策略**：假设你要爬取一个新闻网站，同一个新闻可能出现在首页、分类页、搜索结果中。默认的 URL 去重能正确处理吗？如果不能，你会怎么设计去重逻辑？

**参考答案**

**分两种情况**：

- 如果各处链接指向**完全相同的 URL**，默认 URL 去重完全够用——指纹相同，第二次出现的请求直接被过滤，这正是它的设计目标。
- 但现实中同一篇新闻常常有**不同 URL**：带跟踪参数（`?utm_source=home`、`?spm=...`）、移动端域名（`m.example.com` vs `www.example.com`）、搜索结果页的跳转链接等。这时默认去重会漏掉，同一篇新闻被爬好几遍。

我会设计**两层去重**：

1. **请求层（自定义指纹）**：先做 URL 归一化——去掉跟踪参数、统一域名、排序剩余参数——再算指纹。这样"长得不同但内容相同"的 URL 在入队前就被合并。
2. **数据层（Pipeline 兜底）**：从 URL 或页面里提取新闻 ID（如 `/news/123` 中的 `123`），在 Pipeline 里按 ID 去重，重复的 `raise DropItem`；拿不到 ID 时可用标题+正文的哈希兜底。请求层省带宽，数据层保准确。

小例子（已验证，URL 归一化）：

```python
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def normalize_url(url):
    """归一化新闻 URL：去掉跟踪参数、统一移动端域名"""
    parsed = urlparse(url)
    # 去掉常见的跟踪参数（不影响页面内容）
    tracking = {"utm_source", "utm_medium", "utm_campaign", "spm", "from"}
    params = [(k, v) for k, v in parse_qsl(parsed.query) if k not in tracking]
    # 移动端域名统一成桌面域名
    netloc = parsed.netloc.replace("m.example.com", "www.example.com")
    return urlunparse(parsed._replace(netloc=netloc, query=urlencode(params), fragment=""))

urls = [
    "https://www.example.com/news/123?utm_source=home",
    "https://www.example.com/news/123?utm_source=search&spm=a2c4e",
    "https://m.example.com/news/123?from=timeline",
]
normalized = {normalize_url(u) for u in urls}
print("归一化后:", normalized)
print("3 个不同 URL 实际指向同一篇新闻:", len(normalized) == 1)
```

预期输出：

```
归一化后: {'https://www.example.com/news/123'}
3 个不同 URL 实际指向同一篇新闻: True
```

⚠️ 注意：去跟踪参数前要确认它真的不影响内容——有些站点用参数区分版本（如 `?page=2`），误删会把不同页面当成重复。

3. **管道顺序**：如果你有三个管道——存储到数据库、发送告警邮件、数据统计，它们的执行顺序应该怎么安排？为什么？

**参考答案**

推荐顺序：**数据统计（100）→ 存储到数据库（200）→ 发送告警邮件（300）**。

理由按"副作用从小到大"排列：

- **统计**是纯内存计算，快、无副作用、不会失败，放最前面顺手完成（比如累计条数、价格均值）。
- **存储**是核心目标，应在任何对外通知之前完成——保证"告警响了，数据库里一定有对应数据"。
- **告警邮件**依赖外部 SMTP 服务，慢且容易失败，放最后：即使邮件发送失败，数据也已经安全入库；反过来若邮件在前，一旦它抛异常或 DropItem，数据就丢了。

两个补充原则：

1. 任何管道 `raise DropItem` 后，**后面的管道都不会执行**。所以"必须执行"的逻辑（如资源清理）不要放在可能丢数据的管道之后，而应放在 `close_spider` 里。
2. 如果统计的口径是"只统计成功入库的数据"，那统计应挪到存储之后（存储 100 → 统计 200 → 邮件 300）。顺序没有绝对标准，核心是：**无副作用的先做，不可逆/依赖外部的后做，并想清楚每一步的输入依赖。**

4. **断点续爬**：JOBDIR 机制是如何实现断点续爬的？它保存了哪些状态？有什么局限性？

**参考答案**

设置 `JOBDIR`（或命令行 `--jobdir`）后，Scrapy 会把调度器的关键状态持久化到该目录，重启时自动加载，从而"接着上次爬"。保存的内容主要有三块：

1. **待爬请求队列**：磁盘队列（默认 `PickleLifoDiskQueue`）保存还没发出的请求，重启后重新入队。
2. **去重指纹集合**：`requests.seen` 文件记录已爬请求的指纹，重启后这些 URL 不会被重复爬取。
3. **爬虫状态**：如果 Spider 定义了 `state` 字典属性，`SpiderState` 扩展会用 pickle 把它存成 `spider.state` 文件，重启后恢复（可用来存自定义进度）。

局限性：

- **不保存已下载的数据**：响应和 Item 不在其中，数据落库要自己保证（所以管道写入要幂等）。
- **中断瞬间正在下载的请求会丢**：它们的指纹已记入 `requests.seen`，但请求本身不在队列里，重启后不会被重爬。
- **代码变更可能不兼容**：`spider.state` 是 pickle，类结构改了可能加载失败。
- **不适合周期性监控**：`requests.seen` 会挡住"再次爬同一 URL"，监控场景要么每次用新 JOBDIR，要么 `dont_filter=True`。

💡 提示：JOBDIR 是"同一任务的中断恢复"，不是"增量更新"；想只爬有变化的页面，需要配合时间戳/内容哈希（见 Day 078 思考题）。

5. **性能优化**：当爬虫需要处理 10 万条数据时，Pipeline 中的数据库写入会成为瓶颈吗？你会怎么优化？

**参考答案**

**会**。如果每条 Item 都单独执行一次 INSERT 并提交事务，10 万条就是 10 万次"磁盘落盘/网络往返 + 事务提交"。爬虫下载是并发的，写入却是串行的，数据库很快成为短板，甚至拖慢整个引擎。

优化手段（按收益排序）：

1. **批量写入**：Pipeline 里维护缓冲区，攒够 500~1000 条用 `executemany`（SQL）或 `insert_many`（MongoDB）一次写入；`close_spider` 时把剩余数据 flush 掉，防止丢尾部。
2. **复用连接**：在 `open_spider` 建连接/连接池，`close_spider` 关闭，不要每条数据都新建连接。
3. **异步写入**：把 Item 丢进队列，由独立线程/进程负责写库，爬取不被 IO 阻塞。
4. **减少索引与事务开销**：批量导入时先去掉非必要索引、导完再建；调低提交频率。
5. **用批量导入工具**：MySQL 的 `LOAD DATA`、PostgreSQL 的 `COPY` 比逐条 INSERT 快一个量级。

小例子（已验证，SQLite 对比"逐条提交"和"批量写入"，临时数据库用完自动删除）：

```python
import sqlite3
import tempfile
import time
import os

N = 2000
rows = [(i, f"商品{i}", 9.9 + i % 100) for i in range(N)]

with tempfile.TemporaryDirectory() as tmpdir:  # 临时目录，用完自动删除
    db_path = os.path.join(tmpdir, "items.db")

    # 方式A：每条数据一次 INSERT + 一次 COMMIT
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE items (id INTEGER, name TEXT, price REAL)")
    start = time.perf_counter()
    for row in rows:
        conn.execute("INSERT INTO items VALUES (?, ?, ?)", row)
        conn.commit()          # 每条都提交，每次都要等磁盘落盘
    a_time = time.perf_counter() - start
    conn.close()
    os.remove(db_path)

    # 方式B：executemany 批量插入，最后统一提交一次
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE items (id INTEGER, name TEXT, price REAL)")
    start = time.perf_counter()
    conn.executemany("INSERT INTO items VALUES (?, ?, ?)", rows)
    conn.commit()              # 整批只提交一次
    b_time = time.perf_counter() - start
    conn.close()

print(f"逐条提交: {a_time:.3f}s")
print(f"批量写入: {b_time:.3f}s")
print(f"加速约 {a_time / b_time:.0f} 倍")
```

预期输出（具体耗时因机器/磁盘而异，量级关系稳定）：

```
逐条提交: 2.616s
批量写入: 0.002s
加速约 1083 倍
```

本地 SQLite 尚且如此，换成走网络的 MySQL/MongoDB，逐条写入的往返延迟会让差距更大——这就是"批量 + 复用连接"几乎是爬虫存储标配的原因。

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
