"""漏洞检测引擎共享核心（Day 163 · 安全审计工具箱 第 2 天）。

Day 162 解决的是"资产面"：**有什么**（端口 / 目录 / 技术栈）。
本模块解决"漏洞面"：**哪里可能有问题**（SQL 注入 / 反射型 XSS）。

它提供四样东西：

1. **Scope（范围门禁）**：主机 + 端口 + HTTP 基址三重校验。
   与 Day 162 同构，但**独立成文件**——这样 Day 163 可以单独运行，
   不依赖上一天的目录是否还在（教学代码要能"冻结快照"式复现）。
2. **LabVulnHTTP（本机实验靶标）**：只绑定 `127.0.0.1`，里面**故意**放着
   有缺陷的端点与安全的对照端点：

   | 端点 | 行为 | 用途 |
   |---|---|---|
   | `/product?id=1` | 把 `id` 直接拼进 SQL（模拟） | **有缺陷**：错误回显 + 布尔差分 |
   | `/safe-product?id=1` | 参数化，值当字面量 | **安全对照**：检测器必须在这里沉默 |
   | `/search?q=x` | 原样反射进 HTML 文本节点 | **有缺陷**：反射型 XSS |
   | `/safe-search?q=x` | `html.escape()` + CSP 头 | **安全对照** |
   | `/profile?name=x` | 反射进**双引号属性** | 上下文：属性内 |
   | `/greeting?name=x` | 反射进 `<script>` 块 | 上下文：脚本块（最危险） |
   | `/comment?note=x` | 反射进 HTML 注释 | 上下文：注释 |
   | `/echo?id=x` | 原样回显（**已转义**） | **假阳性陷阱**：长度必然变化 |

3. **只读 HTTP 客户端 `fetch()`**：只发 `GET`（幂等），不跟随重定向，
   不带任何凭据，响应体只读前 8KB。
4. **两个检测器**：
   * `detect_sqli()`：**错误回显** + **布尔差分**（基线锚定）；
   * `detect_xss()`：**反射确认** + **上下文判定** + **缓解措施检查**。

## 安全边界（刻意为之，读完再用）

* 只对**自己拥有或已书面授权**的目标使用；
* 只发 `GET`，**不 POST、不写数据**；
* SQLi 只做**检测**：不 `UNION` 取数、不拖库、不 `DROP`、不注释掉后续 SQL 做绕过；
* **不做时间盲注**（`SLEEP`/`pg_sleep`）：那是在目标上"占用资源"，本课刻意排除；
* XSS 探针**不是可执行载荷**：用自定义标签 `<zq163>`（浏览器不执行），
  而不是 `<script>alert(1)</script>`——原因见 README 2.6；
* 默认限速 **2 请求/秒**：每个探针都会真正进入服务端业务逻辑，
  比目录爆破更需要克制；
* 每个参数最多 **4 个探针**，并在报告里写明用了几个。

自检：
    python3 vuln_core.py --self-test     # 输出 SELF-TEST OK
"""

from __future__ import annotations

import html
import http.server
import json
import re
import socketserver
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

CST = timezone(timedelta(hours=8))
DEFAULT_TIMEOUT = 2.0
DEFAULT_RATE = 2.0            # 漏洞检测默认 2 请求/秒（比目录爆破更慢）
READ_LIMIT = 8192             # 响应体最多读这么多字节
MAX_PROBES_PER_PARAM = 4      # 每个参数最多几个探针（授权边界的"硬闸门"）

# 唯一标记：用于在响应中定位"我们的输入到底出现在哪一段字节里"
XSS_MARKER = "zq163x7"
# 无害探针：破引号 + 破标签 + 一个**自定义标签**（浏览器不认识 → 不执行）
# 刻意**不用** <script>alert(1)</script>：见 README 2.6「为什么探针不该是可执行载荷」
XSS_PROBE = XSS_MARKER + '"\'><zq163>'

# 数据库报错特征（全部小写后匹配）。注意：只**匹配特征**，不提取报错全文。
# 为什么？报错页里可能带出表名/列名等真实信息，把它们抄进报告 = 顺手泄密。
SQL_ERROR_SIGNATURES = (
    r"sql syntax",
    r"sqlite3\.",
    r"syntax error",
    r"unclosed quotation mark",
    r"you have an error in your sql",
    r"quoted string not properly terminated",
    r"ora-\d{5}",
    r"pg_query\(\)",
    r"mysql_fetch",
    r"warning:\s*mysql",
)

SEVERITY_LEVELS = ["info", "low", "medium", "high", "critical"]

