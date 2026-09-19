# Day 160 — 日志安全分析：格式标准化 · 异常登录 · 暴力破解识别

> **Phase 10 — 网络安全开发（Day 146–165）** · 主题：日志安全分析（实战）
>
> **使用边界（重要）**：本课只分析**你自己拥有或已获书面授权**的日志。
> 分析器**只读**日志文件：不修改、不删除、不重写日志，**不发起任何网络请求**，
> 不构造任何攻击或验证请求（发现"目录穿越探测"时只记录日志事实）。
> 教材中的 IP 一律取自文档专用网段（203.0.113.0/24、198.51.100.0/24、192.0.2.0/24），
> 账号均为占位名。

## 1. 学习目标

完成本课后，你应该能够：

- 把异构日志（sshd syslog / nginx combined / 应用 JSON）**标准化**成统一事件模型
- 说清"为什么时间戳缺失 / 不可解析时不能猜时间"，以及它对结论的影响
- 用**滑动窗口**识别单源暴力破解，并解释它为什么优于"按分钟分桶"
- 识别**分布式爆破**（每个来源都低于单源阈值），并理解它的置信度为何只能是 medium
- 用 `(host, user, src_ip)` 关联"失败后成功"，并说清跨主机/跨来源关联会造成什么误报
- 明确"**零告警 ≠ 没有攻击**"：报告必须回显阈值、声明覆盖缺口、标注可判定性
- 把日志分析接进 CI：退出码 0/2/3/4 的语义与优先级

## 2. 概念解释

### 2.1 安全日志分析在做什么

安全日志分析 = **把"发生过什么"从异构文本里抽出来，再用行为模式找出可疑序列**。

它天然分三段，而且每段的失败模式完全不同：

| 阶段 | 输入 → 输出 | 典型失败模式 |
|---|---|---|
| **解析 / 标准化** | 文本行 → `LogEvent` | 格式变了、编码错了、时间戳没了 → 后续全部失真 |
| **检测** | 事件序列 → `Alert` | 阈值太宽（漏报）/ 太窄（误报）、跨主体混淆 |
| **报告 / 判定** | `Alert` → 结论 | 覆盖不全却写"未发现异常"、阈值不回显导致结论不可复核 |

**把这三段混在一起写，是日志分析脚本最常见的结构问题**：
一旦"某个格式解析失败"，你会误以为"检测逻辑有问题"，从而在错误的地方调参数。

### 2.2 标准化（normalization）到底做了什么

标准化不是"把日志读进来"，而是做四件事：

1. **字段统一**：`ip` / `src_ip` / `client_ip` → `LogEvent.src_ip`
2. **语义统一**：`Failed password` / `Authentication failure` / `login_failed`
   → `action="login_failed"`（动作词表）
3. **时间统一**：全部解析成**带时区**的 `datetime`，比较前统一到同一时区
4. **来源统一**：记录这条事件来自哪种日志（`source=sshd/nginx/app`），
   因为不同来源的可信度与解读方式不同

为什么要做？因为**检测逻辑只能写一遍**。三种日志各写一套检测，
意味着三个地方会各自出 bug。

### 2.3 时间戳：不猜是纪律，不是洁癖

窗口类检测（"5 分钟内失败 10 次"）**必须**有时间。日志里常见的三种情况：

```text
Sep 19 06:12:01 ...        ← syslog：没有年份、没有时区（必须显式假设）
19/Sep/2026:06:12:01 +0800 ← nginx：完整，带偏移
{"event": "login_failed"}  ← 应用日志：干脆没有时间字段
```

对第二种可以精确解析；第一种要提供一个显式的假设（年 + 时区）并在报告里说明；
第三种**不能猜**：把文件修改时间填进去，会让"攻击窗口"变成一个编造出来的数字，
比缺失更有害——因为它看起来像证据。

所以本课实现的是：`ts=None` 保留事件（它的**存在**是事实），
但所有窗口类检测器通过 `_timed()` 过滤掉它，同时 `coverage.no_timestamp` 计数，
报告里必须声明"这部分无法参与判定"。

### 2.4 时间窗口：滑动窗口 vs 分桶

**按分钟分桶**（`00:59` 一个桶、`01:01` 一个桶）看起来更简单，但给攻击者
留了一个免费的规避手法：把 9 次尝试均摊到相邻两桶（各 4～5 次），
两桶都低于阈值，攻击完全隐形。

**滑动窗口**问的是"任意 W 秒内最多多少次"，无法靠对齐边界躲开：

```text
       ┌────────── W = 300s ──────────┐
 ● ● ● ● ● ● ● ● ● ●  ...
 ↑                                ↑
 left                           right
 当 right 纳入新事件时，弹出所有 (right - left) > W 的旧事件，窗口内计数即"任意 W 秒内"的次数
```

代价是：滑动窗口计算量更大（O(n) 均摊，用 `deque` 实现），
且同一批攻击可能在多个窗口位置被重复计数——所以本实现只取**最大窗口**，
每 `(host, src_ip)` 输出一条告警（而不是每个窗口一条）。

### 2.5 严重度与置信度（沿用 Day 159 的模型）

```text
severity   = 这件事被确认为攻击后的影响
confidence = 只看日志，我们有多确定它是攻击
```

日志检测的置信度天花板很实在：**没有值班表、变更记录、来源情报，
任何检测器都上不了 high**。例如：

- `off_hours_success`（非工作时段成功登录）→ severity=low, confidence=low：
  运维值班、发布窗口、跨时区同事会产生大量正常夜间登录
- `failed_then_success`（失败后成功）→ severity=high, confidence=medium：
  可能是本人连错口令后输对，也可能是爆破得手；**必须人工确认**
- `brute_force_single_source` → high/high：
  短窗口内高频失败，加上"成功登录"这一跳才是确定失陷；失败本身几乎不可能是正常行为

`priority = (severity+1) × (confidence+1)`，分档 `P0/P1/P2/P3`。

### 2.6 主体键（subject key）：跨主机混淆

统计键必须是 `(host, src_ip)` / `(host, user)`，不能只用 `src_ip` 或 `user`：

```text
web01: admin ← 203.0.113.7  失败 6 次
web02: admin ← 203.0.113.7  失败 6 次

按 src_ip 聚合      → 12 次 → "同一台机器被打 12 次"（不存在的场景，假告警）
按 (host, src_ip)   → 6 次 + 6 次 → 两条独立事实
```

同理 `admin@web01` 与 `admin@web02` 可能是完全不同的人（本地账号、不同域）。

## 3. 原理解释

### 3.1 为什么"去重"必须做，而且不能去重过头

日志重采、轮转边界、多份拷贝合并都会产生**完全相同的行**。
不去重会让计数虚高（把阈值冲爆），产生假告警。所以去重键取
`(ts, host, action, user, src_ip, status, path)` —— 完全一致才算重复。

但去重键**不能**放宽到"同一秒同一 IP 就算重复"：同一秒内来自同一 IP 的
两次失败是两条真实事实（并发爆破很常见）。宁可留着，也不能吞掉。

### 3.2 为什么乱序必须统计，但不必阻止分析

多主机日志合并后，文件顺序毫无意义（不同机器的时钟、采集器缓冲都会打乱顺序）。
正确做法是**排序后再统计**，所以乱序本身不会让检测出错。

但它仍然值得报告：高比例乱序意味着"日志来源被清洗/拼接/时间被调整过"，
这在取证场景里是需要解释的事实。

### 3.3 为什么"分布式爆破"是必须单独写的检测器

单源规则抓的都是"一个来源很努力地打"。真实攻击常做的是
**每个来源都很克制**：

```text
198.51.100.{1..5} 各失败 3 次 → 单源规则（阈值 8）全部 ✗
按 (host, user) 聚合：600s 内 15 次失败，5 个来源 → 命中
```

它的置信度只能是 medium，因为**共享出口 IP / NAT / 代理池**也会长成这样：
一个公司 100 个员工从同一个出口登录失败，看起来就像分布式爆破。

这条规则真正的作用是：**在报告里承认"我看见了这件事"**，
而不是判定它是攻击。

### 3.4 为什么"失败后成功"要限死 host + user + ip

如果把关联条件放宽成"同账号失败若干次 + 同账号成功"（忽略来源），
那么任何人在任何 IP 上连错 3 次，随后换个网络正常登录，都会变成 P0 告警。
把三个维度全部限死后，语义才准确：**同一条链路上的同一个人/程序**。

