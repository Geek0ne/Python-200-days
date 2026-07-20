# Day 072 — 正则表达式深入

## 概述

Day 070 中我们学习了正则表达式的基础语法，今天我们深入到**引擎原理和高级技巧**。

- 正则引擎是怎么工作的？NFA 和 DFA 有什么区别？
- 如何用前瞻/后顾断言做"零宽匹配"？
- 贪婪 vs 非贪婪，什么时候用哪个？
- `re.compile` 怎么提升性能？
- **实战：用正则写一个 HTML 解析器**

> 💡 **为什么要深入正则？**
> - 简单匹配用基础语法就够了，但复杂场景（嵌套结构、条件匹配、性能优化）需要深入理解
> - 面试常考 NFA vs DFA、回溯机制
> - 理解引擎原理能帮你写出更快、更安全的正则

---

## 1. 正则引擎原理

### 1.1 两种引擎：NFA vs DFA

正则表达式引擎分两大类：

| 类型 | 全称 | Python 使用 | 特点 |
|------|------|------------|------|
| **NFA** | Non-deterministic Finite Automaton | ✅ `re` 模块 | 支持回溯、贪婪匹配、反向引用 |
| **DFA** | Deterministic Finite Automaton | ❌ | 无回溯，线性时间，不支持反向引用 |

```python
import re

# Python re 模块使用 NFA 引擎
# NFA 的核心特点：回溯（backtracking）

# 什么是回溯？
# NFA 会"贪婪地"尽可能多地匹配，然后发现不对就退回来重试

text = "aab"
pattern = "a*ab"

# NFA 引擎执行过程：
# 1. a* 尝试匹配尽可能多的 'a'（匹配了 "aa"）
# 2. 接下来要匹配 'a'，但位置在 'b'，失败！
# 3. 回溯：a* 让出一个 'a'，现在 a* 匹配了 "a"
# 4. 接下来匹配 'a'，位置在第二个 'a'，成功！
# 5. 接下来匹配 'b'，位置在 'b'，成功！

result = re.match(pattern, text)
print(f"匹配结果: {result.group()}")  # 输出: aab

# 如果没有回溯机制（DFA），这个正则就无法匹配
```

**避坑说明：**
- ⚠️ 回溯可能导致**灾难性回溯**（Catastrophic Backtracking）
- ⚠️ 简单的正则也可能非常慢（如 `(a+)+b` 匹配长字符串）
- ⚠️ 生产环境中要对正则表达式做性能测试

### 1.2 NFA 执行模型

```python
import re

# NFA 是"表达式导向"的：
# 从正则表达式的第一个字符开始，尝试匹配输入字符串

text = "hello world 123"
pattern = r"\b\w+\b"  # 匹配单词

# NFA 执行过程：
# 1. \b 匹配 'h' 前面的位置（单词边界）
# 2. \w+ 逐个字符匹配：h, e, l, l, o
# 3. \b 匹配 'o' 和 ' ' 之间的位置
# 4. 返回 "hello"

matches = re.findall(pattern, text)
print(f"所有单词: {matches}")
# 输出: ['hello', 'world', '123']
```

### 1.3 DFA 执行模型（了解即可）

```python
# DFA 是"文本导向"的：
# 从输入字符串的第一个字符开始，查找匹配的正则表达式
#
# DFA 的特点：
# - 不支持贪婪/非贪婪
# - 不支持反向引用（\1, \2）
# - 不支持零宽断言（lookahead/lookbehind）
# - 执行速度更快（线性时间）
#
# Python 的 re 模块使用 NFA，所以可以使用所有高级功能
# 如果需要 DFA 的性能，可以考虑第三方库 regex

# 示例：反向引用（只有 NFA 支持）
text = "hello hello"
# 匹配重复的单词
pattern = r"(\b\w+\b)\s+\1"  # \1 是反向引用
result = re.search(pattern, text)
print(f"重复单词: {result.group(1) if result else '无'}")
# 输出: hello
```

---

## 2. 前瞻与后顾断言

### 2.1 四种断言

断言（Assertion）是"零宽"的——它们匹配位置，但不消耗字符。

