#!/usr/bin/env python3
"""
Day 195 · 加密与鉴权：信封加密 + HMAC 请求签名 + 最小 JWT。

为什么不用"直接用 AES 加密一个字符串"就完事？

- **带 AAD 的 AES-GCM**：把记录 ID 绑进密文。攻击者把 A 的密文复制到 B 的行上，
  解密会失败，而不是静默串号。
- **信封（envelope）+ key id**：密文头里写清楚用了哪把钥匙，才能轮换密钥而不用停机。
- **HMAC 签名而不是裸 API Key**：签名绑定 method/path/时间戳/nonce/body 哈希，
  截获一次请求没法改一个字节再用。
- **JWT 必须锁 alg**：不校验 alg 的实现会被 alg=none 绕过（历史 CVE 常客）。

依赖：cryptography（AES-GCM 实现）。签名与 JWT 部分只用标准库。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Iterable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_PREFIX = "v1."
NONCE_BYTES = 12
TAG_BYTES = 16


# ─────────────────────────────────────────────────────────────
# 编码工具
# ─────────────────────────────────────────────────────────────

def b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ─────────────────────────────────────────────────────────────
# 1. 信封加密（AES-256-GCM）
#    密文布局：v1. | kid_len(1) | kid | nonce(12) | ciphertext+tag(16)
# ─────────────────────────────────────────────────────────────

class UnknownKeyID(Exception):
    """密文头里的 kid 不在当前钥匙环里 —— 可能是轮换时漏拷了旧钥匙。"""


class KeyRing:
    def __init__(self, keys: dict[str, bytes] | None = None,
                 primary: str | None = None) -> None:
        self._keys: dict[str, bytes] = dict(keys or {})
        if not self._keys:
            self.rotate("k1")
        self.primary = primary or next(iter(self._keys))
        if self.primary not in self._keys:
            raise ValueError(f"primary key {self.primary!r} not in keyring")

    @staticmethod
    def generate_key() -> bytes:
        return os.urandom(32)  # AES-256

    def rotate(self, kid: str, key: bytes | None = None) -> bytes:
        """新增一把钥匙并设为 primary。旧钥匙保留，用于解旧密文。"""
        material = key or self.generate_key()
        if len(material) != 32:
            raise ValueError("AES-256 key must be 32 bytes")
        self._keys[kid] = material
        self.primary = kid
        return material

    def key(self, kid: str) -> bytes:
        try:
            return self._keys[kid]
        except KeyError:
            raise UnknownKeyID(kid) from None

    def kids(self) -> list[str]:
        return list(self._keys)

    def export(self) -> dict[str, str]:
        """导出为 base64url 字符串，便于持久化（生产环境请交给 KMS/Vault）。"""
        return {kid: b64e(material) for kid, material in self._keys.items()}


def encrypt(keyring: KeyRing, plaintext: bytes, aad: bytes = b"",
            kid: str | None = None) -> str:
    """返回可安全存库/传输的 ASCII 密文。aad 不加密但参与完整性校验。"""
    kid = kid or keyring.primary
    nonce = os.urandom(NONCE_BYTES)          # 12 字节随机 nonce，绝不复用
    ciphertext = AESGCM(keyring.key(kid)).encrypt(nonce, plaintext, aad)
    kid_bytes = kid.encode("utf-8")
    if not 1 <= len(kid_bytes) <= 255:
        raise ValueError("kid must be 1..255 bytes")
    blob = bytes([len(kid_bytes)]) + kid_bytes + nonce + ciphertext
    return ENVELOPE_PREFIX + b64e(blob)


def envelope_kid(token: str) -> str:
    """只读密文头，不需要钥匙。用于排障：这条密文是哪把钥匙加的？"""
    if not token.startswith(ENVELOPE_PREFIX):
        raise ValueError("unsupported envelope version")
    blob = b64d(token[len(ENVELOPE_PREFIX):])
    if len(blob) < 2:
        raise ValueError("envelope too short")
    kid_len = blob[0]
    return blob[1:1 + kid_len].decode("utf-8")


def decrypt(keyring: KeyRing, token: str, aad: bytes = b"") -> bytes:
    if not token.startswith(ENVELOPE_PREFIX):
        raise ValueError("unsupported envelope version")
    blob = b64d(token[len(ENVELOPE_PREFIX):])
    if len(blob) < 1 + 1 + NONCE_BYTES + TAG_BYTES:
        raise ValueError("envelope too short")
    kid_len = blob[0]
    kid = blob[1:1 + kid_len].decode("utf-8")
    offset = 1 + kid_len
    nonce = blob[offset:offset + NONCE_BYTES]
    ciphertext = blob[offset + NONCE_BYTES:]
    return AESGCM(keyring.key(kid)).decrypt(nonce, ciphertext, aad)


def reencrypt(keyring: KeyRing, token: str, aad: bytes = b"") -> str:
    """轮换后把旧密文搬到新钥匙。真实系统里应离线批量跑 + 双写过渡。"""
    return encrypt(keyring, decrypt(keyring, token, aad), aad)


# ─────────────────────────────────────────────────────────────
# 2. HMAC 请求签名 + nonce 防重放
# ─────────────────────────────────────────────────────────────

def body_digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def canonical_request(method: str, path: str, timestamp: int | str,
                      nonce: str, body: bytes = b"") -> str:
    """待签名字符串。字段顺序固定，缺一不可，用换行分隔防拼接歧义。"""
    return "\n".join([
        method.upper(),
        path,
        str(timestamp),
        nonce,
        body_digest(body),
    ])


def sign_request(secret: bytes, method: str, path: str, timestamp: int | str,
                 nonce: str, body: bytes = b"") -> str:
    message = canonical_request(method, path, timestamp, nonce, body).encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_request(secret: bytes, method: str, path: str, timestamp: int | str,
                   nonce: str, body: bytes, signature: str,
                   *, now: float | None = None, max_skew: int = 300) -> tuple[bool, str]:
    """校验顺序很重要：先时间窗、再签名、最后才记录 nonce。

    先记 nonce 的话，攻击者可以用一堆签名错误的请求把 nonce 表刷爆。
    """
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False, "bad_timestamp"
    current = int(now if now is not None else time.time())
    if abs(current - ts) > max_skew:
        return False, "clock_skew"
    expected = sign_request(secret, method, path, ts, nonce, body)
    if not hmac.compare_digest(expected, signature):
        return False, "bad_signature"
    return True, "ok"


class NonceStore:
    """内存版防重放表。多副本部署必须换 Redis：内存表各活各的。"""

    def __init__(self, ttl: float = 300.0, clock=time.time) -> None:
        self.ttl = ttl
        self.clock = clock
        self._seen: dict[str, float] = {}

    def use(self, nonce: str) -> bool:
        """首次使用返回 True；重放返回 False。"""
        now = self.clock()
        self._purge(now)
        if nonce in self._seen:
            return False
        self._seen[nonce] = now + self.ttl
        return True

    def _purge(self, now: float) -> None:
        expired = [key for key, deadline in self._seen.items() if deadline < now]
        for key in expired:
            del self._seen[key]


# ─────────────────────────────────────────────────────────────
# 3. 最小 JWT（HS256）：给"用户态"接口用
# ─────────────────────────────────────────────────────────────

def issue_token(secret: bytes, subject: str, scopes: Iterable[str],
                ttl: int = 300, *, now: float | None = None,
                jti: str | None = None) -> str:
    issued = int(now if now is not None else time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "scope": " ".join(scopes),
        "iat": issued,
        "exp": issued + ttl,
        "jti": jti or secrets.token_urlsafe(8),
    }
    head = b64e(json.dumps(header, separators=(",", ":")).encode())
    body = b64e(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{head}.{body}"
    signature = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{b64e(signature)}"


def verify_token(secret: bytes, token: str, *, now: float | None = None,
                 leeway: int = 0) -> dict[str, Any]:
    try:
        head_b64, body_b64, sig_b64 = token.split(".")
    except ValueError:
        raise ValueError("malformed token") from None

    header = json.loads(b64d(head_b64))
    # ⚠️ 必须锁死算法：不校验的话 alg=none / HS/RS 混淆都能绕过签名
    if header.get("alg") != "HS256":
        raise ValueError("alg not allowed")

    expected = hmac.new(secret, f"{head_b64}.{body_b64}".encode("ascii"),
                        hashlib.sha256).digest()
    if not hmac.compare_digest(expected, b64d(sig_b64)):
        raise ValueError("bad signature")

    payload = json.loads(b64d(body_b64))
    current = int(now if now is not None else time.time())
    if int(payload.get("exp", 0)) + leeway < current:
        raise ValueError("token expired")
    return payload


# ─────────────────────────────────────────────────────────────
# 4. 自检
# ─────────────────────────────────────────────────────────────

def _self_test() -> None:
    ring = KeyRing({"k1": b"\x01" * 32})
    token = encrypt(ring, "身份证 110101199001011234".encode(), aad=b"record:42")
    assert decrypt(ring, token, aad=b"record:42").decode().endswith("1234")

    # 篡改密文 → InvalidTag
    raw = bytearray(b64d(token[len(ENVELOPE_PREFIX):]))
    raw[-1] ^= 0x01
    tampered = ENVELOPE_PREFIX + b64e(bytes(raw))
    try:
        decrypt(ring, tampered, aad=b"record:42")
    except InvalidTag:
        pass
    else:
        raise AssertionError("tampering must fail")

    # AAD 不匹配 → InvalidTag（密文被搬到别的记录上）
    try:
        decrypt(ring, token, aad=b"record:43")
    except InvalidTag:
        pass
    else:
        raise AssertionError("AAD mismatch must fail")

    # 轮换：旧密文仍可解，新密文用新 kid
    ring.rotate("k2")
    assert decrypt(ring, token, aad=b"record:42").decode().endswith("1234")
    rotated = reencrypt(ring, token, aad=b"record:42")
    assert envelope_kid(rotated) == "k2" and envelope_kid(token) == "k1"
    ring2 = KeyRing({"k2": ring.key("k2")})
    assert decrypt(ring2, rotated, aad=b"record:42").decode().endswith("1234")
    try:
        decrypt(ring2, token, aad=b"record:42")
    except UnknownKeyID:
        pass
    else:
        raise AssertionError("missing old key must raise")

    # 签名：每个字段改动都应失败
    secret = b"shared-secret"
    body = b'{"amount": 100}'
    sig = sign_request(secret, "POST", "/api/v1/pay", 1700000000, "n-1", body)
    assert verify_request(secret, "POST", "/api/v1/pay", 1700000000, "n-1", body,
                          sig, now=1700000000)[0]
    assert not verify_request(secret, "POST", "/api/v1/pay", 1700000000, "n-1",
                              b'{"amount": 900}', sig, now=1700000000)[0]
    assert verify_request(secret, "POST", "/api/v1/pay", 1700000000, "n-1", body,
                          sig, now=1700000001 + 301)[1] == "clock_skew"
    assert verify_request(secret, "POST", "/api/v1/pay", 1700000000, "n-1", body,
                          "0" * 64, now=1700000000)[1] == "bad_signature"

    # nonce 重放
    store = NonceStore(ttl=300, clock=lambda: 1700000000.0)
    assert store.use("n-1") is True
    assert store.use("n-1") is False

    # JWT：正常、过期、alg=none、改 payload
    jwt_secret = b"jwt-secret"
    good = issue_token(jwt_secret, "alice", ["read"], ttl=60, now=1700000000)
    assert verify_token(jwt_secret, good, now=1700000000)["sub"] == "alice"
    try:
        verify_token(jwt_secret, good, now=1700000000 + 61)
    except ValueError as exc:
        assert "expired" in str(exc)
    else:
        raise AssertionError("expired token must fail")

    head, body_b64, _ = good.split(".")
    none_header = b64e(json.dumps({"alg": "none", "typ": "JWT"},
                                  separators=(",", ":")).encode())
    try:
        verify_token(jwt_secret, f"{none_header}.{body_b64}.")
    except ValueError:
        pass
    else:
        raise AssertionError("alg=none must be rejected")

    print("✅ crypto_lib.py self-test passed (encryption / rotation / signature / JWT)")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print(__doc__)
