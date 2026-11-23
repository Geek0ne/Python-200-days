#!/usr/bin/env python3
"""
Day 184 · 示例 04 —— 翻车复现：SQLite 并发写导致的『database is locked』

为什么要有这个文件？（这是本日最值钱的部分）
    我自己第一版日志平台就死在这里：采集器一个进程、平台 API 一个进程，
    两个进程都往同一个 logs.db 写。低流量时一切正常，压测一开始就出现：

        sqlite3.OperationalError: database is locked

    然后是更糟的：日志**直接被吞掉了**（写入失败、异常没人 catch，行就没了）。

复现逻辑（本文件跑的是真并发，用的是 multiprocessing 的真进程）：
    进程 A：开一个写事务 → 写一行 → 睡 1.5 秒 → COMMIT（模拟「写一半卡住」）
    进程 B：0.3 秒后开始写 → 撞上 A 的写锁

    bad  模式：默认 journal + timeout=0        → B 立刻报 database is locked
    good 模式：WAL + busy_timeout=5000          → B 等 A 提交后成功，并记录等了多少毫秒

为什么 WAL 能解决？
    默认的 rollback journal 模式下，一个写事务进行中，其他连接连**读**都被挡住，
    写更是直接拿不到锁；WAL 模式下写者只往 -wal 文件追加，读的是快照，
    同一时刻「一个写者 + 任意多个读者」可以并存。写者之间仍然互斥，
    所以还需要 busy_timeout —— 让拿不到锁的连接等一会儿，而不是立刻失败。

为什么还要 busy_timeout？
    SQLITE_BUSY 是「立刻返回」的错误，不是「等一等」的。默认 sqlite3 的 timeout=5s
    其实已经给了忙等待，但很多人手写 connection 时用 timeout=0（或没设），
    或者用 PRAGMA busy_timeout=0，就等于告诉 SQLite「别等，直接报错」。

运行方式：
    python3 04-pitfall-db-locked.py --mode bad       # 复现报错（预期 rc=1）
    python3 04-pitfall-db-locked.py --mode good      # 修复后成功（预期 rc=0）
    python3 04-pitfall-db-locked.py --self-test      # 两种模式都跑一遍并断言

注意：本文件只在 /tmp 下建临时库，跑完自己删，不留状态。
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = "CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, ts TEXT, msg TEXT)"


def writer_a(db: str, hold_seconds: float, exclusive: bool) -> None:
    """持有写事务 hold_seconds 秒。exclusive=True 用 BEGIN EXCLUSIVE，让冲突更确定。"""
    conn = sqlite3.connect(db, timeout=5.0, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL" if not exclusive else "PRAGMA journal_mode=DELETE")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("INSERT INTO logs(ts,msg) VALUES(?,?)", ("t0", "writer-A"))
    time.sleep(hold_seconds)
    conn.execute("COMMIT")
    conn.close()


def writer_b(db: str, mode: str) -> tuple[bool, float, str]:
    """返回 (是否成功, 等待秒数, 错误信息)。"""
    if mode == "good":
        conn = sqlite3.connect(db, timeout=5.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
    else:
        # bad：timeout=0 → 不等，撞锁立刻抛错
        conn = sqlite3.connect(db, timeout=0.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=0")
    started = time.monotonic()
    try:
        conn.execute("INSERT INTO logs(ts,msg) VALUES(?,?)", ("t1", "writer-B"))
        return True, time.monotonic() - started, ""
    except sqlite3.OperationalError as exc:
        return False, time.monotonic() - started, f"{type(exc).__name__}: {exc}"
    finally:
        conn.close()


def run_case(mode: str, hold_seconds: float = 1.5, db: str | None = None) -> dict:
    cleanup = db is None
    if db is None:
        tmpdir = tempfile.mkdtemp(prefix="day184-lock-")
        db = str(Path(tmpdir) / "lock.db")

    seed = sqlite3.connect(db)
    seed.execute(SCHEMA)
    seed.commit()
    seed.close()

    proc_a = mp.Process(target=writer_a, args=(db, hold_seconds, mode == "bad"))
    proc_a.start()
    time.sleep(0.3)  # 等 A 真的把写锁拿到手
    ok, waited, err = writer_b(db, mode)
    proc_a.join(timeout=10)

    result = {"mode": mode, "ok": ok, "waited_s": round(waited, 3), "error": err, "db": db}
    if cleanup:
        import shutil

        shutil.rmtree(Path(db).parent, ignore_errors=True)
    return result


def self_test() -> int:
    """断言：bad 模式必须失败且错误信息含 locked；good 模式必须成功且等待 > hold 的一半。"""
    bad = run_case("bad", hold_seconds=1.0)
    print(f"  bad  模式 → ok={bad['ok']} waited={bad['waited_s']}s error={bad['error']}")
    assert bad["ok"] is False, "bad 模式本应报 database is locked，居然成功了"
    assert "locked" in bad["error"], bad["error"]

    good = run_case("good", hold_seconds=1.0)
    print(f"  good 模式 → ok={good['ok']} waited={good['waited_s']}s")
    assert good["ok"] is True, "good 模式本应等到锁释放后成功"
    assert good["waited_s"] > 0.5, "good 模式应该真的等了 A 一段时间"

    print("✅ self-test 通过：bad 模式复现 database is locked，good 模式（WAL+busy_timeout）等到锁后成功")
    print(f"   关键数字：bad 失败耗时 {bad['waited_s']}s（几乎立即失败） / "
          f"good 等待 {good['waited_s']}s 后成功")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()

    mode = args[args.index("--mode") + 1] if "--mode" in args else "bad"
    hold = float(args[args.index("--hold") + 1]) if "--hold" in args else 1.5
    result = run_case(mode, hold_seconds=hold)
    print(f"mode={result['mode']} ok={result['ok']} waited={result['waited_s']}s")
    if not result["ok"]:
        print(f"❌ 写入失败: {result['error']}")
        print("   修复：01) PRAGMA journal_mode=WAL  02) PRAGMA busy_timeout=5000（或 connect(timeout=5)）")
        print("   再想一层：写入失败的日志不能丢 —— 采集器要有降级落盘（见 03 号示例的 Sender.spill）")
        return 1
    print("✅ 写入成功：WAL + busy_timeout 让写者排队而不是报错")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
