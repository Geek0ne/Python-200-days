# Day 129 - 动态渲染（Selenium）

> 🎯 **今日目标**：理解 JavaScript 渲染页面的本质，掌握 Selenium WebDriver 的工作原理、元素定位与等待策略、无头浏览器，能抓取 requests 抓不到的"动态页面"。

---

## 📋 概念总览

### 为什么 requests + Scrapy 会"失灵"？

```bash
# 你用 requests 抓某电商搜索页
response = requests.get(url)
print(response.text)   # 里面根本没有商品数据！只有一堆 <div id="root"></div> 和 <script>
```

**原因**：现代网站的很多数据不是写在初始 HTML 里的，而是由**浏览器执行 JavaScript 后**再"画"到页面上的。流程对比：

```
静态页面：
  服务器返回完整 HTML（数据已在标签里） → requests 能直接解析 ✅

动态渲染页面（SPA / Ajax）：
  服务器返回空壳 HTML + JS 代码
      → 浏览器下载并执行 JS
      → JS 发送 Ajax/XHR 请求拿 JSON 数据
      → JS 把 JSON 填进 DOM（页面才"长出"内容）
  requests 不执行 JS → 拿到的永远是空壳 ❌
```

### 三种解决方案（按成本从低到高）

| 方案 | 原理 | 适用 |
|---|---|---|
| ① 逆向 Ajax 接口 | 直接请求 JS 调用的 JSON API | 接口无复杂加密时最优 |
| ② Selenium | 真浏览器执行 JS | 接口加密难逆向、交互复杂 |
| ③ Playwright | 更现代的浏览器自动化（明天讲） | 同上，体验更好 |

今天的主角 Selenium 属于②：**"打不过 JS，就自己开个真浏览器"**。

---

## 🏗️ 一、Selenium WebDriver 原理

### 1.1 架构：三件套

```
你的 Python 代码
      │ (HTTP/JSON Wire 协议 / W3C 协议)
      ▼
ChromeDriver（一个本地"翻译官"程序，监听端口）
      │ (DevTools/CDP 协议)
      ▼
Chrome 浏览器（真正干活：加载页面、执行 JS、点击）
```

**为什么要中间的 Driver？** 浏览器厂商不提供 Python API，但都提供了调试协议。Driver 把"Python 的 `driver.get(url)`"翻译成"浏览器：请导航到 url"，并把浏览器的执行结果翻译回 JSON 给 Python。这叫 **W3C WebDriver 协议**，是一套统一标准--所以换浏览器只需换 Driver，Python 代码几乎不变。

### 1.2 安装

```bash
pip install selenium
# Selenium 4.6+ 自带 Selenium Manager，会自动下载匹配的 ChromeDriver！
# （老版本需要手动下 chromedriver 放到 PATH，经常版本对不上，是经典大坑）
```

```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

opts = Options()
opts.add_argument("--headless=new")   # 无头模式：不弹出窗口（见第四节）
driver = webdriver.Chrome(options=opts)
```

---

## 🎯 二、元素定位（八种方式）

```python
from selenium.webdriver.common.by import By

driver.find_element(By.ID, "username")                    # ① ID（首选，唯一且最快）
driver.find_element(By.CLASS_NAME, "price")               # ② class
driver.find_element(By.TAG_NAME, "h1")                    # ③ 标签名
driver.find_element(By.NAME, "q")                         # ④ name 属性（表单常用）
driver.find_element(By.LINK_TEXT, "下一页")                # ⑤ 完整链接文字
driver.find_element(By.PARTIAL_LINK_TEXT, "下一")          # ⑥ 部分链接文字
driver.find_element(By.CSS_SELECTOR, "div.item > a.title")# ⑦ CSS 选择器（万能）
driver.find_element(By.XPATH, "//div[@class='item']/a")   # ⑧ XPath（最强，可按文本找）
```

**选择优先级（经验法则）**：
1. 有唯一 `id` 就用 ID
2. 没有 id 用 CSS（简洁、性能好）
3. 需要"按文本匹配/找父节点"才用 XPath：`//a[contains(text(), "登录")]`
4. 多个匹配时 `find_elements`（复数）返回列表，不会抛异常

**经典报错**：`NoSuchElementException` —— 90% 的情况不是选择器写错，而是**元素还没渲染出来**。这引出最重要的一节：

---

## ⏳ 三、等待策略（Selenium 的灵魂）

### 3.1 为什么"硬等"是菜鸟写法

```python
driver.get(url)
time.sleep(5)   # ❌ 菜鸟：拍脑袋等 5 秒
elem = driver.find_element(By.ID, "content")
```

问题：网络快时白等 5 秒（慢）；网络慢时 5 秒还不够（崩）。**正确思路：等到条件满足为止，最多等 X 秒。**

### 3.2 隐式等待（全局兜底）

```python
driver.implicitly_wait(10)   # 所有 find_element 最多等 10 秒元素出现
```

