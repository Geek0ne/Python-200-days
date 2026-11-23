"""
Day 094 - 安全编程
02-cryptography.py: 密码学基础（hashlib + cryptography）

知识点:
  - 哈希算法（MD5, SHA-256, bcrypt）
  - HMAC 签名验证
  - 对称加密（AES-GCM）
  - 非对称加密（RSA）
  - 数字签名
"""

import hashlib
import hmac
import os
import secrets
import base64
import time

# ============================================================
# 第一部分：哈希算法
# ============================================================

def hash_demo():
    """演示各种哈希算法"""
    message = "Hello, Python Security!"
    
    print("=" * 50)
    print("哈希算法对比")
    print("=" * 50)
    
    # MD5（不推荐用于安全场景）
    md5 = hashlib.md5(message.encode()).hexdigest()
    print(f"MD5:    {md5}")
    print(f"        长度: {len(md5)} 字符 ({len(md5) * 4} bits)")
    
    # SHA-1（已不安全）
    sha1 = hashlib.sha1(message.encode()).hexdigest()
    print(f"SHA-1:  {sha1}")
    print(f"        长度: {len(sha1)} 字符 ({len(sha1) * 4} bits)")
    
    # SHA-256（推荐）
    sha256 = hashlib.sha256(message.encode()).hexdigest()
    print(f"SHA-256: {sha256}")
    print(f"         长度: {len(sha256)} 字符 ({len(sha256) * 4} bits)")
    
    # SHA-512
    sha512 = hashlib.sha512(message.encode()).hexdigest()
    print(f"SHA-512: {sha512[:64]}...")
    print(f"         长度: {len(sha512)} 字符 ({len(sha512) * 4} bits)")
    
    # 雪崩效应演示
    print("\n--- 雪崩效应 ---")
    msg1 = "Hello"
    msg2 = "HellO"  # 只改变一个字母
    print(f"  '{msg1}' → SHA-256: {hashlib.sha256(msg1.encode()).hexdigest()[:32]}...")
    print(f"  '{msg2}' → SHA-256: {hashlib.sha256(msg2.encode()).hexdigest()[:32]}...")
    print("  一个字符的变化导致完全不同的哈希值")


# ============================================================
# 第二部分：密码存储（bcrypt）
# ============================================================

def password_hashing_demo():
    """演示安全的密码存储"""
    try:
        import bcrypt
        has_bcrypt = True
    except ImportError:
        has_bcrypt = False
        print("⚠️ bcrypt 未安装，使用模拟演示")
        print("   安装命令: pip install bcrypt")
    
    print("\n" + "=" * 50)
    print("密码存储最佳实践")
    print("=" * 50)
    
    passwords = ["password123", "MyS3cur3P@ss!", "abc"]
    
    if has_bcrypt:
        for pwd in passwords:
            # 生成盐并哈希
            salt = bcrypt.gensalt(rounds=12)
            hashed = bcrypt.hashpw(pwd.encode(), salt)
            
            print(f"\n密码: {pwd}")
            print(f"  盐:   {salt.decode()}")
            print(f"  哈希: {hashed.decode()[:50]}...")
            
            # 验证
            start = time.time()
            valid = bcrypt.checkpw(pwd.encode(), hashed)
            elapsed = time.time() - start
            print(f"  验证: {'✅ 正确' if valid else '❌ 错误'} ({elapsed:.3f}s)")
    else:
        # 模拟演示
        for pwd in passwords:
            # 简单模拟
            fake_salt = secrets.token_hex(16)
            fake_hash = hashlib.sha256((fake_salt + pwd).encode()).hexdigest()
            
            print(f"\n密码: {pwd}")
            print(f"  盐:   {fake_salt}")
            print(f"  哈希: {fake_hash[:50]}...")
            print(f"  验证: ✅ 正确 (模拟)")
    
    # ❌ 错误示范
    print("\n--- ❌ 错误示范 ---")
    
    # 不加盐的哈希
    password = "password123"
    naive_hash = hashlib.sha256(password.encode()).hexdigest()
    print(f"  不加盐 SHA-256: {naive_hash}")
    print("  ⚠️ 彩虹表攻击可以轻松反推")
    
    # MD5（更不安全）
    md5_hash = hashlib.md5(password.encode()).hexdigest()
    print(f"  MD5: {md5_hash}")
    print("  ⚠️ MD5 已被破解，可以在秒级反推")


# ============================================================
# 第三部分：HMAC 签名
# ============================================================

