# Day 191 · 概念词典：爬虫引擎骨架

> 本文是 README 的压缩版，用于快速复习与面试口述。所有数字来自本机实测。

## 1. 引擎分层

| 层 | 输入 | 输出 | 不知道什么 |
|---|---|---|---|
| Frontier | 新链接 | 下一个 URL | 网络、HTML |
| Fetcher | URL | HTML / 分类错误 | 页面含义 |
| Parser | HTML | 字段 + 新链接 | 限速、重试 |
| Pipeline | 字段 | 干净记录 | 存储形态 |
| Sink | 记录 | 一行数据 | 抓取顺序 |

**分层的判据**：这一层能不能用纯内存单测？能，就该独立成层。

## 2. URL 规范化八条规则

1. 相对路径用 base 补全
2. scheme / host 小写
3. 去默认端口 80 / 443
4. 折叠 `//`，解析 `.` 与 `..`
5. query 按键排序
6. 丢 `utm_*` / `ref` / `fbclid` / `gclid` / `spm`
7. 丢 fragment
8. 非 http(s) 拒绝

**规范形态即幂等键**：去重、UPSERT、续爬三处必须用同一个键，否则三条链路各说各话。

## 3. 队列

| 结构 | 出队复杂度 | 问题 |
|---|---|---|
| `list.pop(0)` | O(n) | 10 万条时每次出队搬内存 |
| `deque.popleft()` | O(1) | 无 |
| 纯 `set` | 无序 | 随机爬，可能陷入单层无限膨胀 |
| `deque` + `seen` | O(1) | 需要额外内存存 seen |

**BFS vs DFS**：爬虫默认 BFS——先把一层抓全，才能估算站点规模和价值；
DFS 会顺着一条链深入，遇到“下一天/下一页”型无限链就再也回不来。

## 4. 限速

```text
每 worker sleep(1/rate)  → 全局 = workers × rate（实测 5.9 倍超速）
全局令牌桶 capacity=1    → 偏差 0.3%–0.8%
```

| 参数 | 含义 | 爬虫取值 |
|---|---|---|
| rate | 长期平均速率 | 按站点容忍度，1–10 req/s 常见 |
| capacity | 瞬时突发额度 | **1**（严格），批量详情页可 3–5 |
| 预扣 | 锁内记账、锁外 sleep | 防多线程同抢一个令牌 |

**p95 而不是平均值**：平均值把 1 次 3 秒的超时摊薄到看不见，p95 会直接暴露。

## 5. robots.txt

- 语义：**最长匹配**，不是文件顺序
- 取用：`urllib.robotparser.RobotFileParser.can_fetch("*", url)`
- 拿不到 robots（404/超时）→ 默认放行（RFC 9309 允许）
- 禁区 URL 必须 **release 预算**，否则“限 40 页只抓 22 页”

## 6. 重试

| 状态 | 分类 | 处理 |
|---|---|---|
| 2xx | 成功 | 落库 |
| 408/425/429/5xx | 可重试 | 退避后重试 |
| 400/401/403/404/405/410/451 | 永久 | 立即放弃，记 failures |
| 超时/连接重置/DNS | 可重试 | 退避后重试 |

退避公式（full jitter）：

```python
ceiling = min(cap, base * 2 ** (attempt - 1))
sleep(random.uniform(0, ceiling))
```

`Retry-After` 优先级高于任何自算退避。

## 7. 幂等

```sql
INSERT INTO pages(url, ...) VALUES(?, ...)
ON CONFLICT(url) DO UPDATE SET ...
```

- 应用层 `if not exists: insert` 有竞态；唯一约束是原子的
- 重放安全 = at-least-once 投递 + 幂等写入
- 续爬 = `all_urls - SELECT url FROM pages`

## 8. 今天踩过的坑（面试可直接讲）

1. `..` 不是过滤而是出栈——手写路径归一化漏了它，自检 FAIL
2. `capacity=rate` 是突发额度不是桶大小——60 req/s 实测跑成 119.55
3. robots 拒绝不归还预算——40 页预算只抓到 22 页

## 9. 一分钟口述版

> 爬虫引擎分五层：Frontier 管“下一个抓谁”，Fetcher 管“怎么抓且不越界”，
> Parser 抽字段和链接，Pipeline 清洗，Sink 幂等落库。
> 正确性的第一关是 URL 规范化——规范形态同时充当去重键和数据库主键。
> 限速必须是全局共享令牌桶，容量设 1；每 worker 各自 sleep 会让速率翻 N 倍（实测 5.9 倍）。
> 重试要先分类 4xx 与 5xx，退避用 full jitter，尊重 Retry-After。
> 落库用 UPSERT，断点续爬就是查差集。
> 先把引擎做诚实，再去谈反爬对抗。
