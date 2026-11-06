#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 148 — 02 RSA 非对称加密进阶用法与避坑
==========================================

运行环境：
    pip install cryptography
    python3 02-rsa-asymmetric.py

本节目标：
    1. 生成 RSA 密钥对，序列化成 PEM（公钥可公开、私钥要保密）
    2. 用 OAEP 填充做加密/解密，并亲眼看到"RSA 加密有长度上限"
    3. 用 PSS 填充做签名/验签（签名 = 私钥加密摘要，公钥验证明身份）
    4. 演示一个经典错误：给 RSA 加密一把错位的钥匙会怎样

⚠️ 避坑提示：
    - RSA 加密的是"短消息"，最大明文长度 ≈ 密钥字节数 - 2*哈希长度 - 2。
      2048-bit 密钥 + SHA-256 ≈ 190 字节。别拿它加密大文件！
    - 永远不要用"教科书 RSA"（明文直接 ^e mod n），必须配 OAEP/PSS 填充，
      否则相同明文加出来密文相同，且小消息可被开方还原。
    - 私钥不要 print 到日志里。本文件打印私钥 hex 只为教学。
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
import base64

# ----------------------------------------------------------------------
# 1. 生成 RSA 密钥对
# ----------------------------------------------------------------------
print("[1] 生成 RSA-2048 密钥对（约 0.1~1 秒）")
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()
print(f"    私钥类型: {type(private_key).__name__}")
print(f"    公钥指数 e = {private_key.private_numbers().public_numbers.e}")
print(f"    模数 n 位数 = {private_key.key_size} bit")

# 序列化：公钥可以随意公开（这就是"public"的含义）
pem_public = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
print("\n    公钥 PEM（前 3 行，可公开分发）:")
for line in pem_public.decode().splitlines()[:3]:
    print("      " + line)

# 私钥也可以用密码（passphrase）再加密一层，防止 PEM 文件被盗直接可用
pem_private_enc = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(b"demo-passphrase"),
)
print(f"    私钥 PEM 已用口令加密，共 {len(pem_private_enc)} 字节（截断显示）")


# ----------------------------------------------------------------------
# 2. RSA + OAEP 加密（非对称加密）
# ----------------------------------------------------------------------
print("\n[2] RSA-OAEP 加密与解密")
oaep = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)
secret = b"session-key-AES-256"
ciphertext = public_key.encrypt(secret, oaep)
print(f"    明文 {secret} → 密文 {len(ciphertext)} 字节（2048bit=256 字节定长）")

plain_again = private_key.decrypt(ciphertext, oaep)
assert plain_again == secret
print(f"    用私钥解密还原: {plain_again} ✅")


# ----------------------------------------------------------------------
# 3. 避坑：RSA 加密长度有上限
# ----------------------------------------------------------------------
print("\n[3] 避坑演示：为什么 RSA 不能加密大文件")
max_len = 256 - 2 * 32 - 2          # 密钥字节数 - 2*哈希长度 - 2
print(f"    2048-bit 密钥 + SHA-256 时，最大明文 ≈ {max_len} 字节")
too_long = b"A" * (max_len + 1)
try:
    public_key.encrypt(too_long, oaep)
    print("    ❌ 竟然加密成功了（不应该）")
except ValueError as e:
    print(f"    ✅ 超长明文被拒绝: {e}")
    print("    👉 结论：RSA 只用来加密一个「会话密钥」（几十字节），")
    print("       真正的数据用 AES 加密——这就是「混合加密」（见 03 文件）。")


# ----------------------------------------------------------------------
# 4. RSA + PSS 签名与验签
# ----------------------------------------------------------------------
print("\n[4] 数字签名（RSA-PSS）")
pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                  salt_length=padding.PSS.MAX_LENGTH)
doc = b"transfer: 100 CNY to Alice"
signature = private_key.sign(doc, pss, hashes.SHA256())
print(f"    签名长度 = {len(signature)} 字节（等于密钥长度）")

public_key.verify(signature, doc, pss, hashes.SHA256())
print("    ✅ 真签名验签通过")

try:
    public_key.verify(signature, b"transfer: 10000 CNY to Alice", pss, hashes.SHA256())
    print("    ❌ 篡改文档竟然验签通过（不应该）")
except InvalidSignature:
    print("    ✅ 文档被改一个字符 → 验签失败（防篡改 + 身份认证）")

print("\n    签名 vs 加密（最重要的一张对照）:")
print("      加密：公钥加密 → 私钥解密   （目标：只有我能看）")
print("      签名：私钥签名 → 公钥验证   （目标：证明是我发的，且没被改）")


print("\n✅ 02 运行完毕：RSA 适合加密短数据与做签名，大数据交给 AES。")
