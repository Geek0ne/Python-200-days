#!/usr/bin/env python3
"""
Day 022 - Generator Basics
生成器基础：yield、send、throw、close、yield from
"""

from collections.abc import Generator, Iterator, Iterable
import sys
import types


# ============================================================
# 1. 最简单的生成器
# ============================================================

def simple_generator():
    """最简单的生成器——展示 yield 的暂停/恢复"""
    print("  [生成器] 启动")
    yield 1
    print("  [生成器] 第一次恢复")
    yield 2
    print("  [生成器] 第二次恢复")
    yield 3
    print("  [生成器] 结束")


def test_simple_generator():
    """测试简单生成器"""
    print("=" * 60)
    print("最简单的生成器")
    print("=" * 60)

    print("\n▶ 创建生成器对象（不执行任何代码）:")
    gen = simple_generator()
    print(f"   生成器对象: {gen}")
    print(f"   类型: {type(gen)}")
    print(f"   是 Generator: {isinstance(gen, Generator)}")

    print("\n▶ 逐步调用 next():")
    print(f"   next(gen) = {next(gen)}")
    print(f"   next(gen) = {next(gen)}")
    print(f"   next(gen) = {next(gen)}")

    print("\n▶ 第四次调用 -> StopIteration:")
    try:
        next(gen)
    except StopIteration:
        print("   StopIteration: 生成器已耗尽 ✅")


# ============================================================
# 2. 生成器函数 vs 生成器表达式
# ============================================================

def count_up_to(n):
    """生成器函数：生成 0 到 n-1"""
    i = 0
    while i < n:
        yield i
        i += 1


def test_generator_vs_expression():
    """对比生成器函数和生成器表达式"""
    print("=" * 60)
    print("生成器函数 vs 生成器表达式")
    print("=" * 60)

    # 生成器函数
    print("\n▶ 生成器函数:")
    gen_func = count_up_to(5)
    print(f"   类型: {type(gen_func)}")
    print(f"   值: {list(gen_func)}")

    # 生成器表达式
    print("\n▶ 生成器表达式:")
    gen_expr = (x**2 for x in range(5))
    print(f"   类型: {type(gen_expr)}")
    print(f"   值: {list(gen_expr)}")

    # 列表推导式（立即求值）
    print("\n▶ 对比：列表推导式:")
    squares_list = [x**2 for x in range(5)]
    print(f"   类型: {type(squares_list)}")
    print(f"   值: {squares_list}")

    # 内存对比
    print("\n▶ 大数量内存对比 (10^6):")
    gen = (x for x in range(10**6))
    lst = [x for x in range(10**6)]
    print(f"   生成器大小: {sys.getsizeof(gen)} 字节")
    print(f"   列表大小: {sys.getsizeof(lst):,} 字节 （~{sys.getsizeof(lst)/1024/1024:.1f}MB）")


# ============================================================
# 3. send() — 向生成器发送值
# ============================================================

def echo_generator():
    """echo 生成器：接收值并打印"""
    print("  [echo] 启动")
    while True:
        received = yield  # yield 右侧没有表达式，只接收不发送
        print(f"  [echo] 收到: {received!r}")


def accumulator():
    """累加器生成器：接收值并返回累计和"""
    total = 0
    i = 0
    while True:
        received = yield total  # 发送 total，接收新的值
        if received is None:
            received = 0
        total += received
        i += 1


def test_send():
    """测试 send() 方法"""
    print("=" * 60)
    print("send() — 向生成器发送值")
    print("=" * 60)

    # echo 生成器
    print("\n▶ echo 生成器:")
    gen = echo_generator()
    next(gen)  # 启动到第一个 yield（必须先启动！）
    gen.send("Hello")
    gen.send("World")
    gen.send([1, 2, 3])

    # 累加器
    print("\n▶ 累加器生成器:")
    acc = accumulator()
    next(acc)  # 启动
    print(f"   send(10) → {acc.send(10)}")  # total=10
    print(f"   send(20) → {acc.send(20)}")  # total=30
    print(f"   send(5)  → {acc.send(5)}")   # total=35

    # 必须先启动
    print("\n▶ 必须先 next() 启动:")
    new_acc = accumulator()
    # 如果直接 send(10)，会报错 TypeError: can't send non-None value...
    try:
        new_acc.send(10)
    except TypeError as e:
        print(f"   ❌ 未启动直接 send(): {e}")
    print(f"   ✅ 必须先用 next(gen) 或 gen.send(None) 启动")


# ============================================================
# 4. throw() — 向生成器抛异常
# ============================================================

