#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 182 - 自动化运维平台（一）：服务器监控 + 告警
03 - 告警路由与降级：按严重级别选通道，通道挂了自动降级

要点：
- 「路由」= 告警对象 -> 通道链。critical 走 webhook 值班群，warning 进文件，
  抖动中的告警只留档不叫人（降噪）。
- 「降级」= 主通道发不出去时，按 fallback 链依次尝试，直到有一个成功。
  真实世界里 webhook 打得最多，也最容易挂（对端 502、网络抖动）。
- 每个通道内部还有重试（attempts）；重试完还不成才降级——别把一次网络抖动
  当成「对端全挂」。
- --dry-run：只打印将发往哪里，不碰网络、不写文件（演练/CI 用）。

用法：
    python3 03-alert-routing.py --self-test
    python3 03-alert-routing.py --dry-run --demo
    python3 03-alert-routing.py --demo --webhook http://127.0.0.1:9999/hook --file /tmp/day182/alerts.jsonl
"""

import argparse
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


# --------------------------------------------------------------------------- #
# 事件 -> 告警对象
# --------------------------------------------------------------------------- #
def to_alert(event):
    """把 02 引擎吐出的事件包装成「告警对象」——后续路由/去重都吃这个结构。"""
    etype = event["type"]
    if etype == "firing":
        status = "firing"
    elif etype == "resolved":
        status = "resolved"
    else:
        status = "pending"      # pending / dropped 都不是「可通知」的状态
    is_fire = status == "firing"
    return {
        "name": event["rule"],
        "type": etype,
        "status": status,
        "severity": event.get("severity", "warning"),
        "metric": event.get("metric"),
        "value": event.get("value"),
        "threshold": event.get("threshold"),
        "flapping": bool(event.get("flapping", False)),
        "summary": "[%s] %s %s %s (值=%s 阈值=%s)"
                   % (event.get("severity", "warning"), event["rule"], event.get("metric"),
                      {"firing": "越界", "resolved": "恢复"}.get(status, "待观察"),
                      event.get("value"), event.get("threshold")),
        "labels": {"rule": event["rule"], "metric": event.get("metric")},
        "ts": event.get("ts"),
    }


# --------------------------------------------------------------------------- #
# 通道
# --------------------------------------------------------------------------- #
class Channel:
    name = "channel"

    def send(self, alert):
        raise NotImplementedError


class ConsoleChannel(Channel):
    def __init__(self, name="console"):
        self.name = name

    def send(self, alert):
        print("      [console] %s" % alert["summary"])
        return True, "printed"


class FileChannel(Channel):
    def __init__(self, path, name="file"):
        self.name = name
        self.path = path

    def send(self, alert):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert, ensure_ascii=False) + "\n")
            return True, self.path
        except OSError as exc:
            return False, "OSError: " + str(exc)


class WebhookChannel(Channel):
    def __init__(self, url, timeout=1.5, name="webhook"):
        self.name = name
        self.url = url
        self.timeout = timeout

    def send(self, alert):
        body = json.dumps(alert, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=body, method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "day182-monitor/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                code = resp.getcode()
                resp.read(256)
            if 200 <= code < 300:
                return True, "HTTP %s" % code
            return False, "HTTP %s（非 2xx）" % code
        except urllib.error.HTTPError as exc:
            return False, "HTTPError: HTTP %s" % exc.code
        except Exception as exc:
            return False, type(exc).__name__ + ": " + str(exc)


class DryRunChannel(Channel):
    """--dry-run 用：名字照旧，但只打印，不产生任何副作用。"""

    def __init__(self, name):
        self.name = name

    def send(self, alert):
        print("      [dry-run] 本应发往 %-8s -> %s" % (self.name, alert["name"]))
        return True, "dry-run"


# --------------------------------------------------------------------------- #
# 路由
# --------------------------------------------------------------------------- #
def default_routes():
    return [
        {"name": "flap-silenced", "match": {"flapping": True}, "primary": "file", "fallback": []},
        {"name": "critical", "match": {"severity": "critical"}, "primary": "webhook", "fallback": ["file", "console"]},
        {"name": "warning", "match": {"severity": "warning"}, "primary": "file", "fallback": ["console"]},
        {"name": "default", "match": {}, "primary": "console", "fallback": []},
    ]


class Router:
    def __init__(self, channels, routes=None, attempts=2, verbose=True):
        self.channels = {c.name: c for c in channels}
        self.routes = routes if routes is not None else default_routes()
        self.attempts = attempts
        self.verbose = verbose

    def select_route(self, alert):
        for route in self.routes:
            matched = all(alert.get(k) == v for k, v in route.get("match", {}).items())
            if matched:
                return route
        return {"name": "default", "match": {}, "primary": "console", "fallback": []}

    def deliver(self, alert):
        route = self.select_route(alert)
        chain = [route["primary"]] + list(route.get("fallback", []))
        report = {
            "alert": alert["name"],
            "severity": alert["severity"],
            "route": route["name"],
            "chain": chain,
            "attempts": {},
            "errors": [],
            "delivered_by": None,
            "detail": None,
        }
        for name in chain:
            channel = self.channels.get(name)
            if channel is None:
                report["errors"].append("%s: 通道未定义" % name)
                continue
            for attempt in range(1, self.attempts + 1):
                report["attempts"][name] = attempt
                ok, detail = channel.send(alert)
                if ok:
                    report["delivered_by"] = name
                    report["detail"] = detail
                    return report
                report["errors"].append("%s(第%d次): %s" % (name, attempt, detail))
                if self.verbose:
                    print("      %s 发送失败（第 %d 次）：%s" % (name, attempt, detail))
        return report


def make_channels(webhook_url, file_path, dry_run):
    if dry_run:
        return [DryRunChannel("console"), DryRunChannel("file"), DryRunChannel("webhook")]
    return [ConsoleChannel(), FileChannel(file_path), WebhookChannel(webhook_url)]


# --------------------------------------------------------------------------- #
# 自检用的 webhook 收数桩
# --------------------------------------------------------------------------- #
class _HookHandler(BaseHTTPRequestHandler):
    received = []
    mode = {"code": 200}

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except ValueError:
            payload = {"_raw": raw.decode("utf-8", "replace")}
        _HookHandler.received.append(payload)
        code = _HookHandler.mode["code"]
        body = b"ok" if code == 200 else b"boom"
        self.send_response(code)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):
        pass


def _free_port():
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --------------------------------------------------------------------------- #
# 自检
# --------------------------------------------------------------------------- #
def self_test(webhook_url=None, file_path=None):
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    print("== 03 路由/降级自检 ==")
    tmpdir = tempfile.mkdtemp(prefix="day182-routing-")

    # 起收数桩
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _HookHandler)
    hook_port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    hook_url = "http://127.0.0.1:%d/hook" % hook_port
    try:
        # 1) 主通道可用：critical 走 webhook，一次成功
        _HookHandler.received.clear()
        _HookHandler.mode["code"] = 200
        f1 = os.path.join(tmpdir, "a.jsonl")
        router = Router(make_channels(hook_url, f1, dry_run=False), attempts=2, verbose=False)
        alert = to_alert({"rule": "host_cpu_high", "type": "firing", "severity": "critical",
                          "metric": "host_metrics.cpu_percent", "value": 95.0, "threshold": 90,
                          "flapping": False, "ts": 1.0})
        rep = router.deliver(alert)
        check(rep["delivered_by"] == "webhook", "critical -> webhook 投递成功（实测 %s）" % rep["delivered_by"])
        check(rep["attempts"].get("webhook") == 1, "主通道第 1 次就成功，不重试（实测 attempts=%s）" % rep["attempts"].get("webhook"))
        check(_HookHandler.received and _HookHandler.received[0]["name"] == "host_cpu_high",
              "收数桩真的收到了 payload（实测 %d 条）" % len(_HookHandler.received))

        # 2) 主通道返回 500：重试 attempts 次后降级到 file
        _HookHandler.received.clear()
        _HookHandler.mode["code"] = 500
        f2 = os.path.join(tmpdir, "b.jsonl")
        router = Router(make_channels(hook_url, f2, dry_run=False), attempts=2, verbose=False)
        rep = router.deliver(alert)
        check(rep["delivered_by"] == "file", "webhook 返回 500 -> 降级到 file（实测 %s）" % rep["delivered_by"])
        check(rep["attempts"].get("webhook") == 2, "降级前在主通道重试了 2 次（实测 %s）" % rep["attempts"].get("webhook"))
        check(len(rep["errors"]) == 2, "记录 2 条失败原因（实测 %d 条）" % len(rep["errors"]))
        check(os.path.exists(f2) and "host_cpu_high" in open(f2, encoding="utf-8").read(),
              "降级通道真的落盘了（%d 字节）" % os.path.getsize(f2))

        # 3) 主通道连不上（端口没人听）：连接被拒 -> 降级到 file
        dead = _free_port()
        f3 = os.path.join(tmpdir, "c.jsonl")
        router = Router(make_channels("http://127.0.0.1:%d/hook" % dead, f3, dry_run=False),
                        attempts=2, verbose=False)
        rep = router.deliver(alert)
        check(rep["delivered_by"] == "file", "webhook 连不上 -> 降级到 file（实测 %s）" % rep["delivered_by"])
        check(any("URLError" in e or "refused" in e.lower() for e in rep["errors"]),
              "失败原因里有连接被拒的证据（%s）" % rep["errors"][0][:80])

        # 4) warning 不走 webhook
        _HookHandler.received.clear()
        f4 = os.path.join(tmpdir, "d.jsonl")
        router = Router(make_channels(hook_url, f4, dry_run=False), attempts=1, verbose=False)
        warn = to_alert({"rule": "host_mem_high", "type": "firing", "severity": "warning",
                         "metric": "host_metrics.mem_percent", "value": 88.0, "threshold": 85,
                         "flapping": False, "ts": 2.0})
        rep = router.deliver(warn)
        check(rep["chain"] == ["file", "console"], "warning 的路由链是 file->console（实测 %s）" % rep["chain"])
        check(_HookHandler.received == [], "warning 不打扰 webhook（实测收到 %d 条）" % len(_HookHandler.received))

        # 5) 抖动中的告警只留档、不叫人
        f5 = os.path.join(tmpdir, "e.jsonl")
        router = Router(make_channels(hook_url, f5, dry_run=False), attempts=1, verbose=False)
        flap = to_alert({"rule": "host_cpu_high", "type": "firing", "severity": "critical",
                         "metric": "host_metrics.cpu_percent", "value": 95.0, "threshold": 90,
                         "flapping": True, "ts": 3.0})
        rep = router.deliver(flap)
        check(rep["route"] == "flap-silenced" and rep["delivered_by"] == "file",
              "抖动告警走静默路由，只落 file（实测 route=%s by=%s）" % (rep["route"], rep["delivered_by"]))

        # 6) dry-run：不碰网络不写盘
        f6 = os.path.join(tmpdir, "f.jsonl")
        router = Router(make_channels(hook_url, f6, dry_run=True), attempts=1, verbose=False)
        rep = router.deliver(alert)
        check(rep["delivered_by"] == "webhook" and rep["detail"] == "dry-run",
              "dry-run 报告投递成功但 detail=dry-run（实测 %s）" % rep["detail"])
        check(not os.path.exists(f6) and _HookHandler.received == [],
              "dry-run 没写文件也没发包（实测 received=%d）" % len(_HookHandler.received))

        # 7) 所有通道都挂 -> delivered_by=None（不能假装成功）
        dead2 = _free_port()
        router = Router([WebhookChannel("http://127.0.0.1:%d/h" % dead2),
                         FileChannel("/proc/不可写/钉死.jsonl", name="file")],
                        routes=[{"name": "all-dead", "match": {}, "primary": "webhook", "fallback": ["file"]}],
                        attempts=1, verbose=False)
        rep = router.deliver(alert)
        check(rep["delivered_by"] is None, "全部通道失败时 delivered_by 为 None（实测 %s）" % rep["delivered_by"])
        check(len(rep["errors"]) >= 2, "两条通道的失败都被记录（实测 %d 条）" % len(rep["errors"]))
    finally:
        srv.shutdown()
        srv.server_close()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    if failures:
        print("self-test 失败 %d 项" % len(failures))
        return 1
    print("self-test 通过 | 路由 4 例 + 降级 2 例 + dry-run + 全失败兜底 全部成立")
    return 0


def demo(webhook_url, file_path, dry_run):
    router = Router(make_channels(webhook_url, file_path, dry_run=dry_run), attempts=2)
    alerts = [
        to_alert({"rule": "host_disk_high", "type": "firing", "severity": "critical",
                  "metric": "host_metrics.disk_percent", "value": 91.0, "threshold": 85,
                  "flapping": False, "ts": 1.0}),
        to_alert({"rule": "app_latency_slow", "type": "firing", "severity": "warning",
                  "metric": "app_metrics[0].latency_ms", "value": 880.0, "threshold": 500,
                  "flapping": False, "ts": 2.0}),
        to_alert({"rule": "host_cpu_high", "type": "firing", "severity": "critical",
                  "metric": "host_metrics.cpu_percent", "value": 96.0, "threshold": 90,
                  "flapping": True, "ts": 3.0}),
    ]
    for alert in alerts:
        print("  >> %s" % alert["summary"])
        rep = router.deliver(alert)
        print("     路由=%-13s 链=%-28s 投递=%s %s"
              % (rep["route"], "->".join(rep["chain"]), rep["delivered_by"] or "失败", rep["detail"] or ""))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Day 182 · 03 告警路由与降级")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="只打印路由决定，不碰网络/文件")
    ap.add_argument("--webhook", default="http://127.0.0.1:9999/hook", help="webhook 地址")
    ap.add_argument("--file", default=os.path.join(tempfile.gettempdir(), "day182", "alerts.jsonl"))
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if args.demo or args.dry_run:
        print("路由演练%s（webhook=%s file=%s）"
              % ("（dry-run）" if args.dry_run else "", args.webhook, args.file))
        return demo(args.webhook, args.file, args.dry_run)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
