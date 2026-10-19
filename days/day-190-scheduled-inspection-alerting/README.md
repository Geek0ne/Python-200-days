# Day 190 — 定时巡检、变更告警与一键部署

> **阶段**：Phase 12 — 综合实战
> **项目**：企业资产监控系统 · 第 5/5 天
> **子主题**：调度窗口 · 重试幂等 · 告警降噪 · Compose 一键部署
> **代码**：6 个脚本 + 1 套 Compose 栈，全部带自检
> **实测环境**：Linux 7.0.0-34-generic / Python 3.12.3 / SQLite 3.45.1 / Docker 29.1.3 / Compose 2.40.3 / 2026-10-20 06:03–06:06 CST

---

## 今天在项目里的位置

`@text
Day 186  资产发现        → 有哪些域名/IP
Day 187  端口 + 指纹     → 哪些端口开着、跑什么服务
Day 188  Web 漏洞检测    → 开着的服务有没有洞
Day 189  入库 + 可视化   → 把"某一天"变成"可比较的历史"
Day 190  调度 + 告警     → 让它自己跑，出事自己喊人   ← 今天
`@

前四天造好了一台"能手动开的机器"。今天要解决的是**它不在你盯着的时候怎么办**：

1. 谁来每天按时按点跑？（调度）
2. 跑到一半崩了、重试了，数据会不会写两遍？（幂等）
3. 一晚上 500 条变化，怎么让人不把告警群静音？（降噪）
4. 换台机器，怎么三分钟内复现出同样一套？（一键部署）

---

## 概念速览

完整手册见 **concepts.md**，图解见 **diagrams/README.md**。

| 概念 | 一句话 | 为什么重要 |
|---|---|---|
| 固定延迟 | 上次完成 + interval | 漂移会累积，一天能漂 3 分钟 |
| 锚点网格 | anchor + n × interval | 不累积漂移，巡检的正确姿势 |
| 抖动 jitter | 把触发时刻在窗口内摊开 | 防止 8 个副本同一秒打爆目标 |
| grace 期 | 迟到多久之内还值得补跑 | 抑制停机恢复后的补跑风暴 |
| catch-up storm | 停机后把积压格子一口气补跑 | 一次恢复 = 24 次全量扫描 |
| 幂等键 idem_key | 业务语义的唯一标识 | 重试/重叠不产生第二次副作用 |
| 租约 lease | 领取时写明"我占到什么时候" | 崩溃后任务能被别人接手 |
| at-least-once | 至少执行一次 | 现实里唯一能保证的投递语义 |
| 恰好一次（效果） | 重放不会重复生效 | 靠唯一约束，不靠协议 |
| full jitter | 退避时间取 random(0, ceiling) | 防同步重试的 thundering herd |
| 永久错误 | 重试也不会好的错误 | 重试它只会放大故障 |
| 告警指纹 | 什么算"同一个问题" | 决定降噪会不会吞掉真警报 |
| 冷却窗口 | 同指纹多久内不重复打扰 | 压掉端口抖动噪声 |
| 分组 | 一个时间窗合成一条消息 | 500 条变 2 条 |
| 令牌桶 | 单位时间最多发几条 | 限流，但不许静默丢数据 |
| 静默窗口 | 维护期只计数不打扰 | 计划内变更不该叫人 |
| liveness / readiness | 活着 / 能干活 | 心跳文件能抓"活着但卡死" |
| Compose 健康依赖 | depends_on: service_healthy | 消掉启动竞态 |

---

## 概念解释

### 1. 为什么"跑完再睡 15 分钟"是错的

最直觉的写法：

```python
while True:
    scan()
    time.sleep(900)
```

它假设 `scan()` 不花时间。真实扫描 1~3 秒，于是每一天的起点都在往后蹭：

`@text
第 1 次   00:00:00 开始，00:00:02 结束
第 2 次   00:15:02 开始   ← 晚了 2 秒
第 3 次   00:30:04 开始   ← 晚了 4 秒
...
第 96 次  23:47:xx 开始   ← 一天累计晚了 187 秒
`@

