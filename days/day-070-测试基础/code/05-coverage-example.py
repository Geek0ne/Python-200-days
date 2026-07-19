"""
Day 070 — 测试覆盖率示例
运行方式：
  pytest 05-coverage-example.py --cov=. --cov-report=term-missing
  pytest 05-coverage-example.py --cov=. --cov-report=html
"""
import pytest


# ========== 被测试的代码 ==========

def classify_number(n: int) -> str:
    """根据数字分类"""
    if not isinstance(n, int):
        raise TypeError("必须是整数")
    if n < 0:
        return "负数"
    elif n == 0:
        return "零"
    elif n % 2 == 0:
        return "正偶数"
    else:
        return "正奇数"

def validate_email(email: str) -> bool:
    """简单的邮箱验证"""
    if not email:
        return False
    if "@" not in email:
        return False
    if "." not in email.split("@")[-1]:
        return False
    return True

def calculate_discount(price: float, is_vip: bool = False) -> float:
    """计算折扣价格"""
    if price < 0:
        raise ValueError("价格不能为负")
    if price == 0:
        return 0.0
    
    discount = 0.1 if is_vip else 0.05
    return round(price * (1 - discount), 2)

def fibonacci(n: int) -> int:
    """计算斐波那契数列"""
    if n < 0:
        raise ValueError("n 不能为负数")
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# ========== 测试函数 ==========

class TestClassifyNumber:
    def test_negative(self):
        assert classify_number(-5) == "负数"
    
    def test_zero(self):
        assert classify_number(0) == "零"
    
    def test_positive_even(self):
        assert classify_number(4) == "正偶数"
    
    def test_positive_odd(self):
        assert classify_number(3) == "正奇数"
    
    def test_type_error(self):
        with pytest.raises(TypeError):
            classify_number("abc")


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") is True
    
    def test_no_at(self):
        assert validate_email("userexample.com") is False
    
    def test_no_dot(self):
        assert validate_email("user@example") is False
    
    def test_empty(self):
        assert validate_email("") is False


class TestCalculateDiscount:
    def test_normal_price(self):
        assert calculate_discount(100) == 95.0
    
    def test_vip_price(self):
        assert calculate_discount(100, is_vip=True) == 90.0
    
    def test_zero_price(self):
        assert calculate_discount(0) == 0.0
    
    def test_negative_price(self):
        with pytest.raises(ValueError):
            calculate_discount(-10)


class TestFibonacci:
    def test_fibonacci(self):
        assert fibonacci(0) == 0
        assert fibonacci(1) == 1
        assert fibonacci(5) == 5
        assert fibonacci(10) == 55
    
    def test_fibonacci_negative(self):
        with pytest.raises(ValueError):
            fibonacci(-1)


# 运行覆盖率：
# pip install pytest-cov
# pytest 05-coverage-example.py --cov=. --cov-report=term-missing
# pytest 05-coverage-example.py --cov=. --cov-report=html
