# Day 192 完成清单与练习

## 今日完成清单

- [ ] 能说清"代理列表"和"代理池"的区别（至少四个职责）
- [ ] 能解释为什么健康检查必须是"200 + 预期标记"，而不是 TCP 能连
- [ ] 能解释 407 与 401 的区别，以及为什么 Proxy-Authorization 不能透传
- [ ] 能解释 CONNECT 隧道与"HTTP 通、HTTPS 全灭"的关系
- [ ] 能写出 score = success_rate² / (1 + EWMA 延迟) 并说明平方的意义
- [ ] 能画出闭→开→半开→闭的熔断状态机
- [ ] 能解释为什么"轮换不等于提速"，以及每出口令牌桶的必要性
- [ ] 能说清粘滞会话的适用场景与失效条件
- [ ] 跑通四个脚本的 \`--self-test\`，全部 PASS

---

## 本机复现命令（逐条执行）

\`\`\`bash
cd ~/code/Learn-Python/days/day-192-proxy-pool/code

# 1. 实验台自证（8 项）
python3 00-proxy-lab.py --self-test

# 2. 基础代理池（7 项）
python3 01-basic-proxy-rotation.py --self-test

# 3. 三个翻车现场（6 项；无外网加 --offline）
python3 02-pitfall-connect-and-env.py --self-test

# 4. 生产级池（9 项）
python3 03-production-proxy-pool.py --self-test

# 5. 一条命令串跑，任一失败即停
for f in 00-proxy-lab.py 01-basic-proxy-rotation.py \
         02-pitfall-connect-and-env.py 03-production-proxy-pool.py; do
  echo "== $f =="; python3 "$f" --self-test || exit 1
done
\`\`\`

**期望**：依次输出 \`8/8 项通过\`、\`7/7 项通过\`、\`6/6 项通过\`、\`9/9 项通过\`。
**若失败**：先看端口是否被占用（\`ss -ltn | grep 127.0.0.1\`），
脚本用的是随机空闲端口，正常不会冲突；再确认 Python ≥ 3.10。

---

## 练习 1（基础）：给健康检查加"延迟上限"

当前 \`check_one()\` 只看状态码。请增加：延迟超过 \`max_latency_ms\` 的出口仍算健康，
但 \`healthy\` 与 \`usable\` 分开——\`healthy\` 表示能通，\`usable\` 表示还能接业务。

**验收**：构造一个 \`delay=0.5\` 的代理，设置 \`max_latency_ms=200\`，
断言 \`healthy is True and usable is False\`。

**提示**：不要直接把 \`healthy=False\`，否则你分不清"坏了"和"慢"。

---

## 练习 2（基础）：实现"最少使用"策略

给 \`ProxyPool\` 增加 \`strategy="least_used"\`：每次选 \`requests\` 最小的可用出口，
同数时选最久没用的。

**验收**：9 个请求后三个出口的请求数为 3/3/3；连续 2 个请求不会落在同一出口。

**思考**：它和轮询有什么区别？在出口性能差异很大时，哪个更合理？

---

## 练习 3（进阶）：把粘滞迁移记成指标

给 \`ProductionProxyPool\` 增加：

- \`migrations: list[dict]\`，每次粘滞域因冷却换出口时追加
  \`{"domain": ..., "from": ..., "to": ..., "reason": ...}\`；
- \`metrics()["migration_rate"] = 迁移次数 / 粘滞会话数\`。

**验收**：让 shop 的固定出口在两次请求之间进入冷却，
断言发生 1 次迁移，且下一次请求落在新出口并保持粘滞。

---

## 练习 4（进阶）：实现半开探针

当前冷却到期后会直接参与正常评分竞争。请改成严格半开：

1. 冷却到期 → 状态 \`half_open\`，只允许 1 个请求；
2. 成功 → \`closed\`，权重恢复；
3. 失败 → \`open\`，冷却时间 ×2（上限 60s）。

**验收**：坏代理连续 3 轮"冷却→探针失败"后，冷却时长依次为 3s、6s、12s；
期间其他出口承担全部流量。

---

## 练习 5（挑战）：用真实代理做一次端到端

在你能控制的机器上起一个真实代理（squid / tinyproxy / 3proxy 任一），
用 \`HTTP_PROXY\` 之外的**显式**配置跑 20 个请求，记录：

- 每出口请求数、成功率、p50/p95；
- 杀掉代理进程后，池子多久发现（健康检查间隔 + 超时）；
- 把代理限速到 1 req/s 后，令牌桶是否真的把速率压住（用靶站计数验证）。

**产出**：一张 \`exports/metrics.json\` + 一段 200 字以内的结论。
**要求**：必须贴真实数字与命令，不接受"应该会"。
