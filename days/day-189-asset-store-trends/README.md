# Day 189 — 综合项目 I（四）：资产入库与趋势可视化

> **阶段**：Phase 12 — 综合实战
> **项目**：企业资产监控系统 · 第 4/5 天
> **子主题**：SQLite 资产模型 · 增量快照 · 变更检测 · 趋势看板
> **代码**：1 个夹具生成器 + 5 个脚本，全部带 `--self-test`
> **实测环境**：Linux 7.0.0-34-generic / Python 3.12.3 / SQLite 3.45.1 / 2026-10-19

---

## 今天在项目里的位置

~~~text
Day 186  资产发现        → 域名 / IP
Day 187  端口 + 指纹     → 127.0.0.1:18080 是 HTTP 服务
Day 188  Web 漏洞检测    → 这个 HTTP 服务有 SQLi / XSS
Day 189  入库 + 可视化   → 把"某一天的结果"变成"可比较的历史"
Day 190  调度 + 告警     → 让整条链路自己跑起来
~~~

昨天之前，扫描器每次运行都把结果打印到终端，跑完就没了。
今天要解决一个更实际的问题：**怎么知道资产是在变多、变少，还是只是扫描器抽风？**

答案不是"再扫一次"，而是：**把每次扫描当成一份不可变快照存起来，再对相邻快照做集合差。**

---

## 概念速览

完整定义见 **`concepts.md`**，SQL / Python API 速查见 **`sql-cheatsheet.md`**。

| 概念 | 一句话 | 为什么重要 |
|---|---|---|
| 资产（asset） | 一个 `(ip, port, proto)` 三元组 | 只有自然键稳定，自增 id 会变 |
| 当前状态表 | 每个资产一行，保存"现在" | 查询快，回答"当前暴露面" |
| 观测流水 | 每次扫描看到了哪些资产 | 趋势图的原料，不可变 |
| 全量快照 | 一次扫描的完整观测集合 | 只有全量才能判断"消失" |
| 增量差集 | 相邻快照的 appeared/missing/gone | 告警和日报的核心 |
| grace 期 | 连续 N 次没看到才确认下线 | 抑制端口抖动造成的假告警 |
| 幂等入库 | 同一份数据重跑结果不变 | 重试、补扫不会污染数据 |
| UPSERT | 有则更新、无则插入 | 资产库的标准写入方式 |
| WAL | 写前日志，读写不互斥 | 扫描写入时看板仍可查询 |
| 趋势口径 | 每天取最后一次快照 | 否则"扫得越勤数字越大" |

---

## 概念解释

### 1. 当前状态表 vs 观测流水：为什么要两张表

只存当前状态会丢历史：

~~~text
Day 1: 10.0.0.5:22  active
Day 2: 10.0.0.5:22  active     ← 覆盖 last_seen
Day 3: 端口关闭，行被 DELETE   ← "曾经存在过"这件事消失了
~~~

只存流水又会很慢：

~~~text
每次问"22 端口现在还开着吗" → 扫全表找最后一条记录 → O(n) 且写法复杂
~~~

标准解法是**两层模型**：

~~~text
            ┌─────────────────────────────┐
   写路径 → │ assets（当前真相，唯一键）  │ ← 看板/告警直接查，O(1)
            └──────────────▲──────────────┘
                           │ UPSERT
            ┌──────────────┴──────────────┐
            │ scans + scan_assets（流水） │ ← 趋势/审计按天聚合
            └─────────────────────────────┘
~~~

- `assets`：回答"现在有什么"，会被更新；
- `scans` / `scan_assets`：回答"某天看到了什么"，只追加、不修改。

这就是 CQRS（命令查询职责分离）的简化版：**写模型负责记录事实，读模型负责快速回答。**

### 2. 自然键为什么不能是自增 id

程序里经常犯的错：

~~~python
# 错误：拿数据库 id 做资产身份
old_ids = {row["id"] for row in old_scan}
new_ids = {row["id"] for row in new_scan}
new_assets = new_ids - old_ids      # 永远是空集或全是噪音
~~~

自增 id 是**存储实现细节**：重建库、换机器、VACUUM 后都可能变。
资产的业务身份是 `(ip, port, proto)`——只有它跨扫描稳定。

同理，不能"按行数比较"：

~~~text
昨天 100 行，今天 100 行  →  看起来没变化
实际：关了 3 个端口，又开了 3 个新端口  →  风险完全变了
~~~

集合差必须基于键，而不是数量。

