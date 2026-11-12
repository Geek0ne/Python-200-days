# Day 182 — 阶段项目 · 自动化运维平台（一）：服务器监控 + 告警

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185）
> **本日主题**：阶段项目 Day 182–185 的第 1 天。今天只做一件事——
> 把 `采集 → 判定 → 去重 → 路由` 这条**竖切**从真机上跑通，做出一个能自己喊人的最小平台。
> **子主题**：主机/应用指标采集 · 阈值与抖动判定 · 告警路由与降级 · 告警去重与恢复通知
> **实测环境**：Linux 7.0.0-34-generic (x64)，Python 3.12.3，Docker 29.1.3，2026-10-16

---

## 概念解释

### 0. 先把「监控」和「告警」拆开

Day 177 解决的是「把数字收上来、画成图」。今天要解决的是后半句：

> 数字难看的时候，**怎么喊人，而且只喊一次**。

一条告警链路有四段，每段回答一个完全不同的问题：

| 段 | 本日脚本 | 回答的问题 | 少了它会发生什么 |
|---|---|---|---|
| **采集** | `01-collect-metrics.py` | 现在到底是什么值？ | 无从判断 |
| **判定** | `02-threshold-engine.py` | 这个值算不算「事」？ | 每次抖动都报警，一分钟 20 条 |
| **去重** | `04-alert-dedup-recovery.py` | 这事是不是已经喊过了？ | 同一个故障刷 60 条 |
| **路由** | `03-alert-routing.py` | 喊给谁、用哪条路喊？ | 半夜把 warning 打进值班电话 |
| **串联** | `05-platform-demo.py` | 四段拼起来还对不对？ | 每段都对，合起来漏告警 |

新手最常见的写法是把这四件事塞进一个 `if`：

```python
if cpu > 90:
    send_mail()          # 这行代码会在真实环境里制造三种事故
```

它会**抖动风暴**（CPU 在 90 边缘反复穿越）、**重复通知**（每分钟都发）、
**漏掉恢复**（没人知道它什么时候好了）。今天这 6 个脚本，每一个都是在补它漏掉的一环。

### 1. 主机指标 vs 应用指标

「服务器监控」听起来是一件事，其实是两类数据源：

| | 主机指标（host metrics） | 应用指标（app metrics） |
|---|---|---|
| 数据从哪来 | 内核自己统计：`/proc/stat` `/proc/meminfo` `/proc/uptime` | 应用的行为：探活结果、请求延迟、队列长度 |
| 采集方式 | **本地读取**（成本几乎为 0） | **主动探测**（HTTP GET，有网络成本） |
| 典型值 | CPU / 内存 / 磁盘 / load / uptime | up-or-down / latency_ms / http_code |
| 表征「谁」 | 机器 | 业务 |
| 挂了说明什么 | 机器要出事 | 业务要出事（机器可能完全正常） |
| 本日实现 | psutil 优先，`/proc` 兜底（两个后端产出同样的字段） | 标准库 `urllib` 探活，不用 requests |

关键区别：**主机指标是「读来的」，应用指标是「测出来的」**。
读来的东西一定拿得到数（除非机器真挂了）；测出来的东西**每次都是一个猜测**——
连接被拒、超时、对端 502，都是不同的故事，不能都当成「挂了」。
所以 `01` 里的探活口径被写死成两条（后面实验会验证）：

```
status=up    收到了 HTTP 响应（200/404/500 都算「进程活着在应答」）
status=down  连接失败 / 超时 / DNS 失败——进程或网络不可用
http_code    单独记录，用来区分「活着但在报 500」
```

### 2. 「超了阈值」≠「该喊人」：中间隔着三件事

这是本日最重要的认知。`cpu = 95 > 90` 只说明「这一刻超了」，剩下的三个问题才是告警系统的全部难度：

**(a) 超了几次？—— 连续次数（`consecutive`，对应 Prometheus 的 `for: 3m`）**

一次采样超阈值，可能只是这一秒在编译、在 GC、在解压。
要求**连续 N 次**都超，才能过滤掉绝大多数毛刺。
本日实测就抓到了一个活例子（实验 4 的真机输出）：

```
[2026-10-16T14:25:53Z] cpu=97.6%  ... pending  -  host_cpu_high
[2026-10-16T14:25:56Z] cpu=94.9%  ... pending  -  host_cpu_high
[2026-10-16T14:25:58Z] cpu=87.5%  ... dropped  -  host_cpu_high     <- 第 3 次掉回 90 以下，告警没发
```

这台机器当时负载确实高（load 8+，4 核），CPU 在 87%~97% 之间反复横跳。
**如果阈值判定是「只要超一次就报」，这几分钟里会响 6 次；连续 3 次的要求把它压成了 0 次。**

**(b) 回落了吗？—— 迟滞（hysteresis）**

阈值 90、恢复也按 90 判，会得到一个致命后果：指标在 89.9 / 90.1 之间抖动时，
系统会不停地 firing → resolved → firing → resolved。
解法是给**「进入告警」和「退出告警」用两个不同的阈值**：

```
          进入告警的线（threshold = 90）
                   ↓
  ───── 90 ────────────────────────  值在这条线以上 = 越界
  ───── 80 ────────────────────────  值必须掉到这条线以下 = 才算恢复
                   ↑
          恢复的线（release = 80）
```

中间那 10 个点（80, 90] 就是**迟滞带**：进去难，出来也难。
本日自检断言了这个语义（实验 2 的真机输出里能看到 `88 / 86 / 84 / 82 / 81 全部「迟滞保持」，
直到 79 才 resolved）。

**(c) 是不是在抖？—— 抖动判定（flapping）**

有些故障天生就是「坏 30 秒、好 30 秒」（网络闪断、被 OOM 杀掉又自动重启的进程）。
连续次数救不了它：它每次都真的连续超了 3 次。
判定的办法是**统计一段时间窗内的状态翻转次数**：窗口内翻转 ≥ N 次，就给它贴一个
`flapping=True` 的标签，下游据此**降级处理**（只留档，不叫人）。本日：

```
flap_window = 300s, flap_limit = 4   →  5 分钟内 firing/resolved 翻转 4 次 = 抖动
```

### 3. 告警路由：按级别选通道，通道挂了要能降级

「路由」回答的是「这条告警该走哪条路」。本日的路由表（`03-alert-routing.py`）：

```
flapping=True        → file               （抖动只留档，不叫人）
severity=critical    → webhook → file → console   （值班群，发不出去就落盘，再不行打屏幕）
severity=warning     → file → console
其它                 → console
```

两个设计要点：

1. **降级链（fallback）是顺序的，不是并行的**：webhook 发不出去才落盘，不是「又发 webhook 又落盘」。
   否则一次故障会在三个地方各留一份，事后对账对不上。
2. **重试（attempts）和降级是两层**：先在同一通道重试 `attempts` 次，
   重试完还不成才换下一个通道。真实世界里 webhook 一次 502 就降级是过度反应——
   大部分 webhook 失败是瞬时的。本日 `attempts=2`。

### 4. 去重与恢复：靠「指纹」把 60 条压成 1 条

同一个故障在 5 分钟里会被采到 60 次。去重的做法是给每条告警算一个**稳定的指纹**：

```
指纹 = sha256(告警名 + 严重级别 + 关键标签)   取前 12 位十六进制
例：host_cpu_high / critical / {rule, instance=ace}  →  f05360f106d8
```

指纹相同 = 同一个故障。第一次发通知，后面 59 次只把计数 +1。

**恢复通知（recovery）也必须算出同一个指纹**，否则匹配不上——这是最容易踩的坑，
下面「翻车复盘」有专门一条：把 `status` 算进指纹后，`resolved` 告警的指纹和 `firing` 不同，
恢复通知会永远变成「没有主的孤儿」被丢弃。

三态语义（本日实现，自检里全部断言过）：

| 动作 | 触发条件 | 说明 |
|---|---|---|
| `notify` | 首次收到某指纹的 firing | 真正打扰人的那一条 |
| `suppress` | 同指纹再次 firing，且未超再提醒间隔 | 只计数，不通知 |
| `renotify` | 同指纹 firing 持续超过 `resend_interval` | 长时间不恢复，再提醒一次（别彻底静音） |
| `recover` | 收到同指纹的 resolved | 发恢复通知，并清掉状态 |
| `drop` | resolved 但找不到活动告警 | 不发明知道匹配不上的通知 |

### 5. 一条告警的生命周期

```
                     越界 1..N-1 次
        ok ─────────────────────────▶ pending ────┐
         ▲                             │          │ 第 N 次越界
         │ 未达连续次数就回落             │          ▼
         │ （毛刺被过滤 dropped）        │        firing ──▶ 通知（notify）
         └─────────────────────────────┘          │
                                                  │ 同指纹重复上报
                                                  ├──▶ suppress（只计数）
                                                  │
                                                  │ 超过 resend_interval
                                                  ├──▶ renotify（再提醒）
                                                  │
                                                  │ 值跌回中间带（release < v < threshold）
                                                  │        → 保持 firing（迟滞）
                                                  │
                                                  │ 值跌破 release
                                                  ▼
                                                 ok ──▶ 恢复通知（recover）
