#!/usr/bin/env python3
"""
02-pitfall-connect-and-env.py — 代理池的三个真实翻车现场

翻车 1：代理能做 HTTP，却不支持 CONNECT —— HTTPS 全部失败，而健康检查（用 http）
        是绿的。你会以为"代理没问题，是目标站封我"。
翻车 2：urllib 默认读环境变量代理 —— 你代码里明明传了 proxy={}，请求还是被
        http_proxy 劫持到一台死代理上。
翻车 3：轮换 = 绕过自己的限速 —— 每个出口都按全局速率打，目标站按出口计数，
        于是 3 个出口一起进冷却。

运行：
    python3 02-pitfall-connect-and-env.py              # 全部实验（HTTPS 需要外网）
    python3 02-pitfall-connect-and-env.py --offline    # 跳过外网实验
    python3 02-pitfall-connect-and-env.py --self-test  # 断言版（离线部分）

所有输出都来自真实 socket / 真实 HTTP，不 mock。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Tuple

HERE = Path(__file__).resolve().parent


def load_lab():
    path = HERE / "00-proxy-lab.py"
    spec = importlib.util.spec_from_file_location("proxy_lab", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module          # dataclass 需要模块已注册
    spec.loader.exec_module(module)
    return module


lab = load_lab()
fetch = lab.fetch


def fetch_status(url: str, proxy: str, timeout: float = 5.0):
    """只看状态码和响应首字节——example.com 返回 HTML，不能用 lab.fetch 的 JSON 解析。"""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy, "https": proxy})
    )
    with opener.open(url, timeout=timeout) as resp:
        return resp.status, resp.read(40)


# ────────────────────────── 翻车 1：CONNECT ──────────────────────────

def experiment_connect(offline: bool) -> dict:
    print("=" * 68)
    print("翻车 1：健康检查用 HTTP，业务走 HTTPS —— 代理只支持一半")
    print("=" * 68)
    result = {"http_ok": False, "https_error": "", "https_via_tunnel": ""}

    with lab.Lab() as env:
        # 把 p1 配成"不支持 CONNECT"的代理，模拟市面上大量廉价 HTTP 代理
        env.set_config("p1", support_connect=False)

        # 1a) HTTP 健康检查：通过
        code, body, _ = fetch(env.origin.url + "/health", proxy=env.proxy_url("p1"))
        result["http_ok"] = code == 200
        print(f"[1a] HTTP 健康检查      -> {code} {body}   ← 绿灯，骗过你")

        # 1b) HTTPS 业务：URLError: Tunnel connection failed: 501
        if offline:
            result["https_error"] = "skipped(offline)"
            print("[1b] HTTPS 经同一代理    -> 跳过（--offline）")
        else:
            try:
                code, _ = fetch_status("https://example.com/", env.proxy_url("p1"), timeout=5)
                result["https_error"] = f"unexpected {code}"
                print(f"[1b] HTTPS 经同一代理    -> 意外成功 {code}")
            except Exception as exc:                   # noqa: BLE001
                result["https_error"] = f"{type(exc).__name__}: {exc}"
                print(f"[1b] HTTPS 经同一代理    -> {result['https_error']}")

        # 1c) 同一个代理，打开 CONNECT 后重试（模拟换成支持隧道的供应商）
        if not offline:
            env.set_config("p1", support_connect=True)
            try:
                code, head = fetch_status("https://example.com/", env.proxy_url("p1"), timeout=8)
                result["https_via_tunnel"] = f"HTTP {code}"
                print(f"[1c] 打开 CONNECT 后重试 -> HTTP {code} 首字节={head[:15]!r}")
            except Exception as exc:                   # noqa: BLE001
                result["https_via_tunnel"] = f"{type(exc).__name__}: {exc}"
                print(f"[1c] 打开 CONNECT 后重试 -> {result['https_via_tunnel']}")

        print("\n结论：健康检查必须覆盖业务真正用的协议。")
        print("     只探 http:// 的池子，会在 HTTPS 站点上全员判活、全员失败。\n")
    return result


# ────────────────────────── 翻车 2：环境变量 ──────────────────────────

def experiment_env_proxy() -> dict:
    print("=" * 68)
    print("翻车 2：显式传了 proxy={}，请求还是走了环境变量里的死代理")
    print("=" * 68)
    result = {"env_failed": False, "explicit_ok": False, "error": ""}

    # 先占一个端口再关掉，保证它是"确定连不上"的地址
    import socket
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    dead_port = probe.getsockname()[1]
    probe.close()

    saved = {k: os.environ.get(k) for k in ("http_proxy", "HTTP_PROXY",
                                             "https_proxy", "HTTPS_PROXY")}
    try:
        os.environ["http_proxy"] = f"http://127.0.0.1:{dead_port}"
        os.environ["HTTP_PROXY"] = f"http://127.0.0.1:{dead_port}"

        with lab.Lab() as env:
            url = env.origin.url + "/health"

            # 2a) build_opener() 不带参数 = ProxyHandler() = 读环境变量
            try:
                with urllib.request.build_opener().open(url, timeout=2) as resp:
                    result["env_failed"] = False
                    print(f"[2a] 默认 opener          -> {resp.status}（环境代理没生效？）")
            except Exception as exc:                   # noqa: BLE001
                result["env_failed"] = True
                result["error"] = f"{type(exc).__name__}: {exc}"
                print(f"[2a] 默认 opener          -> {result['error']}")

            # 2b) 显式 ProxyHandler({}) 才是"这次真的直连"
            try:
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                with opener.open(url, timeout=2) as resp:
                    body = json.loads(resp.read())
                    result["explicit_ok"] = resp.status == 200 and body["exit"] == "direct"
                    print(f"[2b] ProxyHandler({{}})   -> {resp.status} exit={body['exit']}")
            except Exception as exc:                   # noqa: BLE001
                print(f"[2b] ProxyHandler({{}})   -> {type(exc).__name__}: {exc}")

            print("\n结论：代理池必须显式管理 opener，不能依赖全局默认 opener；")
            print("     生产容器里那个看不见的 http_proxy，能让整池代理'看起来全死'。\n")
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return result


# ────────────────────────── 翻车 3：轮换绕过限速 ──────────────────────────

class TokenBucket:
    """每个出口一个桶：rate 个/秒，允许 capacity 的突发。

    注意：等待必须发生在"扣令牌之前"的同一个临界区里（acquire），
    否则会出现"等完了却不扣"的漏洞——实测速率会从 2.7/s 涨到 3.6/s。
    """

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
        """只看还要等多久，不消耗令牌（用于挑出口）。"""
        self._refill()
        return 0.0 if self.tokens >= 1 else (1 - self.tokens) / self.rate

    def acquire(self):
        """阻塞式取令牌：等够了再扣，扣完才返回。"""
        self._refill()
        if self.tokens < 1:
            time.sleep((1 - self.tokens) / self.rate)
            self._refill()
        self.tokens -= 1


def experiment_rate_limit() -> dict:
    print("=" * 68)
    print("翻车 3：轮换不等于提速 —— 目标站按出口计数")
    print("=" * 68)
    result = {}

    N = 30
    # 先测"照脸打"：3 个出口轮询，每个出口 4 次/3 秒的窗口
    with lab.Lab(ban_limit=4, ban_window=3.0) as env:
        names = ["p1", "p2", "p3"]
        urls = {n: env.proxy_url(n) for n in names}
        codes: List[int] = []
        ok = 0
        for i in range(N):
            name = names[i % 3]
            code, _, _ = fetch(env.origin.url + f"/limited/{i}", proxy=urls[name])
            codes.append(code)
            ok += code == 200
        result["naive_200"] = ok
        result["naive_429"] = codes.count(429)
        print(f"[3a] 裸轮换 30 次        -> 200={ok} 429={codes.count(429)}")
        print(f"     前 15 个状态码: {codes[:15]}")

    # 再测"每出口限速 + 429 冷却"：0.9 req/s per exit，桶容量 2
    with lab.Lab(ban_limit=4, ban_window=3.0) as env:
        names = ["p1", "p2", "p3"]
        urls = {n: env.proxy_url(n) for n in names}
        buckets = {n: TokenBucket(rate=0.9, capacity=1) for n in names}
        cooldown_until = {n: 0.0 for n in names}
        codes = []
        ok = 0
        started = time.monotonic()
        for i in range(N):
            # 选一个不在冷却的出口；全在冷却就等到最近的那个
            now = time.monotonic()
            ready = [n for n in names if cooldown_until[n] <= now]
            if not ready:
                wait = min(cooldown_until.values()) - now
                time.sleep(max(0.0, wait))
                ready = [n for n in names if cooldown_until[n] <= time.monotonic()]
            name = min(ready, key=lambda n: buckets[n].ready_in())  # 取最早可发的
            buckets[name].acquire()
            code, _, _ = fetch(env.origin.url + f"/limited/{i}", proxy=urls[name])
            codes.append(code)
            ok += code == 200
            if code == 429:
                cooldown_until[name] = time.monotonic() + 1.5
    elapsed = time.monotonic() - started
    result["paced_200"] = ok
    result["paced_429"] = codes.count(429)
    result["paced_seconds"] = round(elapsed, 2)
    result["paced_rps"] = round(N / elapsed, 2)
    print(f"[3b] 每出口限速+冷却     -> 200={ok} 429={codes.count(429)} "
          f"用时={elapsed:.2f}s ({N/elapsed:.2f} req/s)")
    print("\n结论：轮换只改变'从哪个 IP 出去'，不改变'目标站允许多快'。")
    print("     正确做法：每出口一个令牌桶 + 429 冷却；总速率 = Σ 出口速率。\n")
    return result


# ────────────────────────────── 入口 ──────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="跳过需要外网的 HTTPS 实验")
    parser.add_argument("--self-test", action="store_true", help="断言版（自动跳过外网）")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    offline = args.offline or args.self_test
    results = {}
    results["connect"] = experiment_connect(offline)
    results["env"] = experiment_env_proxy()
    results["rate"] = experiment_rate_limit()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    if not args.self_test:
        return 0

    checks: List[Tuple[str, bool, str]] = [
        ("HTTP 健康检查通过（陷阱成立的前提）", results["connect"]["http_ok"], ""),
        ("默认 opener 被环境变量劫持", results["env"]["env_failed"], results["env"]["error"]),
        ("显式空 ProxyHandler 能直连", results["env"]["explicit_ok"], ""),
        ("裸轮换会打出 429", results["rate"]["naive_429"] > 0,
         str(results["rate"]["naive_429"])),
        ("每出口限速后 429 归零", results["rate"]["paced_429"] == 0,
         str(results["rate"]["paced_429"])),
        ("限速后仍然跑完全部请求", results["rate"]["paced_200"] == 30,
         str(results["rate"]["paced_200"])),
    ]
    print("── 断言 ──")
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  {detail}")
    failed = sum(1 for _, ok, _ in checks if not ok)
    print(f"{len(checks) - failed}/{len(checks)} 项通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
