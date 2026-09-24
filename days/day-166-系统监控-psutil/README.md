# Day 166 — 系统监控（psutil）

> **Phase 11 — 自动化运维与 DevOps（Day 166–185）** · 主题：系统监控 · 子主题：实战
>
> **安全与边界声明**：
> - 本课所有代码只**读取本机指标**，不发送任何网络请求，不修改系统配置。
> - 演示进程只操作**本进程自己**（`os.getpid()`）和一个我们亲手启动的 `sleep` 子进程，
>   **绝不**对系统进程调用 `terminate()` / `kill()`。
> - 教材里出现的 IP 一律是文档网段（RFC 5737 的 `192.0.2.0/24`）。
> - 想要在生产机上跑监控脚本，请先用 `--dry-run` 或小 `--duration` 试跑。

---

## 1. 学习目标

完成本课后，你应该能够：

- 说清"监控"和"看一次数据"的本质区别，以及**轮询（polling）**与**事件（event）**两条路线的取舍
- 解释 psutil 的定位：为什么它是一个**库**，而不是 `top`/`free`/`df` 命令行的 Python 包装
- 分清三类指标：**计数器（counter）**、**瞬时值（gauge）**、**状态（state）**，并说出为什么搞混它们会得出错误结论
- 说清 `psutil.cpu_percent()` 为什么需要**两次读数**才能算出百分比，以及它内部到底除的是什么
- 解释 `cpu_percent(interval=None)` 首次调用返回 `0.0` 的根因，并给出三种正确写法
- 说清什么是**采样非原子性**，以及它为什么会让你看到"进程用了一个不存在的用户的 CPU"
- 解释 `rss` / `vms` / `uss` / `pss` 四个内存字段各自的含义与适用场景
- 说清 **pid 复用（pid reuse）** 陷阱，以及 `Process` 对象缓存带来的迷惑行为
- 解释为什么容器里 `psutil.virtual_memory().total` 会给出**宿主机的内存总量**，以及正确的读法
- 掌握 `NoSuchProcess` / `AccessDenied` / `ZombieProcess` 三个异常的出现条件与处理套路
- 能独立写出一个**带阈值告警、可输出 JSON/Markdown 报告**的系统监控脚本

---

## 2. 概念解释

### 2.1 先分清：监控 ≠ 读一次数据

很多人第一次写"监控脚本"，写出来的是这个东西：

```python
import psutil
print(psutil.cpu_percent())
```

这不是监控，这只是**一次采样**。监控（monitoring）这个词至少有四个组成部分：

```text
        ┌──────────────── 监控的四个组成部分 ────────────────┐
        │                                                   │
  ①  采集      ②  时间维度       ③  判定        ④  表达/交付
  采哪些指标    持续、带间隔、    阈值/趋势/      日志/告警/
              连续观察         基线对比         JSON/看板
        │            │                │              │
        └────────────┴────────────────┴──────────────┘
                    缺任何一个都不是"监控"
```

- **只有 ①** → 这是"查状态"，`top` 按一次 q 就退出。
- **只有 ①+②** → 这是"记录仪"，有数据但没有结论。
- **只有 ①+②+③** → 这是"告警器"，能用但会吵（阈值抖动、告警风暴）。
- **①+②+③+④** → 这才叫监控：**观测 → 判定 → 可复核的表达**。

本课的主线就是把这四块补齐。psutil 只负责第 ① 块（采集），
另外三块是我们自己写的逻辑 —— **别把工具的边界当成问题的边界**。

#### 为什么先说这个？

因为 psutil 的 API 长得太"顺滑"了：`cpu_percent()`、`virtual_memory()`、`disk_usage('/')`，
一行一个指标，容易让人以为监控就是"把这些值 print 出来"。
真正的坑全在 ②③④：**间隔取多少、两次读数之间发生了什么、阈值该定在哪、
抖动怎么抑制、数据怎么存**。这些 psutil 不替你想。

---

### 2.2 psutil 是什么，不是什么

**psutil = process and system utilities**（进程与系统工具）。

| 维度 | 说明 |
|:---|:---|
| 形态 | 纯 Python 库（底层少量 C 扩展），`pip install psutil` |
| 依赖 | 零外部依赖，不依赖 `top`/`free`/`vmstat` 等命令是否存在 |
| 平台 | Linux / Windows / macOS / FreeBSD / OpenBSD / NetBSD / SunOS / AIX |
| 数据源 | Linux = `/proc` 虚拟文件系统；macOS/BSD = `sysctl` 与系统调用；Windows = Win32 API |
| 授权 | BSD-3-Clause，可商用 |

**它是库，不是命令行的包装。** 这一点极其关键，对比一下就懂：

```text
❌ 反例：subprocess 调 top 再解析文本

   psutil 想要的值  ← top 的格式化输出 ← 终端宽度、locale、版本差异 ← 全靠正则硬啃
                                      ↑
                          列顺序变了 / 中文 locale 了 → 你的脚本当场去世

✅ psutil 的做法

   psutil 想要的值  ← 直接读 /proc/stat、/proc/meminfo、/proc/<pid>/stat

   → 拿到的是**结构化数字**，不是给人看的文本
   → 不受 locale、终端宽度、工具版本影响
```

命令行解析的三大脆性，psutil 一次性全部绕开：

1. **格式化脆性**：`top` 的头几行在不同发行版/版本上不一样，`free -m` 的单位和列名变过。
2. **语言脆性**：`LANG=zh_CN.UTF-8` 时某些工具的表头会变，正则立刻失配。
3. **依赖脆性**：容器里常常**没装** `top`/`free`（busybox 镜像尤甚），但 `/proc` 一定在。

> **原理锚点**：Linux 上"一切皆文件"不只是口号 —— `/proc` 是内核导出的
> **实时只读视图**。`psutil` 在 Linux 上基本就是"一个很懂 `/proc` 格式的解析器"。
> 理解了这一点，后面所有"为什么要两次读数""为什么会读到 0"的问题都能自己推出来。

#### psutil 不能做什么（边界）

- **不做历史存储**：它只给你"此刻"的值，不给你"昨天三点"。历史要靠 InfluxDB/Prometheus 这类时序库（Day 177 讲）。
- **不做告警分发**：没有邮件/企微/钉钉（Day 171 讲）。
- **不做采样调度**：不会自动每 5 秒采一次（Day 170 讲）。
- **不做容器隔离**：它如实报告**它自己看到的** `/proc`（这个坑见 3.7 与 7.6）。
- **不是安全边界**：普通用户读不到别的用户的进程详情时会 `AccessDenied`，这不是 bug。

---

### 2.3 三类指标：counter / gauge / state

这是全课**最重要的一次分类**。分不清这三类，后面必然算错。

| 类型 | 含义 | 单调性 | 例子 | 正确用法 |
|:---|:---|:---|:---|:---|
| **计数器 counter** | 开机以来**累计**的量 | 单调递增（除非溢出/重启） | `net_io_counters().bytes_sent`<br>`disk_io_counters().read_bytes`<br>`cpu_times().user` | **必须两次读数相减**，再除以时间间隔 |
| **瞬时值 gauge** | 此刻的**水平/存量** | 上下浮动 | `virtual_memory().used`<br>`disk_usage('/').used`<br>`cpu_percent()`（它其实是从 counter 算出来的 gauge） | 直接读，或看趋势 |
| **状态 state** | 离散枚举/字符串 | — | `Process.status()` → `'running'`/`'sleeping'`/`'zombie'`<br>`Process.username()` | 按枚举分支处理 |

#### 为什么必须分清楚？看一个真实错误

```python
# ❌ 错误：把"累计发送字节数"当成"发送速率"
for _ in range(10):
    print(psutil.net_io_counters().bytes_sent)   # 128734, 128740, 128753, ...
    time.sleep(1)

# 读者看到数字一直在涨 → 误判为"持续从零开始的大流量"
# 真相：这是开机以来的累计值，一万多字节是这次循环自己涨的
```

