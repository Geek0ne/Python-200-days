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

## 3. 原理解析

### 3.1 Linux inotify 到底做了什么

inotify 是内核提供的一套**文件系统事件通知接口**，用户态通过三个系统调用使用它：

```text
inotify_init1()          创建一个 inotify 实例 → 返回一个 fd
inotify_add_watch(fd, path, mask)   给某个 path 注册监听 → 返回 wd (watch descriptor)
read(fd, buf, len)       阻塞读，内核把事件结构体塞进这个 fd
```

关键点，逐条说清：

1. **watch 挂在"inode/目录项"上，不是挂在路径字符串上**。
   你 `add_watch("/data")` 之后把 `/data` 改名成 `/data2`，
   watch **仍然有效**（wd 不变），但事件里的路径是内核按当前 dentry 拼出来的，可能已经变成 `/data2/...`。
   → **陷阱**：日志里打印的路径和你注册时的路径可能不一致。

2. **`recursive=True` 不是内核特性，是 watchdog 自己走出来的**。
   内核的 inotify **不支持递归**。watchdog 在 `schedule(recursive=True)` 时会：
   - 对目标目录本身 `add_watch`
   - **遍历所有子目录**，每个目录**再 `add_watch` 一次**
   - 当收到 `IN_CREATE` 且 `is_directory=True` 时，**再给新目录补一个 watch**

   → **陷阱**：这个"补 watch"动作在 watchdog 里是**异步**的（走 emitter 内部队列）。
   在目录刚创建、文件已经写进去的**极短窗口**内，可能漏掉文件事件。
   → 于是就有了"新建目录然后立刻 cp 一堆文件进去，结果只收到目录 created"的经典 bug。

3. **每个 watch 消耗一份内核配额**。
   检查与调整：

   ```bash
   cat /proc/sys/fs/inotify/max_user_watches    # 默认常见 8192 / 65536 / 524288
   cat /proc/sys/fs/inotify/max_user_instances  # 默认 128，Observer 数量受它限制
   cat /proc/sys/fs/inotify/max_queued_events   # 默认 16384
   ```

   监控一个 `node_modules`（20 万目录）会直接 `OSError: inotify watch limit reached`。
   → **这不是 watchdog 的锅，是内核配额**。要么调大，要么**别递归监控这种东西**（加 ignore）。

4. **事件队列有限，会溢出**。内核把事件放进与 fd 关联的队列，容量 = `max_queued_events`。
   你的进程读得不够快 → 队列满 → 内核**丢弃事件**并投递一个特殊的 `IN_Q_OVERFLOW`。
   watchdog 会把它转成 `event.event_type == 'closed_no_write'` 之类不常见形态，
   **更常见的是你压根不知道丢了事件**。

### 3.2 watchdog 的线程模型

```text
主线程
 │
 ├── Observer.start()
 │       │
 │       ├── 线程 A: Emitter（真实实现是 InotifyEmitter，内含 select/poll）
 │       │       │  阻塞 read(inotify_fd) → 解析 inotify_event → 转成 FileSystemEvent
 │       │       └→ 放入 event_queue (queue.Queue)
 │       │
 │       └── 线程 B: dispatch 线程
 │               └→ queue.get() → 遍历所有已注册 handler → 调用你的 on_xxx()
 │
 └── observer.join()  ← 等线程结束
```

**由此推出三条实战结论**：

- **你的 handler 跑在 Observer 的 dispatch 线程里**。handler 一慢，
  整个 observer 的事件消费就慢 → 队列堆积 → 溢出丢事件。
  **handler 里不要做重活**（转码、上传、大文件解析）→ 丢给 `queue.Queue` 或线程池。
- **Observer 线程默认是 `daemon=True`**？不是。watchdog 的 Observer 是**非守护线程**，
  你自己不 `stop()`，程序**不会退出**（Ctrl+C 都可能卡住）。
  所以 `finally: observer.stop(); observer.join()` 是**必写**的。
- **一个 Observer 可以 schedule 多个 path / 多个 handler**，
  事件会分发给**所有匹配的 handler**（不是就近匹配），别指望"handler 只收自己目录的"。

### 3.3 轮询背后的 Emitter：`PollingObserver`

watchdog 还提供一个 **`watchdog.observers.polling.PollingObserver`**，
它**不用 inotify**，而是"扫目录 + 比 mtime/size"。

**什么时候必须用它**：

- 监控 NFS / SMB / CIFS 挂载（远端内核 != 本机内核）
- 监控 Docker bind mount 且宿主改动
- 容器里 `inotify` 被 seccomp 限制

