# Day 025 — 上下文管理器

## 📖 学习目标

- 理解 `with` 语句的底层执行流程
- 掌握 `__enter__` / `__exit__` 上下文管理协议
- 熟练使用 `contextlib` 模块的各种工具
- 掌握嵌套和动态上下文管理
- 实战：文件操作、数据库连接、计时器、资源管理等
- 理解异步上下文管理器

---

## 一、为什么需要上下文管理器？

### 1.1 资源管理的痛点

在编程中，我们经常需要管理各种资源：文件、网络连接、数据库连接、锁等。这些资源的共同特点是：**用完后必须释放**，否则会导致资源泄漏。

**传统方式 — try/finally：**

```python
# 每个资源都要自己管理，容易出错
f = None
try:
    f = open("data.txt")
    data = f.read()
    process(data)
finally:
    if f:
        f.close()
```

缺点：
- 代码冗长，容易忘记 `finally`
- 如果忘记 `close()`，文件句柄泄漏
- 多个资源嵌套时复杂度指数级上升
- 异常处理逻辑和业务逻辑混杂

**上下文管理器方式：**

```python
with open("data.txt") as f:
    data = f.read()
    process(data)
# 文件自动关闭
```

### 1.2 设计原理

上下文管理器解决的核心问题是**资源生命周期管理**。它的设计哲学是：

1. **关注点分离**：资源的获取和释放由管理器负责，业务代码只关注"用资源做什么"
2. **确定性清理**：无论正常退出还是异常退出，都能保证清理代码被执行
3. **声名式语法**：用 `with` 关键字明确标记资源的使用范围
4. **可组合性**：多个管理器可以自由组合、嵌套

> 这种模式也称为 **RAII**（Resource Acquisition Is Initialization，资源获取即初始化），源自 C++，Python 的 `with` 语句实现了类似的效果。

---

## 二、with 语句底层原理

### 2.1 执行流程

```python
with EXPRESSION as TARGET:
    BLOCK
```

背后的执行步骤：

```text
Step 1: 计算 EXPRESSION，得到上下文管理器对象 manager
Step 2: 调用 manager.__enter__()，返回值赋给 TARGET
Step 3: 执行 BLOCK 代码块
Step 4a: 如果 BLOCK 正常完成 → 调用 __exit__(None, None, None)
Step 4b: 如果 BLOCK 抛出异常 → 调用 __exit__(exc_type, exc_val, exc_tb)
Step 5: 根据 __exit__ 返回值决定是否抑制异常
```

### 2.2 字节码层面

CPython 为 `with` 语句生成了特殊的字节码指令：

```python
import dis


def demo():
    with open("/dev/null") as f:
        f.read()

dis.dis(demo)
```

部分输出：
```text
  2     SETUP_WITH    → 设置上下文管理器，调用 __enter__
  5     STORE_FAST    → 将 __enter__ 返回值赋给 f
  6     LOAD_FAST     → 加载 f
  7     LOAD_ATTR     → 加载 f.read
  10    CALL_FUNCTION → 调用 f.read()
  13    POP_TOP
  14    POP_BLOCK
  15    LOAD_CONST    → 加载 None
  18    WITH_EXCEPT_START → 开始异常处理
```

`SETUP_WITH` 和 `WITH_EXCEPT_START` 是专为 `with` 语句设计的字节码，确保 `__exit__` 在任何情况下都会被调用。

### 2.3 伪代码等价形式

```python
# with EXPRESSION as TARGET:
#     BLOCK

# 等价于（简化版）：
manager = EXPRESSION
target = manager.__enter__()
exc = True
try:
    TARGET = target
    BLOCK
    exc = False
except:
    if not manager.__exit__(*sys.exc_info()):
        raise
finally:
    if not exc:
        manager.__exit__(None, None, None)
```

---

## 三、__enter__ / __exit__ 协议详解

### 3.1 __enter__ 方法

```python
def __enter__(self):
    """进入 with 块时调用"""
    # 1. 执行准备工作（打开文件、获取锁、建立连接等）
    # 2. 返回一个值（可选），该值绑定到 as 子句
    return self  # 或其他对象
```

**关键点：**
- `__enter__` 的返回值是 `as` 子句绑定的值
- 如果不需要 `as` 绑定，可以不返回任何值（返回 None）
- `__enter__` 中如果抛出异常，`__exit__` **不会被调用**（因为 never entered）

