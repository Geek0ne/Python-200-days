# Day 185 — 阶段项目 · 自动化运维平台（四）：一键部署 + 端到端验收

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185，本日收官）
> **子主题**：预检（端口身份）· 存活/就绪双探针 · 一键部署与自动回滚 · 端到端冒烟验收 · 故障演练（MTTR）
> **位置**：Day 182–185 阶段项目的第 4 天，也是这个项目的收尾。本目录自带全部代码，**不依赖其它 day 目录**。

> 本课所有命令输出都是 **2026-10-17 在本机真机执行捕获**，原样粘贴。
> 环境：Linux 7.0.0-34-generic (x64) / 4 vCPU / 15.6 GiB / Python 3.12.3 /
> 零第三方依赖（只用标准库：`http.server` / `subprocess` / `signal` / `socket`）。

---

## 这个项目最后长成什么样

| 天 | 交付物 | 回答的问题 |
|---|---|---|
| Day 182 | 平台 API（主机清单/健康/指标） | "现在系统什么状态？" |
| Day 183 | 容器化 + CI + 一键部署脚本雏形 | "怎么把它搬上别的机器？" |
| Day 184 | 日志接收端 + 采集器 + 看板 | "出事了去哪看日志？" |
| **Day 185（今天）** | 部署流水线 + 验收 + 演练 | **"发布敢不敢按下去？坏了多久能好？"** |

今天的核心命题只有一句：**把"部署成功"变成程序能判定的结论**，并且用**真实数字**回答"多快能恢复"。

---

## 概念解释（速览，完整版在 `concepts.md`）

**预检（preflight）**：动手前回答"现在能不能安全地改线上"。关键是**判身份而不是判空**：
端口被占时，先看 ocupier 是不是自己的服务（pidfile + `cmdline` 标记），是则允许原地升级，
不是则失败退出 —— **绝不杀无名进程**。

**存活 vs 就绪**：`/healthz` 答"进程还在吗"（失败→重启）；
`/readyz` 答"现在能接流量吗"（失败→摘流量，不重启）。合并成一个探针是发布事故的常见来源。

**优雅停机**：收到 SIGTERM 后 ①停止 accept ②排空在途请求 ③退出。
注意 `socketserver` 的 daemon 线程**不会**被 `server_close()` 等待，必须自己记账。

**回滚**：判定条件必须是外部可观测的（就绪超时 / 验收断言失败），且回滚路径必须演练过。

**MTTR**：从故障注入到业务恢复的时间。探针间隔是它的下限 —— 这个数字决定了告警阈值该定多少。

---

## 原理解释（三条实测结论）

### 1. "我注册了 SIGTERM handler" ≠ "在途请求会被做完"（本日最重要的翻车）

第一版实现（`signal.signal + httpd.shutdown()`）的实测结果：

```text
在途请求结果: {"code": 0, "err": "RemoteDisconnected", "el": 0.547}
SIGTERM 后进程仍存活: 0.297s        ← 进程 0.3 秒就没了
api.log: sigterm_received(45.800) → stopped(46.085)   ← 285ms 就退场
```

根因：处理线程是 daemon 线程，主线程一返回，解释器就把它带走。
修复：自己维护在途请求计数（`TrackingServer`），停机顺序改为
`shutdown()`（停收）→ `wait_idle(宽限期)`（排空）→ `server_close()`（收尾）。复测：

```text
在途请求结果: {"code": 200, "body": {"slept_ms": 1500, "done": true}, "el": 1.502}
api.log: {"msg":"drained","waited_s":0.839,"active":0,"max_concurrent":1}
```

### 2. PID 号不是身份凭证

04 号示例真机跑了一遍"照 pidfile kill"的错误逻辑，结果就是**静默杀掉一个无关进程**：

