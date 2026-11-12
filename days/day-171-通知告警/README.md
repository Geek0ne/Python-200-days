# Day 171 — 通知告警

> **一句话定义**：通知告警 = **把「系统出事了」这件事，可靠地送到唯一能看到它的人手里**。
> 难点从来不是「发出去」——发一条 HTTP 请求三行代码就能写完。
> 真正的难点是：**你以为发出去了，其实根本没送到。**

---

## 1. 学习目标

学完本课，你应该能够：

- [ ] 说清告警系统的 **4 层模型**：采集 → 判定 → 路由 → 送达
- [ ] 用 `smtplib` + `EmailMessage` 发出不会被拒收、不会乱码的中文邮件
- [ ] 解释 **MIME / multipart / RFC 2047 编码**各自解决什么问题
- [ ] 熟练接入 **钉钉 / 企业微信 / Slack** 三种 Webhook 机器人
- [ ] ⭐ 说出并复现本课最重要的发现：**HTTP 200 不代表发送成功**
- [ ] 区分「可重试错误」与「永久错误」，实现指数退避 + 限流感知重试
- [ ] 用 **指纹（fingerprint）+ 抑制窗口**把告警风暴压缩一个数量级
- [ ] 用**令牌桶**在撞到平台限流之前就自己排队
- [ ] 写出一个可用的多渠道告警中枢（扇出 / 去重 / 恢复 / 降级 / 脱敏 / 审计）
- [ ] 说清为什么**告警系统自己需要被监控**

---

## 2. 概念解释

### 2.1 告警不是「发消息」，是「送达」

初学者把告警理解成一个发送动作：

```python
requests.post(webhook, json={"text": "服务挂了"})
```

这个理解是错的。告警是一条**链路**，链路上任何一环断了，告警就没了：

```
[指标采集] → [阈值判定] → [路由选择] → [网络传输] → [平台接收] → [人真的看到]
     ↓            ↓             ↓            ↓            ↓            ↓
  采集失败     阈值写错     级别过滤错     超时/断网     200+errcode   被刷屏淹没
```

最后三环是最容易悄悄断掉的。**本课 80% 的篇幅都在讲它们。**

### 2.2 四层模型

| 层 | 职责 | 典型事故 |
|---|---|---|
| **采集层** | 从系统里取指标 | psutil 采集异常、指标本身为空 |
| **判定层** | 决定"是否该报警" | 阈值写死、抖动导致反复触发 |
| **路由层** | 决定"发给谁、走哪些渠道" | 级别过滤失效、群发所有人 |
| **送达层** | 真正把消息送出去 | **HTTP 200 但失败**、限流、超时 |

本课的代码主要落在**送达层**，因为这一层的坑最隐蔽。

### 2.3 为什么 Email 和 IM Webhook 是两套完全不同的协议

| 维度 | 邮件（SMTP） | IM 机器人（Webhook） |
|---|---|---|
| 协议 | 有状态的、多次往返的 TCP 会话 | 无状态的、一次 HTTP 请求 |
| 成功语义 | `250 OK` 且抛异常与否 | ⚠️ **HTTP 200 可能仍是失败** |
| 送达延迟 | 秒级（含反垃圾扫描） | 毫秒级 |
| 适合 | 详细报告、留档、值班交接 | 即时通知、需要 @ 人的紧急事件 |
| 可靠度 | 高（有退信、可重发） | 低（限流严格、会丢） |

**结论：生产告警系统两者都要——IM 负责"快"，邮件负责"全"。**

---

## 3. 原理深入

### 3.1 SMTP 会话长什么样（本机抓包实测）

`smtplib` 发一封邮件，实际在 TCP 上是这样的**多轮问答**：

```
C: ehlo [127.0.1.1]                          ← 客户端问「你支持什么扩展」
S: 250-capture.local greets you
S: 250-8BITMIME                            ← 我能收 8bit 正文
S: 250-SMTPUTF8                             ← 我能收 UTF-8 标题
S: 250 SIZE 10485760                        ← 单封最大 10MB
C: mail FROM:<alert@learn-python.dev> size=635
S: 250 2.1.0 Ok
C: rcpt TO:<niedong@learn-python.dev>
S: 250 2.1.5 Ok
C: data                                     ← 我要发正文了
S: 354 End data with <CR><LF>.<CR><LF>      ← 你发吧，以单独一行的 . 结束
C: From: ... To: ... Subject: =?utf-8?b?5pWw5o2u5bqT?= ...   ← 整封 MIME 原文
   .
S: 250 2.0.0 Ok: queued as CAPTURED
C: quit
S: 221 2.0.0 closing connection
```

**三个必须理解的细节：**

1. **`size=635` 是 ESMTP 参数，不是地址的一部分。**
   我第一次实现抓包服务器时，用 `line.partition(":")[2]` 抠地址，结果得到
   `selftest@learn-python.dev> size=246`，断言直接挂掉。**必须先按空格切掉参数区。**

2. **`Subject` 里那一串 `=?utf-8?b?5pWw5o2u5bqT?= ` 是 RFC 2047 编码。**
   邮件头只允许 ASCII，中文必须按这个格式编码 + base64。
   好消息：`EmailMessage` 会**自动**帮你做，你不用手写。

3. **`354` 之后是"以单独一行 `.` 结尾"的流式协议。**
   正文里如果有一行正好是 `.`，会被"点填充（dot-stuffing）"转义成 `..`。
   抓包服务器必须做**反转义**，否则日志会多出一个点。

