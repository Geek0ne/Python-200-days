# Day 185 练习与验收清单 —— 一键部署与端到端验收

> 所有命令可直接复制执行；每个脚本都带 `--self-test`（离线、零第三方依赖）。

---

## ✅ 今日完成清单

- [ ] 读完 `concepts.md`，能说清"存活"和"就绪"为什么不能合并
- [ ] 跑通 00：看到 `/healthz=200` 而 `/readyz=503` 的那段时间窗
- [ ] 跑通 01：亲眼看到"陈旧 PID 被识破"和"优雅停机成功"
- [ ] 跑通 02：正常部署 → 坏版本自动回滚 → 端口冲突被预检拦截（三个场景都跑）
- [ ] 跑通 03：9 项验收断言全绿（含在途请求被做完）
- [ ] 跑通 04：看 naive 逻辑**真的**杀掉了一个无关进程
- [ ] 跑通 05：拿到自己机器上的 MTTR / 发现延迟 / 停机对比数字
- [ ] 收尾：无残留进程、端口释放、临时目录已删

### 一键离线自证（不起任何外部依赖）

```bash
cd ~/code/Learn-Python/days/day-185-运维平台-一键部署与验收/code
for f in 0*.py; do echo "== $f"; timeout 120 python3 "$f" --self-test || echo "❌ $f 失败"; done
```

### 真机端到端（本课实验手册的精简版）

```bash
cd ~/code/Learn-Python/days/day-185-运维平台-一键部署与验收/code
STATE=/tmp/d185-demo; PORT=8400
rm -rf $STATE && mkdir -p $STATE
printf '%s' '[{"host":"web-01"},{"host":"web-02"}]' > $STATE/hosts.json

# 1) 正常部署
python3 02-deploy-oneclick.py --port $PORT --version v1.0.0 --state-dir $STATE --data $STATE/hosts.json
curl -s 127.0.0.1:$PORT/readyz; curl -s 127.0.0.1:$PORT/api/v1/hosts

# 2) 坏版本 → 自动回滚
python3 02-deploy-oneclick.py --port $PORT --version v1.1.0-bad --state-dir $STATE --simulate-bad-release
echo "退出码=$?（4=已自动回滚）"; cat $STATE/current.json

# 3) 验收
python3 03-smoke-acceptance.py --port $PORT

# 4) 故障演练（D1 kill -9 / D2 端口冲突 / D3 停机对比）
python3 05-drill-chaos.py --json $STATE/drill.json

# 5) 清理
python3 - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("r", "01-process-runner.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.stop_service("/tmp/d185-demo/api.pid"))
PY
ss -ltn | grep $PORT || echo "端口已释放"
rm -rf $STATE
```

---

## 📝 基础练习

### 练习 1：给就绪探针加一个"依赖检查"
现在的 `/readyz` 只看进程自己的 warmup 状态。请让它额外检查一个"外部依赖"
（本地可以用"某个文件是否存在 / 某个端口是否可连"来模拟）。
要求：依赖挂了 → `503` 且 body 里说明是哪个依赖；依赖恢复 → 自动变回 `200`。
思考：为什么这个检查**不能**放进 liveness 探针？（提示：liveness 失败会触发重启，
依赖抖动时你会把健康的应用反复重启 —— 这就是"抖动放大成雪崩"的经典机制。）

### 练习 2：给 `validate_pid` 加一条"启动时间"判据
现在身份靠 `cmdline`。再加一条：把启动时间（`/proc/<pid>/stat` 的第 22 个字段
`starttime`，单位 jiffies）写进 pidfile，校验时比对。
说明：这条能解决 `cmdline` 解决不了的哪种情况？（提示：同一份代码被起了两次 ——
比如运维平台自己重启时旧实例没死干净，两个进程 cmdline 一模一样。）

### 练习 3：让部署脚本支持 `--rollback-only`
实现"我只想回滚到 `current.json` 里的上一个版本"这个动作（不部署新版）。
要求：能从上一次 `history.jsonl` 里找出上一个可用版本号，并且回滚后要跑一遍
业务验收（不能只重启就算完）。

### 练习 4：把验收断言搬到 CI
把 `03-smoke-acceptance.py` 包成"退出码即结论"的形式（已经是了），
然后写一个 GitHub Actions 步骤：构建 → 起服务 → 跑验收 → 失败则 red。
思考：为什么"验收脚本在 CI 里跑"比"人在发布后点两下"更可靠？

---

## 🚀 进阶挑战

### 挑战 1：实现真正的"零停机"（蓝绿切换）
本课是原地替换（有秒级空窗）。改造为蓝绿：
- 同时起 v1（端口 A）与 v2（端口 B）；
- 用一个小反向代理（标准库即可：`http.server` 转发）把流量切到 B；
- 切换失败（B 的验收不过）→ 切回 A。
验收标准：切换过程中持续压测（每秒 10 次请求），**不允许出现任何非 200**。

### 挑战 2：把 MTTR 拆成分项指标并导出
现在 `05-drill-chaos.py` 只打印一次时间线。请改成：
- 重复 20 轮 D1，输出 `detect_latency_s` / `restart_to_ready_s` / `mttr_s` 的
  P50/P95/最大值（真数字，不是感觉）；
- 解释为什么这里的 P95 比平均值更该被用来定告警阈值。

### 挑战 3：加"部署前置检查"的清单化
把 `preflight()` 改成一个可扩展的检查清单（每项是一个函数，返回 (ok, msg)）：
磁盘空间、Python 版本、目标端口身份、state 目录可写、上一版本二进制存在、
必要环境变量齐全。要求：任何一项失败都打印**全部**失败项（不是只报第一个），
因为发布时要一次看全所有问题。

### 挑战 4：给回滚加上"熔断"
如果同一个版本连续回滚 3 次，脚本应该**拒绝再部署它**（把它标记为 bad release），
并把这件事写进 `history.jsonl`。
思考：这和 K8s `progressDeadlineSeconds` 的语义有什么异同？

### 挑战 5：演练"磁盘写满"时的日志降级
用 `fallocate` 造一个 1MB 的小分区（或 `tmpfs`），把日志目录放进去并写满，
验证：日志写失败时服务**不能崩**，而要以明确的方式降级（丢日志 + 记一条"我在丢日志"的告警）。
这是"日志系统自身也需要可观测"的练习（呼应 Day 184 的 spill 降级）。

---

## 🧪 验收标准（能不能算"今天过关"）

| 项 | 达标线 |
|---|---|
| 离线自证 | 6 个脚本 `--self-test` 全绿 |
| 就绪语义 | 能亲眼看到 `/healthz=200` 而 `/readyz=503` 的时间窗 |
| 自动回滚 | 坏版本退出码为 4，且 `current.json` 仍是上一个好版本 |
| 停机质量 | SIGTERM 时在途请求返回 200，进程随后 <3s 退出 |
| 演练数字 | 至少报出 3 个实测数字（发现延迟 / MTTR / 停机对比） |
| 安全边界 | 端口被非本服务占用时，预检失败且占用者存活 |
| 卫生 | 无残留进程、端口释放、临时目录已删 |
