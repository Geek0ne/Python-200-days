# Day 184 练习与验收清单 —— 日志收集 + 可视化

> 所有命令都可以**直接复制执行**。每个脚本都带 `--self-test`，
> 所以在没有外部服务的机器上也能先自证代码是对的（离线、零第三方依赖）。

---

## ✅ 今日完成清单

- [ ] 读完 `concepts.md`，能说清「为什么要结构化日志」而不是「日志加个格式」
- [ ] 跑通 01：人读格式 vs JSON Lines 的对比输出
- [ ] 跑通 02：起一个真实 HTTP 接收端，用 `curl` 打一条日志进去，再查 `/stats`
- [ ] 跑通 03：真机做一次 `mv app.log app.log.1` 轮转，确认采集器**没有丢**
- [ ] 跑通 03 `--naive`：用同一个轮转动作，确认 naive 模式**真的丢**
- [ ] 跑通 04：复现 `database is locked`，再用 WAL + `busy_timeout` 修掉
- [ ] 跑通 05：拿到本机自己的四组写入吞吐数字
- [ ] 跑通 06：从库里生成 ASCII 看板 + 单文件 HTML 报告
- [ ] 实验收尾：确认没有残留进程、没有残留端口、临时目录已删

### 一键离线自证（不需要起任何服务）

```bash
cd ~/code/Learn-Python/days/day-184-运维平台-日志收集与可视化/code
for f in 0*.py; do echo "== $f"; python3 "$f" --self-test || echo "❌ $f 失败"; done
```

### 真机端到端（本课实验手册的精简版）

```bash
cd ~/code/Learn-Python/days/day-184-运维平台-日志收集与可视化/code
mkdir -p /tmp/day184

# 1) 起接收端
python3 02-log-ingest-server.py --port 8099 --db /tmp/day184/logs.db &

# 2) 起采集器（抗轮转）
python3 03-log-collector.py --file /tmp/day184/app.log \
        --url http://127.0.0.1:8099/ingest --seconds 20 &

# 3) 造日志
python3 -c "
import json
p='/tmp/day184/app.log'
for i in range(5):
    open(p,'a').write(json.dumps({'level':'INFO','msg':'before-%d'%i})+chr(10))
"

# 4) 轮转（这一步才是重点）
mv /tmp/day184/app.log /tmp/day184/app.log.1
python3 -c "
import json
p='/tmp/day184/app.log'
for i in range(5):
    open(p,'a').write(json.dumps({'level':'INFO','msg':'after-%d'%i})+chr(10))
"

sleep 3
curl -s '127.0.0.1:8099/stats'        # 期望 INFO=10（轮转前后都不丢）

# 5) 看板
python3 06-log-report.py --db /tmp/day184/logs.db --html /tmp/day184/report.html

# 6) 清理
pkill -f '[l]og-ingest-server' ; pkill -f '[l]og-collector'
ss -ltn | grep 8099 || echo "端口已释放"
rm -rf /tmp/day184
```

---

## 📝 基础练习

### 练习 1：给结构化日志补一个字段，并让查询能用上
给 `01-structured-logging.py` 的 `JsonLineFormatter` 增加一个固定字段 `host`
（值取 `socket.gethostname()`），并说明：为什么用「格式化器统一加」比「每条日志手写」更好？
（提示：漏写一个字段的日志，会在按 host 聚合时变成"未知主机"，静默地把数据算错。）

### 练习 2：让接收端能按时间范围过滤
`02-log-ingest-server.py` 目前只支持 `/stats?window=N`。加一个
`/logs?level=ERROR&limit=20`：返回最近 N 条指定级别的原始行。
要求：参数缺失时给合理的默认值；`limit` 上限 100（防止有人 `limit=99999999` 把内存打爆）。

### 练习 3：把「半行」写进自证脚本
在 `03-log-collector.py --self-test` 里增加一个用例：**一条 JSON 被拆成三段**
（`a⏎b⏎c` 这种，中间还带空行），断言最终刚好产出 1 条完整行、且缓冲区内没有残留。
为什么中间的空行必须不能产生"空日志"？

### 练习 4：给写入失败加一条告警
现在 `Sender` 投递失败只是 `print` 到 stderr。改成：连续失败 3 次时向
`/tmp/day184/alerts.log` 追加一行 JSON 告警（含 `lines_lost_if_any`）。
思考：这条告警本身如果也写不进去，怎么办？（提示：日志系统的最后一道防线是 stderr + 退出码，
所以不要吞掉异常直接 `pass`。）

---

## 🚀 进阶挑战

### 挑战 1：让"重复入库"变成不可能（幂等）
本日实验中真实出现过：接收端响应慢 → 采集器重试 → **同一批日志入库两次**。
请设计并实现去重：在 `logs` 表加 `dedup_key`（如 `sha1(service+ts+msg+request_id)`）
并建 UNIQUE 索引，插入用 `INSERT OR IGNORE`。
验收标准：造 100 条日志，用 `curl` 把**同一批** POST 三次，`SELECT COUNT(*)` 必须仍是 100。

### 挑战 2：写一个"日志丢失检测"的对照实验
用 `wc -l` 数出应用写进文件的**总行数**，再取 `SELECT COUNT(*) FROM logs`，
两者差值必须为 0。然后故意把采集器换成 `--naive` 并做一次轮转，
证明差值 > 0，再把结论写成一句话贴在 README 里。
（这是把"日志丢了"从"感觉"变成"数字"的练习。）

### 挑战 3：把看板变成真正的"告警"
给 `06-log-report.py` 加 `--alert-error-rate 0.05`：当窗口内 ERROR 占比
超过阈值时，`exit 2`（而不是 0/1，方便区分"跑失败"和"触发了告警"）。
再用 cron/systemd timer 每分钟跑一次，把退出码接到你的告警通道。

### 挑战 4：压测接收端，找出它的天花板
用 `05-bench-insert.py` 的思路给接收端做压测：并发 4 个客户端，
每批 200 条，跑 30 秒，分别测 `batch_size=1/50/1000` 三种配置下的
**每秒入库条数**与 `database is locked` 出现次数。
要求给出表格 + 你机器上的真实数字，并解释"为什么 batch 越大不一定越好"。

### 挑战 5：换存储，验证理解
把 `LogStore` 换成"追加 JSONL 文件 + 按天切分"的实现（不用 SQLite），
保持 `query_summary` / `query_timeseries` 的接口不变（读时再扫文件）。
对比：查询延迟、写入吞吐、磁盘占用、崩溃安全。什么规模下你会换回 SQLite，什么规模下该上 Loki？

---

## 🧪 验收标准（能不能算"今天过关"）

| 项 | 达标线 |
|---|---|
| 离线自证 | 6 个脚本 `--self-test` 全绿 |
| 端到端 | 轮转前后共 10 条日志，库里 `COUNT(*)=10` |
| 反面验证 | naive 采集器在同一动作下丢行数 > 0 |
| 并发 | `04` 能复现 `database is locked`，且 `good` 模式成功 |
| 实测数字 | 至少报出 2 个本机实测吞吐/等待数字（不是引用的） |
| 卫生 | 无残留进程、端口释放、`/tmp/day184` 已删 |
