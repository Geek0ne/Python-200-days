#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 00 —— 本地回环靶场（纯标准库，用来复现所有扫描场景）
==================================================================

为什么需要这个文件？
--------------------
学习目录扫描/指纹识别时，最大的障碍是「没有可复现的靶场」：
  · DVWA / VulnHub 要下载、要 Docker、要授权；
  · 拿真实网站练手 = 违法。

所以本文件用 **Python 标准库 http.server** 在 127.0.0.1 上起一个
「行为受控的恶意站点模拟器」，把真实世界会让扫描器翻车的行为全部复现：

  1. 软 404（soft 404）：不存在的路径返回 200 + 自定义 404 页面，
     且页面里带**每次都在变的计数器**（把「只看状态码」和「只看长度」
     两种错误做法都打脸）；
  2. 通配路由（wildcard）：任何路径都返回首页 200（SPA try_files 效果）；
  3. `/admin` → 301 `/admin/`、`/admin/` → 401、`/secret/` → 403
     （"存在但受限"的三种典型）；
  4. `/login` → 302 `/login?next=/admin/`（未登录跳转）；
  5. `Server: nginx/1.24.0` + `X-Powered-By: PHP/8.1.2` + `PHPSESSID`
     （指纹识别素材，故意暴露版本号，方便演示"信息泄露"）；
  6. `/gzip` 返回 gzip 压缩正文（演示"压缩体不能直接字符串替换"）；
  7. `/slow` 故意慢 0.2s（演示超时与并发收益）；
  8. 可选限流：超过 N 个请求就返回 429 + `Retry-After`（演示退避）；
  9. 故意放几个"危险文件"：`/.env`（200）、`/.git/HEAD`（403）、
     `/actuator/env`（200）——用来演示"高价值发现"。

运行：
    # 默认：8080 端口，软 404 模式（推荐先跑这个）
    python3 days/day-154-directory-scan-fingerprint/code/00-local-lab.py

    # 换端口 / 换模式
    python3 .../00-local-lab.py --port 9000 --mode strict404
    python3 .../00-local-lab.py --mode wildcard       # 通配路由（SPA 场景）
    python3 .../00-local-lab.py --rate-limit 5        # 第 6 个请求起返回 429

    # 离线自检（起临时端口，跑完自动关；不联网、不写仓库文件）
    python3 .../00-local-lab.py --self-test

⚠️ 安全设计（请阅读，这是"工具"和"玩具"的区别）
------------------------------------------------
  · 只绑定 127.0.0.1：代码里硬编码 host="127.0.0.1"，**没有**参数能改成
    0.0.0.0。这样即使误运行，局域网内其他人也无法访问；
  · 所有响应内容都是**写死的常量**，不读取本机任何文件、不执行任何系统命令；
  · 不写任何文件到磁盘（所以不会污染 git 工作树）；
  · 只用于教学演示：它模拟的是"一个配置有缺陷的站点"，本身不含漏洞利用。
"""

from __future__ import annotations

import argparse
import gzip
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ─────────────────────────────────────────────────────────────
# 0. 靶场配置
# ─────────────────────────────────────────────────────────────
# 三种 404 策略，对应真实世界三种站点配置：
#   soft404    → nginx 自定义 404 页面被写成 200（很多老站）
#   strict404  → 规范做法，不存在就是 404
#   wildcard   → SPA 的 try_files $uri /index.html，任何路径都 200 返回首页
MODES = ("soft404", "strict404", "wildcard")

# 故意暴露的指纹素材。
# 思考：如果你是运维，这里应该写成什么？→ 见 README「防护/修复原理」章节。
SERVER_HEADER = "nginx/1.24.0"
POWERED_BY = "PHP/8.1.2"

# 首页：带 <title> 和 Google 风格的 generator meta，供被动指纹识别
HOME_HTML = b"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Demo Shop \xe9\xa6\x96\xe9\xa1\xb5</title>
  <meta name="generator" content="WordPress 6.4.2">
  <link rel="stylesheet" href="/static/app.css?v=3">
</head>
<body>
  <h1>Demo Shop</h1>
  <p>\xe8\xbf\x99\xe6\x98\xaf\xe4\xb8\x80\xe4\xb8\xaa\xe7\x94\xa8\xe6\x9d\xa5\xe6\xbc\x94\xe7\xa4\xba\xe6\x8c\x87\xe7\xba\xb9\xe8\xaf\x86\xe5\x88\xab\xe7\x9a\x84\xe6\x9c\xac\xe5\x9c\xb0\xe9\x9d\xb6\xe5\x9c\xba\xe3\x80\x82</p>
  <script src="/static/app.js"></script>
</body>
</html>
"""

