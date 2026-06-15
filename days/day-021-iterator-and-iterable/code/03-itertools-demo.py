#!/usr/bin/env python3
"""
Day 021 - itertools 模块应用实战
count, cycle, chain, zip_longest, islice, groupby, product 等
"""

import itertools
import operator
import time


# ============================================================
# 1. count — 无限计数器
# ============================================================

def demo_count():
    """count(start, step) — 无限等差数列"""
    print("=" * 60)
    print("itertools.count() — 无限计数器")
    print("=" * 60)

    print("\n▶ count(10, 2.5) — 从 10 开始，步长 2.5:")
    counter = itertools.count(start=10, step=2.5)
    for i, val in enumerate(counter):
        if i >= 5:
            break
        print(f"   {i}: {val}")

    print("\n▶ 配合 enumerate 实现自定义编号:")
    fruits = ['apple', 'banana', 'cherry']
    ids = itertools.count(start=1001, step=1)
    for fruit in fruits:
        print(f"   {next(ids)}: {fruit}")

    print("\n▶ 配合 zip 使用（代替 range(len)）:")
    names = ['Alice', 'Bob', 'Charlie']
    scores = [85, 92, 78]
    for i, (name, score) in enumerate(zip(names, scores), 1):
        print(f"   {i}. {name}: {score}")


# ============================================================
# 2. cycle — 无限循环
# ============================================================

def demo_cycle():
    """cycle(iterable) — 无限循环遍历"""
    print("=" * 60)
    print("itertools.cycle() — 无限循环")
    print("=" * 60)

    print("\n▶ 轮询服务器分配:")
    servers = ['S1', 'S2', 'S3']
    pool = itertools.cycle(servers)
    for i in range(7):
        print(f"   请求 {i+1} → {next(pool)}")

    print("\n▶ 红绿灯模拟:")
    lights = ['🔴 Red', '🟡 Yellow', '🟢 Green']
    traffic = itertools.cycle(lights)
    for i in range(6):
        print(f"   时刻 {i}: {next(traffic)}")

    print("\n▶ 交替背景色（DataGrid 场景）:")
    colors = itertools.cycle(['#f0f0f0', '#ffffff'])
    for i, row in enumerate(['行1', '行2', '行3', '行4', '行5']):
        color = next(colors)
        print(f"   {color}: {row}")


# ============================================================
# 3. repeat — 重复元素
# ============================================================

def demo_repeat():
    """repeat(elem, n) — 重复元素"""
    print("=" * 60)
    print("itertools.repeat() — 重复元素")
    print("=" * 60)

    print("\n▶ 重复固定值:")
    for x in itertools.repeat('Hello', 3):
        print(f"   {x}")

    print("\n▶ 创建默认值列表:")
    defaults = list(itertools.repeat(0, 5))
    print(f"   {defaults}")

    print("\n▶ 配合 map 提供常量参数:")
    result = list(map(pow, [2, 3, 4], itertools.repeat(2)))
    print(f"   pow(2,2), pow(3,2), pow(4,2) = {result}")


# ============================================================
# 4. chain — 串联迭代器
# ============================================================

def demo_chain():
    """chain(*iters) — 串联多个迭代器"""
    print("=" * 60)
    print("itertools.chain() — 串联迭代器")
    print("=" * 60)

    print("\n▶ 合并多个列表:")
    a = [1, 2, 3]
    b = [4, 5, 6]
    c = [7, 8]
    result = list(itertools.chain(a, b, c))
    print(f"   chain({a}, {b}, {c}) = {result}")

    print("\n▶ chain 不会创建中间列表（节省内存）:")
    result = list(itertools.chain(range(3), range(3, 6)))
    print(f"   chain(range(3), range(3,6)) = {result}")

    print("\n▶ chain.from_iterable 处理嵌套可迭代对象:")
    nested = [[1, 2], [3, 4, 5], [6]]
    flattened = list(itertools.chain.from_iterable(nested))
    print(f"   from_iterable({nested}) = {flattened}")

    print("\n▶ 对比: sum() 拼接会创建中间列表:")
    import sys
    big_lists = [list(range(1000)) for _ in range(100)]
    chain_mem = sys.getsizeof(itertools.chain.from_iterable(big_lists))
    print(f"   chain.from_iterable 内存占用: {chain_mem} 字节 (固定)")


