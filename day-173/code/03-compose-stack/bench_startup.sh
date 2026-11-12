#!/usr/bin/env bash
# 测量两种 depends_on 策略下，app 容器从 Up 到 healthy 的耗时
# 用法：./bench_startup.sh
set -uo pipefail
cd "$(dirname "$0")"

wait_app_healthy() {   # $1 = 毫秒时间戳基点
  while :; do
    s=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
        day173-lab-app-1 2>/dev/null || echo none)
    [ "$s" = "healthy" ] && break
    sleep 0.2
  done
  echo $(( ($(date +%s%N) - $1) / 1000000 ))
}

run_case() {           # $1=标签  $2=compose 文件参数
  docker compose down -v >/dev/null 2>&1
  t0=$(date +%s%N)
  # shellcheck disable=SC2086
  docker compose $2 up -d >/dev/null 2>&1
  ms=$(wait_app_healthy "$t0")
  printf '%-18s app 到 healthy 耗时 = %s ms\n' "$1" "$ms"
}

echo "=== Day 173 实测：depends_on 策略对启动时延的影响 ==="
run_case "service_healthy" ""
run_case "service_started" "-f compose.yaml -f compose.nohealth.yaml"
run_case "service_healthy(2)" ""
docker compose down -v >/dev/null 2>&1