# favicon.ico：固定字节（真实 ICO 头 + 填充），保证多次请求哈希一致。
# 前 4 字节 00 00 01 00 是 ICO 魔数，6 字节后是目录项，后面是"图像数据"。
FAVICON = (b"\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x20\x00\x68\x04"
           b"\x00\x00\x16\x00\x00\x00" + bytes(range(256)) * 3)

GZIP_HTML = (b"<!DOCTYPE html><html><head><title>Gzip Demo</title></head>"
             b"<body><p>gzip body: MUST decompress before replace</p></body></html>")


def soft404_body(hits: int) -> bytes:
    """软 404 页面。

    ⚠️ 关键设计：正文里带 `hits={hits}` 计数器，**每次请求都不一样**。
    这样可以让三种错误做法同时翻车：
      · 只看状态码   → 200 全都"命中"（100% 误报）
      · 只比原始哈希 → 每次都不同，还是"命中"
      · 只比长度(严格等长) → hits 从 9 变 10 时长度 +1，也判成"命中"
    而正确做法（数字归一化后比对哈希）能把它们全部识破。
    """
    return (b"<!DOCTYPE html>\n<html><head><title>404 Not Found</title></head>\n"
            b"<body><h1>404 Not Found</h1>\n"
            b"<p>The page you requested does not exist.</p>\n"
            b"<p>hits=" + str(hits).encode() + b"</p>\n"
            b"</body></html>\n")


LOGIN_HTML = b"""<!DOCTYPE html>
<html><head><title>Login</title></head>
<body><h1>Login</h1><form method="post" action="/login">
<input name="user"><input name="pass" type="password"></form></body></html>
"""


def rate_limited_body() -> bytes:
    return b"too many requests, slow down"


# ─────────────────────────────────────────────────────────────
# 1. 靶场状态（放在 server 实例上，每个服务实例独立）
# ─────────────────────────────────────────────────────────────
class LabState:
    def __init__(self, mode: str = "soft404", rate_limit: int = 0,
                 slow_delay: float = 0.2):
        assert mode in MODES, mode
        self.mode = mode
        self.rate_limit = rate_limit          # 0 = 不限流
        self.slow_delay = slow_delay
        self.lock = threading.Lock()
        self.hits = 0                          # 软 404 计数器（每次 +1）
        self.requests = 0                      # 全站请求计数（限流用）
        self.started = time.time()

    def bump(self) -> tuple:
        """返回 (软404计数, 全站请求序号)，线程安全。"""
        with self.lock:
            self.hits += 1
            self.requests += 1
            return self.hits, self.requests


