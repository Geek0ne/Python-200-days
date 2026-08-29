# -*- coding: utf-8 -*-
"""
03 - 实战：多进程模拟分布式集群 + 生产部署要点

不依赖 scrapy 命令行，用 CrawlerProcess 在一个脚本里拉起 3 个"节点"
（多进程），共享同一个 Redis，直观观察：
1. 请求被不同节点竞争消费
2. 指纹去重全局生效（总数 = 去重后数量）
3. 生产部署检查清单

运行方式：
    pip install scrapy scrapy-redis
    docker run -d -p 6379:6379 redis:7
    python3 03-cluster-launcher.py
"""
import multiprocessing as mp

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy_redis.spiders import RedisSpider

REDIS_URL = "redis://127.0.0.1:6379/0"
REDIS_KEY = "cluster_demo:start_urls"
SEEDS = [f"https://quotes.toscrape.com/page/{i}/" for i in range(1, 11)]


class ClusterDemoSpider(RedisSpider):
    name = "cluster_demo"
    redis_key = REDIS_KEY

    custom_settings = {
        "SCHEDULER": "scrapy_redis.scheduler.Scheduler",
        "DUPEFILTER_CLASS": "scrapy_redis.dupefilter.RFPDupeFilter",
        "REDIS_URL": REDIS_URL,
        "SCHEDULER_PERSIST": False,      # 演示完自动清理
        "CONCURRENT_REQUESTS": 4,
        "DOWNLOAD_DELAY": 0.2,
        "ROBOTSTXT_OBEY": True,
        "LOG_LEVEL": "DEBUG",
        # 关键：分布式爬虫默认不因队列空而关闭，这里设小一点让演示能结束
        "SCHEDULER_IDLE_BEFORE_CLOSE": 5,
        "CLOSESPIDER_ITEMCOUNT": 20,     # 每个"节点"抓够 20 条就停
    }

    def parse(self, response):
        # 记录是哪个进程（节点）处理了这个页面
        self.logger.info(
            "🟢 节点 %s 处理了 %s",
            mp.current_process().pid, response.url,
        )
        for q in response.css("div.quote"):
            yield {"author": q.css("small.author::text").get()}
        nxt = response.css("li.next a::attr(href)").get()
        if nxt:
            yield response.follow(nxt, callback=self.parse)


def run_node():
    """一个进程 = 一个爬虫节点"""
    process = CrawlerProcess(settings={"USER_AGENT": "Mozilla/5.0 ClusterDemo"})
    process.crawl(ClusterDemoSpider)
    process.start()


def main():
    # 1. 注入种子（模拟"任务发布方"）
    import redis

    r = redis.Redis.from_url(REDIS_URL)
    r.delete(REDIS_KEY)  # 清掉上次残留，保证可重复运行
    r.lpush(REDIS_KEY, *SEEDS)
    print(f"✅ 已注入 {len(SEEDS)} 个种子到 {REDIS_KEY}")

    # 2. 拉起 3 个"节点"（多进程模拟多台机器）
    nodes = [mp.Process(target=run_node, name=f"node-{i}") for i in range(3)]
    for p in nodes:
        p.start()
    for p in nodes:
        p.join()

    # 3. 观察结果
    print("\n========== 集群运行结果 ==========")
    print("剩余队列长度:", r.zcard("cluster_demo:requests"))
    print("全局指纹数量:", r.scard("cluster_demo:dupefilter"))
    print("""
生产部署检查清单：
  [ ] Redis 开启 requirepass + 内网/VPN 访问（指纹集合=你的爬取历史，泄露即暴露）
  [ ] SCHEDULER_PERSIST=True 用于断点续爬，全量重爬前手动 FLUSH 对应 key
  [ ] 每个节点独立 log 文件 + 统一的 job 名，方便追踪哪个节点抓了什么
  [ ] 部署用 scrapyd / Docker / k8s，而不是裸 nohup
  [ ] 监控 Redis 内存（指纹 set 会一直增长，大站考虑 RedisBloom）
  [ ] Item 各节点自己入库，别全走 RedisPipeline（Redis 会成为瓶颈）
""")


if __name__ == "__main__":
    mp.set_start_method("spawn")  # macOS/Windows 兼容
    main()