这不是"误差"，是**系统性的积分**。一天 96 次、每次 2 秒，就是 192 秒。三个月后，你的"每天 0 点巡检"会跑到凌晨 3 点。

正确写法是锚点网格：**第 n 次的时刻由锚点算出来，和执行耗时无关**。

```python
slot = int((now - anchor) // interval)
fire_at = anchor + slot * interval + jitter_offset(slot)
```

实测对比（24 小时 / 96 格）：固定延迟漂移 **187.0s**，固定频率只受抖动影响 **-17.1s**。

### 2. 网格带来了两个新问题

**问题一：错过的格子补不补？**

进程 02:00 挂到 08:00，恢复时 24 个格子都过期了。

- 全补：24 次全量扫描瞬间打出去，目标侧看到的是"攻击"，自己这边看到的是超时雪崩
- 不补：监控出现 6 小时空白，且没人知道

正确做法是第三条路：**只补最近一个格子，其余记为 skipped 并落审计表**。判据是"这条巡检结果现在还有意义吗"——巡检看的是当前状态，6 小时前的结果已经过期。

**问题二：同时刻的实例会不会撞车？**

8 个副本用同一个锚点，没有抖动时窗口跨度 0 秒（实测），等于 8 份流量同时到。加 ±8% 抖动后跨度 85 秒（实测），总工作量不变，峰值降到 1/8。

注意：抖动必须**确定**。用 `random.random()` 的话，重启后同一个 slot 会算出不同偏移，幂等键对不上，同一格会执行两次。用 `hash(job_id + slot)` 做种子。

### 3. 调度器只管"触发"，不管"只生效一次"

cron 每 60 秒触发一次，而一次扫描要 75 秒 —— 这是真实项目里最常见的配置错误。后果不只是"跑两遍"，而是两个进程同时写同一个 SQLite：

`@text
Traceback (most recent call last):
  File "/tmp/d190-cron/job.py", line 6, in <module>
    conn.execute("BEGIN IMMEDIATE")
sqlite3.OperationalError: database is locked
`@

这是本次真机实验的实际输出（见实验 3）。SQLite 的默认 busy timeout 是 5 秒，第一个进程持锁 75 秒，第二个等 5 秒后放弃。

解法不是"把 timeout 调大"（那只是把冲突推迟），而是**入口互斥 + 任务幂等**：

- 进程级：`flock -n`，拿不到锁直接退出（不是排队）
- 任务级：每个时间格子一个幂等键，写库时 UNIQUE 挡住重复

### 4. 至少一次 + 幂等 = 恰好一次的效果

分布式系统里没有免费的 exactly-once。能保证的是：

1. 任务**至少**被投递一次（租约 + 失败重投）
2. 副作用**最多**生效一次（唯一约束）

两者相乘，才是业务意义上的"恰好一次"。

`@text
claim:   UPDATE jobs SET status='running', lease_until=now+30
                  WHERE idem_key=? AND (status='pending' OR lease 过期)
finish:  INSERT OR IGNORE INTO effects(idem_key)   ← 第二次插入被主键挡住
`@

实验 2 的数字：60 个任务、8 个 worker 并发、0.03 秒跑完，**effects=60/60**，没有一条重复副作用。

### 5. 崩溃恢复：只查 pending 会卡死任务

第一版 `claim()` 只认 `status='pending'`。worker 领了任务后崩溃，任务永远停在 `running` —— 既不会重试，也不会被接手，成了僵尸。

这是本次编写时**真实踩到**的坑（实验 4 有完整过程）。修复后的条件必须同时认领"到期的 pending"和"租约过期的 running"。

### 6. 告警降噪：一条漏斗，五道闸

`@text
500 条变化
  → 去重（同资产同规则，30 分钟内只发一次）    拦掉 444
  → 静默（维护窗口内只计数）
  → 分组（一个时间窗合成一条）
  → 限流（令牌桶，超出的进 overflow 队列）
  → 2 条消息，critical 20/20 全部送达
`@

