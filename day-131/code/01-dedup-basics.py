# -*- coding: utf-8 -*-
"""
Day 131 - 爬虫策略基础：URL 去重（set / Bloom Filter / URL 归一化）
=====================================================================
运行：python 01-dedup-basics.py
（纯本地运行，不发网络请求）
"""
from collections import deque
from urllib.parse import urlsplit, urlunsplit, parse_qsl
import time


# ---------------------------------------------------------------
# 1. URL 归一化：去重的前提！
#    同一页面可能有 N 种写法，不归一化 set 会认成不同 URL
# ---------------------------------------------------------------
def normalize(url: str) -> str:
    """URL 归一化：去 fragment、去跟踪参数、排序 query、统一大小写和末尾斜杠"""
    parts = urlsplit(url)
    # 1) 剔除跟踪参数 + 参数按字典序排（顺序不同视为相同）
    TRACKING = {"utm_source", "utm_medium", "utm_campaign", "session", "ref"}
    query_pairs = sorted((k, v) for k, v in parse_qsl(parts.query)
                         if k not in TRACKING)
    query = "&".join(f"{k}={v}" for k, v in query_pairs)
    # 2) 域名小写、去掉末尾斜杠、丢弃 #fragment
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       path, query, ""))


def demo_normalize():
    urls = [
        "http://Example.com/list/?utm_source=x&id=5",
        "http://example.com/list/?id=5",
        "http://example.com/list?id=5#comments",
        "http://example.com/list/?id=5&utm_medium=banner",
    ]
    for u in urls:
        print(f"  {u:55s} -> {normalize(u)}")
    print("归一化后全部相同:", len({normalize(u) for u in urls}) == 1)


# ---------------------------------------------------------------
# 2. set 去重 + 队列：小规模爬虫的骨架
# ---------------------------------------------------------------
def demo_set_dedup():
    # 模拟环形链接：A->B->C->A，如果不去重会死循环
    graph = {
        "a": ["b", "c"],
        "b": ["c", "a"],      # b 又指回 a
        "c": ["a"],           # c 也指回 a
        "d": ["b"],
    }
    visited = set()
    queue = deque(["a"])
    order = []
    while queue:
        url = queue.popleft()
        if url in visited:            # O(1) 判重，环在这里被切断
            continue
        visited.add(url)
        order.append(url)
        queue.extend(graph.get(url, []))
    print("遍历顺序:", order, "（无死循环、无重复）")


# ---------------------------------------------------------------
# 3. 极简布隆过滤器：理解原理
#    生产建议用成熟库（如 pybloom-live / redis 的 RedisBloom）
# ---------------------------------------------------------------
class SimpleBloomFilter:
    """
    bit 数组 + k 个哈希函数。
    - add:    k 个位置置 1
    - 查询:   k 个位置全 1 -> "可能存在"；任一为 0 -> "肯定不存在"
    特性：有假阳性（误判存在），无假阴性（绝不漏判不存在）
    """
    def __init__(self, expected_items=100_000, fp_rate=0.01):
        # 标准公式：m = -n * ln(p) / (ln2)^2 ；k = (m/n) * ln2
        import math
        n, p = expected_items, fp_rate
        self.m = max(int(-n * math.log(p) / (math.log(2) ** 2)), 1024)
        self.k = max(int((self.m / n) * math.log(2)), 1)
        self.bits = bytearray((self.m + 7) // 8)   # 每字节存 8 个 bit
        self.count = 0

    def _positions(self, item: str):
        """用双哈希技巧：h_i(x) = h1(x) + i*h2(x)，省去 k 个独立哈希函数"""
        h1 = hash(item) & 0x7FFFFFFF
        h2 = (hash(item + "#seed") & 0x7FFFFFFF) or 1
        for i in range(self.k):
            yield (h1 + i * h2) % self.m

    def add(self, item: str):
        for pos in self._positions(item):
            self.bits[pos // 8] |= (1 << (pos % 8))   # 置 1
        self.count += 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[pos // 8] & (1 << (pos % 8))
                   for pos in self._positions(item))


def demo_bloom():
    bf = SimpleBloomFilter(expected_items=1000, fp_rate=0.01)
    urls = [f"http://site.com/page/{i}" for i in range(1000)]
    for u in urls:
        bf.add(u)

    # ① 已添加的 URL：必须 100% 报"存在"（无假阴性）
    hit = sum(1 for u in urls if u in bf)
    print(f"已添加 URL 命中: {hit}/1000（必须等于 1000）")

    # ② 未添加的 URL：统计假阳性率
    test = [f"http://site.com/other/{i}" for i in range(10000)]
    fp = sum(1 for u in test if u in bf)
    print(f"未添加 URL 误判: {fp}/10000 = {fp/100:.2f}%（应接近 1%）")

    # ③ 内存对比
    set_mem = sum(len(u) for u in urls)          # set 至少存下所有字符串
    bloom_mem = len(bf.bits)                     # bloom 只存 bit 数组
    print(f"1000 个 URL：字符串总量 {set_mem}B vs bloom 位图 {bloom_mem}B")


def main():
    print("== 1. URL 归一化 ==")
    demo_normalize()
    print("\n== 2. set 去重（环形链接）==")
    demo_set_dedup()
    print("\n== 3. 布隆过滤器 ==")
    demo_bloom()


if __name__ == "__main__":
    main()