代价：`PollingObserver(timeout=1)` 就是**每秒全树扫描一次**。
默认 `timeout` 是 **1 秒**，大目录树上会非常耗 IO —— 必须显式调大（如 `timeout=5`）。

### 3.4 为什么 vim 保存一个文件会产生 3~6 条事件

因为现代编辑器普遍用 **原子写（atomic write）**：

```text
vim 保存 a.txt 的实际动作：
  1. write  a.txt.swp / a.txt.tmp       → IN_CREATE  a.txt.tmp
  2. write  内容到 tmp                  → IN_MODIFY  a.txt.tmp
  3. close(tmp)                        → IN_CLOSE_WRITE a.txt.tmp
  4. rename(a.txt.tmp → a.txt)          → IN_MOVED_FROM a.txt.tmp + IN_MOVED_TO a.txt
  5. 可能还要 chmod / 更新备份           → IN_ATTRIB
```

于是你的 handler 会收到：

```text
created  /dir/a.txt.tmp
modified /dir/a.txt.tmp
closed   /dir/a.txt.tmp
moved    /dir/a.txt.tmp → /dir/a.txt     ← 注意：watchdog 用 FileMovedEvent 表示
```

**为什么编辑器要这么做**：rename 在 POSIX 上是**原子**的。
如果直接覆盖写原文件，另一个正在读的进程可能读到**写了一半的内容**；
rename 则保证"要么旧文件、要么新文件"，永远不会读到半成品。
**编辑器是对的，我们的监控代码必须适配它。**

→ 由此引出两个设计：

- **`.tmp` / `.swp` / `~` / `#...#` 结尾的文件必须默认忽略**，否则你会处理一堆垃圾。
- **必须做防抖**：同一个 `dest_path` 在 T 毫秒内的重复事件合并成一次业务动作。

### 3.5 防抖（debounce）与节流（throttle）

| 策略 | 行为 | 适合 |
|:---|:---|:---|
| **防抖 debounce** | 事件持续到来 → **一直推迟**，直到**静默 T 毫秒**后才执行一次 | "写完了再处理" |
| **节流 throttle** | 每 T 毫秒**最多**执行一次 | "边写边采样" |

文件场景几乎总是**防抖**：因为你要的是"写入结束"这个时刻。

一个最小的防抖实现（`code/03-advanced-watch.py` 里用的就是这个思路）：

```python
import threading, time

class Debouncer:
    def __init__(self, delay, action):
        self.delay = delay
        self.action = action
        self.timers = {}            # key -> threading.Timer
        self.lock = threading.Lock()

    def trigger(self, key, *args):
        with self.lock:
            old = self.timers.pop(key, None)
            if old:
                old.cancel()        # 取消上一次未触发的动作
            t = threading.Timer(self.delay, self._fire, args=(key, args))
            t.daemon = True
            self.timers[key] = t
            t.start()

    def _fire(self, key, args):
        with self.lock:
            self.timers.pop(key, None)
        self.action(key, *args)
```

**三个必须注意的点**：

1. **`Timer.cancel()` 只在定时器还没触发时有效**，已经触发的取消不掉 → 所以 `_fire` 要先把自己从字典里摘掉。
2. **`timers` 字典要被多线程访问**（dispatch 线程 trigger、Timer 线程 fire）→ 必须加锁，
   否则会出现"两个动作同时跑"或字典 size 变化异常。
3. **防抖键（key）要用绝对路径**，否则 `./a.txt` 和 `/data/a.txt` 会被当成两个文件。

### 3.6 文件自动分类的思路

"文件自动分类"不是 watchdog 的功能，而是**你在 handler 里写的业务规则**。
一个靠谱的分类器要回答四个问题：

```text
   ① 匹配规则是什么？        扩展名 / MIME / 文件名正则 / 内容嗅探
   ② 冲突怎么办？            同扩展名多规则 → 优先级 / 先匹配先赢
   ③ 目标是哪里？            目标目录不存在自动建？跨设备移动会退化成复制
   ④ 可逆吗？                要不要写操作日志，方便撤销
```

扩展名匹配的**坑**：`.tar.gz` 用 `endswith('.gz')` 会被归到"压缩包-gz"，
但你其实想要"tar.gz"。→ **规则要按扩展名长度倒序匹配**（长的优先）。
另外一个常见的错误：用 `os.rename` 跨文件系统移动会抛 `OSError: [Errno 18] Invalid cross-device link`，
必须 `shutil.move`（它内部会退回 copy+unlink）。

---

## 4. 定义与使用方法（API 速查表）

### 4.1 观察者 Observer

