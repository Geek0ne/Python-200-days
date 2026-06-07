"""统计计算模块（相对导入示例）"""

from .basic import sqrt as _sqrt


def mean(data: list) -> float:
    """算术平均值"""
    if not data:
        raise ValueError("空数据集")
    return sum(data) / len(data)


def median(data: list) -> float:
    """中位数"""
    if not data:
        raise ValueError("空数据集")
    sorted_data = sorted(data)
    n = len(sorted_data)
    mid = n // 2
    if n % 2 == 1:
        return sorted_data[mid]
    return (sorted_data[mid - 1] + sorted_data[mid]) / 2


def mode(data: list):
    """众数"""
    if not data:
        raise ValueError("空数据集")
    from collections import Counter
    counter = Counter(data)
    max_count = max(counter.values())
    modes = [k for k, v in counter.items() if v == max_count]
    return modes[0] if len(modes) == 1 else modes


def variance(data: list, ddof: int = 0) -> float:
    """方差"""
    if not data:
        raise ValueError("空数据集")
    n = len(data)
    if n <= ddof:
        raise ValueError(f"数据量 {n} 不足以计算自由度 {ddof} 的方差")
    avg = mean(data)
    return sum((x - avg) ** 2 for x in data) / (n - ddof)


def std_dev(data: list, ddof: int = 0) -> float:
    """标准差"""
    return _sqrt(variance(data, ddof))
