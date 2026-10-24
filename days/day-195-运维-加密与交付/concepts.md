# Day 195 概念卡 — 运维、加密与交付

> 配套正文：`README.md` ｜ 代码：`code/` ｜ 图解：`diagrams/README.md`
> 所有结论都来自 2026-10-25 上午在本机的真实执行，不是转述。

---

## 1. 重试（Retry）

### 1.1 四个必须先回答的问题

| 问题 | 错误做法 | 正确做法 |
|---|---|---|
| 什么错该重试 | 所有异常都 `except: retry` | 先分类：5xx/超时/429 可重试，4xx/401 不重试 |
| 等多久 | 固定 `sleep(1)` | 指数退避 + 上限 + 抖动 |
| 最多等多久 | 只限次数 | 次数 + 总时长预算（deadline）双约束 |
| 重试安全吗 | 默认安全 | 只有幂等操作能安全重试；非幂等要 Idempotency-Key |

### 1.2 错误分类表

| 异常/状态 | 分类 | 处理 | 理由 |
|---|---|---|---|
| 连接超时、连接重置 | retryable | 退避重试 | 网络瞬断，重试大概率成功 |
| 500 / 502 / 503 / 504 | retryable | 退避重试 | 上游临时故障 |
| 429 | rate_limit | 按 Retry-After 等待 | 服务端明确告诉你节奏 |
| 401 / 403 | auth | 立即失败并告警 | 凭证错了，重试只会刷爆风控 |
| 400 / 404 / 422 | fatal | 立即失败 | 请求本身错了 |
| 未知异常 | fatal | 立即失败（默认） | 宁可少试，不放大事故 |

**为什么默认 FATAL**：重试的期望收益是"瞬时故障恢复"，如果异常类型未知，你无法判断它是否瞬时；
而重试未知异常可能触发重复扣款、重复建单。生产系统里"少做"通常比"做错"便宜。

### 1.3 退避公式

`
delay_n = min(max_delay, base_delay × factor^(n-1))
sleep  = U(0, delay_n)          # full jitter
`

- `base_delay`：第一次等待，通常 0.1–1s；
- `factor`：常见 2；
- `max_delay`：必须有上限，否则第 10 次要等 8 分钟；
- `full jitter`：在 [0, delay] 均匀取值，把同时重试的客户端打散。

实测（本机，500 客户端 × 5 次重试，10ms 时间桶）：
无抖动最大同桶 500，equal jitter 为 5，full jitter 为 5；平均总等待 15.50s / 11.59s / 7.68s。

### 1.4 幂等（Idempotency）

同一个请求执行一次和执行 N 次，结果相同。

- HTTP 语义：GET/PUT/DELETE 天然幂等，POST 不幂等；
- 实现：客户端生成 `Idempotency-Key`，服务端持久化 key → 结果，重试命中直接返回原结果；
- 关键：key 必须在重试间保持不变，且服务端要落库（内存表重启就失效）。

实测：第一次 POST 已写库但响应丢失，朴素重试后库里 2 条；带幂等键后 1 条。

### 1.5 重试预算

`
attempts=5, deadline=10s
`

只限次数不够：如果每次 delay 被 Retry-After 拉到 5 秒，5 次就是 25 秒，超过上游 SLA。
预算到了就抛 `TimeoutError`，让上层决定降级还是失败。

---

## 2. 调度（Scheduling）

| 方式 | 适用 | 缺点 |
|---|---|---|
| cron / systemd timer | 单机、低频、允许漂移 | 多副本会重复执行；无内建重试/告警 |
| 长驻 worker + 队列 | 高频、需要重试/并发控制 | 要自己处理堆积、死信、优雅退出 |
| 托管调度（K8s CronJob 等） | 云上、多副本 | 仍有"至少一次"语义 |

### 2.1 至少一次（at-least-once）
所有可靠队列默认至少一次：任务可能重复投递。因此任务本身必须幂等，
或者用"租约锁 + 完成标记"去重。不要假设"只会执行一次"。

### 2.2 调度器自身的高可用
单点 cron 挂了没人知道，比不调度更危险。最低要求：
- 每次执行写一条带 trace_id 的日志；
- 失败连续 N 次触发告警；
- 记录 last_success_at，监控"多久没成功"而不是"有没有报错"。

---

## 3. 日志（Logging）

### 3.1 一行 JSON 的固定字段

