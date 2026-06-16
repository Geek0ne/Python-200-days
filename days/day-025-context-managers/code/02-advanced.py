#!/usr/bin/env python3
"""
Day 025 — 上下文管理器进阶

涵盖：
1. contextlib 模块：@contextmanager 装饰器
2. contextlib.closing — 任意对象的 close 方法
3. contextlib.suppress — 静默忽略特定异常
4. contextlib.redirect_stdout / redirect_stderr
5. contextlib.redirect_stderr
6. contextlib.ExitStack — 动态管理多个上下文管理器
7. contextlib.nullcontext — 条件上下文
8. 嵌套上下文管理器的等价写法
9. 异步上下文管理器（__aenter__ / __aexit__）
"""

import contextlib
import sys
import io
import os


print("=" * 60)
print("1. @contextmanager 装饰器 — 生成器方式")
print("=" * 60)


@contextlib.contextmanager
def managed_file(filename, mode="r"):
    """使用生成器实现的上下文管理器

    原理：
      - yield 之前 → __enter__
      - yield 的值 → as 子句绑定的值
      - yield 之后 → __exit__
      - 如果生成器中抛异常，自动在 yield 处传播

    等价于：
      class ManagedFile:
          def __enter__(self): ...
          def __exit__(self, ...): ...
    """
    print(f"  [enter] 打开 {filename}")
    f = open(filename, mode)
    try:
        yield f  # ← __enter__ 返回值
    finally:
        print(f"  [exit] 关闭 {filename}")
        f.close()


print("--- 使用 @contextmanager ---")
with managed_file("/etc/hostname", "r") as f:
    content = f.read()
    print(f"  内容: {content.strip()}")


# 更实用的例子：数据库事务
@contextlib.contextmanager
def transaction(conn_name="default"):
    """模拟数据库事务上下文管理器"""
    print(f"  [BEGIN] 事务开始 ({conn_name})")
    # 模拟 begin
    yield  # 事务上下文

    # yield 后没有异常 → commit
    # 如果有异常，会跳过 yield 后的代码
    print(f"  [COMMIT] 事务提交 ({conn_name})")


print("\n--- 模拟事务提交 ---")
with transaction("db1"):
    print("  执行 SQL 操作...")

print("\n--- 模拟事务回滚 ---")
try:
    with transaction("db2"):
        print("  执行 SQL 操作...")
        raise RuntimeError("SQL 执行失败！")
except RuntimeError:
    print("  (外层) 事务自动回滚（未达到 commit）")


# 如果要支持回滚，需要捕获异常
@contextlib.contextmanager
def safe_transaction(conn_name="default"):
    """带回滚的事务上下文管理器"""
    print(f"  [BEGIN] 事务开始 ({conn_name})")
    try:
        yield
        print(f"  [COMMIT] 事务提交 ({conn_name})")
    except Exception as e:
        print(f"  [ROLLBACK] 事务回滚 ({conn_name}): {e}")
        raise  # 重新抛出异常


print("\n--- 带回滚的事务 ---")
try:
    with safe_transaction("db3"):
        raise ValueError("数据校验失败")
except ValueError:
    print("  (外层) 异常继续传播")


print()
print("=" * 60)
print("2. @contextmanager 的异常传播机制")
print("=" * 60)


@contextlib.contextmanager
def demo_exception_handling():
    """演示 @contextmanager 的异常处理"""
    print("  [enter]")
    try:
        yield
    except ZeroDivisionError as e:
        print(f"  [处理] 捕获到 ZeroDivisionError: {e}")
        # 不重新抛出 → 抑制异常
        print(f"  [处理] 异常被抑制")
    except Exception as e:
        print(f"  [处理] 其他异常: {e}")
        raise  # 重新抛出，继续传播


print("--- 被抑制的异常 ---")
with demo_exception_handling():
    1 / 0
print("  (继续执行)")

print("\n--- 未被抑制的异常 ---")
try:
    with demo_exception_handling():
        raise ValueError("其他异常")
except ValueError:
    print("  (外层) 异常继续传播")


print()
print("=" * 60)
print("3. contextlib.closing — 简化 close 方法")
print("=" * 60)


class MyConnection:
    """模拟一个需要 close 的连接对象"""

    def __init__(self, name):
        self.name = name
        print(f"  [init] 创建连接 {name}")

    def query(self, sql):
        print(f"  [query] 在 {self.name} 上执行: {sql}")
        return "result"

    def close(self):
        print(f"  [close] 关闭连接 {self.name}")


