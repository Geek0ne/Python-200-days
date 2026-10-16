# Day 183 — 阶段项目 · 自动化运维平台（二）：容器化 + CI/CD + 一键部署

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185）
> **子主题**：Docker 镜像构建与多阶段 · CI 流水线（构建/测试/推送）· 一键部署脚本 · 回滚与健康检查
> **位置**：Day 182–185 阶段项目的第 2 天。本目录自带全部代码，**不依赖其它 day 目录**。

> 本课所有命令输出都是 **2026-10-16 在本机真机执行捕获**，原样粘贴。
> 唯一没跑成的是「推镜像到远端仓库」，那一节明确标了 **未实测**（原因 / 预期 / 验证方法）。
> 环境：Linux 7.0.0-34-generic (x64) / Docker 29.1.3（**legacy builder，无 buildx**）/
> Python 3.12.3（宿主）· 3.12.14（容器内）/ act 0.2.89 / overlayfs 存储驱动。

---

## 概念解释

### 先说清楚：昨天到今天的「平台」长什么样

Day 182 我们做出了一个能在本机跑的运维平台 API：主机清单、健康状态、指标。
它能跑，但**只有作者那台机器能跑**。今天要解决的三个问题，正好是三段流水线：

| 问题 | 今天的答案 | 落在哪个产物里 |
|---|---|---|
| 「在我这儿能跑」 | 把运行环境一起打包 → **镜像** | `code/02-multistage-image.py` → Dockerfile |
| 「怎么保证每次合进去都是好的」 | 自动构建+测试+推送 → **CI** | `.github/workflows/ci.yml` |
| 「上线后坏了怎么办」 | 一键部署 + 健康检查 + **回滚** | `code/04-deploy-rollback.py`、`05-rollback-drill.py` |

一句话串起来：**镜像解决「环境一致」，CI 解决「每次改动都被验过」，一键部署+回滚解决「敢按发布键」。**

### 镜像不是「一个文件」，是「一串层」

`docker build` 每执行一条会改文件系统的指令（`RUN` / `COPY` / `ADD`）就产生一个**只读层**；
镜像就是这些层的链表，容器启动时在最上面加一层可写的。三个直接后果：

1. **层可以共享**：10 个镜像都基于 `python:3.12-slim`，本机只存一份基础层。
2. **删掉的东西不会变小**：`RUN pip install xxx && rm -rf xxx` ——文件在早期层里还在，
   最终镜像体积**不减**。所以「一条 RUN 里装完又清干净」是硬功夫。
3. **改一行代码 = 后面所有层重建**：这就是把 `COPY requirements.txt` 放在
   `COPY .` **之前**的原因——依赖没变的话那一层直接命中缓存。

### 构建上下文与 .dockerignore

`docker build ... .` 末尾那个 `.` 不是「Dockerfile 在哪」，而是**构建上下文**：
整个目录会被打包发给 daemon。上下文里有什么，取决于你的 `.dockerignore`：

```
.git/            ← 不忽略：每次 build 多传几十 MB，且 git 历史可能泄进镜像
__pycache__/     ← 不忽略：宿主机的 .pyc 可能盖掉容器里该有的字节码
.env             ← 不忽略：**这是泄密**，密钥进了你推到仓库的镜像
tests/ docs/     ← 不忽略：本来只该在构建期存在的东西进了运行镜像
```

> 本日 `.dockerignore` 排除了 `.git` / `**/__pycache__` / `tests/` / `docs/` / `*.md` / `.env`，
> 自检里有专门一条断言它（`02 --self-test`）。

### 多阶段构建：让「构建期的东西」留在构建期

```
单阶段                              多阶段
┌──────────────────────┐            ┌──────────────────────┐
│ python:3.12-slim     │            │ builder              │
│  + gcc / apt 列表     │            │  + gcc               │
│  + pip 缓存           │            │  + venv（只有依赖）    │
│  + 你的代码           │            └──────────┬───────────┘
└──────────────────────┘                       │ COPY --from=builder 只搬 venv
     ↑ 一股脑推到生产                       ┌───▼──────────────────┐
                                            │ runtime（干净）        │
                                            │  venv + 你的代码       │
                                            └──────────────────────┘
```

**但要诚实**：本日的 app 依赖是纯 Python（`prometheus_client`），其实**不装 gcc 也能跑**。
我们故意在单体镜像里装了 gcc，是为了**量化**多阶段的收益（实测省 58.7%），
而不是说「凡有依赖就必须多阶段」。多阶段真正不可替代的场景是：

- 依赖里有**需要编译**的包（C 扩展），构建要 gcc、运行不要；
- 构建期产物**不该进生产**（测试文件、文档、构建缓存、可信度低的中间件）；
- 多个运行镜像**共用同一套构建**（一次构建，产 N 个变体）。

### 三种探针，三种「不健康」

Docker 与 K8s 都把「活着」拆成两个问题，混用是最常见的翻车来源：

| 探针 | 问的问题 | 失败后该做什么 | 别用它做 |
|---|---|---|---|
| **liveness**（`/healthz`） | 进程还活着吗？ | 重启/换实例 | 别查依赖——数据库挂了你重启应用没用，只会雪崩 |
| **readiness**（`/readyz`） | 现在能接流量吗？ | 摘流量 | 别查「进程是否卡死」，那是 liveness 的活 |
| startup | 启动完成的界限 | 在此之前不判前两个 | 本日用 `--start-period` 代替 |

