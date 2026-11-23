#!/usr/bin/env python3
"""Day 191 · 进阶：错误分类 + 全抖动退避 + 幂等落库 + 断点续爬

三件事决定爬虫能不能“跑一整夜”：
  1. 哪些错误值得重试（重试 404 是纯浪费配额）
  2. 重试间隔怎么算（固定 1s 会让所有 worker 同时回撞）
  3. 重试成功后，数据会不会写两遍（SQLite 唯一约束 > 应用层“我记得写过”）

用法：
  python3 03-retry-and-sink.py --self-test
  python3 03-retry-and-sink.py --url http://127.0.0.1:8099 --pages 40 --db /tmp/day191.sqlite
  python3 03-retry-and-sink.py --resume --db /tmp/day191.sqlite --url http://127.0.0.1:8099
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
PERMANENT_STATUS = {400, 401, 403, 404, 405, 410, 451}


class PermanentError(Exception):
    """重试也不会变好的错误：调用方必须放弃，不要吃掉重试预算。"""


class RetryableError(Exception):
    def __init__(self, msg: str, retry_after: float | None = None) -> None:
        super().__init__(msg)
        self.retry_after = retry_after


@dataclass
class RetryPolicy:
    attempts: int = 4
    base: float = 0.1
    cap: float = 2.0
    jitter: str = "full"  # none | full

    def delay(self, attempt: int, retry_after: float | None = None, rng=random) -> float:
        """attempt 从 1 开始。full jitter = random(0, ceiling)，
        它把同时失败的 N 个 worker 摊开，而不是让它们在同一毫秒再撞一次。"""
        if retry_after is not None:
            return min(self.cap, max(0.0, retry_after))
        ceiling = min(self.cap, self.base * (2 ** (attempt - 1)))
        if self.jitter == "full":
            return rng.uniform(0, ceiling)
        return ceiling


def classify(exc: BaseException) -> tuple[bool, float | None]:
    """返回 (是否可重试, Retry-After 秒数)。"""
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in RETRYABLE_STATUS:
            ra = exc.headers.get("Retry-After") if exc.headers else None
            try:
                return True, float(ra) if ra is not None else None
            except ValueError:
                return True, None
        if exc.code in PERMANENT_STATUS:
            return False, None
        return False, None
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return True, None
    return False, None


def fetch(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        retryable, ra = classify(e)
        raise (RetryableError(f"HTTP {e.code}", ra) if retryable else PermanentError(f"HTTP {e.code}")) from e
    except Exception as e:
        retryable, _ = classify(e)
        raise (RetryableError(e.__class__.__name__) if retryable else PermanentError(str(e))) from e


def fetch_with_retry(url: str, policy: RetryPolicy | None = None,
                     *, sleeper=time.sleep, log: list | None = None) -> tuple[int, str, int]:
    policy = policy or RetryPolicy()
    last: BaseException | None = None
    for attempt in range(1, policy.attempts + 1):
        try:
            code, body = fetch(url)
            if log is not None:
                log.append({"url": url, "attempt": attempt, "ok": True})
            return code, body, attempt
        except PermanentError as e:
            if log is not None:
                log.append({"url": url, "attempt": attempt, "ok": False, "kind": "permanent", "err": str(e)})
            raise
        except RetryableError as e:
            last = e
            if log is not None:
                log.append({"url": url, "attempt": attempt, "ok": False, "kind": "retryable", "err": str(e)})
            if attempt == policy.attempts:
                break
            sleeper(policy.delay(attempt, e.retry_after))
    raise RetryableError(f"retries exhausted: {last}")


SCHEMA = """
CREATE TABLE IF NOT EXISTS pages (
    url        TEXT PRIMARY KEY,   -- 规范 URL 即幂等键
    title      TEXT,
    body_len   INTEGER,
    status     INTEGER,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id     TEXT PRIMARY KEY,
    started_at TEXT,
    pages      INTEGER,
    errors     INTEGER
);
CREATE TABLE IF NOT EXISTS failures (
    url      TEXT PRIMARY KEY,
    attempts INTEGER,
    last_err TEXT
);
"""


def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def save_page(conn: sqlite3.Connection, url: str, title: str, body_len: int, status: int) -> bool:
    """UPSERT：重复抓同一页不会长出第二行，只会刷新 fetched_at。
    返回 True 表示这是一次“新写入”，False 表示覆盖更新。
    """
    exists = conn.execute("SELECT 1 FROM pages WHERE url=?", (url,)).fetchone() is not None
    conn.execute(
        "INSERT INTO pages(url,title,body_len,status,fetched_at) VALUES(?,?,?,?,datetime('now')) "
        "ON CONFLICT(url) DO UPDATE SET title=excluded.title, body_len=excluded.body_len, "
        "status=excluded.status, fetched_at=excluded.fetched_at",
        (url, title, body_len, status),
    )
    conn.commit()
    return not exists


def title_of(html: str) -> str:
    i, j = html.find("<title>"), html.find("</title>")
    return html[i + 7:j].strip() if i >= 0 and j > i else ""


def record_failure(conn: sqlite3.Connection, url: str, attempts: int, err: str) -> None:
    conn.execute(
        "INSERT INTO failures(url,attempts,last_err) VALUES(?,?,?) "
        "ON CONFLICT(url) DO UPDATE SET attempts=excluded.attempts, last_err=excluded.last_err",
        (url, attempts, err),
    )
    conn.commit()


def pending_urls(conn: sqlite3.Connection, all_urls: list[str]) -> list[str]:
    have = {r[0] for r in conn.execute("SELECT url FROM pages")}
    return [u for u in all_urls if u not in have]


def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    # 1) 分类：404 永久、503 可重试、429 带 Retry-After
    def fake(code: int, headers: dict | None = None):
        return urllib.error.HTTPError("http://x", code, "e", __import__("email.message").message.Message(), None)

    checks.append(("404 不可重试", classify(fake(404))[0] is False))
    checks.append(("503 可重试", classify(fake(503))[0] is True))
    checks.append(("URLError 可重试", classify(urllib.error.URLError("x"))[0] is True))

    # 2) 退避上限与抖动范围
    p = RetryPolicy(attempts=5, base=0.1, cap=1.0, jitter="full")
    seq = [p.delay(a, rng=random.Random(0)) for a in range(1, 6)]
    ceilings = [min(1.0, 0.1 * 2 ** (a - 1)) for a in range(1, 6)]
    checks.append(("抖动不超过封顶", all(s <= c + 1e-9 for s, c in zip(seq, ceilings))))
    checks.append(("指数封顶生效", ceilings == [0.1, 0.2, 0.4, 0.8, 1.0]))
    checks.append(("Retry-After 优先", p.delay(1, retry_after=0.5) == 0.5))

    # 3) 真实重试：靶站 /flaky/1 第一次 503，第二次 200
    import threading
    from http.server import ThreadingHTTPServer
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    spec = importlib.util.spec_from_file_location("lab", os.path.join(here, "00-local-server.py"))
    lab = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lab)
    srv = lab.serve(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    log: list = []
    code, body, used = fetch_with_retry(base + "/flaky/2", RetryPolicy(base=0.01, cap=0.02),
                                        sleeper=lambda s: time.sleep(s), log=log)
    checks.append(("503 后重试成功", code == 200 and used == 2))
    checks.append(("重试有完整轨迹", len(log) == 2 and log[0]["ok"] is False))
    try:
        fetch_with_retry(base + "/nope", RetryPolicy(base=0.01))
        checks.append(("404 直接放弃", False))
    except PermanentError:
        checks.append(("404 直接放弃", True))
    checks.append(("404 不消耗重试", len(log) == 2))

    # 4) 幂等落库
    db = "/tmp/day191-selftest.sqlite"
    if os.path.exists(db):
        os.remove(db)
    conn = open_db(db)
    a = save_page(conn, "http://x/1", "t1", 10, 200)
    b = save_page(conn, "http://x/1", "t2", 12, 200)
    n = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    checks.append(("UPSERT 不产生重复行", a is True and b is False and n == 1))
    checks.append(("UPSERT 刷新内容", conn.execute("SELECT title FROM pages").fetchone()[0] == "t2"))
    conn.close()
    srv.shutdown()

    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    passed = sum(ok for _, ok in checks)
    print(f"\nself-test: {passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--url", default="http://127.0.0.1:8099")
    ap.add_argument("--pages", type=int, default=40)
    ap.add_argument("--db", default="/tmp/day191.sqlite")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    base = a.url.rstrip("/")
    urls = [f"{base}/page/{i}" for i in range(1, a.pages + 1)] + [f"{base}/flaky/{i}" for i in range(1, 6)]
    conn = open_db(a.db)
    todo = pending_urls(conn, urls) if a.resume else urls
    if a.dry_run:
        print(json.dumps({"db": a.db, "total": len(urls), "todo": len(todo),
                          "resume": a.resume}, indent=2))
        return 0

    t0 = time.perf_counter()
    ok = fail = new = 0
    for u in todo:
        try:
            code, body, used = fetch_with_retry(u, RetryPolicy(base=0.05, cap=0.4))
            new += save_page(conn, u, title_of(body), len(body), code)
            ok += 1
        except (PermanentError, RetryableError) as e:
            record_failure(conn, u, 4, str(e))
            fail += 1
    wall = time.perf_counter() - t0
    total = conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    print(json.dumps({"todo": len(todo), "ok": ok, "fail": fail, "new_rows": new,
                      "rows_total": total, "wall_s": round(wall, 2)}, ensure_ascii=False))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
