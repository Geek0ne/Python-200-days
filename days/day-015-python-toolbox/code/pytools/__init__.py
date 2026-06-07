"""
pytools — Python 工具箱

一个综合性的日常开发工具包，提供文件管理、文本处理和
数据统计三大核心功能，支持命令行和交互式两种使用模式。

使用方式:
    python -m pytools.main              # 交互模式
    python -m pytools.main file ...     # 命令行模式
    python -m pytools.main text ...
    python -m pytools.main stats ...
"""

from pytools.file_tools import (
    batch_rename,
    find_files,
    dir_size_stats,
    classify_files,
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

__all__ = [
    # File tools
    "batch_rename",
    "find_files",
    "dir_size_stats",
    "classify_files",
    # Text tools
    "word_frequency",
    "analyze_csv",
    "search_text",
    "convert_text",
    # Stats tools
    "mean",
    "median",
    "mode",
    "variance",
    "std_dev",
    "frequency_distribution",
    "sort_and_dedup",
    "percentiles",
    "visual_histogram",
    "summary_report",
]

__version__ = "1.0.0"
__author__ = "Learn-Python"