```python
# ✅ 正确：差分 + 除以时间
a = psutil.net_io_counters().bytes_sent
time.sleep(1.0)
b = psutil.net_io_counters().bytes_sent
rate = (b - a) / 1.0        # bytes/s
print(f"{rate / 1024:.1f} KiB/s")
```

> **一句话记忆**：**counter 要减，gauge 要读，state 要判。**

#### 差分为什么除以"时间间隔"而不是"sleep 的秒数"？

因为 `sleep(1.0)` 只能保证"**至少**睡 1 秒"，实际可能 1.003 秒（调度、GC、系统负载都会拖）。
在需要精度的场合，应该用 `time.monotonic()` 实测：

```python
t0, a = time.monotonic(), psutil.net_io_counters().bytes_sent
time.sleep(1.0)
t1, b = time.monotonic(), psutil.net_io_counters().bytes_sent
rate = (b - a) / (t1 - t0)     # 用实测间隔，误差显著更小
```

而且要用 `time.monotonic()`（单调时钟）而**不是** `time.time()`：
后者会被 NTP 校时、闰秒、手动改时间**往回拨**，一旦往回拨，
`t1 - t0` 可能变成负数或 0，你的速率就成了 `inf` / 负值。

---

### 2.4 采样的核心：为什么必须"两次"

这是初学者最大的困惑点：**"我就想知道现在 CPU 用了多少，为什么要等一秒？"**

答案：**因为操作系统里根本没有"当前 CPU 使用率"这个数字。**

内核维护的是一堆**累计刻度**（jiffies），比如 `/proc/stat` 的第一行：

```text
cpu  120456 3312 42910 9876543 12043 0 812 0 0 0
     │      │   │     │       │     │ │  │
     │      │   │     │       │     │ │  └─ steal（被虚拟化抢走的时间）
     │      │   │     │       │     │ └──── guest_nice
     │      │   │     │       │     └────── guest
     │      │   │     │       └──────────── irq / softirq（中断处理）
     │      │   │     └──────────────────── idle（空闲）
     │      │   └────────────────────────── system（内核态）
     │      └────────────────────────────── nice（低优先级用户态）
     └───────────────────────────────────── user（用户态）
     单位：USER_HZ（Linux 上通常是 1/100 秒 = 10ms 一个 tick）
```

**使用率是算出来的，不是读出来的：**

```text
        t0 时刻读数                      t1 时刻读数
   ┌──────────────┐              ┌──────────────┐
   │ user0  nice0 │              │ user1  nice1 │
   │ sys0   idle0 │  ───────►    │ sys1   idle1 │
   │ ...          │   Δt 秒      │ ...          │
   └──────────────┘              └──────────────┘
                  ↓  差分
   busy = (user1-user0) + (nice1-nice0) + (sys1-sys0) + ...
   total = busy + (idle1-idle0) + (iowait1-iowait0) + ...
   usage = busy / total × 100%      ← 这才是 "CPU 使用率"
```

由此推出三条必然结论：

1. **第一次调用没有参照物** → 只能返回 `0.0`（psutil 的选择，见 7.1）。
2. **间隔越短，噪声越大**。Δt=10ms 时，一个 tick 的调度误差就能让结果上下跳 10%。
3. **`usage` 天然是"过去 Δt 的平均值"**，不是"此刻的瞬时值"。
   系统里从来就没有后者 —— 任何声称给你瞬时 CPU 的工具都在撒谎。

#### 那么"瞬时值"是怎么被造出来的？

`top` 默认 3 秒刷新一次；`psutil.cpu_percent(interval=0.1)` 用 0.1 秒；
Prometheus 的 `node_exporter` 用 15 秒；云监控厂商常见 60 秒。

它们都在做同一件事：**选一个 Δt，让内核两次读书相减**。
Δt 的选择是一个**权衡**：

| Δt | 优点 | 缺点 | 适用 |
|:---|:---|:---|:---|
| 0.01–0.1s | 反应快 | 噪声大，且频繁读取本身有开销 | 交互式调试 |
| 0.5–1s | 够快也够稳 | — | 脚本告警（推荐） |
| 5–15s | 稳定 | 短时尖峰被平均掉 | 看板、长期趋势 |

> **记住**：你选的不只是刷新频率，而是**这台机器上"多久之内的异常算异常"的定义**。
> 选 15 秒，就意味着一次持续 8 秒的 CPU 打满**永远不会**被你发现。

---

### 2.5 进程是一等公民

psutil 对进程的建模很直白：`Process(pid)` 是一个**句柄（handle）**，
每次你调 `.cpu_percent()` / `.memory_info()`，它都是**现场去读一次** `/proc/<pid>/xxx`。

```text
   psutil.Process(pid=1234)
            │
            ├── .name()          → "python3"          ← 读 /proc/1234/comm
            ├── .cmdline()       → ["python3", "x.py"] ← 读 /proc/1234/cmdline
            ├── .exe()           → "/usr/bin/python3" ← 读 /proc/1234/exe（符号链接）
            ├── .cwd()           → "/root/code"       ← 读 /proc/1234/cwd
            ├── .status()        → "sleeping"         ← 读 /proc/1234/stat 第 3 字段
            ├── .memory_info()   → rss/vms/...        ← 读 /proc/1234/statm + status
            ├── .cpu_times()     → user/system/...    ← 读 /proc/1234/stat
            ├── .connections()   → 网络连接列表        ← 读 /proc/1234/net/ 与 socket inode
            └── .children()      → [Process, ...]     ← 遍历 /proc/*/stat 找 ppid
```

关键心态转变：**`Process` 是"活的"，不是"快照"**。
你拿到对象后，那个进程可能已经死了；你调用任何方法都可能抛 `NoSuchProcess`。
这不是设计缺陷，而是**如实反映现实** —— 现实里的进程确实会随时消失。

#### 为什么是"句柄"而不是"快照"？

因为监控的本意是"持续观察同一个对象"。如果 `Process(1234)` 是快照，
那每次采样都得重新 `Process(1234)`，无法回答"这个进程过去 5 分钟涨了多少内存"。

代价就是**非原子性**（下一个概念）和 **pid 复用**（3.4）这两个坑。

---

### 2.6 采集的"非原子性"：你看到的世界从来不是同一瞬间的

一个容易被忽略的事实：`psutil.process_iter()` 遍历进程时，
**系统在同时变化**。

```text
 你(采集者)                          系统(被观测者)
 ─────────                          ──────────────
 读到 pid=100 的 CPU  ────────────►  100 已退出
 读到 pid=200 的内存 ────────────►  200 被 AccessDenied（别的用户）
 遍历 /proc 列表 ────────────────► 3321 刚被创建（本轮的列表里没有它）
 ─────────                          ──────────────
 得到的结果 = 不同时刻、不同状态的拼接
```

这叫**采样非原子性（non-atomic sampling）**。它不是 bug，是**分布式观测的基本事实**。
后果有三类，必须显式处理：

| 现象 | 原因 | 处理 |
|:---|:---|:---|
| 抛 `NoSuchProcess` | 进程在两次调用之间退出 | `try/except` 跳过 |
| 抛 `AccessDenied` | 进程属于其他用户，普通用户读不到 | `try/except`，或降级为"只知道 pid 存在" |
| 抛 `ZombieProcess` | 进程已退出但父进程没 `wait()` | 单独识别并报告（本身是个问题信号） |
| 数值"对不上账" | 各项指标来自不同时刻 | 接受；或用 `Process.oneshot()` 缩小窗口 |

#### `oneshot()`：把多次读合并成一次

```python
p = psutil.Process(os.getpid())

# 普通写法：每次属性访问可能落一次系统调用/文件读
print(p.name(), p.status(), p.memory_info())

# oneshot 写法：进入上下文后，psutil 一次性把关键文件读完并缓存
with p.oneshot():
    print(p.name(), p.status(), p.memory_info())
```

