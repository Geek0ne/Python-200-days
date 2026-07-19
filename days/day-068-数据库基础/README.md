# Day 068 — 数据库基础：SQLite3 与 SQL 入门

## 概述

Day 067 我们学习了 FastAPI，知道了 Web API 需要存储数据。今天来学习**数据存储的基石**——**数据库**。

Python 内置了 `sqlite3` 模型，无需安装任何第三方库就能操作数据库。SQLite 是一个**文件型数据库**，整个数据库就是一个 `.db` 文件，非常适合学习和小型应用。

**今天你将学到：**
1. SQLite3 模块——Python 内置的数据库引擎
2. SQL 基础——CRUD（增删改查）、JOIN（联表查询）、索引
3. 连接池与事务管理——确保数据安全
4. **实战：通讯录管理系统**——一个完整的数据库应用

> 💡 **为什么学 SQL？** 即使你以后用 ORM（Day 069），理解底层 SQL 也能帮你写出更好的代码，调试更快，性能优化更精准。

---

## 1. SQLite3 模块

### 1.1 什么是 SQLite？

SQLite 是一个**嵌入式关系型数据库**：

- **无需服务器**：不像 MySQL/PostgreSQL 需要单独运行服务进程
- **文件型数据库**：整个数据库就是一个 `.db` 文件
- **零配置**：不需要安装、配置、用户管理
- **跨平台**：Windows/Mac/Linux 通用
- **Python 内置**：`import sqlite3` 就能用

```python
# SQLite vs 其他数据库
# MySQL/PostgreSQL: 需要安装 → 启动服务 → 创建用户 → 配置权限
# SQLite: import sqlite3 → conn = sqlite3.connect("data.db") → 完成！
```

### 1.2 连接数据库

```python
# code/01-sqlite3-basics.py
import sqlite3

# 连接数据库（文件不存在会自动创建）
conn = sqlite3.connect("example.db")

# 获取游标——执行 SQL 的工具
cursor = conn.cursor()

# 执行 SQL
cursor.execute("SELECT 1 + 1 AS result")
row = cursor.fetchone()  # 获取一行
print(row)  # (2,)

# 关闭连接
conn.close()
```

### 1.3 使用 with 语句管理连接

```python
# 推荐写法——自动管理连接
with sqlite3.connect("example.db") as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT 1 + 1 AS result")
    print(cursor.fetchone())  # (2,)
# 离开 with 块时自动关闭连接
```

### 1.4 Row 工厂——按列名访问

```python
# 默认访问方式：cursor[0], cursor[1]...（按索引）
row = cursor.fetchone()
print(row[0])  # 不直观

# 使用 Row 工厂——按列名访问
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT * FROM users")
row = cursor.fetchone()
print(row["name"])  # ✅ 直观！
print(dict(row))    # 转为字典
```

### 1.5 常见游标方法

```python
cursor.execute(sql, params)  # 执行单条 SQL
cursor.executemany(sql, params_list)  # 执行多条 SQL（批量操作）
cursor.fetchone()   # 获取一行（返回 tuple 或 Row）
cursor.fetchall()   # 获取所有行（返回 list）
cursor.fetchmany(n) # 获取 n 行
cursor.lastrowid    # 最后插入行的 ID（INSERT 后使用）
cursor.rowcount     # 受影响的行数
```

> ⚠️ **避坑指南**：`fetchone()` 返回的是 tuple，不是字典！要用 `conn.row_factory = sqlite3.Row` 才能按列名访问。

---

## 2. SQL 基础

### 2.1 创建表（CREATE TABLE）

