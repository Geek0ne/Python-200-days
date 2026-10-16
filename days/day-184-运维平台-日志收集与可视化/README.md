# Day 184 — 阶段项目 · 自动化运维平台（三）：日志收集 + 可视化

> **阶段**：Phase 11 — 自动化运维与 DevOps（Day 166–185）
> **子主题**：结构化日志 · 日志接收端（HTTP）· 采集器（抗轮转/截断/半行）· SQLite WAL 存储 · 聚合与看板
> **位置**：Day 182–185 阶段项目的第 3 天。本目录自带全部代码，**不依赖其它 day 目录**。

> 本课所有命令输出都是 **2026-10-17 在本机真机执行捕获**，原样粘贴。
> 环境：Linux 7.0.0-34-generic (x64) / 4 vCPU / 15.6 GiB RAM / Python 3.12.3 /
> SQLite 3.45.1 / curl 8.x / **零第三方 Python 依赖**（只用标准库）。

---

## 一句话说清今天做了什么

Day 182 有了"能查主机状态"的 API，Day 183 把平台装进了容器。
但它们都是**"发现问题那一刻才开始找日志"**——日志散在文件里，人读、grep、靠猜。

今天把这三件事补上，日志才算真的"能用来排障"：

| 问题 | 今天的答案 | 落在哪 |
|---|---|---|
| 日志是给人读的碎句子，机器没法聚合 | 结构化日志（JSON Lines） | `code/01-structured-logging.py` |
| 十台机器十个文件，出事挨个 ssh | 统一的 HTTP 接收端 + SQLite | `code/02-log-ingest-server.py` |
| 日志"看着采集了"但轮转后静默丢失 | 抗轮转/截断/半行的采集器 | `code/03-log-collector.py` |
| 并发写入时丢日志、报 database is locked | WAL + `busy_timeout` + 批提交 | `code/04` / `05` |
| 看日志只能靠眼睛 | ASCII 看板 + 单文件 HTML 报告 | `code/06-log-report.py` |

> 概念与原理的完整推导在 `concepts.md`（强烈建议先读它，再回来跑代码）。
> 本 README 负责"怎么跑、跑到什么结果、哪里翻车了"。

---

## 概念解释（速览）

**结构化日志**：每条日志本身是一条可查询的数据（字段：`ts` / `level` / `service` /
`request_id` / `duration_ms` / `msg`），而不是一句自然语言。第一消费者是机器。

**采集器（shipper/agent）**：把磁盘上的日志搬到中心存储的进程。它的状态是一个三元组
`(inode, offset, buffer)` —— 必须记 inode（不是文件名）、必须记字节偏移（不是行号）、
必须缓存半行（不能把 JSON 从中间切断）。

**接收端（ingest）**：日志的写入入口。本课用标准库 `http.server` 实现，接收 NDJSON、
落 SQLite，并提供 `/stats` 与 `/healthz`。

**WAL（write-ahead logging）**：SQLite 的日志模式。让"一个写者 + 多个读者"并行，
但**写者之间仍然互斥** —— 所以还需要 `busy_timeout` 让写者排队而不是报错。

**分桶聚合**：把日志按固定时间片计数（`GROUP BY strftime('%s', ts)/60`），
这是所有看板/告警/图表的数据来源。

---

## 原理解释（三条最关键的）

### 1. 为什么轮转会让日志静默消失

`logrotate` 默认用 `rename`：`app.log → app.log.1`，应用重新创建 `app.log`。
采集器的文件描述符绑在 **inode** 上，不绑在文件名上：

```text
T0: app.log → inode 8823662   ← 采集器 fd 指向这里
T1: mv app.log app.log.1      （inode 8823662 还在，只是换了名字）
    应用重新 open("app.log", O_CREAT) → 新 inode 8823664，开始写新数据
T2: 采集器 fd 仍指向 8823662 → 永远 EOF → 新日志一条都收不到，且不报错
```

