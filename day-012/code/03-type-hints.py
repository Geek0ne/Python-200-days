#!/usr/bin/env python3
"""
03-type-hints.py — 函数注解与类型提示

演示 Python 3 的函数注解语法、常见类型注解模式、
注解的存储机制（__annotations__），以及 mypy 静态检查的示例。

运行: python3 03-type-hints.py
"""

# Python 3.10+ 原生支持 X | Y 语法，无需 typing.Union
# Python 3.9+ 原生支持 list[int] 等泛型，无需 typing.List
# 兼容性: Python 3.8+ 需要 from __future__ import annotations

import sys


# ============================================================
# 1. 基本函数注解语法
# ============================================================
print("=" * 60)
print("1️⃣  基本函数注解语法")
print("=" * 60)


def greet(name: str) -> str:
    """
    参数 name 标注为 str 类型
    返回值标注为 str 类型
    """
    return f"你好, {name}!"


# Python 不强制类型约束 —— 传入 int 也能运行！
result = greet(42)
print(f"greet(42) = {result}  (类型: {type(result).__name__})")
print("   → 说明: 注解只是提示，不强制检查类型")


# ============================================================
# 2. __annotations__ 存储机制
# ============================================================
print("\n" + "=" * 60)
print("2️⃣  __annotations__ 字典（注解的存储位置）")
print("=" * 60)


def add(x: int, y: int) -> int:
    return x + y


def get_user(name: str, age: int) -> dict:
    return {"name": name, "age": age}


# 所有注解存储在函数的 __annotations__ 属性中
print(f"\nadd.__annotations__  = {add.__annotations__}")
print(f"get_user.__annotations__ = {get_user.__annotations__}")

# 可以修改 __annotations__
add.__annotations__["x"] = float
print(f"修改后 add.__annotations__ = {add.__annotations__}")

# 注解值可以是任何表达式（不一定是类型）
print(f"\n注解值可以是任何表达式:")


def labeled_func(
    name: "用户名（长度 2-20 字符）",
    age: "年龄（正整数）"
) -> "格式化后的用户信息字符串":
    return f"{name}({age})"


print(f"  labeled_func.__annotations__ = {labeled_func.__annotations__}")


# ============================================================
# 3. 常见类型注解
# ============================================================
print("\n" + "=" * 60)
print("3️⃣  常见类型注解模式")
print("=" * 60)

from typing import Optional, Union, Any, Callable, List, Dict, Tuple, Set

# Python 3.9+ 可以直接用 list[int] 而不用 List[int]
# Python 3.10+ 可以直接用 int | None 而不用 Optional[int]
# 为兼容性，本文件使用新语法（假设 Python 3.9+）

print("\n--- 基础类型 ---")


def calculate_bmi(weight: float, height: float) -> float:
    """基础类型注解"""
    return weight / (height ** 2)


print(f"  BMI: {calculate_bmi(70, 1.75):.2f}")

print("\n--- 容器类型 ---")


def process_scores(scores: list[int]) -> dict[str, float]:
    """列表和字典注解"""
    return {
        "sum": sum(scores),
        "avg": sum(scores) / len(scores) if scores else 0.0,
        "max": max(scores),
        "min": min(scores),
    }


result = process_scores([85, 92, 78, 95, 88])
print(f"  scores: {result}")


def find_indices(target: str, text: str) -> list[int]:
    """返回字符串中所有匹配位置的索引"""
    indices = []
    start = 0
    while True:
        pos = text.find(target, start)
        if pos == -1:
            break
        indices.append(pos)
        start = pos + 1
    return indices


print(f"\n  查找 'ab' 在 'ababcab' 中: {find_indices('ab', 'ababcab')}")

print("\n--- 可选类型 (Optional/Union) ---")

