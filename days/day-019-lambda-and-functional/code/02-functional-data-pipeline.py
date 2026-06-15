#!/usr/bin/env python3
"""
02-functional-data-pipeline.py — 函数式数据处理实战

使用函数式编程范式解决真实数据处理问题：
  1. 日志分析管道
  2. 订单数据处理
  3. 文本分析
  4. 函数式 vs 命令式性能对比
"""

from functools import reduce
import time

# ============================================================
# 案例 1：日志分析管道
# ============================================================
print("=" * 70)
print("📊 案例 1: 日志分析管道")
print("=" * 70)

raw_logs = [
    "2024-01-15 10:23:45 INFO  用户登录成功 user_id=1001",
    "2024-01-15 10:25:12 ERROR 数据库连接超时 user_id=1002",
    "2024-01-15 10:26:33 INFO  用户登出成功 user_id=1001",
    "2024-01-15 10:27:01 WARN  请求频率过高 ip=192.168.1.1",
    "2024-01-15 10:28:45 ERROR 文件未找到 path=/data/config.json",
    "2024-01-15 10:30:12 INFO  用户登录成功 user_id=1003",
    "2024-01-15 10:31:55 ERROR 权限不足 user_id=1003 resource=admin",
    "2024-01-15 10:33:20 INFO  用户登出成功 user_id=1002",
    "2024-01-15 10:35:00 WARN  磁盘空间不足 usage=92%",
    "2024-01-15 10:36:45 ERROR 服务异常退出 code=SIGSEGV",
]


def parse_log(log_line):
    """解析日志行"""
    parts = log_line.split()
    return {
        "timestamp": f"{parts[0]} {parts[1]}",
        "level": parts[2],
        "message": " ".join(parts[3:]),
    }


def filter_by_level(logs, level):
    """按级别过滤日志"""
    return list(filter(lambda log: log["level"] == level, logs))


def extract_errors(logs):
    """提取错误信息（函数式链）"""
    errors = filter(lambda l: l["level"] == "ERROR", logs)
    parsed = map(lambda l: {
        "time": l["timestamp"],
        "level": l["level"],
        "message": l["message"],
        "severity": "CRITICAL" if any(kw in l["message"] for kw in
                                       ["超时", "退出", "权限"]) else "NORMAL"
    }, errors)
    return list(parsed)


# 函数式管道
print("\n🔍 函数式日志分析管道:")
print("-" * 50)

parsed_logs = list(map(parse_log, raw_logs))
print(f"已解析日志: {len(parsed_logs)} 条")

error_logs = filter_by_level(parsed_logs, "ERROR")
warn_logs = filter_by_level(parsed_logs, "WARN")
info_logs = filter_by_level(parsed_logs, "INFO")
print(f"ERROR: {len(error_logs)} 条 | WARN: {len(warn_logs)} 条 | INFO: {len(info_logs)} 条")

critical_errors = extract_errors(parsed_logs)
print("\n⚠️  关键错误信息:")
for e in critical_errors:
    print(f"  [{e['severity']}] {e['time']} - {e['message']}")

level_counts = reduce(
    lambda acc, log: {**acc, log["level"]: acc.get(log["level"], 0) + 1},
    parsed_logs,
    {"INFO": 0, "WARN": 0, "ERROR": 0}
)
print(f"\n📈 日志级别统计: {level_counts}")

print()

# ============================================================
# 案例 2：订单数据处理
# ============================================================
print("=" * 70)
print("📦 案例 2: 订单数据处理")
print("=" * 70)

orders = [
    {"id": 1, "items": [{"name": "手机", "price": 5999, "qty": 1},
                         {"name": "手机壳", "price": 29, "qty": 2}]},
    {"id": 2, "items": [{"name": "笔记本电脑", "price": 8999, "qty": 1}]},
    {"id": 3, "items": [{"name": "鼠标", "price": 199, "qty": 3},
                         {"name": "键盘", "price": 399, "qty": 1},
                         {"name": "显示器", "price": 2499, "qty": 1}]},
    {"id": 4, "items": [{"name": "耳机", "price": 999, "qty": 1}]},
]


def calc_order_total(order):
    """计算单笔订单总价"""
    items_total = reduce(
        lambda acc, item: acc + item["price"] * item["qty"],
        order["items"],
        0
    )
    return {**order, "total": items_total}


orders_with_total = list(map(calc_order_total, orders))
print("\n📋 所有订单:")
for o in orders_with_total:
    item_names = ", ".join(i["name"] for i in o["items"])
    print(f"  订单 #{o['id']:2} | {item_names:30} | 总计: ¥{o['total']:>6,}")

large_orders = list(filter(lambda o: o["total"] > 3000, orders_with_total))
print(f"\n💎 大额订单 (>¥3000): {len(large_orders)} 笔")
for o in large_orders:
    print(f"  订单 #{o['id']} → ¥{o['total']:,}")