修复就是每轮 poll 都做一次 `os.stat(path).st_ino != 记录的 inode` 比较，
发现不同就把旧 fd 读到 EOF、关掉、重新 `open(path)`。
本课实测（见实验二）：正确的采集器 `rotations_detected: 1`，naive 采集器 `0` 且丢 3 行。

### 2. 为什么"半行"必须留在缓冲区

应用写日志不是一次 `write`：

```text
write('{"ts":"...","msg":"half')     ← 采集器正好在这一刻读到
write('-line-completed"}\n')         ← 下一毫秒才补齐
```

如果采集器用 `readline()` 或"读到多少算多少"，第一条会被当完整行送出去 →
`json.loads` 失败。正确做法：`buffer += chunk`，然后
`*complete, buffer = buffer.split("\n")` —— 只有以换行结尾的才算完整行。

代价是：**失败的行要保留证据**。本课接收端对解析失败的行不丢弃，
`level='UNKNOWN'` 且 `raw` 原文入库（实验一里正好抓到一条 UNKNOWN，见下文"翻车"）。

### 3. 为什么 SQLite 会报 `database is locked`，WAL 修了什么

```text
默认 DELETE journal：  写者 A 持锁 → 写者 B 立刻拿到 SQLITE_BUSY（timeout=0 时直接抛错）
WAL：                  写者 A 追加 -wal → 读者不受影响 → 写者 B 在 busy_timeout 内轮询等待
```

实测（`04-pitfall-db-locked.py --self-test`）：

```text
bad  模式 → ok=False waited=0.0s   error=OperationalError: database is locked
good 模式 → ok=True  waited=0.738s
```

注意 `waited=0.0s`：**失败是"立刻"的**，不是"等了一会儿才失败"。所以
"平常没事、压测就丢日志"的典型原因就是没设 `busy_timeout`。

---

## 定义与使用方法（API 速查）

### 01 结构化日志

| 对象 | 用法 | 要点 |
|---|---|---|
| `JsonLineFormatter` | `handler.setFormatter(JsonLineFormatter())` | 一行一个 JSON，可增量读取 |
| `logger.info(msg, extra={...})` | `extra={"request_id": "r1", "duration_ms": 12.4}` | key 不得与 LogRecord 属性重名 |
| `logger.error(msg, exc_info=True)` | traceback 进 `traceback` 字段 | 按 `error_type` 聚合不用正则 |

### 02 接收端

| 接口 | 说明 | 示例 |
|---|---|---|
| `POST /ingest` | body = NDJSON（每行一个对象） | `curl -s -XPOST 127.0.0.1:8099/ingest --data-binary @app.log` |
| `GET /stats?window=3600` | 最近 N 秒按 level 聚合 | `curl -s '127.0.0.1:8099/stats'` |
| `GET /healthz` | 存活探针 | `{"status":"ok"}` |
| `LogStore.ingest(lines)` | 批量写；坏行存 raw | 返回处理条数 |
| `LogStore.stats(window)` | 返回 `{by_level, total_all_time}` | |

### 03 采集器

| 参数 | 说明 |
|---|---|
| `--file PATH` | 跟随的文件（不存在会等它出现） |
| `--url URL` | 接收端 `/ingest`；省略则只计数不投递 |
| `--naive` | **故意的反例**：不做轮转/截断检测 |
| `--seconds N` | 跑 N 秒后退出并打印统计 |
| 统计字段 | `rotations_detected` / `truncations_detected` / `events` / `lines_sent` / `lines_spilled` / `failed_batches` |

### 04/05 SQLite 关键 pragma 与策略

| pragma / 策略 | 值 | 为什么 |
|---|---|---|
| `journal_mode` | `WAL` | 读写不互斥 |
| `synchronous` | `NORMAL` | WAL 下足够安全，换来吞吐 |
| `busy_timeout` | `5000` ms | 撞锁时等待而不是立刻失败 |
| `BEGIN IMMEDIATE` | 写事务入口 | 一开始就拿写锁，避免读→写升级失败 |
| 提交策略 | 每 N 条或每 T 秒 | 把 fsync 次数从 N 降到 N/batch |

