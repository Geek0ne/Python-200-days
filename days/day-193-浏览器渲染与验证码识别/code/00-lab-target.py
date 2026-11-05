#!/usr/bin/env python3
"""00-lab-target.py — 本地靶站：JS 动态渲染 + 验证码登录（真机实验台）

为什么不用真实网站做实验：
    1. 真实站点会限流、封 IP，实验不可复现；
    2. 无法控制"渲染延迟 / 验证码难度 / 失败率"，测出来的数字无法解释；
    3. 抓别人的验证码有法律风险。
    靶站是自建的，所以每个数字都可信、可复现、可回归。

页面里刻意埋了 4 个"静态抓不到"的点：
    · 商品列表由 fetch 在 700ms 后注入（静态 HTML 里只有一个空 <ul>）
    · #status 由 MutationObserver 之外的 JS 定时器改写
    · 指纹字段（canvas / WebGL / 时区 / 字体）全部在客户端计算
    · 登录必须带验证码，验证码一次性、绑定 sid

用法：
    python3 00-lab-target.py --port 8931          # 起服务
    python3 00-lab-target.py --self-test          # 离线自检，不需要浏览器
"""
from __future__ import annotations

import argparse
import json
import os
import random
import signal
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from captcha_lib import random_text, render_captcha  # noqa: E402

ITEMS = [
    {"id": i, "title": f"SKU-{1000 + i} 动态渲染商品", "price": round(19.9 + i * 3.7, 2)}
    for i in range(1, 13)
]
SESSIONS: dict[str, str] = {}      # sid -> 验证码答案（一次性）
STATS = {"captcha_served": 0, "login_ok": 0, "login_fail": 0, "items_served": 0}
LOCK = threading.Lock()

INDEX_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Day193 靶站</title>
<style>
 body{font-family:system-ui;margin:24px;max-width:760px}
 #list li{padding:6px 0;border-bottom:1px solid #eee}
 #status{color:#666;font-size:13px}
 #fp{background:#f6f6f6;padding:10px;font-size:12px;white-space:pre-wrap}
</style></head>
<body>
<h1>Day 193 动态靶站</h1>
<p id="status">booting…</p>
<ul id="list"><!-- JS 注入前是空的 --></ul>
<h2>客户端指纹</h2><div id="fp">computing…</div>
<h2>验证码</h2>
<img id="cap" src="/captcha" alt="captcha" width="160" height="60">
<form id="f"><input id="ans" autocomplete="off" placeholder="输入验证码">
<button>登录</button></form>
<pre id="result"></pre>
<script>
const t0 = performance.now();
function h(s){let x=0;for(let i=0;i<s.length;i++){x=(x*31+s.charCodeAt(i))>>>0}return x.toString(16).padStart(8,'0')}

// 700ms 后才拉数据：这就是"必须等待"的来源
setTimeout(async () => {
  const r = await fetch('/api/items?page=1&ds=700');
  const data = await r.json();
  const ul = document.getElementById('list');
  for (const it of data.items) {
    const li = document.createElement('li');
    li.textContent = it.title + ' — ¥' + it.price;
    ul.appendChild(li);
  }
  document.getElementById('status').textContent =
    'ready items=' + data.items.length + ' took=' + Math.round(performance.now() - t0) + 'ms';
}, 700);

