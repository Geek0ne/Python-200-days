# Day 025 — 上下文管理器 🎯

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

### 思考题 3：ExitStack 的设计意图

假设你有以下场景：

```python
files = ["a.txt", "b.txt", "c.txt"]
# 想同时打开所有文件并处理
```

1. 用 `with open(f1) as a, open(f2) as b, ...` 有什么问题？
2. `ExitStack` 如何解决这个问题？
3. 如果中间一个文件打开失败，已经打开的文件应该怎么处理？

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

---

## 📚 参考资料

- [PEP 343 — The "with" Statement](https://peps.python.org/pep-0343/)
- [Python 官方文档 — With Statement Context Managers](https://docs.python.org/3/reference/datamodel.html#context-managers)
- [Python 官方文档 — contextlib](https://docs.python.org/3/library/contextlib.html)
- [PEP 492 — Coroutines with async and await syntax](https://peps.python.org/pep-0492/)（异步上下文管理器）
- [Effective Python — Item 34: Use with Statements for Resource Management](https://effectivepython.com/)
- [Fluent Python — Chapter 15: Context Managers and else Blocks](https://www.oreilly.com/library/view/fluent-python/9781491946237/)
