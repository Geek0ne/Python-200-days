# Day 147 — 密码学基础：哈希、加盐与 HMAC

> 阶段：Phase 7 — 进阶与性能优化 · 主题：实战密码学基础
>
> 前置知识：Day 146（HTTPS/TLS 分析）中你已经见过"摘要算法"在数字签名/证书里的角色。今天我们系统地学习 Python 标准库 `hashlib` 与 `hmac`，并把它们用到文件完整性校验这个真实场景中。

---

## 一、概念解释

### 1.1 什么是哈希（Hash / 摘要 / Digest）

哈希函数是把**任意长度**的输入映射为**固定长度**输出的单向函数：

- **确定性**：同样的输入永远得到同样的输出。
- **单向性（不可逆）**：从摘要几乎不可能反推出原文。
- **抗碰撞性**：很难找到两个不同的输入拥有相同摘要。
- **雪崩效应**：输入改 1 个比特，输出约一半比特发生变化。

常见算法对比（Python `hashlib` 全部内置）：

| 算法 | 摘要长度 | 安全性 | 典型用途 |
|---|---|---|---|
| MD5 | 128 bit (16 字节) | ❌ 已被碰撞攻击攻破 | 仅用于非安全校验（如缓存 key） |
| SHA-1 | 160 bit | ❌ 2017 年被实际碰撞 | 遗留系统 |
| SHA-256 | 256 bit | ✅ 安全 | 通用场景默认选择 |
| SHA-512 | 512 bit | ✅ 安全 | 64 位平台大文件 |
| SHA-3 | 可变 | ✅ 安全 | 抗未来攻击的新标准 |
| BLAKE2 / BLAKE2b | 可变 | ✅ 安全且更快 | 高性能场景 |

> **为什么 MD5 还到处都是？** 历史惯性。但绝不能用于密码存储或安全校验——攻击者可以构造两个不同文件具有相同 MD5（碰撞攻击），从而"偷梁换柱"。

### 1.2 为什么"裸哈希存密码"是灾难

很多人第一次写登录系统时这样存密码：

```python
hashlib.sha256(password.encode()).hexdigest()  # ❌ 错误做法
```

问题有三层：

1. **彩虹表攻击**：攻击者提前把常见密码的 SHA-256 全部算好存表，拖库后直接反查。`123456` 的 SHA-256 在任何机器上都是一样的。
2. **字典/暴力破解极快**：SHA-256 设计目标是"快"，现代 GPU 每秒可算数十亿次。攻击者拿到数据库后可以离线高速爆破。
3. **相同密码摘要相同**：一眼能看出哪些用户用了同一个密码。

正确做法：**加盐 + 慢哈希**（见 1.3 与 1.5）。

### 1.3 加盐哈希（Salt）

**盐（salt）** 是一段随机数据，与密码拼接后再哈希：

```python
salt = os.urandom(16)                    # 每个用户独立的随机盐
digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100_000)
```

为什么加盐能救命：

- 相同密码 + 不同盐 ⇒ 不同摘要 ⇒ 彩虹表全部失效（表必须为每个盐重新生成，代价爆炸）。
- 盐不需要保密，可以明文存进数据库（通常 `salt$digest` 拼一起）。
- **每次设置密码都要生成新盐**，绝不能复用全局固定盐。

### 1.4 HMAC（基于哈希的消息认证码）

哈希只能保证"内容没被意外篡改"（完整性），**不能证明来源可信**：攻击者可以连同哈希一起篡改。

HMAC = Hash + **密钥**，公式：

```
HMAC(K, m) = H((K' ^ opad) || H((K' ^ ipad) || m))
```

- 只有持有同一个密钥 `K` 的人才能算出/验证该摘要 → **完整性 + 认证**。
- 内外两层哈希结构是精心设计的，能抵御长度扩展攻击（length extension attack）——这正是"直接 `sha256(key + msg)`"不安全的原因。
- 典型用途：API 签名（微信/支付宝支付回调）、WebSocket JWT 签名、TLS 记录层 MAC。

### 1.5 密码哈希的正确姿势：慢哈希

安全存密码的关键不是"更复杂的算法"，而是"**故意慢**"：

| 方案 | 特点 | Python 位置 |
|---|---|---|
| PBKDF2 | 标准库内置，迭代次数可调 | `hashlib.pbkdf2_hmac()` |
| bcrypt | 自带盐、费用因子 | 第三方 `bcrypt` 库 |
| scrypt / argon2 | 内存困难型，抗 GPU | 第三方库 |

