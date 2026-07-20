"""
Day 076 - Scrapy 基础爬虫示例
爬取 quotes.toscrape.com 名言数据

运行方式（在 Scrapy 项目中）：
    scrapy crawl quotes

独立运行方式（演示基本原理）：
    python 01-基础爬虫.py
"""
import requests
from html.parser import HTMLParser


class QuoteParser(HTMLParser):
    """
    简易 HTML 解析器 - 演示爬虫的底层原理
    
    Scrapy 内部使用了更强大的 Selector，
    但理解底层的 HTML 解析有助于理解爬虫工作原理。
    """
    
    def __init__(self):
        super().__init__()
        self.quotes = []
        self.current_quote = {}
        self.in_quote = False
        self.in_author = False
        self.in_text = False
        self.text_buffer = []
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get("class", "")
        
        if tag == "div" and "quote" in class_name:
            self.in_quote = True
            self.current_quote = {}
        
        if self.in_quote:
            if tag == "span" and "text" in class_name:
                self.in_text = True
                self.text_buffer = []
            elif tag == "small" and "author" in class_name:
                self.in_author = True
                self.text_buffer = []
            elif tag == "a" and "tag" in class_name:
                tag_text = self.get_text()
                self.current_quote.setdefault("tags", []).append(tag_text)
    
    def handle_endtag(self, tag):
        if self.in_text and tag == "span":
            self.current_quote["text"] = "".join(self.text_buffer).strip()
            self.in_text = False
        
        if self.in_author and tag == "small":
            self.current_quote["author"] = "".join(self.text_buffer).strip()
            self.in_author = False
        
        if tag == "div" and self.in_quote:
            if self.current_quote.get("text"):
                self.quotes.append(self.current_quote)
            self.in_quote = False
            self.current_quote = {}
    
    def handle_data(self, data):
        if self.in_text or self.in_author:
            self.text_buffer.append(data)


def crawl_quotes():
    """
    基础爬虫：爬取名言网站
    
    流程：
    1. 发送 HTTP 请求获取页面
    2. 解析 HTML 提取数据
    3. 处理分页
    4. 保存结果
    """
    base_url = "https://quotes.toscrape.com"
    all_quotes = []
    page = 1
    
    print("🕷️  开始爬取 quotes.toscrape.com...")
    
    while True:
        url = f"{base_url}/page/{page}/"
        print(f"📄 正在爬取第 {page} 页: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ 请求失败: {e}")
            break
        
        # 解析页面
        parser = QuoteParser()
        parser.feed(response.text)
        
        if not parser.quotes:
            print("✅ 没有更多数据，爬取结束")
            break
        
        all_quotes.extend(parser.quotes)
        print(f"   提取到 {len(parser.quotes)} 条名言")
        
        # 检查是否有下一页
        if f"page/{page + 1}/" not in response.text:
            print("✅ 已到最后一页")
            break
        
        page += 1
    
    # 统计结果
    print(f"\n📊 爬取完成！共 {len(all_quotes)} 条名言")
    
    # 显示前 5 条
    for i, q in enumerate(all_quotes[:5], 1):
        text = q["text"][:50] + "..." if len(q["text"]) > 50 else q["text"]
        tags = ", ".join(q.get("tags", []))
        print(f"  {i}. [{q['author']}] {text}")
        print(f"     标签: {tags}")
    
    # 保存到文件
    import json
    output_file = "quotes.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_quotes, f, ensure_ascii=False, indent=2)
    print(f"\n💾 数据已保存到 {output_file}")
    
    return all_quotes


if __name__ == "__main__":
    crawl_quotes()