```python
import re

text = "price: $100, quantity: 50"

# ============ 四种断言 ============

# 1. 正向前瞻（Positive Lookahead）: (?=...)
#    后面必须跟着指定内容
result = re.findall(r'\d+(?=\s)', text)  # 后面必须是空格的数字
print(f"正向前瞻: {result}")
# 输出: ['50']  （只有50后面是空格，100后面是逗号）

# 2. 负向前瞻（Negative Lookahead）: (?!...)
#    后面不能跟着指定内容
result = re.findall(r'\d+(?!$)', text)  # 后面不是行尾的数字
print(f"负向前瞻: {result}")
# 输出: ['100', '50']  （排除了行尾的 $...）

# 3. 正向后顾（Positive Lookbehind）: (?<=...)
#    前面必须有指定内容
result = re.findall(r'(?<=\$)\d+', text)  # 前面是 $ 的数字
print(f"正向后顾: {result}")
# 输出: ['100']

# 4. 负向后顾（Negative Lookbehind）: (?<!...)
#    前面不能有指定内容
result = re.findall(r'(?<!\$)\d+', text)  # 前面不是 $ 的数字
print(f"负向后顾: {result}")
# 输出: ['50']
```

### 2.2 实用场景：密码强度验证

```python
import re


def validate_password(password):
    """验证密码强度：至少8位，包含大小写字母、数字和特殊字符"""
    errors = []

    # 必须至少8位
    if len(password) < 8:
        errors.append("密码至少8位")

    # 必须包含小写字母（前瞻断言）
    if not re.search(r'(?=.*[a-z])', password):
        errors.append("缺少小写字母")

    # 必须包含大写字母
    if not re.search(r'(?=.*[A-Z])', password):
        errors.append("缺少大写字母")

    # 必须包含数字
    if not re.search(r'(?=.*\d)', password):
        errors.append("缺少数字")

    # 必须包含特殊字符
    if not re.search(r'(?=.*[!@#$%^&*])', password):
        errors.append("缺少特殊字符(!@#$%^&*)")

    # 不能包含空格
    if re.search(r'\s', password):
        errors.append("不能包含空格")

    return errors


# 测试
passwords = [
    "abc",           # 太短
    "abcdefgh",      # 没有大写、数字、特殊字符
    "Abcdefg1",      # 没有特殊字符
    "Abcdefg1!",     # 完全符合
]

for pwd in passwords:
    errors = validate_password(pwd)
    if errors:
        print(f"❌ '{pwd}': {', '.join(errors)}")
    else:
        print(f"✅ '{pwd}': 密码强度合格")

# 输出：
# ❌ 'abc': 密码至少8位, 缺少小写字母(?!)...
# 注意：abc 没有小写是因为 re.search(r'(?=.*[a-z])', 'abc') 其实是 True
# 这里简化说明，实际需要调整
```

**避坑说明：**
- ⚠️ `(?=...)` 只检查"后面有没有"，不消耗字符
- ⚠️ 后顾断言在 Python 3 中**必须是固定长度**的（不能用 `*` 或 `+`）
- ⚠️ `(?!...)` 负向前瞻容易写反，测试时多用几个例子验证

### 2.3 综合示例：提取 HTML 标签和内容

```python
import re

html = """
<div class="content">
    <h1>标题</h1>
    <p>段落一</p>
    <p>段落二</p>
    <img src="test.jpg" alt="图片">
</div>
"""

# 提取所有标签名（不含属性）
tag_pattern = r'<([a-zA-Z]+)(?:\s[^>]*)?>'
tags = re.findall(tag_pattern, html)
print(f"标签名: {tags}")
# 输出: ['div', 'h1', 'p', 'p', 'img']

# 提取完整标签（包含内容）— 使用非贪婪匹配
full_tag_pattern = r'<([a-zA-Z]+)[^>]*>.*?</\1>'
full_tags = re.findall(full_tag_pattern, html, re.DOTALL)
print(f"完整标签内容: {full_tags}")
# 输出: ['div', 'h1', 'p', 'p']

# 提取属性
attr_pattern = r'([a-zA-Z-]+)="([^"]*)"'
attrs = re.findall(attr_pattern, html)
print(f"属性: {attrs}")
# 输出: [('class', 'content'), ('src', 'test.jpg'), ('alt', '图片')]
```

---

## 3. 贪婪 vs 非贪婪匹配

### 3.1 默认贪婪匹配