`oneshot()` 内部把 `/proc/<pid>/stat`、`/proc/<pid>/status`、`/proc/<pid>/cmdline`
等文件**读一次缓存起来**，上下文退出后缓存失效。
它带来两个好处：**更快**、**同一时刻性更好**（减少跨时刻拼接）。

> 注意：`oneshot()` 里的值在上下文内**不会更新**。所以它适合"一次采集内读多个字段"，
> **不能**用来替代循环采样 —— 在 `with` 里循环读只会一直读到同一份旧数据。

---

### 2.7 内存指标要分清：rss / vms / uss / pss

`Process.memory_info()` 返回的字段，名字很像但含义差别巨大：

| 字段 | 全称 | 含义 | 大小关系 | 用途 |
|:---|:---|:---|:---|:---|
| `rss` | Resident Set Size | 实际占用的**物理内存**（含共享库） | 大 | 最常用，但**会重复计算共享页** |
| `vms` / `vsz` | Virtual Memory Size | 申请的**虚拟地址空间** | 最大 | 排查地址空间泄漏；**不等于真占内存** |
| `uss` | Unique Set Size | **本进程独占**的物理内存 | 最小 | Linux 独有；**最能代表"杀掉它能释放多少"** |
| `pss` | Proportional Set Size | 共享页**按比例摊分**后的物理内存 | rss ≥ pss ≥ uss | 容器/多进程场景最公平 |

```text
  物理内存                       进程 A 的视角          进程 B 的视角
  ┌────────────────────┐
  │ A 私有 100MB       │  ← 只属于 A            rss 计入 100MB
  ├────────────────────┤
  │ B 私有 200MB       │       (不属于 A)                    rss 计入 200MB
  ├────────────────────┤
  │ 共享库 libc 10MB   │  ← A/B 都在用          rss 计入 10MB   rss 计入 10MB
  └────────────────────┘
                    ↑
     计入 A.rss(10) + B.rss(10) = 20MB，但物理上只有 10MB
     → 这就是 "把所有进程 rss 加起来 > 总内存" 的原因
     → 用 pss 摊分：A.pss(5) + B.pss(5) = 10MB ✅
```

**实战结论**：

- 排行"谁最占内存" → 用 `rss`（直观）。
- 判断"干掉它能省多少" → 用 `uss`（准确）。
- 容器里做资源核算 → 用 `pss`（公平）。
- 看到 `vms` 几十 GB 就报警 → **错误**，虚拟内存不等于物理占用（Python 进程尤其夸张）。

---

### 2.8 跨平台与容器：同一行代码，两个世界

psutil 的 API 是跨平台的，但**语义不总是可移植**：

| 能力 | Linux | macOS | Windows | 说明 |
|:---|:---:|:---:|:---:|:---|
| `cpu_percent()` | ✅ | ✅ | ✅ | 可用 |
| `virtual_memory()` | ✅ | ✅ | ✅ | 可用 |
| `disk_partitions()` | ✅ | ✅ | ✅ | 挂载点命名差异大，**别硬编码 `/`** |
| `sensors_temperatures()` | ✅ | ❌ | ❌ | macOS/Windows 通常返回 `{}` |
| `sensors_fans()` | ✅ | ❌ | ❌ | 同上 |
| `Process.connections()` | ✅ | ✅ | ✅ | 需要相应权限 |
| `Process.ionice()` | ✅ | ❌ | ✅ | macOS 无 |
| `Process.rlimit()` | ✅ | ❌ | ❌ | Linux/FreeBSD |
| `net_io_counters(pernic=True)` | ✅ | ✅ | ✅ | 网卡名差异大（`eth0` vs `en0` vs `以太网`） |

#### 容器的真相：psutil 读的是"它看到的 /proc"

这是**运维实战里最容易踩的大坑**。在 Docker 容器里跑：

```python
psutil.virtual_memory().total     # → 62.8 GB   ← 宿主机内存，不是容器限额！
psutil.cpu_count()                # → 8         ← 宿主机核数！
psutil.cpu_percent()              # → 反映宿主机整体负载！
```

为什么会这样？因为**默认情况下容器与宿主机共享 `/proc` 的一部分视图**：

```text
   ┌─────────────────── 宿主机（64GB / 8 核）───────────────────┐
   │                                                            │
   │   /proc/meminfo   → MemTotal: 65814128 kB  （整机）         │
   │   /proc/cpuinfo   → 8 个 processor                         │
   │   /proc/stat      → 整机 CPU 累计刻度                       │
   │                                                            │
   │   ┌──────────── 容器 A（cgroup 限额 512MB / 1 核）────────┐ │
   │   │  读 /proc/meminfo  → 看到 65814128 kB  ❌（宿主的值） │ │
   │   │  读 /sys/fs/cgroup/memory.max → 536870912 ✅（自己的）│ │
   │   └───────────────────────────────────────────────────────┘ │
   └────────────────────────────────────────────────────────────┘
```

**正确读法**（Linux cgroup v2）：

```python
from pathlib import Path

def cgroup_memory_limit() -> int | None:
    """返回容器内存限额（字节）；无限制或不支持时返回 None。"""
    # cgroup v2
    p2 = Path("/sys/fs/cgroup/memory.max")
    if p2.exists():
        raw = p2.read_text().strip()
        if raw != "max":
            return int(raw)
    # cgroup v1
    p1 = Path("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if p1.exists():
        val = int(p1.read_text().strip())
        # v1 的"无限制"是一个极大值（接近 2^63），要挡掉
        if val < 1 << 62:
            return val
    return None
```

同理，容器的 CPU 限额在 `/sys/fs/cgroup/cpu.max`（v2，格式 `<quota> <period>`，如 `50000 100000` = 0.5 核）。

> **经验法则**：**在容器里做容量判断，永远先问"我的限额是多少"，而不是"机器有多少"。**
> 监控一个 512MB 的容器却按 64GB 的阈值告警，等于没有告警。

---
## 3. 原理深入

### 3.1 psutil 在 Linux 上到底读了什么

理解这张映射表，等于拿到了"为什么会出错"的排查地图：

| psutil API | Linux 数据源 | 读法 |
|:---|:---|:---|
| `cpu_times()` | `/proc/stat` 第 1 行（`cpu `） | 解析 10 个累计 jiffies |
| `cpu_times(percpu=True)` | `/proc/stat` 的 `cpu0`/`cpu1`... 行 | 同上，逐核 |
| `cpu_count(logical=True)` | `/proc/cpuinfo` 的 `processor` 条目数 或 `os.cpu_count()` | 计数 |
| `cpu_count(logical=False)` | `/proc/cpuinfo` 去重 `core id` + `physical id` | 需要解析拓扑 |
| `cpu_freq()` | `/proc/cpuinfo` 的 `cpu MHz` 或 `/sys/devices/system/cpu/*/cpufreq/` | 单值/列表 |
| `virtual_memory()` | `/proc/meminfo`（`MemTotal`/`MemAvailable`/`SwapTotal`...） | 逐字段解析 |
| `swap_memory()` | `/proc/meminfo`（`SwapTotal`/`SwapFree`） | 同上 |
| `disk_partitions()` | `/proc/filesystems` + `/proc/self/mounts`（或 `/etc/mtab`） | 过滤伪文件系统 |
| `disk_usage(path)` | `statvfs(2)` 系统调用 | 直接系统调用，**不读 /proc** |
| `disk_io_counters()` | `/proc/diskstats` | 累计扇区数 × 512 = 字节 |
| `net_io_counters()` | `/proc/net/dev` | 累计字节/包 |
| `net_connections()` | `/proc/net/tcp`、`/proc/net/udp` + socket inode 映射 | 需要权限 |
| `boot_time()` | `/proc/stat` 的 `btime` 行（或 `/proc/uptime` 反推） | 秒级时间戳 |
| `Process.name()` | `/proc/<pid>/comm` | 截断到 15 字符！ |
| `Process.cmdline()` | `/proc/<pid>/cmdline`（`\0` 分隔） | 可能为空（内核线程/已退出） |
| `Process.status()` | `/proc/<pid>/stat` 第 3 字段 | 单字符码（R/S/D/Z/T...） |
| `Process.memory_info()` | `/proc/<pid>/statm` + `/proc/<pid>/status` | 页数 × 页大小 |
| `Process.username()` | `/proc/<pid>/status` 的 `Uid:` → `/etc/passwd` 反查 | 需要权限 |
| `sensors_temperatures()` | `/sys/class/hwmon/*` | 需要驱动支持 |

