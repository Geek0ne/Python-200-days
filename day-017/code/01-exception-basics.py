#!/usr/bin/env python3
"""
Day 017 — 异常处理基础用法示例

涵盖：
  1. try/except 基本捕获
  2. 多个 except 子句
  3. try/except/else
  4. try/except/finally
  5. 完整结构：try/except/else/finally
  6. 异常链与 raise from
  7. 重抛异常
  8. 断言 assert

运行方式：
  python3 01-exception-basics.py
"""

import sys
import json
import traceback

SEP = "=" * 60


# ═══════════════════════════════════════════════════════════════
# 1. try/except 最简形式
# ═══════════════════════════════════════════════════════════════

def demo_basic_try_except():
    """基本 try/except 捕获异常"""
    print(SEP)
    print("1️⃣  基本 try/except")
    print(SEP)

    try:
        result = 10 / 0
        print("这行不会执行")
    except ZeroDivisionError:
        print("捕获到: 不能除以零！")

    # 捕获多个异常
    try:
        values = {"a": 1}
        print(values["b"])  # KeyError
    except (KeyError, IndexError) as e:
        print(f"捕获到多个异常类型: {e}")

    # 使用 as 获取异常对象
    try:
        int("不是数字")
    except ValueError as e:
        print(f"ValueError: {e}  (类型: {type(e).__name__})")


# ═══════════════════════════════════════════════════════════════
# 2. 分层捕获多个不同异常
# ═══════════════════════════════════════════════════════════════

def demo_hierarchical_except():
    """分层捕获不同异常"""
    print(SEP)
    print("2️⃣  分层捕获多个异常")
    print(SEP)

    def risky_calc(x):
        """根据 x 的值触发不同异常"""
        if x == 0:
            return 10 / 0  # ZeroDivisionError
        elif x == 1:
            return int("abc")  # ValueError
        elif x == 2:
            d = {}
            return d["missing"]  # KeyError
        return 42

    for x in [0, 1, 2, 3]:
        try:
            print(f"\nrisky_calc({x}) = ", end="")
            result = risky_calc(x)
            print(result)
        except ZeroDivisionError:
            print("❌ ZeroDivisionError — 除零错误")
        except ValueError:
            print("❌ ValueError — 值无效")
        except KeyError as e:
            print(f"❌ KeyError — 键不存在: {e}")
        else:
            print(f"✅ 成功: {result}")
        finally:
            print(f"   finally: 清理操作 (x={x})")


# ═══════════════════════════════════════════════════════════════
# 3. try/except/else — 无异常时的分支
# ═══════════════════════════════════════════════════════════════

def demo_else_clause():
    """else 子句 — 仅当无异常时执行"""
    print(SEP)
    print("3️⃣  else 子句 (无异常时执行)")
    print(SEP)

    def safe_divide(a, b):
        """安全除法"""
        try:
            result = a / b
        except ZeroDivisionError:
            print(f"  {a}/{b} = ❌ 除零错误")
            return None
        except TypeError:
            print(f"  {a}/{b} = ❌ 类型错误")
            return None
        else:
            # 仅当 try 完成无异常时执行
            print(f"  {a}/{b} = ✅ {result}")
            return result
        finally:
            print(f"    [finally] 除法运算结束")

    safe_divide(10, 2)
    safe_divide(10, 0)
    safe_divide(10, "a")


# ═══════════════════════════════════════════════════════════════
# 4. try/except/finally — 始终执行清理
# ═══════════════════════════════════════════════════════════════

def demo_finally():
    """finally 始终执行 — 即使 return 也会执行"""
    print(SEP)
    print("4️⃣  finally — 始终执行")
    print(SEP)

    def read_file(path):
        """模拟文件读取，演示 finally"""
        f = None
        try:
            print(f"  尝试打开: {path}")
            f = open(path, "r")
            return f.read()
        except FileNotFoundError:
            print(f"  ❌ 文件不存在: {path}")
            return "FALLBACK_DATA"
        finally:
            print(f"  ✅ finally: 确保关闭文件...")
            if f and not f.closed:
                f.close()
                print(f"  ✅ 文件已关闭: {f.closed}")

    print("\n--- 情况 1: 文件存在 ---")
    # 创建临时文件
    with open("/tmp/_demo_file.txt", "w") as tf:
        tf.write("Hello, 异常处理!")
    print(f"  内容: {read_file('/tmp/_demo_file.txt')!r}")

    print("\n--- 情况 2: 文件不存在 ---")
    print(f"  内容: {read_file('/nonexistent.txt')!r}")