# 上下文 → (严重度, 置信度, 说明)
XSS_CONTEXT_RISK = {
    "script_block":       ("high",   "high",   "位于 <script> 块内：闭合字符串即可执行 JS"),
    "attr_unquoted":      ("high",   "high",   "位于无引号属性内：空格即可注入事件处理器"),
    "attr_quoted_double": ("medium", "high",   "位于双引号属性内：需闭合引号才能注入"),
    "attr_quoted_single": ("medium", "high",   "位于单引号属性内：需闭合引号才能注入"),
    "text_node":          ("medium", "high",   "位于 HTML 文本节点：可注入标签"),
    "html_comment":       ("low",    "medium", "位于 HTML 注释：需先闭合注释才能利用"),
    "none":               ("info",   "high",   "未在响应中找到标记：未见反射"),
}


class AuthorizationError(RuntimeError):
    """越界。策略拒绝，**不重试、不降级**。"""


class ScopeError(ValueError):
    """范围/参数不合法。"""


# ── 基础工具 ───────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(CST).isoformat(timespec="seconds")


def sanitize(text: str, limit: int = 80) -> str:
    """响应内容一律视为**目标控制**的不可信文本：净化控制字符并截断。

    为什么必须做？因为报告是给人看的（Markdown/终端），目标可以在响应里
    塞 ANSI 转义、`\\r`、超长字符串，污染日志甚至伪造报告结构。
    """
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


# ── 范围门禁 ───────────────────────────────────────────────────────────

@dataclass
class Scope:
    """授权范围。`check_url()` 是**唯一**允许构造请求的出口。"""

    networks: Sequence[str] = ("127.0.0.1/32",)
    ports: Sequence[int] = (8086,)
    http_bases: Sequence[str] = ("http://127.0.0.1:8086",)
    ticket: str = "LAB-163-LOCAL"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["networks"] = list(self.networks)
        d["ports"] = list(self.ports)
        d["http_bases"] = list(self.http_bases)
        return d

    def _host_allowed(self, host: str) -> bool:
        import ipaddress
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return False                      # 域名一律拒绝：解析域名本身就是一次外发
        for net in self.networks:
            if ip in ipaddress.ip_network(net, strict=False):
                return True
        return False

    def check_url(self, url: str) -> str:
        """协议 / 主机 / 端口 / 基址前缀 四重校验。越界抛 AuthorizationError。"""
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in ("http", "https"):
            raise AuthorizationError(f"协议不允许: {parts.scheme}")
        host, port = parts.hostname or "", parts.port or (443 if parts.scheme == "https" else 80)
        if not self._host_allowed(host):
            raise AuthorizationError(f"主机不在授权网段内: {host}（URL: {url}）")
        if port not in tuple(self.ports):
            raise AuthorizationError(f"端口不在授权列表内: {port}（URL: {url}）")
        base_ok = any(url.startswith(b.rstrip("/") + "/") or url.rstrip("/") == b.rstrip("/")
                      for b in self.http_bases)
        if not base_ok:
            raise AuthorizationError(f"URL 不在授权基址之内: {url}")
        return url


def default_lab_scope(port: int = 8086) -> Scope:
    return Scope(networks=("127.0.0.1/32",), ports=(port,),
                 http_bases=(f"http://127.0.0.1:{port}",), ticket="LAB-163-LOCAL")


# ── 实验靶标（本机回环） ───────────────────────────────────────────────

PRODUCTS = [
    {"id": 1, "name": "lab-router", "price": 199},
    {"id": 2, "name": "lab-switch", "price": 349},
]

LAB_INDEX_HTML = (
    "<!DOCTYPE html><html><head><title>Vuln Lab</title></head><body>"
    "<h1>Vuln Lab（Day 163 实验靶标）</h1>"
    "<ul>"
    '<li><a href="/product?id=1">/product?id=1</a> — SQLi 有缺陷</li>'
    '<li><a href="/safe-product?id=1">/safe-product?id=1</a> — SQLi 对照（安全）</li>'
    '<li><a href="/search?q=hello">/search?q=hello</a> — XSS 有缺陷</li>'
    '<li><a href="/safe-search?q=hello">/safe-search?q=hello</a> — XSS 对照（安全）</li>'
    '<li><a href="/profile?name=ops">/profile?name=ops</a> — 属性上下文</li>'
    '<li><a href="/greeting?name=ops">/greeting?name=ops</a> — 脚本块上下文</li>'
    '<li><a href="/comment?note=hi">/comment?note=hi</a> — 注释上下文</li>'
    "<li>/echo?id=x — 假阳性陷阱（已转义，但长度必变）</li>"
    "</ul></body></html>"
)


class LabSQLError(Exception):
    """模拟"数据库把语法错误抛回给了 Web 层"。"""


