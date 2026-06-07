"""字符串格式化模块"""


def to_title_case(text: str) -> str:
    """转为标题格式"""
    return text.title()


def to_snake_case(text: str) -> str:
    """转为蛇形命名（words_like_this）"""
    result = []
    for i, ch in enumerate(text):
        if ch.isupper():
            if i > 0 and text[i - 1].islower():
                result.append('_')
            result.append(ch.lower())
        elif ch in (' ', '-', '.'):
            if result and result[-1] != '_':
                result.append('_')
        else:
            result.append(ch)
    return ''.join(result).strip('_')


def to_camel_case(text: str) -> str:
    """转为驼峰命名（camelCase）"""
    words = text.replace('-', ' ').replace('_', ' ').split()
    if not words:
        return ''
    return words[0].lower() + ''.join(w.capitalize() for w in words[1:])


def mask_sensitive(text: str, visible_chars: int = 4, mask_char: str = '*') -> str:
    """脱敏处理：保留最后 visible_chars 位，其余替换为 mask_char"""
    if len(text) <= visible_chars:
        return text
    return mask_char * (len(text) - visible_chars) + text[-visible_chars:]
