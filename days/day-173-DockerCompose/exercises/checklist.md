# Day 173 · Docker Compose 练习与验收清单

---

## 一、今日完成清单

- [ ] 能手写一份含 5 个服务（app / worker / redis / postgres / nginx）的 compose.yaml
- [ ] 说清 `service_started` / `service_healthy` / `service_completed_successfully` 三种依赖语义的区别
- [ ] 理解为什么容器里跨服务要用**服务名**而不是 `localhost`
- [ ] 分清绑定挂载 / 命名卷 / tmpfs 三种存储，以及 `down` 与 `down -v` 的差别
- [ ] 独立完成 `code/03-compose-stack` 的真机拉起，并解释 `docker compose up` 的输出顺序
- [ ] 用 `--scale` 扩出一个无状态服务的多副本
- [ ] 清理干净全部实验残留（容器 / 卷 / 网络 / 端口）

---

## 二、离线自证（无需 Docker，30 秒跑完）

```bash
cd ~/code/Learn-Python/days/day-173-DockerCompose/code

python3 01-compose-basics.py --self-test
# 期望：01-compose-basics self-test: PASS（5 组断言全过）

python3 02-compose-pitfalls.py --self-test
# 期望：02-compose-pitfalls self-test: PASS（4 组断言全过）

python3 01-compose-basics.py            # 看概念演示输出
python3 02-compose-pitfalls.py          # 逐条看六类坑的复现
```

应用脚本也能离线自证：

```bash
python3 03-compose-stack/app.py --self-test
python3 03-compose-stack/app.py --dry-run   # 只打印将要连接的目标，不发起连接
```

**验收标准**：三行 self-test 全部输出 `PASS`，`--dry-run` 打印出
`redis: redis:6379` / `postgres: postgres:5432`。

---

## 三、练习题

### 基础 1 — 写一份最小 compose

**要求**：写一份 `compose.yaml`，含一个 `web` 服务（`nginx:alpine`，映射 `8080:80`）
和一个 `api` 服务（`python:3.12-slim`，跑 `python -m http.server 8000`，映射 `8090:8000`），
`api` 依赖 `web`，用 `service_started`。

**验收命令**：
```bash
mkdir -p /tmp/compose-ex1 && cd /tmp/compose-ex1
# 写好 compose.yaml 后：
docker compose config          # 必须能校验通过
docker compose up -d
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8090/   # 期望 200
docker compose down
```

**思考**：从 `api` 容器内部应该怎么访问 `web`？写出来并验证。

---

### 基础 2 — 找出并修复三个错

下面这份 compose 有三个问题，逐个说明原因并修好：

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secret
  app:
    image: myapp:latest
    environment:
      DATABASE_URL: postgres://app@db:5432/appdb    # (A)
    depends_on:
      - db
    ports:
      - "8000:8000:8000"                            # (B)
```

**验收**：解释每个错误的后果，并用 `docker compose config` 与一次 `up -d` 证明修复有效。

---

### 进阶 3 — 量化 `service_healthy` 的代价

**要求**：复用 `code/03-compose-stack/`，把 `bench_startup.sh` 改成**重复 5 次**，
取每种策略的均值与极差。

**验收命令**：
```bash
cd ~/code/Learn-Python/days/day-173-DockerCompose/code/03-compose-stack
for i in 1 2 3 4 5; do ./bench_startup.sh; done
```

本课实测的 3 次采样（2026-10-04，Docker 29.1.3 / Compose v2.40.3）为：
```
service_healthy    = 12344 ms
service_started    = 7313 ms
service_healthy(2) = 9573 ms
```
你跑出的 5 次均值应落在一个相近量级。**结论要写清**：多出的 2–5 秒买到了什么？
如果换成 50 个服务各等 5 秒，这个成本会不会变成问题？

---

### 进阶 4 — 加一个一次性迁移任务

**要求**：给 `03-compose-stack` 增加一个 `migrate` 服务，跑一次建表后退出；
让 `app` 用 `condition: service_completed_successfully` 等它。

**验收命令**：
```bash
cd ~/code/Learn-Python/days/day-173-DockerCompose/code/03-compose-stack
docker compose up -d
docker compose ps -a migrate       # 期望 Exited (0)
docker compose logs migrate
curl -s http://127.0.0.1:18080/stats   # 期望 postgres 段有真实数据
docker compose down -v
```

**思考**：`restart: "no"` 这一行删掉会怎样？`depends_on` 不加条件会怎样？

---

### 挑战 5 — 自己搭一套带网络隔离的栈

**要求**：改造 `compose.yaml`，拆成 `front`（nginx + app）与 `back`（postgres + redis）
两个网络：`app` 同时接入两个网络，`postgres`/`redis` 只在 `back`，
`nginx` 只在 `front`。

**验收命令**：
```bash
docker compose up -d
docker network inspect day173-lab_back --format '{{range .Containers}}{{.Name}} {{end}}'
# 期望只出现 postgres / redis，不含 app?（app 也在 back，因为它要连它们）
# front 则只应出现 nginx / app
docker compose exec -T nginx getent hosts postgres   # 期望失败（查不到）
docker compose down -v
```

**思考**：这个拓扑挡住了什么？如果 `nginx` 被攻破，攻击者还能直连数据库吗？

---

## 四、收尾检查（每次实验后必做）

```bash
cd ~/code/Learn-Python/days/day-173-DockerCompose/code/03-compose-stack
docker compose down -v

# 全局残留检查，四条都应无输出
docker ps -a    --filter name=day173-lab --format '{{.Names}}'
docker volume ls --format '{{.Name}}' | grep 173
docker network ls --format '{{.Name}}' | grep 173
ss -ltn | grep -E '18080|18081'
```

镜像 `day173-app:1.0` 建议保留（构建缓存能显著缩短下次实验时间），
不需要时用 `docker rmi day173-app:1.0` 删除。