关键不是"少发"，而是**该发的不能少**。实验 5 证明：指纹设计错一次，就能让 4 条 critical 凭空消失（实测 v1 丢失 4 条）。

### 7. 一键部署：把隐性状态写成文件

手工部署的隐性状态有四种：依赖、端口、残留容器、健康判断。Compose 把它们变成声明式：

```yaml
services:
  worker:
    depends_on:
      sink:
        condition: service_healthy   # 等真能接流量，不是等容器起来
```

再加一层 worker 自己的心跳 healthcheck：`now - mtime(heartbeat) < 20`。为什么不用 HTTP？因为"端口还在监听但循环卡死"是最常见的故障形态，HTTP 探活抓不到。

---

## 原理解释

### 8. 漂移的数学

固定延迟下，第 n 次的开始时刻：

`@text
T(n) = T(0) + n * interval + Σ(i=1..n) duration(i)
漂移(n) = Σ duration(i)   ← 单调递增，不可逆
`@

锚点网格下：

`@text
T(n) = anchor + n * interval + jitter(n)
漂移(n) = jitter(n)       ← 有界，不累积
`@

所以判断一个调度实现对不对，只需要问：**它的触发时刻函数里有没有"上次的完成时间"**。有，就会漂。

### 9. 为什么 grace 期不能省

设 grace=0，则停机 6 小时后所有格子都"过期"，一个都不补，监控出现 6 小时盲区；设 grace=∞，则补 24 次，恢复瞬间产生 24 倍负载。grace 的本质是**给"过期"一个可解释的边界**：300 秒内的结果还能代表"现在"，再早就只是历史。

实测：积压 24 格 → 补 1 次、跳过 23 次。

### 10. 为什么退避要加 full jitter

所有失败任务的下一次重试时间如果都按同一个指数曲线，它们会在同一秒集体回来。下游刚恢复就要再挨一次峰值，这叫 thundering herd。

full jitter 把等待摊成 `uniform(0, ceiling)`：期望不变，峰值削平。实测（attempt 1/3/20）：0.13s / 0.54s / 8.06s，封顶 60s。

### 11. 令牌桶为什么不许"直接丢弃"

丢弃最省事，但丢的是**证据**：出事时你无法回答"当时到底有多少条"。所以超限的条目进 overflow 队列，下一条消息里带"另有 N 条被合并"。实测：限流触发 4 次，5 条最终全部送达。

### 12. 为什么指纹里不能放"描述"

`@text
fingerprint = rule + asset          → 17 条消息，0 丢失   ✅
fingerprint = rule + asset + "第3次" → 125 条消息，0 丢失  ❌ 等于没降噪
fingerprint = rule                   → 2 条消息，丢 4 条   ❌ 更危险
`@

身份（哪个资产、哪条规则）稳定；描述（第几次、多少条、什么时间）每次都变。把描述放进指纹，冷却窗口永远命不中。

---

## 定义与使用方法（API 速查）

### 调度

| 函数 | 参数 | 返回 | 说明 |
|---|---|---|---|
| `grid_fire_time(anchor, slot, policy, rng)` | 锚点、格子号、策略、随机源 | datetime | 第 slot 格的触发时刻，抖动确定可复现 |
| `plan_catchup(anchor, last_slot, now, policy)` | 锚点、上次执行格、现在 | CatchUpPlan(fires, skipped) | grace 内最多补 max_catchup 个 |
| `burst_spread(policy, workers)` | 策略、实例数 | (无抖动跨度, 有抖动跨度, 样本) | 验证抖动是否摊平尖峰 |

### 任务队列

