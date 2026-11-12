# Day 127 — BeautifulSoup / lxml 解析

> 🎯 **今日目标**：掌握 HTML 解析的两大库 — BeautifulSoup 和 lxml，能高效提取网页中的结构化数据。

---

## 📋 概念总览

### 为什么需要 HTML 解析？

爬虫获取到的网页是 HTML 源码，我们需要从中提取有用的数据。HTML 解析库就是用来做这件事的工具。

| 库 | 特点 | 适用场景 |
|---|------|---------|
| BeautifulSoup | API 简洁，容错性好 | 小规模爬虫、快速开发 |
| lxml | 性能极高，支持 XPath | 大规模爬虫、性能敏感 |
| html.parser | Python 内置，无需安装 | 简单场景、无第三方依赖 |

---

## 🏗️ BeautifulSoup 基础

### 安装与导入

```bash
pip install beautifulsoup4 lxml
```

```python
from bs4 import BeautifulSoup

# 解析 HTML
html = """
<html>
<head><title>示例页面</title></head>
<body>
    <div class="content">
        <h1>欢迎</h1>
        <p class="desc">这是一个<b>示例</b>页面</p>
        <ul>
            <li><a href="/page1">页面1</a></li>
            <li><a href="/page2">页面2</a></li>
        </ul>
    </div>
</body>
</html>
"""

soup = BeautifulSoup(html, "lxml")  # 使用 lxml 解析器
# 或
soup = BeautifulSoup(html, "html.parser")  # 使用内置解析器
```

### 解析器对比

```
┌──────────────────────────────────────────────────────────────┐
│                    解析器对比                                  │
├──────────────┬──────────────┬──────────────┬─────────────────┤
│     特性     │   lxml       │ html.parser  │  html5lib       │
├──────────────┼──────────────┼──────────────┼─────────────────┤
│   速度       │   ⚡ 最快    │   ⚡ 较快     │   🐢 最慢       │
│   容错性     │   ⭐⭐      │   ⭐⭐⭐     │   ⭐⭐⭐⭐      │
│   依赖       │   需安装     │   Python内置  │   需安装        │
│   HTML5支持  │   ✅         │   ❌         │   ✅            │
│   推荐场景   │   生产环境   │   简单场景    │   脏HTML处理    │
└──────────────┴──────────────┴──────────────┴─────────────────┘
```

---

## 🔍 元素查找方法

### find() 和 find_all()

```python
# find() — 返回第一个匹配的元素
title = soup.find("title")
print(title.text)  # "示例页面"

# find_all() — 返回所有匹配的元素
links = soup.find_all("a")
for link in links:
    print(link["href"], link.text)

# 按 CSS 类查找
desc = soup.find("p", class_="desc")
print(desc.text)

# 按属性查找
div = soup.find("div", attrs={"class": "content"})

# 按 ID 查找
element = soup.find(id="main")

# 组合查找
result = soup.find("div", class_="content").find("h1")
```

### CSS 选择器

```python
# 使用 CSS 选择器（更强大）
soup.select("h1")                    # 标签选择器
soup.select(".desc")                 # 类选择器
soup.select("#main")                 # ID 选择器
soup.select("div.content")           # 组合选择器
soup.select("ul > li > a")           # 子元素选择器
soup.select("a[href^='/page']")      # 属性前缀匹配
soup.select("a[href$='1']")          # 属性后缀匹配
soup.select("p.desc, h1")            # 多选择器
soup.select_one("h1")                # 返回第一个匹配
```

---

## 🚀 lxml 与 XPath

### XPath 语法速查

```python
from lxml import html

tree = html.fromstring(html_content)

# 基础 XPath
tree.xpath("//h1")                    # 所有 h1 元素
tree.xpath("//a/@href")              # 所有 a 标签的 href
tree.xpath("//div[@class='content']") # 按属性查找
tree.xpath("//li/a/text()")          # 提取文本

# 路径表达式
tree.xpath("//div/p[1]")             # 第一个 p 元素
tree.xpath("//div/p[last()]")        # 最后一个 p 元素
tree.xpath("//div/p[position()<3]")   # 前两个 p 元素
tree.xpath("//div/p[contains(@class,'desc')]")  # 模糊匹配

# 组合查询
tree.xpath("//h1 | //h2")            # h1 或 h2
tree.xpath("//div//a")               # div 下的所有 a（任意层级）
tree.xpath("//div/a")                # div 下的直接子 a
```

### XPath vs CSS 选择器

| 操作 | CSS 选择器 | XPath |
|------|-----------|-------|
| 所有链接 | `a` | `//a` |
| 按类查找 | `.classname` | `//*[@class="classname"]` |
| 子元素 | `div > p` | `//div/p` |
| 后代元素 | `div p` | `//div//p` |
| 属性选择 | `[href]` | `[@href]` |
| 文本内容 | N/A | `//a/text()` |
| 索引选择 | `li:nth-child(2)` | `//li[2]` |
| 父元素 | N/A | `//a/..` |

---

## 📊 实战：数据提取流程

