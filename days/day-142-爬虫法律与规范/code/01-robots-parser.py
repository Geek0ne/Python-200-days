#!/usr/bin/env python3
"""01-robots-parser.py — robots.txt 基础解析与合规判断

用法: python3 01-robots-parser.py [网址]
演示 urllib.robotparser 的核心用法。
"""
import sys
from urllib import robotparser
from urllib.parse import urlparse

# ---- 1. 最基础：让解析器自己去读目标站的 robots.txt ----
def build_parser(site_url: str) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser()
    rp.set_url(site_url.rstrip("/") + "/robots.txt")
    rp.read()  # 发请求并解析；404 或网络失败时视为"全部允许"
    return rp

def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "https://www.python.org"
    rp = build_parser(site)

    print(f"== {site} 的 robots.txt 摘要 ==")
    print(f"  上次读取时间 mtime: {rp.mtime()}")

    # ---- 2. can_fetch：判断某 UA 能否抓某路径 ----
    test_paths = ["/", "/about/", "/admin/secret", "/downloads/"]
    for path in test_paths:
        ok = rp.can_fetch("MyPoliteBot/1.0", site + path)
        print(f"  can_fetch('{path}') -> {'✅ 允许' if ok else '❌ 禁止'}")

    # ---- 3. crawl_delay / request_rate：礼貌参数 ----
    print(f"  Crawl-delay: {rp.crawl_delay('MyPoliteBot/1.0')} 秒")
    print(f"  Request-rate: {rp.request_rate('MyPoliteBot/1.0')}")

    # ---- 4. 也可以不走网络：parse() 直接解析文本 ----
    print("\n== 离线解析示例（最长前缀匹配）==")
    rp2 = robotparser.RobotFileParser()
    rp2.parse([
        "User-agent: *",
        "Allow: /public/",   # ⚠️ 避坑: CPython 的 robotparser 中 Allow 要写在 Disallow 前
        "Disallow: /",       #    顺序颠倒会让 /public/ 也被误判为禁止
    ])
    cases = ["/public/a.html", "/private/x", "/"]
    for p in cases:
        ok = rp2.can_fetch("*", p)
        print(f"  {p:20s} -> {'✅ 允许' if ok else '❌ 禁止'}")
    # 解析: /public/a.html 命中 Allow:/public/ => 允许；其余只命中 Disallow:/ => 禁止。
    # ⚠️ 避坑实测: 若把 Disallow:/ 写在 Allow:/public/ 前面，CPython 会把
    #    /public/a.html 也判为禁止（规则顺序敏感）。写 robots.txt 或解析时
    #    请把更具体的 Allow 规则放在前面，且上线前务必用真实用例回归测试。

    # ---- 5. 小工具函数：给任意 URL 做合规断言 ----
    def is_allowed(url: str, ua: str = "MyPoliteBot/1.0") -> bool:
        o = urlparse(url)
        base = f"{o.scheme}://{o.netloc}"
        return build_parser(base).can_fetch(ua, url)

    print("\n== 合规断言函数 ==")
    for u in [f"{site}/", f"{site}/admin/"]:
        print(f"  {u} -> {'可以抓' if is_allowed(u) else '不要抓'}")

if __name__ == "__main__":
    main()
