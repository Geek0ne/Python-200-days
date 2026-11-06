#!/usr/bin/env python3
"""
Day 195 · 03 API 鉴权：HMAC 签名、防重放、JWT 的常见坑

运行：
    python3 03-api-auth.py               # 打印 10 个请求的判定结果
    python3 03-api-auth.py --self-test   # 离线自检

核心观点：
- **API Key 放在 header 里 = 一把永久万能钥匙**。泄露一次，攻击者可以读、
  可以改、可以重放到天荒地老。签名则把"这一次请求"钉死。
- 签名必须覆盖 body 哈希，否则攻击者能改金额但保留签名。
- 时间窗 + nonce 缺一不可：只有时间窗，攻击者能在 5 分钟内重放；
  只有 nonce，攻击者能攒一堆旧 nonce 慢慢试。
- JWT 不是"更安全的 session"，它只是"签名的 JSON"。不校验 alg 等于没签。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from crypto_lib import (  # noqa: E402
    NonceStore, issue_token, sign_request, verify_request, verify_token,
)

SECRET = b"demo-shared-secret-do-not-reuse"
JWT_SECRET = b"demo-jwt-secret"


def header_get(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


class RequestGate:
    """模拟服务端鉴权中间件。返回 (http_status, error_code)。"""

    def __init__(self, secret: bytes = SECRET, skew: int = 300) -> None:
        self.secret = secret
        self.skew = skew
        self.nonces = NonceStore(ttl=skew)

    def check(self, method: str, path: str, headers: dict[str, str],
              body: bytes = b"", now: float | None = None) -> tuple[int, str]:
        timestamp = header_get(headers, "X-Timestamp")
        nonce = header_get(headers, "X-Nonce")
        signature = header_get(headers, "X-Signature")
        if not (timestamp and nonce and signature):
            return 401, "missing_auth_headers"

        ok, reason = verify_request(
            self.secret, method, path, timestamp, nonce, body, signature,
            now=now, max_skew=self.skew,
        )
        if not ok:
            return 401, reason
        if not self.nonces.use(nonce):
            return 409, "replayed_nonce"
        return 200, "ok"


def signed(method: str, path: str, body: bytes = b"", timestamp: int | None = None,
           nonce: str = "nonce-1", secret: bytes = SECRET,
           now: int | None = None) -> dict[str, str]:
    """生成一组签名头。now 是 timestamp 的别名，方便演示代码读起来顺。"""
    resolved = int(now if now is not None else (timestamp if timestamp is not None
                                                else 1_700_000_000))
    signature = sign_request(secret, method, path, resolved, nonce, body)
    return {
        "X-Timestamp": str(resolved),
        "X-Nonce": nonce,
        "X-Signature": signature,
        "Content-Type": "application/json",
    }


def demo_gate() -> None:
    print("=" * 72)
    print("演示 1：同一个接口，七种请求的判定")
    print("=" * 72)
    gate = RequestGate()
    path = "/api/v1/transfers"
    body = b'{"amount":100,"to":"alice"}'
    now = 1_700_000_000

    cases: list[tuple[str, str, str, dict[str, str], bytes, int]] = []

    cases.append(("正常请求", "POST", path, signed("POST", path, body, now=now, nonce="n-1"),
                  body, now))
    cases.append(("原样重放（nonce 复用）", "POST", path,
                  signed("POST", path, body, now=now, nonce="n-1"), body, now))
    cases.append(("改金额但复用签名", "POST", path,
                  signed("POST", path, body, now=now, nonce="n-2"),
                  b'{"amount":999999,"to":"alice"}', now))
    cases.append(("时间戳过期 6 分钟", "POST", path,
                  signed("POST", path, body, timestamp=now - 361, nonce="n-3"),
                  body, now))
    cases.append(("时间戳来自未来 10 分钟", "POST", path,
                  signed("POST", path, body, timestamp=now + 600, nonce="n-4"),
                  body, now))
    cases.append(("错误的共享密钥", "POST", path,
                  signed("POST", path, body, now=now, nonce="n-5", secret=b"wrong"),
                  body, now))
    cases.append(("缺少 X-Signature", "POST", path,
                  {k: v for k, v in signed("POST", path, body, now=now, nonce="n-6").items()
                   if k != "X-Signature"}, body, now))
    cases.append(("把 GET 的签名用于 POST", "POST", path,
                  signed("GET", path, body, now=now, nonce="n-7"), body, now))

    print(f"  {'场景':<24}{'状态':>6}  {'原因':<22}")
    print("  " + "-" * 60)
    for label, method, request_path, headers, request_body, ts in cases:
        status, reason = gate.check(method, request_path, headers, request_body, now=ts)
        mark = "✅" if status == 200 else "🚫"
        print(f"  {label:<24}{status:>6}  {reason:<22}{mark}")

    print("\n  注意第 2 行：签名完全有效，但 nonce 已经用过 → 409。")
    print("  只验签不验 nonce，等于允许攻击者在时间窗内无限重放。")


def demo_jwt() -> None:
    print("\n" + "=" * 72)
    print("演示 2：JWT —— 过期、篡改、alg=none")
    print("=" * 72)
    now = 1_700_000_000
    token = issue_token(JWT_SECRET, "alice", ["read", "write"], ttl=300, now=now)
    print(f"  签发的 token（前 60 字符）: {token[:60]}...")

    checks: list[tuple[str, str, float]] = [
        ("正常校验", token, now + 10),
        ("过期 1 秒", token, now + 301),
        ("宽限 5 秒内", token, now + 305),
    ]
    import base64, json

    def b64e(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    head, payload, _ = token.split(".")
    forged_payload = b64e(json.dumps({
        "sub": "alice", "scope": "admin", "iat": now, "exp": now + 9999,
    }, separators=(",", ":")).encode())
    checks.append(("篡改 payload 提权", f"{head}.{forged_payload}.{token.split('.')[2]}", now + 10))

    none_head = b64e(json.dumps({"alg": "none", "typ": "JWT"},
                                separators=(",", ":")).encode())
    checks.append(("alg=none 绕过", f"{none_head}.{payload}.", now + 10))

    print(f"  {'场景':<22}{'结果':<10}原因")
    print("  " + "-" * 60)
    for label, candidate, moment in checks:
        leeway = 5 if label == "宽限 5 秒内" else 0
        try:
            claims = verify_token(JWT_SECRET, candidate, now=moment, leeway=leeway)
            print(f"  {label:<22}{'通过 ✅':<10}sub={claims['sub']} scope={claims.get('scope')}")
        except ValueError as exc:
            print(f"  {label:<22}{'拒绝 🚫':<10}{exc}")

    print("\n  第 4、5 行是最常见的两个洞：不校验签名覆盖范围、不锁 alg。")
    print("  另外：JWT 无法主动吊销，短 TTL + refresh token 是标配。")


def demo_scope() -> None:
    print("\n" + "=" * 72)
    print("演示 3：scope 校验 —— 只读 token 不能转账")
    print("=" * 72)
    now = 1_700_000_000
    read_only = issue_token(JWT_SECRET, "bob", ["records:read"], ttl=300, now=now)
    claims = verify_token(JWT_SECRET, read_only, now=now)
    granted = set(claims.get("scope", "").split())
    required = "records:write"
    print(f"  token scopes = {sorted(granted)}")
    print(f"  需要 {required} → {'允许' if required in granted else '403 Forbidden 🚫'}")
    print("  鉴权 = 认证（你是谁）+ 授权（你能干什么），两件事要分开写。")


def self_test() -> None:
    gate = RequestGate()
    now = 1_700_000_000
    body = b'{"amount":1}'
    headers = signed("POST", "/pay", body, now=now, nonce="sc-1")
    assert gate.check("POST", "/pay", headers, body, now=now) == (200, "ok")
    assert gate.check("POST", "/pay", headers, body, now=now) == (409, "replayed_nonce")
    assert gate.check("POST", "/pay", headers, b'{"amount":2}', now=now)[1] == "bad_signature"
    stale = signed("POST", "/pay", body, timestamp=now - 301, nonce="sc-2")
    assert gate.check("POST", "/pay", stale, body, now=now) == (401, "clock_skew")

    token = issue_token(JWT_SECRET, "u", ["a"], ttl=10, now=now)
    assert verify_token(JWT_SECRET, token, now=now)["sub"] == "u"
    try:
        verify_token(JWT_SECRET, token, now=now + 11)
    except ValueError:
        pass
    else:
        raise AssertionError("expired token must fail")
    print("✅ 03 self-test passed")


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return
    demo_gate()
    demo_jwt()
    demo_scope()


if __name__ == "__main__":
    main()
