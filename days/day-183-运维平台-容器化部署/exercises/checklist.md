# Day 183 · 练习与检查表

> 目标：亲手跑通「构建镜像 → 起容器 → 一键部署 → 坏版本自动回滚 → CI 在本机跑绿」这条链，
> 并亲眼看见**七个「绿着但没干活」的坑**。
> **前置**：Docker 可用；本机有 `python3`。全部命令都在 `days/day-183-运维平台-容器化部署/` 下执行。

---

## 一、动手题（必做）

### 练习 1 — 先把靶子跑起来（5 分钟）

```bash
cd days/day-183-运维平台-容器化部署
python3 code/01-ops-service.py --self-test
python3 code/01-ops-service.py --once
```

- [ ] 自检 8 项全过？注意 `backend=` 后面是什么（宿主上应该是 `stdlib-fallback`）
- [ ] `--once` 输出里 `by_role` 和 `alerts` 分别是什么？为什么 `db-01` 进了 alerts？
- [ ] 手动起服务（`--port 18080`）+ `curl -s localhost:18080/readyz`，再用
      `--fail-mode readiness` 起一次，同一个端点返回什么？状态码是多少？

<details><summary>参考答案</summary>

`by_role` = `{"web": 2, "db": 1, "cache": 1}`（按 role 计数）；
`alerts` 是 mem > 70 的主机 → `db-01`（72.4）。
`--fail-mode readiness` 时 `/readyz` 返回 **503** `{"status": "not-ready"}`，而 `/healthz` 仍是 200 ——
**「进程活着」与「能接流量」是两件事**。

</details>

### 练习 2 — 生成 Dockerfile，先别构建（10 分钟）

```bash
python3 code/02-multistage-image.py --self-test
python3 code/02-multistage-image.py --out /tmp/day183/build --write-only
cat /tmp/day183/build/Dockerfile.multi
cat /tmp/day183/build/.dockerignore
```

- [ ] `Dockerfile.multi` 里有两个 `FROM`，分别是哪两个阶段？哪个装了 gcc？
- [ ] `COPY --from=builder` 搬的是什么？为什么不是搬整个 `/build`？
- [ ] `.dockerignore` 里排掉了什么？如果漏掉 `.env`，后果是什么？
- [ ] 自检里有一条 `两者都不依赖 curl`，为什么 Dockerfile 的注释里会出现 curl 这个词？（提示：翻车复盘第 1 条）

<details><summary>参考答案</summary>

`builder` 装了 gcc，`runtime` 没有。搬到 runtime 的只有 `/opt/venv`（依赖）与 `ops_service.py`；
不搬整个 `/build` 是因为那里还有 requirements.txt、字节码等构建期残留。
漏掉 `.env` → 密钥被打进镜像，而镜像会被推到仓库、被别的主机拉走。
注释里出现 curl 是因为注释在解释「为什么探针用 python3 而不是 curl」，断言必须先剥注释再判断。

</details>

### 练习 3 — 真构建，量出差异（15 分钟，需要 Docker）

```bash
python3 code/02-multistage-image.py --out /tmp/day183/build --build both
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' | grep day183
docker image inspect day183-ops:single --format '{{.Size}}'; docker image inspect day183-ops:multi --format '{{.Size}}'
```

- [ ] 两个变体的 `inspect .Size` 各是多少？差多少（MiB 和百分比）？
- [ ] `docker images` 的 SIZE 列和 `inspect .Size` 差多少倍？你会在 README 里写哪个，怎么标注？
- [ ] 多阶段的**构建时间**是更长还是更短？为什么值这个代价？

<details><summary>参考答案</summary>

本机实测：single 114,586,798 B（≈109.3 MiB）/ multi 47,352,410 B（≈45.2 MiB），省 64.1 MiB ≈ 58.7%。
`docker images` 列在**本机 legacy builder + overlayfs** 下比 `inspect .Size` 大约 4 倍
（434MB / 196MB）——**口径不同**，写文档要标清用哪个命令测的。
多阶段构建更慢（48.73s vs 40.67s），换来的是每个部署节点少拉 64 MB。

</details>

### 练习 4 — 起容器，看「健康」的两个时钟（10 分钟）

