#!/usr/bin/env python3
"""
Day 188 · 00 — 本地漏洞靶场（仅供本机实验）

启动一个带真实 SQLite 的 HTTP 服务，故意保留两个漏洞：
  /product?id=1   → 字符串拼接 SQL，存在 SQL 注入
  /search?q=...   → 原样回显，存在反射型 XSS
  /safe-search    → 正确转义，作为对照组

为什么用标准库而不是 DVWA/靶场镜像：
  · 零依赖、离线可跑、启动 <1 秒；
  · 代码完全可读，读者能对照漏洞成因；
  · 只监听 127.0.0.1，不对外暴露。

用法：
  python3 00-vuln-lab.py --port 18081
  # 另开终端：curl 'http://127.0.0.1:18081/product?id=1'
"""

from __future__ import annotations

import argparse
import html
import json
import sqlite3
import sys
import tempfile
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PRODUCTS = [
    (1, "Mechanical Keyboard", 89.0),
    (2, "Trackball Mouse", 45.5),
    (3, 'Monitor 27"', 239.0),
]


def init_db(path: str) -> None:
    conn = sqlite3.connect(path)
    with conn:
        conn.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
        conn.executemany("INSERT OR REPLACE INTO products(id, name, price) VALUES (?, ?, ?)", PRODUCTS)
    conn.close()


class LabHandler(BaseHTTPRequestHandler):
    server_version = "VulnLab/1.0"

    def _send(self, status: int, body: str, ctype: str = "text/html; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

        if parsed.path == "/health":
            self._send(200, json.dumps({"ok": True}), "application/json")
            return

        if parsed.path == "/product":
            pid = qs.get("id", ["1"])[0]
            # ⚠️ 故意漏洞：字符串拼接，未参数化
            sql = "SELECT id, name, price FROM products WHERE id = " + pid
            try:
                conn = sqlite3.connect(self.server.db_path)
                row = conn.execute(sql).fetchone()
                conn.close()
            except sqlite3.Error as exc:
                # ⚠️ 故意把数据库错误回显给客户端（error-based 信号）
                self._send(500, f"SQL error: {exc}")
                return
            if row:
                self._send(200, f"<html><title>Product</title><h1>{row[1]}</h1><p>Price: {row[2]}</p></html>")
            else:
                self._send(404, "<html><title>Not found</title><p>No such product</p></html>")
            return

        if parsed.path == "/search":
            q = qs.get("q", [""])[0]
            # ⚠️ 故意漏洞：原样回显，未转义
            self._send(200, f"<html><title>Search</title><h1>Search</h1><p>Results for: {q}</p></html>")
            return

        if parsed.path == "/safe-search":
            q = html.escape(qs.get("q", [""])[0], quote=True)
            self._send(200, f"<html><title>Search</title><h1>Search</h1><p>Results for: {q}</p></html>")
            return

        self._send(404, "<html><title>Not found</title><p>not found</p></html>")

    def log_message(self, fmt, *args):
        # 实验时保留一行访问日志，便于观察扫描器发了什么
        sys.stderr.write("[lab] " + (fmt % args) + "\n")


def serve(host: str = "127.0.0.1", port: int = 0):
    """启动靶场，返回 (server, thread, base_url)。port=0 由内核分配。"""
    tmp = tempfile.NamedTemporaryFile(prefix="vulnlab-", suffix=".db", delete=False)
    tmp.close()
    init_db(tmp.name)

    server = ThreadingHTTPServer((host, port), LabHandler)
    server.db_path = tmp.name
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{host}:{server.server_address[1]}"
    return server, thread, base_url


def main() -> int:
    parser = argparse.ArgumentParser(description="本地漏洞靶场（仅 127.0.0.1）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost"):
        parser.error("实验靶场只允许监听 127.0.0.1")

    server, _, base_url = serve(args.host, args.port)
    print(f"[*] 靶场已启动: {base_url}")
    print(f"    漏洞点: {base_url}/product?id=1  (SQLi)")
    print(f"             {base_url}/search?q=test (XSS)")
    print(f"    对照组: {base_url}/safe-search?q=test")
    print("[*] Ctrl-C 停止")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[*] 正在停止...")
    finally:
        server.shutdown()
        server.server_close()
        Path(server.db_path).unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

