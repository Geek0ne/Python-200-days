# Day 150 — OAuth2 与认证安全：授权流程、CSRF/SSRF 与安全审计

> 阶段：Phase 7 — 进阶与性能优化 · 主题：实战认证安全
>
> 前置知识：Day 146 HTTPS/TLS、Day 147 哈希与 HMAC、Day 148 对称/非对称加密、
> Day 149 JWT。今天把前面几天的密码学与令牌知识，接到 Web 世界里最普遍、也最
> 容易被做错的一套协议上：**OAuth 2.0**。同时补齐两个"不见血但很致命"的漏洞
> 类型：**CSRF**（跨站请求伪造）与 **SSRF**（服务端请求伪造），最后写一个
> **认证系统安全审计脚本**把今天所有检查点自动化。

---

## 一、概念解释

### 1.1 先分清：认证（Authentication）与授权（Authorization）

这两个词中文只差一个字，含义完全不同，混用会导致整个账号体系设计跑偏。

| 概念 | 英文 | 回答的问题 | 典型技术 |
|---|---|---|---|
| 认证 | Authentication | **你是谁？** | 密码、短信码、TOTP、WebAuthn、JWT |
| 授权 | Authorization | **你能做什么？** | OAuth2、RBAC、ABAC、scope、权限表 |

> 记忆法：**认证在前，授权在后**。你必须先证明"你是张三"，系统才能判断
> "张三能不能删这条订单"。

**为什么必须分开？** 因为现实里有两种完全不同的需求：

1. **我要登录你的系统** → 认证问题 → 用密码/验证码 → 得到"我是谁"。
2. **我要让第三方应用读取我在你系统里的数据，但我**不想把密码给它** →
   授权问题 → 用 OAuth2 → 得到"第三方能做什么"的受限凭证。

OAuth2 **只解决第 2 类问题**。它本身**不是登录协议**——用 OAuth2 做登录，
必须在它之上再套一层（OpenID Connect，简称 OIDC）才能安全地拿到"用户是谁"。
很多系统出安全事故，根源就是**把 OAuth2 当登录协议用了**。

---

### 1.2 OAuth2 是什么，不是什么

**定义**：OAuth 2.0（RFC 6749）是一个**授权框架（authorization framework）**，
它让资源所有者（用户）可以授权第三方应用（Client）**有限地、可撤销地**
访问自己在某服务上的受保护资源，而**无需把自己的密码交给第三方**。

它解决问题的方式可以一句话概括：

> **把"密码"换成"有范围、有期限、可撤销的令牌（Access Token）"。**

**它不是什么：**

- ❌ 不是认证协议（不告诉你"用户是谁"，只告诉你"这个令牌被授权做什么"）。
- ❌ 不是加密协议（它规定怎么"要令牌"，不规定令牌内容必须加密）。
- ❌ 不是身份提供商的实现（Google/微信/钉钉 是**实现了 OAuth2 的服务**）。

**为什么需要它？** 想象 2010 年以前的做法：你在某个"导入通讯录"网站里
输入 Gmail 的**账号密码**，它拿你的密码去登录 Gmail 抓联系人。后果是：

- 网站能拿到你的**明文密码**，等于把家门钥匙给了别人；
- 网站权限**无限大**，能读邮件、能发邮件、能改密码；
- 你**无法撤销**，除非改密码（改了所有设备都掉线）。

OAuth2 把这三件事全解决了：**不传密码、限定 scope、令牌可撤销且有期限**。

---

### 1.3 四个角色（必须背下来）

| 角色 | 英文 | 通俗解释 | 例子 |
|---|---|---|---|
| 资源所有者 | Resource Owner | 数据的主人 | 你 |
| 客户端 | Client | 想访问数据的应用 | "某记账 App" |
| 授权服务器 | Authorization Server | 发令牌的地方 | Google 账号中心 |
| 资源服务器 | Resource Server | 存数据、验令牌的地方 | Gmail API |

⚠️ **授权服务器和资源服务器可以是同一台，也可以是两台**（微服务里经常拆开）。
很多漏洞就出在"授权服务器验的令牌，资源服务器验得不一样"。