# ─────────────────────────────────────────────────────────────
# 2. 路由表：真实世界里 "一个配置有缺陷的站点" 长什么样
# ─────────────────────────────────────────────────────────────
# 精确匹配的路由 → (状态码, 正文 bytes, 额外响应头 dict)
def build_routes(state: LabState) -> dict:
    return {
        "/": (200, HOME_HTML, {"Content-Type": "text/html; charset=utf-8"}),
        "/index.html": (200, HOME_HTML, {"Content-Type": "text/html; charset=utf-8"}),
        # 目录不带斜杠 → 301 补斜杠（nginx 默认行为）
        "/admin": (301, b"", {"Location": "/admin/"}),
        # 目录存在但需要登录 → 401 + WWW-Authenticate
        "/admin/": (401, b"login required",
                    {"WWW-Authenticate": 'Basic realm="admin"'}),
        # 存在但被规则禁止 → 403（对扫描器是"强线索"）
        "/secret/": (403, b"forbidden by rule", {}),
        "/secret": (301, b"", {"Location": "/secret/"}),
        # 未登录跳转 → 302（allow_redirects=True 会把这条信息吞掉）
        "/login": (302, b"", {"Location": "/login?next=/admin/"}),
        "/logout": (302, b"", {"Location": "/login"}),
        # 正常 API
        "/api/v1": (200, b'{"version":"v1","users":42}',
                    {"Content-Type": "application/json"}),
        "/api/v2": (200, b'{"version":"v2","users":43}',
                    {"Content-Type": "application/json"}),
        "/api/old": (200, b'{"version":"old"}', {"Content-Type": "application/json"}),
        # 静态资源（带 query 也要能命中）
        "/static/app.js": (200, b"console.log('app');",
                           {"Content-Type": "application/javascript"}),
        "/static/app.css": (200, b"body{color:#333}",
                            {"Content-Type": "text/css"}),
        # 站点常规文件
        "/robots.txt": (200, b"User-agent: *\nDisallow: /admin/\nDisallow: /secret/\n",
                        {"Content-Type": "text/plain"}),
        "/sitemap.xml": (200, b"<?xml version='1.0'?><urlset></urlset>",
                         {"Content-Type": "application/xml"}),
        "/favicon.ico": (200, FAVICON, {"Content-Type": "image/x-icon"}),
        # gzip 压缩正文：改包/替换前必须先解压
        "/gzip": (200, gzip.compress(GZIP_HTML),
                  {"Content-Type": "text/html; charset=utf-8",
                   "Content-Encoding": "gzip"}),
        # 慢接口：用来演示超时设置与并发收益
        "/slow": (200, b"slow but ok", {"Content-Type": "text/plain"}),
        # ── 故意配置错误的"危险文件"（演示高价值发现）──
        "/.env": (200, b"APP_ENV=demo\nDB_USER=demo\nDB_PASSWORD=***masked***\n",
                  {"Content-Type": "text/plain"}),
        "/.git/HEAD": (403, b"forbidden", {}),
        "/actuator/env": (200, b'{"activeProfiles":["demo"]}',
                          {"Content-Type": "application/json"}),
        "/server-status": (403, b"forbidden", {}),
        # 默认 404（严格模式下生效）
        "/phpinfo.php": (404, b"not found", {}),
    }


