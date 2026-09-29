"""
Day 127 - BeautifulSoup / lxml 解析：进阶用法
02-advanced-parsing.py

演示高级解析技巧：容错处理、性能优化、复杂场景
"""

from bs4 import BeautifulSoup, Comment
from lxml import html
import re
import time
from typing import List, Dict, Optional


# ============================================================
# 1. 容错处理
# ============================================================

def demo_fault_tolerance():
    """演示 BeautifulSoup 的容错处理"""
    print("=" * 60)
    print("🔧 1. 容错处理")
    print("=" * 60)

    # 脏 HTML（未闭合标签、嵌套错误）
    dirty_html = """
    <html>
    <body>
        <div class="content">
            <p>段落1
            <p>段落2
            <p>段落3</p>
            <div>
                <span>嵌套的<span>文本</span>
            </div>
        </div>
    </body>
    """

    # html.parser 会自动修复
    soup = BeautifulSoup(dirty_html, "html.parser")
    paragraphs = soup.find_all("p")
    print(f"\n--- html.parser 容错 ---")
    print(f"找到 {len(paragraphs)} 个 <p> 标签")
    for i, p in enumerate(paragraphs):
        print(f"  [{i+1}] {p.text}")

    # lxml 更强大
    soup_lxml = BeautifulSoup(dirty_html, "lxml")
    paragraphs_lxml = soup_lxml.find_all("p")
    print(f"\n--- lxml 容错 ---")
    print(f"找到 {len(paragraphs_lxml)} 个 <p> 标签")


# ============================================================
# 2. 复杂选择器
# ============================================================

def demo_complex_selectors():
    """演示复杂选择器"""
    print("\n" + "=" * 60)
    print("🔧 2. 复杂选择器")
    print("=" * 60)

    html_content = """
    <div class="article">
        <h1 class="title">文章标题</h1>
        <div class="meta">
            <span class="author">作者: 张三</span>
            <span class="date">2024-01-15</span>
            <span class="category">分类: 技术</span>
        </div>
        <div class="content">
            <p>第一段内容</p>
            <p>第二段内容</p>
            <blockquote>引用内容</blockquote>
            <p>第三段内容</p>
            <img src="image1.jpg" alt="图片1">
            <img src="image2.jpg" alt="图片2">
        </div>
        <div class="tags">
            <a href="/tag/python" class="tag">Python</a>
            <a href="/tag/web" class="tag">Web</a>
            <a href="/tag/crawler" class="tag">爬虫</a>
        </div>
    </div>
    """

    soup = BeautifulSoup(html_content, "lxml")

    # 伪类选择器
    print("\n--- 伪类选择器 ---")
    first_tag = soup.select_one(".tags .tag:first-child")
    if first_tag:
        print(f"  第一个标签: {first_tag.text}")

    last_tag = soup.select_one(".tags .tag:last-child")
    if last_tag:
        print(f"  最后一个标签: {last_tag.text}")

    # 属性选择器
    print("\n--- 属性选择器 ---")
    imgs = soup.select("img[alt^='图片']")
    for img in imgs:
        print(f"  图片: {img.get('alt')} ({img.get('src')})")

    # 否定选择器
    print("\n--- 否定选择器 ---")
    all_tags = soup.select(".tags a:not(.tag)")
    print(f"  非 .tag 的链接: {len(all_tags)}")

    # 相邻兄弟选择器
    print("\n--- 相邻兄弟选择器 ---")
    blockquote = soup.select_one("blockquote")
    if blockquote:
        next_p = blockquote.find_next_sibling("p")
        if next_p:
            print(f"  blockquote 后的段落: {next_p.text}")


# ============================================================
# 3. 数据清洗与提取
# ============================================================

def demo_data_cleaning():
    """演示数据清洗"""
    print("\n" + "=" * 60)
    print("🔧 3. 数据清洗与提取")
    print("=" * 60)

    html_content = """
    <div class="article">
        <h1>  文章标题  </h1>
        <div class="content">
            <p>这是第一段。
            这是第二句话。</p>
            <p>这是第二段。
            <a href="/link1">链接1</a>
            <a href="/link2">链接2</a></p>
            <!-- 这是注释 -->
            <script>var x = 1;</script>
            <style>.hidden { display: none; }</style>
            <p>这是第三段。</p>
        </div>
    </div>
    """

    soup = BeautifulSoup(html_content, "lxml")

    # 清理脚本和样式
    print("\n--- 清理脚本和样式 ---")
    for script in soup(["script", "style"]):
        script.decompose()  # 完全移除

    # 提取文本
    print("\n--- 提取干净文本 ---")
    article = soup.find("div", class_="article")
    if article:
        # get_text() 自动处理空白
        text = article.get_text(separator="\n", strip=True)
        print(f"  文章内容:\n{text}")

    # 清理注释
    print("\n--- 清理注释 ---")
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    print(f"  已移除 {len(comments)} 个注释")

    # 提取链接
    print("\n--- 提取链接 ---")
    links = soup.find_all("a", href=True)
    for link in links:
        text = link.get_text(strip=True)
        href = link.get("href")
        print(f"  {text}: {href}")


