# -*- coding: utf-8 -*-
"""
Day 128 - Scrapy 基础：Spider 与选择器
========================================
本文件演示 Scrapy 爬虫的"最小核心"：
1. 如何定义一个 Spider
2. CSS / XPath 选择器的基本用法
3. 翻页逻辑

运行方式（需要先 pip install scrapy）：
    python 01-scrapy-basics.py

说明：为了让新手不用先学 scrapy startproject 的目录结构，
这里用 CrawlerProcess 直接在单文件里跑通完整流程。
target 站点 books.toscrape.com 是官方练习站，专供爬虫练习。
"""
import scrapy
from scrapy.crawler import CrawlerProcess


# ---------------------------------------------------------------
# 1. 定义数据结构（Item）：提前声明要抓哪些字段
#    为什么不用字典？字段名拼错会在入库前就暴露问题
# ---------------------------------------------------------------
class BookItem(scrapy.Item):
    title = scrapy.Field()   # 书名
    price = scrapy.Field()   # 价格（原始字符串，如 £51.77）


# ---------------------------------------------------------------
# 2. 定义爬虫：继承 scrapy.Spider
# ---------------------------------------------------------------
class BooksSpider(scrapy.Spider):
    name = "books_basic"          # 爬虫唯一标识（必填）
    allowed_domains = ["books.toscrape.com"]  # 安全阀：只爬这个域
    start_urls = ["http://books.toscrape.com/"]  # 入口页

    def parse(self, response):
        """框架下载完 start_urls 后自动调用本方法，传入 response"""
        # 打印一下方便观察
        self.logger.info("正在解析: %s", response.url)

        # CSS 选择器：article.product_pod 是每本书的卡片
        for book in response.css("article.product_pod"):
            yield BookItem(
                # ::attr(title) 取 <a title="..."> 的 title 属性（完整书名）
                title=book.css("h3 a::attr(title)").get(),
                # ::text 取标签内的文本
                price=book.css("p.price_color::text").get(),
            )

        # ---- 翻页：找 "next" 按钮 ----
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            # response.follow 会自动把相对路径补成绝对 URL
            yield response.follow(next_page, callback=self.parse)


# ---------------------------------------------------------------
# 3. XPath 选择器演示（同样重要）
#    XPath 更强大：可以按文本内容找节点、向上找父节点
# ---------------------------------------------------------------
XPATH_DEMO = """
在 scrapy shell 里练习：
    response.xpath("//h1/text()").get()
        -> 取所有 h1 的文本（// 从全文档找）
    response.xpath('//p[@class="price_color"]/text()').get()
        -> 按 class 精确定位
    response.xpath('//a[contains(text(), "next")]/@href').get()
        -> 按"链接文字包含 next"来定位（CSS 做不到！）
"""


# ---------------------------------------------------------------
# 4. 启动爬虫：CrawlerProcess 是单进程内运行爬虫的入口
# ---------------------------------------------------------------
def main():
    process = CrawlerProcess(
        settings={
            "USER_AGENT": "Mozilla/5.0 (LearnPython tutorial)",
            # 只爬前 3 页演示就够了：CLOSESPIDER_PAGECOUNT 达到页数自动停
            "CLOSESPIDER_PAGECOUNT": 3,
            "ROBOTSTXT_OBEY": True,   # 遵守 robots.txt，做个礼貌爬虫
            "DOWNLOAD_DELAY": 0.5,    # 每次请求间隔 0.5 秒，别打爆对方
            "FEEDS": {
                "books_basic.json": {"format": "json", "encoding": "utf-8"},
            },
            "LOG_LEVEL": "INFO",
        }
    )
    process.crawl(BooksSpider)
    process.start()  # 阻塞直到爬虫结束


if __name__ == "__main__":
    print(XPATH_DEMO)
    main()
