# -*- coding: utf-8 -*-
"""
01 - Scrapy-Redis 最小可用分布式爬虫（基础用法）

演示内容：
1. RedisSpider 的写法（不再用 start_urls，改用 redis_key）
2. settings 中必须替换的三个组件
3. 如何向 Redis 注入种子 URL 并启动

运行方式（单机也能跑，装个 redis 即可）：
    pip install scrapy scrapy-redis
    # 启动 redis（docker 最简单）：
    docker run -d -p 6379:6379 redis:7
    # 终端 1：启动爬虫（会阻塞等待种子）
    scrapy runspider 01-basic-redis-spider.py
    # 终端 2：注入种子
    redis-cli lpush demo_spider:start_urls "https://quotes.toscrape.com/page/1/"
"""
import scrapy
from scrapy_redis.spiders import RedisSpider


class QuotesSpider(RedisSpider):
    """最基础的分布式爬虫：继承 RedisSpider 而不是 scrapy.Spider"""

    name = "demo_spider"
    # 不写 start_urls！种子 URL 从 Redis 的这个 key 里取
    redis_key = "demo_spider:start_urls"

    # ---- 可选：自定义 Redis 连接（也可以全放 settings） ----
    custom_settings = {
        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        # 本地 docker 起的 redis
        "REDIS_URL": "redis://127.0.0.1:6379/0",
        # 断点续爬：重启不清空队列和指纹
        "SCHEDULER_PERSIST": True,
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 0.5,   # 每个节点都要限速！分布式节点多，总量容易打爆对方
        "ROBOTSTXT_OBEY": True,
    }

    def parse(self, response):
        """注意：RedisSpider 里没有 start_requests()，parse 直接处理种子页"""
        for quote in response.css("div.quote"):
            yield {
                "text": quote.css("span.text::text").get(),
                "author": quote.css("small.author::text").get(),
                "tags": quote.css("a.tag::text").getall(),
            }

        # 翻页：yield 出去的 Request 会进入 Redis 共享队列，任何节点都可能接手
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)


# ===== 单机自测辅助（不启动 scrapy 时也能验证 redis 连通性） =====
if __name__ == "__main__":
    try:
        import redis

        r = redis.Redis.from_url("redis://127.0.0.1:6379/0")
        r.ping()
        # 注入种子，模拟另一个终端的 lpush
        r.lpush("demo_spider:start_urls", "https://quotes.toscrape.com/page/1/")
        print("✅ Redis 连通，种子已注入：demo_spider:start_urls")
        print("   现在运行: scrapy runspider 01-basic-redis-spider.py")
    except Exception as e:
        print(f"❌ Redis 不可用: {e}")
        print("   先启动: docker run -d -p 6379:6379 redis:7")
