# Day 176 — ELK 日志系统

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185）
> **子主题**：实战 · 日志采集、存储、检索与可视化

---

## 概念解释

### ELK 是什么

**ELK** 是三件套的合称：

- **Elasticsearch**（E）— 分布式搜索和分析引擎，把日志存成「可搜索的索引」
- **Logstash**（L）— 服务器端数据处理管道，把日志采集、过滤、转换、转发
- **Kibana**（K）— 数据和 Elasticsearch 的可视化仪表板，画图表、看板

合称 **ELK Stack**（现在官方也叫 **Elastic Stack**）。

一句话理解它的分工：

```
日志源 ── Logstash  ── Elasticsearch ── Kibana
（收集）    （加工）      （存储/搜索）     （展示）
```

**为什么不用 `grep` 查日志了？** 因为：

| 场景 | grep / tail | ELK |
|------|-------------|-----|
| 单台服务器一个文件 | ✅ 够用 | ⚠️ 杀鸡用牛刀 |
| 100 台服务器 1000 个日志文件 | ❌ 逐个登录、逐个 grep | ✅ 一键全文检索 |
| 按时间、状态码、用户维度聚合 | ❌ 写脚本拼凑 | ✅ 一次聚合查询 |
| 实时告警 | ❌ 轮询脚本 | ✅ 内置监控告警 |
| 历史趋势图 | ❌ 自己画 | ✅ 拖拽生成 |

---

### Elasticsearch：分布式搜索引擎

Elasticsearch 的**核心模型**：

```
索引 (index)            → 一个日志类型，如 "nginx-access"
  ├─ 分片 (shard)        → 索引分成的碎片，分布在不同节点
  │   └─ 文档 (document) → 一条日志，JSON 格式
  └─ 副本 (replica)      → 分片的备份，防单点故障
```

**倒排索引** 是它快的原因：

```
正排索引（传统数据库）: 文档 ID → 关键词
  1001 → "error"
  1002 → "warning"
  1003 → "error"

倒排索引（Elasticsearch）: 关键词 → 文档 ID 列表
  "error"  → [1001, 1003]
  "warning" → [1002]
```

查「所有 error」→ 直接拿倒排列表，**不用扫描全表**。

**核心 API**：

```
GET /_search           # 搜索
PUT /logs-2026.10.06   # 建索引
GET /logs-2026.10.06   # 查看索引
DELETE /logs-2026.10.06 # 删索引
```

---

### Logstash：日志处理管道

Logstash 的工作方式：

```
input  → 从哪读（文件/数据库/消息队列）
filter → 怎么加工（解析/清洗/富化/过滤）
output → 往哪写（Elasticsearch/文件/邮件）
```

一个典型 pipeline：

```ruby
input {
  file { path => "/var/log/nginx/access.log" }
}

filter {
  grok { match => { "message" => "%{COMBINEDAPACHELOG}" } }
  date  { match => [ "@timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ] }
  mutate { rename => { "message" => "raw_log" } }
}

output {
  elasticsearch { hosts => ["localhost:9200"] }
  stdout { codec => rubydebug }
}
```

**grok** 是把非结构化日志转结构化 JSON 的关键：

```
原始日志:
127.0.0.1 - - [10/Oct/2026:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 2326

grok 模式 COMBINEDAPACHELOG 解析为:
{
  "clientip": "127.0.0.1",
  "timestamp": "10/Oct/2026:13:55:36 +0000",
  "verb": "GET",
  "request": "/api/users",
  "response": 200,
  "bytes": 2326,
  "agent": "Mozilla/5.0 ..."
}
```

---

### Kibana：可视化仪表板

Kibana 的四大功能：

| 功能 | 用途 |
|------|------|
| **Dashboard** | 把多个图表拼成一个看板 |
| **Visualize** | 画柱状图、折线图、饼图 |
| **Discover** | 单表全文检索，像搜索引擎一样查日志 |
| **Dev Tools** | 直接写 ES DSL 查询 |

---

## 原理深入

### Elasticsearch 一次写入的完整链路

```
客户端 PUT 文档
     │
     ├─ 负载均衡 → 某个主节点（coordinator）
     │
     ├─ coordinator 计算分片（哈希路由）
     │   hash("_logs-2026.10.06") % 5 = 3 → shard_03
     │
     ├─ 发写请求到 shard_03 所在节点
     │   ├─ 写入内存 buffer（translog）
     │   └─ 返回成功给 coordinator
     │
     └─ coordinator 汇总所有分片 → 返回 201 给客户端
```

关键点：

- **主分片写成功 ≠ 全局可见**。副本还在刷盘，此时查询可能查不到（**near real time**，默认 1 秒刷新）。
- 要立刻查到，发 `?refresh=true`。
- **写入不阻塞读**：读走旧版本的分片副本，写走新分片。

---

### Elasticsearch 一次查询的完整链路

```
客户端 GET /logs/_search
     │
     ├─ coordinator 节点
     │   ├─ 向所有相关分片发 query（phase: query）
     │   │   └─ 每个分片返回 (docId, score) 局部结果
     │   └─ 全局 top-N 合并 → 返回结果
     │
     └─ 客户端收到结果
```

