#!/usr/bin/env bash
# 本地复刻 CI：语法检查 → 全部自检 → 启动服务跑验收 → 可选构建镜像
# 用法：./ci/run-local.sh [--with-docker]

set -euo pipefail
cd "$(dirname "$0")/.."

stage() { printf '\n▶ %s\n' "$*"; }
WITH_DOCKER=0
[[ "${1:-}" == "--with-docker" ]] && WITH_DOCKER=1

stage "1/4 语法检查（compileall，输出 .pyc 到临时目录）"
PYTHONPYCACHEPREFIX="$(mktemp -d)" python3 -m compileall -q code
echo "  所有 .py 编译通过"

stage "2/4 离线自检（不联网、不占端口）"
for file in code/ops_lib.py code/crypto_lib.py \
            code/01-retry-backoff.py code/02-crypto-envelope.py \
            code/03-api-auth.py code/04-logging-alert.py code/app.py; do
    printf '  %-28s ' "$(basename "$file")"
    python3 "$file" --self-test >/dev/null
    echo "OK"
done

stage "3/4 起服务 + 跑验收（真实 HTTP）"
WORK="$(mktemp -d)"
API_SECRET="ci-secret-${RANDOM}"
export API_SECRET
DATA_DIR="$WORK/data" PORT=18096 python3 code/app.py >"$WORK/app.log" 2>&1 &
APP_PID=$!
cleanup() {
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
    rm -rf "$WORK"
}
trap cleanup EXIT

for _ in $(seq 1 50); do
    if python3 - "$WORK" <<'PY'
import sys, urllib.request
try:
    urllib.request.urlopen("http://127.0.0.1:18096/readyz", timeout=1)
except Exception:
    sys.exit(1)
PY
    then break; fi
    sleep 0.2
done
python3 code/smoke_test.py --url http://127.0.0.1:18096 --secret "$API_SECRET"

if (( WITH_DOCKER )); then
    stage "4/4 Docker 构建 + 容器内验收"
    docker build -t learn195-app:ci -f code/Dockerfile code
else
    stage "4/4 跳过 Docker（加 --with-docker 启用）"
fi

echo -e "\n✅ CI 全部通过"
