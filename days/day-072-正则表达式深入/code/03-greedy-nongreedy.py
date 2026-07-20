"""
Day 072 — 贪婪 vs 非贪婪匹配
运行方式：python 03-greedy-nongreedy.py
"""
import re


def main():
    # ========== 1. 基本对比 ==========
    print("=" * 60)
    print("📊 贪婪 vs 非贪婪 基本对比")
    print("=" * 60)

    text = "aabab"

    patterns = [
        ("a*",   "a*?",   "零次或多次"),
        ("a+",   "a+?",   "一次或多次"),
        ("a?",   "a??",   "零次或一次"),
        ("a{2}", "a{2}?", "恰好两次"),
        (".*",   ".*?",   "任意字符零次或多次"),
    ]

    print(f"文本: '{text}'")
    print()

    for greedy, nongreedy, desc in patterns:
        g_result = re.findall(greedy, text)
        n_result = re.findall(nongreedy, text)
        print(f"{desc}:")
        print(f"  贪婪 {greedy:8s} → {g_result}")
        print(f"  非贪婪 {nongreedy:8s} → {n_result}")
        print()

    # ========== 2. HTML 标签匹配 ==========
    print("=" * 60)
    print("🌐 HTML 标签匹配")
    print("=" * 60)

    html = "<div>内容1</div><div>内容2</div>"
    print(f"HTML: '{html}'")
    print()

    # 贪婪匹配
    greedy = re.findall(r'<div>.*</div>', html)
    print(f"贪婪:    {greedy}")
    print(f"  → .* 把整个字符串都匹配了")
    print()

    # 非贪婪匹配
    nongreedy = re.findall(r'<div>.*?</div>', html)
    print(f"非贪婪:  {nongreedy}")
    print(f"  → 每个标签单独匹配")
    print()

    # ========== 3. 引号内容提取 ==========
    print("=" * 60)
    print("💬 引号内容提取")
    print("=" * 60)

    text = '他说"你好"，然后说"再见"'
    print(f"文本: '{text}'")
    print()

    # 贪婪匹配
    greedy = re.findall(r'"(.*)"', text)
    print(f"贪婪:    {greedy}")
    print(f"  → 匹配从第一个引号到最后一个引号的所有内容")
    print()

    # 非贪婪匹配
    nongreedy = re.findall(r'"(.*?)"', text)
    print(f"非贪婪:  {nongreedy}")
    print(f"  → 匹配最近的引号对")
    print()

    # ========== 4. URL 匹配 ==========
    print("=" * 60)
    print("🔗 URL 匹配")
    print("=" * 60)

    url = "https://example.com/path?name=test&value=123"
    print(f"URL: '{url}'")
    print()

    # 贪婪匹配
    greedy_match = re.search(r'https://(.*)', url)
    if greedy_match:
        print(f"贪婪:    {greedy_match.group(1)}")
        print(f"  → .* 会匹配到末尾")
    print()

    # 非贪婪匹配
    nongreedy_match = re.search(r'https://(.*?)(?:\?|$)', url)
    if nongreedy_match:
        print(f"非贪婪:  {nongreedy_match.group(1)}")
        print(f"  → 匹配到第一个 ? 或行尾")
    print()

    # ========== 5. 何时用非贪婪？ ==========
    print("=" * 60)
    print("📝 何时用非贪婪？")
    print("=" * 60)

    print("""
    使用非贪婪的场景：
    1. 匹配引号内的内容（避免匹配整个字符串）
    2. 匹配 HTML/XML 标签（避免跨越多个标签）
    3. 提取 URL 参数（避免匹配到末尾）
    4. 任何需要"最近匹配"的场景

    使用贪婪的场景：
    1. 需要尽可能多地匹配
    2. 匹配整个字符串或行
    3. 简单的文本提取（不需要精确分割）

    记忆技巧：
    - 贪婪 = 贪心 = 尽可能多
    - 非贪婪 = 节制 = 尽可能少
    - 非贪婪 = 贪婪 + ?
    """)

    # ========== 6. 实际应用 ==========
    print("=" * 60)
    print("🎯 实际应用示例")
    print("=" * 60)

    # 6.1 提取日期范围
    text = "活动时间：2024-01-15 至 2024-02-15"
    dates = re.findall(r'\d{4}-\d{2}-\d{2}', text)
    print(f"日期范围: {dates}")

    # 6.2 提取括号内容
    text = "函数调用 func(1, 2, 3) 和另一个 func(4, 5)"
    args = re.findall(r'func\((.*?)\)', text)
    print(f"函数参数: {args}")

    # 6.3 提取嵌套内容（非贪婪的典型场景）
    text = "[[第一层]] [[第二层]] [[第三层]]"
    nested = re.findall(r'\[\[(.*?)\]\]', text)
    print(f"嵌套内容: {nested}")

    # 6.4 清理多余空格
    text = "hello    world     foo"
    cleaned = re.sub(r'\s+', ' ', text)
    print(f"清理空格: '{cleaned}'")


if __name__ == '__main__':
    main()
