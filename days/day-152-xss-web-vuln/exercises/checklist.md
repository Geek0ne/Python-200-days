# Day 152 — XSS 与 Web 漏洞 · 练习与完成清单

> 主题：XSS 三种类型 / 输出编码与 CSP / CSRF 防护 / 本地检测实战
> 实战：XSS 反射检测与安全头扫描脚本
> 预计用时：90~150 分钟（不含思考题）

> ⚠️ 全部动手环节**只针对本目录 `code/` 里自带的本地靶场**（127.0.0.1）。
> 对任何外部系统做安全测试前，必须拿到**书面授权**。

---

## ✅ 今日完成清单

### 概念理解（能用自己的话讲清楚）
- [ ] 用一句话说清 XSS 的本质："用户输入变成了**在站点源下执行**的代码"
- [ ] 说出三种 XSS 的**数据源**分别是什么（请求参数 / 数据库 / 浏览器本地）
- [ ] 说清**为什么存储型最危险**（不需要社工、影响所有访客、可持久、可打后台）
- [ ] 说清**为什么 DOM 型服务端修不了**（fragment 不发给服务器）
- [ ] 说出至少 4 个危险信宿（`innerHTML` / `document.write` / `eval` / `insertAdjacentHTML`）
- [ ] 说清 XSS 与 SQL 注入共享的**同一个根因**（数据与代码在同一字符串通道里）
- [ ] 说清 XSS / CSRF / CSP 三者的关系（谁能防谁、谁能绕过谁）

### 原理掌握（能画出流程图）
- [ ] 能默画"浏览器解析 HTML 的状态机"（字节 → 字符 → Token → DOM）
- [ ] 能说出**五种输出上下文**，以及每种对应的编码方式
- [ ] 解释**为什么"输入时过滤"既损坏数据又不安全**（一条数据要进多个出口）
- [ ] 解释**为什么黑名单必然失败**（大小写 / 嵌套 / 上下文 / 编码层次）
- [ ] 解释 CSP 的 `nonce` 机制，以及**为什么它能让注入脚本执行不了**
- [ ] 说出 CSP 的三种"白写"情形（`unsafe-inline` / CDN 白名单 / 固定 nonce）
- [ ] 解释 `HttpOnly` **防读不防用**，并举出它挡不住的两件事
- [ ] 说清富文本净化为什么必须"解析成树 + 白名单"，正则为什么不行
- [ ] 说清 CSRF 三前提，以及 `SameSite` **挡不住同站子域**这个坑

### 动手实践（跑代码 + 改代码）
- [ ] 运行 `code/01-xss-types-basics.py`，对照打印出的**原始响应体**找出
      "危险版"与"安全版"的字节差异（`<x152probe>` vs `&lt;x152probe&gt;`）
- [ ] 在 `01` 里给 `/guestbook` 再加一条正常留言，确认**所有访客**都能看到它
- [ ] 在 `01` 的 `simulate_dom_sinks()` 里换成 `'"><x152probe>` 再看 innerHTML 语义输出
- [ ] 运行 `code/02-xss-defense-pitfalls.py`，确认末尾"自测失败项合计: 0"
- [ ] 在 `02` 里**故意**把 `enc_html_attr` 改成 `html.escape(s, quote=False)`，
      重跑并观察哪些自测项变红 —— 亲手制造一次"回归"
- [ ] 在 `02` 的 `MiniSanitizer` 白名单里加入 `img`，重跑观察 `onerror` 是否还能漏出来
- [ ] 运行 `code/03-xss-scanner.py`，确认 `/search` FAIL、`/attr` WARN、
      `/safe` 与 `/secure` PASS
- [ ] 运行 `python3 code/03-xss-scanner.py --json > /tmp/x152.json`，用 Python 解析并打印 counts
- [ ] 把 `LabHandler./search` 改成 `html.escape(val, quote=True)`，重跑确认 FAIL 减少
- [ ] 运行 `python3 code/03-xss-scanner.py --url https://example.com/`，
      确认它**拒绝执行**并返回退出码 2

### 输出物
- [ ] `days/day-152-xss-web-vuln/` 下 4 类文件齐全（README / code / diagrams / exercises）
- [ ] 3 个 `.py` 全部能 `python3` 直接跑通，**无第三方依赖**
- [ ] 能对着 `diagrams/README.md` 给别人讲一遍"三种 XSS 的差别 + 纵深防御七层"

