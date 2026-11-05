# 装饰器语法糖与执行时机

## @ 语法糖的等价关系

```python
@decorator
def func():
    pass

# 完全等价于：
def func():
    pass
func = decorator(func)
```

## 执行时机：定义时

```python
# 装饰器在 def 语句执行时立即调用！
# 不是在调用 func() 时才调用。

@register        # ← 此时 decorator(func) 被调用
def func():      # ← func 被定义后立即被装饰
    pass
```

## 装饰与调用分离验证

```python
def log(func):
    print(f"定义时: {func.__name__} 被装饰")
    return func

@log
def a(): pass   # 输出：定义时: a 被装饰

@log
def b(): pass   # 输出：定义时: b 被装饰

# 此时还没有调用 a() 或 b()
# 但装饰器已经执行了！

a()  # 这里只执行原始函数，装饰器不执行
b()  # 同上
```

## 执行顺序总结

| 阶段 | 顺序 | 说明 |
|------|------|------|
| **装饰阶段** | 自下而上 | 靠近函数的装饰器先执行 |
| **调用阶段** | 自上而下（洋葱） | 外层先入，内层后出 |
