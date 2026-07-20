"""
Day 076 - Scrapy 反爬策略与实战示例
演示常见的反爬手段及其应对方法

运行方式：
    python 03-反爬策略与实战.py

注意：本示例仅做技术演示，请遵守目标网站的 robots.txt
"""
import time
import random
import hashlib
import json
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser


# ============================================================
# 1. 随机 User-Agent 轮换
# ============================================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
]


class RandomUserAgentMiddleware:
    """
    随机 User-Agent 中间件
    
    在 Scrapy 中，中间件拦截请求/响应，可以：
    - 修改请求头
    - 添加代理
    - 处理重试
    - 添加 Cookie
    """
    
    def __init__(self, user_agents=None):
        self.user_agents = user_agents or USER_AGENTS
    
    def process_request(self, request):
        """处理出站请求 - 随机设置 User-Agent"""
        ua = random.choice(self.user_agents)
        request["User-Agent"] = ua
        print(f"  🎭 User-Agent: {ua[:50]}...")
        return request


# ============================================================
# 2. 下载延迟与限速控制
# ============================================================

class RateLimiter:
    """
    请求限速器
    
    控制请求频率，避免触发反爬。
    支持固定延迟和随机延迟两种模式。
    """
    
    def __init__(self, delay=1.0, randomize=True):
        """
        Args:
            delay: 基础延迟秒数
            randomize: 是否随机化延迟（0.5*delay ~ 1.5*delay）
        """
        self.delay = delay
        self.randomize = randomize
        self.last_request_time = 0
    
    def wait(self):
        """等待直到可以发送下一个请求"""
        now = time.time()
        elapsed = now - self.last_request_time
        
        if self.randomize:
            actual_delay = self.delay * random.uniform(0.5, 1.5)
        else:
            actual_delay = self.delay
        
        if elapsed < actual_delay:
            sleep_time = actual_delay - elapsed
            print(f"  ⏳ 限速等待 {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()


# ============================================================
# 3. 会话管理（处理 Cookie）
# ============================================================

class SessionManager:
    """
    会话管理器
    
    某些网站需要登录态才能访问，
    SessionManager 帮助维护 Cookie。
    """
    
    def __init__(self):
        self.cookies = {}
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    
    def update_cookies(self, response_cookies):
        """从响应中更新 Cookie"""
        self.cookies.update(response_cookies)
        print(f"  🍪 更新 Cookie: {list(response_cookies.keys())}")
    
    def get_request_headers(self):
        """获取包含 Cookie 的请求头"""
        cookie_str = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        headers = self.headers.copy()
        if cookie_str:
            headers["Cookie"] = cookie_str
        return headers


# ============================================================
# 4. URL 去重过滤器
# ============================================================

class URLFilter:
    """
    URL 去重过滤器
    
    基于 URL 指纹去重，避免重复爬取相同页面。
    支持忽略查询参数进行去重。
    """
    
    def __init__(self, ignore_params=None):
        self.seen_fingerprints = set()
        self.ignore_params = ignore_params or ["utm_source", "utm_medium", "utm_campaign"]
    
    def get_fingerprint(self, url, ignore_params=True):
        """生成 URL 指纹"""
        parsed = urlparse(url)
        
        if ignore_params:
            # 移除跟踪参数
            params = parsed.query.split("&") if parsed.query else []
            filtered = [p for p in params 
                       if not any(p.startswith(param + "=") 
                                 for param in self.ignore_params)]
            clean_query = "&".join(sorted(filtered))
        else:
            clean_query = parsed.query
        
        fingerprint = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"
        return hashlib.md5(fingerprint.encode()).hexdigest()
    
    def is_seen(self, url):
        """检查 URL 是否已访问"""
        fp = self.get_fingerprint(url)
        if fp in self.seen_fingerprints:
            return True
        self.seen_fingerprints.add(fp)
        return False


# ============================================================
# 5. 完整爬虫示例：带反爬应对的电商爬虫
# ============================================================

class EcommerceSpider:
    """
    电商爬虫 - 综合演示反爬策略
    
    功能：
    - 随机 User-Agent
    - 请求限速
    - URL 去重
    - 会话管理
    - 错误重试
    """
    
    def __init__(self, base_url, max_retries=3):
        self.base_url = base_url
        self.max_retries = max_retries
        
        # 初始化各组件
        self.ua_middleware = RandomUserAgentMiddleware()
        self.rate_limiter = RateLimiter(delay=1.5)
        self.session = SessionManager()
        self.url_filter = URLFilter()
        
        # 统计
        self.stats = {
            "requests": 0,
            "success": 0,
            "failed": 0,
            "duplicates": 0,
        }
    
    def make_request(self, url):
        """
        发送请求（带反爬策略）
        
        在实际 Scrapy 中，这些逻辑分散在：
        - UserAgentMiddleware
        - RetryMiddleware
        - HttpCacheMiddleware
        - AutoThrottleExtension
        """
        import requests as req
        
        # 1. 检查是否已访问
        if self.url_filter.is_seen(url):
            print(f"  🔁 跳过重复: {url}")
            self.stats["duplicates"] += 1
            return None
        
        # 2. 限速
        self.rate_limiter.wait()
        
        # 3. 设置随机 UA
        headers = self.session.get_request_headers()
        headers["User-Agent"] = random.choice(USER_AGENTS)
        
        # 4. 带重试的请求
        for attempt in range(1, self.max_retries + 1):
            try:
                self.stats["requests"] += 1
                print(f"  🌐 请求 [{attempt}/{self.max_retries}]: {url[:60]}")
                
                response = req.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                self.stats["success"] += 1
                return response
                
            except req.RequestException as e:
                print(f"  ❌ 请求失败: {e}")
                if attempt < self.max_retries:
                    wait_time = attempt * 2  # 指数退避
                    print(f"  ⏳ {wait_time}s 后重试...")
                    time.sleep(wait_time)
                else:
                    self.stats["failed"] += 1
        
        return None
    
    def parse_product_list(self, html_content):
        """
        解析商品列表页
        
        这里简化为 HTML 解析演示，
        实际 Scrapy 使用 Selector 更强大。
        """
        # 简单的正则提取演示
        products = []
        # 注意：实际项目中应使用 Scrapy Selector
        # 这里仅做演示
        print(f"  📦 解析页面内容 ({len(html_content)} 字节)")
        return products
    
    def crawl(self, start_url, max_pages=5):
        """
        执行爬取
        
        演示完整的爬取流程：
        1. 从起始 URL 开始
        2. 提取商品数据
        3. 发现新链接
        4. 递归爬取
        """
        print(f"\n🕷️  开始爬取: {start_url}")
        print(f"   最大页数: {max_pages}")
        print(f"   请求延迟: {self.rate_limiter.delay}s")
        print("=" * 50)
        
        pages_crawled = 0
        
        while pages_crawled < max_pages:
            response = self.make_request(start_url)
            
            if response is None:
                break
            
            # 解析页面
            self.parse_product_list(response.text)
            pages_crawled += 1
            
            print(f"  ✅ 第 {pages_crawled} 页完成")
        
        # 输出统计
        print(f"\n{'=' * 50}")
        print(f"📊 爬取统计:")
        print(f"   总请求: {self.stats['requests']}")
        print(f"   成功: {self.stats['success']}")
        print(f"   失败: {self.stats['failed']}")
        print(f"   去重跳过: {self.stats['duplicates']}")
        print(f"{'=' * 50}")


# ============================================================
# 6. 运行演示
# ============================================================

def main():
    print("=" * 60)
    print("Day 076 - Scrapy 反爬策略与实战演示")
    print("=" * 60)
    
    # 演示 1: User-Agent 轮换
    print("\n📌 演示 1: User-Agent 轮换")
    middleware = RandomUserAgentMiddleware()
    for i in range(3):
        fake_request = {}
        result = middleware.process_request(fake_request)
        print(f"  请求 {i+1}: UA 已设置")
    
    # 演示 2: 限速器
    print("\n📌 演示 2: 下载延迟控制")
    limiter = RateLimiter(delay=1.0, randomize=True)
    for i in range(3):
        start = time.time()
        limiter.wait()
        elapsed = time.time() - start
        print(f"  请求 {i+1}: 等待 {elapsed:.1f}s")
    
    # 演示 3: URL 去重
    print("\n📌 演示 3: URL 去重过滤")
    url_filter = URLFilter()
    test_urls = [
        "https://example.com/product/1?utm_source=google",
        "https://example.com/product/1?utm_source=baidu",
        "https://example.com/product/2",
        "https://example.com/product/1?utm_source=google",
    ]
    for url in test_urls:
        seen = url_filter.is_seen(url)
        status = "跳过" if seen else "新增"
        print(f"  [{status}] {url}")
    
    # 演示 4: 完整爬虫（模拟）
    print("\n📌 演示 4: 完整爬虫流程")
    print("  （实际运行需要网络连接，此处仅展示结构）")
    
    spider = EcommerceSpider("https://example.com")
    print(f"  爬虫已初始化，UA轮换: {len(spider.ua_middleware.user_agents)} 个")
    print(f"  请求延迟: {spider.rate_limiter.delay}s")
    print(f"  最大重试: {spider.max_retries} 次")
    
    print("\n✅ 所有演示完成！")
    print("\n💡 提示: 将这些中间件集成到 Scrapy 项目中，")
    print("   在 settings.py 的 DOWNLOADER_MIDDLEWARES 中启用即可。")


if __name__ == "__main__":
    main()
