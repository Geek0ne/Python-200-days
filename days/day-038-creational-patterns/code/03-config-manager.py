"""
Day 038 — 创建型设计模式：实战案例
====================================

实战：配置管理器 — 综合运用单例 + 工厂 + 建造者模式

系统设计：
- 单例模式：ConfigManager 全局唯一
- 工厂模式：ConfigFactory 从不同来源创建配置
- 建造者模式：ConfigBuilder 链式构建配置
- 观察者模式：配置变更通知
"""

import json
import os
import threading
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime


# ═══════════════════════════════════════════════════
# 1. 配置管理器（单例模式）
# ═══════════════════════════════════════════════════

class ConfigManager:
    """
    配置管理器 — 单例模式

    使用 __new__ 确保全局只有一个实例
    使用 _initialized 标志确保 __init__ 只执行一次
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}
        self._listeners: List[Callable] = []
        self._history: List[Dict] = []
        self._readonly_keys: set = set()
        self._lock = threading.Lock()
        self._frozen = False
        self._initialized = True

    # ── 基本操作 ──

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的键"""
        with self._lock:
            keys = key.split('.')
            value = self._config
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return default
                if value is None:
                    return default
            return value

    def set(self, key: str, value: Any) -> 'ConfigManager':
        """设置配置值，支持点号分隔"""
        with self._lock:
            if self._frozen:
                raise RuntimeError("配置已冻结，无法修改")

            # 检查只读键
            if key in self._readonly_keys:
                raise ValueError(f"键 '{key}' 是只读的")

            # 解析并设置
            keys = key.split('.')
            config = self._config
            for k in keys[:-1]:
                if k not in config or not isinstance(config[k], dict):
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value

            # 记录变更
            self._history.append({
                "key": key,
                "value": value,
                "timestamp": datetime.now().isoformat(),
            })

            self._notify(key, value)
            return self  # 链式调用

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self._lock:
            return self._deep_copy(self._config)

    def has(self, key: str) -> bool:
        """检查键是否存在"""
        return self.get(key, _SENTINEL) is not _SENTINEL

    # ── 批量操作 ──

    def load_dict(self, data: Dict[str, Any],
                  prefix: str = "") -> 'ConfigManager':
        """加载字典"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self.load_dict(value, full_key)
            else:
                self.set(full_key, value)
        return self

    def load_json(self, json_str: str) -> 'ConfigManager':
        """从 JSON 字符串加载"""
        return self.load_dict(json.loads(json_str))

    def update(self, other: 'ConfigManager') -> 'ConfigManager':
        """从另一个配置管理器更新"""
        other_dict = other.get_all()
        return self.load_dict(other_dict)

    # ── 保护机制 ──

    def freeze(self) -> 'ConfigManager':
        """冻结配置，禁止修改"""
        self._frozen = True
        return self

    def unfreeze(self) -> 'ConfigManager':
        """解冻配置"""
        self._frozen = False
        return self

    def make_readonly(self, *keys: str) -> 'ConfigManager':
        """将指定键设为只读"""
        self._readonly_keys.update(keys)
        return self

    # ── 监听器 ──

    def on_change(self, callback: Callable[[str, Any], None]) -> 'ConfigManager':
        """注册变更监听器"""
        self._listeners.append(callback)
        return self

    def _notify(self, key: str, value: Any):
        for listener in self._listeners:
            try:
                listener(key, value)
            except Exception as e:
                print(f"  ⚠️ 监听器错误: {e}")

    # ── 历史与回滚 ──

    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取最近变更历史"""
        return self._history[-limit:]

    def rollback(self, steps: int = 1) -> bool:
        """回滚最近的变更"""
        with self._lock:
            if steps > len(self._history):
                return False
            for _ in range(steps):
                entry = self._history.pop()
                key = entry["key"]
                # 这里简化处理，实际上需要保存旧值
                self._notify(key, f"<rollback>")
            return True

    # ── 导入/导出 ──

    def to_json(self, indent: int = 2) -> str:
        """导出为 JSON"""
        return json.dumps(self._config, ensure_ascii=False, indent=indent)

    def to_env_dict(self, prefix: str = "APP_") -> Dict[str, str]:
        """导出为环境变量格式"""
        result = {}

        def _flatten(data: Dict, parent_key: str = ""):
            for key, value in data.items():
                full_key = f"{parent_key}{key.upper()}" if parent_key else key.upper()
                full_key = full_key.replace('.', '_')
                if isinstance(value, dict):
                    _flatten(value, f"{full_key}_")
                else:
                    result[f"{prefix}{full_key}"] = str(value)

        _flatten(self._config)
        return result

    # ── 辅助 ──

    def _deep_copy(self, obj):
        import copy
        return copy.deepcopy(obj)

    @property
    def stats(self) -> Dict:
        return {
            "total_keys": self._count_keys(self._config),
            "last_modified": self._history[-1]["timestamp"]
            if self._history else None,
            "total_changes": len(self._history),
            "frozen": self._frozen,
            "readonly_keys": list(self._readonly_keys),
        }

    def _count_keys(self, d: dict, prefix: str = "") -> int:
        count = 0
        for k, v in d.items():
            full = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                count += self._count_keys(v, full)
            else:
                count += 1
        return count

    def __repr__(self) -> str:
        keys = self._count_keys(self._config)
        return f"ConfigManager(keys={keys}, frozen={self._frozen})"


