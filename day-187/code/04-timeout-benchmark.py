#!/usr/bin/env python3
"""
Day 187 · 04 — 性能与超时：open / closed / filtered 的真实耗时

扫描器的速度不由"端口数量"决定，而由**最慢的那类端口**决定：
  · open     ：本机回环通常 <1ms
  · closed   ：内核立刻回 RST，通常 <1ms
  · filtered ：防火墙 DROP，必须等超时，耗时 ≈ timeout × 重试次数

本脚本用真实 socket 测三类目标，给出中位数，说明：
  1. 为什么扫描器必须限制超时；
  2. 为什么"扫一个 /16 网段"在没有并发时会跑到天荒地老；
  3. 并发能把"等待"重叠掉，但不能突破单次 timeout 的下限。

用法：
  python3 04-timeout-benchmark.py
  python3 04-timeout-benchmark.py --self-test
"""

from __future__ import annotations

import argparse
import socket
import statistics
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def timed_connect(host: str, port: int, timeout: float) -> tuple[str, float]:
    started = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        code = sock.connect_ex((host, port))
        if code == 0:
            state = "open"
        elif code in (111, 61, 10061):
            state = "closed"
        elif code in (11, 115, 110, 60, 10060):
            # 11=EAGAIN：真实实测中黑洞地址会返回它，耗时≈timeout
            state = "filtered"
        elif code in (101, 51, 10051):
            state = "unreachable"
        else:
            state = f"error({code})"
    except socket.timeout:
        state = "filtered"
    finally:
        sock.close()
    return state, round((time.perf_counter() - started) * 1000, 2)


def measure(host: str, port: int, timeout: float, repeats: int = 5) -> dict:
    rows = [timed_connect(host, port, timeout) for _ in range(repeats)]
    states = [r[0] for r in rows]
    times = [r[1] for r in rows]
    return {
        "host": host, "port": port, "timeout": timeout,
        "state": max(set(states), key=states.count),
        "median_ms": round(statistics.median(times), 2),
        "min_ms": min(times), "max_ms": max(times), "repeats": repeats,
    }


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


def self_test() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    closed_port = probe.getsockname()[1]
    probe.close()
    try:
        state, _ = timed_connect("127.0.0.1", port, 0.5)
        assert state == "open", state
        state, _ = timed_connect("127.0.0.1", closed_port, 0.5)
        assert state == "closed", state
        print("✅ self-test passed: open/closed 判定正确")
        return 0
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.self_test:
        return self_test()

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    open_port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    closed_port = probe.getsockname()[1]
    probe.close()

    rows = []
    try:
        rows.append(measure("127.0.0.1", open_port, 0.5, args.repeats))
        rows.append(measure("127.0.0.1", closed_port, 0.5, args.repeats))
        for timeout in (0.2, 1.0):
            rows.append(measure("198.51.100.1", 81, timeout, args.repeats))
    finally:
        server.shutdown()
        server.server_close()

    print(f"{'目标':<24}{'timeout':>9}{'状态':>12}{'中位数ms':>10}{'范围ms':>16}")
    for r in rows:
        target = f"{r['host']}:{r['port']}"
        print(f"{target:<24}{r['timeout']:>9}{r['state']:>12}{r['median_ms']:>10}"
              f"{r['min_ms']:>8}~{r['max_ms']:<7}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

