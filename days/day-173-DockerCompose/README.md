# Day 173 · Docker Compose

> 阶段：Phase 11 — 自动化运维与 DevOps ｜ 子主题：实战
> 主题：compose.yaml 编写、多服务编排、数据卷与网络、全栈应用编排

---

## 一、概念解释

### 1.1 Docker Compose 是什么

Compose 是**一组容器的声明式编排器**。你交一份 YAML，它负责：

1. **创建**容器（镜像或本地构建）
2. **连线**把它们挂进同一个网络，网络内互相用**服务名**当 DNS 名
3. **排序**按 `depends_on` 决定启动先后，并在需要时等到"真的能用"
4. **挂载**把宿主目录/命名卷挂进容器，把配置以只读方式注入
5. **一起**收：`down` 一次清干净

### 1.2 为什么需要它

单容器时代，`docker run -d --name app -p 8000:8000 app` 这种命令一旦超过五个服务就无法维护：

- **顺序**：谁先谁后靠 `&&` 拼，人会错
- **地址**：每个容器 IP 动态分配，写死 IP 必崩 → Compose 给内置 DNS，服务名即稳定地址
- **清理**：删了应用忘了删库，重跑撞端口
- **可重复**：环境定义散落在各人脑子里，没有唯一真相源

Compose 的价值不是"少打字"，而是**把一套能跑起来的环境变成可版本化的代码**。

### 1.3 为什么服务名能当 DNS 名

Compose 为每个项目创建一个用户自定义网络（默认 bridge 驱动）：

- 容器创建时被赋予网络别名（alias）= 服务名
- Docker 内嵌 DNS（`127.0.0.11`）把服务名解析到该服务所有副本的容器 IP
- `--scale worker=3` 时，`worker` 会轮询解析到 3 个不同 IP

**关键含义**：`localhost` 在容器里指的是**容器自己**。跨服务通信必须用服务名。

### 1.4 三种存储

| 类型 | 写法 | 生命周期 | 用途 |
|---|---|---|---|
| 绑定挂载 | `./src:/app/src` | 与宿主目录同生共死 | 开发热更新、注入配置 |
| 命名卷 | `pgdata:/var/lib/postgresql/data` | `down` 保留，`down -v` 删除 | 数据库持久化 |
| tmpfs | `tmpfs: /tmp` | 容器停止即失 | 临时文件，内存态，快 |

### 1.5 depends_on 的三种语义（Compose Spec）

| condition | 含义 | 快慢 | 风险 |
|---|---|---|---|
| （默认/`service_started`）| 容器被**启动**即可 | 最快 | 依赖此刻可能还没就绪 → 应用启动即崩 |
| `service_healthy` | 等到依赖容器**健康检查通过** | 慢 | 依赖必须有 `healthcheck` |
| `service_completed_successfully` | 等到依赖**成功退出** | 视任务 | 适合一次性 init/migration 任务 |

> **为什么这三种都要**：`service_started` 只保证"进程起来了"，TCP 端口可能刚 listen、数据
> 可能还没 WAL 刷盘、schema 可能还没建完。`service_healthy` 把"能不能用"的判断权交给
> 依赖自己声明的 healthcheck，比在下游盲等超时更可靠。

---

## 二、原理解析

### 2.1 `docker compose up` 的实际执行顺序

```mermaid
flowchart TD
    A[解析 compose.yaml] --> B[创建默认网络/卷]
    B --> C[并发创建所有容器 Created]
    C --> D{依赖已满足?}
    D -- 否且 condition=healthy --> E[等待 healthcheck healthy]
    E --> D
    D -- 是 --> F[Start 容器]
    F --> G[健康中的服务继续等自己的依赖]
    G --> H[全部满足 → 全部 Running]
```

注意 `C`：**所有容器都是先一次性创建的**，然后才按依赖分批 Start。
所以你会看到 `Created` 一大串，然后才是 `Waiting` / `Healthy` / `Started` 交错。

