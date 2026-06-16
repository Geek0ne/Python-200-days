#!/usr/bin/env python3
"""
Day 025 — 上下文管理器实战案例

涵盖：
1. 数据库连接池管理器
2. 精确计时器装饰器（多种计时模式）
3. 资源管理器（嵌套资源释放）
4. 临时目录切换（chdir 上下文）
5. 环境变量临时修改
6. 信号量 / 锁的上下文管理
7. 自定义日志上下文
8. 原子化 JSON 文件写入
9. 性能分析上下文
10. 综合案例：Web 请求会话管理器
"""

import contextlib
import time
import os
import json
import threading
import tempfile
import shutil
from functools import wraps


print("=" * 60)
print("实战 1：数据库连接池管理器")
print("=" * 60)


class Connection:
    """模拟数据库连接"""

    def __init__(self, conn_id, db_url):
        self.conn_id = conn_id
        self.db_url = db_url
        self.active = True
        print(f"  [创建] 连接 #{conn_id} ({db_url})")

    def execute(self, sql):
        if not self.active:
            raise RuntimeError(f"连接 #{self.conn_id} 已关闭！")
        print(f"  [执行] #{self.conn_id}: {sql[:50]}...")
        return f"结果 from #{self.conn_id}"

    def close(self):
        if self.active:
            self.active = False
            print(f"  [关闭] 连接 #{self.conn_id}")
        return self


class ConnectionPool:
    """简单的数据库连接池（上下文管理器）"""

    def __init__(self, db_url, min_size=2, max_size=5):
        self.db_url = db_url
        self.min_size = min_size
        self.max_size = max_size
        self._pool = []
        self._in_use = set()
        self._lock = threading.Lock()
        self._init_pool()

    def _init_pool(self):
        """初始化最小连接数"""
        for i in range(self.min_size):
            conn = Connection(i + 1, self.db_url)
            self._pool.append(conn)

    def acquire(self):
        """获取一个连接"""
        with self._lock:
            if self._pool:
                conn = self._pool.pop()
                self._in_use.add(conn.conn_id)
                return conn
            # 无可用连接时创建新连接
            if len(self._in_use) < self.max_size:
                conn_id = len(self._in_use) + len(self._pool) + 1
                if conn_id <= self.max_size:
                    conn = Connection(conn_id, self.db_url)
                    self._in_use.add(conn.conn_id)
                    return conn
            raise RuntimeError("连接池已满，无法获取连接")

    def release(self, conn):
        """释放连接回池中"""
        with self._lock:
            self._in_use.discard(conn.conn_id)
            if conn.active:
                self._pool.append(conn)
            print(f"  [归还] 连接 #{conn.conn_id} 回池")

    def close_all(self):
        """关闭所有连接"""
        for conn in self._pool:
            conn.close()
        self._pool.clear()
        self._in_use.clear()
        print("  [关闭] 连接池已销毁")

    def __enter__(self):
        """with pool as connection: 获取一个连接"""
        self._conn = self.acquire()
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release(self._conn)
        return False


# 使用连接池
print("--- 创建连接池 ---")
pool = ConnectionPool("postgresql://localhost/mydb", min_size=2)

print("\n--- 使用连接池的 with 语句 ---")
with pool as conn:
    result = conn.execute("SELECT * FROM users WHERE id = 1")
    print(f"  查询结果: {result}")

print("\n--- 再次获取连接 ---")
with pool as conn:
    result = conn.execute("INSERT INTO logs VALUES (...)")
    print(f"  插入结果: {result}")

print(f"\n--- 连接池状态 ---")
print(f"  池中空闲: {len(pool._pool)}, 使用中: {len(pool._in_use)}")

pool.close_all()


print()
print("=" * 60)
print("实战 2：精确计时器（装饰器 + 上下文管理器）")
print("=" * 60)


