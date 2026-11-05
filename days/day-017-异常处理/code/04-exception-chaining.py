#!/usr/bin/env python3
"""
Day 017 — 异常链与 raise 进阶用法

深入展示异常链（Exception Chaining）的各种模式和最佳实践。

运行方式：
  python3 04-exception-chaining.py
"""

import sys
import json
import traceback

SEP = "=" * 60


# ═══════════════════════════════════════════════════════════════
# 1. 裸 raise — 重抛当前异常（保留完整 traceback）
# ═══════════════════════════════════════════════════════════════

def demo_bare_raise():
    """裸 raise 保留完整调用栈"""
    print(SEP)
    print("1️⃣  裸 raise — 重抛当前异常")
    print(SEP)

    def validate(age_str):
        try:
            age = int(age_str)
            if age < 0:
                raise ValueError(f"年龄不能为负: {age}")
            return age
        except ValueError:
            print("  [validate] 记录错误日志")
            raise  # 保留原 traceback，继续传播

    def process_age(data):
        try:
            age = validate(data)
            return f"年龄: {age}"
        except ValueError as e:
            print(f"  [process_age] 最终处理: {e}")
            return "无效"

    print("\n▶ 裸 raise 传播流程:")
    result = process_age("-5")
    print(f"  结果: {result}")


# ═══════════════════════════════════════════════════════════════
# 2. raise ... from — 显式异常链
# ═══════════════════════════════════════════════════════════════

class BusinessError(Exception):
    """业务异常"""
    pass

def demo_explicit_chaining():
    """显式异常链 — 保留因果关系"""
    print(SEP)
    print("2️⃣  raise ... from — 显式异常链")
    print(SEP)

    def fetch_user_from_api(user_id):
        """模拟 API 调用"""
        raise ConnectionError(f"无法连接到用户服务 (user_id={user_id})")

    def get_user(user_id):
        """获取用户信息，将网络异常包装为业务异常"""
        try:
            return fetch_user_from_api(user_id)
        except ConnectionError as e:
            raise BusinessError("获取用户信息失败") from e

    print("\n▶ 异常链输出:")
    try:
        get_user(42)
    except BusinessError as e:
        print(f"  业务异常: {e}")
        print(f"  原因: {type(e.__cause__).__name__}: {e.__cause__}")
        print()
        print("  完整 Traceback:")
        traceback.print_exc()


# ═══════════════════════════════════════════════════════════════
# 3. raise ... from None — 抑制异常链
# ═══════════════════════════════════════════════════════════════

