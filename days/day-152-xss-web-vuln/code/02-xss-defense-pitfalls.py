#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 152 · 示例 02：XSS 防护原理与常见坑（进阶用法）
===================================================

目标
----
示例 01 让你看到了"漏洞长什么样"；本示例回答**"怎么修，以及为什么
大部分'看起来在修'的写法其实没修"**。

内容分四块：

    ① 上下文编码器        —— HTML 文本 / 属性 / URL / JS 字符串 四种，各自正确写法
    ② 七个经典坑          —— 每个都给出"错误写法 → 会被怎样绕过 → 正确写法"
    ③ 最小 HTML 净化器    —— 基于 html.parser 的白名单实现（教学用！）
    ④ 安全响应头服务器    —— 真实返回 CSP(nonce) / HttpOnly Cookie / nosniff，
                             并用 urllib 验证它们确实生效

⚠️ 安全声明
-----------
本脚本是**纯防御教学**：所有"攻击字符串"都是用来**验证自己的防护是否失效**
的自测样例（断言用），运行过程只访问 127.0.0.1 上自建的演示服务。
请勿用于未授权目标。

运行
----
    python3 02-xss-defense-pitfalls.py
"""

import argparse
import html
import http.server
import json
import re
import secrets
import sys
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser

W = 68


def banner(title: str) -> None:
    print("\n" + "═" * W)
    print(f"  {title}")
    print("═" * W)


def sub(title: str) -> None:
    print(f"\n── {title} " + "─" * max(0, W - 6 - len(title)))


# ══════════════════════════════════════════════════════════════════
# ① 上下文编码器：四种上下文，四套正确写法
# ══════════════════════════════════════════════════════════════════

def enc_html_text(s: str) -> str:
    """【上下文 1】HTML 文本节点。

    <p>{HERE}</p>
    需要转义：& < >（引号转不转都安全，但转了一劳永逸）
    """
    return html.escape(s, quote=True)


def enc_html_attr(s: str) -> str:
    """【上下文 2】HTML 属性值（**必须加引号**）。

    <input value="{HERE}">
    必须转义引号！否则攻击者用 `"` 闭合属性，凭空造出 on* 事件处理器。
    这就是为什么 html.escape 的 quote 参数默认是 True。
    """
    return html.escape(s, quote=True)


def enc_url_param(s: str) -> str:
    """【上下文 3】URL 的查询参数值。

    <a href="/search?q={HERE}">
    用 percent-encoding。safe='' 表示连 '/' '&' '=' 也一起编码，
    避免参数被"劈成"两个参数（参数注入）。
    """
    return urllib.parse.quote(s, safe="")


def enc_js_string(s: str) -> str:
    """【上下文 4】JS 字符串字面量 —— 最好的答案是**不要拼**。

    ❌ var name = '{HERE}';
    手写 JS 转义极容易漏（要处理 ' " \\ \\n \\r \\u2028 \\u2029</script>）。
    ✅ 项目里的两种正解：
        a) 用 json.dumps() 生成合法 JS 字面量（它转义了控制字符与引号）
        b) 更推荐：把值放到 data-* 属性里，JS 用 dataset 读
           （data 属性走的是"上下文 2"，有 HTML 转义兜底）
    """
    # json.dumps 产出的是合法 JS/JSON 字符串字面量；再额外干掉 U+2028/2029，
    # 因为它们虽然是合法 JSON 字符，但在旧版 JS 里会被当换行符，可用来逃逸。
    out = json.dumps(s, ensure_ascii=False)
    out = out.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    # 再转义 < > & —— 因为这段 JS 通常嵌在 <script> 里，
    # 裸的 "</script>" 会**提前闭合脚本块**，把后面的内容变成 HTML。
    # 用 \u003c 形式既不影响 JS 语义，又让浏览器找不到闭合标签。
    for ch, repl in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        out = out.replace(ch, repl)
    return out


def enc_css_value(s: str) -> str:
    """【上下文 5】CSS 值 —— 基本不该动态化。

    ❌ style="color: {HERE}"
    ✅ 只允许白名单格式（下面用颜色做例子），否则直接丢弃。
    """
    if re.fullmatch(r"#[0-9a-fA-F]{6}", s):
        return s
    return "#000000"          # 不安全的一律回落到默认值


# ══════════════════════════════════════════════════════════════════
# ② 七个经典坑：错误写法 → 为什么没用 → 正确写法
# ══════════════════════════════════════════════════════════════════

# 这些是**自测样例**：用来证明"错误写法拦不住"，不是用于攻击任何东西。
ATTACK_SAMPLES = {
    "闭合属性造事件": '" onmouseover="x152()" autofocus="',
    "标签注入": "<x152probe>",
    "大小写变体": "<ScRiPt>",
    "嵌套绕过": "<scr<script>ipt>",
    "协议伪协议": "javascript:x152()",
    "字符引用": "&#x3c;x152probe&#x3e;",
}


def pitfall_1_blacklist() -> None:
    sub("坑 1：黑名单过滤（replace 掉危险词）")

    def bad_filter(s: str) -> str:
        # ❌ 典型错误写法
        return s.replace("<script>", "").replace("onerror", "")

    sample = "<scr<script>ipt>"
    print(f"  输入: {sample}")
    print(f"  黑名单过滤后: {bad_filter(sample)}")
    print("  → 过滤掉中间的 '<script>' 后，两侧拼起来又是完整的 <script>！")
    print("  ✅ 正确做法：不要做'删除危险词'，做'按上下文编码'。")
    print(f"     编码后: {enc_html_text(sample)}  （任何标签都变成字符）")


def pitfall_2_only_lt() -> None:
    sub("坑 2：只转义 '<' 和 '>'，不管引号")

    sample = ATTACK_SAMPLES["闭合属性造事件"]
    naive = sample.replace("<", "&lt;").replace(">", "&gt;")     # ❌
    correct = html.escape(sample, quote=True)                    # ✅

    print(f"  输入: {sample}")
    print("\n  ❌ 只转义尖括号，放进属性里:")
    print(f'     <input value="{naive}">')
    print('     → 引号是裸的，直接闭合了 value="，后面的 onmouseover 被当属性解析')
    print("\n  ✅ 用 html.escape(quote=True):")
    print(f'     <input value="{correct}">')
    print("     → 引号变成 &#x27; / &quot;，闭不出属性，攻击面消失")


def pitfall_3_quote_false() -> None:
    sub("坑 3：html.escape(s, quote=False) 用在属性上下文")

    sample = ATTACK_SAMPLES["闭合属性造事件"]
    print("  quote=False 只转义 & < >，**保留引号** —— 它只适合 HTML 文本节点。")
    print(f"  文本节点里用它: 安全（引号在文本上下文没有特殊含义）")
    print(f"  属性值里用它:   不安全")
    print(f"     escape(quote=False) → {html.escape(sample, quote=False)}")
    print(f"     escape(quote=True)  → {html.escape(sample, quote=True)}")
    print("  ✅ 记一条规则：**属性值里的数据，永远 quote=True**。别为省事关掉它。")


def pitfall_4_double_encode() -> None:
    sub("坑 4：在'输入处'编码 → 双重编码 + 数据损坏")

    # ❌ 在输入处编码（很多老系统的做法）
    stored = html.escape("A & B <3", quote=True)      # 存进库就是 &amp; 了
    print(f'  用户输入:  "A & B <3"')
    print(f"  ❌ 输入时编码后入库: {stored!r}")
    print("     问题 1：库里存的是**损坏的数据**，导出 Excel / 发邮件时都是 &amp;")
    print("     问题 2：再经过一次输出编码会变成 &amp;amp; → 页面显示 &amp;")
    print("     问题 3：搜索 'A & B' 永远搜不到，因为存的是别的字符串")

    # ✅ 正确：原样存，输出才编码
    print(f"  ✅ 原样入库: 'A & B <3'，输出到 HTML 时再编码 → "
          f"{html.escape('A & B <3', quote=True)}")


def pitfall_5_template_safe() -> None:
    sub("坑 5：模板引擎的 '不转义' 开关（|safe / autoescape off）")

    def render_with_safe(user: str) -> str:
        # 模拟 Jinja2 的 {{ user|safe }}：原样插入，不做转义
        return f"<h2>欢迎 {user}</h2>"

    def render_autoescape(user: str) -> str:
        # 模拟 Jinja2 默认的 {{ user }}：自动转义
        return f"<h2>欢迎 {html.escape(user, quote=True)}</h2>"

    sample = "<x152probe>"
    print(f"  {{% autoescape true %}}（默认）→ {render_autoescape(sample)}")
    print(f"  {{{{ user|safe }}}}（手动关掉）→ {render_with_safe(sample)}")
    print("  ✅ 规则：模板默认**总是开着** autoescape；")
    print("     只有'已经是可信 HTML'的内容（比如净化后的富文本）才允许 |safe，")
    print("     且必须在净化之后立刻标记，中间不能插入新的用户数据。")


def pitfall_6_javascript_url() -> None:
    sub("坑 6：URL 上下文 —— <a href='javascript:...'>")

    def bad_link(url: str) -> str:
        return f'<a href="{html.escape(url, quote=True)}">点我</a>'

    def good_link(url: str) -> str:
        cleaned = "".join(ch for ch in url if ord(ch) > 32)   # 去掉控制字符
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):", cleaned)
        if m and m.group(1).lower() not in {"http", "https", "mailto"}:
            return '<a href="#">点我</a>'                     # 拒绝危险协议
        return f'<a href="{html.escape(url, quote=True)}">点我</a>'

    for sample in ["javascript:x152()", "JaVaScRiPt:x152()", "java\tscript:x152()"]:
        print(f"  输入: {sample!r}")
        print(f"     ❌ 只做 HTML 编码: {bad_link(sample)}")
        print("        （HTML 编码救不了它 —— 'javascript:' 里没有需要转义的字符）")
        print(f"     ✅ 协议白名单:      {good_link(sample)}")
    print("  ✅ 规则：URL 要**两步** —— ① 协议白名单 ② 再做 HTML 属性编码。")


def pitfall_7_innerhtml() -> None:
    sub("坑 7：前端把不可信数据塞进 innerHTML")

    print("  ❌ el.innerHTML = location.hash.slice(1)")
    print("     innerHTML 会把字符串当 HTML 解析 → 元素被真的创建 → 事件被触发")
    print("  ✅ 三种替代：")
    print("     1) el.textContent = data          （纯文本，最常用）")
    print("     2) el.setAttribute('title', data) （属性值，不进解析器）")
    print("     3) 需要富文本时 → 净化库（DOMPurify / nh3）+ 严格 CSP")
    print("  ⚠️ 注意：`el.innerHTML = ''` 清空是安全的；危险的是**赋值非空不可信内容**。")


# ══════════════════════════════════════════════════════════════════
# ③ 最小 HTML 净化器（教学用白名单实现）
# ══════════════════════════════════════════════════════════════════

class MiniSanitizer(HTMLParser):
    """一个**教学用**的 HTML 白名单净化器。

    ⚠️ 生产环境千万不要用自己写的净化器！
       浏览器容错解析的边界情况极多（mXSS、命名空间混淆、模板标签等），
       Python 侧请用成熟库：nh3（Rust 实现，推荐）、bleach（已归档）、
       lxml.html.clean；前端用 DOMPurify。

    实现思路（这才是重点）：
        解析成树 → 逐节点判断 → 白名单外的标签丢弃（但保留其文字）→ 重新序列化
    为什么不能用正则替换？因为浏览器会**容错修补**畸形 HTML，
    正则看到的字符串和浏览器最终构建的 DOM 树不是一回事。
    """

    # 允许保留的标签
    ALLOWED_TAGS = {
        "p", "br", "b", "i", "u", "em", "strong", "code", "pre",
        "ul", "ol", "li", "blockquote", "a", "h1", "h2", "h3",
    }
    # 允许保留的属性（按标签限制，越小越安全）
    ALLOWED_ATTRS = {
        "a": {"href", "title"},
    }
    # URL 属性允许的协议
    ALLOWED_SCHEMES = {"http", "https", "mailto"}
    # 自闭合（void）标签
    VOID_TAGS = {"br", "hr", "img"}
    # 这些标签连同**内容**一起丢弃（脚本、样式、表单、外链资源……）
    DROP_WITH_CONTENT = {"script", "style", "iframe", "object", "embed", "svg", "math"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.stack: list[str] = []
        self._drop_depth = 0        # >0 表示正在丢弃标签的内容
        self.dropped: list[str] = []   # 记录被丢掉了什么，便于自测断言

    # ── 内部：URL 属性协议白名单 ──────────────────────────────
    def _safe_url(self, value: str) -> str | None:
        # 去掉所有 ASCII 控制字符/空白，"java\tscript:" 是经典绕过
        cleaned = "".join(ch for ch in value if ord(ch) > 32)
        m = re.match(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):", cleaned)
        if m and m.group(1).lower() not in self.ALLOWED_SCHEMES:
            return None
        return value.strip()

    # ── HTMLParser 回调 ───────────────────────────────────────
    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        if tag in self.DROP_WITH_CONTENT:
            self._drop_depth += 1          # 连内容一起丢
            self.dropped.append(tag)
            return
        if self._drop_depth:
            return
        if tag not in self.ALLOWED_TAGS:
            self.dropped.append(tag)       # 丢标签，保留文字（安全且不丢信息）
            return

        allowed = self.ALLOWED_ATTRS.get(tag, set())
        kept = []
        for name, value in attrs:
            name = name.lower()
            if name.startswith("on"):          # 事件处理器：一律丢
                self.dropped.append(f"{tag}[{name}]")
                continue
            if name not in allowed:            # 不在白名单：丢
                self.dropped.append(f"{tag}[{name}]")
                continue
            if name in {"href", "src"}:
                value = self._safe_url(value or "")
                if value is None:
                    self.dropped.append(f"{tag}[{name}=危险协议]")
                    continue
            kept.append(f' {name}="{html.escape(value or "", quote=True)}"')

        if tag in self.VOID_TAGS:
            self.out.append(f"<{tag}{''.join(kept)}>")
        else:
            self.out.append(f"<{tag}{''.join(kept)}>")
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)     # 简单处理：当普通开始标签
        if tag.lower() not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.DROP_WITH_CONTENT:
            if self._drop_depth:
                self._drop_depth -= 1
            return
        if self._drop_depth:
            return
        if tag in self.stack:
            # 闭合到最近的同名开始标签（浏览器也是这么容错的）
            while self.stack:
                top = self.stack.pop()
                self.out.append(f"</{top}>")
                if top == tag:
                    break

    def handle_data(self, data: str) -> None:
        if self._drop_depth:
            return
        # 文本一律重新编码 —— 即使它原本是实体，也归一到最安全形式
        self.out.append(html.escape(data, quote=False))

    def handle_comment(self, data: str) -> None:
        # 注释一律丢弃：注释里可以藏 "--> <script>..."，且没有业务价值
        self.dropped.append("comment")

    def result(self) -> str:
        while self.stack:                    # 补全未闭合标签，保证输出合法
            self.out.append(f"</{self.stack.pop()}>")
        return "".join(self.out)


def sanitize(raw_html: str) -> str:
    s = MiniSanitizer()
    s.feed(raw_html)
    s.close()
    return s.result()


# ══════════════════════════════════════════════════════════════════
# ④ 安全响应头服务器：把"配置"也验证一遍
# ══════════════════════════════════════════════════════════════════

class SecureHandler(http.server.BaseHTTPRequestHandler):
    """一个配置了基础安全头的演示服务器。

    每次响应生成一个**新的 nonce**，同时写进 CSP 头和页面里的 <script nonce>。
    这样即使页面某处漏了编码，注入的 <script> 也没有正确 nonce → 浏览器拒绝执行。
    """

    server_version = "SecureDemo/1.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        nonce = secrets.token_urlsafe(16)
        # ⚠️ 注意：nonce 用 secrets 生成（密码学安全），不要用 random
        csp = (
            "default-src 'self'; "
            f"script-src 'nonce-{nonce}' 'strict-dynamic'; "
            "object-src 'none'; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'"
        )

        body = (
            "<!DOCTYPE html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<title>安全演示</title></head>\n<body>\n"
            "<h1>这是一个配置了安全头的页面</h1>\n"
            f'<script nonce="{nonce}">document.title = "nonce 生效";</script>\n'
            "</body></html>\n"
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Security-Policy", csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        # 会话 Cookie 三件套：HttpOnly（JS 读不到）+ Secure（只走 HTTPS）
        # + SameSite=Lax（跨站请求不带，削弱 CSRF）
        self.send_header(
            "Set-Cookie",
            "session=x152-demo-value; HttpOnly; Secure; SameSite=Lax; Path=/",
        )
        self.end_headers()
        self.wfile.write(body)


def start_server(handler) -> tuple[http.server.ThreadingHTTPServer, int]:
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


# ══════════════════════════════════════════════════════════════════
# 主流程：先讲坑，再做自测断言，最后验证真实响应头
# ══════════════════════════════════════════════════════════════════

def demo_pitfalls() -> None:
    banner("② 七个经典坑（错误写法 → 会被怎样绕过 → 正确写法）")
    pitfall_1_blacklist()
    pitfall_2_only_lt()
    pitfall_3_quote_false()
    pitfall_4_double_encode()
    pitfall_5_template_safe()
    pitfall_6_javascript_url()
    pitfall_7_innerhtml()


class _SelfTest:
    """极简断言收集器：把「期望 vs 实际」都记下来，最后一次性汇报。

    【为什么不用 assert？】
      1) `python3 -O` 会把 assert 整条优化掉 —— 质量检查不能建在这上面；
      2) assert 在第一个失败点就抛异常，看不到"一共有几处不对"。
    收集式自测能一次给出全貌，失败时明确打印期望值与实际值。
    """

    def __init__(self) -> None:
        self.total = 0
        self.failures: list[str] = []

    def check(self, label: str, ok: bool, expect: str, actual: str) -> None:
        self.total += 1
        if ok:
            print(f"   ✅ {label}")
        else:
            self.failures.append(label)
            print(f"   ❌ {label}")
            print(f"        期望: {expect}")
            print(f"        实际: {actual}")

    def eq(self, label: str, actual, expect) -> None:
        self.check(label, actual == expect, repr(expect), repr(actual))

    def contains(self, label: str, haystack: str, needle: str) -> None:
        self.check(label, needle in haystack, f"包含 {needle!r}", _clip(haystack))

    def absent(self, label: str, haystack: str, needle: str) -> None:
        self.check(label, needle not in haystack, f"不包含 {needle!r}", _clip(haystack))


def _clip(text: str, limit: int = 160) -> str:
    """把长文本压成一行并截断，避免自测失败时刷屏。"""
    flat = " ".join(str(text).split())
    return repr(flat[:limit] + ("…" if len(flat) > limit else ""))


class _SanitizedOutputChecker(HTMLParser):
    """把"净化后的 HTML"再解析一遍，找出其中残留的**可执行结构**。

    判据有三条（任何一条命中都算不安全）：
        ① 出现了白名单之外的标签（含 script / iframe / svg / object …）；
        ② 出现了 on* 事件处理器属性，或该标签不允许的属性；
        ③ href/src 用了 http/https/mailto 之外的协议（javascript: / data: …）。
    注意：`handle_data` 收到的文本即使写着 "onerror=" 也只是**文本**，不算命中 ——
    这正是"要看解析结果、不要看字符串"的原因。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.bad: list[str] = []

    def _inspect(self, tag: str, attrs: list) -> None:
        tag = tag.lower()
        if tag not in MiniSanitizer.ALLOWED_TAGS:
            self.bad.append(f"非白名单标签 <{tag}>")
            return
        allowed = MiniSanitizer.ALLOWED_ATTRS.get(tag, set())
        for name, value in attrs:
            name = name.lower()
            if name.startswith("on"):
                self.bad.append(f"事件处理器属性 <{tag} {name}>")
            elif name not in allowed:
                self.bad.append(f"越权属性 <{tag} {name}>")
            elif name in {"href", "src"} and value:
                cleaned = "".join(ch for ch in value if ord(ch) > 32).lower()
                scheme = cleaned.split(":", 1)[0] if ":" in cleaned else ""
                if scheme and scheme not in MiniSanitizer.ALLOWED_SCHEMES:
                    self.bad.append(f"危险协议 {cleaned!r}")

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self._inspect(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self._inspect(tag, attrs)


def _scan_for_executable(html_text: str) -> list[str]:
    """返回净化结果里残留的可执行结构列表（空列表 = 安全）。"""
    checker = _SanitizedOutputChecker()
    checker.feed(html_text)
    checker.close()
    return checker.bad


def self_test() -> int:
    """离线自测：验证"编码 / 净化"是不是真的按预期工作。返回失败项数量。

    【为什么自测不需要起 HTTP 服务？】
    因为它验证的全部是**纯函数**（编码器、净化器、CSS 白名单），
    没有 socket、没有文件、没有第三方依赖，所以：
        · 任何环境都能跑（包括没网的 CI、容器、沙箱）；
        · 结果**完全确定**，不会因为端口占用/防火墙而随机失败；
        · 毫秒级返回，可以放在每次提交前跑。
    "响应头是否真的下发到浏览器" 那部分由 demo_headers() 在**默认运行**里验证，
    两者分工：**自测证明逻辑，演示证明链路**。
    """
    banner("③ 自测（--self-test 复用的同一套断言）：防护是否真的生效")

    t = _SelfTest()

    # ══ 测试 A：四种上下文的编码器 ═══════════════════════════════
    sub("测试 A：上下文编码器 —— 编码后不能再出现该上下文里的危险字符")
    for name, fn, forbidden in [
        ("HTML 文本（含引号一起转义）", enc_html_text, "<>\""),
        ("HTML 属性值（引号必须转义）", enc_html_attr, "<>\""),
        ("URL 查询参数（percent-encoding）", enc_url_param, "<>\""),
        # ⚠️ JS 上下文特殊：json.dumps 产出的字面量**两端必须带引号**，
        #    所以这里只禁止裸的 < 和 >（它们能提前闭合 </script>）。
        ("JS 字符串字面量（JSON 转义 + 硬编码转义）", enc_js_string, "<>"),
    ]:
        bad: list[tuple[str, str]] = []
        for sample_name, sample in ATTACK_SAMPLES.items():
            out = fn(sample)
            hit = [ch for ch in forbidden if ch in out]
            if hit:
                bad.append((sample_name, f"残留 {hit} → {out!r}"))
        t.check(f"{name}：{len(ATTACK_SAMPLES)} 个样本均无危险字符残留",
                not bad,
                "全部样本编码后不含 " + forbidden,
                "；".join(f"{n}: {d}" for n, d in bad) if bad else "无残留")

    # 属性上下文专项：引号必须被编码（否则闭合引号造事件处理器）
    attr_out = enc_html_attr(ATTACK_SAMPLES["闭合属性造事件"])
    t.absent('属性编码把 " 变成实体（攻击者无法闭合 value="）', attr_out, '"')
    t.contains('属性编码结果里出现 &quot;', attr_out, "&quot;")

    # URL 上下文专项：& 和 = 也必须编码，否则会被"劈成"两个参数
    t.eq("URL 编码把 & 转义（防参数注入）",
         enc_url_param("a&b=c"), "a%26b%3Dc")
    t.eq("URL 编码把空格转成 %20", enc_url_param("a b"), "a%20b")
    t.eq("URL 编码把 / 也编码（safe='' 的用意）", enc_url_param("a/b"), "a%2Fb")

    # JS 上下文专项：既要"不能提前闭合 <script>"，又要"数据不走样"
    js_sample = "</script><img src=x onerror=x152()>"
    js_out = enc_js_string(js_sample)
    t.absent("JS 字面量里没有裸的 </script>（不会提前闭合脚本块）", js_out, "</script>")
    t.contains("危险字符改用 \\u003c 形式表达", js_out, "\\u003c")
    t.eq("JS 编码后仍可用 json.loads 还原出原始数据（无损，不是「洗掉」）",
         json.loads(js_out), js_sample)
    t.eq("U+2028 / U+2029 被显式转义（旧 JS 引擎会把它们当换行，可用来逃逸）",
         enc_js_string("a\u2028b").count("\\u2028"), 1)

    # CSS 上下文专项
    sub("测试 C：CSS 值只允许白名单格式")
    t.eq("合法 6 位十六进制颜色原样保留", enc_css_value("#1a2b3c"), "#1a2b3c")
    t.eq("大写十六进制也合法", enc_css_value("#AABBCC"), "#AABBCC")
    for bad_css in ["red; } body{", "#12345", "expression(alert(1))", "#gggggg"]:
        t.eq(f"非法 CSS 值回落默认色: {bad_css!r}",
             enc_css_value(bad_css), "#000000")

    # ══ 测试 B：白名单净化器 ═════════════════════════════════════
    sub("测试 B：HTML 净化器（白名单）行为")
    cases = [
        # (输入, 必须出现, 必须不出现, 说明)
        ("<b>加粗</b>", "<b>加粗</b>", None, "白名单标签保留"),
        ("<script>x152()</script>你好", "你好", "<script>", "script 连内容一起丢"),
        ('<a href="javascript:x152()">链接</a>', "<a", "javascript:",
         "危险协议被拒绝"),
        ('<img src=x onerror="x152()">', "", "onerror",
         "img 不在白名单 → 整标签丢弃（含事件处理器）"),
        ("<p onclick='x152()'>点我</p>", "<p>点我</p>", "onclick",
         "事件处理器属性一律丢弃"),
        ("<!-- 注释 -->正文", "正文", "<!--", "注释一律丢弃"),
        ("<iframe src='//evil.example'></iframe>安全", "安全", "iframe",
         "iframe 连内容一起丢"),
        ('<a href="https://ok.example/" title="t">好链接</a>',
         'href="https://ok.example/"', None, "合法链接保留"),
        ("<b>半开的标签", "<b>半开的标签</b>", None, "未闭合标签被补全（输出始终合法）"),
        ("&lt;script&gt;", "&lt;script&gt;", "<script>",
         "实体化的输入不会被「复活」成真标签"),
        ("<div><script>坏</script>安全文字</div>", "安全文字", "script",
         "嵌套在允许标签里的 script 依然被丢弃"),
        ("<svg><script>x152()</script></svg>ok", "ok", "svg",
         "svg/math 等外来命名空间整体丢弃（mXSS 常见入口）"),
        ('<a href="java\tscript:x152()">带制表符</a>', "<a", "javascript:",
         "协议解析前先剥掉控制字符（java\\tscript: 是经典绕过）"),
    ]
    for src_html, must_have, must_not, why in cases:
        out = sanitize(src_html)
        ok = must_have in out and (must_not is None or must_not not in out)
        t.check(f"净化 {why}: {src_html!r}",
                ok,
                f"含 {must_have!r}" + (f" 且不含 {must_not!r}" if must_not else ""),
                f"{out!r}")

    # 语料级断言：不靠字符串匹配，而是**把净化结果再解析一遍**找可执行结构。
    # 【为什么这样更可靠？】字符串里出现 "onmouseover=" 未必是属性（可能只是文本），
    # 而"解析后是否存在事件处理器属性 / 非白名单标签 / 危险协议"才是真正的判据。
    leftovers = []
    for name, sample in ATTACK_SAMPLES.items():
        out = sanitize(sample)
        leftovers += [f"{name} → {item}" for item in _scan_for_executable(out)]
    t.check("所有攻击样本净化后：再解析也不含可执行结构（事件属性/非白名单标签/危险协议）",
            not leftovers, "无残留", "；".join(leftovers) if leftovers else "无残留")

    # 定式（幂等）属性：净化器的输出再净化一次必须一模一样 —— 否则说明
    # "净化后的内容"还有第二遍才消失的东西，不能直接当可信 HTML 使用。
    non_idempotent = []
    for name, sample in ATTACK_SAMPLES.items():
        once = sanitize(sample)
        twice = sanitize(once)
        if once != twice:
            non_idempotent.append(f"{name}: 第一次 {once!r} ≠ 第二次 {twice!r}")
    t.check("净化是幂等的（净化输出再净化不变 → 可以直接标记为可信 HTML）",
            not non_idempotent, "两次结果相同",
            "；".join(non_idempotent) if non_idempotent else "相同")

    # ══ 汇总 ═════════════════════════════════════════════════════
    print(f"\n   断言总数: {t.total}，失败: {len(t.failures)}")
    return len(t.failures)


def demo_headers() -> None:
    banner("④ 真实响应头验证：配置写了 ≠ 浏览器收到了")

    httpd, port = start_server(SecureHandler)
    url = f"http://127.0.0.1:{port}/"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "x152-demo"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            headers = resp.headers
            body = resp.read().decode("utf-8")

        sub("服务端返回的安全头")
        for name in [
            "Content-Security-Policy", "X-Content-Type-Options",
            "X-Frame-Options", "Referrer-Policy", "Permissions-Policy",
            "Set-Cookie",
        ]:
            print(f"   {name}: {headers.get(name)}")

        sub("逐项判定")
        csp = headers.get("Content-Security-Policy", "")
        checks = [
            ("CSP 存在", bool(csp)),
            ("CSP 不含 unsafe-inline", "unsafe-inline" not in csp),
            ("CSP 含 nonce", "'nonce-" in csp),
            ("CSP 限制 object-src", "object-src" in csp),
            ("CSP 限制 base-uri", "base-uri" in csp),
            ("CSP 限制 frame-ancestors", "frame-ancestors" in csp),
            ("nosniff", headers.get("X-Content-Type-Options") == "nosniff"),
            ("X-Frame-Options", headers.get("X-Frame-Options") == "DENY"),
            ("Referrer-Policy 存在", bool(headers.get("Referrer-Policy"))),
        ]
        cookie = headers.get("Set-Cookie", "")
        checks += [
            ("Cookie HttpOnly", "HttpOnly" in cookie),
            ("Cookie Secure", "Secure" in cookie),
            ("Cookie SameSite", "SameSite=" in cookie),
        ]
        for name, ok in checks:
            print(f"   {'✅' if ok else '❌'} {name}")

        sub("nonce 是否真的写进了页面")
        has_nonce_in_html = "<script nonce=" in body
        print(f"   {'✅' if has_nonce_in_html else '❌'} "
              f"页面里存在 <script nonce=...>（与响应头一致才能执行）")
        print("\n   ⚠️ 关键认知：CSP 的 nonce 必须**每次响应都不同**。")
        print("      若把 nonce 写成固定值，攻击者读一次页面就知道了，等于没写。")

    finally:
        httpd.shutdown()


def conclusion() -> None:
    banner("小结：XSS 防护清单（按优先级）")
    print("""
1. 【根治】输出编码：按上下文（HTML/属性/URL/JS/CSS）编码，属性值永远加引号
2. 【根治】不要拼 HTML：用 DOM API / 模板引擎自动转义，禁用 |safe
3. 【前端】不可信数据永远不进 innerHTML/document.write/eval
4. 【富文本】解析 + 白名单净化（用成熟库），禁止 script/style/on*
5. 【兜底】CSP：nonce + strict-dynamic，禁 unsafe-inline，限制 base-uri/object-src
6. 【兜底】Cookie：HttpOnly + Secure + SameSite（注意 HttpOnly 防读不防用）
7. 【兜底】响应头：nosniff / X-Frame-Options / Referrer-Policy
8. 【流程】输入校验管"合法性"，输出编码管"安全性"，两件事都要做且互不替代
""")


def demo() -> None:
    """默认运行：完整教学演示。

    顺序是刻意安排的：先看**错误的做法**（坑），再用自测断言证明
    **正确的做法真的有效**，最后把"配置"落到真实的 HTTP 响应头上验证。
    """
    demo_pitfalls()
    failures = self_test()
    demo_headers()
    conclusion()

    print(f"自测失败项合计: {failures}（0 表示全部通过）")
    if failures:
        print("⚠️ 有失败项：请回看上面带 ❌ 的断言，它打印了「期望 vs 实际」。")


def main(argv: list[str] | None = None) -> int:
    """命令行入口。

        python3 02-xss-defense-pitfalls.py              → 完整演示（含回环服务）
        python3 02-xss-defense-pitfalls.py --self-test  → 纯离线自测
    """
    parser = argparse.ArgumentParser(
        description="Day 152 示例 02：XSS 防护原理、常见坑与最小净化器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 02-xss-defense-pitfalls.py              # 完整演示\n"
            "  python3 02-xss-defense-pitfalls.py --self-test  # 离线自测，输出 SELF-TEST OK\n"
        ),
    )
    parser.add_argument("--self-test", action="store_true",
                        help="只跑离线自测（纯函数断言，无网络、无第三方依赖）")
    args = parser.parse_args(argv)

    if args.self_test:
        failures = self_test()
        print()
        if failures:
            print(f"❌ SELF-TEST FAILED：{failures} 项断言未通过"
                  "（请回看上面打印的「期望 / 实际」）")
            return 1
        print("✅ SELF-TEST OK（全部断言通过；离线运行，无 sudo、无第三方依赖）")
        return 0

    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
