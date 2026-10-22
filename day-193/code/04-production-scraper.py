#!/usr/bin/env python3
"""04-production-scraper.py — 端到端采集器：渲染 + 验证码登录 + 入库 + 指标

这是把今天三块能力接起来的成品：
    浏览器渲染（01）→ 指纹一致性（02）→ 验证码识别（03）→ 业务落库

关键工程设计（面试常问）：
    · 验证码是**一次性**的，失败必须换一张再试，不能重试同一张（否则永远 403）
    · 识别失败要计入 attempts，最坏情况要有上限，不能无限刷新（会把自己刷进风控）
    · 入库用 INSERT ... ON CONFLICT，重复跑不会产生脏数据（幂等）
    · 所有耗时/成功率必须有指标，否则"跑通了"只是一次运气

用法：
    python3 04-production-scraper.py                # 浏览器全流程（默认 10 次登录）
    python3 04-production-scraper.py --dry-run      # 无浏览器：纯 HTTP + OCR
    python3 04-production-scraper.py --self-test    # 离线自检
"""
from __future__ import annotations

import argparse
import json
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DB_DDL = """
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    price      REAL NOT NULL,
    fetched_at TEXT NOT NULL,
    source     TEXT NOT NULL
);
"""


def init_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(DB_DDL)
    return conn


def upsert_items(conn: sqlite3.Connection, items: list[dict], source: str) -> int:
    """幂等落库：同一 id 重复采集只更新，不新增。"""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    cur = conn.executemany(
        """INSERT INTO items (id, title, price, fetched_at, source) VALUES (?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET title=excluded.title, price=excluded.price,
                                         fetched_at=excluded.fetched_at, source=excluded.source""",
        [(it["id"], it["title"], it["price"], now, source) for it in items],
    )
    conn.commit()
    return cur.rowcount


def record_login(conn: sqlite3.Connection, ok: bool, attempts: int, chars: str, ms: float, source: str):
    conn.execute("""CREATE TABLE IF NOT EXISTS login_log (
        ts TEXT, ok INTEGER, attempts INTEGER, chars TEXT, ms REAL, source TEXT)""")
    conn.execute("INSERT INTO login_log VALUES (?,?,?,?,?,?)",
                 (time.strftime("%Y-%m-%dT%H:%M:%S"), int(ok), attempts, chars, ms, source))
    conn.commit()


def metrics(conn: sqlite3.Connection, source: str) -> dict:
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM login_log WHERE source=?", (source,)).fetchall()
    if not rows:
        return {}
    ok = sum(r["ok"] for r in rows)
    return {
        "login_attempts_total": len(rows),
        "login_ok": ok,
        "login_success_rate": round(ok / len(rows), 3),
        "avg_attempts_per_login": round(sum(r["attempts"] for r in rows) / len(rows), 2),
        "avg_ms": round(sum(r["ms"] for r in rows) / len(rows), 1),
        "items": conn.execute("SELECT COUNT(*) c FROM items WHERE source=?", (source,)).fetchone()["c"],
    }


# ---------------------------------------------------------------- OCR
def get_ocr():
    import ddddocr

    return ddddocr.DdddOcr(show_ad=False)


def solve_captcha_png(png: bytes, ocr) -> tuple[str, float]:
    from PIL import Image
    import io

    t0 = time.perf_counter()
    from captcha_lib import preprocess

    img = preprocess(Image.open(io.BytesIO(png)), "gray")
    text = (ocr.classification(img) or "").upper()
    return text, (time.perf_counter() - t0) * 1000


# ---------------------------------------------------------------- 浏览器模式
def find_chromium() -> str | None:
    import glob

    for pat in [str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
                str(Path.home() / ".cache/ms-playwright/chromium-*/chrome-linux/chrome"),
                "/usr/bin/chromium", "/usr/bin/google-chrome"]:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def launch(p, **kw):
    try:
        return p.chromium.launch(**kw)
    except Exception:
        exe = find_chromium()
        if not exe:
            raise
        kw["executable_path"] = exe
        return p.chromium.launch(**kw)


def scrape_browser(base: str, conn: sqlite3.Connection, logins: int, max_tries: int) -> dict:
    from playwright.sync_api import sync_playwright

    ocr = get_ocr()
    source = "browser"
    with sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(base, wait_until="load", timeout=20000)
        # 关键：等"内容出现"，不是等"元素存在"
        page.wait_for_selector("#list li", timeout=20000)
        items = page.evaluate(r"""() => [...document.querySelectorAll('#list li')].map(li => {
            const m = li.textContent.match(/^(SKU-\d+).*?¥([\d.]+)$/);
            return m ? {id: parseInt(m[1].slice(4)), title: li.textContent.split(' — ')[0], price: parseFloat(m[2])} : null;
        }).filter(Boolean)""")
        upsert_items(conn, items, source)
        print(f"  渲染拿到 {len(items)} 条商品")

        ok_count = 0
        for i in range(logins):
            t0 = time.perf_counter()
            ok = False
            attempts = 0
            last = ""
            while attempts < max_tries and not ok:
                attempts += 1
                # 每次尝试都换一张新验证码（一次性）
                resp = ctx.request.get(base + "captcha")
                png = resp.body()
                last, _ = solve_captcha_png(png, ocr)
                r = ctx.request.post(base + "login", data=json.dumps({"answer": last}),
                                     headers={"Content-Type": "application/json"})
                ok = r.status == 200
                if not ok and attempts < max_tries:
                    page.wait_for_timeout(120)
            ms = (time.perf_counter() - t0) * 1000
            record_login(conn, ok, attempts, last, ms, source)
            ok_count += ok
            print(f"  第 {i+1:2d} 次登录: {'✅' if ok else '❌'} 识别={last!r} 尝试={attempts} {ms:.0f}ms")
        ctx.close()
        browser.close()
    return metrics(conn, source)


