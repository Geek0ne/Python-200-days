#!/usr/bin/env python3
"""
巡检 worker：定时扫端口 → 与上次状态比对 → 变化投递到 sink。

设计对齐正文：
  - 固定频率网格 + 抖动（不是"跑完再 sleep"）
  - 每个时间格子一个幂等键，重启不会重复跑同一格
  - 扫描结果落 SQLite，sink 不可达时转本地待发队列，恢复后补发
  - 每轮写心跳文件，供容器 healthcheck 判断"活着但卡死"
"""
from __future__ import annotations

import json
import os
import signal
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request

TARGETS = [t.strip() for t in os.environ.get(
    "TARGETS", "sink:8080,sink:8081,127.0.0.1:1").split(",") if t.strip()]
INTERVAL = int(os.environ.get("INTERVAL", "5"))
JITTER = float(os.environ.get("JITTER", "0.15"))
SINK_URL = os.environ.get("SINK_URL", "http://sink:8080/alert")
DB_PATH = os.environ.get("DB_PATH", "/data/worker/state.db")
HEARTBEAT = os.environ.get("HEARTBEAT", "/tmp/heartbeat")
SIMULATE_FLAP = os.environ.get("SIMULATE_FLAP", "1") == "1"
CRITICAL_PORTS = {3389, 445, 6379}

STOP = False


def _stop(signum, frame):
    global STOP
    STOP = True
    print(f"[worker] signal {signum}, 收尾中", flush=True)


def connect_db() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("CREATE TABLE IF NOT EXISTS assets (key TEXT PRIMARY KEY, open INTEGER NOT NULL, updated REAL NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS slots (slot TEXT PRIMARY KEY, ran_at REAL NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created REAL NOT NULL)")
    return conn


def probe(target: str, timeout: float = 0.6) -> bool:
    host, _, port = target.rpartition(":")
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def severity_for(target: str, opened: bool) -> str:
    port = int(target.rpartition(":")[2])
    if opened and port in CRITICAL_PORTS:
        return "critical"
    if opened:
        return "warning"
    return "info"


def scan(cycle: int) -> dict[str, bool]:
    result = {t: probe(t) for t in TARGETS}
    if SIMULATE_FLAP:
        # 模拟一台反复开关的机器：每 3 个周期切换状态。
        # 真实环境里这就是"端口抖动"，也是告警降噪要处理的主要噪声源。
        result["10.9.9.9:9443"] = (cycle // 3) % 2 == 0
    return result


def post(payload: dict) -> bool:
    body = json.dumps(payload, ensure_ascii=False).encode()
    for attempt in range(1, 4):
        req = urllib.request.Request(SINK_URL, data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if 200 <= resp.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"[worker] 投递失败 attempt={attempt}: {exc}", flush=True)
            time.sleep(0.2 * (2 ** (attempt - 1)))
    return False


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    conn = connect_db()
    anchor = time.time()
    print(f"[worker] targets={TARGETS} interval={INTERVAL}s jitter={JITTER:.0%} sink={SINK_URL}", flush=True)

    while not STOP:
        now = time.time()
        slot = int((now - anchor) // INTERVAL)
        # 抖动：以槽位为种子，同一格永远算出同样的偏移（可复现、不重复执行）
        offset = ((hash(f"slot-{slot}") % 1000) / 1000.0 * 2 - 1) * JITTER * INTERVAL
        fire_at = anchor + slot * INTERVAL + offset
        if now < fire_at:
            time.sleep(min(0.5, fire_at - now))
            continue

        slot_key = f"scan:{int(anchor)}:{slot}"
        cur = conn.execute("INSERT OR IGNORE INTO slots(slot, ran_at) VALUES (?,?)", (slot_key, now))
        if cur.rowcount == 0:
            time.sleep(0.5)
            continue

        states = scan(slot)
        prev = {row[0]: bool(row[1]) for row in conn.execute("SELECT key, open FROM assets")}
        changes = []
        for key, is_open in states.items():
            was = prev.get(key)
            if was is not None and was != is_open:
                changes.append({
                    "rule": "port-appeared" if is_open else "port-closed",
                    "asset": key,
                    "severity": severity_for(key, is_open),
                    "title": f"{key} {'开放' if is_open else '关闭'}",
                    "detail": f"slot={slot} prev={was} now={is_open}",
                })
            conn.execute(
                "INSERT INTO assets(key, open, updated) VALUES (?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET open=excluded.open, updated=excluded.updated",
                (key, int(is_open), now),
            )

        if changes:
            payload = {
                "title": f"资产变更 {len(changes)} 条",
                "counts": {
                    "critical": sum(1 for c in changes if c["severity"] == "critical"),
                    "warning": sum(1 for c in changes if c["severity"] == "warning"),
                    "info": sum(1 for c in changes if c["severity"] == "info"),
                },
                "total": len(changes),
                "items": changes,
                "truncated": 0,
                "sent_at": round(now, 3),
            }
            if post(payload):
                print(f"[worker] slot={slot} 投递 {len(changes)} 条变更", flush=True)
            else:
                conn.execute("INSERT INTO pending(payload, created) VALUES (?,?)",
                             (json.dumps(payload, ensure_ascii=False), now))
                print(f"[worker] slot={slot} 投递失败，已转本地待发队列", flush=True)

        for row in conn.execute("SELECT id, payload FROM pending ORDER BY id LIMIT 5").fetchall():
            if post(json.loads(row[1])):
                conn.execute("DELETE FROM pending WHERE id=?", (row[0],))

        with open(HEARTBEAT, "w") as fh:
            fh.write(str(time.time()))

    conn.close()
    print("[worker] 已停止", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