---

### 1.4 四个授权模式（Grant Types）

| 模式 | 适用场景 | 安全性 | 现代建议 |
|---|---|---|---|
| **授权码（Authorization Code）** | 有后端的 Web / App | ⭐⭐⭐⭐⭐ | ✅ 首选 |
| **授权码 + PKCE** | 纯前端 SPA、移动 App | ⭐⭐⭐⭐⭐ | ✅ 移动/SPA 必须 |
| 隐式（Implicit） | 老式 SPA | ⭐⭐ | ❌ 已废弃，用 `code+PKCE` |
| 密码（Password / ROPC） | 自家 App 登录自家服务 | ⭐ | ❌ 已废弃 |
| 客户端凭证（Client Credentials） | 服务端对服务端，**无用户** | ⭐⭐⭐⭐ | ✅ 机器间调用 |

**为什么隐式模式被废弃？** 因为它把 access_token 直接放在**URL 的 fragment**
（`#access_token=...`）里返回。URL 会被写进浏览器历史、被 Referer 头带出去、
被日志系统记录、被前端 JS 读到——令牌泄漏面极大，而且**没法用 refresh token**
（因为刷新需要客户端认证，前端没有"秘密"可认证）。RFC 9700（OAuth 2.0
Security Best Current Practice）已明确建议弃用。

**为什么需要 PKCE？** 授权码流程有个天生弱点：在移动 App / SPA 里，客户端
**没有能力安全保存 client_secret**（反编译 App 就能拿到）。于是攻击者可以
冒充这个 client 去换 token。PKCE 的思路是：**每次请求都生成一对临时的
"验证码 + 摘要"**，用一次就作废，从而不需要长期密钥。

---

### 1.5 CSRF（跨站请求伪造）是什么

**定义**：攻击者诱导**已登录用户的浏览器**，向目标网站发送一个**用户并不知情
的、带有用户身份凭证的请求**。

**关键前提（三个条件同时成立才会中招）：**

1. 浏览器会自动携带身份凭证（主要是 **Cookie**）；
2. 服务器**只靠 Cookie 判断"是谁"**，不校验请求来源；
3. 攻击者能构造出有效的、有副作用的请求（转账、改密码、发帖……）。

**为什么危险？** 因为服务器看到的确实是"合法用户的合法 Cookie"，从服务端
视角**完全无法区分**这是用户自己点的，还是恶意网页自动发的。它不是"偷密码"，
而是"**借你的手**"——所以中文也译作"跨站请求伪造"。

**一句话原理**：Cookie 的 `SameSite` 默认行为和"跨站请求会带 Cookie"这个
浏览器设计，是 CSRF 存在的土壤。

---

### 1.6 SSRF（服务端请求伪造）是什么

**定义**：攻击者**控制了服务端发起的网络请求的目标地址**，让服务器去请求
攻击者指定的 URL —— 从而以服务器的身份、从**内网视角**发起请求。

**为什么它比 CSRF 更凶险？**

- 服务器通常**在内网**，能访问外网访问不到的东西：数据库、Redis、
  内部管理后台、K8s API、云厂商**元数据服务**（`169.254.169.254`）。
- 很多云环境的元数据服务能直接换取**临时云凭证**（IAM Role），拿到就等于
  **接管整台云主机/整个云账号**（2019 年 Capital One 泄露 1 亿用户数据就是 SSRF）。
- 它常常只是"**跳板**"：先用 SSRF 打通内网，再配合其他漏洞扩大战果。

**典型入口**：图片抓取、网页截图、URL 预览、Webhook 回调、PDF 导出、
"从链接导入数据"等**用户可控 URL** 的功能。

---

## 二、原理解释（底层机制）

### 2.1 授权码流程（Authorization Code Flow）逐步拆解