| 函数 | 关键行为 |
|---|---|
| `enqueue(conn, job, idem_key, payload)` | UNIQUE 冲突返回 False（去重） |
| `claim(conn, worker, now, lease_s)` | BEGIN IMMEDIATE + 条件 UPDATE，同时认领过期租约 |
| `finish_success(conn, key, kind, now)` | INSERT OR IGNORE effects，返回是否首次生效 |
| `finish_failure(..., permanent)` | permanent 或 attempts 超限 → dead；否则退避重投 |
| `backoff_delay(attempt, rng)` | min(60, 1×2^(n-1)) 上的 full jitter |

### 告警

| 方法 | 参数 | 作用 |
|---|---|---|
| `AlertPipeline.submit(alert, now)` | Alert、单调时钟 | 走完静默→去重→分组→限流 |
| `AlertPipeline.flush(now, force)` | 时间、是否强制 | 满窗或满批时投递 |
| `AlertPipeline.close(now)` | 时间 | 强制冲刷 + 排空 overflow |
| `Alert.fingerprint()` | — | `rule|asset`，不含 severity |
| `HttpSender.send(payload)` | dict | 3 次重试，指数退避，2s 超时 |

### 部署

| 命令 | 作用 |
|---|---|
| `bash deploy/deploy.sh up` | preflight → build → up --wait → 等第一条告警 → 打印 counts |
| `bash deploy/deploy.sh status` | 容器状态 + /health + /counts |
| `bash deploy/deploy.sh logs` | 最近 40 行日志 |
| `bash deploy/deploy.sh down` | down -v + 校验端口释放 + 校验容器为 0 |

---

## 图解

完整版见 **diagrams/README.md**，这里放两张最关键的。

### 调度网格与补跑

`@text
锚点网格：  |----|----|----|----|----|----|
            s0   s1   s2   s3   s4   s5
停机 6h 后：                                ▲ 现在
            积压 s1..s24
            无策略：24 次同时补跑（catch-up storm）
            有策略：只补 1 次，skipped=23 落审计
`@

### 告警漏斗

`@mermaid
flowchart TD
    E[Alert] --> S{静默窗口?}
    S -- 是 --> X[只计数]
    S -- 否 --> D{fingerprint 冷却中?}
    D -- 是且未升级 --> X
    D -- 否/升级 --> B[分组缓冲]
    B --> W{窗口满 或 批量满?}
    W -- 否 --> B
    W -- 是 --> T{令牌桶有令牌?}
    T -- 是 --> M[合并成一条消息]
    T -- 否 --> O[overflow 队列]
    O --> M
    M --> H[HTTP 投递 + 重试]
`@

---

## 实战代码案例

| 文件 | 作用 | 自检 |
|---|---|---|
| `code/00-fixture.py` | 68 台资产的两份快照 + 差异 | 6 项 |
| `code/01-scheduler-basic.py` | 固定延迟/固定频率/抖动/补跑推演 | 5 项 |
| `code/02-retry-idempotency.py` | 入队去重、租约、幂等写、退避 | 6 项 |
| `code/03-alert-dedup.py` | 五级漏斗 + 本地 HTTP 接收端 | 7 项 |
| `code/04-pitfall-dedup-key.py` | 三种指纹设计的真实结局 | 5 项 |
| `code/05-e2e-acceptance.py` | 差异 → 队列 → 告警 → 验收 | 6 项断言 |

全部只用标准库。跑法：

```bash
cd days/day-190-scheduled-inspection-alerting/code
python3 01-scheduler-basic.py
python3 02-retry-idempotency.py --demo
python3 03-alert-dedup.py --e2e
python3 04-pitfall-dedup-key.py
python3 05-e2e-acceptance.py --e2e
```


---

## 实战实验手册

> 以下所有「实际结果」都是 2026-10-20 06:03–06:06（CST）在本机跑出来的原始输出，
> 不是示意。环境：Python 3.12.3 / SQLite 3.45.1 / Docker 29.1.3 / Compose 2.40.3。

### 实验 1：固定延迟 vs 锚点网格（虚拟时钟，不 sleep）

**目的**：验证"漂移是耗时的积分"，并量出 24 小时的差距。

**准备**：

```bash
cd days/day-190-scheduled-inspection-alerting/code
```

**执行**：

