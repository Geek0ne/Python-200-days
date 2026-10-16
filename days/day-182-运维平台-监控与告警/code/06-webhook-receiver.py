#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 182 - 自动化运维平台（一）：服务器监控 + 告警
06 - 最小 webhook 接收端（实验用）：证明告警真的发出去了

要点：
- 03 里的 webhook 通道是「POST 一个 JSON 过去」。要验证它真发了，
  就得有一个真的接收端。本脚本就是那个接收端：收到一条打印一条、落一份盘。
- 不做任何鉴权/重试/队列——它只是实验台上的示波器，不是生产组件。

用法：
    python3 06-webhook-receiver.py --port 19090 --log /tmp/day182/hook.jsonl
    python3 06-webhook-receiver.py --self-test
"""

import argparse
import json
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ReceiverHandler(BaseHTTPRequestHandler):
    log_path = None
    received = 0

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            alert = json.loads(raw.decode("utf-8"))
        except ValueError:
            alert = {"_raw": raw.decode("utf-8", "replace")}
        ReceiverHandler.received += 1
        print("[%s] #%d %s status=%s severity=%s value=%s"
              % (time.strftime("%H:%M:%S"), ReceiverHandler.received,
                 alert.get("name"), alert.get("status"), alert.get("severity"), alert.get("value")))
        sys.stdout.flush()   # 被 kill 时缓冲会丢日志，逐条刷
        if self.log_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(alert, ensure_ascii=False) + "\n")
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        body = ("day182 webhook receiver: 已接收 %d 条\n" % ReceiverHandler.received).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *args):   # 静音
        pass


def self_test():
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)
        print(("  PASS  " if cond else "  FAIL  ") + msg)

    import tempfile
    print("== 06 webhook 接收端自检 ==")
    tmpdir = tempfile.mkdtemp(prefix="day182-hook-")
    log_path = os.path.join(tmpdir, "recv.jsonl")
    ReceiverHandler.log_path = log_path
    ReceiverHandler.received = 0
    srv = ThreadingHTTPServer(("127.0.0.1", 0), ReceiverHandler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    try:
        payload = {"name": "host_cpu_high", "status": "firing", "severity": "critical", "value": 95.0}
        req = urllib.request.Request(
            "http://127.0.0.1:%d/hook" % port,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            code = resp.getcode()
        check(code == 200, "POST /hook 返回 200（实测 %s）" % code)
        check(ReceiverHandler.received == 1, "接收端计数 +1（实测 %d）" % ReceiverHandler.received)
        check(os.path.exists(log_path) and "host_cpu_high" in open(log_path, encoding="utf-8").read(),
              "payload 落盘（%d 字节）" % (os.path.getsize(log_path) if os.path.exists(log_path) else 0))
        with urllib.request.urlopen("http://127.0.0.1:%d/status" % port, timeout=2.0) as resp:
            body = resp.read().decode("utf-8")
        check("已接收 1 条" in body, "GET /status 报告计数（实测 %s）" % body.strip())
    finally:
        srv.shutdown()
        srv.server_close()
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

    if failures:
        print("self-test 失败 %d 项" % len(failures))
        return 1
    print("self-test 通过 | POST 接收 + 落盘 + 计数 全部成立")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Day 182 · 06 最小 webhook 接收端（实验用）")
    ap.add_argument("--port", type=int, default=19090)
    ap.add_argument("--log", default="/tmp/day182/hook.jsonl")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    ReceiverHandler.log_path = args.log
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), ReceiverHandler)
    print("webhook 接收端已启动：http://127.0.0.1:%d/hook  （日志 %s，Ctrl-C 退出）" % (args.port, args.log))
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n共接收 %d 条。退出。" % ReceiverHandler.received)
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
