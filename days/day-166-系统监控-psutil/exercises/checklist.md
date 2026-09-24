# Day 166 — 系统监控（psutil）· 完成清单与练习

> 建议顺序：先读完 `README.md`（尤其第 2、3、5 节），再跑 `code/` 下的 5 个文件，
> 最后做练习。**每个练习都要求"能解释为什么"，而不只是"跑通"。**

---

## ✅ 今日完成清单

### 一、环境与依赖

- [ ] 已确认 Python ≥ 3.9：`python3 -V`
- [ ] 已安装 psutil：`pip install psutil`
- [ ] 已验证版本：`python3 -c "import psutil; print(psutil.__version__)"`

### 二、跑通示例代码（每项都要求先预测输出，再运行验证）

- [ ] `cd days/day-166-系统监控-psutil/code`
- [ ] `python3 01-system-info.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 01-system-info.py --sensors` → 看到 CPU/内存/磁盘/网络/系统 五个区块
- [ ] `python3 02-process-monitor.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 02-process-monitor.py --top 5 --memory-detail` → 看到进程排行与内存四字段对比
- [ ] `python3 03-pitfalls.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 03-pitfalls.py` → 十条陷阱逐条跑完，末尾看到"十条陷阱回顾"
- [ ] `python3 04-benchmark.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 04-benchmark.py --rounds 5` → 拿到本机的采集耗时倍数
- [ ] `python3 05-monitor-tool.py --self-test` → 输出 `SELF-TEST OK`
- [ ] `python3 05-monitor-tool.py --duration 5 --interval 1 --out-dir ./reports`
      → 退出码 0，`reports/` 下生成 `.json` 与 `.md` 两个文件
- [ ] `python3 05-monitor-tool.py --duration 2.5 --interval 0.5 --cpu 1 --low-gap 0.5 --need 2 --dry-run`
      → 退出码 **2**，并看到 `⚠ CPU 达到 ...%`

### 三、动手改造（"读懂了"的唯一证明）

- [ ] 把 `01-system-info.py` 的 `--interval` 改成 `0.1` 与 `3.0` 各跑一次，
      观察 CPU 使用率的**波动幅度**变化，并写下一句话解释原因
- [ ] 把 `03-pitfalls.py --only 9` 的 `need` 从 3 改成 1 再改成 5，
      记录告警次数从几条变到几条
- [ ] 在 `05-monitor-tool.py` 里新增一个 `--swap` 阈值，让 swap 使用率也能告警
      （提示：`Sample.swap_percent` 可能是 `None`，必须处理）

### 四、概念自检（不看 README，口头或纸面回答）

- [ ] 我能说清 `counter` / `gauge` / `state` 的区别，并各举一个 psutil 的例子
- [ ] 我能解释为什么 `cpu_percent()` 第一次调用返回 `0.0`
- [ ] 我能解释为什么"采样间隔"必须用 `time.monotonic()`
- [ ] 我能解释 `rss` / `vms` / `uss` / `pss` 的区别，并说出各自适用场景
- [ ] 我能解释为什么容器里 `virtual_memory().total` 是宿主机内存，以及正确读法
- [ ] 我能解释"滞回带 + 连续次数"两个机制各自解决什么问题
- [ ] 我能说出退出码 `0 / 2 / 1` 三者的语义差异，以及为什么告警用 `2` 而不是 `1`

---

## 📝 基础练习题（1–3）

### 练习 1：安全的内存水位播报

写一个脚本，每隔 2 秒打印一次内存状态，共 5 次。要求：

1. 使用 `psutil.virtual_memory()`
2. **必须同时**打印 `used` 与 `available` 两个口径，并各自换算成 GiB
3. 当 `available` 低于总内存的 20% 时，在行首加 `⚠` 前缀
4. swap 未启用时（`total == 0`）不能打印 `0.0%`，而应打印"未启用"

**验收标准**：把脚本里的 `time.sleep(2)` 改成 `time.sleep(0.2)` 也应该正常输出
（说明你没有把逻辑写死在某一次读数上）。

<details>
<summary>💡 提示（先自己写，卡住了再看）</summary>

- `vm.percent` 的口径是 `(total - available) / total`，所以"available 低于 20%"
  等价于 `vm.percent > 80`。两种写法都对，但**要能说清它们是等价的**。
- `human_bytes` 可以直接从 `01-system-info.py` 抄（或用 `f"{n / 2**30:.1f} GiB"`）。
- swap 判断：`sw.total == 0` → 未启用。
</details>

---

### 练习 2：计数器差分求"网卡速率表"

写一个函数 `nic_rates(interval: float) -> dict[str, dict[str, float]]`：

- 采样两次 `psutil.net_io_counters(pernic=True)`，中间用 `time.monotonic()` 实测间隔
- 返回每个网卡的 `sent_bps` / `recv_bps`（字节/秒）
- 网卡在两次采样之间**消失**时不能崩（用 `dict.get` 处理）
- 计数器被重置（差分出现负数）时，该网卡本轮速率为 `0.0` 并额外返回一个
  `"reset": True` 标记

**验收标准**：函数在 `interval=0` 时不得抛 `ZeroDivisionError`，而应返回空字典或全 0。

