"""
Day 070 — pytest 基础
运行方式：pytest 02-pytest-basics.py -v
"""
import pytest


# ========== 被测试的代码 ==========

def greet(name: str) -> str:
    """打招呼"""
    if not name:
        return "Hello, World!"
    return f"Hello, {name}!"

def factorial(n: int) -> int:
    """计算阶乘"""
    if n < 0:
        raise ValueError("n 不能为负数")
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fizzbuzz(n: int) -> str:
    """FizzBuzz 问题"""
    if n % 15 == 0:
        return "FizzBuzz"
    elif n % 3 == 0:
        return "Fizz"
    elif n % 5 == 0:
        return "Buzz"
    return str(n)

def is_palindrome(s: str) -> bool:
    """判断回文"""
    s = s.lower().replace(" ", "")
    return s == s[::-1]


# ========== 测试函数（pytest 风格） ==========

def test_greet_normal():
    assert greet("Alice") == "Hello, Alice!"

def test_greet_empty():
    assert greet("") == "Hello, World!"

def test_greet_special_chars():
    assert greet("世界") == "Hello, 世界!"

def test_factorial():
    assert factorial(5) == 120
    assert factorial(0) == 1
    assert factorial(1) == 1

def test_factorial_negative():
    with pytest.raises(ValueError):
        factorial(-1)

def test_fizzbuzz():
    assert fizzbuzz(1) == "1"
    assert fizzbuzz(3) == "Fizz"
    assert fizzbuzz(5) == "Buzz"
    assert fizzbuzz(15) == "FizzBuzz"
    assert fizzbuzz(7) == "7"

def test_palindrome():
    assert is_palindrome("racecar") is True
    assert is_palindrome("hello") is False
    assert is_palindrome("A man a plan a canal Panama") is True

# ========== 参数化测试 ==========

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (0, 0),
    (-1, -2),
    (100, 200),
])
def test_double(input, expected):
    """参数化测试——一个函数多组数据"""
    assert input * 2 == expected

@pytest.mark.parametrize("a,b,expected", [
    (1, 1, 2),
    (2, 3, 5),
    (-1, 1, 0),
    (0, 0, 0),
    (100, 200, 300),
])
def test_add(a, b, expected):
    assert a + b == expected

@pytest.mark.parametrize("s,expected", [
    ("racecar", True),
    ("hello", False),
    ("", True),
    ("a", True),
    ("ab", False),
])
def test_is_palindrome(s, expected):
    assert is_palindrome(s) is expected


# ========== 异常测试 ==========

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        1 / 0

def test_value_error_message():
    with pytest.raises(ValueError, match="不能为负"):
        factorial(-5)


# ========== 运行 ==========
# pytest 02-pytest-basics.py -v
# pytest 02-pytest-basics.py -v -s  # 显示 print
# pytest 02-pytest-basics.py -k "fizzbuzz" -v  # 按名称过滤
# pytest 02-pytest-basics.py -x  # 第一个失败就停止
