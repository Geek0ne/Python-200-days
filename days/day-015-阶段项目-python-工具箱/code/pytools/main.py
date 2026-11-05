"""
main.py — Python 工具箱命令行入口与交互菜单

提供两种使用模式：
1. 命令行模式：通过 argparse 解析参数直接调用各模块功能
2. 交互式菜单：友好的 TUI 选择界面

使用方式：
    python -m pytools.main                    # 交互式菜单
    python -m pytools.main interactive         # 交互式菜单
    python -m pytools.main file find <path>    # 命令行模式
    python -m pytools.main text freq <file>
    python -m pytools.main stats analyze <data.json>
"""

import argparse
import json
import os
import sys
from typing import NoReturn, Optional

from pytools.file_tools import (
    batch_rename,
    find_files,
    dir_size_stats,
    classify_files,
    _format_size,
)
from pytools.text_tools import (
    word_frequency,
    analyze_csv,
    search_text,
    convert_text,
)
from pytools.stats_tools import (
    mean,
    median,
    mode,
    variance,
    std_dev,
    frequency_distribution,
    sort_and_dedup,
    percentiles,
    visual_histogram,
    summary_report,
)


# ══════════════════════════════════════════════
# 命令行模式：argparse 参数解析
# ══════════════════════════════════════════════


