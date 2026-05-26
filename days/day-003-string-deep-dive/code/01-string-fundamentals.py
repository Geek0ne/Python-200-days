#!/usr/bin/env python3
"""
Day 003 — 字符串深入：基础操作大全
==============================

涵盖：不可变性、切片、格式化、转义字符、原始字符串
可直接运行：python3 01-string-fundamentals.py
"""

# ============================================================
# 第一部分：字符串不可变性
# ============================================================

print("=" * 60)
print("【第一部分】字符串不可变性 — 内存探秘")
print("=" * 60)

s1 = "hello"
print(f"初始字符串: {s1}")
print(f"初始内存地址: {id(s1)}")

# "修改"字符串 — 实际上创建了新对象
s1 = s1 + " world"
print(f"\n执行 s1 = s1 + \" world\" 之后:")
print(f"s1 = {s1}")
print(f"新内存地址: {id(s1)}")  # 地址变化了！

# 证明不可变性
try:
    s1[0] = "H"  # 这会抛出 TypeError
except TypeError as e:
    print(f"\n尝试修改不可变对象: {e}")

# 字符串驻留（interning）演示
print("\n--- 字符串驻留 ---")
a = "python_intern"
b = "python_intern"
print(f"a = 'python_intern', b = 'python_intern'")
print(f"a is b: {a is b}")            # True（驻留优化）

# 运行时生成的字符串可能不驻留
c = "".join(["python", "_", "intern"])
print(f"\nc = ''.join(['python', '_', 'intern'])")
print(f"c = {c!r}")
print(f"a == c: {a == c}")            # True（值相等）
print(f"a is c: {a is c}")            # 可能是 False（不一定驻留）

# 小整数驻留
print("\n--- 小整数驻留 ---")
x, y = 256, 256
print(f"x = 256, y = 256, x is y: {x is y}")  # True
x, y = 257, 257
print(f"x = 257, y = 257, x is y: {x is y}")  # False


# ============================================================
# 第二部分：切片操作
# ============================================================

print("\n" + "=" * 60)
print("【第二部分】字符串切片 — 花式提取子串")
print("=" * 60)

s = "Python Programming"
length = len(s)
print(f"字符串: \"{s}\"")
print(f"长度: {length}")
print()

# 基础切片
print("--- 基础切片 ---")
print(f"s[0:6]     = {s[0:6]!r}")       # "Python"
print(f"s[7:18]    = {s[7:18]!r}")      # "Programming"
print(f"s[:6]      = {s[:6]!r}")        # 从开头到索引6
print(f"s[7:]      = {s[7:]!r}")        # 从索引7到末尾
print(f"s[:]       = {s[:]!r}")         # 完整复制
print()

# 负数索引
print("--- 负数索引 ---")
print(f"s[-1]      = {s[-1]!r}")        # 最后一个字符
print(f"s[-3:]     = {s[-3:]!r}")       # 后三个字符
print(f"s[:-7]     = {s[:-7]!r}")       # 去掉后七个
print()

# 步进切片
print("--- 步进切片 ---")
print(f"s[::2]     = {s[::2]!r}")       # 每隔一个取一个
print(f"s[::-1]    = {s[::-1]!r}")      # 反转 🔥
print(f"s[::-2]    = {s[::-2]!r}")      # 反转后每隔一个
print()

# 切片边界测试
print("--- 边界测试 ---")
print(f"s[0:100]   = {s[0:100]!r}")     # 超出范围不报错
print(f"s[100:200] = {s[100:200]!r}")   # 空字符串
print(f"s[0:0]     = {s[0:0]!r}")       # 空字符串
print()

# 实用切片技巧
print("--- 实用技巧 ---")
email = "alice@example.com"
print(f"邮箱: {email}")
username = email[:email.index("@")]
domain = email[email.index("@") + 1:]
print(f"用户名: {username}")
print(f"域名: {domain}")

# slice() 对象
sl = slice(1, 10, 2)
print(f"\n手动创建 slice 对象: {sl}")
print(f"s[{sl}] = {s[sl]!r}")


# ============================================================
# 第三部分：字符串拼接性能对比
# ============================================================

print("\n" + "=" * 60)
print("【第三部分】字符串拼接 — 好方法 vs 坏方法")
print("=" * 60)

import time

# 坏方法：使用 + 
def bad_concat(n: int) -> str:
    result = ""
    for i in range(n):
        result += str(i)
    return result

# 好方法：使用列表 + join
def good_concat(n: int) -> str:
    parts = [str(i) for i in range(n)]
    return "".join(parts)

n = 50000
print(f"拼接 {n} 个数字...")

start = time.perf_counter()
bad_result = bad_concat(n)
bad_time = time.perf_counter() - start
print(f"  + 拼接: {bad_time:.4f} 秒")

start = time.perf_counter()
good_result = good_concat(n)
good_time = time.perf_counter() - start
print(f"  join拼接: {good_time:.4f} 秒")

# 验证结果一致
print(f"\n结果相同: {bad_result == good_result}")


# ============================================================
# 第四部分：字符串格式化三剑客
# ============================================================

print("\n" + "=" * 60)
print("【第四部分】字符串格式化 — 三种方式大比拼")
print("=" * 60)

name = "Alice"
age = 25
score = 92.5
city = "Beijing"

# 1. % 格式化（旧式）
print("--- % 格式化 ---")
print("姓名: %s, 年龄: %d, 城市: %s" % (name, age, city))
print("分数: %.1f, 分数(两位): %.2f" % (score, score))
print("十六进制: %x, 八进制: %o" % (255, 255))
print("科学计数: %e" % (12345.6789))

