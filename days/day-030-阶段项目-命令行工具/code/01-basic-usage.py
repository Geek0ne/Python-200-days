"""
Day 030 — 阶段项目：命令行工具集
======================================================================
基础用法：sys.argv、argparse 基础、简单的 CLI 工具
======================================================================
"""

import sys
import os
import argparse

# ====================================================================
# 1. sys.argv 基础
# ====================================================================
print("=" * 60)
print("1️⃣  sys.argv — 最基础的参数获取")
print("=" * 60)

print(f"  脚本名: {sys.argv[0]}")
print(f"  参数数量: {len(sys.argv) - 1}")
print(f"  参数列表: {sys.argv[1:]}")
print()

# 模拟用户传递参数
print("  🔍 模拟参数解析:")


def parse_with_sysargv(argv_list):
    """手动解析 sys.argv"""
    args = argv_list[1:]  # 跳过脚本名
    options = {'verbose': False, 'output': None}
    positional = []

    i = 0
    while i < len(args):
        if args[i] in ('-v', '--verbose'):
            options['verbose'] = True
        elif args[i] in ('-o', '--output') and i + 1 < len(args):
            options['output'] = args[i + 1]
            i += 1
        elif args[i].startswith('-'):
            print(f"  ⚠️  未知选项: {args[i]}")
        else:
            positional.append(args[i])
        i += 1

    return options, positional


# 测试
test_args = ['script.py', '-v', '--output', 'result.txt', 'file1', 'file2']
opts, pos = parse_with_sysargv(test_args)
print(f"  测试参数: {test_args[1:]}")
print(f"  解析结果:")
print(f"    verbose = {opts['verbose']}")
print(f"    output  = {opts['output']}")
print(f"    位置参数 = {pos}")


# ====================================================================
# 2. argparse 基础
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  argparse — 标准参数解析库")
print("=" * 60)

