# Day 170 — 定时任务 · 完成清单与练习

> 先读 `README.md`（第 2、3 节），再跑 `code/` 下 4 个脚本，最后做练习。
> **每道题都要能回答"为什么"** —— 尤其"为什么幂等比准确更重要"。

---

## ✅ 今日完成清单

### 一、环境与依赖

- [ ] 已确认 Python ≥ 3.9：`python3 -V`
- [ ] 已安装三个包：`pip install schedule apscheduler sqlalchemy`
- [ ] 已验证版本：
      `python3 -c "from importlib.metadata import version; print(version('schedule'), version('apscheduler'), version('sqlalchemy'))"`
- [ ] 已确认四件套可导入：
      `python3 -c "from apscheduler.schedulers.background import BackgroundScheduler; from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore; from apscheduler.triggers.cron import CronTrigger; print('ok')"`
- [ ] 已确认复合触发器在 `apscheduler.triggers.combining`（不是 `.and` / `.or`）

### 二、跑通示例代码（先预测输出，再运行验证）

- [ ] `cd days/day-170-定时任务/code`
- [ ] `python3 01-basic-schedule.py --self-test` → `SELF-TEST OK`（22/22）
- [ ] `python3 01-basic-schedule.py --demo compare`
      → 看到朴素循环 4 轮后漂移 20s（倍率 1.083）
- [ ] `python3 01-basic-schedule.py --demo schedule --seconds 1 --rounds 3`
      → 触发 3 次，间隔均 ≈1.00s
- [ ] `python3 01-basic-schedule.py --demo apscheduler --seconds 1 --rounds 3`
      → 打印出 `misfire_grace_time / coalesce / max_instances`
- [ ] `python3 02-pitfalls.py --self-test` → `SELF-TEST OK`（13/13）
- [ ] `python3 02-pitfalls.py` → 10 个坑逐个复现
      → 特别注意坑 ①（三次推算返回同一时刻）和坑 ⑦（5 个任务 vs 1 个）
- [ ] `python3 03-advanced-scheduler.py --self-test` → `SELF-TEST OK`（24/24）
- [ ] `python3 03-advanced-scheduler.py --demo persist`
      → 亲眼看到 `next_run_time` 跨进程被持久化、重启后任务原样恢复
- [ ] `python3 03-advanced-scheduler.py --demo coalesce`
      → 4 秒内理论到期 4 次，实际只跑 1~2 次
- [ ] `python3 04-backup-scheduler.py --self-test` → `SELF-TEST OK`（33/33）
- [ ] `python3 04-backup-scheduler.py --dry-run` → 连续 3 次成功报告
- [ ] `python3 04-backup-scheduler.py --selftest-job`
      → 每 2 秒触发一次，**注意控制台先打 `⏭ 跳过：今天已成功备份过`**（幂等生效）
- [ ] `python3 04-backup-scheduler.py --register`
      → 打印 `next_run = 次日 03:00`；`Ctrl-C` 后重启，任务仍在

### 三、动手改造（"读懂了"的唯一证明）

- [ ] 把 `04` 的 `--keep-days` 改成 `0`，跑 `--dry-run`，观察 prune 把上一个包也删了
      —— 想清楚为什么生产上**绝不能**把 keep-days 设成 0
- [ ] 给 `04` 加一个 `--verify-only` 参数：不解包，只算归档的 sha256 并与 `backup_log` 比对
- [ ] 给 `04` 的 `verify()` 故意造一个"能写出来但解不开"的包（写满不压缩数据再截断），
      确认它会被识别并删除
- [ ] 把 `02` 的坑 ① 改成：previous 传 None 时循环 10 次，统计它返回了几种不同时间
- [ ] 用 `03` 的 `nxt()` 推算「每月最后一天」，写出一个等价的 `CronTrigger`
- [ ] 给 `03` 补一个 `IntervalTrigger` + `AndTrigger` 的**超时保护**实验：
      放进子进程跑并设 5s 超时，证明它确实不返回（复现 README 陷阱 ⑪）
- [ ] 把 `01` 的 `demo_schedule` 改成 0.2 秒间隔，观察 `run_pending()` 的轮询
      精度如何影响实际触发时刻（提示：`sleep(1)` 的循环撑不住 0.2s 间隔）
- [ ] 把 `04` 的 `JobLock.ttl` 改成 0.1，然后让持锁的进程 `kill -9`，
      验证下一个实例能在一轮之后抢到锁

### 四、概念自检（不看 README）