```bash
python3 01-scheduler-basic.py --self-test
python3 01-scheduler-basic.py --simulate 24
python3 01-scheduler-basic.py --outage 6
```

**实际结果**：

```text
[PASS] 抖动不超界: max_offset=71.7s
[PASS] 抖动确定可复现: 同 slot 同种子结果一致
[PASS] 补跑被合并: fires=1 skipped=23
[PASS] 固定延迟漂移更大: delay=197s rate=-27s
[PASS] 抖动摊平尖峰: solid=0s spread=85s

全部通过（5 项）

推演窗口: 24h  格子: 900s  抖动: ±8%
------------------------------------------------------------------
策略                执行次数       末次漂移(秒)        末次时刻
fixed-delay         96         187.0    23:48:06
fixed-rate          96         -17.1    23:59:42
------------------------------------------------------------------
固定延迟的漂移 ≈ 每轮耗时累计： 187.0s ≈ 96 轮 × 约 2s
固定频率的漂移只来自抖动上界： -17.1s ≤ 72s
------------------------------------------------------------------
8 个实例同锚点触发：
  无抖动窗口跨度 = 0s（全部同时打出去）
  有抖动窗口跨度 = 85s，偏移样本(s) = [-25, -50, 21, -61, 5, -19, -63, 1]

停机 6h 后恢复（格子 900s，grace 300s）：
  积压格子数        : 24
  无策略会补跑      : 24 次（catch-up storm）
  有 grace+上限     : 补跑 1 次，跳过 23 次
```

**结论**：固定延迟一天漂 187 秒，且随天数线性增长；锚点网格的偏差只剩抖动上界（72s，且不累积）。停机 6 小时的补跑从 24 次压到 1 次。

**清理**：无副作用（纯内存推演）。

---

### 实验 2：重复入队、崩溃重领、并发去重（真实 SQLite）

**目的**：证明"至少一次投递 + 幂等写"能拼出恰好一次的效果。

**执行**：

```bash
python3 02-retry-idempotency.py --self-test
python3 02-retry-idempotency.py --demo
```

**实际结果**：

```text
[A] 同一 idem_key 被 4 次重复入队（cron 重叠的真实形态）
    enqueue 返回: [True, False, False, False]
    表里实际行数: 1  → 3 次被 UNIQUE 挡住

[B] 任务前两次连接重置，第三次成功
    t= 1000.0 scan:2026-10-20T10:00Z:assets -> pending(+0.64s)
    t= 1001.0 scan:2026-10-20T10:00Z:assets -> pending(+1.28s)
    t=1002.28 scan:2026-10-20T10:00Z:assets -> done(applied=True)
    最终: status=done attempts=3 effects=1

[C] 8 个 worker 并发处理 60 个任务，每个任务都会写一次副作用
    耗时 0.03s，处理结果按状态: [('done', 60, 60)]
    effects 行数 = 60 / 60 个任务

[D] 永久错误（400 参数错误）不应重试
    bad-target -> dead → status=dead attempts=1（attempts=1 即放弃）

[E] worker 领了任务但崩溃（不 finish），租约到期后被另一个 worker 接手
    第一次领取: crash-case（w-crashed）
    t+1s 再领: None（被租约挡住）
    t+3s 再领: crash-case → 崩溃任务可恢复
```

**结论**：4 次重复入队只落 1 行；60 个任务 8 线程并发只产生 60 条副作用；崩溃任务在租约过期后可被接手。

**清理**：脚本自建临时目录并在结束时删除（含 -wal/-shm）。

---

### 实验 3：500 条变化 → 2 条告警（真实 HTTP 接收端）

**目的**：量出降噪漏斗的压缩比，并验证"接收端 500 时消息不丢"。

**准备**：脚本自己在本机随机端口起 ThreadingHTTPServer，不需要外部服务。

**执行**：

```bash
python3 03-alert-dedup.py --self-test
python3 03-alert-dedup.py --e2e
python3 03-alert-dedup.py --e2e --flaky-receiver
```

