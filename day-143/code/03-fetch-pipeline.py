#!/usr/bin/env python3
"""03-fetch-pipeline.py — 实战：静态/动态自动分流取数管线

整合 Day 143 三大件：
  - ProxyPool（来自 01，此处简化内联版）
  - httpx 静态直取（带代理）
  - Playwright 动态渲染兜底（带指纹规避）
  - 结果统一落地 raw_data.jsonl

依赖: pip install httpx playwright && playwright install chromium
用法: python3 03-fetch-pipeline.py <url> [url2 ...]
"""
import json
import random
import sys
import time

import httpx

try:
    from playwright.sync_api import sync_playwright
    HAS_PW = True
except ImportError:
    HAS_PW = False

SEED_PROXIES = ["127.0.0.1:8888"]  # 占位；接入 01 的 ProxyPool 即可
RAW_FILE = "raw_data.jsonl"
JS_HINTS = ("__NEXT_DATA__", "id=\"app\"", "data-reactroot", "vue", "ng-app")

# ---------------- 简化代理层 ----------------
class SimpleProxies:
    def __init__(self, addrs): self._addrs = list(addrs)
    def pick(self):
        return random.choice(self._addrs) if self._addrs else None

# ---------------- 静态直取 ----------------
def fetch_static(url: str, proxy: str | None) -> dict:
    """静态直取；代理失败时自动降级为直连再试一次。"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    if proxy:
        try:
            with httpx.Client(timeout=15, follow_redirects=True,
                              proxy=f"http://{proxy}") as c:
                r = c.get(url, headers=headers)
                return {"url": url, "status": r.status_code, "html": r.text,
                        "via": f"static+proxy({proxy})"}
        except httpx.HTTPError:
            print(f"  [降级] 代理 {proxy} 不可用，改用直连")
    with httpx.Client(timeout=15, follow_redirects=True) as c:
        r = c.get(url, headers=headers)
        return {"url": url, "status": r.status_code, "html": r.text, "via": "static"}

# ---------------- 动态渲染兜底 ----------------
def fetch_dynamic(url: str) -> dict:
    if not HAS_PW:
        return {"url": url, "status": None, "html": None, "via": "dynamic(unavailable)"}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        page.goto(url, wait_until="networkidle", timeout=30000)
        html = page.content()
        browser.close()
    return {"url": url, "status": 200, "html": html, "via": "dynamic(playwright)"}

# ---------------- 分流决策 ----------------
def looks_dynamic(html: str) -> bool:
    """启发式判断：静态 HTML 里出现前端框架挂载点 => 大概率 JS 渲染。"""
    low = html.lower()
    return any(h.lower() in low for h in JS_HINTS) or len(html) < 2000

def pipeline(url: str, proxies: SimpleProxies) -> dict:
    proxy = proxies.pick()
    result = fetch_static(url, proxy)

    if result["status"] == 200 and not looks_dynamic(result["html"]):
        result["mode"] = "static"
        return result

    print(f"  [分流] {url} 需要动态渲染 (status={result['status']})")
    dyn = fetch_dynamic(url)
    dyn["mode"] = "dynamic"
    return dyn

def main():
    urls = sys.argv[1:] or ["https://www.python.org/"]
    proxies = SimpleProxies(SEED_PROXIES)
    with open(RAW_FILE, "a", encoding="utf-8") as f:
        for u in urls:
            t0 = time.time()
            r = pipeline(u, proxies)
            r.pop("html", None)  # 落地时只存元信息，正文另行入库
            r["elapsed_s"] = round(time.time() - t0, 2)
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"✅ {u} -> {r['mode']} via {r['via']} ({r['elapsed_s']}s)")
    print(f"元信息已追加到 {RAW_FILE}")

if __name__ == "__main__":
    main()