# ============================================================
# 5. zip_longest — 以最长为基准的 zip
# ============================================================

def demo_zip_longest():
    """zip_longest(*iters, fillvalue) — 以最长为准"""
    print("=" * 60)
    print("itertools.zip_longest() — 等长压缩")
    print("=" * 60)

    print("\n▶ 不等长列表:")
    names = ['Alice', 'Bob', 'Charlie', 'David']
    scores = [85, 92, 78]

    print(f"   names: {names}")
    print(f"   scores: {scores}")

    print(f"\n   普通 zip: {list(zip(names, scores))}")
    print(f"   zip_longest: {list(itertools.zip_longest(names, scores, fillvalue='N/A'))}")

    print("\n▶ 多列数据对齐:")
    col1 = [1, 2]
    col2 = ['a', 'b', 'c']
    col3 = [10.0, 20.0, 30.0, 40.0]
    aligned = list(itertools.zip_longest(col1, col2, col3, fillvalue='-'))
    for row in aligned:
        print(f"   {row}")


# ============================================================
# 6. islice — 迭代器切片
# ============================================================

def demo_islice():
    """islice(iter, start, stop, step) — 惰性切片"""
    print("=" * 60)
    print("itertools.islice() — 迭代器切片")
    print("=" * 60)

    print("\n▶ 无限序列的前 5 个:")
    result = list(itertools.islice(itertools.count(0), 5))
    print(f"   islice(count(0), 5) = {result}")

    print("\n▶ 从 10 开始取 5 个:")
    result = list(itertools.islice(itertools.count(0), 10, 15))
    print(f"   islice(count(0), 10, 15) = {result}")

    print("\n▶ 步长切片:")
    result = list(itertools.islice(range(10), 0, None, 2))
    print(f"   islice(range(10), 0, None, 2) = {result}")

    print("\n▶ 文件行惰性读取:")
    fake_lines = [f"line {i}" for i in range(100)]
    # 模拟只读取第 10-20 行，不提前加载前面部分
    selected = list(itertools.islice(fake_lines, 10, 15))
    print(f"   行 10-14: {selected}")


# ============================================================
# 7. takewhile / dropwhile — 条件筛选
# ============================================================

def demo_takewhile_dropwhile():
    """takewhile / dropwhile — 条件筛选"""
    print("=" * 60)
    print("itertools.takewhile / dropwhile")
    print("=" * 60)

    data = [1, 3, 5, 2, 4, 6, 7, 9]

    print(f"\n▶ 数据: {data}")

    # takewhile: 从开头取，直到条件不满足
    result = list(itertools.takewhile(lambda x: x < 5, data))
    print(f"   takewhile(x < 5): {result}")

    # dropwhile: 跳过开头满足条件的，从第一个不满足的开始取
    result = list(itertools.dropwhile(lambda x: x < 5, data))
    print(f"   dropwhile(x < 5): {result}")

    print("\n▶ 实战: 跳过文件注释行:")
    fake_file = [
        '# This is a comment',
        '# another comment',
        '',
        'actual code line 1',
        'actual code line 2',
        '',
        '# another comment section',
        'more code'
    ]
    # 跳过开头的注释和空行
    important = list(itertools.dropwhile(
        lambda line: line.startswith('#') or line == '',
        fake_file
    ))
    print(f"   原始数据:")
    for line in fake_file:
        print(f"     {line!r}")
    print(f"   处理后（跳过头注释）:")
    for line in important:
        print(f"     {line!r}")


# ============================================================
# 8. product — 笛卡尔积
# ============================================================

