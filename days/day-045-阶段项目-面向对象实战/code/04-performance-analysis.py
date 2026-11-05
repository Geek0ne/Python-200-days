"""
Day 045 - OOP 性能分析
对比不同 OOP 实现方式的性能差异
"""

import time
import sys
from typing import List


class RegularClass:
    """普通类"""
    def __init__(self, x, y):
        self.x = x
        self.y = y


class SlottedClass:
    """使用 __slots__ 的类"""
    __slots__ = ['x', 'y']

    def __init__(self, x, y):
        self.x = x
        self.y = y


class DataClass:
    """使用 dataclass 的类"""
    def __init__(self, x, y):
        self.x = x
        self.y = y


def benchmark_creation(cls, n: int) -> float:
    """测试对象创建性能"""
    start = time.time()
    for _ in range(n):
        cls(1, 2)
    end = time.time()
    return end - start


def benchmark_attribute_access(obj, n: int) -> float:
    """测试属性访问性能"""
    start = time.time()
    for _ in range(n):
        _ = obj.x
        _ = obj.y
    end = time.time()
    return end - start


def benchmark_memory(cls, n: int) -> float:
    """测试内存使用"""
    objects = []
    for _ in range(n):
        objects.append(cls(1, 2))
    # 估算内存使用
    memory = sys.getsizeof(objects) + sum(sys.getsizeof(obj) for obj in objects)
    return memory / 1024  # 返回 KB


def main():
    print("=" * 60)
    print("Day 045 - OOP 性能分析")
    print("=" * 60)

    n = 100000  # 测试数量

    print(f"\n测试数量: {n}")
    print("-" * 40)

    # 1. 对象创建性能
    print("\n1. 对象创建性能")
    print("-" * 40)

    regular_time = benchmark_creation(RegularClass, n)
    slotted_time = benchmark_creation(SlottedClass, n)
    dataclass_time = benchmark_creation(DataClass, n)

    print(f"普通类: {regular_time:.4f} 秒")
    print(f"Slots 类: {slotted_time:.4f} 秒")
    print(f"DataClass: {dataclass_time:.4f} 秒")

    # 计算性能提升
    if regular_time > 0:
        print(f"\n性能对比:")
        print(f"Slots vs 普通类: {((regular_time - slotted_time) / regular_time * 100):.1f}% 提升")
        print(f"DataClass vs 普通类: {((regular_time - dataclass_time) / regular_time * 100):.1f}% 提升")

    # 2. 属性访问性能
    print("\n2. 属性访问性能")
    print("-" * 40)

    regular_obj = RegularClass(1, 2)
    slotted_obj = SlottedClass(1, 2)
    dataclass_obj = DataClass(1, 2)

    access_n = 1000000  # 访问次数

    regular_access = benchmark_attribute_access(regular_obj, access_n)
    slotted_access = benchmark_attribute_access(slotted_obj, access_n)
    dataclass_access = benchmark_attribute_access(dataclass_obj, access_n)

    print(f"普通类: {regular_access:.4f} 秒")
    print(f"Slots 类: {slotted_access:.4f} 秒")
    print(f"DataClass: {dataclass_access:.4f} 秒")

    # 3. 内存使用
    print("\n3. 内存使用")
    print("-" * 40)

    memory_n = 10000

    regular_memory = benchmark_memory(RegularClass, memory_n)
    slotted_memory = benchmark_memory(SlottedClass, memory_n)
    dataclass_memory = benchmark_memory(DataClass, memory_n)

    print(f"普通类: {regular_memory:.2f} KB")
    print(f"Slots 类: {slotted_memory:.2f} KB")
    print(f"DataClass: {dataclass_memory:.2f} KB")

    if regular_memory > 0:
        print(f"\n内存对比:")
        print(f"Slots vs 普通类: {((regular_memory - slotted_memory) / regular_memory * 100):.1f}% 节省")
        print(f"DataClass vs 普通类: {((regular_memory - dataclass_memory) / regular_memory * 100):.1f}% 节省")

    # 4. 继承性能
    print("\n4. 继承性能")
    print("-" * 40)

    class Base:
        def method(self):
            pass

    class Child(Base):
        def method(self):
            pass

    class GrandChild(Child):
        def method(self):
            pass

    def benchmark_inheritance(cls, n: int) -> float:
        start = time.time()
        for _ in range(n):
            obj = cls()
            obj.method()
        end = time.time()
        return end - start

    base_time = benchmark_inheritance(Base, n)
    child_time = benchmark_inheritance(Child, n)
    grandchild_time = benchmark_inheritance(GrandChild, n)

    print(f"基类: {base_time:.4f} 秒")
    print(f"子类: {child_time:.4f} 秒")
    print(f"孙类: {grandchild_time:.4f} 秒")

    # 5. 总结
    print("\n" + "=" * 60)
    print("性能分析总结")
    print("=" * 60)

    print("\n1. __slots__ 的优势:")
    print("   - 对象创建更快")
    print("   - 内存使用更少")
    print("   - 属性访问更快")
    print("   - 适用于需要大量实例的场景")

    print("\n2. 继承的影响:")
    print("   - 继承层级越深，性能越差")
    print("   - 方法调用需要遍历 MRO（方法解析顺序）")
    print("   - 建议保持继承层级简单")

    print("\n3. 使用建议:")
    print("   - 大量实例时使用 __slots__")
    print("   - 简单数据容器使用 dataclass")
    print("   - 避免过深的继承层级")
    print("   - 考虑使用组合代替继承")

    print("\n" + "=" * 60)
    print("性能分析完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
