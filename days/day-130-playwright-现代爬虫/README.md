# Day 130 - Playwright 现代爬虫

> 🎯 **今日目标**：掌握微软出品的 Playwright 浏览器自动化框架，理解它相比 Selenium 的优势（自动等待、多浏览器、API 更现代），并学会用它突破反爬网站。

---

## 📋 概念总览

### Playwright 是什么？

微软 2020 年开源的浏览器自动化框架（由 Puppeteer 原班人马打造），设计目标就是解决 Selenium 的历史包袱。

### Selenium vs Playwright 全面对比

| 维度 | Selenium | Playwright |
|---|---|---|
| 协议 | 每浏览器一个 Driver（ChromeDriver/GeckoDriver） | **直接说 CDP/协议**，内置驱动，`playwright install` 一条命令装齐 |
| 自动等待 | ❌ 手写 WebDriverWait | ✅ **默认所有操作自动等待**元素可用 |
| 浏览器 | Chrome/Firefox/Safari/Edge（驱动版本易踩坑） | Chromium / Firefox / WebKit（Safari 内核） |
| 多浏览器上下文 | 一个浏览器一个"用户" | ✅ BrowserContext：秒开无痕隔离会话，Cookie/存储互不干扰 |
| 并发 | 多线程/多进程（重） | ✅ 原生 async，一个进程开 N 个 context 并发 |
| 网络拦截 | 需要 CDP 硬核操作 | ✅ `page.route()` 几行代码拦截/改写/mock 请求 |
| API 风格 | find_element + click 分离式 | ✅ 链式 `page.locator().click()`，自动重试 |
| 录制 | 需插件 | ✅ `playwright codegen` 录制生成代码 |
| Trace | 弱 | ✅ Trace Viewer：失败现场回放（截图+DOM快照+网络） |

**结论**：新项目首选 Playwright；维护老项目、生态兼容（如配合 BrowserStack 云测）仍常见 Selenium。

---

## 🏗️ 一、安装与启动

```bash
pip install playwright
playwright install chromium   # 下载浏览器内核（Firefox/WebKit 可选装）
```

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://quotes.toscrape.com/js/")
    print(page.title())
    browser.close()
```

**同步 API vs 异步 API**：
- `sync_api`：写法直观，爬虫脚本够用（本文主线）。
- `async_api`：高并发场景（多页面同时爬），配合 `asyncio.gather` 性能拉满。

---

## ⏳ 二、自动等待（最大的进步）

Selenium 里 80% 的代码在写等待；Playwright 里几乎不用写：

```python
# Playwright：click() 自动等待元素【可见+启用+稳定（不抖动）】
page.locator("a.next").click()

# 等价于 Selenium 的三行：
# wait.until(EC.element_to_be_clickable(...)); elem.click()
```

**自动等待在等什么（actionability 检查）**：

```
操作执行前，Playwright 反复检查：
  1. Visible      元素可见
  2. Stable       元素尺寸稳定（动画结束）
  3. Receives events   没被遮挡
  4. Enabled      没被 disabled
  全部满足才执行，默认 30s 超时（可通过 timeout= 改）
