# Day 167 — 文件监控（watchdog）

> **Phase 11 — 自动化运维与 DevOps（Day 166–185）** · 主题：文件监控 · 子主题：实战
>
> **安全与边界声明**：
> - 本课所有代码只在**你自己的目录**里创建/删除/移动文件，监控范围由 `--path` 显式指定。
> - **绝不**建议、也不演示对 `/`、`/etc`、`/usr` 等系统目录做递归监控（会吃掉 inotify 配额）。
> - 演示文件一律写在 `./sandbox/` 或 `tempfile.mkdtemp()` 生成的临时目录里，脚本结束自动清理。
> - 想在生产机上用，请先用 `--dry-run` 与 `--duration 10` 小范围试跑。

---

## 1. 学习目标

完成本课后，你应该能够：

- 说清 **轮询（polling）** 与 **事件驱动（event-driven）** 两种文件监控路线的本质差别、各自代价与适用边界
- 解释 Linux **inotify** 的工作模型（watch descriptor、事件队列、`IN_Q_OVERFLOW`），并说清"递归监控"在底层到底做了什么
- 说清 watchdog 的三件套 **Observer / EventHandler / FileSystemEvent** 各自负责什么，以及它们跑在哪个线程里
- 准确区分 `created` / `deleted` / `modified` / `moved` / `closed` 五类事件，并知道**哪几类事件永远不会单独出现**
- 解释为什么用 vim / VSCode 保存一个文件，会一次性产生 **3~6 条** 事件，以及如何用 **防抖（debounce）** 收敛
- 说清 **原子写（write temp + rename）** 为什么会让 `moved` 事件看起来"凭空多出来一个文件"
- 说清 watchdog 的**三个经典陷阱**：递归监控后新建子目录不触发、handler 里抛异常导致监听静默失效、事件队列溢出丢事件
- 能独立写出一个 **带防抖、支持规则匹配、可输出 JSON 报告** 的文件变化监控/自动分类工具

---

## 2. 概念解释

### 2.1 文件监控解决什么问题

先想清楚"为什么要监控文件"，而不是先想 API：

```text
        ┌──────────────── 文件监控的典型用途 ────────────────┐
        │                                                   │
   ①  自动化触发        ②  数据管道          ③  安全审计
   有新文件就处理       目录即队列          谁动了我的配置
   (上传→转码/入库)     (落地→解析→归档)    (篡改/删除留痕)
        │                     │                    │
        └─────────────────────┴────────────────────┘
                   共同点：**不能靠人盯着**
```

三种用途都指向同一个需求：**在文件系统发生变化的那一瞬间，被通知到**。
差别只在于对**延迟**和**可靠性**的要求不同：

| 用途 | 可接受延迟 | 关键要求 |
|:---|:---|:---|
| 上传即处理 | 秒级 | 必须拿到**完整的**文件（写入结束才处理） |
| 数据管道 | 亚秒级 | 不能丢事件，顺序要大致正确 |
| 安全审计 | 毫秒级 | 不能漏，尤其是 `deleted` / `moved` |

### 2.2 两条路线：轮询 vs 事件驱动

**轮询（polling）**：每隔 N 秒扫描一次目录，和上次的快照对比，算出"变了什么"。

```text
t=0s   扫描 → {a.py, b.py}           快照 S0
t=5s   扫描 → {a.py, b.py, c.py}     快照 S1  → diff: +c.py
t=10s  扫描 → {a.py}                 快照 S2  → diff: -b.py, -c.py
```

优点：**跨平台、实现简单、不需要任何权限**（只要有读目录权限）。
缺点：**延迟 = 轮询间隔**，且**间隔内"创建又删除"的文件永远看不到**（漏事件）；
扫描大目录树本身要花 CPU 和 IO（100 万文件 × 每 5 秒 = 磁盘被你和自己打爆）。

**事件驱动（event-driven）**：把目录注册给内核，内核在变化发生时**主动通知**你。

