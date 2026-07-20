"""
Day 072 — re.compile 与性能优化
运行方式：python 04-re-compile.py
"""
import re
import time


def main():
    # ========== 1. re.compile 基础 ==========
    print("=" * 60)
    print("⚡ re.compile 基础用法")
    print("=" * 60)

    # 方法1：不使用 compile
    text = "hello world"
    result1 = re.findall(r'\w+', text)
    print(f"不 compile: {result1}")

    # 方法2：使用 compile
    pattern = re.compile(r'\w+')
    result2 = pattern.findall(text)
    print(f"使用 compile: {result2}")

    # 方法3：模块级别编译（推荐）
    # 在文件顶部定义常量
    WORD_PATTERN = re.compile(r'\w+')
    result3 = WORD_PATTERN.findall(text)
    print(f"模块级别: {result3}")
    print()

    # ========== 2. 性能对比 ==========
    print("=" * 60)
    print("⏱️ 性能对比")
    print("=" * 60)

    text = "hello" * 10000  # 重复 10000 次
    pattern_str = r"(hello\s*)+"

    # 方法1：不使用 compile（每次调用都重新编译）
    start = time.time()
    for _ in range(1000):
        re.findall(pattern_str, text)
    no_compile = time.time() - start

    # 方法2：使用 compile（编译一次，多次使用）
    compiled = re.compile(pattern_str)
    start = time.time()
    for _ in range(1000):
        compiled.findall(text)
    with_compile = time.time() - start

    print(f"不 compile: {no_compile:.4f}s")
    print(f"使用 compile: {with_compile:.4f}s")
    if with_compile > 0:
        print(f"性能提升: {no_compile / with_compile:.2f}x")
    print()

    # ========== 3. 最佳实践 ==========
    print("=" * 60)
    print("📝 最佳实践")
    print("=" * 60)

    # 模块级别编译正则（常量）
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

    # 测试
    print(f"邮箱验证 'test@example.com': {validate_email('test@example.com')}")
    print(f"邮箱验证 'invalid': {validate_email('invalid')}")
    print(f"提取手机号 '联系我：13812345678': {extract_phones('联系我：13812345678')}")
    print(f"提取 URL '访问 https://example.com': {extract_urls('访问 https://example.com')}")
    print()

    # ========== 4. 性能优化技巧 ==========
    print("=" * 60)
    print("🚀 性能优化技巧")
    print("=" * 60)

    # 技巧1：在循环中使用 compile
    print("\n技巧1：在循环中使用 compile")

    text_list = ["hello world", "foo bar", "test case"] * 100

    # ❌ 慢
    start = time.time()
    results1 = []
    for text in text_list:
        results1.extend(re.findall(r'\w+', text))
    time1 = time.time() - start

    # ✅ 快
    compiled = re.compile(r'\w+')
    start = time.time()
    results2 = []
    for text in text_list:
        results2.extend(compiled.findall(text))
    time2 = time.time() - start

    print(f"  不 compile: {time1:.4f}s")
    print(f"  使用 compile: {time2:.4f}s")

    # 技巧2：使用具体字符类
    print("\n技巧2：使用具体字符类")

    text = "hello123world456"

    # ❌ 慢：. 匹配任意字符
    start = time.time()
    for _ in range(10000):
        re.findall(r'.*email.*', text)
    time1 = time.time() - start

    # ✅ 快：用具体字符类
    start = time.time()
    for _ in range(10000):
        re.findall(r'[a-zA-Z0-9@.]*email[a-zA-Z0-9@.]*', text)
    time2 = time.time() - start

    print(f"  使用 . : {time1:.4f}s")
    print(f"  使用具体字符类: {time2:.4f}s")

    # 技巧3：使用 re.VERBOSE 写复杂的正则
    print("\n技巧3：使用 re.VERBOSE")

    email_regex = re.compile(r"""
        ^                   # 字符串开始
        [a-zA-Z0-9._%+-]+  # 用户名部分
        @                   # @ 符号
        [a-zA-Z0-9.-]+     # 域名
        \.                  # 点
        [a-zA-Z]{2,}        # 顶级域名
        $                   # 字符串结束
    """, re.VERBOSE)

    print(f"  复杂正则验证 'test@example.com': {bool(email_regex.match('test@example.com'))}")

    print("\n" + "=" * 60)
    print("💡 总结")
    print("=" * 60)
    print("""
    1. 重复使用的正则一定要 compile
    2. 在模块级别编译为常量
    3. 避免在循环中使用 re 函数
    4. 使用具体字符类而非 .
    5. 复杂正则用 re.VERBOSE 提高可读性
    6. Python 内部有正则缓存（最多512个），简单场景不 compile 也可以
    """)


if __name__ == '__main__':
    main()
