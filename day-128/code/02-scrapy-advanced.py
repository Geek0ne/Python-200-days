# -*- coding: utf-8 -*-
"""
Day 128 - Scrapy 进阶与避坑：Pipeline / Middleware / 常见坑
=============================================================
运行：python 02-scrapy-advanced.py

覆盖：
1. 多级页面解析（列表页 -> 详情页，callback 串联）
2. Pipeline 数据清洗 / 校验 / 落盘（含 open/close_spider 钩子）
3. 自定义 Downloader Middleware（随机 UA + 重试日志）
4. 新手必踩的坑逐条注释
"""
import json
import random
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import DropItem


# ================= Item =================
class BookItem(scrapy.Item):
    title = scrapy.Field()
    price = scrapy.Field()      # 清洗后 float
    rating = scrapy.Field()     # 星级（单词）
    description = scrapy.Field()
    url = scrapy.Field()


# ================= Spider：列表页 -> 详情页 =================
class BookDetailSpider(scrapy.Spider):
    name = "books_detail"
    allowed_domains = ["books.toscrape.com"]
    start_urls = ["http://books.toscrape.com/catalogue/category/books/travel_2/index.html"]

    def parse(self, response):
        """列表页：只负责发现详情页链接"""
        for link in response.css("h3 a::attr(href)").getall()[:5]:  # 演示只取 5 本
            # ⚠️ 坑 1：列表页链接是相对路径且带 catalogue 前缀层级，
            # response.follow 会自动 urljoin，别手写拼接！
            yield response.follow(link, callback=self.parse_detail)

    def parse_detail(self, response):
        """详情页：提取完整字段"""
        # 星级在 <p class="star-rating Three"> 的 class 里
        rating = response.css("p.star-rating::attr(class)").get("")  # get("") 给默认值防 None
        yield BookItem(
            title=response.css("h1::text").get(),
            price=response.css("p.price_color::text").get(),
            rating=rating.replace("star-rating", "").strip() if rating else "",
            description=response.xpath('//div[@id="product_description"]/following-sibling::p/text()').get(),
            url=response.url,
        )


# ================= Pipelines：注意执行顺序（数字越小越先） =================
class CleaningPipeline:
    """清洗：'£51.77' -> 51.77"""
    def process_item(self, item, spider):
        # ⚠️ 坑 2：价格字符串里有货币符号和可能的空格，直接 float() 会崩
        raw = item.get("price", "")
        try:
            item["price"] = float(raw.replace("£", "").replace("Â", "").strip())
        except (TypeError, ValueError):
            # ⚠️ 坑 3：坏数据不要静默跳过，要么修复要么 DropItem，方便排查
            raise DropItem(f"价格无法解析: {raw!r} ({item.get('url')})")
        return item  # ⚠️ 坑 4：忘记 return item 会导致数据在管道里"消失"！


class ValidationPipeline:
    """校验：必填字段缺失就丢弃"""
    def process_item(self, item, spider):
        if not item.get("title"):
            raise DropItem(f"缺标题: {item.get('url')}")
        return item


class JsonWriterPipeline:
    """落盘：open/close_spider 钩子只执行一次"""
    def open_spider(self, spider):
        # ⚠️ 坑 5：encoding 必须指定 utf-8，否则 Windows 默认 gbk 写中文会崩
        self.file = open("books_detail.json", "w", encoding="utf-8")
        self.count = 0

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info("共写入 %d 条数据", self.count)

    def process_item(self, item, spider):
        self.file.write(json.dumps(dict(item), ensure_ascii=False) + "\n")
        self.count += 1
        return item


# ================= Middleware：随机 UA =================
class RandomUaMiddleware:
    """每个请求随机换一个 UA，降低被识别为爬虫的概率"""
    UA_LIST = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0 Safari/537.36",
    ]

    def process_request(self, request, spider):
        # 返回 None = 继续正常下载流程
        request.headers["User-Agent"] = random.choice(self.UA_LIST)


# ================= 启动 =================
def main():
    process = CrawlerProcess(
        settings={
            "ROBOTSTXT_OBEY": True,
            "DOWNLOAD_DELAY": 0.3,
            "DOWNLOAD_TIMEOUT": 15,
            "RETRY_TIMES": 2,            # 失败自动重试 2 次
            # Pipeline 顺序：先校验(100) -> 再清洗(200) -> 最后落盘(300)
            # ⚠️ 坑 6：顺序反了会导致"清洗阶段就崩"或"脏数据已入库"
            "ITEM_PIPELINES": {
                ValidationPipeline: 100,
                CleaningPipeline: 200,
                JsonWriterPipeline: 300,
            },
            "DOWNLOADER_MIDDLEWARES": {
                RandomUaMiddleware: 400,
            },
            "LOG_LEVEL": "INFO",
            "CLOSESPIDER_ITEMCOUNT": 5,  # 拿到 5 条就停（演示用）
        }
    )
    process.crawl(BookDetailSpider)
    process.start()


if __name__ == "__main__":
    main()
