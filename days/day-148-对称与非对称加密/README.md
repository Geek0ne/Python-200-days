# Day 148 — 对称与非对称加密：AES、RSA 与混合加密

> 阶段：Phase 7 — 进阶与性能优化 · 主题：实战密码学
>
> 前置知识：Day 147 学了哈希与 HMAC（解决**完整性 / 不可否认**）。今天进入另一个方向——**机密性（Confidentiality）**：数据要在不可信信道上传输，怎么保证别人看不到。理解了 AES / RSA / 混合加密，你才看得懂 TLS、VPN、加密聊天软件、JWT 签名背后到底发生了什么。

---

## 一、概念解释

### 1.1 对称加密（Symmetric Encryption）

**定义**：加密和解密使用**同一把密钥**的加密方式。

```
明文 + 密钥 K ──[加密]──► 密文 ──[解密]──► 明文（同一个密钥 K）
```

代表算法：

| 算法 | 密钥长度 | 分组长度 | 状态 | 说明 |
|---|---|---|---|---|
| DES | 56 bit | 64 bit | ❌ 已淘汰 | 密钥太短，暴力可破 |
| 3DES | 112/168 bit | 64 bit | ⚠️ 逐步淘汰 | 性能差、Sweet32 攻击 |
| **AES** | 128/192/256 bit | **128 bit** | ✅ 主流 | 硬件加速，业界标准 |
| ChaCha20 | 256 bit | 流式 | ✅ 主流 | 无 AES 硬件时的首选（移动端） |
| SM4 | 128 bit | 128 bit | ✅ 国密 | 国内合规场景 |

**为什么它快？** 加密算法本身只做查表、移位、异或这类按位运算，且可以
硬件指令加速（x86 的 AES-NI）。实测 AES-GCM 在现代 CPU 上可达 **1~5 GB/s**。

**它解决不了的问题**：密钥分发。A 和 B 隔着不可信网络，怎么让两人拥有
同一把密钥？如果先能安全传密钥，那干脆用它传数据就好了——这就是死循环。
非对称加密负责打破这个死循环。

### 1.2 非对称加密（Asymmetric / Public-Key Encryption）

**定义**：使用**一对**数学关联的密钥——公开的公钥（public key）和保密的
私钥（private key）。公钥加密的数据，只有对应私钥能解；私钥签名的数据，
任何持有公钥的人都能验证。

| 算法 | 安全基础 | 典型密钥长度 | 特点 |
|---|---|---|---|
| RSA | 大整数分解难题 | 2048 / 3072 / 4096 bit | 最通用，兼容性好，慢 |
| ECC (ECDSA/ECDH) | 椭圆曲线离散对数 | 256 bit | 同等安全下密钥更短、更快 |
| Ed25519 | 爱德华兹曲线 | 256 bit | 现代签名首选，快且抗侧信道 |
| DH / ECDHE | 离散对数 | — | 用于**密钥协商**，不用于加密数据 |

**为什么它慢？** 运算对象是上千位的大整数，核心操作是模幂（`m^e mod n`），
大量大数乘法和取模，比 AES 的按位操作慢几个数量级（通常几十到上千倍）。

**两大用途必须分清**：

```
① 加密（保证机密性）:  公钥加密 ──► 私钥解密
   目标：任何人都能发消息给我，但只有我能看

② 签名（保证身份+完整性）:  私钥签名 ──► 公钥验签
   目标：证明"这条消息确实来自私钥持有者"，且未被篡改
```

> 常见误区："用私钥加密、公钥解密" 这种说法容易误导。正确表述是
> **签名 = 用私钥对消息摘要做运算，公钥可以验证**。因为公钥是公开的，
> 用"私钥加密"得到的密文谁都能解开，根本谈不上保密。

### 1.3 混合加密（Hybrid Encryption）

工业界从不单用 RSA 加密业务数据，而是**混合**：

```
① 随机生成一次性对称密钥 K（会话密钥，如 32 字节）
② 用接收方公钥加密 K            → 解决"密钥分发"（非对称的强项）
③ 用 K 加密真正的数据（AES-GCM）→ 解决"高速大批量"（对称的强项）
④ 接收方用私钥解出 K，再解密数据
```

TLS/HTTPS、PGP、Signal、VPN 全是这个套路。**记住一句话：
非对称加密只用来搬运密钥和做签名，真正的数据永远交给对称加密。**

### 1.4 三个概念别混淆：编码 / 哈希 / 加密

