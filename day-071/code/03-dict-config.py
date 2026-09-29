"""
Day 071 — 字典配置日志系统
运行方式：python 03-dict-config.py
"""
import logging
import logging.config
import os


# ========== 日志配置字典 ==========
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d "
                      "%(funcName)s() - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "app.log",
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.FileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "error.log",
            "encoding": "utf-8",
        },
    },

    "loggers": {
        "": {  # 根 logger
            "level": "DEBUG",
            "handlers": ["console", "file", "error_file"],
        },
        "my_app": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}


def main():
    # 清理旧日志
    for f in ["app.log", "error.log"]:
        if os.path.exists(f):
            os.remove(f)

    # 应用配置
    logging.config.dictConfig(LOGGING_CONFIG)

    # 使用
    logger = logging.getLogger("my_app")
    logger.info("日志系统配置完成")
    logger.debug("详细调试信息")
    logger.error("错误信息")

    print("✅ 配置完成，检查 app.log 和 error.log")


if __name__ == "__main__":
    main()