> **`Process.name()` 与 15 字符截断**（实测过的细节）：
> 内核的 `/proc/<pid>/comm` 字段上限是 `TASK_COMM_LEN`=16 字节（含结尾 `\0`），
> 所以**内核层面**最多只保留 15 个可见字符。但 psutil 会在 `len(name) >= 15` 时
> **回退去读 `cmdline()`**：若 `cmdline[0]` 的 basename 以该截断名开头，就返回完整名字
> （源码见 `Process.name()` 的 POSIX 分支，动机是 `gnome-keyring-d` → `gnome-keyring-daemon`）。
> 所以「名字被截断」这个坑，真正会伤到你的场景是：**`cmdline()` 不可用的时候** ——
> 内核线程（`cmdline` 为空）、僵尸进程（抛 `ZombieProcess`）、无权限（抛 `AccessDenied`）。
> 完整验证见 `code/03-pitfalls.py --only 5`。

#### 为什么不直接读 `/proc/diskstats` 拿"磁盘使用率"？

因为 `/proc/diskstats` 给的是**累计扇区数**，得到使用率还需要第二个数据：
**"这段时间花在 IO 上多少秒"**。psutil 把它整理成了 `read_time` / `write_time`（毫秒），
于是：

```python
io = psutil.disk_io_counters()
busy_ms = io.read_time + io.write_time          # 累计 IO 忙时长
# 两次采样后：
utilization = (busy_ms1 - busy_ms0) / (t1 - t0) / 1000   # 0.0 ~ 1.0
```

注意 **`busy_ms` 也可能 >100%**（多队列块设备 nvme 会并发），
所以这个数叫"**设备忙碌度**"更准确，别直接当 `df` 那种"空间占用率"理解。
**空间 vs 忙碌是两件事** —— `disk_usage()` 看空间，`disk_io_counters()` 看吞吐/忙碌。

---

### 3.2 `cpu_percent()` 的内部实现（伪代码级）

psutil 的实现可以概括成下面这段（简化自 CPython 扩展）：

```python
# 概念性伪代码，用于理解行为，不要照抄
_LAST = {}   # 模块级：{key: (busy_time, total_time)}  ← 注意：是"上次的绝对值"

def cpu_percent(interval=None, percpu=False):
    key = 'percpu' if percpu else 'total'
    now = _read_cpu_times()                 # 读 /proc/stat
    busy_now  = now.user + now.nice + now.system + now.irq + now.softirq + ...
    total_now = busy_now + now.idle + now.iowait + ...

    last = _LAST.get(key)
    _LAST[key] = (busy_now, total_now)      # ★ 立刻更新"上次"缓存

    if interval is not None:                # ★ 阻塞语义
        time.sleep(interval)
        busy_then, total_then = _read_cpu_times_again()  # 重新读
        # 用 interval 前后的两次读数算
        ...

    if last is None:                        # ★ 首次调用
        return 0.0

    busy_delta  = busy_now - last[0]
    total_delta = total_now - last[1]
    if total_delta <= 0:
        return 0.0
    return busy_delta / total_delta * 100.0
```

由此可以**推导**出全部行为（后面 7.1/7.2 的坑都是这里的直接推论）：

1. **首次调用返回 `0.0`**：`_LAST` 里没有参照物 → 返回 0.0。
2. **`_LAST` 是模块级全局**：同一个进程里，**任何地方**调用 `cpu_percent()` 都会
   重置这个基准。所以两处代码交替调用会互相"偷时间"，导致结果偏小。
3. **`interval` 不是 None 时是阻塞的**：调用会 `sleep(interval)`，
   这在单线程脚本里意味着**你的整个循环被拖慢 interval 秒**。
4. **`interval=None` 是非阻塞的**：立刻返回"自上次调用以来"的平均值 ——
   这意味着**结果取决于你多久调一次**。

#### 三种正确写法

```python
# ✅ 写法 A：阻塞式，最简单，适合串行脚本（每次调用自带一秒窗口）
while True:
    print(f"CPU: {psutil.cpu_percent(interval=1.0):5.1f}%")   # 每次阻塞 1s

# ✅ 写法 B：非阻塞 + 自己控制节奏（推荐用于多指标组合采集）
psutil.cpu_percent(interval=None)        # 预热：建立基准，返回值丢弃
while True:
    time.sleep(1.0)
    cpu = psutil.cpu_percent(interval=None)    # 读"过去 1 秒"的平均
    mem = psutil.virtual_memory().percent
    print(f"CPU {cpu:5.1f}%  MEM {mem:5.1f}%")

# ✅ 写法 C：逐核（percpu=True）
per = psutil.cpu_percent(interval=1.0, percpu=True)
print(" ".join(f"core{i}:{v:4.1f}%" for i, v in enumerate(per)))
```

> **写法 B 的"预热"是必须的吗？** 不是必须，但**不预热的第一轮会打印 0.0**，
> 观感很差且容易误判。把"预热 + 丢弃返回值"写进初始化阶段，是工程上的好习惯。
> 反复强调同一个原则：**观测工具本身需要被正确初始化。**

---

### 3.3 进程时间：`cpu_times()` 与它的"两个时钟"

`Process.cpu_times()` 返回的是一组**累计 CPU 时间**（单位秒，浮点）：

| 字段 | 含义 |
|:---|:---|
| `user` | 进程在**用户态**消耗的 CPU 时间 |
| `system` | 进程在**内核态**消耗的 CPU 时间 |
| `children_user` | **已回收的子进程**在用户态的时间（Linux/macOS） |
| `children_system` | 已回收子进程的内核态时间 |
| `iowait` | 等待 IO 的时间（Linux，**部分内核不填**） |

要点：

1. **这是该进程"消费掉多少 CPU 秒"**，不是"墙上时间（wall clock）"。
   一个进程跑 10 秒，可能只消费 0.2 秒 CPU（大部分时间在等 IO）。
2. `user + system` 是**跨多核可以超过墙上时间**的 —— 8 线程跑 1 秒最多能消费 8 秒 CPU。
   所以 `Process.cpu_percent()` 可能返回 **800%**，这**不是 bug**。
3. `children_*` 只统计**已经被父进程 `wait()` 回收**的子进程。没回收的不算。

```python
p = psutil.Process(os.getpid())
ct = p.cpu_times()
print(f"user={ct.user:.2f}s system={ct.system:.2f}s")
```

#### `Process.cpu_percent()` 与进程存活时长

还有一个反直觉点：**新创建就立刻查 `Process.cpu_percent()`，可能返回 0.0 或者很怪的值**。
因为 psutil 用进程的 `create_time()` 作为"总时间"的分母基准，
进程刚出生时分母极小，百分比会剧烈跳动。

> **实操建议**：对刚启动的进程，**至少等一个采样周期**再读 `cpu_percent()`。

---

### 3.4 pid 复用：`Process` 对象缓存与"僵尸对象"

Linux 的 pid 是**循环复用**的（`/proc/sys/kernel/pid_max`，默认 32768 或 4194304）。
一个进程退出后，它的 pid 很快会被新进程占用。

```text
 t0:  Process(pid=1234) 指向 "python3 backup.py"       ← 你抓住了它
 t1:  "python3 backup.py" 退出
 t2:  pid 1234 被 "nginx: worker" 占用（pid 复用！）
 t3:  你再次访问 p.name()  →  返回 "nginx"   ❗❓
```

