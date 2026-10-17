# Day 188 · 概念与原理：SQLi 与 XSS 自动检测

> 本日的靶场、扫描器、报告全部在本机真实运行。
> 目标不是"学会入侵"，而是**理解检测器如何判定、为什么会误报**。

---

## 1. SQL 注入：从字符串拼接开始

漏洞代码：

```python
sql = "SELECT id, name, price FROM products WHERE id = " + pid
row = conn.execute(sql).fetchone()
```

正常输入 `1` → `WHERE id = 1`。
恶意输入 `1'` → `WHERE id = 1'` → SQLite 报错 `unrecognized token: "'"`。

**根因不是引号，而是"数据被当成了代码"**。参数化查询把 SQL 结构与数据分开传输：

```python
conn.execute("SELECT ... WHERE id = ?", (pid,))
```

### 1.1 四类注入与检测难度

| 类型 | 判定信号 | 检测难度 | 本日是否实现 |
|---|---|---|---|
| 报错型 | 数据库错误回显 | 低 | ✅ |
| 布尔型 | 真/假条件响应不同 | 中 | ✅ |
| UNION 型 | 联合查询改变结果集 | 中 | ❌ |
| 时间盲注 | 响应延迟 | 高（慢、易受网络影响） | ❌ |

**为什么先做报错型**：信号最明确、请求最少、几乎不改变目标状态。
**为什么还要布尔型**：生产环境通常关闭错误回显，报错型会漏报。

### 1.2 布尔型的判定逻辑

```text
payload A: 1 AND 1=1   → 200，包含 "Mechanical Keyboard"
payload B: 1 AND 1=2   → 404，不包含产品
结论：条件表达式进入了 SQL，且结果可观测 → 布尔盲注成立
```

注意：如果 false 条件也返回 200（例如页面有缓存/统一错误页），不能判定漏洞。
必须要求"真条件有结果、假条件无结果"这个**差异**。

---

## 2. XSS：转义不是删除

漏洞代码：

```python
body = f"<p>Results for: {q}</p>"        # 原样拼接
```

输入 `<svg/onload=alert(1)>` 会被浏览器当成标签执行。

修复：

```python
import html
body = f"<p>Results for: {html.escape(q, quote=True)}</p>"
```

输出变成 `&lt;svg/onload=alert(1)&gt;` —— 浏览器显示文本，不执行。

### 2.1 三类 XSS

| 类型 |  payload 存哪 | 触发点 | 检测方式 |
|---|---|---|---|
| 反射型 | URL 参数 | 本次响应 | 请求后看是否原样回显 |
| 存储型 | 数据库 | 之后的页面 | 写入后再次读取（需谨慎） |
| DOM 型 | 前端 JS | 浏览器执行 | 需要浏览器/JS 引擎 |

本日只做反射型：它最容易在无浏览器环境下自动判定。

### 2.2 为什么"搜 alert 关键字"会误报

`/safe-search` 的响应里仍然有 `alert` 这个词，只是 `<` 被转义成 `&lt;`。
朴素检测器看到 `alert` 就报警 → 假阳性。

正确判定必须同时满足：
1. 完整 payload 原样出现（`<svg/onload=...>`）；
2. 不存在对应的转义形式（`&lt;svg`）。

本日实测：naive 命中 2 个（1 真 1 假），precise 命中 1 个（0 假阳性）。

---

## 3. 扫描器的结构：baseline → payload → oracle

```text
baseline 请求（正常输入）
   │  记录：状态码、关键内容、长度
   ▼
逐个 payload 请求
   │
   ▼
oracle（判定器）
   ├─ 报错特征匹配
   ├─ 真/假条件差异
   └─ 原始 payload 回显 + 转义检查
   ▼
findings（类型、payload、证据、置信度）
```

**baseline 的作用**：
- 确认目标可达、页面正常；
- 提供"正常响应"的参照，避免把模板里本来就有的内容当成回显；
- 如果 baseline 失败，后续所有 payload 结论都不可信。

**oracle 的设计原则**：
- 宁可漏报，不可大量误报（误报会消耗信任）；
- 每个 finding 必须带**可复现的 payload 和证据**；
- 置信度分级，low 的结论不直接进工单。

---

## 4. 误报与漏报的来源

| 来源 | 表现 | 对策 |
|---|---|---|
| 统一错误页 | 所有 500 都含 "error" | 要求错误特征 + 状态变化 + 基线对比 |
| WAF 拦截页 | 所有 payload 都返回 403 | 识别 WAF 特征，标记 inconclusive |
| 转义后文本仍在 | 搜关键字命中 | 检查原始 payload 与转义形式 |
| 缓存 | 真假条件返回同一页面 | 加随机参数/no-cache 头 |
| 网络抖动 | 超时被当成 false | 重试 + 记录耗时 |
| 动态内容 | 长度随机变化 | 用稳定标记而非整页比较 |

---

## 5. 合规边界（必须遵守）

- 只测试**自有系统或书面授权**目标；本日靶场只监听 `127.0.0.1`。
- 检测到注入后**停止**，不拖库、不写文件、不执行系统命令。
- 不扫描第三方公网站点；不对生产环境做时间盲注（会拖慢数据库）。
- 报告只记录"存在漏洞 + 复现 payload"，不包含敏感数据。
- 真实项目要走变更/测试窗口，避免影响业务。

---

## 6. API 速查

| 需求 | 写法 | 注意 |
|---|---|---|
| URL 编码 | `urllib.parse.quote(payload)` | 空格→%20，引号→%27 |
| GET 请求 | `urllib.request.urlopen(req, timeout=3)` | 捕获 `HTTPError` 才能读 4xx/5xx body |
| 读错误响应 | `except HTTPError as e: e.read()` | 默认异常不带 body |
| 转义 HTML | `html.escape(s, quote=True)` | 同时转义 `"` 和 `'` |
| 正则提取 | `re.search(r"...", body, re.S)` | 跨行要 `re.S` |
| JSON 报告 | `json.dumps(..., ensure_ascii=False, indent=2)` | 中文可读 |
| SQLite 参数化 | `conn.execute(sql, (value,))` | 不要用 f-string 拼 SQL |
| 临时服务 | `ThreadingHTTPServer(("127.0.0.1", 0), H)` | 端口 0 自动分配 |

---

## 7. 思考题

1. 为什么"报错型 + 布尔型"都实现后，仍然可能漏掉 UNION 注入？
2. 如果目标把所有 500 页面都替换成统一错误页，报错型检测会怎样？如何降低误报？
3. 转义（escaping）和过滤（sanitization）有什么区别？各自适合什么场景？
4. 时间盲注的判定需要控制哪些变量？为什么在网络不稳定时不可靠？
5. 设计一个"漏洞扫描器上线前"的自检清单，至少包含 5 项。