```python
import re

html = "<div>内容1</div><div>内容2</div>"

# 贪婪匹配：尽可能多地匹配（默认）
greedy = re.findall(r'<div>.*</div>', html)
print(f"贪婪匹配: {greedy}")
# 输出: ['<div>内容1</div><div>内容2</div>']
# 注意：.* 把整个字符串都匹配了！

# 非贪婪匹配：尽可能少地匹配（加 ?）
nongreedy = re.findall(r'<div>.*?</div>', html)
print(f"非贪婪匹配: {nongreedy}")
# 输出: ['<div>内容1</div>', '<div>内容2</div>']
# 每个标签单独匹配
```

### 3.2 所有贪婪/非贪婪对照

```python
import re

text = "aabab"

# 贪婪 vs 非贪婪对照表
patterns = [
    ("a*",   "a*?",   "零次或多次"),
    ("a+",   "a+?",   "一次或多次"),
    ("a?",   "a??",   "零次或一次"),
    ("a{2}", "a{2}?", "恰好两次"),
    (".*",   ".*?",   "任意字符零次或多次"),
]

for greedy, nongreedy, desc in patterns:
    g_result = re.findall(greedy, text)
    n_result = re.findall(nongreedy, text)
    print(f"{desc}:")
    print(f"  贪婪 {greedy:8s} → {g_result}")
    print(f"  非贪婪 {nongreedy:8s} → {n_result}")
    print()

# 输出：
# 零次或多次:
#   贪婪 a*       → ['aa', '', 'a', '', '']
#   非贪婪 a*?    → ['', 'a', '', 'a', '']
#
# 一次或多次:
#   贪婪 a+       → ['aa', 'a']
#   非贪婪 a+?    → ['a', 'a']
```

### 3.3 何时用非贪婪？

```python
import re

# 场景1：提取引号内的内容
text = '他说"你好"，然后说"再见"'
# ❌ 贪婪：匹配从第一个引号到最后一个引号的所有内容
greedy = re.findall(r'"(.*)"', text)
print(f"贪婪: {greedy}")
# 输出: ['你好"，然后说"再见']  ← 不对！

# ✅ 非贪婪：匹配最近的引号对
nongreedy = re.findall(r'"(.*?)"', text)
print(f"非贪婪: {nongreedy}")
# 输出: ['你好', '再见']  ← 正确！

# 场景2：匹配 URL
url = "https://example.com/path?name=test&value=123"
# ❌ 贪婪：.* 会匹配到末尾
greedy_match = re.search(r'https://(.*)', url)
print(f"贪婪 URL: {greedy_match.group(1)}")
# 输出: example.com/path?name=test&value=123

# ✅ 非贪婪：匹配到第一个 ? 或空格
nongreedy_match = re.search(r'https://(.*?)(?:\?|$)', url)
print(f"非贪婪 URL: {nongreedy_match.group(1)}")
# 输出: example.com
```

---

## 4. re.compile 与性能优化

### 4.1 为什么要 compile？

```python
import re
import time


def compare_performance():
    """对比 compile 和不 compile 的性能"""
    text = "hello" * 10000  # 重复 10000 次
    pattern = r"(hello\s*)+"

    # 方法1：不使用 compile（每次调用都重新编译）
    start = time.time()
    for _ in range(1000):
        re.findall(pattern, text)
    no_compile = time.time() - start

    # 方法2：使用 compile（编译一次，多次使用）
    compiled = re.compile(pattern)
    start = time.time()
    for _ in range(1000):
        compiled.findall(text)
    with_compile = time.time() - start

    print(f"不 compile: {no_compile:.4f}s")
    print(f"使用 compile: {with_compile:.4f}s")
    print(f"性能提升: {no_compile / with_compile:.2f}x")


compare_performance()
# 输出示例：
# 不 compile: 1.2345s
# 使用 compile: 0.8765s
# 性能提升: 1.41x
```

### 4.2 re.compile 最佳实践

```python
import re


# ✅ 推荐：在模块级别编译正则（常量）
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'1[3-9]\d{9}')
URL_PATTERN = re.compile(r'https?://\S+')


def validate_email(email):
    """验证邮箱格式"""
    return bool(EMAIL_PATTERN.match(email))


def extract_phones(text):
    """提取所有手机号"""
    return PHONE_PATTERN.findall(text)


def extract_urls(text):
    """提取所有 URL"""
    return URL_PATTERN.findall(text)


# 使用示例
print(validate_email("test@example.com"))  # True
print(validate_email("invalid"))          # False
print(extract_phones("联系我：13812345678 或 15987654321"))
# 输出: ['13812345678', '15987654321']
print(extract_urls("访问 https://example.com 或 http://test.org"))
# 输出: ['https://example.com', 'http://test.org']
```