```python
# code/02-sql-crud.py
import sqlite3

# ========== 创建表 ==========
with sqlite3.connect("contacts.db") as conn:
    cursor = conn.cursor()

    # 创建通讯录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            category TEXT DEFAULT '朋友',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # CREATE TABLE IF NOT EXISTS: 表已存在则跳过（不会报错）
    # PRIMARY KEY AUTOINCREMENT: 自增主键
    # NOT NULL: 非空约束
    # DEFAULT: 默认值

    # 创建索引（加速查询）
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_contacts_name 
        ON contacts(name)
    """)
    # 索引加速按 name 查询，但会稍微降低写入速度

    conn.commit()  # 提交事务——必须调用！
    print("✅ 表创建成功")
```

### 2.2 插入数据（INSERT）

```python
# ========== 插入数据 ==========
with sqlite3.connect("contacts.db") as conn:
    cursor = conn.cursor()

    # 单条插入——使用参数化查询（防 SQL 注入！）
    cursor.execute(
        "INSERT INTO contacts (name, phone, email, category) VALUES (?, ?, ?, ?)",
        ("张三", "13800138000", "zhangsan@email.com", "同事")
    )
    # ⚠️ 千万不要这样写！（SQL 注入风险）
    # cursor.execute(f"INSERT INTO contacts VALUES ('{name}', '{phone}')")

    # 批量插入
    contacts = [
        ("李四", "13900139000", "lisi@email.com", "朋友"),
        ("王五", "13700137000", "wangwu@email.com", "家人"),
        ("赵六", "13600136000", "zhaoliu@email.com", "同事"),
    ]
    cursor.executemany(
        "INSERT INTO contacts (name, phone, email, category) VALUES (?, ?, ?, ?)",
        contacts
    )

    conn.commit()
    print(f"✅ 插入成功，ID: {cursor.lastrowid}")
```

> ⚠️ **避坑指南**：插入后**必须**调用 `conn.commit()`，否则数据不会保存！SQLite 默认不自动提交。

### 2.3 查询数据（SELECT）

```python
# ========== 查询数据 ==========
with sqlite3.connect("contacts.db") as conn:
    conn.row_factory = sqlite3.Row  # 启用 Row 工厂
    cursor = conn.cursor()

    # 查询所有
    cursor.execute("SELECT * FROM contacts")
    all_contacts = cursor.fetchall()
    print("所有联系人:")
    for contact in all_contacts:
        print(f"  {contact['name']} - {contact['phone']}")

    # 条件查询
    cursor.execute("SELECT * FROM contacts WHERE category = ?", ("同事",))
    colleagues = cursor.fetchall()
    print(f"\n同事数量: {len(colleagues)}")

    # 模糊查询
    cursor.execute("SELECT * FROM contacts WHERE name LIKE ?", ("%张%",))
    zhangs = cursor.fetchall()
    print(f"\n姓张的人: {[c['name'] for c in zhangs]}")

    # 排序
    cursor.execute("SELECT * FROM contacts ORDER BY name ASC")
    sorted_contacts = cursor.fetchall()

    # 限制结果数量
    cursor.execute("SELECT * FROM contacts LIMIT 2")
    top2 = cursor.fetchall()
```

### 2.4 更新数据（UPDATE）

```python
# ========== 更新数据 ==========
with sqlite3.connect("contacts.db") as conn:
    cursor = conn.cursor()

    # 更新单条记录
    cursor.execute(
        "UPDATE contacts SET phone = ? WHERE name = ?",
        ("13812345678", "张三")
    )
    print(f"更新了 {cursor.rowcount} 条记录")

    # 批量更新
    cursor.execute(
        "UPDATE contacts SET category = ? WHERE category = ?",
        ("工作伙伴", "同事")
    )

    conn.commit()
```

### 2.5 删除数据（DELETE）

```python
# ========== 删除数据 ==========
with sqlite3.connect("contacts.db") as conn:
    cursor = conn.cursor()

    # 删除单条
    cursor.execute("DELETE FROM contacts WHERE name = ?", ("赵六",))

    # 删除所有（危险操作！）
    # cursor.execute("DELETE FROM contacts")

    # 删除表（更危险！）
    # cursor.execute("DROP TABLE contacts")

    conn.commit()
    print(f"删除了 {cursor.rowcount} 条记录")
```

