# Day 195 — 运维、加密与交付

> **阶段**：Phase 12 — 综合实战
> **项目**：AI 赋能反爬数据平台 · 第 5/5 天
> **子主题**：调度与重试 · 日志与告警 · 数据加密 · API 鉴权 · Docker 多阶段构建 · 一键部署与回滚
> **代码**：2 个共享库 + 4 个教学脚本 + 1 个可部署服务 + 部署/验收/CI 脚本
> **实测环境**：Linux 7.0.0-34-generic / Python 3.12.3 / Docker 29.1.3 / Ubuntu 24.04.4 / 4 vCPU / 15.59 GiB / 2026-10-25 06:00–06:10 CST

---

## 今天在项目里的位置

```text
Day 191  引擎骨架      → 队列、限速、重试、落库                 ✅
Day 192  代理池        → IP 轮换、健康检查、按目标分配出口       ✅
Day 193  浏览器与验证码 → JS 渲染、指纹、验证码识别              ✅
Day 194  AI 增强       → 风险预测、内容去重、清洗入库管道        ✅
Day 195  运维与交付    → 调度、加密、鉴权、Docker + CI/CD      ← 今天
```

前四天解决的是**怎么把数据拿回来**。今天解决的是**这套东西怎么长期、安全、可重复地跑**：
抓取进程半夜挂了有没有人知道？数据库备份泄露了用户手机号会不会裸奔？
改一行代码后，你敢不敢直接在生产上重启？

一句话概括：**重试决定故障时能不能自愈，加密决定泄露时损失多大，交付决定你敢不敢改代码。**

---

## 概念速览

完整图解见 **diagrams/README.md**，定义与对比表见 **concepts.md**。

| 概念 | 一句话 | 为什么重要 |
|---|---|---|
| 错误分类 | 先判断该不该重试，再决定怎么重试 | 对 401 重试是把账号往风控里送 |
| 指数退避 | 每次失败等待翻倍，封顶 | 固定 1 秒会把上游打死 |
| full jitter | 在 [0, 退避值] 随机 | 500 个客户端同毫秒醒来 = 自己 DDoS 自己 |
| 重试预算 | 次数 + 总时长双上限 | 只限次数会被 Retry-After 拖到超 SLA |
| 幂等键 | 客户端生成，服务端持久化 | 没有它，重试 POST = 重复下单 |
| 结构化日志 | 一行 JSON，字段稳定 | 自由文本没法按 status 聚合 |
| 日志脱敏 | 在 logger 内部替换敏感键 | 靠调用方记得 = 迟早泄露 |
| 告警收敛 | 冷却窗口 + 抑制计数 | 1000 条相同告警 = 没人看 |
| AES-GCM | AEAD，机密性 + 完整性 | 只加密不认证会被篡改 |
| AAD | 不加密但参与认证 | 防密文被搬到别的记录上 |
| 信封加密 | 密文头带 kid | 才能轮换钥匙而不停机 |
| HMAC 签名 | 请求内容 + 时间 + nonce 一起签 | 泄露一次不等于永久失守 |
| 防重放 | 时间窗 + nonce 表 | 有效签名也能被原样重发 |
| 多阶段构建 | builder 装依赖，runtime 只拷产物 | 运行镜像更小、攻击面更少 |
| liveness / readiness | 活着 / 能接流量 | 合并会把小故障放大成雪崩 |
| 自动回滚 | 失败回到 PREV_REF | 手忙脚乱时最可靠的是脚本 |

---

## 一、概念解释

### 1. 调度、失败重试、日志与告警

#### 1.1 为什么“失败就重试”是错的

把重试写成 `for i in range(3): try: ... except: sleep(1)` 有三个问题：

1. **重试了不该重试的错误**：401 重试三次，等于把错误密码试三次；
2. **等待时间固定**：上游已经过载，所有客户端仍每秒撞一次；
3. **重试非幂等操作**：第一次其实成功了，只是响应丢了，第二次又下一单。

所以重试前必须先回答四个问题：**什么错、等多久、最多等多久、重试安不安全**。
这四问对应的实现就是：错误分类 → 指数退避 → 预算 → 幂等键。

#### 1.2 退避与抖动

```text
delay_n = min(max_delay, base × factor^(n-1))
sleep  = U(0, delay_n)        # full jitter
```

