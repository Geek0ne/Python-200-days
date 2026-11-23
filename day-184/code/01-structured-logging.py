#!/usr/bin/env python3
"""
Day 184 · 示例 01 —— 结构化日志基础：从 f-string 拼字符串到 JSON Lines

为什么要有这个文件？
    运维平台的「日志」如果只是人读的一行字符串，机器就没法聚合、没法告警、没法画图。
    结构化的意思是：**每条日志本身就是一条可查询的数据**（JSON 对象 / key=value 对），
    时间、级别、服务名、请求 id、耗时都是独立字段，而不是塞在自然语言里的碎片。

本文件演示三件事：
    1. 人读格式 vs 机器读格式（JSON Lines）的真实输出对比；
    2. 用 logging.Formatter 把 stdlib logging 直接改成结构化输出（不用第三方库）；
    3. 异常日志也必须结构化 —— traceback 要作为独立字段保留，方便按错误聚合。

运行方式：
    python3 01-structured-logging.py               # 打印两种格式的真实输出
    python3 01-structured-logging.py --self-test   # 离线自证：不依赖任何外部服务

关键点（都是踩过坑才写的）：
    * JSON Lines（每行一个 JSON 对象）才能被 `tail -f` / 采集器按行增量读取；
      整份 JSON 数组做不到增量读取。
    * ensure_ascii=False 让中文日志可读，代价是字节数变大；
      日志量大时建议用 True（本文件用 False，方便你看）。
    * 时间必须带时区偏移，否则跨机器聚合时无法对齐。
"""

from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone

SERVICE = "ops-platform-api"
TZ = timezone.utc


class JsonLineFormatter(logging.Formatter):
    """把 LogRecord 渲染成一行 JSON —— 这就是「结构化日志」的核心实现。

    设计原理：
        logging 的 Formatter 只负责 format(record) -> str。
        我们不去动 logging 的内部状态，只替换渲染函数，
        于是所有 logging 的能力（handler、级别过滤、propagate）全部保留。
    """

    #: 业务字段通过 logger.info("msg", extra={...}) 传入，
    #: 但这些 key 不能和 LogRecord 自带的属性重名（否则 logging 会抛 KeyError）。
    RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, TZ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "service": SERVICE,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # 业务字段：extra={} 里那些不跟 LogRecord 冲突的键
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value

        # 异常：traceback 放进独立字段，别拼进 msg。
        # 这样「按错误类型聚合」只需 GROUP BY error_type，不用正则去抠字符串。
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["traceback"] = self.formatException(record.exc_info)

        # separators 去掉空格，一行更短；ensure_ascii=False 保留中文
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def build_logger(json_mode: bool = True, stream=sys.stdout) -> logging.Logger:
    """返回一个只挂一个 handler 的 logger（避免重复输出 —— 最常见的新手坑）。"""
    logger = logging.getLogger("demo")
    logger.handlers.clear()  # 重复 import / 多次调用时不清空就会打印两遍
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    handler = logging.StreamHandler(stream)
    if json_mode:
        handler.setFormatter(JsonLineFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
        )
    logger.addHandler(handler)
    return logger


def emit_sample(logger: logging.Logger) -> None:
    """打几条典型的平台日志：正常请求、慢请求、异常。"""
    start = time.perf_counter()

    logger.info(
        "request handled",
        extra={
            "request_id": "req-8f21",
            "method": "GET",
            "path": "/api/v1/hosts",
            "status": 200,
            "duration_ms": round((time.perf_counter() - start) * 1000, 3),
        },
    )
    logger.warning(
        "slow request",
        extra={"request_id": "req-8f22", "path": "/api/v1/metrics", "duration_ms": 812.4},
    )

    try:
        {}["missing_key"]
    except KeyError:
        logger.error(
            "handler crashed",
            exc_info=True,
            extra={"request_id": "req-8f23", "status": 500},
        )


def self_test() -> int:
    """离线自证：把 JSON 日志写到内存 StringIO，逐条解析并断言字段。"""
    import io

    buf = io.StringIO()
    logger = build_logger(json_mode=True, stream=buf)
    emit_sample(logger)

    lines = [line for line in buf.getvalue().splitlines() if line.strip()]
    assert len(lines) == 3, f"应输出 3 条日志，实际 {len(lines)}"

    events = [json.loads(line) for line in lines]
    for ev in events:
        assert {"ts", "level", "service", "msg"}.issubset(ev), ev
        assert datetime.fromisoformat(ev["ts"]).tzinfo is not None, ev["ts"]

    assert events[0]["path"] == "/api/v1/hosts"
    assert events[0]["status"] == 200
    assert events[1]["level"] == "WARNING"
    assert events[2]["error_type"] == "KeyError", events[2]
    assert "KeyError" in events[2]["traceback"]

    print("✅ self-test 通过：3 条结构化日志字段完整，异常类型可聚合")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()

    print("=== ① 人读格式（自然语言）—— 机器没法直接聚合 ===")
    human = build_logger(json_mode=False)
    emit_sample(human)
    print(
        "\n问题：status=200 和 duration_ms 只是长字符串里的一段，\n"
        "      想统计「P95 耗时」或「非 200 占比」只能上正则，慢且易错。\n"
    )

    print("=== ② 机器读格式（JSON Lines）—— 每行一个对象，可直接 jq / 入库 ===")
    machine = build_logger(json_mode=True)
    emit_sample(machine)
    print("\n提示：接管道验证一下 jq 能不能直接吃：")
    print("      python3 01-structured-logging.py 2>/dev/null | tail -3 | jq -c '.level,.msg'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
