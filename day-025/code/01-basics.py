#!/usr/bin/env python3
"""
Day 025 — 上下文管理器基础

涵盖：
1. with 语句的基本用法
2. __enter__ / __exit__ 协议详解
3. 基于类的上下文管理器
4. 异常处理机制
5. 上下文管理器 vs try/finally 对比
"""

import sys
import io


print("=" * 60)
print("1. with 语句的基本用法 — 文件操作")
print("=" * 60)

# 传统方式：需要手动关闭文件
print("--- 传统方式（需要手动 close）---")
f = None
try:
    f = open("/etc/hostname", "r")
    content = f.read()
    print(f"内容: {content.strip()}")
finally:
    if f:
        f.close()
        print("文件已手动关闭")

# with 语句方式：自动关闭
print("\n--- with 语句方式（自动管理）---")
with open("/etc/hostname", "r") as f:
    content = f.read()
    print(f"内容: {content.strip()}")
print("文件已在 with 块结束后自动关闭")


print()
print("=" * 60)
print("2. __enter__ / __exit__ 协议 — 手写上下文管理器")
print("=" * 60)


class ManagedFile:
    """一个简单的文件上下文管理器，演示 __enter__ 和 __exit__"""

    def __init__(self, filename, mode="r"):
        self.filename = filename
        self.mode = mode
        self.file = None

    def __enter__(self):
        """进入 with 块时调用

        返回值：with ... as <var> 中 <var> 获取的值
        """
        print(f"  [__enter__] 打开文件: {self.filename}")
        self.file = open(self.filename, self.mode)
        return self.file  # as 子句绑定的就是这个值

    def __exit__(self, exc_type, exc_val, exc_tb):
        """离开 with 块时调用

        参数：
          exc_type: 异常类型（无异常则为 None）
          exc_val:  异常实例（无异常则为 None）
          exc_tb:   异常回溯对象（无异常则为 None）

        返回值：
          True  → 抑制异常（不传播）
          False → 让异常继续传播（默认）
        """
        print(f"  [__exit__] 关闭文件: {self.filename}")
        if self.file:
            self.file.close()

        if exc_type is not None:
            print(f"  [__exit__] 捕获异常: {exc_type.__name__}: {exc_val}")
            # 返回 False 让异常继续传播
            return False

        print("  [__exit__] 无异常，正常退出")
        return False


print("\n--- 正常使用 ---")
with ManagedFile("/etc/hostname", "r") as f:
    content = f.read()
    print(f"  读取到: {content.strip()}")
print("  (with 块结束)")

print("\n--- 异常情况 ---")
try:
    with ManagedFile("/tmp/nonexistent_file_xyz", "r") as f:
        content = f.read()
except FileNotFoundError as e:
    print(f"  (捕获到异常): {e}")


print()
print("=" * 60)
print("3. 上下文管理器的完整生命周期")
print("=" * 60)


