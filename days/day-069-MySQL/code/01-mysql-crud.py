"""
Day 069 — MySQL 连接与 CRUD（含事务）
运行方式：
  python 01-mysql-crud.py               # 需要 MySQL 环境（环境变量配置连接）
  python 01-mysql-crud.py --self-test   # SQLite 内存库离线自检
"""
import os
import sqlite3
import sys


# ========== 双后端薄封装 ==========
# MySQL 用 %s 占位符，SQLite 用 ? —— 这个差异本身就是面试题

class DB:
    """极简 DB-API 封装：execute / commit / rollback / fetchall"""

    def __init__(self, conn, paramstyle):
        self.conn = conn
        self.paramstyle = paramstyle  # "format" | "qmark"

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        if self.paramstyle == "qmark":
            sql = sql.replace("%s", "?")
        cur.execute(sql, params)
        return cur

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def connect_sqlite():
    return DB(sqlite3.connect(":memory:"), "qmark")


def connect_mysql():
    import pymysql  # 仅真实环境需要
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "testdb"),
        charset="utf8mb4",
        autocommit=False,
    )
    return DB(conn, "format")


# ========== 业务逻辑（与后端无关） ==========

def setup(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               email TEXT UNIQUE
           )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS accounts (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               name TEXT NOT NULL,
               balance INTEGER NOT NULL DEFAULT 0
           )"""
    )
    db.commit()


def create_user(db, name, email):
    cur = db.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
    return cur.lastrowid


def get_user(db, user_id):
    cur = db.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
    return cur.fetchone()


def update_email(db, user_id, email):
    db.execute("UPDATE users SET email = %s WHERE id = %s", (email, user_id))


def delete_user(db, user_id):
    db.execute("DELETE FROM users WHERE id = %s", (user_id,))


def transfer(db, from_id, to_id, amount):
    """事务：转账两步要么全成，要么全不成"""
    try:
        db.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (amount, from_id))
        db.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (amount, to_id))
        db.commit()
    except Exception:
        db.rollback()
        raise


def demo(db):
    setup(db)
    uid = create_user(db, "alice", "alice@example.com")
    print("✅ 插入用户 id =", uid)
    update_email(db, uid, "alice@newmail.com")
    print("✅ 更新后:", get_user(db, uid))

    db.execute("INSERT INTO accounts (name, balance) VALUES (%s, %s)", ("A", 1000))
    db.execute("INSERT INTO accounts (name, balance) VALUES (%s, %s)", ("B", 0))
    db.commit()
    transfer(db, 1, 2, 300)
    cur = db.execute("SELECT name, balance FROM accounts ORDER BY id")
    print("✅ 转账后余额:", cur.fetchall())


# ========== 离线自检 ==========

def self_test():
    db = connect_sqlite()
    setup(db)

    uid = create_user(db, "bob", "bob@example.com")
    assert get_user(db, uid)[1] == "bob", "插入/查询失败"

    update_email(db, uid, "bob@x.com")
    assert get_user(db, uid)[2] == "bob@x.com", "更新失败"

    db.execute("INSERT INTO accounts (name, balance) VALUES (%s, %s)", ("A", 100))
    db.execute("INSERT INTO accounts (name, balance) VALUES (%s, %s)", ("B", 0))
    db.commit()
    transfer(db, 1, 2, 40)
    cur = db.execute("SELECT balance FROM accounts ORDER BY id")
    balances = [r[0] for r in cur.fetchall()]
    assert balances == [60, 40], f"转账结果错误: {balances}"

    # 异常路径：余额不足（CHECK 约束模拟）→ 必须回滚
    db.execute("DROP TABLE accounts")
    db.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY AUTOINCREMENT,"
               " name TEXT, balance INTEGER CHECK (balance >= 0))")
    db.execute("INSERT INTO accounts (name, balance) VALUES (%s, %s)", ("A", 10))
    db.execute("INSERT INTO accounts (name, balance) VALUES (%s, %s)", ("B", 0))
    db.commit()
    try:
        transfer(db, 1, 2, 100)
        assert False, "应当触发约束异常"
    except Exception:
        pass
    cur = db.execute("SELECT balance FROM accounts ORDER BY id")
    balances = [r[0] for r in cur.fetchall()]
    assert balances == [10, 0], f"回滚失败: {balances}"

    db.close()
    print("✅ self-test 全部通过（SQLite 离线自检）")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        demo(connect_mysql())