```
① 用户点"用 Google 登录"
   Client → 浏览器重定向 → Authorization Server
   GET /authorize?response_type=code
                &client_id=CLIENT_ID
                &redirect_uri=https://app.com/cb
                &scope=email+profile
                &state=RANDOM_CSRF_TOKEN
                &code_challenge=xxx&code_challenge_method=S256   ← PKCE

② 用户在授权服务器上"同意授权"（这一步能看到"应用要读你的邮箱"）

③ 授权服务器重定向回 Client
   302 https://app.com/cb?code=AUTH_CODE&state=RANDOM_CSRF_TOKEN

④ Client 后端用 code 换 token（这一步走服务器到服务器，浏览器看不到）
   POST /token
     grant_type=authorization_code
     &code=AUTH_CODE
     &redirect_uri=https://app.com/cb
     &client_id=...&client_secret=...
     &code_verifier=原始随机串    ← PKCE

⑤ 授权服务器返回
   {"access_token":"...", "refresh_token":"...", "expires_in":3600, "token_type":"Bearer"}

⑥ Client 用 access_token 访问资源
   GET /userinfo  Authorization: Bearer <access_token>
```

**为什么要把"发码"和"换令牌"分成两步？**

- 授权码是**通过浏览器前端**（URL 重定向）传回来的，可以被 URL 日志、历史记录、
  Referer 泄漏 —— 所以它**天生不安全**。
- 因此设计上给授权码加了两个保险：**① 一次性、极短有效期（通常 30~60 秒）；
  ② 换令牌时必须由客户端**后端**带着 `client_secret` 发起**。
- 攻击者就算截到授权码，只要换不了令牌（拿不到 secret），也拿不到 access_token。

这就是**授权码流程最核心的设计思想**：让"敏感的令牌"永远不经过浏览器，
浏览器只传一个"很快就作废的临时凭证"。

### 2.2 PKCE 原理（Proof Key for Code Exchange, RFC 7636）

PKCE 解决的是"**公开客户端（Public Client）没有 client_secret**"的问题。

```
Client 侧（一次性随机）:
  code_verifier  = 随机 43~128 字符的高熵字符串
  code_challenge = BASE64URL( SHA256(code_verifier) )      # method = S256

① 授权请求带上 code_challenge
② 换令牌请求带上 code_verifier
③ 授权服务器计算 SHA256(verifier)，与最初存的 challenge 比对
```

**为什么这样能防攻击？** 攻击者即使**截获了授权码**，也不知道 `code_verifier`
（它只存在于生成它的那个客户端内存里，从不经过浏览器 URL）。没有 verifier，
换不到令牌。

⚠️ **避坑**：`code_challenge_method` 必须是 `S256`，**绝不能用 `plain`**
（plain 等于明文传 verifier，PKCE 白做）。另外 verifier 必须用
**密码学安全的随机源**（Python 里是 `secrets`，不是 `random`）。

### 2.3 `state` 参数：OAuth2 里的 CSRF 防护

`state` 是一段**客户端自己生成的随机串**，在授权请求里带上，授权服务器
**原样回传**。客户端在回调里比对：对不上就拒绝。

**它防的正是 CSRF**。攻击流程如下（无 state 时）：

```
攻击者用自己的账号在 Google 走完授权，拿到一个回调 URL:
  https://victim-app.com/cb?code=ATTACKER_CODE
然后把这个 URL 发给受害者，诱导其点击（图片/链接/短链）。
受害者浏览器带着自己的会话 Cookie 访问该 URL；
应用用 ATTACKER_CODE 换了令牌，把攻击者的第三方账号
绑定到了受害者的账号上 → 攻击者以后可以用自己的第三方账号登录受害者账号。
```

加了 `state` 后：回调里的 state 和受害者浏览器会话里存的 state 不一致 → 拒绝。

**记住三件绑定关系：** `state` 必须

1. **随机且高熵**（`secrets.token_urlsafe(32)`）；
2. **存在用户会话里**（服务端 session，或加密 Cookie）；
3. **用后即焚**（一次性，回调后立刻删除，防重放）。

### 2.4 CSRF 攻击原理与四层防护

**攻击本体（一个恶意 HTML 页面就够了）：**

