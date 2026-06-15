# 权限装饰器实战速查

## 角色检查

```python
def require_role(role):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if user.get("role") != role:
                raise PermissionError(f"需要 {role} 角色")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator
```

## 权限检查

```python
def require_permission(permission):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if permission not in user.get("permissions", []):
                raise PermissionError(f"缺少 {permission} 权限")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator
```

## 认证 + 授权链

```python
@audit_log              # 3. 记录审计日志
@authenticated          # 2. 检查认证
@require_role("admin")  # 1. 检查角色
def delete_user(user, id):
    return {"status": "deleted"}
```

## 用户模型设计

```python
user = {
    "name": "Alice",
    "authenticated": True,     # 是否已登录
    "role": "admin",           # 角色（单一）
    "permissions": [           # 权限（多个）
        "read", "write", "delete"
    ]
}
```

## 权限继承原则

- 角色是权限的集合
- admin 拥有所有权限
- editor 拥有 read + write
- viewer 只有 read
- 权限检查优先于角色检查