# ═══════════════════════════════════════════════════════════════
# 5. 异常链与 raise from
# ═══════════════════════════════════════════════════════════════

class ConfigError(Exception):
    """配置错误"""
    pass


def demo_exception_chaining():
    """异常链 — raise from"""
    print(SEP)
    print("5️⃣  异常链 — raise ... from")
    print(SEP)

    config_data = '{"name": "test", "version": }'  # 无效 JSON

    def load_config(data: str) -> dict:
        """加载配置，将底层异常包装为业务异常"""
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            # 使用 from 建立异常链
            raise ConfigError("配置文件 JSON 格式无效") from e

    def load_config_suppressed(data: str) -> dict:
        """使用 from None 抑制异常链"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ConfigError("配置文件错误") from None

    # 展示异常链
    print("\n▶ 使用 raise ... from (保留因果链):")
    try:
        load_config(config_data)
    except ConfigError as e:
        print(f"  ConfigError: {e}")
        cause = e.__cause__
        if cause:
            print(f"  ├── 由 {type(cause).__name__} 引发: {cause}")
            print(f"  └── traceback:\n{''.join(traceback.format_exception_only(type(cause), cause)).rstrip()}")

    print("\n▶ 使用 raise ... from None (抑制因果链):")
    try:
        load_config_suppressed(config_data)
    except ConfigError as e:
        print(f"  ConfigError: {e}")
        print(f"  __cause__ = {e.__cause__}")  # None


# ═══════════════════════════════════════════════════════════════
# 6. 重抛与保留追踪
# ═══════════════════════════════════════════════════════════════

def demo_reraise():
    """重抛异常（保留完整 traceback）"""
    print(SEP)
    print("6️⃣  重抛异常 — 保留完整 traceback")
    print(SEP)

    def low_level():
        """底层函数"""
        raise PermissionError("底层: 没有权限访问资源")

    def mid_level():
        """中层函数"""
        try:
            low_level()
        except PermissionError as e:
            print(f"  [mid_level] 记录日志: {e}")
            # 记录后重抛，保留原始 traceback
            print(f"  [mid_level] 重抛异常...")
            raise  # 裸 raise = 重抛当前异常

    def high_level():
        """高层函数"""
        try:
            mid_level()
        except PermissionError as e:
            print(f"  [high_level] 最终处理: {e}")

    print("\n▶ 重抛流程:")
    high_level()


# ═══════════════════════════════════════════════════════════════
# 7. 断言 assert
# ═══════════════════════════════════════════════════════════════

def demo_assert():
    """断言用法与注意事项"""
    print(SEP)
    print("7️⃣  断言 — assert 语句")
    print(SEP)

    def withdraw(balance: float, amount: float) -> float:
        """模拟取款（内部不变量检查）"""
        assert amount > 0, f"取款金额 ({amount}) 必须为正数"
        assert balance >= amount, f"余额 ({balance}) 不足 ({amount})"
        return balance - amount

    # 正常情况
    result = withdraw(100.0, 30.0)
    print(f"  ✅ 取款成功, 余额: {result}")

    # 断言失败
    try:
        withdraw(50.0, -10.0)
    except AssertionError as e:
        print(f"  ❌ 断言触发: {e}")

    try:
        withdraw(50.0, 100.0)
    except AssertionError as e:
        print(f"  ❌ 断言触发: {e}")

    # 注意：断言不等于输入验证
    print("\n  ⚠️  注意: 断言可被 -O 禁用，")
    print("     请勿用 assert 替代用户输入的验证！")


# ═══════════════════════════════════════════════════════════════
# 8. sys.exc_info 与 traceback 模块
# ═══════════════════════════════════════════════════════════════

def demo_exc_info():
    """使用 sys.exc_info() 与 traceback 模块"""
    print(SEP)
    print("8️⃣  sys.exc_info() 与 traceback 模块")
    print(SEP)

    try:
        1 / 0
    except ZeroDivisionError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        print(f"  异常类型: {exc_type.__name__}")
        print(f"  异常值:   {exc_value}")
        print(f"  traceback: {exc_tb}")
        print(f"\n  格式化 traceback:")
        fmt = traceback.format_exc()
        for line in fmt.strip().split("\n"):
            print(f"    {line}")


# ═══════════════════════════════════════════════════════════════
# 主函数
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 异常处理基础用法示例")
    print()

    demo_basic_try_except()
    demo_hierarchical_except()
    demo_else_clause()
    demo_finally()
    demo_exception_chaining()
    demo_reraise()
    demo_assert()
    demo_exc_info()

    print(SEP)
    print("✅ 所有演示完成！")


if __name__ == "__main__":
    main()