(async () => {
  // 1) Canvas 指纹：字体渲染在不同 GPU/驱动/字体栈下像素不同
  const c = document.createElement('canvas'); c.width = 240; c.height = 60;
  const ctx = c.getContext('2d');
  ctx.textBaseline = 'top'; ctx.font = '16px "DejaVu Sans"';
  const g = ctx.createLinearGradient(0, 0, 240, 0);
  g.addColorStop(0, '#f60'); g.addColorStop(1, '#069');
  ctx.fillStyle = g; ctx.fillRect(0, 0, 240, 60);
  ctx.fillStyle = 'rgba(20,20,20,0.85)';
  ctx.fillText('Day193 指纹 😀 CwWm', 4, 8);
  const canvasHash = h(c.toDataURL());

  // 2) WebGL 指纹：真实的 GPU 型号（或 SwiftShader 软件渲染）
  let glVendor = 'n/a', glRenderer = 'n/a', glHash = 'n/a';
  try {
    const gl = document.createElement('canvas').getContext('webgl');
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    glVendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
    glRenderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    glHash = h([gl.getParameter(gl.VERSION), glVendor, glRenderer,
                gl.getParameter(gl.MAX_TEXTURE_SIZE), gl.getParameter(gl.ALIASED_LINE_WIDTH_RANGE)].join('|'));
  } catch (e) { glRenderer = 'blocked'; }

  // 3) 字体探测：同一段文字在不同字体下的宽度不同
  const probe = 'mmmmmmmmmmlli';
  const base = ['monospace', 'serif', 'sans-serif'];
  const candidates = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'Noto Sans', 'Times New Roman', 'Wingdings'];
  const span = document.createElement('span');
  span.style.cssText = 'position:absolute;left:-9999px;font-size:72px;white-space:nowrap';
  span.textContent = probe; document.body.appendChild(span);
  const widths = {};
  for (const b of base) { span.style.fontFamily = b; widths[b] = span.offsetWidth; }
  const detected = candidates.filter(f => base.some(b => {
    span.style.fontFamily = '"' + f + '",' + b; return span.offsetWidth !== widths[b];
  }));
  span.remove();

  const fp = {
    ua: navigator.userAgent,
    platform: navigator.platform,
    languages: navigator.languages,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    screen: screen.width + 'x' + screen.height,
    devicePixelRatio: window.devicePixelRatio,
    hardwareConcurrency: navigator.hardwareConcurrency,
    webdriver: navigator.webdriver,
    canvas: canvasHash,
    webglVendor: glVendor,
    webglRenderer: glRenderer,
    webglHash: glHash,
    fonts: detected,
    fontsCount: detected.length,
  };
  document.getElementById('fp').textContent = JSON.stringify(fp, null, 1);
  window.__fp = fp;
})();

document.getElementById('f').addEventListener('submit', async (e) => {
  e.preventDefault();
  const ans = document.getElementById('ans').value;
  const r = await fetch('/login', {method:'POST', headers:{'Content-Type':'application/json'},
                                   body: JSON.stringify({answer: ans})});
  document.getElementById('result').textContent = r.status + ' ' + await r.text();
});
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "Day193Lab/1.0"

    def log_message(self, fmt, *args):  # 静默，实验输出才看得清
        pass

    def _send(self, code: int, body: bytes | str, ctype: str = "text/html; charset=utf-8", cookies: list[str] | None = None):
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for c in cookies or []:
            self.send_header("Set-Cookie", c)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode())
        elif u.path == "/health":
            self._send(200, json.dumps({"ok": True, **STATS}).encode(), "application/json")
        elif u.path == "/api/items":
            ds = min(int(q.get("ds", ["0"])[0]), 5000) / 1000
            if ds:
                time.sleep(ds)          # 人为延迟，用来测"等待策略"
            page = int(q.get("page", ["1"])[0])
            with LOCK:
                STATS["items_served"] += 1
            self._send(200, json.dumps({"page": page, "items": ITEMS, "server_time": time.time()}).encode(),
                       "application/json")
        elif u.path == "/captcha":
            sid = uuid.uuid4().hex[:16]
            text = random_text(4)
            with LOCK:
                SESSIONS[sid] = text
                STATS["captcha_served"] += 1
                if len(SESSIONS) > 5000:      # 防止内存无限涨
                    for k in list(SESSIONS)[:1000]:
                        SESSIONS.pop(k, None)
            png = Path("/tmp/day193-captcha.png")
            render_captcha(text, noise="medium", seed=random.randrange(10**6)).save(png, "PNG")
            cookie = f"sid={sid}; Path=/; HttpOnly"
            self._send(200, png.read_bytes(), "image/png", [cookie])
        else:
            self._send(404, b"not found")

    def do_POST(self):
        if urlparse(self.path).path != "/login":
            self._send(404, b"not found")
            return
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            data = {}
        sid = ""
        for part in (self.headers.get("Cookie") or "").split(";"):
            if part.strip().startswith("sid="):
                sid = part.strip()[4:]
        expected = SESSIONS.pop(sid, None)     # 一次性：无论对错都作废
        ok = bool(expected) and str(data.get("answer", "")).upper() == expected
        with LOCK:
            STATS["login_ok" if ok else "login_fail"] += 1
        self._send(200 if ok else 403,
                   json.dumps({"ok": ok, "reason": "ok" if ok else ("no_sid" if expected is None else "wrong")}),
                   "application/json")


