#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 151 · 示例 03：SQL 注入检测脚本（实战 · 防御工具）
=====================================================

这是一个**给开发者自己用的注入检测器**，不是攻击器。它做两件事：

  【静态检测】扫描 Python 源码的 AST，找出"把用户数据拼进 SQL"的写法
              （f-string / 字符串加法 / % / .format / executescript / raw ...）
  【动态验证】对**本地内存靶场**发几条"金丝雀字符串"，比对响应差异，
              确认某个查询函数到底能不能被注入。本质是一套可以进 CI 的
              **注入回归测试**：修复后必须全绿。

⚠️ 使用边界
------------
• 动态检测只打 `sqlite3` 的 `:memory:` 库，不发起任何网络请求；
• 静态检测只读你自己的源码；
• **不要**把这个脚本改造成针对他人站点的扫描器。授权之外做注入测试
  在我国属于《刑法》第 285/286 条规制范围。要练，就练自己的代码。

运行
----
    python3 03-sqli-detector.py                     # 检测内置样本 + 本地动态验证
    python3 03-sqli-detector.py path/to/your.py     # 检测你自己的文件（可多个）
    python3 03-sqli-detector.py --no-dynamic        # 只做静态检测（更快）
    echo $?                                         # 0=干净，1=发现高危问题（可接 CI）
