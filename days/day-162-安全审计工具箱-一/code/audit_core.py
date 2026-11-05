"""安全审计工具箱 — 共享核心（Day 162）。

本模块提供三个模块（端口扫描 / 目录爆破 / 指纹识别）公用的地基：

1. **Scope**：授权范围（主机 + 端口 + 允许的 HTTP 基址）。
   `check_url()` 是本课在 HTTP 层的门禁——`urljoin` 可以产出**绝对 URL**，
   拼接后必须重新校验，否则会跳出授权范围。
2. **LabHTTP**：本机实验服务器（只绑定 127.0.0.1），提供可复现的审计靶标：
   403 管理入口、301 重定向、`/legacy/*` 软 404、429 限速、
   可下载的假备份文件、多种指纹信号。
3. **只读 HTTP 客户端 `fetch()`**：只发 `GET`，**不自动跟随重定向**，
   **不发送任何凭据**，响应体只取前 N 字节用于指纹/长度判定。
4. **目录爆破 `dir_brute()`**：软 404 基线 + 状态码分类 + 限速 + 429 指数退避。

安全边界（刻意为之）：
  * 只做匿名视角审计，**不登录、不带 Cookie、不爆破凭据**；
  * 只发 GET，**不 POST/上传/修改任何数据**；
  * 词表内置且很短（30 条公开文档化路径），默认 5 请求/秒；
  * 全部实验只在 127.0.0.1 的回环实验服务上完成。

自检：
    python3 audit_core.py --self-test     # 输出 SELF-TEST OK
"""

from __future__ import annotations

import errno
import http.server
import ipaddress
import json
import random
import re
import secrets
import socket
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

CST = timezone(timedelta(hours=8))
DEFAULT_TIMEOUT = 2.0
DEFAULT_RATE = 5.0            # 目录爆破默认 5 请求/秒（约等于人工浏览速度）
DEFAULT_WORKERS = 8
READ_LIMIT = 4096             # 响应体最多读这么多字节

SERVICE_MAP = {
    22: "ssh", 25: "smtp", 53: "domain", 80: "http", 110: "pop3",
    143: "imap", 443: "https", 3306: "mysql", 3389: "rdp", 5432: "postgresql",
    6379: "redis", 8000: "http-alt", 8080: "http-proxy", 8443: "https-alt",
}

# 内置词表：全部是公开文档化的常见路径，不含任何"绕过/猜解"类词条
DEFAULT_WORDS = [
    "robots.txt", "sitemap.xml", "favicon.ico", "healthz", "login",
    "admin", "admin/", "portal", "backup.zip", "api/v1/users",
    "server-status", "config.json", "index.html", "dashboard",
    "static/", "uploads/", "docs/", "logs/", "phpinfo.php", "wp-login.php",
    "legacy/app", "legacy/panel", "legacy/old", "test", "dev",
    "staging", "private/", "internal/", "metrics", "version.json",
]

BACKUP_SUFFIXES = (".zip", ".tar", ".gz", ".bak", ".sql", ".old", ".swp")

SEVERITY_LEVELS = ["info", "low", "medium", "high", "critical"]


class AuthorizationError(RuntimeError):
    """越界。策略拒绝，**不重试、不降级**。"""


class ScopeError(ValueError):
    """范围/参数不合法。"""


# ── 基础工具 ───────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sanitize(text: str, limit: int = 80) -> str:
    """响应内容一律视为**目标控制**的不可信文本：净化控制字符并截断。"""
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return (cleaned[:limit] + "…") if len(cleaned) > limit else cleaned


def parse_port_spec(spec: str) -> list[int]:
    ports: set[int] = set()
    for chunk in str(spec).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            lo, _, hi = chunk.partition("-")
            lo_i, hi_i = int(lo), int(hi)
            if lo_i > hi_i:
                raise ScopeError(f"端口区间反向: {chunk}")
            ports.update(range(lo_i, hi_i + 1))
        else:
            ports.add(int(chunk))
    for p in ports:
        if not 1 <= p <= 65535:
            raise ScopeError(f"端口超出范围: {p}")
    return sorted(ports)


def parse_host_spec(spec: str) -> list[str]:
    """只接受 IP/CIDR（拒绝域名：解析域名本身就是一次外发）。"""
    spec = str(spec).strip()
    if not spec:
        return []
    try:
        net = ipaddress.ip_network(spec, strict=False)
    except ValueError as exc:
        raise ScopeError(f"只接受 IP / CIDR: {spec!r} ({exc})") from exc
    if net.num_addresses == 1:
        return [str(net.network_address)]
    return [str(ip) for ip in net.hosts()] or [str(net.network_address)]


# ── 范围 ───────────────────────────────────────────────────────────────

