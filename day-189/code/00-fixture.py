#!/usr/bin/env python3
"""
Day 189 · 00 — 扫描结果夹具生成器（离线可跑）

给 05 端到端流水线准备输入：多天扫描 JSON，包含新增 / 消失 / 服务变化。
格式与真实扫描器导出保持同构，方便替换成 nmap/masscan 的解析结果。

用法：
    python3 00-fixture.py --out /tmp/day189-scans --days 5
    python3 00-fixture.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOSTS = [
    {"ip": "10.20.0.11", "ports": [{"port": 22, "service": "ssh", "banner": "OpenSSH_8.9"},
                                    {"port": 80, "service": "http", "banner": "nginx/1.24.0"}]},
    {"ip": "10.20.0.12", "ports": [{"port": 443, "service": "https", "banner": "nginx/1.24.0"},
                                    {"port": 3306, "service": "mysql", "banner": "8.0.36"}]},
    {"ip": "10.20.0.30", "ports": [{"port": 6379, "service": "redis", "banner": "7.2.4"}]},
]


def scan_docs(days: int = 5, start: datetime | None = None) -> list[dict]:
    start = start or datetime(2026, 10, 15, 2, 0, tzinfo=timezone.utc)
    docs = []
    for d in range(days):
        at = (start + timedelta(days=d)).isoformat(timespec="seconds")
        hosts = json.loads(json.dumps(HOSTS))  # 深拷贝

        if d >= 2:
            # 第 3 天起：新开 8080，22 端口 SSH 版本升级
            hosts[0]["ports"].append({"port": 8080, "service": "http", "banner": "tomcat/9.0"})
            hosts[0]["ports"][0]["banner"] = "OpenSSH_9.6"
        if d >= 3:
            # 第 4 天起：6379 连续消失（先 missing，后 gone）
            hosts[2]["ports"] = []
        docs.append({"scanned_at": at, "label": f"fixture-d{d+1}", "hosts": hosts})
    return docs


def self_test() -> int:
    docs = scan_docs(5)
    assert len(docs) == 5
    assert any(p["port"] == 8080 for p in docs[2]["hosts"][0]["ports"])
    assert docs[3]["hosts"][2]["ports"] == []
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        for i, doc in enumerate(docs):
            (out / f"scan-{i+1}.json").write_text(
                json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        assert len(list(out.glob("*.json"))) == 5
    print("✅ 00 self-test 通过：5 天夹具包含新增端口与消失资产")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="扫描结果夹具生成器")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--out", default="out/day189-scans")
    ap.add_argument("--days", type=int, default=5)
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for i, doc in enumerate(scan_docs(args.days)):
        path = out / f"scan-{i+1}.json"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"写入 {path}（{len(doc['hosts'])} 台主机）")
    print(f"共 {args.days} 份扫描结果 → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
