#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 03 —— 实战：Web 资产发现与指纹识别工具
=========================================================

把示例 01（并发扫描）和示例 02（软 404 + 指纹）合成一个能用的 CLI 工具。

两种运行方式
------------
方式 A（联机演示：扫自己的站点/靶场）:
    # 1) 起靶场（另一个终端）
    python3 code/00-local-lab.py --port 8080
    # 2) 跑资产发现
    python3 code/03-asset-discovery.py --url http://127.0.0.1:8080
    python3 code/03-asset-discovery.py --url http://127.0.0.1:8080 --workers 5 --delay 0.2
    python3 code/03-asset-discovery.py --url http://127.0.0.1:8080 --wordlist common.txt --out-dir /tmp/out

方式 B（离线自检：完全离线，跑通整条流水线）:
    python3 code/03-asset-discovery.py --self-test

功能：
  1. 软 404 / 通配路由基线探测（自动区分 SPA 通配 vs 自定义 404 页）
  2. 并发目录扫描（线程池 + 全局限速 + 429 指数退避）
  3. Web 指纹识别（响应头 / Cookie / HTML 特征 / 主动探针 / favicon 哈希）
  4. 安全响应头体检（HSTS / CSP / X-Frame-Options …）
  5. 输出 JSON + Markdown 报告

⚠️ 法律边界：非本机目标必须显式 --i-have-authorization。默认严格限速。
⚠️ 本工具只做"发现"，不做任何漏洞利用。
⚠️ 输出目录默认是**系统临时目录**（tempfile.mkdtemp），不会污染仓库工作树。

依赖说明
--------
`requests` / `mmh3` 都是可选的：
  · 没有 requests → 自动用 `00-local-lab.py` 的标准库 urllib 实现；
  · 没有 mmh3     → 自动用内置纯 Python MurmurHash3（结果与 mmh3 一致）。