```

### 6. 和 Day 177 / 工业标准的对照

今天这几个手写组件，在工业界都有对应物。对照着看，术语就不难记了：

| 本日实现 | Prometheus / Alertmanager 里叫什么 | 差异 |
|---|---|---|
| `consecutive=N` 连续 N 次才 firing | 规则里的 `for: 3m` | 本日按「次数」，标准按「时长」（等价，因为采样间隔固定） |
| `threshold / release` 双阈值 | 没有内建；自己写表达式或用 `keep_firing_for` | Alertmanager 里要靠两个维护条件近似 |
| `flapping` 抖动判定 | 部分实现（如 `alertmanager` 的 inhibit、PagerDuty 的 reduction） | 本日是显式状态 + 静默路由 |
| 指纹 `fingerprint()` | Alertmanager 的 fingerprint（同样是 hash 标签集合） | 一致：都**不含** value |
| `resend_interval` | `repeat_interval` | 一致 |
| `recover` 恢复通知 | Alertmanager 的 resolved 通知 | 一致 |
| 路由链 + fallback | `route` + `receiver` | 标准里 fallback 要靠多条 route 自己配 |

一句话：**Prometheus/Alertmanager 做的事，本质就是今天这四个脚本做的事**，
只是它把状态存在了磁盘上、把去重做成了全局的。

---

## 原理深入

### 为什么 `/proc/stat` 必须读两次

`/proc` 是**内核暴露的累加计数器**，不是「当前使用率」：

```
$ cat /proc/stat | head -1
cpu  user nice system idle iowait irq softirq steal guest guest_nice
```

`cpu` 这一行全是「自开机以来累计的 jiffies」。所谓 CPU 使用率，只能是**两个时刻的差**：

```
使用率 = 1 - (idle2 - idle1) / (total2 - total1)
```

这就是为什么 `01` 里 `_proc_cpu_percent()` 要 `time.sleep(0.10)` 再读第二次——
**这一步的睡眠是物理上省不掉的**，psutil 的 `cpu_percent(interval=0.1)` 内部做的是同一件事。
本日实测这个 0.1s 窗口占了采集耗时的绝大部分（`--once` 总耗时 0.195~0.267 s）。
顺带一提：第一次调用 psutil 的 `cpu_percent()` 若 `interval=0` 会返回 0.0（它拿不到上一时刻的引用），
这也是新手第一次用 psutil 拿到 0 的原因。

### 迟滞为什么能治抖动（一点算术）

设阈值 90、恢复线 80，指标在 89.9 和 90.1 之间抖动。**不用迟滞**时，每次穿越 90 都是一次状态翻转；
**用迟滞**时，要退出告警必须一路跌到 80，抖动幅度只有 0.2 个点，根本够不着。

所以迟滞带的宽度决定了「多大的抖动才治得住」：

```
迟滞带宽度  >  抖动的振幅        → 抖动被完全吸收（不翻转）
迟滞带宽度  <  抖动的振幅        → 每次波动都是一次 notification
```

这也是为什么 `02` 的自检里有一条**参数校验**：`op='>' 时 release 必须 <= threshold`，
写反了（比如 release=95 > threshold=90）会导致**永远恢复不了**——因为没有任何值能同时满足
「> 90 才算越界」和「<= 95 才算恢复」的互补关系，状态机会卡在 firing 出不来。
这种错误必须让程序当场报错，不能静默跑起来。

### 抖动判定：窗口是时间的，不是次数的

一个容易写错的地方：用「总翻转次数」判抖动。那样一个跑了 30 天、偶尔抖一下的系统，
攒够 100 次翻转也会被判定成抖动。

正确做法是**滑动时间窗口**：只统计最近 `flap_window` 秒内的翻转。
本日自检专门钉住了这一点（实验 6）：

```
窗口内翻转 4 次后判定为抖动（flapping=True）
窗口 2s、采样间隔 10s 时不会误判抖动（时间窗口生效）    <- 同样的翻转次数，窗口不对就不算抖动
```

第二行是关键：**同样的 7 次翻转，间隔 10 秒就完全不算抖动**（每次翻转之间系统平静了 10 秒，
那是「偶尔出事」不是「反复横跳」）。

### 降级链的失败语义：重试 ≠ 降级

```
attempts=2 的语义：
  webhook 第 1 次失败  → 立刻重试        （排除瞬时网络抖动）
  webhook 第 2 次失败  → 放弃这个通道，进入 fallback 链
  file 成功            → 记 delivered_by=file，整个投递结束
  全部失败             → delivered_by=None（★绝不假装成功）
```

最后一行是纪律：**投递失败必须能被上层看见**。很多自研告警系统的 bug 是
`except: pass` —— 告警发不出去，日志里一行记录都没有，事后无从追查。
本日 `03` 的自检里有一条专门断言「全部通道失败时 `delivered_by` 为 None」。

### 指纹的稳定性：为什么不能含 `value` / `status`

- 含 `value`（比如 95.0）→ 每次采样值都不同 → 每次都算新指纹 → **去重完全失效**，退化成刷屏。
- 含 `status` → firing 和 resolved 的指纹不同 → **恢复通知匹配不上活动告警** → 恢复永远发不出去。
- 含时间戳 `ts` → 同 `value` 的后果。

所以指纹只能由**故障的身份**构成：告警名 + 严重级别 + 关键标签（instance / job / 挂载点 …）。
这跟 Alertmanager 的 design 完全一致（它的 fingerprint 也是标签集合的 hash，绝不含采样值）。

---

## 定义与方法（速查）

### 本日的四个核心结构

```python
# 1. 指标快照（采集层的输出，全平台唯一输入格式）
{"ts": "...", "host": "ace",
 "host_metrics": {"cpu_percent": 87.2, "mem_percent": 42.7, "disk_percent": 38.4,
                  "load1": 8.27, "load5": 6.9, "load15": 5.6, "cpu_count": 4,
                  "uptime_seconds": 1545270, "backend": "psutil"},
 "app_metrics": [{"target": "http://127.0.0.1:18082/", "status": "up",
                  "http_code": 200, "latency_ms": 3.1, "error": None}]}

# 2. 规则（判定层）
ThresholdRule(name, metric, op, threshold, release=None,
              consecutive=1, flap_window=60.0, flap_limit=4, severity="warning")

# 3. 事件（判定层的输出）
{"rule": "host_cpu_high", "metric": "host_metrics.cpu_percent", "type": "firing",
 "state": "firing", "value": 97.6, "threshold": 90.0, "release": 80.0,
 "consecutive": 3, "breach_run": 3, "severity": "critical",
 "flapping": False, "ts": 1792160763.0}

# 4. 告警对象（去重/路由的输入）
{"name": "host_cpu_high", "type": "firing", "status": "firing",
 "severity": "critical", "metric": "host_metrics.cpu_percent",
 "value": 97.6, "threshold": 90.0, "flapping": False,
 "summary": "[critical] host_cpu_high host_metrics.cpu_percent 越界 (值=97.6 阈值=90.0)",
 "labels": {"rule": "host_cpu_high", "metric": "host_metrics.cpu_percent"}, "ts": ...}
```

### 事件类型与动作速查

| 类型/动作 | 出处 | 含义 |
|---|---|---|
| `pending` | 02 | 越界但未达连续次数（**不进告警通道**） |
| `dropped` | 02 | 未达连续次数就回落——被过滤掉的毛刺 |
| `firing` | 02 | 升级为告警 |
| `resolved` | 02 | 跌破恢复线，故障解除 |
| `notify` / `suppress` / `renotify` / `recover` / `drop` | 04 | 见上文三态表 |
| `delivered_by` | 03 | 最终由哪个通道送达；`None` = 全部失败 |

### 常用参数与取值理由

| 参数 | 本日默认 | 为什么 |
|---|---|---|
| `consecutive`（CPU） | 3 | 采样 30s 一次时 ≈ `for: 90s`，能吃掉绝大多数编译/GC 毛刺 |
| `release` | threshold - 10 | 迟滞带 10 个百分点，覆盖正常运行波动 |
| `flap_window` / `flap_limit` | 300s / 4 | 5 分钟内翻转 4 次；更密说明故障在自愈循环 |
| `resend_interval` | 300s | 不恢复的故障每小时提醒 12 次太多，5 分钟太吵，取折中 |
| `attempts` | 2 | 一次重试足以排除瞬时失败，再多会拖慢降级 |
| 探活 `timeout` | 2.0s | 内网探活超过 2s 已经算「不可用」 |

### 命令行速查

```bash
# 01 采集
python3 01-collect-metrics.py --once                       # 采集一次（人读格式）
python3 01-collect-metrics.py --once --json                # JSON 一行一份
python3 01-collect-metrics.py --backend proc --once        # 强制走 /proc 回退
python3 01-collect-metrics.py --once --count 3 --interval 1
python3 01-collect-metrics.py --once --probe http://127.0.0.1:18082/ --probe http://127.0.0.1:9999/
python3 01-collect-metrics.py --once --out /tmp/day182/snap.jsonl

# 02 判定
python3 02-threshold-engine.py --self-test
python3 02-threshold-engine.py --demo --scenario spike|sustained|hysteresis|flap|disk

# 03 路由
python3 03-alert-routing.py --self-test
python3 03-alert-routing.py --dry-run --demo               # 只打印路由决定
python3 03-alert-routing.py --demo --webhook URL --file F  # 真发

# 04 去重
python3 04-alert-dedup-recovery.py --self-test
python3 04-alert-dedup-recovery.py --demo

# 05 串联（默认 dry-run；--live 才真发）
python3 05-platform-demo.py --self-test
python3 05-platform-demo.py --once --probe http://127.0.0.1:18082/
python3 05-platform-demo.py --serve --count 10 --interval 2 --live --webhook URL --file F

# 06 实验用接收端
python3 06-webhook-receiver.py --port 19090 --log /tmp/day182/hook.jsonl
```

### 依赖说明（优雅退化）

| 依赖 | 有没有它的区别 | 退化行为 |
|---|---|---|
| `psutil` | 主机指标走 psutil（含 `cpu_percent`、`boot_time`） | 自动退到 `/proc`，字段完全一致，仅 `backend` 不同 |
| `requests` | **不需要** | 探活一律用标准库 `urllib` |
| Docker | 只有「容器被监控」那个实验需要 | 其余实验全部可离线跑 |
| 网络/外网 | **不需要** | webhook 全部打本机 `127.0.0.1`，不发外网 |

本机实测：`psutil 7.2.2` 已安装；把 `--backend proc` 强制成回退路径也能出数（实验 1、实验 6）。

---

## 图解

见 [`diagrams/README.md`](diagrams/README.md)：六张图 ——
四层链路数据流、告警状态机、迟滞带、抖动窗口、指纹去重、降级链。

链路总览（先看这张）：

```
┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
│ 01 采集      │   │ 02 判定       │   │ 04 去重        │   │ 03 路由       │
│             │   │              │   │               │   │              │
│ /proc+psutil│──▶│ 连续次数 N    │──▶│ 指纹 sha256   │──▶│ critical→hook│
│ HTTP 探活    │   │ 迟滞 80/90   │   │ 状态表         │   │ 失败→file    │
│             │   │ 抖动窗口      │   │ notify/suppress│   │ →console     │
└─────────────┘   └──────────────┘   └───────────────┘   └──────────────┘
   快照 JSON         事件               动作               投递报告
                                   （05 把四段串起来）
