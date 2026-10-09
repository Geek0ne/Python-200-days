# Day 177 — Prometheus + Grafana

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185）
> **子主题**：监控指标暴露 · Prometheus 采集 · Grafana 看板 · **实战**：应用监控看板

---

## 概念解释

### 先分清：Day 176 的「日志」和今天的「指标」

昨天 ELK 处理的是**日志（log）**，今天 Prometheus 处理的是**指标（metric）**。
它们不是替代关系，回答的是不同的问题：

| | 日志（ELK） | 指标（Prometheus） |
|---|---|---|
| 数据形态 | 离散事件，一行一条，可长可短 | 数值 + 时间戳，固定结构 |
| 典型问题 | 「**为什么**这次请求失败了？」 | 「**现在**慢了多少？从几点开始？」 |
| 查询方式 | 全文检索 + 聚合 | PromQL 数值运算 |
| 单条体积 | 大（KB 级） | 小（几十字节） |
| 保留期 | 通常 7–30 天 | 通常 15 天–1 年（可下采样） |
| 成本 | 高（存储全文） | 低（只存数字） |

一句话：**日志用来查因，指标用来看势。**

### Prometheus 是什么

Prometheus 是一个**时间序列数据库 + 拉取式采集器 + 查询语言（PromQL）+ 告警引擎**。
2012 年从 SoundCloud 出来，2016 年加入 CNCF，现在是云原生监控的事实标准
（Kubernetes 的内置监控就走它）。

四个组件，各管一段：

```
应用/主机/exporter ──(HTTP GET /metrics)──▶ Prometheus ──▶ PromQL ──▶ Grafana / Alertmanager
      「被采集」                「拉」           「存储+查询」         「展示/告警」
```

### 拉（pull）模型 vs 推（push）

这是 Prometheus 最反直觉、也最关键的一个设计决定：

```
pull（Prometheus 主动来拉）           push（Agent 主动推上去）
                                    
Prometheus ──GET /metrics──▶ 应用     应用 ──POST──▶ 收集端
   ▲                                          │
   └── 我知道你活没活（GET 失败=挂了）          └── 你不推我就永远不知道你挂了
```

| 维度 | pull（Prometheus） | push（StatsD / 大多数 SaaS） |
|---|---|---|
| 谁发起 | 采集端 | 被采集端 |
| 存活探测 | **白送**：拉不到就是挂了 → `up=0` | 需要额外心跳机制 |
| 目标管理 | 集中配置/服务发现，一处改全局生效 | 每个实例各自配置 |
| 短命任务（批处理） | ❌ 可能还没被拉就结束了 | ✅ 天然支持 |
| 防火墙方向 | 采集端 → 被采集端 | 被采集端 → 采集端 |
| 传输是否可控 | ✅ 天然限流（一次拉一遍） | ❌ 推送风暴可能压垮收集端 |

**三条从「拉」直接推出来的结论**（后面实战会一一验证）：

1. `up` 这个指标不需要你写一行代码，Prometheus 自动为每个目标生成；
2. 修改采集范围只需改 **采集端** 的配置，被采集的应用完全不知情；
3. 秒级就结束的批处理任务采不到——那类要用 **Pushgateway** 兜底。

### 数据模型：一切都是一条「时间线」

Prometheus 里没有「表」也没有「行」，只有：

```
指标名 + 一组标签  =  一条时间线（series）
   ↓
时间线 + 时间戳 + 浮点值  =  一个样本（sample）

app_http_requests_total{method="GET",path="/",status="200"}   ← 这是一条时间线的身份证
   08:57:12 → 30
   08:57:17 → 30
   08:57:22 → 30
```

几个必须记住的规矩：

- **标签值的每一种组合都是一条独立的时间线**。`path="/"` 和 `path="/api/items"`
  是两条线，各自计数。标签组合数量爆炸叫做**高基数（high cardinality）**，
  是 Prometheus 最常见的事故原因（比如把 `user_id`、`request_id` 当标签）。
- **指标名和标签名都不能随便改**：改了就是新的时间线，历史数据接不上。
- 值是 `float64`，文本格式里连整数都写成 `30.0`（后面的坑之一）。