- [ ] 我能说清调度要解决的 4 个问题：触发、并发、持久化、错过补偿
- [ ] 我能解释为什么 `while True: work(); sleep()` 会漂移，而 cron/interval 不会
- [ ] 我能说出 `get_next_fire_time(None, now)` 为什么会原地打转
- [ ] 我知道为什么推算时间时基准点必须带 tzinfo（naive 会怎样）
- [ ] 我能区分 `coalesce` / `max_instances` / `misfire_grace_time` 各自防哪种事故
- [ ] 我能解释 `AndTrigger` 为什么不能用来拼两个 cron 表达式，以及正确写法是什么
- [ ] 我能说明 `job_state` 为什么要求函数必须在模块顶层
- [ ] 我能解释 `id` + `replace_existing=True` 为什么叫"幂等注册"
- [ ] 我能说出多实例重复执行的三种解法，以及各自代价
- [ ] 我能解释为什么锁必须带 TTL，否则会出现"没有任何报错但任务再也不会运行"
- [ ] 我能解释为什么备份系统"打完包必须立刻解包校验"

---

## 📝 练习题

### 基础题（每题 15 分钟）

**1. 漂移计算**
每 30 分钟执行一次任务，任务本身耗时 40 秒。连续跑 100 次后，
朴素 `sleep` 写法比调度器累计落后多少分钟？

<details>
<summary>参考答案</summary>

朴素循环的实际间隔 = 30 + 40/60 = 30.67 分钟。
100 次共落后 `40/60 × 99 ≈ 66` 分钟（约 1.1 小时）。

调度器（interval 或 cron）算的是**绝对时刻**，不受任务耗时影响，偏差为 0。
</details>

**2. 选 Executor**
下面三个任务分别该用哪个 Executor？说明理由。
① 调用 3 个外部 HTTP 接口，每响应 2 秒
② 对 800 张图片批量做感知哈希
③ 任务函数本身是 `async def`，内部 `await` 了 5 个异步请求

<details>
<summary>参考答案</summary>

① `ThreadPoolExecutor`（IO 等待为主，线程即可）
② `ProcessPoolExecutor`（纯 CPU 计算，绕 GIL）
③ `AsyncIOScheduler` + `AsyncIOExecutor`（本来就是协程，别绕线程）

注意：② 用进程池时，任务函数和参数**必须可 pickle**，不能传数据库连接/文件句柄。
</details>

**3. 三个参数**
一个每 5 分钟采集一次指标的任务，某天机器卡了 20 分钟。分别用
`coalesce=False/True` 和 `misfire_grace_time=0/300` 组合，会执行几次？各有什么风险？

<details>
<summary>参考答案</summary>

- `coalesce=False, grace=0`：0 次（迟到全部丢弃），风险是**丢数据**，但干净
- `coalesce=True, grace=0`：0 次（同上）
- `coalesce=False, grace=300`：积压 4 次但只有落在这 5 分钟内的能跑 → 0~1 次
- `coalesce=True, grace=300`：最多 1 次（合并后的最后一次）

采集类任务通常选 `coalesce=True` + 较宽 grace；
但**如果你要的是"每次都不能少"**（比如对账、计费），那就该换成
`interval` 拉取"自上次成功以来的增量"，而不是指望调度器帮你补跑。
</details>

### 进阶题（每题 30 分钟）

**4. 设计补跑**
需求：每天 03:00 生成前一天的账单，**一天都不能少**。
服务器可能在任意时刻宕机，宕机时长不确定。
用 `schedule` / APScheduler 各自怎么实现？对比两种方案。

<details>
<summary>参考答案</summary>

`schedule`：做不到。它没有持久化，重启即丢，且没有 misfire 概念。

APScheduler：
1. 用 `SQLAlchemyJobStore` 持久化任务
2. `coalesce=True` + 较宽的 `misfire_grace_time`
3. **但真正的保障不在调度器里** —— 调度器保证不了"停机 3 天后补 3 次"

正确设计是**拉取式**：任务不按"每天"触发，而是每 10 分钟醒一次，
检查 `last_billed_date` 与 `昨天` 的差距，有缺口就补算。
这样无论停机多久，醒来后都会自动把缺口补齐，且天然幂等。
</details>

**5. 锁与幂等**
`04` 里有两道闸：互斥锁 + "今天已成功过"幂等检查。
如果只有其中一道会怎样？两道的职责有什么区别？

<details>
<summary>参考答案</summary>

只有锁：能挡住**多实例同时跑**，但挡不住"同一个实例一天内被触发多次"
（misfire 补跑、coalesce 合并、手工 force），仍可能重复出包。

只有幂等（查 `backup_log` 里的 day）：能挡住**重复执行**，
但挡不住两个实例**同时**通过了检查、同时写日志、同时打包——
典型的 check-then-act 竞态。