def _fake_execute(expr: str) -> list[dict]:
    """模拟一个**把用户输入直接拼进 SQL** 的服务端（这就是缺陷本身）。

    真实的缺陷是 `"SELECT * FROM products WHERE id = '" + user_input + "'"`。
    这里用一个 40 行的确定性小引擎复刻它的可观测行为，好处是：
    实验可复现、不需要真实数据库、也**不可能**误伤真实数据。
    """
    if expr.count("'") % 2 == 1:                      # 引号不配对 → 语法错误
        raise LabSQLError(f'near "{expr}": syntax error')
    if re.search(r"and\s+1\s*=\s*2", expr, re.I):     # 恒假 → 无结果
        return []
    if re.search(r"and\s+1\s*=\s*1", expr, re.I):     # 恒真 → 全部结果
        return list(PRODUCTS)
    return [p for p in PRODUCTS if str(p["id"]) == expr.strip()]


def _alert_page(text: str, title: str = "Lab") -> str:
    return f"<!DOCTYPE html><html><head><title>{title}</title></head><body>{text}</body></html>"


def _rows_html(rows: Sequence[dict]) -> str:
    if not rows:
        return "<p>没有匹配的商品。</p>"
    items = "".join(f"<li>#{r['id']} {r['name']} ¥{r['price']}</li>" for r in rows)
    return f"<p>共 {len(rows)} 条结果</p><ul>{items}</ul>"


class _LabHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _LabHandler(http.server.BaseHTTPRequestHandler):
    server_version = "vuln-lab/0.9"
    sys_version = ""

    def log_message(self, *args) -> None:      # 静音，避免污染演示输出
        pass

    def _send(self, code: int, ctype: str, body: str, extra: dict | None = None) -> None:
        payload = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if payload:
            self.wfile.write(payload)

    def do_GET(self) -> None:                  # noqa: N802 - 框架约定
        srv: _LabHTTPServer = self.server      # type: ignore[assignment]
        with srv.counter_lock:                 # type: ignore[attr-defined]
            srv.request_count += 1             # type: ignore[attr-defined]
            count = srv.request_count          # type: ignore[attr-defined]
        if srv.throttle_after and count > srv.throttle_after:   # type: ignore[attr-defined]
            self._send(429, "text/plain", "Too Many Requests", {"Retry-After": "1"})
            return

        parts = urllib.parse.urlsplit(self.path)
        path = parts.path
        q = {k: v[0] for k, v in urllib.parse.parse_qs(parts.query, keep_blank_values=True).items()}

        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", LAB_INDEX_HTML)
            return

        # ── SQLi：有缺陷的端点（字符串拼接） ──
        if path == "/product":
            expr = q.get("id", "1")
            try:
                rows = _fake_execute(expr)
            except LabSQLError as exc:
                # 典型错误配置：把数据库异常页直接返回给客户端（verbose error）
                page = _alert_page(
                    f"<h1>Internal Server Error</h1>"
                    f"<pre>sqlite3.OperationalError: {exc}</pre>", "500")
                self._send(500, "text/html; charset=utf-8", page)
                return
            self._send(200, "text/html; charset=utf-8",
                       _alert_page(f"<h1>商品查询</h1>{_rows_html(rows)}"))
            return

        # ── SQLi：安全对照（参数化：值永远是字面量） ──
        if path == "/safe-product":
            literal = q.get("id", "1")
            rows = [p for p in PRODUCTS if str(p["id"]) == literal]
            self._send(200, "text/html; charset=utf-8",
                       _alert_page(f"<h1>商品查询（参数化）</h1>{_rows_html(rows)}"))
            return

        # ── XSS：有缺陷的端点（原样反射进文本节点） ──
        if path == "/search":
            value = q.get("q", "")
            page = _alert_page(
                f"<h1>搜索</h1><form action='/search'><input name='q'></form>"
                f"<p>未找到 “{value}” 的相关结果。</p>", "Search")
            self._send(200, "text/html; charset=utf-8", page)
            return

        # ── XSS：安全对照（转义 + CSP） ──
        if path == "/safe-search":
            value = html.escape(q.get("q", ""), quote=True)
            page = _alert_page(f"<h1>搜索（安全）</h1><p>未找到 “{value}” 的相关结果。</p>", "SafeSearch")
            self._send(200, "text/html; charset=utf-8", page,
                       {"Content-Security-Policy": "default-src 'self'; object-src 'none'",
                        "X-Content-Type-Options": "nosniff"})
            return

        # ── XSS：属性上下文（双引号属性内，原样反射） ──
        if path == "/profile":
            value = q.get("name", "")
            page = _alert_page(
                f"<h1>个人资料</h1><form><input name='fullname' value=\"{value}\">"
                f"<button>保存</button></form>", "Profile")
            self._send(200, "text/html; charset=utf-8", page)
            return

        # ── XSS：脚本块上下文（最危险的一种） ──
        if path == "/greeting":
            value = q.get("name", "")
            page = _alert_page(
                "<h1>欢迎</h1><div id='greet'></div>"
                f"<script>var who = \"{value}\";"
                "document.getElementById('greet').textContent = 'Hi ' + who;</script>",
                "Greeting")
            self._send(200, "text/html; charset=utf-8", page)
            return

        # ── XSS：注释上下文 ──
        if path == "/comment":
            value = q.get("note", "")
            page = _alert_page(f"<h1>订单备注</h1><!-- note: {value} --><p>已保存</p>", "Comment")
            self._send(200, "text/html; charset=utf-8", page)
            return

        # ── 假阳性陷阱：转义了（不是 XSS），但页面**原样回显输入**，
        #    因此任何"比长度"的检测器都会看到"响应长度变了"→ 误报。
        if path == "/echo":
            value = html.escape(q.get("id", ""), quote=True)
            page = _alert_page(f"<h1>回显</h1><p>你输入的是：{value}</p>", "Echo")
            self._send(200, "text/html; charset=utf-8", page)
            return

        self._send(404, "text/html; charset=utf-8", _alert_page("<h1>404</h1>", "404"))

    def do_HEAD(self) -> None:                 # noqa: N802
        self.do_GET()


