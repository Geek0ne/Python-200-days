#!/usr/bin/env python3
"""
Day 187 · 01 — 基础用法：TCP connect 端口扫描（纯标准库）

原理：
  对目标端口发起一次完整的 TCP 三次握手。
    - 握手成功        → open
    - RST 立刻返回    → closed（端口没人监听，但主机可达）
    - 一直无响应      → filtered（防火墙 DROP / 主机不可达）
    - 其他错误        → error

为什么用 connect 扫描（而不是 SYN 半开）：
  · 不需要 root、不需要 raw socket，任何用户都能跑；
  · 会产生完整连接，目标日志里会留下记录（这是特性也是缺点）；
  · 对教学和授权测试足够，SYN 扫描属于更激进的工具（nmap -sS）范畴。

本脚本只应扫描你有权测试的主机。默认目标是 127.0.0.1。

用法：
  python3 01-port-scan-basic.py --host 127.0.0.1 --ports 22,80,8000-8010
  python3 01-port-scan-basic.py --self-test
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_ports(spec: str) -> list[int]:
    """把 "22,80,8000-8003" 解析成有序去重的端口列表。"""
    ports: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_s, end_s = chunk.split("-", 1)
            start, end = int(start_s), int(end_s)
            if start > end:
                start, end = end, start
            ports.update(range(start, end + 1))
        else:
            ports.add(int(chunk))
    bad = [p for p in ports if not 1 <= p <= 65535]
    if bad:
        raise ValueError(f"端口越界: {bad[:5]}")
    return sorted(ports)


def scan_port(host: str, port: int, timeout: float = 0.5) -> dict:
    """扫描单个 TCP 端口，返回 {port, state, latency_ms, error}。"""
    started = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    state = "error"
    error = ""
    try:
        code = sock.connect_ex((host, port))
        if code == 0:
            state = "open"
        elif code in (111, 61, 10061):      # ECONNREFUSED (Linux/macOS/Windows)
            state = "closed"
        elif code in (11, 115, 110, 60, 10060):  # EAGAIN/EINPROGRESS/ETIMEDOUT
            # 真实踩坑：对黑洞地址 connect_ex 会返回 11(EAGAIN)，
            # 耗时正好等于 timeout；把它当成 error 会漏报"被过滤"。
            state = "filtered"
        elif code in (101, 51, 10051):      # ENETUNREACH
            state = "unreachable"
        else:
            state = "error"
            error = f"errno={code}"
    except socket.timeout:
        state = "filtered"
    except OSError as exc:
        state = "error"
        error = str(exc)
    finally:
        sock.close()
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return {"port": port, "state": state, "latency_ms": latency_ms, "error": error}


def scan_host(host: str, ports: list[int], workers: int = 100,
              timeout: float = 0.5, progress=None) -> list[dict]:
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(scan_port, host, p, timeout): p for p in ports}
        for fut in as_completed(futures):
            item = fut.result()
            results.append(item)
            if progress and item["state"] == "open":
                progress(item)
    return sorted(results, key=lambda r: r["port"])


def self_test() -> int:
    """离线自测：真实绑定几个本地端口，验证 open/closed 判定。"""
    listeners = []
    try:
        for _ in range(3):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            listeners.append(s)
        open_ports = [s.getsockname()[1] for s in listeners]

        # 拿一个刚释放的端口，确保它是 closed
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]
        probe.close()

        results = scan_host("127.0.0.1", open_ports + [closed_port], workers=4, timeout=0.5)
        by_port = {r["port"]: r for r in results}

        for port in open_ports:
            assert by_port[port]["state"] == "open", by_port[port]
        assert by_port[closed_port]["state"] == "closed", by_port[closed_port]
        assert parse_ports("80, 79-81,80") == [79, 80, 81]

        print("✅ self-test passed: 3 个监听端口判定 open，1 个释放端口判定 closed")
        print(f"   监听端口: {open_ports} / 已关闭端口: {closed_port}")
        return 0
    finally:
        for s in listeners:
            s.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="TCP connect 端口扫描")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ports", default="22,80,443,8000-8010")
    parser.add_argument("--workers", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=0.5)
    parser.add_argument("--open-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    try:
        ports = parse_ports(args.ports)
    except ValueError as exc:
        parser.error(str(exc))

    print(f"[*] 扫描 {args.host} 的 {len(ports)} 个端口，超时 {args.timeout}s，并发 {args.workers}")
    started = time.perf_counter()
    results = scan_host(args.host, ports, args.workers, args.timeout,
                        progress=lambda r: print(f"  [+] {r['port']}/tcp open ({r['latency_ms']}ms)"))
    elapsed = time.perf_counter() - started

    if not args.open_only:
        for r in results:
            if r["state"] != "open":
                print(f"  [-] {r['port']}/tcp {r['state']} ({r['latency_ms']}ms)")

    counts: dict[str, int] = {}
    for r in results:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    print(f"[*] 用时 {elapsed:.3f}s，结果: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

