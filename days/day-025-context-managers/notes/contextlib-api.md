# contextlib API 速查与对比

## 上下文管理器实现方式对比

| 方式 | 代码量 | 灵活性 | 可读性 | 适用场景 |
|------|--------|--------|--------|----------|
| 基于类（`__enter__`/`__exit__`） | 较多 | 高 | 好 | 复杂逻辑、需要状态管理、需要继承 |
| `@contextmanager` 装饰器 | 少 | 中 | 极好 | 简单场景、资源获取/释放 |
| `contextlib.closing` | 最少 | 低 | 好 | 已有 close() 方法的对象 |
| `contextlib.ContextDecorator` | 中 | 高 | 好 | 既当装饰器又当上下文管理器 |

## contextlib 工具使用时机

| 工具 | 使用时机 | 替代方案 |
|------|----------|----------|
| `closing` | 对象有 close() 但不支持 with | 手写包装类 |
| `suppress` | 忽略特定异常 | try-except-pass |
| `redirect_stdout` | 临时捕获 print 输出 | 手动 sys.stdout 替换 |
| `redirect_stderr` | 临时捕获错误输出 | 手动 sys.stderr 替换 |
| `ExitStack` | 动态数量的资源管理 | 嵌套 with |
| `nullcontext` | 条件性上下文管理 | if-else 分支 |
| `ContextDecorator` | 装饰器+上下文复用 | 分别实现 |

## 常见异常处理模式

```python
# 模式 1：传播异常（默认行为）
def __exit__(self, *args):
    return False  # 或 return None

# 模式 2：抑制异常
def __exit__(self, *args):
    return True  # 谨慎使用！

# 模式 3：记录日志后传播
def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type:
        logger.error(f"异常: {exc_val}")
    return False

# 模式 4：只抑制特定异常
def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type is ValueError:
        return True  # 抑制 ValueError
    return False     # 其他异常继续传播
```

## __exit__ 返回值速查

| 返回值 | 异常状态 | 效果 |
|--------|----------|------|
| `False` 或 `None` | 有异常 | 异常继续传播 |
| `False` 或 `None` | 无异常 | 正常退出 |
| `True` | 有异常 | 异常被抑制 |
| `True` | 无异常 | 正常退出 |