"""

import argparse
import ast
import sqlite3
import statistics
import sys
import time

# ══════════════════════════════════════════════════════════════════
# 第 0 部分：内置的"被测样本"
# ══════════════════════════════════════════════════════════════════
# 这是一段**故意写错**的迷你应用，用来证明检测器真的能抓到东西。
# 注意：它只是被 parse 的文本，永远不会被执行。
SAMPLE_CODE = '''
import sqlite3

def login(conn, username, password):
    sql = "SELECT id FROM users WHERE username = '" + username + "' AND password = '" + password + "'"
    return conn.execute(sql).fetchall()

def search_articles(conn, keyword):
    sql = f"SELECT id, title FROM articles WHERE title LIKE '%{keyword}%'"
    return conn.execute(sql).fetchall()

def sort_users(conn, column):
    return conn.execute("SELECT * FROM users ORDER BY " + column).fetchall()

def count_by_role(conn, role):
    return conn.execute("SELECT count(*) FROM users WHERE role = ?", (role,)).fetchall()

def write_log(conn, name):
    conn.executescript("DELETE FROM log; INSERT INTO log VALUES ('" + name + "');")

def get_by_id(conn, uid):
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (uid,))
    return cur.fetchall()

def report(conn, start):
    return conn.execute("SELECT * FROM orders WHERE created > '{}'".format(start)).fetchall()
'''

# ══════════════════════════════════════════════════════════════════
# 第 1 部分：静态检测
# ══════════════════════════════════════════════════════════════════

SQL_HINTS = (
    "select ", "insert into", "update ", "delete from", " where ", "where ",
    " from ", "from ", "order by", "union ", "values (", " like ", "set ",
    "drop table", "sqlite_master",
)

SEV_HIGH, SEV_MED, SEV_LOW, SEV_OK = "HIGH", "MED", "LOW", "OK"


def looks_like_sql(text: str) -> bool:
    """粗判一个字符串常量是不是 SQL。

    ✨ 为什么用"粗判"就够？因为静态检测的目标是**提示人去复核**，
    不是做编译器级的证明。假阳性（多报）可接受，假阴性（漏报）才危险，
    所以关键词表宁可宽一点。
    """
    low = text.lower()
    return any(h in low for h in SQL_HINTS)


class Finding:
    def __init__(self, line: int, sev: str, code: str, why: str, fix: str):
        self.line, self.sev, self.code, self.why, self.fix = line, sev, code, why, fix

    def __str__(self) -> str:
        return f"[{self.sev:>4}] 行 {self.line:>3}: {self.code}\n        原因：{self.why}\n        修复：{self.fix}"


class SQLSourceAuditor(ast.NodeVisitor):
    """基于 AST 的"SQL 拼接"检测器。

    ✨ 为什么用 AST 而不是 grep 正则？因为正则看见 `f"..."` 只当它是字符串，
    而 AST 能告诉我们："这段 SQL 里插了一个**变量**"，
    这正是漏洞的判据。正则会把 `execute(sql, (a,))` 也误报，AST 不会。
    """

    DANGEROUS_EXEC = {"execute", "executemany", "executescript"}
    ORM_RAW = {"raw", "extra", "RawSQL", "whereRaw", "text", "execute_sql"}

    def __init__(self, source: str):
        self.source = source
        self.lines = source.splitlines()
        self.findings: list[Finding] = []
        # 记录"这个变量名里装的是拼出来的 SQL"
        self.dynamic_sql_vars: dict[str, int] = {}

    # ── 工具 ──────────────────────────────────────────────────
    def _src(self, node: ast.AST) -> str:
        try:
            return ast.get_source_segment(self.source, node) or ""
        except Exception:
            return ""

    def _add(self, node: ast.AST, sev, code, why, fix) -> None:
        self.findings.append(Finding(getattr(node, "lineno", 0), sev, code, why, fix))

    # ── 检测点 1：变量赋值里的动态 SQL ────────────────────────
    def visit_Assign(self, node: ast.Assign) -> None:
        risk = self._dynamic_sql_kind(node.value)
        if risk:
            reason, sev, name = risk
            snippet = self._src(node.value)
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.dynamic_sql_vars[t.id] = node.lineno
            self._add(
                node, sev, snippet[:96],
                f"SQL 字符串里插入了动态内容（{reason}），参数会变成 SQL 语法的一部分。",
                "改成占位符：sql = \"... WHERE col = ?\"；执行时 conn.execute(sql, (value,))。",
            )
        self.generic_visit(node)

    def _string_parts(self, node: ast.AST) -> tuple[str, bool]:
        """把一个字符串表达式拆成 (字面量部分, 是否含动态部分)。

        ✨ 为什么要递归？因为真实代码经常写成
           "SELECT ... = '" + name + "' AND p = '" + pwd + "'"
        这是一个**左结合的嵌套加法**，只看最外层会漏掉，
        递归展开才能看到里面有 3 段字面量 + 2 个变量。
        """
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value, False
        if isinstance(node, ast.JoinedStr):                     # f"...{x}..."
            literal = "".join(v.value for v in node.values
                              if isinstance(v, ast.Constant) and isinstance(v.value, str))
            has_dyn = any(isinstance(v, ast.FormattedValue) for v in node.values)
            return literal, has_dyn
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            l1, d1 = self._string_parts(node.left)
            l2, d2 = self._string_parts(node.right)
            return l1 + l2, d1 or d2
        return "", True                                          # 未知表达式 → 视为动态

    def _dynamic_sql_kind(self, node: ast.AST):
        """返回 (原因, 严重级, 描述) 若该表达式是"含变量且像 SQL"的字符串。"""
        if isinstance(node, ast.JoinedStr):
            literal, has_dyn = self._string_parts(node)
            if looks_like_sql(literal) and has_dyn:
                return ("f-string 插值", SEV_HIGH, "f-string")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):   # "..." + x
            literal, has_dyn = self._string_parts(node)
            if looks_like_sql(literal) and has_dyn:
                return ("字符串用 + 拼接", SEV_HIGH, "concat")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):   # "..." % x
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                return ("字符串用 % 格式化", SEV_HIGH, "percent")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr == "format":                            # "...".format(x)
            base = node.func.value
            if isinstance(base, ast.Constant) and isinstance(base.value, str) and looks_like_sql(base.value):
                return ("str.format() 注入", SEV_HIGH, "format")
        return None

    # ── 检测点 2：调用 execute / executescript ────────────────
    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        attr = func.attr if isinstance(func, ast.Attribute) else (
            func.id if isinstance(func, ast.Name) else "")

        if attr in self.DANGEROUS_EXEC and node.args:
            arg = node.args[0]
            has_params = len(node.args) >= 2

            if attr == "executescript":
                self._add(node, SEV_HIGH, self._src(node)[:96],
                          "executescript 允许多语句执行，`;` 之后可被追加任意语句（堆叠注入）。",
                          "改用 execute + 参数化；确实需要脚本时，脚本必须是常量。")
            elif isinstance(arg, ast.Constant):
                if isinstance(arg.value, str) and "%s" in arg.value and not has_params:
                    self._add(node, SEV_MED, self._src(node)[:96],
                              "SQL 里有 %s 占位符却没有传参数，可能是手工替换。",
                              "用 qmark(?) 或 paramstyle 对应占位符，并把参数作为第二参数传入。")
            elif isinstance(arg, ast.Name):
                if arg.id in self.dynamic_sql_vars:
                    self._add(node, SEV_HIGH, self._src(node)[:96],
                              f"执行的 {arg.id} 是拼出来的 SQL（定义在第 {self.dynamic_sql_vars[arg.id]} 行）。",
                              "把变量值改为通过参数传入，SQL 字符串保持静态。")
                else:
                    self._add(node, SEV_MED, self._src(node)[:96],
                              "执行了一个变量形式的 SQL，静态分析无法确认它是否被拼接。",
                              "人工复核该变量的来源；确认是常量模板 + 参数化执行。")
            else:
                # f-string / 加法 / % / format 直接作为参数
                if self._dynamic_sql_kind(arg):
                    self._add(node, SEV_HIGH, self._src(node)[:96],
                              "直接把拼好的 SQL 交给 execute（f-string / 加法 / % / format 都会重新引入注入）。",
                              "改成 execute(\"静态SQL ?\", (value,))。")

        if attr in self.ORM_RAW:
            self._add(node, SEV_MED, self._src(node)[:96],
                      f"ORM 的 {attr}() 是『逃生舱』，会绕过 ORM 的参数化保护。",
                      "优先用 ORM 的 filter()/where()；必须用 raw 时，参数一定要绑定而不是拼接。")

        self.generic_visit(node)

    def run(self) -> list[Finding]:
        tree = ast.parse(self.source)
        self.visit(tree)
        return sorted(self.findings, key=lambda f: f.line)


def audit_static(name: str, source: str) -> tuple[int, int]:
    """返回 (HIGH 数量, 总问题数)。"""
    print(f"\n┌─ 静态检测：{name} " + "─" * max(0, 52 - len(name)))
    try:
        findings = SQLSourceAuditor(source).run()
    except SyntaxError as e:
        print(f"│ ❌ 解析失败（不是合法的 Python 文件）：{e}")
        return 0, 0

    if not findings:
        print("│ ✅ 没发现明显的 SQL 拼接写法")
        print("└" + "─" * 66)
        return 0, 0

    for f in findings:
        print("│ " + str(f).replace("\n", "\n│ "))
    highs = sum(1 for f in findings if f.sev == SEV_HIGH)
    print(f"│")
    print(f"│ 📊 小计：{len(findings)} 处问题，其中 HIGH {highs} 处")
    print("└" + "─" * 66)
    return highs, len(findings)


# ══════════════════════════════════════════════════════════════════
# 第 2 部分：动态验证（对本地内存靶场）
# ══════════════════════════════════════════════════════════════════
#
# 下面用到的字符串只有 4 个"金丝雀"，它们**不是**针对特定数据库的攻击
# payload 集合，而是四个"语法特征探针"：
#     CANARY_TRUE   —— 让 WHERE 恒真（结果应包含全部行）
#     CANARY_FALSE  —— 让 WHERE 恒假（结果应为空）
#     CANARY_UNION  —— 追加一个固定列数的 UNION
#     CANARY_QUOTE  —— 单独一个引号，制造语法错误
# 判定逻辑是**差分**：只看"两种输入的结果是否不一致"，
# 所以它不依赖任何数据库特性，也不会泄漏数据（探针里没有真实表名列名，
# 全是数字常量 1/2/3）。

CANARY_TRUE = "zzz' OR '1'='1"
CANARY_FALSE = "zzz' OR '1'='2"
CANARY_UNION = "zzz' UNION SELECT 1,2,3--"
CANARY_QUOTE = "zzz'"

HEAVY_ITER = 300_000
HEAVY_EXPR = (
    "(SELECT count(*) FROM (WITH RECURSIVE cc(n) AS "
    f"(SELECT 1 UNION ALL SELECT n+1 FROM cc WHERE n<{HEAVY_ITER}) SELECT n FROM cc))"
)


def make_range() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, role TEXT, api_token TEXT);
    """)
    conn.executemany(
        "INSERT INTO users (username, role, api_token) VALUES (?, ?, ?)",
        [("admin", "administrator", "tk9xq2"),
         ("alice", "user", "u_alice_01"),
         ("bob", "user", "u_bob_0002")],
    )
    conn.commit()
    return conn


