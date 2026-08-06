# Day 100 - 快速参考卡

## 🎯 核心概念速查

### 迭代器协议
```python
class Iterator:
    def __iter__(self): return self
    def __next__(self): ...
```

### 上下文管理器协议
```python
class ContextManager:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc_val, exc_tb): ...
```

### 装饰器模式
```python
def decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

## 📊 并发模型速查

| 场景 | 推荐 | 原因 |
|------|------|------|
| IO 密集型 | asyncio | 单线程高并发 |
| CPU 密集型 | 多进程 | 绕过 GIL |
| 简单 IO | 多线程 | 实现简单 |

## 🔧 常用工具

```bash
# 性能剖析
python -m cProfile script.py

# 内存追踪
python -m memory_profiler script.py

# 代码质量
python -m py_compile script.py
```