def safe_generator():
    """带异常处理的生成器"""
    i = 0
    while True:
        try:
            yield i
            i += 1
        except ValueError as e:
            print(f"  [生成器] 捕获 ValueError: {e}")
            # 继续执行
        except GeneratorExit:
            print("  [生成器] 收到 GeneratorExit，执行清理...")
            raise  # 必须重新抛出 GeneratorExit


def test_throw():
    """测试 throw() 方法"""
    print("=" * 60)
    print("throw() — 向生成器抛异常")
    print("=" * 60)

    gen = safe_generator()

    print("\n▶ 正常取值:")
    print(f"   {next(gen)}")  # 0
    print(f"   {next(gen)}")  # 1

    print("\n▶ 抛出 ValueError:")
    gen.throw(ValueError, "测试异常")
    print(f"   {next(gen)}")  # 继续取值

    print("\n▶ 如果生成器不处理异常:")
    def broken_gen():
        yield 1
        yield 2

    b = broken_gen()
    next(b)  # 1
    try:
        b.throw(RuntimeError, "未处理的异常")
    except RuntimeError as e:
        print(f"   ❌ 异常穿透到调用者: {e}")


# ============================================================
# 5. close() — 关闭生成器
# ============================================================

def resource_gen():
    """模拟一个需要清理资源的生成器"""
    print("  [资源] 打开连接...")
    try:
        for i in range(10):
            yield i
    except GeneratorExit:
        print("  [资源] 关闭连接...")  # 清理操作
        raise
    finally:
        print("  [资源] 清理完毕")


def test_close():
    """测试 close() 方法"""
    print("=" * 60)
    print("close() — 关闭生成器")
    print("=" * 60)

    print("\n▶ 正常关闭:")
    gen = resource_gen()
    print(f"   next: {next(gen)}")  # 0
    print(f"   next: {next(gen)}")  # 1
    gen.close()
    print("   已关闭")

    print("\n▶ 关闭后再取值:")
    try:
        next(gen)
    except StopIteration:
        print("   ❌ 关闭后 next() → StopIteration")

    print("\n▶ with 语句中的 GC 自动关闭:")
    def temp_gen():
        yield 42
    g = temp_gen()
    print(f"   {list(g)}")
    # g 离开作用域后自动关闭

    print("\n▶ 检查生成器状态:")
    gen = resource_gen()
    print(f"   gi_frame (有值=挂起): {gen.gi_frame}")
    print(f"   gi_running: {gen.gi_running}")
    next(gen)
    print(f"   取值后 gi_frame: {gen.gi_frame}")
    gen.close()
    print(f"   关闭后 gi_frame: {gen.gi_frame}")
    print(f"   关闭后 gi_running: {gen.gi_running}")


# ============================================================
# 6. yield from — 委托给子生成器
# ============================================================

def sub_gen():
    """子生成器"""
    received = yield "子-准备就绪"
    print(f"   [子] 收到: {received}")
    received2 = yield "子-处理中"
    print(f"   [子] 收到: {received2}")
    return "子-最终结果"


def main_gen():
    """主生成器，委托给子生成器"""
    result = yield from sub_gen()
    print(f"   [主] 子返回: {result}")
    return result


def chain_generators(*iterables):
    """使用 yield from 实现 chain"""
    for it in iterables:
        yield from it


def flatten(items):
    """使用 yield from 递归展开嵌套列表"""
    for item in items:
        if isinstance(item, (list, tuple)):
            yield from flatten(item)
        else:
            yield item


def test_yield_from():
    """测试 yield from 语法"""
    print("=" * 60)
    print("yield from — 委托给子生成器")
    print("=" * 60)

    print("\n▶ 基本 yield from:")
    gen = main_gen()
    print(f"   next: {next(gen)}")  # 进入子生成器
    print(f"   send('数据A'): {gen.send('数据A')}")  # send 到子生成器
    try:
        gen.send('数据B')
    except StopIteration as e:
        print(f"   返回值: {e.value}")

    print("\n▶ yield from 实现 chain:")
    result = list(chain_generators([1, 2], [3, 4], 'AB'))
    print(f"   chain([1,2], [3,4], 'AB') = {result}")

    print("\n▶ yield from 递归展开:")
    nested = [1, [2, [3, 4]], 5, [6]]
    result = list(flatten(nested))
    print(f"   flatten({nested}) = {result}")


# ============================================================
# 7. 生成器状态与生命周期
# ============================================================

def gen_state_machine():
    """演示生成器的状态机特性"""
    print("  [状态机] 步骤 A")
    yield "A"
    print("  [状态机] 步骤 B")
    yield "B"
    print("  [状态机] 步骤 C")
    yield "C"
    print("  [状态机] 完成")
    return "DONE"