# 2. str.format()
print("\n--- str.format() ---")
print("姓名: {}, 年龄: {}, 城市: {}".format(name, age, city))
print("分数: {:.2f}".format(score))
print("右对齐: {:>15}".format(name))
print("左对齐: {:<15}".format(name))
print("居中: {:^15}".format(name))
print("百分比: {:.1%}".format(0.856))
print("二进制: {:b}, 补零: {:08b}".format(42, 42))

# 3. f-string（推荐）
print("\n--- f-string ---")
print(f"姓名: {name}, 年龄: {age}")
print(f"分数: {score:.1f}")
print(f"明年 {name} {age + 1} 岁")
print(f"{name = }, {age = }")  # Python 3.8+ 调试输出
print(f"二进制: {255:#b}, 十六进制: {255:#x}")

# 千分位分隔
big_num = 1234567890
print(f"大数: {big_num:,}")
print(f"浮点千分位: {1234567.89:,.2f}")

# 嵌套格式化
precision = 3
pi = 3.1415926535
print(f"π 保留 {precision} 位: {pi:.{precision}f}")

# 多行 f-string
info = (
    f"姓名: {name}\n"
    f"年龄: {age}\n"
    f"分数: {score}"
)
print(f"\n多行信息:\n{info}")


# ============================================================
# 第五部分：转义字符与原始字符串
# ============================================================

print("\n" + "=" * 60)
print("【第五部分】转义字符与原始字符串")
print("=" * 60)

print("--- 转义字符 ---")
print("换行符: 第一行\n第二行")
print("制表符: 列1\t列2\t列3")
print("引号: 他说：\"Python 很有趣\"")
print("反斜杠: C:\\Users\\Alice\\Documents")

# Unicode 字符
print("\n--- Unicode 转义 ---")
print("\u4e2d\u6587")             # 中文
print("\U0001F600")                # 笑脸 emoji
print("\N{Grinning Face}")         # 同样的笑脸
print("\N{SNOWMAN}")               # ☃
print("\N{PEACE SYMBOL}")          # ☮

# 原始字符串
print("\n--- 原始字符串 ---")
normal_path = "C:\\Users\\name"       # \n 被转义为换行
raw_path = r"C:\Users\name"         # 保持原样
print(f"普通字符串: {normal_path}")
print(f"原始字符串: {raw_path}")

# 正则表达式中的原始字符串
import re
text = "价格是 19.99 美元，折扣价是 14.50 美元"
# 使用原始字符串匹配浮点数
prices = re.findall(r"\d+\.\d+", text)
print(f"\n正则提取价格: {prices}")

# 三引号多行字符串
print("\n--- 三引号多行字符串 ---")
multiline = """这是一个
跨越多行
的字符串
"""
print(multiline)

# 三引号 + 原始字符串 = 无敌
raw_multiline = r"""C:\Users\Alice\Documents
C:\Users\Bob\Desktop
C:\Users\Charlie\Downloads"""
print(raw_multiline)


# ============================================================
# 第六部分：字符串内置方法大全
# ============================================================

print("=" * 60)
print("【第六部分】字符串内置方法速查")
print("=" * 60)

s = "  Hello World!  "

# 大小写
print("--- 大小写转换 ---")
print(f"upper:     {s.upper()!r}")
print(f"lower:     {s.lower()!r}")
print(f"capitalize: {s.capitalize()!r}")
print(f"title:     {s.title()!r}")
print(f"swapcase:  {s.swapcase()!r}")

# 查找替换
print("\n--- 查找与替换 ---")
text = "hello world, hello python"
print(f"find 'hello': {text.find('hello')}")
print(f"rfind 'hello': {text.rfind('hello')}")
print(f"count 'hello': {text.count('hello')}")
print(f"startswith 'hello': {text.startswith('hello')}")
print(f"endswith 'python': {text.endswith('python')}")
print(f"replace 'hello' → 'hi': {text.replace('hello', 'hi')}")
print(f"replace x1: {text.replace('hello', 'hi', 1)}")

# 拆分
print("\n--- 拆分与拼接 ---")
csv = "apple,banana,orange,grape"
print(f"split: {csv.split(',')}")
print(f"split x2: {csv.split(',', 2)}")
print(f"rsplit x2: {csv.rsplit(',', 2)}")

user_info = "alice:password123"
print(f"partition: {user_info.partition(':')}")
print(f"rpartition: {user_info.rpartition(':')}")

# 空白处理
print(f"\nstrip:   {s.strip()!r}")
print(f"lstrip:  {s.lstrip()!r}")
print(f"rstrip:  {s.rstrip()!r}")

dots = "...test..."
print(f"strip '.': {dots.strip('.')!r}")

print(f"\ncenter(20): {s.center(20)!r}")
print(f"ljust(20):  {s.ljust(20)!r}")
print(f"rjust(20):  {s.rjust(20)!r}")
print(f"zfill(10):  {'42'.zfill(10)!r}")

# 判断方法
print("\n--- 判断方法 ---")
tests = ["hello", "123", "abc123", "  ", "Hello", "你好"]
for t in tests:
    print(f"{t!r:>12} → isalpha={t.isalpha()}, isdigit={t.isdigit()}, "
          f"isalnum={t.isalnum()}, isspace={t.isspace()}")

# 格式化对齐
print("\n--- 对齐输出 ---")
header = f"{'商品':<10}{'单价':>8}{'数量':>6}{'小计':>8}"
print(header)
print("-" * 32)
for item, price, qty in [("苹果", 5.5, 3), ("香蕉", 3.0, 5), ("西瓜", 12.0, 1)]:
    print(f"{item:<10}{price:>8.1f}{qty:>6}{price * qty:>8.1f}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("✅ 所有基础示例运行完成！")
    print("=" * 60)
