#!/usr/bin/env python3
"""
Day 185 · 服务本体 —— 一个"值得被一键部署"的最小运维平台 API

为什么要有这个文件？
    讲"一键部署"最容易变成空话："写个脚本 start.sh 就行了"。
    所以本课先有一个**真实的服务**（有存活探针、就绪探针、优雅停机、版本号），
    再让部署脚本去管它 —— 只有服务是真实的，部署脚本要解决的问题才是真实的。

接口（全部真机可 curl）：
    GET /healthz        存活：进程活着就 200（负载均衡/看门狗用）
    GET /readyz         就绪：**真正能对外服务**才 200，否则 503
                        （K8s readinessProbe / 部署脚本的"等到能用"用）
    GET /api/v1/hosts   业务接口：返回主机清单（来自 --data 指定的 JSON）
    GET /metrics        运行指标：请求数、启动时间、版本

运行方式：
    python3 00-platform-api.py --port 8200 --version v1.2.0 --data /tmp/p/hosts.json
    curl -s 127.0.0.1:8200/healthz; curl -s 127.0.0.1:8200/readyz
    python3 00-platform-api.py --self-test

两个刻意的设计（都是真实故障逼出来的）：
  1) 存活 ≠ 就绪。进程起来了、端口在听，不代表能干活（数据没加载完/依赖没连上）。
     只有一个探针的系统，会在"刚启动就被打流量"时大面积报错。
  2) 收到 SIGTERM 后**先把在途请求做完**再退出（优雅停机）。
     否则滚动发布时用户会看到一堆 ConnectionResetError。
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class State:
    version = "dev"
    started_at = time.time()
    ready_at: float | None = None
    ready = False
    requests = 0
    hosts: list = []
    lock = threading.Lock()


def log(event: str, **fields) -> None:
    """极简 JSON Lines 日志（Day 184 的做法，这里复用一下，不引入依赖）。"""
    payload = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
               "level": "INFO", "service": "ops-platform-api", "msg": event}
    payload.update(fields)
    print(json.dumps(payload, ensure_ascii=False), flush=True)


class TrackingServer(ThreadingHTTPServer):
    """自己记账的 HTTP 服务器 —— 为了做到**真正的**优雅停机。

    为什么不能指望 socketserver 自带的机制（本日真机踩到）：
        `ThreadingMixIn.server_close()` 只会 join 它自己记录的线程，而我们的处理线程是
        daemon（daemon_threads=True）。实测：SIGTERM 之后进程 0.297s 就退出了，
        正在 sleep 的 /slow 请求被连根切断，客户端收到 RemoteDisconnected。
        也就是说：**"我设了 SIGTERM handler" 不等于 "在途请求会被做完"**。

    所以这里显式维护一个"在途请求计数"，停机时等它归零（或到宽限期）。
    """
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._active = 0
        self._cv = threading.Condition()
        self.max_seen = 0

    def process_request_thread(self, request, client_address):
        with self._cv:
            self._active += 1
            self.max_seen = max(self.max_seen, self._active)
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._cv:
                self._active -= 1
                self._cv.notify_all()

    @property
    def active_requests(self) -> int:
        with self._cv:
            return self._active

    def wait_idle(self, timeout: float) -> tuple[bool, float]:
        """等在途请求归零。返回 (是否排空, 实际等待秒数)。"""
        started = time.monotonic()
        deadline = started + timeout
        with self._cv:
            while self._active > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False, round(time.monotonic() - started, 3)
                self._cv.wait(remaining)
        return True, round(time.monotonic() - started, 3)


class Handler(BaseHTTPRequestHandler):
    server_version = "ops-platform/1.0"

    def log_message(self, *args):  # 不把 HTTP 访问日志混进我们的结构化日志
        pass

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        with State.lock:
            State.requests += 1
        path = self.path.split("?")[0]

        if path == "/healthz":
            self._json(200, {"status": "ok", "version": State.version,
                             "pid": __import__("os").getpid()})
        elif path == "/readyz":
            if State.ready:
                self._json(200, {"ready": True, "warmup_s": round(State.ready_at - State.started_at, 3)
                                 if State.ready_at else None})
            else:
                # 503 是"还没准备好"的标准语义：客户端应该重试，而不是认为服务挂了
                self._json(503, {"ready": False, "version": State.version})
        elif path == "/api/v1/hosts":
            if not State.ready:
                self._json(503, {"error": "not ready"})
            else:
                self._json(200, {"count": len(State.hosts), "hosts": State.hosts})
        elif path == "/slow":
            # 故意慢的接口：用来验证「优雅停机时在途请求会被做完」。
            # 没有这种接口，就永远测不出 kill -9 和 SIGTERM 的区别。
            from urllib.parse import parse_qs, urlparse
            ms = int(parse_qs(urlparse(self.path).query).get("ms", ["500"])[0])
            time.sleep(ms / 1000.0)
            self._json(200, {"slept_ms": ms, "done": True})
        elif path == "/metrics":
            self._json(200, {"requests_total": State.requests, "version": State.version,
                             "uptime_s": round(time.time() - State.started_at, 3),
                             "ready": State.ready})
        else:
            self._json(404, {"error": "not found", "path": path})


def warmup(delay: float, fail_ready: bool, data_file: str | None) -> None:
    """模拟"启动后需要一点时间才能干活"：加载数据、建连接池、预热缓存。"""
    log("warmup_start", delay_s=delay, fail_ready=fail_ready)
    time.sleep(delay)
    if data_file:
        try:
            State.hosts = json.loads(Path(data_file).read_text(encoding="utf-8"))
            log("data_loaded", hosts=len(State.hosts))
        except FileNotFoundError:
            log("data_missing", file=data_file)
    if fail_ready:
        # 模拟"这个版本坏了"：进程活着、端口在听、但永远不就绪 → 部署脚本必须回滚
        log("ready_never", reason="simulated bad release")
        return
    State.ready = True
    State.ready_at = time.time()
    log("ready", warmup_s=round(State.ready_at - State.started_at, 3))


def self_test() -> int:
    """离线自证：真起服务 → 真探针 → 断言 not-ready 阶段与 ready 阶段的行为差异。"""
    import tempfile
    import urllib.error
    import urllib.request

    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "hosts.json"
        data.write_text(json.dumps([{"host": "web-01", "ip": "10.0.0.11"}]), encoding="utf-8")
        State.ready = False
        State.hosts = []
        State.started_at = time.time()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        httpd.daemon_threads = True
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        threading.Thread(target=warmup, args=(0.6, False, str(data)), daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        def get(path):
            try:
                with urllib.request.urlopen(base + path, timeout=3) as r:
                    return r.status, json.loads(r.read())
            except urllib.error.HTTPError as e:
                return e.code, json.loads(e.read())

        # 存活探针：进程活着就该是 200（哪怕还没就绪）
        code, body = get("/healthz")
        assert code == 200 and body["status"] == "ok", (code, body)

        # 就绪探针：warmup 期间必须 503 —— 这是本文件最重要的断言
        code, body = get("/readyz")
        assert code == 503 and body["ready"] is False, (code, body)
        code, body = get("/api/v1/hosts")
        assert code == 503, (code, body)   # 没就绪时业务接口也不该给数据

        # 等就绪
        deadline = time.time() + 5
        while time.time() < deadline:
            code, body = get("/readyz")
            if code == 200:
                break
            time.sleep(0.1)
        assert code == 200 and body["ready"] is True, (code, body)

        code, body = get("/api/v1/hosts")
        assert code == 200 and body["count"] == 1, (code, body)
        code, body = get("/metrics")
        assert body["requests_total"] >= 4, body

        httpd.shutdown()
        print("✅ self-test 通过：未就绪时 /readyz=503 且业务接口拒绝服务，就绪后全部 200")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="运维平台 API（Day 185 的被部署对象）")
    parser.add_argument("--port", type=int, default=8200)
    parser.add_argument("--version", default="v1.0.0")
    parser.add_argument("--data", default=None)
    parser.add_argument("--ready-delay", type=float, default=1.0)
    parser.add_argument("--fail-ready", action="store_true")
    parser.add_argument("--grace", type=float, default=10.0,
                        help="停机时等在途请求的上限秒数")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    State.version = args.version
    State.started_at = time.time()
    httpd = TrackingServer(("127.0.0.1", args.port), Handler)

    def on_term(signum, frame):   # 优雅停机：停止接收新连接，等在途请求结束
        log("sigterm_received", signum=signum)
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)

    threading.Thread(target=warmup, args=(args.ready_delay, args.fail_ready, args.data),
                     daemon=True).start()
    log("listen", port=args.port, version=args.version)
    try:
        httpd.serve_forever()
    finally:
        # 先停止接收新连接（on_term 里的 shutdown 已经做了），再把在途请求排空 —— 顺序不能反。
        drained, waited = httpd.wait_idle(args.grace)
        log("drained" if drained else "drain_timeout", waited_s=waited,
            active=httpd.active_requests, max_concurrent=httpd.max_seen)
        httpd.server_close()
        log("stopped", requests_total=State.requests)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
