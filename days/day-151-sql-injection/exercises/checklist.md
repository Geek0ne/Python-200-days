# Day 151 — SQL 注入原理 · 练习与完成清单

> 主题：五类注入（UNION / 报错 / 布尔盲注 / 时间盲注 / 堆叠）·
> 参数化查询防护原理 · ORM 自动防注入与失效场景
> 实战：SQL 注入检测脚本
> 预计用时：90~150 分钟（不含思考题）
>
> ⚠️ 全部练习只针对**本地 sqlite3 内存靶场**或**你自己的代码**。
> 禁止对任何未授权系统做注入测试。

---

## ✅ 今日完成清单

### 概念理解（能用自己的话讲清楚）
- [ ] 用一句话说清 SQL 注入的定义，并指出它的**唯一根因**（数据被当成代码）
- [ ] 解释"注入的本质不是特殊字符，而是**字面量边界被跨越**"
- [ ] 说出 SQL 注入的 4 类危害等级（读 / 改 / 删 / 越权），并各举一个后果
- [ ] 说清 SQL 注入与 XSS、命令注入、CSRF/SSRF、越权访问的**区别**

### 原理掌握（能画出流程图）
- [ ] 能默画数据库解析 SQL 的**五步流水线**（词法→语法→语义→计划→执行）
- [ ] 能指出"边界是在第 ① 步（词法分析）被破坏的"
- [ ] 解释参数化查询为什么是**两次往返**（PREPARE / EXECUTE），
      以及"值不经过 Lexer"为什么就能根治
- [ ] 说清参数化与**转义**的本质差别（结构性防御 vs 过滤式防御）
- [ ] 说出五类注入各自的**信息回传信道**，并默写那张分类表
- [ ] 解释布尔盲注里为什么必须用 `OR` 而不是 `AND`（短路求值细节）
- [ ] 解释时间盲注里"为什么重表达式必须写在 `OR` 的右边"
- [ ] 解释 ORM 到底做了什么才"自动防注入"，以及**三种失效场景**
- [ ] 说清为什么 WAF / 黑名单 / 转义都不算根治
- [ ] 能回答"能参数化 / 不能参数化"速查表（尤其是标识符那三行）

### 动手实践（跑代码 + 改代码）
- [ ] 运行 `code/01-sql-injection-basics.py`，看懂每个 payload 实际执行的 SQL 长什么样
- [ ] 记录 `03` 布尔盲注的提取结果（应为 `tk9xq2`）和请求次数
- [ ] 记录时间盲注的两组耗时（恒真 ≈ 几十~百 ms，恒假 ≈ 0ms）
- [ ] 运行 `code/02-parameterized-pitfalls.py`，把 7 个坑的"❌/✅"输出都看懂
- [ ] 在 `02` 里给 `insecure_sort()` 加一个"只允许 3 种字段"的白名单版本，并自测
- [ ] 在 `02` 里把二次注入的 `UPDATE ... WHERE username='{stored}'` 改成按 id 定位
- [ ] 运行 `code/03-sqli-detector.py`，数一数内置样本报了几处 HIGH（应为 7）
- [ ] 运行 `python3 code/03-sqli-detector.py --no-dynamic`，确认静态检测独立可用
- [ ] 用检测器扫你自己的任意一个项目文件：
      `python3 code/03-sqli-detector.py /path/to/your.py`
- [ ] 运行 `echo $?` 确认退出码语义（有 HIGH ⇒ 1，干净 ⇒ 0）

### 输出物
- [ ] `days/day-151-sql-injection/` 目录下 4 类文件齐全（README / code / diagrams / exercises）
- [ ] 3 个 `.py` 全部能 `python3` 直接跑通，**无第三方依赖、无省略号**
- [ ] 能对着 `diagrams/README.md` 给别人讲一遍"拼接 vs 参数化"的协议差异
- [ ] 能说出你要在自己项目里做的**前三条**整改动作

---

## 📝 练习题

### 基础题（巩固机制）

**Q1. 拼出完整 SQL（理解语义改写）**

假设应用代码是：

```python
sql = "SELECT id, email FROM users WHERE email = '" + email + "'"
conn.execute(sql)
```

请写出当 `email` 分别是下面三个值时，数据库**实际收到并执行**的完整 SQL，
并说明每一个的后果（返回值/是否报错/是否有副作用）：

```
A. alice@example.com
B. nobody@example.com' OR '1'='1
C. nobody@example.com' UNION SELECT 1, api_token FROM users-- 
```

**Q2. 五类注入配对**