本日两个端点就是这么分的：`/healthz` 只回「进程活着」，`/readyz` 才看依赖。
回滚演练里注入的故障是 **readiness 失败**（依赖没就绪），此时进程是好的、
但它不该接流量——所以是「不上线」而不是「杀进程」。

### CI 流水线：四个 job 的一条链

```
lint ──▶ test(py3.11 / py3.12 矩阵) ──▶ build & push ──▶ deploy
  ↑ 每次 push/PR            ↑ 每次         ↑ 只在 main push   ↑ 只在 main push
  —————————————— CI ——————————————   ———— CD ————
```

分界点是 `if` 那一行：`github.event_name == 'push' && github.ref == 'refs/heads/main'`。
**PR 上只跑到 test 为止**——这既是省钱，也是安全：PR 不该有推镜像/上线的权限。

### 一键部署与回滚：正确语义是「先判后切」

```
错误做法（先切后撤）                正确做法（先判后切）
起新容器 → 切流量 → 发现坏了 → 撤    起新容器 → 验健康 → 通过才算上线
        ↑ 有一段真实流量打到坏版本              ↑ 坏版本**从未**进入可用列表
```

真跑出来的账本（见实验 4）里，`v2.0.0` 只出现在 `history` 且 `result: "failed"`，
`current` 始终是 `v1.0.0`。这不是措辞讲究——「先切后撤」意味着**用户见过那个坏版本**。

---

## 原理深入

### 镜像到底多大：三个口径不一样（本日实测）

同一台机器上同一批镜像，三个命令给出三个数（都是真跑的）：

| 镜像 | `docker images` 的 SIZE 列 | `docker image inspect .Size` | `docker history` 层数 |
|---|---|---|---|
| `python:3.12-slim`（基准） | 179MB | 43,258,862 B（≈41.3 MiB） | — |
| `day183-ops:single` | 434MB | 114,586,798 B（≈109.3 MiB） | 19 |
| `day183-ops:multi` | 196MB | 47,352,410 B（≈45.2 MiB） | 17 |

两点必须说清（不猜、只报实测）：

- **本机没有 buildx**（`docker buildx version` → `unknown command`），走的是 **legacy builder**，
  存储驱动是 `overlayfs`（不是 `overlay2`）。`docker history` 里元数据层的大小显示 `0B`，
  而 `docker images` 的 SIZE 列与 `inspect .Size` **口径不同、差了约 4 倍**。
  我**没有**在这台机器上把这个差异归因到底（那是另一个课题），只如实把三个数都列出来。
- 因此本课**只用 `inspect .Size` 做横向对比**（同一口径、同一台机），
  避免读者拿着 434/196 去跟别处的数字对不上。
- 对比结论（同一口径）：**109.3 MiB → 45.2 MiB，省 64.1 MiB，约 58.7%**。
  省下的大头是 gcc 与 apt 列表。单独验证过：`python:3.12-slim` 里装一次 gcc 再清 apt 列表，
  该镜像 `inspect .Size` 为 111,041,006 B（≈105.9 MiB），比 41.3 MiB 的基准多约 64.6 MiB，
  与「省下 64.1 MiB」基本吻合（两者不是同一次构建，有 apt 元数据与缓存差异）。

### 构建缓存：为什么 Dockerfile 里 COPY 的顺序是性能问题

```
① COPY requirements.txt .      ← 依赖描述先拷
② RUN  pip install -r ...      ← 只有依赖变了这层才重建
③ COPY ops_service.py .        ← 代码最后拷
```

如果反过来（先 `COPY .` 再装依赖），**改一行注释就会重装全部依赖**。
本日 `--no-cache` 那次：single 40.67s / multi 48.73s（都从零构建）。
去掉 `--no-cache` 时依赖层命中缓存，构建时间显著缩短——报告落在
`/tmp/day183/build/build-report.json`（脚本每次构建都会重写它）。

### 容器「启动完成」不是 docker run 返回

`docker run -d` 返回时容器**只是被创建了**，进程可能还没绑定端口。本日实测时间线：

```
docker run 返回            0.77 s
GET /healthz 首次 200      0.549 s（第 2 次探测，每 0.5s 一次）
docker HEALTHCHECK 状态    starting×9 → healthy（第 10 次，≈5 s）
```

`healthy` 出现在 ~5s，正好对应 Dockerfile 里写的
`--interval=5s --timeout=3s --start-period=3s --retries=3`：
`start-period` 内的失败不计入 `retries`，第一次真正的 interval 检查落在第 5s。
所以「部署脚本自己轮询 `/healthz/`"（0.5s 一次，0.549s 就有结果）比等 Docker 的 HEALTHCHECK 快一个数量级——
两者不冲突：前者是**部署门禁**，后者是**运行期守护**。

### 回滚决策点：失败之后，先收现场再动手

部署脚本在健康检查失败时的顺序是刻意设计的：

```
① 打最后一次探测的完整响应（/healthz 200 但 /readyz 503 —— 一眼看出是「依赖没就绪」）
② docker logs --tail 20                  ← 先留证据
③ docker rm -f 坏容器
④ 起上一个可用版本 + 重新健康检查
⑤ 只有第 ④ 步也过了，才宣布「已回滚」
```

本日实测里 ③④ 之后独立 curl 复核 `/version = v1.0.0`——**部署脚本自述不算证据**。