抖动不是为了“看起来随机”，而是为了**打散重试洪峰**。本机模拟 500 个客户端同时失败：
无抖动时 500 个客户端落在同一个 10ms 桶里；full jitter 后最大同桶只有 5 个。
平均总等待从 15.50s 降到 7.68s——因为少了很多“撞车后一起再失败”的轮次。

#### 1.3 幂等：重试的前置条件

GET/PUT/DELETE 天然幂等，POST 不是。生产做法：客户端生成 `Idempotency-Key`，
服务端把 key 和结果一起落库；重试命中 key 就直接返回第一次的结果。

本课实测：第一次 POST 已经写库但响应返回 503，朴素重试后数据库里 2 条记录；
带幂等键重试后仍然是 1 条。**服务端必须持久化 key**，内存表重启就失效。

#### 1.4 调度：至少一次

cron 适合低频、允许漂移的任务；长驻 worker + 队列适合高频、需要重试和并发控制的任务。
所有可靠队列默认 **at-least-once**：任务可能重复投递，所以任务本身必须幂等。
调度器还要监控 **last_success_at**——“多久没成功”比“有没有报错”更接近真实故障。

#### 1.5 日志：一行 JSON

固定字段：`ts / level / service / event / request_id` + 业务字段。
事件名要稳定（`db_connect_failed`），不要写自由文本；否则无法聚合与告警。
脱敏必须做在 logger 内部：按 key 名递归替换 password/token/authorization/cookie/master_key。

#### 1.6 告警：症状、收敛、分级

- 告警**症状**（5xx 比例、支付成功率、队列积压），不是**原因**（CPU 高）；
- 同 key 在冷却窗口内只发一条，其余累计 suppressed；
- critical 打电话，warning 只开工单；
- 恢复时 reset 冷却状态，否则下次故障会被上一次的窗口吞掉。

实测：1000 次数据库失败，60s 冷却窗口下只发出 10 条告警，每条汇总 99 次抑制。

### 2. 数据加密与 API 鉴权

#### 2.1 三种加密边界

| 边界 | 保护什么 | 本课做法 |
|---|---|---|
| 传输 | 链路窃听 | 生产用 TLS 终止（本机实验未配 TLS，见“已知边界”） |
| 静态 | 磁盘/备份泄露 | AES-256-GCM 加密 secret 字段后入 SQLite |
| 字段级 | DBA 也看不到明文 | AAD 绑定记录 ID，密文与行强绑定 |

#### 2.2 AES-GCM 的关键约束

AES-GCM = CTR 加密 + GHASH 认证。它同时给机密性和完整性，但有一个致命约束：
**同一把钥匙下 nonce 绝不能重复**。重复会让攻击者拿到两条明文的异或，
认证密钥也可能被恢复。所以 nonce 用 12 字节随机数，密文头里带上 kid。

#### 2.3 AAD 与信封

```text
v1. | kid_len(1) | kid | nonce(12) | ciphertext+tag(16)
```

把 record_id 作为 AAD：密文从 row-42 复制到 row-43 会解密失败，而不是静默串号。
kid 写在密文头里，解密方才知道用哪把钥匙——这是轮换的前提。

#### 2.4 密钥轮换

轮换不是“换一把钥匙重启”：旧密文还在。正确顺序是：新增 k2 并设为 primary → 新数据用 k2 →
后台批量重加密旧数据 → 确认无 k1 密文后再删除 k1。本课实测旧密文在轮换后仍可解；
只带新钥匙的副本会明确抛 `UnknownKeyID`，而不是返回垃圾。

密钥不能和数据放同一个卷，更不能进 git。生产用 KMS/Vault；本课用 `.master-key`（chmod 600）
只是为了让实验可复现。

#### 2.5 从 API Key 到 HMAC

静态 API Key 是一把永久万能钥匙：泄露一次，攻击者可以读、改、重放到天荒地老。
HMAC 签名把**这一次请求**钉死：

```text
canonical = METHOD + newline + PATH + newline + TS + newline + NONCE + newline + SHA256(body)
signature = HMAC-SHA256(secret, canonical)
```

服务端先验时间窗（±300s），再常量时间比较签名，最后查 nonce 表防重放。
顺序不能反：先记 nonce 会让攻击者用错误签名刷爆内存表。

#### 2.6 JWT 的边界

JWT 只是“签名的 JSON”，不是“更安全的 session”。两个经典洞：
不锁 `alg`（`alg=none` 直接绕过）、只验签名不验 scope。
另外 JWT 无法主动吊销，必须靠短 TTL + refresh token。

### 3. Docker 与 CI/CD