```

需要手动等待时（比如等 Ajax 数据）：

```python
page.wait_for_selector("li.product")                 # 等选择器出现
page.wait_for_url("**/detail/**")                    # 等 URL 变化
page.wait_for_load_state("networkidle")              # 等网络空闲（SPA 加载完）
page.wait_for_function("document.querySelectorAll('.item').length > 20")
```

**⚠️ 坑**：`networkidle` 在长轮询页面（一直有心跳请求）永远不会空闲，会超时--这种情况改用具体元素等待。

---

## 🔍 三、定位器（Locator）

Playwright 的定位器是**惰性 + 自动重试**的（Selenium 的 WebElement 是即时快照，页面一变就 Stale）：

```python
page.locator("#username")                        # CSS
page.locator("text=登录")                         # 按文本（超好用！）
page.get_by_role("button", name="搜索")           # 语义化（推荐！）
page.get_by_placeholder("请输入关键词")
page.get_by_text("下一页")
page.locator("li.item").nth(0)                   # 第 N 个
page.locator("li.item").filter(has_text="Python") # 过滤
```

**取数据**：

```python
page.locator("h1").text_content()        # 文本（含隐藏）
page.locator("h1").inner_text()          # 可见文本
page.locator("a").get_attribute("href")  # 属性
page.locator("li.item").all_text_contents()  # 批量取文本列表
```

---

## 🎭 四、多浏览器与 BrowserContext

### 4.1 三种内核

```python
browser = p.chromium.launch()   # Chrome/Edge 内核
browser = p.firefox.launch()    # 火狐
browser = p.webkit.launch()     # Safari 内核（测 iOS 兼容性神器）
```

### 4.2 BrowserContext（会话隔离）

```python
context = browser.new_context(
    user_agent="Mozilla/5.0 ...",
    viewport={"width": 1920, "height": 1080},
    locale="zh-CN",
    storage_state="login.json",   # 恢复登录态（保存的 Cookie）
)
page = context.new_page()
```

**为什么 Context 是大杀器？**
- 开一个 context ≈ 开一个无痕窗口，**比启动浏览器进程快一个数量级**。
- 并发爬虫 = 1 个浏览器 + N 个 context，各自 Cookie/缓存互不污染（模拟 N 个独立用户）。

---

## 📸 五、截图与录屏

```python
page.screenshot(path="page.png")               # 视口截图
page.screenshot(path="full.png", full_page=True)  # 整页长截图（懒加载自动滚）
context.tracing.start(screenshots=True, snapshots=True)
# ... 操作 ...
context.tracing.stop(path="trace.zip")         # 失败现场，playwright show-trace trace.zip 回放
```

调试三板斧：`page.pause()`（打开 Inspector）、`playwright codegen`（录制）、Trace（回放）。

---

## 🥷 六、反爬突破实战

### 6.1 隐身/反检测

```python
browser = p.chromium.launch(
    headless=True,
    args=["--disable-blink-features=AutomationControlled"],
)
context = browser.new_context(
    user_agent=...,                    # 换真实 UA
    viewport={"width": 1920, "height": 1080},
    java_script_enabled=True,
)
# 修补 navigator.webdriver（Playwright 的 chromium 默认已处理大部分指纹，
# 比普通 Selenium 裸奔更难被识别；对抗严格站点可用 playwright-stealth 补丁）
```

### 6.2 网络拦截（page.route）

可以**拦截/mock 请求**，让反爬脚本"打空"：

```python
# 拦截掉指纹检测脚本，直接返回空 JS
def block(route, request):
    if "fingerprint.js" in request.url:
        route.abort()          # 或者 route.fulfill(body="") 假装成功
    else:
        route.continue_()

page.route("**/*", block)
```

### 6.3 提取"接口数据"（比解析 DOM 更稳）

很多 SPA 数据在 `window.__INITIAL_STATE__` 里，直接取 JS 变量比爬 DOM 快而稳：

```python
data = page.evaluate("() => window.__INITIAL_STATE__")
```

### 6.4 常见反爬手段与应对

| 反爬手段 | 应对 |
|---|---|
| UA/指纹检测 | 真实 UA + stealth 补丁 + 固定 viewport |
| webdriver 标记 | launch args 关闭 AutomationControlled |
| 行为检测（轨迹） | `page.mouse.move()` 模拟人手滑动（拖动验证码） |
| IP 频率限制 | 代理池（Day 132 详讲） |
| 验证码 | 打码平台 / 换 Playwright 无头检测概率更低 |

---

## 💻 七、实战

完整代码见 `code/03-practical-playwright.py`：Playwright 版全站爬虫（quotes.toscrape.com/js/），含自动翻页、上下文复用、反检测、接口数据提取。

---

## ❓ 思考题

1. Playwright 的 Locator 和 Selenium 的 WebElement 有什么本质区别？为什么 Playwright 没有 StaleElementReferenceException？
2. "自动等待"在 click 前检查了哪些条件？什么情况下自动等待救不了你（仍需手动 wait_for）？
3. BrowserContext 相比"多开浏览器进程"的优势是什么？什么场景下体现最明显？
4. `page.route()` 除了反爬还能做什么？（提示：mock 测试环境接口）
5. 对一个数据在 `window.__APP_DATA__` 里的页面，用 `page.evaluate` 取数据和解析 DOM 各有什么优缺点？

---

## 📚 延伸阅读

- 官方文档：https://playwright.dev/python/
- 明天预告：Day 131 爬虫策略 -- 去重、断点续爬、限速，把"能爬"变成"爬得稳、爬得久"。