**实际结果**（正常接收端）：

```text
接收端: 127.0.0.1:41599  (前 0 次故意 500)
输入事件           : 500
去重拦截           : 444
静默拦截           : 0
严重级升级放行     : 0
限流合并           : 0
发出的消息         : 2
HTTP 成功 POST     : 2  失败次数: 0
接收端收到         : 2  总请求: 2
耗时               : 26.3 ms
送达的 critical 条 : 20 / 20
送达总条数         : 56 (含合并的限流条目)
验收: PASS
```

**实际结果**（接收端前 2 次返回 500）：

```text
接收端: 127.0.0.1:33769  (前 2 次故意 500)
输入事件           : 500
去重拦截           : 444
发出的消息         : 2
HTTP 成功 POST     : 2  失败次数: 2
接收端收到         : 2  总请求: 4
耗时               : 181.2 ms
送达的 critical 条 : 20 / 20
验收: PASS
```

**结论**：500 → 2 条（压缩 250 倍），critical 20/20 全达；接收端 500 时发送端重试 2 次后成功，总请求 4、成功投递 2，消息没有丢也没有重复入库。

**清理**：接收端随进程退出自动关闭端口，无残留。

---

### 实验 4：去重键设计翻车（同一事件流，三种指纹）

**目的**：证明"降噪设计错"比"不降噪"更危险。

**执行**：

```bash
python3 04-pitfall-dedup-key.py
```

**实际结果**：

```text
事件流: 125 条，其中 critical 5 条
分布: {'info': 120, 'critical': 5}

方案                   消息数    丢失 critical  说明
------------------------------------------------------------------------------
v1 rule                2              4  指纹=规则，冷却 600s
v2 rule+asset+title        125              0  指纹=规则+资产+标题(含次数)
v3 rule+asset         17              0  指纹=规则+资产，高危放行
------------------------------------------------------------------------------

v1 的问题：消息少，但把 4 条高危一起吞了——比不降噪更危险。
v2 的问题：一条没丢，但发了 125 条消息，等于把收件人训练成盲点。
v3 的结果：17 条消息（12 个资产各 1 条 + 5 条高危），丢失 0。
```

**结论**：指纹必须放"身份"（rule + asset），不能只放规则（吞高危），也不能放描述（等于没降噪）。

**清理**：无副作用。

---

### 实验 5：端到端验收（差异 → 队列 → 告警 → 断言）

**目的**：把前四步串成一条流水线，用退出码而不是肉眼判定成败。

**执行**：

```bash
python3 05-e2e-acceptance.py --e2e
echo "exit=$?"
```

**实际结果**：

```text
接收端: 127.0.0.1:37763

验收清单
----------------------------------------------------------------------
[PASS] 任务数等于差异数（重复入队被去重）            jobs=7 entries=7
[PASS] 每个任务只产生一次副作用                 effects=7 dup=0
[PASS] 严重事件全部送达                     critical=2
[PASS] 消息条数受控                       messages=1
[PASS] 消息内无重复条目                     dup_items=0
[PASS] 送达总数与漏斗统计一致                  delivered=7 received=7
----------------------------------------------------------------------
漏斗: 收到 7 / 去重 0 / 消息 1 / 服务端收到 1
队列: jobs=7 effects=7
...
总体: ACCEPTED
exit=0
```

**结论**：7 条差异（2 critical + 3 warning + 2 info）重复入队两遍，最终仍是 7 个任务、7 条副作用、1 条消息、0 重复条目。

**清理**：临时目录随进程退出删除；接收端自动关闭。

---

### 实验 6：Docker Compose 一键部署（真容器）

**目的**：验证"换台机器，一条命令拉起整套巡检 + 告警接收端"。

**环境**：Docker 29.1.3 / Compose 2.40.3 / 基础镜像 python:3.12-slim（本机已有）。

**准备**：

```bash
cd days/day-190-scheduled-inspection-alerting/deploy
docker compose version
ss -ltn | grep 18090 || echo "18090 free"
```