#### 3.1 镜像分层与多阶段

每个 `RUN/COPY` 一层，层可缓存；多阶段构建把编译器和 pip 缓存留在 builder，
运行镜像只拷 `/install`。本课运行镜像 201 MB（python:3.12-slim + cryptography）。

#### 3.2 最小权限

| 措施 | 作用 |
|---|---|
| `USER app`（uid 10001） | 逃逸后不是 root |
| `--read-only` + tmpfs /tmp | 运行期不能改镜像 |
| `--cap-drop ALL` | 去掉全部 capabilities |
| `--security-opt no-new-privileges` | 禁止提权 |

这些不是“安全表演”：容器逃逸的第一跳通常是写文件或提权，去掉这些能力会显著抬高成本。

#### 3.3 健康检查与优雅退出

`HEALTHCHECK` 在容器内跑，退出码 0 = 健康；`start-period` 内的失败不计入重试。
liveness（活着）和 readiness（能接流量）必须分开：数据库抖 10 秒时，
合并成一个探针会导致所有副本被重启，把小故障放大成雪崩。

SIGTERM 到来时停止接收新连接、等在途请求处理完再退出。
本课实测 `docker stop` 0.40s，日志里依次出现 `shutdown_requested signal=15` 与 `shutdown_complete`。

#### 3.4 部署与回滚

部署脚本启动前记录当前镜像引用 `PREV_REF`；新容器健康检查或验收失败就回滚。
验收不能只 curl 首页，要真实走一遍：readyz → 签名写入 → 解密读回 → 重放拒绝。
本课坏镜像在 8 秒内被判 unhealthy，自动回滚到 v1，验收重新通过（详见实验 7）。

#### 3.5 CI

流水线：语法检查 → 离线自检 → 起服务跑验收 → 构建镜像。
每一层都要能在**没有外部服务**的情况下自证，否则 CI 会变成“只有 CI 机器能过”的玄学。
---

## 二、原理深入

### 2.1 为什么指数退避要配抖动

假设 1000 个客户端在同一秒失败，退避都是 1s、2s、4s：它们会在同一毫秒再次同时醒来。
上游刚缓过来又被同样规模的流量打回去，形成“同步重试 → 二次过载 → 再同步”的循环。

full jitter 把第 n 次等待从固定值变成 `U(0, delay_n)`，代价是平均等待变长，
收益是到达时间被摊平。实测 500 客户端：同桶峰值 500 → 5，平均总等待 15.50s → 7.68s。

重试预算（deadline）是第二道闸：只限次数时，一次 `Retry-After: 5` 就能把 5 次重试拖成 25 秒。
预算到了必须抛错，把“继续等”变成“上层决定降级”。

### 2.2 AES-GCM 到底做了什么

```text
明文 ──CTR(key, nonce)──▶ 密文
                    │
AAD ──▶ GHASH(H, AAD, 密文) ──▶ tag(16B)
```

- CTR 部分提供机密性：nonce 复用 = 两次性 One-Time Pad 复用，异或即可消掉密钥流；
- GHASH 部分提供完整性：任何一位改动都会让 tag 不匹配；
- tag 不匹配时 `cryptography` 抛 `InvalidTag`，**不要**捕获后返回部分明文。

信封里带 kid 的意义：解密时先读 kid，再选钥匙；轮换期间新旧密文共存。

### 2.3 签名 canonicalization 的三个坑

1. **字段拼接歧义**：`a|bc` 和 `ab|c` 可能拼成同一个字符串。用换行分隔并固定字段顺序；
2. **只签 path 不签 query**：攻击者可以改 `?amount=1` 为 `?amount=999`；
3. **只签 body 不签 method**：GET 的签名能被拿去发 POST。本课实测这两种篡改都被 401 拦下。

比较签名必须用 `hmac.compare_digest`，普通 `==` 的短路比较会泄露前缀匹配长度。

### 2.4 健康检查的生命周期

```text
容器启动 → starting（start-period 内的失败不计入 retries）
        → healthy（连续成功）
        → unhealthy（连续 retries 次失败）
```

Docker 只在 healthy/unhealthy 之间切换，**不会**因为 unhealthy 自动重启容器（除非用 Swarm/K8s）。
所以部署脚本必须自己把 unhealthy 当作失败——本课第一版漏了这个分支，白等 30 秒。

### 2.5 优雅退出为什么值钱