def argparse_demo():
    """argparse 基本使用演示"""
    parser = argparse.ArgumentParser(
        description='argparse 基础演示',
        epilog='示例: python 01-basic-usage.py Alice -c 3 -v',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # 位置参数
    parser.add_argument('name', type=str, help='你的名字')

    # 可选参数
    parser.add_argument(
        '-c', '--count',
        type=int,
        default=1,
        help='重复次数（默认: 1）'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    parser.add_argument(
        '-l', '--lang',
        choices=['zh', 'en', 'ja'],
        default='zh',
        help='语言（默认: zh）'
    )

    # 解析（使用预设参数演示）
    test_input = ['Alice', '-c', '3', '-v', '-l', 'en']
    args = parser.parse_args(test_input)

    greetings = {
        'zh': '你好',
        'en': 'Hello',
        'ja': 'こんにちは'
    }

    print(f"\n  名称: {args.name}")
    print(f"  次数: {args.count}")
    print(f"  语言: {args.lang} -> {greetings[args.lang]}")
    print(f"  详细: {args.verbose}")
    print()

    for i in range(args.count):
        msg = f"{greetings[args.lang]}, {args.name}!"
        print(f"    {msg}")
        if args.verbose:
            print(f"      (第 {i+1}/{args.count} 次输出)")

argparse_demo()


# ====================================================================
# 3. 文件统计工具 (wc)
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  文件统计工具 — 类 wc 命令")
print("=" * 60)


def wc_count(filename, count_lines=True, count_words=True, count_chars=True):
    """
    统计文件行数、单词数、字符数

    Args:
        filename: 文件名
        count_lines: 是否统计行数
        count_words: 是否统计单词数
        count_chars: 是否统计字符数（含换行符）
    """
    if not os.path.exists(filename):
        return None

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {}
    if count_lines:
        result['lines'] = content.count('\n')
    if count_words:
        result['words'] = len(content.split())
    if count_chars:
        result['chars'] = len(content)
    return result


# 创建测试文件
test_content = """Hello world
Python is great
This is a test file
Learning CLI tools
Day 30 project
"""

with open('/tmp/test_wc.txt', 'w') as f:
    f.write(test_content)

stats = wc_count('/tmp/test_wc.txt')
print(f"  文件: /tmp/test_wc.txt")
print(f"  内容:")
for line in test_content.strip().split('\n'):
    print(f"    │ {line}")
print()
print(f"  行数:  {stats['lines']}")
print(f"  单词数: {stats['words']}")
print(f"  字符数: {stats['chars']}")


# 统计当前目录下的 Python 文件
this_file = __file__
self_stats = wc_count(this_file)
print(f"\n  本文件统计 ({os.path.basename(this_file)}):")
print(f"  行数: {self_stats['lines']}")
print(f"  单词数: {self_stats['words']}")
print(f"  字符数: {self_stats['chars']}")


# ====================================================================
# 4. 文本搜索工具 (grep)
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  文本搜索工具 — 类 grep 命令")
print("=" * 60)


def grep_search(pattern, filename, ignore_case=False, show_line_num=True,
                color_output=False, context_lines=0):
    """
    在文件中搜索文本模式

    Args:
        pattern: 搜索文本
        filename: 文件名
        ignore_case: 忽略大小写
        show_line_num: 显示行号
        color_output: 颜色输出
        context_lines: 上下文的行数

    Returns:
        匹配结果列表
    """
    if not os.path.exists(filename):
        return []

    matches = []
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        if ignore_case:
            found = pattern.lower() in line.lower()
        else:
            found = pattern in line

        if found:
            # 添加上下文
            start = max(0, line_num - 1 - context_lines)
            end = min(len(lines), line_num + context_lines)
            for ctx_line in range(start + 1, end + 1):
                if ctx_line == line_num:
                    marker = ">>"
                else:
                    marker = "  "
                if show_line_num:
                    matches.append(f"{marker} {ctx_line:4d}: {lines[ctx_line-1].rstrip()}")
                else:
                    matches.append(f"{marker} {lines[ctx_line-1].rstrip()}")
            matches.append("---")

    return matches


# 在当前文件中搜索 'print'
results = grep_search('def ', __file__, show_line_num=True, context_lines=0)
print(f"  搜索 'def ' 在 {os.path.basename(__file__)}:")
print(f"  找到 {len(results)} 个匹配")
for r in results[:10]:
    print(f"    {r}")
if len(results) > 10:
    print(f"    ... (还有 {len(results) - 10} 行)")


# ====================================================================
# 5. Python 代码行数统计
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  Python 代码统计工具")
print("=" * 60)


def count_py_lines(root_dir=None):
    """统计 Python 文件的行数（忽略空行和注释）"""
    if root_dir is None:
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 回到 day-030- 目录

    target_dir = root_dir
    total_files = 0
    total_lines = 0
    total_code = 0
    total_comments = 0
    total_blanks = 0

    for fname in os.listdir(target_dir):
        if fname.endswith('.py'):
            filepath = os.path.join(target_dir, fname)
            code_lines = 0
            comment_lines = 0
            blank_lines = 0

            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped:
                        blank_lines += 1
                    elif stripped.startswith('#'):
                        comment_lines += 1
                    elif stripped.startswith('"""') or stripped.startswith("'''"):
                        comment_lines += 1
                    else:
                        code_lines += 1

            total_files += 1
            total_lines += code_lines + comment_lines + blank_lines
            total_code += code_lines
            total_comments += comment_lines
            total_blanks += blank_lines

            print(f"  {fname:<25} {code_lines:4d} 行代码, "
                  f"{comment_lines:2d} 注释, {blank_lines:2d} 空行")

    print(f"  {'='*40}")
    print(f"  总共: {total_files} 个文件, {total_lines} 行")
    print(f"  代码: {total_code}, 注释: {total_comments}, 空行: {total_blanks}")


count_py_lines()

print("\n" + "=" * 60)
print("✅  Day 30 基础用法演示完成!")
print("=" * 60)
