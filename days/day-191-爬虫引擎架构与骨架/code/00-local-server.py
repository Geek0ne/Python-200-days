#!/usr/bin/env python3
"""Day 191 实验靶站：一个可复现的本地爬虫演练场。

为什么需要它：讲“限速 / 去重 / 重试”如果不给一个会慢、会 500、会 302、
有 robots.txt 的真实服务端，所有结论都只能靠想象。这个文件用标准库
起一个多线程 HTTP 服务，覆盖四种真实站点行为：

  /page/N        200，正常页面（带链接，可爬深）
  /slow/N        200，但服务端 sleep 50ms（模拟慢站点）
  /flaky/N       第一次 503 + Retry-After，第二次 200（模拟抖动）
  /private/N     200，但被 robots.txt 禁止（模拟不该爬的路径）
  /redirect/N    302 → /page/N（模拟跳转）
  /status        JSON 统计：各路径被请求了多少次

用法：
  python3 00-local-server.py --port 8099          # 前台起服务
  python3 00-local-server.py --self-test          # 离线自检（自动选端口）
  curl -s localhost:8099/status | python3 -m json.tool

清理：Ctrl-C 即可，服务不落任何文件。
"""
from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGES = 500
SLOW_MS = 50

_lock = threading.Lock()
_hits: dict[str, int] = {}
_flaky_attempt: dict[str, int] = {}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # 静音，避免污染实验结果
        pass

    # ---------- 工具 ----------
    def _bump(self, key: str) -> int:
        with _lock:
            _hits[key] = _hits.get(key, 0) + 1
            return _hits[key]

    def _send(self, code: int, body: str, ctype: str = "text/html; charset=utf-8",
              extra: dict[str, str] | None = None) -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 (http.server 约定)
        path = self.path.split("?", 1)[0]
        key = path.rsplit("/", 1)[0] if path.startswith(("/page/", "/slow/", "/private/", "/redirect/")) else path
        n_hit = self._bump(key)

        if path == "/robots.txt":
            self._send(200, "User-agent: *\nDisallow: /private\nAllow: /\n", "text/plain")
            return

        if path == "/status":
            with _lock:
                payload = json.dumps({"pages": PAGES, "hits": dict(_hits)}, ensure_ascii=False)
            self._send(200, payload, "application/json")
            return

        if path.startswith("/page/"):
            n = self._num(path)
            if n is None or not (1 <= n <= PAGES):
                self._send(404, "no such page")
                return
            links = "".join(
                f'<a href="/page/{m}">page {m}</a>' for m in (n + 1, n + 2) if m <= PAGES
            )
            # 故意挂一个禁区链接：真实站点也常把后台/草稿挂在页面上
            links += f'<a href="/private/{n}" class="hidden">draft</a>' 
            self._send(200, f"<html><head><title>page {n}</title></head><body>"
                            f"<h1>page {n}</h1>{links}</body></html>")
            return

        if path.startswith("/slow/"):
            time.sleep(SLOW_MS / 1000)
            self._send(200, f"<html><title>slow</title>slow {path}</html>")
            return

        if path.startswith("/flaky/"):
            # 同一路径第 1 次必 503，之后 200：用来验证重试真的生效
            with _lock:
                attempt = _flaky_attempt.get(path, 0) + 1
                _flaky_attempt[path] = attempt
            if attempt == 1:
                self._send(503, "try later", extra={"Retry-After": "0"})
            else:
                self._send(200, f"<html><title>flaky</title>ok after {attempt}</html>")
            return

        if path.startswith("/private/"):
            self._send(200, "<html><title>secret</title>should not be crawled</html>")
            return

        if path.startswith("/redirect/"):
            n = self._num(path)
            self._send(302, "", extra={"Location": f"/page/{n or 1}"})
            return

        if path == "/":
            self._send(200, '<html><title>index</title><a href="/page/1">start</a></html>')
            return

        self._send(404, "not found")

    @staticmethod
    def _num(path: str) -> int | None:
        try:
            return int(path.rstrip("/").rsplit("/", 1)[-1])
        except ValueError:
            return None


def serve(port: int) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def self_test() -> int:
    """离线自检：不需要用户先手动起服务，自己起自己测，跑完就关。"""
    srv = serve(0)
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    checks: list[tuple[str, bool]] = []

    def get(path: str) -> tuple[int, bytes]:
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    code, body = get("/page/7")
    checks.append(("page 200 且含标题", code == 200 and b"page 7" in body))
    code, _ = get("/flaky/1")
    checks.append(("flaky 首次 503", code == 503))
    code, _ = get("/flaky/1")
    checks.append(("flaky 二次 200", code == 200))
    code, body = get("/robots.txt")
    checks.append(("robots 禁 /private", code == 200 and b"Disallow: /private" in body))
    code, _ = get("/redirect/3")
    checks.append(("redirect 跟随到 200", code == 200))
    code, body = get("/status")
    checks.append(("status 有统计", code == 200 and b'"hits"' in body))

    srv.shutdown()
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    print(f"\nself-test: {len(checks) - len(bad)}/{len(checks)} passed")
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    srv = serve(a.port)
    print(f"lab server on http://127.0.0.1:{a.port}  (page 1..{PAGES}, Ctrl-C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nstopping...")
    finally:
        srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
