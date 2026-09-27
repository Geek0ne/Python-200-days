# Day 170 — 定时任务

> **一句话定义**：定时任务 = **在正确的时间点，可靠地执行一段代码**。
> 难点不在"怎么定时"，而在于 **错过怎么办、重复启动怎么办、重启后还记得吗、跑太久撞车了怎么办**。
> 本课用两个库把这件事讲透：`schedule`（极简玩具→小工具）与 `APScheduler`（生产级四件套）。

---

## 1. 学习目标

学完本课，你应该能够：

- [ ] 说清"调度"要解决的 4 个真问题：**触发、并发、持久化、错过补偿**
- [ ] 用 `schedule` 写出最小可跑的定时器，并说清它**为什么不能用于生产**
- [ ] 用 `APScheduler` 的 **Trigger / JobStore / Executor / Scheduler** 四件套组织一个调度程序
- [ ] 用 `cron` / `interval` / `date` 三种触发器分别表达"每天 3 点""每 30 秒""某年某月某日一次"
- [ ] 正确设置 `misfire_grace_time`、`coalesce`、`max_instances`，并说清三者各自防的是哪种事故
- [ ] 用 `SQLAlchemyJobStore` 做任务持久化，做到"进程重启后任务不丢、也不会重复补跑"
- [ ] 独立写出一个**定时备份系统**：备份 → 校验 → 保留策略 → 报告
- [ ] 识别多实例部署下的"重复执行"事故，并知道至少 3 种解法（单实例 / 分布式锁 / 外部编排）

---

## 2. 概念解释

### 2.1 先问：为什么不能直接 `time.sleep`？

初学者最常见的"定时"写法：

```python
import time

while True:
    do_something()
    time.sleep(3600)   # 睡一小时
```

这段代码有 4 个致命问题，它们正好对应本课的 4 个核心概念：

| 问题 | 具体表现 | 对应的概念 |
|:---|:---|:---|
| **漂移（drift）** | `do_something()` 花了 5 分钟，那实际间隔变成 65 分钟，日积月累会越偏越远 | 触发（Trigger） |
| **阻塞** | 睡眠期间什么都干不了，多个任务只能排队 | 执行器（Executor） |
| **丢失** | 进程重启，任务表回到零点，今天的备份没了 | 持久化（JobStore） |
| **错过即无** | 机器 3:00 关机、3:05 开机，3:00 的任务永远不跑 | 错过补偿（misfire / coalesce） |

> **设计原理**：一个"调度器"的本质就是把这 4 件事从业务代码里抽出来，
> 交给一个专职组件管理。你只声明"什么时候做什么"，剩下的边界情况由框架兜底。

### 2.2 调度的三要素

任何调度系统都可以拆成三个概念（`cron` 也是，只不过它写死在配置里）：

```text
        ┌──────────────┐
        │   Trigger    │  「什么时候执行？」
        │ 触发器        │  cron: 0 3 * * *  → 每天 03:00
        └──────┬───────┘  interval: 每 30 秒
               │ 算出下一次触发时间 next_run_time
               ▼
        ┌──────────────┐
        │  Scheduler   │  「谁来决定现在该不该跑？」
        │ 调度器        │  主循环：不断比对 now 与 next_run_time
        └──────┬───────┘
               │ 到期就提交
               ▼
        ┌──────────────┐
        │  Executor    │  「用什么去跑？」
        │ 执行器        │  线程池 / 进程池 / asyncio 事件循环
        └──────┬───────┘
               │ 跑完回写结果
               ▼
        ┌──────────────┐
        │  JobStore    │  「任务记在哪？」
        │ 作业存储      │  内存字典 / SQLite / PostgreSQL / Redis
        └──────────────┘
```

**为什么叫"作业"（Job）而不是"函数"**：一个 Job = **函数引用 + 触发器 + 参数 + 状态（上次运行、下次运行、运行次数）**。
持久化保存的就是这个"状态对象"，所以 Job 的函数必须是**可以被重新导入的顶层函数**（不能是 lambda 或局部函数）——这是第 6 节最重要的坑。

### 2.3 `schedule` 库：把"人话"编译成触发器

`schedule` 的卖点是**读起来像英语**：

```python
import schedule, time

schedule.every(10).minutes.do(backup)          # 每 10 分钟
schedule.every().day.at("03:00").do(backup)    # 每天 03:00
schedule.every().monday.at("08:30").do(report) # 每周一 08:30

while True:
    schedule.run_pending()   # 检查有没有到期的任务
    time.sleep(1)            # 自己睡 1 秒，再检查
```

**它的内部实现极其简单**，简单到你应该"看穿"它：