| 名称 | 可逆？ | 有密钥？ | 目的 |
|---|---|---|---|
| Base64 编码 | ✅ 可逆 | ❌ 无 | 把二进制塞进文本协议，**不是安全措施** |
| 哈希（SHA-256） | ❌ 不可逆 | ❌ 无 | 完整性校验、指纹 |
| HMAC | ❌ 不可逆 | ✅ 有 | 带密钥的完整性/认证（Day 147） |
| 对称加密 | ✅ 可逆 | ✅ 有 | 机密性 |
| 非对称加密 | ✅ 可逆 | ✅ 有（一对） | 机密性 + 密钥分发 |
| 数字签名 | — | ✅ 有 | 身份认证 + 完整性 + 不可否认 |

> ⚠️ 把 Base64 当加密用是新手最常见的笑话：
> `base64.b64encode(b"password")` 的结果 `cGFzc3dvcmQ=` 任何人都能解。

### 1.5 分组密码的五个关键术语

- **分组（Block）**：AES 一次处理的固定长度，恒为 128 bit（16 字节）。
- **密钥长度**：AES-128/192/256，**只影响轮数**（10/12/14 轮），不改分组大小。
- **模式（Mode）**：如何把多个分组串起来加密，决定安全性（见 2.2）。
- **IV / nonce**：初始向量 / 一次性数字，保证"同样的明文每次加密结果不同"。
- **填充（Padding）**：明文长度不是分组整数倍时补齐到整数倍（见 2.3）。

**为什么 AES 分组是 128 bit 不变？** 因为 `SubBytes/ShiftRows/MixColumns` 这一套
"状态矩阵"运算天然是 16 字节的结构（4×4 字节矩阵）；加大分组会让安全性
提升有限而性能骤降，所以设计者选择用更多轮数（更长的密钥）来提升强度。

## 二、原理深入

### 2.1 AES 内部结构（为什么它安全且可逆）

AES 把 16 字节明文排成 4×4 的"状态矩阵"，每轮做四个变换：

```mermaid
flowchart TB
    P[明文 16 字节] --> AK0[AddRoundKey: 与第0轮子密钥异或]
    AK0 --> R{重复 9/11/13 轮}
    R --> SB[SubBytes: 逐字节 S盒非线性替换]
    SB --> SR[ShiftRows: 每行循环左移 0/1/2/3]
    SR --> MC[MixColumns: 列混淆 4x4 矩阵乘法]
    MC --> AK[AddRoundKey: 异或本轮子密钥]
    AK --> R
    R --> F[最后一轮: SubBytes/ShiftRows/AddRoundKey 无 MixColumns]
    F --> C[密文 16 字节]
    KS[密钥扩展 Key Schedule] -.子密钥.-> AK0
    KS -.子密钥.-> AK
```

四个变换各自的作用（**为什么是这四个**）：

1. **SubBytes**：唯一的**非线性**步骤（S 盒）。没有它，整个密码就是线性
   方程组，能被直接解出密钥。它提供"混淆（confusion）"。
2. **ShiftRows**：把字节在列之间打散，保证一个字节的影响扩散到多列。
3. **MixColumns**：列内线性混合，提供"扩散（diffusion）"——一位变化迅速
   影响整块。
4. **AddRoundKey**：把密钥真正"掺"进去，否则算法与密钥无关。

**密钥扩展**：从 128/192/256 bit 主密钥推导出每轮一把子密钥。这也是为什么
密钥越长为轮数越多（10/12/14 轮），而不是改分组长度。

**AES 的逆运算**正是把上述步骤逆序 + 用逆 S 盒 / 逆 ShiftRows / 逆 MixColumns，
所以能解密（这是"对称"的底层保证）。

### 2.2 分组模式：ECB / CBC / CTR / GCM

分组密码只能处理固定 16 字节，现实数据远超 16 字节，于是有了"模式"。

**ECB（Electronic Codebook）— ❌ 千万不要用**

```
独立加密每个分组:  C_i = AES(P_i)
```
问题：相同明文分组 → 相同密文分组。加密一张位图后仍能看清轮廓（"ECB 企鹅"）。
**它泄露的是数据的结构，而这往往就是最敏感的信息。**

**CBC（Cipher Block Chaining）— ⚠️ 可用但需谨慎**

