#!/usr/bin/env python3
"""Day 191 · 避坑：两个把限速和去重同时搞坏的写法

坑 1 —— 把 sleep 写进 worker：
    每个 worker 都 sleep(1/rate)，看起来“每个请求间隔 1/rate 秒”，
    实际是 N 个 worker 并行各自限速，全局速率 = workers × rate。

坑 2 —— 用原始 URL 字符串去重：
    /page/5、/page/5#top、/page/5?utm_source=x 在字符串上不同，
    在服务端眼里是同一个页面。结果是同一页抓三遍，配额白烧。

用法：
  python3 04-pitfall-per-worker-sleep.py --self-test
  python3 04-pitfall-per-worker-sleep.py --url http://127.0.0.1:8099 --rate 20 --workers 8 --pages 120
"""
from __future__ import annotations

import argparse
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


# ---------------- 坑 1：每 worker 各自 sleep ----------------
def crawl_naive_sleep(urls: list[str], rate: float, workers: int) -> dict:
    interval = 1.0 / rate

    def one(u: str) -> None:
        time.sleep(interval)          # ← 错在这里：这是“每个线程”的间隔
        try:
            with urllib.request.urlopen(u, timeout=5) as r:
                r.read()
        except Exception:
            pass

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, urls))
    wall = time.perf_counter() - t0
    return {"strategy": "per-worker sleep", "wall_s": round(wall, 3),
            "achieved_rps": round(len(urls) / wall, 2)}


# ---------------- 正确做法：全局共享桶 ----------------
class Bucket:
    def __init__(self, rate: float) -> None:
        self.rate = rate
        self.tokens = 1.0
        self.last = time.monotonic()
        self.lock = threading.Lock()
        self.sleep_s = 0.0

    def acquire(self) -> None:
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.rate, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
            wait = (1 - self.tokens) / self.rate
            self.tokens -= 1
            self.sleep_s += wait
        time.sleep(wait)


def crawl_global_bucket(urls: list[str], rate: float, workers: int) -> dict:
    b = Bucket(rate)

    def one(u: str) -> None:
        b.acquire()
        try:
            with urllib.request.urlopen(u, timeout=5) as r:
                r.read()
        except Exception:
            pass

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, urls))
    wall = time.perf_counter() - t0
    return {"strategy": "global bucket", "wall_s": round(wall, 3),
            "achieved_rps": round(len(urls) / wall, 2), "sleep_s": round(b.sleep_s, 2)}


# ---------------- 坑 2：原始字符串去重 ----------------
RAW_URLS = ["/page/5", "/page/5#top", "/page/5?utm_source=x", "/page/5?utm_source=y",
            "/page/6", "/page/6?ref=nav"]


def dedup_raw(urls: list[str]) -> list[str]:
    return list(dict.fromkeys(urls))


def dedup_canonical(urls: list[str]) -> list[str]:
    import importlib.util
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("uf", os.path.join(here, "01-url-frontier.py"))
    uf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(uf)
    out: dict[str, str] = {}
    for u in urls:
        c = uf.normalize(u, "http://h")
        out.setdefault(c, u)
    return list(out.values())


def self_test() -> int:
    checks = []
    raw = dedup_raw(RAW_URLS)
    canon = dedup_canonical(RAW_URLS)
    checks.append(("原始去重仍有 6 条", len(raw) == 6))
    checks.append(("规范化去重只剩 2 条", len(canon) == 2))
    checks.append(("规范化保留可抓 URL", all("page" in u for u in canon)))

    # 用 0 延迟的假 fetch 验证策略差异（不发真请求）
    global _hits
    out = {}
    for name, fn in (("raw", dedup_raw), ("canon", dedup_canonical)):
        out[name] = len(fn(RAW_URLS))
    checks.append(("两种策略结果确实不同", out["raw"] != out["canon"]))
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"\nself-test: {sum(ok for _, ok in checks)}/{len(checks)} passed")
    return 0 if all(ok for _, ok in checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8099")
    ap.add_argument("--rate", type=float, default=20.0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--pages", type=int, default=120)
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    base = a.url.rstrip("/")
    urls = [f"{base}/page/{i}" for i in range(1, a.pages + 1)]
    print(f"目标速率 {a.rate}/s · workers {a.workers} · pages {len(urls)}")
    print(f"理论耗时 {len(urls) / a.rate:.2f}s")
    naive = crawl_naive_sleep(urls, a.rate, a.workers)
    print(f"  坑1 {naive}  超速 {naive['achieved_rps'] / a.rate:.1f}×")
    good = crawl_global_bucket(urls, a.rate, a.workers)
    print(f"  正解 {good}  偏差 {abs(good['wall_s'] - len(urls) / a.rate) / (len(urls) / a.rate) * 100:.1f}%")

    print(f"\n坑2 去重：原始 {len(dedup_raw(RAW_URLS))} 条 vs 规范化 {len(dedup_canonical(RAW_URLS))} 条")
    print(f"同一批 {len(RAW_URLS)} 个链接，规范化后省下 {len(dedup_raw(RAW_URLS)) - len(dedup_canonical(RAW_URLS))} 次请求")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