```

---

## 实战环境

| 项 | 版本 / 说明 |
|---|---|
| 主机 | Linux 7.0.0-34-generic (x64)，4 核，16 GB，load 6~9（复现时注意这台机器本身就偏忙） |
| Python | 3.12.3（标准库 + psutil，无需安装任何第三方库） |
| psutil | 7.2.2 |
| Docker | 29.1.3，实验用镜像 `nginx:alpine`（**本地已有，不联网拉取**） |
| 被监控目标 | 容器 `d182-web`，映射到宿主端口 18082 |
| webhook 接收端 | `06-webhook-receiver.py`，监听 127.0.0.1:19090 |

本日 6 个脚本**全部只用标准库**（`psutil` 可选），都能 `--self-test` 离线自检；
只有实验 4「容器端到端」需要 Docker。

---

## 实验 1：采集真机指标（两个后端 + 耗时 + 体积）

**目的**：看清一份指标快照到底长什么样，并对比 psutil 与 `/proc` 两条路径。

**执行**：
```bash
cd days/day-182-运维平台-监控与告警/code
time python3 01-collect-metrics.py --once
time python3 01-collect-metrics.py --backend proc --once
python3 01-collect-metrics.py --once --json | wc -c
```

**实际结果**（真机 stdout，2026-10-16T14:25:24Z）：

```
$ time python3 01-collect-metrics.py --once
[2026-10-16T14:25:24Z] ace  (backend=psutil)
  主机  cpu= 85.4%  mem= 45.2%  disk= 38.3%  load=8.28/6.75/5.45  cores=4  uptime=1545179s
  应用  （未指定 --probe，跳过应用探活）

real	0m0.267s
user	0m0.075s
sys	0m0.016s

$ time python3 01-collect-metrics.py --backend proc --once
[2026-10-16T14:25:24Z] ace  (backend=proc)
  主机  cpu= 64.1%  mem= 45.3%  disk= 36.3%  load=8.58/6.84/5.49  cores=4  uptime=1545179s
  应用  （未指定 --probe，跳过应用探活）

real	0m0.195s
user	0m0.064s
sys	0m0.019s

$ python3 01-collect-metrics.py --once --json | wc -c
257
```

**结论**：
- 两个后端的**字段完全一致**（只有 `backend` 值不同），所以上游判定层不需要知道数据是怎么拿到的；
- 同一时刻 `mem` 一个是 45.2%、一个是 45.3%，`disk` 一个是 38.3%（psutil，按文件系统）、
  一个是 36.3%（`shutil.disk_usage("/")`）——**同一台机器的同一个指标，换个实现就能有 2 个点的差**，
  所以「阈值」必须和「采集口径」一起定，不能拿 A 工具的数去配 B 工具的规则；
- 耗时 0.195~0.267 s 里，绝大部分是两次读 `/proc/stat` 之间那个 0.1 s 的窗口（物理必需，见「原理深入」）；
- 不带探活的快照只有 **257 字节**——这就是监控数据便宜的原因（Day 177 的结论在这里复现）。

**清理**：无（只读）。

---

## 实验 2：阈值与抖动的四种行为（离线，确定性时间线）

**目的**：用「假时钟」把几分钟的行为在毫秒内跑完，亲眼看见 pending / dropped / 迟滞 / 抖动。

**执行**：
```bash
python3 02-threshold-engine.py --demo --scenario spike
python3 02-threshold-engine.py --demo --scenario sustained
python3 02-threshold-engine.py --demo --scenario hysteresis
python3 02-threshold-engine.py --demo --scenario flap
```

**(a) spike —— 单次尖峰被过滤**（真机输出）：

```
tick   value    state     event     note
0      40.0     ok        -
1      40.0     ok        -
2      95.0     pending   pending   越界 1/3
3      41.0     ok        dropped   毛刺被过滤（未达连续次数）
4      42.0     ok        -
5      40.0     ok        -
```

**(b) sustained —— 连续 3 次升级，然后迟滞保持**（真机输出）：

```
0      40.0     ok        -
1      88.0     ok        -
2      91.0     pending   pending   越界 1/3
3      92.0     pending   pending   越界 2/3
4      93.0     firing    firing    升级为告警
5      94.0     firing    -         迟滞保持（未到恢复线 80.0）
6      95.0     firing    -         迟滞保持（未到恢复线 80.0）
7      70.0     ok        resolved  恢复通知
8      65.0     ok        -
```

**(c) hysteresis —— 89 到 79 的降落过程一个告警都不发**（真机输出）：

```
3      95.0     firing    firing    升级为告警
4      88.0     firing    -         迟滞保持（未到恢复线 80.0）
5      86.0     firing    -         迟滞保持（未到恢复线 80.0）
6      84.0     firing    -         迟滞保持（未到恢复线 80.0）
7      82.0     firing    -         迟滞保持（未到恢复线 80.0）
8      81.0     firing    -         迟滞保持（未到恢复线 80.0）
9      79.0     ok        resolved  恢复通知
```

**(d) flap —— 抖动判定开始生效**（真机输出，截取）：
```
7      95.0     firing    firing    升级为告警
8      60.0     ok        resolved  恢复通知（抖动中，将降级/抑制）
...
11     95.0     firing    firing    升级为告警（抖动中，将降级/抑制）
12     60.0     ok        resolved  恢复通知（抖动中，将降级/抑制）
13     95.0     pending   pending   越界 1/3
```

**结论**：
- 第 (a) 条就是「为什么要有 `for`」的答案：**一次越界什么都不是**；
- 第 (c) 条是迟滞的价值：从 95 降到 79 的过程中，值在 88/86/84/82/81 都低于阈值 90 了，
  但**一个通知都不发**——因为还没到恢复线；
- 第 (d) 条是抖动判定的价值：从第 8 个 tick 起，事件被贴上 `flapping` 标签，
  下游会把它从「喊人」降级成「留档」。注意第 13 行的 `pending` **不再带抖动标签**——
  因为窗口内已经没有翻转了（5 分钟内只有 4 次，窗口滑过去就自动摘掉标签）。

**清理**：无（纯内存计算，不起服务）。

---

## 实验 3：应用探活 —— 把一个服务起起来，再杀掉

**目的**：验证「up / down」到底是怎么判的，以及两种失败（连接被拒 vs 超时）的差别。

**执行**：
```bash
python3 -m http.server 18081 --bind 127.0.0.1 &
sleep 1
python3 01-collect-metrics.py --once --probe http://127.0.0.1:18081/
kill %1
python3 01-collect-metrics.py --once --probe http://127.0.0.1:18081/
```

**实际结果**（真机 stdout，2026-10-16T14:25:40Z）：

```
# 服务活着
[2026-10-16T14:25:40Z] ace  (backend=psutil)
  主机  cpu= 70.0%  mem= 45.6%  disk= 38.3%  load=9.03/7.03/5.57  cores=4  uptime=1545195s
  应用  http://127.0.0.1:18081/            up   code=200   latency=40.912ms

# 同一命令、同一端口，服务被杀掉之后
[2026-10-16T14:25:40Z] ace  (backend=psutil)
  主机  cpu= 74.4%  mem= 45.7%  disk= 38.3%  load=9.03/7.03/5.57  cores=4  uptime=1545195s
  应用  http://127.0.0.1:18081/            down code=None  latency=28.955ms  URLError: <urlopen error [Errno 111] Connection refused>
