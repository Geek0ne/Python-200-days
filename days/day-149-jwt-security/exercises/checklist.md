# Day 149 练习与检查表 — JWT 安全

## ✅ 完成清单

- [ ] 能画出 JWT 的三段结构，并说清每段存的是什么
- [ ] 记住 Header 里的 `alg` / `typ` / `kid` / `jku` / `x5u` 各是什么
- [ ] 能背出 7 个注册声明：`iss` `sub` `aud` `exp` `nbf` `iat` `jti`
- [ ] 知道 `exp`/`nbf`/`iat` 单位是 **Unix 秒**，不是毫秒
- [ ] 能解释"Base64 是编码不是加密"，payload 任何人可读
- [ ] 理解签名的本质：`sign(base64url(header).base64url(payload))`
- [ ] 能说清 HMAC（HS256）与非对称（RS256/ES256）的信任模型差异
- [ ] 理解 HMAC 为什么要用双层哈希（防长度扩展攻击）
- [ ] 能复述 `alg=none` 攻击的原理与防护
- [ ] 能复述 HS/RS 算法混淆攻击的原理与防护
- [ ] 知道弱密钥可**离线**爆破，密钥必须 ≥32 字节随机熵
- [ ] 知道 `kid` 注入（路径穿越 / SQLi）与 `jku` 密钥注入
- [ ] 能列出验证时**必须**检查的 6 件事（签名/alg/exp/nbf/iss/aud）
- [ ] 理解 `aud` 不校验会导致跨服务 token 混用
- [ ] 知道 `options={"require": [...]}` 的作用
- [ ] 知道对外统一返回 401、不泄露具体失败原因
- [ ] 跑通 `code/01`、`code/02`、`code/03` 三个示例
- [ ] 用 `code/03` 审计一个真实站点的 token（仅限自有/授权系统）

## 📝 练习题

### 基础

**1. 结构默写**：不查资料，写出下面这张表：

| 段 | 内容 | 编码方式 | 是否加密 | 被签名保护？ |
|---|---|---|---|---|
| Header | ? | ? | ? | ? |
| Payload | ? | ? | ? | ? |
| Signature | ? | ? | ? | — |

**2. 手工造 token**：不用 `pyjwt`，只用 `json` + `base64` + `hmac` + `hashlib`，
为一个 payload `{"sub":"42","exp":<现在+60>}` 生成合法的 HS256 token，
再用 `jwt.decode(token, key, algorithms=["HS256"])` 验证通过。

**3. 时间单位陷阱**：下面这段代码有什么问题？会导致什么后果？

```python
payload = {"sub": "1", "exp": int(time.time() * 1000) + 300_000}
```

**4. 异常分类**：下列场景分别抛哪个异常？把左右连起来（可写多个）。

| 场景 | 异常 |
|---|---|
| A. 签名不匹配 | 1. `ExpiredSignatureError` |
| B. token 已过期 | 2. `InvalidSignatureError` |
| C. `nbf` 是未来时间 | 3. `InvalidAlgorithmError` |
| D. 用 HS256 签却按 RS256 验 | 4. `ImmatureSignatureError` |
| E. `aud` 不匹配 | 5. `InvalidAudienceError` |

**5. 解码不验签**：写一段代码，**不验证签名**地打印出某个 token 的
Header 和 Payload，并解释为什么这个操作在"取 `kid` 之前"是允许的，
而在"做鉴权决策"时是致命的。

### 进阶

**6. 写一个"故意的脆弱验证器"再修好它**：实现 `vulnerable_verify(token, key)`，
要求同时存在两个漏洞：① 算法取自 `Header.alg`；② 不校验 `exp`。
然后用它攻击自己（伪造 `alg=none` 的 admin token），确认攻击成功；
最后写 `secure_verify(token, key)` 把两个洞都堵上，确认攻击失败。

**7. 扩展 `code/03` 的审计器**：新增一条规则 —— 检测 **`iat` 与 `exp` 的
时间跨度**（即 token 生命周期）：
- 若 `exp - iat > 3600` 报"中危：生命周期 > 1 小时"
- 若 `exp - iat > 86400` 报"高危：生命周期 > 24 小时"
- 若 `exp - iat <= 0` 报"严重：时间区间非法"
要求：写出规则函数，并对至少 3 个构造样本验证输出正确。

**8. 给审计器加"HS256 公钥混淆"检测**：如果 token 的 `alg` 是 HS256，
但 `kid` 或 Header 里出现了 `jku`/`x5u`（说明系统本可能是非对称体系），
这本身就是强烈的可疑信号。实现这条规则并解释判断依据。

**9. 实现 refresh token 撤销**：用内存字典模拟：
```python
revoked = set()
def logout(jti): revoked.add(jti)
def is_revoked(jti): return jti in revoked
```
实现"登出后 refresh 立刻失效"的完整流程，并回答：为什么 access token
在登出后**仍然可能有效**？如何把这个窗口从 15 分钟压到接近 0？
（提示：access 也带 `jti` + 短黑名单；或引入 token 版本号。）

### 挑战

**10. 完整实现 RS256 认证服务（含密钥轮换）**：
- 用 `cryptography` 生成两对 RSA 密钥，分别打上 `kid`：「k1」「k2」
- 实现 `/jwks` 端点逻辑：把两把公钥序列化成 JWKS（`kty`/`n`/`e`/`kid`/`alg`）
- 实现 `verify(token)`：从 Header 读 `kid` → 从**本地密钥环**（不是网络）
  取对应公钥 → 按 `algorithms=["RS256"]` 验签
- 模拟轮换：用 k2 签发新 token，同时 k1 仍可验证旧 token；过渡期结束后
  移除 k1，旧 token 自然失效
- 用 `jwt.api_jwk.PyJWKClient` 对照实现一版"从 JWKS 拉公钥"的写法，
  并说明为什么绝不能信任 token 里的 `jku` 指向的 URL

**11. 红队视角：写一份 JWT 检查清单**：假设你在给一个 Web 系统做
授权渗透测试，只被允许拿到一个测试账号。请写出你的完整 JWT 攻击
尝试清单（按优先级排序），每条包含：
- 检测手法（怎么判断有没有这个洞）
- 利用方式
- 修复建议
- 风险等级

至少要覆盖：`alg=none`、算法混淆、弱密钥爆破（说明用什么工具：
`hashcat -m 16500` / `jwt_tool`）、`kid` 注入、`jku`/`x5u` 注入、
`exp` 缺失/过长、`aud` 缺失导致的跨服务混用、payload 信息泄露、
以及"签名校验被整体关闭"这种实现级失误。

**12. 防御纵深设计（开放题）**：请为一个拥有 50 个微服务、
10 万日活用户的系统，设计完整的 JWT 认证架构方案，说明：
- 用哪种算法？为什么？
- access / refresh 各自 TTL 与存储位置（Cookie 还是 localStorage？）
- 如何防 XSS 窃取 token？如何防 CSRF？
- 如何实现"封禁用户后 1 分钟内全网生效"？
- 密钥如何生成、存储、轮换、应急更换？
- 如何监控异常（如大量验签失败、同一 `jti` 高频复用）？

要求给出取舍理由，而不是只给结论。
