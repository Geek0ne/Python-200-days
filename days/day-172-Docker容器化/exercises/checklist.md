# Day 172 练习与验收清单 — Docker 容器化

> 全部命令均可在 Linux 机器上直接复制执行。带 ⚠️ 的会创建容器/镜像，**执行完请务必按「清理」小节撤销**。

---

## 一、今日完成清单

- [ ] 能说清容器与虚拟机的隔离层次差异（namespace + cgroup vs Hypervisor）
- [ ] 能手写不踩缓存坑的 Dockerfile（依赖清单与业务代码分开 COPY）
- [ ] 能解释为什么 `docker history` 显示的 pip 层删不掉
- [ ] 能复现实验 4：应用绑 `127.0.0.1` 导致「容器内 200、容器外 000」
- [ ] 能说清 `EXPOSE` 是纯文档、`-p` 才是真发布端口
- [ ] 能复现实验 8：`--prefix` + `COPY --from` 路径不匹配导致容器秒退
- [ ] 能写出带 `USER` + `HEALTHCHECK` + exec form `CMD` 的生产 Dockerfile

---

## 二、练习题

### 基础 1：构建并验证最小镜像

**目标**：走通 build → run → verify → cleanup 闭环。

```bash
cd ~/code/Learn-Python/days/day-172-Docker容器化/code/03-containerized-app

# 1. 先离线自测（不需要 Docker，验证核心逻辑）
python3 app.py --self-test

# 2. 构建
docker build -t day172-ex1 .

# 3. 查看分层：哪一层最贵？
docker history day172-ex1 --format '{{.Size}}\t{{.CreatedBy}}' | head -8

# 4. 运行（换一个端口，避免与教材实验冲突）
docker run -d --name day172-ex1 -p 18077:8000 day172-ex1

# 5. 验证四个端点
sleep 3
curl -s http://127.0.0.1:18077/health;  echo
curl -s "http://127.0.0.1:18077/echo?msg=ex1"; echo
curl -s http://127.0.0.1:18077/config;     echo
curl -s http://127.0.0.1:18077/;           echo

# 6. 容器内身份（应是非 root）
docker exec day172-ex1 id

# 7. 优雅停止耗时（应 < 10 秒）
time docker stop day172-ex1
```

**验收标准**：四个端点均返回 JSON 且含 `"version":"1.0.0"`；
`docker exec … id` 输出含 `uid=10001(appuser)`；`docker stop` 耗时 < 10s。

**清理**：

```bash
docker rm -f day172-ex1
docker rmi -f day172-ex1
```

---

### 基础 2：复现「容器内通、容器外不通」

**目标**：亲手踩一次 Day 172 翻车实验 #4。

```bash
mkdir -p /tmp/ex2 && cd /tmp/ex2
cat > app.py <<'PY'
from flask import Flask, jsonify
app = Flask(__name__)
@app.get("/health")
def health(): return jsonify(status="ok")
app.run(host="127.0.0.1", port=8000)   # 故意绑回环
PY
printf 'flask==3.0.3\n' > requirements.txt
cat > Dockerfile <<'DOCKER'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["python", "app.py"]
DOCKER

docker build -t day172-ex2 .
docker run -d --name day172-ex2 -p 18078:8000 day172-ex2
sleep 3

echo "--- 容器状态（注意：Up，但外部连不上）---"
docker ps --filter name=day172-ex2 --format '{{.Status}}'
echo "--- 容器内 curl ---"
docker exec day172-ex2 python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"
echo "--- 宿主 curl（预期 000）---"
curl -s -m 5 -o /dev/null -w "http_code=%{http_code}\n" http://127.0.0.1:18078/health
```

**思考**：容器显示 `Up` 却连不上——如果只看 `docker ps` 或编排系统的
Deployment 副本数（容器活着 = 副本就绪），会得出「服务正常」的错误结论。
这就是为什么必须配 `HEALTHCHECK` / Readiness Probe。

**修复并复测**：`sed -i 's/127.0.0.1/0.0.0.0/' app.py` 重建重跑，宿主 curl 应返回 200。

**清理**：

```bash
docker rm -f day172-ex2
docker rmi -f day172-ex2
rm -rf /tmp/ex2
```

---

### 进阶 3：量化缓存，并解释你的数字

**目标**：自己跑出缓存对比，而不是背结论。