# Python 3.10+ 语法: int | None
# Python 3.9 语法: Optional[int]
def find_user(user_id: int) -> dict | None:
    """可能返回 None 的函数"""
    users = {
        1: {"name": "张三", "age": 25},
        2: {"name": "李四", "age": 30},
    }
    return users.get(user_id)  # 不存在时返回 None


u1 = find_user(1)
u2 = find_user(999)
print(f"  find_user(1) = {u1}")
print(f"  find_user(999) = {u2}")


def parse_number(text: str) -> int | float | None:
    """联合类型：可能返回 int、float 或 None"""
    try:
        if "." in text:
            return float(text)
        return int(text)
    except (ValueError, TypeError):
        return None


print(f"\n  parse_number('42') = {parse_number('42')}")
print(f"  parse_number('3.14') = {parse_number('3.14')}")
print(f"  parse_number('abc') = {parse_number('abc')}")


print("\n--- Callable（可调用对象）---")


def apply_twice(func: Callable[[int], int], value: int) -> int:
    """接收一个函数作为参数"""
    return func(func(value))


def square(x: int) -> int:
    return x * x


print(f"  apply_twice(square, 3) = {apply_twice(square, 3)}")  # (3²)² = 81

print("\n--- Any（任意类型）---")


def debug_print(value: Any, prefix: str = "") -> None:
    """Any 表示可以是任何类型；None 表示无返回值"""
    print(f"{prefix}{value!r} (类型: {type(value).__name__})")


debug_print(42, "整数: ")
debug_print("hello", "字符串: ")
debug_print([1, 2, 3], "列表: ")


# ============================================================
# 4. 复杂类型注解：嵌套类型
# ============================================================
print("\n" + "=" * 60)
print("4️⃣  复杂嵌套类型注解")
print("=" * 60)


def analyze_grades(grades: dict[str, list[int]]) -> dict[str, dict[str, float]]:
    """
    分析多门课程的成绩

    参数: {"数学": [85, 92, 78], "英语": [88, 95, 90]}
    返回: {"数学": {"avg": 85.0, "max": 92, "min": 78}, ...}
    """
    result: dict[str, dict[str, float]] = {}
    for subject, scores in grades.items():
        result[subject] = {
            "avg": sum(scores) / len(scores),
            "max": max(scores),
            "min": min(scores),
        }
    return result


data = {
    "数学": [85, 92, 78, 95],
    "英语": [88, 95, 90],
    "物理": [76, 82, 91, 88],
}
print(f"  分析结果:")
for subject, stats in analyze_grades(data).items():
    print(f"    {subject}: 平均{stats['avg']:.1f} 最高{stats['max']} 最低{stats['min']}")


# ============================================================
# 5. 实战：带完整类型注解的数据清洗函数
# ============================================================
print("\n" + "=" * 60)
print("5️⃣  实战：带完整类型注解的数据清洗")
print("=" * 60)

# 定义类型别名（Type Alias）
# Python 3.12+ 支持 type Record = dict[str, str]
# 兼容写法：
Record = Dict[str, str]
Report = Dict[str, Union[int, float, str, List[str]]]

def clean_data(raw_data: list[Record]) -> tuple[list[Record], Report]:
    """
    清洗数据并生成报告

    Args:
        raw_data: 原始数据列表（每条记录是字符串字典）

    Returns:
        元组 (清洗后的数据, 清洗报告)
    """
    valid: list[Record] = []
    total = len(raw_data)
    invalid_count = 0
    invalid_ids: list[str] = []

    for record in raw_data:
        if record.get("name") and record.get("age"):
            valid.append(record)
        else:
            invalid_count += 1
            invalid_ids.append(record.get("id", "unknown"))

    report: Report = {
        "total_records": total,
        "valid_count": len(valid),
        "invalid_count": invalid_count,
        "invalid_ids": invalid_ids,
        "clean_rate": f"{len(valid) / total * 100:.1f}%" if total else "N/A",
    }

    return valid, report


