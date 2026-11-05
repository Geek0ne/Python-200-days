#!/usr/bin/env python3
"""
Day 026 — 正则表达式基础

涵盖：
1. 元字符与基本匹配
2. re.search / re.match / re.fullmatch
3. re.findall / re.finditer
4. 分组与捕获（命名组、非捕获组）
5. 贪婪与非贪婪匹配

可直接运行：python3 01-regex-basics.py
"""

import re

print("=" * 60)
print("1. 基本匹配 — 元字符入门")
print("=" * 60)

text = "Hello! My email is alice@example.com and phone is 138-1234-5678."

# . 匹配任意字符
result = re.search(r'H.llo', text)
print(f"'.' 匹配 H.llo: {result.group() if result else '无匹配'}")

# \d 匹配数字
result = re.search(r'\d{3}-\d{4}-\d{4}', text)
print(f"手机号匹配: {result.group() if result else '无匹配'}")

# \w 匹配单词字符
result = re.findall(r'\w+', text)
print(f"所有单词: {result[:6]}...")  # 只显示前6个

# ^ 和 $ 匹配开头和结尾
print(f"是否以 Hello 开头: {bool(re.search(r'^Hello', text))}")
print(f"是否以句号结尾: {bool(re.search(r'\.$', text))}")

print("\n" + "=" * 60)
print("2. search / match / fullmatch 的区别")
print("=" * 60)

data = "  年收入: 500000 元"

# match — 从开头匹配（不忽略空白）
m = re.match(r'年收入', data)
print(f"re.match('年收入'): {m}")  # None，因为开头有空格

# search — 搜索整个字符串
m = re.search(r'年收入', data)
print(f"re.search('年收入'): '{m.group()}' 位置: {m.span() if m else None}")

# fullmatch — 整个字符串完全匹配
m = re.fullmatch(r'500000', data)
print(f"re.fullmatch('500000'): {m}")  # None

m = re.fullmatch(r'.+', data)
print(f"re.fullmatch('.+'): '{m.group()}'" if m else "无匹配")

# 实用场景：验证完整输入
email_pattern = r'^[\w.+-]+@[\w-]+\.[\w.]+$'
tests = ['user@example.com', 'invalid@', '@domain.com', 'a@b.co']
for t in tests:
    is_valid = bool(re.fullmatch(email_pattern, t))
    print(f"  邮箱验证 '{t}': {'✅ 有效' if is_valid else '❌ 无效'}")

print("\n" + "=" * 60)
print("3. findall vs finditer — 找到所有匹配")
print("=" * 60)

log_text = """
2026-06-17 10:15:30 [INFO] 用户 alice 登录成功
2026-06-17 10:16:45 [ERROR] 数据库连接超时
2026-06-17 10:17:01 [WARN] 磁盘使用率 85%
2026-06-17 10:18:22 [INFO] 用户 bob 退出登录
"""

# findall — 返回所有匹配的列表
levels = re.findall(r'\[(INFO|WARN|ERROR)\]', log_text)
print(f"所有日志级别 (findall): {levels}")

# findall 带分组 — 返回元组列表
entries = re.findall(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.*)', log_text)
print(f"提取的结构化条目:")
for date, level, msg in entries:
    print(f"  [{level:5s}] {date} — {msg}")

# finditer — 返回迭代器，包含完整 Match 对象
print("\n--- finditer 带详细位置信息 ---")
for m in re.finditer(r'\[(\w+)\]', log_text):
    print(f"  级别: {m.group(1):5s} | 位置: {m.span()} | 上下文: ...{log_text[max(0,m.start()-10):m.end()+15]}...")

print("\n" + "=" * 60)
print("4. 分组与捕获 — 提取结构化信息")
print("=" * 60)

# 基本分组
text = "我的生日是 1995-03-20，不是 1996-01-15"
pattern = r'(\d{4})-(\d{2})-(\d{2})'
m = re.search(pattern, text)
if m:
    print(f"完整匹配: {m.group()}")
    print(f"年: {m.group(1)}, 月: {m.group(2)}, 日: {m.group(3)}")
    print(f"所有分组: {m.groups()}")

# 命名分组 — 更容易阅读
named_pattern = r'(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})'
m = re.search(named_pattern, text)
if m:
    print(f"\n命名分组:")
    print(f"  年: {m.group('year')}, 月: {m.group('month')}, 日: {m.group('day')}")
    print(f"  字典形式: {m.groupdict()}")

# 非捕获分组 (?:...) — 只分组但不保存
text = "我喜欢猫和狗"
pattern_with_capture = r'猫|狗'        # 会产生分组结果
pattern_nocap = r'(?:猫|狗)'           # 不产生分组
m = re.search(pattern_nocap, text)
print(f"\n非捕获分组: {m.group() if m else '无匹配'}")

print("\n" + "=" * 60)
print("5. 贪婪 vs 非贪婪 — 最容易踩的坑")
print("=" * 60)

html = '<div class="main">内容A</div><p>段落</p><div>内容B</div>'

# 贪婪匹配 — 尽可能多匹配
greedy = re.findall(r'<div>(.*)</div>', html)
print(f"贪婪匹配结果: {greedy}")
print(f"  → 从第一个 <div> 匹配到最后一个 </div>")

# 非贪婪匹配 — 尽可能少匹配
non_greedy = re.findall(r'<div>(.*?)</div>', html)
print(f"非贪婪匹配结果: {non_greedy}")
print(f"  → 分别匹配每个 <div>...</div> 对")

# 另一个经典例子：HTML 标签属性
html_tag = '<a href="https://example.com" title="链接" class="link">点击</a>'

# 贪婪：匹配 href="..." 后面的一切
greedy_attr = re.search(r'href="(.*)"', html_tag)
if greedy_attr:
    print(f"\n贪婪提取 href: '{greedy_attr.group(1)}'")
    print(f"  → 把 title 和 class 也吞进去了！")

# 非贪婪：只匹配最短的 ""
non_greedy_attr = re.search(r'href="(.*?)"', html_tag)
if non_greedy_attr:
    print(f"非贪婪提取 href: '{non_greedy_attr.group(1)}'")
    print(f"  → 正确提取")

print("\n" + "=" * 60)
print("6. 常用匹配模式实战")
print("=" * 60)

test_cases = {
    "国内手机号": (r'1[3-9]\d{9}', "13812345678", "12345"),
    "IP 地址": (r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', "192.168.1.1", "999.999.999.999"),
    "URL": (r'https?://[\w./?#-]+', "https://example.com/path?a=1", "not a url"),
    "中文": (r'[\u4e00-\u9fff]+', "你好世界", "hello"),
    "身份证号": (r'\d{17}[\dXx]', "110101199001011234", "12345"),
}

for name, (pattern, ok, fail) in test_cases.items():
    r1 = re.search(pattern, ok)
    r2 = re.search(pattern, fail)
    print(f"  {name}: '{ok}' → {'✅' if r1 else '❌'} | '{fail}' → {'✅' if r2 else '❌'}")

print("\n✅ 正则表达式基础演示完成！")
