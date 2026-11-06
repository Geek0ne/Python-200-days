"""
Day 072 — SQL 注入复现（仅本地 sqlite，教学演示）
运行方式：python 12-sql-injection-basics.py --self-test
"""
import sqlite3
import sys


def build_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, secret TEXT)")
    cur.executemany("INSERT INTO users (name, secret) VALUES (?, ?)",
                    [("alice", "alice-pwd"), ("bob", "bob-pwd")])
    conn.commit()
    return conn


# ========== ❌ 拼接构造 SQL：注入的根源 ==========

def login_unsafe(conn, username):
    sql = f"SELECT * FROM users WHERE name = '{username}'"
    cur = conn.execute(sql)
    return cur.fetchall(), sql


# ========== ✅ 参数化查询：数据永远只是数据 ==========

def login_safe(conn, username):
    sql = "SELECT * FROM users WHERE name = ?"
    cur = conn.execute(sql, (username,))
    return cur.fetchall(), sql


ATTACKS = [
    "' OR '1'='1",        # 引号闭合：绕过认证
    "alice' --",          # 注释截断
    "' UNION SELECT 1,2,3 --",   # UNION 探测
]


def self_test():
    conn = build_db()

    print("=== 拼接版：被 payload 打穿 ===")
    for payload in ATTACKS:
        rows, sql = login_unsafe(conn, payload)
        print(f"payload={payload!r}\n  SQL={sql}\n  命中 {len(rows)} 行: {rows}")

    # 致命一击：' OR '1'='1' 返回全表
    rows, _ = login_unsafe(conn, "' OR '1'='1")
    assert len(rows) == 2, f"注入应当打穿: {rows}"
    print("💀 注入成立：全表数据泄露")

    print("\n=== 参数化版：payload 失效 ===")
    for payload in ATTACKS:
        rows, sql = login_safe(conn, payload)
        print(f"payload={payload!r} → 命中 {len(rows)} 行")
        assert rows == [], f"参数化后不应命中: {rows}"
    print("✅ 参数化查询：输入只能是值，注入失效")

    # 正常用户不受影响
    rows, _ = login_safe(conn, "alice")
    assert len(rows) == 1 and rows[0][1] == "alice"

    conn.close()
    print("\n✅ self-test 全部通过")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        print(__doc__)
