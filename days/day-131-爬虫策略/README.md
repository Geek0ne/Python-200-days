# Day 131 - 爬虫策略

> 🎯 **今日目标**：掌握大规模爬虫的三块基石--URL 去重（set / Bloom Filter）、断点续爬（状态持久化）、限速与礼貌爬取，把"能跑一次"的爬虫升级成"跑得稳、跑得久、跑得快也不被封"的生产级系统。

---

## 📋 概念总览

前四天解决了"怎么抓"（requests / Scrapy / Selenium / Playwright）。今天解决"怎么抓得稳"：

| 问题 | 不处理的后果 | 解决方案 |
|---|---|---|
| URL 去重 | 同一页抓 N 遍，数据重复浪费带宽 | set / 布隆过滤器 |
| 断点续爬 | 跑 3 小时崩了，从头再来 | 状态持久化 + 恢复机制 |
| 限速礼貌 | 把人家网站打挂，IP 被封 | 延迟 / AutoThrottle / 并发控制 |

---

## 🧹 一、URL 去重

### 1.1 为什么必须去重？

- 网页之间互相链接（A→B→A），**环形链接**会让爬虫无限循环；
- 翻页、推荐位、不同入口指向同一 URL；
- 失败重试时同一 URL 会再次入队。

### 1.2 方案一：set（简单粗暴，小规模够用）

```python
visited = set()          # 已访问 URL
queue = deque(seed_urls) # 待访问队列

while queue:
    url = queue.popleft()
    if url in visited:       # O(1) 判重
        continue
    visited.add(url)
    # ... 下载解析，新链接 if url not in visited: queue.append(url)
```

**代价**：一个 URL 平均 70 字节，`set` 存字符串本身 + Python 对象开销 ≈ 200+ 字节/条。
**估算**：1000 万 URL ≈ 2~3GB 内存。**中小规模（百万级以下）完全够用，别过度设计。**

**规范 URL 很重要**（去重前先归一化，否则同一个页面认不出来）：

```python
from urllib.parse import urlsplit, urlunsplit, parse_qsl

def normalize(url):
    """URL 归一化：去掉片段、跟踪参数，统一大小写与末尾斜杠"""
    parts = urlsplit(url)
    # 丢弃 #fragment；query 参数排序并剔除跟踪参数
    query = [(k, v) for k, v in sorted(parse_qsl(parts.query))
             if k not in ("utm_source", "utm_medium", "session")]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path,
                       "&".join(f"{k}={v}" for k, v in query), ""))
# http://A.com/x/?utm_source=b <-> http://a.com/x  ->  同一个页面！
```

### 1.3 方案二：布隆过滤器（Bloom Filter）

**核心思想**：用"可能存在"换内存--它可能误判"存在"（假阳性），但绝不漏判"不存在"。

**原理（bit 数组 + k 个哈希函数）**：

```
插入 URL：
  用 k=3 个哈希函数算出 3 个位置 -> 把 bit 数组对应位置置 1

  h1(url) -> bit[2]=1
  h2(url) -> bit[7]=1
  h3(url) -> bit[11]=1

查询 URL：
  三个位置都是 1？ -> "可能存在"（也可能是别的 URL 撞的）
  任一位置是 0？  -> "肯定不存在"（100% 确定）
```

**内存效果**：1 亿 URL、1% 误判率，只需约 **120MB**（set 要 20GB+）。

**误判的后果**：极少数没爬过的 URL 被误判为爬过 -> 被跳过 -> 丢一点数据。**取舍**：大规模爬虫宁可丢 1% 也不爆内存。

**不能删除**：标准布隆的 bit 是共享的，清掉一个 URL 的位会误伤别人。要删用 Counting Bloom（每个位换成计数器）。

```python
# 自己实现一个极简版（理解原理用；生产用 pybloom-live / mmh3）
import mmh3   # pip install mmh3
from bitarray import bitarray   # pip install bitarray

class SimpleBloomFilter:
    def __init__(self, expected_items=1_000_000, fp_rate=0.01):
        # 公式：m = -n·ln(p)/(ln2)^2, k = m/n·ln2
        self.m = int(-expected_items * (fp_rate ** 0.5) * 2.08)  # 简化
        self.m = max(self.m, 1024)
        self.k = 3
        self.bits = bitarray(self.m)
        self.bits.setall(0)

    def _positions(self, url):
        # 用 mmh3 的多 seed 生成 k 个哈希（比造 k 个哈希函数简单）
        return (abs(mmh3.hash(url, seed=i)) % self.m for i in range(self.k))

    def add(self, url):
        for pos in self._positions(url):
            self.bits[pos] = 1

    def __contains__(self, url):
        return all(self.bits[pos] for pos in self._positions(url))
```

### 1.4 方案选型

| 规模 | 方案 |
|---|---|
| < 100 万 | set + URL 归一化 |
| 百万~亿级 | Bloom Filter（内存） |
| 多机分布式 | Redis set / RedisBloom / Scrapy-Redis |

---

## 🔋 二、断点续爬

### 2.1 思路：把状态当数据存起来

爬虫的"状态"就三样：**已访问集合、待爬队列、已产出数据**。只要定期把它们落盘（JSON/SQLite/Redis），崩溃后重新加载就能接着跑。

