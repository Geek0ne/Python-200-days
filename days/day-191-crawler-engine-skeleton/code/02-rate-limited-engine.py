#!/usr/bin/env python3
"""Day 191 · 进阶：令牌桶限速 + 并发抓取引擎 + 实测吞吐

为什么不用 time.sleep(1/rate)：
  并发 8 个 worker 各自 sleep，等于 8 路并行限速，总速率是 8×rate。
  限速必须是**全局共享的一个桶**，所有 worker 从同一个桶取令牌。

本脚本给出一个可复用的最小引擎：
  TokenBucket  —— 令牌桶（支持注入时钟，便于离线自检）
  CrawlEngine  —— 线程池 + frontier + 桶 + 每请求指标
  p50/p95      —— 自己算分位，不引入 numpy

用法：
  python3 02-rate-limited-engine.py --self-test
  python3 02-rate-limited-engine.py --url http://127.0.0.1:8099 --pages 120 --rate 20 --workers 8
"""
from __future__ import annotations

import argparse
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


class TokenBucket:
    """经典令牌桶：capacity 决定突发上限，rate 决定长期平均速率。

    - 桶满则丢弃新令牌（不允许攒出无限突发）
    - 取令牌时先按时间差补桶，再判断；不够就睡到下一个令牌可用
    - 全程持锁：桶是全局共享状态，锁的粒度就是“一次取令牌”
    """

    def __init__(self, rate: float, capacity: float | None = None, *, clock=time.monotonic,
                 sleeper=time.sleep) -> None:
        if rate <= 0:
            raise ValueError("rate 必须 > 0")
        self.rate = float(rate)
        # 关键：默认容量 1，即“严格均匀放行”。若把 capacity 设成 rate，
        # 一开跑就能瞬间打出 rate 个请求，短任务的实际速率会翻倍（Day 191 实测过）。
        self.capacity = float(capacity if capacity is not None else 1.0)
        self.tokens = self.capacity
        self.clock = clock
        self.sleeper = sleeper
        self.last = clock()
        self._lock = threading.Lock()
        self.waited = 0.0

    def _refill(self) -> None:
        now = self.clock()
        delta = now - self.last
        if delta > 0:
            self.tokens = min(self.capacity, self.tokens + delta * self.rate)
            self.last = now

    def acquire(self) -> float:
        """阻塞直到拿到 1 个令牌，返回实际等待秒数。"""
        with self._lock:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return 0.0
            need = (1.0 - self.tokens) / self.rate
            # 预扣：先把令牌记成负数，避免释放锁后一群线程同时醒来抢同一个令牌
            self.tokens -= 1.0
            self.waited += need
        self.sleeper(need)
        return need


@dataclass
class Stats:
    ok: int = 0
    http_err: int = 0
    net_err: int = 0
    latencies: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, ok: bool, kind: str, latency: float) -> None:
        with self._lock:
            if ok:
                self.ok += 1
            elif kind == "http":
                self.http_err += 1
            else:
                self.net_err += 1
            self.latencies.append(latency)

    def pct(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        xs = sorted(self.latencies)
        k = max(0, min(len(xs) - 1, int(round((p / 100) * (len(xs) - 1)))))
        return xs[k] * 1000


class CrawlEngine:
    def __init__(self, rate: float, workers: int = 8, timeout: float = 5.0,
                 bucket: TokenBucket | None = None) -> None:
        self.bucket = bucket or TokenBucket(rate)
        self.workers = workers
        self.timeout = timeout
        self.stats = Stats()

    def _one(self, url: str) -> tuple[str, str]:
        self.bucket.acquire()
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as r:
                body = r.read()
                dt = time.perf_counter() - t0
                self.stats.record(True, "", dt)
                return url, body.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            self.stats.record(False, "http", time.perf_counter() - t0)
            return url, f"HTTP {e.code}"
        except Exception as e:
            self.stats.record(False, "net", time.perf_counter() - t0)
            return url, e.__class__.__name__

    def crawl(self, urls: list[str]) -> dict:
        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            list(ex.map(self._one, urls))
        wall = time.perf_counter() - t0
        return {
            "pages": len(urls),
            "wall_s": round(wall, 3),
            "req_per_s": round(len(urls) / wall, 2) if wall else 0.0,
            "ok": self.stats.ok,
            "http_err": self.stats.http_err,
            "net_err": self.stats.net_err,
            "p50_ms": round(self.stats.pct(50), 1),
            "p95_ms": round(self.stats.pct(95), 1),
            "bucket_wait_s": round(self.bucket.waited, 3),
        }


def self_test() -> int:
    # 假时钟：不真的睡，验证桶的数学是否精确
    cls = type("FakeClock", (), {})
    c = cls()
    c.t = 0.0
    c.slept = 0.0

    def clock() -> float:
        return c.t

    def sleeper(sec: float) -> None:
        c.slept += sec
        c.t += sec

    b = TokenBucket(rate=10, capacity=5, clock=clock, sleeper=sleeper)
    # 容量 5 是“突发额度”，用于验证桶满封顶；默认容量 1 是严格限速。
    got = [b.acquire() for _ in range(5)]
    ok1 = got == [0.0] * 5
    wait = b.acquire()
    ok2 = abs(wait - 0.1) < 1e-9
    waits = [b.acquire() for _ in range(9)]
    ok3 = all(abs(w - 0.1) < 1e-9 for w in waits)
    # 静置 10 秒只补到 capacity=5，不能补成 100
    c.t += 10
    ok4 = (b._refill() or b.tokens) <= 5.000001
    print(f"  {'PASS' if ok1 else 'FAIL'}  突发 5 个令牌不等待")
    print(f"  {'PASS' if ok2 else 'FAIL'}  第 6 个令牌等 0.1s，实测 {wait:.6f}s")
    print(f"  {'PASS' if ok3 else 'FAIL'}  后续 9 个令牌每个等 0.1s")
    print(f"  {'PASS' if ok4 else 'FAIL'}  桶容量封顶（静置 10s 后 tokens={b.tokens:.3f}）")
    total = 4
    passed = sum([ok1, ok2, ok3, ok4])
    print(f"\nself-test: {passed}/{total} passed")
    return 0 if passed == total else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8099")
    ap.add_argument("--pages", type=int, default=120)
    ap.add_argument("--rate", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不发请求")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    urls = [f"{a.url.rstrip('/')}/page/{i}" for i in range(1, a.pages + 1)]
    plan = {"pages": len(urls), "rate": a.rate, "workers": a.workers,
            "expected_s": round(len(urls) / a.rate, 2), "first": urls[0]}
    if a.dry_run:
        import json
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    print(f"计划: {plan}")
    eng = CrawlEngine(rate=a.rate, workers=a.workers)
    res = eng.crawl(urls)
    print("结果:", res)
    ideal = len(urls) / a.rate
    print(f"目标速率 {a.rate}/s，理论耗时 {ideal:.2f}s，实际 {res['wall_s']}s，"
          f"偏差 {abs(res['wall_s'] - ideal) / ideal * 100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