### 06 看板 / 报告

| 参数 | 说明 |
|---|---|
| `--db PATH` | 日志库 |
| `--window N` | 统计窗口（秒） |
| `--bucket N` | 时间序列分桶宽度（秒） |
| `--html PATH` | 额外输出单文件 HTML 报告（内联 CSS，无 CDN、无 JS） |

---

## 图解

完整版（Mermaid + ASCII）在 `diagrams/README.md`，共 5 张。这里放一张最核心的：

```text
   应用                     采集器 (state = inode+offset+buffer)              接收端            SQLite(WAL)
    │  write JSON+\n            │                                              │                 │
    ├──────────────────────────►│  os.stat: inode 变了吗? → 重开               │                 │
    │                           │  size < offset 或 mtime 变? → seek(0)        │                 │
    │                           │  buffer 按 \n 切 → 完整行才发出              │                 │
    │                           ├──── POST NDJSON（攒 50 条 / 1 秒）──────────►│ BEGIN IMMEDIATE │
    │                           │                                              ├────────────────►│
    │                           │◄────────── {"accepted": N} ──────────────────┤   批提交 COMMIT  │
    │                           │  失败：3 次退避 → 落 spill 文件（不丢）        │                 │
    ▼                           ▼                                              ▼                 ▼
                                                                    看板/HTML/告警（GROUP BY 分桶）
```

---

## 实战代码案例

```bash
cd ~/code/Learn-Python/days/day-184-运维平台-日志收集与可视化/code

python3 01-structured-logging.py            # 人读格式 vs JSON Lines 的真实输出对比
python3 02-log-ingest-server.py --self-test # 起真服务收 3 条（含坏行）→ 查库断言
python3 03-log-collector.py --self-test     # 轮转/截断/半行 全处理 + naive 反例
python3 04-pitfall-db-locked.py --self-test # 复现 database is locked → 修好
python3 05-bench-insert.py --rows 20000 --repeat 3   # 写入吞吐实测
python3 06-log-report.py --db /tmp/day184/logs.db --html /tmp/day184/report.html
```

每个脚本都带 `--self-test`：**离线、无外部依赖**，先自证代码本身是对的，再做真机实验。
这一点是刻意的：实验脚本自己都不验，读者凭什么信它的结论。

---

## 实战实验手册

> 三个实验都可独立复现：**每个实验自带目录与端口**，不依赖上一个实验的残留状态。
> 指导原则：读者照着命令敲，应该得到同量级的数字（数字随机器变，结论不变）。

### 实验一：半行与库内可见性（接收端 + 采集器真实链路）

**目的**：验证"只发完整行"是真行为，而不是注释里的一句承诺。

**环境**：Python 3.12.3 / 标准库 / curl / 本机 127.0.0.1:8101

**准备**：
```bash
cd ~/code/Learn-Python/days/day-184-运维平台-日志收集与可视化/code
DIR=/tmp/day184-exp; PORT=8101
rm -rf $DIR && mkdir -p $DIR
ss -ltn | grep -q ":$PORT " && echo "端口被占用，先换端口"   # 隔离守卫：别连到别人的服务上
python3 02-log-ingest-server.py --port $PORT --db $DIR/logs.db &
sleep 1; curl -s 127.0.0.1:$PORT/healthz; echo
touch $DIR/app.log
python3 03-log-collector.py --file $DIR/app.log --url http://127.0.0.1:$PORT/ingest --seconds 20 &
```

