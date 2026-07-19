"""
Day 071 — 日志轮转示例
运行方式：python 04-log-rotation.py
"""
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os


def main():
    # ========== 按大小轮转 ==========
    print("=" * 50)
    print("📝 按大小轮转日志")
    print("=" * 50)

    # 每个文件最大 1KB（演示用），保留 3 个备份
    size_handler = RotatingFileHandler(
        "size_rotate.log",
        maxBytes=1024,  # 1KB
        backupCount=3,
        encoding="utf-8"
    )
    size_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))

    size_logger = logging.getLogger("size_rotate")
    size_logger.setLevel(logging.DEBUG)
    size_logger.addHandler(size_handler)

    # 写入大量日志，触发轮转
    for i in range(100):
        size_logger.info(f"这是第 {i} 条日志消息，用于测试日志轮转功能")

    # 查看生成的文件
    log_files = [f for f in os.listdir(".") if f.startswith("size_rotate")]
    print(f"生成的日志文件: {sorted(log_files)}")

    # ========== 按时间轮转 ==========
    print("\n" + "=" * 50)
    print("📝 按时间轮转日志")
    print("=" * 50)

    time_handler = TimedRotatingFileHandler(
        "time_rotate.log",
        when="S",  # 每秒轮转（演示用）
        interval=10,  # 每 10 秒
        backupCount=5,
        encoding="utf-8"
    )
    time_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s"
    ))

    time_logger = logging.getLogger("time_rotate")
    time_logger.setLevel(logging.DEBUG)
    time_logger.addHandler(time_handler)

    # 写入日志
    for i in range(5):
        time_logger.info(f"时间轮转日志 {i}")

    print("✅ 日志轮转示例完成")


if __name__ == "__main__":
    main()