```

**结论**：
- 探活失败时 `http_code=None`、`status=down`，**并且把原因原文记下来了**
  （`Connection refused`）——这是排障时最值钱的一个字段：连接被拒是「进程没了」，
  `TimeoutError` 是「进程还在但不响应」，两种故障的处理方式完全不同；
- 注意 `down` 时 `latency` 仍有 28.9 ms：那是**失败前的等待时间**，
  不是「响应时间」。看不懂这一点就会在延迟看板上被误导；
- 探活的超时口径（`timeout=2.0s`）在自检里被单独钉住：本地桩故意 sleep 0.25s，
  用 `timeout=0.05` 探它必须得到 `down / TimeoutError`。

**清理**：`kill %1`（后台的 `http.server`）；端口 18081 实验后无监听。

---

## 实验 4：端到端 —— 用 Docker 造一个「被监控的服务」，然后把它停掉（重点实验）

**目的**：验证整条链路在真机上闭环：**容器活着 = 无告警；容器被停 = 告警；容器再起 = 恢复通知。**

**准备**：
```bash
docker run -d --name d182-web -p 18082:80 nginx:alpine
python3 06-webhook-receiver.py --port 19090 --log /tmp/day182/live/hook.jsonl &
```

**执行**（平台每 2s 采一次，中途停/起容器）：
```bash
python3 05-platform-demo.py --serve --live --count 10 --interval 2 --probe http://127.0.0.1:18082/ --webhook http://127.0.0.1:19090/hook --file /tmp/day182/live/platform.jsonl &
sleep 6 ; docker stop d182-web
sleep 7 ; docker start d182-web
wait
```

**实际结果**（真机 stdout，2026-10-16T14:25:53Z ~ 14:26:13Z）：

```
真机模式：采集 10 次，间隔 2.0s，probe=['http://127.0.0.1:18082/']，dry-run=False
  [2026-10-16T14:25:53Z] cpu=97.6% mem=42.0% disk=38.4% probe=[('http://127.0.0.1:18082/', 'up')]
      pending  -          host_cpu_high
  [2026-10-16T14:25:56Z] cpu=94.9% mem=42.1% disk=38.4% probe=[('http://127.0.0.1:18082/', 'up')]
      pending  -          host_cpu_high
  [2026-10-16T14:25:58Z] cpu=87.5% mem=42.3% disk=38.4% probe=[('http://127.0.0.1:18082/', 'up')]
      dropped  -          host_cpu_high
  [2026-10-16T14:26:00Z] cpu=97.5% mem=42.7% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
      pending  -          host_cpu_high
      pending  -          app_down
  [2026-10-16T14:26:02Z] cpu=89.7% mem=42.5% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
      dropped  -          host_cpu_high
   t=1792160763 告警       [critical] app_down app_metrics[0].status 越界 (值=0.0 阈值=0.5) | 路由=critical      webhook+file+console->webhook
  [2026-10-16T14:26:04Z] cpu=80.0% mem=42.1% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
  [2026-10-16T14:26:06Z] cpu=87.5% mem=42.7% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
  [2026-10-16T14:26:09Z] cpu=100.0% mem=42.6% disk=38.4% probe=[('http://127.0.0.1:18082/', 'up')]
      pending  -          host_cpu_high
   t=1792160769 恢复       [critical] app_down app_metrics[0].status 恢复 (值=1.0 阈值=0.5) | 路由=critical      webhook+file+console->webhook
  [2026-10-16T14:26:11Z] cpu=90.2% mem=43.1% disk=38.4% probe=[('http://127.0.0.1:18082/', 'up')]
      pending  -          host_cpu_high
  [2026-10-16T14:26:13Z] cpu=82.9% mem=42.6% disk=38.4% probe=[('http://127.0.0.1:18082/', 'up')]
      dropped  -          host_cpu_high
汇总：样本 10 | 事件 11 | 通知 1 | 去重 0 | 恢复 1 | 投递 {'webhook': 2}
```

webhook 接收端**真的收到了**这两条（落盘文件 `/tmp/day182/live/hook.jsonl` 原样内容，2 行）：

```
{"name": "app_down", "type": "firing", "status": "firing", "severity": "critical", "metric": "app_metrics[0].status", "value": 0.0, "threshold": 0.5, "flapping": false, "summary": "[critical] app_down app_metrics[0].status 越界 (值=0.0 阈值=0.5)", "labels": {"rule": "app_down", "metric": "app_metrics[0].status"}, "ts": 1792160762.8318417}
{"name": "app_down", "type": "resolved", "status": "resolved", "severity": "critical", "metric": "app_metrics[0].status", "value": 1.0, "threshold": 0.5, "flapping": false, "summary": "[critical] app_down app_metrics[0].status 恢复 (值=1.0 阈值=0.5)", "labels": {"rule": "app_down", "metric": "app_metrics[0].status"}, "ts": 1792160769.1524293}
```

接收端自己的 stdout（另一次同类实验，2026-10-16T22:27:12）：

```
webhook 接收端已启动：http://127.0.0.1:19090/hook  （日志 /tmp/day182/live/hook2.jsonl，Ctrl-C 退出）
[22:27:12] #1 app_down status=firing severity=critical value=0.0
```

**结论**（这是本日最重要的一段）：
- 容器 stop 后**第 1 个采样点**（约 1s 后）探活就变 `down`，`consecutive=2` 让它在第 2 个点升级为告警；
  容器 start 后第 1 个采样点直接进 `resolved`，恢复通知随发；
- **两台机器（这里是一个进程扮演三个角色）之间真的发生了 HTTP POST**：
  平台 → `127.0.0.1:19090` 的 JSON 就是上面那两行，不是打印出来的假日志；
- **降噪真的发生了**：10 个采样点里 `app_down` 相关的事件有 5 个（pending/pending/firing/中间三次不发/resolved 前），
  最终只有 **2 条通知**（1 故障 + 1 恢复）；样本 10 → 事件 11 → 通知 2；
- 顺带复现了一个**真实的抖动**：这台机器负载本来就高（load 8+），
  `host_cpu_high` 在 97.6 / 94.9（pending、pending）之后 87.5 掉下来（dropped），
  后面又 97.5、89.7、100.0、90.2、82.9 反复穿越——**从头到尾一次都没 firing**。
  这就是「连续 3 次」在真实世界里的作用：**这台 4 核机器当时的 CPU 其实一直在报警边缘，但没打扰任何人。**
- `/tmp/day182/live/platform.jsonl` **不存在**——因为 webhook 成功了，
  file 只是 fallback，不该被写。这是路由「顺序链」而不是「广播」的直接证据。

**清理**：见文末「清理」一节（本实验后已执行，端口 18082 / 19090 实测无监听，容器已删）。

---

## 实验 5：降级 —— 把 webhook 打到没人听的端口

**目的**：验证通道挂了以后的降级链，以及「全部失败必须如实上报」。

**执行**：
```bash
python3 03-alert-routing.py --demo --webhook http://127.0.0.1:19999/hook --file /tmp/day182/live/fallback.jsonl
```

**实际结果**（真机 stdout，2026-10-16）：

```
路由演练（webhook=http://127.0.0.1:19999/hook file=/tmp/day182/live/fallback.jsonl）
  >> [critical] host_disk_high host_metrics.disk_percent 越界 (值=91.0 阈值=85)
      webhook 发送失败（第 1 次）：URLError: <urlopen error [Errno 111] Connection refused>
      webhook 发送失败（第 2 次）：URLError: <urlopen error [Errno 111] Connection refused>
     路由=critical      链=webhook->file->console       投递=file /tmp/day182/live/fallback.jsonl
  >> [warning] app_latency_slow app_metrics[0].latency_ms 越界 (值=880.0 阈值=500)
     路由=warning       链=file->console                投递=file /tmp/day182/live/fallback.jsonl
  >> [critical] host_cpu_high host_metrics.cpu_percent 越界 (值=96.0 阈值=90)
     路由=flap-silenced 链=file                         投递=file /tmp/day182/live/fallback.jsonl
```

平台层的降级（真机，容器已被停掉 + webhook 打空端口）：

```
真机模式：采集 3 次，间隔 1.0s，probe=['http://127.0.0.1:18082/']，dry-run=False
  [2026-10-16T14:26:28Z] cpu=67.5% mem=42.6% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
      pending  -          app_down
  [2026-10-16T14:26:29Z] cpu=76.3% mem=42.6% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
      webhook 发送失败（第 1 次）：URLError: <urlopen error [Errno 111] Connection refused>
      webhook 发送失败（第 2 次）：URLError: <urlopen error [Errno 111] Connection refused>
   t=1792160790 告警       [critical] app_down app_metrics[0].status 越界 (值=0.0 阈值=0.5) | 路由=critical      webhook+file+console->file
  [2026-10-16T14:26:30Z] cpu=87.5% mem=43.0% disk=38.4% probe=[('http://127.0.0.1:18082/', 'down')]
汇总：样本 3 | 事件 2 | 通知 1 | 去重 0 | 恢复 0 | 投递 {'file': 1}
```

**结论**：
- critical 告警**没有丢**：webhook 失败 2 次 → 落 file → 投递成功，报告里 `投递=file`
  （链路 `webhook+file+console->file` 一眼看出「前两个没成功、第三个成功」）；
- warning 告警**根本没碰 webhook**（链是 `file->console`），
  证明路由是「按级别选路」而不是「全都试一遍」；
- 抖动告警走 `flap-silenced` 路由，链上只有 `file`——**不会有人被叫起来**；
- 失败原因（`Connection refused`）被逐条记进 `errors`，不是吞掉。

**清理**：无（只写了一个 /tmp 下的 jsonl，随 `rm -rf /tmp/day182` 一起删）。

---

## 实验 6：六个脚本的离线自检（含耗时实测）

**目的**：证明每一层都能**在没有网络、没有 Docker、没有真实故障**的情况下自证正确。

**执行**：
```bash
cd code
for f in 01-collect-metrics 02-threshold-engine 03-alert-routing \
         04-alert-dedup-recovery 05-platform-demo 06-webhook-receiver; do
  /usr/bin/time -f "%e s | %M KB" python3 $f.py --self-test
done
```

**实际结果**（真机，/usr/bin/time 测量，2026-10-16）：

| 脚本 | 退出码 | 耗时 | 峰值内存 | PASS 数 |
|---|---|---|---|---|
| 01-collect-metrics | 0 | **1.34 s** | 24888 KB | 14 |
| 02-threshold-engine | 0 | **0.03 s** | 12872 KB | 14 |
| 03-alert-routing | 0 | **0.80 s** | 23880 KB | 16 |
| 04-alert-dedup-recovery | 0 | **0.04 s** | 16692 KB | 16 |
| 05-platform-demo | 0 | **0.76 s** | 24024 KB | 19 |
| 06-webhook-receiver | 0 | **0.75 s** | 23388 KB | 4 |
| **合计** | 全部 0 | **≈3.7 s** | — | **83** |

> 测量条件：单进程串行执行，本机 load ≈ 8（偏忙）；01 的 1.34s 里有约 3×0.1s
> 是 CPU 采样窗口的固定睡眠。内存含 Python 解释器本身的约 9 MB。

关键脚本的自检输出（原样，节选）：

```
$ python3 02-threshold-engine.py --self-test
  PASS  release > threshold（op='>'）被拒绝
  PASS  release < threshold（op='<'）被拒绝
  PASS  单次尖峰：只出 pending + dropped，不出 firing（实测 ['pending', 'dropped']）
  PASS  单次尖峰后状态回到 ok（实测 ok）
  PASS  连续 3 次越界只 firing 一次（实测 1 次）
  PASS  升级发生在第 3 次越界（实测 breach_run=3）
  PASS  迟滞：85 在 (release=80, threshold=90] 之间，保持 firing 且无事件
  PASS  跌破 release=80 -> resolved（实测 resolved）
  PASS  恢复后再次越界 -> 再次 firing
  PASS  窗口内翻转 4 次后判定为抖动（flapping=True）
  PASS  窗口 2s、采样间隔 10s 时不会误判抖动（时间窗口生效）
  PASS  extract 取字典路径
  PASS  extract 把 down 映射成 0.0
  PASS  RuleSet 端到端：app down 进入 pending（consecutive=2）