psutil 对此有**部分**防御：`Process` 对象会缓存 `create_time`（进程启动时刻），
调用 `_is_running()` 时会比对，**通常**能识别出 pid 已被复用并抛 `NoSuchProcess`。
但：

- 这个保护**依赖 create_time 可读**（权限不足时读到的是 0.0，保护失效）。
- `process_iter()` 默认对**本轮内**的进程做缓存（`Process` 实例复用），
  在 pid 密集复用的机器上（如高频 fork 的构建机）仍可能出错。

**防御性写法**：只要跨采样周期持有 `Process` 对象，就**每次都校验身份**：

```python
def identity(p: psutil.Process) -> tuple:
    """进程身份指纹：pid + 启动时刻。两者都相同才算同一个进程。"""
    try:
        return (p.pid, p.create_time())
    except psutil.Error:
        return (p.pid, 0.0)

# 采集时记住指纹，判断时比对
before = identity(p)
time.sleep(60)
after = identity(p)
if before != after:
    print("进程已经不是原来那个了（或已退出），丢弃旧数据")
```

> **一句话**：**在监控里，"pid 相同"绝不等于"同一个进程"。**

---

### 3.5 IO 计数器：差分、溢出与重置

`net_io_counters()` / `disk_io_counters()` 返回的都是累计值，
所以差分时会遇到三种"负数/怪数"的来源：

| 现象 | 原因 | 处理 |
|:---|:---|:---|
| 差分为**负数** | 计数器被重置（网卡重启、容器重启、模块卸载重载） | 检测 `delta < 0` → 视为无效样本，跳过 |
| 差分为**极大值** | 采样间隔异常大（进程被挂起、系统休眠） | 校验实测 Δt，超阈值丢弃该样本 |
| 计数器**不增长** | 该网卡无流量 / 采到了不存在的接口 | 属正常；注意网卡名变化 |

```python
def safe_rate(prev, cur, dt, *, reset_on_negative=True):
    """安全求速率：处理计数器重置与异常间隔。"""
    if dt <= 0:
        return None
    delta = cur - prev
    if delta < 0:
        if not reset_on_negative:
            return None
        delta = cur          # 视为计数器重置：本次增量 = 当前绝对值
    return delta / dt
```

#### Python 的整数不会溢出，但内核的可能回绕

Python 的 `int` 是任意精度，所以 `delta < 0` 不会因为 Python 而溢出。
但**内核的计数器是定长的**（如 32 位）。在极老的 32 位系统上，
`/proc/net/dev` 的字节计数在超过 4GB 后会回绕 —— 表现为差分突然变成负数。
`psutil` 在现代 64 位系统上不存在这个问题，但**写防御性代码永远是对的**。

---

### 3.6 异常层次：该捕哪个，不该捕哪个

```text
psutil.Error                      ← 所有 psutil 异常的共同基类
├── NoSuchProcess                 ← 进程不存在（已退出 / pid 无效）
├── AccessDenied                  ← 权限不足（别的用户 / 需要 root）
├── TimeoutExpired                ← 等待超时（如 wait() 带 timeout）
├── ZombieProcess                 ← 进程存在但已是僵尸，信息读不全
└── (POSIX 场景下的其他子类)

psutil.AccessDenied 继承自 psutil.Error（不是 PermissionError）
psutil.NoSuchProcess 不继承自 FileNotFoundError
```

**正确姿势**：

```python
try:
    rss = psutil.Process(pid).memory_info().rss
except psutil.NoSuchProcess:
    rss = None            # 进程没了：这是"预期内的正常情况"，不该崩
except psutil.AccessDenied:
    rss = None            # 权限不够：也是正常情况，记录为"不可测"
except psutil.ZombieProcess:
    rss = None
```

**错误姿势（很常见）**：

```python
try:
    ...
except Exception:        # ❌ 吞掉一切：连自己代码里的 TypeError 都被吃了
    pass
```

> **原则**：监控代码必须**区分"目标不可测"和"我写错了"**。
> 前者静默降级 + 计数上报；后者必须炸出来，否则你会监控一个永远返回空值的假象。

---

### 3.7 采样开销与"观测者效应"

监控不是免费的。三个成本来源：

1. **读取成本**：每次 `Process.memory_info()` 都至少读 1~2 个 `/proc` 文件。
   遍历 2000 个进程 × 读 5 个字段 = 上万次文件读。
2. **对象成本**：`process_iter()` 为每个进程构造 `Process` 对象。
3. **sleep 误差**：`time.sleep(1)` 实际可能 1.001~1.05 秒，长跑会漂移。

实测参考（本机 Ubuntu / 4 核 / **322 个进程**，可复现脚本 `code/04-benchmark.py`，
每项取多轮**最小值**）：

| 采集方式 | 最小耗时 | 相对「只要 pid」 | 说明 |
|:---|:---:|:---:|:---|
| `psutil.pids()` | 180 µs | 1.00× | 只列 `/proc` 目录项 |
| `process_iter()`（不取属性） | 458 µs | 2.54× | 构造迭代器 |
| `process_iter(['name'])` | 17.2 ms | **95.6×** | 每进程读一次 `comm` |
| `process_iter([...5 字段含 memory_info])` | 33.3 ms | **184.6×** | 每进程多读几个文件 |
| 逐进程 `Process(pid).name()` | 22.0 ms | 122.0× | 无迭代器复用，比 `process_iter(['name'])` 还慢 1.28× |

系统级单项指标则便宜得多（同一台机器、同一轮次）：

| 调用 | 最小耗时 |
|:---|:---:|
| `cpu_percent(interval=None)` | 35 µs |
| 手写解析 `/proc/stat`（同样算一次） | 34 µs —— 说明 psutil 几乎没额外开销 |
| `virtual_memory()` | 48 µs |
| `disk_usage('/')` | 5.6 µs（`statvfs` 系统调用） |
| `net_io_counters()` | 80 µs |
| `disk_partitions()` | 209 µs |
| `with p.oneshot()` 读 3 字段 × 200 轮 | 9.8 ms （无 oneshot 12.7 ms → **快 1.3×**） |

```text
  ┌────────────────────────── 采样周期与采集耗时的硬约束 ───────────────────────────┐
  │                                                                              │
  │    采样周期 Δt  必须  ≫  单轮采集耗时 T                                        │
  │                                                                              │
  │    Δt=1s, T=33ms   → T/Δt ≈ 3.3%   可接受                                     │
  │    Δt=1s, T=300ms  → T/Δt ≈ 30%    监控自己就成了主要负载 ❌                    │
  │    Δt=5s, T=300ms  → T/Δt ≈ 6%     勉强                                      │
  │                                                                              │
  │    → 这就是 3.7 节「观测者效应」的量化版本                                    │
  └──────────────────────────────────────────────────────────────────────────────┘
```

> ⚠ **诚实记录**：本节最初的「约 1.5 倍 / 2.5 倍」是拍脑袋写的，被自己的基准测试
> 当场打脸 —— 实测相差**两个数量级**。这就是「先测再写」的意义：
> `04-benchmark.py` 里所有倍数都是**运行时从实测数据算出来的**，不写死。
> 你换一台机器跑出来的倍数会不同，但「**进程枚举才是大头，系统级指标可以忽略**」
> 这个结论是稳的。

> **结论**：**用 `process_iter(attrs=[...])` 并只取需要的字段**。
> 在 2000 进程的机器上，全量扫描可能轻松破百毫秒 —— 这个数字**直接决定采样周期的下限**，
> 也决定了你能否在 1 秒周期内做一轮完整采集。

#### 观测者效应

你的监控进程本身也在消耗 CPU 和内存。当阈值设得很低时，
**你会看到自己的脚本排在 CPU 排行前列**。所以：

- 排行里**先排除自己**（`pid == os.getpid()`）；
- 阈值告警时**排除监控自身**的贡献；
- 采样周期越短，这个偏差越大（Day 177 讲 Prometheus 时会再遇到这个问题）。

---

### 3.8 时间基准：`create_time()`、`boot_time()` 与时钟跳变

