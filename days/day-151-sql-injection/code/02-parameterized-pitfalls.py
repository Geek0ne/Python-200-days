#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 151 · 示例 02：参数化查询的边界与 ORM 防注入失效场景（进阶/避坑）
=====================================================================

示例 01 我们证明了"参数化查询能根治注入"。但真实项目里，
**"我用了参数化"和"我没有注入"是两件事**。本示例专门收集那些
"看起来安全、实际上还是能注入"的写法，以及 ORM 自动防注入的机制与失效场景。

本地靶场：依然是 sqlite3 内存库，不连网络、不碰真实站点。

本示例的 7 个坑
--------------
    坑 1  占位符不能当标识符用（表名/列名/ORDER BY 列）
    坑 2  半参数化：只参数化了 WHERE，却把 ORDER BY 拼接进去
    坑 3  LIKE 通配符注入：参数化了，`%` 仍然是通配符
    坑 4  IN 子句：把值拼进括号里
    坑 5  二次注入：入库时安全，取出后再拼接
    坑 6  ORM 自动防注入的机制与三种典型失效场景
    坑 7  日志/异常把 SQL 与参数混在一起，泄漏数据

运行
----
    python3 02-parameterized-pitfalls.py
"""

import sqlite3


def banner(title: str) -> None:
    print("\n" + "═" * 70)
    print(f"  {title}")
    print("═" * 70)


def sub(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))


SCHEMA = """
CREATE TABLE users (
    id       INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    role     TEXT NOT NULL,
    api_token TEXT NOT NULL
);
CREATE TABLE audits (
    id   INTEGER PRIMARY KEY,
    note TEXT
);
"""


def make_range() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO users (username, role, api_token) VALUES (?, ?, ?)",
        [
            ("admin", "administrator", "tk9xq2"),
            ("alice", "user", "u_alice_01"),
            ("bob", "user", "u_bob_0002"),
        ],
    )
    conn.commit()
    return conn


# ══════════════════════════════════════════════════════════════════
# 坑 1：占位符只能放"值"，不能放"标识符"
# ══════════════════════════════════════════════════════════════════

def pitfall_1(conn: sqlite3.Connection) -> None:
    banner("坑 1：表名 / 列名 / 排序方向 **不能**用占位符")
    print("先纠正一个最常见的误解：参数化不是『字符串替换』，")
    print("它是把值交给数据库的**执行引擎**去绑定的，所以只能出现在")
    print("『值』的位置（WHERE 右边、INSERT 的 VALUES、UPDATE 的 SET 值……），")
    print("不能出现在『标识符』的位置（表名、列名、ASC/DESC……）。")

    sub("1.1 占位符放表名 → 数据库直接报语法错误")
    try:
        conn.execute("SELECT * FROM ? WHERE id = ?", ("users", 1))
    except sqlite3.OperationalError as e:
        print("   SELECT * FROM ? WHERE id = ?  →", e)
        print("   ✨ 报错其实是好事：说明数据库**拒绝了**把值当结构用。")

    sub("1.2 正确做法：白名单映射（不是转义，不是黑名单）")
    ALLOWED_TABLES = {"users": "users", "audits": "audits"}

    def safe_count(table_key: str) -> int:
        table = ALLOWED_TABLES.get(table_key)
        if table is None:                     # 不在白名单 → 直接拒绝
            raise ValueError(f"非法表名: {table_key!r}")
        # 只有**通过白名单校验之后**，才允许把它拼进 SQL。
        # 拼接的内容来自我们自己的常量表，绝不来自用户。
        return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    print("   safe_count('users')  →", safe_count("users"))
    print("   safe_count('secrets')→", end=" ")
    try:
        safe_count("secrets")
    except ValueError as e:
        print(f"拒绝：{e}")
    print("   ✨ 关键：拼进去的是**白名单里的常量**，用户输入只用于『查表』这一步。")


# ══════════════════════════════════════════════════════════════════
# 坑 2：半参数化 —— WHERE 安全了，ORDER BY 还是拼接
# ══════════════════════════════════════════════════════════════════

def insecure_sort(conn: sqlite3.Connection, order_by: str) -> list:
    """❌ 反例：ORDER BY 是拼接的，WHERE 根本没参数（没法参数化列名）。"""
    return conn.execute(
        f"SELECT username, role FROM users ORDER BY {order_by}"
    ).fetchall()


def pitfall_2(conn: sqlite3.Connection) -> None:
    banner("坑 2：半参数化 —— ORDER BY 注入（盲注的另一个信道）")

    print("正常排序：insecure_sort('username') →")
    print("   ", [r[0] for r in insecure_sort(conn, "username")])

    sub("2.1 排序结果本身也能当『信息信道』")
    for label, cond in [("admin 令牌首字母 = 't'", "1"), ("首字母 = 'x'", "0")]:
        expr = (
            "(CASE WHEN "
            "(substr((SELECT api_token FROM users WHERE username='admin'),1,1)='t') "
            "THEN username ELSE -id END)"
        )
        if cond == "0":
            expr = expr.replace("='t'", "='x'")     # 构造一个为假的条件做对照
        rows = insecure_sort(conn, expr)
        print(f"   {label:<24} → 排序结果 {[r[0] for r in rows]}")
    print("   ✨ 两次的**行顺序不同**，说明排序表达式被执行了 ——")
    print("      攻击者不需要看到数据内容，只看顺序就能读出 1 bit。")

    sub("2.2 正确做法：排序字段与方向都走白名单")
    ALLOWED_SORT = {"username", "id", "role"}
    ALLOWED_DIR = {"ASC", "DESC"}

    def safe_sort(column: str, direction: str = "ASC") -> list:
        if column not in ALLOWED_SORT:
            raise ValueError(f"非法排序字段: {column!r}")
        if direction.upper() not in ALLOWED_DIR:
            raise ValueError(f"非法排序方向: {direction!r}")
        # 能到这里，column / direction 一定是常量集合里的元素
        return conn.execute(
            f"SELECT username, role FROM users ORDER BY {column} {direction.upper()}"
        ).fetchall()

    print("   safe_sort('username','DESC') →", [r[0] for r in safe_sort("username", "desc")])
    try:
        safe_sort("(CASE WHEN 1=1 THEN id ELSE username END)")
    except ValueError as e:
        print(f"   safe_sort('(CASE ...)')  → 拒绝：{e}")
    print("   ⚠️ 避坑：ORDER BY 的方向也要白名单 ——")
    print("      `DESC; DROP TABLE users` 在支持多语句的驱动上同样能打。")


# ══════════════════════════════════════════════════════════════════
# 坑 3：LIKE 通配符注入（参数化防注入，但防不住"语义滥用"）
# ══════════════════════════════════════════════════════════════════

def pitfall_3(conn: sqlite3.Connection) -> None:
    banner("坑 3：LIKE 通配符注入 —— 参数化也拦不住 `%`")
    print("很多人以为『用了参数化就万事大吉』。但 LIKE 的通配符")
    print("（`%` 任意多个字符、`_` 任意一个字符）是**数据层**的元字符，")
    print("参数化只保证它不被当 SQL 语法，不保证它不被当 LIKE 通配符。")

    def search_naive(kw: str) -> list:
        # ✅ 参数化，无 SQL 注入
        # ❌ 但用户传 "%" 就等于查全表；传 "a%c" 会匹配到意料之外的行
        return conn.execute(
            "SELECT username FROM users WHERE username LIKE ?", (f"%{kw}%",)
        ).fetchall()

    print("\n   search_naive('a')   →", [r[0] for r in search_naive("a")])
    print("   search_naive('%')   →", [r[0] for r in search_naive("%")], "  ← 全表被返回")
    print("   search_naive('_')   →", [r[0] for r in search_naive("_")], "  ← 所有单字符用户名")

    def search_escaped(kw: str) -> list:
        # ✨ 正确做法：把用户输入里的 LIKE 元字符转义，再用 ESCAPE 声明转义符
        esc = kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return conn.execute(
            "SELECT username FROM users WHERE username LIKE ? ESCAPE '\\'",
            (f"%{esc}%",),
        ).fetchall()

    print("\n   修复后 search_escaped('%') →", [r[0] for r in search_escaped("%")],
          " ← `%` 被当成普通字符")
    print("   ✨ 结论：参数化解决『代码/数据』边界，业务语义（通配符、长度、范围）")
    print("      要另外校验。这也是『输入校验不能省』的最好例子。")


# ══════════════════════════════════════════════════════════════════
# 坑 4：IN 子句
# ══════════════════════════════════════════════════════════════════

def insecure_in_clause(conn: sqlite3.Connection, names: list) -> list:
    """❌ 反例：把值拼进 IN (...)。"""
    joined = "', '".join(names)
    return conn.execute(
        f"SELECT username, role FROM users WHERE username IN ('{joined}')"
    ).fetchall()


def safe_in_clause(conn: sqlite3.Connection, names: list) -> list:
    """✅ 正例：**只拼占位符**，值全部走参数。

    ✨ 为什么这样安全？拼接进 SQL 的只有 "?, ?, ?" 这种**结构**，
    数量取决于列表长度但内容永远是常量；真正的值通过参数列表下发。
    换句话说：用户能影响"有几个问号"，但不能影响"问号里是什么"。
    """
    if not names:
        return []                                   # ⚠️ IN () 是语法错误，必须特判
    placeholders = ", ".join("?" for _ in names)
    return conn.execute(
        f"SELECT username, role FROM users WHERE username IN ({placeholders})",
        tuple(names),
    ).fetchall()


def pitfall_4(conn: sqlite3.Connection) -> None:
    banner("坑 4：IN 子句 —— 只拼『占位符』，绝不拼『值』")

    print("   safe_in_clause(['alice','bob']) →", [r[0] for r in safe_in_clause(conn, ["alice", "bob"])])

    evil = "x') UNION SELECT api_token, 'leak' FROM users--"
    print("\n   正常写法面对注入串：")
    print("     insecure_in_clause([evil]) →", insecure_in_clause(conn, [evil]))
    print("   ✅ 安全写法面对同一串：")
    print("     safe_in_clause([evil])     →", safe_in_clause(conn, [evil]), " ← 当成普通值")
    print("   ⚠️ 避坑：还要限制列表长度（比如最多 500 个），")
    print("      否则 `IN (?,?,...)` 几万个占位符会打爆 SQL 解析器（DoS）。")


# ══════════════════════════════════════════════════════════════════
# 坑 5：二次注入（Second-Order Injection）
# ══════════════════════════════════════════════════════════════════

def pitfall_5(conn: sqlite3.Connection) -> None:
    banner("坑 5：二次注入 —— 入库时安全，取出后拼接就中招")
    print("这是最阴的一类：扫描器扫不出来，代码评审也容易漏，")
    print("因为它**跨越了两次请求**。")

    evil_name = "x' OR '1'='1"

    sub("5.1 第一次请求：注册。全程参数化，**完全安全**")
    conn.execute(
        "INSERT INTO users (username, role, api_token) VALUES (?, 'user', 'tk_new')",
        (evil_name,),
    )
    print(f"   已入库的 username：{conn.execute('SELECT username FROM users WHERE api_token=?', ('tk_new',)).fetchone()[0]!r}")
    print("   ✨ 注意：数据库里存的确实是这段**恶意字符串本身**，它没有变成 SQL。")

    sub("5.2 第二次请求：从库里读出来，然后拼进 SQL（❌ 在这里中招）")
    stored = conn.execute(
        "SELECT username FROM users WHERE api_token = ?", ("tk_new",)
    ).fetchone()[0]
    sql = f"UPDATE users SET role = 'vip' WHERE username = '{stored}'"
    print("   拼出来的 SQL：")
    print("   ", sql)
    print("   解读：WHERE username = 'x' OR '1'='1'  → **恒真**，全表被改！")
    conn.execute(sql)
    print("   更新后所有人的 role：",
          dict(conn.execute("SELECT username, role FROM users").fetchall()))

    sub("5.3 正确做法：永远只用**标识符**（主键/ID）做定位，且仍然参数化")
    conn.execute("UPDATE users SET role = 'user'")            # 复原
    conn.execute("UPDATE users SET role = 'admin' WHERE id = 1")
    conn.execute(
        "UPDATE users SET role = 'vip' WHERE id = ?",
        (conn.execute("SELECT id FROM users WHERE api_token = ?", ("tk_new",)).fetchone()[0],),
    )
    print("   用 id 定位后：",
          dict(conn.execute("SELECT username, role FROM users").fetchall()))
    print("   ✨ 两条铁律：")
    print("     ① 数据出库**不代表可信**，二次使用仍要参数化（『数据污染』）；")
    print("     ② 定位记录用不可变的 id，不要用用户可控的 name/email 拼 WHERE。")


# ══════════════════════════════════════════════════════════════════
# 坑 6：ORM 自动防注入的机制与失效场景
# ══════════════════════════════════════════════════════════════════

class MiniORM:
    """一个"迷你 ORM"，用来揭示 ORM 到底是怎么防注入的。

    真实 ORM（Django ORM / SQLAlchemy）的核心做法和这里一模一样：
        把 Python 的链式调用**翻译成带占位符的 SQL + 参数列表**，
        再交给 DBAPI 执行。
    所以"ORM 防注入"不是玄学：**它就是自动帮你写了参数化查询**。
    反过来说，只要你让 ORM 走"拼接字符串"的口子，保护立刻消失。
    """

    ALLOWED_COLUMNS = {"id", "username", "role", "api_token"}

    def __init__(self, conn: sqlite3.Connection, table: str = "users"):
        if table not in {"users", "audits"}:
            raise ValueError("表名不在白名单")
        self.conn = conn
        self.table = table

    # ── filter(**kwargs)：ORM 的安全区 ────────────────────────
    def filter(self, **kwargs) -> "MiniORM":
        """支持 username='x'、id__gt=1、username__like='a%'。

        ✨ 关键：后缀（__gt/__like）只决定**运算符**（常量映射），
        字段名走白名单，值走参数 —— 三样东西各归各位。
        """
        clauses, params = [], []
        for key, value in kwargs.items():
            field, _, op = key.partition("__")
            if field not in self.ALLOWED_COLUMNS:
                raise ValueError(f"非法字段: {field!r}")   # 白名单挡标识符注入
            operator = {"": "=", "gt": ">", "lt": "<", "like": "LIKE"}[op]
            clauses.append(f"{field} {operator} ?")        # 只拼常量运算符
            params.append(value)                           # 值走参数
        self._where = " AND ".join(clauses) or "1=1"
        self._params = params
        return self

    def order_by(self, column: str, desc: bool = False) -> "MiniORM":
        if column not in self.ALLOWED_COLUMNS:
            raise ValueError(f"非法排序字段: {column!r}")
        self._order = f" ORDER BY {column}{' DESC' if desc else ' ASC'}"
        return self

    def sql(self) -> str:
        return f"SELECT * FROM {self.table} WHERE {self._where}{getattr(self, '_order', '')}"

    def all(self) -> list:
        return self.conn.execute(self.sql(), self._params).fetchall()

    # ── raw()：ORM 的"逃生舱"，也是事故高发区 ────────────────
    def raw(self, sql: str) -> list:
        return self.conn.execute(sql).fetchall()

    def raw_documented_unsafe(self, sql: str) -> None:
        """真实 ORM 里对应 Django 的 `extra()`/`RawSQL`、SQLAlchemy 的 `text()`
        + f-string —— 名字里都写着"我不负责安全"。"""
        self.conn.execute(sql).fetchall()


def pitfall_6(conn: sqlite3.Connection) -> None:
    banner("坑 6：ORM 自动防注入的机制与三种失效场景")

    sub("6.1 机制：ORM 只是自动帮你做参数化")
    orm = MiniORM(conn)
    q = orm.filter(username="x' OR '1'='1", role="user")
    print("   ORM 生成的 SQL :", q.sql())
    print("   实际下发的参数 :", ["x' OR '1'='1", "user"])
    print("   查询结果       :", q.all(), " ← 恶意串被当成普通值 ✅")
    print("   ✨ 看到 `?` 了吗？ORM 没有『消毒』字符串，它只是**没有拼接**。")

    sub("6.2 失效场景 A：`extra()` / `RawSQL` / `whereRaw` 里拼字符串")
    user_input = "x' OR '1'='1"
    print("   ❌ raw(f\"... username = '{user_input}'\")：")
    print("      →", MiniORM(conn).raw(
        f"SELECT username FROM users WHERE username = '{user_input}'"
    ))
    print("   ✨ 一旦用了 raw，ORM 已经不在你的参数化链路上，等同手写拼接。")

    sub("6.3 失效场景 B：字段名/表名由用户决定（ORM 无法参数化标识符）")
    try:
        MiniORM(conn).filter(**{"(CASE WHEN 1=1 THEN id ELSE username END)": 1})
    except ValueError as e:
        print("   ❌ filter(**{恶意字段名: 1}) →", f"拒绝：{e}")
        print("   ✨ ORM 挡得住是因为它做了白名单；如果代码写成")
        print("      `.extra(order_by=[request.GET['sort']])` 或")
        print("      `.order_by(request.GET['sort'])`，就是把这个白名单漏掉了。")

    sub("6.4 失效场景 C：`.raw()` / cursor 里用 `%` 或 `.format()` 二次加工")
    print("   ❌ 典型事故：")
    print("      cursor.execute(sql % params)         # 参数化被 `%` 掉包")
    print("      cursor.execute(f\"SELECT ... {col}\")  # 又回到拼接")
    print("   ✅ 正确：cursor.execute(sql, params) —— 逗号，不是百分号。")
    print("   ⚠️ 记忆点：**只要 SQL 字符串里出现了用户数据，参数化就已经失效**。")
    print("      判断标准很简单：SQL 变量里能不能看到 f-string / + / %，能看到就有风险。")


# ══════════════════════════════════════════════════════════════════
# 坑 7：日志与异常
# ══════════════════════════════════════════════════════════════════

def pitfall_7(conn: sqlite3.Connection) -> None:
    banner("坑 7：日志 / 异常把 SQL 与参数拼在一起，等于自己泄漏数据")
    print("   ❌ log.info(f\"SQL: {sql_with_values}\")  → 密码、token 进日志")
    print("   ❌ 把 sqlite3 异常原文返回前端      → 泄漏表名、列名（见示例 01）")
    print()
    print("   ✅ 正确做法：")
    print("      ① 日志记『SQL 模板 + 参数个数』，敏感参数脱敏；")
    print("      ② 对外统一错误码，异常细节只进服务端日志；")
    print("      ③ 日志系统本身做访问控制与保留期管理。")
    print("\n   演示：同一个查询，安全的日志写法长这样")
    sql, params = "SELECT username FROM users WHERE role = ?", ("user",)
    print(f"      log: sql={sql!r} params=[<{len(params)} value(s) masked>]")
    print("   结果（正常返回，不影响功能）：", conn.execute(sql, params).fetchall())


def main() -> None:
    conn = make_range()
    pitfall_1(conn)
    pitfall_2(conn)
    pitfall_3(conn)
    pitfall_4(conn)
    pitfall_5(conn)
    pitfall_6(conn)
    pitfall_7(conn)

    banner("小结：参数化『能用/不能用』速查")
    print("""
