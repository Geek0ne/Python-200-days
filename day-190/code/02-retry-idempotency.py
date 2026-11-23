#!/usr/bin/env python3
"""
Day 190 · 02 — 重试、幂等与租约：让"至少一次"的执行变成"恰好一次"的效果

调度器只保证"任务被触发"，不保证"任务只生效一次"。cron 重叠、进程崩溃、
网络超时重试，任何一条路径都可能让同一次巡检写两遍数据、发两遍告警。

本脚本用 SQLite 实现一套最小可用的执行模型：
  - 入队去重：idem_key 主键，重复入队被 UNIQUE 挡住
  - 租约领取：BEGIN IMMEDIATE + status 条件更新，并发 worker 只有一个能拿到
  - 崩溃恢复：租约过期后可被重新领取（至少一次）
  - 效果幂等：effects.idem_key 主键，重放只会有一次副作用（恰好一次的效果）
  - 退避重试：指数退避 + full jitter，永久错误直接进 dead 不重试

用法：
  python3 02-retry-idempotency.py --self-test
  python3 02-retry-idempotency.py --demo
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import sys
import tempfile
import threading
import time
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    idem_key    TEXT PRIMARY KEY,
    job         TEXT NOT NULL,
    payload     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    attempts    INTEGER NOT NULL DEFAULT 0,
    visible_at  REAL NOT NULL,
    lease_owner TEXT,
    lease_until REAL,
    last_error  TEXT,
    created_at  REAL NOT NULL,
    finished_at REAL
);
CREATE TABLE IF NOT EXISTS effects (
    idem_key   TEXT PRIMARY KEY,
    kind       TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    idem_key    TEXT NOT NULL,
    worker      TEXT NOT NULL,
    attempt     INTEGER NOT NULL,
    outcome     TEXT NOT NULL,
    at          REAL NOT NULL
);
"""

BASE_DELAY = 1.0
MAX_DELAY = 60.0
MAX_ATTEMPTS = 3


class PermanentError(Exception):
    """不该重试的错误：参数错误、404、权限拒绝。重试只会放大故障。"""


class TransientError(Exception):
    """该重试的错误：连接重置、超时、503。"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10.0, isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def enqueue(conn: sqlite3.Connection, job: str, idem_key: str, payload: dict, now: float | None = None) -> bool:
    """入队。返回 True 表示这次真的插入了，False 表示已存在（被去重）。

    idem_key 必须由"业务语义"决定，例如 scan:2026-10-20T10:00Z:assets，
    而不是由"这次请求"决定（uuid 会让去重完全失效）。
    """
    now = time.time() if now is None else now
    try:
        conn.execute(
            "INSERT INTO jobs (idem_key, job, payload, status, visible_at, created_at) VALUES (?,?,?,?,?,?)",
            (idem_key, job, json.dumps(payload, ensure_ascii=False), "pending", now, now),
        )
        return True
    except sqlite3.IntegrityError:
        return False


def claim(conn: sqlite3.Connection, worker: str, now: float, lease_s: float = 30.0) -> dict | None:
    """领取一个到期任务。并发安全靠 BEGIN IMMEDIATE + 条件 UPDATE 的行数校验。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        # 注意：这里同时认领"到期的 pending"和"租约过期的 running"。
        # 只查 pending 会让崩溃在 running 的任务永远卡死——这是第一版真实踩到的坑。
        row = conn.execute(
            "SELECT idem_key, job, payload, attempts FROM jobs "
            "WHERE (status='pending' AND visible_at<=?) "
            "   OR (status='running' AND lease_until IS NOT NULL AND lease_until<=?) "
            "ORDER BY visible_at LIMIT 1",
            (now, now),
        ).fetchone()
        if row is None:
            conn.execute("COMMIT")
            return None
        cur = conn.execute(
            "UPDATE jobs SET status='running', lease_owner=?, lease_until=?, attempts=attempts+1 "
            "WHERE idem_key=? AND ((status='pending' AND visible_at<=?) "
            "                   OR (status='running' AND lease_until IS NOT NULL AND lease_until<=?))",
            (worker, now + lease_s, row[0], now, now),
        )
        if cur.rowcount != 1:
            conn.execute("ROLLBACK")
            return None
        conn.execute("COMMIT")
        return {"key": row[0], "job": row[1], "payload": json.loads(row[2]), "attempt": row[3] + 1}
    except Exception:
        conn.execute("ROLLBACK")
        raise


