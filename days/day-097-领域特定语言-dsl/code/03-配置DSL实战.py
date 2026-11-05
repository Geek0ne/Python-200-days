"""
Day 097 - 实战：配置 DSL 与验证器

学习要点：
1. 构建一个完整的配置 DSL
2. 添加类型验证和默认值
3. 支持嵌套配置和链式调用
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, get_type_hints
import json


# ============================================================
# 配置 DSL 核心
# ============================================================

class ConfigNode:
    """配置节点 —— 支持嵌套的配置 DSL"""
    
    def __init__(self, name: str = "root"):
        self._name = name
        self._values: dict[str, Any] = {}
        self._children: dict[str, 'ConfigNode'] = {}
        self._validators: dict[str, Callable] = {}
        self._defaults: dict[str, Any] = {}
        self._types: dict[str, type] = {}
    
    def __getattr__(self, name: str):
        """
        DSL 核心：属性访问 → 配置读写
        
        config.database.host  # 读取
        config.database.host = "localhost"  # 写入
        """
        if name.startswith("_"):
            raise AttributeError(name)
        
        # 如果是子节点，返回子节点
        if name in self._children:
            return self._children[name]
        
        # 返回一个属性代理，支持赋值
        return _ConfigProxy(self, name)
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._set_value(name, value)
    
    def _set_value(self, name: str, value: Any):
        """设置值（带类型检查）"""
        if name in self._types:
            expected = self._types[name]
            if not isinstance(value, expected):
                raise TypeError(
                    f"配置项 [{name}] 期望类型 {expected.__name__}，"
                    f"实际得到 {type(value).__name__}"
                )
        if name in self._validators:
            if not self._validators[name](value):
                raise ValueError(f"配置项 [{name}] 验证失败: {value}")
        self._values[name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._values.get(name, self._defaults.get(name, default))
    
    def child(self, name: str) -> 'ConfigNode':
        """创建子节点（DSL 方法）"""
        if name not in self._children:
            self._children[name] = ConfigNode(name)
        return self._children[name]
    
    def validate_type(self, name: str, expected_type: type):
        """声明类型约束"""
        self._types[name] = expected_type
        return self
    
    def validate(self, name: str, func: Callable):
        """声明验证规则"""
        self._validators[name] = func
        return self
    
    def default(self, name: str, value: Any):
        """设置默认值"""
        self._defaults[name] = value
        return self
    
    def to_dict(self) -> dict:
        """导出为字典"""
        result = {}
        # 合并默认值和实际值
        for k, v in {**self._defaults, **self._values}.items():
            result[k] = v
        # 递归处理子节点
        for name, child in self._children.items():
            result[name] = child.to_dict()
        return result
    
    def to_json(self, indent=2) -> str:
        """导出为 JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def __repr__(self):
        return f"ConfigNode({self._name}, values={self._values}, children={list(self._children.keys())})"


class _ConfigProxy:
    """配置属性代理"""
    
    def __init__(self, node: ConfigNode, name: str):
        self._node = node
        self._name = name
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            # 这里是 node.xxx.yyy = value 的情况
            # 先创建子节点
            child = self._node.child(self._name)
            child._set_value(name, value)
    
    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        child = self._node.child(self._name)
        return getattr(child, name)
    
    def __repr__(self):
        return repr(self._node.get(self._name))


# ============================================================
# DSL 使用演示
# ============================================================

print("=" * 60)
print("配置 DSL 实战演示")
print("=" * 60)

# ---------- 构建配置 DSL ----------
config = ConfigNode("app")

# 数据库配置（嵌套）
config.database.host = "localhost"
config.database.port = 5432
config.database.name = "myapp_db"
config.database.pool_size = 10

# 缓存配置
config.cache.backend = "redis"
config.cache.host = "127.0.0.1"
config.cache.port = 6379
config.cache.ttl = 3600

# 日志配置
config.logging.level = "INFO"
config.logging.format = "%(asctime)s [%(levelname)s] %(message)s"
config.logging.file = "/var/log/app.log"

# 验证规则
config.database.validate("port", lambda v: 1 <= v <= 65535)
config.database.validate_type("host", str)
config.cache.validate("ttl", lambda v: v > 0)

print("\n--- 配置树 ---")
print(f"数据库: {config.database.to_dict()}")
print(f"缓存: {config.cache.to_dict()}")
print(f"日志: {config.logging.to_dict()}")

print("\n--- JSON 输出 ---")
print(config.to_json())


# ---------- 默认值 ----------

config2 = ConfigNode("minimal")
config2.default("timeout", 30)
config2.default("retries", 3)
config2.default("debug", False)

print("\n--- 带默认值的配置 ---")
print(f"timeout: {config2.get('timeout')}")  # 30 (默认)
print(f"retries: {config2.get('retries')}")  # 3 (默认)
config2._set_value("debug", True)
print(f"debug: {config2.get('debug')}")  # True (覆盖默认)


# ---------- 类型检查 ----------

print("\n--- 类型检查演示 ---")
try:
    config.database.port = "not_a_number"  # 应该报错
except TypeError as e:
    print(f"  类型错误捕获: {e}")

try:
    config.cache.ttl = -1  # 应该验证失败
except ValueError as e:
    print(f"  验证错误捕获: {e}")

print("\n✅ 类型安全的配置 DSL！")


# ============================================================
# DSL 设计模式总结
# ============================================================

print("\n" + "=" * 60)
print("DSL 设计模式总结")
print("=" * 60)
print("""
本示例用到的 DSL 模式：
1. 属性代理 (Property Proxy) → config.xxx.yyy 语法
2. 链式调用 (Fluent Interface) → .validate().default() 链
3. 类型约束 (Type Safety) → 运行时类型检查
4. 值验证 (Validation) → 自定义验证规则
5. 默认值 (Defaults) → 部分配置省略时有默认值

关键：这些模式让配置代码「读起来像声明式 DSL」，
而不是一堆 if/else 和字典操作。
""")