`hashlib.pbkdf2_hmac('sha256', pwd, salt, 600_000)`：OWASP 2023 建议 PBKDF2-HMAC-SHA256 至少 60 万次迭代——每次校验约几百毫秒，用户无感，爆破者绝望。

---

## 二、原理深入

### 2.1 Merkle–Damgård 结构（MD5/SHA-1/SHA-2 的共同骨架）

```
消息 M (任意长度)
   │
   ▼
┌──────────────┐  填充 padding：先补 1 位 '1'，
│ 分块处理      │  再补 0 直到长度 ≡ 56 (mod 64)，
│ 512 bit/块   │  最后 8 字节存原始长度（长度填充）
└──────┬───────┘
       ▼
  IV(初始向量) ──►┌────────┐   ┌────────┐   ┌────────┐
                 │ 压缩函数 │──►│ 压缩函数 │──►│ 压缩函数 │──► 摘要
        块1 ────►│  f()   │   │  f()   │   │  f()   │
                 └────────┘   └────────┘   └────────┘
                    块1          块2          块N
```

要点：

- **为什么补长度**：防止"不同长度的消息通过填充后变成同一块序列"造成碰撞。
- **长度扩展攻击**：由于 `摘要 = 压缩(IV, M)` 的链式结构，知道 `H(M)` 的输出就等于知道中间状态，攻击者无需知道 M 就能算 `H(M || padding || extra)`。HMAC 的内外双 hash 结构正好切断这条路。

### 2.2 HMAC 内部结构

```
                 message m
                     │
        key K ──► K' = H(K) 若 K 超过块长则先哈希，不足补零到块长
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
   K' ^ ipad (0x36…)     K' ^ opad (0x5c…)
          │                     │
          ▼                     ▼
   ┌─────────────┐       ┌─────────────┐
   │ 内层 SHA256 │◄──────│ 外层 SHA256 │──► HMAC 输出
   └─────────────┘  digest└─────────────┘
        ▲
        └── (K' ^ ipad) || m 作为内层输入
```

- **ipad/opad 是固定常数**，任何实现都一致，保证跨语言互认。
- 双层结构在证明上把 HMAC 的安全性归约到底层哈希函数的 PRF（伪随机函数）性质，即使底层哈希有轻微缺陷也稳。

### 2.3 为什么 PBKDF2 "慢得恰到好处"

```
PBKDF2(pwd, salt, iter, n):
    U1 = HMAC(pwd, salt || 0x00000001)
    U2 = HMAC(pwd, U1)
    ...
    Uiter = HMAC(pwd, U_{iter-1})
    return U2 ^ U3 ^ ... ^ Uiter 的前 n 字节   # 全部异或
```

- 每次迭代必须**串行**依赖上一次结果，无法并行加速单次登录校验。
- 攻击者想爆破 1 亿个候选密码？每个候选都要跑 60 万轮 HMAC —— 硬件成本从"秒级"变成"千年级"。
- 迭代次数是一个**随硬件进化不断调大**的参数，这也是它比"写死的复杂算法"长寿的原因。

### 2.4 大文件哈希：流式处理

一次性 `f.read()` 会把几 GB 文件全灌进内存。正确姿势是分块喂给哈希对象——`hashlib` 内部维护增量状态，内存占用恒定：

```python
h = hashlib.sha256()
with open(path, 'rb') as f:
    for chunk in iter(lambda: f.read(1 << 20), b''):  # 1 MiB 块
        h.update(chunk)
```

`update()` 可以任意次调用，结果等价于一次性喂入全部字节——这正是 Merkle–Damgård 增量结构带来的天然能力。

---

## 三、API 速查

### hashlib

```python
import hashlib, hmac, os, secrets

hashlib.new('sha256')            # 按名字创建（兼容未知算法）
hashlib.sha256(b'data')          # 常用算法直接是属性
h = hashlib.sha256(); h.update(b'a'); h.update(b'b')
h.digest()                       # → bytes（16/32/64 字节）
h.hexdigest()                    # → 'a3f5...'（小写十六进制）
h.name; h.digest_size; h.block_size

hashlib.pbkdf2_hmac('sha256', pwd, salt, 600_000, dklen=32)
hashlib.blake2b(b'data', digest_size=32, key=b'k')  # 原生带 key 的 BLAKE2

hashlib.file_digest(open('f','rb'), 'sha256')        # Python 3.11+ 高速文件哈希
hashlib.algorithms_available; hashlib.algorithms_guaranteed
```

