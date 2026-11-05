#!/usr/bin/env python3
"""
Day 189 · 04 — 入库性能实测：事务、批量、索引

资产库每天要吃几千到几十万条观测，写法不同差 1~2 个数量级。
本脚本在**本机实时计时**，不引用别人的结论。

对比项：
  A. 自动提交 + 逐条 INSERT     （每个 INSERT 一次 fsync）
  B. 显式事务 + 逐条 INSERT
  C. 显式事务 + executemany
  D. 显式事务 + UPSERT（先查再写，模拟真实入库）
  E. 查询：无索引 vs 有索引（按 (ip, port) 精确定位）

用法：
    python3 04-perf-benchmark.py                # 默认 20000 行
    python3 04-perf-benchmark.py --rows 50000
    python3 04-perf-benchmark.py --self-test
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE {table} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    port INTEGER NOT NULL,
    proto TEXT NOT NULL DEFAULT 'tcp',
    service TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    UNIQUE (ip, port, proto)
);
"""


def make_rows(n: int) -> list[tuple]:
    ts = "2026-10-19T00:00:00+00:00"
    rows = []
    for i in range(n):
        ip = f"10.{i // 65536 % 256}.{i // 256 % 256}.{i % 256}"
        service = ("http", "https", "ssh", "mysql")[i % 4]
        rows.append((ip, 10000 + i % 50000, "tcp", service, ts, ts))
    return rows


def fresh(path: Path, table: str = "assets") -> sqlite3.Connection:
    conn = sqlite3.connect(path, isolation_level=None)
    conn.executescript(SCHEMA.format(table=table))
    return conn


def timed(fn) -> float:
    t = time.perf_counter()
    fn()
    return (time.perf_counter() - t) * 1000


def bench(rows: list[tuple], workdir: Path,
          autocommit_rows: int = 100) -> dict[str, dict]:
    """返回 {用例: {n, ms}}。autocommit 单独用小样本：本机每行 fsync 约 15ms。"""
    out: dict[str, dict] = {}
    insert_sql = ("INSERT INTO assets(ip, port, proto, service, first_seen, last_seen) "
                  "VALUES (?, ?, ?, ?, ?, ?)")
    a_rows = rows[:autocommit_rows]

    # A. autocommit：每个 INSERT 独立事务
    db = workdir / "a.db"
    conn = fresh(db)
    def a():
        for r in a_rows:
            conn.execute(insert_sql, r)
    out["A autocommit 逐条"] = {"n": len(a_rows), "ms": timed(a)}
    conn.close()

    # B. 单事务逐条
    db = workdir / "b.db"
    conn = fresh(db)
    def b():
        conn.execute("BEGIN")
        for r in rows:
            conn.execute(insert_sql, r)
        conn.execute("COMMIT")
    out["B 单事务 逐条"] = {"n": len(rows), "ms": timed(b)}
    conn.close()

    # C. 单事务 executemany
    db = workdir / "c.db"
    conn = fresh(db)
    def c():
        conn.execute("BEGIN")
        conn.executemany(insert_sql, rows)
        conn.execute("COMMIT")
    out["C 单事务 executemany"] = {"n": len(rows), "ms": timed(c)}
    conn.close()

    # D. UPSERT：先 SELECT，命中 UPDATE，未命中 INSERT（真实增量入库路径）
    db = workdir / "d.db"
    conn = fresh(db)
    def d():
        conn.execute("BEGIN")
        for r in rows:
            cur = conn.execute(
                "SELECT id FROM assets WHERE ip=? AND port=? AND proto=?",
                (r[0], r[1], r[2]),
            ).fetchone()
            if cur is None:
                conn.execute(insert_sql, r)
            else:
                conn.execute("UPDATE assets SET last_seen=? WHERE id=?", (r[5], cur[0]))
        conn.execute("COMMIT")
    out["D 单事务 UPSERT"] = {"n": len(rows), "ms": timed(d)}
    conn.close()

    return out


def bench_lookup(n: int, workdir: Path, queries: int = 500) -> tuple[float, float]:
    rows = make_rows(n)
    insert_sql = ("INSERT INTO assets(ip, port, proto, service, first_seen, last_seen) "
                  "VALUES (?, ?, ?, ?, ?, ?)")

    db = workdir / "noindex.db"
    conn = fresh(db)
    conn.execute("BEGIN")
    conn.executemany(insert_sql, rows)
    conn.execute("COMMIT")
    conn.execute("ANALYZE")
    # SQLite 对 UNIQUE(ip,port,proto) 会自动建索引，所以这里显式查询一个**非索引列**
    # 才能看到"无索引"的真实代价：按 service 过滤。
    def no_index():
        for _ in range(queries):
            conn.execute("SELECT COUNT(*) FROM assets WHERE service='http'").fetchone()
    t_no = timed(no_index)
    conn.close()

    db = workdir / "indexed.db"
    conn = fresh(db)
    conn.execute("BEGIN")
    conn.executemany(insert_sql, rows)
    conn.execute("COMMIT")
    conn.execute("CREATE INDEX idx_service ON assets(service)")
    conn.execute("ANALYZE")
    def indexed():
        for _ in range(queries):
            conn.execute("SELECT COUNT(*) FROM assets WHERE service='http'").fetchone()
    t_yes = timed(indexed)
    conn.close()
    return t_no, t_yes


def self_test() -> int:
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        rows = make_rows(500)
        result = bench(rows, workdir, autocommit_rows=60)
        for name, rec in result.items():
            assert rec["ms"] > 0, (name, rec)
        expected = {"a": 60, "b": 500, "c": 500, "d": 500}
        for db, want in expected.items():
            conn = sqlite3.connect(workdir / f"{db}.db")
            assert conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == want, db
            conn.close()
        t_no, t_yes = bench_lookup(2000, workdir, queries=50)
        assert t_no > 0 and t_yes > 0
    print(f"✅ 04 self-test 通过：4 种写入路径行数一致，索引查询 {t_no:.1f}ms → {t_yes:.1f}ms")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="SQLite 入库性能实测")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--rows", type=int, default=5000,
                    help="B/C/D 用例行数（A autocommit 只取前 100 行）")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    n = args.rows
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        rows = make_rows(n)
        print(f"测试条件：B/C/D {n} 行，A 仅前 100 行 · {len(rows[0])} 列 · "
              f"SQLite {sqlite3.sqlite_version} · {sys.version.split()[0]} · 单次运行（未取均值）")
        result = bench(rows, workdir)
        ref = result["B 单事务 逐条"]["ms"] / result["B 单事务 逐条"]["n"]
        print(f"\n{'写入方式':<22}{'行数':>6}{'耗时(ms)':>10}{'行/秒':>10}"
              f"{'相对B(每行)':>12}{'µs/行':>9}")
        for name, rec in result.items():
            per = rec["ms"] / rec["n"]
            print(f"{name:<22}{rec['n']:>6}{rec['ms']:>10.1f}{1000 / per:>10.0f}"
                  f"{ref / per:>11.2f}x{per * 1000:>9.0f}")

        lookup_rows = 20000
        t_no, t_yes = bench_lookup(lookup_rows, workdir)
        print(f"\n查询 500 次 service='http'（{lookup_rows} 行）："
              f"无索引 {t_no:.1f}ms / 有索引 {t_yes:.1f}ms，加速 {t_no / t_yes:.1f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
