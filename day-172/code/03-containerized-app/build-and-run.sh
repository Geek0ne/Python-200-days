#!/usr/bin/env bash
# 真机复现 Day 172 实战：构建 → 运行 → 验证 → 清理
set -euo pipefail
cd "$(dirname "$0")"

PORT="${PORT:-18099}"
IMAGE="day172-app:test"
CNAME="day172-app-test"

cleanup() {
  echo "── 清理 ──"
  docker rm -f "$CNAME" 2>/dev/null || true
  docker rmi -f "$IMAGE" 2>/dev/null || true
  echo "容器、镜像、端口 $PORT 已释放"
}
trap cleanup EXIT

echo "── 1. 离线自测（不需要 Docker）──"
python3 app.py --self-test

echo
echo "── 2. 构建 ──"
docker build -t "$IMAGE" .

echo
echo "── 3. 镜像分层与体积 ──"
docker images -f "reference=$IMAGE" --format '{{.Repository}}:{{.Tag}}  {{.Size}}'
docker history "$IMAGE" --format '{{.Size}}	{{.CreatedBy}}' | head -8

echo
echo "── 4. 运行 ──"
docker run -d --name "$CNAME" -p "$PORT":8000 \
  -e APP_NAME=from-env-via-docker-run \
  "$IMAGE"

sleep 3
echo "容器内身份： $(docker exec "$CNAME" id)"

echo
echo "── 5. 验证 ──"
for ep in "/health" "/echo?msg=day172" "/config" "/"; do
  printf '  GET %-22s → ' "$ep"
  curl -s "http://127.0.0.1:$PORT$ep" || echo "❌ 失败"
  echo
done

echo
echo "── 6. HEALTHCHECK 状态 ──"
sleep 12
docker inspect -f '{{.State.Health.Status}}' "$CNAME"

echo
echo "── 7. 优雅停止耗时（<10s 说明 SIGTERM 被处理）──"
start=$(date +%s)
docker stop "$CNAME"
echo "docker stop 耗时 $(( $(date +%s) - start ))s"

echo
echo "── 8. 日志 ──"
docker logs "$CNAME" 2>&1 | tail -10
