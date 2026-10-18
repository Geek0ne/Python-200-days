#!/usr/bin/env python3
"""
Day 189 · 02 — 增量快照与变更检测

一次扫描 = 一份"全量快照"，但人真正关心的是**两次快照之间的差**：
    appeared  新暴露的资产
    changed   同一资产的服务/版本变了
    missing   这次没看到（可能抖动），还没确认下线
    gone      连续 N 次没看到，确认下线
    revived   已确认下线的资产又回来了

三个必须做对的点：
  1. 用自然键 (ip, port, proto) 做集合差，不要用 COUNT 或自增 id
  2. "没看到" ≠ "下线"：先记 missing，连续 grace 次才 gone（抑制端口抖动）
  3. 变更事件要落库，否则日报只能看当下，看不了"这周新增了几个"
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    label      TEXT
);
CREATE TABLE IF NOT EXISTS assets (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ip         TEXT NOT NULL,
    port       INTEGER NOT NULL,
    proto      TEXT NOT NULL DEFAULT 'tcp',
    service    TEXT,
    banner     TEXT,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    state      TEXT NOT NULL DEFAULT 'active'
               CHECK (state IN ('active', 'missing', 'gone')),
    miss_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ip, port, proto)
);
CREATE TABLE IF NOT EXISTS scan_assets (
    scan_id  INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    seen_at  TEXT NOT NULL,
    PRIMARY KEY (scan_id, asset_id)
);
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id    INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    seen_at    TEXT NOT NULL,
    event      TEXT NOT NULL,
    ip         TEXT NOT NULL,
    port       INTEGER NOT NULL,
    proto      TEXT NOT NULL,
    old_value  TEXT,
    new_value  TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_scan ON events(scan_id);
CREATE INDEX IF NOT EXISTS idx_events_event ON events(event);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def key_of(row_or_obs) -> tuple[str, int, str]:
    return (row_or_obs["ip"], int(row_or_obs["port"]), row_or_obs["proto"])


def run_scan(conn: sqlite3.Connection, observations, label: str = "",
             seen_at: str | None = None, grace: int = 2) -> list[dict]:
    """应用一次全量快照，返回本次产生的事件列表。

    grace=2 的含义：第一次消失记 missing；第二次仍消失才 gone。
    对"每天扫一次"的场景，等于给一次抖动留了 24 小时缓冲。
    """
    seen_at = seen_at or utcnow()
    cur = conn.execute("INSERT INTO scans(started_at, label) VALUES (?, ?)", (seen_at, label))
    scan_id = int(cur.lastrowid)

    events: list[dict] = []
    seen: set[tuple[str, int, str]] = set()

    # 同一批观测里重复的 key 只算一次（保留最后一条，通常信息更全）
    by_key: dict[tuple[str, int, str], dict] = {}
    for obs in observations:
        k = (obs["ip"], int(obs["port"]), obs.get("proto", "tcp"))
        by_key[k] = obs

    def add(event: str, ip: str, port: int, proto: str,
            old: str | None = None, new: str | None = None) -> None:
        events.append({"event": event, "ip": ip, "port": port, "proto": proto,
                       "old": old, "new": new})
        conn.execute(
            """INSERT INTO events(scan_id, seen_at, event, ip, port, proto, old_value, new_value)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (scan_id, seen_at, event, ip, port, proto, old, new),
        )

    for (ip, port, proto), obs in by_key.items():
        row = conn.execute(
            "SELECT * FROM assets WHERE ip=? AND port=? AND proto=?", (ip, port, proto)
        ).fetchone()

        if row is None:
            cur = conn.execute(
                """INSERT INTO assets(ip, port, proto, service, banner, first_seen, last_seen,
                                      state, miss_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active', 0)""",
                (ip, port, proto, obs.get("service"), obs.get("banner"), seen_at, seen_at),
            )
            asset_id = int(cur.lastrowid)
            add("appeared", ip, port, proto, None, obs.get("service"))
        else:
            asset_id = int(row["id"])
            old_service = row["service"]
            new_service = obs.get("service") or old_service
            old_banner = row["banner"]
            new_banner = obs.get("banner") or old_banner
            if row["state"] == "gone":
                add("revived", ip, port, proto, None, new_service)
            if old_service != new_service:
                add("changed", ip, port, proto, old_service, new_service)
            elif old_banner != new_banner:
                # 版本变化同样值得记录：OpenSSH_8.9 -> 9.6 可能意味着补丁或回滚
                add("changed", ip, port, proto, f"banner:{old_banner}", f"banner:{new_banner}")
            conn.execute(
                """UPDATE assets
                      SET last_seen=?, service=?, banner=?, state='active', miss_count=0
                    WHERE id=?""",
                (seen_at, new_service, new_banner, row["id"]),
            )
        conn.execute(
            "INSERT OR IGNORE INTO scan_assets(scan_id, asset_id, seen_at) VALUES (?, ?, ?)",
            (scan_id, asset_id, seen_at),
        )
        seen.add((ip, port, proto))

    # 差集：库里有、本次没看到的
    for row in conn.execute("SELECT * FROM assets WHERE state != 'gone'").fetchall():
        k = key_of(row)
        if k in seen:
            continue
        miss = int(row["miss_count"]) + 1
        if miss >= grace:
            conn.execute("UPDATE assets SET miss_count=?, state='gone' WHERE id=?",
                         (miss, row["id"]))
            add("gone", row["ip"], row["port"], row["proto"], row["service"], None)
        else:
            conn.execute("UPDATE assets SET miss_count=?, state='missing' WHERE id=?",
                         (miss, row["id"]))
            add("missing", row["ip"], row["port"], row["proto"], row["service"], None)

    conn.commit()
    return events