### 3.2 为什么 MIME 存在

早期邮件只能传纯 ASCII 正文，于是需要一个机制同时携带**多段**和**多种编码**的内容 —— 这就是 MIME。

```
multipart/mixed                       ← 本课带附件时自动生成的顶层类型
├── text/plain; charset="utf-8"       ← 第 1 段：正文
│   Content-Transfer-Encoding: 8bit
│
└── text/plain; filename="app.log"    ← 第 2 段：附件
    Content-Disposition: attachment
```

- `Content-Type` 说什么这是什么类型
- `Content-Transfer-Encoding` 说什么编码方式（7bit / 8bit / base64 / quoted-printable）
- `Content-Disposition` 说这是正文还是附件

### 3.3 ⭐ 核心机制：HTTP 200 不等于成功

这是本课**最有价值的一条**，而且是本机真连官方端点测出来的：

```
钉钉     -> HTTP 200  {"errcode":300005,"errmsg":"token is not exist"}
企业微信 -> HTTP 200  {"errcode":93000,"errmsg":"invalid webhook url, hint: [...], from ip: 119.145.35.9, ..."}
Slack    -> HTTP 404  no_team
```

**为什么？** HTTP 状态码表达的是**传输层**语义：请求到达了、你的 Webhook 地址存在、服务器愿意处理。
而"这个机器人/token 有没有被禁用""你的关键词配不配""你是不是被限流了"属于**业务层**语义。

钉钉和企业微信把业务结果放在 body 的 `errcode` 里：

| errcode | 含义 | 该重试吗 |
|---|---|---|
| `0` | 成功 | — |
| `300005` | token 不存在 | ❌ 永久，重试无意义 |
| `310000` | 关键词不匹配 | ❌ 永久 |
| `400013` | 签名错误 / IP 不在白名单 | ❌ 永久 |
| `410100` / `130101` | 发送太频繁 | ✅ 该退避重试 |
| `45009`（企业微信） | 调用超限 | ✅ 该退避重试 |

所以正确写法是：

```python
r = requests.post(url, json=payload, timeout=10)
r.raise_for_status()                  # 第一层：传输层
body = r.json()
if body.get("errcode") != 0:          # 第二层：业务层 —— 千万别漏
    ...处理失败...
```

> **⚠️ 安全提醒**：上面企业微信返回的 `from ip: 119.145.35.9` 是**本机的公网出口 IP**。
> 真实环境中，Webhook 的错误信息会回显你的出口 IP —— 这意味着：
> 任何能拿到你 Webhook URL 的人，都能通过错误信息推断出你的服务器出口 IP。
> 所以 Webhook URL 必须当作**密钥**保管，并且开启平台的 IP 白名单。

### 3.4 为什么需要指纹去重

指标在阈值附近抖动是常态。假设每 5 秒检查一次，一个抖动的指标会这样：

```
92% ✓告警  88% ✗恢复  93% ✓告警  89% ✗恢复  91% ✓告警 ...
```

朴素实现每 5 秒检查一次是否越界 → 半小时发出 **200 条**一模一样的内容。
真实故障会被埋在噪声里，人会开始屏蔽这个机器人 —— **告警系统就此失效**。

解法是引入**指纹（fingerprint）**：

```
fingerprint = sha1(rule | instance | metric)
```

同一指纹在**抑制窗口**（如 30 分钟）内只发一次；恢复时补发一条 RECOVERED。
注意指纹里必须含 `instance` —— `web-01` 和 `web-02` 都爆盘时是两个独立事件。

**本机实测：100 次检查、40 次越界 → 去重后只发 1 条，压缩比 40:1。**

---

## 4. 定义与方法（API 速查）

### 4.1 smtplib

| 成员 | 用途 | 备注 |
|---|---|---|
| `smtplib.SMTP(host, port, timeout=10)` | 明文连接 | **timeout 必设**，否则会永久阻塞 |
| `smtplib.SMTP_SSL(host, port)` | 隐式 TLS（465） | 一上来就加密 |
| `s.ehlo()` | 宣告扩展能力 | `starttls()` 之后要**再调一次** |
| `s.starttls()` | 明文升级为 TLS（587） | 服务器不支持会抛异常 |
| `s.login(user, password)` | 认证 | QQ/163 必须用**授权码**，不是登录密码 |
| `s.send_message(msg)` | 发送（自动处理 MIME） | 推荐用它，而不是 `sendmail` |
| `s.set_debuglevel(1)` | 打印完整会话 | 排查 SMTP 问题的唯一利器 |

**异常分类（决定要不要重试）：**

| 异常 | 含义 | 重试 |
|---|---|---|
| `SMTPServerDisconnected` | 对端断开 | ✅ |
| `SMTPConnectError` | 连不上 | ✅ |
| `SMTPResponseException` 4xx | 临时不可用 | ✅ |
| `SMTPResponseException` 5xx | 永久失败（如 535 认证错） | ❌ |
| `SMTPAuthenticationError` | 认证失败 | ❌ |

### 4.2 email.message.EmailMessage

| 调用 | 用途 |
|---|---|
| `EmailMessage()` | 创建（自动生成 MIME-Version） |
| `msg["Subject"] = "中文"` | 自动 RFC 2047 编码，**不用自己 base64** |
| `msg.set_content("正文")` | 设置纯文本正文 |
| `msg.add_attachment(str, filename=...)` | 文本附件 |
| `msg.add_attachment(bytes, maintype=..., subtype=..., filename=...)` | 二进制附件 |
| `msg.as_bytes()` | 得到完整 MIME 原文 |

