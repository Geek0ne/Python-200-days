#!/usr/bin/env python3
"""01-proxy-pool.py — 基础：带评分与后台校验的代理池

纯标准库实现（校验用 http://httpbin.org/ip，可用 PROXY_SOURCE 换成任意
返回纯文本代理列表的 URL，格式 host:port 每行一个）。

用法: python3 01-proxy-pool.py
"""
import random
import threading
import time
import urllib.request

PROXY_SOURCE = "https://example.com/proxies.txt"  # 占位：换成你的代理来源
SEED_PROXIES = [  # 演示用种子代理（不可用属正常，会被自动淘汰）
    "127.0.0.1:8888",
    "127.0.0.1:8889",
    "127.0.0.1:8890",
]
CHECK_URL = "http://httpbin.org/ip"
CHECK_INTERVAL = 30  # 秒
MAX_FAILS = 3        # 连续失败 MAX_FAILS 次即淘汰


class Proxy:
    __slots__ = ("addr", "ok", "fail", "latency_ms")

    def __init__(self, addr: str):
        self.addr = addr
        self.ok = 0
        self.fail = 0
        self.latency_ms = None

    @property
    def score(self) -> float:
        total = self.ok + self.fail
        if total == 0:
            return 0.5  # 新代理给中性分
        return self.ok / total

    def record(self, success: bool, latency_ms=None):
        if success:
            self.ok += 1
            self.fail = 0
            self.latency_ms = latency_ms
        else:
            self.fail += 1
            self.ok = 0

    @property
    def dead(self) -> bool:
        return self.fail >= MAX_FAILS


class ProxyPool:
    """线程安全的加权随机代理池。"""

    def __init__(self, proxies: list[str] | None = None):
        self._lock = threading.Lock()
        self._proxies = [Proxy(a) for a in (proxies or SEED_PROXIES)]

    def add(self, addr: str):
        with self._lock:
            if not any(p.addr == addr for p in self._proxies):
                self._proxies.append(Proxy(addr))

    def acquire(self) -> str | None:
        """加权随机取一个代理地址：score 越高越可能被选中。"""
        with self._lock:
            alive = [p for p in self._proxies if not p.dead]
            if not alive:
                return None
            weights = [max(p.score, 0.01) for p in alive]
            return random.choices(alive, weights=weights, k=1)[0].addr

    def feedback(self, addr: str, success: bool, latency_ms=None):
        """爬虫用完代理后回报结果（成功/失败），驱动评分。"""
        with self._lock:
            for p in self._proxies:
                if p.addr == addr:
                    p.record(success, latency_ms)
                    break

    def stats(self) -> str:
        with self._lock:
            lines = [f"  {p.addr:20s} score={p.score:.2f} ok={p.ok} fail={p.fail}"
                     + (" (淘汰)" if p.dead else "") for p in self._proxies]
            return f"代理池({len(self._proxies)} 个):\n" + "\n".join(lines)


def check_proxy(addr: str, timeout: float = 8) -> tuple[bool, float | None]:
    """用 CHECK_URL 验证代理可用性，返回 (是否成功, 延迟ms)。"""
    proxy_handler = urllib.request.ProxyHandler({
        "http": f"http://{addr}", "https": f"http://{addr}",
    })
    opener = urllib.request.build_opener(proxy_handler)
    t0 = time.time()
    try:
        with opener.open(CHECK_URL, timeout=timeout) as resp:
            resp.read(512)
        return True, round((time.time() - t0) * 1000)
    except Exception:
        return False, None


def background_checker(pool: ProxyPool):
    """后台线程：定期全量校验池内代理。"""
    while True:
        with pool._lock:
            addrs = [p.addr for p in pool._proxies if not p.dead]
        for addr in addrs:
            ok, lat = check_proxy(addr)
            pool.feedback(addr, ok, lat)
        time.sleep(CHECK_INTERVAL)


def main():
    pool = ProxyPool(SEED_PROXIES)
    t = threading.Thread(target=background_checker, args=(pool,), daemon=True)
    t.start()

    # 模拟爬虫取用 5 次
    for i in range(5):
        addr = pool.acquire()
        if addr is None:
            print("池已空，等待补充新代理")
            break
        print(f"[{i+1}] 取得代理: {addr} (score 加权随机)")
        time.sleep(0.2)
    print(pool.stats())


if __name__ == "__main__":
    main()
