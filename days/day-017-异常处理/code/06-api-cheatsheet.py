#!/usr/bin/env python3
"""
Day 017 — 异常处理 API 速查表

可运行的快速参考手册，展示 Python 异常处理全部核心 API。

运行方式：
  python3 06-api-cheatsheet.py
"""


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════
# 1. try/except 系列
# ═══════════════════════════════════════════════════════════════

def demo_basic_structures():
    """异常处理基本结构"""
    section("try/except 系列")

    # --- 基础 try/except ---
    try:
        1 / 0
    except ZeroDivisionError:
        print("  ✅ try/except: 基础捕获")

    # --- 多个 except ---
    try:
        [][5]
    except IndexError:
        print("  ✅ 多个 except: 捕获 IndexError")
    except KeyError:
        print("  不会执行")

    # --- 元组捕获 ---
    try:
        {}["missing"]
    except (KeyError, IndexError, ValueError):
        print("  ✅ 元组捕获: 同时处理多种异常")

    # --- except as ---
    try:
        int("abc")
    except ValueError as e:
        print(f"  ✅ except ... as e: 获取异常对象 → {e}")

    # --- else ---
    try:
        result = 10 / 2
    except ZeroDivisionError:
        pass
    else:
        print(f"  ✅ else: 无异常时执行 → 结果 = {result}")

    # --- finally ---
    try:
        1 / 0
    except ZeroDivisionError:
        print("  ✅ finally: 始终执行", end="")
    finally:
        print("（包括清理操作）")


# ═══════════════════════════════════════════════════════════════
# 2. raise 系列
# ═══════════════════════════════════════════════════════════════

def demo_raise_api():
    """raise 用法"""
    section("raise 系列")

    # --- 简单 raise ---
    try:
        raise ValueError("主动抛出异常")
    except ValueError as e:
        print(f"  ✅ raise: 主动抛出 → {e}")

    # --- raise Exception("msg") ---
    try:
        raise RuntimeError("运行时错误")
    except RuntimeError as e:
        print(f"  ✅ raise RuntimeError: {e}")

    # --- 裸 raise ---
    def inner():
        raise ValueError("内部错误")

    def outer():
        try:
            inner()
        except ValueError:
            print("  ✅ 裸 raise: 记录日志后重抛")
            raise

    try:
        outer()
    except ValueError as e:
        print(f"     传播到外层 → {e}")

    # --- raise ... from ---
    try:
        try:
            raise FileNotFoundError("文件缺失")
        except FileNotFoundError as e:
            raise RuntimeError("加载失败") from e
    except RuntimeError as e:
        print(f"  ✅ raise ... from: {e}")
        print(f"     原因: {e.__cause__}")

    # --- raise ... from None ---
    try:
        try:
            raise PermissionError("无权限")
        except PermissionError:
            raise RuntimeError("访问被拒") from None
    except RuntimeError as e:
        print(f"  ✅ raise ... from None: {e}")
        print(f"     原因: {e.__cause__} (已隐藏)")


# ═══════════════════════════════════════════════════════════════
# 3. assert
# ═══════════════════════════════════════════════════════════════

def demo_assert_api():
    """assert 用法"""
    section("assert 断言")

    assert 1 + 1 == 2, "数学还是正确的"
    print("  ✅ assert True: 断言通过")

    try:
        assert 1 + 1 == 3, "数学错误！"
    except AssertionError as e:
        print(f"  ✅ assert False: AssertionError → {e}")

    print("  ⚠️  注意: assert 在 python -O 下禁用")


# ═══════════════════════════════════════════════════════════════
# 4. sys 模块 API
# ═══════════════════════════════════════════════════════════════

def demo_sys_api():
    """sys.exc_info 系列"""
    section("sys 模块")

    import sys

    try:
        1 / 0
    except ZeroDivisionError:
        exc_type, exc_val, exc_tb = sys.exc_info()
        print(f"  ✅ sys.exc_info():")
        print(f"     类型: {exc_type.__name__}")
        print(f"     值: {exc_val}")
        print(f"     traceback: {exc_tb}")


