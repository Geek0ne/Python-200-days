#!/usr/bin/env python3
"""03-polite-crawler.py — 实战：一个"礼貌爬虫"骨架

特性：
  - 启动时读取并缓存 robots.txt（带 TTL，不重复下载）
  - 每个请求前做 can_fetch 检查
  - 每域名限速（令牌桶简化版：固定间隔）
  - 全程审计日志，留下"我努力合规"的证据链

用法: python3 03-polite-crawler.py <url> [url2 ...]
"""
import sys
import time
import logging
from urllib import robotparser, request as urlrequest
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("polite_audit.log", encoding="utf-8")],
)
log = logging.getLogger("polite-crawler")

UA = "MyPoliteBot/1.0 (+https://example.com/bot; contact@example.com)"
ROBOTS_TTL = 3600  # robots.txt 缓存 1 小时
DEFAULT_DELAY = 2.0

class RobotsCache:
    """按域名缓存 robots.txt 解析结果，避免每个请求都重新下载。"""
    def __init__(self, ttl: int = ROBOTS_TTL):
        self.ttl = ttl
        self._cache = {}  # netloc -> (parser, fetched_at)

    def get(self, netloc: str, scheme: str) -> robotparser.RobotFileParser:
        now = time.time()
        hit = self._cache.get(netloc)
        if hit and now - hit[1] < self.ttl:
            return hit[0]
        rp = robotparser.RobotFileParser()
        rp.set_url(f"{scheme}://{netloc}/robots.txt")
        try:
            rp.read()
            log.info("robots.txt 已加载: %s", netloc)
        except Exception as e:
            log.warning("robots.txt 读取失败(%s)，视为允许", e)
        self._cache[netloc] = (rp, now)
        return rp

class RateLimiter:
    """每域名固定间隔限速：保证对同一站点的请求间隔 >= delay 秒。"""
    def __init__(self):
        self._last = {}  # netloc -> 上次请求时间戳

    def wait(self, netloc: str, delay: float):
        last = self._last.get(netloc, 0)
        elapsed = time.time() - last
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last[netloc] = time.time()

class PoliteCrawler:
    def __init__(self, ua: str = UA, default_delay: float = DEFAULT_DELAY):
        self.ua = ua
        self.default_delay = default_delay
        self.robots = RobotsCache()
        self.limiter = RateLimiter()
        self.stats = {"fetched": 0, "skipped_by_robots": 0, "failed": 0}

    def fetch(self, url: str) -> str | None:
        o = urlparse(url)
        if o.scheme not in ("http", "https") or not o.netloc:
            log.error("非法 URL: %s", url)
            return None

        # 1) robots 检查
        rp = self.robots.get(o.netloc, o.scheme)
        if not rp.can_fetch(self.ua, url):
            log.warning("⛔ robots.txt 禁止，跳过: %s", url)
            self.stats["skipped_by_robots"] += 1
            return None

        # 2) 限速（优先用站点的 Crawl-delay）
        delay = rp.crawl_delay(self.ua) or self.default_delay
        self.limiter.wait(o.netloc, delay)

        # 3) 发请求
        req = urlrequest.Request(url, headers={"User-Agent": self.ua})
        try:
            with urlrequest.urlopen(req, timeout=15) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                body = resp.read(200_000).decode(charset, errors="replace")  # 只读前 200KB
                self.stats["fetched"] += 1
                log.info("✅ 已抓取 (%d bytes): %s", len(body), url)
                return body
        except Exception as e:
            self.stats["failed"] += 1
            log.error("抓取失败 %s: %s", url, e)
            return None

def main():
    urls = sys.argv[1:] or ["https://www.python.org/"]
    crawler = PoliteCrawler()
    for u in urls:
        crawler.fetch(u)
    log.info("统计: %s", crawler.stats)

if __name__ == "__main__":
    main()