┌──────────────────────────┬─────────────┬──────────────────────────────┐
│ SQL 位置                 │ 能参数化？  │ 正确做法                     │
├──────────────────────────┼─────────────┼──────────────────────────────┤
│ WHERE 条件值             │ ✅ 能       │ col = ?                      │
│ INSERT 的 VALUES         │ ✅ 能       │ VALUES (?, ?)                │
│ UPDATE 的 SET 值         │ ✅ 能       │ SET col = ?                  │
│ LIMIT / OFFSET 数值      │ ✅ 多数支持 │ LIMIT ? LIMIT ? OFFSET ?     │
│ IN 列表的值              │ ✅ 能       │ 只拼 "?,?,?"，值走参数       │
│ LIKE 的模式串            │ ✅ 能(语法) │ 仍需转义 %/_ + ESCAPE        │
│ IN 列表的**长度**        │ ⚠️ 半能    │ 生成占位符，但需限长防 DoS   │
│ 表名 / 列名              │ ❌ 不能     │ 白名单映射                   │
│ ORDER BY 字段 / 方向     │ ❌ 不能     │ 白名单映射                   │
│ 运算符（AND/OR/=/LIKE）  │ ❌ 不能     │ 代码里固定，不由用户决定     │
└──────────────────────────┴─────────────┴──────────────────────────────┘

三条铁律：
  1. 用户数据出现在 SQL 字符串里 = 参数化已失效（f-string / % / + / format 都是信号）。
  2. 标识符（表名、列名、排序）用**白名单**，不要用『转义/黑名单』。
  3. 数据库账号最小权限 + 关闭详细报错，让『万一漏了』的损失可控。
""")


if __name__ == "__main__":
    main()
