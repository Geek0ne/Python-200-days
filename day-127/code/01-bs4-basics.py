"""
Day 127 - BeautifulSoup / lxml 解析：基础用法
01-bs4-basics.py

演示 BeautifulSoup 的核心功能：查找、提取、遍历
"""

from bs4 import BeautifulSoup
from lxml import html
import re


# ============================================================
# 示例 HTML
# ============================================================

SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>商品列表 - 示例电商网站</title>
</head>
<body>
    <header class="main-header">
        <nav>
            <a href="/" class="logo">首页</a>
            <ul class="nav-links">
                <li><a href="/category/electronics">电子产品</a></li>
                <li><a href="/category/clothing">服装</a></li>
                <li><a href="/category/books">图书</a></li>
            </ul>
        </nav>
    </header>

    <main class="content">
        <h1>热门商品</h1>

        <div class="product-list">
            <div class="product-card" data-id="1">
                <h2 class="product-name">Python编程入门</h2>
                <span class="price" data-currency="CNY">¥89.00</span>
                <span class="rating">⭐ 4.8</span>
                <p class="description">适合初学者的Python教程</p>
                <a href="/product/1" class="detail-link">查看详情</a>
            </div>

            <div class="product-card" data-id="2">
                <h2 class="product-name">机器学习实战</h2>
                <span class="price" data-currency="CNY">¥128.00</span>
                <span class="rating">⭐ 4.9</span>
                <p class="description">深入浅出的机器学习指南</p>
                <a href="/product/2" class="detail-link">查看详情</a>
            </div>

            <div class="product-card" data-id="3">
                <h2 class="product-name">数据分析基础</h2>
                <span class="price" data-currency="CNY">¥68.00</span>
                <span class="rating">⭐ 4.5</span>
                <p class="description">Pandas和NumPy入门</p>
                <a href="/product/3" class="detail-link">查看详情</a>
            </div>
        </div>

        <div class="pagination">
            <a href="?page=1" class="active">1</a>
            <a href="?page=2">2</a>
            <a href="?page=3">3</a>
            <span class="ellipsis">...</span>
            <a href="?page=10">10</a>
        </div>
    </main>

    <footer class="main-footer">
        <p>© 2024 示例电商网站</p>
        <div class="contact">
            <p>联系邮箱: contact@example.com</p>
            <p>电话: 400-123-4567</p>
        </div>
    </footer>
