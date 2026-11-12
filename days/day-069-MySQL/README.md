# Day 069 — MySQL 基础：pymysql、SQL 进阶与备份恢复

> 🎯 **今日目标**：把最流行的开源关系库装进工具箱——pymysql 的连接与 CRUD、连接池的原理与实现、SQL 进阶（连接查询 / 子查询 / 索引与执行计划）、备份与恢复，最后用一个订单库实战完成建模与查询优化。

## 概述

Day 068 用 SQLite 走通了 SQL 的基本功，今天换到真正的服务端数据库 MySQL。核心差异有三点：**网络连接**（需要连接池）、**存储引擎与索引**（查询优化的主战场）、**运维职责**（备份恢复、权限）。SQL 语法本身 90% 通用，所以今天把重点放在"服务端数据库才有"的部分。

> 💡 本日代码设计为**双后端可运行**：安装了 `pymysql` 并有 MySQL 环境时走真库；没有环境时用 `--self-test` 在 SQLite 内存库上离线自检（SQL 逻辑通用，连接层差异在代码里显式标注）。

## 学习目标

- 掌握 pymysql 的连接、CRUD 与事务
- 理解连接池解决什么问题，能手写一个简易连接池
- 会用 EXPLAIN 分析查询、用索引优化慢查询
- 会用 mysqldump 做逻辑备份与恢复
- 能独立完成订单库的建模与查询优化

---

## 1. 环境准备

```bash
# Docker 一行起（开发用）
docker run -d --name mysql-dev -e MYSQL_ROOT_PASSWORD=dev123456 \
  -p 3306:3306 mysql:8

# 安装驱动
pip install pymysql
```

连接参数建议全部走环境变量，别写死在代码里：

```python
import os, pymysql

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DB", "testdb"),
    charset="utf8mb4",          # 支持 emoji，别用 utf8
    autocommit=False,            # 显式事务更安全
)
```

## 2. pymysql 连接与 CRUD

完整代码见 `code/01-mysql-crud.py`。要点：

```python
with conn.cursor() as cur:
    cur.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s)",   # 占位符是 %s
        ("alice", "alice@example.com"),
    )
    user_id = cur.lastrowid
conn.commit()   # 或 conn.rollback()
```

**事务的正确姿势**：提交失败必须回滚，否则连接处于未决状态。

```python
try:
    with conn.cursor() as cur:
        cur.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", (100, 1))
        cur.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", (100, 2))
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

## 3. 连接池

每次请求都 `connect()` 意味着一次 TCP 握手 + 认证（毫秒级开销，高并发下成为瓶颈）。连接池**预先建立、循环复用**一组连接：

```
请求 → 从池中借出连接 → 执行 SQL → 归还连接 → 响应
              ↓ 池空且未达上限
           新建连接
```

`code/02-connection-pool.py` 用 `queue.Queue` 实现了一个约 60 行的线程安全连接池（借出 / 归还 / 超时 / 无效连接剔除）。生产环境直接用成熟方案：

| 方案 | 说明 |
|------|------|
| SQLAlchemy QueuePool | ORM 项目的默认选择 |
| DBUtils PooledDB | 裸 pymysql 场景的轻量选择 |
| 云厂商 ProxySQL / RDS 连接代理 | 架构层解决 |

## 4. SQL 进阶：连接查询、子查询、索引与执行计划

完整示例见 `code/03-sql-advanced.py`。

**连接查询**——四种 JOIN 的语义差异是面试高频题：

```sql
SELECT o.id, u.name, o.amount
FROM orders o
INNER JOIN users u ON o.user_id = u.id;      -- 只保留两边都匹配的行

SELECT u.name, o.amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;      -- 左表全保留，右表可 NULL
```

**子查询**——先想 JOIN 再想子查询（多数情况下 JOIN 更易优化）：

```sql
-- 消费超过平均值的用户
SELECT * FROM orders
WHERE amount > (SELECT AVG(amount) FROM orders);
```

**索引与执行计划**——优化的第一步永远是看 EXPLAIN：

```sql
EXPLAIN SELECT * FROM orders WHERE user_id = 42;
```

| 关键列 | 怎么看 |
|--------|--------|
| type | `ALL`（全表扫描）→ 危险；`ref`/`range` → 可接受 |
| key | 实际命中的索引，`NULL` = 没走索引 |
| rows | 预估扫描行数，数量级比精确值重要 |
| Extra | `Using filesort` / `Using temporary` → 考虑加索引 |

**索引设计三原则**：最左前缀匹配、覆盖索引减少回表、选择性低的列（如性别）不适合单独建索引。

## 5. 备份与恢复

```bash
# 逻辑备份（结构 + 数据）
mysqldump -h127.0.0.1 -uroot -p testdb > backup.sql