| 字段 | 作用 |
|---|---|
| `ts` | UTC ISO8601，带毫秒 |
| `level` | DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `service` | 哪个服务 |
| `event` | 稳定的事件名（不是自由文本） |
| `request_id` | 贯穿一次请求 |
| 业务字段 | status、duration_ms、route、attempt… |

**为什么 event 名要稳定**：`"failed to connect db"` 和 `"db connect error"` 是两条无法聚合的日志；
`db_connect_failed` 才能按 event 做计数和告警。

### 3.2 脱敏
在 logger 内部按 key 名递归替换（password/token/authorization/cookie/master_key…）。
放在调用方迟早会漏。注意：只按 key 名不够，正文里的身份证/手机号仍需字段级加密或掩码。

### 3.3 采样与级别
- 高频成功日志：采样或降级到 DEBUG；
- 错误日志：不采样，但要做告警收敛；
- 生产默认 INFO，排障时临时开 DEBUG 并设 TTL。

---

## 4. 告警（Alerting）

### 4.1 告警的是症状，不是原因
好告警：`5xx 比例 > 5% 持续 2 分钟`、`支付成功率 < 95%`、`队列积压 > 10 万`。
坏告警：`CPU 高`（可能完全不影响业务）。

### 4.2 收敛
同 key 在冷却窗口内只发一条，其余累计 `suppressed`。
实测：1000 次数据库失败 → 10 条告警（60s 窗口），每条汇总 99 次抑制。

### 4.3 分级
| 级别 | 去向 | 例子 |
|---|---|---|
| critical | 电话 + IM + 工单 | 支付网关全挂 |
| error | IM + 工单 | 缓存命中率骤降 |
| warning | 工单 | 慢查询增多 |
| info | 仅日志 | 用户登录 |

### 4.4 恢复要 reset
故障恢复时清空冷却状态，否则下一次故障会被上一次的窗口吞掉。

---

## 5. 加密（Encryption）

### 5.1 三个必须区分的东西
| 名称 | 保护什么 | 典型算法 |
|---|---|---|
| 传输加密 | 链路上不被窃听 | TLS 1.3 |
| 静态加密 | 磁盘/备份泄露后不可读 | AES-256-GCM |
| 字段级加密 | 只加密敏感列，DBA 也看不到 | AES-GCM + KMS |

### 5.2 AES-GCM
- 认证加密（AEAD）：机密性 + 完整性一次完成；
- 组成：CTR 模式加密 + GHASH 认证标签（16 字节）；
- **nonce 绝不能复用**：同一 key 下 nonce 重复，攻击者可用两条密文异或恢复明文异或值；
- 推荐 12 字节随机 nonce；
- 密文比明文长 16 字节（tag）。

### 5.3 AAD
附加认证数据：不加密，但参与完整性校验。
把 `record_id` 作为 AAD，密文被复制到另一行时解密失败——防止"密文搬家"攻击。

### 5.4 信封加密与轮换
`
v1. | kid_len(1) | kid | nonce(12) | ciphertext+tag
`

- `kid` 让解密方知道用哪把钥匙；
- 轮换时保留旧钥匙，先双写再批量重加密；
- 实测：轮换到 k2 后旧密文仍可解；只带新钥匙的副本会明确抛 `UnknownKeyID`，而不是返回垃圾。

### 5.5 密钥管理
- 不要提交到 git（本课用 `.master-key` + chmod 600，仅演示）；
- 不要把密钥和数据放同一个卷；
- 生产用 KMS/Vault，密钥不落地；
- 轮换要有审计：谁、何时、哪把 key。

### 5.6 实测性能（本机，单线程，1 MiB × 30 次取中位数）
- 加密 4.98 ms/次 ≈ 201 MiB/s
- 解密 6.46 ms/次 ≈ 155 MiB/s
- 54 字节小记录：13.8 µs/次 ≈ 72,592 次/秒

结论：加密本身通常不是瓶颈，成本在 KMS 调用与轮换窗口。

---

## 6. 鉴权（Authentication & Authorization）

### 6.1 三种常见方案

| 方案 | 优点 | 风险 |
|---|---|---|
| 静态 API Key | 简单 | 永久有效；泄露即全损；无法防重放 |
| HMAC 请求签名 | 每次请求绑定时间/nonce/body | 实现复杂；时钟偏移要处理 |
| JWT | 无状态、可带 scope | 无法主动吊销；alg 配置错误等于没签 |