```
C_1 = AES(P_1 XOR IV)
C_i = AES(P_i XOR C_{i-1})
```
每个明文分组先与**前一个密文分组**异或，破坏了"相同明文→相同密文"。
要求：IV 必须随机且**不可预测**，且每次加密换新 IV。
缺点：**只保证机密性，不保证完整性**（可被 bit-flipping 篡改），且不能并行加密。

**CTR（Counter）— ✅ 流式，可并行**

```
C_i = P_i XOR AES(nonce || counter_i)
```
把分组密码当**流密码**用：加密一串计数器，再与明文异或。优点：可并行、
可随机访问、无填充。缺点：**nonce+counter 组合绝不能重复**，且同样不带完整性。

**GCM（Galois/Counter Mode）— ✅ 现代默认**

```
GCM = CTR 模式加密  +  GHASH 认证标签
```
它是 **AEAD（Authenticated Encryption with Associated Data）**：
一次运算同时给出机密性 + 完整性，还能附带 **AAD**（不加密但受保护的元数据）。
只要 tag 校验不过，解密直接失败——**不会把被篡改的数据交给你**。
这就是 TLS 1.3 里只剩 AES-GCM / ChaCha20-Poly1305 的原因。

| 模式 | 机密性 | 完整性 | 可并行 | 推荐度 |
|---|---|---|---|---|
| ECB | ❌ 泄露结构 | ❌ | ✅ | 🚫 禁止 |
| CBC | ✅ | ❌ | ❌ | ⚠️ 仅配合 HMAC（Encrypt-then-MAC） |
| CTR | ✅ | ❌ | ✅ | ⚠️ 需自行加 MAC |
| **GCM** | ✅ | ✅ | ✅ | ✅ 推荐 |
| ChaCha20-Poly1305 | ✅ | ✅ | ✅ | ✅ 无 AES 硬件时推荐 |

### 2.3 填充（Padding）与 PKCS#7

CBC 要求明文长度是 16 的整数倍。PKCS#7 规则：缺 n 字节就补 n 个值为 n
的字节；若刚好整除，则补满一整块 16 个 `0x10`。

```
"HELLO"(5字节) → 补 11 个 0x0B  → 16 字节
16 字节整块     → 补 16 个 0x10 → 32 字节（必须补！否则无法区分"已去掉填充"）
```

> **Padding Oracle 攻击**：如果服务端对"填充错误"和"内容错误"返回不同提示，
> 攻击者可以逐字节解出明文。这就是为什么 CBC 时代要格外小心，也是 GCM 这种
> AEAD 更安全的原因之一。

### 2.4 RSA 的数学原理

```
密钥生成:
  选两个大素数 p, q（2048 bit 密钥 ⇒ p、q 各约 1024 bit）
  n = p * q                       （公开的"模数"）
  φ(n) = (p-1)(q-1)
  选 e 与 φ(n) 互素（惯例 65537）
  求 d 使 e * d ≡ 1 (mod φ(n))
  公钥 = (n, e)     私钥 = (n, d)

加密: c = m^e mod n
解密: m = c^d mod n
```

**为什么安全**：攻击者知道 n 和 e，想求 d 必须先分解 n 得到 p、q。而
2048-bit 的大整数分解在现有算力下不可行。**为什么 e 常取 65537**：
它是 `2^16+1`，二进制只有两个 1，模幂运算快，且足够大以避免小指数攻击。

**为什么"教科书 RSA"不安全**：

- 确定性：相同明文 + 相同公钥 → 相同密文（可被枚举比对）。
- 小消息可开方：若 `m^e < n`，则 `c = m^e`，直接对 c 开 e 次方即得 m。
- 可乘性：`E(m1)*E(m2) = E(m1*m2)`，攻击者可构造定向密文。

**填充救场**：OAEP（加密用）在明文前掺入随机数并做 Feistel 变换，让同一明文
每次密文都不同；PSS（签名用）用随机盐保证签名不可伪造、不可复用。

### 2.5 密钥协商与前向保密（Forward Secrecy）

RSA 封装密钥有个隐患：**服务器私钥一旦泄露，攻击者录下的历史流量全被解开**。

Diffie-Hellman（DH）解决这个：

```mermaid
sequenceDiagram
    participant A as 客户端
    participant B as 服务器
    A->>B: A = g^a mod p （公开）
    B->>A: B = g^b mod p （公开）
    Note over A: K = B^a mod p
    Note over B: K = A^b mod p
    Note over A,B: 双方算出同一个 K，窃听者只知道 A、B，算不出 K（离散对数难题）
```