class LabVulnHTTP:
    """本机实验靶标服务（仅回环）。`throttle_after` 用于演示 429 覆盖缺口。"""

    def __init__(self, port: int = 8086, host: str = "127.0.0.1",
                 throttle_after: int | None = None):
        self.host, self.port, self.throttle_after = host, port, throttle_after
        self._httpd: _LabHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> int:
        httpd = _LabHTTPServer((self.host, self.port), _LabHandler)
        httpd.request_count = 0                                   # type: ignore[attr-defined]
        httpd.counter_lock = threading.Lock()                     # type: ignore[attr-defined]
        httpd.throttle_after = self.throttle_after                # type: ignore[attr-defined]
        self._httpd = httpd
        self.port = httpd.server_address[1]
        self._thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self._thread.start()
        return self.port

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def __enter__(self) -> "LabVulnHTTP":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()


# ── 只读 HTTP 客户端 ───────────────────────────────────────────────────

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """捕获重定向而**不自动跟随**（避免被引到范围外，也避免掩盖真实状态码）。"""

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
                                 headers={"User-Agent": "vuln-lab/1.0 (authorized audit)"})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            raw = resp.read(READ_LIMIT)
            return HttpResult(
                url=url, status=resp.status, length=len(raw),
                body=raw.decode("utf-8", "replace"),
                headers={k: v for k, v in resp.headers.items()},
                elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
            )
    except urllib.error.HTTPError as exc:      # 4xx/5xx（含未跟随的 3xx）走这里
        raw = exc.read(READ_LIMIT) if hasattr(exc, "read") else b""
        return HttpResult(
            url=url, status=exc.code, length=len(raw),
            body=raw.decode("utf-8", "replace"),
            headers={k: v for k, v in (exc.headers or {}).items()},
            elapsed_ms=round((time.perf_counter() - started) * 1000, 2),
        )
    except Exception as exc:                    # noqa: BLE001 - 网络异常统一记录
        return HttpResult(url=url, error=f"{type(exc).__name__}: {exc}",
                          elapsed_ms=round((time.perf_counter() - started) * 1000, 2))


# ── 限速 ───────────────────────────────────────────────────────────────

class TokenBucket:
    """令牌桶限速。默认 2 请求/秒：探针会进入业务逻辑，比目录爆破更需要克制。"""

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


# ── 工具：URL 参数改写 ─────────────────────────────────────────────────

def set_query_param(url: str, name: str, value: str) -> str:
    """安全地把 URL 里的某个查询参数替换成探针值（其余参数原样保留）。"""
    parts = urllib.parse.urlsplit(url)
    pairs = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    found = False
    out: list[tuple[str, str]] = []
    for k, v in pairs:
        if k == name:
            out.append((k, value))
            found = True
        else:
            out.append((k, v))
    if not found:                     # 参数不存在就**不擅自添加**：新增参数可能改变业务行为
        raise ScopeError(f"URL 中不存在参数 {name!r}：{url}")
    query = urllib.parse.urlencode(out, quote_via=urllib.parse.quote)
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


class RateLimiter:
    """限速 + 429 计数的小包装，让检测器把"覆盖缺口"如实带进报告。"""

    def __init__(self, rate: float = DEFAULT_RATE, max_probes: int = MAX_PROBES_PER_PARAM):
        self.bucket = TokenBucket(rate=rate)
        self.max_probes = max_probes
        self.probes = 0
        self.throttled = 0
        self.errors = 0

    def get(self, url: str, timeout: float = DEFAULT_TIMEOUT) -> HttpResult:
        if self.probes >= self.max_probes:
            raise ScopeError(f"探针数超过上限 {self.max_probes}：授权边界拒绝继续")
        self.bucket.acquire()
        self.probes += 1
        res = fetch(url, timeout=timeout)
        if res.status == 429:
            self.throttled += 1
        elif res.error:
            self.errors += 1
        return res