> ⚠️ **实测踩坑**：`add_attachment` 的 `maintype/subtype` 是否必填，取决于传什么类型：
>
> | 传入 | 结果（本机 Python 3.12.3 实测） |
> |---|---|
> | `str` + `maintype/subtype` | ❌ `TypeError: set_text_content() got an unexpected keyword argument 'maintype'` |
> | `str` + 不传 | ✅ OK |
> | `bytes` + 不传 | ❌ `TypeError: set_bytes_content() missing 2 required positional arguments` |
> | `bytes` + 显式类型 | ✅ OK |
> | `BytesIO` | ❌ `KeyError: '_io.BytesIO'`（3.12 不支持） |
> | `EmailMessage` | ✅ OK（嵌套邮件） |

### 4.3 三家平台的端点与安全设置

| 平台 | 端点 | 安全设置 | 频率限制 |
|---|---|---|---|
| 钉钉 | `oapi.dingtalk.com/robot/send?access_token=` | 加签 / 自定义关键词 / IP 白名单 | 20 条/分钟 |
| 企业微信 | `qyapi.weixin.qq.com/cgi-bin/webhook/send?key=` | （群机器人） | **20 条/分钟** |
| Slack | `hooks.slack.com/services/T…/B…/…` | — | 约 1 条/秒 |

**钉钉加签算法**（HMAC-SHA256）：

```python
string_to_sign = f"{timestamp}\n{secret}"
sign = base64.b64encode(hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest())
# 然后 sign 要 URL-encode 后作为 &sign= 传参
```

---

## 5. 图解

见 [`diagrams/README.md`](diagrams/README.md)，共 11 张图。核心一张：

```
                        ┌─────────────────────────────────┐
                        │      AlertHub（告警中枢）        │
  Alert(指标+规则+实例) ─▶│                                 │
                        │  1. fingerprint = sha1(r|i|m)   │
                        │  2. 抑制窗口内去重              │
                        │  3. 令牌桶限流（20 条/分钟）     │
                        │  4. 敏感信息脱敏                │
                        └───────────┬─────────────────────┘
                                    │ 按级别扇出
        ┌───────────────┬───────────┼───────────┬───────────────┐
        ▼               ▼           ▼           ▼               ▼
   ┌─────────┐   ┌──────────┐ ┌────────┐ ┌────────┐      ┌─────────┐
   │ 邮件     │   │ 钉钉     │ │企业微信│ │ Slack  │      │ stdout  │
   │ SMTP    │   │ Webhook  │ │Webhook │ │Webhook │      │  兜底   │
   └────┬────┘   └────┬─────┘ └───┬────┘ └───┬────┘      └────┬────┘
        │             │           │          │                │
        │       ┌─────▼───────────▼──────────▼─────┐          │
        │       │  HTTP 200 但 errcode != 0  ← 陷阱 │          │
        │       │  必须判业务层，不能只看状态码     │          │
        │       └───────────────────────────────────┘          │
        │                                                       │
        └──────────── 任一渠道失败都不影响其他渠道 ──────────────┘
                              全失败 → 降级到 stdout
```

---

## 6. 实战实验手册

> 运行环境：**Python 3.12.3 / Linux x86_64 / 2026-10-01**
> 所有实验都可以在你自己机器上复现，不需要真实 IM 机器人、不需要邮箱、不需要外网。
> 唯一的外部依赖是 `psutil`（可选，缺失会自动降级）。

```bash
cd days/day-171-通知告警/code
```

### 实验 1：手写抓包 SMTP 服务器，看清 smtplib 到底发了什么

**目的**：把 SMTP 的多轮会话和 MIME 原文完整打出来。

**准备**：无，纯标准库。

**执行**：

```bash
python3 smtp_capture_server.py --self-test          # 先跑离线自检
python3 smtp_capture_server.py --port 1025          # 终端 A：启动抓包服务器
python3 01-basic-smtplib.py --port 1025              # 终端 B：发一封带附件的邮件
```

**实际结果**（本机真实输出，已裁剪）：

```
send: 'ehlo [127.0.1.1]\r\n'
  C: ehlo [127.0.1.1]
reply: b'250-capture.local greets you\r\n'
reply: b'250-8BITMIME\r\n'
reply: b'250-SMTPUTF8\r\n'
reply: b'250 SIZE 10485760\r\n'
send: 'mail FROM:<alert@learn-python.dev> size=635\r\n'
  C: mail FROM:<alert@learn-python.dev> size=635
    [envelope sender] alert@learn-python.dev
send: 'rcpt TO:<niedong@learn-python.dev>\r\n'
  C: rcpt TO:<niedong@learn-python.dev>
    [envelope rcpt] niedong@learn-python.dev
send: 'data\r\n'
  C: data
reply: b'354 End data with <CR><LF>.<CR><LF>\r\n'
data: (354, b'End data with <CR><LF>.<CR><LF>')
send: b'From: alert@learn-python.dev\r\nTo: niedong@learn-python.dev\r\n
  Subject: [P1] =?utf-8?b?5pWw5o2u5bqT56OB55uY5L2/55So546H?= 91%\r\n
  MIME-Version: 1.0\r\nContent-Type: multipart/mixed;
  boundary="===============5168995940432228121=="\r\n\r\n
  --===============5168995940432228121==\r\n
  Content-Type: text/plain; charset="utf-8"\r\n
  Content-Transfer-Encoding: 8bit\r\n\r\n
  \xe7\xa3\x81\xe7\x9b\x98...\r\n
  --===============5168995940432228121==\r\n
  Content-Type: text/plain; charset="utf-8"\r\n
  Content-Disposition: attachment; filename="app.log"\r\n\r\n
  log line 1\r\nlog line 2\r\n
  --===============5168995940432228121==--\r\n.\r\n'
reply: b'250 2.0.0 Ok: queued as CAPTURED\r\n'
reply: retcode (250); Msg: b'2.0.0 Ok: queued as CAPTURED'
send: 'quit\r\n'
=== captured: 1 size: 635 B ===
```

