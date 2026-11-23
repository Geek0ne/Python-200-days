#!/usr/bin/env python3
"""
Day 188 · 02 — 进阶用法：反射型 XSS 检测（上下文感知）

朴素做法：在响应里搜 "alert(" —— 会把"已经转义但文本仍在"的页面误判为漏洞。
正确做法：检查**原始 payload 是否未被转义地出现在 HTML 中**。

检测流程：
  1. 生成唯一标记 payload：<svg/onload=alert('LPX<random>')>
  2. 请求 /search?q=<payload>
  3. 判定：
     - body 中含完整原始 payload，且 &lt;svg 不存在 → 未转义 → vulnerable
     - body 中含 &lt;svg...&gt; → 已转义 → safe
  4. 对 /safe-search 做同样请求，必须判 safe（对照组）

为什么用唯一标记：
  页面本身可能就有 <svg> 或 alert 字样，唯一标记能避免把模板内容当成回显。

用法：
  python3 02-xss-detect.py --base-url http://127.0.0.1:18081
  python3 02-xss-detect.py --self-test
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_lab():
    spec = importlib.util.spec_from_file_location("vuln_lab", HERE / "00-vuln-lab.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "LearnPython-XSSScan/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:
        return 0, f"REQUEST_FAILED: {exc}"


def make_payload() -> tuple[str, str]:
    token = "LPX" + "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(8))
    return token, f"<svg/onload=alert('{token}')>"


def probe(base_url: str, path: str, payload: str, timeout: float = 3.0) -> dict:
    url = f"{base_url.rstrip('/')}{path}?q={urllib.parse.quote(payload)}"
    status, body = http_get(url, timeout)
    raw_reflection = payload in body
    escaped_reflection = "&lt;svg" in body.lower()
    return {
        "path": path,
        "url": url,
        "status": status,
        "raw_reflection": raw_reflection,
        "escaped_reflection": escaped_reflection,
        "vulnerable": bool(raw_reflection and not escaped_reflection),
        "body_excerpt": body[:300],
    }


def scan(base_url: str, timeout: float = 3.0) -> dict:
    token, payload = make_payload()
    vulnerable_ep = probe(base_url, "/search", payload, timeout)
    control_ep = probe(base_url, "/safe-search", payload, timeout)
    findings = []
    if vulnerable_ep["vulnerable"]:
        findings.append({
            "type": "reflected-xss",
            "endpoint": "/search",
            "payload": payload,
            "evidence": f"原始 payload 未转义回显（标记 {token}）",
            "confidence": "high",
        })
    false_positive_guard = not control_ep["vulnerable"]
    return {
        "target": base_url,
        "payload": payload,
        "token": token,
        "vulnerable": bool(findings),
        "findings": findings,
        "control_safe": false_positive_guard,
        "control": {k: control_ep[k] for k in ("path", "status", "raw_reflection", "escaped_reflection")},
        "vulnerable_endpoint": {k: vulnerable_ep[k] for k in ("path", "status", "raw_reflection", "escaped_reflection")},
    }


def self_test() -> int:
    lab = load_lab()
    server, _, base_url = lab.serve(port=0)
    try:
        result = scan(base_url)
        assert result["vulnerable"] is True, result
        assert result["control_safe"] is True, result
        assert result["findings"][0]["endpoint"] == "/search", result
        assert result["control"]["escaped_reflection"] is True, result
        print("✅ self-test passed: /search 检出反射型 XSS，/safe-search 正确判 safe")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        server.shutdown()
        server.server_close()
        Path(server.db_path).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="反射型 XSS 检测（本地/授权目标）")
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--json", help="结果写入 JSON")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    result = scan(args.base_url, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[*] 已写入 {args.json}")
    return 0 if result["vulnerable"] else 1


if __name__ == "__main__":
    sys.exit(main())

