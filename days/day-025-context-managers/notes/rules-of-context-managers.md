# 上下文管理器设计原则

## 黄金法则

1. **资源获取即初始化**：在 `__init__` 或 `__enter__` 中获取资源
2. **确定性清理**：在 `__exit__` 中确保释放资源
3. **异常透明**：默认让异常传播，只在确切知道后果时抑制异常
4. **单一职责**：一个上下文管理器只管理一种资源

## 常见反模式

```python
# ❌ 反模式 1：捕获所有异常但什么都不做
class AntiPattern1:
    def __exit__(self, *args):
        return True  # 所有的 bug 都被隐藏

# ❌ 反模式 2：__exit__ 中抛异常
class AntiPattern2:
    def __exit__(self, *args):
        1 / 0  # 覆盖了 with 块内的异常

# ❌ 反模式 3：在 __init__ 中做资源操作
class AntiPattern3:
    def __init__(self):
        self.f = open("file")  # 应该在 __enter__ 中打开
    def __enter__(self):
        return self.f
    def __exit__(self, *args):
        self.f.close()

# ✅ 正确做法
class CorrectPattern:
    def __init__(self, filename):
        self.filename = filename
    def __enter__(self):
        self.f = open(self.filename)
        return self.f
    def __exit__(self, *args):
        self.f.close()
```

## ExitStack 使用场景速查

| 场景 | 解决方案 |
|------|----------|
| 文件列表（运行时才知道） | `[stack.enter_context(open(f)) for f in files]` |
| 条件性资源 | `if cond: stack.enter_context(resource)` |
| 延迟清理 | `stack.callback(cleanup_func)` |
| 转移所有权 | `new_stack.pop_all(old_stack)` |
| 注册多个回调 | `stack.push(exit_func)` |
