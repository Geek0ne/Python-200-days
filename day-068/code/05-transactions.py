"""
Day 068 — 事务管理详解
运行方式：python 05-transactions.py
"""
import sqlite3


def main():
    # ========== 1. 基本事务 ==========
    print("=" * 50)
    print("💰 银行转账事务示例")
    print("=" * 50)

    with sqlite3.connect("bank.db") as conn:
        cursor = conn.cursor()

        # 创建账户表
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY,
                name TEXT,
                balance REAL DEFAULT 0
            );
            DELETE FROM accounts;
        """)
        cursor.executemany(
            "INSERT INTO accounts VALUES (?, ?, ?)",
            [(1, "张三", 1000), (2, "李四", 500), (3, "王五", 200)]
        )
        conn.commit()

        # 显示初始余额
        def show_balances():
            cursor.execute("SELECT name, balance FROM accounts ORDER BY id")
            for row in cursor.fetchall():
                print(f"  {row[0]}: ¥{row[1]:.2f}")

        print("初始余额:")
        show_balances()

        # ========== 正常转账 ==========
        print("\n--- 转账: 张三 → 李四 100 元 ---")
        try:
            cursor.execute(
                "UPDATE accounts SET balance = balance - 100 WHERE id = 1"
            )
            cursor.execute(
                "UPDATE accounts SET balance = balance + 100 WHERE id = 2"
            )
            conn.commit()
            print("✅ 转账成功")
        except Exception as e:
            conn.rollback()
            print(f"❌ 转账失败: {e}")

        print("转账后余额:")
        show_balances()

        # ========== 失败的转账（模拟错误） ==========
        print("\n--- 转账: 李四 → 王五 500 元（模拟失败） ---")
        try:
            cursor.execute(
                "UPDATE accounts SET balance = balance - 500 WHERE id = 2"
            )
            # 模拟第二步出错
            raise Exception("网络超时，转账失败")
            cursor.execute(
                "UPDATE accounts SET balance = balance + 500 WHERE id = 3"
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ 转账失败，已回滚: {e}")

        print("回滚后余额:")
        show_balances()

        # ========== 余额不足 ==========
        print("\n--- 转账: 王五 → 张三 500 元（余额不足） ---")
        try:
            cursor.execute(
                "UPDATE accounts SET balance = balance - 500 WHERE id = 3"
            )
            if cursor.rowcount == 0:
                raise Exception("账户不存在")
            cursor.execute(
                "UPDATE accounts SET balance = balance + 500 WHERE id = 1"
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"❌ 转账失败，已回滚: {e}")

        print("最终余额:")
        show_balances()

    # ========== 2. 使用 try-except-finally ==========
    print("\n" + "=" * 50)
    print("🔧 try-except-finally 模式")
    print("=" * 50)

    conn = sqlite3.connect("manual.db")
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("INSERT INTO notes (content) VALUES (?)", ("第一条笔记",))
        cursor.execute("INSERT INTO notes (content) VALUES (?)", ("第二条笔记",))
        conn.commit()
        print("✅ 两条笔记插入成功")

        # 验证数据
        cursor.execute("SELECT * FROM notes")
        for row in cursor.fetchall():
            print(f"  [{row[0]}] {row[1]}")

    except Exception as e:
        conn.rollback()
        print(f"❌ 操作失败，已回滚: {e}")
    finally:
        conn.close()
        print("🔒 连接已关闭")

    # ========== 3. 嵌套事务 ==========
    print("\n" + "=" * 50)
    print("📌 savepoint（保存点）")
    print("=" * 50)

    with sqlite3.connect("savepoint.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        cursor.execute("DELETE FROM items")

        # 第一批数据
        cursor.executemany(
            "INSERT INTO items (name) VALUES (?)",
            [("苹果",), ("香蕉",), ("橘子",)]
        )

        # 创建保存点
        cursor.execute("SAVEPOINT sp1")

        # 第二批数据
        cursor.executemany(
            "INSERT INTO items (name) VALUES (?)",
            [("西瓜",), ("葡萄",)]
        )

        # 回滚到保存点（丢弃第二批）
        cursor.execute("ROLLBACK TO SAVEPOINT sp1")

        conn.commit()

        # 查看结果——只有第一批
        cursor.execute("SELECT * FROM items")
        print("保存点回滚后的数据:")
        for row in cursor.fetchall():
            print(f"  [{row[0]}] {row[1]}")
        # 结果：苹果、香蕉、橘子（西瓜、葡萄被丢弃）


if __name__ == "__main__":
    main()
