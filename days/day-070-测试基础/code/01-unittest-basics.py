"""
Day 070 — unittest 基础
运行方式：python 01-unittest-basics.py
"""
import unittest


# ========== 被测试的代码 ==========

def add(a: int, b: int) -> int:
    """两数相加"""
    return a + b

def divide(a: float, b: float) -> float:
    """两数相除"""
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b

def is_even(n: int) -> bool:
    """判断是否为偶数"""
    return n % 2 == 0

def classify_age(age: int) -> str:
    """根据年龄分类"""
    if age < 0:
        raise ValueError("年龄不能为负数")
    if age < 13:
        return "儿童"
    elif age < 18:
        return "青少年"
    elif age < 60:
        return "成年"
    else:
        return "老年"


# ========== 测试类 ==========

class TestMathFunctions(unittest.TestCase):
    """测试数学函数"""

    def test_add_positive(self):
        """测试正数相加"""
        self.assertEqual(add(2, 3), 5)

    def test_add_negative(self):
        """测试负数相加"""
        self.assertEqual(add(-1, -1), -2)

    def test_add_zero(self):
        """测试加零"""
        self.assertEqual(add(5, 0), 5)

    def test_add_large_numbers(self):
        """测试大数"""
        self.assertEqual(add(1000000, 2000000), 3000000)

    def test_divide_normal(self):
        """测试正常除法"""
        self.assertAlmostEqual(divide(10, 3), 3.333, places=2)

    def test_divide_exact(self):
        """测试整除"""
        self.assertEqual(divide(10, 2), 5.0)

    def test_divide_by_zero(self):
        """测试除以零"""
        with self.assertRaises(ValueError) as context:
            divide(10, 0)
        self.assertEqual(str(context.exception), "除数不能为零")


class TestIsEven(unittest.TestCase):
    """测试偶数判断"""

    def test_even_numbers(self):
        """测试偶数"""
        self.assertTrue(is_even(0))
        self.assertTrue(is_even(2))
        self.assertTrue(is_even(4))
        self.assertTrue(is_even(-2))

    def test_odd_numbers(self):
        """测试奇数"""
        self.assertFalse(is_even(1))
        self.assertFalse(is_even(3))
        self.assertFalse(is_even(-1))


class TestClassifyAge(unittest.TestCase):
    """测试年龄分类"""

    def test_child(self):
        self.assertEqual(classify_age(10), "儿童")
        self.assertEqual(classify_age(0), "儿童")

    def test_teenager(self):
        self.assertEqual(classify_age(15), "青少年")
        self.assertEqual(classify_age(13), "青少年")

    def test_adult(self):
        self.assertEqual(classify_age(30), "成年")
        self.assertEqual(classify_age(18), "成年")

    def test_senior(self):
        self.assertEqual(classify_age(65), "老年")
        self.assertEqual(classify_age(60), "老年")

    def test_negative_age(self):
        with self.assertRaises(ValueError):
            classify_age(-1)


# ========== setUp / tearDown ==========

class TestWithSetup(unittest.TestCase):
    """演示 setUp/tearDown"""

    def setUp(self):
        """每个测试前执行"""
        self.data = [3, 1, 4, 1, 5, 9, 2, 6]
        print(f"\n  setUp: 准备数据 {self.data}")

    def tearDown(self):
        """每个测试后执行"""
        print(f"  tearDown: 清理完成")

    def test_length(self):
        self.assertEqual(len(self.data), 8)

    def test_sorted(self):
        self.assertEqual(sorted(self.data), [1, 1, 2, 3, 4, 5, 6, 9])

    def test_max(self):
        self.assertEqual(max(self.data), 9)

    def test_sum(self):
        self.assertEqual(sum(self.data), 31)


# ========== 运行 ==========
if __name__ == "__main__":
    unittest.main(verbosity=2)
