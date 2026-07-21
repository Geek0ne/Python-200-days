# Day 078 — 爬虫部署、监控与优化

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

2. **分布式调度**：如果要在多台机器上部署爬虫实例，如何实现任务的公平分配和避免重复爬取？（提示：考虑 Celery 或自建调度器）

3. **优雅停机**：爬虫正在运行时收到 SIGTERM 信号，如何确保当前任务完成后再退出？如何处理正在处理中的数据？

4. **增量爬取**：如何设计增量爬取策略，只爬取有变化的页面？比较基于时间戳和基于内容哈希两种方案的优劣。

5. **法律合规**：在编写爬虫时，哪些行为可能触犯法律？如何在技术层面确保爬虫的合规性？（提示：robots.txt、请求频率、数据使用）

---

## 📚 延伸阅读

- [Scrapy 官方文档 - 部署](https://docs.scrapy.org/en/latest/topics/deploy.html)
- [Docker + Scrapy 最佳实践](https://docs.docker.com/compose/networking/)
- [Prometheus Python 客户端](https://github.com/prometheus/client_python)
- [布隆过滤器原理](https://en.wikipedia.org/wiki/Bloom_filter)

---

> 🎉 **恭喜完成 Web 爬虫系统项目！** 你现在已经掌握了从爬虫开发到生产部署的完整流程。接下来的 Day 79-81 将进入数据分析领域，用数据来分析你爬取的结果！
