#!/usr/bin/env python3
"""
03-production-proxy-pool.py — 生产级代理池：评分、熔断、冷却、粘滞会话

在 01 的基础上加四件事，每一件都对应一个真实故障：
    1. 评分（success_rate + EWMA 延迟）—— 慢代理不该和快代理平分流量
    2. 熔断（连续失败 N 次进冷却）      —— 坏代理不该被反复重试
    3. 429/403 冷却（尊重 Retry-After） —— 被封的出口要休息，不是换一个继续打
    4. 粘滞会话（同域固定出口）         —— 同一个会话换 IP，等于告诉对方"我是爬虫"

运行：
    python3 03-production-proxy-pool.py             # 三组对照实验（真实端口）
    python3 03-production-proxy-pool.py --self-test # 断言版
    python3 03-production-proxy-pool.py --json      # 机器可读指标

依赖：仅标准库；靶站/代理由 00-proxy-lab.py 在 127.0.0.1 起。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent


def load_lab():
    path = HERE / "00-proxy-lab.py"
    spec = importlib.util.spec_from_file_location("proxy_lab", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lab = load_lab()
fetch = lab.fetch


# ────────────────────────────── 出口状态 ──────────────────────────────

@dataclass
class ProxyState:
    name: str
    url: str
    # 观测值（不是配置值）
    requests: int = 0
    successes: int = 0
    failures: int = 0
    banned_429: int = 0
    consecutive_failures: int = 0
    ewma_latency: float = 0.0          # 秒；0 表示还没有样本
    cooldown_until: float = 0.0
    cooldown_reason: str = ""
    cooldown_count: int = 0
    last_used: float = 0.0

    def success_rate(self) -> float:
        # Laplace 平滑：0 次请求时给 0.5，避免"没试过 = 最好"
        return (self.successes + 1) / (self.requests + 2)

    def score(self) -> float:
        latency = self.ewma_latency if self.ewma_latency > 0 else 0.5
        return (self.success_rate() ** 2) / (1.0 + latency)

    def cooling(self, now: Optional[float] = None) -> bool:
        return self.cooldown_until > (now if now is not None else time.monotonic())

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "requests": self.requests,
            "successes": self.successes,
            "failures": self.failures,
            "banned_429": self.banned_429,
            "success_rate": round(self.success_rate(), 3),
            "ewma_latency_ms": round(self.ewma_latency * 1000, 1),
            "score": round(self.score(), 3),
            "cooldown_count": self.cooldown_count,
            "cooling_now": self.cooling(),
            "cooldown_reason": self.cooldown_reason,
        }


class TokenBucket:
    def __init__(self, rate: float, capacity: float = 1.0):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated = time.monotonic()

    def _refill(self):
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now

    def ready_in(self) -> float:
        self._refill()
        return 0.0 if self.tokens >= 1 else (1 - self.tokens) / self.rate

    def acquire(self):
        self._refill()
        if self.tokens < 1:
            time.sleep((1 - self.tokens) / self.rate)
            self._refill()
        self.tokens -= 1


# ────────────────────────────── 池 ──────────────────────────────

class ProductionProxyPool:
    """按分数选出口 + 失败熔断 + 429 冷却 + 按域粘滞。"""

    def __init__(self, urls: Dict[str, str], check_url: str,
                 rate_per_exit: float = 0.9, failure_threshold: int = 3,
                 base_cooldown: float = 3.0, max_cooldown: float = 15.0):
        self.states: Dict[str, ProxyState] = {
            name: ProxyState(name=name, url=url) for name, url in urls.items()
        }
        self.check_url = check_url
        self.rate_per_exit = rate_per_exit
        self.failure_threshold = failure_threshold
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown
        self.buckets: Dict[str, TokenBucket] = {
            name: TokenBucket(rate_per_exit) for name in urls
        }
        self.domain_pin: Dict[str, str] = {}
        self.latencies: List[float] = []
        self.events: List[dict] = []

    # ── 选择 ──
    def _eligible(self, now: float) -> List[ProxyState]:
        return [s for s in self.states.values() if not s.cooling(now)]

    def acquire(self, domain: str = "", sticky: bool = False) -> Optional[ProxyState]:
        now = time.monotonic()
        eligible = self._eligible(now)
        if not eligible:
            # 全在冷却：等到最早恢复的那个，而不是硬打
            wait = min(s.cooldown_until for s in self.states.values()) - now
            time.sleep(max(0.0, min(wait, 5.0)))
            eligible = self._eligible(time.monotonic())
            if not eligible:
                return None

        pinned = None
        if sticky and domain and domain in self.domain_pin:
            candidate = self.states[self.domain_pin[domain]]
            if not candidate.cooling():
                pinned = candidate

        if pinned is not None:
            # 粘滞：同域必须复用同一出口，否则 cookie/风控全部对不上
            chosen = pinned
        else:
            # 冷启动必须先探一次：纯 argmax 会让第一个成功的出口永久吃满流量，
            # 其余出口永远 0 样本，坏代理也永远发现不了（实测 p2/p3 req=0）。
            untried = [s for s in eligible if s.requests == 0]
            if untried:
                chosen = min(untried, key=lambda s: s.last_used)
            else:
                # 分数优先；同分时选最久没用的（自然分散）
                chosen = max(eligible, key=lambda s: (s.score(), -s.last_used))
        if sticky and domain:
            self.domain_pin[domain] = chosen.name
        self.buckets[chosen.name].acquire()
        chosen.last_used = time.monotonic()
        return chosen

    # ── 回报 ──
    def report(self, proxy: ProxyState, ok: bool, latency: float = 0.0,
               status: int = 0, retry_after: Optional[float] = None):
        proxy.requests += 1
        if ok:
            proxy.successes += 1
            proxy.consecutive_failures = 0
            alpha = 0.3
            proxy.ewma_latency = (latency if proxy.ewma_latency == 0
                                  else alpha * latency + (1 - alpha) * proxy.ewma_latency)
        else:
            proxy.failures += 1
            proxy.consecutive_failures += 1
            if status == 429:
                proxy.banned_429 += 1
                # 尊重 Retry-After；没有就退避
                cooldown = retry_after if retry_after else self.base_cooldown
                self._cool(proxy, cooldown, "429")
            elif status == 403:
                self._cool(proxy, self.base_cooldown * 2, "403")
            elif proxy.consecutive_failures >= self.failure_threshold:
                self._cool(proxy, self.base_cooldown, f"{status or 'error'} x{proxy.consecutive_failures}")

    def _cool(self, proxy: ProxyState, seconds: float, reason: str):
        proxy.cooldown_count += 1
        exponent = min(proxy.cooldown_count - 1, 4)
        seconds = min(self.max_cooldown, seconds * (2 ** exponent) / 2)
        proxy.cooldown_until = time.monotonic() + max(1.0, seconds)
        proxy.cooldown_reason = reason
        self.events.append({"t": round(time.monotonic(), 2), "proxy": proxy.name,
                            "event": "cooldown", "reason": reason,
                            "seconds": round(seconds, 2)})

    # ── 请求 ──
    def get(self, path: str, domain: str = "", sticky: bool = False) -> dict:
        proxy = self.acquire(domain=domain, sticky=sticky)
        if proxy is None:
            return {"ok": False, "status": 0, "exit": None, "error": "no eligible proxy"}
        url = self.check_url.rsplit("/", 1)[0] + path
        try:
            code, body, elapsed = fetch(url, proxy=proxy.url, timeout=3.0)
            retry_after = None
            if code == 429:
                retry_after = 1.0
            ok = code == 200
            self.report(proxy, ok, elapsed, code, retry_after)
            self.latencies.append(elapsed)
            return {"ok": ok, "status": code, "exit": proxy.name, "body": body}
        except Exception as exc:                       # noqa: BLE001
            self.report(proxy, False, 0.0, 0)
            return {"ok": False, "status": 0, "exit": proxy.name,
                    "error": f"{type(exc).__name__}: {exc}"}

    # ── 指标 ──
    def metrics(self) -> dict:
        lat = sorted(self.latencies)
        def pct(p: float) -> float:
            if not lat:
                return 0.0
            idx = min(len(lat) - 1, int(round(p * (len(lat) - 1))))
            return round(lat[idx] * 1000, 1)

        return {
            "requests": sum(s.requests for s in self.states.values()),
            "successes": sum(s.successes for s in self.states.values()),
            "failures": sum(s.failures for s in self.states.values()),
            "banned_429": sum(s.banned_429 for s in self.states.values()),
            "p50_ms": pct(0.50),
            "p95_ms": pct(0.95),
            "per_exit": [s.as_dict() for s in self.states.values()],
            "cooldowns": len(self.events),
        }


# ────────────────────────────── 实验 ──────────────────────────────

N = 36


def run_scoring(use_smart: bool) -> dict:
    """p2 慢（120ms）、p3 坏（502）；比较盲轮询与评分选择。"""
    with lab.Lab(ban_limit=100) as env:
        env.set_config("p2", delay=0.12)
        env.set_config("p3", fail=True)
        urls = {n: env.proxy_url(n) for n in ("p1", "p2", "p3")}
        if use_smart:
            # 502 基本等于"这个出口坏了"，一次就熔断
            pool = ProductionProxyPool(urls, env.origin.url + "/health",
                                       rate_per_exit=3.0, failure_threshold=1)
            results = [pool.get(f"/item/{i}") for i in range(N)]
        else:
            # 盲轮询：不看结果，平均分配，也不冷却
            order = ["p1", "p2", "p3"]
            results = []
            for i in range(N):
                name = order[i % 3]
                code, body, elapsed = fetch(env.origin.url + f"/item/{i}", proxy=urls[name])
                results.append({"ok": code == 200, "status": code, "exit": name})
            pool = None
    ok = sum(1 for r in results if r["ok"])
    return {
        "ok": ok,
        "fail": N - ok,
        "by_exit": {n: sum(1 for r in results if r["exit"] == n) for n in ("p1", "p2", "p3")},
        "metrics": pool.metrics() if pool else None,
    }


def run_sticky() -> dict:
    """两个域各 6 次请求：粘滞应各固定 1 个出口，盲轮询会漂移。"""
    with lab.Lab(ban_limit=100) as env:
        urls = {n: env.proxy_url(n) for n in ("p1", "p2", "p3")}
        smart = ProductionProxyPool(urls, env.origin.url + "/health", rate_per_exit=5.0)
        sticky_exits: Dict[str, set] = {"shop": set(), "news": set()}
        for i in range(6):
            for domain in ("shop", "news"):
                got = smart.get(f"/item/{domain}-{i}", domain=domain, sticky=True)
                sticky_exits[domain].add(got["exit"])

        blind_exits: Dict[str, set] = {"shop": set(), "news": set()}
        order = ["p1", "p2", "p3"]
        for i in range(6):
            for j, domain in enumerate(("shop", "news")):
                name = order[(i * 2 + j) % 3]
                fetch(env.origin.url + f"/item/b-{domain}-{i}", proxy=urls[name])
                blind_exits[domain].add(name)
    return {
        "sticky": {k: sorted(v) for k, v in sticky_exits.items()},
        "blind": {k: sorted(v) for k, v in blind_exits.items()},
    }


def run_cooldown() -> dict:
    """先用 5 个快速请求把 p1 打成 429，再看池子是否让它休息并切走。"""
    with lab.Lab(ban_limit=6, ban_window=3.0) as env:
        urls = {n: env.proxy_url(n) for n in ("p1", "p2", "p3")}
        pool = ProductionProxyPool(urls, env.origin.url + "/health",
                                   rate_per_exit=20.0, base_cooldown=6.0)
        # 预热：让 p1 拿到最高分（快）
        pool.buckets["p1"].tokens = 0
        for _ in range(8):
            code, _, _ = fetch(env.origin.url + "/limited/burst", proxy=urls["p1"])
            pool.report(pool.states["p1"], code == 200, 0.001, code, 1.0)
        banned_state = pool.states["p1"].as_dict()

        # 之后 6 个请求：不应再落到冷却中的 p1
        after = []
        for i in range(6):
            got = pool.get(f"/limited/{i}")
            after.append((got["exit"], got["status"]))
        used_p1 = sum(1 for name, _ in after if name == "p1")

        # 等冷却结束，p1 应能重新接活
        time.sleep(3.2)
        recovered = not pool.states["p1"].cooling()
        got = pool.get("/item/recover")
    return {
        "banned": banned_state,
        "after": after,
        "used_p1_during_cooldown": used_p1,
        "recovered": recovered,
        "recover_exit": got["exit"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    print("=" * 70)
    print("实验 A：盲轮询 vs 评分选择（p2 慢 120ms，p3 永远 502）")
    print("=" * 70)
    blind = run_scoring(use_smart=False)
    smart = run_scoring(use_smart=True)
    print(f"盲轮询 : 成功 {blind['ok']}/{N}  失败 {blind['fail']}  "
          f"分布 {blind['by_exit']}")
    print(f"评分池 : 成功 {smart['ok']}/{N}  失败 {smart['fail']}  "
          f"分布 {smart['by_exit']}")
    m = smart["metrics"]
    print(f"评分池指标: p50={m['p50_ms']}ms p95={m['p95_ms']}ms "
          f"冷却次数={m['cooldowns']}")
    for row in m["per_exit"]:
        print(f"   {row['name']}: req={row['requests']} ok={row['successes']} "
              f"fail={row['failures']} ewma={row['ewma_latency_ms']}ms "
              f"score={row['score']} cooldown={row['cooldown_count']}")

    print()
    print("=" * 70)
    print("实验 B：粘滞会话（同一域必须固定出口）")
    print("=" * 70)
    sticky = run_sticky()
    print(f"粘滞   : {sticky['sticky']}")
    print(f"盲轮询 : {sticky['blind']}")

    print()
    print("=" * 70)
    print("实验 C：429 冷却与恢复")
    print("=" * 70)
    cool = run_cooldown()
    print(f"p1 被打爆后: 429={cool['banned']['banned_429']} "
          f"冷却次数={cool['banned']['cooldown_count']} 原因={cool['banned']['cooldown_reason']}")
    print(f"冷却期间 6 个请求: {cool['after']}")
    print(f"冷却期间落到 p1 的次数: {cool['used_p1_during_cooldown']}")
    print(f"冷却结束后恢复: {cool['recovered']}，下一个请求出口={cool['recover_exit']}")

    snapshot = {"blind": blind, "smart": smart, "sticky": sticky, "cooldown": cool}
    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))

    if not args.self_test:
        return 0

    checks: List[Tuple[str, bool, str]] = [
        ("盲轮询确实会打到坏代理", blind["fail"] > 0, str(blind["fail"])),
        ("评分池成功率 >= 90%", smart["ok"] >= N * 0.9, f"{smart['ok']}/{N}"),
        ("评分池比盲轮询成功更多", smart["ok"] > blind["ok"], f"{smart['ok']} vs {blind['ok']}"),
        ("坏代理进入冷却", any(r["cooldown_count"] > 0 for r in m["per_exit"]), ""),
        ("粘滞域只用一个出口", all(len(v) == 1 for v in sticky["sticky"].values()),
         str(sticky["sticky"])),
        ("盲轮询同域用多个出口", any(len(v) > 1 for v in sticky["blind"].values()),
         str(sticky["blind"])),
        ("429 后进入冷却", cool["banned"]["cooldown_count"] > 0,
         str(cool["banned"]["cooldown_count"])),
        ("冷却期间不再使用 p1", cool["used_p1_during_cooldown"] == 0,
         str(cool["used_p1_during_cooldown"])),
        ("冷却结束能恢复", cool["recovered"], str(cool["recover_exit"])),
    ]
    print("\n── 断言 ──")
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    failed = sum(1 for _, ok, _ in checks if not ok)
    print(f"{len(checks) - failed}/{len(checks)} 项通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
