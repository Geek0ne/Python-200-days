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

---

## 3. 原理深入

### 3.1 一次触发，内部到底发生了什么

从 `scheduler.start()` 到你的函数被调用，中间经过这些步骤：

```text
  1. 主循环（_process_jobs）每隔 wakeup_interval（默认 10s，可调）醒来
  2. 从 JobStore 取出所有 next_run_time 非空的任务
  3. 逐个比较 now >= next_run_time
  4. 命中的：检查 misfire_grace_time → 决定跳过还是执行
  5. 抢 max_instances 名额（用 job 自身的锁），抢不到就记 warning 跳过
  6. 交给 Executor（线程池 submit）
  7. Executor 线程里真正调用你的函数
  8. 回调：更新 last_run_time、算下一次 next_run_time、写回 JobStore
  9. 派发 EVENT_JOB_EXECUTED 或 EVENT_JOB_ERROR
```

**注意第 4 步在第 5 步之前**。也就是说：一个迟到的任务，**先**因为 misfire 被跳过，
才轮到 max_instances 判断。反过来，如果你两者都设成很宽容，
一个卡了 10 分钟的调度器醒来时可能一次性补跑一大批任务——这就是"惊群"。

### 3.2 `next_run_time` 是整个系统的中枢

调度器本身不记任何东西，它只是**反复地把 now 和 next_run_time 做比较**。
所以：

- 任务会不会跑，**只取决于** `next_run_time` 是不是过去时间
- 想手动触发一次 → 直接 `job.modify(next_run_time=datetime.now())`
- 想暂停 → `job.pause()`（把 `next_run_time` 置为 `None`）
- 想恢复 → `job.resume()`（重算下一次）
- 持久化 JobStore 存的就是 `next_run_time` + 整个 Job 的 pickle

**推论**：所有"任务没按预期跑"的故障，最终都要问一个问题——
**`next_run_time` 当时是什么值？** 这也是排错第一句话。

### 3.3 为什么 `coalesce` 和 `max_instances` 不是一回事

这两个词都跟"重复"有关，但管的是不同维度：

| | `max_instances` | `coalesce` |
|:---|:---|:---|
| 管的是 | **同时**能跑几个 | 积压的触发**怎么处理** |
| 默认 | 1 | True |
| 场景 | 上一轮还没结束 | 调度器卡了 10 分钟，期间积压 5 次 |
| 行为 | 第 2 个并发直接丢弃 | 5 次补跑 1 次（合并） |
| 类比 | 餐厅只有 1 张桌子 | 5 个人排队，只做 1 桌饭 |

一个任务慢导致**当前**多出来的触发，是 `max_instances` 管；
一个任务不慢但**调度器**卡住导致的历史积压，是 `coalesce` 管。
两个都默认开启，所以大多数时候你不会注意到它们。

### 3.4 持久化到底解决了什么，没解决什么

**解决了**：
- 进程重启后任务不丢
- 不用每次启动都重新注册（配合幂等注册后，代码里 `add_job` 可以放在启动流程）
- 多进程共享任务表（`next_run_time` 变成跨进程的协调点）

**没解决**：
- **停机期间的任务不会补跑**。因为 `next_run_time` 是被持久化的，
  停机 3 小时再起来，它还指着那 3 小时前的时间点——但那时已经"迟到"，
  落在 `misfire_grace_time` 之外就被跳过。
- **多实例不会自动互斥**。持久化只是让它们**看得到同一张表**，
  至于谁真的去跑，得靠 `next_run_time` 竞争（不安全）或显式加锁（安全）。

> 一句话：**持久化解决"记忆"，不解决"互斥"，也不解决"补偿"。**
> 后两件事必须你自己做。

---

## 4. 定义与使用方法（API 速查表）

### 4.1 `schedule` 常用调用

```python
import schedule, time

schedule.every(10).seconds.do(task)
schedule.every(10).minutes.do(task)
schedule.every().hour.do(task)
schedule.every().day.at("03:00").do(task)
schedule.every().monday.at("08:30").do(task)
schedule.every().wednesday.at("13:15").do(task)
schedule.every(10).seconds.do(task, arg1, kwarg=1)     # 带参数

# 修饰器写法
@schedule.every().day.at("03:00")
def nightly(): ...

# 主循环（必须你自己写）
while True:
    schedule.run_pending()
    time.sleep(1)

# 其他方法
schedule.clear(tag=None)          # 清空
schedule.next_run()               # 下一个任务的 datetime
schedule.idle_seconds()           # 距离下次触发还有几秒
```

