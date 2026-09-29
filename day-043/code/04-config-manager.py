"""
Day 43 - 04-config-manager.py
实战：配置管理系统

一个完整的、基于 dataclass 的配置管理系统，支持：
1. 多级配置来源（默认值 → 环境变量 → JSON 文件 → 命令行参数）
2. 配置验证（类型检查、范围检查、枚举检查）
3. 不可变配置保护（frozen=True）
4. 配置序列化（JSON 导出/导入）
5. 配置合并（多来源自动合并）

场景：一个 Web 服务应用的配置管理
"""

from dataclasses import dataclass, field, asdict, fields
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os
import sys


# =============================================================================
# 1. 配置模型定义
# =============================================================================
# 用 dataclass 定义分层配置结构

@dataclass
class DatabaseConfig:
    """数据库连接配置"""
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = field(default="", repr=False)       # 不显示密码
    database: str = "app_db"
    pool_size: int = 10
    max_connections: int = 100
    # 连接超时（秒），-1 表示不超时
    connect_timeout: int = field(default=30, metadata={"min": -1, "max": 300})
    ssl_enabled: bool = False

    def __post_init__(self) -> None:
        """验证数据库配置"""
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"端口号 {self.port} 不在有效范围 (1-65535)")
        if self.pool_size < 1:
            raise ValueError(f"连接池大小必须 >= 1，当前 {self.pool_size}")
        if self.connect_timeout < -1 or self.connect_timeout > 300:
            raise ValueError(f"超时时间必须在 -1 到 300 之间，当前 {self.connect_timeout}")


@dataclass
class RedisConfig:
    """Redis 缓存配置"""
    host: str = "localhost"
    port: int = 6379
    password: str = field(default="", repr=False)
    db: int = 0
    # 集群模式是否启用
    cluster_mode: bool = False
    # 缓存过期时间（秒）
    default_ttl: int = 3600

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"Redis 端口 {self.port} 无效")
        if self.db < 0 or self.db > 15:
            raise ValueError(f"Redis 数据库编号 {self.db} 超出范围 (0-15)")


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    file: Optional[str] = None
    max_size_mb: int = 100
    backup_count: int = 5

    VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def __post_init__(self) -> None:
        if self.level.upper() not in self.VALID_LEVELS:
            raise ValueError(
                f"日志级别 {self.level} 无效，有效值: {', '.join(sorted(self.VALID_LEVELS))}"
            )
        # 自动转为大写
        self.level = self.level.upper()