# ── 被测目标 A：❌ 拼接版（应该被判定为"可注入"）──────────────
def target_vulnerable(conn: sqlite3.Connection, name: str) -> list:
    sql = f"SELECT id, username, role FROM users WHERE username = '{name}'"
    return conn.execute(sql).fetchall()


# ── 被测目标 B：✅ 参数化版（应该被判定为"安全"）──────────────
def target_parameterized(conn: sqlite3.Connection, name: str) -> list:
    return conn.execute(
        "SELECT id, username, role FROM users WHERE username = ?", (name,)
    ).fetchall()


def probe_boolean_diff(fn, conn) -> tuple[bool, str]:
    """差分探针：恒真 vs 恒假，结果不同 = 条件可控 = 可注入。"""
    try:
        rows_true = fn(conn, CANARY_TRUE)
        rows_false = fn(conn, CANARY_FALSE)
    except sqlite3.Error as e:
        return False, f"执行异常，跳过（{type(e).__name__}）"
    if rows_true != rows_false:
        return True, f"恒真返回 {len(rows_true)} 行，恒假返回 {len(rows_false)} 行"
    return False, f"两者都返回 {len(rows_true)} 行"


def probe_union(fn, conn) -> tuple[bool, str]:
    """UNION 探针：不该有结果的输入却返回了行，说明结果集被改写。"""
    try:
        rows = fn(conn, CANARY_UNION)
    except sqlite3.Error as e:
        return False, f"执行异常（{e}）"
    if rows:
        return True, f"返回了非空结果 {rows}（数据可被读出）"
    return False, "返回空结果"


