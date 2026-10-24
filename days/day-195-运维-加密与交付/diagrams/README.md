# Day 195 图解 — 重试、加密、交付

> Mermaid 源码可直接粘到支持 Mermaid 的 Markdown 渲染器；ASCII 图用于终端阅读。

## 1. 重试状态机

```mermaid
stateDiagram-v2
    [*] --> Call
    Call --> Success: 2xx
    Call --> Classify: 异常 / 非 2xx
    Classify --> FailFast: 401/403/4xx/未知
    Classify --> Wait: 5xx/超时/429
    Wait --> Call: attempt < max 且未超预算
    Wait --> GiveUp: 次数或预算耗尽
    Success --> [*]
    FailFast --> [*]
    GiveUp --> [*]
```

ASCII 时间线（实测 01 脚本，base=0.1s，factor=2，full jitter）：

```text
attempt 1 ──503──▶ sleep 0.079s
attempt 2 ──503──▶ sleep 0.200s   (Retry-After 下限)
attempt 3 ──200──▶ done            总耗时 0.313s
```

## 2. 抖动如何削平重试洪峰

```text
无抖动（500 客户端）               full jitter
│██████████████████│ 500           │█│█│█│█│█│█│█│█│ 峰值 5
└── 同一 10ms 桶 ──┘               └── 分散到整个窗口 ──┘
```

## 3. 信封密文布局

```text
 v1. | kid_len | kid | nonce(12B) | ciphertext + tag(16B)
 ─┬─   ─┬──     ─┬─   ───┬─────     ─────────┬─────────
  │     │        │        │                   │
  │     │        │        └─ 随机，绝不复用    └─ AES-256-GCM 输出
  │     │        └─ 密钥 ID，支持轮换
  │     └─ 1 字节长度
  └─ 版本前缀（base64url 整体编码）

AAD（例如 record_id）不进密文，但参与认证：
密文从 row-42 复制到 row-43 → tag 校验失败 → InvalidTag
```

## 4. 请求签名与校验顺序

```mermaid
sequenceDiagram
    participant C as Client
    participant S as Server
    C->>C: canonical = METHOD/PATH/TS/NONCE/SHA256(body)
    C->>C: sig = HMAC-SHA256(secret, canonical)
    C->>S: headers + body
    S->>S: 1. |now-ts| <= 300 ?
    S->>S: 2. compare_digest(sig, expected)
    S->>S: 3. nonce 未用过 ?
    alt 全部通过
        S-->>C: 200
    else 时间/签名/nonce 失败
        S-->>C: 401 / 409
    end
```

## 5. 部署与自动回滚

```mermaid
flowchart TD
    A[记录 PREV_REF] --> B[构建新镜像]
    B --> C[停旧容器 / 起新容器]
    C --> D{HEALTHCHECK 通过?}
    D -- 是 --> E[跑 smoke_test]
    D -- 否 --> R[回滚 PREV_REF]
    E -- 通过 --> F[部署成功]
    E -- 失败 --> R
    R --> G{旧版本健康?}
    G -- 是 --> H[退出码 1，人工介入]
    G -- 否 --> I[退出码 2，紧急告警]
```

## 6. liveness vs readiness

```text
            ┌──────────────┐
  probe ───▶│  /healthz    │ 进程活着？ → 失败：重启容器
            └──────────────┘
            ┌──────────────┐
  probe ───▶│  /readyz     │ 能写库 + 有密钥？ → 失败：摘掉流量
            └──────────────┘

合并成一个的后果：数据库抖 10 秒 → 所有副本被重启 → 雪崩
```

## 7. 告警收敛时间轴

```text
t=0s      error █  → 发第 1 条（suppressed=0）
t=0.6s    error █  → 抑制
...
t=59.4s   error █  → 抑制（共 99 条）
t=60s     error █  → 发第 2 条（suppressed=99）
```