### 四种指标类型

Prometheus 客户端只有四种类型，选错类型是新手第一大坑：

| 类型 | 语义 | 能不能减 | 典型用途 | 查询时怎么用 |
|---|---|---|---|---|
| **Counter** | 只增不减的累计值 | ❌ | 请求数、错误数、字节数 | **必须**配 `rate()` / `increase()` |
| **Gauge** | 当前值，可增可减可设值 | ✅ | 在线人数、队列长度、内存占用 | 直接查，或 `avg_over_time()` |
| **Histogram** | 分桶累计 + 总和 + 计数 | ❌（桶累计） | 延迟、请求体大小 | `histogram_quantile()` 算分位 |
| **Summary** | 客户端算好的分位 + 总和 + 计数 | ❌ | 同上，但想要客户端分位 | 直接读 `quantile` 标签 |

选型口诀：**「数次数」用 counter，「量当前」用 gauge，「看分布」用 histogram。**

> ⚠️ 反面教材：用 counter 存「当前在线人数」—— 用户下线时你只能 `dec()`，
> 而 counter 的 `dec()` 会让 `rate()` 算出负数，看板直接崩。

### 暴露格式（exposition format）

被采集端要吐出来的东西是**纯文本**，不是 JSON。每一族指标三行起：

```
# HELP app_http_requests_total HTTP 请求总数
# TYPE app_http_requests_total counter
app_http_requests_total{method="GET",path="/",status="200"} 30.0
```

- `# HELP` —— 人类可读说明（会出现在 Grafana 的 tooltip 里）
- `# TYPE` —— 四种类型之一，Prometheus 靠它决定怎么算
- 样本行 —— `指标名{标签}` 空格 `值`；**没有时间戳**，时间戳由采集端在收到时打上
  （这正是「拉」模型的又一个体现：谁收到谁打时间，避免了客户端时钟不准的污染）

### PromQL：指标世界的 SQL

一条 PromQL 表达式，输入是一批时间线，输出也是一批时间线：

```
app_http_requests_total                        # 原始（几乎没人直接看）
sum by (status) (rate(app_http_requests_total[1m]))   # 每秒请求数，按状态码分组
histogram_quantile(0.95, rate(app_http_request_duration_seconds_bucket[5m]))  # P95
```

`[1m]` 叫**区间选择器**：它把「最近 1 分钟内的所有样本」取出来交给函数。
**这是 PromQL 最容易出错的地方**——什么时候选多长的窗口，是有讲究的。

### Grafana：只负责画

Grafana 自己**不存数据**，它连数据源（这里就是 Prometheus），拿查询结果画图。
所以架构上它是可替换的：换成 VictoriaMetrics、Thanos 照样能用。

关键认知：**Grafana 的看板是 JSON，不是「点出来」的**。
它可以导出、进版本库、被 review、被 provisioning 自动加载——下面实战会验证这一点。

---

## 原理深入

### 一次 scrape 的完整链路

```
        每 5s 一轮
┌──────────────────────────────────────────────────────────┐
│ 1. 读 scrape_configs → 得到目标列表 [{job=app, 9101}]      │
│ 2. 对每个目标 GET http://host:9101/metrics                │
│ 3. 解析文本 → (指标名, 标签集合, 值)                        │
│ 4. ★ 用「采集端的当前时间」给每个样本打时间戳（客户端说不了算）│
│ 5. 写进内存 + WAL 预写日志 → 每 2h 落成一个持久块            │
│ 6. 无论成功失败，都写入一个系统指标 up{job=...} = 1 / 0      │
└──────────────────────────────────────────────────────────┘
```

第 6 步值得展开：**`up` 是 Prometheus 唯一「替你做」的指标**。
只要配置里写了目标，不管它活不活、返回什么，都会有一条 `up` 时间线。
所以「服务是不是挂了」这个最常用的问题，答案永远是：

```promql
up{job="app"} == 0
```

### TSDB 内部：为什么它写得快、查得也快

- **WAL（预写日志）**：新样本先追加到 WAL（顺序写，快），再进内存块。
  进程崩了不至于丢最近两小时的样本。
