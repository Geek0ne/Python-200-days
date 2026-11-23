#!/usr/bin/env python3
"""
Day 183 — 阶段项目 · 自动化运维平台（二）
被部署的「运维平台 API」服务本体（纯标准库，可直接跑，也可进容器）

它只有五个端点，但每一个都对应 CI/CD 里的一个真实角色：

    GET /healthz    存活探针（liveness）—— 进程还活着吗？
    GET /readyz     就绪探针（readiness）—— 能接流量吗？（依赖是否就绪）
    GET /version    版本信息（回滚时用它确认「现在到底跑的是哪个版本」）
    GET /api/hosts  业务接口（主机清单）
    GET /metrics    指标（Prometheus 文本格式，供 Day 177 那套体系采集）

如果装了 prometheus_client 就用它渲染指标，没装就退化为手写文本——
两种输出都是 Prometheus 真正吃的 exposition format。

用法：
    python3 01-ops-service.py --port 8080            # 起服务
    python3 01-ops-service.py --self-test            # 自检：绑 0 号端口，逐个打端点断言
    python3 01-ops-service.py --once                 # 打一份 JSON 快照后退出（不用起服务）
    python3 01-ops-service.py --port 8080 --fail-mode readiness   # 故意让就绪探针失败
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

APP_NAME = "ops-platform-api"

# --- 指标后端：有 prometheus_client 就用，没有就退到 stdlib --------------------
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

    METRICS_BACKEND = "prometheus_client"
except ImportError:  # pragma: no cover - 取决于环境
    METRICS_BACKEND = "stdlib-fallback"

TEXT_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# --- 平台状态（真实项目里来自数据库/CMDB，这里内联，保证零依赖可复现）---------
HOSTS = [
    {"name": "web-01", "addr": "10.0.0.11", "role": "web", "cpu": 12.5, "mem": 41.2},
    {"name": "web-02", "addr": "10.0.0.12", "role": "web", "cpu": 9.8, "mem": 38.7},
    {"name": "db-01", "addr": "10.0.0.21", "role": "db", "cpu": 33.1, "mem": 72.4},
    {"name": "cache-01", "addr": "10.0.0.31", "role": "cache", "cpu": 4.2, "mem": 19.0},
]

START_TS = time.time()
REQUESTS_TOTAL = 0
REQUESTS_IN_FLIGHT = 0
_LOCK = threading.Lock()

if METRICS_BACKEND == "prometheus_client":
    REQ_COUNTER = Counter(
        "ops_http_requests_total", "HTTP 请求总数", ["path", "status"]
    )
    IN_FLIGHT = Gauge("ops_http_in_flight", "处理中的请求数")
    UPTIME = Gauge("ops_uptime_seconds", "进程已运行秒数")
else:  # pragma: no cover
    REQ_COUNTER = IN_FLIGHT = UPTIME = None


class State:
    """服务运行态。fail_mode 是给回滚演练用的「故障注入开关」。"""

    def __init__(self, version: str, fail_mode: str = "none"):
        self.version = version
        self.fail_mode = fail_mode  # none | readiness | liveness
        self.started = time.time()

    def readiness(self) -> tuple[bool, str]:
        if self.fail_mode == "readiness":
            return False, "依赖未就绪（故障注入：fail_mode=readiness）"
        return True, "依赖正常"

    def liveness(self) -> tuple[bool, str]:
        if self.fail_mode == "liveness":
            return False, "进程内部状态异常（故障注入：fail_mode=liveness）"
        return True, "存活"


def _metrics_text(state: State, reqs: int, in_flight: int) -> str:
    uptime = time.time() - state.started
    if METRICS_BACKEND == "prometheus_client":
        UPTIME.set(uptime)
        return generate_latest().decode("utf-8")
    # stdlib 回退：手写 exposition format（Prometheus 真正吃的就是这个文本）
    return (
        "# HELP ops_http_requests_total HTTP 请求总数\n"
        "# TYPE ops_http_requests_total counter\n"
        f"ops_http_requests_total {float(reqs)}\n"
        "# HELP ops_http_in_flight 处理中的请求数\n"
        "# TYPE ops_http_in_flight gauge\n"
        f"ops_http_in_flight {float(in_flight)}\n"
        "# HELP ops_uptime_seconds 进程已运行秒数\n"
        "# TYPE ops_uptime_seconds gauge\n"
        f"ops_uptime_seconds {uptime:.3f}\n"
        "# HELP ops_build_info 构建信息\n"
        "# TYPE ops_build_info gauge\n"
        f'ops_build_info{{version="{state.version}"}} 1.0\n'
    )


def make_handler(state: State):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "ops-platform/" + state.version

        def log_message(self, fmt, *args):  # 静音，避免污染实验输出
            pass

        # --- 工具 ---------------------------------------------------------
        def _send(self, code: int, body: bytes, ctype: str = "application/json"):
            global REQUESTS_TOTAL
            with _LOCK:
                REQUESTS_TOTAL += 1
            if METRICS_BACKEND == "prometheus_client":
                REQ_COUNTER.labels(path=self.path.split("?")[0], status=str(code)).inc()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict):
            self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        # --- 路由 ---------------------------------------------------------
        def do_GET(self):
            global REQUESTS_IN_FLIGHT
            path = self.path.split("?")[0]
            with _LOCK:
                REQUESTS_IN_FLIGHT += 1
            if METRICS_BACKEND == "prometheus_client":
                IN_FLIGHT.inc()
            try:
                if path == "/healthz":
                    ok, why = state.liveness()
                    self._json(200 if ok else 503, {"status": "ok" if ok else "fail", "reason": why})
                elif path == "/readyz":
                    ok, why = state.readiness()
                    self._json(200 if ok else 503, {"status": "ready" if ok else "not-ready", "reason": why})
                elif path == "/version":
                    self._json(200, {
                        "app": APP_NAME,
                        "version": state.version,
                        "metrics_backend": METRICS_BACKEND,
                        "uptime_seconds": round(time.time() - state.started, 3),
                    })
                elif path == "/api/hosts":
                    self._json(200, {"count": len(HOSTS), "hosts": HOSTS})
                elif path == "/api/summary":
                    self._json(200, {
                        "hosts": len(HOSTS),
                        "by_role": _count_by_role(),
                        "avg_cpu": round(sum(h["cpu"] for h in HOSTS) / len(HOSTS), 2),
                        "alerts": [h["name"] for h in HOSTS if h["mem"] > 70],
                    })
                elif path == "/metrics":
                    self._send(200, _metrics_text(state, REQUESTS_TOTAL, REQUESTS_IN_FLIGHT).encode("utf-8"), TEXT_CONTENT_TYPE)
                else:
                    self._json(404, {"error": "not found", "path": path})
            finally:
                with _LOCK:
                    REQUESTS_IN_FLIGHT -= 1
                if METRICS_BACKEND == "prometheus_client":
                    IN_FLIGHT.dec()

    return Handler


def _count_by_role() -> dict:
    out: dict[str, int] = {}
    for h in HOSTS:
        out[h["role"]] = out.get(h["role"], 0) + 1
    return out


def serve(port: int, state: State) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("0.0.0.0", port), make_handler(state))
    httpd.daemon_threads = True
    return httpd


# --- 自检 / 快照 --------------------------------------------------------------
def self_test() -> int:
    """绑 0 号端口起真服务，用 urllib 打每个端点并断言。"""
    import urllib.error
    import urllib.request

    checks = []
    state = State(version="self-test", fail_mode=os.environ.get("FAIL_MODE", "none"))
    httpd = serve(0, state)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    try:
        def get(p):
            try:
                with urllib.request.urlopen(base + p, timeout=5) as r:
                    return r.status, r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                return e.code, e.read().decode("utf-8")

        st, body = get("/healthz")
        checks.append(("GET /healthz -> 200", st == 200 and json.loads(body)["status"] == "ok"))

        st, body = get("/readyz")
        checks.append(("GET /readyz -> 200", st == 200 and json.loads(body)["status"] == "ready"))

        st, body = get("/version")
        checks.append(("GET /version -> 200 且带 version", st == 200 and json.loads(body)["version"] == "self-test"))

        st, body = get("/api/hosts")
        checks.append(("GET /api/hosts -> 4 台主机", st == 200 and json.loads(body)["count"] == 4))

        st, body = get("/api/summary")
        checks.append(("GET /api/summary -> 按角色聚合", st == 200 and json.loads(body)["by_role"] == {"web": 2, "db": 1, "cache": 1}))

        st, body = get("/metrics")
        checks.append(("GET /metrics -> 文本暴露格式", st == 200 and "# TYPE ops_http_requests_total counter" in body))

        st, body = get("/nope")
        checks.append(("GET /nope -> 404", st == 404))

        # 故障注入路径：就绪探针必须报 503
        bad = State(version="self-test", fail_mode="readiness")
        bad_httpd = serve(0, bad)
        bad_port = bad_httpd.server_address[1]
        threading.Thread(target=bad_httpd.serve_forever, daemon=True).start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{bad_port}/readyz", timeout=5) as r:
                bad_code = r.status
        except urllib.error.HTTPError as e:
            bad_code = e.code
        checks.append(("fail_mode=readiness -> /readyz 503", bad_code == 503))
        bad_httpd.shutdown()
    finally:
        httpd.shutdown()

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    if failed:
        print(f"❌ self-test 失败：{len(failed)}/{len(checks)} 项不通过 -> {failed}")
        return 1
    print(f"✅ self-test 通过：{len(checks)} 项断言全过 | backend={METRICS_BACKEND} | 端口={port}")
    return 0


def once() -> int:
    """不起服务，直接打印一份「快照」，方便在 CI 里做冒烟。"""
    state = State(version=os.environ.get("APP_VERSION", "dev"), fail_mode=os.environ.get("FAIL_MODE", "none"))
    ok_r, why_r = state.readiness()
    ok_l, why_l = state.liveness()
    snap = {
        "app": APP_NAME,
        "version": state.version,
        "metrics_backend": METRICS_BACKEND,
        "liveness": {"ok": ok_l, "reason": why_l},
        "readiness": {"ok": ok_r, "reason": why_r},
        "hosts": len(HOSTS),
        "by_role": _count_by_role(),
        "alerts": [h["name"] for h in HOSTS if h["mem"] > 70],
    }
    print(json.dumps(snap, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Day 183 · 运维平台 API 服务")
    p.add_argument("--port", type=int, default=8080, help="监听端口（默认 8080）")
    p.add_argument("--self-test", action="store_true", help="自检：绑 0 号端口打端点断言")
    p.add_argument("--once", action="store_true", help="打印一份状态快照后退出")
    p.add_argument("--fail-mode", choices=["none", "readiness", "liveness"], default=None,
                   help="故障注入：让就绪/存活探针失败（回滚演练用）")
    args = p.parse_args(argv)

    if args.fail_mode:
        os.environ["FAIL_MODE"] = args.fail_mode
    if args.self_test:
        return self_test()
    if args.once:
        return once()

    state = State(
        version=os.environ.get("APP_VERSION", "dev"),
        fail_mode=os.environ.get("FAIL_MODE", "none"),
    )
    httpd = serve(args.port, state)
    print(f"✅ {APP_NAME} v{state.version} 监听 0.0.0.0:{args.port} "
          f"(fail_mode={state.fail_mode}, metrics={METRICS_BACKEND})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n收到 Ctrl-C，退出")
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
