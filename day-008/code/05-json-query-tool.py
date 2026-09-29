#!/usr/bin/env python3
"""
05-json-query-tool.py
Day 008 — 练习 5：嵌套 JSON 查询工具

使用点号路径语法查询嵌套字典/列表数据。
支持：基本路径、列表索引、通配符、递归搜索

可直接运行：python3 05-json-query-tool.py
"""

from typing import Any, Optional, List, Union


def json_query(data: Any, path: str) -> Optional[Any]:
    """
    使用点号路径语法查询嵌套 JSON 数据

    支持语法：
      "users.0.name"           → data["users"][0]["name"]
      "settings.theme.color"   → data["settings"]["theme"]["color"]
      "users.*.name"           → 所有用户的 name 列表（通配符）
      "..version"              → 递归搜索所有层级的 version（返回第一个匹配）
    """
    if not path:
        return data

    # 递归搜索语法：..key
    if path.startswith(".."):
        search_key = path[2:]
        return _recursive_search(data, search_key)

    # 解析路径
    parts = _parse_path(path)
    current = data

    for part in parts:
        if part == "*":
            # 通配符：如果 current 是列表，对每个元素继续执行剩余路径
            if isinstance(current, list):
                remaining = ".".join(parts[parts.index(part) + 1:])
                results = []
                for item in current:
                    result = json_query(item, remaining)
                    if result is not None:
                        results.append(result)
                return results
            else:
                return None
        else:
            current = _get_part(current, part)
            if current is None:
                return None

    return current


def _parse_path(path: str) -> List[str]:
    """解析点号路径为部件列表"""
    # 简单实现：按点分割
    # 注意：不支持包含点的键名
    return path.split(".")


def _get_part(data: Any, part: Union[str, int]) -> Optional[Any]:
    """
    从 data 中获取指定部件。
    part 可能是字符串键或整数索引
    """
    # 尝试整数索引（处理 list 索引）
    try:
        idx = int(part)
        if isinstance(data, (list, tuple)):
            if 0 <= idx < len(data):
                return data[idx]
            return None
    except (ValueError, TypeError):
        pass

    # 字典键访问
    if isinstance(data, dict):
        return data.get(part)

    # 属性访问（类对象）
    if hasattr(data, part):
        return getattr(data, part)

    return None


def _recursive_search(data: Any, key: str) -> Optional[Any]:
    """
    递归搜索所有层级，返回第一个匹配 key 的值
    """
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            result = _recursive_search(value, key)
            if result is not None:
                return result
    elif isinstance(data, (list, tuple)):
        for item in data:
            result = _recursive_search(item, key)
            if result is not None:
                return result

    return None


def json_query_all(data: Any, path: str) -> List[Any]:
    """
    查询所有匹配的结果（即使第一个匹配也继续搜索）
    适用于 .. 递归搜索
    """
    results = []

    if isinstance(data, dict):
        for key, value in data.items():
            if path.startswith(".."):
                search_key = path[2:]
                if key == search_key:
                    results.append(value)
                # 继续递归
                deeper = json_query_all(value, path)
                results.extend(deeper)
            else:
                result = json_query(data, path)
                if result is not None:
                    results.append(result)
    elif isinstance(data, (list, tuple)):
        for item in data:
            result = json_query_all(item, path)
            results.extend(result)

    return results


def json_set(data: dict, path: str, value: Any) -> bool:
    """
    设置嵌套路径的值（修改原字典）
    返回是否设置成功
    """
    parts = _parse_path(path)
    current = data

    for i, part in enumerate(parts[:-1]):
        next_part = parts[i + 1]

        try:
            next_is_index = isinstance(next_part, str) and next_part.lstrip('-').isdigit()
        except (ValueError, AttributeError):
            next_is_index = False

        if part not in current:
            # 自动创建中间结构
            current[part] = [] if next_is_index else {}

        current = current[part]
        if current is None:
            return False

    last_key = parts[-1]
    try:
        last_key = int(last_key)
    except (ValueError, TypeError):
        pass

    if isinstance(current, dict):
        current[last_key] = value
        return True
    elif isinstance(current, list) and isinstance(last_key, int):
        if 0 <= last_key < len(current):
            current[last_key] = value
            return True

    return False


def json_delete(data: dict, path: str) -> bool:
    """删除嵌套路径的键"""
    parts = _parse_path(path)
    current = data

    for part in parts[:-1]:
        current = _get_part(current, part)
        if current is None:
            return False

    last_key = parts[-1]
    try:
        last_key = int(last_key)
    except (ValueError, TypeError):
        pass

    if isinstance(current, dict) and last_key in current:
        del current[last_key]
        return True
    elif isinstance(current, list) and isinstance(last_key, int):
        if 0 <= last_key < len(current):
            del current[last_key]
            return True

    return False


def main():
    # 测试数据
    data = {
        "users": [
            {
                "name": "Alice",
                "age": 25,
                "address": {"city": "Beijing", "district": "Haidian"},
                "scores": [95, 87, 92],
            },
            {
                "name": "Bob",
                "age": 30,
                "address": {"city": "Shanghai", "district": "Pudong"},
                "scores": [78, 85, 90],
            },
        ],
        "settings": {
            "theme": {"color": "dark", "font_size": 14},
            "notifications": True,
        },
        "metadata": {
            "version": "2.0",
            "last_updated": "2024-01-15",
        },
    }

    print("=" * 60)
    print("  🔍 JSON 嵌套查询工具")
    print("=" * 60)
    print(f"\n  数据集概览: 3 个顶级键, {len(data['users'])} 个用户")

    # 测试各种查询
    tests = [
        ("users.0.name", "Alice"),
        ("users.1.address.city", "Shanghai"),
        ("users.0.scores.2", 92),
        ("settings.theme.color", "dark"),
        ("settings.theme", {"color": "dark", "font_size": 14}),
        ("metadata.version", "2.0"),
        ("users.2.name", None),  # 越界
        ("nonexistent.path", None),  # 不存在
    ]

    print("\n  📌 基本查询测试:")
    print(f"  {'路径':<30} {'预期':<30} {'结果'}")
    print(f"  {'-'*70}")

    for path, expected in tests:
        result = json_query(data, path)
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} {path:<30} {str(expected):<30} → {result}")

    print("\n  📌 通配符查询:")
    names = json_query(data, "users.*.name")
    print(f"     users.*.name  → {names}")

    ages = json_query(data, "users.*.age")
    print(f"     users.*.age   → {ages}")

    cities = json_query(data, "users.*.address.city")
    print(f"     users.*.address.city → {cities}")

    print("\n  📌 递归搜索（..语法）:")
    version = json_query(data, "..version")
    print(f"     ..version     → {version}")

    all_versions = json_query_all(data, "..version")
    print(f"     ..version (全部) → {all_versions}")

    print("\n  📌 路径设置:")
    print(f"     设置前: data['settings']['theme']['font_size'] = {data['settings']['theme']['font_size']}")
    json_set(data, "settings.theme.font_size", 16)
    print(f"     设置后: {data['settings']['theme']['font_size']}")

    json_set(data, "metadata.description", "JSON query demo")
    print(f"     新增键: {data['metadata']['description']}")

    print("\n  📌 路径删除:")
    print(f"     删除前: 'description' in metadata = {'description' in data['metadata']}")
    json_delete(data, "metadata.description")
    print(f"     删除后: 'description' in metadata = {'description' in data.get('metadata', {})}")

    print("\n" + "=" * 60)
    print("  ✅ JSON 查询工具演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