### 3.2 __exit__ 方法

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    """离开 with 块时调用

    参数：
      exc_type: 异常类型（没有异常时为 None）
      exc_val:  异常实例（没有异常时为 None）
      exc_tb:   回溯对象（没有异常时为 None）

    返回值：
      True  → 抑制异常（异常不会继续传播）
      False → 让异常继续传播（默认行为）
    """
    # 1. 执行清理工作（关闭文件、释放锁、断开连接等）
    # 2. 根据异常情况决定返回值
    return False
```

**关键点：**
- 三个参数在没有异常时**全是 None**
- 返回 `True` 会**静默吞掉异常**，谨慎使用
- 如果 `__exit__` 自身抛出异常，**原异常会被覆盖**
- 返回值和 `return` 语义不同：显式返回 True 才抑制，默认 None（等价 False）

### 3.3 异常处理模式

```python
class FileManager:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode

    def __enter__(self):
        self.file = open(self.filename, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

        if exc_type is None:
            # 正常退出
            print("正常关闭")
            return False

        if exc_type is FileNotFoundError:
            # 文件未找到，记录日志但不中断
            print(f"文件不存在: {exc_val}")
            return True  # 抑制异常

        # 其他异常，记录并传播
        print(f"发生异常: {exc_type.__name__}: {exc_val}")
        return False  # 继续传播
```

### 3.4 常见陷阱和最佳实践

| 陷阱 | 说明 | 最佳实践 |
|------|------|----------|
| `__exit__` 意外返回 True | 异常被静默吞掉，难以调试 | 只在确定需要抑制时返回 True |
| `__exit__` 中抛异常 | 覆盖原异常 | 用 try/except 包裹清理代码 |
| 管理器重复使用 | 大多数管理器是一次性的 | 添加 `used` 标志或重新创建 |
| 忘记 `super().__exit__()` | 子类重写时丢失父类清理 | 始终调用 `super().__exit__()` |
| `__enter__` 返回 self | 不能区分管理和被管理对象 | 按职责分离 |

---

## 四、基于类的上下文管理器

### 4.1 完整示例

```python
class DatabaseConnection:
    """数据库连接上下文管理器"""

    def __init__(self, host, port, database):
        self.host = host
        self.port = port
        self.database = database
        self.connection = None

    def __enter__(self):
        print(f"连接到 {self.host}:{self.port}/{self.database}")
        # 模拟建立连接
        self.connection = {"host": self.host, "db": self.database}
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("关闭数据库连接")
        self.connection = None

        if exc_type:
            print(f"连接异常关闭: {exc_type.__name__}")
            # 数据库错误通常需要回滚，但这里继续传播
            return False

        print("连接正常关闭")
        return False


# 使用
with DatabaseConnection("localhost", 5432, "mydb") as conn:
    print(f"查询数据库: {conn}")
```

### 4.2 返回值模式

| `__enter__` 返回值 | `as` 绑定 | 适用场景 |
|---|---|---|
| `self` (管理器自身) | 管理器对象 | 管理器提供操作方法时 |
| `self.resource` (被管理资源) | 资源对象 | 资源是第三方对象时 |
| 一个新对象 | 新对象 | 需要转换或包装时 |
| `None` (无返回值) | `None` | 只需要副作用时 |

示例：返回不同对象

```python
class ConnectionPool:
    """连接池 — 返回连接，而非自身"""

    def __init__(self):
        self._connections = [{"id": 1}, {"id": 2}]

    def __enter__(self):
        # 从池中借出一个连接
        conn = self._connections.pop()
        print(f"借出连接 {conn['id']}")
        return conn  # 返回连接对象，不是 self

    def __exit__(self, *args):
        # 归还连接
        self._connections.append(args)
        return False
```

---

## 五、contextlib 模块

Python 标准库提供了 `contextlib` 模块，大大简化了上下文管理器的实现和使用。

### 5.1 API 速查表

| 工具 | 用途 | 一句话说明 |
|------|------|-----------|
| `@contextmanager` | 用生成器实现上下文管理器 | yield 前是 enter，yield 后是 exit |
| `closing(thing)` | 自动调用对象的 close() | 给任意对象添加 with 支持 |
| `suppress(*exceptions)` | 静默忽略指定异常 | 替代 `try: ... except: pass` |
| `redirect_stdout(file)` | 临时重定向 stdout | 捕获 print 输出 |
| `redirect_stderr(file)` | 临时重定向 stderr | 捕获错误输出 |
| `ExitStack()` | 动态管理多个上下文管理器 | 运行时决定打开哪些资源 |
| `nullcontext(enter_result=None)` | 空操作上下文管理器 | 条件分支中的统一接口 |
| `ContextDecorator` | 既是装饰器又是上下文管理器 | 一个类两种用法 |
| `@asynccontextmanager` | 异步版 @contextmanager | async with 配套 |

### 5.2 @contextmanager 装饰器

这是最常用的工具，用**生成器函数**实现上下文管理器：

```python
from contextlib import contextmanager


@contextmanager
def managed_resource(*args, **kwargs):
    """用生成器实现上下文管理器"""
    # __enter__ 部分
    resource = acquire_resource(*args, **kwargs)
    try:
        yield resource  # ← 这个值被 as 绑定
    finally:
        # __exit__ 部分（无论如何都会执行）
        release_resource(resource)
```

**原理：** `@contextmanager` 将生成器函数包装成一个实现了 `__enter__`/`__exit__` 的类。

- `__enter__`：调用生成器，推进到第一个 `yield`
- `__exit__`：推进生成器继续执行（或传入异常）

**限制：**
- 生成器必须 yield **恰好一次**（不能多，不能少）
- 不能在 yield 前后使用 return 返回值
- 不支持协程（需要 `@asynccontextmanager`）

### 5.3 contextlib.closing

用于那些有 `close()` 方法但没有实现上下文管理器的对象：

```python
from contextlib import closing
from urllib.request import urlopen

with closing(urlopen("https://python.org")) as page:
    for line in page:
        print(line)
# page.close() 自动调用
```

等价于：

```python
class closing:
    def __init__(self, thing):
        self.thing = thing
    def __enter__(self):
        return self.thing
    def __exit__(self, *exc_info):
        self.thing.close()
```

### 5.4 contextlib.suppress

替代 `try-except-pass` 模式，更简洁：

```python
from contextlib import suppress

# 传统方式
try:
    os.remove("temp.txt")
except FileNotFoundError:
    pass

# suppress 方式
with suppress(FileNotFoundError):
    os.remove("temp.txt")

# 抑制多种异常
with suppress(FileNotFoundError, PermissionError):
    os.remove("protected.txt")
```

### 5.5 contextlib.redirect_stdout / redirect_stderr

临时重定向标准输出/错误：

```python
from contextlib import redirect_stdout, redirect_stderr
import io

# 捕获 print 输出到字符串
f = io.StringIO()
with redirect_stdout(f):
    print("这行不会显示在控制台")
    print("会被捕获到 StringIO")
captured = f.getvalue()  # "这行不会显示在控制台\n会被捕获到 StringIO\n"

# 重定向到文件
with open("log.txt", "w") as log, redirect_stdout(log):
    print("这行写入日志文件")
```

### 5.6 contextlib.ExitStack

**最强大的上下文管理工具**，适用于运行时才能确定需要的资源数量：

```python
from contextlib import ExitStack


def process_files(file_list):
    """处理多个文件（数量在运行时才能确定）"""
    with ExitStack() as stack:
        files = [
            stack.enter_context(open(fname))
            for fname in file_list
        ]
        # 所有文件在退出时自动关闭
        for f in files:
            process(f)
```

**高级用法：**

```python
# 1. 条件性进入
with ExitStack() as stack:
    if need_cache:
        cache = stack.enter_context(open("cache.txt"))
    # ... 其他操作

# 2. 推迟清理（手动清理）
stack = ExitStack()
f1 = stack.enter_context(open("a.txt"))
f2 = stack.enter_context(open("b.txt"))
# ... 一些操作
stack.close()  # 手动触发 LIFO 顺序清理

# 3. 注册回调
stack.callback(lambda: print("cleanup"))
stack.push(exit_func)  # 注册 __exit__ 风格的函数

# 4. pop_all 转移所有权
stack2 = ExitStack()
stack2.pop_all(stack)  # stack 的所有清理任务移交给 stack2
```

### 5.7 contextlib.nullcontext

在条件分支中提供统一的上下文管理器接口：

```python
from contextlib import nullcontext


def process(data, profile=False):
    """profile=True 时启用性能分析，否则无操作"""
    profiler = cProfile.Profile() if profile else nullcontext()
    with profiler:
        result = expensive_computation(data)
    return result
```

### 5.8 contextlib.ContextDecorator

让同一个类既能做上下文管理器，又能做装饰器：

```python
from contextlib import ContextDecorator


class trace(ContextDecorator):
    def __enter__(self):
        print("开始")
        return self
    def __exit__(self, *exc):
        print("结束")
        return False


# 作为装饰器
@trace()
def hello():
    print("hello")

# 作为上下文管理器
with trace():
    print("world")
```

---

## 六、嵌套上下文管理器

### 6.1 嵌套写法

```python
# 方式 1：缩进嵌套
with open("a.txt") as f1:
    with open("b.txt") as f2:
        data1 = f1.read()
        data2 = f2.read()

# 方式 2：单行多个（Python 3.1+）
with open("a.txt") as f1, open("b.txt") as f2:
    data1 = f1.read()
    data2 = f2.read()

# 方式 3：ExitStack（动态数量）
with ExitStack() as stack:
    f1 = stack.enter_context(open("a.txt"))
    f2 = stack.enter_context(open("b.txt"))

# 方式 4：括号语法（Python 3.10+）
with (
    open("a.txt") as f1,
    open("b.txt") as f2,
    open("c.txt") as f3,
):
    ...
```

### 6.2 退出顺序

嵌套上下文管理器的退出顺序是 **LIFO**（后进先出）：

```python
class Tag:
    def __init__(self, name):
        self.name = name
    def __enter__(self):
        print(f"<{self.name}>")
        return self
    def __exit__(self, *args):
        print(f"</{self.name}>")
        return False

with Tag("div"):
    with Tag("p"):
        print("Hello")
# 输出：
# <div>
# <p>
# Hello
# </p>
# </div>
```

### 6.3 异常传播顺序

```text
内层异常 → 内层 __exit__ → 外层 __exit__

如果内层 __exit__ 返回 True（抑制）：
  → 外层认为没有异常
  → 外层 __exit__(None, None, None)

如果内层 __exit__ 返回 False（传播）：
  → 异常传播到外层
  → 外层 __exit__(exception_type, ...)
```

---

## 七、异步上下文管理器

### 7.1 协议

Python 3.5+ 引入了异步上下文管理器，用于 `async with` 语句：

```python
class AsyncResource:
    async def __aenter__(self):
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.sleep(0.1)
        return False


# 使用
async def main():
    async with AsyncResource() as res:
        await res.do_work()
```

### 7.2 @asynccontextmanager

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def async_open(filename):
    f = await aio_open(filename)
    try:
        yield f
    finally:
        await f.close()
```

### 7.3 与普通上下文管理器的对比

| 特性 | 同步 | 异步 |
|------|------|------|
| 协议方法 | `__enter__` / `__exit__` | `__aenter__` / `__aexit__` |
| 语句 | `with` | `async with` |
| 装饰器 | `@contextmanager` | `@asynccontextmanager` |
| 堆栈 | `ExitStack` | `AsyncExitStack` |
| 引入版本 | Python 2.5 (PEP 343) | Python 3.5 (PEP 492) |

---

## 八、实战案例

### 8.1 原子化 JSON 写入

```python
class AtomicJSONWriter:
    """保证 JSON 写入的原子性

    原理：先写入临时文件，成功后再原子 rename
    如果中间出错，临时文件自动删除，不破坏原文件
    """

    def __init__(self, filepath, indent=2):
        self.filepath = filepath
        self.indent = indent
        self.temp_path = filepath + ".tmp"

    def __enter__(self):
        self.fp = open(self.temp_path, "w", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fp.close()
        if exc_type is not None:
            os.remove(self.temp_path)  # 回滚
            return False
        os.replace(self.temp_path, self.filepath)  # 原子提交
        return False

    def write(self, data):
        json.dump(data, self.fp, ensure_ascii=False, indent=self.indent)
```

### 8.2 数据库连接池

```python
class ConnectionPool:
    """简单的数据库连接池管理器

    with pool as conn: 自动管理连接的获取和归还
    """

    def __init__(self, max_connections=5):
        self._pool = [self._create_conn(i) for i in range(max_connections)]
        self._in_use = set()
        self._lock = threading.Lock()

    def _create_conn(self, id):
        return {"id": id, "active": True}

    def __enter__(self):
        with self._lock:
            conn = self._pool.pop()
            self._in_use.add(conn["id"])
            return conn

    def __exit__(self, *args):
        with self._lock:
            self._in_use.remove(self._current_conn["id"])
            self._pool.append(self._current_conn)
        return False
```

### 8.3 计时器装饰器 + 上下文管理器

```python
class Timer:
    """既是上下文管理器又是装饰器的计时器"""

    def __init__(self, name="Timer"):
        self.name = name
        self.elapsed = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self.start
        print(f"[{self.name}] {self.elapsed*1000:.2f}ms")
        return False

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


# 两种用法
@Timer("排序")
def sort():
    ...

with Timer("查询"):
    ...
```

### 8.4 临时环境变量

```python
@contextmanager
def set_env(**environ):
    """临时设置环境变量"""
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(old_environ)


with set_env(DATABASE_URL="sqlite:///test.db"):
    assert os.environ["DATABASE_URL"] == "sqlite:///test.db"
# 环境变量恢复
```

### 8.5 日志分组上下文

```python
class LogGroup:
    """日志分组 — 自动缩进和时间标记"""

    indent = 0

    def __init__(self, label):
        self.label = label
        self.start = None

    def __enter__(self):
        self.start = time.time()
        self._log(f"▶ {self.label}")
        LogGroup.indent += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        LogGroup.indent -= 1
        elapsed = time.time() - self.start
        status = "✓" if exc_type is None else "✗"
        self._log(f"{status} {self.label} ({elapsed:.2f}s)")
        return False

    @classmethod
    def _log(cls, msg):
        print(f"{'  ' * cls.indent}{msg}")


with LogGroup("HTTP 请求"):
    LogGroup._log("验证 token...")
    with LogGroup("数据库查询"):
        LogGroup._log("SELECT ...")
```

---

## 九、最佳实践和设计模式

### 9.1 什么时候用上下文管理器？

| 场景 | 典型资源 | 示例 |
|------|----------|------|
| 文件 I/O | 文件句柄 | `with open(...) as f:` |
| 网络连接 | socket | `with socket.create_connection(...) as s:` |
| 数据库 | 连接/游标 | `with db.cursor() as cur:` |
| 线程同步 | 锁/信号量 | `with lock:` |
| 临时状态 | 环境变量 | `with set_env(DEBUG="1"):` |
| 事务 | 数据库事务 | `with transaction():` |
| 计时 | 时间测量 | `with Timer() as t:` |
| 重定向 | stdout/stderr | `with redirect_stdout(f):` |
| 精度/上下文 | decimal 精度 | `with localcontext() as ctx:` |

### 9.2 设计模式

**模式 1：资源获取与释放**

```python
class Resource:
    def __enter__(self):
        self._acquire()
        return self
    def __exit__(self, *args):
        self._release()
        return False
```

**模式 2：临时状态修改**

```python
@contextmanager
def temporary_change(obj, attr, value):
    old = getattr(obj, attr)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        setattr(obj, attr, old)
```

**模式 3：条件执行**

```python
@contextmanager
def optional(condition, cm, else_cm=None):
    """条件性进入上下文管理器"""
    if condition:
        with cm:
            yield
    else:
        if else_cm:
            with else_cm:
                yield
        else:
            yield
```

**模式 4：重试/回滚**

```python
@contextmanager
def transaction(conn):
    savepoint = conn.savepoint()
    try:
        yield
    except:
        conn.rollback(savepoint)
        raise
    else:
        conn.commit()
```

### 9.3 性能考虑

- 上下文管理器的开销极小（主要是函数调用和几个字节码）
- 不要为了避免 `with` 而写 `try/finally` — `with` 更安全
- `ExitStack` 的 enter_context 有轻微开销，但对大多数应用可忽略
- 热路径（内层循环）中慎用嵌套上下文管理器

---

## 十、常见误区 FAQ

### Q1: `__exit__` 返回 True 到底是什么意思？

A: 告诉 Python 解释器："我已经处理了这个异常，不要传播它"。程序会继续执行 with 块之后的代码。

```python
class Eater:
    def __exit__(self, *args):
        return True  # 吃掉一切异常

with Eater():
    1 / 0  # ZeroDivisionError 被静默吞掉
print("这行会执行")  # ← 真的会执行！
```

### Q2: `@contextmanager` 生成器里 yield 后面的代码在异常时会执行吗？

A: **会的**，前提是你用了 try/finally。如果直接 yield 没有 try/finally，且抛出异常，yield 之后的代码不会执行：

```python
@contextmanager
def bad():
    print("enter")
    yield
    print("exit")  # 如果异常发生，这行不执行

@contextmanager
def good():
    print("enter")
    try:
        yield
    finally:
        print("exit")  # 无论如何都执行
```

### Q3: ExitStack 可以代替嵌套 with 吗？

A: 可以，但更适合动态场景。对于已知数量的固定资源，嵌套 `with` 或逗号分隔更清晰。`ExitStack` 的优势在于：

- 运行时才能知道需要多少资源
- 需要条件性进入某些上下文
- 需要将清理推迟到不确定的未来

### Q4: 上下文管理器可以重复使用吗？

A: 默认**不能**。大多数上下文管理器（如 `open()` 返回的文件对象）在 `__exit__` 后状态已改变。但你可以：

1. 每次创建新实例
2. 在 `__exit__` 中"重置"状态（不推荐）
3. 使用工厂函数每次返回新管理器

---

## 十一、思考题

### 思考题 1：上下文管理器的本质

为什么 Python 选择用协议（`__enter__`/`__exit__`）而不是继承（抽象基类）来实现上下文管理器？这种设计有什么好处？

**提示**：想想 Python 的"鸭子类型"哲学、标准库的灵活性、以及用户自定义类型的自由度。

**参考答案**

Python 选择"协议"而不是"抽象基类"（ABC，即强制子类实现某些方法的基类），核心原因是鸭子类型（duck typing）哲学：只要一个对象走起来像鸭子、叫起来像鸭子，它就是鸭子。对象只要有 `__enter__` 和 `__exit__` 两个方法，`with` 就能用它，完全不需要继承某个特定基类。

这样做的好处：

- **零侵入**：标准库和第三方库的既有类（文件对象、锁、数据库连接）只需实现两个方法就能支持 `with`，不必改动继承树。
- **不受继承束缚**：一个类可以继承任意业务基类，同时又是上下文管理器，不用为了这个能力额外挤进一层 ABC。
- **风格统一**：迭代（`__iter__`）、可调用（`__call__`）等能力都走同样的"特殊方法协议"路线，学会一个就学会一类。
- **组合灵活**：`contextlib.closing` 这类工具可以给任何带 `close()` 的对象"贴上" with 能力；若走继承路线，就得修改类本身或做注册，麻烦得多。

极小的例子——没有任何继承，照样能用 `with`：

```python
class Hello:
    def __enter__(self):
        print("进入")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("退出")
        return False


with Hello():
    print("中间")
```

依次输出 `进入`、`中间`、`退出`。`with` 只检查"有没有这两个方法"，不关心"继承了谁"。

### 思考题 2：try/finally vs with

```python
# 方式 A
f = open("file")
try:
    process(f)
finally:
    f.close()

# 方式 B
with open("file") as f:
    process(f)
```

方式 A 和方式 B 是严格等价的吗？如果不是，差异在哪里？

**提示**：想想 `open()` 本身可能失败的情况，以及 `__exit__` 的返回值。

**参考答案**

不是严格等价。对内置文件对象这个具体例子，两者的可观察行为几乎一致（都保证关闭文件；`open()` 失败时都不做清理）；但在协议层面有两点关键差异：

1. **`open()` 本身失败时**：方式 A 的 `open()` 写在 `try` 之外，它抛异常时 `finally` 不会执行——不过此时文件根本没打开，也没有东西可关；方式 B 中 `__enter__` 失败时同样不会调用 `__exit__`。这一点两者其实一致，真正的启示是：资源要在 `__enter__` 里获取，而不是在 `__init__` 里，否则获取失败时清理逻辑不会执行，就会泄漏。
2. **`__exit__` 能抑制异常，`finally` 不能**：`with` 会把异常信息传给 `__exit__`，若它返回 `True`，异常就被吞掉、程序继续往下走；`try/finally` 只保证清理代码执行，异常仍会向外传播。文件对象的 `__exit__` 返回 `None`（不抑制），所以本例表现相同；换成自定义管理器差异就出现了：

```python
class Swallow:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return True  # 抑制异常


# with 版本：异常被 __exit__ 吞掉
with Swallow():
    raise ValueError("出错了")
print("with 版本：异常被吞掉，程序继续")

# try/finally 版本：finally 无法抑制异常
try:
    try:
        raise ValueError("出错了")
    finally:
        pass  # 相当于清理动作
except ValueError:
    print("try/finally 版本：异常照常抛出，需要外部捕获")
```

预期输出：

```text
with 版本：异常被吞掉，程序继续
try/finally 版本：异常照常抛出，需要外部捕获
```

💡 提示：`with` 还有工程上的优势——代码更短、不会忘记写 `finally`、资源的作用域一目了然，所以日常应优先用 `with`。

### 思考题 3：ExitStack 的设计意图

假设你有以下场景：

```python
files = ["a.txt", "b.txt", "c.txt"]
# 想同时打开所有文件并处理
```

1. 用 `with open(f1) as a, open(f2) as b, ...` 有什么问题？
2. `ExitStack` 如何解决这个问题？
3. 如果中间一个文件打开失败，已经打开的文件应该怎么处理？

**参考答案**

1. 逗号分隔的写法要求**写代码时就知道文件数量**。而 `files` 是运行时的列表，长度不定，没法写出固定个数的 `open`；硬要做只能递归嵌套或拼接代码字符串，既丑陋又容易出错。
2. `ExitStack` 是一个"动态上下文管理器栈"：每调用一次 `stack.enter_context(...)` 就登记一个管理器，`with` 块结束时按 **LIFO**（后进先出）顺序自动调用它们的 `__exit__`。资源数量完全由运行时决定，一行列表推导就能打开任意多个文件。
3. 中间某个文件打开失败时，异常会传出 `with` 块，`ExitStack` 的 `__exit__` 依然会执行，把**已经打开的文件按相反顺序全部关闭**，不会泄漏。这正是手写多层 `try/finally` 难以保证的地方。

完整示例（自包含，用临时文件演示两种情况）：

```python
import os
import tempfile
from contextlib import ExitStack

# 准备演示用的临时文件（实际使用时换成你自己的文件列表）
tmpdir = tempfile.mkdtemp()
paths = [os.path.join(tmpdir, n) for n in ("a.txt", "b.txt", "c.txt")]
for i, p in enumerate(paths):
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"文件 {i} 的内容")

# 正常情况：运行时决定打开多少个文件
with ExitStack() as stack:
    handles = [stack.enter_context(open(p, encoding="utf-8")) for p in paths]
    for h in handles:
        print(h.read())
print("全部关闭:", all(h.closed for h in handles))

# 异常情况：第三个文件不存在
bad_paths = paths[:2] + [os.path.join(tmpdir, "不存在.txt")]
opened = []
try:
    with ExitStack() as stack:
        for p in bad_paths:
            opened.append(stack.enter_context(open(p, encoding="utf-8")))
except FileNotFoundError:
    print("有文件打开失败，异常向外传播")
print("失败前已打开的文件是否全部自动关闭:", all(h.closed for h in opened))

# 清理演示文件
for p in paths:
    os.remove(p)
os.rmdir(tmpdir)
```

预期输出：

```text
文件 0 的内容
文件 1 的内容
文件 2 的内容
全部关闭: True
有文件打开失败，异常向外传播
失败前已打开的文件是否全部自动关闭: True
```

关键看第二段演示：`不存在.txt` 触发 `FileNotFoundError`，但之前打开的两个文件仍被自动关闭（`h.closed` 全为 `True`）。

### 思考题 4：__exit__ 中的异常吞噬

```python
class Swallower:
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type == ValueError:
            print("吞掉 ValueError")
            return True
        # RuntimeError 不处理
        return False

with Swallower():
    raise ValueError("test")
print("ValueError 被吞掉")

with Swallower():
    pass  # 正常退出
```

如果 `__exit__` 中除了返回 True，还打印了日志，这个日志是否可能被用户忽略？在生产环境中应该如何处理这种"抑制"操作？

**参考答案**

很可能被忽略。`print` 只是写到标准输出：生产环境里 stdout 未必被收集，可能被海量正常输出淹没，而且没有级别、时间戳和完整堆栈，出了问题很难追查。"抑制异常"意味着程序带着一个隐患继续运行，所以必须留下可审计的记录。

生产环境的建议做法：

- 用 `logging` 模块代替 `print`，以 `warning` 或 `error` 级别记录，并通过 `exc_info` 附上完整 traceback（异常堆栈）。
- 只抑制"预期的、可恢复的"异常（如文件不存在），抑制范围尽量小，并在注释里写明为什么可以安全忽略。
- 关键路径上配合监控指标或告警，让"被抑制的异常"能被统计和看见，而不是无声无息。

```python
import logging

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logger = logging.getLogger("demo")


class Swallower:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and issubclass(exc_type, ValueError):
            # 用 warning 级别记录，并带上完整 traceback
            logger.warning("抑制了一个 ValueError: %s", exc_val,
                           exc_info=(exc_type, exc_val, exc_tb))
            return True
        return False


with Swallower():
    raise ValueError("test")
print("ValueError 被吞掉，程序继续执行")
```

预期输出（traceback 部分输出到 stderr，细节随环境略有差异）：

```text
WARNING 抑制了一个 ValueError: test
Traceback (most recent call last):
  ...
ValueError: test
ValueError 被吞掉，程序继续执行
```

⚠️ 注意：题目中的 `Swallower` 只定义了 `__exit__`、缺少 `__enter__`，直接运行会报错（Python 3.12 报 `TypeError: 'Swallower' object does not support the context manager protocol`），需要补上 `def __enter__(self): return self`。另外原式 `exc_type == ValueError` 只匹配该类型本身，用 `issubclass` 还能覆盖它的子类。

### 思考题 5：与装饰器的组合

如何实现一个既可以用作 `@timer` 装饰器又可以用作 `with timer:` 上下文管理器的工具？这两种使用方式在语义上有什么细微差别？

```python
# 装饰器方式 — 整个函数耗时
@timer
def load_data():
    ...

# 上下文管理器方式 — 代码块耗时
with timer():
    load_data()
```

**提示**：考虑一下，装饰器方式无法精确控制计时范围，而上下文管理器可以。如果需要同时支持两种模式，需要满足什么接口？

**参考答案**

关键是让同一个类同时满足两套接口：上下文管理器协议（`__enter__`/`__exit__`）和"可调用"接口（`__call__`，即实例能像函数一样被调用，这正是装饰器的工作方式）。标准库的 `contextlib.ContextDecorator` 已经实现了后者——它的 `__call__` 会把被装饰函数包进 `with self:` 里执行，所以继承它就一次获得两种用法。

两种方式的语义差别：

- **装饰器方式**：计时范围是整个函数体，且每次调用都自动计时，适合"长期监控某个函数的整体耗时"；但没法只给函数中的一部分代码计时。
- **上下文管理器方式**：计时范围是任意代码块，可以只测函数里的三行，还能通过 `as t` 拿到实例、读取 `t.elapsed` 做后续处理，控制更精确。

```python
import time
from contextlib import ContextDecorator


class timer(ContextDecorator):
    def __init__(self, name="timer"):
        self.name = name
        self.elapsed = None  # 保存计时结果，供 with ... as t 读取

    def __enter__(self):
        self._start = time.perf_counter()  # 高精度计时起点
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.perf_counter() - self._start
        print(f"[{self.name}] 耗时 {self.elapsed:.4f} 秒")
        return False  # 不抑制异常


# 用法 1：装饰器 —— 每次调用函数都自动计时
@timer("load_data")
def load_data():
    time.sleep(0.05)  # 模拟耗时操作
    return 42


# 用法 2：上下文管理器 —— 只给指定代码块计时
with timer("代码块") as t:
    time.sleep(0.02)

print("函数返回值:", load_data())
print(f"代码块耗时约 {t.elapsed:.2f} 秒")
```

预期输出（具体耗时数值因机器而异）：

```text
[代码块] 耗时 0.0204 秒
[load_data] 耗时 0.0504 秒
函数返回值: 42
代码块耗时约 0.02 秒
```

💡 提示：作装饰器时要写带括号的 `@timer("名字")`，它会为每个被装饰函数创建新实例；若写裸的 `@timer`，函数会被当成 `name` 传进 `__init__`，语义就错了。不想继承 `ContextDecorator` 的话，也可以自己手写 `__call__` 返回包装函数（参见正文 8.3 节的 `Timer` 例子）。

---

## 📚 参考资料

- [PEP 343 — The "with" Statement](https://peps.python.org/pep-0343/)
- [Python 官方文档 — With Statement Context Managers](https://docs.python.org/3/reference/datamodel.html#context-managers)
- [Python 官方文档 — contextlib](https://docs.python.org/3/library/contextlib.html)
- [PEP 492 — Coroutines with async and await syntax](https://peps.python.org/pep-0492/)（异步上下文管理器）
- [Effective Python — Item 34: Use with Statements for Resource Management](https://effectivepython.com/)
- [Fluent Python — Chapter 15: Context Managers and else Blocks](https://www.oreilly.com/library/view/fluent-python/9781491946237/)
