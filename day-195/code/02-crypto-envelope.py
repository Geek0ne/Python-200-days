#!/usr/bin/env python3
"""
Day 195 · 02 信封加密：AES-GCM、AAD、密钥轮换与性能

运行：
    python3 02-crypto-envelope.py               # 演示 + 50MB 基准
    python3 02-crypto-envelope.py --self-test   # 离线自检

为什么值得学这一层，而不是"存库前 base64 一下"：
- base64 是可逆编码，不是加密；
- 只加密不认证，攻击者能改密文让程序解出乱七八糟的东西（padding oracle 的温床）；
- AES-GCM 一次解决"机密性 + 完整性"，但 nonce 复用会直接泄露明文异或值；
- 密钥要能轮换，否则一次泄露 = 全量数据永久裸奔。
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cryptography.exceptions import InvalidTag  # noqa: E402

from crypto_lib import (  # noqa: E402
    ENVELOPE_PREFIX, KeyRing, UnknownKeyID, b64d, b64e, decrypt, encrypt,
    envelope_kid, reencrypt,
)


def section(title: str) -> None:
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


def demo_basic() -> None:
    section("演示 1：一条 PII 记录 —— 加密、落库形态、解密")
    ring = KeyRing({"k1": KeyRing.generate_key()})
    record_id = "user-42"
    plaintext = "姓名=张三; 手机=13800138000; 身份证=110101199001011234".encode()

    # AAD 绑定记录 ID：密文被复制到别的行上会解不开
    token = encrypt(ring, plaintext, aad=record_id.encode())
    print(f"  密文（存库/传输形态，{len(token)} 字符）:")
    print(f"  {token[:96]}...")
    print(f"  密文头里的 kid: {envelope_kid(token)}")
    print(f"  解密结果: {decrypt(ring, token, aad=record_id.encode()).decode()}")

    # 演示：把 user-42 的密文复制到 user-43 这一行
    try:
        decrypt(ring, token, aad=b"user-43")
    except InvalidTag:
        print("  ✅ 换一个 AAD 解密失败：密文无法被搬到别的记录上")


def demo_tamper() -> None:
    section("演示 2：篡改一个字节 —— GCM 的认证标签会拦住")
    ring = KeyRing({"k1": KeyRing.generate_key()})
    token = encrypt(ring, b"balance=1000", aad=b"acct-1")
    raw = bytearray(b64d(token[len(ENVELOPE_PREFIX):]))
    position = len(raw) - 1          # 最后一个字节落在认证标签里
    original = raw[position]
    raw[position] ^= 0x01
    flipped = ENVELOPE_PREFIX + b64e(bytes(raw))
    print(f"  原始密文: {token}")
    print(f"  篡改位置: 倒数第 1 字节  0x{original:02x} → 0x{raw[position]:02x}")
    try:
        decrypt(ring, flipped, aad=b"acct-1")
    except InvalidTag:
        print("  ✅ 解密抛 InvalidTag —— 程序不会拿着被篡改的数据继续跑")
    else:
        raise AssertionError("tampering was not detected")


def demo_rotation() -> None:
    section("演示 3：密钥轮换 —— 旧密文还能不能解？")
    ring = KeyRing({"k1": KeyRing.generate_key()})
    old_tokens = [encrypt(ring, f"secret-{i}".encode(), aad=f"row-{i}".encode())
                  for i in range(3)]
    print(f"  轮换前 primary={ring.primary}，密文 kid 全是 {envelope_kid(old_tokens[0])}")

    ring.rotate("k2")
    print(f"  轮换后 primary={ring.primary}，钥匙环含 {ring.kids()}")
    new_token = encrypt(ring, b"secret-new", aad=b"row-new")
    print(f"  新密文 kid={envelope_kid(new_token)}（自动用新钥匙）")
    print(f"  旧密文仍可解: {decrypt(ring, old_tokens[0], aad=b'row-0')!r}")

    migrated = [reencrypt(ring, token, aad=f"row-{i}".encode())
                for i, token in enumerate(old_tokens)]
    print(f"  批量重加密后 kid: {[envelope_kid(t) for t in migrated]}")

    # 只带新钥匙的副本（模拟新环境）解旧密文 → UnknownKeyID，暴露"漏拷旧钥匙"
    fresh = KeyRing({"k2": ring.key("k2")})
    try:
        decrypt(fresh, old_tokens[0])
    except UnknownKeyID as exc:
        print(f"  ✅ 缺少旧钥匙时明确报 UnknownKeyID({exc})，而不是静默返回垃圾")


def demo_benchmark() -> None:
    section("演示 4：AES-256-GCM 实测吞吐（本机 CPU，单线程）")
    ring = KeyRing({"k1": KeyRing.generate_key()})

    big = os.urandom(1024 * 1024)      # 1 MiB
    rounds = 30
    encrypt_times, decrypt_times = [], []
    token = encrypt(ring, big, aad=b"bench")
    for _ in range(rounds):
        start = time.perf_counter()
        token = encrypt(ring, big, aad=b"bench")
        encrypt_times.append(time.perf_counter() - start)
        start = time.perf_counter()
        assert decrypt(ring, token, aad=b"bench") == big
        decrypt_times.append(time.perf_counter() - start)

    enc_mbps = (len(big) / (1024 * 1024)) / statistics.median(encrypt_times)
    dec_mbps = (len(big) / (1024 * 1024)) / statistics.median(decrypt_times)
    print(f"  负载 1 MiB × {rounds} 次，取中位数")
    print(f"  加密: {statistics.median(encrypt_times) * 1000:.2f} ms/次  ≈ {enc_mbps:.0f} MiB/s")
    print(f"  解密: {statistics.median(decrypt_times) * 1000:.2f} ms/次  ≈ {dec_mbps:.0f} MiB/s")

    small = b'{"phone":"13800138000","id_card":"110101199001011234"}'
    small_rounds = 5000
    start = time.perf_counter()
    for _ in range(small_rounds):
        decrypt(ring, encrypt(ring, small, aad=b"u1"), aad=b"u1")
    per_op = (time.perf_counter() - start) / small_rounds
    print(f"  小记录（{len(small)} B）加解密: {per_op * 1e6:.1f} µs/次 "
          f"≈ {1 / per_op:,.0f} 次/秒")
    print("  结论：GCM 吞吐通常高于磁盘和网络，加密不是性能瓶颈；")
    print("        真正的成本在密钥管理（KMS 调用）和轮换重加密的窗口。")


def self_test() -> None:
    ring = KeyRing({"k1": b"\x02" * 32})
    token = encrypt(ring, b"hello", aad=b"a")
    assert decrypt(ring, token, aad=b"a") == b"hello"
    try:
        decrypt(ring, token, aad=b"b")
    except InvalidTag:
        pass
    else:
        raise AssertionError("AAD must be authenticated")
    ring.rotate("k2")
    assert envelope_kid(encrypt(ring, b"x")) == "k2"
    assert decrypt(ring, token, aad=b"a") == b"hello"
    print("✅ 02 self-test passed")


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return
    demo_basic()
    demo_tamper()
    demo_rotation()
    demo_benchmark()


if __name__ == "__main__":
    main()
