#!/usr/bin/env bash
# Day 195 · 一键部署 + 健康检查 + 失败自动回滚
#
# 用法：
#   ./deploy.sh                     # 构建并部署新版本（tag=时间戳）
#   ./deploy.sh --tag v2            # 指定 tag
#   ./deploy.sh --ref learn195-app:broken --no-build   # 部署一个"坏镜像"看回滚
#   ./deploy.sh --down              # 停止并删除容器与数据卷
#
# 设计要点：
# - 失败自动回滚到"部署前正在跑的那个镜像引用"；
# - 健康检查由 Docker HEALTHCHECK 驱动，不用 sleep 5 碰运气；
# - 验收脚本真实走一遍签名 → 写入 → 读回 → 重放，不是只看端口通不通。

set -euo pipefail
cd "$(dirname "$0")"

IMAGE="${IMAGE:-learn195-app}"
TAG="${TAG:-$(date +%Y%m%d-%H%M%S)}"
REF="${REF:-}"
NAME="${NAME:-learn195-app}"
PORT="${PORT:-18095}"
VOLUME="${VOLUME:-learn195-data}"
API_SECRET="${API_SECRET:-demo-api-secret-change-me}"
MASTER_KEY_FILE="${MASTER_KEY_FILE:-.master-key}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-30}"
DO_BUILD=1
DO_DOWN=0

log() { printf '[deploy %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

usage() {
    sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --tag) TAG="$2"; shift 2 ;;
        --ref) REF="$2"; shift 2 ;;
        --image) IMAGE="$2"; shift 2 ;;
        --port) PORT="$2"; shift 2 ;;
        --name) NAME="$2"; shift 2 ;;
        --volume) VOLUME="$2"; shift 2 ;;
        --no-build) DO_BUILD=0; shift ;;
        --down) DO_DOWN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "未知参数: $1" >&2; exit 2 ;;
    esac
done

if (( DO_DOWN )); then
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    docker volume rm "$VOLUME" >/dev/null 2>&1 || true
    log "已停止并清理容器 $NAME、数据卷 $VOLUME"
    exit 0
fi

# ── 主密钥：持久化在仓库外（这里用 .master-key + chmod 600，生产用 KMS）──
if [[ -z "${MASTER_KEY:-}" ]]; then
    if [[ -f "$MASTER_KEY_FILE" ]]; then
        MASTER_KEY="$(cat "$MASTER_KEY_FILE")"
    else
        MASTER_KEY="$(python3 -c 'import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode())')"
        umask 077
        printf '%s' "$MASTER_KEY" > "$MASTER_KEY_FILE"
        chmod 600 "$MASTER_KEY_FILE"
        log "已生成主密钥并写入 $MASTER_KEY_FILE（勿提交，勿挂进数据卷）"
    fi
fi

# ── 记录当前版本，失败时回滚到它 ──
PREV_REF=""
if docker inspect "$NAME" >/dev/null 2>&1; then
    PREV_REF="$(docker inspect -f '{{.Config.Image}}' "$NAME")"
    log "当前运行版本: $PREV_REF"
else
    log "当前没有运行中的容器（首次部署）"
fi

start_container() {
    local ref="$1"
    docker rm -f "$NAME" >/dev/null 2>&1 || true
    log "启动 $ref → 127.0.0.1:$PORT"
    docker run -d --name "$NAME" \
        --restart unless-stopped \
        -p "127.0.0.1:${PORT}:8080" \
        -e "API_SECRET=${API_SECRET}" \
        -e "MASTER_KEY=${MASTER_KEY}" \
        -v "${VOLUME}:/data" \
        --read-only --tmpfs "/tmp:rw,noexec,nosuid,size=16m" \
        --cap-drop ALL --security-opt no-new-privileges \
        "$ref" >/dev/null
}

wait_healthy() {
    local deadline=$((SECONDS + HEALTH_TIMEOUT))
    local status
    while (( SECONDS < deadline )); do
        status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$NAME" 2>/dev/null || echo missing)"
        case "$status" in
            healthy)
                log "容器健康（耗时 ${SECONDS}s）"
                return 0
                ;;
            unhealthy)
                # Docker 已经按 --retries 重试过；再等只是让故障窗口变长。
                # 第一次跑回滚实验时漏了这个分支，白等了 30 秒超时。
                log "健康检查失败（unhealthy），不再等待"
                return 1
                ;;
            exited|dead|missing)
                log "容器状态=$status，停止等待"
                return 1
                ;;
        esac
        sleep 1
    done
    log "等待健康超时（${HEALTH_TIMEOUT}s），最后状态=${status:-unknown}"
    return 1
}

restore_previous() {
    if [[ -z "$PREV_REF" ]]; then
        log "没有上一个版本可回滚（首次部署失败）"
        return 1
    fi
    log "回滚到 $PREV_REF"
    start_container "$PREV_REF" || return 1
    wait_healthy || return 1
    log "✅ 回滚完成，旧版本已恢复服务"
}

# ── 构建 ──
if (( DO_BUILD )); then
    if [[ -n "$REF" ]]; then
        echo "--ref 与构建互斥；用 --no-build 部署已有镜像" >&2
        exit 2
    fi
    REF="$IMAGE:$TAG"
    log "构建 $REF"
    docker build --tag "$REF" -f Dockerfile .
else
    REF="${REF:-$IMAGE:$TAG}"
    log "跳过构建，直接部署 $REF"
fi

# ── 部署 ──
if ! start_container "$REF"; then
    log "❌ 容器启动失败"
    docker logs --tail 30 "$NAME" 2>&1 || true
    restore_previous || true
    exit 1
fi

if ! wait_healthy; then
    log "❌ 新版本未通过健康检查，最近日志："
    docker logs --tail 30 "$NAME" 2>&1 || true
    restore_previous || true
    exit 1
fi

log "验收：签名写入 → 解密读回 → 重放拒绝"
if ! python3 smoke_test.py --url "http://127.0.0.1:$PORT" --secret "$API_SECRET"; then
    log "❌ 验收失败，最近日志："
    docker logs --tail 30 "$NAME" 2>&1 || true
    restore_previous || true
    exit 1
fi

log "✅ 部署成功：$REF"
docker inspect -f '  镜像={{.Config.Image}} 状态={{.State.Status}} 健康={{.State.Health.Status}}' "$NAME"