- `boot_time()`：系统启动时刻（Unix 时间戳）。
- `Process.create_time()`：进程创建时刻（Unix 时间戳）。
- **两者都基于可被调整的系统时钟**（`CLOCK_REALTIME`）。

如果运维改了系统时间（或 NTP 大步校正），计算"进程跑了多久"会出现**负数或跳变**：

```python
uptime = time.time() - p.create_time()     # 时钟被回拨时 → 负数
```

**更稳的写法**：只用**同一个时钟基准**做减法的同时，显式检测负值。

```python
import time


def process_age_seconds(create_time: float) -> float | None:
    """进程已存活秒数。

    create_time 来自 Process.create_time()，与 time.time() 同为
    CLOCK_REALTIME 基准，可以直接相减。
    若系统时钟被回拨，差值会变成负数 —— 此时返回 None（不可信）。
    """
    age = time.time() - create_time
    return age if age >= 0 else None
```

> **不要做的两件事**：
> 1. **不要把 `time.monotonic()` 和 `create_time()` 相减**。
>    `monotonic()` 的基准是"某个未指定的过去时刻"（Linux 上通常是开机），
>    而 `create_time()` 是 Unix 时间戳 —— 两者基准不同，相减**没有任何意义**。
> 2. **不要为了绕过负值而 `abs()`**。时钟被回拨时 `abs()` 会把一个巨大的
>    错误值伪装成"正常时长"，比返回负数更危险。宁可返回 `None` 并如实上报。
>
> **工程结论**：算存活时长用 `time.time() - create_time()` 并**显式检测负值**；
> 测**采样间隔**用 `time.monotonic()`（它不会被 NTP 校时影响，这正是 2.3 节
> 求速率时必须用它、而不是 `time.time()` 的原因）。

---
## 4. API 速查表

### 4.1 CPU

| API | 返回 | 要点 |
|:---|:---|:---|
| `psutil.cpu_times()` | `scputimes` | **累计**刻度；差分用 |
| `psutil.cpu_times(percpu=True)` | `list[scputimes]` | 逐核 |
| `psutil.cpu_percent(interval=None)` | `float` | **非阻塞**；首次返回 0.0 |
| `psutil.cpu_percent(interval=1.0)` | `float` | **阻塞** 1s 后返回 |
| `psutil.cpu_percent(percpu=True)` | `list[float]` | 逐核百分比 |
| `psutil.cpu_count()` | `int\|None` | 逻辑核数 |
| `psutil.cpu_count(logical=False)` | `int\|None` | 物理核数（可能返回 None） |
| `psutil.cpu_stats()` | `scpustats` | 上下文切换/中断/软中断累计数 |
| `psutil.cpu_freq()` | `scpufreq\|None` | `current/min/max`（MHz） |
| `psutil.getloadavg()` | `(1m,5m,15m)` | Unix 才有；Windows 上返回最近算出的值 |

> `getloadavg()` 返回的是**运行队列长度**（不是百分比）。
> 经验阈值：**load > 逻辑核数 × 1.0 即已饱和**；> 核数 × 2 属严重排队。

### 4.2 内存

| API | 关键字段 | 要点 |
|:---|:---|:---|
| `psutil.virtual_memory()` | `total/available/used/free/percent` | **优先看 `available`**，见下 |
| `psutil.swap_memory()` | `total/used/free/percent/sin/sout` | `sin/sout` 是**累计**换入换出页数 |
| `Process.memory_info()` | `rss/vms/...` | 见 2.7 的四字段对比 |
| `Process.memory_info().uss` | `int\|None` | Linux 独有 |
| `Process.memory_info().pss` | `int\|None` | Linux 独有 |
| `Process.memory_full_info()` | 含 `uss/pss/swap` | 略慢，容器场景值得 |
| `Process.memory_percent()` | `float` | 相对**总内存**的百分比 |

**`used` vs `available`，一定要用 `available`：**

```text
  MemTotal ─────────────────────────────────────────────────────────┐
  │ MemFree │ buffers/cache │ 可回收(slab等) │ 真正不可用            │
  └─────────────────────────────────────────────────────────────────┘
        ↑            ↑                  ↑
      used 只扣掉    Linux 会把          available = MemFree + 可回收
      MemFree       几乎所有空闲内存     ← 这才是"还能申请多少"
                    拿去做 page cache
      → thin-provisioning 让 used 常年 90%+，其实毫无压力
```

> **为什么"`used` 高"经常是假警报？** 因为 Linux 的设计哲学是"空闲内存就是浪费的内存"，
> 它会主动把没用到的 RAM 缓存文件页（page cache）。这些页在应用需要时**立刻可回收**。
> 所以监控内存**看 `available`**，或者看 `percent`（psutil 的 `percent` 用的是
> `total - available` 口径，这一点和 `free` 命令的"available"列一致）。

### 4.3 磁盘

| API | 关键字段 | 要点 |
|:---|:---|:---|
| `psutil.disk_partitions()` | `device/mountpoint/fstype/opts` | 会包含 `tmpfs`/`overlay` 等伪设备 |
| `psutil.disk_partitions(all=False)` | 同上 | 默认已过滤大部分伪文件系统 |
| `psutil.disk_usage(path)` | `total/used/free/percent` | **按挂载点**查，`path` 必须是真实存在的路径 |
| `psutil.disk_io_counters()` | `read_bytes/write_bytes/read_time/write_time` | **累计**，差分求速率 |
| `psutil.disk_io_counters(perdisk=True)` | `dict[str, sdiskio]` | 逐设备 |
| `shutil.disk_usage(path)` | `usage` 命名元组 | 标准库替代（无 percent） |

**`disk_usage` 的正确姿势：**

```python
# ❌ 硬编码 '/'：Windows 上直接炸，容器里可能不是你要的分区
psutil.disk_usage('/')

# ✅ 遍历真实挂载点
for part in psutil.disk_partitions(all=False):
    try:
        u = psutil.disk_usage(part.mountpoint)
    except (PermissionError, FileNotFoundError, OSError):
        continue          # 已卸载/无法访问的挂载点很常见，必须容错
    print(f"{part.mountpoint:20s} {u.percent:5.1f}%  {u.free/2**30:6.1f} GiB free")
```

### 4.4 网络

| API | 关键字段 | 要点 |
|:---|:---|:---|
| `psutil.net_io_counters()` | `bytes_sent/recv`, `packets_sent/recv`, `errin/errout`, `dropin/dropout` | **累计**，差分求速率 |
| `psutil.net_io_counters(pernic=True)` | `dict[str, snetio]` | 逐网卡 |
| `psutil.net_connections(kind='inet')` | `list[sconn]` | kind: `inet`/`tcp`/`udp`/`unix`/`all` |
| `psutil.net_if_addrs()` | `dict[nic, list[snicaddr]]` | IP/MAC/掩码 |
| `psutil.net_if_stats()` | `dict[nic, snicstats]` | `isup/speed/mtu/duplex` |
| `Process.connections(kind='inet')` | 同上 | 需要权限；`AccessDenied` 常见 |

> `errin/errout/dropin/dropout` 是**质量指标**：网卡在丢包/出错时才会增长。
> 它们天生是"坏消息计数器"，**任何增长都值得记录**（哪怕绝对量很小）。

### 4.5 进程

