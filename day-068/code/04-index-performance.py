"""
Day 068 — 索引与性能对比
运行方式：python 04-index-performance.py
"""
import sqlite3
import time


def main():
    with sqlite3.connect("perf_demo.db") as conn:
        cursor = conn.cursor()

        # 创建表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT,
                price REAL
            )
        """)

        # 清空旧数据
        cursor.execute("DELETE FROM products")

        # 插入 10 万条测试数据
        print("正在插入 10 万条数据...")
        start = time.time()
        products = [
            (f"商品{i:06d}", f"分类{i % 100}", i * 0.1)
            for i in range(100_000)
        ]
        cursor.executemany(
            "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
            products
        )
        conn.commit()
        print(f"插入耗时: {time.time() - start:.2f}秒\n")

        # ========== 无索引查询 ==========
        print("=" * 50)
        print("📊 无索引查询性能测试")
        print("=" * 50)

        start = time.time()
        cursor.execute("SELECT * FROM products WHERE category = '分类50'")
        results = cursor.fetchall()
        no_index_time = time.time() - start
        print(f"查询结果: {len(results)} 条")
        print(f"耗时: {no_index_time:.4f}秒")

        # ========== 创建索引 ==========
        print(f"\n正在创建索引...")
        start = time.time()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON products(category)")
        conn.commit()
        print(f"索引创建耗时: {time.time() - start:.4f}秒")

        # ========== 有索引查询 ==========
        print(f"\n📊 有索引查询性能测试")
        print("=" * 50)

        start = time.time()
        cursor.execute("SELECT * FROM products WHERE category = '分类50'")
        results = cursor.fetchall()
        with_index_time = time.time() - start
        print(f"查询结果: {len(results)} 条")
        print(f"耗时: {with_index_time:.4f}秒")

        # ========== 性能对比 ==========
        print(f"\n📊 性能对比")
        print("=" * 50)
        print(f"无索引: {no_index_time:.4f}秒")
        print(f"有索引: {with_index_time:.4f}秒")
        if with_index_time > 0:
            speedup = no_index_time / with_index_time
            print(f"加速比: {speedup:.1f}倍")

        # ========== 多条件查询 ==========
        print(f"\n📊 多条件查询测试")
        print("=" * 50)

        # 创建组合索引
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_cat_price "
            "ON products(category, price)"
        )
        conn.commit()

        start = time.time()
        cursor.execute(
            "SELECT * FROM products WHERE category = '分类50' AND price > 5"
        )
        results = cursor.fetchall()
        print(f"多条件查询: {len(results)} 条, 耗时 {time.time() - start:.4f}秒")

        # ========== 查看索引信息 ==========
        print(f"\n📊 表的索引信息")
        print("=" * 50)
        cursor.execute("PRAGMA index_list(products)")
        for idx in cursor.fetchall():
            idx_name = idx[1]
            cursor.execute(f"PRAGMA index_info({idx_name})")
            cols = [info[2] for info in cursor.fetchall()]
            print(f"  索引 {idx_name}: {', '.join(cols)}")


if __name__ == "__main__":
    main()
