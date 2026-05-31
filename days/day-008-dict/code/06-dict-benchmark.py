#!/usr/bin/env python3
"""
06-dict-benchmark.py — Day 008 补充
字典性能基准测试套件

对比：list vs dict vs set 在不同操作下的性能差异
测试项目：查找、插入、删除、遍历、内存

可直接运行：python3 06-dict-benchmark.py
"""

import time
import random
import sys
from collections import defaultdict


# ============================================================
# 基准测试框架
# ============================================================

class Benchmark:
    """简易基准测试框架"""

    def __init__(self, name: str):
        self.name = name
        self.results = []

    def test(self, label: str, func, iterations: int = 1):
        """运行测试并记录"""
        # 预热
        func()

        # 计时
        start = time.perf_counter()
        for _ in range(iterations):
            func()
        elapsed = time.perf_counter() - start

        avg = elapsed / iterations
        self.results.append((label, elapsed, avg, iterations))
        return elapsed

    def report(self):
        """输出报告"""
        print(f"\n{'=' * 60}")
        print(f"  📊 {self.name}")
        print(f"{'=' * 60}")
        print(f"  {'操作':<25} {'总耗时':<12} {'平均':<12} {'次数'}")
        print(f"  {'-' * 60}")

        for label, total, avg, count in self.results:
            total_s = f"{total:.4f}s" if total < 60 else f"{total/60:.1f}m"
            avg_s = f"{avg*1e6:.2f}µs" if avg < 1 else f"{avg*1e3:.2f}ms" if avg < 60 else f"{avg:.2f}s"
            print(f"  {label:<25} {total_s:<12} {avg_s:<12} {count}")


# ============================================================
# 测试 1：查找性能（这是字典最强项）
# ============================================================

