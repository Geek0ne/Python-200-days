# -*- coding: utf-8 -*-
"""
02 - Redis 去重 + MySQL/MongoDB 双写 + 批量缓冲（进阶与避坑）

演示：
1. RedisDedupePipeline：SADD 唯一键做全局去重
2. 双写管道：同一份数据进 MongoDB(原始层) 和 MySQL(结构层)
3. 批量缓冲 + close_spider 兜底 flush
4. 避坑：幂等入库（ON DUPLICATE KEY UPDATE / upsert）

依赖：pip install redis pymongo pymysql
未装数据库也能运行——代码自动降级为"只打印"模式。
"""
from scrapy.exceptions import DropItem


class RedisDedupePipeline:
    """第三层：基于业务主键的分布式去重（比指纹去重更贴近业务）"""

    def __init__(self, redis_url="redis://127.0.0.1:6379/0"):
        self.redis_url = redis_url
        self.key = "books:seen"
        self.r = None

    def open_spider(self, spider):
        try:
            import redis

            self.r = redis.Redis.from_url(self.redis_url, decode_responses=True)
            self.r.ping()
        except Exception:
            self.r = None   # 降级：无 Redis 时跳过去重

    def process_item(self, item, spider):
        if self.r is None:
            return item
        # SADD 原子操作：返回 1 说明第一次见到
        if not self.r.sadd(self.key, item["url"]):
            raise DropItem(f"重复数据: {item['url']}")
        return item


class DualWritePipeline:
    """第四层：批量缓冲 + MySQL/MongoDB 双写（幂等）"""

    BATCH = 50  # 攒 50 条写一次

    def __init__(self):
        self.buffer = []
        self.mysql = None
        self.mongo = None
        self.written = 0

    def open_spider(self, spider):
        # MySQL（可选）
        try:
            import pymysql

            self.mysql = pymysql.connect(
                host="127.0.0.1", user="root", password="root", db="spider"
            )
            with self.mysql.cursor() as c:
                c.execute("""CREATE TABLE IF NOT EXISTS books(
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255),
                    price FLOAT,
                    url VARCHAR(500),
                    UNIQUE KEY uk_url (url))""")
            self.mysql.commit()
        except Exception:
            print("ℹ️ MySQL 不可用，跳过 MySQL 写入")
        # MongoDB（可选）
        try:
            import pymongo

            cli = pymongo.MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=2000)
            cli.server_info()   # 快速失败探测
            col = cli["spider"]["books"]
            col.create_index("url", unique=True)   # ⚠️ 避坑：先建唯一索引再写
            self.mongo = col
        except Exception:
            print("ℹ️ MongoDB 不可用，跳过 Mongo 写入")

    def process_item(self, item, spider):
        self.buffer.append(dict(item))
        if len(self.buffer) >= self.BATCH:
            self._flush()
        return item

    def close_spider(self, spider):
        if self.buffer:
            self._flush()      # ⚠️ 避坑：关闭时必须把残余缓冲刷进库，否则丢尾部数据
        if self.mysql:
            self.mysql.close()

    def _flush(self):
        if self.mysql:
            with self.mysql.cursor() as c:
                # ⚠️ 避坑：幂等写。重跑爬虫不会产生重复行
                c.executemany(
                    """INSERT INTO books (title, price, url)
                       VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE title=VALUES(title), price=VALUES(price)""",
                    [(b["title"], b["price"], b["url"]) for b in self.buffer],
                )
            self.mysql.commit()
        if self.mongo:
            # upsert：存在则整体替换，不存在则插入 -> 天然幂等
            from pymongo import ReplaceOne

            ops = [ReplaceOne({"url": b["url"]}, b, upsert=True) for b in self.buffer]
            self.mongo.bulk_write(ops, ordered=False)  # ordered=False 出错继续，吞吐更高
        else:
            print("（模拟入库）", *[b["url"] for b in self.buffer], sep="\n  ")
        self.written += len(self.buffer)
        self.buffer = []


if __name__ == "__main__":
    class FakeSpider:
        name = "fake"

    dedupe = RedisDedupePipeline()
    dedupe.open_spider(FakeSpider)
    writer = DualWritePipeline()
    writer.open_spider(FakeSpider)

    demo = [{"title": f"书{i}", "price": 10.0 + i, "url": f"https://example.com/{i}"} for i in range(7)]
    demo.append(demo[0])  # 故意塞一条重复的（无 Redis 时不会拦，仅演示流程）

    for it in demo:
        try:
            it = dedupe.process_item(it, FakeSpider)
            writer.process_item(it, FakeSpider)
        except DropItem as e:
            print(f"🗑️ {e}")

    writer.close_spider(FakeSpider)
    print(f"\n🎉 管道结束，共写入 {writer.written} 条（去重后）")
