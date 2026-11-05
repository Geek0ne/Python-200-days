#!/usr/bin/env python3
"""
01 - UA 池基础用法
=================
演示：UA 池 + 完整请求头模板，每个"会话"固定一个浏览器身份。

为什么这样做：
- 只改 UA 不够，反爬会做"头组合"交叉验证
- 一个会话内 UA 必须稳定（真实用户不会中途换浏览器）

运行：python3 01-ua-pool-basic.py
"""
import random
import requests

# ---------------------------------------------------------------
# UA 池：按市场份额加权（Chrome 最多），只用近两年的主流 UA
# ---------------------------------------------------------------
WEIGHTED_UA_POOL = [
    # (UA, 权重)
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", 45),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0", 10),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
     "(KHTML, like Gecko) Version/17.4 Safari/605.1.15", 15),
    ("Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0", 8),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
     "Gecko/20100101 Firefox/127.0", 12),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", 10),
]


def pick_ua() -> str:
    """加权随机抽取 UA，模拟真实用户分布。"""
    uas, weights = zip(*WEIGHTED_UA_POOL)
    return random.choices(uas, weights=weights, k=1)[0]


def build_headers(ua: str) -> dict:
    """
    与 UA 配套的完整请求头模板。
    原理：反爬会校验"头组合指纹"，缺 Accept-Language 的 Chrome 是假的。
    """
    return {
        "User-Agent": ua,
        "Accept": ("text/html,application/xhtml+xml,application/xml;"
                   "q=0.9,image/avif,image/webp,*/*;q=0.8"),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def make_session() -> requests.Session:
    """创建一个'固定身份'的会话：UA 在会话生命周期内不变。"""
    s = requests.Session()
    s.headers.update(build_headers(pick_ua()))
    return s


if __name__ == "__main__":
    # 对比：默认 UA（一眼假） vs 伪装后
    print("=== 默认 UA（会被反爬直接识别）===")
    r = requests.get("https://httpbin.org/get", timeout=15)
    print(r.json()["headers"].get("User-Agent"))

    print("\n=== UA 池伪装后的会话 ===")
    s = make_session()
    # 同一会话发 3 个请求，UA 保持一致
    for i in range(3):
        r = s.get("https://httpbin.org/get", timeout=15)
        print(f"请求{i + 1}: {r.json()['headers'].get('User-Agent')[:60]}...")