```
┌──────────────────────────────────────────────────────────────┐
│                    数据提取流程                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ 获取HTML  │───▶│ 解析HTML  │───▶│ 查找元素  │               │
│  │ requests │    │ BS4/lxml │    │ find/xpath│               │
│  └──────────┘    └──────────┘    └──────────┘               │
│                                      │                       │
│                                      ▼                       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐               │
│  │ 存储数据  │◀───│ 清洗数据  │◀───│ 提取属性  │               │
│  │ CSV/JSON │    │ 去重/格式 │    │ text/attr│               │
│  └──────────┘    └──────────┘    └──────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 💡 最佳实践

### 1. 选择解析器

```python
# 推荐：lxml（速度快）
soup = BeautifulSoup(html, "lxml")

# 容错：html5lib（处理脏 HTML）
soup = BeautifulSoup(html, "html5lib")

# XPath：直接使用 lxml
tree = html.fromstring(html)
```

### 2. 处理编码

```python
# 自动检测编码
resp = requests.get(url)
resp.encoding = resp.apparent_encoding  # 自动检测
soup = BeautifulSoup(resp.text, "lxml")

# 指定编码
soup = BeautifulSoup(html.encode("utf-8"), "lxml")
```

### 3. 避免常见错误

```python
# ❌ 错误：直接访问可能不存在的属性
link = soup.find("a")
href = link["href"]  # 如果 link 为 None 会报错

# ✅ 正确：先检查是否存在
link = soup.find("a")
if link:
    href = link.get("href", "")

# ❌ 错误：find_all 返回空列表时直接索引
links = soup.find_all("a", class_="special")
first = links[0]  # 空列表会 IndexError

# ✅ 正确：使用 find 或检查长度
link = soup.find("a", class_="special")
if link:
    href = link["href"]
```

---

## 🤔 思考题

1. **性能对比**：在处理 10MB 的 HTML 文件时，lxml 比 BeautifulSoup 快多少？为什么？

**参考答案**

量级上，**纯 lxml（C 解析器 + XPath）通常比 BeautifulSoup + html.parser 快约 5~10 倍**；但 BeautifulSoup 即使改用 lxml 做后端，提速也有限。原因：

- **lxml 底层是 C 库 libxml2**，解析在 C 层完成，极快。
- **html.parser 是纯 Python** 实现，解析慢。
- **bs4 的开销主要在 Python 层**：它要把解析树包装成 Python 对象，`find_all` 遍历也在 Python 层，所以即便解析快了，遍历仍拖后腿。

因此"快多少"取决于用法：纯 lxml + XPath 最快，bs4 + lxml 次之，bs4 + html.parser 最慢。下面本地生成约 10MB HTML 实测（需先 `pip install beautifulsoup4 lxml`）：

```python
import time
from bs4 import BeautifulSoup
from lxml import html as lxml_html

# 构造约 10MB 的 HTML：12 万个商品卡片
card = '<div class="item"><a href="/p/1">商品标题</a><span class="price">99.00</span></div>\n'
page = "<html><body>" + card * 120_000 + "</body></html>"
print(f"HTML 大小: {len(page.encode('utf-8')) / 1024 / 1024:.1f} MB")

def bench(name, parse):
    start = time.perf_counter()
    n = parse(page)          # 解析并顺便提取所有链接，模拟真实工作
    cost = time.perf_counter() - start
    print(f"{name:28s} 耗时 {cost:6.2f}s  提取链接 {n} 个")
    return cost

t1 = bench("BeautifulSoup(html.parser)",
           lambda h: len(BeautifulSoup(h, "html.parser").find_all("a")))
t2 = bench("BeautifulSoup(lxml)",
           lambda h: len(BeautifulSoup(h, "lxml").find_all("a")))
t3 = bench("lxml.html.fromstring + xpath",
           lambda h: len(lxml_html.fromstring(h).xpath("//a/@href")))
print(f"加速比: bs4+lxml 是 bs4+html.parser 的 {t1/t2:.1f} 倍；纯 lxml 是 {t1/t3:.1f} 倍")
```

本机一次实测输出（数字随机器和文档结构变化，量级供参考）：

```
HTML 大小: 10.1 MB
BeautifulSoup(html.parser)   耗时   4.58s  提取链接 120000 个
BeautifulSoup(lxml)          耗时   3.74s  提取链接 120000 个
lxml.html.fromstring + xpath 耗时   0.50s  提取链接 120000 个
加速比: bs4+lxml 是 bs4+html.parser 的 1.2 倍；纯 lxml 是 9.1 倍
```

可见纯 lxml + XPath 比 bs4 + html.parser 快约 9 倍，而 bs4 换 lxml 后端只快 1.2 倍——瓶颈在 Python 层的对象封装与遍历。

2. **XPath 独有能力**：XPath 有哪些 BeautifulSoup 无法轻松实现的功能？（提示：父元素选择、文本节点）

**参考答案**

XPath 更轻松/独有的能力：

- **轴导航**：`parent::`、`ancestor::`、`following-sibling::` 等反向/横向找节点（传统 CSS 没有父选择器）。
- **文本节点**：`text()` 精确取直接文本（不含子标签文字）、`contains(text(), ...)` 按文本内容匹配元素。
- **位置函数**：`last()`、`position()` 选最后一个/第 N 个。
- **属性与逻辑组合**：`@attr` 取属性、`and`/`or` 组合条件。

bs4 虽能用 `.parent`、`.find(text=True)` 等 Python 代码实现部分功能，但 XPath 一条表达式就搞定，更系统。下面离线演示（需先 `pip install lxml`）：

```python
from lxml import html