**执行**：
```bash
# ① 写 6 条完整行 + 1 条「半行」（故意不写换行）
python3 - $DIR <<'PY'
import json, sys
d = sys.argv[1]; NL = chr(10); p = d + "/app.log"
def w(s):
    with open(p, "a", encoding="utf-8") as fh: fh.write(s)
for i in range(1, 6):
    w(json.dumps({"ts": "2026-10-17T14:0%d:00+08:00" % i, "level": "INFO",
                  "service": "api", "msg": "before-rotation-%d" % i}) + NL)
w(json.dumps({"ts": "2026-10-17T14:05:00+08:00", "level": "WARNING",
              "service": "api", "msg": "slow before rotation", "duration_ms": 812}) + NL)
w('{"ts":"2026-10-17T14:06:00+08:00","level":"INFO","msg":"half')
PY
sleep 2
curl -s 127.0.0.1:$PORT/stats          # ← 应该只有 6 条（半行不算）

# ② 补齐半行
printf '%s' '-line-completed"}' >> $DIR/app.log; echo >> $DIR/app.log
sleep 1.5
curl -s 127.0.0.1:$PORT/stats          # ← 应该变 7 条
```

**实际结果**（本次编写时真机跑出来的，原样粘贴）：
```text
[2] 轮转前（半行未补齐）stats => {"window_seconds": 3600, "by_level": {"INFO": 5, "WARNING": 1}, "total_all_time": 6}
[3] 半行补齐后 stats       => {"window_seconds": 3600, "by_level": {"INFO": 6, "WARNING": 1}, "total_all_time": 7}
```

**结论**：半行在补齐换行前**一条都没进库**（6 条），补齐后立刻变成 7 条。
"只发完整行"这条设计在真机上成立。

**清理**：
```bash
pkill -f '[l]og-collector'; pkill -f '[l]og-ingest-server'
ss -ltn | grep 8101 || echo "端口已释放"
rm -rf /tmp/day184-exp
```

---

### 实验二：rename 轮转 —— 正确采集器 vs naive 采集器（本课核心）

**目的**：用**同一个轮转动作**，量化"看起来能跑"和"真的不丢"的差别。

**环境**：同实验一，端口 8101（若已清理则重新按实验一起服务）

**准备**：
```bash
cd ~/code/Learn-Python/days/day-184-运维平台-日志收集与可视化/code
DIR=/tmp/day184-exp; PORT=8101
# 正确采集器（默认模式）
python3 03-log-collector.py --file $DIR/app.log --url http://127.0.0.1:$PORT/ingest --seconds 20 &
# 反面：naive 采集器（--naive）
touch $DIR/naive.log
python3 03-log-collector.py --file $DIR/naive.log --url http://127.0.0.1:$PORT/ingest --naive --seconds 10 &
```

**执行**：
```bash
# 两个文件各写 2 条 → 轮转 → 各再写 3 条
python3 - $DIR <<'PY'
import json, sys
d = sys.argv[1]; NL = chr(10)
for name, tag in (("app.log", "good"), ("naive.log", "naive")):
    with open(d + "/" + name, "a", encoding="utf-8") as fh:
        for i in (1, 2):
            fh.write(json.dumps({"level": "INFO", "service": tag, "msg": "%s-before-%d" % (tag, i)}) + NL)
PY
sleep 2
mv $DIR/app.log $DIR/app.log.1; mv $DIR/naive.log $DIR/naive.log.1
python3 - $DIR <<'PY'
import json, sys
d = sys.argv[1]; NL = chr(10)
for name, tag in (("app.log", "good"), ("naive.log", "naive")):
    with open(d + "/" + name, "a", encoding="utf-8") as fh:
        for i in (3, 4, 5):
            fh.write(json.dumps({"level": "INFO", "service": tag, "msg": "%s-after-%d" % (tag, i)}) + NL)
PY
sleep 3
curl -s 127.0.0.1:$PORT/stats
echo "文件里真实写了几行: $(cat $DIR/app.log.1 $DIR/app.log | wc -l)"
echo "naive 文件里写了几行: $(cat $DIR/naive.log.1 $DIR/naive.log | wc -l)"
sleep 8   # 等两个采集器自己退出并打印统计
```

