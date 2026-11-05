"""
mathutils - 数学计算工具包

提供基础运算、统计计算和单位转换功能。
"""

from mathutils.basic import (
    add, subtract, multiply, divide,
    power, sqrt, factorial, gcd, lcm,
)

from mathutils.statistics import (
    mean, median, mode, variance, std_dev,
)

from mathutils.conversion import (
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    km_to_miles,
    miles_to_km,
    kg_to_lbs,
    lbs_to_kg,
)

__version__ = '0.1.0'
__all__ = [
    'add', 'subtract', 'multiply', 'divide',
    'power', 'sqrt', 'factorial', 'gcd', 'lcm',
    'mean', 'median', 'mode', 'variance', 'std_dev',
    'celsius_to_fahrenheit', 'fahrenheit_to_celsius',
    'km_to_miles', 'miles_to_km', 'kg_to_lbs', 'lbs_to_kg',
]
