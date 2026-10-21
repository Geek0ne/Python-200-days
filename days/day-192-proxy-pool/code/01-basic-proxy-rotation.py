#!/usr/bin/env python3
"""
01-basic-proxy-rotation.py — 代理池最小可用版：健康检查 + 轮换

今天的第一层：先别想"反反爬"，先回答三个问题：
    1. 这个代理现在到底能不能用？（不是端口通，是"真的从它出去了"）
    2. 手上还有几个能用的？（healthy 集合）
    3. 下一个请求该给谁？（轮换策略）

运行：
    python3 01-basic-proxy-rotation.py             # 跑完整演示（会起本地靶站+3 个代理）
    python3 01-basic-proxy-rotation.py --self-test # 离线自证，8 项断言
    python3 01-basic-proxy-rotation.py --json      # 机器可读输出

本例只依赖标准库，靶站和代理都由 00-proxy-lab.py 起在 127.0.0.1。
"""

from __future__ import annotations

import argparse
import importlib.util
import itertools
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent


def load_lab():
    """按文件路径加载 00-proxy-lab.py（文件名带数字，不能直接 import）。"""
    path = HERE / "00-proxy-lab.py"
    spec = importlib.util.spec_from_file_location("proxy_lab", path)
    module = importlib.util.module_from_spec(spec)
    # 必须先注册进 sys.modules 再 exec：dataclass 装饰器在解析注解时
    # 会用 cls.__module__ 反查模块（sys.modules.get(name).__dict__），
    # 没注册时 .get() 返回 None，报 'NoneType' object has no attribute '__dict__'。
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lab_mod = load_lab()
fetch = lab_mod.fetch


# ────────────────────────────── 数据模型 ──────────────────────────────

@dataclass
class Proxy:
    """一个出口。字段都是"观测出来的"，不是配置里抄来的。"""
    url: str
    name: str = ""
    healthy: bool = False
    latency_ms: Optional[float] = None
    successes: int = 0
    failures: int = 0
    last_error: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self.url

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total else 0.0

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "healthy": self.healthy,
            "latency_ms": None if self.latency_ms is None else round(self.latency_ms, 1),
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": round(self.success_rate, 3),
            "last_error": self.last_error,
        }


class ProxyPool:
    """最小的代理池：健康检查 + 轮换。

    刻意不做的事（留给 03 的进阶版）：
        - 不做评分排序（只分死活）
        - 不做冷却（429 之后还会继续用同一个出口）
        - 不做粘滞会话（同一站点每次换出口）
    先把"能挑出一个活的"做对。
    """

    def __init__(self, urls: List[str], check_url: str, timeout: float = 2.0,
                 names: Optional[List[str]] = None):
        # name 只用于报表，不要拿它当身份：真实代理的"身份"是 url + 出口 IP
        self.proxies: List[Proxy] = [
            Proxy(url=u, name=(names[i] if names else u)) for i, u in enumerate(urls)
        ]
        self.check_url = check_url
        self.timeout = timeout
        self._cycle = itertools.cycle(self.proxies)
        self.requests_sent = 0

    # ── 健康检查 ──
    def check_one(self, proxy: Proxy) -> bool:
        """真发一次请求。判据是"靶站回 200 且带我们的标记"，不是 TCP 能连。"""
        try:
            code, body, elapsed = fetch(self.check_url, proxy=proxy.url,
                                        timeout=self.timeout)
            ok = code == 200 and body.get("ok") is True
            proxy.healthy = ok
            proxy.latency_ms = elapsed * 1000
            if ok:
                proxy.successes += 1
                proxy.last_error = ""
            else:
                proxy.failures += 1
                proxy.last_error = f"HTTP {code}"
            return ok
        except Exception as exc:                       # noqa: BLE001
            proxy.healthy = False
            proxy.failures += 1
            proxy.last_error = f"{type(exc).__name__}: {exc}"
            return False

    def check_all(self) -> Dict[str, bool]:
        return {p.name: self.check_one(p) for p in self.proxies}

    # ── 取用与回报 ──
    def alive(self) -> List[Proxy]:
        return [p for p in self.proxies if p.healthy]

    def acquire(self) -> Optional[Proxy]:
        """轮询取一个活着的出口；全死返回 None（调用方必须处理）。"""
        for _ in range(len(self.proxies)):
            proxy = next(self._cycle)
            if proxy.healthy:
                return proxy
        return None

    def report(self, proxy: Proxy, ok: bool, error: str = ""):
        if ok:
            proxy.successes += 1
            proxy.last_error = ""
        else:
            proxy.failures += 1
            proxy.last_error = error
            # 连续失败 2 次就先摘掉，等下一轮健康检查再决定是否恢复
            if proxy.failures >= 2:
                proxy.healthy = False

    def get(self, path: str) -> Optional[dict]:
        proxy = self.acquire()
        if proxy is None:
            return None
        self.requests_sent += 1
        try:
            code, body, _ = fetch(self.check_url.rsplit("/", 1)[0] + path,
                                  proxy=proxy.url, timeout=self.timeout)
            self.report(proxy, code == 200, f"HTTP {code}")
            return {"code": code, "body": body, "exit": proxy.name}
        except Exception as exc:                       # noqa: BLE001
            self.report(proxy, False, f"{type(exc).__name__}: {exc}")
            return {"code": 0, "body": {}, "exit": proxy.name, "error": str(exc)}

    def table(self) -> str:
        rows = ["出口          健康   延迟ms   成功/失败   最近错误"]
        for p in self.proxies:
            latency = "-" if p.latency_ms is None else f"{p.latency_ms:7.1f}"
            rows.append(f"{p.name:<12} {'✅' if p.healthy else '❌':<5} {latency:>7}   "
                        f"{p.successes:>2}/{p.failures:<2}      {p.last_error[:40]}")
        return "\n".join(rows)