self-test 通过 | 参数校验 2 + 行为断言 9 全部成立

$ python3 04-alert-dedup-recovery.py --self-test
  PASS  同一故障连来 3 次 -> 只通知 1 次（实测 ['notify', 'suppress', 'suppress']）
  PASS  被去重的告警仍然在计数（实测 count=3）
  PASS  状态表里只有 1 条活动告警（实测 1）
  PASS  value 不同但指纹相同（f05360f106d8 == f05360f106d8）
  PASS  不同 instance 各通知一次（实测 notify / notify）
  PASS  不同 instance 指纹不同（f05360f106d8 != 8d1c84ba6b8f）
  PASS  两条活动告警并存（实测 2）
  PASS  resolved 触发恢复通知（实测 recover）
  PASS  恢复通知带上被去重的次数（实测 count=2）
  PASS  恢复通知带活动时长（实测 恢复；活动时长 60s）
  PASS  重复的恢复通知被丢弃（实测 drop）
  PASS  恢复后状态表清空（实测 0）
  PASS  恢复后再次故障 -> 重新通知（实测 notify）
  PASS  未恢复超过 resend_interval 再提醒一次（实测 ['notify', 'suppress', 'renotify']）
  PASS  把 status 放进指纹后：恢复通知变成 drop（实测 drop）——这就是那个坑
  PASS  两种状态的指纹不同（8570a82c242d != c6ab7a8c93fd）
self-test 通过 | 去重 3 + 恢复 5 + 再提醒/指纹陷阱 2 全部成立

$ python3 05-platform-demo.py --self-test
  PASS  四个同目录模块都从真实文件加载成功
  PASS  跑完整条时间线，共 32 个采样点（实测 32）
  PASS  cpu 前两次越界只到 pending，被挡在告警通道之外（实测 2）
  PASS  首次告警 7 条：cpu 1 + 延迟抖动 6（实测 7）
  PASS  恢复通知 6 条：cpu 1 + 延迟 5（实测 6）
  PASS  阈值引擎只在状态变化时吐事件，这一轮没有重复告警要去重（实测 suppress=0 renotify=0）
  PASS  抖动判定生效后 8 条通知改走静默路由（实测 routes={'critical': 2, 'warning': 3, 'flap-silenced': 8}）
  PASS  critical 的 1 告警 + 1 恢复走 webhook（实测 {'webhook': 2, 'file': 11}）
  PASS  收数桩实测收到 2 条 payload（故障 + 恢复）
  PASS  payload 名字是 host_cpu_high（['host_cpu_high', 'host_cpu_high']）
  PASS  payload 一条 firing 一条 resolved（['firing', 'resolved']）
  PASS  通知数（13）远少于采样数（32）——这就是降噪
  PASS  webhook 全挂时，所有通知降级到 file（实测 {'file': 13}）
  PASS  降级场景下 webhook 一次也没成功
  PASS  降级通道的落盘文件非空（4850 字节）
  PASS  降级落盘的第一条是 cpu 告警（实测 host_cpu_high/firing）
  PASS  dry-run 模式全程没写盘
  PASS  dry-run 也如实汇报「本应投递」的条数（13）
  PASS  无状态源连发 10 条同指纹告警 -> 压成 1 条通知（实测 ['notify', 'suppress', ..., 'suppress']）
self-test 通过 | 场景 A/B/C/D 全部断言成立（采样 32 -> 通知 13，抖动静默 8，去重 10->1）
```

**结论**：
- 83 条断言全部通过，且**每条断言都打印实测值**（不是「跑了没报错」）——
  这是这一系列脚本的风格，出问题时一眼能看出是「预期错」还是「实现错」；
- `05` 的自检用**假时钟 + 假快照**把 32 个采样点毫秒级跑完，但**投递是真的**——
  它起了一个本地 HTTP 收数桩，断言桩里真的收到了 2 条 payload。
  「离线可跑」不等于「什么都没验证」。

---

## 实验 7：清理与残留自检

**执行**（也是每次实验后都该做的）：
```bash
docker rm -f d182-web                                   # 收容器
pkill -f "06-webhook-receiver.py --port 19090"          # 收接收端
pkill -f "http.server 18081"                            # 收实验 3 的临时服务
rm -rf /tmp/day182                                      # 收临时目录
```

**自检项与实测结果**：
```bash
$ ss -ltnp | grep -E ':18081|:18082|:19090'
无残留端口
$ docker ps -a --format '{{.Names}}' | grep d182
无残留容器（d182-*）
$ ps aux | grep -E 'day182|05-platform|06-webhook|01-collect' | grep -v grep
无残留进程
```

> 说明：`pkill -f` 里一定要带足够具体的模式（`06-webhook-receiver.py --port 19090`），
> 不要写 `pkill -f python3` ——那会把别人的 Python 一起打死。本机还有别人的容器在跑
> （`dk-*`、`cranky_sammet`），实验全程没有碰它们。

---

## 翻车复盘（本日真实踩到的 5 个问题）

### 1. `to_alert()` 把 `pending` 误映射成 `resolved` —— 自检抓到的设计 bug

**症状**：`05` 的流水线统计里，`notify` 之外冒出一堆 `drop`（「收到恢复通知但没有对应的活动告警」）。

**根因**：`03` 的 `to_alert()` 最初写成
```python
"status": "firing" if is_fire else "resolved",     # 只要不是 firing 就当恢复
```
于是 `02` 吐出的 `pending`（还没到该报警的程度）和 `dropped`（被过滤的毛刺）
都被包装成了 `resolved` 告警塞给了去重层——去重层找不到对应的活动告警，只能 drop。

**修复**：显式三态映射（`firing / resolved / pending`），并且让**流水线在 `pending`/`dropped` 处直接截断**：

```python
if event["type"] not in ("firing", "resolved"):
    self.stats["filtered"] += 1      # pending / dropped 只在前两层内部消化
    continue
```

**复测**：`PASS cpu 前两次越界只到 pending，被挡在告警通道之外（实测 2）`。

> 教训：**枚举状态一定不要用「否则就是另一种」这种二分法写。** 三态写成二态，
> 中间态就被静默地当成最后一个分支处理了——而且没有任何报错，只在统计里露出一点马脚。

### 2. 「去重层好像没用」——其实是我对流水线的预期错了

**症状**：`05` 自检里我断言持续越界的 7 个采样点会被去重（`suppress == 7`），
实测 `suppress == 0`，缓存 4 条断言全红。

**排查**：打印每层输出后发现，**`02` 的引擎在状态不变时根本不吐事件**——
它从 firing 到 resolved 之间一个事件都不发。所以「重复告警」压根没走到去重层。

**根因**：这不是 bug，是**层与层的职责边界**。去重层真正的服务对象是：

1. 无状态的上游（每次采样都发一条告警，比如直接用 Prometheus webhook 转发、多采集器重复上报）；
2. 进程重启后状态丢失、同一个故障被重新上报；
3. 多实例/多副本同时上报同一个故障。

**修复**：把断言的期望值改成实际值（`suppress == 0`），并**补了场景 D**用无状态源验证去重层：

```
PASS  阈值引擎只在状态变化时吐事件，这一轮没有重复告警要去重（实测 suppress=0 renotify=0）
PASS  无状态源连发 10 条同指纹告警 -> 压成 1 条通知（实测 ['notify', 'suppress', ... 'suppress']）
```

> 教训：**测试失败时先分清「实现错了」还是「预期错了」。** 这次是预期错了，
> 但改预期之前必须先解释清楚「为什么实际值才是对的」——解释不清就别改断言，那是掩盖 bug。

### 3. 超时探活把自检的服务端打成异常刷屏（`BrokenPipeError`）

**症状**：`01 --self-test` 一开始会先吐一段红色的 socketserver traceback：

```
Exception occurred during processing of request from ('127.0.0.1', 37774)
...
BrokenPipeError: [Errno 32] Broken pipe
```

**根因**：自检里有一条「客户端 0.05s 超时」的用例。客户端超时后立刻关掉了连接，
而桩服务还在 `time.sleep(0.25)`，等它醒过来写 response 时连接早没了 → `BrokenPipeError`。

**修复**：桩里写回时容忍这两种「对端先走」的异常：

```python
try:
    self.wfile.write(body)
except (BrokenPipeError, ConnectionResetError):
    pass   # 探活方超时后先断开，服务端写回时就会撞上 BrokenPipe
