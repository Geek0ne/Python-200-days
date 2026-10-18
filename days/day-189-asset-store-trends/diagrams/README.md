# Day 189 图解 — 资产入库与趋势

## 1. 端到端数据流

~~~text
┌──────────────┐   parse    ┌──────────────────────────────────────┐
│ scan-*.json  │───────────▶│ run_scan(observations)               │
└──────────────┘            │                                      │
                            │  1. INSERT scans（批次元数据）       │
                            │  2. UPSERT assets（当前状态）        │
                            │  3. INSERT scan_assets（观测流水）   │
                            │  4. 差集 → events（变更审计）        │
                            └───────────────┬──────────────────────┘
                                            │
              ┌─────────────────────────────┼─────────────────────────┐
              ▼                             ▼                         ▼
       ┌────────────┐               ┌──────────────┐          ┌────────────┐
       │ assets     │               │ scan_assets  │          │ events     │
       │ 当前真相   │               │ 历史观测     │          │ 变更审计   │
       └─────┬──────┘               └──────┬───────┘          └─────┬──────┘
             │                             │                        │
             └──────────────┬──────────────┴────────────┬───────────┘
                            ▼                           ▼
                   collect_daily()                 recent events
                            │                           │
                            ▼                           ▼
                   ASCII 趋势 + SVG 看板（单文件 HTML）
~~~

## 2. 资产状态机

~~~mermaid
stateDiagram-v2
    [*] --> active: appeared（首次观测）
    active --> missing: 本次未观测\nmiss_count += 1
    missing --> active: 再次观测\nmiss_count = 0
    missing --> gone: miss_count >= grace
    gone --> active: revived（重新出现）
    gone --> [*]: 归档（可选）
~~~

## 3. ER 图

~~~mermaid
erDiagram
    SCANS ||--o{ SCAN_ASSETS : contains
    ASSETS ||--o{ SCAN_ASSETS : observed_in
    SCANS ||--o{ EVENTS : produces

    SCANS {
        int id PK
        text started_at
        text source
        text note
    }
    ASSETS {
        int id PK
        text ip
        int port
        text proto
        text service
        text banner
        text first_seen
        text last_seen
        text state
        int miss_count
    }
    SCAN_ASSETS {
        int scan_id FK
        int asset_id FK
        text seen_at
    }
    EVENTS {
        int id PK
        int scan_id FK
        text seen_at
        text event
        text ip
        int port
        text proto
        text old_value
        text new_value
    }
~~~

## 4. 时序：一次扫描写入

~~~mermaid
sequenceDiagram
    participant S as Scanner
    participant P as Pipeline
    participant DB as SQLite
    participant R as Renderer

    S->>P: scan JSON（全量观测）
    P->>DB: BEGIN
    P->>DB: INSERT scans → scan_id
    loop 每个观测
        P->>DB: SELECT asset by (ip,port,proto)
        alt 不存在
            P->>DB: INSERT assets
            P->>DB: INSERT events(appeared)
        else 已存在
            P->>DB: UPDATE assets(last_seen, service...)
            opt service/banner 变化
                P->>DB: INSERT events(changed)
            end
        end
        P->>DB: INSERT scan_assets(scan_id, asset_id)
    end
    loop 库中未观测的资产
        P->>DB: UPDATE miss_count
        alt miss_count >= grace
            P->>DB: UPDATE state='gone'
            P->>DB: INSERT events(gone)
        else
            P->>DB: UPDATE state='missing'
            P->>DB: INSERT events(missing)
        end
    end
    P->>DB: COMMIT
    P->>R: 生成看板
    R->>DB: 按天聚合
    R-->>P: dashboard.html
~~~

## 5. 每天取哪次快照

~~~text
10-17  ├── 02:00 scan#41  6 端口
       ├── 08:00 scan#42  7 端口
       └── 14:00 scan#43  6 端口  ◀── MAX(id) = 43，取这次
10-18  ├── 02:00 scan#44  6 端口
       └── 08:00 scan#45  5 端口  ◀── 取这次

若把一天所有扫描相加：6+7+6 = 19，趋势会随扫描频率虚高。
~~~

## 6. 性能对比（本机实测，单次运行）

~~~text
单行成本（对数刻度，µs）

A autocommit    ████████████████████████████████████████  12994
B 单事务逐条    ▏                                              7
C executemany   ▏                                              6
D UPSERT        ▎                                             10

查询 500 次（20000 行）
无索引          ██████████████████████  532.7 ms
有索引          █████                  127.8 ms   （4.2x）
~~~