**结论**：
- 中文主题被自动编码成 `=?utf-8?b?...?=`（RFC 2047），不用手写；
- 带附件时顶层变成 `multipart/mixed`，boundary 由库生成；
- `MAIL FROM` 带了 `size=635` 这个 ESMTP 参数 —— 这正是翻车实验 1 的根源。

**清理**：终端 A 按 `Ctrl-C`；或直接 `python3 smtp_capture_server.py --self-test`（自检用的是临时端口，跑完自动关闭）。

---

### 实验 2：⭐ 真连官方端点，证明「HTTP 200 但业务失败」

**目的**：用一个**故意写错的 token** 打出真实的生产环境响应，验证本课最重要的结论。

**环境**：需要外网。**不会打扰任何人**（token 是假的，请求必然被拒）。

**执行**：

```bash
python3 02-webhook-notify.py --probe
```

**实际结果**（本机真实输出，2026-10-01 06:11 CST）：

```
说明：下面用的是【故意写错的 token】，不会打扰任何人，
      目的只是真实演示「HTTP 200 但业务失败」。

钉钉     -> [dingtalk] ok=False http=200 errcode=300005 errmsg='token is not exist' elapsed=163ms attempts=1
         ^^^ 铁证：HTTP 200 却是失败，errcode=300005

企业微信   -> [wecom] ok=False http=200 errcode=93000 errmsg='invalid webhook url, hint: [1790806079345572489457392], from ip: 119.145.35.9, more info at https://open.work.weixin.qq.com/devtool/query?e=93000' elapsed=209ms attempts=1
         ^^^ 铁证：HTTP 200 却是失败，errcode=93000

Slack   -> [slack] ok=False http=404 errcode=404 errmsg='no_team' elapsed=363ms attempts=1
```

**结论**：
- 钉钉和企业微信的失败**都是 HTTP 200**，只写 `raise_for_status()` 的代码会把它们全部当成功；
- Slack 的语义不同 —— 失败直接是 4xx，且 body 是纯文本不是 JSON，不能无脑 `.json()`；
- 顺带发现一个安全问题：企业微信的报错**回显了本机出口 IP**。

**清理**：本实验不产生任何本地状态，无需清理。

---

### 实验 3：离线复现「HTTP 200 + errcode 失败」并验证降级

**目的**：把实验 2 的现象做成可离线重放的自动化断言。

**执行**：

```bash
python3 02-webhook-notify.py --self-test
python3 04-alert-hub.py --self-test
```

**实际结果**（本机真实输出）：

```
OK 正常发送: [dingtalk] ok=True http=200 errcode=0 errmsg='ok' elapsed=3ms attempts=1
OK 核心陷阱: HTTP 200 但 errcode=300005 被正确识别为失败 -> [dingtalk] ok=False http=200 errcode=300005 errmsg='token is not exist' elapsed=2ms attempts=1
OK 限流退避: 重试 3 次，总耗时 308ms（>=300ms）-> [wecom] ok=False http=200 errcode=45009 errmsg='接口调用超过限制' elapsed=4ms attempts=3
OK 永久错误不重试: 5 次 retries 配置下实际只发 1 次
OK Slack 语义不同: 4xx 判失败且不解析 JSON -> [slack] ok=False http=404 errcode=404 errmsg='no_service' elapsed=2ms attempts=1
OK 钉钉加签确定性: timestamp=1700000000000 sign=Orf%2Bfj1NyYtycFhdVp...
OK 钉钉自定义关键词自动注入正文（否则 errcode=310000 拒收）
SELFTEST PASS
```

告警中枢的全渠道降级：

```
--- 5. ⭐ 全渠道 HTTP 200 + errcode 失败 -> 必须识别并降级 ---
  OK 3 渠道全部失败 -> 自动降级到 stdout；errcode 300005 被正确识别为失败
      (若只看 HTTP 状态码，这里会被误判成成功 —— 就是那个致命陷阱)
```

**结论**：传输层 + 业务层双重判定；限流类错误才退避重试，永久错误立刻放弃（避免重试风暴）。

**清理**：`--self-test` 用的都是内核分配的临时端口，进程退出即释放。

---

### 实验 4：告警风暴压测 —— 实测去重与限流的收益

**目的**：量化指纹去重和令牌桶到底省了多少。

**执行**：

```bash
python3 04-alert-hub.py --storm
```

**实际结果**（本机真实输出）：

