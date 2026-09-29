#!/usr/bin/env python3
"""
Day 062 - 数据序列化
示例 3: 实战 — 通用配置文件解析器

本示例实现一个通用的配置管理器 ConfigManager，支持：
1. 自动检测配置文件格式（JSON / YAML）
2. 环境变量替换（${VAR_NAME}）
3. 配置合并与深度覆盖
4. 配置验证与 Schema 校验
5. 配置热加载（文件变更自动重载）

运行方式: python3 03-config-parser.py
"""

import json
import os
import re
import copy
from pathlib import Path
from typing import Any, Dict, Optional, List

# 尝试导入 yaml
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# ─── 自定义异常 ───


class ConfigError(Exception):
    """配置相关错误的基类"""
    pass


class ConfigValidationError(ConfigError):
    """配置验证错误"""
    pass


class ConfigNotFoundError(ConfigError):
    """配置文件未找到"""
    pass


# ════════════════════════════════════════════
# ConfigManager — 通用配置管理器
# ════════════════════════════════════════════

class ConfigManager:
    """
    通用配置管理器
    
    特性：
    - 支持 JSON / YAML 格式自动检测
    - 环境变量替换: ${VAR_NAME} 或 ${VAR_NAME:-default_value}
    - 配置深度合并
    - Schema 校验
    - 配置热加载（可选）
    - 支持默认配置

    使用示例:
        config = ConfigManager("config.yaml")
        value = config.get("database.host", "localhost")
    """

    # 支持的文件格式
    SUPPORTED_FORMATS = {
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
    }

    def __init__(
        self,
        config_path: Optional[str] = None,
        defaults: Optional[Dict] = None,
        enable_env_var: bool = True,
        enable_hot_reload: bool = False,
    ):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径（可选）
            defaults: 默认配置字典
            enable_env_var: 是否启用环境变量替换
            enable_hot_reload: 是否启用热加载（文件变更时自动重载）
        """
        self._config_path = Path(config_path) if config_path else None
        self._defaults = defaults or {}
        self._enable_env_var = enable_env_var
        self._enable_hot_reload = enable_hot_reload
        self._last_mtime: float = 0
        self._config: Dict[str, Any] = {}

        # 如果有配置文件，立即加载
        if self._config_path and self._config_path.exists():
            self._config = self._load_file(self._config_path)
            self._last_mtime = self._config_path.stat().st_mtime
        elif self._config_path:
            raise ConfigNotFoundError(
                f"配置文件未找到: {self._config_path}")

        # 合并默认配置
        if self._defaults:
            self._config = self._deep_merge(self._defaults, self._config)

    # ─── 核心加载方法 ───

    def _detect_format(self, path: Path) -> str:
        """检测文件格式"""
        ext = path.suffix.lower()
        fmt = self.SUPPORTED_FORMATS.get(ext)
        if not fmt:
            raise ConfigError(
                f"不支持的配置文件格式: {ext} (支持: {', '.join(self.SUPPORTED_FORMATS.keys())})"
            )
        return fmt

    def _load_file(self, path: Path) -> Dict[str, Any]:
        """加载配置文件"""
        fmt = self._detect_format(path)
        content = path.read_text(encoding="utf-8")

        if fmt == "json":
            return json.loads(content)
        elif fmt == "yaml":
            if not HAS_YAML:
                raise ConfigError(
                    "需要安装 PyYAML: pip install pyyaml")
            return yaml.safe_load(content) or {}
        else:
            raise ConfigError(f"未知格式: {fmt}")

    def _resolve_env_vars(self, value: Any) -> Any:
        """
        递归解析字符串中的环境变量引用
        
        支持语法:
        - ${VAR_NAME}            — 引用环境变量，未设置则报错
        - ${VAR_NAME:-default}   — 引用环境变量，未设置时使用默认值
        - ${VAR_NAME:?error_msg} — 引用环境变量，未设置时抛出错误
        """
        if isinstance(value, str):
            pattern = r'\$\{([^}]+)\}'

            def replace_env(match):
                expr = match.group(1)
                if ':-' in expr:
                    # 带默认值: ${VAR:-default}
                    var_name, default = expr.split(':-', 1)
                    return os.environ.get(var_name.strip(), default.strip())
                elif ':?' in expr:
                    # 带错误消息: ${VAR:?error}
                    var_name, error_msg = expr.split(':?', 1)
                    val = os.environ.get(var_name.strip())
                    if val is None:
                        raise ConfigError(
                            f"环境变量 {var_name.strip()} 未设置: {error_msg.strip()}"
                        )
                    return val
                else:
                    # 普通引用: ${VAR}
                    var_name = expr.strip()
                    val = os.environ.get(var_name)
                    if val is None:
                        raise ConfigError(
                            f"环境变量未设置: {var_name}. "
                            f"可在文件中使用 ${{{var_name}:-default_value}} 设置默认值。"
                        )
                    return val

            return re.sub(pattern, replace_env, value)
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(item) for item in value]
        return value

    # ─── 深层合并 ───

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        深度合并两个字典
        
        - 键值冲突时 override 覆盖 base
        - 如果两边的值都是 dict，递归合并
        - 如果 override 的值是 None，删除该键（如果 base 中有）
        """
        result = copy.deepcopy(base)
        for key, value in override.items():
            if value is None and key in result:
                del result[key]
            elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result

    # ─── 公共 API ───

    def load(self, path: str) -> None:
        """加载新的配置文件"""
        self._config_path = Path(path)
        if not self._config_path.exists():
            raise ConfigNotFoundError(f"配置文件未找到: {path}")
        self._config = self._load_file(self._config_path)
        self._last_mtime = self._config_path.stat().st_mtime
        if self._defaults:
            self._config = self._deep_merge(self._defaults, self._config)

    def reload(self) -> None:
        """重新加载配置（用于热加载）"""
        if not self._config_path:
            return
        self._config = self._load_file(self._config_path)
        self._last_mtime = self._config_path.stat().st_mtime
        if self._defaults:
            self._config = self._deep_merge(self._defaults, self._config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号路径
        
        例如:
            config.get("database.host") -> 获取 config["database"]["host"]
        
        Args:
            key: 点号分隔的键路径
            default: 键不存在时返回的默认值
        """
        if self._enable_hot_reload:
            self._check_hot_reload()

        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值，支持点号路径"""
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def update(self, updates: Dict, merge: bool = True) -> None:
        """批量更新配置"""
        if merge:
            self._config = self._deep_merge(self._config, updates)
        else:
            self._config.update(updates)

    def get_all(self) -> Dict[str, Any]:
        """获取完整配置（返回深拷贝）"""
        if self._enable_hot_reload:
            self._check_hot_reload()

        # 递归解析环境变量
        if self._enable_env_var:
            return self._resolve_env_vars(copy.deepcopy(self._config))
        return copy.deepcopy(self._config)

    def dump(self, format: str = "json", path: Optional[str] = None) -> str:
        """
        导出配置
        
        Args:
            format: 导出格式 (json / yaml)
            path: 可选，写入文件路径
        
        Returns:
            导出的字符串
        """
        config = self._resolve_env_vars(copy.deepcopy(self._config))

        if format == "json":
            output = json.dumps(config, indent=2, ensure_ascii=False)
        elif format == "yaml":
            if not HAS_YAML:
                raise ConfigError("需要安装 PyYAML")
            output = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        else:
            raise ConfigError(f"不支持的导出格式: {format}")

        if path:
            Path(path).write_text(output, encoding="utf-8")

        return output

    def _check_hot_reload(self):
        """检查文件是否变更，触发热加载"""
        if self._config_path and self._config_path.exists():
            current_mtime = self._config_path.stat().st_mtime
            if current_mtime > self._last_mtime:
                self.reload()

    # ─── 配置验证 ───

    def validate_schema(self, schema: Dict[str, Any]) -> List[str]:
        """
        验证配置是否符合定义的 Schema
        
        Schema 格式示例:
        {
            "database.host": {"type": str, "required": True},
            "database.port": {"type": int, "required": True, "min": 1, "max": 65535},
            "app.debug": {"type": bool, "required": False, "default": False},
            "app.name": {"type": str, "required": True, "pattern": r"^[a-zA-Z]+$"},
        }
        
        Returns:
            验证错误列表，空列表表示全部通过
        """
        errors = []
        config = self._resolve_env_vars(copy.deepcopy(self._config))

        for key_path, rules in schema.items():
            value = self.get(key_path)

            # 必需的键
            if rules.get("required") and value is None:
                errors.append(f"[{key_path}] 必需的配置项缺失")
                continue

            if value is None:
                continue

            # 类型检查
            expected_type = rules.get("type")
            if expected_type and not isinstance(value, expected_type):
                errors.append(
                    f"[{key_path}] 类型错误: 期望 {expected_type.__name__}, "
                    f"实际 {type(value).__name__}"
                )
                continue

            # 数值范围检查
            if isinstance(value, (int, float)):
                min_val = rules.get("min")
                max_val = rules.get("max")
                if min_val is not None and value < min_val:
                    errors.append(f"[{key_path}] 值 {value} 小于最小值 {min_val}")
                if max_val is not None and value > max_val:
                    errors.append(f"[{key_path}] 值 {value} 大于最大值 {max_val}")

            # 字符串正则检查
            if isinstance(value, str):
                pattern = rules.get("pattern")
                if pattern and not re.match(pattern, value):
                    errors.append(f"[{key_path}] 值 '{value}' 不匹配正则: {pattern}")

                choices = rules.get("choices")
                if choices and value not in choices:
                    errors.append(
                        f"[{key_path}] 值 '{value}' 不在允许列表中: {choices}"
                    )

        return errors

    def __repr__(self) -> str:
        return (f"ConfigManager(path={self._config_path}, "
                f"loaded_keys={len(self._config)})")


# ════════════════════════════════════════════
# 使用演示
# ════════════════════════════════════════════

def main():
    print("=" * 60)
    print("🚀 实战：通用配置文件解析器")
    print("=" * 60)

    # ─── 准备测试配置文件 ───
    tmp_dir = Path("/tmp/day062_config")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 创建一个 JSON 配置文件
    json_config = {
        "app": {
            "name": "my-app",
            "version": "1.0.0",
            "debug": False
        },
        "server": {
            "host": "${SERVER_HOST:-0.0.0.0}",
            "port": "${SERVER_PORT:-8080}",
            "workers": 4
        },
        "database": {
            "host": "${DB_HOST:-localhost}",
            "port": 5432,
            "name": "myapp",
            "pool": {
                "min": 2,
                "max": 20
            }
        },
        "logging": {
            "level": "INFO",
            "file": "/var/log/app.log"
        }
    }

    json_path = tmp_dir / "config.json"
    json_path.write_text(json.dumps(json_config, indent=2, ensure_ascii=False))

    # ─── 1. 使用 JSON 配置 ───

    print("\n--- 1. 加载 JSON 配置文件 ---")
    config = ConfigManager(str(json_path), enable_env_var=True)
    print(f"加载成功: {config}")

    # 读取配置
    print(f"\napp.name: {config.get('app.name')}")
    print(f"server.port: {config.get('server.port')}")

    # 设置环境变量
    os.environ["SERVER_HOST"] = "192.168.1.100"
    os.environ["SERVER_PORT"] = "9090"

    resolved = config.get_all()
    print(f"\n环境变量替换后 server.host: {resolved['server']['host']}")
    print(f"环境变量替换后 server.port (字符串!): {resolved['server']['port']}")

    # ⚠️ 环境变量替换后，字符串 "9090" 还是字符串类型！
    # 可以手动转换
    port = int(config.get("server.port", "8080"))
    print(f"手动转换 port 为 int: {port}")

    # ─── 2. 配置合并 ───

    print("\n\n--- 2. 配置深度合并 ---")

    base_config = ConfigManager(str(json_path))
    override_config = {
        "app": {
            "debug": True,
            "extra_feature": "enabled"
        },
        "server": {
            "workers": 8
        }
    }
    base_config.update(override_config)
    print(f"合并后 app.debug: {base_config.get('app.debug')}")
    print(f"合并后 app.extra_feature: {base_config.get('app.extra_feature')}")
    print(f"合并后 server.workers: {base_config.get('server.workers')}")
    print(f"合并后 database.host (应保留): {base_config.get('database.host')}")

    # ─── 3. 默认配置 ───

    print("\n\n--- 3. 默认配置 ---")

    defaults = {
        "app": {
            "name": "default-app",
            "debug": False
        },
        "server": {
            "port": 3000,
            "workers": 1
        }
    }

    # 如果配置文件里没有这些项，会使用默认值
    config_with_defaults = ConfigManager(
        str(json_path), defaults=defaults)

    print(f"源自配置文件 - app.name: {config_with_defaults.get('app.name')}")
    print(f"源自配置文件 - app.debug: {config_with_defaults.get('app.debug')}")
    print(f"源自配置文件 - server.port: {config_with_defaults.get('server.port')}")

    # ─── 4. Schema 校验 ───

    print("\n\n--- 4. Schema 校验 ---")

    # 定义 Schema
    schema = {
        "app.name": {"type": str, "required": True},
        "app.debug": {"type": bool, "required": False},
        "server.host": {"type": str, "required": True},
        "server.port": {"type": str, "required": True},  # 环境变量可能是字符串
        "server.workers": {"type": int, "required": True, "min": 1, "max": 16},
        "database.host": {"type": str, "required": True},
        "database.port": {"type": int, "required": True, "min": 1, "max": 65535},
        "database.pool.min": {"type": int, "min": 1},
        "database.pool.max": {"type": int, "min": 1},
    }

    errors = config.validate_schema(schema)
    if not errors:
        print("✅ Schema 校验通过！")
    else:
        print("❌ Schema 校验失败:")
        for err in errors:
            print(f"  - {err}")

    # ─── 5. YAML 配置 ───

    print("\n\n--- 5. YAML 配置文件 ---")

    if HAS_YAML:
        yaml_content = """
app:
  name: my-yaml-app
  debug: false

server:
  host: "${SERVER_HOST:-0.0.0.0}"
  port: 3000

database:
  host: "${DB_HOST:-localhost}"
  port: 5432
  name: yamldb
  pool:
    min: 1
    max: 10

logging:
  level: DEBUG
  handlers:
    - type: console
      format: standard
    - type: file
      path: /var/log/app.log
      max_size: 100MB
"""
        yaml_path = tmp_dir / "config.yaml"
        yaml_path.write_text(yaml_content)

        yaml_config = ConfigManager(str(yaml_path), enable_env_var=True)
        print(f"YAML 配置加载成功")
        print(f"app.name: {yaml_config.get('app.name')}")
        print(f"logging.handlers 数量: {len(yaml_config.get('logging.handlers'))}")
        print(f"logging.handlers[0].type: {yaml_config.get('logging.handlers')[0]['type']}")

        # 导出
        exported = yaml_config.dump(format="yaml")
        print(f"\n导出 YAML (前300字符):\n{exported[:300]}")

    # ─── 6. 配置导出 ───

    print("\n\n--- 6. 导出配置 ---")

    export_path = tmp_dir / "exported_config.json"
    config.dump(format="json", path=str(export_path))
    print(f"配置已导出到: {export_path}")
    print(f"导出内容:\n{export_path.read_text(encoding='utf-8')}")

    # ─── 清理 ───
    import shutil
    shutil.rmtree(tmp_dir)

    print("\n" + "=" * 60)
    print("✅ 配置文件解析器演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