class Timer:
    """高精度计时器 — 同时支持上下文和装饰器模式

    支持多种时间模式：
      - perf_counter: 高精度挂钟时间（包括 sleep，默认）
      - process_time: CPU 时间（不包括 sleep）
      - monotonic: 单调递增时间（不受系统时钟调整影响）
    """

    mode_map = {
        "perf": time.perf_counter,
        "process": time.process_time,
        "monotonic": time.monotonic,
    }

    def __init__(self, name="Timer", mode="perf", logger=print):
        self.name = name
        self.time_func = self.mode_map.get(mode, time.perf_counter)
        self.logger = logger
        self.start = None
        self.elapsed = None

    # --- 上下文管理器模式 ---
    def __enter__(self):
        self.start = self.time_func()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = self.time_func() - self.start
        prefix = ""
        if exc_type:
            prefix = f" (异常: {exc_type.__name__})"
        self.logger(f"  ⌚ [{self.name}] 耗时 {self.elapsed*1000:.3f}ms{prefix}")
        return False

    # --- 装饰器模式 ---
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)
        return wrapper


# 上下文管理器方式
print("--- 上下文管理器方式 ---")
with Timer("数据加载"):
    data = [i ** 2 for i in range(1_000_000)]
print(f"  数据长度: {len(data)}")

# 装饰器方式
print("\n--- 装饰器方式 ---")


@Timer("数据处理", mode="process")
def process_data(n):
    total = 0
    for i in range(n):
        total += i ** 2
    return total


result = process_data(5_000_000)
print(f"  计算结果: {result}")


# 嵌套计时器
print("\n--- 嵌套计时器 ---")


def complex_operation():
    with Timer("阶段1") as t1:
        sum(range(1_000_000))

    with Timer("阶段2") as t2:
        sum(range(2_000_000))

    with Timer("阶段3") as t3:
        sum(range(500_000))

    return t1.elapsed + t2.elapsed + t3.elapsed


total_time = complex_operation()
print(f"  总耗时: {total_time*1000:.3f}ms")


print()
print("=" * 60)
print("实战 3：原子化 JSON 文件写入")
print("=" * 60)


