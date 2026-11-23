#!/usr/bin/env python3
"""
Day 187 · 02 — 进阶用法：banner 抓取与服务指纹

端口开着只能说明"有人监听"，不能说明"是什么服务"。
指纹识别要回答：这是 nginx 还是 Apache？是 Python http.server 还是 Flask？
是 OpenSSH 还是 Dropbear？

三条证据链（按可靠性排序）：
  1. 协议响应：HTTP 状态行 + 响应头（Server/X-Powered-By）
  2. 应用内容：HTML <title>、特定路径的固定响应
  3. 原始 banner：SSH/FTP/SMTP 建立连接后主动吐出的版本字符串

为什么要指纹：
  · 决定下一步用什么扫描器（HTTP 服务才谈 SQLi/XSS）
  · 版本信息可关联已知 CVE（但不要只信 banner，版本可伪造）
  · 资产台账需要"服务"这一层，而不只是"端口开着"

用法：
  python3 02-banner-fingerprint.py --host 127.0.0.1 --port 8000
  python3 02-banner-fingerprint.py --self-test
"""

from __future__ import annotations

import argparse
import re
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SIGNATURES = [
    ("nginx", "nginx"),
    ("apache", "Apache httpd"),
    ("microsoft-iis", "Microsoft IIS"),
    ("simplehttp", "Python http.server"),
    ("werkzeug", "Flask/Werkzeug"),
    ("gunicorn", "Gunicorn"),
    ("openssh", "OpenSSH"),
    ("dropbear", "Dropbear SSH"),
    ("proftpd", "ProFTPD"),
    ("vsftpd", "vsftpd"),
    ("postfix", "Postfix SMTP"),
    ("exim", "Exim SMTP"),
]


def read_some(sock: socket.socket, limit: int = 8192) -> bytes:
    """读到 header 结束，再按 Content-Length 把 body 读完。

    只读到 \r\n\r\n 就返回是一个真实踩过的 bug：
    HEAD 没问题，但 GET 的 <title> 在 body 里，永远拿不到。
    """
    buf = b""
    while len(buf) < limit:
        try:
            data = sock.recv(min(1024, limit - len(buf)))
        except socket.timeout:
            break
        if not data:
            break
        buf += data
        head, sep, body = buf.partition(b"\r\n\r\n")
        if not sep:
            continue
        match = re.search(rb"Content-Length:\s*(\d+)", head, re.I)
        need = int(match.group(1)) if match else 0
        if len(body) >= need:
            break
    return buf


def grab_banner(host: str, port: int, timeout: float = 1.5,
                send: bytes | None = None) -> dict:
    """连接并读取 banner；HTTP 服务用 HEAD 请求触发响应。"""
    result = {"port": port, "banner": "", "status_line": "", "headers": {}, "title": "", "error": ""}
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            if send is None:
                # 先等 300ms 看服务是否主动说话（SSH/FTP/SMTP 会）
                sock.settimeout(0.3)
                try:
                    peek = sock.recv(1024)
                except socket.timeout:
                    peek = b""
                if peek:
                    result["banner"] = peek.decode("utf-8", "replace").strip()
                    return result
                sock.settimeout(timeout)
                send = b"HEAD / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n"
            sock.sendall(send)
            raw = read_some(sock)
    except OSError as exc:
        result["error"] = str(exc)
        return result

    text = raw.decode("utf-8", "replace")
    result["banner"] = text.strip()[:300]
    lines = text.split("\r\n")
    if lines and lines[0].startswith("HTTP/"):
        result["status_line"] = lines[0]
        for line in lines[1:]:
            if not line.strip():
                break
            if ":" in line:
                key, value = line.split(":", 1)
                result["headers"][key.strip().lower()] = value.strip()
    match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if match:
        result["title"] = re.sub(r"\s+", " ", match.group(1)).strip()[:120]
    return result


def fingerprint(info: dict) -> dict:
    """把 banner/headers/title 映射成产品猜测与置信度。"""
    haystack = " ".join([
        info.get("banner", ""),
        info.get("status_line", ""),
        " ".join(f"{k}:{v}" for k, v in info.get("headers", {}).items()),
        info.get("title", ""),
    ]).lower()

    product = "unknown"
    evidence = ""
    for needle, name in SIGNATURES:
        if needle in haystack:
            product = name
            evidence = needle
            break

    confidence = "low"
    if info.get("headers", {}).get("server"):
        confidence = "high" if product != "unknown" else "medium"
    elif info.get("status_line"):
        confidence = "medium"
    elif info.get("banner"):
        confidence = "medium"

    return {
        "product": product,
        "evidence": evidence,
        "confidence": confidence,
        "server_header": info.get("headers", {}).get("server", ""),
        "title": info.get("title", ""),
    }


class _TestHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Server", "nginx/1.24.0")
        self.send_header("X-Powered-By", "PHP/8.2")
        self.end_headers()

    def do_GET(self):
        body = b"<html><head><title>Test Landing</title></head><body>ok</body></html>"
        self.send_response(200)
        self.send_header("Server", "nginx/1.24.0")
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def self_test() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TestHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        info = grab_banner("127.0.0.1", port)
        assert info["status_line"].startswith("HTTP/1.0 200"), info
        assert info["headers"].get("server") == "nginx/1.24.0", info
        fp = fingerprint(info)
        assert fp["product"] == "nginx", fp
        assert fp["confidence"] == "high", fp
        # GET 才能拿 title
        info_get = grab_banner("127.0.0.1", port, send=b"GET / HTTP/1.0\r\nHost: x\r\n\r\n")
        assert info_get["title"] == "Test Landing", info_get
        print("✅ self-test passed: 状态行 / Server 头 / title / nginx 指纹 均正确")
        print("   指纹:", fp)
        return 0
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="banner 抓取与服务指纹")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=False)
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.port:
        parser.error("需要 --port，或用 --self-test")

    info = grab_banner(args.host, args.port, args.timeout)
    if info["error"]:
        print(f"[x] 连接失败: {info['error']}")
        return 2
    fp = fingerprint(info)
    print(f"[*] {args.host}:{args.port}")
    print(f"    状态行: {info['status_line'] or '(无)'}")
    print(f"    Server: {info['headers'].get('server', '(无)')}")
    print(f"    Title : {info['title'] or '(无)'}")
    print(f"    指纹  : {fp['product']} (置信度 {fp['confidence']}, 证据 {fp['evidence'] or '—'})")
    if info["banner"]:
        print("    Banner 前 200 字符:")
        print("    " + info["banner"][:200].replace("\n", "\n    "))
    return 0


if __name__ == "__main__":
    sys.exit(main())

