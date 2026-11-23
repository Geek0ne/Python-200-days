"""
Day 068 — SQLite3 基础操作
运行方式：python 01-sqlite3-basics.py
"""
import sqlite3


def main():
    # ========== 1. 连接数据库 ==========
    # connect() 会创建文件（如果不存在）
    # 数据库文件就是当前目录下的 example.db
    conn = sqlite3.connect("example.db")
    cursor = conn.cursor()
    print("✅ 数据库连接成功")

    # ========== 2. 创建表 ==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT
        )
    """)
    conn.commit()
    print("✅ 表创建成功")

    # ========== 3. 插入数据 ==========
    # 参数化查询：? 是占位符，值通过第二个参数传入
    cursor.execute(
        "INSERT INTO users (name, age, email) VALUES (?, ?, ?)",
        ("张三", 25, "zhangsan@email.com")
    )
    print(f"✅ 插入成功，ID: {cursor.lastrowid}")

    # 批量插入
    users = [
        ("李四", 30, "lisi@email.com"),
        ("王五", 28, "wangwu@email.com"),
        ("赵六", 35, "zhaoliu@email.com"),
    ]
    cursor.executemany(
        "INSERT INTO users (name, age, email) VALUES (?, ?, ?)",
        users
    )
    conn.commit()
    print(f"✅ 批量插入 {len(users)} 条记录")

    # ========== 4. 查询数据 ==========
    # fetchone() 返回一条
    cursor.execute("SELECT * FROM users WHERE name = ?", ("张三",))
    row = cursor.fetchone()
    print(f"\n查询张三: {row}")

    # fetchall() 返回所有
    cursor.execute("SELECT * FROM users ORDER BY age")
    all_users = cursor.fetchall()
    print(f"\n所有用户（按年龄排序）:")
    for user in all_users:
        print(f"  ID={user[0]}, 姓名={user[1]}, 年龄={user[2]}, 邮箱={user[3]}")

    # 条件查询
    cursor.execute("SELECT * FROM users WHERE age > ?", (28,))
    older_users = cursor.fetchall()
    print(f"\n年龄大于 28 的用户: {len(older_users)} 人")

    # ========== 5. 更新数据 ==========
    cursor.execute(
        "UPDATE users SET age = ? WHERE name = ?",
        (26, "张三")
    )
    conn.commit()
    print(f"\n✅ 更新了 {cursor.rowcount} 条记录")

    # ========== 6. 删除数据 ==========
    cursor.execute("DELETE FROM users WHERE name = ?", ("赵六",))
    conn.commit()
    print(f"✅ 删除了 {cursor.rowcount} 条记录")

    # ========== 7. 统计查询 ==========
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\n剩余用户数: {count}")

    # ========== 8. 关闭连接 ==========
    conn.close()
    print("\n✅ 数据库连接已关闭")


if __name__ == "__main__":
    main()