def demo(db_path: str) -> None:
    conn = connect(db_path)
    t0 = datetime(2026, 10, 16, 2, 0, tzinfo=timezone.utc)

    scans = [
        ("D1 全量", [
            {"ip": "10.0.0.5", "port": 22, "service": "ssh"},
            {"ip": "10.0.0.5", "port": 80, "service": "http"},
            {"ip": "10.0.0.7", "port": 443, "service": "https"},
        ]),
        ("D2 全量", [
            {"ip": "10.0.0.5", "port": 22, "service": "ssh"},
            {"ip": "10.0.0.5", "port": 80, "service": "http"},
            {"ip": "10.0.0.7", "port": 443, "service": "https"},
            {"ip": "10.0.0.9", "port": 8080, "service": "http"},
        ]),
        ("D3 全量", [
            {"ip": "10.0.0.5", "port": 22, "service": "ssh"},
            {"ip": "10.0.0.5", "port": 80, "service": "http"},
        ]),
        ("D4 全量", [
            {"ip": "10.0.0.5", "port": 22, "service": "ssh"},
            {"ip": "10.0.0.5", "port": 80, "service": "http"},
            {"ip": "10.0.0.9", "port": 8080, "service": "http"},
        ]),
    ]

    for i, (label, obs) in enumerate(scans):
        at = (t0 + timedelta(days=i)).isoformat(timespec="seconds")
        evs = run_scan(conn, obs, label=label, seen_at=at, grace=2)
        summary = ", ".join(f"{e['event']} {e['ip']}:{e['port']}" for e in evs) or "无变化"
        print(f"[{label}] {summary}")

    print("\n最终状态：")
    for r in conn.execute("SELECT ip, port, service, state, miss_count FROM assets ORDER BY ip, port"):
        print(f"  {r['ip']:<10}:{r['port']:<6}{r['service'] or '-':<8}{r['state']:<8}miss={r['miss_count']}")
    print("\n事件表（全部）：")
    for r in conn.execute("SELECT scan_id, event, ip, port, old_value, new_value FROM events ORDER BY id"):
        print(f"  scan#{r['scan_id']} {r['event']:<9}{r['ip']}:{r['port']:<6}"
              f"{r['old_value'] or '-':>8} -> {r['new_value'] or '-'}")
    conn.close()


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        conn = connect(Path(td) / "t.db")
        t = datetime(2026, 1, 1, tzinfo=timezone.utc)

        def at(d):
            return (t + timedelta(days=d)).isoformat(timespec="seconds")

        base = [
            {"ip": "203.0.113.1", "port": 22, "service": "ssh"},
            {"ip": "203.0.113.1", "port": 80, "service": "http"},
            {"ip": "203.0.113.1", "port": 443, "service": "https"},
        ]

        e1 = run_scan(conn, base, "s1", at(0))
        assert [e["event"] for e in e1] == ["appeared"] * 3, e1

        e2 = run_scan(conn, base + [{"ip": "203.0.113.9", "port": 8080, "service": "http"}],
                      "s2", at(1))
        assert {e["event"] for e in e2} == {"appeared"}, e2
        assert e2[0]["port"] == 8080

        # 8080 抖动一次，443 开始消失
        obs3 = [{"ip": "203.0.113.1", "port": 22, "service": "ssh"},
                {"ip": "203.0.113.1", "port": 80, "service": "http"}]
        e3 = run_scan(conn, obs3, "s3", at(2))
        assert sorted(e["event"] for e in e3) == ["missing", "missing"], e3

        r = conn.execute("SELECT * FROM assets WHERE port=8080").fetchone()
        assert r["state"] == "missing" and r["miss_count"] == 1

        # 8080 回来；443 第二次消失 -> gone
        obs4 = obs3 + [{"ip": "203.0.113.9", "port": 8080, "service": "http"}]
        e4 = run_scan(conn, obs4, "s4", at(3))
        assert {e["event"] for e in e4} == {"gone"}, e4
        r = conn.execute("SELECT * FROM assets WHERE port=443").fetchone()
        assert r["state"] == "gone" and r["miss_count"] == 2
        r = conn.execute("SELECT * FROM assets WHERE port=8080").fetchone()
        assert r["state"] == "active" and r["miss_count"] == 0

        # 服务变化
        obs5 = obs4 + [{"ip": "203.0.113.1", "port": 22, "service": "telnet"}]
        e5 = run_scan(conn, obs5, "s5", at(4))
        assert [e["event"] for e in e5] == ["changed"], e5
        assert e5[0]["old"] == "ssh" and e5[0]["new"] == "telnet"

        # gone 的资产重新出现 -> revived
        obs6 = obs5 + [{"ip": "203.0.113.1", "port": 443, "service": "https"}]
        e6 = run_scan(conn, obs6, "s6", at(5))
        assert [e["event"] for e in e6] == ["revived"], e6

        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3 + 1 + 2 + 1 + 1 + 1
        conn.close()
    print("✅ 02 self-test 通过：appeared / missing / gone / changed / revived 全部符合预期")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="增量快照与变更检测")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--db", default=str(Path(tempfile.gettempdir()) / "day189-diff.db"))
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    demo(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
