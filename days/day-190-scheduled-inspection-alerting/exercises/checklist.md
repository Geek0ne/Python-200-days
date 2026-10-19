# Day 190 练习与完成清单

> 所有命令都在 days/day-190-scheduled-inspection-alerting/ 下执行。
> 每个脚本都支持离线自检，不需要网络或外部服务（Docker 部分除外）。

---

## ✅ 完成清单（照着敲，逐条打勾）

### A. 调度（离线，约 1 分钟）

- [ ] `cd code && python3 01-scheduler-basic.py --self-test` → 5 项全 PASS
- [ ] `python3 01-scheduler-basic.py --simulate 24` → fixed-delay 漂移约 187s，fixed-rate 仅抖动
- [ ] `python3 01-scheduler-basic.py --outage 6` → 积压 24 次，实际只补 1 次、跳过 23 次
- [ ] 能口头解释：为什么 `max_catchup=1` 比"全补"更正确

### B. 幂等（离线，约 10 秒）

- [ ] `python3 02-retry-idempotency.py --self-test` → 6 项全 PASS
- [ ] `python3 02-retry-idempotency.py --demo` → 重复入队只留 1 行、effects=60/60、租约过期可重领
- [ ] 手动验证：把 `claim()` 的 SQL 改回只查 `status='pending'`，再跑 [E]，确认崩溃任务会卡死

### C. 告警降噪（离线 + 真 HTTP）

- [ ] `python3 03-alert-dedup.py --self-test` → 7 项全 PASS
- [ ] `python3 03-alert-dedup.py --e2e` → 500 条事件压成 2 条消息，critical 20/20
- [ ] `python3 03-alert-dedup.py --e2e --flaky-receiver` → 前 2 次 500，失败 2 次后成功，消息不丢
- [ ] `python3 04-pitfall-dedup-key.py` → v1 丢 4 条 critical、v2 发 125 条、v3 发 17 条零丢失

### D. 端到端验收（离线 + 真 HTTP）

- [ ] `python3 05-e2e-acceptance.py --self-test` → ACCEPTED
- [ ] `python3 05-e2e-acceptance.py --e2e` → ACCEPTED，退出码 0
- [ ] `echo $?` 确认是 0（不是靠肉眼看 PASS）

### E. 一键部署（需要 Docker）

- [ ] `bash deploy/deploy.sh up` → 构建 → 启动 → sink healthy → 收到 ≥1 条告警 → 打印 counts
- [ ] `bash deploy/deploy.sh status` → 两个容器均 healthy
- [ ] `curl -s http://127.0.0.1:18090/counts` → alerts 持续增长
- [ ] `bash deploy/deploy.sh down` → 容器 0、卷已删、端口 18090 已释放
- [ ] `ss -ltn | grep 18090` 无输出

### F. cron 重叠（可选，需要能改 crontab）

- [ ] 按 README「实验 3」搭一遍，亲眼看到 `database is locked`
- [ ] 加 `flock -n` 后看到 SKIP 而不是报错
- [ ] 实验后 `crontab -l` 已恢复原样（无 d190-cron 条目）

---

## 练习 1（基础）：把"跑完再睡"改成锚点网格

文件：新建 `code/my-fixed-rate.py`

要求：不看 01，自己实现 `next_fire(anchor, slot, interval, jitter)`：

1. 连续 1000 个 slot，偏移绝对值不超过 `interval * jitter`
2. 同一 slot 调 100 次结果完全一致（不允许直接 `random.random()`）
3. 打印第 1/500/1000 个 slot 的时刻

验收：

```bash
python3 code/my-fixed-rate.py | tail -3
```

---

## 练习 2（基础）：给告警漏斗加可选指纹策略

文件：`code/03-alert-dedup.py`

现在指纹是 `rule|asset`。改成 `fingerprint=strategy`，支持三种：

- `rule`：只看规则（复现 v1 丢高危）
- `rule+asset`：默认
- `rule+asset+port`：更细

要求：用 `--self-test` 证明 rule+asset 下 critical 仍 20/20，
且消息条数不超过 10。

---

## 练习 3（进阶）：实现静默窗口 API

文件：`code/03-alert-dedup.py`

新增方法 `silence_asset(prefix, until_ts, reason)`：

1. 按资产前缀匹配（`10.0.1.*`）
2. 静默期内只累加计数，不发送
3. 静默结束后，第一条消息里带「静默期间共 N 条被抑制」
4. 自测：静默 3 条 → 到期后第一条消息包含 N=3

---

## 练习 4（进阶）：给 worker 加跨轮去重

文件：`deploy/app/worker.py`

现状：worker 每轮把变更直接投递（sink 的 duplicates=3 就是这么来的）。

要求：

1. 用 SQLite 表 `alert_state(fingerprint PRIMARY KEY, last_sent REAL, last_sev TEXT)`
2. 同指纹 60s 内重复不发；severity 升高必须发
3. 在 README 补实测：改前 duplicates=X，改后 duplicates=0 且 critical 不丢

---

## 练习 5（挑战）：让部署脚本支持回滚

文件：`deploy/deploy.sh`

要求：

1. up 前把当前镜像 tag 记到 `.last-good`
2. up 失败（health 超时）自动 down 并恢复上一个 tag
3. 新增 `rollback` 子命令
4. 用"故意把 sink 的 /health 改成 500"验证回滚真的触发

---

## 自测记录表（打印出来填）

| 项目 | 命令 | 期望 | 实际 | 通过 |
|---|---|---|---|---|
| 调度自检 | 01 --self-test | 5 PASS | | ☐ |
| 幂等自检 | 02 --self-test | 6 PASS | | ☐ |
| 降噪自检 | 03 --self-test | 7 PASS | | ☐ |
| 翻车复现 | 04 --self-test | 5 PASS | | ☐ |
| 端到端 | 05 --e2e | ACCEPTED / exit 0 | | ☐ |
| 部署 | deploy.sh up | 收到 ≥1 告警 | | ☐ |
| 清理 | deploy.sh down | 端口释放 | | ☐ |