### 3. 一次扫描 = 一份全量快照

增量扫描（只扫上次没扫的）不能直接用来判断"消失"：
没扫到可能只是**没扫**，不是**关了**。

所以变更检测的前提是：每次扫描覆盖同一批目标，产出一份**全量观测**。
扫描器可以内部做增量优化，但交给入库模块的必须是"这次看到的完整集合"。

### 4. 五种变更，语义各不相同

| 事件 | 含义 | 触发条件 | 典型动作 |
|---|---|---|---|
| `appeared` | 新暴露 | 键不在库中 | 立刻告警（可能是误开公网） |
| `changed` | 服务/版本变了 | 同键，service 或 banner 不同 | 关注版本回滚、补丁缺失 |
| `missing` | 这次没看到 | 同键在库，本次未观测 | 只记录，不告警 |
| `gone` | 确认下线 | 连续 `grace` 次未观测 | 关闭工单、更新台账 |
| `revived` | 下线后又出现 | 状态为 gone 的键再次被观测 | 高优先级：可能是临时开放 |

**`missing` 和 `gone` 必须分开。** 端口抖动、防火墙临时规则、扫描超时都会造成单次"没看到"。
如果第一次没看到就告警，运维一天会收到几十条"误报"，最后没人看告警——这比不告警更糟。

### 5. grace 期：用连续次数换信噪比

~~~text
扫描 1: 22,80,443        → 全部 active
扫描 2: 22,80            → 443 missing(miss=1)
扫描 3: 22,80            → 443 gone(miss=2)      ← grace=2
扫描 4: 22,80,443        → 443 revived           ← 如果它又回来了
~~~

`grace` 是**可配置的业务参数**，不是技术参数：

- 每天扫一次 + grace=2 → 给 24 小时缓冲；
- 每小时扫一次 + grace=2 → 只给 1 小时，可能仍然太敏感；
- 关键资产可以 grace=3，边缘资产 grace=1。

原则：**grace 的时长要大于"已知抖动的最长持续时间"。**

### 6. 趋势口径：一天多次扫描取哪次

如果一天扫了 6 次，把 6 次的端口数相加，会得到"扫得越勤、资产越多"的假趋势。
正确做法是**每天只取最后一次完整快照**：

~~~sql
SELECT date(started_at) AS d, MAX(id) AS last_scan
  FROM scans
 GROUP BY date(started_at)
~~~

`MAX(id)` 在这里等价于"当天最后一次"（自增 id 单调）。
用 `MAX(started_at)` 也可以，但同一秒内多次扫描会并列，id 更稳。

### 7. 为什么看板是静态 HTML

- 零依赖：不用起 Flask、不用 Node，`python3` 就能生成；
- 易分发：单个文件，扔到任意静态服务器 / GitHub Pages / 内网共享盘；
- 易审计：生成时间和数据源写在页面上，谁都能复核；
- 安全：没有服务端，就没有"看板本身被拿下的"风险。

代价是数据不是实时的。资产趋势按天看，本来也不需要秒级实时。

---

## 原理解释

### 1. SQLite 的 UPSERT 到底做了什么

本课用"先 SELECT 再 INSERT/UPDATE"的手写 UPSERT，原因是它能在同一事务里
顺便拿到 `asset_id`，并区分 `new` / `existing` 两种结果（审计需要）。

SQLite 也支持原生语法：

~~~sql
INSERT INTO assets(ip, port, proto, service, first_seen, last_seen)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(ip, port, proto) DO UPDATE SET
    last_seen = excluded.last_seen,
    service   = COALESCE(excluded.service, assets.service);
~~~

`excluded` 指"本次试图插入的那一行"。原生 UPSERT 少一次查询，但拿不到
"这次是新插入还是更新"的返回值，需要额外判断。

### 2. 事务边界决定了 100 倍的性能差

SQLite 默认每个 `INSERT` 自动提交，每次提交都要 fsync 日志。
在普通云盘上，一次 fsync 约 10~20ms——**单行入库的瓶颈根本不在 SQL，而在磁盘。**

~~~text
A. 自动提交：  INSERT → fsync → INSERT → fsync ...    ~13ms/行
B. 单事务：    BEGIN → INSERT × N → COMMIT → fsync     ~7µs/行
~~~

本课实测 A 比 B 慢 **1800 倍**（见实验 5）。
批量入库的铁律：**一个批次一个事务**，批次大小 1000~10000 行。

### 3. 索引为什么能加速，但不是什么都能加速

