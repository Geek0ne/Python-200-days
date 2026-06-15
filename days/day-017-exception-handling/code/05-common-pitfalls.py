#!/usr/bin/env python3
"""
Day 017 — 常见异常处理陷阱与避坑

用实际代码演示最常犯的异常处理错误，以及正确的做法。

运行方式：
  python3 05-common-pitfalls.py
"""

SEP = "=" * 60


# ═══════════════════════════════════════════════════════════════
# 陷阱 1：裸 except 捕获了不该捕获的
# ═══════════════════════════════════════════════════════════════

def pitfall_bare_except():
    """陷阱：使用裸 except 捕获所有异常"""
    print(SEP)
    print("🚩 陷阱 1：裸 except 捕获所有异常")
    print(SEP)

    def bad_example():
        """❌ 裸 except 连 KeyboardInterrupt 都捕获了"""
        try:
            # 模拟一个耗时操作
            import time
            time.sleep(10)
        except:  # ← 捕获了 BaseException 的所有子类！
            print("  捕获到异常（但可能是 Ctrl+C）")

    def good_example():
        """✅ 只捕获 Exception 及其子类"""
        try:
            import time
            time.sleep(10)
        except Exception:  # ← 不会捕获 KeyboardInterrupt, SystemExit
            print("  捕获到 Exception 类型异常")

    print("\n  ❌ 错误做法: except: 捕获一切")
    print("    包括 KeyboardInterrupt (Ctrl+C) 和 SystemExit")
    print("  ✅ 正确做法: except Exception: 只捕获常规异常")


# ═══════════════════════════════════════════════════════════════
# 陷阱 2：空 except 吞没异常
# ═══════════════════════════════════════════════════════════════

def pitfall_swallow_exception():
    """陷阱：静默吞没异常"""
    print(SEP)
    print("🚩 陷阱 2：静默吞没异常")
    print(SEP)

    def bad_example():
        """❌ 捕获后什么都不做"""
        try:
            result = 10 / 0
        except ZeroDivisionError:
            pass  # ← 错误被静默吞掉！

    def good_example():
        """✅ 至少记录日志"""
        import logging
        logging.basicConfig(level=logging.WARNING)

        try:
            result = 10 / 0
        except ZeroDivisionError as e:
            logging.warning("除零错误发生: %s", e)
            # 返回默认值或重新 raise

    print("\n  ❌ 错误做法: except ... : pass")
    print("    异常被静默吞没，bug 难以追踪")
    print("  ✅ 正确做法: 至少记录日志或返回默认值")


# ═══════════════════════════════════════════════════════════════
# 陷阱 3：finally 中的 return 覆盖异常
# ═══════════════════════════════════════════════════════════════

def pitfall_finally_return():
    """陷阱：finally 中的 return 或 raise 覆盖异常"""
    print(SEP)
    print("🚩 陷阱 3：finally 中的 return 覆盖异常")
    print(SEP)

    def bad_example():
        """❌ finally return 吞掉异常"""
        try:
            raise ValueError("原始错误")
        finally:
            return 42  # ← 覆盖了 ValueError！

    def also_bad():
        """❌ finally raise 也覆盖原异常"""
        try:
            raise ValueError("原始错误")
        finally:
            raise TypeError("finally 中的新异常")

    print("\n  ❌ 错误做法:")
    result = bad_example()
    print(f"    bad_example() 返回: {result} (ValueError 被吞掉！)")

    print("\n  ❌ finally raise:")
    try:
        also_bad()
    except TypeError as e:
        print(f"    捕获到 TypeError: {e}")
        print(f"    原始 ValueError 丢失了！")

    print("\n  ✅ 建议: finally 中不要使用 return 或 raise")
    print("    finally 只适合做清理操作（关闭文件、释放资源）")


# ═══════════════════════════════════════════════════════════════
# 陷阱 4：异常处理范围过大
# ═══════════════════════════════════════════════════════════════

def pitfall_too_broad():
    """陷阱：try 块太大，捕获了不该捕获的异常"""
    print(SEP)
    print("🚩 陷阱 4：try 块范围过大")
    print(SEP)

    def bad_example():
        """❌ 整个函数都包在 try 里"""
        try:
            data = {"user": "alice"}
            name = data.get("name")
            # 假设此处本应是 .lower()，但写错了变量名
            result = name.lowe()  # NameError: .lowe()
            return result.upper()
        except KeyError:
            return "默认值"

    def good_example():
        """✅ 只包裹可能抛出异常的那一行"""
        data = {"user": "alice"}
        name = data.get("name")
        # .lowe() 会抛出 AttributeError — 不会被意外吞掉
        result = name.lowe()  # 这个 bug 不会被掩盖
        return result.upper()

    print("\n  ❌ 错误做法: 大 try 包裹过多代码")
    print("    不应该发生的 NamedError/AttributeError 被意外捕获")
    print("  ✅ 正确做法: 只包裹可能抛出特定异常的那段代码")