现代 TLS 用 **ECDHE**（椭圆曲线临时 DH）：每次连接生成**一次性**密钥对，
用完即弃。这样即使长期私钥泄露，也解不开历史会话——即"前向保密"。
Day 149 学的 JWT 与 Day 148 的这套密码学知识，是同一批底层工具的两种应用。

### 2.6 为什么非对称加密慢：数量级对比

| 操作 | 相对速度 | 原因 |
|---|---|---|
| AES-256-GCM 加解密 | 1× (基准) | 按位运算 + 硬件加速 |
| RSA-2048 加密（公钥运算） | ~1000× 慢 | 大数模幂，e=65537 已优化 |
| RSA-2048 解密（私钥运算） | ~3000× 慢 | d 是 2048 bit，全长度模幂 |
| ECC-256 运算 | ~100× 慢 | 椭圆曲线点乘 |

正是这个数量级差，逼出了混合加密这一必然方案。

## 三、常见陷阱与避坑指南

### 3.1 用 ECB 模式加密（结构性泄露）

```python
# ❌ 错误：ECB 会让相同明文块产生相同密文块
cipher = Cipher(algorithms.AES(key), modes.ECB())
```

**后果**：加密图片能看出轮廓，加密数据库字段能看出哪些行值相同。
**正确做法**：用 `AESGCM`（推荐）或 CBC + 随机 IV。

### 3.2 IV / nonce 重用（最致命的一类错误）

- **CBC 的 IV 可预测**：固定 IV 或"时间戳当 IV"，会让相同明文前缀产生相同
  密文前缀，泄露信息（BEAST 攻击）。
- **GCM 的 nonce 重用是毁灭性的**：同一个 (key, nonce) 加密两条消息，
  两条密文异或 = 两条明文异或（直接泄露明文关系），更严重的是可以恢复出
  **认证密钥 H**，从而伪造任意消息的 tag。

```python
# ❌ 错误：nonce 写死 / 每次用同一个
aesgcm.encrypt(b"\x00" * 12, data, None)
# ✅ 正确：每次加密都生成新 nonce
nonce = os.urandom(12)
```

**纪律**：自己管 nonce 时用随机 12 字节（碰撞概率极低）或严格单调计数器；
用 `AESGCM` 时把 nonce 与密文一起存储/传输。

### 3.3 用"教科书 RSA"（无填充）

```python
# ❌ 错误：确定性加密 + 可乘性 + 小消息可开方
c = pow(int.from_bytes(msg, "big"), e, n)
# ✅ 正确：必须带 OAEP 填充
public_key.encrypt(msg, padding.OAEP(mgf=..., algorithm=SHA256(), label=None))
```

### 3.4 拿 RSA 加密大文件 / 超长消息

2048-bit 密钥 + SHA-256 的 OAEP 上限约 **190 字节**。超了会直接报
`ValueError: Encryption failed`。正确姿势是用混合加密（见 `code/03`）。

### 3.5 用 `==` 比较密钥、tag、HMAC

字符串/字节比较会在第一个不同字节处提前返回，攻击者可据耗时逐字节猜测
（**时序攻击**）。必须用常数时间比较：

```python
import hmac
hmac.compare_digest(a, b)   # ✅
a == b                      # ❌ 用于安全比较
```

### 3.6 硬编码密钥 / 把密钥提交进 Git

```python
KEY = b"1234567890123456"   # ❌ 会被 git 永远记住
```
正确做法：密钥放环境变量、KMS、Vault 或密钥管理服务；用 `.gitignore`
排除密钥文件；一旦泄露必须**轮换密钥**（历史提交无法真正删除）。

### 3.7 自己发明加密方案 / 自造填充

"我用 AES 加密，再把结果倒序一下，再加个盐，肯定更安全" —— 这类
**自制密码学（Roll Your Own Crypto）** 是安全事故高发区。用经过审计的
库与标准组合：`AESGCM`、`ChaCha20Poly1305`、`Fernet`。

### 3.8 把编码当加密

`base64`、`hex`、`urlencode` 全部可逆且无密钥，**不能保护任何机密**。
它们只用于让二进制适配文本协议。

### 3.9 加密了却忘了认证（Encrypt-then-MAC 顺序）

CBC 加密不防篡改。若必须用 CBC，应"先加密、后对密文做 HMAC"（
Encrypt-then-MAC），并**先验 MAC 再解密**。顺序颠倒会引入 Padding Oracle。
GCM 已经内置了这个顺序，所以优先选 GCM。