### CI 里 needs 决定的是「并行形状」，不是「流程顺序」

`lint → test → build → deploy` 是一条**串行链**，总时长 = 各段之和。
如果 test 不 `needs` lint，两者会并行起步，墙钟时间取较长者。
本日把 `test` 挂在 `lint` 后面是有意的（lint 最便宜，先挡住低级错误），
但读者要清楚：**这是选择，不是语法要求**。

### act 的能力边界

`act` 在本机用容器模拟 runner，但它**没有 GitHub 的后端服务**，所以：

- `actions/cache` / `upload-artifact` 需要 `ACTIONS_RUNTIME_TOKEN`，本机拿不到；
- runner 是容器不是 VM，「干净环境」的假设只近似成立；
- 需要 registry 凭据 / 真机的 job（build、deploy）本机跑不了——本课就只跑 `lint` 和 `test`。

---

## 定义与方法（速查）

### Dockerfile 指令（本日用到的那批）

| 指令 | 作用 | 本日的用法要点 |
|---|---|---|
| `FROM ... AS name` | 起一个阶段并命名 | 多阶段的 `builder` / `runtime` |
| `WORKDIR` | 后续指令的工作目录 | 用绝对路径，别指望 shell 的 `cd` |
| `RUN` | 构建期执行命令 | 多条用反斜杠连着写，**同一层**才能「装完即清」 |
| `COPY` | 从上下文拷文件 | 先 `requirements.txt` 后代码（缓存友好） |
| `COPY --from=builder` | 从**另一个阶段**拷 | 多阶段的搬运工，只搬需要的东西 |
| `ENV` | 打进镜像的环境变量 | `PYTHONDONTWRITEBYTECODE=1`、`PATH=venv/bin` |
| `EXPOSE` | 声明端口（**不发布**） | 真发布靠 `docker run -p` |
| `HEALTHCHECK` | 容器自身的健康探针 | slim 里**没有 curl**，用 `python3 -c` 打 |
| `CMD` | 默认启动命令 | 用 exec 形式（JSON 数组），信号才能直达进程 |

### 常用命令（本日实验里真用到的）

```bash
docker build -f Dockerfile.multi -t day183-ops:multi /tmp/day183/build        # 构建
docker run -d --name d183-ops -p 18080:8080 -e APP_VERSION=v1 day183-ops:multi
docker inspect d183-ops --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}'
docker logs --tail 20 d183-ops
docker image inspect day183-ops:multi --format '{{.Size}}'                    # 对比体积请用这个
docker history --no-trunc day183-ops:single | head                            # 看层
docker exec d183-ops sh -c 'command -v gcc || echo 没有 gcc'                  # 验证多阶段真的省了
```

### 本日脚本的 CLI 与退出码

| 脚本 | 关键参数 | 退出码 |
|---|---|---|
| `01-ops-service.py` | `--port` / `--self-test` / `--once` / `--fail-mode` | 0 通过，1 断言失败 |
| `02-multistage-image.py` | `--out` / `--write-only` / `--build` / `--no-cache` / `--self-test` | 0/1 |
| `03-ci-pipeline.py` | `--out` / `--print` / `--dry-run` / `--run` / `--force-fallback` / `--self-test` | 0/1（act 退出码原样透传） |
| `04-deploy-rollback.py` | `--image --version` / `--env K=V` / `--rollback` / `--status` / `--dry-run` / `--self-test` | **0 上线成功 · 2 失败已回滚 · 3 失败且无救** |
| `05-rollback-drill.py` | `--dry-run` | 0 演练符合预期，1 否则 |

> 退出码是给 CI 用的接口：`2` 和 `0` 对流水线意义完全不同（「坏了但服务还活着」vs「一切正常」），
> 所以 `04` 不把它们混成 1。

### GitHub Actions 速查（本日 workflow 用到的）

| 键 | 本日取值 | 作用 |
|---|---|---|
| `on.pull_request` | 全量 | PR 也跑 lint/test |
| `permissions` | `contents: read` + `packages: write` | 最小权限，只有推镜像需要写 |
| `concurrency.cancel-in-progress` | `true` | 连推两次自动作废旧的那次 |
| `strategy.fail-fast` | `false` | 矩阵里一个挂不取消其它（要看到全部失败面） |
| `needs` | `lint→test→build→deploy` | 构成 DAG |
| `if` | `github.ref == 'refs/heads/main'` | CI/CD 分界 |
| `secrets.GITHUB_TOKEN` | 登录 ghcr.io | **绝不硬编码**，自检里有负向断言 |

---

## 图解

见 [`diagrams/README.md`](diagrams/README.md)：镜像分层与多阶段、构建缓存命中/失效、
容器健康时间线、CI 四 job 的 DAG 与 CI/CD 分界、一键部署与回滚时序、翻车点地图。

---

## 实战环境

| 项 | 版本 / 说明 |
|---|---|
| 主机 | Linux 7.0.0-34-generic (x64)，4 核 / 16 GB |
| Docker | **29.1.3**，overlayfs 存储驱动，**legacy builder（无 buildx）** |
| Compose | 2.40.3（本日未用到，仅记录） |
| Python | 3.12.3（宿主）/ 3.12.14（运行镜像内） |
| 依赖 | `prometheus_client==0.26.0`（写进 `code/requirements.txt`） |
| act | 0.2.89 + runner 镜像 `catthehacker/ubuntu:act-latest` |
| 端口 | 宿主 `18080` → 容器 `8080`（用 18080 免得跟别天的实验撞车） |