```text
洞2: {"scenario":"pidfile-指向别的进程（PID 复用）","victim_pid":2167648,
      "naive_is_running":true,"correct_is_running":false,
      "correct_reason":"pid-reused(cmdline='sleep 120')",
      "naive_action":{"killed":2167648,"by":"naive(kill -9, 未验证身份)"},
      "victim_alive_after_naive_kill":false}     ← 无辜进程真的没了
洞1: {"scenario":"pidfile-指向已死进程","naive_is_running":false,
      "correct_reason":"stale-pidfile(pid-dead)"}
```

还有一个更隐蔽的：**僵尸进程的 `/proc/<pid>` 依然存在**。
用"目录存在"判断存活，会让停机脚本永远等一个已经死掉的进程（本日真机踩到：
优雅停机其实成功了，脚本却判定超时并去 SIGKILL 一具尸体）。
正确判据是读 `/proc/<pid>/stat` 的 state 字符。

### 3. 端口冲突要用"身份"判定，`bind()` 要认 `TIME_WAIT`

两个都是真机撞出来的：
- 演练脚本自己 `bind()` 失败：`OSError: [Errno 98] Address already in use` ——
  上一轮演练在同一端口留下 TIME_WAIT 连接对，监听 socket 必须设 `SO_REUSEADDR`。
- 部署脚本"端口被占 → 失败"导致**第二次部署永远做不成**（上一版就在监听这个端口）。
  修成"按身份判定"后：自己的服务 → 允许继续（先优雅停它）；别人的 → 快速失败且不杀。

---

## 定义与使用方法（API 速查）

### 00 服务本体

| 接口 | 语义 | 状态码 |
|---|---|---|
| `/healthz` | 存活 | 200（进程活着）/ 连不上 |
| `/readyz` | 就绪 | 200 就绪 / **503 未就绪** |
| `/api/v1/hosts` | 业务 | 200 带数据 / 503 未就绪 |
| `/metrics` | 指标 | 200（requests_total / uptime_s / ready） |
| `/slow?ms=N` | 测试用慢接口 | 200（用于验证排空） |

参数：`--port` / `--version` / `--data hosts.json` / `--ready-delay` /
`--fail-ready`（模拟坏版本）/ `--grace`（排空宽限期秒数）

### 01 进程管理三件套

| 函数 | 作用 | 关键点 |
|---|---|---|
| `validate_pid(pidfile, marker)` | 判定"这个 PID 是不是我们的" | `cmdline` 含 marker；僵尸算已死 |
| `start_service(...)` | 起进程 + 等就绪 | `wait=False` 可只起不等（观察未就绪阶段） |
| `stop_service(pidfile)` | SIGTERM → 等 → 超时才 SIGKILL | 强杀会标记 `graceful:false`（应告警） |
| `wait_ready(url, timeout)` | 轮询就绪探针 | 返回 (ok, 耗时, 最后状态码) |

### 02 一键部署

```bash
python3 02-deploy-oneclick.py --port 8400 --version v1.2.0 --state-dir /tmp/d185
python3 02-deploy-oneclick.py --port 8400 --version v1.2.1 --state-dir /tmp/d185 --simulate-bad-release
python3 02-deploy-oneclick.py --port 8400 --version v1.2.2 --state-dir /tmp/d185 --dry-run
```
退出码：`0` 成功 / `3` 预检失败 / `4` 已自动回滚 / `5` 回滚也失败。

### 03 验收 / 05 演练

```bash
python3 03-smoke-acceptance.py --self-test            # 9 项断言
python3 03-smoke-acceptance.py --compare-kill         # 额外对比 SIGKILL 的破坏力
python3 05-drill-chaos.py --json /tmp/drill.json      # D1/D2/D3 时间线
```

---

## 图解

完整 5 张在 `diagrams/README.md`。最该先看的是停机时间线：

```text
SIGTERM（正确实现）                          SIGKILL / 没排空（第一版实现）
t0.00 收到 SIGTERM，停止 accept              t0.00 信号到达
t0.25 在途请求还在处理                        t0.30 进程消失（实测 0.297s）
t1.20 请求完成 → 客户端 200 ✅                t0.55 客户端 RemoteDisconnected ❌
t1.34 进程退出（exit_took 0.051s）            用户看到连接重置
```