# ── SQLi 检测器 ────────────────────────────────────────────────────────

@dataclass
class SqliProbe:
    label: str
    value: str
    status: int
    length: int
    note: str = ""


@dataclass
class SqliResult:
    url: str
    param: str
    base_value: str
    probes: list[SqliProbe] = field(default_factory=list)
    technique: str = ""            # error_based / boolean_based / none
    evidence: str = ""
    sql_error_hit: bool = False
    throttled: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["probes"] = [asdict(p) for p in self.probes]
        return d


def match_sql_error(body: str) -> str:
    """在响应体里匹配**数据库报错特征**。只返回命中的特征名，不回抄报错全文。"""
    low = body.lower()
    for sig in SQL_ERROR_SIGNATURES:
        if re.search(sig, low):
            return sig
    return ""


def detect_sqli(url: str, scope: Scope, param: str | None = None,
                rate: float = DEFAULT_RATE, timeout: float = DEFAULT_TIMEOUT,
                tol_abs: int = 32, tol_rel: float = 0.05) -> SqliResult:
    """对 URL 中的参数做**两段式** SQLi 检测。

    探针计划（最多 4 个，顺序固定）：

    ```text
    #0 baseline : 原值            → 建立"正常响应"的锚点
    #1 error    : 原值 + '        → 触发语法错误 → 报错回显（error-based）
    #2 true     : 1 AND 1=1       → 应等价于 baseline（结果集不变）
    #3 false    : 1 AND 1=2       → 应产生不同响应（结果集为空）
    ```

    为什么布尔差分必须**锚定 baseline**？见 README 3.3：
    只比较 true/false 两者的差异会被"回显型"页面骗到（`/echo` 陷阱）。

    返回 `SqliResult`；**不做**任何数据提取、不构造 UNION、不时间盲注。
    """
    scope.check_url(url)
    if param is None:
        query = urllib.parse.urlsplit(url).query
        first = urllib.parse.parse_qsl(query, keep_blank_values=True)
        if not first:
            raise ScopeError("URL 中没有可测参数")
        param = first[0][0]
    base_value = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get(param, "")
    if not base_value:
        base_value = "1"

    lim = RateLimiter(rate=rate)
    result = SqliResult(url=url, param=param, base_value=base_value)

    plan = [
        ("baseline", base_value),
        ("error", base_value + "'"),
        ("true", f"{base_value} AND 1=1"),
        ("false", f"{base_value} AND 1=2"),
    ]

    seen: dict[str, HttpResult] = {}
    for label, value in plan:
        target = set_query_param(url, param, value)
        scope.check_url(target)
        res = lim.get(target, timeout=timeout)
        seen[label] = res
        result.probes.append(SqliProbe(label=label, value=value, status=res.status,
                                       length=res.length,
                                       note=sanitize(res.error, 60) if res.error else ""))

    result.throttled = lim.throttled > 0

    # ① 报错回显：状态码 5xx 或响应体匹配数据库报错特征
    err_sig = ""
    for label in ("error", "true", "false"):
        res = seen.get(label)
        if res is None:
            continue
        sig = match_sql_error(res.body)
        if res.status >= 500 or sig:
            err_sig = sig or f"HTTP {res.status}"
            break
    if err_sig:
        result.technique = "error_based"
        result.sql_error_hit = True
        result.evidence = f"探针 {label!r} 触发数据库报错特征: {err_sig}"
        return result

    # ② 布尔差分：true 必须"贴近 baseline"，false 必须"明显偏离 baseline"
    base, t, f = seen.get("baseline"), seen.get("true"), seen.get("false")
    if base and t and f and base.status == 200:
        def close(a: int, b: int) -> bool:
            return abs(a - b) <= max(tol_abs, tol_rel * max(a, b))

        if t.status == f.status and close(t.length, base.length) and not close(f.length, base.length):
            result.technique = "boolean_based"
            result.evidence = (f"true 探针贴近 baseline（{t.length}≈{base.length}），"
                               f"false 探针偏离（{f.length}）")
            return result

    result.technique = "none"
    result.evidence = "探针未触发报错，且布尔对未形成「贴近基线 / 偏离基线」的差值"
    return result


# ── XSS 检测器 ─────────────────────────────────────────────────────────