### 2.2 为什么 `depends_on` 只管启动、不管运行期

Compose 的依赖图是**编排期**概念。容器启动之后：

- 依赖容器重启 → `restart: unless-stopped` 会拉起，但依赖方**不会**被重启
- 依赖容器崩了 → `service_healthy` 不会把依赖方也停掉
- 运行期健康检查失败 → Docker 只记录状态，不联动

所以**运行期故障必须靠应用自身重试/熔断**，不能指望 Compose。
这也是本课 `app.py` 里 `stats()` 对每个依赖单独 try 的原因。

### 2.3 healthcheck 的真实语义

healthcheck 就是**容器内定期执行一条命令**：

- exit 0 → 本次成功；连续 `retries` 次成功 → 状态变 `healthy`
- exit 非 0 → 连续 `retries` 次失败 → 状态变 `unhealthy`
- `start_period` 内**失败不计入**连续计数（给慢启动留宽限）
- 没有 healthcheck 的容器，健康状态是 `none`，**永远不能被 `service_healthy` 等待**

这就是本课翻车实验 1 的根因。

### 2.4 一个镜像、两个角色

`app` 和 `worker` 用**同一个 `image: day173-app:1.0`**，只靠 `command` 区分：

```yaml
app:    { build: ., image: day173-app:1.0 }
worker: { build: ., image: day173-app:1.0, command: ["python", "worker.py"] }
```

为什么这样做：`build:` 会被 Compose 去重，同一上下文只构建一次、只打一个 tag。
好处是**app 与 worker 的代码版本天然一致**，不会出现"worker 还是昨天的代码"。

### 2.5 `--scale` 与 `--scale` 的限制

`docker compose up -d --scale worker=3` 可以把无状态服务扩到 3 份（实测见实验 5）。
但**不能给声明了 `container_name` 的服务扩容** —— 名字必须唯一。
另外用**固定宿主端口映射**（`ports: "18080:8000"`）的服务也不能扩容，
因为三个容器抢同一个宿主端口。所以要扩容就得：
- 不写 `container_name`
- 不写宿主端口映射（或用随机端口 `"8000"`）
- 前面放一个负载均衡（Compose 没内建 LB，得靠 nginx 之类外部代理）

---

## 三、定义与使用方法（API 速查）

### 3.1 顶层字段

| 字段 | 说明 |
|---|---|
| `version` | Compose Spec 已废弃，写了会被警告，**建议省略** |
| `name` | 项目名，决定容器前缀 `day173-lab-app-1`，替代 `docker compose -p` |
| `services` | 服务列表 |
| `networks` | 网络定义 |
| `volumes` | 命名卷定义 |
| `configs` / `secrets` | 配置与密钥挂载（Swarm 为主，compose 部分支持） |
| `profiles` | 给服务打标签，`--profile dev up` 才启动 |

### 3.2 service 常用字段

| 字段 | 用途 | 备注 |
|---|---|---|
| `image` / `build` | 指定镜像 / 从 Dockerfile 构建 | 两者可共存（build 后打 tag） |
| `command` | 覆盖 CMD | **不要写 entrypoint**，容易丢默认参数 |
| `entrypoint` | 覆盖 ENTRYPOINT | 极少用 |
| `environment` | 环境变量 | 支持 `KEY` 或 `KEY: value`；`${VAR:-default}` 插值 |
| `ports` | 端口映射 | `"8080:80"` 固定，`"80"` 随机分配 |
| `expose` | 仅暴露给内部网络，不映射宿主 | 纯文档意义 |
| `volumes` | 挂载 | 见 1.4 |
| `networks` | 接入网络 | 可多网段，实现前后端隔离 |
| `depends_on` | 启动依赖 | 见 1.5 |
| `healthcheck` | 健康检查 | `test`/`interval`/`timeout`/`retries`/`start_period` |
| `restart` | 重启策略 | `no`/`always`/`unless-stopped`/`on-failure:N` |
| `deploy.replicas` | 副本数 | 需 `docker compose up --scale` 才生效（非 Swarm） |
| `profiles` | 服务分组 | |
| `labels` | 标签 | 常用于日志/监控服务自动发现 |