- **块（block）**：内存里的数据每 2 小时压成一块不可变文件，后台压缩合并。
  **不可变**是关键——查询不需要加锁，随便并发。
- **倒排索引**：`指标名{标签}` → 时间线 ID，所以「按标签筛时间线」很快。
- **保留期（retention）**：默认 15 天，按时间整块删除（删除 = 删目录，不是扫全表）。

理解了「块不可变」，就理解了为什么 Prometheus 重写历史数据这么别扭，
以及为什么长时间存储要交给 Thanos / VictoriaMetrics 这类旁路系统。

### 为什么 counter 必须配 `rate()`

counter 的值本身没有意义（一个进程跑了 3 天可能累计 100 万次请求），
有意义的是**变化率**：

```
原始 counter:      1000 ── 1050 ── 1100 ── 1150     （只能看出在涨）
rate(counter[1m]):      0.83 ── 0.83 ── 0.83       （每秒 0.83 次）
```

`rate()` 还做了两件聪明事：

1. **自动处理 counter 归零**（进程重启后 counter 从 0 重来）——
   它把归零识别为「重置」，跳过那一段，而不是算出一个巨大的负数。
2. **外推（extrapolation）**：窗口边界上的样本不一定正好落在边界，
   `rate()` 会按比例外推，所以 `rate()` 的结果是**估算值**，不是精确除法。

第 2 点导致一个反直觉结论：`increase()` 的结果可能不是整数。

### histogram 的桶是「累计」的

这是 histogram 最容易看错的地方：

```
demo_latency_seconds_bucket{le="0.05"} 2.0     ← 耗时 ≤ 0.05s 的有 2 个
demo_latency_seconds_bucket{le="0.1"}  4.0     ← 耗时 ≤ 0.1s 的累计有 4 个（含前面那 2 个）
demo_latency_seconds_bucket{le="+Inf"} 6.0     ← 所有观测，等于 _count
```

`le` = less than or equal。**每个桶都包含前面所有桶**，所以：

- 桶计数必须单调不减；
- 想要「落在 0.05–0.1 之间」的个数，得自己 `le="0.1"` 减 `le="0.05"`；
- 精度由桶边界决定——**边界划多了才准，少了就只能插值**。

### `histogram_quantile()` 的插值本质

它**不是**从原始耗时里数出来的 P95，而是从累计桶里**线性插值**算出来的：

```
假设 le="0.1" 累计 90 个，le="0.25" 累计 100 个，总数 100：
P95 落在 (0.1, 0.25] 这个桶里，桶内线性插值：
 0.1 + (0.25-0.1) × (95-90)/(100-90) = 0.175s
```

两条推论：

1. 桶边界如果刚好卡在你关心的分位上（比如 0.2s 是 SLA 线），结果会很准；
   否则只能给你一个「在这两个边界之间」的粗糙值。
2. `histogram_quantile()` **必须**作用在 `rate()` 之后的 `_bucket` 上，
   直接对原始 `_bucket` 用会得到错误结果（下面翻车复盘里会踩）。

### 拉模型的边界

- **采不到短命任务**：跑 200ms 就退出的脚本，5s 一轮的采集永远碰不上。
  解法是让它把结果推给 **Pushgateway**，Prometheus 改去拉 Pushgateway。
- **目标多了要服务发现**：写死 IP 列表在 K8s 里没法用，所以有
  `kubernetes_sd_configs`、`file_sd_configs`、`consul_sd_configs` 等。
- **时钟以采集端为准**：这对监控是好事（客户端时间乱也不影响存储），
  但排查「指标时间戳对不上业务日志时间」时要知道这一点。

---

## 定义与方法（速查）

### Python 暴露指标（prometheus_client）

```python
from prometheus_client import Counter, Gauge, Histogram, start_http_server

c = Counter("app_http_requests_total", "HTTP 请求总数", ["path", "status"])
c.labels(path="/", status="200").inc()          # 打标签 + 计数

g = Gauge("app_inflight", "处理中的请求数")
g.inc(); g.dec(); g.set(5)                       # 可增可减可设

h = Histogram("app_latency_seconds", "耗时", buckets=(.01, .05, .1, .5, 1))
h.observe(0.037)                                 # 落进对应桶

start_http_server(9101)                          # 起一个 /metrics 端点
```

