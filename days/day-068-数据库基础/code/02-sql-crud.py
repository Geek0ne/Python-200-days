"""
Day 068 — SQL CRUD 操作详解
运行方式：python 02-sql-crud.py
"""
import sqlite3


def main():
    # 使用 with 语句自动管理连接
    with sqlite3.connect("crud_demo.db") as conn:
        conn.row_factory = sqlite3.Row  # 启用 Row 工厂
        cursor = conn.cursor()

        # ========== CREATE（创建表） ==========
        cursor.executescript("""
            -- 图书表
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                price REAL CHECK(price > 0),
                category TEXT DEFAULT '其他',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 索引
            CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
            CREATE INDEX IF NOT EXISTS idx_books_category ON books(category);
        """)
        print("✅ 表和索引创建成功")

        # ========== INSERT（插入数据） ==========
        # 单条插入
        cursor.execute(
            "INSERT INTO books (title, author, price, category) VALUES (?, ?, ?, ?)",
            ("Python编程", "张三", 59.9, "技术")
        )
        print(f"✅ 插入 1 条，ID: {cursor.lastrowid}")

        # 批量插入
        books = [
            ("JavaScript高级编程", "李四", 79.9, "技术"),
            ("百年孤独", "马尔克斯", 45.0, "小说"),
            ("活着", "余华", 35.0, "小说"),
            ("Python数据分析", "王五", 89.0, "技术"),
            ("三体", "刘慈欣", 56.0, "科幻"),
        ]
        cursor.executemany(
            "INSERT INTO books (title, author, price, category) VALUES (?, ?, ?, ?)",
            books
        )
        conn.commit()
        print(f"✅ 批量插入 {len(books)} 条")

        # ========== SELECT（查询数据） ==========
        print("\n" + "=" * 50)
        print("📚 所有图书：")
        cursor.execute("SELECT * FROM books")
        for book in cursor.fetchall():
            print(f"  [{book['id']}] {book['title']} - {book['author']} "
                  f"¥{book['price']} ({book['category']})")

        # 条件查询
        print("\n📖 技术类图书：")
        cursor.execute("SELECT * FROM books WHERE category = ?", ("技术",))
        for book in cursor.fetchall():
            print(f"  {book['title']} - ¥{book['price']}")

        # 价格范围查询
        print("\n💰 价格 40-60 元的图书：")
        cursor.execute("SELECT * FROM books WHERE price BETWEEN ? AND ?", (40, 60))
        for book in cursor.fetchall():
            print(f"  {book['title']} - ¥{book['price']}")

        # 模糊搜索
        print("\n🔍 搜索含'Python'的图书：")
        cursor.execute("SELECT * FROM books WHERE title LIKE ?", ("%Python%",))
        for book in cursor.fetchall():
            print(f"  {book['title']} - {book['author']}")

        # 排序
        print("\n📊 按价格从高到低：")
        cursor.execute("SELECT * FROM books ORDER BY price DESC")
        for book in cursor.fetchall():
            print(f"  ¥{book['price']:.1f} - {book['title']}")

        # 聚合查询
        print("\n📈 统计信息：")
        cursor.execute("SELECT COUNT(*), AVG(price), MAX(price), MIN(price) FROM books")
        stats = cursor.fetchone()
        print(f"  总数: {stats[0]}")
        print(f"  平均价: ¥{stats[1]:.2f}")
        print(f"  最高价: ¥{stats[2]:.2f}")
        print(f"  最低价: ¥{stats[3]:.2f}")

        # 分组统计
        print("\n📂 按分类统计：")
        cursor.execute("""
            SELECT category, COUNT(*) as count, AVG(price) as avg_price
            FROM books GROUP BY category ORDER BY count DESC
        """)
        for row in cursor.fetchall():
            print(f"  {row['category']}: {row['count']} 本, 均价 ¥{row['avg_price']:.2f}")

        # ========== UPDATE（更新数据） ==========
        print("\n" + "=" * 50)
        cursor.execute(
            "UPDATE books SET price = ? WHERE title = ?",
            (49.9, "活着")
        )
        conn.commit()
        print(f"✅ 更新《活着》价格，影响 {cursor.rowcount} 行")

        # ========== DELETE（删除数据） ==========
        cursor.execute("DELETE FROM books WHERE title = ?", ("三体",))
        conn.commit()
        print(f"✅ 删除《三体》，影响 {cursor.rowcount} 行")

        # 最终状态
        print("\n📋 最终图书列表：")
        cursor.execute("SELECT * FROM books")
        for book in cursor.fetchall():
            print(f"  [{book['id']}] {book['title']} ¥{book['price']}")


if __name__ == "__main__":
    main()
