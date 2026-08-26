# -*- coding: utf-8 -*-
"""
Day 130 - Playwright 进阶与避坑：多上下文 / 网络拦截 / evaluate / 录屏
=======================================================================
运行：python 02-playwright-advanced.py
"""
import json
from playwright.sync_api import sync_playwright


def demo_contexts(p):
    """多 BrowserContext：一个浏览器进程模拟多个独立用户"""
    browser = p.chromium.launch(headless=True)
    try:
        # 两个 context 各自的 Cookie/存储完全隔离
        ctx_a = browser.new_context(user_agent="UA-UserA")
        ctx_b = browser.new_context(user_agent="UA-UserB")

        pa = ctx_a.new_page()
        pa.goto("http://quotes.toscrape.com/js/")
        print("[ctx A] 标题:", pa.title())

        pb = ctx_b.new_page()
        pb.goto("http://quotes.toscrape.com/js/")
        print("[ctx B] 标题:", pb.title())
        # ⚠️ 坑 1：context 也要关，否则浏览器进程内存越积越多
        ctx_a.close()
        ctx_b.close()
    finally:
        browser.close()


def demo_route(p):
    """网络拦截：拦截请求（反爬）、mock 响应（测试）"""
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # ⚠️ 坑 2：route 要在 goto 之前注册才生效！
    def handler(route, request):
        url = request.url
        if "jquery" in url:            # 演示：把 JS 库请求直接掐断
            print("[拦截] abort:", url)
            route.abort()
        else:
            route.continue_()          # 其余正常放行

    page.route("**/*", handler)

    # mock 演示：给某个接口返回假数据（爬虫测试不依赖外网的神技）
    def mock_api(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"hello": "mocked"}),
        )
    page.route("**/api/data", mock_api)

    page.goto("http://quotes.toscrape.com/js/")
    # jquery 被掐断后该 JS 站点渲染会失败——正好验证拦截生效
    print("[route] 页面名言数（应为 0，因 JS 库被拦）:", page.locator("div.quote").count())

    context.close()
    browser.close()


def demo_evaluate_and_trace(p):
    """evaluate 取 JS 变量 + tracing 录制失败现场"""
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # 开启 trace：截图+DOM快照+网络，失败后可回放排查
    context.tracing.start(screenshots=True, snapshots=True)

    page = context.new_page()
    page.goto("http://quotes.toscrape.com/js/")

    # evaluate：在页面里执行任意 JS 并拿返回值
    # ⚠️ 坑 3：sync API 里 evaluate 的函数会被序列化后送进页面执行，
    #          闭包变量要用参数传入，不能直接引用外部 Python 变量
    n = page.evaluate("() => document.querySelectorAll('div.quote').length")
    print("[evaluate] 名言数量:", n)

    title = page.evaluate("() => document.title")
    print("[evaluate] 标题:", title)

    # 结束录制，保存现场（用 `playwright show-trace trace.zip` 回放）
    context.tracing.stop(path="trace.zip")
    print("已保存 trace.zip（回放命令: playwright show-trace trace.zip）")

    context.close()
    browser.close()


def demo_wait_pitfalls(p):
    """等待相关的坑"""
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    # ⚠️ 坑 4：wait_for_load_state("networkidle") 在有心跳请求的页面
    #          会永远等不到空闲而超时；SPA 更推荐等具体元素
    page.goto("http://quotes.toscrape.com/js/")
    page.wait_for_load_state("networkidle", timeout=15000)  # 此站点无长连接，OK
    print("[wait] networkidle 达成")

    # ⚠️ 坑 5：默认超时 30s，个别慢页面要单独调
    page.set_default_timeout(10000)   # 之后所有操作 10s 超时

    context.close()
    browser.close()


def main():
    with sync_playwright() as p:
        demo_contexts(p)
        demo_route(p)
        demo_evaluate_and_trace(p)
        demo_wait_pitfalls(p)


if __name__ == "__main__":
    main()