# ────────────────────────────── 演示 ──────────────────────────────

def run_demo(as_json: bool = False) -> int:
    checks = []
    with lab_mod.Lab(ban_limit=100) as lab:            # 本课不测限流，阈值放宽
        origin = lab.origin.url
        pool = ProxyPool([lab.proxy_url(n) for n in ("p1", "p2", "p3")],
                         check_url=origin + "/health", names=["p1", "p2", "p3"])

        # 1) 全量健康检查
        result = pool.check_all()
        checks.append(("三个代理都健康", all(result.values()), str(result)))
        checks.append(("健康检查真的发了请求",
                       all(p.successes == 1 for p in pool.proxies), pool.table()))

        # 2) 轮换：9 个请求应该 3/3/3
        hits = {"p1": 0, "p2": 0, "p3": 0}
        for i in range(9):
            got = pool.get(f"/item/{i}")
            hits[got["exit"]] += 1
        checks.append(("轮询分布均匀 3/3/3", hits == {"p1": 3, "p2": 3, "p3": 3}, str(hits)))

        # 3) 杀掉一个：健康检查必须发现，且不再分配
        lab.kill("p2")
        pool.check_all()
        hits_after = {"p1": 0, "p2": 0, "p3": 0}
        for i in range(6):
            got = pool.get(f"/item/k{i}")
            hits_after[got["exit"]] += 1
        checks.append(("死掉的 p2 被摘除", hits_after["p2"] == 0, str(hits_after)))
        checks.append(("剩余两个均分 3/3", hits_after == {"p1": 3, "p2": 0, "p3": 3},
                       str(hits_after)))

        # 4) 全部死掉时返回 None，而不是抛异常或死循环
        lab.kill("p1")
        lab.kill("p3")
        pool.check_all()
        checks.append(("全死时 acquire 返回 None", pool.acquire() is None, "None"))
        checks.append(("全死时 get 也安全返回 None", pool.get("/item/x") is None, "None"))

        snapshot = {
            "proxies": [p.as_dict() for p in pool.proxies],
            "requests_sent": pool.requests_sent,
            "distribution": hits,
            "distribution_after_kill": hits_after,
            "origin_total": lab.origin_total(),
        }

    if as_json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print("── 代理池状态（请求结束后）──")
        print(pool.table())
        print(f"\n轮换分布: {hits}  |  p2 死后: {hits_after}")
        print(f"靶站实际收到请求: {snapshot['origin_total']} 次")

    failed = [c for c in checks if not c[1]]
    print("\n── 断言 ──")
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"{len(checks) - len(failed)}/{len(checks)} 项通过")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="离线自证（等价于跑一遍演示并断言）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 快照")
    args = parser.parse_args()
    return run_demo(as_json=args.json)


if __name__ == "__main__":
    sys.exit(main())
