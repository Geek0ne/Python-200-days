# functools.wraps 原理速查

`functools.wraps(func)` = `functools.update_wrapper(wrapper, func, assigned=WRAPPER_ASSIGNMENTS, updated=WRAPPER_UPDATES)`

## 复制的内容

| 属性 | 说明 | 默认值 |
|------|------|--------|
| `__module__` | 模块名 | 复制自原始函数 |
| `__name__` | 函数名 | 复制自原始函数 |
| `__qualname__` | 限定名 | 复制自原始函数 |
| `__annotations__` | 类型标注 | 复制自原始函数 |
| `__doc__` | 文档字符串 | 复制自原始函数 |
| `__dict__` | 属性字典 | 更新（合并） |

## 额外设置

```python
wrapper.__wrapped__ = func  # 保留原始函数引用
```

## 不要手动复制

```python
# ❌ 不要这样做
wrapper.__name__ = func.__name__
wrapper.__doc__ = func.__doc__

# ✅ 使用 wraps
@functools.wraps(func)
def wrapper():
    ...
```

## 为什么不加 wraps 很危险？

1. **调试困难** — 堆栈跟踪显示 `wrapper` 而非真实函数名
2. **文档生成** — Sphinx 等工具依赖 `__doc__`
3. **框架依赖** — Flask/Django 路由依赖 `__name__`
4. **内省工具** — `help()`、`inspect` 等依赖元信息
