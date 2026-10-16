# Day 182 · 练习与检查表

> 目标：亲手把 `采集 → 判定 → 去重 → 路由` 四段跑通，并**亲眼看见**抖动被过滤、
> 恢复通知被发出、通道挂了会降级。
> **前置**：Python 3.12+（本日脚本只用标准库，psutil 可选）；实验 4 需要 Docker。
> **全部命令都在 `days/day-182-运维平台-监控与告警/` 目录下执行。**

---

## 一、动手题（必做）

### 练习 1 — 看清一份指标快照（5 分钟）

```bash
cd code
python3 01-collect-metrics.py --once
python3 01-collect-metrics.py --once --json | python3 -m json.tool | head -20
python3 01-collect-metrics.py --backend proc --once
```

- [ ] 抄下 psutil 和 `/proc` 两个后端的 `cpu_percent / mem_percent / disk_percent`，四个数两两对比
- [ ] 快照 JSON 里有几个顶层字段？`app_metrics` 为什么是个数组？
- [ ] 不带 `--probe` 时快照有多少字节？（实测参考：257 字节）

<details><summary>参考答案</summary>

1. 两个后端字段**完全一致**（只有 `backend` 值不同）。但数值会有差异，本机实测
   `disk` 是 38.3%（psutil）vs 36.3%（`shutil.disk_usage`）——口径不同，数就不一样。
2. 顶层 4 个：`ts / host / host_metrics / app_metrics`。
   `app_metrics` 是数组，因为「应用」天然可能有多个（多端口、多副本、多依赖）。
3. 257 字节（无 probe 时）。监控数据便宜就便宜在这——只有数字，没有文本。

</details>

### 练习 2 — 让 `pending` 与 `dropped` 现形（10 分钟）

```bash
python3 02-threshold-engine.py --demo --scenario spike
python3 02-threshold-engine.py --demo --scenario sustained
```

- [ ] 在 spike 场景里，第 3 个 tick 值 = 41.0，状态是什么？事件是什么？
- [ ] 在 sustained 场景里，第 5、6 个 tick 值 = 94.0 / 95.0，为什么**没有**新事件？
- [ ] 把规则改成 `consecutive=1`（自己改 `default_rules()` 里的 `consecutive`），
      spike 场景的输出会变成什么？

<details><summary>参考答案</summary>

1. 状态 `ok`，事件 `dropped`——「毛刺被过滤（未达连续次数）」。
   注意它**不是 firing**，而且连 pending 都没留住。
2. 94 和 95 都在 firing 状态里，状态没变 → 引擎不吐事件。这正是「60 次采样 1 条通知」的机制来源。
3. `consecutive=1` 时，spike 第 2 个 tick（95.0）就会直接 firing，
   `dropped` 那条消失——**毛刺过滤能力完全取决于这个参数**。

</details>

### 练习 3 — 亲手复现「迟滞」（10 分钟）

```bash
python3 02-threshold-engine.py --demo --scenario hysteresis
```

- [ ] 从第 4 行到第 8 行，值分别是 88/86/84/82/81，**全都低于阈值 90**，为什么还是 firing？
- [ ] 把 `release` 从 80 改成 85，输出会怎么变？（先猜，再改）
- [ ] 如果把 `release` 写成 95（比 threshold 90 还大）会怎样？

<details><summary>参考答案</summary>

1. 因为**恢复的条件不是「低于 threshold」，而是「低于 release」**。81 > 80，所以还在告警。
   这就是迟滞：设两道线，进去难，出来也难。
2. 第 6 个 tick（84.0）就会 `resolved`——迟滞带从 (80,90] 缩窄成 (85,90]，
   更容易恢复，但也更容易被抖动重新触发。
3. 程序**当场报错**：`op='>' 时 release 必须 <= threshold（否则永远恢复不了）`。
   这是自检里的一条断言——这种参数写反了必须炸，不能静默。
   证据：改完运行会看到 `ValueError`，而不是「跑起来但永远不恢复」。

</details>