直接 `kill -9` 会丢掉在途请求，客户端看到连接重置；对写操作还可能留下半条数据。
正确顺序：收到 SIGTERM → 停止 accept → 等在途 handler 结束 → 关数据库 → 退出 0。
本课用 `ThreadingHTTPServer(daemon_threads=False, block_on_close=True)` 实现，
实测 `docker stop` 0.40s，exit code 0。

### 2.6 回滚的原子性

回滚不是“把旧镜像再跑一遍”这么简单：
- 要先删掉失败容器（同名冲突）；
- 要复用同一个数据卷（数据不能丢）；
- 要重新等健康检查，确认旧版本真的活了；
- 回滚本身失败要返回不同退出码（本课 1 = 已回滚，2 = 回滚也失败），让上层告警分级。

---

## 三、定义与使用方法（API 速查）

### 3.1 ops_lib.py

| 名称 | 签名 | 说明 |
|---|---|---|
| `classify` | `classify(exc) -> Failure` | 异常 → retryable / rate_limit / auth / fatal |
| `RetryPolicy` | `(attempts=5, base_delay=0.2, factor=2.0, max_delay=5.0, jitter='full', deadline=None)` | 重试参数 |
| `retry_call` | `retry_call(fn, policy, on_retry=None, sleep=time.sleep, clock=time.monotonic) -> (value, report)` | 执行并按策略重试 |
| `compute_delay` | `compute_delay(policy, attempt, retry_after=None) -> float` | 计算第 n 次失败后的等待 |
| `JsonLogger` | `JsonLogger(service, level='INFO').bind(**fields)` | 结构化日志；`info/warning/error` |
| `redact` | `redact(obj) -> obj` | 递归脱敏 |
| `AlertSink` | `AlertSink(cooldown=60, clock=time.monotonic)` | `emit(key, severity, message)`；`reset(key)` |

### 3.2 crypto_lib.py

| 名称 | 签名 | 说明 |
|---|---|---|
| `KeyRing` | `KeyRing(keys=None, primary=None)` | 钥匙环；`rotate(kid)` / `key(kid)` / `export()` |
| `encrypt` | `encrypt(ring, plaintext: bytes, aad=b'', kid=None) -> str` | 返回 `v1.` 前缀密文 |
| `decrypt` | `decrypt(ring, token, aad=b'') -> bytes` | 篡改/错 AAD 抛 `InvalidTag` |
| `envelope_kid` | `envelope_kid(token) -> str` | 不解密读 kid |
| `reencrypt` | `reencrypt(ring, token, aad=b'') -> str` | 轮换后重加密 |
| `sign_request` | `sign_request(secret, method, path, ts, nonce, body) -> hex` | 生成签名 |
| `verify_request` | `verify_request(...) -> (bool, reason)` | 时间窗 + 签名 |
| `NonceStore` | `NonceStore(ttl=300).use(nonce) -> bool` | 防重放（单进程内存） |
| `issue_token` | `issue_token(secret, subject, scopes, ttl=300) -> str` | HS256 JWT |
| `verify_token` | `verify_token(secret, token, now=None, leeway=0) -> dict` | 校验 exp/alg/签名 |

### 3.3 服务接口（app.py）

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/healthz` | 否 | 存活探针，只证明进程能响应 |
| GET | `/readyz` | 否 | 就绪探针，检查 SQLite 可读 + 主密钥存在 |
| GET | `/metrics` | 否 | 进程内计数器 JSON |
| POST | `/api/v1/records` | HMAC | body: `{name, secret}`；secret 加密落库 |
| GET | `/api/v1/records/{id}` | HMAC | 解密返回 |
| GET | `/api/v1/records` | HMAC | 列出 id/name/kid，绝不返回 secret |

请求头：`X-Timestamp`、`X-Nonce`、`X-Signature`；可选 `X-Request-ID`（不传则服务端生成）。

### 3.4 常用命令

| 目的 | 命令 |
|---|---|
| 离线自检 | `python3 code/app.py --self-test` |
| 本地起服务 | `DATA_DIR=./data API_SECRET=demo python3 code/app.py --port 8080` |
| 构建 | `docker build -t learn195-app:v1 -f code/Dockerfile code` |
| 一键部署 | `cd code && ./deploy.sh --tag v1` |
| 部署已有镜像 | `./deploy.sh --ref learn195-app:v1 --no-build` |
| 验收 | `python3 smoke_test.py --url http://127.0.0.1:18095 --secret ...` |
| 查看健康 | `docker inspect -f '{{.State.Health.Status}}' learn195-app` |
| 清理 | `./deploy.sh --down` |
| 本地 CI | `./ci/run-local.sh --with-docker` |

