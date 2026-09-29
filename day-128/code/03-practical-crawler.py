# -*- coding: utf-8 -*-
"""
Day 128 - Scrapy 实战：完整的图书爬虫项目（含翻页 + 详情页 + 全套管道）
=======================================================================
运行：python 03-practical-crawler.py
产出：practical_books.jsonlines

这是一个"麻雀虽小五脏俱全"的完整爬虫：
- Item 定义 + ItemLoader 风格清洗
- 列表页翻页（自动翻完全站）
- 详情页二级解析
- 去重 Pipeline（按 URL 去重）
- 统计 Pipeline（结尾打印汇总）
- 自定义异常处理（errback）

站点：books.toscrape.com（官方爬虫练习站，可放心爬）
"""
import json
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import DropItem


class BookItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()
    rating = scrapy.Field()
    stock = scrapy.Field()     # 库存数量
    url = scrapy.Field()


class FullBookSpider(scrapy.Spider):
    """爬取 books.toscrape.com 全站图书（约 1000 本）"""
    name = "full_books"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["http://books.toscrape.com/"]

    def parse(self, response):
        # ---- 列表页：把每本书的详情链接交给 parse_detail ----
        # 列表页的链接形如 ../../../catalogue/xxx_123/index.html
        # 直接用 css 找到相对链接，response.follow 自动补全
        for link in response.css("article.product_pod h3 a::attr(href)").getall():
            yield response.follow(link, callback=self.parse_detail,
                                  errback=self.on_error)  # errback：请求失败时的回调

        # ---- 翻页：直到没有 next 为止 ----
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_detail(self, response):
        """详情页：提取书名 / 价格 / 星级 / 库存"""
        # 库存文本如 "In stock (22 available)"，用正则抠出数字
        import re
        stock_text = response.css("p.instock.availability::text").get("") or ""
        m = re.search(r"\((\d+) available\)", stock_text)
        rating = response.css("p.star-rating::attr(class)").get("") or ""
        yield BookItem(
            title=response.css("h1::text").get(),
            price=response.css("p.price_color::text").get(),
            rating=rating.replace("star-rating", "").strip(),
            stock=int(m.group(1)) if m else 0,
            url=response.url,
        )

    def on_error(self, failure):
        """errback：某个详情页下载失败时走这里，不会让整个爬虫崩掉"""
        self.logger.error("请求失败: %s -> %s", failure.request.url, failure.value)


# ---------------- Pipelines ----------------
class CleanAndValidate:
    def process_item(self, item, spider):
        if not item.get("title"):
            raise DropItem("无标题")
        try:
            item["price"] = float(str(item["price"]).replace("£", "").strip())
        except ValueError:
            raise DropItem(f"价格异常 {item.get('url')}")
        return item


class DedupPipeline:
    """按 URL 去重：防止重复页/重试导致的数据重复"""
    def open_spider(self, spider):
        self.seen = set()  # 全量放内存，数据量极大时可换 Bloom Filter（Day 131 讲）

    def process_item(self, item, spider):
        if item["url"] in self.seen:
            raise DropItem(f"重复: {item['url']}")
        self.seen.add(item["url"])
        return item


class StatsAndSavePipeline:
    def open_spider(self, spider):
        self.fh = open("practical_books.jsonlines", "w", encoding="utf-8")
        self.n = 0

    def process_item(self, item, spider):
        self.fh.write(json.dumps(dict(item), ensure_ascii=False) + "\n")
        self.n += 1
        return item

    def close_spider(self, spider):
        self.fh.close()
        # 汇总：全部爬完后打印平均价格与总数
        print(f"\n===== 汇总：共 {self.n} 本书 =====")


def main():
    process = CrawlerProcess(settings={
        "USER_AGENT": "Mozilla/5.0 (LearnPython-Day128 practical)",
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,  # 温和并发，练习站也别火力全开
        "AUTOTHROTTLE_ENABLED": True,
        "ITEM_PIPELINES": {
            CleanAndValidate: 100,
            DedupPipeline: 200,
            StatsAndSavePipeline: 300,
        },
        "LOG_LEVEL": "INFO",
        # 想爬全站就删掉下面这行；演示默认只取前 60 条
        "CLOSESPIDER_ITEMCOUNT": 60,
    })
    process.crawl(FullBookSpider)
    process.start()


if __name__ == "__main__":
    main()