### hmac

```python
hmac.new(key, msg, hashlib.sha256).hexdigest()
hmac.compare_digest(a, b)   # 恒定时间比较，防时序攻击（永远用它比较 MAC/口令）
hmac.digest(key, msg, 'sha256')  # 3.7+ 一步出结果，最快
```

### secrets（顺带记住）

```python
secrets.token_bytes(16); secrets.token_hex(16); secrets.token_urlsafe(16)
secrets.compare_digest(a, b)
```

> **避坑**：校验 MAC/口令时**永远用 `hmac.compare_digest`**，不要用 `==`。`==` 在第一个不匹配字节处提前返回，攻击者可通过测量响应时间逐字节猜出正确值（时序攻击）。

---

## 四、图解

### 文件完整性校验全流程

```
 发布方（软件作者）                        验证方（下载用户）
 ─────────────────────                    ─────────────────────
 app-v2.1.tar.gz                          1. 下载 app-v2.1.tar.gz
      │                                   2. 下载 SHA256SUMS（含摘要+文件名）
      │ sha256sum                         3. 本地重新计算摘要
      ▼                                        │
 SHA256SUMS 文件 ────（发布到官网/邮件列表）──►  ▼
                                           4. compare_digest 比对
                                                │
                                     ┌──────────┴──────────┐
                                     ▼                     ▼
                                  相等 ✅ 放心安装      不等 ❌ 文件被篡改/损坏
```

### 加盐哈希存储结构（数据库一行）

```
┌────────────┬────────────────────────────────────────────────┐
│ username   │ password_hash                                  │
├────────────┼────────────────────────────────────────────────┤
│ alice      │ pbkdf2$sha256$600000$<salt_hex>$<digest_hex>   │
└────────────┴────────────────────────────────────────────────┘
     ▲              ▲        ▲       ▲           ▲
   明文用户名     算法标识  迭代次数   随机盐     慢哈希结果
   （可公开）    （用于未来升级换算法，盐和迭代次数随行存储）
```

---

## 五、实战代码案例

**文件完整性校验工具**（完整可运行版本见 `code/03-file-integrity.py`）：

```python
import hashlib, sys, hmac

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk), b''):
            h.update(block)
    return h.hexdigest()

def verify(path, expected_hex):
    return hmac.compare_digest(sha256_file(path), expected_hex.lower())

if __name__ == '__main__':
    print(verify(sys.argv[1], sys.argv[2]))
```

**密码哈希存储器**（见 `code/02-password-hashing.py`）：

```python
import hashlib, os, hmac

ITER = 600_000

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITER)
    return f"pbkdf2$sha256${ITER}${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    _, algo, it, salt_hex, digest_hex = stored.split('$')
    calc = hashlib.pbkdf2_hmac(algo, password.encode(), bytes.fromhex(salt_hex), int(it))
    return hmac.compare_digest(calc.hex(), digest_hex)
```

---

## 六、思考题

1. 为什么"盐不需要保密，但必须唯一且随机"？如果全站共用一个固定盐，攻击者需要为每个盐重新生成彩虹表吗？
2. 既然 SHA-256 比 PBKDF2 快得多，为什么存密码反而要选"慢"的 PBKDF2？这两个场景对哈希函数的诉求差在哪？（提示：一个防篡改、一个防爆破）
3. `sha256(secret_key + message)` 看起来也有"密钥"，为什么它不等于 HMAC，会被什么攻击打穿？
4. 如果攻击者能测量你服务器的响应时间，用 `==` 比较密码摘要有什么风险？`hmac.compare_digest` 是如何消除这个风险的？
5. 你要给一个 10 GB 的镜像文件做校验：为什么必须用流式 `update()` 分块读取？如果中途网络断了重传，能否从断点继续计算哈希？（想一想 Merkle–Damgård 的链式结构意味着什么）

---

## 参考

- [hashlib 官方文档](https://docs.python.org/zh-cn/3/library/hashlib.html)
- [hmac 官方文档](https://docs.python.org/zh-cn/3/library/hmac.html)
- RFC 2104（HMAC）、RFC 8018（PBKDF2）
- OWASP Password Storage Cheat Sheet