### 2.6 聚合查询

```python
# ========== 聚合查询 ==========
with sqlite3.connect("contacts.db") as conn:
    cursor = conn.cursor()

    # 统计总数
    cursor.execute("SELECT COUNT(*) FROM contacts")
    total = cursor.fetchone()[0]
    print(f"总联系人数: {total}")

    # 按分类统计
    cursor.execute("""
        SELECT category, COUNT(*) as count 
        FROM contacts 
        GROUP BY category
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 人")

    # 平均值、最大值、最小值（适用于数值字段）
    # cursor.execute("SELECT AVG(price), MAX(price), MIN(price) FROM products")
```

---

## 3. JOIN 联表查询

### 3.1 为什么需要 JOIN？

现实中的数据通常分布在多个表中：

```sql
-- 联系人表
CREATE TABLE contacts (id, name, phone);

-- 通话记录表
CREATE TABLE calls (id, contact_id, call_time, duration);

-- 需要 JOIN 才能查出"张三的所有通话记录"
```

### 3.2 JOIN 类型

```python
# code/03-join-queries.py
import sqlite3

with sqlite3.connect("join_demo.db") as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 创建表
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
            product TEXT,
            amount REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        -- 插入测试数据
        INSERT INTO users VALUES (1, '张三', 'zhang@email.com');
        INSERT INTO users VALUES (2, '李四', 'li@email.com');
        INSERT INTO users VALUES (3, '王五', 'wang@email.com');

        INSERT INTO orders VALUES (1, 1, 'Python书', 59.9);
        INSERT INTO orders VALUES (2, 1, '键盘', 199.0);
        INSERT INTO orders VALUES (3, 2, '显示器', 1299.0);
    """)

    # ========== INNER JOIN ==========
    # 只返回两个表中都能匹配的行
    print("=== INNER JOIN ===")
    cursor.execute("""
        SELECT users.name, orders.product, orders.amount
        FROM users
        INNER JOIN orders ON users.id = orders.user_id
    """)
    for row in cursor.fetchall():
        print(f"  {row['name']} 买了 {row['product']} (¥{row['amount']})")
    # 注意：王五没有订单，所以不会出现在结果中

    # ========== LEFT JOIN ==========
    # 返回左表所有行，右表无匹配则填 NULL
    print("\n=== LEFT JOIN ===")
    cursor.execute("""
        SELECT users.name, orders.product, orders.amount
        FROM users
        LEFT JOIN orders ON users.id = orders.user_id
    """)
    for row in cursor.fetchall():
        product = row['product'] or "无"
        amount = row['amount'] or 0
        print(f"  {row['name']}: {product} (¥{amount})")
    # 王五也会出现，product 显示为"无"

    # ========== 聚合 + JOIN ==========
    print("\n=== 每个用户的总消费 ===")
    cursor.execute("""
        SELECT users.name, SUM(orders.amount) as total
        FROM users
        LEFT JOIN orders ON users.id = orders.user_id
        GROUP BY users.id
        ORDER BY total DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row['name']}: ¥{row['total']:.2f}")
```

### 3.3 JOIN 类型速查表

| JOIN 类型 | 说明 | 结果 |
|-----------|------|------|
| INNER JOIN | 只返回匹配的行 | 两表都有的数据 |
| LEFT JOIN | 返回左表所有行 | 左表全部 + 右表匹配 |
| RIGHT JOIN | 返回右表所有行 | SQLite 不支持！用 LEFT JOIN 替代 |
| FULL JOIN | 返回两表所有行 | SQLite 不支持！用 UNION 替代 |

> ⚠️ **避坑指南**：SQLite **不支持** RIGHT JOIN 和 FULL JOIN！需要用 LEFT JOIN + UNION 模拟。

---

## 4. 索引与性能优化

### 4.1 什么是索引？

索引就像书的**目录**——帮助数据库快速找到数据，而不必扫描整张表。

