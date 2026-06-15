# Day 024 — 装饰器进阶练习题与检查表

## ✅ 完成检查表

### 概念理解
- [ ] 理解带参数装饰器的三层嵌套结构
- [ ] 能解释 `@decorator` 和 `@decorator(args)` 的等价关系
- [ ] 理解类装饰器的 `__init__` 和 `__call__` 分工
- [ ] 理解类装饰器 vs 函数装饰器的优劣
- [ ] 能分析多层装饰器的执行顺序（洋葱模型）
- [ ] 理解 "关注点分离" 在装饰器中的应用
- [ ] 理解缓存、重试、权限装饰器的适用场景

### 代码实践
- [ ] 能实现带参数装饰器
- [ ] 能实现 `@log` 和 `@log(level=...)` 智能装饰器
- [ ] 能实现类装饰器
- [ ] 能实现缓存装饰器（简单、LRU、TTL）
- [ ] 能实现重试装饰器（带退避）
- [ ] 能实现权限检查装饰器
- [ ] 能组合多个装饰器
- [ ] 能创建装饰器工厂

### 练习完成
- [ ] 基础练习（1-4 题）
- [ ] 进阶练习（5-7 题）
- [ ] 挑战练习（8-10 题）

---

## 📝 基础练习

### 练习 1：自定义日志级别装饰器

实现装饰器 `log_with_level(level)`，使被装饰函数调用时以指定级别打印日志。同时支持 `@log_with_level`（默认 INFO）和 `@log_with_level("DEBUG")`。

```python
@log_with_level
def foo():
    return "foo"

@log_with_level("WARNING")
def bar():
    return "bar"

foo()  # [INFO] foo() 被调用
bar()  # [WARNING] bar() 被调用
```

<details>
<summary>提示</summary>
使用默认参数技巧：`def log_with_level(func=None, level="INFO")`
</details>

### 练习 2：限流装饰器

实现装饰器 `rate_limit(max_calls, window)`，在 window 秒内最多允许 max_calls 次调用，超出时抛出 RuntimeError。

```python
@rate_limit(max_calls=3, window=5)
def api_call():
    return "调用成功"

for i in range(5):
    try:
        print(api_call())
    except RuntimeError as e:
        print(f"第 {i+1} 次: {e}")
```

### 练习 3：输入验证装饰器

实现装饰器 `validate_args`，检查参数类型是否符合函数的类型注解。

```python
@validate_args
def add(a: int, b: int) -> int:
    return a + b

add(1, 2)       # ✅
add("1", 2)     # ❌ TypeError: a 应该是 int，得到 str
```

<details>
<summary>提示</summary>
使用 `inspect.signature(func)` 获取参数类型标注。
</details>

### 练习 4：类装饰器实现计时器

使用类装饰器实现 `Timer`，自动记录函数执行时间，并提供 `.stats()` 方法输出统计。

```python
@Timer
def slow(n):
    time.sleep(n / 10)
    return n

slow(1)
slow(2)
slow.stats()  # 输出平均耗时、调用次数等
```

---

## 🔥 进阶练习

### 练习 5：观察者模式装饰器

实现装饰器 `observable`，当被装饰函数被调用时，通知所有注册的观察者。

```python
@observable
def user_login(username):
    return f"用户 {username} 登录成功"

# 注册观察者
def send_email(user):
    print(f"发送登录通知邮件给 {user}")

def log_login(user):
    print(f"记录登录日志: {user}")

user_login.attach(send_email)
user_login.attach(log_login)

user_login("Alice")
# 输出：
# 用户 Alice 登录成功
# 发送登录通知邮件给 Alice
# 记录登录日志: Alice
```

<details>
<summary>提示</summary>
在 wrapper 上维护一个观察者列表，调用原函数后遍历通知所有观察者。
</details>

### 练习 6：函数节流装饰器

实现装饰器 `throttle(interval)`，在 interval 秒内只执行一次函数，丢弃多余调用。

```python
@throttle(1)
def refresh():
    print("刷新数据")

refresh()  # 执行
refresh()  # 忽略（1秒内）
time.sleep(1)
refresh()  # 执行（已过 1 秒）
```

### 练习 7：带失效时间的权限装饰器

扩展权限装饰器，添加权限缓存（在指定时间内不重复检查权限）。

```python
@cached_permission(ttl=5)
def delete_resource(user, resource_id):
    """检查用户是否有删除权限"""
    # 假设这里是数据库查询，耗时 0.5s
    time.sleep(0.5)
    return user.get("role") == "admin"

# 第一次调用：花 0.5s 检查
# 5 秒内再次调用：立刻返回缓存结果
```

