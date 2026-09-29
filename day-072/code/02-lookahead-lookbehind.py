"""
Day 072 — 前瞻与后顾断言
运行方式：python 02-lookahead-lookbehind.py
"""
import re


def main():
    text = "price: $100, quantity: 50, total: $200"

    # ========== 1. 四种断言 ==========
    print("=" * 60)
    print("🔍 四种断言演示")
    print("=" * 60)
    print(f"文本: '{text}'")
    print()

    # 1. 正向前瞻 (?=...)
    # 后面必须跟着指定内容
    print("1. 正向前瞻 (?=...):")
    print("   查找后面跟着空格的数字")
    result = re.findall(r'\d+(?=\s)', text)
    print(f"   结果: {result}")
    print()

    # 2. 负向前瞻 (?!...)
    # 后面不能跟着指定内容
    print("2. 负向前瞻 (?!...):")
    print("   查找后面不是逗号的数字")
    result = re.findall(r'\d+(?!.*\d+)', text)  # 用更精确的模式
    result = re.findall(r'\d+(?!$)', text)  # 后面不是行尾的数字
    print(f"   结果: {result}")
    print()

    # 3. 正向后顾 (?<=...)
    # 前面必须有指定内容
    print("3. 正向后顾 (?<=...):")
    print("   查找前面是 $ 的数字")
    result = re.findall(r'(?<=\$)\d+', text)
    print(f"   结果: {result}")
    print()

    # 4. 负向后顾 (?<!...)
    # 前面不能有指定内容
    print("4. 负向后顾 (?<!...):")
    print("   查找前面不是 $ 的数字")
    result = re.findall(r'(?<!\$)\d+', text)
    print(f"   结果: {result}")
    print()

    # ========== 2. 实用场景：密码验证 ==========
    print("=" * 60)
    print("🔐 密码强度验证（使用断言）")
    print("=" * 60)

    def validate_password(password):
        """验证密码强度"""
        checks = [
            (r'(?=.*[a-z])', '小写字母'),
            (r'(?=.*[A-Z])', '大写字母'),
            (r'(?=.*\d)', '数字'),
            (r'(?=.*[!@#$%^&*])', '特殊字符'),
        ]

        passed = []
        failed = []

        for pattern, name in checks:
            if re.search(pattern, password):
                passed.append(name)
            else:
                failed.append(name)

        return passed, failed

    passwords = [
        "abc",
        "abcdefgh",
        "Abcdefg1",
        "Abcdefg1!",
    ]

    for pwd in passwords:
        passed, failed = validate_password(pwd)
        if failed:
            print(f"❌ '{pwd}': 缺少 {', '.join(failed)}")
        else:
            print(f"✅ '{pwd}': 通过所有检查 ({', '.join(passed)})")

    print()

    # ========== 3. 提取 HTML 内容 ==========
    print("=" * 60)
    print("🌐 提取 HTML 内容（使用断言）")
    print("=" * 60)

    html = '<div class="content">Hello World</div>'

    # 提取标签内的文本（不含标签）
    # 使用后顾和前瞻断言，不消耗字符
    text_content = re.search(r'(?<=>)[^<]+(?=</)', html)
    if text_content:
        print(f"标签内容: '{text_content.group()}'")

    # 提取属性值
    attr_value = re.search(r'(?<=class=")[^"]+', html)
    if attr_value:
        print(f"class 属性: '{attr_value.group()}'")

    print()

    # ========== 4. 高级用法 ==========
    print("=" * 60)
    print("🎯 高级用法")
    print("=" * 60)

    # 4.1 组合使用
    text = "error: file not found, warning: disk full"
    # 提取 error 后面的内容
    result = re.search(r'(?<=error: )\w[\w ]+', text)
    if result:
        print(f"错误信息: '{result.group()}'")

    # 4.2 多个断言
    text = "2024-01-15 is a Monday"
    # 提取日期部分（假设格式为 YYYY-MM-DD）
    result = re.search(r'(?<=\d{4}-\d{2}-)\d{2}', text)
    if result:
        print(f"日期中的日: '{result.group()}'")

    # 4.3 零宽匹配技巧
    text = "abc123def456"
    # 在数字前插入空格
    result = re.sub(r'(?=\d)', ' ', text)
    print(f"数字前加空格: '{result}'")

    # 在字母后插入空格
    result = re.sub(r'([a-zA-Z])(?=[0-9])', r'\1 ', text)
    print(f"字母后加空格: '{result}'")

    print()

    # ========== 5. 注意事项 ==========
    print("=" * 60)
    print("⚠️ 注意事项")
    print("=" * 60)

    print("""
    1. 正向/负向前瞻：(?=...) (?!...)
       - 检查后面的内容，不消耗字符
       - 可以使用任意长度的模式

    2. 正向/负向后顾：(?<=...) (?<!...)
       - 检查前面的内容，不消耗字符
       - ⚠️ Python 中必须是固定长度！
       - 不能用 * + ? 等量词

    3. 常见错误：
       - (?<=\$)\d+ ✅ 正确（固定长度）
       - (?<=\$*)\d+ ❌ 错误（可变长度）
       - (?<=\$+\d*)\d+ ❌ 错误（可变长度）

    4. 替代方案：
       - 如果后顾断言有限制，可以用捕获组
       - 或者分两步匹配
    """)


if __name__ == '__main__':
    main()