def probe_error(fn, conn) -> tuple[bool, str]:
    """报错探针：异常是否冒泡到调用方（会泄漏结构信息）。"""
    try:
        fn(conn, CANARY_QUOTE)
    except sqlite3.Error as e:
        return True, f"抛出 {type(e).__name__}: {e}"
    return False, "未抛异常"


def probe_time(fn, conn, repeats: int = 3) -> tuple[bool, str]:
    """时间探针：条件真假导致响应耗时出现显著差异 = 时间盲注信道。

    ✨ 为什么要取中位数、还要跑多次？因为单次计时噪声太大，
    用中位数可以抗住一次偶发的系统抖动。
    """
    def elapsed(cond: str) -> float:
        payload = f"zzz' OR CASE WHEN ({cond}) THEN {HEAVY_EXPR} ELSE 0 END--"
        t0 = time.perf_counter()
        try:
            fn(conn, payload)
        except sqlite3.Error:
            return -1.0
        return time.perf_counter() - t0

    t_true = statistics.median(elapsed("1=1") for _ in range(repeats))
    t_false = statistics.median(elapsed("1=2") for _ in range(repeats))
    if t_true < 0 or t_false < 0:
        return False, "执行异常，跳过"
    diff = (t_true - t_false) * 1000
    if diff > 20:                      # 阈值 20ms：低于它认为是噪声
        return True, f"恒真 {t_true*1000:.1f}ms vs 恒假 {t_false*1000:.1f}ms（差 {diff:.1f}ms）"
    return False, f"耗时无显著差异（{t_true*1000:.1f}ms / {t_false*1000:.1f}ms）"


