# Day 195 练习与验收 — 运维、加密与交付

> 先跑通「本机验收」，再做题。所有命令都在 `days/day-195-运维-加密与交付/code` 目录下执行。

## 一、本机验收（必须全部打勾）

### 1. 离线自检（不需要 Docker、不占端口）

```bash
cd days/day-195-运维-加密与交付/code
for f in ops_lib.py crypto_lib.py 01-retry-backoff.py 02-crypto-envelope.py \
         03-api-auth.py 04-logging-alert.py app.py; do
  python3 "$f" --self-test || echo "FAIL: $f"
done
```

**预期**：7 行 ✅，没有 FAIL。

### 2. 本地起服务 + 验收

```bash
WORK=$(mktemp -d)
API_SECRET=dev-secret DATA_DIR="$WORK" python3 app.py --port 18095 &
APP_PID=$!
sleep 2
python3 smoke_test.py --url http://127.0.0.1:18095 --secret dev-secret
curl -s http://127.0.0.1:18095/readyz
kill $APP_PID; rm -rf "$WORK"
```

**预期**：四行 ✅ + `SMOKE PASS`；readyz 返回 `{"status": "ready", "kid": "local"}`。

### 3. 容器部署（需要 Docker）

```bash
./deploy.sh --tag v1
docker inspect -f 'health={{.State.Health.Status}} user={{.Config.User}} readonly={{.HostConfig.ReadonlyRootfs}}' learn195-app
curl -s http://127.0.0.1:18095/healthz
./deploy.sh --down
```

**预期**：
```text
SMOKE PASS
[deploy ...] ✅ 部署成功：learn195-app:v1
health=healthy user=app readonly=true
{"status": "ok", "pid": 1}
```

### 4. 回滚演练（可选但强烈建议）

```bash
docker build -t learn195-app:broken -f broken/Dockerfile broken
./deploy.sh --ref learn195-app:broken --no-build   # 预期非 0 退出，但服务回到 v1
python3 smoke_test.py --url http://127.0.0.1:18095 --secret demo-api-secret-change-me
```

**预期**：日志出现 `健康检查失败（unhealthy）` 与 `回滚到 learn195-app:v1`；回滚后 SMOKE PASS。

### 5. 清理确认

```bash
docker ps -a --format '{{.Names}}' | grep learn195 || echo 'no containers'
docker volume ls --format '{{.Name}}' | grep learn195 || echo 'no volumes'
docker images --format '{{.Repository}}:{{.Tag}}' | grep learn195 || echo 'no images'
```

**预期**：三行 no …；端口 18095 已释放。

---

## 二、基础练习

### 练习 1：给重试加“按错误类型选择策略”

修改 `ops_lib.retry_call`，让 429 的等待**至少等于** Retry-After、且不应用抖动；
让 5xx 使用 full jitter。写一个 self-test 证明两者行为不同。

验收：`python3 -c "import ops_lib"` 无副作用；你的测试里 fake sleep 序列可预测。

### 练习 2：给日志加采样

实现 `JsonLogger.sample(every_n)`：同一个 event 每 N 条只输出 1 条，但计数器照常累加。
要求：输出里带 `sampled=true` 与 `suppressed` 字段。

验收：连续写 100 条 `request` 日志，输出 10 条（N=10），且总计数仍是 100。

### 练习 3：把 AAD 用错，观察后果

把 `app.get_record` 里的 `aad=row[0].encode()` 改成 `aad=b''`，
然后用两条记录交叉读取，解释为什么“还能读出来”，并说明这为什么危险。

验收：能用自己的话写出“密文搬家”攻击的完整步骤。

---

## 三、进阶挑战

### 挑战 1：NonceStore 换成 SQLite 实现

当前 nonce 表在内存，多副本会失效。用 SQLite 建 `nonces(nonce PRIMARY KEY, expires_at)` 表，
实现原子 `INSERT OR IGNORE`，并清理过期行。

验收：两个独立进程共享同一个 DB 文件，重放第二个进程的 nonce 必须返回 409。

### 挑战 2：给部署脚本加“金丝雀”

在同一个镜像上同时起 v1（18095）和 v2（18096），用脚本把 10% 的 smoke 请求打到 v2；
v2 的 p95 超过 v1 两倍或错误率 > 1% 就自动摘掉 v2 并回滚。

提示：不要用随机数直接决定生产流量；真实系统在网关层按 header/cookie 分桶。

### 挑战 3：把密钥轮换做成后台任务

实现 `rotate_keys.py`：新增 k3 → 把所有 `kid != k3` 的记录重加密 → 校验解密 → 删除旧 key。
要求：可中断、可重入、每批 100 条、失败时打印 record_id 并继续。

验收：`--self-test` 在临时目录里造 1000 条记录，轮换后 1000 条全部可解，且 kid 都是 k3。

---

## 四、复盘问题（写进你的笔记）

1. 你所在的项目里，哪一个 POST 接口最需要 Idempotency-Key？为什么？
2. 如果明天密钥泄露，你的系统多久能完成轮换？瓶颈在哪一步？
3. 你们的健康检查如果哪天开始误报，最先坏掉的会是什么？

---

## 五、提交前自检

```bash
git status --short
find . -name '__pycache__' -o -name '.master-key' -o -name 'data' | head
```

**预期**：`.master-key`、`data/`、`__pycache__/` 都不应出现在 git status 里（已在 .gitignore 中）。