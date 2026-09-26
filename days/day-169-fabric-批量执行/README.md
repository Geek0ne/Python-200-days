# Day 169 — Fabric 批量执行

> **一句话定义**：Fabric = **Invoke（任务/CLI 层）** + **Paramiko（SSH 层）**。
> 它把你昨天手写的"连接池 + 线程池 + 审计"换成了几个声明式原语，
> 代价是你必须接受它的**抽象边界**（尤其：它不提供幂等）。

本课从"Fabric 到底帮你做了什么"讲到"如何写出一份能回滚的部署脚本"。

---

## 1. 学习目标

学完本课，你应该能够：

- [ ] 说清 Fabric 的三层结构（`@task` / `Connection` / `Group`）与它和 paramiko 的关系
- [ ] 用 `Connection.run()` / `sudo()` / `put()` / `get()` 完成一次单机交互
- [ ] 用 `ThreadingGroup` / `SerialGroup` 做多机批量执行，并正确处理 `GroupException`
- [ ] 解释 `warn` / `hide` / `echo` / `pty` 四个参数各自的语义与误用后果
- [ ] 写出"release 目录 + 软链切换 + 上一版保留"的可回滚部署脚本
- [ ] 说清 Fabric **不提供**什么（幂等、状态管理、依赖图），以及什么时候该换 Ansible

---

## 2. 概念解释

### 2.1 Fabric 是什么：先把两层拆开

```text
┌───────────────────────────────────────────────────────────────┐
│  Invoke（任务与 CLI 层）                                        │
│    @task 装饰的函数 → 自动变成命令行子命令                        │
│    fab deploy --env=prod                                      │
│    处理：参数解析、任务依赖、环境变量（Context）、交互式提示        │
├───────────────────────────────────────────────────────────────┤
│  Fabric（SSH 层，本站重点）                                     │
│    Connection  —— 一台机器的一次会话                             │
│    Group       —— 多台机器的集合（Threading / Serial）            │
│    处理：run/sudo/put/get、认证、跳板机、结果对象                   │
├───────────────────────────────────────────────────────────────┤
│  Paramiko（协议层，Day 168 学过）                               │
│    Transport / Channel / SFTPClient                           │
└───────────────────────────────────────────────────────────────┘
```

**为什么这个分层很重要**：当 Fabric 的行为让你困惑时，先判断"这是 Invoke 的问题、
Fabric 的问题，还是 Paramiko 的问题"。绝大多数诡异的"卡住"，根因都在最底下那层
（TCP/认证/超时），而 Fabric 只是没帮你设好超时。

### 2.2 `Connection`：一台机器的一切动作都收进一个对象

```python
from fabric import Connection

c = Connection("web-01", user="deploy", port=22,
               connect_kwargs={"key_filename": "~/.ssh/id_ed25519"})

r = c.run("uname -a")          # 执行命令，返回 Result
print(r.stdout.strip())        # Result 是"已执行完的快照"，不是流
c.put("app.tar.gz", "/tmp/app.tar.gz")
c.sudo("systemctl restart nginx")
```

**三个关键点**：

| 点 | 说明 |
|:---|:---|
| `Connection` 复用一条 SSH 连接 | 同一个 `c` 上的多次 `run` 复用 Transport（和 Day 168 的池是一样的道理） |
| `run` 默认**非惰性** | 调用即执行、立即返回 `Result`，异常会立刻抛（除非 `warn=True`） |
| `connect_kwargs` 透传给 paramiko | 所以 `timeout`、`banner_timeout`、`auth_timeout` 都在这里设 |

### 2.3 `Result`：一次执行的完整快照

```python
from invoke.runners import Result

r = c.run("cat /etc/hostname")
r.command        # 'cat /etc/hostname'
r.stdout         # 'web-01\n'
r.stderr         # ''
r.return_code    # 0
r.ok             # True   （return_code == 0）
r.failed         # False
r.exited         # True   （进程已退出）
```

**为什么要看 `ok` 而不是 `return_code == 0`**：
`ok` 是 `return_code == 0` 的语义化别名；而 `exited` 在"被信号杀死"时为 `True`
但 `return_code` 可能是 `-1`。用 `ok`/`failed` 表达意图，用 `return_code` 做精细判断。

### 2.4 `Group`：多机原语

```python
from fabric import ThreadingGroup, SerialGroup

web = ThreadingGroup("web-01", "web-02", "web-03",
                     user="deploy", connect_kwargs={...})

results = web.run("uptime")        # dict: {host_str: Result}
for host, r in results.items():
    print(host, r.ok, r.stdout.strip())
```

