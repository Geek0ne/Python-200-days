# 装饰器 API 速查表

## 核心概念

| 模式 | 代码 | 说明 |
|------|------|------|
| 基础装饰器 | `def d(f): def w(): ...; return w` | 最简形式 |
| 通用装饰器 | `def d(f): def w(*a,**k): ...; return w` | 处理任意参数 |
| 带 wraps | `@functools.wraps(f) def w(): ...` | 保留元信息 |
| 带参数 | `def d(x): def dec(f): ...; return dec` | 三层嵌套 |
| 类装饰器 | `class D: __init__(self,f); __call__(self,...)` | 可调用对象 |
| 可选参数 | `def d(f=None, *, kw=...):` | 两种调用方式 |

## 属性保留

| 装饰后属性 | 无 wraps | 有 wraps |
|-----------|---------|---------|
| `__name__` | `wrapper` | 原始函数名 |
| `__doc__` | `None` | 原始文档 |
| `__wrapped__` | 无 | 指向原始函数 |

## 装饰器排列

```python
@A           # 等价于：func = A(B(C(func)))
@B           # 装饰顺序：C → B → A（从下到上）
@C           # 调用顺序：A → B → C → func → C → B → A
def func():  # 洋葱模型：从外到里进，从里到外出
    pass
```
