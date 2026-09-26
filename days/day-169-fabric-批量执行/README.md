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