| 类 | 执行方式 | 适用场景 |
|:---|:---|:---|
| `ThreadingGroup` | 全部并发（每台一个线程） | 只读巡检、采集信息：快 |
| `SerialGroup` | 顺序执行，一台一台来 | 变更操作、滚动重启：安全（有问题立即停） |

**关键区别（也是本课最重要的一条实践）**：

```text
巡检 / 采集 / 查状态   → ThreadingGroup（并发，越快越好，失败无所谓）
变更 / 部署 / 重启     → SerialGroup   （串行，一台失败立刻停，别把集群一起打挂）
```

**为什么**：并发变更一旦打到一半失败，你的集群会处于"一半新一半旧"的中间态，
而且很难判断停在哪。串行变更的失败是"清晰可判定"的。

### 2.5 `GroupException`：并行失败的聚合

```python
from fabric.exceptions import GroupException

try:
    ThreadingGroup("a", "b", "c").run("false")
except GroupException as exc:
    # exc.result 是 dict: {host_str: Exception}
    for host, err in exc.result.items():
        print(host, type(err).__name__, err)
```

**为什么需要它**：并发时"部分失败"是常态，但 Python 的异常模型只能抛一个。
Fabric 的解法是"抛一个装着所有失败的容器异常"。你必须显式遍历它，
否则会丢掉"另外两台成功/失败的信息"。

### 2.6 `sudo` 与 pty：为什么它要密码参数

```python
# 远端有 NOPASSWD sudo → 直接跑
c.sudo("systemctl restart nginx")

# 需要密码 → 必须显式给（Fabric 不会去猜）
from invoke import Responder
c.sudo("systemctl restart nginx", password="...", pty=True)
```

`sudo` 在远端通常要求 **tty**，所以 Fabric 内部会帮你加 `pty=True`。
而 pty 的副作用（Day 168 陷阱 3）在这里同样成立：**stdout 与 stderr 合流**。
所以"需要干净地分离输出"时，宁可走 `run("sudo -n ...")` + `!requiretty`。

### 2.7 `Config`：配置优先级

```text
优先级从低到高：
  ① 内置默认值
  ② ~/.fabric.yml / fabric.yml（项目级 Config）
  ③ 环境变量（FABRIC_*）
  ④ 代码里显式传入（Connection(config=...)）
  ⑤ 命令行参数（-H host、--user、--port）

配置合并用：
    from fabric import Config
    cfg = Config(overrides={"run": {"warn": True},
                            "ssh": {"connect_kwargs": {"timeout": 10}}})
```

**为什么要分层**：同一份部署代码要在 CI（无交互）和本地（有交互）跑出不同行为，
分层配置让你**不改代码**就能切换。

### 2.8 与 paramiko / Ansible 的定位对比

| | paramiko | Fabric | Ansible |
|:---|:---|:---|:---|
| 抽象层级 | 协议/会话 | 会话 + 任务 CLI | 声明式状态编排 |
| 多机并发 | 自己写线程池 | `ThreadingGroup` | `forks` 内建 |
| 幂等 | ❌ | ❌（要自己写检查） | ✅（模块级） |
| 需要目标机装东西吗 | 只需 sshd | 只需 sshd | 只需 python（或无 agent 模式） |
| 适合 | 库/精细控制 | **一次性脚本/部署/巡检** | 长期配置管理、大规模状态收敛 |

**判断口诀**：
> "我要**执行命令**" → paramiko / Fabric；
> "我要**保证状态**" → Ansible。

Fabric 是**过程式**的：你写的是"先 A 再 B"。
Ansible 是**声明式**的：你写的是"最终应该是 X"。这两种诉求不会互相替代。

---

## 3. 原理深入

### 3.1 Fabric 内部：一次 `c.run("uptime")` 到底发生了什么

```text
  你的代码                Fabric                    Invoke                 Paramiko
    │                       │                         │                      │
    │ c.run("uptime")       │                         │                      │
    ├──────────────────────▶│                         │                      │
    │                       │ 组装上下文（env/hide/   │                      │
    │                       │ warn/pty/echo…）        │                      │
    │                       ├────────────────────────▶│                      │
    │                       │                         │ 选 runner（Local/Remote）
    │                       │                         ├─────────────────────▶│
    │                       │                         │  open_session()      │
    │                       │                         │  exec_command()      │
    │                       │                         │◀── stdout/stderr ────┤
    │                       │◀── Result(stdout, ...) ─┤                      │
    │◀── Result ────────────┤                         │                      │

  要点：Connection 自己持有一个 paramiko.SSHClient（惰性建连 + 复用），
        所以同一个 Connection 上的 100 次 run 只做 1 次 KEX/认证。
```

