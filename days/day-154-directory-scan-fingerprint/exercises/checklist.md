# Day 154 — 目录扫描与指纹识别 · 完成清单与练习

> 阶段：Phase 7 — 进阶与性能优化
> 目标：能独立写出一个**误报率可控、限速合规、带指纹识别**的 Web 资产发现工具。

---

## ✅ 今日完成清单

### 理解层面（能自己讲出来才算过）

- [ ] 能解释**为什么** Web 上会出现"没有任何页面链接指向"的资源（unlinked）
- [ ] 能说出 `200 / 301 / 302 / 401 / 403 / 404 / 429 / 500` 在扫描里各代表什么
- [ ] 能解释**为什么 `403` 和 `401` 是"命中"而不是"失败"**
- [ ] 能画出一次 HTTP 请求经过 CDN → nginx → 应用服务器 → 框架的完整链路
- [ ] 能解释**软 404（soft 404）**是怎么产生的（`try_files` / catch-all 路由）
- [ ] 能说出软 404 过滤的三种手段及其优先级（哈希 > 长度 > 关键词）
- [ ] 能解释 favicon 哈希为什么跨域名有效，以及 mmh3 为什么被选为事实标准
- [ ] 能说出至少 5 种指纹证据，并按可靠性排序
- [ ] 能解释**为什么扫描必须限速**（法律 / 可用性 / WAF 三个角度）

### 操作层面（动手做过才算过）

- [ ] 跑通 `code/01-dir-brute-basics.py --url http://127.0.0.1/`
- [ ] 对比单线程 30 条 vs 线程池全量的耗时差，记录倍率：________
- [ ] 跑通 `code/02-fingerprint-pitfalls.py --self-test`（全部断言通过）
- [ ] 跑通 `code/03-asset-discovery.py --url http://127.0.0.1:8080`
- [ ] 打开生成的 `out/asset-discovery-*.md`，读懂每一栏
- [ ] 用 `--workers 5 --delay 0.2` 再跑一次，感受限速参数的影响

### 产出物

- [ ] 一份 JSON 报告
- [ ] 一份 Markdown 报告
- [ ] 一张自己画的"扫描决策流程图"（可手绘，拍照也行）

---

## 📝 基础练习（必做）

<details>
<summary>点击展开答案要点</summary>

### Q1 状态码语义练习

不写代码，回答：你的扫描器请求了以下 6 个路径，分别返回下列状态码。
哪些应该记录为"存在"？分别说明理由。

| 路径 | 状态码 | Location | 是否记录 | 理由 |
|---|---|---|---|---|
| `/admin` | 302 | `/login` | ? | |
| `/backup.zip` | 200 | — | ? | |
| `/zzz-random` | 200 | — | ? | |
| `/.git/HEAD` | 403 | — | ? | |
| `/phpinfo.php` | 404 | — | ? | |
| `/api/v2` | 429 | — | ? | |

**答案要点：**

- `/admin → 302 /login`：**记录**。说明受保护资源存在，只是需要登录。
- `/backup.zip → 200`：**记录**（但需与基线比对，确认不是软 404）。
- `/zzz-random → 200`：**不记录**。这是随机路径，属于基线；如果它和字典路径
  返回内容一致 → 说明站点有通配路由，必须切换判定策略。
- `/.git/HEAD → 403`：**记录，且是高危**。Git 仓库被部署到 Web 根目录，
  即使当前被 nginx 规则挡了，也说明源码可能泄露。
- `/phpinfo.php → 404`：**不记录**（确认不存在）。
- `/api/v2 → 429`：**不记录为命中，但要立即降速**。429 是限流信号，
  与资源是否存在无关；继续扫会被封 IP。

### Q2 写一个最小可用扫描器（20 行内）

```python
import requests, sys
from concurrent.futures import ThreadPoolExecutor

BASE = "http://127.0.0.1/"
assert BASE.startswith("http://127.0.0.1") or BASE.startswith("http://localhost")

def probe(w):
    try:
        r = requests.get(BASE + w, timeout=3, allow_redirects=False)
        return w, r.status_code, len(r.content)
    except requests.RequestException:
        return w, None, None

words = ["admin", "login", "robots.txt", ".git/HEAD", "backup.zip", "api/v1"]
with ThreadPoolExecutor(20) as ex:
    for w, st, ln in ex.map(probe, words):
        if st and st != 404:
            print(f"{st} {ln:>6} /{w}")
```

**要点：** `allow_redirects=False` 必须有；`timeout` 必须有；
`except RequestException` 必须兜底；目标必须是本机或已授权。

### Q3 基线比对函数

实现 `is_soft404(status, body_hash, body_len, baseline)`。

