#!/usr/bin/env bash
# Day 190 一键部署 / 撤收 / 验收
#   bash deploy.sh up      构建 + 启动 + 等待健康 + 端到端验收
#   bash deploy.sh status  看容器、健康、计数
#   bash deploy.sh logs    看最近日志
#   bash deploy.sh down    停服务 + 删卷 + 验端口已释放
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE=(docker compose -f "${DIR}/docker-compose.yml")
PORT=18090
BASE="http://127.0.0.1:${PORT}"

log() { printf '\033[36m[deploy]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[deploy] %s\033[0m\n' "$*" >&2; exit 1; }

preflight() {
  command -v docker >/dev/null || die "docker 未安装"
  docker info >/dev/null 2>&1 || die "docker daemon 不可用"
  "${COMPOSE[@]}" version >/dev/null || die "docker compose 插件不可用"
  if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    die "端口 ${PORT} 已被占用，先处理占用进程"
  fi
  log "preflight ok: docker + compose + 端口 ${PORT} 空闲"
}

wait_accept() {
  log "等待 sink 健康检查..."
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 2 "${BASE}/health" >/dev/null 2>&1; then break; fi
    sleep 1
  done
  curl -fsS --max-time 2 "${BASE}/health" >/dev/null || die "sink 未就绪"

  log "等待第一条告警送达（最多 90s）..."
  alerts=0
  for _ in $(seq 1 45); do
    alerts=$(curl -fsS --max-time 2 "${BASE}/counts" | python3 -c 'import json,sys;print(json.load(sys.stdin)["alerts"])')
    if [ "${alerts}" -ge 1 ]; then
      log "已收到 ${alerts} 条告警"
      break
    fi
    sleep 2
  done
  [ "${alerts:-0}" -ge 1 ] || die "90s 内没有收到任何告警"

  "${COMPOSE[@]}" ps --format 'table {{.Name}}\t{{.Status}}'
  echo
  log "counts: $(curl -fsS --max-time 2 "${BASE}/counts")"
  log "验收通过：sink 健康 + worker 心跳 + 告警落库"
}

case "${1:-up}" in
  up)
    preflight
    log "构建镜像..."
    "${COMPOSE[@]}" build
    log "启动..."
    "${COMPOSE[@]}" up -d --wait --wait-timeout 90
    wait_accept
    ;;
  status)
    "${COMPOSE[@]}" ps
    echo
    curl -fsS --max-time 2 "${BASE}/health" && echo
    curl -fsS --max-time 2 "${BASE}/counts" && echo
    ;;
  logs)
    "${COMPOSE[@]}" logs --tail 40
    ;;
  down)
    log "停止并删除容器/卷..."
    "${COMPOSE[@]}" down -v --remove-orphans
    if ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
      die "端口 ${PORT} 仍被占用"
    fi
    remaining=$(docker ps -aq --filter "label=com.docker.compose.project=d190" | wc -l)
    [ "${remaining}" -eq 0 ] || die "仍有 ${remaining} 个容器残留"
    log "已清理：容器 0、卷已删、端口 ${PORT} 已释放"
    ;;
  *)
    die "用法: $0 {up|status|logs|down}"
    ;;
esac