**惰性建连**：`Connection(...)` 只是记下参数，**不**发网络包；
直到第一次 `run()` / `put()` 才真正连接。所以"构造 Connection 不写 try"
是安全的，而"run 不写 try"是危险的。

### 3.2 跳板机（gateway）：Fabric 帮你做的事

```python
jump = Connection("bastion", user="ops", connect_kwargs={"key_filename": "~/.ssh/id_rsa"})

inner = Connection("10.0.0.11", user="deploy", gateway=jump,
                   connect_kwargs={"key_filename": "~/.ssh/id_ed25519"})
inner.run("hostname")     # 实际链路：本机 → bastion → 10.0.0.11
```

**原理**：Fabric 在 gateway 上开一个 `direct-tcpip` channel（Day 168 图 3 提到的
第四种 channel 类型），把内网的 TCP 流"隧道"过去，然后在隧道里跑完整的 SSH。

**为什么重要**：手工 `ssh -o ProxyJump` 无法在 Python 里编排多跳；
Fabric 把这件事变成一行参数。这也是"为什么不用系统 ssh 命令"的现实理由之一。

### 3.3 `warn` / `hide` / `echo` / `pty`：四个高频参数的真实语义

| 参数 | 默认 | 语义 | 误用后果 |
|:---|:---|:---|:---|
| `warn` | `False` | `False`：非 0 退出码 → 抛 `UnexpectedExit`；`True`：只记录不抛 | 批量场景里用默认值，第一台失败就中断整批；反过来全用 `True` 会**静默吞掉**真故障 |
| `hide` | `False` | `True`：不打印命令与输出；也可 `hide="stdout"` / `hide="both"` | 部署时把整个文件内容 echo 出来，日志刷屏还泄露内容 |
| `echo` | `False` | `True`：把执行的命令本身打到本地输出 | 调试神器；但会泄露命令里的敏感参数 |
| `pty` | `False` | `True`：远端分配伪终端 | 见 Day 168 陷阱 3：stdout/stderr 合流、多出 `\r` |

**推荐组合**：

```python
c.run("systemctl is-active nginx", hide=True, warn=True)   # 巡检：静默 + 不中断
c.run("tar -xzf /tmp/app.tar.gz", echo=True)               # 变更：打印命令便于审计
c.sudo("systemctl restart nginx", pty=True)                # 需要 tty：只在这时才开
```

### 3.4 并发模型的真相：`ThreadingGroup` 没有"连接池"

```text
  ThreadingGroup("h1".."h200").run("uptime")

  构造时：为每台机器**预先**创建一个 Connection 对象（含 connect_kwargs）
  run 时：  每台一个线程，各自连接 + 执行

  ⇒ 并发度 = 机器数，没有上限概念
  ⇒ 200 台就是 200 个线程同时发起认证 → 目标侧 MaxStartups 限流
  ⇒ Fabric 没有 "workers" 参数；要限流必须**自己分片**
```

**限流写法（生产必备）**：

```python
import itertools
from fabric import ThreadingGroup

def chunks(seq, n):
    it = iter(seq)
    while (batch := list(itertools.islice(it, n))):
        yield batch

for batch in chunks(hosts, 16):          # 每批 16 台
    try:
        ThreadingGroup(*batch, **opts).run("uptime")
    except GroupException as exc:
        ...                              # 逐批处理失败，别让一批拖垮全局
```

### 3.5 幂等：Fabric 不提供，你必须自己写

```text
   ❌ 不幂等
   c.run("mkdir /opt/app/releases/20260927")     # 重跑一次 → 报错 exist
   c.run("systemctl restart nginx")              # 重跑 → 服务抖动

   ✅ 幂等
   c.run("mkdir -p /opt/app/releases/20260927")  # -p 容忍存在
   c.run("test -f /opt/app/current/.deployed-20260927 || systemctl restart nginx")
```

**为什么要强调**：Fabric 的定位是"远程命令执行器"，它**不理解**你的目标状态。
幂等必须由你在命令层与脚本层保证（`-p`、`||`、先查后改、版本标记文件）。

### 3.6 部署事务：release 目录 + 软链切换