B-Tree 索引把 `(service)` 的值排好序，查询 `WHERE service='http'` 时直接定位，
不用逐行比较。代价：

- 写入时要维护索引（每次 INSERT 多几次页写）；
- 占磁盘；
- 低选择性的列（比如 `state` 只有 3 个值）收益有限。

本课实测 20000 行、500 次查询：无索引 532.7ms → 有索引 127.8ms（4.2x）。
注意 `UNIQUE(ip, port, proto)` 已经自动建了索引，所以按资产键查询本来就快；
真正需要额外索引的是 `service`、`state` 这类过滤列。

### 4. WAL 模式：扫描写入时看板还能查

默认 rollback journal 模式下，写事务持有排他锁，读会被阻塞。
WAL（Write-Ahead Logging）把修改先写日志，读事务看旧快照，写事务追加新页：

~~~text
读者 ──▶ WAL 快照（一致，不被阻塞）
写者 ──▶ WAL 追加 ──▶ 定期 checkpoint 回主库
~~~

资产库是"写多读少但要求随时可查"的典型场景，所以：

~~~python
conn.execute("PRAGMA journal_mode = WAL")
~~~

注意：WAL 会产生 `-wal` / `-shm` 文件，备份时要一起考虑（或用 `VACUUM INTO`）。

### 5. 事件表为什么不能只存"最终状态"

假设只存 `assets.state`，你只能回答"443 现在关了"。
但运维真正会问：

- 它是什么时候关的？
- 关了之后又开过吗？
- 这周一共新增了几个暴露面？

`events` 表是**只追加的审计流**：

~~~sql
CREATE TABLE events (
    id, scan_id, seen_at, event,
    ip, port, proto, old_value, new_value
);
~~~

有了它，日报就是一条 `GROUP BY date(seen_at), event` 的查询，
而不是"再跑一次扫描然后猜"。

---

## 图解

### 数据流

~~~text
scan-1.json ─┐
scan-2.json ─┼─▶ parse ─▶ run_scan() ─┬─▶ assets     （UPSERT 当前状态）
scan-3.json ─┘                        ├─▶ scan_assets（本次观测）
                                      ├─▶ events     （变更审计）
                                      └─▶ scans      （批次元数据）
                                                   │
                                                   ▼
                                     collect_daily() ─▶ ASCII 趋势
                                                   └─▶ HTML + SVG 看板
~~~

### 状态机

~~~text
                 首次观测
        (无) ───────────────▶ active
                               │  ▲
             本次未观测         │  │ 再次观测
                               ▼  │
                            missing
                               │  │
              连续 grace 次未观测│  │ 再次观测（revived）
                               ▼  │
                             gone ─┘
~~~

Mermaid 版本见 `diagrams/README.md`。

### 每天取哪次快照

~~~text
10-17  ├── 02:00 scan#41  6 端口
       ├── 08:00 scan#42  7 端口
       └── 14:00 scan#43  6 端口  ◀── 取这次（MAX(id)）
10-18  ├── 02:00 scan#44  6 端口
       └── 08:00 scan#45  5 端口  ◀── 取这次
~~~

---

## 实战代码案例

| 文件 | 作用 | 关键点 |
|---|---|---|
| `code/00-fixture.py` | 生成多天扫描 JSON | 离线、可复现，含新增/消失/版本变化 |
| `code/01-asset-store-basic.py` | 两层模型 + UPSERT | 幂等、`first_seen` 保留、NULL 不覆盖 |
| `code/02-incremental-snapshot.py` | 变更检测 | 自然键差集、grace、事件落库 |
| `code/03-trend-dashboard.py` | 趋势 + HTML | 每天最后一次快照、零依赖 SVG |
| `code/04-perf-benchmark.py` | 性能实测 | 事务、executemany、索引 |
| `code/05-ingest-pipeline.py` | 端到端编排 | 复用 02 当模块、子进程调 03 |

所有脚本都支持 `--self-test`，且自检**不依赖外部服务、不写仓库目录**。

---

## 实战实验手册

> 以下输出均为 2026-10-19 06:01~06:03（Asia/Shanghai）在本机真实执行所得，
> 不是示意。所有实验都在 `/tmp` 下进行，结束会清理。

### 实验 1：建立资产库并验证幂等

**目的**：验证同一份扫描重跑不会产生重复资产，且 `first_seen` 不被覆盖。

**环境**：Python 3.12.3，SQLite 3.45.1，无外部依赖。

**准备**：

