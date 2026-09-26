# Day 169 — Fabric 批量执行 · 完成清单与练习

> 先读 `README.md`（第 2、3 节），再跑 `code/` 下 4 个脚本，最后做练习。
> **每道题都要能回答"为什么"** —— 尤其"为什么读用并发、写用串行"。

---

## ✅ 今日完成清单

### 一、环境与依赖

- [ ] 已确认 Python ≥ 3.9：`python3 -V`
- [ ] 已安装 Fabric：`pip install fabric`
- [ ] 已验证三个包版本：
      `python3 -c "import fabric, invoke, paramiko; print(fabric.__version__, invoke.__version__, paramiko.__version__)"`
- [ ] 已确认 `Connection` / `ThreadingGroup` / `SerialGroup` 可导入：
      `python3 -c "from fabric import Connection, ThreadingGroup, SerialGroup; print('ok')"`
- [ ] 有一台可测目标机（沿用 Day 168 的本地 sshd 或容器即可）

### 二、跑通示例代码（先预测输出，再运行验证）

- [ ] `cd days/day-169-fabric-批量执行/code`
- [ ] `python3 01-basic-fabric.py --self-test` → `SELF-TEST OK`
- [ ] `python3 01-basic-fabric.py --host <h> --user <u> --key <k> --cmd "uname -a" --echo`
      → 看到 `[ok] ...`，且命令本身被 echo 出来
- [ ] `python3 01-basic-fabric.py --host <h> --user <u> --key <k> --cmd "exit 3"`
      → 看到 `[FAILED(exit=3)]`，且脚本**没有**崩（warn=True）
- [ ] `python3 02-pitfalls.py --self-test` → `SELF-TEST OK`
- [ ] `python3 02-pitfalls.py` → 6 个陷阱逐个复现（陷阱 4 要看到 `key=<Connection …>`）
- [ ] `python3 03-advanced-fabric.py --self-test` → `SELF-TEST OK`
- [ ] `python3 03-advanced-fabric.py --hosts <好主机>,127.0.0.1:9 --user <u> --key <k> --cmd uptime --batch 8`
      → 好主机 `ok`、坏主机 `unreachable`，退出码 **2**
- [ ] `python3 03-advanced-fabric.py --hosts <h> --user <u> --key <k> --rolling --cmd "echo a" --health-cmd "uname -s"`
      → 看到"滚动 1/N → 健康检查通过"
- [ ] `python3 04-deploy-tool.py --self-test` → `SELF-TEST OK`
- [ ] `python3 04-deploy-tool.py --hosts <h> --user <u> --key <k> --artifact <tar.gz> --release r1 --root /tmp/deploy-test`
      → **dry-run** 打印 11 步，远端**没有任何**改动
- [ ] 加 `--apply --restart-cmd true --health-cmd true` 真跑一次，远端出现
      `releases/r1/` 与 `current -> releases/r1`

### 三、动手改造（"读懂了"的唯一证明）

- [ ] 把 `04` 的 `--health-cmd` 改成 `false` 再部署 `r2`，观察：
      ① 健康检查失败 → ② 自动回滚 → ③ `current` 指回 `r1` → ④ 退出码非 0
- [ ] 用 `readlink -f /tmp/deploy-test/current` 亲自确认回滚后指向 r1
- [ ] 给 `04` 增加 `--pre-check` 参数：部署前先跑一条前置检查命令，失败直接跳过本机
- [ ] 把 `03` 的 `--batch` 从 1 调到 16，用 `time` 对比总耗时，算出加速比
- [ ] 给 `03` 的 `chunked_run()` 加一个"失败批次自动重试 1 次"的逻辑，
      并说明为什么重试只对**读**操作安全

### 四、概念自检（不看 README）

- [ ] 我能说清 Invoke / Fabric / Paramiko 三层各管什么，以及排错顺序
- [ ] 我能解释 `Connection(...)` 为什么不会立刻报错
- [ ] 我能说出 `Result.ok` / `return_code` / `exited` 三者的关系
- [ ] 我能解释 `warn=True` 在"读"与"写"场景下为什么结论相反
- [ ] 我能说出 `GroupException` 的键是什么类型，以及成功主机的信息在哪
- [ ] 我能解释为什么 `ThreadingGroup` 没有并发上限，以及怎么补
- [ ] 我能解释 `ln -sfn` 为什么是原子的，`rm -f current && ln -s` 差在哪
- [ ] 我能说出健康检查三级各自能发现什么故障
- [ ] 我能说清"什么时候该从 Fabric 换成 Ansible"

---

