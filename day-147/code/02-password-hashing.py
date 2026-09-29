#!/usr/bin/env python3
"""Day 147 - 02 密码哈希与 HMAC：正确姿势 + 避坑

演示：
  A. 裸哈希存密码的错误与攻击原理
  B. PBKDF2 加盐慢哈希（正确姿势）
  C. HMAC 消息认证 + 时序攻击避坑

直接运行: python3 02-password-hashing.py
"""

import hashlib
import hmac
import os
import time

# =========================================================
# A. ❌ 错误示范：裸哈希存密码（只做演示，切勿用于生产）
# =========================================================
def unsafe_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# 彩虹表预计算演示：常见弱口令 → 摘要 可以提前全部算好
rainbow = {unsafe_hash(p): p for p in ["123456", "password", "admin", "qwerty"]}
print("彩虹表攻击演示: 拖库拿到摘要 →", rainbow.get(unsafe_hash("123456")))

# =========================================================
# B. ✅ 正确姿势：PBKDF2 + 随机盐 + 高迭代次数
# =========================================================
ITERATIONS = 100_000   # 演示用 10 万次（生产建议 ≥ 60 万，OWASP 2023）

def hash_password(password: str) -> str:
    """生成自描述的存储串: 算法$迭代$盐$摘要"""
    salt = os.urandom(16)                                    # 每个密码独立随机盐
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, ITERATIONS, dklen=32
    )
    return f"pbkdf2$sha256${ITERATIONS}${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_hex, digest_hex = stored.split("$")[1:]
        calc = hashlib.pbkdf2_hmac(
            algo, password.encode("utf-8"), bytes.fromhex(salt_hex), int(iter_s), dklen=32
        )
        # ⚠️ 必须用 compare_digest，不能 ==（防时序攻击）
        return hmac.compare_digest(calc.hex(), digest_hex)
    except ValueError:
        return False

print("\n--- 密码哈希（正确姿势）---")
stored = hash_password("S3cret!_PASS")
print("存储串:", stored[:60], "...")
print("正确密码验证:", verify_password("S3cret!PASS_", stored))   # 错密码 → False
print("正确密码验证:", verify_password("S3cret!PASS", stored))

# 加盐后：相同密码每次哈希结果都不同（盐不同），彩虹表失效
print("两次哈希同一密码:", hash_password("abc") != hash_password("abc"))

# 慢哈希到底多慢？感受一下
t0 = time.perf_counter()
hashlib.pbkdf2_hmac("sha256", b"x", b"salt", ITERATIONS)
print(f"PBKDF2 {ITERATIONS} 次迭代耗时: {(time.perf_counter()-t0)*1000:.1f} ms")
print(f"SHA-256 单次耗时: 0.0x ms 级 —— 快正是裸哈希存密码的致命伤")

# =========================================================
# C. HMAC：完整性 + 认证
# =========================================================
API_KEY = os.urandom(32)

def sign(body: str) -> str:
    """服务端签名"""
    return hmac.new(API_KEY, body.encode(), hashlib.sha256).hexdigest()

def check(body: str, sig: str) -> bool:
    return hmac.compare_digest(sign(body), sig)

print("\n--- HMAC 消息认证 ---")
body = "action=transfer&to=bob&amount=100"
sig = sign(body)
print("签名有效:", check(body, sig))
print("篡改后验证:", check("action=transfer&to=bob&amount=999", sig))  # False

# ⚠️ 避坑 1：为什么不能 sha256(key + msg)？长度扩展攻击
#    Merkle–Damgård 结构下，知道 H(key||msg) 可以算出 H(key||msg||padding||extra)
#    HMAC 的双层结构免疫此攻击。
# ⚠️ 避坑 2：比较签名必须恒定时间
bad = False
# bad = sign(body) == sig          # ❌ 短路比较，可被时序攻击逐字节猜测
good = hmac.compare_digest(sign(body), sig)  # ✅
print("恒定时间比较结果:", good)

# ⚠️ 避坑 3：盐/密钥随机源要用密码学安全的 os.urandom / secrets，
#    不要用 random 模块（梅森旋转可预测）
