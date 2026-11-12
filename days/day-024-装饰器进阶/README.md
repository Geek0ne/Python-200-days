# Day 024 — 装饰器进阶

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

**参考答案**

三层嵌套对应**三种不同的职责**，每层都是一个可调用对象：

1. **最外层**：接收**装饰器参数**（如 `n=3`），返回中间层。`@repeat(3)` 会先执行 `repeat(3)`。
2. **中间层**：接收**被装饰的函数**（`func`），返回内层。这才是真正的"装饰器"。
3. **最内层（wrapper）**：接收**函数的调用参数**（`*args, **kwargs`），执行增强逻辑。

之所以要三层，是因为"装饰器参数、被装饰函数、调用参数"这三类信息在不同时机传入，必须各用一层来捕获。`@repeat(3)` 本质是 `say = repeat(3)(say)`，两次调用分别剥掉两层，最后由 wrapper 处理调用参数。

**能否更少层？** 三种职责无法省略，但可以用 `functools.partial` 或类来压缩"显式 def 嵌套层数"。例如用 partial 预先绑定参数，只需写两层 def：

```python
import functools
from functools import partial

def repeat(func, n):           # 只有两层：repeat + wrapper
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = None
        for _ in range(n):
            result = func(*args, **kwargs)
        return result
    return wrapper

@partial(repeat, n=3)          # partial 预先绑定 n，补上"参数层"
def say(msg):
    print(msg)

say("hi")
```

预期输出：

```text
hi
hi
hi
```

这里 `partial(repeat, n=3)` 生成了一个"只等 func"的可调用对象，承担了最外层的角色，于是显式嵌套减为两层。同理，带参数的类装饰器用 `__init__` 收参数、`__call__` 收函数，也能把嵌套压平。

2. 类装饰器和函数装饰器在内存管理上有什么区别？

**参考答案**

两者在"保留哪些对象存活"上没有本质差别——都持有原函数和自身状态的引用，只要被装饰的名字还在，这些对象就不会被回收。区别在于**状态存放的位置和对象开销**：

- **函数装饰器**：状态存在**闭包单元**（自由变量，如 `count`、`cache`）里，或通过 `wrapper.count = ...` 附加到 wrapper 上。被装饰的名字最终指向一个**函数对象**，相对轻量。
- **类装饰器**：状态存在**实例属性**（`self.count`、`self.cache`）里，即实例的 `__dict__`。被装饰的名字最终指向一个**类实例**，实例默认带 `__dict__`，单个对象开销通常比"函数 + 闭包单元"略大（可用 `__slots__` 减小）。

```python
import functools

def func_deco(func):
    count = 0
    @functools.wraps(func)
    def wrapper(*a, **kw):
        nonlocal count
        count += 1
        return func(*a, **kw)
    return wrapper

class ClassDeco:
    def __init__(self, func):
        self.func = func
        self.count = 0
    def __call__(self, *a, **kw):
        self.count += 1
        return self.func(*a, **kw)

@func_deco
def f():
    pass

@ClassDeco
def g():
    pass

f(); f()
g(); g()

# 函数装饰器：状态藏在闭包单元里
cells = dict(zip(f.__code__.co_freevars, (c.cell_contents for c in f.__closure__)))
print(cells["count"])      # 2
print(type(f).__name__)    # function

# 类装饰器：状态在实例 __dict__ 里
print(g.count)             # 2
print(type(g).__name__)    # ClassDeco
```

预期输出：

```text
2
function
2
ClassDeco
```

实际影响：简单状态（一个计数器）用闭包更轻量；复杂状态（缓存 + 过期时间 + 命中统计 + 连接池）用类实例能组织多个字段和方法，也更容易定义清理逻辑（如 `__del__` 或 close 方法）来显式释放资源。另外，类装饰器若持有绑定方法、方法又反向引用实例，可能形成循环引用，需要垃圾回收器来打破——闭包同样可能出现循环引用。

3. 如有 `@A @B` 和 `@B @A` 两种情况，什么场景下结果会不同？

**参考答案**

当两个装饰器**不可交换（non-commutative）**时结果不同。典型场景：

- **对返回值做变换**：如 `bold` 把结果包 `<b>`、`italic` 包 `<i>`，顺序决定标签的嵌套次序。
- **有顺序依赖的副作用**：如"先鉴权再记日志"与"先记日志再鉴权"；又如 `@lru_cache` 放在 `@timer` 内层还是外层，决定计时是否包含缓存命中。
- **一个依赖另一个添加的行为**：如重试装饰器应包住"已降级"的函数，顺序影响重试的对象。

反之，若两个装饰器只添加**彼此独立、互不干扰**的副作用（如两段无关日志），最终返回值通常相同（但副作用的输出先后仍不同）。