def hmac_demo():
    """演示 HMAC 签名与验证"""
    print("\n" + "=" * 50)
    print("HMAC 签名验证")
    print("=" * 50)
    
    # 模拟 API 密钥
    api_key = b"my-secret-api-key-2024"
    
    # 模拟请求数据
    request_data = b"action=transfer&amount=1000&to=alice"
    
    # 生成 HMAC 签名
    signature = hmac.new(
        api_key,
        request_data,
        hashlib.sha256
    ).hexdigest()
    
    print(f"请求数据: {request_data.decode()}")
    print(f"HMAC 签名: {signature}")
    
    # 验证签名
    def verify_hmac(key, data, sig):
        """验证 HMAC（使用常量时间比较，防止时序攻击）"""
        expected = hmac.new(key, data, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)
    
    # 正确签名
    valid = verify_hmac(api_key, request_data, signature)
    print(f"验证正确签名: {'✅' if valid else '❌'}")
    
    # 篡改数据
    tampered_data = b"action=transfer&amount=99999&to=alice"
    valid = verify_hmac(api_key, tampered_data, signature)
    print(f"验证篡改数据: {'✅' if valid else '❌'}")
    
    # 错误密钥
    wrong_key = b"wrong-key"
    valid = verify_hmac(wrong_key, request_data, signature)
    print(f"验证错误密钥: {'✅' if valid else '❌'}")
    
    # Webhook 验证示例
    print("\n--- Webhook 验证示例 ---")
    webhook_secret = b"whsec_1234567890"
    webhook_payload = b'{"event":"payment","amount":100}'
    
    # 发送方签名
    webhook_sig = hmac.new(
        webhook_secret,
        webhook_payload,
        hashlib.sha256
    ).hexdigest()
    
    print(f"Webhook 载荷: {webhook_payload.decode()}")
    print(f"Webhook 签名: sha256={webhook_sig}")
    
    # 接收方验证
    valid = verify_hmac(webhook_secret, webhook_payload, webhook_sig)
    print(f"验证 Webhook: {'✅' if valid else '❌'}")


# ============================================================
# 第四部分：对称加密（AES-GCM）
# ============================================================

def symmetric_encryption_demo():
    """演示 AES-GCM 对称加密"""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        has_crypto = True
    except ImportError:
        has_crypto = False
        print("\n⚠️ cryptography 未安装，跳过加密演示")
        print("   安装命令: pip install cryptography")
        return
    
    print("\n" + "=" * 50)
    print("AES-GCM 对称加密")
    print("=" * 50)
    
    # 生成 256 位密钥
    key = AESGCM.generate_key(bit_length=256)
    print(f"密钥 (hex): {key.hex()[:32]}...")
    print(f"密钥长度: {len(key)} 字节 ({len(key) * 8} bits)")
    
    # 要加密的数据
    plaintext = "这是一条敏感信息：银行卡号 6222 0200 0000 1234 567"
    plaintext_bytes = plaintext.encode('utf-8')
    
    print(f"\n明文: {plaintext}")
    
    # 加密
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 12 字节随机 nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext_bytes, None)
    
    print(f"Nonce (hex): {nonce.hex()}")
    print(f"密文 (hex): {ciphertext.hex()[:64]}...")
    print(f"密文长度: {len(ciphertext)} 字节")
    
    # 解密
    decrypted = aesgcm.decrypt(nonce, ciphertext, None)
    print(f"\n解密: {decrypted.decode('utf-8')}")
    
    # 篡改检测
    print("\n--- 篡改检测 ---")
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0xFF  # 篡改一个字节
    tampered = bytes(tampered)
    
    try:
        aesgcm.decrypt(nonce, tampered, None)
        print("  篡改检测: ❌ 未检测到（不应该发生）")
    except Exception as e:
        print(f"  篡改检测: ✅ 检测到篡改 ({type(e).__name__})")
    
    # 附加数据（AAD）
    print("\n--- 附加认证数据 (AAD) ---")
    aad = b"user_id=12345"  # 附加数据，不加密但参与认证
    ciphertext_with_aad = aesgcm.encrypt(nonce, plaintext_bytes, aad)
    decrypted = aesgcm.decrypt(nonce, ciphertext_with_aad, aad)
    print(f"  使用 AAD 加解密: ✅ {decrypted.decode()[:30]}...")


# ============================================================
# 第五部分：非对称加密（RSA）
# ============================================================

def asymmetric_encryption_demo():
    """演示 RSA 非对称加密"""
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa, padding
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.backends import default_backend
        has_crypto = True
    except ImportError:
        print("\n⚠️ cryptography 未安装，跳过 RSA 演示")
        return
    
    print("\n" + "=" * 50)
    print("RSA 非对称加密")
    print("=" * 50)
    
    # 生成密钥对
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    
    print("密钥对已生成 (2048 bits)")
    
    # 序列化密钥
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    print(f"私钥长度: {len(private_pem)} 字节")
    print(f"公钥长度: {len(public_pem)} 字节")
    
    # 加密（用公钥）
    message = "机密信息：RSA 加密演示"
    ciphertext = public_key.encrypt(
        message.encode(),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    print(f"\n明文: {message}")
    print(f"密文 (hex): {ciphertext.hex()[:64]}...")
    
    # 解密（用私钥）
    decrypted = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    print(f"解密: {decrypted.decode()}")
    
    # 数字签名
    print("\n--- 数字签名 ---")
    message_to_sign = "我要签署这份合同"
    
    # 签名（用私钥）
    signature = private_key.sign(
        message_to_sign.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    print(f"签名 (hex): {signature.hex()[:64]}...")
    
    # 验证签名（用公钥）
    try:
        public_key.verify(
            signature,
            message_to_sign.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        print("签名验证: ✅ 有效")
    except Exception:
        print("签名验证: ❌ 无效")
    
    # 篡改验证
    try:
        public_key.verify(
            signature,
            "篡改后的消息".encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        print("篡改验证: ❌ 未检测到")
    except Exception:
        print("篡改验证: ✅ 检测到篡改")


# ============================================================
# 主程序
# ============================================================

if __name__ == '__main__':
    hash_demo()
    password_hashing_demo()
    hmac_demo()
    symmetric_encryption_demo()
    asymmetric_encryption_demo()
    
    print("\n" + "=" * 50)
    print("✅ 密码学演示完成")
    print("=" * 50)
