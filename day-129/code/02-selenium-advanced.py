# -*- coding: utf-8 -*-
"""
Day 129 - Selenium 进阶与避坑：显式等待 / iframe / 反检测 / 懒加载
====================================================================
运行：pip install selenium && python 02-selenium-advanced.py

覆盖的坑：
1. time.sleep 硬等的弊端 -> 显式等待
2. iframe 内元素定位不到 -> switch_to.frame
3. 被识别为自动化 -> 修改 navigator.webdriver
4. 懒加载 -> 滚动到底触发加载
5. 页面刷新后旧元素失效 -> staleness_of
"""
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def build_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    # ⚠️ 坑 3：默认 navigator.webdriver=True，很多网站据此识别爬虫
    # 用启动参数关掉它（比注入 JS 更早生效）
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=opts)
    return driver


def demo_explicit_wait(driver):
    """显式等待的多种条件"""
    driver.get("http://quotes.toscrape.com/js/")
    wait = WebDriverWait(driver, 10, poll_frequency=0.5)

    # ① 等元素"存在"（DOM 有即可，哪怕不可见）
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "quote")))
    # ② 等元素"可见"
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "quote")))
    # ③ 等指定文本出现（比 presence 更严格）
    wait.until(EC.text_to_be_present_in_element(
        (By.CLASS_NAME, "quote"), "“"))
    print("[显式等待] 名言已渲染完成")


def demo_iframe(driver):
    """坑 2：iframe 是独立文档，不切换进去永远定位不到内部元素"""
    # 用 data: 协议本地构造一个含 iframe 的页面，离线可跑
    inner_html = "<h2 id='inner-title'>IFRAME 内部标题</h2>"
    page = f"<iframe id='fr' srcdoc=\"{inner_html}\"></iframe>"
    driver.get("data:text/html," + page.replace("\n", ""))

    # ❌ 直接找会报 NoSuchElementException：
    #    driver.find_element(By.ID, "inner-title")
    # ✅ 正确姿势：先切进 iframe
    driver.switch_to.frame("fr")   # 可用 id / name / 索引 / WebElement
    print("[iframe] 内部标题:", driver.find_element(By.ID, "inner-title").text)
    driver.switch_to.default_content()  # ⚠️ 用完必须切回主文档，否则后续定位全乱


def demo_stale_element(driver):
    """坑 5：翻页/刷新后旧元素的引用失效（StaleElementReferenceException）"""
    driver.get("http://quotes.toscrape.com/js/")
    wait = WebDriverWait(driver, 10)
    old_first = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "quote")))

    next_btn = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "next")))
    next_btn.click()

    # 等"旧的第一条名言失效" + "新的第一条出现"，再重新定位
    WebDriverWait(driver, 10).until(EC.staleness_of(old_first))
    new_first = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "quote")))
    print("[翻页] 新页面第一条:", new_first.text[:30], "...")


def demo_lazy_scroll(driver):
    """坑 4：懒加载图片/内容需要滚动触发"""
    driver.get("http://quotes.toscrape.com/scroll")  # 该站点的无限滚动演示页
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "quote")))

    seen = set()
    for _ in range(5):  # 最多滚 5 次
        # 滚动到底部，触发 JS 加载更多
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        # 等一小会儿让 Ajax 完成（用元素数量变化判断更严谨，这里简化演示）
        WebDriverWait(driver, 5).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, "quote")) > len(seen)
            or not d.find_elements(By.CLASS_NAME, "next"))
        quotes = driver.find_elements(By.CLASS_NAME, "quote")
        for q in quotes:
            seen.add(q.find_element(By.CLASS_NAME, "text").text)
        # 已到底：没有 next 且数量不再增长就停
        try:
            if not driver.find_element(By.CLASS_NAME, "next"):
                break
        except Exception:
            break
    print(f"[懒加载] 共收集 {len(seen)} 条名言")


def main():
    driver = build_driver()
    try:
        demo_explicit_wait(driver)
        demo_iframe(driver)
        demo_stale_element(driver)
        demo_lazy_scroll(driver)
    finally:
        driver.quit()   # ⚠️ quit 不是 close：quit 连 ChromeDriver 一起杀干净


if __name__ == "__main__":
    main()
