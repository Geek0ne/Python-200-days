#!/usr/bin/env python3
"""
Day 177 — Prometheus + Grafana
01 · 让 Python 应用暴露指标（/metrics 端点）

要点：
- Prometheus 是 **拉（pull）** 模型：它定时来 HTTP GET 你的 /metrics，你不推。
- /metrics 返回的是纯文本 **exposition format**（文本暴露格式），不是 JSON。
- 优先用官方库 prometheus_client 生成；没装时退化为 stdlib 手写，
  正好把「格式本身长什么样」摊开给你看。

用法：
    python3 01-expose-metrics.py --once          # 打印一次指标快照（不用起服务）
    python3 01-expose-metrics.py --port 9101     # 起服务，浏览器/curl 访问 /metrics
    python3 01-expose-metrics.py --self-test     # 自检：绑 0 号端口，抓取并断言
"""

import argparse
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- 后端选择：有 prometheus_client 就用它，没有就退到 stdlib -----------------
try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    BACKEND = "prometheus_client"
except ImportError:  # pragma: no cover - 取决于环境
    BACKEND = "stdlib-fallback"

CONTENT_TYPE_LATEST_FALLBACK = "text/plain; version=0.0.4; charset=utf-8"


class StdlibMetrics:
    """没有 prometheus_client 时的最小实现：只支持 counter 和 gauge。

    它不是玩具——它输出的就是 Prometheus 真正吃的文本格式。
    """

    def __init__(self):
        self._families = {}  # name -> (help, type, {labels_tuple: value})

    def _register(self, name, help_text, mtype):
        if name not in self._families:
            self._families[name] = [help_text, mtype, {}]

    def counter(self, name, help_text):
        self._register(name, help_text, "counter")
        return _StdlibCounter(self, name)

    def gauge(self, name, help_text):
        self._register(name, help_text, "gauge")
        return _StdlibGauge(self, name)

    def _set(self, name, labels, value):
        self._families[name][2][tuple(sorted(labels.items()))] = value

    def _inc(self, name, labels, delta):
        self._set(name, labels, self._families[name][2].get(tuple(sorted(labels.items())), 0.0) + delta)

    def _get(self, name, labels):
        return self._families[name][2].get(tuple(sorted(labels.items())), 0.0)

    def render(self):
        lines = []
        for name, (help_text, mtype, samples) in self._families.items():
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {mtype}")
            if not samples:
                lines.append(f"{name} 0.0")
            for labels, value in samples.items():
                if labels:
                    label_str = ",".join(f'{k}="{v}"' for k, v in labels)
                    lines.append(f"{name}{{{label_str}}} {_fmt(value)}")
                else:
                    lines.append(f"{name} {_fmt(value)}")
        if not lines:
            lines.append("# (empty)")
        return "\n".join(lines) + "\n"


class _StdlibCounter:
    def __init__(self, metrics, name):
        self._m, self._n = metrics, name

    def inc(self, amount=1.0, **labels):
        self._m._inc(self._n, labels, amount)

    def labels(self, **labels):
        return _StdlibChild(self._m, self._n, labels)


class _StdlibGauge:
    def __init__(self, metrics, name):
        self._m, self._n = metrics, name

    def set(self, value, **labels):
        self._m._set(self._n, labels, value)

    def inc(self, amount=1.0, **labels):
        self._m._inc(self._n, labels, amount)

    def dec(self, amount=1.0, **labels):
        self._m._inc(self._n, labels, -amount)

    def labels(self, **labels):
        return _StdlibChild(self._m, self._n, labels)


class _StdlibChild:
    def __init__(self, metrics, name, labels):
        self._m, self._n, self._l = metrics, name, labels

    def inc(self, amount=1.0):
        self._m._inc(self._n, self._l, amount)

    def set(self, value):
        self._m._set(self._n, self._l, value)


def _fmt(v):
    """Prometheus 文本格式：整数就不带小数点，浮点保留原样。"""
    return str(int(v)) if float(v).is_integer() else repr(float(v))


