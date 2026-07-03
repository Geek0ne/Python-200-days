"""
Day 048 - 混入(Mixin) - 实战案例
构建一个完整的可序列化、可日志记录的用户管理系统
"""
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================
# Mixin 定义
# ============================================

class SerializationMixin:
    """序列化混入 — 将对象转为字典/JSON"""

    def to_dict(self):
        result = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, 'to_dict'):
                value = value.to_dict()
            elif isinstance(value, list):
                value = [
                    item.to_dict() if hasattr(item, 'to_dict') else item
                    for item in value
                ]
            result[key] = value
        return result

    def to_json(self, indent=2):
        return json.dumps(
            self.to_dict(), ensure_ascii=False,
            indent=indent, default=str
        )

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)
        return cls(**data)

    def update_from(self, data: dict):
        for key, value in data.items():
            if hasattr(self, key) and not key.startswith('_'):
                setattr(self, key, value)


class LoggingMixin:
    """日志混入 — 为任何类添加日志能力"""

    def _setup_logger(self):
        if not hasattr(self, '_logger') or self._logger is None:
            self._logger = logging.getLogger(self.__class__.__name__)
            if not self._logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(logging.Formatter(
                    '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
                    datefmt='%H:%M:%S'
                ))
                self._logger.addHandler(handler)
                self._logger.setLevel(logging.INFO)
        return self._logger

    def log(self, message: str, level: int = logging.INFO):
        logger = self._setup_logger()
        logger.log(level, message)

    def log_operation(self, op_name: str):
        """装饰器：自动记录操作耗时"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                self.log(f"▶ 开始: {op_name}")
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start
                    self.log(f"✓ 完成: {op_name} ({elapsed:.3f}s)")
                    return result
                except Exception as e:
                    self.log(f"✗ 失败: {op_name} - {e}", logging.ERROR)
                    raise
            return wrapper
        return decorator


class ValidationMixin:
    """验证混入 — 为类添加字段验证能力"""

    def _validate_field(self, name: str, value: Any, rules: dict) -> List[str]:
        errors = []

        if 'type' in rules and not isinstance(value, rules['type']):
            errors.append(f"{name}: 期望 {rules['type'].__name__}, 实际 {type(value).__name__}")

        if 'min_length' in rules and isinstance(value, str) and len(value) < rules['min_length']:
            errors.append(f"{name}: 长度不能少于 {rules['min_length']}")

        if 'max_length' in rules and isinstance(value, str) and len(value) > rules['max_length']:
            errors.append(f"{name}: 长度不能超过 {rules['max_length']}")

        if 'required' in rules and rules['required'] and not value:
            errors.append(f"{name}: 不能为空")

        if 'pattern' in rules and isinstance(value, str):
            import re
            if not re.match(rules['pattern'], value):
                errors.append(f"{name}: 格式不正确")

        if 'in' in rules and value not in rules['in']:
            errors.append(f"{name}: 必须是 {rules['in']} 之一")

        return errors


class CacheMixin:
    """缓存混入 — 为类添加方法结果缓存能力"""

    def __init__(self, **kwargs):
        self._method_cache: Dict[str, Any] = {}
        super().__init__(**kwargs)

    def cached(self, method_name: str, *args, **kwargs):
        """缓存方法调用结果"""
        cache_key = f"{method_name}:{args}:{kwargs}"
        if cache_key not in self._method_cache:
            self._method_cache[cache_key] = getattr(self, method_name)(*args, **kwargs)
        return self._method_cache[cache_key]

    def clear_cache(self):
        self._method_cache.clear()


# ============================================
# 业务类定义
# ============================================

class User(SerializationMixin, LoggingMixin, ValidationMixin):
    """用户类 — 组合序列化、日志、验证能力"""

    # 字段验证规则
    _field_rules = {
        'name': {'type': str, 'min_length': 2, 'max_length': 50, 'required': True},
        'email': {'type': str, 'required': True,
                  'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'},
        'age': {'type': int, 'in': range(1, 151)},
        'role': {'type': str, 'in': ['admin', 'user', 'guest']},
    }

    def __init__(self, name: str, email: str, age: int = 25, role: str = "user"):
        # 验证
        errors = []
        errors.extend(self._validate_field('name', name, self._field_rules['name']))
        errors.extend(self._validate_field('email', email, self._field_rules['email']))
        errors.extend(self._validate_field('age', age, self._field_rules['age']))
        errors.extend(self._validate_field('role', role, self._field_rules['role']))

        if errors:
            raise ValueError("用户验证失败:\n" + "\n".join(errors))

        self.name = name
        self.email = email
        self.age = age
        self.role = role
        self.created_at = datetime.now()
        self.last_login = None
        self._login_count = 0

    def login(self):
        self._login_count += 1
        self.last_login = datetime.now()
        self.log(f"用户 {self.name} 登录 (第 {self._login_count} 次)")
        return True

    def __repr__(self):
        return f"User(name='{self.name}', role='{self.role}')"


class UserManager(LoggingMixin, CacheMixin):
    """用户管理器 — 管理多个用户"""

    def __init__(self):
        self._users: Dict[int, User] = {}
        self._next_id = 1

    @LoggingMixin.log_operation.__func__  # 绑定到实例
    def add_user(self, name, email, age=25, role="user"):
        user = User(name, email, age, role)
        user_id = self._next_id
        self._users[user_id] = user
        self._next_id += 1
        self.log(f"添加用户: {user}")
        return user_id

    def get_user(self, user_id: int) -> Optional[User]:
        return self._users.get(user_id)

    def find_users(self, **kwargs) -> List[User]:
        """按条件查找用户"""
        results = []
        for user in self._users.values():
            match = True
            for key, value in kwargs.items():
                if getattr(user, key, None) != value:
                    match = False
                    break
            if match:
                results.append(user)
        return results

    def remove_user(self, user_id: int) -> bool:
        if user_id in self._users:
            user = self._users.pop(user_id)
            self.log(f"删除用户: {user}")
            return True
        self.log(f"用户不存在: ID={user_id}", logging.WARNING)
        return False

    def export_all(self) -> str:
        """导出所有用户为 JSON"""
        users_data = [user.to_dict() for user in self._users.values()]
        return json.dumps(users_data, ensure_ascii=False, indent=2, default=str)

    def stats(self) -> dict:
        """统计信息"""
        users = list(self._users.values())
        return {
            "total": len(users),
            "roles": {role: len([u for u in users if u.role == role])
                      for role in set(u.role for u in users)},
            "avg_age": sum(u.age for u in users) / len(users) if users else 0
        }


# ============================================
# 使用演示
# ============================================

if __name__ == "__main__":
    print("=" * 60)
    print("Day 048 - 混入(Mixin) 实战：用户管理系统")
    print("=" * 60)

    manager = UserManager()

    # 添加用户
    print("\n--- 添加用户 ---")
    try:
        uid1 = manager.add_user("张三", "zhangsan@example.com", 28, "admin")
        uid2 = manager.add_user("李四", "lisi@example.com", 32, "user")
        uid3 = manager.add_user("王五", "wangwu@example.com", 22, "user")
    except ValueError as e:
        print(f"错误: {e}")

    # 登录
    print("\n--- 用户登录 ---")
    user = manager.get_user(uid1)
    if user:
        user.login()
        user.login()

    # 查找
    print("\n--- 查找用户 ---")
    admins = manager.find_users(role="admin")
    print(f"管理员: {admins}")

    young = [u for u in manager._users.values() if u.age < 25]
    print(f"25岁以下: {young}")

    # 统计
    print("\n--- 统计信息 ---")
    print(json.dumps(manager.stats(), ensure_ascii=False, indent=2))

    # 导出
    print("\n--- 导出所有用户 ---")
    print(manager.export_all())