```python
# 无索引：扫描 100 万行
# cursor.execute("SELECT * FROM users WHERE email = 'test@email.com'")
# → 逐行检查每一条，慢！

# 有索引：直接跳到目标
# CREATE INDEX idx_users_email ON users(email);
# → 通过索引直接定位，快！
```

### 4.2 创建和使用索引

```python
# code/04-index-performance.py
import sqlite3
import time

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

    # 插入 10 万条测试数据
    products = [
        (f"商品{i}", f"分类{i % 100}", i * 1.5)
        for i in range(100_000)
    ]
    cursor.executemany(
        "INSERT INTO products (name, category, price) VALUES (?, ?, ?)",
        products
    )
    conn.commit()

    # ========== 无索引查询 ==========
    start = time.time()
    cursor.execute("SELECT * FROM products WHERE category = '分类50'")
    results = cursor.fetchall()
    no_index_time = time.time() - start
    print(f"无索引查询: {len(results)} 条, 耗时 {no_index_time:.4f}秒")

    # ========== 创建索引 ==========
    start = time.time()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON products(category)")
    conn.commit()
    print(f"创建索引耗时: {time.time() - start:.4f}秒")

    # ========== 有索引查询 ==========
    start = time.time()
    cursor.execute("SELECT * FROM products WHERE category = '分类50'")
    results = cursor.fetchall()
    with_index_time = time.time() - start
    print(f"有索引查询: {len(results)} 条, 耗时 {with_index_time:.4f}秒")

    speedup = no_index_time / with_index_time if with_index_time > 0 else float('inf')
    print(f"加速比: {speedup:.1f}倍")
```

### 4.3 索引最佳实践

```python
# ✅ 应该加索引的场景
# 1. WHERE 条件经常用到的列
CREATE INDEX idx_users_email ON users(email);

# 2. JOIN 的关联列
CREATE INDEX idx_orders_user_id ON orders(user_id);

# 3. ORDER BY 排序列
CREATE INDEX idx_products_price ON products(price);

# 4. 组合索引（多列查询）
CREATE INDEX idx_products_cat_price ON products(category, price);

# ❌ 不应该加索引的场景
# 1. 很少用于查询的列（如"备注"字段）
# 2. 数据量很小的表（直接扫描更快）
# 3. 频繁更新的列（索引维护成本高）
# 4. 区分度低的列（如"性别"只有男/女两种值）
```

---

## 5. 事务管理

### 5.1 什么是事务？

事务确保**一组操作要么全部成功，要么全部失败**，避免数据不一致。

```python
# 场景：银行转账
# A 转 100 元给 B
# 1. A 的余额 -100
# 2. B 的余额 +100
# 如果第 2 步失败了，第 1 步应该回滚！

# 事务 = 保证这两步要么都成功，要么都不执行
```

### 5.2 事务操作

```python
# code/05-transactions.py
import sqlite3

# ========== 基本事务 ==========
with sqlite3.connect("bank.db") as conn:
    cursor = conn.cursor()

    # 创建账户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            name TEXT,
            balance REAL DEFAULT 0
        )
    """)
    cursor.executemany(
        "INSERT OR IGNORE INTO accounts VALUES (?, ?, ?)",
        [(1, "张三", 1000), (2, "李四", 500)]
    )
    conn.commit()

    # ========== 正常转账 ==========
    try:
        cursor.execute("UPDATE accounts SET balance = balance - 100 WHERE id = 1")
        cursor.execute("UPDATE accounts SET balance = balance + 100 WHERE id = 2")
        conn.commit()  # 两步都成功，提交
        print("✅ 转账成功")
    except Exception as e:
        conn.rollback()  # 出错回滚
        print(f"❌ 转账失败: {e}")

    # ========== 失败的转账（余额不足） ==========
    try:
        cursor.execute("UPDATE accounts SET balance = balance - 9999 WHERE id = 2")
        # 模拟第二步失败
        raise Exception("模拟错误")
        cursor.execute("UPDATE accounts SET balance = balance + 9999 WHERE id = 1")
        conn.commit()
    except Exception as e:
        conn.rollback()  # 回滚，余额不变
        print(f"❌ 转账失败，已回滚: {e}")

    # 查看余额
    cursor.execute("SELECT name, balance FROM accounts")
    for row in cursor.fetchall():
        print(f"  {row[0]}: ¥{row[1]:.2f}")

# ========== 自动提交模式 ==========
# conn = sqlite3.connect("test.db", isolation_level=None)
# isolation_level=None 表示每条 SQL 自动提交
# 不推荐用于需要事务的场景
```