### 3.10 忽略随机源质量

用 `random` 模块生成密钥/IV 是灾难（伪随机，种子可预测）。
**密钥、IV、盐一律用 `os.urandom()` 或 `secrets` 模块。**

```python
import secrets
key = secrets.token_bytes(32)   # ✅ 密码学安全
```

## 四、定义与使用方法（API 速查表）

> 本节所有 API 来自 `cryptography` 库（`pip install cryptography`），它是
> Python 生态事实标准的密码学库，底层用 OpenSSL/Rust 实现，**不要自己
> 用纯 Python 手写 AES/RSA**。

### 4.1 对称加密 AESGCM

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# 生成密钥
key = AESGCM.generate_key(bit_length=256)     # 返回 32 字节 bytes
# 或 key = os.urandom(32)

aes = AESGCM(key)
nonce = os.urandom(12)                        # 12 字节，每次加密都要新
ct = aes.encrypt(nonce, plaintext_bytes, aad) # aad 可为 None 或 bytes
pt = aes.decrypt(nonce, ct, aad)              # 篡改/密钥错 → InvalidTag
```

| 方法 | 参数 | 返回 | 说明 |
|---|---|---|---|
| `AESGCM.generate_key(bit_length)` | 128/192/256 | `bytes` | 生成随机密钥 |
| `AESGCM(key)` | 32/24/16 字节 | 实例 | key 长度不对会报错 |
| `.encrypt(nonce, data, aad)` | nonce 8~128B（推荐 12） | `bytes` | 输出 = 密文 + 16B tag |
| `.decrypt(nonce, data, aad)` | 同上 | `bytes` | 失败抛 `InvalidTag` |

### 4.2 ChaCha20-Poly1305（无 AES 硬件时的替代）

```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
chacha = ChaCha20Poly1305(ChaCha20Poly1305.generate_key())
ct = chacha.encrypt(os.urandom(12), b"data", b"aad")
```

### 4.3 RSA 密钥生成与序列化

```python
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 导出 PEM
pem_pub = public_key.public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo)

pem_priv = private_key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.BestAvailableEncryption(b"passphrase"))   # 口令保护

# 从 PEM 加载
pub = serialization.load_pem_public_key(pem_pub)
priv = serialization.load_pem_private_key(pem_priv, password=b"passphrase")
```

### 4.4 RSA 加密（OAEP）与签名（PSS）

```python
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

OAEP = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                    algorithm=hashes.SHA256(), label=None)
PSS  = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                   salt_length=padding.PSS.MAX_LENGTH)

ct = public_key.encrypt(b"short msg", OAEP)      # ≤ 190 字节 (2048+SHA256)
pt = private_key.decrypt(ct, OAEP)

sig = private_key.sign(b"doc", PSS, hashes.SHA256())      # 私钥签名
public_key.verify(sig, b"doc", PSS, hashes.SHA256())      # 公钥验签，失败抛 InvalidSignature
```

### 4.5 常用填充别名

```python
from cryptography.hazmat.primitives import padding as sym_padding
padder = sym_padding.PKCS7(128).padder()     # 128 bit = 16 字节分组
```

### 4.6 选型速查

| 需求 | 推荐 API |
|---|---|
| 加密任意数据（同时要完整性） | `AESGCM` / `ChaCha20Poly1305` |
| 加密会话密钥 / 短消息 | `RSA-OAEP` 或 ECIES |
| 数字签名 | `RSA-PSS`（兼容） / `Ed25519`（现代） |
| 密钥协商 | `ECDH` / `X25519` |
| 密码存储 | `pbkdf2_hmac` / `scrypt` / Argon2（Day 147） |
| 完整性校验（无密钥） | `hashlib.sha256`（Day 147） |

### 4.7 官方文档入口

- `https://cryptography.io/en/latest/hazmat/primitives/`
- 选模式时先看 "Authenticated encryption" 章节

---

## 五、图解（Mermaid / ASCII）

### 5.1 两种加密的密钥流向

```mermaid
flowchart LR
    subgraph SYM[对称加密 AES]
        K1[同一把密钥 K] --> E1[加密] --> C1[密文]
        K1 --> D1[解密] --> P1[明文]
    end
    subgraph ASYM[非对称加密 RSA]
        PU[公钥 - 可公开] --> E2[加密] --> C2[密文]
        PR[私钥 - 保密] --> D2[解密] --> P2[明文]
    end
```

### 5.2 混合加密时序