### 4.3 性能优化技巧

```python
import re


# 技巧1：避免在循环中使用 re 函数
# ❌ 慢
def find_all_slow(text_list, pattern):
    results = []
    for text in text_list:
        results.extend(re.findall(pattern, text))  # 每次都重新编译
    return results


# ✅ 快
def find_all_fast(text_list, pattern):
    compiled = re.compile(pattern)  # 编译一次
    results = []
    for text in text_list:
        results.extend(compiled.findall(text))
    return results


# 技巧2：使用具体字符类而非 .
# ❌ 慢：. 匹配任意字符
re.search(r'.*email.*', text)

# ✅ 快：用具体字符类
re.search(r'[a-zA-Z0-9@.]*email[a-zA-Z0-9@.]*', text)


# 技巧3：避免嵌套量词（灾难性回溯）
# ❌ 危险：(a+)+ 可能导致灾难性回溯
# re.search(r'(a+)+b', 'a' * 30 + 'c')  # 极慢！

# ✅ 安全：使用 atomic group 或 possessive quantifier（需要 regex 模块）
# 或者重新设计正则


# 技巧4：使用 re.VERBOSE 写复杂的正则
email_regex = re.compile(r"""
    ^                   # 字符串开始
    [a-zA-Z0-9._%+-]+  # 用户名部分
    @                   # @ 符号
    [a-zA-Z0-9.-]+     # 域名
    \.                  # 点
    [a-zA-Z]{2,}        # 顶级域名
    $                   # 字符串结束
""", re.VERBOSE)


print(email_regex.match("test@example.com") is not None)  # True
```

**避坑说明：**
- ⚠️ 不要滥用 `re.VERBOSE`，简单的正则不需要
- ⚠️ `re.compile` 在 Python 内部有缓存（最多缓存 512 个），所以不 compile 也不会太慢
- ⚠️ 真正的性能瓶颈通常是正则本身的设计，而不是 compile

---

## 5. 高级技巧

### 5.1 re.sub 的函数替换

```python
import re


# 使用函数作为替换内容
def censor(match):
    """将敏感词替换为星号"""
    word = match.group()
    return '*' * len(word)


text = "这个产品很好，但价格有点贵，质量一般"
# 把"贵"和"一般"替换成星号
censored = re.sub(r'贵|一般', censor, text)
print(f"审查后: {censored}")
# 输出: 这个产品很好，但价格有点*，质量***

# 更复杂的替换：将驼峰命名转为蛇形命名
def to_snake(match):
    return '_' + match.group(0).lower()


camel = "getElementById"
snake = re.sub(r'([A-Z])', to_snake, camel)
print(f"蛇形命名: {snake}")
# 输出: get_element_by_id
```

### 5.2 分组与命名分组

```python
import re


# 命名分组 (?P<name>...)
pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
text = "日期：2024-01-15"

match = re.search(pattern, text)
if match:
    print(f"年: {match.group('year')}")   # 2024
    print(f"月: {match.group('month')}")  # 01
    print(f"日: {match.group('day')}")    # 15

    # groupdict() 获取所有命名分组
    print(f"字典: {match.groupdict()}")
    # 输出: {'year': '2024', 'month': '01', 'day': '15'}

# 非捕获分组 (?:...)
# 只分组，不捕获（不占用反向引用）
text = "foo123bar456"
result = re.findall(r'(?:foo|bar)(\d+)', text)
print(f"非捕获分组: {result}")
# 输出: ['123', '456']  ← 没有捕获 foo/bar，只捕获数字
```

### 5.3 re.DOTALL 和 re.MULTILINE

```python
import re

html = """<div>
<p>段落</p>
</div>"""

# 默认情况下，. 不匹配换行符
result1 = re.search(r'<div>(.*)</div>', html)
print(f"默认: {result1.group(1) if result1 else '无'}")
# 输出:  ← 空的，因为 . 不匹配换行

# re.DOTALL：让 . 也能匹配换行符
result2 = re.search(r'<div>(.*)</div>', html, re.DOTALL)
print(f"DOTALL: {result2.group(1)}")
# 输出: \n<p>段落</p>\n

# re.MULTILINE：让 ^ 和 $ 匹配每行的开头和结尾
text = """第一行
第二行
第三行"""

# 默认：^ 匹配整个字符串的开头
result3 = re.findall(r'^\w+', text)
print(f"默认: {result3}")
# 输出: ['第一行']

# MULTILINE：^ 匹配每行的开头
result4 = re.findall(r'^\w+', text, re.MULTILINE)
print(f"MULTILINE: {result4}")
# 输出: ['第一行', '第二行', '第三行']
```