### 练习 4 — 复现抖动判定，并撞一次「窗口陷阱」（15 分钟，重点）

```bash
python3 02-threshold-engine.py --demo --scenario flap
python3 02-threshold-engine.py --self-test | grep -E '抖动|时间窗口'
```

- [ ] flap 场景里，从第几个 tick 开始事件带上「抖动中」的标注？
- [ ] 第 13 行的 pending **没有**抖动标注，为什么？
- [ ] 为什么自检里要专门有一条「窗口 2s、采样间隔 10s 时不会误判抖动」？

<details><summary>参考答案</summary>

1. 第 8 个 tick——此时 `flap_window=300s` 内已经累积了 4 次 firing/resolved 翻转。
2. 因为窗口滑过去了：第 13 行距离上一次翻转已经超过窗口，`_transitions` 被清空，
   `flapping` 被自动摘掉。**抖动标签是会自己消失的**，这是滑动窗口的特性。
3. 因为「抖动」的定义是**短时间内的反复翻转**，不是「历史上翻转过很多次」。
   同样的 7 次翻转，间隔 10 秒就是「偶尔出事」，不是「反复横跳」。
   用总次数判定会把长期稳定的系统误判成抖动。

</details>

### 练习 5 — 去重：让 10 条变成 1 条（10 分钟）

```bash
python3 04-alert-dedup-recovery.py --demo
python3 04-alert-dedup-recovery.py --self-test | grep -E '指纹|去重|恢复'
```

- [ ] demo 里 t=0/10/20 三条同 instance 的告警，动作分别是什么？
- [ ] t=330 那条为什么变成 `renotify`？
- [ ] 自己改一行：把 `make_alert(instance="ace")` 的 instance 改成 @"node-b"@，重跑，
      第 2 条的动作变成什么？

<details><summary>参考答案</summary>

1. `notify / suppress / suppress`——只有第一条真正打扰人，后两条只把 count 加到 3。
2. 因为故障从 t=0 一直没恢复，超过了 `resend_interval=300s`。
   「再提醒」是必要的：不然一个挂了一整晚的服务，中间只有开头响过一次。
3. 变成 `notify`。指纹里含 `instance`，换个实例就是**另一条告警**——
   这正是我们要的：A 机器和 B 机器同时 CPU 高，应该收到两条。

</details>

### 练习 6 — 亲手制造「恢复通知丢失」事故（10 分钟，本日最值钱的一题）

```bash
python3 - <<'EOF'
import importlib.util, json
spec = importlib.util.spec_from_file_location("d", "04-alert-dedup-recovery.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

a = m.make_alert(status="firing", value=95.0)
b = m.make_alert(status="resolved", value=40.0)
print("正常指纹 :", m.fingerprint(a), m.fingerprint(b), "->", m.fingerprint(a) == m.fingerprint(b))
print("含 status:", m.fingerprint(a, ("status",)), m.fingerprint(b, ("status",)),
      "->", m.fingerprint(a, ("status",)) == m.fingerprint(b, ("status",)))

s = m.AlertStore(extra_keys=("status",))
print("firing  ->", s.process(a, 0.0)["action"])
print("resolved->", s.process(b, 60.0)["action"])
EOF
```

- [ ] 正常指纹下，firing / resolved 的指纹相同吗？
- [ ] 加了 `status` 之后呢？resolved 的动作变成了什么？
- [ ] 用一句话解释：为什么「恢复通知」比「告警通知」更容易被写坏？

<details><summary>参考答案</summary>

1. 相同（`f05360f106d8 == f05360f106d8`）——所以恢复通知能匹配到活动告警。
2. 不同（`8570a82c242d != c6ab7a8c93fd`），于是 `resolved` 的动作是 `drop`：
   「收到恢复通知但没有对应的活动告警」。**告警发得出去，恢复通知永远发不出去。**
3. 因为恢复通知要和**之前那条告警**配对，所以它对「指纹必须稳定」的要求更高。
   告警通知写错了马上能发现（用户收到重复/漏掉的告警）；
   恢复通知写错了**没有症状**——系统里只有一堆永远不结束的故障，没人知道是漏了通知。