**查询阶段**：

```json
{
  "query": {
    "bool": {
      "must":    [ { "match": { "response": 200 } } ],
      "filter":  [ { "range": { "@timestamp": { "gte": "now-1h" } } } ],
      "must_not": [ { "match": { "status": 404 } } ]
    }
  }
}
```

- `must`：命中才计分
- `filter`：命中但不计分（可缓存，性能更好）
- `must_not`：命中直接排除

---

### Logstash 的内存与性能模型

Logstash 是**单线程管道**（一个 pipeline 一个 JVM 线程），所以：

```yaml
# pipeline.workers = 1 时，管道串行处理
# 要提高吞吐：增加 workers（但同一 event 会随机分到一个 worker）
pipeline.workers: 4

# 批次大小：每个批次处理的事件数
pipeline.batch.size: 125

# 批次延迟：攒够 batch.size 才发，或等这么久才发
pipeline.batch.delay: 50
```

**常见坑**：

- **背压（backpressure）**：写入慢 → Logstash 内存涨 → OOM。要配 `queue.type: persisted` + `queue.max_bytes`。
- **file input 的 inode 轮转**：日志轮转后 `tail -F` 跟丢。Logstash 用 `sincedb` 记录文件偏移，轮转后自动切到新文件（**默认开，不要关**）。

---

### Beats：轻量采集器

**Beats 家族**（比 Logstash 轻，直接装到业务服务器上）：

| Beats | 用途 |
|-------|------|
| **Filebeat** | 采集文件日志（最常用） |
| **Metricbeat** | 采集系统/应用指标（CPU、内存、QPS） |
| **Packetbeat** | 网络包分析 |
| **Heartbeat** | 监控服务存活 |

典型架构：

```
Filebeat（业务服务器） → Kafka/Logstash → Elasticsearch → Kibana
```

Filebeat 配置极简：

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/nginx/access.log
  fields:
    service: nginx
    env: prod

output.elasticsearch:
  hosts: ["es-cluster:9200"]
```

---

## 定义与使用方法

### 基础查询 DSL

```json
GET /logs-*/_search
{
  "size": 10,
  "query": {
    "match": { "status": 200 }
  }
}
```

### 聚合查询

**统计 HTTP 状态码分布**：

```json
GET /logs-*/_search
{
  "size": 0,
  "aggs": {
    "status_codes": {
      "terms": { "field": "response.keyword" }
    }
  }
}
```

**统计每分钟的请求数**：

```json
GET /logs-*/_search
{
  "size": 0,
  "aggs": {
    "requests_per_minute": {
      "date_histogram": {
        "field": "@timestamp",
        "calendar_interval": "minute"
      }
    }
  }
}
```

---

### Kibana 查询语言（KQL）

KQL 比 DSL 简单，Kibana Discover 用这个：

```
response:200
status:5xx
@timestamp:>now-1h
service:nginx AND response:200
```

---

### 常用 REST API

```bash
# 健康检查
GET /_cluster/health

# 建索引
PUT /logs-2026.10.06

# 查索引信息
GET /logs-2026.10.06

# 删除索引
DELETE /logs-2026.10.06

# 删除所有旧索引（轮转策略）
DELETE /logs-2026.10.*

# 创建索引模板（自动按天建索引）
PUT /_index_template/logs
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": { "number_of_shards": 1, "number_of_replicas": 0 },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "service":   { "type": "keyword" },
        "message":   { "type": "text" }
      }
    }
  }
}
```

---

## 图解

### ELK 整体架构图（ASCII）

```
┌──────────────────────────────────────────────────────────────────────┐
│                         业务服务器集群                                │
│                                                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│  │  Web-01  │  │  Web-02  │  │  App-01  │  ...                        │
│  │ nginx    │  │  nginx   │  │  flask   │                           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                           │
│       │ logs        │ logs        │ logs                            │
│  ┌────▼─────────────▼─────────────▼─────┐                          │
│  │           Filebeat (每个节点)          │                          │
│  └────────────────────┬─────────────────┘                          │
└───────────────────────┼────────────────────────────────────────────┘
                        │ syslog/HTTP
                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         采集层                                         │
│                                                                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │
│  │   Logstash A    │  │   Logstash B    │  │   Kafka         │      │
│  │  (管道加工)      │  │  (管道加工)      │  │  (缓冲队列)      │      │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘      │
│           └─────────────────────┼───────────────────┘               │
│                                 ▼                                    │
└─────────────────────────────────┼────────────────────────────────────┘
                                  │ 写入
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         存储层                                         │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Elasticsearch 集群                          │   │
│  │                                                               │   │
│  │   Node-1         Node-2         Node-3                        │   │
│  │   ┌──────┐      ┌──────┐      ┌──────┐                       │   │
│  │   │shard │      │shard │      │shard │  ← 主分片              │   │
│  │   │  03  │      │  01  │      │  02  │                       │   │
│  │   └──┬───┘      └──┬───┘      └──┬───┘                       │   │
│  │      │replica     │replica     │replica                      │   │
│  │   ┌──▼───┐      ┌──▼───┐      ┌──▼───┐                       │   │
│  │   │shard │      │shard │      │shard │  ← 副本分片            │   │
│  │   │  03  │      │  01  │      │  02  │                       │   │
│  │   └──────┘      └──────┘      └──────┘                       │   │
│  │                                                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
                                  │ 查询
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         展示层                                         │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                         Kibana                                │   │
│  │   Dashboard  │  Discover  │  Visualize  │  Dev Tools          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 倒排索引原理图

