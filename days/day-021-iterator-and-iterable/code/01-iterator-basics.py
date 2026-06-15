#!/usr/bin/env python3
"""
Day 021 - Iterator Basics
迭代器协议实现、for 循环底层模拟、__getitem__ 回退
"""

from collections.abc import Iterable, Iterator


# ============================================================
# 1. 手动实现 for 循环（底层原理模拟）
# ============================================================

def simulate_for_loop(iterable):
    """模拟 Python for 循环的底层实现

    Python 的 for x in iterable: 实际上等价于：

        _it = iter(iterable)
        while True:
            try:
                x = next(_it)
            except StopIteration:
                break
            # 循环体
        del _it
    """
    print(f"  📦 步骤1: 调用 iter({type(iterable).__name__})")
    _it = iter(iterable)
    print(f"  🔄 获得迭代器: {type(_it).__name__}")

    print(f"  🔁 步骤2: 开始 while 循环调用 next()")
    while True:
        try:
            x = next(_it)
            print(f"    → next() 返回值: {x!r}")
        except StopIteration:
            print(f"  ⏹️  步骤3: 捕获 StopIteration，循环结束")
            break
        # 模拟循环体：什么都不做

    print(f"  🧹 步骤4: 清理迭代器")
    del _it
    print()


def test_for_loop_simulation():
    """测试 for 循环模拟"""
    print("=" * 60)
    print("for 循环底层模拟")
    print("=" * 60)

    print("\n▶ 遍历列表 [10, 20, 30]:")
    simulate_for_loop([10, 20, 30])

    print("▶ 遍历字符串 'AB':")
    simulate_for_loop('AB')

    print("▶ 遍历空列表 []:")
    simulate_for_loop([])


# ============================================================
# 2. 迭代器协议实现 — 简单计数器
# ============================================================

class Counter:
    """实现迭代器协议的计数器

    演示 __iter__ 和 __next__ 的基本用法
    """

    def __init__(self, start: int = 0, end: int = 10):
        self.current = start
        self.end = end

    def __iter__(self):
        """返回迭代器自身

        迭代器协议要求 __iter__ 返回迭代器对象。
        对于本身就是迭代器的类，返回 self。
        """
        print(f"    __iter__() 被调用 → 返回 self (reset to {self.__class__.__name__})")
        self.current = 0  # 重置为初始值，以便重新开始
        return self

    def __next__(self):
        """返回下一个元素

        如果没有更多元素，抛出 StopIteration
        """
        if self.current >= self.end:
            print(f"    __next__(): {self.current} >= {self.end} → StopIteration")
            raise StopIteration

        value = self.current
        self.current += 1
        print(f"    __next__(): 返回 {value}")
        return value


def test_counter():
    """测试基本计数器迭代器"""
    print("=" * 60)
    print("迭代器协议实现 — Counter")
    print("=" * 60)

    print("\n▶ 创建 Counter(0, 5):")
    counter = Counter(start=0, end=5)

    print("\n▶ 使用 for 循环:")
    for x in counter:
        print(f"     循环体: x = {x}")

    print("\n▶ 检查类型:")
    print(f"   isinstance(counter, Iterable): {isinstance(counter, Iterable)}")
    print(f"   isinstance(counter, Iterator): {isinstance(counter, Iterator)}")


# ============================================================
# 3. 手动使用 next() 遍历
# ============================================================

def test_manual_iteration():
    """手动使用 iter() 和 next() 遍历"""
    print("=" * 60)
    print("手动迭代演示")
    print("=" * 60)

    data = [10, 20, 30]
    print(f"\n▶ 数据: {data}")

    it = iter(data)  # 获取迭代器
    print(f"   迭代器类型: {type(it).__name__}")

    # 手动 next
    print(f"   next(it) = {next(it)}")
    print(f"   next(it) = {next(it)}")
    print(f"   next(it) = {next(it)}")

    try:
        next(it)
    except StopIteration:
        print("   next(it) → StopIteration: 迭代器已耗尽 ✅")

    # 验证：迭代器只能遍历一次
    print("\n▶ 迭代器只能用一次:")
    it2 = iter([1, 2])
    print(f"   第一次遍历:")
    for x in it2:
        print(f"     {x}")

    print(f"   第二次遍历:")
    for x in it2:
        print(f"     {x}")  # 不执行！
    print(f"     (空 — 迭代器已耗尽)")


# ============================================================
# 4. 原始迭代器协议（str 等）内部实现模拟
# ============================================================

class StringIterator:
    """模拟字符串迭代器内部实现"""

    def __init__(self, s: str):
        self.s = s
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.s):
            raise StopIteration
        char = self.s[self.index]
        self.index += 1
        return char


def test_string_iterator():
    """测试字符串迭代器"""
    print("=" * 60)
    print("字符串迭代器模拟")
    print("=" * 60)

    s = "Hello"
    print(f"\n▶ 字符串 '{s}' 的迭代过程:")

    it = StringIterator(s)
    chars = []
    while True:
        try:
            c = next(it)
            chars.append(c)
        except StopIteration:
            break

    print(f"   迭代结果: {''.join(chars)}")
    print(f"   原字符串: {s}")
    print(f"   匹配: {''.join(chars) == s}")


# ============================================================
# 5. __getitem__ 回退机制
# ============================================================

