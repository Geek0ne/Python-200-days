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
