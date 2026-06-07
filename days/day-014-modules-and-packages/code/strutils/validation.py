"""字符串验证模块（相对导入示例）"""

from .formatting import to_snake_case
import re


def is_email(text: str) -> bool:
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, text.strip()))


def is_phone(text: str) -> bool:
    """验证中国大陆手机号"""
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, text.strip()))


def is_url(text: str) -> bool:
    """验证 URL 格式"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, text.strip()))


def is_palindrome(text: str) -> bool:
    """判断是否为回文字符串"""
    cleaned = re.sub(r'[^a-zA-Z0-9]', '', text).lower()
    return cleaned == cleaned[::-1]


# 演示相对导入 —— 使用同包的 formatting 模块
def normalize_and_validate(email: str) -> dict:
    """规范化邮箱并验证"""
    normalized = to_snake_case(email.strip().lower())
    return {
        'original': email,
        'normalized': normalized,
        'is_valid': is_email(normalized),
    }