# ============================================================
# 4. 性能对比
# ============================================================

def demo_performance():
    """演示解析器性能对比"""
    print("\n" + "=" * 60)
    print("🔧 4. 性能对比")
    print("=" * 60)

    # 生成大 HTML
    items = []
    for i in range(1000):
        items.append(f"""
        <div class="item" data-id="{i}">
            <h3>Item {i}</h3>
            <p class="desc">Description for item {i}</p>
            <span class="price">${i * 9.99:.2f}</span>
        </div>
        """)

    large_html = f"""
    <html>
    <body>
        <div class="list">
            {"".join(items)}
        </div>
    </body>
    </html>
    """

    # BeautifulSoup html.parser
    start = time.time()
    soup = BeautifulSoup(large_html, "html.parser")
    items_found = soup.find_all("div", class_="item")
    bs4_time = time.time() - start
    print(f"\n  BeautifulSoup (html.parser): {bs4_time:.3f}s, 找到 {len(items_found)} 个元素")

    # BeautifulSoup lxml
    start = time.time()
    soup = BeautifulSoup(large_html, "lxml")
    items_found = soup.find_all("div", class_="item")
    bs4_lxml_time = time.time() - start
    print(f"  BeautifulSoup (lxml):        {bs4_lxml_time:.3f}s, 找到 {len(items_found)} 个元素")

    # 纯 lxml XPath
    start = time.time()
    tree = html.fromstring(large_html)
    items_found = tree.xpath("//div[@class='item']")
    lxml_time = time.time() - start
    print(f"  lxml (XPath):                {lxml_time:.3f}s, 找到 {len(items_found)} 个元素")

    # 速度对比
    if lxml_time > 0:
        print(f"\n  lxml 比 BS4(html.parser) 快 {bs4_time/lxml_time:.1f}x")
        print(f"  lxml 比 BS4(lxml) 快 {bs4_lxml_time/lxml_time:.1f}x")


# ============================================================
# 5. 正则表达式配合
# ============================================================

def demo_regex配合():
    """演示正则表达式配合使用"""
    print("\n" + "=" * 60)
    print("🔧 5. 正则表达式配合")
    print("=" * 60)

    html_content = """
    <div class="prices">
        <span>¥199.00</span>
        <span>$29.99</span>
        <span>€25.50</span>
        <span>无价格</span>
        <span>¥388.00</span>
    </div>
    """

    soup = BeautifulSoup(html_content, "lxml")

    # 使用正则匹配价格
    print("\n--- 正则匹配价格 ---")
    price_pattern = re.compile(r'[¥$€]\d+(\.\d+)?')
    spans = soup.find_all("span", string=price_pattern)
    for span in spans:
        print(f"  价格: {span.text}")

    # 使用正则匹配属性
    print("\n--- 正则匹配 class ---")
    html2 = """
    <div class="item-1">Item 1</div>
    <div class="item-2">Item 2</div>
    <div class="item-3">Item 3</div>
    <div class="other">Other</div>
    """
    soup2 = BeautifulSoup(html2, "lxml")
    items = soup2.find_all("div", class_=re.compile(r"^item-\d+$"))
    for item in items:
        print(f"  {item.get('class')}: {item.text}")


# ============================================================
# 6. 构建结构化数据
# ============================================================

def demo_structured_extraction():
    """演示结构化数据提取"""
    print("\n" + "=" * 60)
    print("🔧 6. 构建结构化数据")
    print("=" * 60)

    html_content = """
    <table class="data-table">
        <thead>
            <tr>
                <th>姓名</th>
                <th>年龄</th>
                <th>城市</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>张三</td>
                <td>28</td>
                <td>北京</td>
            </tr>
            <tr>
                <td>李四</td>
                <td>35</td>
                <td>上海</td>
            </tr>
            <tr>
                <td>王五</td>
                <td>42</td>
                <td>广州</td>
            </tr>
        </tbody>
    </table>
    """

    soup = BeautifulSoup(html_content, "lxml")

    # 提取表头
    headers = [th.text for th in soup.select("thead th")]
    print(f"  表头: {headers}")

    # 提取数据行
    print("\n--- 提取表格数据 ---")
    rows = soup.select("tbody tr")
    data = []
    for row in rows:
        cells = [td.text for td in row.find_all("td")]
        row_dict = dict(zip(headers, cells))
        data.append(row_dict)
        print(f"  {row_dict}")

    # 提取统计信息
    ages = [int(row["年龄"]) for row in data]
    print(f"\n  平均年龄: {sum(ages) / len(ages):.1f}")
    print(f"  最大年龄: {max(ages)}")
    print(f"  最小年龄: {min(ages)}")


# ============================================================
# 7. 主流程
# ============================================================

def main():
    print("🚀 Day 127 - BeautifulSoup / lxml 解析：进阶用法\n")

    demo_fault_tolerance()
    demo_complex_selectors()
    demo_data_cleaning()
    demo_performance()
    demo_regex配合()
    demo_structured_extraction()

    print("\n" + "=" * 60)
    print("✅ 进阶用法演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