这也是检测器的通用教训：**关联条件每放宽一维，误报都会成倍增长**。

### 3.5 为什么报告要回显参数

"没有告警"这句话，在下面两种情况下含义完全不同：

```text
brute_threshold = 8   → 300 秒内 8 次失败会告警；没告警 ≈ 确实很安静
brute_threshold = 50  → 几乎不可能告警；没告警 ≈ 什么都不能说明
```

不写参数的报告，让读者无法区分"没攻击"与"阈值太宽"。
所以 `AlertReport.parameters` 会回显实际使用的每一个阈值，
Markdown 报告里还有专门的"检测参数"段，并标注"默认"还是"本次自定义"。

### 3.6 为什么覆盖缺口优先于告警（退出码 4 > 3）

CI 门禁的价值是**可信**。当有 20% 的日志行无法解析、或有 500 条事件没有时间戳时，
"未发现异常"这句话本身不成立。此时先修采集/解析，再谈要不要处理告警。

| 退出码 | 含义 | 优先级 |
|---|---|---|
| 2 | 用法错误 / 无输入 | 最高 |
| 4 | 覆盖不全（unparsed / no_timestamp / read_error / 空输入） | 高 |
| 3 | 存在严重度 ≥ `--fail-on` 的告警 | 中 |
| 0 | 覆盖完整且无达标告警 | 低 |

### 3.7 报告脱敏：日志比配置更敏感

日志里除了凭据片段，还有**用户名、内部 IP、访问路径、时间规律**——
这些组合起来就是一份内部资产与作息表。所以：

- `LogEvent` **不含原始行**（需要溯源时用 `ref` 指向 `文件:行号`）
- 报告中的主体 IP 默认**末段掩码**（`203.0.113.x`）
- 每个主体附 `subject_sha` 指纹，用于**跨报告关联同一对象**（掩码后仍可追踪）
- 报告只列输入文件名，不输出绝对路径
## 4. 攻击方式 · 手段 · 原理 → 检测原理

### 4.0 总纲：从"攻击行为"到"一条可检测的信号"

日志检测的推导链条比 Day 159 更长，因为中间多了一层**时间**：

```text
攻击行为          观测痕迹                       特征（主体 + 时间 + 数量）        检测器
口令猜测        「失败」集中出现在一个来源  →  300s 内同源失败 ≥ 8            →  brute_force_single_source
```

四个必须记住的前提：

1. **痕迹是行为的影子，不是行为本身**。一次成功的爆破，在 sshd 日志里留下的**唯一**痕迹就是"一堆失败 + 一次成功"；如果攻击者成功之后清了日志，你就什么都看不到（见 4.7）。
2. **时间窗口是推导出来的，不是拍脑袋定的**（见 4.8）。窗口 ≈ 攻击者达到目的所需时长；阈值 ≈ 正常行为的噪声上沿 × 安全系数。
3. **主体键决定了你能看见什么**。按 `src_ip` 聚合看得见"一台机器被打"，看不见"一个账号被多个来源打"；反过来也一样。**每个检测器都在回答一个特定聚合维度上的问题**（见 2.6）。
4. **每个检测器都有一个"免费"的反制手法**（攻击者改变形态即可绕过），所以检测器必须**成对出现、互相补位**（见 4.9）。

本节按"**攻击形态 → 痕迹 → 特征 → 窗口推导 → 攻击者如何规避 → 检测如何对抗**"六段式展开。

---

### 4.1 SSH 暴力破解（单源定向）

**攻击形态**

针对一个已知账号（`root`、`admin`、`deploy`、`oracle`、`test`）做口令字典攻击。工具化程度最高：`hydra -l root -P rockyou.txt ssh://target`、`medusa`、`ncrack`，或自己写 `paramiko` 脚本循环。

真实环境里的形态是：**持续几分钟到几十分钟、每秒数次到数十次**，全是 `Failed password`，期间可能夹杂 `Invalid user`（说明账号名来自字典）。

**观测痕迹（sshd 会留下什么）**

```text
Sep 19 07:00:00 web01 sshd[1234]: Failed password for invalid user admin from 203.0.113.7 port 51001 ssh2
  │       │       │         │                          │                 │
  │       │       │         │                          │                 └ 源端口（每次不同 → 不能用端口去重）
  │       │       │         │                          └ 源 IP（统计主键之一）
  │       │       │         └ 账号（可能是字典里的假账号）
  │       │       └ 主机名（多主机合并时必须区分，见 2.6）
  │       └ 时间（窗口统计的基础）
  └ 固定前缀（syslog 无年份、无时区 → 需显式假设，见 2.3）
```

关键观测事实：

- `Failed password` 是 sshd **明确记录的安全事件**，不是"日志噪声"；
- 每次尝试**源端口不同**，所以同一秒内可以出现多次失败（并发爆破）——**去重键既不能含端口，也不能放宽到"同秒同 IP 算重复"**（见 3.1）；
- `invalid user admin` 说明**账号名来自字典**（`admin` 在本机不存在），这本身就是强信号。

**特征（检测器看什么）**

```text
主体键：   (host, src_ip)        ← 必须含 host（见 2.6）
事件筛选： action == "login_failed"
窗口：     任意 300s（滑动窗口，见 2.4）
阈值：     ≥ 8 次
```

**窗口与阈值是怎么推导出来的**

- 一个**人**输错口令：3–5 次就会去翻密码本或重置，**不会**在 5 分钟内连错 8 次；
- 一个**自动化脚本**在 5 分钟内通常能打**几百到几千**次（受网络 RTT 与 sshd 的 `MaxStartups` 限流影响）；
- 阈值放在 8 是刻意为"低慢速"留余量：**宁可放过低慢速（由 4.2 兜底），也不要让正常的输错触发告警**；
- 300s 的选取理由：覆盖"手滑 + 重试"的典型节奏，同时短到让攻击者**无法用"每小时 7 次"的节奏长期潜伏**；
- 严重度在 `count >= threshold * 3`（即 ≥ 24 次）时升为 `critical`：**强度本身就是证据**——一个人不可能在 5 分钟内"不小心"输错 24 次。

**攻击者如何规避**

| 规避手法 | 效果 | 代价 |
|---|---|---|
| 降低频率（每 10 分钟 7 次） | 低于任何 300s 窗口阈值 | 攻击周期从分钟级变成月级 |
| 换来源（每打 7 次换一个 IP） | 单源规则失效 | 进入 4.2 的检测面 |
| 打不同账号（每个账号 3 次） | 单账号维度不集中 | 本课的单源规则**恰好**能看见（一个 IP 打多个账号 = 失败总数仍在同一 (host, ip) 上累积） |
| 改用密钥认证接口探测 | 事件形态变为 `Failed publickey` | 本课规则同时匹配 `Failed (?:password\|publickey)`，照样计数 |

**检测如何对抗**

- 主体键选 `(host, src_ip)`：来源维度上的集中**换不掉**——攻击者可以换 IP，但换 IP 就变成"每个 IP 都很安静"，即分布式形态；
- **滑动窗口而不是按分钟分桶**（见 2.4）：让"对齐时间边界"这类规避手法无效，攻击者只能真正降频；
- 与 `failed_then_success` 联动：高频失败本身还不是"失陷"，**失败之后是否有成功**才是关键一跳。

---

### 4.2 分布式爆破 / 撞库（多来源同一账号）

**攻击形态**

口令喷洒（Password Spraying）+ 分布式：用 IP 池、代理链、云主机、被控终端，**每个来源只试几次**，把总量摊薄到任何单源阈值以下。Web 变体：用泄露库里的账号口令组合对登录接口批量尝试（撞库）。

**观测痕迹**

```text
198.51.100.1  →  svc@web01    失败 3 次
198.51.100.2  →  svc@web01    失败 3 次
198.51.100.3  →  svc@web01    失败 3 次
198.51.100.4  →  svc@web01    失败 3 次
198.51.100.5  →  svc@web01    失败 3 次
─────────────────────────────────────────
单源规则（阈值 8）：      **全部不命中**
按 (host, user) 聚合：   600s 内 15 次失败、5 个来源  →  命中
```

**特征**

```text
主体键：  (host, user)      ← 换成"账号"维度，而不是"来源"维度
窗口：    600s（放长，因为摊薄后单源节奏更慢）
阈值：    ≥ 10 次失败
并且：    去重后的来源数 ≥ 3      ← 这条规则的灵魂
```