### 5.3 事务隔离级别

```python
# SQLite 的默认隔离级别：DEFERRED
# 还有 IMMEDIATE 和 EXCLUSIVE

# DEFERRED: 事务开始时不锁定数据库
# IMMEDIATE: 事务开始时立即获取预留锁
# EXCLUSIVE: 事务开始时获取排他锁

# 一般用默认的 DEFERRED 就够了
conn = sqlite3.connect("test.db")
# 或者显式指定
conn = sqlite3.connect("test.db", isolation_level="DEFERRED")
```

### 5.4 上下文管理器（推荐）

```python
# 使用 with 语句自动管理事务
with sqlite3.connect("test.db") as conn:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users VALUES (1, 'test')")
    # 离开 with 块时：
    # - 没有异常 → 自动 commit
    # - 有异常 → 自动 rollback
```

> ⚠️ **避坑指南**：`with sqlite3.connect()` 在**没有异常时会自动 commit**，但**有异常时不一定自动 rollback**（取决于 Python 版本）。最安全的做法是在 except 中显式调用 `conn.rollback()`。

---

## 6. 防 SQL 注入

### 6.1 什么是 SQL 注入？

```python
# ❌ 危险写法——直接拼接字符串
name = input("请输入用户名: ")  # 假设用户输入: ' OR '1'='1
sql = f"SELECT * FROM users WHERE name = '{name}'"
# 实际执行: SELECT * FROM users WHERE name = '' OR '1'='1'
# 结果: 返回所有用户！数据库被攻破了！

# ✅ 安全写法——参数化查询
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
# SQLite 会自动处理特殊字符，防止注入
```

### 6.2 参数化查询规则

```python
# SQLite 支持两种参数风格

# 风格 1：? 占位符（推荐）
cursor.execute("SELECT * FROM users WHERE name = ? AND age > ?", ("张三", 18))

# 风格 2：:name 命名参数
cursor.execute("SELECT * FROM users WHERE name = :name AND age > :age",
               {"name": "张三", "age": 18})

# ❌ 永远不要这样做
# cursor.execute(f"SELECT * FROM users WHERE name = '{name}'")
# cursor.execute("SELECT * FROM users WHERE name = '%s'" % name)
```

> ⚠️ **避坑指南**：即使你确定用户输入是安全的，也要用参数化查询！这是**安全编程的基本原则**。

---

## 实战项目：通讯录管理系统

### 项目说明

构建一个完整的命令行通讯录系统，包含：
- 联系人的增删改查
- 分类管理
- 搜索功能
- 数据持久化（SQLite）

### 完整代码

