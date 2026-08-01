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
2. **JWT Token 过期后如何实现无感刷新？** 提示：双 Token 机制
3. **如何防止 JWT 被盗用？** 提示：考虑 HTTPS、HttpOnly Cookie、Token 绑定
4. **对称加密和非对称加密分别适合什么场景？为什么？**
5. **如何设计一个安全的密码重置流程？** 提示：考虑时序、一次性 Token、通知用户

---

## 📚 扩展阅读

- [Python hashlib 官方文档](https://docs.python.org/3/library/hashlib.html)
- [cryptography 库文档](https://cryptography.io/en/latest/)
- [OWASP Top 10 安全风险](https://owasp.org/www-project-top-ten/)
- [JWT 规范 (RFC 7519)](https://tools.ietf.org/html/rfc7519)