---

## 实战代码案例

```bash
cd ~/code/Learn-Python/days/day-185-运维平台-一键部署与验收/code
for f in 0*.py; do echo "== $f"; timeout 120 python3 "$f" --self-test || echo "❌ $f"; done
```

每个脚本都带 `--self-test`：离线、零依赖、自己起服务自己收尾。
这一课的自证尤其重要 —— 因为**部署代码的 bug 只有"跑完一遍"才现形**（本日踩了 4 个）。

---

## 实战实验手册

> 三个实验独立复现：各自用随机空闲端口 + 临时目录，跑完自己清理。

### 实验一：就绪语义 + 在途请求排空（真实链路）

**目的**：证明"端口在听"和"能接流量"是两回事；证明 SIGTERM 会把在途请求做完。

**环境**：Python 3.12.3 / 标准库 / 本机回环

**准备 + 执行**：
```bash
cd ~/code/Learn-Python/days/day-185-运维平台-一键部署与验收/code
python3 03-smoke-acceptance.py --self-test
```

**实际结果**（真机捕获，原样粘贴）：
```text
验收目标: http://127.0.0.1:40257  版本 v-smoke  数据文件 .../hosts.json (3 台主机)
  ✅ 0. 端口已开始监听  — 等待 0.137s
  ✅ 1. /healthz == 200  — code=200 version=v-smoke
  ✅ 2a. 未就绪时 /readyz == 503  — code=503
  ✅ 2b. 就绪后 /readyz == 200  — 就绪等待=2.037s last=200
  ✅ 3. /api/v1/hosts 条数 == 数据文件条数  — code=200 count=3 expect=3
  ✅ 4. /metrics requests_total 增量 == 6  — before=26 after=32 delta=6
  ✅ 5. 未知路径 404 且 body 是 JSON  — code=404
  ✅ 6. SIGTERM 时在途请求被做完（200）  — {'code': 200, 'slept_ms': 1200, 'elapsed': 1.201}
  ✅ 7. SIGTERM 后进程及时退出（<3s）  — 退出耗时=0.051s（完成在途请求后）

结果: 9/9 项通过
```

**结论**：`/readyz` 在 warmup 期间确实 503（第 2a 项），业务接口也拒绝服务；
SIGTERM 后在途请求拿到 200（1.201s 跑完），进程随后 51ms 退出。

**清理**：脚本自带（临时目录 + 进程回收）。

---

### 实验二：一键部署的三个场景（成功 / 坏版本自动回滚 / 端口冲突）

**目的**：证明"部署成功"是被**判定**出来的，而不是"脚本没报错"。

**执行**：
```bash
cd ~/code/Learn-Python/days/day-185-运维平台-一键部署与验收/code
STATE=/tmp/d185-exp; rm -rf $STATE; mkdir -p $STATE
printf '%s' '[{"host":"web-01"},{"host":"web-02"}]' > $STATE/hosts.json

python3 02-deploy-oneclick.py --port 8400 --version v1.0.0 --state-dir $STATE --data $STATE/hosts.json
python3 02-deploy-oneclick.py --port 8400 --version v1.0.1-bad --state-dir $STATE --simulate-bad-release
echo "退出码=$?"
cat $STATE/current.json
python3 02-deploy-oneclick.py --self-test        # 三个场景的自动断言版
```

**实际结果**（真机捕获，节选）：
```text
[2] 启动结果: {"started": true, "pid": 2167601, "ready": false, "ready_wait_s": 3.001,
              "last_ready_code": 503, "business_ok": false}          ← 坏版本：永远不就绪
[!] 新版未通过验收 → 触发自动回滚
[5] 回滚到 v1.0.0: {"ready": true, "ready_wait_s": 0.408,
                    "business_check": {"code": 200, "count": 0}, "business_ok": true}
✅ 已回滚到上一个可用版本（线上没坏）
✅ self-test 通过：部署成功 → 坏版本自动回滚 → 端口占用被预检拦截；事件: ['deploy-ok', 'rollback-ok']
```