def demo_product():
    """product(*iters) — 笛卡尔积"""
    print("=" * 60)
    print("itertools.product() — 笛卡尔积")
    print("=" * 60)

    print("\n▶ 简单的笛卡尔积:")
    colors = ['红', '蓝']
    sizes = ['S', 'M', 'L']
    result = list(itertools.product(colors, sizes))
    print(f"   {colors} × {sizes} = {result}")

    print("\n▶ 骰子组合:")
    dice = [1, 2, 3, 4, 5, 6]
    pairs = list(itertools.product(dice, repeat=2))
    print(f"   两个骰子的组合数: {len(pairs)} 种")
    print(f"   前 5 个: {pairs[:5]}")

    print("\n▶ 对比嵌套 for 循环:")
    result_product = []
    for color in colors:
        for size in sizes:
            result_product.append((color, size))
    print(f"   嵌套 for 结果: {result_product}")

    print("\n▶ 密码暴力破解模拟:")
    chars = 'ab'
    for length in range(1, 4):
        combos = list(itertools.product(chars, repeat=length))
        print(f"   长度 {length}: {len(combos)} 种组合")


# ============================================================
# 9. permutations / combinations — 排列组合
# ============================================================

def demo_permutations_combinations():
    """permutations / combinations — 排列组合"""
    print("=" * 60)
    print("itertools.permutations / combinations")
    print("=" * 60)

    items = ['A', 'B', 'C']

    print(f"\n▶ 元素: {items}")

    print(f"\n   permutations — 排列（顺序重要）:")
    for r in [1, 2, 3]:
        result = list(itertools.permutations(items, r))
        print(f"   P({len(items)},{r}) = {len(result)}: {result}")

    print(f"\n   combinations — 组合（顺序不重要）:")
    for r in [1, 2, 3]:
        result = list(itertools.combinations(items, r))
        print(f"   C({len(items)},{r}) = {len(result)}: {result}")

    print(f"\n▶ 实战: 组队方案")
    members = ['Alice', 'Bob', 'Charlie', 'David']
    teams = list(itertools.combinations(members, 2))
    print(f"   {len(members)} 人中选 2 人组队: {len(teams)} 种")
    for team in teams:
        print(f"     {team[0]} & {team[1]}")


# ============================================================
# 10. groupby — 相邻元素分组
# ============================================================

def demo_groupby():
    """groupby(iter, key) — 相邻元素分组"""
    print("=" * 60)
    print("itertools.groupby() — 分组")
    print("=" * 60)

    print("\n▶ 简单分组（数据必须已排序!）:")
    data = [('A', 1), ('A', 2), ('B', 3), ('B', 4), ('A', 5)]
    # ❌ 不排序 -> 'A' 被分成两组
    for key, group in itertools.groupby(data, key=lambda x: x[0]):
        print(f"   {key}: {list(group)}")

    print("\n▶ 排序后分组:")
    data.sort(key=lambda x: x[0])
    for key, group in itertools.groupby(data, key=lambda x: x[0]):
        print(f"   {key}: {list(group)}")

    print("\n▶ 实战: 按首字母分组:")
    words = ['apple', 'banana', 'avocado', 'cherry', 'blueberry', 'apricot']
    words.sort(key=lambda w: w[0])  # 按首字母排序
    for letter, group in itertools.groupby(words, key=lambda w: w[0]):
        print(f"   {letter}: {list(group)}")


# ============================================================
# 11. 实战: 数据处理管道
# ============================================================