```python
def is_soft404(status, body_hash, body_len, baseline, tol=0.05):
    # baseline: [(status, hash, norm_len), ...]
    for b_status, b_hash, b_len in baseline:
        if status != b_status:
            continue
        if body_hash == b_hash:
            return True
        if b_len and abs(body_len - b_len) / max(b_len, 1) <= tol:
            return True
    return False
```

**要点：** 先比哈希（最可靠），再比归一化长度（容差可配），状态码不同直接不算。

### Q4 为示例 03 增加"后缀变体"

给字典里每个词自动追加 `.bak` / `.old` / `~` / `.swp` / `.zip`：

```python
SUFFIXES = [".bak", ".old", "~", ".swp", ".zip", ".tar.gz", ".1"]

def expand(words):
    out = []
    for w in words:
        out.append(w)
        for s in SUFFIXES:
            out.append(w + s)
    return out
```

**注意：** 字典会膨胀 8 倍，必须同步提高延迟或降低并发，
否则你会从"扫描"变成"DDoS 练习"。

### Q5 安全头体检为什么比目录列表更有价值？

**答案要点：** 目录列表告诉你"哪里有东西"，安全头体检告诉你
"**哪里该有的防护没有**"。前者是信息，后者是可直接排期的加固项：
缺 HSTS → 可被 SSL 剥离；缺 CSP → XSS 无第二道防线；
缺 `X-Content-Type-Options` → MIME 嗅探可执行上传文件。
一份"缺失清单"能直接变成工单，而"发现 `/admin`"需要进一步验证才能定性。

</details>

---

## 🚀 进阶挑战（选做，做完写进当天笔记）

<details>
<summary>点击展开</summary>

### C1 让扫描器支持"重试 + 断点续扫"

需求：

1. 每扫完 100 条，把已扫路径与结果写入 `progress.jsonl`；
2. 进程被 Ctrl-C 打断后，重新运行能从断点继续（跳过已扫路径）；
3. 遇到 `429` 时把当前并发数减半（而不是只 sleep）。

**提示：** 并发数减半可以用"动态 `Semaphore`"实现——
每次限流时 `acquire()` 一个许可不放，等效于缩小并发窗口。

### C2 实现一个"通配路由检测 + 自适应判定"

需求：当检测到通配路由时，不再依赖状态码，改为：

1. 取基线页面的**内容长度分布**（多次采样求均值与标准差）；
2. 判定命中条件改为 `|len - μ| > 3σ`；
3. 输出时明确标注"本结果在通配路由下产生，置信度低"。

**思考：** 如果目标对每个路径返回**长度随机**的页面，这个方法还成立吗？
你有什么替代思路？

### C3 把工具改成"被动优先"模式

需求：默认只做被动指纹（响应头/Cookie/HTML），
只有加 `--active` 才发主动探针（`/actuator/env`、`/.git/HEAD` 等）。

**为什么这样设计更好？** 主动探针会产生明显异常流量，容易触发告警；
被动指纹零风险。真实项目里应该"默认安静，按需喧闹"。

### C4 用 `httpx.AsyncClient` 重写扫描核心

对比 `asyncio` 版本与线程池版本的：

- 1 万路径总耗时；
- 内存占用（`tracemalloc` 或 `psutil`）；
- 代码复杂度。

**提示：** 用 `asyncio.Semaphore(n)` 控制并发，`asyncio.gather` 收集结果，
`httpx.AsyncClient(http2=True, limits=httpx.Limits(max_connections=100))`。
注意：**并发上限依然要压住**，协程只是更省资源，不代表可以更快地打别人。

### C5 加一个"自我审计"子命令

`--audit-self` 参数：只检查本机是否暴露了危险文件：

```bash
python3 03-asset-discovery.py --url http://127.0.0.1:8080 --audit-self
# 只检查: .git/HEAD, .env, wp-config.php.bak, phpinfo.php,
#         server-status, actuator/env, .DS_Store
```

**这才是本日最推荐的用法**：拿它扫自己的站点，把发现的问题修掉。

</details>

---

## 📌 今日自检的三个问题

1. 如果目标站点对你**每一个**路径都返回 `200`，你还能不能扫？怎么扫？
2. `401` / `403` 为什么比 `200` 更值得记录？
3. 你的扫描器里，如果只能保留一条限速措施，你保留哪条？为什么？

---

## 🚫 今日红线

- ❌ 不扫描任何**不属于你**、且**没有书面授权**的目标；
- ❌ 不把 `--workers` 开到 100+ 去打生产站点（`400+` 请求/秒 = DDoS 特征）；
- ❌ 不在报告的 JSON/Markdown 里保存任何从响应中抓到的**凭据/令牌**；
- ❌ 不用本日工具去"验证别人的 `.env` 里有什么"；
- ✅ 拿不准时，**只扫 127.0.0.1**。