```text
 /opt/app/
 ├── releases/
 │   ├── 20260926-1830/     ← 上一版（保留，用于回滚）
 │   └── 20260927-0600/     ← 本次发布
 ├── current -> releases/20260927-0600     ← 原子切换点（ln -sfn）
 └── shared/
     ├── .env               ← 配置不进 release 目录
     └── logs/              ← 日志目录软链进 release

 部署步骤：
   ① 上传 → ② 解包到新 release 目录
   ③ 装上 shared 软链 → ④ 跑迁移/预热
   ⑤ ln -sfn 原子切换 current → ⑥ 重启服务 → ⑦ 健康检查
   ⑧ 失败 → ln -sfn 回上一版 → 重启（回滚，秒级）

 为什么这么设计：
   · 新版本在切换前**不影响**正在服务的旧版本 → 出错不影响线上
   · 软链切换是**原子**的（rename 语义），不会出现"半个版本"
   · 旧目录保留 N 版 → 回滚只需要一次 ln + 一次 restart
```

### 3.7 健康检查与"假成功"

```text
  重启服务返回 exit 0 ≠ 服务真的起来了。
  systemctl restart 成功只代表"进程被拉起了"，不代表它能接受请求。

  三级健康检查：
    ① 进程级：systemctl is-active --quiet nginx        （最快，最弱）
    ② 端口级：ss -ltn | grep -q ':80 '                 （中等）
    ③ 业务级：curl -fsS -m 5 http://127.0.0.1/healthz  （最真实）

  部署脚本必须等到 ③ 通过才算成功；并设置**超时**与**重试间隔**：
    失败了要回滚，不能让"半启动"的服务继续对外。
```

---

## 4. 定义与使用方法（API 速查表）

### 4.1 `Connection`

| 成员 | 说明 |
|:---|:---|
| `Connection(host, user=None, port=None, config=None, gateway=None, forward_agent=None, connect_timeout=None, connect_kwargs=None, inline_ssh_env=None)` | 惰性建连；`connect_kwargs` 传给 paramiko |
| `run(command, warn=False, hide=False, echo=False, pty=False, timeout=None, watchers=(), env=None, replace_env=False)` | 执行命令 → `Result` |
| `sudo(command, password=None, user=None, ...)` | sudo 执行（内部偏 pty） |
| `local(command, ...)` | 在**本地**执行（同一套 Result 语义） |
| `put(local, remote=None, preserve_mode=True)` | SFTP 上传 |
| `get(remote, local=None, preserve_mode=True)` | SFTP 下载 |
| `is_connected` | 是否已建连 |
| `open()` / `close()` | 显式控制连接生命周期 |
| `cd(path)` / `prefix(cmd)` | 上下文管理器：`with c.cd("/opt/app"):` |

### 4.2 `Result`（`invoke.runners.Result`）

| 属性 | 说明 |
|:---|:---|
| `stdout` / `stderr` | 字符串（pty 模式下 stderr 为空） |
| `return_code` | 退出码；被信号杀死时可能是负数 |
| `ok` / `failed` | `return_code == 0` 的语义别名 |
| `exited` | 进程是否已退出 |
| `command` | 原始命令 |
| `shell` | 执行用的 shell 包装 |
| `tail` | `stdout.splitlines()[-10:]`，看末尾最方便 |
| `__str__` | 还原为"命令 + 输出"的可读文本 |

### 4.3 `Group`

| 成员 | 说明 |
|:---|:---|
| `ThreadingGroup(*hosts, **kwargs)` | 并发；`kwargs` 与 `Connection` 相同 |
| `SerialGroup(*hosts, **kwargs)` | 串行 |
| `.run(cmd, ...)` / `.sudo(...)` / `.put(...)` / `.get(...)` | 返回 `{host: Result}` |
| `.from_connections([c1, c2])` | 用已有 Connection 构造 Group（可带各自参数） |
| 失败行为 | 任一主机失败 → 抛 `GroupException`；其 `.result` 是 `{host: Exception}` |

### 4.4 `Config` 与 task

```python
from fabric import Config, task, Connection

# 配置分层
cfg = Config(overrides={"run": {"warn": True, "hide": True},
                        "ssh": {"connect_kwargs": {"timeout": 10}}})

@task
def check(c, hosts="web-01,web-02"):
    """巡检：fab check --hosts=web-01,web-02"""
    for h in hosts.split(","):
        with Connection(h, config=cfg) as conn:
            r = conn.run("uptime", hide=True)
            print(h, r.stdout.strip())

# 命令行：fab -f tasks.py check --hosts=web-01
```

| 要点 | 说明 |
|:---|:---|
| `@task` 函数第一个参数是 `Context`（习惯叫 `c`） | 不是 Connection！对本地用 `c.run`，对远端用 `Connection(...)` |
| `fab -l` | 列出所有任务（含 docstring） |
| `fab -H h1,h2 task` | 临时指定主机（需任务里读取 `c.hosts`） |
| `hide`/`warn` 也可在 `@task(hide=True)` 指定 | 任务级默认值 |