</body>
</html>
"""


# ============================================================
# 1. 解析 HTML
# ============================================================

def demo_parse():
    """演示 HTML 解析"""
    print("=" * 60)
    print("🔧 1. 解析 HTML")
    print("=" * 60)

    # 使用 lxml 解析器
    soup = BeautifulSoup(SAMPLE_HTML, "lxml")
    print(f"解析器: {soup.parser_class}")

    # 获取标题
    title = soup.find("title")
    print(f"标题: {title.text}")

    # 获取页面编码
    meta = soup.find("meta", attrs={"charset": "UTF-8"})
    print(f"编码: {meta.get('charset', 'N/A')}")


# ============================================================
# 2. 查找元素
# ============================================================

def demo_find_elements():
    """演示元素查找"""
    print("\n" + "=" * 60)
    print("🔧 2. 查找元素")
    print("=" * 60)

    soup = BeautifulSoup(SAMPLE_HTML, "lxml")

    # find() - 查找单个元素
    print("\n--- find() 查找单个元素 ---")
    h1 = soup.find("h1")
    print(f"h1 文本: {h1.text}")

    # find_all() - 查找所有元素
    print("\n--- find_all() 查找所有元素 ---")
    products = soup.find_all("div", class_="product-card")
    print(f"商品数量: {len(products)}")
    for p in products:
        name = p.find("h2", class_="product-name").text
        price = p.find("span", class_="price").text
        print(f"  - {name}: {price}")

    # 按属性查找
    print("\n--- 按属性查找 ---")
    links = soup.find_all("a", href=True)
    for link in links:
        print(f"  {link.get('href')}: {link.text}")


# ============================================================
# 3. CSS 选择器
# ============================================================

def demo_css_selector():
    """演示 CSS 选择器"""
    print("\n" + "=" * 60)
    print("🔧 3. CSS 选择器")
    print("=" * 60)

    soup = BeautifulSoup(SAMPLE_HTML, "lxml")

    # 标签选择器
    print("\n--- 标签选择器 ---")
    all_links = soup.select("a")
    print(f"所有链接数量: {len(all_links)}")

    # 类选择器
    print("\n--- 类选择器 ---")
    nav_links = soup.select(".nav-links a")
    for link in nav_links:
        print(f"  导航链接: {link.text} → {link.get('href')}")

    # 组合选择器
    print("\n--- 组合选择器 ---")
    prices = soup.select(".product-card .price")
    for price in prices:
        print(f"  价格: {price.text}")

    # 属性选择器
    print("\n--- 属性选择器 ---")
    product_links = soup.select("a[href^='/product']")
    for link in product_links:
        print(f"  商品链接: {link.get('href')}")

    # 子元素选择器
    print("\n--- 子元素选择器 ---")
    first_product = soup.select_one(".product-card:first-child .product-name")
    if first_product:
        print(f"  第一个商品: {first_product.text}")


# ============================================================
# 4. 元素遍历
# ============================================================

def demo_traversal():
    """演示元素遍历"""
    print("\n" + "=" * 60)
    print("🔧 4. 元素遍历")
    print("=" * 60)

    soup = BeautifulSoup(SAMPLE_HTML, "lxml")

    # 父元素
    print("\n--- 父元素遍历 ---")
    price = soup.find("span", class_="price")
    if price:
        parent = price.parent
        print(f"  price 的父元素: {parent.name}.{parent.get('class', '')}")

    # 子元素
    print("\n--- 子元素遍历 ---")
    product_list = soup.find("div", class_="product-list")
    if product_list:
        children = [child.name for child in product_list.children if child.name]
        print(f"  product-list 的子元素: {children}")

    # 兄弟元素
    print("\n--- 兄弟元素遍历 ---")
    h1 = soup.find("h1")
    if h1:
        next_sibling = h1.find_next_sibling()
        if next_sibling:
            print(f"  h1 的下一个兄弟: {next_sibling.name}.{next_sibling.get('class', '')}")


# ============================================================
# 5. 提取数据
# ============================================================

def demo_extract():
    """演示数据提取"""
    print("\n" + "=" * 60)
    print("🔧 5. 提取数据")
    print("=" * 60)

    soup = BeautifulSoup(SAMPLE_HTML, "lxml")

    # 提取文本
    print("\n--- 提取文本 ---")
    footer = soup.find("footer")
    if footer:
        # get_text() 可以指定分隔符
        text = footer.get_text(separator=" | ", strip=True)
        print(f"  页脚文本: {text}")

    # 提取属性
    print("\n--- 提取属性 ---")
    product = soup.find("div", class_="product-card")
    if product:
        data_id = product.get("data-id")
        print(f"  data-id: {data_id}")

        price = product.find("span", class_="price")
        currency = price.get("data-currency")
        print(f"  货币: {currency}")

    # 提取所有链接
    print("\n--- 提取所有链接 ---")
    all_links = soup.find_all("a", href=True)
    link_data = [{"text": a.text, "href": a.get("href")} for a in all_links]
    for link in link_data:
        print(f"  {link['text']}: {link['href']}")


# ============================================================
# 6. lxml XPath
# ============================================================

def demo_lxml_xpath():
    """演示 lxml XPath"""
    print("\n" + "=" * 60)
    print("🔧 6. lxml XPath")
    print("=" * 60)

    tree = html.fromstring(SAMPLE_HTML)

    # 查找所有商品名
    print("\n--- 查找所有商品名 ---")
    names = tree.xpath("//h2[@class='product-name']/text()")
    for name in names:
        print(f"  商品: {name}")

    # 查找所有价格
    print("\n--- 查找所有价格 ---")
    prices = tree.xpath("//span[@class='price']/text()")
    for price in prices:
        print(f"  价格: {price}")

    # 查找所有链接
    print("\n--- 查找所有链接 ---")
    links = tree.xpath("//a/@href")
    for link in links:
        print(f"  链接: {link}")

    # 查找特定属性的元素
    print("\n--- 查找 data-id 属性 ---")
    ids = tree.xpath("//div[@data-id]/@data-id")
    for id_val in ids:
        print(f"  ID: {id_val}")

    # 组合查询
    print("\n--- 组合查询: 商品名和价格 ---")
    products = tree.xpath("//div[@class='product-card']")
    for product in products:
        name = product.xpath(".//h2/text()")[0]
        price = product.xpath(".//span[@class='price']/text()")[0]
        print(f"  {name}: {price}")


# ============================================================
# 7. 主流程
# ============================================================

def main():
    print("🚀 Day 127 - BeautifulSoup / lxml 解析：基础用法\n")

    demo_parse()
    demo_find_elements()
    demo_css_selector()
    demo_traversal()
    demo_extract()
    demo_lxml_xpath()

    print("\n" + "=" * 60)
    print("✅ 基础用法演示完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