def classify_context(body: str, marker: str) -> str:
    """判断标记出现在 HTML 的哪种上下文里（决定严重度）。

    为什么必须判定上下文？因为"能不能注入标签"和"注入后能不能执行"
    是两件事：文本节点里注入 `<zq163>` 只是标签注入；
    但 `<script>` 块里的 `"` 就能闭合字符串、直接执行任意 JS。
    """
    idx = body.find(marker)
    if idx < 0:
        return "none"
    before = body[:idx]
    # 1) HTML 注释
    if before.rfind("<!--") > before.rfind("-->"):
        return "html_comment"
    # 2) <script> / <style> 块内
    open_block = max(before.rfind("<script"), before.rfind("<style"))
    if open_block != -1 and open_block > before.rfind("</script>") \
            and open_block > before.rfind("</style>"):
        return "script_block"
    # 3) 标签内部（最近一个 '<' 还没被 '>' 闭合）
    if before.rfind("<") > before.rfind(">"):
        fragment = body[before.rfind("<"):idx]
        if re.search(r"=\s*\"[^\"]*$", fragment):
            return "attr_quoted_double"
        if re.search(r"=\s*'[^']*$", fragment):
            return "attr_quoted_single"
        return "attr_unquoted"
    return "text_node"


@dataclass
class XssResult:
    url: str
    param: str
    probe: str
    reflected: bool = False
    raw_tag: bool = False          # 探针里的 <zq163> 原样出现在响应里 → HTML 注入成立
    raw_full: bool = False         # 连引号都原样出现
    escaped: bool = False          # 出现的是 &lt;zq163&gt; 等实体 → 已转义
    context: str = "none"
    severity: str = "info"
    confidence: str = "high"
    risk_note: str = ""
    mitigations: list[str] = field(default_factory=list)
    throttle_or_error: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def check_xss_mitigations(headers: dict) -> list[str]:
    """检查与 XSS 相关的响应头。头部字段是**硬事实**（但不能证明端点安全）。"""
    low = {k.lower(): v for k, v in headers.items()}
    missing = []
    if "content-security-policy" not in low:
        missing.append("缺少 Content-Security-Policy（无纵深防御，注入一旦成立即可执行）")
    if low.get("x-content-type-options", "").lower() != "nosniff":
        missing.append("缺少 X-Content-Type-Options: nosniff（可能被 MIME 嗅探利用）")
    ctype = low.get("content-type", "")
    if "charset" not in ctype.lower():
        missing.append(f"Content-Type 未声明字符集（{sanitize(ctype, 40) or '缺失'}）：可能触发编码混淆")
    return missing


def detect_xss(url: str, scope: Scope, param: str | None = None,
               rate: float = DEFAULT_RATE, timeout: float = DEFAULT_TIMEOUT) -> XssResult:
    """反射型 XSS 检测：**反射确认 → 转义判定 → 上下文判定 → 缓解措施**。

    探针是 `XSS_PROBE`（唯一标记 + 破引号 + 非可执行的自定义标签）。
    只看"响应里出现了什么"，**不构造任何可执行脚本**（边界见 README 2.6）。
    """
    scope.check_url(url)
    if param is None:
        first = urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query, keep_blank_values=True)
        if not first:
            raise ScopeError("URL 中没有可测参数")
        param = first[0][0]

    lim = RateLimiter(rate=rate, max_probes=2)
    target = set_query_param(url, param, XSS_PROBE)
    scope.check_url(target)
    res = lim.get(target, timeout=timeout)

    out = XssResult(url=url, param=param, probe=XSS_PROBE)
    if res.status == 429 or res.error:
        out.throttle_or_error = True
        out.confidence = "unknown"
        out.risk_note = f"未取得有效响应（status={res.status} error={sanitize(res.error, 40)}）"
        return out

    body = res.body
    out.reflected = XSS_MARKER in body
    out.raw_full = XSS_PROBE in body
    out.raw_tag = "<zq163>" in body
    out.escaped = ("&lt;zq163&gt;" in body) or (html.escape(XSS_PROBE, quote=True) in body)
    out.context = classify_context(body, XSS_MARKER) if out.reflected else "none"
    out.mitigations = check_xss_mitigations(res.headers)

    if not out.reflected:
        out.severity, out.confidence = "info", "high"
        out.risk_note = "标记未在响应中出现：本轮未观察到反射（不代表其他参数/编码下也安全）"
        return out

    if out.raw_tag or out.raw_full:
        sev, conf, note = XSS_CONTEXT_RISK.get(out.context, ("medium", "medium", "上下文未识别"))
        out.severity, out.confidence, out.risk_note = sev, conf, note
        if out.mitigations:
            out.risk_note += "；且响应缺少缓解措施"
    elif out.escaped:
        out.severity, out.confidence = "info", "high"
        out.risk_note = "标记被 HTML 实体转义（&lt;zq163&gt;）：本轮未发现反射注入"
    else:
        out.severity, out.confidence = "low", "medium"
        out.risk_note = "标记被反射但危险字符未完整出现：可能被部分过滤，建议人工确认编码链"
    return out


# ── Finding 与报告 ─────────────────────────────────────────────────────

