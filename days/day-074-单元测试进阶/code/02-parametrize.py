"""
Day 074 — 参数化测试
运行方式：python 02-parametrize.py
"""
import pytest
import math


# ========== 1. 基本参数化 ==========


@pytest.mark.parametrize("input,expected", [
    ("hello", 5),
    ("", 0),
    ("a", 1),
    ("hello world", 11),
])
def test_string_length(input, expected):
    """测试字符串长度"""
    assert len(input) == expected


@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_addition(a, b, expected):
    """测试加法"""
    assert a + b == expected


# ========== 2. 嵌套参数化 ==========


@pytest.mark.parametrize("x", [1, 2, 3])
@pytest.mark.parametrize("y", [10, 20])
def test_multiply(x, y):
    """测试乘法（6个组合）"""
    result = x * y
    assert result > 0
    assert result == x * y


# ========== 3. 使用 ids 自定义测试名称 ==========


@pytest.mark.parametrize("value,expected", [
    (None, False),
    (0, False),
    ("", False),
    ([], False),
    ({}, False),
    (1, True),
    ("hello", True),
    ([1, 2], True),
], ids=["none", "zero", "empty-string", "empty-list",
        "empty-dict", "nonzero", "non-empty-string", "non-empty-list"])
def test_bool_conversion(value, expected):
    """测试布尔转换"""
    assert bool(value) == expected


# ========== 4. 使用 pytest.param ==========


@pytest.mark.parametrize("input,expected", [
    pytest.param(1, 1.0, id="int-to-float"),
    pytest.param(2.5, 2.5, id="float-to-float"),
    pytest.param("3", 3.0, id="str-to-float"),
])
def test_convert_to_float(input, expected):
    """测试转换为浮点数"""
    assert float(input) == expected


# ========== 5. 实际应用：数学函数测试 ==========


@pytest.mark.parametrize("x,expected", [
    (0, 0),
    (1, 1),
    (4, 2),
    (9, 3),
    (16, 4),
    (25, 5),
])
def test_sqrt(x, expected):
    """测试平方根"""
    assert math.sqrt(x) == expected


@pytest.mark.parametrize("x,expected", [
    (0, 1),
    (1, 1),
    (2, 2),
    (3, 6),
    (4, 24),
    (5, 120),
])
def test_factorial(x, expected):
    """测试阶乘"""
    assert math.factorial(x) == expected


# ========== 6. 参数化 vs 循环 ==========


# ❌ 不推荐：循环写测试
def test_bad_practice():
    """不推荐的循环测试"""
    test_cases = [
        (1, 2, 3),
        (0, 0, 0),
        (-1, 1, 0),
    ]
    for a, b, expected in test_cases:
        assert a + b == expected  # 失败时无法知道是哪个用例


# ✅ 推荐：参数化
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (0, 0, 0),
    (-1, 1, 0),
])
def test_addition_param(a, b, expected):
    """参数化测试"""
    assert a + b == expected


# ========== 7. 运行测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 参数化测试演示")
    print("=" * 60)
    print()
    pytest.main([__file__, "-v"])