```html
<!-- evil.com 上的页面 -->
<form action="https://bank.com/transfer" method="POST" id="f">
  <input name="to"   value="attacker">
  <input name="amount" value="10000">
</form>
<script>document.getElementById('f').submit()</script>
```

用户只要在登录 bank.com 的状态下访问 evil.com，浏览器就会**自动带上
bank.com 的 Cookie** 去 POST —— 服务器以为是用户本人操作。

> ⚠️ 注意：**CORS 不能防 CSRF**。CORS 限制的是"JS 能不能读取响应"，
> 不是"请求能不能发出去"。简单请求（表单、img、script）根本不受 CORS 预检约束。

**四层防护，建议全上（纵深防御）：**

| 防护 | 机制 | 强度 | 备注 |
|---|---|---|---|
| `SameSite=Lax/Strict` Cookie | 浏览器跨站请求时不带该 Cookie | ⭐⭐⭐⭐ | 现代首选，默认 `Lax` |
| Synchronizer Token（CSRF Token） | 服务端生成随机 token 存 session，表单/头里必须带上并比对 | ⭐⭐⭐⭐⭐ | 传统可靠方案 |
| Double Submit Cookie | token 同时放 Cookie 和请求体，服务端比对两者 | ⭐⭐⭐ | 适合无状态服务，需签名 |
| `Origin` / `Referer` 校验 | 检查请求来源域名白名单 | ⭐⭐⭐ | 作为补充，不要单独依赖 |

⚠️ **避坑**：`SameSite=None` 必须配合 `Secure`；只对**状态改变**的请求
（POST/PUT/DELETE）做校验，GET 必须**无副作用**（否则 CSRF 防护失效）；
JSON API 若靠 `Content-Type: application/json` 做隐式防护是**不可靠的**
（攻击者可用 `text/plain` 绕过表单限制的场景要具体分析）。

### 2.5 SSRF 原理、检测与防护

**原理**：任何"服务端会去请求一个 URL"的功能，如果 URL 部分或全部
**用户可控**，就可能是 SSRF。

**常见绕过手法（做检测时必须考虑）：**

| 绕过手法 | 例子 |
|---|---|
| 十进制/八进制/十六进制 IP | `http://2130706433/` = `127.0.0.1`；`http://0x7f000001/` |
| IPv6 映射 | `http://[::ffff:127.0.0.1]/`、`http://[::1]/` |
| 短域名/重定向 | `http://attacker.com` → 302 到 `http://169.254.169.254/` |
| DNS Rebinding | 第一次解析到公网 IP（通过校验），第二次解析到内网 IP（发起请求） |
| 用户名 @ 混淆 | `http://expected.com@evil.com/` |
| 域名后缀混淆 | `http://evil.com#expected.com`、`http://expected.com.evil.com` |
| URL 解析差异 | `http://expected.com%2f@evil.com`、多余 `\` 或 `@` |

**高危目标（防护黑名单必须包含）：**

- `127.0.0.0/8`、`::1`（本机）
- `10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`（内网）
- `169.254.0.0/16` 特别是 `169.254.169.254`（云元数据）
- `0.0.0.0/8`、`100.64.0.0/10`（CGNAT）、`224.0.0.0/4`（组播）
- 云厂商专用：`metadata.google.internal`、`100.100.100.200`（阿里云）

**正确防护顺序（白名单 > 黑名单）：**

1. **业务上优先白名单**：只允许固定域名/路径，用映射表（`id → URL`）而非直接收 URL；
2. **协议白名单**：只允许 `http/https`，禁止 `file://`、`gopher://`、`dict://`、
   `ftp://`（老漏洞里这些协议能打内网服务）；
3. **解析 → 校验 → 再请求，且 IP 校验后不要再二次 DNS 解析**（防 Rebinding），
   最稳的是：**解析出 IP 后直接连该 IP，并带上 Host 头**；
4. **禁止跟随重定向**（或每次跳转都重新校验）；
5. **网络层隔离**：出网走代理，代理侧做白名单；云元数据服务用 IMDSv2（需要 token）。

---

