# 重试装饰器实战速查

## 基础重试模式

```python
def retry(max_attempts=3):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    print(f"重试 {attempt}/{max_attempts}: {e}")
            return wrapper
        return decorator
```

## 指数退避 (Exponential Backoff)

```python
def retry_with_backoff(max_attempts=3, delay=0.1, backoff=2.0):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        raise
                    time.sleep(current_delay)
                    current_delay *= backoff
            return wrapper
        return decorator
```

## 异常白名单

```python
def retry_on(exceptions=(ConnectionError,), max_attempts=3):
    """只重试指定类型的异常"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                except Exception:
                    raise  # 非白名单异常直接抛出
            return wrapper
        return decorator
```

## 适用场景

- ✅ 网络请求（ConnectionError, Timeout）
- ✅ 数据库操作（连接断开）
- ✅ 外部 API 调用（临时故障）
- ❌ 非幂等操作（支付、转账）
- ❌ 业务逻辑错误（输入校验失败）
- ❌ 永远不可能成功的操作（除以零）