def test_lookup_performance(sizes=[100, 1000, 10_000, 100_000]):
    """对比 list 和 dict 在不同数据量下的查找性能"""
    print("\n" + "=" * 60)
    print("  🔍 Test 1: 查找性能对比（list vs dict vs set）")
    print("=" * 60)

    rows = []
    for size in sizes:
        # 准备数据
        keys = list(range(size))
        values = [f"val_{k}" for k in keys]
        data_list = list(zip(keys, values))
        data_dict = dict(zip(keys, values))
        data_set = set(keys)

        # 随机选择要查找的键（10% 命中，90% 未命中以模拟真实场景）
        search_keys = random.choices(keys, k=min(5000, size))
        # 混入一些不存在的键
        search_keys += [random.randint(size * 10, size * 20) for _ in range(len(search_keys) // 3)]
        random.shuffle(search_keys)

        # 列表查找（O(n)）
        found_list = 0
        start_list = time.perf_counter()
        for sk in search_keys:
            for k, v in data_list:
                if k == sk:
                    found_list += 1
                    break
        list_time = time.perf_counter() - start_list

        # 字典查找（O(1)）
        found_dict = 0
        start_dict = time.perf_counter()
        for sk in search_keys:
            if sk in data_dict:
                found_dict += 1
        dict_time = time.perf_counter() - start_dict

        # 集合查找（O(1)）
        found_set = 0
        start_set = time.perf_counter()
        for sk in search_keys:
            if sk in data_set:
                found_set += 1
        set_time = time.perf_counter() - start_set

        speedup_vs_list = f"{list_time / dict_time:.0f}x" if dict_time > 0 else "∞"
        rows.append((size, len(search_keys), list_time, dict_time, set_time, speedup_vs_list))

    # 输出表格
    print(f"\n  {'数据量':<10} {'查找次数':<10} {'列表(秒)':<12} {'字典(秒)':<12} {'集合(秒)':<12} {'加速比'}")
    print(f"  {'-' * 68}")
    for size, count, lt, dt, st, sp in rows:
        print(f"  {size:<10,} {count:<10,} {lt:<12.4f} {dt:<12.6f} {st:<12.6f} {sp}")

    print("\n  💡 结论：数据量越大，字典/集合相对列表的优势越明显！")


# ============================================================
# 测试 2：插入性能
# ============================================================

def test_insert_performance():
    """对比 list.append vs dict[key]=value"""
    print("\n" + "=" * 60)
    print("  📝 Test 2: 插入性能对比")
    print("=" * 60)

    sizes = [10_000, 100_000, 1_000_000]

    rows = []
    for n in sizes:
        # 列表插入（尾部追加）
        start = time.perf_counter()
        lst = []
        for i in range(n):
            lst.append(i)
        list_time = time.perf_counter() - start

        # 字典插入
        start = time.perf_counter()
        d = {}
        for i in range(n):
            d[i] = i
        dict_time = time.perf_counter() - start

        rows.append((n, list_time, dict_time))

    print(f"\n  {'数据量':<12} {'列表追加(秒)':<16} {'字典插入(秒)':<16} {'差异'}")
    print(f"  {'-' * 56}")
    for n, lt, dt in rows:
        diff = f"{abs(lt-dt)*1e3:.1f}ms"
        faster = "列表快" if lt < dt else "字典快"
        print(f"  {n:<12,} {lt:<16.4f} {dt:<16.4f} {diff} ({faster})")

    print("\n  💡 结论：尾部追加时列表稍快；字典插入需要哈希计算但仍是 O(1) amortized。")


# ============================================================
# 测试 3：遍历性能
# ============================================================

def test_iteration_performance():
    """对比遍历性能"""
    print("\n" + "=" * 60)
    print("  🔄 Test 3: 遍历性能对比")
    print("=" * 60)

    n = 1_000_000
    lst = list(range(n))
    d = {i: i * 2 for i in range(n)}

    bm = Benchmark("遍历对比")

    # 遍历列表
    def iter_list():
        total = 0
        for x in lst:
            total += x
        return total

    # 遍历字典 keys
    def iter_dict_keys():
        total = 0
        for k in d.keys():
            total += k
        return total

    # 遍历字典 items
    def iter_dict_items():
        total = 0
        for k, v in d.items():
            total += k + v
        return total

    bm.test("list 遍历", iter_list, 10)
    bm.test("dict keys() 遍历", iter_dict_keys, 10)
    bm.test("dict items() 遍历", iter_dict_items, 10)

    bm.report()

    print("\n  💡 结论：列表遍历最快（连续内存），dict keys() 次之，items() 有拆包开销。")


# ============================================================
# 测试 4：删除性能
# ============================================================

def test_deletion_performance():
    """对比 list.remove vs del dict[key]"""
    print("\n" + "=" * 60)
    print("  🗑️  Test 4: 删除性能对比")
    print("=" * 60)

    n = 50_000  # 数据量适当，避免列表删除 O(n) 太慢
    keys = list(range(n))
    random.shuffle(keys)

    # 列表删除（按值）
    lst = keys.copy()
    start = time.perf_counter()
    for k in keys[:1000]:  # 只测前 1000 个
        lst.remove(k)
    list_time = time.perf_counter() - start

    # 字典删除（按键）
    d = {k: k for k in keys}
    start = time.perf_counter()
    for k in keys[:1000]:
        del d[k]
    dict_time = time.perf_counter() - start

    print(f"\n  删除 1,000 个元素（{n:,} 数据中）")
    print(f"    list.remove(): {list_time:.4f}s (O(n) 逐个查找)")
    print(f"    del dict[key]: {dict_time:.6f}s (O(1) 哈希直接定位)")
    print(f"    字典快 {list_time / dict_time:.0f}x")

    print("\n  💡 结论：删除性能差距最大 — 字典 O(1) vs 列表 O(n)，量级差异！")


# ============================================================
# 测试 5：内存占用
# ============================================================

def test_memory_usage():
    """粗略对比内存占用（通过 sys.getsizeof）"""
    print("\n" + "=" * 60)
    print("  💾 Test 5: 内存占用对比")
    print("=" * 60)

    n = 100_000
    lst = list(range(n))
    d = {i: i for i in range(n)}

    # sys.getsizeof 只返回对象本身大小，不递归计算内含对象
    # 但用于比较仍有一定参考价值
    list_size = sys.getsizeof(lst)
    dict_size = sys.getsizeof(d)

    print(f"\n  存储 {n:,} 个整数:")
    print(f"    list:     {list_size / 1024:.1f} KB")
    print(f"    dict:     {dict_size / 1024:.1f} KB")
    print(f"    字典/列表: {dict_size / list_size:.1f}x")

    print("\n  💡 结论：字典内存开销大约是列表的 2~3 倍（存储哈希值+键+值）。")


# ============================================================
# 测试 6：defaultdict vs 普通 dict 带检查
# ============================================================

def test_defaultdict_performance():
    """对比 defaultdict 与普通 dict 的计数性能"""
    print("\n" + "=" * 60)
    print("  🛡️  Test 6: defaultdict vs 普通 dict 计数性能")
    print("=" * 60)

    n = 500_000
    # 生成大量数据，只有 100 个唯一值 — 模拟词频统计
    data = [random.randint(0, 99) for _ in range(n)]

    # 普通 dict
    start = time.perf_counter()
    counter = {}
    for x in data:
        if x not in counter:
            counter[x] = 0
        counter[x] += 1
    plain_time = time.perf_counter() - start

    # defaultdict
    start = time.perf_counter()
    dd = defaultdict(int)
    for x in data:
        dd[x] += 1
    dd_time = time.perf_counter() - start

    # Counter
    from collections import Counter
    start = time.perf_counter()
    c = Counter(data)
    counter_time = time.perf_counter() - start

    print(f"\n  统计 {n:,} 条数据（100 个唯一值）:")
    print(f"    dict + if not in:   {plain_time:.4f}s")
    print(f"    defaultdict(int):   {dd_time:.4f}s")
    print(f"    Counter:            {counter_time:.4f}s")
    print(f"    defaultdict 提升:   {plain_time / dd_time:.1f}x vs 普通 dict")


# ============================================================
# 测试 7：字典推导式 vs 循环
# ============================================================

def test_dict_comprehension_performance():
    """对比字典推导式与 for 循环"""
    print("\n" + "=" * 60)
    print("  ⚡ Test 7: 字典推导式 vs for 循环")
    print("=" * 60)

    n = 1_000_000
    numbers = list(range(n))

    # for 循环
    start = time.perf_counter()
    d1 = {}
    for x in numbers:
        d1[x] = x ** 2
    loop_time = time.perf_counter() - start

    # 字典推导式
    start = time.perf_counter()
    d2 = {x: x ** 2 for x in numbers}
    comp_time = time.perf_counter() - start

    print(f"\n  创建 {n:,} 条 x → x² 映射:")
    print(f"    for 循环:      {loop_time:.4f}s")
    print(f"    字典推导式:    {comp_time:.4f}s")
    print(f"    推导式提升:    {loop_time / comp_time:.2f}x")

    print("\n  💡 结论：字典推导式比 for 循环快 10-20%，语法也更简洁。")


# ============================================================
# 测试 8：dict.get vs 直接索引（含异常处理）
# ============================================================

def test_get_vs_bracket():
    """对比 dict[key] vs dict.get(key)"""
    print("\n" + "=" * 60)
    print("  🎯 Test 8: dict[key] vs dict.get(key) 性能")
    print("=" * 60)

    n = 1_000_000
    d = {i: i for i in range(1000)}  # 只有 1000 个键
    lookups = [random.randint(-500, 1500) for _ in range(n)]  # 约 40% 命中

    # dict[key] + 异常处理
    start = time.perf_counter()
    results1 = []
    for k in lookups:
        try:
            results1.append(d[k])
        except KeyError:
            results1.append(None)
    bracket_time = time.perf_counter() - start

    # dict.get(key, None)
    start = time.perf_counter()
    results2 = [d.get(k) for k in lookups]
    get_time = time.perf_counter() - start

    print(f"\n  查找 {n:,} 次（1000 键池，40% 命中率）:")
    print(f"    d[k] + try/except:  {bracket_time:.4f}s")
    print(f"    d.get(k, default):  {get_time:.4f}s")
    print(f"    get 方法快:         {bracket_time / get_time:.1f}x")

    # 纯命中场景（不存在 KeyError） 
    lookups_hit = [random.randint(0, 999) for _ in range(n)]

    start = time.perf_counter()
    for k in lookups_hit:
        _ = d[k]
    bracket_hit = time.perf_counter() - start

    start = time.perf_counter()
    for k in lookups_hit:
        _ = d.get(k)
    get_hit = time.perf_counter() - start

    print(f"\n  纯命中 {n:,} 次:")
    print(f"    d[k] (纯命中):  {bracket_hit:.4f}s")
    print(f"    d.get(k) (纯命中): {get_hit:.4f}s")

    print("\n  💡 结论：有 KeyError 时 get 明显更快；纯命中场景二者几乎无差别。")


# ============================================================
# 主入口
# ============================================================

def main():
    print("=" * 60)
    print("  📊 Dictionary 全方位性能基准测试")
    print("  🐍 Python " + sys.version.split()[0])
    print("=" * 60)

    test_lookup_performance([100, 1000, 10_000])

    test_insert_performance()

    test_iteration_performance()

    test_deletion_performance()

    test_memory_usage()

    test_defaultdict_performance()

    test_dict_comprehension_performance()

    test_get_vs_bracket()

    print("\n" + "=" * 60)
    print("  ✅ 基准测试完成！")
    print("\n  📌 核心结论:")
    print("  1. 查 找 — dict O(1) vs list O(n), 千倍级差距")
    print("  2. 插 入 — dict O(1), list O(1) amortized（尾部追加）")
    print("  3. 删 除 — dict O(1), list O(n)（按值删除需遍历）")
    print("  4. 内 存 — dict 约为 list 的 2-3 倍")
    print("  5. 遍 历 — list > dict.keys() > dict.items()")
    print("  6. 推 导 式 — 比 for 循环快 10-20%")
    print("  7. get 方 法 — 有 KeyError 场景下优于 try/except")
    print("=" * 60)


if __name__ == "__main__":
    main()
