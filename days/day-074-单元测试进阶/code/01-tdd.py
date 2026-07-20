"""
Day 074 — TDD 流程实战
运行方式：python 01-tdd.py
"""
import pytest


# ========== TDD 第一步：写测试 ==========


class TestStringCalculator:
    """字符串计算器测试（TDD 风格）"""

    def test_empty_string(self):
        """空字符串返回 0"""
        assert add("") == 0

    def test_single_number(self):
        """单个数字返回自身"""
        assert add("1") == 1

    def test_two_numbers(self):
        """两个数字相加"""
        assert add("1,2") == 3

    def test_multiple_numbers(self):
        """多个数字相加"""
        assert add("1,2,3,4,5") == 15

    def test_custom_delimiter(self):
        """自定义分隔符"""
        assert add("//;\n1;2;3") == 6

    def test_negative_numbers(self):
        """负数抛出异常"""
        with pytest.raises(ValueError, match="负数不允许"):
            add("1,-2,3")

    def test_numbers_greater_than_1000(self):
        """大于1000的数字忽略"""
        assert add("1000,1001,2") == 1002


# ========== TDD 第二步：实现 ==========


def add(numbers: str) -> int:
    """字符串计算器

    Args:
        numbers: 逗号分隔的数字字符串，支持自定义分隔符

    Returns:
        数字之和

    Raises:
        ValueError: 包含负数时抛出
    """
    if not numbers:
        return 0

    # 处理自定义分隔符
    if numbers.startswith("//"):
        delimiter = numbers[2]
        numbers = numbers[4:]

    # 分割并转换为整数
    nums = [int(n) for n in numbers.split(",")]

    # 检查负数
    negatives = [n for n in nums if n < 0]
    if negatives:
        raise ValueError(f"负数不允许: {negatives}")

    # 过滤大于1000的数字
    nums = [n for n in nums if n <= 1000]

    return sum(nums)


# ========== TDD 第三步：运行测试 ==========

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TDD 实战：字符串计算器")
    print("=" * 60)
    print()
    print("运行测试...")
    print()
    pytest.main([__file__, "-v"])
