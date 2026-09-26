# Day 168 — SSH 远程管理（paramiko）· 完成清单与练习

> 建议顺序：先读 `README.md`（第 2、3 节是核心），再跑 `code/` 下 4 个脚本，
> 最后做练习。**每道练习都要能回答"为什么"**，而不是"跑通了"。

---

## ✅ 今日完成清单

### 一、环境与依赖

- [ ] 已确认 Python ≥ 3.9：`python3 -V`
- [ ] 已安装 paramiko：`pip install paramiko`
- [ ] 已验证版本：`python3 -c "import paramiko; print(paramiko.__version__)"`
- [ ] 已确认 `cryptography` 一并装好（paramiko 的加密后端）：
      `python3 -c "import cryptography; print(cryptography.__version__)"`
- [ ] 有一台可测的 SSH 目标机（任选其一）：
      - 本机自测：`sudo apt install openssh-server && sudo systemctl start ssh`
      - 容器/虚机：`docker run -d -p 2222:22 --name sshd-test linuxserver/openssh-server`
      - 云上跳板机（**只读账号，别拿生产 root 练手**）

### 二、跑通示例代码（先预测输出，再运行）

- [ ] `cd days/day-168-ssh-远程管理/code`
- [ ] `python3 01-basic-ssh.py --self-test` → `SELF-TEST OK`
- [ ] `python3 01-basic-ssh.py --target <user>@<host> --key ~/.ssh/id_ed25519 --cmd "uname -a"`
      → 看到 `exit=0 (成功)` 与 stdout 摘要
- [ ] `python3 01-basic-ssh.py --target ... --cmd "echo o; echo e >&2; exit 3"`
      → **同时**看到 stdout 与 stderr，退出码 3
- [ ] `python3 02-pitfalls.py --self-test` → `SELF-TEST OK`
- [ ] `python3 02-pitfalls.py` → 6 个陷阱逐个复现（陷阱 1 要看到"文件真被删了"）
- [ ] `python3 03-advanced-ssh.py --self-test` → `SELF-TEST OK`
- [ ] `python3 03-advanced-ssh.py --host <h> --user <u> --key <k> --cmd hostname --repeat 5`
      → 观察"首次含握手 vs 之后平均毫秒数"的对比，以及 **1 个 Transport 开了 6 个 channel**
- [ ] `python3 04-batch-ops.py --self-test` → `SELF-TEST OK`
- [ ] `python3 04-batch-ops.py --inventory ./inventory.ini --cmd "df -h /" --workers 8 --out ./reports`
      → 退出码符合契约，`reports/` 下有 `batch-audit.jsonl` 与 `batch-report.json`

### 三、动手改造（"读懂了"的唯一证明）

- [ ] 把 `01` 里的 `timeout=10` 改成 `timeout=0.001`，观察报错类型；
      再改成 `None`，用 `timeout 20 python3 ...` 强制打断，记录它卡了多久
- [ ] 给 `01` 的 `run()` 加一个 `stdin_data` 参数，支持把内容喂给远端 `cat > /tmp/x`
      （提示：先 `write` 再 `shutdown_write()`）
- [ ] 把 `03` 的 `--repeat` 加到 200，观察"平均 ms/条"是否继续下降并趋于稳定
      （如果不降了，说明瓶颈已经从握手变成网络 RTT 或远端进程启动）
- [ ] 给 `04` 增加 `--tag <name>`，过滤 inventory 里某一组（用别名前缀匹配即可）
- [ ] 把 `04` 的 `--workers` 从 8 改成 1，记录总耗时差异，算出本轮的真实并发加速比

### 四、概念自检（不看 README）

- [ ] 我能画出 SSH 四层结构，并说清每层解决什么
- [ ] 我能完整描述公钥认证的 challenge-response 三步，并解释为什么能防重放
- [ ] 我能解释"前向保密"（PFS）防止的是哪种攻击
- [ ] 我能说出 `SSHClient` / `Transport` / `Channel` 三层各自的所有权关系
- [ ] 我能解释为什么"不读 stderr"会导致死锁（提到管道缓冲区大小）
- [ ] 我能说出 `get_pty=True` 的两个副作用
- [ ] 我能解释 `recv_exit_status()` 为什么必须在读完流之后调用
- [ ] 我能说出 `timeout` / `banner_timeout` / `auth_timeout` / `channel.settimeout()` 各防什么
- [ ] 我能解释为什么并发度不是越大越好（`MaxStartups`）
- [ ] 我能说出退出码 0 / 2 / 1 的语义，以及"为什么 2 不是 1"

---

## 📝 基础练习题（1–3）

### 练习 1：安全的目标解析与连接自检

扩展 `01-basic-ssh.py` 的 `parse_target()`，支持从 URL 风格写法解析：

```text
ssh://deploy@web-01:2222      → Target(deploy, web-01, 2222)
deploy@web-01                 → Target(deploy, web-01, 22)
web-01                        → 报错（缺少用户，不允许"猜"用户）
```

要求：

1. 为三种合法/非法输入各写一个 `--self-test` 断言
2. 端口必须是 1~65535，否则 `ValueError`（不是 `AssertionError`）
3. **说明**：为什么"不允许省略用户名"是个好设计？
   （提示：想想脚本在多用户机器上以 root 运行会发生什么）

<details>
<summary>💡 提示</summary>

先剥掉 `ssh://` 前缀，再沿用现在的 `user@host[:port]` 逻辑。
"不允许猜用户"的好处：避免脚本在不同的 `$USER` 环境下把命令发到错误的账号上
（`root` 跑 cron 时 `$USER=root`，而你以为自己在操作 `deploy`）。
</details>

---

### 练习 2：退出码翻译器

写一个 `explain_status(code)`，把远端退出码翻译成中文，至少覆盖：

```text
0    成功
1    通用错误
2    用法错误 / 自定义告警（本课契约）
126  权限不足（文件不可执行）
127  命令不存在
130  被 SIGINT（Ctrl+C）中断
137  被 SIGKILL 杀死（常见于 OOM）
143  被 SIGTERM 终止
```

要求：

1. 128 以上统一按"被信号 N 杀死"处理，并用 `signal.Signals(N-128).name` 取名字
2. 对未知信号号不能抛异常，要优雅降级
3. 写出 8 条 `--self-test` 断言

---

### 练习 3：SFTP 上传后的强制校验

把 `01` 的 `send_file()` 升级成"上传 + 校验 + 失败即删"：

1. `put()` 之后用远端 `md5sum`/`sha256sum` 与本地哈希比对
2. 不一致时：**删除远端文件**并返回 `False`（避免留下半个文件被误用）
3. 远端没有 `sha256sum` 时，退化为"比对文件大小"，并在返回值里**明确说明降级了**
4. 用一个 5 MB 文件测一次，再用 `truncate` 造一个"半成品"模拟不一致

<details>
<summary>💡 提示</summary>

远程取哈希：`client.exec_command(f"sha256sum {shlex.quote(path)}")`，
输出第一列就是哈希。删除：`sftp.remove(path)`。
"明确说明降级"很重要 —— 安全相关的能力降级必须**可见**，否则等于没有。
</details>

---
