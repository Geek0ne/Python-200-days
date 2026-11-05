# Day 189 API 速查 — SQLite 资产库

## 1. 表结构

~~~sql
-- 批次
CREATE TABLE scans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,          -- UTC ISO8601
    source     TEXT NOT NULL,          -- nmap-xml / masscan / manual
    note       TEXT
);

-- 当前状态（每个自然键一行）
CREATE TABLE assets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ip         TEXT NOT NULL,
    port       INTEGER NOT NULL,
    proto      TEXT NOT NULL DEFAULT 'tcp',
    service    TEXT,
    banner     TEXT,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    state      TEXT NOT NULL DEFAULT 'active'
               CHECK (state IN ('active', 'missing', 'gone')),
    miss_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ip, port, proto)
);

-- 观测流水（只追加）
CREATE TABLE scan_assets (
    scan_id  INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    seen_at  TEXT NOT NULL,
    PRIMARY KEY (scan_id, asset_id)
);

-- 变更审计（只追加）
CREATE TABLE events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id   INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    seen_at   TEXT NOT NULL,
    event     TEXT NOT NULL,
    ip        TEXT NOT NULL,
    port      INTEGER NOT NULL,
    proto     TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT
);

CREATE INDEX idx_assets_state ON assets(state);
CREATE INDEX idx_events_seen ON events(seen_at);
CREATE INDEX idx_events_event ON events(event);
~~~

## 2. 常用查询

### 当前活跃资产

~~~sql
SELECT ip, port, service, last_seen
  FROM assets
 WHERE state = 'active'
 ORDER BY ip, port;
~~~

### 本周新增

~~~sql
SELECT ip, port, service, first_seen
  FROM assets
 WHERE date(first_seen) >= date('now', '-7 days')
 ORDER BY first_seen DESC;
~~~

### 某资产的端口历史

~~~sql
SELECT date(s.started_at) AS day, COUNT(*) AS seen
  FROM scan_assets sa
  JOIN scans s ON s.id = sa.scan_id
  JOIN assets a ON a.id = sa.asset_id
 WHERE a.ip = ? AND a.port = ?
 GROUP BY day
 ORDER BY day;
~~~

### 每天最后一次快照的资产数

~~~sql
WITH last_scan AS (
    SELECT date(started_at) AS d, MAX(id) AS scan_id
      FROM scans
     GROUP BY date(started_at)
)
SELECT l.d, COUNT(sa.asset_id) AS open_ports
  FROM last_scan l
  LEFT JOIN scan_assets sa ON sa.scan_id = l.scan_id
 GROUP BY l.d
 ORDER BY l.d;
~~~

### 每天各类事件数

~~~sql
SELECT date(seen_at) AS day, event, COUNT(*) AS n
  FROM events
 GROUP BY day, event
 ORDER BY day, event;
~~~

### 连续两次以上未观测（候选下线）

~~~sql
SELECT ip, port, service, miss_count, last_seen
  FROM assets
 WHERE state != 'gone' AND miss_count > 0
 ORDER BY miss_count DESC, last_seen;
~~~

## 3. Python sqlite3 API

| API | 作用 | 注意 |
|---|---|---|
| `sqlite3.connect(path)` | 打开/创建库 | 默认 `isolation_level=""` 自动开事务 |
| `conn.row_factory = sqlite3.Row` | 行支持按列名访问 | 比 tuple 下标可读 |
| `conn.execute(sql, params)` | 单条语句 | 必须用参数绑定，不要拼字符串 |
| `conn.executemany(sql, seq)` | 批量 | 仍需外层事务 |
| `conn.executescript(sql)` | 执行多语句 | 会隐式提交 |
| `with conn:` | 事务上下文 | 异常回滚，正常提交 |
| `conn.execute("PRAGMA foreign_keys=ON")` | 打开外键 | **每条连接**都要设 |
| `conn.execute("PRAGMA journal_mode=WAL")` | WAL 模式 | 持久化到库文件 |
| `conn.execute("PRAGMA synchronous=NORMAL")` | 降低 fsync | WAL 下通常安全，崩溃可能丢最后事务 |
| `conn.execute("VACUUM INTO ?", (path,))` | 在线备份 | 生成的副本不含 WAL |

## 4. UPSERT 两种写法

### 手写（本课采用）

~~~python
row = conn.execute(
    "SELECT id FROM assets WHERE ip=? AND port=? AND proto=?",
    (ip, port, proto),
).fetchone()
if row is None:
    cur = conn.execute("INSERT INTO assets(...) VALUES (...)", (...))
    asset_id = cur.lastrowid
    status = "new"
else:
    asset_id = row["id"]
    conn.execute("UPDATE assets SET last_seen=?, service=COALESCE(?, service) WHERE id=?",
                 (seen_at, service, asset_id))
    status = "existing"
~~~

优点：能拿到 `asset_id` 和 `new/existing`；缺点：两次往返。

### 原生

~~~sql
INSERT INTO assets(ip, port, proto, service, first_seen, last_seen)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(ip, port, proto) DO UPDATE SET
    last_seen = excluded.last_seen,
    service   = COALESCE(excluded.service, assets.service);
~~~

优点：一次往返；缺点：拿不到"是否新插入"，需要 `RETURNING` 或额外查询。
SQLite 3.35+ 支持 `RETURNING`。

## 5. 陷阱清单

| 陷阱 | 现象 | 正确做法 |
|---|---|---|
| 用自增 id 做集合差 | 每次都是"全新增/全消失" | 用自然键 |
| 按 COUNT 判断变化 | 一进一出显示"无变化" | 比较键集合 |
| 忘记 `PRAGMA foreign_keys=ON` | 删除父表后子表留孤儿 | 每条连接显式打开 |
| 自动提交逐条写 | 每秒几十行 | `BEGIN/COMMIT` 或 `executemany` |
| `date(now)` 用本地时区 | 跨时区差一天 | 存 UTC，展示时再转换 |
| `CREATE TABLE IF NOT EXISTS` | 上游没写也查不到错 | 加行数对账/断言 |
| banner 直接比较 | 随机 token 导致天天 `changed` | 归一化后再哈希 |
| WAL 文件未备份 | 恢复后丢最近数据 | `VACUUM INTO` 或 `.backup` |
| 在 `executemany` 后读 `cursor.rowcount` | 值不可靠 | 单独 `SELECT COUNT(*)` |

## 6. 索引选择

| 查询模式 | 建议索引 |
|---|---|
| `WHERE ip=? AND port=?` | `UNIQUE(ip, port, proto)`（自动） |
| `WHERE state='active'` | 视数据分布；active 占 95% 时通常无用 |
| `WHERE service=?` | `idx_service`，选择性高时收益明显 |
| `WHERE date(seen_at)=?` | 函数包裹列会让索引失效，改用范围条件 |
| `ORDER BY last_seen DESC LIMIT 20` | `idx_last_seen` |

~~~sql
-- 让 date(seen_at)=? 走索引的写法
WHERE seen_at >= ? AND seen_at < ?
~~~
