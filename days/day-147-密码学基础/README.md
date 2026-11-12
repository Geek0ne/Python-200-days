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

**参考答案**

盐的作用不是"保密"，而是**让每个用户的哈希输入独一无二**。设想威胁模型是"数据库被拖库"：攻击者拿到哈希的同时也拿到了盐，所以盐保不保密根本不影响安全性；真正重要的是让攻击者**无法复用预先算好的结果**。

唯一且随机的盐带来两个效果：① 相同密码在不同用户处产生不同摘要，彩虹表（攻击者提前算好的"常见密码 → 摘要"对照表）彻底失效——表必须针对每个盐重新生成，代价随用户数爆炸；② 无法从库里一眼看出哪些用户用了同一个密码。

如果全站共用一个固定盐，攻击者**不需要为"每个盐"建表——因为只有一个盐**：他只需生成一张掺入该盐的彩虹表，就能批量反查所有用户；而且盐固定不变，这张表甚至可以在拖库之前就预先算好。相同密码的用户摘要仍然相同，破解一个等于破解一片。

小例子：alice 和 bob 都用 `123456`。独立随机盐下，两人的摘要完全不同，攻击者必须分别爆破；共享固定盐下，两人摘要一模一样，查一次表同时命中两个账号。

⚠️ 注意：盐要用 `os.urandom()` / `secrets` 这类密码学安全随机源生成（建议至少 16 字节）。用用户名当"唯一盐"也不行——它可预测，攻击者仍能针对每个用户名预计算定向表。

2. 既然 SHA-256 比 PBKDF2 快得多，为什么存密码反而要选"慢"的 PBKDF2？这两个场景对哈希函数的诉求差在哪？（提示：一个防篡改、一个防爆破）

**参考答案**

两个场景的**攻击者模型**完全不同，所以对"速度"的诉求正好相反。

- **防篡改（完整性校验、数字签名）**：攻击者的目标是找到碰撞或伪造摘要，SHA-256 的抗碰撞性让这在计算上不可行——算得再快也帮不了攻击者。而防守方要给 GB 级文件、海量请求算摘要，"快"是刚需。
- **防爆破（密码存储）**：拖库后攻击者离线穷举——把候选密码逐个哈希再比对。此时哈希函数的速度**直接等于攻击者的爆破速度**：SHA-256 在 GPU 上每秒可算数十亿次，弱密码瞬间沦陷。

PBKDF2 把 HMAC 串行迭代几十万次，故意让单次计算耗时几百毫秒：合法用户每次登录只算一次，几乎无感；攻击者每试一个候选密码都要付同样的代价，爆破成本被放大几十万倍。

小例子：爆破一个 100 万条的常见密码字典，裸 SHA-256 毫秒级跑完；PBKDF2（60 万次迭代、单次约 0.2 秒）单核要跑约 2.3 天——而这还只是针对一个用户的盐。

一句话总结：防篡改要"快 + 抗碰撞"，防爆破要"慢 + 加盐 + 成本可调"。💡 提示：迭代次数应随硬件进步不断调大（OWASP 建议 PBKDF2-HMAC-SHA256 至少 60 万次）；新项目也可选 scrypt / argon2 这类"内存困难型"算法，抗 GPU 并行爆破更强。

3. `sha256(secret_key + message)` 看起来也有"密钥"，为什么它不等于 HMAC，会被什么攻击打穿？

**参考答案**

它确实掺了密钥，但结构是"密钥前置 + 单次哈希"，正好撞上 Merkle–Damgård 结构（MD5/SHA-1/SHA-2 的共同骨架）的**长度扩展攻击（length extension attack）**。

原理：SHA-256 按 512 bit 分块链式处理，最终摘要就是处理完所有块后的内部状态。攻击者拿到 `H(key || msg)`，就等于拿到了"处理完 `key || msg || padding` 之后的状态"。他**无需知道 key**，就能从这个状态继续链式计算，得到 `H(key || msg || padding || extra)` 的合法摘要。

后果：攻击者可以在已签名消息后面**追加任意内容**并算出新的"有效签名"。例如原消息是 `amount=100`，他扩展成 `amount=100<padding字节>&admin=true`，服务端用 `sha256(key + 新消息)` 校验照样通过。

HMAC 为什么免疫：它是**双层哈希**——内层算 `H((K'^ipad) || msg)` 得到固定长度摘要，外层再算 `H((K'^opad) || 内层摘要)`。外层输入与"key||消息"的前缀状态无关，攻击者无法从最终结果继续扩展；且密钥通过 ipad/opad 参与了内外两层。

