#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 148 — 01 AES-GCM 对称加密基础用法
=====================================

运行环境：
    pip install cryptography
    python3 01-aes-gcm-basics.py

本节目标（新手友好版）：
    1. 生成一个 256-bit AES 密钥
    2. 用 AES-GCM 加密字符串，再解密还原
    3. 亲眼看到"篡改密文会被检测出来"（认证加密 AEAD 的核心价值）
    4. 认识 nonce（随机数）为什么绝对不能重用

⚠️ 避坑提示（先读再跑）：
    - AES-GCM 的 nonce 在同一条密钥下**只能使用一次**！重复使用会让攻击者
      直接恢复出认证密钥（详见 README 第 3.2 节）。所以这里每次加密都
      os.urandom(12) 新生成一个 12 字节 nonce，并把 nonce 和密文一起传输。
    - 加密只保证"机密性"，GCM 还额外提供"完整性"（篡改可检测），但它
      **不提供**"这条消息是谁发的"（那是签名/认证的事）。
    - 密钥绝不能硬编码进源码！本文件只是教学演示，真实项目请用 KMS/
      环境变量/密钥管理服务。
"""

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
import os
import base64

# ----------------------------------------------------------------------
# 1. 生成密钥
# ----------------------------------------------------------------------
# AES-256 需要 32 字节（256 bit）的密钥。os.urandom 是密码学安全随机源，
# 千万不要用 random.randbytes()/random.randint()（那是伪随机，可预测！）。
KEY = AESGCM.generate_key(bit_length=256)   # 等价于 os.urandom(32)
print(f"[1] 已生成 AES-256 密钥: {KEY.hex()}")
print(f"    密钥长度 = {len(KEY) * 8} bit")


def encrypt(plaintext: str, key: bytes, aad: bytes = b"") -> tuple[bytes, bytes]:
    """加密字符串，返回 (nonce, 密文+16字节认证标签)。

    aad = Additional Authenticated Data（附加认证数据）：
        它会被校验完整性，但**不会被加密**。典型用途：把消息头（如
        user_id、版本号）放进去，防止攻击者偷换这些元数据。
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)                       # 96 bit nonce，GCM 推荐长度
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
    return nonce, ciphertext


def decrypt(nonce: bytes, ciphertext: bytes, key: bytes, aad: bytes = b"") -> str:
    """解密；如果密文/AAD 被篡改，会抛出 InvalidTag 异常。"""
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, aad).decode("utf-8")


# ----------------------------------------------------------------------
# 2. 正常加解密
# ----------------------------------------------------------------------
print("\n[2] 正常加解密流程")
msg = "聂董的秘密：明天下午 3 点开会"
# 把消息头放进 AAD，防止攻击者篡改接收方
aad = b"to=niedong;version=1"

nonce, ct = encrypt(msg, KEY, aad)
print(f"    明文  : {msg}")
print(f"    nonce : {base64.b64encode(nonce).decode()}")
print(f"    密文  : {base64.b64encode(ct).decode()}")

recovered = decrypt(nonce, ct, KEY, aad)
print(f"    解密后: {recovered}")
assert recovered == msg, "解密结果与原文不一致！"
print("    ✅ 解密成功，原文一致")


# ----------------------------------------------------------------------
# 3. 篡改检测（GCM 的"认证"能力）
# ----------------------------------------------------------------------
print("\n[3] 篡改攻击演示")

# 3.1 修改密文里的任何一个字节
tampered = bytearray(ct)
tampered[-1] ^= 0x01        # 翻转最后 1 个 bit
try:
    decrypt(nonce, bytes(tampered), KEY, aad)
    print("    ❌ 篡改没有被发现（不应该发生！）")
except InvalidTag:
    print("    ✅ 密文被篡改 → 解密时抛出 InvalidTag，攻击被拦住")

# 3.2 修改 AAD（元数据）
try:
    decrypt(nonce, ct, KEY, b"to=hacker;version=1")
    print("    ❌ AAD 篡改没有被发现（不应该发生！）")
except InvalidTag:
    print("    ✅ AAD 被篡改 → 同样抛出 InvalidTag")

# 3.3 换一条错误的密钥
wrong_key = AESGCM.generate_key(bit_length=256)
try:
    decrypt(nonce, ct, wrong_key, aad)
    print("    ❌ 错误密钥竟然解密成功（不应该发生！）")
except InvalidTag:
    print("    ✅ 密钥不对 → 抛出 InvalidTag")


# ----------------------------------------------------------------------
# 4. nonce 重用为什么致命（直观演示）
# ----------------------------------------------------------------------
print("\n[4] nonce 重用演示（仅演示现象，不做真实攻击）")
fixed_nonce = os.urandom(12)
c1 = AESGCM(KEY).encrypt(fixed_nonce, b"AAAA", None)
c2 = AESGCM(KEY).encrypt(fixed_nonce, b"BBBB", None)
# 两条消息用同一个 nonce：密文的前若干字节出现可预测的 XOR 关系
xor_head = bytes(a ^ b for a, b in zip(c1[:4], c2[:4]))
print(f"    明文A=AAAA  明文B=BBBB  逐字节异或 = {xor_head.hex()}")
print("    ⚠️ 同一 nonce 加密两条明文，密文异或 = 明文异或。")
print("       攻击者不需要密钥就能推出明文关系；GCM 下更严重——可恢复认证密钥。")
print("       结论：nonce = 一次性数字，绝不能重复（用随机数或单调计数器）。")


print("\n✅ 01 运行完毕：你已掌握 AES-GCM 的加解密、认证与 nonce 纪律。")