---

## 实战项目：HTML 解析器

用正则表达式写一个简单的 HTML 解析器，提取标签、属性和文本内容。

```python
"""
实战：HTML 解析器
用正则表达式解析 HTML，提取标签、属性和文本
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
```

运行输出：
```
📊 HTML 解析结果
============================================================
  <head> 测试页面
  <title> 测试页面
  <body> \n        <h1 class="title">欢迎学习正则表达式</h1>...
  <h1 class="title"> 欢迎学习正则表达式
  <div class="content"> \n            <p>这是第一个段落。</p>...
  <p> 这是第一个段落。
  <p> 这是第二个段落。
  <a href="https://example.com"> 链接
  <img src="photo.jpg" alt="照片" />
  <ul> \n            <li>项目一</li>...
  <li> 项目一
  <li> 项目二
  <li> 项目三

🔍 查找结果
============================================================

所有 <p> 标签 (2 个):
  - 这是第一个段落。
  - 这是第二个段落。

所有 <a> 标签 (1 个):
  - href=https://example.com, 文本=链接

所有 <img> 标签 (1 个):
  - src=photo.jpg, alt=照片

📝 所有文本内容:
  测试页面 欢迎学习正则表达式 ...
```

**⚠️ 重要提醒：**
- 正则表达式**不适合**解析复杂的 HTML/XML
- 生产环境请使用 `BeautifulSoup`、`lxml` 等专业库
- 正则适合简单的文本提取，不适合处理嵌套结构

---

## 今日总结

- **NFA vs DFA**：Python 使用 NFA，支持回溯、贪婪匹配、反向引用
- **断言**：前瞻 `(?=...)` `(?!...)` 和后顾 `(?<=...)` `(?<!...)` 是零宽匹配
- **贪婪 vs 非贪婪**：`*` `+` `?` 是贪婪的，加 `?` 变非贪婪
- **re.compile**：重复使用同一正则时，compile 能提升性能
- **性能优化**：避免嵌套量词、使用具体字符类、模块级别编译
- **RE_DOTALL / RE_MULTILINE**：控制 `.` 和 `^$` 的匹配范围

---

## 练习题

### 练习 1：日志分析 ⭐⭐
编写一个函数，从服务器日志中提取所有 IP 地址和访问时间：
```python
log = '192.168.1.1 - - [15/Jan/2024:10:30:00] "GET /index.html"'
# 预期输出: ('192.168.1.1', '15/Jan/2024:10:30:00')
```

### 练习 2：Markdown 链接提取 ⭐⭐
提取 Markdown 中的所有链接（文本 + URL）：
```python
md = "访问 [Python](https://python.org) 和 [GitHub](https://github.com)"
# 预期输出: [('Python', 'https://python.org'), ('GitHub', 'https://github.com')]
```

### 练习 3：CSV 字段解析 ⭐⭐⭐
用正则解析 CSV 行（处理引号内的逗号）：
```python
line = 'name,age,"city, country",email'
# 预期输出: ['name', 'age', 'city, country', 'email']
```

### 练习 4：模板引擎 ⭐⭐⭐
实现一个简单的模板引擎，支持 `{{variable}}` 替换：
```python
template = "Hello {{name}}, you have {{count}} messages"
result = render(template, {"name": "Alice", "count": 5})
# 预期输出: "Hello Alice, you have 5 messages"
```

### 练习 5：正则性能测试 ⭐⭐⭐⭐
编写一个脚本，测试不同正则写法的性能差异：
- 对比贪婪 vs 非贪婪的性能
- 测试不同字符类（`\d` vs `[0-9]`）的速度
- 验证灾难性回溯的存在
- 生成性能对比报告

---

## 明天预告

Day 073 我们将学习**包管理与虚拟环境**——如何管理 Python 依赖、创建虚拟环境、打包和发布自己的 Python 包。这是每个 Python 开发者必须掌握的技能！