---

## 四、图解

Mermaid + ASCII 全套见 **diagrams/README.md**。最重要的两张：

```text
重试：Call → Classify →(可重试) Wait → Call
                     └(401/4xx) FailFast
部署：记录 PREV_REF → 起新容器 → HEALTHCHECK → smoke → 成功
                                └─失败→ 回滚 PREV_REF → 再验收
```

看图重点：**决策点在哪、失败分支回到哪**。运维代码的价值几乎全在这两个问题上。
---

## 五、实战实验手册

> 所有「实际结果」都是 2026-10-25 06:00–06:10 CST 在本机跑出来的原文，
> 不是示意图。命令按顺序可直接复制；每个实验末尾都有清理步骤。

### 实验 0：确认环境

**目的**：记录可复现的基线。

```bash
python3 -V
docker --version
uname -r
```

**实际结果**：

```text
Python 3.12.3
Docker version 29.1.3, build 29.1.3-0ubuntu3~24.04.2
7.0.0-34-generic
```

---

### 实验 1：重试、抖动与幂等（离线 + 本地假上游）

**目的**：验证错误分类、退避、抖动、幂等键四件事。

**准备**：无外部依赖。

```bash
cd days/day-195-运维-加密与交付/code
python3 01-retry-backoff.py
```

**实际结果（节选）**：

```text
演示 1：两次 503 之后成功 —— 看时间线
  attempt 1: GET /flaky
    ↳ TransientError(HTTP 503) → sleep 0.079s
  attempt 2: GET /flaky
    ↳ TransientError(HTTP 503) → sleep 0.200s
  attempt 3: GET /flaky
  ✅ HTTP 200 {"ok": true, "call": 3}
  总尝试 3 次，实际耗时 0.313s，退避序列 [0.079, 0.2]

演示 2：错误分类决定重试次数
  401 凭证过期       分类=auth       调用 1 次  耗时 0.0ms
  404 资源不存在      分类=fatal      调用 1 次  耗时 0.0ms
  503 上游过载       分类=retryable  调用 4 次  耗时 70.4ms
  429 被限流        分类=rate_limit 调用 4 次  耗时 600.4ms

演示 3：500 个客户端同时重试
  策略                   同一 10ms 桶最大并发        平均总等待(s)
  无抖动                          500             15.50
  equal                          5             11.59
  full                           5              7.68

演示 4：重试 POST
  服务端实际落库 2 条（客户端只看到 1 次成功）
  带幂等键后实际落库 1 条
```

**结论**：
- 401/404 一次就停，503/429 才值得重试；
- 抖动把同桶峰值从 500 压到 5；
- 幂等键把重复写入从 2 条降到 1 条。

**清理**：脚本自己 shutdown 本地 server，无残留端口。

---

### 实验 2：AES-GCM 加密、篡改检测、轮换与吞吐

**目的**：确认 AAD 防搬家、认证标签能拦篡改、轮换可解旧数据，并测真实吞吐。

```bash
python3 02-crypto-envelope.py
```

**实际结果（节选）**：

```text
轮换前 primary=k1，密文 kid 全是 k1
轮换后 primary=k2，钥匙环含 ['k1', 'k2']
旧密文仍可解: b'secret-0'
批量重加密后 kid: ['k2', 'k2', 'k2']
✅ 缺少旧钥匙时明确报 UnknownKeyID(k1)，而不是静默返回垃圾

负载 1 MiB × 30 次，取中位数
加密: 4.98 ms/次  ≈ 201 MiB/s
解密: 6.46 ms/次  ≈ 155 MiB/s
小记录（54 B）加解密: 13.8 µs/次 ≈ 72,592 次/秒
```

**结论**：加密不是瓶颈；瓶颈在密钥管理（KMS 往返）和轮换重加密窗口。

---

### 实验 3：多阶段构建 + 一键部署

**目的**：验证 Dockerfile、非 root、只读根文件系统、健康检查与验收脚本能协同工作。

```bash
cd days/day-195-运维-加密与交付/code
./deploy.sh --tag v1
```

**实际结果（节选）**：

