#!/usr/bin/env python3
"""
00-proxy-lab.py — 代理池实验台（真实 TCP，不 mock）

本文件起三个东西：
  1. OriginServer  —— 靶站（/health /item/N /limited/N /blocked）
  2. ProxyServer   —— 真实的 HTTP 正向代理，支持绝对 URI、Proxy-Authorization、CONNECT 隧道
  3. Lab           —— 把上面两类服务器拉起来/杀掉/降速/统计的夹具

为什么不用 mock：
    代理池的坑几乎全在"网络边界"上——407、501 CONNECT、连接被拒、超时。
    把 requests.get 换成假对象，这些坑一个都复现不出来。
    所以本实验台用真 socket、真端口、真 HTTP 报文，但只跑在 127.0.0.1，离线可复现。

用法：
    python3 00-proxy-lab.py --self-test     # 离线自证：起靶站+代理，跑通 6 项断言
    python3 00-proxy-lab.py --demo          # 起一套实验环境，打印端口与统计，Ctrl-C 退出
"""

from __future__ import annotations

import argparse
import base64
import json
import select
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Optional, Tuple


# ────────────────────────────── 靶站 ──────────────────────────────

class QuietThreadingHTTPServer(ThreadingHTTPServer):
    """客户端提前断开时不要打整页 traceback（读日志时噪音太大）。"""

    daemon_threads = True

    def handle_error(self, request, client_address):
        exc = sys.exc_info()[1]
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


class OriginState:
    """靶站共享状态：按出口统计限流窗口。"""

    def __init__(self, ban_limit: int = 4, ban_window: float = 3.0):
        self.ban_limit = ban_limit
        self.ban_window = ban_window
        self.lock = threading.Lock()
        self.hits: Dict[str, List[float]] = {}      # exit_id -> [ts, ...]
        self.total = 0
        self.banned_429 = 0

    def count_request(self):
        """靶站收到的每一个请求都计数（不管路径）。"""
        with self.lock:
            self.total += 1

    def hit(self, exit_id: str) -> bool:
        """记一次限流窗口；返回 True 表示应该 429。"""
        now = time.monotonic()
        with self.lock:
            window = [t for t in self.hits.get(exit_id, []) if now - t < self.ban_window]
            window.append(now)
            self.hits[exit_id] = window
            if len(window) > self.ban_limit:
                self.banned_429 += 1
                return True
        return False


def make_origin_handler(state: OriginState):
    class OriginHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "LabOrigin/1.0"

        def log_message(self, fmt, *args):      # 静音，避免污染实验输出
            pass

        def _send(self, code: int, payload: dict, extra: Optional[dict] = None):
            body = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def do_GET(self):
            exit_id = self.headers.get("X-Exit-Id", "direct")
            state.count_request()
            path = self.path
            if path == "/health":
                self._send(200, {"ok": True, "exit": exit_id, "origin": "lab"})
                return
            if path == "/blocked":
                # 模拟"这个 IP 已被目标站拉黑"
                self._send(403, {"error": "forbidden", "exit": exit_id})
                return
            if path.startswith("/limited/"):
                if state.hit(exit_id):
                    self._send(429, {"error": "too_many_requests", "exit": exit_id},
                               {"Retry-After": "1"})
                else:
                    self._send(200, {"id": path.rsplit("/", 1)[-1], "exit": exit_id})
                return
            if path.startswith("/item/"):
                self._send(200, {"id": path.rsplit("/", 1)[-1], "exit": exit_id})
                return
            self._send(200, {"path": path, "exit": exit_id})

        def do_POST(self):
            state.count_request()
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)
            self._send(200, {"posted": True, "exit": self.headers.get("X-Exit-Id", "direct")})

    return OriginHandler


class OriginServer:
    def __init__(self, state: OriginState):
        self.state = state
        self.httpd = QuietThreadingHTTPServer(("127.0.0.1", 0), make_origin_handler(state))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


# ────────────────────────────── 代理 ──────────────────────────────

@dataclass
class ProxyConfig:
    name: str
    username: Optional[str] = None
    password: Optional[str] = None
    delay: float = 0.0             # 模拟慢代理
    fail: bool = False             # 模拟坏代理：一律 502
    support_connect: bool = True   # 是否实现 CONNECT 隧道


class ProxyStats:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests = 0
        self.bytes_out = 0
        self.rejected_407 = 0
        self.errors_502 = 0

    def bump(self, requests=0, bytes_out=0, rejected_407=0, errors_502=0):
        with self.lock:
            self.requests += requests
            self.bytes_out += bytes_out
            self.rejected_407 += rejected_407
            self.errors_502 += errors_502

    def snapshot(self) -> dict:
        with self.lock:
            return {"requests": self.requests, "bytes_out": self.bytes_out,
                    "407": self.rejected_407, "502": self.errors_502}