doc = html.fromstring("""
<html><body>
  <div class="box">
    <p>第一段</p>
    <p class="target">目标段落<b>加粗子元素</b></p>
    <p>第三段</p>
  </div>
</body></html>
""")

# ① 父元素选择：从 .target 反向找到它的父 div（CSS 选择器做不到）
parent = doc.xpath("//p[@class='target']/parent::div")[0]
print("① 父元素 class =", parent.get("class"))

# ② 只取"直接文本节点"，不含子标签 <b> 里的文字
direct_text = doc.xpath("//p[@class='target']/text()")
print("② 直接文本节点 =", direct_text)   # 只有 '目标段落'，不含 '加粗子元素'

# ③ 按文本内容匹配元素
by_text = doc.xpath("//p[contains(text(), '第三')]")
print("③ 按文本匹配到 =", by_text[0].text)

# ④ 取某个元素后面的兄弟节点
following = doc.xpath("//p[@class='target']/following-sibling::p")
print("④ 后面的兄弟 p 数量 =", len(following))
```

预期输出：

```
① 父元素 class = box
② 直接文本节点 = ['目标段落']
③ 按文本匹配到 = 第三段
④ 后面的兄弟 p 数量 = 1
```

💡 提示：新版 bs4 的 soupsieve 引擎已支持 `:has()` 等部分能力，但 XPath 的轴体系仍更完整、表达力更强。

3. **动态内容**：如果网页内容是通过 JavaScript 动态加载的，BeautifulSoup 能直接提取吗？应该用什么工具？

**参考答案**

不能。BeautifulSoup 只解析"你拿到的 HTML 字符串"，它**不执行 JavaScript**。如果数据是 JS 运行后才填进 DOM 的，bs4 拿到的只是空壳。

应改用：

- **优先逆向 Ajax 接口**：F12 找到 JS 调用的 JSON API，直接用 requests 请求（最快、最稳）。
- **浏览器自动化**：用 Selenium / Playwright 驱动真浏览器执行 JS，再取渲染后的 HTML 或元素。

小例子：一个 SPA 页面，bs4 只看到 `<div id="root"></div>`；要用 Playwright 渲染后，里面才有真实内容。

4. **选择器优化**：`soup.select("div > p > a")` 和 `soup.select("div p a")` 有什么区别？哪种更快？

**参考答案**

区别在层级关系：

- **`div > p > a`**（子代选择器）：要求 a 的父是 p、p 的父是 div，**严格逐层直接父子**。
- **`div p a`**（后代选择器）：只要 a 在 div 内、p 在 div 内即可，中间可隔**任意层级**，匹配范围更大。

速度上两者通常在同一量级，选择依据应是**语义正确性**；在超大文档上更严格的选择器候选更少、往往略快，但差异远小于"解析器选择"带来的影响。下面离线演示（需先 `pip install beautifulsoup4`）：

```python
from bs4 import BeautifulSoup

doc = BeautifulSoup("""
<div>
  <p><a>直接孙链接</a></p>
  <section><p><a>深层嵌套链接</a></p></section>
</div>
""", "html.parser")

# div > p > a：要求 a 的父是 p、p 的父是 div（严格逐层）
strict = doc.select("div > p > a")
# div p a：只要 a 在 div 内部、p 在 div 内部即可（任意层级）
loose = doc.select("div p a")

print("div > p > a 命中:", [a.text for a in strict])
print("div p a   命中:", [a.text for a in loose])
```

预期输出：

```
div > p > a 命中: ['直接孙链接']
div p a   命中: ['直接孙链接', '深层嵌套链接']
```

第二个链接的 p 外面隔了 `<section>`，不满足严格父子关系，所以只被后代选择器命中。

5. **反爬虫对抗**：如果网站检测到你频繁解析同一个页面的不同部分，应该如何优化？

**参考答案**

核心思路是"减少重复请求与重复解析"，而不是高频硬撞：

- **一次下载、一次解析、复用树**：把 HTML 缓存下来，解析成 soup/tree 后，所有字段都从同一棵树提取，别为每个部分重新请求或重新解析。
- **批量提取**：一次性 `select` 出所有需要的节点，避免多次遍历。
- **本地缓存 HTML**（文件/Redis）：调试时离线反复解析，不再打扰服务器。
- **控制请求频率**：加延迟、限并发，避免触发反爬。
- **用 lxml** 提升解析速度。

⚠️ 合规提示：遵守 robots.txt 与频率限制，"优化"应是减少重复请求、降低对方负担，而非绕过检测高频抓取。