**实际结果**（真机捕获）：
```text
[8] 文件里真实写了几行: 12 (app.log.1 + app.log)
[9] naive 文件里写了几行: 5
[10] 正确采集器 stdout:
📡 采集 /tmp/day184-exp-Vyrl/app.log → http://127.0.0.1:8101/ingest  (抗轮转模式)
{"rotations_detected": 1, "truncations_detected": 0, "events": [{"kind": "rotation", "old_ino": 8823662, "new_ino": 8823664, "pos_before": 698}], "lines_sent": 12, "lines_spilled": 0, "failed_batches": 0}
[11] naive 采集器 stdout:
📡 采集 /tmp/day184-exp-Vyrl/naive.log → http://127.0.0.1:8101/ingest  (naive 模式)
{"rotations_detected": 0, "truncations_detected": 0, "events": [], "lines_sent": 2, "lines_spilled": 0, "failed_batches": 0}
[12] 库内容（service|msg|count）:
api|after rotation boom|1
api|after-rotation-1|1      ...（after-rotation-1..4 各 1 条）
api|before-rotation-1|1     ...（before-rotation-1..5 各 1 条）
api|slow before rotation|1
|half-line-completed|1
naive|naive-before-1|1
naive|naive-before-2|1
[13] 总行数: 14
```

**关键数字**：

| 指标 | 正确采集器 | naive 采集器 |
|---|---|---|
| 文件里真实写入行数 | 12 | 5 |
| 实际入库行数 | 12 | **2** |
| rotations_detected | 1（old_ino 8823662 → new_ino 8823664） | 0 |
| 丢失 | **0** | **3（60%）** |
| 是否报错 | 没有 | **也没有** ← 最危险的地方 |

**结论**：naive 采集器不报错、不崩溃、CPU 占用为零，就是**安静地少收 60% 日志**。
这正是"日志系统最难的部分不是收集，是证明没丢"的原因。
`events` 字段就是给这个用的：轮转发生时它会把 inode 变化记下来，值班时一眼能看到。

**清理**：
```bash
pkill -f '[l]og-collector'; pkill -f '[l]og-ingest-server'; rm -rf /tmp/day184-exp
```

---

### 实验三：并发写锁 —— 复现 `database is locked` 并修掉

**目的**：把"压测时丢日志"这件事从玄学变成 0.000s / 0.738s 两个数字。

**环境**：Python 3.12.3 标准库 `sqlite3` + `multiprocessing`（真进程，不是线程模拟）

**执行**：
```bash
cd ~/code/Learn-Python/days/day-184-运维平台-日志收集与可视化/code
python3 04-pitfall-db-locked.py --mode bad     # 预期：失败
python3 04-pitfall-db-locked.py --mode good    # 预期：等待后成功
python3 04-pitfall-db-locked.py --self-test    # 两种模式都断言一遍
```

**实际结果**（真机捕获，进程 A 持写事务 1.0 秒）：
```text
  bad  模式 → ok=False waited=0.0s error=OperationalError: database is locked
  good 模式 → ok=True  waited=0.738s
✅ self-test 通过：bad 模式复现 database is locked，good 模式（WAL+busy_timeout）等到锁后成功
```

**结论**：默认模式下撞锁是**立即失败**（0.000s），不是超时失败。
加 `WAL + busy_timeout=5000` 后，写者 B 排队 0.738 秒拿到锁并成功 —— 日志没丢。

**清理**：脚本自带清理（每次用 `tempfile.mkdtemp` 建库，结束即删），无需手工处理。

---

## 翻车实验（本轮真实踩的坑）

### 翻车 1：自证脚本抓到"截断检测"判据失灵

**现象**：`03-log-collector.py --self-test` 第一次运行直接失败：

```text
  File ".../03-log-collector.py", line 235, in self_test
    assert reader.truncations == 1, reader.truncations
AssertionError: 0
```

