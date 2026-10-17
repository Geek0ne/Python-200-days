# Day 188 — 综合项目 I（三）：Web 漏洞检测（SQLi / XSS）

> **阶段**：Phase 12 — 综合实战
> **项目**：企业资产监控系统 · 第 3/5 天
> **子主题**：SQLi 报错型/布尔型 · 反射型 XSS · baseline→payload→oracle · 误报治理
> **代码**：1 个本地靶场 + 4 个扫描/报告脚本，全部带 `--self-test`
> **实测环境**：Linux 7.0.0-34-generic / Python 3.12.3 / 2026-10-18

---

## 今天在项目里的位置

```text
Day 186  资产发现        → 域名 / IP
Day 187  端口 + 指纹     → 127.0.0.1:18080 是 HTTP 服务
Day 188  Web 漏洞检测    → 这个 HTTP 服务有 SQLi / XSS
Day 189  入库 + 可视化   → 漏洞如何长期跟踪
Day 190  调度 + 告警     → 如何自动跑、自动通知
```

今天不追求"扫描器多强"，而是把**判定逻辑**讲透：
为什么同一个响应，朴素检测器会误报，而上下文检测器不会。

---

## 概念速览

完整定义、四类 SQLi、三类 XSS、误报来源见 **`concepts.md`**。

| 概念 | 一句话 | 为什么重要 |
|---|---|---|
| SQLi | 用户输入被当成 SQL 代码 | 可读库、改数据 |
| 参数化查询 | SQL 模板与数据分离 | 根本修复方式 |
| 报错型注入 | 数据库错误回显 | 最明确的检测信号 |
| 布尔型注入 | 真假条件响应不同 | 无错误回显时仍可检测 |
| 反射型 XSS | payload 在本次响应中原样回显 | 可执行脚本 |
| 转义 | 把 `<` 变成 `&lt;` | 文本仍在，但不可执行 |
| oracle | 判定器：把响应映射成结论 | 扫描器的核心 |

---

## 原理解释

### 1. baseline 不是可选项

扫描器先请求 `/product?id=1`，确认：
- 状态码 200；
- 页面包含已知产品名 `Mechanical Keyboard`。

如果 baseline 失败，后续 payload 的"500"就无法区分是注入导致，还是目标本来就坏了。
**没有 baseline 的扫描器只会制造噪音。**

### 2. 报错型与布尔型的分工

- 报错型：`1'` → 500 + `SQL error: unrecognized token`。信号强，但依赖错误回显。
- 布尔型：`1 AND 1=1` 有产品，`1 AND 1=2` 无产品。信号弱，但不依赖错误页。

本日两者都命中，因此置信度都是 high。

### 3. 为什么 `alert` 关键字会误报

`/safe-search` 输出 `&lt;svg/onload=alert('LPX...')&gt;`：
- 文本里确实有 `alert`；
- 但 `<` 已转义，浏览器不会执行。

朴素判定 `"alert" in body` → 假阳性。
正确判定要求：**完整 payload 原样出现，且不存在转义形式**。

### 4. "6 个 finding" ≠ "6 个漏洞"

本日报告 6 条 finding：
- 4 条 error-based（`1'`、`1"`、`1)`、`1'--`）其实是同一个根因；
- 1 条 boolean-based 是对同一根因的二次确认；
- 1 条 XSS 是独立问题。

真实报告应合并为 **2 个漏洞**（SQLi ×1、XSS ×1），并保留多条证据。
否则管理层会以为"有 6 个洞"，修复优先级被稀释。

---

## API 速查

| 需求 | 写法 | 注意 |
|---|---|---|
| URL 编码 | `urllib.parse.quote(payload)` | `'` → `%27` |
| GET + 读错误页 | `urlopen` / `except HTTPError` | 4xx/5xx 必须读 `e.read()` |
| HTML 转义 | `html.escape(q, quote=True)` | 修复 XSS 的最小改动 |
| 参数化 SQL | `conn.execute(sql, (v,))` | 不要 f-string 拼接 |
| 临时 HTTP 服务 | `ThreadingHTTPServer(("127.0.0.1", 0), H)` | 端口 0 自动分配 |
| 报告序列化 | `json.dumps(..., ensure_ascii=False)` | 中文可读 |
| 时间戳 | `datetime.now().isoformat(timespec="seconds")` | 报告可追溯 |

---

## 代码导览

| 文件 | 作用 |
|---|---|
| `00-vuln-lab.py` | 本地靶场：`/product` SQLi、`/search` XSS、`/safe-search` 对照 |
| `01-sqli-detect.py` | 报错型 + 布尔型检测，7 个 payload |
| `02-xss-detect.py` | 唯一标记 + 原始/转义判定，带对照组 |
| `03-security-scan-report.py` | 组合扫描、严重级别、JSON + Markdown |
| `04-false-positive-drill.py` | naive vs precise 的误报实测 |