**窗口与阈值推导**

- 阈值放到 10：聚合之后单看数量已失去量级意义，这条规则真正要看的是**来源数目**这个新维度；
- `min_sources ≥ 3` 是**关键**：1 个来源 15 次 = 4.1 的单源爆破；3 个以上来源打同一账号 15 次 = 摊薄形态。缺了 `min_sources`，它就退化成"任何 10 次失败"，与 4.1 重复且误报更多；
- 600s 比 300s 长：攻击者为了摊薄**必然**拉长时间线，窗口太短就看不见"同一场攻击"的全貌。

**为什么置信度只能是 medium**

共享出口会**长得一模一样**：

- 一个公司 100 人从同一个 NAT 出口登录 → 看起来像"多来源"；
- 多个办公室共用同一个代理池 / 企业 VPN 出口；
- 反向代理 / CDN 把真实客户端 IP 统一成了 CDN 的 IP（`X-Forwarded-For` 没被正确采集时尤其明显）；
- 员工集体改密后集中重登失败。

所以这条告警的正确语义是"**我看见了这件事，请判断**"，而不是"已被攻击"。要把它抬到 `high`，至少还需要三类外部信息：

1. **值班表 / 变更记录**（区分"内部人正常操作"）；
2. **来源情报**（IP 归属、信誉、是否爬虫/代理池）；
3. **认证日志的其它维度**（是否伴随成功登录、是否只打这一个账号、账号覆盖面）。

**规避与对抗**

| 规避手法 | 检测对抗 |
|---|---|
| 每源只打 1–2 次 | 阈值降到 10 仍能看见摊薄后的总量 |
| 只打一个账号 | 本检测器**正好**针对这个维度 |
| 打很多账号、每账号几次 | 落到 4.1 的单源规则（来源维度集中） |
| 伪造 `X-Forwarded-For` | 属于**采集/解析**问题（要配 `%{X-Forwarded-For}i`），**不是检测器问题**——这也是"覆盖缺口优先"的又一个理由 |

---

### 4.3 失败后成功（爆破得手 / 凭据有效）

**攻击形态**

两种截然不同的情况在日志里**长得一模一样**：

1. **攻击成功**：爆破/喷洒最终命中一个弱口令，随后攻击者**用同一来源**登录成功；
2. **同事手滑**：本人连续输错几次，然后输对了。

第 2 种远多于第 1 种——**这就是置信度只能是 medium 的根本原因**，也是这条告警永远需要人工确认的原因。

**观测痕迹**

```text
09:00:00  deploy@web01  ←  192.0.2.9   Failed password      ┐
09:00:01  deploy@web01  ←  192.0.2.9   Failed password      │  同一 host + 同一 user
09:00:02  deploy@web01  ←  192.0.2.9   Failed password      │  + 同一 src_ip
09:00:03  deploy@web01  ←  192.0.2.9   Failed password      ┘
09:00:09  deploy@web01  ←  192.0.2.9   Accepted password   ← 成功
```

**特征**

```text
主体键：  (host, user, src_ip)    ← 三维全限死
窗口：    900s
条件：    同一链路上、成功登录之前的窗口内，失败 ≥ 3 次
```

**为什么必须限死三维（关联条件每放宽一维，误报都成倍增长）**

| 被放宽的维度 | 后果 |
|---|---|
| 去掉 `src_ip`（只看 host+user） | 任何人在任何 IP 上连错 3 次、随后换网络正常登录 → P0 假告警。**这是最常见的写法错误。** |
| 去掉 `user`（只看 host+src_ip） | 同一台跳板机上 A 输错、B 登录成功 → 假关联 |
| 去掉 `host`（只看 user+src_ip） | 用户在多台机器部署，A 机失败 + B 机成功 → 假关联 |
| 窗口放宽到 24h | 早上的失败与晚上的成功被串成一条 → 假告警 |

**窗口 900s 的推导**：正常情况下"输错 → 再输对"的间隔在**秒级到分钟级**（人会立刻重试），15 分钟已经非常宽裕；同时它短于"同一个人在两段不相干时间里的正常登录"，避免把无关事件串起来。

**攻击者如何规避**

- **打完就走，不登录**（把凭据拿去别处用或卖掉）→ 这条链路就断了。此时**只能靠 4.1 的单源高频失败告警兜底**——这就是"检测器必须成对出现"的含义。
- 爆破成功后**立即清日志**（见 4.7）。
- 低频慢速打到凭据后，隔很久才回来登录（超出 900s）。
- 成功的认证方式换成 `publickey`：本课实现按 `action == "login_failed"` 统计，**不区分认证方式**，所以 `Failed publickey` 也计入。这是有意的设计，不是漏洞。

**检测如何对抗**

- 三维限死 → 保准确率；
- 与 4.1 成对 → 覆盖"打完就走"；
- 与 `login_from_unexpected_source` 联动 → 如果成功的来源**不在基线内**，两条告警会同时出现，人工复核时应显著提高其优先级（**这个组合判断本课不自动做**，理由见 10"不会自动处置"）。

---

### 4.4 扫描探测（账号枚举 / 目录穿越 / 认证接口滥用）

扫描是**入侵的前置阶段**，特征是"广撒网、低强度、多目标"，与爆破的"集中、高强度、单目标"正好互补。

**（a）SSH 账号枚举**

形态：用字典猜**用户名**（`Invalid user admin`、`Invalid user oracle`、`Invalid user test`），口令固定或随机。

痕迹：`Invalid user <name> from <ip>`。

检测侧要点：本课把它解析为独立动作 `invalid_user`，**不参与** `brute_force_single_source` 的失败计数（该检测器只统计 `login_failed`）。这是**有意的取舍**，因为 sshd 对不存在的用户会**先记**一条 `Invalid user`，**再记**一条 `Failed password for invalid user`——枚举行为**已经**体现在失败计数里，无需重复计。理解这一点，才不会误判为"枚举没被检测"。

**（b）Web 目录穿越探测**

形态：`GET /static/../../etc/passwd`、`GET /?file=..%2f..%2fetc%2fpasswd`、双重编码 `%252e%252e`（专门绕只解一次码的过滤器）。

痕迹：请求行里出现 `../`、`%2e%2e`、`%252e`。

特征：

```python
pattern = re.compile(r"(\.\./|%2e%2e|%252e)", re.IGNORECASE)
kind == "http" 且 path 命中
```

窗口：**瞬时类**（`window_seconds=0`）——**单次命中就足够了**，因为正常业务请求里**不会**出现规范化后的 `../`。

误报来源：

- 应用**故意**接收相对路径参数（日志查看器、文件管理器）；
- 某些框架把路径规范化**放在日志之后**，于是日志里留下的是原始未规范化路径 → 命中，但**实际已被安全处理**。

> **本课的边界**：只记录"日志里出现了这个特征"，**不构造请求去验证**（那是渗透测试，需要单独授权）。响应码 `404` 只能说明**可能**没读成功，**不能**据此断言"漏洞不存在"。

**（c）Web 认证接口高频失败（撞库）**

形态：对 `/login`、`/api/token`、`/oauth/token` 等接口用大批账号口令组合尝试。痕迹是**同一来源在短时间内产生大量 401/403**。

特征：

```text
主体键：  (host, src_ip)
事件：    kind == "http" 且 status ∈ {401, 403}
窗口：    600s
阈值：    ≥ 20 次
```

**阈值推导**：正常用户输错一次就只会重试一两次，**不会**在 10 分钟内产生 20 次 401；而撞库工具受 HTTP 开销限制，10 分钟内几百到几千次很常见。阈值放 20 同样是"给低慢速留余量"。

误报来源：**前端轮询的错误处理**（Token 过期后疯狂重试刷 401）、**移动端断网重连风暴**、**监控探针/健康检查**打到需要鉴权的接口、**爬虫**。所以给 medium/medium。

**规避与对抗**：攻击者改用**分布式**打 Web 接口（每个 IP 低于 20 次）→ 需要按"接口 + 账号"聚合；改慢 → 需要按天/按周的"低频持久"检测（本课不做，属局限，见第 11 节思考题第 2 题）。

---

### 4.5 横向移动（意料之外的来源 / 新来源登录）

**攻击形态**

拿到一个账号后（尤其是**服务账号**或**有跳板权限的账号**），从**非预期的来源**登录，接着在内网横向移动：跳板机 → 应用机 → 数据库机；同一个账号在**多台主机**上先后出现。