## 📝 基础练习题（1–3）

### 练习 1：把 `Result` 翻译成一行运维摘要

写一个 `summary(r)`，对任意 `Result` 返回一行结构化摘要：

```text
ok    | web-01 | exit=0 | 0.42s | up 3 days, load 0.4
FAIL  | web-02 | exit=1 | 0.51s | nginx: inactive (dead)
KILLED| web-03 | exit=137 | 0.09s | (无输出，疑似 OOM)
ABORT | web-04 | exit=None | 5.00s | (超时/自动应答失败)
```

要求：

1. 用 `r.exited` 区分 ok / FAIL / KILLED（≥128 或 <0 算 KILLED）/ ABORT（`None`）
2. 摘要优先取 `stdout` 第一行，为空时取 `stderr` 第一行，都空则 `(无输出)`
3. 写 4 条 `--self-test` 断言，覆盖四种状态
4. **说明**：为什么把 KILLED 与 FAIL 分开？（提示：处置动作不同）

---

### 练习 2：安全的目标解析（禁止猜用户）

写 `parse_target(text)` 支持：

```text
deploy@web-01:2222   → (deploy, web-01, 2222)
deploy@web-01        → (deploy, web-01, 22)
web-01               → ValueError("必须显式给出用户")
```

要求：

1. 端口范围校验 1~65535
2. IPv6 字面量 `deploy@[::1]:2222` 也要支持
3. 为什么"必须显式给出用户"？用一句话说清与 `sudo`/cron 的关系

<details>
<summary>💡 提示</summary>

脚本在 CI 或 cron 里跑时，`$USER` 可能是 `root`，也可能为空。
"不猜"能避免你把变更发到错误的账号上 —— 这类事故在共享跳板机上很常见。
</details>

---

### 练习 3：分片并发的最小实现

不借助 Fabric 的 `Group`，用 `ThreadPoolExecutor` + `Connection` 自己实现
`run_chunked(hosts, cmd, batch=8)`：

1. 每批最多 `batch` 台同时执行
2. 返回 `{host: Result | Exception}`
3. 任何一台失败都不影响其他机器
4. 打印每批耗时与累计进度 `[3/13]`

**并说明**：自己实现相比 `ThreadingGroup` 多得到了什么能力？
（提示：限流粒度、每台独立超时、失败重试的粒度。）

---

## 🚀 进阶挑战题（4–5）

### 练习 4：给部署工具加"金丝雀 + 自动决策"

在 `04` 上扩展：

1. `--canary 1`：先只发 1 台，等它健康检查通过再发剩余机器
2. 金丝雀失败 → **直接中止**，不碰剩余主机，退出码 2
3. `--soak 30`：金丝雀起来后**持续观察 30 秒**（每 5 秒探一次 `/healthz`），
   期间任一次失败 → 回滚金丝雀并中止
4. 报告里明确标注哪台是金丝雀

**思考并写下**：为什么"金丝雀 + 浸泡观察"比"一次性全量"更值得写进脚本？
提示从"故障半径"与"回滚成本"两个角度回答。

<details>
<summary>💡 提示</summary>

金丝雀的价值不在"少发几台"，而在**把故障暴露在影响半径最小的时候**。
浸泡观察解决的是"启动成功但 30 秒后崩"这类慢故障 —— 而健康检查只看当下。
</details>

---

### 练习 5：把"部署"与"巡检"合成一条流水线

写一个 `fab` 任务（`@task`），串起三件事：

```text
fab -f ops.py release --rev=20260927 --hosts=h1,h2,h3
      ① 部署前巡检：磁盘 < 85%、服务当前是 active、目标版本未部署过（幂等）
      ② 逐步滚动部署（复用 04 的逻辑）
      ③ 部署后巡检：健康检查 + 版本核对（cat current/VERSION）
      → 任一步骤失败：打印"停在哪一步/哪一台" + 回滚建议 + 退出码 1
```

要求：

1. 用 `@task` + `Context`，命令行能传 `--rev` 与 `--hosts`
2. "未部署过"用版本标记文件判断（幂等）
3. 每一步的结论都写进 `deploy-audit.jsonl`
4. 说明：为什么"部署前巡检"能省掉很多回滚？（提示：把可预见的失败前置）

<details>
<summary>💡 提示</summary>

`@task` 函数的第一个参数是 `Context`（习惯叫 `c`），**不是** `Connection`：
需要远端连接时要自己 `Connection(host, ...)`。
`@task(hosts=[...])` 或 `--hosts` 由你自己解析 —— Fabric 只负责把参数传进来。
</details>
