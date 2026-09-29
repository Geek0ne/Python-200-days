# -*- coding: utf-8 -*-
"""
02 - RedisCrawlSpider 进阶用法与避坑

演示内容：
1. RedisCrawlSpider：CrawlSpider 的分布式版本（自动跟踪链接规则）
2. 常见三大坑：
   坑1: 优先级队列的 score 是取负的，priority 越大越先出队
   坑2: SCHEDULER_PERSIST=True 导致"改了代码但旧指纹还在"，调试时抓不到数据
   坑3: don't filter=True 的请求会被重复入队，分布式下重复问题被放大
3. 重写 next_requests() 实现种子鉴权/批量预取

运行方式：
    scrapy runspider 02-distributed-crawl.py
"""
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Rule
from scrapy_redis.spiders import RedisCrawlSpider


class BookCrawlSpider(RedisCrawlSpider):
    name = "book_crawl"
    redis_key = "book_crawl:start_urls"

    custom_settings = {
        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "REDIS_URL": "redis://127.0.0.1:6379/0",

        # ---- 坑1: 队列与优先级 ----
        # SpiderQueue 内部是 zset，score = -priority（取负），
        # 所以 priority 越大 score 越小，ZRANGE 从小到大取 => 大优先级先出队 ✅
        "SCHEDULER_QUEUE_CLASS": "scrapy_redis.queue.SpiderQueue",

        # ---- 坑2: 调试期建议 False，生产期改 True ----
        # True  = 重启后指纹和队列保留（断点续爬）
        # False = 爬虫正常关闭时清空队列+指纹（重新全量爬）
        "SCHEDULER_PERSIST": False,

        # ---- 坑3: 分布式下更要控制并发与限速 ----
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "DOWNLOAD_DELAY": 0.3,
        "AUTOTHROTTLE_ENABLED": True,          # 自动限速，节点越多越重要
        "AUTOTHROTTLE_MAX_DELAY": 5,
        "ROBOTSTXT_OBEY": True,
        "RETRY_TIMES": 2,
        "HTTPCACHE_ENABLED": False,            # 分布式下别开本地缓存，会掩盖真实请求
    }

    # CrawlSpider 的链接规则，命中即自动 yield Request（进入 Redis 共享队列）
    rules = (
        # 列表页：跟踪翻页
        Rule(LinkExtractor(allow=r"/catalogue/page-\d+/"), follow=True),
        # 详情页：交给 parse_book，且不再跟踪
        Rule(LinkExtractor(allow=r"/catalogue/.+/\d+/"), callback="parse_book"),
    )

    def parse_book(self, response):
        yield {
            "title": response.css("div.product_main h1::text").get(),
            "price": response.css("p.price_color::text").get(),
            "url": response.url,
        }

    # ---- 进阶：重写 next_requests() 控制种子消费 ----
    def next_requests(self):
        """默认每批取一个种子。重写它可以：
        - 批量预取（减少 Redis 往返）
        - 加种子过滤逻辑（比如丢弃非 http 开头的脏数据）
        """
        for url in super().next_requests():
            if not str(url).startswith(("http://", "https://")):
                self.logger.warning("丢弃非法种子: %r", url)
                continue
            yield url

    # ---- 进阶：spider_idle 信号优雅退出 ----
    def spider_idle(self):
        """队列空时 scrapy-redis 不会自动关闭爬虫（会等待新种子）。
        生产上常在空闲 N 秒后主动 close_spider 释放节点。"""
        self.logger.info("队列空闲，等待新种子... (Ctrl+C 可安全退出)")