_SENTINEL = object()


# ═══════════════════════════════════════════════════
# 2. 配置工厂（工厂模式 + 抽象工厂）
# ═══════════════════════════════════════════════════

class ConfigFactory:
    """
    配置工厂 — 从不同来源创建配置

    支持 JSON 文件、Python 字典、环境变量、YAML（扩展）
    """

    @staticmethod
    def from_json_file(filepath: str) -> ConfigManager:
        """从 JSON 文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return ConfigFactory.from_json_str(f.read())

    @staticmethod
    def from_json_str(json_str: str) -> ConfigManager:
        """从 JSON 字符串加载"""
        config = ConfigManager()
        config.load_json(json_str)
        return config

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ConfigManager:
        """从字典加载"""
        config = ConfigManager()
        config.load_dict(data)
        return config

    @staticmethod
    def from_env(prefix: str = "APP_") -> ConfigManager:
        """从环境变量加载"""
        config = ConfigManager()
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # APP_DATABASE_HOST → database.host
                config_key = key[len(prefix):].lower().replace('_', '.')
                config.set(config_key, value)
        return config

    @staticmethod
    def from_defaults() -> ConfigManager:
        """从默认配置加载"""
        return ConfigFactory.from_dict({
            "app": {
                "name": "MyApp",
                "version": "1.0.0",
                "debug": False,
                "port": 8080,
            },
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "app",
                "user": "admin",
                "password": "",
            },
            "redis": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "app.log",
            },
        })


# ═══════════════════════════════════════════════════
# 3. 配置建造者（建造者模式）
# ═══════════════════════════════════════════════════

class ConfigBuilder:
    """
    配置建造者 — 链式构建复杂配置

    使用建造者模式的好处：
    - 可以按任意顺序设置配置
    - 可以设置默认值
    - 链式调用清晰明了
    - 可以创建预定义的配置模板
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {}

    def set(self, key: str, value: Any,
            description: str = "") -> 'ConfigBuilder':
        """设置一个配置项"""
        keys = key.split('.')
        current = self._data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

        if description:
            self._metadata[key] = {"description": description}
        return self

    # ── 预定义配置模板 ──

    def set_database(self, host: str = "localhost",
                     port: int = 5432,
                     name: str = "app",
                     user: str = "admin",
                     password: str = "") -> 'ConfigBuilder':
        """配置数据库"""
        return self \
            .set("database.host", host, "数据库主机") \
            .set("database.port", port, "数据库端口") \
            .set("database.name", name, "数据库名") \
            .set("database.user", user, "数据库用户") \
            .set("database.password", password, "数据库密码")

    def set_redis(self, host: str = "localhost",
                  port: int = 6379,
                  db: int = 0,
                  password: str = "") -> 'ConfigBuilder':
        """配置 Redis"""
        return self \
            .set("redis.host", host, "Redis 主机") \
            .set("redis.port", port, "Redis 端口") \
            .set("redis.db", db, "Redis 数据库编号") \
            .set("redis.password", password, "Redis 密码")

    def set_app(self, name: str = "App",
                version: str = "1.0.0",
                debug: bool = False,
                port: int = 8080) -> 'ConfigBuilder':
        """配置应用"""
        return self \
            .set("app.name", name, "应用名称") \
            .set("app.version", version, "应用版本") \
            .set("app.debug", debug, "调试模式") \
            .set("app.port", port, "服务端口")

    def set_logging(self, level: str = "INFO",
                    file: str = "app.log") -> 'ConfigBuilder':
        """配置日志"""
        return self \
            .set("logging.level", level, "日志级别") \
            .set("logging.file", file, "日志文件")

    def set_email(self, host: str = "smtp.example.com",
                  port: int = 587,
                  user: str = "",
                  password: str = "") -> 'ConfigBuilder':
        """配置邮件"""
        return self \
            .set("email.host", host, "SMTP 主机") \
            .set("email.port", port, "SMTP 端口") \
            .set("email.user", user, "邮箱用户") \
            .set("email.password", password, "邮箱密码")

    # ── 构建 ──

    def build(self) -> ConfigManager:
        """构建配置管理器"""
        config = ConfigManager()
        config.load_dict(self._data)
        return config

    def build_and_freeze(self) -> ConfigManager:
        """构建并冻结"""
        config = self.build()
        config.freeze()
        return config


