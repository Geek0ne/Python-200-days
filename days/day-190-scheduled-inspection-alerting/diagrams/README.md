# Day 190 图解：调度、幂等、告警漏斗与部署拓扑

> 所有图都是文本（Mermaid / ASCII），可直接在 GitHub 渲染，不需要图片文件。

---

## 1. 三种调度模型的时间轴

`@text
时间 ──────────────────────────────────────────────────────►

固定延迟（跑完 + interval）：
[任务1 2s][等15m][任务2 2s][等15m][任务3 2s]...
           ▲ 每次起点都晚 2s，一天累积 187s

锚点网格（anchor + n*interval）：
 |---------|---------|---------|---------|---------|
 ▲         ▲         ▲         ▲         ▲         ▲
 s0        s1        s2        s3        s4        s5     ← 与耗时无关
`@

`@mermaid
flowchart LR
    A[anchor 锚点] --> B[slot n = floor&#40;now-anchor / interval&#41;]
    B --> C{fire_at 已到?}
    C -- 否 --> D[睡到 fire_at]
    C -- 是 --> E{slot 已执行?}
    E -- 是 --> D
    E -- 否 --> F[写入 slot 幂等键]
    F --> G[执行巡检]
    G --> H[记录结果/告警]
    H --> D
`@

---

## 2. 停机恢复：catch-up storm 与 grace

`@text
正常：   s1    s2    s3    s4    s5    s6
        [✓]   [✓]   [✓]   [✓]   [✓]   [✓]

宕机 6h：
        s1    s2    s3 ........................ s24   ← 24 个格子没跑
                                                    ▲ 恢复
无策略：  ████████████████████████████████████████  24 次同时补跑 → 打爆目标
有策略：                                          [✓]  只补 1 次
         跳过 23 次，写 audit 表：skipped=23
`@

判定公式：

`@text
可补跑条件 = (now - fire_at) <= grace_s
实际补跑数 = min(count(可补跑), max_catchup)
`@

---

## 3. 任务状态机（租约 + 重试）

`@mermaid
stateDiagram-v2
    [*] --> pending: enqueue（idem_key 唯一）
    pending --> running: claim（BEGIN IMMEDIATE）
    running --> done: 成功 + effects 幂等写
    running --> pending: 临时错误（退避 + jitter）
    running --> dead: 永久错误 / 超过最大次数
    running --> pending: 租约过期（崩溃恢复）
    done --> [*]
    dead --> [*]
`@

`@text
         claim                     finish
pending ───────► running ─────────────────► done
   ▲               │
   │  退避到期      │ 崩溃（不 finish）
   └───────────────┘
                   │ lease_until < now
                   ▼
              可被其他 worker 重新 claim
`@

---

## 4. 告警五级漏斗

`@text
500 events
   │
   ├─① 归一化 ─────────────── 统一字段/词表
   │
   ├─② 去重 fingerprint ───── 444 条被拦（同资产同规则 30 分钟内重复）
   │
   ├─③ 静默 ───────────────── 维护窗口内只计数
   │
   ├─④ 分组 ───────────────── 一个时间窗 = 一条消息
   │
   └─⑤ 限流令牌桶 ─────────── 超出的进 overflow，下一条合并
   │
   ▼
 2 条消息（critical 20/20 全达）
`@

`@mermaid
flowchart TD
    E[Alert] --> S{静默窗口?}
    S -- 是 --> X[计数丢弃]
    S -- 否 --> D{fingerprint 在冷却中?}
    D -- 是且无升级 --> X
    D -- 否/升级 --> B[进分组缓冲]
    B --> W{窗口满 或 批量满?}
    W -- 否 --> B
    W -- 是 --> T{令牌桶有令牌?}
    T -- 是 --> M[合并成一条消息]
    T -- 否 --> O[overflow 队列]
    O --> M
    M --> H[HTTP 投递 + 重试]
`@

---

## 5. 指纹设计三种结局

`@text
v1  fingerprint = rule
    info(10.0.0.1) ─┐
    info(10.0.0.2) ─┼─► 同一个键 ─► 只发 1 条 ─► critical 被吞（丢 4 条）

v2  fingerprint = rule + asset + title("第 N 次")
    每次抖动都是新键 ─► 125 条消息 ─► 收件人静音

v3  fingerprint = rule + asset，severity 升级放行
    12 个资产 = 12 条 + 5 条 critical = 17 条 ─► 零丢失、可读
`@

---

## 6. 部署拓扑

`@text
             host: 127.0.0.1:18090
                     │
        ┌────────────▼─────────────┐
        │  d190-sink-1             │  GET  /health, /counts
        │  python sink.py          │  POST /alert  → /data/sink/alerts.jsonl
        │  healthcheck: HTTP 200   │
        └────────────▲─────────────┘
                     │ http://sink:8080/alert（compose 内部 DNS）
        ┌────────────┴─────────────┐
        │  d190-worker-1           │  TARGETS=sink:8080,sink:8081,127.0.0.1:1
        │  python worker.py        │  interval=5s, jitter=15%
        │  healthcheck: 心跳文件    │  SQLite: /data/worker/state.db
        └──────────────────────────┘
                     │
              volume d190-data（sink 与 worker 各自子目录）
`@

---

## 7. 一键部署 / 撤收时序

`@mermaid
sequenceDiagram
    participant U as deploy.sh
    participant D as docker compose
    participant S as sink
    participant W as worker

    U->>U: preflight（docker / compose / 端口 18090）
    U->>D: build
    U->>D: up -d --wait
    D->>S: start
    S-->>D: healthy（/health 200）
    D->>W: start（depends_on: service_healthy）
    W->>S: POST /alert（首次变更）
    S-->>W: 200 {"ok":true}
    U->>S: GET /counts
    S-->>U: {"alerts":1}
    U->>U: 验收通过
    U->>D: down -v
    D->>S: stop + remove
    D->>W: stop + remove
    U->>U: 校验端口已释放、容器为 0
`@

---

## 8. 真实故障：cron 每分钟触发 + 单次跑 75 秒

`@text
06:03:01  cron 触发 #1  ── BEGIN IMMEDIATE ── 持有写锁 ──────────────┐
06:04:01  cron 触发 #2  ── BEGIN IMMEDIATE ── 等锁 5s ── ✗ locked   │
06:04:16                                              #1 COMMIT ─────┘

修复：flock -n 包住整个脚本
06:05:01  cron 触发 #1  ── flock 拿到锁 ── 执行 ── DONE
06:06:01  cron 触发 #2  ── flock -n 失败 ── SKIP（立即退出，不排队）
`@
