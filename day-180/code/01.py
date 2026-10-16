# 原文件名：01-基础用法.py
"""基础用法示例 - pytest 基础测试"""
import pytest


def add(a, b):
    """两数相加"""
    return a + b


def test_add_basic():
    """测试基本加法"""
    result = add(2, 3)
    assert result == 5


def test_add_negative():
    """测试负数相加"""
    result = add(-1, -2)
    assert result == -3


def test_add_mixed():
    """测试正负混合"""
    result = add(-1, 1)
    assert result == 0


# parametrize 示例
@pytest.mark.parametrize("a, b, expected", [
    (0, 0, 0),
    (1, 2, 3),
    (-1, 1, 0),
    (100, 200, 300),
])
def test_add_parametrized(a, b, expected):
    """参数化测试 add 函数"""
    assert add(a, b) == expected