#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Day 152 · 示例 01：三种 XSS 的最小复现（基础用法）
===================================================

目标
----
用**纯标准库**在本地（127.0.0.1）起一个 HTTP 演示服务，把 XSS 的三种形态
真实地跑一遍，并且**同时给出"危险写法"和"安全写法"的响应体对比**，
让你亲眼看到"数据变成代码"的那一刻到底发生了什么。

⚠️ 安全声明
-----------
本脚本是**防御教学**用：服务只绑定 127.0.0.1（本机），演示用的"payload"
只是一个无害标记串（不含任何真实攻击代码），它唯一的作用是让我们能观察到
"字符串被原样输出"还是"被编码后输出"。
请勿把这里的技术用于任何未授权的真实目标。

为什么不用 Flask / Django？
--------------------------
因为我们想看清楚"模板引擎到底替我们做了什么"。框架的自动转义是**好事**，
但它把 XSS 的成因藏起来了——只有亲手写一次原始拼接，你才会知道
"为什么生产环境绝不能手写 HTML 字符串"。

运行
----
    python3 01-xss-types-basics.py

阅读顺序
--------
    ① 存储层 / 工具函数        —— 原始数据必须原样存
    ② DemoHandler             —— 三种 XSS 的三个端点
    ③ simulate_dom_sinks()    —— DOM 型 XSS 的语义模拟器（不执行脚本）
    ④ main()                  —— 用 urllib 真实请求，打印原始响应体
"""

import argparse
import html
import http.server
import re
import sys
import threading
import urllib.parse
import urllib.request
from html.parser import HTMLParser

# ══════════════════════════════════════════════════════════════════
# ① 存储层：存储型 XSS 的"数据库"（内存版）
# ══════════════════════════════════════════════════════════════════

# ⚠️ 关键设计：这里**原样保存**用户输入，不做任何"清洗"。
#    原因见 README 2.2：同一条数据可能要去往 HTML / JSON / 邮件多个出口，
#    在**输入处**清洗会永久损坏数据，而且换了出口仍然不安全。
#    ✅ 正确做法：原样存 → 在**每个输出位置**按上下文编码。
GUESTBOOK: list[str] = []

# 本次演示用的"无害探测标记"：不含脚本、不含事件处理器，纯粹为了看它被怎么输出
PROBE = "<x152probe>"

BANNER_WIDTH = 68


def esc(s: str) -> str:
    """HTML 输出编码：把 & < > " ' 变成实体。

    quote=True 非常重要——属性上下文里，攻击者靠闭合引号来"造出"新属性，
    只转义尖括号是拦不住的。
    """
    return html.escape(s, quote=True)


def banner(title: str) -> None:
    print("\n" + "═" * BANNER_WIDTH)
    print(f"  {title}")
    print("═" * BANNER_WIDTH)


def show(label: str, text: str, limit: int = 420) -> None:
    """打印一段可能很长的文本，超长就截断（避免刷屏）。"""
    print(f"\n--- {label} ---")
    if len(text) > limit:
        print(text[:limit] + f"\n…（共 {len(text)} 字符，已截断）")
    else:
        print(text)


# ══════════════════════════════════════════════════════════════
# ①-b 渲染层：把「响应体长什么样」从 HTTP 处理里抽出来（纯函数）
# ══════════════════════════════════════════════════════════════
# 【为什么要把这几段 HTML 构造抽成独立函数？】
#   1) 可测试：纯函数没有 socket、没有 self，`--self-test` 可以在**完全离线**
#      的环境里断言「危险版真的原样输出」「安全版真的编码了」；
#   2) 单一职责：Handler 只负责"收包 / 发包"，"渲染"是另一件事；
#   3) 分岔点一目了然：每个函数里**只有一处** `if safe`，漏洞与修复都在那一行。
#
# ⚠️ 真实的框架（Django/Jinja2）就是把这个"渲染层"做成了模板引擎，
#    并默认对所有变量做自动转义。这里手写，是为了让 XSS 的成因无处藏身。

def render_reflect(user_input: str, safe: bool) -> str:
    """构造 `/reflect` 的响应体。`safe` 是危险版/安全版的**唯一**分岔点。

    注意这段 HTML 同时踩了两个上下文：
        · <div>…</div>           → HTML 文本上下文
        · <input value="…">      → HTML 属性上下文（引号必须一起编码！）
    同一份数据、同一个出口页面，两个上下文要的是**同一种**编码（html.escape），
    但只要漏掉引号（quote=False），属性那个位置就破了。
    """
    if safe:
        rendered = esc(user_input)           # ✅ 输出前按上下文编码
        label = "✅ safe=1 —— 已做 HTML 输出编码（html.escape）"
    else:
        rendered = user_input                # ❌ 危险：原始字节直接进 HTML
        label = "❌ safe=0 —— 原始拼接，未做任何编码"

    return (
        f"<h1>搜索结果</h1>\n"
        f"<p>{label}</p>\n"
        f'<div class="search">你搜索了：{rendered}</div>\n'
        # 顺便演示"属性上下文"：属性值必须加引号，且同样要编码
        f'<input type="text" name="q" value="{rendered}">\n'
    )


def render_guestbook(items: list[str], safe: bool) -> str:
    """构造 `/guestbook` 的响应体。`items` 是"数据库"里存着的**原文**。

    这里刻意体现"存储型 XSS 的锅在输出、不在存储"：
    同一个 items 列表，safe=False 时所有访客都会中招，safe=True 时一切正常。
    数据库里的数据始终没变 —— 这正是不应该在输入处做清洗的原因（见 README 2.2）。
    """
    rendered_items = []
    for i, text in enumerate(items, 1):
        shown = esc(text) if safe else text      # ← 唯一的分岔点
        rendered_items.append(f"<li>#{i}: {shown}</li>")

    if not rendered_items:
        rendered_items.append("<li>（还没有留言）</li>")

    mode = "✅ safe=1 输出已编码" if safe else "❌ safe=0 输出未编码"
    return (
        f"<h1>留言板（{mode}）</h1>\n"
        f"<ul>\n" + "\n".join(rendered_items) + "\n</ul>\n"
    )


def render_dom_page() -> str:
    """构造 `/dom` 的页面。

    危险写法**只写在 HTML 注释里**，页面真正执行的脚本用的是 textContent。
    这样既讲清了机制，又不会真的在本机留下一个可利用的 DOM 型 XSS 页面 ——
    教学靶场也不该给未来翻到这些代码的人埋雷。
    """
    return """<h1>DOM 型 XSS 演示页</h1>