> 反面清单：`path`、`status`、`method` 这类**有限取值**的可以当标签；
> `user_id`、`request_id`、完整 URL 这类**无限取值**的绝对不能（高基数）。

### PromQL 速查

| 表达式 | 用途 |
|---|---|
| `up{job="app"} == 0` | 目标挂了 |
| `rate(counter[1m])` | 每秒速率（Grafana 里最常用） |
| `increase(counter[5m])` | 5 分钟增量 |
| `sum by (status) (rate(counter[1m]))` | 按标签聚合 |
| `topk(3, rate(counter[1m]))` | 最热的前 3 条 |
| `histogram_quantile(0.95, rate(bucket[5m]))` | P95 |
| `avg_over_time(gauge[10m])` | gauge 的平滑 |
| `time() - process_start_time_seconds` | 进程已运行秒数 |
| `rate(counter[5m]) > 0.1` | 阈值过滤 |

### HTTP API 速查

```
GET /api/v1/query?query=<expr>&time=<unix>                 瞬时查询
GET /api/v1/query_range?query=&start=&end=&step=5          区间查询（画图用）
GET /api/v1/targets                                        采集目标与健康状态
GET /api/v1/rules                                          告警/记录规则
GET /-/ready                                               就绪探针
```

响应永远是 `{"status":"success"|"error", "data": {...}}`，
`resultType` 是 `vector`（瞬时）或 `matrix`（区间）。

### Grafana provisioning 目录约定

```
grafana/provisioning/datasources/*.yml     数据源（落盘即生效，不用点 UI）
grafana/provisioning/dashboards/*.yml      看板提供者（告诉 Grafana 去哪读 JSON）
grafana/dashboards/*.json                  看板本体
```

---

## 实战环境

| 项 | 版本 / 说明 |
|---|---|
| 主机 | Linux 7.0.0-34-generic (x64) |
| Docker | 29.1.3 |
| Prometheus | `prom/prometheus:v3.0.1`（实测 `--version` 见实验 2） |
| Python | 3.12，`prometheus_client` **0.26.0**（`pip install --target` 隔离安装） |

本日代码在 `code/`，四个脚本都能脱离 Prometheus 自检（`--self-test`）；
只有真正采集/画图的那两步需要 Docker。

---

## 图解

见 [`diagrams/README.md`](diagrams/README.md)：拉模型时序、scrape 链路、
TSDB 落盘、PromQL 数据流、看板数据流。

---

## 实验 1：让应用暴露 `/metrics`

**目的**：看清「被采集端」到底要吐什么。

**准备**：
```bash
python3 -m pip install --target ./.deps prometheus_client
```

**执行**（逐条可复制）：
```bash
PYTHONPATH=./.deps python3 code/01-expose-metrics.py --self-test
python3 code/01-expose-metrics.py --self-test          # 无依赖，走 stdlib 回退
PYTHONPATH=./.deps python3 code/01-expose-metrics.py --once
```

**预期结果**：`--self-test` 退出码 0；`--once` 打印文本暴露格式。

**实际结果**（本机真实 stdout，2026-10-09）：

```
✅ self-test 通过 | backend=prometheus_client | 端口=33095 | Content-Type=text/plain | 抓取 3557 字节
✅ self-test 通过 | backend=stdlib-fallback | 端口=36011 | Content-Type=text/plain | 抓取 367 字节
```

`--once` 的关键几行：

```
# HELP app_http_requests_total HTTP 请求总数
# TYPE app_http_requests_total counter
app_http_requests_total{method="GET",path="/",status="200"} 2.0
app_http_requests_total{method="GET",path="/api/items",status="200"} 1.0
app_http_requests_total{method="GET",path="/missing",status="404"} 1.0
# TYPE app_http_inflight gauge
app_http_inflight 0.0
# TYPE app_http_request_duration_seconds histogram
app_http_request_duration_seconds_bucket{le="0.025"} 4.0
app_http_request_duration_seconds_bucket{le="+Inf"} 4.0
```

