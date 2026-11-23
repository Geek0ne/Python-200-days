#!/usr/bin/env python3
"""
Day 184 · 示例 05 —— 写入性能实测：逐条提交 vs 批提交 vs WAL

为什么要有这个文件？
    日志平台的瓶颈几乎永远不在「解析 JSON」，而在「写多少条、提交多少次」。
    提交（COMMIT）在默认 synchronous=FULL 下意味着一次 fsync —— 磁盘每秒能做的
    fsync 数量是硬上限，所以「每条日志提交一次」的吞吐会被钉死在几百到几千/秒。

    本文件把四种写法放在同一台机器、同一份数据上跑，给出**实测数字**，
    而不是引用别人的博客。所有数字都由 --repeat 次运行取中位数。

四种写法：
    A per-row-commit   : 每条 INSERT 自己一个事务（DELETE journal = 默认模式）
    B per-row-commit-wal: 同上但 journal_mode=WAL
    C single-txn       : 全部 N 条塞进一个事务（内存爆炸风险版）
    D batched-1000     : 每 1000 条一个事务（生产推荐的折中）

运行方式：
    python3 05-bench-insert.py                       # 默认 20000 条 × 3 次
    python3 05-bench-insert.py --rows 5000 --repeat 3
    python3 05-bench-insert.py --self-test           # 快速版，断言批提交确实更快

读数字的正确姿势（写在前面，避免误读）：
    * 这些数字是**本机**的（4 vCPU / virtio 块设备 / overlay 上的 ext4），
      换机器必然不同，但相对关系（B 比 A 快、D 比 A 快一到两个数量级）是稳的。
    * 「快」不等于「该用」：C 模式在一个事务里塞全部数据，崩溃时全丢且内存吃紧，
      生产里用 D。
"""

from __future__ import annotations

import argparse
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = "CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, ts TEXT, level TEXT, msg TEXT)"
ROW = ("2026-10-17T06:00:00+00:00", "INFO", "benchmark row")


def bench(strategy: str, rows: int, db: str, batch: int = 1000) -> float:
    """跑一种写入策略，返回每秒写入条数。"""
    Path(db).unlink(missing_ok=True)
    Path(db + "-wal").unlink(missing_ok=True)
    Path(db + "-shm").unlink(missing_ok=True)

    conn = sqlite3.connect(db, isolation_level=None)
    if strategy == "A":
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
    else:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(SCHEMA)

    sql = "INSERT INTO logs(ts,level,msg) VALUES(?,?,?)"
    payload = [ROW] * rows
    started = time.perf_counter()

    if strategy in ("A", "B"):
        # 每条 INSERT 一个隐式事务（isolation_level=None = 自动提交）
        for _ in range(rows):
            conn.execute(sql, ROW)
    elif strategy == "C":
        conn.execute("BEGIN IMMEDIATE")
        conn.executemany(sql, payload)
        conn.execute("COMMIT")
    elif strategy == "D":
        for start in range(0, rows, batch):
            conn.execute("BEGIN IMMEDIATE")
            conn.executemany(sql, payload[start : start + batch])
            conn.execute("COMMIT")
    else:
        raise ValueError(strategy)

    elapsed = time.perf_counter() - started
    conn.close()
    return rows / elapsed


def run_all(rows: int, repeat: int) -> dict:
    results: dict[str, list[float]] = {k: [] for k in "ABCD"}
    with tempfile.TemporaryDirectory(prefix="day184-bench-") as tmp:
        for _ in range(repeat):
            for strategy in "ABCD":
                db = str(Path(tmp) / f"bench-{strategy}.db")
                results[strategy].append(bench(strategy, rows, db))
    return {k: {"median": statistics.median(v), "runs": [round(x) for x in v]}
            for k, v in results.items()}


def self_test() -> int:
    """快速断言：批提交必须显著快于逐条提交。"""
    res = run_all(rows=1000, repeat=2)
    a = res["A"]["median"]
    d = res["D"]["median"]
    b = res["B"]["median"]
    print(f"  1000 行 × 2 次：A(逐条提交)={a:,.0f}/s  B(逐条+WAL)={b:,.0f}/s  D(批1000)={d:,.0f}/s")
    assert d > a * 2, f"批提交应至少快 2 倍，实际 {d / a:.1f} 倍"
    assert b > a, "WAL 应比默认 journal 快"
    print(f"✅ self-test 通过：批提交比逐条提交快 {d / a:.1f} 倍；WAL 比默认 journal 快 {b / a:.1f} 倍")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLite 日志写入策略实测")
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    print(f"=== SQLite 写入实测：{args.rows} 行 × {args.repeat} 次，取中位数 ===")
    res = run_all(args.rows, args.repeat)
    labels = {
        "A": "per-row-commit (DELETE journal, FULL)",
        "B": "per-row-commit (WAL, NORMAL)",
        "C": "single-txn (全部一个事务)",
        "D": "batched-1000 (每 1000 条一事务)",
    }
    base = res["A"]["median"]
    for key in "ABCD":
        r = res[key]
        print(f"  {key} {labels[key]:<38} {r['median']:>10,.0f} 条/秒   "
              f"x{r['median'] / base:>6.1f}   各次={[f'{x:,.0f}' for x in r['runs']]}")
    print("\n结论：把提交次数从 N 降到 N/batch，吞吐提升一到两个数量级；"
          "WAL 额外再提一截（读写不再互斥）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