```text
[deploy 06:05:47] 当前运行版本: learn195-app:v1
[deploy 06:05:48] 启动 learn195-app:v1 → 127.0.0.1:18095
[deploy 06:05:54] 容器健康（耗时 7s）
[deploy 06:05:54] 验收：签名写入 → 解密读回 → 重放拒绝
  ✅ readyz 200     HTTP 200 b'{"status": "ready", "kid": "env"}'
  ✅ 签名写入 201       HTTP 201 b'{"id": "672d931d...", "kid": "env"}'
  ✅ 解密读回一致         HTTP 200 secret='smoke-d5d05463'
  ✅ 重放被拒 409       HTTP 409 b'{"error": "replayed_nonce"}'
SMOKE PASS
[deploy 06:05:54] ✅ 部署成功：learn195-app:v1
  镜像=learn195-app:v1 状态=running 健康=healthy
```

镜像大小：`learn195-app:v1  201MB`（多阶段构建后的运行镜像）。

**清理**：`./deploy.sh --down`（会删除容器与数据卷）。

---

### 实验 4：安全基线与“落库真的是密文”

```bash
docker inspect -f 'User={{.Config.User}} Readonly={{.HostConfig.ReadonlyRootfs}} CapDrop={{.HostConfig.CapDrop}} NoNewPriv={{.HostConfig.SecurityOpt}}' learn195-app
curl -s http://127.0.0.1:18095/metrics
docker exec learn195-app python -c "import sqlite3;c=sqlite3.connect('/data/app.db');print(c.execute('select ciphertext from records limit 1').fetchone()[0][:40])"
```

**实际结果**：

```text
User=app Readonly=true CapDrop=[ALL] NoNewPriv=[no-new-privileges]
{"auth_checks": 6, "auth_failures": 2, "metrics_scrapes": 1, "records_created": 2, "records_read": 2, "requests_total": 14}
v1.A2VudhSSWADq_T1gE3vgGmkeL79gE76MqKfP-...
```

**结论**：容器以 uid 10001 运行、根文件系统只读、能力全 drop；数据库里只有 `v1.` 前缀的密文。

---

### 实验 5（翻车 1）：用 curl 写 HEALTHCHECK，容器永远 unhealthy

**目的**：复现一个极常见的 Docker 事故。

```bash
docker run -d --name d195-curlhealth -p 127.0.0.1:18097:8080 \
  -e API_SECRET=x -e MASTER_KEY="$(cat .master-key)" -v d195-curl-vol:/data \
  --health-cmd 'curl -fsS http://127.0.0.1:8080/healthz || exit 1' \
  --health-interval 2s --health-timeout 1s --health-retries 2 learn195-app:v1
```

**实际结果**：

```text
t=1s health=starting
...
t=13s health=unhealthy

=== health log ===
{"ExitCode": 1, "Output": "/bin/sh: 1: curl: not found\n"}
{"ExitCode": 1, "Output": "/bin/sh: 1: curl: not found\n"}

=== app still serving ===
HTTP 200
```

**根因**：`python:3.12-slim` 里没有 curl。健康检查失败被 Docker 判为 unhealthy，
但应用本身完全正常（直接请求 /healthz 返回 200）。这就是“探针骗人”。

**修复**：用镜像里一定存在的 python 自检（最终 Dockerfile 的写法）：

```dockerfile
HEALTHCHECK --interval=5s --timeout=3s --start-period=8s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).status == 200 else 1)"]
```

**清理**：

```bash
docker rm -f d195-curlhealth
docker volume rm d195-curl-vol
```

---

### 实验 6（翻车 2）：绑定挂载目录属主是 root，非 root 容器起不来

```bash
mkdir -p /tmp/d195-bind-data && chown root:root /tmp/d195-bind-data && chmod 755 /tmp/d195-bind-data
docker run -d --name d195-bind -p 127.0.0.1:18098:8080 \
  -e API_SECRET=x -e MASTER_KEY="$(cat .master-key)" \
  -v /tmp/d195-bind-data:/data learn195-app:v1
```

**实际结果**：

```text
bind dir: root:root 755
status=exited exit=1
  File "/app/app.py", line 394, in main
    app = App(data_dir, api_secret.encode(), keyring)
  File "/app/app.py", line 108, in __init__
    self._init_db()
sqlite3.OperationalError: unable to open database file
```

**根因**：容器内 uid 10001 对 root:root 755 目录没有写权限；SQLite 连 WAL 都建不了。
命名卷（named volume）不会踩坑，因为 Docker 首次创建时会继承镜像里 /data 的属主；
**绑定挂载（bind mount）不会**，它原样暴露宿主机权限。