| API | 说明 |
|:---|:---|
| `psutil.pids()` | 当前所有 pid 列表（快照） |
| `psutil.process_iter(attrs=[...])` | 迭代器；`proc.info` 只含请求的字段（**性能关键**） |
| `psutil.Process(pid)` | 构造句柄；pid 不存在时**不报错**（首次调用方法时才报） |
| `p.pid` / `p.ppid()` | 自身/父进程 pid |
| `p.name()` / `p.exe()` / `p.cmdline()` / `p.cwd()` | 身份信息（name 截断 15 字符） |
| `p.status()` | `running/sleeping/disk-sleep/zombie/stopped/...` |
| `p.create_time()` | 启动时刻（Unix 时间戳） |
| `p.cpu_times()` / `p.cpu_percent()` | 累计 CPU 时间 / 百分比（可 >100%） |
| `p.memory_info()` / `p.memory_percent()` | 内存 |
| `p.num_threads()` / `p.threads()` | 线程数 / 线程列表 |
| `p.open_files()` | 打开的文件（需权限） |
| `p.children(recursive=False)` | 子进程 |
| `p.parent()` | 父进程（`Process` 或 `None`） |
| `p.nice()` / `p.ionice()` | 优先级 |
| `p.username()` | 属主（需权限） |
| `p.terminate()` / `p.kill()` | SIGTERM / SIGKILL（**危险，本课只用在自己启动的子进程上**） |
| `p.wait(timeout=...)` | 等待退出（配合 `terminate` 做优雅停止） |
| `p.as_dict(attrs=[...], ad_value=None)` | 一次性取多字段，异常字段填 `ad_value` |
| `p.oneshot()` | 上下文管理器，缓存多次读取 |
| `p.is_running()` | 是否存活 |

### 4.6 其他

| API | 说明 |
|:---|:---|
| `psutil.boot_time()` | 开机时间戳 |
| `psutil.users()` | 登录用户列表 |
| `psutil.sensors_temperatures()` | 温度（Linux） |
| `psutil.sensors_battery()` | 电池（笔记本） |
| `psutil.sensors_fans()` | 风扇转速（Linux） |
| `psutil.PROCFS_PATH` | 可改写 `/proc` 路径（主要用于测试/特殊挂载） |

---

## 5. 常见陷阱 Top 10

### 陷阱 1：`cpu_percent()` 首次返回 0.0

```python
print(psutil.cpu_percent())     # 0.0  ← 骗人！
```

**根因**：没有上一次的参照读数（见 3.2）。
**修法**：预热一次并丢弃，或用 `interval=`。

```python
psutil.cpu_percent(interval=None)     # 预热
time.sleep(1)
print(psutil.cpu_percent())           # 真实值
```

### 陷阱 2：以为 `interval=None` 是"瞬时值"

```python
for _ in range(1000):
    v = psutil.cpu_percent()      # 非阻塞，但窗口 = 两次调用的间隔
    # 这里窗口可能只有微秒 → 结果在 0 和 100 之间乱跳，或一直是 0.0
```

**修法**：非阻塞模式下，**自己保证调用间隔 ≥ 采样窗口**。

### 陷阱 3：把累计值当瞬时值（最致命的坑）

```python
print(psutil.net_io_counters().bytes_sent)   # ❌ 开机以来累计
```

**修法**：差分 ÷ 实测 Δt（见 2.3）。

### 陷阱 4：`disk_usage('/')` 在容器里毫无意义 / Windows 直接崩

**修法**：遍历 `disk_partitions()`，并且对每个挂载点 `try/except`。

### 陷阱 5：`Process.name()` 的 15 字符截断，以及 psutil 的回退

```text
  可执行文件 basename: very-long-application-name-exceeds-comm-limit (45 字符)
  内核 /proc/<pid>/comm: 'very-long-appli'                            ← 内核截断到 15
  psutil Process.name(): 'very-long-application-name-...' (45 字符)    ← psutil 回退了
  cmdline()[0] basename: 完整名字
```

**根因**：内核 `/proc/<pid>/comm` 的 `TASK_COMM_LEN`=16 字节（含 `\0`），只能放 15 个字符。
**psutil 的补偿**：发现 `len(name) >= 15` 时去读 `cmdline()`，若 basename 以截断名开头就返回完整版。

**所以真正的坑不在截断本身**，而在 `cmdline()` 不可用的三种情况：

| 场景 | `name()` | `cmdline()` | 后果 |
|:---|:---|:---|:---|
| 内核线程 | 截断值/空 | 空列表 | 拿不到完整身份 |
| 僵尸进程 | 可能可读 | 抛 `ZombieProcess` | 回退失败，只剩截断值 |
| 其他用户进程 | 截断值 | 抛 `AccessDenied` | 回退失败，只剩截断值 |

**修法**：优先 `cmdline()[0]` 的 basename，失败回退 `name()`，再失败输出占位符**并计数**
（`身份不全` 计数是采样完整性的重要指标，见 2.6）。

```python
def full_name(p) -> str:
    try:
        cmd = p.cmdline()
        if cmd:
            return os.path.basename(cmd[0]) or p.name()
    except psutil.Error:
        pass
    try:
        return p.name()
    except psutil.Error:
        return f"<pid {p.pid}>"
```

### 陷阱 6：容器里读到宿主机的内存/核数

见 2.8。**修法**：读 cgroup 限额。

### 陷阱 7：不处理 `NoSuchProcess` / `AccessDenied`

遍历进程时不 catch，脚本会在"某个进程刚好退出"时**随机崩溃**。
这类 bug 最难复现 —— **它取决于时序**。

### 陷阱 8：用 `time.time()` 算采样间隔

NTP 校时会让 Δt 变成负数或 0 → 速率变 `inf`。**修法**：`time.monotonic()`。

### 陷阱 9：`Process.cpu_percent()` 超过 100% 就报警

多线程/多进程程序的 `cpu_percent()` **上限是 100% × 核数**。
`800%` 在 8 核机器上表示"打满了全部 8 核"，**不是异常数据**。
**修法**：阈值按"核数 × 目标利用率"来定，或改用 `cpu_percent()` 的系统级指标。

### 陷阱 10：阈值抖动导致告警风暴

CPU 在 79% 和 81% 之间反复横跳，阈值 80% 会让你收到几百条告警。
**修法**：**去抖（debounce）** —— 连续 N 次超阈值才告警，连续 M 次恢复才解除。

```python
class Threshold:
    """带滞回（hysteresis）与连续次数去抖的阈值判定。

    - high: 超过则计一次"异常"
    - low:  低于则计一次"正常"（必须 < high，形成滞回带）
    - need: 连续多少次才真正翻转状态
    """

    def __init__(self, high: float, low: float, need: int = 3):
        if low >= high:
            raise ValueError("low 必须小于 high，否则滞回带为空")
        self.high, self.low, self.need = high, low, need
        self.state = False       # False=正常 True=告警
        self._streak = 0

    def feed(self, value: float) -> bool:
        """送入一个样本，返回当前（可能已翻转的）告警状态。"""
        if self.state:
            # 已告警：需要连续 need 次低于 low 才恢复
            if value < self.low:
                self._streak += 1
                if self._streak >= self.need:
                    self.state, self._streak = False, 0
            else:
                self._streak = 0
        else:
            if value >= self.high:
                self._streak += 1
                if self._streak >= self.need:
                    self.state, self._streak = True, 0
            else:
                self._streak = 0
        return self.state
```

---
## 6. 实战代码案例

本课的可运行代码全部在 `code/` 下，每个文件都能独立跑、都自带 `--self-test`。

### 6.1 文件清单与用途

| 文件 | 类型 | 讲什么 | 自检命令 |
|:---|:---|:---|:---|
| `code/01-system-info.py` | 基础用法 | CPU / 内存 / 磁盘 / 网络 / 系统 / 传感器 六类指标的正确读法 | `--self-test` |
| `code/02-process-monitor.py` | 进阶用法 | 进程扫描账本、Top-N 排行、进程树、pid 复用防御、优雅停止 | `--self-test` |
| `code/03-pitfalls.py` | 避坑 | **十条陷阱逐条实测**：从"首调 0.0"到"cgroup 限额" | `--self-test` / `--only N` |
| `code/04-benchmark.py` | 性能 | 五种进程枚举写法 + oneshot + 系统级指标的**实测耗时** | `--self-test` / `--rounds N` |
| `code/monitor_core.py` | 实战（库） | `Collector` / `Threshold` / `safe_rate` / 渲染器 | 被 05 调用 |
| `code/05-monitor-tool.py` | 实战（CLI） | 完整监控工具：采样 + 去抖告警 + JSON/Markdown 报告 + 退出码契约 | `--self-test` |