---

## 📝 练习题

### 基础题（巩固机制）

**Q1. 分类判断**
对下面每个场景，判断它最可能是**反射型 / 存储型 / DOM 型**中的哪一种，
并写出"修复应该改哪一层"：

```
A. 搜索页把 q 参数直接显示在 "<div>你搜索了：{q}</div>" 里
B. 用户昵称在个人主页、评论列表、邮件通知三处都被渲染
C. 页面 JS 把 location.hash 直接赋给 el.innerHTML
D. 后台"查看访问日志"页面，把 User-Agent 原样显示（UA 是攻击者可控的）
E. 前端把 postMessage 收到的数据直接写进 document.write
F. 商品评价内容在详情页被渲染（评价由用户提交）
```

**Q2. 上下文配对**
左边是输出位置，右边是正确做法。请配对并说明"用错会怎样"：

| 输出位置 | 应选方案 |
|---|---|
| `<p>{X}</p>` | A. `urllib.parse.quote(x, safe='')` |
| `<input value="{X}">` | B. 不要拼；用 `json.dumps` 或 `data-*` 属性 |
| `<a href="/s?q={X}">` | C. `html.escape(x, quote=True)` |
| `<script>var a = '{X}';</script>` | D. 只允许白名单格式（如颜色正则），否则回落默认值 |
| `style="color: {X}"` | E. `html.escape(x, quote=True)` + 属性必须加引号 |

**Q3. 响应头纠错**
下面这个响应头集合有哪些问题？请写出修复后的版本并逐条说明原因。

```http
Content-Security-Policy: default-src *; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net
X-Content-Type-Options: sniff
Set-Cookie: sid=abc; SameSite=None; Path=/
Server: nginx/1.14.0
```

**Q4. 判断题（必须写理由，不要只写对错）**
1. 只要用了 ORM / 参数化查询，就不会有 XSS。
2. `html.escape(s)` 可以安全地用在 `<script>` 里的字符串常量上。
3. Cookie 设了 `HttpOnly` 之后，XSS 就"没有危害"了。
4. 前端用 `textContent` 就一定不会有 DOM 型 XSS。
5. 在输入处统一 `html.escape` 一遍，输出时就不用再编码了。
6. `SameSite=Lax` 加上去之后 CSRF Token 就不需要了。

**Q5. 手写编码器**
不查资料，写出下面三个函数，并用 Q1 里的样例自测：

```python
def safe_html_text(s: str) -> str: ...
def safe_html_attr(s: str) -> str: ...
def safe_url_param(s: str) -> str: ...
```

要求：对输入 `<x152probe>`、`" onmouseover="x()"`、`'><b>`、
`&amp;` 四个样例，输出中**不允许**出现裸的 `< > " '` 四个字符。
写完后回到 `code/02-xss-defense-pitfalls.py` 对照。

---

### 进阶题（动手 + 攻防视角）

**Q6. 给扫描器加一种上下文**
在 `code/03-xss-scanner.py` 的 `PROBE_TEMPLATES` 里增加一种探测：

```
"URL 属性上下文（javascript: 伪协议）": "javascript:x152probe{t}"
```

要点：

1. 探测标记不要带 `()`，避免任何"像代码"的样子；
2. 在 `classify()` 里增加一条判定：如果响应里出现了 `javascript:` 且**未被改写**，
   输出 FAIL，建议"URL 属性必须做协议白名单"；
3. 在本地靶场 `LabHandler` 里加一个 `/link` 端点专门演示这个漏洞
   （把用户输入放进 `<a href="{val}">`）；
4. 用你改完的扫描器跑一遍，确认 `/link` 被判成 FAIL。

**Q7. 让扫描器识别"双重编码"**
如果一个服务端把输入的 `<` 先变成 `&lt;`、再整体编码一次变成 `&amp;lt;`，
那么浏览器最终显示的是 `&lt;` 而不是 `<` —— 这**不是安全漏洞，是 Bug**。

请给 `classify()` 增加一条 `WARN` 分支：

- 当响应中出现 `&amp;lt;` 形态时，判为 WARN，提示
  "疑似双重编码：数据被编码了两次（数据损坏，页面会显示实体字符）"；
- 在 `/safe` 端点里加一个 `?double=1` 开关来制造这个现象，验证你的实现。

