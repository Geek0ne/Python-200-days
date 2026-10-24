#!/usr/bin/env python3
"""
一键部署后的验收：签一个请求 → 写入 → 读回 → 重放必须被拒。

不使用第三方库（容器外的验收机可能什么都没有）。
退出码 0 = 验收通过。
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
import time
import urllib.error
import urllib.request


def sign(secret: bytes, method: str, path: str, timestamp: int,
         nonce: str, body: bytes) -> str:
    canonical = "\n".join([
        method.upper(), path, str(timestamp), nonce,
        hashlib.sha256(body).hexdigest(),
    ])
    return hmac.new(secret, canonical.encode(), hashlib.sha256).hexdigest()


def request(method: str, url: str, headers: dict[str, str],
            body: bytes = b"") -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body or None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        print(f"❌ 连不上 {url}: {exc}")
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--secret", required=True)
    args = parser.parse_args()
    secret = args.secret.encode()

    checks: list[tuple[str, bool, str]] = []

    status, body = request("GET", f"{args.url}/readyz", {})
    checks.append(("readyz 200", status == 200 and b'"ready"' in body,
                   f"HTTP {status} {body[:80]!r}"))

    path = "/api/v1/records"
    payload = json.dumps({"name": "smoke", "secret": "smoke-" + secrets.token_hex(4)}).encode()
    timestamp = int(time.time())
    nonce = "smoke-" + secrets.token_urlsafe(8)
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Signature": sign(secret, "POST", path, timestamp, nonce, payload),
    }
    status, body = request("POST", f"{args.url}{path}", headers, payload)
    ok_create = status == 201
    record_id = json.loads(body).get("id") if ok_create else None
    checks.append(("签名写入 201", ok_create, f"HTTP {status} {body[:80]!r}"))

    if record_id:
        read_path = f"/api/v1/records/{record_id}"
        nonce2 = "smoke-" + secrets.token_urlsafe(8)
        headers2 = {
            "X-Timestamp": str(timestamp),
            "X-Nonce": nonce2,
            "X-Signature": sign(secret, "GET", read_path, timestamp, nonce2, b""),
        }
        status, body = request("GET", f"{args.url}{read_path}", headers2)
        returned = json.loads(body).get("secret") if status == 200 else None
        expected = json.loads(payload)["secret"]
        checks.append(("解密读回一致", status == 200 and returned == expected,
                       f"HTTP {status} secret={returned!r}"))

        # 原样重放（同一个 nonce）必须 409
        status, body = request("POST", f"{args.url}{path}", headers, payload)
        checks.append(("重放被拒 409", status == 409,
                       f"HTTP {status} {body[:80]!r}"))
    else:
        checks.append(("解密读回一致", False, "没有拿到 record id"))
        checks.append(("重放被拒 409", False, "没有拿到 record id"))

    success = all(passed for _, passed, _ in checks)
    for label, passed, detail in checks:
        print(f"  {'✅' if passed else '❌'} {label:<14} {detail}")
    print("SMOKE PASS" if success else "SMOKE FAIL")
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
