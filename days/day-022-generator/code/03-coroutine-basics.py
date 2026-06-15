#!/usr/bin/env python3
"""
Day 022 - Coroutine Basics
协程基础：生成器作为协程、send/throw/close 进阶、yield from 双向通道
"""

import time
import random


# ============================================================
# 1. 协程的基本概念
# ============================================================

# 协程（Coroutine）是通过 send() 和 yield 实现的双向通信
# 生成器协程 vs async/await 协程：
#   - 生成器协程: 基于 yield/send 的"老式"协程
#   - async/await: Python 3.5+ 的原生协程
#   - 本例关注生成器协程，它是理解 async/await 的基础

def simple_coroutine():
    """最简单的协程——演示协程的启动和数据接收"""
    print("  [协程] 启动！")
    while True:
        value = yield  # 接收数据
        print(f"  [协程] 收到数据: {value!r}")


def test_simple_coroutine():
    """测试简单协程"""
    print("=" * 60)
    print("简单协程演示")
    print("=" * 60)

    print("\n▶ 创建并启动协程:")
    coro = simple_coroutine()

    # 必须先用 next() 或 send(None) 启动到第一个 yield
    print("   使用 next(coro) 启动...")
    next(coro)

    print("\n▶ 向协程发送数据:")
    coro.send("Hello")
    coro.send(42)
    coro.send([1, 2, 3])


# ============================================================
# 2. 协程状态机
# ============================================================

def coroutine_state_machine():
    """展示协程的不同状态"""
    print("  [状态机] 初始启动")
    data = yield "请输入名字"
    print(f"  [状态机] 收到: {data}")

    data = yield "请输入年龄"
    print(f"  [状态机] 收到: {data}")

    data = yield "请输入城市"
    print(f"  [状态机] 收到: {data}")

    return "信息收集完毕"


def test_coroutine_state():
    """测试协程状态"""
    print("=" * 60)
    print("协程状态机")
    print("=" * 60)

    coro = coroutine_state_machine()

    print("\n▶ 逐步交互:")
    print(f"   启动: {next(coro)}")      # "请输入名字"
    print(f"   回复: {coro.send('Alice')}")  # "请输入年龄"
    print(f"   回复: {coro.send('28')}")      # "请输入城市"

    try:
        coro.send("Beijing")
    except StopIteration as e:
        print(f"   完成: {e.value}")

    # 检查生成器状态
    import inspect
    coro = coroutine_state_machine()
    next(coro)

    print(f"\n▶ 生成器状态枚举:")
    print(f"   GEN_CREATED = {inspect.GEN_CREATED}")
    print(f"   GEN_RUNNING = {inspect.GEN_RUNNING}")
    print(f"   GEN_SUSPENDED = {inspect.GEN_SUSPENDED}")
    print(f"   GEN_CLOSED = {inspect.GEN_CLOSED}")

    # 各阶段状态
    g = coroutine_state_machine()
    print(f"\n   刚创建: {inspect.getgeneratorstate(g)}")

    next(g)
    print(f"   挂起: {inspect.getgeneratorstate(g)}")

    g.close()
    print(f"   关闭: {inspect.getgeneratorstate(g)}")


# ============================================================
# 3. 数据流处理协程
# ============================================================

def running_average():
    """协程：计算运行平均值

    每次 send 一个数值，yield 当前平均值。
    这是协程最经典的应用之一：数据流处理。
    """
    total = 0.0
    count = 0
    average = None

    print("  [平均计算] 初始化完成")

    while True:
        value = yield average  # 接收新值，返回当前平均
        total += value
        count += 1
        average = total / count
        print(f"  [平均计算] 收到 {value}, 当前平均 = {average:.2f}")