<p>这个页面会把 URL 的 <code>#</code> 后面内容渲染到下面的 div 里。</p>
<div id="out">（等待渲染）</div>
<!--
  ❌ 危险写法（教学演示，本脚本不会执行它）：
      document.getElementById('out').innerHTML = decodeURIComponent(location.hash.slice(1));
  因为 innerHTML 把字符串当 **HTML** 解析，所以 URL 里带的标签会被真的创建出来，
  其中的事件处理器一旦被触发就会执行脚本。

  ✅ 安全写法：用 textContent，它把字符串当**纯文本**，永远不解析标签。
-->
<script>
  // 本演示页用的是安全写法，避免产生可被利用的页面：
  document.getElementById('out').textContent =
      decodeURIComponent(location.hash.slice(1) || '（没有 fragment）');
</script>"""


def page(title: str, body: str) -> str:
    """包一层最简单的 HTML 外壳。"""
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{title}</title></head>\n<body>\n{body}\n</body></html>\n"
    )


# ══════════════════════════════════════════════════════════════════
# ② 演示服务器：三个端点对应三种 XSS
# ══════════════════════════════════════════════════════════════════

class DemoHandler(http.server.BaseHTTPRequestHandler):
    """一个"故意有漏洞"的教学服务器。

    它提供两个开关（safe=0/1），用来对比"危险写法"与"安全写法"的响应差异。
    真实世界不会给你这个开关，所以本脚本只用于理解机制。
    """

    server_version = "XssDemo/1.0"

    # 默认的日志会打到 stderr，本演示里我们自己打印，所以静音
    def log_message(self, fmt: str, *args) -> None:
        pass

    # ── 响应工具 ──────────────────────────────────────────────
    def _send(self, body: bytes, ctype: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        # 教学服务器不加 CSP，这样才能演示"编码缺失会怎样"。
        # 生产环境应该在这里加 Content-Security-Policy（见示例 02）。
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, body: str, status: int = 200) -> None:
        self._send(body.encode("utf-8"), "text/html; charset=utf-8", status)

    def _send_text(self, body: str, status: int = 200) -> None:
        self._send(body.encode("utf-8"), "text/plain; charset=utf-8", status)

    # ── 路由 ─────────────────────────────────────────────────
    def do_GET(self) -> None:  # noqa: N802 （http.server 规定的方法名）
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        q = urllib.parse.parse_qs(parsed.query)
        safe = q.get("safe", ["0"])[0] == "1"

        if path == "/":
            self._handle_index()
        elif path == "/reflect":
            self._handle_reflect(q, safe)
        elif path == "/guestbook":
            self._handle_guestbook(safe)
        elif path == "/dom":
            self._handle_dom()
        else:
            self._send_text("404 not found", status=404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/guestbook":
            self._send_text("404 not found", status=404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        form = urllib.parse.parse_qs(raw)

        # ✅ 存的时候**原样存**。存储型 XSS 的锅不在"存"，在"输出"。
        GUESTBOOK.append(form.get("text", [""])[0])

        body = "<h1>留言成功</h1><p>共 " + str(len(GUESTBOOK)) + " 条留言。</p>"
        body += '<p><a href="/guestbook">去看留言板</a></p>'
        self._send_html(page("留言成功", body))

    # ── 端点 1：反射型 ────────────────────────────────────────
    def _handle_reflect(self, q: dict, safe: bool) -> None:
        """反射型 XSS：把**本次请求参数**直接拼进 HTML。

        '反射'的意思是：payload 像镜子一样进来又立刻弹回去，不落库。
        修复只需要改这一处代码，所以它比存储型好修。

        【这个方法"很薄"是刻意的】它只做两件事：从 query 里取值、
        交给 render_reflect 渲染。于是"HTTP 处理"和"HTML 渲染"能被分开测试，
        这也是真实框架"路由 / 模板"分层的缩影。
        """
        user_input = q.get("q", [""])[0]
        self._send_html(page("搜索", render_reflect(user_input, safe)))

    # ── 端点 2：存储型 ────────────────────────────────────────
    def _handle_guestbook(self, safe: bool) -> None:
        """存储型 XSS：把**数据库里读出来的**内容拼进 HTML。

        和反射型的唯一区别是数据来源：一个是"这次的请求参数"，
        一个是"之前存进去的数据"。但后果完全不同——每个访问者都会中招。
        """
        self._send_html(page("留言板", render_guestbook(GUESTBOOK, safe)))

    # ── 端点 3：DOM 型 ────────────────────────────────────────
    def _handle_dom(self) -> None:
        """DOM 型 XSS：服务器**完全没有参与**。

        响应体里不含任何用户数据 —— 危险发生在浏览器本地：前端 JS 把
        location.hash 写进了危险信宿。fragment 不会随请求发给服务器，所以
        服务端日志、WAF、服务端输出编码，一个都救不了它。
        """
        self._send_html(page("DOM 型演示", render_dom_page()))


# ══════════════════════════════════════════════════════════════════
# ③ DOM sink 语义模拟器：不执行脚本，只把"会被解析成什么"打印出来
# ══════════════════════════════════════════════════════════════════

class ElementCollector(HTMLParser):
    """收集一段 HTML 片段里的标签与属性。

    用途：模拟 innerHTML 的语义 —— "这段字符串会被浏览器建造成什么节点"。
    我们只**观察结构**，不渲染、不执行任何东西。
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[tuple[str, list[tuple[str, str]]]] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        self.elements.append((tag, [(k, v or "") for k, v in attrs]))

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self.handle_starttag(tag, attrs)