```
运行中：                       崩溃后重启：
queue: [u5,u6,u7]              读 checkpoint.json
visited: {u1..u4}       ──►    queue 和 visited 恢复原样
data: [...1000 条]             data 以追加模式续写
        │ 每 N 条存一次 checkpoint
        ▼
  checkpoint.json
```

### 2.2 关键细节（避坑）

1. **原子写入**：直接 `open("ckpt.json","w")` 写一半又崩 = 孤儿文件。正确姿势：先写临时文件再 `os.replace()`（同分区 rename 是原子操作）。
2. **数据去重**：续爬后写入的数据可能和崩溃前重叠，落库前按主键去重（或用 SQLite 主键约束）。
3. **何时存**：每 N 条或每 M 分钟存一次，太频繁伤性能，太稀疏丢进度。
4. **队列也要持久化**：只在内存 deque 里的待爬 URL 崩了就没了。

```python
import os, json

def save_checkpoint(state, path="checkpoint.json"):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    os.replace(tmp, path)   # 原子替换，绝不会写一半

# 重启时：存在 checkpoint 就恢复，不存在就全新开始
```

Scrapy 的对应方案：`scrapy crawl myspider -s JOBDIR=crawls/run1`（内置 job 挂起/恢复）。

---

## 🐢 三、限速与礼貌爬取

### 3.1 为什么要"礼貌"？

- 对方服务器是别人的：高频请求 = 消耗别人资源，过火就是攻击；
- 爬虫被识别后 IP 被封、数据拿不到，**礼貌也是自保**；
-  robots.txt 是"网站对爬虫的公告"，遵守它是底线（法律与道德都是）。

### 3.2 限速手段（由粗到细）

```python
# ① 固定延迟：每个请求间 sleep
time.sleep(1)

# ② 令牌桶（token bucket）：允许突发但限制平均速率
class TokenBucket:
    """每 rate 秒生成一个令牌，拿到令牌才能发请求"""
    def __init__(self, rate=1.0, capacity=5):
        self.rate = rate          # 令牌生成速率（个/秒）
        self.capacity = capacity  # 桶容量（允许的突发量）
        self.tokens = capacity
        import time; self.last = time.monotonic()

    def acquire(self):
        import time
        while True:
            now = time.monotonic()
            # 补充这段时间该生成的令牌（不超容量）
            self.tokens = min(self.capacity,
                              self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            time.sleep((1 - self.tokens) / self.rate)  # 等下个令牌

# ③ Scrapy AutoThrottle：根据响应速度自适应调节
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 60
```

**固定延迟 vs 令牌桶**：固定延迟"永远慢"；令牌桶允许突发（页面刚加载完快速发几个请求，然后歇），更接近真实用户行为，吞吐也更高。

### 3.3 礼貌爬取清单

- [ ] 遵守 robots.txt（`urllib.robotparser` 可编程检查）
- [ ] 设置合理 UA，标识自己是爬虫（有条件留联系方式）
- [ ] 控制单域名并发（Scrapy `CONCURRENT_REQUESTS_PER_DOMAIN`）
- [ ] 错峰：避开目标站高峰时段
- [ ] 尊重 `Retry-After` 响应头；收到 429 就退避
- [ ] 指数退避重试：`delay = base * 2**retry_count`，别 1 秒一次硬撞

---

## 🏗️ 四、稳定大规模爬虫架构

```
                ┌─────────────┐
  seed URLs ──► │ URL 调度器   │◄──┐
                │ 去重(Bloom)  │   │ 新发现的 URL
                └──────┬──────┘   │
                       ▼          │
                ┌─────────────┐   │
                │ 限速器       │  │
                │ (令牌桶)     │   │
                └──────┬──────┘   │
                       ▼          │
                ┌─────────────┐   │
                │ 下载器       │───┘ 解析出 new_urls + items
                │ 重试/退避    │
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │ 数据管道     │ 去重入库（主键约束）
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │ 断点模块     │ 定期 checkpoint（原子写）
                └─────────────┘
```

---

## 💻 五、实战

`code/03-practical-crawler.py`：把以上全部组装成一个**可断点续爬、Bloom 去重、令牌桶限速**的健壮爬虫（爬 books.toscrape.com，中途 Ctrl+C 杀掉再重启可验证续爬）。

---

## ❓ 思考题

1. 布隆过滤器为什么"可能误报存在，绝不漏报不存在"？这个特性对爬虫意味着什么？
2. 1000 万 URL 的爬虫，用 set 去重大约要多少内存？Bloom Filter（1% 误判）呢？误判的 1% 会造成什么后果？
3. 为什么 checkpoint 要"写临时文件 + os.replace"而不能直接覆盖原文件？
4. 令牌桶和固定 sleep 相比有什么优势？什么场景下优势最明显？
5. 收到 429（Too Many Requests）后，爬虫正确的应对流程是什么？

---

## 📚 延伸阅读

- 布隆过滤器详解：https://en.wikipedia.org/wiki/Bloom_filter
- Scrapy AutoThrottle：https://docs.scrapy.org/en/latest/topics/autothrottle.html
- 明天预告：Day 132 代理池搭建 -- 当 IP 被封时的"车轮战"方案。
