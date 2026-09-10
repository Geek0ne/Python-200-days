# Day 148 练习与检查表 — 对称与非对称加密

## ✅ 完成清单

- [ ] 能说清"对称加密"与"非对称加密"的区别，以及各自的核心优缺点
- [ ] 理解"密钥分发难题"，知道非对称加密为什么能解决它
- [ ] 知道 AES 的密钥/分组长度（AES-128/192/256，分组恒为 128 bit）
- [ ] 理解分组模式 ECB / CBC / CTR / GCM 的差异，能说出为什么不要用 ECB
- [ ] 理解 AEAD（认证加密）：AES-GCM 同时给机密性 + 完整性
- [ ] 记住 nonce/IV 绝对不能在同一条密钥下重用，并知道后果
- [ ] 理解 RSA 数学基础（大整数分解）与为什么必须配 OAEP/PSS 填充
- [ ] 记住 RSA 加密长度上限公式：密钥字节数 − 2×哈希长度 − 2
- [ ] 能分清"加密（公钥加密→私钥解密）"与"签名（私钥签名→公钥验证）"
- [ ] 理解混合加密：RSA 封装会话密钥 + AES 传数据
- [ ] 跑通 `code/01`、`code/02`、`code/03` 三个示例，并看懂篡改演示的报错

## 📝 练习题

### 基础

**1. 对称 vs 非对称对照表填空**：不查资料，写出下面表格（每行 1~2 点即可）：

| 维度 | AES 对称加密 | RSA 非对称加密 |
|---|---|---|
| 密钥数量 | ? | ? |
| 加解密速度 | ? | ? |
| 能加密的数据量 | ? | ? |
| 典型用途 | ? | ? |
| 密钥如何分发 | ? | ? |

答完后再对照 `README.md` 第 1.1 / 1.2 节修正。

**2. 给 `code/01-aes-gcm-basics.py` 加一个 `encrypt_file()` 函数**：
读取一个文件的字节内容，用 AES-GCM 加密并写出 `原文件名.enc`，格式为
`nonce(12B) || ciphertext`。再用对应的 `decrypt_file()` 还原，并用
`filecmp.cmp` 验证与原文件一致。要求：用 `os.urandom(12)` 生成 nonce，
不允许把 nonce 写死。

**3. 解释现象**：运行下面这段代码，观察两条密文的关系，并解释为什么
攻击者在不知道密钥的情况下也能看出明文之间的关系：

```python
key = AESGCM.generate_key(bit_length=256)
n = os.urandom(12)
c1 = AESGCM(key).encrypt(n, b"password=123456", None)
c2 = AESGCM(key).encrypt(n, b"password=654321", None)
print(xor(c1[:16], c2[:16]))   # 前 16 字节异或的结果说明了什么？
```


### 进阶

**4. 实现带 AAD 的"加密消息头"**：写一对函数
`seal(msg: str, key: bytes, meta: dict) -> bytes` /
`open_(blob: bytes, key: bytes) -> str`。要求把 `meta` 序列化成 JSON 作为
AAD（不加密但受完整性保护），并把 `blob` 设计成
`nonce || len(aad) || aad || ciphertext` 的可解析格式。测试：把 blob 里的
`meta` 改一个字符后 `open_` 必须抛出 `InvalidTag`。

**5. 用 RSA 给配置下发做签名**：模拟"服务器下发配置、客户端校验"：
服务器生成 RSA 密钥对并公开公钥；对配置 JSON 用 RSA-PSS 签名；
客户端用公钥验签后才加载配置。测试并回答：为什么这里**不能**改成
"服务器用自己私钥加密配置、客户端用公钥解密"？（提示：公钥是公开的，
谁都能解密；那只能证明完整性吗？）

### 挑战

**6. 设计一个"带前向保密"的简化握手**：现有方案里，会话密钥被 RSA 公钥
封装，一旦服务器私钥泄露，攻击者录下的历史流量都能被解开。查阅 ECDHE /
Diffie-Hellman，用 `cryptography` 的 `ec.generate_private_key` +
`exchange(ECDH(), peer_public_key)` 实现一次性密钥协商，并画时序图说明
为什么服务器私钥事后泄露也解不开历史会话（前向保密 / Forward Secrecy）。

**7.（选做）性能实测**：用 `time.perf_counter` 对比同样加密/解密 1 MB
数据的 AES-256-GCM 与 RSA-2048（RSA 需分块，实际不可用），把耗时比例
算出来，用数据解释"为什么混合加密是唯一可行方案"。