**关键点**：坏版本是"进程活着、端口在听、业务接口 503"——**这正是只做 liveness 探针会漏掉的情况**。
如果验收只检查"端口通不通"，这个坏版本会被判为部署成功。

**清理**：`rm -rf /tmp/d185-exp`（脚本自证用临时目录，自动清理）。

---

### 实验三：故障演练 —— MTTR / 端口冲突 / 停机对比

**目的**：把"能不能恢复"量成数字，用来推导告警阈值。

**执行**：
```bash
cd ~/code/Learn-Python/days/day-185-运维平台-一键部署与验收/code
python3 05-drill-chaos.py --json /tmp/d185-drill.json
```

**实际结果**（真机捕获，完整时间线）：
```json
{
  "host": "ace", "port": 52237,
  "D1": { "drill": "D1-kill9", "probe_interval_s": 0.2, "detect_latency_s": 0.001,
          "restart_to_ready_s": 0.002, "mttr_s": 0.416, "business_after_recovery_code": 200 },
  "D2": { "drill": "D2-port-conflict", "preflight_ok": false,
          "preflight_reason": "端口 52237 被**非本服务**占用，拒绝部署（不杀无名进程；pidfile 判定=no-pidfile）",
          "fail_fast_s": 0.0002, "occupier_still_alive": true },
  "D3": { "SIGTERM": { "in_flight_code": 200, "in_flight_elapsed_s": 1.202, "exit_took_s": 0.05 },
          "SIGKILL": { "in_flight_code": 0,   "in_flight_elapsed_s": 0.252, "exit_took_s": 0.0 } }
}
```

**关键数字（本机实测）**：

| 指标 | 数值 | 说明 |
|---|---|---|
| D1 发现延迟 | 0.001s | 0.2s 轮询；kill -9 后端口立即关闭，首次轮询即失败 |
| D1 重启到就绪 | 0.416s（MTTR） | 同机本地进程，无调度器（K8s 拉 Pod 会明显更久） |
| D2 预检失败耗时 | 0.0002s | 快速失败，且占用者进程存活（无二次事故） |
| D3 SIGTERM 在途请求 | 200（1.202s 完成） | 排空生效 |
| D3 SIGKILL 在途请求 | 连接失败（0.252s 被切断） | 强杀的代价 |

**结论**：本机 MTTR ≈ 0.4s，所以"不可用 1 秒"当 P1 会全是噪音；
真正该告警的是**探针连续失败超过 MTTR 的若干倍**，以及 `drain_timeout` 这类"排空没做完"的事件。

**清理**：脚本自带（随机端口 + 临时目录 + 进程回收）。

---

## 翻车实验（本日真机踩的坑，全部保留证据）

### 翻车 1：优雅停机是假的（最重要）

**现象**：SIGTERM 之后 0.297s 进程就退出，在途 `/slow?ms=1500` 请求被切断，
客户端 `RemoteDisconnected`。
**假设**：handler 注册了，shutdown 调了，应该没问题。
**验证手段**：在请求进行中发 SIGTERM，同时比对 API 自己写的日志时间戳
（`sigterm_received` 45.800 → `stopped` 46.085，只差 285ms，而请求需要 1500ms）。
**真实根因**：处理线程是 daemon 线程，`socketserver` 的 `server_close()` 不会为它阻塞；
主线程返回后解释器直接把 daemon 线程带走。
**修复**：`TrackingServer` 自己维护在途计数 + Condition，停机顺序
stop-accept → wait_idle(grace) → server_close。
**复测**：在途请求 200（1.502s 完整跑完），进程随后 0.051s 退出，日志出现 `drained waited_s=0.839`。

