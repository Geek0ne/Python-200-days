"""
01-scheduler-basics.py
Scrapy 调度器基础用法演示

运行方式：直接 python3 01-scheduler-basics.py
无需 Scrapy 环境，用纯 Python 模拟调度器行为
"""

import heapq
import hashlib
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ============================================================
# 1. 简易调度器实现：理解调度器的工作原理
# ============================================================

@dataclass(order=True)
class Request:
    """模拟 Scrapy 的 Request 对象"""
    priority: int = field(compare=True)  # 优先级（越大越先）
    url: str = field(compare=False)
    callback: str = field(default='parse', compare=False)
    fingerprint: str = field(default='', compare=False, init=False)

    def __post_init__(self):
        """自动生成请求指纹"""
        self.fingerprint = hashlib.sha1(
            self.url.encode() + b'GET' + b''
        ).hexdigest()


class SimpleScheduler:
    """
    简易调度器：模拟 Scrapy 调度器的核心行为
    - 请求入队
    - 优先级调度
    - 去重过滤
    """

    def __init__(self):
        self.queue = []          # 优先级堆
        self.seen = set()        # 已见指纹集合
        self.pending_count = 0   # 待处理请求数

    def enqueue(self, request: Request, dont_filter: bool = False) -> bool:
        """
        将请求加入调度队列
        返回 True 表示成功入队，False 表示被去重过滤
        """
        # 去重检查
        if not dont_filter and request.fingerprint in self.seen:
            print(f"  ⛔ 去重过滤: {request.url}")
            return False

        # 记录指纹
        self.seen.add(request.fingerprint)
        # 加入优先级堆（注意：Python heapq 是最小堆，取负数实现最大优先）
        heapq.heappush(self.queue, (-request.priority, request))
        self.pending_count += 1
        print(f"  ✅ 入队成功: {request.url} (优先级={request.priority})")
        return True

    def next_request(self) -> Optional[Request]:
        """取出优先级最高的请求"""
        if not self.queue:
            return None
        neg_priority, request = heapq.heappop(self.queue)
        self.pending_count -= 1
        return request

    @property
    def size(self) -> int:
        return self.pending_count


# ============================================================
# 2. 演示：调度器的实际行为
# ============================================================

def demo_scheduler():
    """演示调度器的优先级调度和去重"""
    print("=" * 60)
    print("📊 Demo 1: 调度器基础 — 优先级调度与去重")
    print("=" * 60)

    scheduler = SimpleScheduler()

    # 模拟一个电商网站的爬取
    requests = [
        Request(url="https://shop.com/", priority=10, callback="parse_home"),
        Request(url="https://shop.com/category/phones", priority=5, callback="parse_category"),
        Request(url="https://shop.com/product/123", priority=0, callback="parse_product"),
        Request(url="https://shop.com/category/laptops", priority=5, callback="parse_category"),
        Request(url="https://shop.com/", priority=10, callback="parse_home"),  # 重复请求
    ]

    print("\n📥 入队请求:")
    for req in requests:
        scheduler.enqueue(req)

    print(f"\n队列大小: {scheduler.size}")
    print("\n📤 出队顺序（按优先级）:")
    while scheduler.size > 0:
        req = scheduler.next_request()
        print(f"  → {req.url} (优先级={req.priority})")

    print(f"\n剩余队列大小: {scheduler.size}")


# ============================================================
# 3. 自定义去重：忽略查询参数
# ============================================================

def custom_fingerprint(url: str, ignore_params: list = None) -> str:
    """
    自定义指纹生成：忽略指定的查询参数
    场景：时间戳、session_id 等动态参数不应影响去重
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

    if ignore_params is None:
        ignore_params = []

    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    # 移除忽略的参数
    for key in ignore_params:
        params.pop(key, None)

    # 重新排序参数
    sorted_query = urlencode(sorted(params.items()), doseq=True)
    new_url = urlunparse(parsed._replace(query=sorted_query))

    return hashlib.sha1(new_url.encode()).hexdigest()


def demo_custom_dedup():
    """演示自定义去重逻辑"""
    print("\n" + "=" * 60)
    print("📊 Demo 2: 自定义去重 — 忽略动态参数")
    print("=" * 60)

    urls = [
        "https://api.example.com/products?page=1&timestamp=111",
        "https://api.example.com/products?page=1&timestamp=222",  # 同页不同时间戳
        "https://api.example.com/products?page=1&session_id=abc",
        "https://api.example.com/products?page=2&timestamp=333",  # 不同页
    ]

    ignore = ['timestamp', 'session_id']
    seen = set()

    print(f"\n忽略参数: {ignore}\n")
    for url in urls:
        fp = custom_fingerprint(url, ignore)
        is_new = fp not in seen
        if is_new:
            seen.add(fp)
        status = "✅ 新请求" if is_new else "⛔ 重复"
        print(f"  {status}: {url}")
        print(f"    指纹: {fp[:16]}...")


# ============================================================
# 4. 优先级调度实际场景
# ============================================================

def demo_priority_scheduling():
    """演示不同页面类型的优先级设置"""
    print("\n" + "=" * 60)
    print("📊 Demo 3: 电商爬虫优先级策略")
    print("=" * 60)

    scheduler = SimpleScheduler()

    # 模拟真实爬取场景
    pages = [
        ("首页", "https://shop.com/", 10),
        ("分类-手机", "https://shop.com/cat/phones", 8),
        ("分类-电脑", "https://shop.com/cat/laptops", 8),
        ("商品详情-热门", "https://shop.com/p/1001", 5),
        ("商品详情-普通", "https://shop.com/p/1002", 3),
        ("评论页", "https://shop.com/p/1001/reviews", 1),
        ("API-价格", "https://shop.com/api/price/1001", 7),
    ]

    print("\n📥 按类型设置不同优先级:")
    for name, url, priority in pages:
        req = Request(url=url, priority=priority, callback="parse")
        scheduler.enqueue(req)

    print(f"\n📤 出队顺序（电商爬虫实际调度）:")
    step = 1
    while scheduler.size > 0:
        req = scheduler.next_request()
        print(f"  {step}. {req.url} (priority={req.priority})")
        step += 1


# ============================================================
# 5. 基于 deque 的 FIFO 队列（MemoryQueue 的简化版）
# ============================================================

def demo_memory_queue():
    """演示内存队列的工作方式"""
    print("\n" + "=" * 60)
    print("📊 Demo 4: 内存队列 vs 优先级队列")
    print("=" * 60)

    # FIFO 队列（先进先出）
    fifo = deque()
    urls = [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]

    print("\nFIFO 队列（先进先出）:")
    for url in urls:
        fifo.append(url)
        print(f"  入队: {url}")

    print("\n出队顺序:")
    while fifo:
        print(f"  出队: {fifo.popleft()}")

    # 优先级队列
    print("\n优先级队列（高优先级先出）:")
    pq = []
    items = [("低优先级", 1), ("高优先级", 10), ("中优先级", 5)]
    for name, pri in items:
        heapq.heappush(pq, (-pri, name))
        print(f"  入队: {name} (priority={pri})")

    print("\n出队顺序:")
    while pq:
        neg_pri, name = heapq.heappop(pq)
        print(f"  出队: {name} (priority={-neg_pri})")


# ============================================================
# 主函数
# ============================================================

if __name__ == '__main__':
    print("🐍 Scrapy 调度器基础用法演示")
    print("=" * 60)

    demo_scheduler()
    demo_custom_dedup()
    demo_priority_scheduling()
    demo_memory_queue()

    print("\n" + "=" * 60)
    print("✅ 所有演示完成！")
    print("=" * 60)