```
压测：注入 500 个抖动事件，观察去重与限流效果
  注入事件    : 600 条（500 条 CPU 抖动 + 100 条磁盘抖动）
  最终发送    : 21 条
  被抑制      : 579 条
  恢复通知    : 0 条
  总耗时      : 1031ms  (平均每条 1.72ms)
  实际 HTTP 请求: 63 次   实际 SMTP: 21 封
```

**结论**（测试条件：600 个事件 / 20 个实例 / 本机单进程 / 单次运行）：

| 指标 | 朴素实现 | AlertHub | 收益 |
|---|---|---|---|
| 收到的告警事件 | 600 | 600 | — |
| 真正发出的通知 | 600 × 4 渠道 ≈ 2400 | **21** | **压低 99.1%** |
| 实际 HTTP 请求 | 2400 | **63** | 压低 97.4% |
| 平均处理耗时 | — | 1.72 ms/事件 | 告警本身不该成为性能瓶颈 |

21 条 = 20 个 CPU 节点各 1 条 + `web-01` 磁盘 1 条。

---

### 实验 5：9 个陷阱全离线复现

**执行**：

```bash
python3 03-pitfalls.py --self-test
python3 03-pitfalls.py --only 5      # 只看某一个
```

**实际结果**（节选，本机真实输出）：

```
【陷阱 1】HTTP 200 ≠ 成功（errcode 在 body 里）
  HTTP 状态码      = 200
  body.errcode     = 300005  (token is not exist)
  天真写法判断成功? = True   <-- 错！
  正确写法判断成功? = False   <-- 对

【陷阱 2】重试风暴：永久错误也重试
  天真写法（永久错误也重试 5 次）-> 实际发出 5 次请求
  正确写法（识别为永久错误）      -> 实际发出 1 次请求

【陷阱 4】告警风暴：缺少指纹去重
  100 次检查中越界 40 次
  天真写法     -> 发出 40 条告警
  指纹去重     -> 发出 1 条，抑制 39 条 (压缩比 40:1)

【陷阱 5】SMTP 不设 timeout 卡死告警线程
  天真（无 timeout）: 仍在阻塞（线程卡在等 220 欢迎语）, 等待 3.0s 后依然没返回
  正确（timeout=0.3）: SMTPServerDisconnected, 耗时 301ms

【陷阱 8】忽略平台频率限制
  100 次调用，桶容量=5 -> 立即放行 5 次，剩余 95 次被延迟
```

**结论**：陷阱 5 的对照最有说服力 —— 不设 timeout 时线程**3 秒后依然卡在等欢迎语**，
而这在生产里意味着告警线程池被慢慢耗尽，且你不会收到任何错误。

---

### 实验 6：告警风暴 -> 恢复的完整闭环（真实指标）

**执行**：

```bash
python3 04-alert-hub.py --demo
```

**实际结果**（本机真实输出）：

```
演示：磁盘告警触发 -> 抖动 -> 恢复
* 真实指标: 磁盘 43.2%  CPU 12.5%  内存 32.1%
[AlertHub] SUPPRESSED 5fa27966b740a126 (0s < 1800s)
[AlertHub] RECOVERED 5fa27966b740a126
[AlertHub]   OK  email      46.0ms
[AlertHub]   OK  dingtalk   1.1ms  errcode=0 errmsg=ok
[AlertHub]   OK  wecom      0.8ms  errcode=0 errmsg=ok
[AlertHub]   OK  slack      1.4ms  HTTP 200

统计: {'received': 6, 'sent': 2, 'suppressed': 3, 'recovered': 1, 'channel_fail': 0, 'fallback': 0}
```

**结论**：6 个事件 → 只发 2 条通知（1 条真实告警 + 1 条恢复），3 条抖动被抑制。
RECOVERED 事件**不受抑制窗口限制**，保证故障闭环可见。

---

## 7. 翻车实验记录

> 教材里最值钱的部分 —— 以下都是本课编写过程中**真实踩过**的坑。

### 翻车 1：`MAIL FROM` 里的 ESMTP 参数

- **现象**：抓包服务器的 `--self-test` 断言失败：
  `AssertionError: selftest@learn-python.dev> size=246`
- **假设**：`partition(":")` 之后全是地址 —— 显然不对。
- **验证**：打印真实 SMTP 报文，看到 `mail FROM:<alert@learn-python.dev> size=635`
- **真实根因**：SMTP 的 `MAIL FROM` 语法是 `<address> [参数...]`，
  参数区与地址用**空格**分隔。`size=` 是客户端预告正文大小（`8BITMIME` 场景下还会有 `BODY=8BITMIME`）。
  天真实现取了冒号后的全部内容。
- **修复**：先 `rest.strip().split(" ")[0]` 切掉参数区，再剥尖括号。
- **复测**：`SELFTEST PASS`。

**教训**：任何形如 `VERB:<something> [params]` 的协议行，都要先读 spec 再写 parser。

### 翻车 2：`add_attachment` 的参数矩阵

- **现象**：连踩 3 次不同报错。
- **根因**：`add_attachment` 内部走 `email.contentmanager`，
  它按传入对象的类型分派到不同的 setter，而 `maintype/subtype` 对不同 setter 的意义不同。
- **验证**：写了个 6 格的矩阵探针，把每种组合的真实异常都打出来：

  | 传入 | 真实结果 |
  |---|---|
  | `str` + `maintype/subtype` | `TypeError: set_text_content() got an unexpected keyword argument 'maintype'` |
  | `str` + 不传 | OK |
  | `bytes` + 不传 | `TypeError: set_bytes_content() missing 2 required positional arguments: 'maintype' and 'subtype'` |
  | `BytesIO` + `text/plain` | `KeyError: '_io.BytesIO'` |
  | `BytesIO` + `application/octet-stream` | `KeyError: '_io.BytesIO'` |
  | `EmailMessage` | OK |

