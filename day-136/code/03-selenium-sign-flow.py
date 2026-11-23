#!/usr/bin/env python3
"""Day 136 - 03 - 实战：无头浏览器取签名自动化流程（离线 mock 演示）

场景：目标加密函数强依赖浏览器环境（读 canvas、检测 DOM），
补环境成本过高 -> 改用 Selenium 驱动真实浏览器执行 JS。

本文件离线可运行：
- 用 mock 代替真实 Selenium（未安装 selenium 也能跑通流程）
- 附带真实环境可直接使用的完整代码模板（文末字符串）
"""

from unittest.mock import MagicMock


# ─── 1. 注入浏览器的 Hook 脚本（addScriptToEvaluateOnNewDocument 用） ──

HOOK_JS = """(function () {
  var _orig = window.getSign;
  window.getSign = function (p) {
    var r = _orig(p);
    window.__sign_log__ = window.__sign_log__ || [];
    window.__sign_log__.push({ params: p, sign: r, ts: Date.now() });
    return r;
  };
})();"""


# ─── 2. mock 一个"浏览器页面"：模拟目标网站环境 ────────────────

def make_mock_driver():
    """模拟 Selenium driver + 一个会自己调 getSign 的网页"""
    driver = MagicMock()
    # 模拟目标网站的加密函数（真实场景中是页面里几十万行混淆 JS）
    driver.execute_script.side_effect = _execute_script
    return driver


def _execute_script(script: str, *args):
    """模拟浏览器执行 JS"""
    import hashlib
    if script == HOOK_JS:
        # 注入 Hook：把包装函数挂上（这里直接返回成功）
        _execute_script.injected = True
        return None
    if script.startswith("return window.getSign"):
        # 真实场景: 浏览器里执行页面已有的加密函数
        params = args[0] if args else "{}"
        return hashlib.md5(("browser_secret|" + str(params)).encode()).hexdigest()
    if script == "return window.__sign_log__":
        return [{"params": "page=1", "sign": "mocked...", "ts": 1770000000123}]
    return None


# ─── 3. 自动化取签名主流程 ────────────────────────────────────

def get_sign_via_browser(driver, params: str) -> str:
    """核心流程：驱动浏览器执行目标 JS，拿回签名"""
    # 步骤1: 每个新文档加载前注入 Hook（时机早于页面脚本！）
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument", {"source": HOOK_JS}
    )
    # 步骤2: 加载目标页面（页面 JS 执行时 Hook 已就位）
    driver.get("https://www.example.com/list")
    # 步骤3: 直接调用页面里的加密函数取签名
    sign = driver.execute_script("return window.getSign(arguments[0])", params)
    return sign


def main():
    print("=" * 60)
    print("无头浏览器取签名流程（mock 演示，离线可跑）")
    print("=" * 60)

    driver = make_mock_driver()
    params = "page=1&size=20&ts=1770000000"
    sign = get_sign_via_browser(driver, params)

    print(f"  ① Hook 已通过 addScriptToEvaluateOnNewDocument 注入")
    print(f"  ② 页面已加载: https://www.example.com/list")
    print(f"  ③ 取到签名: sign={sign}")
    print(f"  ④ Python 携带签名请求接口 -> 拿到数据 ✓")

    print()
    print("=" * 60)
    print("真实环境完整模板（安装 selenium 后可直接用）")
    print("=" * 60)
    print(REAL_TEMPLATE)


REAL_TEMPLATE = '''import time
from selenium import webdriver

def make_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")  # 隐藏 webdriver 特征
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    d = webdriver.Chrome(options=opts)
    d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                      {"source": HOOK_JS})
    return d

def fetch_data(page: int):
    d = make_driver()
    try:
        d.get("https://www.example.com/list")
        time.sleep(2)  # 等页面 JS 执行
        sign = d.execute_script(
            "return window.getSign(arguments[0])", f"page={page}")
        # 拿到 sign 后用 requests 直接请求接口（速度远快于逐页开浏览器）
        import requests
        resp = requests.get("https://www.example.com/api/list",
                            params={"page": page, "sign": sign},
                            headers={"User-Agent": "..."})
        return resp.json()
    finally:
        d.quit()

if __name__ == "__main__":
    print(fetch_data(1))
'''


if __name__ == "__main__":
    main()