@dataclass
class Scope:
    networks: list[str] = field(default_factory=list)
    ports: list[tuple[int, int]] = field(default_factory=list)
    http_bases: list[str] = field(default_factory=list)   # 允许的基址 URL
    ticket: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Scope":
        networks = list(data.get("networks", []))
        if not networks:
            raise ScopeError("networks 不能为空（没有范围的授权等于没有授权）")
        ports: list[tuple[int, int]] = []
        for item in data.get("ports", []):
            if isinstance(item, str):
                ports += [(p, p) for p in parse_port_spec(item)]
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                ports.append((int(item[0]), int(item[1])))
            else:
                raise ScopeError(f"无法解析端口条目: {item!r}")
        if not ports:
            raise ScopeError("ports 不能为空")
        return cls(networks=networks, ports=ports,
                   http_bases=list(data.get("http_bases", [])),
                   ticket=str(data.get("ticket", "")), note=str(data.get("note", "")))

    @classmethod
    def load(cls, path: str | Path) -> "Scope":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ports"] = [[lo, hi] for lo, hi in self.ports]
        return d

    def allows_host(self, host: str) -> bool:
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return False      # 域名一律不在范围内（只授权 IP，避免 DNS 外发）
        return any(ip in ipaddress.ip_network(n, strict=False) for n in self.networks)

    def allows_port(self, port: int) -> bool:
        return any(lo <= port <= hi for lo, hi in self.ports)

    def check_host_port(self, host: str, port: int) -> None:
        if not self.allows_host(host):
            raise AuthorizationError(f"主机不在授权网段内: {host}")
        if not self.allows_port(port):
            raise AuthorizationError(f"端口不在授权区间内: {port}")

    def check_url(self, url: str) -> str:
        """HTTP 层门禁：只允许**授权基址的子路径**，且协议/主机/端口都要对得上。"""
        target = urllib.parse.urlsplit(url)
        if target.scheme not in ("http", "https"):
            raise AuthorizationError(f"只允许 http/https: {url}")
        host = target.hostname or ""
        port = target.port or (443 if target.scheme == "https" else 80)
        try:
            self.check_host_port(host, port)
        except AuthorizationError as exc:
            raise AuthorizationError(f"{exc}（URL: {url}）") from exc
        if not self.http_bases:
            return url
        if not any(url == base or url.startswith(base.rstrip("/") + "/")
                   or url.startswith(base.rstrip("/") + "?")
                   for base in self.http_bases):
            raise AuthorizationError(f"URL 不在授权基址之下: {url}")
        return url


def default_lab_scope() -> Scope:
    """默认实验范围：回环 + 8000-8099 + 实验基址。"""
    return Scope(networks=["127.0.0.1/32"], ports=[(8000, 8099)],
                 http_bases=["http://127.0.0.1:8080", "http://127.0.0.1:8000"],
                 ticket="LAB-SELF-002", note="self-owned loopback lab only")


# ── 实验 HTTP 服务 ─────────────────────────────────────────────────────

LAB_INDEX_HTML = (
    "<!DOCTYPE html><html><head><title>Lab Portal</title>"
    '<meta name="generator" content="lab-cms 0.9">'
    "</head><body><h1>Lab Portal</h1></body></html>"
)
LAB_LOGIN_HTML = (
    "<!DOCTYPE html><html><head><title>Sign in</title></head>"
    '<body><form method="post" action="/login">'
    '<input name="user"><input name="pass" type="password"></form></body></html>'
)
SOFT_404_BODY = "<html><head><title>Not Found</title></head><body>Page Not Found</body></html>"
NOT_FOUND_BODY = "<html><head><title>Not Found</title></head><body>Hard 404</body></html>"
SERVER_STATUS = "Apache Server Status for 127.0.0.1\nServer Version: Apache/2.4.52\n"

LAB_ROUTES: dict[str, tuple[int, str, str, dict]] = {
    "/": (200, "text/html", LAB_INDEX_HTML, {}),
    "/index.html": (200, "text/html", LAB_INDEX_HTML, {}),
    "/login": (200, "text/html", LAB_LOGIN_HTML, {}),
    "/admin/": (403, "text/html", "<h1>403 Forbidden</h1>", {}),
    "/admin": (301, "text/html", "", {"Location": "/admin/"}),
    "/portal": (302, "text/html", "", {"Location": "/login"}),
    "/server-status": (200, "text/plain", SERVER_STATUS, {}),
    "/robots.txt": (200, "text/plain",
                    "User-agent: *\nDisallow: /admin/\nDisallow: /backup.zip\n", {}),
    "/backup.zip": (200, "application/zip", "PK\x03\x04lab-fake-archive", {}),
    "/api/v1/users": (200, "application/json", '{"users": ["ops", "deploy"]}', {}),
    "/healthz": (200, "text/plain", "ok", {}),
    "/config.json": (403, "application/json", '{"error": "forbidden"}', {}),
    "/logs/": (401, "text/html", "<h1>401 Unauthorized</h1>", {}),
    "/phpinfo.php": (404, "text/html", NOT_FOUND_BODY, {}),
}