# --- 业务指标：一个「假装在服务的 HTTP 应用」---------------------------------
def build_app():
    """返回 (render_callable, content_type)。"""
    if BACKEND == "prometheus_client":
        requests_total = Counter(
            "app_http_requests_total", "HTTP 请求总数", ["method", "path", "status"]
        )
        inflight = Gauge("app_http_inflight", "正在处理的请求数")
        latency = Histogram(
            "app_http_request_duration_seconds",
            "请求耗时（秒）",
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
        )

        def render():
            return generate_latest(), CONTENT_TYPE_LATEST

        def observe(path, status, seconds):
            inflight.inc()
            time.sleep(seconds)
            inflight.dec()
            requests_total.labels(method="GET", path=path, status=str(status)).inc()
            latency.observe(seconds)

        app = {
            "render": render,
            "observe": observe,
            "names": ["app_http_requests_total", "app_http_inflight",
                      "app_http_request_duration_seconds"],
        }
        return app

    m = StdlibMetrics()
    requests_total = m.counter("app_http_requests_total", "HTTP 请求总数")
    inflight = m.gauge("app_http_inflight", "正在处理的请求数")

    def render():
        return m.render().encode("utf-8"), CONTENT_TYPE_LATEST_FALLBACK

    def observe(path, status, seconds):
        inflight.inc()
        time.sleep(seconds)
        inflight.dec()
        requests_total.labels(method="GET", path=path, status=status).inc()

    return {
        "render": render,
        "observe": observe,
        "names": ["app_http_requests_total", "app_http_inflight"],
    }


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/metrics":
                payload, ctype = app["render"]()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            else:
                status = 404 if self.path == "/missing" else 200
                app["observe"](self.path, status, 0.01)
                body = b'{"ok":true}\n'
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def log_message(self, *args):  # 静音，别刷屏
            pass

    return Handler


def simulate_traffic(app):
    for path, status in [("/", 200), ("/", 200), ("/api/items", 200), ("/missing", 404)]:
        app["observe"](path, status, 0.02)


def run_once(app):
    simulate_traffic(app)
    payload, ctype = app["render"]()
    sys.stdout.write(payload.decode("utf-8"))
    print(f"\n# Content-Type: {ctype}")
    print(f"# backend: {BACKEND}")


def run_server(app, port):
    srv = ThreadingHTTPServer(("0.0.0.0", port), make_handler(app))
    print(f"[{BACKEND}] 监听 0.0.0.0:{port}，指标在 http://0.0.0.0:{port}/metrics")
    print("按 Ctrl-C 停止")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        srv.server_close()


def self_test():
    """自检：绑 0 号端口（让内核分配），起真服务，抓 /metrics 并断言。"""
    import urllib.request

    app = build_app()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        simulate_traffic(app)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5) as r:
            body = r.read().decode("utf-8")
            ctype = r.headers.get("Content-Type", "")
        assert "app_http_requests_total" in body, "缺少 app_http_requests_total"
        assert "app_http_inflight" in body, "缺少 app_http_inflight"
        assert "# TYPE app_http_requests_total counter" in body, "缺少 TYPE 行"
        assert 'path="/missing",status="404"' in body.replace(" ", "") or \
               'status="404"' in body, "缺少 404 标签样本"
        # 值断言：4 次请求 → 至少有一个 path/status 组合累计到 2（"/" 打了两次）
        assert 'app_http_requests_total{method="GET",path="/",status="200"} 2' in body \
               or 'app_http_requests_total{path="/",status="200"} 2' in body, \
               "累计计数不对（期望 / 200 出现 2 次）"
        print(f"✅ self-test 通过 | backend={BACKEND} | 端口={port} | "
              f"Content-Type={ctype.split(';')[0]} | 抓取 {len(body)} 字节")
        return 0
    finally:
        srv.shutdown()
        srv.server_close()


def main():
    ap = argparse.ArgumentParser(description="Day 177 · 01 暴露指标")
    ap.add_argument("--port", type=int, default=9101, help="监听端口（默认 9101）")
    ap.add_argument("--once", action="store_true", help="只打印一次指标快照后退出")
    ap.add_argument("--self-test", action="store_true", help="起临时服务并断言 /metrics")
    args = ap.parse_args()

    # 注意：build_app() 会向 prometheus_client 的默认 registry 注册指标，
    # 同一进程里调用两次会抛 DuplicateTimeseries —— 所以只在这里建一次。
    if args.self_test:
        sys.exit(self_test())

    app = build_app()
    if args.once:
        run_once(app)
        return
    run_server(app, args.port)


if __name__ == "__main__":
    main()