~~~bash
cd days/day-189-asset-store-trends/code
rm -f /tmp/day189-demo.db*
~~~

**执行**：

~~~bash
python3 01-asset-store-basic.py --self-test
python3 01-asset-store-basic.py --db /tmp/day189-demo.db
~~~

**实际结果**：

~~~text
✅ 01 self-test 通过：UPSERT 幂等 / first_seen 保留 / NULL 不覆盖
库文件: /tmp/day189-demo.db
scan #1: {'new': 3, 'existing': 0, 'observed': 3}
scan #2: {'new': 1, 'existing': 3, 'observed': 4}

当前资产表：
ip            port  proto service state   first_seen
10.0.0.5        22  tcp   ssh     active  2026-10-18T22:01:07+00:00
10.0.0.5        80  tcp   http    active  2026-10-18T22:01:07+00:00
10.0.0.7       443  tcp   https   active  2026-10-18T22:01:07+00:00
10.0.0.9      6379  tcp   redis   active  2026-10-18T22:01:07+00:00

assets=4  scan_assets=7
~~~

**结论**：第二次扫描 3 个旧资产全部命中 `existing`，只新增 1 个；
`scan_assets` 有 7 行（3+4），说明观测流水完整保留，没有去重丢失历史。

**清理**：

~~~bash
rm -f /tmp/day189-demo.db /tmp/day189-demo.db-wal /tmp/day189-demo.db-shm
~~~

---

### 实验 2：端口抖动与确认下线

**目的**：验证 `missing` 不会立刻变成 `gone`，以及 `revived` 能被识别。

**准备**：

~~~bash
rm -f /tmp/day189-diff.db*
~~~

**执行**：

~~~bash
python3 02-incremental-snapshot.py --self-test
python3 02-incremental-snapshot.py --db /tmp/day189-diff.db
~~~

**实际结果**：

~~~text
✅ 02 self-test 通过：appeared / missing / gone / changed / revived 全部符合预期
[D1 全量] appeared 10.0.0.5:22, appeared 10.0.0.5:80, appeared 10.0.0.7:443
[D2 全量] appeared 10.0.0.9:8080
[D3 全量] missing 10.0.0.7:443, missing 10.0.0.9:8080
[D4 全量] gone 10.0.0.7:443

最终状态：
  10.0.0.5  :22    ssh     active  miss=0
  10.0.0.5  :80    http    active  miss=0
  10.0.0.7  :443   https   gone    miss=2
  10.0.0.9  :8080  http    active  miss=0

事件表（全部）：
  scan#1 appeared 10.0.0.5:22           - -> ssh
  scan#1 appeared 10.0.0.5:80           - -> http
  scan#1 appeared 10.0.0.7:443          - -> https
  scan#2 appeared 10.0.0.9:8080         - -> http
  scan#3 missing  10.0.0.7:443      https -> -
  scan#3 missing  10.0.0.9:8080      http -> -
  scan#4 gone     10.0.0.7:443      https -> -
~~~

**结论**：8080 在 D3 抖动消失，只记 `missing`，D4 回来后 `miss_count` 归零，
**没有产生任何下线告警**；443 连续两次消失才 `gone`。
如果把 grace 改成 1，D3 就会误报 443 下线。

**清理**：

~~~bash
rm -f /tmp/day189-diff.db /tmp/day189-diff.db-wal /tmp/day189-diff.db-shm
~~~

---

### 实验 3：30 天趋势与静态看板

**目的**：验证按天聚合口径，并产出可直接打开的单文件 HTML。

**准备**：

~~~bash
rm -f /tmp/day189-trend.db* /tmp/day189-dashboard.html
~~~

**执行**：

~~~bash
python3 03-trend-dashboard.py --db /tmp/day189-trend.db \
    --out /tmp/day189-dashboard.html --seed-days 30
~~~

**实际结果**：

~~~text
开放端口趋势  2026-09-20 → 2026-10-19
  ▁▁▂▂▃▃▃▃▃▃▄▄▅▅▅▅▆▆▆▆▆▆▇▇▇▇▇▇▇█
  min=0  max=12  latest=12

日期              端口    新增    下线    变更
2026-10-10       9     1     0     0
2026-10-11       8     0     1     0
2026-10-12      10     2     0     0
2026-10-13      11     1     0     1
2026-10-14      11     0     0     1
2026-10-15      11     1     1     0
2026-10-16      11     1     1     0
2026-10-17      11     0     0     1
2026-10-18      11     1     1     0
2026-10-19      12     1     0     0