```text
注册: 内核(IN_CREATE 监听 /data)
        │
        │  某个进程 write("/data/x.csv")
        ▼
内核 → [ IN_CREATE x.csv ] → 你的进程（阻塞的 read() 被唤醒）
```

优点：**零轮询开销**（空闲时完全不吃 CPU），**延迟毫秒级**，**不漏事件**。
缺点：**依赖操作系统能力**，各平台实现完全不同：

| 平台 | 机制 | 精度 |
|:---|:---|:---|
| Linux | **inotify** | 最细，能区分 create/delete/modify/attrib |
| macOS | **FSEvents** | 目录级粗粒度，自带合并，"延迟投递" |
| Windows | **ReadDirectoryChangesW** | 类似 inotify，但缓冲区是**每次调用**传的 |
| 网络盘 (NFS/SMB) | ❌ 通常不支持 | 远端内核看不到你的 watch，只能轮询 |

**这就是 watchdog 存在的理由**：它把上面 4 套 API 抽象成**同一套 Python 事件模型**，
你写 `observer.schedule(handler, path, recursive=True)` 就能跨平台跑。

> ⚠️ **新手最容易犯的错**：在 Docker 容器里监控**宿主机 bind mount 进来的目录**。
> 宿主机上别人改文件，容器里的 inotify **收不到**（事件是在宿主机内核里产生的，
> 但 masquerade 了的 mount 有时不转发）。这种场景只能轮询。

### 2.3 watchdog 三件套

watchdog 的 API 只有三个核心角色，先记住这张表，后面全部代码都是它的组合：

| 角色 | 类 | 职责 | 关键点 |
|:---|:---|:---|:---|
| **观察者** | `Observer` | 起一个后台线程，把内核事件读出来、投递出去 | 一个 Observer 可以调度**多个** watch |
| **处理器** | `FileSystemEventHandler` | 收到事件后**你要做什么** | 每个回调在 Observer 线程里执行 |
| **事件** | `FileSystemEvent` | 一次变化的**不可变描述** | 有 `src_path` / `dest_path` / `is_directory` / `event_type` |

最小骨架（这就是本课 `code/01-basic-watch.py` 的核心）：

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MyHandler(FileSystemEventHandler):
    def on_created(self, event):
        print("created:", event.src_path)

observer = Observer()
observer.schedule(MyHandler(), path="/data", recursive=True)
observer.start()          # 起后台线程
try:
    while True:
        time.sleep(1)     # 主线程干别的（或 join）
finally:
    observer.stop()
    observer.join()       # 必须 join，否则可能丢最后一波事件
```

四个回调名分别是 `on_created` / `on_deleted` / `on_modified` / `on_moved`，
另外还有一个"全量入口" `on_any_event(event)`（**它先于具体回调被调用**，适合统一日志）。

### 2.4 五类事件与它们的"组合关系"

watchdog 定义的事件类型（`event.event_type` 字符串）：

| event_type | 触发条件 | 载体类 | 有 `dest_path` 吗 |
|:---|:---|:---|:---|
| `created` | 新建文件/目录 | `FileCreatedEvent` / `DirCreatedEvent` | ❌ |
| `deleted` | 删除文件/目录 | `FileDeletedEvent` / `DirDeletedEvent` | ❌ |
| `modified` | 内容被写入（**不带元数据变更**） | `FileModifiedEvent` | ❌ |
| `moved` | 重命名 / 移动 | `FileMovedEvent` / `DirMovedEvent` | ✅ |
| `closed` | 文件句柄关闭（仅 inotify 支持） | `FileClosedEvent` | ❌ |

**关键认知**：这些事件**不是互斥的"状态"，而是内核视角的"动作流水"**。
你脑海里想的是"文件从 A 变成 B"（状态差），内核给你的是一串动作：

```text
你的心智模型：            a.txt 内容变了
内核实际给你的流水：      MODIFY a.txt
                         MODIFY a.txt
                         CLOSE_WRITE a.txt
```

所以**永远不要去"猜"事件的含义，要去"聚合"事件**。这就是下一节要讲的防抖。

---
