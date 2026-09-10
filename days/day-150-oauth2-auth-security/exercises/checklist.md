# Day 150 — OAuth2 与认证安全 · 练习与完成清单

> 主题：OAuth2 授权流程 / CSRF 攻击与防护 / SSRF 漏洞检测
> 实战：认证系统安全审计
> 预计用时：90~150 分钟（不含思考题）

---

## ✅ 今日完成清单

### 概念理解（能用自己的话讲清楚）
- [ ] 说清 **认证（Authentication）** 与 **授权（Authorization）** 的区别，并举 2 个例子
- [ ] 说出 OAuth2 的 **4 个角色**（Resource Owner / Client / Authorization Server / Resource Server）
- [ ] 说出 4 种 grant type 及各自适用场景，并能解释**为什么隐式模式被废弃**
- [ ] 解释 OAuth2 的"**用令牌换密码**"这个设计解决了什么真实问题
- [ ] 说清 OAuth2 **不是登录协议**，为什么做登录要配合 OIDC

### 原理掌握（能画出流程图）
- [ ] 能默画 **授权码流程 6 步**，并标出"哪一步走浏览器、哪一步走服务器"
- [ ] 解释授权码为什么是**一次性 + 短有效期**
- [ ] 解释 **PKCE** 的 `code_verifier → S256 → code_challenge` 三段关系，以及它防的是什么
- [ ] 解释 **state** 参数防的是什么攻击，为什么必须"会话存储 + 一次性"
- [ ] 说清 CSRF 成立的 **3 个前提条件**
- [ ] 说清 **SameSite=Lax 挡不住什么**（至少 2 种场景）
- [ ] 说清 SSRF 为什么危险（能举出云元数据 `169.254.169.254` 的后果）

### 动手实践（跑代码 + 改代码）
- [ ] 运行 `code/01-oauth2-auth-code-flow.py`，观察两种模式（机密 / PKCE）的输出差异
- [ ] 把 `01` 里的 `MiniAuthServer.CODE_TTL` 改成 `1`，再运行一次，观察"授权码过期"分支
- [ ] 故意把 `01` 里的 `state` 校验注释掉，观察漏洞版行为，然后改回来
- [ ] 运行 `code/02-oauth2-csrf-pitfalls.py`，把 4 个坑的"修复前/后"输出都看懂
- [ ] 在 `02` 的 `Bank` 里加一个 `enable_origin_check` 参数，实现 Origin 校验层
- [ ] 运行 `code/03-auth-security-audit.py`，理解 13 个 FAIL 分别对应哪一类问题
- [ ] 运行 `python3 code/03-auth-security-audit.py --json`，把报告存成文件并解析
- [ ] 修改 `03` 的 `demo_config()`，把失败项逐个修好，直到 FAIL 数为 0

### 输出物
- [ ] `days/day-150-oauth2-auth-security/` 目录下 4 类文件齐全（README / code / diagrams / exercises）
- [ ] 3 个 `.py` 全部能 `python3` 直接跑通，无第三方依赖
- [ ] 能对着 `diagrams/README.md` 给别人讲一遍授权码 + PKCE 流程

---

## 📝 练习题

### 基础题（巩固机制）

**Q1. 流程排序**
把下面打乱的事件排成正确的授权码 + PKCE 顺序，并标出每一步发生在哪一侧
（浏览器 / Client 后端 / 授权服务器）：

```
A. 客户端生成 code_verifier 与 state
B. 授权服务器校验 SHA256(code_verifier) == code_challenge
C. 浏览器被重定向到 /callback?code=...&state=...
D. 客户端校验 state 是否与会话中一致
E. 用户点击"同意授权"
F. 客户端 POST /token 携带 code + code_verifier + client_secret
G. 客户端生成 code_challenge = Base64URL(SHA256(code_verifier))
H. 授权服务器返回 access_token 与 refresh_token
```

**Q2. 参数配对**
为下列参数选出它"防的是什么攻击"：

| 参数 | 选项 |
|---|---|
| `state` | A. 授权码被第三方截获后换取令牌 |
| `code_challenge` / `code_verifier` | B. CSRF：攻击者用自己的 code 绑定受害者账号 |
| `redirect_uri` 精确匹配 | C. 令牌重放 / 身份混淆（OIDC） |
| `nonce`（OIDC） | D. 授权码被重定向到攻击者服务器 |
| `refresh_token` 轮转 | E. 刷新令牌被窃取后长期滥用 |

**Q3. Cookie 配置纠错**
下面这行 `Set-Cookie` 有哪些安全问题？请写出修复后的版本并逐条说明原因。

```http
Set-Cookie: session=abc123; Domain=example.com; Path=/; Max-Age=2592000
```

**Q4. 判断题（说明理由，不要只写对错）**
1. 有了 `SameSite=Lax` 就可以不要 CSRF Token 了。
2. `SameSite=None` 表示"允许跨站发送 Cookie，所以更宽松更兼容，没什么风险"。
3. 只要用了参数化查询/ORM，SSRF 就不可能发生了。
4. `redirect_uri` 用 `startswith("https://myapp.com/cb")` 判断就够了。
5. access_token 存在 localStorage 和存在 Cookie 一样安全，只要页面没有 XSS。

