#!/usr/bin/env python3
"""
Day 189 · 01 — SQLite 资产库基础

核心模型（两层）：
  1) assets      当前状态表：一个 (ip, port, proto) 只有一行，回答"现在是什么样"
  2) scans / scan_assets  观测流水：回答"哪次扫描看到了什么"，是趋势图的原料

为什么要分两层？
  只存当前状态 → 历史被覆盖，画不出趋势；
  只存流水     → 每次查询都要扫全表，而且"资产是否还在"无法 O(1) 判断。
  当前状态 + 不可变观测，是资产管理的标准做法（CQRS 的简化版）。

用法：
    python3 01-asset-store-basic.py --self-test
    python3 01-asset-store-basic.py --db /tmp/day189-demo.db
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    source      TEXT NOT NULL,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ip          TEXT NOT NULL,
    port        INTEGER NOT NULL,
    proto       TEXT NOT NULL DEFAULT 'tcp',
    service     TEXT,
    banner      TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    state       TEXT NOT NULL DEFAULT 'active'
                CHECK (state IN ('active', 'missing', 'gone')),
    UNIQUE (ip, port, proto)
);

CREATE TABLE IF NOT EXISTS scan_assets (
    scan_id   INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    asset_id  INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    seen_at   TEXT NOT NULL,
    PRIMARY KEY (scan_id, asset_id)
);

CREATE INDEX IF NOT EXISTS idx_assets_state ON assets(state);
CREATE INDEX IF NOT EXISTS idx_scan_assets_asset ON scan_assets(asset_id);
"""


def utcnow() -> str:
    """统一用 UTC ISO8601，秒级精度：跨时区比较不会错位。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # 外键默认是关的，必须每条连接显式打开
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL：读写不互相阻塞，适合"边扫边查"
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def start_scan(conn: sqlite3.Connection, source: str, note: str | None = None,
               started_at: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO scans(started_at, source, note) VALUES (?, ?, ?)",
        (started_at or utcnow(), source, note),
    )
    return int(cur.lastrowid)


def upsert_asset(conn: sqlite3.Connection, ip: str, port: int, proto: str = "tcp",
                 service: str | None = None, banner: str | None = None,
                 seen_at: str | None = None) -> tuple[int, str]:
    """按自然键 (ip, port, proto) 做 UPSERT，返回 (asset_id, 'new'|'existing')。

    自然键必须稳定：不能用自增 id 比对，因为 id 是数据库内部实现细节，
    重建库、换机器都会变。
    """
    seen_at = seen_at or utcnow()
    row = conn.execute(
        "SELECT id FROM assets WHERE ip=? AND port=? AND proto=?",
        (ip, port, proto),
    ).fetchone()

    if row is None:
        cur = conn.execute(
            """INSERT INTO assets(ip, port, proto, service, banner,
                                  first_seen, last_seen, state)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active')""",
            (ip, port, proto, service, banner, seen_at, seen_at),
        )
        return int(cur.lastrowid), "new"

    # COALESCE：本次没识别出 service 时，保留上一次的结论，不要用 NULL 覆盖
    conn.execute(
        """UPDATE assets
              SET last_seen = ?,
                  service   = COALESCE(?, service),
                  banner    = COALESCE(?, banner),
                  state     = 'active'
            WHERE id = ?""",
        (seen_at, service, banner, row["id"]),
    )
    return int(row["id"]), "existing"


