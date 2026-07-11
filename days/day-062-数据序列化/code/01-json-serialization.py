#!/usr/bin/env python3
"""
Day 062 - 数据序列化
示例 1: JSON 序列化基础与进阶用法

本示例演示 Python json 模块的核心功能，包括：
1. 基础序列化/反序列化
2. 美化输出与中文处理
3. 自定义类型编码
4. 流式处理大文件
5. 性能对比与最佳实践

运行方式: python3 01-json-serialization.py
"""

import json
import math
import time
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

print("=" * 60)
print("📦 JSON 序列化 —— 基础用法")
print("=" * 60)

# ─── 1. 基础序列化 ───

print("\n--- 1. 基础序列化 ---")

# Python 对象
data = {
    "name": "Alice",
    "age": 30,
    "is_student": False,
    "scores": [95, 87, 92],
    "address": {
        "city": "Beijing",
        "district": "Haidian"
    },
    "tags": None
}

# dumps: Python 对象 → JSON 字符串
json_str = json.dumps(data)
print(f"原始 JSON:\n{json_str}")

# loads: JSON 字符串 → Python 对象
restored = json.loads(json_str)
print(f"\n反序列化恢复: {restored}")
print(f"类型: {type(restored)}")
print(f"name == restored['name']: {'Alice' == restored['name']}")

# ⚠️ 注意：JSON 中的 true/false/null 映射为 Python 的 True/False/None
assert restored["is_student"] is False
assert restored["tags"] is None

# ─── 2. 美化输出 ───

print("\n\n--- 2. 美化输出 ---")

# indent 参数控制缩进
pretty_json = json.dumps(data, indent=2, ensure_ascii=False)
print(f"美化输出（indent=2）:\n{pretty_json}")

# sort_keys 按键排序
sorted_json = json.dumps(data, indent=2, sort_keys=True)
print(f"\n按键排序:\n{sorted_json}")

# separators 控制分隔符，用于最小化体积
compact_json = json.dumps(data, separators=(",", ":"))
print(f"\n紧凑输出（最小体积）:\n{compact_json}")
print(f"原始长度: {len(json_str)}, 紧凑长度: {len(compact_json)}")

# ─── 3. 中文处理 ───

print("\n\n--- 3. 中文处理 ---")

chinese_data = {
    "name": "张三",
    "city": "北京",
    "description": "Python 开发者"
}

# 默认 ensure_ascii=True，中文会被转义为 \uXXXX
default_encoding = json.dumps(chinese_data)
print(f"默认编码（中文转义）:\n{default_encoding}")

# ensure_ascii=False 保留原始中文
proper_encoding = json.dumps(chinese_data, ensure_ascii=False, indent=2)
print(f"\n关闭 ASCII 转义:\n{proper_encoding}")

# ─── 4. 自定义类型编码 ───

print("\n\n--- 4. 自定义类型编码 ---")


class CustomEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，支持更多 Python 类型"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return {"__type__": "datetime", "value": obj.isoformat()}
        if isinstance(obj, date):
            return {"__type__": "date", "value": obj.isoformat()}
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return {"__type__": "bytes", "value": obj.hex()}
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, complex):
            return {"__type__": "complex", "real": obj.real, "imag": obj.imag}
        # 如果还是无法处理，调用父类抛出 TypeError
        return super().default(obj)


def custom_decoder(dct):
    """自定义 JSON 解码器，配合 CustomEncoder"""
    if "__type__" in dct:
        type_name = dct["__type__"]
        if type_name == "datetime":
            return datetime.fromisoformat(dct["value"])
        if type_name == "date":
            return date.fromisoformat(dct["value"])
        if type_name == "bytes":
            return bytes.fromhex(dct["value"])
        if type_name == "complex":
            return complex(dct["real"], dct["imag"])
    return dct


# 包含特殊类型的复杂数据
complex_data = {
    "current_time": datetime.now(),
    "today": date.today(),
    "price": Decimal("19.99"),
    "binary": b"hello",
    "tags": {"python", "json", "serialization"},  # set 类型
    "phase": complex(1, 2)  # 复数
}

# 编码
encoded = json.dumps(complex_data, cls=CustomEncoder, indent=2, ensure_ascii=False)
print(f"自定义类型编码结果:\n{encoded}")

# 解码
decoded = json.loads(encoded, object_hook=custom_decoder)
print(f"\n自定义类型解码结果:")
for key, value in decoded.items():
    print(f"  {key}: {type(value).__name__} = {value}")