---

### 进阶题（动手 + 攻防视角）

**Q5. 给 `02` 加一层防护**
在 `code/02-oauth2-csrf-pitfalls.py` 的 `Bank` 类里实现 **Origin 校验层**：

- 新增 `self.allowed_origins = {"https://bank.com"}`
- `transfer()` 增加 `origin` 参数，当 `origin not in allowed_origins` 时返回 403
- 用一个通过 SameSite 检查（`same-site`）但 Origin 伪造的请求测试它
- 思考：为什么 Origin 校验只能当"补充层"？（提示：谁一定会带 Origin 头？）

**Q6. 写一个 `redirect_uri` 校验器**
要求：

1. 输入：`registered: list[str]`、`incoming: str`
2. 规则：精确匹配注册值；scheme 必须为 `https`（`http://localhost` 例外）
3. 输出：`(bool, reason)`
4. 用下面这些攻击样例自测，全部必须被拒绝：

```
https://app.com/cb.evil.com
https://app.com/cb/../steal
https://app.com/cb@evil.com
https://app.com.evil.com/cb
https://app.com/cb?x=1#@evil.com
http://app.com/cb            ← 非 https，应拒绝
```

**Q7. 扩展 SSRF 检测器**
为 `code/03-auth-security-audit.py` 的 `check_url_ssrf()` 增加两项检测：

1. **IPv6 映射检测**：`http://[::ffff:127.0.0.1]/`、`http://[::1]/` 必须报警
2. **短域名/重定向链检测**：如果 URL 主机是已知短链服务
   （`bit.ly`、`t.cn`、`tinyurl.com` 等），输出 WARN 提示"最终目标不可控"

再用这些样例验证你的实现：

```
http://[::ffff:127.0.0.1]/
http://[::1]:8080/
https://bit.ly/3xyzAbc
https://cdn.example.com/ok.png
```

**Q8. 审计报告接 CI**
写一个 shell 脚本 `ci-audit.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
python3 code/03-auth-security-audit.py --json > /tmp/audit.json || true
python3 - <<'PY'
import json, sys
r = json.load(open('/tmp/audit.json'))
print(f"FAIL={r['counts']['FAIL']} WARN={r['counts']['WARN']}")
sys.exit(1 if r['counts']['FAIL'] else 0)
PY
```

然后：把 `demo_config()` 的失败项全部修好，确认脚本退出码从 `1` 变 `0`。

---

### 挑战题（综合设计，无唯一答案）

**Q9. 设计一个"零信任"登录链路**
为一个"手机 App + Web 后台 + 第三方登录"的系统，写出完整的认证/授权方案，
必须覆盖：

- 用哪种 grant type？为什么？
- `state` / PKCE / `nonce` 分别放哪、谁生成、谁校验、存哪里？
- access_token 与 refresh_token 的有效期、存储位置、轮转策略
- CSRF 防护用哪几层？
- 用户改密码 / 登出 / 检测到 refresh 重放时，如何做到"立刻失效"？
- 全链路哪些地方可能出 SSRF？怎么防？

请用 **1 张流程图 + 1 张参数表 + 1 份风险清单** 呈现结论。

**Q10. 还原一次真实漏洞**
搜索 2019 年 Capital One 数据泄露事件的公开分析，回答：

1. SSRF 出现在哪个功能上？（提示：WAF 与 EC2 元数据）
2. 攻击者最终拿到的是什么？为什么这比"读到一个页面"严重得多？
3. 如果当时做了"解析后校验 IP 且不跟随重定向"，攻击能否被阻止？
4. 除了代码层，云侧配置还应做什么加固？

> ⚠️ 注意：只做**公开资料的学习与复盘**，不要对任何未授权目标做实际测试。

---

## 🎯 自测标准

| 水平 | 标准 |
|---|---|
| 及格 | 能说清授权码流程 6 步，能解释 state 与 PKCE 各防什么 |
| 良好 | 能独立写出 CSRF 的四层防护，并跑通 3 个示例代码 |
| 优秀 | 能扩展审计脚本（Q7），并完整设计 Q9 的零信任登录链路 |

---

## 📚 延伸阅读（建议自行搜索原文）

- RFC 6749 — The OAuth 2.0 Authorization Framework
- RFC 7636 — PKCE（Proof Key for Code Exchange）
- RFC 9700 — OAuth 2.0 Security Best Current Practice（强烈推荐通读）
- RFC 6265bis — Cookies: HTTP State Management（`SameSite` 权威定义）
- OWASP Cheat Sheet — CSRF Prevention / SSRF Prevention
- OWASP Top 10（2021）A01 访问控制失效、A10 SSRF
- PortSwigger Web Security Academy — CSRF / SSRF 实验（有免费靶场）