### 6.2 HMAC 签名规范

`
canonical = METHOD + newline + PATH + newline + TIMESTAMP + newline + NONCE + newline + SHA256(body)
signature = HMAC-SHA256(secret, canonical)
`

服务端校验顺序：
1. 时间窗（±300s）→ 防旧请求；
2. 签名（`hmac.compare_digest` 常量时间比较）→ 防篡改；
3. nonce 表 → 防重放。

**为什么先验签再记 nonce**：否则攻击者可以用大量签名错误的请求把 nonce 表刷爆（内存 DoS）。

### 6.3 JWT 的两个经典洞
- 不校验 `alg` → `alg=none` 直接绕过；
- 只验签名不验 payload 范围 → 改 `scope` 提权（签名会失败，但很多实现漏验）。

实测拦截：重放 409、改金额 401、过期/未来时间 401、错密钥 401、缺头 401、GET 签名用于 POST 401。

---

## 7. 容器（Docker）

### 7.1 镜像分层与多阶段
每个 `RUN/COPY` 一层；多阶段构建把编译器/包缓存留在 builder，运行镜像只留产物。
本课运行镜像基于 `python:3.12-slim`，201 MB。

### 7.2 最小权限
| 措施 | 作用 |
|---|---|
| `USER app`（uid 10001） | 逃逸后不是 root |
| `--read-only` + tmpfs /tmp | 运行期不能改镜像 |
| `--cap-drop ALL` | 去掉全部 Linux capabilities |
| `--security-opt no-new-privileges` | 禁止提权 |
| 非 root + 数据卷 | 数据目录权限要显式处理（见翻车实验 2） |

### 7.3 健康检查
- `HEALTHCHECK` 在容器内执行，退出码 0 = 健康；
- `start-period` 内的失败不计入 retries；
- 只装 python 的 slim 镜像里没有 curl —— 用 `python -c urllib` 自检；
- liveness 失败应重启，readiness 失败只摘流量，二者不能混。

### 7.4 优雅退出
SIGTERM → 停止接收新连接 → 等在途请求 → 退出 0。
实测 `docker stop` 0.40s，日志依次出现 `shutdown_requested signal=15` 与 `shutdown_complete`。

---

## 8. 交付（CI/CD）

### 8.1 流水线阶段
`
lint → unit/self-test → build image → smoke test → deploy → verify → (rollback on fail)
`

### 8.2 发布策略
| 策略 | 特点 | 回滚速度 |
|---|---|---|
| 重建（recreate） | 简单，有停机 | 秒级（换回旧镜像） |
| 滚动（rolling） | 无停机，版本混跑 | 分钟级 |
| 蓝绿 | 两套环境切流量 | 秒级 |
| 金丝雀 | 按比例放量 | 秒级 |

### 8.3 回滚必须是一等公民
部署脚本要在启动前记录 `PREV_REF`，健康检查或验收失败时自动回到它。
实测：坏镜像 8 秒被判 unhealthy，自动回滚到 v1，验收脚本重新通过。

### 8.4 验收而不是"端口通了"
本课 `smoke_test.py` 走完整链路：readyz → 签名写入 → 解密读回 → 重放拒绝。
只 curl 一下首页，无法发现"鉴权失效"或"写库失败"。

---

## 9. 术语速查

| 术语 | 一句话 |
|---|---|
| 指数退避 | 每次失败等待时间翻倍，避免持续冲击 |
| full jitter | 在 [0, 退避值] 随机，打散重试洪峰 |
| 重试预算 | 次数 + 总时长双上限 |
| 幂等键 | 客户端生成、服务端持久化，重复请求返回原结果 |
| AEAD | 同时提供机密性与完整性的加密模式 |
| AAD | 不加密但参与认证的附加数据 |
| kid | 密钥 ID，写在密文头里支持轮换 |
| nonce | 一次性随机数，GCM 下绝不复用 |
| HMAC | 用共享密钥对消息做认证的 MAC |
| 重放攻击 | 截获并原样重发有效请求 |
| liveness | 进程是否活着（失败→重启） |
| readiness | 是否可接流量（失败→摘除） |
| 多阶段构建 | builder 装依赖，runtime 只拷产物 |
| 金丝雀发布 | 先给小比例流量验证 |