看板已写入 /tmp/day189-dashboard.html（6489 bytes）
~~~

页面自检：

~~~bash
grep -c '<svg' /tmp/day189-dashboard.html
# 1
grep -o '<title>[^<]*' /tmp/day189-dashboard.html
# <title>资产趋势看板 · Day 189
~~~

**结论**：30 天数据从 0 增长到 12 个开放端口，中间有增有减，
sparkline 与表格口径一致；HTML 只有一个 SVG，无外部 JS/CSS 请求。

**清理**：

~~~bash
rm -f /tmp/day189-trend.db /tmp/day189-trend.db-wal /tmp/day189-trend.db-shm
rm -f /tmp/day189-dashboard.html
~~~

---

### 实验 4：端到端流水线（JSON → 库 → 看板）

**目的**：验证多天扫描结果能自动入库、产生正确事件并生成看板。

**准备**：

~~~bash
rm -rf /tmp/day189-scans
rm -f /tmp/day189-pipeline.db* /tmp/day189-pipeline.html
python3 00-fixture.py --out /tmp/day189-scans --days 5
~~~

**执行**：

~~~bash
python3 05-ingest-pipeline.py --scan-dir /tmp/day189-scans \
    --db /tmp/day189-pipeline.db --out /tmp/day189-pipeline.html
~~~

**实际结果**：

~~~text
写入 /tmp/day189-scans/scan-1.json（3 台主机）
写入 /tmp/day189-scans/scan-2.json（3 台主机）
写入 /tmp/day189-scans/scan-3.json（3 台主机）
写入 /tmp/day189-scans/scan-4.json（3 台主机）
写入 /tmp/day189-scans/scan-5.json（3 台主机）
共 5 份扫描结果 → /tmp/day189-scans

开放端口趋势  2026-10-15 → 2026-10-19
  ▁▁█▁▁
  min=5  max=6  latest=5

日期              端口    新增    下线    变更
2026-10-15       5     5     0     0
2026-10-16       5     0     0     0
2026-10-17       6     1     0     1
2026-10-18       5     0     0     0
2026-10-19       5     0     1     0

看板已写入 /tmp/day189-pipeline.html（5144 bytes）

入库结果：
  scan-1.json    observed=5   appeared=5
  scan-2.json    observed=5   无变化
  scan-3.json    observed=6   appeared=1, changed=1
  scan-4.json    observed=5   missing=1
  scan-5.json    observed=5   gone=1

数据库：/tmp/day189-pipeline.db
看板：  /tmp/day189-pipeline.html
~~~

**结论**：第 3 天新增 8080 并被识别为 `appeared`，同时 SSH banner 从
`OpenSSH_8.9` 变为 `9.6` 产生 `changed`；第 4 天 6379 首次消失为 `missing`，
第 5 天确认 `gone`。全链路无需人工干预。

**清理**：

~~~bash
rm -rf /tmp/day189-scans
rm -f /tmp/day189-pipeline.db /tmp/day189-pipeline.db-wal /tmp/day189-pipeline.db-shm
rm -f /tmp/day189-pipeline.html
~~~

---

### 实验 5：入库性能与索引实测

**目的**：量化"自动提交 vs 单事务"和"有索引 vs 无索引"的差距。

**环境**：同一台机器，单次运行，未取均值；B/C/D 5000 行，A 仅 100 行
（本机 fsync 约 13ms/行，全量跑 A 会超过 10 分钟）。

**执行**：

~~~bash
python3 04-perf-benchmark.py --self-test
python3 04-perf-benchmark.py
~~~

**实际结果**：

~~~text
✅ 04 self-test 通过：4 种写入路径行数一致，索引查询 7.3ms → 1.5ms
测试条件：B/C/D 5000 行，A 仅前 100 行 · 6 列 · SQLite 3.45.1 · 3.12.3 · 单次运行（未取均值）

写入方式                      行数    耗时(ms)       行/秒     相对B(每行)     µs/行
A autocommit 逐条          100    1299.4        77       0.00x    12994
B 单事务 逐条                5000      36.8    135695       1.00x        7
C 单事务 executemany       5000      29.6    169134       1.25x        6
D 单事务 UPSERT            5000      50.6     98842       0.73x       10

查询 500 次 service='http'（20000 行）：无索引 532.7ms / 有索引 127.8ms，加速 4.2x
~~~

**结论**：

