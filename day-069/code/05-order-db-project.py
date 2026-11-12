"""
Day 069 — 实战：订单库设计与查询优化
运行方式：
  python 05-order-db-project.py --self-test   # SQLite 离线跑全流程
  python 05-order-db-project.py               # MySQL 环境实测（环境变量配置连接）
"""
import os
import random
import sqlite3
import sys
import time

SCHEMA = [
    """CREATE TABLE users (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           city TEXT
       )""",
    """CREATE TABLE products (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           price INTEGER NOT NULL
       )""",
    """CREATE TABLE orders (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER NOT NULL,
           created_at TEXT NOT NULL,
           status TEXT NOT NULL DEFAULT 'paid'
       )""",
    """CREATE TABLE order_items (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           order_id INTEGER NOT NULL,
           product_id INTEGER NOT NULL,
           quantity INTEGER NOT NULL,
           price INTEGER NOT NULL
       )""",
]

# 慢查询（初始写法）：子查询 + 非必要全列
SLOW_SQL = """
    SELECT o.id, o.created_at,
           (SELECT p.name FROM order_items oi
             JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = o.id LIMIT 1) AS first_product
    FROM orders o
    WHERE o.user_id = %s AND o.created_at >= %s
    ORDER BY o.created_at DESC
"""

# 优化写法：JOIN 一次取齐 + 只取需要的列（配合联合索引）
FAST_SQL = """
    SELECT o.id, o.created_at, p.name
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    JOIN products p ON p.id = oi.product_id
    WHERE o.user_id = %s AND o.created_at >= %s
    ORDER BY o.created_at DESC
"""

INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_orders_user_time ON orders(user_id, created_at)"


def connect_sqlite():
    conn = sqlite3.connect(":memory:")
    return conn, lambda s: s.replace("%s", "?")


def connect_mysql():
    import pymysql
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "testdb"),
        charset="utf8mb4",
    )
    return conn, lambda s: s


def seed(conn, adapt, n_users=20, n_products=10, n_orders=10000):
    cur = conn.cursor()
    for ddl in SCHEMA:
        cur.execute(adapt(ddl))
    cur.executemany("INSERT INTO users (name, city) VALUES (?, ?)",
                    [(f"user{i}", random.choice(["BJ", "SH", "SZ"])) for i in range(n_users)])
    cur.executemany("INSERT INTO products (name, price) VALUES (?, ?)",
                    [(f"product{i}", random.randint(10, 999)) for i in range(n_products)])
    orders, items = [], []
    for i in range(n_orders):
        uid = random.randint(1, n_users)
        day = random.randint(1, 30)
        orders.append((uid, f"2026-10-{day:02d}"))
        items.append((i + 1, random.randint(1, n_products), random.randint(1, 3), 100))
    cur.executemany("INSERT INTO orders (user_id, created_at) VALUES (?, ?)", orders)
    cur.executemany("INSERT INTO order_items (order_id, product_id, quantity, price)"
                    " VALUES (?, ?, ?, ?)", items)
    conn.commit()


def timed_query(conn, adapt, sql, params):
    cur = conn.cursor()
    t0 = time.perf_counter()
    cur.execute(adapt(sql), params)
    rows = cur.fetchall()
    return time.perf_counter() - t0, rows


def explain_text(conn, adapt, sql, params):
    cur = conn.cursor()
    prefix = "EXPLAIN QUERY PLAN " if isinstance(conn, sqlite3.Connection) else "EXPLAIN "
    cur.execute(adapt(prefix + sql), params)
    return " | ".join(str(r) for r in cur.fetchall())


def run_flow(conn, adapt):
    seed(conn, adapt)
    params = (1, "2026-10-01")

    t_slow, rows_slow = timed_query(conn, adapt, SLOW_SQL, params)
    plan_slow = explain_text(conn, adapt, SLOW_SQL, params)

    cur = conn.cursor()
    cur.execute(adapt(INDEX_SQL))
    conn.commit()

    t_fast, rows_fast = timed_query(conn, adapt, FAST_SQL, params)
    plan_fast = explain_text(conn, adapt, FAST_SQL, params)

    print(f"慢查询: {t_slow * 1000:.1f}ms, {len(rows_slow)} 行")
    print(f"  计划: {plan_slow}")
    print(f"优化后: {t_fast * 1000:.1f}ms, {len(rows_fast)} 行")
    print(f"  计划: {plan_fast}")
    return rows_slow, rows_fast, plan_slow, plan_fast


def self_test():
    conn, adapt = connect_sqlite()
    rows_slow, rows_fast, plan_slow, plan_fast = run_flow(conn, adapt)
    # 两条 SQL 语义等价：返回行数一致
    assert len(rows_slow) == len(rows_fast), (
        f"语义应一致: {len(rows_slow)} vs {len(rows_fast)}")
    # 索引应当出现在优化后的计划里
    assert "idx_orders_user_time" in plan_fast, f"应当命中联合索引: {plan_fast}"
    conn.close()
    print("✅ self-test 全部通过（建模 → 灌数 → 慢查询 → 索引优化 → 验证一致）")


def demo_mysql():
    conn, adapt = connect_mysql()
    run_flow(conn, adapt)
    conn.close()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo_mysql()
