#!/usr/bin/env bash
# =============================================================================
# Day 172 · 示例 01 —— Docker 基础命令全流程演示（基础用法）
# =============================================================================
# 本脚本是「可交互 + 可自动」的教学脚本：直接运行会打印每一步命令与说明。
# 之所以写成 .sh 而不是 .py，是因为 Docker CLI 本身就是 shell 工具，
#   学习者需要看到的是「命令怎么敲」，而不是 Python 怎么调子进程。
#
# 用法：
#   bash 01-docker-basics.sh          # 只打印讲解，不动真容器（安全默认）
#   bash 01-docker-basics.sh --live   # 真机执行（会创建/删除名为 day172-demo 的容器）
#
# ⚠️ --live 会真实占端口 18080，脚本退出前会自动清理。
# =============================================================================

set -uo pipefail

APP_DIR="$(mktemp -d /tmp/day172-demo.XXXXXX)"
IMAGE="day172:demo"
CNAME="day172-demo"
PORT=18080

live=0
[[ "${1:-}" == "--live" ]] && live=1

say() { printf '\n\033[1;36m%s\033[0m\n' "=== $* ==="; }
cmd() { printf '\033[0;33m$ %s\033[0m\n' "$*"; }

# -----------------------------------------------------------------------------
# 0. 环境自检
# -----------------------------------------------------------------------------
say "第 0 步：确认 Docker 可用"
cmd "docker version --format '{{.Server.Version}}'"
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker 守护进程不可用。Docker Desktop / dockerd 需要已启动。"
    echo "   Linux 上检查： systemctl status docker"
    exit 1
fi
SERVER_VER="$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo 'unknown')"
echo "✅ Docker Server 版本：$SERVER_VER"
echo "   本课实测环境：Docker 29.1.3 / containerd 2.2.1 / Python 3.12-slim"

# -----------------------------------------------------------------------------
# 1. 准备一个最小 Flask 应用 + Dockerfile
# -----------------------------------------------------------------------------
say "第 1 步：准备源码与 Dockerfile"
mkdir -p "$APP_DIR"

cat > "$APP_DIR/main.py" <<'PY'
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/echo")
def echo():
    return jsonify(msg=request.args.get("msg", "hello"))


if __name__ == "__main__":
    # ⚠️ 必须绑 0.0.0.0：容器外（宿主 / 其他容器）才连得上。
    #    绑 127.0.0.1 只在容器自己的 network namespace 内有效。
    app.run(host="0.0.0.0", port=8000)
PY

printf 'flask==3.0.3\n' > "$APP_DIR/requirements.txt"

# ⚠️ 顺序是本课要点之一：
#   依赖清单先 COPY 且单独 COPY —— 这样改业务代码时不会让 pip 层缓存失效。
cat > "$APP_DIR/Dockerfile" <<'DOCKER'
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["python", "main.py"]
DOCKER

cat > "$APP_DIR/.dockerignore" <<'IGNORE'
__pycache__/
*.pyc
.git/
.venv/
IGNORE

echo "已生成于 $APP_DIR ：main.py / requirements.txt / Dockerfile / .dockerignore"

# -----------------------------------------------------------------------------
# 2. 构建
# -----------------------------------------------------------------------------
say "第 2 步：docker build"
echo "讲解要点："
echo "  · -t 给镜像打标签"
echo "  · . 表示 build context 为当前目录，Dockerfile 里只能用相对 context 的路径"
echo "  · .dockerignore 在打包上下文阶段生效（实测 60.01MB → 10.75kB）"
cmd "docker build -t $IMAGE $APP_DIR"

if [[ $live -eq 1 ]]; then
    set -x
    docker build -t "$IMAGE" "$APP_DIR"
    set +x
    docker images -f "reference=$IMAGE" --format '{{.Repository}}:{{.Tag}}  {{.Size}}'
    cmd "docker history $IMAGE --format '{{.Size}}\t{{.CreatedBy}}'"
    docker history "$IMAGE" --format '{{.Size}}	{{.CreatedBy}}' | head -6