```bash
docker run -d --name d183-ops -p 18080:8080 -e APP_VERSION=try1 day183-ops:multi
for i in $(seq 1 30); do curl -s -o /dev/null -w '%{http_code} ' localhost:18080/healthz; sleep 0.5; done; echo
docker inspect d183-ops --format '{{.State.Health.Status}}'
docker exec d183-ops sh -c 'command -v gcc || echo 没有 gcc'
```

- [ ] `curl` 第几次拿到 200？`.State.Health.Status` 什么时候变成 `healthy`？
- [ ] 两个时间差在哪？分别由 Dockerfile 里的哪几个参数决定？
- [ ] 容器里有没有 gcc？这验证了多阶段的哪一点？

<details><summary>参考答案</summary>

本机实测：第 2 次探测（0.549s）就 200；HEALTHCHECK 到第 10 次（≈5s）才 `healthy`。
差值由 `--interval` / `--start-period` / `--retries` 决定：`start-period` 内的失败不计入 retries，
所以第一次判定点落在 `interval`。
没有 gcc → 构建期工具链确实没进运行镜像。

</details>

### 练习 5 — 一键部署 + 回滚演练（20 分钟，重点）

```bash
python3 code/05-rollback-drill.py --dry-run
python3 code/05-rollback-drill.py
cat /tmp/day183/state/releases.json
```

- [ ] 第二幕的 rc 是多少？它和「失败」是一回事吗？
- [ ] 「判死耗时」和「回滚耗时」分别是多少？哪个是策略参数、哪个是性能？
- [ ] `releases.json` 里 `v2.0.0` 出现在 `current` 了吗？为什么这个区别很重要？
- [ ] 第三幕为什么必须存在？（提示：谁在自证）

<details><summary>参考答案</summary>

rc=2（**失败但已回滚**），与 rc=3（失败且无救）和 rc=0 都不同。
判死 ≈30.4s（= 健康检查超时，是**策略**）；回滚 ≈0.5s（是**性能**）。
v2.0.0 只在 `history` 且 `result: "failed"`，从不进 `current` ——
意味着它**从未接过流量**（先判后切 vs 先切后撤）。
第三幕用独立 curl 复核，因为**部署脚本的自述不能当证据**。

</details>

### 练习 6 — 让 CI 在本机跑绿（20 分钟）

```bash
python3 code/03-ci-pipeline.py --self-test
python3 code/03-ci-pipeline.py --force-fallback --self-test    # 降级后端也要过（会显示 3 项跳过）
python3 code/03-ci-pipeline.py --out /tmp/day183/ci --dry-run  # 只看会跑什么
# 真跑：见 README 实验 5（需要 --act-mode / --path-prefix / --bind 三件套）
```

- [ ] `--dry-run` 打出的拓扑序是什么？4 个 job 是并行还是串行？
- [ ] 为什么 `build` / `deploy` 在 PR 上不跑？由哪一行控制？
- [ ] `--force-fallback` 下哪几条断言被跳过？为什么是「跳过」而不是「失败」？
- [ ] 如果你把 test job 里的 venv 那步删掉、改回 `pip install -r`，会发生什么？

<details><summary>参考答案</summary>

顺序 `lint → test → build → deploy`（串行链，4 层）。
由 `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` 控制。
跳过的 3 条需要读深层结构（permissions.packages、matrix.fail-fast、steps 数量），
正则后端解不出来——**标跳过是诚实，标通过是骗人**。
删掉 venv 会撞 PEP 668：`error: externally-managed-environment`，test job 两个腿全红（实测过）。

</details>

---

## 二、判断题（对/错 + 一句话理由）

- [ ] `docker run -d` 返回 0 就说明服务已经可以接流量了。
- [ ] `EXPOSE 8080` 会把端口发布到宿主机。
- [ ] 多阶段构建之所以省空间，是因为 Docker 把中间层压缩合并了。
- [ ] `HEALTHCHECK` 可以用 `curl` 写，因为 `python:3.12-slim` 里自带 curl。
- [ ] 健康检查失败时，应该先把坏容器停掉再去收集日志。
- [ ] 镜像标签用 `latest` 就够了，反正部署脚本会记下版本号。
- [ ] CI 里某一步返回 0，就说明这一步真的干了它该干的事。

<details><summary>答案</summary>