**Q8. 审计报告接 CI**
写一个脚本 `ci-xss-check.sh`，把扫描结果接到流水线上：

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 code/03-xss-scanner.py --json > /tmp/xss.json || true
python3 - <<'PY'
import json, sys
r = json.load(open('/tmp/xss.json'))
c = r['counts']
print(f"PASS={c['PASS']} WARN={c['WARN']} FAIL={c['FAIL']} INFO={c['INFO']}")
for f in r['findings']:
    if f['level'] == 'FAIL':
        print(f"  [FAIL] {f['category']} {f['target']}: {f['detail']}")
sys.exit(1 if c['FAIL'] else 0)
PY
```

然后：

1. 确认当前运行退出码是 `1`；
2. 修改 `LabHandler`，把 `/search` 与 `/attr` 都改成**完整正确编码**，
   并给三个端点都加上完整安全头；
3. 再跑脚本，确认退出码变成 `0`。

**Q9. 写一个"最小 CSP 生成器"**
实现函数 `build_csp(nonce: str, allow_inline_style: bool = False) -> str`：

- 必须包含 `default-src`、`script-src`（带 nonce 且带 `'strict-dynamic'`）、
  `object-src 'none'`、`base-uri 'none'`、`frame-ancestors 'none'`、
  `form-action 'self'`；
- `allow_inline_style=True` 时才加 `style-src 'unsafe-inline'`；
- 写一个自测：断言生成结果**不含** `unsafe-inline`（默认情况下）且**含** `nonce-`。

然后用 `code/02-xss-defense-pitfalls.py` 的 `SecureHandler` 替换成你的生成器，
对比输出差异。

---

### 挑战题（综合设计，无唯一答案）

**Q10. 设计一个"富文本"安全方案**
业务需要允许用户发**带格式的文章**（加粗、链接、图片、代码块）。请设计：

1. 白名单包含哪些标签和属性？为什么 `img` 很危险？为什么 `a` 必须校验协议？
2. 净化在**哪个环节**做（入库前 / 输出时 / 两者都做）？各自利弊是什么？
3. 如何防止 **mXSS**（净化后的 HTML 重新被浏览器解析时又变异出危险结构）？
4. CSP 在这里应该怎么配？`img-src` 要不要允许任意外域？
5. 写一段"安全渲染"的伪代码（可用任何语言），体现"净化 → 输出 → CSP"三步。

请用 **1 张白名单表 + 1 张流程图 + 1 份风险清单** 呈现结论。

**Q11. 复盘一次真实 XSS 事件**
搜索并阅读任意一个公开的 XSS 事件分析（例如某社交平台的
"昵称/签名 XSS"、某电商的"评论 XSS"、或某 CMS 的 XSS CVE 公告），回答：

1. 它是**哪一类** XSS？数据源和输出点分别在哪？
2. 站方当时**已经做了**哪些防护？为什么还是被打穿了？
3. 修复具体改了哪一层？（编码？净化？CSP？）
4. 如果你现在负责同样的功能，你会怎么设计**端到端**的防护？
5. 这个事件里，"纵深防御"的哪一层本该兜底却没兜住？

> ⚠️ 只做**公开资料的学习与复盘**，不要对任何未授权目标做实际测试。

---

## 🎯 自测标准

| 水平 | 标准 |
|---|---|
| 及格 | 能说清三种 XSS 的差异，能解释输出编码与 `HttpOnly` 的作用边界 |
| 良好 | 能独立写出四种上下文的编码函数，跑通 3 个示例并看懂每条 FAIL 的含义 |
| 优秀 | 能扩展扫描器（Q6/Q7），并完整设计 Q10 的富文本安全方案 |

---

## 📚 延伸阅读（建议自行搜索原文）

- OWASP Cheat Sheet — XSS Prevention（**最权威的上下文编码速查表**）
- OWASP Cheat Sheet — DOM based XSS Prevention / CSRF Prevention / CSP
- OWASP Top 10（2021）A03 注入、A01 访问控制失效
- MDN — Content-Security-Policy（各指令语义与浏览器兼容）
- MDN — `SameSite` cookies 与 `Set-Cookie` 属性说明
- HTML 标准 — "Tokenization" 一节（HTML 解析器状态机，读懂它就不会再写黑名单）
- PortSwigger Web Security Academy — XSS / CSRF 免费实验靶场
- Google — "CSP Evaluator"（把你的 CSP 粘进去，直接告诉你哪里弱）