@dataclass
class Finding:
    key: str
    title: str
    severity: str
    confidence: str
    target: str
    evidence: str
    detail: str = ""

    @property
    def priority(self) -> str:
        sev = SEVERITY_LEVELS.index(self.severity)
        conf = SEVERITY_LEVELS.index(self.confidence)
        score = (sev + 1) * (conf + 1)
        return "P0" if score >= 20 else "P1" if score >= 12 else "P2" if score >= 6 else "P3"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["priority"] = self.priority
        return d


def findings_from_sqli(results: Sequence[SqliResult]) -> list[Finding]:
    out: list[Finding] = []
    for r in results:
        if r.throttled:
            out.append(Finding(
                key="coverage_gap", title="漏洞检测未完成：目标限速",
                severity="medium", confidence="high", target=r.url,
                evidence=f"探针 {len(r.probes)} 个中出现 429",
                detail="限速期间提交的参数**未得到有效结论**，需降速重跑。",
            ))
            continue
        if r.technique == "error_based":
            out.append(Finding(
                key="sqli_error_based", title=f"疑似 SQL 注入（错误回显）：参数 {r.param}",
                severity="high", confidence="high", target=r.url,
                evidence=r.evidence,
                detail="证据：错误探针触发了数据库报错特征。本工具**未做任何数据提取**，"
                       "需人工在授权窗口内复核（参数化修复是标准处置）。",
            ))
        elif r.technique == "boolean_based":
            out.append(Finding(
                key="sqli_boolean_based", title=f"疑似 SQL 注入（布尔差分）：参数 {r.param}",
                severity="high", confidence="medium", target=r.url,
                evidence=r.evidence,
                detail="证据：恒真探针等价于基线、恒假探针明显偏离。"
                       "置信度只到 medium——动态内容也可能造成长度差异，需人工复核。",
            ))
        else:
            out.append(Finding(
                key="sqli_none", title=f"未发现 SQLi 迹象：参数 {r.param}",
                severity="info", confidence="medium", target=r.url,
                evidence=r.evidence,
                detail="只代表**这 4 个探针**没有命中，不代表该参数安全。",
            ))
    return out


def findings_from_xss(results: Sequence[XssResult]) -> list[Finding]:
    out: list[Finding] = []
    for r in results:
        if r.throttle_or_error:
            out.append(Finding(
                key="coverage_gap", title="XSS 检测未完成：限速或网络异常",
                severity="medium", confidence="high", target=r.url,
                evidence=r.risk_note,
                detail="本轮无结论，需重跑。",
            ))
            continue
        key = "xss_reflected" if r.raw_tag or r.raw_full else (
            "xss_escaped" if r.escaped else "xss_none")
        title = {
            "xss_reflected": f"疑似反射型 XSS（上下文：{r.context}）：参数 {r.param}",
            "xss_escaped": f"未见反射注入（已转义）：参数 {r.param}",
            "xss_none": f"未见反射：参数 {r.param}",
        }[key]
        out.append(Finding(
            key=key, title=title, severity=r.severity, confidence=r.confidence,
            target=r.url,
            evidence=f"probe={sanitize(r.probe, 40)} context={r.context} raw_tag={r.raw_tag} escaped={r.escaped}",
            detail=r.risk_note + ("；缓解措施缺口：" + "、".join(r.mitigations) if r.mitigations else ""),
        ))
        if (r.raw_tag or r.raw_full) and r.mitigations:
            out.append(Finding(
                key="xss_mitigation_missing", title=f"XSS 缓解措施缺失（{r.context}）",
                severity="low", confidence="high", target=r.url,
                evidence="; ".join(sanitize(m, 60) for m in r.mitigations),
                detail="头部缺失是**事实**，但「缺头不等于是有洞」：它的意义是"
                       "「一旦注入成立，没有纵深防御兜底」。",
            ))
    return out


def exit_code(findings: Sequence[Finding], incomplete: bool) -> int:
    """语义化退出码：2 越界/用法 > 4 覆盖不完整 > 3 有 P0/P1 > 0 干净。"""
    if incomplete:
        return 4
    if any(f.priority in ("P0", "P1") for f in findings):
        return 3
    return 0