为每个场景选择最可能奏效的注入类型（可能不止一个答案，说明理由）：

| 场景 | 选项 |
|---|---|
| A. 页面把查询结果直接渲染成表格 | ① UNION 注入 |
| B. 页面只显示"登录成功/失败" | ② 报错注入 |
| C. 页面回显 `SQLSTATE[42000]` 之类的报错原文 | ③ 布尔盲注 |
| D. 页面永远返回同一个静态页面，无任何差异 | ④ 时间盲注 |
| E. 驱动允许一次执行多条语句 | ⑤ 堆叠注入 |

**Q3. 判别参数化的"真假"**

下面 6 个调用，哪些真正实现了参数化？哪些仍是拼接？分别说明风险：

```python
# ①
conn.execute("SELECT * FROM users WHERE id = ?", (uid,))
# ②
conn.execute("SELECT * FROM users WHERE id = %s" % uid)
# ③
conn.execute("SELECT * FROM users WHERE id = {}".format(uid))
# ④
conn.execute(f"SELECT * FROM users WHERE id = {uid}")
# ⑤
conn.execute("SELECT * FROM users WHERE id = :id", {"id": uid})
# ⑥
sql = "SELECT * FROM users WHERE id = ?"
conn.execute(sql, (uid,))
```

**Q4. 判断题（说明理由，不要只写对错）**

1. 只要用了参数化查询，就绝对不会被注入了。
2. 把 `'` 过滤掉就能防注入。
3. Django 的 `.filter(username=x)` 会"消毒"用户输入里的引号。
4. `ORDER BY` 后面的字段名也可以用 `?` 参数化。
5. LIKE 查询里用了参数化，用户传 `%` 也没关系。
6. `executescript()` 和 `execute()` 一样安全，只是能跑多条语句。
7. 一台数据库只开一个在用的账号（root）最省事，反正有参数化兜底。

**Q5. 修复下面的代码（4 处问题）**

```python
import sqlite3

def search(conn, keyword, sort_field, page_size):
    sql = ("SELECT id, title FROM articles WHERE title LIKE '%" + keyword + "%' "
           "ORDER BY " + sort_field + " LIMIT " + str(page_size))
    return conn.execute(sql).fetchall()

def update_profile(conn, uid, new_name):
    stored = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()[0]
    conn.execute(f"UPDATE users SET username = '{new_name}' WHERE username = '{stored}'")
    return True
```

要求：指出每一处的风险类型（UNION/盲注/通配符/标识符/二次注入…），
然后给出**参数化 + 白名单**的修复版本。

---

### 进阶题（动手 + 攻防视角）

**Q6. 给检测器加一条规则**

在 `code/03-sqli-detector.py` 的 `SQLSourceAuditor` 里新增一个检测点：
**`cursor.execute(sql % params)` 形式**（即第一个参数是 `BinOp(Mod)`，
且左操作数是一个**变量名**而不是字符串常量）。

要求：
1. 用 AST 判断：`arg0` 是 `BinOp`，`op` 是 `Mod`，`left` 是 `Name`；
2. 报 HIGH，原因写明"参数被 `%` 提前格式化，参数化被掉包"；
3. 在内置 `SAMPLE_CODE` 里加一个函数触发它（例如 `conn.execute(sql % (x,))`），
   确认检测器能报出来；
4. 思考：为什么这条规则不能简单用"找 `%`"的正则实现？

**Q7. 写一个"参数化改造"小工具（选做）**

写一个脚本 `refactor_hint.py`：扫描给定 Python 文件，
对每一处 `execute(<含用户变量的字符串>)` 输出一条**改造建议**，格式：

```
文件: app/dao.py:42
现状: conn.execute(f"SELECT * FROM users WHERE id = {uid}")
建议: conn.execute("SELECT * FROM users WHERE id = ?", (uid,))
```

提示：可以直接复用示例 03 的 `SQLSourceAuditor`，只改报告输出。
（**不要**尝试自动改写代码并覆盖原文件 —— 静态改写风险极高，
本练习只要求"给出建议"。）

**Q8. 给本地靶场写一套注入回归测试**

仿照 `code/03-sqli-detector.py` 的 `dynamic_scan()`，为你自己写的一个
"有漏洞的迷你 DAO"（3~5 个函数，包含一个安全、一个不安全）写测试脚本：

要求：
1. 探针只使用示例 03 里那 4 个**通用语法探针**（恒真/恒假/UNION/单引号），
   不引入任何针对特定数据库的攻击载荷；