"""

import argparse
import base64
import concurrent.futures as cf
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── requests：可选 ──
try:
    import requests
    from requests.exceptions import RequestException

    HAVE_REQUESTS = True
    NET_ERRORS = (RequestException,)
except ImportError:                            # pragma: no cover
    requests = None                            # type: ignore[assignment]
    HAVE_REQUESTS = False
    NET_ERRORS = (OSError,)

# ── mmh3：可选 ──
try:
    import mmh3 as _mmh3

    HAVE_MMH3 = True
except ImportError:
    _mmh3 = None
    HAVE_MMH3 = False

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
UA = "OwnedSiteAudit/2.0 (+asset-discovery; self-check only)"

DEFAULT_WORDS = [
    "admin", "administrator", "login", "logout", "dashboard", "panel",
    "api", "api/v1", "api/v2", "graphql", "swagger.json", "openapi.json",
    "docs", "static", "assets", "uploads", "files", "images",
    "backup.zip", "www.zip", "site.tar.gz", ".env", ".git/HEAD", ".git/config",
    ".svn/entries", ".DS_Store", "config.php", "settings.py", "web.config",
    "robots.txt", "sitemap.xml", "favicon.ico", "crossdomain.xml",
    "phpinfo.php", "info.php", "test.php", "debug.log", "error.log",
    "server-status", "actuator", "actuator/health", "actuator/env",
    "wp-login.php", "wp-admin", "xmlrpc.php", "manager/html",
    "console", "jmx-console", "status", "health", "metrics", "version",
]

# ── 指纹库 ──────────────────────────────────────────────────
HEADER_FP = [
    (r"nginx(?:/([\d.]+))?", "nginx"),
    (r"Apache(?:/([\d.]+))?", "Apache httpd"),
    (r"gunicorn(?:/([\d.]+))?", "Gunicorn (Python WSGI)"),
    (r"uvicorn", "Uvicorn (ASGI)"),
    (r"openresty(?:/([\d.]+))?", "OpenResty"),
    (r"Microsoft-IIS/([\d.]+)", "Microsoft IIS"),
    (r"cloudflare", "Cloudflare CDN"),
    (r"Tengine", "Tengine (阿里)"),
    (r"Jetty", "Jetty"),
    (r"Tomcat", "Apache Tomcat"),
    (r"Werkzeug(?:/([\d.]+))?", "Werkzeug (Flask dev server)"),
    (r"Kestrel", "Kestrel (ASP.NET Core)"),
]
XPB_FP = [
    (r"PHP/([\d.]+)", "PHP"),
    (r"ASP\.NET", "ASP.NET"),
    (r"Express", "Express (Node.js)"),
    (r"Servlet/([\d.]+)", "Java Servlet"),
    (r"Next\.js", "Next.js"),
]
COOKIE_FP = {
    "PHPSESSID": "PHP", "JSESSIONID": "Java Servlet", "csrftoken": "Django",
    "django_language": "Django", "sessionid": "Django/通用",
    "laravel_session": "Laravel (PHP)", "connect.sid": "Express (Node.js)",
    "ASP.NET_SessionId": "ASP.NET", "grafana_session": "Grafana",
    "wp-settings": "WordPress", "wordpress_": "WordPress",
    "XSRF-TOKEN": "Laravel/Angular", "ci_session": "CodeIgniter",
    "JSESSIONIDSSO": "Java SSO", "SERVERID": "Java 负载均衡",
}
BODY_FP = [
    (r'name="generator"\s+content="WordPress\s*([\d.]+)"', "WordPress"),
    (r"wp-content/", "WordPress"),
    (r"wp-includes/", "WordPress"),
    (r"/_next/static/", "Next.js"),
    (r"__NEXT_DATA__", "Next.js"),
    (r"/static/js/main\.[0-9a-f]+\.js", "React (CRA)"),
    (r"Drupal\.settings", "Drupal"),
    (r"cdn\.shopify\.com", "Shopify"),
    (r"__VIEWSTATE", "ASP.NET WebForms"),
    (r"Powered by Discuz", "Discuz!"),
    (r"grafana-app", "Grafana"),
]
PROBE_FP = {
    "wp-login.php": "WordPress",
    "administrator/": "Joomla",
    "user/login": "Drupal",
    "actuator/health": "Spring Boot Actuator ⚠️",
    "actuator/env": "Spring Boot Actuator (env 泄露) 🚨",
    ".git/HEAD": "Git 目录泄露 🚨",
    ".env": ".env 文件泄露 🚨",
    "phpinfo.php": "phpinfo 泄露 ⚠️",
    "server-status": "Apache server-status ⚠️",
    "swagger.json": "Swagger/OpenAPI 文档",
    "graphql": "GraphQL 接口",
}
SECURITY_HEADERS = {
    "Strict-Transport-Security": "HSTS（防 SSL 剥离）",
    "Content-Security-Policy": "CSP（XSS 第二道防线）",
    "X-Content-Type-Options": "MIME 嗅探防护",
    "X-Frame-Options": "点击劫持防护",
    "Referrer-Policy": "Referrer 泄露控制",
    "Permissions-Policy": "浏览器特性授权控制",
}

_LAB_CACHE = None


def load_lab():
    """按路径加载同目录 `00-local-lab.py`（标准库 HTTP 客户端 + 回环靶场）。"""
    global _LAB_CACHE
    if _LAB_CACHE is not None:
        return _LAB_CACHE
    path = Path(__file__).resolve().parent / "00-local-lab.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("day154_lab", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)               # type: ignore[union-attr]
    _LAB_CACHE = mod
    return mod


def header_values(resp, name: str) -> list:
    """安全读取"可能出现多次"的响应头（Set-Cookie）。

    ⚠️ 这是一个真实的踩坑点：requests 的 `resp.headers` 是
      `CaseInsensitiveDict`，**没有** `get_all()`。写成
      `hdrs.get_all("Set-Cookie") or []` 在真实环境会抛 AttributeError。
      正确路径：我们的 StdlibResponse 提供 get_all；
      requests 走 `resp.raw.headers.getlist()`；都没有就退回 get()。
    """
    h = resp.headers
    if hasattr(h, "get_all"):
        return h.get_all(name)
    raw_headers = getattr(getattr(resp, "raw", None), "headers", None)
    if raw_headers is not None and hasattr(raw_headers, "getlist"):
        return raw_headers.getlist(name)
    v = h.get(name)
    return [v] if v else []


# ═══════════════════════════════════════════════════════════════
# 纯 Python MurmurHash3 x86_32（mmh3 缺失时的离线降级路径）
# ═══════════════════════════════════════════════════════════════
def murmur3_x86_32(data: bytes, seed: int = 0) -> int:
    """MurmurHash3 x86_32 规范实现；与 mmh3.hash(bytes) 逐位一致。

    favicon 指纹库（Shodan/Fofa）要求哈希严格一致，所以这里不能"近似"：
    32 位溢出必须每一步 & 0xFFFFFFFF，最终结果要转成**有符号**整数。
    """
    c1, c2 = 0xCC9E2D51, 0x1B873593
    length = len(data)
    h1 = seed & 0xFFFFFFFF
    rounded_end = length & 0xFFFFFFFC
    for i in range(0, rounded_end, 4):
        k1 = (data[i] | (data[i + 1] << 8) | (data[i + 2] << 16) | (data[i + 3] << 24))
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
        h1 = ((h1 << 13) | (h1 >> 19)) & 0xFFFFFFFF
        h1 = (h1 * 5 + 0xE6546B64) & 0xFFFFFFFF
    k1 = 0
    tail = length & 0x03
    if tail == 3:
        k1 ^= data[rounded_end + 2] << 16
    if tail >= 2:
        k1 ^= data[rounded_end + 1] << 8
    if tail >= 1:
        k1 ^= data[rounded_end]
        k1 = (k1 * c1) & 0xFFFFFFFF
        k1 = ((k1 << 15) | (k1 >> 17)) & 0xFFFFFFFF
        k1 = (k1 * c2) & 0xFFFFFFFF
        h1 ^= k1
    h1 ^= length
    h1 ^= h1 >> 16
    h1 = (h1 * 0x85EBCA6B) & 0xFFFFFFFF
    h1 ^= h1 >> 13
    h1 = (h1 * 0xC2B2AE35) & 0xFFFFFFFF
    h1 ^= h1 >> 16
    return h1 - 0x100000000 if h1 >= 0x80000000 else h1


def mmh3_hash(data: bytes, seed: int = 0) -> int:
    if HAVE_MMH3:
        return _mmh3.hash(data, seed)
    return murmur3_x86_32(data, seed)


def favicon_hash(data: bytes, style: str = "shodan") -> int:
    """Shodan 口径：mmh3.hash(base64.encodebytes(data))（带换行的 base64）。"""
    if style == "shodan":
        return mmh3_hash(base64.encodebytes(data))
    return mmh3_hash(base64.b64encode(data))


# ═══════════════════════════════════════════════════════════════
# 限速器：全局令牌桶的简化版（固定间隔 + 429 指数退避）
# ═══════════════════════════════════════════════════════════════
class RateLimiter:
    """线程安全的限速器。

    为什么不用 token bucket 完整实现？
    → 扫描场景只需要"平均速率可控 + 遇 429 能退避"，固定间隔 + 全局退避已足够，
      实现简单、行为可预测。生产级采集器才需要真正的令牌桶/漏桶。

    退避策略（与 RFC 的精神一致、比"睡死 60 秒"更聪明）：
      · 触发限流 → backoff = min(max(backoff*2, Retry-After), 60)
      · 成功一次 → backoff 减半（最多减到 0）
    这样连续被限流会快速退到安全速率，而偶尔一次 429 不会把整体拖死。
    """

    MAX_BACKOFF = 60.0

    def __init__(self, delay: float = 0.0):
        self.base_delay = delay
        self.backoff = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            wait_for = self.base_delay + self.backoff
        if wait_for > 0:
            time.sleep(wait_for)

    def on_throttled(self, retry_after: float = 5.0):
        with self._lock:
            self.backoff = min(max(self.backoff * 2, retry_after), self.MAX_BACKOFF)

    def on_success(self):
        with self._lock:
            if self.backoff > 0:
                self.backoff = max(self.backoff / 2 - 0.05, 0.0)


# ═══════════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════════
DIGITS_RE = re.compile(rb"\d+")
WS_RE = re.compile(rb"\s+")
TITLE_RE = re.compile(rb"<title[^>]*>(.*?)</title>", re.I | re.S)


def normalize(content: bytes) -> bytes:
    return WS_RE.sub(b" ", DIGITS_RE.sub(b"#", content)).strip()


def content_fp(content: bytes) -> str:
    return hashlib.sha256(normalize(content)).hexdigest()[:16]


def get_title(content: bytes) -> str:
    m = TITLE_RE.search(content)
    return m.group(1).decode("utf-8", "ignore").strip()[:100] if m else ""


def match_fp(patterns, text):
    hits = []
    for pat, name in patterns:
        m = re.search(pat, text, re.I)
        if m:
            ver = next((g for g in m.groups() if g), None)
            hits.append(f"{name} {ver}".strip() if ver else name)
    return hits


# ═══════════════════════════════════════════════════════════════
# 核心：扫描器
# ═══════════════════════════════════════════════════════════════
class AssetDiscovery:
    def __init__(self, base, workers=10, delay=0.1, timeout=6.0, session=None):
        self.base = base.rstrip("/") + "/"
        self.workers = max(1, min(workers, 50))     # 硬上限 50，防止把自己玩死
        self.timeout = timeout
        self.limiter = RateLimiter(delay)
        self.session = session or self._make_session()
        self.baseline = []                          # [(status, fp, norm_len)]
        self.wildcard = False                       # 任何路径都返回同一 200
        self.catch_all_kind = "unknown"             # soft404 / wildcard / normal
        self.results = []
        self.fingerprints = set()
        self.findings = []                          # 高价值发现
        self.security = {}
        self.scanned = []

    @staticmethod
    def _make_session():
        if HAVE_REQUESTS:
            s = requests.Session()
            s.headers.update({"User-Agent": UA, "Accept": "*/*",
                              "Connection": "keep-alive"})
            # 连接池必须 ≥ 线程数，否则线程会排队等连接（表现为"加了线程也没变快"）
            ad = requests.adapters.HTTPAdapter(pool_connections=60, pool_maxsize=60)
            s.mount("http://", ad)
            s.mount("https://", ad)
            return s
        lab = load_lab()
        if lab is None:
            print("既没有 requests 也找不到 00-local-lab.py，无法建立连接。")
            sys.exit(3)
        s = lab.StdlibSession()
        s.headers.update({"User-Agent": UA, "Accept": "*/*"})
        return s

    # ── 底层请求：统一处理限速、退避、异常 ──
    def _get(self, path, timeout=None):
        url = urljoin(self.base, path)
        for _attempt in range(3):
            self.limiter.wait()
            try:
                r = self.session.get(url, timeout=(3, timeout or self.timeout),
                                     allow_redirects=False)
            except NET_ERRORS as e:
                return {"url": url, "path": "/" + path.lstrip("/"), "status": None,
                        "error": type(e).__name__, "length": None, "location": None,
                        "fp": None, "norm_len": None, "content": b""}
            if r.status_code in (429, 503):
                ra = header_values(r, "Retry-After") or [None]
                try:
                    ra_f = float(ra[0]) if ra[0] else 5.0
                except ValueError:
                    ra_f = 5.0                        # Retry-After 也可能是 HTTP 日期
                self.limiter.on_throttled(ra_f)
                continue                              # 退避后重试
            self.limiter.on_success()
            return {
                "url": url, "path": "/" + path.lstrip("/"), "status": r.status_code,
                "length": len(r.content), "location": r.headers.get("Location"),
                "fp": content_fp(r.content), "norm_len": len(normalize(r.content)),
                "error": None, "content": r.content,   # content 供 favicon 复用，报告里会剔除
            }
        return {"url": url, "path": "/" + path.lstrip("/"), "status": None,
                "error": "RateLimited", "length": None, "location": None,
                "fp": None, "norm_len": None, "content": b""}

    # ── 步骤 1：基线 ──
    def build_baseline(self, n=3):
        print("[1/4] 建立软 404 基线 …")
        for i in range(n):
            rec = self._get(f"zz-not-exist-{int(time.time()) % 10**6}-{i}-x9f3")
            if rec["status"] is not None:
                self.baseline.append((rec["status"], rec["fp"], rec["norm_len"]))
            print(f"     基线 {i}: status={rec['status']} len={rec['length']} "
                  f"title={get_title(rec['content'])!r}")
        if len(self.baseline) >= 3:
            self.wildcard = (len({b[1] for b in self.baseline}) == 1
                             and self.baseline[0][0] == 200)
        if self.wildcard:
            # 关键细分：随机路径返回的页面 == 首页 → SPA 通配路由；
            #           != 首页 → 自定义 404 页（软 404）
            home = self._get("")
            self.catch_all_kind = ("wildcard"
                                   if home["fp"] and home["fp"] == self.baseline[0][1]
                                   else "soft404")
            if self.catch_all_kind == "wildcard":
                print("     ⚠️ 检测到【通配路由】：所有未知路径都返回首页（SPA try_files）")
                print("        → 状态码/长度全部失效，结果置信度低，必须人工复核。")
            else:
                print("     ⚠️ 检测到【软 404】：未知路径返回 200 的专用错误页")
                print("        → 已启用归一化哈希 + 长度容差过滤。")
        else:
            self.catch_all_kind = "normal"
            print("     ✅ 未检测到通配响应，基线可用于比对。")

    def _is_baseline(self, rec, tolerance=0.05):
        for (st, fp, nl) in self.baseline:
            if rec["status"] != st:
                continue
            if rec["fp"] and rec["fp"] == fp:
                return True
            if nl and rec["norm_len"] is not None:
                if abs(rec["norm_len"] - nl) / max(nl, 1) <= tolerance:
                    return True
        return False

    # ── 步骤 2：并发扫描 ──
    def scan(self, words):
        print(f"[2/4] 扫描 {len(words)} 个路径（{self.workers} 线程，基础延迟 "
              f"{self.limiter.base_delay}s）…")
        self.scanned = list(words)
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = {ex.submit(self._get, w): w for w in words}
            for i, fut in enumerate(cf.as_completed(futs), 1):
                try:
                    rec = fut.result()
                except Exception as e:
                    rec = {"path": "/" + futs[fut], "status": None, "error": repr(e),
                           "length": None, "location": None, "fp": None,
                           "norm_len": None, "content": b"", "url": ""}
                self._classify(rec)
                if i % 20 == 0:
                    print(f"     进度 {i}/{len(words)}  命中 {len(self.results)}")
        print(f"     完成，耗时 {time.time() - t0:.2f}s")

    def _classify(self, rec):
        """把一条响应归类：丢弃 / 记录 / 高价值发现。"""
        st = rec["status"]
        if st is None:
            return
        if st == 404:
            return
        if self._is_baseline(rec):
            return                                    # 软 404 / 通配首页，丢弃
        if st in (200, 201, 204, 301, 302, 307, 308, 401, 403, 405, 500):
            rec["verdict"] = self._verdict(rec)
            self.results.append(rec)
            key = rec["path"].strip("/")
            if key in PROBE_FP:
                self.findings.append(f"{rec['path']} → {PROBE_FP[key]} (HTTP {st})")

    @staticmethod
    def _verdict(rec):
        st = rec["status"]
        if st in (401, 403):
            return "存在但受限（需认证/被拦截）"
        if st in (301, 302, 307, 308):
            return f"重定向 → {rec.get('location')}"
        if st == 200:
            return "命中"
        return f"HTTP {st}"

    # ── 步骤 3：指纹识别 + 安全头体检 ──
    def fingerprint(self):
        print("[3/4] 指纹识别与安全头体检 …")
        try:
            r = self.session.get(self.base, timeout=(3, self.timeout),
                                 allow_redirects=False)
        except NET_ERRORS as e:
            print(f"     首页请求失败：{type(e).__name__}")
            return
        hdrs = r.headers
        print(f"     首页: HTTP {r.status_code}  Server={hdrs.get('Server')!r}")

        self.fingerprints |= set(match_fp(HEADER_FP, hdrs.get("Server", "")))
        self.fingerprints |= set(match_fp(HEADER_FP, hdrs.get("Via", "")))
        self.fingerprints |= set(match_fp(XPB_FP, hdrs.get("X-Powered-By", "")))

        # ⚠️ 用 header_values()，别写 hdrs.get_all()（requests 没有这个方法）
        cookie_all = "; ".join(header_values(r, "Set-Cookie"))
        for cname, tech in COOKIE_FP.items():
            if cname.lower() in cookie_all.lower():
                self.fingerprints.add(tech)

        body = r.content.decode("utf-8", "ignore")
        self.fingerprints |= set(match_fp(BODY_FP, body))

        # favicon 哈希（mmh3 缺失时自动用内置纯 Python 实现，永远可用）
        fav = self._get("favicon.ico")
        if fav["status"] == 200 and fav["content"]:
            raw = fav["content"]
            h = favicon_hash(raw, "shodan")
            h2 = favicon_hash(raw, "standard")
            self.fingerprints.add(f"favicon mmh3={h}")
            print(f"     favicon {len(raw)}B → mmh3(Shodan口径)={h}  (标准口径={h2})")
        else:
            print(f"     favicon 不可用（status={fav['status']}），跳过哈希")

        # 安全头体检
        for name, desc in SECURITY_HEADERS.items():
            val = hdrs.get(name)
            self.security[name] = {"desc": desc, "present": bool(val), "value": val}

        print(f"     识别到技术栈: {sorted(self.fingerprints) or '（无明确特征）'}")
        missing = [k for k, v in self.security.items() if not v["present"]]
        print(f"     缺失安全头 {len(missing)}/{len(SECURITY_HEADERS)}: {missing}")

    # ── 步骤 4：报告 ──
    def build_report(self):
        by_status = Counter(str(r["status"]) for r in self.results)
        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "target": self.base,
            "http_backend": "requests" if HAVE_REQUESTS else "urllib (stdlib)",
            "hash_backend": "mmh3" if HAVE_MMH3 else "pure-python murmur3",
            # 三个字段一起看才不会误解：wildcard 表示"存在 catch-all 响应"，
            # 而 kind 决定它是 SPA 通配（body 无判别力）还是软 404（可过滤）
            "catch_all_detected": self.wildcard,
            "catch_all_kind": self.catch_all_kind,
            "wildcard_route_detected": self.catch_all_kind == "wildcard",
            "baseline": [{"status": s, "fp": f} for (s, f, _n) in self.baseline],
            "scanned_paths": len(self.scanned),
            "hits": len(self.results),
            "status_distribution": dict(by_status),
            "fingerprints": sorted(self.fingerprints),
            "high_value_findings": self.findings,
            "security_headers": self.security,
            # content 是 bytes（不能进 JSON），这里剔除
            "results": sorted(
                ({k: v for k, v in r.items() if k != "content"} for r in self.results),
                key=lambda r: (r["status"], r["path"])),
        }


def write_reports(rep, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    jf = out_dir / f"asset-discovery-{ts}.json"
    mf = out_dir / f"asset-discovery-{ts}.md"
    jf.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Web 资产发现报告", "",
        f"- 目标: `{rep['target']}`",
        f"- 生成时间: {rep['generated_at']}",
        f"- catch-all 形态: `{rep['catch_all_kind']}`"
        + {"soft404": "（未知路径返回 200 的专用错误页 → 已按哈希过滤）",
           "wildcard": "（未知路径返回首页 → 响应体无判别力，结果需人工复核）",
           "normal": "（无 catch-all，按状态码 + 哈希判定）"}.get(rep["catch_all_kind"], ""),
        f"- SPA 通配路由: {'⚠️ 是' if rep['wildcard_route_detected'] else '否'}",
        f"- 扫描路径: {rep['scanned_paths']} | 命中: {rep['hits']}",
        f"- HTTP 后端: {rep['http_backend']} | 哈希后端: {rep['hash_backend']}", "",
        "## 技术栈指纹", "",
    ]
    lines += [f"- {x}" for x in rep["fingerprints"]] or ["- （无）"]
    lines += ["", "## 高价值发现", ""]
    lines += [f"- 🚨 {x}" for x in rep["high_value_findings"]] or ["- （无）"]
    lines += ["", "## 安全响应头体检", "", "| 响应头 | 说明 | 状态 |", "|---|---|---|"]
    for k, v in rep["security_headers"].items():
        lines.append(f"| `{k}` | {v['desc']} | {'✅ 存在' if v['present'] else '❌ 缺失'} |")
    lines += ["", "## 命中路径", "", "| 状态 | 长度 | 路径 | 说明 |", "|---|---|---|---|"]
    for r in rep["results"]:
        lines.append(f"| {r['status']} | {r['length']} | `{r['path']}` | {r.get('verdict','')} |")
    lines += ["", "> 本报告由 Day154 教学工具生成，仅用于自有资产自检。"]

    mf.write_text("\n".join(lines), encoding="utf-8")
    return jf, mf


def guard(target_url, has_auth):
    host = urlparse(target_url).hostname or ""
    if host in LOCAL_HOSTS:
        return
    if has_auth:
        print(f"⚠️  已声明对 {host} 的授权。请确认授权范围/时间窗/速率上限。")
        return
    print("⛔ 拒绝执行：非本机目标且未声明授权。加 --i-have-authorization 表示你有书面授权。")
    sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser(description="Day154 Web 资产发现与指纹识别（仅授权目标）")
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--wordlist", default=None)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--delay", type=float, default=0.1, help="每请求基础延迟（秒）")
    ap.add_argument("--out-dir", default=None,
                    help="报告输出目录；默认用系统临时目录（不污染当前工作树）")
    ap.add_argument("--self-test", action="store_true", help="离线自检（不联网）")
    ap.add_argument("--i-have-authorization", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    guard(args.url, args.i_have_authorization)

    # 默认输出到临时目录：避免把报告写进 git 工作树（演示产物不入库）
    if args.out_dir:
        out_dir = Path(args.out_dir)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="day154-asset-"))
        print(f"ℹ️ 未指定 --out-dir，报告写入临时目录 {out_dir}")

    words = DEFAULT_WORDS
    if args.wordlist:
        with open(args.wordlist, encoding="utf-8", errors="ignore") as f:
            words = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        print(f"载入字典 {len(words)} 条")

    tool = AssetDiscovery(args.url, workers=args.workers, delay=args.delay)
    try:
        tool.build_baseline()
        tool.scan(words)
        tool.fingerprint()
        rep = tool.build_report()
    finally:
        try:
            tool.session.close()
        except Exception:
            pass
    jf, mf = write_reports(rep, out_dir)

    print("\n" + "=" * 66)
    print(f"✅ 命中 {rep['hits']} 条 | 指纹 {len(rep['fingerprints'])} 项 | "
          f"高价值发现 {len(rep['high_value_findings'])} 条")
    print(f"   JSON 报告: {jf}")
    print(f"   Markdown : {mf}")
    print("=" * 66)
    print("📌 复盘建议：")
    print("  1. 先看「高价值发现」——那些是真正需要立刻处理的（.env / .git / actuator）")
    print("  2. 再看「安全响应头」缺失清单——这是低成本的加固项")
    print(f"  3. 最后核对命中路径里是否有软 404 漏网（catch_all_kind={rep['catch_all_kind']}）")
    return 0


# ═══════════════════════════════════════════════════════════════
# 离线自检
# ═══════════════════════════════════════════════════════════════
class _FallbackSelfTest:
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


def self_test() -> int:
    lab = load_lab()
    if lab is not None:
        t = lab.SelfTest("day-154 示例03 资产发现工具")
    else:
        t = _FallbackSelfTest("day-154 示例03 资产发现工具")
        print("⚠️ 未找到 00-local-lab.py，只跑纯函数断言。")

    # ── 1. 纯函数 ──
    t.check("normalize(): 数字归一", normalize(b"a1b22"), b"a#b#")
    t.check("content_fp(): 长度固定 16", len(content_fp(b"abc")), 16)
    t.check("content_fp(): 数字抖动不影响哈希",
            content_fp(b"count 1"), content_fp(b"count 98765"))
    t.check("get_title(): 提取标题", get_title(b"<title> X </title>"), "X")
    t.check("get_title(): 无标题返回空串", get_title(b"<html></html>"), "")
    t.check("match_fp(): 提取版本号",
            match_fp(HEADER_FP, "nginx/1.24.0"), ["nginx 1.24.0"])
    t.check("match_fp(): 无匹配返回空", match_fp(HEADER_FP, "hello"), [])
    t.check("match_fp(): 多规则可同时命中",
            sorted(match_fp([(r"nginx", "nginx"), (r"openresty", "OpenResty")],
                            "openresty/1.21 nginx")), ["OpenResty", "nginx"])

    # ── 2. RateLimiter 退避数学 ──
    rl = RateLimiter(0.0)
    t.check("退避：初始为 0", rl.backoff, 0.0)
    rl.on_throttled(5.0)
    t.check("退避：首次按 Retry-After", rl.backoff, 5.0)
    rl.on_throttled(5.0)
    t.check("退避：第二次翻倍", rl.backoff, 10.0)
    for _ in range(10):
        rl.on_throttled(5.0)
    t.check("退避：上限封顶", rl.backoff, RateLimiter.MAX_BACKOFF)
    rl.on_success()
    t.check("恢复：成功一次减半", rl.backoff, 29.95)
    rl2 = RateLimiter(0.0)
    rl2.on_throttled(1.0)
    t.check("退避：Retry-After 小于 2×0 时取 Retry-After", rl2.backoff, 1.0)

    # ── 3. 哈希实现一致性 ──
    t.check("favicon hash: Shodan 口径可复现",
            favicon_hash(b"\x00\x01\x02\x03" * 16, "shodan"),
            favicon_hash(b"\x00\x01\x02\x03" * 16, "shodan"))
    t.truthy("favicon hash: 两种口径不同（必须统一）",
             favicon_hash(b"x" * 100, "shodan") != favicon_hash(b"x" * 100, "standard"))
    if HAVE_MMH3:
        t.check("纯 Python 与 mmh3 一致（空串）", murmur3_x86_32(b""), _mmh3.hash(b""))
        t.check("纯 Python 与 mmh3 一致（abc）", murmur3_x86_32(b"abc"), _mmh3.hash(b"abc"))
    else:
        print("ℹ️  未安装 mmh3，使用内置纯 Python MurmurHash3（已知向量 foo/-156908512 已在校验集中）")
    t.check('MurmurHash3 已知向量 "foo"', murmur3_x86_32(b"foo"), -156908512)

    # ── 4. 端到端：对着回环靶场跑完整流水线 ──
    if lab is not None:
        srv = lab.start_lab(0, mode="soft404", slow_delay=0.01)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        tmp = tempfile.mkdtemp(prefix="day154-selftest-")
        try:
            tool = AssetDiscovery(base, workers=4, delay=0.0,
                                  session=lab.StdlibSession())
            tool.build_baseline()
            t.check("流水线：识别为软 404 站点", tool.catch_all_kind, "soft404")
            t.check("流水线：wildcard 标志（存在 catch-all）", tool.wildcard, True)

            # 在默认字典基础上补两条"需登录/被拒"的路径，用于验证 401/403 也会被记录
            words = list(DEFAULT_WORDS) + ["admin/", "secret/"]
            tool.scan(words)
            hits = {r["path"]: r["status"] for r in tool.results}
            # 存在的资源必须被记录，且 401/403 也要记录（初学者最容易漏）
            t.check("流水线：/admin → 301 被记录", hits.get("/admin"), 301)
            t.check("流水线：/admin/ 记录为 401", hits.get("/admin/"), 401)
            t.check("流水线：/secret/ 记录为 403", hits.get("/secret/"), 403)
            t.check("流水线：/robots.txt 记录为 200", hits.get("/robots.txt"), 200)
            t.check("流水线：/.env 记录为 200（高价值）", hits.get("/.env"), 200)
            # 不存在的路径必须被过滤掉（软 404 过滤生效）
            t.check("流水线：不存在路径未出现在结果中", hits.get("/phpinfo.php"), None)
            t.check("流水线：不存在路径（中文/随机）也被过滤",
                    hits.get("/test.php"), None)
            t.check("流水线：命中数远小于扫描数",
                    len(tool.results) < len(words) // 2, True)
            t.truthy("流水线：命中里没有一条是软 404 基线",
                     all(r["fp"] not in {b[1] for b in tool.baseline}
                         for r in tool.results))

            tool.fingerprint()
            t.truthy("指纹：识别到 nginx", "nginx 1.24.0" in tool.fingerprints)
            t.truthy("指纹：识别到 PHP", "PHP 8.1.2" in tool.fingerprints)
            t.truthy("指纹：Cookie 名识别到 PHP", "PHP" in tool.fingerprints)
            t.truthy("指纹：HTML generator 识别到 WordPress",
                     any(f.startswith("WordPress") for f in tool.fingerprints))
            t.truthy("指纹：favicon 哈希已计算",
                     any(f.startswith("favicon mmh3=") for f in tool.fingerprints))
            t.check("安全头：HSTS 判定为缺失",
                    tool.security["Strict-Transport-Security"]["present"], False)
            t.check("安全头：共体检 6 项", len(tool.security), len(SECURITY_HEADERS))
            t.truthy("高价值发现：包含 .git/HEAD",
                     any(".git/HEAD" in f for f in tool.findings))
            t.truthy("高价值发现：包含 /actuator/env",
                     any("actuator/env" in f for f in tool.findings))

            rep = tool.build_report()
            t.check("报告：scanned_paths", rep["scanned_paths"], len(words))
            t.check("报告：hits 与结果数一致", rep["hits"], len(tool.results))
            t.check("报告：catch_all_kind 写入", rep["catch_all_kind"], "soft404")
            t.check("报告：catch_all_detected=True 但 wildcard_route=False"
                    "（软404 不等于 SPA 通配）",
                    (rep["catch_all_detected"], rep["wildcard_route_detected"]),
                    (True, False))
            t.truthy("报告：results 里不含 bytes（可 JSON 序列化）",
                     all("content" not in r for r in rep["results"]))

            jf, mf = write_reports(rep, Path(tmp))
            t.check("报告：JSON 已落盘", jf.exists(), True)
            t.check("报告：Markdown 已落盘", mf.exists(), True)
            loaded = json.loads(jf.read_text(encoding="utf-8"))
            t.check("报告：JSON 可被重新解析", loaded["hits"], rep["hits"])
            md = mf.read_text(encoding="utf-8")
            t.truthy("报告：Markdown 含高价值发现小节", "高价值发现" in md)
            t.truthy("报告：Markdown 含安全头表格", "安全响应头体检" in md)
            t.check("报告：输出目录在临时目录（不污染仓库）",
                    Path(tmp).is_dir(), True)

            tool.session.close()

            # ── 5. 通配路由站点：catch_all_kind 必须能区分 ──
            srv2 = lab.start_lab(0, mode="wildcard", slow_delay=0.01)
            try:
                tool2 = AssetDiscovery(f"http://127.0.0.1:{srv2.server_address[1]}",
                                       workers=2, delay=0.0,
                                       session=lab.StdlibSession())
                tool2.build_baseline()
                t.check("通配靶场：识别为 wildcard", tool2.catch_all_kind, "wildcard")
                tool2.session.close()
            finally:
                srv2.shutdown()
                srv2.server_close()

            # ── 6. 严格 404 站点：不该有 catch-all ──
            srv3 = lab.start_lab(0, mode="strict404", slow_delay=0.01)
            try:
                tool3 = AssetDiscovery(f"http://127.0.0.1:{srv3.server_address[1]}",
                                       workers=2, delay=0.0,
                                       session=lab.StdlibSession())
                tool3.build_baseline()
                t.check("严格靶场：catch_all_kind=normal", tool3.catch_all_kind, "normal")
                t.check("严格靶场：wildcard=False", tool3.wildcard, False)
                tool3.session.close()
            finally:
                srv3.shutdown()
                srv3.server_close()

            # ── 7. 限流退避：构造一个"永远返回 429"的假会话 ──
            #     （比等真实靶场限流快得多，且完全确定；Retry-After 取小值避免拖慢自检）
            class Always429:
                def get(self, url, timeout=None, allow_redirects=False, **kw):
                    return lab.StdlibResponse(
                        429, lab.CIHeaders([("Retry-After", "0.05"),
                                            ("Content-Type", "text/plain")]),
                        b"too many requests", url, 0.0)

                def close(self):
                    pass

            tool4 = AssetDiscovery("http://127.0.0.1:1", workers=1, delay=0.0,
                                   session=Always429())
            rec = tool4._get("anything")
            t.check("限流：重试耗尽后标记 RateLimited", rec["error"], "RateLimited")
            t.truthy("限流：退避值被抬高（指数退避生效）",
                     tool4.limiter.backoff >= 0.05)

            # 反向：成功一次后退避必须衰减，否则扫描会越来越慢
            tool4.limiter.on_throttled(10.0)
            before = tool4.limiter.backoff
            tool4.limiter.on_success()
            t.truthy(f"限流：成功后退避从 {before} 衰减到 {tool4.limiter.backoff}",
                     tool4.limiter.backoff < before)
            tool4.session.close()
        finally:
            srv.shutdown()
            srv.server_close()

    return t.finish()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
