# Day 078 — 爬虫部署与监控

> 🎯 **今日目标**：将前两天搭建的 Web 爬虫系统从开发环境推向生产环境，掌握部署、监控、性能优化的完整流程。

---

## 📋 今日知识点总览

| 序号 | 知识点 | 难度 | 重要性 |
|------|--------|------|--------|
| 1 | Scrapyd 部署服务 | ⭐⭐ | 🔥🔥🔥 |
| 2 | Docker 容器化部署 | ⭐⭐ | 🔥🔥🔥 |
| 3 | 日志系统与监控 | ⭐⭐⭐ | 🔥🔥🔥 |
| 4 | 限速与反反爬策略 | ⭐⭐⭐ | 🔥🔥 |
| 5 | 性能优化与调优 | ⭐⭐⭐ | 🔥🔥🔥 |
| 6 | 完整项目集成 | ⭐⭐⭐⭐ | 🔥🔥🔥 |

---

## 1. Scrapyd 部署服务

### 1.1 什么是 Scrapyd？

Scrapyd 是 Scrapy 官方提供的部署和运行爬虫的服务。它允许你：
- 通过 HTTP API 远程部署 Scrapy 项目
- 启动、停止、查看爬虫运行状态
- 管理多个爬虫项目的版本

### 1.2 安装与启动

```bash
# 安装 scrapyd
pip install scrapyd

# 启动服务（默认监听 6800 端口）
scrapyd

# 或指定配置
scrapyd -p 6800 -d /path/to/logs
```

### 1.3 项目打包与部署

```bash
# 安装 scrapyd-deploy
pip install scrapyd-deploy

# 配置 scrapyd-deploy（在 setup.cfg 或 scrapyd-deploy 配置文件中）
# [deploy]
# url = http://localhost:6800/
# project = ecommerce_monitor

# 打包并部署
scrapyd-deploy default -p ecommerce_monitor
```

### 1.4 通过 API 控制爬虫

```python
import requests
import json

SCRAPYD_URL = "http://localhost:6800"

# 启动爬虫
def start_spider(spider_name, **kwargs):
    """启动指定爬虫"""
    data = {
        "project": "ecommerce_monitor",
        "spider": spider_name,
    }
    data.update(kwargs)
    
    response = requests.post(f"{SCRAPYD_URL}/schedule.json", data=data)
    result = response.json()
    print(f"✅ 爬虫已启动，Job ID: {result.get('jobid')}")
    return result

# 查看运行中的爬虫
def list_running_spiders():
    """查看所有运行中的爬虫"""
    response = requests.get(f"{SCRAPYD_URL}/listjobs.json?project=ecommerce_monitor")
    jobs = response.json()
    
    print("📋 运行中的爬虫：")
    for job in jobs.get("running", []):
        print(f"  - {job['spider']} (ID: {job['id']})")
    
    print("\n⏳ 等待中的爬虫：")
    for job in jobs.get("pending", []):
        print(f"  - {job['spider']}")
    
    return jobs

# 删除爬虫任务
def cancel_spider(job_id):
    """取消指定任务"""
    data = {
        "project": "ecommerce_monitor",
        "job": job_id,
    }
    response = requests.post(f"{SCRAPYD_URL}/cancel.json", data=data)
    print(f"🗑️  任务已取消: {response.json()}")

# 使用示例
if __name__ == "__main__":
    # 启动价格监控爬虫
    start_spider("price_monitor", category="electronics")
    
    # 查看状态
    list_running_spiders()
```

---

## 2. Docker 容器化部署

### 2.1 为什么用 Docker？

- **环境一致性**：开发和生产环境完全一致
- **快速部署**：一条命令启动整个系统
- **资源隔离**：爬虫、数据库、监控互相独立
- **弹性扩展**：轻松增减爬虫实例数量

### 2.2 Dockerfile 编写

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（Scrapy 需要）
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口（scrapyd）
EXPOSE 6800

# 启动命令
CMD ["scrapyd"]
```

### 2.3 Docker Compose 编排

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 爬虫服务
  scrapyd:
    build: .
    ports:
      - "6800:6800"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - SCRAPYD_LOG_LEVEL=INFO
    restart: unless-stopped
    networks:
      - crawler-network

  # Redis 缓存（去重队列）
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped
    networks:
      - crawler-network

  # MongoDB（数据存储）
  mongodb:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo-data:/data/db
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password
    restart: unless-stopped
    networks:
      - crawler-network

  # 监控面板
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped
    networks:
      - crawler-network

volumes:
  redis-data:
  mongo-data:
  grafana-data:

networks:
  crawler-network:
    driver: bridge
```

