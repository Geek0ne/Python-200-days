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

2. **XPath 独有能力**：XPath 有哪些 BeautifulSoup 无法轻松实现的功能？（提示：父元素选择、文本节点）

3. **动态内容**：如果网页内容是通过 JavaScript 动态加载的，BeautifulSoup 能直接提取吗？应该用什么工具？

4. **选择器优化**：`soup.select("div > p > a")` 和 `soup.select("div p a")` 有什么区别？哪种更快？

5. **反爬虫对抗**：如果网站检测到你频繁解析同一个页面的不同部分，应该如何优化？
