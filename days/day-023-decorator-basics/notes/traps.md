# 常见装饰器陷阱与避坑

## 陷阱 1：忘记 functools.wraps

```python
# ❌ 错误
def decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

# ✅ 正确
def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

## 陷阱 2：返回值类型假设

```python
# ❌ 假设返回值是字符串
def uppercase(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs).upper()  # 如果返回 int 就崩了
    return wrapper
```

## 陷阱 3：装饰器参数不匹配

```python
# ❌ 固定参数
def decorator(func):
    def wrapper(x, y):
        return func(x, y)
    return wrapper

# ✅ 通用参数
def decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

## 陷阱 4：类方法装饰器忘记 self

```python
# ❌ 类方法装饰器忘记第一个参数 self
def decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)  # 需要 args[0] 是 self
    return wrapper
```

## 陷阱 5：带参数装饰器忘记括号

```python
# ❌ @decorator 是装饰器；@decorator() 是调用装饰器
@log        # 正确——log 本身是装饰器
@log()      # 正确——log() 返回装饰器（如果实现正确）
@log("DEBUG")  # 正确——三层嵌套
```