痕迹有两层：

1. **单点层**：`Accepted ... for <user> from <ip>`，而 `<ip>` **不在**该账号已知来源里；
2. **聚合层**：同一账号在**多台主机**上出现（本课的数据模型天然支持，因为主体键含 host）。

**特征（本课 `detect_new_source` 一个函数两种形态）**

```text
有基线（{"host|user": [已知 IP, ...]}）：
      → login_from_unexpected_source    medium / medium   （"来源是否越界"是可判定的布尔问题）
无基线：
      → login_from_single_source        low / low          （"本次范围内只看得到一个来源"的启发式）
```

**为什么"置信度取决于你掌握多少外部信息"**

- 有基线时你问的是"**这个来源是否越界**"——这是一个**可判定**的问题；
- 无基线时你只能问"**我见过这个来源吗**"——而"没见过的来源"在第一次收集日志时**到处都是**（每台新接入的主机、每个出差的人）。所以它只能是 low/low：**它在说"我缺少判断依据"，而不是"有坏事发生"**。

这条设计正好演示了 2.5 的置信度天花板：**没有外部信息，任何检测器都上不了 high**。

**攻击者如何规避**

- 用**已被基线接受的**跳板机作为中转（这正是跳板机的用途，也是基线必须**定期复查**的原因）；
- 用**本来就该出现的**来源 IP 做出口（NAT、多人共用）；
- 把横向移动全部走**免密的 SSH Agent 转发**或**内网 API**，不在 `auth.log` 留下 `Accepted`（只留在应用日志里）→ **单一日志源看不见**，这是本课"只看日志"的核心局限（见 10）。

**检测如何对抗**

- **建立并维护基线**：把"确认过的正常来源"写进 baseline JSON（格式见 6.5），把 low/low 的启发式升级为 medium/medium 的**可判定**检测；
- **定期复查基线**，否则它会变成永久消音器（与 Day 159 的 baseline 同理）；
- 与 `off_hours_success`（见 4.6）叠加：**非工作时段 + 新来源**同时出现时，人工复核优先级应显著提高。

---

### 4.6 非工作时段活动（`off_hours_success`）

**攻击形态**

攻击者（尤其是**内部人员**或已拿到凭据的外部人员）会刻意选择**没有值班、没人看告警**的时段活动：凌晨 2–6 点、周末、节假日。

**痕迹**

```text
Sep 19 03:20:00 web01 sshd[1240]: Accepted publickey for deploy from 192.0.2.20 port 2200 ssh2
```

**特征**

```text
条件：  action == "login_success"
判断：  事件本地时间的小时数 不在 [work_start, work_end) 内
窗口：  瞬时类（0）
```

**为什么 severity 与 confidence 都只能是 low**

运维值班、发布窗口（很多团队在凌晨发布）、跨时区同事、个人加班、定时任务用的服务账号——**都会产生合法的夜间登录**。没有排班表就无法区分"凌晨 3 点登录的是值班的 A 还是攻击者 B"。

所以这条检测器的**真实价值是给人工复核提供上下文**。它的正确用法不是"看到 P3 就去处理"，而是**在另一条更高危的告警旁边作为加权因素**：

```text
[P0] failed_then_success   deploy@web01    ← 已经是高危
[P3] off_hours_success     deploy@web01    ← 加固了"这不是正常上班场景"的判断
```

**时区陷阱（必踩）**：`start_hour/end_hour` 是按 `DEFAULT_TZ`（UTC+8）判断的（实现为 `event.ts.astimezone(DEFAULT_TZ).hour`）。如果日志来自跨时区设备，**必须先统一时区**再判断，否则会把"对方的下班时间"当成"你的凌晨"。本课实现的前提是 `event.ts` **已经带正确时区**——这正是 2.3 坚持"不猜时间"的价值：猜出来的时区会让整条规则的结果整体偏移。

**规避与对抗**：攻击者可以在**工作时段**活动（融入噪声）；对抗方式是**多信号组合**（新来源 + 失败后成功 + 覆盖面异常）。单条 `off_hours` 从来不是结论。

---

### 4.7 日志清痕与日志侧规避（为什么"零告警 ≠ 没攻击"）

这是**所有日志检测的共同对手**，必须单独讲。

**攻击形态**

1. **删除 / 截断日志**：`rm /var/log/auth.log`、`truncate -s 0`；
2. **定向清除**：`sed -i '/203\.0\.113\.7/d'` —— 只删掉自己那几次记录（**最阴险**，总量看起来完全正常）；
3. **停止 / 篡改采集**：停 `rsyslog` / `auditd`、改 `rsyslog.conf` 的转发目标、污染时间源（NTP）让时间错乱；
4. **日志注水**：制造海量噪声（大量来自全世界的 `Invalid user`），让真正的攻击混在里面；
5. **利用采集链漏洞**：注入换行伪造整条日志行、注入控制字符污染解析器（**日志注入 / CRLF 注入**）；
6. **制造时间戳问题**：让事件落进 `no_timestamp` 桶，从而**被排除在窗口判定之外**。

**检测侧的对抗原则**

| 攻击手法 | 检测侧对抗 | 本课做了什么 |
|---|---|---|
| 删除 / 清空日志 | 不可变存储 + 远端实时转发（日志在攻击者够不着的地方）；文件行数基线告警 | **超出本课范围**——本课只读日志，无法知道日志被删过，必须写进局限 |
| 定向清除 | 与**其它维度**交叉验证（主机侧、网络侧、云审计日志） | 本课**做不到**，只能提醒 |
| 时间戳缺失 / 不可用 | **拒绝下结论**，而不是猜 | ✅ `no_timestamp` 计数 → `complete=False` → 退出码 4 |
| 日志注入（伪造行） | 结构化解析 + 严格正则；对无法识别的行**计数** | ✅ `unparsed` 计数（`lab --dirty` 演示的 `!!! log rotation marker` 就是这种） |
| 乱序 / 拼接 | 排序后再统计，同时**统计乱序次数**（异常高的乱序本身就是线索） | ✅ `out_of_order` |
| 重放 / 重复行 | 全字段元组去重 | ✅ `deduped` |
| 注水淹没 | 阈值 + 优先级排序 + 主体聚合 | ⚠️ 部分覆盖（本课没有"告警量基线"） |
| 低频慢速 | 需要**跨天长窗口**检测 | ❌ 局限，见第 11 节思考题第 2 题 |

**最重要的一条结论**

> 日志分析的输出**永远**是"在我能看到的范围内、用这套阈值，我看到了什么"。
> **"零告警"必须和"覆盖是否完整"一起读**，否则它什么都不能说明——这就是退出码 `4 > 3` 的工程含义（见 5.6）。

---

### 4.8 阈值与时间窗口的完整推导（把七个检测器算一遍）

把前面散落的推导集中成一张表，方便你**按自己组织的作息重新标定**。

| 检测器 | 窗口 | 阈值 | 推导依据 | 调参方向 |
|---|---|---|---|---|
| `brute_force_single_source` | 300s | 8 次 | 人会连错 3–5 次就停；自动化脚本 5 分钟能打几百次。取 8 是"离人的噪声远、离脚本的真实强度也远"。`count ≥ 3×阈值` 升为 critical | 有严格登录限流（fail2ban）时可上调；面对顽固攻击可下调 |
| `brute_force_distributed` | 600s | 10 次 **且** ≥3 来源 | 摊薄后单源节奏更慢 → 窗口必须放长；`min_sources` 是这条规则区别于单源规则的**唯一理由** | NAT 出口多的组织应上调 `min_sources`，否则共享出口会持续误报 |
| `failed_then_success` | 900s | 前置失败 ≥3 | "输错→再输对"正常在秒级；15 分钟已极宽裕。失败数 ≥3 是为了排除"连续两次手滑" | 口令策略弱时应下调到 2 并配合其它信号 |
| `login_from_unexpected_source` | 瞬时 | 无（基线比对） | 这不是统计问题，是**集合隶属**问题 | 基线的质量决定一切 |
| `login_from_single_source` | 瞬时 | 无（启发式） | 无基线时的退化形态，只用来提示"缺基线" | 应尽快用真基线替代 |
| `off_hours_success` | 瞬时 | 工作时段 8–20 | 需要覆盖绝大多数组织的作息；跨时区必须先统一 | 按自己组织的排班改（`--work-start/--work-end`） |
| `web_auth_abuse` | 600s | 20 次 401/403 | 人不会 10 分钟内失败 20 次；但前端轮询 bug 会 → 所以给 medium | 有验证码/MFA 时可上调；接口被扫描时下调 |
| `path_traversal_probe` | 瞬时 | 1 次 | 正常请求**不会**含规范化后的 `../`——单次即足够 | 有业务确实传相对路径时，需按路径白名单收窄 |

