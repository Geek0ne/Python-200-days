"""
Day 072 — ORM 注入对照实验：text() 拼接 vs text() 占位符 vs 列表达式
运行方式：python 14-orm-injection-defense.py --self-test
说明：用 sqlite3 模拟三种写法的等价语义，不需要 SQLAlchemy 即可理解差异。
      真实 SQLAlchemy 写法见 README 对照表。
"""
import sqlite3
import sys


def build_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, role TEXT)")
    cur.executemany("INSERT INTO users (name, role) VALUES (?, ?)",
                    [("alice", "admin"), ("bob", "guest")])
    conn.commit()
    return conn


# 写法 A：text() 裸写拼接 —— ❌ 危险（等价于 session.execute(text(f"..."))）
def find_by_name_text_concat(conn, name):
    sql = f"SELECT * FROM users WHERE name = '{name}'"   # 真实代码里这里是 text(f"...")
    return conn.execute(sql).fetchall()


# 写法 B：text() + 占位符 —— ✅（等价于 text("... WHERE name = :name")）
def find_by_name_text_param(conn, name):
    sql = "SELECT * FROM users WHERE name = ?"           # 真实代码：text("... :name"), {"name": name}
    return conn.execute(sql, (name,)).fetchall()


# 写法 C：列表达式 —— ✅（等价于 session.query(User).filter(User.name == name)）
def find_by_name_column_expr(conn, name):
    return conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchall()


PAYLOAD = "' OR '1'='1"


def self_test():
    conn = build_db()

    a = find_by_name_text_concat(conn, PAYLOAD)
    assert len(a) == 2, f"A 应被打穿: {a}"
    print("💀 A（text 拼接）被注入，泄露:", a)

    b = find_by_name_text_param(conn, PAYLOAD)
    assert b == [], f"B 不应被注入: {b}"
    print("✅ B（text 占位符）安全")

    c = find_by_name_column_expr(conn, PAYLOAD)
    assert c == [], f"C 不应被注入: {c}"
    print("✅ C（列表达式）安全")

    # 正常查询三者等价
    for fn in (find_by_name_text_concat, find_by_name_text_param, find_by_name_column_expr):
        assert len(fn(conn, "alice")) == 1

    conn.close()
    print("✅ self-test 全部通过（对照结论：ORM 不是护身符，写法才是）")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        print(__doc__)
