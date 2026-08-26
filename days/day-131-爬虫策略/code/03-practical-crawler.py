# -*- coding: utf-8 -*-
"""
Day 131 - 爬虫策略实战：稳定大规模爬虫
=======================================
把 去重(Bloom) + 限速(令牌桶) + 断点续爬 + 退避重试 组装成一个健壮爬虫。

运行：python 03-practical-crawler.py
  - 全程爬取 books.toscrape.com（官方练习站）
  - 中途 Ctrl+C 强杀，再重新运行 -> 自动从断点继续（可自行验证！）
产出：stable_books.jsonl + checkpoint.json

依赖：requests（Day 126 学过）
"""
import json
import os
import time
import requests
from collections import deque
from urllib.parse import urljoin, urlsplit

class SimpleBloomFilter:
    def __init__(self, expected_items=100_000, fp_rate=0.01):
        import math
        n, p = expected_items, fp_rate
        self.m = max(int(-n * math.log(p) / (math.log(2) ** 2)), 1024)
        self.k = max(int((self.m / n) * math.log(2)), 1)
        self.bits = bytearray((self.m + 7) // 8)

    def _positions(self, item):
        h1 = hash(item) & 0x7FFFFFFF
        h2 = (hash(item + "#seed") & 0x7FFFFFFF) or 1
        for i in range(self.k):
            yield (h1 + i * h2) % self.m

    def add(self, item):
        for pos in self._positions(item):
            self.bits[pos // 8] |= (1 << (pos % 8))

    def __contains__(self, item):
        return all(self.bits[pos // 8] & (1 << (pos % 8))
                   for pos in self._positions(item))


class TokenBucket:
    def __init__(self, rate=1.0, capacity=3):
        self.rate, self.capacity = rate, capacity
        self.tokens, self.last = float(capacity), time.monotonic()

    def acquire(self):
        while True:
            now = time.monotonic()
            self.tokens = min(self.capacity,
                              self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            time.sleep((1 - self.tokens) / self.rate)


class StableCrawler:
    """生产级爬虫骨架：Bloom 去重 + 令牌桶 + checkpoint + 指数退避"""
    BASE = "http://books.toscrape.com/"
    CKPT = "checkpoint.json"
    OUT = "stable_books.jsonl"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (LearnPython-Day131 StableCrawler)"
        self.bloom = SimpleBloomFilter()
        self.bucket = TokenBucket(rate=2.0, capacity=3)  # 平均 2 req/s，礼貌限速
        self.queue = deque()
        self.visited_count = 0
        self.item_count = 0
        self.fail_urls = []

    # ---------- 断点续爬 ----------
    def save_ckpt(self):
        tmp = self.CKPT + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"queue": list(self.queue)[:500],   # 只存前 500 条防文件过大
                       "visited_count": self.visited_count,
                       "item_count": self.item_count}, f, ensure_ascii=False)
        os.replace(tmp, self.CKPT)   # 原子写

    def try_resume(self):
        if not os.path.exists(self.CKPT):
            return
        with open(self.CKPT, encoding="utf-8") as f:
            d = json.load(f)
        self.queue = deque(d["queue"])
        self.visited_count = d["visited_count"]
        self.item_count = d["item_count"]
        print(f"[续爬] 恢复: 待爬 {len(self.queue)}，已访问 {self.visited_count}，"
              f"已有数据 {self.item_count} 条")

    # ---------- 下载（指数退避） ----------
    def fetch(self, url, max_retries=3):
        for attempt in range(max_retries):
            self.bucket.acquire()               # 每次真实请求前拿令牌
            try:
                r = self.session.get(url, timeout=10)
                if r.status_code == 200:
                    return r.text
                if r.status_code == 429:        # 限流：尊重 Retry-After
                    wait = int(r.headers.get("Retry-After", 2 ** attempt))
                    print(f"  429，等待 {wait}s")
                    time.sleep(wait)
                    continue
                print(f"  状态码 {r.status_code}，放弃 {url}")
                return None
            except requests.RequestException as e:
                print(f"  网络错误({e})，退避重试 {attempt + 1}/{max_retries}")
                time.sleep(2 ** attempt)        # 1s, 2s, 4s
        self.fail_urls.append(url)
        return None

    # ---------- 主流程 ----------
    def run(self, max_items=50):
        self.try_resume()
        if not self.queue:
            self.queue.append(self.BASE)
        # 数据文件用追加模式：续爬时接着写（主键去重交给下游/入库逻辑）
        with open(self.OUT, "a", encoding="utf-8") as out:
            while self.queue and self.item_count < max_items:
                url = self.queue.popleft()
                if url in self.bloom:           # Bloom 判重（含极小概率误判 -> 宁可少抓不重复抓）
                    continue
                self.bloom.add(url)

                html = self.fetch(url)
                if html is None:
                    continue
                self.visited_count += 1

                items, new_urls = self.parse(html, url)
                for it in items:
                    out.write(json.dumps(it, ensure_ascii=False) + "\n")
                    self.item_count += 1
                for u in new_urls:
                    if u not in self.bloom:
                        self.queue.append(u)

                # 每 10 个页面存一次进度
                if self.visited_count % 10 == 0:
                    self.save_ckpt()
        self.save_ckpt()
        print(f"\n[完成] 已访问页面 {self.visited_count}，产出数据 {self.item_count} 条")
        if self.fail_urls:
            print(f"[失败清单] {len(self.fail_urls)} 个 URL 待下次补爬: {self.fail_urls[:3]}...")

    @staticmethod
    def parse(html, url):
        """解析：标题+价格（书籍数据），并从 <a href> 发现新链接"""
        from bs4 import BeautifulSoup   # Day 127 学过的解析库
        soup = BeautifulSoup(html, "lxml")
        items = []
        for card in soup.select("article.product_pod"):
            title = card.select_one("h3 a")["title"]
            price = card.select_one("p.price_color").get_text(strip=True)
            items.append({"title": title, "price": price, "from": urlsplit(url).path})
        # 同域链接才入队（防爬飞）
        new_urls = []
        for a in soup.select("a[href]"):
            absu = urljoin(url, a["href"])
            if urlsplit(absu).netloc == urlsplit(StableCrawler.BASE).netloc:
                new_urls.append(absu)
        return items, new_urls


if __name__ == "__main__":
    StableCrawler().run(max_items=100)
    print("提示：中途 Ctrl+C 杀掉再运行，会从 checkpoint 续爬")