**结论**：
- 暴露格式就是「`# HELP` + `# TYPE` + 样本行」，**没有时间戳**——时间由采集端打；
- 同一个指标名加了不同标签，就是**不同的时间线**（三条 `app_http_requests_total`）；
- 整数也写成 `2.0`，因为 Prometheus 的值是 float64；
- 没装 `prometheus_client` 也能跑（stdlib 回退），这证明了格式本身没什么魔法。

**清理**：`--self-test` 自己绑 0 号端口并立即关闭，不留进程；`Ctrl-C` 停手动起的服务。

---

## 实验 2：Prometheus 真的来拉（`up` 从哪来）

**目的**：验证 pull 模型，以及 `up` 是采集端自动生成的。

**准备**（生成配置并起栈）：
```bash
python3 code/04-scrape-and-dashboard.py --out /tmp/day177/stack
# 应用（被采集端）
setsid nohup env PYTHONPATH=./.deps python3 code/01-expose-metrics.py --port 9101 &
# Prometheus（采集端，--network host 才能拉到本机 9101）
docker run -d --name d177-prom --network host \
  -v /tmp/day177/stack/prometheus.yml:/etc/prometheus/prometheus.yml:ro \
  prom/prometheus:v3.0.1 --config.file=/etc/prometheus/prometheus.yml
```

**预期结果**：`/api/v1/targets` 里两个目标 `health=up`。

**实际结果**（2026-10-09T00:58Z）：

```
job=app          url=http://localhost:9101/metrics      health=up    lastScrape=2026-10-09T00:58:09.546320971Z
job=prometheus   url=http://localhost:9090/metrics      health=up    lastScrape=2026-10-09T00:58:08.885230241Z
```

> 注意第二个目标是 **Prometheus 自己**——配置里那一段没有删，
> 因为元监控（Prometheus 自己挂了谁知道）是这个体系的标配。

真实 PromQL：

```
$ python3 code/03-promql-query.py --query 'up'
up{instance=localhost:9090,job=prometheus}  1   @00:56:58Z
up{instance=localhost:9101,job=app}  1   @00:56:58Z

$ python3 code/03-promql-query.py --query 'app_http_requests_total'
app_http_requests_total{instance=localhost:9101,job=app,method=GET,path=/,status=200}  30   @00:57:17Z
app_http_requests_total{instance=localhost:9101,job=app,method=GET,path=/api/items,status=200}  30   @00:57:17Z
app_http_requests_total{instance=localhost:9101,job=app,method=GET,path=/missing,status=404}  30   @00:57:17Z
```

**结论**：
- **我们没写任何「上报」代码**，Prometheus 主动拉，`up` 自动就有——这是 pull 的红利；
- `up` 的标签里自动带了 `job` 和 `instance`，这也是采集端加的；
- 应用完全不知道 Prometheus 的存在（第 2 条推论）。

**清理**：`docker rm -f d177-prom`（实验 4 会一起收）。

---

## 实验 3：PromQL —— 一个「看起来该有数、结果是 0」的坑

**目的**：跑通查询接口，并亲手撞上 `rate()` 的窗口陷阱。

**执行**：
```bash
for i in $(seq 1 30); do
  curl -s -o /dev/null http://localhost:9101/
  curl -s -o /dev/null http://localhost:9101/api/items
  curl -s -o /dev/null http://localhost:9101/missing
done
sleep 8
python3 code/03-promql-query.py --query 'sum by (status) (rate(app_http_requests_total[1m]))'
```

**实际结果**（第一次，2026-10-09T00:57:17Z）：

```
# resultType=vector · 时间线 2 条
{status=200}  0   @00:57:17Z
{status=404}  0   @00:57:17Z
```

**这不对啊**：counter 明明从 0 涨到了 30（上一个实验刚验证过）。

**排查过程**：
```bash
# 1. 拉原始样本看变化到底发生在什么时候
GET /api/v1/query_range?query=app_http_requests_total{path="/",status="200"}&step=5
  08:57:12 30
  08:57:17 30
  08:57:22 30
  08:57:27 30
  08:57:32 30
```

