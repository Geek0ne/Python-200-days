#!/usr/bin/env python3
"""
Day 195 · 04 结构化日志与告警收敛

运行：
    python3 04-logging-alert.py               # 演示
    python3 04-logging-alert.py --self-test   # 离线自检

三个真实痛点：
1. 日志里打了 token / 密码，被采集到 ELK，等于把钥匙贴在公告栏；
2. 故障时 1000 条同样的告警，值班的人 5 分钟后开始全部已读；
3. 只有 message 没有字段，排查时只能 grep 猜，没法按 status/route 聚合。
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_lib import AlertSink, JsonLogger, redact  # noqa: E402


def section(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def demo_structured_log() -> None:
    section("演示 1：一行 JSON，字段稳定，密钥自动脱敏")
    stream = io.StringIO()
    logger = JsonLogger("payment-api", stream=stream).bind(
        request_id="req-7f3a", user_id="u-42", route="/api/v1/pay",
    )
    logger.info("request_started", method="POST", ip="10.0.0.9")
    logger.info("credentials_loaded",
                password="hunter2", api_key="sk-live-xxx", nested={"token": "abc"})
    logger.error("upstream_failed", status=503, attempt=2, retry_in_ms=400)

    for line in stream.getvalue().splitlines():
        print("  " + line)

    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert records[0]["request_id"] == "req-7f3a"
    assert records[1]["password"] == "***"
    assert records[1]["nested"]["token"] == "***"
    print("\n  为什么这样打日志：")
    print("  - 固定 event 名 + 结构化字段 → Loki/ES 可直接按 status 聚合；")
    print("  - request_id 贯穿整条链路 → 一次请求的所有日志能串起来；")
    print("  - 脱敏放在 logger 内部而不是调用方 → 没人会忘记。")


def demo_alert_storm() -> None:
    section("演示 2：1000 次数据库失败，应该发几条告警？")
    now = [0.0]
    sink = AlertSink(cooldown=60, clock=lambda: now[0])
    stream = io.StringIO()
    logger = JsonLogger("payment-api", level="ERROR", stream=stream)

    for index in range(1000):
        now[0] = index * 0.6           # 10 分钟内均匀发生
        logger.error("db_query_failed", error="connection reset", shard=index % 4)
        sink.emit("db_query_failed", "critical", "数据库查询连续失败")

    print(f"  原始失败事件: 1000 条")
    print(f"  实际发出告警: {len(sink.sent)} 条（冷却窗口 60s）")
    for alert in sink.sent:
        print(f"    - {alert.severity:<9} {alert.key:<16} "
              f"抑制了 {alert.suppressed} 条重复")

    now[0] += 1
    sink.reset("db_query_failed")      # 故障恢复
    recovered = sink.emit("db_query_failed", "critical", "数据库再次失败")
    print(f"  恢复后立刻复发 → 立刻告警: {recovered is not None}")
    print("\n  告警设计三件事：")
    print("  1. 按 key 聚合，冷却窗口内只发一条汇总；")
    print("  2. 恢复时 reset，否则下一次故障会被上一次的冷却吞掉；")
    print("  3. 汇总里带 suppressed 计数 —— 让人知道规模，而不是以为只错了一次。")


def demo_severity_routing() -> None:
    section("演示 3：不是所有 ERROR 都值得半夜打电话")
    routes = {
        "critical": "电话 + 企业微信 + 工单",
        "error": "企业微信 + 工单",
        "warning": "工单",
        "info": "仅日志",
    }
    events = [
        ("payment_gateway_down", "critical"),
        ("db_slow_query", "warning"),
        ("cache_miss_ratio_high", "error"),
        ("user_login", "info"),
    ]
    print(f"  {'事件':<28}{'级别':<10}去向")
    print("  " + "-" * 60)
    for event, severity in events:
        print(f"  {event:<28}{severity:<10}{routes[severity]}")
    print("\n  分级不是为了好看：是为了让 on-call 在 3 秒内判断要不要起床。")


def self_test() -> None:
    stream = io.StringIO()
    logger = JsonLogger("t", stream=stream).bind(trace="abc")
    logger.info("hello", password="x", value=1)
    record = json.loads(stream.getvalue().strip())
    assert record["trace"] == "abc" and record["password"] == "***" and record["value"] == 1
    assert redact({"Authorization": "Bearer x"}) == {"Authorization": "***"}

    now = [0.0]
    sink = AlertSink(cooldown=10, clock=lambda: now[0])
    assert sink.emit("k", "error", "m") is not None
    for _ in range(5):
        assert sink.emit("k", "error", "m") is None
    now[0] = 10.0
    second = sink.emit("k", "error", "m")
    assert second is not None and second.suppressed == 5
    print("✅ 04 self-test passed")


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return
    demo_structured_log()
    demo_alert_storm()
    demo_severity_routing()


if __name__ == "__main__":
    main()
