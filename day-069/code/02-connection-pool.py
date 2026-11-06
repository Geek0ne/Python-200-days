"""
Day 069 — 手写线程安全连接池
运行方式：
  python 02-connection-pool.py --self-test   # SQLite 连接池离线自检
  python 02-connection-pool.py               # MySQL 环境基准对比
"""
import queue
import sqlite3
import sys
import threading
import time


class SimpleConnectionPool:
    """线程安全连接池：借出 / 归还 / 超时 / 无效连接剔除

    生产环境请用 SQLAlchemy QueuePool / DBUtils，这里手写是为了理解原理。
    """

    def __init__(self, factory, max_size=5, timeout=3):
        self._factory = factory          # 无参可调用，返回一个新连接
        self._pool = queue.Queue(maxsize=max_size)
        self._max_size = max_size
        self._timeout = timeout
        self._created = 0
        self._lock = threading.Lock()
        self.reused = 0                  # 复用计数（演示用）

    def getconn(self):
        try:
            conn = self._pool.get_nowait()
            self.reused += 1
            return conn
        except queue.Empty:
            pass
        with self._lock:
            if self._created < self._max_size:
                self._created += 1
                return self._factory()
        # 池满：等待归还
        try:
            conn = self._pool.get(timeout=self._timeout)
            self.reused += 1
            return conn
        except queue.Empty:
            raise TimeoutError("连接池耗尽，等待超时")

    def putconn(self, conn, discard=False):
        if discard:
            with self._lock:
                self._created -= 1
            try:
                conn.close()
            except Exception:
                pass
            return
        self._pool.put(conn)

    def closeall(self):
        while not self._pool.empty():
            conn = self._pool.get()
            try:
                conn.close()
            except Exception:
                pass
        with self._lock:
            self._created = 0


def benchmark(pool, worker_sql, n_workers=10, n_queries=100):
    """并发借还，统计总耗时与复用次数"""

    def work():
        for _ in range(n_queries):
            conn = pool.getconn()
            try:
                cur = conn.cursor()
                cur.execute(worker_sql)
                cur.fetchall()
            finally:
                pool.putconn(conn)

    threads = [threading.Thread(target=work) for _ in range(n_workers)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.perf_counter() - t0, pool.reused


def self_test():
    def factory():
        return sqlite3.connect(":memory:")

    pool = SimpleConnectionPool(factory, max_size=3, timeout=1)

    # 基本借还
    c1 = pool.getconn()
    c2 = pool.getconn()
    assert pool._created == 2
    pool.putconn(c1)
    c3 = pool.getconn()
    assert c3 is c1, "应当复用归还的连接"
    pool.putconn(c2)
    pool.putconn(c3)

    # discard 路径
    c4 = pool.getconn()
    pool.putconn(c4, discard=True)
    assert pool._created == 1, "丢弃后应释放创建额度（2 → 1）"

    # 超时路径：3 个连接全借出后，第 4 个应当超时
    holders = [pool.getconn() for _ in range(3)]
    try:
        pool.getconn()
        assert False, "应当超时"
    except TimeoutError:
        pass
    for c in holders:
        pool.putconn(c)

    # 并发借还不崩 + 有复用
    pool.closeall()
    pool = SimpleConnectionPool(factory, max_size=3, timeout=2)
    elapsed, reused = benchmark(pool, "SELECT 1", n_workers=8, n_queries=50)
    assert reused > 0, "应当发生连接复用"
    print(f"✅ 并发基准: 8 线程 × 50 次查询, 耗时 {elapsed:.3f}s, 复用 {reused} 次")
    pool.closeall()
    print("✅ self-test 全部通过")


def demo_mysql():
    import pymysql

    def factory():
        return pymysql.connect(host="127.0.0.1", user="root",
                               password="", database="testdb", charset="utf8mb4")

    pool = SimpleConnectionPool(factory, max_size=5, timeout=3)
    t, reused = benchmark(pool, "SELECT 1", n_workers=10, n_queries=100)
    print(f"有连接池: {t:.3f}s, 复用 {reused} 次")

    t0 = time.perf_counter()
    for _ in range(200):
        conn = factory()
        conn.cursor().execute("SELECT 1")
        conn.close()
    print(f"无连接池(200 次): {time.perf_counter() - t0:.3f}s")
    pool.closeall()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo_mysql()
