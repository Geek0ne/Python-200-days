"""
Day 072 — 正则引擎原理（NFA vs DFA）
运行方式：python 01-nfa-dfa.py
"""
import re
import time


def main():
    # ========== 1. NFA 回溯机制演示 ==========
    print("=" * 60)
    print("🔬 NFA 回溯机制演示")
    print("=" * 60)

    text = "aab"
    pattern = "a*ab"

    print(f"文本: '{text}'")
    print(f"正则: '{pattern}'")
    print()

    # 手动模拟 NFA 执行过程
    print("NFA 执行过程:")
    print("1. a* 尝试匹配尽可能多的 'a' → 匹配了 'aa'")
    print("2. 接下来要匹配 'a'，当前位置在 'b' → 失败！")
    print("3. 回溯：a* 让出一个 'a'，现在 a* 匹配了 'a'")
    print("4. 接下来匹配 'a'，位置在第二个 'a' → 成功！")
    print("5. 接下来匹配 'b'，位置在 'b' → 成功！")
    print()

    result = re.match(pattern, text)
    print(f"匹配结果: '{result.group()}'")
    print()

    # ========== 2. 回溯导致性能问题 ==========
    print("=" * 60)
    print("⚠️ 回溯导致性能问题（灾难性回溯）")
    print("=" * 60)

    # 简单的正则也可能非常慢
    # (a+)+b 这种嵌套量词会导致指数级回溯
    safe_text = "a" * 25 + "c"  # 不匹配的情况
    safe_pattern = r"(a+)+c"

    print(f"文本长度: {len(safe_text)}")
    print(f"正则: '{safe_pattern}'")
    print()

    start = time.time()
    result = re.match(safe_pattern, safe_text)
    elapsed = time.time() - start

    print(f"匹配结果: {'匹配' if result else '不匹配'}")
    print(f"耗时: {elapsed:.4f}秒")
    print()

    if elapsed > 1:
        print("⚠️ 警告：这个正则可能导致灾难性回溯！")
        print("   原因：(a+)+ 会产生大量回溯路径")
        print("   解决：使用 atomic group 或重新设计正则")
    # 输出：耗时可能非常长（几秒甚至几分钟）
    # 注意：在实际运行中，这个正则可能真的需要很长时间
    # 这里设置了安全的文本长度（25个a），如果太长请减小

    # ========== 3. NFA 支持的功能 ==========
    print("\n" + "=" * 60)
    print("✅ NFA 支持的功能（DFA 不支持）")
    print("=" * 60)

    text = "hello hello world"

    # 3.1 贪婪/非贪婪匹配
    print("\n1. 贪婪/非贪婪匹配:")
    greedy = re.findall(r'.*o', text)     # 贪婪：尽可能多
    nongreedy = re.findall(r'.*?o', text)  # 非贪婪：尽可能少
    print(f"   贪婪: {greedy}")
    print(f"   非贪婪: {nongreedy}")

    # 3.2 反向引用
    print("\n2. 反向引用（捕获组）:")
    pattern = r"(\b\w+\b)\s+\1"
    result = re.search(pattern, text)
    if result:
        print(f"   重复的单词: '{result.group(1)}'")

    # 3.3 零宽断言
    print("\n3. 零宽断言:")
    price_text = "$100 and $200"
    result = re.findall(r'(?<=\$)\d+', price_text)
    print(f"   正向后顾提取价格: {result}")

    # ========== 4. DFA vs NFA 对比 ==========
    print("\n" + "=" * 60)
    print("📊 DFA vs NFA 对比总结")
    print("=" * 60)

    comparison = """
    ┌─────────────────┬──────────────────┬──────────────────┐
    │ 特性            │ NFA (Python re)  │ DFA              │
    ├─────────────────┼──────────────────┼──────────────────┤
    │ 执行模型        │ 表达式导向        │ 文本导向          │
    │ 贪婪/非贪婪     │ ✅ 支持          │ ❌ 不支持        │
    │ 反向引用        │ ✅ 支持          │ ❌ 不支持        │
    │ 零宽断言        │ ✅ 支持          │ ❌ 不支持        │
    │ 回溯            │ ✅ 有            │ ❌ 无            │
    │ 最坏时间复杂度  │ 指数级           │ 线性             │
    │ 适用场景        │ 复杂模式匹配      │ 高性能简单匹配    │
    └─────────────────┴──────────────────┴──────────────────┘
    """
    print(comparison)

    # ========== 5. 安全的正则写法 ==========
    print("=" * 60)
    print("🛡️ 安全的正则写法")
    print("=" * 60)

    # ❌ 危险写法
    dangerous_pattern = r"(a+)+b"

    # ✅ 安全写法1：使用原子组（需要 regex 模块）
    # import regex
    # safe_pattern1 = regex.compile(r"(?>a+)+b")

    # ✅ 安全写法2：重新设计正则
    safe_pattern2 = r"a+b"  # 简单的 a+ 即可

    # ✅ 安全写法3：添加超时
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("正则匹配超时")

    # 设置 1 秒超时
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(1)  # 1秒超时

    try:
        text = "a" * 25 + "c"
        result = re.match(safe_pattern2, text)
        print(f"安全正则匹配: {'匹配' if result else '不匹配'}")
    except TimeoutError:
        print("⚠️ 正则匹配超时！")
    finally:
        signal.alarm(0)  # 取消超时

    print("\n💡 建议：")
    print("1. 避免嵌套量词：(a+)+ → a+")
    print("2. 使用具体字符类：[a-z] 比 . 更快")
    print("3. 模块级别编译正则：compiled = re.compile(pattern)")
    print("4. 对用户输入的正则设置超时")


if __name__ == '__main__':
    main()