# 测试数据
raw = [
    {"id": "001", "name": "张三", "age": "25"},
    {"id": "002", "name": "", "age": "30"},        # 空名字 → 无效
    {"id": "003", "name": "李四", "age": "28"},
    {"id": "004", "name": "王五"},                  # 缺 age → 无效
    {"id": "005", "name": "赵六", "age": "35"},
]

valid_data, report = clean_data(raw)
print(f"  有效数据: {valid_data}")
print(f"  清洗报告:")
for key, value in report.items():
    print(f"    {key}: {value}")


# ============================================================
# 6. TypeVar 与泛型函数
# ============================================================
print("\n" + "=" * 60)
print("6️⃣  泛型函数（TypeVar）")
print("=" * 60)

from typing import TypeVar

T = TypeVar("T")       # 任意类型
U = TypeVar("U")       # 任意类型
Number = TypeVar("Number", int, float)  # 只允许 int 或 float


def first_element(items: list[T]) -> T | None:
    """
    返回列表的第一个元素（泛型）

    类型参数 T 在调用时被实际类型替换：
    - first_element([1, 2, 3]) → T 为 int
    - first_element(["a", "b"]) → T 为 str
    """
    if items:
        return items[0]
    return None


print(f"  first_element([1, 2, 3]) = {first_element([1, 2, 3])!r}")
print(f"  first_element(['a', 'b']) = {first_element(['a', 'b'])!r}")
print(f"  first_element([]) = {first_element([])!r}")


def swap_pair(pair: tuple[T, U]) -> tuple[U, T]:
    """交换元组中两个元素的顺序（使用两个类型参数）"""
    return pair[1], pair[0]


print(f"\n  swap_pair((1, 'hello')) = {swap_pair((1, 'hello'))}")


# ============================================================
# 7. 静态类型检查：mypy 的使用方法
# ============================================================
print("\n" + "=" * 60)
print("7️⃣  静态类型检查（mypy）")
print("=" * 60)

print("""
mypy 是一个静态类型检查工具，它分析代码中的类型注解，
在**运行前**发现类型不匹配的问题。

安装:
  pip install mypy

使用方法:
  mypy 03-type-hints.py

检查示例（以下代码如果被 mypy 检查，会报错）:

  def add(x: int, y: int) -> int:
      return x + y

  # mypy 会发现这行有类型错误:
  result = add("hello", "world")  # mypy 报错!
""")


def check_mypy_available() -> bool:
    """检查 mypy 是否安装"""
    try:
        import mypy
        return True
    except ImportError:
        return False


if check_mypy_available():
    print("\n  ✅ mypy 已安装，你可以运行: mypy 03-type-hints.py")
else:
    print("\n  ❌ mypy 未安装，运行 pip install mypy 安装")


# ============================================================
# 8. 何时使用 Type Hints
# ============================================================
print("\n" + "=" * 60)
print("📋 Type Hints 使用建议")
print("=" * 60)

guidance = """
┌───────────────────┬───────────┬──────────────────────────────────┐
│ 场景              │ 建议      │ 理由                             │
├───────────────────┼───────────┼──────────────────────────────────┤
│ 学习/练习         │ 可选      │ 帮助理解类型，但别被类型困住       │
│ 个人脚本 (<200行) │ 可不加    │ 自己看懂就够了                    │
│ 中小型项目         │ 核心函数   │ 提高可读性，IDE 自动补全         │
│ 大型项目           │ 全面添加  │ 配合 mypy 做 CI 检查            │
│ 库/API 开发        │ 必须     │ 使用者需要明确的接口              │
│ 教学代码           │ 推荐     │ 帮助学生理解数据和类型            │
└───────────────────┴───────────┴──────────────────────────────────┘

核心原则:
  - 参数和返回值类型 → 加注解 🎯
  - 函数内部变量类型 → 看情况（复杂时可加）
  - 多使用 Optional 标注可能为 None 的情况
  - 使用 TypeVar 提高泛型函数的可读性
"""
print(guidance)
