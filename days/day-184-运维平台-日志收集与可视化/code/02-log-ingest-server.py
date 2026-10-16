#!/usr/bin/env python3
"""
Day 184 · 示例 02 —— 真实的日志接收端：HTTP 收日志 + SQLite 落库（WAL）

为什么要有这个文件？
    Day 184 的目标是「日志收集 + 可视化」。收集的第一步是**有一个地方能收**。
    真实项目里这一步通常是 Filebeat / Fluentd / Loki，但它们的本质动作只有三个：
        ① 收（HTTP / TCP / 读文件）  ② 落库（带索引）  ③ 能查（聚合）
    本文件用标准库把这三个动作在**本机真实跑起来**，不依赖任何第三方包。

本文件是一个可以直接 curl 的真实服务：
    POST /ingest   body 是 JSON Lines，逐行入库（也接受单个单行 JSON 对象）
    GET  /stats    按 level 聚合最近 N 秒的日志
    GET  /healthz  健康检查（真实项目里给 K8s / 负载均衡用）

运行方式：
    python3 02-log-ingest-server.py --port 8099 --db /tmp/day184/logs.db
    curl -s -XPOST 127.0.0.1:8099/ingest --data-binary '{"ts":"2026-10-17T06:00:00Z","level":"INFO","msg":"hello"}'
    python3 02-log-ingest-server.py --self-test     # 离线自证（自己起服务、自己打请求）

设计上的两个「为什么」，都是生产里踩出来的：
    1) 为什么用 WAL 而不是默认的 delete 日志模式？
       默认模式下写事务会阻塞所有读；WAL 让「读」和「写」互不阻塞。
       代价是多出 -wal / -shm 两个文件，备份时要一起拷。
    2) 为什么 commit 不是每来一条就提交？
       每条一次 commit 就是每条一次 fsync，吞吐掉到百级/秒。
       批提交（攒 N 条或攒 T 毫秒）能把吞吐拉高一个数量级以上，
       代价是崩溃时最多丢最后一批 —— 05 号示例里有实测数字。

实现上的一个硬约束（真机踩过）：
    sqlite3 的 Connection 默认只能被创建它的线程使用（check_same_thread=True）。
    ThreadingHTTPServer 每条请求一个线程，所以这里用「单连接 + check_same_thread=False
    + 自己加锁串行化写」的做法：写操作本来就该串行，这样既简单又不会踩 sqlite3 的线程检查。
"""

from __future__ import annotations

