#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 154 · 示例 03 —— 实战：Web 资产发现与指纹识别工具
=========================================================

把示例 01（并发扫描）和示例 02（软 404 + 指纹）合成一个能用的 CLI 工具。

功能：
  1. 软 404 基线探测（自动识别通配路由）
  2. 并发目录扫描（线程池 + 限速 + 429 指数退避）
  3. Web 指纹识别（响应头 / Cookie / HTML 特征 / 主动探针 / favicon 哈希）
  4. 安全响应头体检（HSTS / CSP / X-Frame-Options …）
  5. 输出 JSON + Markdown 报告

运行：
    python3 03-asset-discovery.py --url http://127.0.0.1:8080
    python3 03-asset-discovery.py --url http://127.0.0.1:8080 --workers 5 --delay 0.2
    python3 03-asset-discovery.py --url http://127.0.0.1:8080 --wordlist common.txt --out-dir ./out

⚠️ 法律边界：非本机目标必须显式 --i-have-authorization。默认严格限速。
⚠️ 本工具只做"发现"，不做任何漏洞利用。
"""

import argparse
import base64
import concurrent.futures as cf
import hashlib
import json
import re
import sys
import threading
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    print("需要 requests：pip install requests")
    sys.exit(1)

try:
    import mmh3
except ImportError:
    mmh3 = None

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


# ═══════════════════════════════════════════════════════════════
# 限速器：全局令牌桶的简化版（固定间隔 + 429 指数退避）
# ═══════════════════════════════════════════════════════════════
class RateLimiter:
    """线程安全的限速器。

    为什么不用 token bucket 完整实现？
    → 扫描场景只需要"平均速率可控 + 遇 429 能退避"，固定间隔 + 全局退避已足够，
      实现简单、行为可预测。生产级采集器才需要真正的令牌桶/漏桶。
    """

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
            self.backoff = min(max(self.backoff * 2, retry_after), 60.0)
            print(f"   ⚠️ 触发限流，退避 {self.backoff:.1f}s")

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
    def __init__(self, base, workers=10, delay=0.1, timeout=6.0):
        self.base = base.rstrip("/") + "/"
        self.workers = max(1, min(workers, 50))     # 硬上限 50，防止把自己玩死
        self.timeout = timeout
        self.limiter = RateLimiter(delay)
        self.session = self._make_session()
        self.baseline = []                          # [(status, fp, norm_len)]
        self.wildcard = False
        self.results = []
        self.fingerprints = set()
        self.findings = []                          # 高价值发现
        self.security = {}

    def _make_session(self):
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept": "*/*", "Connection": "keep-alive"})
        ad = requests.adapters.HTTPAdapter(pool_connections=self.workers + 10,
                                           pool_maxsize=self.workers + 10)
        s.mount("http://", ad)
        s.mount("https://", ad)
        return s

    # ── 底层请求：统一处理限速、退避、异常 ──
    def _get(self, path, timeout=None):
        url = urljoin(self.base, path)
        for attempt in range(3):
            self.limiter.wait()
            try:
                r = self.session.get(url, timeout=(3, timeout or self.timeout),
                                     allow_redirects=False)
            except RequestException as e:
                return {"url": url, "path": "/" + path.lstrip("/"), "status": None,
                        "error": type(e).__name__, "length": None, "location": None,
                        "fp": None, "norm_len": None}
            if r.status_code in (429, 503):
                ra = r.headers.get("Retry-After")
                try:
                    ra_f = float(ra) if ra else 5.0
                except ValueError:
                    ra_f = 5.0                        # Retry-After 也可能是 HTTP 日期
                self.limiter.on_throttled(ra_f)
                continue                              # 退避后重试
            self.limiter.on_success()
            return {
                "url": url, "path": "/" + path.lstrip("/"), "status": r.status_code,
                "length": len(r.content), "location": r.headers.get("Location"),
                "fp": content_fp(r.content), "norm_len": len(normalize(r.content)),
                "error": None,
            }
        return {"url": url, "path": "/" + path.lstrip("/"), "status": None,
                "error": "RateLimited", "length": None, "location": None,
                "fp": None, "norm_len": None}

    # ── 步骤 1：基线 ──
    def build_baseline(self, n=3):
        print("[1/4] 建立软 404 基线 …")
        for i in range(n):
            rec = self._get(f"zz-not-exist-{int(time.time())}-{i}-x9f3")
            if rec["status"] is not None:
                self.baseline.append((rec["status"], rec["fp"], rec["norm_len"]))
            print(f"     基线 {i}: status={rec['status']} len={rec['length']}")
        if len(self.baseline) >= 3:
            self.wildcard = (len({b[1] for b in self.baseline}) == 1
                             and self.baseline[0][0] == 200)
        if self.wildcard:
            print("     ⚠️ 检测到通配响应（所有路径都返回相同 200 页面）")
            print("        → 本工具将只采用“哈希差异”判定，误报会明显增多，请人工复核。")

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
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=self.workers) as ex:
            futs = {ex.submit(self._get, w): w for w in words}
            for i, fut in enumerate(cf.as_completed(futs), 1):
                try:
                    rec = fut.result()
                except Exception as e:
                    rec = {"path": "/" + futs[fut], "status": None, "error": repr(e),
                           "length": None, "location": None, "fp": None, "norm_len": None,
                           "url": ""}
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
            return                                    # 软 404，丢弃
        if st in (200, 201, 204, 301, 302, 307, 308, 401, 403, 405, 500):
            rec["verdict"] = self._verdict(rec)
            self.results.append(rec)
            if rec["path"].strip("/") in PROBE_FP:
                self.findings.append(f"{rec['path']} → {PROBE_FP[rec['path'].strip('/')]} "
                                     f"(HTTP {st})")

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
        except RequestException as e:
            print(f"     首页请求失败：{type(e).__name__}")
            return
        hdrs = r.headers
        print(f"     首页: HTTP {r.status_code}  Server={hdrs.get('Server')!r}")

        self.fingerprints |= set(match_fp(HEADER_FP, hdrs.get("Server", "")))
        self.fingerprints |= set(match_fp(HEADER_FP, hdrs.get("Via", "")))
        self.fingerprints |= set(match_fp(XPB_FP, hdrs.get("X-Powered-By", "")))

        cookie_all = "; ".join(hdrs.get_all("Set-Cookie") or [])
        for cname, tech in COOKIE_FP.items():
            if cname.lower() in cookie_all.lower():
                self.fingerprints.add(tech)

        body = r.content.decode("utf-8", "ignore")
        self.fingerprints |= set(match_fp(BODY_FP, body))

        # favicon 哈希
        if mmh3 is not None:
            fav = self._get("favicon.ico")
            if fav["status"] == 200 and fav["fp"]:
                try:
                    raw = self.session.get(urljoin(self.base, "favicon.ico"),
                                           timeout=(3, self.timeout)).content
                    if raw:
                        h = mmh3.hash(base64.encodebytes(raw))
                        self.fingerprints.add(f"favicon mmh3={h}")
                except RequestException:
                    pass
        else:
            print("     ℹ️ 未安装 mmh3，跳过 favicon 哈希（pip install mmh3）")

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
            "wildcard_route_detected": self.wildcard,
            "baseline": [{"status": s, "fp": f} for (s, f, _n) in self.baseline],
            "scanned_paths": len(getattr(self, "scanned", [])),
            "hits": len(self.results),
            "status_distribution": dict(by_status),
            "fingerprints": sorted(self.fingerprints),
            "high_value_findings": self.findings,
            "security_headers": self.security,
            "results": sorted(self.results, key=lambda r: (r["status"], r["path"])),
        }


def write_reports(rep, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    jf = out_dir / f"asset-discovery-{ts}.json"
    mf = out_dir / f"asset-discovery-{ts}.md"
    jf.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Web 资产发现报告", "",
        f"- 目标: `{rep['target']}`",
        f"- 生成时间: {rep['generated_at']}",
        f"- 通配路由: {'⚠️ 是（结果需人工复核）' if rep['wildcard_route_detected'] else '否'}",
        f"- 命中数: {rep['hits']}", "", "## 技术栈指纹", "",
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
    ap.add_argument("--url", default="http://127.0.0.1/")
    ap.add_argument("--wordlist", default=None)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--delay", type=float, default=0.1, help="每请求基础延迟（秒）")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--i-have-authorization", action="store_true")
    args = ap.parse_args()

    guard(args.url, args.i_have_authorization)

    words = DEFAULT_WORDS
    if args.wordlist:
        with open(args.wordlist, encoding="utf-8", errors="ignore") as f:
            words = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        print(f"载入字典 {len(words)} 条")

    tool = AssetDiscovery(args.url, workers=args.workers, delay=args.delay)
    tool.scanned = words
    tool.build_baseline()
    tool.scan(words)
    tool.fingerprint()
    rep = tool.build_report()
    jf, mf = write_reports(rep, Path(args.out_dir))

    print("\n" + "=" * 66)
    print(f"✅ 命中 {rep['hits']} 条 | 指纹 {len(rep['fingerprints'])} 项 | "
          f"高价值发现 {len(rep['high_value_findings'])} 条")
    print(f"   JSON 报告: {jf}")
    print(f"   Markdown : {mf}")
    print("=" * 66)
    print("📌 复盘建议：")
    print("  1. 先看“高价值发现”——那些是真正需要立刻处理的（.env / .git / actuator）")
    print("  2. 再看“安全响应头”缺失清单——这是低成本的加固项")
    print("  3. 最后核对命中路径里是否有软 404 漏网（尤其 wildcard=True 时）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(130)
