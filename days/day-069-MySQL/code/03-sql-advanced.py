"""
Day 069 — SQL 进阶：连接查询 / 子查询 / EXPLAIN
运行方式：
  python 03-sql-advanced.py --self-test   # SQLite 离线自检（含 EXPLAIN QUERY PLAN）
  python 03-sql-advanced.py               # 打印示例 SQL 与要点
"""
import sqlite3
import sys


SCHEMA = [
    """CREATE TABLE users (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL,
           city TEXT
       )""",
    """CREATE TABLE orders (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           user_id INTEGER NOT NULL,
           amount INTEGER NOT NULL,
           created_at TEXT,
           FOREIGN KEY (user_id) REFERENCES users(id)
       )""",
]

SEED = [
    ("INSERT INTO users (name, city) VALUES (%s, %s)", [("alice", "BJ"), ("bob", "SH"), ("carol", "BJ")]),
    ("INSERT INTO orders (user_id, amount, created_at) VALUES (%s, %s, %s)",
     [(1, 100, "2026-11-01"), (1, 250, "2026-11-03"), (2, 80, "2026-11-02")]),
]


def build_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    for ddl in SCHEMA:
        cur.execute(ddl)
    for sql, rows in SEED:
        for row in rows:
            cur.execute(sql.replace("%s", "?"), row)
    conn.commit()
    return conn


# ========== 1. 连接查询 ==========

INNER_JOIN = """
    SELECT o.id, u.name, o.amount
    FROM orders o
    INNER JOIN users u ON o.user_id = u.id
    ORDER BY o.id
"""

LEFT_JOIN = """
    SELECT u.name, COUNT(o.id) AS order_cnt, COALESCE(SUM(o.amount), 0) AS total
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    GROUP BY u.id
    ORDER BY u.name
"""


# ========== 2. 子查询 ==========

SUBQUERY_GT_AVG = """
    SELECT id, amount FROM orders
    WHERE amount > (SELECT AVG(amount) FROM orders)
    ORDER BY id
"""

# 等价的 JOIN 写法（多数情况更易优化）
JOIN_GT_AVG = """
    SELECT o.id, o.amount
    FROM orders o
    JOIN (SELECT AVG(amount) AS avg_amount FROM orders) a
      ON o.amount > a.avg_amount
    ORDER BY o.id
"""


# ========== 3. EXPLAIN ==========

def explain(conn, sql, params=()):
    cur = conn.cursor()
    if params:
        sql = sql.replace("%s", "?")
    cur.execute("EXPLAIN QUERY PLAN " + sql, params)
    return cur.fetchall()


def demo():
    for name, sql in [("INNER JOIN", INNER_JOIN), ("LEFT JOIN + 聚合", LEFT_JOIN),
                      ("子查询", SUBQUERY_GT_AVG), ("JOIN 等价改写", JOIN_GT_AVG)]:
        print(f"--- {name} ---")
        print(sql.strip())
        print()


def self_test():
    conn = build_db()
    cur = conn.cursor()

    cur.execute(INNER_JOIN)
    rows = cur.fetchall()
    assert len(rows) == 3, f"INNER JOIN 应返回 3 行订单: {rows}"

    cur.execute(LEFT_JOIN)
    rows = cur.fetchall()
    # carol 无订单也必须出现（LEFT JOIN 的语义）
    names = [r[0] for r in rows]
    assert names == ["alice", "bob", "carol"], f"LEFT JOIN 结果错误: {rows}"
    assert rows[2][1] == 0, f"carol 订单数应为 0: {rows[2]}"

    cur.execute(SUBQUERY_GT_AVG)
    rows = cur.fetchall()
    # 平均值 143.3，应只有 250 的订单
    assert [r[1] for r in rows] == [250], f"子查询结果错误: {rows}"

    cur.execute(JOIN_GT_AVG)
    rows2 = cur.fetchall()
    assert rows2 == rows, "JOIN 改写应与子查询结果一致"

    # EXPLAIN：无索引时 user_id 查询应显示扫描
    plan = explain(conn, "SELECT * FROM orders WHERE user_id = %s", (1,))
    text = " ".join(str(p) for p in plan)
    print("无索引计划:", text)
    assert "SCAN" in text or "SEARCH" in text

    # 加索引后应当走 SEARCH
    cur.execute("CREATE INDEX idx_orders_user ON orders(user_id, created_at)")
    plan2 = explain(conn, "SELECT * FROM orders WHERE user_id = %s", (1,))
    text2 = " ".join(str(p) for p in plan2)
    print("有索引计划:", text2)
    assert "idx_orders_user" in text2, f"应当命中索引: {text2}"

    conn.close()
    print("✅ self-test 全部通过")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo()