# 恢复
mysql -h127.0.0.1 -uroot -p testdb < backup.sql

# 只备份结构 / 只备份数据
mysqldump -uroot -p --no-data testdb > schema.sql
mysqldump -uroot -p --no-create-info testdb > data.sql
```

`code/04-backup-restore.py` 演示了备份归档、恢复与保留 N 份的完整流程（MySQL 用 mysqldump，SQLite 用 backup API 等价复现）。生产备份三铁律：**定时执行、异地存放、定期演练恢复**——没演练过的备份等于没有备份。

## 6. 常见陷阱（实测）

| # | 陷阱 | 后果 | 正确做法 |
|---|------|------|----------|
| 1 | `charset="utf8"` | emoji 存成乱码 | 用 `utf8mb4` |
| 2 | 拼接 SQL | 注入（见 Day 072） | `%s` 占位符 |
| 3 | 长事务不提交 | 锁等待、回滚段膨胀 | 尽快 commit/rollback |
| 4 | `SELECT *` 大表 | 内存/带宽爆炸 | 按需取列，善用覆盖索引 |
| 5 | 索引列上用函数 | 索引失效 | `WHERE created_at >= ?` 而非 `DATE(created_at) = ?` |
| 6 | 忽略 EXPLAIN | 慢查询上线才发现 | 上线前对核心查询跑 EXPLAIN |
| 7 | root 账号跑业务 | 误操作无法兜底 | 建最小权限业务账号 |
| 8 | 不设连接超时 | 僵尸连接占满池 | `connect_timeout` + 池的失效检测 |
| 9 | 备份只写本地磁盘 | 磁盘损坏即全丢 | 异地 / 对象存储备份 |
| 10 | `LIMIT 1000000, 10` 深分页 | 越翻越慢 | 延迟关联或游标分页 |

## 7. 实战：订单库设计与查询优化

`code/05-order-db-project.py` 完整走一遍：

1. **建模**：users / products / orders / order_items 四张表，外键 + 合理字段类型
2. **灌数**：批量插入 1 万笔订单
3. **慢查询**："查某用户最近 30 天订单及商品名"的初始写法（子查询 + `SELECT *`）
4. **优化**：EXPLAIN 定位全表扫描 → 加联合索引 `(user_id, created_at)` → 延迟关联改写
5. **验收**：对比优化前后扫描行数与耗时

```bash
python code/05-order-db-project.py --self-test   # SQLite 离线跑全流程
python code/05-order-db-project.py               # MySQL 环境实测
```

## 8. 思考题

1. **占位符与 SQL 注入**：`cur.execute("SELECT * FROM users WHERE name = '%s'" % name)` 与 `cur.execute("SELECT * FROM users WHERE name = %s", (name,))` 有什么本质区别？为什么本日反复强调 `charset="utf8mb4"`？

**参考答案**

第一种是 **Python 字符串格式化**：先把用户输入拼进 SQL 文本，再整条发给数据库。数据库无法区分哪部分是「指令」、哪部分是「数据」。如果 `name` 是 `' OR '1'='1`，最终 SQL 变成 `WHERE name = '' OR '1'='1'`，条件恒真，整张用户表就被拖走了——这就是 SQL 注入。

第二种把 **SQL 模板与参数分开**交给驱动：参数只会被当成「值」处理（驱动负责转义或走预编译），里面的引号、分号不会改变语句结构，注入自然失效。

⚠️ 注意：pymysql 的 `%s` 是 DB-API 占位符，**不是** Python 的 `%` 格式化，千万别写成 `cur.execute(sql % params)`。占位符只能替代「值」，表名、列名、`ORDER BY` 方向都不能用它，这类需求要用白名单校验。

`utf8mb4` 的原因：MySQL 里的 `utf8` 其实是 `utf8mb3`，每字符最多 3 字节，而 emoji 是 4 字节，存进去会报错或变乱码。`utf8mb4` 才是完整的 UTF-8，建库、建表、连接三处都要统一。

2. **事务与回滚（代码）**：转账要执行两条 UPDATE，若第一条成功、第二条失败会发生什么？请给出可离线运行的最小示例，并说明 pymysql 中的等价写法。

**参考答案**

```python
# 依赖：仅标准库 sqlite3（本日「双后端」设计的离线版；真库需自行准备 MySQL 并 pip install pymysql）
import sqlite3

