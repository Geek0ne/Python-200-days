"""
stats_tools.py — 数据统计工具集

提供基础统计分析功能：集中趋势、离散程度、分布统计、
排序统计和综合报告生成。

功能列表:
    mean()                 — 算术平均值
    median()               — 中位数
    mode()                 — 众数（支持多个众数）
    variance()             — 方差（样本/总体）
    std_dev()              — 标准差（样本/总体）
    frequency_distribution() — 频数分布（直方图分箱）
    sort_and_dedup()       — 排序并去重统计
    percentiles()          — 分位数计算
    visual_histogram()     — 终端字符直方图
    summary_report()       — 综合统计分析报告
"""

import math
from collections import Counter
from typing import Optional, Union


class StatsToolError(Exception):
    """统计工具操作异常基类。"""
    pass


# ──────────────────────────────────────────────
# 数据校验辅助函数
# ──────────────────────────────────────────────


def _validate_numeric_data(data: list) -> list[float]:
    """
    校验并转换输入数据为浮点数列表。

    Args:
        data: 输入数据列表。

    Returns:
        转换后的浮点数列表。

    Raises:
        StatsToolError: 数据为空或包含非数值时抛出。
    """
    if not data:
        raise StatsToolError("数据列表为空，无法进行计算")

    result: list[float] = []
    for i, val in enumerate(data):
        if val is None:
            continue
        if isinstance(val, str):
            val = val.strip()
            if not val:
                continue
        try:
            result.append(float(val))
        except (ValueError, TypeError):
            raise StatsToolError(
                f"位置 {i} 的数据 '{val}' 不是有效的数值"
            )

    if not result:
        raise StatsToolError("过滤后没有有效的数值数据")

    return result


# ──────────────────────────────────────────────
# 集中趋势
# ──────────────────────────────────────────────


def mean(data: list) -> float:
    """
    计算数据的算术平均值。

    Args:
        data: 数值列表。

    Returns:
        算术平均值。

    Raises:
        StatsToolError: 数据为空或包含非数值时抛出。

    Examples:
        >>> mean([1, 2, 3, 4, 5])
        3.0
        >>> mean([10, 20, 30])
        20.0
    """
    values = _validate_numeric_data(data)
    return sum(values) / len(values)


