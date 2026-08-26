"""03-高匿名代理池实战.py - 完整可运行的最小代理池

架构：抓取器 -> 并发验证器 -> 分数池 -> 随机取用 API -> 业务侧自动换代理重试

运行: python3 03-高匿名代理池.py
依赖: pip install aiohttp requests

说明：免费代理来源随时间变化，抓取器内置的站点可能失效。
      本文件的核心是「代理池架构与分数机制」，跑通流程即可学习。
"""

import asyncio
import random
import time

import aiohttp
import requests

# ============================================================
# 模块 1: 抓取器 Fetcher
# ============================================================
# 生产环境来源越多越好；这里演示 2 个真实免费站点的解析方式


def fetch_89ip(session: requests.Session) -> list[str]:
    """从 89ip 抓取免费代理（表格页面，直接正则提取）"""
    import re

    proxies = []
    try:
        resp = session.get("https://www.89ip.cn/tqdl.html?num=30", timeout=8)
        # 页面格式: IP 在 <td> 中，后面跟着端口
        rows = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})</td>\s*<td>(\d{2,5})", resp.text)
        for ip, port in rows:
            proxies.append(f"http://{ip}:{port}")
    except Exception as e:
        print(f"  [89ip] 抓取失败: {e}")
    return proxies


def fetch_free_proxy_list(session: requests.Session) -> list[str]:
    """从 free-proxy-list.net 抓取（海外源）"""
    import re

    proxies = []
    try:
        resp = session.get("https://free-proxy-list.net/", timeout=10)
        rows = re.findall(r"(\d{1,3}(?:\.\d{1,3}){3})</td><td>(\d{2,5})", resp.text)
        for ip, port in rows:
            proxies.append(f"http://{ip}:{port}")
    except Exception as e:
        print(f"  [fpl] 抓取失败: {e}")
    return proxies


# ============================================================
# 模块 2: 验证器 Validator（asyncio 并发）
# ============================================================

TEST_URL = "https://httpbin.org/ip"


async def validate(session: aiohttp.ClientSession, proxy: str) -> dict | None:
    """验证代理：连通 + 延迟。通过返回记录，失败返回 None"""
    start = time.monotonic()
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        async with session.get(TEST_URL, proxy=proxy, timeout=timeout) as resp:
            latency = round((time.monotonic() - start) * 1000)
            if resp.status == 200:
                # 进一步要求低延迟才算「优秀」
                return {"proxy": proxy, "latency": latency, "score": 50}
    except Exception:
        return None
    return None


# ============================================================
# 模块 3: 代理池（分数机制，模拟 Redis ZSet）
# ============================================================


class ProxyPool:
    """内存版代理池：score 0~100，验证成功 +10，失败 -10，归零移除"""

    def __init__(self):
        self._pool: dict[str, dict] = {}  # proxy -> {"latency": ms, "score": int}
        self.raw_candidates: list[str] = []

    # ---- 抓取 ----
    def fetch_all(self) -> None:
        with requests.Session() as s:
            s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) Chrome/120"
            sources = [fetch_89ip, fetch_free_proxy_list]
            for src in sources:
                got = src(s)
                print(f"  [{src.__name__}] 抓到 {len(got)} 个")
                self.raw_candidates.extend(got)
        self.raw_candidates = list(set(self.raw_candidates))
        # 新代理初始分 50：半信半疑
        for p in self.raw_candidates:
            if p not in self._pool:
                self._pool[p] = {"latency": None, "score": 50}

    # ---- 验证 ----
    async def validate_all(self) -> None:
        dead = []
        conn = aiohttp.TCPConnector(limit=100)
        async with aiohttp.ClientSession(connector=conn) as session:
            tasks = [validate(session, p) for p in self._pool]
            results = await asyncio.gather(*tasks)

        for proxy, result in zip(self._pool, results):
            if result:
                self._pool[proxy]["score"] = min(100, self._pool[proxy]["score"] + 10)
                self._pool[proxy]["latency"] = result["latency"]
            else:
                self._pool[proxy]["score"] -= 10
                if self._pool[proxy]["score"] <= 0:
                    dead.append(proxy)
        for p in dead:
            self._pool.pop(p)
        alive = self.stats()
        print(f"  验证完成: 可用 {alive['usable']}/{alive['total']}，移除 {len(dead)}")

    # ---- 取用 API ----
    def get_proxy(self, min_score: int = 60) -> str | None:
        """随机返回一个高分数代理（随机避免所有爬虫集中在最快那一个上）"""
        usable = [p for p, info in self._pool.items() if info["score"] >= min_score]
        return random.choice(usable) if usable else None

    def mark_fail(self, proxy: str) -> None:
        """业务侧使用失败时调用：扣分，归零移除"""
        if proxy in self._pool:
            self._pool[proxy]["score"] -= 10
            if self._pool[proxy]["score"] <= 0:
                del self._pool[proxy]

    def stats(self) -> dict:
        return {
            "total": len(self._pool),
            "usable": sum(1 for i in self._pool.values() if i["score"] >= 60),
        }

    # ---- 后台保活循环（生产环境独立协程/进程）----
    async def keep_alive(self, interval: int = 600) -> None:
        while True:
            await self.validate_all()
            await asyncio.sleep(interval)


# ============================================================
# 模块 4: 业务侧使用示例（自动换代理重试）
# ============================================================


def crawl_with_pool(pool: ProxyPool, url: str, max_retry: int = 5) -> str | None:
    """爬虫业务：拿代理 -> 请求 -> 失败扣分换下一个"""
    for _ in range(max_retry):
        proxy = pool.get_proxy()
        if proxy is None:
            print("  代理池耗尽，等待下一轮抓取验证")
            return None
        try:
            resp = requests.get(
                url,
                proxies={"http": proxy, "https": proxy},
                timeout=(3, 8),
            )
            if resp.status_code == 200:
                print(f"  ✅ 成功（via {proxy}）")
                return resp.text
            # 403/429 说明被目标站封了 -> 扣分换代理
            pool.mark_fail(proxy)
        except Exception:
            pool.mark_fail(proxy)  # 连接失败 -> 扣分
    return None


# ============================================================
# 主流程演示
# ============================================================

if __name__ == "__main__":
    pool = ProxyPool()

    print("① 抓取免费代理...")
    pool.fetch_all()

    print("② 并发验证...")
    asyncio.run(pool.validate_all())

    print("③ 业务抓取（自动换代理重试）...")
    crawl_with_pool(pool, "https://httpbin.org/ip")

    print("④ 池状态:", pool.stats())
