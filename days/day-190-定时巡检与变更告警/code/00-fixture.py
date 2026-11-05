#!/usr/bin/env python3
"""
Day 190 · 00 — 夹具：两次资产扫描快照 + 差异 + 严重级映射

调度与告警要有东西可跑。这个脚本用固定种子造两份资产快照（t0 / t1），
模拟真实世界的三种变化：新端口暴露、服务下线、高危端口被打开。

  python3 00-fixture.py --emit /tmp/d190-fix
  python3 00-fixture.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys

CRITICAL_PORTS = {3389: "RDP", 445: "SMB", 6379: "Redis", 9200: "Elasticsearch", 2375: "Docker API"}
HIGH_PORTS = {22: "SSH", 3306: "MySQL", 5432: "PostgreSQL", 8080: "HTTP-alt"}
SERVICES = {80: "http", 443: "https", 22: "ssh", 8080: "http-alt", 8443: "https-alt"}


def build_hosts(n: int = 30) -> list[str]:
    return [f"10.0.{(i // 250) + 1}.{(i % 250) + 10}" for i in range(n)]


def baseline() -> list[dict]:
    """t0：30 台主机，每台开 80/443，外加若干高危端口（模拟遗留系统）。"""
    assets = []
    for idx, host in enumerate(build_hosts(30)):
        assets.append({"ip": host, "port": 80, "service": "http"})
        assets.append({"ip": host, "port": 443, "service": "https"})
        if idx % 6 == 0:
            assets.append({"ip": host, "port": 22, "service": "ssh"})
        if idx % 10 == 0:
            assets.append({"ip": host, "port": 3306, "service": "mysql"})
    return assets


def evolved() -> list[dict]:
    """t1：3 台新主机上线、2 个服务下线、1 台机器的 RDP 被打开（真正的高危事件）。"""
    assets = [a for a in baseline() if not (a["ip"] == "10.0.1.11" and a["port"] == 443)]
    assets = [a for a in assets if not (a["ip"] == "10.0.1.12" and a["port"] == 80)]
    for host in ("10.0.1.40", "10.0.1.41", "10.0.1.42"):
        assets.append({"ip": host, "port": 8080, "service": "http-alt"})
    assets.append({"ip": "10.0.1.10", "port": 3389, "service": "rdp"})
    assets.append({"ip": "10.0.1.30", "port": 6379, "service": "redis"})
    return sorted(assets, key=lambda a: (a["ip"], a["port"]))


def severity_for(port: int) -> str:
    if port in CRITICAL_PORTS:
        return "critical"
    if port in HIGH_PORTS:
        return "warning"
    return "info"


def diff(old: list[dict], new: list[dict]) -> dict:
    key = lambda a: (a["ip"], a["port"])
    old_map = {key(a): a for a in old}
    new_map = {key(a): a for a in new}
    appeared = [new_map[k] for k in sorted(new_map.keys() - old_map.keys())]
    missing = [old_map[k] for k in sorted(old_map.keys() - new_map.keys())]
    changed = []
    for k in sorted(new_map.keys() & old_map.keys()):
        if new_map[k].get("service") != old_map[k].get("service"):
            changed.append({"ip": k[0], "port": k[1],
                            "from": old_map[k].get("service"), "to": new_map[k].get("service")})
    for item in appeared + missing:
        item["severity"] = severity_for(item["port"])
    return {"appeared": appeared, "missing": missing, "changed": changed}


def emit(outdir: str) -> dict:
    os.makedirs(outdir, exist_ok=True)
    old, new = baseline(), evolved()
    d = diff(old, new)
    payload = {"t0": old, "t1": new, "diff": d}
    with open(os.path.join(outdir, "snapshots.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return payload


def self_test() -> int:
    old, new = baseline(), evolved()
    d = diff(old, new)
    crit = [a for a in d["appeared"] if a["severity"] == "critical"]
    checks = [
        # 30 台 × (80,443) = 60，再加 5 台 22 端口、3 台 3306 = 68
        ("基线规模", len(old) == 68, f"assets={len(old)}"),
        # 68 - 2 下线 + 3 新主机 + 2 高危 = 71
        ("演化后规模", len(new) == 71, f"assets={len(new)}"),
        ("新增 5 个", len(d["appeared"]) == 5, f"appeared={len(d['appeared'])}"),
        ("下线 2 个", len(d["missing"]) == 2, f"missing={len(d['missing'])}"),
        ("高危新增 2 个", len(crit) == 2, f"critical={[a['port'] for a in crit]}"),
        ("差异可复现", diff(old, new) == d, "两次 diff 结果一致"),
    ]
    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    print(f"\n{'全部通过' if ok else '存在失败项'}（{len(checks)} 项）")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="资产快照夹具")
    ap.add_argument("--emit", metavar="DIR")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.emit:
        ap.print_help()
        return 2
    payload = emit(args.emit)
    d = payload["diff"]
    print(f"已写入 {args.emit}/snapshots.json")
    print(f"  t0={len(payload['t0'])} t1={len(payload['t1'])}")
    print(f"  appeared={len(d['appeared'])} missing={len(d['missing'])} changed={len(d['changed'])}")
    for a in d["appeared"]:
        print(f"  + {a['ip']}:{a['port']}/{a['service']} [{a['severity']}]")
    for a in d["missing"]:
        print(f"  - {a['ip']}:{a['port']}/{a['service']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