```mermaid
sequenceDiagram
    participant C as 客户端
    participant S as 服务器
    C->>C: 生成一次性会话密钥 K
    C->>S: RSA_OAEP(服务器公钥, K)
    C->>S: AES_GCM(K, 业务数据)
    S->>S: 私钥解出 K → 解密数据
    S-->>C: 后续通信都走 AES(K)
    Note over C,S: RSA 只搬 32 字节密钥，数据全走 AES
```

### 5.3 AEAD 密文结构

```
 nonce(12B)      ciphertext(与明文等长)         tag(16B)
┌──────────┬───────────────────────────────┬──────────────┐
│  随机数   │         加密后的数据           │  认证标签     │
└──────────┴───────────────────────────────┴──────────────┘
     ▲                      ▲                       ▲
  可公开传输          AAD 参与认证但不加密      篡改任一字节
                                             → tag 校验失败
```

更完整的图解（ECB 对比、RSA 数学直觉、选型决策树）见
[`diagrams/README.md`](diagrams/README.md)。

## 六、实战代码案例

本日三个可运行示例位于 `code/`，逐层递进（每个文件都能直接
`python3 xxx.py` 运行，需要 `pip install cryptography`）：

| 文件 | 类型 | 内容 |
|---|---|---|
| `01-aes-gcm-basics.py` | 基础用法 | AES-256-GCM 加解密、AAD 认证、篡改检测、nonce 重用演示 |
| `02-rsa-asymmetric.py` | 进阶 / 避坑 | RSA 密钥对生成与 PEM 序列化、OAEP 加解密、长度上限、PSS 签名验签 |
| `03-hybrid-secure-channel.py` | 实战 | 混合加密安全通信工具：客户端/服务器类、密钥封装、签名、篡改与伪造攻击演示 |

### 6.1 `01` — 基础：把一次加密做对

演示了正确姿势的完整闭环：`os.urandom(12)` 生成 nonce → `AESGCM.encrypt`
→ 传输 `(nonce, 密文)` → `AESGCM.decrypt`。并连续演示三种篡改（翻密文位、
改 AAD、换密钥）全部被 `InvalidTag` 拦下——这是 GCM 相比 CBC 的核心价值。

### 6.2 `02` — 进阶：RSA 的正确边界

关键代码与结论：

```python
max_len = 256 - 2 * 32 - 2      # 2048bit 密钥 + SHA-256 ⇒ 190 字节
public_key.encrypt(b"A" * 191, OAEP)   # ValueError: Encryption failed
```

`02` 用一个真实的 `ValueError` 让你记住：**RSA 装不下业务数据**。同时对比
"公钥加密→私钥解密"（机密性）与"私钥签名→公钥验证"（身份+完整性）两条
方向不同的链路。

### 6.3 `03` — 实战：安全通信工具

模拟 TLS 的简化版，`SecureServer` / `SecureClient` 两个类完整走通：

```
客户端                                         服务器
  │ 生成会话密钥 K ── RSA_OAEP(服务器公钥, K) ──► 私钥解出 K
  │ AES_GCM(K, 消息) + nonce ─────────────────► 用 K 解密
  │ RSA_PSS(客户端私钥, 密文) ─────────────────► 用登记的客户端公钥验签
```

`03` 还内置了两场攻击演示：
- **篡改密文** → 验签/解密失败；
- **攻击者自带密钥伪造消息** → 因公钥不在服务器信任名单内被拒。

这解释了真实系统为什么要"证书固定 / CA 信任链"：**光有加密不够，
还必须确认"你手里的公钥真的是对方的"**——否则中间人可以直接换掉公钥。

### 6.4 运行方式

```bash
cd days/day-148-对称与非对称加密/code
pip install cryptography
python3 01-aes-gcm-basics.py
python3 02-rsa-asymmetric.py
python3 03-hybrid-secure-channel.py
```

---

## 七、思考题

1. **为什么 AES 分组长度固定 128 bit，但密钥可以是 128/192/256 bit？**
   密钥变长改变的是轮数还是分组？这样做的好处是什么？

**参考答案**

分组长度由算法的**内部结构**决定：AES 把 16 字节排成 4×4 的"状态矩阵"，SubBytes（逐字节替换）、ShiftRows（行移位）、MixColumns（列混合）这套运算天然定义在 16 字节上，改分组等于重新设计整个算法。

密钥变长改变的是**轮数**，不是分组：密钥扩展从主密钥推导出每轮一把子密钥，AES-128/192/256 分别跑 10/12/14 轮。轮数越多，混淆与扩散越充分，安全裕度越大。

