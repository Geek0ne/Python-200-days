"""
Day 072 — 参数化查询的正确姿势（含 LIKE / IN / 动态排序）
运行方式：python 13-parameterized-queries.py --self-test
"""
import sqlite3
import sys


def build_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
    cur.executemany("INSERT INTO products (name, price) VALUES (?, ?)",
                    [("apple-pie", 30), ("banana", 10), ("cherry-cake", 50), ("date", 20)])
    conn.commit()
    return conn


# 1. LIKE：通配符作为参数的一部分，语句结构不变
def search(conn, keyword):
    return conn.execute(
        "SELECT * FROM products WHERE name LIKE ?",
        (f"%{keyword}%",),
    ).fetchall()


# 2. IN：占位符数量由代码生成，值仍然全部走参数
def by_ids(conn, ids):
    ids = list(ids)
    placeholders = ",".join("?" * len(ids))
    return conn.execute(
        f"SELECT * FROM products WHERE id IN ({placeholders})", ids
    ).fetchall()


# 3. 动态排序：字段名不能参数化 → 白名单映射
SORT_WHITELIST = {
    "price_asc": "price ASC",
    "price_desc": "price DESC",
    "name": "name ASC",
}


def sorted_products(conn, sort_key):
    order = SORT_WHITELIST.get(sort_key)
    if order is None:
        raise ValueError(f"非法排序参数: {sort_key}")
    return conn.execute(f"SELECT * FROM products ORDER BY {order}").fetchall()


def self_test():
    conn = build_db()

    rows = search(conn, "cake")
    assert [r[0] for r in rows] == [3], rows

    # 注入 payload 当 keyword：只能搜到"匹配这个字面值"的东西
    rows = search(conn, "' OR '1'='1")
    assert rows == [], f"LIKE 参数化后注入失效: {rows}"

    rows = by_ids(conn, [1, 3])
    assert [r[0] for r in rows] == [1, 3], rows

    rows = sorted_products(conn, "price_desc")
    assert [r[2] for r in rows] == [50, 30, 20, 10], rows

    try:
        sorted_products(conn, "price; DROP TABLE products")
        assert False, "白名单应拦截"
    except ValueError:
        pass

    # 表还在 = 白名单拦住了注入
    assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 4
    conn.close()
    print("✅ self-test 全部通过（LIKE / IN / 动态排序均安全）")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        print(__doc__)