```

**复测**：`01 --self-test` 输出干净，14 条 PASS。

> 教训：这一段 traceback **不是 bug，是健康的信号**——它精确说明了「超时」在 TCP 层面长什么样：
> 客户端放弃等待、连接被撕掉。写 Web 服务时同理，这类异常必须显式吞掉，
> 否则日志会被正常的客户端超时刷满。

### 4. 接收端被 `kill` 之后，日志里只剩启动那一行

**症状**：实验 4 第一次跑完，接收端的 stdout 只有「已启动」，但它的落盘 jsonl 里明明有 2 条告警。

**根因**：stdout 被重定向到文件时是**块缓冲**的（不是行缓冲）。进程被 `SIGTERM` 杀掉时，
缓冲区里那两条打印**跟着进程一起消失了**。（落盘用的是 `with open(...) as fh:`，每次自动 close，所以没丢。）

**修复**：`06` 里每条打印后显式 `sys.stdout.flush()`。

**复测**：重跑同类实验，接收端 stdout 正常：

```
[22:27:12] #1 app_down status=firing severity=critical value=0.0
```

> 教训：**长驻进程的 stdout 一定要逐条 flush**（或 `python3 -u`），
> 否则「日志没写出来」会被误判成「事件没发生」。

### 5. 容器停/起的采样赛跑

**症状**：第一版实验把 `docker stop` 安排在采样点正中间，结果第一个 `down` 样本
比预期晚了一个周期，导致 `consecutive=2` 的告警延后。

**根因**：`docker stop` 本身要 ~1s 发送信号并等待进程退出，探活的下一个采样点可能正好落在
「容器还没完全停、端口还开着」的缝隙里。**监控系统的采样间隔和运维动作的耗时是同一个数量级时，
这类「晚一个周期」是常态，不是 bug。**

**处理**：把 `interval` 放到 2s、并在读完前 3 个样本后才动手，让现象稳定可复现
（实验 4 里 `docker stop` 在 14:25:59，第一个 `down` 样本在 14:26:00）。

> 教训：**告警延迟不是纯粹的软件问题，它等于「采样间隔 + 连续次数窗口 + 判定周期」。**
> 本日实测：2s 间隔 + 2 次连续 ⇒ 从故障发生到收到通知约 3~4 秒。
> 想更快只能缩短采样间隔（更贵），或者接受这个数字并写进 SLA。

---

## 清理（每次实验后都做）

```bash
docker rm -f d182-web                                   # 实验 4 的 nginx 容器
pkill -f "06-webhook-receiver.py --port 19090"          # 实验 4/5 的收数桩
pkill -f "http.server 18081"                            # 实验 3 的临时服务
rm -rf /tmp/day182 /tmp/day182-capture                  # 临时数据（快照/告警/截图）

# 自检
ss -ltnp | grep -E ':18081|:18082|:19090' || echo "无残留端口"
docker ps -a --format '{{.Names}}' | grep d182 || echo "无残留容器"
```

**本日实测结果**：`无残留端口 / 无残留容器（d182-*） / 无残留进程`（见实验 7）。

---

## 未实测（诚实清单）

| 项 | 原因 | 预期结果 | 验证方法 |
|---|---|---|---|
| 真实 IM 通道（飞书/钉钉/企业微信机器人） | 本日只用一个**本地**接收端验证「POST 真的发出去了」，不往外部服务发数据 | 各家的机器人要的是自己的 JSON 结构（飞书是 `msg_type` + `content`），且多数要求签名/关键词校验 | 把 `03` 的 `WebhookChannel` 子类化，覆盖 `send()` 里的 body 结构；先对一个测试群跑通，再加签名校验 |
| Alertmanager 的 `group_interval` / `inhibit_rules` 对照实验 | 本机没跑 Alertmanager（Day 177 已记录镜像拉取不稳） | 本日的 `resend_interval` ≈ `repeat_interval`；本日的「抖动静默」与 `inhibit_rules` 目的一致但机制不同（一个是状态判定，一个是规则匹配） | 若镜像可用：起 `prom/alertmanager`，把本日的路由表翻译成 `route`/`inhibit_rules`，用 `amtool` 发假告警比对通知条数 |
| 跨进程/跨机器去重（本日状态表在内存里） | 进程重启即丢状态；多副本会各自报警 | 单机单进程下正确；重启后同一故障会再通知一次（幂等性丢失） | 把 `AlertStore.table` 换成 Redis 的 `HSET`（key = 指纹），并给写操作加 TTL；用两个进程同时 `process()` 断言只发一次 |
| 告警通道的指数退避与熔断 | 本日只有固定 `attempts=2` | 对端长时间不可用时会持续重试，占用判定周期 | 在 `Router` 里给每个通道维护 `next_retry_at`（指数退避），并加半开探测 |
| 磁盘专项规则（`--scenario disk`） | 演示数据已给出（50→86→88…），但没有真实把磁盘写满来触发 | 磁盘预测可用「趋势 + 剩余可用天数」而非固定阈值 | 用 `fallocate` 造一个临时大文件逼近阈值（注意清理），或在 tmpfs 上做 |

---

## 思考题

1. 本日 `01` 里，`/proc` 后端和 psutil 后端对同一台机器给出 `disk 38.3%` 与 `disk 36.3%`
   （差了 2 个点）。如果告警规则阈值是 37%，会发生什么？这说明「阈值」和什么必须绑在一起定？

**参考答案**

阈值取 37% 时，**同一台机器、同一时刻会得到两种相反的命运**：psutil 口径 38.3% > 37% 判越界，`/proc` 口径（`shutil.disk_usage`）36.3% < 37% 判正常。而且本日磁盘规则 `host_disk_high` 是 `consecutive=1`（没有毛刺过滤），psutil 口径第一个样本就直接 firing，proc 口径则永远安静。

由此会出三种真实事故：

- **告警「凭空出现/消失」**：psutil 被卸载或 import 失败时 `01` 自动回退 `/proc`，告警随之消失——磁盘一个字节都没变，变的只是测量口径；
- **校准错觉**：拿 A 工具的历史数据校准阈值，再用 B 工具跑，2 个点的口径差足以让阈值骑在告警线上反复横跳；
- 同样的道理也适用于 mem（45.2% vs 45.3%，`MemAvailable` 公式不同）和 CPU（采样窗口长短不同）。

所以**阈值必须和「采集口径」绑在一起定**：哪个工具、哪个公式、哪个挂载点、多长的采样窗口，乃至 `consecutive` 与采样间隔（时间口径）。工程上的做法是：固定 backend 与版本、用快照里的 `backend` 字段做审计、用同一口径的历史数据校准阈值，并给口径差异留余量（比如定 40% 而不是 37%）。

💡 提示：这正是实验 1 的结论——「不能拿 A 工具的数去配 B 工具的规则」。阈值不是绝对物理量，而是相对于测量方式的约定。

2. 迟滞带宽度取 10 个点（90 / 80）。如果这台机器的指标抖动振幅是 15 个点，迟滞还管用吗？
   此时该改迟滞带，还是该改用别的手段？（提示：想想抖动判定和「连续 N 次」分别在治什么）

**参考答案**

**不管用了。** 迟滞的算术是「带宽 > 抖动振幅 → 吸收；带宽 < 振幅 → 每次波动都翻转」。振幅 15 个点（比如在 95↔80 之间横跳）会同时穿越进入线 90 和恢复线 80，每个来回都产生一次 firing→resolved 翻转。用复刻 `02` 状态机的代码实跑验证（consecutive=1，1 tick = 1 秒，聚焦迟滞本身）：

```python
def simulate(values, release, threshold=90.0, flap_window=300.0, flap_limit=4):
    """复刻 02 的状态机（consecutive=1，1 tick = 1 秒），聚焦迟滞与抖动"""
    state, transitions, events = "ok", [], []
    for t, v in enumerate(values):
        etype = None
        if v > threshold:                      # 越界
            if state != "firing":
                state, etype = "firing", "firing"
        elif state == "firing":
            if v <= release:                   # 跌破恢复线才算恢复
                state, etype = "ok", "resolved"
            # 没到恢复线：保持 firing（迟滞）
        if etype:
            transitions.append(float(t))
            transitions = [x for x in transitions if x >= t - flap_window]  # 滑动时间窗口
            flapping = len(transitions) >= flap_limit
            events.append((t, v, etype, flapping))
    return state, events

values = [95.0, 80.0] * 6                      # 振幅 15 个点，在 95/80 之间反复横跳
for release in (80.0, 75.0):
    state, events = simulate(values, release)
    print("release=%.0f（带宽 %.0f）: 翻转 %d 次, 出现过 flapping=%s, 最终状态=%s"
          % (release, 90.0 - release, len(events), any(e[3] for e in events), state))
```

预期输出：

```
release=80（带宽 10）: 翻转 12 次, 出现过 flapping=True, 最终状态=ok
release=75（带宽 15）: 翻转 1 次, 出现过 flapping=False, 最终状态=firing
```

两个结论：

- **加宽迟滞带（release 80→75）确实能吸收**，但代价看得见：80 不再算恢复，指标一半时间低于阈值 90 也永远 firing——恢复变得迟钝甚至「永不恢复」。带宽越宽抗抖越强、恢复越钝，这是权衡不是免费午餐。
- **「连续 N 次」救不了真抖动**：「坏 30 秒、好 30 秒」的故障每轮都真的连续超 N 次（实验 2 的 flap 场景就是 95,95,95,60,…）。连续次数治的是「一次性毛刺」，治不了「反复横跳」。

所以此时的正解是**抖动判定**：上面 release=80 的演示里，窗口内第 4 次翻转就打上 `flapping=True`，`03` 的 `flap-silenced` 路由把它降级成「只留档、不叫人」。三个工具各司其职：连续次数挡毛刺、迟滞挡边界小震荡、抖动判定挡真抖动——识别出抖动后应该去修根因（OOM 循环、网络闪断），而不是硬压通知。

⚠️ 注意：加宽带时必须保持 `release <= threshold`（op='>' 时），`02` 的参数校验会拒绝写反——否则状态机卡在 firing 永远出不来。

3. `02` 里抖动判定用的是「时间窗口内的翻转次数」。如果换成「总翻转次数」，
   一个稳定运行 30 天、每天抖 1 次的系统会怎样？为什么本日自检要专门断言
   「窗口 2s、采样间隔 10s 时不会误判抖动」？

**参考答案**

用「总翻转次数」，这个稳定系统会被**永久误判成抖动**。每天抖 1 次（firing+resolved 共 2 次翻转），第 2 天累计就到 4 次、达到 `flap_limit=4`；而且总次数只增不减，标签一旦贴上就永远摘不掉。后果：它之后所有告警——包括真正持续的故障——都被 `flap-silenced` 路由降级成只留档不叫人，**降噪机制变成了漏报机制**。实跑对比两种判定：

```python
flap_limit = 4
window = 300.0                     # 本日默认 flap_window=300s
total_flips = 0                    # 错误做法：累计总次数
window_flips = []                  # 正确做法：只保留窗口内的时间戳
for day in range(30):              # 稳定运行 30 天，每天抖 1 次
    for k in range(2):             # 每次抖动 = firing+resolved 共 2 次翻转，间隔 10 秒
        now = day * 86400 + k * 10
        total_flips += 1
        window_flips = [t for t in window_flips if now - t <= window]
        window_flips.append(now)