```bash
cd ~/code/Learn-Python/days/day-172-Docker容器化/code
python3 02-dockerfile-patterns.py --self-test     # 先跑离线自测
python3 02-dockerfile-patterns.py --dry-run       # 看 5 个模板的静态分析
```

**验收标准**：
1. `--self-test` 退出码为 0，输出 `🎉 全部自测通过`
2. 自测里包含两条断言：`BAD_CACHE 模型预测 hot≈9.4s` 与
   `CACHE_FRIENDLY 模型预测 hot≈1.7s`，它们分别对应真机实测 9.426s / 1.727s
3. `--dry-run` 输出中 `bad-cache` 必须被报出错误码 `002` 和 `004`

**进阶部分**：在 `/tmp/ex3` 里自己写两份 Dockerfile（一份 `COPY . .` 放前面、
一份依赖清单分离），然后实测三次构建耗时，填下表：

| 场景 | 你的实测(s) | 教材实测(s) |
|---|---|---|
| 无改动重建 | | 0.118 |
| 只改 app.py | | 1.727 |
| 改 requirements.txt | | 9.426 |

**要求**：三个数字必须递增。若「只改 app.py」反而比「改 requirements.txt」慢，
说明你的 `COPY` 顺序有问题，用 `docker history` 和 `docker build` 的 `Step` 输出自查。

---

### 进阶 4：修好一个多阶段构建的 prefix 陷阱

**目标**：亲手复现并修复 Day 172 翻车实验 #8。

```bash
mkdir -p /tmp/ex4 && cd /tmp/ex4
cat > app.py <<'PY'
import flask
print("flask ok:", flask.__version__ if hasattr(flask,'__version__') else 'loaded', flush=True)
PY
printf 'flask==3.0.3\n' > requirements.txt

# 故意写错的版本：从 final 阶段自己的空目录拷
cat > Dockerfile <<'DOCKER'
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
COPY --from=builder /usr/local/lib/python3.12/site-packages/ \
     /usr/local/lib/python3.12/site-packages/
COPY app.py .
CMD ["python", "app.py"]
DOCKER

docker build -t day172-ex4 .                          # 注意：构建会「成功」
docker run --rm day172-ex4                            # 但运行会失败
```

**思考三连**：
1. 为什么 `docker build` 成功而 `docker run` 失败？
2. `docker history` 里那一层 COPY 显示 5.02MB——它拷到东西了吗？
3. 怎么用一条命令确认真实安装路径？
   （提示：`docker run --rm python:3.12-slim sh -c "pip install --prefix=/install … && find /install -maxdepth 3 -type d"`）

**修复**：把 `COPY --from=builder` 的源路径改成
`/install/lib/python3.12/site-packages/`，重建后 `docker run --rm` 应输出 `flask ok: …`。

**清理**：

```bash
rm -rf /tmp/ex4
docker rmi -f day172-ex4
```

---

### 挑战 5：给 Day 173 预热

Docker Compose（明天的主题）会把多个容器连成网络。请先想清楚两个问题，
明天会用实验直接验证：

1. 同一 network 里，容器 A 该用 `172.17.0.3` 还是服务名 `redis` 去连容器 B？
   为什么？（提示：容器重启后 IP 会变；docker 会在 DNS 里注册服务名）
2. `docker run -v /host/data:/var/lib/postgresql/data` 与容器可写层相比，
   哪个更适合放数据库？容器删除后数据还在吗？

---

## 三、验收清单（完成后逐项打勾）

- [ ] 练习 1 四个端点全部 200，`id` 显示 uid=10001
- [ ] 练习 2 复现出宿主 `http_code=000`，并能解释 namespace loopback 独立
- [ ] 练习 3 `02-dockerfile-patterns.py --self-test` 退出码 0
- [ ] 练习 4 复现容器秒退，并能说出 `--prefix` 的真实目录语义
- [ ] 练习 4 修复后 `docker run --rm` 成功
- [ ] 全部临时容器已删除：`docker ps -a --filter "name=day172-ex"` 输出为空
- [ ] 临时镜像已删除：`docker image ls -f reference='day172-ex*'` 输出为空

### 一次性清理（全部做完后执行）

```bash
docker ps -a --filter "name=day172-" --format '{{.Names}}'   # 应为空
docker image ls -f reference='day172-ex*'                     # 应为空
rm -rf /tmp/ex2 /tmp/ex3 /tmp/ex4
docker builder prune -f                                      # 清构建缓存（约回收数 GB）
```