def data_pipeline_demo():
    """使用 itertools 构建数据处理管道"""
    print("=" * 60)
    print("itertools 数据处理管道实战")
    print("=" * 60)

    # 模拟从多个 API 分页获取数据
    def api_page(page_num):
        """模拟 API 分页返回数据"""
        if page_num > 5:
            return []  # 没有更多数据
        return list(range(page_num * 10, page_num * 10 + 10))

    print("\n▶ 从多个 API 页面获取数据:")

    # 1. 生成页码
    pages = itertools.count(1)

    # 2. 获取数据
    all_data = itertools.chain.from_iterable(
        itertools.takewhile(
            lambda items: items,  # 不为空就继续
            (api_page(p) for p in pages)
        )
    )

    # 3. 取前 25 个
    sample = list(itertools.islice(all_data, 25))
    print(f"   前 25 条数据: {sample}")

    print("\n▶ 统计处理:")
    data = list(range(1, 21))
    print(f"   原始数据: {data}")

    # 偶数
    evens = [x for x in data if x % 2 == 0]
    print(f"   偶数: {evens}")

    # 每 3 个一组
    grouped = [data[i:i+3] for i in range(0, len(data), 3)]
    print(f"   每 3 个一组: {grouped}")


# ============================================================
# 12. 实战: 滑动窗口
# ============================================================

def sliding_window(iterable, n):
    """生成滑动窗口迭代器

    使用 tee 和 islice 实现高效的滑动窗口。
    """
    iterators = itertools.tee(iterable, n)
    return zip(*(
        itertools.islice(it, i, None)
        for i, it in enumerate(iterators)
    ))


def demo_sliding_window():
    """测试滑动窗口"""
    print("=" * 60)
    print("滑动窗口实战")
    print("=" * 60)

    data = [1, 2, 3, 4, 5, 6]
    print(f"\n▶ 数据: {data}")

    windows = list(sliding_window(data, 3))
    print(f"   滑动窗口 (n=3): {windows}")

    print("\n▶ 移动平均线计算:")
    prices = [10, 12, 11, 13, 15, 14, 16]
    windows = list(sliding_window(prices, 3))
    moving_avgs = [sum(w) / 3 for w in windows]
    print(f"   价格: {prices}")
    print(f"   3日移动平均: {moving_avgs}")


# ============================================================
# 13. 综合实战: 日志分析
# ============================================================

def log_analysis_demo():
    """使用 itertools 分析日志数据"""
    print("=" * 60)
    print("日志分析实战")
    print("=" * 60)

    # 模拟日志数据
    log_entries = [
        ("INFO", "Server started"),
        ("INFO", "Loading config"),
        ("WARN", "Disk usage 85%"),
        ("ERROR", "Connection timeout"),
        ("INFO", "Retrying connection"),
        ("WARN", "Memory usage 90%"),
        ("INFO", "Connection re-established"),
        ("ERROR", "Disk write failed"),
        ("CRITICAL", "System shutting down"),
        ("INFO", "Cleanup complete"),
    ]

    print(f"\n▶ 日志条目: {len(log_entries)} 条")
    for level, msg in log_entries:
        print(f"   [{level:>8}] {msg}")

    # 1. 按日志级别分组
    log_entries.sort(key=lambda x: x[0])
    print(f"\n▶ 按级别分组:")
    for level, group in itertools.groupby(log_entries, key=lambda x: x[0]):
        count = len(list(group))
        print(f"   {level}: {count} 条")

    # 2. 提取所有 WARN 及以上级别
    print(f"\n▶ WARN 及以上级别:")
    warnings = itertools.dropwhile(
        lambda x: x[0] not in ('WARN', 'ERROR', 'CRITICAL'),
        sorted(log_entries, key=lambda x: x[0])
    )
    for level, msg in warnings:
        if level == 'INFO':
            continue
        print(f"   [{level}] {msg}")


# ============================================================
# Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("Day 021 — itertools 模块应用实战")
    print("=" * 60)

    demo_count()
    demo_cycle()
    demo_repeat()
    demo_chain()
    demo_zip_longest()
    demo_islice()
    demo_takewhile_dropwhile()
    demo_product()
    demo_permutations_combinations()
    demo_groupby()
    data_pipeline_demo()
    demo_sliding_window()
    log_analysis_demo()

    print("\n" + "=" * 60)
    print("✅ itertools 实战完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