print("30 天后 总次数判定 flapping =", total_flips >= flap_limit)
print("30 天后 时间窗口判定 flapping =", len(window_flips) >= flap_limit)
```

预期输出：

```
30 天后 总次数判定 flapping = True
30 天后 时间窗口判定 flapping = False
```

自检专门断言「窗口 2s、采样间隔 10s 时不会误判抖动」，就是为了钉死这个语义：**抖动 = 短时间内的反复翻转，不是「历史上翻转过很多次」**。同样的 7 次翻转，每次之间平静了 10 秒，2s 窗口里任何时刻最多只有 1 次翻转，永远凑不够 4 次——那是「偶尔出事」，不是「反复横跳」。这条断言防止有人把滑动窗口「优化」成累计计数器。

💡 提示：滑动窗口还有一个好处——标签会**自己消失**：旧翻转滑出窗口后 `flapping` 自动回到 False（实验 2(d) 第 13 行的 pending 就不再带抖动标签）。总次数永远做不到这一点。

4. `03` 的路由链是**顺序**尝试的（webhook 失败才落 file）。如果改成**并行**
   （三个通道同时发），会带来什么运维问题？（提示：值班同学在不同地方看到不同状态）

**参考答案**

改成并行（三个通道同时广播）会制造至少四类运维问题：

- **对账对不上**：一次故障在三个地方各留一份，不知道哪份是权威。报告里 `delivered_by` 的语义直接崩坏——到底算 webhook 还是 file？实验 4 的直接证据是 `/tmp/day182/live/platform.jsonl` **不存在**：webhook 成功了，file 就不该被写；并行模式下这条证据消失，事后无法还原「这条告警到底送达了没有」。
- **值班同学在不同地方看到不同状态**：webhook 延迟或失败、file/console 却已有记录。看群的人以为「没人管」，看落盘的人以为「已通知」——要么没人响应，要么多人重复响应；恢复通知发出后，各渠道的状态更加不同步。
- **分级路由失效**：路由的意义就是 warning 不碰 webhook、flapping 只留档（实验 5：warning 的链是 `file->console`）。并行广播等于每条告警全通道都发，半夜把 warning 打进值班电话——正是路由表要防的事故。
- **失败语义与负载失控**：部分成功部分失败算成功还是失败？失败通道要不要重试？重试又会在已成功的通道里制造重复（接收端必须做幂等）。告警风暴时每条告警 × 3 通道 × attempts 放大负载，外部 IM 的限流更容易被触发，真正的 critical 反而发不出去。

顺序链的本质是：**一条告警只有一个权威投递结果，降级路径清晰、可审计**（`webhook+file+console->file` 一眼看出谁失败谁成功）。

💡 提示：如果业务真要多通道冗余，那是显式的「广播模式」——需要事件唯一 ID + 接收端幂等去重 + 明确的对账规则，复杂度代价远高于顺序链，不是把 `for` 改成线程就完事的。

5. 本日的去重表存在进程内存里，重启就丢。重启之后同一个故障会怎样表现？
   如果这个平台跑在 Kubernetes 的两个副本上（无共享状态），用户会收到几条通知？
   怎么改？（至少给出两种方案，并说明各自代价）

**参考答案**

**重启之后**：状态表清零，进行中的故障再次上报时被当成「新故障」→ 再次 `notify`（重复打扰），`renotify` 的计时也从零开始。更糟的是，如果此时来了 `resolved` 而表里没有活动告警（比如上游是无状态源、或恢复事件落到另一个副本），动作是 `drop`——**用户只看到故障，永远看不到恢复**。**两个副本无共享状态**：若两个副本都完整采集同一目标，各自都走一遍「首次」→ 用户收到 **2 条**通知；若事件被负载均衡到不同副本，firing 和 resolved 可能落在不同副本上，恢复通知变孤儿。实跑验证：

```python
import hashlib, json

def fingerprint(alert):
    """与 04 同构：name + severity + labels，不含 value/status/ts"""
    base = {"name": alert["name"], "severity": alert["severity"]}
    base.update(alert["labels"])
    return hashlib.sha256(json.dumps(base, sort_keys=True).encode("utf-8")).hexdigest()[:12]

alert = {"name": "app_down", "severity": "critical", "labels": {"instance": "ace"}}
fp = fingerprint(alert)

# 场景1：进程重启，表清零，同一故障再次上报
table = {}                         # 重启前这里本来有 fp 的记录（已通知过、count=3）
print("重启后同故障 firing ->", "notify（再喊一次）" if fp not in table else "suppress")

# 场景2：resolved 落到没有活动告警的表上（重启后 / 另一副本）
table_b = {}                       # 副本B 从没通知过这条 firing
print("副本B 收到 resolved ->", "recover" if fp in table_b else "drop（恢复通知变孤儿）")

# 场景3：两个副本都完整处理同一故障
tables = [{}, {}]
notifies = 0
for t in tables:
    if fp not in t:                # 各自都认为是「首次」
        t[fp] = 1
        notifies += 1
print("两副本都处理同一 firing，用户收到通知数 =", notifies)
```

预期输出：

```
重启后同故障 firing -> notify（再喊一次）
副本B 收到 resolved -> drop（恢复通知变孤儿）
两副本都处理同一 firing，用户收到通知数 = 2
```

改造方案（至少两种，各有代价）：

- **方案一：共享外部状态存储（推荐）**——把 `AlertStore.table` 换成 Redis：`HSET fp count first last_notify` 并给 key 加 TTL（正是 README「未实测」与 checklist 改造 2 的方向）。跨副本去重、重启恢复一次解决。代价：引入外部依赖（Redis 自己也要高可用和监控）；每次判定多一次网络往返；并发写必须用原子操作（`HSETNX`/Lua），否则两个副本仍会双发；TTL 难定——太短丢状态、太长膨胀。
- **方案二：本地持久化**——状态表落盘（JSON/SQLite），启动时加载、变更时刷盘。无外部依赖，解决单实例重启后的重复通知。代价：只救重启、救不了多副本（各写各的盘，照样双发）；要处理写盘时机与文件损坏；机器挂了状态照样丢。
- **方案三：单活/分片**——用 K8s Lease 选主让只有一个副本工作，或按目标（instance）分片，每台机器只归一个副本判定。不需要共享存储。代价：选主/分片逻辑复杂；故障切换窗口内可能漏报或重报；分片要维护目标元数据，副本扩缩容时还要再平衡。

💡 提示：还可以再加一层「接收端幂等」（通知网关按事件 ID 在时间窗内去重）兜底，但它把复杂度推给下游、要求所有通道配合，只能作补充，不能替代共享状态。

6. 实验 4 里 `host_cpu_high` 全程在 pending/dropped 之间来回，一次都没 firing。
   这是「正确的冷静」还是「漏报」？如果业务方投诉「CPU 都 97% 了你们居然不报警」，
   你会怎么改规则，代价是什么？

**参考答案**

**对「喊人处理故障」这个契约来说，这是正确的冷静。** 这台机器 4 核、load 8+，CPU 在 87%~100% 之间反复穿越 90，但从没连续 3 次——它是「忙」，不是「持续故障」。checklist 练习 7 的结论相同：若单次越界就报，这几分钟会响 6 次，`consecutive=3` 在真实机器上救了你一次。规则的契约是「持续越界才喊人」，引擎忠实执行了契约，不是 bug。

**但算不算「漏报」要看业务语义。** 如果业务 SLO 是「CPU 到 97% 哪怕几秒也会让请求超时」，那当前规则确实没覆盖这个需求——这是规则设计与业务需求不匹配，该改规则，而不是跟投诉争论。改法与代价：

- **调低 consecutive（3→2 或 1）**：响应更快；代价是毛刺风暴回归（本机实测会响 6 次），值班开始无视告警。
- **分级规则**：critical 保持 90/3 次（喊人），另加一条 warning 级 85/3 次只走 file 不打电话。代价是规则变多，warning 层也要治理噪音，否则留档爆炸。
- **换判定口径**：用 `load1/cpu_count` 或 5 分钟滑动平均代替瞬时 CPU。代价是响应变钝，且要保存历史样本（本日引擎是纯状态机，只吃当前值）。
- **缩短采样间隔**（30s→5s，3 次 = 15s 窗口）：不降阈值也能更快抓住真实持续高位。代价是采集/存储开销成倍增加。

更根本的做法：把告警绑在**业务症状**上（`app_latency_slow`、错误率），资源指标只作辅助证据。先和业务对齐「CPU 97% 对你意味着什么」，再把折中写进规则和 SLA。

⚠️ 注意：别为了安抚投诉直接降阈值——那会把「正确的冷静」变成「告警疲劳」，真故障来时反而没人看了。

7. 本日 `pending` 状态**不进入告警通道**（被流水线截断）。如果业务要求
   「进入 pending 也要通知，但标注为『观察中』」，最小改动是改哪一层？会不会破坏去重？

**参考答案**

**最小改动在 `05` 的流水线截断处**（`Pipeline.step` 里 `if event["type"] not in ("firing","resolved"): continue`），外加 `03` 加一条低噪音路由。`02` 不用动——它本来就吐带 `breach_run`（1/3、2/3）的 `pending` 事件；`03` 的 `to_alert()` 也已经是三态映射，会把 pending 包装成 `status="pending"`、summary 为「待观察」。所以只需：放行 `pending`（加个开关），路由表里加一条匹配 `status="pending"` 的路由只走 file/console（标注「观察中」，不打 webhook），`dropped` 仍然截断。

**会不会破坏去重，取决于 pending 进不进 `04` 的 `process()`。** 关键陷阱：`AlertStore.process` 只认 `firing`，**其余一律走 resolved 分支**。如果 naive 地放开截断、把 pending 直接塞进去重层，pending 会被当成恢复通知——同指纹已有活动告警时误判 `recover`、提前清掉状态，之后真正的 resolved 反而变 `drop`。实跑验证：

```python
# 复刻 AlertStore.process 的分支语义：只认 firing，其余一律走 resolved 分支
table = {}
fp = "f05360f106d8"                # 本日实测指纹（host_cpu_high/critical/instance=ace）