def simulate_dom_sinks(payload: str) -> None:
    """对比同一个字符串在 innerHTML 与 textContent 下的不同命运。"""
    print(f"\n输入字符串（来自 location.hash，永远不会发给服务器）:\n  {payload!r}")

    # ── innerHTML 语义：解析成 DOM 节点 ──
    parser = ElementCollector()
    parser.feed(payload)
    print("\n  ▶ innerHTML 语义（把字符串当 HTML 解析）:")
    if not parser.elements:
        print("     没有解析出任何元素 —— 它只是一段文本")
    for tag, attrs in parser.elements:
        print(f"     创建元素 <{tag}>")
        for k, v in attrs:
            danger = "  ⚠️ 事件处理器，一触发就执行代码！" if k.startswith("on") else ""
            print(f"        属性 {k}={v!r}{danger}")

    # ── textContent 语义：全部当纯文本 ──
    print("\n  ▶ textContent 语义（把字符串当纯文本）:")
    print(f"     页面上原样显示文本: {payload}")
    print("     ✅ 不创建任何元素、不解释任何属性 → DOM 型 XSS 消失")

    print("\n  结论：同一个字符串，进 innerHTML 是'代码'，进 textContent 是'文本'。")
    print("        前端的安全防线，本质就是'给字符串选对信宿(sink)'。")


