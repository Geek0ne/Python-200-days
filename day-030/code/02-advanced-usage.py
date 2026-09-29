"""
Day 030 — 阶段项目：命令行工具
======================================================================
进阶用法：argparse 子命令、文件查找工具、JSON 格式化、颜色输出
======================================================================
"""

import argparse
import os
import json
import sys
from pathlib import Path
from datetime import datetime

# ====================================================================
# 1. argparse 子命令 — Git 风格 CLI
# ====================================================================
print("=" * 60)
print("1️⃣  Git 风格子命令")
print("=" * 60)


def build_git_style_cli():
    """构建 git 风格的多命令 CLI（演示版）"""
    parser = argparse.ArgumentParser(
        description='mytools — 实用命令行工具集',
        epilog='示例: mytools wc file.txt\n'
               '       mytools grep pattern file.txt -i',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest='command',
        help='可用命令 (使用 mytools <command> --help 查看详情)',
        required=True,
    )

    # ---- wc 子命令 ----
    wc_parser = subparsers.add_parser('wc', help='统计文件行数/单词数/字符数')
    wc_parser.add_argument('file', help='文件名')
    wc_parser.add_argument('-l', '--lines', action='store_true', help='只统计行数')
    wc_parser.add_argument('-w', '--words', action='store_true', help='只统计单词数')
    wc_parser.add_argument('-c', '--chars', action='store_true', help='只统计字符数')

    # ---- grep 子命令 ----
    grep_parser = subparsers.add_parser('grep', help='搜索文本')
    grep_parser.add_argument('pattern', help='搜索模式')
    grep_parser.add_argument('file', help='文件名')
    grep_parser.add_argument('-i', '--ignore-case', action='store_true', help='忽略大小写')
    grep_parser.add_argument('-n', '--line-number', action='store_true', help='显示行号')

    # ---- find 子命令 ----
    find_parser = subparsers.add_parser('find', help='查找文件')
    find_parser.add_argument('root', nargs='?', default='.', help='根目录 (默认: 当前目录)')
    find_parser.add_argument('--name', help='文件名模式')
    find_parser.add_argument('--type', choices=['f', 'd'], help='类型: f=文件, d=目录')
    find_parser.add_argument('--size', help='大小过滤: +100M, -1K')

    # ---- json-fmt 子命令 ----
    json_parser = subparsers.add_parser('json-fmt', help='JSON 格式化')
    json_parser.add_argument('input', nargs='?', help='JSON 字符串或文件路径')
    json_parser.add_argument('--indent', type=int, default=2, help='缩进空格数')
    json_parser.add_argument('--sort', action='store_true', help='按键排序')

    # ---- format 子命令 ----
    fmt_parser = subparsers.add_parser('format', help='格式化输出')
    fmt_parser.add_argument('--date', help='日期格式示例')
    fmt_parser.add_argument('--size', type=int, help='文件大小（字节）')

    # 模拟测试
    test_commands = [
        ['wc', 'test.txt', '-l'],
        ['grep', 'hello', 'test.txt', '-i', '-n'],
        ['find', '.', '--name', '*.py', '--type', 'f'],
        ['json-fmt', '{"a":1,"b":2}', '--indent', '4'],
    ]

    print("  构建的子命令树:")
    for sub_name, sub_parser in subparsers.choices.items():
        print(f"    {sub_name:<10} - {sub_parser.description}")
    print()

    print("  模拟子命令测试:")
    for cmd in test_commands:
        args = parser.parse_args(cmd)
        print(f"    $ mytools {' '.join(cmd)}")
        print(f"      → command={args.command}, args={args}")

    return parser


build_git_style_cli()


# ====================================================================
# 2. 文件查找工具 (find)
# ====================================================================
print("\n" + "=" * 60)
print("2️⃣  文件查找工具 — 类 find 命令")
print("=" * 60)