**执行**：

```bash
bash deploy.sh up
bash deploy.sh status
```

**实际结果**（节选）：

```text
[deploy] preflight ok: docker + compose + 端口 18090 空闲
[deploy] 构建镜像...
 sink  Built
 worker  Built
[deploy] 启动...
 Container d190-sink-1  Started
 Container d190-sink-1  Healthy
 Container d190-worker-1  Started
 Container d190-worker-1  Healthy
[deploy] 已收到 1 条告警
NAME            STATUS
d190-sink-1     Up 25 seconds (healthy)
d190-worker-1   Up 19 seconds (healthy)

[deploy] counts: {"alerts": 1, "items": 1, "duplicates": 0, "invalid": 0, "last_at": "2026-10-19T22:03:52", "distinct": 1}
[deploy] 验收通过：sink 健康 + worker 心跳 + 告警落库
```

跑约 80 秒后再看（端口扫描每 5 秒一轮，模拟目标每 3 轮翻转一次状态）：

```text
$ curl -s http://127.0.0.1:18090/counts
{"alerts": 5, "items": 5, "duplicates": 3, "invalid": 0, "last_at": "2026-10-19T22:04:52", "distinct": 2}

$ docker compose logs --tail 5 worker
worker-1  | [worker] slot=3 投递 1 条变更
worker-1  | [worker] slot=6 投递 1 条变更
worker-1  | [worker] slot=9 投递 1 条变更
worker-1  | [worker] slot=12 投递 1 条变更
worker-1  | [worker] slot=15 投递 1 条变更

$ docker exec d190-sink-1 wc -l /data/sink/alerts.jsonl
5 /data/sink/alerts.jsonl

$ docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}' d190-sink-1 d190-worker-1
d190-sink-1 23.06% 14.09MiB / 15.59GiB
d190-worker-1 0.22% 14.35MiB / 15.59GiB
```

**结论**：从零到"收到告警"约 22 秒；两个容器都通过 healthcheck；duplicates=3 是真实缺陷的证据——worker 每轮直接投递，没有跨轮去重，这正是练习 4 要补的洞。

**清理**（单独执行并验证）：

```bash
bash deploy.sh down
```

```text
[deploy] 停止并删除容器/卷...
 Container d190-sink-1  Stopped
 Container d190-sink-1  Removed
 Volume d190_d190-data  Removed
[deploy] 已清理：容器 0、卷已删、端口 18090 已释放
```

复核：docker ps -a 无 d190 容器，ss -ltn 无 18090 监听。

---

## 翻车实验

### 翻车 1：只查 pending 的 claim，让崩溃任务永远卡死

**现象**：实验 [E] 第一次跑出来时，t+3s 那一行本应重领成功，实际返回 None；而脚本的提示文字仍写着"崩溃任务可恢复"，差点让我误判为通过。

**假设**：租约时间算错，或者用了墙上时钟导致比较失败。

**验证**：查库：

```sql
SELECT idem_key, status, attempts, lease_until FROM jobs WHERE idem_key='crash-case';
-- running | 1 | 5002.0   ← 租约确实过期了，但 claim 根本没看 running
```

**真实根因**：claim() 的 WHERE 只有 status='pending'。租约过期只改变了状态的含义，没有改变查询条件——租约机制形同虚设。

**修复**：

```sql
WHERE (status='pending' AND visible_at<=?)
   OR (status='running' AND lease_until IS NOT NULL AND lease_until<=?)
```

条件 UPDATE 也要带同样的 WHERE，否则并发下两个 worker 都能改到行。

**复测**：t+1s 仍是 None，t+3s 返回 crash-case，attempts 从 1 变 2。实验 2 的 [E] 输出即为修复后结果。

---

### 翻车 2：cron 每 60 秒触发，单次跑 75 秒 → database is locked

**现象**（真实 crontab，每分钟触发，脚本内 sleep 75 秒模拟全量扫描）：

