#!/usr/bin/env python3
"""
Day 188 · 03 — 实战：组合漏洞扫描报告

把 SQLi 与 XSS 两个检测器串成一份可交付的报告：
  · 统一 findings 结构
  · 计算严重级别（critical / high / none）
  · 输出 JSON（给机器）和 Markdown（给人）

严重级别规则（本课简化版）：
  SQLi + XSS 都有        → critical
  只有 SQLi              → high（可读库）
  只有 XSS               → high（可打管理员会话）
  都没有                 → none

用法：
  python3 03-security-scan-report.py --base-url http://127.0.0.1:18081 \
      --json /tmp/scan.json --markdown /tmp/scan.md
  python3 03-security-scan-report.py --self-test
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sqli = load("sqli_detect", "01-sqli-detect.py")
xss = load("xss_detect", "02-xss-detect.py")


def scan_all(base_url: str, timeout: float = 3.0) -> dict:
    sqli_result = sqli.scan(base_url, timeout)
    xss_result = xss.scan(base_url, timeout)

    findings = []
    for f in sqli_result["findings"]:
        findings.append({"category": "SQLi", "severity": "high", **f})
    for f in xss_result["findings"]:
        findings.append({"category": "XSS", "severity": "high", **f})

    if sqli_result["vulnerable"] and xss_result["vulnerable"]:
        severity = "critical"
    elif findings:
        severity = "high"
    else:
        severity = "none"

    return {
        "target": base_url,
        "scanned_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "severity": severity,
        "finding_count": len(findings),
        "findings": findings,
        "sqli": sqli_result,
        "xss": xss_result,
    }


def to_markdown(result: dict) -> str:
    lines = [
        "# 漏洞扫描报告",
        "",
        f"- 目标：{result['target']}",
        f"- 时间：{result['scanned_at']}",
        f"- 严重级别：**{result['severity']}**",
        f"- 发现数：{result['finding_count']}",
        "",
        "## Findings",
        "",
        "| # | 类别 | 类型 | 证据 | 置信度 |",
        "|---:|---|---|---|---|",
    ]
    for i, f in enumerate(result["findings"], 1):
        evidence = str(f.get("evidence", "")).replace("|", "\\|")
        lines.append(f"| {i} | {f['category']} | {f['type']} | {evidence} | {f['confidence']} |")
    if not result["findings"]:
        lines.append("| - | - | 未发现 | - | - |")

    lines += [
        "",
        "## 复现命令",
        "",
        "```bash",
        f"python3 01-sqli-detect.py --base-url {result['target']}",
        f"python3 02-xss-detect.py --base-url {result['target']}",
        "```",
        "",
        "> 本报告仅用于授权测试。检测到漏洞后应停止进一步利用并通知资产所有者。",
    ]
    return "\n".join(lines) + "\n"


def self_test() -> int:
    lab = load("vuln_lab", "00-vuln-lab.py")
    server, _, base_url = lab.serve(port=0)
    try:
        result = scan_all(base_url)
        assert result["severity"] == "critical", result
        assert result["finding_count"] >= 2, result
        categories = {f["category"] for f in result["findings"]}
        assert categories == {"SQLi", "XSS"}, categories
        md = to_markdown(result)
        assert "严重级别：**critical**" in md, md
        assert "SQLi" in md and "XSS" in md, md
        print("✅ self-test passed: 组合扫描 → 严重级别 → Markdown 报告 全链路正确")
        print(f"   severity={result['severity']}, findings={result['finding_count']}")
        print("   markdown 前 6 行:")
        print("\n".join(md.splitlines()[:6]))
        return 0
    finally:
        server.shutdown()
        server.server_close()
        Path(server.db_path).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="组合漏洞扫描报告")
    parser.add_argument("--base-url", default="http://127.0.0.1:18081")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--json", help="JSON 输出路径")
    parser.add_argument("--markdown", help="Markdown 输出路径")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    result = scan_all(args.base_url, args.timeout)
    print(json.dumps({k: result[k] for k in ("target", "severity", "finding_count", "findings")},
                     ensure_ascii=False, indent=2))
    if args.json:
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[*] JSON 已写入 {args.json}")
    if args.markdown:
        Path(args.markdown).write_text(to_markdown(result), encoding="utf-8")
        print(f"[*] Markdown 已写入 {args.markdown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