def backoff_delay(attempt: int, rng: random.Random | None = None) -> float:
    """指数退避 + full jitter：delay = rand(0, min(cap, base*2^(attempt-1)))。

    full jitter 的意义：失败的下游通常是一起失败的，如果所有任务都按同一个
    指数退避，它们会在同一秒集体重试，把刚恢复的服务再打挂（thundering herd）。
    """
    rng = rng or random
    ceiling = min(MAX_DELAY, BASE_DELAY * (2 ** (attempt - 1)))
    return rng.uniform(0.0, ceiling)


def finish_success(conn: sqlite3.Connection, key: str, kind: str, now: float) -> bool:
    """写副作用 + 标记完成。返回 True 表示这次副作用是第一次生效。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO effects (idem_key, kind, created_at) VALUES (?,?,?)", (key, kind, now)
        )
        applied = cur.rowcount == 1
        conn.execute("UPDATE jobs SET status='done', finished_at=?, lease_owner=NULL WHERE idem_key=?", (now, key))
        conn.execute("COMMIT")
        return applied
    except Exception:
        conn.execute("ROLLBACK")
        raise


def finish_failure(conn: sqlite3.Connection, key: str, err: str, attempt: int, now: float,
                   permanent: bool = False, rng: random.Random | None = None) -> str:
    """失败处理：永久错误直接 dead；临时错误退避后重新可见。返回新状态。"""
    if permanent or attempt >= MAX_ATTEMPTS:
        conn.execute(
            "UPDATE jobs SET status='dead', last_error=?, lease_owner=NULL WHERE idem_key=?",
            (err, key),
        )
        return "dead"
    delay = backoff_delay(attempt, rng)
    conn.execute(
        "UPDATE jobs SET status='pending', visible_at=?, last_error=?, lease_owner=NULL WHERE idem_key=?",
        (now + delay, err, key),
    )
    return f"pending(+{delay:.2f}s)"


def log_attempt(conn: sqlite3.Connection, key: str, worker: str, attempt: int, outcome: str, now: float) -> None:
    conn.execute(
        "INSERT INTO attempts_log (idem_key, worker, attempt, outcome, at) VALUES (?,?,?,?,?)",
        (key, worker, attempt, outcome, now),
    )


def run_worker(conn: sqlite3.Connection, worker: str, now: float, lease_s: float,
               task, rng: random.Random | None = None) -> str | None:
    """跑一轮：领一个 → 执行 → 成功/失败落库。task 抛异常即视为失败。"""
    job = claim(conn, worker, now, lease_s)
    if job is None:
        return None
    try:
        task(job)
    except PermanentError as exc:
        status = finish_failure(conn, job["key"], str(exc), job["attempt"], now, permanent=True)
        log_attempt(conn, job["key"], worker, job["attempt"], f"permanent:{exc}", now)
        return f"{job['key']} -> {status}"
    except TransientError as exc:
        status = finish_failure(conn, job["key"], str(exc), job["attempt"], now, rng=rng)
        log_attempt(conn, job["key"], worker, job["attempt"], f"transient:{status}", now)
        return f"{job['key']} -> {status}"
    applied = finish_success(conn, job["key"], job["job"], now)
    log_attempt(conn, job["key"], worker, job["attempt"], "ok" if applied else "ok-duplicate-effect", now)
    return f"{job['key']} -> done(applied={applied})"


def demo() -> int:
    tmp = tempfile.mkdtemp(prefix="d190-idem-")
    db = os.path.join(tmp, "jobs.db")
    conn = connect(db)
    init_db(conn)
    print(f"数据库: {db}\n")

    # --- 实验 A：重复入队 ---
    print("[A] 同一 idem_key 被 4 次重复入队（cron 重叠的真实形态）")
    conn.execute("BEGIN")
    results = [enqueue(conn, "scan", "scan:2026-10-20T10:00Z:assets", {"targets": 40}, now=1000.0)
               for _ in range(4)]
    conn.execute("COMMIT")
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    print(f"    enqueue 返回: {results}")
    print(f"    表里实际行数: {total}  → 3 次被 UNIQUE 挡住\n")

    # --- 实验 B：失败两次后成功 ---
    print("[B] 任务前两次连接重置，第三次成功")
    calls = {"n": 0}

    def flaky(job: dict) -> None:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise TransientError(f"ConnectionResetError: peer reset (call {calls['n']})")

    statuses = []
    simulated_now = 1000.0
    for _ in range(6):
        out = run_worker(conn, "w1", simulated_now, 30, flaky, random.Random(42))
        if out:
            statuses.append((round(simulated_now, 2), out))
        # 把虚拟时钟推进到下一个可见时刻
        row = conn.execute("SELECT visible_at FROM jobs WHERE idem_key=?", ("scan:2026-10-20T10:00Z:assets",)).fetchone()
        simulated_now = max(row[0] if row and row[0] else simulated_now + 1, simulated_now + 1)
    for ts, s in statuses:
        print(f"    t={ts:>7} {s}")
    row = conn.execute("SELECT status, attempts FROM jobs WHERE idem_key=?", ("scan:2026-10-20T10:00Z:assets",)).fetchone()
    effects = conn.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
    print(f"    最终: status={row[0]} attempts={row[1]} effects={effects}\n")

    # --- 实验 C：8 线程并发 60 个任务，看会不会重复生效 ---
    print("[C] 8 个 worker 并发处理 60 个任务，每个任务都会写一次副作用")
    conn2 = connect(db)
    init_db(conn2)
    conn2.execute("BEGIN")
    for i in range(60):
        enqueue(conn2, "alert", f"alert:2026-10-20:{i:03d}", {"asset": f"10.0.0.{i}"}, now=1.0)
    conn2.execute("COMMIT")
    ok_counter = {"ok": 0}
    lock = threading.Lock()

    def worker_loop(wid: int) -> None:
        c = connect(db)
        rng = random.Random(wid)
        for _ in range(200):
            def task(_job: dict) -> None:
                time.sleep(0.001)
            out = run_worker(c, f"w{wid}", time.time(), 30, task, rng)
            if out is None:
                return
            with lock:
                ok_counter["ok"] += 1
        c.close()

    t0 = time.perf_counter()
    threads = [threading.Thread(target=worker_loop, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - t0
    rows = conn2.execute(
        "SELECT status, COUNT(*), SUM(attempts) FROM jobs WHERE job='alert' GROUP BY status"
    ).fetchall()
    eff = conn2.execute("SELECT COUNT(*) FROM effects WHERE kind='alert'").fetchone()[0]
    print(f"    耗时 {elapsed:.2f}s，处理结果按状态: {rows}")
    print(f"    effects 行数 = {eff} / 60 个任务")
    print(f"    → 效果数 == 任务数，说明重试/并发没有制造重复副作用\n")

    # --- 实验 D：永久错误不重试 ---
    print("[D] 永久错误（400 参数错误）不应重试")
    enqueue(conn2, "scan", "bad-target", {"target": "http://%"})
    out = run_worker(conn2, "w1", time.time(), 30, lambda _j: (_ for _ in ()).throw(PermanentError("HTTP 400")))
    row = conn2.execute("SELECT status, attempts FROM jobs WHERE idem_key='bad-target'").fetchone()
    print(f"    {out} → status={row[0]} attempts={row[1]}（attempts=1 即放弃）\n")

    # --- 实验 E：worker 崩溃后租约过期重领 ---
    print("[E] worker 领了任务但崩溃（不 finish），租约到期后被另一个 worker 接手")
    enqueue(conn2, "scan", "crash-case", {"x": 1}, now=5000.0)
    got = claim(conn2, "w-crashed", 5000.0, lease_s=2.0)
    again_early = claim(conn2, "w2", 5001.0, lease_s=2.0)
    again_late = claim(conn2, "w2", 5003.0, lease_s=2.0)
    print(f"    第一次领取: {got['key'] if got else None}（w-crashed）")
    print(f"    t+1s 再领: {again_early['key'] if again_early else 'None（被租约挡住）'}")
    print(f"    t+3s 再领: {again_late['key'] if again_late else 'None'} → 崩溃任务可恢复")

    # 清理
    conn.close()
    conn2.close()
    for suffix in ("", "-wal", "-shm"):
        p = db + suffix
        if os.path.exists(p):
            os.remove(p)
    os.rmdir(tmp)
    return 0


def self_test() -> int:
    checks: list[tuple[str, bool, str]] = []
    tmp = tempfile.mkdtemp(prefix="d190-selftest-")
    db = os.path.join(tmp, "t.db")
    conn = connect(db)
    init_db(conn)

    # 1. 入队去重
    a = enqueue(conn, "scan", "k1", {}, now=1.0)
    b = enqueue(conn, "scan", "k1", {}, now=1.0)
    checks.append(("入队幂等", a is True and b is False, f"first={a} second={b}"))

    # 2. 租约互斥
    j1 = claim(conn, "w1", 2.0, 5.0)
    j2 = claim(conn, "w2", 2.0, 5.0)
    checks.append(("租约互斥", j1 is not None and j2 is None, f"w1={bool(j1)} w2={bool(j2)}"))

    # 3. 重放不重复生效
    first = finish_success(conn, "k1", "scan", 3.0)
    second = finish_success(conn, "k1", "scan", 4.0)
    eff = conn.execute("SELECT COUNT(*) FROM effects").fetchone()[0]
    checks.append(("效果幂等", first is True and second is False and eff == 1, f"applied={first},{second} effects={eff}"))

    # 4. 退避上限
    delays = [backoff_delay(1, random.Random(1)), backoff_delay(3, random.Random(1)), backoff_delay(20, random.Random(1))]
    checks.append(("退避不超过上限", all(0 <= d <= MAX_DELAY for d in delays),
                   "delays=" + ", ".join(f"{d:.2f}s" for d in delays)))

    # 5. 永久错误进 dead
    enqueue(conn, "scan", "k2", {}, now=10.0)
    claim(conn, "w1", 10.0, 5.0)
    st = finish_failure(conn, "k2", "400", 1, 10.0, permanent=True)
    row = conn.execute("SELECT status FROM jobs WHERE idem_key='k2'").fetchone()
    checks.append(("永久错误不重试", st == "dead" and row[0] == "dead", f"status={row[0]}"))

    # 6. 临时错误重试后成功
    enqueue(conn, "scan", "k3", {}, now=20.0)
    claim(conn, "w1", 20.0, 5.0)
    st2 = finish_failure(conn, "k3", "reset", 1, 20.0, rng=random.Random(7))
    row2 = conn.execute("SELECT status, visible_at FROM jobs WHERE idem_key='k3'").fetchone()
    checks.append(("临时错误退避重试", row2[0] == "pending" and row2[1] > 20.0, f"{st2} visible_at={row2[1]:.2f}"))

    ok = all(c[1] for c in checks)
    for name, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    print(f"\n{'全部通过' if ok else '存在失败项'}（{len(checks)} 项）")
    conn.close()
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    os.rmdir(tmp)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="重试、幂等与租约")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    return demo()


if __name__ == "__main__":
    sys.exit(main())