**两条通用原则**

1. **阈值是参数，不是真理**。报告必须**回显实际使用的阈值**（`parameters` 段），否则"没告警"与"阈值太宽"无法区分（见 3.5）。
2. **窗口越长，误报越多；窗口越短，攻击者越容易摊薄到窗口外**。唯一稳妥的组合是**多个不同粒度的检测器并存**（秒级 / 分钟级 / 小时级 / 天级）。本课只做到分钟级——**天级（低频持久）是明确的缺口**。

---

### 4.9 攻击者规避 ↔ 检测对抗 总表

| # | 攻击手法 | 靠什么痕迹被发现 | 攻击者的免费规避 | 检测的补偿手段 | 本课是否覆盖 |
|---|---|---|---|---|---|
| 1 | 单源高频爆破 | 同源失败密度 | 降频 | 分布式检测 | ✅ |
| 2 | 分布式 / 喷洒 | 同账号多来源密度 | 降来源数、每源只试 1 次 | 来源情报 + 采样面扩大 | ✅（medium） |
| 3 | 爆破得手 | 失败后同链路成功 | 打完就走 / 清日志 | 与 #1 成对、加强采集 | ✅ |
| 4 | 账号枚举 | `Invalid user` 密度 | 低频、用真实账号列表 | 与失败计数合并 | ✅（间接） |
| 5 | 目录穿越探测 | 请求路径特征串 | 编码变形（`%252e`）、分隔符变体（`..\`） | 归一化后再匹配、多形态正则 | ✅（部分：`\` 变体未覆盖） |
| 6 | Web 撞库 | 401/403 密度 | 分布式、降频 | 与 #2 同思路 | ✅（medium） |
| 7 | 横向移动 | 新来源 / 多主机出现 | 走已授权跳板、走内网 API | 基线 + 定期复查 + 多日志源 | ✅（medium/low） |
| 8 | 非工作时段活动 | 成功登录的时间 | 在工作时段活动 | 与 #3/#7 组合加权 | ✅（low） |
| 9 | 日志清痕 | （**看不见**） | 直接删 | 不可变存储 + 远端转发 + 交叉日志源 | ❌ 必须靠架构 |
| 10 | 日志注入 / 伪造行 | `unparsed` 异常 | 构造合法格式的假行 | 结构化解析 + 采集侧校验 | ⚠️ 部分 |
| 11 | 时间戳缺失 | `no_timestamp` | 制造无时间戳事件 | 拒绝下结论（退出码 4） | ✅ |
| 12 | 低频慢速 | （分钟窗口看不见） | 拉长到天 / 周 | 天级窗口、成功失败比、账号覆盖面 | ❌ 局限 |

**这张表的用法**：任何一条告警被确认后，**先把"攻击者的免费规避"这一列读一遍**——它决定你下一步该加固哪个检测器，而不是加班看更多日志。


## 5. 核心机制详解

### 5.1 模块结构

```text
log_core.py            核心：事件模型 / 解析器 / 检测器 / 覆盖统计
 ├─ LogEvent           标准化事件（不含原始行）
 ├─ LogCoverage        行数 / 解析 / 无法识别 / 缺时间戳 / 去重 / 乱序
 ├─ parse_timestamp()  四种时间格式 → 带时区 datetime（失败返回 None）
 ├─ parse_sshd/nginx/json_log()
 ├─ detect_source()    JSON → nginx → sshd → unknown
 ├─ parse_lines()      解析 + 去重 + 排序 + 统计
 ├─ 7 个检测器（产生 8 类告警）
 └─ analyze()          跑全部检测器并排序汇总

