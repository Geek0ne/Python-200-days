#!/usr/bin/env python3
"""
Day 188 · 01 — 基础用法：SQL 注入自动检测（报错型 + 布尔型）

检测思路（只做"是否存在"，不拖库）：
  1. 基线：请求 id=1，确认页面正常、包含已知产品名
  2. 报错型：依次注入 ' / " / ) / '-- / AND 1=1
     若响应出现数据库错误特征（SQL error / unrecognized token / syntax error），
     说明输入进入了 SQL 解析器
  3. 布尔型：比较 "1 AND 1=1" 与 "1 AND 1=2"
     前者正常、后者无结果 → 条件表达式被执行
  4. 输出置信度：报错型 high，布尔型 high（两者都有则 critical）

边界：
  · 只对本地靶场或书面授权目标使用
  · 不包含 UNION 拖库、时间盲注、堆叠查询
  · 检测到即停止，不做进一步利用

用法：
  python3 01-sqli-detect.py --base-url http://127.0.0.1:18081
  python3 01-sqli-detect.py --self-test
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ERROR_SIGNATURES = [
    "sql error",
    "unrecognized token",
    "syntax error",
    "sqlite3.",
    "operationalerror",
    "you have an error in your sql syntax",
    "quoted string not properly terminated",
]
ERROR_PAYLOADS = ["1'", '1"', "1)", "1'--", "1 AND 1=1"]
TRUE_PAYLOAD = "1 AND 1=1"
FALSE_PAYLOAD = "1 AND 1=2"
PRODUCT_MARKER = "Mechanical Keyboard"


def load_lab():
    spec = importlib.util.spec_from_file_location("vuln_lab", HERE / "00-vuln-lab.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def http_get(url: str, timeout: float = 3.0) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "LearnPython-SQLiScan/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # 连接失败也返回可诊断信息
        return 0, f"REQUEST_FAILED: {exc}"


def inject_url(base_url: str, payload: str) -> str:
    return f"{base_url.rstrip('/')}/product?id={urllib.parse.quote(payload)}"


def scan(base_url: str, timeout: float = 3.0) -> dict:
    baseline_status, baseline_body = http_get(inject_url(base_url, "1"), timeout)
    baseline_ok = baseline_status == 200 and PRODUCT_MARKER.lower() in baseline_body.lower()

    findings = []

    for payload in ERROR_PAYLOADS:
        status, body = http_get(inject_url(base_url, payload), timeout)
        hit = next((sig for sig in ERROR_SIGNATURES if sig in body.lower()), None)
        if hit:
            findings.append({
                "type": "error-based",
                "payload": payload,
                "evidence": hit,
                "status": status,
                "confidence": "high",
            })

    true_status, true_body = http_get(inject_url(base_url, TRUE_PAYLOAD), timeout)
    false_status, false_body = http_get(inject_url(base_url, FALSE_PAYLOAD), timeout)
    true_ok = true_status == 200 and PRODUCT_MARKER.lower() in true_body.lower()
    false_empty = not (false_status == 200 and PRODUCT_MARKER.lower() in false_body.lower())
    if true_ok and false_empty:
        findings.append({
            "type": "boolean-based",
            "payload": f"{TRUE_PAYLOAD} vs {FALSE_PAYLOAD}",
            "evidence": "true 条件返回产品，false 条件返回空",
            "status": true_status,
            "confidence": "high",
        })

    return {
        "target": f"{base_url.rstrip('/')}/product?id=1",
        "baseline_ok": baseline_ok,
        "baseline_status": baseline_status,
        "vulnerable": bool(findings),
        "findings": findings,
        "payloads_sent": len(ERROR_PAYLOADS) + 2,
    }


def self_test() -> int:
    lab = load_lab()
    server, _, base_url = lab.serve(port=0)
    try:
        result = scan(base_url)
        types = {f["type"] for f in result["findings"]}
        assert "error-based" in types, result
        assert "boolean-based" in types, result
        assert result["vulnerable"] is True, result
        print("✅ self-test passed: 报错型 + 布尔型 SQLi 均检出")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        server.shutdown()
        server.server_close()
        Path(server.db_path).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLi 检测（本地/授权目标）")
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