# ══════════════════════════════════════════════════════════════════
# ④ 客户端工具：启动服务 + 真实请求
# ══════════════════════════════════════════════════════════════════

def start_server() -> tuple[http.server.ThreadingHTTPServer, int]:
    """在 127.0.0.1 的**随机空闲端口**上启动演示服务。

    端口写 0 = 让操作系统分配一个空闲端口，避免撞端口。
    只用 127.0.0.1 绑定 = 只有本机能访问，不会把漏洞暴露到局域网。
    """
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def get(url: str) -> str:
    """发一个 GET，返回响应体文本。"""
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.read().decode("utf-8")


def post_form(url: str, data: dict) -> str:
    """发一个 form-urlencoded POST，返回响应体文本。"""
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.read().decode("utf-8")


def demo() -> None:
    httpd, port = start_server()
    base = f"http://127.0.0.1:{port}"
    print(f"演示服务已启动: {base}  （只监听本机，用完即关）")

    # ── ① 反射型：同一条输入，两种输出 ──────────────────────
    banner("① 反射型 XSS：输入 → 立刻反射回来")

    query = urllib.parse.urlencode({"q": f"苹果 {PROBE}"})
    vuln = get(f"{base}/reflect?{query}&safe=0")
    safe = get(f"{base}/reflect?{query}&safe=1")

    show("危险版响应体（safe=0）：标记原样出现 = 浏览器会把它当标签解析",
         vuln)
    show("安全版响应体（safe=1）：标记被编码为实体 = 浏览器只显示字符",
         safe)

    print("\n🔍 观察点：")
    print(f"   危险版里出现了裸的 {PROBE}  → 它在浏览器眼里是一个'元素'")
    print(f"   安全版里出现的是 &lt;x152probe&gt; → 它只是一串字符")
    print("   同一个端点、同一份数据，差别只在'输出前有没有编码'。")

    # ── ② 存储型：写一次，所有访客都中招 ────────────────────
    banner("② 存储型 XSS：写一次，污染所有后续访客")

    post_form(f"{base}/guestbook", {"text": f"第一条留言 {PROBE}"})
    post_form(f"{base}/guestbook", {"text": "大家好，我是正常用户"})

    visitor_a = get(f"{base}/guestbook?safe=0")
    visitor_b = get(f"{base}/guestbook?safe=1")

    print("\n访客 A 看到的（服务端未编码）：")
    for line in visitor_a.splitlines():
        if "probe" in line or "留言" in line and "<li>" in line:
            print("   " + line.strip())
    show("访客 A 的原始响应片段", visitor_a)

    print("\n访客 B 看到的（服务端已编码）：")
    show("访客 B 的原始响应片段", visitor_b)

    print("\n🔍 观察点：")
    print("   payload 只在'提交'时出现过一次，之后每个访问 /guestbook 的人都会看到它。")
    print("   → 这就是存储型比反射型严重的地方：不需要社工，受害者只是正常访问。")
    print("   → 注意数据库里存的仍是原文，安全版是**输出时**才编码的。")

    # ── ③ DOM 型：服务器全程不知情 ───────────────────────────
    banner("③ DOM 型 XSS：服务器完全无辜")

    dom_page = get(f"{base}/dom")
    show("服务端返回的页面（注意其中的 JS sink 说明）", dom_page)

    print("\n🧪 前端 sink 语义模拟（真的执行 JS 需要浏览器，这里只模拟解析结果）")
    simulate_dom_sinks(f"{PROBE}")

    print("\n🔍 观察点：")
    print("   fragment（# 后面的内容）**不会被浏览器发送给服务器**。")
    print("   所以这条路径上：服务端日志看不到、WAF 拦不到、服务端编码管不着。")
    print("   唯一的修复位置是客户端 JS —— 换 sink（textContent / createElement）。")

    # ── 收尾 ─────────────────────────────────────────────────
    banner("小结")
    print("""
• 反射型：数据源是**本次请求参数**，不落库，改一处输出代码即可修复
• 存储型：数据源是**数据库**，一次注入影响所有访客，危害最大
• DOM 型：数据源是**浏览器本地**（location/referrer/postMessage），
          服务端从头到尾没见过它 → 必须在客户端修
• 三者共享同一个根因：**数据与代码的边界被打破**
• 统一修复原则：**在数据进入输出位置的那一刻，按该上下文正确编码**
• 存的时候原样存，输出的时候才编码 —— 不要把两件事混在一起
""")

    httpd.shutdown()
    print("演示服务已关闭。")


