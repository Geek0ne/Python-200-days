# Day 189 练习与验收清单

## 一、完成清单

- [ ] 能说清 `assets` 与 `scan_assets` 各自回答什么问题
- [ ] 能手写 `(ip, port, proto)` 的 UPSERT，并保留 `first_seen`
- [ ] 能解释为什么不能用自增 id 或行数做集合差
- [ ] 能画出 `active → missing → gone → revived` 状态机
- [ ] 能说明 `grace` 的语义以及它为什么依赖扫描频率
- [ ] 能写出"每天最后一次快照"的聚合 SQL
- [ ] 能解释 autocommit 为什么比单事务慢两个数量级
- [ ] 能生成并打开单文件 HTML 看板
- [ ] 知道 `CREATE TABLE IF NOT EXISTS` 带来的静默失败风险

## 二、真机验收（按顺序执行）

~~~bash
cd days/day-189-asset-store-trends/code

# 1. 全部自检
for f in 0*.py; do echo "== $f"; python3 "$f" --self-test || exit 1; done

# 2. 5 天端到端
rm -rf /tmp/d189-scans /tmp/d189.db* /tmp/d189.html
python3 00-fixture.py --out /tmp/d189-scans --days 5
python3 05-ingest-pipeline.py --scan-dir /tmp/d189-scans \
    --db /tmp/d189.db --out /tmp/d189.html

# 3. 核对事件
sqlite3 /tmp/d189.db \
  "SELECT event, COUNT(*) FROM events GROUP BY event ORDER BY event;"

# 4. 看板可打开
test -s /tmp/d189.html && grep -q '<svg' /tmp/d189.html && echo OK
~~~

**验收标准**：

- 5 个 `--self-test` 全部输出 ✅；
- 事件统计中 `appeared=5, changed=1, missing=1, gone=1`；
- 看板端口序列为 `5,5,6,5,5`；
- HTML 体积 > 3KB 且包含 `<svg`。

**清理**：

~~~bash
rm -rf /tmp/d189-scans /tmp/d189.db /tmp/d189.db-wal /tmp/d189.db-shm /tmp/d189.html
~~~

## 三、基础练习

### 练习 1：当前暴露面报表

写一个 SQL，输出 `state='active'` 的资产，按 `service` 分组统计数量，
并按数量降序。要求排除 `service IS NULL` 的行，并解释为什么 NULL 会被 `GROUP BY` 单独成组。

参考：

~~~sql
SELECT service, COUNT(*) AS n
  FROM assets
 WHERE state='active' AND service IS NOT NULL
 GROUP BY service
 ORDER BY n DESC, service;
~~~

### 练习 2：某 IP 的端口时间线

给定 `ip='10.20.0.11'`，列出该 IP 每个端口在哪些天被观测到，
输出 `(port, day, seen)`。思考：为什么必须 `JOIN scans` 才能拿到日期？

### 练习 3：区分"流量"与"存量"

分别写出：

1. 昨天新增的资产数（流量）；
2. 当前仍活跃、且首次出现于昨天的资产数（存量）。

解释两者为什么可能不同，以及日报应该用哪个。

## 四、进阶练习

### 练习 4：把 grace 改成时间口径

当前 `grace` 是"连续次数"。实现 `--max-silence-hours N`：
只要 `last_seen` 距今超过 N 小时且本次未观测，就直接 `gone`。

要求：

- 保留旧的次数口径作为 `--grace`，两者互斥；
- 自检覆盖"扫描间隔不均匀"的场景（例如 1 小时后又隔 30 小时）；
- 说明时间口径在时钟回拨时会出什么问题。

### 练习 5：事件去抖与归一化

某些 banner 含随机 token（如 `SSH-2.0-OpenSSH_8.9 session=ab12cd`）。
直接比较会让每天都产生 `changed`。

要求：

1. 写一个 `normalize_banner()`，去掉 `session=...`、时间戳、随机十六进制串；
2. 用归一化后的值参与比较；
3. 保留原始 banner 到 `banner_raw` 列，便于取证；
4. 自检：同一服务两次不同 token 的 banner，归一化后应相等。

### 练习 6（挑战）：历史归档与趋势保留

`scan_assets` 每天 10 万行，保留 3 年会到 1 亿行。设计归档方案：

- 近 90 天保留逐次观测；
- 90 天以前按天聚合到 `daily_stats(day, open_ports, new_assets, gone_assets)`；
- 趋势看板优先读 `daily_stats`，缺失的日期回退查明细；
- 写一个 `--archive-before YYYY-MM-DD` 命令，自检验证归档后
  "总端口趋势"与归档前一致（允许 ±0）；
- 说明归档为什么不可逆，以及备份策略。

## 五、提交前自检

~~~bash
python3 -m py_compile code/*.py
git status --porcelain
~~~

- 不提交任何 `*.db`、`*.html`、`out/`、`__pycache__/`；
- 每个脚本都能在空目录下 `--self-test` 通过；
- README 中粘贴的输出与本次真实运行一致。