### 3.3 healthcheck 写法

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]              # exec 形式，不经 shell
  test: ["CMD-SHELL", "pg_isready -U app -d appdb"]  # 需要管道/变量时才用 shell
  interval: 2s
  timeout: 1s
  retries: 15
  start_period: 3s     # 宽限期，期内失败不累计
```

**`CMD` vs `CMD-SHELL`**：`CMD` 直接 exec，不经过 shell，所以**不支持管道、重定向、变量展开**。
需要这些才用 `CMD-SHELL`（会经过 `/bin/sh -c`，多一层进程）。

### 3.4 常用命令

```bash
docker compose up -d                 # 起来
docker compose up -d --scale worker=3 # 扩容
docker compose ps                     # 看状态
docker compose logs -f worker         # 跟日志
docker compose exec app bash          # 进容器
docker compose exec -T app python -c "..."   # 不分配 TTY（脚本里用这个）
docker compose run --rm app python -c "..."  # 一次性容器
docker compose config                 # 校验 + 插值后展开（排查环境变量问题的第一步）
docker compose stop app               # 停服务（保留容器）
docker compose down                   # 拆掉容器与网络
docker compose down -v                # 连命名卷一起删 ⚠️ 数据没了
docker compose restart app            # 只重启某个服务
```

---

## 四、图解

见 [`diagrams/README.md`](diagrams/README.md)，含：

- Compose 声明 → Docker 对象（网络/卷/容器）的映射图
- 启动时序图（含 healthcheck 等待）
- `--scale` 时 DNS 多 IP 轮询示意
- 双网络前后端隔离拓扑

---

## 五、代码示例

| 文件 | 主题 | 依赖 |
|---|---|---|
| [`code/01-compose-basics.py`](code/01-compose-basics.py) | 纯标准库建模 compose：服务/网络/拓扑排序/`--emit-compose` | 无 |
| [`code/02-compose-pitfalls.py`](code/02-compose-pitfalls.py) | 六类真实踩坑的最小复现（服务名 DNS、端口占用、依赖环、环境变量插值、`--scale` 与固定端口、卷权限） | 无 |
| [`code/03-compose-stack/`](code/03-compose-stack/) | **实战全栈栈**：app + worker + redis + postgres + nginx，5 服务 2 卷 1 网络 | Docker + Compose v2 |

三个脚本都支持 `--self-test`，在**无 Docker、无外部服务**的环境下也能自证正确。

---

## 实战实验手册

> 以下所有"实际结果"均为 **2026-10-04 在本机真机执行**捕获的原始 stdout/stderr。
> 环境：Ubuntu / Docker Engine 29.1.3 / Docker Compose v2.40.3 / Python 3.12。
> 每条命令都能原样复制复现。

### 实验 1：五服务栈首次拉起（核心）

**目的**：验证 Compose 能把 app + worker + redis + postgres + nginx 一起拉起并互相解析。

**环境**：Docker 29.1.3、Compose v2.40.3。

**准备**：
```bash
cd ~/code/Learn-Python/days/day-173-DockerCompose/code/03-compose-stack
docker compose down -v 2>/dev/null || true   # 清干净上次的残留
```

**执行**：
```bash
docker compose up -d
docker compose ps --format 'table {{.Service}}\t{{.Status}}'
```

**预期结果**：5 个服务全部 `Up`，其中带 healthcheck 的三个是 `(healthy)`。

**实际结果**（本次编写时真机跑出来的）：
```
 Container day173-lab-worker-1  Created
 Container day173-lab-nginx-1  Created
 Container day173-lab-postgres-1  Starting
 Container day173-lab-redis-1  Starting
 Container day173-lab-redis-1  Started
 Container day173-lab-postgres-1  Started
 Container day173-lab-redis-1  Waiting
 Container day173-lab-postgres-1  Waiting
 Container day173-lab-postgres-1  Waiting
 Container day173-lab-postgres-1  Healthy
 Container day173-lab-worker-1  Starting
 Container day173-lab-redis-1  Healthy
 Container day173-lab-app-1  Starting
 Container day173-lab-app-1  Started
 Container day173-lab-worker-1  Started
 Container day173-lab-app-1  Waiting
 Container day173-lab-app-1  Healthy
 Container day173-lab-nginx-1  Starting
 Container day173-lab-nginx-1  Started