print("--- 使用 contextlib.closing ---")
with contextlib.closing(MyConnection("DB-Pool-1")) as conn:
    result = conn.query("SELECT 1")
    print(f"  查询结果: {result}")
print("  连接已自动关闭")

# closing 等价的手写实现：
class MyClosing:
    """contextlib.closing 的简化实现"""
    def __init__(self, thing):
        self.thing = thing
    def __enter__(self):
        return self.thing
    def __exit__(self, *exc_info):
        self.thing.close()


print("\n--- 使用手动实现的 MyClosing ---")
with MyClosing(MyConnection("DB-Pool-2")) as conn:
    conn.query("SELECT 2")


print()
print("=" * 60)
print("4. contextlib.suppress — 静默忽略异常")
print("=" * 60)

print("--- 传统方式 ---")
try:
    os.remove("/tmp/nonexistent_file.txt")
except FileNotFoundError:
    pass
print("  (已忽略 FileNotFoundError)")

print("\n--- 使用 contextlib.suppress ---")
with contextlib.suppress(FileNotFoundError):
    os.remove("/tmp/nonexistent_file.txt")
print("  (已静默处理)")

print("\n--- 抑制多种异常 ---")
with contextlib.suppress(FileNotFoundError, PermissionError):
    os.remove("/tmp/nonexistent_file.txt")
print("  (多种异常都被抑制)")


print()
print("=" * 60)
print("5. contextlib.redirect_stdout / redirect_stderr")
print("=" * 60)


print("--- redirect_stdout 到 StringIO ---")
fake_stdout = io.StringIO()
with contextlib.redirect_stdout(fake_stdout):
    print("这行输出被重定向到 StringIO")
    print("这行也一样")
    print("所有 print 都去了 StringIO")
print("重定向结束，回到控制台")
captured = fake_stdout.getvalue()
print(f"捕获到的输出:\n{captured}")


print("--- 重定向到文件 ---")
with open("/tmp/redirected_output.txt", "w") as f:
    with contextlib.redirect_stdout(f):
        print("这行写入文件")
        print("这行也写入文件")
print("检查文件内容:")
with open("/tmp/redirected_output.txt") as f:
    print(f.read())


# redirect_stderr 同理
print("\n--- redirect_stderr ---")
fake_stderr = io.StringIO()
with contextlib.redirect_stderr(fake_stderr):
    sys.stderr.write("错误信息\n")
    sys.stderr.write("更多错误\n")
print("stderr 已恢复")
print(f"stderr 捕获内容: {fake_stderr.getvalue()!r}")


print()
print("=" * 60)
print("6. contextlib.ExitStack — 动态管理多个管理器")
print("=" * 60)


# ExitStack 适合以下场景：
# 1. 不知道运行时需要打开多少资源
# 2. 需要条件性地进入上下文
# 3. 需要将上下文管理器的生命周期交给另一个对象

class Connection:
    """模拟数据库连接"""
    def __init__(self, name):
        self.name = name
        print(f"  [连接] {self.name} 已建立")

    def close(self):
        print(f"  [关闭] {self.name} 已释放")

    def execute(self, sql):
        print(f"  [执行] {self.name}: {sql}")


print("--- ExitStack — 动态添加资源 ---")
with contextlib.ExitStack() as stack:
    # 条件性打开连接
    conn1 = stack.enter_context(contextlib.closing(Connection("主库")))
    conn1.execute("SELECT 1")

    # 根据需要打开更多连接
    if True:
        conn2 = stack.enter_context(contextlib.closing(Connection("从库")))
        conn2.execute("SELECT 2")

    print("  退出 with 块，所有连接自动关闭")
print("  所有连接已释放")


print("\n--- ExitStack — 推迟清理 ---")


class ResourceManager:
    """使用 ExitStack 管理多个资源的生命周期"""

    def __init__(self):
        self._stack = contextlib.ExitStack()
        self._resources = []

    def add_connection(self, name):
        conn = Connection(name)
        self._stack.enter_context(contextlib.closing(conn))
        self._resources.append(conn)
        return conn

    def close_all(self):
        """手动关闭所有资源"""
        self._stack.close()
        print("  所有资源已清理")


manager = ResourceManager()
conn_a = manager.add_connection("连接-A")
conn_b = manager.add_connection("连接-B")
conn_a.execute("INSERT INTO ...")
conn_b.execute("UPDATE ...")
print("  手动触发清理...")
manager.close_all()


print()
print("=" * 60)
print("7. contextlib.nullcontext — 条件上下文")
print("=" * 60)


