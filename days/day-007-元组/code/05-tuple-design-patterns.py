#!/usr/bin/env python3
"""
05-tuple-design-patterns.py — Day 007 补充
元组实战设计模式：常量配置、状态机、依赖注入、数据管道

可直接运行：python3 05-tuple-design-patterns.py
"""

from collections import namedtuple
from typing import Tuple, List, Optional, NamedTuple
from enum import Enum
import re


# ============================================================
# 模式 1：元组作为常量配置
# ============================================================

def pattern_constants():
    """元组作为不可变常量集合"""
    print("=" * 60)
    print("  模式 1: 元组作为常量配置")
    print("=" * 60)

    # 颜色常量（命名元组）
    RGB = namedtuple("RGB", ["r", "g", "b"])

    class Colors:
        RED = RGB(255, 0, 0)
        GREEN = RGB(0, 255, 0)
        BLUE = RGB(0, 0, 255)
        WHITE = RGB(255, 255, 255)
        BLACK = RGB(0, 0, 0)
        YELLOW = RGB(255, 255, 0)

    print(f"\n  预定义颜色:")
    for name in dir(Colors):
        if not name.startswith("_"):
            color = getattr(Colors, name)
            print(f"    {name:<8} = RGB({color.r:3d}, {color.g:3d}, {color.b:3d})")

    # HTTP 状态码常量
    class HTTPStatus:
        OK = (200, "OK")
        CREATED = (201, "Created")
        BAD_REQUEST = (400, "Bad Request")
        UNAUTHORIZED = (401, "Unauthorized")
        FORBIDDEN = (403, "Forbidden")
        NOT_FOUND = (404, "Not Found")
        SERVER_ERROR = (500, "Internal Server Error")

    print(f"\n  HTTP 状态码:")
    for name in dir(HTTPStatus):
        if not name.startswith("_"):
            code, msg = getattr(HTTPStatus, name)
            print(f"    {name:<15} = {code} {msg}")


# ============================================================
# 模式 2：元组作为函数选项/配置
# ============================================================

def pattern_function_options():
    """用元组作为函数选项和配置参数"""
    print("\n" + "=" * 60)
    print("  模式 2: 元组作为函数选项")
    print("=" * 60)

    # 数据库连接配置
    DBConfig = namedtuple("DBConfig", ["host", "port", "user", "password", "database"])

    # 用元组传配置——不可变，安全
    def connect_db(config: DBConfig) -> str:
        """模拟数据库连接"""
        # 元组不可变保证配置在连接过程中不会被意外修改
        return f"已连接: {config.user}@{config.host}:{config.port}/{config.database}"

    dev_config = DBConfig("localhost", 5432, "admin", "secret", "myapp_dev")
    print(f"\n  数据库配置:")
    print(f"    {connect_db(dev_config)}")

    # 使用 _replace 创建变体
    prod_config = dev_config._replace(
        host="prod-db.example.com",
        database="myapp_prod"
    )
    print(f"    {connect_db(prod_config)}")

    # 分页参数
    Pagination = namedtuple("Pagination", ["page", "size", "sort_by", "order"])

    def query_users(pagination: Pagination) -> dict:
        """模拟分页查询"""
        return {
            "page": pagination.page,
            "size": pagination.size,
            "sort": f"{pagination.sort_by} {pagination.order}",
            "offset": (pagination.page - 1) * pagination.size,
        }

    p = Pagination(1, 20, "created_at", "DESC")
    print(f"\n  分页查询:")
    print(f"    {query_users(p)}")


# ============================================================
# 模式 3：元组作为状态机
# ============================================================

def pattern_state_machine():
    """用元组实现简单的状态机"""
    print("\n" + "=" * 60)
    print("  模式 3: 元组作为状态机")
    print("=" * 60)

    # 状态转移表：((current_state, action), next_state)
    # 使用元组作为 "状态 × 动作" 的键
    transitions = {
        ("idle", "start"): "running",
        ("running", "pause"): "paused",
        ("running", "stop"): "idle",
        ("paused", "resume"): "running",
        ("paused", "stop"): "idle",
        ("idle", "reset"): "idle",
    }

    class SimpleStateMachine:
        def __init__(self, initial_state="idle"):
            self._state = initial_state
            self._history = [(initial_state, "__init__", initial_state)]

        def transition(self, action: str) -> str:
            key = (self._state, action)
            if key not in transitions:
                raise ValueError(
                    f"非法转移: 状态={self._state}, 动作={action}"
                )
            old_state = self._state
            self._state = transitions[key]
            self._history.append((old_state, action, self._state))
            return self._state

        @property
        def state(self):
            return self._state

        @property
        def history(self):
            return self._history

    sm = SimpleStateMachine("idle")
    print(f"\n  初始状态: {sm.state}")

    for action in ["start", "pause", "resume", "stop", "start", "stop"]:
        try:
            new_state = sm.transition(action)
            print(f"    {action:8} → {new_state}")
        except ValueError as e:
            print(f"    {action:8} → ❌ {e}")

    print(f"\n  完整历史:")
    for old, action, new in sm.history:
        actor = "__init__" if action == "__init__" else action
        print(f"    {old:8} ─[{actor:8}]→ {new}")