```
传统索引（正排）:
┌────────┬───────────────────┐
│ doc_id │ content           │
├────────┼───────────────────┤
│   1    │ "error occurred"  │
│   2    │ "warning issued"  │
│   3    │ "error fixed"     │
└────────┴───────────────────┘
         查 "error" → 扫 3 行

倒排索引:
"error"   → [1, 3]
"occurred"→ [1]
"warning" → [2]
"issued"  → [2]
"fixed"   → [3]
         查 "error" → 直接 [1,3]，O(1)
```

### Logstash pipeline 数据流

```
  ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────────┐
  │  input  │ ──► │ filter  │ ──► │ mutate  │ ──► │   output    │
  │  (文件) │     │ (grok)  │     │ (重命名)│     │(ES + stdout)│
  └─────────┘     └─────────┘     └─────────┘     └─────────────┘
       │               │
  raw text        {clientip, request, response, ...}
  {message}
```

---

## 实战代码案例

完整工程在 `code/` 目录：

| 文件 | 用途 |
|------|------|
| `01-elk-install-setup.py` | 一键部署单节点 ELK（docker-compose） |
| `02-log-collection.py` | 用 Logstash/Filebeat 采集 Nginx 日志 |
| `03-log-analysis-query.py` | 日志查询与聚合分析脚本 |
| `04-dashboard-export.py` | 导出 Kibana 仪表板为 JSON |
| `elk-stack.yml` | Docker Compose 编排 |

---

## 实战实验手册

### 实验 1：部署单节点 ELK（10 分钟）

```bash
git clone git@github.com:Geek0ne/Python-200-days.git
cd Python-200-days/days/day-176-elk-日志系统/code

docker-compose -f elk-stack.yml up -d

# 检查健康
curl -s http://localhost:9200/_cluster/health | python3 -m json.tool
```

预期输出：`"status": "green"`

---

### 实验 2：采集 Nginx 日志（15 分钟）

```bash
# 模拟流量
for i in $(seq 1 100); do
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost/
done

# 用脚本写入测试日志
python3 02-log-collection.py --count 100 --output /tmp/access.log

# 重启 Logstash 让它读到新文件
docker-compose -f elk-stack.yml restart logstash

# 查询
curl -s "http://localhost:9200/logs-*/_search?size=5" | python3 -m json.tool
```

---

### 实验 3：状态码统计聚合（5 分钟）

```bash
curl -s "http://localhost:9200/logs-*/_search?size=0" \
  -H 'Content-Type: application/json' \
  -d '{
    "aggs": {
      "status": { "terms": { "field": "response.keyword" } }
    }
  }' | python3 -m json.tool
```

预期输出类似：

```json
{
  "aggregations": {
    "status": {
      "buckets": [
        { "key": "200", "doc_count": 87 },
        { "key": "404", "doc_count": 8 },
        { "key": "500", "doc_count": 5 }
      ]
    }
  }
}
```

---

### 实验 4：排查 5xx 错误（10 分钟）

```bash
curl -s "http://localhost:9200/logs-*/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": { "range": { "response": { "gte": 500, "lte": 599 } } },
    "sort": [ { "@timestamp": "desc" } ],
    "size": 20
  }' | python3 -m json.tool
```

---

### 实验 5：删除旧索引（维护）

```bash
# 删除 7 天前的索引
curl -s -X DELETE "http://localhost:9200/logs-2026.09.*"

# 删除今天之前的（按天轮转后清理）
curl -s -X DELETE "http://localhost:9200/logs-2026.09.*/"
```

---

## 思考题

1. **为什么 Elasticsearch 默认 1 秒后才能查到刚写入的日志？** 如果要立刻查到该怎么做？

2. **主分片和副本分片有什么区别？** 为什么生产环境建议至少 3 个节点？

3. **Logstash 的 `grok` 模式匹配失败会怎样？** 怎么调试 grok 表达式？（提示：Logstash 自带 grok debugger）

4. **`filter` 和 `must` 有什么区别？** 什么时候用哪个更快？

5. **Filebeat 和 Logstash 应该装在哪里？** 什么场景下需要两层（Filebeat → Logstash → ES）？

6. **索引模板的作用是什么？** 为什么不建议每次写入前手动建索引？

7. **Kibana 的 `size: 0` 是什么意思？** 它返回什么？

---

## 参考资料

- [Elasticsearch 官方文档](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash 官方文档](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Kibana 官方文档](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Filebeat 官方文档](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)
- [ELK 架构最佳实践](https://www.elastic.co/what-is/elk-stack)

---

<div align="center">
  <sub>Day 176 · Phase 11 · 自动化运维与 DevOps</sub>
</div>