def process(status):
    if status == "firing":
        if fp not in table:
            table[fp] = 1
            return "notify"
        table[fp] += 1
        return "suppress"
    if fp not in table:            # resolved 分支：无活动告警 -> drop
        return "drop"
    del table[fp]                  # resolved 分支：匹配到 -> recover 并清状态
    return "recover"

print("firing   ->", process("firing"))     # 正常：故障通知
print("pending  ->", process("pending"))    # 事故：被当成恢复，状态被误清
print("resolved ->", process("resolved"))   # 事故：真正的恢复反而成了孤儿
```

预期输出：

```
firing   -> notify
pending  -> recover
resolved -> drop
```

所以正确姿势是：**观察通知绕过去重表**（不参与 firing/resolved 配对、不写状态），或给 `AlertStore` 增加显式的 `pending` 分支（只计数、不通知）。只要 pending 不碰 firing/resolved 的配对逻辑，去重就不会被破坏。这正是翻车复盘 1 的教训：三态不能写成二态，中间态必须显式处理。

⚠️ 注意：pending 本身也会刷屏（越界 1/3、2/3 各一条，下个周期又来），观察通知同样要限流（比如同指纹一个窗口只发一条），否则只是把「一分钟 20 条」的问题搬到了另一个通道。

8. `06` 的坑是「stdout 块缓冲 + SIGTERM」。如果这是一个在 K8s 里的 sidecar 容器，
   优雅退出（`preStop` + `SIGTERM` + 宽限期）会怎么改变这个现象？

**参考答案**

先复现现象：stdout 重定向到文件/管道时是**块缓冲**（约 8KB），而 SIGTERM 的默认处置是立即终止进程——Python 来不及跑 `finally`/`atexit`，缓冲区里的打印随进程一起消失。实跑验证（Windows 下 `terminate()` 是强杀，效果等价于 SIGTERM 的默认处置）：

```python
import os, subprocess, sys, tempfile, time

def run_and_kill(extra_args, code):
    """子进程 stdout 重定向到文件（块缓冲），1 秒后杀掉它"""
    fd, path = tempfile.mkstemp(suffix=".log")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        p = subprocess.Popen([sys.executable, *extra_args, "-c", code], stdout=fh)
        time.sleep(1.0)            # 等子进程执行完两条 print（但还躺在缓冲区里）
        p.terminate()              # 模拟 SIGTERM：默认处置立即终止，不刷缓冲
        p.wait()
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    os.unlink(path)
    return content

code = "import time; print('alert-1'); print('alert-2'); time.sleep(30)"
print("默认块缓冲 + 被杀 ->", repr(run_and_kill([], code)))
print("-u 无缓冲  + 被杀 ->", repr(run_and_kill(["-u"], code)))
```

预期输出：

```
默认块缓冲 + 被杀 -> ''
-u 无缓冲  + 被杀 -> 'alert-1\nalert-2\n'
```

K8s 优雅退出改变的是**给进程「准备后事」的时间**：`preStop` 钩子先执行（比如 sleep 几秒、或通知进程收尾），然后 kubelet 发 SIGTERM，最多等 `terminationGracePeriodSeconds`（默认 30s）才发 SIGKILL。但注意：**宽限期本身不救缓冲**——如果进程不处理 SIGTERM（像 `06` 的默认行为），信号一到照样立刻死，宽限期白给。必须用 `signal.signal(signal.SIGTERM, ...)` 注册处理器，在处理器里 `sys.stdout.flush()`、关文件、再退出，日志才写得出来。对 sidecar，preStop 还有一个用途：等主容器把日志写完再退，避免日志尾巴被截断。

所以完整答案分两层：优雅退出 + SIGTERM 处理器解决**计划内退出**的日志丢失；但 OOMKilled、节点宕机、宽限期超时后的 SIGKILL 根本不给你 flush 的机会。因此 `06` 的逐条 `sys.stdout.flush()`（或 `python3 -u` / `PYTHONUNBUFFERED=1`）仍是底线纪律——**每条立即写出去，不赌自己能死得优雅**。落盘用 `with open(...)` 每次自动 close，不受影响，这就是实验里 jsonl 有 2 条而 stdout 只剩启动行的原因。

⚠️ 注意：`except KeyboardInterrupt` 只接得住 SIGINT（Ctrl-C），接不住 SIGTERM；K8s 里容器 stdout 由运行时采集到节点日志文件，同样是管道、同样块缓冲，坑在容器里一模一样。

9. 如果采集本身就失败了（比如 psutil 抛异常、`/proc` 读不到），本日引擎会怎样？
   应该产生哪一类告警？（提示：想想 Prometheus 的 `up` 指标为什么是白送的——
   监控系统必须能区分「指标是 0」和「拿不到指标」）

**参考答案**

本日实现里有三种结局，都**不会产生「采集失败」告警**：

- **探活失败不算异常**：`probe_http` 捕获一切异常，转成 `status=down` + error 原文——这是「有效的观测数据」（进程没了），走正常 `app_down` 规则；
- **主机采集失败**：`01` 的 main 捕获 `RuntimeError` 打印「采集失败」退出码 2（psutil 抛其它异常则直接 traceback）；而 `05` 的 `real_run` 没有捕获，异常一路上抛——**整个平台进程崩掉**，监控自己先死了；
- **残缺快照 / NaN**：`02` 的 `RuleSet.evaluate` 对 `extract` 捕获 `KeyError/IndexError/...` 后静默 `continue`；`/proc` 读不到时返回的 NaN 更隐蔽——NaN 与任何数比较都是 False，既不越界也不恢复，**状态机原地冻结**。实跑验证：

```python
def extract(snap, path):
    """与 02 同构：按字典路径取值"""
    cur = snap
    for part in path.split("."):
        cur = cur[part]            # 缺字段 -> KeyError
    return float(cur)

good = {"host_metrics": {"cpu_percent": 95.0}}
bad = {"host_metrics": {}}                                  # 采集失败，字段没了
nan_snap = {"host_metrics": {"cpu_percent": float("nan")}}  # /proc 读不到时返回 NaN

for name, snap in (("正常  ", good), ("缺字段", bad), ("NaN   ", nan_snap)):
    try:
        v = extract(snap, "host_metrics.cpu_percent")
        print(name, "-> 取到值", v, "| >90 越界判定:", v > 90)
    except KeyError:
        print(name, "-> KeyError 被 evaluate 捕获后 continue：无事件、无告警（静默）")
```

预期输出：

```
正常   -> 取到值 95.0 | >90 越界判定: True
缺字段 -> KeyError 被 evaluate 捕获后 continue：无事件、无告警（静默）
NaN    -> 取到值 nan | >90 越界判定: False
```

应该产生的是**「监控自身健康」类告警**（如 `collector_down` / `scrape_failed`，severity=critical，带错误原因），同样走连续次数 + 去重 + 路由。这正是 Prometheus 白送 `up` 指标的原因：`up=0` 表示「抓取失败」，而不是「被监控的值是 0」——**监控系统必须区分「指标是 0」和「拿不到指标」**：前者是观测（app down 映射成 0.0），后者是没有观测，没有观测绝不能静默当成「一切正常」。还要补一条**数据新鲜度规则**：连续 N 秒没有新快照 → stale 告警，覆盖进程卡死不抛异常的情况。

⚠️ 注意：采集失败告警不能依赖已经失败的采集路径本身（通道要独立），否则全挂时它自己也发不出去；更大规模上要有「死人开关」——由外部 watchdog 监控监控平台，平台自己哑了就由它报警。

---

## 交付清单

| 文件 | 行数 | 字节 | 说明 |
|---|---|---|---|
| `README.md` | — | 本文件 | 概念/原理/速查/图解/实战/复盘/思考题 |
| `code/01-collect-metrics.py` | 385 | 14200 | 采集：主机指标（psutil + `/proc` 双后端）+ 应用探活 |
| `code/02-threshold-engine.py` | 353 | 14768 | 判定：连续次数 / 迟滞 / 抖动窗口 |
| `code/03-alert-routing.py` | 386 | 16864 | 路由：分级路由 + 重试 + 降级链 + `--dry-run` |
| `code/04-alert-dedup-recovery.py` | 231 | 10588 | 去重：指纹 + 状态表 + 恢复通知 + 再提醒 |
| `code/05-platform-demo.py` | 331 | 16278 | 串联：采集→判定→去重→路由（真机 / 假时钟双模式） |
| `code/06-webhook-receiver.py` | 141 | 5393 | 实验用最小 webhook 接收端 |
| `diagrams/README.md` | — | 6 张原理图 | 链路、状态机、迟滞、抖动、指纹、降级 |
| `exercises/checklist.md` | — | 练习与检查表 | 动手题 + 参考答案 + 自检表 |

> 六个脚本合计 **1827 行**（78091 字节），**83 条自检断言全部通过**，全部只需标准库（psutil 可选）。
> 本文所有命令输出均为 2026-10-16 在本机实测粘贴；未能实测的项目集中列在「未实测」一节。
