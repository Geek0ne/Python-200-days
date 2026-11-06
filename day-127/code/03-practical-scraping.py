"""
Day 127 - BeautifulSoup / lxml 解析：实战案例
03-practical-scraping.py

演示完整的网页数据提取流程
"""

from bs4 import BeautifulSoup
from lxml import html
import requests
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


# ============================================================
# 1. 数据模型
# ============================================================

@dataclass
class Product:
    """商品数据模型"""
    id: str
    name: str
    price: float
    currency: str
    rating: float
    review_count: int
    category: str
    url: str
    in_stock: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass
class Article:
    """文章数据模型"""
    title: str
    author: str
    date: str
    category: str
    content: str
    tags: List[str]
    url: str


# ============================================================
# 2. 通用爬虫框架
# ============================================================

class WebScraper:
    """通用网页爬虫框架"""

    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self.session = self._create_session()
        self.results = []

    def _create_session(self) -> requests.Session:
        """创建带伪装的 Session"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        return session

    def fetch(self, url: str) -> Optional[BeautifulSoup]:
        """获取并解析网页"""
        try:
            full_url = url if url.startswith("http") else f"{self.base_url}{url}"
            resp = self.session.get(full_url, timeout=10)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            print(f"  ⚠️ 获取失败: {url} - {e}")
            return None

    def fetch_lxml(self, url: str) -> Optional[html.HtmlElement]:
        """获取并解析为 lxml 树"""
        try:
            full_url = url if url.startswith("http") else f"{self.base_url}{url}"
            resp = self.session.get(full_url, timeout=10)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return html.fromstring(resp.text)
        except Exception as e:
            print(f"  ⚠️ 获取失败: {url} - {e}")
            return None

    def save_json(self, data: list, filename: str):
        """保存为 JSON"""
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已保存: {filepath} ({len(data)} 条)")

    def save_csv(self, data: list, filename: str, fieldnames: list = None):
        """保存为 CSV"""
        if not data:
            return
        output_dir = Path("data")
        output_dir.mkdir(exist_ok=True)
        filepath = output_dir / filename

        if fieldnames is None:
            fieldnames = list(data[0].keys())

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"  ✅ 已保存: {filepath} ({len(data)} 条)")


# ============================================================
# 3. 实战：从模拟 HTML 提取商品数据
# ============================================================

def demo_product_extraction():
    """演示商品数据提取"""
    print("=" * 60)
    print("🔧 实战 1: 商品数据提取")
    print("=" * 60)

    # 模拟电商页面 HTML
    html_content = """
    <html>
    <body>
        <div class="search-results">
            <div class="product-item" data-sku="P001">
                <h3 class="title"><a href="/product/1">Python编程从入门到实践</a></h3>
                <div class="price">
                    <span class="current">¥68.00</span>
                    <span class="original">¥99.00</span>
                </div>
                <div class="rating">
                    <span class="stars">⭐ 4.8</span>
                    <span class="count">(1,234条评价)</span>
                </div>
                <span class="category">计算机/编程</span>
                <span class="stock in-stock">有货</span>
            </div>

            <div class="product-item" data-sku="P002">
                <h3 class="title"><a href="/product/2">机器学习实战</a></h3>
                <div class="price">
                    <span class="current">¥128.00</span>
                </div>
                <div class="rating">
                    <span class="stars">⭐ 4.9</span>
                    <span class="count">(567条评价)</span>
                </div>
                <span class="category">计算机/AI</span>
                <span class="stock in-stock">有货</span>
            </div>

            <div class="product-item" data-sku="P003">
                <h3 class="title"><a href="/product/3">数据分析基础</a></h3>
                <div class="price">
                    <span class="current">¥45.00</span>
                </div>
                <div class="rating">
                    <span class="stars">⭐ 4.5</span>
                    <span class="count">(89条评价)</span>
                </div>
                <span class="category">计算机/数据</span>
                <span class="stock out-of-stock">缺货</span>
            </div>
        </div>
    </body>
    </html>
    """

    soup = BeautifulSoup(html_content, "lxml")
    products = []

    # 提取所有商品
    items = soup.find_all("div", class_="product-item")
    for item in items:
        # 提取 SKU
        sku = item.get("data-sku", "")

        # 提取标题和链接
        title_tag = item.find("h3", class_="title")
        name = title_tag.text.strip() if title_tag else ""
        link = title_tag.find("a")
        url = link.get("href", "") if link else ""

        # 提取价格
        price_tag = item.find("span", class_="current")
        price_text = price_tag.text.strip() if price_tag else "0"
        price = float(re.sub(r'[¥￥,]', '', price_text))

        # 提取评分
        stars_tag = item.find("span", class_="stars")
        rating_text = stars_tag.text.strip() if stars_tag else "0"
        rating = float(re.sub(r'[^\d.]', '', rating_text))

        # 提取评价数
        count_tag = item.find("span", class_="count")
        count_text = count_tag.text.strip() if count_tag else "0"
        review_count = int(re.sub(r'[^\d]', '', count_text))

        # 提取分类
        category = item.find("span", class_="category")
        category_text = category.text.strip() if category else ""

        # 判断库存
        stock_tag = item.find("span", class_="stock")
        in_stock = "in-stock" in stock_tag.get("class", []) if stock_tag else True

        product = Product(
            id=sku,
            name=name,
            price=price,
            currency="CNY",
            rating=rating,
            review_count=review_count,
            category=category_text,
            url=url,
            in_stock=in_stock,
        )
        products.append(product)

    # 打印结果
    print(f"\n  提取到 {len(products)} 个商品:")
    for p in products:
        stock_status = "✅ 有货" if p.in_stock else "❌ 缺货"
        print(f"  [{p.id}] {p.name} - ¥{p.price} ({p.rating}⭐, {p.review_count}条评价) {stock_status}")

    # 保存数据
    product_dicts = [p.to_dict() for p in products]
    # 创建一个简单的 WebScraper 来调用保存方法
    scraper = WebScraper()
    scraper.save_json(product_dicts, "products.json")

    import re
    return products


# ============================================================
# 4. 实战：文章内容提取
# ============================================================

def demo_article_extraction():
    """演示文章内容提取"""
    print("\n" + "=" * 60)
    print("🔧 实战 2: 文章内容提取")
    print("=" * 60)

    html_content = """
    <article class="post">
        <header>
            <h1 class="entry-title">Python 爬虫入门指南</h1>
            <div class="entry-meta">
                <span class="author">作者: 张三</span>
                <time class="date" datetime="2024-01-15">2024年1月15日</time>
                <span class="category">分类: Python</span>
            </div>
        </header>

        <div class="entry-content">
            <h2>什么是爬虫？</h2>
            <p>爬虫是一种自动化程序，用于从互联网上获取数据。</p>
            <p>它可以模拟浏览器的行为，访问网页并提取所需信息。</p>

            <h2>爬虫的基本流程</h2>
            <ol>
                <li>发送 HTTP 请求</li>
                <li>获取网页内容</li>
                <li>解析 HTML</li>
                <li>提取数据</li>
                <li>存储数据</li>
            </ol>

            <h2>注意事项</h2>
            <ul>
                <li>遵守 robots.txt 协议</li>
                <li>控制请求频率</li>
                <li>处理异常情况</li>
            </ul>

            <div class="code-block">
                <pre><code>import requests