---

## 🏆 挑战练习

### 练习 8：装饰器链分析器

实现一个 `analyze_decorators` 工具，可以分析函数上应用了哪些装饰器以及它们的顺序。

```python
@decorator_a
@decorator_b
@decorator_c
def my_func():
    pass

info = analyze_decorators(my_func)
# 输出：
# 装饰器链（从内到外）：
#   1. decorator_c
#   2. decorator_b
#   3. decorator_a
```

<details>
<summary>提示</summary>
通过 `__wrapped__` 属性逐层分析（需要所有装饰器都用了 @functools.wraps）。
</details>

### 练习 9：可组合的数据转换管道

实现装饰器 `pipeline(*transformers)`，创建一个数据转换管道，输入数据依次通过所有转换器。

```python
@pipeline(
    lambda x: x.strip(),
    lambda x: x.upper(),
    lambda x: f"---{x}---",
)
def get_input():
    return "  hello world  "

result = get_input()
print(result)  # "---HELLO WORLD---"
```

### 练习 10：完整的 Web 请求处理管道

组合以下装饰器，模拟一个完整的 Web 请求处理流程：

1. `@route("/api/users")` — 路由匹配
2. `@authenticate` — 认证（检查 token）
3. `@require_permission("users:read")` — 权限检查
4. `@validate_json({"page": int, "limit": int})` — 参数校验
5. `@cache_response(ttl=30)` — 响应缓存
6. `@rate_limit(max_calls=10, window=60)` — 限流

```python
@route("/api/users")
@authenticate
@require_permission("users:read")
@validate_json({"page": int, "limit": int})
@cache_response(ttl=30)
@rate_limit(max_calls=10, window=60)
def list_users(request):
    """返回用户列表"""
    ...
```

**要求**：至少实现 3-4 个装饰器，展示它们如何协同工作。

---

## 💡 思考题

1. 带参数装饰器什么时候需要三层嵌套？能否用一层实现？什么情况下会失败？
2. 类装饰器如何支持被装饰函数的属性访问（例如 `func.some_attr`）？
3. 缓存装饰器在并发环境下有什么线程安全问题？如何解决？
4. 装饰器链中，如果一个装饰器抛出异常，其他装饰器的清理逻辑还能执行吗？
5. 装饰器是否可以被删除/撤销？如果可以，怎么实现？

## 📊 自我评估

| 技能 | 😰 不熟练 | 🤔 基本掌握 | 💪 熟练 |
|------|----------|------------|--------|
| 带参数装饰器 | | | |
| 可选参数装饰器 | | | |
| 类装饰器 | | | |
| 洋葱模型理解 | | | |
| 缓存装饰器 | | | |
| 重试装饰器 | | | |
| 权限装饰器 | | | |
| 装饰器链组合 | | | |
| 装饰器工厂 | | | |
| 装饰器顺序分析 | | | |

---

## 🧪 练习题解答思路

### 练习 1：日志级别装饰器

```python
def log_with_level(func=None, level="INFO"):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[{level}] {func.__name__}() 被调用")
            return func(*args, **kwargs)
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
```

### 练习 2：限流装饰器

```python
def rate_limit(max_calls, window):
    timestamps = []

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            while timestamps and now - timestamps[0] > window:
                timestamps.pop(0)
            if len(timestamps) >= max_calls:
                raise RuntimeError("请求过于频繁")
            timestamps.append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### 练习 3：类型验证装饰器

```python
import inspect

def validate_args(func):
    sig = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        for param_name, param_value in bound.arguments.items():
            param = sig.parameters[param_name]
            if param.annotation is not inspect.Parameter.empty:
                expected = param.annotation
                if not isinstance(param_value, expected):
                    raise TypeError(
                        f"{param_name} 应该是 {expected.__name__}，"
                        f"得到 {type(param_value).__name__}"
                    )
        return func(*args, **kwargs)
    return wrapper
```

### 练习 5：观察者装饰器

```python
def observable(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        for observer in wrapper._observers:
            observer(*args, **kwargs)
        return result

    wrapper._observers = []

    def attach(observer):
        wrapper._observers.append(observer)

    def detach(observer):
        wrapper._observers.remove(observer)

    wrapper.attach = attach
    wrapper.detach = detach
    return wrapper
```

### 练习 6：节流装饰器

```python
def throttle(interval):
    def decorator(func):
        last_called = 0

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal last_called
            now = time.time()
            if now - last_called < interval:
                return  # 或记录丢弃
            last_called = now
            return func(*args, **kwargs)
        return wrapper
    return decorator
```