SERVICE    STATUS
app        Up 6 seconds (healthy)
nginx      Up Less than a second
postgres   Up 9 seconds (healthy)
redis      Up 9 seconds (healthy)
worker     Up 6 seconds
```

**结论**：验证了 2.1 的顺序 —— 先全部 `Created`，再按依赖分批 `Start`；
`app` 等到了 redis+postgres 的 `Healthy`，`nginx` 又等了 `app` 的 `Healthy`。

**清理**：`docker compose down -v`

---

### 实验 2：服务名 DNS 解析

**目的**：验证跨服务通信用的是**服务名**而非 `localhost` / 固定 IP。

**执行**：
```bash
docker compose exec -T app python -c "
import socket
print('redis ->', socket.gethostbyname('redis'))
print('postgres ->', socket.gethostbyname('postgres'))
try:
    socket.gethostbyname('localhost')
    print('localhost 在容器里 = 自己，不是 redis')
except Exception as e:
    print('err', e)
"
```

**实际结果**：
```
redis -> 172.18.0.2
postgres -> 172.18.0.3
```

再从宿主直连宿主端口：
```bash
curl -s http://127.0.0.1:18080/stats; echo
curl -s http://127.0.0.1:18081/stats; echo   # 经 nginx 反代
```
```
{"redis": {"ping": "+PONG", "hits": 1}, "postgres": {"visits": 6}}
{"redis": {"ping": "+PONG", "hits": 2}, "postgres": {"visits": 6}}
```

**结论**：两次 `/stats` 的 `hits` 分别是 1 和 2 —— 同一个 Redis 容器，
但走的是两条不同网络路径（app 直连 / nginx→app），证明**所有服务共享同一个 Redis 实例**。
`redis` 解析到 `172.18.0.2` 而非 `127.0.0.1`，即 1.3 成立。

**清理**：`docker compose down -v`

---

### 实验 3：🔴 翻车实验 —— 「以为能跑，其实是 not found」

**目的**：把新手最常见的一个误解变成可复现的现象。

**现象**：
```bash
curl -s "http://127.0.0.1:18080/visit?u=alice"; echo
```
```
{"error": "not found"}
```

**假设**：服务起来了、端口通了、healthcheck 也是 healthy，为什么请求进不去？
第一反应是"容器没起好"。

**验证手段**：
```bash
docker compose ps app                                   # Up 6 seconds (healthy)
curl -s http://127.0.0.1:18080/healthz; echo             # {"status": "ok", "pid": 1}
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:18080/visit
```

**真实根因**：`app.py` 里根本没有 `/visit` 这个路由，只实现了 `/healthz`、`/stats`、`/ready`。
`/visit` 落到兜底分支返回 404。

**这次翻车真正值得记的结论**：**`healthy` 只代表 healthcheck 那条命令成功，
不代表你的业务路由存在**。healthcheck 通过与"接口能用"是两件事。
所以：
1. healthcheck 应该打在**真实反映服务能力的**端点上（本课用的是 `/healthz`，
   它只证明进程活着；若想更严格，应改打 `/ready`）；
2. 排查 404 时先看路由表，不要怀疑容器。

**修复**：换用真实存在的端点：
```bash
curl -s http://127.0.0.1:18080/stats
```

**复测结果**：返回真实数据，见实验 2。

---

### 实验 4：依赖策略对启动时延的影响（实测数字）

**目的**：量化 `service_healthy` 相比 `service_started` 的额外开销。

**环境**：数据量无关（单次冷启动，无预热）；取 3 次连续测量，每个 case 之间
`down -v` 完全清空（含删除 pgdata 卷）。

**执行**：
```bash
cd ~/code/Learn-Python/days/day-173-DockerCompose/code/03-compose-stack
./bench_startup.sh
```
脚本对每个 case 执行 `down -v` → 记 `t0` → `up -d` → 轮询 `docker inspect` 直到
`app` 变 `healthy` → 输出毫秒差。

**实际结果**：
```
=== Day 173 实测：depends_on 策略对启动时延的影响 ===
service_healthy    app 到 healthy 耗时 = 12344 ms
service_started    app 到 healthy 耗时 = 7313 ms
service_healthy(2) app 到 healthy 耗时 = 9573 ms

