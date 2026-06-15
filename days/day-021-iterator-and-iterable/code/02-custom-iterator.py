#!/usr/bin/env python3
"""
Day 021 - Custom Iterator Implementation
自定义迭代器实战：斐波那契、素数生成、二叉树遍历、分页
"""

from collections.abc import Iterator, Iterable
import math
import time


# ============================================================
# 1. 斐波那契迭代器
# ============================================================

class Fibonacci:
    """斐波那契数列迭代器

    可指定上限，避免无限生成。
    对比递归/迭代版本：迭代器版本可以按需取值，不需要一次性计算所有。
    """

    def __init__(self, max_count: int = None):
        """
        参数:
            max_count: 最大生成数量，None 表示无限
        """
        self.max_count = max_count
        self._count = 0
        self._a, self._b = 0, 1

    def __iter__(self):
        return self

    def __next__(self):
        if self.max_count is not None and self._count >= self.max_count:
            raise StopIteration

        if self._count == 0:
            self._count += 1
            return self._a

        self._count += 1
        self._a, self._b = self._b, self._a + self._b
        return self._a


def test_fibonacci():
    """测试斐波那契迭代器"""
    print("=" * 60)
    print("斐波那契迭代器")
    print("=" * 60)

    print("\n▶ 前 10 个斐波那契数:")
    fib = Fibonacci(max_count=10)
    print(f"   {list(fib)}")

    print("\n▶ 惰性取值：只取大于 100 的第一个值:")
    fib = Fibonacci()
    for val in fib:
        if val > 100:
            print(f"   第一个 > 100 的值: {val}")
            break

    print(f"\n▶ 检查类型:")
    fib = Fibonacci(max_count=5)
    print(f"   isinstance(fib, Iterable): {isinstance(fib, Iterable)}")
    print(f"   isinstance(fib, Iterator): {isinstance(fib, Iterator)}")


# ============================================================
# 2. 素数迭代器
# ============================================================

class PrimeIterator:
    """素数生成迭代器

    使用简单的试除法判断素数，展示迭代器如何封装算法逻辑。
    """

    def __init__(self, max_value: int = None):
        self.max_value = max_value
        self.current = 2  # 从第一个素数开始

    def __iter__(self):
        return self

    def _is_prime(self, n: int) -> bool:
        """判断是否为素数"""
        if n < 2:
            return False
        if n == 2:
            return True
        if n % 2 == 0:
            return False

        limit = int(math.sqrt(n)) + 1
        for i in range(3, limit, 2):
            if n % i == 0:
                return False
        return True

    def __next__(self):
        # 查找下一个素数
        while True:
            if self.max_value is not None and self.current > self.max_value:
                raise StopIteration

            candidate = self.current
            self.current += 1

            if self._is_prime(candidate):
                return candidate


def test_prime_iterator():
    """测试素数迭代器"""
    print("=" * 60)
    print("素数迭代器")
    print("=" * 60)

    print("\n▶ 100 以内的素数:")
    primes = PrimeIterator(max_value=100)
    prime_list = list(primes)
    print(f"   共 {len(prime_list)} 个: {prime_list}")

    print("\n▶ 前 20 个素数:")
    primes = PrimeIterator()
    first_20 = []
    for i, p in enumerate(primes):
        if i >= 20:
            break
        first_20.append(p)
    print(f"   {first_20}")


# ============================================================
# 3. 分页迭代器
# ============================================================

class PaginatedIterator:
    """分页迭代器

    将大数据分成小页，每页返回固定大小的元素。
    非常适合处理 API 分页、大列表分批处理等场景。
    """

    def __init__(self, data: list, page_size: int = 3):
        self.data = data
        self.page_size = page_size
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self.data):
            raise StopIteration

        start = self._index
        end = min(start + self.page_size, len(self.data))
        page = self.data[start:end]
        self._index = end
        return ("page", start // self.page_size, page)


def test_pagination():
    """测试分页迭代器"""
    print("=" * 60)
    print("分页迭代器")
    print("=" * 60)

    data = list(range(1, 11))  # [1, 2, ..., 10]
    print(f"\n▶ 数据: {data}")
    print(f"   每页 3 个元素")

    paginator = PaginatedIterator(data, page_size=3)
    for label, page_num, page_data in paginator:
        print(f"   第 {page_num + 1} 页: {page_data}")


# ============================================================
# 4. 可重置的迭代器（支持重复遍历）
# ============================================================

class ResettableIterable:
    """支持重复遍历的可迭代对象

    这不是迭代器——它每次都返回一个新的迭代器。
    这才是标准做法：容器类实现 __iter__，但不实现 __next__。
    """

    def __init__(self, data):
        self.data = data

    def __iter__(self):
        """每次都返回一个新的迭代器"""
        return ResettableIterator(self.data)


class ResettableIterator:
    """内部迭代器类"""

    def __init__(self, data):
        self.data = data
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.data):
            raise StopIteration
        value = self.data[self.index]
        self.index += 1
        return value


def test_resettable():
    """测试可重复遍历"""
    print("=" * 60)
    print("可重复遍历 vs 单次迭代器")
    print("=" * 60)

    # ✅ 可重复遍历
    container = ResettableIterable(['A', 'B', 'C'])
    print(f"\n▶ ResettableIterable（可重复遍历）:")
    print(f"   第一次: {list(container)}")
    print(f"   第二次: {list(container)}")
    print(f"   第三次: {list(container)}")

    # ❌ 单次迭代器
    it = iter(['A', 'B', 'C'])
    print(f"\n▶ 普通迭代器（只能一次）:")
    print(f"   第一次: {list(it)}")
    print(f"   第二次: {list(it)}")

    print(f"\n▶ isinstance(container, Iterable): {isinstance(container, Iterable)}")
    print(f"   isinstance(container, Iterator): {isinstance(container, Iterator)}")


