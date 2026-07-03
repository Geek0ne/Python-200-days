"""
Day 050 - 槽(__slots__) - 基础用法
演示：__slots__ 的基本概念、内存优化、属性访问
"""
import sys


# ============================================
# 1. 普通类 vs __slots__ 类
# ============================================

class PointNormal:
    """普通类 — 使用 __dict__ 存储属性"""

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


class PointSlots:
    """使用 __slots__ 的类 — 没有 __dict__"""

    __slots__ = ('x', 'y', 'z')

    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z


# ============================================
# 2. 基本测试
# ============================================

if __name__ == "__main__":
    print("=" * 50)
    print("Day 050 - 槽(__slots__) 基础用法")
    print("=" * 50)

    # 创建对象
    normal = PointNormal(1.0, 2.0, 3.0)
    slots = PointSlots(1.0, 2.0, 3.0)

    # 对比 __dict__
    print("\n--- __dict__ 对比 ---")
    print(f"普通类有 __dict__: {hasattr(normal, '__dict__')}")
    print(f"__slots__ 类有 __dict__: {hasattr(slots, '__dict__')}")
    print(f"普通类 __dict__: {normal.__dict__}")
    # slots.__dict__  # ❌ AttributeError

    # 属性访问
    print("\n--- 属性访问 ---")
    print(f"普通类: x={normal.x}, y={normal.y}, z={normal.z}")
    print(f"__slots__: x={slots.x}, y={slots.y}, z={slots.z}")

    # 内存大小
    print("\n--- 内存大小 ---")
    normal_size = sys.getsizeof(normal)
    slots_size = sys.getsizeof(slots)
    print(f"普通类对象大小: {normal_size} bytes")
    print(f"__slots__ 类对象大小: {slots_size} bytes")
    print(f"对象本身节省: {normal_size - slots_size} bytes ({(1-slots_size/normal_size)*100:.1f}%)")

    # 注意：普通类还有 __dict__ 的开销
    dict_size = sys.getsizeof(normal.__dict__)
    print(f"普通类 __dict__ 大小: {dict_size} bytes")
    print(f"实际总节省: {normal_size + dict_size - slots_size} bytes "
          f"({(1-slots_size/(normal_size+dict_size))*100:.1f}%)")

    # 动态添加属性
    print("\n--- 动态添加属性 ---")
    normal.new_attr = "可以添加"  # ✅ 普通类可以
    print(f"普通类添加新属性: {normal.new_attr}")

    try:
        slots.new_attr = "不允许"  # ❌ __slots__ 类不允许
    except AttributeError as e:
        print(f"__slots__ 类添加新属性失败: {e}")

    # 批量创建对比
    print("\n--- 批量创建对比 ---")
    n = 100000

    import time

    start = time.perf_counter()
    normal_list = [PointNormal(i, i*2, i*3) for i in range(n)]
    normal_time = time.perf_counter() - start

    start = time.perf_counter()
    slots_list = [PointSlots(i, i*2, i*3) for i in range(n)]
    slots_time = time.perf_counter() - start

    print(f"创建 {n} 个普通类对象: {normal_time:.3f}s")
    print(f"创建 {n} 个 __slots__ 类对象: {slots_time:.3f}s")
    print(f"速度比: {normal_time/slots_time:.2f}x")

    # 属性访问性能
    print("\n--- 属性访问性能 ---")
    iterations = 1000000

    start = time.perf_counter()
    for _ in range(iterations):
        _ = normal_list[0].x
    normal_access = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(iterations):
        _ = slots_list[0].x
    slots_access = time.perf_counter() - start

    print(f"普通类属性访问 {iterations} 次: {normal_access:.3f}s")
    print(f"__slots__ 类属性访问 {iterations} 次: {slots_access:.3f}s")
    print(f"加速比: {normal_access/slots_access:.2f}x")