**修复方式（三选一）**：
```bash
# 1) 用命名卷（本课 deploy.sh 的选择）
docker volume create learn195-data
# 2) 预先把宿主机目录 chown 10001:10001
sudo chown -R 10001:10001 /tmp/d195-bind-data
# 3) 启动时用 --user $(id -u):$(id -g)（会牺牲“固定非 root uid”的可移植性）
```

**清理**：

```bash
docker rm -f d195-bind
rm -rf /tmp/d195-bind-data
```

---

### 实验 7（翻车 3）：坏镜像部署，回滚等 31 秒才动

**目的**：验证自动回滚，并暴露等待逻辑的缺陷。

```bash
docker build -t learn195-app:broken -f broken/Dockerfile broken
./deploy.sh --ref learn195-app:broken --no-build
```

**第一次实际结果（有缺陷的版本）**：

```text
[deploy 06:07:11] 启动 learn195-app:broken → 127.0.0.1:18095
[deploy 06:07:42] 等待健康超时（30s），最后状态=unhealthy
[deploy 06:07:42] ❌ 新版本未通过健康检查
[deploy 06:07:43] 回滚到 learn195-app:v1
```

**根因**：`wait_healthy` 的 `case` 只处理了 healthy / exited / dead / missing，
漏了 **unhealthy**。Docker 早已判定失败，脚本却继续轮询到 30 秒超时。

**修复**：把 unhealthy 当作立即失败（见 deploy.sh 注释）。

**复测实际结果**：

```text
[deploy 06:07:53] 启动 learn195-app:broken → 127.0.0.1:18095
[deploy 06:08:01] 健康检查失败（unhealthy），不再等待
[deploy 06:08:01] ❌ 新版本未通过健康检查，最近日志：
broken app listening on :8080
[deploy 06:08:01] 回滚到 learn195-app:v1
```

**数字对比**：故障判定 31s → 8s；回滚后 `smoke_test.py` 重新 PASS。

---

### 实验 8：验收与真实延迟

**目的**：证明服务不只好看，写入/解密读回真的可用，并量化延迟。

```bash
python3 smoke_test.py --url http://127.0.0.1:18095 --secret demo-api-secret-change-me
python3 /tmp/d195-bench.py   # 100 次 POST + 100 次 GET，单线程顺序
```

**实际结果**：

```text
  ✅ readyz 200     HTTP 200 b'{"status": "ready", "kid": "env"}'
  ✅ 签名写入 201       HTTP 201
  ✅ 解密读回一致         HTTP 200 secret='smoke-d40122b1'
  ✅ 重放被拒 409       HTTP 409 b'{"error": "replayed_nonce"}'
SMOKE PASS

POST /api/v1/records (AES-GCM + SQLite): n=100 mean=8.57ms p50=8.13ms p95=11.92ms max=23.48ms
GET  /api/v1/records/{id} (SQLite + decrypt): n=100 mean=1.81ms p50=1.40ms p95=4.06ms max=5.33ms
```

**测试条件**：同一台 4 vCPU / 15.59 GiB 机器，客户端与服务端同机，单线程顺序请求，
含 TLS 之外的完整 HTTP + HMAC 验签 + AES-GCM + SQLite WAL 写。数字用于横向比较，不是容量承诺。

---

### 实验 9：优雅退出

```bash
/usr/bin/time -f 'stop took %e s' docker stop learn195-app
docker logs --tail 4 learn195-app
```

**实际结果**：

```text
stop took 0.40 s
{"event": "shutdown_requested", "signal": 15}
{"event": "shutdown_complete"}
status: exited exit=0
```

---

### 实验 10：本地 CI

```bash
./ci/run-local.sh
```

**实际结果（节选）**：

```text
▶ 1/4 语法检查（compileall）
  所有 .py 编译通过
▶ 2/4 离线自检
  ops_lib.py / crypto_lib.py / 01 / 02 / 03 / 04 / app.py  OK
▶ 3/4 起服务 + 跑验收
  ✅ readyz 200 ... SMOKE PASS
▶ 4/4 跳过 Docker（加 --with-docker 启用）
✅ CI 全部通过
```

**未实测说明**：`ci/github-actions.yml` 没有在 GitHub 上真正触发（本课环境没有远程 Actions 运行器）。
它和 `run-local.sh` 的步骤一一对应；验证方法：把该文件放到仓库 `.github/workflows/` 下推送，
预期看到 test job 依次通过 compileall、7 个 self-test、docker build。

---

