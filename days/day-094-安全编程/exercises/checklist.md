# Day 094 — 安全编程 · 练习清单

## ✅ 今日完成清单

- [ ] 理解常见安全漏洞（SQL 注入、命令注入、XSS）
- [ ] 掌握输入验证的最佳实践
- [ ] 学习哈希算法（MD5/SHA-256/bcrypt）的使用场景
- [ ] 理解对称加密与非对称加密的区别
- [ ] 实现简单的 JWT 认证系统
- [ ] 了解安全编码的最佳实践

---

## 📝 练习题

### 基础题

**1. 输入验证器增强**

在 01-input-validation.py 的 InputValidator 类中添加：
- 手机号验证（中国大陆手机号格式）
- URL 验证（合法的 HTTP/HTTPS URL）
- IP 地址验证（IPv4 格式）

```python
# 测试用例
validator = InputValidator()
assert validator.validate_phone("13812345678") == (True, "")
assert validator.validate_phone("12345") == (False, "手机号格式不正确")
assert validator.validate_url("https://example.com") == (True, "")
assert validator.validate_ip("192.168.1.1") == (True, "")
```

**2. 密码强度评估器**

编写一个密码强度评估器，返回分数（0-100）和建议：
- 长度（25分）
- 字符多样性（25分）
- 无常见弱密码（25分）
- 无连续重复字符（25分）

```python
score, suggestions = evaluate_password("MyP@ss123")
# score: 85
# suggestions: ["避免使用常见密码模式"]
```

**3. HMAC 签名验证**

实现一个简单的 API 签名验证中间件：
- 客户端在请求头中携带 `X-Signature` 签名
- 签名 = HMAC-SHA256(request_body + timestamp, api_key)
- 服务器验证签名和时间戳（5分钟内有效）

### 进阶题

**4. 密码策略管理器**

实现一个可配置的密码策略管理器：
- 支持自定义密码规则（长度、字符类型等）
- 支持密码历史检查（不允许重复使用最近 5 次的密码）
- 支持密码过期策略
- 记录密码修改历史

**5. 安全的文件加密工具**

使用 AES-GCM 实现一个文件加密工具：
- 支持加密任意文件
- 使用 PBKDF2 从密码派生密钥
- 加密文件包含元数据（原文件名、时间戳）
- 支持解密恢复原文件

```bash
# 使用方式
python encrypt.py secret.txt  # 生成 secret.txt.enc
python decrypt.py secret.txt.enc  # 恢复 secret.txt
```

**6. JWT Token 刷新机制**

实现双 Token 机制：
- Access Token（短有效期，如 15 分钟）
- Refresh Token（长有效期，如 7 天）
- Access Token 过期时，用 Refresh Token 获取新的 Access Token
- Refresh Token 使用后失效（Rotation）

---

## 🔍 检查点

完成后，确认你能回答以下问题：

1. 为什么不应该用 MD5 存储密码？bcrypt 的优势是什么？
2. 对称加密和非对称加密分别适合什么场景？
3. JWT Token 由哪三部分组成？每部分的作用是什么？
4. 如何防止 JWT Token 被盗用后在其他设备使用？
5. 什么是时序攻击？`hmac.compare_digest` 如何防御？
