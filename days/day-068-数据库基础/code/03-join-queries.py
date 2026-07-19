"""
Day 068 — JOIN 联表查询详解
运行方式：python 03-join-queries.py
"""
import sqlite3


def main():
    with sqlite3.connect("join_demo.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # ========== 创建表结构 ==========
        cursor.executescript("""
            -- 用户表
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT
            );

            -- 订单表
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                product TEXT NOT NULL,
                amount REAL NOT NULL,
                order_date DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            -- 清空旧数据
            DELETE FROM orders;
            DELETE FROM users;

            -- 插入测试数据
            INSERT INTO users VALUES (1, '张三', 'zhang@email.com');
            INSERT INTO users VALUES (2, '李四', 'li@email.com');
            INSERT INTO users VALUES (3, '王五', 'wang@email.com');
            INSERT INTO users VALUES (4, '赵六', 'zhao@email.com');

            INSERT INTO orders VALUES (1, 1, 'Python书', 59.9, '2024-01-01');
            INSERT INTO orders VALUES (2, 1, '键盘', 199.0, '2024-01-02');
            INSERT INTO orders VALUES (3, 2, '显示器', 1299.0, '2024-01-03');
            INSERT INTO orders VALUES (4, 2, '鼠标', 89.0, '2024-01-04');
            INSERT INTO orders VALUES (5, 3, '耳机', 299.0, '2024-01-05');
        """)

        # ========== INNER JOIN ==========
        # 只返回两个表都能匹配的行
        print("=" * 50)
        print("🔗 INNER JOIN（内连接）")
        print("只显示有订单的用户：")
        cursor.execute("""
            SELECT users.name, orders.product, orders.amount
            FROM users
            INNER JOIN orders ON users.id = orders.user_id
        """)
        for row in cursor.fetchall():
            print(f"  {row['name']} 买了 {row['product']} (¥{row['amount']})")
        # 注意：赵六没有订单，不会出现

        # ========== LEFT JOIN ==========
        # 返回左表所有行，右表无匹配则填 NULL
        print("\n" + "=" * 50)
        print("🔗 LEFT JOIN（左连接）")
        print("显示所有用户（包括没有订单的）：")
        cursor.execute("""
            SELECT users.name, orders.product, orders.amount
            FROM users
            LEFT JOIN orders ON users.id = orders.user_id
        """)
        for row in cursor.fetchall():
            product = row['product'] or "无订单"
            amount = row['amount'] or 0
            print(f"  {row['name']}: {product} (¥{amount})")
        # 赵六也会出现，product 显示为"无订单"

        # ========== 多表 JOIN ==========
        print("\n" + "=" * 50)
        print("🔗 多表 JOIN")
        print("用户 + 订单 + 邮箱：")
        cursor.execute("""
            SELECT users.name, users.email, orders.product, orders.amount
            FROM users
            INNER JOIN orders ON users.id = orders.user_id
            ORDER BY users.name, orders.amount DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row['name']} ({row['email']}): "
                  f"{row['product']} ¥{row['amount']}")

        # ========== 聚合 + JOIN ==========
        print("\n" + "=" * 50)
        print("📊 每个用户的总消费（LEFT JOIN + GROUP BY）：")
        cursor.execute("""
            SELECT 
                users.name,
                COUNT(orders.id) as order_count,
                COALESCE(SUM(orders.amount), 0) as total_spent
            FROM users
            LEFT JOIN orders ON users.id = orders.user_id
            GROUP BY users.id
            ORDER BY total_spent DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row['name']}: {row['order_count']} 笔订单, "
                  f"总消费 ¥{row['total_spent']:.2f}")

        # ========== 子查询 ==========
        print("\n" + "=" * 50)
        print("🔍 子查询：消费超过 200 元的用户：")
        cursor.execute("""
            SELECT name FROM users
            WHERE id IN (
                SELECT user_id FROM orders
                GROUP BY user_id
                HAVING SUM(amount) > 200
            )
        """)
        for row in cursor.fetchall():
            print(f"  {row['name']}")

        # ========== 自连接 ==========
        print("\n" + "=" * 50)
        print("📊 商品价格对比（自连接）：")
        cursor.execute("""
            SELECT 
                a.product as 商品A,
                b.product as 商品B,
                a.amount as 价格A,
                b.amount as 价格B,
                ABS(a.amount - b.amount) as 差价
            FROM orders a
            INNER JOIN orders b ON a.user_id = b.user_id AND a.id < b.id
            ORDER BY 差价
        """)
        for row in cursor.fetchall():
            print(f"  {row['商品A']} (¥{row['价格A']}) vs "
                  f"{row['商品B']} (¥{row['价格B']}) = 差价 ¥{row['差价']:.1f}")


if __name__ == "__main__":
    main()
