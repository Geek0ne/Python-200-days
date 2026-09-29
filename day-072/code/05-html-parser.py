"""
Day 072 — 实战：HTML 解析器
用正则表达式解析 HTML，提取标签、属性和文本内容
运行方式：python 05-html-parser.py
"""
import re


class SimpleHTMLParser:
    """简单的 HTML 解析器（教学用，生产环境请用 BeautifulSoup）"""

    def __init__(self, html):
        self.html = html
        self.tree = []
        self._parse()

    def _parse(self):
        """解析 HTML 字符串"""
        # 匹配所有标签
        tag_pattern = re.compile(
            r'<([a-zA-Z][a-zA-Z0-9]*)'  # 标签名
            r'((?:\s+[a-zA-Z-]+(?:=(?:"[^"]*"|\'[^\']*\'|[^\s>]*))?)*'  # 属性
            r'\s*/?)>'  # 可能是自闭合
            r'(.*?)'  # 标签内容（非贪婪）
            r'(?:</\1>)?',  # 闭合标签（可选）
            re.DOTALL
        )

        for match in tag_pattern.finditer(self.html):
            tag_name = match.group(1)
            attrs_str = match.group(2)
            content = match.group(3)

            # 解析属性
            attrs = self._parse_attributes(attrs_str)

            self.tree.append({
                'tag': tag_name,
                'attrs': attrs,
                'content': content.strip(),
            })

    def _parse_attributes(self, attrs_str):
        """解析标签属性"""
        attrs = {}
        attr_pattern = re.compile(
            r'([a-zA-Z-]+)'  # 属性名
            r'(?:=(?:"([^"]*)"|\'([^\']*)\'|(\S+)))?'  # 属性值
        )
        for match in attr_pattern.finditer(attrs_str):
            name = match.group(1)
            value = match.group(2) or match.group(3) or match.group(4) or True
            attrs[name] = value
        return attrs

    def find_tags(self, tag_name):
        """查找所有指定标签"""
        return [node for node in self.tree if node['tag'] == tag_name]

    def get_text(self):
        """获取所有文本内容"""
        return ' '.join(node['content'] for node in self.tree if node['content'])

    def print_tree(self, indent=0):
        """打印解析树"""
        for node in self.tree:
            prefix = '  ' * indent
            attrs = ' '.join(f'{k}="{v}"' for k, v in node['attrs'].items())
            attrs_str = f' {attrs}' if attrs else ''
            content_preview = node['content'][:30] + '...' if len(node['content']) > 30 else node['content']
            print(f"{prefix}<{node['tag']}{attrs_str}> {content_preview}")


def main():
    html = """
    <html>
    <head><title>测试页面</title></head>
    <body>
        <h1 class="title">欢迎学习正则表达式</h1>
        <div class="content">
            <p>这是第一个段落。</p>
            <p>这是第二个段落。</p>
            <a href="https://example.com">链接</a>
        </div>
        <img src="photo.jpg" alt="照片" />
        <ul>
            <li>项目一</li>
            <li>项目二</li>
            <li>项目三</li>
        </ul>
    </body>
    </html>
    """

    parser = SimpleHTMLParser(html)

    print("=" * 60)
    print("📊 HTML 解析结果")
    print("=" * 60)

    # 打印解析树
    parser.print_tree()

    # 查找特定标签
    print("\n" + "=" * 60)
    print("🔍 查找结果")
    print("=" * 60)

    paragraphs = parser.find_tags('p')
    print(f"\n所有 <p> 标签 ({len(paragraphs)} 个):")
    for p in paragraphs:
        print(f"  - {p['content']}")

    links = parser.find_tags('a')
    print(f"\n所有 <a> 标签 ({len(links)} 个):")
    for link in links:
        print(f"  - href={link['attrs'].get('href', 'N/A')}, 文本={link['content']}")

    images = parser.find_tags('img')
    print(f"\n所有 <img> 标签 ({len(images)} 个):")
    for img in images:
        print(f"  - src={img['attrs'].get('src', 'N/A')}, alt={img['attrs'].get('alt', 'N/A')}")

    # 获取所有文本
    print(f"\n📝 所有文本内容:")
    print(f"  {parser.get_text()}")


if __name__ == '__main__':
    main()
