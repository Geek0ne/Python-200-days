"""单位转换模块"""


def celsius_to_fahrenheit(c: float) -> float:
    """摄氏度 → 华氏度"""
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f: float) -> float:
    """华氏度 → 摄氏度"""
    return (f - 32) * 5 / 9


def km_to_miles(km: float) -> float:
    """公里 → 英里"""
    return km * 0.621371


def miles_to_km(miles: float) -> float:
    """英里 → 公里"""
    return miles / 0.621371


def kg_to_lbs(kg: float) -> float:
    """公斤 → 磅"""
    return kg * 2.20462


def lbs_to_kg(lbs: float) -> float:
    """磅 → 公斤"""
    return lbs / 2.20462