</details>

### 练习 7 — 端到端：造一个真故障，再看它恢复（20 分钟，需要 Docker）

```bash
# 终端 A：起接收端
python3 06-webhook-receiver.py --port 19090 --log /tmp/day182/live/hook.jsonl

# 终端 B：起容器 + 跑平台
docker run -d --name d182-web -p 18082:80 nginx:alpine
python3 05-platform-demo.py --serve --live --count 10 --interval 2 \
  --probe http://127.0.0.1:18082/ \
  --webhook http://127.0.0.1:19090/hook --file /tmp/day182/live/platform.jsonl &
sleep 6 ; docker stop d182-web
sleep 7 ; docker start d182-web
wait
```

（注：上面为了可读性用了行尾反斜杠换行，实际执行时可写成一行。）

- [ ] 终端 A 一共收到几条？分别是什么 `status`？
- [ ] 从 `docker stop` 到收到告警，隔了几个采样点？（本日实测：1~2 个）
- [ ] `/tmp/day182/live/platform.jsonl` 有没有被创建？为什么？
- [ ] 有没有看到 `host_cpu_high` 的告警？为什么？（提示：看那几个 `pending / dropped`）

<details><summary>参考答案</summary>

1. 2 条：一条 `firing`（app_down 越界），一条 `resolved`（app_down 恢复）。
2. `docker stop` 在 14:25:59，第一条 down 采样在 14:26:00（差 1s），
   告警（`consecutive=2`）在 14:26:02 升级 → 约 3 秒。
   **告警延迟 = 采样间隔 + 连续次数窗口**，这个数要写进 SLA。
3. **不存在**。webhook 成功了，file 只是 fallback，不该被写。
   这是「顺序链」而非「广播」的直接证据。
4. 没有。本机 load 8+、CPU 在 87%~100% 之间反复穿越 90，
   但每次都在第 2 次越界之后掉回去 → 一直 pending / dropped。
   **这是「连续 N 次」在真实机器上救了你一次**（如果阈值判定是单次越界就报，这几分钟会响 6 次）。

</details>

### 练习 8 — 把主通道弄挂，看降级（10 分钟）

```bash
python3 03-alert-routing.py --demo --webhook http://127.0.0.1:19999/hook --file /tmp/day182/live/fb.jsonl
tail -3 /tmp/day182/live/fb.jsonl
python3 03-alert-routing.py --dry-run --demo
```

- [ ] critical 告警的链路显示成 `webhook+file+console->file`，怎么读这个记号？
- [ ] warning 告警的链路是 `file->console`，说明什么？
- [ ] `--dry-run` 和真发的输出差在哪里？它到底证明了什么？

<details><summary>参考答案</summary>

1. 左边 `webhook+file+console` 是**候选链**，右边 `file` 是**最终成功的通道**。
   `->` 后面那个才是结果。
2. warning 的路由表里压根没有 webhook——**分级路由**，不是「所有通道都试一遍」。
3. dry-run 只打印「本应发往哪里」，不碰网络不写盘。
   它证明的是**路由决策**正确（选对了链、选对了级别），
   但不证明投递成功——投递要用 `--live` 加真接收端验证（练习 7）。

</details>

---

## 二、改造题（选做，动手改代码）

### 改造 1 — 给规则加一条「趋势预警」

磁盘满了才发现太晚。实现一个「剩余可用天数」规则：
用最近 3 个样本的斜率外推，剩余天数 < 7 天就告警。

- 提示：`02` 的 `ThresholdRule` 是纯函数状态机，可以新写一个 `TrendRule`
       （同样实现 `update(value, now)` 接口），塞进 `RuleSet` 的 `rules` 里
- 验收：写一个 `--self-test` 断言「线性增长序列在预计第 N 天触发」

### 改造 2 — 把去重表搬到 Redis（跨进程去重）

