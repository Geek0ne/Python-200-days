# -*- coding: utf-8 -*-
"""
Day 129 - Selenium 基础：打开浏览器、定位元素、等待策略
=========================================================
运行前：pip install selenium
（Selenium 4.6+ 自带 Selenium Manager，会自动下载 ChromeDriver，无需手动配置）

运行：python 01-selenium-basics.py
说明：目标站点 quotes.toscrape.com 是官方爬虫练习站；
     其 /js/ 版本内容完全由 JavaScript 渲染，requests 抓不到，
     正好用来演示"动态渲染"场景。
"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def build_driver(headless=True):
    """创建浏览器实例。封装成函数便于复用"""
    opts = Options()
    if headless:
        # --headless=new 是 Chrome 109+ 推荐的无头模式，渲染行为和有头一致
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")  # ⚠️ 无头模式务必固定窗口大小，
                                                  # 否则响应式网站可能渲染成手机版
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")  # Linux root 用户常需此参数
    driver = webdriver.Chrome(options=opts)
    # 隐式等待：全局兜底（每个 find_element 最多等 10 秒）
    # ⚠️ 隐式/显式不要混用，本函数只设置一个演示位
    driver.implicitly_wait(10)
    return driver


def main():
    driver = build_driver(headless=True)
    try:
        # ---------------------------------------------------
        # 1. 对比：requests 抓 JS 渲染页拿到的只是空壳
        #    （页面内容在 <div id="quotes"> 里由 JS 填充）
        # ---------------------------------------------------
        driver.get("http://quotes.toscrape.com/js/")

        # ---------------------------------------------------
        # 2. 显式等待：等到"至少一条名言出现"再抓
        #    为什么不 sleep？网络快不浪费时间，网络慢不会崩
        # ---------------------------------------------------
        wait = WebDriverWait(driver, timeout=10, poll_frequency=0.5)
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "quote")))

        quotes = driver.find_elements(By.CLASS_NAME, "quote")
        print(f"本页名言数: {len(quotes)}")
        for q in quotes[:3]:  # 只打印前 3 条演示
            text = q.find_element(By.CLASS_NAME, "text").text
            author = q.find_element(By.CLASS_NAME, "author").text
            print(f"  {author}: {text[:40]}...")

        # ---------------------------------------------------
        # 3. 八种定位方式演示（同一元素用不同方式找）
        # ---------------------------------------------------
        # By.CLASS_NAME
        _ = driver.find_element(By.CLASS_NAME, "quote")
        # By.CSS_SELECTOR（推荐通用方案）
        _ = driver.find_element(By.CSS_SELECTOR, "div.quote span.text")
        # By.XPATH（最强：可按文本匹配）
        _ = driver.find_element(By.XPATH, '//span[@class="text"][contains(., "world")]')
        # By.TAG_NAME
        title = driver.find_element(By.TAG_NAME, "title").get_attribute("textContent")
        print(f"页面标题: {title}")

        # ---------------------------------------------------
        # 4. 页面源码对比：Selenium 的 page_source 是"渲染后"的
        #    这就是它和 requests 的本质区别！
        # ---------------------------------------------------
        html = driver.page_source
        print(f"渲染后 HTML 长度: {len(html)}（含名言内容: {'world' in html}）")

        # ---------------------------------------------------
        # 5. 截图（无头模式也能用，调试神器）
        # ---------------------------------------------------
        driver.save_screenshot("selenium_basics.png")
        print("已保存截图 selenium_basics.png")

    finally:
        # ⚠️ 必须关闭，否则 Chrome 进程残留，越积越多
        driver.quit()


if __name__ == "__main__":
    main()