## 六、翻车复盘（现象 → 假设 → 验证 → 根因 → 修复 → 复测）

| # | 现象 | 假设 | 验证 | 真实根因 | 修复 | 复测 |
|---|---|---|---|---|---|---|
| 1 | 容器一直 unhealthy，但手 curl 服务是 200 | 应用挂了 / 探针写错 | `docker inspect .State.Health.Log` | slim 镜像没有 curl，探针命令本身失败 | 改用 `python -c urllib` | healthy，容器正常接流量 |
| 2 | 非 root 容器启动即退出 | 代码 bug / 卷权限 | `docker logs` 看到 sqlite `unable to open database file` | bind mount 目录 root:root 755，uid 10001 不可写 | 换命名卷或 chown 10001 | 服务起来，readyz 200 |
| 3 | 坏镜像回滚要等 31 秒 | Docker 没检测到失败 | 日志显示 30s 超时后状态才 unhealthy | `wait_healthy` 漏了 unhealthy 分支 | 加 case unhealthy 立即失败 | 判定时间 8 秒 |

三条都不是“理论上的坑”，是这次编写时真实踩到并修掉的。它们共同说明一件事：
**运维脚本的错误分支比正常分支更值得写测试。**

---

## 七、收尾卫生（本次实际清理）

```text
docker rm -f learn195-app d195-curlhealth d195-bind
docker volume rm learn195-data d195-curl-vol
docker rmi learn195-app:v1 learn195-app:broken learn195-app:ci
rm -rf code/__pycache__ code/.master-key code/data
```

验证结果：

```text
no containers
no volumes
no images
```

清理后宿主机没有残留监听端口（18095/18097/18098 均已释放）。
注意：`.master-key` 被删除意味着本次实验数据的解密钥匙也没了——这正是预期行为，
演示“密钥不与数据同生命周期”。

---

## 八、思考题

1. 你的服务对下游重试 3 次，下游也对它的下游重试 3 次，最坏情况下一次用户请求会放大成多少次调用？
   怎么用重试预算和抖动把放大倍数压住？
2. 为什么 AES-GCM 的 nonce 复用比“密钥稍微弱一点”更危险？如果必须在分布式系统里生成 nonce，你会怎么保证唯一？
3. HMAC 签名已经覆盖 body 哈希，为什么还要签 method 和 path？举一个只签 body 会被利用的场景。
4. liveness 探针里如果检查数据库连接，会发生什么？请描述“数据库抖动 10 秒”到“全站雪崩”的完整链条。
5. 自动回滚失败时，脚本应该返回什么退出码、发什么级别的告警？如果回滚后旧版本也不健康，人工介入的第一步应该是什么？

---

## 九、验收清单

- [ ] `python3 code/ops_lib.py --self-test` 通过
- [ ] `python3 code/crypto_lib.py --self-test` 通过
- [ ] 01–04 四个脚本的 `--self-test` 全部通过
- [ ] `python3 code/app.py --self-test` 通过
- [ ] `docker build` 成功，镜像以非 root 运行、根文件系统只读
- [ ] `./deploy.sh` 输出 SMOKE PASS，健康状态 healthy
- [ ] 用坏镜像部署能看到“回滚到上一版本”，且回滚后 smoke 重新 PASS
- [ ] `docker stop` 在 1 秒级完成，日志有 shutdown_complete，退出码 0
- [ ] 实验结束后 `docker ps -a` / `docker volume ls` / `docker images` 无 learn195 残留

逐条命令与预期输出见 **exercises/checklist.md**。

---

## 十、已知边界（诚实说明）

1. **没有配 TLS**：本机实验直接跑 HTTP。生产必须在反向代理/负载均衡终止 TLS，
   并把 HSTS、证书轮换纳入交付流程。
2. **密钥管理是教学级**：`MASTER_KEY` 放环境变量、`.master-key` 放仓库目录（已 gitignore），
   生产应使用 KMS/Vault，且密钥不落盘。
3. **nonce 表在进程内存**：多副本部署时各副本各记各的，重放可打到另一个副本。生产换 Redis。
4. **单机部署**：本课是 recreate 策略，有秒级停机；生产用滚动/蓝绿，并做连接 draining。
5. **GitHub Actions 未实际触发**：只做了本地等价验证（见实验 10 的未实测说明）。
6. **压测是单线程顺序请求**：数字用于比较实现开销，不代表并发容量。

下一步（Day 196–200）会把 200 天的知识串成体系，并准备面试与开源贡献。