- `schedule.every(10).minutes` 返回一个 **Job 构造器**，`.do(f)` 把 `f` 注册进 `schedule.default_scheduler.jobs` 列表；
- 每个 Job 记录 `interval`（间隔秒数）+ `next_run`（下次运行时间戳）+ `last_run`；
- `run_pending()` 遍历所有 Job，`now >= next_run` 就执行，并把 `next_run` **对齐到整点倍数**（所以它不像 `sleep` 那样漂移）。

| 特性 | `schedule` | 说明 |
|:---|:---|:---|
| 触发器 | interval + day/time | 只有这两种，没有秒级 cron |
| 持久化 | ❌ 无 | 重启即丢 |
| 并发 | ❌ 单线程串行 | 一个任务卡住，后面全堵 |
| 错过补偿 | ❌ 无 | 停机期间的任务直接跳过 |
| 依赖 | 0（纯标准库） | 复制一个文件就能用 |
| 适用 | 单体小脚本、树莓派灯控、本地定时提醒 | **别用来跑生产关键任务** |

> **一句话结论**：`schedule` 是"带索引的闹钟"，`APScheduler` 是"带值班表的调度中心"。

### 2.4 `APScheduler`：四件套对应四种自由

`APScheduler` 把它自己的架构直接暴露给你，于是每一种需求都对应一个可替换组件：

| 组件 | 可选实现 | 什么时候换 |
|:---|:---|:---|
| **Trigger** | `cron` / `interval` / `date` / `and` / `or` | 需要"工作日 9-18 点每 5 分钟" |
| **JobStore** | `MemoryJobStore` / `SQLAlchemyJobStore` / `RedisJobStore` / `MongoJobStore` | 需要重启不丢 |
| **Executor** | `ThreadPoolExecutor` / `ProcessPoolExecutor` / `AsyncIOExecutor` / `GeventExecutor` | 任务 CPU 密集 / 是 async 函数 |
| **Scheduler** | `BlockingScheduler` / `BackgroundScheduler` / `AsyncIOScheduler` / `GeventScheduler` | 主线程要不要被占住 |

最小的生产级骨架（**记住这个模板，它能覆盖 80% 场景**）：

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

scheduler = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")},
    executors={"default": ThreadPoolExecutor(10)},
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
)
scheduler.add_job(backup, "cron", hour=3, minute=0, id="daily-backup", replace_existing=True)
scheduler.start()      # 后台线程开始调度，主线程继续干别的
```

**为什么 `id` 和 `replace_existing=True` 这么重要**：定时任务程序经常被重启。
如果代码里每次都 `add_job` 一次而 JobStore 又持久化，就会出现**同一任务被注册 N 次**，
重启 10 次就每天备份 10 次。给任务一个稳定 `id` + `replace_existing=True` 让它变成**幂等注册**。

### 2.5 任务持久化：JobStore 到底存了什么

以 `SQLAlchemyJobStore` 为例，它只建**一张表** `apscheduler_jobs`：

| 列 | 含义 |
|:---|:---|
| `id` | 任务的唯一标识（你给的那个 `id`，不给则自动生成 UUID） |
| `next_run_time` | 下次运行时间（**调度器就是按这一列排序取任务的**） |
| `job_state` | Pickle 序列化后的整个 Job 对象（函数引用、参数、trigger 配置） |

两个由此推出的**硬约束**：

1. **`job_state` 是 pickle**，所以被调用的函数必须**在模块顶层可导入**。
   把函数写在 `if __name__ == "__main__":` 里、或写成本地函数，重启后反序列化会 `ModuleNotFoundError` / `AttributeError`。
2. **数据库中 `next_run_time` 是共享状态**，所以多个进程连同一个库时会**互相抢任务**——
   这正是"多实例重复执行"问题的根源，也是我们能拿它做**互斥**的原因。

### 2.6 多实例部署的经典事故

```text
        ┌─────────────┐        ┌─────────────┐
        │ 容器 A       │        │ 容器 B       │
        │ Scheduler   │        │ Scheduler   │
        └──────┬──────┘        └──────┬──────┘
               │                      │
               └────────┬─────────────┘
                        ▼
              ┌──────────────────┐
              │  同一个任务：       │
              │  每天 03:00 备份   │  ← 3:00 时 A、B 同时认为自己该跑
              └──────────────────┘
                        ▼
              💥 备份了两个文件 / 文件互相覆盖 / 邮件发了两封
```

**三种标准解法**：

| 方案 | 做法 | 代价 |
|:---|:---|:---|
| 单实例 | 调度器只部署 1 个副本（web 多副本，scheduler 单独一份） | 有单点，但要可靠简单 |
| 分布式锁 | 任务开头抢一把锁（Redis `SET NX` / 数据库行锁），抢不到就退出 | 需要外部依赖 |
| 外部编排 | 交给 `cron`、K8s CronJob、Airflow 等"只管触发"的系统 | 要接受它的世界观 |

> 记一条经验：**"调度"本身几乎不花资源，"可靠地只执行一次"才是难点。** 生产上 90% 的调度事故都出在这里。