def make_proxy_handler(cfg: ProxyConfig, stats: ProxyStats):

    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "LabProxy/1.0"

        def log_message(self, fmt, *args):
            pass

        def _deny(self, code: int, msg: str, extra: Optional[dict] = None):
            body = msg.encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def _check_auth(self) -> bool:
            if not cfg.username:
                return True
            # 每次请求重算：凭证可以在运行期轮换（闭包只算一次会读到旧值，
            # 这个坑我在写实验台时真踩了，见 README 的翻车实验 2）
            raw = f"{cfg.username}:{cfg.password or ''}".encode()
            expected_auth = "Basic " + base64.b64encode(raw).decode()
            got = self.headers.get("Proxy-Authorization", "")
            if got != expected_auth:
                stats.bump(rejected_407=1)
                self._deny(407, "proxy auth required",
                           {"Proxy-Authenticate": 'Basic realm="lab"'})
                return False
            return True

        def do_GET(self):
            if not self._check_auth():
                return
            if cfg.fail:
                stats.bump(errors_502=1)
                self._deny(502, "bad gateway (simulated)")
                return
            if not self.path.startswith("http://"):
                # 经典错误：把普通请求当正向代理请求处理
                self._deny(400, "absolute URI required")
                return
            if cfg.delay:
                time.sleep(cfg.delay)
            try:
                body, status, headers = self._forward(self.path)
            except Exception as exc:                      # noqa: BLE001
                stats.bump(errors_502=1)
                self._deny(502, f"upstream error: {exc}")
                return
            data = body
            self.send_response(status)
            for key in ("Content-Type", "Retry-After"):
                if key in headers:
                    self.send_header(key, headers[key])
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            stats.bump(requests=1, bytes_out=len(data))
            self.close_connection = True

        def _forward(self, absolute_url: str) -> Tuple[bytes, int, dict]:
            import http.client
            from urllib.parse import urlsplit
            parts = urlsplit(absolute_url)
            conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=5)
            path = parts.path or "/"
            if parts.query:
                path += "?" + parts.query
            headers = {"Host": parts.netloc, "X-Exit-Id": cfg.name,
                       "Connection": "close"}
            # 只透传少量安全头，避免把 Proxy-Authorization 泄露给目标站
            for key in ("Accept", "User-Agent", "Accept-Encoding"):
                if self.headers.get(key):
                    headers[key] = self.headers[key]
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            body = resp.read()
            hdrs = {k: v for k, v in resp.getheaders()}
            conn.close()
            return body, resp.status, hdrs

        def do_CONNECT(self):
            if not self._check_auth():
                return
            if not cfg.support_connect:
                # 这就是翻车实验里的 501：代理能做 HTTP，不做 HTTPS 隧道
                stats.bump(errors_502=1)
                self._deny(501, "CONNECT not implemented")
                return
            if cfg.fail:
                stats.bump(errors_502=1)
                self._deny(502, "bad gateway (simulated)")
                return
            host, _, port = self.path.partition(":")
            try:
                upstream = socket.create_connection((host, int(port or 443)), timeout=5)
            except OSError as exc:
                stats.bump(errors_502=1)
                self._deny(502, f"connect failed: {exc}")
                return
            self.send_response(200, "Connection Established")
            self.end_headers()
            self.wfile.flush()
            self.connection.settimeout(None)
            peers = {self.connection: upstream, upstream: self.connection}
            try:
                while True:
                    readable, _, _ = select.select(list(peers), [], [], 10)
                    if not readable:
                        break
                    for sock in readable:
                        chunk = sock.recv(65536)
                        if not chunk:
                            return
                        peers[sock].sendall(chunk)
                        stats.bump(bytes_out=len(chunk))
            finally:
                upstream.close()

    return ProxyHandler


class ProxyRuntime:
    def __init__(self, cfg: ProxyConfig):
        self.cfg = cfg
        self.stats = ProxyStats()
        self.httpd = QuietThreadingHTTPServer(("127.0.0.1", 0),
                                              make_proxy_handler(cfg, self.stats))
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.dead = False

    def start(self):
        self.thread.start()
        return self

    def kill(self):
        """真关端口：后续连接会得到 Connection refused。"""
        if not self.dead:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.dead = True

    @property
    def url(self) -> str:
        auth = ""
        if self.cfg.username:
            auth = f"{self.cfg.username}:{self.cfg.password}@"
        return f"http://{auth}127.0.0.1:{self.port}"


# ────────────────────────────── 夹具 ──────────────────────────────

