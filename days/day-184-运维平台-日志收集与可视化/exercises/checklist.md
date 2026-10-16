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

