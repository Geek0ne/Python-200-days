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

---

## 二、原理深入：签名、验证与算法选择

### 2.1 HMAC（HS256）到底怎么算的

HMAC 的核心思想是**双层哈希**，防止长度扩展攻击：

```
HMAC(K, m) = H( (K ⊕ opad) || H( (K ⊕ ipad) || m ) )

其中 ipad = 0x36 重复到分组长度，opad = 0x5c 重复到分组长度
```

- **第一层**：把密钥与明文混在一起做哈希，产生"内部摘要"。
- **第二层**：再用密钥对内部摘要做一次哈希，产生最终 MAC。

**为什么不能直接 `SHA256(key + msg)`？** 因为 SHA-256 是 Merkle–Damgård
结构，攻击者知道 `SHA256(k||m)` 后，可以在不知道 `k` 的情况下接力算出
`SHA256(k||m||padding||extra)` —— 这就是著名的**长度扩展攻击**。HMAC 的
双层设计把这个可能性堵死了。

**HS256 的安全前提**：密钥必须有**足够的熵**。`secret`、`123456`、
`company2024` 这类弱密钥，配合 JWT 常见的高频词表，几秒钟就能被爆破。
RFC 7518 要求 HS256 密钥**至少 256 bit（32 字节）的随机熵**。

### 2.2 RSA（RS256）验证流程

非对称签名解决了"验证方不该拿到签名密钥"的问题：

```
签发方（Auth Server）                    验证方（API Server）
     ┌──────────┐                            ┌──────────┐
     │ 私钥(sec)│                            │ 公钥(pub)│
     └────┬─────┘                            └────┬─────┘
   sign(header.payload)                         verify(header.payload, sig)
          │                                          │
          ▼                                          ▼
      signature ────── 网络上传输 ─────────────►  通过? → 信任
```

- **HS256**：签发方 = 验证方，共享一把密钥。适合单体应用。
- **RS256/ES256**：只有授权服务器有私钥，其他服务只持公钥。适合微服务、
  第三方登录（Google 的公钥是公开的，谁都能验，但只有 Google 能签）。
- **ES256**：256 bit 密钥 ≈ 3072 bit RSA 的安全强度，签名更短、速度更快，
  现代系统首选。

**选型口诀**：多方验证用非对称（RS/ES/PS），单方自用可 HMAC（HS），
**永远不要用 none**。

### 2.3 验证方必须检查的 6 件事

一个**正确**的 JWT 验证不是"签名对就放行"，而是逐项校验：

| # | 检查项 | 不检查的后果 |
|---|---|---|
| 1 | **签名**（用 Header 里声明的算法，但算法必须来自服务端白名单） | 伪造 token |
| 2 | **`alg` 在白名单内** | `alg:none` / HS-RS 混淆攻击 |
| 3 | **`exp`** 未过期（并允许少量 clock skew，如 30s） | 永久有效 token |
| 4 | **`nbf`** 已生效 | 提前使用 |
| 5 | **`iss`** 等于可信签发者 | 拿别家签的 token 登录 |
| 6 | **`aud`** 包含自己 | **跨服务 token 混用**：给 A 服务的 token 拿去调 B 服务 |

第 6 条最容易被忽略：如果 A 服务和 B 服务共用一把密钥/同一签发者，
而双方都不校验 `aud`，那**低权限服务签发的 token 就能直接访问高权限服务**。

**为什么 `exp` 要允许 clock skew？** 分布式系统各机器时钟有毫秒到秒级
漂移，不允许偏差会偶发地"刚签发就过期"。

### 2.4 攻击面全景

JWT 的经典攻击分两大类：**算法类**和**密钥/实现类**。

```
                    ┌─────────────────────────────┐
                    │        JWT 攻击面            │
                    └──────────────┬──────────────┘
        ┌──────────────────────┐   │   ┌──────────────────────┐
        │      算法类攻击       │   │   │     密钥 / 实现类      │
        ├──────────────────────┤   │   ├──────────────────────┤
        │ alg=none             │   │   │ 弱密钥爆破 (HS256)     │
        │ HS/RS 算法混淆        │   │   │ kid 路径穿越 / SQLi    │
        │ 弱算法降级 (HS256)    │   │   │ jku/x5u 密钥注入       │
        └──────────────────────┘   │   │ 库实现漏洞 (CVE)       │
                                   │   │ payload 里藏敏感数据    │
                                   │   │ 无 exp / 超长有效期     │
                                   └──────────────────────┘
```

