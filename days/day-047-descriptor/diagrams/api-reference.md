# Day 047 — 描述符 API 速查表

## 描述符协议方法

| 方法 | 触发时机 | 参数 | 返回值 |
|------|----------|------|--------|
| `__get__(self, obj, objtype)` | 读取属性 | obj=实例(类访问为None), objtype=所属类 | 属性值 |
| `__set__(self, obj, value)` | 赋值属性 | obj=实例, value=新值 | None |
| `__delete__(self, obj)` | 删除属性 | obj=实例 | None |
| `__set_name__(self, owner, name)` | 类定义时 | owner=所属类, name=属性名 | None |

## 描述符类型对比

| 类型 | 实现方法 | 优先级 | 典型用途 |
|------|----------|--------|----------|
| 数据描述符 | `__get__` + `__set__` | 高于实例 `__dict__` | `property`, 字段验证 |
| 非数据描述符 | 仅 `__get__` | 低于实例 `__dict__` | 方法绑定, `@staticmethod` |

## property API

```python
@property
def attr(self): ...        # getter

@attr.setter
def attr(self, value): ... # setter

@attr.deleter
def attr(self): ...        # deleter
```

## 描述符 vs 普通方法 vs property

| 特性 | 描述符 | 普通方法 | property |
|------|--------|----------|----------|
| 自动调用 | ✅ | ✅ | ✅ |
| 可自定义校验 | ✅ | ❌ | ✅ |
| 可复用 | ✅✅✅ | ❌ | ❌ |
| 支持 `__set_name__` | ✅ | ❌ | ❌ |

## 常用描述符模式

```python
# 类型检查
class Typed:
    def __init__(self, expected_type): ...
    def __set__(self, obj, value):
        if not isinstance(value, self.expected_type):
            raise TypeError(...)

# 懒加载/缓存
class LazyProperty:
    def __get__(self, obj, objtype=None):
        value = self.func(obj)
        obj.__dict__[self.attrname] = value  # 绕过描述符
        return value

# 只读
class ReadOnly:
    def __set__(self, obj, value):
        if hasattr(obj, self.private_name):
            raise AttributeError("只读属性")

# 日志
class Logged:
    def __get__(self, obj, objtype=None):
        print(f"[GET] {self.name}")
        return getattr(obj, self.private_name)
```