# ═══════════════════════════════════════════════════════════════
# 陷阱 5：混淆 exception 类型
# ═══════════════════════════════════════════════════════════════

def pitfall_wrong_exception_type():
    """陷阱：捕获了错误的异常类型"""
    print(SEP)
    print("🚩 陷阱 5：捕获错误的异常类型")
    print(SEP)

    def bad_example():
        """❌ 捕获 ValueError 但实际抛出 KeyError"""
        try:
            d = {"a": 1}
            print(d["b"])  # 抛出 KeyError，不是 ValueError
        except ValueError:
            print("  值错误")  # 永远不会执行！
        # KeyError 向上传播，程序崩溃

    def good_example():
        """✅ 捕获正确的异常类型"""
        d = {"a": 1}
        try:
            print(d["b"])
        except KeyError:
            print("  ❌ 键不存在")

    print("\n  ❌ 错误做法: 捕获的错误类型")
    print("    except ValueError 不会捕获 KeyError")
    print("  ✅ 正确做法: 根据实际异常类型确定")


# ═══════════════════════════════════════════════════════════════
# 陷阱 6：except 顺序错误
# ═══════════════════════════════════════════════════════════════

def pitfall_except_order():
    """陷阱：except 顺序从子类到父类"""
    print(SEP)
    print("🚩 陷阱 6：except 顺序错误")
    print(SEP)

    def bad_example():
        """❌ 父类在前，子类永远捕获不到"""
        try:
            int("abc")
        except Exception:  # ← 父类在前
            print("  捕获到 Exception")
        except ValueError:  # ← 子类在后，永远不会执行！
            print("  捕获到 ValueError")

    def good_example():
        """✅ 子类在前，父类在后"""
        try:
            int("abc")
        except ValueError:  # ← 子类在前
            print("  捕获到 ValueError: 值无效")
        except Exception:  # ← 父类在后
            print("  捕获到其他异常")

    print("\n  ❌ 错误做法: except Exception 先于 except ValueError")
    print("    ValueError 永远不会被执行（已被 Exception 捕获）")
    print("  ✅ 正确做法: 从具体到宽泛（子类 ➔ 父类）")


# ═══════════════════════════════════════════════════════════════
# 陷阱 7：assert 用于输入验证
# ═══════════════════════════════════════════════════════════════

def pitfall_assert_for_input():
    """陷阱：用 assert 做输入验证"""
    print(SEP)
    print("🚩 陷阱 7：用 assert 做输入验证")
    print(SEP)

    def bad_example(age_str):
        """❌ 用 assert 做验证（可被 -O 禁用）"""
        assert int(age_str) > 0, "年龄必须为正数"
        print(f"  年龄: {age_str}")

    def good_example(age_str):
        """✅ 用 raise ValueError 做验证"""
        age = int(age_str)
        if age <= 0:
            raise ValueError("年龄必须为正数")
        print(f"  年龄: {age}")

    print("\n  ❌ 错误做法: assert 检查用户输入")
    print("    python -O 运行时，assert 会被禁用！")
    print("  ✅ 正确做法: 用 if + raise ValueError")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 常见异常处理陷阱与避坑")
    print()
    print("共 7 个常见陷阱：")
    traps = [
        "裸 except 捕获了不该捕获的",
        "空 except 吞没异常",
        "finally 中的 return 覆盖异常",
        "try 块范围过大",
        "混淆异常类型",
        "except 顺序错误",
        "用 assert 做输入验证",
    ]
    for i, t in enumerate(traps, 1):
        print(f"  {i}. {t}")

    pitfall_bare_except()
    pitfall_swallow_exception()
    pitfall_finally_return()
    pitfall_too_broad()
    pitfall_wrong_exception_type()
    pitfall_except_order()
    pitfall_assert_for_input()

    print(SEP)
    print("✅ 陷阱展示完毕！")
    print("📌 黄金法则: 精确捕获、最小范围、绝不沉默、finally 只清理")


if __name__ == "__main__":
    main()