- **修复**：文本附件传 `str`，二进制附件传 `bytes` + 显式类型。
- **复测**：附件邮件 `multipart/mixed` 生成成功，644B。

### 翻车 3：`python -m smtpd` 在 Python 3.12 已经不存在

- **现象**：想用标准库的 `DebuggingServer` 做实验，`import smtpd` 直接 `ModuleNotFoundError`。
- **根因**：**PEP 594** 在 Python 3.12 移除了大量废弃模块，`smtpd` 正在其中
  （同批还有 `cgi`、`telnetlib`、`nntplib` 等）。
- **验证**：`python3 -c "import smtpd"` → `ModuleNotFoundError: No module named 'smtpd'`
- **修复**：不再依赖任何第三方库，改用 `socketserver` 手写 ~80 行抓包服务器。
  顺带也用 `pip install --target /tmp/xxx aiosmtpd` 装了一份**独立交叉验证**，
  确认我实现的协议行为与官方库一致（而非自定义了一个假服务器骗自己）。
- **复测**：自检通过，且 `--probe` 打到了真实官方端点。

### 翻车 4：自检脚本把自己跑死了

- **现象**：跑 `03-pitfalls.py --self-test` 时进程**永远不返回**，只能强杀。
- **假设**：陷阱 5 里那个"黑洞 SMTP 服务器"（accept 后永不回应 `220`）
  配上不设 timeout 的 `smtplib.SMTP`，会**永久阻塞**。
- **验证**：确实是它。而且这恰好**就是陷阱本身** —— 我为了演示这个坑，被这个坑绊倒了。
- **根因**：主线程直接调用阻塞 API，而 `join()` 无上限。
- **修复**：把天真写法放进 `daemon=True` 的线程，用 `join(timeout=3.0)` 限定等待，
  超过就报告"仍在阻塞"——既保住了实验的对比效果，又不会卡死测试。
- **复测**：陷阱 5 输出"等待 3.0s 后依然没返回"，对比组 301ms 抛 `SMTPServerDisconnected`。

### 翻车 5：`pkill -f` 杀掉了自己

- **现象**：`pkill -f "03-pitfalls.py"` 之后，当前 shell 报 `Command aborted by signal SIGTERM`。
- **根因**：`pkill -f` 匹配**完整命令行**，而我自己的 `bash -c` 命令行里就含这个字符串 → 自杀。
- **修复**：用字符类打断字面量 —— `pkill -f "03-pitfalls[.]py"`，正则匹配到的字符串与自身命令行不匹配。
- **复测**：`pgrep -cf '03-pitfalls[.]py'` 返回 0。

### 翻车 6：断言里的数字是"想当然"，不是实测

- **现象**：三处断言挂在自己的假设上：
  1. 断言"100 次检查中越界 > 50 次" —— 实测是**恰好 40 次**；
  2. 断言"`web-02` 独立发送后 hits == 6" —— 忘了前面恢复事件已产生 3 次，实测是 **9**；
  3. 断言"桶容量 20 就放行 20 次" —— 实测放行 **21** 次。
- **根因**：先写断言再想结果。
- **验证**：第 3 条尤其值得说 —— 令牌桶是**持续补充**的，被拦下的 19 次调用每次 sleep ~50ms，
  1 秒多时间里又回充了 ~0.33 个令牌，于是挤出了第 21 个。**这是正确行为，不是 bug。**
- **修复**：把断言改成真实语义（第 3 条放宽为 `20 <= allowed <= 22` 并在注释里解释为什么）。
- **复测**：全部通过。

**教训**：压测类实验里，**先跑出数字，再写断言**。反过来就是在给自己写 bug。

---

## 8. API 速查与对比

### 8.1 发送方式横向对比

| 方案 | 延迟 | 可靠度 | 成本 | 适合 |
|---|---|---|---|---|
| `smtplib` 直连 | 秒级 | 高 | 0 | 详细报告、留档 |
| 钉钉机器人 | 毫秒 | 中（有严格限流） | 0 | 国内团队即时通知 |
| 企业微信 | 毫秒 | 中（20 条/分钟） | 0 | 已在用企微的团队 |
| Slack | 毫秒 | 中 | 0 | 海外团队 |
| 云监控（阿里云/腾讯云） | 秒级 | 高 | 付费 | 托管服务 |
| AlertManager | 秒级 | 高 | 需自建 | Prometheus 生态 |

### 8.2 成功判定方式对照（**最容易搞错的一张表**）

| 平台 | 传输层成功 | 业务层成功 | 危险写法 |
|---|---|---|---|
| 钉钉 | HTTP 200 | `errcode == 0` | ❌ 只看 200 |
| 企业微信 | HTTP 200 | `errcode == 0` | ❌ 只看 200 |
| Slack | 2xx | body `ok` | ❌ 无脑 `.json()` |
| SMTP | 收 `250` | 无异常 | ❌ 不设 timeout |

---

## 9. 代码清单

