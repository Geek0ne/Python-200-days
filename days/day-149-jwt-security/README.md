# Day 149 — JWT 安全：结构、签名与攻击面

> 阶段：Phase 7 — 进阶与性能优化 · 主题：实战认证安全
>
> 前置知识：Day 147 哈希/HMAC，Day 148 对称与非对称加密。今天把密码学
> 知识落到一个你每天都在用的东西上——**JWT（JSON Web Token）**。
> 几乎所有现代 Web / 微服务 / 移动端的登录态都在用它。它看起来只是
> 一小段 Base64 字符串，但里面藏着的坑多到能写一本书。

---

## 一、概念解释

### 1.1 JWT 是什么

**定义**：JWT（JSON Web Token，读作 "jot"）是一个**开放标准（RFC 7519）**，
它把一组"声明（claims）"编码成一个**紧凑的、URL 安全的、可签名/可加密**的
字符串，用来在双方之间安全地传递信息。

关键词逐个拆开：

| 词 | 含义 |
|---|---|
| JSON | 载荷（payload）本质是一段 JSON 对象 |
| Web | 设计上适合放在 HTTP Header / URL / Cookie 里传输 |
| Token | 它是一次"凭证"，不是会话本身；服务器不用保存它（无状态） |

**为什么发明它？** 传统 Session 方案里，服务器要在内存/数据库里存一份
`session_id → 用户信息` 的映射。当服务从 1 台扩到 100 台，你必须做
**会话共享**（Redis、sticky session……），否则用户请求飘到另一台机器就掉线。
JWT 的思路是：**把用户信息本身放进 token，用签名保证它没被篡改**，服务器
拿到 token 验签即可，不需要查任何存储 —— 这就是**无状态认证**。

**代价是什么？** 无状态不是白来的：

- **无法主动失效**：签发出去的 token 在过期前一直有效，除非引入黑名单
  （那又不无状态了）。所以 JWT 的有效期通常很短（5~30 分钟）。
- **体积大**：Base64 后的 token 通常 200~800 字节，比 `session_id=abc123` 大得多，
  每个请求都要带上。
- **信息是"明文"的**：JWT 的签名只保证**完整性**，不保证**机密性**。
  任何人 Base64 解码就能看到 payload —— 里面**绝对不能放密码、身份证号**。

---

### 1.2 JWT 的三段结构

一个 JWT 是三个 Base64URL 片段用 `.` 连接：

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 . eyJzdWIiOiIxMjMiLCJuYW1lIjoi5LiJIn0 . dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
└──────────── Header ────────────┘   └──────────── Payload ────────────┘   └──────────── Signature ────────────┘
```

#### ① Header（头部）

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- `alg`：**签名算法**，是整份 token 最关键、也是被攻击最多的字段。
  常见值：`HS256/384/512`（HMAC + SHA）、`RS256/384/512`（RSA）、
  `ES256/384/512`（ECDSA）、`PS256`（RSA-PSS），以及危险的 `none`。
- `typ`：类型，固定 `JWT`（可选但有约定）。
- `kid`：**密钥 ID**，告诉验证方用哪把密钥验签（多密钥轮换时用），
  ⚠️ 这也是攻击入口之一（见 2.4）。
- `jku` / `x5u`：指向密钥集合的 URL，⚠️ **极度危险**，绝不能盲信。

#### ② Payload（载荷）

一组 **claims（声明）**，分三类：

**注册声明（Registered Claims）——RFC 定义的"标准字段"：**

| 字段 | 全称 | 含义 | 类型 |
|---|---|---|---|
| `iss` | Issuer | 签发者 | String |
| `sub` | Subject | 主体（通常是用户 ID） | String |
| `aud` | Audience | 预期接收方 | String / Array |
| `exp` | Expiration Time | 过期时间（Unix 秒） | NumericDate |
| `nbf` | Not Before | 生效时间，早于此时间不可用 | NumericDate |
| `iat` | Issued At | 签发时间 | NumericDate |
| `jti` | JWT ID | 唯一 ID，用于防重放/黑名单 | String |

**公共声明（Public Claims）**：注册在 IANA 或用了防冲突命名空间的字段。
**私有声明（Private Claims）**：你和业务约定的字段，如 `role`、`tenant_id`。

```json
{
  "sub": "10086",
  "iss": "https://auth.example.com",
  "aud": "api.example.com",
  "exp": 1757558400,
  "iat": 1757554800,
  "jti": "a1b2c3d4",
  "role": "admin"
}
```

⚠️ **`exp`/`nbf`/`iat` 用的是 Unix 时间戳（秒），不是毫秒**。写成毫秒会
导致 token 有效期变成 5 万年 —— 这是真实出现过的生产事故。

#### ③ Signature（签名）

签名算法的骨架（HMAC 版本）：

```
HMAC-SHA256(
    base64url(header) + "." + base64url(payload),
    secret_key
)
```

用 RSA/ECDSA 时是：

```
RSASSA-PKCS1-v1_5(
    SHA256(base64url(header) + "." + base64url(payload)),
    private_key
)
```

**为什么要签名？** 因为 Header 和 Payload 只是 Base64**编码**（不是加密！），
任何人都能把 `"role":"user"` 改成 `"role":"admin"` 再重新编码。签名的
作用是：**验证方用密钥重新算一遍签名，对得上才说明这段内容自签发后没被
改过**。这就是 JWT 的全部安全根基。

**Base64URL vs Base64**：JWT 用的是 URL 安全变体 —— 把 `+` 换成 `-`、
`/` 换成 `_`，并且**去掉末尾的 `=` 填充**。这样 token 能安全地放进 URL
和 HTTP Header 里，不会因为 `+` `/` `=` 被转义或截断。

### 1.3 JWT ≠ JWE

初学最常见的混淆：**JWS 与 JWE 是两件事**。

| | JWS（签名） | JWE（加密） |
|---|---|---|
| 保证 | 完整性 + 来源 | 机密性 + 完整性 |
| 段数 | **3 段** | **5 段** |
| payload | Base64 明文，谁都能读 | 密文，需密钥才能读 |
| 典型头 | `alg: HS256` | `alg: RSA-OAEP`, `enc: A256GCM` |
| 日常说的"JWT" | 99% 指这个 | 少见 |

所以看到 `xxx.yyy.zzz.aaa.bbb`（5 段）才是加密 JWT。日常的 3 段 JWT
**payload 是公开可读的**，别往里塞秘密。