def _validate_path(path: str) -> str:
    """验证路径是否存在。"""
    if not os.path.exists(path):
        raise argparse.ArgumentTypeError(f"路径不存在: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器。

    Returns:
        配置好的 ArgumentParser 实例。
    """
    parser = argparse.ArgumentParser(
        prog="pytools",
        description="Python 工具箱 — 文件管理 / 文本处理 / 数据统计",
        epilog="使用 'python -m pytools.main <子命令> --help' 查看子命令详情",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用子命令")

    # ── file 子命令 ──
    file_parser = subparsers.add_parser("file", help="文件管理工具")
    file_sub = file_parser.add_subparsers(dest="action", help="文件操作类型")

    # file rename
    rename_parser = file_sub.add_parser("rename", help="批量重命名文件")
    rename_parser.add_argument("path", type=_validate_path, help="目标目录")
    rename_parser.add_argument("--prefix", default="", help="文件名前缀")
    rename_parser.add_argument("--suffix", default="", help="文件名后缀")
    rename_parser.add_argument("--replace", nargs=2, metavar=("OLD", "NEW"), help="替换字符串")
    rename_parser.add_argument("--ext", default=None, help="只处理指定扩展名，如 .txt")
    rename_parser.add_argument("--start", type=int, default=1, help="序号起始值（默认 1）")
    rename_parser.add_argument("--dry-run", action="store_true", help="仅模拟运行")
    rename_parser.add_argument("--overwrite", action="store_true", help="覆盖已存在文件")

    # file find
    find_parser = file_sub.add_parser("find", help="查找文件")
    find_parser.add_argument("path", type=_validate_path, help="搜索目录")
    find_parser.add_argument("--ext", default=None, help="扩展名过滤，如 .py")
    find_parser.add_argument("--min-size", type=int, default=None, help="最小文件大小（字节）")
    find_parser.add_argument("--max-size", type=int, default=None, help="最大文件大小（字节）")
    find_parser.add_argument("--date-from", default=None, help="起始日期 YYYY-MM-DD")
    find_parser.add_argument("--date-to", default=None, help="截止日期 YYYY-MM-DD")
    find_parser.add_argument("--no-recursive", action="store_true", help="不递归搜索")
    find_parser.add_argument("--top", type=int, default=20, help="显示前 N 条结果（默认 20）")

    # file size
    size_parser = file_sub.add_parser("size", help="目录大小统计")
    size_parser.add_argument("path", type=_validate_path, help="目标目录")

    # file classify
    classify_parser = file_sub.add_parser("classify", help="按扩展名分类整理文件")
    classify_parser.add_argument("path", type=_validate_path, help="目标目录")
    classify_parser.add_argument("--dry-run", action="store_true", help="仅模拟运行")

    # ── text 子命令 ──
    text_parser = subparsers.add_parser("text", help="文本处理工具")
    text_sub = text_parser.add_subparsers(dest="action", help="文本操作类型")

    # text freq
    freq_parser = text_sub.add_parser("freq", help="词频统计")
    freq_parser.add_argument("file", type=_validate_path, help="文本文件路径")
    freq_parser.add_argument("--top", type=int, default=20, help="显示前 N 个词（默认 20）")
    freq_parser.add_argument("--no-stopwords", action="store_false", dest="stopwords",
                             help="不排除停用词")
    freq_parser.add_argument("--min-length", type=int, default=1,
                             help="最小词长度（默认 1）")

    # text csv
    csv_parser = text_sub.add_parser("csv", help="CSV 文件分析")
    csv_parser.add_argument("file", type=_validate_path, help="CSV 文件路径")
    csv_parser.add_argument("--column", default=None, help="要分析的目标列")
    csv_parser.add_argument("--delimiter", default=",", help="字段分隔符（默认逗号）")

    # text search
    search_parser = text_sub.add_parser("search", help="文本搜索")
    search_parser.add_argument("file", type=_validate_path, help="文件路径")
    search_parser.add_argument("pattern", help="搜索模式")
    search_parser.add_argument("--regex", action="store_true", help="使用正则表达式")
    search_parser.add_argument("--no-case", action="store_false", dest="case_sensitive",
                               help="不区分大小写")

    # text convert
    convert_parser = text_sub.add_parser("convert", help="文本格式转换")
    convert_parser.add_argument("file", type=_validate_path, help="文件路径")
    convert_parser.add_argument("--to-case", choices=["upper", "lower", "title"],
                                default=None, help="目标大小写")
    convert_parser.add_argument("--newline", choices=["unix", "windows", "old_mac"],
                                default=None, help="换行符格式")
    convert_parser.add_argument("--encoding", default=None, help="目标编码")
    convert_parser.add_argument("--output", default=None, help="输出文件路径")

    # ── stats 子命令 ──
    stats_parser = subparsers.add_parser("stats", help="数据统计工具")
    stats_sub = stats_parser.add_subparsers(dest="action", help="统计操作类型")

    # stats analyze (from stdin or file arg)
    analyze_parser = stats_sub.add_parser("analyze", help="数据分析")
    analyze_parser.add_argument("data", nargs="?", default=None,
                                help="JSON 数据文件路径（留空则从 stdin 读取）")

    # stats histogram
    hist_parser = stats_sub.add_parser("histogram", help="直方图")
    hist_parser.add_argument("data", nargs="?", default=None,
                              help="JSON 数据文件路径（留空则从 stdin 读取）")
    hist_parser.add_argument("--bins", type=int, default=10, help="分箱数量（默认 10）")

    # stats report
    report_parser = stats_sub.add_parser("report", help="综合统计报告")
    report_parser.add_argument("data", nargs="?", default=None,
                                help="JSON 数据文件路径（留空则从 stdin 读取）")

    return parser


def _load_data(data_arg: Optional[str]) -> list:
    """
    从文件或标准输入加载数据。

    Args:
        data_arg: 文件路径或 None。

    Returns:
        数据列表。
    """
    if data_arg:
        with open(data_arg, "r") as f:
            return json.load(f)
    else:
        print("请输入数据（JSON 格式数组），按 Ctrl+D 结束：")
        input_data = sys.stdin.read()
        return json.loads(input_data)


def run_command(args: argparse.Namespace) -> None:
    """
    根据解析的命令行参数执行对应功能。

    Args:
        args: 解析后的命令行参数。
    """
    if args.command == "file":
        _run_file_command(args)
    elif args.command == "text":
        _run_text_command(args)
    elif args.command == "stats":
        _run_stats_command(args)
    else:
        print(f"未知命令: {args.command}")
        sys.exit(1)


def _run_file_command(args: argparse.Namespace) -> None:
    """执行文件管理子命令。"""
    if args.action == "rename":
        ext = args.ext.split(",") if args.ext and "," in args.ext else args.ext
        replace_tuple = tuple(args.replace) if args.replace else None
        result = batch_rename(
            path=args.path,
            prefix=args.prefix,
            suffix=args.suffix,
            replace=replace_tuple,
            ext=ext,
            start=args.start,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
        print(f"\n批量重命名结果:")
        print(f"  总数: {result['total']}")
        print(f"  成功: {result['renamed']}")
        print(f"  跳过: {result['skipped']}")
        if result["errors"]:
            print(f"  错误: {len(result['errors'])}")
            for err in result["errors"][:5]:
                print(f"    - {err}")

    elif args.action == "find":
        ext = args.ext.split(",") if args.ext and "," in args.ext else args.ext
        result = find_files(
            path=args.path,
            ext=ext,
            min_size=args.min_size,
            max_size=args.max_size,
            date_from=args.date_from,
            date_to=args.date_to,
            recursive=not args.no_recursive,
        )
        print(f"\n查找结果 ({result['total_count']} 个文件, " +
              f"总计 {_format_size(result['total_size'])}):")
        print("-" * 70)
        for fpath, fsize, fdate in result["files"][:args.top]:
            print(f"  {_format_size(fsize):>10s}  {fdate}  {fpath}")
        if result["total_count"] > args.top:
            print(f"  ... 还有 {result['total_count'] - args.top} 个文件未显示")

    elif args.action == "size":
        result = dir_size_stats(args.path)
        print(f"\n目录大小统计: {result['path']}")
        print(f"  总大小: {result['total_size_str']}")
        print(f"  文件数: {result['total_files']}")
        print(f"  子目录: {result['total_dirs']}")
        print(f"\n子目录大小排行 (Top 10):")
        for sub in result["subdirs"][:10]:
            print(f"  {sub['size_str']:>10s}  {sub['name']}")

    elif args.action == "classify":
        result = classify_files(args.path, dry_run=args.dry_run)
        print(f"\n文件分类整理结果:")
        print(f"  总数: {result['total']}")
        print(f"  移动: {result['moved']}")
        print(f"\n分类统计:")
        for cat, count in sorted(
            result["category_counts"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {cat:>12s}: {count} 个文件")

    else:
        print(f"未知文件操作: {args.action}")


def _run_text_command(args: argparse.Namespace) -> None:
    """执行文本处理子命令。"""
    if args.action == "freq":
        result = word_frequency(
            args.file,
            ignore_stopwords=args.stopwords,
            top_n=args.top,
            min_length=args.min_length,
        )
        print(f"\n词频统计结果:")
        print(f"  总词数: {result['total_words']}")
        print(f"  唯一词: {result['unique_words']}")
        if args.stopwords:
            print(f"  排除停用词: {result['stopwords_removed']} 个")
        print(f"\nTop {args.top} 高频词:")
        print("-" * 40)
        for word, count in result["top_words"]:
            print(f"  {word:<15s} {count} 次")

    elif args.action == "csv":
        result = analyze_csv(
            args.file,
            column=args.column,
            delimiter=args.delimiter,
        )
        print(f"\nCSV 文件分析: {result['file']}")
        print(f"  总行数: {result['total_rows']}")
        print(f"  列: {', '.join(result['columns'])}")
        print(f"\n列分析:")
        for col_name, analysis in result["analysis"].items():
            print(f"  [{col_name}] ({analysis['type']})")
            print(f"    非空: {analysis['non_null']}, 缺失: {analysis['missing']}")
            print(f"    唯一值: {analysis['unique_values']}")
            if "mean" in analysis:
                print(f"    均值: {analysis['mean']:.2f}, " +
                      f"范围: [{analysis['min']:.2f}, {analysis['max']:.2f}]")

    elif args.action == "search":
        result = search_text(
            args.file,
            pattern=args.pattern,
            use_regex=args.regex,
            case_sensitive=args.case_sensitive,
        )
        print(f"\n文本搜索: '{result['pattern']}'")
        print(f"  总行数: {result['total_lines']}")
        print(f"  匹配行: {result['total_matches']}")
        print(f"\n匹配结果:")
        print("-" * 60)
        for match in result["matches"][:50]:
            content = match["content"][:80]
            print(f"  第{match['line_number']:>6d}行 | {content}")
        if result["total_matches"] > 50:
            print(f"  ... 还有 {result['total_matches'] - 50} 行匹配结果")

    elif args.action == "convert":
        result = convert_text(
            args.file,
            to_case=args.to_case,
            newline=args.newline,
            encoding=args.encoding,
            output=args.output,
        )
        print(f"\n文本格式转换完成:")
        print(f"  源文件: {result['source']}")
        print(f"  输出: {result['output']}")
        print(f"  变更: {', '.join(result['changes'])}")
        print(f"  原大小: {_format_size(result['original_size'])}")
        print(f"  新大小: {_format_size(result['new_size'])}")

    else:
        print(f"未知文本操作: {args.action}")


def _run_stats_command(args: argparse.Namespace) -> None:
    """执行数据统计子命令。"""
    try:
        data = _load_data(args.data)
    except Exception as e:
        print(f"数据加载失败: {e}")
        sys.exit(1)

    if args.action == "analyze":
        print(f"\n数据分析结果:")
        print(f"  样本量: {len(data)}")
        print(f"  均值: {mean(data):.4f}")
        print(f"  中位数: {median(data):.4f}")
        print(f"  众数: {mode(data)}")
        print(f"  方差: {variance(data, sample=True):.4f}")
        print(f"  标准差: {std_dev(data, sample=True):.4f}")
        print(f"  最小值: {min(data):.4f}")
        print(f"  最大值: {max(data):.4f}")

    elif args.action == "histogram":
        print(visual_histogram(data, bins=args.bins))

    elif args.action == "report":
        report = summary_report(data)
        print(f"\n{'=' * 50}")
        print(f"  综合统计分析报告")
        print(f"{'=' * 50}")
        print(f"  样本量:    {report['样本量']}")
        print(f"  均值:      {report['均值']}")
        print(f"  中位数:    {report['中位数']}")
        print(f"  众数:      {report['众数']}")
        print(f"  方差:      {report['方差']}")
        print(f"  标准差:    {report['标准差']}")
        print(f"  最小值:    {report['最小值']}")
        print(f"  最大值:    {report['最大值']}")
        print(f"  极差:      {report['极差']}")
        print(f"  Q1:        {report['Q1']}")
        print(f"  Q3:        {report['Q3']}")
        print(f"  IQR:       {report['IQR']}")
        print(f"  偏度:      {report['偏度']}")
        print(f"  去重数:    {report['去重数']}")
        print(f"  重复数:    {report['重复数']}")
        print(f"{'=' * 50}")
        print(f"  分布:")
        for f_data in report["分布"]:
            bar = "█" * max(1, f_data["count"])
            print(f"    {f_data['range']:>15s}  {bar} {f_data['count']} 次")

    else:
        print(f"未知统计操作: {args.action}")


# ══════════════════════════════════════════════
# 交互式菜单模式
# ══════════════════════════════════════════════


def interactive_mode() -> NoReturn:
    """
    启动交互式菜单模式。

    用户可以通过数字选择不同的功能模块和操作，
    按 q 退出程序。
    """
    print("\n" + "=" * 55)
    print("  🐍 Python 工具箱 — 交互式菜单")
    print("=" * 55)

    while True:
        print("\n请选择功能模块:")
        print("  ┌─────────────────────────────────────┐")
        print("  │  [1] 📁 文件管理工具                │")
        print("  │  [2] 📝 文本处理工具                │")
        print("  │  [3] 📊 数据统计工具                │")
        print("  │  [q] 🚪 退出                       │")
        print("  └─────────────────────────────────────┘")

        choice = input("\n请输入选择 (1-3, q): ").strip()

        if choice == "q":
            print("感谢使用 Python 工具箱！再见 👋")
            sys.exit(0)
        elif choice == "1":
            _file_menu()
        elif choice == "2":
            _text_menu()
        elif choice == "3":
            _stats_menu()
        else:
            print("❌ 无效选择，请重新输入")


def _file_menu() -> None:
    """文件管理工具子菜单。"""
    while True:
        print("\n  ┌─────── 📁 文件管理工具 ────────┐")
        print("  │  [1] 批量重命名                 │")
        print("  │  [2] 文件查找                   │")
        print("  │  [3] 目录大小统计               │")
        print("  │  [4] 文件分类整理               │")
        print("  │  [b] 返回上级菜单               │")
        print("  └───────────────────────────────┘")

        choice = input("\n请输入选择 (1-4, b): ").strip()

        if choice == "b":
            return
        elif choice == "1":
            path = input("目标目录路径: ").strip()
            if not os.path.isdir(path):
                print("❌ 目录不存在")
                continue
            prefix = input("前缀 (留空跳过): ").strip()
            suffix = input("后缀 (留空跳过): ").strip()
            ext = input("仅处理扩展名 (如 .txt, 留空全部): ").strip() or None
            dry = input("仅模拟 (y/n): ").strip().lower() == "y"
            result = batch_rename(path, prefix=prefix, suffix=suffix, ext=ext, dry_run=dry)
            print(f"\n结果: 总数 {result['total']}, 成功 {result['renamed']}, 跳过 {result['skipped']}")

        elif choice == "2":
            path = input("搜索目录: ").strip()
            if not os.path.isdir(path):
                print("❌ 目录不存在")
                continue
            ext = input("扩展名过滤 (如 .py, 留空全部): ").strip() or None
            min_size_s = input("最小大小 (字节, 留空不限): ").strip()
            max_size_s = input("最大大小 (字节, 留空不限): ").strip()
            min_size = int(min_size_s) if min_size_s else None
            max_size = int(max_size_s) if max_size_s else None
            top = input("显示前几条 (默认 20): ").strip()
            top = int(top) if top else 20

            result = find_files(path, ext=ext, min_size=min_size, max_size=max_size)
            print(f"\n找到 {result['total_count']} 个文件, 总计 {_format_size(result['total_size'])}:")
            for fpath, fsize, fdate in result["files"][:top]:
                print(f"  {_format_size(fsize):>10s}  {fdate}  {fpath}")

        elif choice == "3":
            path = input("目标目录路径: ").strip()
            if not os.path.isdir(path):
                print("❌ 目录不存在")
                continue
            result = dir_size_stats(path)
            print(f"\n总大小: {result['total_size_str']}")
            print(f"文件数: {result['total_files']}")
            print(f"子目录: {result['total_dirs']}")
            print("\nTop 5 子目录:")
            for sub in result["subdirs"][:5]:
                print(f"  {sub['size_str']:>10s}  {sub['name']}")

        elif choice == "4":
            path = input("要整理的目录路径: ").strip()
            if not os.path.isdir(path):
                print("❌ 目录不存在")
                continue
            dry = input("仅模拟 (y/n): ").strip().lower() == "y"
            result = classify_files(path, dry_run=dry)
            print(f"\n分类完成: {result['moved']} 个文件已移动")
            for cat, count in result["category_counts"].items():
                print(f"  {cat}: {count} 个文件")

        else:
            print("❌ 无效选择")


def _text_menu() -> None:
    """文本处理工具子菜单。"""
    while True:
        print("\n  ┌─────── 📝 文本处理工具 ────────┐")
        print("  │  [1] 词频统计                   │")
        print("  │  [2] CSV 文件分析               │")
        print("  │  [3] 文本搜索                   │")
        print("  │  [4] 文本格式转换               │")
        print("  │  [b] 返回上级菜单               │")
        print("  └───────────────────────────────┘")

        choice = input("\n请输入选择 (1-4, b): ").strip()

        if choice == "b":
            return
        elif choice == "1":
            path = input("文本文件路径: ").strip()
            if not os.path.isfile(path):
                print("❌ 文件不存在")
                continue
            top = input("显示前几个词 (默认 20): ").strip()
            top = int(top) if top else 20
            no_stop = input("排除停用词 (y/n, 默认 y): ").strip().lower() != "n"
            result = word_frequency(path, ignore_stopwords=no_stop, top_n=top)
            print(f"\n总词数: {result['total_words']}, 唯一词: {result['unique_words']}")
            print(f"Top {top}:")
            for word, count in result["top_words"]:
                print(f"  {word:<15s} {count} 次")

        elif choice == "2":
            path = input("CSV 文件路径: ").strip()
            if not os.path.isfile(path):
                print("❌ 文件不存在")
                continue
            col = input("目标列 (留空分析所有列): ").strip() or None
            delim = input("分隔符 (默认逗号): ").strip() or ","
            result = analyze_csv(path, column=col, delimiter=delim)
            print(f"\n总行数: {result['total_rows']}")
            print(f"列: {', '.join(result['columns'])}")
            for col_name, analysis in result["analysis"].items():
                print(f"\n  [{col_name}] ({analysis['type']})")
                print(f"    非空: {analysis['non_null']}, 缺失: {analysis['missing']}")
                if "mean" in analysis:
                    print(f"    均值: {analysis['mean']:.2f}")

        elif choice == "3":
            path = input("文件路径: ").strip()
            if not os.path.isfile(path):
                print("❌ 文件不存在")
                continue
            pattern = input("搜索模式: ").strip()
            if not pattern:
                print("❌ 搜索模式不能为空")
                continue
            use_regex = input("使用正则 (y/n): ").strip().lower() == "y"
            case = input("区分大小写 (y/n, 默认 y): ").strip().lower() != "n"
            result = search_text(path, pattern, use_regex=use_regex, case_sensitive=case)
            print(f"\n匹配 {result['total_matches']} 行 / 共 {result['total_lines']} 行")
            for match in result["matches"][:20]:
                print(f"  行 {match['line_number']:>5d} | {match['content'][:70]}")

        elif choice == "4":
            path = input("文件路径: ").strip()
            if not os.path.isfile(path):
                print("❌ 文件不存在")
                continue
            print("\n大小写转换选项:")
            print("  1) 全部大写")
            print("  2) 全部小写")
            print("  3) 首字母大写")
            print("  0) 不转换")
            case_choice = input("请选择 (0-3): ").strip()
            case_map = {"1": "upper", "2": "lower", "3": "title"}
            to_case = case_map.get(case_choice)

            print("\n换行符选项:")
            print("  1) Unix (\\n)")
            print("  2) Windows (\\r\\n)")
            print("  3) Old Mac (\\r)")
            print("  0) 不转换")
            nl_choice = input("请选择 (0-3): ").strip()
            nl_map = {"1": "unix", "2": "windows", "3": "old_mac"}
            newline = nl_map.get(nl_choice)

            enc = input("目标编码 (留空保持原样): ").strip() or None
            output = input("输出路径 (留空覆盖原文件): ").strip() or None

            result = convert_text(path, to_case=to_case, newline=newline, encoding=enc, output=output)
            print(f"\n转换完成: {', '.join(result['changes'])}")

        else:
            print("❌ 无效选择")


def _stats_menu() -> None:
    """数据统计工具子菜单。"""
    while True:
        print("\n  ┌─────── 📊 数据统计工具 ────────┐")
        print("  │  [1] 快速分析                   │")
        print("  │  [2] 终端直方图                 │")
        print("  │  [3] 综合统计报告               │")
        print("  │  [4] 排序去重统计               │")
        print("  │  [b] 返回上级菜单               │")
        print("  └───────────────────────────────┘")

        choice = input("\n请输入选择 (1-4, b): ").strip()

        if choice == "b":
            return
        elif choice in ("1", "2", "3", "4"):
            # 获取数据
            data_path = input("输入数据文件 (JSON 数组格式, 留空手动输入): ").strip()
            if data_path and os.path.isfile(data_path):
                with open(data_path, "r") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print("❌ JSON 解析失败")
                        continue
            else:
                print("请输入数值，用逗号分隔:")
                raw = input("> ").strip()
                try:
                    data = [float(x.strip()) for x in raw.split(",") if x.strip()]
                except ValueError:
                    print("❌ 输入数据格式错误")
                    continue
                if not data:
                    print("❌ 没有有效数据")
                    continue

            if choice == "1":
                print(f"\n--- 快速分析 ---")
                print(f"样本量: {len(data)}")
                print(f"均值:   {mean(data):.4f}")
                print(f"中位数: {median(data):.4f}")
                print(f"众数:   {mode(data)}")
                print(f"标准差: {std_dev(data, sample=True):.4f}")
                print(f"最小值: {min(data):.4f}")
                print(f"最大值: {max(data):.4f}")

            elif choice == "2":
                bins_s = input("分箱数 (默认 10): ").strip()
                bins = int(bins_s) if bins_s else 10
                print()
                print(visual_histogram(data, bins=bins))

            elif choice == "3":
                report = summary_report(data)
                print(f"\n{'=' * 50}")
                print(f"  综合统计分析报告")
                print(f"{'=' * 50}")
                for key, val in report.items():
                    if key != "分布":
                        print(f"  {key}: {val}")
                print(f"\n  分布:")
                for f_data in report["分布"]:
                    bar = "█" * max(1, f_data["count"])
                    print(f"    {f_data['range']:>15s}  {bar} {f_data['count']} 次")

            elif choice == "4":
                result = sort_and_dedup(data)
                print(f"\n--- 排序去重统计 ---")
                print(f"原始数据量: {result['original_count']}")
                print(f"去重后:     {result['unique_count']}")
                print(f"重复数:     {result['duplicates_removed']}")
                print(f"排序后:     {result['sorted_data']}")

        else:
            print("❌ 无效选择")


# ══════════════════════════════════════════════
# 程序入口
# ══════════════════════════════════════════════


def main() -> None:
    """
    程序主入口。

    根据命令行参数决定进入命令行模式还是交互式菜单模式。
    """
    parser = build_parser()
    args = parser.parse_args()

    if args.command is None or args.command == "interactive":
        interactive_mode()
    else:
        run_command(args)


if __name__ == "__main__":
    main()
