"""
Day 071 — Logger、Handler、Formatter 详解
运行方式：python 02-logging-components.py
"""
import logging


def main():
    # ========== 创建 Logger ==========
    logger = logging.getLogger("my_app")
    logger.setLevel(logging.DEBUG)

    # 清除已有的 handler（避免重复输出）
    logger.handlers.clear()

    # ========== 创建 Formatter ==========
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    simple_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s"
    )

    # ========== 创建 Handler ==========
    # 控制台 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # 文件 Handler
    file_handler = logging.FileHandler("app.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)

    # 错误文件 Handler
    error_handler = logging.FileHandler("error.log", encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # ========== 组装 ==========
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    # ========== 使用 ==========
    print("=" * 50)
    print("📝 日志输出测试：")
    print("=" * 50)

    logger.debug("详细调试信息 - 只写入 app.log")
    logger.info("一般信息 - 写入控制台 + app.log")
    logger.warning("警告信息 - 写入控制台 + app.log")
    logger.error("错误信息 - 写入控制台 + app.log + error.log")
    logger.critical("严重错误 - 写入控制台 + app.log + error.log")

    print("\n✅ 日志已写入 app.log 和 error.log")


if __name__ == "__main__":
    main()
