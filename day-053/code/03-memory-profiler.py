"""
Day 053 - 实战：内存分析工具
主题：内存分析与优化
"""

import gc
import sys
from collections import defaultdict
from datetime import datetime
from functools import wraps
import time


# ============================================================
# 1. 内存分析器
# ============================================================
print("=" * 60)
print("1. 内存分析器")
print("=" * 60)

class MemoryProfiler:
    """内存分析工具"""

    def __init__(self):
        self._snapshots = []

    def snapshot(self, label=""):
        """获取内存快照"""
        gc.collect()
        objects = gc.get_objects()

        type_counts = defaultdict(int)
        type_sizes = defaultdict(int)

        for obj in objects:
            type_name = type(obj).__name__
            type_counts[type_name] += 1
            try:
                type_sizes[type_name] += sys.getsizeof(obj)
            except:
                pass

        total_size = sum(type_sizes.values())

        snapshot = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "total_objects": len(objects),
            "total_size": total_size,
            "type_counts": dict(type_counts),
            "type_sizes": dict(type_sizes)
        }

        self._snapshots.append(snapshot)
        return snapshot

    def diff(self, index1=-2, index2=-1):
        """对比两个快照"""
        if len(self._snapshots) < 2:
            print("需要至少两个快照")
            return None

        snap1 = self._snapshots[index1]
        snap2 = self._snapshots[index2]

        diff = {
            "objects_diff": snap2["total_objects"] - snap1["total_objects"],
            "size_diff": snap2["total_size"] - snap1["total_size"],
            "type_diff": {}
        }

        all_types = set(list(snap1["type_counts"].keys()) + list(snap2["type_counts"].keys()))
        for type_name in all_types:
            count1 = snap1["type_counts"].get(type_name, 0)
            count2 = snap2["type_counts"].get(type_name, 0)
            if count1 != count2:
                diff["type_diff"][type_name] = count2 - count1

        return diff

    def print_report(self):
        """打印内存报告"""
        if not self._snapshots:
            print("没有快照数据")
            return

        latest = self._snapshots[-1]
        print(f"\n{'='*60}")
        print(f"内存报告 - {latest['label']} ({latest['timestamp']})")
        print(f"{'='*60}")

        print(f"\n总对象数: {latest['total_objects']}")
        print(f"总内存: {latest['total_size'] / 1024:.2f} KB")

        print(f"\n占用最多的类型 (Top 10):")
        sorted_types = sorted(
            latest["type_sizes"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        for type_name, size in sorted_types:
            count = latest["type_counts"][type_name]
            print(f"  {type_name}: {count} 个, {size / 1024:.2f} KB")

        if len(self._snapshots) >= 2:
            diff = self.diff()
            print(f"\n与上一次快照对比:")
            print(f"  对象数变化: {'+' if diff['objects_diff'] > 0 else ''}{diff['objects_diff']}")
            print(f"  内存变化: {'+' if diff['size_diff'] > 0 else ''}{diff['size_diff'] / 1024:.2f} KB")

            if diff["type_diff"]:
                print(f"  类型变化:")
                for type_name, count_change in sorted(diff["type_diff"].items(), key=lambda x: abs(x[1]), reverse=True)[:5]:
                    print(f"    {type_name}: {'+' if count_change > 0 else ''}{count_change}")


# 使用
profiler = MemoryProfiler()

# 快照 1
profiler.snapshot("初始状态")

# 创建一些对象
data = {f"key_{i}": [j for j in range(100)] for i in range(100)}

# 快照 2
profiler.snapshot("创建数据后")

# 删除数据
del data
gc.collect()

# 快照 3
profiler.snapshot("清理后")

profiler.print_report()


# ============================================================
# 2. 函数内存分析装饰器
# ============================================================
print("\n" + "=" * 60)
print("2. 函数内存分析装饰器")
print("=" * 60)

def memory_profile(func):
    """内存分析装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        gc.collect()
        before_objects = len(gc.get_objects())
        before_size = sum(sys.getsizeof(obj) for obj in gc.get_objects()[:1000])

        result = func(*args, **kwargs)

        gc.collect()
        after_objects = len(gc.get_objects())
        after_size = sum(sys.getsizeof(obj) for obj in gc.get_objects()[:1000])

        objects_diff = after_objects - before_objects
        size_diff = after_size - before_size

        print(f"\n📊 {func.__name__} 内存分析:")
        print(f"  对象数: {before_objects} -> {after_objects} ({'+' if objects_diff > 0 else ''}{objects_diff})")
        print(f"  内存变化: {'+' if size_diff > 0 else ''}{size_diff / 1024:.2f} KB")

        return result
    return wrapper

@memory_profile
def process_data(n):
    """处理数据"""
    return [dict(zip(range(100), range(100))) for _ in range(n)]

# 测试
result = process_data(500)
del result
gc.collect()


# ============================================================
# 3. 循环引用检测器
# ============================================================
print("\n" + "=" * 60)
print("3. 循环引用检测器")
print("=" * 60)

class CycleDetector:
    """循环引用检测器"""

    def __init__(self):
        self._visited = set()
        self._cycles = []

    def detect_cycles(self):
        """检测循环引用"""
        gc.collect()
        self._visited = set()
        self._cycles = []

        for obj in gc.get_objects():
            obj_id = id(obj)
            if obj_id not in self._visited:
                self._check_cycle(obj, set())

        return self._cycles

    def _check_cycle(self, obj, path):
        """检查单个对象的循环引用"""
        obj_id = id(obj)

        if obj_id in path:
            # 发现循环
            cycle_start = list(path).index(obj_id)
            cycle = list(path)[cycle_start:] + [obj_id]
            self._cycles.append(cycle)
            return

        if obj_id in self._visited:
            return

        self._visited.add(obj_id)
        path.add(obj_id)

        # 检查所有引用
        referents = gc.get_referents(obj)
        for ref in referents:
            if id(ref) not in self._visited:
                self._check_cycle(ref, path.copy())

        path.discard(obj_id)

    def report(self):
        """打印检测报告"""
        cycles = self.detect_cycles()
        print(f"\n检测到 {len(cycles)} 个循环引用")

        for i, cycle in enumerate(cycles[:5]):
            print(f"\n循环 {i+1}:")
            for obj_id in cycle:
                try:
                    obj = gc.get_objects()
                    for o in obj:
                        if id(o) == obj_id:
                            print(f"  {type(o).__name__}: {str(o)[:50]}")
                            break
                except:
                    print(f"  对象 ID: {obj_id}")


# 测试
class CycleNode:
    def __init__(self, name):
        self.name = name
        self.ref = None

a = CycleNode("A")
b = CycleNode("B")
c = CycleNode("C")
a.ref = b
b.ref = c
c.ref = a  # 循环引用

detector = CycleDetector()
detector.report()


# ============================================================
# 4. 内存优化建议
# ============================================================
print("\n" + "=" * 60)
print("4. 内存优化建议")
print("=" * 60)

class RegularClass:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

class OptimizedClass:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

# 对比
regular = RegularClass(1, 2, 3)
optimized = OptimizedClass(1, 2, 3)

print(f"RegularClass 实例大小: {sys.getsizeof(regular)} bytes")
print(f"OptimizedClass 实例大小: {sys.getsizeof(optimized)} bytes")
print(f"节省: {sys.getsizeof(regular) - sys.getsizeof(optimized)} bytes")

# 列表 vs 生成器
print(f"\n列表 vs 生成器:")
list_data = [i for i in range(100000)]
gen_data = (i for i in range(100000))
print(f"列表大小: {sys.getsizeof(list_data)} bytes")
print(f"生成器大小: {sys.getsizeof(gen_data)} bytes")


# ============================================================
# 5. 实战：简易内存监控器
# ============================================================
print("\n" + "=" * 60)
print("5. 实战：简易内存监控器")
print("=" * 60)

class MemoryMonitor:
    """简易内存监控器"""

    def __init__(self):
        self._threshold = 100000  # 对象数阈值
        self._alert_callback = None

    def set_threshold(self, threshold):
        self._threshold = threshold

    def set_alert_callback(self, callback):
        self._alert_callback = callback

    def check(self):
        """检查内存状态"""
        gc.collect()
        object_count = len(gc.get_objects())

        status = {
            "object_count": object_count,
            "threshold": self._threshold,
            "is_over": object_count > self._threshold
        }

        if status["is_over"] and self._alert_callback:
            self._alert_callback(status)

        return status

    def auto_cleanup(self):
        """自动清理"""
        before = len(gc.get_objects())
        gc.collect()
        after = len(gc.get_objects())
        cleaned = before - after
        print(f"  自动清理: {cleaned} 个对象")
        return cleaned


# 使用
monitor = MemoryMonitor()
monitor.set_threshold(50000)

def alert_handler(status):
    print(f"  ⚠️ 内存警告: 对象数 {status['object_count']} 超过阈值 {status['threshold']}")

monitor.set_alert_callback(alert_handler)

# 测试
print("检查内存状态:")
status = monitor.check()
print(f"  对象数: {status['object_count']}, 超过阈值: {status['is_over']}")

# 创建大量对象
data = [list(range(100)) for _ in range(10000)]
status = monitor.check()
print(f"  创建后对象数: {status['object_count']}, 超过阈值: {status['is_over']}")

# 清理
del data
monitor.auto_cleanup()