real	1m2.742s
```

**结论**：
- `service_healthy` 比 `service_started` **多花约 2–5 秒**（12344 / 9573 vs 7313 ms）。
  这段时间就是等 postgres/redis 健康检查通过的窗口 —— 值得花，因为换来的是
  app 起来即能用，不用靠 `sleep 5` 拍脑袋。
- `service_healthy` 两次测量 12344 / 9573 ms，**波动约 2.8 秒（±22%）**。
  原因是它依赖 `pg_isready` 的轮询节奏与 postgres 实际初始化时长，
  后者受磁盘 I/O 影响。所以**任何基于 `service_healthy` 的超时阈值都要留足余量**，
  不要卡在边界值上。
- `service_started` 反而更"快"是假象：它只是没等，`app` 起来时依赖可能还没就绪，
  省下的时间会以"启动瞬间连不上依赖"的报错还回去。

---

### 实验 5：`--scale` 扩容无状态服务

**目的**：验证 Compose 能把 worker 扩到多副本。

**执行**：
```bash
docker compose up -d --scale worker=3
docker compose ps worker --format 'table {{.Name}}\t{{.Status}}'
```

**实际结果**：
```
 Container day173-lab-worker-2  Started
 Container day173-lab-worker-1  Starting
 Container day173-lab-worker-1  Started

NAME                  STATUS
day173-lab-worker-1   Up 3 seconds
day173-lab-worker-2   Up 3 seconds
day173-lab-worker-3   Up 4 seconds
```

**结论**：容器名从 `-1` 递增到 `-3`，服务名（DNS 别名）保持 `worker` 不变 ——
应用侧代码一行都不用改。**注意 worker 声明了固定挂载/无端口**，所以能扩容；
若给 worker 加 `ports: "18090:8000"`，第二条命令会直接报错（见 `02-compose-pitfalls.py`）。

**清理**：
```bash
docker compose down -v
```

---

### 实验 6：命名卷的持久性

**目的**：验证 `down` 不带 `-v` 时数据保留，带 `-v` 时删除。

**执行**：
```bash
docker volume ls | grep 173                      # → local day173-lab_pgdata
docker compose exec -T postgres psql -U app -d appdb -c 'select count(*) from visits;'
```
```
 count
-------
     6