这样做的好处：① 三种强度**共用同一套数据通路和 S 盒**，硬件（AES-NI 指令）与软件实现只需微调轮数，生态兼容性好；② 想提升强度只需"多跑几轮"，代价是线性的性能下降，而不是推倒重来；③ 128 bit 分组对生日界攻击已经足够安全——同一密钥下加密到 2^64 个分组（约 2^68 字节）才需要担心分组碰撞，现实中远达不到。

小例子：AES-128 和 AES-256 每次都处理 16 字节明文，后者只是多跑 4 轮、子密钥更长，密文块大小完全一样。

2. **GCM 的 nonce 只有 12 字节，如果高并发系统每秒加密上百万条消息，
   随机 nonce 会不会碰撞？** 请从生日悖论角度估算碰撞概率，并说明工业界
   如何避免（提示：计数器 / 随机 96 位 / 密钥轮换）。

**参考答案**

会有碰撞风险，而且随消息数**平方增长**。生日悖论告诉我们：在 2^96 个可能取值里随机取 N 次，出现重复的概率约为 `p ≈ N² / 2^97`——远早于"取遍所有值"就会撞上。

用代码估算"每秒 100 万条"的场景（纯标准库）：

```python
# 生日悖论估算：随机 96 位 nonce 的碰撞概率
# 近似公式：p ≈ N^2 / 2^97（N 为同一把密钥下加密的消息总数）

def collision_prob(n_messages: int) -> float:
    return n_messages ** 2 / 2 ** 97

per_second = 10 ** 6                      # 每秒加密 100 万条
print('1 秒内碰撞概率:  %.2e' % collision_prob(per_second))
print('1 天累计碰撞概率: %.2e' % collision_prob(per_second * 86400))
print('1 年累计碰撞概率: %.4f' % collision_prob(per_second * 86400 * 365))

# NIST 建议：同一密钥下随机 nonce 最多加密 2^32 条消息
print('2^32 条消息碰撞概率: 2^%d' % round(32 * 2 - 97))
```

预期输出（实测）：

```
1 秒内碰撞概率:  6.31e-18
1 天累计碰撞概率: 4.71e-08
1 年累计碰撞概率: 0.0063
2^32 条消息碰撞概率: 2^-33
```

解读：单看一秒几乎不可能撞（6.3e-18），但**同一把密钥连续用一年**，累计概率约 0.6%——对高价值系统已不可忽略；而 GCM 的 nonce 重用是毁灭性的（泄露明文异或关系、可恢复认证密钥 H 伪造 tag）。

工业界三种对策：① **计数器 nonce**：严格单调递增，数学上保证不重复，但要持久化计数状态，分布式多实例需给每个实例划分独立号段；② **随机 96 位 + 密钥轮换**：NIST 建议同一密钥下随机 nonce 最多用 2^32 次（此时 p≈2^-33），到量就换新密钥，把 N 压回安全区；③ 两者结合：实例 ID 拼计数器，既免持久化全局状态又绝不碰撞。

3. **RSA 公钥加密没有前向保密，为什么现代 TLS 1.3 干脆删掉了 RSA 密钥
   交换，只保留 (EC)DHE？** 如果服务器私钥被盗，两种方案的后果差别在哪？

**参考答案**

RSA 密钥交换的流程是：客户端生成预主密钥，用**服务器长期公钥**加密后发过去。这意味着会话密钥的"根"就是那把长期私钥——攻击者只要**先录下全部流量、日后拿到私钥**，就能解开所有历史会话。前向保密（Forward Secrecy：长期密钥泄露不危及过去会话）完全不存在。

(EC)DHE 每次连接生成**一次性**的临时密钥对，会话密钥由双方的临时 DH 共享秘密推导，临时私钥用完即弃。长期私钥在 TLS 1.3 里只负责**签名认证**，不再参与加密。私钥被盗后：攻击者只能冒充服务器发起**未来**的连接，对录下的历史流量一条也解不开——因为解密所需的临时私钥早已销毁。

小例子：攻击者录了一年的流量后偷到私钥。RSA 方案：一年记录全部明文曝光；ECDHE 方案：历史流量仍是乱码，损失被限制在"未来可被冒充"（换证书即可止血）。

顺带的好处：删掉 RSA 密钥交换也一并消灭了 Bleichenbacher/ROBOT 这类针对 RSA 解密填充的预言机攻击面，协议更简单、握手更快（1-RTT）。

