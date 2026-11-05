#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 148 — 03 实战：混合加密安全通信工具
========================================

运行环境：
    pip install cryptography
    python3 03-hybrid-secure-channel.py

场景（模拟 TLS 的简化版）：
    客户端想给服务器发一条机密消息，但双方只有通过不安全的信道，
    并且客户端事先只拿到了服务器的**公钥**（可以从官网/证书获得）。

混合加密方案（工业界标准做法）：
    1. 客户端生成一个临时（一次性）AES-256 会话密钥
    2. 用服务器的 RSA 公钥加密这个会话密钥（密钥封装）
    3. 用 AES-GCM 加密真正的业务数据（对称加密，快）
    4. 服务器用私钥解出会话密钥，再解出业务数据
    5. 客户端再对消息做 RSA-PSS 签名，服务器验签确认"真的是客户端发的"

为什么这样设计？
    - 对称加密快但"怎么安全地把密钥给对方"很难（密钥分发问题）
    - 非对称加密解决了密钥分发，但慢且有长度限制
    - 混合 = 用 RSA 只传 32 字节密钥 + 用 AES 传任意大数据，两全其美

⚠️ 本文件是教学示例：真实 TLS 用 ECDHE 做**前向保密**（即使服务器私钥
   泄露，历史会话也解不开），并配有证书链与 MAC。这里只演示核心思路。
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidTag, InvalidSignature
import os
import json
import base64

OAEP = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),
                    algorithm=hashes.SHA256(), label=None)
PSS = padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                  salt_length=padding.PSS.MAX_LENGTH)


# ======================================================================
# 服务器：持有私钥/公钥，负责解密与验签
# ======================================================================
class SecureServer:
    def __init__(self):
        self._private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)
        self._trusted_client_pem = None      # 预先登记的可信客户端公钥（类似白名单/证书固定）

    @property
    def public_pem(self) -> bytes:
        """公钥以 PEM 分发（真实世界会封装进 X.509 证书）。"""
        return self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def register_client(self, client_public_pem: bytes) -> None:
        """登记可信客户端公钥（真实系统里通过证书/CA 或预共享完成）。"""
        self._trusted_client_pem = client_public_pem.strip()

    def receive(self, packet: dict) -> str:
        """收到 {wrapped_key, nonce, ciphertext, signature} 并解密。"""
        # 0. 校验发送方公钥在信任名单内（否则攻击者可自带密钥伪造签名）
        if self._trusted_client_pem is None or \
                packet["client_pub"].strip().encode() != self._trusted_client_pem:
            raise InvalidSignature("客户端公钥不在信任名单内")

        session_key = self._private_key.decrypt(
            base64.b64decode(packet["wrapped_key"]), OAEP)
        nonce = base64.b64decode(packet["nonce"])
        ct = base64.b64decode(packet["ciphertext"])
        aad = packet["header"].encode()

        # 先验签（证明来源 + 完整性），用发送方的公钥验
        verifier = serialization.load_pem_public_key(self._trusted_client_pem)
        verifier.verify(
            base64.b64decode(packet["signature"]), ct, PSS, hashes.SHA256())

        # 再解密（AES-GCM 自带完整性校验）
        return AESGCM(session_key).decrypt(nonce, ct, aad).decode("utf-8")


# ======================================================================
# 客户端：持有服务器公钥，负责封装密钥与加密
# ======================================================================
class SecureClient:
    def __init__(self, server_public_pem: bytes):
        self._server_pub = serialization.load_pem_public_key(server_public_pem)
        self._signing_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)   # 客户端自己的签名密钥

    @property
    def public_pem(self) -> bytes:
        return self._signing_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    def send(self, message: str, header: str = "v1") -> dict:
        session_key = AESGCM.generate_key(bit_length=256)   # 一次性会话密钥
        nonce = os.urandom(12)
        aad = header.encode()
        ct = AESGCM(session_key).encrypt(nonce, message.encode(), aad)

        return {
            "header": header,
            "client_pub": self.public_pem.decode(),
            "wrapped_key": base64.b64encode(
                self._server_pub.encrypt(session_key, OAEP)).decode(),
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ct).decode(),
            "signature": base64.b64encode(self._signing_key.sign(
                ct, PSS, hashes.SHA256())).decode(),
        }


# ======================================================================
# 演示
# ======================================================================
def main():
    print("=" * 60)
    print("混合加密安全通信演示")
    print("=" * 60)

    server = SecureServer()
    client = SecureClient(server.public_pem)
    server.register_client(client.public_pem)     # 预先登记客户端身份
    print(f"\n[1] 服务器已就绪，公钥 {len(server.public_pem)} 字节（可公开）")
    print("    已登记可信客户端公钥（白名单）")

    msg = "账号密码已更新：user=niedong, pwd=********"
    packet = client.send(msg)
    print(f"[2] 客户端发送密文包，字段: {list(packet.keys())}")
    print(f"    线路上看到的 ciphertext = {packet['ciphertext'][:60]}...")
    print("    🔒 中间人只能看到 RSA 定长密文 + AES 密文，得不到明文")
    print("    📦 wrapped_key 仅 256 字节，真正数据走 AES，效率最优")

    got = server.receive(packet)
    print(f"[3] 服务器解密并验签成功: {got}")
    assert got == msg

    # ---- 攻击 1：中间人篡改密文 ----
    print("\n[4] 攻击演示：中间人篡改密文")
    bad = dict(packet)
    raw = bytearray(base64.b64decode(bad["ciphertext"]))
    raw[-1] ^= 0x01
    bad["ciphertext"] = base64.b64encode(bytes(raw)).decode()
    try:
        server.receive(bad)
        print("    ❌ 篡改未被发现")
    except (InvalidSignature, InvalidTag):
        print("    ✅ 验签/解密失败，篡改被发现，攻击失败")

    # ---- 攻击 2：攻击者用自己的密钥伪造消息 ----
    print("\n[5] 攻击演示：攻击者用自己生成的会话密钥伪造")
    fake_packet = dict(packet)
    fake_session = AESGCM.generate_key(bit_length=256)
    fake_nonce = os.urandom(12)
    fake_ct = AESGCM(fake_session).encrypt(fake_nonce, b"transfer all money!", None)
    fake_packet["ciphertext"] = base64.b64encode(fake_ct).decode()
    fake_packet["nonce"] = base64.b64encode(fake_nonce).decode()
    try:
        server.receive(fake_packet)
        print("    ❌ 伪造消息被接受")
    except (InvalidSignature, InvalidTag):
        print("    ✅ 伪造消息验签失败（攻击者没有服务器认可的签名私钥）")

    print("\n" + "=" * 60)
    print("✅ 03 实战结束：RSA 封装密钥 + AES 传数据 + 签名保真 = 混合加密")
    print("=" * 60)


if __name__ == "__main__":
    main()