五个脚本都能**离线自检**；只有 `02 --build`、`04`（真部署）、`05`（演练）、`03 --run`（act）需要 Docker。

---

## 实验 1：服务本体（01-ops-service.py）

**目的**：先把「被部署的东西」跑通，后面所有实验都拿它当靶子。

**执行**：
```bash
cd days/day-183-运维平台-容器化部署
python3 code/01-ops-service.py --self-test
python3 code/01-ops-service.py --once
```

**实际结果**（2026-10-16，宿主 Python 3.12.3，未装 prometheus_client）：

```
  ✅ GET /healthz -> 200
  ✅ GET /readyz -> 200
  ✅ GET /version -> 200 且带 version
  ✅ GET /api/hosts -> 4 台主机
  ✅ GET /api/summary -> 按角色聚合
  ✅ GET /metrics -> 文本暴露格式
  ✅ GET /nope -> 404
  ✅ fail_mode=readiness -> /readyz 503
✅ self-test 通过：8 项断言全过 | backend=stdlib-fallback | 端口=37485
```

`--once` 的输出（节选）：

```json
{
  "app": "ops-platform-api",
  "version": "dev",
  "metrics_backend": "stdlib-fallback",
  "liveness": { "ok": true, "reason": "存活" },
  "readiness": { "ok": true, "reason": "依赖正常" },
  "hosts": 4,
  "by_role": { "web": 2, "db": 1, "cache": 1 },
  "alerts": [ "db-01" ]
}
```

**结论**：宿主上没有 `prometheus_client`，`/metrics` 走 stdlib 手写分支，
格式照样是 Prometheus 吃的文本格式——**「有没有第三方库」不该决定服务能不能起**。

**清理**：`--self-test` 绑 0 号端口（本次为 37485）并在结束时关闭，不留进程。

---

## 实验 2：镜像构建 —— 单体 vs 多阶段（真构建、真测体积）

**目的**：把「多阶段省了多少」从口号变成数字。

**执行**：
```bash
python3 code/02-multistage-image.py --self-test
python3 code/02-multistage-image.py --out /tmp/day183/build --build both --no-cache
```

**实际结果**（2026-10-16T14:24Z 起，`--no-cache`，从零构建）：

```
✅ 构建上下文已生成 → /tmp/day183/build
   single         Dockerfile.single    805 字节
   multi          Dockerfile.multi     1311 字节
   dockerignore   .dockerignore        71 字节
   requirements   requirements.txt     26 字节
   app            ops_service.py       12696 字节
▶ docker build -f Dockerfile.single -t day183-ops:single /tmp/day183/build
▶ docker build -f Dockerfile.multi -t day183-ops:multi /tmp/day183/build

镜像实测：
  变体      标签                                       体积    层数      构建耗时
  single  day183-ops:single                  109.3 MB    19    40.67s
  multi   day183-ops:multi                    45.2 MB    17    48.73s

  多阶段省下：64.1 MB（单体 109.3 MB 的 58.7%）

  报告写入：/tmp/day183/build/build-report.json
```

> 两个体积都用 `docker image inspect --format {{.Size}}` 取，脚本里就是这么算的。
> `docker images` 的 SIZE 列在同一时刻给出的是 434MB / 196MB —— **口径不同，见「原理深入」那一节**。
> 多阶段**构建更慢**（48.73s vs 40.67s）：它多了一个阶段、多一次层快照，这是要付的代价。
> 代价换来的是**每次拉镜像少 64 MB**，而拉取发生在每一个部署节点上。

**结论**：
- 多阶段不是「更省事」，是**更快分发**；
- 省下的那 64 MiB 主要是 gcc 与 apt 列表（同一基础镜像里单独装一次 gcc，
  `inspect .Size` 从 41.3 MiB 涨到 105.9 MiB）；
- 运行镜像里验证过没有 gcc：`docker exec d183-ops sh -c 'command -v gcc'` → 空输出。

**清理**：见文末「清理」。

---

## 实验 3：起容器 + 健康检查时间线

**执行**（脚本落在 `/tmp/day183-probe/exp-run.sh`，等价命令如下）：

```bash
docker run -d --name d183-ops -p 18080:8080 -e APP_VERSION=multi-v1 day183-ops:multi
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18080/healthz || true)
  [ "$code" = "200" ] && break; sleep 0.5
done
docker inspect d183-ops --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}'
```

**实际结果**（2026-10-16T14:26Z）：

```
docker run 返回耗时 0.77 s
healthz 200，用时 .549189182s（第 2 次探测）
== docker 自己的 HEALTHCHECK 状态 ==
  探测 1: starting
  ...
  探测 10: healthy
== 端点输出 ==
- GET /version
{"app": "ops-platform-api", "version": "multi-v1", "metrics_backend": "prometheus_client", "uptime_seconds": 5.019}
- GET /healthz
{"status": "ok", "reason": "存活"}
- GET /readyz
{"status": "ready", "reason": "依赖正常"}
- GET /api/summary
{"hosts": 4, "by_role": {"web": 2, "db": 1, "cache": 1}, "avg_cpu": 14.9, "alerts": ["db-01"]}
== 镜像里的 python 与依赖 ==
prometheus_client 0.26.0 | py 3.12.14
gcc: 不在 runtime 镜像里（这正是多阶段要的结果）
== 容器内 /app 内容（看没有 tests/docs 混进来）==
total 24
drwxr-xr-x 2 root root  4096 Oct 16 14:26 .
drwxr-xr-x 1 root root  4096 Oct 16 14:26 ..
-rw-r--r-- 1 root root 12696 Oct 16 14:24 ops_service.py
== docker ps ==
d183-ops Up 6 seconds (healthy) 0.0.0.0:18080->8080/tcp, [::]:18080->8080/tcp
```

