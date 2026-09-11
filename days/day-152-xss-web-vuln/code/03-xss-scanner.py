#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 152 · 示例 03：XSS 反射检测与安全头扫描（实战）
=====================================================

这个脚本回答一个很实际的问题：
    **"我怎么知道一个页面到底有没有把用户输入编码？"**

它自带一个**本地漏洞靶场**（只监听 127.0.0.1），然后自动完成：

    ① 反射检测   —— 注入**无害探测标记**，看响应里是"原样出现"还是"实体化出现"
    ② 上下文判定 —— 标记落在 HTML 文本 / 双引号属性 / 单引号属性 的哪一种里
    ③ Sink 扫描  —— 页面 JS 里有没有 innerHTML / document.write / eval 这类危险信宿
    ④ 安全头审计 —— CSP / nosniff / X-Frame-Options / Referrer-Policy / Cookie 标志
    ⑤ 分级报告   —— PASS / WARN / FAIL + 修复建议，支持 --json 与退出码（可接 CI）

⚠️ 为什么探测标记是"无害"的？
---------------------------
因为检测 XSS **不需要真的弹窗**。判断一个反射点是否危险，只要看：
    "我送进去的 `<x152probe>` 是原样出现在 HTML 里，还是被转义成了
     `&lt;x152probe&gt;`？"
前者说明"标签注入能力存在"，后者说明"已编码"。整个过程不执行任何脚本、
不带任何事件处理器、不针对任何真实业务数据。

⚠️ 使用边界
-----------
* 默认只扫描**本脚本自己启动的本地靶场**；
* 用 `--url` 扫描外部目标时，**非回环地址必须显式加 `--authorized`**，
  表示你已获得该目标的书面授权（授权渗透测试 / SRC / 自己的资产）。
  未授权测试是违法行为，本脚本拒绝执行。

运行
----
    python3 03-xss-scanner.py                 # 扫描内置本地靶场（演示漏洞 + 安全版）
    python3 03-xss-scanner.py --json          # 输出 JSON 报告
    python3 03-xss-scanner.py --url http://127.0.0.1:8000/ --param q
    echo $?                                   # 有 FAIL 时为 1，可接 CI