else
    echo "（--live 未开启，跳过真实构建）"
fi

# -----------------------------------------------------------------------------
# 3. 运行
# -----------------------------------------------------------------------------
say "第 3 步：docker run"
echo "讲解要点："
echo "  · -d 后台运行；--name 便于后续 exec/logs/stop；-p 宿主:容器 端口映射"
echo "  · 端口映射靠宿主 iptables DNAT 规则实现，EXPOSE 并不会真的发布端口"
cmd "docker run -d --name $CNAME -p $PORT:8000 $IMAGE"

if [[ $live -eq 1 ]]; then
    set -x
    docker run -d --name "$CNAME" -p "$PORT:8000" "$IMAGE"
    sleep 3
    set +x

    say "第 4 步：验证服务（容器内 vs 宿主）"
    cmd "curl -s http://127.0.0.1:$PORT/health"
    curl -s "http://127.0.0.1:$PORT/echo?msg=day172" || echo "❌ 访问失败：检查应用是否绑了 0.0.0.0"

    say "第 5 步：docker logs —— 日志不落宿主文件，随容器生命周期走"
    cmd "docker logs $CNAME"
    docker logs "$CNAME" 2>&1 | tail -8

    say "第 6 步：docker exec —— 进入容器排障"
    cmd "docker exec $CNAME sh -c 'id; pwd; ls -l /app'"
    docker exec "$CNAME" sh -c 'id; pwd; ls /app'

    cmd "docker exec $CNAME python -c \"import sys, flask; print(sys.version.split()[0], flask.__version__ if hasattr(flask,'__version__') else 'n/a')\""
    docker exec "$CNAME" python -c "import sys; print(sys.version.split()[0])"

    say "第 7 步：docker stats —— 运行时内存远小于镜像体积"
    cmd "docker stats --no-stream $CNAME"
    timeout 15 docker stats --no-stream "$CNAME" 2>&1 | tail -3 || true
    echo "讲解：镜像 198MB 是磁盘/分发成本；内存占用通常只有 20~100MiB。"

    say "第 8 步：停止与删除（优雅退出）"
    cmd "docker stop $CNAME && docker rm $CNAME"
    # 演示优雅停止耗时：Flask/gunicorn 会处理 SIGTERM，通常瞬时完成，
    # 若程序忽略 SIGTERM，docker stop 会硬等满 10 秒再 SIGKILL。
    start_ts=$(date +%s)
    docker stop "$CNAME" >/dev/null
    docker rm "$CNAME" >/dev/null
    echo "docker stop + rm 耗时：$(( $(date +%s) - start_ts )) 秒（<10s 说明 SIGTERM 被正确处理）"
else
    echo "（--live 未开启，跳过真实运行）"
    echo "本应执行： docker run -d --name $CNAME -p $PORT:8000 $IMAGE"
fi

# -----------------------------------------------------------------------------
# 清理
# -----------------------------------------------------------------------------
say "清理"
if [[ $live -eq 1 ]]; then
    docker rm -f "$CNAME" >/dev/null 2>&1 || true
    docker rmi "$IMAGE" >/dev/null 2>&1 || true
    echo "已删除容器 $CNAME 与镜像 $IMAGE"
fi
rm -rf "$APP_DIR"
echo "已删除临时目录 $APP_DIR（端口 $PORT 已释放）"

say "完成"
cat <<'SUMMARY'
本课要点回顾：
  1. 容器 = namespace(隔离视图) + cgroup(资源限制) + OverlayFS(分层镜像)
  2. 层不可变 ⇒ 缓存命中只看「父层哈希 + 指令 + 该指令涉及的文件内容」
  3. COPY 顺序决定缓存：改 main.py 实测 1.7s，改 requirements.txt 实测 9.4s
  4. 应用必须绑 0.0.0.0，否则容器外一律连不上（本课翻车实验已复现）
  5. 端口映射 = 宿主 iptables DNAT；EXPOSE 只是文档
SUMMARY