# ─── 5. 文件读写 ───

print("\n\n--- 5. 文件读写 ---")

temp_file = Path("/tmp/day062_example.json")

# 写入 JSON 文件
with open(temp_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"写入文件: {temp_file}")

# 读取 JSON 文件
with open(temp_file, "r", encoding="utf-8") as f:
    loaded_data = json.load(f)
print(f"从文件读取: {loaded_data}")

# 清理
temp_file.unlink()

# ─── 6. 流式处理大 JSON 文件 ───

print("\n\n--- 6. 流式处理（适合大文件） ---")

# 当 JSON 文件很大时（GB 级别），一次性 json.load() 会占用过多内存
# 使用 iterative 解析器可以逐行处理

# 模拟一个大 JSON 数组
large_data = [{"id": i, "value": f"item_{i}"} for i in range(10000)]

print(f"准备写入 10000 条记录...")

large_file = Path("/tmp/day062_large.json")
with open(large_file, "w") as f:
    json.dump(large_data, f)

file_size_mb = large_file.stat().st_size / 1024 / 1024
print(f"文件大小: {file_size_mb:.2f} MB")

# 流式读取（逐行处理 JSON 数组元素）
# 使用 io.TextIOWrapper + JSONDecoder.raw_decode 实现流式解析
print("\n流式读取前 5 条:")
with open(large_file, "r", encoding="utf-8") as f:
    # 跳过 [
    f.read(1)
    decoder = json.JSONDecoder()
    # 读取并解析每个元素
    buffer = ""
    count = 0
    while count < 5:
        chunk = f.read(1024)
        if not chunk:
            break
        buffer += chunk
        try:
            obj, idx = decoder.raw_decode(buffer)
            print(f"  id={obj['id']}, value={obj['value']}")
            buffer = buffer[idx:].lstrip(", \n")
            count += 1
        except json.JSONDecodeError:
            # 需要读取更多数据才能完成解析
            continue

# 清理
large_file.unlink()

# ─── 7. 性能对比 ───

print("\n\n--- 7. 性能对比 ---")

test_data = {"key": "value" * 1000, "numbers": list(range(1000)), "nested": {"a": 1, "b": 2}}

N = 10000

# 测试序列化
start = time.perf_counter()
for _ in range(N):
    json.dumps(test_data)
serialize_time = time.perf_counter() - start

# 测试反序列化
json_str = json.dumps(test_data)
start = time.perf_counter()
for _ in range(N):
    json.loads(json_str)
deserialize_time = time.perf_counter() - start

print(f"序列化 {N} 次: {serialize_time:.3f} 秒 ({serialize_time/N*1000:.3f} ms/次)")
print(f"反序列化 {N} 次: {deserialize_time:.3f} 秒 ({deserialize_time/N*1000:.3f} ms/次)")

# ─── 8. 常见陷阱与避坑 ───

print("\n\n--- 8. 常见陷阱与避坑 ---")

# 陷阱 1: tuple 被序列化为 list
tuple_data = (1, 2, 3)
tuple_json = json.dumps(tuple_data)
tuple_restored = json.loads(tuple_json)
print(f"原始: {type(tuple_data).__name__}, 恢复后: {type(tuple_restored).__name__}")
# 如果需要 tuple，需要自定义转换

# 陷阱 2: float 特殊值
special_floats = {
    "inf": float("inf"),
    "neg_inf": float("-inf"),
    "nan": float("nan")
}
try:
    json.dumps(special_floats)
except ValueError as e:
    print(f"JSON 不支持 inf/nan: {e}")
    # 解决方案：手动替换
    fixed = json.dumps(special_floats, default=lambda x: str(x))
    print(f"  替代方案: {fixed}")

# 陷阱 3: dict 键只能是字符串
dict_with_int_key = {1: "one", 2: "two"}
dict_json = json.dumps(dict_with_int_key)
dict_restored = json.loads(dict_json)
print(f"原始键类型: int, 恢复后键类型: {type(list(dict_restored.keys())[0]).__name__}")
# JSON 要求键是字符串，数字键会被自动转换为字符串

# 陷阱 4: 重复键
dup_json = '{"name": "Alice", "name": "Bob"}'
dup_result = json.loads(dup_json)
print(f"重复键 JSON 解析结果: {dup_result}")  # 后一个值覆盖前一个

print("\n✅ JSON 序列化示例完成！")