"""

import argparse
import html as html_mod
import http.server
import ipaddress
import json
import re
import secrets
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

# ══════════════════════════════════════════════════════════════════
# 数据结构
# ══════════════════════════════════════════════════════════════════

PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"

# 扫描过程中是否打印进度。用 --json 时必须关掉，
# 否则进度文字会混进 JSON 里，导致 `--json | jq` 直接解析失败。
PROGRESS = True


@dataclass
class Finding:
    """一条扫描结论。level 决定它是否会让退出码变成 1。"""
    level: str
    category: str
    target: str
    detail: str
    advice: str = ""
    evidence: str = ""      # 原始证据（命中的响应片段），便于人工复核


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, category: str, target: str,
            detail: str, advice: str = "", evidence: str = "") -> None:
        self.findings.append(
            Finding(level, category, target, detail, advice, evidence))
        # 一边扫一边给个进度提示，长扫描时不会让人以为程序卡住了
        if PROGRESS:
            print(f"  {ICON.get(level, '?')} [{level}] {category}: {target} — "
                  f"{detail[:60]}")

    def counts(self) -> dict:
        c = {PASS: 0, WARN: 0, FAIL: 0, INFO: 0}
        for f in self.findings:
            c[f.level] = c.get(f.level, 0) + 1
        return c

    def to_dict(self) -> dict:
        return {
            "counts": self.counts(),
            "findings": [vars(f) for f in self.findings],
        }


# ══════════════════════════════════════════════════════════════════
# 探测标记（无害）
# ══════════════════════════════════════════════════════════════════

# 每种探测都针对一个"上下文"：标签注入、双引号属性逃逸、单引号属性逃逸。
# 注意：**没有**事件处理器，**没有** alert，**没有**任何会执行的东西。
PROBE_TEMPLATES = {
    "HTML 文本上下文（标签注入）": "<{t}>",
    "双引号属性上下文（属性逃逸）": '"><{t}>',
    "单引号属性上下文（属性逃逸）": "'><{t}>",
}

# 判断"危险信宿"的正则：出现在返回的页面 JS 里就提示可能存在的 DOM 型风险
SINK_PATTERNS = {
    r"\.innerHTML\s*=": "innerHTML 赋值（字符串会被当 HTML 解析）",
    r"\.outerHTML\s*=": "outerHTML 赋值",
    r"document\.write\s*\(": "document.write（直接写文档流）",
    r"insertAdjacentHTML\s*\(": "insertAdjacentHTML",
    r"\beval\s*\(": "eval（字符串当代码）",
    r"new\s+Function\s*\(": "new Function（字符串当代码）",
    r"location\.(hash|search|href)": "直接读取 location（可能的污点源）",
    r"document\.(referrer|URL)": "直接读取 document.referrer/URL",
}

# 常见的安全响应头检查项（名称 → 说明）
SECURITY_HEADERS = {
    "X-Content-Type-Options": "应设为 nosniff，防止 MIME 嗅探导致脚本被当 HTML 执行",
    "X-Frame-Options": "应设为 DENY/SAMEORIGIN，防点击劫持",
    "Referrer-Policy": "建议 strict-origin-when-cross-origin，减少信息泄漏",
    "Permissions-Policy": "按需关闭 geolocation/camera/microphone 等能力",
}


def make_probe(template_key: str) -> tuple[str, str]:
    """生成一个**唯一**的探测标记与对应 payload。

    唯一性是关键：如果标记是固定串，可能和页面已有内容撞车，
    导致"其实没回显"被误判成"回显了"。每次都带随机后缀才可靠。
    """
    token = "x152probe" + secrets.token_hex(3)
    return token, PROBE_TEMPLATES[template_key].format(t=token)


def classify(body: str, token: str, payload: str) -> tuple[str, str]:
    """判断 payload 在响应体里的"命运"。

    返回 (level, 说明)。
      * 原样出现          → FAIL：标签/属性注入能力存在
      * 只转义了尖括号    → WARN：引号还是裸的，属性上下文依然危险
      * 完整转义成实体    → PASS：输出编码生效
      * 完全没出现        → INFO：参数未回显，无从判断
    """
    if payload in body:
        return FAIL, "探测标记**原样出现**，说明未做输出编码"
    if html_mod.escape(payload, quote=True) in body:
        return PASS, "探测标记被完整转义为 HTML 实体，输出编码生效"
    # 有些实现只替换 < >（quote=False 风格）—— 文本上下文够用，属性上下文不够
    angle_only = payload.replace("<", "&lt;").replace(">", "&gt;")
    if angle_only in body:
        return WARN, "只转义了尖括号，**引号仍是裸的**：属性上下文可被闭合逃逸"
    if token in body:
        return WARN, f"标记存在但形式不明确（疑似部分转义/被改写），需人工确认"
    return INFO, "参数未在响应中回显，无法据此判断（不代表安全）"


def context_snippet(body: str, needle: str, width: int = 70) -> str:
    """取出命中位置前后的上下文，方便人工判断落在了哪种上下文里。"""
    idx = body.find(needle)
    if idx < 0:
        return ""
    start = max(0, idx - width)
    end = min(len(body), idx + len(needle) + width)
    snippet = body[start:end].replace("\n", " ")
    return ("…" if start else "") + snippet + ("…" if end < len(body) else "")


# ══════════════════════════════════════════════════════════════════
# HTTP 客户端（标准库）
# ══════════════════════════════════════════════════════════════════

@dataclass
class HttpResponse:
    status: int
    headers: dict
    body: str
    final_url: str


def http_get(url: str, timeout: float = 5.0,
             follow_redirects: bool = True) -> HttpResponse | None:
    """发 GET，返回状态码 / 头 / 正文。

    注意：真实扫描器必须处理重定向、超时、非 200、编码异常等；
    这里保持最小实现，但把"异常不能崩"这条守住了。
    """
    req = urllib.request.Request(url, headers={"User-Agent": "x152-lab-scanner/1.0"})
    opener = urllib.request.build_opener()
    if not follow_redirects:
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **kw):
                return None
        opener = urllib.request.build_opener(NoRedirect)

    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return HttpResponse(
                status=resp.status,
                headers={k: v for k, v in resp.headers.items()},
                body=raw.decode(charset, errors="replace"),
                final_url=resp.url,
            )
    except urllib.error.HTTPError as e:
        raw = e.read()
        return HttpResponse(
            status=e.code,
            headers={k: v for k, v in e.headers.items()} if e.headers else {},
            body=raw.decode("utf-8", errors="replace"),
            final_url=url,
        )
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        print(f"  ⚠️  请求失败 {url}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# 本地漏洞靶场（仅供本脚本自测；只绑定 127.0.0.1）
# ══════════════════════════════════════════════════════════════════

class LabHandler(http.server.BaseHTTPRequestHandler):
    """教学靶场：故意包含几种不同安全水准的端点。

    /search  → 反射型：**完全未编码**（应被扫成 FAIL）
    /attr    → 属性上下文：**只转义尖括号**（应被扫成 WARN）
    /safe    → 正确编码（应被扫成 PASS）
    /secure  → 正确编码 + 全套安全响应头（用于验证头部审计）
    """

    server_version = "X152Lab/1.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _send(self, body: str, extra_headers: dict | None = None) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(parsed.query)
        path = parsed.path

        if path == "/search":
            val = q.get("q", [""])[0]
            # ❌ 危险写法：原样拼接
            self._send(f"<h1>搜索结果</h1><div>你搜索了：{val}</div>")

        elif path == "/attr":
            val = q.get("name", [""])[0]
            # ❌ 半吊子写法：只替换尖括号，引号原样 → 属性逃逸依然可行
            half = val.replace("<", "&lt;").replace(">", "&gt;")
            self._send(f'<h1>属性演示</h1><input type="text" value="{half}">')

        elif path == "/safe":
            val = q.get("q", [""])[0]
            # ✅ 正确写法：按上下文完整编码
            self._send(
                "<h1>安全搜索</h1>"
                f"<div>你搜索了：{html_mod.escape(val, quote=True)}</div>"
            )

        elif path == "/secure":
            val = q.get("q", [""])[0]
            csp = (
                "default-src 'self'; script-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'"
            )
            self._send(
                "<h1>安全端点</h1>"
                f"<div>你搜索了：{html_mod.escape(val, quote=True)}</div>",
                extra_headers={
                    "Content-Security-Policy": csp,
                    "X-Content-Type-Options": "nosniff",
                    "X-Frame-Options": "DENY",
                    "Referrer-Policy": "strict-origin-when-cross-origin",
                    "Permissions-Policy": "camera=(), microphone=()",
                    # 三件套齐全才算合格。注意：Secure 标志意味着"只在 HTTPS 下回传"，
                    # 本地 http 靶场环境下浏览器不会把它带回来，但**响应头的正确性**
                    # 仍然可以并且应该被审计到。
                    "Set-Cookie": "sid=lab; HttpOnly; Secure; SameSite=Lax; Path=/",
                },
            )

        elif path == "/dom":
            # 一个含危险信宿的页面（用于验证 sink 扫描；本页不会真的执行危险赋值）
            self._send(
                "<h1>DOM 演示</h1>"
                "<div id='out'></div>"
                "<script>"
                "var h = decodeURIComponent(location.hash.slice(1));"
                "document.getElementById('out').textContent = h;"   # 安全写法
                "// 危险写法示例（未启用）: el.innerHTML = h;"
                "</script>"
            )

        else:
            self._send("<h1>X152 本地靶场</h1><p>试试 /search?q=1 /attr?name=1 "
                       "/safe?q=1 /secure?q=1 /dom</p>")


def start_lab() -> tuple[http.server.ThreadingHTTPServer, str]:
    """启动本地靶场，返回 (server, base_url)。"""
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), LabHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.server_address[1]
    return httpd, f"http://127.0.0.1:{port}"


# ══════════════════════════════════════════════════════════════════
# 扫描逻辑
# ══════════════════════════════════════════════════════════════════

def scan_reflection(report: Report, url: str, param: str,
                    timeout: float) -> None:
    """对 (url, param) 做三种上下文的反射检测。"""
    for ctx_name in PROBE_TEMPLATES:
        token, payload = make_probe(ctx_name)
        query = urllib.parse.urlencode({param: payload})
        target = f"{url}?{query}"
        resp = http_get(target, timeout=timeout)
        if resp is None:
            report.add(WARN, "反射检测", f"{url}?{param}",
                       f"{ctx_name}：请求失败，未能完成检测",
                       "确认目标可达、端口开放、没有被网络策略拦截")
            return

        level, detail = classify(resp.body, token, payload)
        advice = ""
        if level == FAIL:
            advice = ("对该参数做**对应上下文**的输出编码：HTML 文本用 html.escape "
                      "(quote=True)，属性值必须加引号，URL 用 quote()，"
                      "JS 用 json.dumps 或 data-* 属性传递")
        elif level == WARN:
            advice = "补齐引号转义（html.escape(quote=True)），并给所有属性值加引号"
        elif level == PASS:
            advice = "保持；建议再加 CSP 作为纵深防御（见 header 审计）"

        evidence = ""
        if level in (FAIL, WARN):
            evidence = context_snippet(
                resp.body, payload if payload in resp.body else token)

        report.add(level, "反射检测", f"{url} [{param}]",
                   f"{ctx_name} → {detail}",
                   advice, evidence)


def scan_sinks(report: Report, url: str, timeout: float) -> None:
    """扫描返回页面里的 JavaScript 危险信宿（DOM 型 XSS 的线索）。"""
    resp = http_get(url, timeout=timeout)
    if resp is None:
        return

    found: list[str] = []
    for pattern, desc in SINK_PATTERNS.items():
        n = len(re.findall(pattern, resp.body))
        if n:
            found.append(f"{desc} × {n}")

    if not found:
        report.add(PASS, "Sink 扫描", url, "未在返回页面中发现已知危险信宿",
                   "继续用 textContent / createElement 等安全 DOM API")
    else:
        report.add(WARN, "Sink 扫描", url,
                   "发现危险信宿（需人工确认数据来源是否可控）：" + "；".join(found),
                   "确认这些 sink 的输入**不是**用户可控数据；"
                   "若是，改用 textContent，或对富文本先净化再插入")



def scan_headers(report: Report, url: str, timeout: float) -> None:
    """审计响应安全头与 Cookie 标志。"""
    resp = http_get(url, timeout=timeout)
    if resp is None:
        report.add(WARN, "安全头", url, "请求失败，无法审计响应头", "确认目标可达")
        return

    h = {k.lower(): v for k, v in resp.headers.items()}

    # ── CSP ──
    csp = h.get("content-security-policy", "")
    if not csp:
        report.add(FAIL, "安全头", url,
                   "缺少 Content-Security-Policy（XSS 的第二道防线不存在）",
                   "加上 CSP：default-src 'self'; script-src 'nonce-<每次随机>' "
                   "'strict-dynamic'; object-src 'none'; base-uri 'none'; "
                   "frame-ancestors 'none'")
    else:
        problems = []
        if "unsafe-inline" in csp:
            problems.append("含 'unsafe-inline'（内联脚本可执行，XSS 防线基本失效）")
        if "unsafe-eval" in csp:
            problems.append("含 'unsafe-eval'（允许字符串当代码执行）")
        if "object-src" not in csp:
            problems.append("未限制 object-src（建议 'none'）")
        if "base-uri" not in csp:
            problems.append("未限制 base-uri（可被 <base> 劫持相对路径）")
        if "frame-ancestors" not in csp and "x-frame-options" not in h:
            problems.append("未限制 frame-ancestors（点击劫持风险）")
        if problems:
            report.add(FAIL if any("unsafe" in p for p in problems) else WARN,
                       "安全头", url,
                       "CSP 已存在但存在弱点：" + "；".join(problems),
                       "移除 unsafe-inline/unsafe-eval，改用 nonce + strict-dynamic，"
                       "并补齐 object-src / base-uri / frame-ancestors")
        else:
            report.add(PASS, "安全头", url, "CSP 配置良好（无 unsafe-*，关键指令齐全）")

    # ── 其他安全头 ──
    for name, advice in SECURITY_HEADERS.items():
        value = h.get(name.lower())
        if value:
            report.add(PASS, "安全头", url, f"{name}: {value}")
        else:
            report.add(WARN, "安全头", url, f"缺少 {name}", advice)

    # ── 信息泄漏 ──
    for leak in ("server", "x-powered-by", "x-aspnet-version"):
        if leak in h:
            report.add(INFO, "信息泄漏", url,
                       f"暴露了 {leak}: {h[leak]}",
                       "生产环境建议隐藏或改写版本信息，减少攻击面探测")

    # ── Cookie 标志 ──
    set_cookie = h.get("set-cookie", "")
    if not set_cookie:
        report.add(INFO, "Cookie", url, "本次响应未下发 Cookie，跳过检查")
    else:
        missing = [flag for flag in ("HttpOnly", "Secure", "SameSite")
                   if flag.lower() not in set_cookie.lower()]
        if missing:
            report.add(FAIL, "Cookie", url,
                       f"Cookie 缺少标志: {', '.join(missing)}",
                       "会话 Cookie 应设为 HttpOnly; Secure; SameSite=Lax; Path=/ "
                       "（注意 HttpOnly 防的是'被 JS 读取'，不能防 XSS 发请求）")
        else:
            report.add(PASS, "Cookie", url, "Cookie 具备 HttpOnly / Secure / SameSite")


# ══════════════════════════════════════════════════════════════════
# 授权守卫：只允许扫本地，或"已声明授权"的目标
# ══════════════════════════════════════════════════════════════════

def is_loopback(host: str) -> bool:
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def guard_target(url: str, authorized: bool) -> str | None:
    """返回错误信息；None 表示允许扫描。"""
    try:
        host = urllib.parse.urlparse(url).hostname or ""
    except ValueError:
        return f"无法解析 URL: {url!r}"
    if not host:
        return f"URL 缺少主机名: {url!r}"
    if is_loopback(host) or authorized:
        return None
    return (f"拒绝扫描非本地目标 {host}：未声明授权。\n"
            "  如果你确实拥有该目标的测试授权（自有资产 / 书面授权 / SRC 范围），\n"
            "  请加 `--authorized` 参数重新运行。\n"
            "  ⚠️ 未经授权对他人系统做安全测试可能违法。")


# ══════════════════════════════════════════════════════════════════
# 输出
# ══════════════════════════════════════════════════════════════════

ICON = {PASS: "✅", WARN: "⚠️ ", FAIL: "❌", INFO: "ℹ️ "}


def print_report(report: Report) -> None:
    print("\n" + "═" * 74)
    print("  扫描结果")
    print("═" * 74)

    grouped: dict[str, list[Finding]] = {}
    for f in report.findings:
        grouped.setdefault(f.category, []).append(f)

    for category, items in grouped.items():
        print(f"\n【{category}】")
        for f in items:
            print(f"  {ICON.get(f.level, '?')} [{f.level}] {f.target}")
            print(f"        {f.detail}")
            if f.evidence:
                print(f"        证据: {f.evidence[:200]}")
            if f.advice and f.level in (WARN, FAIL):
                print(f"        ↳ 建议：{f.advice}")

    c = report.counts()
    print("\n" + "─" * 74)
    print(f"  汇总:  PASS={c[PASS]}  WARN={c[WARN]}  FAIL={c[FAIL]}  INFO={c[INFO]}")
    print("─" * 74)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="本地 XSS 反射检测 + 安全头审计（教学用）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="默认扫描内置本地靶场；扫描外部目标需 --authorized。",
    )
    parser.add_argument("--url", help="目标 URL（默认使用内置本地靶场）")
    parser.add_argument("--param", action="append", default=None,
                        help="要测试的参数名，可重复（默认 q/name/search/query/keyword）")
    parser.add_argument("--timeout", type=float, default=5.0, help="单次请求超时秒数")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出报告")
    parser.add_argument("--authorized", action="store_true",
                        help="声明你已获得目标授权（扫描非回环地址时必须）")
    args = parser.parse_args()

    global PROGRESS
    PROGRESS = not args.json      # --json 时保持 stdout 干净，只输出机器可读报告

    report = Report()
    lab = None
    # targets: [(要测的 URL, 该 URL 上要测的参数名列表), ...]
    targets: list[tuple[str, list[str]]] = []

    try:
        if args.url:
            err = guard_target(args.url, args.authorized)
            if err:
                print(err, file=sys.stderr)
                return 2
            params = args.param or ["q", "name", "search", "query", "keyword"]
            targets = [(args.url, params)]
            base = args.url
            if PROGRESS:
                print(f"目标: {args.url}")
        else:
            # 启动内置靶场：同时包含"有漏洞"和"已修复"的端点，
            # 正好验证扫描器能不能区分两者（能区分，才说明检测逻辑可信）。
            lab, base = start_lab()
            targets = [
                (f"{base}/search", ["q"]),      # 未编码          → 期望 FAIL
                (f"{base}/attr", ["name"]),     # 只转义尖括号    → 期望 WARN
                (f"{base}/safe", ["q"]),        # 正确编码        → 期望 PASS
                (f"{base}/secure", ["q"]),      # 编码 + 安全头   → 期望 PASS
            ]
            if PROGRESS:
                print(f"内置本地靶场已启动: {base}")

        if PROGRESS:
            print("\n开始扫描……")
        for t, params in targets:
            # ① 反射检测（每个参数 × 三种上下文）
            for p in params:
                scan_reflection(report, t, p, args.timeout)
            # ② Sink 扫描 + ③ 安全头审计（对页面本身做一次）
            scan_sinks(report, t, args.timeout)
            scan_headers(report, t, args.timeout)

    finally:
        if lab is not None:
            lab.shutdown()

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print_report(report)
        print("\n📌 判定标准（教学）:")
        print("   FAIL = 未编码/缺少关键防护（应立刻修）")
        print("   WARN = 防护不完整或存在弱点（应排期修）")
        print("   PASS = 该检查项已达标")
        print("   INFO = 仅供参考，不构成结论")
        print("\n💡 提示（反射检测类）：/search 应 FAIL，/attr 应 WARN，/safe 与 /secure 应 PASS。")
        print("   （安全头类里只有 /secure 会 PASS —— 其余端点故意没配安全头。）")
        print("   如果扫描器区分不出这四者的差别，说明检测逻辑本身有问题。")

    c = report.counts()
    code = 1 if c[FAIL] else 0
    if not args.json:
        print(f"\n📤 退出码: {code}（存在 FAIL 时为 1，无条件为 0）")
        print("   这是**设计行为**，不是崩溃：方便直接接到 CI 里当门禁。")
    return code


if __name__ == "__main__":
    sys.exit(main())