def running_median():
    """协程：计算运行中位数

    维护一个已排序的列表，每次 send 返回当前中位数。
    """
    import bisect
    numbers = []

    while True:
        value = yield  # 接收新值
        bisect.insort(numbers, value)
        n = len(numbers)
        if n % 2 == 1:
            median = numbers[n // 2]
        else:
            median = (numbers[n // 2 - 1] + numbers[n // 2]) / 2
        print(f"  [中位数] 收到 {value}, 当前中位数 = {median}")


def test_dataflow_coroutines():
    """测试数据流处理协程"""
    print("=" * 60)
    print("数据流处理协程")
    print("=" * 60)

    # 运行平均值
    print("\n▶ 运行平均值计算:")
    avg = running_average()
    next(avg)  # 启动

    for val in [10, 20, 30, 40, 50]:
        result = avg.send(val)
        print(f"   发送 {val} → 平均: {result}")

    avg.close()

    # 运行中位数
    print("\n▶ 运行中位数计算:")
    med = running_median()
    next(med)

    for val in [5, 3, 8, 1, 9]:
        med.send(val)

    med.close()


# ============================================================
# 4. 协程装饰器（避免手动 next）
# ============================================================

def coroutine(func):
    """协程装饰器：自动调用 next() 启动协程

    这样使用者可以直接 coro.send(value) 而不需要先 next()。
    """
    def wrapper(*args, **kwargs):
        gen = func(*args, **kwargs)
        next(gen)  # 自动启动
        return gen
    return wrapper


@coroutine
def auto_averager():
    """自动启动的平均计算协程"""
    total = 0.0
    count = 0
    try:
        while True:
            value = yield total / count if count > 0 else 0.0
            total += value
            count += 1
    except GeneratorExit:
        print(f"   [自动平均] 最终平均: {total / count:.2f} (基于 {count} 个值)")


def test_coroutine_decorator():
    """测试协程装饰器"""
    print("=" * 60)
    print("协程装饰器")
    print("=" * 60)

    print("\n▶ 使用 @coroutine 装饰器自动启动:")
    avg = auto_averager()
    # 不需要 next(avg)！

    for val in [10, 15, 20, 25]:
        result = avg.send(val)
        print(f"   send({val}) → 平均: {result:.2f}")

    avg.close()

    print("\n▶ 对比：普通协程需要手动 next()")


# ============================================================
# 5. 协程异常处理
# ============================================================

@coroutine
def robust_coroutine():
    """健壮的协程——能处理异常和清理"""
    print("  [健壮协程] 启动")
    try:
        while True:
            try:
                value = yield
                if value < 0:
                    raise ValueError(f"负数不允许: {value}")
                print(f"  [健壮协程] 处理: {value}")
            except ValueError as e:
                print(f"  [健壮协程] 捕获错误: {e}")
                # 继续运行
    except GeneratorExit:
        print("  [健壮协程] 正在关闭...")
        # 清理资源
        print("  [健壮协程] 清理完毕")
        raise


def test_robust_coroutine():
    """测试健壮的协程"""
    print("=" * 60)
    print("健壮协程 — 异常处理")
    print("=" * 60)

    coro = robust_coroutine()

    print("\n▶ 发送正常值:")
    coro.send(10)
    coro.send(20)

    print("\n▶ 发送负值（协程内部处理异常）:")
    coro.send(-5)

    print("\n▶ 外部 throw 异常:")
    try:
        coro.throw(RuntimeError, "外部错误")
    except RuntimeError as e:
        print(f"   未处理的异常穿透: {e}")

    print("\n▶ 关闭:")
    coro.close()


# ============================================================
# 6. yield from + 协程：双向通道
# ============================================================

def sub_coro():
    """子协程"""
    print("   [子协程] 启动")
    try:
        while True:
            value = yield
            print(f"   [子协程] 处理: {value!r}")
    except GeneratorExit:
        print("   [子协程] 关闭")
        raise


def main_coro():
    """主协程：通过 yield from 委托"""
    print("  [主协程] 启动，委托给子协程...")
    yield from sub_coro()
    print("  [主协程] 子协程结束")


def test_delegating_coroutine():
    """测试委托协程"""
    print("=" * 60)
    print("yield from + 协程：双向通道")
    print("=" * 60)

    print("\n▶ 委托协程——send 直接传递到子协程:")
    main = main_coro()
    next(main)  # 启动，进入子协程

    main.send("数据A")
    main.send("数据B")

    print("\n▶ 关闭:")
    main.close()


# ============================================================
# 7. 实战：事件管道系统
# ============================================================

@coroutine
def event_printer():
    """事件打印器——消费事件"""
    try:
        while True:
            event = yield
            print(f"    📋 [Printer] 事件: {event}")
    except GeneratorExit:
        pass


@coroutine
def event_filter(min_priority=5):
    """事件过滤器——按优先级过滤"""
    try:
        child = event_printer()
        while True:
            event = yield
            if event.get('priority', 0) >= min_priority:
                print(f"    🔍 [Filter] 优先级 {event['priority']} >= {min_priority}，通过")
                child.send(event)
            else:
                print(f"    🔍 [Filter] 优先级 {event['priority']} < {min_priority}，过滤")
    except GeneratorExit:
        child.close()


@coroutine
def event_transformer():
    """事件转换器——为事件添加时间戳"""
    try:
        child = event_filter(min_priority=3)
        while True:
            event = yield
            event['timestamp'] = time.strftime('%H:%M:%S')
            print(f"    🔄 [Transformer] 添加时间戳: {event['timestamp']}")
            child.send(event)
    except GeneratorExit:
        child.close()


def test_event_pipeline():
    """测试事件处理管道"""
    print("=" * 60)
    print("事件处理管道")
    print("=" * 60)

    pipeline = event_transformer()

    print("\n▶ 发送事件流:")
    events = [
        {'type': 'click', 'priority': 1, 'data': 'button1'},
        {'type': 'login', 'priority': 5, 'data': 'user123'},
        {'type': 'error', 'priority': 8, 'data': 'disk_full'},
        {'type': 'hover', 'priority': 2, 'data': 'menu_item'},
        {'type': 'shutdown', 'priority': 10, 'data': 'system_down'},
    ]

    for event in events:
        print(f"\n   输入: {event['type']} (优先级 {event['priority']})")
        pipeline.send(event)

    pipeline.close()


# ============================================================
# 8. 实战：生产者-消费者模型
# ============================================================

@coroutine
def consumer():
    """消费者协程"""
    total_items = 0
    try:
        while True:
            item = yield
            total_items += 1
            print(f"    📦 [消费者] 处理第 {total_items} 个商品: {item!r}")
            time.sleep(0.05)  # 模拟处理时间
    except GeneratorExit:
        print(f"    📊 [消费者] 总共处理了 {total_items} 个商品")


def producer(consumer_coro, count=10):
    """生产者函数——生成数据并发送给消费者"""
    print(f"  🏭 [生产者] 开始生产 {count} 个商品...")
    for i in range(count):
        item = f"product-{i+1}"
        print(f"  🏭 [生产者] 产出: {item}")
        consumer_coro.send(item)
    consumer_coro.close()
    print(f"  🏭 [生产者] 生产完成")


def test_producer_consumer():
    """测试生产者-消费者模型"""
    print("=" * 60)
    print("生产者-消费者模型")
    print("=" * 60)

    print("\n▶ 启动生产-消费流程:")
    cons = consumer()
    producer(cons, 5)

    print("\n▶ 多个生产者共享一个消费者:")
    shared_consumer = consumer()
    for id_ in range(3):
        print(f"\n   ----- 生产者 {id_+1} -----")
        for i in range(3):
            shared_consumer.send(f"producer-{id_+1}-item-{i+1}")
    shared_consumer.close()


# ============================================================
# 9. 协程 vs async/await（概念对比）
# ============================================================

def test_coroutine_comparison():
    """协程概念对比"""
    print("=" * 60)
    print("生成器协程 vs async/await")
    print("=" * 60)

    print("""
    ┌─────────────────────────────────────────────────────────┐
    │              协程的演进历史                               │
    ├─────────────────────────────────────────────────────────┤
    │ Python 2.2: yield 引入（生成器基础）                      │
    │ Python 2.5: send/throw/close（生成器协程）                │
    │ Python 3.3: yield from（委托给子生成器）                   │
    │ Python 3.5: async/await 原生协程                          │
    └─────────────────────────────────────────────────────────┘

    ├───────────────┬──────────────────┬──────────────────────┤
    │               │ 生成器协程       │ async/await 协程      │
    ├───────────────┼──────────────────┼──────────────────────┤
    │ 关键字         │ yield/send       │ async/await          │
    │ 返回值         │ Generator 对象   │ Coroutine 对象        │
    │ 调度方式       │ 手动（调用者）    │ 事件循环（自动）      │
    │ 适用场景       │ 数据管道/流处理   │ I/O 密集型异步编程    │
    │ 协程间切换     │ send/throw       │ await                │
    │ 并发模型       │ 协作式（手动）    │ 协作式（事件循环）    │
    └───────────────┴──────────────────┴──────────────────────┘
    """)

    print("▶ 共同本质: 都是可暂停、可恢复的计算")
    print("▶ 核心区别: 调度者不同（手动 vs 自动）")
    print("▶ 学习建议: 先掌握生成器协程，再学 async/await 会更轻松")


# ============================================================
# Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("Day 022 — 协程基础实战")
    print("=" * 60)

    test_simple_coroutine()
    test_coroutine_state()
    test_dataflow_coroutines()
    test_coroutine_decorator()
    test_robust_coroutine()
    test_delegating_coroutine()
    test_event_pipeline()
    test_producer_consumer()
    test_coroutine_comparison()

    print("\n" + "=" * 60)
    print("✅ 协程基础实战完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