@dataclass
class ServerConfig:
    """Web 服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    debug: bool = False
    # 跨域配置
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    # 请求限流（次/分钟）
    rate_limit: int = 60

    # API 密钥（环境变量注入，从 __init__ 隐藏）
    api_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ValueError(f"服务端口 {self.port} 无效")
        if self.workers < 1:
            self.workers = 1  # 自动修正最小值


@dataclass(frozen=True)
class AppConfig:
    """
    应用主配置（不可变）
    组合了所有子配置，frozen=True 保证全局配置不被意外修改。
    """
    app_name: str = "MyApp"
    version: str = "1.0.0"
    environment: str = "development"  # development / testing / production

    # 子配置（嵌套 dataclass）
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    server: ServerConfig = field(default_factory=ServerConfig)

    # 特性开关
    features: Dict[str, bool] = field(default_factory=lambda: {
        "new_api": False,
        "cache_enabled": True,
        "metrics": True,
    })

    VALID_ENVIRONMENTS = {"development", "testing", "production"}

    def __post_init__(self) -> None:
        """验证主配置"""
        if self.environment not in self.VALID_ENVIRONMENTS:
            raise ValueError(
                f"环境 '{self.environment}' 无效，"
                f"有效值: {', '.join(self.VALID_ENVIRONMENTS)}"
            )


# =============================================================================
# 2. 配置加载器
# =============================================================================

class ConfigLoader:
    """
    配置加载器：按优先级合并多来源配置

    优先级（低 → 高）:
      默认值 → JSON 配置文件 → 环境变量 → 显式覆盖
    """

    # 环境变量前缀
    ENV_PREFIX = "APP_"

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

    def load(self, overrides: Optional[Dict[str, Any]] = None) -> AppConfig:
        """
        加载并合并配置

        Args:
            overrides: 最高优先级的显式覆盖配置（如命令行参数）

        Returns:
            最终的 AppConfig 实例
        """
        # 第1层：默认值（由 dataclass 的默认值提供）
        config_dict = {}  # 从空白开始，只存储覆盖项

        # 第2层：JSON 配置文件
        if self.config_path and Path(self.config_path).exists():
            file_config = self._load_json(self.config_path)
            self._deep_merge(config_dict, file_config)
            print(f"📁 从文件加载配置: {self.config_path}")

        # 第3层：环境变量
        env_config = self._load_env_vars()
        if env_config:
            self._deep_merge(config_dict, env_config)
            print(f"📋 从环境变量加载配置")

        # 第4层：显式覆盖（命令行参数等）
        if overrides:
            self._deep_merge(config_dict, overrides)
            print(f"⚙️ 应用显式覆盖配置")

        # 通过 config_dict 构建 AppConfig
        config = self._build_config(config_dict)
        return config

    def _load_json(self, path: str) -> Dict[str, Any]:
        """从 JSON 文件加载配置"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"⚠️ JSON 加载失败: {e}")
            return {}

    def _load_env_vars(self) -> Dict[str, Any]:
        """
        从环境变量加载配置

        环境变量命名规则：
          APP_DATABASE_HOST  → database.host
          APP_SERVER_PORT    → server.port
          APP_FEATURES_NEW_API → features.new_api
          APP_REDIS_PASSWORD → redis.password

        用双下划线 __ 表示嵌套层级。
        """
        result: Dict[str, Any] = {}

        for key, value in os.environ.items():
            if not key.startswith(self.ENV_PREFIX):
                continue

            # 去掉前缀
            path_str = key[len(self.ENV_PREFIX):]

            # 支持双下划线嵌套：APP_DATABASE__HOST → database.host
            parts = path_str.lower().split("__")

            # 尝试类型转换
            typed_value = self._convert_value(value)

            # 嵌入到嵌套字典
            current = result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = typed_value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        return result

    def _convert_value(self, value: str):
        """尝试将字符串自动转换为合适的类型"""
        # 布尔值
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # None
        if value.lower() in ("none", "null", ""):
            return None

        # 整数
        try:
            return int(value)
        except ValueError:
            pass

        # 浮点数
        try:
            return float(value)
        except ValueError:
            pass

        # 逗号分隔的列表
        if "," in value:
            return [item.strip() for item in value.split(",")]

        # 字符串
        return value

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """
        深度合并两个字典。
        override 中的值会覆盖 base 中的值（递归处理字典）。
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _build_config(self, config_dict: Dict) -> AppConfig:
        """
        从字典构建 AppConfig 实例。
        自动处理嵌套 dataclass 的构建。
        """
        # 顶层字段
        top_level = {}
        sub_configs = {
            "database": DatabaseConfig,
            "redis": RedisConfig,
            "logging": LoggingConfig,
            "server": ServerConfig,
        }

        for key, value in config_dict.items():
            if key in sub_configs and isinstance(value, dict):
                # 构建子配置对象
                sub_cls = sub_configs[key]
                # 只传递子配置类有的字段
                valid_fields = {f.name for f in fields(sub_cls)}
                filtered = {k: v for k, v in value.items() if k in valid_fields}
                top_level[key] = sub_cls(**filtered)
            else:
                top_level[key] = value

        return AppConfig(**top_level)


# =============================================================================
# 3. 使用示例
# =============================================================================

def demo_basic_usage() -> None:
    """基本使用：默认配置"""
    print("=" * 60)
    print("🎯 场景 1：使用默认配置")
    print("=" * 60)

    config = AppConfig()  # 全默认值
    print(f"应用: {config.app_name} v{config.version}")
    print(f"环境: {config.environment}")
    print(f"数据库: {config.database.host}:{config.database.port}/{config.database.database}")
    print(f"Redis: {config.redis.host}:{config.redis.port}/{config.redis.db}")
    print(f"服务器: {config.server.host}:{config.server.port}")
    print(f"日志级别: {config.logging.level}")
    print(f"特性开关: {config.features}")

    # frozen=True 防止修改
    try:
        config.app_name = "Hacked"
    except Exception as e:
        print(f"不可变保护: {type(e).__name__}")

    print()


def demo_json_config() -> None:
    """从 JSON 文件加载配置"""
    print("=" * 60)
    print("🎯 场景 2：从 JSON 文件加载配置")
    print("=" * 60)

    # 创建示例配置文件
    sample_config = {
        "app_name": "ProductionApp",
        "environment": "production",
        "database": {
            "host": "prod-db.example.com",
            "port": 5432,
            "username": "app_user",
            "password": "encrypted_password_123",
            "database": "prod_db",
            "pool_size": 20,
            "ssl_enabled": True,
        },
        "redis": {
            "host": "prod-redis.example.com",
            "port": 6379,
            "db": 1,
            "cluster_mode": True,
        },
        "logging": {
            "level": "WARNING",
            "file": "/var/log/app.log",
        },
        "server": {
            "workers": 8,
            "rate_limit": 1000,
        },
        "features": {
            "new_api": True,
            "metrics": True,
            "cache_enabled": True,
        },
    }

    config_path = "/tmp/app_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(sample_config, f, indent=2)
    print(f"已创建示例配置: {config_path}")

    # 加载
    loader = ConfigLoader(config_path=config_path)
    config = loader.load()

    print(f"应用: {config.app_name}")
    print(f"环境: {config.environment}")
    print(f"数据库: {config.database.username}@{config.database.host}:{config.database.port}")
    print(f"Redis 集群模式: {config.redis.cluster_mode}")
    print(f"日志级别: {config.logging.level}")
    print(f"工作进程数: {config.server.workers}")

    # 清理
    Path(config_path).unlink()

    print()


def demo_env_config() -> None:
    """从环境变量加载配置（模拟）"""
    print("=" * 60)
    print("🎯 场景 3：通过环境变量覆盖配置")
    print("=" * 60)

    # 模拟设置环境变量
    os.environ["APP_DATABASE__HOST"] = "env-db.example.com"
    os.environ["APP_DATABASE__PORT"] = "5432"
    os.environ["APP_DATABASE__POOL_SIZE"] = "50"
    os.environ["APP_SERVER__WORKERS"] = "16"
    os.environ["APP_SERVER__API_KEY"] = "sk-env-secret-xyz"
    os.environ["APP_FEATURES__NEW_API"] = "true"
    os.environ["APP_ENVIRONMENT"] = "testing"

    loader = ConfigLoader()
    config = loader.load()

    print(f"环境: {config.environment}")
    print(f"数据库: {config.database.host}:{config.database.port} (池大小: {config.database.pool_size})")
    print(f"工作进程: {config.server.workers}")
    print(f"环境变量 api_key: {'✅ 已注入' if config.server.api_key else '❌ 为空'}")
    print(f"新 API 功能: {'✅ 启用' if config.features.get('new_api') else '❌ 禁用'}")

    # 清理环境变量（避免影响其他测试）
    for key in list(os.environ.keys()):
        if key.startswith("APP_"):
            del os.environ[key]

    print()


def demo_export() -> None:
    """配置序列化与导出"""
    print("=" * 60)
    print("🎯 场景 4：配置序列化（导出为 JSON）")
    print("=" * 60)

    config = AppConfig(
        app_name="TestApp",
        environment="development",
        server=ServerConfig(host="127.0.0.1", port=9000, debug=True),
        features={"new_api": True, "beta": True},
    )

    # 导出为字典（自动处理嵌套 dataclass）
    config_dict = asdict(config)
    print("导出为字典:")
    print(json.dumps(config_dict, indent=2, ensure_ascii=False)[:500])

    print()


def demo_full_workflow() -> None:
    """完整工作流：配置加载 → 验证 → 使用"""
    print("=" * 60)
    print("🎯 场景 5：完整配置工作流")
    print("=" * 60)

    # 1. 定义多层配置
    # 使用正确的类型构造子配置
    loader_config = AppConfig(
        app_name="ECommerceAPI",
        environment="production",
        database=DatabaseConfig(
            host="localhost",
            port=3306,
            username="ecom_user",
            password="secure_pass_123",
            database="ecommerce",
            pool_size=15,
            connect_timeout=60,
        ),
        logging=LoggingConfig(
            level="INFO",
            file="/var/log/ecom.log",
        ),
        server=ServerConfig(
            workers=4,
            rate_limit=200,
        ),
        features={
            "new_recommendation": True,
            "payment_v2": True,
        },
    )

    # 2. config = loader_config（已经构建好了）
    config = loader_config

    # 3. 使用配置

    print(f"🚀 启动 {config.app_name} v{config.version}")
    print(f"📦 环境: {config.environment}")
    print(f"🔌 数据库: {config.database.host}:{config.database.port}")
    print(f"⚡ 工作进程: {config.server.workers}")

    # 特性检查
    if config.features.get("payment_v2"):
        print("💳 支付系统 v2 已启用")
    if config.features.get("new_recommendation"):
        print("🎯 新推荐算法已启用")

    print()

    # 4. 敏感信息保护（repr=False）
    print("配置 repr（密码/API 密钥已隐藏）：")
    print(f"  数据库: {config.database!r}")
    print(f"  服务器: {config.server!r}")

    print()

    # 5. 验证错误演示（直接构造错误的配置）
    print("配置验证演示：")
    try:
        AppConfig(
            app_name="BadApp",
            environment="development",
            database=DatabaseConfig(
                host="localhost", port=99999,  # 无效端口
                username="user",
            ),
        )
    except ValueError as e:
        print(f"  ✅ 端口验证生效: {e}")

    try:
        AppConfig(
            app_name="BadApp2",
            environment="development",
            logging=LoggingConfig(level="VERBOSE"),  # 无效日志级别
        )
    except ValueError as e:
        print(f"  ✅ 日志级别验证生效: {e}")

    print()


# =============================================================================
# 入口
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("📋 Day 43 实战：配置管理系统")
    print("基于 dataclass 构建的多来源配置管理")
    print("=" * 60)
    print()

    demo_basic_usage()
    demo_json_config()
    demo_env_config()
    demo_export()
    demo_full_workflow()

    print("=" * 60)
    print("🎉 配置管理系统实战演示完成！")
    print("=" * 60)