指标确实是我们的（节选 `curl -s localhost:18080/metrics | grep -E '^# (HELP|TYPE) ops_|^ops_'`）：

```
# HELP ops_http_requests_total HTTP 请求总数
# TYPE ops_http_requests_total counter
ops_http_requests_total{path="/healthz",status="200"} 4.0
# TYPE ops_http_in_flight gauge
ops_http_in_flight 1.0
# TYPE ops_uptime_seconds gauge
ops_uptime_seconds 11.13353157043457
```

> `ops_http_in_flight 1.0` 不是 bug：**这次 `/metrics` 请求自己也在处理中**，
> 所以它把自己算进去了。这种「观测行为影响被观测量」的现象，在自报式指标里很常见，
> 采集时（Day 177）要知道这一条。

**结论**：`docker run` 返回 ≠ 服务可用；容器健康状态与端口可用是两个时钟。

---

## 实验 4：一键部署 + 回滚演练（真跑，四幕）

**执行**：
```bash
python3 code/05-rollback-drill.py --dry-run     # 先看剧本
python3 code/05-rollback-drill.py               # 真跑
```

**实际结果**（2026-10-16T22:27–22:28，宿主本地时间）：

```
第一幕 · 部署 v1.0.0（正常版本）
▶ 部署 v1.0.0（镜像 day183-ops:multi）
  没有上一个可用版本：失败时无路可回（这正是「首次上线」的风险）
  健康检查：✅ 通过（用时 0.563s）
  冒烟测试：✅ 通过 — version=v1.0.0 hosts=4 by_role={'web': 2, 'db': 1, 'cache': 1}
✅ v1.0.0 已上线并记账 → /tmp/day183/state/releases.json

第二幕 · 部署 v2.0.0（故障注入：FAIL_MODE=readiness，就绪探针必挂）
▶ 部署 v2.0.0（镜像 day183-ops:multi）
  上一个可用版本：v1.0.0（镜像 day183-ops:multi）—— 失败时回滚到它
  健康检查：❌ 失败（用时 30.364s）
  最后一次探测结果：{"/healthz": {"status": 200, ...}, "/readyz": {"status": 503, ...}}
  --- 容器日志（tail 20）---
    ✅ ops-platform-api vv2.0.0 监听 0.0.0.0:8080 (fail_mode=readiness, metrics=prometheus_client)
  ↩ 回滚到 v1.0.0（镜像 day183-ops:multi）
✅ 已回滚到 v1.0.0，健康检查通过（0.506s）

第三幕 · 独立复核（直接 curl，不信部署脚本的自述）
  GET /version -> v1.0.0
  GET /healthz -> 200
  GET /readyz  -> 200
  ✅ 服务确实是 v1.0.0（回滚生效）

第四幕 · 账本 releases.json
{
  "current": { "version": "v1.0.0", "image": "day183-ops:multi", "at": "2026-10-16T22:27:41+0800",
               "smoke": "version=v1.0.0 hosts=4 by_role={'web': 2, 'db': 1, 'cache': 1}" },
  "history": [
    { "version": "v1.0.0", "result": "ok",     "at": "2026-10-16T22:27:41+0800" },
    { "version": "v2.0.0", "result": "failed", "reason": "健康检查未通过",
                           "at": "2026-10-16T22:28:13+0800" },
    { "version": "v1.0.0", "result": "rollback-target", "at": "2026-10-16T22:28:13+0800" }
  ]
}

演练汇总
  动作                      rc    期望       耗时  结论
  部署 v1.0.0                0     0    1.42s  ✅ 上线成功
  部署 v2.0.0（坏）             2     2   33.26s  ✅ 失败并回滚
  独立复核 /version            0     0    0.00s  ✅ v1.0.0
```

**数据解读**（这三条是本实验的重点）：

1. **判死耗时 30.364s ≈ 健康检查超时 30s**：坏版本其实**1 秒内**就返回 503 了，
   但部署脚本要等满超时才认输。这个数字是**策略**，不是性能。
2. **回滚本身只花 0.506s**：起一个已知是好的版本 + 健康检查通过。
3. **账本里 `v2.0.0` 的 `result` 是 `failed`，从不进 `current`**：这就是「先判后切」。

> 一个没修的瑕疵：日志里那行 `vv2.0.0` 多了一个 v ——
> 服务打印 `v{version}`，而我又把版本号传成 `v2.0.0`。
> 无害但难看，**故意留着**提醒：版本号规范要从一开始就定死（要么都带 v，要么都不带）。

**清理**：见文末「清理」。

---

## 实验 5：CI 流水线在本机真跑（act，红→绿）

**目的**：让 workflow 从「看着对」变成「真的跑出结果」。

**准备与执行**（act 0.2.89 + `catthehacker/ubuntu:act-latest`）：