本日 `AlertStore.table` 是进程内存里的 dict，重启就丢。
- 提示：换成一个 `RedisStore`，用 `HSET fp count first last_notify`，并给 key 加 TTL
- 验收：起两个进程同时 `process()` 同一条告警，断言只有一条 `notify`

### 改造 3 — 给路由加指数退避

本日 `attempts=2` 是无脑重试。改成「同一个通道失败后，`next_retry_at = now + 2^n`」。

- 验收：模拟一个连挂 3 轮的通道，断言第 2/3/4 轮的重试时机间隔在变长

---

## 三、检查表（做完打勾）

### 环境与运行

- [ ] `python3 --version` ≥ 3.12（本日脚本只用标准库）
- [ ] `python3 code/01-collect-metrics.py --self-test` 退出码 0（本机实测 14 PASS / 1.34 s）
- [ ] `python3 code/01-collect-metrics.py --backend proc --self-test` 也退出码 0（回退路径可用）
- [ ] `python3 code/02-threshold-engine.py --self-test` 退出码 0（14 PASS）
- [ ] `python3 code/03-alert-routing.py --self-test` 退出码 0（16 PASS）
- [ ] `python3 code/04-alert-dedup-recovery.py --self-test` 退出码 0（16 PASS）
- [ ] `python3 code/05-platform-demo.py --self-test` 退出码 0（19 PASS）
- [ ] `python3 code/06-webhook-receiver.py --self-test` 退出码 0（4 PASS）
- [ ] 六个脚本**不装任何第三方库**也能跑（psutil 只是加速/加字段）

### 概念掌握（能口头解释才算过）

- [ ] 能说出 `pending` / `dropped` / `firing` / `resolved` 四者的区别
- [ ] 能解释为什么「超阈值」不等于「该告警」，并举出三种要解决的问题
- [ ] 能画出迟滞带，并说出 `release` 写反会导致什么
- [ ] 能解释抖动判定为什么必须用**时间窗口**而不是总次数
- [ ] 能说出指纹**必须排除**的三个字段（value / status / ts）以及各自的后果
- [ ] 能说出「重试」和「降级」的区别（同一通道 vs 换通道）
- [ ] 能解释为什么 `delivered_by=None` 必须被上层看见，而不是 `except: pass`
- [ ] 能说出本日的告警延迟由哪几段构成（采样间隔 + 连续次数）

### 实测证据（都要亲眼看到）

- [ ] 看到过 `dropped`（毛刺被过滤）的真实输出
- [ ] 看到过迟滞保持（88/86/84/82/81 全都不恢复）
- [ ] 看到过 flapping 标注出现，以及它**自己消失**
- [ ] 看到过 10 条同指纹告警压成 1 条通知（或 32 个采样 → 13 条通知）
- [ ] 看到过 webhook 真的收到 HTTP POST（`06` 的 stdout 或落盘文件）
- [ ] 看到过 webhook 挂掉 → 降级到 file，且报告里 `投递=file`
- [ ] 看到过**恢复通知**真的发出来了（`status=resolved` 那一条）

### 清理（做完必查，别留垃圾）

- [ ] `docker rm -f d182-web` 已执行
- [ ] `pkill -f "06-webhook-receiver.py --port 19090"` 已执行
- [ ] `rm -rf /tmp/day182` 已执行
- [ ] `ss -ltnp | grep -E ':18081|:18082|:19090'` → 无输出
- [ ] `docker ps -a --format '{{.Names}}' | grep d182` → 无输出
- [ ] 没有误伤别人的容器（本机有 `dk-*` 等其它容器在跑）

### 自我验收（能回答这三个问题就毕业了）

- [ ] 为什么这台 4 核机器 CPU 长时间 90%+，本日的平台**一次报警都没发**？这是对还是错？
- [ ] 如果我把这一天的平台部署到 100 台机器上，第一个会爆的地方在哪？（提示：状态表在内存里）
- [ ] 本日的「抖动判定」和「去重」分别在解决什么问题？它们会不会互相覆盖？
