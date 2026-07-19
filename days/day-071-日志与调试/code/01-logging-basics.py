"""
Day 071 — logging 模块基础
运行方式：python 01-logging-basics.py
"""
import logging


def main():
    # ========== 1. basicConfig 快速配置 ==========
    # 注意：basicConfig 只能调用一次！
    logging.basicConfig(
        level=logging.DEBUG,  # 最低级别
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 创建 logger
    logger = logging.getLogger(__name__)

    # ========== 2. 不同级别 ==========
    print("=" * 50)
    print("📝 不同日志级别：")
    print("=" * 50)

    logger.debug("🔧 这是调试信息 - 开发时使用")
    logger.info("ℹ️ 这是一般信息 - 确认程序运行正常")
    logger.warning("⚠️ 这是警告 - 潜在问题")
    logger.error("❌ 这是错误 - 某个功能失败")
    logger.critical("💥 这是严重错误 - 程序可能崩溃")

    # ========== 3. 格式化日志 ==========
    print("\n" + "=" * 50)
    print("📝 格式化日志：")
    print("=" * 50)

    user = "Alice"
    action = "登录"
    logger.info(f"用户 {user} {action}成功")  # f-string 方式
    logger.info("用户 %s %s成功", user, action)  # % 格式化（推荐！）

    # ========== 4. 记录异常 ==========
    print("\n" + "=" * 50)
    print("📝 记录异常信息：")
    print("=" * 50)

    try:
        result = 1 / 0
    except Exception as e:
        logger.error(f"数学运算错误: {e}")
        logger.error("数学运算错误", exc_info=True)  # 带完整堆栈

    # ========== 5. 多个 Logger ==========
    print("\n" + "=" * 50)
    print("📝 多个 Logger：")
    print("=" * 50)

    app_logger = logging.getLogger("my_app")
    db_logger = logging.getLogger("my_app.database")
    api_logger = logging.getLogger("my_app.api")

    app_logger.info("应用启动")
    db_logger.info("数据库连接成功")
    api_logger.info("API 服务器启动")


if __name__ == "__main__":
    main()