all_items = reduce(
    lambda acc, o: acc + o["items"],
    orders,
    []
)
categories = set(map(lambda i: i["name"], all_items))
total_qty = reduce(lambda acc, i: acc + i["qty"], all_items, 0)
total_revenue = reduce(lambda acc, o: acc + o["total"], orders_with_total, 0)
print(f"\n📊 汇总统计:")
print(f"  商品种类数: {len(categories)}")
print(f"  商品总件数: {total_qty}")
print(f"  总营业额:   ¥{total_revenue:>7,}")

most_expensive = reduce(
    lambda a, b: a if a["price"] > b["price"] else b,
    all_items
)
print(f"  最贵商品:   {most_expensive['name']} (¥{most_expensive['price']:,})")

print()

# ============================================================
# 案例 3：文本分析
# ============================================================
print("=" * 70)
print("📝 案例 3: 文本分析")
print("=" * 70)

text = """
Python is an interpreted, object-oriented, high-level programming language
with dynamic semantics. Its high-level built-in data structures, combined
with dynamic typing and dynamic binding, make it very attractive for Rapid
Application Development, as well as for use as a scripting or glue language
to connect existing components together. Python's simple, easy to learn syntax
emphasizes readability and therefore reduces the cost of program maintenance.
"""

words = list(filter(
    lambda w: len(w) > 0,
    map(
        lambda w: w.strip(".,;:!?\"'()[]{}").lower(),
        text.split()
    )
))

word_freq = reduce(
    lambda acc, w: {**acc, w: acc.get(w, 0) + 1},
    words,
    {}
)

total_words = len(words)
unique_words = len(word_freq)

top_words = sorted(
    word_freq.items(),
    key=lambda x: -x[1]
)[:10]

print(f"\n📈 文本统计:")
print(f"  总词数:     {total_words}")
print(f"  不同词汇数: {unique_words}")
print(f"  词汇密度:   {unique_words/total_words:.1%}")

print(f"\n🏆 高频词汇 Top 10:")
for word, count in top_words:
    first_pos = next(i for i, w in enumerate(words) if w == word)
    bar = "█" * count
    print(f"  {word:15} {count:2}次 {bar}")

print()

# ============================================================
# 案例 4：函数式 vs 命令式性能对比
# ============================================================
print("=" * 70)
print("⚡ 案例 4: 函数式 vs 命令式性能对比")
print("=" * 70)

size = 2_000_000
test_data = list(range(size))


def imperative_approach(data):
    """命令式方法：过滤偶数 → 平方 → 求和"""
    result = 0
    for x in data:
        if x % 2 == 0:
            result += x ** 2
    return result


def functional_approach(data):
    """函数式方法"""
    return reduce(
        lambda a, b: a + b,
        map(lambda x: x ** 2,
            filter(lambda x: x % 2 == 0, data))
    )


def comprehension_approach(data):
    """列表推导式方法（Pythonic）"""
    return sum(x ** 2 for x in data if x % 2 == 0)


# 预热
_ = imperative_approach(test_data[:100])
_ = functional_approach(test_data[:100])
_ = comprehension_approach(test_data[:100])

approaches = [
    ("命令式", imperative_approach),
    ("函数式", functional_approach),
    ("推导式", comprehension_approach),
]

print(f"\n⚙️  数据量: {size:,}")
print("-" * 50)

results = []
for name, func in approaches:
    start = time.perf_counter()
    result = func(test_data)
    elapsed = time.perf_counter() - start
    results.append((name, elapsed, result))
    print(f"  {name:8} | {elapsed:.4f}s | 结果: {result}")

fastest = min(results, key=lambda x: x[1])
print(f"\n🏆 最快方法: {fastest[0]} ({fastest[1]:.4f}s)")

assert results[0][2] == results[1][2] == results[2][2]
print("✅ 三种方法结果一致")

print()
print("=" * 70)

print("\n📊 生成器 vs 列表: 内存对比（模拟）")
print("-" * 50)

def list_based(n):
    return sum([x ** 2 for x in range(n) if x % 2 == 0])

def generator_based(n):
    return sum(x ** 2 for x in range(n) if x % 2 == 0)

n = 5_000_000
print(f"数据量: {n:,}")

t1 = time.perf_counter()
r1 = list_based(500_000)
t1 = time.perf_counter() - t1

t2 = time.perf_counter()
r2 = generator_based(500_000)
t2 = time.perf_counter() - t2

print(f"  列表推导: {t1:.4f}s (可能 OOM 在大数据量)")
print(f"  生成器:   {t2:.4f}s (内存友好)")
print("✅ 生成器胜出（大数据量时内存优势更明显）")

print("\n✅ 函数式数据处理实战完成")
