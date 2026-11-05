"""基础运算模块"""


def add(*args: float) -> float:
    """加法"""
    return sum(args)


def subtract(a: float, b: float) -> float:
    """减法"""
    return a - b


def multiply(*args: float) -> float:
    """乘法"""
    result = 1
    for n in args:
        result *= n
    return result


def divide(a: float, b: float) -> float:
    """除法"""
    if b == 0:
        raise ZeroDivisionError("除数不能为 0")
    return a / b


def power(base: float, exp: float) -> float:
    """乘方"""
    return base ** exp


def sqrt(n: float) -> float:
    """平方根"""
    if n < 0:
        raise ValueError("负数没有实数平方根")
    return n ** 0.5


def factorial(n: int) -> int:
    """阶乘"""
    if n < 0:
        raise ValueError("负数没有阶乘")
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def gcd(a: int, b: int) -> int:
    """最大公约数（欧几里得算法）"""
    while b:
        a, b = b, a % b
    return abs(a)


def lcm(a: int, b: int) -> int:
    """最小公倍数"""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)
