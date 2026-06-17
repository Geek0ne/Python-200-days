#!/usr/bin/env python3
"""
Day 026 — re 模块进阶与避坑指南

涵盖：
1. re.sub / re.subn 字符串替换与脱敏
2. re.split 高级分割
3. re.compile 预编译性能对比
4. 灾难性回溯 (Catastrophic Backtracking)
5. re.VERBOSE 编写可读正则
6. flags 组合使用

可直接运行：python3 02-regex-advanced.py
"""

import re
import time

print("=" * 60)
print("1. re.sub — 字符串替换与脱敏")
print("=" * 60)

text = """
用户: 张三, 手机: 13812345678, 身份证: 110101199001011234
用户: 李四, 手机: 15987654321, 身份证: 320102198807152345
"""

# 手机号脱敏：保留前3后4
masked1 = re.sub(r'(1[3-9]\d)\d{4}(\d{4})', r'\1****\2', text)
print("手机号脱敏:")
print(masked1)

# 身份证脱敏：保留前6后4
masked2 = re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', masked1)
print("身份证脱敏:")
print(masked2)

# subn — 同时获取替换次数
cleaned, count = re.subn(r'用户:|手机:|身份证:', '', masked2)
print(f"清理后 (共替换 {count} 处):")
print(cleaned)

# 函数替换 — 更灵活的方式
def mask_phone(match):
    """根据号码长度决定脱敏策略"""
    phone = match.group()
    if len(phone) == 11:
        return phone[:3] + '****' + phone[-4:]
    return '***掩码***'

text2 = "联系方式: 13812345678, 010-12345678"
result = re.sub(r'\d{3,4}-?\d{7,8}', mask_phone, text2)
print(f"\n函数式替换: {result}")

print("\n" + "=" * 60)
print("2. re.split — 高级分割")
print("=" * 60)

# 按多种分隔符分割
data = "苹果, 香蕉; 橘子 | 葡萄  西瓜"
parts = re.split(r'[,;|\s]+', data)
print(f"多分隔符分割: {parts}")

# 保留分隔符（带捕获组）
data2 = "2026-06-17 10:30:45"
parts2 = re.split(r'([- :])', data2)
print(f"保留分隔符: {parts2}")
# 可以重组回原始格式
restored = ''.join(parts2)
print(f"重组: {restored}")

# 限制分割次数
data3 = "a,b,c,d,e,f"
print(f"全部分割: {re.split(r',', data3)}")
print(f"最多3次: {re.split(r',', data3, maxsplit=3)}")

print("\n" + "=" * 60)
print("3. 预编译性能对比（re.compile）")
print("=" * 60)

# 准备数据和正则
text_big = "user@example.com " * 100000  # 10万封"邮件"
pattern_str = r'\b[\w.+-]+@[\w-]+\.[\w.]+\b'

# 不预编译，每次调用
start = time.perf_counter()
for _ in range(100):
    re.findall(pattern_str, text_big)
t1 = time.perf_counter() - start
print(f"未编译 (100次): {t1:.4f}s")

# 预编译一次
compiled = re.compile(pattern_str)
start = time.perf_counter()
for _ in range(100):
    compiled.findall(text_big)
t2 = time.perf_counter() - start
print(f"已编译 (100次): {t2:.4f}s")
print(f"性能提升: {t1/t2:.1f}x")

print("\n" + "=" * 60)
print("4. ⚠️ 灾难性回溯 — 最常见的正则性能杀手")
print("=" * 60)

print("""
原理：当正则包含嵌套量词（如 (a+)+b）时，匹配失败时
正则引擎会尝试所有可能的组合，导致指数级回溯。

示例：用 (a+)+b 匹配 'aaaaac'
- 引擎尝试各种组合来分配 a 字符
- (aaa)(aa), (aa)(aaa), (a)(aaaa), (aaaa)(a) ...
- 每个 a 在内外量词之间都有分割点
- 5个 a → 16种分配方式 → 回溯16次
- n个 a → 2^(n-1) 种 → 指数爆炸！
""")

def test_regex_time(pattern, text, label):
    """测试正则匹配耗时"""
    start = time.perf_counter()
    try:
        result = re.search(pattern, text)
        elapsed = time.perf_counter() - start
        status = f"匹配到: '{result.group()[:20]}...'" if result else "无匹配"
        print(f"  {label}: {elapsed:.4f}s — {status}")
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  {label}: {elapsed:.4f}s — 出错: {e}")