# ─────────────────────────────────────────────────────────────
# 3. HTTP 处理器
# ─────────────────────────────────────────────────────────────
class LabHandler(BaseHTTPRequestHandler):
    # HTTP/1.1 + 正确的 Content-Length = 支持 keep-alive 连接复用，
    # 这样 01/03 示例里的 Session 连接池才有意义
    protocol_version = "HTTP/1.1"
    server_version = "LabOrigin"
    sys_version = ""

    def version_string(self) -> str:
        """http.server 会自动把 `Server` 头塞进每个响应（值来自 version_string()）。

        这里直接让它返回我们想要的假 banner `nginx/1.24.0`——
        顺便说明一个真实世界的事实：**`Server` 头完全由服务端自己填**，
        想写什么就写什么。所以"看到 nginx 就认定是 nginx"并不可靠，
        指纹识别必须做**多证据交叉验证**（见 README 第 2.6 节）。
        """
        return SERVER_HEADER

    # 关掉默认的 stderr 每请求日志，避免把扫描输出淹没（想看日志加 --verbose）
    verbose = False

    def log_message(self, fmt, *args):      # noqa: D102
        if self.verbose:
            sys.stderr.write("  [lab] %s - %s\n" % (self.address_string(), fmt % args))

    # ── 统一入口 ──
    def do_GET(self):
        self._handle("GET")

    def do_HEAD(self):
        self._handle("HEAD")

    def do_POST(self):
        # 读者练习：给 /api/* 加上 POST 支持。当前只回 405，
        # 顺便演示"405 也说明资源存在"这一点。
        self._send(405, b"method not allowed", {"Allow": "GET, HEAD"})

    def _handle(self, method: str):
        st: LabState = self.server.state          # type: ignore[attr-defined]
        hits, seq = st.bump()

        # ① 限流：注意它发生在路由之前，且与"资源是否存在"无关
        if st.rate_limit and seq > st.rate_limit:
            body = rate_limited_body()
            self._send(429, body, {"Content-Type": "text/plain",
                                   "Retry-After": "1"}, method=method)
            return

        parsed = urlparse(self.path)
        path = parsed.path                        # 丢掉 query，只看路径
        query = parsed.query
        # ② 慢接口
        if path == "/slow":
            time.sleep(st.slow_delay)

        # ③ 未登录跳转：没有 next 参数 → 302 到登录页；已经带上 next → 渲染登录页。
        #    之所以这样设计，是为了让"跟随重定向"的演示能收敛（否则会无限循环）。
        #    真实世界里这个循环同样存在，只是浏览器/库会自己停下来并报
        #    TooManyRedirects —— 这也是扫描器必须 allow_redirects=False 的原因之一。
        if path == "/login" and "next=" in query:
            self._send(200, LOGIN_HTML,
                       {"Content-Type": "text/html; charset=utf-8"}, method=method)
            return

        routes = build_routes(st)
        if path in routes:
            status, body, extra = routes[path]
            self._send(status, body, extra, method=method)
            return

        # ③ 未知路径：按模式决定行为
        if st.mode == "strict404":
            self._send(404, b"<html><title>404 Not Found</title></html>",
                       {"Content-Type": "text/html; charset=utf-8"}, method=method)
        elif st.mode == "wildcard":
            # SPA 行为：任何路径都返回首页（try_files $uri /index.html）
            self._send(200, HOME_HTML,
                       {"Content-Type": "text/html; charset=utf-8"}, method=method)
        else:                                     # soft404
            self._send(200, soft404_body(hits),
                       {"Content-Type": "text/html; charset=utf-8"}, method=method)

    def _send(self, status: int, body: bytes, extra: dict, method: str = "GET"):
        self.send_response(status)     # ← Server 头由 version_string() 提供
        # 指纹素材：故意暴露版本号（真实站点应该删除，见 README 防御章节）
        self.send_header("X-Powered-By", POWERED_BY)
        # 会话 Cookie：Cookie 名本身就是指纹（PHPSESSID → PHP）
        self.send_header("Set-Cookie", "PHPSESSID=demo1234567890; Path=/")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        # Content-Length 必须精确等于实际发送的字节数：
        # 写成 len(body) 而不是 len(body.decode(...))，避免中文/二进制长度算错
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if method != "HEAD" and body:
            self.wfile.write(body)


# ─────────────────────────────────────────────────────────────
# 4. 启动辅助（供 CLI 和 self-test 复用）
# ─────────────────────────────────────────────────────────────
def start_lab(port: int = 0, mode: str = "soft404", rate_limit: int = 0,
              slow_delay: float = 0.2, verbose: bool = False) -> ThreadingHTTPServer:
    """在 127.0.0.1 上起靶场，返回已就绪的 server 对象。

    port=0 表示让操作系统分配空闲端口（self-test 用，避免端口冲突）。
    daemon_threads=True 让 Ctrl-C 能立刻退出，不用等挂起的连接。
    """
    srv = ThreadingHTTPServer(("127.0.0.1", port), LabHandler)  # 硬编码回环！
    srv.daemon_threads = True
    srv.state = LabState(mode=mode, rate_limit=rate_limit, slow_delay=slow_delay)
    LabHandler.verbose = verbose
    t = threading.Thread(target=srv.serve_forever, name="lab", daemon=True)
    t.start()
    return srv


# ─────────────────────────────────────────────────────────────
# 5. 标准库 HTTP 客户端（离线降级路径的核心）
# ─────────────────────────────────────────────────────────────
# 为什么要有这一层？
#   · 本仓库的 01/02/03 示例默认用 requests。如果学习者环境里**没装** requests，
#     示例就跑不起来 —— 这不符合"可复现"要求。
#   · 所以这里提供一个**纯标准库**（urllib）的等价实现，接口刻意与 requests
#     保持兼容（`.get(url, timeout=..., allow_redirects=...)`、
#     `r.status_code` / `r.headers.get(...)` / `r.content` / `r.text` / `r.json()`），
#     这样上层扫描代码**一行都不用改**就能在两种后端之间切换。
#   · 它同时是教学材料：你可以亲眼看到 requests 帮你封装了哪些东西
#     （重定向策略、大小写不敏感头、gzip 解压、超时语义）。
# 注意：标准库路径不做连接池复用（urllib 每次请求新建连接），
#   所以它比 requests 慢 —— 这正好解释了"为什么扫描器要用 Session"。
import urllib.error
import urllib.request


