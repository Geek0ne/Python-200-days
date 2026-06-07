"""
strutils - 字符串处理工具包

提供字符串操作、验证和格式化功能。
"""

from strutils.manipulation import (
    reverse,
    count_words,
    remove_duplicates,
    truncate,
)

from strutils.validation import (
    is_email,
    is_phone,
    is_url,
    is_palindrome,
)

from strutils.formatting import (
    to_title_case,
    to_snake_case,
    to_camel_case,
    mask_sensitive,
)

__version__ = '0.1.0'
__all__ = [
    'reverse', 'count_words', 'remove_duplicates', 'truncate',
    'is_email', 'is_phone', 'is_url', 'is_palindrome',
    'to_title_case', 'to_snake_case', 'to_camel_case', 'mask_sensitive',
]