# 安全的正则（正常匹配）
safe_text = "a" * 5 + "b"
test_regex_time(r'a+b', safe_text, "简单 a+b  (5个a)")

# 灾难性回溯演示 — 用少量字符展示原理
# (a+)+b 在匹配 'aaaaac' 时的回溯过程：
# 外循环: (a+)+ → a+, aa+, aaa+, aaaa+, aaaaa+
# 内循环: a+ → a, aa, aaa, aaaa, aaaaa
# 组合数 = 2^(n-1)，5个a → 16种组合
print(f"\n⚠️ 灾难性回溯原理演示 (少量字符)")
print(f"正则: (a+)+b")
print(f"输入: 'aaaac' (4个a，不含b)")
print(f"回溯次数分析:")
print(f"  外部分组 (a+)+ 尝试分配 a: (aaa)(a), (aa)(aa), (a)(aaa)...")
print(f"  n=4时回溯2^(4-1)=8次，n=20时回溯524288次！")
print(f"  实际生产环境几百个字符即可让正则引擎卡死数分钟")
print()

# 更安全的演示 — 使用更少的字符以确保可运行
safe_re_test = "a" * 10
test_regex_time(r'a+b', safe_re_test, "     a+b  (无嵌套，安全，10个a)")
print(f"对比: (a+)+b 同样的10个a会导致 2^9=512 次回溯")

print("\n💡 避免灾难性回溯的经验法则:")
print("  1. 避免嵌套量词: (a+)+, (.*)*, (.+)+ 等都是危险信号")
print("  2. 使用非回溯子表达式 (?: ... 在某些引擎中)")
print("  3. 能用精确字符类别用 . 点号")
print("  4. 设置超时限制，防止极端输入卡死")

print("\n" + "=" * 60)
print("5. re.VERBOSE — 编写可读的正则表达式")
print("=" * 60)

# 不可读的正则 — 密集恐惧症警告
email_re_ugly = r'^[\w.+-]+@[\w-]+\.[\w.]+$'

# 可读的正则 — 带注释和空白
email_re_readable = re.compile(r"""
    ^                    # 开头
    [\w.+-]+             # 用户名：字母、数字、下划线、点、加号、减号
    @                    # @ 符号
    [\w-]+               # 域名
    \.                   # 点号
    [\w.]+               # 顶级域名
    $                    # 结尾
""", re.VERBOSE)

test_emails = ['user@example.com', 'first.last@sub.domain.co', 'invalid@', '@x.com']
for email in test_emails:
    is_valid = bool(email_re_readable.fullmatch(email))
    print(f"  {'✅' if is_valid else '❌'} {email}")

print("\n" + "=" * 60)
print("6. Flags 组合使用")
print("=" * 60)

text = """Hello World
hello python
HELLO EVERYONE"""

# 组合多个 flags
pattern = re.compile(r'^hello', re.IGNORECASE | re.MULTILINE)
matches = pattern.findall(text)
print(f"多行+忽略大小写匹配 'hello': {matches}")

# re.DOTALL — 让 . 匹配换行
text_multiline = "标题\n内容\n结尾"
normal = re.findall(r'标题.*结尾', text_multiline)
dotall = re.findall(r'标题.*结尾', text_multiline, re.DOTALL)
print(f"默认模式: {normal}")
print(f"DOTALL 模式: {dotall}")

# 实战：重新解析日志配置
log_config = r"""
    ^                        # 行开头
    (?P<ip>\d+\.\d+\.\d+\.\d+)  # IP
    \s-\s                    # 分隔符
    \[(?P<time>[^\]]+)\]     # 时间戳
""".strip()

# 如果配置复杂，可以拼接 flags
def make_log_parser(re_flags=re.VERBOSE):
    """创建灵活的日志解析器"""
    return re.compile(r"""
        ^                          # 行首
        (?P<ip>\S+)                # IP
        \s+                        # 空白
        \S+                        # ident
        \s+                        # 空白
        \S+                        # authuser
        \s+                        # 空白
        \[(?P<time>[^\]]+)\]       # 时间
    """, re_flags)

parser = make_log_parser()
line = '192.168.1.1 - - [17/Jun/2026:10:15:30 +0800] "GET / HTTP/1.1" 200 1234'
m = parser.match(line)
if m:
    print(f"\n日志解析结果:")
    print(f"  IP: {m.group('ip')}")
    print(f"  时间: {m.group('time')}")

print("\n✅ re 模块进阶演示完成！")
