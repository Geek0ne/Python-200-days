# -*- coding: utf-8 -*-
"""
Day 130 - Playwright 基础：启动、定位器、自动等待
===================================================
运行前：
    pip install playwright
    playwright install chromium

运行：python 01-playwright-basics.py
目标：quotes.toscrape.com/js/（JS 渲染练习站）
"""
from playwright.sync_api import sync_playwright


def main():
    # sync_playwright() 上下文管理器负责启动/关闭驱动进程
    with sync_playwright() as p:
        # launch 一次 ≈ 启动一个浏览器进程
        browser = p.chromium.launch(
            headless=True,  # False 可看到浏览器窗口，调试时很有用
            args=["--disable-blink-features=AutomationControlled"],  # 反检测
        )
        # new_context ≈ 无痕窗口：UA/视口/Cookie 全隔离
        context = browser.new_context(
            user_agent="Mozilla/5.0 (LearnPython-Day130)",
            viewport={"width": 1920, "height": 1080},  # 固定视口防布局错乱
        )
        page = context.new_page()

        # ---------------------------------------------------
        # 1. 打开 JS 渲染页面：goto 默认等到 load 事件
        # ---------------------------------------------------
        page.goto("http://quotes.toscrape.com/js/")

        # ---------------------------------------------------
        # 2. 自动等待演示：不需要 WebDriverWait！
        #    locator 是"惰性"的，操作时才查找并自动重试
        # ---------------------------------------------------
        quotes = page.locator("div.quote")
        print("本页名言数:", quotes.count())

        # 批量取文本（all_inner_texts 内部会等待并批量执行）
        texts = page.locator("span.text").all_inner_texts()
        for t in texts[:3]:
            print(" ", t[:50], "...")

        # ---------------------------------------------------
        # 3. 多种定位器写法（等价定位同一个元素）
        # ---------------------------------------------------
        _ = page.locator("span.text")                  # CSS
        _ = page.locator("div.quote").first            # 第一个
        _ = page.get_by_text("→")                      # 按文本
        author = page.locator("div.quote").first.locator("small.author").inner_text()
        print("第一条作者:", author)

        # ---------------------------------------------------
        # 4. 取属性 / 取数据
        # ---------------------------------------------------
        href = page.locator("li.next a").get_attribute("href")
        print("下一页链接:", href)

        # ---------------------------------------------------
        # 5. 截图（整页长截图，自动滚动处理懒加载）
        # ---------------------------------------------------
        page.screenshot(path="pw_basics.png", full_page=True)
        print("已保存整页截图 pw_basics.png")

        # ---------------------------------------------------
        # 6. 等待指定元素出现（自动等待覆盖不了的场景）
        # ---------------------------------------------------
        page.wait_for_selector("li.next")  # 等"下一页"按钮渲染出来

        browser.close()


if __name__ == "__main__":
    main()
