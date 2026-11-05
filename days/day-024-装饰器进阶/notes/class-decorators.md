# 类装饰器 与装饰器组合详解

## 类装饰器模式

```python
class MyDecorator:
    def __init__(self, func):
        """接收被装饰的函数"""
        functools.update_wrapper(self, func)
        self.func = func

    def __call__(self, *args, **kwargs):
        """调用时执行"""
        return self.func(*args, **kwargs)
```

## 函数装饰器 vs 类装饰器

| 对比维度 | 函数装饰器 | 类装饰器 |
|---------|-----------|---------|
| 状态管理 | 闭包变量或 wrapper 属性 | `self.xxx` 直接访问 |
| 可读性 | 嵌套较深时难读 | 扁平结构 |
| 方法扩展 | 手动赋值到 wrapper | 直接在类中定义 |
| 继承支持 | 有限 | 完整 |
| 调试便利 | 有限 | 良好 |

## 装饰器工厂模式

```python
def compose_decorators(*decorators):
    """将多个装饰器组合为一个"""
    def combined(func):
        for dec in reversed(decorators):
            func = dec(func)
        return func
    return combined

# 使用
secure_api = compose_decorators(
    audit_log,
    authenticated,
    require_role("admin")
)

@secure_api
def delete_resource(id):
    ...
```

## 带参数的类装饰器

```python
class Retry:
    def __init__(self, max_attempts=3):
        self.max_attempts = max_attempts

    def __call__(self, func):
        """__call__ 接收被装饰函数"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(self.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    pass
            raise
        return wrapper
```
