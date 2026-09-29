#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 155 · 示例 00 —— 本地 MITM 实验台（纯标准库，不需要安装 mitmproxy）
======================================================================

为什么要写这个文件？
--------------------
学习 mitmproxy 有三道门槛：
  1. `pip install mitmproxy` 在某些环境装不上（要编译、要 root、要联网）；
  2. 要抓 HTTPS 还得给客户端装 CA 证书，踩坑一大堆；
  3. 抓真实站点流量**违法**，抓自己的 App 又需要环境。

所以这里用 **Python 标准库** 搭一个完整的、只在 127.0.0.1 上跑的实验台：

  ┌──────────┐   绝对URI请求     ┌──────────────┐   HTTP/1.1    ┌────────────┐
  │ 客户端    │ ───────────────► │ MiniProxy     │ ───────────► │ OriginServer│
  │ curl/urllib│ ◄─────────────── │ (正向代理)    │ ◄─────────── │ (假上游站点) │
  └──────────┘                  └──────┬───────┘               └────────────┘
                                       │ 调用 Addon 的 request()/response()
                                       ▼
                                ┌──────────────┐
                                │ 你的 Addon    │  ← 与 mitmproxy 同一套 API
                                └──────────────┘

它包含三个部件：
  A. `OriginServer`  —— 假上游站点：/api/users、/login、/gzip、/slow、/admin …
  B. `MiniProxy`     —— 真正的 HTTP 正向代理（支持绝对 URI 请求 + 405/501 说明）
  C. `mitmproxy` shim—— 把 `ctx` / `http` / `flow` 对象按 mitmproxy 的语义实现，
                        并通过 sys.modules 注入，这样你为 mitmproxy 写的 Addon
                        **一行都不用改**就能在这里跑（`from mitmproxy import ctx, http` 会成功）。

shim 刻意对齐的关键语义（都是 mitmproxy 里最容易踩坑的地方）：
  · `flow.response.text`  自动 gunzip 解压 + 解码；
  · 给 `.text` / `.content` **赋值后自动重算 Content-Length**（坑 1）；
  · `flow.response.headers` 大小写不敏感（坑 4）；
  · `http.Response.make(status, body, headers)` 直接造响应（mock，坑 6）；
  · `ctx.options` 支持 addon 自定义 `--set` 选项（`loader.add_option`）。

局限（必须知道，别当成真 mitmproxy）：
  · **只支持明文 HTTP**，不支持 CONNECT 隧道 → HTTPS 拦截必须用真 mitmproxy + 装 CA；
  · 不做连接复用/HTTP2/WebSocket；每次请求一条连接；
  · `getaddrinfo` 只连 127.0.0.1/localhost 以外的地址时会**拒绝**（防止误用到外网）。

运行：
    # 1) 直接起实验台（含上游站点），打印使用说明
    python3 code/00-local-lab.py

    # 2) 加载某个 Addon 一起跑（Addon 文件写的是 mitmproxy API，不用改）
    python3 code/00-local-lab.py --addon code/01-addon-basics.py
    python3 code/00-local-lab.py --addon code/02-addon-pitfalls.py --set demo_rewrite=true
    python3 code/00-local-lab.py --addon code/03-traffic-tool.py --set traffic_out_dir=/tmp/traffic

    # 3) 离线自检（自动起服务、发请求、断言结果，全程 127.0.0.1）
    python3 code/00-local-lab.py --self-test

⚠️ 安全设计：监听地址硬编码 127.0.0.1（没有参数可以改成对外），
   上游白名单默认只允许 127.0.0.1 / localhost。所有演示都不出本机。