### 翻车 2：僵尸进程让"停机"永远等不到

**现象**：`01-process-runner.py --self-test` 报
`{'stopped': True, 'graceful': False, 'took_s': 5.026, 'note': 'graceful 超时，已 SIGKILL'}`
—— 而 API 日志明明写着 `stopped`（它其实优雅退出了）。
**假设**：进程没退出。
**验证手段**：直接 `kill -TERM` 后轮询 `/proc/<pid>` 是否存在。
**真实根因**：子进程退出后没人 `wait()`，成了**僵尸**；
僵尸的 `/proc/<pid>` 目录依然存在，于是"进程还在"永远为真。
**修复**：`pid_alive()` 改读 `/proc/<pid>/stat` 的 state（`Z/X` 视为已死），
并对自己启动的子进程做回收。
**复测**：`✅ 陈旧 PID 被识破、就绪等待生效、重复启动被拒、优雅停机成功`。

### 翻车 3：自证脚本自己泄漏端口，第二次就跑不动

**现象**：第二次运行 `02` 自证时，第 3 个场景期望"预检拦截"却先被自己的残留进程拦住了
（`AssertionError: 3`）。
**真实根因**：上一次运行崩溃在临时目录删除之后，pidfile 随临时目录一起没了，
服务进程成了孤儿继续监听端口 → 下一次运行"端口被占"。
**修复**：自证里用 `try/finally` 显式 `stop_service(pidfile)`，
端口改为 `free_port()`（内核分配空闲端口）。
**教训**：**测试的收尾和业务逻辑一样重要**；写死端口的自证脚本天生不可重入。

### 翻车 4：演练脚本 `bind()` 被 TIME_WAIT 挡住

**现象**：`05-drill-chaos.py` 在 D2 崩了：`OSError: [Errno 98] Address already in use`
—— 明明上一轮的服务已经停了。
**真实根因**：上一轮演练在该端口留下 TIME_WAIT 连接对，不带 `SO_REUSEADDR` 的 `bind()` 会被拒。
**修复**：监听 socket 设 `SO_REUSEADDR`（只复用 TIME_WAIT，不会抢占真正在 listen 的端口）。
**附带收获**：这条正好解释了生产里"重启服务报端口占用"的一大类报障。

---

## 思考题

1. 本课 MTTR 0.416s 是"同机、本地进程"的数字。换成 K8s（拉 Pod + 镜像拉取 + 调度），
   MTTR 会由哪几段组成？请指出其中**最容易被你误判为"应用慢"**的一段。

2. `/readyz` 里做依赖检查会让"依赖抖动"变成"服务被摘流量"。
   在什么业务下这是对的，什么业务下这是灾难？请给出两种业务的判断标准。

3. 回滚到旧版本时，数据库 schema 可能已经被新版本改过（"向前兼容"问题）。
   在**回滚**这个动作上，你会加什么约束或检查？（提示：迁移脚本的双向可用性 / expand-contract 模式。）

4. 如果 `preflight` 里"端口被占"判定为"是本服务"，但 pidfile 恰好是过期的
   （进程活着但其实是别的实例），会发生什么？怎么用启动时间（`starttime`）再收一道口子？

5. 把 `stop_service` 的超时从 5s 改成 0.5s "为了发布更快"，会发生什么？
   请从"在途请求 / 长连接 / 后台任务"三个角度说明代价。

---

## 收尾卫生（本课自己遵守的）

- 所有实验都在 `/tmp` 下的独立目录、**内核分配的空闲端口**上做，结束即 `rm -rf`。
- 每个 `--self-test` 都在 `finally` 里停服务（否则端口泄漏会让下一次运行失败 —— 本日真机踩到）。
- 演练结束确认：无残留 `platform-api` 进程、端口释放。
- 本目录零第三方依赖，也无外部服务（无 Docker/Redis/ES），换一台有 Python 3.10+ 的机器即可复现。
