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

import html
import http.server
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
        """
        user_input = q.get("q", [""])[0]

        if safe:
            rendered = esc(user_input)
            label = "✅ safe=1 —— 已做 HTML 输出编码（html.escape）"
        else:
            rendered = user_input            # ❌ 危险：原始字节直接进 HTML
            label = "❌ safe=0 —— 原始拼接，未做任何编码"

        body = (
            f"<h1>搜索结果</h1>\n"
            f"<p>{label}</p>\n"
            f'<div class="search">你搜索了：{rendered}</div>\n'
            # 顺便演示"属性上下文"：属性值必须加引号，且同样要编码
            f'<input type="text" name="q" value="{rendered}">\n'
        )
        self._send_html(page("搜索", body))

    # ── 端点 2：存储型 ────────────────────────────────────────
    def _handle_guestbook(self, safe: bool) -> None:
        """存储型 XSS：把**数据库里读出来的**内容拼进 HTML。

        和反射型的唯一区别是数据来源：一个是"这次的请求参数"，
        一个是"之前存进去的数据"。但后果完全不同——每个访问者都会中招。
        """
        items = []
        for i, text in enumerate(GUESTBOOK, 1):
            shown = esc(text) if safe else text      # ← 唯一的分岔点
            items.append(f"<li>#{i}: {shown}</li>")

        if not items:
            items.append("<li>（还没有留言）</li>")

        mode = "✅ safe=1 输出已编码" if safe else "❌ safe=0 输出未编码"
        body = (
            f"<h1>留言板（{mode}）</h1>\n"
            f"<ul>\n" + "\n".join(items) + "\n</ul>\n"
        )
        self._send_html(page("留言板", body))

    # ── 端点 3：DOM 型 ────────────────────────────────────────
    def _handle_dom(self) -> None:
        """DOM 型 XSS：服务器**完全没有参与**。

        下面这个页面把 location.hash（# 后面的内容）直接写进 innerHTML。
        fragment 不会被浏览器发给服务器 —— 所以服务端日志、WAF、
        服务端输出编码，一个都救不了它。必须在客户端 JS 里修。
        """
        body = """<h1>DOM 型 XSS 演示页</h1>
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
        self._send_html(page("DOM 型演示", body))


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


def main() -> None:
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


if __name__ == "__main__":
    main()