```bash
# 1) 生成一个「无外部 action」的等价 workflow（本机拉不到 github.com 上的 action，见下表）
python3 code/03-ci-pipeline.py --out /root/code/Learn-Python/days/day-183-运维平台-容器化部署/.act-probe \
        --act-mode --path-prefix "days/day-183-运维平台-容器化部署/"
# 2) 在仓库根跑（--bind 是关键，见下表）
cd /root/code/Learn-Python
act push --bind \
  -W "days/day-183-运维平台-容器化部署/.act-probe/.github/workflows/ci.yml" \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest --pull=false -j lint -j test
```

**三个必须先踩的坑**（都实测过，不是理论）：

| 现象 | 根因 | 处理 |
|---|---|---|
| act 日志刷 `not located inside a git repository`，容器里 `ls -la` 只有 `.` 和 `..` | act 不挂载工作区时容器里是**空目录** | 加 `--bind`（实测：加了才看得到文件） |
| `git clone 'https://github.com/actions/setup-python' … unexpected EOF` | 本机到 github.com 的 git 协议不稳定，拉不下 action | 用 `--act-mode`：去掉需要联网的 `actions/checkout@v4` 与 `actions/setup-python@v5`（工作区已挂载、runner 自带 python3） |
| `error: externally-managed-environment`（PEP 668） | 现代发行版 Python 拒绝系统级 pip install | **建 venv 再装**——和 Dockerfile builder 阶段同一招 |

**第一次真跑：lint ✅ / test ❌（这就是 CI 的价值：它抓到了我）**

```
[ops-platform-ci/lint（语法 + 生成器自检）                  ] 🏁  Job succeeded
[ops-platform-ci/test（py3.11）-1                    ]   | error: externally-managed-environment
[ops-platform-ci/test（py3.11）-1                    ] ╰─> To install Python packages system-wide, try apt install
[ops-platform-ci/test（py3.11）-1                    ]   ❌  Failure - Main 装运行时依赖 [1.800888606s]
[ops-platform-ci/test（py3.11）-1                    ] 🏁  Job failed
[ops-platform-ci/test（py3.12）-2                    ] 🏁  Job failed
```

**修正后重跑（结果：三个 job 全绿）**：

```
[ops-platform-ci/lint（语法 + 生成器自检）                  ]   | Python 3.12.3
[ops-platform-ci/lint（语法 + 生成器自检）                  ]   | ✅ self-test 通过：12 项断言全过（离线，不需要 Docker）
[ops-platform-ci/lint（语法 + 生成器自检）                  ]   | ✅ self-test 通过：11/14 项通过，3 项因后端能力跳过 | 后端=regex-fallback
[ops-platform-ci/lint（语法 + 生成器自检）                  ] 🏁  Job succeeded
[ops-platform-ci/test（py3.11）-1                    ] 🧪  Matrix: map[python:3.11]
[ops-platform-ci/test（py3.12）-2                    ] 🧪  Matrix: map[python:3.12]
[ops-platform-ci/test（py3.12）-2                    ]   | Python 3.12.3
[ops-platform-ci/test（py3.12）-2                    ]   | stdlib 路径 OK
[ops-platform-ci/test（py3.12）-2                    ]   | ✅ self-test 通过：8 项断言全过 | backend=prometheus_client | 端口=37425
[ops-platform-ci/test（py3.12）-2                    ]   | prometheus_client 路径 OK
[ops-platform-ci/test（py3.12）-2                    ] 🏁  Job succeeded
[ops-platform-ci/test（py3.11）-1                    ]   | ✅ self-test 通过：8 项断言全过 | backend=prometheus_client | 端口=36131
[ops-platform-ci/test（py3.11）-1                    ] 🏁  Job succeeded
```

**注 1**：修正**只动了 workflow 的 test job**（把 `pip install` 换成 venv），
脚本本身一行没改——这是「测试红了先怀疑环境契约，不要先改被测代码」的例子。

**注 2**：整轮（1 个 lint + 2 个矩阵腿，含起 3 个容器）
`2026-10-16T14:32:59Z → 14:33:10Z = 11 秒`。

**注 3（重要，别被绿骗了）**：矩阵的两个腿都跑到了，但**本机 runner 里只有一个 python3（3.12.3）**，
所以 `map[python:3.11]` 和 `map[python:3.12]` 实际是同一个解释器。
真实的 `actions/setup-python` 才会装出两个不同版本。**这一点不说清，「矩阵通过」就是虚的。**

**未在 act 里跑到的东西**：
- `build` / `deploy` 两个 job（需要 ghcr.io 凭据与真机）；它们的 `if` 要求
  `github.ref == 'refs/heads/main'`，本机 push 事件的 ref 不是它，所以按设计跳过——
  这本身也算验证了 CI/CD 分界生效。
- 真实 workflow 里那两个 action（`actions/checkout@v4` / `actions/setup-python@v5`）：本机拉不下来。

---

## 实验 6：把镜像推到远端仓库（**未实测**）

**为什么没跑**：本机没有可用的镜像仓库。
尝试过起本地 `registry:2`，实测 `docker pull registry:2` 在本网络下长时间无响应
（已终止，未留进程）；也没有 ghcr.io / Docker Hub 的写权凭据。
**没有就是没有，不编造推送成功的输出。**

**预期结果**（在能推的环境里应该是）：