4. **"签名"和"HMAC"都能防篡改，什么时候必须用签名而不能用 HMAC？**
   （提示：HMAC 双方共享同一把密钥，谁都能伪造）

**参考答案**

核心区别在**密钥的分布**：HMAC 是对称的，通信双方持有同一把密钥，**任何一方都能算出合法 MAC**；数字签名是非对称的，只有私钥持有者能生成，任何人用公钥都能验证。由此推出三类必须用签名的场景：

- **不可否认（防抵赖）**：合同、交易指令、审计证据。HMAC 场景下接收方自己也能伪造 MAC，发送方可以抵赖说"是你自己造的"，第三方裁判无法区分；签名只有私钥能产生，抵赖不成立。
- **一对多验证**：软件安装包、证书、公开发布的 JWT。验证者成千上万，若用 HMAC 就得把密钥发给每个验证者——等于公开密钥，任何人都能伪造"官方包"。签名只需分发公钥，验证者没有伪造能力。
- **验证方不可信**：你希望对方能校验、但绝不能让对方有能力篡改或冒充你。

HMAC 的优势是快、实现简单，适合**双方互信且封闭**的场景：支付回调验签（商户与平台共享密钥）、会话 Cookie、内部服务间认证。

小例子：软件厂商用私钥给安装包签名，百万用户用内置公钥验证；换成 HMAC，密钥必须塞进每个客户端，提取出来就能伪造任意"官方更新"。

5. **假设你要做一个"端到端加密聊天软件"，设计了：客户端各自生成 RSA
   密钥对，互相用对方公钥加密消息。** 这个方案有哪些致命问题？
   请至少说出两点并给出改进方向（提示：为何实际产品用双棘轮 / Signal 协议）。

**参考答案**

至少有四个致命问题：

- **公钥没有认证 → 中间人换钥**：你怎么确认拿到的"对方公钥"真的属于对方？恶意服务器或网络中间人可以把自己的公钥塞给你，解密读完再用真公钥转发，双方毫无察觉。改进：通过可信渠道核对公钥指纹（Signal 的"安全码"/扫码），或引入证书与密钥透明日志。
- **没有前向保密**：消息直接用长期 RSA 公钥加密，私钥一旦被盗，**全部历史聊天记录**被解开。改进：用临时 Diffie-Hellman（如 X25519）协商会话密钥，临时私钥用完即弃。
- **没有泄露后安全（post-compromise security）**：某时刻密钥泄露后，之后的所有消息也持续可读。改进：**双棘轮**（Double Ratchet）——每条消息都通过 DH 棘轮 + 对称密钥棘轮推进密钥，一次泄露只影响有限窗口，后续自动恢复安全。
- **性能与长度上限**：RSA-2048 + OAEP 单次最多加密约 190 字节，长消息、图片、语音根本装不下；RSA 运算慢、移动端耗电。改进：**混合加密**——非对称只搬运一次性对称密钥，数据全走 AES-GCM。

这正是 Signal 协议的组成：X3DH 解决"对方离线时的首次密钥协商"，双棘轮解决持续的前向保密与泄露后安全，数据层用 AEAD 对称加密。自己拿 RSA 直接加密消息，等于把上面所有坑都踩一遍。

> 做完思考题，再回看 `diagrams/README.md` 的决策树，尝试用它回答：
> "给 100 万用户的数据库字段做加密，你会怎么设计密钥体系？"

**参考答案**

按决策树，字段数据远超几百字节且需要保密，走**混合加密（信封加密）**分支，密钥分两层：

- **数据密钥 DEK**：每个用户（甚至每条记录）一把随机 AES-256 密钥，用 AES-GCM 加密字段；nonce 每次随机生成并与密文同存，把用户 ID、字段名放进 AAD 防止"张冠李戴"式篡改。
- **主密钥 KEK**：DEK 用 KEK 加密后与密文一起存库（"信封"），KEK 本身放在 KMS/HSM 里，绝不落库、不进 Git。

这样设计的好处：① 100 万用户互不牵连——单个 DEK 泄露只影响一个用户；② 轮换 KEK 只需重新封装 DEK，不必重加密海量数据；③ 数据库被拖走时，没有 KMS 里的 KEK 就全是乱码。💡 提示：高并发下注意 GCM 的 nonce 用量上限（见第 2 题），按用户分钥天然把每把密钥的消息数压得很低。
