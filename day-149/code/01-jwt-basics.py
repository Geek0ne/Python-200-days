#!/usr/bin/env python3
"""
Day 149 · 示例 01 —— JWT 基础用法（结构 / 签发 / 验证）

运行前安装依赖：
    pip install pyjwt

本示例演示：
    1. 手工拆解 JWT 三段结构（不依赖任何库，看清 Base64URL 本质）
    2. 用 PyJWT 签发 / 验证 HS256 token
    3. 过期时间 exp 与各种标准 claim 的正确写法
    4. 篡改 payload 后验签必然失败（JWT 的安全根基）

所有密钥都用运行时随机生成，避免把密钥写死在代码里（这也是最佳实践）。
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

import jwt  # PyJWT


# ────────────────────────────────────────────────────────────────
# 工具：Base64URL 编解码（JWT 用的变体：+ → -, / → _, 去掉 = 填充）
# ────────────────────────────────────────────────────────────────
def b64url_encode(raw: bytes) -> str:
    """标准 Base64 → Base64URL：替换字符 + 去掉填充"""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def b64url_decode(text: str) -> bytes:
    """Base64URL → 原始字节：自动补回填充（长度必须凑成 4 的倍数）"""
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


# ────────────────────────────────────────────────────────────────
# 第 1 部分：手工拆解一个 JWT
# ────────────────────────────────────────────────────────────────
def demo_parse_structure() -> None:
    print("=" * 62)
    print("第 1 部分：手工拆解 JWT 的三段结构")
    print("=" * 62)

    # 手工构造一个 HS256 token，完全不用库，理解每一步
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": "10086", "name": "聂董", "iat": int(time.time())}

    # JSON 序列化时用 compact 分隔符，避免多余空格（空格也会进签名）
    h_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode())

    signing_input = f"{h_b64}.{p_b64}".encode()

    secret = secrets.token_bytes(32)  # 256 bit 随机密钥（RFC 7518 推荐）
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    token = f"{h_b64}.{p_b64}.{b64url_encode(signature)}"

    print(f"\n[完整 token]\n{token}\n")

    parts = token.split(".")
    assert len(parts) == 3, "JWT 必须是 3 段"

    print(f"[① Header ] {b64url_decode(parts[0]).decode()}")
    print(f"[② Payload] {b64url_decode(parts[1]).decode()}")
    print(f"[③ Sig len] {len(b64url_decode(parts[2]))} 字节（SHA-256 → 固定 32 字节）")

    # 关键提醒：payload 是明文可读的！所以绝不能放敏感信息
    print("\n⚠️  注意：payload 用 Base64 解码就能直接读，签名不提供机密性！")


# ────────────────────────────────────────────────────────────────
# 第 2 部分：PyJWT 签发 + 验证
# ────────────────────────────────────────────────────────────────
def demo_encode_decode() -> None:
    print("\n" + "=" * 62)
    print("第 2 部分：PyJWT 签发与验证（HS256）")
    print("=" * 62)

    secret = secrets.token_bytes(32)
    now = int(time.time())

    # 注意：exp/iat/nbf 单位是「秒」而不是毫秒（写成毫秒 = 有效期 5 万年）
    payload = {
        "sub": "10086",                 # 主体：用户 ID
        "iss": "https://auth.example.com",  # 签发者
        "aud": "api.example.com",       # 预期接收方
        "iat": now,                     # 签发时间
        "nbf": now,                     # 生效时间
        "exp": now + 300,               # 过期时间：5 分钟后
        "jti": secrets.token_hex(8),    # 唯一 ID，用于防重放 / 黑名单
        "role": "user",
    }

    token = jwt.encode(payload, secret, algorithm="HS256")
    print(f"\n[签发的 token]\n{token}")

    # 验证：algorithms 参数必须显式给出（PyJWT 2.x 强制要求）
    decoded = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        audience="api.example.com",
        issuer="https://auth.example.com",
    )
    print(f"\n[验证通过，解出的 payload]\n{json.dumps(decoded, indent=2, ensure_ascii=False)}")

    # 顺手看看 Header（pyjwt 用 get_unverified_header 获取）
    print(f"\n[Header] {jwt.get_unverified_header(token)}")


# ────────────────────────────────────────────────────────────────
# 第 3 部分：篡改 payload → 验签失败（JWT 的安全根基）
# ────────────────────────────────────────────────────────────────
def demo_tamper_detected() -> None:
    print("\n" + "=" * 62)
    print("第 3 部分：篡改 payload 后验签必然失败")
    print("=" * 62)

    secret = secrets.token_bytes(32)
    payload = {"sub": "10086", "role": "user", "exp": int(time.time()) + 300}
    token = jwt.encode(payload, secret, algorithm="HS256")

    h_b64, p_b64, sig_b64 = token.split(".")

    # 攻击者：不改签名，只把 role 从 user 改成 admin
    fake_payload = {"sub": "10086", "role": "admin", "exp": int(time.time()) + 300}
    fake_p_b64 = b64url_encode(
        json.dumps(fake_payload, separators=(",", ":")).encode()
    )
    forged = f"{h_b64}.{fake_p_b64}.{sig_b64}"

    print(f"\n[伪造后的 token]\n{forged}")
    try:
        jwt.decode(forged, secret, algorithms=["HS256"])
        print("❌ 竟然通过了？说明代码有大问题！")
    except jwt.InvalidSignatureError as e:
        print(f"\n✅ 被拦下了：{type(e).__name__}: {e}")
        print("   原因：payload 变了 → 签名对不上 → 验证失败")

    # 再演示一遍：直接改签名也一样失败
    bad_sig = forged.rsplit(".", 1)[0] + "." + b64url_encode(b"\x00" * 32)
    try:
        jwt.decode(bad_sig, secret, algorithms=["HS256"])
    except jwt.InvalidSignatureError:
        print("✅ 篡改签名同样被拦下")


# ────────────────────────────────────────────────────────────────
# 第 4 部分：过期 / 未生效 / 用错算法 的异常类型
# ────────────────────────────────────────────────────────────────
def demo_claim_validation() -> None:
    print("\n" + "=" * 62)
    print("第 4 部分：各种校验失败的异常类型")
    print("=" * 62)

    secret = secrets.token_bytes(32)
    now = int(time.time())

    cases = {
        "已过期 (exp 在过去)": {
            "sub": "1", "exp": now - 10, "iat": now - 100,
        },
        "尚未生效 (nbf 在未来)": {
            "sub": "1", "exp": now + 300, "nbf": now + 100,
        },
    }

    for name, payload in cases.items():
        token = jwt.encode(payload, secret, algorithm="HS256")
        try:
            jwt.decode(token, secret, algorithms=["HS256"])
            print(f"  {name}: ❌ 意外通过")
        except jwt.ExpiredSignatureError:
            print(f"  {name}: ✅ ExpiredSignatureError")
        except jwt.ImmatureSignatureError:
            print(f"  {name}: ✅ ImmatureSignatureError")
        except jwt.InvalidTokenError as e:
            print(f"  {name}: ✅ {type(e).__name__}")

    # 用 HS256 签、却按 RS256 验证 → 必须失败（防止算法混淆）
    token = jwt.encode({"sub": "1", "exp": now + 300}, secret, algorithm="HS256")
    try:
        jwt.decode(token, secret, algorithms=["RS256"])
        print("  HS256 token 用 RS256 验证: ❌ 意外通过")
    except jwt.InvalidAlgorithmError:
        print("  HS256 token 用 RS256 验证: ✅ InvalidAlgorithmError（算法白名单生效）")

    # clock skew：允许 30 秒偏差，避免分布式时钟漂移导致误判
    token = jwt.encode({"sub": "1", "exp": now - 5}, secret, algorithm="HS256")
    decoded = jwt.decode(token, secret, algorithms=["HS256"], leeway=30)
    print(f"  leeway=30 容忍 5 秒时钟漂移: ✅ 通过 (sub={decoded['sub']})")


def main() -> None:
    demo_parse_structure()
    demo_encode_decode()
    demo_tamper_detected()
    demo_claim_validation()
    print("\n" + "=" * 62)
    print("全部演示完成 ✅  重点记住：签名只保完整性，payload 是明文！")
    print("=" * 62)


if __name__ == "__main__":
    main()
