#!/usr/bin/env python3
"""
Day 186 · 03 — 实战：资产清单入库 + 快照差分

为什么资产测绘必须落库：
  单次枚举只是"一张照片"。安全运维真正关心的是**变化**：
  新增了一个 dev 子域名？某个域名解析到新 IP？昨天还在、今天消失了？
  没有历史快照，这些问题一个都答不了。

数据模型（刻意保持简单）：
  snapshots(id, label, taken_at)                 —— 每次扫描一个快照
  assets(snapshot_id, host, ips, source)         —— 快照内的资产行

差分口径：
  added   = 本次有、上次没有
  removed = 上次有、本次没有
  changed = 两边都有，但 IP 集合不同

用法：
  python3 03-asset-inventory.py --db assets.db --input subs.json --label 2026-10-18-am
  python3 03-asset-inventory.py --db assets.db --show
  python3 03-asset-inventory.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    label     TEXT NOT NULL,
    taken_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    snapshot_id INTEGER NOT NULL REFERENCES snapshots(id) ON DELETE CASCADE,
    host        TEXT NOT NULL,
    ips         TEXT NOT NULL,          -- JSON 数组字符串，保持顺序稳定
    source      TEXT NOT NULL DEFAULT 'dns',
    PRIMARY KEY (snapshot_id, host)
);
CREATE INDEX IF NOT EXISTS idx_assets_host ON assets(host);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def save_snapshot(conn: sqlite3.Connection, label: str,
                  assets: dict[str, list[str]], source: str = "dns",
                  taken_at: str | None = None) -> int:
    """写入一个完整快照，返回 snapshot_id。"""
    taken_at = taken_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:  # 事务：要么整批进，要么一条不进
        cur = conn.execute(
            "INSERT INTO snapshots(label, taken_at) VALUES (?, ?)", (label, taken_at)
        )
        snapshot_id = int(cur.lastrowid)
        conn.executemany(
            "INSERT INTO assets(snapshot_id, host, ips, source) VALUES (?, ?, ?, ?)",
            [(snapshot_id, host, json.dumps(sorted(ips)), source)
             for host, ips in sorted(assets.items())],
        )
    return snapshot_id


def load_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> dict[str, list[str]]:
    rows = conn.execute(
        "SELECT host, ips FROM assets WHERE snapshot_id = ? ORDER BY host", (snapshot_id,)
    ).fetchall()
    return {host: json.loads(ips) for host, ips in rows}


def latest_two(conn: sqlite3.Connection) -> tuple[int | None, int | None]:
    rows = conn.execute("SELECT id FROM snapshots ORDER BY id DESC LIMIT 2").fetchall()
    ids = [r[0] for r in rows]
    if len(ids) == 2:
        return ids[1], ids[0]     # (previous, current)
    if len(ids) == 1:
        return None, ids[0]
    return None, None


def diff_snapshots(previous: dict[str, list[str]], current: dict[str, list[str]]) -> dict:
    prev_hosts, curr_hosts = set(previous), set(current)
    added = sorted(curr_hosts - prev_hosts)
    removed = sorted(prev_hosts - curr_hosts)
    changed = [
        {"host": host, "before": previous[host], "after": current[host]}
        for host in sorted(prev_hosts & curr_hosts)
        if previous[host] != current[host]
    ]
    return {"added": added, "removed": removed, "changed": changed}


def parse_input(path: str) -> tuple[dict[str, list[str]], str]:
    """兼容 01 的 {assets:{host:[ips]}} 与 02 的 {names:[host]} 两种输入。"""
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload.get("assets"), dict):
        return {h: list(ips) for h, ips in payload["assets"].items()}, "dns"
    if isinstance(payload.get("names"), list):
        return {name: [] for name in payload["names"]}, "ct"
    raise ValueError("输入格式不认识：需要 {assets: {...}} 或 {names: [...]}")


def print_diff(result: dict) -> None:
    print(f"新增 {len(result['added'])} 个：")
    for host in result["added"]:
        print(f"  + {host}")
    print(f"消失 {len(result['removed'])} 个：")
    for host in result["removed"]:
        print(f"  - {host}")
    print(f"IP 变化 {len(result['changed'])} 个：")
    for item in result["changed"]:
        print(f"  ~ {item['host']}: {item['before']} -> {item['after']}")


def self_test() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        conn = connect(Path(tmp) / "assets.db")
        save_snapshot(conn, "run-1", {
            "www.example.test": ["192.0.2.10"],
            "api.example.test": ["192.0.2.11"],
        }, taken_at="2026-10-17T00:00:00+00:00")
        prev_id, _ = latest_two(conn)

        save_snapshot(conn, "run-2", {
            "www.example.test": ["192.0.2.10"],
            "api.example.test": ["192.0.2.12"],   # IP 变了
            "dev.example.test": ["192.0.2.20"],   # 新增
            # mail 原来就没有，这里不放
        }, taken_at="2026-10-18T00:00:00+00:00")
        prev_id, curr_id = latest_two(conn)
        result = diff_snapshots(load_snapshot(conn, prev_id), load_snapshot(conn, curr_id))

        assert result["added"] == ["dev.example.test"], result
        assert result["removed"] == [], result
        assert result["changed"] == [
            {"host": "api.example.test", "before": ["192.0.2.11"], "after": ["192.0.2.12"]}
        ], result

        # 再存一个快照，验证 removed
        save_snapshot(conn, "run-3", {"www.example.test": ["192.0.2.10"]})
        prev_id, curr_id = latest_two(conn)
        result = diff_snapshots(load_snapshot(conn, prev_id), load_snapshot(conn, curr_id))
        assert result["removed"] == ["api.example.test", "dev.example.test"], result

        # 空快照也必须能存
        save_snapshot(conn, "run-4", {})
        prev_id, curr_id = latest_two(conn)
        result = diff_snapshots(load_snapshot(conn, prev_id), load_snapshot(conn, curr_id))
        assert result["removed"] == ["www.example.test"], result

        count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        assert count == 4, count
        conn.close()

    print("✅ self-test passed: 新增 / 消失 / IP 变化 / 空快照 四种差分口径都正确")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="资产清单快照与差分")
    parser.add_argument("--db", default="assets.db")
    parser.add_argument("--input", help="01/02 的输出 JSON")
    parser.add_argument("--label", help="快照标签，如 2026-10-18-am")
    parser.add_argument("--source", default=None, help="dns / ct")
    parser.add_argument("--show", action="store_true", help="只展示最近两次差分")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    conn = connect(args.db)
    if args.input:
        assets, detected_source = parse_input(args.input)
        label = args.label or datetime.now().strftime("%Y-%m-%d-%H%M")
        snapshot_id = save_snapshot(conn, label, assets, source=args.source or detected_source)
        print(f"[*] 已写入快照 #{snapshot_id} ({label})，资产 {len(assets)} 条")
    elif not args.show:
        parser.error("需要 --input 或 --show，或用 --self-test")

    prev_id, curr_id = latest_two(conn)
    if prev_id is None or curr_id is None:
        print("[*] 还没有两次快照，无法差分（再跑一次就有了）")
    else:
        result = diff_snapshots(load_snapshot(conn, prev_id), load_snapshot(conn, curr_id))
        print(f"[*] 对比快照 #{prev_id} -> #{curr_id}")
        print_diff(result)

    total = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    print(f"[*] 数据库共有 {total} 个快照: {args.db}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