def demo_suppress_chaining():
    """抑制异常链 — 隐藏内部细节"""
    print(SEP)
    print("3️⃣  raise ... from None — 抑制异常链")
    print(SEP)

    def parse_config(data):
        """解析配置，抑制 JSON 解析细节"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("配置格式错误") from None
            # from None 隐藏了 JSONDecodeError 的细节

    print("\n▶ 抑制链（只暴露业务异常）:")
    try:
        parse_config("{invalid: json")
    except ValueError as e:
        print(f"  捕获: {e}")
        print(f"  __cause__ = {e.__cause__}")
        print(f"  __suppress_context__ = {e.__suppress_context__}")
        print("  用户看到的是简洁的错误，内部细节被隐藏")


# ═══════════════════════════════════════════════════════════════
# 4. 隐式异常链 — Python 自动链接
# ═══════════════════════════════════════════════════════════════

def demo_implicit_chaining():
    """隐式异常链 — Python 自动建立 __context__"""
    print(SEP)
    print("4️⃣  隐式异常链 — __context__ 自动链接")
    print(SEP)

    def parse(data):
        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            # 没有使用 from，Python 自动设置 __context__
            raise ValueError("解析 JSON 失败")

    print("\n▶ 隐式链（Python 自动设置 __context__）:")
    try:
        parse("not json")
    except ValueError as e:
        print(f"  异常: {e}")
        ctx = e.__context__
        print(f"  __context__ = {type(ctx).__name__}: {ctx}")


# ═══════════════════════════════════════════════════════════════
# 5. 异常链的 __cause__ 与 __context__ 区别
# ═══════════════════════════════════════════════════════════════

def demo_chain_difference():
    """__cause__ vs __context__ 的区别"""
    print(SEP)
    print("5️⃣  __cause__ vs __context__ 对比")
    print(SEP)

    scenarios = [
        ("显式链 (raise ... from)", True, False),
        ("隐式链 (无 from)", False, False),
        ("抑制链 (raise ... from None)", False, True),
    ]

    for scenario_name, use_from, suppress in scenarios:
        print(f"\n▶ {scenario_name}:")

        try:
            try:
                raise RuntimeError("原始错误")
            except RuntimeError as e:
                if suppress:
                    raise ValueError("包装错误") from None
                elif use_from:
                    raise ValueError("包装错误") from e
                else:
                    raise ValueError("包装错误")
        except ValueError as e:
            print(f"  __cause__  = {e.__cause__}")
            print(f"  __context__ = {e.__context__}")
            print(f"  __suppress_context__ = {e.__suppress_context__}")


# ═══════════════════════════════════════════════════════════════
# 6. 多级异常链
# ═══════════════════════════════════════════════════════════════

class DBError(Exception): pass
class ServiceError(Exception): pass
class APIError(Exception): pass


def demo_multi_level_chain():
    """多级异常链 — 逐层包装"""
    print(SEP)
    print("6️⃣  多级异常链")
    print(SEP)

    def db_layer():
        raise DBError("数据库连接超时")

    def service_layer():
        try:
            db_layer()
        except DBError as e:
            raise ServiceError("服务层: 数据获取失败") from e

    def api_layer():
        try:
            service_layer()
        except ServiceError as e:
            raise APIError("API: 请求处理失败") from e

    print("\n▶ 三级异常链:")
    try:
        api_layer()
    except APIError as e:
        print(f"  Level 1 (API): {e}")
        print(f"  Level 2 (Service): {e.__cause__}")
        print(f"  Level 3 (DB): {e.__cause__.__cause__}")


# ═══════════════════════════════════════════════════════════════
# 7. 异常链模式在实际项目中的应用
# ═══════════════════════════════════════════════════════════════

class ConfigError(Exception): pass
class DatabaseError(Exception): pass

def demo_real_world_patterns():
    """实际项目中的异常链模式"""
    print(SEP)
    print("7️⃣  实际项目中的异常链模式")
    print(SEP)

    patterns = {
        "适配器模式": "将第三方库异常转换为项目内部异常",
        "分层架构": "每层将底层异常包装为层次语义",
        "重试机制": "将临时异常转换为业务可处理的重试异常",
        "错误聚合": "将多个操作异常聚合成一个事务异常",
    }
    for name, desc in patterns.items():
        print(f"  • {name}: {desc}")

    # 示例：数据库重试 + 异常链
    print("\n▶ 实际场景：数据库连接 + 重试失败")

    class RetryableDBError(Exception):
        pass

    class FinalDBError(Exception):
        pass

    attempt = 0

    def connect_db():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise RetryableDBError(f"连接尝试 {attempt} 失败")
        return "连接成功"

    try:
        for i in range(3):
            try:
                result = connect_db()
                print(f"  ✅ {result}")
                break
            except RetryableDBError as e:
                if i == 2:
                    raise FinalDBError("数据库连接失败，已重试 3 次") from e
                print(f"  🔄 重试... ({e})")
    except FinalDBError as e:
        print(f"  ❌ {e}")
        print(f"    最后一次底层错误: {e.__cause__}")


# ═══════════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════════

def main():
    print("🐍 Python 异常链与 raise 进阶用法")
    print()

    demo_bare_raise()
    demo_explicit_chaining()
    demo_suppress_chaining()
    demo_implicit_chaining()
    demo_chain_difference()
    demo_multi_level_chain()
    demo_real_world_patterns()

    print(SEP)
    print("✅ 所有演示完成！")
    print("📌 核心规则:")
    print("   裸 raise → 保留完整 traceback 传播")
    print("   raise X from Y → 建立因果关系")
    print("   raise X from None → 抑制底层细节")
    print("   无 from → Python 自动设置 __context__")


if __name__ == "__main__":
    main()