```python
# code/06-contacts-manager.py
"""
📇 通讯录管理系统 —— 完整实战项目
功能：CRUD、分类、搜索、数据持久化
"""
import sqlite3
from datetime import datetime


class ContactManager:
    """通讯录管理器"""

    def __init__(self, db_path: str = "contacts.db"):
        """初始化数据库连接"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """创建数据库表"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT DEFAULT '',
                category TEXT DEFAULT '朋友',
                note TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
            CREATE INDEX IF NOT EXISTS idx_contacts_category ON contacts(category);
            CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
        """)
        self.conn.commit()

    def add_contact(self, name: str, phone: str, email: str = "",
                    category: str = "朋友", note: str = "") -> int:
        """添加联系人"""
        now = datetime.now().isoformat()
        cursor = self.conn.execute(
            """INSERT INTO contacts (name, phone, email, category, note,
               created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, phone, email, category, note, now, now)
        )
        self.conn.commit()
        print(f"✅ 添加成功: {name} (ID: {cursor.lastrowid})")
        return cursor.lastrowid

    def get_contact(self, contact_id: int) -> dict | None:
        """获取单个联系人"""
        cursor = self.conn.execute(
            "SELECT * FROM contacts WHERE id = ?", (contact_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_contacts(self, category: str = None,
                      search: str = None) -> list[dict]:
        """获取联系人列表"""
        sql = "SELECT * FROM contacts WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        if search:
            sql += " AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern] * 3)

        sql += " ORDER BY name"

        cursor = self.conn.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_contact(self, contact_id: int, **kwargs) -> bool:
        """更新联系人"""
        allowed_fields = {"name", "phone", "email", "category", "note"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            print("❌ 没有要更新的字段")
            return False

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [contact_id]

        cursor = self.conn.execute(
            f"UPDATE contacts SET {set_clause} WHERE id = ?", values
        )
        self.conn.commit()

        if cursor.rowcount > 0:
            print(f"✅ 更新成功 (ID: {contact_id})")
            return True
        else:
            print(f"❌ 未找到联系人 (ID: {contact_id})")
            return False

    def delete_contact(self, contact_id: int) -> bool:
        """删除联系人"""
        # 先检查是否存在
        contact = self.get_contact(contact_id)
        if not contact:
            print(f"❌ 未找到联系人 (ID: {contact_id})")
            return False

        cursor = self.conn.execute(
            "DELETE FROM contacts WHERE id = ?", (contact_id,)
        )
        self.conn.commit()
        print(f"✅ 已删除: {contact['name']}")
        return True

    def get_statistics(self) -> dict:
        """获取统计信息"""
        cursor = self.conn.execute("SELECT COUNT(*) FROM contacts")
        total = cursor.fetchone()[0]

        cursor = self.conn.execute("""
            SELECT category, COUNT(*) as count
            FROM contacts GROUP BY category ORDER BY count DESC
        """)
        categories = {row["category"]: row["count"] for row in cursor.fetchall()}

        return {"total": total, "categories": categories}

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


# ========== 命令行界面 ==========
def main():
    manager = ContactManager()

    while True:
        print("\n" + "=" * 40)
        print("📇 通讯录管理系统")
        print("=" * 40)
        print("1. 添加联系人")
        print("2. 查看联系人")
        print("3. 搜索联系人")
        print("4. 更新联系人")
        print("5. 删除联系人")
        print("6. 统计信息")
        print("0. 退出")
        print("-" * 40)

        choice = input("请选择操作 (0-6): ").strip()

        if choice == "1":
            name = input("姓名: ").strip()
            phone = input("电话: ").strip()
            email = input("邮箱 (可选): ").strip()
            category = input("分类 (朋友/同事/家人，默认朋友): ").strip() or "朋友"
            note = input("备注 (可选): ").strip()
            manager.add_contact(name, phone, email, category, note)

        elif choice == "2":
            category = input("按分类过滤 (直接回车显示全部): ").strip() or None
            contacts = manager.list_contacts(category=category)
            if not contacts:
                print("📭 没有找到联系人")
            else:
                print(f"\n📋 共 {len(contacts)} 个联系人:")
                for c in contacts:
                    print(f"  [{c['id']}] {c['name']} - {c['phone']} "
                          f"({c['category']})")

        elif choice == "3":
            keyword = input("搜索关键词 (姓名/电话/邮箱): ").strip()
            contacts = manager.list_contacts(search=keyword)
            if not contacts:
                print("🔍 没有找到匹配的联系人")
            else:
                print(f"\n🔍 找到 {len(contacts)} 个匹配:")
                for c in contacts:
                    print(f"  [{c['id']}] {c['name']} - {c['phone']}")

        elif choice == "4":
            try:
                cid = int(input("联系人 ID: ").strip())
            except ValueError:
                print("❌ 无效的 ID")
                continue
            print("留空表示不修改该字段")
            name = input("新姓名: ").strip() or None
            phone = input("新电话: ").strip() or None
            email = input("新邮箱: ").strip() or None
            updates = {}
            if name: updates["name"] = name
            if phone: updates["phone"] = phone
            if email: updates["email"] = email
            if updates:
                manager.update_contact(cid, **updates)

        elif choice == "5":
            try:
                cid = int(input("要删除的联系人 ID: ").strip())
            except ValueError:
                print("❌ 无效的 ID")
                continue
            confirm = input(f"确认删除联系人 {cid}? (y/N): ").strip()
            if confirm.lower() == "y":
                manager.delete_contact(cid)

        elif choice == "6":
            stats = manager.get_statistics()
            print(f"\n📊 统计信息:")
            print(f"  总联系人数: {stats['total']}")
            for cat, count in stats["categories"].items():
                print(f"  {cat}: {count} 人")

        elif choice == "0":
            print("👋 再见！")
            break

        else:
            print("❌ 无效选择，请重试")

    manager.close()


if __name__ == "__main__":
    main()
```

