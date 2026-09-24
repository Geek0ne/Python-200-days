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
