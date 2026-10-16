# Day 184 图解 —— 日志管道与采集状态机

> 全部用 Mermaid / ASCII，**不生成图片文件**：这样它们能跟代码一起 review，
> 也能在 GitHub、终端（配合 mermaid-cli）里直接看。

---

## 图 1：日志管道全景（谁把日志搬到哪去了）

```mermaid
flowchart TB
    subgraph 产生端["① 产生：应用"]
        A1["api 服务<br/>JsonLineFormatter"] --> A2["/var/log/api/app.log<br/>JSON Lines"]
    end

    subgraph 采集["② 采集：采集器（每台机器一个）"]
        B1["FollowReader<br/>(inode, offset, buffer)"]
        B2{"攒够 50 条<br/>或 1 秒?"}
        B3["Sender<br/>POST NDJSON + 3 次退避"]
        B4["spill 文件<br/>（投递失败降级）"]
        B1 --> B2 --> B3
        B3 -.失败.-> B4
    end

    subgraph 存储["③ 存储：接收端 + SQLite"]
        C1["ThreadingHTTPServer<br/>POST /ingest"]
        C2["LogStore<br/>WAL + busy_timeout=5000"]
        C3[("logs.db<br/>+ 3 个索引")]
        C1 --> C2 --> C3
    end

    subgraph 查询["④ 查询与可视化"]
        D1["GROUP BY 分桶"]
        D2["ASCII 看板（值班）"]
        D3["单文件 HTML（存档）"]
        D4["告警规则<br/>ERROR 占比"]
        D1 --> D2
        D1 --> D3
        D1 --> D4
    end

    A2 -->|"rename 轮转后<br/>必须重开文件"| B1
    B3 --> C1
    C3 --> D1
```

**读图要点**：箭头上的小字才是真正的知识点。管道的每一跳都有自己的失败模式，
"日志丢了"从来不是单一原因。

---

## 图 2：一次请求的日志生命周期（时序）

```mermaid
sequenceDiagram
    participant App as api 服务
    participant File as app.log
    participant Col as 采集器
    participant Srv as 接收端
    participant DB as SQLite(WAL)

    App->>File: write(JSON + "\n")  ← 原子性只保证到 buffer
    File-->>Col: 增量读（offset → 新 offset）
    Col->>Col: buffer 按 "\n" 切；尾巴留着
    Col->>Srv: POST /ingest（一批 50 条或 1 秒）
    Srv->>DB: BEGIN IMMEDIATE + executemany（批提交）
    DB-->>Srv: COMMIT
    Srv-->>Col: {"accepted": 50}
    Note over Col,DB: 任一步失败 → 重试 3 次 → 落 spill 文件
    Col->>Srv: GET /stats?window=3600
    Srv-->>Col: {"by_level":{"INFO":49,"ERROR":1}}
```

---

## 图 3：采集器状态机（为什么必须记 inode）

```text
                  ┌──────────────────────────────────────────┐
                  │  state = (inode, offset, buffer, mtime)  │
                  └──────────────────────────────────────────┘
                                     │ 每 0.2s poll 一次
                                     ▼
                      ┌──────────────────────────────┐
                      │ os.stat(path) 成功?           │
                      └──────────────────────────────┘
                        │ 否                        │ 是
                        ▼                           ▼
                  等待文件出现            ┌───────────────────────────┐
                  （不报错）              │ st_ino != state.inode ?    │
                                          └───────────────────────────┘
                                             │ 是（发生了 rename 轮转）
                                             ▼
                                   把旧 fd 读到 EOF → 关闭
                                   → open(path) 重新取 inode
                                   → rotations += 1
                                             │ 否
                                             ▼
                             ┌──────────────────────────────────────┐
                             │ size < offset 或 (size<=offset 且       │
                             │ mtime 变了) ?  → 截断                  │
                             └──────────────────────────────────────┘
                                             │ 是
                                             ▼
                                    seek(0); offset = 0
                                    truncations += 1
                                             │ 否
                                             ▼
                                  chunk = fd.read()
                                  buffer += chunk
                                  *完整行, buffer = buffer.split("\n")
                                  → 完整行交给 Sender
```

**反例（naive 模式）**：删掉图中的两个判断框，只保留 `fd.read()`。
文件被 rename 后，`fd` 仍指向旧 inode，读不到任何新内容，
而且**不报错** —— 这是日志系统里最危险的一种失败（静默丢数据）。

---

## 图 4：SQLite 两种 journal 模式的锁时间线

```text
默认 rollback journal（DELETE）—— 写会挡住读
时间轴 →
写者 A:  [BEGIN IMMEDIATE]──写──[RESERVED]──────────[EXCLUSIVE 落盘]──[COMMIT]
读者 R:  ──────────读 OK──────────┐                    ↑ 读被挡
写者 B:                            └─[尝试写]→ SQLITE_BUSY（立刻失败！）

WAL —— 一写多读并行，写者之间排队
写者 A:  [BEGIN IMMEDIATE]──写──[追加 -wal]──────[COMMIT]
读者 R:  ──────────始终读旧快照，不阻塞─────────→ 看见新数据
写者 B:                            └─[尝试写]→ busy_timeout 内轮询等待 → 成功后写
```

**结论**：WAL 解决"读写互斥"，但**不解决"多写者互斥"**。
多写者场景必须再加上 `busy_timeout`（让 B 等而 A 而不是立刻报错）。
04 号示例实测：`timeout=0` 时 B 在 0.000s 就失败；加 WAL + `busy_timeout=5000` 后
B 等待 0.738s 拿到锁并成功。

---

## 图 5：轮转（rename）—— 正确采集器 vs naive 采集器

```text
时刻 T0  app.log ──┐
                   └─ inode 8823645  ← 两个采集器的 fd 都指向它
        正确采集器: state.inode = 8823645
        naive 采集器: fd → inode 8823645

时刻 T1  mv app.log app.log.1        （inode 8823645 还在，只是换了名字）
        应用 open("app.log", O_CREAT) → 新 inode 8823700，开始往里写

        正确采集器: os.stat("app.log").st_ino = 8823700 ≠ 8823645
                    → 重开 → 收到新行 ✅   rotations_detected: 1
        naive 采集器: fd 仍是 8823645（旧文件，无人再写）
                    → 永远 EOF，静默什么都不发 ❌  rotations_detected: 0
```

这就是 `--naive` 开关存在的意义：**它把"看起来能跑"和"真的不丢"的差别
变成一次可复现的对照实验**，而不是一句口头警告。