class OldStyleIterable:
    """旧式可迭代对象——只有 __getitem__，没有 __iter__

    Python 会回退通过 __getitem__ 来实现迭代：
    - 从 index=0 开始调用 __getitem__(i)
    - 捕获 IndexError 转为 StopIteration
    """

    def __init__(self, data):
        self.data = data

    def __getitem__(self, index):
        """旧式迭代协议：按索引取值"""
        if index >= len(self.data):
            raise IndexError(f"index {index} out of range")
        print(f"   __getitem__({index}) → {self.data[index]}")
        return self.data[index]


def test_getitem_fallback():
    """测试 __getitem__ 回退机制"""
    print("=" * 60)
    print("__getitem__ 回退机制")
    print("=" * 60)

    obj = OldStyleIterable([10, 20, 30])

    print("\n▶ 检查类型:")
    print(f"   has __iter__: {hasattr(obj, '__iter__')}")
    print(f"   has __getitem__: {hasattr(obj, '__getitem__')}")
    print(f"   isinstance(obj, Iterable): {isinstance(obj, Iterable)}")
    print(f"   isinstance(obj, Iterator): {isinstance(obj, Iterator)}")

    print("\n▶ for 循环遍历:")
    for x in obj:
        print(f"     循环体: x = {x}")

    # 获得的是 sequence iterator
    print("\n▶ iter() 返回的类型:")
    it = iter(obj)
    print(f"   {type(it).__name__}")


# ============================================================
# 6. 迭代器的惰性求值演示
# ============================================================

class LazyRange:
    """惰性求值的 range 模拟

    和 Python 3 的 range() 一样，不是一次性生成所有值，
    而是在需要时才计算。
    """

    def __init__(self, start: int, end: int, step: int = 1):
        self.start = start
        self.end = end
        self.step = step

    def __iter__(self):
        return LazyRangeIterator(self.start, self.end, self.step)


class LazyRangeIterator:
    def __init__(self, start: int, end: int, step: int):
        self.current = start
        self.end = end
        self.step = step

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.end:
            raise StopIteration
        value = self.current
        self.current += self.step
        return value


def test_lazy_evaluation():
    """测试惰性求值"""
    print("=" * 60)
    print("惰性求值演示")
    print("=" * 60)

    print("\n▶ LazyRange(0, 5):")
    r = LazyRange(0, 5)
    print(f"   创建后: r = {r}")
    print(f"   立即转换为列表: {list(r)}")

    print("\n▶ 内存对比（概念演示）:")
    import sys

    # 真实 range 也是惰性的
    r1 = range(10**6)
    l1 = list(range(10**6))

    print(f"   range(1_000_000) 大小:    {sys.getsizeof(r1):>8} 字节")
    print(f"   list(range(1_000_000)) 大小: {sys.getsizeof(l1):>8} 字节")

    ratio = sys.getsizeof(l1) / sys.getsizeof(r1)
    print(f"   内存差距约 {ratio:.0f} 倍!")


# ============================================================
# 7. 无限迭代器演示
# ============================================================

class InfiniteCounter:
    """无限递增的迭代器"""

    def __init__(self, start: int = 0):
        self.current = start

    def __iter__(self):
        return self

    def __next__(self):
        value = self.current
        self.current += 1
        return value


def test_infinite_iterator():
    """测试无限迭代器"""
    print("=" * 60)
    print("无限迭代器演示")
    print("=" * 60)

    print("\n▶ InfiniteCounter(100) — 只取前 5 个:")
    counter = InfiniteCounter(start=100)
    for i, val in enumerate(counter):
        if i >= 5:
            break
        print(f"   {val}")

    print("\n▶ 无限迭代器必须手动终止！")
    print(f"   否则会无限执行下去。")

    print("\n▶ 配合 itertools.islice 使用:")
    import itertools
    counter = InfiniteCounter(start=0)
    first_10 = list(itertools.islice(counter, 10))
    print(f"   islice 取前 10 个: {first_10}")


# ============================================================
# 8. 迭代器陷阱
# ============================================================

def test_iterator_traps():
    """展示迭代器的常见陷阱"""
    print("=" * 60)
    print("迭代器常见陷阱")
    print("=" * 60)

    # 陷阱 1: 迭代器只能遍历一次
    print("\n⚠️ 陷阱 1: 迭代器只能遍历一次")
    nums = iter([1, 2, 3])
    print(f"   第一次: {list(nums)}")
    print(f"   第二次: {list(nums)} (已耗尽!)")

    # 陷阱 2: 迭代时修改列表
    print("\n⚠️ 陷阱 2: 迭代时修改集合")
    items = [1, 2, 3, 4, 5]
    print(f"   原始: {items}")
    for item in items[:]:  # 使用切片副本
        if item % 2 == 0:
            items.remove(item)
    print(f"   移除偶数后: {items}")

    # 陷阱 3: 确认迭代器类型
    print("\n⚠️ 陷阱 3: 区分可迭代对象和迭代器")
    lst = [1, 2, 3]
    it = iter(lst)
    print(f"   list 是 Iterable: {isinstance(lst, Iterable)}")
    print(f"   list 是 Iterator: {isinstance(lst, Iterator)}")
    print(f"   iter(list) 是 Iterator: {isinstance(it, Iterator)}")
    print(f"   list 有 __iter__: {hasattr(lst, '__iter__')}")
    print(f"   list 有 __next__: {hasattr(lst, '__next__')}")


# ============================================================
# 9. Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("Day 021 — 迭代器基础")
    print("=" * 60)

    test_for_loop_simulation()
    test_counter()
    test_manual_iteration()
    test_string_iterator()
    test_getitem_fallback()
    test_lazy_evaluation()
    test_infinite_iterator()
    test_iterator_traps()

    print("\n" + "=" * 60)
    print("✅ Day 021 迭代器基础完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