# ============================================================
# 模式 4：元组作为轻量级依赖注入
# ============================================================

def pattern_dependency_injection():
    """元组在依赖注入模式中的应用"""
    print("\n" + "=" * 60)
    print("  模式 4: 元组作为依赖注入容器")
    print("=" * 60)

    # 用 namedtuple 作为 DI 容器
    class Services(NamedTuple):
        db: callable
        cache: callable
        logger: callable

    # 模拟的服务实现
    def create_db_service(name: str):
        def query(sql: str) -> list:
            return [f"[{name}] 执行: {sql}"]
        return query

    def create_cache_service(ttl: int = 300):
        def get(key: str) -> Optional[str]:
            return f"[缓存 TTL={ttl}s] 获取 {key}"
        return get

    def create_logger(level: str = "INFO"):
        def log(msg: str):
            print(f"  [{level}] {msg}")
        return log

    # 创建不同的服务组合
    dev_services = Services(
        db=create_db_service("开发数据库"),
        cache=create_cache_service(30),
        logger=create_logger("DEBUG"),
    )

    prod_services = dev_services._replace(
        db=create_db_service("生产数据库"),
        cache=create_cache_service(600),
        logger=create_logger("INFO"),
    )

    print(f"\n  Dev 环境:")
    dev_services.logger("启动开发环境")
    print(f"    DB: {dev_services.db('SELECT 1')}")
    print(f"    Cache: {dev_services.cache('user_1')}")

    print(f"\n  Prod 环境（替换依赖）:")
    prod_services.logger("启动生产环境")
    print(f"    DB: {prod_services.db('SELECT 1')}")
    print(f"    Cache: {prod_services.cache('user_1')}")


# ============================================================
# 模式 5：元组作为 ETL 数据管道
# ============================================================

def pattern_data_pipeline():
    """元组在数据处理管道中的应用"""
    print("\n" + "=" * 60)
    print("  模式 5: 元组作为 ETL 数据管道")
    print("=" * 60)

    # 数据记录用 namedtuple — 不可变保障数据完整性
    RawRecord = namedtuple("RawRecord", ["id", "name", "email", "age_str"])
    CleanRecord = namedtuple("CleanRecord", ["id", "name", "email", "age", "email_valid"])

    raw_data = [
        RawRecord(1, "Alice", "alice@example.com", "25"),
        RawRecord(2, "Bob", "bob@example", "30"),          # 无效邮箱
        RawRecord(3, "Charlie", "charlie@example.com", "not_a_number"),  # 无效年龄
        RawRecord(4, "", "", "28"),                        # 缺失数据
    ]

    def validate_email(email: str) -> Tuple[str, bool]:
        """返回 (清洗后email, 是否有效)"""
        email = email.strip().lower()
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        valid = bool(re.match(pattern, email)) and len(email) > 0
        return (email, valid)

    def parse_age(age_str: str) -> Tuple[int, bool]:
        """尝试解析年龄"""
        age_str = age_str.strip()
        if not age_str:
            return (0, False)
        try:
            age = int(age_str)
            return (age, 0 < age < 150)
        except ValueError:
            return (0, False)

    def clean_record(raw: RawRecord) -> CleanRecord:
        """清洗一条记录 — 返回不可变的 CleanRecord"""
        name = raw.name.strip() if raw.name else "UNKNOWN"
        (email, email_valid) = validate_email(raw.email)
        (age, age_valid) = parse_age(raw.age_str)
        return CleanRecord(
            id=raw.id,
            name=name if name else "UNKNOWN",
            email=email,
            age=age if age_valid else 0,
            email_valid=email_valid,
        )

    print(f"\n  原始数据 → 清洗结果:")
    print(f"  {'ID':<4} {'Name':<10} {'Email':<25} {'Age':<5} {'Valid':<6}")
    print(f"  {'-' * 50}")

    for raw in raw_data:
        clean = clean_record(raw)
        valid_mark = "✅" if clean.email_valid else "❌"
        print(f"  {clean.id:<4} {clean.name:<10} {clean.email:<25} {clean.age:<5} {valid_mark}")

    print(f"\n  💡 namedtuple 不可变保证：清洗后的数据不会被下游意外修改！")


# ============================================================
# 主程序
# ============================================================

def main():
    from typing import NamedTuple
    pattern_constants()
    pattern_function_options()
    pattern_state_machine()
    pattern_dependency_injection()
    pattern_data_pipeline()

    print("\n" + "=" * 60)
    print("  ✅ 元组设计模式演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
