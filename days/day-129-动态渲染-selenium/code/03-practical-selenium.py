# -*- coding: utf-8 -*-
"""
Day 129 - Selenium 实战：抓取 JS 渲染页面（完整流程）
======================================================
目标：http://quotes.toscrape.com/js/ —— 名言完全由 JS 渲染
功能：自动翻页抓取全站名言 + 作者 + 标签，保存为 JSON

流程：
  1. 无头模式启动（含反检测参数）
  2. 显式等待每页渲染完成
  3. 提取数据 -> 翻页 -> 直到没有 next 按钮
  4. 存 JSON、打印统计
"""
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

START_URL = "http://quotes.toscrape.com/js/"


def build_driver():
    """无头 + 反检测的浏览器"""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    # 练习站也设个 UA，养成习惯
    opts.add_argument("user-agent=Mozilla/5.0 (LearnPython-Day129)")
    return webdriver.Chrome(options=opts)


def scrape_page(driver, wait):
    """提取当前页所有名言。返回 dict 列表"""
    # 等"本页至少一条 quote 出现"，确保 JS 渲染完成
    wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "quote")))
    data = []
    for q in driver.find_elements(By.CLASS_NAME, "quote"):
        # 每条数据都重新从 DOM 取，避免缓存失效问题
        text = q.find_element(By.CLASS_NAME, "text").text
        author = q.find_element(By.CLASS_NAME, "author").text
        tags = [t.text for t in q.find_elements(By.CLASS_NAME, "tag")]
        data.append({"text": text, "author": author, "tags": tags})
    return data


def main():
    driver = build_driver()
    wait = WebDriverWait(driver, timeout=10, poll_frequency=0.5)
    all_quotes = []
    page = 1
    try:
        driver.get(START_URL)
        while True:
            items = scrape_page(driver, wait)
            all_quotes.extend(items)
            print(f"第 {page} 页：抓到 {len(items)} 条，累计 {len(all_quotes)} 条")

            # ---- 翻页 ----
            try:
                next_btn = driver.find_element(By.CLASS_NAME, "next")
            except NoSuchElementException:
                break  # 没有 next 了 = 最后一页，正常结束

            old_first = driver.find_element(By.CLASS_NAME, "quote")
            next_btn.find_element(By.TAG_NAME, "a").click()

            # 等"旧元素失效"确认页面真的刷新了（防拿重复数据）
            try:
                WebDriverWait(driver, 10).until(EC.staleness_of(old_first))
            except TimeoutException:
                print("页面未刷新，可能已到末页，停止")
                break
            page += 1

    finally:
        driver.quit()

    # ---- 保存 ----
    with open("quotes_js.json", "w", encoding="utf-8") as f:
        json.dump(all_quotes, f, ensure_ascii=False, indent=2)

    # ---- 统计 ----
    authors = {}
    for q in all_quotes:
        authors[q["author"]] = authors.get(q["author"], 0) + 1
    top = sorted(authors.items(), key=lambda x: -x[1])[:5]
    print(f"\n共 {len(all_quotes)} 条名言，{len(authors)} 位作者")
    print("TOP5 作者:", top)
    print("已保存到 quotes_js.json")


if __name__ == "__main__":
    main()