#### 攻击 1：`alg: none`

最古老的 JWT 漏洞。攻击者把 Header 改成 `{"alg":"none","typ":"JWT"}`，
删掉签名段（保留末尾的点），构造 `header.payload.`。如果服务端库在
`alg` 为 `none` 时**跳过验签**，攻击者就能伪造任意身份。

**根因**：库的"宽容"设计 + 应用没指定允许的算法。
**防护**：验证时**显式指定** `algorithms=["HS256"]`，并把 `none` 列入
黑名单。现代 PyJWT 默认会拒绝 `none`，除非你传 `options={"verify_signature": False}`。

#### 攻击 2：HS/RS 算法混淆（Algorithm Confusion）

前提：服务端用 **RS256**（公钥公开可得），但验证代码写成"按 Header 里的
`alg` 动态选择算法"。攻击者把 Header 改成 `{"alg":"HS256"}`，然后用
**服务端公开的 RSA 公钥字符串**当作 HMAC 密钥重新签名。

```
服务端预期：  RS256 验证 → 用公钥验签
攻击者构造：  HS256 签名 → 密钥 = 公钥文本（人人可得！）
服务端 bug：  看到 alg=HS256 → 拿"公钥"当 HMAC 密钥 → 验签通过 ✅ 伪造成功
```

**根因**：信任了攻击者可控的 Header 字段来决定"用什么算法验证"。
**防护**：**算法必须由服务端配置决定，绝不能来自 token**。
PyJWT 要求显式传 `algorithms=["RS256"]` 正是为此。

#### 攻击 3：弱密钥爆破

如果服务端用 HS256 且密钥是弱口令，攻击者可以**离线**爆破：本地拿
token + 候选密钥字典算出签名对比即可，完全不需要访问服务器。

```python
for candidate in wordlist:
    if jwt.encode(header_payload, candidate, algorithm="HS256") == stolen_token:
        print("密钥是", candidate)   # 几秒到几分钟
```

**防护**：密钥用 `secrets.token_bytes(32)` 或 KMS 生成/托管，
定期轮换；用强随机密钥后爆破在计算上不可行。

#### 攻击 4：`kid` 注入

`kid` 用来标识用哪把密钥，实现不当会变成漏洞：

- **路径穿越**：`kid=../../../../dev/null` → 读到空文件 → HMAC 密钥为空 → 可伪造。
- **SQL 注入**：`kid=' UNION SELECT 'attacker_key'--` → 密钥变成攻击者已知值。
- **命令注入**：`kid` 拼进 shell 命令。

**防护**：`kid` **绝不可直接用作文件路径或 SQL**，必须映射到服务端
预置的密钥表。

#### 攻击 5：`jku` / `x5u` 密钥注入

Header 里 `jku` 指向 JWKS（JSON Web Key Set）地址。若服务端盲信，
攻击者把 `jku` 指向自己的服务器，放上自己的公钥，用自己的私钥签名 —— 验证通过。

**防护**：`jku`/`x5u` 必须在**服务端白名单**内，绝不取用户可控 URL。

#### 攻击 6：payload 泄密

payload 只是 Base64，**不是加密**。把手机号、身份证、内部 IP 放进去，
等于明文广播。

**防护**：payload 只放**非敏感**标识（`sub`、`jti`、`role`）；敏感数据
服务端按 `sub` 查库；确需放入则改用 JWE。

---

## 三、定义与使用方法（API 速查）

### 3.1 PyJWT 核心 API

安装：`pip install pyjwt`（要 RS256/ES256 再加 `pip install cryptography`）。

| 函数 | 签名 | 说明 |
|---|---|---|
| `jwt.encode` | `(payload, key, algorithm="HS256", headers=None)` → `str` | 签发 token。PyJWT ≥2.0 返回 `str`，不再是 `bytes` |
| `jwt.decode` | `(jwt, key, algorithms=[...], options=None, audience=None, issuer=None, leeway=0)` | 验证 + 解码。**`algorithms` 必填** |
| `jwt.get_unverified_header` | `(jwt)` → `dict` | ⚠️ **不验签**只解 Header，仅用于取 `kid` 选密钥 |
| `jwt.decode_complete` | `(jwt, key, algorithms=[...])` → `dict` | 同时返回 `header` / `payload` / `signature` |
| `jwt.api_jwk.PyJWKClient` | `(uri).get_signing_key_from_jwt(token)` | 从 JWKS 端点按 `kid` 取公钥（内含缓存） |