class CIHeaders:
    """大小写不敏感的响应头容器（模拟 requests 的 CaseInsensitiveDict）。

    HTTP 规范（RFC 7230 §3.2）明确规定头字段名**不区分大小写**，
    所以必须用 lower() 归一化后再存；否则 `r.headers["Server"]` 会 KeyError。
    另外提供 `get_all()`：Set-Cookie 这类头**可以出现多次**，
    用 dict 取值会被覆盖，必须能拿到列表。
    """

    def __init__(self, items=()):
        self._d: dict = {}          # lower_key -> [orig_key, [values...]]
        for k, v in items:
            self.add(k, v)

    def add(self, key: str, value: str) -> None:
        lk = key.lower()
        if lk in self._d:
            self._d[lk][1].append(value)
        else:
            self._d[lk] = [key, [value]]

    def get(self, key: str, default=None):
        hit = self._d.get(key.lower())
        if not hit:
            return default
        # 多值头按 HTTP 惯例用 ", " 连接（和 requests 行为一致）
        return ", ".join(hit[1])

    def get_all(self, key: str) -> list:
        hit = self._d.get(key.lower())
        return list(hit[1]) if hit else []

    def __contains__(self, key) -> bool:
        return key.lower() in self._d

    def __getitem__(self, key):
        v = self.get(key)
        if v is None:
            raise KeyError(key)
        return v

    def items(self):
        for _lk, (orig, values) in self._d.items():
            yield orig, ", ".join(values)

    def keys(self):
        return [orig for _lk, (orig, _v) in self._d.items()]

    def __len__(self):
        return len(self._d)

    def __iter__(self):
        return iter(self.keys())


class StdlibResponse:
    """urllib 响应的适配层，字段名与 requests.Response 对齐。"""

    def __init__(self, status_code: int, headers: CIHeaders, content: bytes,
                 url: str, elapsed: float, history: list = None):
        self.status_code = status_code
        self.headers = headers
        self.content = content            # bytes：算哈希/比长度永远用这个
        self.url = url
        self.elapsed = elapsed            # ⚠️ requests 这里是 timedelta，本实现是秒(float)
        self.history = history or []      # 重定向链

    @property
    def text(self) -> str:
        """按 Content-Encoding 解压 + 按 charset 解码，等价于 requests 的 .text。

        为什么标准库要自己写这一层？
        → urllib **不会**自动解压 gzip/deflate，也不会猜编码。
          直接用 content.decode() 会得到乱码或抛异常 —— 这是"压缩体不能
          直接做字符串替换"那条坑的根源。
        """
        raw = self.content
        enc = (self.headers.get("Content-Encoding") or "").lower()
        if "gzip" in enc:
            raw = gzip.decompress(raw)
        elif "deflate" in enc:
            import zlib
            try:
                raw = zlib.decompress(raw)
            except zlib.error:            # 有些服务器发的是裸 deflate
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        ctype = self.headers.get("Content-Type") or ""
        charset = "utf-8"
        if "charset=" in ctype:
            charset = ctype.split("charset=")[-1].split(";")[0].strip() or "utf-8"
        return raw.decode(charset, "replace")

    def json(self):
        import json as _json
        return _json.loads(self.content.decode("utf-8", "replace"))