- 优点：一行搞定全局。
- 缺点：只能等"元素存在"，等不了"可点击""消失""文本变化"等复杂条件。**与显式等待混用会互相干扰，别一起用！**

### 3.3 显式等待（生产必用）

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

wait = WebDriverWait(driver, timeout=10, poll_frequency=0.5)

# 等元素"可见且可点击"再点
btn = wait.until(EC.element_to_be_clickable((By.ID, "submit")))
btn.click()

# 等 Ajax 加载的列表出现
items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.product")))

# 等 loading 遮罩消失（"负向等待"）
wait.until(EC.invisibility_of_element_located((By.ID, "loading-mask")))
```

**常用 EC 条件速查**：

| 条件 | 等到什么时候 |
|---|---|
| `presence_of_element_located` | 元素在 DOM 里（不一定可见） |
| `visibility_of_element_located` | 元素可见（有尺寸、非 hidden） |
| `element_to_be_clickable` | 可见 + 可点击 |
| `invisibility_of_element_located` | 元素消失（等 loading 消失） |
| `text_to_be_present_in_element` | 元素里出现指定文本 |
| `staleness_of` | 旧元素失效（页面刷新后） |

### 3.4 自定义等待条件

```python
wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
# JS 层面确认页面加载完成，比 sleep 靠谱得多
```

---

## 👻 四、无头浏览器（Headless）

"无头"= 没有图形界面，页面在内存里渲染。**功能和普通模式一致，只是你看不见窗口。**

```python
opts = Options()
opts.add_argument("--headless=new")            # 新版无头模式（Chrome 109+）
opts.add_argument("--disable-gpu")             # 部分系统需要
opts.add_argument("--window-size=1920,1080")   # ⚠️ 无头默认窗口很小，
                                               # 响应式网站可能渲染成"手机版"布局！
opts.add_argument("--no-sandbox")              # Linux root 下常见坑
driver = webdriver.Chrome(options=opts)
```

**无头模式的坑**：
1. 默认视口小 → 响应式网站元素位置/布局不同，可能定位不到 → 固定 `--window-size`。
2. 有些网站检测 `navigator.webdriver == true` 识别自动化 → 可注入 JS 修改（见实战代码）。
3. 截图排查：`driver.save_screenshot("debug.png")` 无头也能用！

---

## 🖱️ 五、交互操作

```python
elem.click()                       # 点击
elem.send_keys("关键词")             # 输入框打字
elem.clear()                       # 清空输入框
from selenium.webdriver.common.keys import Keys
elem.send_keys(Keys.ENTER)         # 回车
driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")  # 滚到底（触发懒加载）
driver.switch_to.frame("iframe_name")   # ⚠️ 进 iframe 后才能定位里面的元素！
driver.switch_to.default_content()      # 用完切回主文档
ActionChains(driver).move_to_element(hover_elem).perform()  # 悬停菜单
```

**iframe 大坑**：元素明明在 F12 里看得到，就是定位不到？检查它是否在 `<iframe>` 里。iframe 是独立文档，必须先 `switch_to.frame()` 切进去。

---

## 🔍 六、怎么找到真实数据接口？（逆向思路）

开浏览器 F12 → Network → XHR/Fetch，刷新页面，观察哪个请求返回了你要的 JSON。如果能直接 `requests.get` 那个接口（参数不加密），就根本不需要 Selenium--速度差 10 倍以上。

**决策树**：

```
要抓动态页面
  ├─ F12 能找到干净的 JSON 接口？→ requests 直接调（最优）
  ├─ 接口有加密参数/签名，逆向成本高？→ Selenium/Playwright
  └─ 需要登录+交互+JS 挑战？→ 浏览器自动化
```

---

## 💻 七、实战：抓取 JS 渲染页面

完整代码见 `code/03-practical-selenium.py`：用 Selenium 爬取 quotes.toscrape.com 的 JS 渲染版（quotes.toscrape.com/js/），含翻页、滚动触发、无头模式、反检测，全部逐行中文注释。

```python
# 核心骨架
driver.get("http://quotes.toscrape.com/js/")
wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "quote")))
for q in driver.find_elements(By.CLASS_NAME, "quote"):
    text = q.find_element(By.CLASS_NAME, "text").text
driver.find_element(By.CLASS_NAME, "next").click()  # 翻页
```

---

## ❓ 思考题

1. requests 抓到的页面里没有商品数据，请描述这中间浏览器做了什么，数据到底从哪来？
2. `time.sleep(5)` 和 `WebDriverWait(...).until(...)` 的本质区别是什么？各自的问题/优势？
3. 隐式等待和显式等待混用会发生什么？为什么？
4. 元素在 F12 里明明存在，`find_element` 却报 `NoSuchElementException`，列出至少 3 种可能原因。
5. 什么情况下应放弃 Selenium、改用 requests 直接调接口？怎么判断接口"干净不干净"？

---

## 📚 延伸阅读

- Selenium 文档：https://www.selenium.dev/documentation/
- 明天预告：Day 130 Playwright -- 微软出品的新一代爬虫利器，自动等待开箱即用。
