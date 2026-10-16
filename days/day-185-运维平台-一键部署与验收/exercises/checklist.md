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

