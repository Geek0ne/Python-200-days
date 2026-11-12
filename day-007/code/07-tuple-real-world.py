#!/usr/bin/env python3
"""
07-tuple-real-world.py — Day 007 补充
元组实际应用案例集：网络协议、CSV解析、配置管理、数据校验

可直接运行：python3 07-tuple-real-world.py
"""

from collections import namedtuple
from typing import List, Tuple, Optional, NamedTuple
import csv
import io
import json
import re
from datetime import datetime


# ============================================================
# 案例 1：网络协议头解析
# ============================================================

def case_network_protocol():
    """元组在网络协议解析中的应用"""
    print("=" * 60)
    print("  案例 1: 网络协议头解析")
    print("=" * 60)

    # TCP/IP 使用固定长度的头部字段 — 元组天然适合
    # 模拟一个简单的自定义协议头
    # 格式：version(1) | type(1) | length(2) | flags(1) | checksum(2) | payload(n)

    PacketHeader = namedtuple("PacketHeader", [
        "version", "pkt_type", "length", "flags", "checksum"
    ])

    def parse_packet(raw: bytes) -> Tuple[PacketHeader, bytes]:
        """解析自定义协议包"""
        if len(raw) < 7:
            raise ValueError("数据包太短")

        header = PacketHeader(
            version=raw[0],
            pkt_type=raw[1],
            length=int.from_bytes(raw[2:4], "big"),
            flags=raw[4],
            checksum=int.from_bytes(raw[5:7], "big"),
        )
        payload = raw[7:7 + header.length] if header.length > 0 else b""
        return (header, payload)

    # 构造一个数据包
    raw_packet = bytes([
        0x01,  # version=1
        0x05,  # type=5 (DATA)
        0x00, 0x08,  # length=8
        0x00,  # flags
        0xAB, 0xCD,  # checksum
        0x48, 0x65, 0x6C, 0x6C, 0x6F, 0x21, 0x0A, 0x00,  # "Hello!\n\0"
    ])

    header, payload = parse_packet(raw_packet)
    print(f"\n  原始数据包: {raw_packet.hex()}")
    print(f"  解析结果:")
    print(f"    头部: v={header.version}, type={header.pkt_type}, "
          f"len={header.length}, flags={header.flags:08b}, chk={header.checksum:04x}")
    print(f"    载荷: {payload.decode('utf-8', errors='replace')!r}")

    # 元组的不可变性保证协议头不会被意外篡改
    # 后续处理中 header 是只读的
    print(f"\n  💡 协议头不可变保证：解析后的头部不能被下游修改，保证数据完整性")


# ============================================================
# 案例 2：CSV 数据解析
# ============================================================

def case_csv_parsing():
    """namedtuple 解析 CSV 数据"""
    print("\n" + "=" * 60)
    print("  案例 2: CSV 数据解析（namedtuple）")
    print("=" * 60)

    csv_data = """id,name,department,salary,years
1,Alice,Engineering,15000,5
2,Bob,Marketing,12000,3
3,Charlie,Engineering,18000,7
4,Diana,Sales,14000,4
5,Eve,Engineering,16000,6"""

    # 方法 1：手动定义 namedtuple
    Employee = namedtuple("Employee", ["id", "name", "department", "salary", "years"])

    employees = []
    reader = csv.DictReader(io.StringIO(csv_data))
    for row in reader:
        emp = Employee(
            id=int(row["id"]),
            name=row["name"],
            department=row["department"],
            salary=int(row["salary"]),
            years=int(row["years"]),
        )
        employees.append(emp)

    print(f"\n  解析 {len(employees)} 条记录:")
    for emp in employees:
        print(f"    {emp.id:<3} {emp.name:<10} {emp.department:<15} "
              f"¥{emp.salary:<6} {emp.years}年")

    # 数据分析 — 利用 namedtuple 的属性访问
    print(f"\n  数据分析:")
    avg_salary = sum(e.salary for e in employees) / len(employees)
    print(f"    平均薪资: ¥{avg_salary:.0f}")

    eng_salaries = [e.salary for e in employees if e.department == "Engineering"]
    if eng_salaries:
        avg_eng = sum(eng_salaries) / len(eng_salaries)
        print(f"    工程部平均薪资: ¥{avg_eng:.0f}")

    # 按部门分组
    dept_groups = {}
    for emp in employees:
        dept_groups.setdefault(emp.department, []).append(emp.name)
    print(f"    部门分组: {dept_groups}")


# ============================================================
# 案例 3：配置文件管理
# ============================================================