<details>
<summary>💡 提示</summary>

- 先取 `before = psutil.net_io_counters(pernic=True)` 并记录 `t0 = time.monotonic()`
- `time.sleep(interval)` 后取 `after` 与 `t1`，`dt = t1 - t0`
- 逐 `nic in before`：若 `nic not in after` → 跳过；若 `after[nic].bytes_sent < before[nic].bytes_sent`
  → 视为重置
</details>

---

### 练习 3：带四类计数的进程扫描

基于 `02-process-monitor.py` 的 `scan_processes`，写一个独立脚本，输出：

```text
看到 N 个 pid → 成功 X，已退出 Y，无权限 Z，僵尸 W
僵尸进程列表: <pid> (<name>) ...   # 若无则打印 "无"
```

要求：

1. 使用 `process_iter(attrs=[...])`，**只请求** `pid` 与 `status`
2. 僵尸进程（`status == 'zombie'`）必须单独列出 pid
3. 用 `os.getpid()` 排除脚本自身
4. 必须用 `try/except` 覆盖 `NoSuchProcess` / `AccessDenied` / `ZombieProcess` 三类，
   **不允许**使用 `except Exception`

**验收标准**：连续跑 10 次不出现任何未捕获异常。

---

## 🧠 思考题（口头回答即可，不写代码）

1. **"CPU 使用率 80%" 这句话缺了哪个必要参数？** 为什么没有这个参数，这个数字就没有意义？
   （提示：想想采样窗口，以及"谁在什么粒度上平均"。）

2. **一个进程的 `Process.cpu_percent()` 返回 `450%`，你该报警吗？** 判断依据是什么？
   如果这台机器有 4 个核、而这个进程是你自己写的多线程爬虫，结论会变吗？

3. **为什么 "所有进程的 RSS 之和" 经常超过物理内存总量？**
   如果要回答"现在实际被占用了多少物理内存"，应该用什么口径？

4. **你的监控脚本连续 3 次采到 CPU 为 0.0%，你确定机器是空闲的吗？**
   列出至少两种可能导致"假的 0.0%"的原因。

5. **告警阈值该定在 80% 还是 95%？** 这个问题为什么不能只从技术层面回答？
   什么是"告警疲劳"，它与"漏报"哪个更危险？为什么？

---

## 📚 延伸阅读

- `README.md` 第 2.8 节 —— 容器 vs 宿主机（cgroup 读法）
- `README.md` 第 3.7 节 —— 采样开销与观测者效应（附本机实测数据）
- `diagrams/README.md` —— 四层架构图与采样差分序列图
- psutil 官方文档：<https://psutil.readthedocs.io/>
- Linux `/proc` 手册：`man 5 proc`

---

## 🚀 进阶挑战题（4–6，选做但强烈推荐）

### 挑战 4：给监控脚本加"趋势"而不是"水平"

现在 `05-monitor-tool.py` 只看**当前水平值**（如内存 28%）。但运维真正关心的是**趋势**：

> "内存从 20% 涨到 28% 用了 5 分钟" —— 这是泄漏的开始。
> "内存一直在 28%" —— 这是健康状态。

**任务**：为内存实现一个**线性趋势检测**：

1. 用内存使用率的采样序列做最小二乘拟合，得到斜率（百分比/秒）
2. 当"按当前斜率继续，30 分钟内会突破告警阈值"时，额外输出一条**预测告警**
3. 预测告警与水平告警**各有各的阈值**，不要混用

**验收标准**：

- 用一个明显上升的模拟序列（如 `[20, 22, 24, 26, ...]`）测试，应触发预测告警
- 用一个平稳抖动的序列（如 `[28, 28.1, 27.9, 28.2, ...]`）测试，**不应**触发
- 采样点少于 5 个时不做预测（样本不足的预测是伪科学）

<details>
<summary>💡 提示</summary>

最小二乘斜率（一元线性回归）：

```python
def slope(xs: list[float], ys: list[float]) -> float:
    """返回 ys 关于 xs 的线性拟合斜率。"""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else 0.0
```

时间轴用 `sample.ts - samples[0].ts`（单调时钟，见陷阱 4）。

⚠ **别忘了**：趋势检测对噪声极其敏感。一个 0.5% 的抖动在两条采样点之间
就能拟出"正向斜率"。所以务必：
1. 用**足够多的点**（≥5，最好 ≥10）；
2. 对斜率本身也做一次**去抖**（连续 N 次都为正才认）；
3. 报告里**同时给出斜率和样本数**，让读者能自己判断可信度。
</details>

---

### 挑战 5：容器感知的容量判定（真实工程痛点）

`psutil.virtual_memory()` 在容器里返回**宿主机**内存。请实现一个正确的容量判定层：

```python
def effective_memory() -> dict:
    """返回容器感知的内存口径。

    {
      "limit": int | None,      # 真实可利用上限（cgroup 限额优先）
      "source": "cgroup" | "host",
      "total": int,
      "used": int,
      "percent": float,
    }
    """
```

要求：