# ═══════════════════════════════════════════════════════════════
# 5. traceback 模块 API
# ═══════════════════════════════════════════════════════════════

def demo_traceback_api():
    """traceback 模块"""
    section("traceback 模块")

    import traceback

    try:
        1 / 0
    except ZeroDivisionError:
        tb_str = traceback.format_exc()
        lines = tb_str.strip().split("\n")
        print(f"  ✅ traceback.format_exc():")
        for line in lines[-3:]:
            print(f"     {line}")

    try:
        raise ValueError("测试")
    except ValueError as e:
        lines = traceback.format_exception_only(type(e), e)
        print(f"  ✅ traceback.format_exception_only:")
        for line in lines:
            print(f"     {line.strip()}")


# ═══════════════════════════════════════════════════════════════
# 6. contextlib 辅助
# ═══════════════════════════════════════════════════════════════

def demo_contextlib_helpers():
    """contextlib 辅助工具"""
    section("contextlib 辅助")

    from contextlib import suppress

    # suppress — 静默指定异常
    with suppress(FileNotFoundError):
        open("/nonexistent/file.txt")  # 不会报错
    print("  ✅ contextlib.suppress: 静默指定异常")

    # redirect_stderr
    from contextlib import redirect_stderr
    import io
    f = io.StringIO()
    with redirect_stderr(f):
        try:
            1 / 0
        except ZeroDivisionError:
            print("  ✅ contextlib.redirect_stderr: 重定向错误输出", file=__import__('sys').stderr)


# ═══════════════════════════════════════════════════════════════
# 7. ExceptionGroup (Python 3.11+)
# ═══════════════════════════════════════════════════════════════

def demo_exception_group():
    """ExceptionGroup (Python 3.11+)"""
    section("ExceptionGroup (3.11+)")

    try:
        exec("""
from exceptiongroup import ExceptionGroup
try:
    raise ExceptionGroup("多个错误", [
        ValueError("值1"),
        TypeError("类型2"),
    ])
except* ValueError as e:
    pass
except* TypeError as e:
    pass
""")
    except Exception as e:
        print(f"  ℹ️  ExceptionGroup 需要 Python 3.11+")
        if "ExceptionGroup" in str(e):
            print(f"     当前 Python: {__import__('sys').version.split()[0]}")


# ═══════════════════════════════════════════════════════════════
# 8. 内置异常速查
# ═══════════════════════════════════════════════════════════════

def demo_builtin_exceptions():
    """常见内置异常一览"""
    section("常见内置异常速查")

    exceptions = [
        ("ValueError", "int('abc')", True),
        ("TypeError", "1 + 'a'", True),
        ("IndexError", "[][10]", True),
        ("KeyError", "{}['k']", True),
        ("FileNotFoundError", "open('/x')", True),
        ("ZeroDivisionError", "1/0", True),
        ("AttributeError", "None.x", True),
        ("ImportError", "import nonexistent", True),
        ("StopIteration", "next(iter([]))", True),
        ("RuntimeError", "raise RuntimeError()", True),
    ]

    print(f"  {'异常类型':<25s} {'触发场景':<30s} {'可捕获':<8s}")
    print(f"  {'-'*25} {'-'*30} {'-'*8}")
    for name, trigger, catchable in exceptions:
        status = "✅" if catchable else "❌"
        print(f"  {name:<25s} {trigger:<30s} {status:<8s}")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 异常处理 API 速查表")
    print()

    demo_basic_structures()
    demo_raise_api()
    demo_assert_api()
    demo_sys_api()
    demo_traceback_api()
    demo_contextlib_helpers()
    demo_exception_group()
    demo_builtin_exceptions()

    print()
    print("=" * 60)
    print("  ✅ API 速查完毕！")
    print("=" * 60)


if __name__ == "__main__":
    main()
