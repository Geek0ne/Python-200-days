"""
text_tools.py — 文本处理工具集

提供文本分析与处理功能：词频统计、CSV 分析、
文本搜索和格式转换。

功能列表:
    word_frequency() — 统计文本词频，支持排除停用词
    analyze_csv()    — 读取 CSV 并返回基本分析信息
    search_text()    — 正则或普通方式搜索文本
    convert_text()   — 大小写、换行符、编码转换
"""

import csv
import os
import re
from collections import Counter
from typing import Optional, Union

# ──────────────────────────────────────────────
# 默认停用词列表（中文 + 英文常见词）
# ──────────────────────────────────────────────

DEFAULT_STOPWORDS: set[str] = {
    # English stopwords
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "up", "about", "into", "over", "after", "before", "between", "under",
    "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "also", "and", "but", "or",
    "if", "because", "as", "until", "while", "that", "which", "who",
    "whom", "this", "these", "those", "it", "its", "i", "me", "my",
    "myself", "we", "our", "ours", "you", "your", "yours", "he", "him",
    "his", "she", "her", "hers", "they", "them", "their", "theirs",
    "what", "am", "been", "being", "having", "doing", "getting",
    # Chinese stopwords (common)
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
    "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们",
    "那", "什么", "怎么", "为什么", "因为", "所以", "但是", "而且",
    "虽然", "如果", "那么", "还是", "只是", "不过", "已经", "可以",
    "能够", "应该", "可能", "必须", "一定", "确实", "一直", "从来",
    "别人", "大家", "每", "某", "某", "几", "谁", "哪", "哪些",
    "怎样", "吗", "吧", "呢", "啊", "哦", "嗯", "哈", "呀",
}


class TextToolError(Exception):
    """文本工具操作异常基类。"""
    pass


# ──────────────────────────────────────────────
# 词频统计
# ──────────────────────────────────────────────