01-log-parser.py       基础：标准化与覆盖统计
02-detectors.py        进阶：七个场景 + 七类踩坑演示
03-log-analyzer.py     实战：CLI（parse / analyze / lab）
```

### 5.2 解析层：识别顺序与失败处理

```mermaid
flowchart TD
    A[一行日志] --> B{以 { 开头?}
    B -->|是| C[parse_json_log]
    B -->|否| D{匹配 nginx combined?}
    D -->|是| E[parse_nginx]
    D -->|否| F{syslog 且含 sshd/sudo?}
    F -->|是| G[parse_sshd]
    F -->|否| H[unknown → coverage.unparsed]
    C --> I{解析成功?}
    E --> I
    G --> I
    I -->|否/不是关心的动作| H
    I -->|是| J{时间可解析?}
    J -->|否| K[ts=None → coverage.no_timestamp]
    J -->|是| L[带时区 datetime]
```

三个容易忽略的设计点：

1. **`detect_source` 是启发式**：JSON 靠首字符 `{`、nginx 靠完整正则、
   sshd 靠 syslog 前缀 + 进程名。识别失败 → 计入 `unparsed`，
   **绝不"尽力猜一种格式硬解析"**（那会造出错误字段，比丢行更糟）。
2. **sshd 行里不关心的动作（如 `Connection closed`）不算解析失败**：
   它返回 None，但在本实现中被计入 `unparsed`——这是一个**有意的取舍**，
   报告里会显示 `unparsed=1` 提醒你"这行我没用上"。
3. **syslog 无年份**：`Sep 19 06:12:01` 必须补年份，所以 `parse_lines`
   接受 `year=` 参数。跨年日志要按文件分批传入（否则 12 月 31 日的日志
   可能被补成错误年份）。

### 5.3 时间与派生字段

| 输入形态 | 解析结果 | 说明 |
|---|---|---|
| `2026-09-19T06:12:01+08:00` | 带偏移的 datetime | 最理想 |
| `2026-09-19T06:12:01Z` | UTC datetime | `Z` 会被换成 `+00:00` |
| `19/Sep/2026:06:12:01 +0800` | nginx 标准格式 | `%d/%b/%Y:%H:%M:%S %z` |
| `Sep 19 06:12:01` | 需 `year` + 假设时区 | 缺信息 → 假设必须显式 |
| 无法解析 | `None` | **不填 now()、不填文件时间** |

`LogEvent.ts` 全部带时区，比较/排序不会出现"naive 与 aware 混用"的经典异常。
报告展示统一按 `DEFAULT_TZ`（UTC+8）渲染。

### 5.4 检测器清单（7 个注册检测器 / 8 类告警）

| 检测器 | 主体键 | 窗口/阈值（默认） | severity | confidence |
|---|---|---|---|---|
| `brute_force_single_source` | (host, src_ip) | 300s / 8 次 | high（≥24 次升级 critical） | high |
| `brute_force_distributed` | (host, user) | 600s / 10 次 / ≥3 来源 | medium | medium |
| `failed_then_success` | (host, user, src_ip) | 900s / 前置失败 ≥3 | high | medium |
| `login_from_unexpected_source` | (host, user) | 基线比对 | medium | medium |
| `login_from_single_source` | (host, user) | 无基线时的启发式 | low | low |
| `off_hours_success` | (host, user) | 工作时段 8:00–20:00 | low | low |
| `web_auth_abuse` | (host, src_ip) | 600s / 20 次 401-403 | medium | medium |
| `path_traversal_probe` | (host, src_ip) | 单次命中 | medium | high |

> `login_from_unexpected_source` 与 `login_from_single_source` 由**同一个函数**
> `detect_new_source()` 产生：有基线时是前者（medium/medium），
> 无基线时退化到后者（low/low）。这体现了"**置信度取决于你掌握多少外部信息**"。

### 5.5 覆盖与可判定性

| 字段 | 含义 | 会影响结论吗 |
|---|---|---|
| `lines_total` | 读取到的非空行数 | — |
| `parsed` | 成功标准化的事件数 | — |
| `unparsed` | 无法识别格式的行 | ✅ 使 `complete=False` |
| `no_timestamp` | 缺少/无法解析时间的事件 | ✅ 使 `complete=False`，且退出窗口检测 |
| `deduped` | 被判定为重复的行 | 否（信息性） |
| `out_of_order` | 文件顺序中的时间倒挂次数 | 否（已排序，信息性） |
| `hosts` / `time_start` / `time_end` | 主机集合与时间范围 | 用于判断"范围是否对得上" |
| `complete` | `unparsed == 0 and no_timestamp == 0` | ✅ 唯一"可以下结论"的开关 |

CLI 额外把**空输入**和 **read_error**（编码错误、IO 错误、超过行数上限）
也算作覆盖缺口。

### 5.6 门禁与报告渲染

```text
报告结构（Markdown）：
  摘要（行数/解析/主机/时间范围/告警分级）
  ⚠️ 覆盖声明        ← 必须在明细之前
  告警明细（按 priority 降序，每条形如"主体 / 次数 / 窗口 / 时间 / 证据 / 为什么 / 建议"）
  检测参数（阈值回显，标注默认 or 自定义）
  检测器清单
  免责声明
```

`--format json` 输出结构化报告（`summary` / `parameters` / `coverage` / `detectors_run` / `alerts`），
供 CI 与工单系统消费；`analyze --output file` 落盘；`report` 之类的重渲染
按需自建（本课的 JSON 已含渲染所需全部字段）。

### 5.7 快速开始

```bash
cd ~/code/Learn-Python
D=days/day-160-日志安全分析/code

python3 $D/01-log-parser.py --self-test          # 标准化与覆盖统计
python3 $D/02-detectors.py --self-test           # 七场景 + 七类踩坑
python3 $D/03-log-analyzer.py --self-test        # CLI 整合
python3 $D/03-log-analyzer.py lab                # 合成日志 → 报告 + 退出码 3
python3 $D/03-log-analyzer.py lab --dirty        # 混入脏数据 → 覆盖声明 + 退出码 4
python3 $D/03-log-analyzer.py parse /var/log/auth.log
python3 $D/03-log-analyzer.py analyze /var/log --fail-on high --format json --output /tmp/a.json
python3 $D/03-log-analyzer.py analyze /var/log --brute-threshold 20 --work-start 7 --work-end 22
```

无第三方依赖，Python 3.10+（本仓库在 3.12 上验证）。
`--host` 用于指定"日志里没有主机名时的回退主机名"（会出现在报告的 hosts 里）。
## 6. 定义与使用方法（API 速查）

### 6.1 数据结构

| 结构 | 字段 | 说明 |
|---|---|---|
| `LogEvent` | `ts / host / source / kind / action / user / src_ip / status / path / ref` | `frozen=True`；**无 raw 字段**；`subject` 属性 = `(host, src_ip, user)` |
| `LogCoverage` | `lines_total / parsed / unparsed / no_timestamp / deduped / out_of_order / hosts / time_start / time_end` | `complete` = `unparsed==0 and no_timestamp==0`；`gaps` 为人类可读缺口列表 |
| `Alert` | `detector / title / severity / confidence / subject / subject_sha / count / window_seconds / first_ts / last_ts / evidence / why / remediation / parameters` | `band` 属性 = P0..P3；`subject` 已掩码 |
| `AlertReport` | `alerts / coverage / detectors_run / parameters` | `by_severity()` / `at_or_above(t)` / `to_dict()` |

### 6.2 解析层函数

| 函数 | 签名要点 | 用途 |
|---|---|---|
| `parse_timestamp(text, *, assume_tz=DEFAULT_TZ, year=2026)` | `→ datetime \| None` | 四种格式；失败返回 None |
| `detect_source(line)` | `→ 'app'\|'nginx'\|'sshd'\|'unknown'` | 形态识别 |
| `parse_sshd / parse_nginx / parse_json_log(line, host, *, assume_tz, year, ref)` | `→ LogEvent \| None` | 单格式解析 |
| `parse_line(line, host, *, ...)` | `→ LogEvent \| None` | 自动分派 |
| `parse_lines(lines, *, fallback_host, assume_tz, year, source_name)` | `→ (events, coverage)` | 解析 + 去重 + 排序 + 统计 |
| `mask_ip(ip)` / `subject_sha(value)` | `→ str` | 报告脱敏 / 跨报告关联 |
| `priority(sev, conf)` / `triage_band(sev, conf)` | `→ int / 'P0'..'P3'` | 分档排序 |

### 6.3 检测器函数

| 函数 | 关键参数 | 触发条件 |
|---|---|---|
| `detect_brute_force(events, *, window_seconds=300, threshold=8, host=None)` | 窗口/阈值 | 同 `(host, src_ip)` 窗口内失败 ≥ 阈值 |
| `detect_distributed_bruteforce(events, *, window_seconds=600, threshold=10, min_sources=3)` | 窗口/阈值/来源数 | 同 `(host, user)` 窗口内失败 ≥ 阈值且来源 ≥ min_sources |
| `detect_failed_then_success(events, *, window_seconds=900, min_failures=3)` | 窗口/前置失败数 | 同 `(host, user, src_ip)` 失败 ≥ N 次后成功 |
| `detect_new_source(events, baseline=None)` | 基线 dict | 有基线：来源不在基线内；无基线：退化为 single_source 启发式 |
| `detect_off_hours_success(events, *, start_hour=8, end_hour=20)` | 工作时段 | 成功登录发生在时段外 |
| `detect_web_auth_abuse(events, *, window_seconds=600, threshold=20)` | 窗口/阈值 | 同 `(host, src_ip)` 窗口内 401/403 ≥ 阈值 |
| `detect_path_traversal_probe(events)` | — | 请求路径含 `../` / `%2e%2e` / `%252e` |
| `analyze(events, coverage=None, *, baseline=None, parameters=None)` | — | 跑全部检测器，返回 `AlertReport` |

所有检测器都只读事件、不写任何东西；`window_seconds=0` 表示"瞬时类"告警（无窗口）。

### 6.4 CLI 速查（`03-log-analyzer.py`）

| 子命令 | 参数 | 说明 |
|---|---|---|
| `parse <targets...>` | `--year` `--host` | 打印标准化事件表与覆盖统计 |
| `analyze <targets...>` | `--format {markdown,json}` `--fail-on {low,medium,high,critical}` `--baseline FILE` `--output FILE` `--year` `--host` `--brute-window` `--brute-threshold` `--fts-window` `--fts-min-failures` `--work-start` `--work-end` `--web-window` `--web-threshold` | 完整检测 + 报告；退出码即门禁结果 |
| `lab` | `--dirty` `--format` `--fail-on` | 临时目录生成合成日志并分析 |
| `--self-test` | — | 自测，输出 `SELF-TEST OK` |

`<targets>` 可以是文件，也可以是目录（目录只收 `*.log` / `*.txt`，递归查找）。

### 6.5 基线文件格式（`--baseline`）

```json
{
  "web01|deploy": ["192.0.2.9", "192.0.2.20"],
  "web02|ops": ["198.51.100.31"]
}
```

键是 `host|user`，值是**该账号已知的正常来源 IP 列表**。
有基线的账号走 `login_from_unexpected_source`（medium/medium），
没基线的账号只能走低置信度启发式（low/low）。

## 7. 运行命令 + 真实预期输出（实测）

> 本节所有输出都是**在本机真实跑出来的**（Python 3.12），不是手写示意。
> `-B` 表示不生成 `__pycache__`，保证"跑完不留产物"；
> 所有演示的临时文件都落在 `tempfile.TemporaryDirectory()` 里，**不污染仓库工作树**。

### 7.0 准备

```bash
cd /root/code/Learn-Python
D=days/day-160-日志安全分析/code
```

### 7.1 三个脚本的自检（必跑，必须逐行输出 `SELF-TEST OK`）

```bash
python3 -B $D/01-log-parser.py --self-test
python3 -B $D/02-detectors.py --self-test
python3 -B $D/03-log-analyzer.py --self-test
```

实测输出（三行，逐字）：

```text
SELF-TEST OK
SELF-TEST OK
SELF-TEST OK
```

自检**完全离线**：不联网、不读 `/var/log`、不写仓库；`03` 的自检在临时目录里生成合成日志并分析。

> `log_core.py` 是**被 import 的核心库**，不是 CLI 入口，它没有 `--self-test`（直接执行会静默退出 0、不输出 OK）。它的行为由上面三个脚本的断言覆盖。

### 7.2 标准化：三种异构日志 → 统一事件模型

```bash
python3 -B $D/01-log-parser.py
```

实测输出（完整）：

```text
TIME(UTC+8)          HOST    SOURCE  ACTION         USER     SRC_IP           STATUS REF
----------------------------------------------------------------------------------------
2026-09-19 05:59:00  web01   sshd    login_success  deploy   10.0.0.x         -      synthetic.log:4
2026-09-19 06:12:01  web01   sshd    login_failed   admin    203.0.113.x      -      synthetic.log:1
2026-09-19 06:12:04  web01   sshd    login_failed   admin    203.0.113.x      -      synthetic.log:2
2026-09-19 06:13:20  unknown-host nginx   request        -        203.0.113.x      401    synthetic.log:5
2026-09-19 06:14:00  api01   app     login_failed   ops      198.51.100.x     -      synthetic.log:6
2026-09-19 06:15:00  web01   sshd    login_success  deploy   10.0.0.x         -      synthetic.log:3
??                   api02   app     login_failed   svc      198.51.100.x     -      synthetic.log:7

覆盖统计：
  lines_total=9 parsed=7 unparsed=1 no_timestamp=1 deduped=1 out_of_order=1
  hosts=['api01', 'api02', 'unknown-host', 'web01']
  time_range=2026-09-19 05:59:00+08:00 → 2026-09-19 06:15:00+08:00
  complete=False  gaps=['unparsed=1 行无法识别格式（未参与判定）', 'no_timestamp=1 条缺少时间戳（窗口类检测不可用）']

提示：缺时间戳 / 无法识别的行不会参与窗口判定，但必须在报告里声明。
```

读这份输出时注意五处：

- **`??`**：JSON 行没有 `time` 字段 → `ts=None`，**不猜时间**，但仍保留事件（它的**存在**是事实）；
- **`synthetic.log:4` 排在 `:1` 前面**：第 4 行是 05:59，比第 1 行的 06:12 早——**乱序被排序修正**，同时 `out_of_order=1` 如实记录；
- **`deduped=1`**：第 8 行与第 1 行完全一致 → 被去重；
- **`unparsed=1`**：最后那句自然语言行无法识别 → 计入覆盖缺口；
- **`complete=False` + 两条 `gaps`**：报告必须声明"这部分未参与判定"。

### 7.3 七个检测器与七类踩坑演示

```bash
python3 -B $D/02-detectors.py
```

实测输出（完整）：

```text
检测器：brute_force_distributed, brute_force_single_source, failed_then_success, login_from_unexpected_source, off_hours_success, path_traversal_probe, web_auth_abuse

── 场景1/2 单源爆破 + 跨主机隔离
   [P0] brute_force_single_source      high     203.0.113.x@web01 count=10 300s 内失败 10 次；涉及账号数 1
   [P0] brute_force_single_source      high     203.0.113.x@web02 count=10 300s 内失败 10 次；涉及账号数 1
   覆盖：complete=True gaps=[]
── 场景3 分布式爆破
   [P2] brute_force_distributed        medium   svc@web01 count=15 600s 内失败 15 次，来源 IP 5 个
   覆盖：complete=True gaps=[]
── 场景4 失败后成功
   [P1] failed_then_success            high     deploy@web01 count=4 失败 4 次后成功，来源 192.0.2.x
   [P3] login_from_single_source       low      deploy@web01 count=1 来源 192.0.2.x（无基线，仅启发式）
   覆盖：complete=True gaps=[]
── 场景5 非工作时段登录
   [P3] login_from_single_source       low      deploy@web01 count=1 来源 192.0.2.x（无基线，仅启发式）
   [P3] off_hours_success              low      deploy@web01 count=1 本地时间 03:20（工作时段 8:00-20:00）
   覆盖：complete=True gaps=[]
── 场景6 Web 撞库 + 穿越探测
   [P1] path_traversal_probe           medium   203.0.113.x@unknown-host count=1 路径含穿越特征，响应码 404（仅记录，未构造请求验证）
   [P2] web_auth_abuse                 medium   203.0.113.x@unknown-host count=25 600s 内 401/403 共 25 次；热点路径 ['/login']
   覆盖：complete=True gaps=[]
── 场景7 缺时间戳
   （无告警）
   覆盖：complete=False gaps=['no_timestamp=1 条缺少时间戳（窗口类检测不可用）']

提示：阈值是参数不是真理。报告必须回显参数，否则'没告警'与'阈值太宽'无法区分。
```

三处值得对照：

- **场景 1/2 出现两条 P0**，分别对应 `web01` 与 `web02`——同一个源 IP 打两台主机，**必须是两条独立告警**（2.6 的跨主机混淆）；
- **场景 3 单源规则完全沉默**，只有按账号聚合的 `brute_force_distributed` 命中（15 次 / 5 个来源）——这就是"分布式爆破为什么必须单独写一个检测器"；
- **场景 4/5 各多出一条 `login_from_single_source`（P3）**：因为没有提供 baseline，`detect_new_source` 退化为低置信度启发式。**这是设计使然**，不是 bug——它正是在提示"你缺少基线"。

### 7.4 端到端演示：`lab`（合成日志 → 报告 → 退出码 3）

```bash
python3 -B $D/03-log-analyzer.py lab; echo "退出码=$?"
```

实测输出（节选）：

```text
# 安全日志分析报告

- 输入文件：1 个（lab-auth.log…）
- 行数：50（解析 50，无法识别 0，缺时间戳 0，去重 0，乱序 1）
- 主机：lab-auth, web01, web02
- 时间范围：2026-09-19 03:20:00+08:00 → 2026-09-19 11:30:00+08:00（统一为 UTC+8 展示）
- 告警：7 条（low=2、medium=2、high=3）

- 覆盖：完整（全部行均成功解析且带时间戳）

## 告警明细（按优先级排序）

### [P0] brute_force_single_source — 单一来源暴力破解尝试

- 主体：`203.0.113.x@web01`（sha: f362b0ed476a）
- 次数 / 窗口：10 次 / 300s
- 时间：2026-09-19 07:00:00+08:00 → 2026-09-19 07:00:09+08:00
- 严重度 / 置信度：high / high
- 证据：300s 内失败 10 次；涉及账号数 1
- 为什么可疑：短窗口内高频认证失败是口令猜测的直接特征，成功一次即可能失陷。
- 处置建议：对该来源限速/封禁或改用密钥认证；检查是否已有成功登录。
```

stderr（摘要与退出码）：

```text
# alerts=7 [low=2 medium=2 high=3] lines=50 parsed=50 覆盖完整
# lab 退出码 = 3（0=通过 3=有告警 4=覆盖不全）
```

退出码为 `3`。注意主体是 `203.0.113.x@web01`——**IP 末段已掩码**，并附 `sha` 指纹供跨报告关联（见 3.7）。

### 7.5 脏数据演示：`lab --dirty`（覆盖缺口优先 → 退出码 4）

```bash
python3 -B $D/03-log-analyzer.py lab --dirty; echo "退出码=$?"
```

实测输出（节选）：

```text
# 安全日志分析报告

- 输入文件：1 个（lab-auth.log…）
- 行数：52（解析 51，无法识别 1，缺时间戳 1，去重 0，乱序 1）
- 主机：api01, lab-auth, web01, web02
- 时间范围：2026-09-19 03:20:00+08:00 → 2026-09-19 11:30:00+08:00（统一为 UTC+8 展示）
- 告警：7 条（low=2、medium=2、high=3）

## ⚠️ 覆盖声明（先读这一段）

- unparsed=1 行无法识别格式（未参与判定）
- no_timestamp=1 条缺少时间戳（窗口类检测不可用）

上述范围内的日志**没有参与判定**。本次报告不能用于得出「未发现异常」的结论。
```

stderr：

```text
# alerts=7 [low=2 medium=2 high=3] lines=52 parsed=51 覆盖不全
# lab 退出码 = 4（0=通过 3=有告警 4=覆盖不全）
```

**同样的 7 条告警，只因为多了一行乱码和一条缺时间戳的事件，退出码就从 3 变成 4**——告警数没变，但结论的**可信度**变了。这正是"覆盖缺口优先"（见 5.6）的现场演示。

### 7.6 `parse`：先看清日志本身，再谈检测

先把一小段 sshd 日志放到临时目录（9 行、全部是同一来源的失败）：

```bash
T=$(mktemp -d)
cat > "$T/auth.log" <<'EOF'
Sep 19 07:00:00 web01 sshd[1]: Failed password for invalid user admin from 203.0.113.7 port 51001 ssh2
...（此处共 9 行，时间 07:00:00 → 07:00:08，其余字段同上）
EOF
```

```bash
python3 -B $D/03-log-analyzer.py parse "$T/auth.log" --host web01
```

实测输出（节选）：

```text
TIME                 HOST     SOURCE  ACTION         USER     SRC_IP
------------------------------------------------------------------------------
2026-09-19 07:00:00  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:01  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:02  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:03  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:04  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:05  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:06  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:07  web01    sshd    login_failed   admin    203.0.113.x
2026-09-19 07:00:08  web01    sshd    login_failed   admin    203.0.113.x

行数 9 / 解析 9 / 无法识别 0 / 缺时间戳 0 / 去重 0 / 乱序 0
```

> `--host web01` 只在日志**自带主机名**时才是多余的；对 nginx combined（不含主机名）与无 `host` 字段的 JSON，它是把事件归到哪台机器的**唯一依据**，会出现在报告的 `hosts` 里。

### 7.7 `analyze`：检测 + 参数回显 + JSON

```bash
python3 -B $D/03-log-analyzer.py analyze "$T/auth.log" --host web01 --fail-on high
```

实测（节选，stderr 摘要 + 告警头部）：

```text
# alerts=1 [high=1] lines=9 parsed=9 覆盖完整

# 安全日志分析报告
## 告警明细（按优先级排序）
### [P0] brute_force_single_source — 单一来源暴力破解尝试

- 主体：`203.0.113.x@web01`（sha: f362b0ed476a）
- 次数 / 窗口：9 次 / 300s
- 严重度 / 置信度：high / high
- 证据：300s 内失败 9 次；涉及账号数 1
```

**参数回显段（实测，这是"阈值不能省"的落点）**：

```text
## 检测参数（阈值回显）

| 参数 | 值 | 含义 |
| --- | --- | --- |
| `brute_window` | 300 （本次自定义） | |
| `brute_threshold` | 8 （本次自定义） | |
| `dist_window` | 600 （默认） | |
| `dist_threshold` | 10 （默认） | |
| `dist_min_sources` | 3 （默认） | |
| `fts_window` | 900 （本次自定义） | |
| `fts_min_failures` | 3 （本次自定义） | |
| `work_start` | 8 （本次自定义） | |
| `work_end` | 20 （本次自定义） | |
| `web_window` | 600 （本次自定义） | |
| `web_threshold` | 20 （本次自定义） | |

## 检测器清单（7 个）

- `brute_force_distributed`、`brute_force_single_source`、`failed_then_success`、`login_from_unexpected_source`、`off_hours_success`、`path_traversal_probe`、`web_auth_abuse`
```

> 标"本次自定义"的参数，是因为 `analyze` 子命令总是显式传入命令行默认值；只有 `lab` 走纯 `{}` 参数，全部显示"（默认）"。**这个标注差别本身就是有用信息**：它告诉你这份报告是用哪条代码路径生成的。

JSON 输出（实测节选）：

```json
{
  "summary": {
    "alerts": 1,
    "by_severity": { "info": 0, "low": 0, "medium": 0, "high": 1, "critical": 0 },
    "by_triage_band": { "P0": 1, "P1": 0, "P2": 0, "P3": 0 }
  },
  "detectors_run": [
    "brute_force_distributed",
    "brute_force_single_source",
    "failed_then_success",
    "login_from_unexpected_source",
    "off_hours_success",
    "path_traversal_probe",
    "web_auth_abuse"
  ],
  "coverage": {
    "lines_total": 9, "parsed": 9, "unparsed": 0, "no_timestamp": 0, "complete": true
  }
}
```

### 7.8 退出码实测对照

| 场景 | 命令 | 实测退出码 |
|---|---|---|
| 合成日志、覆盖完整、有 high 告警 | `03-log-analyzer.py lab` | **3** |
| 混入脏数据（unparsed=1, no_timestamp=1） | `03-log-analyzer.py lab --dirty` | **4** |
| 覆盖完整、无达标告警 | `analyze ... --fail-on critical` | **0** |
| 空日志文件 | `analyze empty.log` | **4**（`empty_input`） |
| 目标不存在 / 无输入 | `parse /nonexistent` | **2** |

优先级 `2 > 4 > 3 > 0`：**不可信的结果不配当门禁依据**。


## 8. 实战流程（六步）

1. **确定范围与时区**：哪些主机、哪些日志文件、日志时间基准是什么
   （UTC 还是本地时间、有没有跨时区设备）。这一步错了，后面全错。
2. **先 parse，后 analyze**：先跑 `parse` 看事件表与覆盖统计。
   有大量 `unparsed` 就先修采集/格式，不要急着调检测阈值。
3. **确认可判定性**：看 `no_timestamp` 是否为 0。不为 0 时，
   窗口类结论一律打折——报告里的"覆盖声明"就是在说这件事。
4. **跑检测并回显参数**：`analyze --fail-on high`，检查报告"检测参数"段
   是否符合你所在组织的作息（`work-start/work-end`、阈值）。
5. **人工复核优先级最高的告警**：对照值班表、变更记录、来源情报。
   `failed_then_success` 永远先看——它最可能是真的。
6. **建立并维护基线**：把确认过的正常来源写进 baseline JSON，
   并定期复查（否则基线会变成永久消音器，与 Day 159 的 baseline 同理）。

## 9. 常见陷阱（对照表）

| 陷阱 | 症状 | 正确做法 |
|---|---|---|
| 猜时间戳 | 攻击窗口变成编造的数字 | 无时间戳 → `ts=None` + `no_timestamp` 计数 |
| 按分钟分桶 | 攻击均摊到两桶即可隐形 | 滑动窗口（任意 W 秒内） |
| 按 IP 聚合跨主机 | 假告警（"一台机器被打 12 次"） | 主体键必须带 host |
| 忽略重复行 | 计数虚高、误报爆炸 | 按全字段元组去重 |
| 只写单源检测 | 分布式爆破完全隐形 | 增加按账号聚合的检测器 + 置信度说明 |
| 关联条件过宽 | "失败后成功"全是误报 | 限死 host + user + src_ip |
| 不回显阈值 | "没告警"与"阈值太宽"无法区分 | 报告里输出实际参数 |
| 覆盖不全仍下结论 | 漏掉的日志里就是攻击 | 覆盖缺口优先（退出码 4 > 3） |
| 报告输出完整 IP | 内部拓扑泄露 | 末段掩码 + sha 指纹 |
| 输出原始日志行 | 可能带出口令/Cookie | 只输出结构化字段 + `ref` 溯源指针 |

## 10. 局限（必须写进报告，不能省略）

- **只看日志**：没有主机侧证据（进程、文件、连接），无法确认是否失陷。
- **日志可被篡改**：攻击者删除失败记录后，本工具"看不到"任何东西；
  需要用不可变存储/远端转发来补偿。
- **无情报关联**：不知道某个 IP 是否为已知恶意来源，置信度因此受限。
- **检测器是教学基线**：7 个检测器远不及真实 SOC 规则集。
- **未评测检出率**：没有在带标签的真实日志集上计算 precision/recall，
  **不能**替代生产 SIEM/SOC 产品。
- **不会自动处置**：不封 IP、不改配置、不发请求——处置需要单独的授权与流程。

## 11. 思考题

1. 如果"零告警"可能来自"阈值太宽"，那么在给管理层做汇报时，
   **除了告警数**你还必须报告什么，才能让这个数字有意义？
2. 攻击者知道滑动窗口阈值后可以降低频率（例如每 10 分钟 7 次）。
   这种"低频慢速"攻击在当前设计里会以什么形式留下痕迹？
   需要补充哪一类检测（提示：时间跨度、成功/失败比、账号覆盖面）？
3. `no_timestamp` 的事件无法参与窗口判定。如果这些事件恰好全部是
   攻击者构造的，会出现什么后果？如何设计一个"缺时间戳即拒绝下结论"
   的严格模式（思考 `--strict` 的语义）？
4. 分布式爆破的置信度只有 medium，因为 NAT/共享出口也会长成这样。
   要把它抬到 high，你需要哪三类外部信息？分别从哪里获得？
5. 日志分析器是只读的。如果给它加上"自动封禁 IP"的能力，
   哪一类误报会直接升级为生产事故（提示：想想 `login_from_single_source`
   这种 low/low 的启发式告警）？为什么本课刻意不做这件事？