```text
06:03:01 START pid=2353894
Traceback (most recent call last):
  File "/tmp/d190-cron/job.py", line 6, in <module>
    conn.execute("BEGIN IMMEDIATE")
sqlite3.OperationalError: database is locked
06:04:16 DONE  pid=2353894
```

**假设**：SQLite 的 busy timeout 太短，调大就好。

**验证**：把 timeout 从 5s 调大到 30s，第二个进程仍然失败（只是晚 30 秒失败）；把第一个进程的持锁时间从 75s 降到 10s，则不再冲突。说明根因不是 timeout 值，而是两个进程本来就该互斥。

**真实根因**：cron 不做单实例保护。每 60 秒起一个新进程，上一轮还在跑就并发执行。第二个进程的 BEGIN IMMEDIATE 等锁 5 秒后放弃，这一轮巡检直接丢失。

**修复**：入口加 flock -n，拿不到锁立即退出（不是排队，排队只会堆积）：

```bash
exec 9>/tmp/d190-cron/run.lock
if ! flock -n 9; then
  echo "$(date '+%H:%M:%S') SKIP 上一轮仍在运行（flock 未拿到锁）"
  exit 0
fi
exec /usr/bin/python3 job.py
```

**复测**（真实输出）：

```text
06:05:01 START pid=2355469
06:06:01 SKIP 上一轮仍在运行（flock 未拿到锁）
06:06:16 DONE  pid=2355469
```

**清理**：实验结束后用 crontab -l 过滤掉实验行再写回，原有条目（每天 5:00 的更新任务）保留未动，复核输出只剩原来那一行。

---

### 翻车 3（小）：importlib 加载带 dataclass 的脚本报 AttributeError

**现象**：

```text
AttributeError: 'NoneType' object has no attribute '__dict__'
```

**根因**：spec.loader.exec_module(mod) 之前没有把模块注册进 sys.modules，dataclasses 反查 cls.__module__ 时拿到 None。

**修复**：先 sys.modules[name] = mod，再 exec_module。

**教训**：这类错误只在"用文件路径动态导入"时出现，正常 import 不会。写工具脚本时容易忽略。

---

## 收尾卫生

| 项目 | 处理 | 复核 |
|---|---|---|
| 容器 | deploy.sh down -v | docker ps -a 过滤 d190 无输出 |
| 数据卷 | 随 down 删除 | docker volume ls 无 d190 |
| 端口 18090 | 容器删除后释放 | ss -ltn 无 18090 |
| crontab | 删除实验行 | crontab -l 只剩原有更新任务 |
| 临时目录 | /tmp/d190-cron、/tmp/d190-fix 删除 | ls /tmp 无 d190 |
| 镜像 | d190-alert-sink:1.0 保留（可复用，不占端口） | docker images 可见 177MB |

---

## 思考题

1. 如果巡检间隔 5 分钟、单次耗时 4 分 50 秒，你会选固定延迟还是网格？grace 设多少？为什么？
2. 幂等键用 scan:{date}:{target} 时，同一天手动重扫会被去重挡住。这是 bug 还是 feature？若业务要求"手动重扫必须生效"，键该怎么改？
3. 令牌桶容量 5、补充速率 2/s，而 critical 每秒来 10 条。设计一个策略，保证 critical 不被限流，同时 info 仍被合并。
4. depends_on: service_healthy 能消掉启动竞态，但消不掉"运行中下游挂掉"。worker 的待发队列（pending 表）应该多久重试一次？重试到什么时候放弃？
5. 如果让你把本课的 SQLite 换成 PostgreSQL，哪些设计可以原样保留？哪些必须重写（提示：BEGIN IMMEDIATE、INSERT OR IGNORE、busy_timeout）？

---

## 下一步

Day 191 起进入综合项目 II（AI 赋能反爬数据平台）。今天这套"调度 + 幂等 + 降噪 + 一键部署"的骨架会直接复用：爬虫的定时抓取、代理池轮换的去重、验证码失败的重试，本质上是同一组问题。