# ═══════════════════════════════════════════════════
# 4. 演示
# ═══════════════════════════════════════════════════

def demo():
    print("=" * 60)
    print("⚙️  配置管理器 — 综合设计模式演示")
    print("=" * 60)

    # ── 使用 Builder 构建配置 ──
    print("\n📦 使用 Builder 构建配置:")
    config = ConfigBuilder() \
        .set_app(name="MyAPI", version="2.0.0", debug=True, port=3000) \
        .set_database(host="db.prod.com", port=5432, name="myapi_prod") \
        .set_redis(host="redis.prod.com") \
        .set_logging(level="DEBUG") \
        .set_email() \
        .build()

    print(f"  App: {config.get('app.name')} v{config.get('app.version')}")
    print(f"  Database: {config.get('database.host')}:{config.get('database.port')}")
    print(f"  Debug: {config.get('app.debug')}")
    print(f"  Server: :{config.get('app.port')}")

    # ── 验证单例 ──
    print(f"\n🔒 验证单例:")
    c1 = ConfigManager()
    c2 = ConfigManager()
    print(f"  c1 is c2: {c1 is c2}")
    print(f"  c1.get('app.name'): {c1.get('app.name')}")
    print(f"  c2.get('app.name'): {c2.get('app.name')}")

    # ── 使用 Factory 从默认值创建 ──
    print(f"\n🏭 使用 Factory 创建:")
    default_config = ConfigFactory.from_defaults()
    print(f"  App: {default_config.get('app.name')}")
    print(f"  Database port: {default_config.get('database.port')}")

    # ── 变更监听 ──
    print(f"\n👂 变更监听:")
    config.on_change(lambda k, v: print(f"    🔔 配置变更: {k} = {v}"))
    config.set("app.port", 4000)

    # ── 冻结测试 ──
    print(f"\n❄️  冻结测试:")
    config.freeze()
    try:
        config.set("app.port", 5000)
    except RuntimeError as e:
        print(f"  ⚠️ {e}")

    config.unfreeze()
    config.set("app.port", 5000)
    print(f"  解冻后: port = {config.get('app.port')}")

    # ── 导出 ──
    print(f"\n📤 导出:")
    print(f"  JSON:")
    print(f"  {config.to_json()}")
    print(f"  变更历史: {config.get_history(3)}")

    # ── 验证建造者链 ──
    print(f"\n🔗 建造者链对比:")
    dev_config = ConfigBuilder() \
        .set_app(name="DevAPI", debug=True) \
        .set_database(host="localhost") \
        .set_logging(level="DEBUG") \
        .build()

    prod_config = ConfigBuilder() \
        .set_app(name="ProdAPI", debug=False, port=443) \
        .set_database(host="db.prod.internal") \
        .set_logging(level="WARNING", file="/var/log/app.log") \
        .build_and_freeze()

    print(f"  开发环境: debug={dev_config.get('app.debug')}, "
          f"db={dev_config.get('database.host')}")
    print(f"  生产环境: debug={prod_config.get('app.debug')}, "
          f"db={prod_config.get('database.host')}, "
          f"frozen={prod_config.stats['frozen']}")

    print("\n" + "=" * 60)
    print("✅ 配置管理器演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo()
