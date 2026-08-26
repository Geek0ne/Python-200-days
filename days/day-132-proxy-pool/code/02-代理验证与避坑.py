"""02-代理验证与避坑.py - 单代理验证器 + 常见陷阱演示

运行: python3 02-代理验证与避坑.py
依赖: pip install aiohttp

覆盖主题：
  - asyncio 并发验证多个代理
  - 验证指标：连通性、延迟、匿名度
  - 常见坑：不设超时、目标协议搞错、环境变量代理干扰
"""

import asyncio
import time

import aiohttp

# 待验证的代理列表（真实使用时从免费网站抓取）
CANDIDATES = [
    "http://123.56.1.2:8080",
    "http://111.13.3.4:80",
    "http://58.220.95.6:8080",
]

# 验证目标：选择稳定、响应快的检测站点
# httpbin.org 有时被墙/限流，可换成自己的服务器
TEST_URL = "https://httpbin.org/ip"


async def validate_one(session: aiohttp.ClientSession, proxy: str) -> dict:
    """验证单个代理，返回验证结果 dict"""
    start = time.monotonic()
    try:
        timeout = aiohttp.ClientTimeout(total=8)  # 坑1: 不设超时会被死代理拖死
        async with session.get(TEST_URL, proxy=proxy, timeout=timeout) as resp:
            latency = round((time.monotonic() - start) * 1000)
            data = await resp.json()
            return {
                "proxy": proxy,
                "ok": True,
                "latency_ms": latency,
                "exit_ip": data.get("origin"),
            }
    except Exception as e:
        return {"proxy": proxy, "ok": False, "error": type(e).__name__}


async def validate_all(proxies: list[str]) -> list[dict]:
    """并发验证所有代理 -- 协程让 1000 个代理的验证从小时级降到秒级"""
    conn = aiohttp.TCPConnector(limit=200)  # 并发上限
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [validate_one(session, p) for p in proxies]
        return await asyncio.gather(*tasks)


def show_pitfalls():
    """三个最常见的代理坑"""
    print("\n=== 常见陷阱 ===")

    print("""
坑 1: 不设 timeout
     免费代理 90% 是死的，requests/aiohttp 默认无超时，
     一个死代理就能挂住整个验证流程。
     ✅ 永远显式设置 timeout=(3, 8)

坑 2: proxies 字典的 key 搞错
     key 是你访问的目标协议，不是代理的协议：
     proxies = {"https": "http://1.2.3.4:8080"}  # ✅ 正确
     proxies = {"httpx": "http://1.2.3.4:8080"}  # ❌ 拼错则代理不生效

坑 3: 环境变量代理干扰
     若 shell 设置了 HTTP_PROXY/HTTPS_PROXY，requests 会自动使用，
     本地调试时代理可能悄悄生效。可在会话开头：
     import os; os.environ.pop("HTTP_PROXY", None)
""")


if __name__ == "__main__":
    results = asyncio.run(validate_all(CANDIDATES))
    print("=== 验证结果 ===")
    for r in results:
        if r["ok"]:
            print(f"✅ {r['proxy']}  延迟 {r['latency_ms']}ms  出口 {r['exit_ip']}")
        else:
            print(f"❌ {r['proxy']}  失败原因: {r['error']}")
    show_pitfalls()