def ingest_scan(conn: sqlite3.Connection, observations, source: str = "manual",
                started_at: str | None = None, note: str | None = None):
    """把一次扫描的完整观测写入库。同一份数据重跑是幂等的。"""
    scan_id = start_scan(conn, source, note, started_at)
    stats = {"new": 0, "existing": 0, "observed": 0}

    with conn:  # 事务：要么全成功，要么全回滚
        for obs in observations:
            asset_id, status = upsert_asset(
                conn,
                obs["ip"],
                int(obs["port"]),
                obs.get("proto", "tcp"),
                obs.get("service"),
                obs.get("banner"),
                obs.get("seen_at"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO scan_assets(scan_id, asset_id, seen_at) VALUES (?, ?, ?)",
                (scan_id, asset_id, obs.get("seen_at") or utcnow()),
            )
            stats[status] += 1
            stats["observed"] += 1
    return scan_id, stats


def demo(db_path: str) -> None:
    conn = connect(db_path)
    first = [
        {"ip": "10.0.0.5", "port": 22, "service": "ssh", "banner": "OpenSSH_8.9"},
        {"ip": "10.0.0.5", "port": 80, "service": "http", "banner": "nginx/1.24.0"},
        {"ip": "10.0.0.7", "port": 443, "service": "https", "banner": "nginx/1.24.0"},
    ]
    scan_id, stats = ingest_scan(conn, first, source="nmap-xml", note="第一次全量")

    second = [
        {"ip": "10.0.0.5", "port": 22, "service": "ssh", "banner": "OpenSSH_9.6"},
        {"ip": "10.0.0.5", "port": 80, "service": "http", "banner": "nginx/1.24.0"},
        {"ip": "10.0.0.7", "port": 443, "service": "https", "banner": "nginx/1.24.0"},
        {"ip": "10.0.0.9", "port": 6379, "service": "redis", "banner": None},
    ]
    scan2, stats2 = ingest_scan(conn, second, source="nmap-xml", note="第二次全量")

    print(f"库文件: {db_path}")
    print(f"scan #{scan_id}: {stats}")
    print(f"scan #{scan2}: {stats2}")
    print("\n当前资产表：")
    print(f"{'ip':<12}{'port':>6}  {'proto':<6}{'service':<8}{'state':<8}first_seen")
    for r in conn.execute("SELECT * FROM assets ORDER BY ip, port"):
        print(f"{r['ip']:<12}{r['port']:>6}  {r['proto']:<6}{r['service'] or '-':<8}"
              f"{r['state']:<8}{r['first_seen']}")
    print(f"\nassets={conn.execute('SELECT COUNT(*) FROM assets').fetchone()[0]}  "
          f"scan_assets={conn.execute('SELECT COUNT(*) FROM scan_assets').fetchone()[0]}")
    conn.close()


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"
        conn = connect(db)
        obs = [
            {"ip": "192.0.2.10", "port": 22, "service": "ssh", "banner": "OpenSSH_8.9",
             "seen_at": "2026-01-01T00:00:00+00:00"},
            {"ip": "192.0.2.10", "port": 80, "service": "http", "banner": "nginx/1.24.0",
             "seen_at": "2026-01-01T00:00:00+00:00"},
        ]
        s1, st1 = ingest_scan(conn, obs, source="test",
                              started_at="2026-01-01T00:00:00+00:00")
        assert st1 == {"new": 2, "existing": 0, "observed": 2}, st1

        # 重放同一批数据：应全部命中 existing，资产数不变
        s2, st2 = ingest_scan(conn, obs, source="test", note="replay",
                              started_at="2026-01-02T00:00:00+00:00")
        assert st2 == {"new": 0, "existing": 2, "observed": 2}, st2
        assert conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM scan_assets").fetchone()[0] == 4

        # 服务升级但 first_seen 必须保留
        ingest_scan(conn, [{"ip": "192.0.2.10", "port": 22, "service": "ssh",
                            "banner": "OpenSSH_9.6",
                            "seen_at": "2026-01-03T00:00:00+00:00"}],
                    source="test", note="upgrade",
                    started_at="2026-01-03T00:00:00+00:00")
        row = conn.execute(
            "SELECT * FROM assets WHERE ip='192.0.2.10' AND port=22").fetchone()
        assert row["banner"] == "OpenSSH_9.6"
        assert row["first_seen"] < row["last_seen"]

        # 本次没识别出 service，不应覆盖旧值
        ingest_scan(conn, [{"ip": "192.0.2.10", "port": 80, "banner": "nginx/1.25.1",
                            "seen_at": "2026-01-04T00:00:00+00:00"}],
                    source="test", note="no-service",
                    started_at="2026-01-04T00:00:00+00:00")
        row = conn.execute(
            "SELECT * FROM assets WHERE ip='192.0.2.10' AND port=80").fetchone()
        assert row["service"] == "http", row["service"]

        conn.close()
    print("✅ 01 self-test 通过：UPSERT 幂等 / first_seen 保留 / NULL 不覆盖")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SQLite 资产库基础")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--db", default=str(Path(tempfile.gettempdir()) / "day189-assets.db"))
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    demo(args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
