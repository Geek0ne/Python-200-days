"""
Day 045 - 工具函数集合
OOP 实战中常用的工具函数
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_id(prefix: str = "") -> str:
    """生成唯一 ID"""
    timestamp = datetime.now().timestamp()
    hash_str = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
    return f"{prefix}{hash_str}"


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    import re
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))


def sanitize_string(value: str) -> str:
    """清理字符串"""
    if not isinstance(value, str):
        return str(value)
    return value.strip()


def format_currency(amount: float, currency: str = "CNY") -> str:
    """格式化货币"""
    if currency == "CNY":
        return f"¥{amount:,.2f}"
    elif currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    return dt.strftime(format_str)


def parse_json(json_str: str) -> Optional[Dict]:
    """解析 JSON 字符串"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


def to_json(obj: Any, ensure_ascii: bool = False) -> str:
    """转换为 JSON 字符串"""
    return json.dumps(obj, ensure_ascii=ensure_ascii, indent=2)


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """扁平化字典"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """将列表分割为块"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_duplicates(lst: List) -> List:
    """移除列表中的重复项"""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def merge_dicts(*dicts: Dict) -> Dict:
    """合并多个字典"""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def deep_merge_dicts(base: Dict, override: Dict) -> Dict:
    """深度合并字典"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 045 - 工具函数集合")
    print("=" * 60)

    # 测试工具函数
    print("\n1. 生成唯一 ID")
    print("-" * 40)
    print(f"用户 ID: {generate_id('user_')}")
    print(f"订单 ID: {generate_id('order_')}")
    print(f"通用 ID: {generate_id()}")

    print("\n2. 验证格式")
    print("-" * 40)
    print(f"邮箱 'test@example.com': {validate_email('test@example.com')}")
    print(f"邮箱 'invalid': {validate_email('invalid')}")
    print(f"手机号 '13800138000': {validate_phone('13800138000')}")
    print(f"手机号 '123': {validate_phone('123')}")

    print("\n3. 字符串处理")
    print("-" * 40)
    print(f"清理 '  hello  ': '{sanitize_string('  hello  ')}'")
    print(f"清理 123: '{sanitize_string(123)}'")

    print("\n4. 格式化")
    print("-" * 40)
    print(f"货币 1234.5: {format_currency(1234.5)}")
    print(f"货币 1234.5 USD: {format_currency(1234.5, 'USD')}")
    print(f"日期时间: {format_datetime(datetime.now())}")

    print("\n5. JSON 处理")
    print("-" * 40)
    data = {"name": "张三", "age": 25, "skills": ["Python", "JavaScript"]}
    json_str = to_json(data)
    print(f"JSON 字符串:\n{json_str}")
    parsed = parse_json(json_str)
    print(f"解析结果: {parsed}")

    print("\n6. 字典操作")
    print("-" * 40)
    nested = {"a": 1, "b": {"c": 2, "d": {"e": 3}}}
    flat = flatten_dict(nested)
    print(f"扁平化前: {nested}")
    print(f"扁平化后: {flat}")

    print("\n7. 列表操作")
    print("-" * 40)
    lst = [1, 2, 3, 4, 5, 6, 7, 8]
    chunks = chunk_list(lst, 3)
    print(f"分块: {chunks}")

    lst_with_dups = [1, 2, 2, 3, 3, 3, 4]
    unique = remove_duplicates(lst_with_dups)
    print(f"去重前: {lst_with_dups}")
    print(f"去重后: {unique}")

    print("\n8. 字典合并")
    print("-" * 40)
    dict1 = {"a": 1, "b": 2}
    dict2 = {"b": 3, "c": 4}
    merged = merge_dicts(dict1, dict2)
    print(f"合并: {merged}")

    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"d": 4, "e": 5}, "f": 6}
    deep_merged = deep_merge_dicts(base, override)
    print(f"深度合并: {deep_merged}")

    print("\n" + "=" * 60)
    print("工具函数集合演示完成！")
    print("=" * 60)
