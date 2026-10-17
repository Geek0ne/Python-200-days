#!/usr/bin/env python3
"""
Day 188 · 04 — 性能与避坑：误报演练（为什么"搜关键字"不可靠）

两个判定器对同一组响应的结论：

  naive   : body 里出现 "alert" 就算 XSS
  precise : 原始 payload 未被转义地出现才算 XSS

对 /search（有漏洞）和 /safe-search（已转义）分别跑：
  · naive 会把两个都判成漏洞 → 1 个真阳性 + 1 个假阳性
  · precise 只判 /search → 0 假阳性

这说明：**转义不会删掉文本，只会改变字符表示**。
安全扫描器必须看"上下文是否可执行"，而不是"关键字是否出现"。

用法：
  python3 04-false-positive-drill.py
  python3 04-false-positive-drill.py --self-test
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import string
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_lab():
    spec = importlib.util.spec_from_file_location("vuln_lab", HERE / "00-vuln-lab.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def http_get(url: str) -> tuple[int, str]:
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "LearnPython-FPDrill/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def naive_judge(body: str) -> bool:
    return "alert" in body.lower()


def precise_judge(body: str, payload: str) -> bool:
    return payload in body and "&lt;svg" not in body.lower()


def run(base_url: str) -> dict:
    token = "LPX" + "".join(random.choice(string.ascii_lowercase) for _ in range(6))
    payload = f"<svg/onload=alert('{token}')>"
    rows = []
    for path in ("/search", "/safe-search"):
        url = f"{base_url.rstrip('/')}{path}?q={urllib.parse.quote(payload)}"
        status, body = http_get(url)
        rows.append({
            "path": path,
            "status": status,
            "naive_vulnerable": naive_judge(body),
            "precise_vulnerable": precise_judge(body, payload),
            "contains_alert": "alert" in body.lower(),
            "contains_raw_payload": payload in body,
            "contains_escaped": "&lt;svg" in body.lower(),
        })
    naive_count = sum(r["naive_vulnerable"] for r in rows)
    precise_count = sum(r["precise_vulnerable"] for r in rows)
    return {
        "payload": payload,
        "rows": rows,
        "naive_flagged": naive_count,
        "precise_flagged": precise_count,
        "false_positives_naive": naive_count - 1,   # /search 是真阳性
        "false_positives_precise": precise_count - 1,
    }


def self_test() -> int:
    lab = load_lab()
    server, _, base_url = lab.serve(port=0)
    try:
        result = run(base_url)
        assert result["naive_flagged"] == 2, result
        assert result["precise_flagged"] == 1, result
        assert result["false_positives_naive"] == 1, result
        assert result["false_positives_precise"] == 0, result
        row_safe = next(r for r in result["rows"] if r["path"] == "/safe-search")
        assert row_safe["contains_alert"] is True, row_safe
        assert row_safe["contains_escaped"] is True, row_safe
        print("✅ self-test passed: naive 2 命中/1 误报，precise 1 命中/0 误报")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        Path(server.db_path).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    lab = load_lab()
    server, _, base_url = lab.serve(port=0)
    try:
        result = run(base_url)
    finally:
        server.shutdown()
        server.server_close()
        Path(server.db_path).unlink(missing_ok=True)

    print(f"payload: {result['payload']}")
    print(f"{'endpoint':<16}{'naive':>8}{'precise':>9}{'has_alert':>11}{'raw':>6}{'escaped':>9}")
    for r in result["rows"]:
        print(f"{r['path']:<16}{str(r['naive_vulnerable']):>8}{str(r['precise_vulnerable']):>9}"
              f"{str(r['contains_alert']):>11}{str(r['contains_raw_payload']):>6}{str(r['contains_escaped']):>9}")
    print(json.dumps({k: result[k] for k in
                      ("naive_flagged", "precise_flagged",
                       "false_positives_naive", "false_positives_precise")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