def find_files(root_dir='.', name_pattern=None, file_type=None,
               min_size=None, max_size=None, max_depth=None,
               follow_symlinks=False):
    """
    递归查找文件

    Args:
        root_dir: 根目录
        name_pattern: 文件名模式（支持 glob）
        file_type: 'f' 文件或 'd' 目录
        min_size: 最小字节数
        max_size: 最大字节数
        max_depth: 最大递归深度
        follow_symlinks: 是否追踪符号链接

    Returns:
        匹配的文件路径列表
    """
    results = []
    root = Path(root_dir)

    if not root.exists():
        return results

    def _walk(path, depth=0):
        if max_depth is not None and depth > max_depth:
            return

        try:
            entries = list(path.iterdir())
        except PermissionError:
            return

        for entry in entries:
            # 文件类型过滤
            is_file = entry.is_file()
            is_dir = entry.is_dir()

            if file_type == 'f' and not is_file:
                continue
            if file_type == 'd' and not is_dir:
                continue

            # 文件名模式过滤
            if name_pattern:
                if not entry.match(name_pattern):
                    continue

            # 文件大小过滤
            if min_size is not None or max_size is not None:
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = None

                if is_file and size is not None:
                    if min_size is not None and size < min_size:
                        continue
                    if max_size is not None and size > max_size:
                        continue

            results.append(entry)

            # 递归子目录
            if is_dir:
                _walk(entry, depth + 1)

    _walk(root)
    return results


# 在当前 day 目录下查找
current_dir = Path(__file__).parent
print(f"  当前目录: {current_dir}")

# 查找所有 .py 文件
py_files = find_files(str(current_dir), name_pattern='*.py', file_type='f')
print(f"\  找到 {len(py_files)} 个 Python 文件:")
for f in py_files:
    size = f.stat().st_size
    print(f"    {f.name:<25} {size:>6} bytes")

# 查找大于 1KB 的文件
large_files = find_files(str(current_dir), min_size=1024)
print(f"\n  大文件 (>1KB): {len(large_files)} 个")
for f in large_files:
    size = f.stat().st_size
    print(f"    {f.name:<25} {size:>6} bytes")


# ====================================================================
# 3. JSON 格式化工具
# ====================================================================
print("\n" + "=" * 60)
print("3️⃣  JSON 格式化工具")
print("=" * 60)


def json_format_tool(input_data, indent=2, sort_keys=False, compact=False):
    """
    JSON 格式化工具

    Args:
        input_data: JSON 字符串
        indent: 缩进空格数
        sort_keys: 是否按键排序
        compact: 紧凑模式（无缩进）
    """
    try:
        data = json.loads(input_data)
        if compact:
            return json.dumps(data, ensure_ascii=False)
        return json.dumps(data, indent=indent, sort_keys=sort_keys,
                          ensure_ascii=False)
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析错误: {e}"
    except Exception as e:
        return f"❌ 错误: {e}"


# 测试 JSON 格式化
test_json = '{"name":"Python","version":3.12,"features":["simple","elegant","powerful"],"nested":{"level1":{"level2":42,"list":[1,2,3]}}}'

print(f"  原始 JSON:")
print(f"    {test_json}")
print()

formatted = json_format_tool(test_json, indent=2, sort_keys=True)
print(f"  格式化后:")
for line in formatted.split('\n'):
    print(f"    {line}")

# 紧凑模式
compact = json_format_tool(test_json, compact=True)
print(f"\n  紧凑模式: {compact}")

# 行内检缩
inline = json_format_tool(test_json, indent=4)
print(f"\n  缩进=4:")
for line in inline.split('\n')[:5]:
    print(f"    {line}")
print("    ...")


# ====================================================================
# 4. 文件操作工具
# ====================================================================
print("\n" + "=" * 60)
print("4️⃣  文件批量操作工具")
print("=" * 60)