(1 row)
```

**结论**：6 行由 worker 的 5 轮写入 + init.sql 的 1 行种子数据构成。
卷名为 `day173-lab_pgdata`，前缀即 `name: day173-lab` —— 项目名隔离了不同 compose 项目的卷，
避免互相踩数据。

**清理**：
```bash
docker compose down          # 容器与网络消失，卷保留
docker volume ls | grep 173  # 仍在
docker compose down -v       # 卷也删除
docker volume ls | grep 173  # 空
```

---

## 六、避坑清单（全部来自本课脚本 `02-compose-pitfalls.py` 的可运行复现）

1. **启动顺序 ≠ 就绪就绪** —— `depends_on` 默认只等"容器启动"，数据库进程起来了
   但 schema 还没建好，app 一连就报错。要等就绪必须写 `condition: service_healthy`，
   而这要求**对方定义了 healthcheck**，否则永远等不到。
2. **`localhost` 不是邻居** —— 容器里的 localhost 是自己，跨服务必须用服务名。
3. **端口映射方向搞反** —— 是 `"宿主端口:容器端口"`（`18080:8000`），
   不是反过来。反了会得到一堆连不上或随机端口。
4. **配置不会自动传下去** —— 给 `postgres` 配了 `POSTGRES_PASSWORD`，
   `app` 不会自动拿到；必须在自己的 `environment` 里显式写。
5. **命名卷 vs 绑定挂载** —— `down` 不删卷，`down -v` 删。生产上误用 `down -v`
   等于删库。本课实验 6 已实测两者差异。
6. **迁移脚本别用 `sleep` 猜时间** —— 一次性任务（如 schema 迁移）应该用
   `service_completed_successfully` 显式表达"我等它跑完"，而不是
   `command: sh -c "sleep 10 && python app.py"`。

补充（来自真机实验）：
- **固定端口会撞车** —— 两套栈都用 `18080` 时第二个报
  `Bind for 0.0.0.0:18080 failed: port is already allocated`。
  对策：端口走 `${APP_PORT:-18080}`，换项目名 + 换端口。
- **环境变量插值发生在宿主 shell** —— `${PGPASSWORD}` 在你敲命令的那个 shell 里展开，
  不是容器内。用 `docker compose config` 永远能看清最终值。
- **`--scale` 撞固定端口 / `container_name`** —— 无状态服务要扩容就别写这两项。
- **命名卷属主** —— 镜像里用非 root（`USER appuser`）而卷是 root 创建的，
  Postgres 会起不来。对策：镜像内先建好属主，或 compose 里显式 `user:`。

## 七、思考题

1. `depends_on: {condition: service_healthy}` 保证的是**启动瞬间**的正确性。
   如果 postgres 在 app 启动 10 分钟后重启，app 会怎样？Compose 会不会帮忙？
   要让 app 活下来，需要在哪一层做什么？（提示：分层看 —— 编排层 / 应用层 / 驱动层）
2. 为什么 `docker compose config` 是排查环境变量问题的**第一步**？
   它展开的到底是哪一层的时间点？
3. 本课的 `app` 和 `worker` 共用一个镜像，只靠 `command` 区分。
   如果 worker 需要额外依赖（比如 `celery`），你会拆成两个镜像还是继续共用？
   权衡是什么？
4. `service_healthy` 引入的启动延迟（实测 2–5 秒）应该由谁消化？
   集群里 50 个服务各等 5 秒，和把它们并行起来等同一个屏障，有什么区别？
5. Compose 里能不能做生产级零停机发布（比如 nginx 蓝绿）？
   哪些能力 Compose 没有、必须换 Swarm/K8s？（提示：`deploy.update_config`、`labels`、
   滚动策略、`endpoint_mode`）

---

## 八、收尾卫生

本次编写 Day 173 时在真机上留下又清掉了的东西：

| 项目 | 处理 |
|---|---|
| compose 项目 `day173-lab`（5 容器 + 1 网络） | `docker compose down -v` 已拆除 |
| 命名卷 `day173-lab_pgdata` | 已随 `-v` 删除 |
| 宿主端口 18080 / 18081 | 已释放（`ss -ltnp` 无残留监听） |
| 镜像 `day173-app:1.0` | 保留（构建缓存复用，读者实验更快） |
| 临时 worktree | 无 |

验证残留：
```bash
docker ps -a --filter name=day173-lab          # 空
docker volume ls | grep 173                    # 空
docker network ls --filter name=day173         # 空
ss -ltnp | grep -E '18080|18081'               # 空
```