def median(data: list) -> float:
    """
    计算数据的中位数。

    中位数是将数据按大小排序后位于中间位置的值。
    如果数据个数为奇数，取中间值；为偶数，取中间两个值的平均数。

    Args:
        data: 数值列表。

    Returns:
        中位数。

    Raises:
        StatsToolError: 数据为空或包含非数值时抛出。

    Examples:
        >>> median([1, 3, 5, 7, 9])
        5.0
        >>> median([1, 3, 5, 7])
        4.0
    """
    values = _validate_numeric_data(data)
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    if n % 2 == 1:
        return float(sorted_vals[n // 2])
    else:
        mid = n // 2
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def mode(data: list) -> Union[float, list[float]]:
    """
    计算数据的众数（出现次数最多的值）。

    支持多个众数（多峰分布）。

    Args:
        data: 数值列表。

    Returns:
        如果是单众数，返回一个浮点数；
        如果是多众数，返回浮点数列表。

    Raises:
        StatsToolError: 数据为空或包含非数值时抛出。

    Examples:
        >>> mode([1, 2, 2, 3, 4])
        2.0
        >>> mode([1, 1, 2, 2, 3])
        [1.0, 2.0]
    """
    values = _validate_numeric_data(data)
    counter = Counter(values)
    max_count = max(counter.values())
    modes = [val for val, count in counter.items() if count == max_count]

    if len(modes) == 1:
        return modes[0]
    return modes


# ──────────────────────────────────────────────
# 离散程度
# ──────────────────────────────────────────────


def variance(data: list, sample: bool = True) -> float:
    """
    计算数据的方差。

    Args:
        data:   数值列表。
        sample: True 为样本方差（除以 n-1），False 为总体方差（除以 n）。

    Returns:
        方差值。

    Raises:
        StatsToolError: 数据为空或包含非数值时抛出。

    Examples:
        >>> variance([1, 2, 3, 4, 5], sample=True)
        2.5
        >>> variance([1, 2, 3, 4, 5], sample=False)
        2.0
    """
    values = _validate_numeric_data(data)
    n = len(values)
    avg = sum(values) / n

    if sample and n < 2:
        raise StatsToolError("样本方差需要至少 2 个数据点")

    denominator = n - 1 if sample else n
    return sum((x - avg) ** 2 for x in values) / denominator


def std_dev(data: list, sample: bool = True) -> float:
    """
    计算数据的标准差。

    Args:
        data:   数值列表。
        sample: True 为样本标准差，False 为总体标准差。

    Returns:
        标准差。

    Raises:
        StatsToolError: 数据为空或包含非数值时抛出。

    Examples:
        >>> std_dev([1, 2, 3, 4, 5], sample=True)
        1.5811388300841898
    """
    return math.sqrt(variance(data, sample=sample))


# ──────────────────────────────────────────────
# 分布统计
# ──────────────────────────────────────────────


def frequency_distribution(
    data: list,
    bins: int = 10,
    min_val: Optional[float] = None,
    max_val: Optional[float] = None,
) -> dict:
    """
    计算数据的频数分布（直方图分箱）。

    Args:
        data:    数值列表。
        bins:    分箱数量。
        min_val: 最小值边界（默认取数据最小值）。
        max_val: 最大值边界（默认取数据最大值）。

    Returns:
        频数分布结果字典：
        {
            "bins":           分箱总数,
            "bin_width":      箱宽,
            "range": [最小值, 最大值],
            "frequencies": [
                {"range": "[a, b)", "count": 频数, "percent": 百分比},
                ...
            ],
        }

    Examples:
        >>> fd = frequency_distribution([1, 2, 2, 3, 3, 3, 4, 4, 5], bins=5)
        >>> fd["frequencies"][0]
        {"range": "[1.0, 1.8)", "count": 1, "percent": 11.11}
    """
    values = _validate_numeric_data(data)
    n = len(values)

    if min_val is None:
        min_val = min(values)
    if max_val is None:
        max_val = max(values)

    if max_val <= min_val:
        # 所有值相同
        bin_width = 1.0
    else:
        bin_width = (max_val - min_val) / bins

    frequencies: list[dict] = []

    for i in range(bins):
        lower = min_val + i * bin_width
        upper = lower + bin_width

        if i == bins - 1:
            # 最后一个箱包含最大值
            count = sum(1 for v in values if lower <= v <= upper)
        else:
            count = sum(1 for v in values if lower <= v < upper)

        percent = round(count / n * 100, 2) if n > 0 else 0.0

        frequencies.append({
            "range": f"[{lower:.2f}, {upper:.2f})",
            "count": count,
            "percent": percent,
        })

    return {
        "bins": bins,
        "bin_width": round(bin_width, 4),
        "range": [min_val, max_val],
        "frequencies": frequencies,
    }


# ──────────────────────────────────────────────
# 排序与去重统计
# ──────────────────────────────────────────────


def sort_and_dedup(data: list, reverse: bool = False) -> dict:
    """
    对数据进行排序并去重，返回统计信息。

    Args:
        data:    数值列表。
        reverse: 是否降序排列。

    Returns:
        排序统计结果字典：
        {
            "original_count": 原始数据量,
            "unique_count":   去重后数据量,
            "duplicates_removed": 去除的重复数,
            "sorted_data":    排序后的唯一值列表,
        }

    Examples:
        >>> sort_and_dedup([3, 1, 2, 3, 1, 5])
        {"original_count": 6, "unique_count": 4, "duplicates_removed": 2, ...}
    """
    values = _validate_numeric_data(data)
    unique = sorted(set(values), reverse=reverse)

    return {
        "original_count": len(values),
        "unique_count": len(unique),
        "duplicates_removed": len(values) - len(unique),
        "sorted_data": unique,
    }


# ──────────────────────────────────────────────
# 分位数
# ──────────────────────────────────────────────


def percentiles(
    data: list,
    percents: Optional[list[float]] = None,
) -> dict:
    """
    计算数据的分位数。

    使用线性插值法计算指定百分位数的值。

    Args:
        data:     数值列表。
        percents: 要计算的百分位数列表（0-100 之间）。
                  默认计算：[25, 50, 75, 90, 95, 99]。

    Returns:
        分位数结果字典：
        {
            "p25": 25% 分位数 (Q1),
            "p50": 50% 分位数 (中位数),
            "p75": 75% 分位数 (Q3),
            ...
        }

    Examples:
        >>> p = percentiles([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        >>> p["p25"]
        3.25
        >>> p["p50"]
        5.5
    """
    if percents is None:
        percents = [25, 50, 75, 90, 95, 99]

    for p in percents:
        if not (0 <= p <= 100):
            raise StatsToolError(f"百分位数必须在 0-100 之间: {p}")

    values = _validate_numeric_data(data)
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    result: dict[str, float] = {}

    for p in percents:
        # 线性插值法计算百分位数
        idx = (p / 100.0) * (n - 1)
        lower_idx = int(math.floor(idx))
        upper_idx = int(math.ceil(idx))

        if lower_idx == upper_idx:
            result[f"p{int(p)}"] = float(sorted_vals[lower_idx])
        else:
            frac = idx - lower_idx
            val = sorted_vals[lower_idx] * (1 - frac) + sorted_vals[upper_idx] * frac
            result[f"p{int(p)}"] = round(val, 4)

    return result


# ──────────────────────────────────────────────
# 终端字符直方图
# ──────────────────────────────────────────────


def visual_histogram(
    data: list,
    bins: int = 10,
    width: int = 50,
    show_values: bool = True,
) -> str:
    """
    生成在终端中显示的字符直方图。

    Args:
        data:        数值列表。
        bins:        分箱数量。
        width:       直方图的最大字符宽度。
        show_values: 是否在条形旁显示数值。

    Returns:
        可用于终端打印的字符串直方图。

    Examples:
        >>> print(visual_histogram([1, 2, 2, 3, 3, 3, 4, 5], bins=4))
    """
    freq = frequency_distribution(data, bins=bins)
    max_count = max(f["count"] for f in freq["frequencies"])

    lines: list[str] = []
    lines.append(f"直方图 (bins={bins}, bin_width={freq['bin_width']})")
    lines.append(f"范围: [{freq['range'][0]:.2f}, {freq['range'][1]:.2f}]")
    lines.append("")

    for f_data in freq["frequencies"]:
        count = f_data["count"]
        bar_len = int((count / max_count) * width) if max_count > 0 else 0
        bar = "█" * bar_len

        if show_values:
            lines.append(f"  {f_data['range']:>15s} | {bar} {count} ({f_data['percent']:.1f}%)")
        else:
            lines.append(f"  {f_data['range']:>15s} | {bar}")

    lines.append("")
    lines.append(f"总计: {sum(f['count'] for f in freq['frequencies'])} 个数据点")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 综合统计报告
# ──────────────────────────────────────────────


def summary_report(data: list) -> dict:
    """
    一键生成数据的综合统计分析报告。

    Args:
        data: 数值列表。

    Returns:
        包含完整统计信息的报告字典：
        {
            "样本量": n,
            "均值": mean,
            "中位数": median,
            "众数": mode,
            "方差": variance,
            "标准差": std_dev,
            "最小值": min,
            "最大值": max,
            "极差": range,
            "Q1": 第一四分位数,
            "Q3": 第三四分位数,
            "IQR": 四分位距,
            "偏度": skewness,       # 简单的偏度估计
            "分布": [
                {"范围": "...", "频数": n, "百分比": "%"},
                ...
            ],
        }

    Examples:
        >>> report = summary_report([12, 15, 18, 22, 22, 25, 30])
        >>> print(report["均值"])
        20.57...
    """
    values = _validate_numeric_data(data)
    n = len(values)

    # 计算基本统计量
    avg = mean(values)
    med = median(values)
    mod = mode(values)

    var_val = variance(values, sample=True)
    std = std_dev(values, sample=True)

    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val

    # 计算四分位数
    pcts = percentiles(values, [25, 50, 75])
    q1 = pcts.get("p25", 0)
    q3 = pcts.get("p75", 0)
    iqr = q3 - q1

    # 简单偏度估计（皮尔逊偏度系数）
    if isinstance(mod, list):
        # 多众数时使用第一个
        skewness = (avg - mod[0]) / std if std > 0 else 0
    else:
        skewness = (avg - mod) / std if std > 0 else 0

    # 频数分布
    if n <= 50:
        bin_count = 5
    elif n <= 200:
        bin_count = 10
    else:
        bin_count = 20

    freq = frequency_distribution(values, bins=bin_count)

    # 排序去重信息
    dedup = sort_and_dedup(values)

    return {
        "样本量": n,
        "均值": round(avg, 4),
        "中位数": round(med, 4) if isinstance(med, float) else med,
        "众数": mod,
        "方差": round(var_val, 4),
        "标准差": round(std, 4),
        "最小值": min_val,
        "最大值": max_val,
        "极差": round(range_val, 4),
        "Q1": round(q1, 4),
        "Q3": round(q3, 4),
        "IQR": round(iqr, 4),
        "偏度": round(skewness, 4),
        "去重数": dedup["unique_count"],
        "重复数": dedup["duplicates_removed"],
        "分布": freq["frequencies"],
    }