def batch_rename(directory, pattern, replacement, dry_run=True):
    """
    批量重命名文件

    Args:
        directory: 目录路径
        pattern: 要替换的模式
        replacement: 替换后的字符串
        dry_run: 仅预览不执行
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"  目录不存在: {directory}")
        return

    renamed = 0
    for path in dir_path.iterdir():
        if path.is_file() and pattern in path.name:
            new_name = path.name.replace(pattern, replacement)
            new_path = path.parent / new_name
            if dry_run:
                print(f"  [预览] {path.name} → {new_name}")
            else:
                path.rename(new_path)
                print(f"  [重命名] {path.name} → {new_name}")
            renamed += 1

    if renamed == 0:
        print(f"  (没有找到包含 '{pattern}' 的文件)")
    else:
        print(f"  {'[预览]' if dry_run else '[完成]'} 共处理 {renamed} 个文件")


# 创建测试文件
test_dir = Path('/tmp/batch_rename_test')
test_dir.mkdir(exist_ok=True)
for i in range(5):
    (test_dir / f"report_2024_{i+1}.txt").write_text("test")
for i in range(3):
    (test_dir / f"data_backup_{i+1}.csv").write_text("test")

print(f"测试目录: {test_dir}")
batch_rename(str(test_dir), "report_", "annual_report_", dry_run=True)

print(f"\n  实际执行重命名:")
batch_rename(str(test_dir), "report_", "annual_report_", dry_run=False)


# ====================================================================
# 5. 格式转换工具
# ====================================================================
print("\n" + "=" * 60)
print("5️⃣  格式转换工具")
print("=" * 60)


def human_readable_size(size_bytes):
    """将字节转换为可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_timestamp(timestamp, fmt='%Y-%m-%d %H:%M:%S'):
    """格式化时间戳"""
    return datetime.fromtimestamp(timestamp).strftime(fmt)


# 测试格式转换
sizes = [500, 2048, 1048576, 1073741824, 1099511627776]
print(f"  文件大小格式化:")
for s in sizes:
    print(f"    {s:>15,} bytes → {human_readable_size(s)}")

# 当前时间
print(f"\n  时间格式化:")
now = datetime.now()
print(f"    当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"    日期:     {now.strftime('%Y/%m/%d')}")
print(f"    ISO:      {now.isoformat()}")

print(f"\n  当前文件信息:")
this_file = Path(__file__)
stat = this_file.stat()
print(f"    文件名:   {this_file.name}")
print(f"    大小:     {human_readable_size(stat.st_size)}")
print(f"    修改时间: {format_timestamp(stat.st_mtime)}")
print(f"    创建时间: {format_timestamp(stat.st_ctime)}")


# ====================================================================
# 6. argparse 文件参数类型
# ====================================================================
print("\n" + "=" * 60)
print("6️⃣  argparse 文件类型与类型自定义")
print("=" * 60)

parser = argparse.ArgumentParser(description='argparse 文件类型演示', add_help=False)

# FileType 自动处理文件打开/关闭
parser.add_argument('--input', type=argparse.FileType('r'),
                    help='输入文件')
parser.add_argument('--output', type=argparse.FileType('w'),
                    help='输出文件')

# 自定义类型函数
def positive_int(value):
    """验证正整数"""
    try:
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                f"{value} 不是正整数")
        return ivalue
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{value} 不是有效的整数")


parser.add_argument('--count', type=positive_int, default=1,
                    help='计数（必须是正整数）')
parser.add_argument('--mode', choices=['simple', 'detailed', 'debug'],
                    default='simple', help='运行模式')

# 演示
test_args = ['--count', '5', '--mode', 'debug']
args = parser.parse_args(test_args)
print(f"  解析结果: count={args.count}, mode={args.mode}")
print(f"  类型: count={type(args.count).__name__}, mode={type(args.mode).__name__}")

# 测试错误情况
try:
    parser.parse_args(['--count', '-1'])
except argparse.ArgumentTypeError as e:
    print(f"  错误捕获: {e}")


print("\n" + "=" * 60)
print("✅  Day 30 进阶用法演示完成!")
print("=" * 60)
