# -*- coding: utf-8 -*-
"""
Day 130 - Playwright 实战：反检测全站爬虫（JS 渲染 + 翻页 + 接口数据）
========================================================================
运行：python 03-practical-playwright.py
产出：quotes_playwright.json

亮点：
1. 反检测：关闭自动化标记 + 真实 UA + 固定视口
2. 自动等待：全程零 WebDriverWait
3. 翻页用 Locator 自动重试（无 StaleElement 问题）
4. 页面数据直接 evaluate 取（比解析 DOM 更稳的思路演示）
"""
import json
from playwright.sync_api import sync_playwright

START_URL = "http://quotes.toscrape.com/js/"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def scrape_all(page):
    """翻页抓取全站，返回列表"""
    all_quotes = []
    page_num = 1
    while True:
        # 自动等待：locator 的操作自带 actionability 检查
        # 但取"数量"前先等第一条渲染出来（goto 只等到 load，JS 可能还在跑）
        page.wait_for_selector("div.quote")

        # 批量提取：一次 JS 调用拿整页数据（比逐元素循环快得多）
        items = page.evaluate(
            """() => Array.from(document.querySelectorAll('div.quote')).map(q => ({
                text: q.querySelector('span.text')?.innerText || '',
                author: q.querySelector('small.author')?.innerText || '',
                tags: Array.from(q.querySelectorAll('a.tag')).map(t => t.innerText),
            }))"""
        )
        all_quotes.extend(items)
        print(f"第 {page_num} 页: {len(items)} 条, 累计 {len(all_quotes)} 条")

        # ---- 翻页判断：next 按钮存在才点 ----
        if page.locator("li.next a").count() == 0:
            break
        # click 自带等待（可见/稳定/可点），不会点空
        page.locator("li.next a").click()
        # 等新页面第一条渲染（防重复抓旧数据）
        page.wait_for_function(
            "() => document.querySelectorAll('div.quote').length > 0 "
            "&& document.querySelector('li.next a') === null "
            "|| document.querySelector('div.quote') !== null"
        )
        page_num += 1
    return all_quotes


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],  # 去掉 webdriver 标记
        )
        context = browser.new_context(
            user_agent=UA,                          # 真实 UA
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = context.new_page()
        page.set_default_timeout(15000)

        page.goto(START_URL)
        data = scrape_all(page)

        # 顺手截一张全页长图存档
        page.screenshot(path="quotes_full.png", full_page=True)

        context.close()
        browser.close()

    with open("quotes_playwright.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    authors = {}
    for q in data:
        authors[q["author"]] = authors.get(q["author"], 0) + 1
    print(f"\n共 {len(data)} 条名言 / {len(authors)} 位作者")
    print("TOP5:", sorted(authors.items(), key=lambda x: -x[1])[:5])
    print("已保存 quotes_playwright.json / quotes_full.png")


if __name__ == "__main__":
    main()