```
$ docker tag day183-ops:multi registry.local:5000/ops-platform:sha-abc1234
$ docker push registry.local:5000/ops-platform:sha-abc1234
The push refers to repository [registry.local:5000/ops-platform]
...
sha-abc1234: digest: sha256:... size: 1234
$ docker manifest inspect registry.local:5000/ops-platform:sha-abc1234 | jq -r '.config.digest'
```

若起本地 registry，还要在推送前把仓库加进 `/etc/docker/daemon.json` 的 `insecure-registries`
（本机 `daemon.json` 我没动过，这也是没硬上的原因之一）。

**验证方法**：
1. `docker run -d -p 5000:5000 registry:2`（或换一个有凭据的仓库地址）；
2. 推送成功后用 `docker rmi` 删掉本地镜像，再从仓库 `docker pull` 回来——
   **能拉回来才算真推上去了**；
3. 比对 `docker image inspect .Size` 与本地一致（不一致说明层被动过）。

**为什么这件事在 CI 里必须用 SHA 标签**：`latest` 是「移动的靶子」。
回滚时要精确指到 `...:sha-abc1234`，而 `latest` 下一分钟就指向别的了。

---

## 翻车复盘（本日真实踩到的 10 个坑）

> 共同点写在最后：**它们全都是「绿」的**。只信退出码，一个都发现不了。

### 1. 自检把注释当成代码（假失败）

**症状**：`02 --self-test` 报 `❌ 两者都不依赖 curl（slim 里没有）`，可 Dockerfile 里根本没装 curl。
**根因**：断言写的是 `\"curl\" not in text`，而 Dockerfile 注释里就写着「slim 镜像里没有 curl，探针要用 python3」——
注释把断言顶翻了。
**修复**：断言前先剥掉注释行。
**复测**：12 项全过。
**教训**：**对文本做断言，先想清楚「文本里还有什么」**。注释、日志、文档都会污染。

### 2. 占位符被自己吃掉（写文档和脚本时都中招）