class AtomicJSONWriter:
    """原子化 JSON 写入

    原理：
      1. 先写入临时文件
      2. 写入成功后，原子性重命名
      3. 如果中途出错，临时文件自动删除
      保证不会出现"半写"的损坏文件
    """

    def __init__(self, filepath, indent=2):
        self.filepath = filepath
        self.indent = indent
        self.temp_path = filepath + ".tmp"
        self.fp = None

    def __enter__(self):
        self.fp = open(self.temp_path, "w", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # 异常发生 → 删除临时文件
            self.fp.close()
            if os.path.exists(self.temp_path):
                os.remove(self.temp_path)
            print(f"  [回滚] 临时文件已删除（{exc_type.__name__}）")
            return False

        # 正常完成 → 写入 JSON 并重命名
        self.fp.close()
        os.replace(self.temp_path, self.filepath)  # 原子操作
        print(f"  [提交] 已写入 {self.filepath}")
        return False

    def write(self, data):
        """将数据写入临时文件"""
        json.dump(data, self.fp, ensure_ascii=False, indent=self.indent)
        self.fp.write("\n")


# 正常写入
print("--- 正常写入 ---")
data = {
    "name": "Python 学习",
    "days": list(range(1, 26)),
    "topics": ["变量", "函数", "类", "装饰器", "上下文管理器"],
}

writer = AtomicJSONWriter("/tmp/progress.json")
with writer:
    writer.write(data)

print("验证写入内容:")
with open("/tmp/progress.json") as f:
    print(f.read())

# 异常写入（模拟写入失败）
print("\n--- 异常写入（回滚）---")
try:
    writer2 = AtomicJSONWriter("/tmp/broken.json")
    with writer2:
        writer2.write({"status": "ok"})
        raise ValueError("磁盘空间不足！")
except ValueError:
    print("  回滚成功，临时文件已清理")

# 验证目标文件不存在
if not os.path.exists("/tmp/broken.json"):
    print("  ✓ broken.json 未创建（回滚成功）")


print()
print("=" * 60)
print("实战 4：临时工作目录（chdir 上下文）")
print("=" * 60)


@contextlib.contextmanager
def temp_working_dir(path=None):
    """临时切换工作目录

    - 如果 path=None，创建临时目录
    - 离开时自动恢复原目录
    - 临时目录自动清理（如果是创建的）
    """
    original_dir = os.getcwd()
    created_temp = False

    if path is None:
        path = tempfile.mkdtemp(prefix="py_working_")
        created_temp = True
        print(f"  [创建] 临时目录: {path}")
    else:
        os.makedirs(path, exist_ok=True)
        print(f"  [切换] 目录: {path}")

    try:
        os.chdir(path)
        yield path
    finally:
        os.chdir(original_dir)
        print(f"  [恢复] 原目录: {original_dir}")
        if created_temp:
            shutil.rmtree(path, ignore_errors=True)
            print(f"  [清理] 临时目录已删除")


print("--- 临时目录 ---")
with temp_working_dir() as work_dir:
    print(f"  当前目录: {os.getcwd()}")
    # 在临时目录中创建文件
    with open("test.txt", "w") as f:
        f.write("hello")
    print(f"  目录内容: {os.listdir('.')}")
print(f"  已回到: {os.getcwd()}")


print()
print("=" * 60)
print("实战 5：临时环境变量修改")
print("=" * 60)


@contextlib.contextmanager
def set_env(**environ):
    """临时设置环境变量

    使用方式：
      with set_env(DATABASE_URL="sqlite:///test.db", DEBUG="1"):
          ...
    """
    old_environ = dict(os.environ)
    os.environ.update(environ)
    try:
        yield
    finally:
        # 恢复旧的环境变量
        os.environ.clear()
        os.environ.update(old_environ)


print("--- 临时环境变量 ---")
print(f"  修改前 DATABASE_URL: {os.environ.get('DATABASE_URL', '未设置')}")

with set_env(DATABASE_URL="sqlite:///test.db", DEBUG="true"):
    print(f"  修改后 DATABASE_URL: {os.environ.get('DATABASE_URL')}")
    print(f"  修改后 DEBUG: {os.environ.get('DEBUG')}")

print(f"  恢复后 DATABASE_URL: {os.environ.get('DATABASE_URL', '未设置')}")


print()
print("=" * 60)
print("实战 6：锁的上下文管理")
print("=" * 60)


class Counter:
    """带锁的线程安全计数器"""

    def __init__(self):
        self.value = 0
        self.lock = threading.Lock()

    def increment(self):
        # threading.Lock 本身就是上下文管理器
        with self.lock:
            current = self.value
            # 模拟一些处理时间
            time.sleep(0.0001)
            self.value = current + 1
            return self.value

    def decrement(self):
        with self.lock:
            current = self.value
            time.sleep(0.0001)
            self.value = current - 1
            return self.value

    def get_value(self):
        # 读操作也需要锁，防止读脏数据
        with self.lock:
            return self.value


def worker(counter, n):
    """工作线程：执行 n 次递增"""
    for _ in range(n):
        counter.increment()


print("--- 线程安全计数器 ---")
counter = Counter()
threads = [threading.Thread(target=worker, args=(counter, 1000))
           for _ in range(5)]

for t in threads:
    t.start()
for t in threads:
    t.join()

print(f"  计数器值: {counter.get_value()} (期望: 5000)")


# 自定义锁包装
class RWLock:
    """读写锁（简化版）"""

    def __init__(self):
        self._lock = threading.Lock()
        self._readers = 0

    def read(self):
        """读锁上下文管理器"""
        return _ReadLock(self)

    def write(self):
        """写锁上下文管理器"""
        return _WriteLock(self)


class _ReadLock:
    def __init__(self, rwlock):
        self.rwlock = rwlock
    def __enter__(self):
        self.rwlock._lock.acquire()
        self.rwlock._readers += 1
        self.rwlock._lock.release()
        return self
    def __exit__(self, *args):
        self.rwlock._lock.acquire()
        self.rwlock._readers -= 1
        self.rwlock._lock.release()


class _WriteLock:
    def __init__(self, rwlock):
        self.rwlock = rwlock
    def __enter__(self):
        self.rwlock._lock.acquire()
        return self
    def __exit__(self, *args):
        self.rwlock._lock.release()


print()
print("=" * 60)
print("实战 7：自定义日志上下文（分级日志）")
print("=" * 60)


class LogContext:
    """日志上下文管理器 — 自动缩进和分组

    ```
    [INFO] 开始处理请求 (req-001)
      [DEBUG] 验证请求参数...
      [INFO] 执行数据库查询...
      [WARN] 查询耗时 > 1s
    [INFO] 请求处理完成
    ```
    """
    _indent = 0

    def __init__(self, message, level="INFO"):
        self.message = message
        self.level = level
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        self._log(f"▶ {self.message}")
        LogContext._indent += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        LogContext._indent -= 1
        elapsed = (time.perf_counter() - self.start_time) * 1000
        if exc_type:
            self._log(f"✗ {self.message} 失败 ({elapsed:.1f}ms) — {exc_type.__name__}")
        else:
            self._log(f"✓ {self.message} ({elapsed:.1f}ms)")
        return False

    @classmethod
    def _log(cls, message):
        indent = "  " * cls._indent
        print(f"{indent}[LOG] {message}")

    @classmethod
    def info(cls, message):
        cls._log(message)


print("--- 日志上下文 ---")
with LogContext("处理 HTTP 请求", "INFO"):
    LogContext.info("验证 token...")
    with LogContext("查询数据库", "DEBUG"):
        LogContext.info("执行 SELECT")
        time.sleep(0.05)
        LogContext.info("返回 3 条结果")
    with LogContext("组装响应", "DEBUG"):
        LogContext.info("JSON 序列化")
    LogContext.info("请求处理完成")


print()
print("=" * 60)
print("实战 8：性能分析上下文")
print("=" * 60)


import cProfile
import pstats
import io as io_module


class Profiler:
    """性能分析上下文管理器

    在 with 块内执行代码分析，退出时打印分析结果
    """

    def __init__(self, sort_by="cumtime", top_n=10):
        self.sort_by = sort_by
        self.top_n = top_n
        self.profiler = cProfile.Profile()

    def __enter__(self):
        self.profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profiler.disable()
        s = io_module.StringIO()
        ps = pstats.Stats(self.profiler, stream=s).sort_stats(self.sort_by)
        ps.print_stats(self.top_n)
        print("性能分析结果:")
        print(s.getvalue())
        return False


print("--- 性能分析 ---")
with Profiler(sort_by="time", top_n=5):
    def fib(n):
        if n <= 1:
            return n
        return fib(n - 1) + fib(n - 2)

    fib(30)


print()
print("=" * 60)
print("实战 9：重试上下文（自动重试失败操作）")
print("=" * 60)


class RetryContext:
    """自动重试上下文管理器

    当 with 块内抛出指定异常时，自动重试
    """

    def __init__(self, max_retries=3, delay=0.1, backoff=2.0,
                 exceptions=(Exception,)):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions
        self.attempts = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False  # 没有异常，正常退出

        if not issubclass(exc_type, self.exceptions):
            return False  # 不是要重试的异常类型

        self.attempts += 1
        if self.attempts >= self.max_retries:
            return False  # 已达到最大重试次数，让异常传播

        wait_time = self.delay * (self.backoff ** (self.attempts - 1))
        print(f"  [重试] 第 {self.attempts}/{self.max_retries} 次，等待 {wait_time:.2f}s...")
        time.sleep(wait_time)
        return True  # 抑制异常 → 重新执行 with 块


# 注意：__exit__ 返回 True 只是抑制异常，但不会自动重新进入 with 块
# 要实现真正的"重试"，需要更复杂的设计。
# 上面的实现实际效果是抑制异常让程序继续，而不是重新执行。
# 下面展示真正的重试模式：


class RetryExecutor:
    """真正的可重试执行器"""

    def __init__(self, max_retries=3, delay=0.1, backoff=2.0,
                 exceptions=(Exception,)):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff
        self.exceptions = exceptions

    def execute(self, func, *args, **kwargs):
        """执行函数并自动重试"""
        last_exc = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except self.exceptions as e:
                last_exc = e
                if attempt < self.max_retries:
                    wait = self.delay * (self.backoff ** (attempt - 1))
                    print(f"  [重试] 第 {attempt}/{self.max_retries} 次失败，"
                          f"等待 {wait:.2f}s... ({e})")
                    time.sleep(wait)
                else:
                    print(f"  [失败] 已达到最大重试次数")
        raise last_exc


# 模拟一个偶尔失败的操作
attempt_counter = {"count": 0}


def flaky_operation():
    attempt_counter["count"] += 1
    print(f"  尝试 #{attempt_counter['count']}...")
    if attempt_counter["count"] < 3:
        raise ConnectionError("网络连接超时")
    return "数据加载成功"


print("--- 自动重试 ---")
retryer = RetryExecutor(max_retries=4, delay=0.05, backoff=1.5)
try:
    result = retryer.execute(flaky_operation)
    print(f"  最终结果: {result}")
except ConnectionError as e:
    print(f"  所有重试失败: {e}")


print()
print("=" * 60)
print("实战 10：综合案例 — Web 请求会话管理器")
print("=" * 60)


class Response:
    """模拟 HTTP 响应"""

    def __init__(self, status_code, body, headers=None):
        self.status_code = status_code
        self.body = body
        self.headers = headers or {}

    def json(self):
        return json.loads(self.body)

    def text(self):
        return self.body


class Session:
    """模拟 HTTP 会话管理器

    功能：
      - 连接池管理（复用 HTTP 连接）
      - 自动重试（可配置）
      - 请求计时
      - 响应日志
      - 自动关闭
    """

    def __init__(self, base_url="", timeout=30, max_retries=3):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {
            "User-Agent": "Python-Learn/1.0",
            "Accept": "application/json",
        }
        self._connected = False

    def __enter__(self):
        print(f"  [会话] 打开 HTTP 会话 (timeout={self.timeout}s)")
        self._connected = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"  [会话] 关闭 HTTP 会话")
        self._connected = False
        if exc_type:
            print(f"  [会话] 发生时: {exc_type.__name__}: {exc_val}")
        return False

    def _ensure_connected(self):
        if not self._connected:
            raise RuntimeError("会话未打开，请使用 with 语句")

    def request(self, method, path, **kwargs):
        """模拟 HTTP 请求"""
        self._ensure_connected()
        url = self.base_url + path
        print(f"  [请求] {method} {url}")

        # 模拟网络延迟
        time.sleep(0.05)

        # 模拟响应
        return Response(
            status_code=200,
            body=json.dumps({"url": url, "method": method, "success": True}),
            headers={"Content-Type": "application/json"},
        )

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)


# 使用示例
print("--- 使用 Session ---")
with Session(base_url="https://api.example.com", timeout=10) as session:
    # 设置认证头
    session.headers["Authorization"] = "Bearer token123"

    # 发送 GET 请求
    resp = session.get("/users/1")
    data = resp.json()
    print(f"  响应: {data}")

    # 发送 POST 请求
    resp = session.post("/users", data={"name": "Alice"})
    print(f"  状态码: {resp.status_code}")

print("\n--- Session 嵌套其它上下文 ---")


def fetch_user_data(user_id):
    """综合使用多种上下文管理器来获取用户数据"""
    session = Session(base_url="https://api.example.com")

    with Timer(f"获取用户 {user_id}") as timer:
        with session:
            with LogContext("HTTP 请求"):
                session.headers["Authorization"] = "Bearer token"
                resp = session.get(f"/users/{user_id}")
                data = resp.json()

    return data, timer.elapsed


result, elapsed = fetch_user_data(42)
print(f"  耗时: {elapsed*1000:.1f}ms")


print()
print("✅ 所有实战案例执行完毕")