1. ✗ 只是容器被创建了，进程可能还没绑定端口（本机实测 0.77s vs 0.549s 才可用）。
2. ✗ `EXPOSE` 只是声明；发布要靠 `-p`。
3. ✗ 没有合并——是**没搬**那些层过来。
4. ✗ slim 里没有 curl（本课实测踩过这个想当然），探针要用 `python3 -c`。
5. ✗ **先收日志**（`docker logs --tail`）再 `rm -f`，否则现场没了。
6. ✗ `latest` 是移动的靶子，回滚时无法精确指向；必须用 SHA。
7. ✗ 反例见翻车复盘第 10 条：`compileall` 对不存在的路径也返回 0。

</details>

---

## 三、排障演练

给三个现象，说出**先查什么**：

| 现象 | 你的第一步 |
|---|---|
| `docker run` 成功，但 `curl localhost:18080` 一直连不上 | |
| 镜像构建成功，但容器一启动就退出（`Exited (1)`） | |
| 部署脚本报「已回滚」，但用户说还是坏的 | |

<details><summary>参考答案</summary>

1. 先 `docker ps -a` 看状态（是不是 `Exited`），再 `docker logs`；
   若 Up 但连不上 → 看 `-p` 是否写对、服务是否绑 `0.0.0.0`（绑 `127.0.0.1` 时宿主访问不到）。
2. `docker logs <name>` 看退出原因；最常见是 `CMD` 里的路径/入口写错——
   **构建期就该跑一次 `--once` 冒烟**（本课 Dockerfile 的 builder 阶段就是这么做的）。
3. 不信自述，独立复核：`curl /version` 看到底是哪个版本在服务；
   再看 `releases.json` 的 `current`；最后确认回滚目标的健康检查**真的**通过过。

</details>

---

## 四、验收清单（做完打勾）

**离线部分（不需要 Docker）**

- [ ] `01 --self-test`：8 项断言全过
- [ ] `02 --self-test`：12 项断言全过
- [ ] `03 --self-test`：14 项全过（PyYAML 后端）
- [ ] `03 --force-fallback --self-test`：11 通过 / 3 跳过 / 0 失败
- [ ] `04 --self-test`：12 项断言全过（FakeRuntime）
- [ ] `04 --dry-run`、`05 --dry-run`、`03 --dry-run` 都能打印计划且不碰 Docker

**需要 Docker**

- [ ] `02 --build both` 真构建出两个镜像，能说出体积差与耗时差
- [ ] 容器起来后 `/healthz`、`/readyz`、`/version`、`/api/summary` 都能返回 200
- [ ] `docker exec … command -v gcc` 返回空（多阶段生效）
- [ ] `05-rollback-drill.py` 演练通过：坏版本 rc=2、独立复核回到 v1.0.0
- [ ] 说出「判死耗时」为什么等于健康检查超时

**CI（可选，需要 act）**

- [ ] `03 --out … --act-mode --path-prefix …` 生成成功
- [ ] `act push --bind … -j lint -j test` 三个 job 全绿
- [ ] 能解释**为什么必须加 `--bind`**（不加时容器里是空目录）

**收尾**

- [ ] 执行了 README「清理」章节的全部命令
- [ ] `docker ps -a | grep d183` 无输出；`ss -ltnp | grep 18080` 无输出
- [ ] `/tmp/day183` 与 `/tmp/day183-probe` 已删除

---

## 五、延伸（选做）

1. 给 `04-deploy-rollback.py` 加一个 `--canary`：先起新容器在 18081 上跑健康检查，
   通过了再切换端口映射——体会「先判后切」再往前一步（蓝绿部署的雏形）。
2. 把 `.dockerignore` 故意删掉 `.env`，往上下文里放一个假的 `.env`，
   构建后用 `docker run … sh -c 'ls -la /app'` 证明它进了镜像。想清楚为什么这很危险。
3. 给 CI 加第三个 job `security`：用 `pip-audit` 检查依赖漏洞，并让 `build` 依赖它。
   注意它是「必须绿」还是「允许红」（不同团队答案不同，但**必须有人明确决定**）。
4. 把 `latest` 从 workflow 的 tags 里删掉，只留 SHA 标签。然后写清楚：
   人怎么找到「当前线上是哪个 SHA」？（提示：靠 `releases.json` 这种账本，而不是靠标签）
5. 给 `05-rollback-drill.py` 加第五幕：模拟**回滚目标也不健康**（把两个版本都注入故障），
   看脚本是不是老实报 rc=3。**不要让它假装成功**。