class Lab:
    """一套可复现的靶站 + 代理集群。"""

    def __init__(self, proxies: Tuple[str, ...] = ("p1", "p2", "p3"),
                 ban_limit: int = 4, ban_window: float = 3.0):
        self.state = OriginState(ban_limit=ban_limit, ban_window=ban_window)
        self.origin = OriginServer(self.state)
        self.proxies: Dict[str, ProxyRuntime] = {
            name: ProxyRuntime(ProxyConfig(name=name)) for name in proxies
        }

    def __enter__(self):
        self.origin.start()
        for p in self.proxies.values():
            p.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    def stop(self):
        for p in self.proxies.values():
            p.kill()
        try:
            self.origin.stop()
        except Exception:                                  # noqa: BLE001
            pass

    def proxy_url(self, name: str) -> str:
        return self.proxies[name].url

    def kill(self, name: str):
        self.proxies[name].kill()

    def set_config(self, name: str, **kwargs):
        cfg = self.proxies[name].cfg
        for key, value in kwargs.items():
            setattr(cfg, key, value)

    def stats(self) -> dict:
        return {name: p.stats.snapshot() for name, p in self.proxies.items()}

    def origin_total(self) -> int:
        return self.state.total


def fetch(url: str, proxy: Optional[str] = None, timeout: float = 3.0,
          headers: Optional[dict] = None) -> Tuple[int, dict, float]:
    """用 urllib 发请求，返回 (状态码, JSON, 耗时秒)。"""
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {})]
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers=headers or {})
    started = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, json.loads(body), time.monotonic() - started
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            payload = json.loads(body)
        except Exception:                                  # noqa: BLE001
            payload = {"raw": body.decode(errors="replace")}
        return exc.code, payload, time.monotonic() - started


# ────────────────────────────── 自证 ──────────────────────────────

def self_test() -> int:
    checks: List[Tuple[str, bool, str]] = []
    with Lab(ban_limit=3, ban_window=2.0) as lab:
        # 1. 直连靶站
        code, body, _ = fetch(lab.origin.url + "/health")
        checks.append(("直连靶站 200", code == 200 and body["exit"] == "direct", str(body)))

        # 2. 经代理，靶站看到代理注入的出口标识
        code, body, _ = fetch(lab.origin.url + "/health", proxy=lab.proxy_url("p1"))
        checks.append(("经 p1 出口标识正确", code == 200 and body["exit"] == "p1", str(body)))
        checks.append(("p1 确实收到 1 个请求",
                       lab.proxies["p1"].stats.snapshot()["requests"] == 1,
                       str(lab.stats()["p1"])))

        # 3. CONNECT 关闭时 HTTPS 走不通（501 语义）
        lab.set_config("p2", support_connect=False)
        try:
            fetch("https://example.com/", proxy=lab.proxy_url("p2"), timeout=3)
            ok, detail = False, "意外成功"
        except Exception as exc:                           # noqa: BLE001
            ok, detail = True, f"{type(exc).__name__}: {exc}"
        checks.append(("无 CONNECT 时代理拒绝 HTTPS", ok, detail))

        # 4. 407：不带凭证被拒；带对凭证才放行
        lab.set_config("p3", username="u", password="secret")
        naked = f"http://127.0.0.1:{lab.proxies['p3'].port}"
        code, body, _ = fetch(lab.origin.url + "/health", proxy=naked)
        checks.append(("不带凭证得到 407", code == 407, f"{code} {body}"))
        code, body, _ = fetch(lab.origin.url + "/health", proxy=lab.proxy_url("p3"))
        checks.append(("带对凭证得到 200", code == 200 and body["exit"] == "p3", f"{code} {body}"))

        # 5. 限流：同一出口连打触发 429
        codes = []
        for i in range(5):
            code, _, _ = fetch(lab.origin.url + f"/limited/{i}",
                               proxy=lab.proxy_url("p1"))
            codes.append(code)
        checks.append(("同一出口超过窗口得到 429", 429 in codes, str(codes)))

        # 6. kill 后连接被拒（不是超时）
        lab.kill("p2")
        try:
            fetch(lab.origin.url + "/health", proxy=lab.proxy_url("p2"), timeout=1)
            ok, detail = False, "意外成功"
        except Exception as exc:                           # noqa: BLE001
            ok = "refused" in str(exc).lower() or "Connection" in str(exc)
            detail = f"{type(exc).__name__}: {exc}"
        checks.append(("kill 后连接被拒", ok, detail))

    failed = 0
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}  ->  {detail}")
        failed += 0 if ok else 1
    print(f"\n{len(checks) - failed}/{len(checks)} 项通过")
    return 1 if failed else 0


def demo():
    with Lab(ban_limit=4, ban_window=3.0) as lab:
        print(f"靶站: {lab.origin.url}")
        for name in lab.proxies:
            print(f"代理 {name}: {lab.proxy_url(name)}")
        print("Ctrl-C 退出（所有端口会自动关闭）")
        try:
            for i in range(3):
                for name in lab.proxies:
                    code, body, dt = fetch(lab.origin.url + f"/item/{i}",
                                            proxy=lab.proxy_url(name))
                    print(f"  #{i} via {name}: {code} exit={body.get('exit')} {dt*1000:.0f}ms")
        except KeyboardInterrupt:
            pass
        finally:
            print("统计:", json.dumps(lab.stats(), ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true", help="离线自证")
    parser.add_argument("--demo", action="store_true", help="起一套实验环境")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.demo:
        demo()
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