### 4.2 `APScheduler` Scheduler

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Background：主线程继续干别的
sched = BackgroundScheduler(
    jobstores={"default": SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")},
    executors={"default": ThreadPoolExecutor(10)},
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
    timezone="Asia/Shanghai",
)
sched.start()
sched.pause()            # 暂停调度（不影响已注册任务）
sched.resume()
sched.shutdown(wait=True)   # 优雅关闭：等正在跑的任务结束
sched.get_jobs()
sched.get_job("id")
sched.remove_all_jobs()
```

### 4.3 `add_job` 常用参数

```python
sched.add_job(
    func,                    # 必须是模块顶层可导入的函数
    trigger,                 # "cron" / "interval" / "date" / 或 Trigger 对象
    args=(1, 2), kwargs={"k": 3},
    id="stable-id",          # 幂等注册的前提
    name="给人看的名字",
    replace_existing=True,   # 同 id 覆盖
    coalesce=True,
    max_instances=1,
    misfire_grace_time=60,   # 秒；None = 无限宽容
    next_run_time=datetime.now(),   # 手动指定首次触发
    timezone="Asia/Shanghai",
)
```

### 4.4 Trigger 对象

```python
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.combining import OrTrigger     # ⚠️ 别用 AndTrigger 拼 cron

# cron 常用字段
CronTrigger(hour=3, minute=0)                       # 每天 03:00
CronTrigger(day_of_week="mon-fri", hour="9-18")     # 工作日 9-18 点整
CronTrigger(day="last")                             # 每月最后一天
CronTrigger(month=1, day=1, hour=0)                 # 每年元旦

# interval
IntervalTrigger(seconds=30, start_date=datetime.now())  # start_date 建议显式给
IntervalTrigger(minutes=30)

# date（一次性）
DateTrigger(run_date=datetime(2026, 1, 1, 0, 0))

# 复合
OrTrigger([CronTrigger(day_of_week="sat"), CronTrigger(day_of_week="sun")])
```

### 4.5 JobStore

```python
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.jobstores.redis import RedisJobStore

SQLAlchemyJobStore(url="sqlite:///jobs.sqlite")
SQLAlchemyJobStore(url="postgresql+psycopg://u:p@h/db", tablename="my_jobs")
```

### 4.6 Executor

```python
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.executors.gevent import GeventExecutor

ThreadPoolExecutor(10)          # IO 密集
ProcessPoolExecutor(4)         # CPU 密集（参数必须可 pickle）
AsyncIOExecutor()              # 任务是 async 函数
```

### 4.7 事件监听

```python
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_EXECUTED

def on_error(event):
    print(f"任务 {event.job_id} 失败：{event.exception}")

sched.add_listener(on_error, EVENT_JOB_ERROR)
sched.add_listener(lambda e: print(e.job_id), EVENT_JOB_EXECUTED)
```

---

## 5. 图解

完整的 11 张图（ASCII + Mermaid）在 `diagrams/README.md`，包括：
调度器四件套数据流、三个防重复参数的时间轴对照、`AndTrigger` 死循环推演、
多实例重复执行的三种解法、备份任务时序图、锁 TTL 的必要性。

---

## 6. 常见陷阱 Top 11

### 陷阱 1：`get_next_fire_time(None, now)` 原地打转

```python
# ❌ previous 一直传 None → now 命中 cron 时返回 now 本身，永远不推进
c = base
for _ in range(3):
    c = trig.get_next_fire_time(None, c)   # 三次都是同一个时间

# ✅ 把上一次结果传回去
prev, now = None, base
for _ in range(3):
    nxt = trig.get_next_fire_time(prev, now)
    prev = now = nxt
```

**症状**：写"推算未来几次触发时间"的工具时，死循环或输出全一样。
**实测**：见 `02-pitfalls.py` 坑 ①。

### 陷阱 2：naive vs aware datetime 直接 TypeError

```python
# ❌
IntervalTrigger(minutes=30).get_next_fire_time(None, datetime(2026, 1, 5, 2, 30))
# TypeError: can't compare offset-naive and offset-aware datetimes

# ✅ 调度器返回的时间带 tzinfo，基准点也要带
base = datetime(2026, 1, 5, 2, 30, tzinfo=datetime.now().astimezone().tzinfo)
```

**根因**：`IntervalTrigger` 内部拿 `start_date`（默认是带时区的"现在"）
和 `now` 比较。**症状**：写测试时莫名 TypeError，但手动跑又没事。

### 陷阱 3：`IntervalTrigger` 不给 `start_date` 就不可预测

```python
# ❌ 默认 start_date =「此刻 + interval」，跟你的基准点无关
IntervalTrigger(minutes=30).start_date   # → 2026-09-29 16:33（真实现在）

# ✅ 显式指定
IntervalTrigger(minutes=30, start_date=base)
```

**症状**：单元测试里"下次运行是 30 分钟后"这种断言永远写不稳。

### 陷阱 4：`max_instances=1` 是丢弃，不是排队

```python
sched.add_job(slow_job, "interval", seconds=1, max_instances=1)
# slow_job 要跑 1.5 秒
```

**症状**：日志出现 `Execution of job ... skipped: maximum number of running
instances reached (1)`，任务"明明该跑却没跑"。
**要点**：默认 1，且是**丢弃**。要排队得显式调大。
**实测**：见 `03-advanced-scheduler.py` 的 max_instances 用例（3.2 秒内只跑 1 次）。

### 陷阱 5：`misfire_grace_time` 决定了"错过"和"补跑"的分界

```python
job_defaults={"misfire_grace_time": 1}
sched.add_job(f, "interval", seconds=10,
              next_run_time=datetime.now() - timedelta(seconds=5))
# → 迟到 5 秒 > 容忍 1 秒 → 直接跳过，不补跑
```

**要点**：`None` = 来者不拒（但会把积压全补一遍）；`0` = 严格准点。
**别指望调度器帮你补跑**——需要"一天都不能少"的任务，
正确做法是任务自己记录 `last_success` 并在醒来时检查缺口（拉取式）。

### 陷阱 6：`job_state` 是 pickle → 函数必须模块顶层

```python
# ❌ 重启后反序列化直接炸
def main():
    sched.add_job(lambda: backup(), ...)   # pickle.dumps 就已经报错了
    def local(): ...
    sched.add_job(local, ...)
```

**症状**：配置了持久化 JobStore，重启后任务消失或 `ModuleNotFoundError`。
**正解**：把任务函数提到模块顶层。

### 陷阱 7：`add_job` 不给 id + 持久化 → 重启 N 次注册 N 遍

```python
# ❌ 无 id：内存里 5 个任务；配上持久化后重启几次就是几个任务
sched.add_job(backup, "cron", hour=3)

# ✅ 稳定 id + replace_existing=True = 幂等注册
sched.add_job(backup, "cron", hour=3, id="daily-backup", replace_existing=True)
```

**症状**：每天凌晨备份跑了 5 遍，邮件发 5 封。
**实测**：`02-pitfalls.py` 坑 ⑦ / `03-advanced-scheduler.py` 持久化用例。

### 陷阱 8：`schedule` 只有一个线程，一个慢任务堵死全部

```python
sched.every(0.1).seconds.do(slow)   # 睡 0.6s
sched.every(0.1).seconds.do(fast)
# 实际顺序：slow → fast（快的被堵在慢的后面）
```

**要点**：`schedule` 无并发。`run_pending()` 串行执行所有到期任务。

### 陷阱 9：多实例部署 → 同一任务跑 N 遍

**症状**：备份出现多份、告警发多条、写入互相覆盖。
**三种解法**（详见 2.6）：单实例 / 分布式锁 / 外部编排。

### 陷阱 10：任务抛异常被静默吞掉

```python
sched.add_job(always_fails, "interval", seconds=1)
# 不抛到你的主线程，只写 APScheduler 内部日志
# 而且任务**依然留在表里**，会一直静默地失败下去
```

**正解**：
```python
sched.add_listener(lambda e: alert(e.job_id, e.exception), EVENT_JOB_ERROR)
```

### 陷阱 11（本日最坑）：`AndTrigger` 拼两个 cron → 调度器死循环

```python
# ❌ 会把整个调度器卡死，CPU 100%，其他任务全部不再执行
AndTrigger([CronTrigger(day_of_week="mon-fri"), CronTrigger(hour=9)])
```

**根因**：官方实现是 `while True`，要求各子触发器产出**完全相同**的时间戳
才返回。而 cron 永远不会对齐（一个给 00:00、一个给 09:00）→ 永不收敛。
官方 docstring 其实警告了（说混 `IntervalTrigger` 会挂起调度器）。

**正解**：条件过滤写进**同一个** cron 表达式：
```python
CronTrigger(day_of_week="mon-fri", hour=9)   # 安全，一次返回
```

> ⚠️ 编写这一课时我就是先写了 `AndTrigger` 版本，self-test 跑到这一步直接
> 卡死，进程占满一个核停不下来。最后用 `faulthandler.dump_traceback_later`
> 打出栈才发现是 `combining.py` 的 `while True`。所以 `03` 里**故意不导入**
> `AndTrigger`，只留注释警告——避免有人照抄。

---

## 7. 实战项目：定时备份系统

需求（`code/04-backup-scheduler.py` 的完整实现）：

> 每天 03:00 打包 `data/`，保留最近 7 天，校验失败要立刻知道，
> 多实例部署下只跑一次。

**备份 → 校验 → 保留 → 报告** 四步，每步都要考虑"失败了怎么办"：

| 步骤 | 做法 | 关键决策 |
|:---|:---|:---|
| **互斥** | SQLite 行锁 `job_lock`，带 TTL | 多实例只跑一次；TTL 防死锁 |
| **幂等** | `backup_log` 表记 `day`，当天已成功就跳过 | 挡跨时间的重复 |
| **备份** | `tarfile` 打包，`%Y%m%d-%H%M%S` 命名 | 同名时加序号防覆盖 |
| **校验** | 立刻解包，算 sha256 + 数文件 | 失败当场删掉坏包，不冒充成功 |
| **落账** | 写 `backup_log` | 记录 size/sha256/文件数/耗时 |
| **保留** | 按文件名日期删超期的 | 解析失败要报错不能静默 |
| **报告** | `render_report` 输出可读摘要 | 失败必须被看见 |

**运行**：
```bash
python3 04-backup-scheduler.py --self-test     # 33 项断言
python3 04-backup-scheduler.py --dry-run       # 走完整流程
python3 04-backup-scheduler.py --selftest-job  # 每 2s 真实触发
python3 04-backup-scheduler.py --register      # 真正注册 cron(03:00)
```

**开发过程中抓到的 3 个真 bug**（都写进了代码注释和陷阱节）：

1. **同秒运行静默覆盖** —— 时间戳只到秒，`run(force=True)` 在同一秒内
   再跑会算出完全相同的文件名，把上一个归档覆盖掉，"成功两次最后剩一个包"。
2. **`prune()` 从来没删过任何文件** —— 把 `backup-20260929-161234` 整体
   用 `%Y%m%d` 解析必然 `ValueError`，而这个异常被 `except: continue` 吞掉，
   于是保留策略形同虚设且**没有任何报错**。
3. **`AndTrigger` 死循环** —— 见陷阱 11。

> 这三个 bug 的共同点：**都是"看起来成功、实际没做事"**。
> 这正是定时任务最危险的地方——它不崩，它只是悄悄地不工作。

---

## 8. 思考题

1. **为什么 cron 不会漂移而 `sleep` 会？** 从"计算下一次触发的绝对时刻"
   vs "睡 N 秒"这个区别解释，并说明为什么"对齐到网格"在多任务场景尤其重要。

2. **`coalesce=True` 和"任务幂等"是同一件事吗？** 如果你的任务是"每天给
   1000 个用户各发一封邮件"（不可重复），coalesce 够吗？还需要什么？

3. **多实例部署下，为什么"用 `next_run_time` 竞争"是不安全的？**
   两个进程同时读到"该跑了"，会同时执行——这个 TOCTOU 竞态怎么破？

4. **假设你的任务要"每分钟检查一次，发现过期就清理"**，为什么这比
   "每天凌晨清理一次"更健壮？反过来，什么场景下"每天一次"反而更好？

5. **设计一个"绝不重复扣款"的定时任务。** 从幂等键、事务边界、
   唯一索引三个角度给出方案，并说明为什么光靠"加锁"不够。

6. **心跳 `activeHours` 配错（窗口写反），会在任务面板留下一堆 `failed`
   噪音记录。** 想想为什么系统把"静默跳过"记成"失败"而不是"跳过"，
   以及这个设计对监控告警意味着什么。

---

## 9. 小结

```text
  一句话记住定时任务：
    调度本身不花资源，"可靠地只执行一次"才是难点。

  五条铁律：
    ① 别用 while True + sleep（有漂移、有丢失、不能并发）
    ② add_job 一律给稳定 id + replace_existing=True（幂等注册）
    ③ 持久化 JobStore → 函数必须模块顶层（pickle 要求）
    ④ 任务失败要接 EVENT_JOB_ERROR，否则它会静默失败到天荒地老
    ⑤ 多实例必加互斥，且锁要带 TTL（否则会永久静默失效）

  三个参数的分工：
    max_instances     管"同时"跑几个（默认 1，超了丢弃）
    coalesce          管积压几次合并成几次（默认 True）
    misfire_grace_time 管迟到多久还算数（默认无，即严格准点）

  最危险的三种"假成功"：
    · AndTrigger 死循环 → 调度器卡死
    · 保留策略解析失败被吞 → 永远不清理
    · 任务抛异常无人监听 → 一直失败但没人知道
```

> 下一课 Day 171：**消息队列** —— 解耦、削峰、可靠投递的三种姿势，
> 以及"消费幂等"这个和今天一脉相承的话题。
