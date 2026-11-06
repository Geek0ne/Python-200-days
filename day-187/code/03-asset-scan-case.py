#!/usr/bin/env python3
"""
Day 187 · 03 — 实战：扫描 + 指纹 + 资产记录

把 01 的端口扫描和 02 的指纹识别串起来：
  1. 只扫描指定端口范围
  2. 对 open 端口做一次指纹探测
  3. 输出结构化资产记录（JSON），可选写入 SQLite

为什么要串起来：
  单独一份"open 端口列表"价值有限。运维想知道的是
  "10.0.0.5:8000 是 Python http.server，title 是 Directory listing"，
  这样才判断得出该不该暴露在公网。

安全边界：
  默认只扫 127.0.0.1。要扫别的地址必须显式 --host，
  并且在真实项目里加"授权清单"校验，拒绝未授权目标。

用法：
  python3 03-asset-scan-case.py --host 127.0.0.1 --ports 8000-8010
  python3 03-asset-scan-case.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# 同目录脚本名带连字符，不能直接 import，用 importlib 按路径加载
import importlib.util

HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


scanner = _load("port_scan", "01-port-scan-basic.py")
fingerprinter = _load("banner_fp", "02-banner-fingerprint.py")

SCHEMA = """
CREATE TABLE IF NOT EXISTS service_assets (
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    product TEXT NOT NULL,
    confidence TEXT NOT NULL,
    server_header TEXT,
    title TEXT,
    scanned_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (host, port)
);
"""


def build_assets(host: str, scan_results: list[dict], timeout: float = 1.5) -> list[dict]:
    assets = []
    for item in scan_results:
        if item["state"] != "open":
            continue
        # 显式发 GET：既能拿 Server 头，也能读到 <title>（HEAD 没有 body）
        request = f"GET / HTTP/1.0\r\nHost: {host}\r\n\r\n".encode()
        info = fingerprinter.grab_banner(host, item["port"], timeout, send=request)
        fp = fingerprinter.fingerprint(info)
        assets.append({
            "host": host,
            "port": item["port"],
            "state": item["state"],
            "latency_ms": item["latency_ms"],
            "product": fp["product"],
            "confidence": fp["confidence"],
            "server_header": fp["server_header"],
            "title": fp["title"],
            "error": info["error"],
        })
    return assets


def save_sqlite(db_path: str, assets: list[dict]) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        with conn:
            conn.executemany(
                """INSERT INTO service_assets(host, port, product, confidence, server_header, title)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(host, port) DO UPDATE SET
                     product=excluded.product,
                     confidence=excluded.confidence,
                     server_header=excluded.server_header,
                     title=excluded.title,
                     scanned_at=datetime('now')""",
                [(a["host"], a["port"], a["product"], a["confidence"],
                  a["server_header"], a["title"]) for a in assets],
            )
    finally:
        conn.close()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"<html><title>Inventory Target</title><body>hello</body></html>"
        self.send_response(200)
        self.send_header("Server", "Apache/2.4.58 (Ubuntu)")
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def self_test() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    probe = __import__("socket").socket()
    probe.bind(("127.0.0.1", 0))
    closed_port = probe.getsockname()[1]
    probe.close()

    try:
        results = scanner.scan_host("127.0.0.1", [port, closed_port], workers=2, timeout=0.5)
        assets = build_assets("127.0.0.1", results)
        assert len(assets) == 1, assets
        assert assets[0]["port"] == port, assets
        assert assets[0]["product"] == "Apache httpd", assets
        assert assets[0]["title"] == "Inventory Target", assets
        assert assets[0]["confidence"] == "high", assets

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "assets.db")
            save_sqlite(db, assets)
            conn = sqlite3.connect(db)
            row = conn.execute("SELECT host, port, product, title FROM service_assets").fetchone()
            conn.close()
            assert row == ("127.0.0.1", port, "Apache httpd", "Inventory Target"), row

        print("✅ self-test passed: 扫描 → 指纹 → JSON 结构 → SQLite 落库 全链路正确")
        print("   资产:", assets[0])
        return 0
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描 + 指纹 + 资产记录")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--ports", default="8000-8010")
    parser.add_argument("--workers", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=0.5)
    parser.add_argument("--json", help="资产写入 JSON 文件")
    parser.add_argument("--db", help="资产写入 SQLite")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    ports = scanner.parse_ports(args.ports)
    print(f"[*] 目标 {args.host}，{len(ports)} 个端口")
    results = scanner.scan_host(args.host, ports, args.workers, args.timeout)
    assets = build_assets(args.host, results, timeout=max(args.timeout, 1.0))

    if not assets:
        print("[*] 没有发现 open 端口")
    for a in assets:
        print(f"  [+] {a['host']}:{a['port']}  {a['product']} ({a['confidence']})"
              f"  Server={a['server_header'] or '—'}  Title={a['title'] or '—'}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"host": args.host, "assets": assets}, fh,
                      ensure_ascii=False, indent=2)
        print(f"[*] JSON 已写入 {args.json}")
    if args.db:
        save_sqlite(args.db, assets)
        print(f"[*] SQLite 已写入 {args.db}（表 service_assets）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

