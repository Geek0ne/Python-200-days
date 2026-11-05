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

## 小结

- pymysql：`%s` 占位符 + 显式事务 + 必须回滚兜底
- 连接池是服务端数据库的标配，别让 TCP 握手成为瓶颈
- 优化慢查询的固定动作：EXPLAIN → 看 type/key/rows → 设计索引 → 验证
- 备份的价值在恢复，定期演练