⚠️ 注意：长度扩展只对 MD 结构的哈希成立；SHA-3、BLAKE2 结构上天然免疫。但工程上的标准做法仍是直接用 `hmac` 模块，不要自造任何"密钥+消息"拼接方案。

4. 如果攻击者能测量你服务器的响应时间，用 `==` 比较密码摘要有什么风险？`hmac.compare_digest` 是如何消除这个风险的？

**参考答案**

Python 对 bytes/str 的 `==` 是**短路比较**：从第一个字节开始逐位比，遇到第一个不匹配就立刻返回 False。这意味着"匹配的前缀字节越多，比较耗时越长"——耗时泄露了内容信息。

能测量响应时间的攻击者可以**逐字节猜解**（时序攻击，侧信道攻击的一种：通过执行时间差推断秘密）：先对第 1 个字节尝试 0~255，统计哪个值的平均响应略长，那就是正确字节；固定第 1 字节再猜第 2 个……本来需要 2^256 次尝试的 32 字节摘要，最多 256×32 次就能猜完。网络抖动可以用大量请求取平均来消除。

`hmac.compare_digest` 是**恒定时间比较**：无论内容在第几个字节不同，它都会比较完全部字节才返回结果，耗时只取决于长度、与内容无关，攻击者从时间上得不到任何线索。

小例子：校验 API 签名时，`if sig == expected:` 有泄露风险；`if hmac.compare_digest(sig, expected):` 安全。

💡 提示：远程时序攻击受网络噪声影响，实施难度比本地大，但工程纪律是"比较 MAC、密码摘要、token 一律用 `compare_digest`"——零成本，没有理由不用。

5. 你要给一个 10 GB 的镜像文件做校验：为什么必须用流式 `update()` 分块读取？如果中途网络断了重传，能否从断点继续计算哈希？（想一想 Merkle–Damgård 的链式结构意味着什么）

**参考答案**

一次性 `f.read()` 会把 10 GB 全灌进内存，普通机器直接内存溢出。流式做法每次只读 1 MB 喂给 `h.update()`：hashlib 内部维护链式中间状态，**内存占用恒定**，与文件大小无关。

能否断点续算：**原理上可以**。Merkle–Damgård 的链式结构意味着"处理完前 k 个字节后，全部历史信息都浓缩在当前内部状态里"，后续计算只依赖这个状态、不再依赖前面的内容。所以只要保存了处理完 k 字节时的中间状态，重传后从第 k+1 字节继续喂入，最终结果与一次性计算完全一致。

工程现实：标准库的哈希对象不支持直接序列化存盘（不能 pickle），同一进程内可以用 `h.copy()` 做状态快照；跨进程/重启则要么让对象一直活着，要么重算前缀，要么换用能导出内部状态的第三方实现。Python 3.11+ 的 `hashlib.file_digest()` 已内置流式读取。

下面用内存数据模拟大文件，验证"分块等价"与"断点续算"：

```python
import hashlib

data = b'hello world' * 100000  # 用内存数据模拟大文件（约 1.1 MB）

# 方式一：一次性喂入全部字节
one_shot = hashlib.sha256(data).hexdigest()

# 方式二：流式分块喂入，每次 4096 字节
h = hashlib.sha256()
for i in range(0, len(data), 4096):
    h.update(data[i:i + 4096])
print('分块结果 == 一次性结果:', one_shot == h.hexdigest())

# 断点续算：处理完前半段后用 copy() 保存中间状态快照
half = len(data) // 2
h2 = hashlib.sha256()
h2.update(data[:half])
checkpoint = h2.copy()          # 快照：此刻的内部链式状态
checkpoint.update(data[half:])  # “重传后”继续喂入后半段
print('断点续算 == 一次性结果:', checkpoint.hexdigest() == one_shot)
```

预期输出：

```
分块结果 == 一次性结果: True
断点续算 == 一次性结果: True
```

两个 True 说明：`update()` 可以任意次、任意块大小地调用，结果等价于一次性喂入；`copy()` 快照中间状态后接着算，与从未中断完全一致。对真实文件，把 `data` 换成以 `'rb'` 打开、分块 `read()` 的文件即可。

---

## 参考

- [hashlib 官方文档](https://docs.python.org/zh-cn/3/library/hashlib.html)
- [hmac 官方文档](https://docs.python.org/zh-cn/3/library/hmac.html)
- RFC 2104（HMAC）、RFC 8018（PBKDF2）
- OWASP Password Storage Cheat Sheet