### 2.4 部署命令

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f scrapyd

# 停止所有服务
docker-compose down

# 重启单个服务
docker-compose restart scrapyd
```

---

## 3. 日志系统与监控

### 3.1 结构化日志

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name, log_file="crawler.log"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        self.logger.addHandler(console_handler)
    
    def log_event(self, event_type, data):
        """记录结构化事件"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
        return log_entry
    
    def log_scrape(self, url, status, items_count, duration):
        """记录爬取事件"""
        return self.log_event("scrape", {
            "url": url,
            "status": status,
            "items_count": items_count,
            "duration_seconds": round(duration, 2)
        })
    
    def log_error(self, error, context=None):
        """记录错误事件"""
        return self.log_event("error", {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context or {}
        })
    
    def log_price_change(self, product_id, old_price, new_price, change_pct):
        """记录价格变动"""
        return self.log_event("price_change", {
            "product_id": product_id,
            "old_price": old_price,
            "new_price": new_price,
            "change_percent": round(change_pct, 2)
        })

# 使用示例
logger = StructuredLogger("ecommerce_crawler")

# 记录爬取
logger.log_scrape(
    url="https://example.com/product/123",
    status="success",
    items_count=15,
    duration=3.2
)

# 记录价格变动
logger.log_price_change(
    product_id="SKU-001",
    old_price=99.99,
    new_price=89.99,
    change_pct=-10.0
)
```

### 3.2 监控指标收集

```python
import time
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

@dataclass
class CrawlerMetrics:
    """爬虫运行指标"""
    start_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    items_scraped: int = 0
    items_dropped: int = 0
    response_times: List[float] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
    
    def record_request(self, success: bool, response_time: float):
        """记录请求"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.response_times.append(response_time)
    
    def record_item(self, dropped: bool = False):
        """记录数据项"""
        if dropped:
            self.items_dropped += 1
        else:
            self.items_scraped += 1
    
    def record_error(self, error_type: str, message: str):
        """记录错误"""
        self.errors.append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    @property
    def duration(self) -> float:
        """运行时长（秒）"""
        return time.time() - self.start_time if self.start_time else 0
    
    @property
    def success_rate(self) -> float:
        """请求成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests * 100
    
    @property
    def avg_response_time(self) -> float:
        """平均响应时间"""
        if not self.response_times:
            return 0.0
        return sum(self.response_times) / len(self.response_times)
    
    @property
    def requests_per_second(self) -> float:
        """每秒请求数"""
        if self.duration == 0:
            return 0.0
        return self.total_requests / self.duration
    
    def summary(self) -> Dict:
        """生成摘要报告"""
        return {
            "duration_seconds": round(self.duration, 2),
            "total_requests": self.total_requests,
            "success_rate": f"{self.success_rate:.1f}%",
            "avg_response_time": f"{self.avg_response_time:.2f}s",
            "requests_per_second": round(self.requests_per_second, 2),
            "items_scraped": self.items_scraped,
            "items_dropped": self.items_dropped,
            "errors_count": len(self.errors)
        }

# 使用示例
metrics = CrawlerMetrics()
metrics.start()

# 模拟爬取过程
import random
for i in range(100):
    success = random.random() > 0.1  # 90% 成功率
    response_time = random.uniform(0.5, 3.0)
    metrics.record_request(success, response_time)
    
    if success and random.random() > 0.2:
        metrics.record_item(dropped=False)
    else:
        metrics.record_item(dropped=True)

# 输出报告
print("📊 爬虫运行报告：")
for key, value in metrics.summary().items():
    print(f"  {key}: {value}")
```

### 3.3 Prometheus 指标导出

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# 定义指标
REQUEST_COUNT = Counter(
    'crawler_requests_total',
    'Total crawler requests',
    ['spider', 'status']
)

