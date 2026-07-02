# Day 047 — 描述符常见陷阱总结

## 陷阱 1：实例属性覆盖非数据描述符

```python
class MyMethod:
    def __get__(self, obj, objtype=None):
        return lambda: "called"

class MyClass:
    method = MyMethod()

obj = MyClass()
obj.method = "overwritten"  # ⚠️ 覆盖了描述符
obj.method()                # TypeError!
```

**解决**：使用数据描述符（同时实现 `__set__`）。

## 陷阱 2：描述符实例共享状态

```python
class Shared:
    def __get__(self, obj, objtype=None):
        return self.value  # ⚠️ 所有实例共享 self.value
    def __set__(self, obj, value):
        self.value = value  # ⚠️ 写到描述符对象上
```

**解决**：把状态存到 `obj.__dict__[self.name]`。

## 陷阱 3：忘记处理类访问 (obj=None)

```python
class Desc:
    def __get__(self, obj, objtype=None):
        return obj.name  # ⚠️ 类访问时 obj 是 None → AttributeError
```

**解决**：
```python
def __get__(self, obj, objtype=None):
    if obj is None:
        return self  # 类访问返回描述符本身
    return obj.name
```

## 陷阱 4：`__set_name__` 遗忘

不写 `__set_name__`，描述符不知道自己的字段名，无法：
- 在错误消息中显示字段名
- 存储到正确的实例属性名

**解决**：始终实现 `__set_name__`。

## 陷阱 5：描述符中循环引用

描述符 `__get__` 返回实例本身可能导致无限递归。

**解决**：缓存到 `obj.__dict__`，下次访问直接读缓存。