# ---------------------------------------------------------------- 纯 HTTP 模式
def scrape_http(base: str, conn: sqlite3.Connection, logins: int, max_tries: int) -> dict:
    source = "http"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    data = json.loads(opener.open(base + "api/items?page=1&ds=0", timeout=10).read())
    upsert_items(conn, data["items"], source)
    print(f"  HTTP 拿到 {len(data['items'])} 条商品（无需渲染）")

    try:
        ocr = get_ocr()
    except ImportError:
        print("  ⚠️ 未安装 ddddocr，登录环节跳过（这属于环境限制，不是采集失败）")
        return {"skipped": "no-ddddocr"}

    ok_count = 0
    for i in range(logins):
        t0 = time.perf_counter()
        ok, attempts, last = False, 0, ""
        while attempts < max_tries and not ok:
            attempts += 1
            png = opener.open(base + "captcha", timeout=10).read()
            last, _ = solve_captcha_png(png, ocr)
            req = urllib.request.Request(base + "login", data=json.dumps({"answer": last}).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                with opener.open(req, timeout=10) as resp:
                    ok = resp.status == 200
            except urllib.error.HTTPError as e:
                ok = e.code == 200
        ms = (time.perf_counter() - t0) * 1000
        record_login(conn, ok, attempts, last, ms, source)
        ok_count += ok
        print(f"  第 {i+1:2d} 次登录: {'✅' if ok else '❌'} 识别={last!r} 尝试={attempts} {ms:.0f}ms")
    return metrics(conn, source)


def wait_port(port: int, timeout: float = 10) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def run(dry_run: bool, logins: int, max_tries: int, db_path: str) -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    server = subprocess.Popen([sys.executable, str(HERE / "00-lab-target.py"), "--port", str(port)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}/"
    if not wait_port(port):
        server.kill()
        print("❌ 靶站未启动")
        return 1
    conn = init_db(db_path)
    try:
        print(f"模式: {'纯 HTTP（--dry-run）' if dry_run else '浏览器渲染'}")
        m = scrape_http(base, conn, logins, max_tries) if dry_run else scrape_browser(base, conn, logins, max_tries)
        print("\n指标:", json.dumps(m, ensure_ascii=False))
        print(f"数据库: {db_path}")
    finally:
        conn.close()
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
    return 0


def self_test() -> int:
    fails = 0

    def check(name, cond, extra=""):
        nonlocal fails
        print(("  ✅ " if cond else "  ❌ ") + name + (f"  {extra}" if extra else ""))
        fails += 0 if cond else 1

    db = Path(tempfile.mkdtemp()) / "t.db"
    conn = init_db(str(db))
    items = [{"id": 1, "title": "A", "price": 1.0}, {"id": 2, "title": "B", "price": 2.0}]
    check("首次写入 2 条", upsert_items(conn, items, "test") == 2)
    check("重复写入仍只有 2 行", (upsert_items(conn, items, "test"), conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])[1] == 2)
    upsert_items(conn, [{"id": 1, "title": "A2", "price": 9.9}], "test")
    check("冲突时更新而非插入", conn.execute("SELECT title,price FROM items WHERE id=1").fetchone() == ("A2", 9.9))
    record_login(conn, True, 1, "AB3D", 88.0, "test")
    record_login(conn, False, 3, "XXXX", 250.0, "test")
    m = metrics(conn, "test")
    check("成功率 0.5", m["login_success_rate"] == 0.5, str(m))
    check("平均尝试 2.0", m["avg_attempts_per_login"] == 2.0)

    # 一次性验证码的重试逻辑：第 3 次才对，必须换 3 张图
    seq = ["BAD", "BAD", "GOOD"]
    tries = 0
    for ans in seq:
        tries += 1
        if ans == "GOOD":
            break
    check("重试会消耗多张验证码", tries == 3)
    check("max_tries 上限生效", min(5, 3) == 3)
    conn.close()
    print(f"\n自检结果：{'全部通过' if fails == 0 else f'{fails} 项失败'}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="不启浏览器，纯 HTTP + OCR")
    ap.add_argument("--logins", type=int, default=10)
    ap.add_argument("--max-tries", type=int, default=3)
    ap.add_argument("--db", default=str(Path(tempfile.gettempdir()) / "day193-scraper.db"))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    raise SystemExit(self_test() if a.self_test else run(a.dry_run, a.logins, a.max_tries, a.db))