def serve(port: int):
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"靶站已启动 http://127.0.0.1:{port}/  (Ctrl-C 停止)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.shutdown()
        print("已停止")


def self_test() -> int:
    """离线自检：起临时端口 → 打 4 个接口 → 断言 → 关闭。不需要浏览器。"""
    import urllib.request

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    fails = 0

    def check(name, cond, extra=""):
        nonlocal fails
        print(("  ✅ " if cond else "  ❌ ") + name + (f"  {extra}" if extra else ""))
        fails += 0 if cond else 1

    try:
        t0 = time.time()
        html = urllib.request.urlopen(base + "/", timeout=5).read().decode()
        check("首页返回 HTML 且含空列表骨架", "<ul id=\"list\"><!--" in html, f"{(time.time()-t0)*1000:.0f}ms")

        t0 = time.time()
        data = json.loads(urllib.request.urlopen(base + "/api/items?page=1&ds=700", timeout=5).read())
        check("延迟接口真的延迟了 ≥0.6s", time.time() - t0 >= 0.6, f"{time.time()-t0:.2f}s")
        check("接口返回 12 条商品", len(data["items"]) == 12)

        # 验证码：拿 cookie 和图片，再从服务端内存里取答案（模拟"知道答案的靶场"）
        req = urllib.request.Request(base + "/captcha")
        with urllib.request.urlopen(req, timeout=5) as resp:
            png = resp.read()
            cookie = resp.headers.get("Set-Cookie", "")
            sid = cookie.split("sid=")[1].split(";")[0]
        check("验证码是 PNG 且 >1KB", png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 1024, f"{len(png)}B")
        answer = SESSIONS[sid]   # 靶场特权：直接读答案（peek，不消耗会话）

        def post(ans, sess, use_sid=True):
            # 注意：sid 必须显式传参。上一版这里闭包捕获了外层 sid，
            # 换第二张验证码时仍发旧 sid，导致"正确答案也 403"（真实翻车点）。
            body = json.dumps({"answer": ans}).encode()
            r = urllib.request.Request(base + "/login", data=body, headers={
                "Content-Type": "application/json",
                "Cookie": f"sid={sess}" if use_sid else "",
            })
            try:
                with urllib.request.urlopen(r, timeout=5) as resp:
                    return resp.status
            except urllib.error.HTTPError as e:
                return e.code

        check("错误验证码 → 403", post("ZZZZ", sid) == 403)
        check("验证码一次性（重复用正确码也失败）", post(answer, sid) == 403)

        req = urllib.request.Request(base + "/captcha")
        with urllib.request.urlopen(req, timeout=5) as resp:
            sid2 = resp.headers["Set-Cookie"].split("sid=")[1].split(";")[0]
        answer2 = SESSIONS[sid2]
        check("正确验证码 → 200", post(answer2, sid2) == 200)
        check("/health 统计可读", json.loads(urllib.request.urlopen(base + "/health", timeout=5).read())["login_ok"] >= 1)
    finally:
        srv.shutdown()
    print(f"\n自检结果：{'全部通过' if fails == 0 else f'{fails} 项失败'}")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8931)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        raise SystemExit(self_test())
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    serve(a.port)
