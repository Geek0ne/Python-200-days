"""字符串操作模块"""


def reverse(text: str) -> str:
    """反转字符串"""
    return text[::-1]


def count_words(text: str) -> int:
    """统计单词数"""
    return len(text.split())


def remove_duplicates(text: str) -> str:
    """移除连续重复字符"""
    if not text:
        return text
    result = [text[0]]
    for ch in text[1:]:
        if ch != result[-1]:
            result.append(ch)
    return ''.join(result)


def truncate(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """截断字符串到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
