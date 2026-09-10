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