"""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import socket
import sys
import threading
import time
import types
import urllib.error
import urllib.parse
import urllib.request
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 只允许代理去连这些主机（防止这个实验台被当成"任意转发器"）
ALLOWED_UPSTREAM = {"127.0.0.1", "localhost", "::1"}

# hop-by-hop 头：RFC 7230 §6.1 明确要求代理**不要**转发这些头
HOP_BY_HOP = {
    "connection", "proxy-connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade",
}


# ═══════════════════════════════════════════════════════════════
# A. 假上游站点（OriginServer）
# ═══════════════════════════════════════════════════════════════
USERS_JSON = json.dumps({"users": [{"id": 1, "name": "nina"}, {"id": 2, "name": "leo"}]},
                        ensure_ascii=False).encode()
PAGE_HTML = (b"<!DOCTYPE html><html><head><title>Origin App</title></head>\n"
             b"<body><h1>Origin App</h1><p>hello from upstream</p></body></html>\n")
GZIP_HTML = (b"<!DOCTYPE html><html><head><title>Gzip Page</title></head>\n"
             b"<body><h1>gzip demo</h1><p>token=super-secret-token</p></body></html>\n")
LOGIN_HTML = b"<html><head><title>Login</title></head><body><form></form></body></html>"


class OriginHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            sys.stderr.write("  [origin] " + (fmt % args) + "\n")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/users":
            self._send(200, USERS_JSON, {"Content-Type": "application/json"})
        elif path == "/api/old":
            self._send(200, b'{"version":"old"}', {"Content-Type": "application/json"})
        elif path == "/gzip":
            # 压缩正文：演示"改包前必须先解压"
            self._send(200, GZIP_HTML, {"Content-Type": "text/html; charset=utf-8",
                                        "Content-Encoding": "gzip"})
        elif path == "/login":
            if "next=" in urllib.parse.urlparse(self.path).query:
                self._send(200, LOGIN_HTML, {"Content-Type": "text/html; charset=utf-8"})
            else:
                self._send(302, b"", {"Location": "/login?next=/admin",
                                      "Set-Cookie": "sessionid=upstream-cookie-value"})
        elif path == "/admin":
            self._send(401, b"login required",
                       {"WWW-Authenticate": 'Basic realm="admin"'})
        elif path == "/slow":
            time.sleep(0.5)
            self._send(200, b"slow ok", {"Content-Type": "text/plain"})
        elif path == "/":
            self._send(200, PAGE_HTML, {"Content-Type": "text/html; charset=utf-8",
                                        "Set-Cookie": "sessionid=upstream-cookie-value"})
        else:
            self._send(404, b"not found upstream", {"Content-Type": "text/plain"})

    def _send(self, status, body, extra):
        # /gzip 的 body 需要压缩后再发送
        if extra.get("Content-Encoding") == "gzip" and not body.startswith(b"\x1f\x8b"):
            body = gzip.compress(body)
        self.send_response(status)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_origin(port: int = 0, verbose: bool = False) -> ThreadingHTTPServer:
    """起假上游站点，返回 server（127.0.0.1 硬编码）。"""
    srv = ThreadingHTTPServer(("127.0.0.1", port), OriginHandler)
    srv.daemon_threads = True
    srv.verbose = verbose                      # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ═══════════════════════════════════════════════════════════════
# B. mitmproxy 兼容 shim（注入 sys.modules）
# ═══════════════════════════════════════════════════════════════
class Headers:
    """大小写不敏感、可保留重复头字段的头容器（对齐 mitmproxy 的 http.Headers）。

    为什么不能直接用 dict？
      · HTTP 头不区分大小写，dict 区分；
      · Set-Cookie 等头可以出现多次，dict 会覆盖。
    """

    def __init__(self, items=()):
        self._items: list = []
        for k, v in items:
            self._items.append((str(k), str(v)))

    # ── 读 ──
    def get(self, key, default=None):
        vals = self.get_all(key)
        return ", ".join(vals) if vals else default

    def get_all(self, key):
        lk = key.lower()
        return [v for k, v in self._items if k.lower() == lk]

    def __getitem__(self, key):
        vals = self.get_all(key)
        if not vals:
            raise KeyError(key)
        return ", ".join(vals)

    def __contains__(self, key):
        return bool(self.get_all(key))

    def __iter__(self):
        return iter([k for k, _v in self._items])

    def __len__(self):
        return len(self._items)

    def items(self):
        return list(self._items)

    def keys(self):
        return [k for k, _v in self._items]

    def values(self):
        return [v for _k, v in self._items]

    # ── 写 ──
    def __setitem__(self, key, value):
        self._items = [(k, v) for k, v in self._items if k.lower() != key.lower()]
        self._items.append((key, str(value)))

    def add(self, key, value):
        self._items.append((str(key), str(value)))

    def __delitem__(self, key):
        if not self.get_all(key):
            raise KeyError(key)
        self._items = [(k, v) for k, v in self._items if k.lower() != key.lower()]

    def pop(self, key, default=None):
        vals = self.get_all(key)
        if not vals:
            return default
        del self[key]
        return ", ".join(vals)

    def copy(self):
        return Headers(self._items)

    def __repr__(self):
        return f"Headers({self._items!r})"


def _decode_body(raw: bytes, encoding: str) -> bytes:
    """按 Content-Encoding 解压（gzip/deflate），对齐 mitmproxy 的 .text 语义。"""
    enc = (encoding or "").lower()
    if not raw:
        return b""
    if "gzip" in enc:
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    if "deflate" in enc:
        import zlib
        try:
            return zlib.decompress(raw)
        except zlib.error:
            try:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
            except zlib.error:
                return raw
    if "br" in enc:
        # brotli 需要第三方库；没有就原样返回（并在日志里提示）
        return raw
    return raw


def _encode_body(plain: bytes, encoding: str) -> bytes:
    enc = (encoding or "").lower()
    if "gzip" in enc:
        return gzip.compress(plain)
    if "deflate" in enc:
        import zlib
        return zlib.compress(plain)
    return plain


class Message:
    """Request / Response 的公共父类：body 的读写与 Content-Length 维护。"""

    def __init__(self, headers=None, content: bytes = b""):
        self.headers = headers if isinstance(headers, Headers) else Headers(headers or [])
        self._plain: bytes | None = None       # 解压后的明文（懒计算）
        self._encoded: bytes = content or b""  # 线上实际传输的字节
        self._tainted = False                  # 是否被 addon 改过

    # ── .content：原始（可能是压缩的）字节 ──
    @property
    def content(self) -> bytes:
        return self._encoded

    @content.setter
    def content(self, value: bytes):
        self._encoded = bytes(value)
        self._plain = None
        self._tainted = True
        self._fix_content_length()

    # ── .text：自动解压 + 解码（mitmproxy 的核心便利） ──
    @property
    def text(self) -> str:
        if self._plain is None:
            self._plain = _decode_body(self._encoded,
                                       self.headers.get("Content-Encoding", ""))
        return self._plain.decode(self._charset(), "replace")

    @text.setter
    def text(self, value: str):
        raw = value.encode(self._charset())
        self._plain = raw
        # 关键：按原来的 Content-Encoding 重新压缩回去，避免"压缩体里塞明文"
        self._encoded = _encode_body(raw, self.headers.get("Content-Encoding", ""))
        self._tainted = True
        self._fix_content_length()

    @property
    def raw_content(self) -> bytes:            # mitmproxy 里 raw_content = 未解码的原文
        return self._encoded if self._tainted else _decode_body(
            self._encoded, self.headers.get("Content-Encoding", ""))

    def _charset(self) -> str:
        ctype = self.headers.get("Content-Type", "") or ""
        if "charset=" in ctype:
            return ctype.split("charset=")[-1].split(";")[0].strip() or "utf-8"
        return "utf-8"

    def _fix_content_length(self):
        """改写 body 后**必须**重算长度（这就是"坑 1"的正解）。

        mitmproxy 自动做这件事，所以我们这里也自动做 —— 这样你在 shim 下
        写同样的 Addon，行为与真 mitmproxy 一致。
        同时把 Transfer-Encoding 去掉：长度已知就不该再分块。
        """
        self.headers["Content-Length"] = str(len(self._encoded))
        if "Transfer-Encoding" in self.headers:
            del self.headers["Transfer-Encoding"]

    def json(self):
        """对齐 mitmproxy：`flow.request.json()` 是**方法**，不是属性。

        ⚠️ 常见错误是写 `flow.request.json`（忘了括号）→ 拿到一个方法对象，
           再对它取 ["key"] 会报 TypeError。mitmproxy 文档里就是带括号的。
        """
        return json.loads(self.text)

    def set_json(self, value):
        """写 JSON 体（mitmproxy 用 `flow.request.set_json(...)` 或直接赋值 .text）。"""
        self.text = json.dumps(value, ensure_ascii=False)
        self.headers["Content-Type"] = "application/json"

    def get_text(self, strict: bool = False) -> str:
        return self.text

    def set_text(self, value: str):
        self.text = value

    def __repr__(self):
        return f"{type(self).__name__}({len(self._encoded)}B)"


class Request(Message):
    def __init__(self, method="GET", scheme="http", host="", port=80, path="/",
                 http_version="HTTP/1.1", headers=None, content=b"", client_addr=None):
        super().__init__(headers, content)
        self.method = method
        self.scheme = scheme
        self.host = host
        self.port = port
        self.path = path
        self.http_version = http_version
        self.client_addr = client_addr

    @property
    def host_header(self) -> str:
        return self.headers.get("Host", f"{self.host}:{self.port}")

    @property
    def url(self) -> str:
        default_port = 80 if self.scheme == "http" else 443
        netloc = self.host if self.port == default_port else f"{self.host}:{self.port}"
        return f"{self.scheme}://{netloc}{self.path}"

    @url.setter
    def url(self, value: str):
        u = urllib.parse.urlsplit(value)
        self.scheme = u.scheme or "http"
        self.host = u.hostname or self.host
        self.port = u.port or (443 if self.scheme == "https" else 80)
        self.path = u.path + (("?" + u.query) if u.query else "")

    @property
    def pretty_url(self) -> str:
        return self.url

    @property
    def query(self):
        return urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query,
                                     keep_blank_values=True)

    @property
    def cookies(self):
        out = {}
        for pair in (self.headers.get("Cookie") or "").split(";"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                out[k.strip()] = v.strip()
        return out


class Response(Message):
    def __init__(self, status_code=200, reason="OK", headers=None, content=b"",
                 http_version="HTTP/1.1"):
        super().__init__(headers, content)
        self.status_code = status_code
        self.reason = reason
        self.http_version = http_version

    @classmethod
    def make(cls, status_code=200, content=b"", headers=None, **kwargs):
        """对齐 mitmproxy 的 `http.Response.make(200, b"...", {"Header": "v"})`。

        用途：在 `request()` 里直接造一个响应 = mock 后端（不用真发到上游）。
        """
        if isinstance(content, str):
            content = content.encode()
        h = Headers(headers.items() if isinstance(headers, dict) else (headers or []))
        reason = kwargs.get("reason", "OK")
        r = cls(status_code=status_code, reason=reason, headers=h, content=content)
        if "Content-Length" not in h:
            r._fix_content_length()
        return r


class Error:
    """flow.error 的最小实现（字符串化后可读）。"""

    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return f"Error({self.msg!r})"


class HTTPFlow:
    def __init__(self, request: Request):
        self.id = f"flow-{int(time.time() * 1000)}-{id(request) % 9973}"
        self.type = "http"
        self.request = request
        self.response: Response | None = None
        self.error: Error | None = None
        self.metadata: dict = {}
        self.client_conn = types.SimpleNamespace(peername=("127.0.0.1", 0))
        self.server_conn = types.SimpleNamespace(
            address=(request.host, request.port), peername=(request.host, request.port))

    def __repr__(self):
        return f"HTTPFlow({self.request.method} {self.request.path})"


# ── ctx：日志与选项 ──
class _Log:
    """把日志同时写进 records（供 self-test 断言）和 stdout/stderr。"""

    def __init__(self):
        self.records: list = []

    def _emit(self, level, msg):
        line = f"[{level}] {msg}"
        self.records.append((level, msg))
        if _Log.verbose:
            print(line, flush=True)

    def info(self, msg):
        self._emit("info", msg)

    def warn(self, msg):
        self._emit("warn", msg)

    def error(self, msg):
        self._emit("error", msg)

    def debug(self, msg):
        self._emit("debug", msg)


_Log.verbose = True


class _Option:
    def __init__(self, name, typespec, default, help=""):
        self.name = name
        self.typespec = typespec
        self.default = default
        self.help = help
        self.value = default


class _Options(types.SimpleNamespace):
    """简化版 mitmproxy 选项系统：addon 用 loader.add_option 注册，--set 赋值。"""

    def __init__(self):
        super().__init__()
        self._registry: dict = {}

    def register(self, option: _Option):
        self._registry[option.name] = option
        setattr(self, option.name, option.value)
        return option

    def set(self, name, raw_value: str):
        if name not in self._registry:
            return False
        opt = self._registry[name]
        if opt.typespec is bool:
            value = str(raw_value).lower() in ("1", "true", "yes", "on")
        elif opt.typespec is int:
            value = int(raw_value)
        elif opt.typespec is float:
            value = float(raw_value)
        else:
            value = str(raw_value)
        opt.value = value
        setattr(self, name, value)
        return True

    def names(self):
        return list(self._registry)


class _Loader:
    """loader.add_option(...) 的接收方（与 mitmproxy 的签名保持一致）。"""

    def __init__(self, options: _Options):
        self.options = options

    def add_option(self, name, typespec=None, default=None, help="", **kwargs):
        # 兼容两种调用风格：
        #   loader.add_option("a", bool, False, "help")      ← 位置参数（本仓库示例用这种）
        #   loader.add_option(name="a", typespec=bool, ...)  ← 关键字参数（官方文档风格）
        spec = typespec if typespec is not None else kwargs.get("typespec", str)
        dflt = default if default is not None else kwargs.get("default")
        return self.options.register(_Option(name, spec, dflt, help))


def build_mitmproxy_shim():
    """构造 `mitmproxy` / `mitmproxy.http` / `mitmproxy.ctx` 三个模块对象。

    注入 sys.modules 后，Addon 里那句
        `from mitmproxy import ctx, http`
    会成功导入我们的 shim —— 这就是"零改动跑 Addon"的原理。
    """
    http = types.ModuleType("mitmproxy.http")
    http.Headers = Headers
    http.Message = Message
    http.Request = Request
    http.Response = Response
    http.HTTPFlow = HTTPFlow
    http.Error = Error

    ctx = types.ModuleType("mitmproxy.ctx")
    ctx.log = _Log()
    ctx.options = _Options()

    mitmproxy = types.ModuleType("mitmproxy")
    mitmproxy.http = http
    mitmproxy.ctx = ctx

    sys.modules["mitmproxy"] = mitmproxy
    sys.modules["mitmproxy.http"] = http
    sys.modules["mitmproxy.ctx"] = ctx
    return mitmproxy


def install_shim():
    if "mitmproxy" in sys.modules and getattr(sys.modules["mitmproxy"], "_is_shim", False):
        return sys.modules["mitmproxy"]
    mod = build_mitmproxy_shim()
    mod._is_shim = True                        # type: ignore[attr-defined]
    return mod


def load_addon(path: str, options: dict | None = None):
    """按路径加载 Addon 文件，返回 (addon 实例列表, 模块)。

    步骤与真实 mitmdump 一致：
      install_shim() → 按路径 exec 模块 → 读模块级 `addons` 列表 →
      调用 load(loader)（注册选项）→ --set 赋值 → configure(updated) → running()
    """
    install_shim()
    from mitmproxy import ctx                    # 拿 shim 里的 ctx
    spec = importlib.util.spec_from_file_location("day155_addon", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                 # type: ignore[union-attr]
    addons = list(getattr(mod, "addons", []))
    if not addons:
        raise SystemExit(f"{path} 里没有模块级 `addons = [...]` 列表")

    loader = _Loader(ctx.options)
    for a in addons:
        if hasattr(a, "load"):
            a.load(loader)

    changed = set()
    for k, v in (options or {}).items():
        if ctx.options.set(k, v):
            changed.add(k)
    # 简化：启动时把所有已注册选项都视为 changed（真 mitmproxy 只报变化的项）
    changed |= set(ctx.options.names())

    for a in addons:
        if hasattr(a, "configure"):
            a.configure(changed)
        if hasattr(a, "running"):
            a.running()
    return addons, mod


def run_addon_event(addons, event: str, flow):
    """按顺序把事件分发给所有 addon（真 mitmproxy 也是这个顺序语义）。"""
    for a in addons:
        fn = getattr(a, event, None)
        if fn is not None:
            fn(flow)


def addon_done(addons):
    for a in addons:
        fn = getattr(a, "done", None)
        if fn is not None:
            fn()


# ═══════════════════════════════════════════════════════════════
# C. MiniProxy：真正的 HTTP 正向代理
# ═══════════════════════════════════════════════════════════════
class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "MiniProxy"

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            sys.stderr.write("  [proxy] " + (fmt % args) + "\n")

    # ── 请求入口 ──
    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_HEAD(self):
        self._handle("HEAD")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_CONNECT(self):
        """HTTPS 的 CONNECT 隧道。

        真 mitmproxy 在这里做的事是：回 `200 Connection established`，
        然后**自己扮演服务器**做 TLS 握手（用 CA 现场签发的域名证书），
        再扮演客户端去连真服务器 —— 即"两次 TLS"。
        本实验台没有 CA/证书体系，所以明确拒绝，并告诉你该用真 mitmproxy。
        """
        body = (b"MiniProxy does not implement CONNECT (HTTPS interception).\n"
                b"Use real mitmproxy with a CA certificate for HTTPS.\n")
        self.send_response(501)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str):
        srv = self.server
        addons = getattr(srv, "addons", [])
        raw_line = self.requestline                 # "GET http://host:port/path HTTP/1.1"
        target = urllib.parse.urlsplit(self.path)

        # 正向代理要求请求行里是**绝对 URI**；只有路径说明客户端没配代理
        if not target.scheme:
            body = (b"MiniProxy expects an absolute URI in the request line.\n"
                    b"Set your client proxy to http://127.0.0.1:<port> and request\n"
                    b"  http://127.0.0.1:<origin-port>/api/users\n")
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        host = target.hostname or ""
        port = target.port or (443 if target.scheme == "https" else 80)
        path = target.path + (("?" + target.query) if target.query else "")

        # 只允许连本机上游（防止实验台被当成任意转发器）
        if host.lower() not in ALLOWED_UPSTREAM:
            body = (f"MiniProxy refuses upstream {host!r}: only "
                    f"{sorted(ALLOWED_UPSTREAM)} are allowed.\n").encode()
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # 读请求体
        length = self.headers.get("Content-Length")
        req_body = self.rfile.read(int(length)) if length else b""
        if self.headers.get("Transfer-Encoding", "").lower() == "chunked":
            req_body = self._read_chunked()

        # ── 组装 flow（与 mitmproxy 的对象结构一致）──
        req_headers = Headers([(k, v) for k, v in self.headers.items()])
        flow = HTTPFlow(Request(method=method, scheme=target.scheme, host=host, port=port,
                                path=path, http_version=self.request_version,
                                headers=req_headers, content=req_body,
                                client_addr=self.client_address))
        flow.metadata["_started"] = time.time()

        # ── ① 请求事件：addon 可以改请求，也可以直接 mock 出响应 ──
        run_addon_event(addons, "request", flow)

        if flow.response is not None:
            # addon 自己造了响应 → 不发到上游（坑 6 的正确姿势）
            self._relay(flow, note="mocked by addon")
            return

        # ── ② 转发到上游 ──
        try:
            resp = self._forward(flow, host, port)
        except Exception as e:                      # 连接失败/超时…
            flow.error = Error(f"{type(e).__name__}: {e}")
            run_addon_event(addons, "error", flow)
            self._send_own(502, f"upstream error: {flow.error}".encode(),
                           {"Content-Type": "text/plain; charset=utf-8"})
            return

        flow.response = resp
        flow.server_conn.peername = (host, port)

        # ── ③ 响应事件：addon 改响应之后才回给客户端 ──
        run_addon_event(addons, "response", flow)

        self._relay(flow, note="proxied")

    # ── 上游转发 ──
    def _forward(self, flow: HTTPFlow, host: str, port: int) -> Response:
        conn = HTTPConnection(host, port, timeout=10)
        try:
            # 去掉 hop-by-hop 头（RFC 7230 §6.1）：这些头只对"单段连接"有意义
            fwd_headers = {k: v for k, v in flow.request.headers.items()
                           if k.lower() not in HOP_BY_HOP}
            fwd_headers["Host"] = flow.request.host_header
            conn.request(flow.request.method, flow.request.path,
                         body=flow.request.content or None, headers=fwd_headers)
            raw = conn.getresponse()
            body = raw.read()
            # getheaders() 会保留重复头（Set-Cookie），不能用 dict
            resp = Response(status_code=raw.status, reason=raw.reason,
                            headers=Headers([(k, v) for k, v in raw.getheaders()]),
                            content=body, http_version=f"HTTP/{raw.version // 10}")
            return resp
        finally:
            conn.close()

    def _read_chunked(self) -> bytes:
        """最小 chunked 解码（只够本实验台用）。

        chunked 的形态是：`<十六进制长度>\r\n<数据>\r\n` 重复，最后 `0\r\n\r\n` 结束。
        真 mitmproxy 会把 body 完整读进来再交给 addon，所以我们也读完整。
        ⚠️ 生产代理必须支持"边读边转发"，否则大文件上传会爆内存。
        """
        out = bytearray()
        while True:
            size_line = self.rfile.readline().strip()
            if not size_line:
                break
            try:
                size = int(size_line.split(b";")[0], 16)
            except ValueError:
                break
            if size == 0:
                self.rfile.readline()          # 吃掉结尾的 CRLF
                break
            out += self.rfile.read(size)
            self.rfile.readline()              # 吃掉每个 chunk 后的 CRLF
        return bytes(out)

    # ── 把 flow.response 回给客户端 ──
    def _relay(self, flow: HTTPFlow, note: str = ""):
        """把 flow.response 回给客户端。

        ⚠️ 用 `send_response_only` 而不是 `send_response`：
          后者会自动再加一对 `Server` / `Date` 头，而上游响应里**本来就有**，
          结果客户端收到重复头（curl 能忍，严格的客户端/中间件会出问题）。
          代理的正确做法是"原样转发上游的头，缺什么补什么"。
        """
        r = flow.response
        # hop-by-hop 头不转发
        headers = [(k, v) for k, v in r.headers.items()
                   if k.lower() not in HOP_BY_HOP]
        names = {k.lower() for k, _v in headers}
        body = r.content

        self.send_response_only(r.status_code, r.reason)
        if getattr(self.server, "verbose", False):
            self.log_request(r.status_code, len(body))
        for k, v in headers:
            # Content-Length 由我们统一重算（addon 改过 body 也不会协议错乱）
            if k.lower() == "content-length":
                continue
            self.send_header(k, v)
        if "server" not in names:                  # 上游没给就补一个
            self.send_header("Server", self.version_string())
        if "date" not in names:
            self.send_header("Date", self.date_time_string())
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-MiniProxy", note)
        self.end_headers()
        if flow.request.method != "HEAD" and body:
            self.wfile.write(body)

    def _send_own(self, status, body, extra):
        self.send_response(status)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MiniProxy(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port=0, addons=None, verbose=False):
        super().__init__(("127.0.0.1", port), ProxyHandler)   # 硬编码回环
        self.addons = addons or []
        self.verbose = verbose


def start_proxy(port: int = 0, addons=None, verbose: bool = False) -> MiniProxy:
    srv = MiniProxy(port, addons, verbose)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ═══════════════════════════════════════════════════════════════
# D. 客户端工具（走代理发请求，纯标准库）
# ═══════════════════════════════════════════════════════════════
def proxy_get(url: str, proxy_port: int, timeout: float = 10.0, method: str = "GET",
              data: bytes = None, extra_headers: dict = None):
    """通过 MiniProxy 发一个请求，返回 (status, headers dict, body, elapsed_ms)。

    实现要点：`urllib.request.ProxyHandler` 会为 http 请求写**绝对 URI** 的请求行，
    这正是正向代理协议的形态；重定向用 NoRedirect 处理，避免被自动跟随。
    """

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    proxy = f"http://127.0.0.1:{proxy_port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy}),
                                         NoRedirect)
    req = urllib.request.Request(url, data=data, method=method,
                                headers=dict(extra_headers or {}))
    t0 = time.time()
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, dict(r.headers.items()), r.read(), (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers.items()), e.read(), (time.time() - t0) * 1000


# ═══════════════════════════════════════════════════════════════
# E. 离线自检
# ═══════════════════════════════════════════════════════════════
class SelfTest:
    def __init__(self, title):
        self.failures = 0
        self.total = 0
        print("=" * 70)
        print(f"{title}（离线自检，不联网）")
        print("=" * 70)

    def check(self, name, actual, expected):
        self.total += 1
        if actual == expected:
            print(f"✅ {name}: {actual!r}")
        else:
            self.failures += 1
            print(f"❌ {name}\n     实际值: {actual!r}\n     期望值: {expected!r}")

    def truthy(self, name, actual):
        self.total += 1
        if actual:
            print(f"✅ {name}")
        else:
            self.failures += 1
            print(f"❌ {name} → 期望真值，实际 {actual!r}")

    def finish(self):
        print("-" * 70)
        if self.failures:
            print(f"❌ {self.failures}/{self.total} 项断言失败")
            return 1
        print(f"✅ 全部 {self.total} 项断言通过")
        print("SELF-TEST OK")
        return 0


def self_test(addon_dir=None) -> int:
    t = SelfTest("day-155 本地 MITM 实验台")
    here = addon_dir or __import__("pathlib").Path(__file__).resolve().parent

    # ── 1. shim 的数据结构 ──
    h = Headers([("Content-Type", "text/html"), ("Set-Cookie", "a=1"),
                 ("Set-Cookie", "b=2")])
    t.check("Headers: 大小写不敏感", h.get("content-TYPE"), "text/html")
    t.check("Headers: 保留重复头", h.get_all("Set-Cookie"), ["a=1", "b=2"])
    h["X-New"] = "1"
    t.check("Headers: 写入", h.get("x-new"), "1")
    t.check("Headers: 覆盖同名（大小写无关）", (h.__setitem__("CONTENT-type", "x"),
                                              h.get("content-type"))[1], "x")
    t.check("Headers: pop 返回旧值", h.pop("X-New"), "1")
    t.check("Headers: 删除后不可见", "X-New" in h, False)

    # ── 2. Response.make / Content-Length 自动维护（坑 1、坑 6）──
    r = Response.make(200, b'{"mock":true}', {"Content-Type": "application/json"})
    t.check("Response.make: 状态码", r.status_code, 200)
    t.check("Response.make: 自动补 Content-Length（= 13 字节）",
            r.headers.get("Content-Length"), "13")
    r.text = '{"mock":true,"more":1}'
    t.check("改 .text 后 Content-Length 自动重算",
            r.headers.get("Content-Length"), str(len(r.content)))
    t.check("改 .text 后长度确实变了", len(r.content), 22)

    # ── 3. gzip 语义（坑 2）──
    g = Response(headers=Headers([("Content-Encoding", "gzip"),
                                  ("Content-Type", "text/html")]),
                 content=gzip.compress(b"<p>secret token</p>"))
    t.check("压缩体里搜不到明文", b"secret token" in g.content, False)
    t.truthy(".text 自动解压", "secret token" in g.text)
    g.text = g.text.replace("secret token", "masked")
    t.check("改 .text 后仍保持 Content-Encoding", g.headers.get("Content-Encoding"), "gzip")
    t.truthy("重新压缩后解压可见替换结果",
             b"masked" in gzip.decompress(g.content))
    t.check("Content-Length 与压缩后长度一致",
            g.headers.get("Content-Length"), str(len(g.content)))

    # ── 4. Request 属性 ──
    q = Request(method="GET", host="127.0.0.1", port=8090, path="/api/users?page=2",
                headers=Headers([("Host", "127.0.0.1:8090"), ("Cookie", "sid=abc")]))
    t.check("Request.url", q.url, "http://127.0.0.1:8090/api/users?page=2")
    t.check("Request.pretty_url", q.pretty_url, q.url)
    t.check("Request.query 解析", q.query.get("page"), ["2"])
    t.check("Request.cookies 解析", q.cookies.get("sid"), "abc")
    q.url = "http://127.0.0.1:9999/other"
    t.check("改 .url 会改 host/port/path",
            (q.host, q.port, q.path), ("127.0.0.1", 9999, "/other"))

    # ── 5. 端到端：起上游 + 代理，跑真实请求 ──
    origin = start_origin(0)
    oport = origin.server_address[1]
    proxy = start_proxy(0)
    pport = proxy.server_address[1]
    try:
        st, _h, body, _ms = proxy_get(f"http://127.0.0.1:{oport}/api/users", pport)
        t.check("代理转发：状态码", st, 200)
        t.check("代理转发：正文一致", json.loads(body)["users"][0]["name"], "nina")

        st, h, _b, _ms = proxy_get(f"http://127.0.0.1:{oport}/login", pport)
        t.check("代理转发：302 不被跟随（客户端决定）", st, 302)
        t.check("代理转发：Location 透传", h.get("Location"), "/login?next=/admin")

        # 直连拿不到的"上游错误"路径：连一个不存在的端口
        st, _h, body, _ms = proxy_get("http://127.0.0.1:1/nope", pport)
        t.check("上游不可达 → 502", st, 502)
        t.truthy("502 正文说明原因", b"upstream error" in body)

        # 非本机上游被拒（安全护栏）
        st, _h, _b, _ms = proxy_get("http://example.com/", pport)
        t.check("非白名单上游被拒（403）", st, 403)
    finally:
        proxy.shutdown()
        proxy.server_close()
        origin.shutdown()
        origin.server_close()

    # ── 6. 端到端：加载真实 Addon（01 只读观察器）──
    from pathlib import Path
    a01 = Path(here) / "01-addon-basics.py"
    if a01.exists():
        origin = start_origin(0)
        oport = origin.server_address[1]
        addons, _mod = load_addon(str(a01))
        proxy = start_proxy(0, addons=addons)
        pport = proxy.server_address[1]
        try:
            st, _h, _b, _ms = proxy_get(f"http://127.0.0.1:{oport}/api/users", pport)
            t.check("Addon01：请求仍然被正常转发", st, 200)
            t.check("Addon01：request() 被调用过一次", addons[0].seq, 1)
            # 静态资源被跳过（.js/.css 不计数）
            proxy_get(f"http://127.0.0.1:{oport}/static/a.css", pport)
            t.check("Addon01：静态资源不计数", addons[0].seq, 1)
            # 非白名单主机不计数（走 403 分支，addon 看不到它）
            proxy_get("http://example.com/", pport)
            t.check("Addon01：非白名单主机不计数", addons[0].seq, 1)
        finally:
            addon_done(addons)
            proxy.shutdown()
            proxy.server_close()
            origin.shutdown()
            origin.server_close()

    # ── 7. 端到端：加载 Addon 02（改包 + mock），验证坑 1/2/6/7 的正解 ──
    a02 = Path(here) / "02-addon-pitfalls.py"
    if a02.exists():
        origin = start_origin(0)
        oport = origin.server_address[1]
        addons, _mod = load_addon(str(a02), {"demo_rewrite": "true"})
        t.truthy("Addon02：configure 收到 demo_rewrite 并置位", addons[0].rewrite_enabled)
        proxy = start_proxy(0, addons=addons)
        pport = proxy.server_address[1]
        try:
            # 7.1 mock：/mock/ 前缀直接由 addon 造响应，不上游
            st, h, body, _ms = proxy_get(f"http://127.0.0.1:{oport}/mock/users", pport)
            t.check("Addon02 坑6：mock 响应状态码", st, 200)
            t.check("Addon02 坑6：mock 响应来源标记", json.loads(body)["mock"], True)
            t.check("Addon02 坑6：X-MiniProxy 说明未被上游覆盖",
                    h.get("X-MiniProxy"), "mocked by addon")

            # 7.2 改 URL：/api/old → /api/new（只改 path，不动 host）
            st, _h, body, _ms = proxy_get(f"http://127.0.0.1:{oport}/api/old", pport)
            t.check("Addon02 坑7：改 path 后请求落到上游的 /api/new（上游无此路径 → 404）",
                    st, 404)

            # 7.3 注入 HTML：改 .text 必须重算 Content-Length 且客户端能完整收到
            st, h, body, _ms = proxy_get(f"http://127.0.0.1:{oport}/", pport)
            t.check("Addon02 坑1：注入后状态码不变", st, 200)
            t.truthy("Addon02 坑1：注入内容出现在响应里",
                     b"injected by mitmproxy" in body)
            t.check("Addon02 坑1：Content-Length 与真实 body 长度一致",
                    int(h.get("Content-Length")), len(body))
            t.truthy("Addon02：rewritten 计数增加", addons[0].rewritten >= 1)

            # 7.4 gzip 页面：先在压缩体上解压、替换、再压缩
            st, h, body, _ms = proxy_get(f"http://127.0.0.1:{oport}/gzip", pport)
            t.check("Addon02 坑2：gzip 页面仍返回 200", st, 200)
            t.check("Addon02 坑2：Content-Encoding 保持 gzip",
                    h.get("Content-Encoding"), "gzip")
            plain = gzip.decompress(body)
            t.truthy("Addon02 坑2：gzip 页面上注入成功", b"injected by mitmproxy" in plain)
            t.check("Addon02 坑2：Content-Length 与压缩后长度一致",
                    int(h.get("Content-Length")), len(body))
            # 注意：明文 token 在响应里被注入脚本替换后仍然存在（本 Addon 只注入不脱敏）
            t.truthy("Addon02：脱敏日志里没有明文 token（只统计，不改写敏感值）",
                     "super-secret-token" not in str(
                         [m for _lv, m in _get_log_records() if "请求头" in m]))
        finally:
            addon_done(addons)
            proxy.shutdown()
            proxy.server_close()
            origin.shutdown()
            origin.server_close()

    # ── 8. 端到端：加载 Addon 03（流量落盘 + 脱敏），验证 jsonl 内容 ──
    a03 = Path(here) / "03-traffic-tool.py"
    if a03.exists():
        import tempfile
        outdir = tempfile.mkdtemp(prefix="day155-lab-traffic-")
        origin = start_origin(0)
        oport = origin.server_address[1]
        addons, _mod = load_addon(str(a03), {"traffic_out_dir": outdir,
                                            "capture_domains": "127.0.0.1"})
        proxy = start_proxy(0, addons=addons)
        pport = proxy.server_address[1]
        try:
            proxy_get(f"http://127.0.0.1:{oport}/api/users", pport,
                      extra_headers={"Authorization": "Bearer supersecrettoken"})
            proxy_get(f"http://127.0.0.1:{oport}/", pport)
            addon_done(addons)               # 触发 done() → 关闭 jsonl 文件
            jl = Path(outdir) / "flows.jsonl"
            t.check("Addon03：flows.jsonl 已生成", jl.exists(), True)
            lines = [json.loads(x) for x in jl.read_text(encoding="utf-8").splitlines() if x]
            t.check("Addon03：捕获到 2 条流量", len(lines), 2)
            t.check("Addon03：Authorization 已脱敏", lines[0]["request"]["headers"]
                    .get("Authorization"), "***")
            t.check("Addon03：路径被记录", lines[0]["request"]["path"], "/api/users")
            t.truthy("Addon03：jsonl 里没有明文凭据",
                     "supersecrettoken" not in jl.read_text(encoding="utf-8"))
        finally:
            proxy.shutdown()
            proxy.server_close()
            origin.shutdown()
            origin.server_close()

    return t.finish()


def _get_log_records():
    from mitmproxy import ctx
    return ctx.log.records


# ═══════════════════════════════════════════════════════════════
# F. CLI
# ═══════════════════════════════════════════════════════════════
def main() -> int:
    ap = argparse.ArgumentParser(description="Day155 本地 MITM 实验台（纯标准库）")
    ap.add_argument("--port", type=int, default=0, help="代理监听端口（0=自动分配）")
    ap.add_argument("--origin-port", type=int, default=0, help="上游站点端口（0=自动）")
    ap.add_argument("--addon", default=None, help="要加载的 Addon 文件路径")
    ap.add_argument("--set", action="append", default=[], metavar="K=V",
                    help="传给 Addon 的选项，可重复")
    ap.add_argument("--quiet", action="store_true", help="不打印 addon 日志")
    ap.add_argument("--verbose", action="store_true", help="打印每个请求的访问日志")
    ap.add_argument("--self-test", action="store_true", help="离线自检后退出")
    args = ap.parse_args()

    if args.self_test:
        _Log.verbose = False                  # 自检时安静一点（断言才是重点）
        return self_test()

    _Log.verbose = not args.quiet
    options = {}
    for kv in args.set:
        if "=" not in kv:
            print(f"⚠️ 忽略无法解析的 --set {kv!r}（应为 K=V）")
            continue
        k, v = kv.split("=", 1)
        options[k.strip()] = v

    origin = start_origin(args.origin_port, verbose=args.verbose)
    oport = origin.server_address[1]

    addons = []
    if args.addon:
        addons, _mod = load_addon(args.addon, options)
        print(f"✅ 已加载 Addon: {args.addon}（{len(addons)} 个实例）"
              f"{'  选项: ' + str(options) if options else ''}")
    else:
        print("ℹ️ 未加载 Addon（只起纯代理，用于对比'不拦截'时的行为）")

    proxy = start_proxy(args.port, addons=addons, verbose=args.verbose)
    pport = proxy.server_address[1]

    print("=" * 70)
    print(f"🎯 上游站点: http://127.0.0.1:{oport}")
    print(f"🎯 正向代理: http://127.0.0.1:{pport}")
    print("=" * 70)
    print("用 curl 走代理（-x 指定代理）：")
    print(f"  curl -x http://127.0.0.1:{pport} http://127.0.0.1:{oport}/api/users")
    print(f"  curl -x http://127.0.0.1:{pport} -i http://127.0.0.1:{oport}/login")
    print(f"  curl -x http://127.0.0.1:{pport} http://127.0.0.1:{oport}/gzip | gunzip")
    print(f"  curl -x http://127.0.0.1:{pport} http://127.0.0.1:{oport}/mock/users")
    print("或用 Python：")
    print("  import urllib.request")
    print(f"  opener = urllib.request.build_opener(urllib.request.ProxyHandler({{'http': 'http://127.0.0.1:{pport}'}}))")
    print(f"  print(opener.open('http://127.0.0.1:{oport}/api/users').read().decode())")
    print()
    print("⚠️ 本实验台只支持明文 HTTP。HTTPS（CONNECT 隧道）需要用真 mitmproxy：")
    print("     pip install mitmproxy")
    print(f"     mitmdump -s {args.addon or 'code/01-addon-basics.py'} -p 8080")
    print("Ctrl-C 停止。")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止。")
    finally:
        if addons:
            addon_done(addons)
        proxy.shutdown()
        proxy.server_close()
        origin.shutdown()
        origin.server_close()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