def build_report(scope: Scope, sqli: Sequence[SqliResult], xss: Sequence[XssResult],
                 findings: Sequence[Finding], coverage: dict, tag: str = "day163") -> dict:
    return {
        "tool": "vuln-lab/0.9 (Day 163 · 检测-only)",
        "tag": tag,
        "generated_at": now_iso(),
        "scope": scope.to_dict(),
        "coverage": coverage,
        "sqli": [r.to_dict() for r in sqli],
        "xss": [r.to_dict() for r in xss],
        "findings": [f.to_dict() for f in findings],
        "summary": {
            "total": len(findings),
            "by_priority": {p: sum(1 for f in findings if f.priority == p)
                            for p in ("P0", "P1", "P2", "P3")},
        },
        "disclaimer": (
            "本报告由自动化**检测**工具产出，全部结论停留在"
            "「事实 / 推断 / 待验证」三档，**不含任何已验证漏洞**；"
            "未做数据提取、未做绕过、未使用凭据。"
        ),
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# 漏洞检测报告 · {report['tag']}",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 授权范围：{', '.join(report['scope']['http_bases'])}",
        f"- 探针合计：{report['coverage'].get('probes', 0)}"
        f"（限速命中 {report['coverage'].get('throttled', 0)}）",
        f"- 覆盖：{'完整' if not report['coverage'].get('incomplete') else '**不完整（存在 429/异常）**'}",
        "",
        "## 发现汇总",
        "",
        "| 优先级 | 严重度 | 置信度 | 发现 |",
        "|---|---|---|---|",
    ]
    for f in report["findings"]:
        lines.append(f"| {f['priority']} | {f['severity']} | {f['confidence']} | {f['title']} |")
    lines += ["", "## 明细", ""]
    for f in report["findings"]:
        lines += [f"### {f['priority']} · {f['title']}", "",
                  f"- 目标：`{f['target']}`",
                  f"- 证据：{f['evidence']}"]
        if f.get("detail"):
            lines.append(f"- 说明：{f['detail']}")
        lines.append("")
    lines += ["## SQLi 探针明细", "", "| 参数 | 探针 | 值 | 状态 | 长度 |", "|---|---|---|---|---|"]
    for r in report["sqli"]:
        for p in r["probes"]:
            lines.append(f"| {r['param']} | {p['label']} | `{p['value']}` | {p['status']} | {p['length']} |")
    lines += ["", "## XSS 探针明细", "", "| 参数 | 反射 | 原样标签 | 已转义 | 上下文 | 严重度 |", "|---|---|---|---|---|---|"]
    for r in report["xss"]:
        lines.append(f"| {r['param']} | {r['reflected']} | {r['raw_tag']} | {r['escaped']} | "
                     f"{r['context']} | {r['severity']} |")
    lines += ["", "---", "", f"> {report['disclaimer']}"]
    return "\n".join(lines) + "\n"


def write_report(report: dict, out_dir: str | Path = "out") -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"{report['tag']}-report.json"
    mp = out / f"{report['tag']}-report.md"
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    mp.write_text(render_markdown(report), encoding="utf-8")
    return jp, mp


# ── 自检 ───────────────────────────────────────────────────────────────

def _self_test() -> None:
    """端到端自检：起靶标 → 跑两个检测器 → 校验"该报的报、该沉默的沉默"。"""
    port = 18086
    with LabVulnHTTP(port=port) as lab:
        scope = default_lab_scope(port)
        base = f"http://127.0.0.1:{port}"

        # ① SQLi：有缺陷的端点必须报出来
        r1 = detect_sqli(f"{base}/product?id=1", scope, rate=50)
        assert r1.technique == "error_based", r1
        assert r1.sql_error_hit

        # ② SQLi：安全对照必须沉默
        r2 = detect_sqli(f"{base}/safe-product?id=1", scope, rate=50)
        assert r2.technique == "none", r2

        # ③ XSS：有缺陷的端点必须报出来，且上下文=属性/文本
        r3 = detect_xss(f"{base}/search?q=hi", scope, rate=50)
        assert r3.raw_tag and r3.context == "text_node", r3
        r4 = detect_xss(f"{base}/greeting?name=hi", scope, rate=50)
        assert r4.context == "script_block" and r4.severity == "high", r4

        # ④ XSS：安全对照必须沉默
        r5 = detect_xss(f"{base}/safe-search?q=hi", scope, rate=50)
        assert not r5.raw_tag and r5.escaped, r5

        # ⑤ 假阳性陷阱：/echo 已转义 → 不是 XSS，且 SQLi 布尔差分也必须沉默
        r6 = detect_xss(f"{base}/echo?id=hi", scope, rate=50)
        assert not r6.raw_tag and r6.escaped, r6
        r7 = detect_sqli(f"{base}/echo?id=1", scope, rate=50)
        assert r7.technique == "none", r7

        # ⑥ 越界必须被门禁拒绝
        try:
            detect_sqli("http://192.0.2.1:8086/product?id=1", scope, rate=50)
            raise AssertionError("越界未被拒绝")
        except AuthorizationError:
            pass

        # ⑦ 探针上限必须生效
        try:
            detect_sqli(f"{base}/product?id=1", scope, rate=50, param="id")
            lim = RateLimiter(rate=50, max_probes=2)
            for _ in range(3):
                lim.get(f"{base}/product?id=1")
            raise AssertionError("探针上限未生效")
        except ScopeError:
            pass

    print("SELF-TEST OK")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _self_test()
    else:
        print(__doc__)