class StdlibSession:
    """requests.Session 的最小等价实现（只用标准库）。

    支持：
      · `s.headers.update({...})` 默认请求头
      · `s.get(url, timeout=(3,5), allow_redirects=False)`
      · `with StdlibSession() as s:` 上下文管理
    不支持（教学示例用不到）：连接池、CookieJar 持久化、HTTP/2、代理链。
    """

    def __init__(self, default_headers: dict | None = None):
        self.headers = {"User-Agent": "StdlibSession/1.0"}
        if default_headers:
            self.headers.update(default_headers)
        self._opener = urllib.request.build_opener(_NoRedirectHandler())
        self.closed = False

    def close(self):
        self.closed = True
        self._opener.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    @staticmethod
    def _as_timeout(timeout):
        """requests 的 timeout 是 (连接超时, 读取超时) 元组；
        urllib 只有一个超时旋钮 → 取两者较大者，宁可等久一点也不要误判超时。"""
        if isinstance(timeout, (tuple, list)):
            return max(float(x) for x in timeout)
        return float(timeout) if timeout else 5.0

    def get(self, url, timeout=(3, 5), allow_redirects=False, **kwargs):
        return self.request("GET", url, timeout=timeout,
                            allow_redirects=allow_redirects, **kwargs)

    def head(self, url, timeout=(3, 5), allow_redirects=False, **kwargs):
        return self.request("HEAD", url, timeout=timeout,
                            allow_redirects=allow_redirects, **kwargs)

    def post(self, url, data=None, timeout=(3, 5), allow_redirects=False, **kwargs):
        return self.request("POST", url, data=data, timeout=timeout,
                            allow_redirects=allow_redirects, **kwargs)

    def request(self, method, url, data=None, timeout=(3, 5),
                allow_redirects=False, max_redirects=10, **kwargs):
        history = []
        cur = url
        for _hop in range(max_redirects + 1):
            t0 = time.time()
            try:
                req = urllib.request.Request(cur, data=data, method=method)
                for k, v in self.headers.items():
                    req.add_header(k, v)
                if data is not None and req.get_header("Content-type") is None:
                    req.add_header("Content-Type", "application/x-www-form-urlencoded")
                with self._opener.open(req, timeout=self._as_timeout(timeout)) as r:
                    resp = StdlibResponse(r.status, CIHeaders(r.headers.items()),
                                          r.read(), cur, time.time() - t0, list(history))
            except urllib.error.HTTPError as e:
                # 4xx/5xx 也会抛异常，但它**是一个正常响应**：状态码/头/正文都在
                resp = StdlibResponse(e.code, CIHeaders(e.headers.items()),
                                      e.read(), cur, time.time() - t0, list(history))
            # 到底要不要跟随跳转？
            if (allow_redirects and resp.status_code in (301, 302, 303, 307, 308)
                    and resp.headers.get("Location")):
                history.append(resp)
                cur = urllib.parse.urljoin(cur, resp.headers.get("Location"))
                continue
            return resp
        raise RuntimeError("重定向次数超过 %d 次" % max_redirects)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """让 urllib **不要**自动跟随 30x。

    这是扫描器最关键的一个细节：默认的 HTTPRedirectHandler 会把 302 悄悄跟到
    登录页，然后给你一个 200 —— 于是"存在但需要登录"的信息彻底丢失。
    requests 的 allow_redirects=False 是同一个道理，只是更显式。
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def http_get(url: str, timeout: float = 5.0) -> tuple:
    """一次性 GET，返回 (status, headers(dict), body(bytes), elapsed_ms)。

    self-test 里大量用到；日常写代码请优先用 StdlibSession（可复用连接）。
    """
    s = StdlibSession()
    try:
        r = s.get(url, timeout=(timeout, timeout), allow_redirects=False)
        return r.status_code, dict(r.headers.items()), r.content, r.elapsed * 1000
    finally:
        s.close()


# ─────────────────────────────────────────────────────────────
# 6. 离线自检
# ─────────────────────────────────────────────────────────────
class SelfTest:
    """极简断言器：失败打印「实际值 vs 期望值」，最后统一返回退出码。"""

    def __init__(self, title: str):
        self.failures = 0
        self.total = 0
        print("=" * 70)
        print(f"{title}（离线自检，不联网）")
        print("=" * 70)

    def check(self, name: str, actual, expected):
        self.total += 1
        if actual == expected:
            print(f"✅ {name}: {actual!r}")
        else:
            self.failures += 1
            print(f"❌ {name}\n     实际值: {actual!r}\n     期望值: {expected!r}")

    def truthy(self, name: str, actual):
        self.total += 1
        if actual:
            print(f"✅ {name}")
        else:
            self.failures += 1
            print(f"❌ {name} → 期望真值，实际 {actual!r}")

    def finish(self) -> int:
        print("-" * 70)
        if self.failures:
            print(f"❌ {self.failures}/{self.total} 项断言失败")
            return 1
        print(f"✅ 全部 {self.total} 项断言通过")
        print("SELF-TEST OK")
        return 0


def self_test() -> int:
    t = SelfTest("day-154 本地靶场")

    # ── 1. 软 404 模式 ──
    srv = start_lab(0, mode="soft404", slow_delay=0.2)
    port = srv.server_address[1]
    base = f"http://127.0.0.1:{port}"
    try:
        st1, h1, b1, _ = http_get(base + "/definitely-not-here-a1")
        t.check("软404模式：未知路径状态码", st1, 200)
        t.truthy("软404模式：正文含 404 标题",
                 b"<title>404 Not Found</title>" in b1)
        t.check("指纹素材：Server 头", h1.get("Server"), SERVER_HEADER)
        t.check("指纹素材：X-Powered-By", h1.get("X-Powered-By"), POWERED_BY)
        t.truthy("指纹素材：PHPSESSID Cookie", "PHPSESSID" in h1.get("Set-Cookie", ""))

        # 计数器让「原始哈希」和「严格等长」同时失效
        st2, _h2, b2, _ = http_get(base + "/definitely-not-here-b2")
        t.truthy("软404页面：原始字节每次都不同（hits 计数器）", b1 != b2)
        t.check("软404页面：hits=1", b"hits=1" in b1, True)
        t.check("软404页面：hits=2", b"hits=2" in b2, True)

        # ── 2. 存在但受限：301 / 401 / 403 ──
        st, h, _b, _ = http_get(base + "/admin")
        t.check("/admin 状态码", st, 301)
        t.check("/admin Location", h.get("Location"), "/admin/")
        st, _h, _b, _ = http_get(base + "/admin/")
        t.check("/admin/ 状态码", st, 401)
        st, _h, _b, _ = http_get(base + "/secret/")
        t.check("/secret/ 状态码", st, 403)
        st, h, _b, _ = http_get(base + "/login")
        t.check("/login 状态码", st, 302)
        t.check("/login Location", h.get("Location"), "/login?next=/admin/")
        st, _h, b, _ = http_get(base + "/login?next=/admin/")
        t.check("/login?next=... 渲染登录页（200）", st, 200)
        t.truthy("登录页含表单", b"<form" in b)
        # 跟随重定向的等效操作：/admin → /admin/ → 401
        st, _h, _b, _ = http_get(base + "/admin/")
        t.check("跟随一次重定向后的最终状态码（401，说明确实存在）", st, 401)

        # ── 3. gzip 正文 ──
        st, h, body, _ = http_get(base + "/gzip")
        t.check("/gzip 状态码", st, 200)
        t.check("/gzip Content-Encoding", h.get("Content-Encoding"), "gzip")
        t.check("gzip 解压后正文一致", gzip.decompress(body), GZIP_HTML)

        # ── 4. favicon 稳定性 ──
        _s, _h, f1, _ = http_get(base + "/favicon.ico")
        _s, _h, f2, _ = http_get(base + "/favicon.ico")
        t.check("favicon 两次请求字节一致", f1 == f2, True)
        t.check("favicon 长度", len(f1), len(FAVICON))

        # ── 5. 慢接口 ──
        _s, _h, _b, ms = http_get(base + "/slow")
        t.truthy(f"慢接口耗时 ≥200ms（实测 {ms:.0f}ms）", ms >= 200)

        # ── 6. 危险文件 ──
        st, _h, b, _ = http_get(base + "/.env")
        t.check("/.env 状态码（高价值发现）", st, 200)
        t.truthy("/.env 正文被脱敏演示", b"DB_PASSWORD" in b)
        st, _h, _b, _ = http_get(base + "/.git/HEAD")
        t.check("/.git/HEAD 状态码", st, 403)
    finally:
        srv.shutdown()
        srv.server_close()

    # ── 7. 严格 404 模式 ──
    srv = start_lab(0, mode="strict404")
    try:
        port = srv.server_address[1]
        st, _h, _b, _ = http_get(f"http://127.0.0.1:{port}/nope-xyz")
        t.check("strict404 模式：未知路径 → 404", st, 404)
    finally:
        srv.shutdown()
        srv.server_close()

    # ── 8. 通配路由模式（SPA）──
    srv = start_lab(0, mode="wildcard")
    try:
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"
        st_a, _h, body_a, _ = http_get(base + "/whatever-a")
        st_b, _h, body_b, _ = http_get(base + "/another/path/b")
        t.check("wildcard 模式：任意路径 200", (st_a, st_b), (200, 200))
        t.check("wildcard 模式：正文与首页完全相同", body_a == body_b == HOME_HTML, True)
    finally:
        srv.shutdown()
        srv.server_close()

    # ── 9. 限流 + Retry-After ──
    srv = start_lab(0, mode="strict404", rate_limit=3)
    try:
        port = srv.server_address[1]
        base = f"http://127.0.0.1:{port}"
        codes = [http_get(base + f"/x{i}")[0] for i in range(5)]
        t.check("限流：前 3 个放行", codes[:3], [404, 404, 404])
        t.check("限流：第 4/5 个返回 429", codes[3:], [429, 429])
        _s, h, _b, _ = http_get(base + "/x9")
        t.check("限流：带 Retry-After", h.get("Retry-After"), "1")
    finally:
        srv.shutdown()
        srv.server_close()

    return t.finish()


# ─────────────────────────────────────────────────────────────
# 7. CLI
# ─────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Day154 本地回环靶场（纯标准库）")
    ap.add_argument("--port", type=int, default=8080, help="监听端口（只绑 127.0.0.1）")
    ap.add_argument("--mode", choices=MODES, default="soft404",
                    help="未知路径的行为：soft404 / strict404 / wildcard")
    ap.add_argument("--rate-limit", type=int, default=0,
                    help="超过 N 个请求后返回 429（0=不限流）")
    ap.add_argument("--slow-delay", type=float, default=0.2, help="/slow 的延迟秒数")
    ap.add_argument("--verbose", action="store_true", help="打印每个请求的访问日志")
    ap.add_argument("--self-test", action="store_true", help="离线自检后退出")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    srv = start_lab(args.port, mode=args.mode, rate_limit=args.rate_limit,
                    slow_delay=args.slow_delay, verbose=args.verbose)
    port = srv.server_address[1]
    print("=" * 70)
    print(f"🎯 本地靶场已启动: http://127.0.0.1:{port}  (mode={args.mode})")
    print("=" * 70)
    print("可用端点：")
    print("  /                    首页（带 WordPress generator meta）")
    print("  /admin → /admin/     301 → 401（存在但需登录）")
    print("  /secret/             403（存在但被规则拒绝）")
    print("  /login               302 → /login?next=/admin/")
    print("  /api/v1  /api/v2     200 JSON")
    print("  /gzip                gzip 压缩正文")
    print("  /slow                延迟返回（默认 0.2s）")
    print("  /.env                🚨 200（演示「危险文件泄露」场景）")
    print("  /.git/HEAD           403")
    print("  <未知路径>           %s" % {
        "soft404": "200 + 自定义 404 页（带 hits 计数器）",
        "strict404": "404",
        "wildcard": "200 + 首页（SPA 通配路由）",
    }[args.mode])
    print()
    print("现在可以另开终端运行：")
    print(f"  python3 code/01-dir-brute-basics.py --url http://127.0.0.1:{port}")
    print(f"  python3 code/02-fingerprint-pitfalls.py --url http://127.0.0.1:{port}")
    print(f"  python3 code/03-asset-discovery.py --url http://127.0.0.1:{port} --out-dir $(mktemp -d)")
    print()
    print("Ctrl-C 停止。")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止靶场。")
    finally:
        srv.shutdown()
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