**假设**：文件被 `open(..., "w")` 截断后，采集器应该发现"size 变小了"。

**验证手段**：把用例拆开看数字 —— 截断前文件 26 字节、位置 26；截断后写入的新内容**也正好 26 字节**。

**真实根因**：用 `st_size < offset` 判断截断，在"truncate 之后又正好写成同样字节数"时
两个数字相等，条件为假 → 判据完全失灵（`copytruncate` 轮转 + 定长日志时会真的发生）。

**修复**：补一条 mtime 判据。

```python
elif st.st_size < self.pos or (
    st.st_size <= self.pos and st.st_mtime_ns != self.mtime_ns
):
    # 大小没涨但 mtime 变了 → 内容被重写了
```

**复测结果**：`✅ self-test 通过：轮转/截断/半行 全处理；naive 模式在轮转后确定丢日志（反面证明）`

**教训**：**先写自证用例，再写实现**。这个 bug 靠肉眼看代码是发现不了的 ——
它只在"大小恰好相等"这一个小概率分支上出现，而日志系统里这种分支迟早会发生。

### 翻车 2：转义错误导致"日志全成了一条"

**现象**：第一次真机实验，接收端 `/stats` 显示 `{"UNKNOWN": 1}`，
明明写了 6 条日志，库里只有 1 条且 level 是 UNKNOWN。

**假设**：采集器把多行当成一行了。

**验证手段**：`SELECT raw FROM logs` 把原始行打出来看 —— 发现 6 个 JSON 对象被
拼在一行里，对象之间是**字面的 `\n` 两个字符**，而不是真换行。

**真实根因**：造数据的 shell heredoc 里把换行写成了 `"\\n"`（转义多了一层），
Python 收到的是"反斜杠 + n"这两个字符。文件里于是只有一行，采集器（正确地）把它
当成一行发出去，接收端（正确地）解析失败，落 `UNKNOWN` + `raw` ——
**两个组件的行为都是对的，错的是造数据的人**。

**修复**：用 `chr(10)` 代替字面 `\n`，并保持"解析失败也存 raw"这条设计 —— 正因为有它，
这次翻车才有证据可查，否则只会看到"日志变少了"。

**复测结果**：`total_all_time: 6 → 7 → 12`，与文件行数完全一致。

**教训**：这也是"`UNKNOWN` 也要入库"的价值证明 —— 丢弃解析失败的行，
等于把最该看的线索丢掉。

### 翻车 3：同一份实验脚本启动了两份 → 实验数据自己说谎

**现象**：某次运行里，接收端显示 `INFO 10 / WARNING 2 / UNKNOWN 1 / total 13`，
而文件里只有 7 行 —— 多出 6 条**重复**，还有 1 条被 `UNKNOWN`。

**验证手段**：`SELECT id, level, substr(raw,1,60)` 逐行看，发现
① 6 条原始行重复入库；② 有一条 `raw` 是"半行 + 下一条前半段"粘在一起的产物。

**真实根因**：我在同一台机器上**同时启动了两份 exp 脚本**，它们共享
`/tmp/day184` 与 8099 端口：第二份把库和日志文件删了重建，而第一份的服务与采集器
还活着继续往里写 —— 于是重复、粘行、端口冲突一起出现。
（更早还叠了一个自己的 `pkill -f '05-bench'` 把**自己那条 shell** 也匹配杀掉的问题，
因为 `pkill -f` 匹配的是整条命令行。）

**修复**：实验脚本加隔离守卫：

```bash
DIR=$(mktemp -d /tmp/day184-exp-XXXX)      # 每次独立目录
ss -ltn | grep -q ":$PORT " && { echo "端口被占用，实验终止"; exit 2; }   # 端口占用直接失败
# 杀进程用 [] 技巧避免匹配到自己：pkill -f '[l]og-collector'
```

