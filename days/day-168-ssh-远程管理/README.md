# Day 168 — SSH 远程管理（paramiko）

> **一句话定义**：SSH 是一条**加密、可复用、双向**的隧道；paramiko 是这条隧道的
> **纯 Python 客户端实现**，让你不装 `ssh` 命令也能执行远程命令、传文件。

本课从"SSH 到底在保护什么"讲到"批量运维工具怎么写才不会把自己玩死"，
最后落在一个可运行的四脚本工程上（`code/01`~`04`）。

---

## 1. 学习目标

学完本课，你应该能够：

- [ ] 说清 SSH 协议的四层结构，以及每层各解决什么问题
- [ ] 解释"公钥认证比密码认证更安全"的**三个具体理由**（不是口号）
- [ ] 用 `paramiko.SSHClient` 连上一台机器，正确取回 `stdout`/`stderr`/`exit_status`
- [ ] 用 `Transport` + `Channel` 复用一条连接跑几百条命令，而不是每次新建连接
- [ ] 用 `SFTPClient` 上传/下载文件，并知道它与 `scp`/`sftp` 命令的关系
- [ ] 写出**带并发、带超时、带重试、带审计**的批量运维脚本
- [ ] 说出至少 5 个真实生产事故对应的坑（拼接注入、无超时、不校验主机密钥……）

---

## 2. 概念解释

### 2.1 SSH 解决的是什么问题

回到 1995 年：`telnet` 明文传输，`rsh`/`rlogin` 依赖 `.rhosts` 信任（等于没有认证）。
一个网络抓包就能拿到你的密码和全部操作内容。

SSH 的三个核心承诺（按重要性排序）：

| 承诺 | 手段 | 如果缺失会怎样 |
|:---|:---|:---|
| **机密性** | 对称加密（AES/ChaCha20） | 同网段任何人都能用 tcpdump 看到你的密码 |
| **完整性** | MAC（HMAC）/ AEAD | 中间人可以静默篡改命令内容 |
| **对端认证** | 主机密钥 + 用户认证 | 你以为连的是生产机，其实是攻击者的跳板 |

> **关键认知**：SSH 不是"一条管道"，而是一条**可以复用、可开多路**的隧道。
> 一次 TCP 连接里可以同时跑 3 个 shell、2 个 SFTP 会话、若干端口转发。
> 这就是为什么"每次命令都新建连接"的脚本是**反协议设计**的。

### 2.2 认证：密码 vs 公钥

```text
密码认证（password）：
    client ──"我是 root，密码是 hunter2"──▶ server
    ❌ 密码会离开客户端（虽然隧道加密，但服务端拿到了明文；
       且可被钓鱼、可被暴力破解、无法自动化轮换）

公钥认证（publickey）：
    server 事先持有 client 的公钥
    client ──"我想用 key 指纹 XX 登录"──▶ server
    server ──"challenge: 用私钥签这段随机数"──▶ client
    client ──"签名 = ..."──▶ server  （私钥永不离开客户端！）
    ✅ 私钥不出本机、✅ 抗暴力破解（4096 位 ≈ 不可枚举）、
    ✅ 可无交互自动化、✅ 一条 known_hosts + 一个 key 就能精确吊销
```

**工程结论**：
- 自动化用**密钥**，密钥必须有口令（passphrase）+ 用代理（ssh-agent）避免硬编码
- 密码认证留给"人第一次登录"，之后立刻换密钥
- 永远不要 `password="..."` 写死在代码里（Git 历史删不干净）

### 2.3 paramiko 是什么，不是什么

| 是 | 不是 |
|:---|:---|
| 纯 Python 的 SSH2 客户端/服务端库 | 不是 `ssh` 命令的包装（不读你的 `~/.ssh/config`！） |
| 支持公钥/密码/键盘交互认证、SFTP、端口转发 | 不是运维框架（无并发编排、无重试、无幂等） |
| 依赖 `cryptography`，可跨平台 | 不负责"任务该不该跑"——那是 Ansible/Fabric/Salt 的事 |

> ⚠ 最常见的误解：**paramiko 不会自动读 `~/.ssh/config`**。
> 你在命令行能 `ssh prod` 是因为 `ssh` 命令读了 config；
> 用 paramiko 就必须自己解析 `Host` 段（`04` 实战脚本里演示了简化版解析）。

### 2.4 三层 API：SSHClient / Transport / Channel