def test_generator_state():
    """测试生成器状态"""
    print("=" * 60)
    print("生成器状态与 gi_* 属性")
    print("=" * 60)

    gen = gen_state_machine()

    print("\n▶ 初始状态（刚创建，未启动）:")
    print(f"   gi_frame: {gen.gi_frame}")
    print(f"   gi_code: {gen.gi_code.co_name}")
    try:
        print(f"   gi_yieldfrom: {gen.gi_yieldfrom}")
    except AttributeError:
        pass

    print("\n▶ 执行到第一个 yield:")
    print(f"   next(gen) = {next(gen)}")
    print(f"   gi_frame.f_lineno: {gen.gi_frame.f_lineno}")  # 当前行号

    print("\n▶ 执行到第二个 yield:")
    print(f"   next(gen) = {next(gen)}")
    print(f"   gi_frame.f_lineno: {gen.gi_frame.f_lineno}")

    print("\n▶ 执行到第三个 yield:")
    print(f"   next(gen) = {next(gen)}")
    print(f"   gi_frame.f_lineno: {gen.gi_frame.f_lineno}")

    print("\n▶ 执行完毕:")
    try:
        next(gen)
    except StopIteration as e:
        print(f"   StopIteration, value = {e.value}")
    print(f"   gi_frame (消耗后): {gen.gi_frame}")


# ============================================================
# 8. 生成器 vs 迭代器实现对比
# ============================================================

class CountUpIterator:
    """迭代器方式：完整类定义"""
    def __init__(self, n):
        self.n = n
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.n:
            raise StopIteration
        val = self.i
        self.i += 1
        return val


def count_up_generator(n):
    """生成器方式：简洁函数"""
    i = 0
    while i < n:
        yield i
        i += 1


def test_iterator_vs_generator():
    """对比迭代器和生成器的代码量"""
    print("=" * 60)
    print("迭代器 vs 生成器代码对比")
    print("=" * 60)

    print("\n▶ 功能相同：生成 0..n-1")
    n = 5

    # 迭代器方式
    it = CountUpIterator(n)
    print(f"   迭代器: {list(it)}")

    # 生成器方式
    gen = count_up_generator(n)
    print(f"   生成器: {list(gen)}")

    print("\n▶ 代码行数对比:")
    import inspect
    it_lines = len(inspect.getsource(CountUpIterator).split('\n'))
    gen_lines = len(inspect.getsource(count_up_generator).split('\n'))
    print(f"   迭代器 CountUpIterator: {it_lines} 行")
    print(f"   生成器 count_up_generator: {gen_lines} 行")
    print(f"   生成器减少了 {it_lines - gen_lines} 行")


# ============================================================
# 9. 生成器陷阱
# ============================================================

def test_generator_traps():
    """展示生成器的常见陷阱"""
    print("=" * 60)
    print("生成器常见陷阱")
    print("=" * 60)

    # 陷阱 1: 生成器只能遍历一次
    print("\n⚠️ 陷阱 1: 生成器只能遍历一次")
    gen = (x for x in range(5))
    print(f"   第一次: {list(gen)}")
    print(f"   第二次: {list(gen)} (空的!)")

    # 陷阱 2: 意外传递生成器
    print("\n⚠️ 陷阱 2: 生成器部分消耗后传给另一个函数")
    def first_half(iterable):
        result = []
        for i, x in enumerate(iterable):
            if i >= 3:
                break
            result.append(x)
        return result

    def second_half(iterable):
        return list(iterable)

    data = (x for x in [1, 2, 3, 4, 5, 6])
    part1 = first_half(data)
    part2 = second_half(data)  # 从索引 3 开始！
    print(f"   first_half: {part1}")
    print(f"   second_half: {part2} (只有后 3 个!)")

    # 陷阱 3: 生成器提前被GC
    print("\n⚠️ 陷阱 3: 生成器变量被覆盖")
    results = []
    for i in range(3):
        gen = (x**2 for x in range(i, i+3))
        results.append(list(gen))
    print(f"   结果: {results}")

    # 陷阱 4: 在 lambda 中捕获循环变量
    print("\n⚠️ 陷阱 4: lambda 中的延迟求值")
    gens = [(lambda: (yield x)) for x in range(3)]
    print(f"   这是一个常见的错误用法，yield 在 lambda 中无效")


# ============================================================
# Demo 入口
# ============================================================

def main():
    print("=" * 60)
    print("Day 022 — 生成器基础")
    print("=" * 60)

    test_simple_generator()
    test_generator_vs_expression()
    test_send()
    test_throw()
    test_close()
    test_yield_from()
    test_generator_state()
    test_iterator_vs_generator()
    test_generator_traps()

    print("\n" + "=" * 60)
    print("✅ Day 022 生成器基础完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