所有脚本都只监听/访问 `127.0.0.1`。

---

## 实战实验手册

> 环境：Linux 7.0.0-34-generic / Python 3.12.3 / 2026-10-18。
> 靶场只绑定 `127.0.0.1:18081`，实验结束立即 kill。

### 实验 1：启动靶场并确认漏洞可复现

**目的**：先手工确认"漏洞真的存在"，再让扫描器去判定。

**准备**：无需第三方依赖。

**执行**：

```bash
cd days/day-188-web漏洞检测-sqli-xss/code
setsid python3 00-vuln-lab.py --port 18081 </dev/null >/tmp/day188-lab.log 2>&1 &
echo $! >/tmp/day188-lab.pid
sleep 1
curl -s http://127.0.0.1:18081/health; echo
curl -s 'http://127.0.0.1:18081/product?id=1'; echo
curl -s "http://127.0.0.1:18081/product?id=1'"; echo
curl -s 'http://127.0.0.1:18081/search?q=%3Cb%3Ehi%3C/b%3E'; echo
curl -s 'http://127.0.0.1:18081/safe-search?q=%3Cb%3Ehi%3C/b%3E'; echo
```

**实际结果**（真机 stdout）：

```text
{"ok": true}
<html><title>Product</title><h1>Mechanical Keyboard</h1><p>Price: 89.0</p></html>
SQL error: unrecognized token: "'"
<html><title>Search</title><h1>Search</h1><p>Results for: <b>hi</b></p></html>
<html><title>Search</title><h1>Search</h1><p>Results for: &lt;b&gt;hi&lt;/b&gt;</p></html>
```

**结论**：
- `/product?id=1` 正常返回产品；
- 加一个单引号直接触发 SQLite 报错，且错误被回显 → 报错型注入成立；
- `/search` 原样回显 HTML，`/safe-search` 转义 → 一组完美的实验/对照。

---

### 实验 2：SQLi 检测器自测与真实扫描

**执行**：

```bash
python3 01-sqli-detect.py --self-test
python3 01-sqli-detect.py --base-url http://127.0.0.1:18081
```

**实际结果**（自测节选）：

```text
[lab] "GET /product?id=1" 200 -
[lab] "GET /product?id=1%27" 500 -
[lab] "GET /product?id=1%22" 500 -
[lab] "GET /product?id=1%29" 500 -
[lab] "GET /product?id=1%27--" 500 -
[lab] "GET /product?id=1%20AND%201%3D1" 200 -
[lab] "GET /product?id=1%20AND%201%3D2" 404 -
✅ self-test passed: 报错型 + 布尔型 SQLi 均检出
```

**结论**：
- 7 个 payload（5 个报错型 + 2 个布尔对照）全部按预期返回；
- 4 个单引号/双引号/括号/payload 触发 500；
- `AND 1=1` 返回 200，`AND 1=2` 返回 404 → 布尔条件确实进入 SQL。

---

### 实验 3：XSS 检测器（唯一标记 + 对照组）

**执行**：

```bash
python3 02-xss-detect.py --self-test
python3 02-xss-detect.py --base-url http://127.0.0.1:18081
```

**实际结果**（自测节选）：

```text
[lab] "GET /search?q=%3Csvg/onload%3Dalert%28%27LPXedsovpsn%27%29%3E" 200 -
[lab] "GET /safe-search?q=%3Csvg/onload%3Dalert%28%27LPXedsovpsn%27%29%3E" 200 -
✅ self-test passed: /search 检出反射型 XSS，/safe-search 正确判 safe
```

判定细节：

```text
/search:      raw_reflection=True,  escaped_reflection=False → vulnerable
/safe-search: raw_reflection=False, escaped_reflection=True  → safe
```

**结论**：唯一标记（`LPX...`）避免把页面模板里已有的 `<svg>` 当成回显；
对照组确保检测器不是"见谁都报警"。

---

### 实验 4：组合扫描报告（端到端）

**执行**：

```bash
python3 03-security-scan-report.py --base-url http://127.0.0.1:18081 \
  --json /tmp/day188-report.json --markdown /tmp/day188-report.md
cat /tmp/day188-report.md
```

**实际结果**（真机，节选）：