import json
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,          -- 日志自身时间（ISO8601，带时区）
    received_at TEXT NOT NULL,          -- 服务收到的时间（用来发现「时钟不同步」）
    level       TEXT NOT NULL,
    service     TEXT,
    msg         TEXT,
    raw         TEXT NOT NULL           -- 原始行，永不丢；字段解析失败也能查
);
CREATE INDEX IF NOT EXISTS idx_logs_ts    ON logs(ts);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level, ts);
CREATE INDEX IF NOT EXISTS idx_logs_recv  ON logs(received_at);
"""

INSERT_SQL = "INSERT INTO logs(ts, received_at, level, service, msg, raw) VALUES(?,?,?,?,?,?)"


class LogStore:
    """SQLite 写入器：WAL + 忙等待 + 批提交。"""

    def __init__(self, db_path: str, batch_size: int = 200, flush_interval: float = 1.0):
        self.db_path = db_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._lock = threading.Lock()
        self._pending = 0
        self._last_flush = time.monotonic()
        self.written = 0

        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, timeout=5.0, isolation_level=None,
                                    check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")     # 读写不互斥
        self.conn.execute("PRAGMA synchronous=NORMAL")   # WAL 下 NORMAL 已足够安全
        self.conn.execute("PRAGMA busy_timeout=5000")    # 锁等待 5 秒再报错，而不是立刻失败
        self.conn.executescript(SCHEMA)

    def ingest(self, lines: list[str]) -> int:
        """把一个批次的行写进去，返回处理条数（坏行也入库，raw 保留）。

        显式 BEGIN IMMEDIATE 开一个写事务，攒够 batch_size 或超过 flush_interval 才 COMMIT。
        为什么用 IMMEDIATE 而不是默认的 DEFERRED：IMMEDIATE 在事务开始就拿写锁，
        避免「读到一半才发现要升级锁、结果拿到 SQLITE_BUSY」这种经典死法。
        """
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        rows = []
        for line in lines:
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
                rows.append(
                    (
                        str(ev.get("ts") or now),
                        now,
                        str(ev.get("level", "INFO")).upper(),
                        ev.get("service"),
                        str(ev.get("msg", "")),
                        line,
                    )
                )
            except json.JSONDecodeError:
                # 关键设计：解析不了也要存。日志系统最忌讳「因为格式不对所以丢了」。
                rows.append((now, now, "UNKNOWN", None, "unparsable", line))

        if not rows:
            return 0

        with self._lock:
            if not self.conn.in_transaction:
                self.conn.execute("BEGIN IMMEDIATE")
            self.conn.executemany(INSERT_SQL, rows)
            self._pending += len(rows)
            self.written += len(rows)
            if self._pending >= self.batch_size or (
                time.monotonic() - self._last_flush
            ) >= self.flush_interval:
                self.conn.execute("COMMIT")
                self._pending = 0
                self._last_flush = time.monotonic()
        return len(rows)

    def flush(self) -> None:
        with self._lock:
            if self.conn.in_transaction:
                self.conn.execute("COMMIT")
            self._pending = 0
            self._last_flush = time.monotonic()

    def stats(self, window_seconds: int = 3600) -> dict:
        cutoff = datetime.fromtimestamp(time.time() - window_seconds, timezone.utc).isoformat(
            timespec="milliseconds"
        )
        with self._lock:
            rows = self.conn.execute(
                "SELECT level, COUNT(*) FROM logs WHERE received_at >= ? "
                "GROUP BY level ORDER BY 2 DESC",
                (cutoff,),
            ).fetchall()
            total = self.conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
        return {
            "window_seconds": window_seconds,
            "by_level": {level: count for level, count in rows},
            "total_all_time": total,
        }


class Handler(BaseHTTPRequestHandler):
    store: LogStore = None  # type: ignore[assignment]
    server_version = "day184-ingest/1.0"

    def log_message(self, fmt, *args):  # 安静点：不要把自己的访问日志混进被测日志
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            self._send(200, {"status": "ok"})
        elif parsed.path == "/stats":
            window = int(parse_qs(parsed.query).get("window", ["3600"])[0])
            self._send(200, self.store.stats(window))
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if urlparse(self.path).path != "/ingest":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace")
        # 输入约定：JSON Lines（每行一个对象）。单行 JSON 对象自然也是一行。
        accepted = self.store.ingest(body.splitlines())
        self._send(200, {"accepted": accepted})


def serve(port: int, store: LogStore) -> ThreadingHTTPServer:
    Handler.store = store
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    return httpd


def self_test() -> int:
    """离线自证：起真服务（随机端口）→ 真 HTTP 请求 → 真查库断言。"""
    import tempfile
    import urllib.request

    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / "self.db")
        store = LogStore(db, batch_size=1000)
        httpd = serve(0, store)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}"

        good = json.dumps({"ts": "2026-10-17T06:00:00+00:00", "level": "info", "msg": "ok"})
        slow = json.dumps({"ts": "2026-10-17T06:00:01+00:00", "level": "warning", "msg": "slow"})
        req = urllib.request.Request(
            base + "/ingest", data=(good + "\n" + slow + "\nthis-is-not-json").encode()
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read())
        assert payload["accepted"] == 3, payload

        with urllib.request.urlopen(base + "/stats") as resp:
            stats = json.loads(resp.read())
        assert stats["by_level"]["INFO"] == 1, stats
        assert stats["by_level"]["WARNING"] == 1, stats
        assert stats["by_level"]["UNKNOWN"] == 1, stats   # 坏行也没丢
        assert stats["total_all_time"] == 3, stats

        with urllib.request.urlopen(base + "/healthz") as resp:
            assert json.loads(resp.read())["status"] == "ok"

        store.flush()
        httpd.shutdown()
        print("✅ self-test 通过：真 HTTP 收 3 条（含 1 条坏行）→ SQLite 按 level 聚合正确")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--self-test" in args:
        return self_test()

    def opt(name: str, default):
        return args[args.index(name) + 1] if name in args else default

    port = int(opt("--port", 8099))
    db = opt("--db", "/tmp/day184/logs.db")
    store = LogStore(db)
    httpd = serve(port, store)
    print(f"📥 日志接收端已启动 http://127.0.0.1:{port}   db={db}", flush=True)
    print("   POST /ingest  GET /stats?window=3600  GET /healthz", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        store.flush()
        httpd.server_close()
        print(f"\n🛑 已停止，累计写入 {store.written} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