- A 的单行成本约 **13ms**，B 约 **7µs**，相差约 **1800 倍**；
- `executemany` 比逐条 `execute` 快约 25%，差距不大但稳定；
- UPSERT 多一次 SELECT，单行成本从 7µs 升到 10µs（+43%），这是正确性的合理代价；
- 索引把等值查询从 532.7ms 降到 127.8ms（4.2x），但写入会变慢，按需建。

**清理**：脚本内部使用 `TemporaryDirectory`，退出即删除；无残留。

---

## 翻车实验：看板上的端口数全是 0

这是本次编写时**真实发生**的问题，值得单独记下来。

**现象**：跑完 5 天流水线，资产表和事件表都有数据，但看板显示：

~~~text
开放端口趋势  2026-10-15 → 2026-10-19
  ▄▄▄▄▄
  min=0  max=0  latest=0
~~~

**假设 1**：时区导致 `date(started_at)` 分组错位。
验证：直接查 `SELECT date(started_at), COUNT(*) FROM scans GROUP BY 1`，
5 天分组正确 → 排除。

**假设 2**：`scan_assets` 没写进去。
验证：

~~~sql
SELECT COUNT(*) FROM scan_assets;
-- 0
~~~

**根因**：02 的 `run_scan()` 只更新了 `assets` 和 `events`，**漏写了观测流水**。
03 的 `connect()` 里执行 `CREATE TABLE IF NOT EXISTS scan_assets`，
会自动建出一张**空表**——于是查询不报错，只是安静地返回 0。

这就是典型的**静默失败**：schema 自动创建掩盖了"上游没写"的事实。

**修复**：

1. 02 在每次 UPSERT 后写入 `scan_assets(scan_id, asset_id, seen_at)`；
2. 05 的 `--self-test` 增加断言：`scan_assets` 行数必须等于观测数；
3. 看板自检断言 `open_ports > 0`，而不是只检查文件存在。

**复测**：实验 4 输出端口 5→5→6→5→5，事件 appeared/missing/gone 全部正确。

**教训**：`CREATE TABLE IF NOT EXISTS` 很方便，但它会把"表不存在"这个
**上游缺陷**变成一个"表存在但为空"的**下游谜题**。跨模块协作时，
要么让下游对空数据显式报错，要么在流水线里加行数对账。

---

## 实测关键数字

| 指标 | 数值 | 条件 |
|---|---|---|
| 单行 autocommit 成本 | 12.99 ms/行 | 100 行，本机磁盘 |
| 单事务逐条 | 7 µs/行 | 5000 行 |
| 单事务 executemany | 6 µs/行 | 5000 行，1.25x |
| 单事务 UPSERT | 10 µs/行 | 5000 行 |
| 索引等值查询 | 532.7ms → 127.8ms | 20000 行 × 500 次，4.2x |
| 30 天看板生成 | 6489 bytes | 含 1 个内联 SVG |
| 5 天流水线 | 5144 bytes / 5 次扫描 | 事件数 5+0+2+1+1 |

---

## 思考题

1. **grace 应该按"次数"还是"时长"配置？**
   如果扫描器有时一天跑 1 次、有时一天跑 10 次，`grace=2` 的语义还稳定吗？
   你会怎么改数据模型？

2. **`scan_assets` 会无限增长。**
   每天 10 万条观测、保留 3 年就是 1 亿行。有哪些清理策略？
   清理后还能回答"三个月前这个端口开过吗"吗？

3. **如果扫描器漏扫了一整段网段**（比如 VPN 断了），
   下次扫描会把几百个资产标成 `missing`。怎样区分"资产真的消失"和"扫描失败"？
   需要什么额外信号？

4. **趋势图应该展示"开放端口数"还是"高风险端口数"？**
   两种口径会讲出什么不同的故事？如果只允许选一个放首页，你选哪个，为什么？

5. **事件表的 `changed` 目前比较 service 和 banner 字符串。**
   如果 banner 里带随机 token（每次连接都变），会发生什么？
   应该怎样做归一化？

---

## 收尾卫生

本次实验全部在 `/tmp` 下完成，编写结束后已确认：

~~~bash
ps aux | grep -E 'day189|perf-benchmark' | grep -v grep   # 无残留
ls /tmp/day189-* 2>/dev/null                              # 无残留文件
~~~

仓库内不产生数据库、HTML 或扫描 JSON；`out/` 与 `__pycache__/` 均已被 `.gitignore` 覆盖。
`04-perf-benchmark.py` 使用 `TemporaryDirectory`，异常退出也会自动清理。