```text
┌──────────────────────────────────────────────────────────────┐
│ 最上层 SSHClient   —— "一把好用的瑞士军刀"                      │
│   · connect() / exec_command() / open_sftp()                  │
│   · 每次 exec_command 在内部**复用**同一条 Transport 的 channel │
│   · 适合：脚本化、命令量不大（几十~几百条）                      │
├──────────────────────────────────────────────────────────────┤
│ 中层 Transport     —— "连接本体"，可精细控制                     │
│   · 管理密钥交换、加密、keepalive、channel 生命周期              │
│   · 可同时 open_session() 多个 channel（真正的多路复用）          │
│   · 适合：连接池、长连接、自定义保活、端口转发                    │
├──────────────────────────────────────────────────────────────┤
│ 下层 Channel       —— "一条逻辑流"                              │
│   · 有独立的 recv/send、exit_status、pty 设置                   │
│   · exec_command / invoke_shell / SFTP 都跑在 channel 上         │
└──────────────────────────────────────────────────────────────┘
```

**为什么值得分清**：`SSHClient.exec_command()` 每调一次就开一个新 channel；
如果你要跑 1000 条命令，要么复用 client（推荐），要么用 `Transport.open_session()`
自己管理。`SSHClient` 底层也是 `Transport`，只是帮你把脏活包了。

### 2.5 主机密钥验证：TOFU 模型

```text
第一次连接某主机：
    服务端发来自己的公钥指纹
    客户端：没记录过 → 弹窗"你确定吗？(yes/no)"
            你输 yes → 指纹写进 ~/.ssh/known_hosts（Trust On First Use）

第二次以后：
    指纹与记录一致 → 静默通过
    指纹不一致     → ⚠⚠⚠ "REMOTE HOST IDENTIFICATION HAS CHANGED"
                    （可能被 MITM，也可能只是重装系统）
```

paramiko 的默认策略是 **`RejectPolicy`**：未知主机直接抛异常。
这比命令行 `ssh` 更严格。开发时图省事写成 `AutoAddPolicy` 很方便，
但**生产脚本里应该改成"白名单校验"**（见陷阱 2）。

```python
# ❌ 生产禁用：等于完全不校验
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# ✅ 生产写法：显式加载一份受信 known_hosts，未知主机直接失败
client.load_system_host_keys("/etc/ssh/ssh_known_hosts")
client.set_missing_host_key_policy(paramiko.RejectPolicy())
```

### 2.6 SFTP 与 SCP 的区别

| | SCP | SFTP |
|:---|:---|:---|
| 协议 | 复用 `ssh` 命令 + 传统 cp 语义（老） | **独立子系统**，跑在 SSH channel 上 |
| 能否断点续传 | 不能 | 能（`seek` + `prefetch`） |
| 能否列目录/改权限/建软链 | 不能 | 能 |
| 能否在文件不影响 shell 的情况下并发 | 差 | 好 |
| paramiko 支持 | 无直接 API（用 sftp 代替） | `open_sftp()` |

**结论**：自动化里统一用 SFTP。paramiko 的 `SFTPClient` 还提供了
`put`/`get`/`listdir`/`stat`/`chmod`/`rename`/`symlink` 等一整套。

### 2.7 并发模型：批量运维为什么必须并发

假设 200 台机器，每台执行一条 `uptime` 耗时 1.2 秒（网络 RTT 占大头）：

| 模式 | 总耗时 | 说明 |
|:---|:---|:---|
| 顺序 | 200 × 1.2 ≈ **240 秒** | 4 分钟里你只是在等网络 |
| 并发 20 | 10 批 × 1.2 ≈ **12 秒** | 运维体验的临界点 |
| 并发 100 | 2 批 × 1.2 ≈ **2.4 秒** | 但可能触发目标机 `sshd` 的 `MaxStartups` 限流 |
| 并发 200 | ~1.2 秒 | ❌ 大概率被限流/被安全设备判定为扫描 |

> **关键认知**：并发的瓶颈**不是 CPU**（网络 IO 等待），
> 所以用 `ThreadPoolExecutor` 就够了，不需要 asyncio 重写。
> 但并发度必须**有上限**（默认建议 8~16），否则你会亲手制造一次"分布式拒绝服务"。

```text
顺序执行（200 台）             并发 16（200 台）
台1 ──1.2s──▶                  16 台并排 ──1.2s──▶ 第 1 批
台2 ──1.2s──▶                  16 台并排 ──1.2s──▶ 第 2 批
...                            ...
台200 ──1.2s──▶                ≈ 13 批 × 1.2s ≈ 15.6s
总计 ≈ 240s                    吞吐提升 ≈ 15×
```