---

## 今日总结

- **SQLite 是 Python 内置的文件型数据库**，无需安装，适合学习和小型应用
- **SQL CRUD**：INSERT（增）、SELECT（查）、UPDATE（改）、DELETE（删）
- **参数化查询**防止 SQL 注入，永远不要拼接字符串
- **JOIN** 连接多个表：INNER JOIN（匹配）、LEFT JOIN（左表全部）
- **索引**加速查询，但会降低写入速度，合理使用
- **事务**确保数据一致性：commit 提交、rollback 回滚
- **conn.commit()** 必须调用，否则数据不会保存

## 练习题

### 练习 1：学生成绩管理 ⭐⭐
创建一个学生成绩管理系统：
- 创建 students 表（id, name, class_name）
- 创建 scores 表（id, student_id, subject, score）
- 实现功能：
  - 添加学生和成绩
  - 查询某学生的全部成绩
  - 查询某科目的平均分、最高分、最低分
  - 查询每个学生的总分排名

### 练习 2：商品库存管理 ⭐⭐
创建一个商品库存系统：
- products 表（id, name, price, stock, category）
- orders 表（id, product_id, quantity, order_time）
- 实现功能：
  - 商品的增删改查
  - 下单（扣减库存，库存不足时拒绝）
  - 查询销量排行榜
  - 查询库存预警（stock < 10）

### 练习 3：日志分析器 ⭐⭐⭐
编写一个日志分析脚本：
- 读取日志文件，解析并存入 SQLite
- 日志格式：`[2024-01-01 12:00:00] INFO: 用户登录 - user_id=123`
- 实现功能：
  - 统计每种日志级别的数量
  - 统计每小时的日志量
  - 查找所有 ERROR 日志
  - 生成日志报告

### 练习 4：数据迁移脚本 ⭐⭐⭐
编写一个数据库迁移脚本：
- 从 CSV 文件读取数据导入 SQLite
- 支持字段映射和类型转换
- 处理重复数据（去重策略）
- 记录迁移日志

### 练习 5：数据库备份工具 ⭐⭐⭐⭐
编写一个数据库备份和恢复工具：
- 备份：导出数据库为 SQL 文件
- 恢复：从 SQL 文件恢复数据库
- 增量备份：只备份变更的部分
- 完整性校验：验证备份文件是否可用

## 明天预告

Day 069 将学习**ORM 深入（SQLAlchemy）**——把数据库表映射成 Python 类，用面向对象的方式操作数据库。我们将构建一个电商数据模型，体验 ORM 的强大之处！