conn = sqlite3.connect(":memory:")     # 内存库，进程结束即消失，不留文件
conn.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
conn.executemany("INSERT INTO accounts VALUES (?, ?)", [(1, 500), (2, 500)])
conn.commit()

def transfer(conn, src, dst, amount):
    """转账：两条 UPDATE 必须同生共死"""
    try:
        with conn:                     # 正常结束自动 commit，抛异常自动 rollback
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?",
                         (amount, src))
            if amount > 1000:          # 模拟业务校验失败（此时钱已扣掉一半）
                raise ValueError("单笔限额 1000")
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?",
                         (amount, dst))
    except ValueError as e:
        print("已回滚:", e)

transfer(conn, 1, 2, 100)              # 成功：1 号 -100，2 号 +100
print(conn.execute("SELECT * FROM accounts").fetchall())

transfer(conn, 1, 2, 5000)             # 失败：第一条 UPDATE 也要撤销
print(conn.execute("SELECT * FROM accounts").fetchall())
```

预期输出：

```
[(1, 400), (2, 600)]
已回滚: 单笔限额 1000
[(1, 400), (2, 600)]
```

关键在于**事务的原子性**：两条 UPDATE 属于同一个事务，要么一起生效，要么一起作废。示例中第二次转账在扣款之后抛错，`with conn:` 触发回滚，余额回到 `(400, 600)`，钱不会凭空消失。如果没有回滚（或中途误提交），就会出现「A 扣了钱、B 没收到」的脏账。

换到 pymysql：把 `?` 换成 `%s`，把 `with conn:` 换成本日第 2 节的显式写法——`try: ... conn.commit()` / `except Exception: conn.rollback(); raise`。连接时保持 `autocommit=False`，让事务边界由自己掌控。

💡 提示：长事务不提交会一直持锁、撑大回滚段，务必尽快 commit/rollback；连接归还连接池之前，也要确认事务已经结束，否则下一个借用者会继承你的未决事务。

3. **索引与执行计划**：为什么 `WHERE DATE(created_at) = '2026-11-11'` 用不上索引，改成范围查询就可以？联合索引 `(user_id, created_at)` 的「最左前缀」是什么意思？`LIMIT 1000000, 10` 为什么越翻越慢？

**参考答案**

索引（InnoDB 的 B+ 树）里存的是**列的原始值**，靠有序性快速定位。一旦在索引列上套函数 `DATE(created_at)`，比较的对象变成了「函数计算结果」，树的有序性用不上了，只能逐行算一遍——EXPLAIN 里表现为 `type=ALL`、`key=NULL`（全表扫描）。改写成 `created_at >= '2026-11-11 00:00:00' AND created_at < '2026-11-12 00:00:00'`，列保持「裸露」，就能走 `range`。

**最左前缀**：联合索引 `(user_id, created_at)` 是先按 `user_id` 排序、`user_id` 相同再按 `created_at` 排序。所以 `WHERE user_id = ? AND created_at >= ?` 能用整条索引；`WHERE user_id = ?` 能用前一半；而只给 `created_at` 的条件，因为数据在全局上并不是按时间有序的，通常用不上这条索引。建索引时要把「最常用来等值过滤的列」放左边。

**深分页**：`LIMIT 1000000, 10` 的语义是「扫描并丢弃前 100 万行，再取 10 行」，偏移越大越慢。两种改法：延迟关联（先用覆盖索引取出这 10 行的主键，再 JOIN 回原表取完整列）；游标分页（记住上一页最后的 `id`，用 `WHERE id > ? ORDER BY id LIMIT 10`，每页成本恒定）。

⚠️ 注意：索引不是越多越好，每次写入都要维护索引；选择性低的列（如性别）单独建索引几乎没收益。`EXPLAIN` 是 MySQL 语法，SQLite 对应的是 `EXPLAIN QUERY PLAN`，输出含义不同；上面的执行计划验证需自行准备 MySQL 环境。

## 小结

- pymysql：`%s` 占位符 + 显式事务 + 必须回滚兜底
- 连接池是服务端数据库的标配，别让 TCP 握手成为瓶颈
- 优化慢查询的固定动作：EXPLAIN → 看 type/key/rows → 设计索引 → 验证
- 备份的价值在恢复，定期演练