class _LabHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _LabHandler(http.server.BaseHTTPRequestHandler):
    server_version = "lab-nginx/1.18.0"     # 刻意"伪装"成 nginx：指纹可被伪造
    sys_version = ""

    def log_message(self, *args) -> None:    # 静音，避免污染演示输出
        pass

    def _send(self, code: int, ctype: str, body: str, extra: dict | None = None) -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Powered-By", "PHP/7.4.33")
        self.send_header("Set-Cookie", "LABSESSID=0123456789abcdef; Path=/")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def do_GET(self) -> None:                # noqa: N802 - BaseHTTPRequestHandler 约定
        srv: _LabHTTPServer = self.server      # type: ignore[assignment]
        with srv.counter_lock:
            srv.request_count += 1
            count = srv.request_count
        if srv.throttle_after and count > srv.throttle_after:
            self._send(429, "text/plain", "Too Many Requests", {"Retry-After": "1"})
            return
        path = urllib.parse.urlsplit(self.path).path
        route = LAB_ROUTES.get(path)
        if route is not None:
            code, ctype, body, extra = route
            self._send(code, ctype, body, extra)
            return
        if path.startswith("/legacy/"):
            # 软 404：**不存在**的路径却返回 200 + "Page Not Found"
            self._send(200, "text/html", SOFT_404_BODY)
            return
        # 这里模拟一个非常常见的错误配置：重写规则（SPA / 伪静态）把
        # **所有未匹配的路径**都交给同一个页面处理，于是统统返回 200。
        # 目录爆破如果"只认 200"，在这里会产出满屏假发现。
        self._send(200, "text/html", SOFT_404_BODY)

    def do_HEAD(self) -> None:                # noqa: N802
        self.do_GET()


