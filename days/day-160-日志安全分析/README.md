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
## 4. 核心机制详解

### 4.1 模块结构

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

### 4.2 解析层：识别顺序与失败处理

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

### 4.3 时间与派生字段

| 输入形态 | 解析结果 | 说明 |
|---|---|---|
| `2026-09-19T06:12:01+08:00` | 带偏移的 datetime | 最理想 |
| `2026-09-19T06:12:01Z` | UTC datetime | `Z` 会被换成 `+00:00` |
| `19/Sep/2026:06:12:01 +0800` | nginx 标准格式 | `%d/%b/%Y:%H:%M:%S %z` |
| `Sep 19 06:12:01` | 需 `year` + 假设时区 | 缺信息 → 假设必须显式 |
| 无法解析 | `None` | **不填 now()、不填文件时间** |

`LogEvent.ts` 全部带时区，比较/排序不会出现"naive 与 aware 混用"的经典异常。
报告展示统一按 `DEFAULT_TZ`（UTC+8）渲染。

### 4.4 检测器清单（7 个注册检测器 / 8 类告警）

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

### 4.5 覆盖与可判定性

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

### 4.6 门禁与报告渲染

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

### 4.7 快速开始

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
## 5. 定义与使用方法（API 速查）

### 5.1 数据结构

| 结构 | 字段 | 说明 |
|---|---|---|
| `LogEvent` | `ts / host / source / kind / action / user / src_ip / status / path / ref` | `frozen=True`；**无 raw 字段**；`subject` 属性 = `(host, src_ip, user)` |
| `LogCoverage` | `lines_total / parsed / unparsed / no_timestamp / deduped / out_of_order / hosts / time_start / time_end` | `complete` = `unparsed==0 and no_timestamp==0`；`gaps` 为人类可读缺口列表 |
| `Alert` | `detector / title / severity / confidence / subject / subject_sha / count / window_seconds / first_ts / last_ts / evidence / why / remediation / parameters` | `band` 属性 = P0..P3；`subject` 已掩码 |
| `AlertReport` | `alerts / coverage / detectors_run / parameters` | `by_severity()` / `at_or_above(t)` / `to_dict()` |

### 5.2 解析层函数

| 函数 | 签名要点 | 用途 |
|---|---|---|
| `parse_timestamp(text, *, assume_tz=DEFAULT_TZ, year=2026)` | `→ datetime \| None` | 四种格式；失败返回 None |
| `detect_source(line)` | `→ 'app'\|'nginx'\|'sshd'\|'unknown'` | 形态识别 |
| `parse_sshd / parse_nginx / parse_json_log(line, host, *, assume_tz, year, ref)` | `→ LogEvent \| None` | 单格式解析 |
| `parse_line(line, host, *, ...)` | `→ LogEvent \| None` | 自动分派 |
| `parse_lines(lines, *, fallback_host, assume_tz, year, source_name)` | `→ (events, coverage)` | 解析 + 去重 + 排序 + 统计 |
| `mask_ip(ip)` / `subject_sha(value)` | `→ str` | 报告脱敏 / 跨报告关联 |
| `priority(sev, conf)` / `triage_band(sev, conf)` | `→ int / 'P0'..'P3'` | 分档排序 |

### 5.3 检测器函数

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

### 5.4 CLI 速查（`03-log-analyzer.py`）

| 子命令 | 参数 | 说明 |
|---|---|---|
| `parse <targets...>` | `--year` `--host` | 打印标准化事件表与覆盖统计 |
| `analyze <targets...>` | `--format {markdown,json}` `--fail-on {low,medium,high,critical}` `--baseline FILE` `--output FILE` `--year` `--host` `--brute-window` `--brute-threshold` `--fts-window` `--fts-min-failures` `--work-start` `--work-end` `--web-window` `--web-threshold` | 完整检测 + 报告；退出码即门禁结果 |
| `lab` | `--dirty` `--format` `--fail-on` | 临时目录生成合成日志并分析 |
| `--self-test` | — | 自测，输出 `SELF-TEST OK` |

`<targets>` 可以是文件，也可以是目录（目录只收 `*.log` / `*.txt`，递归查找）。

### 5.5 基线文件格式（`--baseline`）

```json
{
  "web01|deploy": ["192.0.2.9", "192.0.2.20"],
  "web02|ops": ["198.51.100.31"]
}
```

键是 `host|user`，值是**该账号已知的正常来源 IP 列表**。
有基线的账号走 `login_from_unexpected_source`（medium/medium），
没基线的账号只能走低置信度启发式（low/low）。

## 6. 实战流程（六步）

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

## 7. 常见陷阱（对照表）

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

## 8. 局限（必须写进报告，不能省略）

- **只看日志**：没有主机侧证据（进程、文件、连接），无法确认是否失陷。
- **日志可被篡改**：攻击者删除失败记录后，本工具"看不到"任何东西；
  需要用不可变存储/远端转发来补偿。
- **无情报关联**：不知道某个 IP 是否为已知恶意来源，置信度因此受限。
- **检测器是教学基线**：7 个检测器远不及真实 SOC 规则集。
- **未评测检出率**：没有在带标签的真实日志集上计算 precision/recall，
  **不能**替代生产 SIEM/SOC 产品。
- **不会自动处置**：不封 IP、不改配置、不发请求——处置需要单独的授权与流程。

## 9. 思考题

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
