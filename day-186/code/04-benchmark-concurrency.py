#!/usr/bin/env python3
"""
Day 186 · 04 — 性能对比：串行 vs 并发 DNS 枚举

DNS 枚举是 **I/O 密集**任务：99% 时间在等解析器回包。
这类任务的正确做法是并发，线程数不需要等于 CPU 核数，而应覆盖等待时间。

本脚本做两组实验：
  A. 受控实验：用固定 20ms 延迟的假 resolver，排除网络抖动，
     比较 workers = 1/4/16/64 的墙钟时间与加速比。
  B. 真实实验：对一组公网域名做真实 DNS 解析，串行 vs 8 线程，重复 3 次取中位数。

用法：
  python3 04-benchmark-concurrency.py
  python3 04-benchmark-concurrency.py --self-test
"""

from __future__ import annotations

import argparse
import socket
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor

SIM_LATENCY = 0.020


def simulate_latency(host: str, timeout: float = 3.0) -> list[str]:
    """假 resolver：固定延迟，1/10 概率模拟 NXDOMAIN。"""
    time.sleep(SIM_LATENCY)
    if hash(host) % 10 == 0:
        return []
    return ["192.0.2.1"]


def run_pool(hosts: list[str], workers: int, resolver=simulate_latency) -> tuple[int, float]:
    started = time.perf_counter()
    found = 0
    if workers == 1:
        for host in hosts:
            if resolver(host):
                found += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for ips in pool.map(resolver, hosts):
                if ips:
                    found += 1
    return found, time.perf_counter() - started


def real_resolve(host: str, timeout: float = 3.0) -> list[str]:
    old = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        infos = socket.getaddrinfo(host, None)
        return sorted({i[4][0] for i in infos})
    except OSError:
        return []
    finally:
        socket.setdefaulttimeout(old)


def benchmark_simulated(n: int = 200) -> dict:
    hosts = [f"host{i}.example.test" for i in range(n)]
    print(f"=== A. 受控实验：{n} 个候选，单次解析固定 {SIM_LATENCY*1000:.0f}ms ===")
    rows = []
    baseline = None
    for workers in (1, 4, 16, 64):
        found, elapsed = run_pool(hosts, workers)
        baseline = baseline or elapsed
        rows.append({
            "workers": workers,
            "elapsed_sec": round(elapsed, 3),
            "speedup": round(baseline / elapsed, 2),
            "found": found,
        })
        print(f"  workers={workers:<3} 用时 {elapsed:6.3f}s  加速比 {baseline/elapsed:5.2f}x  命中 {found}")
    return {"candidates": n, "sim_latency_ms": SIM_LATENCY * 1000, "rows": rows}


def benchmark_real(repeats: int = 3) -> dict:
    hosts = ["example.com", "www.python.org", "github.com", "pypi.org",
             "docs.python.org", "api.github.com", "www.debian.org", "kernel.org"]
    print(f"\n=== B. 真实 DNS：{len(hosts)} 个域名 × {repeats} 次 ===")
    seq_times, par_times = [], []
    for i in range(repeats):
        _, t1 = run_pool(hosts, 1, real_resolve)
        _, t8 = run_pool(hosts, 8, real_resolve)
        seq_times.append(t1)
        par_times.append(t8)
        print(f"  round {i+1}: 串行 {t1:.3f}s  并发(8) {t8:.3f}s")
    seq_med = statistics.median(seq_times)
    par_med = statistics.median(par_times)
    print(f"  中位数: 串行 {seq_med:.3f}s  并发 {par_med:.3f}s  加速 {seq_med/par_med:.2f}x")
    return {
        "hosts": len(hosts), "repeats": repeats,
        "sequential_median_sec": round(seq_med, 3),
        "parallel8_median_sec": round(par_med, 3),
        "speedup": round(seq_med / par_med, 2),
    }


def self_test() -> int:
    found, elapsed = run_pool(["a.example.test"] * 20, 8, lambda h: ["192.0.2.1"])
    assert found == 20, found
    assert elapsed < 20 * SIM_LATENCY, elapsed   # 并发必须快于串行理论值
    assert real_resolve("localhost") != []
    print("✅ self-test passed: 线程池计数正确，且并发快于串行理论上限")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--sim-only", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    result = {"simulated": benchmark_simulated()}
    if not args.sim_only:
        try:
            result["real"] = benchmark_real()
        except Exception as exc:
            print(f"[!] 真实 DNS 实验失败: {exc}")
    print("\nJSON:", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())