class LabHTTP:
    """本机实验 HTTP 服务（仅回环）。`throttle_after` 用于演示 429 退避。"""

    def __init__(self, port: int = 8080, host: str = "127.0.0.1",
                 throttle_after: int | None = None):
        self.host, self.port = host, port
        self.throttle_after = throttle_after
        self.httpd: _LabHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> int:
        self.httpd = _LabHTTPServer((self.host, self.port), _LabHandler)
        self.httpd.throttle_after = self.throttle_after     # type: ignore[attr-defined]
        self.httpd.request_count = 0                        # type: ignore[attr-defined]
        self.httpd.counter_lock = threading.Lock()           # type: ignore[attr-defined]
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.port

    def stop(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    def __enter__(self) -> "LabHTTP":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


# ── 只读 HTTP 客户端 ───────────────────────────────────────────────────

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """捕获重定向而**不自动跟随**（可能被引到范围外，且会掩盖真实状态码）。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


@dataclass
class HttpResult:
    url: str
    status: int = 0
    length: int = 0
    body: str = ""
    headers: dict = field(default_factory=dict)
    redirect_to: str = ""
    elapsed_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["body"] = sanitize(self.body, 200)
        return d


def fetch(url: str, timeout: float = DEFAULT_TIMEOUT) -> HttpResult:
    """只读 GET。不跟随重定向、不发送凭据、响应体只读前 READ_LIMIT 字节。"""
    started = time.perf_counter()
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "audit-lab/1.0 (authorized)"})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read(READ_LIMIT)
            return HttpResult(
                url=url, status=resp.status, length=len(raw),
                body=raw.decode("utf-8", "replace"),
                headers={k: v for k, v in resp.headers.items()},
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )
    except urllib.error.HTTPError as exc:      # 4xx/5xx 走这里（含 3xx 未跟随）
        raw = exc.read(READ_LIMIT) if hasattr(exc, "read") else b""
        return HttpResult(
            url=url, status=exc.code, length=len(raw),
            body=raw.decode("utf-8", "replace"),
            headers={k: v for k, v in (exc.headers or {}).items()},
            redirect_to=(exc.headers or {}).get("Location", "") if exc.code in (301, 302, 303, 307, 308) else "",
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:                    # noqa: BLE001 - 网络类异常统一记录
        return HttpResult(url=url, error=f"{type(exc).__name__}: {exc}",
                          elapsed_ms=round((time.perf_counter() - started) * 1000, 2))


# ── 令牌桶 ─────────────────────────────────────────────────────────────

class TokenBucket:
    """限速：默认 5 请求/秒。这是**授权边界的技术表达**，不是性能取舍。"""

    def __init__(self, rate: float = DEFAULT_RATE, capacity: float = 1.0):
        if rate <= 0:
            raise ValueError("rate 必须 > 0")
        self.rate, self.capacity = float(rate), float(max(1.0, capacity))
        self._tokens, self._updated = self.capacity, time.monotonic()
        self._lock = threading.Lock()
        self.waited_s = 0.0

    def acquire(self) -> float:
        waited = 0.0
        while True:
            with self._lock:
                now = time.monotonic()
                self._tokens = min(self.capacity, self._tokens + (now - self._updated) * self.rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    self.waited_s += waited
                    return waited
                need = (1.0 - self._tokens) / self.rate
            time.sleep(min(need, 0.05))
            waited += min(need, 0.05)


# ── 端口扫描 ───────────────────────────────────────────────────────────

@dataclass
class PortResult:
    host: str
    port: int
    state: str                  # open / closed / filtered / error
    service: str = ""
    service_source: str = ""    # banner / port_map
    banner: str = ""
    elapsed_ms: float = 0.0
    error: str = ""

    @property
    def key(self) -> str:
        return f"{self.host}:{self.port}"

    def to_dict(self) -> dict:
        return asdict(self)


def scan_port(host: str, port: int, timeout: float = 0.5, retries: int = 1) -> PortResult:
    """TCP connect 只读探测（三态语义见 README 4.1）。"""
    started, attempt, last_err = time.perf_counter(), 0, ""
    while attempt <= retries:
        attempt += 1
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)          # ★ 必须显式设置，否则走 OS 默认超时
            code = sock.connect_ex((host, port))
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            if code == 0:
                banner = ""
                try:
                    sock.settimeout(min(timeout, 0.3))
                    banner = sock.recv(256).decode("utf-8", "replace").strip()
                except (socket.timeout, OSError):
                    pass
                return PortResult(host, port, "open",
                                  service=guess_service(port, banner),
                                  service_source="banner" if banner else "port_map",
                                  banner=sanitize(banner), elapsed_ms=elapsed)
            if code == errno.ECONNREFUSED:
                return PortResult(host, port, "closed", elapsed_ms=elapsed)
            last_err = f"errno={code}"
        except OSError as exc:
            last_err = f"{type(exc).__name__}: {exc}"
        finally:
            sock.close()
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    state = "filtered" if ("timed out" in last_err.lower() or "errno=11" in last_err) else "error"
    return PortResult(host, port, state, elapsed_ms=elapsed, error=last_err)


def guess_service(port: int, banner: str = "") -> str:
    low = banner.lower()
    if "ssh-" in low:
        return "ssh"
    if low.startswith("http/") or "server:" in low:
        return "http"
    if "smtp" in low:
        return "smtp"
    if "mysql" in low:
        return "mysql"
    return SERVICE_MAP.get(port, "unknown")


def scan_ports(hosts: Sequence[str], ports: Sequence[int], scope: Scope,
               timeout: float = 0.5, rate: float = 50.0) -> list[PortResult]:
    bucket = TokenBucket(rate=rate, capacity=8)
    results: list[PortResult] = []
    for host in hosts:
        for port in ports:
            scope.check_host_port(host, port)     # ★ 门禁：越界即中止
            bucket.acquire()
            results.append(scan_port(host, port, timeout=timeout))
    return results


# ── 目录爆破 ───────────────────────────────────────────────────────────

@dataclass
class DirEntry:
    word: str
    url: str
    status: int = 0
    length: int = 0
    category: str = ""          # accessible/soft_404/protected/redirect/missing/throttled/server_error/error
    soft_404_suspect: bool = False
    redirect_to: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Baseline:
    status: int = 0
    length: int = 0
    samples: list = field(default_factory=list)

    def matches(self, status: int, length: int, abs_tol: int = 32, rel_tol: float = 0.05) -> bool:
        """与基线"一致"的判定：状态码相同 + 长度在容差内。"""
        if status != self.status:
            return False
        tol = max(abs_tol, int(rel_tol * max(1, self.length)))
        return abs(length - self.length) <= tol


def build_baseline(base_url: str, scope: Scope, samples: int = 3) -> Baseline:
    """用**随机路径**取得"不存在"时的 (状态码, 长度) 基线。

    这是目录爆破最关键的一步：没有基线，`200` 就毫无意义。
    """
    scope.check_url(base_url)
    baseline = Baseline()
    for _ in range(max(1, samples)):
        token = secrets.token_hex(6)
        url = urllib.parse.urljoin(base_url.rstrip("/") + "/", f"{token}")
        scope.check_url(url)
        res = fetch(url)
        baseline.samples.append({"url": url, "status": res.status, "length": res.length})
        if baseline.status == 0:
            baseline.status, baseline.length = res.status, res.length
    return baseline


def classify(status: int, length: int, baseline: Baseline, soft_suspect: bool) -> str:
    if status == 0:
        return "error"
    if status == 429:
        return "throttled"
    if status in (401, 403):
        return "protected"
    if status in (301, 302, 303, 307, 308):
        return "redirect"
    if status >= 500:
        return "server_error"
    if status == 200:
        return "soft_404" if soft_suspect else "accessible"
    if status == 404:
        return "missing"
    return "other"


def dir_brute(base_url: str, words: Sequence[str], scope: Scope,
              rate: float = DEFAULT_RATE, max_backoff: float = 4.0,
              throttle_demo: bool = False) -> tuple[list[DirEntry], Baseline, dict]:
    """目录爆破：软 404 基线 + 分类 + 限速 + 429 指数退避。

    返回 (条目列表, 基线, 覆盖统计)。**所有请求都是只读 GET。**
    """
    scope.check_url(base_url)
    baseline = build_baseline(base_url, scope)
    bucket = TokenBucket(rate=rate, capacity=1)
    entries: list[DirEntry] = []
    coverage = {"total": len(words), "completed": 0, "throttled": 0,
                "errors": 0, "backoff_events": 0, "max_backoff_s": 0.0}
    backoff = 0.5
    for word in words:
        url = urllib.parse.urljoin(base_url.rstrip("/") + "/", word)
        try:
            scope.check_url(url)               # ★ urljoin 可能产出绝对 URL，必须复检
        except AuthorizationError as exc:
            raise AuthorizationError(f"词条导致越界，整轮终止: {word} → {exc}") from exc
        bucket.acquire()
        res = fetch(url)
        soft = baseline.matches(res.status, res.length)
        category = classify(res.status, res.length, baseline, soft)
        entry = DirEntry(word=word, url=url, status=res.status, length=res.length,
                         category=category, soft_404_suspect=soft,
                         redirect_to=res.redirect_to, error=res.error)
        entries.append(entry)
        if category == "throttled":
            coverage["throttled"] += 1
            coverage["backoff_events"] += 1
            sleep_for = min(backoff, max_backoff)
            coverage["max_backoff_s"] = max(coverage["max_backoff_s"], sleep_for)
            time.sleep(sleep_for)              # 指数退避：0.5 → 1 → 2 → 4（上限）
            backoff = min(backoff * 2, max_backoff)
        elif category == "error":
            coverage["errors"] += 1
        else:
            coverage["completed"] += 1
    coverage["incomplete"] = coverage["throttled"] > 0 or coverage["errors"] > 0
    return entries, baseline, coverage


# ── 指纹识别 ───────────────────────────────────────────────────────────

@dataclass
class Signal:
    tech: str
    source: str          # header:Server / cookie / html:meta / path:/server-status ...
    value: str
    weight: float


@dataclass
class TechGuess:
    tech: str
    score: float
    confidence: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


META_RE = re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
VERSION_RE = re.compile(r"([A-Za-z][A-Za-z0-9\-_]*)[/ ](\d+(?:\.\d+)+)")


def collect_signals(main: HttpResult, probes: dict[str, HttpResult]) -> list[Signal]:
    """采集指纹信号。**所有信号都来自目标，因此都可被伪造。**"""
    signals: list[Signal] = []
    server = main.headers.get("Server", "")
    if server:
        tech = server.split("/")[0].strip().lower() or "unknown"
        signals.append(Signal(tech, "header:Server", server, 0.40))
    xpb = main.headers.get("X-Powered-By", "")
    if xpb:
        signals.append(Signal(xpb.split("/")[0].strip().lower(), "header:X-Powered-By", xpb, 0.25))
    cookie = main.headers.get("Set-Cookie", "")
    if cookie:
        name = cookie.split("=")[0].strip()
        tech = {"PHPSESSID": "php", "JSESSIONID": "java", "ASP.NET_SessionId": "aspnet",
                "LABSESSID": "lab-cms"}.get(name, name.lower())
        signals.append(Signal(tech, "cookie", name, 0.20))
    meta = META_RE.search(main.body)
    if meta:
        signals.append(Signal(meta.group(1).split()[0].lower(), "html:meta", meta.group(1), 0.30))
    title = TITLE_RE.search(main.body)
    if title:
        signals.append(Signal(title.group(1).strip().lower(), "html:title", title.group(1).strip(), 0.10))
    for path, res in probes.items():
        if res.status == 200 and "Server Version" in res.body:
            signals.append(Signal("apache", f"path:{path}", sanitize(res.body, 40), 0.60))
        if res.status == 200 and sanitize(res.body).startswith("PK"):
            signals.append(Signal("zip-artifact", f"path:{path}", "PK zip magic", 0.50))
    return signals


def score_signals(signals: Iterable[Signal], cap: float = 0.95) -> list[TechGuess]:
    """按 tech 聚合权重并分档。上限 0.95：**永不给出"确定"的断言**。"""
    agg: dict[str, list[Signal]] = {}
    for s in signals:
        agg.setdefault(s.tech, []).append(s)
    guesses: list[TechGuess] = []
    for tech, items in agg.items():
        score = min(cap, sum(i.weight for i in items))
        confidence = ("high" if score >= 0.8 else "medium" if score >= 0.5
                      else "low" if score >= 0.2 else "info")
        guesses.append(TechGuess(
            tech=tech, score=round(score, 2), confidence=confidence,
            evidence=[f"{i.source}={sanitize(i.value, 40)} (+{i.weight})" for i in items],
        ))
    return sorted(guesses, key=lambda g: -g.score)


# ── Finding 与报告 ─────────────────────────────────────────────────────

@dataclass
class Finding:
    key: str
    title: str
    severity: str
    confidence: str
    target: str = ""
    evidence: str = ""
    detail: dict = field(default_factory=dict)

    @property
    def priority(self) -> str:
        s = SEVERITY_LEVELS.index(self.severity) if self.severity in SEVERITY_LEVELS else 0
        c = SEVERITY_LEVELS.index(self.confidence) if self.confidence in SEVERITY_LEVELS else 0
        score = (s + 1) * (c + 1)
        return "P0" if score >= 20 else "P1" if score >= 12 else "P2" if score >= 6 else "P3"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["priority"] = self.priority
        return d


def findings_from_ports(results: Sequence[PortResult]) -> list[Finding]:
    out: list[Finding] = []
    for r in results:
        if r.state != "open":
            continue
        if r.service in {"http", "ftp", "telnet", "pop3", "imap", "smtp"}:
            out.append(Finding("cleartext_service", f"明文协议服务: {r.service}",
                               "high", "medium", r.key,
                               f"service_source={r.service_source} banner={r.banner!r}"))
        if r.port > 1024:
            out.append(Finding("high_port_service", f"高位端口服务: {r.port}",
                               "info", "medium", r.key, f"service={r.service}"))
    return out


def findings_from_dirs(entries: Sequence[DirEntry], coverage: dict) -> list[Finding]:
    out: list[Finding] = []
    for e in entries:
        if e.category == "protected":
            out.append(Finding("protected_path", f"受保护路径（{e.status}）: /{e.word}",
                               "medium", "high", e.url,
                               f"status={e.status} len={e.length}（存在但当前身份无权限）"))
        elif e.category == "accessible" and e.word.endswith(BACKUP_SUFFIXES):
            out.append(Finding("backup_artifact", f"可下载的备份/归档文件: /{e.word}",
                               "high", "medium", e.url,
                               f"status={e.status} len={e.length}（仅记录『可下载』这一事实）"))
        elif e.category == "redirect":
            out.append(Finding("redirect_path", f"重定向路径: /{e.word}",
                               "info", "high", e.url,
                               f"status={e.status} → {e.redirect_to or '?'}（未跟随）"))
        elif e.soft_404_suspect:
            out.append(Finding("soft_404_noise", f"软 404（与基线一致）: /{e.word}",
                               "info", "high", e.url,
                               f"status={e.status} len={e.length}（疑似不存在）"))
    if coverage.get("throttled"):
        out.append(Finding("coverage_gap", "目录爆破未完成：目标限速",
                           "medium", "high", "-",
                           f"429 次数={coverage['throttled']}，最大退避={coverage['max_backoff_s']}s"))
    return out


def findings_from_tech(guesses: Sequence[TechGuess], main: HttpResult) -> list[Finding]:
    out: list[Finding] = []
    for g in guesses:
        if g.tech in {"zip-artifact"}:
            continue
        out.append(Finding("tech_fingerprint", f"技术栈推断: {g.tech}（{g.confidence}）",
                           "info", g.confidence, main.url,
                           "; ".join(g.evidence[:3]), detail={"score": g.score}))
    for header_name in ("Server", "X-Powered-By"):
        value = main.headers.get(header_name, "")
        if VERSION_RE.search(value):
            out.append(Finding("version_disclosure", f"{header_name} 暴露版本: {value}",
                               "low", "medium", main.url, f"{header_name}: {value}"))
    return out


def exit_code(findings: Sequence[Finding], ports: Sequence[PortResult],
              coverage: dict | None = None) -> int:
    """2 > 4 > 3 > 0。"""
    if coverage and coverage.get("incomplete"):
        return 4
    if any(p.state in ("filtered", "error") for p in ports):
        return 4
    if any(f.priority in ("P0", "P1") for f in findings):
        return 3
    return 0


def build_report(scope: Scope, ports: Sequence[PortResult], entries: Sequence[DirEntry],
                 baseline: Baseline, coverage: dict, guesses: Sequence[TechGuess],
                 findings: Sequence[Finding], params: dict) -> dict:
    return {
        "generated_at": now_iso(),
        "scope": scope.to_dict(),
        "params": params,
        "coverage": {
            "ports": {"total": len(ports),
                      "open": sum(1 for p in ports if p.state == "open"),
                      "closed": sum(1 for p in ports if p.state == "closed"),
                      "filtered": sum(1 for p in ports if p.state == "filtered"),
                      "error": sum(1 for p in ports if p.state == "error")},
            "dirs": coverage,
            "incomplete": bool(coverage.get("incomplete"))
            or any(p.state in ("filtered", "error") for p in ports),
        },
        "baseline": asdict(baseline),
        "dirs": [e.to_dict() for e in entries],
        "fingerprint": [g.to_dict() for g in guesses],
        "findings": [f.to_dict() for f in findings],
        "exit_code": exit_code(findings, ports, coverage),
    }


def render_markdown(report: dict) -> str:
    c = report["coverage"]
    lines = [
        "# 安全审计工具箱报告（资产面：端口 / 目录 / 指纹）",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 授权单号：{report['scope'].get('ticket') or '（未填写）'}",
        f"- 范围：{report['scope']['networks']} · 端口 {report['scope']['ports']}",
        f"- 基址：{report['scope']['http_bases']}",
        f"- 参数：`{report['params']}`",
        "",
        "## 覆盖与结论可信度",
        "",
        f"- 端口：总数 {c['ports']['total']}｜open {c['ports']['open']}｜closed {c['ports']['closed']}"
        f"｜filtered {c['ports']['filtered']}｜error {c['ports']['error']}",
        f"- 目录：词条 {c['dirs']['total']}｜已完成 {c['dirs']['completed']}"
        f"｜被限速 {c['dirs']['throttled']}｜错误 {c['dirs']['errors']}",
        f"- 软 404 基线：status={report['baseline']['status']}"
        f" len={report['baseline']['length']}（随机路径实测）",
        f"- **本轮是否完整：{'否（存在限速/超时/不可判定）' if c['incomplete'] else '是'}**",
        "",
        "## 指纹推断",
        "",
    ]
    if report["fingerprint"]:
        lines += ["| 推断 | 分值 | 置信度 | 证据 |", "| --- | --- | --- | --- |"]
        for g in report["fingerprint"]:
            lines.append(f"| {g['tech']} | {g['score']} | {g['confidence']} | "
                         f"{'; '.join(g['evidence'][:2])} |")
    else:
        lines.append("（无信号）")
    lines += ["", "## 目录结果", "",
              "| 路径 | 状态 | 分类 | 长度 | 说明 |", "| --- | --- | --- | --- | --- |"]
    for e in report["dirs"]:
        note = "软 404 可疑" if e["soft_404_suspect"] else (e["redirect_to"] or "-")
        lines.append(f"| /{e['word']} | {e['status']} | {e['category']} | {e['length']} | {note} |")
    lines += ["", "## 发现（事实 / 推断 / 待验证）", "",
              "| 优先级 | 严重度 | 置信度 | 类型 | 目标 | 说明 |", "| --- | --- | --- | --- | --- | --- |"]
    rank = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    for f in sorted(report["findings"], key=lambda x: rank[x["priority"]]):
        lines.append(f"| {f['priority']} | {f['severity']} | {f['confidence']} | {f['key']} | "
                     f"{f['target']} | {f['title']} |")
    lines += ["", "> 措辞边界：本报告只到『事实 / 推断 / 待验证』三档，"
                  "**不含『已验证漏洞』**。验证与利用需在单独授权的窗口内由人工完成。", ""]
    return "\n".join(lines)


# ── 自检 ───────────────────────────────────────────────────────────────

def _self_test() -> None:
    # 范围与 URL 门禁
    sc = default_lab_scope()
    sc.check_host_port("127.0.0.1", 8080)
    for bad in (("10.0.0.5", 8080), ("127.0.0.1", 22)):
        try:
            sc.check_host_port(*bad)
            raise AssertionError(f"越界应被拒绝: {bad}")
        except AuthorizationError:
            pass
    sc.check_url("http://127.0.0.1:8080/admin/")
    try:
        sc.check_url("http://evil.example/x")       # urljoin 可能产出绝对 URL
        raise AssertionError("基址外的 URL 必须被拒绝")
    except AuthorizationError:
        pass

    assert parse_port_spec("8000-8002,8080") == [8000, 8001, 8002, 8080]
    try:
        parse_host_spec("example.com")
        raise AssertionError("域名必须被拒绝")
    except ScopeError:
        pass

    with LabHTTP(port=0) as lab:
        base = f"http://127.0.0.1:{lab.port}"
        sc2 = Scope(networks=["127.0.0.1/32"], ports=[(lab.port, lab.port)],
                    http_bases=[base], ticket="SELF-TEST")
        # 只读 GET + 不跟随重定向
        root = fetch(f"{base}/")
        assert root.status == 200 and "Lab Portal" in root.body, root.status
        assert root.headers.get("Server", "").startswith("lab-nginx")
        admin = fetch(f"{base}/admin")
        assert admin.status == 301 and admin.redirect_to == "/admin/", admin.to_dict()
        forbidden = fetch(f"{base}/admin/")
        assert forbidden.status == 403, forbidden.status

        # 软 404 基线
        baseline = build_baseline(base, sc2)
        assert baseline.status == 200, baseline
        soft = fetch(f"{base}/legacy/app")
        assert baseline.matches(soft.status, soft.length), (soft.status, soft.length, baseline)
        real = fetch(f"{base}/healthz")
        assert not baseline.matches(real.status, real.length) or real.length != baseline.length

        # 目录爆破：分类正确
        entries, baseline2, coverage = dir_brute(
            base, ["healthz", "admin/", "admin", "backup.zip", "legacy/app", "phpinfo.php"],
            sc2, rate=200.0)
        by_word = {e.word: e for e in entries}
        assert by_word["healthz"].category == "accessible", by_word["healthz"]
        assert by_word["admin/"].category == "protected", by_word["admin/"]
        assert by_word["admin"].category == "redirect", by_word["admin"]
        assert by_word["legacy/app"].category == "soft_404", by_word["legacy/app"]
        assert by_word["phpinfo.php"].category == "missing", by_word["phpinfo.php"]
        assert coverage["incomplete"] is False, coverage

        # 指纹：多信号聚合
        probes = {"server-status": fetch(f"{base}/server-status"),
                  "backup.zip": fetch(f"{base}/backup.zip")}
        signals = collect_signals(root, probes)
        guesses = score_signals(signals)
        techs = {g.tech: g for g in guesses}
        assert techs["lab-cms"].confidence == "medium", techs.get("lab-cms")
        assert techs["apache"].confidence == "medium", techs.get("apache")
        assert all(g.score <= 0.95 for g in guesses)

        # Finding 与退出码
        findings = (findings_from_dirs(entries, coverage)
                    + findings_from_tech(guesses, root))
        keys = {f.key for f in findings}
        assert {"protected_path", "backup_artifact", "soft_404_noise"} <= keys, keys
        assert exit_code(findings, [], coverage) in (0, 3), exit_code(findings, [], coverage)

    # 429 与指数退避（限速演示）
    with LabHTTP(port=0, throttle_after=3) as lab2:
        base2 = f"http://127.0.0.1:{lab2.port}"
        sc3 = Scope(networks=["127.0.0.1/32"], ports=[(lab2.port, lab2.port)],
                    http_bases=[base2], ticket="SELF-TEST-429")
        t0 = time.perf_counter()
        entries2, _bl, cov2 = dir_brute(base2, ["healthz"] * 6, sc3, rate=200.0, max_backoff=0.5)
        elapsed = time.perf_counter() - t0
        assert cov2["throttled"] >= 1, (cov2, [e.status for e in entries2])
        assert cov2["incomplete"] is True
        assert elapsed >= 0.5 * cov2["backoff_events"] - 0.2, elapsed

    # 端口扫描三态
    with LabHTTP(port=0) as lab3:
        open_res = scan_port("127.0.0.1", lab3.port, timeout=0.3)
        assert open_res.state == "open", open_res
        # HTTP 是"请求先行"协议，不会主动吐 banner → 只能靠端口表推断（低置信）
        assert open_res.service_source == "port_map", open_res
    assert scan_port("127.0.0.1", 1, timeout=0.3).state == "closed"

    # banner 优先：开一个"主动问候"的 TCP 服务，验证 service 来自 banner（高置信）
    greet = socket.socket()
    greet.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    greet.bind(("127.0.0.1", 0))
    greet.listen(4)
    greet_port = greet.getsockname()[1]

    def _greet_loop() -> None:
        while True:
            try:
                conn, _ = greet.accept()
            except OSError:
                return
            try:
                conn.sendall(b"SSH-2.0-OpenSSH_lab\r\n")
            except OSError:
                pass
            finally:
                conn.close()

    threading.Thread(target=_greet_loop, daemon=True).start()
    try:
        r = scan_port("127.0.0.1", greet_port, timeout=0.3)
        assert r.state == "open" and r.service == "ssh", r
        assert r.service_source == "banner", r
    finally:
        greet.close()

    print("SELF-TEST OK")


if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
    else:
        print(__doc__)