class LifecycleDemo:
    """演示完整生命周期"""

    def __init__(self, name):
        self.name = name
        print(f"  [__init__] 创建实例: {self.name}")

    def __enter__(self):
        print(f"  [__enter__] 进入上下文: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"  [__exit__] 退出上下文: {self.name}")
        if exc_type:
            print(f"    → 异常: {exc_type.__name__}: {exc_val}")
        else:
            print(f"    → 正常退出")
        return False

    def do_something(self):
        print(f"  [work] 执行操作: {self.name}")


print("--- 正常流程 ---")
with LifecycleDemo("A") as obj:
    obj.do_something()
print("  (外层: with 结束)")

print("\n--- 异常流程 ---")
try:
    with LifecycleDemo("B") as obj:
        obj.do_something()
        raise ValueError("出错了！")
except ValueError as e:
    print(f"  (外层捕获): {e}")


print()
print("=" * 60)
print("4. 异常处理 — 抑制异常与传播异常")
print("=" * 60)


class SuppressErrors:
    """抑制所有异常（返回 True）"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"  [SuppressErrors] 抑制异常: {exc_type.__name__}: {exc_val}")
            return True  # ← 关键：返回 True 抑制异常
        return False


class PropagateErrors:
    """让异常继续传播（返回 False）"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(f"  [PropagateErrors] 异常已记录，但让它继续传播")
            return False  # ← 关键：返回 False 让异常传播
        return False


print("--- 抑制异常（返回 True）---")
try:
    with SuppressErrors():
        print("  即将发生 ZeroDivisionError...")
        1 / 0
        print("  这行不会执行")
    print("  异常被抑制，程序继续执行到这里！")
except ZeroDivisionError:
    print("  (外层: 捕获到 ZeroDivisionError) ← 不会走到这里")

print("\n--- 传播异常（返回 False）---")
try:
    with PropagateErrors():
        print("  即将发生 ZeroDivisionError...")
        1 / 0
        print("  这行不会执行")
    print("  异常被传播，这行不会执行")
except ZeroDivisionError:
    print("  (外层: 捕获到 ZeroDivisionError) ← 异常传播到这里")


print()
print("=" * 60)
print("5. __exit__ 中处理特定异常类型")
print("=" * 60)


class HandleSpecificErrors:
    """只处理 ZeroDivisionError，其他异常继续传播"""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ZeroDivisionError:
            print(f"  [处理] ZeroDivisionError: {exc_val}")
            print(f"  [处理] 记录日志后抑制...")
            return True  # 只抑制 ZeroDivisionError
        elif exc_type is not None:
            print(f"  [不处理] 其他异常: {exc_type.__name__}: {exc_val}，继续传播")
            return False
        return False


print("--- 被处理的异常 ---")
with HandleSpecificErrors():
    1 / 0
print("  除零异常被抑制，继续执行！")

print("\n--- 不被处理的异常 ---")
try:
    with HandleSpecificErrors():
        raise ValueError("自定义错误")
except ValueError as e:
    print(f"  (外层捕获): {e}")


print()
print("=" * 60)
print("6. 上下文管理器 vs try/finally — 为什么用 with")
print("=" * 60)

print("""
with 语句相比 try/finally 的优势：

1. 简洁性
   try/finally:
       f = open('file')
       try:
           process(f)
       finally:
           f.close()
   
   with:
       with open('file') as f:
           process(f)

2. 安全性
   - 如果 open() 成功但 process() 抛异常，finally 保证关闭
   - 如果 open() 本身就抛异常，不会进入 try 块，f 不存在
   - 程序员容易忘记 try/finally，但 with 强制保证

3. 可组合性
   - 多个资源可以写在一个 with 语句中
   - with A() as a, B() as b:  ...

4. 标准化
   - 任何实现 __enter__/__exit__ 的对象都可复用
   - 上下文管理协议是 Python 标准协议的一部分
""")


# 演示：with vs try/finally 的双重保障
class Resource:
    """模拟一个需要清理的资源"""

    def __init__(self, name, fail_on_init=False):
        self.name = name
        if fail_on_init:
            raise RuntimeError(f"资源 {name} 初始化失败")
        print(f"  [init] 资源 {name} 已分配")

    def close(self):
        print(f"  [close] 资源 {self.name} 已释放")

    def use(self):
        print(f"  [use] 正在使用资源 {self.name}")


print("--- 方式 1：try/finally（容易遗漏）---")
r = Resource("DB-1")
try:
    r.use()
finally:
    r.close()

print("\n--- 方式 2：上下文管理器（强制安全）---")


class SafeResource:
    """包装 Resource 的上下文管理器"""

    def __init__(self, name, fail_on_init=False):
        self.resource = Resource(name, fail_on_init)
        self.name = name

    def __enter__(self):
        return self.resource

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.resource.close()
        return False


with SafeResource("DB-2") as r:
    r.use()


print()
print("=" * 60)
print("7. 多个上下文管理器 — 单行语法")
print("=" * 60)


class SimpleResource:
    """简单的资源上下文管理器"""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print(f"  [+] 打开资源: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"  [-] 关闭资源: {self.name} (异常: {exc_type})")
        return False

    def get_name(self):
        return self.name


# Python 3.1+ 支持单行多个上下文管理器
print("--- with A() as a, B() as b: ---")
with SimpleResource("A") as a, SimpleResource("B") as b:
    print(f"  操作 {a.get_name()} 和 {b.get_name()}")
print("  两个资源都已关闭")


print()
print("=" * 60)
print("8. 上下文管理器用于非文件资源")
print("=" * 60)


class Timer:
    """计时器上下文管理器"""

    def __enter__(self):
        import time
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.elapsed = time.perf_counter() - self.start
        print(f"  耗时: {self.elapsed:.4f}s")
        return False


class Indent:
    """缩进上下文管理器 — 控制台输出美化"""

    level = -1  # 类级缩进级别

    def __init__(self, indent_str="  "):
        self.indent_str = indent_str
        self.prev_level = None

    def __enter__(self):
        Indent.level += 1
        self.prev_level = Indent.level
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Indent.level -= 1
        return False

    @staticmethod
    def write(text):
        """使用当前缩进输出"""
        print(f"{'  ' * Indent.level}{text}")


print("--- 计时器 ---")
with Timer() as timer:
    total = sum(range(1_000_000))
print(f"  sum(range(1_000_000)) = {total}")

print("\n--- 缩进管理器 ---")
Indent.write("开始")
with Indent("  "):
    Indent.write("外层")
    with Indent("  "):
        Indent.write("内层")
    Indent.write("回到外层")
Indent.write("结束")


print()
print("=" * 60)
print("9. 上下文管理器的常见陷阱")
print("=" * 60)

print("""
陷阱 1：__exit__ 返回 True 可能掩盖 bug
  - 如果不小心返回 True，异常会被静默吞掉
  - 调试时很难发现

陷阱 2：__enter__ 返回值不等于 with 对象
  - __enter__ 可以返回任何对象
  - 常见坑：返回 self 还是 self.resource？
  - 一定要搞清楚 as 子句绑定的是什么

陷阱 3：重新进入
  - 上下文管理器默认不支持重复使用
  - 大多数管理器只能在一个 with 块中使用一次

陷阱 4：__exit__ 中的异常
  - __exit__ 自身抛出异常会覆盖原异常
  - 原异常会丢失
""")


# 演示陷阱 3：不能重复使用
class OneTimeManager:
    """只能使用一次的上下文管理器"""

    used = False

    def __enter__(self):
        if OneTimeManager.used:
            raise RuntimeError("该上下文管理器已使用过！")
        OneTimeManager.used = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


print("--- 一次性管理器 ---")
with OneTimeManager():
    print("  第一次使用 OK")
# 第二次使用会报错
try:
    with OneTimeManager():
        print("  第二次使用？")
except RuntimeError as e:
    print(f"  第二次使用失败: {e}")

print("\n✅ 代码执行完毕")