```python
import functools

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
    return "Hello"

@italic
@bold
def hello2():
    return "Hello"

print(hello())    # <b><i>Hello</i></b>
print(hello2())   # <i><b>Hello</b></i>
```

预期输出：

```text
<b><i>Hello</i></b>
<i><b>Hello</b></i>
```

`@bold @italic` 等价于 `bold(italic(hello))`：italic 先包内层、bold 再包外层，得到 `<b><i>…</i></b>`；交换后得到 `<i><b>…</b></i>`。这就是"顺序影响结果"的最直观例子。

4. 缓存装饰器在并发场景下会有什么问题？如何解决？（提示：线程安全）

**参考答案**

**问题**（以朴素 `memoize` 的 `if args not in cache: cache[args] = func(args)` 为例）：

- **检查-then-写入竞态**：两个线程同时发现某 key"不在缓存"，于是都去计算、都写入——同一份昂贵计算被重复执行（缓存击穿 / dogpile 效应）。
- **复合操作非原子**：CPython 的 GIL 让单条 dict 读写原子，但"检查 → 计算 → 写入"这一整段不是原子的；对更复杂的缓存（如 LRU 用 OrderedDict 要同时读 + 移动 + 淘汰），并发修改甚至可能破坏结构。在无 GIL 的自由线程版本（3.13+）里问题更突出。

**解决**：

- **加锁**：把"检查 + 计算 + 写入"放进 `threading.Lock` 临界区，保证同一 key 只算一次。缺点是一把全局锁会串行化所有调用；要更高并发可用**按 key 加锁**（只阻塞计算同一 key 的线程）。
- **直接用 `functools.lru_cache`**：它内部带锁，保证缓存结构不会被并发破坏（但同一 key 在极端竞争下仍可能被计算多次——它保证一致性，不保证"只算一次"）。
- 异步场景用 `asyncio.Lock`。

下面用全局锁保证"只算一次"，并用多线程验证：

```python
import functools
import threading

def memoize_locked(func):
    cache = {}
    lock = threading.Lock()
    @functools.wraps(func)
    def wrapper(*args):
        with lock:                   # 检查 + 计算 + 写入都在锁内 → 同一 key 只算一次
            if args not in cache:
                cache[args] = func(*args)
            return cache[args]
    return wrapper

compute_count = 0
count_lock = threading.Lock()

@memoize_locked
def slow_square(n):
    global compute_count
    with count_lock:
        compute_count += 1
    return n * n

threads = [threading.Thread(target=slow_square, args=(7,)) for _ in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(slow_square(7))   # 49
print(compute_count)    # 1：加锁保证只计算一次
```

预期输出：

```text
49
1
```

8 个线程并发请求同一参数，实际只计算了一次。若去掉锁，`compute_count` 可能大于 1（取决于线程调度），那就是竞态问题。

5. 重试装饰器如何处理幂等性问题？哪些操作不适合重试？

**参考答案**

**幂等性**指：一个操作执行一次和执行多次，对系统状态的影响相同。重试的安全前提是操作**幂等**，因为重试意味着"再执行一次"，而超时不等于服务端没执行——第一次可能已经成功、只是响应丢了，重试就会执行第二次。

**适合重试（幂等）**：纯读取（HTTP GET）、纯计算、幂等写入（PUT 更新为同一值、DELETE 指定资源），或带**幂等键（idempotency key）**的请求（服务端按 key 去重）。

**不适合重试（非幂等）**：POST 创建资源（可能重复创建）、支付 / 扣款（可能重复扣钱）、计数器自增（`+=1`）、发送邮件 / 短信（可能重复发送）、向列表或日志追加记录。

重试装饰器处理幂等性的做法：

- **装饰器本身无法判断业务是否幂等**，这是调用者的责任：只把重试用在幂等操作上。
- **先让非幂等操作变幂等**：引入幂等键 / 唯一请求 ID，由服务端去重；或用事务、"先查后做"的去重逻辑，再重试。
- **只重试瞬时异常**（网络超时、503、连接重置），不要重试业务错误（参数校验失败、4xx）——重试它们无意义且可能放大副作用。
- **限制次数 + 指数退避 + 随机抖动**，避免雪崩和对下游的重复冲击。

💡 提示：对"扣款"这类操作，正确姿势不是"失败就重试"，而是"先按订单号查询是否已扣款成功，再决定是否重新发起"——把非幂等变成幂等，才谈得上重试。

## 📚 扩展阅读

- [PEP 3129 — Class Decorators](https://peps.python.org/pep-3129/)
- Python `functools.lru_cache` 源码
- `tenacity` 库——专业的重试库
- `cachetools` 库——专业的缓存库