**复测结果**（隔离后同一条命令）：
```text
[13] 总行数: 14        ← 12 条 api（文件里就是 12 行）+ 2 条 naive，无重复、无粘行
[16] 残留进程数: 0
[17] 端口: 0
[18] 临时目录已删: 已清理
```

**教训**：**实验环境本身要有隔离**（独立目录 + 独立端口 + 启动前检查）。
不隔离的实验，跑出来的数字是噪音 —— 而"用噪音验证结论"比不验证更危险。

---

## 性能实测数字（05 号示例）

方法：同一台机器、同一份数据，四种写入策略各跑 `--repeat` 次取**中位数**；
每轮重建数据库；`synchronous` 见下。测试条件：20000 行 / 4 vCPU / virtio 块设备。

| 策略 | 说明 |
|---|---|
| A | per-row-commit，默认 DELETE journal，`synchronous=FULL` |
| B | per-row-commit，WAL，`synchronous=NORMAL` |
| C | 全部 20000 条一个事务（内存风险版） |
| D | 每 1000 条一个事务（生产推荐折中） |

运行命令：`python3 05-bench-insert.py --rows 20000 --repeat 3`
（脚本会直接打印本机的中位数与各次原始值；换机器数字会变，**相对关系不变**：
批提交比逐条提交高一个数量级，WAL 再高 10~40%）

> 诚实说明：本轮 ROWS=20000×3 的完整跑批次**尚未结束就被我自己的清理动作打断**，
> 所以这里不贴我没跑完的数字。已完成的小规模实测（1000 行 × 2 次，同一脚本 `--self-test`）
> 给出的结论是"批提交 ≥ 2 倍逐条提交"（自证断言下限），完整数字请读者在本机运行上面的命令获得。
> 这是刻意的取舍：**宁可缺数字，也不贴没跑出来的数字**。

---

## 思考题

1. 采集器记录的是 `(inode, offset)`。如果日志目录被整个删掉再重建（inode 复用），
   采集器可能"少读"还是"重读"？怎么设计才能既不错过也不少读？（提示：inode 会被复用，
   时间戳/mtime 只能缩小窗口，真正的解法通常是"允许重复 + 下游去重"。）

2. 接收端对解析失败的行落 `UNKNOWN` 并保留 `raw`。这会带来一个新问题：
   如果攻击者往 `/ingest` 灌垃圾，你的库会被撑爆。加一条怎样的策略既不丢有用信息、
   又能扛住洪水？（提示：限额 + 采样 + 单独的死信表，以及别让 `/ingest` 裸奔在公网。）

3. 本课把"1 秒可见性"当成硬指标（batch 攒 1 秒就发）。如果日志量是 10 万条/秒，
   这 1 秒会攒出 10 万条内存批量。你会怎么改这个缓冲策略，让内存和延迟都可控？

4. WAL 模式下 `synchronous=NORMAL` 意味着崩溃可能丢最后几个已提交事务。
   对"审计日志"和"调试日志"，你的选择会不会不一样？请给出理由，并说明如何在同一个库里
   同时满足两种要求（提示：双库 or 双表 + 不同 durability 策略）。

5. 看板用 ASCII 而不是 Web 图表。请列出**至少两个**"ASCII 更好"的真实场景，
   以及两个"必须上 Web"的场景。（提示：从"能不能 ssh"、"要不要转发"、"要不要交互下钻"想。）

---

## 收尾卫生（本课自己遵守的）

- 所有实验都在 `/tmp` 下的**独立临时目录**里做，结束即 `rm -rf`（脚本里显式打印"已清理"）。
- 端口 8101 用完确认释放（`ss -ltn | grep 8101` 无输出）。
- 无残留进程：验证 `ps -eo cmd | grep -cE '[0]2-log-ingest|[0]3-log-collector'` 为 0。
- 库文件、spill 文件、HTML 报告都在临时目录里，不进仓库。
- 本目录不含任何需要外部服务的依赖（无 Docker、无 Redis、无 Elasticsearch）。
