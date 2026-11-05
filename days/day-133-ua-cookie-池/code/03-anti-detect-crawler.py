#!/usr/bin/env python3
"""
03 - 实战：UA + Cookie 池组合的采集器（绕过基础反爬检测）
========================================================
模拟一个带反爬的采集流程（用 httpbin.org 作为目标演示）：
1. 每个身份 = UA + 头模板 + 游客 Cookie，整体轮换
2. 首次请求"预热"获取游客 Cookie（服务器 Set-Cookie）
3. 失效检测 + 自动降级剔除 + 补充
4. 请求间加随机延时，模拟人类节奏

运行：python3 03-anti-detect-crawler.py
"""
import random
import time
import requests

# ---------------------------------------------------------------
# 身份模板：UA 与平台相关头保持一致（一致性是关键！）
# ---------------------------------------------------------------
IDENTITIES = [
    {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/126.0.0.0 Safari/537.36"),
        "sec-ch-ua-platform": '"Windows"',
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
    {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                       "Version/17.4 Safari/605.1.15"),
        "sec-ch-ua-platform": '"macOS"',
        "Accept-Language": "zh-CN,zh;q=0.9",
    },
    {
        "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64; rv:127.0) "
                       "Gecko/20100101 Firefox/127.0"),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    },
]

TARGET = "https://httpbin.org/get"


class AntiDetectCrawler:
    """组合 UA 池 + Cookie 池的采集器。"""

    def __init__(self, max_fails=3):
        self.max_fails = max_fails
        self.identities = []   # [{"headers":..., "session":..., "fails":..., "alive":...}]

    # -- 生成一个新身份并预热（拿游客 Cookie）--
    def spawn_identity(self):
        tmpl = random.choice(IDENTITIES)
        headers = dict(tmpl)
        headers["Accept"] = ("text/html,application/xhtml+xml,"
                             "application/xml;q=0.9,*/*;q=0.8")
        headers["Referer"] = "https://www.google.com/"
        s = requests.Session()
        s.headers.update(headers)
        # 预热：访问首页让服务器种下游客 Cookie
        try:
            s.get(TARGET, timeout=15)
        except requests.RequestException:
            pass
        ident = {"session": s, "fails": 0, "alive": True,
                 "ua": headers["User-Agent"]}
        self.identities.append(ident)
        return ident

    # -- 取一个可用身份（随机挑活着的）--
    def pick(self):
        alive = [i for i in self.identities if i["alive"]]
        if not alive:
            return self.spawn_identity()
        return random.choice(alive)

    # -- 单页采集 --
    def fetch(self):
        ident = self.pick()
        try:
            r = ident["session"].get(TARGET, timeout=15)
            ok = r.status_code == 200
        except requests.RequestException:
            ok = False
        # 失效反馈
        if ok:
            ident["fails"] = 0
        else:
            ident["fails"] += 1
            if ident["fails"] >= self.max_fails:
                ident["alive"] = False
                print(f"  💀 身份降级: {ident['ua'][:35]}...")
                self.spawn_identity()   # 自动补充
        # 随机延时，模拟人类节奏（0.5~1.5s 抖动）
        time.sleep(random.uniform(0.5, 1.0))
        return ok

    def stats(self):
        alive = sum(1 for i in self.identities if i["alive"])
        return f"身份总数={len(self.identities)}, 存活={alive}"


if __name__ == "__main__":
    crawler = AntiDetectCrawler()
    print("=== 初始补充 3 个身份 ===")
    for _ in range(3):
        crawler.spawn_identity()

    print("\n=== 模拟 10 次采集 ===")
    success = 0
    random.seed(7)
    for i in range(10):
        ok = crawler.fetch()
        success += ok
        print(f"[{i + 1:02d}] {'✅ 成功' if ok else '❌ 失败'} | {crawler.stats()}")
    print(f"\n结果: 成功 {success}/10, {crawler.stats()}")
