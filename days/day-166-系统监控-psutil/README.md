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

> **`Process.name()` 会被截断到 15 字符**，这是内核 `/proc/<pid>/comm` 的限制，
> 不是 psutil 的 bug。想要完整名字必须用 `Process.name()` 之外的手段，
> 比如解析 `cmdline()[0]`。这个坑见 7.5。

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

实测参考（普通云主机，约 100 个进程，见 `code/04-benchmark.py` 可复现）：

| 采集方式 | 相对耗时 | 说明 |
|:---|:---:|:---|
| `process_iter()` 只要 pid | 1.0× | 最快，只列 /proc 目录 |
| `process_iter(['name'])` | ~1.5× | 每进程读 1 个文件 |
| `process_iter(['name','pid','memory_info'])` | ~2.5× | 每进程多读几个文件 |
| 逐进程 `Process(pid).name()` | ~2.5× | 每次新建对象，无缓存复用 |
| 逐进程 `.as_dict(attrs=[...])` | ~2.5× | 等价，但写法更整洁 |
| `/proc/stat` 手写解析（CPU） | 与 psutil 相近 | psutil 已经很少额外开销 |

> **结论**：**用 `process_iter(attrs=[...])` 并只取需要的字段**，
> 比"全量 `as_dict()`"快得多。在 2000 进程的机器上，这个优化能把单轮采集
> 从数百毫秒压到几十毫秒 —— 直接决定了你能不能用 1 秒的采样周期。

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

**更稳的写法**：用系统启动后的**单调时长**做交叉校验：

```python
import time, psutil

def process_age_seconds(p) -> float:
    """进程已存活秒数；用 boot_time + monotonic 交叉校验，防止时钟跳变。"""
    wall = time.time() - p.create_time()
    mono = (time.monotonic() - psutil.boot_time() * 0)  # 占位：monotonic 与 boot_time 不同基准
    # 实用做法：只要 wall < 0 就认为时钟跳变，退化为"用当前差值取绝对安全值"
    if wall < 0:
        # 时钟被回拨过：退回使用 psutil 的进程生命周期近似
        return max(0.0, -wall if False else 0.0)
    return wall
```

> 上面的示例刻意展示了"不要强行拼凑不同时钟基准"。**工程结论**：
> 用 `time.time() - create_time()` 计算存活时长，**并显式检测负值**；
> 需要高精度时长请用 `time.monotonic()`，但它**不能**与 `create_time()` 混算。

---