REQUEST_DURATION = Histogram(
    'crawler_request_duration_seconds',
    'Request duration in seconds',
    ['spider'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

ITEMS_SCRAPED = Counter(
    'crawler_items_scraped_total',
    'Total items scraped',
    ['spider']
)

ACTIVE_SPIDERS = Gauge(
    'crawler_active_spiders',
    'Number of active spiders'
)

def setup_monitoring(port=9100):
    """启动 Prometheus 监控端口"""
    start_http_server(port)
    print(f"📊 监控端口已启动: http://localhost:{port}/metrics")

def record_spider_request(spider_name, status, duration):
    """记录爬虫请求"""
    REQUEST_COUNT.labels(spider=spider_name, status=status).inc()
    REQUEST_DURATION.labels(spider=spider_name).observe(duration)

def record_items(spider_name, count):
    """记录爬取数据量"""
    ITEMS_SCRAPED.labels(spider=spider_name).inc(count)
```

---

## 4. 限速与反反爬策略

### 4.1 Scrapy 自动限速配置

```python
# settings.py

# 自动限速（AutoThrottle）
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1        # 初始延迟（秒）
AUTOTHROTTLE_MAX_DELAY = 10         # 最大延迟（秒）
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0  # 目标并发数
AUTOTHROTTLE_DEBUG = False          # 调试模式

# 下载延迟
DOWNLOAD_DELAY = 2  # 每个请求间隔 2 秒

# 并发控制
CONCURRENT_REQUESTS = 16           # 总并发数
CONCURRENT_REQUESTS_PER_DOMAIN = 8  # 每域名并发数
```

### 4.2 代理 IP 轮换

```python
import random
import requests
from typing import List, Optional

class ProxyManager:
    """代理 IP 管理器"""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.failed_proxies = set()
    
    def add_proxy(self, proxy: str):
        """添加代理"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
    
    def get_proxy(self) -> Optional[str]:
        """获取下一个可用代理"""
        available = [p for p in self.proxies if p not in self.failed_proxies]
        if not available:
            return None
        
        proxy = available[self.current_index % len(available)]
        self.current_index += 1
        return proxy
    
    def mark_failed(self, proxy: str):
        """标记代理失败"""
        self.failed_proxies.add(proxy)
    
    def reset(self):
        """重置失败标记"""
        self.failed_proxies.clear()

class ProxyMiddleware:
    """Scrapy 代理中间件"""
    
    def __init__(self):
        self.proxy_manager = ProxyManager()
    
    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        # 从设置中加载代理列表
        proxy_list = crawler.settings.getlist("PROXY_LIST", [])
        for proxy in proxy_list:
            middleware.proxy_manager.add_proxy(proxy)
        return middleware
    
    def process_request(self, request, spider):
        """为每个请求添加代理"""
        proxy = self.proxy_manager.get_proxy()
        if proxy:
            request.meta["proxy"] = f"http://{proxy}"
            spider.logger.debug(f"使用代理: {proxy}")
```

### 4.3 随机 User-Agent

```python
import random

class RandomUserAgentMiddleware:
    """随机 User-Agent 中间件"""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    ]
    
    def process_request(self, request, spider):
        """随机设置 User-Agent"""
        request.headers["User-Agent"] = random.choice(self.USER_AGENTS)
```

---

## 5. 性能优化与调优

### 5.1 数据库批量写入

```python
import pymongo
from typing import List, Dict
import time

class BatchWriter:
    """批量写入优化器"""
    
    def __init__(self, collection, batch_size=100, flush_interval=5.0):
        self.collection = collection
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: List[Dict] = []
        self.last_flush = time.time()
    
    def add(self, item: Dict):
        """添加数据到缓冲区"""
        self.buffer.append(item)
        
        # 检查是否需要刷新
        if (len(self.buffer) >= self.batch_size or 
            time.time() - self.last_flush >= self.flush_interval):
            self.flush()
    
    def flush(self):
        """刷新缓冲区到数据库"""
        if not self.buffer:
            return
        
        try:
            self.collection.insert_many(self.buffer, ordered=False)
            print(f"✅ 批量写入 {len(self.buffer)} 条数据")
        except pymongo.errors.BulkWriteError as e:
            print(f"⚠️ 部分写入失败: {e.details}")
        
        self.buffer.clear()
        self.last_flush = time.time()
    
    def __del__(self):
        """析构时刷新剩余数据"""
        self.flush()

# 使用示例
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["ecommerce"]
collection = db["products"]

writer = BatchWriter(collection, batch_size=50)
```

### 5.2 请求去重优化（布隆过滤器）

```python
import mmh3
from bitarray import bitarray

class BloomFilter:
    """布隆过滤器 - 高效去重"""
    
    def __init__(self, capacity=1000000, error_rate=0.001):
        """
        初始化布隆过滤器
        
        Args:
            capacity: 预期元素数量
            error_rate: 允许的误判率
        """
        self.capacity = capacity
        self.error_rate = error_rate
        
        # 计算所需位数和哈希函数数量
        self.size = self._optimal_size(capacity, error_rate)
        self.hash_count = self._optimal_hash_count(self.size, capacity)
        
        # 初始化位数组
        self.bit_array = bitarray(self.size)
        self.bit_array.setall(0)
        
        self.count = 0
    
    def _optimal_size(self, n, p):
        """计算最优位数组大小"""
        import math
        m = -(n * math.log(p)) / (math.log(2) ** 2)
        return int(m)
    
    def _optimal_hash_count(self, m, n):
        """计算最优哈希函数数量"""
        import math
        k = (m / n) * math.log(2)
        return int(k)
    
    def add(self, item):
        """添加元素"""
        for i in range(self.hash_count):
            index = mmh3.hash(str(item), i) % self.size
            self.bit_array[index] = 1
        self.count += 1
    
    def contains(self, item) -> bool:
        """检查元素是否可能存在"""
        for i in range(self.hash_count):
            index = mmh3.hash(str(item), i) % self.size
            if not self.bit_array[index]:
                return False
        return True
    
    def __contains__(self, item):
        return self.contains(item)

# 使用示例
bloom = BloomFilter(capacity=1000000)

# 添加 URL
bloom.add("https://example.com/product/1")
bloom.add("https://example.com/product/2")

# 检查 URL 是否已存在
print(bloom.contains("https://example.com/product/1"))  # True
print(bloom.contains("https://example.com/product/999"))  # False
```

### 5.3 异步 IO 优化

```python
import asyncio
import aiohttp
from typing import List
import time

class AsyncFetcher:
    """异步批量请求器"""
    
    def __init__(self, max_concurrent=10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_one(self, session, url):
        """获取单个 URL"""
        async with self.semaphore:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    content = await response.text()
                    return {
                        "url": url,
                        "status": response.status,
                        "length": len(content),
                        "success": True
                    }
            except Exception as e:
                return {
                    "url": url,
                    "status": 0,
                    "length": 0,
                    "success": False,
                    "error": str(e)
                }
    
    async def fetch_batch(self, urls: List[str]) -> List[dict]:
        """批量异步获取"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_one(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            return results

# 使用示例
async def main():
    urls = [
        f"https://example.com/page/{i}" 
        for i in range(100)
    ]
    
    fetcher = AsyncFetcher(max_concurrent=20)
    
    start = time.time()
    results = await fetcher.fetch_batch(urls)
    duration = time.time() - start
    
    success_count = sum(1 for r in results if r["success"])
    print(f"✅ 完成 {success_count}/{len(urls)} 个请求，耗时 {duration:.2f}s")

# 运行
# asyncio.run(main())
```

---

## 6. 完整项目集成

### 6.1 项目结构

```
ecommerce_monitor/
├── scrapy.cfg
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── ecommerce_monitor/
│   ├── __init__.py
│   ├── items.py          # 数据模型
│   ├── pipelines.py      # 数据管道
│   ├── middlewares.py     # 中间件
│   ├── settings.py       # 配置
│   ├── spiders/
│   │   ├── __init__.py
│   │   ├── price_monitor.py
│   │   └── review_monitor.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py      # 日志工具
│       ├── metrics.py     # 指标收集
│       └── bloom.py       # 布隆过滤器
├── deploy/
│   ├── scrapyd-deploy.cfg
│   └── deploy.sh
├── monitor/
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/
└── tests/
    ├── test_spiders.py
    └── test_pipelines.py
```

### 6.2 主爬虫文件

```python
# ecommerce_monitor/spiders/price_monitor.py
import scrapy
from scrapy.exceptions import DropItem
from datetime import datetime
import hashlib

class PriceMonitorSpider(scrapy.Spider):
    """电商价格监控爬虫"""
    
    name = "price_monitor"
    allowed_domains = ["example.com"]
    start_urls = ["https://example.com/products"]
    
    custom_settings = {
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "AUTOTHROTTLE_ENABLED": True,
        "ITEM_PIPELINES": {
            "ecommerce_monitor.pipelines.ValidationPipeline": 100,
            "ecommerce_monitor.pipelines.PriceFilterPipeline": 200,
            "ecommerce_monitor.pipelines.DatabasePipeline": 300,
        },
    }
    
    def __init__(self, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        self.stats = {
            "items_scraped": 0,
            "items_dropped": 0,
            "requests_made": 0,
        }
    
    def parse(self, response):
        """解析商品列表页"""
        self.stats["requests_made"] += 1
        
        # 提取商品链接
        product_links = response.css("a.product-link::attr(href)").getall()
        
        for link in product_links:
            yield response.follow(link, callback=self.parse_product)
        
        # 翻页
        next_page = response.css("a.next-page::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
    
    def parse_product(self, response):
        """解析商品详情页"""
        self.stats["requests_made"] += 1
        
        # 提取数据
        item = {
            "product_id": response.css("div.product-id::text").get("").strip(),
            "name": response.css("h1.product-name::text").get("").strip(),
            "price": float(response.css("span.price::text").get("0").replace("¥", "").replace(",", "")),
            "original_price": float(response.css("span.original-price::text").get("0").replace("¥", "").replace(",", "")),
            "rating": float(response.css("span.rating::attr(data-rating)").get("0")),
            "review_count": int(response.css("span.review-count::text").get("0").replace(",", "")),
            "category": self.category,
            "url": response.url,
            "scraped_at": datetime.now().isoformat(),
            "url_hash": hashlib.md5(response.url.encode()).hexdigest(),
        }
        
        self.stats["items_scraped"] += 1
        yield item
    
    def closed(self, reason):
        """爬虫关闭时输出统计"""
        self.logger.info(f"爬虫统计: {self.stats}")
```

### 6.3 数据管道

```python
# ecommerce_monitor/pipelines.py
import pymongo
from datetime import datetime
from scrapy.exceptions import DropItem

class ValidationPipeline:
    """数据验证管道"""
    
    def process_item(self, item, spider):
        # 检查必填字段
        required_fields = ["product_id", "name", "price"]
        for field in required_fields:
            if not item.get(field):
                raise DropItem(f"缺少必填字段: {field}")
        
        # 价格合理性检查
        if item["price"] <= 0 or item["price"] > 100000:
            raise DropItem(f"价格异常: {item['price']}")
        
        return item

class PriceFilterPipeline:
    """价格过滤管道（只保留降价商品）"""
    
    def __init__(self):
        self.price_history = {}
    
    def process_item(self, item, spider):
        product_id = item["product_id"]
        
        if product_id in self.price_history:
            old_price = self.price_history[product_id]
            if item["price"] >= old_price:
                raise DropItem(f"价格未降低: {old_price} -> {item['price']}")
            spider.logger.info(
                f"💰 降价: {item['name']} {old_price} -> {item['price']}"
            )
        
        self.price_history[product_id] = item["price"]
        return item

class DatabasePipeline:
    """MongoDB 存储管道"""
    
    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None
    
    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI", "mongodb://localhost:27017"),
            mongo_db=crawler.settings.get("MONGO_DB", "ecommerce")
        )
    
    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        spider.logger.info(f"✅ MongoDB 连接成功: {self.mongo_uri}")
    
    def close_spider(self, spider):
        if self.client:
            self.client.close()
    
    def process_item(self, item, spider):
        # 更新或插入
        self.db.products.update_one(
            {"product_id": item["product_id"]},
            {"$set": item},
            upsert=True
        )
        
        # 记录价格历史
        self.db.price_history.insert_one({
            "product_id": item["product_id"],
            "price": item["price"],
            "timestamp": datetime.now()
        })
        
        return item
```

---

## 🖼️ 图解：爬虫系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose 编排                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Scrapyd    │    │    Redis     │    │   MongoDB    │  │
│  │   调度器     │───▶│   去重队列   │───▶│   数据存储   │  │
│  │   端口:6800  │    │   端口:6379  │    │   端口:27017 │  │
│  └──────┬───────┘    └──────────────┘    └──────────────┘  │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────┐    ┌──────────────┐                       │
│  │  爬虫实例 x3 │    │   Grafana    │                       │
│  │  并行运行    │───▶│   监控面板   │                       │
│  │              │    │   端口:3000  │                       │
│  └──────────────┘    └──────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘

数据流向：
  目标网站 ──▶ Scrapyd ──▶ 爬虫实例 ──▶ Pipeline ──▶ MongoDB
                           │
                           ├──▶ Redis（URL去重）
                           └──▶ Prometheus（指标） ──▶ Grafana（可视化）
```

---

## 💡 思考题

1. **缓存策略**：在爬虫中如何设计多级缓存（本地内存 → Redis → 数据库）？各层缓存的失效策略如何设计？

**参考答案**

多级缓存的本质是**用"离计算越近、容量越小、速度越快"的层挡住大部分请求**。典型读路径：先查 L1 本地内存 → 未命中查 L2 Redis → 再未命中查 L3 数据库 → 都没有才去爬目标网站；任何一层命中就返回，并把结果回填到上层。

各层定位与失效策略：

| 层 | 存什么 | 速度/容量 | 失效策略 |
|----|--------|-----------|----------|
| L1 本地内存 | 热点页面/价格 | 纳秒级，几千~几万条 | **短 TTL（秒~分钟）+ LRU 容量淘汰**，进程私有 |
| L2 Redis | 跨实例共享的页面/去重指纹 | 毫秒级，容量大 | **TTL（分钟~小时）+ 更新时主动删除**，多实例共享 |
| L3 数据库 | 全量历史数据 | 较慢，持久 | 不设 TTL，作为"事实来源"，由业务更新 |

设计要点：

- **TTL 按数据变化频率定**：分类结构一天变一次 → 缓存 24 小时；价格分钟级变动 → 缓存 1~5 分钟。
- **写时失效**：数据更新后先写数据库，再删除（而非更新）缓存，下次读时自然重建，避免不一致。
- **防三类经典问题**：缓存穿透（查不存在的数据 → 缓存空值）、缓存击穿（热点 key 过期瞬间大量请求 → 加互斥锁只放一个请求去重建）、缓存雪崩（大批 key 同时过期 → TTL 加随机抖动）。

小例子（已验证，L1 层的 LRU + TTL 实现，用 `now` 参数模拟时间流逝）：

```python
import time
from collections import OrderedDict

class TTLCache:
    """带过期时间的本地缓存（LRU + TTL），模拟多级缓存的 L1 层"""
    def __init__(self, capacity=3, ttl=60):
        self.capacity = capacity   # 最多存几条
        self.ttl = ttl             # 过期时间（秒）
        self.data = OrderedDict()  # key -> (值, 过期时刻)

    def get(self, key, now=None):
        now = time.time() if now is None else now
        if key not in self.data:
            return None
        value, expire_at = self.data[key]
        if now >= expire_at:       # 过期：删除并返回未命中
            del self.data[key]
            return None
        self.data.move_to_end(key) # 命中：挪到末尾（最近使用）
        return value

    def put(self, key, value, now=None):
        now = time.time() if now is None else now
        if key in self.data:
            del self.data[key]
        elif len(self.data) >= self.capacity:
            self.data.popitem(last=False)  # 容量满：淘汰最久未使用的
        self.data[key] = (value, now + self.ttl)

cache = TTLCache(capacity=2, ttl=60)
t0 = 1000.0
cache.put("p1", "价格99", now=t0)
print("TTL 内命中:", cache.get("p1", now=t0 + 30))
print("TTL 过期后未命中:", cache.get("p1", now=t0 + 61))
cache.put("p2", "价格59", now=t0)
cache.put("p3", "价格39", now=t0)
cache.put("p4", "价格19", now=t0)   # 容量只有 2，淘汰最久未用的 p2
print("p2 被 LRU 淘汰:", cache.get("p2", now=t0 + 1))
print("p4 仍在:", cache.get("p4", now=t0 + 1))
```

预期输出：

```
TTL 内命中: 价格99
TTL 过期后未命中: None
p2 被 LRU 淘汰: None
p4 仍在: 价格19
```

💡 提示：L1 是进程私有的，多爬虫实例之间不共享；需要共享的状态（去重指纹、代理池）放 L2 Redis。

2. **分布式调度**：如果要在多台机器上部署爬虫实例，如何实现任务的公平分配和避免重复爬取？（提示：考虑 Celery 或自建调度器）

**参考答案**

分布式爬虫要解决两件事：**任务怎么分**（公平、不闲死也不撑死）和**全局去重**（多台机器不爬同一个 URL）。常见方案：

- **scrapy-redis（共享队列）**：把 Scrapy 调度器的内存队列换成 Redis 队列、去重集合换成 Redis 集合。所有机器从同一个队列抢任务——谁空闲谁取走，天然公平（类似"工作窃取"）；去重指纹全局共享，天然不重复。改造成本最低，是 Scrapy 分布式的事实标准。
- **Celery（中心调度）**：调度器把 URL 拆成任务投进消息队列（RabbitMQ/Redis），各 worker 消费；靠 ack 机制确认完成，worker 挂掉任务可重新投递。适合任务异构、需要复杂编排的场景。
- **自建静态分片**：按 `hash(url) % N` 把 URL 分给 N 台机器。实现最简单，但数据倾斜时不公平，增减机器要重新分片（可用一致性哈希缓解）。

避免重复爬取的关键是**全局指纹 + 原子操作**：用 Redis 的 `SETNX`（不存在才写入）把"检查指纹 + 记录指纹"合成一步原子操作。如果先 `GET` 判断再 `SET`，两台机器可能同时判断"没见过"然后都去爬——竞态条件。超大规模可用分布式布隆过滤器省内存（代价是极小概率误判"见过"）。

其他要考虑的：worker 心跳与失联任务回收、代理池共享与配额、按域名限速（多台机器合力也不能超过对方容忍度）、统一监控各实例进度。

💡 提示：公平分配没有银弹——共享队列简单通用，但要注意"慢任务霸占 worker"问题，可按域名/优先级拆多个队列。

3. **优雅停机**：爬虫正在运行时收到 SIGTERM 信号，如何确保当前任务完成后再退出？如何处理正在处理中的数据？

**参考答案**

核心原则：**信号处理器只设标志位，主循环看到标志后"做完手头的事再退出"**，绝不在信号处理器里直接干重活或立刻 `sys.exit()`。

具体做法：

1. **注册 SIGTERM 处理器**：收到信号只把 `stop_requested = True`。Scrapy 场景下等价于触发 `CloseSpider`/调用引擎关闭——引擎停止调度新请求，但等待在途的下载和解析完成。
2. **主循环检查标志**：每处理完一个任务就看一眼标志，为真则不再取新任务；未开始的任务留在队列里（配合 JOBDIR 持久化），下次启动接着爬。
3. **处理中的数据必须 flush**：批量写入的缓冲区要在退出前落盘（Scrapy 的 `close_spider` 钩子就是干这个的）；数据库连接、文件句柄在 `finally` 里关闭。
4. **写入幂等**：用 upsert（有则更新无则插入）而非盲目 insert，这样中断后重爬不会产生重复数据。
5. **兜底超时**：设一个宽限期（如 30 秒），超时仍未退出就强制结束（Docker 的 `stop_grace_period`、K8s 的 `terminationGracePeriodSeconds` 就是这个机制）。

小例子（已验证，`signal.raise_signal` 模拟操作系统发来 SIGTERM）：

```python
import signal

stop_requested = False

def on_sigterm(signum, frame):
    global stop_requested
    print("收到 SIGTERM：停止调度新任务")
    stop_requested = True

signal.signal(signal.SIGTERM, on_sigterm)

tasks = ["页面A", "页面B", "页面C", "页面D"]
done = []
for i, task in enumerate(tasks):
    if stop_requested:
        print(f"任务 {task} 未开始，留待下次恢复")
        break
    print(f"处理任务: {task}")
    done.append(task)          # 当前任务一定做完
    if i == 1:
        # 模拟此刻操作系统发来 SIGTERM（如 docker stop）
        signal.raise_signal(signal.SIGTERM)

print(f"flush 已完成的 {len(done)} 条数据到磁盘（模拟）")
print("进程优雅退出")
```

预期输出：

```
处理任务: 页面A
处理任务: 页面B
收到 SIGTERM：停止调度新任务
任务 页面C 未开始，留待下次恢复
flush 已完成的 2 条数据到磁盘（模拟）
进程优雅退出
```

可以看到：页面B 做到一半收到信号，仍然做完了；页面C/D 没有开始，数据先 flush 再退出。

⚠️ 注意：Windows 对 SIGTERM 的支持有限（真实进程间发送行为与 Linux 不同），生产部署建议在 Linux/容器里验证信号流程；本例用 `raise_signal` 在进程内触发，跨平台可运行。

4. **增量爬取**：如何设计增量爬取策略，只爬取有变化的页面？比较基于时间戳和基于内容哈希两种方案的优劣。

**参考答案**

两种方案的思路与优劣：

**基于时间戳**：记录每个 URL 上次的爬取时间/页面更新时间，只爬"更新时间晚于上次"的页面。高级玩法是用 HTTP 条件请求——带上 `If-Modified-Since`/`If-None-Match`（ETag），服务器没变化就返回 304，连正文都不用传。

- 优点：省带宽省时间（304 极轻量），实现简单。
- 缺点：依赖服务器"诚实"——很多动态页不返回 Last-Modified，或每次访问都变（页面里嵌了当前时间）；页面标注的发布时间也可能缺失、不准。

**基于内容哈希**：每次照常下载页面，对正文（或提取出的关键字段）算 SHA1/MD5，与库里存的旧指纹比较，不同才处理/入库。

- 优点：判断准确，不依赖服务器元数据；还能过滤"时间戳变了但正文没变"的噪声（广告位、推荐列表）。
- 缺点：省不了下载和解析的开销；哈希对象要选稳定字段，否则误报"有变化"。

**最佳实践是组合**：先用 ETag/304 粗筛（省带宽），命中 200 后再用内容哈希细判（省存储和下游处理）。库里为每个 URL 存 `(etag, last_modified, content_hash)` 三元组。

小例子（已验证，内容哈希判断是否需要更新）：

```python
import hashlib

def content_hash(text):
    """计算内容指纹：只对正文做哈希，排除广告/时间戳等噪声"""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()

# "数据库"里存着上次爬取时各页面的内容指纹
stored = {"https://example.com/news/1": content_hash("正文：产品A发布")}

def need_update(url, new_body):
    new_fp = content_hash(new_body)
    old_fp = stored.get(url)
    if old_fp == new_fp:
        return False          # 内容没变，跳过后续处理/存储
    stored[url] = new_fp      # 变了：更新指纹
    return True

url = "https://example.com/news/1"
print("内容未变，重爬:", need_update(url, "正文：产品A发布"))
print("正文修改后重爬:", need_update(url, "正文：产品A发布（已调价）"))
```

预期输出：

```
内容未变，重爬: False
正文修改后重爬: True
```

💡 提示：增量爬取的请求记得 `dont_filter=True`（或每次用新 JOBDIR），否则 Scrapy 的 URL 去重会把"再次爬同一 URL"直接拦掉。

5. **法律合规**：在编写爬虫时，哪些行为可能触犯法律？如何在技术层面确保爬虫的合规性？（提示：robots.txt、请求频率、数据使用）

**参考答案**

**可能触法的行为**（以中国法律环境为例）：

- **突破技术措施抓取非公开数据**：绕过登录墙、破解验证码/加密接口去拿本不可见的数据，可能涉及"非法获取计算机信息系统数据罪"。
- **把对方服务器爬瘫**：高并发无节制请求造成服务不可用，可能涉及"破坏计算机信息系统罪"，至少承担民事赔偿。
- **批量抓取个人信息**：手机号、身份证、行踪轨迹等，违反《个人信息保护法》，情节严重的涉及刑事犯罪。
- **违反 robots 协议/服务条款大规模搬运内容**：可能构成不正当竞争，或侵犯著作权。

**技术层面的合规措施**：

1. `ROBOTSTXT_OBEY = True`，遵守 robots.txt 的Disallow 规则。
2. 限速：`DOWNLOAD_DELAY` + `AUTOTHROTTLE_ENABLED`，把请求频率控制在对方可承受范围；收到 403/429 立即退避或停止。
3. 只抓**公开可访问**的数据，不绕过登录、付费墙、验证码。
4. User-Agent 表明身份（可附联系方式），不伪装成搜索引擎误导对方。
5. 个人信息最小化：能不抓就不抓，必须抓的做脱敏/匿名化，不转售。
6. 数据使用守边界：不整体搬运原文做竞品，遵守目标网站服务条款与版权。

⚠️ 注意：robots.txt 本身不是法律，而是行业规范——违反它不必然违法，但会成为纠纷中的不利证据；具体业务是否合规应咨询法务。技术上"能做"不等于法律上"可做"。

---

## 📚 延伸阅读

- [Scrapy 官方文档 - 部署](https://docs.scrapy.org/en/latest/topics/deploy.html)
- [Docker + Scrapy 最佳实践](https://docs.docker.com/compose/networking/)
- [Prometheus Python 客户端](https://github.com/prometheus/client_python)
- [布隆过滤器原理](https://en.wikipedia.org/wiki/Bloom_filter)

---

> 🎉 **恭喜完成 Web 爬虫系统项目！** 你现在已经掌握了从爬虫开发到生产部署的完整流程。接下来的 Day 79-81 将进入数据分析领域，用数据来分析你爬取的结果！