def process_data(data, need_profiling=False):
    """条件性使用上下文管理器

    场景：仅在调试时启用性能分析
    """
    # nullcontext 是一个"什么都不做"的上下文管理器
    # 当 need_profiling=False 时，创建 "虚拟" 上下文
    cm = cProfile.Profile() if need_profiling else contextlib.nullcontext()

    with cm as profiler:
        # 模拟数据处理
        result = sum(data)
        print(f"  处理结果: {result}")

    # 如果启用了性能分析，打印结果
    if need_profiling and hasattr(profiler, 'print_stats'):
        # profiler.print_stats()
        pass

    return result


import cProfile
import io

print("--- 无性能分析 ---")
process_data(range(1000), need_profiling=False)

print("\n--- 有性能分析 ---")
process_data(range(1000), need_profiling=True)


print()
print("=" * 60)
print("8. contextlib.ContextDecorator — 类装饰器")
print("=" * 60)


class trace(contextlib.ContextDecorator):
    """既是上下文管理器，又是装饰器"""

    def __init__(self, label="trace"):
        self.label = label

    def __enter__(self):
        print(f"  [enter] {self.label}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"  [exit] {self.label} (异常: {exc_type.__name__})")
        else:
            print(f"  [exit] {self.label} (正常)")
        return False


# 作为上下文管理器使用
print("--- 作为上下文管理器 ---")
with trace("操作1"):
    print("  执行操作...")

# 作为装饰器使用
print("\n--- 作为装饰器 ---")


@trace("操作2")
def do_work():
    print("  执行 do_work...")


do_work()

print("\n--- 装饰器 + 异常 ---")


@trace("操作3")
def failing_work():
    print("  即将失败...")
    raise ValueError("失败了")


try:
    failing_work()
except ValueError:
    print("  (外层捕获异常)")


print()
print("=" * 60)
print("9. 嵌套上下文管理器的等价写法")
print("=" * 60)


@contextlib.contextmanager
def resource(name):
    print(f"  [+] 获得 {name}")
    yield name
    print(f"  [-] 释放 {name}")


print("--- 方式 1：嵌套 ---")
with resource("A") as a:
    with resource("B") as b:
        print(f"  使用 {a} 和 {b}")

print("\n--- 方式 2：单行多个（Python 3.1+）---")
with resource("A") as a, resource("B") as b:
    print(f"  使用 {a} 和 {b}")

print("\n--- 方式 3：contextlib.ExitStack ---")
with contextlib.ExitStack() as stack:
    a = stack.enter_context(resource("A"))
    b = stack.enter_context(resource("B"))
    print(f"  使用 {a} 和 {b}")

# 方式 4：Python 3.10+ 的括号语法
# with (
#     resource("A") as a,
#     resource("B") as b,
#     resource("C") as c,
# ):
#     print(f"  使用 {a}, {b}, {c}")


print()
print("=" * 60)
print("10. 异步上下文管理器 — __aenter__ / __aexit__")
print("=" * 60)


import asyncio


class AsyncResource:
    """异步上下文管理器"""

    async def __aenter__(self):
        print("  [AENTER] 异步打开资源")
        await asyncio.sleep(0.1)  # 模拟异步 I/O
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print("  [AEXIT] 异步释放资源")
        await asyncio.sleep(0.1)
        if exc_type:
            print(f"  [AEXIT] 异常: {exc_type.__name__}: {exc_val}")
        return False

    async def work(self):
        print("  [work] 异步执行任务")
        await asyncio.sleep(0.1)
        return "result"


async def main():
    print("--- 异步上下文管理器 ---")
    async with AsyncResource() as res:
        result = await res.work()
        print(f"  结果: {result}")
    print("  (async with 结束)")

    print("\n--- 异步上下文管理器 + 异常 ---")
    try:
        async with AsyncResource() as res:
            raise RuntimeError("异步操作失败")
    except RuntimeError as e:
        print(f"  (外层捕获): {e}")


asyncio.run(main())


# @asynccontextmanager 装饰器
from contextlib import asynccontextmanager


@asynccontextmanager
async def async_managed_file(filename, mode="r"):
    """异步版本的上下文管理器"""
    print(f"  [AENTER] 打开 {filename}")
    f = await asyncio.to_thread(open, filename, mode)
    try:
        yield f
    finally:
        print(f"  [AEXIT] 关闭 {filename}")
        await asyncio.to_thread(f.close)


async def main2():
    print("\n--- @asynccontextmanager ---")
    async with async_managed_file("/etc/hostname", "r") as f:
        content = await asyncio.to_thread(f.read)
        print(f"  内容: {content.strip()}")


asyncio.run(main2())


print()
print("✅ 所有进阶示例执行完毕")