from bs4 import BeautifulSoup

resp = requests.get("https://example.com")
soup = BeautifulSoup(resp.text, "lxml")
title = soup.find("title").text
print(title)</code></pre>
            </div>
        </div>

        <footer class="entry-footer">
            <div class="tags">
                <a href="/tag/python">Python</a>
                <a href="/tag/crawler">爬虫</a>
                <a href="/tag/tutorial">教程</a>
            </div>
        </footer>
    </article>
    """

    soup = BeautifulSoup(html_content, "lxml")

    # 提取文章元数据
    title = soup.find("h1", class_="entry-title")
    title_text = title.text.strip() if title else ""

    author_tag = soup.find("span", class_="author")
    author = author_tag.text.replace("作者:", "").strip() if author_tag else ""

    date_tag = soup.find("time", class_="date")
    date = date_tag.text.strip() if date_tag else ""

    category_tag = soup.find("span", class_="category")
    category = category_tag.text.replace("分类:", "").strip() if category_tag else ""

    # 提取正文
    content_div = soup.find("div", class_="entry-content")
    if content_div:
        # 清理代码块
        for code in content_div.find_all("pre"):
            code.decompose()

        content = content_div.get_text(separator="\n", strip=True)
    else:
        content = ""

    # 提取标签
    tags = [a.text for a in soup.select(".tags a")]

    article = Article(
        title=title_text,
        author=author,
        date=date,
        category=category,
        content=content,
        tags=tags,
        url="https://example.com/python-crawler-guide",
    )

    print(f"\n  📝 文章信息:")
    print(f"  标题: {article.title}")
    print(f"  作者: {article.author}")
    print(f"  日期: {article.date}")
    print(f"  分类: {article.category}")
    print(f"  标签: {', '.join(article.tags)}")
    print(f"  正文长度: {len(article.content)} 字符")
    print(f"  正文预览: {article.content[:100]}...")

    return article


# ============================================================
# 5. 实战：表格数据提取
# ============================================================

def demo_table_extraction():
    """演示表格数据提取"""
    print("\n" + "=" * 60)
    print("🔧 实战 3: 表格数据提取")
    print("=" * 60)

    html_content = """
    <table class="data-table">
        <thead>
            <tr>
                <th>排名</th>
                <th>编程语言</th>
                <th>流行度</th>
                <th>变化</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>1</td>
                <td>Python</td>
                <td>28.14%</td>
                <td class="up">+2.56%</td>
            </tr>
            <tr>
                <td>2</td>
                <td>Java</td>
                <td>15.42%</td>
                <td class="down">-1.32%</td>
            </tr>
            <tr>
                <td>3</td>
                <td>JavaScript</td>
                <td>8.73%</td>
                <td class="up">+0.56%</td>
            </tr>
            <tr>
                <td>4</td>
                <td>C++</td>
                <td>5.67%</td>
                <td class="down">-0.23%</td>
            </tr>
            <tr>
                <td>5</td>
                <td>Go</td>
                <td>3.89%</td>
                <td class="up">+1.12%</td>
            </tr>
        </tbody>
    </table>
    """

    soup = BeautifulSoup(html_content, "lxml")

    # 提取表头
    headers = [th.text for th in soup.select("thead th")]
    print(f"  表头: {headers}")

    # 提取数据行
    print("\n  编程语言排行:")
    rows = soup.select("tbody tr")
    data = []
    for row in rows:
        cells = row.find_all("td")
        rank = cells[0].text.strip()
        language = cells[1].text.strip()
        popularity = cells[2].text.strip()
        change = cells[3].text.strip()
        change_class = cells[3].get("class", [])
        trend = "📈" if "up" in change_class else "📉"

        row_data = {
            "排名": rank,
            "语言": language,
            "流行度": popularity,
            "变化": f"{trend} {change}",
        }
        data.append(row_data)
        print(f"  {rank}. {language} - {popularity} ({trend} {change})")

    # 保存
    scraper = WebScraper()
    scraper.save_json(data, "language_ranking.json")
    scraper.save_csv(data, "language_ranking.csv")

    return data


# ============================================================
# 6. 主流程
# ============================================================

def main():
    print("🚀 Day 127 - BeautifulSoup / lxml 解析：实战案例\n")

    import re

    # 实战 1: 商品数据提取
    products = demo_product_extraction()

    # 实战 2: 文章内容提取
    article = demo_article_extraction()

    # 实战 3: 表格数据提取
    table_data = demo_table_extraction()

    print("\n" + "=" * 60)
    print("✅ 实战案例演示完成")
    print("=" * 60)
    print("\n📁 数据已保存到 data/ 目录:")
    print("  - products.json")
    print("  - language_ranking.json")
    print("  - language_ranking.csv")


if __name__ == "__main__":
    main()
