#!/usr/bin/env python3
"""
Day 177 — Prometheus + Grafana
03 · 用 HTTP API 查 PromQL（instant / range）

Prometheus 的查询接口就两个，Grafana 的每个图背后都是它们：

    GET /api/v1/query?query=<expr>&time=<unix>        # 瞬时（instant）
    GET /api/v1/query_range?query=&start=&end=&step=  # 区间（range）

本脚本把「查询 → 解析 → 打印」这条链路走通，并内建一个离线桩服务，
所以没有 Prometheus 也能 `--self-test`。

用法：
    python3 03-promql-query.py --url http://localhost:9090 --query 'up'
    python3 03-promql-query.py --url http://localhost:9090 --cheatsheet
    python3 03-promql-query.py --range --query 'rate(app_http_requests_total[1m])'
    python3 03-promql-query.py --self-test     # 离线桩，不需 Prometheus
"""

import argparse
import json
import sys
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CHEATSHEET = [
    ("up", "每个 target 是否在拉；1=活，0=死"),
    ("app_http_requests_total", "原始累计计数（counter 永远涨）"),
    ("rate(app_http_requests_total[1m])", "每秒速率：counter 的正确打开方式"),
    ("increase(app_http_requests_total[5m])", "5 分钟内的增量（近似整数）"),
    ("sum by (status) (rate(app_http_requests_total[1m]))", "按状态码聚合的 QPS"),
    ("histogram_quantile(0.95, rate(app_http_request_duration_seconds_bucket[5m]))",
     "P95 延迟；必须带 _bucket + rate"),
    ("topk(3, rate(app_http_requests_total[1m]))", "最热的前 3 条时间线"),
    ("app_http_inflight > 5", "瞬时过滤：只看积压超过 5 的"),
    ("time() - process_start_time_seconds", "进程已运行秒数（外推型用法）"),
]


def query_instant(base, expr, at=None):
    q = {"query": expr}
    if at:
        q["time"] = str(at)
    url = f"{base}/api/v1/query?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def query_range(base, expr, start, end, step):
    q = {"query": expr, "start": str(start), "end": str(end), "step": str(step)}
    url = f"{base}/api/v1/query_range?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def fmt_value(v):
    """Prometheus 的值一律是字符串，且可能是 'NaN' / '+Inf'。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f != f:
        return "NaN"
    return f"{f:.4f}".rstrip("0").rstrip(".")


def print_instant(payload):
    if payload.get("status") != "success":
        print(f"❌ 查询失败: {payload.get('errorType')}: {payload.get('error')}")
        return 2
    data = payload["data"]
    result = data["result"]
    print(f"# resultType={data['resultType']} · 时间线 {len(result)} 条")
    if not result:
        print("# （无数据：表达式没错，只是这段时间没有样本）")
        return 0
    for series in result[:15]:
        metric = series["metric"]
        name = metric.get("__name__", "")
        labels = ",".join(f"{k}={v}" for k, v in metric.items() if k != "__name__")
        label_str = f"{{{labels}}}" if labels else ""
        ts, val = series["value"]
        t = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S")
        print(f"{name}{label_str}  {fmt_value(val)}   @{t}Z")
    if len(result) > 15:
        print(f"# …还有 {len(result) - 15} 条")
    return 0


def print_range(payload):
    if payload.get("status") != "success":
        print(f"❌ 查询失败: {payload.get('errorType')}: {payload.get('error')}")
        return 2
    result = payload["data"]["result"]
    print(f"# resultType={payload['data']['resultType']} · 时间线 {len(result)} 条")
    for series in result[:5]:
        labels = ",".join(f"{k}={v}" for k, v in series["metric"].items())
        values = series["values"]
        # 只打印首尾两个点，中间用 … 省略
        head = f"{fmt_value(values[0][1])}"
        tail = f"{fmt_value(values[-1][1])}"
        print(f"{labels or '(no labels)'}  点数={len(values)}  {head} … {tail}")
    return 0


# --- 离线桩：不需要 Prometheus 也能自检 --------------------------------------
class _StubHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/v1/query_range"):
            body = {
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {"metric": {"__name__": "up", "job": "app"},
                         "values": [[1_700_000_000, "1"], [1_700_000_015, "1"],
                                    [1_700_000_030, "0"]]}
                    ],
                },
            }
        else:
            body = {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {"metric": {"__name__": "up", "job": "app", "instance": "127.0.0.1:9101"},
                         "value": [1_700_000_000, "1"]},
                        {"metric": {"__name__": "app_http_inflight"},
                         "value": [1_700_000_000, "0.5"]},
                    ],
                },
            }
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


def self_test():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    try:
        p = query_instant(base, "up")
        assert p["status"] == "success"
        assert p["data"]["resultType"] == "vector"
        assert len(p["data"]["result"]) == 2
        assert p["data"]["result"][0]["metric"]["job"] == "app"
        assert fmt_value("1") == "1" and fmt_value("NaN") == "NaN"

        m = query_range(base, "up", 1_700_000_000, 1_700_000_030, 15)
        assert m["data"]["resultType"] == "matrix"
        assert len(m["data"]["result"][0]["values"]) == 3

        # 错误分支：真 Prometheus 失败时返回 status=error
        assert print_instant({"status": "error", "errorType": "bad_data",
                              "error": "parse error"}) == 2

        print(f"✅ self-test 通过（离线桩 :{port}）：instant 2 条向量、range 3 个点、"
              f"错误分支返回 2、NaN/整数格式化正确")
        return 0
    finally:
        srv.shutdown()
        srv.server_close()


def main():
    ap = argparse.ArgumentParser(description="Day 177 · 03 查 PromQL")
    ap.add_argument("--url", default="http://localhost:9090", help="Prometheus 地址")
    ap.add_argument("--query", default="up", help="PromQL 表达式")
    ap.add_argument("--range", action="store_true", help="走 query_range")
    ap.add_argument("--minutes", type=int, default=5, help="range 回看分钟数")
    ap.add_argument("--step", type=int, default=15, help="range 步长（秒）")
    ap.add_argument("--cheatsheet", action="store_true", help="打印常用 PromQL")
    ap.add_argument("--self-test", action="store_true", help="离线桩自检")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(self_test())
    if args.cheatsheet:
        print("# 常用 PromQL（表达式 → 用途）")
        for expr, note in CHEATSHEET:
            print(f"  {expr:70s} # {note}")
        return

    if args.range:
        import time
        end = int(time.time())
        start = end - args.minutes * 60
        payload = query_range(args.url, args.query, start, end, args.step)
        sys.exit(print_range(payload))
    else:
        payload = query_instant(args.url, args.query)
        sys.exit(print_instant(payload))


if __name__ == "__main__":
    main()