def dynamic_scan() -> int:
    print("\n┌─ 动态验证：对本地内存靶场跑注入回归测试 " + "─" * 23)
    conn = make_range()
    probes = [
        ("布尔差分", probe_boolean_diff),
        ("UNION 改写", probe_union),
        ("报错泄漏", probe_error),
        ("时间差异", probe_time),
    ]
    targets = [
        ("target_vulnerable  (拼接版 ❌)", target_vulnerable, True),
        ("target_parameterized (参数化版 ✅)", target_parameterized, False),
    ]

    unexpected = 0
    for label, fn, should_be_injectable in targets:
        print(f"│\n│ ▸ {label}")
        for pname, probe in probes:
            hit, detail = probe(fn, conn)
            mark = "❗可注入" if hit else "✅ 无信号"
            print(f"│    {pname:<10} {mark}   {detail}")
            if hit != should_be_injectable:
                unexpected += 1
                print(f"│      ⚠️ 与预期不符（该目标预期"
                      f"{'可注入' if should_be_injectable else '安全'}）")

    print("│")
    if unexpected == 0:
        print("│ ✅ 检测器行为符合预期：拼接版被判为可注入，参数化版全绿")
    else:
        print(f"│ ❌ 有 {unexpected} 项结果与预期不符，检测器需要校准")
    print("└" + "─" * 66)
    print("""
📌 怎么把这套东西用到你自己的项目：
   1. 把 target_* 换成你真实的查询函数（用测试库，不要连生产库）；
   2. 每个新增的 DAO 函数都配一组探针，断言"全部无信号"；
   3. 接进 CI：任一探针报警就让流水线失败 —— 这就是**注入回归测试**。
   4. 再加静态检测：任何 PR 里出现 f-string 拼 SQL 就直接评论提醒。
""")
    return unexpected


# ══════════════════════════════════════════════════════════════════
# 第 3 部分：主流程
# ══════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser(
        description="SQL 注入检测器（静态 AST 检测 + 本地动态回归验证）")
    ap.add_argument("files", nargs="*", help="要静态检测的 Python 文件；留空则检测内置样本")
    ap.add_argument("--no-dynamic", action="store_true", help="跳过动态验证（更快）")
    args = ap.parse_args()

    print("=" * 68)
    print("  SQL 注入检测器 · 只检测你自己的代码与本地靶场")
    print("=" * 68)

    total_high, total = 0, 0
    if args.files:
        for path in args.files:
            try:
                with open(path, encoding="utf-8") as fh:
                    src = fh.read()
            except OSError as e:
                print(f"\n┌─ 跳过 {path}：{e}")
                continue
            h, n = audit_static(path, src)
            total_high += h
            total += n
    else:
        h, n = audit_static("<内置样本 SAMPLE_CODE>", SAMPLE_CODE)
        total_high += h
        total += n

    dynamic_bad = 0
    if not args.no_dynamic:
        dynamic_bad = dynamic_scan()

    print("\n" + "=" * 68)
    print(f"  汇总：静态 HIGH {total_high} 处 / 静态问题共 {total} 处 / "
          f"动态异常 {dynamic_bad} 项")
    print("  退出码：0 = 干净，1 = 需要处理（可直接接入 CI）")
    print("=" * 68)
    return 1 if (total_high or total or dynamic_bad) else 0


if __name__ == "__main__":
    sys.exit(main())