# ══════════════════════════════════════════════════════════════
# ⑤ 自测（--self-test）：完全离线、确定性、零依赖
# ══════════════════════════════════════════════════════════════
# 【为什么自测不启动 HTTP 服务？】
#   `--self-test` 的定位是"任何环境里都能一秒跑完的回归检查"：
#   不建 socket、不联网、不需要 sudo、不需要第三方库，因此结果**必然确定**。
#   被验证的"渲染逻辑"和"DOM 语义模拟"本来就是纯函数，完全可以在内存里断言。
#   真实的 HTTP 往返由默认运行（`python3 01-xss-types-basics.py`）负责演示。
#   两者分工明确：**自测证明逻辑正确，演示证明端到端可用。**

class _SelfTest:
    """极简断言收集器：把"期望 vs 实际"都记下来，最后一次性汇报。

    【为什么不用 assert？】
      1) `python3 -O` 会把所有 assert 优化掉 —— 安全/质量检查不能建在这上面；
      2) assert 会在第一个失败点抛异常，看不到"一共有几处不对"。
    收集式自测能一次给出全貌，并且失败时清楚打印"期望值 vs 实际值"。
    """

    def __init__(self) -> None:
        self.total = 0
        self.failures: list[str] = []

    def check(self, label: str, ok: bool, expect: str, actual: str) -> None:
        self.total += 1
        if ok:
            print(f"  ✅ {label}")
        else:
            self.failures.append(label)
            print(f"  ❌ {label}")
            print(f"       期望: {expect}")
            print(f"       实际: {actual}")

    def eq(self, label: str, actual, expect) -> None:
        self.check(label, actual == expect, repr(expect), repr(actual))

    def contains(self, label: str, haystack: str, needle: str) -> None:
        self.check(label, needle in haystack, f"包含 {needle!r}", _clip(haystack))

    def absent(self, label: str, haystack: str, needle: str) -> None:
        self.check(label, needle not in haystack, f"不包含 {needle!r}", _clip(haystack))


def _clip(text: str, limit: int = 160) -> str:
    """把长文本截断成一行，避免自测失败时刷屏。"""
    flat = " ".join(text.split())
    return repr(flat[:limit] + ("…" if len(flat) > limit else ""))


def _extract_script(html_text: str) -> str:
    """取出 <script> 与 </script> 之间的内容。

    只用于自测断言，被测字符串是本文件自己生成的，正则在这里足够可靠。
    """
    m = re.search(r"<script>(.*?)</script>", html_text, re.S)
    return m.group(1) if m else ""