| 文件 | 说明 | 运行 |
|---|---|---|
| `code/smtp_capture_server.py` | 手写抓包 SMTP 服务器（纯标准库） | `python3 smtp_capture_server.py --self-test` |
| `code/01-basic-smtplib.py` | 邮件基础 / 附件 / TLS / 重试 | `python3 01-basic-smtplib.py --self-test` |
| `code/02-webhook-notify.py` | 三平台 Webhook 统一封装 | `python3 02-webhook-notify.py --self-test`<br>`--probe` 真连官方 |
| `code/03-pitfalls.py` | 9 个陷阱，全部离线可复现 | `python3 03-pitfalls.py --self-test` |
| `code/04-alert-hub.py` | 实战：多渠道告警中枢 | `python3 04-alert-hub.py --self-test`<br>`--demo` `--storm` |

**全部 5 个脚本都带 `--self-test`，离线、零外部依赖可跑通。**

---

## 10. 思考题

1. **本课实验 2 证明 HTTP 200 可能失败。** 如果让你审查团队现有的告警代码，
   你会用什么手段在最短时间内找出所有"只看状态码"的地方？
   （提示：与其 review 代码，不如让它自己暴露 —— 故意把 token 写错，跑一周看有没有告警。）

   **参考答案**

   核心思路：不靠人眼 review，靠"故障注入"——故意让发送失败，看谁还在报"成功"。

   - **故意写错 token 跑一周**：把测试群的 webhook token 改成错误值（钉钉/企业微信会返回 HTTP 200 + `errcode≠0`）。一周后如果没有任何失败告警，说明这条代码路径只看状态码。这是最快的"让它自己暴露"手段。
   - **本地 mock 服务器离线复现**：用标准库 `http.server` 起一个假 webhook，固定返回 `200` + `{"errcode": 310000, "errmsg": "token is not exist"}`，把告警代码指向它，看它判定成功还是失败——不用等一周，几分钟出结果。
   - **静态扫描缩小范围**：`grep -rn "status_code" 告警模块/`，逐处检查附近有没有 `raise_for_status()` 或解析响应体 `errcode` 的逻辑；用 `requests` 的代码重点看只写了 `if resp.status_code == 200` 就 return 的地方。
   - **用单元测试固化**：给每个发送函数补一条"200 + errcode≠0 必须判定失败"的测试用例放进 CI，以后新写的"只看状态码"代码会立刻红灯。

   ⚠️ 注意：故障注入要在测试群/预发环境做，别把生产告警通道的 token 故意改坏。

2. **`fingerprint` 里我用了 `rule|instance|metric`。**
   如果规则改成"5 分钟内失败率 > 1%" 这种**时间窗口**型指标，
   去重逻辑要怎么调整？为什么纯指标值去重在窗口型规则上会失效？

   **参考答案**

   去重键只能是"身份"，不能是"数值"。fingerprint 仍应保持 `rule|instance|metric`（哪条规则、哪个实例、哪个指标），不要把失败率的具体数值或时间窗口拼进去。

   - **为什么按值去重会失效**：窗口型指标的数值一直在变——10:00 失败率 1.2%，10:01 变 1.5%，10:02 变 1.1%。若按"值"去重，每次变化都被当成新告警，一场事故刷出几十条消息；反过来，如果数值恰好回到之前出现过的数（比如又变成 1.2%），会被误判为"发过了"而吞掉，可故障其实一直在持续。两个方向都错。
   - **正确做法是状态机**：每个 fingerprint 维护一个状态 `OK → FIRING（告警中）→ RECOVERED（已恢复）`。第一次越过阈值发 FIRING；之后只要状态还是 FIRING，无论数值怎么变都不再重发；直到指标回落到阈值以下（且通过去抖确认），发一条 RECOVERED 并把状态复位。
   - **怕被遗忘就用 repeat_interval**：对长期 FIRING 的事故，每隔固定时间（如 4 小时）重发一次提醒，而不是靠数值变化触发。AlertManager 的 `group_by` + `repeat_interval` 就是这个思路。

   一句话总结：按值去重回答的是"这个数出现过没有"，而告警去重要回答的是"这场事故还在不在"——两者不是一回事。

3. **RECOVERED 事件我让它绕过了抑制窗口。**
   设想一个场景：服务持续抖动（反复 firing/recovering），
   这个设计会不会反过来变成"恢复通知刷屏"？你会怎么修？

   **参考答案**

   会。RECOVERED 绕过抑制窗口对"一次性故障"是合理的，但服务持续抖动时（每分钟越线又回落），每个周期都发一条 firing + 一条 recovered，一小时抖 10 次就是 20 条消息——恢复通知反而成了新的刷屏源。

   修法（可组合使用）：

   - **恢复去抖（debounce）**：指标必须连续 N 个采样周期（如 3 次 / 5 分钟）低于阈值才发 RECOVERED。瞬时回落不算恢复，能滤掉大部分抖动。
   - **滞回阈值（hysteresis）**：触发和恢复用两条不同的线——失败率 > 1% 触发告警，但要降到 < 0.5% 才算恢复。指标在 0.6%~0.9% 之间震荡时不会反复翻转状态。
   - **抖动聚合**：同一 fingerprint 在窗口内（如 10 分钟）状态翻转超过 M 次（如 3 次），就不再逐条发 firing/recovered，而是合并成一条"服务持续抖动"告警，提示人工介入查根因。
   - **给 RECOVERED 也加最小间隔**：恢复通知可以绕过"告警抑制窗口"，但应有自己的短冷却期（如同一 fingerprint 5 分钟内最多 1 条），不能彻底不设防。

   💡 提示：Prometheus 规则里的 `for` 持续时长 + 滞回阈值设计，就能在告警源头实现"恢复去抖"，不必全靠通知层兜底。