**`jwt.decode` 常用参数：**

| 参数 | 作用 | 建议值 |
|---|---|---|
| `algorithms` | 允许的算法**白名单** | `["RS256"]`，绝不要传 `[header["alg"]]` |
| `audience` | 校验 `aud` | 你的服务名，如 `"api.example.com"` |
| `issuer` | 校验 `iss` | 可信签发者，如 `"https://auth.example.com"` |
| `leeway` | 允许的时钟偏移（秒） | `30` |
| `options` | 细粒度开关 | 见下 |

**`options` 常用开关：**

```python
options = {
    "verify_signature": True,      # 永远保持 True
    "verify_exp": True,            # 校验过期
    "verify_nbf": True,            # 校验生效时间
    "verify_aud": True,            # 校验受众
    "verify_iss": True,            # 校验签发者
    "require": ["exp", "iat", "sub"],  # 强制这些 claim 必须存在
}
```

`options["require"]` 是**很容易被忽略但极其重要**的一项：把 `exp`、`iss`、
`aud` 设为必填，能从根上避免"攻击者把字段删掉绕过校验"。

### 3.2 异常类型速查（按需捕获）

```
jwt.InvalidTokenError            ← 所有 JWT 异常的基类（兜底 catch 这个）
├── DecodeError                  ← token 格式/Base64 解码错误
├── InvalidSignatureError        ← 签名不匹配（最常见）
├── InvalidAlgorithmError        ← 算法不在白名单
├── ExpiredSignatureError        ← exp 已过
├── ImmatureSignatureError       ← nbf 未到
├── InvalidAudienceError         ← aud 不匹配
├── InvalidIssuerError           ← iss 不匹配
├── MissingRequiredClaimError    ← require 里要求的 claim 缺失
└── InvalidKeyError              ← 密钥类型不对（如拿 PEM 当 HMAC 密钥）
```

**注意**：`ExpiredSignatureError` 继承自 `InvalidSignatureError`，而
`InvalidSignatureError` 继承自 `InvalidTokenError`。所以捕获顺序要从具体到宽泛。
对外返回时**统一返回 401，不要泄露具体是"签名错"还是"过期"**，
否则等于给攻击者送情报。

### 3.3 算法对比与选型

| 算法 | 类型 | 密钥 | 签名长度 | 速度 | 适用场景 |
|---|---|---|---|---|---|
| `HS256` | HMAC-SHA256 | 共享密钥 | 32 B | ⚡ 最快 | 单体应用、内部服务 |
| `RS256` | RSA-PKCS1v1.5 | 私钥签/公钥验 | 256 B | 慢（验证比签名快） | 微服务、开放平台 |
| `PS256` | RSA-PSS | 私钥签/公钥验 | 256 B | 慢 | RS256 的现代化替代，抗签名伪造 |
| `ES256` | ECDSA P-256 | 私钥签/公钥验 | 64 B | 快 | **现代首选**，token 短 |
| `EdDSA` | Ed25519 | 私钥签/公钥验 | 64 B | 最快 | 新系统首选，需较新库支持 |
| `none` | 无签名 | — | 0 B | — | ❌ **永远不要用** |

选型决策：

```
需要多方验证（第三方登录 / 微服务各自验签）？
   ├─ 是 → 用非对称：EdDSA > ES256 > PS256 > RS256
   └─ 否 → 单方自用，可以 HS256，但密钥必须 ≥32B 随机
```

### 3.4 密钥与生命周期管理清单

- [ ] 密钥用 `secrets.token_bytes(32)` 或 KMS 生成，**不写进代码/git**
- [ ] 配置走环境变量或密钥管理服务（Vault / AWS KMS / 阿里云 KMS）
- [ ] 支持**双密钥并存**：换钥时新旧同时可验，过渡期后再撤旧钥
- [ ] access token 短（5~30 分钟）+ refresh token 长（7~30 天，且可撤销）
- [ ] 用 `jti` + 服务端黑名单实现"主动登出"
- [ ] 定期审计：日志里绝不打完整 token（打前 8 位 + 哈希即可）