**根因**：窗口 `[1m]` 内的**每一个样本都已经是终值 30**。
那 30 次自增全部发生在窗口起点之前，窗口里根本没有「增量」——
`rate()` 如实告诉你：这段时间没涨。**表达式没错，窗口选错了。**

**验证**（重新打流量，立刻查）：
```
$ ... --query 'sum(rate(app_http_requests_total[1m]))'
  0.393   @00:57:54Z
```

有增量落进窗口，`rate()` 立刻给出非零值。

**结论**：
- `rate()` 只对**窗口内**的样本做差。窗口不覆盖「变化发生的那一段」，结果就是 0；
- 所以排障时先问「我关心的变化发生在什么时间」，再定 `[1m]` / `[5m]` / `[1h]`；
- 这也解释了为什么 Grafana 上的图在「刚打完流量」时可能还是平的——
  不是没数据，是**采集间隔（scrape_interval）还没过去，样本还没进来**。

**清理**：无（只读查询）。

---

## 实验 4：Grafana 看板，用文件而不是鼠标

**目的**：把「看板」变成可进版本库的产物。

**执行**：
```bash
python3 code/04-scrape-and-dashboard.py --self-test
python3 code/04-scrape-and-dashboard.py --out /tmp/day177/stack
docker run -d --name d177-grafana --network host \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  -v /tmp/day177/stack/grafana/provisioning:/etc/grafana/provisioning:ro \
  -v /tmp/day177/stack/grafana/dashboards:/etc/grafana/dashboards:ro \
  grafana/grafana:11.4.0
```

**实际结果**（生成物 + 结构校验，2026-10-09）：

```
✅ self-test 通过：生成 4 个文件；prometheus.yml 指向 :9101、看板 4 个面板，数据源 uid 全场一致
    
生成：
  prometheus           /tmp/day177/stack/prometheus.yml
  datasource           /tmp/day177/stack/grafana/provisioning/datasources/day177-datasource.yml
  dashboard_provider   /tmp/day177/stack/grafana/provisioning/dashboards/day177.yml
  dashboard            /tmp/day177/stack/grafana/dashboards/day177-app.json
```

**未实测**：本机多个镜像源都拉不下 `grafana/grafana:11.4.0`（底层层已存在，
清单始终不落地），所以**容器启动、数据源自动加载、看板渲染这三步没有在本机跑过**。
按「宁可空着也不编」的规矩，这里不填假输出。预期与验证方法：

- 预期：`curl -s localhost:3000/api/health` 返回 `{"database":"ok",...}`；
  `curl -s 'localhost:3000/api/search?query='` 能列出 `Day 177 · 应用监控看板`。
- 验证方法：镜像可用后执行上面的 `docker run`，再跑 `04 --up`，
  它会依次探测 `/-/ready`、`/api/health`、拉 `/api/v1/targets` 和 `/api/search` 并打印结果。

**结论（已实测部分）**：
- 看板的本质是 **JSON**（4 个面板、每条曲线就是一句 PromQL）；
- 数据源 uid 必须与面板里引用的 uid 一致，**否则图全空**——这是 provisioning
  最常踩的坑，脚本的自检专门断言了这一点；
- 因为都是文件，看板可以 code review、可以回滚，而不是「谁在 UI 上点过」。

**清理**：`docker rm -f d177-grafana d177-prom`。

---

## 翻车复盘（三个真 bug，全部在本日实测中出现）

### 1. `DuplicateTimeseries`：指标注册了两次

**症状**：`--self-test` 直接抛异常：

```
prometheus_client.registry.DuplicateTimeseries: Duplicated timeseries in
CollectorRegistry: {'app_http_requests', 'app_http_requests_created', 'app_http_requests_total'}
```

**假设**：`build_app()` 被调用了两次。
**验证**：`main()` 里先无条件 `app = build_app()`，随后 `self_test()` 里又建了一次。
**根因**：Prometheus 客户端默认注册到一个**进程级全局 registry**，
同名指标第二次注册会被拒绝（这是**保护**，不是 bug——否则两条线会互相覆盖）。
**修复**：把 `build_app()` 移到 `--self-test` 分支之后，只建一次。
**复测**：`✅ self-test 通过 | backend=prometheus_client`。