4. **令牌桶容量设为"一分钟的量"（20）。**
   这个取值合理吗？如果是"凌晨 3 点全集群同时崩"（20 个实例同时告警），
   你的桶会把它们全部立刻放行吗？跨过 20 条之后会发生什么？
   你需要什么样的降级策略？

   **参考答案**

   容量 20 是合理的——令牌桶的本质是"允许短时突发、限制长期平均速率"，一分钟内同时来 20 条正是桶应该吸收的突发，所以 20 个实例同时告警会被全部立刻放行（这是特性不是 bug）。但"全集群同时崩"往往不止 20 条，超出容量的部分就要排队。用标准库模拟一下（不真发消息，用虚拟时钟计算排队时间）：

   ```python
   CAPACITY = 20                 # 桶容量 = 一分钟的配额（20 条）
   RATE = 20 / 60                # 每秒补充的令牌数：20 条/分钟 = 每 3 秒 1 个
   tokens = CAPACITY             # 初始满桶
   wait = 0.0                    # 虚拟时钟：排队告警的累计等待秒数
   immediate = 0

   for i in range(1, 26):        # 凌晨 3 点，25 条告警同时到达
       if tokens >= 1:           # 桶里有令牌：立刻放行
           tokens -= 1
           immediate += 1
       else:                     # 桶空了：排队，每 3 秒补 1 个令牌
           wait += 1 / RATE
           print(f"告警{i:2d}: 桶空，排队 {wait:.0f} 秒后才发出")

   print(f"前 {immediate} 条立即放行，其余排队，最后一条延迟 {wait:.0f} 秒")
   ```

   实际运行输出：

   ```text
   告警21: 桶空，排队 3 秒后才发出
   告警22: 桶空，排队 6 秒后才发出
   告警23: 桶空，排队 9 秒后才发出
   告警24: 桶空，排队 12 秒后才发出
   告警25: 桶空，排队 15 秒后才发出
   前 20 条立即放行，其余排队，最后一条延迟 15 秒
   ```

   可见跨过 20 条后每条多等 3 秒；如果同时来 200 条，最后一条要延迟 (200-20)×3 = 540 秒 = 9 分钟——告警送到时事故都凉了，这不可接受。所以需要降级策略：

   - **先聚合再发送**：同一规则、同一时间窗的告警合并成一条（"20 个实例全部不可用"），200 条变 1 条，令牌桶就不再是瓶颈。
   - **优先级队列**：P0（全集群不可用）插队或走独立通道，P2（单盘预警）可以延后甚至丢弃。
   - **备用通道**：排队深度超过阈值时自动切换到短信/电话等不受 webhook 频率限制的通道。
   - **队列本身也要告警**："积压了 N 条告警发不出去"本身就是最高优先级事故，不能让它在队列里静默过期。

5. **最难的题**：告警系统本身挂了怎么办？
   你的告警中枢进程 OOM 了，或者它依赖的 SMTP 服务器挂了，
   **谁来通知你"告警系统挂了"**？
   （提示：思考一下"最后一道防线"应该是什么形态 —— 是不是应该有一份告警，
   其送达路径与其他所有告警**完全独立**？）

   **参考答案**

   这就是"谁来监督监督者"的问题。答案：最后一道防线不能依赖被监控系统自身的任何组件，要做一个完全独立的"死人开关"（dead man's switch，即"持有者失去行动能力就自动触发"的机制）。

   - **外部心跳监控**：告警中枢每分钟向一个独立的第三方服务（如 Healthchecks.io，或另一台机器上的定时任务）发送心跳。第三方的逻辑是反的："收不到心跳"才告警——进程 OOM、机器断电、网络中断，只要心跳停了，它就用自己的渠道（短信/邮件/电话）通知你。它不依赖你的 SMTP，也不依赖你的进程活着。
   - **常燃看门狗告警（Watchdog）**：AlertManager 的经典做法——配置一条永远处于 firing 状态的 Watchdog 告警，持续发往外部接收器。外部接收器监控的是"这条告警怎么不来了"：一旦停止，说明 Prometheus → AlertManager 整条链路挂了。
   - **送达路径完全独立**：看门狗的通知通道必须与主告警分开——主通道走自建 SMTP，看门狗就走云短信 API；部署在不同机器/不同可用区，避免"一次 OOM 全家带走"。
   - **元监控（meta-monitoring）**：用第二套轻量监控（或云厂商的拨测服务）盯第一套监控，形成互相监督。成本很低，因为看门狗只需回答一个二值问题："它还活着吗"。

   💡 提示：检验标准是——假设告警中枢、它依赖的 SMTP、甚至它所在的机器同时挂掉，还有没有一条路径能给你发出消息？有，那条路径才是最后一道防线。

---

## 11. 延伸阅读方向

- Prometheus AlertManager：`group_by` / `repeat_interval` / 静默（silence）/ 抑制规则（inhibition）
- SMTP RFC 5321（协议）· RFC 2047（标题编码）· RFC 2046（MIME）
- 钉钉/企业微信机器人官方文档的「频率限制」与「IP 白名单」章节
- 抖动与去抖：`hysteresis`（滞回阈值）—— 比固定抑制窗口更优的方案