> 要求：`code/` 下每个脚本都必须能 `python3 <file> --self-test` 输出 `SELF-TEST OK`。
> 这不是形式主义 —— **自检是别人（和未来的你）判断"这段代码还活着"的最快方式**。

### 6.2 实战：一个完整的监控工具长什么样

`05-monitor-tool.py` 是本课的交付物。它的结构就是第 2.1 节那张图的具体化：

```text
  ① 采集               ② 时间维度            ③ 判定              ④ 表达/交付
  Collector.collect()  run_sampling() 的    Threshold.feed()    render_json()
    · cpu/mem/disk       采样循环              · 滞回带             render_markdown()
    · net/disk 差分      · monotonic 计时      · 连续次数去抖        · 原子写入
    · 进程 Top-N         · 绝对下一次时刻       · 僵尸单独判定        · 退出码 0/2/1
    · cgroup 限额        （防误差累积）
```

关键实现片段（都对应一条前面讲过的原理）：

```python
# ① 预热：不预热第一轮 CPU 全是 0.0（陷阱 1）
collector.warmup()

# ② 采样调度用"绝对下一次时刻"，避免 sleep 误差累积漂移
start = time.monotonic()
next_tick = start
while True:
    now = time.monotonic()
    if now - start >= duration:
        break
    if next_tick > now:
        time.sleep(next_tick - now)
    next_tick += interval          # ★ 累加的是"计划时刻"，不是"实际耗时"
    sample = collector.collect()
```

> **为什么是 `next_tick += interval` 而不是 `sleep(interval)`？**
> 后者会把每次的采集耗时也累加进去：采集本身要 30ms，采 60 次就多漂 1.8 秒。
> 前者把"什么时候该醒"和"采集花了多久"解耦，长跑不漂。这是所有定时采样的标准做法。

### 6.3 三条"必须写对"的细节

**(1) 计数器差分必须用实测间隔**

```python
def safe_rate(prev: float, cur: float, dt: float) -> float | None:
    if dt <= 0:
        return None
    delta = cur - prev
    if delta < 0:
        return None      # 计数器被重置（网卡/容器重启）→ 丢弃，绝不进速率计算
    return delta / dt
```

返回 `None` 而不是 `0.0`，是刻意的：`0.0` 会被误读成"没有流量"，
而 `None` 会迫使调用方显式处理"这个样本不可信"。

**(2) 告警必须去抖，且"进入告警"与"恢复"阈值不同**

```python
th = Threshold(name="CPU", high=85, low=80, need=2)
# high=85 才进入告警，low=80 以下才恢复 → 81%~84% 的抖动无法翻转状态
```

**(3) 报告要原子落盘**

```python
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as fh:
    fh.write(content)
os.replace(tmp, path)      # 原子替换：读者要么看到旧文件，要么看到完整的新文件
```

监控报告经常被**另一个正在运行的脚本**读取。非原子写入会让它读到半截 JSON
而解析失败 —— 这种"随机崩溃"最后一定会被归因成"监控系统不稳定"。

### 6.4 退出码契约（再次强调，因为它真的重要）

```text
  0  ── 采集成功，所有指标在阈值内
  2  ── 采集成功，但触发了告警
  1  ── 采集失败 / 参数错误

  为什么这样分？
    cron/CI/K8s 需要区分"脚本自己坏了"(1) 和"被监控对象有问题"(2)。
    混用会导致：真正的故障被当成脚本 bug 排查，或者脚本 bug 被当成系统告警
    反复骚扰运维 —— 两种都会消耗信任。
```

### 6.5 实测输出样例

```text
$ python3 05-monitor-tool.py --duration 3 --interval 0.8 --out-dir /tmp/reports
  · CPU: 告警阈值 ≥85%，恢复阈值 <80%，连续 2 次才翻转
  · 采样：每 0.8s 一次，共 3.0s，进程排行 Top 5

  [06:05:48] CPU   0.0%  MEM  28.2%  DISK  34.5% (/)  NET ↑  0.0 B/s ↓  0.0 B/s  PROC  317  告警[...]
  [06:05:49] CPU   1.6%  MEM  28.2%  DISK  34.5% (/)  NET ↑ 52.6 B/s ↓379.1 B/s  PROC  317  告警[...]

  采样完成：5 个样本，0 条告警
  CPU  平均  1.40%  峰值  1.90%
  报告已写入：
    /tmp/reports/monitor-20260925-060551.json
    /tmp/reports/monitor-20260925-060551.md
  退出码 0（采集成功，无告警）
```

（上面是**真机实测**输出。`CPU 0.0%` 出现在第一行是一种巧合而非 bug：
它是"从预热到第一次 collect"的窗口内平均；窗口极短时确实可能读到 0.0。
这恰好是陷阱 1 与陷阱 2 的现场演示。）

---

## 7. 思考题

1. **"CPU 使用率 80%" 这句话缺了哪个必要参数？** 没有它，这个数字为什么没有意义？
   （提示：采样窗口，以及"平均值"这个词本身。）

2. **一进程 `cpu_percent()` 返回 `450%`，要报警吗？** 判断依据是什么？
   如果机器 4 核、进程是你自己的多线程爬虫，结论变吗？
   再想一想：**如果这个进程属于别人**，你的判断会怎么变？

3. **为什么"所有进程 RSS 之和"经常超过物理内存？**
   要回答"现在实际占用多少物理内存"，应该用什么口径（rss/pss/uss）？
   为什么这个问题在容器里比在物理机上更严重？

4. **连续 3 次采到 CPU 0.0%，你能确定机器空闲吗？**
   列出至少两种造成"假的 0.0%"的原因。

5. **阈值定 80% 还是 95%？** 这个问题为什么不能只从技术层面回答？
   "告警疲劳"和"漏报"哪个更危险？为什么"两个都避免"是不可能的
   （提示：这是统计学的两类错误，不可能同时最小化）？

6. **如果 `psutil` 在某平台上不提供 `sensors_temperatures()`，你的监控脚本应该怎么办？**
   是报错退出、还是静默跳过？给出你的选择并说明理由
   （提示：想一想 2.6 节的"采样完整性计数"）。

7. **观测者效应**：如果监控脚本自己排在 CPU 排行第一，这说明了什么？
   在实际项目里，你会怎么处理这个偏差，又如何在报告里保持诚实？

---

## 8. 参考与延伸

- psutil 官方文档 —— <https://psutil.readthedocs.io/>
- Linux `/proc` 手册 —— `man 5 proc`（`/proc/stat`、`/proc/meminfo`、`/proc/<pid>/stat` 字段定义）
- cgroup v2 文档 —— <https://docs.kernel.org/admin-guide/cgroup-v2.html>
- *Site Reliability Engineering*（Google）第 6 章 "Monitoring Distributed Systems"
  —— 关于"监控什么才是有用的信号"的经典论述
- Brendan Gregg, *Systems Performance* —— 关于 counter/gauge 与观测开销的系统方法

---

## 9. 明日预告

**Day 167 — 文件监控（watchdog）**

今天做的是**轮询（polling）**：我每隔一段时间主动去问"现在怎么样了"。
明天做**事件（event）**：让内核在文件发生变化时**主动通知**我。

两者的取舍是本课的延伸：

| | 轮询（今天） | 事件（明天） |
|:---|:---|:---|
| 机制 | 定时主动采样 | 内核回调通知 |
| 延迟 | 最差 = 采样周期 | 接近实时 |
| 开销 | 与"被监控对象数量"成正比 | 与"变化次数"成正比 |
| 漏报风险 | 两次采样之间的短时事件会被整体平均掉 | 几乎不漏 |
| 复杂度 | 低 | 高（队列溢出、事件合并、重命名竞态） |

预告实例：`watchdog` 的 `FileSystemEventHandler` 与 `inotify` 的队列溢出问题 ——
"你以为你在监控目录，其实你在监控一个会丢事件的队列"。