> 教训：写这种脚本时，任何「模块级/进程级只允许一次」的注册，
> 都要保证**只有一条创建路径**。用 `--self-test` 而不是肉眼看，一下就抓到。

### 2. `Summary` 的 `quantiles=` 参数已经被移除

**症状**：

```
TypeError: MetricWrapperBase.__init__() got an unexpected keyword argument 'quantiles'
```

**假设**：我记的 API 是不是过时了？
**验证**：`inspect.signature(Summary.__init__)` —— 确认签名里只有
`name, documentation, labelnames, namespace, subsystem, unit, registry, _labelvalues`。
装的库文档里当场写着：

> "You can use Histograms for aggregatable calculation of quantiles."

**根因**：`prometheus_client` 在较新版本里**移除了客户端侧的自定义分位**，
官方直接把分位这件事推给 Histogram + `histogram_quantile()`。
**修复**：`02-metric-types.py` 改成只演示 summary 的 `_sum/_count`，
并在自检里断言「传 `quantiles=` 会 `TypeError`」——把 API 现状钉进测试。
**复测**：

```
✅ self-test 通过：counter 单调 / gauge 可增减 / histogram 桶累计 /
   summary 仅 _sum+_count（quantiles= 已移除），四项语义均成立
```

> 教训：**别凭记忆写 API**。一个 `TypeError` + 一次 `inspect.signature()`
> 十秒钟定案，比在网上找三篇互相抄的博客快得多。

### 3. `rate()` 返回 0（见实验 3）

**症状**：counter 涨了 30，`rate(...[1m])` 却是 0。
**根因**：增量全部发生在窗口起点之前，**窗口内没有变化**。
**修复**：不是改代码，是改**窗口长度**（或改查询时机）。
**复测**：重新打流量后同一表达式给出 `0.393`。

> 教训：PromQL 的「没数据」和「没变化」是两件事：
> 前者返回空结果，后者返回 `0`。看板上的平线，两者长得一模一样。

---

## 清理（每次实验后都做）

```bash
docker rm -f d177-prom d177-grafana          # 收容器
pkill -f "01-expose-metrics.py --port 9101"  # 收应用（别用 pkill -f python3，会误伤）
rm -rf /tmp/day177                            # 收临时目录
```

自检项：
```bash
ss -ltnp | grep -E ':9101|:9090|:3000'   # 三个端口都应无输出
docker ps --format '{{.Names}}' | grep d177 || echo "无残留容器"
```

---

## 思考题

1. 为什么 Prometheus 的样本里**没有时间戳**？如果让客户端自己打时间戳，
   引入的问题是什么？（提示：时钟偏移、以及「拉」这个动作发生在谁身上）
2. 用 counter 记录「当前在线用户数」会出什么问题？如果你只有一个
   `user_login_total` / `user_logout_total` 两个 counter，怎么算出在线数？
3. `histogram_quantile(0.95, app_latency_seconds_bucket)`（**不带 `rate()`**）
   会算出什么？为什么必须先 `rate()` 再 `histogram_quantile()`？
4. 一个每 300ms 跑完的批处理脚本，怎么才能被 Prometheus 监控到？
   为什么它自己加个 `/metrics` 端点不行？
5. `up{job="app"}` 和 `app_http_requests_total` 停止更新，在 PromQL 里
   分别表现成什么？这两个信号在排障时分别说明什么？

---

## 交付清单

- `code/01-expose-metrics.py` —— 应用暴露 `/metrics`（prometheus_client + stdlib 回退）
- `code/02-metric-types.py` —— 四种指标类型的语义与坑
- `code/03-promql-query.py` —— PromQL 瞬时/区间查询 + 离线桩自检
- `code/04-scrape-and-dashboard.py` —— 采集配置 + Grafana provisioning 生成
- `diagrams/README.md` —— 五张原理图
- `exercises/checklist.md` —— 练习与检查表