| 类 | 导入 | 说明 |
|:---|:---|:---|
| `Observer` | `from watchdog.observers import Observer` | 自动选平台后端 |
| `PollingObserver` | `from watchdog.observers.polling import PollingObserver` | 纯轮询，跨网络盘必用 |
| `InotifyObserver` | `from watchdog.observers.inotify import InotifyObserver` | 强制 Linux 后端 |

| 方法 | 签名 | 说明 |
|:---|:---|:---|
| `schedule` | `schedule(handler, path, recursive=False, event_filter=None)` | 注册；`path` 必须是**已存在**的目录，否则抛 `OSError` |
| `start` | `start()` | 起线程，返回 `self` |
| `stop` | `stop()` | 通知线程退出（**不阻塞**） |
| `join` | `join(timeout=None)` | **阻塞**等线程结束；收尾必调 |
| `unschedule` | `unschedule(watch)` | 取消某个 watch（需保存 schedule 的返回值） |
| `unschedule_all` | `unschedule_all()` | 取消全部 |
| `add_handler_for_watch` | `add_handler_for_watch(handler, watch)` | 给已存在的 watch 加 handler |

> `schedule()` 的返回值是 `ObservedWatch`，`watch.path` / `watch.is_recursive` 可取。
> **保存它**，否则运行时想关掉某些目录只能全关。

### 4.2 事件对象 FileSystemEvent

所有事件都有的属性：

| 属性 | 类型 | 说明 |
|:---|:---|:---|
| `event_type` | `str` | `'created'` / `'deleted'` / `'modified'` / `'moved'` / `'closed'` |
| `src_path` | `str` | 事件主体路径（**绝对路径**，watchdog 已 normalize） |
| `dest_path` | `str` | 仅 `moved` 事件有；其余是 `''` |
| `is_directory` | `bool` | 目录事件为 `True` |
| `is_synthetic` | `bool` | 是否为合成事件（`on_any_event` 的兜底/文件关闭合成） |
| `event_type` 载体类 | `FileCreatedEvent` / `DirModifiedEvent` / `FileMovedEvent` … | 想 `isinstance` 判断时用 |

速查：**哪些事件有 `dest_path`** → 只有 `moved` 有。

### 4.3 处理器回调

| 回调 | 触发时机 | 备注 |
|:---|:---|:---|
| `on_any_event(event)` | **所有**事件，**先于**具体回调 | 统一日志/统计挂这里 |
| `on_created(event)` | 新建 | 目录新建也走这里（`is_directory=True`） |
| `on_deleted(event)` | 删除 | 删除时 `src_path` 可能已不存在 |
| `on_modified(event)` | 内容修改 | **目录的 modified 也会来**（子项增删导致 mtime 变） |
| `on_moved(event)` | 重命名/移动 | 有 `dest_path` |
| `on_closed(event)` | 句柄关闭 | 仅 inotify；用它判断"写完了"比防抖更精确 |

**经验法则**：判断"文件写完了"有两种思路 ——
`on_closed`（精确，但平台相关）或 **debounce**（通用，但要多等 T 毫秒）。
**生产代码建议 debounce 为主、on_closed 为辅**。

### 4.4 常用配套 API

| 需求 | API |
|:---|:---|
| 递归遍历目录 | `os.walk(path)` / `pathlib.Path.rglob('*')` |
| 读一行式路径匹配 | `fnmatch.fnmatch(name, '*.log')` |
| 正则匹配 | `re.fullmatch(pattern, name)` |
| 拿到最后修改时间 | `os.path.getmtime(p)` / `Path(p).stat().st_mtime` |
| 安全移动（跨设备） | `shutil.move(src, dst)` |
| 唯一化重名 | `Path(dst).with_stem(name + '_' + ts)` |
| 临时目录 | `tempfile.mkdtemp(prefix='wm-')` |
| 立即让 stdout 可见 | `print(..., flush=True)` 或 `python3 -u` |

### 4.5 一个可复制的"防抖处理器"模板

```python
class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, delay=0.5, ignore=('.tmp', '.swp', '~')):
        self.deb = Debouncer(delay, self.on_settled)
        self.ignore = ignore

    def _skip(self, p):
        name = os.path.basename(p)
        return not name or any(name.endswith(s) for s in self.ignore) \
               or '/__pycache__/' in p or name.startswith('.')

    def on_any_event(self, event):
        if event.is_directory or self._skip(event.src_path):
            return
        key = os.path.abspath(event.dest_path or event.src_path)
        self.deb.trigger(key, event.event_type)

    def on_settled(self, path, last_event_type):
        # 到这一步说明该文件已静默 delay 秒，可以安全处理了
        print(f"[settled] {last_event_type:9s} {path}")
```

---
