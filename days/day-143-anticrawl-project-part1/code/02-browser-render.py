#!/usr/bin/env python3
"""02-browser-render.py — 进阶：Playwright 无头渲染 + XHR 拦截 + 指纹规避

依赖: pip install playwright && playwright install chromium
用法: python3 02-browser-render.py [URL]

两条取数路线同时演示：
  A) DOM 路线 —— 等 networkidle 后取标题
  B) 接口路线 —— 拦截 JSON 响应，直接拿结构化数据
"""
import json
import sys

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("请先安装: pip install playwright && playwright install chromium")

# 抹平无头指纹的基础 init script（原理见 Day 137 浏览器指纹）
STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = { runtime: {} };
"""

def render(url: str):
    captured_json = []  # 拦截到的 JSON 响应

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"),
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
        )
        page.add_init_script(STEALTH_JS)

        # 路线 B：监听所有响应，捕获 JSON
        def on_response(resp):
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                try:
                    captured_json.append({"url": resp.url, "data": resp.json()})
                except Exception:
                    pass

        page.on("response", on_response)

        # 路线 A：DOM 渲染路线
        page.goto(url, wait_until="networkidle", timeout=30000)
        title = page.title()
        n_nodes = page.evaluate("document.querySelectorAll('*').length")

        browser.close()

    print(f"== 路线 A: DOM 渲染 ==")
    print(f"  页面标题: {title}")
    print(f"  DOM 节点数: {n_nodes}")

    print(f"\n== 路线 B: 拦截到 {len(captured_json)} 个 JSON 响应 ==")
    for item in captured_json[:5]:
        preview = json.dumps(item["data"], ensure_ascii=False)[:200]
        print(f"  {item['url']}\n    -> {preview}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://www.python.org/"
    render(target)