def case_config_management():
    """元组在配置管理中的应用"""
    print("\n" + "=" * 60)
    print("  案例 3: 配置管理（命名元组 + _replace）")
    print("=" * 60)

    # 多层嵌套配置
    class AppConfig(NamedTuple):
        """应用配置 — 使用 NamedTuple 获得不可变性"""
        app_name: str
        version: str
        debug: bool

    class DatabaseConfig(NamedTuple):
        host: str
        port: int
        database: str
        pool_size: int = 10

    class CacheConfig(NamedTuple):
        engine: str
        host: str
        port: int
        ttl: int = 300
        max_connections: int = 50

    class Config(NamedTuple):
        """完整配置 — namedtuple 组合"""
        app: AppConfig
        database: DatabaseConfig
        cache: CacheConfig

    # 默认配置
    default_config = Config(
        app=AppConfig("MyApp", "1.0.0", debug=False),
        database=DatabaseConfig("localhost", 5432, "myapp"),
        cache=CacheConfig("redis", "localhost", 6379),
    )

    print(f"\n  默认配置:")
    print(f"    App: {default_config.app}")
    print(f"    DB:  {default_config.database}")
    print(f"    Cache: {default_config.cache}")

    # 使用 _replace 创建变体（继承大部分配置）
    dev_config = default_config._replace(
        app=default_config.app._replace(debug=True),
        database=default_config.database._replace(
            database="myapp_dev"
        ),
    )

    print(f"\n  开发配置（部分覆盖）:")
    print(f"    App: {dev_config.app}")
    print(f"    DB:  {dev_config.database}")

    prod_config = default_config._replace(
        app=default_config.app._replace(debug=False),
        database=default_config.database._replace(
            host="prod-db.internal",
            pool_size=50,
        ),
        cache=default_config.cache._replace(
            host="redis-cluster.internal",
            max_connections=200,
        ),
    )

    print(f"\n  生产配置:")
    print(f"    App: {prod_config.app}")
    print(f"    DB:  {prod_config.database}")
    print(f"    Cache: {prod_config.cache}")

    # 配置导出
    def config_to_json(config: Config) -> str:
        """导出配置为 JSON（利用 _asdict）"""
        def convert(obj):
            if hasattr(obj, "_asdict"):
                return {k: convert(v) for k, v in obj._asdict().items()}
            return obj
        return json.dumps(convert(config), indent=2, ensure_ascii=False)

    print(f"\n  配置导出 JSON:")
    print(config_to_json(dev_config))

    print(f"\n  💡 namedtuple 作为配置的优势：")
    print(f"     - 不可变：运行时配置不能被意外修改")
    print(f"     - _replace：方便创建变体配置")
    print(f"     - _asdict：方便序列化")
    print(f"     - 类型注解：IDE 自动补全支持")


# ============================================================
# 案例 4：数据校验管道
# ============================================================

def case_data_validation():
    """元组在数据校验管道中的应用"""
    print("\n" + "=" * 60)
    print("  案例 4: 数据校验管道")
    print("=" * 60)

    # 校验规则：每个规则是一个可调用对象
    # 返回 (True, 清洗后值) 或 (False, 错误信息)
    ValidationRule = callable

    def not_empty(field_name: str) -> ValidationRule:
        def rule(value: str) -> Tuple[bool, str]:
            if not value or not value.strip():
                return (False, f"{field_name} 不能为空")
            return (True, value.strip())
        return rule

    def min_length(field_name: str, min_len: int) -> ValidationRule:
        def rule(value: str) -> Tuple[bool, str]:
            if len(value) < min_len:
                return (False, f"{field_name} 至少 {min_len} 个字符")
            return (True, value)
        return rule

    def is_email(field_name: str) -> ValidationRule:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        def rule(value: str) -> Tuple[bool, str]:
            if not re.match(pattern, value):
                return (False, f"{field_name} 格式无效")
            return (True, value)
        return rule

    def is_in_range(field_name: str, min_v: int, max_v: int) -> ValidationRule:
        def rule(value: str) -> Tuple[bool, str]:
            try:
                v = int(value)
                if v < min_v or v > max_v:
                    return (False, f"{field_name} 应在 {min_v}~{max_v} 之间")
                return (True, v)  # 返回转换后的值！
            except ValueError:
                return (False, f"{field_name} 必须为整数")
        return rule

    # 字段定义：字段名 + 规则列表
    FieldDef = namedtuple("FieldDef", ["name", "rules"])

    registration_fields = [
        FieldDef("username", [not_empty("用户名"), min_length("用户名", 3)]),
        FieldDef("email", [not_empty("邮箱"), is_email("邮箱")]),
        FieldDef("age", [not_empty("年龄"), is_in_range("年龄", 1, 150)]),
    ]

    def validate_form(data: dict, fields: List[FieldDef]) -> Tuple[bool, dict, List[str]]:
        """
        校验表单数据
        返回: (是否通过, 清洗后数据, 错误列表)
        """
        cleaned = {}
        errors = []

        for field in fields:
            value = data.get(field.name, "")
            for rule in field.rules:
                ok, result = rule(str(value))
                if not ok:
                    errors.append(result)
                    break
            else:
                # 所有规则通过
                cleaned[field.name] = result

        return (len(errors) == 0, cleaned, errors)

    # 测试
    test_cases = [
        {"username": "Alice", "email": "alice@example.com", "age": "25"},
        {"username": "Bo", "email": "alice@example", "age": "200"},
        {"username": "", "email": "", "age": "abc"},
    ]

    for i, data in enumerate(test_cases, 1):
        ok, cleaned, errors = validate_form(data, registration_fields)
        status = "✅ 通过" if ok else "❌ 拒绝"
        print(f"\n  测试 {i}: {data}")
        print(f"    结果: {status}")
        if errors:
            for err in errors:
                print(f"    - {err}")
        if cleaned:
            print(f"    清洗后: {cleaned}")


# ============================================================
# 主程序
# ============================================================

def main():
    case_network_protocol()
    case_csv_parsing()
    case_config_management()
    case_data_validation()

    print("\n" + "=" * 60)
    print("  ✅ 元组实际应用案例演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