1. `cgroup v2`（`memory.max` = `"max"` 表示无限制）与 `cgroup v1`
   （`memory.limit_in_bytes` 用接近 2^63 的极大值表示无限制）都要支持
2. 必须在返回值里**显式标注 `source`** —— 让调用方知道自己拿的是哪个口径
3. 容器内：`percent` 用 `cgroup_usage / cgroup_limit`，**不能**用宿主的 `vm.percent`
4. 不在容器内：退化为 `psutil.virtual_memory()`，`source = "host"`
5. 无限制的 cgroup（`max`/极大值）应视为"不在容器内"，退化到 host 口径

**验收标准**：写一个自测，覆盖以下四种输入（可用读取函数注入 mock）：

| cgroup v2 memory.max | cgroup v1 limit | 期望 source |
|:---|:---|:---|
| `"max"` | 不存在 | `host` |
| `"536870912"` | — | `cgroup`，limit=512MiB |
| 不存在 | `9223372036854771712` | `host`（极大值要挡掉） |
| 不存在 | `268435456` | `cgroup`，limit=256MiB |

> **为什么这题重要**：监控容器却不看 cgroup，等于在监控宿主机。
> 这是生产环境最常见的"监控假空"事故来源 —— 告警从未触发过，
> 直到容器被 OOM Killer 杀掉。

---

### 挑战 6：把监控脚本做成"可被编排调用"的工具

现在的脚本是给人看的。但真实运维里，监控脚本要**被别的程序调用**
（cron、CI、Kubernetes liveness probe、上层编排）。

**任务**：改造 `05-monitor-tool.py`，使其满足以下"可编排"要求：

1. **机器可读的 stdout**：加 `--format json`，让 stdout 只输出**一行 JSON**
   （所有人类可读的进度信息改为输出到 **stderr**）
   —— 这样 `./monitor --format json | jq .summary.cpu.max` 才能工作
2. **退出码契约**：`0` 正常 / `2` 告警 / `1` 失败，**三种都要有测试**
3. **超时自保护**：加 `--max-runtime`，超过就停止采样、输出**已完成的部分**、
   以退出码 2 结束（"我采不全，但我不装死"）
4. **不因单个指标失败而整体失败**：某个分区读不到时只记一次"采样缺口"计数，
   继续采其它指标

**验收标准**（逐条实测）：

```bash
# ① JSON 只出现在 stdout，人类信息在 stderr
./05-monitor-tool.py --duration 1 --format json 2>/dev/null | python3 -c "import json,sys; json.load(sys.stdin); print('JSON OK')"

# ② 退出码 0
./05-monitor-tool.py --duration 1 --cpu 100; echo $?     # → 0

# ③ 退出码 2
./05-monitor-tool.py --duration 1.5 --interval 0.5 --cpu 1 --low-gap 0.5 --need 2; echo $?   # → 2

# ④ 退出码 1（参数错误）
./05-monitor-tool.py --interval 0; echo $?               # → 1
```

> **设计要点**：监控工具是**被编排的对象**，不是给人交互的程序。
> 判断标准很简单：**如果它的行为不能被另一个程序可靠推断，它就没法进生产**。
> `stdout` 是数据，`stderr` 是日志，退出码是结论 —— 这不是风格问题，是接口契约。

---

## 🎯 自我检验：你真正掌握了吗？

不用看笔记，回答下面的问题。全部答得上，今天就算过关：

| # | 问题 | 一句话答案（自查用） |
|:--:|:---|:---|
| 1 | 监控和"读一次数据"的区别是什么？ | 监控 = 采集 + 时间维度 + 判定 + 表达，四者缺一不可 |
| 2 | 为什么 `cpu_percent()` 要先"预热"？ | 使用率是两次读数之差算出来的，首次无参照物 |
| 3 | `counter` 与 `gauge` 的处理方式有何不同？ | counter 要差分，gauge 直接读 |
| 4 | 采样间隔为什么用 `monotonic()`？ | 它不受 NTP 校时影响，`time.time()` 会被回拨成负数 |
| 5 | `rss` 与 `uss` 分别回答什么问题？ | rss：它占了多大内存；uss：杀掉它能省多少 |
| 6 | 为什么容器里 `virtual_memory().total` 是宿主的？ | 容器共享宿主的 `/proc` 视图，限额在 cgroup |
| 7 | 为什么进程枚举要记四类计数？ | 才能区分"数据少"是正常的还是漏采的 |
| 8 | 滞回带解决什么问题，连续次数解决什么问题？ | 滞回：边界抖动；连续次数：孤立尖峰 |
| 9 | 告警为什么用退出码 2 而不是 1？ | 2 = 被监控对象的问题，1 = 我自己的错，必须能区分 |
| 10 | 监控脚本为什么不应该自己杀进程？ | 自动处置风险极高，必须由人确认；监控的职责是观测与告知 |

---

## 📌 提交与记录建议

做完练习后，把你的代码放在本目录下的 `solutions/` 里（不进版本库也没关系），
并在下面记录一句"我踩到了什么坑"—— 这一句比代码更有价值：

```text
我的记录:
- 坑 1:
- 坑 2:
- 我最有把握的一点:
- 我还不确定的一点:
```
