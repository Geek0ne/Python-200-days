"""
Day 071 — 📝 生产级日志配置（完整实战项目）
功能：多 Handler、日志轮转、格式化、性能优化
运行方式：python 06-production-logging.py
"""
import logging
import logging.config
import logging.handlers
import os
from datetime import datetime


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
            "format": ("%(asctime)s [%(levelname)s] %(name)s:%(lineno)d "
                       "%(funcName)s() [%(process)d:%(thread)d] - %(message)s"),
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
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/app.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": "logs/error.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "timed_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "logs/timed.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
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
            "handlers": ["console", "file", "error_file", "timed_file"],
            "propagate": False,
        },
        "my_app.api": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },

    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


# ========== 自定义过滤器 ==========
class ContextFilter(logging.Filter):
    """添加上下文信息到日志"""

    def __init__(self):
        super().__init__()
        self.request_id = None
        self.user_id = None

    def filter(self, record):
        record.request_id = self.request_id or "N/A"
        record.user_id = self.user_id or "N/A"
        return True


# ========== 初始化 ==========
def setup_logging():
    """初始化日志系统"""
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)
    context_filter = ContextFilter()
    logger = logging.getLogger("my_app")
    logger.addFilter(context_filter)
    return context_filter


# ========== 业务服务 ==========
class OrderService:
    """订单服务"""

    def __init__(self):
        self.logger = logging.getLogger("my_app.order")

    def create_order(self, user_id: int, items: list) -> dict:
        self.logger.info(f"创建订单: user_id={user_id}, items={len(items)} 个")

        try:
            order_id = 1001
            total = sum(item["price"] * item["qty"] for item in items)
            self.logger.info(f"订单创建成功: order_id={order_id}, total={total}")
            return {"order_id": order_id, "total": total}
        except Exception as e:
            self.logger.error(f"订单创建失败: {e}", exc_info=True)
            raise


class UserService:
    """用户服务"""

    def __init__(self):
        self.logger = logging.getLogger("my_app.user")

    def login(self, username: str, password: str) -> bool:
        self.logger.info(f"用户登录尝试: {username}")

        if username == "admin" and password == "123456":
            self.logger.info(f"用户 {username} 登录成功")
            return True
        else:
            self.logger.warning(f"用户 {username} 登录失败: 密码错误")
            return False


# ========== 运行 ==========
if __name__ == "__main__":
    context_filter = setup_logging()
    logger = logging.getLogger("my_app")

    logger.info("=" * 50)
    logger.info("🚀 应用启动")
    logger.info("=" * 50)

    # 模拟请求上下文
    context_filter.request_id = "req-12345"
    context_filter.user_id = "user-001"

    # 用户服务
    user_service = UserService()
    user_service.login("admin", "123456")
    user_service.login("hacker", "wrong")

    # 订单服务
    order_service = OrderService()
    order_service.create_order(
        user_id=1,
        items=[
            {"name": "Python书", "price": 59.9, "qty": 1},
            {"name": "键盘", "price": 299, "qty": 1},
        ]
    )

    # 测试异常日志
    try:
        1 / 0
    except Exception:
        logger.error("数学运算错误", exc_info=True)

    logger.info("=" * 50)
    logger.info("🛑 应用关闭")
    logger.info("=" * 50)

    print("\n✅ 日志已写入 logs/ 目录")
