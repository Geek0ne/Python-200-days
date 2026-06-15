# Day 024 — 装饰器进阶 🚀

## 📖 学习目标

- 掌握带参数装饰器的原理与实现
- 掌握类装饰器的实现方式
- 理解多个装饰器的组合顺序与陷阱
- 实战：缓存装饰器、重试装饰器、权限装饰器
- 掌握装饰器链式组合的技巧

---

## 一、带参数的装饰器

### 1.1 三层嵌套结构

有时我们需要装饰器本身接受参数，例如指定日志级别、缓存时间等。这就需要**再包一层**：

```python
def repeat(n):              # 第一层：接收装饰器参数
    def decorator(func):    # 第二层：接收被装饰的函数
        @functools.wraps(func)
        def wrapper(*args, **kwargs):  # 第三层：接收函数参数
            for _ in range(n):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

@repeat(3)     # @repeat(3) → repeat(3) 返回 decorator，然后 @decorator 应用到函数
def say(msg):
    print(msg)

# 等价于：say = repeat(3)(say)
```

**执行流程：**
1. `repeat(3)` 被调用，返回内层 `decorator`
2. `@decorator` 将 `say` 函数传入 `decorator`
3. `decorator(say)` 返回 `wrapper`
4. `say` 被替换为 `wrapper`

### 1.2 默认参数技巧

一个常见需求是让装饰器**既能带参数又能不带参数**：

```python
def log(func=None, *, level="INFO"):
    """智能装饰器：@log 和 @log(level="DEBUG") 都支持"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[{level}] 调用 {func.__name__}")
            return func(*args, **kwargs)
        return wrapper

    if func is not None:        # 无参数调用：@log
        return decorator(func)
    return decorator             # 有参数调用：@log(level=...)

# 两种用法都支持
@log
def foo(): pass

@log(level="DEBUG")
def bar(): pass
```

---

## 二、类装饰器

### 2.1 可调用对象 `__call__`

任何实现了 `__call__` 方法的类实例都可以作为装饰器：

```python
class CallCounter:
    """类装饰器：统计函数调用次数"""

    def __init__(self, func):
        self.func = func
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        print(f"调用第 {self.count} 次")
        return self.func(*args, **kwargs)

@CallCounter
def hello():
    print("Hello!")

# hello 现在是 CallCounter 的实例
hello()  # 调用第 1 次
hello()  # 调用第 2 次
print(type(hello))  # <class '__main__.CallCounter'>
```

### 2.2 类装饰器的优势

| 特性 | 函数装饰器 | 类装饰器 |
|------|-----------|---------|
| 状态管理 | 通过 `wrapper.foo = value` 附加 | 直接使用 `self.xxx` |
| 方法扩展 | 手动赋值 | 直接在类中定义方法 |
| 可读性 | 闭包嵌套，不易读 | 扁平结构，清晰 |
| 继承 | 不易复用 | 支持继承 |
| 复杂逻辑 | 嵌套较深时混乱 | 自然 |

**类装饰器更适合**需要管理复杂状态的场景（如缓存、计数器、连接池）。

### 2.3 带参数的类装饰器

```python
class Retry:
    def __init__(self, max_attempts=3, delay=0):
        self.max_attempts = max_attempts
        self.delay = delay

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, self.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == self.max_attempts:
                        raise
                    print(f"第 {attempt} 次失败，重试...")
                    time.sleep(self.delay)
            return wrapper
        return wrapper

@Retry(max_attempts=3, delay=0.1)
def unstable_api():
    ...
```

> ⚠️ **注意**：带参数的类装饰器需要 `__init__` 接收参数，`__call__` 接收函数。类装饰器的 `__call__` 返回 wrapper，实例本身不直接作为 wrapper。

---

## 三、多个装饰器组合

### 3.1 组合顺序

装饰器的复合遵循**洋葱模型**：

```python
@decorator_a        # 外层
@decorator_b        # 中间
@decorator_c        # 内层
def func():
    pass

# 等价于：func = A(B(C(func)))
```

**执行顺序（从上到下）：**
1. **装饰阶段**：先装饰 C，再 B，最后 A（从下往上执行）
2. **调用阶段**：A 前置 → B 前置 → C 前置 → 原始函数 → C 后置 → B 后置 → A 后置（从上往下执行）

### 3.2 组合陷阱

```python
# ⚠️ 陷阱：装饰器顺序影响结果
def bold(func):
    @functools.wraps(func)
    def wrapper():
        return f"<b>{func()}</b>"
    return wrapper

def italic(func):
    @functools.wraps(func)
    def wrapper():
        return f"<i>{func()}</i>"
    return wrapper

@bold
@italic
def hello():
    return "Hello"  # → <b><i>Hello</i></b>

@italic
@bold
def hello2():
    return "Hello"  # → <i><b>Hello</b></i>
```

### 3.3 组合原则

- **关注点分离**：每个装饰器只做一件事
- **顺序依赖**：如果装饰器 A 需要 B 处理后的结果，A 应在上层
- **无副作用**：装饰器不应假设其他装饰器的存在
- **透明传递**：使用 `@functools.wraps` 确保元信息不丢失

---

## 四、实战：缓存装饰器

### 4.1 简单内存缓存

```python
def memoize(func):
    """缓存函数返回结果"""
    cache = {}
    @functools.wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper
```

### 4.2 LRU 缓存

使用 `collections.OrderedDict` 实现 LRU（Least Recently Used）缓存。

### 4.3 TTL 缓存

带过期时间的缓存，指定缓存多少秒后自动失效。

---

## 五、实战：重试装饰器

### 5.1 基础重试

```python
def retry(max_attempts=3):
    """函数执行失败时自动重试"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"第 {attempt} 次失败: {e}")
                    if attempt == max_attempts:
                        raise
            return wrapper
        return decorator
```

### 5.2 高级重试

支持指数退避（exponential backoff）、指定异常类型、最大延迟等。

---

## 六、实战：权限装饰器

### 6.1 角色权限检查

```python
def require_role(role):
    """检查用户是否有指定角色"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(user, *args, **kwargs):
            if user.get("role") != role:
                raise PermissionError(f"需要 {role} 角色")
            return func(user, *args, **kwargs)
        return wrapper
    return decorator
```

### 6.2 多角色与权限组合

支持任意可调用对象作为检查器，灵活组合。

---

## 💡 思考题

1. 为什么带参数的装饰器需要三层嵌套？能否用更少层次实现？
2. 类装饰器和函数装饰器在内存管理上有什么区别？
3. 如有 `@A @B` 和 `@B @A` 两种情况，什么场景下结果会不同？
4. 缓存装饰器在并发场景下会有什么问题？如何解决？（提示：线程安全）
5. 重试装饰器如何处理幂等性问题？哪些操作不适合重试？

## 📚 扩展阅读

- [PEP 3129 — Class Decorators](https://peps.python.org/pep-3129/)
- Python `functools.lru_cache` 源码
- `tenacity` 库——专业的重试库
- `cachetools` 库——专业的缓存库