# ============================================================
# 5. 二叉树遍历迭代器
# ============================================================

class TreeNode:
    """二叉树节点"""
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class InOrderIterator:
    """二叉树中序遍历迭代器

    使用栈来模拟递归遍历，实现在迭代器中逐步返回节点值。
    """

    def __init__(self, root):
        self.stack = []
        self._push_left(root)

    def _push_left(self, node):
        """将左子树全部入栈"""
        while node:
            self.stack.append(node)
            node = node.left

    def __iter__(self):
        return self

    def __next__(self):
        if not self.stack:
            raise StopIteration

        node = self.stack.pop()
        value = node.val

        # 处理右子树
        if node.right:
            self._push_left(node.right)

        return value


class PreOrderIterator:
    """二叉树前序遍历迭代器"""

    def __init__(self, root):
        self.stack = [root] if root else []

    def __iter__(self):
        return self

    def __next__(self):
        if not self.stack:
            raise StopIteration

        node = self.stack.pop()

        # 先右后左（栈是后进先出）
        if node.right:
            self.stack.append(node.right)
        if node.left:
            self.stack.append(node.left)

        return node.val


def build_sample_tree() -> TreeNode:
    """构建示例二叉树

        1
       / \
      2   3
     / \   \
    4   5   6
    """
    return TreeNode(1,
        TreeNode(2, TreeNode(4), TreeNode(5)),
        TreeNode(3, None, TreeNode(6))
    )


def test_tree_iterator():
    """测试二叉树遍历迭代器"""
    print("=" * 60)
    print("二叉树遍历迭代器")
    print("=" * 60)

    root = build_sample_tree()

    print("\n▶ 树结构:")
    print("       1")
    print("      / \\")
    print("     2   3")
    print("    / \\   \\")
    print("   4   5   6")

    print("\n▶ 中序遍历:")
    inorder = list(InOrderIterator(root))
    print(f"   {inorder}")

    print("\n▶ 前序遍历:")
    preorder = list(PreOrderIterator(root))
    print(f"   {preorder}")

    print("\n▶ 支持惰性取值:")
    it = InOrderIterator(root)
    print(f"   取第一个: {next(it)}")
    print(f"   取第二个: {next(it)}")
    print(f"   取第三个: {next(it)}")


# ============================================================
# 6. 迭代器性能对比
# ============================================================

def performance_comparison():
    """迭代器 vs 列表性能对比"""
    print("=" * 60)
    print("迭代器 vs 列表性能对比")
    print("=" * 60)

    n = 10**6

    # 1. 内存对比
    print(f"\n▶ 内存对比（n={n:,}）:")

    # 列表方式：立即创建全部
    import sys
    lst = list(range(n))
    lst_size = sys.getsizeof(lst) + lst[0].__sizeof__() * n

    # 迭代器方式：几乎为 0
    it = iter(range(n))
    it_size = sys.getsizeof(it)

    print(f"   列表内存:   约 {lst_size / 1024 / 1024:.2f} MB")
    print(f"   迭代器内存: 约 {it_size} 字节")

    # 2. 时间对比
    print(f"\n▶ 时间对比（仅筛选）:")

    def process_list(size):
        """使用列表过滤"""
        data = list(range(size))
        result = [x for x in data if x % 2 == 0]
        return len(result)

    def process_iterator(size):
        """使用迭代器过滤——不保留中间列表"""
        data = range(size)  # 本身就是惰性的
        result = [x for x in data if x % 2 == 0]
        return len(result)

    start = time.perf_counter()
    r1 = process_list(10**6)
    t1 = time.perf_counter() - start

    start = time.perf_counter()
    r2 = process_iterator(10**6)
    t2 = time.perf_counter() - start

    print(f"   列表方式:    {t1:.4f}s")
    print(f"   迭代器方式:  {t2:.4f}s")


# ============================================================
# 7. 迭代器组合使用
# ============================================================

class ComposeIterators:
    """组合多个迭代器的高级用法演示"""

    @staticmethod
    def filter_even(iterator):
        """过滤奇数的迭代器"""
        for x in iterator:
            if x % 2 == 0:
                yield x  # 使用生成器（明天的内容）简化

    @staticmethod
    def take(iterator, n):
        """取前 n 个元素的迭代器"""
        for i, x in enumerate(iterator):
            if i >= n:
                break
            yield x


def test_composition():
    """测试迭代器组合"""
    print("=" * 60)
    print("迭代器组合使用")
    print("=" * 60)

    print("\n▶ 链式处理: 前 5 个偶数")
    result = list(
        ComposeIterators.take(
            ComposeIterators.filter_even(
                range(1, 20)
            ),
            5
        )
    )
    print(f"   结果: {result}")

    print("\n▶ 每个操作都是惰性的:")
    print(f"   只有在 list() 调用时才真正计算")


# ============================================================
# Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("Day 021 — 自定义迭代器实战")
    print("=" * 60)

    test_fibonacci()
    test_prime_iterator()
    test_pagination()
    test_resettable()
    test_tree_iterator()
    performance_comparison()
    test_composition()

    print("\n" + "=" * 60)
    print("✅ 自定义迭代器实战完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