职责区分：
- 锁管的是**同一时刻的并发**（互斥）
- 幂等管的是**跨时间的重复**（重复执行无害）

两道都要，因为它们防的是完全不同的失败模式。
</details>

**6. 踩坑复现**
`04` 的 `prune()` 曾经因为把 `backup-20260929-161234` 整体用 `%Y%m%d` 解析而
**永远删不掉任何文件**，且没有任何报错。请回答：
① 为什么这个 bug 会"静默"？② 你会怎么在代码里防住这类问题？

<details>
<summary>参考答案</summary>

① `strptime` 抛的 `ValueError` 被 `except ValueError: continue` 吞掉，
   于是每个文件都走"跳过"分支，函数正常返回空列表，调用方以为"没有可删的"。

② 防御手段：
- **别用裸 except 吞异常**：`continue` 前至少 `log.warning`，让异常可见
- 关键路径用"**必须解析成功**"的语义：解析不了就报错，而不是静默跳过
- 加一条断言型自测：造一批已知年龄的文件，断言 prune 后数量正确
  （本课的 `05` 保留策略用例就是为此存在的）
</details>

### 挑战题（1 小时以上）

**7. 多副本 + 失败告警**
你的服务有 6 个副本，每个都注册了同一个"对账"任务（每天 02:00）。
要求：① 只有一个副本执行；② 失败时**保证有人收到**；③ 任务能优雅停机。

请写出完整方案（锁放哪、告警怎么接、停机时怎么避免正在跑的任务被 kill）。

<details>
<summary>参考答案</summary>

① 互斥：用**所有副本都能连到的那个东西**当锁——通常是数据库行锁
   （如 `04` 的 `JobLock`）或 Redis `SET NX`。关键：**锁要带 TTL**，
   否则持锁进程崩溃后任务静默地再也不会运行。

   更简单的替代：把调度器从 web 进程里拆出去，**只部署 1 份**。
   6 个副本只需要 1 个跑对账，拆出去反而更简单可靠。

② 告警：`add_listener(EVENT_JOB_ERROR)` 把异常接到 Webhook/飞书；
   再加一条"心跳兜底"——对账成功后写 `last_success_at`，
   另一个每 10 分钟跑的检查任务发现它超过 26 小时没更新就告警
   （这样即使调度器整个挂了，也能被发现）

③ 优雅停机：
   - 收到 SIGTERM 后 `scheduler.shutdown(wait=True)`，等正在跑的任务结束
   - 更稳妥的做法：**先从调度器里把自己摘掉**（`pause_job` 或
     `remove_job`），再等任务跑完 —— 避免停机窗口正好落在触发点
   - 容器编排要给 `terminationGracePeriodSeconds` 留够任务的最坏耗时
</details>

**8. 从零实现一个调度器**
不依赖 APScheduler，用标准库实现一个能跑 `cron` 表达式的迷你调度器，要求：
① 支持 `分 时 * * *`（每分钟、每小时、每天几点）
② 进程重启后不重复补跑停机期间的任务
③ 同一个任务不会并发执行两次

提示：② 靠"持久化 `last_run_at`，启动时若 `last_run_at < 今天该跑的时段` 就跳过"；
③ 靠"任务开始时写 `running_until`，结束清除；启动时看到未清除的残留就知道上次被杀了"。

<details>
<summary>参考答案要点</summary>

这三个要求其实就对应了三个可替换组件的最小实现：
① Trigger → 解析 cron 字段，算 next_run_time（注意别踩 `AndTrigger` 那种死循环）
② JobStore → 一个 JSON/SQLite 表，存 `id / next_run_time / last_run_at`
③ Executor → `threading.Lock` + 状态位（比线程池更简单，因为你只要求不并发）

写完你会发现 APScheduler 也就 2000 行，而它多出来的 98% 是在处理
时区、夏令时、job 依赖、executor 选型、事件系统这些"边界自由"。
**这正是"够用"和"生产级"的分界线。**
</details>

---

## 🎯 自我检验（做完练习后逐条打勾）

- [ ] 我写的定时任务在**进程重启后**不会丢，也不会重复补跑
- [ ] 我的任务失败时**一定会有人知道**（不是只写日志）
- [ ] 我的任务在**多副本部署**下不会重复执行
- [ ] 我能说出 `coalesce` / `max_instances` / `misfire_grace_time`
      各自的默认值**和**我为什么这么设
- [ ] 我的备份/对账类任务**有校验或自检**，不是"文件生成了就算成功"
- [ ] 我知道心跳 `activeHours` 的 `start` 含、`end` 不含，
      以及配错时会在任务面板里留下一堆 `failed` 噪音