def word_frequency(
    text_or_file: str,
    ignore_stopwords: bool = True,
    custom_stopwords: Optional[set[str]] = None,
    top_n: Optional[int] = None,
    min_length: int = 1,
) -> dict:
    """
    统计文本中单词的出现频率。

    Args:
        text_or_file:    文本内容或文件路径。如果是文件路径且存在，则读取文件。
        ignore_stopwords:是否排除停用词。
        custom_stopwords:自定义停用词集合（与默认停用词合并）。
        top_n:           只返回出现频率最高的 N 个词，None 表示返回全部。
        min_length:      最小词长度，小于此长度的词将被忽略。

    Returns:
        词频统计结果字典：
        {
            "total_words": 总词数（含重复）,
            "unique_words": 去重词数,
            "top_words": [("word", count), ...],
            "stopwords_removed": 排除的停用词数量,
        }

    Examples:
        >>> wf = word_frequency("hello world hello python")
        >>> wf["top_words"]
        [("hello", 2), ("world", 1), ("python", 1)]

        >>> wf = word_frequency("file.txt", top_n=10)
    """
    # 判断输入是文件路径还是文本内容
    if os.path.isfile(text_or_file):
        try:
            with open(text_or_file, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            try:
                with open(text_or_file, "r", encoding="gbk") as f:
                    text = f.read()
            except Exception as e:
                raise TextToolError(f"无法读取文件 {text_or_file}: {e}")
    else:
        text = text_or_file

    if not text.strip():
        return {
            "total_words": 0,
            "unique_words": 0,
            "top_words": [],
            "stopwords_removed": 0,
        }

    # 预处理：统一小写化
    text = text.lower()

    # 分词：按非字母字符分割
    # 支持中文（每个字符作为一个词）和英文（按空格分割）
    # 使用正则匹配提取连续的字母（含中文）序列
    words = re.findall(r"[a-z]+|[\u4e00-\u9fff]+", text)

    # 过滤长度
    words = [w for w in words if len(w) >= min_length]

    # 合并停用词
    stopwords = set()
    if ignore_stopwords:
        stopwords = DEFAULT_STOPWORDS.copy()
        if custom_stopwords:
            stopwords.update(custom_stopwords)

    stopwords_removed = 0
    if ignore_stopwords:
        filtered_words = []
        for w in words:
            if w in stopwords:
                stopwords_removed += 1
            else:
                filtered_words.append(w)
        words = filtered_words

    # 统计词频
    counter = Counter(words)

    # 按频率排序
    most_common = counter.most_common(top_n)

    return {
        "total_words": len(words),
        "unique_words": len(counter),
        "top_words": most_common,
        "stopwords_removed": stopwords_removed,
    }


# ──────────────────────────────────────────────
# CSV 分析
# ──────────────────────────────────────────────


def analyze_csv(
    filepath: str,
    column: Optional[str] = None,
    delimiter: str = ",",
    has_header: bool = True,
) -> dict:
    """
    读取 CSV 文件并返回基本分析信息。

    Args:
        filepath:   CSV 文件路径。
        column:     要分析的目标列名（如果为 None，分析所有列）。
        delimiter:  字段分隔符（默认逗号）。
        has_header: 文件是否包含表头行。

    Returns:
        CSV 分析结果字典：
        {
            "file": 文件名,
            "total_rows": 总行数,
            "columns": [列名列表],
            "column_types": {"列名": "类型", ...},
            "analysis": {列名: {统计信息}, ...},
        }

        单列分析的统计信息包括：
        - 数据类型
        - 非空值数量
        - 缺失值数量
        - 唯一值数量
        - 示例值（前 5 个）
        - 如果是数字列：均值、最小值、最大值

    Examples:
        >>> result = analyze_csv("data.csv")
        >>> result = analyze_csv("data.csv", column="score")
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            if has_header:
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = reader.fieldnames or []
                rows = list(reader)
            else:
                reader = csv.reader(f, delimiter=delimiter)
                first_row = next(reader, [])
                fieldnames = [f"column_{i}" for i in range(len(first_row))]
                rows = [
                    {name: val for name, val in zip(fieldnames, [first_row] + list(reader))}
                ]

    except Exception as e:
        raise TextToolError(f"无法读取 CSV 文件 {filepath}: {e}")

    if not fieldnames:
        return {
            "file": filepath,
            "total_rows": 0,
            "columns": [],
            "column_types": {},
            "analysis": {},
        }

    total_rows = len(rows)

    def _infer_type(values: list[str]) -> str:
        """推断列的数据类型。"""
        non_empty = [v for v in values if v.strip()]
        if not non_empty:
            return "empty"

        # 检查是否都是数字（整数或浮点数）
        all_numeric = True
        for v in non_empty:
            try:
                float(v)
            except ValueError:
                all_numeric = False
                break

        if all_numeric:
            return "numeric"

        # 检查是否都是整型数字
        all_integer = True
        for v in non_empty:
            try:
                float(v)
                if float(v) != int(float(v)):
                    all_integer = False
                    break
            except ValueError:
                all_integer = False
                break

        if all_integer:
            return "integer"

        return "text"

    def _analyze_column(col_name: str, values: list[str]) -> dict:
        """分析单列数据。"""
        non_empty = [v for v in values if v.strip()]
        missing = len(values) - len(non_empty)
        unique_vals = set(non_empty)
        col_type = _infer_type(values)

        result = {
            "type": col_type,
            "non_null": len(non_empty),
            "missing": missing,
            "unique_values": len(unique_vals),
            "sample_values": non_empty[:5],
        }

        # 如果是数字列，计算统计量
        if col_type in ("numeric", "integer"):
            numeric_vals = []
            for v in non_empty:
                try:
                    numeric_vals.append(float(v))
                except ValueError:
                    continue
            if numeric_vals:
                result["mean"] = sum(numeric_vals) / len(numeric_vals)
                result["min"] = min(numeric_vals)
                result["max"] = max(numeric_vals)

        return result

    # 分析指定列或所有列
    analysis: dict[str, dict] = {}
    for col in fieldnames:
        values = [row.get(col, "") for row in rows]

        if column is not None and col != column:
            continue

        analysis[col] = _analyze_column(col, values)

    # 推断每列类型
    column_types = {col: analysis[col]["type"] for col in analysis}

    return {
        "file": filepath,
        "total_rows": total_rows,
        "columns": fieldnames,
        "column_types": column_types,
        "analysis": analysis,
    }


# ──────────────────────────────────────────────
# 文本搜索
# ──────────────────────────────────────────────


def search_text(
    filepath: str,
    pattern: str,
    use_regex: bool = False,
    case_sensitive: bool = True,
) -> dict:
    """
    在文本文件中搜索指定模式。

    Args:
        filepath:       文件路径。
        pattern:        搜索模式（普通字符串或正则表达式）。
        use_regex:      是否将 pattern 作为正则表达式使用。
        case_sensitive: 是否区分大小写。

    Returns:
        搜索结果字典：
        {
            "pattern": 搜索模式,
            "total_matches": 匹配行数,
            "total_lines": 总行数,
            "matches": [
                {"line_number": 行号, "content": 行内容, "highlight": 高亮文本},
                ...
            ],
        }

    Examples:
        >>> search_text("log.txt", "ERROR", case_sensitive=True)
        >>> search_text("code.py", r"def \w+", use_regex=True)
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    matches: list[dict] = []
    total_lines = 0

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            if use_regex:
                # 编译正则表达式
                flags = 0 if case_sensitive else re.IGNORECASE
                try:
                    regex = re.compile(pattern, flags)
                except re.error as e:
                    raise TextToolError(f"正则表达式错误: {e}")

                for line_number, line in enumerate(f, 1):
                    total_lines += 1
                    line_stripped = line.rstrip("\n").rstrip("\r")
                    match = regex.search(line_stripped)
                    if match:
                        matches.append({
                            "line_number": line_number,
                            "content": line_stripped,
                            "highlight": match.group(),
                        })
            else:
                for line_number, line in enumerate(f, 1):
                    total_lines += 1
                    line_stripped = line.rstrip("\n").rstrip("\r")
                    if case_sensitive:
                        found = pattern in line_stripped
                    else:
                        found = pattern.lower() in line_stripped.lower()

                    if found:
                        matches.append({
                            "line_number": line_number,
                            "content": line_stripped,
                        })
    except UnicodeDecodeError:
        raise TextToolError(f"文件编码错误，请先将文件转换为 UTF-8: {filepath}")
    except Exception as e:
        raise TextToolError(f"读取文件失败: {e}")

    return {
        "pattern": pattern,
        "total_matches": len(matches),
        "total_lines": total_lines,
        "matches": matches,
    }


# ──────────────────────────────────────────────
# 文本格式转换
# ──────────────────────────────────────────────


def convert_text(
    filepath: str,
    to_case: Optional[str] = None,
    newline: Optional[str] = None,
    encoding: Optional[str] = None,
    output: Optional[str] = None,
) -> dict:
    """
    转换文本文件的格式（大小写、换行符、编码）。

    Args:
        filepath: 输入文件路径。
        to_case:  目标大小写模式：
                  "upper" - 全部大写
                  "lower" - 全部小写
                  "title" - 首字母大写
        newline:  目标换行符格式：
                  "unix"  - \\n
                  "windows" - \\r\\n
                  "old_mac" - \\r
        encoding: 目标编码格式，如 "utf-8", "gbk", "latin-1"。
        output:   输出文件路径。如果为 None，覆盖原文件。

    Returns:
        操作结果字典：
        {
            "source": 原文件路径,
            "output": 输出文件路径,
            "changes": 进行了哪些转换,
            "original_size": 原文件大小,
            "new_size": 新文件大小,
        }

    Examples:
        >>> convert_text("notes.txt", to_case="lower")
        >>> convert_text("data.txt", newline="unix", encoding="utf-8")
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # 读取原文件
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # 尝试常见编码
        for enc in ("gbk", "latin-1", "shift-jis", "cp1252"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            raise TextToolError("无法自动检测文件编码")

    original_size = len(content.encode("utf-8"))
    changes: list[str] = []

    # 大小写转换
    if to_case == "upper":
        content = content.upper()
        changes.append("大小写: → 大写")
    elif to_case == "lower":
        content = content.lower()
        changes.append("大小写: → 小写")
    elif to_case == "title":
        content = content.title()
        changes.append("大小写: → 首字母大写")

    # 换行符转换
    if newline == "unix":
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        changes.append("换行符: → Unix (\\n)")
    elif newline == "windows":
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        content = content.replace("\n", "\r\n")
        changes.append("换行符: → Windows (\\r\\n)")
    elif newline == "old_mac":
        content = content.replace("\r\n", "\n").replace("\n", "\r")
        changes.append("换行符: → Old Mac (\\r)")

    # 编码
    out_encoding = encoding or "utf-8"
    if encoding:
        changes.append(f"编码: → {encoding}")

    # 写入文件
    output_path = output or filepath
    try:
        with open(output_path, "w", encoding=out_encoding) as f:
            f.write(content)
    except Exception as e:
        raise TextToolError(f"写入文件失败 {output_path}: {e}")

    new_size = len(content.encode(out_encoding))

    return {
        "source": filepath,
        "output": output_path,
        "changes": changes,
        "original_size": original_size,
        "new_size": new_size,
    }