def self_test() -> int:
    """离线自测。全部通过返回 0 并打印 SELF-TEST OK；否则返回 1。"""
    banner("自测（--self-test）：离线验证渲染逻辑与 DOM 语义模拟")
    t = _SelfTest()

    # ── A. 输出编码器本身 ─────────────────────────────────────
    print("\n[A] HTML 输出编码 esc()")
    t.eq("esc() 把尖括号变成实体", esc(PROBE), "&lt;x152probe&gt;")
    t.absent("编码后不再出现裸的 <", esc(PROBE), "<")
    t.contains("esc() 把双引号也变成实体", esc('" onfocus="x152()"'), "&quot;")
    t.absent("编码后属性里没有裸引号（否则能凭空造出事件处理器）",
             esc('" onfocus="x152()"'), '"')
    t.eq("esc() 做的是「编码」而不是「去重」：对已编码文本再编码会变成 &amp;amp;（双重编码的来源）",
         esc("&amp;"), "&amp;amp;")

    # ── B. 反射型渲染：危险版 vs 安全版 ───────────────────────
    print("\n[B] 反射型：同一个输入，两条渲染路径")
    vuln = render_reflect(PROBE, safe=False)
    good = render_reflect(PROBE, safe=True)
    t.contains("未编码版：探测标记原样出现在响应体里（存在标签注入能力）", vuln, PROBE)
    t.absent("已编码版：响应体里没有裸的探测标记", good, PROBE)
    t.contains("已编码版：出现的是实体形式", good, "&lt;x152probe&gt;")
    t.contains("未编码版：属性上下文也被注入（value 被闭合）",
               vuln, 'value="<x152probe>"')
    t.contains("已编码版：属性值被正确编码", good, 'value="&lt;x152probe&gt;"')
    t.contains("两条路径的 HTML 骨架完全一致，只差被渲染的那一个位置",
               vuln, '<div class="search">你搜索了：')
    t.contains("安全版骨架同样一致（说明修复只改数据、不改结构）",
               good, '<div class="search">你搜索了：')

    # ── C. 存储型渲染 ─────────────────────────────────────────
    print("\n[C] 存储型：数据库存原文，输出时才编码")
    items = [PROBE, "大家好，我是正常用户"]
    t.contains("未编码版：留言原样输出（每个访客都会中招）",
               render_guestbook(items, safe=False), PROBE)
    t.absent("已编码版：留言被编码后才输出",
             render_guestbook(items, safe=True), PROBE)
    t.contains("空留言板有占位提示",
               render_guestbook([], safe=True), "（还没有留言）")
    t.eq("存储层 GUESTBOOK 是列表（原样保存，从不做输入清洗）",
         isinstance(GUESTBOOK, list), True)
    t.eq("存储型与反射型共享同一个编码器 esc()（修复点不同，原理相同）",
         esc(PROBE) in render_guestbook(items, safe=True), True)

    # ── D. DOM 型页面本身必须是安全的 ─────────────────────────
    print("\n[D] DOM 型页面：脚本块必须用 textContent，不能有 innerHTML 赋值")
    dom = render_dom_page()
    script = _extract_script(dom)
    t.contains("页面里有 <script>", dom, "<script>")
    t.contains("脚本从 location.hash 取数据（DOM 型的污点源）",
               script, "location.hash")
    t.contains("脚本用 textContent 写入（安全信宿）", script, "textContent")
    t.absent("脚本里没有 innerHTML 赋值 —— 危险写法只允许出现在注释里",
             script, "innerHTML")
    t.contains("危险写法确实以注释形式保留下来（教学价值）", dom, "innerHTML")

    # ── E. DOM sink 语义模拟器 ────────────────────────────────
    print("\n[E] ElementCollector：同一个字符串在两套 sink 下的命运")
    p1 = ElementCollector()
    p1.feed(PROBE)
    t.eq("innerHTML 语义：字符串被解析成 1 个元素", len(p1.elements), 1)
    t.eq("解析出的标签名", p1.elements[0][0] if p1.elements else None, "x152probe")
    t.eq("该元素没有属性", len(p1.elements[0][1]) if p1.elements else -1, 0)

    p2 = ElementCollector()
    p2.feed('<x152probe onload="x152()">')
    t.eq("带事件处理器的标签会被解析出属性",
         p2.elements[0][1] if p2.elements else None, [("onload", "x152()")])

    p3 = ElementCollector()
    p3.feed(esc(PROBE))
    t.eq("编码之后再进 innerHTML：解析不出任何元素（数据不再被当成代码）",
         len(p3.elements), 0)

    p4 = ElementCollector()
    p4.feed("纯文本，没有标签")
    t.eq("纯文本在 innerHTML 语义下也不产生元素（本例只收集标签）",
         len(p4.elements), 0)

    # ── 汇总 ──────────────────────────────────────────────────
    print("\n" + "─" * BANNER_WIDTH)
    if t.failures:
        print(f"❌ SELF-TEST FAILED：{len(t.failures)}/{t.total} 项不通过")
        for name in t.failures:
            print(f"   · {name}")
        return 1
    print(f"✅ SELF-TEST OK（{t.total} 项断言全部通过；无网络、无 sudo、无第三方依赖）")
    return 0


def main(argv: list[str] | None = None) -> int:
    """命令行入口。

    两种运行方式，用途完全不同：
        python3 01-xss-types-basics.py              → 起本地靶场，演示三种 XSS（联网=回环）
        python3 01-xss-types-basics.py --self-test  → 纯离线自测，秒级返回
    """
    parser = argparse.ArgumentParser(
        description="Day 152 示例 01：三种 XSS 的最小复现（本地教学靶场）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  python3 01-xss-types-basics.py              # 演示（只绑定 127.0.0.1）\n"
            "  python3 01-xss-types-basics.py --self-test  # 离线自测，输出 SELF-TEST OK\n"
        ),
    )
    parser.add_argument("--self-test", action="store_true",
                        help="只跑离线自测（不建 socket / 不联网 / 无第三方依赖）")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