2. 断言"安全函数全部无信号、不安全函数全部报警"；
3. 输出 PASS/FAIL 汇总并设置退出码；
4. 思考：如果哪天有人把安全函数改回拼接，这套测试会在哪一步失败？

**Q9. 最小权限演练（SQL 层面）**

在本地 sqlite3 里做实验：

1. 创建两张表 `users` 和 `secrets`；
2. 用 `CREATE VIEW` 或"只读连接"的方式，让一个"报表查询"函数的
   SQL 里**即使被注入了 `UNION SELECT ... FROM secrets` 也读不到数据**
   （提示：sqlite 可用 `PRAGMA query_only`、只挂载需要的表到单独连接、
   或用视图暴露白名单字段）；
3. 说明：为什么"最小权限"是参数化之外**第二重要**的防线？
   它能防住"参数化漏了一处"的情况吗？

---

### 挑战题（综合设计，无唯一答案）

**Q10. 设计一个"注入免疫"的数据访问层**

为一个中型项目设计数据访问层（DAL），要求覆盖：

- **接口形状**：只暴露 `find_by_id / find_by_conditions / insert / update / delete`，
  内部统一参数化，禁止调用方直接拿 cursor；
- **标识符处理**：排序、分页、表名如何用白名单映射（写出数据结构）；
- **日志规范**：记录什么、脱敏什么、不记录什么；
- **错误处理**：对外的错误码设计，异常如何只进服务端日志；
- **CI 防线**：静态检测 + 动态探针如何接入流水线，失败阈值怎么定；
- **应急响应**：假设线上真被注入了，你的 5 步处置流程是什么
  （提示：隔离→取证→修复→轮换凭证→复盘）。

请用 **1 张分层架构图 + 1 张接口清单表 + 1 份 CI 检查清单** 呈现结论。

**Q11. 复盘一次公开的 SQL 注入事件**

选择一起有公开分析的 SQL 注入事件（如 2011 年索尼 PSN、
2015 年 TalkTalk、或 OWASP 公开案例），回答：

1. 注入点出现在哪个功能上？输入是怎么进入 SQL 的？
2. 为什么"有 WAF / 有开发规范"仍然没挡住？
3. 攻击者最终拿到了什么？业务损失如何？
4. 如果当时做了"参数化查询 + 最小权限 + 统一错误处理"，哪一步会被拦住？
5. 从这个案例里，你能提炼出哪一条**可写进团队规范**的规则？

> ⚠️ 只做公开资料的**学习与复盘**，禁止对涉事系统或任何未授权目标做实际测试。

---

## 🎯 自测标准

| 水平 | 标准 |
|---|---|
| 及格 | 能说清注入的根因，能默写五类注入分类表，能跑通 3 个示例代码 |
| 良好 | 能解释参数化的两阶段协议机制，能独立完成 Q5 的修复与 Q8 的回归测试 |
| 优秀 | 能扩展静态检测器（Q6）、设计出 Q10 的 DAL 方案，并能讲清"纵深防御七层"的分工 |

---

## 🔍 自查小工具（贴到你的项目里用）

```bash
# ① 找"SQL 关键字 + f-string/加号/%" 的粗略线索（正则只能给线索，精确判断用示例 03）
grep -rnE '(SELECT|INSERT|UPDATE|DELETE|WHERE)[^"]*(f"|f\x27|\+ *(col|name|id|user|key))' --include='*.py' .

# ② 找最容易出事的 API 使用点
grep -rnE '\.(execute|executemany|executescript)\(|\.(raw|extra|RawSQL|text)\(|cursor\(' --include='*.py' .

# ③ 用 AST 检测器做精确判断（推荐，误报少）
python3 code/03-sqli-detector.py $(git ls-files '*.py' | head -50)
```

> ✨ 记住：**grep 给线索，AST 给结论，动态探针给证据** —— 三层配合才算完整。

---

## 📚 延伸阅读（建议自行搜索原文）

- OWASP — SQL Injection Prevention Cheat Sheet（**首推**，含 Query Parameterization 章节）
- OWASP Top 10（2021）A03: Injection
- CWE-89: Improper Neutralization of Special Elements used in an SQL Command
- SQLite 官方文档 — `sqlite3` Python 模块 / `PREPARE`、`EXECUTE` 语句与参数绑定
- PostgreSQL 文档 — Prepared Statements（含 `PREPARE` / `EXECUTE` 协议细节）
- PortSwigger Web Security Academy — SQL Injection 实验（**免费靶场，合法练手**）
- 《SQL 注入攻击与防御》（Justin Clarke 等）—— 系统讲原理与各数据库差异
