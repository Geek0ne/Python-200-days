#!/usr/bin/env python3
"""Day 137 - 03 - 实战：过 Cloudflare 完整流程（离线 mock 演示）

策略：uc 浏览器过挑战拿 cf_clearance -> curl_cffi 复用会话直连接口
本文件 mock 掉网络与浏览器依赖，离线跑通整个决策流程，
文末附真实环境可直接使用的完整模板。
"""

from unittest.mock import MagicMock


class MockCloudflare:
    """模拟 Cloudflare 三层防护的判定逻辑"""

    def __init__(self):
        self.session_cookie = None

    def check_request(self, request: dict) -> dict:
        # 第1层: TLS 指纹
        if request.get("tls_fingerprint") != "chrome124":
            return {"blocked": True, "layer": "TLS/JA3",
                    "reason": "非浏览器 TLS 握手特征"}
        # 第2层: 挑战 Cookie
        if not self.session_cookie:
            return {"blocked": True, "layer": "JS Challenge",
                    "reason": "缺少 cf_clearance（未过 5 秒盾）"}
        # 第3层: 一致性风控
        if request.get("fingerprint_consistent") is False:
            return {"blocked": True, "layer": "Fingerprint Risk",
                    "reason": "时区与 IP 归属地矛盾"}
        return {"blocked": False, "data": {"list": [1, 2, 3], "ok": True}}


def uc_bypass_challenge(cf: MockCloudflare, driver) -> str:
    """阶段一：undetected-chromedriver 过挑战，拿 cf_clearance"""
    driver.get("https://protected.example.com/data")
    # 真实场景: uc 打开页面后挑战会自动跑，等待 Cookie 出现即可
    cookie = driver.get_cookie("cf_clearance")
    cf.session_cookie = cookie["value"]
    return cookie["value"]


def curl_cffi_fetch(cf: MockCloudflare, page: int) -> dict:
    """阶段二：curl_cffi 复用 Cookie + Chrome TLS 指纹直连接口"""
    request = {
        "tls_fingerprint": "chrome124",           # impersonate 模拟
        "cf_clearance": cf.session_cookie,
        "fingerprint_consistent": True,           # 时区/语言/UA 与 IP 自洽
        "page": page,
    }
    return cf.check_request(request)


def make_mock_driver():
    """mock 一个 uc 浏览器 driver"""
    driver = MagicMock()
    driver.get.return_value = None
    driver.get_cookie.return_value = {"name": "cf_clearance", "value": "mocked_clearance_abc123"}
    return driver


def main():
    cf = MockCloudflare()
    driver = make_mock_driver()

    print("=" * 60)
    print("阶段 0: 裸 requests 直接请求（反面对照）")
    print("=" * 60)
    result = cf.check_request({"tls_fingerprint": "python-urllib3"})
    print(f"  结果: 被拦截 [{result['layer']}] - {result['reason']}")

    print()
    print("=" * 60)
    print("阶段 1: uc 浏览器过 5 秒盾，拿 cf_clearance")
    print("=" * 60)
    clearance = uc_bypass_challenge(cf, driver)
    print(f"  挑战通过，取得 cf_clearance = {clearance}")

    print()
    print("=" * 60)
    print("阶段 2: curl_cffi + Cookie 直连接口（快车道）")
    print("=" * 60)
    for page in (1, 2, 3):
        result = curl_cffi_fetch(cf, page)
        status = "✓ 数据到手: " + str(result["data"]) if not result["blocked"] \
            else "✗ 被拦: " + result["reason"]
        print(f"  第{page}页 {status}")

    print()
    print("=" * 60)
    print("真实环境完整模板（需 pip install undetected-chromedriver curl_cffi）")
    print("=" * 60)
    print(REAL_TEMPLATE)


REAL_TEMPLATE = '''import time
import undetected_chromedriver as uc
from curl_cffi import requests

def get_clearance(url: str) -> tuple[str, str]:
    """uc 过 Cloudflare 挑战，返回 (cf_clearance, user_agent)"""
    driver = uc.Chrome(headless=False)   # 无头模式过 CF 成功率低，尽量有头
    try:
        driver.get(url)
        for _ in range(30):               # 最多等 30s
            if any(c["name"] == "cf_clearance" for c in driver.get_cookies()):
                break
            time.sleep(1)
        cookie = driver.get_cookie("cf_clearance")["value"]
        ua = driver.execute_script("return navigator.userAgent")
        return cookie, ua
    finally:
        driver.quit()

def fetch_api(api: str, cookie: str, ua: str):
    """curl_cffi 复用会话直连（TLS 指纹也模拟 Chrome）"""
    r = requests.get(api, impersonate="chrome124",
                     headers={"User-Agent": ua},
                     cookies={"cf_clearance": cookie})
    return r.json()

if __name__ == "__main__":
    cookie, ua = get_clearance("https://protected.example.com/")
    print(fetch_api("https://protected.example.com/api/list?page=1", cookie, ua))
'''


if __name__ == "__main__":
    main()