```text
{
  "target": "http://127.0.0.1:18081",
  "severity": "critical",
  "finding_count": 6,
  "findings": [
    {"category": "SQLi", "severity": "high", "type": "error-based", "payload": "1'", "evidence": "sql error", "status": 500, "confidence": "high"},
    {"category": "SQLi", "severity": "high", "type": "error-based", "payload": "1\"", "evidence": "sql error", "status": 500, "confidence": "high"},
    {"category": "SQLi", "severity": "high", "type": "error-based", "payload": "1)", "evidence": "sql error", "status": 500, "confidence": "high"},
    {"category": "SQLi", "severity": "high", "type": "error-based", "payload": "1'--", "evidence": "sql error", "status": 500, "confidence": "high"},
    {"category": "SQLi", "severity": "high", "type": "boolean-based", "payload": "1 AND 1=1 vs 1 AND 1=2", "evidence": "true 条件返回产品，false 条件返回空", "status": 200, "confidence": "high"},
    {"category": "XSS", "severity": "high", "type": "reflected-xss", "endpoint": "/search", "payload": "<svg/onload=alert('LPXdwahw97n')>", "evidence": "原始 payload 未转义回显（标记 LPXdwahw97n）", "confidence": "high"}
  ]
}
```

Markdown 报告：

```text
# 漏洞扫描报告

- 目标：http://127.0.0.1:18081
- 时间：2026-10-18T06:07:30
- 严重级别：**critical**
- 发现数：6

## Findings

| # | 类别 | 类型 | 证据 | 置信度 |
|---:|---|---|---|---|
| 1 | SQLi | error-based | sql error | high |
| 2 | SQLi | error-based | sql error | high |
| 3 | SQLi | error-based | sql error | high |
| 4 | SQLi | error-based | sql error | high |
| 5 | SQLi | boolean-based | true 条件返回产品，false 条件返回空 | high |
| 6 | XSS | reflected-xss | 原始 payload 未转义回显（标记 LPXdwahw97n） | high |
```

**结论**：
- 端到端链路（靶场 → 两个检测器 → 聚合 → 报告）全部打通；
- 严重级别 critical：SQLi + XSS 同时存在；
- **但"发现数 6"会误导**：其中 5 条是同一个 SQLi 根因的不同证据。报告应增加"去重后的漏洞数 = 2"。

---

### 实验 5：误报演练（本日核心翻车）

**执行**：

```bash
python3 04-false-positive-drill.py
```

**实际结果**：

```text
payload: <svg/onload=alert('LPXfylllr')>
endpoint           naive  precise  has_alert   raw  escaped
/search             True     True       True  True    False
/safe-search        True    False       True  False    True
{
  "naive_flagged": 2,
  "precise_flagged": 1,
  "false_positives_naive": 1,
  "false_positives_precise": 0
}
```

**现象**：朴素检测器对"已修复"的 `/safe-search` 也报警。

**假设**：
1. `/safe-search` 其实没修好？—— 手工看响应，`<` 已变成 `&lt;`。
2. 检测器把模板里的 `alert` 当成了回显？—— 页面只有这一处 `alert`。
3. 判定条件太宽？—— 只检查了关键字。

**验证**：打印 `contains_alert / contains_raw_payload / contains_escaped` 三个布尔值：
`/safe-search` 是 `True / False / True`。

**真实根因**：**转义只改变字符表示，不删除文本**。
`html.escape` 后 `alert` 仍是 `alert`，只是 `<` 变成了 `&lt;`。
"搜关键字"本质上无法区分"可执行"与"仅显示"。

**修复**：判定改为 `payload in body and "&lt;svg" not in body.lower()`。

**复测**：naive 2 命中（1 假阳性）→ precise 1 命中（0 假阳性）。

**结论**：
- 这是扫描器最典型的假阳性来源；
- 所有"关键字命中"型规则都应升级为"上下文判定"；
- 对照组（已知安全的端点）是发现假阳性的最有效手段。

---

### 实验 6：收尾与清理

```bash
kill $(cat /tmp/day188-lab.pid) 2>/dev/null
sleep 0.3
(curl -s --max-time 1 http://127.0.0.1:18081/health && echo ' STILL UP') || echo 'lab stopped'
rm -f /tmp/day188-lab.pid /tmp/day188-lab.log \
      /tmp/day188-report.json /tmp/day188-report.md
```

**实际结果**：

```text
lab stopped
```

已确认：靶场进程退出、18081 无监听、临时报告与日志删除。
**没有对任何公网目标发起请求。**

---

## 本日关键数字

| 指标 | 数值 |
|---|---|
| SQLi payload 数 | 7（5 报错 + 2 布尔） |
| 报错型命中 | 4 |
| 布尔型命中 | 1 |
| XSS 命中 | 1（`/search`） |
| 对照组误报 | 0（precise） |
| naive 假阳性 | 1 |
| 报告 severity | critical |
| 去重后真实漏洞 | 2（SQLi、XSS） |

---

## 思考题

1. 如果目标关闭了错误回显，报错型全部失效，布尔型还能怎么加强？
2. 为什么"6 条 finding"不能直接写成"6 个漏洞"？报告应该怎么组织？
3. 转义（escaping）和过滤（sanitization）分别防的是哪类 XSS？
4. 如何设计一个"已知安全"的对照组来量化扫描器假阳性率？
5. 如果扫描器要接入 CI，哪些指标应设为失败阈值？