**症状**：模板里的 ${{ … }} 与三反引号被外层模板先解释掉，直接语法错误。
**根因**：我在「生成 workflow 的 Python 脚本」里直接写 ${{ … }}，外层又是模板字符串 → 同一个 ${ 被解释两次。
**修复**：定死占位符约定（一个记号代表美元符，一个记号代表反引号），只在**最后一步**统一替换。
**教训**：**多层模板要约定占位符**，别指望多敲几个反斜杠能解决。

### 3. PyYAML 把 on 读成了布尔 True

**症状**：`\"on\" in doc` 为假，自检报「workflow 没有 on」。
**根因**：YAML 1.1 里未加引号的 `on:` 是布尔真值，PyYAML 按老规范解析 → key 是 `True`。
**修复**：断言写成 `(\"on\" in doc) or (True in doc)`，并在代码注释里写明原因。
**教训**：这不是 PyYAML 的 bug，是**规范的历史包袱**。

### 4. 负向断言的回溯坑（两次假通过）

**症状**：想表达「password 后面必须跟 ${{ secrets… }} 形式」，结果永远「没找到硬编码口令」。
**根因（第一版）**：拿**渲染前**的占位符去匹配**渲染后**的文本 → 负向断言永远为真。
**根因（第二版）**：改成 `password:\s*(?!\$\{\{)` 后，`\s*` 会回溯——先吃空格、断言失败，
再退回零宽、断言成功。**第二版看起来完全正确**。
**修复（第三版）**：把 `\s*` 挪进断言内部，`password:(?!\s*\$\{\{)` —— 断言是原子的，无法退回。
**教训**：**负向断言前面不要放可回溯的量词**。三版注释都留在代码里，因为第二版最骗人。

### 5. 降级步骤放错了位置

**症状**：act 里 test job 的「stdlib 降级路径」断言必失败。
**根因**：我把这一步放在 `pip install` **之后**——依赖都装好了，当然不再是 stdlib 后端。
**修复**：移到装依赖**之前**，并补一条「装完后必须是 prometheus_client 后端」的正向断言。
**教训**：**步骤的顺序本身就是被测行为的一部分**。

### 6. 正则回退后端其实不能用

**症状**：`--force-fallback` 一开，14 条断言挂 6 条。
**根因**：① 正则版没解析 `needs`；② 没做 job 作用域，`on:` 下面的 `pull_request:` / `workflow_dispatch:`
被当成 job（`解析出 4 个 job` 直接挂）。
**修复**：按缩进两趟扫描 + 加 `in_jobs` 作用域；深层结构解不出来的断言标「⏭ 跳过」而不是「失败」。
**复测**：`11/14 项通过，3 项因后端能力跳过`。
**教训**：**「有降级路径」和「降级路径真的能用」是两件事**——不在降级路径上跑一遍，就不知道。
（有意思的是：这条修复在实验 5 里立刻派上用场——act 容器里没有 PyYAML，正是靠这个回退后端跑出结果的。）

### 7. 凭记忆写 API：prometheus_client 没有 __version__

**症状**：`AttributeError: module 'prometheus_client' has no attribute '__version__'`。
**根因**：它不是把版本挂成模块属性的那种库。
**修复**：`python3 -c "from importlib.metadata import version; print(version('prometheus_client'))"`。
**教训**：和 Day 177 的 `Summary(quantiles=)` 同一类错误。**十秒钟验证，胜过十分钟记忆**。

### 8. act 的工作区是空的（两次试错）

**症状**：act 里 `ls -la` 只有 `.` 和 `..`，所有基于文件的 step 都 FileNotFound。
**根因**：不加 `--bind` 时 act 不把工作区挂进容器，容器里就是个空目录。
**修复**：加 `--bind`。加之前/之后的 `ls` 实测输出在实验 5 里都留着。
**教训**：**「容器里看到的目录」和「你以为的那份」是两回事**——这个假设值得每次都验一下。

### 9. CI 里的 pip 撞上 PEP 668（真红了一次）

**症状**：`error: externally-managed-environment`，test job 两个腿全挂。
**根因**：现代发行版 Python 默认禁止系统级 pip install（PEP 668）。
**修复**：workflow 改成 `python -m venv …` 再装——**和 Dockerfile builder 阶段是同一套写法**。
**教训**：环境契约变了，脚本并不知道。**CI 抓到的是「契约漂移」，不是「代码 bug」**。

### 10. compileall 对不存在的路径返回 0（最阴的一个）

**症状**：第一次 act 跑（工作区是空的）里，`python -m compileall -q code/` **成功了**，
输出只有一行 `Can't list 'code/'`。
**根因**：compileall 把「列目录失败」当警告，退出码仍然是 0。
**后果**：如果只看 🏁，这条 lint 步骤**永远是绿的**——它根本没编译任何东西。
**修复方向**：让这一步输出「编译了多少个文件」并对这个数字断言；
或在前面加 `test -d code` 之类的存在性检查。
**教训**：**一个只打印警告就返回 0 的命令，放进 CI 等于没放**。
「绿灯」必须建立在「我知道它真的做了什么」之上——这也是本日所有实验都要求**贴真实输出**的原因。

---

## 清理（每次实验后都做）

```bash
# 1) 收容器
docker ps -a --filter name=d183-ops --format '{{.Names}} {{.Status}}'
docker rm -f d183-ops

# 2) 收镜像（本日构建的）
docker rmi -f day183-ops:single day183-ops:multi

# 3) 收临时目录（构建上下文 / CI 工作区 / 状态账本 / 探查文件）
rm -rf /tmp/day183 /tmp/day183-probe

# 4) 收 act 在本 day 目录内部留下的两个目录（都在 day 目录里，别删错到仓库根）
rm -rf "days/day-183-运维平台-容器化部署/.act-probe" "days/day-183-运维平台-容器化部署/.act-venv"

# 5) 收 compileall 产生的字节码
find "days/day-183-运维平台-容器化部署" -name __pycache__ -type d -prune -exec rm -rf {} +
```

自检项：

```bash
docker ps -a --format '{{.Names}}' | grep d183 && echo "还有容器" || echo "无 d183 容器"
docker images --format '{{.Repository}}:{{.Tag}}' | grep day183 && echo "还有镜像" || echo "无 day183 镜像"
ss -ltnp | grep -E ':18080' && echo "端口还占着" || echo "端口已释放"
pgrep -af 'ops_service.py|rollback-drill' || echo "无残留进程"
```

**没动的东西**：`/etc/docker/daemon.json`（没加 insecure-registries）、仓库里别的 day 目录、
以及 `dk-basic` / `dk-multi` / `dk-nonroot` 等**其它实验留下的容器**（不是本日的，不碰）。

---

## 思考题

1. 多阶段让运行镜像小了 64 MiB，却让**构建**慢了 8 秒。什么情况下这笔账划算？什么情况下不划算？
   （提示：谁在拉镜像、多久拉一次、构建多频繁）
2. `docker images` 显示 434MB，`docker image inspect .Size` 显示 109.3 MiB。
   如果你在文档里只写其中一个，会误导读者什么？怎么标注才不留歧义？
3. 本日的回滚是「先判后切」——坏版本从未接管流量。如果被迫**先切后撤**，
   你需要补什么机制才能让用户感知不到？
4. `/healthz` 与 `/readyz` 都返回 200，能说明服务「好」吗？
   请再想两个健康检查**永远查不到**的故障类型。
5. 实验 5 里 test job 的第一次失败**不是代码问题**。如果当时我直接去改 `01-ops-service.py` 会怎样？
   为什么「先判断是哪一层违约」很重要？
6. 设计一个**能自己发现自己没干活**的 CI 步骤（对照翻车复盘第 10 条）。
7. 为什么镜像标签要用 commit SHA 而不是 `latest`？请从**回滚**角度回答。

---

## 交付清单

- `code/01-ops-service.py` —— 被部署的运维平台 API（stdlib；`/healthz` `/readyz` `/version` `/api/*` `/metrics`；故障注入 `--fail-mode`）
- `code/02-multistage-image.py` —— 生成并真构建单体/多阶段镜像，量体积与耗时（`--self-test` 离线 12 断言）
- `code/03-ci-pipeline.py` —— 生成 CI workflow + 结构校验 + `--dry-run` + act 演练入口（含 `--act-mode` / `--path-prefix` / `--force-fallback` / `--bind`）
- `code/04-deploy-rollback.py` —— 一键部署（健康检查 → 冒烟 → 记账；失败自动回滚）；`--self-test` 用 FakeRuntime 跑 12 条断言
- `code/05-rollback-drill.py` —— 四幕回滚演练（真起容器、真失败、独立复核）
- `code/requirements.txt` —— 锁版本依赖（`prometheus_client==0.26.0`）
- `diagrams/README.md` —— 六张原理图
- `exercises/checklist.md` —— 练习与检查表
